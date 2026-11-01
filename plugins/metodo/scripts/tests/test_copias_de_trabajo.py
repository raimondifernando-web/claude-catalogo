"""copias-de-trabajo: las copias viven dentro del proyecto y solo se sacan las unidas y limpias.
Disparador: encadenado — python3 -m unittest discover -s scripts/tests."""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "copias-de-trabajo"
ENV = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}


def git(cwd, *a):
    return subprocess.run(["git", "-C", str(cwd), *a], capture_output=True, text=True, check=True, env=ENV)


class Copias(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        t = Path(self.t.name)
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(t / "o.git")], check=True)
        self.repo = t / "r"
        subprocess.run(["git", "clone", "-q", str(t / "o.git"), str(self.repo)], check=True, capture_output=True)
        git(self.repo, "checkout", "-q", "-b", "main")
        (self.repo / "proy").mkdir()
        (self.repo / "proy" / "a.py").write_text("a\n")
        git(self.repo, "add", "-A"); git(self.repo, "commit", "-q", "-m", "base"); git(self.repo, "push", "-q", "origin", "main")

    def tearDown(self):
        self.t.cleanup()

    def cdt(self, *args, cwd=None):
        r = subprocess.run(["python3", str(SCRIPT), "--repo", str(cwd or self.repo / "proy"), *args], capture_output=True,
                           text=True, env=ENV, cwd=cwd or self.repo)
        return r.returncode, r.stdout + r.stderr

    def test_nueva_vive_dentro_del_proyecto_y_git_la_ignora(self):
        rc, out = self.cdt("nueva", "tema1")
        self.assertEqual(rc, 0, out)
        self.assertTrue((self.repo / "proy" / ".worktrees" / "tema1" / "proy" / "a.py").exists())
        self.assertEqual(git(self.repo, "status", "--porcelain").stdout.strip(), "")   # no ensucia el repo

    def test_listar_marca_las_sueltas_y_el_trabajo_sin_unir(self):
        self.cdt("nueva", "tema1")
        suelta = self.repo.parent / "suelta"
        git(self.repo, "worktree", "add", "-q", "-b", "x/suelta", str(suelta), "origin/main")
        (suelta / "n.py").write_text("n\n"); git(suelta, "add", "-A"); git(suelta, "commit", "-q", "-m", "n")
        rc, out = self.cdt("listar")
        self.assertEqual(rc, 0, out)
        self.assertIn("CON TRABAJO SIN UNIR", out)
        self.assertIn("2 copias", out)

    def unir_con_trabajo_viejo(self, tema):
        """Crea la copia, hace un commit de hace 2 días, lo une a main y deja la copia unida."""
        self.cdt("nueva", tema)
        copia = self.repo / "proy" / ".worktrees" / tema
        (copia / "proy" / f"{tema}.py").write_text("x\n")
        git(copia, "add", "-A")
        fecha = "@%d +0000" % (__import__("time").time() - 2 * 86400)
        subprocess.run(["git", "-C", str(copia), "commit", "-q", "-m", tema], check=True, capture_output=True,
                       env={**ENV, "GIT_COMMITTER_DATE": fecha, "GIT_AUTHOR_DATE": fecha})
        git(copia, "push", "-q", "origin", "HEAD:main")
        git(self.repo, "fetch", "-q", "origin", "main")
        return copia

    def test_una_copia_recien_creada_y_vacia_no_se_saca(self):
        self.cdt("nueva", "fresca")
        self.cdt("limpiar", "--aplicar")
        self.assertTrue((self.repo / "proy" / ".worktrees" / "fresca").exists())

    def test_una_copia_vacia_que_trajo_main_no_cuenta_como_trabajo(self):
        self.cdt("nueva", "vacia")
        copia = self.repo / "proy" / ".worktrees" / "vacia"
        (self.repo / "proy" / "otro.py").write_text("o\n"); git(self.repo, "add", "-A"); git(self.repo, "commit", "-q", "-m", "o")
        git(self.repo, "push", "-q", "origin", "main"); git(copia, "fetch", "-q", "origin", "main"); git(copia, "merge", "-q", "--ff-only", "origin/main")
        self.cdt("limpiar", "--aplicar")
        self.assertTrue(copia.exists())

    def test_una_copia_con_archivos_ignorados_no_se_saca(self):
        copia = self.unir_con_trabajo_viejo("conlocal")
        (copia / ".gitignore").write_text("datos.local\n")
        git(copia, "add", "-A"); git(copia, "commit", "-q", "-m", "ign")
        (copia / "datos.local").write_text("cosas que no están en git\n")
        # la copia ahora tiene un commit sin unir: la dejamos unida de nuevo
        git(copia, "push", "-q", "origin", "HEAD:main"); git(self.repo, "fetch", "-q", "origin", "main")
        self.cdt("limpiar", "--aplicar")
        self.assertTrue((copia / "datos.local").exists())

    def test_limpiar_saca_solo_las_unidas_y_limpias_de_worktrees(self):
        self.unir_con_trabajo_viejo("unida"); self.cdt("nueva", "conlabor")
        trabajo = self.repo / "proy" / ".worktrees" / "conlabor"
        (trabajo / "proy" / "b.py").write_text("b\n"); git(trabajo, "add", "-A"); git(trabajo, "commit", "-q", "-m", "b")
        rc, out = self.cdt("limpiar")                       # sin --aplicar solo muestra
        self.assertIn("se sacaría", out)
        self.assertTrue((self.repo / "proy" / ".worktrees" / "unida").exists())
        rc, out = self.cdt("limpiar", "--aplicar")
        self.assertEqual(rc, 0, out)
        self.assertFalse((self.repo / "proy" / ".worktrees" / "unida").exists())
        self.assertTrue(trabajo.exists())                   # con trabajo sin unir: no se toca

    def test_no_saca_la_copia_donde_estas_parado(self):
        copia = self.unir_con_trabajo_viejo("unida")
        rc, out = self.cdt("limpiar", "--aplicar", cwd=copia)
        self.assertTrue(copia.exists(), out)

    def test_una_copia_con_cambios_sin_guardar_no_se_saca(self):
        self.cdt("nueva", "sucia")
        copia = self.repo / "proy" / ".worktrees" / "sucia"
        (copia / "proy" / "a.py").write_text("cambiado\n")
        self.cdt("limpiar", "--aplicar")
        self.assertTrue(copia.exists())


if __name__ == "__main__":
    unittest.main()
