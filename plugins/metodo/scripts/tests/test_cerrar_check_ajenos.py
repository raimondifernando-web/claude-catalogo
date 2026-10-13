"""cerrar-check: en una copia compartida, lo sucio de OTRA carpeta avisa («•») y no frena; lo de ESTA carpeta sí frena.

    python3 -m unittest discover -s plugins/metodo/scripts/tests -v
Todo en carpetas temporales.
"""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

CERRAR = Path(__file__).resolve().parent.parent / "cerrar-check.py"
GENV = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")


def git(cwd, *a):
    subprocess.run(["git", "-C", str(cwd), *a], check=True, capture_output=True, env=GENV)


class Ajenos(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name) / "repo"
        for d in ("a", "b"):
            (self.repo / d).mkdir(parents=True)
            (self.repo / d / "CLAUDE.md").write_text("x\n", encoding="utf-8")
        git(self.repo, "init", "-q", "-b", "main")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "base")

    def tearDown(self):
        self.tmp.cleanup()

    def correr(self):
        r = subprocess.run([sys.executable, str(CERRAR)], cwd=self.repo / "a", capture_output=True, text=True, encoding="utf-8")
        return r.stdout

    def linea_git(self, out):
        return next(l for l in out.splitlines() if "versionados" in l)

    def test_ajeno_sucio_no_frena(self):
        (self.repo / "b" / "CLAUDE.md").write_text("cambio de otra sesión\n", encoding="utf-8")
        out = self.correr()
        self.assertTrue(self.linea_git(out).startswith("✓"), out)
        self.assertIn("FUERA de esta carpeta", out)
        self.assertIn("b/CLAUDE.md", out)

    def test_propio_sucio_frena(self):
        (self.repo / "a" / "CLAUDE.md").write_text("mi cambio sin guardar\n", encoding="utf-8")
        out = self.correr()
        self.assertTrue(self.linea_git(out).startswith("✗"), out)

    def test_propio_y_ajeno_frena_por_el_propio(self):
        (self.repo / "a" / "CLAUDE.md").write_text("mío\n", encoding="utf-8")
        (self.repo / "b" / "CLAUDE.md").write_text("ajeno\n", encoding="utf-8")
        out = self.correr()
        self.assertTrue(self.linea_git(out).startswith("✗"), out)
        self.assertIn(": CLAUDE.md", self.linea_git(out))
        self.assertNotIn("b/", self.linea_git(out))

    def test_ajeno_que_ordena_antes_no_confunde(self):
        (self.repo / "0x").mkdir()
        (self.repo / "0x" / "f").write_text("x\n", encoding="utf-8")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "0x")
        (self.repo / "0x" / "f").write_text("ajeno\n", encoding="utf-8")
        (self.repo / "a" / "CLAUDE.md").write_text("mío\n", encoding="utf-8")
        out = self.correr()
        self.assertTrue(self.linea_git(out).startswith("✗"), out)
        self.assertNotIn("0x", self.linea_git(out))

    def test_estructura_se_muestra_y_no_frena(self):
        out = self.correr()
        self.assertIn("Estructura Claude", out)
        self.assertTrue(any(l.startswith("  • R") and "settings.json" in l for l in out.splitlines()), out)
        falta = next((l for l in out.splitlines() if l.startswith("Falta:")), "")
        self.assertNotIn("settings.json", falta)
        self.assertNotIn("Estructura", falta)


if __name__ == "__main__":
    unittest.main()
