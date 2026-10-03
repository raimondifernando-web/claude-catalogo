"""Pruebas de graphify-en-repo con un Graphify de mentira (no hace falta tenerlo instalado).

Todo corre bajo un HOME temporal y con una configuración general de git vacía: nunca toca la de la computadora.
El Graphify de mentira imita lo que hace el real: escribe su skill, una sección en CLAUDE.md y sus enganches en
.claude/settings.json; `update .` deja graphify-out/graph.json.
"""
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "graphify-en-repo"

FALSO = r"""#!/bin/bash
case "$1" in
  --version) echo "graphify ${FALSO_VERSION:-0.9.65}";;
  install)
    mkdir -p .claude/skills/graphify && echo "skill" > .claude/skills/graphify/SKILL.md
    grep -q '^## graphify' CLAUDE.md 2>/dev/null || printf '\n## graphify\nUsá graphify query antes de leer archivos.\n' >> CLAUDE.md
    python3 - <<'PY'
import json, os
p = ".claude/settings.json"
s = json.load(open(p)) if os.path.exists(p) else {}
s.setdefault("hooks", {}).setdefault("PreToolUse", []).append(
    {"matcher": "Glob|Grep", "hooks": [{"type": "command", "command": "graphify hook"}]})
json.dump(s, open(p, "w"))
PY
    ;;
  update) mkdir -p graphify-out && echo '{}' > graphify-out/graph.json;;
  *) exit 2;;
esac
"""


class GraphifyEnRepoTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.home = base / "home"
        (self.home / ".Trash").mkdir(parents=True)
        self.bin = base / "bin"
        self.bin.mkdir()
        self.repo = base / "mi-repo"
        self.repo.mkdir()
        self.gitcfg = base / "gitconfig"
        self.gitcfg.write_text("")
        self.env = {
            "HOME": str(self.home), "PATH": "{}:/usr/bin:/bin".format(self.bin),
            "GIT_CONFIG_GLOBAL": str(self.gitcfg), "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_AUTHOR_NAME": "Prueba", "GIT_AUTHOR_EMAIL": "prueba@example.com",
            "GIT_COMMITTER_NAME": "Prueba", "GIT_COMMITTER_EMAIL": "prueba@example.com",
            "LANG": "en_US.UTF-8",
        }

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.repo)] + list(args), env=self.env, text=True,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True).stdout

    def iniciar_repo(self, settings=None):
        self.git("init", "-q", "-b", "main")
        (self.repo / "app.py").write_text("print('hola')\n")
        (self.repo / "CLAUDE.md").write_text("# Mi proyecto\n")
        archivos = ["app.py", "CLAUDE.md"]
        if settings is not None:
            (self.repo / ".claude").mkdir()
            (self.repo / ".claude/settings.json").write_text(json.dumps(settings))
            archivos.append(".claude/settings.json")
        self.git("add", *archivos)
        self.git("commit", "-q", "-m", "inicio")

    def poner_falso(self, version="0.9.65"):
        g = self.bin / "graphify"
        g.write_text(FALSO)
        g.chmod(0o755)
        self.env["FALSO_VERSION"] = version

    def correr(self, cwd=None):
        r = subprocess.run(["bash", str(SCRIPT)], cwd=str(cwd or self.repo), env=self.env, text=True,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
        return r.returncode, (r.stdout + r.stderr).strip().splitlines()

    def test_fuera_de_un_repo_para(self):
        self.poner_falso()
        rc, out = self.correr()
        self.assertEqual(rc, 1)
        self.assertTrue(out[-1].startswith("Falta: esta carpeta no es un repositorio"))

    def test_sin_graphify_para_con_el_comando_de_instalacion(self):
        self.iniciar_repo()
        rc, out = self.correr()
        self.assertEqual(rc, 1)
        self.assertIn("uv tool install graphifyy==0.9.65", out[-1])
        self.assertTrue(out[-1].endswith("✗"))
        self.assertFalse((self.repo / ".gitignore").exists(), "no tiene que tocar nada si falta graphify")

    def test_otra_version_para(self):
        self.iniciar_repo()
        self.poner_falso("0.9.71")
        rc, out = self.correr()
        self.assertEqual(rc, 1)
        self.assertIn("tenés 0.9.71", out[-1])
        self.assertFalse((self.repo / ".gitignore").exists())

    def test_cambios_sin_guardar_en_claude_md_para_sin_tocar_nada(self):
        self.iniciar_repo()
        self.poner_falso()
        (self.repo / "CLAUDE.md").write_text("# Mi proyecto\ncambio mío sin guardar\n")
        rc, out = self.correr()
        self.assertEqual(rc, 1)
        self.assertIn("CLAUDE.md", out[-1])
        self.assertFalse((self.repo / "graphify-out").exists())
        self.assertEqual(len(self.git("log", "--oneline").splitlines()), 1)

    def test_camino_feliz_guarda_solo_lo_suyo(self):
        compartido = {"extraKnownMarketplaces": {"catalogo": {"source": {"source": "github", "repo": "x/y"}}}}
        self.iniciar_repo(settings=compartido)
        self.poner_falso()
        # algo que el usuario ya tenía preparado para guardar: no puede entrar en el commit
        (self.repo / "otro.txt").write_text("mío\n")
        self.git("add", "otro.txt")
        # la configuración general de git ignora settings.local.json: no cuenta, tiene que ir al .gitignore
        excl = Path(self.tmp.name) / "excludes"
        excl.write_text(".claude/settings.local.json\n")
        self.gitcfg.write_text("[core]\n\texcludesfile = {}\n".format(excl))

        rc, out = self.correr()
        self.assertEqual(rc, 0, out)
        self.assertTrue(out[-1].startswith("Listo ✓"), out)

        ultimo = self.git("show", "--name-only", "--format=", "HEAD").split()
        self.assertEqual(sorted(ultimo), [".gitignore", "CLAUDE.md"])
        self.assertIn("A  otro.txt", self.git("status", "--porcelain"))
        gi = (self.repo / ".gitignore").read_text()
        self.assertIn("graphify-out/\n", gi)
        self.assertIn(".claude/settings.local.json\n", gi)
        # settings.json: lo compartido sigue igual y sin enganches de graphify
        s = json.loads((self.repo / ".claude/settings.json").read_text())
        self.assertEqual(s, compartido)
        self.assertEqual(self.git("status", "--porcelain", "--", ".claude/settings.json"), "")
        local = json.loads((self.repo / ".claude/settings.local.json").read_text())
        self.assertIn("graphify", json.dumps(local))
        # el mapa y lo local quedan ignorados
        self.assertNotIn("graphify-out", self.git("status", "--porcelain", "--ignored=no"))
        self.assertNotIn("settings.local.json", self.git("status", "--porcelain"))

        # segunda corrida: no duplica nada y no guarda de nuevo
        rc2, out2 = self.correr()
        self.assertEqual(rc2, 0, out2)
        self.assertIn("sin cambios para guardar", out2[-1])
        self.assertEqual((self.repo / ".gitignore").read_text().count("graphify-out/"), 1)
        local2 = json.loads((self.repo / ".claude/settings.local.json").read_text())
        self.assertEqual(len(local2["hooks"]["PreToolUse"]), 1)

    def test_settings_json_creado_solo_por_graphify_va_a_la_papelera(self):
        self.iniciar_repo()
        self.poner_falso()
        rc, out = self.correr()
        self.assertEqual(rc, 0, out)
        self.assertFalse((self.repo / ".claude/settings.json").exists())
        self.assertEqual(len(list((self.home / ".Trash").glob("settings.json.graphify-*"))), 1)

    def test_corre_desde_una_subcarpeta(self):
        self.iniciar_repo()
        self.poner_falso()
        sub = self.repo / "src"
        sub.mkdir()
        rc, out = self.correr(cwd=sub)
        self.assertEqual(rc, 0, out)
        self.assertTrue((self.repo / "graphify-out/graph.json").exists())

    def test_negacion_en_gitignore_para_antes_de_generar(self):
        self.iniciar_repo()
        self.poner_falso()
        (self.repo / ".gitignore").write_text("graphify-out/\n!graphify-out/\n")
        self.git("add", ".gitignore")
        self.git("commit", "-q", "-m", "gi")
        rc, out = self.correr()
        self.assertEqual(rc, 1)
        self.assertIn("graphify-out/graph.json", out[-1])
        self.assertFalse((self.repo / "graphify-out").exists())


if __name__ == "__main__":
    unittest.main()
