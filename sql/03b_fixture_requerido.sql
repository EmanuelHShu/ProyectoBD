-- COMPLEMENTO MINIMO DEL FIXTURE, SIN MODIFICAR EL SQL DE SEBA Y SABRINA.
-- La consigna exige una liga a una sola rueda: con seis equipos son 15 cruces.
-- Los datos originales tenían 13 (incluido 1-6 cancelado).
-- Se agregan los cruces 2-3 y 4-5 sin cambiar los ya definidos.
USE torneo_futbol5;

INSERT INTO partido (id_partido, id_torneo, numero_fecha, id_equipo_local,
                     id_equipo_visitante, dia, id_turno, nombre_cancha,
                     id_complejo, estado)
VALUES
    (14, 1, 5, 2, 3, '2026-11-16', 2, 'Cancha 1', 1, 'programado'),
    (15, 1, 5, 4, 5, '2026-11-16', 3, 'Cancha 1', 1, 'programado');
