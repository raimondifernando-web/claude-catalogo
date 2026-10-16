"""Pruebas de recordar-nombre.py (regla 24): solo lee la ficha de CLAUDE_CONFIG_DIR y nunca inventa un nombre."""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "recordar-nombre.py"


def correr(texto):
    with tempfile.TemporaryDirectory() as d:
        if texto is not None:
            (Path(d) / "CLAUDE.md").write_text(texto, encoding="utf-8")
        env = dict(os.environ, CLAUDE_CONFIG_DIR=d)
        r = subprocess.run([sys.executable, str(SCRIPT)], env=env, capture_output=True, text=True)
        assert r.returncode == 0
        return r.stdout.strip()


class RecordarNombre(unittest.TestCase):
    def test_con_nombre(self):
        self.assertIn("«Ana»", correr("# Ficha\nLlamame: Ana\n"))

    def test_con_negritas_y_guion(self):
        self.assertIn("«Ana»", correr("- **Llamame:** Ana\n"))

    def test_sin_linea_calla(self):
        self.assertEqual(correr("# Ficha\nNada\n"), "")

    def test_sin_ficha_calla(self):
        self.assertEqual(correr(None), "")

    def test_varias_personas_calla(self):
        self.assertEqual(correr("Personas en esta computadora: Ana, Luis\nLlamame: Ana\n"), "")

    def test_ejemplo_del_bloque_de_reglas_no_cuenta(self):
        t = "<!-- reglas-del-metodo:inicio -->\nLlamame: Ejemplo\n<!-- reglas-del-metodo:fin -->\n"
        self.assertEqual(correr(t), "")

    def test_marcador_sin_completar_calla(self):
        self.assertEqual(correr("Llamame: <cómo>\n"), "")


if __name__ == "__main__":
    unittest.main()
