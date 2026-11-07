"""Pruebas de la aplicación web Flask, los reportes de app/reports.py y consultas.sql."""
import re
import sys
import unittest
from datetime import date, timedelta
from decimal import Decimal

from base import (
    ROOT_DIR,
    SCRIPTS_DIR,
    WEB_ADMIN,
    WEB_PLANILLERO,
    TestBD,
    TestWeb,
    crear_edicion_prueba,
    firmar_planilla,
    insertar_partido,
)

APP_DIR = str(ROOT_DIR / "app")
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)
from reports import REPORTS


def normalizar_fila(row):
    out = []
    for val in row.values():
        if isinstance(val, Decimal):
            out.append(float(val))
        elif isinstance(val, timedelta):
            out.append(str(val))
        else:
            out.append(val)
    return tuple(out)


class TestAppWeb(TestWeb):
    def test_rutas_protegidas_redirigen_a_login(self):
        client = self.app.test_client()
        for ruta in ("/", "/partidos", "/partidos/1", "/reportes", "/catalogo/jugador"):
            resp = client.get(ruta)
            self.assertEqual(resp.status_code, 302)
            self.assertEqual(resp.location, "/login")

    def test_login_menu_por_rol_y_logout(self):
        _, resp_mal = self.login((WEB_ADMIN[0], "clave_erronea"))
        self.assertEqual(resp_mal.status_code, 200)
        self.assertIn("Usuario o contraseña incorrectos.", resp_mal.text)

        admin, resp_admin = self.login(WEB_ADMIN)
        self.assertEqual((resp_admin.status_code, resp_admin.location), (302, "/"))
        home_admin = admin.get("/").text
        self.assertIn(">Reportes</a>", home_admin)
        self.assertIn(">Gestión</a>", home_admin)

        planillero, resp_plan = self.login(WEB_PLANILLERO)
        self.assertEqual((resp_plan.status_code, resp_plan.location), (302, "/"))
        home_plan = planillero.get("/").text
        self.assertIn(">Partidos</a>", home_plan)
        self.assertNotIn(">Reportes</a>", home_plan)
        self.assertNotIn(">Gestión</a>", home_plan)

        resp_out = self.post_csrf(admin, "/logout", follow=False)
        self.assertEqual((resp_out.status_code, resp_out.location), (302, "/login"))
        self.assertEqual(admin.get("/").status_code, 302)

    def test_control_csrf_en_formularios(self):
        admin, _ = self.login(WEB_ADMIN)
        resp = admin.post("/catalogo/facultad/nuevo", data={"nombre": "SinToken"})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("Formulario vencido", resp.text)
        self.assertEqual(admin.get("/logout").status_code, 405)

    def test_permisos_web_planillero(self):
        planillero, _ = self.login(WEB_PLANILLERO)
        self.assertEqual(planillero.get("/partidos").status_code, 200)
        self.assertEqual(planillero.get("/partidos/1").status_code, 200)
        self.assertEqual(planillero.get("/reportes").status_code, 403)
        self.assertEqual(planillero.get("/reportes/posiciones").status_code, 403)
        self.assertEqual(planillero.get("/catalogo/jugador").status_code, 403)
        self.assertEqual(self.post_csrf(planillero, "/catalogo/facultad/nuevo", {"nombre": "X"}).status_code, 403)

    def test_abm_catalogos_y_validaciones(self):
        admin, _ = self.login(WEB_ADMIN)

        # Alta, edición y baja de una facultad sin dependencias
        resp_alta = self.post_csrf(admin, "/catalogo/facultad/nuevo", {"nombre": "Enfermeria"})
        self.assertIn("Registro creado correctamente.", resp_alta.text)
        id_fac = self.scalar("SELECT id_facultad FROM facultad WHERE nombre='Enfermeria'")
        self.assertIsNotNone(id_fac)

        resp_edit = self.post_csrf(admin, f"/catalogo/facultad/{id_fac}/editar", {"nombre": "Odontologia"})
        self.assertIn("Registro actualizado.", resp_edit.text)
        self.assertEqual(self.scalar("SELECT nombre FROM facultad WHERE id_facultad=%s", (id_fac,)), "Odontologia")

        resp_baja = self.post_csrf(admin, f"/catalogo/facultad/{id_fac}/eliminar")
        self.assertIn("Registro eliminado.", resp_baja.text)

        # No permite borrar una facultad con equipos asociados ni crear registros inválidos
        resp_fk = self.post_csrf(admin, "/catalogo/facultad/1/eliminar")
        self.assertIn("Cannot delete or update a parent row", resp_fk.text)

        resp_inv = self.post_csrf(
            admin,
            "/catalogo/torneo/nuevo",
            {
                "nombre": "Torneo Mal",
                "anio": "2027",
                "semestre": "1",
                "fecha_inicio": "2027-08-01",
                "fecha_fin": "2027-03-01",
                "estado": "inscripcion",
            },
        )
        self.assertIn("La fecha de inicio debe ser anterior o igual a la final.", resp_inv.text)

        # Las sanciones automáticas no son editables desde el catálogo de administración
        id_roja = self.scalar("SELECT id_sancion FROM sancion_jugador WHERE motivo='roja'")
        self.assertEqual(admin.get(f"/catalogo/sancion_jugador/{id_roja}/editar").status_code, 403)

    def test_flujo_planillero_carga_partido_y_cierre(self):
        ayer = (date.today() - timedelta(days=1)).isoformat()
        crear_edicion_prueba(self.conn, en_curso=True)
        insertar_partido(self.conn, 101, 1, 11, 12, ayer, turno=1)
        insertar_partido(self.conn, 102, 2, 11, 13, ayer, turno=2)
        firmar_planilla(self.conn, 101, 11, ["11111112"])
        firmar_planilla(self.conn, 101, 12, ["22222222"])

        planillero, _ = self.login(WEB_PLANILLERO)

        resp = self.post_csrf(planillero, "/partidos/101/planilla", {"ci": "11111113", "equipo": "11"})
        self.assertIn("Jugador añadido a la planilla.", resp.text)

        resp = self.post_csrf(planillero, "/partidos/101/gol", {"ci_jugador": "11111112", "minuto": "14", "autogol": "0"})
        self.assertIn("Evento registrado correctamente.", resp.text)

        resp = self.post_csrf(planillero, "/partidos/101/gol", {"ci_jugador": "22222222", "minuto": "28", "autogol": "1"})
        self.assertIn("Evento registrado correctamente.", resp.text)

        # Roja en la fecha 1 suspende al jugador en la fecha 2
        resp = self.post_csrf(planillero, "/partidos/101/tarjeta", {"ci_jugador": "11111112", "minuto": "35", "color": "roja"})
        self.assertIn("Evento registrado correctamente.", resp.text)
        self.assertIn("Suspendido", planillero.get("/partidos/102").text)

        resp_susp = self.post_csrf(planillero, "/partidos/102/planilla", {"ci": "11111112", "equipo": "11"})
        self.assertIn("suspendido", resp_susp.text)

        resp_fin = self.post_csrf(planillero, "/partidos/101/finalizar")
        self.assertIn("Partido marcado como jugado.", resp_fin.text)
        self.assertIn("2 : 0", resp_fin.text)
        self.assertEqual(self.scalar("SELECT estado FROM partido WHERE id_partido=101"), "jugado")

    def test_bloqueo_web_partido_futuro_y_ventana_vencida(self):
        futuro = (date.today() + timedelta(days=15)).isoformat()
        crear_edicion_prueba(self.conn, en_curso=True)
        insertar_partido(self.conn, 103, 1, 11, 12, futuro, turno=1)

        planillero, _ = self.login(WEB_PLANILLERO)
        resp_fut = self.post_csrf(planillero, "/partidos/103/planilla", {"ci": "11111111", "equipo": "11"})
        self.assertIn("La planilla de juego solo se registra una vez terminado el turno.", resp_fut.text)

        resp_venc = self.post_csrf(planillero, "/partidos/1/gol", {"ci_jugador": "11111111", "minuto": "10", "autogol": "0"})
        self.assertIn("La ventana de 48 horas para correcciones terminó.", resp_venc.text)

    def test_pantallas_de_reportes(self):
        admin, _ = self.login(WEB_ADMIN)
        self.assertEqual(admin.get("/reportes").status_code, 200)
        for slug, (titulo, _, _) in REPORTS.items():
            resp = admin.get(f"/reportes/{slug}?torneo=1&fecha=2")
            self.assertEqual(resp.status_code, 200, slug)
            self.assertIn(titulo, resp.text)


class TestReportesYConsultasSQL(TestBD):
    def ejecutar_reporte(self, slug, torneo=1, fecha=2):
        rows = self.query(REPORTS[slug][2], {"torneo": torneo, "fecha": fecha})
        return [normalizar_fila(r) for r in rows]

    def test_reportes_con_datos_de_prueba(self):
        posiciones = self.ejecutar_reporte("posiciones")
        self.assertEqual(len(posiciones), 6)
        self.assertEqual(posiciones[0], ("Ingenieria FC", 3, 3, 0, 0, 4, 1, 3, 9))
        self.assertEqual(posiciones[-1], ("Psicologia Sporting", 3, 0, 0, 3, 0, 4, -4, 0))

        goleadores = self.ejecutar_reporte("goleadores")
        self.assertEqual(goleadores[:2], [
            ("22222221", "Sofia Martinez", "Administracion United", 3),
            ("11111111", "Juan Perez", "Ingenieria FC", 3),
        ])

        fairplay = self.ejecutar_reporte("fairplay")
        self.assertEqual(fairplay[-1], ("Psicologia Sporting", 0, 1, 3))

        self.assertEqual(self.ejecutar_reporte("goles_fecha"), [(1, 3, 6, 2.0), (2, 3, 3, 1.0), (3, 3, 3, 1.0)])
        self.assertEqual(self.ejecutar_reporte("goles_global"), [(9, 12, 1.33)])
        self.assertEqual(
            self.ejecutar_reporte("sin_planilla"),
            [("Ingenieria FC", "11111116", "Ana Fernandez", "docente")],
        )
        self.assertEqual(len(self.ejecutar_reporte("asistencia")), 6)
        self.assertEqual(len(self.ejecutar_reporte("inhabilitados", fecha=2)), 2)
        self.assertEqual(len(self.ejecutar_reporte("inhabilitados", fecha=3)), 1)
        self.assertEqual(self.ejecutar_reporte("inhabilitados", fecha=4), [])
        self.assertEqual(self.ejecutar_reporte("estados"), [(15, 9, 1, 0, 5, 60.0, 6.67)])

    def test_autogoles_y_partidos_sin_jugar_en_reportes(self):
        ayer = (date.today() - timedelta(days=1)).isoformat()
        crear_edicion_prueba(self.conn, en_curso=True)
        insertar_partido(self.conn, 101, 1, 11, 12, ayer, turno=1)
        insertar_partido(self.conn, 102, 1, 13, 14, ayer, turno=2)
        firmar_planilla(self.conn, 101, 11, ["11111111"])
        firmar_planilla(self.conn, 101, 12, ["22222221"])
        firmar_planilla(self.conn, 102, 13, ["33333331"])

        # Partido 101 jugado: 1 gol de 11111111 + 1 autogol de 22222221 -> 2 a 0 para Ingenieria B
        self.execute("INSERT INTO gol (id_partido, ci_jugador, minuto, autogol) VALUES (101, '11111111', 10, 0)")
        self.execute("INSERT INTO gol (id_partido, ci_jugador, minuto, autogol) VALUES (101, '22222221', 20, 1)")
        self.execute("UPDATE partido SET estado='jugado' WHERE id_partido=101")

        # Gol en el partido 102 que sigue programado (no debe contarse)
        self.execute("INSERT INTO gol (id_partido, ci_jugador, minuto, autogol) VALUES (102, '33333331', 15, 0)")

        pos = {r[0]: r[1:] for r in self.ejecutar_reporte("posiciones", torneo=2)}
        self.assertEqual(pos["Ingenieria B"], (1, 1, 0, 0, 2, 0, 2, 3))
        self.assertEqual(pos["Administracion B"], (1, 0, 0, 1, 0, 2, -2, 0))
        self.assertEqual(pos["Derecho B"], (0, 0, 0, 0, 0, 0, 0, 0))

        self.assertEqual(
            self.ejecutar_reporte("goleadores", torneo=2),
            [("11111111", "Juan Perez", "Ingenieria B", 1)],
        )

    def test_consultas_sql_ejecutan_bajo_only_full_group_by(self):
        modo = self.scalar("SELECT @@SESSION.sql_mode")
        self.assertIn("ONLY_FULL_GROUP_BY", modo)

        contenido = (SCRIPTS_DIR / "consultas.sql").read_text(encoding="utf-8")
        sin_comentarios = re.sub(r"--[^\n]*", "", contenido)
        selects = [s.strip() for s in sin_comentarios.split(";") if s.strip().upper().startswith("SELECT")]
        self.assertEqual(len(selects), 17)

        for sql in selects:
            filas = self.query(sql)
            self.assertTrue(len(filas) > 0, f"Consulta vacía: {sql[:60]}")


if __name__ == "__main__":
    unittest.main()
