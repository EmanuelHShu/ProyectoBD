# Torneo Interfacultades Fútbol 5 — Obligatorio BD1 (UCU, 2026-2)

**Versión ajustada para respetar las decisiones de Seba y Sabrina.** La aplicación web (Python/Flask + MySQL, sin ORM) se integra con **los cuatro scripts SQL de la rama original de Sabrina, sin cambios**. Se quitaron los controles SQL agregados por la versión anterior y se restablecieron las contraseñas de prueba tal como estaban en los archivos originales.

> **Uso local académico únicamente:** el SQL original guarda las contraseñas de `login` **en texto plano** (`pass123`). Esto sigue la decisión solicitada para esta versión, pero es inseguro para una aplicación pública. La letra NO exige explícitamente hashing. No publicar esta aplicación en Internet ni reutilizar estas credenciales.

## Instalación en Windows (sin Docker)

Requisitos: **MySQL 8.0+** (con Workbench o el cliente `mysql`), **Python 3.11 o superior** y conexión para instalar las bibliotecas de `requirements.txt`.

1. Descomprimir el ZIP y abrir una terminal **PowerShell** en esta carpeta.
2. Crear el archivo de configuración:

   ```powershell
   Copy-Item .env.example .env
   ```

   Reemplazar `APP_SECRET_KEY` en `.env` por un secreto largo. El resto de las credenciales coinciden con el SQL **original** de Sabrina.
3. Abrir **CMD** en la misma carpeta (PowerShell no implementa `<` como redirección para comandos externos). Ejecutar los cinco scripts, **en este orden** y usando un usuario MySQL con permisos para crear bases, rutinas, triggers y roles:

   ```cmd
   mysql -u root -p < sql\01_esquema.sql
   mysql -u root -p < sql\02_reglas.sql
   mysql -u root -p < sql\03_datos.sql
   mysql -u root -p < sql\03b_fixture_requerido.sql
   mysql -u root -p < sql\04_seguridad.sql
   ```

   **¡Atención!** `01_esquema.sql` contiene `DROP DATABASE IF EXISTS torneo_futbol5`. Reejecutarlo **elimina los datos existentes** de esta base. No ejecutar sobre una base que quieran conservar.

   Alternativamente, importar y ejecutar esos archivos en **MySQL Workbench** de a uno, manteniendo el orden. No copiar todos los archivos a una sola consulta sin respetar los `DELIMITER`.
4. Volver a PowerShell, crear el entorno de Python, instalar dependencias y ejecutar:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\python.exe -m pip install -r requirements.txt
   .\.venv\Scripts\python.exe app\app.py
   ```

5. Abrir **http://127.0.0.1:5000**.

| Perfil de ejemplo | Correo | Contraseña web |
|---|---|---|
| Administrador | `admin@ucu.edu.uy` | `pass123` |
| Planillero | `planillero@ucu.edu.uy` | `pass123` |

**No confundir** estas dos cuentas web con los **usuarios MySQL** (`login_user`, `admin_user`, `planillero_user`) y sus contraseñas diferentes, que se definen en `sql/04_seguridad.sql`.

### Si falla la conexión de MySQL

- Verificar que el servicio esté iniciado, puerto 3306, `.env` y usuario correcto.
- Los usuarios del SQL original se crean para `@'localhost'`: por eso el despliegue está planteado para ejecutarse localmente junto a MySQL.
- Si hay un error de creación de funciones con binary logging, el servidor podría requerir `log_bin_trust_function_creators=1` con privilegios administrativos.
- Si hay un error de permisos SQL, comprobar `SHOW GRANTS FOR 'planillero_user'@'localhost';` y el resto de los usuarios creados por Sabrina.
- Ejecutar `python -m unittest discover -s tests -v` para comprobar el código localmente. Estas pruebas **no sustituyen** MySQL real.

## Qué conservamos del equipo

Los siguientes archivos son **copias exactas de la rama `ProyectoBD-Branch_Sabri.zip`**, que concentra los cambios trabajados sobre la rama de Seba:

- `sql/01_esquema.sql`: las 14 tablas y sus relaciones/`CHECK`/`UNIQUE`.
- `sql/02_reglas.sql`: los triggers originales, vista, función y procedimientos, sin restricciones extras.
- `sql/03_datos.sql`: los datos originales, incluidos los usuarios con `pass123`, 6 equipos, 13 encuentros y tarjetas originales.
- `sql/04_seguridad.sql`: los roles y permisos MySQL originales con cuentas `@localhost`.
- `docs/consultas_originales_sabri.sql`: consultas/reportes SQL originales, intactos.
- `docs/avance_original_main.pdf`: el avance en PDF de la rama `main`.

**Única ampliación de datos exigida por la letra:** `sql/03b_fixture_requerido.sql` agrega dos cruces que faltaban en la liga a una rueda (2-3 y 4-5), conservando los 13 partidos cargados por el equipo. De ese modo quedan 15 partidos programados/cancelados en 5 fechas para 6 equipos. No se agregan tarjetas ficticias ni se modifican las sanciones del equipo.

## Qué se añadió para que exista una aplicación funcional

- `app/app.py`: inicio de sesión, autorización por roles, gestión de tablas y de partidos, ingreso de planilla/goles/tarjetas y acceso a reportes.
- `app/db.py`: conexiones transaccionales a MySQL utilizando los usuarios y permisos diseñados por Sabrina.
- `app/models.py`: validación de datos de formularios, acorde con las columnas reales de su esquema.
- `app/reports.py`: consultas parametrizadas para seleccionar el torneo, basadas en los reportes del SQL original.
- `app/templates/` y `app/static/`: interfaz web.
- `docs/informe.md`: borrador técnico que distingue los aportes existentes de la aplicación incorporada.
- `docs/PRUEBAS_MANUALES.md`: pasos para comprobar los requisitos en MySQL.

Se **eliminaron** `app/security.py`, el uso de PBKDF2 y las restricciones SQL extra que había puesto la versión anterior. Se retiraron también Docker y Compose porque son opcionales según la letra y esta versión está orientada a instalación local con los usuarios `@localhost` que Sabrina creó.

**Se mantienen** permisos diferenciados, validaciones funcionales de ingreso de datos y la sesión autenticada de Flask porque son necesarios para gestionar usuarios y cumplir las restricciones de acceso que sí exige el trabajo. La protección CSRF que requiere la interfaz no altera el modelo SQL.

## Recorrido básico de uso

1. Administrador entra con la cuenta de demostración y accede al panel de Gestión.
2. Crea o modifica jugadores, equipos, planteles, complejos/canchas y partidos según las restricciones ya programadas en el SQL original.
3. Planillero ingresa y consulta el fixture; abre un partido cuyo turno haya terminado, carga planilla, goles y tarjetas; finaliza con el procedimiento almacenado de Sabrina.
4. Administrador consulta los 14 reportes de la aplicación.

Los partidos históricos de agosto ya superaron la ventana de corrección de 48 horas. Para probar escrituras, usar **datos de prueba nuevos**, respetando las restricciones y sin modificar el fixture de sus compañeros.

## Verificación antes de la entrega

La sintaxis de Python, las plantillas y la correspondencia con el SQL original pueden revisarse con `python -m unittest discover -s tests -v`. **No se ha validado el flujo completo contra MySQL en este entorno:** antes de entregar hay que instalarlo, ejecutar los scripts y verificar altas/bajas, triggers, sanciones, roles y reportes. Consultar `docs/PRUEBAS_MANUALES.md`.

**La letra original** está en `docs/enunciado_original.pdf`. Antes de presentar el informe deben completar los integrantes, sus aportes reales y los resultados de pruebas efectivamente realizadas.
