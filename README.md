# Torneo Interfacultades de Fútbol 5 — Base de Datos 1

**Universidad Católica del Uruguay · Segundo semestre de 2026**

**Integrantes:** Emanuel Shu, Nicolás Lozano, Sabrina Pereira y Sebastián Berardi.

Sistema para gestionar las ediciones del torneo universitario de fútbol 5: equipos, jugadores, planteles, calendario, planillas, goles, tarjetas, sanciones y reportes. La base de datos se desarrolla en **MySQL**; la aplicación complementaria utiliza **Python, Flask y PyMySQL, sin ORM**.

> **Estado de integración (05/11/2026).** El último ZIP recibido de `main` contiene los scripts SQL en `Scripts/`, pero **no contiene la carpeta `app/`**. Para ejecutar la interfaz hay que incorporar al repositorio la aplicación Python preparada por separado y luego verificarla con una instancia real de MySQL. Este README documenta tanto lo que ya existe en `main` como los pasos para completar esa integración; no implica que las pruebas de extremo a extremo estén aprobadas.

## 1. Estructura del proyecto

```text
ProyectoBD/
├── Scripts/                         # Existente en main: SQL del equipo
│   ├── creacion-tablas.sql
│   ├── triggers-automaticos.sql
│   ├── insercion-datos.sql
│   ├── consultas.sql
│   └── seguridad-roles.sql
├── app/                             # Agregar desde la integración Python
│   ├── app.py
│   ├── db.py
│   ├── models.py
│   ├── reports.py
│   ├── templates/
│   └── static/
├── requirements.txt                 # Agregar con la aplicación Python
├── .env.example                     # Agregar con la aplicación Python
├── docs/
│   └── informe_final.md
└── README.md
```

En `main` también existe `Scripts/seguriad-roles.sql`, duplicado con el nombre mal escrito. El archivo que se debe ejecutar es **`Scripts/seguridad-roles.sql`**. No hace falta ejecutar ambos.

## 2. Requisitos para ejecutar el sistema

- **MySQL Server 8.0 o compatible** en ejecución (DataGrip es solo el cliente para administrar ese servidor).
- **DataGrip** u otro cliente que permita ejecutar archivos SQL.
- **Python 3.11 o superior** y `pip` si se utilizará la interfaz web.
- Un usuario de MySQL con permisos para **crear bases, tablas, vistas, triggers, funciones, procedimientos y usuarios/roles** durante la instalación. **No tiene que llamarse `root`**.

No se requiere Docker: la consigna lo considera un aspecto valorado, pero opcional.

## 3. Inicialización de MySQL desde DataGrip

**Precaución:** `Scripts/creacion-tablas.sql` comienza con `DROP DATABASE IF EXISTS torneo_futbol5;`. **Borra la base existente y todos sus datos**. Hacer un respaldo y trabajar en una base de prueba si ya hay registros importantes.

1. Abrir DataGrip, conectar al servidor MySQL y verificar la conexión (`Test Connection`).
2. Abrir una consola SQL sobre esa conexión y comprobar `SHOW DATABASES;`.
3. Si es una instalación nueva o se ha autorizado recrear `torneo_futbol5`, ejecutar los archivos en este orden mediante **clic derecho en la conexión → SQL Scripts → Run SQL Script…**:

   1. `Scripts/creacion-tablas.sql`
   2. `Scripts/triggers-automaticos.sql`
   3. `Scripts/insercion-datos.sql`
   4. Complemento del fixture **solo si faltan los cruces 2–3 y 4–5** (ver sección siguiente).
   5. `Scripts/seguridad-roles.sql`

4. Detenerse ante cualquier error. El orden es importante: los triggers necesitan las tablas, y la seguridad hace referencia a la vista y al procedimiento definidos en `triggers-automaticos.sql`.
5. Actualizar el explorador de DataGrip para ver las tablas de `torneo_futbol5`.

### 3.1. Fixture: evitar duplicados

El `insercion-datos.sql` del **último `main` recibido** incluye los partidos **1–13**; el partido 13 es el encuentro **1 vs. 6 cancelado**. Para completar los 15 enfrentamientos de seis equipos en una ronda, faltan 2–3 y 4–5. Si esos encuentros **no están insertados**, ejecutar **una sola vez**:

```sql
USE torneo_futbol5;
INSERT INTO partido
(id_partido, id_torneo, numero_fecha, id_equipo_local, id_equipo_visitante,
 dia, id_turno, nombre_cancha, id_complejo, estado)
VALUES
(14, 1, 5, 2, 3, '2026-11-16', 2, 'Cancha 1', 1, 'programado'),
(15, 1, 5, 4, 5, '2026-11-16', 3, 'Cancha 1', 1, 'programado');
```

**Si usaron una copia editada del script de inserción que ya contiene 14 y 15, no ejecuten de nuevo este bloque.** Verifiquen además que esté el partido 13: en el script original estaba **cancelado**, una decisión que conviene conservar en vez de sobrescribirla.

### 3.2. Verificaciones iniciales en DataGrip

```sql
USE torneo_futbol5;

SELECT COUNT(*) AS equipos FROM equipo;          -- Esperado: 6
SELECT COUNT(*) AS jugadores FROM jugador;        -- Esperado: 31
SELECT COUNT(*) AS partidos FROM partido;        -- Esperado: 15 tras el complemento
SELECT COUNT(*) AS jugados FROM partido
WHERE estado = 'jugado';                          -- Esperado: 9

SELECT numero_fecha, COUNT(*) AS partidos
FROM partido
GROUP BY numero_fecha
ORDER BY numero_fecha;                           -- Esperado: 3 por fecha (1 a 5)

SELECT id_partido, estado FROM partido
WHERE id_partido IN (13,14,15)
ORDER BY id_partido;
```

Los números son **resultados esperados a partir de los INSERT**; deben confirmarse ejecutando las consultas. Una cantidad correcta por sí sola no prueba que funcionen todas las restricciones.

## 4. Iniciar la aplicación web con Python

> Esta sección es aplicable **una vez incorporados `app/`, `requirements.txt` y `.env.example`** al mismo repositorio. Esos archivos no están en el último `main` SQL recibido.

Abrir **PowerShell en la raíz de `ProyectoBD/`** y ejecutar:

```powershell
py --version
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Editar el archivo `.env` creado. Configurar:

```ini
APP_SECRET_KEY=REEMPLAZAR_POR_UN_VALOR_LARGO_ALEATORIO
APP_HOST=127.0.0.1
APP_PORT=5000
COOKIE_SECURE=false
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=torneo_futbol5
DB_LOGIN_USER=login_user
DB_LOGIN_PASSWORD=LoginPass2026*
DB_ADMIN_USER=admin_user
DB_ADMIN_PASSWORD=AdminPass2026*
DB_PLAN_USER=planillero_user
DB_PLAN_PASSWORD=PlanilleroPass2026*
```

Los usuarios `login_user`, `admin_user` y `planillero_user` son **usuarios MySQL** creados por `seguridad-roles.sql` en el servidor local. Sus contraseñas deben coincidir con las vigentes en esa instalación. No subir el archivo `.env` a GitHub.

Iniciar Flask:

```powershell
.\.venv\Scripts\python.exe app\app.py
```

Abrir **http://127.0.0.1:5000** en el navegador. El servidor Flask debe permanecer abierto mientras se utiliza la interfaz.

**Cuentas web de demostración** (tabla `login`, diferentes de los usuarios MySQL):

| Perfil | Correo | Contraseña de ejemplo |
|---|---|---|
| Administrador | `admin@ucu.edu.uy` | `pass123` |
| Planillero | `planillero@ucu.edu.uy` | `pass123` |

Estas contraseñas son de **prueba local** y el SQL original las almacena en texto plano. **No exponer la aplicación en Internet** ni reutilizar esas credenciales en otros servicios.

## 5. Uso básico de la aplicación

- **Administrador:** administra jugadores, equipos, planteles, complejos, canchas, turnos, ediciones, partidos y sanciones disciplinarias; consulta los reportes.
- **Planillero:** accede a los partidos, registra participantes, goles y tarjetas, y marca un encuentro como jugado utilizando el procedimiento autorizado por MySQL.
- **Reglas de negocio:** las claves, restricciones, triggers y procedimientos del SQL determinan la validez final de las operaciones; Python valida entradas y comunica errores.

El sistema distingue edición del torneo, fecha deportiva y día/turno del encuentro. Un partido cancelado no cuenta como partido jugado. Los partidos históricos de agosto tienen restricciones de corrección de resultados de 48 horas, así que para comprobar escrituras deben utilizarse escenarios de prueba apropiados.

## 6. Reportes

`Scripts/consultas.sql` conserva las consultas SQL del equipo. La aplicación Python, una vez incorporada, muestra reportes parametrizados en `app/reports.py` (por edición, cuando corresponde). Se incluyen posiciones, goleadores, fair play, promedios de goles, utilización de canchas y turnos, distribución de jugadores, jugadores sin planilla, sanciones, estados de partidos y tres consultas adicionales: asistencia perfecta, jugadores inhabilitados y valla menos vencida.

## 7. Pruebas mínimas antes de entregar

- [ ] Se crea la base y terminan todos los scripts sin errores.
- [ ] Se comprueban 6 equipos, 31 jugadores, 15 partidos y 3 fechas jugadas en los datos de ejemplo.
- [ ] Funcionan las conexiones MySQL desde Python y ambos inicios de sesión.
- [ ] El administrador puede realizar los ABM previstos.
- [ ] El planillero no puede modificar información de administración.
- [ ] Los triggers rechazan equipos repetidos en la misma fecha, enfrentamiento contra sí mismo y participantes suspendidos.
- [ ] Las tarjetas rojas y tres amarillas generan las sanciones previstas.
- [ ] El resultado y la tabla de posiciones coinciden con los goles registrados.
- [ ] Los reportes se ejecutan y muestran datos coherentes.
- [ ] Se documentan los resultados reales de las pruebas en `docs/informe_final.md`.

Se verificó **sintaxis de Python** del complemento en el entorno de preparación del documento, **no** su integración completa con un servidor MySQL real.

## 8. Problemas habituales

| Síntoma | Qué revisar |
|---|---|
| `Access denied for user 'root'` | Credenciales de la cuenta de instalación. `root` no es imprescindible, pero se necesita algún usuario con privilegios suficientes. |
| `Can't connect to MySQL server` | Servicio MySQL iniciado, host/puerto, red y variables de `.env`. |
| `Access denied ... login_user/admin_user` | Ejecutar `seguridad-roles.sql`; comprobar contraseñas y que los usuarios se crearon para `@localhost`. |
| `No module named flask` | Instalar dependencias dentro de `.venv`. |
| `Table ... doesn't exist` | Confirmar creación del esquema y que `.env` apunta a `torneo_futbol5`. |
| Error de clave duplicada en el fixture | No volver a ejecutar INSERT de partidos ya creados. |
| Error `DELIMITER` | Ejecutar el script completo con el ejecutor de scripts, no solo una sentencia seleccionada. |

## 9. Documentación y decisiones

- **Informe técnico:** [`docs/informe_final.md`](docs/informe_final.md).
- **SQL original:** `Scripts/` (se conservan sus decisiones de modelado y reglas).
- **Entrega:** 06/11/2026; **defensa:** 13/11/2026, según la consigna.
- Docker y Docker Compose no son obligatorios y **no forman parte de esta versión**.

El informe diferencia lo implementado en los archivos, lo integrado en la aplicación complementaria y lo que aún requiere pruebas manuales. Antes de la entrega, comprobar el estado real del repositorio y actualizar esas evidencias.
