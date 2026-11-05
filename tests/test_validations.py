import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))
from models import ENTITIES, validate_row, parse_value
from reports import REPORTS


class ModelValidationTests(unittest.TestCase):
    def test_entities_and_reports(self):
        for name in ("jugador", "equipo", "equipo_jugador_torneo", "complejo", "cancha", "partido", "sancion_jugador"):
            self.assertIn(name, ENTITIES)
        self.assertEqual(len(REPORTS), 14)

    def test_reject_invalid_email(self):
        with self.assertRaises(ValueError):
            parse_value({"name": "email", "label": "Correo", "kind": "email", "required": True,
                         "options": [], "ref": None, "maxlen": 150, "minimum": None}, "no-es-email")

    def test_reject_self_match(self):
        match = {"id_torneo": "1", "numero_fecha": "3", "id_equipo_local": "1",
                 "id_equipo_visitante": "1", "dia": "2026-11-10", "id_turno": "2",
                 "nombre_cancha": "Cancha 1", "id_complejo": "1", "estado": "programado"}
        with self.assertRaises(ValueError):
            validate_row("partido", match)

    def test_sanction_must_be_manual(self):
        s = {"ci_jugador": "11111111", "id_torneo": "1", "numero_fecha_inicio": "4", "cantidad_fechas": "2"}
        value = validate_row("sancion_jugador", s)
        self.assertEqual(value["motivo"], "disciplinaria")

    def test_fixtures_not_leaking_sql(self):
        self.assertTrue(all("%(torneo)s" in sql or slug == "facultades" for slug, (_, _, sql) in REPORTS.items()))
        self.assertTrue(all("%s" not in sql.replace("%(torneo)s", "").replace("%(fecha)s", "") for _, (_, _, sql) in REPORTS.items()))

    def test_original_passwords_and_validation(self):
        script = (ROOT / "sql/03_datos.sql").read_text()
        self.assertIn("'pass123'", script)
        field = {"name": "contrasena", "label": "Contraseña", "kind": "password",
                 "required": False, "options": [], "ref": None, "maxlen": 200, "minimum": None}
        self.assertEqual(parse_value(field, "pass123"), "pass123")


if __name__ == "__main__":
    unittest.main()
