"""Corre las pruebas y genera tests/casos_de_prueba.md y tests/resultados.json.

Uso, desde la raiz del proyecto:
    python tests/run_tests.py                 corre todo y regenera los casos de prueba
    python tests/run_tests.py --solo test_05  corre solo los archivos que empiezan asi

Cada prueba documenta su caso en el docstring, con cuatro partes separadas por '|':
    CP-XXX-NN | Caso | Entrada o pasos | Resultado esperado
"""
import argparse
import json
import sys
import time
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))

ESTADOS = ("Aprobado", "Defecto conocido", "Corregido", "Fallo", "Omitido")


class Registro(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.casos = []

    def _guardar(self, test, estado, detalle=""):
        doc = " ".join((getattr(test, "_testMethodDoc", "") or "").split())
        partes = [p.strip() for p in doc.split("|")]
        metodo = getattr(test, getattr(test, "_testMethodName", ""), None)
        marca = getattr(metodo, "defecto", None)
        codigo, obtenido = marca if marca else ("", "")
        self.casos.append({
            "id": partes[0] if len(partes) == 4 else "SIN-ID",
            "caso": partes[1] if len(partes) == 4 else doc or str(test),
            "entrada": partes[2] if len(partes) == 4 else "",
            "esperado": partes[3] if len(partes) == 4 else "",
            "estado": estado,
            "defecto": codigo,
            "obtenido": obtenido if estado == "Defecto conocido" else ("Según lo esperado" if estado == "Aprobado" else detalle[-300:]),
            "modulo": type(test).__module__,
            "prueba": str(getattr(test, "_testMethodName", test)),
        })

    def addSuccess(self, test):
        super().addSuccess(test)
        self._guardar(test, "Aprobado")

    def addExpectedFailure(self, test, err):
        super().addExpectedFailure(test, err)
        self._guardar(test, "Defecto conocido")

    def addUnexpectedSuccess(self, test):
        super().addUnexpectedSuccess(test)
        self._guardar(test, "Corregido", "La prueba pasa: quitar la marca de defecto.")

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self._guardar(test, "Fallo", self._exc_info_to_string(err, test))

    def addError(self, test, err):
        super().addError(test, err)
        if hasattr(test, "_testMethodName"):
            self._guardar(test, "Fallo", self._exc_info_to_string(err, test))

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self._guardar(test, "Omitido", reason)


def celda(texto):
    return str(texto).replace("|", "\\|")


def escribir_documentos(casos, duracion, version):
    casos = sorted(casos, key=lambda c: c["id"])
    conteo = {e: sum(1 for c in casos if c["estado"] == e) for e in ESTADOS}
    resumen = {"fecha": time.strftime("%d/%m/%Y %H:%M"), "mysql": version, "duracion_segundos": round(duracion),
               "total": len(casos), "conteo": conteo}
    (AQUI / "resultados.json").write_text(
        json.dumps({"resumen": resumen, "casos": casos}, ensure_ascii=False, indent=1), encoding="utf-8")
    lineas = ["# Casos de prueba", "",
              "Archivo generado por `python tests/run_tests.py`. No editar a mano.", "",
              f"Última ejecución: {resumen['fecha']}, sobre MySQL {version}.", "",
              "| Estado | Cantidad |", "| --- | ---: |"]
    lineas += [f"| {e} | {conteo[e]} |" for e in ESTADOS if conteo[e]]
    lineas += [f"| **Total** | **{len(casos)}** |", "",
               "Un caso en estado *Defecto conocido* afirma el comportamiento deseado y hoy no se cumple.", "",
               "| ID | Caso | Entrada o pasos | Resultado esperado | Resultado obtenido | Estado |",
               "| --- | --- | --- | --- | --- | --- |"]
    for c in casos:
        estado = c["estado"] + (f" ({c['defecto']})" if c["defecto"] else "")
        lineas.append("| " + " | ".join(celda(c[k]) for k in ("id", "caso", "entrada", "esperado", "obtenido")) + f" | {estado} |")
    (AQUI / "casos_de_prueba.md").write_text("\n".join(lineas) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--solo", help="prefijo de los archivos de prueba a correr, por ejemplo test_05")
    args = parser.parse_args()
    patron = f"{args.solo}*.py" if args.solo else "test_*.py"
    suite = unittest.defaultTestLoader.discover(str(AQUI), pattern=patron, top_level_dir=str(AQUI))
    inicio = time.time()
    resultado = unittest.TextTestRunner(resultclass=Registro, verbosity=1).run(suite)
    duracion = time.time() - inicio
    casos = resultado.casos

    print()
    conteo = {e: sum(1 for c in casos if c["estado"] == e) for e in ESTADOS}
    print("Resultado:", ", ".join(f"{e}: {n}" for e, n in conteo.items() if n), f"(total {len(casos)})")
    sin_id = [c["prueba"] for c in casos if c["id"] == "SIN-ID"]
    if sin_id:
        print("Pruebas sin docstring con formato de caso:", ", ".join(sin_id))
    repetidos = sorted({c["id"] for c in casos if c["id"] != "SIN-ID" and sum(1 for x in casos if x["id"] == c["id"]) > 1})
    if repetidos:
        print("IDs repetidos:", ", ".join(repetidos))

    if not args.solo:
        import base
        version = base.valor(base.conectar(base="mysql"), "SELECT VERSION()")
        escribir_documentos(casos, duracion, version)
        print("Se actualizaron tests/casos_de_prueba.md y tests/resultados.json")
    return 0 if resultado.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
