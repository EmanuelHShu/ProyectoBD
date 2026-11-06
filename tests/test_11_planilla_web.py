"""Flujo del planillero en la pantalla de un partido, con la aplicación real y su cuenta real."""
from datetime import date, timedelta

from base import WEB_PLANILLERO, CasoWeb, alta_partido, avisos, defecto, edicion_prueba, firmar, q, valor

EVENTO_REGISTRADO = "Evento registrado correctamente."


def dias_atras(dias):
    return (date.today() - timedelta(days=dias)).isoformat()


class PlanillaWeb(CasoWeb):
    """Edición 2: partidos 101 (fecha 1) y 102 (fecha 2), ambos de ayer y sin marcar como jugados.

    En la planilla del 101 ya están Carlos Gomez, del local, y Lucia Suarez, del visitante.
    """

    def setUp(self):
        super().setUp()
        edicion_prueba(self.c)
        alta_partido(self.c, 101, 1, 11, 12, dias_atras(1))
        alta_partido(self.c, 102, 2, 11, 13, dias_atras(1), turno=2)
        firmar(self.c, 101, 11, ["11111112"])
        firmar(self.c, 101, 12, ["22222222"])
        self.cliente, _ = self.ingresar(WEB_PLANILLERO)

    def accion(self, ruta, **datos):
        """Envía un formulario como planillero y devuelve los avisos de la página a la que vuelve."""
        return avisos(self.enviar(self.cliente, ruta, datos).text)

    def resultado(self, partido=101):
        fila = q(self.c, "SELECT goles_local,goles_visitante FROM v_resultado_partido WHERE id_partido=%s", (partido,))[0]
        return fila["goles_local"], fila["goles_visitante"]

    def gol_cargado(self):
        """Carga un gol de Carlos Gomez en el partido 101 y devuelve su id."""
        q(self.c, "INSERT INTO gol (id_partido,ci_jugador,minuto,autogol) VALUES (101,'11111112',10,0)")
        return valor(self.c, "SELECT id_gol FROM gol WHERE id_partido=101")

    def expulsar_a_gomez(self):
        """Roja a Carlos Gomez en la fecha 1: queda suspendido para la fecha 2."""
        q(self.c, "INSERT INTO tarjeta (id_partido,ci_jugador,minuto,color) VALUES (101,'11111112',20,'roja')")

    def test_agregar_a_planilla(self):
        """CP-WEB-01 | Agregar un jugador a la planilla | Agregar a Mateo Silva al partido de ayer | Aviso de éxito y el jugador queda en la planilla de su equipo"""
        self.assertEqual(self.accion("/partidos/101/planilla", ci="11111113", equipo="11"),
                         ["Jugador añadido a la planilla."])
        self.assertEqual(valor(self.c, "SELECT id_equipo FROM planilla_partido "
                                       "WHERE id_partido=101 AND ci_jugador='11111113'"), 11)

    def test_cargar_gol(self):
        """CP-WEB-02 | Cargar un gol | Gol de Carlos Gomez, del local, al minuto 10 | Aviso de éxito y resultado 1-0"""
        self.assertEqual(self.accion("/partidos/101/gol", ci_jugador="11111112", minuto="10", autogol="0"),
                         [EVENTO_REGISTRADO])
        self.assertEqual(self.resultado(), (1, 0))

    def test_cargar_autogol(self):
        """CP-WEB-03 | Cargar un autogol | Autogol de Lucia Suarez, del visitante, al minuto 11 | Aviso de éxito, gol marcado como autogol y resultado 1-0 para el local"""
        self.assertEqual(self.accion("/partidos/101/gol", ci_jugador="22222222", minuto="11", autogol="1"),
                         [EVENTO_REGISTRADO])
        self.assertEqual(valor(self.c, "SELECT autogol FROM gol WHERE id_partido=101"), 1)
        self.assertEqual(self.resultado(), (1, 0))

    def test_tarjeta_roja_crea_sancion(self):
        """CP-WEB-04 | Tarjeta roja crea la sanción | Roja a Carlos Gomez en la fecha 1 | Aviso de éxito y sanción por roja de una fecha, desde la fecha 2"""
        self.assertEqual(self.accion("/partidos/101/tarjeta", ci_jugador="11111112", minuto="20", color="roja"),
                         [EVENTO_REGISTRADO])
        self.assertEqual(q(self.c, "SELECT motivo,numero_fecha_inicio,cantidad_fechas FROM sancion_jugador "
                                   "WHERE ci_jugador='11111112' AND id_torneo=2"),
                         [{"motivo": "roja", "numero_fecha_inicio": 2, "cantidad_fechas": 1}])

    def test_editar_gol(self):
        """CP-WEB-05 | Editar un gol | Cambiar un gol del local al minuto 15 y a autogol | Aviso de éxito, datos actualizados y resultado 0-1"""
        id_gol = self.gol_cargado()
        self.assertEqual(self.accion(f"/partidos/101/gol/{id_gol}/editar", ci_jugador="11111112", minuto="15", autogol="1"),
                         ["Evento actualizado."])
        self.assertEqual(q(self.c, "SELECT minuto,autogol FROM gol WHERE id_gol=%s", (id_gol,)),
                         [{"minuto": 15, "autogol": 1}])
        self.assertEqual(self.resultado(), (0, 1))

    def test_borrar_gol(self):
        """CP-WEB-06 | Borrar un gol | Eliminar el único gol del partido | Aviso de éxito y resultado 0-0"""
        id_gol = self.gol_cargado()
        self.assertEqual(self.accion(f"/partidos/101/gol/{id_gol}/borrar"), ["Evento eliminado."])
        self.assertEqual(valor(self.c, "SELECT COUNT(*) FROM gol WHERE id_partido=101"), 0)
        self.assertEqual(self.resultado(), (0, 0))

    def test_quitar_de_planilla(self):
        """CP-WEB-07 | Quitar un jugador de la planilla | Quitar a Carlos Gomez, que tiene un gol | Aviso de éxito; salen de la base el jugador de la planilla y su gol"""
        self.gol_cargado()
        self.assertEqual(self.accion("/partidos/101/planilla/11111112/borrar"), ["Jugador retirado de planilla."])
        self.assertEqual(valor(self.c, "SELECT COUNT(*) FROM planilla_partido "
                                       "WHERE id_partido=101 AND ci_jugador='11111112'"), 0)
        self.assertEqual(valor(self.c, "SELECT COUNT(*) FROM gol WHERE id_partido=101"), 0)

    def test_suspendido_marcado_en_pantalla(self):
        """CP-WEB-08 | Suspendido marcado en la pantalla del partido | Abrir el partido de la fecha 2 tras una roja en la fecha 1 | Carlos Gomez figura como suspendido y es el único"""
        self.expulsar_a_gomez()
        pagina = self.cliente.get("/partidos/102").text
        self.assertIn('Gomez, Carlos</td><td><span class="bad">Suspendido</span>', pagina)
        self.assertEqual(pagina.count('<span class="bad">Suspendido</span>'), 1)

    def test_suspendido_rechazado_en_planilla(self):
        """CP-WEB-09 | Suspendido no puede firmar la planilla | Agregar a Carlos Gomez al partido de la fecha 2 tras una roja | Rechazo: el jugador se encuentra suspendido; no queda en la planilla"""
        self.expulsar_a_gomez()
        self.assertEqual(self.accion("/partidos/102/planilla", ci="11111112", equipo="11"),
                         ["MySQL rechazó la operación: Error: El jugador se encuentra suspendido para esta fecha "
                          "y no puede firmar planilla."])
        self.assertEqual(valor(self.c, "SELECT COUNT(*) FROM planilla_partido WHERE id_partido=102"), 0)

    def test_marcar_jugado(self):
        """CP-WEB-10 | Marcar el partido como jugado | Partido de ayer con un gol del local | Aviso de éxito, estado jugado y pantalla con el resultado 1 : 0"""
        self.gol_cargado()
        pagina = self.enviar(self.cliente, "/partidos/101/finalizar").text
        self.assertEqual(avisos(pagina), ["Partido marcado como jugado. Resultado calculado a partir de los goles."])
        self.assertIn('<span class="score">1 : 0</span>', pagina)
        self.assertEqual(valor(self.c, "SELECT estado FROM partido WHERE id_partido=101"), "jugado")

    def test_marcar_jugado_dos_veces(self):
        """CP-WEB-11 | Un partido jugado no se marca otra vez | Marcar como jugado un partido que ya lo está | Rechazo: solo un partido programado puede marcarse como jugado"""
        q(self.c, "UPDATE partido SET estado='jugado' WHERE id_partido=101")
        self.assertEqual(self.accion("/partidos/101/finalizar"),
                         ["MySQL rechazó la operación: Error: Solo un partido programado puede marcarse como jugado."])

    def test_correccion_dentro_del_plazo(self):
        """CP-WEB-12 | Corrección dentro de las 48 horas | Cargar un gol del visitante en un partido jugado ayer | Aviso de éxito y resultado corregido a 0-1"""
        q(self.c, "UPDATE partido SET estado='jugado' WHERE id_partido=101")
        self.assertEqual(self.accion("/partidos/101/gol", ci_jugador="22222222", minuto="30", autogol="0"),
                         [EVENTO_REGISTRADO])
        self.assertEqual(self.resultado(), (0, 1))

    def test_partido_futuro_rechaza_cargas(self):
        """CP-WEB-13 | Partido futuro no admite planilla ni cierre | Partido de 2099: agregar a planilla, cargar gol y marcar jugado | Las tres acciones avisan que el turno no terminó y nada cambia"""
        alta_partido(self.c, 103, 3, 11, 14, "2099-12-20", turno=3)
        aviso = "La planilla de juego solo se registra una vez terminado el turno."
        self.assertIn(aviso, self.accion("/partidos/103/planilla", ci="11111113", equipo="11"))
        self.assertIn(aviso, self.accion("/partidos/103/gol", ci_jugador="11111113", minuto="5", autogol="0"))
        self.assertIn(aviso, self.accion("/partidos/103/finalizar"))
        self.assertEqual(valor(self.c, "SELECT COUNT(*) FROM planilla_partido WHERE id_partido=103"), 0)
        self.assertEqual(valor(self.c, "SELECT COUNT(*) FROM gol WHERE id_partido=103"), 0)
        self.assertEqual(valor(self.c, "SELECT estado FROM partido WHERE id_partido=103"), "programado")

    def test_partido_cerrado_rechaza_cargas(self):
        """CP-WEB-14 | Partido cerrado no admite correcciones | Partido 1, jugado en agosto: cargar gol, cargar tarjeta y quitar de planilla | Las tres acciones avisan que terminó la ventana de 48 horas y nada cambia"""
        aviso = "La ventana de 48 horas para correcciones terminó."
        self.assertIn(aviso, self.accion("/partidos/1/gol", ci_jugador="11111111", minuto="1", autogol="0"))
        self.assertIn(aviso, self.accion("/partidos/1/tarjeta", ci_jugador="11111111", minuto="1", color="amarilla"))
        self.assertIn(aviso, self.accion("/partidos/1/planilla/11111111/borrar"))
        self.assertEqual(valor(self.c, "SELECT COUNT(*) FROM gol WHERE id_partido=1"), 3)
        self.assertEqual(valor(self.c, "SELECT COUNT(*) FROM tarjeta WHERE id_partido=1"), 1)
        self.assertEqual(valor(self.c, "SELECT COUNT(*) FROM planilla_partido WHERE id_partido=1"), 6)

    def test_minuto_invalido(self):
        """CP-WEB-15 | Minuto inválido se rechaza | Gol con minuto no numérico, vacío, negativo y 500 | Aviso de error en cada caso y ningún gol registrado"""
        for minuto, aviso in (("abc", "Ingrese un minuto válido."), ("", "Ingrese un minuto válido."),
                              ("-1", "El minuto debe estar entre 0 y 120."),
                              ("500", "El minuto debe estar entre 0 y 120.")):
            self.assertEqual(self.accion("/partidos/101/gol", ci_jugador="11111112", minuto=minuto, autogol="0"), [aviso])
        self.assertEqual(valor(self.c, "SELECT COUNT(*) FROM gol WHERE id_partido=101"), 0)

    def test_tipo_de_evento_inexistente(self):
        """CP-WEB-16 | Tipo de evento inexistente da 404 | Enviar alta, edición y borrado con el tipo penal | Las tres rutas responden 404"""
        for ruta in ("/partidos/101/penal", "/partidos/101/penal/1/editar", "/partidos/101/penal/1/borrar"):
            self.assertEqual(self.enviar(self.cliente, ruta, seguir=False).status_code, 404, ruta)

    @defecto("APP-08", "Mostró «Jugador retirado de planilla.» aunque Mateo Silva no estaba en la planilla.")
    def test_quitar_a_quien_no_esta_no_informa_exito(self):
        """CP-WEB-17 | Quitar a quien no está no informa éxito | Quitar de la planilla a Mateo Silva, que no firmó | No aparece el aviso de éxito"""
        self.assertNotIn("Jugador retirado de planilla.", self.accion("/partidos/101/planilla/11111113/borrar"))

    @defecto("APP-08", "Mostró «Evento actualizado.» aunque el gol 99999 no existe.")
    def test_editar_evento_inexistente_no_informa_exito(self):
        """CP-WEB-18 | Editar un evento inexistente no informa éxito | Editar el gol 99999 del partido de ayer | No aparece el aviso de éxito"""
        self.assertNotIn("Evento actualizado.", self.accion("/partidos/101/gol/99999/editar", ci_jugador="11111112",
                                                            minuto="5", autogol="0"))

    @defecto("APP-08", "Mostró «Evento eliminado.» aunque el gol 99999 no existe.")
    def test_borrar_evento_inexistente_no_informa_exito(self):
        """CP-WEB-19 | Borrar un evento inexistente no informa éxito | Borrar el gol 99999 del partido de ayer | No aparece el aviso de éxito"""
        self.assertNotIn("Evento eliminado.", self.accion("/partidos/101/gol/99999/borrar"))

    @defecto("APP-12", "La pantalla del partido de 2099, aún sin jugar, avisa que puede haber vencido el plazo de 48 horas.")
    def test_partido_futuro_sin_aviso_de_48_horas(self):
        """CP-WEB-20 | Partido futuro sin aviso de 48 horas | Abrir un partido programado para 2099 | Ningún aviso menciona el plazo de 48 horas"""
        alta_partido(self.c, 103, 3, 11, 14, "2099-12-20", turno=3)
        self.assertNotIn("48 horas", " ".join(avisos(self.cliente.get("/partidos/103").text)))

    @defecto("REG-15", "Se aceptó: el partido quedó jugado 0-0, sin planilla y ya fuera del plazo de corrección.")
    def test_no_marca_jugado_sin_planilla_con_plazo_vencido(self):
        """CP-WEB-21 | Sin planilla y con plazo vencido no se marca jugado | Marcar como jugado un partido de hace 5 días sin planilla | Rechazo: el partido sigue programado"""
        alta_partido(self.c, 103, 3, 11, 14, dias_atras(5), turno=3)
        self.accion("/partidos/103/finalizar")
        self.assertEqual(valor(self.c, "SELECT estado FROM partido WHERE id_partido=103"), "programado")
