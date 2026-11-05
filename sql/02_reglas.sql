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
-- TRIGGERS, FUNCION Y PROCEDIMIENTO
-- =========================================================================

DELIMITER //

-- -------------------------------------------------------------------------
-- FN_CORRECCION_PERMITIDA
-- Devuelve 1 si el resultado/planilla del partido todavia se puede tocar:
-- el partido no esta 'jugado' o estan dentro de las 48 horas posteriores
-- al fin de su turno. Devuelve 0 si el resultado ya esta cerrado.
-- -------------------------------------------------------------------------
CREATE FUNCTION fn_correccion_permitida(p_id_partido INT)
RETURNS TINYINT
READS SQL DATA
BEGIN
    DECLARE v_estado VARCHAR(20);
    DECLARE v_dia DATE;
    DECLARE v_hora_fin TIME;

    SELECT p.estado, p.dia, t.hora_fin
    INTO v_estado, v_dia, v_hora_fin
    FROM partido p
    JOIN turno t ON p.id_turno = t.id_turno
    WHERE p.id_partido = p_id_partido;

    IF v_estado IS NULL OR v_estado <> 'jugado' THEN
        RETURN 1;
    END IF;

    IF NOW() <= TIMESTAMP(v_dia, v_hora_fin) + INTERVAL 48 HOUR THEN
        RETURN 1;
    END IF;

    RETURN 0;
END//

-- -------------------------------------------------------------------------
-- SP_RECALCULAR_SANCIONES_AUTOMATICAS
-- Recalcula las sanciones automaticas (roja y acumulacion de 3 amarillas) de
-- un jugador en un torneo a partir de las tarjetas que existen hoy. Solo toca
-- las sanciones con id_tarjeta (las disciplinarias cargadas a mano no se tocan).
-- Se invoca al insertar, modificar o borrar tarjetas, asi una correccion dentro
-- de las 48 horas deja las sanciones consistentes.
-- -------------------------------------------------------------------------
CREATE PROCEDURE sp_recalcular_sanciones_automaticas(IN p_ci_jugador VARCHAR(20), IN p_id_torneo INT)
BEGIN
    DELETE FROM sancion_jugador
    WHERE ci_jugador = p_ci_jugador
      AND id_torneo = p_id_torneo
      AND id_tarjeta IS NOT NULL;

    -- Una fecha de suspension por cada tarjeta roja (fecha siguiente a la del partido)
    INSERT INTO sancion_jugador (ci_jugador, id_torneo, motivo, numero_fecha_inicio, cantidad_fechas, id_tarjeta)
    SELECT t.ci_jugador, p.id_torneo, 'roja', p.numero_fecha + 1, 1, t.id_tarjeta
    FROM tarjeta t
    JOIN partido p ON t.id_partido = p.id_partido
    WHERE t.ci_jugador = p_ci_jugador
      AND p.id_torneo = p_id_torneo
      AND t.color = 'roja';

    -- Una fecha de suspension por cada 3 amarillas acumuladas (en orden cronologico).
    -- El numero de orden de cada amarilla es la cantidad de amarillas del jugador
    -- que ocurrieron hasta ella (por fecha, partido, minuto y id).
    INSERT INTO sancion_jugador (ci_jugador, id_torneo, motivo, numero_fecha_inicio, cantidad_fechas, id_tarjeta)
    SELECT t.ci_jugador, p.id_torneo, 'acumulacion de amarillas', p.numero_fecha + 1, 1, t.id_tarjeta
    FROM tarjeta t
    JOIN partido p ON t.id_partido = p.id_partido
    WHERE t.ci_jugador = p_ci_jugador
      AND p.id_torneo = p_id_torneo
      AND t.color = 'amarilla'
      AND (
          SELECT COUNT(*)
          FROM tarjeta t2
          JOIN partido p2 ON t2.id_partido = p2.id_partido
          WHERE t2.ci_jugador = t.ci_jugador
            AND p2.id_torneo = p.id_torneo
            AND t2.color = 'amarilla'
            AND (p2.numero_fecha < p.numero_fecha
                 OR (p2.numero_fecha = p.numero_fecha AND p2.id_partido < p.id_partido)
                 OR (p2.id_partido = p.id_partido AND t2.minuto < t.minuto)
                 OR (p2.id_partido = p.id_partido AND t2.minuto = t.minuto AND t2.id_tarjeta <= t.id_tarjeta))
      ) % 3 = 0;
END//


-- -------------------------------------------------------------------------
-- 1. TRG_EQUIPO_JUGADOR_TORNEO_BEFORE_INSERT
-- Valida: torneo en inscripcion, jugador de la facultad del equipo,
-- limite de plantel (10 max) y docentes/funcionarios (2 max).
-- -------------------------------------------------------------------------
CREATE TRIGGER trg_equipo_jugador_torneo_before_insert
BEFORE INSERT ON equipo_jugador_torneo
FOR EACH ROW
BEGIN
    DECLARE v_total_jugadores INT;
    DECLARE v_total_df INT;
    DECLARE v_tipo_jugador VARCHAR(20);
    DECLARE v_estado_torneo VARCHAR(20);
    DECLARE v_fac_jugador INT;
    DECLARE v_fac_equipo INT;

    -- Los planteles solo pueden modificarse durante la inscripcion
    SELECT estado INTO v_estado_torneo
    FROM torneo
    WHERE id_torneo = NEW.id_torneo;

    IF v_estado_torneo <> 'inscripcion' THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Error: Los planteles solo pueden modificarse mientras el torneo esta en inscripcion.';
    END IF;

    -- Obtener tipo y facultad del jugador que se intenta ingresar
    SELECT tipo, id_facultad INTO v_tipo_jugador, v_fac_jugador
    FROM jugador
    WHERE ci = NEW.ci_jugador;

    -- El jugador debe pertenecer a la facultad que el equipo representa
    SELECT id_facultad INTO v_fac_equipo
    FROM equipo
    WHERE id_equipo = NEW.id_equipo;

    IF v_fac_jugador <> v_fac_equipo THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Error: El jugador debe pertenecer a la facultad que representa el equipo.';
    END IF;

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
-- 1.b TRG_EQUIPO_JUGADOR_TORNEO_BEFORE_UPDATE
-- Solo en inscripcion; solo permite cambiar el numero de camiseta.
-- -------------------------------------------------------------------------
CREATE TRIGGER trg_equipo_jugador_torneo_before_update
BEFORE UPDATE ON equipo_jugador_torneo
FOR EACH ROW
BEGIN
    DECLARE v_estado_torneo VARCHAR(20);

    SELECT estado INTO v_estado_torneo
    FROM torneo
    WHERE id_torneo = OLD.id_torneo;

    IF v_estado_torneo <> 'inscripcion' THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Error: Los planteles solo pueden modificarse mientras el torneo esta en inscripcion.';
    END IF;

    IF NEW.id_equipo <> OLD.id_equipo
       OR NEW.ci_jugador <> OLD.ci_jugador
       OR NEW.id_torneo <> OLD.id_torneo THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Error: Para cambiar a un jugador de equipo, eliminelo del plantel y vuelva a inscribirlo.';
    END IF;
END//


-- -------------------------------------------------------------------------
-- 1.c TRG_EQUIPO_JUGADOR_TORNEO_BEFORE_DELETE
-- Solo en inscripcion; no se puede quitar al capitan del plantel.
-- -------------------------------------------------------------------------
CREATE TRIGGER trg_equipo_jugador_torneo_before_delete
BEFORE DELETE ON equipo_jugador_torneo
FOR EACH ROW
BEGIN
    DECLARE v_estado_torneo VARCHAR(20);

    SELECT estado INTO v_estado_torneo
    FROM torneo
    WHERE id_torneo = OLD.id_torneo;

    IF v_estado_torneo <> 'inscripcion' THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Error: Los planteles solo pueden modificarse mientras el torneo esta en inscripcion.';
    END IF;

    IF EXISTS (SELECT 1 FROM equipo
               WHERE id_equipo = OLD.id_equipo AND ci_capitan = OLD.ci_jugador) THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Error: No se puede quitar al capitan del plantel; cambie primero el capitan del equipo.';
    END IF;
END//


-- -------------------------------------------------------------------------
-- 1.d TRG_EQUIPO_BEFORE_UPDATE
-- El nuevo capitan debe ser un jugador del plantel del equipo.
-- -------------------------------------------------------------------------
CREATE TRIGGER trg_equipo_before_update
BEFORE UPDATE ON equipo
FOR EACH ROW
BEGIN
    IF NEW.ci_capitan <> OLD.ci_capitan THEN
        IF NOT EXISTS (SELECT 1 FROM equipo_jugador_torneo
                       WHERE id_equipo = NEW.id_equipo
                         AND id_torneo = NEW.id_torneo
                         AND ci_jugador = NEW.ci_capitan) THEN
            SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Error: El capitan debe ser uno de los jugadores del plantel del equipo.';
        END IF;
    END IF;
END//


-- -------------------------------------------------------------------------
-- 1.e TRG_TORNEO_BEFORE_UPDATE
-- Al cerrar la inscripcion, todos los capitanes deben estar en su plantel y
-- cada plantel debe tener al menos 5 jugadores.
-- -------------------------------------------------------------------------
CREATE TRIGGER trg_torneo_before_update
BEFORE UPDATE ON torneo
FOR EACH ROW
BEGIN
    IF OLD.estado = 'inscripcion' AND NEW.estado <> 'inscripcion' THEN
        -- Todos los capitanes deben estar en su plantel
        IF EXISTS (
            SELECT 1
            FROM equipo e
            WHERE e.id_torneo = OLD.id_torneo
              AND NOT EXISTS (
                  SELECT 1
                  FROM equipo_jugador_torneo ejt
                  WHERE ejt.id_equipo = e.id_equipo
                    AND ejt.id_torneo = e.id_torneo
                    AND ejt.ci_jugador = e.ci_capitan
              )
        ) THEN
            SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Error: Todos los equipos deben tener a su capitan en el plantel para cerrar la inscripcion.';
        END IF;

        -- Todos los planteles deben tener al menos 5 jugadores (el maximo de 10 se controla al inscribir)
        IF EXISTS (
            SELECT 1
            FROM equipo e
            WHERE e.id_torneo = OLD.id_torneo
              AND (SELECT COUNT(*)
                   FROM equipo_jugador_torneo ejt
                   WHERE ejt.id_equipo = e.id_equipo
                     AND ejt.id_torneo = e.id_torneo) < 5
        ) THEN
            SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Error: Todos los equipos deben tener al menos 5 jugadores en su plantel para cerrar la inscripcion.';
        END IF;
    END IF;
END//


-- -------------------------------------------------------------------------
-- 2. TRG_PARTIDO_BEFORE_INSERT
-- Valida restricciones al insertar un partido: equipos, planteles min. 5,
-- 'jugado' solo si el turno ya paso, y conflictos de cancha/rival/fecha.
-- -------------------------------------------------------------------------
CREATE TRIGGER trg_partido_before_insert
BEFORE INSERT ON partido
FOR EACH ROW
BEGIN
    DECLARE v_cant_local INT;
    DECLARE v_cant_visitante INT;
    DECLARE v_hora_fin TIME;

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

    -- Un partido no puede crearse directamente como jugado si su dia y turno no pasaron
    IF NEW.estado = 'jugado' THEN
        SELECT hora_fin INTO v_hora_fin
        FROM turno
        WHERE id_turno = NEW.id_turno;

        IF NOW() < TIMESTAMP(NEW.dia, v_hora_fin) THEN
            SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Error: Un partido solo puede marcarse como jugado si su dia y turno ya pasaron.';
        END IF;
    END IF;

    -- Controles de programacion (no aplican a partidos cancelados)
    IF NEW.estado <> 'cancelado' THEN
        -- Una cancha no puede tener dos partidos en el mismo dia y turno
        IF EXISTS (SELECT 1 FROM partido WHERE id_torneo = NEW.id_torneo
                   AND dia = NEW.dia AND id_turno = NEW.id_turno
                   AND nombre_cancha = NEW.nombre_cancha AND id_complejo = NEW.id_complejo
                   AND estado <> 'cancelado') THEN
            SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Error: La cancha ya tiene un partido en ese dia y turno.';
        END IF;

        -- Los mismos equipos no pueden enfrentarse dos veces en la edicion
        IF EXISTS (SELECT 1 FROM partido WHERE id_torneo = NEW.id_torneo AND estado <> 'cancelado'
                   AND ((id_equipo_local = NEW.id_equipo_local AND id_equipo_visitante = NEW.id_equipo_visitante)
                     OR (id_equipo_local = NEW.id_equipo_visitante AND id_equipo_visitante = NEW.id_equipo_local))) THEN
            SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Error: Estos equipos ya se enfrentan en esta edicion.';
        END IF;

        -- Un equipo no puede jugar mas de un partido en la misma fecha
        IF EXISTS (SELECT 1 FROM partido WHERE id_torneo = NEW.id_torneo AND numero_fecha = NEW.numero_fecha
                   AND estado <> 'cancelado'
                   AND (id_equipo_local IN (NEW.id_equipo_local, NEW.id_equipo_visitante)
                     OR id_equipo_visitante IN (NEW.id_equipo_local, NEW.id_equipo_visitante))) THEN
            SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Error: Un equipo ya tiene partido en esa fecha.';
        END IF;
    END IF;
END//


-- -------------------------------------------------------------------------
-- 3. TRG_PLANILLA_BEFORE_INSERT
-- La planilla solo admite jugadores del plantel de alguno de los dos equipos
-- del partido, no suspendidos, y dentro de la ventana de correccion de 48 h.
-- -------------------------------------------------------------------------
CREATE TRIGGER trg_planilla_before_insert
BEFORE INSERT ON planilla_partido
FOR EACH ROW
BEGIN
    DECLARE v_id_torneo INT;
    DECLARE v_num_fecha TINYINT;
    DECLARE v_local INT;
    DECLARE v_visitante INT;
    DECLARE v_en_plantel INT;
    DECLARE v_suspenso INT;

    -- Obtener el torneo, la fecha y los equipos del partido
    SELECT id_torneo, numero_fecha, id_equipo_local, id_equipo_visitante
    INTO v_id_torneo, v_num_fecha, v_local, v_visitante
    FROM partido
    WHERE id_partido = NEW.id_partido;

    -- El equipo indicado debe ser uno de los dos que disputan el partido
    IF NEW.id_equipo NOT IN (v_local, v_visitante) THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Error: El equipo indicado no participa en este partido.';
    END IF;

    -- El jugador debe pertenecer al plantel de ese equipo en el torneo
    SELECT COUNT(*) INTO v_en_plantel
    FROM equipo_jugador_torneo
    WHERE id_equipo = NEW.id_equipo
      AND ci_jugador = NEW.ci_jugador
      AND id_torneo = v_id_torneo;

    IF v_en_plantel = 0 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Error: El jugador no integra el plantel del equipo indicado.';
    END IF;

    -- Ventana de correccion de 48 horas
    IF fn_correccion_permitida(NEW.id_partido) = 0 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Error: El resultado solo puede corregirse dentro de las 48 horas posteriores al partido.';
    END IF;

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
-- 3.b TRG_PLANILLA_BEFORE_UPDATE
-- No se permite cambiar partido, jugador o equipo de una fila de planilla
-- (evita saltear los controles de suspension y plantel). Para corregir:
-- eliminar la fila y cargar una nueva.
-- -------------------------------------------------------------------------
CREATE TRIGGER trg_planilla_before_update
BEFORE UPDATE ON planilla_partido
FOR EACH ROW
BEGIN
    IF NEW.id_partido <> OLD.id_partido
       OR NEW.ci_jugador <> OLD.ci_jugador
       OR NEW.id_equipo <> OLD.id_equipo THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Error: No se puede modificar una fila de planilla; eliminela y cargue una nueva.';
    END IF;
END//


-- -------------------------------------------------------------------------
-- 3.c TRG_PLANILLA_BEFORE_DELETE
-- Respeta la ventana de correccion de 48 horas y recalcula las sanciones
-- automaticas si el jugador tenia tarjetas en el partido.
-- -------------------------------------------------------------------------
CREATE TRIGGER trg_planilla_before_delete
BEFORE DELETE ON planilla_partido
FOR EACH ROW
BEGIN
    IF fn_correccion_permitida(OLD.id_partido) = 0 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Error: El resultado solo puede corregirse dentro de las 48 horas posteriores al partido.';
    END IF;

    -- Se borran explicitamente las tarjetas del jugador en este partido para que
    -- se recalculen sus sanciones automaticas (el borrado en cascada no dispara triggers).
    DELETE FROM tarjeta
    WHERE id_partido = OLD.id_partido
      AND ci_jugador = OLD.ci_jugador;
END//


-- -------------------------------------------------------------------------
-- 3.d GOLES: ventana de correccion de 48 horas
-- -------------------------------------------------------------------------
CREATE TRIGGER trg_gol_before_insert
BEFORE INSERT ON gol
FOR EACH ROW
BEGIN
    IF fn_correccion_permitida(NEW.id_partido) = 0 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Error: El resultado solo puede corregirse dentro de las 48 horas posteriores al partido.';
    END IF;
END//

CREATE TRIGGER trg_gol_before_update
BEFORE UPDATE ON gol
FOR EACH ROW
BEGIN
    IF fn_correccion_permitida(OLD.id_partido) = 0 OR fn_correccion_permitida(NEW.id_partido) = 0 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Error: El resultado solo puede corregirse dentro de las 48 horas posteriores al partido.';
    END IF;
END//

CREATE TRIGGER trg_gol_before_delete
BEFORE DELETE ON gol
FOR EACH ROW
BEGIN
    IF fn_correccion_permitida(OLD.id_partido) = 0 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Error: El resultado solo puede corregirse dentro de las 48 horas posteriores al partido.';
    END IF;
END//


-- -------------------------------------------------------------------------
-- 3.e TARJETAS: ventana de correccion de 48 horas
-- -------------------------------------------------------------------------
CREATE TRIGGER trg_tarjeta_before_insert
BEFORE INSERT ON tarjeta
FOR EACH ROW
BEGIN
    IF fn_correccion_permitida(NEW.id_partido) = 0 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Error: El resultado solo puede corregirse dentro de las 48 horas posteriores al partido.';
    END IF;
END//

CREATE TRIGGER trg_tarjeta_before_update
BEFORE UPDATE ON tarjeta
FOR EACH ROW
BEGIN
    IF fn_correccion_permitida(OLD.id_partido) = 0 OR fn_correccion_permitida(NEW.id_partido) = 0 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Error: El resultado solo puede corregirse dentro de las 48 horas posteriores al partido.';
    END IF;
END//

CREATE TRIGGER trg_tarjeta_before_delete
BEFORE DELETE ON tarjeta
FOR EACH ROW
BEGIN
    IF fn_correccion_permitida(OLD.id_partido) = 0 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Error: El resultado solo puede corregirse dentro de las 48 horas posteriores al partido.';
    END IF;
END//


-- -------------------------------------------------------------------------
-- 4. TRG_TARJETA_AFTER_INSERT
-- Aplica sanciones automaticas por roja directa o acumulacion de 3 amarillas
-- (delegando el calculo en sp_recalcular_sanciones_automaticas).
-- -------------------------------------------------------------------------
CREATE TRIGGER trg_tarjeta_after_insert
AFTER INSERT ON tarjeta
FOR EACH ROW
BEGIN
    DECLARE v_id_torneo INT;

    SELECT id_torneo INTO v_id_torneo
    FROM partido
    WHERE id_partido = NEW.id_partido;

    CALL sp_recalcular_sanciones_automaticas(NEW.ci_jugador, v_id_torneo);
END//


-- -------------------------------------------------------------------------
-- 4.b TRG_TARJETA_AFTER_UPDATE
-- Si se corrige una tarjeta (color, jugador o partido), se recalculan las
-- sanciones automaticas del/los jugadores afectados.
-- -------------------------------------------------------------------------
CREATE TRIGGER trg_tarjeta_after_update
AFTER UPDATE ON tarjeta
FOR EACH ROW
BEGIN
    DECLARE v_torneo_old INT;
    DECLARE v_torneo_new INT;

    SELECT id_torneo INTO v_torneo_old FROM partido WHERE id_partido = OLD.id_partido;
    SELECT id_torneo INTO v_torneo_new FROM partido WHERE id_partido = NEW.id_partido;

    CALL sp_recalcular_sanciones_automaticas(OLD.ci_jugador, v_torneo_old);

    IF NEW.ci_jugador <> OLD.ci_jugador OR v_torneo_new <> v_torneo_old THEN
        CALL sp_recalcular_sanciones_automaticas(NEW.ci_jugador, v_torneo_new);
    END IF;
END//


-- -------------------------------------------------------------------------
-- 4.c TRG_TARJETA_AFTER_DELETE
-- Si se elimina una tarjeta, se retiran/recalculan las sanciones automaticas.
-- -------------------------------------------------------------------------
CREATE TRIGGER trg_tarjeta_after_delete
AFTER DELETE ON tarjeta
FOR EACH ROW
BEGIN
    DECLARE v_id_torneo INT;

    SELECT id_torneo INTO v_id_torneo
    FROM partido
    WHERE id_partido = OLD.id_partido;

    IF v_id_torneo IS NOT NULL THEN
        CALL sp_recalcular_sanciones_automaticas(OLD.ci_jugador, v_id_torneo);
    END IF;
END//


-- -------------------------------------------------------------------------
-- 5. TRG_PARTIDO_BEFORE_UPDATE
-- - Un partido jugado queda cerrado pasadas las 48 horas.
-- - Solo puede marcarse 'jugado' si su dia y turno ya pasaron (fin del turno).
-- - Mantiene los controles de cancha, rival y fecha.
-- -------------------------------------------------------------------------
CREATE TRIGGER trg_partido_before_update
BEFORE UPDATE ON partido
FOR EACH ROW
BEGIN
    DECLARE v_hora_fin TIME;

    -- Resultado cerrado: no se puede tocar un partido jugado pasadas 48 horas
    IF OLD.estado = 'jugado' AND fn_correccion_permitida(OLD.id_partido) = 0 THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Error: El resultado solo puede corregirse dentro de las 48 horas posteriores al partido.';
    END IF;

    IF NEW.estado = 'jugado' AND OLD.estado <> 'jugado' THEN
        SELECT hora_fin INTO v_hora_fin
        FROM turno
        WHERE id_turno = NEW.id_turno;

        IF NOW() < TIMESTAMP(NEW.dia, v_hora_fin) THEN
            SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Error: Un partido solo puede marcarse como jugado si su dia y turno ya pasaron.';
        END IF;
    END IF;

    -- Controles de programacion (no aplican a partidos cancelados)
    IF NEW.estado <> 'cancelado' THEN
        -- Una cancha no puede tener dos partidos en el mismo dia y turno
        IF EXISTS (SELECT 1 FROM partido WHERE id_torneo = NEW.id_torneo AND id_partido <> NEW.id_partido
                   AND dia = NEW.dia AND id_turno = NEW.id_turno
                   AND nombre_cancha = NEW.nombre_cancha AND id_complejo = NEW.id_complejo
                   AND estado <> 'cancelado') THEN
            SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Error: La cancha ya tiene un partido en ese dia y turno.';
        END IF;

        -- Los mismos equipos no pueden enfrentarse dos veces en la edicion
        IF EXISTS (SELECT 1 FROM partido WHERE id_torneo = NEW.id_torneo AND id_partido <> NEW.id_partido AND estado <> 'cancelado'
                   AND ((id_equipo_local = NEW.id_equipo_local AND id_equipo_visitante = NEW.id_equipo_visitante)
                     OR (id_equipo_local = NEW.id_equipo_visitante AND id_equipo_visitante = NEW.id_equipo_local))) THEN
            SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Error: Estos equipos ya se enfrentan en esta edicion.';
        END IF;

        -- Un equipo no puede jugar mas de un partido en la misma fecha
        IF EXISTS (SELECT 1 FROM partido WHERE id_torneo = NEW.id_torneo AND id_partido <> NEW.id_partido AND numero_fecha = NEW.numero_fecha
                   AND estado <> 'cancelado'
                   AND (id_equipo_local IN (NEW.id_equipo_local, NEW.id_equipo_visitante)
                     OR id_equipo_visitante IN (NEW.id_equipo_local, NEW.id_equipo_visitante))) THEN
            SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Error: Un equipo ya tiene partido en esa fecha.';
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

    -- Se borran explicitamente las tarjetas del partido para recalcular sanciones automaticas
    DELETE FROM tarjeta WHERE id_partido = OLD.id_partido;
END//


-- -------------------------------------------------------------------------
-- SP_MARCAR_PARTIDO_JUGADO
-- Unica via con la que el planillero cambia el estado de un partido.
-- Se ejecuta con los permisos del DEFINER, asi el planillero no necesita
-- UPDATE sobre la tabla partido. El trigger valida que el turno ya paso.
-- -------------------------------------------------------------------------
CREATE PROCEDURE sp_marcar_partido_jugado(IN p_id_partido INT)
SQL SECURITY DEFINER
BEGIN
    DECLARE v_estado VARCHAR(20);

    SELECT estado INTO v_estado
    FROM partido
    WHERE id_partido = p_id_partido;

    IF v_estado IS NULL THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Error: El partido indicado no existe.';
    END IF;

    IF v_estado <> 'programado' THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Error: Solo un partido programado puede marcarse como jugado.';
    END IF;

    UPDATE partido SET estado = 'jugado' WHERE id_partido = p_id_partido;
END//

DELIMITER ;
