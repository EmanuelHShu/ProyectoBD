"""Pruebas de roles y privilegios de los usuarios de MySQL (seguridad-roles.sql)."""
import unittest
from datetime import date, timedelta
from base import (
    DB_ADMIN,
    DB_LOGIN,
    DB_PLANILLERO,
    TestBD,
    TestBDAislado,
    conectar,
    crear_edicion_prueba,
    firmar_planilla,
    insertar_partido,
)


class TestPermisosRolesSQL(TestBD):
    def setUp(self):
        super().setUp()
        self.conn_login = conectar(*DB_LOGIN, autocommit=False)
        self.conn_plan = conectar(*DB_PLANILLERO, autocommit=False)
        self.conn_admin = conectar(*DB_ADMIN, autocommit=False)

    def tearDown(self):
        for c in (self.conn_login, self.conn_plan, self.conn_admin):
            c.rollback()
            c.close()
        super().tearDown()

    def test_roles_activos_por_defecto(self):
        self.assertIn("rol_login", self.scalar("SELECT CURRENT_ROLE()", conn=self.conn_login))
        self.assertIn("rol_planillero", self.scalar("SELECT CURRENT_ROLE()", conn=self.conn_plan))
        self.assertIn("rol_administrador", self.scalar("SELECT CURRENT_ROLE()", conn=self.conn_admin))

    def test_usuario_login_solo_puede_leer_tabla_login(self):
        self.assertEqual(self.scalar("SELECT COUNT(*) FROM login", conn=self.conn_login), 2)

        for tabla in ("jugador", "partido", "equipo", "sancion_jugador", "v_resultado_partido"):
            self.assertErrorSQL(f"SELECT * FROM {tabla}", contiene="denied", conn=self.conn_login)

        self.assertErrorSQL(
            "INSERT INTO login VALUES ('otro@ucu.edu.uy', '1234', 'planillero')",
            contiene="denied",
            conn=self.conn_login,
        )
        self.assertErrorSQL("DELETE FROM login", contiene="denied", conn=self.conn_login)
        self.assertErrorSQL("CALL sp_marcar_partido_jugado(10)", contiene="denied", conn=self.conn_login)

    def test_planillero_no_accede_a_login_ni_modifica_catalogos(self):
        self.assertErrorSQL("SELECT * FROM login", contiene="denied", conn=self.conn_plan)

        sentencias_bloqueadas = (
            "INSERT INTO jugador VALUES ('99999999', 'A', 'B', 'a@b.uy', '2000-01-01', 1, 'grado')",
            "UPDATE partido SET estado='jugado' WHERE id_partido=10",
            "DELETE FROM partido WHERE id_partido=10",
            "INSERT INTO sancion_jugador (ci_jugador, id_torneo, motivo, numero_fecha_inicio, cantidad_fechas) "
            "VALUES ('11111111', 1, 'disciplinaria', 5, 1)",
            "DELETE FROM equipo",
            "DELETE FROM cancha",
            "CALL sp_recalcular_sanciones_automaticas('66666661', 1)",
        )
        for sql in sentencias_bloqueadas:
            self.assertErrorSQL(sql, contiene="denied", conn=self.conn_plan)

    def test_planillero_registra_planilla_goles_y_tarjetas(self):
        self.assertEqual(self.scalar("SELECT COUNT(*) FROM partido", conn=self.conn_plan), 15)
        res = self.query("SELECT goles_local, goles_visitante FROM v_resultado_partido WHERE id_partido=1", conn=self.conn_plan)[0]
        self.assertEqual((res["goles_local"], res["goles_visitante"]), (2, 1))

        # Carga sobre el partido 10 (fecha 4, programado)
        suplente = "11111114"
        self.execute(
            "INSERT INTO planilla_partido (id_partido, ci_jugador, id_equipo) VALUES (10, %s, 1)",
            (suplente,),
            conn=self.conn_plan,
        )
        self.execute(
            "INSERT INTO gol (id_partido, ci_jugador, minuto, autogol) VALUES (10, %s, 12, 0)",
            (suplente,),
            conn=self.conn_plan,
        )
        # Aunque planillero_user no escribe sancion_jugador directo, el trigger DEFINER crea la sanción
        self.execute(
            "INSERT INTO tarjeta (id_partido, ci_jugador, minuto, color) VALUES (10, %s, 25, 'roja')",
            (suplente,),
            conn=self.conn_plan,
        )
        self.assertEqual(
            self.scalar(
                "SELECT numero_fecha_inicio FROM sancion_jugador WHERE ci_jugador=%s AND id_torneo=1",
                (suplente,),
                conn=self.conn_plan,
            ),
            5,
        )

        # Tampoco puede modificar partidos cerrados fuera de las 48h
        self.assertErrorSQL(
            "INSERT INTO gol (id_partido, ci_jugador, minuto, autogol) VALUES (1, '11111111', 50, 0)",
            contiene="48 horas",
            conn=self.conn_plan,
        )

    def test_admin_user_opera_tablas_pero_no_usuarios_mysql(self):
        self.assertEqual(self.scalar("SELECT COUNT(*) FROM login", conn=self.conn_admin), 2)
        self.execute("INSERT INTO facultad (id_facultad, nombre) VALUES (90, 'Facultad Test')", conn=self.conn_admin)
        self.execute("UPDATE facultad SET nombre='Facultad Editada' WHERE id_facultad=90", conn=self.conn_admin)
        self.execute("DELETE FROM facultad WHERE id_facultad=90", conn=self.conn_admin)

        self.assertErrorSQL("DELETE FROM partido WHERE id_partido=1", contiene="no puede ser eliminado", conn=self.conn_admin)
        self.assertErrorSQL("CREATE USER 'otro'@'localhost' IDENTIFIED BY 'clave'", contiene="denied", conn=self.conn_admin)


class TestCierrePorProcedimiento(TestBDAislado):
    def test_planillero_marca_partido_jugado_con_procedimiento(self):
        crear_edicion_prueba(self.conn, en_curso=True)
        ayer = (date.today() - timedelta(days=1)).isoformat()
        manana = (date.today() + timedelta(days=2)).isoformat()

        insertar_partido(self.conn, 101, 1, 11, 12, ayer)
        insertar_partido(self.conn, 102, 2, 13, 14, manana)
        firmar_planilla(self.conn, 101, 11, ["11111111"])
        firmar_planilla(self.conn, 101, 12, ["22222221"])

        conn_plan = conectar(*DB_PLANILLERO, autocommit=True)
        self.addCleanup(conn_plan.close)

        self.assertErrorSQL("UPDATE partido SET estado='jugado' WHERE id_partido=101", contiene="denied", conn=conn_plan)
        self.execute("CALL sp_marcar_partido_jugado(101)", conn=conn_plan)
        self.assertEqual(self.scalar("SELECT estado FROM partido WHERE id_partido=101"), "jugado")

        self.assertErrorSQL("CALL sp_marcar_partido_jugado(102)", contiene="ya pasaron", conn=conn_plan)


if __name__ == "__main__":
    unittest.main()
