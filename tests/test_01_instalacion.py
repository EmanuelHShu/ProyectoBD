"""Instalación: los scripts corren en orden, se pueden reinstalar y cargan los datos del README."""
from base import (CUENTA_PLANILLERO, ORDEN_SCRIPTS, CasoAislado, CasoTransaccional, conectar, defecto,
                  ejecutar_script, q, valor)

TABLAS = ("login", "facultad", "jugador", "torneo", "equipo", "equipo_jugador_torneo", "complejo", "cancha",
          "turno", "partido", "planilla_partido", "gol", "tarjeta", "sancion_jugador")


def salida(resultado):
    return resultado.stderr.decode("utf-8", "replace")


class Scripts(CasoAislado):
    def correr_scripts(self):
        for nombre in ORDEN_SCRIPTS:
            resultado = ejecutar_script(nombre)
            self.assertEqual(resultado.returncode, 0, f"{nombre}: {salida(resultado)}")

    def filas_por_tabla(self):
        return {tabla: valor(self.c, f"SELECT COUNT(*) FROM torneo_futbol5.{tabla}") for tabla in TABLAS}

    def test_instalacion_desde_cero(self):
        """CP-INS-01 | Instalación completa en un servidor limpio | Borrar base, cuentas y roles y correr los cuatro scripts en orden | Los cuatro terminan sin errores y quedan las 14 tablas"""
        q(self.c, "DROP DATABASE torneo_futbol5")
        q(self.c, "DROP USER 'admin_user'@'localhost','planillero_user'@'localhost','login_user'@'localhost'")
        q(self.c, "DROP ROLE rol_administrador,rol_planillero,rol_login")
        self.correr_scripts()
        self.assertEqual(valor(self.c, "SELECT COUNT(*) FROM information_schema.tables "
                                       "WHERE table_schema='torneo_futbol5' AND table_type='BASE TABLE'"), 14)

    def test_reinstalacion(self):
        """CP-INS-02 | Reinstalación sobre una base ya instalada | Correr otra vez los cuatro scripts en orden | Terminan sin errores y ninguna tabla cambia su cantidad de filas"""
        antes = self.filas_por_tabla()
        self.correr_scripts()
        self.assertEqual(self.filas_por_tabla(), antes)

    def test_reinstalacion_descarta_cambios(self):
        """CP-INS-03 | Reinstalar descarta los datos agregados | Agregar una facultad y correr otra vez los cuatro scripts | La facultad agregada ya no existe"""
        q(self.c, "INSERT INTO facultad (nombre) VALUES ('Agregada')")
        self.correr_scripts()
        self.assertEqual(valor(self.c, "SELECT COUNT(*) FROM torneo_futbol5.facultad WHERE nombre='Agregada'"), 0)

    def test_cuentas_tras_reinstalar(self):
        """CP-INS-04 | Las cuentas de la app funcionan tras reinstalar | Correr otra vez los scripts y conectarse como planillero | Lee los 15 partidos y sigue sin poder leer login"""
        self.correr_scripts()
        planillero = conectar(*CUENTA_PLANILLERO)
        self.addCleanup(planillero.close)
        self.assertEqual(valor(planillero, "SELECT COUNT(*) FROM partido"), 15)
        self.rechaza("SELECT * FROM login", "denied", conexion=planillero)

    def test_roles_antes_de_triggers(self):
        """CP-INS-05 | Los roles dependen de los triggers | Correr creacion-tablas.sql y después seguridad-roles.sql | El script falla porque la vista todavía no existe"""
        self.assertEqual(ejecutar_script("creacion-tablas.sql").returncode, 0)
        resultado = ejecutar_script("seguridad-roles.sql")
        self.assertNotEqual(resultado.returncode, 0)
        self.assertIn("v_resultado_partido", salida(resultado))


class DatosDelReadme(CasoTransaccional):
    def test_equipos(self):
        """CP-INS-06 | Cantidad de equipos cargados | Contar las filas de equipo | 6 equipos"""
        self.assertEqual(valor(self.c, "SELECT COUNT(*) FROM equipo"), 6)

    def test_jugadores(self):
        """CP-INS-07 | Cantidad de jugadores cargados | Contar las filas de jugador | 31 jugadores"""
        self.assertEqual(valor(self.c, "SELECT COUNT(*) FROM jugador"), 31)

    def test_partidos(self):
        """CP-INS-08 | Cantidad de partidos cargados | Contar las filas de partido | 15 partidos"""
        self.assertEqual(valor(self.c, "SELECT COUNT(*) FROM partido"), 15)

    def test_partidos_jugados(self):
        """CP-INS-09 | Cantidad de partidos jugados | Contar los partidos en estado jugado | 9 partidos jugados"""
        self.assertEqual(valor(self.c, "SELECT COUNT(*) FROM partido WHERE estado='jugado'"), 9)

    def test_tres_partidos_por_fecha(self):
        """CP-INS-10 | Partidos por fecha | Agrupar los partidos por número de fecha | 3 partidos en cada fecha, de la 1 a la 5"""
        filas = q(self.c, "SELECT numero_fecha,COUNT(*) AS partidos FROM partido GROUP BY numero_fecha ORDER BY numero_fecha")
        self.assertEqual([(f["numero_fecha"], f["partidos"]) for f in filas], [(n, 3) for n in range(1, 6)])

    def test_ultima_fecha_programada(self):
        """CP-INS-11 | Estado de los partidos 13 a 15 | Consultar el estado de los partidos 13, 14 y 15 | Los tres están programados"""
        filas = q(self.c, "SELECT estado FROM partido WHERE id_partido IN (13,14,15)")
        self.assertEqual([f["estado"] for f in filas], ["programado"] * 3)

    def test_cruces_distintos(self):
        """CP-INS-12 | Liga a una rueda sin cruces repetidos | Contar los pares de equipos sin importar la localía | 15 cruces distintos: todos contra todos"""
        cruces = valor(self.c, "SELECT COUNT(*) FROM (SELECT DISTINCT LEAST(id_equipo_local,id_equipo_visitante) AS a,"
                               "GREATEST(id_equipo_local,id_equipo_visitante) AS b FROM partido) AS cruces")
        self.assertEqual(cruces, 15)

    def test_sin_suspendidos_en_planilla(self):
        """CP-INS-13 | Ningún suspendido firmó planilla en los datos | Cruzar planillas con sanciones por número de fecha | 0 jugadores suspendidos en planilla"""
        suspendidos = valor(self.c, """
            SELECT COUNT(*) FROM planilla_partido pp
            JOIN partido p ON p.id_partido=pp.id_partido
            JOIN sancion_jugador s ON s.ci_jugador=pp.ci_jugador AND s.id_torneo=p.id_torneo
            WHERE p.numero_fecha BETWEEN s.numero_fecha_inicio AND s.numero_fecha_inicio+s.cantidad_fechas-1""")
        self.assertEqual(suspendidos, 0)


class InstalacionSinRoot(CasoAislado):
    """Cuenta con ALL solo sobre torneo_futbol5.*, sin SUPER, y la base con tablas pero sin triggers."""
    CUENTA = ("instalador", "InstaladorPass2026*")

    def setUp(self):
        super().setUp()
        q(self.c, "CREATE USER 'instalador'@'localhost' IDENTIFIED BY %s", (self.CUENTA[1],))
        self.addCleanup(q, self.c, "DROP USER 'instalador'@'localhost'")
        self.addCleanup(q, self.c, "DROP DATABASE IF EXISTS torneo_futbol5")
        q(self.c, "GRANT ALL PRIVILEGES ON torneo_futbol5.* TO 'instalador'@'localhost'")
        resultado = ejecutar_script("creacion-tablas.sql", *self.CUENTA)
        self.assertEqual(resultado.returncode, 0, salida(resultado))

    @defecto("DOC-01", "ERROR 1419 al crear fn_correccion_permitida: la cuenta no tiene SUPER y el binlog está activo.")
    def test_triggers_sin_root(self):
        """CP-INS-14 | Instalar los triggers con una cuenta que no es root | Correr triggers-automaticos.sql con ALL solo sobre torneo_futbol5.* | El script termina sin errores, como afirma el README"""
        resultado = ejecutar_script("triggers-automaticos.sql", *self.CUENTA)
        self.assertEqual(resultado.returncode, 0, salida(resultado))

    def test_triggers_sin_root_con_servidor_que_confia(self):
        """CP-INS-15 | La misma cuenta instala si el servidor lo permite | Activar log_bin_trust_function_creators y correr triggers-automaticos.sql | El script termina sin errores"""
        q(self.c, "SET GLOBAL log_bin_trust_function_creators=1")
        self.addCleanup(q, self.c, "SET GLOBAL log_bin_trust_function_creators=0")
        resultado = ejecutar_script("triggers-automaticos.sql", *self.CUENTA)
        self.assertEqual(resultado.returncode, 0, salida(resultado))
