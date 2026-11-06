"""Acceso a la aplicación web: ingreso, token CSRF, permisos por rol y sesiones vivas."""
import functools
import importlib.util
import os
import re
import sys

from flask import Flask
from flask.sessions import SecureCookieSessionInterface

from base import (RAIZ, WEB_ADMIN, WEB_PLANILLERO, CasoWeb, avisos, defecto, puerto_libre, q, token,
                  valor)

ERROR_DE_INGRESO = "Usuario o contraseña incorrectos."
BAJA_DEL_PLANILLERO = "/catalogo/login/planillero@ucu.edu.uy/eliminar"
SOLO_ADMINISTRADOR = ("/catalogo/jugador", "/catalogo/login", "/catalogo/partido/nuevo",
                      "/catalogo/login/admin@ucu.edu.uy/editar")


def clave_de_ejemplo():
    texto = (RAIZ / ".env.example").read_text(encoding="utf-8")
    return re.search(r"^APP_SECRET_KEY=(.+)$", texto, re.M).group(1).strip()


def cookie_de_administrador(clave):
    """Sesión de administrador firmada con esa clave, sin haber pasado por el login."""
    emisor = Flask("falsificador")
    emisor.secret_key = clave
    firmante = SecureCookieSessionInterface().get_signing_serializer(emisor)
    return firmante.dumps({"user": {"correo": WEB_ADMIN[0], "rol": "administrador"}, "csrf": "x"})


class CasoAcceso(CasoWeb):
    def sin_registro(self):
        """Evita que los errores esperados de la app llenen la salida de las pruebas."""
        registro = self.app.logger
        self.addCleanup(setattr, registro, "disabled", registro.disabled)
        registro.disabled = True

    def caer_base(self):
        """Apunta la app a un puerto cerrado y devuelve la función que la reconecta."""
        config = sys.modules["db"].CONFIG
        reconectar = functools.partial(config.__setitem__, "port", config["port"])
        self.addCleanup(reconectar)
        config["port"] = puerto_libre()
        return reconectar

    def va_a_login(self, respuesta):
        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(respuesta.location, "/login")

    def existe_el_planillero(self):
        return valor(self.c, "SELECT COUNT(*) FROM login WHERE correo=%s", (WEB_PLANILLERO[0],)) == 1

    def administradores(self):
        return valor(self.c, "SELECT COUNT(*) FROM login WHERE rol='administrador'")


class Ingreso(CasoAcceso):
    def test_anonimo_redirigido(self):
        """CP-ACC-01 | Visitante anónimo no entra a páginas protegidas | GET a inicio, partidos, reportes y gestión sin sesión | Redirección a /login en todas"""
        cliente = self.app.test_client()
        for url in ("/", "/partidos", "/partidos/1", "/reportes", "/reportes/posiciones", *SOLO_ADMINISTRADOR):
            self.va_a_login(cliente.get(url))

    def test_anonimo_no_modifica_datos(self):
        """CP-ACC-02 | Visitante anónimo no modifica datos | POST de baja de usuario con el token de /login | Redirección a /login y el usuario sigue"""
        cliente = self.app.test_client()
        self.va_a_login(self.enviar(cliente, BAJA_DEL_PLANILLERO, desde="/login", seguir=False))
        self.assertTrue(self.existe_el_planillero())

    def test_ingreso_administrador(self):
        """CP-ACC-03 | Ingreso correcto del administrador | Correo y contraseña válidos | Redirige al inicio con Reportes y Gestión en el menú"""
        cliente, respuesta = self.ingresar(WEB_ADMIN)
        self.assertEqual((respuesta.status_code, respuesta.location), (302, "/"))
        inicio = cliente.get("/").text
        self.assertIn(">Reportes</a>", inicio)
        self.assertIn(">Gestión</a>", inicio)

    def test_ingreso_planillero(self):
        """CP-ACC-04 | Ingreso correcto del planillero | Correo y contraseña válidos | Redirige al inicio sin Reportes ni Gestión en el menú"""
        cliente, respuesta = self.ingresar(WEB_PLANILLERO)
        self.assertEqual((respuesta.status_code, respuesta.location), (302, "/"))
        inicio = cliente.get("/").text
        self.assertIn(">Partidos</a>", inicio)
        self.assertNotIn(">Reportes</a>", inicio)
        self.assertNotIn(">Gestión</a>", inicio)

    def test_correo_normalizado(self):
        """CP-ACC-05 | El correo ignora mayúsculas y espacios | Correo en mayúsculas con espacios alrededor | Ingreso correcto"""
        _, respuesta = self.ingresar(("  ADMIN@UCU.EDU.UY ", WEB_ADMIN[1]))
        self.assertEqual((respuesta.status_code, respuesta.location), (302, "/"))

    def test_error_generico(self):
        """CP-ACC-06 | El error de ingreso no revela si la cuenta existe | Clave incorrecta y correo inexistente | Mismo mensaje genérico y sin sesión"""
        cliente, clave_mala = self.ingresar((WEB_ADMIN[0], "incorrecta"))
        _, sin_cuenta = self.ingresar(("nadie@ucu.edu.uy", "incorrecta"))
        self.assertEqual(clave_mala.status_code, 200)
        self.assertEqual(sin_cuenta.status_code, 200)
        self.assertEqual(avisos(clave_mala.text), [ERROR_DE_INGRESO])
        self.assertEqual(avisos(sin_cuenta.text), [ERROR_DE_INGRESO])
        self.va_a_login(cliente.get("/"))

    def test_login_con_sesion_activa(self):
        """CP-ACC-07 | Login con sesión activa vuelve al inicio | GET a /login ya autenticado | Redirección al inicio"""
        cliente, _ = self.ingresar(WEB_PLANILLERO)
        respuesta = cliente.get("/login")
        self.assertEqual((respuesta.status_code, respuesta.location), (302, "/"))

    def test_cookie_protegida(self):
        """CP-ACC-08 | Cookie de sesión protegida | Leer Set-Cookie tras ingresar | Incluye HttpOnly y SameSite=Lax"""
        _, respuesta = self.ingresar(WEB_ADMIN)
        cookie = respuesta.headers["Set-Cookie"]
        self.assertIn("HttpOnly", cookie)
        self.assertIn("SameSite=Lax", cookie)

    def test_cookie_con_otra_clave(self):
        """CP-ACC-09 | Cookie firmada con otra clave no abre sesión | Cookie de administrador firmada con una clave ajena | Redirección a /login"""
        cliente = self.app.test_client()
        cliente.set_cookie("session", cookie_de_administrador("una-clave-ajena"), domain="localhost")
        self.va_a_login(cliente.get("/catalogo/login"))


class TokenCsrf(CasoAcceso):
    def test_post_sin_token(self):
        """CP-ACC-10 | POST sin token CSRF se rechaza | Baja de usuario sin csrf_token | HTTP 400, aviso de formulario vencido y el usuario sigue"""
        cliente, _ = self.ingresar(WEB_ADMIN)
        respuesta = cliente.post(BAJA_DEL_PLANILLERO, data={})
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("Formulario vencido", respuesta.text)
        self.assertTrue(self.existe_el_planillero())

    def test_token_de_otra_sesion(self):
        """CP-ACC-11 | Token CSRF de otra sesión se rechaza | Baja de usuario con el token de otro cliente | HTTP 400 y el usuario sigue"""
        cliente, _ = self.ingresar(WEB_ADMIN)
        otro, _ = self.ingresar(WEB_ADMIN)
        ajeno = token(otro.get("/").text)
        self.assertEqual(cliente.post(BAJA_DEL_PLANILLERO, data={"csrf_token": ajeno}).status_code, 400)
        self.assertTrue(self.existe_el_planillero())

    def test_token_previo_al_ingreso(self):
        """CP-ACC-12 | El token anterior al ingreso deja de valer | POST de salida con el token de la página de login | HTTP 400 y la sesión sigue activa"""
        cliente = self.app.test_client()
        previo = token(cliente.get("/login").text)
        cliente.post("/login", data={"csrf_token": previo, "correo": WEB_ADMIN[0], "password": WEB_ADMIN[1]})
        self.assertEqual(cliente.post("/logout", data={"csrf_token": previo}).status_code, 400)
        self.assertEqual(cliente.get("/").status_code, 200)

    def test_login_sin_token(self):
        """CP-ACC-13 | Login sin token CSRF se rechaza | POST a /login con credenciales válidas y sin token | HTTP 400 y sin sesión"""
        cliente = self.app.test_client()
        respuesta = cliente.post("/login", data={"correo": WEB_ADMIN[0], "password": WEB_ADMIN[1]})
        self.assertEqual(respuesta.status_code, 400)
        self.va_a_login(cliente.get("/"))

    def test_salida_por_post(self):
        """CP-ACC-14 | Salida por POST cierra la sesión | POST a /logout con token válido | Redirección a /login y el inicio vuelve a pedir ingreso"""
        cliente, _ = self.ingresar(WEB_ADMIN)
        self.va_a_login(self.enviar(cliente, "/logout", seguir=False))
        self.va_a_login(cliente.get("/"))

    def test_salida_por_get(self):
        """CP-ACC-15 | Salida por GET no está permitida | GET a /logout | HTTP 405 y la sesión sigue activa"""
        cliente, _ = self.ingresar(WEB_ADMIN)
        self.assertEqual(cliente.get("/logout").status_code, 405)
        self.assertEqual(cliente.get("/").status_code, 200)


class Permisos(CasoAcceso):
    def test_planillero_consulta_partidos(self):
        """CP-ACC-16 | Planillero consulta inicio y partidos | GET a inicio, fixture y planilla | HTTP 200 en todas"""
        cliente, _ = self.ingresar(WEB_PLANILLERO)
        for url in ("/", "/partidos", "/partidos/1"):
            self.assertEqual(cliente.get(url).status_code, 200)

    def test_planillero_sin_reportes(self):
        """CP-ACC-17 | Planillero bloqueado en reportes | GET al índice y a un reporte | HTTP 403 con la página de permisos"""
        cliente, _ = self.ingresar(WEB_PLANILLERO)
        for url in ("/reportes", "/reportes/posiciones"):
            respuesta = cliente.get(url)
            self.assertEqual(respuesta.status_code, 403)
            self.assertIn("No tiene permisos", respuesta.text)

    def test_planillero_sin_gestion(self):
        """CP-ACC-18 | Planillero bloqueado en gestión | GET a listado, alta y edición de catálogos | HTTP 403 en todas"""
        cliente, _ = self.ingresar(WEB_PLANILLERO)
        for url in SOLO_ADMINISTRADOR:
            self.assertEqual(cliente.get(url).status_code, 403)

    def test_planillero_no_escribe_en_gestion(self):
        """CP-ACC-19 | Planillero no escribe en gestión | POST de alta, edición y baja de usuarios con token válido | HTTP 403 y la tabla sin cambios"""
        cliente, _ = self.ingresar(WEB_PLANILLERO)
        antes = q(self.c, "SELECT * FROM login")
        datos = {"correo": "intruso@ucu.edu.uy", "contrasena": "ClaveDelIntruso", "rol": "administrador"}
        for url in ("/catalogo/login/nuevo", "/catalogo/login/admin@ucu.edu.uy/editar",
                    "/catalogo/login/admin@ucu.edu.uy/eliminar"):
            self.assertEqual(self.enviar(cliente, url, datos).status_code, 403)
        self.assertEqual(q(self.c, "SELECT * FROM login"), antes)

    def test_administrador_entra_a_todo(self):
        """CP-ACC-20 | Administrador entra a reportes y gestión | GET a reportes y a los catálogos | HTTP 200 en todas"""
        cliente, _ = self.ingresar(WEB_ADMIN)
        for url in ("/reportes", "/reportes/posiciones", *SOLO_ADMINISTRADOR):
            self.assertEqual(cliente.get(url).status_code, 200)

    def test_paginas_de_error(self):
        """CP-ACC-21 | Errores 403 y 404 con página propia | Catálogo inexistente como planillero y como administrador | HTTP 403 y 404 con el mensaje de la aplicación"""
        planillero, _ = self.ingresar(WEB_PLANILLERO)
        administrador, _ = self.ingresar(WEB_ADMIN)
        prohibido = planillero.get("/catalogo/nada")
        inexistente = administrador.get("/catalogo/nada")
        self.assertEqual(prohibido.status_code, 403)
        self.assertIn("No tiene permisos para acceder a esta sección.", prohibido.text)
        self.assertEqual(inexistente.status_code, 404)
        self.assertIn("No se encontró la página o el registro.", inexistente.text)


class SesionViva(CasoAcceso):
    def test_ascenso_de_rol(self):
        """CP-ACC-22 | Ascenso de rol se aplica en la sesión viva | Pasar al planillero a administrador y pedir reportes | HTTP 200 sin volver a ingresar"""
        cliente, _ = self.ingresar(WEB_PLANILLERO)
        self.assertEqual(cliente.get("/reportes").status_code, 403)
        q(self.c, "UPDATE login SET rol='administrador' WHERE correo=%s", (WEB_PLANILLERO[0],))
        self.assertEqual(cliente.get("/reportes").status_code, 200)

    def test_descenso_de_rol(self):
        """CP-ACC-23 | Descenso de rol se aplica en la sesión viva | Pasar al administrador a planillero y pedir reportes | HTTP 403 sin volver a ingresar"""
        cliente, _ = self.ingresar(WEB_ADMIN)
        self.assertEqual(cliente.get("/reportes").status_code, 200)
        q(self.c, "UPDATE login SET rol='planillero' WHERE correo=%s", (WEB_ADMIN[0],))
        self.assertEqual(cliente.get("/reportes").status_code, 403)

    def test_cuenta_borrada(self):
        """CP-ACC-24 | Cuenta borrada pierde la sesión viva | Eliminar la cuenta y pedir el inicio | Redirección a /login"""
        cliente, _ = self.ingresar(WEB_PLANILLERO)
        self.assertEqual(cliente.get("/").status_code, 200)
        q(self.c, "DELETE FROM login WHERE correo=%s", (WEB_PLANILLERO[0],))
        self.va_a_login(cliente.get("/"))

    def test_base_caida_no_conserva_privilegios(self):
        """CP-ACC-25 | Base caída no conserva privilegios | Sesión de administrador con MySQL inaccesible | Redirección a /login y la sesión no vuelve con la base"""
        cliente, _ = self.ingresar(WEB_ADMIN)
        self.assertEqual(cliente.get("/catalogo/login").status_code, 200)
        reconectar = self.caer_base()
        self.va_a_login(cliente.get("/catalogo/login"))
        reconectar()
        self.va_a_login(cliente.get("/catalogo/login"))

    def test_login_con_base_caida(self):
        """CP-ACC-26 | Login con la base caída informa el problema | Ingresar con MySQL inaccesible | Aviso de conexión, sin error 500"""
        self.sin_registro()
        self.caer_base()
        _, respuesta = self.ingresar(WEB_ADMIN)
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("No se pudo conectar a MySQL", " ".join(avisos(respuesta.text)))


class DefectosDeAcceso(CasoAcceso):
    def app_con_clave(self, clave):
        """Carga otra copia de app/app.py, como si el servidor arrancara con esa APP_SECRET_KEY."""
        self.addCleanup(os.environ.__setitem__, "APP_SECRET_KEY", os.environ["APP_SECRET_KEY"])
        os.environ["APP_SECRET_KEY"] = clave
        especificacion = importlib.util.spec_from_file_location("app_con_otra_clave", RAIZ / "app" / "app.py")
        copia = importlib.util.module_from_spec(especificacion)
        sys.modules[especificacion.name] = copia   # Flask ubica templates/ a partir de este módulo.
        self.addCleanup(sys.modules.pop, especificacion.name)
        especificacion.loader.exec_module(copia)
        return copia.app

    @defecto("APP-01", "Error 500 al comparar una contraseña con ñ.")
    def test_clave_incorrecta_no_ascii(self):
        """CP-ACC-27 | Clave incorrecta con ñ da el error genérico | Ingresar con la contraseña «contraseña» | Mensaje genérico, sin error 500"""
        self.sin_registro()
        _, respuesta = self.ingresar((WEB_ADMIN[0], "contraseña"))
        self.assertEqual(avisos(respuesta.text), [ERROR_DE_INGRESO])

    @defecto("APP-01", "Error 500: una cuenta con ñ en la clave no puede ingresar.")
    def test_cuenta_con_clave_no_ascii(self):
        """CP-ACC-28 | Cuenta con ñ en la clave puede ingresar | Crear la cuenta e ingresar con su clave correcta | Ingreso correcto"""
        self.sin_registro()
        cuenta = ("enie@ucu.edu.uy", "ContraseñaLarga")
        q(self.c, "INSERT INTO login (correo,contrasena,rol) VALUES (%s,%s,'planillero')", cuenta)
        _, respuesta = self.ingresar(cuenta)
        self.assertEqual(respuesta.status_code, 302)

    @defecto("APP-01", "Error 500 al comparar un token CSRF no ASCII.")
    def test_token_no_ascii(self):
        """CP-ACC-29 | Token CSRF no ASCII se rechaza como vencido | POST de salida con el token «ñandú» | HTTP 400, sin error 500"""
        self.sin_registro()
        cliente, _ = self.ingresar(WEB_ADMIN)
        self.assertEqual(cliente.post("/logout", data={"csrf_token": "ñandú"}).status_code, 400)

    @defecto("APP-03", "Se aceptó: la cuenta se eliminó y el sistema quedó sin administradores.")
    def test_ultimo_administrador_no_se_elimina(self):
        """CP-ACC-30 | El último administrador no elimina su cuenta | Baja de la propia cuenta desde Usuarios | Rechazo: queda al menos un administrador"""
        cliente, _ = self.ingresar(WEB_ADMIN)
        self.enviar(cliente, "/catalogo/login/admin@ucu.edu.uy/eliminar")
        self.assertEqual(self.administradores(), 1)

    @defecto("APP-03", "Se aceptó: la cuenta pasó a planillero y el sistema quedó sin administradores.")
    def test_ultimo_administrador_no_se_degrada(self):
        """CP-ACC-31 | El último administrador no pierde su rol | Editar la propia cuenta y elegir el rol planillero | Rechazo: queda al menos un administrador"""
        cliente, _ = self.ingresar(WEB_ADMIN)
        self.guardar_edicion(cliente, "/catalogo/login/admin@ucu.edu.uy/editar", rol="planillero")
        self.assertEqual(self.administradores(), 1)

    @defecto("APP-04", "Se aceptó: la cookie forjada abrió el listado de usuarios sin iniciar sesión.")
    def test_clave_de_ejemplo(self):
        """CP-ACC-32 | La clave de ejemplo no permite falsificar sesiones | Arrancar con la APP_SECRET_KEY de .env.example y forjar una cookie de administrador | La app no arranca o rechaza la cookie"""
        ejemplo = clave_de_ejemplo()
        try:
            app = self.app_con_clave(ejemplo)
        except (RuntimeError, SystemExit):
            return   # Negarse a arrancar también impide falsificar sesiones.
        cliente = app.test_client()
        cliente.set_cookie("session", cookie_de_administrador(ejemplo), domain="localhost")
        self.va_a_login(cliente.get("/catalogo/login"))

    @defecto("APP-05", "Error 500 con la página genérica del servidor, sin la plantilla de la aplicación.")
    def test_falta_clave_de_cuenta_de_rol(self):
        """CP-ACC-33 | Falta la clave de una cuenta de rol | Quitar DB_PLAN_PASSWORD y abrir el fixture como planillero | Página propia de la aplicación, no la genérica del servidor"""
        self.sin_registro()
        cliente, _ = self.ingresar(WEB_PLANILLERO)
        self.addCleanup(os.environ.__setitem__, "DB_PLAN_PASSWORD", os.environ.pop("DB_PLAN_PASSWORD"))
        self.assertIn("Sistema de gestión del Torneo", cliente.get("/partidos").text)
