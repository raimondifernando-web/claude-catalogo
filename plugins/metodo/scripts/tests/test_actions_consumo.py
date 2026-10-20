"""Tests de actions-consumo.py: ciclo, escalones de aviso 60/80/90 % y el modo --aviso, sin red ni gh.

Correr desde la raíz del repo:
    python3 -m unittest discover -s plugins/metodo/scripts/tests -p "test_actions_consumo.py" -v
"""
import datetime as dt
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "actions-consumo.py"


def cargar(env):
    for k, v in env.items():
        os.environ[k] = v
    spec = importlib.util.spec_from_file_location("actions_consumo", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class T(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.m = cargar({"CEREBRO_HOME": self.d, "ACTIONS_CICLO_DIA": "4"})

    def test_ciclo(self):
        f = lambda s: self.m.inicio_ciclo(dt.datetime.fromisoformat(s + "T12:00:00+00:00")).isoformat()
        self.assertEqual(f("2026-10-19"), "2026-10-04")
        self.assertEqual(f("2026-10-04"), "2026-10-04")
        self.assertEqual(f("2026-11-02"), "2026-10-04")   # todavía rige el ciclo anterior
        self.assertEqual(f("2026-01-02"), "2025-12-04")

    def test_escalones(self):
        c = lambda t: {"total": t, "cupo": 3000, "proyeccion": 4000, "renueva": "2026-11-04"}
        self.assertIsNone(self.m.linea_aviso(c(1700)))                       # 56 %: callado
        self.assertIn("aviso temprano", self.m.linea_aviso(c(1800))[0])      # 60 %
        self.assertIn("ALTO", self.m.linea_aviso(c(2400))[0])                # 80 %
        self.assertIn("CRÍTICO", self.m.linea_aviso(c(2700))[0])             # 90 %
        self.assertIsNone(self.m.linea_aviso(c(1900), ya_avisado=60))        # mismo escalón: no repite
        self.assertIsNotNone(self.m.linea_aviso(c(2500), ya_avisado=60))     # escalón nuevo: avisa
        self.assertIsNotNone(self.m.linea_aviso(c(2800), ya_avisado=90))     # desde 90 % siempre

    def test_mult(self):
        self.assertEqual((self.m.mult(["ubuntu-latest"]), self.m.mult(["windows-latest"]), self.m.mult(["macos-14"])), (1, 2, 10))

    def _aviso(self, cache):
        Path(self.d, "actions-consumo.json").write_text(json.dumps(cache))
        env = dict(os.environ, CEREBRO_HOME=self.d, PATH="/usr/bin:/bin")   # sin gh en el PATH: no lanza medición
        return subprocess.run([sys.executable, str(SCRIPT), "--aviso"], capture_output=True, text=True, env=env)

    def test_aviso_una_vez_por_escalon(self):
        cache = {"ts": time.time(), "desde": "2026-10-04", "cupo": 3000, "total": 2100, "proyeccion": 3500, "renueva": "2026-11-04"}
        r1 = self._aviso(cache)
        self.assertEqual(r1.returncode, 0)
        self.assertIn("70 %", r1.stdout)
        self.assertEqual(self._aviso(cache).stdout.strip(), "")              # misma situación: silencio
        cache["total"] = 2500
        self.assertIn("ALTO", self._aviso(cache).stdout)

    def test_aviso_sin_cache_calla(self):
        r = subprocess.run([sys.executable, str(SCRIPT), "--aviso"], capture_output=True, text=True,
                           env=dict(os.environ, CEREBRO_HOME=self.d, PATH="/usr/bin:/bin"))
        self.assertEqual((r.returncode, r.stdout.strip()), (0, ""))


if __name__ == "__main__":
    unittest.main()
