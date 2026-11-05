# Informe técnico — Trabajo obligatorio de Base de Datos 1

**Gestión del Torneo Interfacultades de Fútbol 5 · UCU · Segundo Semestre 2026**

> Borrador para revisión del grupo. Completar nombres, aportes reales, fechas y evidencias de las pruebas antes de entregar.

## 1. Objetivo y alcance

Implementar una base de datos MySQL y una aplicación Python/Flask sin ORM para la inscripción de jugadores y equipos, gestión de fixture, planillas de partido, resultados y sanciones, junto con consultas de estadísticas del torneo.

## 2. Procedencia y decisiones del equipo

Se adoptó **sin modificaciones** la versión SQL de `ProyectoBD-Branch_Sabri`, que integra el desarrollo previo de la rama de Seba. Se preservaron:

- Las 14 tablas del esquema y sus claves, restricciones y relaciones.
- La clave primaria simple `partido(id_partido)` decidida en la rama de Sabrina, a diferencia de la propuesta que aparecía en el avance de `main`.
- Las relaciones de planteles por equipo, jugador y edición; la unicidad de jugador por edición y los controles de camiseta.
- Los triggers originales para planteles, partidos, planillas, goles, tarjetas y sanciones.
- La vista de resultados, la función de corrección de 48 horas y los procedimientos de sanciones/finalización de partidos.
- Los roles MySQL `rol_administrador`, `rol_planillero` y `rol_login` con los privilegios que decidieron los autores.
- Los datos maestros, el fixture original y las cuentas de demostración con contraseña `pass123`.
- Las consultas originales, conservadas aparte en `docs/consultas_originales_sabri.sql`.

**No** se conservaron los controles adicionales de la versión integrada anterior, como los nuevos triggers de alta/baja de equipos, los bloqueos extra al editar jugadores/torneos, el horario adicional impuesto en el trigger de planilla o la prohibición adicional de editar datos de fixture ya jugado. Tampoco se conservó la modificación del control de cancha para hacerlo global entre ediciones: se preservó el alcance original del trigger de Sabrina.

## 3. Complemento mínimo de datos

Para completar el requerimiento de liga a una rueda, con seis equipos son necesarios **15 enfrentamientos distintos**. El archivo original registraba 13, así que `sql/03b_fixture_requerido.sql` agrega **2-3** y **4-5** en la fecha 5, sin tocar ninguna fila original. Es el único complemento a los datos SQL.

**Nota de alcance:** un encuentro previamente cancelado sigue cancelado (1-6). Esta versión no inventa una reprogramación ni cambia la interpretación de sus datos.

## 4. Arquitectura de la aplicación incorporada

- **Frontend:** formularios HTML, CSS y plantillas Jinja2 de Flask.
- **Backend:** Python/Flask, conexión directa con PyMySQL y consultas parametrizadas, sin ORM.
- **Datos:** mismos scripts SQL, sin reescribir los procedimientos del equipo.
- **Cuentas:** la aplicación comprueba `login.correo` y `login.contrasena` contra los valores de ejemplo de la base; usa el `rol` obtenido para permitir las operaciones correspondientes. Las conexiones SQL usan las cuentas que creó Sabrina.
- **Validación:** controles HTML y Python para los campos enviados y las restricciones originales de MySQL para la integridad.

## 5. Registro de contraseña / seguridad

La tabla `login` conserva el texto plano **como en el script original de Sabrina**. No se utiliza hashing ni cifrado. Esta decisión **no es apropiada para un sitio real expuesto a Internet** y se mantiene exclusivamente para respetar el trabajo original y realizar una demostración local. El enunciado exige seguridad a nivel MySQL y separación de roles, pero no especifica el formato de almacenamiento de la contraseña. Las cuentas y sus contraseñas de prueba deben ser reemplazadas antes de cualquier despliegue real.

El backend comprueba roles en las rutas y aprovecha los GRANT originales para impedir escrituras de un planillero fuera de planillas/goles/tarjetas y el procedimiento de marcar partido jugado.

## 6. Reportes

La aplicación expone 14 consultas, incluido el conjunto exigido por la letra y tres propuestas adicionales. Para la selección de ediciones se implementaron consultas parametrizadas en `app/reports.py`; los SQL originales se conservan sin editar para facilitar su defensa.

## 7. Bitácora y atribución pendiente

| Trabajo observado | Origen |
|---|---|
| Modelo SQL, creación de tablas, datos, consultas y roles | Ramas de Seba y Sabrina (rama de Sabrina usada como versión integrada) |
| Triggers, función y procedimientos para reglas de negocio | Rama original de Sabrina |
| Interfaz Flask, conexiones SQL y páginas de ABM/reportes | Integración de la aplicación en esta entrega |
| Dos partidos adicionales 2-3 y 4-5 | Archivo aislado `03b_fixture_requerido.sql` para satisfacer la liga a una rueda |
| Instrucciones y pruebas estáticas | Esta integración |

**Completar por los integrantes**: identidad de los autores, fechas reales y evidencias de commits. No se atribuyeron aportes personales específicos sin información comprobable.

## 8. Limitaciones y validación

- No se ha ejecutado el sistema contra una instancia real de MySQL dentro de este entorno. Se deben comprobar instalación, permisos, triggers, reportes, ABM y planillas en equipo local.
- La conservación exacta del SQL original implica conservar sus decisiones y posibles limitaciones; por ejemplo, la exclusión de superposición de cancha se comprueba por torneo, no entre ediciones, en el trigger original.
- Las contraseñas del ejemplo se almacenan en claro y deben usarse solo localmente.
- La edición nueva requiere que la creación de planteles, la selección del capitán y las transiciones de estados respeten los triggers existentes.

## 9. Bibliografía de referencia

1. Universidad Católica del Uruguay, *Trabajo obligatorio BD1 - Gestión del Torneo Interfacultades de Fútbol 5*, 2026, material de cátedra proporcionado.
2. MySQL 8.0 Reference Manual, https://dev.mysql.com/doc/refman/8.0/en/
3. Flask Documentation, https://flask.palletsprojects.com/
4. PyMySQL Documentation, https://pymysql.readthedocs.io/
