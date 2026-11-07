"""Pruebas de programación de partidos, turnos, planillas, resultados y plazo de 48h."""
import unittest
from base import (
    JUGADORES_FACULTAD,
    TestBD,
    crear_edicion_prueba,
    firmar_planilla,
    insertar_partido,
)

SQL_PARTIDO = (
    "INSERT INTO partido (id_torneo, numero_fecha, id_equipo_local, id_equipo_visitante, "
    "dia, id_turno, nombre_cancha, id_complejo, estado) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
)
SQL_GOL = "INSERT INTO gol (id_partido, ci_jugador, minuto, autogol) VALUES (%s, %s, %s, %s)"
SQL_TARJETA = "INSERT INTO tarjeta (id_partido, ci_jugador, minuto, color) VALUES (%s, %s, %s, %s)"


def fijar_reloj(conn, fecha_hora):
    with conn.cursor() as cur:
        cur.execute("SET TIMESTAMP = UNIX_TIMESTAMP(%s)", (fecha_hora,))


class TestFixtureYTurnos(TestBD):
    def setUp(self):
        super().setUp()
        crear_edicion_prueba(self.conn, en_curso=True)

    def test_validaciones_de_turnos(self):
        sql = "INSERT INTO turno (hora_inicio, hora_fin) VALUES (%s, %s)"
        self.execute(sql, ("21:30:00", "22:30:00"))
        self.assertErrorSQL(sql, ("17:00:00", "18:00:00"), "chk_turno_franja")
        self.assertErrorSQL(sql, ("22:30:00", "23:30:00"), "chk_turno_franja")
        self.assertErrorSQL(sql, ("18:00:00", "20:00:00"), "chk_turno_duracion")
        self.assertErrorSQL(sql, ("18:00:00", "19:00:00"), "uk_turno_horas")

    def test_validaciones_equipos_del_partido(self):
        self.execute(SQL_PARTIDO, (2, 1, 11, 12, "2026-12-07", 1, "Cancha 1", 1, "programado"))
        self.assertErrorSQL(SQL_PARTIDO, (2, 2, 11, 11, "2026-12-14", 1, "Cancha 1", 1, "programado"), "si mismo")
        self.assertErrorSQL(SQL_PARTIDO, (2, 2, 11, 1, "2026-12-14", 1, "Cancha 1", 1, "programado"), "visitante debe tener")
        self.assertErrorSQL(SQL_PARTIDO, (2, 0, 13, 14, "2026-12-14", 1, "Cancha 1", 1, "programado"), "chk_partido_fecha")

        # Equipo en otra edición sin plantel completo (< 5 jugadores)
        self.execute(
            "INSERT INTO torneo (id_torneo, nombre, anio, semestre, fecha_inicio, fecha_fin, estado) "
            "VALUES (3, 'Torneo Incompleto', 2028, 1, '2028-03-01', '2028-06-30', 'inscripcion')"
        )
        self.execute(
            "INSERT INTO equipo (id_equipo, nombre, id_torneo, id_facultad, ci_capitan) VALUES "
            "(21, 'Corto A', 3, 1, '11111111'), (22, 'Corto B', 3, 2, '22222221')"
        )
        self.assertErrorSQL(SQL_PARTIDO, (3, 1, 21, 22, "2028-04-01", 1, "Cancha 1", 1, "programado"), "local debe tener")

    def test_disponibilidad_cancha_dia_y_turno(self):
        insertar_partido(self.conn, 101, 1, 11, 12, "2026-12-07", turno=1, cancha="Cancha 1")
        self.assertErrorSQL(
            SQL_PARTIDO,
            (2, 2, 13, 14, "2026-12-07", 1, "Cancha 1", 1, "programado"),
            "cancha ya tiene",
        )

        # Otro turno en la misma cancha u otra cancha en el mismo turno se aceptan
        self.execute(SQL_PARTIDO, (2, 1, 13, 14, "2026-12-07", 2, "Cancha 1", 1, "programado"))

        # Si el partido original se cancela, libera ese horario
        self.execute("UPDATE partido SET estado='cancelado' WHERE id_partido=101")
        self.execute(SQL_PARTIDO, (2, 3, 11, 13, "2026-12-07", 1, "Cancha 1", 1, "programado"))

    def test_no_repite_cruce_ni_juega_dos_veces_en_la_fecha(self):
        insertar_partido(self.conn, 101, 1, 11, 12, "2026-12-07")

        self.assertErrorSQL(SQL_PARTIDO, (2, 2, 11, 12, "2026-12-14", 1, "Cancha 1", 1, "programado"), "enfrentan")
        self.assertErrorSQL(SQL_PARTIDO, (2, 2, 12, 11, "2026-12-14", 1, "Cancha 1", 1, "programado"), "enfrentan")
        self.assertErrorSQL(SQL_PARTIDO, (2, 1, 11, 13, "2026-12-14", 1, "Cancha 1", 1, "programado"), "en esa fecha")
        self.assertErrorSQL(SQL_PARTIDO, (2, 1, 13, 11, "2026-12-14", 1, "Cancha 1", 1, "programado"), "en esa fecha")

        # Al cancelar 101, se permite reprogramar ese mismo cruce
        self.execute("UPDATE partido SET estado='cancelado' WHERE id_partido=101")
        self.execute(SQL_PARTIDO, (2, 2, 11, 12, "2026-12-14", 1, "Cancha 1", 1, "programado"))

    def test_cierre_de_partido_y_restriccion_de_borrado(self):
        insertar_partido(self.conn, 101, 1, 11, 12, "2026-12-07", turno=1)
        firmar_planilla(self.conn, 101, 11, JUGADORES_FACULTAD[1])
        firmar_planilla(self.conn, 101, 12, JUGADORES_FACULTAD[2])

        # El turno 1 termina a las 19:00
        fijar_reloj(self.conn, "2026-12-07 18:59:59")
        self.assertErrorSQL("CALL sp_marcar_partido_jugado(101)", contiene="ya pasaron")

        fijar_reloj(self.conn, "2026-12-07 19:00:00")
        self.execute("CALL sp_marcar_partido_jugado(101)")
        self.assertEqual(self.scalar("SELECT estado FROM partido WHERE id_partido=101"), "jugado")

        self.assertErrorSQL("DELETE FROM partido WHERE id_partido=101", contiene="no puede ser eliminado")
        self.assertErrorSQL("CALL sp_marcar_partido_jugado(9999)", contiene="no existe")

        insertar_partido(self.conn, 102, 2, 13, 14, "2026-12-07", turno=2, estado="postergado")
        fijar_reloj(self.conn, "2026-12-07 21:00:00")
        self.assertErrorSQL("CALL sp_marcar_partido_jugado(102)", contiene="solo un partido programado")
        self.execute("DELETE FROM partido WHERE id_partido=102")


class TestPlanillasYResultados(TestBD):
    def setUp(self):
        super().setUp()
        crear_edicion_prueba(self.conn, en_curso=True)
        insertar_partido(self.conn, 101, 1, 11, 12, "2026-12-07", turno=1)
        insertar_partido(self.conn, 102, 1, 13, 14, "2026-12-07", turno=2)
        fijar_reloj(self.conn, "2026-12-08 10:00:00")
        firmar_planilla(self.conn, 101, 11, ["11111111", "11111112"])
        firmar_planilla(self.conn, 101, 12, ["22222221"])

    def resultado_vista(self, id_partido):
        row = self.query(
            "SELECT goles_local, goles_visitante FROM v_resultado_partido WHERE id_partido=%s",
            (id_partido,),
        )[0]
        return row["goles_local"], row["goles_visitante"]

    def test_controles_al_firmar_planilla(self):
        sql = "INSERT INTO planilla_partido (id_partido, ci_jugador, id_equipo) VALUES (%s, %s, %s)"
        self.execute(sql, (101, "11111113", 11))
        self.execute(sql, (101, "22222222", 12))

        self.assertErrorSQL(sql, (101, "33333331", 13), "no participa")
        self.assertErrorSQL(sql, (101, "22222223", 11), "no integra el plantel")
        self.assertErrorSQL(sql, (101, "11111116", 11), "no integra el plantel")
        self.assertErrorSQL(sql, (101, "11111111", 11), "duplicate")
        self.assertErrorSQL(
            "UPDATE planilla_partido SET id_equipo=12 WHERE id_partido=101 AND ci_jugador='11111111'",
            contiene="eliminela",
        )

    def test_goles_y_tarjetas_requieren_planilla_y_minuto_valido(self):
        self.assertErrorSQL(SQL_GOL, (101, "11111115", 10, 0), "fk_gol_planilla")
        self.assertErrorSQL(SQL_TARJETA, (101, "11111115", 10, "amarilla"), "fk_tarjeta_planilla")

        self.assertErrorSQL(SQL_GOL, (101, "11111111", -1, 0), "chk_gol_minuto")
        self.assertErrorSQL(SQL_GOL, (101, "11111111", 121, 0), "chk_gol_minuto")
        self.assertErrorSQL(SQL_TARJETA, (101, "11111111", -1, "amarilla"), "chk_tarjeta_minuto")
        self.assertErrorSQL(SQL_TARJETA, (101, "11111111", 121, "amarilla"), "chk_tarjeta_minuto")

        self.execute(SQL_GOL, (101, "11111111", 0, 0))
        self.execute(SQL_GOL, (101, "11111111", 120, 0))
        self.execute(SQL_TARJETA, (101, "11111111", 0, "amarilla"))
        self.execute(SQL_TARJETA, (101, "11111111", 120, "amarilla"))

    def test_vista_resultado_con_goles_y_autogoles(self):
        self.assertEqual(self.resultado_vista(102), (0, 0))
        self.assertEqual(self.resultado_vista(1), (2, 1))

        # Local: 1 gol normal + 1 autogol visitante = 2
        # Visitante: 2 goles normales + 1 autogol local = 3
        self.execute(SQL_GOL, (101, "11111111", 8, 0))
        self.execute(SQL_GOL, (101, "11111112", 14, 1))
        self.execute(SQL_GOL, (101, "22222221", 20, 1))
        self.execute(SQL_GOL, (101, "22222221", 31, 0))
        self.execute(SQL_GOL, (101, "22222221", 40, 0))
        self.assertEqual(self.resultado_vista(101), (2, 3))

    def test_quitar_jugador_de_planilla_borra_sus_eventos_y_sancion(self):
        self.execute(SQL_GOL, (101, "11111111", 10, 0))
        self.execute(SQL_GOL, (101, "11111112", 25, 0))
        self.execute(SQL_TARJETA, (101, "11111111", 30, "roja"))
        self.assertEqual(
            self.scalar("SELECT COUNT(*) FROM sancion_jugador WHERE ci_jugador='11111111' AND id_torneo=2"),
            1,
        )

        self.execute("DELETE FROM planilla_partido WHERE id_partido=101 AND ci_jugador='11111111'")
        self.assertEqual(self.scalar("SELECT COUNT(*) FROM gol WHERE id_partido=101"), 1)
        self.assertEqual(self.scalar("SELECT ci_jugador FROM gol WHERE id_partido=101"), "11111112")
        self.assertEqual(self.scalar("SELECT COUNT(*) FROM tarjeta WHERE id_partido=101"), 0)
        self.assertEqual(
            self.scalar("SELECT COUNT(*) FROM sancion_jugador WHERE ci_jugador='11111111' AND id_torneo=2"),
            0,
        )


class TestVentanaCorreccion48h(TestBD):
    def setUp(self):
        super().setUp()
        crear_edicion_prueba(self.conn, en_curso=True)
        # Turno 1: termina 2026-11-01 19:00:00 -> vence 2026-11-03 19:00:00
        insertar_partido(self.conn, 101, 1, 11, 12, "2026-11-01", turno=1)
        firmar_planilla(self.conn, 101, 11, ["11111112", "11111113"])
        self.execute(SQL_GOL, (101, "11111112", 12, 0))
        self.execute(SQL_TARJETA, (101, "11111113", 35, "roja"))
        fijar_reloj(self.conn, "2026-11-01 19:30:00")
        self.execute("CALL sp_marcar_partido_jugado(101)")

    def test_permite_corregir_dentro_del_plazo(self):
        fijar_reloj(self.conn, "2026-11-03 18:59:00")
        self.execute(SQL_GOL, (101, "11111113", 44, 0))
        self.execute("UPDATE tarjeta SET color='amarilla' WHERE id_partido=101")
        self.execute("INSERT INTO planilla_partido (id_partido, ci_jugador, id_equipo) VALUES (101, '11111114', 11)")

        # Exactamente en el borde de 48h también sigue habilitado
        fijar_reloj(self.conn, "2026-11-03 19:00:00")
        self.execute("UPDATE gol SET minuto=15 WHERE id_partido=101 AND ci_jugador='11111112'")
        self.assertEqual(
            self.scalar("SELECT COUNT(*) FROM sancion_jugador WHERE ci_jugador='11111113' AND id_torneo=2"),
            0,
        )

    def test_rechaza_cambios_pasadas_las_48_horas(self):
        fijar_reloj(self.conn, "2026-11-03 19:00:01")
        self.assertErrorSQL(SQL_GOL, (101, "11111113", 50, 0), "48 horas")
        self.assertErrorSQL("UPDATE gol SET minuto=20 WHERE id_partido=101", contiene="48 horas")
        self.assertErrorSQL("DELETE FROM gol WHERE id_partido=101", contiene="48 horas")
        self.assertErrorSQL(SQL_TARJETA, (101, "11111112", 50, "amarilla"), "48 horas")
        self.assertErrorSQL("DELETE FROM tarjeta WHERE id_partido=101", contiene="48 horas")
        self.assertErrorSQL(
            "INSERT INTO planilla_partido (id_partido, ci_jugador, id_equipo) VALUES (101, '11111114', 11)",
            contiene="48 horas",
        )
        self.assertErrorSQL("UPDATE partido SET nombre_cancha='Cancha 2' WHERE id_partido=101", contiene="48 horas")

        # Los partidos jugados de agosto en insercion-datos.sql también están cerrados
        self.assertErrorSQL(SQL_GOL, (1, "11111111", 55, 0), "48 horas")

    def test_partido_programado_permite_carga_tardia_hasta_cerrarse(self):
        insertar_partido(self.conn, 102, 2, 13, 14, "2026-11-01", turno=2)
        firmar_planilla(self.conn, 102, 13, ["33333331"])

        fijar_reloj(self.conn, "2026-11-10 12:00:00")
        self.execute(SQL_GOL, (102, "33333331", 18, 0))
        self.execute("CALL sp_marcar_partido_jugado(102)")
        self.assertErrorSQL("UPDATE gol SET minuto=19 WHERE id_partido=102", contiene="48 horas")


if __name__ == "__main__":
    unittest.main()
