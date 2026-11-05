-- =========================================================================
-- CONSULTAS
-- Incluye consultas operativas de la aplicación y reportes obligatorios y sugeridos.
-- =========================================================================

USE torneo_futbol5;

-- =========================================================================
-- CONSULTAS OPERATIVAS (Necesarias para la interfaz en Python)
-- =========================================================================

-- Fixture y resultados por fecha:
-- Para mostrar partidos de una fecha
SELECT
    p.numero_fecha,
    p.dia,
    t.hora_inicio,
    el.nombre AS equipo_local,
    COALESCE(vr.goles_local, '-') AS goles_local,
    COALESCE(vr.goles_visitante, '-') AS goles_visitante,
    ev.nombre AS equipo_visitante,
    p.nombre_cancha,
    p.estado
FROM partido p
JOIN equipo el ON p.id_equipo_local = el.id_equipo
JOIN equipo ev ON p.id_equipo_visitante = ev.id_equipo
JOIN turno t ON p.id_turno = t.id_turno
LEFT JOIN v_resultado_partido vr ON p.id_partido = vr.id_partido
WHERE p.id_torneo = 1 AND p.numero_fecha = 1
ORDER BY p.dia, t.hora_inicio;

-- Plantel por equipo:
-- Para listar jugadores al armar planillas
SELECT
    ejt.numero_camiseta,
    j.ci,
    j.nombre,
    j.apellido,
    j.tipo AS tipo_jugador,
    f.nombre AS facultad
FROM equipo_jugador_torneo ejt
JOIN jugador j ON ejt.ci_jugador = j.ci
JOIN facultad f ON j.id_facultad = f.id_facultad
WHERE ejt.id_equipo = 1 AND ejt.id_torneo = 1
ORDER BY ejt.numero_camiseta;

-- Control disciplinario general y sanciones de un torneo
SELECT
    s.id_sancion,
    j.ci,
    j.nombre,
    j.apellido,
    eq.nombre AS equipo,
    s.motivo,
    s.numero_fecha_inicio,
    s.cantidad_fechas
FROM sancion_jugador s
JOIN jugador j ON s.ci_jugador = j.ci
JOIN equipo_jugador_torneo ejt ON j.ci = ejt.ci_jugador AND s.id_torneo = ejt.id_torneo
JOIN equipo eq ON ejt.id_equipo = eq.id_equipo
WHERE s.id_torneo = 1;


-- =========================================================================
-- REPORTES OBLIGATORIOS Y SUGERIDOS
-- =========================================================================

-- Tabla de posiciones de una edición del torneo
SELECT
    e.nombre AS equipo,
    COUNT(p.id_partido) AS pj,
    SUM(CASE
        WHEN (p.id_equipo_local = e.id_equipo AND p.goles_local > p.goles_visitante) OR
             (p.id_equipo_visitante = e.id_equipo AND p.goles_visitante > p.goles_local) THEN 1
        ELSE 0
    END) AS pg,
    SUM(CASE WHEN p.goles_local = p.goles_visitante THEN 1 ELSE 0 END) AS pe,
    SUM(CASE
        WHEN (p.id_equipo_local = e.id_equipo AND p.goles_local < p.goles_visitante) OR
             (p.id_equipo_visitante = e.id_equipo AND p.goles_visitante < p.goles_local) THEN 1
        ELSE 0
    END) AS pp,
    SUM(CASE WHEN p.id_equipo_local = e.id_equipo THEN p.goles_local ELSE p.goles_visitante END) AS gf,
    SUM(CASE WHEN p.id_equipo_local = e.id_equipo THEN p.goles_visitante ELSE p.goles_local END) AS gc,
    (SUM(CASE WHEN p.id_equipo_local = e.id_equipo THEN p.goles_local ELSE p.goles_visitante END) -
     SUM(CASE WHEN p.id_equipo_local = e.id_equipo THEN p.goles_visitante ELSE p.goles_local END)) AS dg,
    (SUM(CASE
        WHEN (p.id_equipo_local = e.id_equipo AND p.goles_local > p.goles_visitante) OR
             (p.id_equipo_visitante = e.id_equipo AND p.goles_visitante > p.goles_local) THEN 3
        WHEN p.goles_local = p.goles_visitante THEN 1
        ELSE 0
    END)) AS puntos
FROM equipo e
JOIN v_resultado_partido p ON e.id_equipo = p.id_equipo_local OR e.id_equipo = p.id_equipo_visitante
WHERE p.estado = 'jugado' AND e.id_torneo = 1
GROUP BY e.id_equipo, e.nombre
ORDER BY puntos DESC, dg DESC, gf DESC;

-- Tabla de goleadores:
-- Top 10 jugadores con más goles
SELECT
    j.nombre,
    j.apellido,
    eq.nombre AS equipo,
    COUNT(g.id_gol) AS total_goles
FROM gol g
JOIN planilla_partido pa ON g.id_partido = pa.id_partido AND g.ci_jugador = pa.ci_jugador
JOIN jugador j ON pa.ci_jugador = j.ci
JOIN equipo_jugador_torneo ejt ON j.ci = ejt.ci_jugador AND ejt.id_equipo = pa.id_equipo
JOIN equipo eq ON ejt.id_equipo = eq.id_equipo
WHERE g.autogol = FALSE AND ejt.id_torneo = 1
GROUP BY j.ci, j.nombre, j.apellido, eq.nombre
ORDER BY total_goles DESC
LIMIT 10;

-- Tabla de Fair Play por equipo
SELECT
    e.id_equipo,
    e.nombre AS equipo,
    COALESCE(SUM(CASE WHEN t.color = 'amarilla' THEN 1 ELSE 0 END), 0) AS amarillas,
    COALESCE(SUM(CASE WHEN t.color = 'roja' THEN 1 ELSE 0 END), 0) AS rojas,
    COALESCE(SUM(CASE WHEN t.color = 'amarilla' THEN 1 WHEN t.color = 'roja' THEN 3 ELSE 0 END), 0) AS puntaje
FROM equipo e
LEFT JOIN equipo_jugador_torneo ejt ON e.id_equipo = ejt.id_equipo
LEFT JOIN planilla_partido pa ON ejt.ci_jugador = pa.ci_jugador AND ejt.id_equipo = pa.id_equipo
LEFT JOIN partido p ON pa.id_partido = p.id_partido AND p.estado = 'jugado' AND p.id_torneo = e.id_torneo
LEFT JOIN tarjeta t ON pa.id_partido = t.id_partido AND pa.ci_jugador = t.ci_jugador
WHERE e.id_torneo = 1
GROUP BY e.id_equipo, e.nombre
ORDER BY puntaje ASC, rojas ASC, amarillas ASC;

-- Promedio de goles por fecha
SELECT
    p.numero_fecha,
    COUNT(DISTINCT p.id_partido) AS total_partidos,
    COUNT(g.id_gol) AS total_goles,
    ROUND(COUNT(g.id_gol) * 1.0 / COUNT(DISTINCT p.id_partido), 2) AS prom_goles_fecha
FROM partido p
LEFT JOIN gol g ON p.id_partido = g.id_partido
WHERE p.id_torneo = 1 AND p.estado = 'jugado'
GROUP BY p.numero_fecha
ORDER BY p.numero_fecha;

-- Promedio global en toda la edición
SELECT
    p.id_torneo,
    COUNT(DISTINCT p.id_partido) AS total_partidos_edicion,
    COUNT(g.id_gol) AS total_goles_edicion,
    ROUND(COUNT(g.id_gol) * 1.0 / COUNT(DISTINCT p.id_partido), 2) AS prom_goles_edicion
FROM partido p
LEFT JOIN gol g ON p.id_partido = g.id_partido
WHERE p.id_torneo = 1 AND p.estado = 'jugado'
GROUP BY p.id_torneo;

-- Canchas más utilizadas
SELECT
    c.id_complejo,
    co.nombre AS complejo,
    c.nombre_cancha,
    COUNT(p.id_partido) AS cant_partidos
FROM cancha c
JOIN complejo co ON c.id_complejo = co.id_complejo
JOIN partido p ON c.nombre_cancha = p.nombre_cancha AND c.id_complejo = p.id_complejo
WHERE p.id_torneo = 1 AND p.estado = 'jugado'
GROUP BY c.id_complejo, co.nombre, c.nombre_cancha
ORDER BY cant_partidos DESC;

-- Turnos más utilizados
SELECT
    t.id_turno,
    t.hora_inicio,
    t.hora_fin,
    COUNT(p.id_partido) AS cant_partidos
FROM turno t
JOIN partido p ON t.id_turno = p.id_turno
WHERE p.id_torneo = 1 AND p.estado = 'jugado'
GROUP BY t.id_turno, t.hora_inicio, t.hora_fin
ORDER BY cant_partidos DESC;

-- Cantidad de jugadores por facultad y por tipo
SELECT
    f.id_facultad,
    f.nombre AS facultad,
    j.tipo,
    COUNT(j.ci) AS cantidad_jugadores
FROM facultad f
JOIN jugador j ON f.id_facultad = j.id_facultad
GROUP BY f.id_facultad, f.nombre, j.tipo
ORDER BY f.nombre, j.tipo;

-- Jugadores inscriptos que nunca figuraron en planilla
SELECT
    e.nombre AS equipo,
    j.ci,
    j.nombre,
    j.apellido,
    j.tipo
FROM equipo_jugador_torneo ejt
JOIN jugador j ON ejt.ci_jugador = j.ci
JOIN equipo e ON ejt.id_equipo = e.id_equipo
WHERE ejt.id_torneo = 1
  AND NOT EXISTS (
      SELECT 1
      FROM planilla_partido pa
      JOIN partido p ON pa.id_partido = p.id_partido
      WHERE pa.ci_jugador = ejt.ci_jugador
        AND pa.id_equipo = ejt.id_equipo
        AND p.id_torneo = 1
  )
ORDER BY e.nombre, j.apellido, j.nombre;

-- Cantidad de sanciones por equipo y por motivo
SELECT
    e.nombre AS equipo,
    s.motivo,
    COUNT(s.id_sancion) AS cant_sanciones
FROM sancion_jugador s
JOIN equipo_jugador_torneo ejt ON s.ci_jugador = ejt.ci_jugador AND s.id_torneo = ejt.id_torneo
JOIN equipo e ON ejt.id_equipo = e.id_equipo
WHERE s.id_torneo = 1
GROUP BY e.id_equipo, e.nombre, s.motivo
ORDER BY e.nombre, cant_sanciones DESC;

-- Porcentaje de partidos jugados vs. postergados/cancelados
SELECT
    id_torneo,
    COUNT(id_partido) AS total_partidos,
    SUM(CASE WHEN estado = 'jugado' THEN 1 ELSE 0 END) AS jugados,
    SUM(CASE WHEN estado IN ('postergado', 'cancelado') THEN 1 ELSE 0 END) AS post_canc,
    ROUND(SUM(CASE WHEN estado = 'jugado' THEN 1 ELSE 0 END) * 100.0 / COUNT(id_partido), 2) AS pct_jugados,
    ROUND(SUM(CASE WHEN estado IN ('postergado', 'cancelado') THEN 1 ELSE 0 END) * 100.0 / COUNT(id_partido), 2) AS pct_post_canc
FROM partido
WHERE id_torneo = 1
GROUP BY id_torneo;

-- Jugadores con "Asistencia Perfecta" en su equipo
SELECT
    j.ci,
    j.nombre,
    j.apellido,
    e.nombre AS equipo
FROM equipo_jugador_torneo ejt
JOIN jugador j ON ejt.ci_jugador = j.ci
JOIN equipo e ON ejt.id_equipo = e.id_equipo
WHERE ejt.id_torneo = 1
  AND NOT EXISTS (
      SELECT p.id_partido
      FROM partido p
      WHERE p.id_torneo = 1
        AND p.estado = 'jugado'
        AND (p.id_equipo_local = ejt.id_equipo OR p.id_equipo_visitante = ejt.id_equipo)
        AND NOT EXISTS (
            SELECT 1
            FROM planilla_partido pa
            WHERE pa.id_partido = p.id_partido
              AND pa.ci_jugador = ejt.ci_jugador
              AND pa.id_equipo = ejt.id_equipo
        )
  )
  AND EXISTS (
      SELECT 1
      FROM partido p
      WHERE p.id_torneo = 1
        AND p.estado = 'jugado'
        AND (p.id_equipo_local = ejt.id_equipo OR p.id_equipo_visitante = ejt.id_equipo)
  )
ORDER BY e.nombre, j.apellido;

-- Padrón de jugadores inhabilitados para una fecha específica
SELECT
    e.nombre AS equipo,
    j.ci,
    j.nombre,
    j.apellido,
    s.motivo,
    s.numero_fecha_inicio,
    (s.numero_fecha_inicio + s.cantidad_fechas - 1) AS fecha_fin_sancion
FROM sancion_jugador s
JOIN equipo_jugador_torneo ejt ON s.ci_jugador = ejt.ci_jugador AND s.id_torneo = ejt.id_torneo
JOIN equipo e ON ejt.id_equipo = e.id_equipo
JOIN jugador j ON s.ci_jugador = j.ci
WHERE s.id_torneo = 1
  AND 2 BETWEEN s.numero_fecha_inicio AND (s.numero_fecha_inicio + s.cantidad_fechas - 1)
ORDER BY e.nombre, j.apellido;

-- Premio a la "Valla Menos Vencida" por edición
SELECT
    e.id_equipo,
    e.nombre AS equipo,
    COUNT(vr.id_partido) AS pj,
    COALESCE(SUM(CASE
        WHEN vr.id_equipo_local = e.id_equipo THEN vr.goles_visitante
        WHEN vr.id_equipo_visitante = e.id_equipo THEN vr.goles_local
        ELSE 0
    END), 0) AS goles_recibidos,
    SUM(CASE
        WHEN (vr.id_equipo_local = e.id_equipo AND vr.goles_visitante = 0) OR
             (vr.id_equipo_visitante = e.id_equipo AND vr.goles_local = 0)
        THEN 1 ELSE 0
    END) AS vallas_invictas,
    ROUND(COALESCE(AVG(CASE
        WHEN vr.id_equipo_local = e.id_equipo THEN vr.goles_visitante
        WHEN vr.id_equipo_visitante = e.id_equipo THEN vr.goles_local
        ELSE NULL
    END), 0), 2) AS prom_gc
FROM equipo e
JOIN v_resultado_partido vr ON e.id_equipo = vr.id_equipo_local OR e.id_equipo = vr.id_equipo_visitante
WHERE e.id_torneo = 1 AND vr.estado = 'jugado'
GROUP BY e.id_equipo, e.nombre
ORDER BY prom_gc ASC, vallas_invictas DESC, goles_recibidos ASC;