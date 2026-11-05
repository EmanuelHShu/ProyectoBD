# Plan de pruebas manuales — Versión que conserva SQL de Seba y Sabrina

**Requiere MySQL y la aplicación Flask instalados.** Los casos de abajo no están marcados como realizados.

## 1. Comprobar instalación

Ejecutar los cinco scripts enumerados en `README.md` (solo sobre una base de prueba) y luego, en MySQL:

```sql
USE torneo_futbol5;
SELECT COUNT(*) AS equipos FROM equipo;                      -- 6
SELECT COUNT(*) AS partidos FROM partido;                    -- 15 con el complemento 03b
SELECT COUNT(DISTINCT numero_fecha) AS fechas FROM partido;  -- 5
SELECT COUNT(*) AS jugados FROM partido WHERE estado='jugado'; -- 9
SELECT correo, rol FROM login;  -- administrador y planillero; no mostrar contraseñas en capturas
SHOW GRANTS FOR 'login_user'@'localhost';
SHOW GRANTS FOR 'planillero_user'@'localhost';
SHOW GRANTS FOR 'admin_user'@'localhost';
```

El planillero debe poder editar planillas, goles y tarjetas y ejecutar `sp_marcar_partido_jugado`, pero no modificar equipos, canchas ni partidos por SQL directo.

## 2. Casos funcionales

- [ ] Entrar como `admin@ucu.edu.uy` / `pass123` y consultar Gestión, fixture y reportes.
- [ ] Entrar como `planillero@ucu.edu.uy` / `pass123` y verificar que no entra en Gestión ni Reportes.
- [ ] Crear un jugador, editar sus datos, darlo de baja (sin referencias activas).
- [ ] Crear un equipo y un plantel en inscripción; confirmar los límites originales.
- [ ] Crear/modificar/eliminar complejo y cancha de prueba.
- [ ] Programar un partido válido entre equipos inscritos de la misma edición.
- [ ] Comprobar rechazo de dos equipos iguales y de partido duplicado en una misma edición.
- [ ] Comprobar rechazo del mismo equipo en la misma fecha.
- [ ] Comprobar rechazo de cancha ocupada en el mismo torneo/día/turno.
- [ ] Registrar planilla solo con jugadores del plantel no suspendidos.
- [ ] Registrar gol y tarjeta solo de jugadores de planilla.
- [ ] Marcar partido como jugado luego del turno usando el procedimiento original.
- [ ] Comprobar resultado automático en `v_resultado_partido`.
- [ ] Comprobar sanción automática por roja y acumulación de tres amarillas en prueba controlada.
- [ ] Comprobar que la sanción disciplinaria puede durar varias fechas.
- [ ] Comprobar el bloqueo de correcciones a partidos jugados fuera de 48 horas.
- [ ] Consultar los 14 reportes y verificar cifras frente a las consultas originales.

**No esperar** que falle la superposición de cancha entre ediciones distintas: el trigger SQL original valida el torneo. Esa diferencia se documenta como pendiente respecto de una interpretación global de la consigna, pero no se modificó por pedido del grupo.

## 3. Antes de la entrega

- [ ] Aportar datos reales de integrantes y contribuciones en `docs/informe.md`.
- [ ] Registrar resultados reales de los casos anteriores, sin marcarlos como ejecutados si no lo fueron.
- [ ] Revisar los compromisos de seguridad de usar texto plano (solo desarrollo local).
- [ ] Si hay otro MySQL o proyecto con el mismo nombre de base, respaldarlo: el script original borra y recrea `torneo_futbol5`.
