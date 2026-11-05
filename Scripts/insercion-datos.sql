-- =========================================================================
-- INSERCION DE DATOS
-- =========================================================================

USE torneo_futbol5;

-- 1. LOGIN
INSERT INTO login (correo, contrasena, rol) VALUES
('admin@ucu.edu.uy', 'pass123', 'administrador'),
('planillero@ucu.edu.uy', 'pass123', 'planillero');

-- 2. FACULTAD (6 facultades para los 6 equipos minimos)
INSERT INTO facultad (id_facultad, nombre) VALUES
(1, 'Ingenieria'),
(2, 'Administracion'),
(3, 'Derecho'),
(4, 'Medicina'),
(5, 'Arquitectura'),
(6, 'Psicologia');

-- 3. JUGADOR (Cargamos jugadores suficientes para planteles de 5 a 10 integrantes)
-- Facultad 1 (Ingenieria)
INSERT INTO jugador (ci, nombre, apellido, email, fecha_nacimiento, id_facultad, tipo) VALUES
('11111111', 'Juan', 'Perez', 'juan.perez@correo.com', '2000-05-12', 1, 'grado'),
('11111112', 'Carlos', 'Gomez', 'carlos.gomez@correo.com', '1999-03-15', 1, 'grado'),
('11111113', 'Mateo', 'Silva', 'mateo.silva@correo.com', '2001-07-20', 1, 'grado'),
('11111114', 'Lucas', 'Rodriguez', 'lucas.rodriguez@correo.com', '2000-11-05', 1, 'grado'),
('11111115', 'Martin', 'Lopez', 'martin.lopez@correo.com', '1998-01-10', 1, 'grado'),
('11111116', 'Ana', 'Fernandez', 'ana.fernandez@correo.com', '1985-09-25', 1, 'docente');

-- Facultad 2 (Administracion)
INSERT INTO jugador (ci, nombre, apellido, email, fecha_nacimiento, id_facultad, tipo) VALUES
('22222221', 'Sofia', 'Martinez', 'sofia.martinez@correo.com', '2000-02-14', 2, 'grado'),
('22222222', 'Lucia', 'Suarez', 'lucia.suarez@correo.com', '1999-06-18', 2, 'grado'),
('22222223', 'Valeria', 'Benitez', 'valeria.benitez@correo.com', '2001-09-10', 2, 'grado'),
('22222224', 'Joaquin', 'Acosta', 'joaquin.acosta@correo.com', '2000-12-01', 2, 'grado'),
('22222225', 'Diego', 'Rios', 'diego.rios@correo.com', '1997-04-22', 2, 'posgrado');

-- Facultad 3 (Derecho)
INSERT INTO jugador (ci, nombre, apellido, email, fecha_nacimiento, id_facultad, tipo) VALUES
('33333331', 'Camila', 'Sosa', 'camila.sosa@correo.com', '2000-08-30', 3, 'grado'),
('33333332', 'Agustin', 'Peralta', 'agustin.peralta@correo.com', '1999-10-12', 3, 'grado'),
('33333333', 'Federico', 'Mendoza', 'federico.mendoza@correo.com', '2001-01-05', 3, 'grado'),
('33333334', 'Valentina', 'Castro', 'valentina.castro@correo.com', '2000-03-19', 3, 'grado'),
('33333335', 'Ignacio', 'Viera', 'ignacio.viera@correo.com', '1996-07-11', 3, 'docente');

-- Facultad 4 (Medicina)
INSERT INTO jugador (ci, nombre, apellido, email, fecha_nacimiento, id_facultad, tipo) VALUES
('44444441', 'Mariana', 'Medina', 'mariana.medina@correo.com', '2000-04-04', 4, 'grado'),
('44444442', 'Nicolas', 'Blanco', 'nicolas.blanco@correo.com', '1999-05-21', 4, 'grado'),
('44444443', 'Gonzalo', 'Rivas', 'gonzalo.rivas@correo.com', '2001-02-17', 4, 'grado'),
('44444444', 'Florencia', 'Cabral', 'florencia.cabral@correo.com', '2000-09-09', 4, 'grado'),
('44444445', 'Bruno', 'Ferreira', 'bruno.ferreira@correo.com', '1995-12-30', 4, 'funcionario');

-- Facultad 5 (Arquitectura)
INSERT INTO jugador (ci, nombre, apellido, email, fecha_nacimiento, id_facultad, tipo) VALUES
('55555551', 'Victoria', 'Ponce', 'victoria.ponce@correo.com', '2000-01-11', 5, 'grado'),
('55555552', 'Santiago', 'Juarez', 'santiago.juarez@correo.com', '1999-07-08', 5, 'grado'),
('55555553', 'Facundo', 'Vazquez', 'facundo.vazquez@correo.com', '2001-06-25', 5, 'grado'),
('55555554', 'Julieta', 'Herrera', 'julieta.herrera@correo.com', '2000-10-14', 5, 'grado'),
('55555555', 'Matias', 'Gimenez', 'matias.gimenez@correo.com', '1998-08-19', 5, 'grado');

-- Facultad 6 (Psicologia)
INSERT INTO jugador (ci, nombre, apellido, email, fecha_nacimiento, id_facultad, tipo) VALUES
('66666661', 'Catalina', 'Pintos', 'catalina.pintos@correo.com', '2000-03-27', 6, 'grado'),
('66666662', 'Emiliano', 'Cardozo', 'emiliano.cardozo@correo.com', '1999-09-03', 6, 'grado'),
('66666663', 'Paula', 'Machado', 'paula.machado@correo.com', '2001-04-12', 6, 'grado'),
('66666664', 'Tomas', 'Pereira', 'tomas.pereira@correo.com', '2000-11-28', 6, 'grado'),
('66666665', 'Rocio', 'Lima', 'rocio.lima@correo.com', '1997-02-05', 6, 'posgrado');

-- 4. TORNEO (Edicion 2026-2 en curso)
INSERT INTO torneo (id_torneo, nombre, anio, semestre, fecha_inicio, fecha_fin, estado) VALUES
(1, 'Torneo Interfacultades 2026-2', 2026, 2, '2026-08-01', '2026-11-30', 'en curso');

-- 5. COMPLEJO
INSERT INTO complejo (id_complejo, nombre, direccion, departamento) VALUES
(1, 'Complejo Deportivo Central', 'Av. Italia 2500', 'Montevideo');

-- 6. CANCHA
INSERT INTO cancha (nombre_cancha, id_complejo, superficie, techada) VALUES
('Cancha 1', 1, 'sintético', true),
('Cancha 2', 1, 'sintético', false);

-- 7. TURNO
INSERT INTO turno (id_turno, hora_inicio, hora_fin) VALUES
(1, '18:00:00', '19:00:00'),
(2, '19:00:00', '20:00:00'),
(3, '20:00:00', '21:00:00');

-- 8. EQUIPO (6 equipos, uno por facultad)
INSERT INTO equipo (id_equipo, nombre, id_torneo, id_facultad, ci_capitan) VALUES
(1, 'Ingenieria FC', 1, 1, '11111111'),
(2, 'Administracion United', 1, 2, '22222221'),
(3, 'Derecho Athletic', 1, 3, '33333331'),
(4, 'Medicina Juniors', 1, 4, '44444441'),
(5, 'Arquitectura City', 1, 5, '55555551'),
(6, 'Psicologia Sporting', 1, 6, '66666661');

-- 9. PLANTELES (Planteles de 5 jugadores cada uno)

-- Ingenieria FC (Equipo 1)
INSERT INTO equipo_jugador_torneo (id_equipo, ci_jugador, id_torneo, numero_camiseta) VALUES
(1, '11111111', 1, 10),
(1, '11111112', 1, 5),
(1, '11111113', 1, 7),
(1, '11111114', 1, 8),
(1, '11111115', 1, 9);

-- Administracion United (Equipo 2)
INSERT INTO equipo_jugador_torneo (id_equipo, ci_jugador, id_torneo, numero_camiseta) VALUES
(2, '22222221', 1, 10),
(2, '22222222', 1, 2),
(2, '22222223', 1, 3),
(2, '22222224', 1, 4),
(2, '22222225', 1, 11);

-- Derecho Athletic (Equipo 3)
INSERT INTO equipo_jugador_torneo (id_equipo, ci_jugador, id_torneo, numero_camiseta) VALUES
(3, '33333331', 1, 10),
(3, '33333332', 1, 4),
(3, '33333333', 1, 6),
(3, '33333334', 1, 7),
(3, '33333335', 1, 9);

-- Medicina Juniors (Equipo 4)
INSERT INTO equipo_jugador_torneo (id_equipo, ci_jugador, id_torneo, numero_camiseta) VALUES
(4, '44444441', 1, 10),
(4, '44444442', 1, 2),
(4, '44444443', 1, 5),
(4, '44444444', 1, 8),
(4, '44444445', 1, 12);

-- Arquitectura City (Equipo 5)
INSERT INTO equipo_jugador_torneo (id_equipo, ci_jugador, id_torneo, numero_camiseta) VALUES
(5, '55555551', 1, 10),
(5, '55555552', 1, 3),
(5, '55555553', 1, 6),
(5, '55555554', 1, 7),
(5, '55555555', 1, 9);

-- Psicologia Sporting (Equipo 6)
INSERT INTO equipo_jugador_torneo (id_equipo, ci_jugador, id_torneo, numero_camiseta) VALUES
(6, '66666661', 1, 10),
(6, '66666662', 1, 2),
(6, '66666663', 1, 4),
(6, '66666664', 1, 5),
(6, '66666665', 1, 8);

-- 10. PARTIDO (Al menos 3 fechas disputadas con estado jugado)

-- Fecha 1
INSERT INTO partido (id_partido, id_torneo, numero_fecha, id_equipo_local, id_equipo_visitante, dia, id_turno, nombre_cancha, id_complejo, estado) VALUES
(1, 1, 1, 1, 2, '2026-08-10', 1, 'Cancha 1', 1, 'jugado'),
(2, 1, 1, 3, 4, '2026-08-10', 2, 'Cancha 1', 1, 'jugado'),
(3, 1, 1, 5, 6, '2026-08-10', 3, 'Cancha 1', 1, 'jugado');

-- Fecha 2
INSERT INTO partido (id_partido, id_torneo, numero_fecha, id_equipo_local, id_equipo_visitante, dia, id_turno, nombre_cancha, id_complejo, estado) VALUES
(4, 1, 2, 1, 3, '2026-08-17', 1, 'Cancha 1', 1, 'jugado'),
(5, 1, 2, 2, 5, '2026-08-17', 2, 'Cancha 1', 1, 'jugado'),
(6, 1, 2, 4, 6, '2026-08-17', 3, 'Cancha 1', 1, 'jugado');

-- Fecha 3
INSERT INTO partido (id_partido, id_torneo, numero_fecha, id_equipo_local, id_equipo_visitante, dia, id_turno, nombre_cancha, id_complejo, estado) VALUES
(7, 1, 3, 1, 4, '2026-08-24', 1, 'Cancha 1', 1, 'jugado'),
(8, 1, 3, 2, 6, '2026-08-24', 2, 'Cancha 1', 1, 'jugado'),
(9, 1, 3, 3, 5, '2026-08-24', 3, 'Cancha 1', 1, 'jugado');

-- 11. PLANILLA_PARTIDO (Jugadores que firman planilla en los partidos)

-- Partido 1
INSERT INTO planilla_partido (id_partido, ci_jugador, id_equipo) VALUES
(1, '11111111', 1), (1, '11111112', 1), (1, '11111113', 1),
(1, '22222221', 2), (1, '22222222', 2), (1, '22222223', 2);

-- Partido 2
INSERT INTO planilla_partido (id_partido, ci_jugador, id_equipo) VALUES
(2, '33333331', 3), (2, '33333332', 3), (2, '33333333', 3),
(2, '44444441', 4), (2, '44444442', 4), (2, '44444443', 4);

-- Partido 3
INSERT INTO planilla_partido (id_partido, ci_jugador, id_equipo) VALUES
(3, '55555551', 5), (3, '55555552', 5), (3, '55555553', 5),
(3, '66666661', 6), (3, '66666662', 6), (3, '66666663', 6);

-- Partido 4
INSERT INTO planilla_partido (id_partido, ci_jugador, id_equipo) VALUES
(4, '11111111', 1), (4, '11111112', 1), (4, '11111114', 1),
(4, '33333331', 3), (4, '33333332', 3), (4, '33333334', 3);

-- Partido 5
INSERT INTO planilla_partido (id_partido, ci_jugador, id_equipo) VALUES
(5, '22222221', 2), (5, '22222222', 2), (5, '22222224', 2),
(5, '55555551', 5), (5, '55555552', 5), (5, '55555554', 5);

-- Partido 6
INSERT INTO planilla_partido (id_partido, ci_jugador, id_equipo) VALUES
(6, '44444441', 4), (6, '44444442', 4), (6, '44444444', 4),
(6, '66666661', 6), (6, '66666662', 6), (6, '66666664', 6);

-- Partido 7
INSERT INTO planilla_partido (id_partido, ci_jugador, id_equipo) VALUES
(7, '11111111', 1), (7, '11111113', 1), (7, '11111115', 1),
(7, '44444441', 4), (7, '44444443', 4), (7, '44444445', 4);

-- Partido 8
INSERT INTO planilla_partido (id_partido, ci_jugador, id_equipo) VALUES
(8, '22222221', 2), (8, '22222223', 2), (8, '22222225', 2),
(8, '66666661', 6), (8, '66666663', 6), (8, '66666665', 6);

-- Partido 9
INSERT INTO planilla_partido (id_partido, ci_jugador, id_equipo) VALUES
(9, '33333331', 3), (9, '33333333', 3), (9, '33333335', 3),
(9, '55555551', 5), (9, '55555553', 5), (9, '55555555', 5);

-- 12. GOL (Goles convertidos)
INSERT INTO gol (id_partido, ci_jugador, minuto, autogol) VALUES
(1, '11111111', 12, false),
(1, '11111112', 25, false),
(1, '22222221', 40, false),
(2, '33333331', 10, false),
(3, '55555551', 15, false),
(3, '55555552', 30, false),
(4, '11111111', 20, false),
(5, '22222221', 18, false),
(6, '44444441', 22, false),
(7, '11111111', 5, false),
(8, '22222221', 14, false),
(9, '33333331', 33, false);

-- 13. TARJETA (Tarjetas amarillas y rojas)
INSERT INTO tarjeta (id_partido, ci_jugador, minuto, color) VALUES
(1, '11111111', 35, 'amarilla'),
(2, '33333332', 45, 'amarilla'),
(3, '66666661', 50, 'roja'),
(4, '33333331', 15, 'amarilla');

-- 14. SANCION_JUGADOR (Sanciones registradas)
INSERT INTO sancion_jugador (ci_jugador, id_torneo, motivo, numero_fecha_inicio, cantidad_fechas) VALUES
('66666662', 1, 'disciplinaria', 2, 2);