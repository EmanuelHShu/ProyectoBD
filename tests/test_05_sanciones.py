"""Sanciones automaticas y manuales, y suspension de jugadores en la planilla."""
from datetime import date, timedelta

from base import (WEB_ADMIN, WEB_PLANILLERO, CasoTransaccional, CasoWeb, alta_partido, avisos, defecto,
                  edicion_prueba, firmar, intentar, mover_reloj, q, valor)

JUGADOR = "11111112"
COMPANERO = "11111113"
SUPLENTE = "11111114"
ACUMULACION = "acumulacion de amarillas"

FIRMAR = "INSERT INTO planilla_partido (id_partido,ci_jugador,id_equipo) VALUES (%s,%s,11)"
TARJETA = "INSERT INTO tarjeta (id_partido,ci_jugador,minuto,color) VALUES (%s,%s,%s,%s)"
SANCION = ("INSERT INTO sancion_jugador (ci_jugador,id_torneo,motivo,numero_fecha_inicio,cantidad_fechas) "
           "VALUES (%s,%s,%s,%s,%s)")


def tarjeta(c, partido, color, minuto=10, ci=JUGADOR):
    q(c, TARJETA, (partido, ci, minuto, color))


def manual(c, inicio, cantidad=1, ci=JUGADOR, torneo=2):
    q(c, SANCION, (ci, torneo, "disciplinaria", inicio, cantidad))


def sanciones(c, ci=JUGADOR, torneo=2):
    filas = q(c, "SELECT motivo,numero_fecha_inicio,cantidad_fechas FROM sancion_jugador "
                 "WHERE ci_jugador=%s AND id_torneo=%s ORDER BY numero_fecha_inicio,motivo", (ci, torneo))
    return [(f["motivo"], f["numero_fecha_inicio"], f["cantidad_fechas"]) for f in filas]


def tarjeta_sancionada(c, ci=JUGADOR, torneo=2):
    """Devuelve (partido, minuto) de la tarjeta que origino la sancion del jugador."""
    fila = q(c, "SELECT t.id_partido,t.minuto FROM sancion_jugador s JOIN tarjeta t ON t.id_tarjeta=s.id_tarjeta "
                "WHERE s.ci_jugador=%s AND s.id_torneo=%s", (ci, torneo))
    return (fila[0]["id_partido"], fila[0]["minuto"]) if len(fila) == 1 else None


def fechas_suspendido(c, ci=JUGADOR, torneo=2):
    return sorted({fecha for _, inicio, cantidad in sanciones(c, ci, torneo)
                   for fecha in range(inicio, inicio + cantidad)})


def suspendidos_en_planilla(c):
    """Cuenta los casos que incumplen RI-9: un jugador en la planilla de una fecha de su sancion."""
    return valor(c, """SELECT COUNT(*) FROM planilla_partido pp
                       JOIN partido p ON p.id_partido=pp.id_partido
                       JOIN sancion_jugador s ON s.ci_jugador=pp.ci_jugador AND s.id_torneo=p.id_torneo
                       WHERE p.numero_fecha BETWEEN s.numero_fecha_inicio
                             AND s.numero_fecha_inicio+s.cantidad_fechas-1""")


class Escenario(CasoTransaccional):
    """Edicion 2 con el equipo 11 en las fechas 1 a 3; JUGADOR y COMPANERO firmaron la fecha 1."""
    def setUp(self):
        super().setUp()
        edicion_prueba(self.c)
        alta_partido(self.c, 101, 1, 11, 12, "2026-11-02")
        alta_partido(self.c, 102, 2, 11, 13, "2026-11-09")
        alta_partido(self.c, 103, 3, 11, 14, "2026-11-16")
        firmar(self.c, 101, 11, [JUGADOR, COMPANERO])

    def amarilla_en_cada_fecha(self):
        """Deja a JUGADOR con una amarilla en cada fecha: la tercera lo sanciona en la fecha 4."""
        firmar(self.c, 102, 11, [JUGADOR])
        firmar(self.c, 103, 11, [JUGADOR])
        for partido in (101, 102, 103):
            tarjeta(self.c, partido, "amarilla")


class SancionAutomatica(Escenario):
    def test_roja_sanciona_la_fecha_siguiente(self):
        """CP-SAN-01 | Una roja sanciona la fecha siguiente | Roja en el partido de la fecha 1 | Sanción por roja de 1 fecha desde la fecha 2, ligada a la tarjeta"""
        tarjeta(self.c, 101, "roja")
        self.assertEqual(sanciones(self.c), [("roja", 2, 1)])
        self.assertEqual(tarjeta_sancionada(self.c), (101, 10))

    def test_dos_amarillas_no_sancionan(self):
        """CP-SAN-02 | Dos amarillas no sancionan | Una amarilla en la fecha 1 y otra en la fecha 2 | El jugador no tiene sanciones"""
        firmar(self.c, 102, 11, [JUGADOR])
        tarjeta(self.c, 101, "amarilla")
        tarjeta(self.c, 102, "amarilla")
        self.assertEqual(sanciones(self.c), [])

    def test_tercera_amarilla_sanciona_la_fecha_siguiente(self):
        """CP-SAN-03 | La tercera amarilla sanciona la fecha siguiente | Una amarilla en cada una de las fechas 1, 2 y 3 | Sanción por acumulación de 1 fecha desde la fecha 4"""
        self.amarilla_en_cada_fecha()
        self.assertEqual(sanciones(self.c), [(ACUMULACION, 4, 1)])
        self.assertEqual(tarjeta_sancionada(self.c), (103, 10))

    def test_la_tercera_se_cuenta_por_fecha_y_no_por_carga(self):
        """CP-SAN-04 | La tercera amarilla se cuenta por fecha, no por carga | Cargar primero la amarilla de la fecha 3 y después las de las fechas 1 y 2 | La sanción queda ligada a la tarjeta de la fecha 3"""
        firmar(self.c, 102, 11, [JUGADOR])
        firmar(self.c, 103, 11, [JUGADOR])
        for partido in (103, 101, 102):
            tarjeta(self.c, partido, "amarilla")
        self.assertEqual(sanciones(self.c), [(ACUMULACION, 4, 1)])
        self.assertEqual(tarjeta_sancionada(self.c), (103, 10))

    def test_seis_amarillas_dan_dos_sanciones(self):
        """CP-SAN-05 | Seis amarillas dan dos sanciones | Seis amarillas en un partido, cargadas sin orden de minuto | Dos sanciones, ligadas a la tercera y la sexta por minuto"""
        for minuto in (30, 10, 20, 60, 50, 40):
            tarjeta(self.c, 101, "amarilla", minuto)
        filas = q(self.c, "SELECT t.minuto FROM sancion_jugador s JOIN tarjeta t ON t.id_tarjeta=s.id_tarjeta "
                          "WHERE s.ci_jugador=%s AND s.id_torneo=2 ORDER BY t.minuto", (JUGADOR,))
        self.assertEqual([fila["minuto"] for fila in filas], [30, 60])

    def test_tres_amarillas_en_el_mismo_minuto(self):
        """CP-SAN-06 | Tres amarillas en el mismo minuto sancionan una vez | Tres amarillas en el minuto 10 del mismo partido | Una sola sanción por acumulación"""
        for _ in range(3):
            tarjeta(self.c, 101, "amarilla")
        self.assertEqual(sanciones(self.c), [(ACUMULACION, 2, 1)])

    def test_la_roja_no_suma_a_la_acumulacion(self):
        """CP-SAN-07 | La roja no suma a la acumulación | Dos amarillas y una roja en el mismo partido | Solo la sanción por roja"""
        tarjeta(self.c, 101, "amarilla", 10)
        tarjeta(self.c, 101, "amarilla", 20)
        tarjeta(self.c, 101, "roja", 30)
        self.assertEqual(sanciones(self.c), [("roja", 2, 1)])

    def test_las_amarillas_no_se_acumulan_entre_ediciones(self):
        """CP-SAN-08 | Las amarillas no se acumulan entre ediciones | Una amarilla en la edición 1 y dos en la edición 2 | El jugador no tiene sanciones en ninguna edición"""
        capitan = "11111111"     # ya tiene una amarilla en el partido 1 de la edicion 1
        firmar(self.c, 101, 11, [capitan])
        tarjeta(self.c, 101, "amarilla", 10, capitan)
        tarjeta(self.c, 101, "amarilla", 20, capitan)
        self.assertEqual(sanciones(self.c, capitan, 1), [])
        self.assertEqual(sanciones(self.c, capitan, 2), [])


class Recalculo(Escenario):
    def test_borrar_la_roja_retira_la_sancion(self):
        """CP-SAN-09 | Borrar la roja retira la sanción | Cargar una roja y borrarla | El jugador queda sin sanciones"""
        tarjeta(self.c, 101, "roja")
        q(self.c, "DELETE FROM tarjeta WHERE id_partido=101")
        self.assertEqual(sanciones(self.c), [])

    def test_borrar_y_reponer_una_amarilla(self):
        """CP-SAN-10 | Borrar y reponer una amarilla recalcula | Con tres amarillas, borrar la segunda y volver a cargarla | Sin sanción al borrarla y sanción desde la fecha 4 al reponerla"""
        self.amarilla_en_cada_fecha()
        q(self.c, "DELETE FROM tarjeta WHERE id_partido=102")
        self.assertEqual(sanciones(self.c), [])
        tarjeta(self.c, 102, "amarilla")
        self.assertEqual(sanciones(self.c), [(ACUMULACION, 4, 1)])

    def test_pasar_amarilla_a_roja(self):
        """CP-SAN-11 | Pasar una amarilla a roja crea la sanción | Cambiar el color de la única amarilla del jugador | Sanción por roja desde la fecha 2"""
        tarjeta(self.c, 101, "amarilla")
        q(self.c, "UPDATE tarjeta SET color='roja' WHERE id_partido=101")
        self.assertEqual(sanciones(self.c), [("roja", 2, 1)])

    def test_pasar_roja_a_amarilla(self):
        """CP-SAN-12 | Pasar una roja a amarilla retira la sanción | Cambiar el color de la roja | El jugador queda sin sanciones"""
        tarjeta(self.c, 101, "roja")
        q(self.c, "UPDATE tarjeta SET color='amarilla' WHERE id_partido=101")
        self.assertEqual(sanciones(self.c), [])

    def test_pasar_a_roja_una_de_tres_amarillas(self):
        """CP-SAN-13 | Pasar a roja una de tres amarillas deja de acumular | Tres amarillas en un partido y cambiar la primera a roja | Queda solo la sanción por roja"""
        for minuto in (10, 20, 30):
            tarjeta(self.c, 101, "amarilla", minuto)
        q(self.c, "UPDATE tarjeta SET color='roja' WHERE id_partido=101 AND minuto=10")
        self.assertEqual(sanciones(self.c), [("roja", 2, 1)])

    def test_cambiar_el_minuto_recalcula(self):
        """CP-SAN-14 | Cambiar el minuto recalcula la tarjeta que sanciona | Amarillas a los 10, 20 y 30 y pasar la primera al minuto 40 | La sanción queda ligada a la tarjeta del minuto 40"""
        for minuto in (10, 20, 30):
            tarjeta(self.c, 101, "amarilla", minuto)
        q(self.c, "UPDATE tarjeta SET minuto=40 WHERE id_partido=101 AND minuto=10")
        self.assertEqual(tarjeta_sancionada(self.c), (101, 40))

    def test_mover_la_roja_a_otro_jugador(self):
        """CP-SAN-15 | Mover la roja a otro jugador traslada la sanción | Cambiar el jugador de la tarjeta por un compañero en planilla | El primero queda sin sanción y el compañero sancionado desde la fecha 2"""
        tarjeta(self.c, 101, "roja")
        q(self.c, "UPDATE tarjeta SET ci_jugador=%s WHERE id_partido=101", (COMPANERO,))
        self.assertEqual(sanciones(self.c), [])
        self.assertEqual(sanciones(self.c, COMPANERO), [("roja", 2, 1)])

    def test_mover_una_amarilla_recalcula_a_los_dos(self):
        """CP-SAN-16 | Mover una amarilla recalcula a los dos jugadores | Pasar una de tres amarillas a un compañero que ya tenía dos | El primero queda sin sanción y el compañero sancionado"""
        for minuto in (10, 20, 30):
            tarjeta(self.c, 101, "amarilla", minuto)
        tarjeta(self.c, 101, "amarilla", 40, COMPANERO)
        tarjeta(self.c, 101, "amarilla", 50, COMPANERO)
        q(self.c, "UPDATE tarjeta SET ci_jugador=%s WHERE id_partido=101 AND minuto=10", (COMPANERO,))
        self.assertEqual(sanciones(self.c), [])
        self.assertEqual(sanciones(self.c, COMPANERO), [(ACUMULACION, 2, 1)])

    def test_no_se_mueve_la_tarjeta_a_quien_no_firmo(self):
        """CP-SAN-17 | No se mueve la tarjeta a quien no firmó | Cambiar el jugador de la roja por uno que no está en planilla | Rechazo por clave foránea y la sanción sigue igual"""
        tarjeta(self.c, 101, "roja")
        self.rechaza("UPDATE tarjeta SET ci_jugador=%s WHERE id_partido=101", "foreign key", (SUPLENTE,))
        self.assertEqual(sanciones(self.c), [("roja", 2, 1)])

    def test_mover_la_tarjeta_a_otro_partido(self):
        """CP-SAN-18 | Mover la tarjeta a otro partido mueve la sanción | Pasar la roja de la fecha 1 a la fecha 2 | La sanción pasa a la fecha 3"""
        firmar(self.c, 102, 11, [JUGADOR])
        tarjeta(self.c, 101, "roja")
        q(self.c, "UPDATE tarjeta SET id_partido=102 WHERE id_partido=101")
        self.assertEqual(sanciones(self.c), [("roja", 3, 1)])

    def test_quitar_de_planilla_retira_la_sancion(self):
        """CP-SAN-19 | Quitar de planilla retira la sanción | Roja y luego quitar al jugador de la planilla | Se borran la tarjeta y la sanción"""
        tarjeta(self.c, 101, "roja")
        q(self.c, "DELETE FROM planilla_partido WHERE id_partido=101 AND ci_jugador=%s", (JUGADOR,))
        self.assertEqual(valor(self.c, "SELECT COUNT(*) FROM tarjeta WHERE id_partido=101"), 0)
        self.assertEqual(sanciones(self.c), [])

    def test_borrar_partido_programado_no_deja_huerfanas(self):
        """CP-SAN-20 | Borrar un partido programado no deja sanciones huérfanas | Roja en un partido programado y borrar el partido | No quedan tarjetas ni sanciones de ese partido"""
        tarjeta(self.c, 101, "roja")
        self.acepta("DELETE FROM partido WHERE id_partido=101")
        self.assertEqual(valor(self.c, "SELECT COUNT(*) FROM tarjeta WHERE id_partido=101"), 0)
        self.assertEqual(sanciones(self.c), [])

    def test_borrar_partido_recalcula_la_acumulacion(self):
        """CP-SAN-21 | Borrar un partido recalcula la acumulación | Tres amarillas en tres fechas y borrar el partido de la fecha 2 | El jugador queda sin sanciones"""
        self.amarilla_en_cada_fecha()
        self.acepta("DELETE FROM partido WHERE id_partido=102")
        self.assertEqual(sanciones(self.c), [])


class Suspension(Escenario):
    def test_suspendido_por_roja_no_firma(self):
        """CP-SAN-22 | Suspendido por roja no firma | Roja en la fecha 1 y firmar en la fecha 2 | Rechazo: el jugador está suspendido"""
        tarjeta(self.c, 101, "roja")
        self.rechaza(FIRMAR, "suspendido", (102, JUGADOR))

    def test_suspendido_por_acumulacion_no_firma(self):
        """CP-SAN-23 | Suspendido por acumulación no firma | Tres amarillas en la fecha 1 y firmar en la fecha 2 | Rechazo: el jugador está suspendido"""
        for minuto in (10, 20, 30):
            tarjeta(self.c, 101, "amarilla", minuto)
        self.rechaza(FIRMAR, "suspendido", (102, JUGADOR))

    def test_sancion_de_dos_fechas_bloquea_ambas(self):
        """CP-SAN-24 | Una sanción de dos fechas bloquea ambas | Sanción disciplinaria en las fechas 1 y 2 y firmar en las fechas 1, 2 y 3 | Rechazo en las fechas 1 y 2 y firma aceptada en la 3"""
        manual(self.c, 1, 2, SUPLENTE)
        self.rechaza(FIRMAR, "suspendido", (101, SUPLENTE))
        self.rechaza(FIRMAR, "suspendido", (102, SUPLENTE))
        self.acepta(FIRMAR, (103, SUPLENTE))

    def test_sin_sancion_firma(self):
        """CP-SAN-25 | Un jugador sin sanción firma | Firmar en la fecha 2 sin sanciones | La firma se acepta"""
        self.acepta(FIRMAR, (102, JUGADOR))

    def test_cumplida_la_suspension_firma(self):
        """CP-SAN-26 | Cumplida la suspensión vuelve a firmar | Roja en la fecha 1 y firmar en la fecha 3 | La firma se acepta"""
        tarjeta(self.c, 101, "roja")
        self.acepta(FIRMAR, (103, JUGADOR))

    def test_borrada_la_tarjeta_vuelve_a_firmar(self):
        """CP-SAN-27 | Borrada la tarjeta el jugador firma | Roja en la fecha 1, borrarla y firmar en la fecha 2 | La firma se acepta"""
        tarjeta(self.c, 101, "roja")
        q(self.c, "DELETE FROM tarjeta WHERE id_partido=101")
        self.acepta(FIRMAR, (102, JUGADOR))

    def test_la_sancion_de_otra_edicion_no_bloquea(self):
        """CP-SAN-28 | La sanción de otra edición no bloquea | Sanción en la fecha 4 de la edición 2 y firmar la fecha 4 de la edición 1 | La firma se acepta"""
        manual(self.c, 4, 1, SUPLENTE)
        self.acepta("INSERT INTO planilla_partido (id_partido,ci_jugador,id_equipo) VALUES (10,%s,1)", (SUPLENTE,))

    def test_los_datos_de_prueba_cumplen_la_regla(self):
        """CP-SAN-29 | Los datos de prueba no tienen suspendidos en planilla | Cruzar planillas y sanciones de los datos cargados | Ningún suspendido figura en la planilla de su fecha"""
        self.assertEqual(suspendidos_en_planilla(self.c), 0)


class SancionManual(Escenario):
    def test_el_recalculo_no_toca_la_sancion_manual(self):
        """CP-SAN-30 | El recálculo no toca la sanción manual | Sanción disciplinaria y luego cargar y borrar una roja del mismo jugador | La sanción disciplinaria sigue igual"""
        manual(self.c, 3, 2)
        tarjeta(self.c, 101, "roja")
        self.assertEqual(sanciones(self.c), [("roja", 2, 1), ("disciplinaria", 3, 2)])
        q(self.c, "DELETE FROM tarjeta WHERE id_partido=101")
        self.assertEqual(sanciones(self.c), [("disciplinaria", 3, 2)])

    def test_sancion_a_jugador_fuera_de_la_edicion(self):
        """CP-SAN-31 | No se sanciona a quien no integra la edición | Sanción a un jugador sin plantel en la edición 2 | Rechazo por clave foránea"""
        self.rechaza(SANCION, "foreign key", ("55555551", 2, "disciplinaria", 2, 1))

    def test_fecha_inicial_y_duracion_minimas(self):
        """CP-SAN-32 | La sanción exige fecha inicial y duración válidas | Sanciones con fecha inicial 0 y con duración 0 | Rechazo por las restricciones CHECK"""
        self.rechaza(SANCION, "chk_sancion_fecha_inicio", (JUGADOR, 2, "disciplinaria", 0, 1))
        self.rechaza(SANCION, "chk_sancion_cantidad", (JUGADOR, 2, "disciplinaria", 2, 0))

    def test_cambiar_la_ci_de_un_jugador_sin_sancion(self):
        """CP-SAN-33 | Cambiar la CI de un jugador sin sanción | Actualizar la CI de un jugador con plantel y planillas | La CI cambia en cascada en planteles y planillas"""
        self.acepta("UPDATE jugador SET ci='11111119' WHERE ci=%s", (COMPANERO,))
        self.assertEqual(valor(self.c, "SELECT COUNT(*) FROM equipo_jugador_torneo WHERE ci_jugador='11111119'"), 2)
        self.assertEqual(valor(self.c, "SELECT COUNT(*) FROM planilla_partido WHERE ci_jugador='11111119'"), 3)


class DefectosConocidos(Escenario):
    @defecto("REG-08", "Se aceptó: el jugador quedó suspendido en una fecha que ya había firmado.")
    def test_sancion_manual_sobre_fecha_firmada(self):
        """CP-SAN-34 | Sanción manual sobre una fecha ya firmada | El jugador firma la fecha 2 y luego se carga su sanción para esa fecha | Ningún suspendido queda en planilla"""
        firmar(self.c, 102, 11, [JUGADOR])
        intentar(self.c, SANCION, (JUGADOR, 2, "disciplinaria", 2, 1))
        self.assertEqual(suspendidos_en_planilla(self.c), 0)

    @defecto("REG-08", "Se aceptó: la sanción movida por UPDATE cubre una fecha que el jugador ya firmó.")
    def test_mover_sancion_manual_a_fecha_firmada(self):
        """CP-SAN-35 | Mover una sanción manual a una fecha ya firmada | Sanción en la fecha 3 y cambiarla a la fecha 2, ya firmada | Ningún suspendido queda en planilla"""
        firmar(self.c, 102, 11, [JUGADOR])
        manual(self.c, 3)
        intentar(self.c, "UPDATE sancion_jugador SET numero_fecha_inicio=2 WHERE ci_jugador=%s AND id_torneo=2", (JUGADOR,))
        self.assertEqual(suspendidos_en_planilla(self.c), 0)

    @defecto("REG-08", "Se aceptó: la roja de la fecha 1 suspendió al jugador en la fecha 2, que ya había firmado.")
    def test_roja_cargada_despues_de_firmar_la_fecha_siguiente(self):
        """CP-SAN-36 | Roja cargada después de firmar la fecha siguiente | Firmar las fechas 1 y 2 y recién entonces cargar la roja de la fecha 1 | Ningún suspendido queda en planilla"""
        firmar(self.c, 102, 11, [JUGADOR])
        intentar(self.c, TARJETA, (101, JUGADOR, 10, "roja"))
        self.assertEqual(suspendidos_en_planilla(self.c), 0)

    @defecto("REG-08", "Se aceptó: la tercera amarilla suspendió al jugador en una fecha que ya había firmado.")
    def test_tercera_amarilla_cargada_despues_de_firmar(self):
        """CP-SAN-37 | Tercera amarilla cargada después de firmar la fecha siguiente | Dos amarillas, firmar la fecha 2 y cargar la tercera en la fecha 1 | Ningún suspendido queda en planilla"""
        tarjeta(self.c, 101, "amarilla", 10)
        tarjeta(self.c, 101, "amarilla", 20)
        firmar(self.c, 102, 11, [JUGADOR])
        intentar(self.c, TARJETA, (101, JUGADOR, 30, "amarilla"))
        self.assertEqual(suspendidos_en_planilla(self.c), 0)

    @defecto("REG-09", "La sanción pasó de la fecha 4 a la fecha 3, ya jugada: la suspensión nunca se cumple.")
    def test_el_recalculo_no_mueve_a_una_fecha_jugada(self):
        """CP-SAN-38 | El recálculo no mueve la suspensión a una fecha jugada | Con la sanción en la fecha 4 y la fecha 3 jugada, agregar una amarilla en la fecha 2 | La suspensión sigue en la fecha 4"""
        q(self.c, "UPDATE partido SET dia='2026-11-10' WHERE id_partido=103")
        self.amarilla_en_cada_fecha()
        mover_reloj(self.c, "2026-11-10 20:00:00")
        q(self.c, "UPDATE partido SET estado='jugado' WHERE id_partido IN (101,102,103)")
        intentar(self.c, TARJETA, (102, JUGADOR, 20, "amarilla"))
        self.assertEqual(sanciones(self.c), [(ACUMULACION, 4, 1)])

    @defecto("REG-10", "La tarjeta y la sanción siguen vigentes con el partido cancelado.")
    def test_cancelar_el_partido_retira_la_sancion(self):
        """CP-SAN-39 | Cancelar el partido retira su sanción | Roja en un partido que luego se cancela | El jugador queda sin sanciones"""
        tarjeta(self.c, 101, "roja")
        q(self.c, "UPDATE partido SET estado='cancelado' WHERE id_partido=101")
        self.assertEqual(sanciones(self.c), [])

    @defecto("REG-10", "La amarilla del partido cancelado se contó: hay una sanción por acumulación.")
    def test_amarilla_de_partido_cancelado_no_acumula(self):
        """CP-SAN-40 | La amarilla de un partido cancelado no acumula | Amarilla en la fecha 1, cancelar ese partido y amarillas en las fechas 2 y 3 | El jugador no tiene sanciones"""
        firmar(self.c, 102, 11, [JUGADOR])
        firmar(self.c, 103, 11, [JUGADOR])
        tarjeta(self.c, 101, "amarilla")
        q(self.c, "UPDATE partido SET estado='cancelado' WHERE id_partido=101")
        tarjeta(self.c, 102, "amarilla")
        tarjeta(self.c, 103, "amarilla")
        self.assertEqual(sanciones(self.c), [])

    @defecto("REG-10", "La sanción siguió en la fecha 2 con el partido pasado a la fecha 4.")
    def test_cambiar_el_numero_de_fecha_mueve_la_sancion(self):
        """CP-SAN-41 | Cambiar el número de fecha mueve la sanción | Roja en la fecha 1 y pasar ese partido a la fecha 4 | La sanción pasa a la fecha 5"""
        tarjeta(self.c, 101, "roja")
        q(self.c, "UPDATE partido SET numero_fecha=4 WHERE id_partido=101")
        self.assertEqual(sanciones(self.c), [("roja", 5, 1)])

    @defecto("REG-10", "La sanción quedó en la fecha 2, que el jugador ya había jugado: nunca se cumple.")
    def test_roja_en_partido_postergado(self):
        """CP-SAN-42 | Roja en un partido postergado cae en una fecha por jugar | Postergar la fecha 1, jugar la fecha 2 y recién después cargar la roja de la fecha 1 | La sanción cae en la fecha 3"""
        q(self.c, "UPDATE partido SET estado='postergado' WHERE id_partido=101")
        firmar(self.c, 102, 11, [JUGADOR])
        mover_reloj(self.c, "2026-11-10 12:00:00")
        q(self.c, "UPDATE partido SET estado='jugado' WHERE id_partido=102")
        q(self.c, "UPDATE partido SET estado='programado',dia='2026-11-11' WHERE id_partido=101")
        tarjeta(self.c, 101, "roja")
        self.assertEqual(sanciones(self.c), [("roja", 3, 1)])

    @defecto("REG-10", "Se aceptó: el partido ya firmado pasó a la fecha de la suspensión del jugador.")
    def test_mover_partido_firmado_a_la_fecha_de_la_suspension(self):
        """CP-SAN-43 | Mover un partido firmado a la fecha de una suspensión | El jugador firma la fecha 2, tiene sanción en la fecha 4 y el partido pasa a la fecha 4 | Ningún suspendido queda en planilla"""
        firmar(self.c, 102, 11, [JUGADOR])
        manual(self.c, 4)
        intentar(self.c, "UPDATE partido SET numero_fecha=4 WHERE id_partido=102")
        self.assertEqual(suspendidos_en_planilla(self.c), 0)

    @defecto("REG-19", "Se aceptó: quedó una sanción por roja sin ninguna tarjeta que la origine.")
    def test_sancion_por_roja_sin_tarjeta(self):
        """CP-SAN-44 | Sanción manual con motivo roja | Insertar una sanción con motivo roja y sin tarjeta | Rechazo: ese motivo solo lo genera el sistema"""
        self.rechaza(SANCION, args=(JUGADOR, 2, "roja", 2, 1))

    @defecto("REG-19", "Se aceptó: quedó una sanción por acumulación sin ninguna tarjeta que la origine.")
    def test_sancion_por_acumulacion_sin_tarjeta(self):
        """CP-SAN-45 | Sanción manual con motivo acumulación de amarillas | Insertar una sanción por acumulación y sin tarjeta | Rechazo: ese motivo solo lo genera el sistema"""
        self.rechaza(SANCION, args=(JUGADOR, 2, ACUMULACION, 2, 1))

    @defecto("REG-19", "Se aceptó: la sanción de un jugador quedó ligada a la tarjeta de otro.")
    def test_sancion_con_tarjeta_de_otro_jugador(self):
        """CP-SAN-46 | Sanción ligada a la tarjeta de otro jugador | Insertar una sanción con la tarjeta de un compañero | Rechazo: la tarjeta debe ser del sancionado"""
        tarjeta(self.c, 101, "amarilla", ci=COMPANERO)
        id_tarjeta = valor(self.c, "SELECT id_tarjeta FROM tarjeta WHERE id_partido=101")
        self.rechaza("INSERT INTO sancion_jugador (ci_jugador,id_torneo,motivo,numero_fecha_inicio,cantidad_fechas,"
                     "id_tarjeta) VALUES (%s,2,'disciplinaria',2,1,%s)", args=(JUGADOR, id_tarjeta))

    @defecto("REG-17", "Se aceptó: por SQL la sanción por roja pasó a 5 fechas; solo la aplicación lo impide.")
    def test_sancion_automatica_no_se_edita_por_sql(self):
        """CP-SAN-47 | Una sanción automática no se edita por SQL | Cambiar a 5 fechas la sanción generada por una roja | Rechazo: esa sanción solo la maneja el recálculo"""
        tarjeta(self.c, 101, "roja")
        self.rechaza("UPDATE sancion_jugador SET cantidad_fechas=5 WHERE ci_jugador=%s AND id_torneo=2", args=(JUGADOR,))

    @defecto("REG-21", "Las dos sanciones quedaron en la fecha 4: el jugador cumple una sola fecha.")
    def test_roja_y_tercera_amarilla_no_se_solapan(self):
        """CP-SAN-48 | Roja y tercera amarilla en el mismo partido | Tercera amarilla y roja en la fecha 3 | Se cumplen dos fechas distintas de suspensión"""
        self.amarilla_en_cada_fecha()
        tarjeta(self.c, 103, "roja", 20)
        self.assertEqual(fechas_suspendido(self.c), [4, 5])

    @defecto("REG-22", "Error 1452: la doble cascada hacia sancion_jugador impide cambiar la CI.")
    def test_cambiar_la_ci_de_un_jugador_sancionado(self):
        """CP-SAN-49 | Cambiar la CI de un jugador sancionado | Actualizar la CI de un jugador con sanción disciplinaria | La CI cambia y la sanción la acompaña"""
        self.acepta("UPDATE jugador SET ci='66666669' WHERE ci='66666662'")
        self.assertEqual(sanciones(self.c, "66666669", 1), [("disciplinaria", 2, 2)])


class SancionesEnLaApp(CasoWeb):
    def setUp(self):
        super().setUp()
        ayer = (date.today() - timedelta(days=1)).isoformat()
        edicion_prueba(self.c)
        alta_partido(self.c, 101, 1, 11, 12, ayer)
        alta_partido(self.c, 102, 2, 11, 13, ayer, turno=2)
        firmar(self.c, 101, 11, [JUGADOR])

    def alta_por_formulario(self, cliente, fecha):
        return self.enviar(cliente, "/catalogo/sancion_jugador/nuevo",
                           {"ci_jugador": JUGADOR, "id_torneo": "2", "numero_fecha_inicio": str(fecha),
                            "cantidad_fechas": "1"}, desde="/catalogo/sancion_jugador/nuevo")

    def test_roja_cargada_en_la_app_suspende(self):
        """CP-SAN-50 | Una roja cargada en la app suspende al jugador | El planillero carga la roja e intenta firmarlo en la fecha 2 | Se crea la sanción, figura Suspendido y la firma se rechaza"""
        cliente, _ = self.ingresar(WEB_PLANILLERO)
        respuesta = self.enviar(cliente, "/partidos/101/tarjeta", {"ci_jugador": JUGADOR, "minuto": "20", "color": "roja"},
                                desde="/partidos/101")
        self.assertIn("Evento registrado correctamente.", avisos(respuesta.text))
        self.assertEqual(sanciones(self.c), [("roja", 2, 1)])
        self.assertIn("Suspendido", cliente.get("/partidos/102").text)
        respuesta = self.enviar(cliente, "/partidos/102/planilla", {"ci": JUGADOR, "equipo": "11"}, desde="/partidos/102")
        self.assertIn("suspendido", " ".join(avisos(respuesta.text)))
        self.assertEqual(valor(self.c, "SELECT COUNT(*) FROM planilla_partido WHERE id_partido=102"), 0)

    def test_alta_de_sancion_por_formulario(self):
        """CP-SAN-51 | Alta de sanción disciplinaria por formulario | El administrador indica jugador, edición, fecha y duración | Se guarda con motivo disciplinaria y sin tarjeta"""
        cliente, _ = self.ingresar(WEB_ADMIN)
        respuesta = self.alta_por_formulario(cliente, 3)
        self.assertIn("Registro creado correctamente.", avisos(respuesta.text))
        self.assertEqual(sanciones(self.c), [("disciplinaria", 3, 1)])
        self.assertIsNone(valor(self.c, "SELECT id_tarjeta FROM sancion_jugador WHERE ci_jugador=%s AND id_torneo=2", (JUGADOR,)))

    def test_la_app_no_toca_las_sanciones_automaticas(self):
        """CP-SAN-52 | La app no edita ni borra sanciones automáticas | Abrir por URL la edición y la baja de la sanción de una roja | Error 403 al editar y la sanción sigue vigente"""
        id_sancion = valor(self.c, "SELECT id_sancion FROM sancion_jugador WHERE motivo='roja'")
        cliente, _ = self.ingresar(WEB_ADMIN)
        self.assertEqual(cliente.get(f"/catalogo/sancion_jugador/{id_sancion}/editar").status_code, 403)
        self.enviar(cliente, f"/catalogo/sancion_jugador/{id_sancion}/eliminar", desde="/catalogo/sancion_jugador")
        self.assertEqual(valor(self.c, "SELECT COUNT(*) FROM sancion_jugador WHERE id_sancion=%s", (id_sancion,)), 1)

    @defecto("REG-08", "Se aceptó: el formulario registró la sanción sobre una fecha que el jugador ya había firmado.")
    def test_formulario_de_sancion_sobre_fecha_firmada(self):
        """CP-SAN-53 | Formulario de sanción sobre una fecha ya firmada | El administrador sanciona en la fecha 1 a un jugador que ya la firmó | Ningún suspendido queda en planilla"""
        cliente, _ = self.ingresar(WEB_ADMIN)
        self.alta_por_formulario(cliente, 1)
        self.assertEqual(suspendidos_en_planilla(self.c), 0)
