"""Utilidades base para correr las pruebas sobre un MySQL temporal.

Levanta un mysqld aparte en un puerto libre (con datadir temporal) para no tocar
una base torneo_futbol5 local, ya que creacion-tablas.sql hace DROP DATABASE.
"""
import atexit
import glob
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

import pymysql

sys.dont_write_bytecode = True

ROOT_DIR = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT_DIR / "Scripts"
ORDEN_SCRIPTS = (
    "creacion-tablas.sql",
    "triggers-automaticos.sql",
    "insercion-datos.sql",
    "seguridad-roles.sql",
)
SQL_MODE = (
    "ONLY_FULL_GROUP_BY,STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,"
    "ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION"
)

DB_LOGIN = ("login_user", "LoginPass2026*")
DB_ADMIN = ("admin_user", "AdminPass2026*")
DB_PLANILLERO = ("planillero_user", "PlanilleroPass2026*")

WEB_ADMIN = ("admin@ucu.edu.uy", "pass123")
WEB_PLANILLERO = ("planillero@ucu.edu.uy", "pass123")

JUGADORES_FACULTAD = {
    1: ["11111111", "11111112", "11111113", "11111114", "11111115"],
    2: ["22222221", "22222222", "22222223", "22222224", "22222225"],
    3: ["33333331", "33333332", "33333333", "33333334", "33333335"],
    4: ["44444441", "44444442", "44444443", "44444444", "44444445"],
}


def _buscar_mysql_bin():
    rutas = []
    if os.getenv("MYSQL_BIN"):
        rutas.append(os.environ["MYSQL_BIN"])
    mysqld_path = shutil.which("mysqld")
    if mysqld_path:
        rutas.append(str(Path(mysqld_path).parent))
    rutas.extend(sorted(glob.glob(r"C:\Program Files\MySQL\MySQL Server 8.*\bin"), reverse=True))

    for carpeta in rutas:
        p = Path(carpeta)
        if (p / "mysqld.exe").exists() or (p / "mysqld").exists():
            return p
    raise RuntimeError("No se encontró mysqld. Configurá la variable de entorno MYSQL_BIN.")


def _puerto_libre():
    while True:
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
            if port != 3306:
                return port


class _MysqlTemporal:
    def __init__(self):
        self.bin_dir = _buscar_mysql_bin()
        self.workdir = Path(tempfile.mkdtemp(prefix="torneo_test_"))
        self.datadir = self.workdir / "data"
        self.port = _puerto_libre()
        self.proc = None
        self._log = None

    def _bin(self, nombre):
        exe = self.bin_dir / f"{nombre}.exe"
        return str(exe if exe.exists() else self.bin_dir / nombre)

    def iniciar(self):
        base_args = ["--no-defaults", f"--basedir={self.bin_dir.parent}", f"--datadir={self.datadir}"]
        subprocess.run(
            [self._bin("mysqld"), *base_args, "--initialize-insecure", "--console"],
            check=True,
            capture_output=True,
        )
        self._log = open(self.workdir / "mysqld.log", "wb")
        self.proc = subprocess.Popen(
            [
                self._bin("mysqld"),
                *base_args,
                f"--port={self.port}",
                "--bind-address=127.0.0.1",
                "--mysqlx=0",
                f"--sql-mode={SQL_MODE}",
                "--innodb-flush-log-at-trx-commit=0",
                "--sync-binlog=0",
                "--console",
            ],
            stdout=self._log,
            stderr=self._log,
        )
        deadline = time.time() + 60
        while time.time() < deadline:
            try:
                pymysql.connect(host="127.0.0.1", port=self.port, user="root", password="").close()
                return
            except pymysql.MySQLError:
                time.sleep(0.3)
        raise RuntimeError("No pudo iniciar la instancia temporal de MySQL.")

    def detener(self):
        if self.proc and self.proc.poll() is None:
            subprocess.run(
                [self._bin("mysqladmin"), "--no-defaults", "-h127.0.0.1", f"-P{self.port}", "-uroot", "shutdown"],
                capture_output=True,
            )
            try:
                self.proc.wait(timeout=25)
            except subprocess.TimeoutExpired:
                self.proc.kill()
        if self._log:
            self._log.close()
        shutil.rmtree(self.workdir, ignore_errors=True)


_servidor = None
_db_sucia = True
_flask_mod = None


def servidor_mysql():
    global _servidor
    if _servidor is None:
        _servidor = _MysqlTemporal()
        atexit.register(_servidor.detener)
        _servidor.iniciar()
    return _servidor


def ejecutar_script(nombre, user="root", password=""):
    # Usamos el cliente mysql por consola porque PyMySQL no soporta DELIMITER
    srv = servidor_mysql()
    cmd = [
        srv._bin("mysql"),
        "--no-defaults",
        "-h127.0.0.1",
        f"-P{srv.port}",
        f"-u{user}",
        "--default-character-set=utf8mb4",
    ]
    if password:
        cmd.append(f"-p{password}")
    with open(SCRIPTS_DIR / nombre, "rb") as f:
        res = subprocess.run(cmd, stdin=f, capture_output=True)
    if res.returncode != 0:
        err = res.stderr.decode("utf-8", "replace")
        raise RuntimeError(f"Error ejecutando {nombre}: {err}")


def reset_db():
    global _db_sucia
    for script in ORDEN_SCRIPTS:
        ejecutar_script(script)
    _db_sucia = False


def conectar(user="root", password="", autocommit=True, database="torneo_futbol5"):
    return pymysql.connect(
        host="127.0.0.1",
        port=servidor_mysql().port,
        user=user,
        password=password,
        database=database,
        autocommit=autocommit,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
    )


def crear_edicion_prueba(conn, en_curso=True):
    """Arma el torneo 2 con 4 equipos (id 11..14) y sus 5 titulares cada uno."""
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO torneo (id_torneo, nombre, anio, semestre, fecha_inicio, fecha_fin, estado) "
            "VALUES (2, 'Apertura 2027', 2027, 1, '2026-10-01', '2027-06-30', 'inscripcion')"
        )
        cur.execute(
            "INSERT INTO equipo (id_equipo, nombre, id_torneo, id_facultad, ci_capitan) VALUES "
            "(11, 'Ingenieria B', 2, 1, '11111111'), "
            "(12, 'Administracion B', 2, 2, '22222221'), "
            "(13, 'Derecho B', 2, 3, '33333331'), "
            "(14, 'Medicina B', 2, 4, '44444441')"
        )
        for id_equipo, id_facultad in ((11, 1), (12, 2), (13, 3), (14, 4)):
            for camiseta, ci in enumerate(JUGADORES_FACULTAD[id_facultad], start=1):
                cur.execute(
                    "INSERT INTO equipo_jugador_torneo (id_equipo, ci_jugador, id_torneo, numero_camiseta) "
                    "VALUES (%s, %s, 2, %s)",
                    (id_equipo, ci, camiseta),
                )
        if en_curso:
            cur.execute("UPDATE torneo SET estado='en curso' WHERE id_torneo=2")


def insertar_partido(conn, id_partido, fecha, local, visitante, dia, turno=1,
                     cancha="Cancha 1", complejo=1, estado="programado", torneo=2):
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO partido (id_partido, id_torneo, numero_fecha, id_equipo_local, "
            "id_equipo_visitante, dia, id_turno, nombre_cancha, id_complejo, estado) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (id_partido, torneo, fecha, local, visitante, dia, turno, cancha, complejo, estado),
        )


def firmar_planilla(conn, id_partido, id_equipo, cedulas):
    with conn.cursor() as cur:
        for ci in cedulas:
            cur.execute(
                "INSERT INTO planilla_partido (id_partido, ci_jugador, id_equipo) VALUES (%s, %s, %s)",
                (id_partido, ci, id_equipo),
            )


class _HelpersSQL:
    def query(self, sql, args=None, conn=None):
        c = conn or self.conn
        with c.cursor() as cur:
            cur.execute(sql, args)
            return cur.fetchall()

    def execute(self, sql, args=None, conn=None):
        return self.query(sql, args, conn=conn)

    def scalar(self, sql, args=None, conn=None):
        rows = self.query(sql, args, conn=conn)
        return next(iter(rows[0].values())) if rows else None

    def assertErrorSQL(self, sql, args=None, contiene=None, conn=None):
        with self.assertRaises(pymysql.MySQLError) as ctx:
            self.query(sql, args, conn=conn)
        if contiene:
            self.assertIn(contiene.lower(), str(ctx.exception).lower())


class TestBD(_HelpersSQL, unittest.TestCase):
    """Corre cada test dentro de una transacción y hace rollback al terminar."""

    @classmethod
    def setUpClass(cls):
        if _db_sucia:
            reset_db()

    def setUp(self):
        self.conn = conectar(autocommit=False)

    def tearDown(self):
        self.conn.rollback()
        self.conn.close()


class TestBDAislado(_HelpersSQL, unittest.TestCase):
    """Recarga los scripts antes del test (para pruebas con varias conexiones o commits)."""

    def setUp(self):
        global _db_sucia
        reset_db()
        _db_sucia = True
        self.conn = conectar(autocommit=True)

    def tearDown(self):
        self.conn.close()


def _cargar_flask():
    global _flask_mod
    if _flask_mod is None:
        port = servidor_mysql().port
        os.environ.update({
            "DB_HOST": "127.0.0.1",
            "DB_PORT": str(port),
            "DB_NAME": "torneo_futbol5",
            "DB_LOGIN_USER": DB_LOGIN[0],
            "DB_LOGIN_PASSWORD": DB_LOGIN[1],
            "DB_ADMIN_USER": DB_ADMIN[0],
            "DB_ADMIN_PASSWORD": DB_ADMIN[1],
            "DB_PLAN_USER": DB_PLANILLERO[0],
            "DB_PLAN_PASSWORD": DB_PLANILLERO[1],
            "APP_SECRET_KEY": "clave-pruebas-locales-ucu-bd1",
        })
        app_dir = str(ROOT_DIR / "app")
        if app_dir not in sys.path:
            sys.path.insert(0, app_dir)
        import db as db_mod
        import app as app_mod
        db_mod.CONFIG["host"] = "127.0.0.1"
        db_mod.CONFIG["port"] = port
        db_mod.CONFIG["database"] = "torneo_futbol5"
        _flask_mod = app_mod
    return _flask_mod


def extraer_csrf(html_text):
    m = re.search(r'name="csrf_token"\s+value="([^"]+)"', html_text)
    return m.group(1) if m else ""


class TestWeb(TestBDAislado):
    def setUp(self):
        super().setUp()
        self.app_mod = _cargar_flask()
        self.app = self.app_mod.app

    def login(self, cuenta):
        client = self.app.test_client()
        login_page = client.get("/login")
        resp = client.post(
            "/login",
            data={
                "csrf_token": extraer_csrf(login_page.text),
                "correo": cuenta[0],
                "password": cuenta[1],
            },
        )
        return client, resp

    def post_csrf(self, client, url, data=None, from_url="/", follow=True):
        form_data = dict(data or {})
        if "csrf_token" not in form_data:
            page = client.get(from_url, follow_redirects=True)
            form_data["csrf_token"] = extraer_csrf(page.text)
        return client.post(url, data=form_data, follow_redirects=follow)
