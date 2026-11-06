"""Ventana de correccion de 48 horas posteriores al fin del turno de un partido jugado."""
from datetime import date, timedelta

from base import (WEB_ADMIN, WEB_PLANILLERO, CasoTransaccional, CasoWeb, alta_partido, avisos, defecto,
                  edicion_prueba, firmar, intentar, mover_reloj, q, valor)

GOLEADOR = "11111112"
AMONESTADO = "11111113"
SUPLENTE = "11111114"

# El turno 1 del partido 101 termina el 2026-11-01 a las 19:00.
DIA = "2026-11-01"
A_47H59 = "2026-11-03 18:59:00"
A_48H = "2026-11-03 19:00:00"
A_48H_Y_1S = "2026-11-03 19:00:01"
A_48H01 = "2026-11-03 19:01:00"
DOCE_DIAS_DESPUES = "2026-11-13 19:00:00"
DOS_MESES_DESPUES = "2027-01-05 12:00:00"

NUEVO_GOL = f"INSERT INTO gol (id_partido,ci_jugador,minuto,autogol) VALUES (101,'{AMONESTADO}',30,false)"
EDITAR_GOL = "UPDATE gol SET minuto=6 WHERE id_partido=101"
BORRAR_GOL = "DELETE FROM gol WHERE id_partido=101"
NUEVA_TARJETA = f"INSERT INTO tarjeta (id_partido,ci_jugador,minuto,color) VALUES (101,'{GOLEADOR}',60,'roja')"
EDITAR_TARJETA = "UPDATE tarjeta SET color='amarilla' WHERE id_partido=101"
BORRAR_TARJETA = "DELETE FROM tarjeta WHERE id_partido=101"
FIRMA = f"INSERT INTO planilla_partido (id_partido,ci_jugador,id_equipo) VALUES (101,'{SUPLENTE}',11)"
QUITAR = f"DELETE FROM planilla_partido WHERE id_partido=101 AND ci_jugador='{GOLEADOR}'"
EDITAR_FILA = f"UPDATE planilla_partido SET id_equipo=12 WHERE id_partido=101 AND ci_jugador='{GOLEADOR}'"
EDITAR_PARTIDO = "UPDATE partido SET nombre_cancha='Cancha 2' WHERE id_partido=101"
BORRAR_PARTIDO = "DELETE FROM partido WHERE id_partido=101"
MARCAR = "CALL sp_marcar_partido_jugado(101)"


def resultado(c, partido=101):
    fila = q(c, "SELECT goles_local,goles_visitante FROM v_resultado_partido WHERE id_partido=%s", (partido,))[0]
    return (fila["goles_local"], fila["goles_visitante"])


def cantidad_sanciones(c, ci):
    return valor(c, "SELECT COUNT(*) FROM sancion_jugador WHERE ci_jugador=%s AND id_torneo=2", (ci,))


class PartidoJugado(CasoTransaccional):
    """Partido 101, jugado, con un gol del local (1-0) y una roja que sanciona a AMONESTADO."""
    def setUp(self):
        super().setUp()
        edicion_prueba(self.c)
        alta_partido(self.c, 101, 1, 11, 12, DIA)
        firmar(self.c, 101, 11, [GOLEADOR, AMONESTADO])
        q(self.c, "INSERT INTO gol (id_partido,ci_jugador,minuto,autogol) VALUES (101,%s,5,false)", (GOLEADOR,))
        q(self.c, "INSERT INTO tarjeta (id_partido,ci_jugador,minuto,color) VALUES (101,%s,40,'roja')", (AMONESTADO,))
        mover_reloj(self.c, "2026-11-01 19:30:00")
        q(self.c, MARCAR)


class Goles(PartidoJugado):
    def test_agregar_dentro(self):
        """CP-VEN-01 | A las 47 h 59 min se agrega un gol | Insertar un gol 47 h 59 min después del fin del turno | Se acepta y el resultado pasa a 2-0"""
        mover_reloj(self.c, A_47H59)
        self.acepta(NUEVO_GOL)
        self.assertEqual(resultado(self.c), (2, 0))

    def test_agregar_fuera(self):
        """CP-VEN-02 | A las 48 h 01 min no se agrega un gol | Insertar un gol 48 h 01 min después del fin del turno | Rechazo por el plazo de 48 horas"""
        mover_reloj(self.c, A_48H01)
        self.rechaza(NUEVO_GOL, "48 horas")

    def test_editar_dentro(self):
        """CP-VEN-03 | A las 47 h 59 min se edita un gol | Cambiar el minuto del gol 47 h 59 min después | Se acepta y el minuto cambia"""
        mover_reloj(self.c, A_47H59)
        self.acepta(EDITAR_GOL)
        self.assertEqual(valor(self.c, "SELECT minuto FROM gol WHERE id_partido=101"), 6)

    def test_editar_fuera(self):
        """CP-VEN-04 | A las 48 h 01 min no se edita un gol | Cambiar el minuto del gol 48 h 01 min después | Rechazo por el plazo de 48 horas"""
        mover_reloj(self.c, A_48H01)
        self.rechaza(EDITAR_GOL, "48 horas")

    def test_borrar_dentro(self):
        """CP-VEN-05 | A las 47 h 59 min se borra un gol | Borrar el gol 47 h 59 min después | Se acepta y el resultado pasa a 0-0"""
        mover_reloj(self.c, A_47H59)
        self.acepta(BORRAR_GOL)
        self.assertEqual(resultado(self.c), (0, 0))

    def test_borrar_fuera(self):
        """CP-VEN-06 | A las 48 h 01 min no se borra un gol | Borrar el gol 48 h 01 min después | Rechazo por el plazo y el resultado sigue 1-0"""
        mover_reloj(self.c, A_48H01)
        self.rechaza(BORRAR_GOL, "48 horas")
        self.assertEqual(resultado(self.c), (1, 0))


class Tarjetas(PartidoJugado):
    def test_agregar_dentro(self):
        """CP-VEN-07 | A las 47 h 59 min se agrega una tarjeta | Insertar una roja 47 h 59 min después | Se acepta y se crea la sanción"""
        mover_reloj(self.c, A_47H59)
        self.acepta(NUEVA_TARJETA)
        self.assertEqual(cantidad_sanciones(self.c, GOLEADOR), 1)

    def test_agregar_fuera(self):
        """CP-VEN-08 | A las 48 h 01 min no se agrega una tarjeta | Insertar una roja 48 h 01 min después | Rechazo por el plazo de 48 horas"""
        mover_reloj(self.c, A_48H01)
        self.rechaza(NUEVA_TARJETA, "48 horas")

    def test_editar_dentro(self):
        """CP-VEN-09 | A las 47 h 59 min se edita una tarjeta | Pasar la roja a amarilla 47 h 59 min después | Se acepta y la sanción se retira"""
        mover_reloj(self.c, A_47H59)
        self.acepta(EDITAR_TARJETA)
        self.assertEqual(cantidad_sanciones(self.c, AMONESTADO), 0)

    def test_editar_fuera(self):
        """CP-VEN-10 | A las 48 h 01 min no se edita una tarjeta | Pasar la roja a amarilla 48 h 01 min después | Rechazo por el plazo y la sanción sigue"""
        mover_reloj(self.c, A_48H01)
        self.rechaza(EDITAR_TARJETA, "48 horas")
        self.assertEqual(cantidad_sanciones(self.c, AMONESTADO), 1)

    def test_borrar_dentro(self):
        """CP-VEN-11 | A las 47 h 59 min se borra una tarjeta | Borrar la roja 47 h 59 min después | Se acepta y la sanción se retira"""
        mover_reloj(self.c, A_47H59)
        self.acepta(BORRAR_TARJETA)
        self.assertEqual(cantidad_sanciones(self.c, AMONESTADO), 0)

    def test_borrar_fuera(self):
        """CP-VEN-12 | A las 48 h 01 min no se borra una tarjeta | Borrar la roja 48 h 01 min después | Rechazo por el plazo y la sanción sigue"""
        mover_reloj(self.c, A_48H01)
        self.rechaza(BORRAR_TARJETA, "48 horas")
        self.assertEqual(cantidad_sanciones(self.c, AMONESTADO), 1)


class Planilla(PartidoJugado):
    def test_firmar_dentro(self):
        """CP-VEN-13 | A las 47 h 59 min se agrega a la planilla | Firmar a un jugador 47 h 59 min después | Se acepta"""
        mover_reloj(self.c, A_47H59)
        self.acepta(FIRMA)

    def test_firmar_fuera(self):
        """CP-VEN-14 | A las 48 h 01 min no se agrega a la planilla | Firmar a un jugador 48 h 01 min después | Rechazo por el plazo de 48 horas"""
        mover_reloj(self.c, A_48H01)
        self.rechaza(FIRMA, "48 horas")

    def test_quitar_dentro(self):
        """CP-VEN-15 | A las 47 h 59 min se quita de la planilla | Quitar al goleador 47 h 59 min después | Se acepta y su gol se borra"""
        mover_reloj(self.c, A_47H59)
        self.acepta(QUITAR)
        self.assertEqual(resultado(self.c), (0, 0))

    def test_quitar_fuera(self):
        """CP-VEN-16 | A las 48 h 01 min no se quita de la planilla | Quitar al goleador 48 h 01 min después | Rechazo por el plazo y el resultado sigue 1-0"""
        mover_reloj(self.c, A_48H01)
        self.rechaza(QUITAR, "48 horas")
        self.assertEqual(resultado(self.c), (1, 0))

    def test_editar_dentro(self):
        """CP-VEN-17 | Dentro del plazo una fila de planilla no se edita | Cambiar el equipo de la fila 47 h 59 min después | Rechazo: hay que quitarla y cargarla de nuevo"""
        mover_reloj(self.c, A_47H59)
        self.rechaza(EDITAR_FILA, "eliminela")

    def test_editar_fuera(self):
        """CP-VEN-18 | Fuera del plazo una fila de planilla no se edita | Cambiar el equipo de la fila 48 h 01 min después | Rechazo de la modificación"""
        mover_reloj(self.c, A_48H01)
        self.rechaza(EDITAR_FILA, "eliminela")


class Partido(PartidoJugado):
    def alta_jugado(self):
        alta_partido(self.c, 102, 2, 13, 14, DIA, cancha="Cancha 2", estado="jugado")

    def test_editar_dentro(self):
        """CP-VEN-19 | A las 47 h 59 min se edita el partido | Cambiar la cancha 47 h 59 min después | Se acepta y la cancha cambia"""
        mover_reloj(self.c, A_47H59)
        self.acepta(EDITAR_PARTIDO)
        self.assertEqual(valor(self.c, "SELECT nombre_cancha FROM partido WHERE id_partido=101"), "Cancha 2")

    def test_editar_fuera(self):
        """CP-VEN-20 | A las 48 h 01 min no se edita el partido | Cambiar la cancha 48 h 01 min después | Rechazo por el plazo de 48 horas"""
        mover_reloj(self.c, A_48H01)
        self.rechaza(EDITAR_PARTIDO, "48 horas")

    def test_borrar_dentro(self):
        """CP-VEN-21 | Dentro del plazo un partido jugado no se borra | Borrar el partido 47 h 59 min después | Rechazo: un partido jugado no se elimina"""
        mover_reloj(self.c, A_47H59)
        self.rechaza(BORRAR_PARTIDO, "no puede ser eliminado")

    def test_borrar_fuera(self):
        """CP-VEN-22 | Fuera del plazo un partido jugado no se borra | Borrar el partido 48 h 01 min después | Rechazo: un partido jugado no se elimina"""
        mover_reloj(self.c, A_48H01)
        self.rechaza(BORRAR_PARTIDO, "no puede ser eliminado")

    def test_alta_como_jugado_dentro(self):
        """CP-VEN-23 | Un alta como jugado respeta el plazo abierto | Insertar un partido jugado 47 h 59 min después de su turno y firmar | La firma se acepta"""
        mover_reloj(self.c, A_47H59)
        self.alta_jugado()
        self.acepta("INSERT INTO planilla_partido (id_partido,ci_jugador,id_equipo) VALUES (102,'33333332',13)")

    def test_alta_como_jugado_fuera(self):
        """CP-VEN-24 | Un alta como jugado respeta el plazo vencido | Insertar un partido jugado 48 h 01 min después de su turno y firmar | Rechazo por el plazo de 48 horas"""
        mover_reloj(self.c, A_48H01)
        self.alta_jugado()
        self.rechaza("INSERT INTO planilla_partido (id_partido,ci_jugador,id_equipo) VALUES (102,'33333332',13)", "48 horas")


class LimiteDelPlazo(PartidoJugado):
    def partido_del_ultimo_turno(self):
        """Partido 102, jugado, del turno de 22 a 23."""
        alta_partido(self.c, 102, 2, 13, 14, DIA, turno=5, cancha="Cancha 2")
        firmar(self.c, 102, 13, ["33333332"])
        q(self.c, "INSERT INTO gol (id_partido,ci_jugador,minuto,autogol) VALUES (102,'33333332',5,false)")
        mover_reloj(self.c, "2026-11-01 23:30:00")
        q(self.c, "CALL sp_marcar_partido_jugado(102)")

    def test_justo_a_las_48_horas(self):
        """CP-VEN-25 | Justo a las 48 h todavía se corrige | Editar un gol a las 48 h 00 min 00 s | Se acepta"""
        mover_reloj(self.c, A_48H)
        self.acepta(EDITAR_GOL)

    def test_un_segundo_despues(self):
        """CP-VEN-26 | Un segundo después de las 48 h ya no se corrige | Editar un gol a las 48 h 00 min 01 s | Rechazo por el plazo de 48 horas"""
        mover_reloj(self.c, A_48H_Y_1S)
        self.rechaza(EDITAR_GOL, "48 horas")

    def test_cuenta_desde_el_fin_del_turno(self):
        """CP-VEN-27 | El plazo corre desde el fin del turno | Turno de 22 a 23: editar un gol 48 h 59 min después del inicio | Se acepta porque falta 1 min para vencer"""
        self.partido_del_ultimo_turno()
        mover_reloj(self.c, "2026-11-03 22:59:00")
        self.acepta("UPDATE gol SET minuto=6 WHERE id_partido=102")

    def test_vence_segun_el_turno_del_partido(self):
        """CP-VEN-28 | El vencimiento depende del turno del partido | Turno de 22 a 23: editar un gol 48 h 01 min después de las 23 | Rechazo por el plazo de 48 horas"""
        self.partido_del_ultimo_turno()
        mover_reloj(self.c, "2026-11-03 23:01:00")
        self.rechaza("UPDATE gol SET minuto=6 WHERE id_partido=102", "48 horas")


class MoverEntrePartidos(PartidoJugado):
    """Partido 101 vencido y partido 102 abierto, con un gol y una amarilla de GOLEADOR en cada uno."""
    def setUp(self):
        super().setUp()
        alta_partido(self.c, 102, 2, 11, 13, "2026-11-08")
        firmar(self.c, 102, 11, [GOLEADOR])
        q(self.c, "INSERT INTO gol (id_partido,ci_jugador,minuto,autogol) VALUES (102,%s,7,false)", (GOLEADOR,))
        for partido in (101, 102):
            q(self.c, "INSERT INTO tarjeta (id_partido,ci_jugador,minuto,color) VALUES (%s,%s,50,'amarilla')",
              (partido, GOLEADOR))
        mover_reloj(self.c, A_48H01)

    def test_sacar_un_gol_de_un_partido_cerrado(self):
        """CP-VEN-29 | Un gol no sale de un partido cerrado | Pasar a un partido abierto un gol del partido vencido | Rechazo por el plazo de 48 horas"""
        self.rechaza("UPDATE gol SET id_partido=102 WHERE id_partido=101", "48 horas")

    def test_mover_un_gol_a_un_partido_cerrado(self):
        """CP-VEN-30 | Un gol no entra a un partido cerrado | Pasar al partido vencido un gol de un partido abierto | Rechazo por el plazo de 48 horas"""
        self.rechaza("UPDATE gol SET id_partido=101 WHERE id_partido=102", "48 horas")

    def test_sacar_una_tarjeta_de_un_partido_cerrado(self):
        """CP-VEN-31 | Una tarjeta no sale de un partido cerrado | Pasar a un partido abierto una tarjeta del partido vencido | Rechazo por el plazo de 48 horas"""
        self.rechaza("UPDATE tarjeta SET id_partido=102 WHERE id_partido=101 AND ci_jugador=%s", "48 horas", (GOLEADOR,))

    def test_mover_una_tarjeta_a_un_partido_cerrado(self):
        """CP-VEN-32 | Una tarjeta no entra a un partido cerrado | Pasar al partido vencido una tarjeta de un partido abierto | Rechazo por el plazo de 48 horas"""
        self.rechaza("UPDATE tarjeta SET id_partido=101 WHERE id_partido=102", "48 horas")


class PartidoSinMarcar(CasoTransaccional):
    """Partido 101 aun programado, con planilla y un gol cargados."""
    def setUp(self):
        super().setUp()
        edicion_prueba(self.c)
        alta_partido(self.c, 101, 1, 11, 12, DIA)
        firmar(self.c, 101, 11, [GOLEADOR])
        q(self.c, "INSERT INTO gol (id_partido,ci_jugador,minuto,autogol) VALUES (101,%s,5,false)", (GOLEADOR,))

    def test_un_partido_programado_no_vence(self):
        """CP-VEN-33 | Un partido programado no vence | Doce días después del turno, con el partido sin marcar, corregir un gol | Se acepta"""
        mover_reloj(self.c, DOCE_DIAS_DESPUES)
        self.acepta(EDITAR_GOL)

    def test_marcar_jugado_vencido_cierra_al_instante(self):
        """CP-VEN-34 | Marcar jugado después de vencido cierra al instante | Doce días después del turno, marcar jugado y corregir un gol | La marca se acepta y la corrección se rechaza"""
        mover_reloj(self.c, DOCE_DIAS_DESPUES)
        self.acepta(MARCAR)
        self.rechaza(EDITAR_GOL, "48 horas")

    def test_no_se_marca_antes_del_fin_del_turno(self):
        """CP-VEN-35 | No se marca jugado antes del fin del turno | Marcar jugado un segundo antes de las 19:00 | Rechazo: el turno todavía no pasó"""
        mover_reloj(self.c, "2026-11-01 18:59:59")
        self.rechaza(MARCAR, "ya pasaron")

    def test_se_marca_justo_al_fin_del_turno(self):
        """CP-VEN-36 | Se marca jugado justo al fin del turno | Marcar jugado exactamente a las 19:00 | Se acepta"""
        mover_reloj(self.c, "2026-11-01 19:00:00")
        self.acepta(MARCAR)

    def test_los_partidos_historicos_estan_cerrados(self):
        """CP-VEN-37 | Los partidos históricos de los datos están cerrados | Insertar un gol en el partido 1, jugado en agosto | Rechazo por el plazo de 48 horas"""
        self.rechaza("INSERT INTO gol (id_partido,ci_jugador,minuto,autogol) VALUES (1,'11111113',80,false)", "48 horas")


class DefectosConocidos(PartidoJugado):
    @defecto("REG-01", "Se aceptó toda la cadena: el gol se borró dos meses después y el partido volvió a jugado 0-0.")
    def test_cadena_reabrir_y_corregir_meses_despues(self):
        """CP-VEN-38 | Reabrir dentro del plazo y corregir meses después | Pasar a programado a las 47 h 59 min, borrar el gol dos meses después y volver a jugado | El resultado sigue 1-0 con el partido jugado"""
        mover_reloj(self.c, A_47H59)
        intentar(self.c, "UPDATE partido SET estado='programado' WHERE id_partido=101")
        mover_reloj(self.c, DOS_MESES_DESPUES)
        intentar(self.c, BORRAR_GOL)
        intentar(self.c, "UPDATE partido SET estado='jugado' WHERE id_partido=101")
        self.assertEqual(resultado(self.c), (1, 0))
        self.assertEqual(valor(self.c, "SELECT estado FROM partido WHERE id_partido=101"), "jugado")

    @defecto("REG-01", "Se aceptó: el partido reabierto admitió un gol nuevo dos meses después.")
    def test_reabierto_no_admite_gol_fuera_de_plazo(self):
        """CP-VEN-39 | Un partido reabierto conserva el plazo original | Pasar a programado a las 47 h 59 min e insertar un gol dos meses después | Rechazo por el plazo de 48 horas"""
        mover_reloj(self.c, A_47H59)
        intentar(self.c, "UPDATE partido SET estado='programado' WHERE id_partido=101")
        mover_reloj(self.c, DOS_MESES_DESPUES)
        self.rechaza(NUEVO_GOL, "48 horas")

    @defecto("REG-01", "Se aceptó: el partido pasado a postergado admitió un gol nuevo dos meses después.")
    def test_postergado_no_admite_gol_fuera_de_plazo(self):
        """CP-VEN-40 | Pasar a postergado tampoco reabre el partido | Pasar a postergado a las 47 h 59 min e insertar un gol dos meses después | Rechazo por el plazo de 48 horas"""
        mover_reloj(self.c, A_47H59)
        intentar(self.c, "UPDATE partido SET estado='postergado' WHERE id_partido=101")
        mover_reloj(self.c, DOS_MESES_DESPUES)
        self.rechaza(NUEVO_GOL, "48 horas")

    @defecto("REG-02", "Se aceptó: con el día movido a 2030 el partido jugado admitió un gol fuera de plazo.")
    def test_mover_el_dia_no_extiende_el_plazo(self):
        """CP-VEN-41 | Mover el día no extiende el plazo | Pasar el día del partido a 2030 a las 47 h 59 min e insertar un gol dos meses después | Rechazo por el plazo de 48 horas"""
        mover_reloj(self.c, A_47H59)
        intentar(self.c, "UPDATE partido SET dia='2030-01-01' WHERE id_partido=101")
        mover_reloj(self.c, DOS_MESES_DESPUES)
        self.rechaza(NUEVO_GOL, "48 horas")

    @defecto("REG-02", "Se aceptó: con el turno movido a las 23 el partido admitió un gol a las 48 h 01 min.")
    def test_mover_el_turno_no_extiende_el_plazo(self):
        """CP-VEN-42 | Mover el turno no extiende el plazo | Pasar al turno de 22 a 23 a las 47 h 59 min e insertar un gol a las 48 h 01 min | Rechazo por el plazo de 48 horas"""
        mover_reloj(self.c, A_47H59)
        intentar(self.c, "UPDATE partido SET id_turno=5 WHERE id_partido=101")
        mover_reloj(self.c, A_48H01)
        self.rechaza(NUEVO_GOL, "48 horas")

    @defecto("REG-03", "Se aceptó: el partido jugado pasó a cancelado y se eliminó con su planilla y su gol.")
    def test_no_se_elimina_pasando_por_cancelado(self):
        """CP-VEN-43 | Un jugado no se elimina pasándolo a cancelado | Dentro del plazo, pasar a cancelado y borrar el partido | El partido sigue existiendo con su gol"""
        mover_reloj(self.c, A_47H59)
        intentar(self.c, "UPDATE partido SET estado='cancelado' WHERE id_partido=101")
        intentar(self.c, BORRAR_PARTIDO)
        self.assertEqual(valor(self.c, "SELECT COUNT(*) FROM partido WHERE id_partido=101"), 1)
        self.assertEqual(valor(self.c, "SELECT COUNT(*) FROM gol WHERE id_partido=101"), 1)

    @defecto("REG-03", "Se aceptó: el partido jugado pasó a programado y se eliminó con su planilla y su gol.")
    def test_no_se_elimina_pasando_por_programado(self):
        """CP-VEN-44 | Un jugado no se elimina pasándolo a programado | Dentro del plazo, pasar a programado y borrar el partido | El partido sigue existiendo con su gol"""
        mover_reloj(self.c, A_47H59)
        intentar(self.c, "UPDATE partido SET estado='programado' WHERE id_partido=101")
        intentar(self.c, BORRAR_PARTIDO)
        self.assertEqual(valor(self.c, "SELECT COUNT(*) FROM partido WHERE id_partido=101"), 1)
        self.assertEqual(valor(self.c, "SELECT COUNT(*) FROM gol WHERE id_partido=101"), 1)


class VentanaEnLaApp(CasoWeb):
    def partido_con_gol(self, dias_atras):
        dia = (date.today() - timedelta(days=dias_atras)).isoformat()
        edicion_prueba(self.c)
        alta_partido(self.c, 101, 1, 11, 12, dia)
        firmar(self.c, 101, 11, [GOLEADOR])
        q(self.c, "INSERT INTO gol (id_partido,ci_jugador,minuto,autogol) VALUES (101,%s,5,false)", (GOLEADOR,))

    def cargar_gol(self, cliente):
        return self.enviar(cliente, "/partidos/101/gol", {"ci_jugador": GOLEADOR, "minuto": "30", "autogol": "0"},
                           desde="/partidos/101")

    def test_corregir_dentro_del_plazo(self):
        """CP-VEN-45 | La app corrige un partido jugado ayer | El planillero carga un gol en un partido jugado ayer | Evento registrado y dos goles en el partido"""
        self.partido_con_gol(1)
        q(self.c, MARCAR)
        cliente, _ = self.ingresar(WEB_PLANILLERO)
        self.assertIn("Evento registrado correctamente.", avisos(self.cargar_gol(cliente).text))
        self.assertEqual(valor(self.c, "SELECT COUNT(*) FROM gol WHERE id_partido=101"), 2)

    def test_corregir_fuera_del_plazo(self):
        """CP-VEN-46 | La app no corrige un partido vencido | El planillero carga un gol en un partido jugado hace 5 días | Aviso de plazo terminado y un solo gol en el partido"""
        self.partido_con_gol(5)
        q(self.c, MARCAR)
        cliente, _ = self.ingresar(WEB_PLANILLERO)
        self.assertIn("La ventana de 48 horas para correcciones terminó.", avisos(self.cargar_gol(cliente).text))
        self.assertEqual(valor(self.c, "SELECT COUNT(*) FROM gol WHERE id_partido=101"), 1)

    def test_marcar_vencido_cierra_al_instante(self):
        """CP-VEN-47 | En la app, marcar jugado vencido cierra al instante | Marcar jugado un partido de hace 5 días y cargar un gol | La marca se acepta y el gol se rechaza por el plazo"""
        self.partido_con_gol(5)
        cliente, _ = self.ingresar(WEB_PLANILLERO)
        self.enviar(cliente, "/partidos/101/finalizar", desde="/partidos/101")
        self.assertEqual(valor(self.c, "SELECT estado FROM partido WHERE id_partido=101"), "jugado")
        self.assertIn("La ventana de 48 horas para correcciones terminó.", avisos(self.cargar_gol(cliente).text))

    @defecto("REG-03", "Se aceptó: el administrador pasó el partido jugado a cancelado y lo eliminó.")
    def test_la_app_no_elimina_un_jugado_pasandolo_a_cancelado(self):
        """CP-VEN-48 | La app no elimina un jugado pasándolo a cancelado | El administrador lo edita a cancelado y luego lo elimina | El partido sigue existiendo"""
        self.partido_con_gol(1)
        q(self.c, MARCAR)
        cliente, _ = self.ingresar(WEB_ADMIN)
        self.guardar_edicion(cliente, "/catalogo/partido/101/editar", estado="cancelado")
        self.enviar(cliente, "/catalogo/partido/101/eliminar", desde="/catalogo/partido")
        self.assertEqual(valor(self.c, "SELECT COUNT(*) FROM partido WHERE id_partido=101"), 1)
