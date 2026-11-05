"""Esquema de formularios. Las columnas SQL son constantes del servidor, nunca texto del cliente."""
from datetime import date, datetime
import re


def f(name, label, kind="text", *, required=True, options=None, ref=None, maxlen=255, minimum=None):
    return {"name": name, "label": label, "kind": kind, "required": required,
            "options": options or [], "ref": ref, "maxlen": maxlen, "minimum": minimum}


ENTITIES = {
    "facultad": {"title": "Facultades", "pk": ["id_facultad"], "fields": [f("nombre", "Nombre", maxlen=100)]},
    "jugador": {"title": "Jugadores", "pk": ["ci"], "fields": [
        f("ci", "Cédula (sin puntos ni guiones)", maxlen=20), f("nombre", "Nombre", maxlen=100),
        f("apellido", "Apellido", maxlen=100), f("email", "Correo", "email", maxlen=150),
        f("fecha_nacimiento", "Fecha de nacimiento", "date"),
        f("id_facultad", "Facultad", "ref", ref=("facultad", "id_facultad", "nombre")),
        f("tipo", "Tipo", "select", options=["grado", "posgrado", "docente", "funcionario"])]},
    "torneo": {"title": "Ediciones del torneo", "pk": ["id_torneo"], "fields": [
        f("nombre", "Nombre del torneo", maxlen=100), f("anio", "Año", "int", minimum=2020),
        f("semestre", "Semestre", "select", options=["1", "2"]),
        f("fecha_inicio", "Fecha de inicio", "date"), f("fecha_fin", "Fecha de fin", "date"),
        f("estado", "Estado", "select", options=["inscripcion", "en curso", "finalizado"])]},
    "equipo": {"title": "Equipos", "pk": ["id_equipo"], "fields": [
        f("nombre", "Nombre del equipo", maxlen=100),
        f("id_torneo", "Edición", "ref", ref=("torneo", "id_torneo", "nombre")),
        f("id_facultad", "Facultad", "ref", ref=("facultad", "id_facultad", "nombre")),
        f("ci_capitan", "Capitán", "ref", ref=("jugador", "ci", "nombre"))]},
    "equipo_jugador_torneo": {"title": "Planteles", "pk": ["id_equipo", "ci_jugador", "id_torneo"], "fields": [
        f("id_equipo", "Equipo", "ref", ref=("equipo", "id_equipo", "nombre")),
        f("ci_jugador", "Jugador", "ref", ref=("jugador", "ci", "nombre")),
        f("id_torneo", "Edición", "ref", ref=("torneo", "id_torneo", "nombre")),
        f("numero_camiseta", "Camiseta", "int", minimum=1)]},
    "complejo": {"title": "Complejos deportivos", "pk": ["id_complejo"], "fields": [
        f("nombre", "Nombre", maxlen=100), f("direccion", "Dirección", maxlen=150),
        f("departamento", "Departamento", maxlen=100)]},
    "cancha": {"title": "Canchas", "pk": ["nombre_cancha", "id_complejo"], "fields": [
        f("nombre_cancha", "Nombre de cancha", maxlen=100),
        f("id_complejo", "Complejo", "ref", ref=("complejo", "id_complejo", "nombre")),
        f("superficie", "Superficie", "select", options=["sintetico", "parquet"]),
        f("techada", "Techada", "select", options=["1", "0"])]},
    "turno": {"title": "Turnos", "pk": ["id_turno"], "fields": [
        f("hora_inicio", "Comienzo", "time"), f("hora_fin", "Finalización", "time")]},
    "partido": {"title": "Partidos (administración)", "pk": ["id_partido"], "fields": [
        f("id_torneo", "Edición", "ref", ref=("torneo", "id_torneo", "nombre")),
        f("numero_fecha", "Número de fecha", "int", minimum=1),
        f("id_equipo_local", "Equipo local", "ref", ref=("equipo", "id_equipo", "nombre")),
        f("id_equipo_visitante", "Equipo visitante", "ref", ref=("equipo", "id_equipo", "nombre")),
        f("dia", "Día", "date"),
        f("id_turno", "Turno", "ref", ref=("turno", "id_turno", "hora_inicio")),
        f("nombre_cancha", "Cancha", "text", maxlen=100),
        f("id_complejo", "Complejo de la cancha", "ref", ref=("complejo", "id_complejo", "nombre")),
        f("estado", "Estado", "select", options=["programado", "jugado", "postergado", "cancelado"])]},
    "sancion_jugador": {"title": "Sanciones disciplinarias", "pk": ["id_sancion"], "fields": [
        f("ci_jugador", "Jugador", "ref", ref=("jugador", "ci", "nombre")),
        f("id_torneo", "Edición", "ref", ref=("torneo", "id_torneo", "nombre")),
        f("numero_fecha_inicio", "Fecha inicial (número)", "int", minimum=1),
        f("cantidad_fechas", "Duración (fechas)", "int", minimum=1)]},
    "login": {"title": "Usuarios", "pk": ["correo"], "fields": [
        f("correo", "Correo", "email", maxlen=255),
        f("contrasena", "Contraseña", "password", required=False, maxlen=200),
        f("rol", "Rol", "select", options=["administrador", "planillero"])]},
}

# En las altas, los ID autonuméricos son asignados por MySQL.
AUTO_IDS = {"facultad", "torneo", "equipo", "complejo", "turno", "partido", "sancion_jugador"}


def parse_value(field, value, editing=False):
    value = (value or "").strip()
    label = field["label"]
    if not value:
        if field["required"] and not (editing and field["kind"] == "password"):
            raise ValueError(f"El campo «{label}» es obligatorio.")
        return None
    if len(value) > field["maxlen"]:
        raise ValueError(f"«{label}»: máximo {field['maxlen']} caracteres.")
    kind = field["kind"]
    if kind == "email" and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", value):
        raise ValueError(f"«{label}»: correo no válido.")
    if kind == "date":
        try:
            date.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(f"«{label}»: fecha inválida.") from exc
    if kind == "time":
        try:
            datetime.strptime(value, "%H:%M")
        except ValueError as exc:
            raise ValueError(f"«{label}»: formato HH:MM.") from exc
        value += ":00"
    if kind in ("int", "ref") and (kind == "int" or field["ref"][1].startswith("id_")):
        try:
            number = int(value)
        except ValueError as exc:
            raise ValueError(f"«{label}» debe ser un número.") from exc
        if number < (field["minimum"] if field["minimum"] is not None else 1):
            raise ValueError(f"«{label}» está fuera del rango permitido.")
        value = number
    if kind == "select" and value not in field["options"]:
        raise ValueError(f"«{label}»: opción no permitida.")
    return value


def validate_row(entity, submitted, editing=False):
    schema = ENTITIES[entity]
    result = {}
    for field in schema["fields"]:
        if editing and field["name"] in schema["pk"]:
            continue
        v = parse_value(field, submitted.get(field["name"]), editing)
        if field["kind"] == "password" and editing and v is None:
            continue
        result[field["name"]] = v
    if entity == "sancion_jugador":
        result["motivo"] = "disciplinaria"   # Las automáticas solo las generan triggers
    if entity == "torneo" and result.get("fecha_inicio") and result.get("fecha_fin"):
        if result["fecha_inicio"] > result["fecha_fin"]:
            raise ValueError("La fecha de inicio debe ser anterior o igual a la final.")
    if entity == "partido" and result.get("id_equipo_local") == result.get("id_equipo_visitante"):
        raise ValueError("Un equipo no puede enfrentarse consigo mismo.")
    if entity == "equipo_jugador_torneo" and result.get("numero_camiseta", 1) > 99:
        raise ValueError("El dorsal debe estar entre 1 y 99.")
    return result
