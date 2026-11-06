"""Ediciones del torneo: datos válidos, estados y efectos de reabrir la inscripción."""
from base import CasoTransaccional, defecto, edicion_prueba, intentar, q, valor

NUEVA = ("INSERT INTO torneo (nombre,anio,semestre,fecha_inicio,fecha_fin,estado) "
         "VALUES (%s,%s,%s,%s,%s,%s)")


class DatosDeLaEdicion(CasoTransaccional):
    def test_edicion_valida(self):
        """CP-EDI-01 | Crear una edición válida | Alta en inscripción para 2027, semestre 1 | Se acepta"""
        self.acepta(NUEVA, ("Prueba", 2027, 1, "2027-03-01", "2027-06-30", "inscripcion"))

    def test_fechas_invertidas(self):
        """CP-EDI-02 | Edición con fechas invertidas | Fecha de inicio posterior a la de fin | Rechazo por CHECK"""
        self.rechaza(NUEVA, "chk_torneo_fechas", ("Prueba", 2027, 1, "2027-07-01", "2027-03-01", "inscripcion"))

    def test_semestre_invalido(self):
        """CP-EDI-03 | Semestre inexistente | Alta con semestre 3 | Rechazo por CHECK"""
        self.rechaza(NUEVA, "chk_torneo_semestre", ("Prueba", 2027, 3, "2027-03-01", "2027-06-30", "inscripcion"))

    def test_semestre_repetido(self):
        """CP-EDI-04 | Dos ediciones en el mismo semestre | Alta para 2026, semestre 2, que ya existe | Rechazo por clave duplicada"""
        self.rechaza(NUEVA, "duplicate", ("Otra", 2026, 2, "2026-08-01", "2026-11-30", "inscripcion"))


class CambiosDeEstado(CasoTransaccional):
    def test_cierre_valido(self):
        """CP-EDI-05 | Cerrar la inscripción con planteles válidos | Pasar la edición 2 a en curso | Se acepta"""
        edicion_prueba(self.c, cerrar_inscripcion=False)
        self.acepta("UPDATE torneo SET estado='en curso' WHERE id_torneo=2")

    @defecto("REG-06", "Se aceptó: la edición en curso volvió a inscripción.")
    def test_reabrir_inscripcion(self):
        """CP-EDI-06 | Reabrir la inscripción de una edición en curso | Pasar la edición 1 a inscripción | Rechazo: el estado no retrocede"""
        self.rechaza("UPDATE torneo SET estado='inscripcion' WHERE id_torneo=1")

    @defecto("REG-06", "Se aceptó: la edición finalizó con partidos sin jugar.")
    def test_finalizar_con_pendientes(self):
        """CP-EDI-07 | Finalizar con partidos pendientes | Pasar a finalizado la edición 1 | Rechazo: quedan partidos sin jugar"""
        self.rechaza("UPDATE torneo SET estado='finalizado' WHERE id_torneo=1")

    @defecto("REG-06", "Se aceptó: una edición finalizada volvió a en curso.")
    def test_reactivar_finalizada(self):
        """CP-EDI-08 | Reactivar una edición finalizada | Pasar de finalizado a en curso | Rechazo: queda cerrada"""
        edicion_prueba(self.c)
        q(self.c, "UPDATE torneo SET estado='finalizado' WHERE id_torneo=2")
        self.rechaza("UPDATE torneo SET estado='en curso' WHERE id_torneo=2")


class EfectosDeReabrir(CasoTransaccional):
    @defecto("REG-07", "La sanción desapareció por la cascada al quitar y reinscribir al jugador.")
    def test_reabrir_no_pierde_sanciones(self):
        """CP-EDI-09 | Reabrir no pierde sanciones | Reabrir, quitar y reinscribir a un jugador sancionado | La sanción sigue vigente"""
        intentar(self.c, "UPDATE torneo SET estado='inscripcion' WHERE id_torneo=1")
        intentar(self.c, "DELETE FROM equipo_jugador_torneo WHERE ci_jugador='66666662'")
        intentar(self.c, "INSERT INTO equipo_jugador_torneo VALUES (6,'66666662',1,2)")
        self.assertEqual(valor(self.c, "SELECT COUNT(*) FROM sancion_jugador WHERE ci_jugador='66666662'"), 1)
