-- =========================================================================
-- -- TRIGGERS Y REGLAS TRANSACCIONALES
-- =========================================================================

USE torneo_futbol5;

-- -------------------------------------------------------------------------
-- VISTA: V_RESULTADO_PARTIDO
-- Calcula de forma dinamica los goles locales y visitantes considerando
-- goles normales y goles en contra (autogoles).
-- -------------------------------------------------------------------------
CREATE OR REPLACE VIEW v_resultado_partido AS
SELECT
    p.id_partido,
    p.id_torneo,
    p.numero_fecha,
    p.id_equipo_local,
    p.id_equipo_visitante,
    p.estado,
    COALESCE(gl.goles_locales, 0) AS goles_local,
    COALESCE(gv.goles_visitantes, 0) AS goles_visitante
FROM partido p
LEFT JOIN (
    -- Goles a favor del local (goles normales suyos + autogoles del visitante)
    SELECT
        pa.id_partido,
        COUNT(g.id_gol) AS goles_locales
    FROM planilla_partido pa
    JOIN partido pt ON pa.id_partido = pt.id_partido
    JOIN gol g ON pa.id_partido = g.id_partido AND pa.ci_jugador = g.ci_jugador
    WHERE (pa.id_equipo = pt.id_equipo_local AND g.autogol = false)
       OR (pa.id_equipo = pt.id_equipo_visitante AND g.autogol = true)
    GROUP BY pa.id_partido
) gl ON p.id_partido = gl.id_partido
LEFT JOIN (
    -- Goles a favor del visitante (goles normales suyos + autogoles del local)
    SELECT
        pa.id_partido,
        COUNT(g.id_gol) AS goles_visitantes
    FROM planilla_partido pa
    JOIN partido pt ON pa.id_partido = pt.id_partido
    JOIN gol g ON pa.id_partido = g.id_partido AND pa.ci_jugador = g.ci_jugador
    WHERE (pa.id_equipo = pt.id_equipo_visitante AND g.autogol = false)
       OR (pa.id_equipo = pt.id_equipo_local AND g.autogol = true)
    GROUP BY pa.id_partido
) gv ON p.id_partido = gv.id_partido;


-- =========================================================================
-- TRIGGERS
-- =========================================================================

DELIMITER //

-- -------------------------------------------------------------------------
-- 1. TRG_EQUIPO_JUGADOR_TORNEO_BEFORE_INSERT
-- Valida el limite de plantel (10 max) y docentes/funcionarios (2 max).
-- -------------------------------------------------------------------------
CREATE TRIGGER trg_equipo_jugador_torneo_before_insert
BEFORE INSERT ON equipo_jugador_torneo
FOR EACH ROW
BEGIN
    DECLARE v_total_jugadores INT;
    DECLARE v_total_df INT;
    DECLARE v_tipo_jugador VARCHAR(20);

    -- Obtener el tipo del jugador que se intenta ingresar
    SELECT tipo INTO v_tipo_jugador
    FROM jugador
    WHERE ci = NEW.ci_jugador;

    -- Contar cuantos jugadores tiene ya el equipo en ese torneo
    SELECT COUNT(*) INTO v_total_jugadores
    FROM equipo_jugador_torneo
    WHERE id_equipo = NEW.id_equipo AND id_torneo = NEW.id_torneo;

    IF v_total_jugadores >= 10 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Error: El plantel no puede tener mas de 10 jugadores.';
    END IF;

    -- Si es docente o funcionario, verificar el limite estricto de 2
    IF v_tipo_jugador IN ('docente', 'funcionario') THEN
        SELECT COUNT(*) INTO v_total_df
        FROM equipo_jugador_torneo p
        JOIN jugador j ON p.ci_jugador = j.ci
        WHERE p.id_equipo = NEW.id_equipo
          AND p.id_torneo = NEW.id_torneo
          AND j.tipo IN ('docente', 'funcionario');

        IF v_total_df >= 2 THEN
            SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Error: El plantel admite como maximo 2 jugadores de tipo docente o funcionario.';
        END IF;
    END IF;
END//


-- -------------------------------------------------------------------------
-- 2. TRG_PARTIDO_BEFORE_INSERT
-- Valida restricciones al insertar un partido (equipos y planteles min. 5).
-- -------------------------------------------------------------------------
CREATE TRIGGER trg_partido_before_insert
BEFORE INSERT ON partido
FOR EACH ROW
BEGIN
    DECLARE v_cant_local INT;
    DECLARE v_cant_visitante INT;

    -- Controlar que el equipo local y visitante no sean el mismo
    IF NEW.id_equipo_local = NEW.id_equipo_visitante THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Error: Un equipo no puede enfrentarse a si mismo.';
    END IF;

    -- Contar jugadores activos en el plantel del equipo local
    SELECT COUNT(*) INTO v_cant_local
    FROM equipo_jugador_torneo
    WHERE id_equipo = NEW.id_equipo_local AND id_torneo = NEW.id_torneo;

    IF v_cant_local < 5 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Error: El equipo local debe tener al menos 5 jugadores en su plantel para disputar el partido.';
    END IF;

    -- Contar jugadores activos en el plantel del equipo visitante
    SELECT COUNT(*) INTO v_cant_visitante
    FROM equipo_jugador_torneo
    WHERE id_equipo = NEW.id_equipo_visitante AND id_torneo = NEW.id_torneo;

    IF v_cant_visitante < 5 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Error: El equipo visitante debe tener al menos 5 jugadores en su plantel para disputar el partido.';
    END IF;
END//


-- -------------------------------------------------------------------------
-- 3. TRG_PLANILLA_BEFORE_INSERT
-- Controla que un jugador suspendido no pueda firmar planilla.
-- -------------------------------------------------------------------------
CREATE TRIGGER trg_planilla_before_insert
BEFORE INSERT ON planilla_partido
FOR EACH ROW
BEGIN
    DECLARE v_id_torneo INT;
    DECLARE v_num_fecha TINYINT;
    DECLARE v_suspenso INT;

    -- Obtener el torneo y el numero de fecha del partido
    SELECT id_torneo, numero_fecha INTO v_id_torneo, v_num_fecha
    FROM partido
    WHERE id_partido = NEW.id_partido;

    -- Verificar sancion activa abarcando la fecha
    SELECT COUNT(*) INTO v_suspenso
    FROM sancion_jugador
    WHERE ci_jugador = NEW.ci_jugador
      AND id_torneo = v_id_torneo
      AND v_num_fecha BETWEEN numero_fecha_inicio AND (numero_fecha_inicio + cantidad_fechas - 1);

    IF v_suspenso > 0 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Error: El jugador se encuentra suspendido para esta fecha y no puede firmar planilla.';
    END IF;
END//


-- -------------------------------------------------------------------------
-- 4. TRG_TARJETA_AFTER_INSERT
-- Aplica sanciones automaticas por roja directa o acumulacion de 3 amarillas.
-- -------------------------------------------------------------------------
CREATE TRIGGER trg_tarjeta_after_insert
AFTER INSERT ON tarjeta
FOR EACH ROW
BEGIN
    DECLARE v_id_torneo INT;
    DECLARE v_num_fecha TINYINT;
    DECLARE v_cant_amarillas INT;

    -- Obtener el torneo y el numero de fecha del partido actual
    SELECT p.id_torneo, p.numero_fecha
    INTO v_id_torneo, v_num_fecha
    FROM partido p
    WHERE p.id_partido = NEW.id_partido;

    -- Caso 1: Tarjeta roja directa
    IF NEW.color = 'roja' THEN
        INSERT INTO sancion_jugador (ci_jugador, id_torneo, motivo, numero_fecha_inicio, cantidad_fechas)
        VALUES (NEW.ci_jugador, v_id_torneo, 'roja', v_num_fecha + 1, 1);

    -- Caso 2: Acumulacion de tarjetas amarillas (multiplos de 3)
    ELSEIF NEW.color = 'amarilla' THEN
        SELECT COUNT(*)
        INTO v_cant_amarillas
        FROM tarjeta t
        JOIN partido p ON t.id_partido = p.id_partido
        WHERE t.ci_jugador = NEW.ci_jugador
          AND p.id_torneo = v_id_torneo
          AND t.color = 'amarilla';

        IF v_cant_amarillas % 3 = 0 THEN
            INSERT INTO sancion_jugador (ci_jugador, id_torneo, motivo, numero_fecha_inicio, cantidad_fechas)
            VALUES (NEW.ci_jugador, v_id_torneo, 'acumulacion de amarillas', v_num_fecha + 1, 1);
        END IF;
    END IF;
END//


-- -------------------------------------------------------------------------
-- 5. TRG_PARTIDO_BEFORE_UPDATE
-- Valida que un partido solo pueda marcarse como 'jugado' si ya paso el tiempo.
-- -------------------------------------------------------------------------
CREATE TRIGGER trg_partido_before_update
BEFORE UPDATE ON partido
FOR EACH ROW
BEGIN
    DECLARE v_hora_inicio TIME;
    DECLARE v_fh_partido DATETIME;

    IF NEW.estado = 'jugado' AND OLD.estado <> 'jugado' THEN
        SELECT hora_inicio INTO v_hora_inicio
        FROM turno
        WHERE id_turno = NEW.id_turno;

        SET v_fh_partido = TIMESTAMP(NEW.dia, v_hora_inicio);

        IF NOW() < v_fh_partido THEN
            SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Error: Un partido solo puede marcarse como jugado si su dia y turno ya pasaron.';
        END IF;
    END IF;
END//


-- -------------------------------------------------------------------------
-- 6. TRG_PARTIDO_BEFORE_DELETE
-- Impide eliminar fisicamente partidos que ya fueron jugados.
-- -------------------------------------------------------------------------
CREATE TRIGGER trg_partido_before_delete
BEFORE DELETE ON partido
FOR EACH ROW
BEGIN
    IF OLD.estado = 'jugado' THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Error: Un partido que ya ha sido jugado no puede ser eliminado del sistema.';
    END IF;
END//

DELIMITER ;