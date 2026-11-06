"""Partidos: equipos, cancha, cruces, fechas, estados, borrado y turnos."""
from base import (FACULTAD, CasoTransaccional, alta_partido, defecto, edicion_prueba, firmar, intentar,
                  mover_reloj, q, valor)

INSERTAR = ("INSERT INTO partido (id_torneo,numero_fecha,id_equipo_local,id_equipo_visitante,dia,id_turno,"
            "nombre_cancha,id_complejo,estado) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)")
TURNO = "INSERT INTO turno (hora_inicio,hora_fin) VALUES (%s,%s)"
MARCAR = "UPDATE partido SET estado='jugado' WHERE id_partido=101"
CANCELAR = "UPDATE partido SET estado='cancelado' WHERE id_partido=101"
PROCEDIMIENTO = "CALL sp_marcar_partido_jugado(101)"

# Días dentro de la edición 2. Lo que depende del momento usa mover_reloj, nunca la fecha real.
DIA = "2026-12-07"
OTRO_DIA = "2026-12-14"
ANTES = "2026-12-01 12:00:00"
FIN_TURNO = "2026-12-07 19:00:00"   # Fin del turno 1 de DIA.
DESPUES = "2026-12-08 12:00:00"     # Turno terminado, dentro de las 48 horas.
VENCIDO = "2026-12-12 12:00:00"     # Pasaron más de 48 horas desde el fin del turno.


def partido(fecha, local, visitante, dia=DIA, turno=1, cancha="Cancha 1", complejo=1, estado="programado", torneo=2):
    """Argumentos de INSERTAR, con los mismos valores por defecto que alta_partido."""
    return (torneo, fecha, local, visitante, dia, turno, cancha, complejo, estado)


def firmar_planteles(c):
    firmar(c, 101, 11, FACULTAD[1])
    firmar(c, 101, 12, FACULTAD[2])


class Partidos(CasoTransaccional):
    """Edición 2 en curso, con los equipos 11 a 14 y planteles de 5 jugadores."""
    def setUp(self):
        super().setUp()
        edicion_prueba(self.c)

    def partido_con_gol(self, equipo, ci):
        alta_partido(self.c, 101, 1, 11, 12, DIA)
        mover_reloj(self.c, DESPUES)
        firmar(self.c, 101, equipo, [ci])
        q(self.c, "INSERT INTO gol (id_partido,ci_jugador,minuto,autogol) VALUES (101,%s,10,0)", (ci,))

    def horario_del_partido_10(self):
        """Día, turno, cancha y complejo que ocupa el partido 10 de la edición 1."""
        return tuple(q(self.c, "SELECT dia,id_turno,nombre_cancha,id_complejo FROM partido WHERE id_partido=10")[0].values())

    # ---------------------------------------------------------------- equipos
    def test_alta_valida(self):
        """CP-PAR-01 | Alta de un partido válido | Equipos 11 y 12 de la edición en curso, con cancha libre | Se acepta y queda programado"""
        self.acepta(INSERTAR, partido(1, 11, 12))
        self.assertEqual(valor(self.c, "SELECT estado FROM partido WHERE id_torneo=2"), "programado")

    def test_equipo_contra_si_mismo(self):
        """CP-PAR-02 | Equipo contra sí mismo | Alta con el equipo 11 como local y visitante | Rechazo: un equipo no se enfrenta a sí mismo"""
        self.rechaza(INSERTAR, "si mismo", partido(1, 11, 11))

    def test_equipo_contra_si_mismo_por_update(self):
        """CP-PAR-03 | Equipo contra sí mismo por edición | UPDATE del visitante con el mismo equipo local | Rechazo por la restricción CHECK"""
        alta_partido(self.c, 101, 1, 11, 12, DIA)
        self.rechaza("UPDATE partido SET id_equipo_visitante=11 WHERE id_partido=101", "chk_partido_equipos")

    def test_equipos_de_ediciones_distintas(self):
        """CP-PAR-04 | Equipos de ediciones distintas | Alta en la edición 2 con un visitante de la edición 1 | Rechazo: el visitante no tiene plantel en la edición"""
        self.rechaza(INSERTAR, "visitante debe tener", partido(1, 11, 1))

    def test_cambiar_a_equipo_de_otra_edicion(self):
        """CP-PAR-05 | Cambiar a un equipo de otra edición | UPDATE del visitante con un equipo de la edición 1 | Rechazo por la clave foránea compuesta"""
        alta_partido(self.c, 101, 1, 11, 12, DIA)
        self.rechaza("UPDATE partido SET id_equipo_visitante=1 WHERE id_partido=101", "fk_partido_visitante")

    def test_cambiar_equipos_sin_planilla(self):
        """CP-PAR-06 | Cambiar un equipo de un partido sin planilla | UPDATE del local de un partido sin firmas | Se acepta el cambio"""
        alta_partido(self.c, 101, 1, 11, 12, DIA)
        self.acepta("UPDATE partido SET id_equipo_local=13 WHERE id_partido=101")

    @defecto("REG-11", "Se aceptó: el gol quedó fuera del resultado, que pasó de 1-0 a 0-0.")
    def test_cambiar_local_con_planilla(self):
        """CP-PAR-07 | Cambiar el local de un partido con planilla | Partido con gol del local; UPDATE del local por el equipo 13 | Rechazo: el partido ya tiene planilla y goles"""
        self.partido_con_gol(11, "11111111")
        self.rechaza("UPDATE partido SET id_equipo_local=13 WHERE id_partido=101")

    @defecto("REG-11", "Se aceptó: el gol quedó fuera del resultado, que pasó de 0-1 a 0-0.")
    def test_cambiar_visitante_con_planilla(self):
        """CP-PAR-08 | Cambiar el visitante de un partido con planilla | Partido con gol del visitante; UPDATE del visitante por el equipo 13 | Rechazo: el partido ya tiene planilla y goles"""
        self.partido_con_gol(12, "22222221")
        self.rechaza("UPDATE partido SET id_equipo_visitante=13 WHERE id_partido=101")

    # ---------------------------------------------------------------- cancha, día y turno
    def test_cancha_ocupada(self):
        """CP-PAR-09 | Cancha ocupada en el mismo día y turno | Alta de otro partido en la misma cancha, día y turno | Rechazo: la cancha ya tiene partido"""
        alta_partido(self.c, 101, 1, 11, 12, DIA)
        self.rechaza(INSERTAR, "cancha ya tiene", partido(2, 13, 14))

    def test_mover_a_cancha_ocupada(self):
        """CP-PAR-10 | Mover un partido a una cancha ocupada | UPDATE del turno al de otro partido en la misma cancha | Rechazo: la cancha ya tiene partido"""
        alta_partido(self.c, 101, 1, 11, 12, DIA)
        alta_partido(self.c, 102, 2, 13, 14, DIA, turno=2)
        self.rechaza("UPDATE partido SET id_turno=1 WHERE id_partido=102", "cancha ya tiene")

    def test_misma_cancha_otro_turno(self):
        """CP-PAR-11 | Misma cancha y día en otro turno | Alta de otro partido en el turno siguiente | Se acepta"""
        alta_partido(self.c, 101, 1, 11, 12, DIA)
        self.acepta(INSERTAR, partido(1, 13, 14, turno=2))

    def test_otra_cancha_mismo_turno(self):
        """CP-PAR-12 | Mismo día y turno en otra cancha | Alta de otros dos equipos en Cancha 2 | Se acepta"""
        alta_partido(self.c, 101, 1, 11, 12, DIA)
        self.acepta(INSERTAR, partido(1, 13, 14, cancha="Cancha 2"))

    def test_cancelado_libera_la_cancha(self):
        """CP-PAR-13 | Un partido cancelado libera la cancha | Cancelar un partido y programar otro en su lugar | Se acepta"""
        alta_partido(self.c, 101, 1, 11, 12, DIA)
        q(self.c, CANCELAR)
        self.acepta(INSERTAR, partido(1, 13, 14))

    @defecto("REG-12", "Se aceptó: el equipo 11 quedó en dos canchas el mismo día y turno.")
    def test_equipo_en_dos_canchas(self):
        """CP-PAR-14 | Equipo en dos canchas a la vez | Alta de otro partido del equipo 11 el mismo día y turno en Cancha A | Rechazo: el equipo ya juega en ese horario"""
        alta_partido(self.c, 101, 1, 11, 12, DIA)
        self.rechaza(INSERTAR, None, partido(2, 11, 13, cancha="Cancha A", complejo=2))

    @defecto("REG-12", "Se aceptó: el equipo 11 quedó en dos canchas el mismo día y turno.")
    def test_mover_equipo_a_dos_canchas(self):
        """CP-PAR-15 | Mover un partido deja al equipo en dos canchas | UPDATE del día de un partido del equipo 11 al de otro suyo, en otra cancha | Rechazo: el equipo ya juega en ese horario"""
        alta_partido(self.c, 101, 1, 11, 12, DIA)
        alta_partido(self.c, 102, 2, 11, 13, OTRO_DIA, cancha="Cancha A", complejo=2)
        self.rechaza("UPDATE partido SET dia=%s WHERE id_partido=102", None, (DIA,))

    @defecto("REG-12", "Se aceptó: Cancha 1 quedó con dos partidos solapados de 18:30 a 19:00.")
    def test_turnos_solapados(self):
        """CP-PAR-16 | Turnos solapados en una misma cancha | Partido de 18:00 a 19:00; alta de otro de 18:30 a 19:30 en la misma cancha | Rechazo: la cancha está ocupada en ese horario"""
        intentar(self.c, "INSERT INTO turno (id_turno,hora_inicio,hora_fin) VALUES (50,'18:30:00','19:30:00')")
        alta_partido(self.c, 101, 1, 11, 12, DIA)
        self.rechaza(INSERTAR, None, partido(1, 13, 14, turno=50))

    @defecto("REG-13", "Se aceptó: la cancha quedó con dos partidos a la misma hora, uno de cada edición.")
    def test_cancha_ocupada_por_otra_edicion(self):
        """CP-PAR-17 | Cancha ocupada por otra edición | Alta en la edición 2 en el horario del partido 10 de la edición 1 | Rechazo: la cancha ya tiene partido"""
        self.rechaza(INSERTAR, None, partido(1, 11, 12, *self.horario_del_partido_10()))

    @defecto("REG-13", "Se aceptó: la cancha quedó con dos partidos a la misma hora, uno de cada edición.")
    def test_mover_a_cancha_de_otra_edicion(self):
        """CP-PAR-18 | Mover un partido a una cancha de otra edición | UPDATE al horario del partido 10 de la edición 1 | Rechazo: la cancha ya tiene partido"""
        alta_partido(self.c, 101, 1, 11, 12, DIA)
        self.rechaza("UPDATE partido SET dia=%s,id_turno=%s,nombre_cancha=%s,id_complejo=%s WHERE id_partido=101",
                     None, self.horario_del_partido_10())

    # ---------------------------------------------------------------- cruces
    def test_cruce_repetido(self):
        """CP-PAR-19 | Cruce repetido en la edición | Alta de 11 contra 12 en otra fecha, cuando ya existe ese cruce | Rechazo: esos equipos ya se enfrentan"""
        alta_partido(self.c, 101, 1, 11, 12, DIA)
        self.rechaza(INSERTAR, "enfrentan", partido(2, 11, 12, OTRO_DIA))

    def test_cruce_invertido(self):
        """CP-PAR-20 | Cruce repetido con la localía invertida | Alta de 12 contra 11 en otra fecha, cuando ya existe 11 contra 12 | Rechazo: esos equipos ya se enfrentan"""
        alta_partido(self.c, 101, 1, 11, 12, DIA)
        self.rechaza(INSERTAR, "enfrentan", partido(2, 12, 11, OTRO_DIA))

    def test_cruce_repetido_por_update(self):
        """CP-PAR-21 | Cruce repetido por edición | UPDATE de los equipos de un partido a un cruce ya existente | Rechazo: esos equipos ya se enfrentan"""
        alta_partido(self.c, 101, 1, 11, 12, DIA)
        alta_partido(self.c, 102, 2, 13, 14, OTRO_DIA)
        self.rechaza("UPDATE partido SET id_equipo_local=11,id_equipo_visitante=12 WHERE id_partido=102", "enfrentan")

    def test_cruce_tras_cancelar(self):
        """CP-PAR-22 | Cruce permitido tras cancelar el anterior | Cancelar 11 contra 12 y programar otra vez ese cruce | Se acepta"""
        alta_partido(self.c, 101, 1, 11, 12, DIA)
        q(self.c, CANCELAR)
        self.acepta(INSERTAR, partido(2, 11, 12, OTRO_DIA))

    def test_reactivar_cancelado(self):
        """CP-PAR-23 | Reactivar un partido cancelado | Cancelar un partido y volverlo a programado | Se acepta"""
        alta_partido(self.c, 101, 1, 11, 12, DIA)
        q(self.c, CANCELAR)
        self.acepta("UPDATE partido SET estado='programado' WHERE id_partido=101")

    def test_reactivar_con_cruce_repuesto(self):
        """CP-PAR-24 | Reactivar un cancelado con el cruce ya repuesto | Cancelar, programar otra vez el cruce y reactivar el cancelado | Rechazo: esos equipos ya se enfrentan"""
        alta_partido(self.c, 101, 1, 11, 12, DIA)
        q(self.c, CANCELAR)
        alta_partido(self.c, 102, 2, 11, 12, OTRO_DIA)
        self.rechaza("UPDATE partido SET estado='programado' WHERE id_partido=101", "enfrentan")

    # ---------------------------------------------------------------- una vez por fecha
    def test_dos_veces_en_una_fecha(self):
        """CP-PAR-25 | Equipo dos veces en una fecha | El equipo 11 juega la fecha 1; alta de 11 contra 13 en esa fecha | Rechazo: el equipo ya tiene partido en esa fecha"""
        alta_partido(self.c, 101, 1, 11, 12, DIA)
        self.rechaza(INSERTAR, "en esa fecha", partido(1, 11, 13, OTRO_DIA))

    def test_dos_veces_en_una_fecha_como_visitante(self):
        """CP-PAR-26 | Equipo dos veces en una fecha como visitante | El equipo 11 juega la fecha 1; alta de 13 contra 11 en esa fecha | Rechazo: el equipo ya tiene partido en esa fecha"""
        alta_partido(self.c, 101, 1, 11, 12, DIA)
        self.rechaza(INSERTAR, "en esa fecha", partido(1, 13, 11, OTRO_DIA))

    def test_dos_veces_en_una_fecha_por_update(self):
        """CP-PAR-27 | Cambiar de fecha a una donde el equipo ya juega | UPDATE del número de fecha de otro partido del equipo 11 | Rechazo: el equipo ya tiene partido en esa fecha"""
        alta_partido(self.c, 101, 1, 11, 12, DIA)
        alta_partido(self.c, 102, 2, 11, 13, OTRO_DIA)
        self.rechaza("UPDATE partido SET numero_fecha=1 WHERE id_partido=102", "en esa fecha")

    def test_cancelado_no_ocupa_la_fecha(self):
        """CP-PAR-28 | Un partido cancelado no ocupa la fecha | Cancelar el partido del equipo 11 y programarle otro en esa fecha | Se acepta"""
        alta_partido(self.c, 101, 1, 11, 12, DIA)
        q(self.c, CANCELAR)
        self.acepta(INSERTAR, partido(1, 11, 13, OTRO_DIA))

    def test_numero_de_fecha_cero(self):
        """CP-PAR-29 | Número de fecha fuera de rango | Alta con el número de fecha 0 | Rechazo por la restricción CHECK"""
        self.rechaza(INSERTAR, "chk_partido_fecha", partido(0, 11, 12))

    # ---------------------------------------------------------------- fechas y estado de la edición
    @defecto("REG-14", "Se aceptó: el partido quedó en 2030, después del fin de la edición.")
    def test_dia_posterior_a_la_edicion(self):
        """CP-PAR-30 | Partido después del fin de la edición | Alta el 2030-01-01 en una edición que termina el 2027-06-30 | Rechazo: el día está fuera de las fechas de la edición"""
        self.rechaza(INSERTAR, None, partido(1, 11, 12, "2030-01-01"))

    @defecto("REG-14", "Se aceptó: el partido quedó antes del inicio de la edición.")
    def test_dia_anterior_a_la_edicion(self):
        """CP-PAR-31 | Partido antes del inicio de la edición | Alta el 2026-09-01 en una edición que empieza el 2026-10-01 | Rechazo: el día está fuera de las fechas de la edición"""
        self.rechaza(INSERTAR, None, partido(1, 11, 12, "2026-09-01"))

    @defecto("REG-14", "Se aceptó: el partido quedó en 2030, después del fin de la edición.")
    def test_mover_fuera_de_la_edicion(self):
        """CP-PAR-32 | Mover un partido fuera de la edición | UPDATE del día a 2030-01-01 | Rechazo: el día está fuera de las fechas de la edición"""
        alta_partido(self.c, 101, 1, 11, 12, DIA)
        self.rechaza("UPDATE partido SET dia='2030-01-01' WHERE id_partido=101")

    @defecto("REG-14", "Se aceptó: el partido quedó programado en una edición finalizada.")
    def test_partido_en_edicion_finalizada(self):
        """CP-PAR-33 | Partido en una edición finalizada | Finalizar la edición y dar de alta un partido | Rechazo: la edición ya terminó"""
        q(self.c, "UPDATE torneo SET estado='finalizado' WHERE id_torneo=2")
        self.rechaza(INSERTAR, None, partido(1, 11, 12))

    # ---------------------------------------------------------------- estado jugado
    def test_alta_jugado_con_turno_futuro(self):
        """CP-PAR-34 | Alta como jugado con turno futuro | Reloj antes del día del partido; alta con estado jugado | Rechazo: el día y turno todavía no pasaron"""
        mover_reloj(self.c, ANTES)
        self.rechaza(INSERTAR, "ya pasaron", partido(1, 11, 12, estado="jugado"))

    def test_marcar_jugado_con_turno_futuro(self):
        """CP-PAR-35 | Marcar jugado con turno futuro | Reloj antes del día del partido; UPDATE a jugado | Rechazo: el día y turno todavía no pasaron"""
        alta_partido(self.c, 101, 1, 11, 12, DIA)
        mover_reloj(self.c, ANTES)
        self.rechaza(MARCAR, "ya pasaron")

    def test_procedimiento_con_turno_futuro(self):
        """CP-PAR-36 | Procedimiento de cierre con turno futuro | Reloj antes del día del partido; llamar a sp_marcar_partido_jugado | Rechazo: el día y turno todavía no pasaron"""
        alta_partido(self.c, 101, 1, 11, 12, DIA)
        mover_reloj(self.c, ANTES)
        self.rechaza(PROCEDIMIENTO, "ya pasaron")

    def test_marcar_jugado_un_segundo_antes(self):
        """CP-PAR-37 | Marcar jugado un segundo antes del fin del turno | Reloj a las 18:59:59 de un turno que termina a las 19:00 | Rechazo: el día y turno todavía no pasaron"""
        alta_partido(self.c, 101, 1, 11, 12, DIA)
        mover_reloj(self.c, "2026-12-07 18:59:59")
        self.rechaza(MARCAR, "ya pasaron")

    def test_marcar_jugado_al_terminar_el_turno(self):
        """CP-PAR-38 | Marcar jugado justo al terminar el turno | Reloj a las 19:00:00, planilla firmada y UPDATE a jugado | Se acepta y el partido queda jugado"""
        alta_partido(self.c, 101, 1, 11, 12, DIA)
        mover_reloj(self.c, FIN_TURNO)
        firmar_planteles(self.c)
        self.acepta(MARCAR)
        self.assertEqual(valor(self.c, "SELECT estado FROM partido WHERE id_partido=101"), "jugado")

    def test_procedimiento_marca_jugado(self):
        """CP-PAR-39 | Procedimiento de cierre con turno terminado | Planilla firmada; llamar a sp_marcar_partido_jugado | Se acepta y el partido queda jugado"""
        alta_partido(self.c, 101, 1, 11, 12, DIA)
        mover_reloj(self.c, DESPUES)
        firmar_planteles(self.c)
        self.acepta(PROCEDIMIENTO)
        self.assertEqual(valor(self.c, "SELECT estado FROM partido WHERE id_partido=101"), "jugado")

    def test_procedimiento_con_postergado(self):
        """CP-PAR-40 | Procedimiento de cierre con un partido postergado | Turno terminado; llamar a sp_marcar_partido_jugado | Rechazo: solo se cierra un partido programado"""
        alta_partido(self.c, 101, 1, 11, 12, DIA, estado="postergado")
        mover_reloj(self.c, DESPUES)
        self.rechaza(PROCEDIMIENTO, "solo un partido programado")

    def test_procedimiento_con_partido_inexistente(self):
        """CP-PAR-41 | Procedimiento de cierre con un partido inexistente | Llamar a sp_marcar_partido_jugado con el partido 999 | Rechazo: el partido no existe"""
        self.rechaza("CALL sp_marcar_partido_jugado(999)", "no existe")

    @defecto("REG-15", "Se aceptó: el partido quedó jugado 0-0 sin nadie en la planilla.")
    def test_marcar_jugado_sin_planilla(self):
        """CP-PAR-42 | Marcar jugado un partido sin planilla | Turno terminado y sin firmas; UPDATE a jugado | Rechazo: un partido jugado debe tener planilla"""
        alta_partido(self.c, 101, 1, 11, 12, DIA)
        mover_reloj(self.c, DESPUES)
        self.rechaza(MARCAR)

    @defecto("REG-15", "Se aceptó: el partido quedó jugado 0-0 sin nadie en la planilla.")
    def test_procedimiento_sin_planilla(self):
        """CP-PAR-43 | Procedimiento de cierre sin planilla | Turno terminado y sin firmas; llamar a sp_marcar_partido_jugado | Rechazo: un partido jugado debe tener planilla"""
        alta_partido(self.c, 101, 1, 11, 12, DIA)
        mover_reloj(self.c, DESPUES)
        self.rechaza(PROCEDIMIENTO)

    @defecto("REG-15", "Se aceptó: el partido nació jugado, sin planilla y con las 48 h vencidas.")
    def test_alta_directa_como_jugado(self):
        """CP-PAR-44 | Alta directa de un partido como jugado | Alta con estado jugado cuando pasaron más de 48 h del turno | Rechazo: no tiene planilla y ya no se podría cargar"""
        mover_reloj(self.c, VENCIDO)
        self.rechaza(INSERTAR, None, partido(1, 11, 12, estado="jugado"))

    @defecto("REG-15", "El partido quedó jugado sin planilla: pasadas las 48 h se rechazó firmarla.")
    def test_jugado_sin_planilla_no_queda_cerrado(self):
        """CP-PAR-45 | Partido jugado sin planilla con las 48 h vencidas | Marcarlo jugado sin firmas e intentar firmar cuatro días después | No queda jugado y sin planilla"""
        alta_partido(self.c, 101, 1, 11, 12, DIA)
        mover_reloj(self.c, DESPUES)
        intentar(self.c, MARCAR)
        mover_reloj(self.c, VENCIDO)
        intentar(self.c, "INSERT INTO planilla_partido (id_partido,ci_jugador,id_equipo) VALUES (101,'11111111',11)")
        cerrados_sin_planilla = valor(self.c, """
            SELECT COUNT(*) FROM partido p WHERE p.id_partido=101 AND p.estado='jugado'
            AND NOT EXISTS (SELECT 1 FROM planilla_partido pp WHERE pp.id_partido=p.id_partido)""")
        self.assertEqual(cerrados_sin_planilla, 0)

    # ---------------------------------------------------------------- borrado
    def test_no_borrar_jugado(self):
        """CP-PAR-46 | Borrar un partido jugado | DELETE del partido 1 de los datos, que está jugado | Rechazo: un partido jugado no se elimina"""
        self.rechaza("DELETE FROM partido WHERE id_partido=1", "ya ha sido jugado")

    def test_borrar_programado(self):
        """CP-PAR-47 | Borrar un partido programado | DELETE de un partido sin planilla | Se acepta y el partido ya no existe"""
        alta_partido(self.c, 101, 1, 11, 12, DIA)
        self.acepta("DELETE FROM partido WHERE id_partido=101")
        self.assertEqual(valor(self.c, "SELECT COUNT(*) FROM partido WHERE id_partido=101"), 0)


class EdicionEnInscripcion(CasoTransaccional):
    """Edición 2 todavía en inscripción, con el equipo 15 sin jugadores."""
    def setUp(self):
        super().setUp()
        edicion_prueba(self.c, cerrar_inscripcion=False)
        q(self.c, "INSERT INTO equipo (id_equipo,nombre,id_torneo,id_facultad,ci_capitan) "
                  "VALUES (15,'Incompleto',2,1,'11111116')")

    def test_local_con_menos_de_cinco(self):
        """CP-PAR-48 | Local con menos de 5 jugadores | Alta con el equipo 15, sin plantel, como local | Rechazo: el local necesita al menos 5 jugadores"""
        self.rechaza(INSERTAR, "local debe tener", partido(1, 15, 12))

    def test_visitante_con_menos_de_cinco(self):
        """CP-PAR-49 | Visitante con menos de 5 jugadores | Alta con el equipo 15, sin plantel, como visitante | Rechazo: el visitante necesita al menos 5 jugadores"""
        self.rechaza(INSERTAR, "visitante debe tener", partido(1, 12, 15))

    @defecto("REG-14", "Se aceptó: el partido quedó programado con la edición en inscripción.")
    def test_partido_en_edicion_en_inscripcion(self):
        """CP-PAR-50 | Partido en una edición en inscripción | Alta con dos planteles válidos antes de cerrar la inscripción | Rechazo: la edición todavía no empezó"""
        self.rechaza(INSERTAR, None, partido(1, 11, 12))


class Turnos(CasoTransaccional):
    def test_turno_valido(self):
        """CP-PAR-51 | Turno de una hora dentro de la franja | Alta del turno de 21:30 a 22:30 | Se acepta"""
        self.acepta(TURNO, ("21:30:00", "22:30:00"))

    def test_turno_antes_de_la_franja(self):
        """CP-PAR-52 | Turno antes de la franja horaria | Alta del turno de 17:00 a 18:00 | Rechazo: los turnos van de 18:00 a 23:00"""
        self.rechaza(TURNO, "chk_turno_franja", ("17:00:00", "18:00:00"))

    def test_turno_despues_de_la_franja(self):
        """CP-PAR-53 | Turno que termina después de la franja | Alta del turno de 22:30 a 23:30 | Rechazo: los turnos van de 18:00 a 23:00"""
        self.rechaza(TURNO, "chk_turno_franja", ("22:30:00", "23:30:00"))

    def test_turno_de_dos_horas(self):
        """CP-PAR-54 | Turno de dos horas | Alta del turno de 18:00 a 20:00 | Rechazo: los turnos duran una hora"""
        self.rechaza(TURNO, "chk_turno_duracion", ("18:00:00", "20:00:00"))

    def test_turno_de_media_hora(self):
        """CP-PAR-55 | Turno de media hora | Alta del turno de 18:00 a 18:30 | Rechazo: los turnos duran una hora"""
        self.rechaza(TURNO, "chk_turno_duracion", ("18:00:00", "18:30:00"))

    def test_turno_repetido(self):
        """CP-PAR-56 | Turno repetido | Alta del turno de 18:00 a 19:00, que ya existe | Rechazo por clave única"""
        self.rechaza(TURNO, "uk_turno_horas", ("18:00:00", "19:00:00"))
