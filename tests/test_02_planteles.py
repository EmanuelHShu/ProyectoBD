"""Planteles: inscripción, facultad, dorsales, límites, capitán y cierre de la inscripción."""
from base import CasoAislado, CasoTransaccional, conectar, defecto, edicion_prueba, intentar, q, valor

INSCRIBIR = ("INSERT INTO equipo_jugador_torneo (id_equipo,ci_jugador,id_torneo,numero_camiseta) "
             "VALUES (%s,%s,%s,%s)")
CERRAR = "UPDATE torneo SET estado='en curso' WHERE id_torneo=2"
DOCENTE = "11111116"   # Docente de la facultad 1 que no integra el plantel del equipo 11.


def alta_jugador(c, ci, tipo="grado", facultad=1):
    q(c, "INSERT INTO jugador (ci,nombre,apellido,email,fecha_nacimiento,id_facultad,tipo) "
         "VALUES (%s,'Nombre','Apellido',%s,'2000-01-01',%s,%s)", (ci, f"{ci}@prueba.uy", facultad, tipo))


def alta_equipo(c, capitan=DOCENTE, id_equipo=15, torneo=2, facultad=1):
    q(c, "INSERT INTO equipo (id_equipo,nombre,id_torneo,id_facultad,ci_capitan) VALUES (%s,'Otro',%s,%s,%s)",
      (id_equipo, torneo, facultad, capitan))


def sumar_jugadores(c, equipo, dorsales):
    """Da de alta jugadores de grado de la facultad 1 y los inscribe en el equipo, uno por dorsal."""
    for dorsal in dorsales:
        ci = f"90000{dorsal:04d}"
        alta_jugador(c, ci)
        q(c, INSCRIBIR, (equipo, ci, 2, dorsal))


def tamano_plantel(c, equipo):
    return valor(c, "SELECT COUNT(*) FROM equipo_jugador_torneo WHERE id_equipo=%s", (equipo,))


class Planteles(CasoTransaccional):
    """Edición 2 en inscripción, con los equipos 11 a 14 y planteles de 5 jugadores."""
    def setUp(self):
        super().setUp()
        edicion_prueba(self.c, cerrar_inscripcion=False)

    # ---------------------------------------------------------------- etapa de inscripción
    def test_inscribir_en_inscripcion(self):
        """CP-PLA-01 | Inscribir jugador con la edición en inscripción | Alta de un jugador de la facultad en el equipo 11 | Se acepta y el plantel pasa a 6 jugadores"""
        self.acepta(INSCRIBIR, (11, DOCENTE, 2, 50))
        self.assertEqual(tamano_plantel(self.c, 11), 6)

    def test_inscribir_en_curso(self):
        """CP-PLA-02 | Inscribir jugador con la edición en curso | Cerrar la inscripción e inscribir un jugador | Rechazo: el plantel solo cambia en inscripción"""
        q(self.c, CERRAR)
        self.rechaza(INSCRIBIR, "esta en inscripcion", (11, DOCENTE, 2, 50))

    def test_inscribir_con_edicion_finalizada(self):
        """CP-PLA-03 | Inscribir jugador con la edición finalizada | Finalizar la edición e inscribir un jugador | Rechazo: el plantel solo cambia en inscripción"""
        q(self.c, "UPDATE torneo SET estado='finalizado' WHERE id_torneo=2")
        self.rechaza(INSCRIBIR, "esta en inscripcion", (11, DOCENTE, 2, 50))

    def test_quitar_en_inscripcion(self):
        """CP-PLA-04 | Quitar jugador con la edición en inscripción | Borrar del plantel a un jugador que no es capitán | Se acepta y el plantel pasa a 4 jugadores"""
        self.acepta("DELETE FROM equipo_jugador_torneo WHERE id_equipo=11 AND ci_jugador='11111112'")
        self.assertEqual(tamano_plantel(self.c, 11), 4)

    def test_quitar_en_curso(self):
        """CP-PLA-05 | Quitar jugador con la edición en curso | Cerrar la inscripción y borrar a un jugador del plantel | Rechazo: el plantel solo cambia en inscripción"""
        q(self.c, CERRAR)
        self.rechaza("DELETE FROM equipo_jugador_torneo WHERE id_equipo=11 AND ci_jugador='11111112'", "esta en inscripcion")

    def test_cambiar_dorsal_en_inscripcion(self):
        """CP-PLA-06 | Cambiar dorsal con la edición en inscripción | UPDATE del número de camiseta a un dorsal libre | Se acepta el cambio"""
        self.acepta("UPDATE equipo_jugador_torneo SET numero_camiseta=50 WHERE id_equipo=11 AND ci_jugador='11111112'")

    def test_cambiar_dorsal_en_curso(self):
        """CP-PLA-07 | Cambiar dorsal con la edición en curso | Cerrar la inscripción y cambiar un número de camiseta | Rechazo: el plantel solo cambia en inscripción"""
        q(self.c, CERRAR)
        self.rechaza("UPDATE equipo_jugador_torneo SET numero_camiseta=50 WHERE id_equipo=11 AND ci_jugador='11111112'",
                     "esta en inscripcion")

    # ---------------------------------------------------------------- misma facultad
    def test_jugador_de_otra_facultad(self):
        """CP-PLA-08 | Inscribir jugador de otra facultad | Alta de un jugador de la facultad 6 en el equipo 11 | Rechazo: debe ser de la facultad del equipo"""
        self.rechaza(INSCRIBIR, "facultad", (11, "66666661", 2, 50))

    @defecto("REG-05", "Se aceptó: el jugador quedó en un plantel de otra facultad.")
    def test_editar_facultad_del_jugador(self):
        """CP-PLA-09 | Cambiar la facultad de un jugador inscripto | UPDATE de jugador.id_facultad de un integrante del equipo 11 | Rechazo: quedaría en un plantel de otra facultad"""
        self.rechaza("UPDATE jugador SET id_facultad=2 WHERE ci='11111112'")

    @defecto("REG-05", "Se aceptó: los 5 jugadores del plantel quedaron en un equipo de otra facultad.")
    def test_editar_facultad_del_equipo(self):
        """CP-PLA-10 | Cambiar la facultad de un equipo con plantel | UPDATE de equipo.id_facultad del equipo 11 | Rechazo: el plantel quedaría en otra facultad"""
        self.rechaza("UPDATE equipo SET id_facultad=2 WHERE id_equipo=11")

    def test_editar_facultad_sin_plantel(self):
        """CP-PLA-11 | Cambiar la facultad de un jugador sin plantel | UPDATE de jugador.id_facultad de un jugador no inscripto | Se acepta el cambio"""
        alta_jugador(self.c, "900000001")
        self.acepta("UPDATE jugador SET id_facultad=2 WHERE ci='900000001'")

    # ---------------------------------------------------------------- dorsales
    def test_dorsal_repetido(self):
        """CP-PLA-12 | Dorsal repetido en un plantel | Inscribir a un jugador con un dorsal que el equipo ya usa | Rechazo por clave única"""
        self.rechaza(INSCRIBIR, "uk_ejt_equipo_camiseta", (11, DOCENTE, 2, 1))

    def test_dorsal_repetido_por_update(self):
        """CP-PLA-13 | Cambiar a un dorsal ya usado | UPDATE del número de camiseta a uno ocupado en el mismo plantel | Rechazo por clave única"""
        self.rechaza("UPDATE equipo_jugador_torneo SET numero_camiseta=1 WHERE id_equipo=11 AND ci_jugador='11111112'",
                     "uk_ejt_equipo_camiseta")

    def test_mismo_dorsal_en_otro_equipo(self):
        """CP-PLA-14 | Mismo dorsal en equipos distintos | Inscribir el dorsal 50 en el equipo 11 y también en el 12 | Se aceptan los dos"""
        alta_jugador(self.c, "900000001", facultad=2)
        self.acepta(INSCRIBIR, (11, DOCENTE, 2, 50))
        self.acepta(INSCRIBIR, (12, "900000001", 2, 50))

    def test_dorsal_0(self):
        """CP-PLA-15 | Dorsal por debajo del rango | Inscribir con el dorsal 0 | Rechazo: el dorsal va de 1 a 99"""
        self.rechaza(INSCRIBIR, "chk_ejt_camiseta", (11, DOCENTE, 2, 0))

    def test_dorsal_100(self):
        """CP-PLA-16 | Dorsal por encima del rango | Inscribir con el dorsal 100 | Rechazo: el dorsal va de 1 a 99"""
        self.rechaza(INSCRIBIR, "chk_ejt_camiseta", (11, DOCENTE, 2, 100))

    def test_dorsal_99(self):
        """CP-PLA-17 | Dorsal en el límite superior | Inscribir con el dorsal 99 | Se acepta"""
        self.acepta(INSCRIBIR, (11, DOCENTE, 2, 99))

    # ---------------------------------------------------------------- un equipo por edición
    def test_jugador_en_dos_equipos(self):
        """CP-PLA-18 | Jugador en dos equipos de la misma edición | Inscribir en el equipo 15 a un integrante del equipo 11 | Rechazo por clave única"""
        alta_equipo(self.c)
        self.rechaza(INSCRIBIR, "uk_ejt_jugador_torneo", (15, "11111112", 2, 50))

    def test_jugador_en_dos_ediciones(self):
        """CP-PLA-19 | Jugador en equipos de ediciones distintas | Inscribir en la edición 2 a un integrante de la edición 1 | Se acepta y figura en las dos ediciones"""
        self.acepta(INSCRIBIR, (11, DOCENTE, 2, 50))
        self.assertEqual(valor(self.c, "SELECT COUNT(*) FROM equipo_jugador_torneo WHERE ci_jugador=%s", (DOCENTE,)), 2)

    # ---------------------------------------------------------------- máximo de 10 jugadores
    def test_plantel_de_diez(self):
        """CP-PLA-20 | Plantel de 10 jugadores | Sumar 5 jugadores a un plantel de 5 | Se aceptan y el plantel queda con 10"""
        sumar_jugadores(self.c, 11, range(6, 11))
        self.assertEqual(tamano_plantel(self.c, 11), 10)

    def test_jugador_numero_once(self):
        """CP-PLA-21 | Undécimo jugador en un plantel | Inscribir un jugador en un plantel de 10 | Rechazo: máximo 10 jugadores"""
        sumar_jugadores(self.c, 11, range(6, 11))
        alta_jugador(self.c, "900000001")
        self.rechaza(INSCRIBIR, "mas de 10", (11, "900000001", 2, 50))

    # ---------------------------------------------------------------- máximo de 2 docentes o funcionarios
    def test_dos_docentes_o_funcionarios(self):
        """CP-PLA-22 | Plantel con dos docentes o funcionarios | Inscribir un docente y un funcionario en el equipo 11 | Se aceptan los dos"""
        alta_jugador(self.c, "900000001", "funcionario")
        self.acepta(INSCRIBIR, (11, DOCENTE, 2, 50))
        self.acepta(INSCRIBIR, (11, "900000001", 2, 51))

    def test_tercer_docente_o_funcionario(self):
        """CP-PLA-23 | Tercer docente o funcionario en un plantel | Con un docente y un funcionario, inscribir otro docente | Rechazo: máximo 2 docentes o funcionarios"""
        alta_jugador(self.c, "900000001", "funcionario")
        alta_jugador(self.c, "900000002", "docente")
        q(self.c, INSCRIBIR, (11, DOCENTE, 2, 50))
        q(self.c, INSCRIBIR, (11, "900000001", 2, 51))
        self.rechaza(INSCRIBIR, "maximo 2", (11, "900000002", 2, 52))

    def test_posgrado_no_cuenta_como_docente(self):
        """CP-PLA-24 | Un posgrado no cuenta para el máximo de docentes | Con dos docentes o funcionarios, inscribir un posgrado | Se acepta"""
        alta_jugador(self.c, "900000001", "funcionario")
        alta_jugador(self.c, "900000002", "posgrado")
        q(self.c, INSCRIBIR, (11, DOCENTE, 2, 50))
        q(self.c, INSCRIBIR, (11, "900000001", 2, 51))
        self.acepta(INSCRIBIR, (11, "900000002", 2, 52))

    def test_editar_tipo_sin_superar_maximo(self):
        """CP-PLA-25 | Editar el tipo sin superar el máximo | El equipo 1 tiene un docente; pasar a un jugador de grado a docente | Se acepta el cambio"""
        self.acepta("UPDATE jugador SET tipo='docente' WHERE ci='11111112'")

    @defecto("REG-04", "Se aceptó: el plantel quedó con 3 docentes o funcionarios.")
    def test_editar_tipo_supera_maximo(self):
        """CP-PLA-26 | Editar el tipo supera el máximo de docentes | El equipo 1 ya tiene dos docentes; pasar a otro jugador a funcionario | Rechazo: máximo 2 docentes o funcionarios"""
        q(self.c, "UPDATE jugador SET tipo='docente' WHERE ci='11111112'")
        self.rechaza("UPDATE jugador SET tipo='funcionario' WHERE ci='11111113'")

    # ---------------------------------------------------------------- capitán
    def test_alta_de_equipo_en_inscripcion(self):
        """CP-PLA-27 | Alta de equipo durante la inscripción | Equipo nuevo con capitán de su facultad | Se acepta"""
        self.acepta("INSERT INTO equipo (id_equipo,nombre,id_torneo,id_facultad,ci_capitan) "
                    "VALUES (15,'Otro',2,1,%s)", (DOCENTE,))

    def test_quitar_capitan(self):
        """CP-PLA-28 | Quitar al capitán del plantel | Borrar del plantel al capitán del equipo 11 | Rechazo: primero hay que cambiar el capitán"""
        self.rechaza("DELETE FROM equipo_jugador_torneo WHERE id_equipo=11 AND ci_jugador='11111111'", "capitan")

    def test_capitan_fuera_del_plantel(self):
        """CP-PLA-29 | Nombrar capitán a quien no integra el plantel | UPDATE de ci_capitan con un jugador no inscripto en el equipo | Rechazo: el capitán debe ser del plantel"""
        self.rechaza("UPDATE equipo SET ci_capitan=%s WHERE id_equipo=11", "capitan", (DOCENTE,))

    def test_cambiar_capitan_y_quitar_al_anterior(self):
        """CP-PLA-30 | Cambiar el capitán y quitar al anterior | Nombrar capitán a otro integrante y borrar al anterior del plantel | Se aceptan los dos cambios"""
        self.acepta("UPDATE equipo SET ci_capitan='11111112' WHERE id_equipo=11")
        self.acepta("DELETE FROM equipo_jugador_torneo WHERE id_equipo=11 AND ci_jugador='11111111'")

    def test_capitan_de_dos_equipos(self):
        """CP-PLA-31 | Mismo capitán en dos equipos de la edición | Alta de un equipo con el capitán del equipo 11 | Rechazo por clave única"""
        self.rechaza("INSERT INTO equipo (id_equipo,nombre,id_torneo,id_facultad,ci_capitan) "
                     "VALUES (15,'Otro',2,1,'11111111')", "uk_equipo_capitan_torneo")

    @defecto("REG-16", "Se aceptó: el equipo quedó en la edición en curso sin plantel y con su capitán en otro equipo.")
    def test_equipo_con_edicion_en_curso(self):
        """CP-PLA-32 | Alta de equipo con la edición en curso | Insertar un equipo en la edición 1, que ya empezó | Rechazo: los equipos se crean durante la inscripción"""
        self.rechaza("INSERT INTO equipo (id_equipo,nombre,id_torneo,id_facultad,ci_capitan) "
                     "VALUES (15,'Otro',1,1,%s)", None, (DOCENTE,))

    @defecto("REG-16", "Se aceptó: el equipo de la facultad 1 quedó con un capitán de la facultad 2.")
    def test_equipo_con_capitan_de_otra_facultad(self):
        """CP-PLA-33 | Alta de equipo con capitán de otra facultad | Equipo de la facultad 1 con capitán de la facultad 2 | Rechazo: el capitán debe ser de la facultad del equipo"""
        self.rechaza("INSERT INTO equipo (id_equipo,nombre,id_torneo,id_facultad,ci_capitan) "
                     "VALUES (15,'Otro',2,1,'22222222')")

    # ---------------------------------------------------------------- cierre de la inscripción
    def test_cierre_valido(self):
        """CP-PLA-34 | Cerrar la inscripción con planteles válidos | Pasar a en curso la edición con cuatro planteles de 5 | Se acepta y la edición queda en curso"""
        self.acepta(CERRAR)
        self.assertEqual(valor(self.c, "SELECT estado FROM torneo WHERE id_torneo=2"), "en curso")

    def test_cierre_con_capitan_fuera(self):
        """CP-PLA-35 | Cerrar la inscripción con un capitán fuera del plantel | Equipo 15 con 5 jugadores sin su capitán; pasar a en curso | Rechazo: los capitanes deben estar en su plantel"""
        alta_equipo(self.c)
        sumar_jugadores(self.c, 15, range(1, 6))
        self.rechaza(CERRAR, "capitan")

    def test_cierre_con_menos_de_cinco(self):
        """CP-PLA-36 | Cerrar la inscripción con menos de 5 jugadores | Equipo 15 con su capitán y 3 jugadores más; pasar a en curso | Rechazo: cada plantel necesita al menos 5"""
        alta_equipo(self.c)
        q(self.c, INSCRIBIR, (15, DOCENTE, 2, 50))
        sumar_jugadores(self.c, 15, range(1, 4))
        self.rechaza(CERRAR, "al menos 5")

    # ---------------------------------------------------------------- cambio de equipo
    def test_cambiar_de_equipo_por_update(self):
        """CP-PLA-37 | Cambiar de equipo con UPDATE | Pasar a un jugador del equipo 11 al equipo 15 con UPDATE | Rechazo: hay que quitarlo y volver a inscribirlo"""
        alta_equipo(self.c)
        self.rechaza("UPDATE equipo_jugador_torneo SET id_equipo=15 WHERE id_equipo=11 AND ci_jugador='11111112'", "eliminelo")

    def test_reemplazar_jugador_por_update(self):
        """CP-PLA-38 | Reemplazar a un jugador con UPDATE | Cambiar la cédula de una fila del plantel con UPDATE | Rechazo: hay que quitarlo y volver a inscribirlo"""
        self.rechaza("UPDATE equipo_jugador_torneo SET ci_jugador=%s WHERE id_equipo=11 AND ci_jugador='11111112'",
                     "eliminelo", (DOCENTE,))

    def test_cambiar_de_equipo_quitando_e_inscribiendo(self):
        """CP-PLA-39 | Cambiar de equipo quitando e inscribiendo | Borrar al jugador del equipo 11 e inscribirlo en el equipo 15 | Se acepta y queda solo en el equipo 15"""
        alta_equipo(self.c)
        self.acepta("DELETE FROM equipo_jugador_torneo WHERE id_equipo=11 AND ci_jugador='11111112'")
        self.acepta(INSCRIBIR, (15, "11111112", 2, 50))
        self.assertEqual(valor(self.c, "SELECT id_equipo FROM equipo_jugador_torneo "
                                       "WHERE ci_jugador='11111112' AND id_torneo=2"), 15)


class AltasSimultaneas(CasoAislado):
    """Equipo 11 con un docente y dos docentes más, sin inscribir, para que los den de alta dos sesiones."""
    def setUp(self):
        super().setUp()
        edicion_prueba(self.c, cerrar_inscripcion=False)
        q(self.c, INSCRIBIR, (11, DOCENTE, 2, 50))
        alta_jugador(self.c, "900000001", "docente")
        alta_jugador(self.c, "900000002", "docente")

    @defecto("REG-20", "Se aceptaron las dos altas: el plantel quedó con 3 docentes o funcionarios.")
    def test_altas_simultaneas_de_docentes(self):
        """CP-PLA-40 | Dos altas simultáneas en el límite de docentes | Con un docente en el plantel, dos sesiones inscriben otro antes de confirmar | Una se rechaza: máximo 2 docentes o funcionarios"""
        primera = conectar(autocommit=False)
        segunda = conectar(autocommit=False)
        self.addCleanup(primera.close)
        self.addCleanup(segunda.close)
        # Si una corrección hace esperar a la segunda sesión, el rechazo llega en 2 segundos.
        q(segunda, "SET SESSION innodb_lock_wait_timeout=2")
        self.acepta(INSCRIBIR, (11, "900000001", 2, 51), conexion=primera)
        intentar(segunda, INSCRIBIR, (11, "900000002", 2, 52))
        primera.commit()
        segunda.commit()
        docentes = valor(self.c, "SELECT COUNT(*) FROM equipo_jugador_torneo e JOIN jugador j ON j.ci=e.ci_jugador "
                                 "WHERE e.id_equipo=11 AND j.tipo IN ('docente','funcionario')")
        self.assertLessEqual(docentes, 2)
