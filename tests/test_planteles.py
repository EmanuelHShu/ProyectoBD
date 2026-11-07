"""Pruebas de instalación inicial, ediciones del torneo, equipos y planteles."""
import unittest
from base import TestBD, crear_edicion_prueba

SQL_INSCRIBIR = (
    "INSERT INTO equipo_jugador_torneo (id_equipo, ci_jugador, id_torneo, numero_camiseta) "
    "VALUES (%s, %s, %s, %s)"
)
CI_DOCENTE_ING = "11111116"  # docente de Ingeniería, no está en el equipo 11


def crear_jugador(conn, ci, tipo="grado", id_facultad=1):
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO jugador (ci, nombre, apellido, email, fecha_nacimiento, id_facultad, tipo) "
            "VALUES (%s, 'Jugador', 'Prueba', %s, '2001-05-10', %s, %s)",
            (ci, f"j{ci}@ucu.edu.uy", id_facultad, tipo),
        )


class TestInstalacionYDatos(TestBD):
    def test_esquema_creado_completo(self):
        self.assertEqual(
            self.scalar(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_schema='torneo_futbol5' AND table_type='BASE TABLE'"
            ),
            14,
        )
        self.assertEqual(
            self.scalar("SELECT COUNT(*) FROM information_schema.views WHERE table_schema='torneo_futbol5'"),
            1,
        )
        self.assertEqual(
            self.scalar("SELECT COUNT(*) FROM information_schema.triggers WHERE trigger_schema='torneo_futbol5'"),
            20,
        )
        self.assertEqual(
            self.scalar(
                "SELECT COUNT(*) FROM information_schema.routines "
                "WHERE routine_schema='torneo_futbol5' AND routine_type='FUNCTION'"
            ),
            1,
        )
        self.assertEqual(
            self.scalar(
                "SELECT COUNT(*) FROM information_schema.routines "
                "WHERE routine_schema='torneo_futbol5' AND routine_type='PROCEDURE'"
            ),
            2,
        )

    def test_datos_iniciales_del_fixture(self):
        self.assertEqual(self.scalar("SELECT COUNT(*) FROM equipo"), 6)
        self.assertEqual(self.scalar("SELECT COUNT(*) FROM jugador"), 31)
        self.assertEqual(self.scalar("SELECT COUNT(*) FROM partido"), 15)
        self.assertEqual(self.scalar("SELECT COUNT(*) FROM partido WHERE estado='jugado'"), 9)

        por_fecha = self.query(
            "SELECT numero_fecha, COUNT(*) AS cant FROM partido GROUP BY numero_fecha ORDER BY numero_fecha"
        )
        self.assertEqual([(r["numero_fecha"], r["cant"]) for r in por_fecha], [(f, 3) for f in range(1, 6)])

        fecha_5 = self.query("SELECT estado FROM partido WHERE id_partido IN (13, 14, 15)")
        self.assertEqual([r["estado"] for r in fecha_5], ["programado", "programado", "programado"])

        cruces = self.scalar(
            "SELECT COUNT(*) FROM ("
            "  SELECT DISTINCT LEAST(id_equipo_local, id_equipo_visitante) AS eq1, "
            "                  GREATEST(id_equipo_local, id_equipo_visitante) AS eq2 "
            "  FROM partido"
            ") t"
        )
        self.assertEqual(cruces, 15)


class TestPlantelesYEdiciones(TestBD):
    def setUp(self):
        super().setUp()
        crear_edicion_prueba(self.conn, en_curso=False)

    def test_validaciones_tabla_torneo(self):
        sql = (
            "INSERT INTO torneo (nombre, anio, semestre, fecha_inicio, fecha_fin, estado) "
            "VALUES (%s, %s, %s, %s, %s, %s)"
        )
        self.execute(sql, ("Torneo 2028-1", 2028, 1, "2028-03-01", "2028-06-30", "inscripcion"))
        self.assertErrorSQL(sql, ("Fechas mal", 2028, 2, "2028-11-01", "2028-08-01", "inscripcion"), "chk_torneo_fechas")
        self.assertErrorSQL(sql, ("Semestre mal", 2029, 3, "2029-03-01", "2029-06-30", "inscripcion"), "chk_torneo_semestre")
        self.assertErrorSQL(sql, ("Repetido", 2026, 2, "2026-08-01", "2026-11-30", "inscripcion"), "duplicate")

    def test_plantel_solo_se_modifica_en_inscripcion(self):
        self.execute(SQL_INSCRIBIR, (11, CI_DOCENTE_ING, 2, 15))
        self.assertEqual(self.scalar("SELECT COUNT(*) FROM equipo_jugador_torneo WHERE id_equipo=11"), 6)

        self.execute("UPDATE equipo_jugador_torneo SET numero_camiseta=20 WHERE id_equipo=11 AND ci_jugador='11111112'")
        self.execute("DELETE FROM equipo_jugador_torneo WHERE id_equipo=11 AND ci_jugador='11111112'")

        self.execute("UPDATE torneo SET estado='en curso' WHERE id_torneo=2")
        self.assertErrorSQL(SQL_INSCRIBIR, (11, "11111112", 2, 20), "inscripcion")
        self.assertErrorSQL(
            "UPDATE equipo_jugador_torneo SET numero_camiseta=30 WHERE id_equipo=11 AND ci_jugador='11111113'",
            contiene="inscripcion",
        )
        self.assertErrorSQL(
            "DELETE FROM equipo_jugador_torneo WHERE id_equipo=11 AND ci_jugador='11111113'",
            contiene="inscripcion",
        )

    def test_jugador_debe_ser_de_la_misma_facultad(self):
        # 66666661 es de Psicología (facultad 6) y el equipo 11 es de Ingeniería (facultad 1)
        self.assertErrorSQL(SQL_INSCRIBIR, (11, "66666661", 2, 25), "facultad")

    def test_dorsales_unicos_y_rango_permitido(self):
        self.assertErrorSQL(SQL_INSCRIBIR, (11, CI_DOCENTE_ING, 2, 1), "uk_ejt_equipo_camiseta")
        self.assertErrorSQL(SQL_INSCRIBIR, (11, CI_DOCENTE_ING, 2, 0), "chk_ejt_camiseta")
        self.assertErrorSQL(SQL_INSCRIBIR, (11, CI_DOCENTE_ING, 2, 100), "chk_ejt_camiseta")

        # El mismo dorsal en dos equipos distintos sí es válido
        crear_jugador(self.conn, "80000001", id_facultad=2)
        self.execute(SQL_INSCRIBIR, (11, CI_DOCENTE_ING, 2, 99))
        self.execute(SQL_INSCRIBIR, (12, "80000001", 2, 99))

    def test_un_solo_equipo_por_jugador_en_la_misma_edicion(self):
        self.execute(
            "INSERT INTO equipo (id_equipo, nombre, id_torneo, id_facultad, ci_capitan) "
            "VALUES (15, 'Ingenieria C', 2, 1, %s)",
            (CI_DOCENTE_ING,),
        )
        self.assertErrorSQL(SQL_INSCRIBIR, (15, "11111112", 2, 10), "uk_ejt_jugador_torneo")

        # En cambio, participar en otra edición distinta sí se permite
        self.execute(SQL_INSCRIBIR, (15, CI_DOCENTE_ING, 2, 10))
        cant = self.scalar("SELECT COUNT(*) FROM equipo_jugador_torneo WHERE ci_jugador=%s", (CI_DOCENTE_ING,))
        self.assertEqual(cant, 2)

    def test_maximo_diez_jugadores_por_plantel(self):
        for dorsal in range(6, 11):
            ci = f"810000{dorsal:02d}"
            crear_jugador(self.conn, ci)
            self.execute(SQL_INSCRIBIR, (11, ci, 2, dorsal))

        self.assertEqual(self.scalar("SELECT COUNT(*) FROM equipo_jugador_torneo WHERE id_equipo=11"), 10)

        crear_jugador(self.conn, "81000099")
        self.assertErrorSQL(SQL_INSCRIBIR, (11, "81000099", 2, 50), "mas de 10")

    def test_tope_de_dos_docentes_o_funcionarios(self):
        crear_jugador(self.conn, "82000001", tipo="funcionario")
        crear_jugador(self.conn, "82000002", tipo="posgrado")
        crear_jugador(self.conn, "82000003", tipo="docente")

        self.execute(SQL_INSCRIBIR, (11, CI_DOCENTE_ING, 2, 20))
        self.execute(SQL_INSCRIBIR, (11, "82000001", 2, 21))
        # Posgrado no suma al cupo de docentes/funcionarios
        self.execute(SQL_INSCRIBIR, (11, "82000002", 2, 22))
        self.assertErrorSQL(SQL_INSCRIBIR, (11, "82000003", 2, 23), "maximo 2")

    def test_reglas_del_capitan(self):
        self.assertErrorSQL(
            "DELETE FROM equipo_jugador_torneo WHERE id_equipo=11 AND ci_jugador='11111111'",
            contiene="capitan",
        )
        self.assertErrorSQL(
            "UPDATE equipo SET ci_capitan=%s WHERE id_equipo=11",
            (CI_DOCENTE_ING,),
            contiene="capitan",
        )
        self.assertErrorSQL(
            "INSERT INTO equipo (id_equipo, nombre, id_torneo, id_facultad, ci_capitan) "
            "VALUES (15, 'Repetido Cap', 2, 1, '11111111')",
            contiene="uk_equipo_capitan_torneo",
        )

        self.execute("UPDATE equipo SET ci_capitan='11111112' WHERE id_equipo=11")
        self.execute("DELETE FROM equipo_jugador_torneo WHERE id_equipo=11 AND ci_jugador='11111111'")

    def test_cierre_de_inscripcion_valida_capitan_y_minimo_cinco(self):
        self.execute(
            "INSERT INTO equipo (id_equipo, nombre, id_torneo, id_facultad, ci_capitan) "
            "VALUES (15, 'Ingenieria C', 2, 1, %s)",
            (CI_DOCENTE_ING,),
        )
        for i in range(1, 6):
            ci = f"8300000{i}"
            crear_jugador(self.conn, ci)
            self.execute(SQL_INSCRIBIR, (15, ci, 2, i))

        # Tiene 5 jugadores, pero todavía no está inscripto su capitán
        self.assertErrorSQL("UPDATE torneo SET estado='en curso' WHERE id_torneo=2", contiene="capitan")

        # Dejamos al capitán pero bajamos el plantel a 4 integrantes
        self.execute("DELETE FROM equipo_jugador_torneo WHERE id_equipo=15 AND ci_jugador IN ('83000004', '83000005')")
        self.execute(SQL_INSCRIBIR, (15, CI_DOCENTE_ING, 2, 10))
        self.assertErrorSQL("UPDATE torneo SET estado='en curso' WHERE id_torneo=2", contiene="al menos 5")

        # Volvemos a 5 con capitán incluido y cierra bien
        self.execute(SQL_INSCRIBIR, (15, "83000004", 2, 4))
        self.execute("UPDATE torneo SET estado='en curso' WHERE id_torneo=2")
        self.assertEqual(self.scalar("SELECT estado FROM torneo WHERE id_torneo=2"), "en curso")

    def test_cambiar_de_equipo_requiere_baja_y_alta(self):
        self.execute(
            "INSERT INTO equipo (id_equipo, nombre, id_torneo, id_facultad, ci_capitan) "
            "VALUES (15, 'Ingenieria C', 2, 1, %s)",
            (CI_DOCENTE_ING,),
        )
        self.assertErrorSQL(
            "UPDATE equipo_jugador_torneo SET id_equipo=15 WHERE id_equipo=11 AND ci_jugador='11111112'",
            contiene="eliminelo",
        )
        self.execute("DELETE FROM equipo_jugador_torneo WHERE id_equipo=11 AND ci_jugador='11111112'")
        self.execute(SQL_INSCRIBIR, (15, "11111112", 2, 8))
        self.assertEqual(
            self.scalar("SELECT id_equipo FROM equipo_jugador_torneo WHERE ci_jugador='11111112' AND id_torneo=2"),
            15,
        )


if __name__ == "__main__":
    unittest.main()
