# Sistema de Gestión del Torneo Interfacultades de Fútbol 5

**Trabajo obligatorio de Base de Datos 1 — Universidad Católica del Uruguay — Segundo semestre de 2026**

**Integrantes:** Emanuel Shu, Nicolás Lozano, Sabrina Pereira y Sebastián Berardi.

Aplicación para gestionar las ediciones del torneo, jugadores, equipos, planteles, complejos, canchas, fixture, planillas, goles, tarjetas, sanciones y reportes. El proyecto utiliza **MySQL** para persistencia y reglas de integridad, y **Python + Flask** para la interfaz web. El acceso a la base se realiza con **PyMySQL**, mediante SQL directo y **sin ORM**.

> **Estado de la versión:** el último ZIP del repositorio contiene `Scripts/`, `app/` e `Informe BD.docx`. Se verificó la estructura y la sintaxis del código Python, pero **no se ha confirmado su ejecución integral contra MySQL**. Para instalar el proyecto desde cero también se necesitan `requirements.txt` y `.env.example`, que no venían en ese ZIP y se suministran junto con este README.

## 1. Estructura del proyecto

```text
ProyectoBD/
├── Scripts/
│   ├── creacion-tablas.sql       # Base y tablas
│   ├── triggers-automaticos.sql  # Vista, función, procedimientos y triggers
│   ├── insercion-datos.sql       # Datos de prueba y fixture
│   ├── consultas.sql             # Consultas y reportes SQL
│   ├── seguridad-roles.sql       # Roles y cuentas de MySQL
│   └── seguriad-roles.sql        # Duplicado con errata (no ejecutar)
├── app/
│   ├── app.py                    # Rutas web, login y operaciones
│   ├── db.py                     # Conexiones y transacciones MySQL
│   ├── models.py                 # Formularios y validaciones
│   ├── reports.py                # Reportes parametrizados
│   ├── templates/                # Plantillas HTML
│   └── static/                   # Estilos CSS
├── Informe BD.docx              # Informe del trabajo
├── requirements.txt             # Dependencias de Python (agregar)
├── .env.example                 # Ejemplo de configuración (agregar)
└── README.md
```

El repositorio también contiene el PDF del avance y algunos archivos de configuración local de DataGrip (`.idea/`); **no son necesarios para levantar la aplicación**.

## 2. Requisitos

- Windows con **Python 3.11 o superior** y `pip`.
- **MySQL Server 8** o versión compatible en ejecución.
- **DataGrip** u otro cliente SQL para instalar y revisar la base.
- Una cuenta de MySQL con privilegios suficientes para crear bases de datos, tablas, vistas, funciones, procedimientos, triggers, roles y usuarios. **No tiene que ser `root`**, pero debe contar con los permisos necesarios.

**Docker no es obligatorio** y no se utiliza en esta versión.

## 3. Preparar MySQL con DataGrip

1. Iniciar el servicio **MySQL Server**. DataGrip es un cliente: por sí solo no ejecuta el servidor.
2. En DataGrip, abrir la conexión MySQL y verificar **Test Connection**.
3. En una consola SQL de esa conexión, ejecutar:

   ```sql
   SHOW DATABASES;
   ```

4. **Antes de continuar, comprobar si existe `torneo_futbol5`.** El primer script del proyecto comienza con `DROP DATABASE IF EXISTS torneo_futbol5;` y **elimina esa base y todos sus registros**. No ejecutarlo sobre datos que se quieran conservar; trabajar sobre una instancia de prueba o realizar un respaldo.
5. En una instalación nueva, ejecutar los scripts mediante **clic derecho sobre la conexión → SQL Scripts → Run SQL Script…**, en este orden:

   1. `Scripts/creacion-tablas.sql`
   2. `Scripts/triggers-automaticos.sql`
   3. `Scripts/insercion-datos.sql`
   4. `Scripts/seguridad-roles.sql`

6. Ante cualquier error, **detener la secuencia**, leer el mensaje y corregirlo antes de ejecutar el siguiente archivo. Ejecutar los scripts completos, especialmente `triggers-automaticos.sql`, que utiliza `DELIMITER`.

**Importante:** no ejecutar `seguriad-roles.sql`; es un duplicado de `seguridad-roles.sql` con el nombre mal escrito.

### 3.1. Datos de prueba y fixture

El `insercion-datos.sql` del último ZIP ya incorpora los **15 partidos** necesarios para una liga de una rueda con 6 equipos. Se distribuyen en 5 fechas con 3 partidos en cada una. Los partidos **13, 14 y 15** de la fecha 5 figuran como **`programado`**.

**No es necesario añadir otro script de fixture ni volver a insertar los partidos 13, 14 y 15.** La versión más antigua de los datos tenía el partido 13 cancelado, pero la versión actual lo deja programado.

Al terminar, comprobar desde una consola SQL:

```sql
USE torneo_futbol5;

SELECT COUNT(*) AS equipos FROM equipo;           -- Esperado: 6
SELECT COUNT(*) AS jugadores FROM jugador;         -- Esperado: 31
SELECT COUNT(*) AS partidos FROM partido;         -- Esperado: 15
SELECT COUNT(*) AS jugados FROM partido
WHERE estado = 'jugado';                           -- Esperado: 9

SELECT numero_fecha, COUNT(*) AS partidos
FROM partido
GROUP BY numero_fecha
ORDER BY numero_fecha;                            -- Esperado: 3 en cada fecha (1 a 5)

SELECT id_partido, estado
FROM partido
WHERE id_partido IN (13, 14, 15)
ORDER BY id_partido;                               -- Todos programados
```

Los valores anteriores son los resultados **esperados a partir del script**. Deben verificarse ejecutándolo en MySQL; no sustituyen las pruebas funcionales.

## 4. Preparar Python

Abrir la carpeta raíz de `ProyectoBD` en **VS Code** y abrir una terminal **PowerShell** en esa ubicación. Debe existir la carpeta `app/`.

Verificar Python y crear un entorno virtual:

```powershell
py --version
py -m venv .venv
```

Instalar dependencias:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Crear el archivo de configuración local:

```powershell
Copy-Item .env.example .env
```

Editar **`.env`** con los datos de **tu servidor MySQL**. En una instalación local con los usuarios de demostración creados por `seguridad-roles.sql`, la estructura es:

```ini
APP_SECRET_KEY=CAMBIAR_POR_UN_SECRETO_LARGO_Y_ALEATORIO
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

Los usuarios **`login_user`, `admin_user` y `planillero_user` son cuentas de MySQL**, distintas de las cuentas de acceso web. Si las contraseñas de MySQL ya fueron modificadas en tu servidor, usar las vigentes. Si los usuarios existían antes de ejecutar `seguridad-roles.sql`, la instrucción `CREATE USER IF NOT EXISTS` **no cambia sus contraseñas**.

**No subir `.env` a GitHub**: incluye contraseñas. Para mantenerlo fuera del repositorio, agregar `.env`, `.venv/` y `__pycache__/` al archivo `.gitignore` local del proyecto.

## 5. Levantar la aplicación web

Con MySQL iniciado, la base instalada y el archivo `.env` configurado, ejecutar desde PowerShell en la raíz del proyecto:

```powershell
.\.venv\Scripts\python.exe app\app.py
```

Si Flask inicia correctamente, abrir en el navegador:

**http://127.0.0.1:5000**

La consola debe permanecer abierta mientras se usa la aplicación. Detener con `Ctrl + C`.

### Cuentas web de ejemplo

| Perfil | Correo | Contraseña |
| --- | --- | --- |
| Administrador | `admin@ucu.edu.uy` | `pass123` |
| Planillero | `planillero@ucu.edu.uy` | `pass123` |

Son cuentas definidas en la tabla `login` del script de datos. Sus contraseñas están en texto plano por decisión de esta versión de demostración. **Usar solo en un entorno académico local, no publicar la aplicación en Internet.**

## 6. Funciones principales

**Administrador:** puede utilizar los catálogos y formularios para administrar jugadores, facultades, ediciones, equipos, planteles, complejos, canchas, turnos, partidos, usuarios y sanciones disciplinarias. También puede consultar los reportes.

**Planillero:** puede consultar los partidos y registrar los participantes en planillas, goles y tarjetas; el cambio de un partido a estado `jugado` usa el procedimiento almacenado `sp_marcar_partido_jugado`.

**Base de datos:** las claves, restricciones, triggers, vistas y procedimientos de los scripts SQL determinan la validez final de las operaciones. La interfaz Python envía sentencias parametrizadas y muestra errores cuando MySQL rechaza datos inválidos.

## 7. Reportes

- `Scripts/consultas.sql` conserva los reportes escritos en SQL por el equipo.
- `app/reports.py` define sus versiones parametrizadas para la interfaz web.

Entre los indicadores se incluyen tabla de posiciones, goleadores, fair play, goles por fecha y edición, uso de canchas y turnos, jugadores por facultad y tipo, inscriptos sin participación, sanciones y porcentaje de partidos por estado, además de las tres consultas adicionales incluidas en el proyecto.

## 8. Pruebas manuales pendientes

Después de iniciar correctamente el proyecto, registrar en el informe el resultado **real** de estas verificaciones:

- [ ] Se crearon correctamente las 14 tablas y se ejecutaron los scripts sin errores.
- [ ] Los datos de prueba muestran 6 equipos, 31 jugadores, 15 partidos y 9 jugados.
- [ ] El administrador y el planillero pueden iniciar sesión.
- [ ] El administrador puede consultar, crear, modificar y eliminar registros permitidos.
- [ ] El planillero no puede acceder a las operaciones exclusivas de administrador.
- [ ] El registro de planillas, goles y tarjetas funciona en partidos habilitados.
- [ ] Los triggers rechazan enfrentamientos inválidos y participantes suspendidos.
- [ ] Se generan las sanciones por tarjeta roja y acumulación de tres amarillas.
- [ ] El resultado se calcula a partir de los goles y los reportes se ejecutan correctamente.

Para probar operaciones de escritura, usar una edición de **prueba** y horarios válidos; los partidos históricos están sujetos a las reglas de estados y corrección de 48 horas.

**Estado de la revisión:** comprobación estática de la estructura, scripts y sintaxis Python. **No se han acreditado todavía las pruebas anteriores en un servidor MySQL real.**

## 9. Resolución de problemas

| Problema | Qué revisar |
| --- | --- |
| `Access denied for user 'root'` | Las credenciales de la cuenta administrativa de MySQL; `root` no es obligatorio si existe otra cuenta con privilegios suficientes. |
| `Access denied ... login_user` | Confirmar que se ejecutó `seguridad-roles.sql` y que las contraseñas en `.env` sean correctas. |
| `Can't connect to MySQL server` | Servicio MySQL, dirección `DB_HOST`, puerto `DB_PORT` y firewall. |
| `No module named flask` o `pymysql` | Instalar las dependencias con el Python del entorno virtual. |
| `Table ... doesn't exist` | Verificar que se instalaron los scripts y que `DB_NAME=torneo_futbol5`. |
| Error de claves duplicadas | Evitar ejecutar dos veces los scripts de datos sobre una base ya cargada. |
| Error con `DELIMITER` | Ejecutar el archivo de triggers completo con el ejecutor de scripts SQL de DataGrip. |
| Aparece un error al editar un partido histórico | Revisar el estado del partido y el límite de 48 horas en los triggers. |

## 10. Documentación y entrega

- **Informe del proyecto:** `Informe BD.docx`.
- **SQL:** carpeta `Scripts/`.
- **Backend y frontend:** carpeta `app/`.
- **Fecha de entrega:** 6 de noviembre de 2026.
- **Defensa:** 13 de noviembre de 2026.

Antes de entregar, completar la bitácora con las contribuciones reales del equipo y documentar las pruebas manuales realizadas. Este README describe la **estructura del ZIP revisado** y no afirma que la aplicación esté funcionalmente validada sin esas pruebas.
