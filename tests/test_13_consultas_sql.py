"""Scripts/consultas.sql: cada consulta corre bajo ONLY_FULL_GROUP_BY y coincide con app/reports.py.

Las consultas del archivo están fijas en id_torneo = 1, por eso todo se prueba sobre esa edición.
"""
import re
import sys
from datetime import date, timedelta
from decimal import Decimal

from base import RAIZ, SCRIPTS, CasoTransaccional, defecto, firmar, q, valor

sys.path.insert(0, str(RAIZ / "app"))
from reports import REPORTS

# Las consultas del archivo, en el orden en que aparecen.
NOMBRES = ("fixture", "plantel", "disciplina", "posiciones", "goleadores", "fairplay", "goles_fecha", "goles_global",
           "canchas", "turnos", "facultades", "sin_planilla", "sanciones", "estados", "asistencia", "inhabilitados",
           "valla")


def sentencias():
    """Quita los comentarios del archivo, lo separa por ';' y se queda con los SELECT."""
    texto = re.sub(r"--[^\n]*", "", (SCRIPTS / "consultas.sql").read_text(encoding="utf-8"))
    return [sentencia.strip() for sentencia in texto.split(";") if sentencia.strip().upper().startswith("SELECT")]


CONSULTAS = dict(zip(NOMBRES, sentencias()))


def plano(dato):
    """Lleva los tipos de PyMySQL a literales comparables: DECIMAL a número y TIME a texto."""
    if isinstance(dato, Decimal):
        return float(dato)
    if isinstance(dato, timedelta):
        return str(dato)
    return dato


def columnas(filas, nombres):
    return [tuple(plano(fila[nombre]) for nombre in nombres) for fila in filas]


def consulta(c, nombre, *nombres_columnas):
    """Corre una consulta del archivo y devuelve esas columnas de cada fila."""
    return columnas(q(c, CONSULTAS[nombre]), nombres_columnas)


def reporte(c, slug, *nombres_columnas):
    """Corre el reporte de la app sobre la edición 1 y la fecha 2, las fijas en consultas.sql."""
    return columnas(q(c, REPORTS[slug][2], {"torneo": 1, "fecha": 2}), nombres_columnas)


def nombre_completo(filas):
    """consultas.sql trae nombre y apellido por separado; reports.py, en una sola columna."""
    return [(f"{nombre} {apellido}", *resto) for nombre, apellido, *resto in filas]


class ArchivoDeConsultas(CasoTransaccional):
    def test_cantidad_de_consultas(self):
        """CP-CON-01 | El archivo tiene 17 consultas | Quitar comentarios y separar por punto y coma | Quedan 17 sentencias SELECT"""
        self.assertEqual(len(sentencias()), len(NOMBRES))
        self.assertEqual(len(NOMBRES), 17)

    def test_modo_only_full_group_by(self):
        """CP-CON-02 | Las consultas corren bajo ONLY_FULL_GROUP_BY | Leer el modo SQL de la sesión | El modo incluye ONLY_FULL_GROUP_BY"""
        self.assertIn("ONLY_FULL_GROUP_BY", valor(self.c, "SELECT @@SESSION.sql_mode").split(","))


class ConsultasOperativas(CasoTransaccional):
    """Las tres consultas sin equivalente en reports.py, contra sus valores exactos."""

    def test_fixture(self):
        """CP-CON-03 | Fixture de una fecha | Ejecutar la consulta bajo ONLY_FULL_GROUP_BY | Sin error; los tres partidos de la fecha 1 con su resultado y cancha"""
        dia = date(2026, 8, 10)
        self.assertEqual(consulta(self.c, "fixture", "numero_fecha", "dia", "hora_inicio", "equipo_local", "goles_local",
                                  "goles_visitante", "equipo_visitante", "nombre_cancha", "estado"), [
            (1, dia, "18:00:00", "Ingenieria FC", "2", "1", "Administracion United", "Cancha 1", "jugado"),
            (1, dia, "19:00:00", "Derecho Athletic", "1", "0", "Medicina Juniors", "Cancha 1", "jugado"),
            (1, dia, "20:00:00", "Arquitectura City", "2", "0", "Psicologia Sporting", "Cancha 1", "jugado"),
        ])

    def test_plantel(self):
        """CP-CON-04 | Plantel de un equipo | Ejecutar la consulta bajo ONLY_FULL_GROUP_BY | Sin error; los seis jugadores de Ingenieria FC por número de camiseta"""
        self.assertEqual(consulta(self.c, "plantel", "numero_camiseta", "ci", "nombre", "apellido", "tipo_jugador",
                                  "facultad"), [
            (5, "11111112", "Carlos", "Gomez", "grado", "Ingenieria"),
            (7, "11111113", "Mateo", "Silva", "grado", "Ingenieria"),
            (8, "11111114", "Lucas", "Rodriguez", "grado", "Ingenieria"),
            (9, "11111115", "Martin", "Lopez", "grado", "Ingenieria"),
            (10, "11111111", "Juan", "Perez", "grado", "Ingenieria"),
            (11, "11111116", "Ana", "Fernandez", "docente", "Ingenieria"),
        ])

    def test_control_disciplinario(self):
        """CP-CON-05 | Control disciplinario del torneo | Ejecutar la consulta bajo ONLY_FULL_GROUP_BY | Sin error; las dos sanciones de Psicologia Sporting"""
        filas = consulta(self.c, "disciplina", "ci", "nombre", "apellido", "equipo", "motivo", "numero_fecha_inicio",
                         "cantidad_fechas")
        self.assertEqual(sorted(filas), [
            ("66666661", "Catalina", "Pintos", "Psicologia Sporting", "roja", 2, 1),
            ("66666662", "Emiliano", "Cardozo", "Psicologia Sporting", "disciplinaria", 2, 2),
        ])


class ConsultasContraReportes(CasoTransaccional):
    """Cada consulta con equivalente en reports.py da los mismos valores que su reporte."""

    def coinciden(self, de_consulta, de_reporte):
        """Compara los valores sin importar el orden: varias consultas no definen el orden de los empates."""
        self.assertTrue(de_consulta, "La consulta no devolvió filas")
        self.assertEqual(sorted(de_consulta), sorted(de_reporte))

    def test_posiciones(self):
        """CP-CON-06 | Tabla de posiciones igual a la de la app | Ejecutar la consulta bajo ONLY_FULL_GROUP_BY | Sin error; mismos equipos, valores y orden que el reporte"""
        filas = consulta(self.c, "posiciones", "equipo", "pj", "pg", "pe", "pp", "gf", "gc", "dg", "puntos")
        self.assertTrue(filas)
        self.assertEqual(filas, reporte(self.c, "posiciones", "equipo", "PJ", "PG", "PE", "PP", "GF", "GC", "DG", "puntos"))

    def test_goleadores(self):
        """CP-CON-07 | Goleadores igual a la app | Ejecutar la consulta bajo ONLY_FULL_GROUP_BY | Sin error; mismos jugadores, equipos y goles que el reporte"""
        self.coinciden(nombre_completo(consulta(self.c, "goleadores", "nombre", "apellido", "equipo", "total_goles")),
                       reporte(self.c, "goleadores", "jugador", "equipo", "goles"))

    def test_fairplay(self):
        """CP-CON-08 | Fair play igual a la app | Ejecutar la consulta bajo ONLY_FULL_GROUP_BY | Sin error; mismas amarillas, rojas y puntaje por equipo que el reporte"""
        self.coinciden(consulta(self.c, "fairplay", "equipo", "amarillas", "rojas", "puntaje"),
                       reporte(self.c, "fairplay", "equipo", "amarillas", "rojas", "puntaje"))

    def test_goles_por_fecha(self):
        """CP-CON-09 | Promedio de goles por fecha igual a la app | Ejecutar la consulta bajo ONLY_FULL_GROUP_BY | Sin error; mismos partidos, goles y promedio por fecha que el reporte"""
        self.coinciden(consulta(self.c, "goles_fecha", "numero_fecha", "total_partidos", "total_goles", "prom_goles_fecha"),
                       reporte(self.c, "goles_fecha", "fecha", "partidos", "goles", "promedio"))

    def test_goles_por_edicion(self):
        """CP-CON-10 | Promedio de goles por edición igual a la app | Ejecutar la consulta bajo ONLY_FULL_GROUP_BY | Sin error; mismos partidos, goles y promedio que el reporte"""
        self.coinciden(consulta(self.c, "goles_global", "total_partidos_edicion", "total_goles_edicion", "prom_goles_edicion"),
                       reporte(self.c, "goles_global", "partidos", "goles", "promedio"))

    def test_canchas(self):
        """CP-CON-11 | Canchas con partidos igual a la app | Ejecutar la consulta bajo ONLY_FULL_GROUP_BY | Sin error; las canchas usadas con los mismos partidos que el reporte"""
        usadas = [fila for fila in reporte(self.c, "canchas", "complejo", "cancha", "partidos") if fila[-1] > 0]
        self.coinciden(consulta(self.c, "canchas", "complejo", "nombre_cancha", "cant_partidos"), usadas)

    def test_turnos(self):
        """CP-CON-12 | Turnos con partidos igual a la app | Ejecutar la consulta bajo ONLY_FULL_GROUP_BY | Sin error; los turnos usados con los mismos partidos que el reporte"""
        usados = [fila for fila in reporte(self.c, "turnos", "inicio", "fin", "partidos") if fila[-1] > 0]
        self.coinciden(consulta(self.c, "turnos", "hora_inicio", "hora_fin", "cant_partidos"), usados)

    def test_facultades(self):
        """CP-CON-13 | Jugadores por facultad y tipo igual a la app | Ejecutar la consulta bajo ONLY_FULL_GROUP_BY | Sin error; mismas combinaciones y cantidades que el reporte"""
        self.coinciden(consulta(self.c, "facultades", "facultad", "tipo", "cantidad_jugadores"),
                       reporte(self.c, "facultades", "facultad", "tipo", "jugadores"))

    def test_sin_planilla(self):
        """CP-CON-14 | Inscriptos sin planilla igual a la app | Ejecutar la consulta bajo ONLY_FULL_GROUP_BY | Sin error; mismos jugadores que el reporte"""
        self.coinciden(nombre_completo(consulta(self.c, "sin_planilla", "nombre", "apellido", "equipo", "ci", "tipo")),
                       reporte(self.c, "sin_planilla", "jugador", "equipo", "ci", "tipo"))

    def test_sanciones(self):
        """CP-CON-15 | Sanciones por equipo y motivo igual a la app | Ejecutar la consulta bajo ONLY_FULL_GROUP_BY | Sin error; mismos motivos y cantidades que el reporte"""
        self.coinciden(consulta(self.c, "sanciones", "equipo", "motivo", "cant_sanciones"),
                       reporte(self.c, "sanciones", "equipo", "motivo", "cantidad"))

    def test_estados(self):
        """CP-CON-16 | Porcentajes por estado iguales a la app | Ejecutar la consulta bajo ONLY_FULL_GROUP_BY | Sin error; mismos totales y porcentajes que el reporte"""
        (total, jugados, postergados, cancelados, pct_jugados, pct_post_canc), = reporte(
            self.c, "estados", "total", "jugados", "postergados", "cancelados", "porcentaje_jugados", "porcentaje_post_canc")
        self.coinciden(consulta(self.c, "estados", "total_partidos", "jugados", "post_canc", "pct_jugados", "pct_post_canc"),
                       [(total, jugados, postergados + cancelados, pct_jugados, pct_post_canc)])

    def test_asistencia(self):
        """CP-CON-17 | Asistencia perfecta igual a la app | Ejecutar la consulta bajo ONLY_FULL_GROUP_BY | Sin error; mismos jugadores y equipos que el reporte"""
        self.coinciden(nombre_completo(consulta(self.c, "asistencia", "nombre", "apellido", "ci", "equipo")),
                       reporte(self.c, "asistencia", "jugador", "ci", "equipo"))

    def test_inhabilitados(self):
        """CP-CON-18 | Inhabilitados de la fecha 2 igual a la app | Ejecutar la consulta bajo ONLY_FULL_GROUP_BY | Sin error; mismos jugadores, motivos y fechas que el reporte"""
        self.coinciden(nombre_completo(consulta(self.c, "inhabilitados", "nombre", "apellido", "equipo", "motivo",
                                                "numero_fecha_inicio", "fecha_fin_sancion")),
                       reporte(self.c, "inhabilitados", "jugador", "equipo", "motivo", "desde", "hasta"))

    def test_valla(self):
        """CP-CON-19 | Valla menos vencida igual a la app | Ejecutar la consulta bajo ONLY_FULL_GROUP_BY | Sin error; mismos partidos, goles recibidos, vallas y promedio que el reporte"""
        self.coinciden(consulta(self.c, "valla", "equipo", "pj", "goles_recibidos", "vallas_invictas", "prom_gc"),
                       reporte(self.c, "valla", "equipo", "PJ", "GC", "vallas_invictas", "promedio_gc"))


class DefectosDeLasConsultas(CasoTransaccional):
    def gol_sin_jugar(self, partido, equipo, ci):
        """Reubica el partido en el pasado, en un turno libre, y le carga un gol sin marcarlo jugado."""
        ayer = (date.today() - timedelta(days=1)).isoformat()
        q(self.c, "UPDATE partido SET dia=%s,id_turno=5 WHERE id_partido=%s", (ayer, partido))
        firmar(self.c, partido, equipo, [ci])
        q(self.c, "INSERT INTO gol (id_partido,ci_jugador,minuto,autogol) VALUES (%s,%s,10,0)", (partido, ci))

    def goles(self, jugador):
        """Goles de un jugador según la consulta y según el reporte de la app."""
        de_consulta = nombre_completo(consulta(self.c, "goleadores", "nombre", "apellido", "total_goles"))
        return dict(de_consulta)[jugador], dict(reporte(self.c, "goleadores", "jugador", "goles"))[jugador]

    @defecto("REP-01", "Juan Perez figura con 4 goles: se sumó el del partido 10, que sigue programado.")
    def test_goleadores_ignora_partido_programado(self):
        """CP-CON-20 | Goleadores ignora los partidos programados | Gol de Juan Perez en el partido 10, sin marcarlo jugado | Sigue con 3 goles, igual que en la app"""
        self.gol_sin_jugar(10, 1, "11111111")
        self.assertEqual(self.goles("Juan Perez"), (3, 3))

    @defecto("REP-01", "Camila Sosa figura con 3 goles: se sumó el del partido 12, que quedó cancelado.")
    def test_goleadores_ignora_partido_cancelado(self):
        """CP-CON-21 | Goleadores ignora los partidos cancelados | Gol de Camila Sosa en el partido 12, que luego se cancela | Sigue con 2 goles, igual que en la app"""
        self.gol_sin_jugar(12, 3, "33333331")
        q(self.c, "UPDATE partido SET estado='cancelado' WHERE id_partido=12")
        self.assertEqual(self.goles("Camila Sosa"), (2, 2))

    @defecto("REP-04", "Solo aparecen Cancha 1 y Cancha A: Cancha 2 y Cancha B quedan ocultas por no tener partidos.")
    def test_canchas_lista_las_que_no_se_usaron(self):
        """CP-CON-22 | Canchas sin uso también se listan | Ejecutar la consulta sobre la edición 1 | Aparecen las 4 canchas, Cancha 2 y Cancha B con 0 partidos, como en la app"""
        self.assertEqual(sorted(consulta(self.c, "canchas", "complejo", "nombre_cancha", "cant_partidos")),
                         sorted(reporte(self.c, "canchas", "complejo", "cancha", "partidos")))

    @defecto("REP-04", "Solo aparecen los tres turnos con partidos: los de las 21:00 y las 22:00 quedan ocultos.")
    def test_turnos_lista_los_que_no_se_usaron(self):
        """CP-CON-23 | Turnos sin uso también se listan | Ejecutar la consulta sobre la edición 1 | Aparecen los 5 turnos, los de las 21:00 y las 22:00 con 0 partidos, como en la app"""
        self.assertEqual(sorted(consulta(self.c, "turnos", "hora_inicio", "hora_fin", "cant_partidos")),
                         sorted(reporte(self.c, "turnos", "inicio", "fin", "partidos")))

    @defecto("REP-02", "Ingenieria FC sale antes que Derecho Athletic y Medicina Juniors antes que Arquitectura City.")
    def test_valla_empatados_por_nombre(self):
        """CP-CON-24 | Valla: empatados en orden alfabético | Ejecutar la consulta sobre la edición 1, que tiene empates | Derecho Athletic antes que Ingenieria FC y Arquitectura City antes que Medicina Juniors"""
        self.assertEqual([equipo for equipo, in consulta(self.c, "valla", "equipo")], [
            "Derecho Athletic", "Ingenieria FC", "Administracion United", "Arquitectura City", "Medicina Juniors",
            "Psicologia Sporting"])
