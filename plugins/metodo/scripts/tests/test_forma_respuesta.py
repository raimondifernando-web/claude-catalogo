"""Pruebas de forma-respuesta.py (regla 26): una línea corta por mensaje, apagable con FORMA_RESPUESTA=0."""
import os
import subprocess
import sys
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "forma-respuesta.py"


def correr(**env):
    r = subprocess.run([sys.executable, str(SCRIPT)], env=dict(os.environ, **env), capture_output=True, text=True,
                       encoding="utf-8")
    assert r.returncode == 0
    return r.stdout.strip()


class FormaRespuesta(unittest.TestCase):
    def test_dice_una_linea_corta(self):
        s = correr(FORMA_RESPUESTA="1")
        self.assertIn("regla 26", s)
        self.assertEqual(len(s.splitlines()), 1)
        self.assertLess(len(s.split()), 30)

    def test_se_apaga(self):
        self.assertEqual(correr(FORMA_RESPUESTA="0"), "")


if __name__ == "__main__":
    unittest.main()
