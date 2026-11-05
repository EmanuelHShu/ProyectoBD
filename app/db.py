"""Acceso SQL sin ORM, con cuentas MySQL diferenciadas por rol."""
import os
from contextlib import contextmanager
import pymysql

CONFIG = {
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "database": os.getenv("DB_NAME", "torneo_futbol5"),
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
    "autocommit": False,
    "connect_timeout": 8,
}


def connection(role="login"):
    if role not in {"login", "administrador", "planillero"}:
        raise ValueError("Rol SQL no permitido")
    env = {"login": ("DB_LOGIN_USER", "DB_LOGIN_PASSWORD", "login_user"),
           "administrador": ("DB_ADMIN_USER", "DB_ADMIN_PASSWORD", "admin_user"),
           "planillero": ("DB_PLAN_USER", "DB_PLAN_PASSWORD", "planillero_user")}
    user_key, pass_key, fallback = env[role]
    return pymysql.connect(**CONFIG, user=os.getenv(user_key, fallback),
                           password=os.environ[pass_key])


@contextmanager
def db(role):
    conn = connection(role)
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def transaction(role):
    with db(role) as conn:
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise


def query(role, sql, values=()):
    with db(role) as conn, conn.cursor() as cursor:
        cursor.execute(sql, values)
        return cursor.fetchall()


def one(role, sql, values=()):
    result = query(role, sql, values)
    return result[0] if result else None
