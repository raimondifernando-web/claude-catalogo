"""freno-hija.py: una sesión hija en carpeta compartida no puede reacomodar ni subir trabajo ajeno ni escribir el REANUDAR.md ajeno.

Todo en carpetas temporales con sesiones falsas (CLAUDE_SESIONES_DIR); nunca toca sesiones, repos ni ajustes reales.
Correr: python3 -m unittest discover -s plugins/metodo/scripts/tests   (el hook vive en ../freno-hija.py)
"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

AQUI = Path(__file__).resolve().parent.parent  # plugins/metodo/scripts
FRENO = AQUI / "freno-hija.py"
ES_POSIX = os.name == "posix"
spec = importlib.util.spec_from_file_location("freno_hija", FRENO)
f = importlib.util.module_from_spec(spec)
spec.loader.exec_module(f)

MADRE, HIJA = "local_aaaaaaaa-0000-4000-8000-000000000001", "local_bbbbbbbb-0000-4000-8000-000000000002"
CLI_MADRE, CLI_HIJA = "aaaaaaaa-1111-4000-8000-000000000001", "bbbbbbbb-1111-4000-8000-000000000002"

PELIGROSOS = ["git pull --rebase --autostash", "git -C sub pull", "git stash", "git checkout -b rama/x", "git checkout -- a.txt",
              "git switch main", "git reset --hard", "git rebase main", "git merge otra", "git add -A", "git add .",
              "git commit -m x", "git commit -am x", "git push", "git push -f origin x", "GIT_DIR=x git rebase main",
              "ls && git pull", "git restore a.txt", "git clean -fd", "git commit --amend -m x -- a.txt", "git cherry-pick abc",
              "git revert abc", "git update-ref refs/heads/main abc", "git branch -D main", "git add *", "git add ./", "git add docs/*.md",
              "git worktree remove ../otra", "cd sub && git pull", "git commit -m x"]
INOFENSIVOS = ["git status --short", "git log --oneline -3", "git stash list", "git merge-base --is-ancestor a b", "git add docs/x.md",
               "git commit -m x -- docs/x.md", "git fetch -q", "git diff", "echo \"git pull\"", "git worktree add /tmp/w -b x origin/main",
               "git -C /private/tmp/w push origin x", "git -C /tmp/w rebase main", "ls -la", "git commit -m \"fix\" src/foo.py",
               "git commit -F msg.txt docs/a.md", "cd /tmp/copia && git pull --rebase", "git branch rama/nueva origin/main",
               "git branch --show-current", "git worktree list"]


class Analisis(unittest.TestCase):
    @unittest.skipUnless(ES_POSIX, "usa rutas de ejemplo de sistemas POSIX (/tmp, /Users)")
    def test_peligrosos(self):
        for c in PELIGROSOS:
            self.assertTrue(f.peligro_git(c, "/Users/x/Proyecto", None), c)

    @unittest.skipUnless(ES_POSIX, "usa rutas de ejemplo de sistemas POSIX (/tmp, /Users)")
    def test_inofensivos(self):
        for c in INOFENSIVOS:
            self.assertIsNone(f.peligro_git(c, "/Users/x/Proyecto", None), c)

    def test_reanudar(self):
        self.assertTrue(f.es_reanudar(".claude/prompts/REANUDAR.md", "/tmp/p"))
        self.assertTrue(f.es_reanudar("REANUDAR.md", "/tmp/p"))
        self.assertFalse(f.es_reanudar("docs/REANUDAR.md", "/tmp/p"))
        self.assertFalse(f.es_reanudar(".claude/prompts/TRASPASO-2026-10-21-x.md", "/tmp/p"))


class Evasiones(unittest.TestCase):
    """Formas que antes se escapaban: grupo de flags con A, alias de git por -c y git.exe de Windows (PowerShell)."""

    def test_add_con_grupo_de_flags_y_alias(self):
        for c in ("git add -Av", "git add -vA", "git add -Au", "git -c alias.x=add x -A", "git -calias.pp=push pp", "git -c ALIAS.p=push p"):
            self.assertTrue(f.peligro_git(c, "/proyecto", None), c)
        for c in ("git add -v docs/x.md", "git add -n docs/x.md", "git -c core.quotepath=false status"):
            self.assertIsNone(f.peligro_git(c, "/proyecto", None), c)

    def test_git_exe_con_cualquier_mayuscula(self):
        for c in ("git.exe pull", "GIT.EXE push", "Git.Exe stash", '"C:\\Program Files\\Git\\cmd\\git.exe" pull'):
            self.assertTrue(f.peligro_git(c, "/proyecto", None), c)
        self.assertIsNone(f.peligro_git("git.exe status", "/proyecto", None))


class DePuntaAPunta(unittest.TestCase):
    """El freno corre como lo corre la app: JSON por la entrada estándar."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = Path(self.tmp.name).resolve()
        self.carpeta = t / "proyecto"
        self.carpeta.mkdir()
        self.ses = t / "ses" / "a" / "b"
        self.ses.mkdir(parents=True)
        self.env = dict(os.environ, CLAUDE_CONFIG_DIR=str(t / "cfg"), CLAUDE_SESIONES_DIR=str(t / "ses"))
        for v in ("FRENO_HIJA", "CLAUDE_CODE_SESSION_ID", "CLAUDE_SESSION_ID"):
            self.env.pop(v, None)

    def tearDown(self):
        self.tmp.cleanup()

    def sesion(self, sid, cli, **extra):
        d = {"sessionId": sid, "cliSessionId": cli, "title": sid[-4:], "cwd": str(self.carpeta), "isArchived": False, **extra}
        (self.ses / f"{sid}.json").write_text(json.dumps(d), encoding="utf-8")

    def correr(self, cli, herramienta, **entrada):
        datos = {"session_id": cli, "cwd": str(self.carpeta), "tool_name": herramienta, "tool_input": entrada}
        r = subprocess.run([sys.executable, str(FRENO)], input=json.dumps(datos), env=self.env, capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)["hookSpecificOutput"]["permissionDecision"] if r.stdout.strip() else "pasa"

    def armar(self, compartida=True):
        self.sesion(MADRE, CLI_MADRE)
        self.sesion(HIJA, CLI_HIJA, spawnedFrom={"sessionId": MADRE, "sideSession": True, "sharedFolder": compartida or None, "name": "hija"})

    def test_hija_compartida_frena(self):
        self.armar()
        self.assertEqual(self.correr(CLI_HIJA, "Bash", command="git pull --rebase --autostash"), "deny")
        self.assertEqual(self.correr(CLI_HIJA, "Write", file_path=str(self.carpeta / ".claude" / "prompts" / "REANUDAR.md")), "deny")
        self.assertEqual(self.correr(CLI_HIJA, "Bash", command="git status"), "pasa")
        self.assertEqual(self.correr(CLI_HIJA, "Bash", command="echo x > .claude/prompts/REANUDAR.md"), "deny")
        self.assertEqual(self.correr(CLI_HIJA, "Bash", command="cat .claude/prompts/REANUDAR.md"), "pasa")
        self.assertEqual(self.correr(CLI_HIJA, "Write", file_path=str(self.carpeta / "docs.md")), "pasa")

    def test_powershell_se_trata_como_bash(self):
        self.armar()
        self.assertEqual(self.correr(CLI_HIJA, "PowerShell", command="git.exe pull --rebase"), "deny")
        self.assertEqual(self.correr(CLI_HIJA, "PowerShell", command="git.exe status"), "pasa")
        self.assertEqual(self.correr(CLI_HIJA, "PowerShell", command="git add -Av"), "deny")

    def test_carpeta_con_metacaracteres_no_arma_el_comando_con_la_ruta(self):
        mala = self.carpeta.parent / "raro$(x)"
        mala.mkdir()
        self.carpeta = mala
        self.armar()
        datos = {"session_id": CLI_HIJA, "cwd": str(mala), "tool_name": "Write", "tool_input": {"file_path": str(mala / "REANUDAR.md")}}
        r = subprocess.run([sys.executable, str(FRENO)], input=json.dumps(datos), env=self.env, capture_output=True, text=True, encoding="utf-8")
        motivo = json.loads(r.stdout)["hookSpecificOutput"]["permissionDecisionReason"]
        self.assertNotIn("raro", motivo)
        self.assertIn("parado en la carpeta", motivo)

    def test_el_aviso_manda_el_informe_como_carta(self):
        self.armar()
        datos = {"session_id": CLI_HIJA, "cwd": str(self.carpeta), "tool_name": "Write",
                 "tool_input": {"file_path": str(self.carpeta / "REANUDAR.md")}}
        r = subprocess.run([sys.executable, str(FRENO)], input=json.dumps(datos), env=self.env, capture_output=True, text=True, encoding="utf-8")
        motivo = json.loads(r.stdout)["hookSpecificOutput"]["permissionDecisionReason"]
        self.assertIn("cartas.py", motivo)

    def test_apagado_por_archivo(self):
        self.armar()
        cfg = Path(self.env["CLAUDE_CONFIG_DIR"]) / "metodo"
        cfg.mkdir(parents=True)
        (cfg / "freno-hija.apagado").write_text("", encoding="utf-8")
        self.assertEqual(self.correr(CLI_HIJA, "Bash", command="git pull"), "pasa")

    def test_sucesora_suelta_no_frena(self):
        """La sesión nueva de una mudanza (detach) no es hija: puede hacer git normal."""
        self.armar()
        self.sesion("local_cccccccc-0000-4000-8000-000000000003", "cccccccc-1111-4000-8000-000000000003",
                    spawnedFrom={"sessionId": MADRE, "sideSession": True}, lineageDetached=True)
        self.assertEqual(self.correr("cccccccc-1111-4000-8000-000000000003", "Bash", command="git pull --rebase --autostash"), "pasa")

    def test_hija_sola_en_la_carpeta_no_frena(self):
        """Si no hay otra sesión viva en la carpeta, no hay a quién pisar."""
        self.armar()
        self.sesion(MADRE, CLI_MADRE, isArchived=True)
        self.assertEqual(self.correr(CLI_HIJA, "Bash", command="git pull"), "pasa")

    def test_madre_no_frena(self):
        self.armar()
        self.assertEqual(self.correr(CLI_MADRE, "Bash", command="git pull --rebase --autostash"), "pasa")
        self.assertEqual(self.correr(CLI_MADRE, "Write", file_path=str(self.carpeta / "REANUDAR.md")), "pasa")

    def test_hija_con_carpeta_propia_no_frena(self):
        self.sesion(MADRE, CLI_MADRE)
        self.sesion(HIJA, CLI_HIJA, worktreePath=str(self.carpeta), spawnedFrom={"sessionId": MADRE, "sideSession": True, "name": "hija"})
        self.assertEqual(self.correr(CLI_HIJA, "Bash", command="git pull --rebase"), "pasa")

    def test_apagado(self):
        self.armar()
        self.env["FRENO_HIJA"] = "0"
        self.assertEqual(self.correr(CLI_HIJA, "Bash", command="git pull"), "pasa")

    def test_entrada_rota_deja_pasar(self):
        r = subprocess.run([sys.executable, str(FRENO)], input="no es json", env=self.env, capture_output=True, text=True)
        self.assertEqual((r.returncode, r.stdout), (0, ""))


if __name__ == "__main__":
    unittest.main()
