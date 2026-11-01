"""ramas-que-pisan: avisa/frena cuando otras ramas abiertas tocan los mismos archivos o hay demasiadas a la vez.
Disparador: encadenado — python3 -m unittest discover -s scripts/tests."""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "ramas-que-pisan"
ENV = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}


def git(cwd, *a):
    return subprocess.run(["git", "-C", str(cwd), *a], capture_output=True, text=True, check=True, env=ENV)


@unittest.skipIf(os.name == "nt", "herramienta de Mac/Linux (git, rutas y bash propios); en Windows no se usa")
class Pisan(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        t = Path(self.t.name)
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(t / "o.git")], check=True)
        self.repo = t / "r"
        subprocess.run(["git", "clone", "-q", str(t / "o.git"), str(self.repo)], check=True, capture_output=True)
        git(self.repo, "checkout", "-q", "-b", "main")
        (self.repo / "grande.js").write_text("x\n" * 40000)       # 80 KB
        (self.repo / "chico.py").write_text("a\n")
        git(self.repo, "add", "-A"); git(self.repo, "commit", "-q", "-m", "base"); git(self.repo, "push", "-q", "origin", "main")

    def tearDown(self):
        self.t.cleanup()

    def rama(self, nombre, archivo, texto):
        git(self.repo, "checkout", "-q", "-b", nombre, "main")
        (self.repo / archivo).write_text(texto)
        git(self.repo, "add", "-A"); git(self.repo, "commit", "-q", "-m", nombre)
        git(self.repo, "push", "-q", "origin", nombre)
        git(self.repo, "checkout", "-q", "main")

    def correr(self, *args, tope="3"):
        r = subprocess.run(["python3", str(SCRIPT), "--repo", str(self.repo), "--max", tope, *args],
                           capture_output=True, text=True)
        return r.returncode, r.stdout + r.stderr

    def test_otra_rama_sobre_un_archivo_grande_frena(self):
        self.rama("a", "grande.js", "y\n" * 40000)
        rc, out = self.correr("grande.js")
        self.assertEqual(rc, 1, out)
        self.assertIn("ARCHIVO GRANDE", out)
        self.assertIn("Falta:", out)

    def test_archivo_chico_compartido_solo_avisa(self):
        self.rama("a", "chico.py", "b\n")
        rc, out = self.correr("chico.py")
        self.assertEqual(rc, 0, out)
        self.assertIn("aviso", out)
        self.assertIn("Todo al día ✓", out)

    def test_archivos_distintos_no_chocan(self):
        self.rama("a", "grande.js", "y\n" * 40000)
        rc, out = self.correr("chico.py")
        self.assertEqual(rc, 0, out)

    def test_demasiadas_ramas_abiertas_frena(self):
        for i in range(4):
            self.rama(f"r{i}", f"f{i}.py", "z\n")
        rc, out = self.correr("otro.py")
        self.assertEqual(rc, 1, out)
        self.assertIn("tope 3", out)

    def test_sin_tope_fijo_muchas_ramas_cortas_no_frenan(self):
        for i in range(5):
            self.rama(f"r{i}", f"f{i}.py", "z\n")
        rc, out = subprocess.run(["python3", str(SCRIPT), "--repo", str(self.repo), "otro.py"], capture_output=True,
                                 text=True).returncode, ""
        self.assertEqual(rc, 0)

    def test_una_rama_larga_se_avisa_sin_frenar(self):
        git(self.repo, "checkout", "-q", "-b", "vieja", "main")
        (self.repo / "v.py").write_text("v\n")
        git(self.repo, "add", "-A")
        subprocess.run(["git", "-C", str(self.repo), "commit", "-q", "-m", "v"], check=True, capture_output=True,
                       env={**ENV, "GIT_COMMITTER_DATE": "@%d +0000" % (__import__("time").time() - 4 * 86400),
                            "GIT_AUTHOR_DATE": "@%d +0000" % (__import__("time").time() - 4 * 86400)})
        git(self.repo, "push", "-q", "origin", "vieja"); git(self.repo, "checkout", "-q", "main")
        rc, out = self.correr("otro.py")
        self.assertEqual(rc, 0, out)
        self.assertIn("LARGAS", out)
        self.assertIn("vieja", out)

    def test_una_rama_ya_unida_no_cuenta(self):
        self.rama("a", "chico.py", "b\n")
        git(self.repo, "checkout", "-q", "main"); (self.repo / "chico.py").write_text("b\n")
        git(self.repo, "add", "-A"); git(self.repo, "commit", "-q", "-m", "squash"); git(self.repo, "push", "-q", "origin", "main")
        rc, out = self.correr("chico.py")
        self.assertEqual(rc, 0, out)
        self.assertNotIn("también lo toca", out)


if __name__ == "__main__":
    unittest.main()
