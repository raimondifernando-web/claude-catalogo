"""Pruebas de skill-externa. Repositorio de autor local temporal con git clone simulado."""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

AQUI = Path(__file__).resolve().parent
SCRIPT = AQUI.parent / "skill-externa"


class TestSkillExterna(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        b = Path(self.tmp.name)
        self.home = b / "home"
        self.home.mkdir()
        self.cfgdir = b / "config"
        self.metodo = self.cfgdir / "metodo"
        self.metodo.mkdir(parents=True)

        # Repositorio git local que simula el autor en GitHub (alguien/repo)
        self.autor_repo = b / "autor_repo"
        self.autor_repo.mkdir()

        self.gitcfg = b / "gitconfig"
        self.gitcfg.write_text(f"""[protocol "file"]
    allow = always
[uploadpack]
    allowFilter = true
[url "file://{self.autor_repo}"]
    insteadOf = https://github.com/alguien/repo.git
    insteadOf = https://github.com/alguien/repo
""")

        self.env = {
            "HOME": str(self.home),
            "CLAUDE_CONFIG_DIR": str(self.cfgdir),
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "GIT_CONFIG_GLOBAL": str(self.gitcfg),
            "GIT_CONFIG_NOSYSTEM": "1",
            "LANG": "en_US.UTF-8",
            "GIT_AUTHOR_NAME": "Test Author",
            "GIT_AUTHOR_EMAIL": "test@example.com",
            "GIT_COMMITTER_NAME": "Test Committer",
            "GIT_COMMITTER_EMAIL": "test@example.com",
        }

        # Inicializar autor_repo con una skill (SKILL.md + helper.py)
        self.git(self.autor_repo, "init", "-q", "-b", "main")
        self.git(self.autor_repo, "config", "uploadpack.allowFilter", "true")
        self.git(self.autor_repo, "config", "uploadpack.allowAnySHA1InWant", "true")

        skill_autor = self.autor_repo / "skills" / "mi-skill"
        skill_autor.mkdir(parents=True)
        (skill_autor / "SKILL.md").write_text("---\nname: mi-skill\ndescription: Skill del autor\n---\n\n# Mi Skill\nTexto del autor v1.\n", encoding="utf-8")
        (skill_autor / "helper.py").write_text("def valor():\n    return 'v1'\n", encoding="utf-8")

        self.git(self.autor_repo, "add", ".")
        self.git(self.autor_repo, "commit", "-q", "-m", "version 1")
        self.sha1 = self.git_out(self.autor_repo, "rev-parse", "HEAD").strip()

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, repo, *args):
        subprocess.run(["git", "-C", str(repo)] + list(args), env=self.env, check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def git_out(self, repo, *args):
        r = subprocess.run(["git", "-C", str(repo)] + list(args), env=self.env, check=True,
                           capture_output=True, text=True)
        return r.stdout

    def run_script(self, *args):
        r = subprocess.run([sys.executable, str(SCRIPT)] + list(args), env=self.env, text=True,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
        return r.returncode, r.stdout + r.stderr

    def test_ciclo_completo_separar_revisar_actualizar(self):
        # Carpeta local con skill copiada y cambios de texto a mano
        skill_local = self.home / "mi-skill"
        skill_local.mkdir()
        (skill_local / "ORIGEN.txt").write_text(f"origen: github:alguien/repo//skills/mi-skill@{self.sha1}\n", encoding="utf-8")
        (skill_local / "NOTA-LOCAL.md").write_text("Reglas propias para el entorno local.\n", encoding="utf-8")
        (skill_local / "SKILL.md").write_text("---\nname: mi-skill\ndescription: Skill del autor\n---\n\n# Mi Skill\nTexto editado a mano.\n", encoding="utf-8")
        (skill_local / "helper.py").write_text("def valor():\n    return 'v1'\n", encoding="utf-8")

        # 1. Probar separar: saca lo propio a NOTA-LOCAL.md y deja la copia igual al sha del autor
        rc, out = self.run_script("separar", str(skill_local))
        self.assertEqual(rc, 0, f"separar falló: {out}")
        self.assertTrue((skill_local / "NOTA-LOCAL.md").is_file())
        self.assertEqual((skill_local / "NOTA-LOCAL.md").read_text(encoding="utf-8"), "Reglas propias para el entorno local.\n")
        skill_md = (skill_local / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("Reglas propias para el entorno local.", skill_md)
        self.assertIn("Texto del autor v1.", skill_md)
        self.assertIn("<!-- reglas-locales:inicio", skill_md)
        self.assertEqual((skill_local / "helper.py").read_text(encoding="utf-8"), "def valor():\n    return 'v1'\n")

        # 2. Probar revisar: limpia sale 0
        rc, out = self.run_script("revisar", str(skill_local))
        self.assertEqual(rc, 0, f"revisar debería dar 0 limpia: {out}")
        self.assertIn("igual a autor@", out)

        # Si se edita a mano un archivo del autor, revisar sale 1
        (skill_local / "helper.py").write_text("def valor():\n    return 'editado a mano'\n", encoding="utf-8")
        rc, out = self.run_script("revisar", str(skill_local))
        self.assertEqual(rc, 1, "revisar debería dar 1 si se editó a mano")
        self.assertIn("distinta de autor@", out)

        # Restaurar archivo para continuar
        (skill_local / "helper.py").write_text("def valor():\n    return 'v1'\n", encoding="utf-8")
        rc, out = self.run_script("revisar", str(skill_local))
        self.assertEqual(rc, 0, out)

        # 3. Probar actualizar: a un sha nuevo conservando NOTA-LOCAL insertada en SKILL.md
        # Crear nueva versión en autor_repo
        skill_autor = self.autor_repo / "skills" / "mi-skill"
        (skill_autor / "SKILL.md").write_text("---\nname: mi-skill\ndescription: Skill del autor v2\n---\n\n# Mi Skill\nTexto del autor v2.\n", encoding="utf-8")
        (skill_autor / "helper.py").write_text("def valor():\n    return 'v2'\n", encoding="utf-8")
        self.git(self.autor_repo, "add", ".")
        self.git(self.autor_repo, "commit", "-q", "-m", "version 2")
        sha2 = self.git_out(self.autor_repo, "rev-parse", "HEAD").strip()

        rc, out = self.run_script("actualizar", str(skill_local), sha2)
        self.assertEqual(rc, 0, f"actualizar falló: {out}")
        self.assertIn(f"{self.sha1[:7]} → {sha2[:7]} ✓", out)

        # Verificar que se actualizó el código del autor y se conservó NOTA-LOCAL en SKILL.md
        self.assertEqual((skill_local / "helper.py").read_text(encoding="utf-8"), "def valor():\n    return 'v2'\n")
        skill_md_v2 = (skill_local / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("Texto del autor v2.", skill_md_v2)
        self.assertIn("<!-- reglas-locales:inicio", skill_md_v2)
        self.assertIn("Reglas propias para el entorno local.", skill_md_v2)
        self.assertTrue((skill_local / "NOTA-LOCAL.md").is_file())

        # Revisar en la versión actualizada sale 0 limpia
        rc, out = self.run_script("revisar", str(skill_local))
        self.assertEqual(rc, 0, f"revisar v2 debería dar 0: {out}")


if __name__ == "__main__":
    unittest.main()
