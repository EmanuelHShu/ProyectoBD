"""Sistema UCU Torneo Interfacultades Fútbol 5 (Flask + PyMySQL, sin ORM)."""
import os
import secrets
from datetime import date, datetime, time
from functools import wraps

from dotenv import load_dotenv
load_dotenv()
from flask import (Flask, abort, flash, g, redirect, render_template, request,
                   session, url_for)
from pymysql import MySQLError, IntegrityError

from db import db, one, query, transaction
from models import ENTITIES, AUTO_IDS, parse_value, validate_row
from reports import REPORTS

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.getenv("APP_SECRET_KEY") or secrets.token_hex(32),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.getenv("COOKIE_SECURE", "false").lower() == "true",
    PERMANENT_SESSION_LIFETIME=60 * 60 * 8,
    MAX_CONTENT_LENGTH=1024 * 1024,
)


@app.template_filter("show")
def show(value):
    if value is None:
        return "—"
    if isinstance(value, datetime):
        return value.strftime("%d/%m/%Y %H:%M")
    if isinstance(value, date):
        return value.strftime("%d/%m/%Y")
    if isinstance(value, time):
        return value.strftime("%H:%M")
    if isinstance(value, bytes):
        return value.decode("utf-8", "replace")
    return str(value)


@app.context_processor
def template_helpers():
    return {"csrf_token": lambda: session.setdefault("csrf", secrets.token_urlsafe(32)),
            "logged_user": g.get("user"), "entity_menu": ENTITIES,
            "as_str": lambda x: x.strftime("%Y-%m-%d") if isinstance(x, date) else str(x) if x is not None else ""}


@app.before_request
def session_guard():
    g.user = session.get("user")
    # Revalidar el rol de usuarios autenticados para evitar sesiones obsoletas
    # si un administrador cambia permisos o elimina una cuenta.
    if g.user:
        try:
            actual = one("login", "SELECT rol FROM login WHERE correo=%s", (g.user["correo"],))
            if actual is None:
                session.clear()
                g.user = None
            elif actual["rol"] != g.user["rol"]:
                session["user"] = {"correo": g.user["correo"], "rol": actual["rol"]}
                g.user = session["user"]
        except (MySQLError, KeyError):
            # No conservar privilegios de una sesión sin verificar si la BD cayó.
            session.clear()
            g.user = None
    # Estado del cliente no concede privilegios: la conexión MySQL usa un usuario
    # con GRANTs restringidos, además de verificar el rol en cada ruta.
    if request.method == "POST":
        received = request.form.get("csrf_token", "")
        expected = session.get("csrf", "")
        if not expected or not secrets.compare_digest(received, expected):
            abort(400, description="Formulario vencido; recargue la página e intente otra vez.")


def requires_login(fn):
    @wraps(fn)
    def inner(*a, **kw):
        if not g.user:
            return redirect(url_for("login"))
        return fn(*a, **kw)
    return inner


def requires_admin(fn):
    @wraps(fn)
    @requires_login
    def inner(*a, **kw):
        if g.user["rol"] != "administrador":
            abort(403)
        return fn(*a, **kw)
    return inner


def role():
    return g.user["rol"]


def sql_error(exc):
    if isinstance(exc, IntegrityError):
        return "Conflicto de datos: revise duplicados, claves foráneas y registros relacionados. " + str(exc.args[-1])[:280]
    if isinstance(exc, MySQLError):
        msg = str(exc.args[-1])[:280] if exc.args else ""
        return "MySQL rechazó la operación: " + msg
    if isinstance(exc, ValueError):
        return str(exc)
    app.logger.exception("Error inesperado")
    return "Error inesperado; consulte el registro del servidor."


@app.route("/login", methods=["GET", "POST"])
def login():
    if g.user:
        return redirect(url_for("home"))
    if request.method == "POST":
        correo = request.form.get("correo", "").strip().lower()
        password = request.form.get("password", "")
        try:
            found = one("login", "SELECT correo, contrasena, rol FROM login WHERE correo=%s", (correo,))
        except (MySQLError, KeyError) as exc:
            flash("No se pudo conectar a MySQL. Revise la instalación y el archivo .env.", "error")
            app.logger.warning("Fallo conectando a login: %s", type(exc).__name__)
            return render_template("login.html")
        if found and secrets.compare_digest(found["contrasena"], password):
            session.clear()
            session["user"] = {"correo": found["correo"], "rol": found["rol"]}
            session["csrf"] = secrets.token_urlsafe(32)
            session.permanent = True
            return redirect(url_for("home"))
        flash("Usuario o contraseña incorrectos.", "error")
    return render_template("login.html")


@app.route("/logout", methods=["POST"])
@requires_login
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
@requires_login
def home():
    try:
        torneos = query(role(), "SELECT id_torneo,nombre,anio,semestre,estado FROM torneo ORDER BY anio DESC,semestre DESC")
        stats = one(role(), """SELECT (SELECT COUNT(*) FROM equipo) AS equipos,
                   (SELECT COUNT(*) FROM jugador) AS jugadores,
                   (SELECT COUNT(*) FROM partido) AS partidos,
                   (SELECT COUNT(*) FROM partido WHERE estado='jugado') AS jugados""")
    except (MySQLError, KeyError) as exc:
        flash(sql_error(exc), "error")
        torneos, stats = [], {}
    return render_template("home.html", torneos=torneos, stats=stats)


def key_tuple(schema, slug):
    parts = slug.split("~")
    if len(parts) != len(schema["pk"]):
        abort(404)
    return tuple(parts)


def where_pk(schema):
    return " AND ".join("`" + n + "`=%s" for n in schema["pk"])


def make_slug(row, schema):
    return "~".join(str(row[name]) for name in schema["pk"])


def ref_choices(schema):
    result = {}
    for field in schema["fields"]:
        if field["kind"] != "ref":
            continue
        table, key, label = field["ref"]
        if table == "jugador":
            sql = "SELECT ci AS k, CONCAT(ci,' - ',nombre,' ',apellido) AS label FROM jugador ORDER BY apellido,nombre"
        elif table == "turno":
            sql = "SELECT id_turno AS k, CONCAT(hora_inicio,' / ',hora_fin) AS label FROM turno ORDER BY hora_inicio"
        elif table == "torneo":
            sql = "SELECT id_torneo AS k, CONCAT(nombre,' (',anio,'-',semestre,')') AS label FROM torneo ORDER BY anio DESC,semestre DESC"
        else:
            sql = f"SELECT `{key}` AS k, `{label}` AS label FROM `{table}` ORDER BY `{label}`"
        result[field["name"]] = query(role(), sql)
    return result


@app.route("/catalogo/<entity>")
@requires_admin
def catalog(entity):
    schema = ENTITIES.get(entity)
    if not schema:
        abort(404)
    # Conjunto explícito permitido; nunca se usan nombres de tabla del cliente sin whitelist.
    try:
        rows = query(role(), f"SELECT * FROM `{entity}` ORDER BY " + ",".join("`" + k + "`" for k in schema["pk"]) + " LIMIT 500")
    except MySQLError as exc:
        flash(sql_error(exc), "error")
        rows = []
    if entity == "login":
        rows = [{k: v for k, v in row.items() if k != "contrasena"} for row in rows]
    if entity == "sancion_jugador":
        rows = [r for r in rows if r["motivo"] == "disciplinaria"]
    return render_template("catalog.html", entity=entity, schema=schema, rows=rows,
                           slugs=[make_slug(row, schema) for row in rows])


def persist(entity, schema, editing=False, slug=None):
    values = validate_row(entity, request.form, editing)
    if entity == "login":
        if "correo" in values:
            values["correo"] = values["correo"].lower()
        if not editing and "contrasena" not in values:
            raise ValueError("La contraseña es obligatoria al crear un usuario.")
    if entity == "sancion_jugador" and editing:
        # Prohíbe editar sanciones automáticas; el SQL también usa FK a tarjetas.
        old = one(role(), "SELECT motivo FROM sancion_jugador WHERE id_sancion=%s", key_tuple(schema, slug))
        if not old or old["motivo"] != "disciplinaria":
            raise ValueError("Solo se modifican sanciones disciplinarias manuales.")
    if editing:
        if not values:
            raise ValueError("No hay campos editables.")
        updates = ", ".join(f"`{k}`=%s" for k in values)
        sql = f"UPDATE `{entity}` SET {updates} WHERE {where_pk(schema)}"
        args = list(values.values()) + list(key_tuple(schema, slug))
    else:
        columns = ",".join("`" + k + "`" for k in values)
        placeholders = ",".join("%s" for _ in values)
        sql = f"INSERT INTO `{entity}` ({columns}) VALUES ({placeholders})"
        args = list(values.values())
    with transaction(role()) as conn, conn.cursor() as cursor:
        cursor.execute(sql, args)
        if editing and cursor.rowcount == 0:
            # MySQL también retorna 0 si los datos se repiten: no es necesariamente error.
            pass


@app.route("/catalogo/<entity>/nuevo", methods=["GET", "POST"])
@requires_admin
def create_entity(entity):
    schema = ENTITIES.get(entity)
    if not schema:
        abort(404)
    if request.method == "POST":
        try:
            persist(entity, schema)
            flash("Registro creado correctamente.", "ok")
            return redirect(url_for("catalog", entity=entity))
        except (ValueError, MySQLError) as exc:
            flash(sql_error(exc), "error")
    try:
        options = ref_choices(schema)
    except MySQLError as exc:
        flash(sql_error(exc), "error")
        options = {}
    return render_template("entity_form.html", entity=entity, schema=schema, row=request.form,
                           editing=False, options=options)


@app.route("/catalogo/<entity>/<path:slug>/editar", methods=["GET", "POST"])
@requires_admin
def edit_entity(entity, slug):
    schema = ENTITIES.get(entity)
    if not schema:
        abort(404)
    pk = key_tuple(schema, slug)
    existing = one(role(), f"SELECT * FROM `{entity}` WHERE {where_pk(schema)}", pk)
    if not existing:
        abort(404)
    if entity == "sancion_jugador" and existing["motivo"] != "disciplinaria":
        abort(403)
    if request.method == "POST":
        try:
            persist(entity, schema, editing=True, slug=slug)
            flash("Registro actualizado.", "ok")
            return redirect(url_for("catalog", entity=entity))
        except (ValueError, MySQLError) as exc:
            flash(sql_error(exc), "error")
    try:
        options = ref_choices(schema)
    except MySQLError as exc:
        flash(sql_error(exc), "error")
        options = {}
    return render_template("entity_form.html", entity=entity, schema=schema,
                           row=request.form if request.method == "POST" else existing,
                           editing=True, options=options, slug=slug)


@app.route("/catalogo/<entity>/<path:slug>/eliminar", methods=["POST"])
@requires_admin
def delete_entity(entity, slug):
    schema = ENTITIES.get(entity)
    if not schema:
        abort(404)
    try:
        with transaction(role()) as conn, conn.cursor() as cursor:
            sql = f"DELETE FROM `{entity}` WHERE {where_pk(schema)}"
            vals = list(key_tuple(schema, slug))
            if entity == "sancion_jugador":
                sql += " AND motivo='disciplinaria' AND id_tarjeta IS NULL"
            cursor.execute(sql, vals)
            if cursor.rowcount == 0:
                raise ValueError("No se encontró el registro editable.")
        flash("Registro eliminado.", "ok")
    except (ValueError, MySQLError) as exc:
        flash(sql_error(exc), "error")
    return redirect(url_for("catalog", entity=entity))


@app.route("/partidos")
@requires_login
def matches():
    editions = query(role(), "SELECT id_torneo,nombre,anio,semestre FROM torneo ORDER BY anio DESC,semestre DESC")
    chosen = request.args.get("torneo", type=int)
    if chosen is None and editions:
        chosen = editions[0]["id_torneo"]
    rows = query(role(), """
       SELECT p.id_partido,p.numero_fecha,p.dia,t.hora_inicio,t.hora_fin,
       l.nombre AS local,v.nombre AS visitante,p.estado,c.nombre AS complejo,p.nombre_cancha AS cancha,
       r.goles_local,r.goles_visitante
       FROM partido p JOIN equipo l ON l.id_equipo=p.id_equipo_local
       JOIN equipo v ON v.id_equipo=p.id_equipo_visitante
       JOIN complejo c ON c.id_complejo=p.id_complejo JOIN turno t ON t.id_turno=p.id_turno
       LEFT JOIN v_resultado_partido r ON r.id_partido=p.id_partido
       WHERE p.id_torneo=%s ORDER BY p.numero_fecha,p.dia,t.hora_inicio,p.id_partido
    """, (chosen,)) if chosen else []
    return render_template("matches.html", editions=editions, chosen=chosen, rows=rows)


def match_detail(id_partido):
    match = one(role(), """
        SELECT p.*,l.nombre AS local,v.nombre AS visitante,t.hora_inicio,t.hora_fin,
        r.goles_local,r.goles_visitante
        FROM partido p JOIN equipo l ON l.id_equipo=p.id_equipo_local
        JOIN equipo v ON v.id_equipo=p.id_equipo_visitante JOIN turno t ON t.id_turno=p.id_turno
        JOIN v_resultado_partido r ON r.id_partido=p.id_partido
        WHERE p.id_partido=%s""", (id_partido,))
    if not match:
        abort(404)
    return match


@app.route("/partidos/<int:id_partido>")
@requires_login
def match_view(id_partido):
    match = match_detail(id_partido)
    players = query(role(), """
      SELECT ej.ci_jugador,CONCAT(j.apellido,', ',j.nombre) AS jugador,
      ej.id_equipo,ej.numero_camiseta,
      CASE WHEN EXISTS (SELECT 1 FROM sancion_jugador s WHERE s.ci_jugador=ej.ci_jugador
       AND s.id_torneo=ej.id_torneo AND %s BETWEEN s.numero_fecha_inicio
       AND s.numero_fecha_inicio+s.cantidad_fechas-1) THEN 1 ELSE 0 END AS suspendido,
      CASE WHEN pl.id_partido IS NULL THEN 0 ELSE 1 END AS participo
      FROM equipo_jugador_torneo ej JOIN jugador j ON j.ci=ej.ci_jugador
      LEFT JOIN planilla_partido pl ON pl.id_partido=%s AND pl.ci_jugador=ej.ci_jugador
      WHERE ej.id_equipo IN (%s,%s) AND ej.id_torneo=%s
      ORDER BY ej.id_equipo,ej.numero_camiseta""",
      (match["numero_fecha"], id_partido, match["id_equipo_local"], match["id_equipo_visitante"], match["id_torneo"]))
    lineup = [p for p in players if p["participo"]]
    goals = query(role(), """SELECT g.*,CONCAT(j.nombre,' ',j.apellido) AS jugador FROM gol g
           JOIN jugador j ON j.ci=g.ci_jugador WHERE g.id_partido=%s ORDER BY minuto,id_gol""", (id_partido,))
    cards = query(role(), """SELECT t.*,CONCAT(j.nombre,' ',j.apellido) AS jugador FROM tarjeta t
           JOIN jugador j ON j.ci=t.ci_jugador WHERE t.id_partido=%s ORDER BY minuto,id_tarjeta""", (id_partido,))
    # La BD impide correcciones posteriores a 48 horas. La UI refleja esa limitación.
    end = datetime.combine(match["dia"], (datetime.min + match["hora_fin"]).time()) if not isinstance(match["hora_fin"], time) else datetime.combine(match["dia"], match["hora_fin"])
    from datetime import timedelta
    can_edit = (match["estado"] in ("programado", "jugado")
                and datetime.now() >= end
                and (match["estado"] == "programado" or datetime.now() <= end + timedelta(hours=48)))
    return render_template("match_detail.html", match=match, players=players, lineup=lineup,
                           goals=goals, cards=cards, can_edit=can_edit)


def require_writable_match(match):
    if match["estado"] not in ("programado", "jugado"):
        raise ValueError("Solo se registran datos de partidos programados o jugados.")
    end_dt = datetime.combine(match["dia"], time(0)) + match["hora_fin"] if hasattr(match["hora_fin"], "total_seconds") else datetime.combine(match["dia"], match["hora_fin"])
    from datetime import timedelta
    if datetime.now() < end_dt:
        raise ValueError("La planilla de juego solo se registra una vez terminado el turno.")
    if match["estado"] == "jugado" and datetime.now() > end_dt + timedelta(hours=48):
        raise ValueError("La ventana de 48 horas para correcciones terminó.")


@app.route("/partidos/<int:id_partido>/planilla", methods=["POST"])
@requires_login
def add_lineup(id_partido):
    try:
        match = match_detail(id_partido)
        require_writable_match(match)
        ci = request.form.get("ci", "")
        team = request.form.get("equipo", "")
        if not ci or not team.isdigit():
            raise ValueError("Seleccione un jugador y equipo válidos.")
        with transaction(role()) as conn, conn.cursor() as cursor:
            cursor.execute("INSERT INTO planilla_partido (id_partido,ci_jugador,id_equipo) VALUES (%s,%s,%s)",
                           (id_partido, ci, int(team)))
        flash("Jugador añadido a la planilla.", "ok")
    except (ValueError, MySQLError) as exc:
        flash(sql_error(exc), "error")
    return redirect(url_for("match_view", id_partido=id_partido))


@app.route("/partidos/<int:id_partido>/planilla/<ci>/borrar", methods=["POST"])
@requires_login
def delete_lineup(id_partido, ci):
    try:
        require_writable_match(match_detail(id_partido))
        with transaction(role()) as conn, conn.cursor() as cursor:
            # El comportamiento de esta operación lo determina el SQL original de Sabrina.
            cursor.execute("DELETE FROM planilla_partido WHERE id_partido=%s AND ci_jugador=%s", (id_partido, ci))
        flash("Jugador retirado de planilla.", "ok")
    except (ValueError, MySQLError) as exc:
        flash(sql_error(exc), "error")
    return redirect(url_for("match_view", id_partido=id_partido))


def event_values(kind, data):
    ci = (data.get("ci_jugador") or "").strip()
    if not ci or len(ci) > 20:
        raise ValueError("Seleccione un jugador de la planilla.")
    try:
        minute = int(data.get("minuto", ""))
    except ValueError as exc:
        raise ValueError("Ingrese un minuto válido.") from exc
    if not 0 <= minute <= 120:
        raise ValueError("El minuto debe estar entre 0 y 120.")
    if kind == "gol":
        autogol = data.get("autogol", "0")
        if autogol not in ("0", "1"):
            raise ValueError("Autogol: valor no válido.")
        return (ci, minute, int(autogol))
    color = data.get("color", "")
    if color not in ("amarilla", "roja"):
        raise ValueError("Color de tarjeta inválido.")
    return (ci, minute, color)


@app.route("/partidos/<int:id_partido>/<kind>", methods=["POST"])
@requires_login
def add_event(id_partido, kind):
    if kind not in ("gol", "tarjeta"):
        abort(404)
    try:
        require_writable_match(match_detail(id_partido))
        ci, minute, extra = event_values(kind, request.form)
        column = "autogol" if kind == "gol" else "color"
        with transaction(role()) as conn, conn.cursor() as cursor:
            cursor.execute(f"INSERT INTO `{kind}` (id_partido,ci_jugador,minuto,{column}) VALUES (%s,%s,%s,%s)",
                           (id_partido, ci, minute, extra))
        flash("Evento registrado correctamente.", "ok")
    except (ValueError, MySQLError) as exc:
        flash(sql_error(exc), "error")
    return redirect(url_for("match_view", id_partido=id_partido))


@app.route("/partidos/<int:id_partido>/<kind>/<int:event_id>/editar", methods=["POST"])
@requires_login
def edit_event(id_partido, kind, event_id):
    if kind not in ("gol", "tarjeta"):
        abort(404)
    pk = "id_gol" if kind == "gol" else "id_tarjeta"
    try:
        require_writable_match(match_detail(id_partido))
        ci, minute, extra = event_values(kind, request.form)
        column = "autogol" if kind == "gol" else "color"
        with transaction(role()) as conn, conn.cursor() as cursor:
            cursor.execute(f"UPDATE `{kind}` SET ci_jugador=%s,minuto=%s,`{column}`=%s WHERE {pk}=%s AND id_partido=%s",
                           (ci, minute, extra, event_id, id_partido))
        flash("Evento actualizado.", "ok")
    except (ValueError, MySQLError) as exc:
        flash(sql_error(exc), "error")
    return redirect(url_for("match_view", id_partido=id_partido))


@app.route("/partidos/<int:id_partido>/<kind>/<int:event_id>/borrar", methods=["POST"])
@requires_login
def delete_event(id_partido, kind, event_id):
    if kind not in ("gol", "tarjeta"):
        abort(404)
    pk = "id_gol" if kind == "gol" else "id_tarjeta"
    try:
        require_writable_match(match_detail(id_partido))
        with transaction(role()) as conn, conn.cursor() as cursor:
            cursor.execute(f"DELETE FROM `{kind}` WHERE {pk}=%s AND id_partido=%s", (event_id, id_partido))
        flash("Evento eliminado.", "ok")
    except (ValueError, MySQLError) as exc:
        flash(sql_error(exc), "error")
    return redirect(url_for("match_view", id_partido=id_partido))


@app.route("/partidos/<int:id_partido>/finalizar", methods=["POST"])
@requires_login
def finish_match(id_partido):
    try:
        match = match_detail(id_partido)
        require_writable_match(match)
        with transaction(role()) as conn, conn.cursor() as cursor:
            # El planillero SOLO puede hacerlo a través del procedimiento autorizado.
            cursor.callproc("sp_marcar_partido_jugado", (id_partido,))
        flash("Partido marcado como jugado. Resultado calculado a partir de los goles.", "ok")
    except (ValueError, MySQLError) as exc:
        flash(sql_error(exc), "error")
    return redirect(url_for("match_view", id_partido=id_partido))


@app.route("/reportes")
@requires_admin
def reports_index():
    editions = query(role(), "SELECT id_torneo,nombre,anio,semestre FROM torneo ORDER BY anio DESC,semestre DESC")
    return render_template("reports.html", reports=REPORTS, editions=editions)


@app.route("/reportes/<slug>")
@requires_admin
def report_detail(slug):
    if slug not in REPORTS:
        abort(404)
    editions = query(role(), "SELECT id_torneo,nombre,anio,semestre FROM torneo ORDER BY anio DESC,semestre DESC")
    tournament = request.args.get("torneo", type=int)
    if tournament is None and editions:
        tournament = editions[0]["id_torneo"]
    fecha = request.args.get("fecha", default=2, type=int)
    fecha = max(1, min(fecha, 127))
    title, description, sql = REPORTS[slug]
    rows = []
    if tournament is not None:
        try:
            rows = query(role(), sql, {"torneo": tournament, "fecha": fecha})
        except MySQLError as exc:
            flash(sql_error(exc), "error")
    return render_template("report_detail.html", slug=slug, title=title,
                           description=description, editions=editions, chosen=tournament,
                           fecha=fecha, rows=rows)


@app.errorhandler(403)
def forbidden(_):
    return render_template("error.html", code=403, message="No tiene permisos para acceder a esta sección."), 403


@app.errorhandler(404)
def missing(_):
    return render_template("error.html", code=404, message="No se encontró la página o el registro."), 404


@app.errorhandler(400)
def invalid(exc):
    return render_template("error.html", code=400, message=exc.description), 400


if __name__ == "__main__":
    app.run(host=os.getenv("APP_HOST", "127.0.0.1"), port=int(os.getenv("APP_PORT", "5000")), debug=False)
