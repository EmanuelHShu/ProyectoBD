"""Infraestructura comun de las pruebas automatizadas.

Cada ejecucion levanta una instancia TEMPORAL de MySQL, con datos propios y en un
puerto libre, y la elimina al terminar. Nunca se conecta al servidor MySQL
instalado: los scripts del proyecto empiezan con DROP DATABASE y borrarian una
base real. Requiere tener MySQL 8 instalado (solo se usan sus ejecutables).

Si los ejecutables no estan en la ruta habitual, indicar la carpeta bin con la
variable de entorno MYSQL_BIN.
"""
import atexit
import glob
import html
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from html.parser import HTMLParser
from pathlib import Path

sys.dont_write_bytecode = True

import pymysql

RAIZ = Path(__file__).resolve().parents[1]
SCRIPTS = RAIZ / "Scripts"
ORDEN_SCRIPTS = ("creacion-tablas.sql", "triggers-automaticos.sql",
                 "insercion-datos.sql", "seguridad-roles.sql")
SQL_MODE = ("ONLY_FULL_GROUP_BY,STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,"
            "ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION")

# Cuentas de demostracion definidas en Scripts/seguridad-roles.sql e insercion-datos.sql.
CUENTA_LOGIN = ("login_user", "LoginPass2026*")
CUENTA_ADMIN = ("admin_user", "AdminPass2026*")
CUENTA_PLANILLERO = ("planillero_user", "PlanilleroPass2026*")
WEB_ADMIN = ("admin@ucu.edu.uy", "pass123")
WEB_PLANILLERO = ("planillero@ucu.edu.uy", "pass123")

# Jugadores de los datos de prueba, por facultad (cinco de cada una).
FACULTAD = {
    1: ["11111111", "11111112", "11111113", "11111114", "11111115"],
    2: ["22222221", "22222222", "22222223", "22222224", "22222225"],
    3: ["33333331", "33333332", "33333333", "33333334", "33333335"],
    4: ["44444441", "44444442", "44444443", "44444444", "44444445"],
}


# ---------------------------------------------------------------- servidor temporal
def carpeta_bin():
    candidatos = []
    if os.environ.get("MYSQL_BIN"):
        candidatos.append(os.environ["MYSQL_BIN"])
    if shutil.which("mysqld"):
        candidatos.append(str(Path(shutil.which("mysqld")).parent))
    candidatos += sorted(glob.glob(r"C:\Program Files\MySQL\MySQL Server 8.*\bin"), reverse=True)
    for carpeta in candidatos:
        ruta = Path(carpeta)
        if (ruta / "mysqld.exe").exists() or (ruta / "mysqld").exists():
            return ruta
    raise RuntimeError("No se encontro mysqld. Indicar la carpeta bin con la variable MYSQL_BIN.")


def puerto_libre():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class ServidorTemporal:
    def __init__(self):
        self.bin = carpeta_bin()
        self.carpeta = Path(tempfile.mkdtemp(prefix="torneo_mysql_"))
        self.datos = self.carpeta / "datos"
        self.puerto = puerto_libre()
        self.proceso = None
        self._log = None
        assert self.puerto != 3306

    def exe(self, nombre):
        ruta = self.bin / (nombre + ".exe")
        return str(ruta if ruta.exists() else self.bin / nombre)

    def iniciar(self):
        comun = ["--no-defaults", f"--basedir={self.bin.parent}", f"--datadir={self.datos}"]
        subprocess.run([self.exe("mysqld"), *comun, "--initialize-insecure", "--console"],
                       check=True, capture_output=True)
        self._log = open(self.carpeta / "mysqld.log", "wb")
        self.proceso = subprocess.Popen(
            [self.exe("mysqld"), *comun, f"--port={self.puerto}", "--bind-address=127.0.0.1",
             "--mysqlx=0", f"--sql-mode={SQL_MODE}", "--innodb-flush-log-at-trx-commit=0",
             "--sync-binlog=0", "--console"],
            stdout=self._log, stderr=self._log)
        limite = time.time() + 60
        while time.time() < limite:
            try:
                pymysql.connect(host="127.0.0.1", port=self.puerto, user="root", password="").close()
                return
            except pymysql.MySQLError:
                time.sleep(0.3)
        raise RuntimeError("El servidor temporal de MySQL no inicio a tiempo.")

    def detener(self):
        if self.proceso and self.proceso.poll() is None:
            subprocess.run([self.exe("mysqladmin"), "--no-defaults", "-h127.0.0.1",
                            f"-P{self.puerto}", "-uroot", "shutdown"], capture_output=True)
            try:
                self.proceso.wait(timeout=30)
            except subprocess.TimeoutExpired:
                self.proceso.kill()
        if self._log:
            self._log.close()
        shutil.rmtree(self.carpeta, ignore_errors=True)


_servidor = None
_base_modificada = True


def servidor():
    """Devuelve el servidor temporal de esta ejecucion; lo inicia la primera vez."""
    global _servidor
    if _servidor is None:
        _servidor = ServidorTemporal()
        atexit.register(_servidor.detener)
        _servidor.iniciar()
    return _servidor


def ejecutar_script(nombre, usuario="root", clave=""):
    """Corre un script con el cliente mysql, que es el que entiende DELIMITER."""
    srv = servidor()
    comando = [srv.exe("mysql"), "--no-defaults", "-h127.0.0.1", f"-P{srv.puerto}", f"-u{usuario}",
               "--default-character-set=utf8mb4"]
    if clave:
        comando.append(f"-p{clave}")
    with open(SCRIPTS / nombre, "rb") as archivo:
        return subprocess.run(comando, stdin=archivo, capture_output=True)


def restaurar():
    """Deja la base como recien instalada, corriendo los cuatro scripts en orden."""
    global _base_modificada
    for nombre in ORDEN_SCRIPTS:
        resultado = ejecutar_script(nombre)
        if resultado.returncode != 0:
            raise RuntimeError(f"{nombre} fallo: {resultado.stderr.decode('utf-8', 'replace')}")
    _base_modificada = False


def asegurar_datos():
    if _base_modificada:
        restaurar()


# ---------------------------------------------------------------- acceso a la base
def conectar(usuario="root", clave="", autocommit=True, base="torneo_futbol5"):
    return pymysql.connect(host="127.0.0.1", port=servidor().puerto, user=usuario, password=clave,
                           database=base, autocommit=autocommit, charset="utf8mb4",
                           cursorclass=pymysql.cursors.DictCursor)


def q(c, sql, args=None):
    with c.cursor() as cursor:
        cursor.execute(sql, args)
        return cursor.fetchall()


def valor(c, sql, args=None):
    filas = q(c, sql, args)
    return list(filas[0].values())[0] if filas else None


def intentar(c, sql, args=None):
    """Ejecuta la sentencia y devuelve (salio_bien, mensaje_de_error)."""
    try:
        q(c, sql, args)
        return True, ""
    except pymysql.MySQLError as exc:
        return False, f"{exc.args[0]}: {exc.args[-1]}"


# ---------------------------------------------------------------- escenarios
def alta_plantel(c, equipo, torneo, cedulas):
    for numero, ci in enumerate(cedulas, start=1):
        q(c, "INSERT INTO equipo_jugador_torneo (id_equipo,ci_jugador,id_torneo,numero_camiseta) "
             "VALUES (%s,%s,%s,%s)", (equipo, ci, torneo, numero))


def edicion_prueba(c, cerrar_inscripcion=True):
    """Crea la edicion 2 con los equipos 11 a 14 (facultades 1 a 4) y planteles validos."""
    q(c, "INSERT INTO torneo (id_torneo,nombre,anio,semestre,fecha_inicio,fecha_fin,estado) VALUES "
         "(2,'Prueba',2027,1,'2026-10-01','2027-06-30','inscripcion')")
    q(c, "INSERT INTO equipo (id_equipo,nombre,id_torneo,id_facultad,ci_capitan) VALUES "
         "(11,'A',2,1,'11111111'),(12,'B',2,2,'22222221'),(13,'C',2,3,'33333331'),(14,'D',2,4,'44444441')")
    for equipo, facultad in ((11, 1), (12, 2), (13, 3), (14, 4)):
        alta_plantel(c, equipo, 2, FACULTAD[facultad])
    if cerrar_inscripcion:
        q(c, "UPDATE torneo SET estado='en curso' WHERE id_torneo=2")


def alta_partido(c, id_partido, fecha, local, visitante, dia, turno=1, cancha="Cancha 1",
                 complejo=1, estado="programado", torneo=2):
    q(c, "INSERT INTO partido (id_partido,id_torneo,numero_fecha,id_equipo_local,id_equipo_visitante,"
         "dia,id_turno,nombre_cancha,id_complejo,estado) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
      (id_partido, torneo, fecha, local, visitante, dia, turno, cancha, complejo, estado))


def firmar(c, id_partido, equipo, cedulas):
    for ci in cedulas:
        q(c, "INSERT INTO planilla_partido (id_partido,ci_jugador,id_equipo) VALUES (%s,%s,%s)",
          (id_partido, ci, equipo))


def mover_reloj(c, fecha_hora):
    """Cambia NOW() solo en esta sesion, para probar la ventana de 48 horas."""
    q(c, "SET TIMESTAMP=UNIX_TIMESTAMP(%s)", (fecha_hora,))


# ---------------------------------------------------------------- defectos conocidos
def defecto(codigo, obtenido):
    """Marca una prueba que hoy no se cumple por un defecto o limitacion ya conocida.

    La prueba afirma el comportamiento DESEADO. Mientras el defecto exista figura como
    'Defecto conocido'; cuando se corrija aparece como 'Corregido' y hay que quitar la marca.
    """
    def aplicar(funcion):
        funcion.defecto = (codigo, obtenido)
        return unittest.expectedFailure(funcion)
    return aplicar


# ---------------------------------------------------------------- clases base
class _Afirmaciones:
    def rechaza(self, sql, texto=None, args=None, conexion=None):
        """Afirma que MySQL rechaza la sentencia y, si se indica, con ese texto."""
        ok, mensaje = intentar(conexion or self.c, sql, args)
        self.assertFalse(ok, f"Se esperaba un rechazo y fue aceptada: {sql}")
        if texto:
            self.assertIn(texto.lower(), mensaje.lower())
        return mensaje

    def acepta(self, sql, args=None, conexion=None):
        ok, mensaje = intentar(conexion or self.c, sql, args)
        self.assertTrue(ok, f"Se esperaba que se aceptara y dio: {mensaje}")


class CasoTransaccional(_Afirmaciones, unittest.TestCase):
    """Cada prueba corre en una transaccion que se revierte al final: rapido y aislado.

    Sirve para casos que usan una sola conexion y no ejecutan DDL.
    """
    @classmethod
    def setUpClass(cls):
        asegurar_datos()

    def setUp(self):
        self.c = conectar(autocommit=False)
        self.addCleanup(self._cerrar)

    def _cerrar(self):
        self.c.rollback()
        self.c.close()


class CasoAislado(_Afirmaciones, unittest.TestCase):
    """Reinstala la base antes de cada prueba. Para casos con varias conexiones o con commit."""
    def setUp(self):
        global _base_modificada
        restaurar()
        _base_modificada = True
        self.c = conectar()
        self.addCleanup(self.c.close)


# ---------------------------------------------------------------- aplicacion web
_flask = None


def app_flask():
    """Importa la app real apuntando al servidor temporal, sin usar ningun .env."""
    global _flask
    if _flask is None:
        os.environ.update({
            "DB_HOST": "127.0.0.1", "DB_PORT": str(servidor().puerto), "DB_NAME": "torneo_futbol5",
            "DB_LOGIN_USER": CUENTA_LOGIN[0], "DB_LOGIN_PASSWORD": CUENTA_LOGIN[1],
            "DB_ADMIN_USER": CUENTA_ADMIN[0], "DB_ADMIN_PASSWORD": CUENTA_ADMIN[1],
            "DB_PLAN_USER": CUENTA_PLANILLERO[0], "DB_PLAN_PASSWORD": CUENTA_PLANILLERO[1],
            "APP_SECRET_KEY": "clave-solo-para-pruebas-automatizadas",
        })
        sys.path.insert(0, str(RAIZ / "app"))
        import app as modulo
        _flask = modulo
    return _flask


class _Campos(HTMLParser):
    """Lee el formulario de edicion tal como lo enviaria un navegador."""
    def __init__(self):
        super().__init__()
        self.dentro = False
        self.campos = {}
        self.select = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "form" and "edit-grid" in (a.get("class") or ""):
            self.dentro = True
        if not self.dentro:
            return
        if tag == "input" and a.get("name") and "disabled" not in a:
            self.campos[a["name"]] = a.get("value", "")
        if tag == "select" and a.get("name"):
            self.select = a["name"]
            self.campos[self.select] = ""
        if tag == "option" and self.select and "selected" in a:
            self.campos[self.select] = a.get("value", "")

    def handle_endtag(self, tag):
        if tag == "select":
            self.select = None
        if tag == "form":
            self.dentro = False


def campos_formulario(texto):
    lector = _Campos()
    lector.feed(texto)
    return lector.campos


def token(texto):
    hallado = re.search(r'name="csrf_token" value="([^"]+)"', texto)
    return hallado.group(1) if hallado else ""


def avisos(texto):
    return [html.unescape(m) for m in re.findall(r'<div class="notice[^"]*">(.*?)</div>', texto, re.S)]


class CasoWeb(CasoAislado):
    """Prueba la app real con el cliente de Flask, contra MySQL real y con las cuentas reales."""
    def setUp(self):
        super().setUp()
        self.modulo = app_flask()
        self.app = self.modulo.app

    def ingresar(self, cuenta):
        """Inicia sesion y devuelve (cliente, respuesta)."""
        cliente = self.app.test_client()
        pagina = cliente.get("/login")
        respuesta = cliente.post("/login", data={"csrf_token": token(pagina.text),
                                                 "correo": cuenta[0], "password": cuenta[1]})
        return cliente, respuesta

    def enviar(self, cliente, url, datos=None, desde="/", seguir=True):
        """Hace un POST con token CSRF valido, tomado de la pagina 'desde'."""
        campos = dict(datos or {})
        campos.setdefault("csrf_token", token(cliente.get(desde).text))
        return cliente.post(url, data=campos, follow_redirects=seguir)

    def guardar_edicion(self, cliente, url, **cambios):
        """Abre un formulario de edicion, cambia campos y lo envia como un navegador."""
        campos = campos_formulario(cliente.get(url).text)
        campos.update(cambios)
        return cliente.post(url, data=campos, follow_redirects=True)
