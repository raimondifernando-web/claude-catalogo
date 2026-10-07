"""Pruebas de nombres-prohibidos. Todo bajo carpetas temporales (CLAUDE_CONFIG_DIR y HOME).
Configuración de git aislada con GIT_CONFIG_GLOBAL=/dev/null."""
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

AQUI = Path(__file__).resolve().parent
SCRIPT = AQUI.parent / "nombres-prohibidos"


class TestNombresProhibidos(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        b = Path(self.tmp.name)
        self.home = b / "home"
        self.home.mkdir()
        self.cfgdir = b / "config"
        self.metodo = self.cfgdir / "metodo"
        self.metodo.mkdir(parents=True)
        self.lista_path = self.metodo / "nombres-prohibidos.txt"
        self.env = {
            "HOME": str(self.home),
            "CLAUDE_CONFIG_DIR": str(self.cfgdir),
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_CONFIG_NOSYSTEM": "1",
            "LANG": "en_US.UTF-8",
            "GIT_AUTHOR_NAME": "Test Author",
            "GIT_AUTHOR_EMAIL": "test@example.com",
            "GIT_COMMITTER_NAME": "Test Committer",
            "GIT_COMMITTER_EMAIL": "test@example.com",
        }

    def tearDown(self):
        self.tmp.cleanup()

    def run_script(self, *args, stdin_text=None):
        r = subprocess.run([sys.executable, str(SCRIPT)] + list(args), env=self.env, text=True,
                           input=stdin_text, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
        return r.returncode, r.stdout + r.stderr

    def git(self, repo, *args):
        r = subprocess.run(["git", "-C", str(repo)] + list(args), env=self.env, text=True,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
        return r.returncode, r.stdout + r.stderr

    def test_agregar_no_duplica_y_deja_600(self):
        rc, out = self.run_script("agregar", "Acme")
        self.assertEqual(rc, 0, out)
        self.assertTrue(self.lista_path.is_file())
        modo = stat.S_IMODE(self.lista_path.stat().st_mode)
        self.assertEqual(modo, 0o600)
        self.assertEqual(self.lista_path.read_text(encoding="utf-8").strip(), "Acme")

        # Agregar el mismo nombre no lo duplica
        rc, out = self.run_script("agregar", "Acme")
        self.assertEqual(rc, 0, out)
        lineas = [l.strip() for l in self.lista_path.read_text(encoding="utf-8").splitlines() if l.strip()]
        self.assertEqual(lineas, ["Acme"])
        self.assertEqual(stat.S_IMODE(self.lista_path.stat().st_mode), 0o600)

        # Agregar otro nombre
        rc, out = self.run_script("agregar", "Globex")
        self.assertEqual(rc, 0, out)
        lineas = [l.strip() for l in self.lista_path.read_text(encoding="utf-8").splitlines() if l.strip()]
        self.assertEqual(lineas, ["Acme", "Globex"])
        self.assertEqual(stat.S_IMODE(self.lista_path.stat().st_mode), 0o600)

        # Nunca imprime la lista completa
        self.assertNotIn("Acme\nGlobex", out)

    def test_revisar_palabra_entera(self):
        self.run_script("agregar", "Acme")
        repo = self.home / "repo"
        repo.mkdir()
        self.git(repo, "init", "-q", "-b", "main")

        # Acmeville contiene "Acme" pero no como palabra entera: no debe fallar
        (repo / "info.txt").write_text("Sede en Acmeville sur\n")
        self.git(repo, "add", "info.txt")
        self.git(repo, "commit", "-q", "-m", "menciona acmeville")
        rc, out = self.run_script("revisar", str(repo))
        self.assertEqual(rc, 0, f"Acmeville no debe activar el control: {out}")
        self.assertIn("Todo al día ✓", out)

        # Acme como palabra entera: debe ser detectado y salir 1
        (repo / "info.txt").write_text("Contrato con Acme firmado\n")
        self.git(repo, "add", "info.txt")
        self.git(repo, "commit", "-q", "-m", "agrega acme")
        rc, out = self.run_script("revisar", str(repo))
        self.assertEqual(rc, 1, "Acme debe activar el control")
        self.assertIn("Subida frenada", out)
        self.assertIn("Acme", out)

    def test_lista_vacia_sale_cero_e_instalar_avisa(self):
        repo = self.home / "repo"
        repo.mkdir()
        self.git(repo, "init", "-q", "-b", "main")
        (repo / "archivo.txt").write_text("prueba\n")
        self.git(repo, "add", "archivo.txt")
        self.git(repo, "commit", "-q", "-m", "commit inicial")

        # Sin lista: revisar sale 0
        rc, out = self.run_script("revisar", str(repo))
        self.assertEqual(rc, 0, out)

        # Sin lista: pre-push sale 0 sin bloquear
        rc, out = self.run_script("pre-push", str(repo), stdin_text="")
        self.assertEqual(rc, 0, out)

        # Sin lista: instalar igual instala y avisa en una linea
        rc, out = self.run_script("instalar", str(repo))
        self.assertEqual(rc, 0, out)
        self.assertIn("Lista vacía: sumá nombres con nombres-prohibidos agregar", out)
        self.assertTrue((repo / ".git" / "hooks" / "pre-push").is_file())

    def test_instalar_crea_pre_push(self):
        repo = self.home / "repo"
        repo.mkdir()
        self.git(repo, "init", "-q", "-b", "main")

        rc, out = self.run_script("instalar", str(repo))
        self.assertEqual(rc, 0, out)
        hook = repo / ".git" / "hooks" / "pre-push"
        self.assertTrue(hook.is_file())
        self.assertTrue(bool(hook.stat().st_mode & 0o111))
        contenido = hook.read_text(encoding="utf-8")
        self.assertIn("# nombres-prohibidos (metodo)", contenido)
        self.assertIn("find", contenido)

    def test_push_remoto_local_con_nombre_rechazado_y_sin_nombre_pasa(self):
        remoto = self.home / "remoto.git"
        self.git(self.home, "init", "--bare", "-q", "-b", "main", str(remoto))

        repo = self.home / "repo"
        repo.mkdir()
        self.git(repo, "init", "-q", "-b", "main")
        self.git(repo, "remote", "add", "origin", str(remoto))

        self.run_script("agregar", "Acme")
        rc, out = self.run_script("instalar", str(repo))
        self.assertEqual(rc, 0, out)

        # 1. Commit limpio inicial pasa el push
        (repo / "doc.txt").write_text("Documento sin nombres prohibidos\n")
        self.git(repo, "add", "doc.txt")
        self.git(repo, "commit", "-q", "-m", "inicio limpio")
        rc, out = self.git(repo, "push", "origin", "main")
        self.assertEqual(rc, 0, f"Push limpio debe pasar: {out}")

        # 2. Commit con nombre prohibido «Acme» en un archivo es rechazado
        (repo / "doc.txt").write_text("Proyecto confidencial para Acme\n")
        self.git(repo, "add", "doc.txt")
        self.git(repo, "commit", "-q", "-m", "agrega acme")
        rc, out = self.git(repo, "push", "origin", "main")
        self.assertNotEqual(rc, 0, "Push con Acme debe ser rechazado")
        self.assertIn("Subida frenada", out)
        self.assertIn("Acme", out)

        # 3. Al quitar o corregir el nombre prohibido, el push pasa
        self.git(repo, "reset", "--hard", "HEAD~1")
        (repo / "doc.txt").write_text("Proyecto confidencial para Acmeville\n")
        self.git(repo, "add", "doc.txt")
        self.git(repo, "commit", "-q", "-m", "cambio permitido")
        rc, out = self.git(repo, "push", "origin", "main")
        self.assertEqual(rc, 0, f"Push corregido debe pasar: {out}")


if __name__ == "__main__":
    unittest.main()
