-- =========================================================================
-- CRAEACION DE TABLAS
-- =========================================================================
DROP DATABASE IF EXISTS torneo_futbol5;
CREATE DATABASE IF NOT EXISTS torneo_futbol5;

USE torneo_futbol5;

-- 1. LOGIN

CREATE TABLE login (
    correo VARCHAR(255) NOT NULL,
    contrasena VARCHAR(255) NOT NULL,
    rol ENUM('administrador', 'planillero') NOT NULL,
    PRIMARY KEY (correo)
);

-- 2. FACULTAD
CREATE TABLE facultad (
    id_facultad INT AUTO_INCREMENT NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    PRIMARY KEY (id_facultad),
    CONSTRAINT uk_facultad_nombre UNIQUE (nombre)
);

-- 3. JUGADOR
CREATE TABLE jugador (
    ci VARCHAR(20) NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    apellido VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL,
    fecha_nacimiento DATE NOT NULL,
    id_facultad INT NOT NULL,
    tipo ENUM('grado', 'posgrado', 'docente', 'funcionario') NOT NULL,
    PRIMARY KEY (ci),
    CONSTRAINT uk_jugador_email UNIQUE (email),
    CONSTRAINT fk_jugador_facultad FOREIGN KEY (id_facultad)
        REFERENCES facultad(id_facultad)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);

-- 4. TORNEO
CREATE TABLE torneo (
    id_torneo INT AUTO_INCREMENT NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    anio SMALLINT NOT NULL,
    semestre TINYINT NOT NULL,
    fecha_inicio DATE NOT NULL,
    fecha_fin DATE NOT NULL,
    estado ENUM('inscripcion', 'en curso', 'finalizado') NOT NULL,
    PRIMARY KEY (id_torneo),
    CONSTRAINT uk_torneo_anio_semestre UNIQUE (anio, semestre),
    CONSTRAINT chk_torneo_semestre CHECK (semestre IN (1, 2)),
    CONSTRAINT chk_torneo_fechas CHECK (fecha_inicio <= fecha_fin)
);

-- 5. EQUIPO
CREATE TABLE equipo (
    id_equipo INT AUTO_INCREMENT NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    id_torneo INT NOT NULL,
    id_facultad INT NOT NULL,
    ci_capitan VARCHAR(20) NOT NULL,
    PRIMARY KEY (id_equipo),
    -- Superclave auxiliar para FK compuesta en partidos y plantel
    CONSTRAINT uk_equipo_id_torneo UNIQUE (id_equipo, id_torneo),
    CONSTRAINT uk_equipo_nombre_torneo UNIQUE (id_torneo, nombre),
    CONSTRAINT uk_equipo_capitan_torneo UNIQUE (id_torneo, ci_capitan),
    CONSTRAINT fk_equipo_torneo FOREIGN KEY (id_torneo)
        REFERENCES torneo(id_torneo)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    CONSTRAINT fk_equipo_facultad FOREIGN KEY (id_facultad)
        REFERENCES facultad(id_facultad)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    CONSTRAINT fk_equipo_capitan FOREIGN KEY (ci_capitan)
        REFERENCES jugador(ci)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);

-- 6. EQUIPO_JUGADOR_TORNEO (PLANTELES)
CREATE TABLE equipo_jugador_torneo (
    id_equipo INT NOT NULL,
    ci_jugador VARCHAR(20) NOT NULL,
    id_torneo INT NOT NULL,
    numero_camiseta TINYINT NOT NULL,
    PRIMARY KEY (id_equipo, ci_jugador, id_torneo),
    -- Garantiza que un jugador no integre mas de un equipo en la misma edicion
    CONSTRAINT uk_ejt_jugador_torneo UNIQUE (ci_jugador, id_torneo),
    -- Evita dorsales duplicados en el mismo plantel
    CONSTRAINT uk_ejt_equipo_camiseta UNIQUE (id_equipo, id_torneo, numero_camiseta),
    CONSTRAINT fk_ejt_equipo_torneo FOREIGN KEY (id_equipo, id_torneo)
        REFERENCES equipo(id_equipo, id_torneo)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    CONSTRAINT fk_ejt_jugador FOREIGN KEY (ci_jugador)
        REFERENCES jugador(ci)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    CONSTRAINT fk_ejt_torneo FOREIGN KEY (id_torneo)
        REFERENCES torneo(id_torneo)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);

-- 7. COMPLEJO
CREATE TABLE complejo (
    id_complejo INT AUTO_INCREMENT NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    direccion VARCHAR(150) NOT NULL,
    departamento VARCHAR(100) NOT NULL,
    PRIMARY KEY (id_complejo),
    CONSTRAINT uk_complejo_nombre UNIQUE (nombre)
);

-- 8. CANCHA (Entidad debil dependiente de complejo)
CREATE TABLE cancha (
    nombre_cancha VARCHAR(100) NOT NULL,
    id_complejo INT NOT NULL,
    superficie ENUM('sintetico', 'parquet') NOT NULL,
    techada BOOLEAN NOT NULL,
    PRIMARY KEY (nombre_cancha, id_complejo),
    CONSTRAINT fk_cancha_complejo FOREIGN KEY (id_complejo)
        REFERENCES complejo(id_complejo)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);

-- 9. TURNO
CREATE TABLE turno (
    id_turno INT AUTO_INCREMENT NOT NULL,
    hora_inicio TIME NOT NULL,
    hora_fin TIME NOT NULL,
    PRIMARY KEY (id_turno),
    CONSTRAINT uk_turno_horas UNIQUE (hora_inicio, hora_fin)
);

-- 10. PARTIDO
CREATE TABLE partido (
    id_partido INT AUTO_INCREMENT NOT NULL,
    id_torneo INT NOT NULL,
    numero_fecha TINYINT NOT NULL,
    id_equipo_local INT NOT NULL,
    id_equipo_visitante INT NOT NULL,
    dia DATE NOT NULL,
    id_turno INT NOT NULL,
    nombre_cancha VARCHAR(100) NOT NULL,
    id_complejo INT NOT NULL,
    estado ENUM('programado', 'jugado', 'postergado', 'cancelado') NOT NULL,
    -- Clave primaria compuesta exigida por la letra
    PRIMARY KEY (id_partido, id_torneo),
    -- Unique auxiliar para permitir referencias foraneas directas desde tablas dependientes
    CONSTRAINT uk_partido_id UNIQUE (id_partido),
    CONSTRAINT chk_partido_equipos CHECK (id_equipo_local <> id_equipo_visitante),
    CONSTRAINT fk_partido_torneo FOREIGN KEY (id_torneo)
        REFERENCES torneo(id_torneo)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    CONSTRAINT fk_partido_local FOREIGN KEY (id_equipo_local, id_torneo)
        REFERENCES equipo(id_equipo, id_torneo)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    CONSTRAINT fk_partido_visitante FOREIGN KEY (id_equipo_visitante, id_torneo)
        REFERENCES equipo(id_equipo, id_torneo)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    CONSTRAINT fk_partido_turno FOREIGN KEY (id_turno)
        REFERENCES turno(id_turno)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    CONSTRAINT fk_partido_cancha FOREIGN KEY (nombre_cancha, id_complejo)
        REFERENCES cancha(nombre_cancha, id_complejo)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);

-- 11. PLANILLA_PARTIDO
CREATE TABLE planilla_partido (
    id_partido INT NOT NULL,
    ci_jugador VARCHAR(20) NOT NULL,
    id_equipo INT NOT NULL,
    PRIMARY KEY (id_partido, ci_jugador),
    CONSTRAINT fk_planilla_partido FOREIGN KEY (id_partido)
        REFERENCES partido(id_partido)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    CONSTRAINT fk_planilla_jugador FOREIGN KEY (ci_jugador)
        REFERENCES jugador(ci)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    CONSTRAINT fk_planilla_equipo FOREIGN KEY (id_equipo)
        REFERENCES equipo(id_equipo)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);

-- 12. GOL
CREATE TABLE gol (
    id_gol INT AUTO_INCREMENT NOT NULL,
    id_partido INT NOT NULL,
    ci_jugador VARCHAR(20) NOT NULL,
    minuto TINYINT NOT NULL,
    autogol BOOLEAN NOT NULL,
    PRIMARY KEY (id_gol),
    -- Integridad referencial compuesta hacia planilla_partido (Decision de Diseño #1)
    CONSTRAINT fk_gol_planilla FOREIGN KEY (id_partido, ci_jugador)
        REFERENCES planilla_partido(id_partido, ci_jugador)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);


-- 13. TARJETA
CREATE TABLE tarjeta (
    id_tarjeta INT AUTO_INCREMENT NOT NULL,
    id_partido INT NOT NULL,
    ci_jugador VARCHAR(20) NOT NULL,
    minuto TINYINT NOT NULL,
    color ENUM('amarilla', 'roja') NOT NULL,
    PRIMARY KEY (id_tarjeta),
    -- Integridad referencial compuesta hacia planilla_partido (Decision de Diseño #1)
    CONSTRAINT fk_tarjeta_planilla FOREIGN KEY (id_partido, ci_jugador)
        REFERENCES planilla_partido(id_partido, ci_jugador)
        ON UPDATE CASCADE
        ON DELETE CASCADE
);

-- 14. SANCION_JUGADOR
CREATE TABLE sancion_jugador (
    id_sancion INT AUTO_INCREMENT NOT NULL,
    ci_jugador VARCHAR(20) NOT NULL,
    id_torneo INT NOT NULL,
    motivo ENUM('roja', 'acumulacion de amarillas', 'disciplinaria') NOT NULL,
    numero_fecha_inicio TINYINT NOT NULL,
    cantidad_fechas TINYINT NOT NULL,
    PRIMARY KEY (id_sancion),
    CONSTRAINT fk_sancion_ejt FOREIGN KEY (ci_jugador, id_torneo)
        REFERENCES equipo_jugador_torneo(ci_jugador, id_torneo)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    CONSTRAINT fk_sancion_jugador FOREIGN KEY (ci_jugador)
        REFERENCES jugador(ci)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    CONSTRAINT fk_sancion_torneo FOREIGN KEY (id_torneo)
        REFERENCES torneo(id_torneo)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);