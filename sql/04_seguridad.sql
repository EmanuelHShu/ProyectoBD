-- =========================================================================
-- SEGURIDAD Y ROLES DE BASE DE DATOS
-- =========================================================================

USE torneo_futbol5;

-- 1. CREACIÓN DE ROLES
DROP ROLE IF EXISTS rol_administrador;
DROP ROLE IF EXISTS rol_planillero;
DROP ROLE IF EXISTS rol_login;
CREATE ROLE rol_administrador;
CREATE ROLE rol_planillero;
CREATE ROLE rol_login;

-- 2. ASIGNACIÓN DE PRIVILEGIOS AL ROL ADMINISTRADOR
-- El administrador tiene control total sobre todas las tablas y esquemas
GRANT ALL PRIVILEGES ON torneo_futbol5.* TO rol_administrador;

-- 3. ASIGNACIÓN DE PRIVILEGIOS AL ROL PLANILLERO
-- Lectura de las tablas necesarias para consultar fixtures y planteles.
-- Se excluye la tabla login (correos y contrasenas) a proposito.
-- IMPORTANTE: ejecutar este script DESPUES de triggers-automaticos.sql (la vista debe existir).
GRANT SELECT ON torneo_futbol5.facultad TO rol_planillero;
GRANT SELECT ON torneo_futbol5.jugador TO rol_planillero;
GRANT SELECT ON torneo_futbol5.torneo TO rol_planillero;
GRANT SELECT ON torneo_futbol5.equipo TO rol_planillero;
GRANT SELECT ON torneo_futbol5.equipo_jugador_torneo TO rol_planillero;
GRANT SELECT ON torneo_futbol5.complejo TO rol_planillero;
GRANT SELECT ON torneo_futbol5.cancha TO rol_planillero;
GRANT SELECT ON torneo_futbol5.turno TO rol_planillero;
GRANT SELECT ON torneo_futbol5.partido TO rol_planillero;
GRANT SELECT ON torneo_futbol5.planilla_partido TO rol_planillero;
GRANT SELECT ON torneo_futbol5.gol TO rol_planillero;
GRANT SELECT ON torneo_futbol5.tarjeta TO rol_planillero;
GRANT SELECT ON torneo_futbol5.sancion_jugador TO rol_planillero;
GRANT SELECT ON torneo_futbol5.v_resultado_partido TO rol_planillero;

-- Escritura restringida exclusivamente a planillas, goles y tarjetas
GRANT INSERT, UPDATE, DELETE ON torneo_futbol5.planilla_partido TO rol_planillero;
GRANT INSERT, UPDATE, DELETE ON torneo_futbol5.gol TO rol_planillero;
GRANT INSERT, UPDATE, DELETE ON torneo_futbol5.tarjeta TO rol_planillero;

-- El planillero NO tiene UPDATE sobre partido: marca un partido como jugado
-- unicamente mediante el procedimiento sp_marcar_partido_jugado (SQL SECURITY DEFINER).
GRANT EXECUTE ON PROCEDURE torneo_futbol5.sp_marcar_partido_jugado TO rol_planillero;

-- 3.b ROL DE AUTENTICACION DE LA APLICACION
-- La app necesita leer la tabla login para validar credenciales y conocer el rol
-- antes de conectarse como administrador o planillero. Este rol solo lee login.
GRANT SELECT ON torneo_futbol5.login TO rol_login;

-- Nota: Las sanciones automáticas por tarjetas se ejecutan mediante el trigger
-- con contexto DEFINER, evitando que el planillero requiera permisos de escritura
-- directos sobre la tabla sancion_jugador.

-- 4. CREACIÓN DE USUARIOS DE PRUEBA Y ASIGNACIÓN DE ROLES
CREATE USER IF NOT EXISTS 'admin_user'@'localhost' IDENTIFIED BY 'AdminPass2026*';
CREATE USER IF NOT EXISTS 'planillero_user'@'localhost' IDENTIFIED BY 'PlanilleroPass2026*';

CREATE USER IF NOT EXISTS 'login_user'@'localhost' IDENTIFIED BY 'LoginPass2026*';

GRANT rol_administrador TO 'admin_user'@'localhost';
GRANT rol_login TO 'login_user'@'localhost';
GRANT rol_planillero TO 'planillero_user'@'localhost';

-- Establecer roles predeterminados al iniciar sesión
SET DEFAULT ROLE rol_administrador TO 'admin_user'@'localhost';
SET DEFAULT ROLE rol_planillero TO 'planillero_user'@'localhost';
SET DEFAULT ROLE rol_login TO 'login_user'@'localhost';

FLUSH PRIVILEGES;