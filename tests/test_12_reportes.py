"""Reportes de app/reports.py: valores exactos, pantallas, casos borde y defectos REP-02 y REP-03."""
import sys
from datetime import date, timedelta
from decimal import Decimal

from base import (FACULTAD, RAIZ, WEB_ADMIN, WEB_PLANILLERO, CasoAislado, CasoTransaccional, CasoWeb,
                  alta_partido, avisos, defecto, edicion_prueba, firmar, q)

sys.path.insert(0, str(RAIZ / "app"))
from reports import REPORTS

FACULTADES = [
    ("Administracion", "grado", 4), ("Administracion", "posgrado", 1), ("Arquitectura", "grado", 5),
    ("Derecho", "grado", 4), ("Derecho", "docente", 1), ("Ingenieria", "grado", 5), ("Ingenieria", "docente", 1),
    ("Medicina", "grado", 4), ("Medicina", "funcionario", 1), ("Psicologia", "grado", 4),
    ("Psicologia", "posgrado", 1),
]
CANCHAS_SIN_PARTIDOS = [
    ("Complejo Deportivo Central", "Cancha 1", 0), ("Complejo Deportivo Central", "Cancha 2", 0),
    ("Complejo Deportivo Norte", "Cancha A", 0), ("Complejo Deportivo Norte", "Cancha B", 0),
]
TURNOS_SIN_PARTIDOS = [
    ("18:00:00", "19:00:00", 0), ("19:00:00", "20:00:00", 0), ("20:00:00", "21:00:00", 0),
    ("21:00:00", "22:00:00", 0), ("22:00:00", "23:00:00", 0),
]
# Cantidad de filas de cada reporte en la edición 1 (fecha 2), para comprobar la pantalla.
FILAS_EDICION_1 = {"posiciones": 6, "goleadores": 7, "fairplay": 6, "goles_fecha": 3, "goles_global": 1,
                   "canchas": 4, "turnos": 5, "facultades": 11, "sin_planilla": 1, "sanciones": 2, "estados": 1,
                   "asistencia": 6, "inhabilitados": 2, "valla": 6}
# Reportes que en una edición sin equipos ni partidos no tienen ninguna fila que mostrar.
SIN_FILAS_EN_EDICION_VACIA = ("posiciones", "goleadores", "fairplay", "goles_fecha", "sin_planilla", "sanciones",
                              "asistencia", "inhabilitados", "valla")


def plano(dato):
    """Lleva los tipos de PyMySQL a literales comparables: DECIMAL a número y TIME a texto."""
    if isinstance(dato, Decimal):
        return float(dato)
    if isinstance(dato, timedelta):
        return str(dato)
    return dato


def reporte(c, slug, torneo=1, fecha=2):
    """Ejecuta el SQL real del reporte y devuelve cada fila como tupla, en el orden de sus columnas."""
    filas = q(c, REPORTS[slug][2], {"torneo": torneo, "fecha": fecha})
    return [tuple(plano(dato) for dato in fila.values()) for fila in filas]


def ayer():
    return (date.today() - timedelta(days=1)).isoformat()


def gol(c, partido, ci, minuto, autogol=0):
    q(c, "INSERT INTO gol (id_partido,ci_jugador,minuto,autogol) VALUES (%s,%s,%s,%s)",
      (partido, ci, minuto, autogol))


def tarjeta(c, partido, ci, minuto, color):
    q(c, "INSERT INTO tarjeta (id_partido,ci_jugador,minuto,color) VALUES (%s,%s,%s,%s)",
      (partido, ci, minuto, color))


def marcar(c, estado, *partidos):
    for partido in partidos:
        q(c, "UPDATE partido SET estado=%s WHERE id_partido=%s", (estado, partido))


def alta_edicion_vacia(c):
    q(c, "INSERT INTO torneo (id_torneo,nombre,anio,semestre,fecha_inicio,fecha_fin,estado) VALUES "
         "(3,'Vacía',2028,1,'2028-03-01','2028-06-30','inscripcion')")


class DatosDePrueba(CasoTransaccional):
    """Cada reporte contra sus valores exactos en la edición 1 de los datos de prueba."""

    def test_posiciones(self):
        """CP-REP-01 | Tabla de posiciones | Edición 1 de los datos de prueba | Seis equipos en orden, con Ingenieria FC primero con 9 puntos y todos los valores exactos"""
        self.assertEqual(reporte(self.c, "posiciones"), [
            ("Ingenieria FC", 3, 3, 0, 0, 4, 1, 3, 9),
            ("Administracion United", 3, 2, 0, 1, 3, 2, 1, 6),
            ("Derecho Athletic", 3, 2, 0, 1, 2, 1, 1, 6),
            ("Arquitectura City", 3, 1, 0, 2, 2, 2, 0, 3),
            ("Medicina Juniors", 3, 1, 0, 2, 1, 2, -1, 3),
            ("Psicologia Sporting", 3, 0, 0, 3, 0, 4, -4, 0),
        ])

    def test_goleadores(self):
        """CP-REP-02 | Top 10 goleadores | Edición 1 de los datos de prueba | Siete jugadores, encabezados por Sofia Martinez y Juan Perez con 3 goles"""
        self.assertEqual(reporte(self.c, "goleadores"), [
            ("22222221", "Sofia Martinez", "Administracion United", 3),
            ("11111111", "Juan Perez", "Ingenieria FC", 3),
            ("33333331", "Camila Sosa", "Derecho Athletic", 2),
            ("11111112", "Carlos Gomez", "Ingenieria FC", 1),
            ("55555552", "Santiago Juarez", "Arquitectura City", 1),
            ("44444441", "Mariana Medina", "Medicina Juniors", 1),
            ("55555551", "Victoria Ponce", "Arquitectura City", 1),
        ])

    def test_fairplay(self):
        """CP-REP-03 | Fair play | Edición 1 de los datos de prueba | Seis equipos por puntaje, de 0 a 3, con Psicologia Sporting último por una roja"""
        self.assertEqual(reporte(self.c, "fairplay"), [
            ("Administracion United", 0, 0, 0),
            ("Arquitectura City", 0, 0, 0),
            ("Medicina Juniors", 0, 0, 0),
            ("Ingenieria FC", 1, 0, 1),
            ("Derecho Athletic", 2, 0, 2),
            ("Psicologia Sporting", 0, 1, 3),
        ])

    def test_goles_por_fecha(self):
        """CP-REP-04 | Promedio de goles por fecha | Edición 1 de los datos de prueba | Fecha 1 con 6 goles y promedio 2.00; fechas 2 y 3 con 3 goles y promedio 1.00"""
        self.assertEqual(reporte(self.c, "goles_fecha"), [(1, 3, 6, 2.0), (2, 3, 3, 1.0), (3, 3, 3, 1.0)])

    def test_goles_por_edicion(self):
        """CP-REP-05 | Promedio de goles por edición | Edición 1 de los datos de prueba | 9 partidos, 12 goles y promedio 1.33"""
        self.assertEqual(reporte(self.c, "goles_global"), [(9, 12, 1.33)])

    def test_canchas(self):
        """CP-REP-06 | Canchas más utilizadas | Edición 1 de los datos de prueba | Cancha 1 con 7 partidos, Cancha A con 2, Cancha 2 y Cancha B con 0"""
        self.assertEqual(reporte(self.c, "canchas"), [
            ("Complejo Deportivo Central", "Cancha 1", 7),
            ("Complejo Deportivo Norte", "Cancha A", 2),
            ("Complejo Deportivo Central", "Cancha 2", 0),
            ("Complejo Deportivo Norte", "Cancha B", 0),
        ])

    def test_turnos(self):
        """CP-REP-07 | Turnos más utilizados | Edición 1 de los datos de prueba | Tres turnos con 3 partidos; los de las 21:00 y las 22:00 con 0"""
        self.assertEqual(reporte(self.c, "turnos"), [
            ("18:00:00", "19:00:00", 3), ("19:00:00", "20:00:00", 3), ("20:00:00", "21:00:00", 3),
            ("21:00:00", "22:00:00", 0), ("22:00:00", "23:00:00", 0),
        ])

    def test_facultades(self):
        """CP-REP-08 | Jugadores por facultad y tipo | Edición 1 de los datos de prueba | Once combinaciones de facultad y tipo con sus cantidades exactas"""
        self.assertEqual(reporte(self.c, "facultades"), FACULTADES)

    def test_sin_planilla(self):
        """CP-REP-09 | Inscriptos que nunca jugaron | Edición 1 de los datos de prueba | Solo Ana Fernandez, docente de Ingenieria FC"""
        self.assertEqual(reporte(self.c, "sin_planilla"),
                         [("Ingenieria FC", "11111116", "Ana Fernandez", "docente")])

    def test_sanciones(self):
        """CP-REP-10 | Sanciones por equipo y motivo | Edición 1 de los datos de prueba | Psicologia Sporting con una sanción por roja y una disciplinaria"""
        # Las dos filas empatan en equipo y cantidad, los criterios del reporte: su orden no está definido.
        self.assertEqual(sorted(reporte(self.c, "sanciones")), [
            ("Psicologia Sporting", "disciplinaria", 1),
            ("Psicologia Sporting", "roja", 1),
        ])

    def test_estados(self):
        """CP-REP-11 | Jugados contra postergados y cancelados | Edición 1 de los datos de prueba | 15 partidos: 9 jugados, 1 postergado, 0 cancelados, 5 programados; 60.00 y 6.67 por ciento"""
        self.assertEqual(reporte(self.c, "estados"), [(15, 9, 1, 0, 5, 60.0, 6.67)])

    def test_asistencia(self):
        """CP-REP-12 | Asistencia perfecta | Edición 1 de los datos de prueba | Un jugador por equipo, seis en total"""
        self.assertEqual(reporte(self.c, "asistencia"), [
            ("22222221", "Sofia Martinez", "Administracion United"),
            ("55555551", "Victoria Ponce", "Arquitectura City"),
            ("33333331", "Camila Sosa", "Derecho Athletic"),
            ("11111111", "Juan Perez", "Ingenieria FC"),
            ("44444441", "Mariana Medina", "Medicina Juniors"),
            ("66666663", "Paula Machado", "Psicologia Sporting"),
        ])

    def test_inhabilitados(self):
        """CP-REP-13 | Inhabilitados para una fecha | Fechas 2, 3 y 4 de la edición 1 | Dos jugadores en la fecha 2, uno en la 3 y ninguno en la 4"""
        cardozo = ("Psicologia Sporting", "Emiliano Cardozo", "disciplinaria", 2, 3)
        self.assertEqual(reporte(self.c, "inhabilitados", fecha=2),
                         [("Psicologia Sporting", "Catalina Pintos", "roja", 2, 2), cardozo])
        self.assertEqual(reporte(self.c, "inhabilitados", fecha=3), [cardozo])
        self.assertEqual(reporte(self.c, "inhabilitados", fecha=4), [])

    def test_valla(self):
        """CP-REP-14 | Valla menos vencida | Edición 1 de los datos de prueba | Seis equipos con valores exactos, ordenados por promedio y vallas invictas"""
        filas = reporte(self.c, "valla")
        # Estos datos tienen empates y su orden no está definido (defecto REP-02): se comparan los valores
        # sin importar el orden y, aparte, que se respeten los criterios que el reporte sí define.
        self.assertEqual(sorted(filas), [
            ("Administracion United", 3, 2, 2, 0.67),
            ("Arquitectura City", 3, 2, 1, 0.67),
            ("Derecho Athletic", 3, 1, 2, 0.33),
            ("Ingenieria FC", 3, 1, 2, 0.33),
            ("Medicina Juniors", 3, 2, 1, 0.67),
            ("Psicologia Sporting", 3, 4, 0, 1.33),
        ])
        criterios = [(promedio, -invictas, recibidos) for _, _, recibidos, invictas, promedio in filas]
        self.assertEqual(criterios, sorted(criterios))


class EscenarioAutogolesYEmpate(CasoTransaccional):
    """Edición 2, fecha 1: A le gana 3-2 a B con tres autogoles; C y D empatan 0-0."""

    def setUp(self):
        super().setUp()
        edicion_prueba(self.c)
        alta_partido(self.c, 101, 1, 11, 12, ayer())
        alta_partido(self.c, 102, 1, 13, 14, ayer(), turno=2)
        firmar(self.c, 101, 11, ["11111111", "11111112"])
        firmar(self.c, 101, 12, ["22222221", "22222222"])
        firmar(self.c, 102, 13, ["33333331"])
        firmar(self.c, 102, 14, ["44444441"])
        gol(self.c, 101, "11111111", 5)
        gol(self.c, 101, "22222221", 10, autogol=1)
        gol(self.c, 101, "22222222", 15)
        gol(self.c, 101, "22222222", 20, autogol=1)
        gol(self.c, 101, "11111112", 25, autogol=1)
        marcar(self.c, "jugado", 101, 102)

    def test_autogol_suma_al_rival(self):
        """CP-REP-15 | Autogol suma al rival en posiciones | A gana 3-2 a B con tres autogoles | A con 3 a favor, 2 en contra y 3 puntos; B con 2 a favor, 3 en contra y 0 puntos"""
        filas = {fila[0]: fila[1:] for fila in reporte(self.c, "posiciones", torneo=2)}
        self.assertEqual(filas["A"], (1, 1, 0, 0, 3, 2, 1, 3))
        self.assertEqual(filas["B"], (1, 0, 0, 1, 2, 3, -1, 0))

    def test_autogol_no_cuenta_para_el_goleador(self):
        """CP-REP-16 | Autogol no cuenta para el goleador | Autogoles de tres jugadores, uno de ellos también con gol propio | Solo Juan Perez y Lucia Suarez, con un gol cada uno"""
        self.assertEqual(reporte(self.c, "goleadores", torneo=2),
                         [("11111111", "Juan Perez", "A", 1), ("22222222", "Lucia Suarez", "B", 1)])

    def test_autogol_cuenta_en_los_promedios(self):
        """CP-REP-17 | Autogol cuenta en los promedios de goles | Fecha con un 3-2 con autogoles y un 0-0 | 2 partidos, 5 goles y promedio 2.50, por fecha y por edición"""
        self.assertEqual(reporte(self.c, "goles_fecha", torneo=2), [(1, 2, 5, 2.5)])
        self.assertEqual(reporte(self.c, "goles_global", torneo=2), [(2, 5, 2.5)])

    def test_empate_sin_goles_en_posiciones(self):
        """CP-REP-18 | Un 0-0 da un punto a cada equipo | C y D juegan sin goles | Ambos con un empate, 0 goles y 1 punto, entre el ganador y el perdedor de la fecha"""
        filas = reporte(self.c, "posiciones", torneo=2)
        self.assertEqual([fila[0] for fila in filas], ["A", "C", "D", "B"])
        self.assertEqual(filas[1:3], [("C", 1, 0, 1, 0, 0, 0, 0, 1), ("D", 1, 0, 1, 0, 0, 0, 0, 1)])

    def test_empate_sin_goles_en_valla(self):
        """CP-REP-19 | Un 0-0 cuenta como valla invicta | C y D juegan sin goles | Ambos con 1 partido, 0 goles recibidos, 1 valla invicta y promedio 0"""
        filas = {fila[0]: fila[1:] for fila in reporte(self.c, "valla", torneo=2)}
        self.assertEqual(filas["C"], (1, 0, 1, 0))
        self.assertEqual(filas["D"], (1, 0, 1, 0))


class Escenarios(CasoTransaccional):
    """Casos borde sobre ediciones de prueba y defectos del orden de los reportes."""

    def test_goleadores_como_maximo_diez(self):
        """CP-REP-20 | Goleadores muestra como máximo 10 jugadores | Doce jugadores con gol, uno de ellos con dos | Diez filas, encabezadas por el de dos goles"""
        edicion_prueba(self.c)
        alta_partido(self.c, 101, 1, 11, 12, ayer())
        alta_partido(self.c, 102, 1, 13, 14, ayer(), turno=2)
        for partido, equipo, cedulas in ((101, 11, FACULTAD[1]), (101, 12, FACULTAD[2]),
                                         (102, 13, FACULTAD[3][:1]), (102, 14, FACULTAD[4][:1])):
            firmar(self.c, partido, equipo, cedulas)
            for ci in cedulas:
                gol(self.c, partido, ci, 10)
        gol(self.c, 102, "44444441", 11)
        marcar(self.c, "jugado", 101, 102)
        filas = reporte(self.c, "goleadores", torneo=2)
        self.assertEqual(len(filas), 10)
        self.assertEqual(filas[0], ("44444441", "Mariana Medina", "D", 2))

    def test_partidos_no_jugados_no_cuentan(self):
        """CP-REP-21 | Partidos no jugados no cuentan en los reportes | Goles y tarjetas en partidos programado, postergado y cancelado | Posiciones, goleadores, fair play, promedios, canchas, turnos y valla en cero"""
        edicion_prueba(self.c)
        alta_partido(self.c, 101, 1, 11, 12, ayer())
        alta_partido(self.c, 102, 1, 13, 14, ayer(), turno=2)
        alta_partido(self.c, 103, 2, 11, 13, ayer(), turno=3)
        firmar(self.c, 101, 11, ["11111111"])
        firmar(self.c, 101, 12, ["22222221"])
        firmar(self.c, 102, 13, ["33333331"])
        firmar(self.c, 102, 14, ["44444441"])
        firmar(self.c, 103, 11, ["11111112"])
        firmar(self.c, 103, 13, ["33333332"])
        gol(self.c, 101, "11111111", 5)
        gol(self.c, 102, "33333331", 6)
        gol(self.c, 103, "11111112", 7)
        tarjeta(self.c, 101, "22222221", 8, "amarilla")
        tarjeta(self.c, 102, "44444441", 9, "roja")
        tarjeta(self.c, 103, "33333332", 10, "amarilla")
        marcar(self.c, "cancelado", 102)
        marcar(self.c, "postergado", 103)
        equipos = ["A", "B", "C", "D"]
        self.assertEqual(reporte(self.c, "posiciones", torneo=2), [(n, 0, 0, 0, 0, 0, 0, 0, 0) for n in equipos])
        self.assertEqual(reporte(self.c, "goleadores", torneo=2), [])
        self.assertEqual(reporte(self.c, "fairplay", torneo=2), [(n, 0, 0, 0) for n in equipos])
        self.assertEqual(reporte(self.c, "goles_fecha", torneo=2), [])
        self.assertEqual(reporte(self.c, "goles_global", torneo=2), [(0, 0, 0)])
        self.assertEqual(reporte(self.c, "canchas", torneo=2), CANCHAS_SIN_PARTIDOS)
        self.assertEqual(reporte(self.c, "turnos", torneo=2), TURNOS_SIN_PARTIDOS)
        self.assertEqual(sorted(reporte(self.c, "valla", torneo=2)), [(n, 0, 0, 0, 0) for n in equipos])
        self.assertEqual(reporte(self.c, "estados", torneo=2), [(3, 0, 1, 1, 1, 0, 66.67)])

    def test_edicion_con_equipos_y_sin_partidos(self):
        """CP-REP-22 | Edición con equipos y sin partidos | Cuatro equipos con plantel y ningún partido | Cada equipo en cero y los 20 jugadores figuran como inscriptos sin planilla"""
        edicion_prueba(self.c)
        equipos = ["A", "B", "C", "D"]
        self.assertEqual(reporte(self.c, "posiciones", torneo=2), [(n, 0, 0, 0, 0, 0, 0, 0, 0) for n in equipos])
        self.assertEqual(reporte(self.c, "fairplay", torneo=2), [(n, 0, 0, 0) for n in equipos])
        self.assertEqual(sorted(reporte(self.c, "valla", torneo=2)), [(n, 0, 0, 0, 0) for n in equipos])
        self.assertEqual(reporte(self.c, "goles_global", torneo=2), [(0, 0, 0)])
        self.assertEqual(reporte(self.c, "estados", torneo=2), [(0, 0, 0, 0, 0, 0, 0)])
        self.assertEqual(reporte(self.c, "asistencia", torneo=2), [])
        self.assertEqual(len(reporte(self.c, "sin_planilla", torneo=2)), 20)

    def test_edicion_vacia(self):
        """CP-REP-23 | Edición vacía no da error en ningún reporte | Edición sin equipos ni partidos | Los 14 reportes responden: promedios y porcentajes en 0 y listados de la edición sin filas"""
        alta_edicion_vacia(self.c)
        esperado = {slug: [] for slug in SIN_FILAS_EN_EDICION_VACIA}
        esperado.update({"goles_global": [(0, 0, 0)], "estados": [(0, 0, 0, 0, 0, 0, 0)],
                         "canchas": CANCHAS_SIN_PARTIDOS, "turnos": TURNOS_SIN_PARTIDOS, "facultades": FACULTADES})
        self.assertEqual({slug: reporte(self.c, slug, torneo=3, fecha=1) for slug in REPORTS}, esperado)

    def test_edicion_nueva_no_altera_la_primera(self):
        """CP-REP-24 | Una edición nueva no altera la primera | Partidos, goles, tarjetas y sanciones en la edición 2, con los mismos jugadores | Los 14 reportes de la edición 1 no cambian"""
        antes = {slug: sorted(reporte(self.c, slug)) for slug in REPORTS}
        edicion_prueba(self.c)
        alta_partido(self.c, 101, 1, 11, 12, ayer())
        alta_partido(self.c, 102, 2, 13, 14, ayer(), turno=4, cancha="Cancha B", complejo=2)
        firmar(self.c, 101, 11, ["11111111"])
        firmar(self.c, 101, 12, ["22222221"])
        firmar(self.c, 102, 13, ["33333331"])
        firmar(self.c, 102, 14, ["44444441"])
        gol(self.c, 101, "11111111", 5)
        gol(self.c, 101, "11111111", 6)
        gol(self.c, 102, "44444441", 7)
        tarjeta(self.c, 101, "22222221", 8, "amarilla")
        tarjeta(self.c, 102, "33333331", 9, "roja")
        q(self.c, "INSERT INTO sancion_jugador (ci_jugador,id_torneo,motivo,numero_fecha_inicio,cantidad_fechas) "
                  "VALUES ('44444441',2,'disciplinaria',2,1)")
        marcar(self.c, "jugado", 101, 102)
        self.assertEqual({slug: sorted(reporte(self.c, slug)) for slug in REPORTS}, antes)
        # Control: la edición 2 sí tiene datos y se ven en su propio reporte.
        self.assertEqual(reporte(self.c, "goleadores", torneo=2),
                         [("11111111", "Juan Perez", "A", 2), ("44444441", "Mariana Medina", "D", 1)])

    @defecto("REP-03", "A, con una roja, sale antes que B, con tres amarillas: con igual puntaje ordena por nombre.")
    def test_fairplay_desempata_por_rojas(self):
        """CP-REP-25 | Fair play: a igual puntaje, primero el de menos rojas | A con una roja y B con tres amarillas, 3 puntos cada uno | B queda antes que A"""
        edicion_prueba(self.c)
        alta_partido(self.c, 101, 1, 11, 12, ayer())
        firmar(self.c, 101, 11, ["11111111"])
        firmar(self.c, 101, 12, ["22222221", "22222222", "22222223"])
        tarjeta(self.c, 101, "11111111", 5, "roja")
        for minuto, ci in enumerate(("22222221", "22222222", "22222223"), start=6):
            tarjeta(self.c, 101, ci, minuto, "amarilla")
        marcar(self.c, "jugado", 101)
        self.assertEqual(reporte(self.c, "fairplay", torneo=2),
                         [("C", 0, 0, 0), ("D", 0, 0, 0), ("B", 3, 0, 3), ("A", 0, 1, 3)])

    @defecto("REP-02", "C y D, sin partidos, encabezan la valla con promedio 0.00, por encima de A y B, que jugaron.")
    def test_valla_equipo_sin_partidos_no_encabeza(self):
        """CP-REP-26 | Valla: equipo sin partidos no encabeza el premio | A y B empatan 1-1; C y D no jugaron | Los primeros del reporte son los equipos que jugaron"""
        edicion_prueba(self.c)
        alta_partido(self.c, 101, 1, 11, 12, ayer())
        firmar(self.c, 101, 11, ["11111111"])
        firmar(self.c, 101, 12, ["22222221"])
        gol(self.c, 101, "11111111", 5)
        gol(self.c, 101, "22222221", 6)
        marcar(self.c, "jugado", 101)
        partidos = [fila[1] for fila in reporte(self.c, "valla", torneo=2)]
        self.assertEqual(partidos, sorted(partidos, reverse=True))


class PantallasDeReportes(CasoWeb):
    """Las pantallas reales de la aplicación, con las cuentas reales."""

    def test_administrador_abre_los_reportes(self):
        """CP-REP-27 | Administrador abre los 14 reportes | Abrir cada pantalla con la edición 1 | Responde 200, con su título, sin avisos y con la cantidad de filas esperada"""
        cliente, _ = self.ingresar(WEB_ADMIN)
        for slug, (titulo, _descripcion, _sql) in REPORTS.items():
            respuesta = cliente.get(f"/reportes/{slug}?torneo=1&fecha=2")
            self.assertEqual(respuesta.status_code, 200, slug)
            self.assertIn(f"<h1>{titulo}</h1>", respuesta.text)
            self.assertEqual(avisos(respuesta.text), [], slug)
            self.assertIn(f"<p class=\"hint\">{FILAS_EDICION_1[slug]} fila(s) en el resultado.</p>", respuesta.text)

    def test_planillero_no_accede_a_los_reportes(self):
        """CP-REP-28 | Planillero no accede a los reportes | Abrir el índice y las 14 pantallas como planillero | Todas responden 403"""
        cliente, _ = self.ingresar(WEB_PLANILLERO)
        for ruta in ["/reportes"] + [f"/reportes/{slug}" for slug in REPORTS]:
            self.assertEqual(cliente.get(ruta).status_code, 403, ruta)

    def test_edicion_vacia_en_pantalla(self):
        """CP-REP-29 | Edición vacía se ve sin errores en pantalla | Abrir los 14 reportes de una edición sin equipos ni partidos | Responden 200, sin avisos, y los listados de la edición indican que no hay datos"""
        alta_edicion_vacia(self.c)
        cliente, _ = self.ingresar(WEB_ADMIN)
        for slug in REPORTS:
            respuesta = cliente.get(f"/reportes/{slug}?torneo=3&fecha=1")
            self.assertEqual(respuesta.status_code, 200, slug)
            self.assertEqual(avisos(respuesta.text), [], slug)
            self.assertEqual("No hay datos para este reporte." in respuesta.text,
                             slug in SIN_FILAS_EN_EDICION_VACIA, slug)

    def test_inhabilitados_respeta_la_fecha_indicada(self):
        """CP-REP-30 | Pantalla de inhabilitados respeta la fecha indicada | Fecha 3, fecha no numérica y fecha fuera de rango | 1 fila; 2 filas, porque usa la fecha 2; 0 filas; siempre sin avisos"""
        cliente, _ = self.ingresar(WEB_ADMIN)
        for fecha, filas in (("3", 1), ("abc", 2), ("9999", 0)):
            respuesta = cliente.get(f"/reportes/inhabilitados?torneo=1&fecha={fecha}")
            self.assertEqual(respuesta.status_code, 200, fecha)
            self.assertEqual(avisos(respuesta.text), [], fecha)
            self.assertIn(f"<p class=\"hint\">{filas} fila(s) en el resultado.</p>", respuesta.text)


class VallaEmpatada(CasoAislado):
    """Usa DDL, por eso reinstala la base en lugar de correr en una transacción."""

    @defecto("REP-02", "Salieron Zeta, Yota, Beta y Alfa: el reporte no ordena por nombre y el empate queda librado al plan de MySQL.")
    def test_valla_desempata_por_nombre(self):
        """CP-REP-31 | Valla: empate total se resuelve por nombre | Cuatro equipos con 0-0, sin el índice por nombre | Salen en orden alfabético: Alfa, Beta, Yota y Zeta"""
        edicion_prueba(self.c)
        for equipo, nombre in ((11, "Zeta"), (12, "Yota"), (13, "Beta"), (14, "Alfa")):
            q(self.c, "UPDATE equipo SET nombre=%s WHERE id_equipo=%s", (nombre, equipo))
        alta_partido(self.c, 101, 1, 11, 12, ayer())
        alta_partido(self.c, 102, 1, 13, 14, ayer(), turno=2)
        marcar(self.c, "jugado", 101, 102)
        # El índice único (id_torneo, nombre) puede dar orden alfabético por casualidad, según el plan que
        # elija MySQL. Sin él queda a la vista lo que garantiza la consulta por sí sola.
        q(self.c, "ALTER TABLE equipo ALTER INDEX uk_equipo_nombre_torneo INVISIBLE")
        self.assertEqual([fila[0] for fila in reporte(self.c, "valla", torneo=2)], ["Alfa", "Beta", "Yota", "Zeta"])
