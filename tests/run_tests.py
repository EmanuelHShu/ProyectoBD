"""Script para correr los tests con unittest."""
import sys
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
TESTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS_DIR))


def main():
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        patron = arg if arg.endswith(".py") else f"*{arg}*.py"
    else:
        patron = "test_*.py"
    suite = unittest.defaultTestLoader.discover(str(TESTS_DIR), pattern=patron, top_level_dir=str(TESTS_DIR))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
