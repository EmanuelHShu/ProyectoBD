"""Verificaciones estáticas y de conservación de los scripts del grupo."""
import ast
import hashlib
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
# SHA-256 calculados sobre los archivos originales de ProyectoBD-Branch_Sabri.zip.
ORIGINAL_SQL_SHA256 = {
    'sql/01_esquema.sql': 'ea66e914e59b75c1ec80ca1d4429ca3ac5353ef8b9e3c326fb85af106b2698aa',
    'sql/02_reglas.sql': 'fa0cbd08e9249418c1c7c9077b0d803db6bffa46e0a3bfec78c376330ea57f76',
    'sql/03_datos.sql': '9c3400467b6611a89d53ed4442f3383fd566687cace56466da62a246eb85c472',
    'sql/04_seguridad.sql': 'a29829548ec4d7ce6d0a17a1b01ab69b19164b3e3dc179d60283b88c926b19fb',
    'docs/consultas_originales_sabri.sql': '4bd1ae92e9aca14e98f08a2f425d012743d41acd46848c65d37da098f2ef4d7f',
}


class StructureTests(unittest.TestCase):
    def test_python_parsing(self):
        for script in (ROOT / 'app').glob('*.py'):
            with self.subTest(script=script.name):
                ast.parse(script.read_text(encoding='utf-8'), filename=str(script))

    def test_all_templates_parse(self):
        try:
            from jinja2 import Environment, FileSystemLoader
        except ImportError:
            self.skipTest('jinja2 no disponible')
        templates = ROOT / 'app/templates'
        env = Environment(loader=FileSystemLoader(str(templates)))
        env.filters['show'] = str
        for template in templates.glob('*.html'):
            with self.subTest(template=template.name):
                env.get_template(template.name)

    def test_original_sql_is_intact(self):
        for filename, expected_sha in ORIGINAL_SQL_SHA256.items():
            with self.subTest(file=filename):
                self.assertEqual(hashlib.sha256((ROOT / filename).read_bytes()).hexdigest(), expected_sha)

    def test_no_extra_triggers_or_password_hashes(self):
        rules = (ROOT / 'sql/02_reglas.sql').read_text(encoding='utf-8')
        for added_name in ('trg_equipo_before_insert', 'trg_equipo_before_delete',
                           'trg_jugador_before_update'):
            self.assertNotIn('CREATE TRIGGER ' + added_name, rules)
        seed = (ROOT / 'sql/03_datos.sql').read_text(encoding='utf-8')
        self.assertIn("'pass123'", seed)
        self.assertNotIn('pbkdf2:', seed)
        app = (ROOT / 'app/app.py').read_text(encoding='utf-8')
        self.assertNotIn('hash_password', app)
        self.assertNotIn('verify_password', app)
        self.assertFalse((ROOT / 'app/security.py').exists())

    def test_fixture_requirement_without_changing_original(self):
        a = (ROOT / 'sql/03_datos.sql').read_text(encoding='utf-8')
        b = (ROOT / 'sql/03b_fixture_requerido.sql').read_text(encoding='utf-8')
        rows = []
        for sql in (a, b):
            sections = re.findall(r'INSERT INTO partido\s*\([^;]+;', sql, flags=re.S | re.I)
            for section in sections:
                for f, eq1, eq2, day in re.findall(
                        r"\(\s*\d+,\s*1,\s*(\d+),\s*(\d+),\s*(\d+),\s*'(20\d\d-\d\d-\d\d)'", section):
                    rows.append((int(f), tuple(sorted((int(eq1), int(eq2))))))
        self.assertEqual(len(rows), 15)
        self.assertEqual(len(set(pair for _, pair in rows)), 15)
        self.assertEqual(set(n for n, _ in rows), set(range(1, 6)))

    def test_original_mysql_roles(self):
        security = (ROOT / 'sql/04_seguridad.sql').read_text()
        self.assertIn("'planillero_user'@'localhost'", security)
        self.assertIn('rol_login', security)


if __name__ == '__main__':
    unittest.main()
