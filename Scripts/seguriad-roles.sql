-- =========================================================================
-- SEGURIDAD Y ROLES DE BASE DE DATOS
-- =========================================================================

USE torneo_futbol5;

-- 1. CREACIÓN DE ROLES
DROP ROLE rol_administrador;
DROP ROLE rol_planillero;
CREATE ROLE rol_administrador;
CREATE ROLE rol_planillero;

-- 2. ASIGNACIÓN DE PRIVILEGIOS AL ROL ADMINISTRADOR
-- El administrador tiene control total sobre todas las tablas y esquemas
GRANT ALL PRIVILEGES ON torneo_futbol5.* TO rol_administrador;

-- 3. ASIGNACIÓN DE PRIVILEGIOS AL ROL PLANILLERO
-- Lectura general de todo el sistema para poder consultar fixtures y planteles
GRANT SELECT ON torneo_futbol5.* TO rol_planillero;

-- Escritura restringida exclusivamente a planillas, goles y tarjetas
GRANT INSERT, UPDATE, DELETE ON torneo_futbol5.planilla_partido TO rol_planillero;
GRANT INSERT, UPDATE, DELETE ON torneo_futbol5.gol TO rol_planillero;
GRANT INSERT, UPDATE, DELETE ON torneo_futbol5.tarjeta TO rol_planillero;

-- Permiso a nivel de columna para actualizar únicamente el estado del partido
GRANT UPDATE (estado) ON torneo_futbol5.partido TO rol_planillero;

-- Nota: Las sanciones automáticas por tarjetas se ejecutan mediante el trigger
-- con contexto DEFINER, evitando que el planillero requiera permisos de escritura
-- directos sobre la tabla sancion_jugador.

-- 4. CREACIÓN DE USUARIOS DE PRUEBA Y ASIGNACIÓN DE ROLES
CREATE USER IF NOT EXISTS 'admin_user'@'localhost' IDENTIFIED BY 'AdminPass2026*';
CREATE USER IF NOT EXISTS 'planillero_user'@'localhost' IDENTIFIED BY 'PlanilleroPass2026*';

GRANT rol_administrador TO 'admin_user'@'localhost';
GRANT rol_planillero TO 'planillero_user'@'localhost';

-- Establecer roles predeterminados al iniciar sesión
SET DEFAULT ROLE rol_administrador TO 'admin_user'@'localhost';
SET DEFAULT ROLE rol_planillero TO 'planillero_user'@'localhost';

FLUSH PRIVILEGES;