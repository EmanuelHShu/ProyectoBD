"""Comprueba que las pruebas corren aisladas y que la base se instala completa."""
from base import CasoTransaccional, servidor, valor


class Infraestructura(CasoTransaccional):
    def test_servidor_temporal(self):
        """CP-INF-01 | Las pruebas no usan el servidor MySQL instalado | Consultar el puerto de la conexión | El puerto es distinto de 3306 y coincide con el servidor temporal"""
        puerto = valor(self.c, "SELECT @@port")
        self.assertNotEqual(puerto, 3306)
        self.assertEqual(puerto, servidor().puerto)

    def test_objetos_instalados(self):
        """CP-INF-02 | Los scripts crean todos los objetos | Contar tablas, vistas, triggers, funciones y procedimientos | 14 tablas, 1 vista, 20 triggers, 1 función y 2 procedimientos"""
        esquema = "'torneo_futbol5'"
        self.assertEqual(valor(self.c, f"SELECT COUNT(*) FROM information_schema.tables WHERE table_schema={esquema} AND table_type='BASE TABLE'"), 14)
        self.assertEqual(valor(self.c, f"SELECT COUNT(*) FROM information_schema.views WHERE table_schema={esquema}"), 1)
        self.assertEqual(valor(self.c, f"SELECT COUNT(*) FROM information_schema.triggers WHERE trigger_schema={esquema}"), 20)
        self.assertEqual(valor(self.c, f"SELECT COUNT(*) FROM information_schema.routines WHERE routine_schema={esquema} AND routine_type='FUNCTION'"), 1)
        self.assertEqual(valor(self.c, f"SELECT COUNT(*) FROM information_schema.routines WHERE routine_schema={esquema} AND routine_type='PROCEDURE'"), 2)
