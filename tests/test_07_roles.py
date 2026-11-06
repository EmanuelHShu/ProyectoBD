"""Privilegios de las cuentas MySQL que usa la aplicacion y evasiones desde una sesion directa."""
from datetime import date, timedelta

from base import (CUENTA_ADMIN, CUENTA_LOGIN, CUENTA_PLANILLERO, CasoAislado, CasoTransaccional, alta_partido,
                  conectar, defecto, edicion_prueba, firmar, intentar, q, valor)

SUPLENTE = "11111114"     # integra el equipo 1 y no firmo el partido 10, programado
TABLAS_DE_LECTURA = ("facultad", "jugador", "torneo", "equipo", "equipo_jugador_torneo", "complejo", "cancha",
                     "turno", "partido", "planilla_partido", "gol", "tarjeta", "sancion_jugador")
CATALOGOS = ("torneo", "equipo", "equipo_jugador_torneo", "facultad", "complejo", "cancha", "turno")

FIRMA = f"INSERT INTO planilla_partido (id_partido,ci_jugador,id_equipo) VALUES (10,'{SUPLENTE}',1)"
GOL = f"INSERT INTO gol (id_partido,ci_jugador,minuto,autogol) VALUES (10,'{SUPLENTE}',5,false)"
ROJA = f"INSERT INTO tarjeta (id_partido,ci_jugador,minuto,color) VALUES (10,'{SUPLENTE}',20,'roja')"
GOL_EN_CERRADO = "INSERT INTO gol (id_partido,ci_jugador,minuto,autogol) VALUES (1,'11111113',80,false)"
RECALCULAR = "CALL sp_recalcular_sanciones_automaticas('66666661',1)"


class Cuentas(CasoTransaccional):
    """Una conexion por cuenta, con transaccion revertida al final. Solo una de ellas escribe por prueba."""
    def setUp(self):
        super().setUp()
        self.login = self.cuenta(CUENTA_LOGIN)
        self.planillero = self.cuenta(CUENTA_PLANILLERO)
        self.admin = self.cuenta(CUENTA_ADMIN)

    def cuenta(self, datos):
        conexion = conectar(*datos, autocommit=False)
        self.addCleanup(conexion.close)
        self.addCleanup(conexion.rollback)
        return conexion


class CuentaDeLogin(Cuentas):
    def test_lee_login(self):
        """CP-ROL-01 | login_user lee la tabla login | SELECT sobre login con la cuenta de autenticación | Devuelve las 2 cuentas web"""
        self.assertEqual(valor(self.login, "SELECT COUNT(*) FROM login"), 2)

    def test_no_lee_ninguna_otra_tabla(self):
        """CP-ROL-02 | login_user no lee ninguna otra tabla | SELECT sobre cada tabla y vista distinta de login | Acceso denegado en todas"""
        objetos = q(self.c, "SELECT table_name AS nombre FROM information_schema.tables "
                            "WHERE table_schema='torneo_futbol5' AND table_name<>'login'")
        self.assertEqual(len(objetos), 14)
        for objeto in objetos:
            self.rechaza(f"SELECT * FROM {objeto['nombre']}", "denied", conexion=self.login)

    def test_no_modifica_login(self):
        """CP-ROL-03 | login_user no modifica login | INSERT, UPDATE y DELETE sobre login | Acceso denegado en las tres"""
        for sentencia in ("INSERT INTO login VALUES ('x@ucu.edu.uy','clave','administrador')",
                          "UPDATE login SET rol='administrador'", "DELETE FROM login"):
            self.rechaza(sentencia, "denied", conexion=self.login)

    def test_no_ejecuta_procedimientos(self):
        """CP-ROL-04 | login_user no ejecuta procedimientos | CALL de los dos procedimientos | Acceso denegado en ambos"""
        self.rechaza("CALL sp_marcar_partido_jugado(10)", "denied", conexion=self.login)
        self.rechaza(RECALCULAR, "denied", conexion=self.login)

    def test_cada_cuenta_entra_con_su_rol(self):
        """CP-ROL-05 | Cada cuenta entra con su rol activo | SELECT CURRENT_ROLE() en las tres cuentas | rol_login, rol_planillero y rol_administrador"""
        self.assertIn("rol_login", valor(self.login, "SELECT CURRENT_ROLE()"))
        self.assertIn("rol_planillero", valor(self.planillero, "SELECT CURRENT_ROLE()"))
        self.assertIn("rol_administrador", valor(self.admin, "SELECT CURRENT_ROLE()"))


class PlanilleroSinPermiso(Cuentas):
    def test_no_lee_login(self):
        """CP-ROL-06 | El planillero no lee login | SELECT sobre la tabla de contraseñas | Acceso denegado"""
        self.rechaza("SELECT * FROM login", "denied", conexion=self.planillero)

    def test_no_escribe_jugador(self):
        """CP-ROL-07 | El planillero no escribe jugador | INSERT, UPDATE y DELETE sobre jugador | Acceso denegado en las tres"""
        for sentencia in ("INSERT INTO jugador VALUES ('1','a','b','c@d.uy','2000-01-01',1,'grado')",
                          "UPDATE jugador SET nombre='X' WHERE ci='11111111'",
                          "DELETE FROM jugador WHERE ci='11111116'"):
            self.rechaza(sentencia, "denied", conexion=self.planillero)

    def test_no_hace_update_en_partido(self):
        """CP-ROL-08 | El planillero no hace UPDATE en partido | Marcar jugado con un UPDATE directo | Acceso denegado"""
        self.rechaza("UPDATE partido SET estado='jugado' WHERE id_partido=10", "denied", conexion=self.planillero)

    def test_no_hace_delete_en_partido(self):
        """CP-ROL-09 | El planillero no hace DELETE en partido | Borrar un partido programado | Acceso denegado"""
        self.rechaza("DELETE FROM partido WHERE id_partido=10", "denied", conexion=self.planillero)

    def test_no_inserta_partidos(self):
        """CP-ROL-10 | El planillero no inserta partidos | INSERT sobre partido | Acceso denegado"""
        self.rechaza("INSERT INTO partido (id_torneo,numero_fecha,id_equipo_local,id_equipo_visitante,dia,id_turno,"
                     "nombre_cancha,id_complejo,estado) VALUES (1,6,1,2,'2026-12-01',1,'Cancha 1',1,'programado')",
                     "denied", conexion=self.planillero)

    def test_no_escribe_sanciones(self):
        """CP-ROL-11 | El planillero no escribe sanciones | INSERT, UPDATE y DELETE sobre sancion_jugador | Acceso denegado en las tres"""
        for sentencia in ("INSERT INTO sancion_jugador (ci_jugador,id_torneo,motivo,numero_fecha_inicio,cantidad_fechas) "
                          "VALUES ('11111111',1,'disciplinaria',5,1)",
                          "UPDATE sancion_jugador SET cantidad_fechas=1", "DELETE FROM sancion_jugador"):
            self.rechaza(sentencia, "denied", conexion=self.planillero)

    def test_no_ejecuta_el_recalculo(self):
        """CP-ROL-12 | El planillero no ejecuta el recálculo | CALL sp_recalcular_sanciones_automaticas | Acceso denegado"""
        self.rechaza(RECALCULAR, "denied", conexion=self.planillero)

    def test_no_modifica_catalogos(self):
        """CP-ROL-13 | El planillero no modifica catálogos | DELETE sobre ediciones, equipos, planteles, facultades, complejos, canchas y turnos | Acceso denegado en todos"""
        for tabla in CATALOGOS:
            self.rechaza(f"DELETE FROM {tabla}", "denied", conexion=self.planillero)

    def test_no_toca_un_partido_cerrado(self):
        """CP-ROL-14 | El planillero respeta el plazo de 48 horas | Insertar un gol en el partido 1, de agosto | Rechazo por el plazo de 48 horas"""
        self.rechaza(GOL_EN_CERRADO, "48 horas", conexion=self.planillero)


class PlanilleroConPermiso(Cuentas):
    def test_lee_las_tablas_que_necesita(self):
        """CP-ROL-15 | El planillero lee las tablas que necesita | SELECT sobre las 13 tablas distintas de login | Se aceptan todas"""
        for tabla in TABLAS_DE_LECTURA:
            self.acepta(f"SELECT * FROM {tabla}", conexion=self.planillero)

    def test_lee_la_vista(self):
        """CP-ROL-16 | El planillero lee la vista de resultados | SELECT sobre v_resultado_partido del partido 1 | Devuelve el resultado 2-1"""
        fila = q(self.planillero, "SELECT goles_local,goles_visitante FROM v_resultado_partido WHERE id_partido=1")[0]
        self.assertEqual((fila["goles_local"], fila["goles_visitante"]), (2, 1))

    def test_firma_planilla(self):
        """CP-ROL-17 | El planillero firma la planilla | INSERT sobre planilla_partido en un partido programado | Se acepta"""
        self.acepta(FIRMA, conexion=self.planillero)

    def test_carga_un_gol(self):
        """CP-ROL-18 | El planillero carga un gol | Firmar a un jugador e insertar su gol | Se acepta"""
        q(self.planillero, FIRMA)
        self.acepta(GOL, conexion=self.planillero)

    def test_carga_una_tarjeta_y_se_crea_la_sancion(self):
        """CP-ROL-19 | La tarjeta del planillero crea la sanción por DEFINER | Firmar a un jugador e insertar una roja en la fecha 4 | Se acepta y aparece la sanción desde la fecha 5"""
        q(self.planillero, FIRMA)
        self.acepta(ROJA, conexion=self.planillero)
        self.assertEqual(valor(self.planillero, "SELECT numero_fecha_inicio FROM sancion_jugador "
                                                "WHERE ci_jugador=%s AND id_torneo=1", (SUPLENTE,)), 5)

    def test_corrige_gol_y_tarjeta(self):
        """CP-ROL-20 | El planillero corrige gol y tarjeta | Editar el minuto del gol y borrar la tarjeta | Se aceptan y la sanción se retira"""
        q(self.planillero, FIRMA)
        q(self.planillero, GOL)
        q(self.planillero, ROJA)
        self.acepta("UPDATE gol SET minuto=6 WHERE id_partido=10", conexion=self.planillero)
        self.acepta("DELETE FROM tarjeta WHERE id_partido=10", conexion=self.planillero)
        self.assertEqual(valor(self.planillero, "SELECT COUNT(*) FROM sancion_jugador WHERE ci_jugador=%s", (SUPLENTE,)), 0)

    def test_quita_de_planilla(self):
        """CP-ROL-21 | El planillero quita de la planilla | Borrar de planilla a un jugador con gol y roja | Se borran la fila, el gol, la tarjeta y la sanción"""
        q(self.planillero, FIRMA)
        q(self.planillero, GOL)
        q(self.planillero, ROJA)
        self.acepta(f"DELETE FROM planilla_partido WHERE id_partido=10 AND ci_jugador='{SUPLENTE}'", conexion=self.planillero)
        for tabla in ("planilla_partido", "gol", "tarjeta"):
            self.assertEqual(valor(self.planillero, f"SELECT COUNT(*) FROM {tabla} WHERE id_partido=10"), 0)
        self.assertEqual(valor(self.planillero, "SELECT COUNT(*) FROM sancion_jugador WHERE ci_jugador=%s", (SUPLENTE,)), 0)

    def test_el_procedimiento_rechaza_un_partido_inexistente(self):
        """CP-ROL-22 | Marcar jugado un partido inexistente | CALL sp_marcar_partido_jugado con un id que no existe | Rechazo: el partido no existe"""
        self.rechaza("CALL sp_marcar_partido_jugado(9999)", "no existe", conexion=self.planillero)

    def test_el_procedimiento_rechaza_un_partido_ya_jugado(self):
        """CP-ROL-23 | Marcar jugado un partido ya jugado | CALL sp_marcar_partido_jugado del partido 1 | Rechazo: solo se marca un partido programado"""
        self.rechaza("CALL sp_marcar_partido_jugado(1)", "solo un partido programado", conexion=self.planillero)


class CuentaAdministrador(Cuentas):
    def test_lee_login(self):
        """CP-ROL-24 | admin_user lee login | SELECT sobre login | Devuelve las 2 cuentas web"""
        self.assertEqual(valor(self.admin, "SELECT COUNT(*) FROM login"), 2)

    def test_escribe_tablas(self):
        """CP-ROL-25 | admin_user escribe las tablas | INSERT, UPDATE y DELETE sobre facultad e INSERT de una sanción | Se aceptan todas"""
        self.acepta("INSERT INTO facultad (id_facultad,nombre) VALUES (99,'Prueba')", conexion=self.admin)
        self.acepta("UPDATE facultad SET nombre='Prueba 2' WHERE id_facultad=99", conexion=self.admin)
        self.acepta("DELETE FROM facultad WHERE id_facultad=99", conexion=self.admin)
        self.acepta("INSERT INTO sancion_jugador (ci_jugador,id_torneo,motivo,numero_fecha_inicio,cantidad_fechas) "
                    f"VALUES ('{SUPLENTE}',1,'disciplinaria',5,1)", conexion=self.admin)

    def test_ejecuta_el_recalculo(self):
        """CP-ROL-26 | admin_user ejecuta el recálculo | CALL sp_recalcular_sanciones_automaticas de un jugador con roja | Se acepta y su sanción sigue"""
        self.acepta(RECALCULAR, conexion=self.admin)
        self.assertEqual(valor(self.admin, "SELECT COUNT(*) FROM sancion_jugador WHERE ci_jugador='66666661'"), 1)

    def test_respeta_los_triggers(self):
        """CP-ROL-27 | admin_user respeta los triggers | Borrar y editar el partido 1, jugado en agosto | Rechazo: no se elimina y el plazo venció"""
        self.rechaza("DELETE FROM partido WHERE id_partido=1", "no puede ser eliminado", conexion=self.admin)
        self.rechaza("UPDATE partido SET nombre_cancha='Cancha 2' WHERE id_partido=1", "48 horas", conexion=self.admin)

    def test_no_administra_cuentas(self):
        """CP-ROL-28 | admin_user no administra cuentas | GRANT sobre login y CREATE USER | Acceso denegado en ambos"""
        self.rechaza("GRANT SELECT ON torneo_futbol5.login TO 'planillero_user'@'localhost'", "denied", conexion=self.admin)
        self.rechaza("CREATE USER 'intruso'@'localhost' IDENTIFIED BY 'clave'", "denied", conexion=self.admin)


class Evasiones(Cuentas):
    @defecto("REG-18", "Se aceptó: con SET TIMESTAMP la sesión del planillero reabrió el partido y el gol quedó cargado.")
    def test_set_timestamp_no_reabre_un_partido_cerrado(self):
        """CP-ROL-29 | SET TIMESTAMP no reabre un partido cerrado | El planillero mueve el reloj de su sesión al día siguiente del partido 1 e inserta un gol | Rechazo por el plazo de 48 horas"""
        intentar(self.planillero, "SET TIMESTAMP=UNIX_TIMESTAMP('2026-08-11 12:00:00')")
        self.rechaza(GOL_EN_CERRADO, "48 horas", conexion=self.planillero)

    @defecto("REG-18", "Se aceptó: con foreign_key_checks=0 el planillero cargó un gol de un jugador inexistente.")
    def test_foreign_key_checks_no_crea_huerfanos(self):
        """CP-ROL-30 | foreign_key_checks=0 no crea goles huérfanos | El planillero apaga las claves foráneas de su sesión e inserta un gol sin planilla | Rechazo: la clave foránea sigue vigente"""
        intentar(self.planillero, "SET foreign_key_checks=0")
        self.rechaza("INSERT INTO gol (id_partido,ci_jugador,minuto,autogol) VALUES (10,'00000000',1,false)",
                     conexion=self.planillero)

    @defecto("REG-18", "Se aceptó: con sql_mode vacío el planillero guardó una tarjeta con color vacío.")
    def test_sql_mode_vacio_no_admite_un_color_invalido(self):
        """CP-ROL-31 | sql_mode vacío no admite un color inválido | El planillero vacía el sql_mode de su sesión e inserta una tarjeta verde | Rechazo: el color no es válido"""
        q(self.planillero, FIRMA)
        intentar(self.planillero, "SET SESSION sql_mode=''")
        self.rechaza(f"INSERT INTO tarjeta (id_partido,ci_jugador,minuto,color) VALUES (10,'{SUPLENTE}',5,'verde')",
                     conexion=self.planillero)


class MarcarJugado(CasoAislado):
    def setUp(self):
        super().setUp()
        self.planillero = conectar(*CUENTA_PLANILLERO)
        self.addCleanup(self.planillero.close)
        edicion_prueba(self.c)

    def partido(self, dias):
        alta_partido(self.c, 101, 1, 11, 12, (date.today() + timedelta(days=dias)).isoformat())
        firmar(self.c, 101, 11, ["11111112"])
        firmar(self.c, 101, 12, ["22222222"])

    def test_ejecuta_el_procedimiento(self):
        """CP-ROL-32 | El planillero marca jugado por el procedimiento | CALL sp_marcar_partido_jugado de un partido de ayer | El partido queda jugado sin permiso UPDATE sobre partido"""
        self.partido(-1)
        self.acepta("CALL sp_marcar_partido_jugado(101)", conexion=self.planillero)
        self.assertEqual(valor(self.c, "SELECT estado FROM partido WHERE id_partido=101"), "jugado")

    def test_el_procedimiento_respeta_el_turno(self):
        """CP-ROL-33 | El procedimiento no saltea la regla del turno | CALL sp_marcar_partido_jugado de un partido dentro de 30 días | Rechazo: el turno todavía no pasó"""
        self.partido(30)
        self.rechaza("CALL sp_marcar_partido_jugado(101)", "ya pasaron", conexion=self.planillero)

    @defecto("REG-18", "Se aceptó: con SET TIMESTAMP el planillero marcó jugado un partido de dentro de 30 días.")
    def test_set_timestamp_no_marca_jugado_un_partido_futuro(self):
        """CP-ROL-34 | SET TIMESTAMP no marca jugado un partido futuro | El planillero adelanta el reloj de su sesión y marca jugado un partido de dentro de 30 días | Rechazo y el partido sigue programado"""
        self.partido(30)
        futuro = (date.today() + timedelta(days=31)).isoformat()
        intentar(self.planillero, "SET TIMESTAMP=UNIX_TIMESTAMP(%s)", (futuro + " 12:00:00",))
        self.rechaza("CALL sp_marcar_partido_jugado(101)", conexion=self.planillero)
        self.assertEqual(valor(self.c, "SELECT estado FROM partido WHERE id_partido=101"), "programado")


class EsquemaProtegido(CasoAislado):
    def setUp(self):
        super().setUp()
        self.admin = conectar(*CUENTA_ADMIN)
        self.addCleanup(self.admin.close)

    @defecto("REG-18", "Se aceptó: admin_user vació la tabla gol sin pasar por los triggers.")
    def test_truncate(self):
        """CP-ROL-35 | admin_user no vacía tablas con TRUNCATE | TRUNCATE TABLE gol con la cuenta de la app | Acceso denegado y los goles siguen"""
        self.rechaza("TRUNCATE TABLE gol", "denied", conexion=self.admin)
        self.assertEqual(valor(self.c, "SELECT COUNT(*) FROM gol"), 12)

    @defecto("REG-18", "Se aceptó: admin_user borró el trigger que protege el borrado de goles.")
    def test_drop_trigger(self):
        """CP-ROL-36 | admin_user no borra triggers | DROP TRIGGER trg_gol_before_delete con la cuenta de la app | Acceso denegado y el trigger sigue"""
        self.rechaza("DROP TRIGGER trg_gol_before_delete", "denied", conexion=self.admin)
        self.assertEqual(valor(self.c, "SELECT COUNT(*) FROM information_schema.triggers "
                                       "WHERE trigger_name='trg_gol_before_delete'"), 1)

    @defecto("REG-18", "Se aceptó: admin_user eliminó la tabla gol por tener ALL PRIVILEGES.")
    def test_drop_table(self):
        """CP-ROL-37 | admin_user no borra tablas | DROP TABLE gol con la cuenta de la app | Acceso denegado y la tabla sigue"""
        self.rechaza("DROP TABLE gol", "denied", conexion=self.admin)
        self.assertEqual(valor(self.c, "SELECT COUNT(*) FROM information_schema.tables "
                                       "WHERE table_schema='torneo_futbol5' AND table_name='gol'"), 1)
