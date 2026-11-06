"""Planillas: firmas, goles, tarjetas, minutos, correcciones y resultado del partido."""
from base import CasoTransaccional, alta_partido, defecto, edicion_prueba, firmar, mover_reloj, q, valor

FIRMA = "INSERT INTO planilla_partido (id_partido,ci_jugador,id_equipo) VALUES (%s,%s,%s)"
GOL = "INSERT INTO gol (id_partido,ci_jugador,minuto,autogol) VALUES (%s,%s,%s,%s)"
TARJETA = "INSERT INTO tarjeta (id_partido,ci_jugador,minuto,color) VALUES (%s,%s,%s,%s)"
QUITAR = "DELETE FROM planilla_partido WHERE id_partido=101 AND ci_jugador='11111111'"

# Día dentro de la edición 2. Lo que depende del momento usa mover_reloj, nunca la fecha real.
DIA = "2026-12-07"
ANTES = "2026-12-01 12:00:00"
DESPUES = "2026-12-08 12:00:00"


def resultado(c, id_partido):
    fila = q(c, "SELECT goles_local,goles_visitante FROM v_resultado_partido WHERE id_partido=%s", (id_partido,))[0]
    return (fila["goles_local"], fila["goles_visitante"])


class Planillas(CasoTransaccional):
    """Partido 101 (11 contra 12) con el turno terminado y tres firmas; partido 102 (13 contra 14) sin firmas."""
    def setUp(self):
        super().setUp()
        edicion_prueba(self.c)
        alta_partido(self.c, 101, 1, 11, 12, DIA)
        alta_partido(self.c, 102, 2, 13, 14, DIA, turno=2)
        mover_reloj(self.c, DESPUES)
        firmar(self.c, 101, 11, ["11111111", "11111112"])
        firmar(self.c, 101, 12, ["22222221"])

    # ---------------------------------------------------------------- firmas
    def test_firmar_jugador_local(self):
        """CP-PLN-01 | Firmar un jugador del equipo local | Alta en planilla de un integrante del equipo 11 | Se acepta"""
        self.acepta(FIRMA, (101, "11111113", 11))

    def test_firmar_jugador_visitante(self):
        """CP-PLN-02 | Firmar un jugador del equipo visitante | Alta en planilla de un integrante del equipo 12 | Se acepta"""
        self.acepta(FIRMA, (101, "22222222", 12))

    def test_equipo_ajeno(self):
        """CP-PLN-03 | Firmar por un equipo ajeno al partido | Alta en planilla por el equipo 13 en un partido de 11 contra 12 | Rechazo: el equipo no participa del partido"""
        self.rechaza(FIRMA, "no participa", (101, "33333331", 13))

    def test_jugador_del_rival(self):
        """CP-PLN-04 | Firmar por el equipo rival | Integrante del equipo 12 firma por el equipo 11 | Rechazo: no integra el plantel del equipo indicado"""
        self.rechaza(FIRMA, "no integra el plantel", (101, "22222222", 11))

    def test_jugador_sin_inscribir_en_la_edicion(self):
        """CP-PLN-05 | Firmar sin estar inscripto en la edición | Jugador de la facultad que no integra el plantel del equipo 11 | Rechazo: no integra el plantel del equipo indicado"""
        self.rechaza(FIRMA, "no integra el plantel", (101, "11111116", 11))

    def test_firmar_dos_veces(self):
        """CP-PLN-06 | Firmar dos veces el mismo partido | Alta en planilla de un jugador que ya firmó | Rechazo por clave primaria"""
        self.rechaza(FIRMA, "primary", (101, "11111111", 11))

    # ---------------------------------------------------------------- goles y tarjetas
    def test_gol_de_quien_firmo(self):
        """CP-PLN-07 | Gol de un jugador que firmó | Alta de un gol de un jugador de la planilla | Se acepta"""
        self.acepta(GOL, (101, "11111111", 10, 0))

    def test_gol_de_quien_no_firmo(self):
        """CP-PLN-08 | Gol de un jugador que no firmó | Alta de un gol de un integrante del plantel sin firma | Rechazo por la clave foránea a la planilla"""
        self.rechaza(GOL, "fk_gol_planilla", (101, "11111113", 10, 0))

    def test_gol_en_partido_que_no_firmo(self):
        """CP-PLN-09 | Gol en un partido en el que no firmó | Jugador que firmó el partido 101 convierte en el 102 | Rechazo por la clave foránea a la planilla"""
        self.rechaza(GOL, "fk_gol_planilla", (102, "11111111", 10, 0))

    def test_corregir_autor_del_gol(self):
        """CP-PLN-10 | Corregir el gol a un jugador que no firmó | UPDATE del autor de un gol a un jugador sin firma | Rechazo por la clave foránea a la planilla"""
        q(self.c, GOL, (101, "11111111", 10, 0))
        self.rechaza("UPDATE gol SET ci_jugador='11111113' WHERE id_partido=101", "fk_gol_planilla")

    def test_tarjeta_de_quien_firmo(self):
        """CP-PLN-11 | Tarjeta a un jugador que firmó | Alta de una amarilla a un jugador de la planilla | Se acepta"""
        self.acepta(TARJETA, (101, "11111111", 10, "amarilla"))

    def test_tarjeta_de_quien_no_firmo(self):
        """CP-PLN-12 | Tarjeta a un jugador que no firmó | Alta de una amarilla a un integrante del plantel sin firma | Rechazo por la clave foránea a la planilla"""
        self.rechaza(TARJETA, "fk_tarjeta_planilla", (101, "11111113", 10, "amarilla"))

    # ---------------------------------------------------------------- minutos
    def test_gol_minuto_121(self):
        """CP-PLN-13 | Gol después del minuto 120 | Alta de un gol en el minuto 121 | Rechazo: el minuto va de 0 a 120"""
        self.rechaza(GOL, "chk_gol_minuto", (101, "11111111", 121, 0))

    def test_gol_minuto_negativo(self):
        """CP-PLN-14 | Gol en un minuto negativo | Alta de un gol en el minuto -1 | Rechazo: el minuto va de 0 a 120"""
        self.rechaza(GOL, "chk_gol_minuto", (101, "11111111", -1, 0))

    def test_gol_minutos_limite(self):
        """CP-PLN-15 | Gol en los minutos límite | Alta de goles en los minutos 0 y 120 | Se aceptan los dos"""
        self.acepta(GOL, (101, "11111111", 0, 0))
        self.acepta(GOL, (101, "11111111", 120, 0))

    def test_tarjeta_minuto_121(self):
        """CP-PLN-16 | Tarjeta después del minuto 120 | Alta de una tarjeta en el minuto 121 | Rechazo: el minuto va de 0 a 120"""
        self.rechaza(TARJETA, "chk_tarjeta_minuto", (101, "11111111", 121, "amarilla"))

    def test_tarjeta_minuto_negativo(self):
        """CP-PLN-17 | Tarjeta en un minuto negativo | Alta de una tarjeta en el minuto -1 | Rechazo: el minuto va de 0 a 120"""
        self.rechaza(TARJETA, "chk_tarjeta_minuto", (101, "11111111", -1, "amarilla"))

    def test_tarjeta_minutos_limite(self):
        """CP-PLN-18 | Tarjeta en los minutos límite | Alta de amarillas en los minutos 0 y 120 | Se aceptan las dos"""
        self.acepta(TARJETA, (101, "11111111", 0, "amarilla"))
        self.acepta(TARJETA, (101, "11111111", 120, "amarilla"))

    # ---------------------------------------------------------------- corrección de la planilla
    def test_update_del_jugador(self):
        """CP-PLN-19 | Cambiar el jugador de una firma con UPDATE | UPDATE de ci_jugador en la planilla | Rechazo: hay que eliminar la fila y cargar otra"""
        self.rechaza("UPDATE planilla_partido SET ci_jugador='11111113' WHERE id_partido=101 AND ci_jugador='11111111'", "eliminela")

    def test_update_del_equipo(self):
        """CP-PLN-20 | Cambiar el equipo de una firma con UPDATE | UPDATE de id_equipo en la planilla | Rechazo: hay que eliminar la fila y cargar otra"""
        self.rechaza("UPDATE planilla_partido SET id_equipo=12 WHERE id_partido=101 AND ci_jugador='11111111'", "eliminela")

    def test_update_del_partido(self):
        """CP-PLN-21 | Cambiar el partido de una firma con UPDATE | UPDATE de id_partido en la planilla | Rechazo: hay que eliminar la fila y cargar otra"""
        self.rechaza("UPDATE planilla_partido SET id_partido=102 WHERE id_partido=101 AND ci_jugador='11111111'", "eliminela")

    def test_quitar_arrastra_el_gol(self):
        """CP-PLN-22 | Quitar de planilla arrastra el gol | Borrar la firma de un jugador con un gol | Se acepta y el gol desaparece"""
        q(self.c, GOL, (101, "11111111", 10, 0))
        self.acepta(QUITAR)
        self.assertEqual(valor(self.c, "SELECT COUNT(*) FROM gol WHERE id_partido=101"), 0)

    def test_quitar_arrastra_la_tarjeta_y_la_sancion(self):
        """CP-PLN-23 | Quitar de planilla arrastra la tarjeta y su sanción | Borrar la firma de un jugador con una roja | Se acepta y desaparecen la tarjeta y la sanción"""
        q(self.c, TARJETA, (101, "11111111", 10, "roja"))
        self.assertEqual(valor(self.c, "SELECT COUNT(*) FROM sancion_jugador WHERE ci_jugador='11111111' AND id_torneo=2"), 1)
        self.acepta(QUITAR)
        self.assertEqual(valor(self.c, "SELECT COUNT(*) FROM tarjeta WHERE id_partido=101"), 0)
        self.assertEqual(valor(self.c, "SELECT COUNT(*) FROM sancion_jugador WHERE ci_jugador='11111111' AND id_torneo=2"), 0)

    def test_quitar_no_toca_a_los_demas(self):
        """CP-PLN-24 | Quitar de planilla no afecta a otros jugadores | Dos goleadores; borrar la firma de uno | El gol del otro jugador se conserva"""
        q(self.c, GOL, (101, "11111111", 10, 0))
        q(self.c, GOL, (101, "11111112", 20, 0))
        self.acepta(QUITAR)
        self.assertEqual(valor(self.c, "SELECT ci_jugador FROM gol WHERE id_partido=101"), "11111112")

    # ---------------------------------------------------------------- resultado
    def test_resultado_gol_del_local(self):
        """CP-PLN-25 | Resultado con un gol del local | Gol de un jugador del equipo local | La vista muestra 1-0"""
        q(self.c, GOL, (101, "11111111", 10, 0))
        self.assertEqual(resultado(self.c, 101), (1, 0))

    def test_resultado_gol_del_visitante(self):
        """CP-PLN-26 | Resultado con un gol del visitante | Gol de un jugador del equipo visitante | La vista muestra 0-1"""
        q(self.c, GOL, (101, "22222221", 10, 0))
        self.assertEqual(resultado(self.c, 101), (0, 1))

    def test_resultado_autogol_del_local(self):
        """CP-PLN-27 | Autogol de un jugador local | Autogol de un jugador del equipo local | La vista lo suma al visitante: 0-1"""
        q(self.c, GOL, (101, "11111111", 10, 1))
        self.assertEqual(resultado(self.c, 101), (0, 1))

    def test_resultado_autogol_del_visitante(self):
        """CP-PLN-28 | Autogol de un jugador visitante | Autogol de un jugador del equipo visitante | La vista lo suma al local: 1-0"""
        q(self.c, GOL, (101, "22222221", 10, 1))
        self.assertEqual(resultado(self.c, 101), (1, 0))

    def test_resultado_con_goles_y_autogoles(self):
        """CP-PLN-29 | Resultado con goles y autogoles de ambos | Un gol y un autogol del local; dos goles y un autogol del visitante | La vista muestra 2-3"""
        q(self.c, GOL, (101, "11111111", 5, 0))
        q(self.c, GOL, (101, "11111112", 6, 1))
        q(self.c, GOL, (101, "22222221", 7, 1))
        q(self.c, GOL, (101, "22222221", 8, 0))
        q(self.c, GOL, (101, "22222221", 9, 0))
        self.assertEqual(resultado(self.c, 101), (2, 3))

    def test_resultado_sin_goles(self):
        """CP-PLN-30 | Resultado de un partido sin goles | Consultar la vista para un partido sin goles | La vista muestra 0-0"""
        self.assertEqual(resultado(self.c, 102), (0, 0))

    def test_resultado_de_los_datos(self):
        """CP-PLN-31 | Resultado de un partido de los datos | Consultar la vista para el partido 1 | La vista muestra 2-1"""
        self.assertEqual(resultado(self.c, 1), (2, 1))

    # ---------------------------------------------------------------- reglas que hoy solo aplica la aplicación
    @defecto("REG-17", "Se aceptó: la base registró la firma antes del partido; solo la aplicación lo impide.")
    def test_planilla_en_partido_futuro(self):
        """CP-PLN-32 | Planilla en un partido que no se jugó | Reloj antes del turno; firmar por SQL | Rechazo: el turno todavía no terminó"""
        mover_reloj(self.c, ANTES)
        self.rechaza(FIRMA, None, (101, "11111113", 11))

    @defecto("REG-17", "Se aceptó: la base registró el gol antes del partido; solo la aplicación lo impide.")
    def test_gol_en_partido_futuro(self):
        """CP-PLN-33 | Gol en un partido que no se jugó | Reloj antes del turno; cargar un gol por SQL | Rechazo: el turno todavía no terminó"""
        mover_reloj(self.c, ANTES)
        self.rechaza(GOL, None, (101, "11111111", 10, 0))

    @defecto("REG-17", "Se aceptó: la base registró la tarjeta antes del partido; solo la aplicación lo impide.")
    def test_tarjeta_en_partido_futuro(self):
        """CP-PLN-34 | Tarjeta en un partido que no se jugó | Reloj antes del turno; cargar una tarjeta por SQL | Rechazo: el turno todavía no terminó"""
        mover_reloj(self.c, ANTES)
        self.rechaza(TARJETA, None, (101, "11111111", 10, "amarilla"))

    @defecto("REG-17", "Se aceptó: la base registró la firma en un partido cancelado; solo la aplicación lo impide.")
    def test_planilla_en_partido_cancelado(self):
        """CP-PLN-35 | Planilla en un partido cancelado | Cancelar el partido y firmar por SQL | Rechazo: el partido no se juega"""
        q(self.c, "UPDATE partido SET estado='cancelado' WHERE id_partido=101")
        self.rechaza(FIRMA, None, (101, "11111113", 11))

    @defecto("REG-17", "Se aceptó: la base registró el gol en un partido cancelado; solo la aplicación lo impide.")
    def test_gol_en_partido_cancelado(self):
        """CP-PLN-36 | Gol en un partido cancelado | Cancelar el partido y cargar un gol por SQL | Rechazo: el partido no se juega"""
        q(self.c, "UPDATE partido SET estado='cancelado' WHERE id_partido=101")
        self.rechaza(GOL, None, (101, "11111111", 10, 0))

    @defecto("REG-17", "Se aceptó: la base registró la tarjeta en un partido cancelado; solo la aplicación lo impide.")
    def test_tarjeta_en_partido_cancelado(self):
        """CP-PLN-37 | Tarjeta en un partido cancelado | Cancelar el partido y cargar una tarjeta por SQL | Rechazo: el partido no se juega"""
        q(self.c, "UPDATE partido SET estado='cancelado' WHERE id_partido=101")
        self.rechaza(TARJETA, None, (101, "11111111", 10, "amarilla"))

    @defecto("REG-17", "Se aceptó: la base registró la firma en un partido postergado; solo la aplicación lo impide.")
    def test_planilla_en_partido_postergado(self):
        """CP-PLN-38 | Planilla en un partido postergado | Postergar el partido y firmar por SQL | Rechazo: el partido todavía no se juega"""
        q(self.c, "UPDATE partido SET estado='postergado' WHERE id_partido=101")
        self.rechaza(FIRMA, None, (101, "11111113", 11))
