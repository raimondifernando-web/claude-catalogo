"""Pruebas de unir-a-main con repos de juguete (un remoto «bare» local; nunca toca GitHub).

Correr: python3 -m unittest discover -s plugins/metodo/scripts/tests
"""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "unir-a-main"


def sh(*cmd, cwd=None, env=None):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, env={**os.environ, **(env or {})})


class UnirAMain(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = Path(self.tmp.name)
        self.config = t / "config"
        self.config.mkdir()
        self.remoto = t / "raimondifernando-web" / "cerebro.git"
        self.remoto.parent.mkdir()
        sh("git", "init", "-q", "--bare", "-b", "main", str(self.remoto))
        self.repo = t / "trabajo"
        sh("git", "clone", "-q", str(self.remoto), str(self.repo))
        for c in (["config", "user.email", "t@t"], ["config", "user.name", "t"], ["config", "commit.gpgsign", "false"]):
            sh("git", *c, cwd=self.repo)
        self.escribir("README.md", "hola\n")
        (self.repo / "tests").mkdir()
        self.escribir("tests/test_ok.py", "import unittest\nclass T(unittest.TestCase):\n    def test_a(self): pass\n")
        self.commit("base")
        sh("git", "branch", "-M", "main", cwd=self.repo)
        sh("git", "push", "-q", "origin", "main", cwd=self.repo)
        sh("git", "checkout", "-q", "-b", "tema/prueba", cwd=self.repo)

    def tearDown(self):
        self.tmp.cleanup()

    def escribir(self, ruta, texto):
        p = self.repo / ruta
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(texto)

    def commit(self, msg="c"):
        sh("git", "add", "-A", cwd=self.repo)
        sh("git", "commit", "-q", "-m", msg, cwd=self.repo)

    def unir(self, *extra):
        return sh(sys.executable, str(SCRIPT), "--repo", str(self.repo), "--revisado-por", "subagente code-reviewer",
                  *extra, env={"CLAUDE_CONFIG_DIR": str(self.config)})

    def main_remoto(self):
        return sh("git", "--git-dir", str(self.remoto), "log", "--format=%s%n%b", "-1", "main").stdout

    def test_une_con_pruebas_y_deja_rastro(self):
        self.escribir("a.py", "x = 1\n")
        self.commit("cambio")
        r = self.unir()
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("Unido a main ✓", r.stdout)
        log = self.main_remoto()
        self.assertIn("Unir tema/prueba a main", log)
        self.assertIn("Revisión: subagente code-reviewer", log)
        self.assertRegex(log, r"Pruebas: (pytest|unittest) tests OK")

    def test_pruebas_que_fallan_no_unen(self):
        self.escribir("tests/test_mal.py", "import unittest\nclass T(unittest.TestCase):\n"
                      "    def test_b(self): self.fail('no')\n")
        self.commit("rompe")
        r = self.unir()
        self.assertEqual(r.returncode, 1)
        self.assertIn("fallaron", r.stdout)
        self.assertNotIn("Unir", self.main_remoto())

    def test_zona_sensible_frena_sin_ok(self):
        self.escribir("launchd/local.cerebro.algo.plist", "<plist/>\n")
        self.commit("tarea que arranca sola")
        r = self.unir()
        self.assertEqual(r.returncode, 3)
        self.assertIn("FRENO", r.stdout)
        self.assertNotIn("Unir", self.main_remoto())
        r = self.unir("--ok-fernando")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("Zona sensible: OK de la persona", self.main_remoto())

    def test_cambios_sin_guardar_frenan(self):
        self.escribir("README.md", "a medias\n")
        self.assertEqual(self.unir().returncode, 1)

    def test_main_no_se_une_a_si_mismo(self):
        sh("git", "checkout", "-q", "main", cwd=self.repo)
        r = self.unir()
        self.assertEqual(r.returncode, 1)
        self.assertIn("estás en main", r.stdout)

    def test_repo_fuera_de_la_lista(self):
        (self.config / "unir-a-main.txt").write_text("claude-config\n")
        self.escribir("a.py", "x = 1\n")
        self.commit()
        r = self.unir()
        self.assertEqual(r.returncode, 1)
        self.assertIn("no está en", r.stdout)

    def test_trae_main_nuevo_antes_de_unir(self):
        otro = Path(self.tmp.name) / "otro"
        sh("git", "clone", "-q", str(self.remoto), str(otro))
        for c in (["config", "user.email", "t@t"], ["config", "user.name", "t"]):
            sh("git", *c, cwd=otro)
        (otro / "b.txt").write_text("de otra sesión\n")
        sh("git", "add", "b.txt", cwd=otro)
        sh("git", "commit", "-q", "-m", "otra", cwd=otro)
        sh("git", "push", "-q", "origin", "main", cwd=otro)
        self.escribir("a.py", "x = 1\n")
        self.commit()
        r = self.unir()
        self.assertEqual(r.returncode, 0, r.stdout)
        arbol = sh("git", "--git-dir", str(self.remoto), "ls-tree", "--name-only", "main").stdout
        self.assertIn("b.txt", arbol)
        self.assertIn("a.py", arbol)

    def test_sin_pruebas_pide_motivo(self):
        sh("git", "rm", "-q", "-r", "tests", cwd=self.repo)
        self.commit("sin tests")
        self.assertEqual(self.unir().returncode, 1)
        r = self.unir("--sin-pruebas", "solo documentación")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("sin pruebas en el repo (solo documentación)", self.main_remoto())

    def test_probar_no_sube(self):
        self.escribir("a.py", "x = 1\n")
        self.commit()
        r = self.unir("--probar")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertNotIn("Unir", self.main_remoto())


if __name__ == "__main__":
    unittest.main()
