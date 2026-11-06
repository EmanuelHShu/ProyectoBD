"""Catálogos de administración: listados, altas, ediciones y bajas de cada entidad por la interfaz."""
import re
from datetime import date, timedelta

from base import (WEB_ADMIN, WEB_PLANILLERO, CasoWeb, alta_partido, avisos, campos_formulario, defecto,
                  edicion_prueba, firmar, q, valor)

CREADO = "Registro creado correctamente."
ACTUALIZADO = "Registro actualizado."
ELIMINADO = "Registro eliminado."
CONFLICTO = "Conflicto de datos"
CON_DEPENDENCIAS = "Cannot delete or update a parent row"
NO_ENCONTRADO = "No se encontró el registro editable."
PLANTEL_CERRADO = "Los planteles solo pueden modificarse mientras el torneo esta en inscripcion."
PLAZO_VENCIDO = "El resultado solo puede corregirse dentro de las 48 horas posteriores al partido."
CARGA_XSS = "<script>alert(1)</script>"

JUGADOR = {"ci": "77777771", "nombre": "Ana", "apellido": "O'Brien", "email": "ana.obrien@correo.com",
           "fecha_nacimiento": "2001-02-03", "id_facultad": "1", "tipo": "grado"}
PLANTEL = {"id_equipo": "11", "ci_jugador": "11111116", "id_torneo": "2", "numero_camiseta": "6"}
USUARIO = {"correo": "nuevo@ucu.edu.uy", "contrasena": "ClaveNueva2026", "rol": "planillero"}


def dentro_de(dias):
    return (date.today() + timedelta(days=dias)).isoformat()


def partido_valido():
    return {"id_torneo": "2", "numero_fecha": "1", "id_equipo_local": "11", "id_equipo_visitante": "12",
            "dia": dentro_de(10), "id_turno": "1", "nombre_cancha": "Cancha 1", "id_complejo": "1",
            "estado": "programado"}


class CasoCatalogo(CasoWeb):
    def setUp(self):
        super().setUp()
        self.admin, _ = self.ingresar(WEB_ADMIN)

    def alta(self, entidad, **datos):
        return self.enviar(self.admin, f"/catalogo/{entidad}/nuevo", datos)

    def editar(self, entidad, slug, **cambios):
        return self.guardar_edicion(self.admin, f"/catalogo/{entidad}/{slug}/editar", **cambios)

    def baja(self, entidad, slug):
        return self.enviar(self.admin, f"/catalogo/{entidad}/{slug}/eliminar")

    def filas(self, entidad):
        return q(self.c, f"SELECT * FROM `{entidad}`")

    def disciplinaria(self):
        return valor(self.c, "SELECT id_sancion FROM sancion_jugador WHERE motivo='disciplinaria'")

    def aviso(self, respuesta, texto):
        mensajes = avisos(respuesta.text)
        self.assertTrue(any(texto in m for m in mensajes), f"Se esperaba «{texto}» y se vio {mensajes}")

    def altas_rechazadas(self, entidad, valido, casos):
        """Envía el alta con cada cambio y comprueba el mensaje y que la tabla no cambió."""
        antes = self.filas(entidad)
        for cambios, mensaje in casos:
            self.aviso(self.alta(entidad, **{**valido, **cambios}), mensaje)
        self.assertEqual(self.filas(entidad), antes)

    def bajas_aceptadas(self, casos):
        for entidad, slug in casos:
            cantidad = len(self.filas(entidad))
            self.aviso(self.baja(entidad, slug), ELIMINADO)
            self.assertEqual(len(self.filas(entidad)), cantidad - 1)

    def bajas_rechazadas(self, casos):
        for entidad, slug, mensaje in casos:
            antes = self.filas(entidad)
            self.aviso(self.baja(entidad, slug), mensaje)
            self.assertEqual(self.filas(entidad), antes)


class Recorrido(CasoCatalogo):
    def recorrer(self, entidad, slug, visible):
        """Lista la entidad, abre el alta y reenvía el formulario de edición sin tocarlo."""
        listado = self.admin.get(f"/catalogo/{entidad}")
        self.assertEqual(listado.status_code, 200)
        self.assertIn(visible, listado.text)
        alta = self.admin.get(f"/catalogo/{entidad}/nuevo")
        self.assertEqual(alta.status_code, 200)
        self.assertIn("Crear registro", alta.text)
        antes = self.filas(entidad)
        respuesta = self.editar(entidad, slug)
        self.assertEqual(self.filas(entidad), antes)
        return respuesta

    def test_facultad(self):
        """CP-CAT-01 | Recorrido de facultades | Listar, abrir el alta y guardar la edición sin cambios | Registro actualizado y datos intactos"""
        self.aviso(self.recorrer("facultad", "1", "Ingenieria"), ACTUALIZADO)

    def test_jugador(self):
        """CP-CAT-02 | Recorrido de jugadores | Listar, abrir el alta y guardar la edición sin cambios | Registro actualizado y datos intactos"""
        self.aviso(self.recorrer("jugador", "11111111", "juan.perez@correo.com"), ACTUALIZADO)

    def test_torneo(self):
        """CP-CAT-03 | Recorrido de ediciones del torneo | Listar, abrir el alta y guardar la edición sin cambios | Registro actualizado y datos intactos"""
        self.aviso(self.recorrer("torneo", "1", "Torneo Interfacultades 2026-2"), ACTUALIZADO)

    def test_equipo(self):
        """CP-CAT-04 | Recorrido de equipos | Listar, abrir el alta y guardar la edición sin cambios | Registro actualizado y datos intactos"""
        self.aviso(self.recorrer("equipo", "1", "Ingenieria FC"), ACTUALIZADO)

    def test_plantel_en_curso(self):
        """CP-CAT-05 | Recorrido de planteles con la edición en curso | Listar, abrir el alta y guardar la edición sin cambios | Rechazo: los planteles solo se modifican en inscripción"""
        self.aviso(self.recorrer("equipo_jugador_torneo", "1~11111111~1", "11111111"), PLANTEL_CERRADO)

    def test_plantel_en_inscripcion(self):
        """CP-CAT-06 | Recorrido de planteles con la edición en inscripción | Listar, abrir el alta y guardar la edición sin cambios | Registro actualizado y datos intactos"""
        edicion_prueba(self.c, cerrar_inscripcion=False)
        self.aviso(self.recorrer("equipo_jugador_torneo", "11~11111111~2", "11111111"), ACTUALIZADO)

    def test_complejo(self):
        """CP-CAT-07 | Recorrido de complejos deportivos | Listar, abrir el alta y guardar la edición sin cambios | Registro actualizado y datos intactos"""
        self.aviso(self.recorrer("complejo", "1", "Av. Italia 2500"), ACTUALIZADO)

    def test_cancha(self):
        """CP-CAT-08 | Recorrido de canchas | Listar, abrir el alta y guardar la edición sin cambios | Registro actualizado y datos intactos"""
        self.aviso(self.recorrer("cancha", "Cancha%201~1", "Cancha 1"), ACTUALIZADO)

    @defecto("APP-02", "Rechazo: «Comienzo»: formato HH:MM, porque el formulario trae la hora como 18:00:00.")
    def test_turno_sin_retipear(self):
        """CP-CAT-09 | Recorrido de turnos | Listar, abrir el alta y guardar la edición sin retipear las horas | Registro actualizado y datos intactos"""
        self.aviso(self.recorrer("turno", "1", "18:00:00"), ACTUALIZADO)

    def test_turno_retipeando(self):
        """CP-CAT-10 | Edición de turno con las horas retipeadas | Guardar el turno con horas en formato HH:MM | Registro actualizado"""
        self.aviso(self.editar("turno", "1", hora_inicio="18:00", hora_fin="19:00"), ACTUALIZADO)

    def test_partido_programado(self):
        """CP-CAT-11 | Recorrido de partidos con uno programado | Listar, abrir el alta y guardar la edición sin cambios | Registro actualizado y datos intactos"""
        self.aviso(self.recorrer("partido", "10", "Cancha 1"), ACTUALIZADO)

    def test_partido_cerrado(self):
        """CP-CAT-12 | Edición de un partido cerrado | Guardar sin cambios un partido jugado con 48 h vencidas | Rechazo: el plazo de corrección terminó"""
        self.aviso(self.recorrer("partido", "1", "Cancha 1"), PLAZO_VENCIDO)

    def test_sancion_disciplinaria(self):
        """CP-CAT-13 | Recorrido de sanciones disciplinarias | Listar, abrir el alta y guardar la edición sin cambios | Registro actualizado y datos intactos"""
        self.aviso(self.recorrer("sancion_jugador", str(self.disciplinaria()), "66666662"), ACTUALIZADO)

    def test_usuario(self):
        """CP-CAT-14 | Recorrido de usuarios | Listar, abrir el alta y guardar la edición con la clave vacía | Registro actualizado y la contraseña se conserva"""
        self.aviso(self.recorrer("login", "admin@ucu.edu.uy", "admin@ucu.edu.uy"), ACTUALIZADO)

    def test_menu_de_gestion(self):
        """CP-CAT-15 | Menú de gestión muestra todas las entidades | Abrir un catálogo como administrador | Aparecen los 11 catálogos"""
        pagina = self.admin.get("/catalogo/jugador").text
        entidades = self.modulo.ENTITIES
        self.assertEqual(len(entidades), 11)
        for entidad in entidades:
            self.assertIn(f'href="/catalogo/{entidad}"', pagina)


class Altas(CasoCatalogo):
    def test_facultad(self):
        """CP-CAT-16 | Alta de facultad válida | Nombre nuevo | Registro creado y visible en el listado"""
        respuesta = self.alta("facultad", nombre="Enfermería")
        self.aviso(respuesta, CREADO)
        self.assertIn("Enfermería", respuesta.text)

    def test_facultad_rechazada(self):
        """CP-CAT-17 | Alta de facultad inválida | Nombre vacío, demasiado largo y repetido | Rechazo con su mensaje y sin registro nuevo"""
        self.altas_rechazadas("facultad", {"nombre": "Enfermería"}, (
            ({"nombre": ""}, "El campo «Nombre» es obligatorio."),
            ({"nombre": "x" * 101}, "«Nombre»: máximo 100 caracteres."),
            ({"nombre": "Ingenieria"}, CONFLICTO)))

    def test_jugador(self):
        """CP-CAT-18 | Alta de jugador válida | Datos completos con apóstrofo en el apellido | Registro creado con el apellido intacto"""
        self.aviso(self.alta("jugador", **JUGADOR), CREADO)
        self.assertEqual(valor(self.c, "SELECT apellido FROM jugador WHERE ci=%s", (JUGADOR["ci"],)), "O'Brien")

    def test_jugador_rechazado(self):
        """CP-CAT-19 | Alta de jugador inválida | Correo, fecha, tipo, facultad, cédula y correo repetidos | Rechazo con su mensaje y sin registro nuevo"""
        self.altas_rechazadas("jugador", JUGADOR, (
            ({"email": "mal"}, "«Correo»: correo no válido."),
            ({"fecha_nacimiento": "03/02/2001"}, "«Fecha de nacimiento»: fecha inválida."),
            ({"tipo": "invitado"}, "«Tipo»: opción no permitida."),
            ({"id_facultad": "abc"}, "«Facultad» debe ser un número."),
            ({"id_facultad": "99"}, CONFLICTO),
            ({"ci": "1" * 21}, "«Cédula (sin puntos ni guiones)»: máximo 20 caracteres."),
            ({"ci": "11111111"}, CONFLICTO),
            ({"email": "juan.perez@correo.com"}, CONFLICTO)))

    def test_torneo(self):
        """CP-CAT-20 | Alta de edición válida | Nombre, año, semestre, fechas y estado | Registro creado"""
        self.aviso(self.alta("torneo", nombre="Torneo 2027", anio="2027", semestre="1", fecha_inicio="2027-03-01",
                             fecha_fin="2027-06-30", estado="inscripcion"), CREADO)
        self.assertEqual(valor(self.c, "SELECT COUNT(*) FROM torneo WHERE anio=2027 AND semestre=1"), 1)

    def test_torneo_rechazado(self):
        """CP-CAT-21 | Alta de edición inválida | Fechas invertidas, año, semestre, estado y edición repetida | Rechazo con su mensaje y sin registro nuevo"""
        valido = {"nombre": "Torneo 2027", "anio": "2027", "semestre": "1", "fecha_inicio": "2027-03-01",
                  "fecha_fin": "2027-06-30", "estado": "inscripcion"}
        self.altas_rechazadas("torneo", valido, (
            ({"fecha_fin": "2027-02-01"}, "La fecha de inicio debe ser anterior o igual a la final."),
            ({"anio": "2019"}, "«Año» está fuera del rango permitido."),
            ({"anio": "dos mil"}, "«Año» debe ser un número."),
            ({"semestre": "3"}, "«Semestre»: opción no permitida."),
            ({"estado": "cerrado"}, "«Estado»: opción no permitida."),
            ({"anio": "2026", "semestre": "2"}, CONFLICTO)))

    def test_equipo(self):
        """CP-CAT-22 | Alta de equipo válida | Equipo nuevo en una edición en inscripción | Registro creado"""
        edicion_prueba(self.c, cerrar_inscripcion=False)
        self.aviso(self.alta("equipo", nombre="Arquitectura B", id_torneo="2", id_facultad="5",
                             ci_capitan="55555551"), CREADO)
        self.assertEqual(valor(self.c, "SELECT COUNT(*) FROM equipo WHERE nombre='Arquitectura B'"), 1)

    def test_equipo_rechazado(self):
        """CP-CAT-23 | Alta de equipo inválida | Nombre vacío o repetido, capitán repetido o inexistente, edición inexistente | Rechazo con su mensaje y sin registro nuevo"""
        valido = {"nombre": "Nuevo", "id_torneo": "1", "id_facultad": "1", "ci_capitan": "11111116"}
        self.altas_rechazadas("equipo", valido, (
            ({"nombre": ""}, "El campo «Nombre del equipo» es obligatorio."),
            ({"nombre": "Ingenieria FC"}, CONFLICTO),
            ({"ci_capitan": "11111111"}, CONFLICTO),
            ({"ci_capitan": "00000000"}, CONFLICTO),
            ({"id_torneo": "99"}, CONFLICTO)))

    def test_plantel(self):
        """CP-CAT-24 | Alta en plantel válida | Jugador de la facultad en una edición en inscripción | Registro creado"""
        edicion_prueba(self.c, cerrar_inscripcion=False)
        self.aviso(self.alta("equipo_jugador_torneo", **PLANTEL), CREADO)
        self.assertEqual(valor(self.c, "SELECT numero_camiseta FROM equipo_jugador_torneo "
                                       "WHERE id_equipo=11 AND ci_jugador='11111116'"), 6)

    def test_plantel_rechazado(self):
        """CP-CAT-25 | Alta en plantel inválida | Dorsal fuera de rango o repetido, otra facultad, jugador repetido | Rechazo con su mensaje y sin registro nuevo"""
        edicion_prueba(self.c, cerrar_inscripcion=False)
        self.altas_rechazadas("equipo_jugador_torneo", PLANTEL, (
            ({"numero_camiseta": "100"}, "El dorsal debe estar entre 1 y 99."),
            ({"numero_camiseta": "0"}, "«Camiseta» está fuera del rango permitido."),
            ({"numero_camiseta": "1"}, CONFLICTO),
            ({"ci_jugador": "55555551"}, "El jugador debe pertenecer a la facultad que representa el equipo."),
            ({"ci_jugador": "11111111"}, CONFLICTO)))

    def test_plantel_con_edicion_en_curso(self):
        """CP-CAT-26 | Alta en plantel con la edición en curso | Jugador válido en una edición ya iniciada | Rechazo: los planteles solo se modifican en inscripción"""
        edicion_prueba(self.c)
        self.altas_rechazadas("equipo_jugador_torneo", PLANTEL, (({}, PLANTEL_CERRADO),))

    def test_complejo(self):
        """CP-CAT-27 | Alta de complejo válida | Nombre, dirección y departamento | Registro creado"""
        self.aviso(self.alta("complejo", nombre="Complejo Sur", direccion="Calle 1", departamento="Maldonado"), CREADO)
        self.assertEqual(valor(self.c, "SELECT departamento FROM complejo WHERE nombre='Complejo Sur'"), "Maldonado")

    def test_complejo_rechazado(self):
        """CP-CAT-28 | Alta de complejo inválida | Nombre repetido, departamento vacío y dirección muy larga | Rechazo con su mensaje y sin registro nuevo"""
        valido = {"nombre": "Complejo Sur", "direccion": "Calle 1", "departamento": "Maldonado"}
        self.altas_rechazadas("complejo", valido, (
            ({"nombre": "Complejo Deportivo Central"}, CONFLICTO),
            ({"departamento": ""}, "El campo «Departamento» es obligatorio."),
            ({"direccion": "x" * 151}, "«Dirección»: máximo 150 caracteres.")))

    def test_cancha(self):
        """CP-CAT-29 | Alta de cancha válida | Nombre nuevo en un complejo existente | Registro creado"""
        self.aviso(self.alta("cancha", nombre_cancha="Cancha 3", id_complejo="1", superficie="parquet", techada="0"), CREADO)
        self.assertEqual(valor(self.c, "SELECT superficie FROM cancha WHERE nombre_cancha='Cancha 3'"), "parquet")

    def test_cancha_rechazada(self):
        """CP-CAT-30 | Alta de cancha inválida | Superficie, techada, complejo inexistente y cancha repetida | Rechazo con su mensaje y sin registro nuevo"""
        valido = {"nombre_cancha": "Cancha 3", "id_complejo": "1", "superficie": "parquet", "techada": "0"}
        self.altas_rechazadas("cancha", valido, (
            ({"superficie": "pasto"}, "«Superficie»: opción no permitida."),
            ({"techada": "2"}, "«Techada»: opción no permitida."),
            ({"id_complejo": "99"}, CONFLICTO),
            ({"nombre_cancha": "Cancha 1"}, CONFLICTO)))

    def test_turno(self):
        """CP-CAT-31 | Alta de turno válida | Una hora dentro de la franja de 18 a 23 | Registro creado"""
        self.aviso(self.alta("turno", hora_inicio="18:30", hora_fin="19:30"), CREADO)
        self.assertEqual(valor(self.c, "SELECT COUNT(*) FROM turno WHERE hora_inicio='18:30:00'"), 1)

    def test_turno_rechazado(self):
        """CP-CAT-32 | Alta de turno inválida | Fuera de franja, dos horas, formato incorrecto y turno repetido | Rechazo con su mensaje y sin registro nuevo"""
        self.altas_rechazadas("turno", {"hora_inicio": "18:30", "hora_fin": "19:30"}, (
            ({"hora_inicio": "10:00", "hora_fin": "11:00"}, "chk_turno_franja"),
            ({"hora_fin": "20:30"}, "chk_turno_duracion"),
            ({"hora_inicio": "18"}, "«Comienzo»: formato HH:MM."),
            ({"hora_inicio": "18:00", "hora_fin": "19:00"}, CONFLICTO)))

    def test_partido(self):
        """CP-CAT-33 | Alta de partido válida | Equipos de la edición con cancha y turno libres | Registro creado como programado"""
        edicion_prueba(self.c)
        self.aviso(self.alta("partido", **partido_valido()), CREADO)
        self.assertEqual(valor(self.c, "SELECT estado FROM partido WHERE id_torneo=2"), "programado")

    def test_partido_rechazado(self):
        """CP-CAT-34 | Alta de partido con datos inválidos | Mismo equipo, fecha, día, estado y cancha inexistente | Rechazo con su mensaje y sin registro nuevo"""
        edicion_prueba(self.c)
        self.altas_rechazadas("partido", partido_valido(), (
            ({"id_equipo_visitante": "11"}, "Un equipo no puede enfrentarse consigo mismo."),
            ({"numero_fecha": "0"}, "«Número de fecha» está fuera del rango permitido."),
            ({"dia": "10/11/2026"}, "«Día»: fecha inválida."),
            ({"estado": "suspendido"}, "«Estado»: opción no permitida."),
            ({"nombre_cancha": "Cancha 9"}, CONFLICTO)))

    def test_partido_rechazado_por_fixture(self):
        """CP-CAT-35 | Alta de partido que choca con el fixture | Rival repetido, equipo con partido en la fecha y cancha ocupada | Rechazo con el mensaje de cada regla"""
        edicion_prueba(self.c)
        valido = partido_valido()
        alta_partido(self.c, 101, 1, 11, 12, valido["dia"])
        self.altas_rechazadas("partido", valido, (
            ({"numero_fecha": "2", "id_turno": "2"}, "Estos equipos ya se enfrentan en esta edicion."),
            ({"id_equipo_visitante": "13", "id_turno": "2"}, "Un equipo ya tiene partido en esa fecha."),
            ({"id_equipo_local": "13", "id_equipo_visitante": "14", "numero_fecha": "2"},
             "La cancha ya tiene un partido en ese dia y turno.")))

    def test_sancion(self):
        """CP-CAT-36 | Alta de sanción siempre es disciplinaria | Jugador del plantel, enviando además el motivo roja | Registro creado como disciplinaria y sin tarjeta"""
        self.aviso(self.alta("sancion_jugador", ci_jugador="11111111", id_torneo="1", numero_fecha_inicio="5",
                             cantidad_fechas="2", motivo="roja"), CREADO)
        self.assertEqual(q(self.c, "SELECT motivo,id_tarjeta FROM sancion_jugador WHERE ci_jugador='11111111'"),
                         [{"motivo": "disciplinaria", "id_tarjeta": None}])

    def test_sancion_rechazada(self):
        """CP-CAT-37 | Alta de sanción inválida | Jugador sin plantel, duración cero y fecha no numérica | Rechazo con su mensaje y sin registro nuevo"""
        valido = {"ci_jugador": "11111111", "id_torneo": "1", "numero_fecha_inicio": "5", "cantidad_fechas": "1"}
        self.altas_rechazadas("sancion_jugador", valido, (
            ({"ci_jugador": "00000000"}, CONFLICTO),
            ({"cantidad_fechas": "0"}, "«Duración (fechas)» está fuera del rango permitido."),
            ({"numero_fecha_inicio": "x"}, "«Fecha inicial (número)» debe ser un número.")))

    def test_usuario(self):
        """CP-CAT-38 | Alta de usuario válida | Correo en mayúsculas, clave de 14 caracteres y rol | Correo guardado en minúsculas y la cuenta puede ingresar"""
        self.aviso(self.alta("login", **{**USUARIO, "correo": "NUEVO@ucu.edu.uy"}), CREADO)
        self.assertEqual(valor(self.c, "SELECT correo FROM login WHERE correo=%s", (USUARIO["correo"],)), USUARIO["correo"])
        _, respuesta = self.ingresar((USUARIO["correo"], USUARIO["contrasena"]))
        self.assertEqual(respuesta.status_code, 302)

    def test_usuario_rechazado(self):
        """CP-CAT-39 | Alta de usuario inválida | Correo mal formado, rol no permitido y correo repetido | Rechazo con su mensaje y sin registro nuevo"""
        self.altas_rechazadas("login", USUARIO, (
            ({"correo": "sin-arroba"}, "«Correo»: correo no válido."),
            ({"rol": "invitado"}, "«Rol»: opción no permitida."),
            ({"correo": "ADMIN@ucu.edu.uy"}, CONFLICTO)))


class Ediciones(CasoCatalogo):
    def test_cambios_guardados(self):
        """CP-CAT-40 | La edición guarda los cambios | Cambiar un campo en ocho catálogos | Registro actualizado con el valor nuevo"""
        sancion = self.disciplinaria()
        casos = (
            ("facultad", "1", "nombre", "Ingeniería", "SELECT nombre FROM facultad WHERE id_facultad=1"),
            ("jugador", "11111111", "email", "juan.p@correo.com", "SELECT email FROM jugador WHERE ci='11111111'"),
            ("torneo", "1", "nombre", "Torneo 2026", "SELECT nombre FROM torneo WHERE id_torneo=1"),
            ("equipo", "1", "nombre", "Ingeniería FC", "SELECT nombre FROM equipo WHERE id_equipo=1"),
            ("complejo", "2", "direccion", "Ruta 8 km 18", "SELECT direccion FROM complejo WHERE id_complejo=2"),
            ("cancha", "Cancha%20B~2", "superficie", "parquet",
             "SELECT superficie FROM cancha WHERE nombre_cancha='Cancha B' AND id_complejo=2"),
            ("partido", "10", "id_turno", "4", "SELECT id_turno FROM partido WHERE id_partido=10"),
            ("sancion_jugador", str(sancion), "cantidad_fechas", "3",
             f"SELECT cantidad_fechas FROM sancion_jugador WHERE id_sancion={sancion}"))
        for entidad, slug, campo, nuevo, consulta in casos:
            self.aviso(self.editar(entidad, slug, **{campo: nuevo}), ACTUALIZADO)
            self.assertEqual(str(valor(self.c, consulta)), nuevo)

    def test_clave_primaria_no_cambia(self):
        """CP-CAT-41 | La edición no cambia la clave primaria | Enviar otra cédula junto con un nombre nuevo | Cambia el nombre y la cédula sigue igual"""
        self.aviso(self.editar("jugador", "11111111", ci="99999999", nombre="Juan Manuel"), ACTUALIZADO)
        self.assertEqual(valor(self.c, "SELECT nombre FROM jugador WHERE ci='11111111'"), "Juan Manuel")
        self.assertEqual(valor(self.c, "SELECT COUNT(*) FROM jugador WHERE ci='99999999'"), 0)

    def test_edicion_invalida(self):
        """CP-CAT-42 | Edición inválida no altera datos | Correo mal formado, nombre vacío y tipo no permitido | Rechazo con su mensaje y datos intactos"""
        antes = self.filas("jugador")
        self.aviso(self.editar("jugador", "11111111", email="mal"), "«Correo»: correo no válido.")
        self.aviso(self.editar("jugador", "11111111", nombre=""), "El campo «Nombre» es obligatorio.")
        self.aviso(self.editar("jugador", "11111111", tipo="invitado"), "«Tipo»: opción no permitida.")
        self.assertEqual(self.filas("jugador"), antes)

    def test_registro_inexistente(self):
        """CP-CAT-43 | Editar un registro inexistente da 404 | Cédula sin registro y clave compuesta incompleta | HTTP 404 en ambos casos"""
        for url in ("/catalogo/jugador/00000000/editar", "/catalogo/cancha/Cancha%201/editar"):
            self.assertEqual(self.admin.get(url).status_code, 404)

    def test_cambio_de_contrasena(self):
        """CP-CAT-44 | Cambio de contraseña de un usuario | Editar la cuenta con una clave nueva | Ingresa con la nueva y ya no con la anterior"""
        nueva = "ClaveCambiada2026"
        self.aviso(self.editar("login", WEB_PLANILLERO[0], contrasena=nueva), ACTUALIZADO)
        _, con_la_nueva = self.ingresar((WEB_PLANILLERO[0], nueva))
        _, con_la_anterior = self.ingresar(WEB_PLANILLERO)
        self.assertEqual(con_la_nueva.status_code, 302)
        self.assertEqual(con_la_anterior.status_code, 200)


class Bajas(CasoCatalogo):
    def test_catalogos_sin_dependencias(self):
        """CP-CAT-45 | Baja de registros sin dependencias | Facultad, jugador, complejo, cancha y turno sin uso | Registro eliminado en cada uno"""
        q(self.c, "INSERT INTO facultad (id_facultad,nombre) VALUES (7,'Temporal')")
        q(self.c, "INSERT INTO jugador (ci,nombre,apellido,email,fecha_nacimiento,id_facultad,tipo) VALUES "
                  "('77777771','Ana','Ruiz','ana.ruiz@correo.com','2001-02-03',1,'grado')")
        q(self.c, "INSERT INTO complejo (id_complejo,nombre,direccion,departamento) VALUES (3,'Temporal','Calle 1','Salto')")
        self.bajas_aceptadas((("facultad", "7"), ("jugador", "77777771"), ("complejo", "3"),
                              ("cancha", "Cancha%202~1"), ("turno", "5")))

    def test_competencia_sin_dependencias(self):
        """CP-CAT-46 | Baja de registros de la competencia | Edición vacía, equipo sin plantel, jugador de plantel, partido, sanción y usuario | Registro eliminado en cada uno"""
        edicion_prueba(self.c, cerrar_inscripcion=False)
        q(self.c, "INSERT INTO torneo (id_torneo,nombre,anio,semestre,fecha_inicio,fecha_fin,estado) VALUES "
                  "(3,'Sin equipos',2028,1,'2028-03-01','2028-06-30','inscripcion')")
        q(self.c, "INSERT INTO equipo (id_equipo,nombre,id_torneo,id_facultad,ci_capitan) VALUES "
                  "(15,'Sin plantel',2,5,'55555551')")
        self.bajas_aceptadas((("torneo", "3"), ("equipo", "15"), ("equipo_jugador_torneo", "11~11111112~2"),
                              ("partido", "15"), ("sancion_jugador", str(self.disciplinaria())),
                              ("login", WEB_PLANILLERO[0])))

    def test_catalogos_con_dependencias(self):
        """CP-CAT-47 | Baja rechazada por integridad en la competencia | Facultad, jugador, edición y equipo en uso | Rechazo por clave foránea y datos intactos"""
        self.bajas_rechazadas((("facultad", "1", CON_DEPENDENCIAS), ("jugador", "11111111", CON_DEPENDENCIAS),
                               ("torneo", "1", CON_DEPENDENCIAS), ("equipo", "1", CON_DEPENDENCIAS)))

    def test_infraestructura_con_dependencias(self):
        """CP-CAT-48 | Baja rechazada por integridad en la infraestructura | Complejo, cancha y turno con partidos | Rechazo por clave foránea y datos intactos"""
        self.bajas_rechazadas((("complejo", "1", CON_DEPENDENCIAS), ("cancha", "Cancha%201~1", CON_DEPENDENCIAS),
                               ("turno", "1", CON_DEPENDENCIAS)))

    def test_partido_jugado(self):
        """CP-CAT-49 | Un partido jugado no se elimina | Baja de un partido jugado | Rechazo con su mensaje y el partido sigue"""
        self.bajas_rechazadas((("partido", "1", "Un partido que ya ha sido jugado no puede ser eliminado del sistema."),))

    def test_plantel_protegido(self):
        """CP-CAT-50 | Baja de plantel protegida | Jugador de una edición en curso y capitán en inscripción | Rechazo con el mensaje de cada regla"""
        edicion_prueba(self.c, cerrar_inscripcion=False)
        self.bajas_rechazadas((("equipo_jugador_torneo", "1~11111112~1", PLANTEL_CERRADO),
                               ("equipo_jugador_torneo", "11~11111111~2", "No se puede quitar al capitan del plantel")))

    def test_baja_inexistente(self):
        """CP-CAT-51 | Baja de un registro inexistente | Identificador sin registro | Aviso de registro no encontrado"""
        self.bajas_rechazadas((("facultad", "999", NO_ENCONTRADO),))


class SancionAutomatica(CasoCatalogo):
    def automatica(self):
        return valor(self.c, "SELECT id_sancion FROM sancion_jugador WHERE motivo='roja'")

    def test_no_se_lista(self):
        """CP-CAT-52 | Sanción automática fuera del listado | Abrir el catálogo de sanciones | Solo aparece la disciplinaria"""
        listado = self.admin.get("/catalogo/sancion_jugador").text
        self.assertIn("66666662", listado)
        self.assertNotIn("66666661", listado)

    def test_no_se_edita(self):
        """CP-CAT-53 | Sanción automática no editable | GET y POST a su edición | HTTP 403 y datos intactos"""
        url = f"/catalogo/sancion_jugador/{self.automatica()}/editar"
        antes = self.filas("sancion_jugador")
        self.assertEqual(self.admin.get(url).status_code, 403)
        datos = {"ci_jugador": "66666661", "id_torneo": "1", "numero_fecha_inicio": "4", "cantidad_fechas": "1"}
        self.assertEqual(self.enviar(self.admin, url, datos).status_code, 403)
        self.assertEqual(self.filas("sancion_jugador"), antes)

    def test_no_se_borra(self):
        """CP-CAT-54 | Sanción automática no borrable | POST a su baja | Aviso de registro no encontrado y la sanción sigue"""
        self.bajas_rechazadas((("sancion_jugador", str(self.automatica()), NO_ENCONTRADO),))


class Contrasenas(CasoCatalogo):
    def test_listado(self):
        """CP-CAT-55 | La contraseña no aparece en el listado | Abrir el catálogo de usuarios | Se ven los correos, sin columna ni valor de la clave"""
        listado = self.admin.get("/catalogo/login").text
        self.assertIn(WEB_ADMIN[0], listado)
        self.assertNotIn("contrasena", listado)
        self.assertNotIn(WEB_ADMIN[1], listado)

    def test_formulario_de_edicion(self):
        """CP-CAT-56 | La contraseña no aparece al editar | Abrir la edición de un usuario | El campo de la clave viene vacío"""
        pagina = self.admin.get("/catalogo/login/admin@ucu.edu.uy/editar").text
        self.assertEqual(campos_formulario(pagina)["contrasena"], "")
        self.assertNotIn(WEB_ADMIN[1], pagina)

    def test_alta_rechazada(self):
        """CP-CAT-57 | La clave escrita no vuelve tras un error | Alta de usuario con correo inválido | El formulario reaparece sin la contraseña"""
        respuesta = self.alta("login", **{**USUARIO, "correo": "sin-arroba"})
        self.aviso(respuesta, "«Correo»: correo no válido.")
        self.assertNotIn(USUARIO["contrasena"], respuesta.text)


class EntradasMaliciosas(CasoCatalogo):
    def test_script_guardado(self):
        """CP-CAT-58 | Nombre con etiqueta script sale escapado | Abrir listado, edición, alta de equipo y planilla | El texto se muestra escapado en todas"""
        q(self.c, "UPDATE jugador SET nombre=%s WHERE ci='11111111'", (CARGA_XSS,))
        for url in ("/catalogo/jugador", "/catalogo/jugador/11111111/editar", "/catalogo/equipo/nuevo", "/partidos/1"):
            pagina = self.admin.get(url).text
            self.assertNotIn(CARGA_XSS, pagina)
            self.assertIn("&lt;script&gt;", pagina)

    def test_script_en_mensaje_de_error(self):
        """CP-CAT-59 | Etiqueta script reflejada en un error sale escapada | Repetir el alta de una facultad con ese nombre | Aviso y formulario con el texto escapado"""
        self.aviso(self.alta("facultad", nombre=CARGA_XSS), CREADO)
        respuesta = self.alta("facultad", nombre=CARGA_XSS)
        self.aviso(respuesta, CONFLICTO)
        self.assertNotIn(CARGA_XSS, respuesta.text)
        self.assertIn("&lt;script&gt;", respuesta.text)

    def test_tabla_y_clave_no_permitidas(self):
        """CP-CAT-60 | Tabla fuera del catálogo y clave con SQL dan 404 | Abrir /catalogo/gol y una clave con comillas | HTTP 404 en ambos casos"""
        for url in ("/catalogo/gol", "/catalogo/jugador/%27%20OR%20%271%27%3D%271/editar"):
            self.assertEqual(self.admin.get(url).status_code, 404)


class DefectosDeCatalogos(CasoCatalogo):
    @defecto("APP-06", "Conflicto de datos: Column 'contrasena' cannot be null; la validación propia no corrió.")
    def test_usuario_sin_contrasena(self):
        """CP-CAT-61 | Alta de usuario sin contraseña da mensaje propio | Correo y rol válidos con la clave vacía | Rechazo: la contraseña es obligatoria al crear un usuario"""
        self.aviso(self.alta("login", **{**USUARIO, "contrasena": ""}), "La contraseña es obligatoria al crear un usuario.")

    @defecto("APP-06", "Se aceptó: quedó guardada una clave de 3 caracteres aunque el formulario pide al menos 10.")
    def test_usuario_con_clave_corta(self):
        """CP-CAT-62 | Contraseña corta se rechaza al crear un usuario | Clave de 3 caracteres | Rechazo: mínimo de 10 caracteres"""
        self.alta("login", **{**USUARIO, "contrasena": "abc"})
        self.assertEqual(valor(self.c, "SELECT COUNT(*) FROM login WHERE correo=%s", (USUARIO["correo"],)), 0)

    @defecto("APP-07", "Usuario o contraseña incorrectos: la clave se guardó sin el espacio final.")
    def test_clave_con_espacio_final(self):
        """CP-CAT-63 | Contraseña con espacio final permite ingresar | Crear el usuario e ingresar escribiendo la misma clave | Ingreso correcto"""
        clave = "clave-segura-1 "
        self.alta("login", **{**USUARIO, "contrasena": clave})
        _, respuesta = self.ingresar((USUARIO["correo"], clave))
        self.assertEqual(respuesta.status_code, 302)

    @defecto("APP-09", "La cédula aparece vacía en el formulario después del error.")
    def test_clave_visible_tras_error(self):
        """CP-CAT-64 | La clave sigue visible tras un error al editar | Editar un jugador con un correo ya usado | Aviso de error y la cédula sigue en el formulario"""
        respuesta = self.editar("jugador", "11111111", email="carlos.gomez@correo.com")
        self.aviso(respuesta, CONFLICTO)
        cedula = re.search(r'<input id="f_ci" value="([^"]*)" disabled', respuesta.text).group(1)
        self.assertEqual(cedula, "11111111")

    @defecto("APP-10", "Error 404: el ~ del nombre parte la clave y la edición no abre.")
    def test_cancha_con_virgulilla(self):
        """CP-CAT-65 | Cancha con ~ en el nombre se puede editar | Crear la cancha y abrir su enlace Editar | El formulario abre con HTTP 200"""
        self.alta("cancha", nombre_cancha="Cancha ~ X", id_complejo="1", superficie="parquet", techada="1")
        listado = self.admin.get("/catalogo/cancha").text
        enlace = re.search(r'href="(/catalogo/cancha/[^"]*~[^"]*~1/editar)"', listado).group(1)
        self.assertEqual(self.admin.get(enlace).status_code, 200)

    @defecto("APP-10", "Error 404: el ~ de la cédula parte la clave y el jugador no se puede quitar.")
    def test_jugador_con_virgulilla(self):
        """CP-CAT-66 | Jugador con ~ en la cédula se puede quitar | Baja del jugador desde el catálogo | Registro eliminado"""
        q(self.c, "INSERT INTO jugador (ci,nombre,apellido,email,fecha_nacimiento,id_facultad,tipo) VALUES "
                  "('12~34','Ana','Ruiz','ana.ruiz@correo.com','2001-02-03',1,'grado')")
        self.aviso(self.baja("jugador", "12~34"), ELIMINADO)

    @defecto("APP-10", "Error 404: la / de la cédula no coincide con la ruta y el jugador sigue en la planilla.")
    def test_cedula_con_barra_en_planilla(self):
        """CP-CAT-67 | Jugador con / en la cédula se quita de la planilla | Usar Quitar sobre ese jugador como planillero | El jugador sale de la planilla"""
        q(self.c, "INSERT INTO jugador (ci,nombre,apellido,email,fecha_nacimiento,id_facultad,tipo) VALUES "
                  "('12/34','Ana','Ruiz','ana.ruiz@correo.com','2001-02-03',1,'grado')")
        edicion_prueba(self.c, cerrar_inscripcion=False)
        q(self.c, "INSERT INTO equipo_jugador_torneo (id_equipo,ci_jugador,id_torneo,numero_camiseta) "
                  "VALUES (11,'12/34',2,6)")
        q(self.c, "UPDATE torneo SET estado='en curso' WHERE id_torneo=2")
        alta_partido(self.c, 101, 1, 11, 12, dentro_de(-1))
        firmar(self.c, 101, 11, ["12/34"])
        planillero, _ = self.ingresar(WEB_PLANILLERO)
        pagina = planillero.get("/partidos/101").text
        self.enviar(planillero, re.search(r'action="(/partidos/101/planilla/[^"]+/borrar)"', pagina).group(1))
        self.assertEqual(valor(self.c, "SELECT COUNT(*) FROM planilla_partido WHERE id_partido=101"), 0)

    @defecto("APP-11", "Se aceptó: el jugador quedó registrado con la cédula 1.234.567-8.")
    def test_cedula_con_puntos(self):
        """CP-CAT-68 | Cédula con puntos y guion se rechaza | Alta de jugador con cédula 1.234.567-8 | Rechazo: la cédula va sin puntos ni guiones"""
        self.alta("jugador", **{**JUGADOR, "ci": "1.234.567-8"})
        self.assertEqual(valor(self.c, "SELECT COUNT(*) FROM jugador WHERE ci='1.234.567-8'"), 0)

    @defecto("APP-11", "Se aceptó: el jugador quedó registrado con fecha de nacimiento futura.")
    def test_nacimiento_futuro(self):
        """CP-CAT-69 | Fecha de nacimiento futura se rechaza | Alta de jugador nacido dentro de un año | Rechazo por fecha inválida"""
        self.alta("jugador", **{**JUGADOR, "fecha_nacimiento": dentro_de(365)})
        self.assertEqual(valor(self.c, "SELECT COUNT(*) FROM jugador WHERE ci=%s", (JUGADOR["ci"],)), 0)
