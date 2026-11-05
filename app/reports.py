"""Reportes parametrizados. Todas las consultas usan placeholders nativos de PyMySQL."""
from collections import OrderedDict

REPORTS = OrderedDict([
("posiciones", ("Tabla de posiciones", "Puntos (3-1-0), diferencia de goles y goles a favor.", """
 SELECT e.nombre AS equipo, COUNT(v.id_partido) AS PJ,
 COALESCE(SUM(CASE WHEN (e.id_equipo=v.id_equipo_local AND v.goles_local>v.goles_visitante) OR
 (e.id_equipo=v.id_equipo_visitante AND v.goles_visitante>v.goles_local) THEN 1 ELSE 0 END),0) AS PG,
 COALESCE(SUM(CASE WHEN v.id_partido IS NOT NULL AND v.goles_local=v.goles_visitante THEN 1 ELSE 0 END),0) AS PE,
 COALESCE(SUM(CASE WHEN (e.id_equipo=v.id_equipo_local AND v.goles_local<v.goles_visitante) OR
 (e.id_equipo=v.id_equipo_visitante AND v.goles_visitante<v.goles_local) THEN 1 ELSE 0 END),0) AS PP,
 COALESCE(SUM(CASE WHEN e.id_equipo=v.id_equipo_local THEN v.goles_local ELSE v.goles_visitante END),0) AS GF,
 COALESCE(SUM(CASE WHEN e.id_equipo=v.id_equipo_local THEN v.goles_visitante ELSE v.goles_local END),0) AS GC,
 COALESCE(SUM(CASE WHEN e.id_equipo=v.id_equipo_local THEN v.goles_local-v.goles_visitante
 ELSE v.goles_visitante-v.goles_local END),0) AS DG,
 COALESCE(SUM(CASE WHEN (e.id_equipo=v.id_equipo_local AND v.goles_local>v.goles_visitante) OR
 (e.id_equipo=v.id_equipo_visitante AND v.goles_visitante>v.goles_local) THEN 3
 WHEN v.id_partido IS NOT NULL AND v.goles_local=v.goles_visitante THEN 1 ELSE 0 END),0) AS puntos
 FROM equipo e LEFT JOIN v_resultado_partido v
 ON (v.id_equipo_local=e.id_equipo OR v.id_equipo_visitante=e.id_equipo) AND v.estado='jugado'
 WHERE e.id_torneo=%(torneo)s GROUP BY e.id_equipo,e.nombre ORDER BY puntos DESC,DG DESC,GF DESC,e.nombre
""")),
("goleadores", ("Top 10 goleadores", "No se cuentan los autogoles.", """
 SELECT j.ci, CONCAT(j.nombre,' ',j.apellido) AS jugador, e.nombre AS equipo,
 COUNT(*) AS goles FROM gol g JOIN partido p ON p.id_partido=g.id_partido
 JOIN planilla_partido pa ON pa.id_partido=g.id_partido AND pa.ci_jugador=g.ci_jugador
 JOIN jugador j ON j.ci=g.ci_jugador JOIN equipo e ON e.id_equipo=pa.id_equipo
 WHERE p.id_torneo=%(torneo)s AND p.estado='jugado' AND g.autogol=0
 GROUP BY j.ci,j.nombre,j.apellido,e.nombre ORDER BY goles DESC,j.apellido LIMIT 10
""")),
("fairplay", ("Fair play", "Amarilla: 1 punto; roja: 3. Menos puntos es mejor.", """
 SELECT e.nombre AS equipo,
 COUNT(CASE WHEN ta.color='amarilla' THEN 1 END) AS amarillas,
 COUNT(CASE WHEN ta.color='roja' THEN 1 END) AS rojas,
 SUM(CASE WHEN ta.color='amarilla' THEN 1 WHEN ta.color='roja' THEN 3 ELSE 0 END) AS puntaje
 FROM equipo e LEFT JOIN planilla_partido pl ON pl.id_equipo=e.id_equipo
 LEFT JOIN partido p ON p.id_partido=pl.id_partido AND p.estado='jugado' AND p.id_torneo=e.id_torneo
 LEFT JOIN tarjeta ta ON ta.id_partido=p.id_partido AND ta.ci_jugador=pl.ci_jugador
 WHERE e.id_torneo=%(torneo)s GROUP BY e.id_equipo,e.nombre ORDER BY puntaje ASC,e.nombre
""")),
("goles_fecha", ("Promedio de goles por fecha", "Solo partidos jugados.", """
 SELECT p.numero_fecha AS fecha, COUNT(DISTINCT p.id_partido) AS partidos,
 COUNT(g.id_gol) AS goles,
 ROUND(COUNT(g.id_gol)/NULLIF(COUNT(DISTINCT p.id_partido),0),2) AS promedio
 FROM partido p LEFT JOIN gol g ON g.id_partido=p.id_partido
 WHERE p.id_torneo=%(torneo)s AND p.estado='jugado'
 GROUP BY p.numero_fecha ORDER BY p.numero_fecha
""")),
("goles_global", ("Promedio de goles por edición", "Solo partidos jugados.", """
 SELECT COUNT(DISTINCT p.id_partido) AS partidos, COUNT(g.id_gol) AS goles,
 COALESCE(ROUND(COUNT(g.id_gol)/NULLIF(COUNT(DISTINCT p.id_partido),0),2),0) AS promedio
 FROM partido p LEFT JOIN gol g ON g.id_partido=p.id_partido
 WHERE p.id_torneo=%(torneo)s AND p.estado='jugado'
""")),
("canchas", ("Canchas más utilizadas", "Cantidad de partidos jugados por cancha.", """
 SELECT co.nombre AS complejo,c.nombre_cancha AS cancha,COUNT(p.id_partido) AS partidos
 FROM cancha c JOIN complejo co ON co.id_complejo=c.id_complejo
 LEFT JOIN partido p ON p.id_complejo=c.id_complejo AND p.nombre_cancha=c.nombre_cancha
 AND p.id_torneo=%(torneo)s AND p.estado='jugado'
 GROUP BY co.id_complejo,co.nombre,c.nombre_cancha ORDER BY partidos DESC,complejo,cancha
""")),
("turnos", ("Turnos más utilizados", "Cantidad de partidos jugados por turno.", """
 SELECT t.hora_inicio AS inicio,t.hora_fin AS fin,COUNT(p.id_partido) AS partidos
 FROM turno t LEFT JOIN partido p ON p.id_turno=t.id_turno AND p.id_torneo=%(torneo)s AND p.estado='jugado'
 GROUP BY t.id_turno,t.hora_inicio,t.hora_fin ORDER BY partidos DESC,inicio
""")),
("facultades", ("Jugadores por facultad y tipo", "Conteo global de jugadores registrados (no por edición).", """
 SELECT f.nombre AS facultad,j.tipo,COUNT(*) AS jugadores
 FROM jugador j JOIN facultad f ON f.id_facultad=j.id_facultad
 GROUP BY f.id_facultad,f.nombre,j.tipo ORDER BY facultad,j.tipo
""")),
("sin_planilla", ("Inscriptos que nunca jugaron", "Jugadores del plantel de la edición sin ninguna planilla.", """
 SELECT e.nombre AS equipo,j.ci,CONCAT(j.nombre,' ',j.apellido) AS jugador,j.tipo
 FROM equipo_jugador_torneo ej JOIN jugador j ON j.ci=ej.ci_jugador
 JOIN equipo e ON e.id_equipo=ej.id_equipo WHERE ej.id_torneo=%(torneo)s
 AND NOT EXISTS (SELECT 1 FROM planilla_partido pl JOIN partido p ON pl.id_partido=p.id_partido
 WHERE pl.ci_jugador=ej.ci_jugador AND pl.id_equipo=ej.id_equipo AND p.id_torneo=ej.id_torneo)
 ORDER BY equipo,jugador
""")),
("sanciones", ("Sanciones por equipo y motivo", "Incluye sanciones automáticas y disciplinarias.", """
 SELECT e.nombre AS equipo,s.motivo,COUNT(*) AS cantidad
 FROM sancion_jugador s JOIN equipo_jugador_torneo ej ON ej.ci_jugador=s.ci_jugador AND ej.id_torneo=s.id_torneo
 JOIN equipo e ON e.id_equipo=ej.id_equipo WHERE s.id_torneo=%(torneo)s
 GROUP BY e.id_equipo,e.nombre,s.motivo ORDER BY equipo,cantidad DESC
""")),
("estados", ("Jugados vs. postergados/cancelados", "También se muestran los programados para completar el 100%.", """
 SELECT COUNT(*) AS total,
 COALESCE(SUM(estado='jugado'),0) AS jugados,
 COALESCE(SUM(estado='postergado'),0) AS postergados,
 COALESCE(SUM(estado='cancelado'),0) AS cancelados,
 COALESCE(SUM(estado='programado'),0) AS programados,
 COALESCE(ROUND(100*SUM(estado='jugado')/NULLIF(COUNT(*),0),2),0) AS porcentaje_jugados,
 COALESCE(ROUND(100*SUM(estado IN ('postergado','cancelado'))/NULLIF(COUNT(*),0),2),0) AS porcentaje_post_canc
 FROM partido WHERE id_torneo=%(torneo)s
""")),
("asistencia", ("Asistencia perfecta", "Extra 1: jugadores que participaron en todos los partidos jugados por su equipo.", """
 SELECT j.ci,CONCAT(j.nombre,' ',j.apellido) AS jugador,e.nombre AS equipo
 FROM equipo_jugador_torneo ej JOIN jugador j ON j.ci=ej.ci_jugador
 JOIN equipo e ON e.id_equipo=ej.id_equipo WHERE ej.id_torneo=%(torneo)s
 AND EXISTS (SELECT 1 FROM partido p WHERE p.estado='jugado' AND p.id_torneo=ej.id_torneo
 AND ej.id_equipo IN (p.id_equipo_local,p.id_equipo_visitante))
 AND NOT EXISTS (SELECT 1 FROM partido p WHERE p.estado='jugado' AND p.id_torneo=ej.id_torneo
 AND ej.id_equipo IN (p.id_equipo_local,p.id_equipo_visitante)
 AND NOT EXISTS (SELECT 1 FROM planilla_partido pl WHERE pl.id_partido=p.id_partido AND pl.ci_jugador=j.ci))
 ORDER BY equipo,jugador
""")),
("inhabilitados", ("Inhabilitados para una fecha", "Extra 2: utiliza el número de fecha indicado.", """
 SELECT e.nombre AS equipo,CONCAT(j.nombre,' ',j.apellido) AS jugador,s.motivo,
 s.numero_fecha_inicio AS desde,s.numero_fecha_inicio+s.cantidad_fechas-1 AS hasta
 FROM sancion_jugador s JOIN jugador j ON j.ci=s.ci_jugador
 JOIN equipo_jugador_torneo ej ON ej.ci_jugador=s.ci_jugador AND ej.id_torneo=s.id_torneo
 JOIN equipo e ON e.id_equipo=ej.id_equipo
 WHERE s.id_torneo=%(torneo)s AND %(fecha)s BETWEEN s.numero_fecha_inicio
 AND s.numero_fecha_inicio+s.cantidad_fechas-1 ORDER BY equipo,jugador
""")),
("valla", ("Valla menos vencida", "Extra 3: mejores promedios de goles recibidos por partido jugado.", """
 SELECT e.nombre AS equipo,COUNT(v.id_partido) AS PJ,
 COALESCE(SUM(CASE WHEN v.id_equipo_local=e.id_equipo THEN v.goles_visitante
 WHEN v.id_equipo_visitante=e.id_equipo THEN v.goles_local ELSE 0 END),0) AS GC,
 COALESCE(SUM(CASE WHEN (v.id_equipo_local=e.id_equipo AND v.goles_visitante=0)
 OR (v.id_equipo_visitante=e.id_equipo AND v.goles_local=0) THEN 1 ELSE 0 END),0) AS vallas_invictas,
 COALESCE(ROUND(AVG(CASE WHEN v.id_equipo_local=e.id_equipo THEN v.goles_visitante
 WHEN v.id_equipo_visitante=e.id_equipo THEN v.goles_local END),2),0) AS promedio_gc
 FROM equipo e LEFT JOIN v_resultado_partido v ON v.estado='jugado' AND
 (v.id_equipo_local=e.id_equipo OR v.id_equipo_visitante=e.id_equipo)
 WHERE e.id_torneo=%(torneo)s GROUP BY e.id_equipo,e.nombre ORDER BY promedio_gc ASC,vallas_invictas DESC,GC
""")),
])
