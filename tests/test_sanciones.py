"""Pruebas de sanciones automáticas, recálculo, bloqueo en planilla y sanciones manuales."""
import unittest
from base import TestBD, crear_edicion_prueba, firmar_planilla, insertar_partido

CI_JUGADOR = "11111112"
CI_COMPANERO = "11111113"
CI_SUPLENTE = "11111114"

SQL_TARJETA = "INSERT INTO tarjeta (id_partido, ci_jugador, minuto, color) VALUES (%s, %s, %s, %s)"
SQL_SANCION = (
    "INSERT INTO sancion_jugador (ci_jugador, id_torneo, motivo, numero_fecha_inicio, cantidad_fechas) "
    "VALUES (%s, %s, %s, %s, %s)"
)


class TestSanciones(TestBD):
    def setUp(self):
        super().setUp()
        crear_edicion_prueba(self.conn, en_curso=True)
        insertar_partido(self.conn, 101, 1, 11, 12, "2026-11-02")
        insertar_partido(self.conn, 102, 2, 11, 13, "2026-11-09")
        insertar_partido(self.conn, 103, 3, 11, 14, "2026-11-16")
        firmar_planilla(self.conn, 101, 11, [CI_JUGADOR, CI_COMPANERO])

    def obtener_sanciones(self, ci=CI_JUGADOR, id_torneo=2):
        rows = self.query(
            "SELECT motivo, numero_fecha_inicio, cantidad_fechas FROM sancion_jugador "
            "WHERE ci_jugador=%s AND id_torneo=%s ORDER BY numero_fecha_inicio, motivo",
            (ci, id_torneo),
        )
        return [(r["motivo"], r["numero_fecha_inicio"], r["cantidad_fechas"]) for r in rows]

    def test_roja_directa_sanciona_la_fecha_siguiente(self):
        self.execute(SQL_TARJETA, (101, CI_JUGADOR, 15, "roja"))
        self.assertEqual(self.obtener_sanciones(), [("roja", 2, 1)])

        id_tarjeta = self.scalar(
            "SELECT id_tarjeta FROM sancion_jugador WHERE ci_jugador=%s AND id_torneo=2",
            (CI_JUGADOR,),
        )
        self.assertIsNotNone(id_tarjeta)

    def test_acumulacion_cada_tres_amarillas(self):
        firmar_planilla(self.conn, 102, 11, [CI_JUGADOR])
        firmar_planilla(self.conn, 103, 11, [CI_JUGADOR])

        # Con dos amarillas todavía no hay suspensión
        self.execute(SQL_TARJETA, (101, CI_JUGADOR, 10, "amarilla"))
        self.execute(SQL_TARJETA, (102, CI_JUGADOR, 20, "amarilla"))
        self.assertEqual(self.obtener_sanciones(), [])

        # La tercera amarilla suspende para la fecha 4
        self.execute(SQL_TARJETA, (103, CI_JUGADOR, 25, "amarilla"))
        self.assertEqual(self.obtener_sanciones(), [("acumulacion de amarillas", 4, 1)])

    def test_orden_cronologico_al_cargar_amarillas_desordenadas(self):
        firmar_planilla(self.conn, 102, 11, [CI_JUGADOR])
        firmar_planilla(self.conn, 103, 11, [CI_JUGADOR])

        # Cargamos primero la de la fecha 3 y después las de las fechas 1 y 2
        for id_partido in (103, 101, 102):
            self.execute(SQL_TARJETA, (id_partido, CI_JUGADOR, 12, "amarilla"))

        self.assertEqual(self.obtener_sanciones(), [("acumulacion de amarillas", 4, 1)])
        partido_origen = self.scalar(
            "SELECT t.id_partido FROM sancion_jugador s "
            "JOIN tarjeta t ON t.id_tarjeta = s.id_tarjeta "
            "WHERE s.ci_jugador=%s AND s.id_torneo=2",
            (CI_JUGADOR,),
        )
        self.assertEqual(partido_origen, 103)

    def test_roja_no_suma_amarillas_ni_acumula_entre_ediciones(self):
        self.execute(SQL_TARJETA, (101, CI_JUGADOR, 10, "amarilla"))
        self.execute(SQL_TARJETA, (101, CI_JUGADOR, 20, "amarilla"))
        self.execute(SQL_TARJETA, (101, CI_JUGADOR, 30, "roja"))
        self.assertEqual(self.obtener_sanciones(), [("roja", 2, 1)])

        # 11111111 ya trae 1 amarilla en la edición 1
        firmar_planilla(self.conn, 101, 11, ["11111111"])
        self.execute(SQL_TARJETA, (101, "11111111", 15, "amarilla"))
        self.execute(SQL_TARJETA, (101, "11111111", 40, "amarilla"))
        self.assertEqual(self.obtener_sanciones("11111111", 1), [])
        self.assertEqual(self.obtener_sanciones("11111111", 2), [])

    def test_recalculo_al_corregir_o_eliminar_tarjetas(self):
        self.execute(SQL_TARJETA, (101, CI_JUGADOR, 18, "roja"))
        self.assertEqual(self.obtener_sanciones(), [("roja", 2, 1)])

        # Si se corrige el color a amarilla, desaparece la sanción por roja
        self.execute("UPDATE tarjeta SET color='amarilla' WHERE id_partido=101")
        self.assertEqual(self.obtener_sanciones(), [])

        # Si vuelve a roja y se corrige el jugador al compañero, se traslada la sanción
        self.execute("UPDATE tarjeta SET color='roja', ci_jugador=%s WHERE id_partido=101", (CI_COMPANERO,))
        self.assertEqual(self.obtener_sanciones(CI_JUGADOR), [])
        self.assertEqual(self.obtener_sanciones(CI_COMPANERO), [("roja", 2, 1)])

        # Si se borra el partido programado, también se limpian las sanciones de sus tarjetas
        self.execute("DELETE FROM partido WHERE id_partido=101")
        self.assertEqual(self.obtener_sanciones(CI_COMPANERO), [])

    def test_bloqueo_de_suspendidos_al_firmar_planilla(self):
        sql_firma = "INSERT INTO planilla_partido (id_partido, ci_jugador, id_equipo) VALUES (%s, %s, 11)"
        self.execute(SQL_TARJETA, (101, CI_JUGADOR, 22, "roja"))

        self.assertErrorSQL(sql_firma, (102, CI_JUGADOR), "suspendido")
        # En la fecha 3 ya cumplió la fecha de suspensión
        self.execute(sql_firma, (103, CI_JUGADOR))

    def test_sanciones_disciplinarias_manuales(self):
        sql_firma = "INSERT INTO planilla_partido (id_partido, ci_jugador, id_equipo) VALUES (%s, %s, 11)"
        self.execute(SQL_SANCION, (CI_SUPLENTE, 2, "disciplinaria", 1, 2))

        self.assertErrorSQL(sql_firma, (101, CI_SUPLENTE), "suspendido")
        self.assertErrorSQL(sql_firma, (102, CI_SUPLENTE), "suspendido")
        self.execute(sql_firma, (103, CI_SUPLENTE))

        # Una sanción en el torneo 2 no bloquea partidos del torneo 1
        self.execute("INSERT INTO planilla_partido (id_partido, ci_jugador, id_equipo) VALUES (10, %s, 1)", (CI_SUPLENTE,))

        # El recálculo de tarjetas no altera las sanciones disciplinarias manuales
        self.execute(SQL_SANCION, (CI_JUGADOR, 2, "disciplinaria", 3, 2))
        self.execute(SQL_TARJETA, (101, CI_JUGADOR, 10, "roja"))
        self.execute("DELETE FROM tarjeta WHERE id_partido=101")
        self.assertEqual(self.obtener_sanciones(CI_JUGADOR), [("disciplinaria", 3, 2)])

        # Validaciones de FK y CHECK en sancion_jugador
        self.assertErrorSQL(SQL_SANCION, ("55555551", 2, "disciplinaria", 2, 1), "foreign key")
        self.assertErrorSQL(SQL_SANCION, (CI_JUGADOR, 2, "disciplinaria", 0, 1), "chk_sancion_fecha_inicio")
        self.assertErrorSQL(SQL_SANCION, (CI_JUGADOR, 2, "disciplinaria", 2, 0), "chk_sancion_cantidad")


if __name__ == "__main__":
    unittest.main()
