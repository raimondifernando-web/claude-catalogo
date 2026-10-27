"""Numeración de sesiones con emoji al principio, «(fork)» al final y cambio de ancho (metodo 0.57.2).

    python3 -m unittest discover -s plugins/metodo/scripts/tests -v
Sesiones FALSAS en carpetas temporales (CLAUDE_SESIONES_DIR); nunca toca las reales.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent


class Numeracion(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = Path(os.path.realpath(self.tmp.name))
        self.raiz, self.repo, self.cfg = t / "ses", t / "repo", t / "cfg"
        (self.raiz / "a" / "b").mkdir(parents=True)
        self.repo.mkdir()
        self.cfg.mkdir()
        self.n = 0

    def tearDown(self):
        try:
            self.tmp.cleanup()
        except OSError:
            pass

    def sesion(self, titulo, t, **kw):
        self.n += 1
        sid = f"s{self.n}"
        d = {"sessionId": sid, "cliSessionId": "cli-" + sid, "title": titulo, "cwd": str(self.repo),
             "lastActivityAt": t, **kw}
        (self.raiz / "a" / "b" / f"local_{sid}.json").write_text(json.dumps(d), encoding="utf-8")
        return sid

    def correr(self):
        env = dict(os.environ, HOME=str(self.tmp.name), CLAUDE_SESIONES_DIR=str(self.raiz), CLAUDE_CONFIG_DIR=str(self.cfg),
                   PYTHONIOENCODING="utf-8")
        env.pop("CLAUDE_SESSION_ID", None)
        r = subprocess.run([sys.executable, str(SCRIPTS / "arrancar-check.py")], cwd=self.repo, capture_output=True,
                           text=True, encoding="utf-8", errors="replace", env=env)
        return r.stdout + r.stderr

    def test_emoji_en_la_anterior_y_la_nueva_sin_emoji(self):
        # el caso de la persona que lo reportó: la 04 tiene 🧬, la 05 nació sin él
        vieja = self.sesion("🧬 SERIE SETUP. 04", 1000)
        self.sesion("SERIE SETUP. 05", 2000)
        out = self.correr()
        self.assertIn('"🧬 SERIE SETUP. 05"', out)
        self.assertIn(vieja, out)  # la 04 se manda a archivar
        self.assertNotIn("sin serie numerada", out)

    def test_cierre_hecho_desde_un_fork(self):
        vieja = self.sesion("🧬 SERIE SETUP. 04 (fork)", 1000)
        orig = self.sesion("🧬 SERIE SETUP. 04", 900)
        self.sesion("SERIE SETUP. 05", 2000)
        out = self.correr()
        self.assertIn(vieja, out)
        self.assertIn(orig, out)
        self.assertIn('"🧬 SERIE SETUP. 05"', out)

    def test_nueva_ya_bien_nombrada_no_se_toca(self):
        self.sesion("🧬 SERIE SETUP. 04", 1000)
        self.sesion("🧬 SERIE SETUP. 05", 2000)
        out = self.correr()
        self.assertIn("la sesión ya se llama", out)

    def test_sin_adorno_sigue_igual(self):
        vieja = self.sesion("Proyecto X - 03", 1000)
        self.sesion("Proyecto X - 04", 2000)
        out = self.correr()
        self.assertIn(vieja, out)

    def test_ancho_03_a_04_y_99_a_100(self):
        self.sesion("🧬 Serie 03", 1000)
        self.sesion("Serie 03", 1500)
        self.sesion("Serie 04", 1800)  # la actual (más reciente): ya numerada
        self.assertIn("ya se llama", self.correr())
        # la nueva aún sin número: sale 04 con el mismo ancho
        self.tearDown(); self.setUp()
        self.sesion("🧬 Serie 02", 1000)
        self.sesion("🧬 Serie 03", 1500)
        self.sesion("Nueva sin numero", 2000)
        self.assertIn('"🧬 Serie 04"', self.correr())
        self.tearDown(); self.setUp()
        self.sesion("🧬 Serie 98", 1000)
        self.sesion("🧬 Serie 99", 1500)
        self.sesion("Nueva sin numero", 2000)
        self.assertIn('"🧬 Serie 100"', self.correr())


if __name__ == "__main__":
    unittest.main()
