"""Contrato: el panel «Tareas y pendientes» (paneles) y pendientes-check.py (metodo) aceptan los MISMOS estados.

Pasó el 2026-10-27: /metodo:cerrar y la plantilla escribían «espera dato» y el panel solo leía «espera dato de F»
(«No pude leer bien PENDIENTES.md» en casi todas las listas del cliente). El patrón vive en dos lenguajes (Python y
TypeScript); este test los compara contra la misma tabla y falla si vuelven a divergir.

    python3 -m unittest discover -s plugins/metodo/scripts/tests -v
"""
import importlib.util
import re
import unittest
from pathlib import Path

AQUI = Path(__file__).resolve().parent
PLUGINS = AQUI.parent.parent.parent
REGISTER = PLUGINS / "paneles" / "hooks" / "register.tsx"
CHECK = AQUI.parent / "pendientes-check.py"
PLANTILLA = AQUI.parent.parent / "templates" / "PENDIENTES.plantilla.md"

VALIDOS = [
    "pendiente", "en curso", "hecho",
    "espera dato", "espera OK",              # forma canónica (plantilla y /metodo:cerrar)
    "espera dato de F", "espera OK de F",    # forma larga de las listas viejas
    "espera dato de Ana", "Espera dato", "espera ok",
]
INVALIDOS = ["", "inventado", "esperando", "espera", "espera dato:", "espera datos", "pendiente de F", "en curso (F)"]


def patron_panel():
    m = re.search(r"const ESTADO_VALIDO = /(.+)/(\w*)\n", REGISTER.read_text(encoding="utf-8"))
    assert m, "no encuentro ESTADO_VALIDO en paneles/hooks/register.tsx"
    return re.compile(m.group(1), re.I if "i" in m.group(2) else 0)


def patron_check():
    spec = importlib.util.spec_from_file_location("pendientes_check", CHECK)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.ESTADO_OK


class EstadosDelPanelYDelCheck(unittest.TestCase):
    def test_los_dos_aceptan_y_rechazan_lo_mismo(self):
        panel, check = patron_panel(), patron_check()
        for e in VALIDOS:
            self.assertTrue(panel.match(e), f"el panel rechaza «{e}»")
            self.assertTrue(check.match(e), f"pendientes-check rechaza «{e}»")
        for e in INVALIDOS:
            self.assertIsNone(panel.match(e), f"el panel acepta «{e}»")
            self.assertIsNone(check.match(e), f"pendientes-check acepta «{e}»")

    def test_los_estados_de_la_plantilla_los_lee_el_panel(self):
        texto = PLANTILLA.read_text(encoding="utf-8")
        m = re.search(r"Estado \(solo estos\): (.+?)\. Quién", texto, re.S)
        self.assertIsNotNone(m, "la plantilla ya no lista sus estados")
        estados = [x.strip() for x in re.split(r"·", re.sub(r"\s*\n>\s*", " ", m.group(1)))]
        self.assertGreaterEqual(len(estados), 5)
        panel = patron_panel()
        for e in estados:
            self.assertTrue(panel.match(e), f"la plantilla lista «{e}» y el panel no lo lee")


if __name__ == "__main__":
    unittest.main()
