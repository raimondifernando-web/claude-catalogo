"""Tests de probado-en.py (regla 25: automatizaciones de GitHub se prueban antes en un repo privado real), sin red.

Correr desde la raíz del repo:
    python3 -m unittest discover -s plugins/metodo/scripts/tests -p "test_probado_en.py" -v
"""
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "probado-en.py"
_spec = importlib.util.spec_from_file_location("probado_en", SCRIPT)
pe = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pe)


class T(unittest.TestCase):
    def test_exigencia(self):
        self.assertIsNone(pe.exigencia(["docs/a.md", "src/x.py"], False))
        self.assertIn("ruleset", pe.exigencia([".github/rulesets/main.json"], True))
        self.assertIn("plantillas", pe.exigencia([".claude/controles-repo/controles.yml"], True))
        self.assertIn("instalación masiva", pe.exigencia(["scripts/activar-controles.py"], True))
        self.assertIn("instalación masiva", pe.exigencia(["bin/instalar_todo.sh"], True))
        # un workflow en repo PÚBLICO exige prueba en uno privado; en el propio privado no
        self.assertIn("público", pe.exigencia([".github/workflows/x.yml"], False))
        self.assertIsNone(pe.exigencia([".github/workflows/x.yml"], True))

    def test_declaracion(self):
        self.assertIsNone(pe.declaracion(""))
        self.assertIsNone(pe.declaracion("Probado-en: ninguno"))
        self.assertIsNone(pe.declaracion("Probado-en: catálogo"))
        self.assertIsNone(pe.declaracion("Probado-en: x"))
        self.assertIsNotNone(pe.declaracion("hola\nProbado-en: tibp-docs (PR de prueba de punta a punta, limpio)"))

    def _repo(self, archivo):
        d = tempfile.mkdtemp()
        g = lambda *a: subprocess.run(["git", "-C", d, "-c", "user.email=t@t", "-c", "user.name=t", *a],
                                      capture_output=True, text=True, check=True).stdout.strip()
        g("init", "-q", "-b", "main")
        Path(d, "a.txt").write_text("x"); g("add", "-A"); g("commit", "-qm", "b")
        base = g("rev-parse", "HEAD")
        p = Path(d, archivo); p.parent.mkdir(parents=True, exist_ok=True); p.write_text("x")
        g("add", "-A"); g("commit", "-qm", "h")
        return d, base, g("rev-parse", "HEAD")

    def _correr(self, d, base, head, **env):
        e = {k: v for k, v in os.environ.items() if k not in ("PR_BODY", "PR_AUTOR", "REPO_PRIVADO")}
        return subprocess.run([sys.executable, str(SCRIPT), "--base", base, "--head", head], cwd=d,
                              capture_output=True, text=True, env={**e, **env})

    def test_de_punta_a_punta(self):
        d, b, h = self._repo(".claude/controles-repo/zona-sensible.yml")
        self.assertEqual(self._correr(d, b, h, PR_BODY="sin la linea").returncode, 1)
        self.assertEqual(self._correr(d, b, h, PR_BODY="Probado-en: tibp-docs (instalado y PR de prueba, limpio)").returncode, 0)
        self.assertEqual(self._correr(d, b, h, PR_BODY="", PR_AUTOR="dependabot[bot]").returncode, 0)
        d, b, h = self._repo("docs/n.md")
        self.assertEqual(self._correr(d, b, h, PR_BODY="").returncode, 0)

    def test_refs_invalidas_y_sin_historia(self):
        r = subprocess.run([sys.executable, str(SCRIPT), "--base", "-x", "--head", "HEAD"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 1)
        with tempfile.TemporaryDirectory() as d:
            r = subprocess.run([sys.executable, str(SCRIPT), "--base", "0000000", "--head", "HEAD"], cwd=d, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1)
            self.assertIn("no pude comparar", r.stdout)


if __name__ == "__main__":
    unittest.main()
