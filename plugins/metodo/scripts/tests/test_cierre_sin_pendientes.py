"""Cierre y arranque que HACEN lo resoluble (metodo 0.46.0): las hijas con algo pendiente se resuelven solas, la caché no cuenta
como trabajo y un repo que no une solo dice el camino una vez y no deja el cierre a medias.

    python3 -m unittest discover -s plugins/metodo/scripts/tests -v
Todo con sesiones FALSAS y repos de juguete en carpetas temporales (CLAUDE_SESIONES_DIR); nunca toca sesiones, repos ni GitHub reales.
"""
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS))
import sesiones_hijas as sh  # noqa: E402
import cierre_repo as cr  # noqa: E402

GENV = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t",
            GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")


def g(cwd, *a):
    return subprocess.run(["git", "-C", str(cwd), *a], capture_output=True, text=True, encoding="utf-8", env=GENV)


class Casos(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.t = Path(os.path.realpath(self.tmp.name))
        self.home = self.t / "home"  # arrancar-check busca las sesiones bajo HOME/Library/Application Support/Claude/claude-code-sessions
        self.raiz = self.home / "Library" / "Application Support" / "Claude" / "claude-code-sessions"
        self.cfg, self.repo, self.remoto = self.t / "cfg", self.t / "proyecto", self.t / "remoto.git"
        (self.raiz / "a" / "b").mkdir(parents=True)
        self.cfg.mkdir()
        subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(self.remoto)], check=True, env=GENV)
        subprocess.run(["git", "clone", "-q", str(self.remoto), str(self.repo)], check=True, capture_output=True, env=GENV)
        g(self.repo, "checkout", "-q", "-b", "main")
        self.commit(self.repo, "README.md", "hola\n", "base")
        g(self.repo, "push", "-q", "-u", "origin", "main")
        os.environ["CLAUDE_SESIONES_DIR"] = str(self.raiz)

    def tearDown(self):
        os.environ.pop("CLAUDE_SESIONES_DIR", None)
        self.tmp.cleanup()

    def commit(self, repo, nombre, texto, msg):
        (Path(repo) / nombre).write_text(texto, encoding="utf-8")
        g(repo, "add", nombre)
        g(repo, "commit", "-q", "-m", msg)

    def sesion(self, sid, titulo, **kw):
        d = {"sessionId": sid, "cliSessionId": "cli-" + sid, "title": titulo, "cwd": str(self.repo),
             "lastActivityAt": int(time.time() * 1000), **kw}
        (self.raiz / "a" / "b" / f"local_{sid}.json").write_text(json.dumps(d), encoding="utf-8")

    def reanudar(self, cuerpo="Hecho\n"):
        d = self.repo / ".claude" / "prompts"
        d.mkdir(parents=True, exist_ok=True)
        (d / "REANUDAR.md").write_text("<!-- cierre 2026-10-15-x -->\n" + cuerpo, encoding="utf-8")

    def correr(self, script, yo="yo", lista=""):
        (self.t / "unir.txt").write_text(lista, encoding="utf-8")
        env = dict(GENV, HOME=str(self.home), USERPROFILE=str(self.home), CLAUDE_SESIONES_DIR=str(self.raiz), CLAUDE_CONFIG_DIR=str(self.cfg),
                   CLAUDE_CODE_SESSION_ID="cli-" + yo, CLAUDE_SESSION_ID="cli-" + yo, CIERRE_REPO_LISTA=str(self.t / "unir.txt"))
        r = subprocess.run([sys.executable, str(SCRIPTS / script)], cwd=self.repo, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", env=env)
        return r.stdout + r.stderr

    def hija_wt(self, nombre, rama, subir=True):
        wt = self.t / ("wt-" + nombre)
        g(self.repo, "worktree", "add", "-q", "-b", rama, str(wt), "main")
        self.commit(wt, nombre + ".txt", nombre + "\n", "trabajo " + nombre)
        if subir:
            g(wt, "push", "-q", "-u", "origin", rama)
        return wt

    # ---- a: la caché de herramientas no es trabajo ----
    def test_a_copia_con_solo_cache_no_frena_y_con_cambio_real_si(self):
        wt = self.hija_wt("a", "hija/a")
        (wt / "app" / "x" / ".omc").mkdir(parents=True)
        (wt / "app" / "x" / ".omc" / "n.md").write_text("x")
        (wt / ".DS_Store").write_text("x")
        self.sesion("vieja", "Serie - 1")
        self.sesion("h", "Hija a", spawnedFrom={"sessionId": "vieja"}, worktreePath=str(wt))
        self.sesion("yo", "Serie - 2")
        out = self.correr("arrancar-check.py")
        self.assertIn("SESIONES ANTERIORES SIN ARCHIVAR", out)
        self.assertNotIn("RESOLVER ANTES DE ARCHIVAR", out)
        (wt / "a.txt").write_text("cambio que importa\n")
        out = self.correr("arrancar-check.py")
        self.assertIn("RESOLVER ANTES DE ARCHIVAR", out)
        self.assertIn("SendMessage a la hija", out)

    # ---- b: lo resoluble lo hace la sesión; la persona no recibe tareas ----
    def test_b_pendiente_da_la_accion_no_es_falta_y_se_archiva_al_resolverse(self):
        self.sesion("vieja", "Serie - 1", queuedSideSessionNotes=[{"sessionId": "h", "report": "x"}])
        self.sesion("h", "Hija con informe", spawnedFrom={"sessionId": "vieja"})
        self.sesion("yo", "Serie - 2")
        out = self.correr("arrancar-check.py")
        self.assertIn("• RESOLVER ANTES DE ARCHIVAR", out)
        self.assertIn("leé su informe (get_session)", out)
        self.assertNotIn("Falta: serie", out)
        self.assertNotIn("• SESIONES ANTERIORES SIN ARCHIVAR", out)
        self.sesion("vieja", "Serie - 1")  # la sesión leyó el informe: la nota ya no está en cola
        out = self.correr("arrancar-check.py")
        self.assertNotIn("RESOLVER ANTES DE ARCHIVAR", out)
        self.assertIn("• SESIONES ANTERIORES SIN ARCHIVAR", out)

    def test_b_cerrar_da_la_accion_en_el_rojo(self):
        self.sesion("yo", "Madre")
        self.sesion("h", "Hija sigue", spawnedFrom={"sessionId": "yo"}, sideSessionReportOwed=True)
        self.reanudar()
        out = self.correr("cerrar-check.py")
        self.assertIn("✗ hija «Hija sigue» (h): todavía no entregó su informe", out)
        self.assertIn("nunca una tarea para la persona", out)

    # ---- c / d ----
    def test_c_avisa_en_el_disco_por_que_la_app_rechazaria_archivar(self):
        self.sesion("vieja", "Serie - 1", steeredByRemoteClient=True)
        self.sesion("yo", "Serie - 2")
        self.assertIn("⚠ si la app la rechaza: tiene un cliente remoto abierto", self.correr("arrancar-check.py"))

    def test_d_no_menciona_lo_ya_archivado(self):
        u = "local_44444444-4444-4444-8444-444444444444"
        self.sesion(u, "Hija ya archivada", isArchived=True)
        self.sesion("vieja", "Serie - 1", isArchived=True)
        self.sesion("yo", "Serie - 2")
        self.reanudar(f"Sesiones: {u}\n")
        out = self.correr("arrancar-check.py")
        self.assertNotIn("Hija ya archivada", out)
        self.assertNotIn(u, out)

    # ---- e: repo que no une solo ----
    def test_e_repo_fuera_de_la_lista_lo_dice_una_vez_y_dentro_no(self):
        self.reanudar()
        out = self.correr("cerrar-check.py", lista="otro-repo\n")
        self.assertEqual(out.count("REPO SIN UNIÓN AUTOMÁTICA"), 1)
        for frag in ("«remoto»", "gh pr create", "gh pr merge <N> --squash --auto", "UN solo comando", "cierre_repo.py volver", "paso 10"):
            self.assertIn(frag, out)
        self.assertNotIn("SIN UNIÓN AUTOMÁTICA", self.correr("cerrar-check.py", lista="remoto\n"))

    def test_e_volver_conserva_el_reanudar_y_no_pierde_trabajo(self):
        g(self.repo, "checkout", "-q", "-b", "cierre/2026-10-15")
        self.reanudar("CIERRE NUEVO\n")
        g(self.repo, "add", ".claude/prompts/REANUDAR.md")
        g(self.repo, "commit", "-q", "-m", "cierre")
        ok, txt = cr.volver(str(self.repo))
        self.assertFalse(ok)
        self.assertIn("no están en GitHub", txt)
        g(self.repo, "push", "-q", "-u", "origin", "cierre/2026-10-15")
        (self.repo / "README.md").write_text("sin guardar\n")
        ok, txt = cr.volver(str(self.repo))
        self.assertFalse(ok)
        self.assertIn("sin guardar", txt)
        g(self.repo, "checkout", "-q", "--", "README.md")
        ok, txt = cr.volver(str(self.repo))
        self.assertTrue(ok, txt)
        self.assertEqual(g(self.repo, "branch", "--show-current").stdout.strip(), "main")
        self.assertIn("CIERRE NUEVO", (self.repo / ".claude/prompts/REANUDAR.md").read_text(encoding="utf-8"))

    # ---- recorrido /cerrar → /arrancar: ninguna tarea para la persona ----
    def test_recorrido_sin_tareas_para_la_persona(self):
        self.sesion("yo", "Serie - 1")
        self.sesion("h", "Hija", spawnedFrom={"sessionId": "yo"}, sideSessionReportOwed=True)
        self.reanudar()
        self.assertIn("✗ hija «Hija»", self.correr("cerrar-check.py"))  # 1) /cerrar encuentra lo resoluble
        self.sesion("h", "Hija", spawnedFrom={"sessionId": "yo"})  # 2) la hija entregó
        self.assertNotIn("✗ hija", self.correr("cerrar-check.py"))
        self.sesion("nueva", "Serie - 2", spawnedFrom={"sessionId": "yo"}, lineageDetached=True)  # 3) abre la siguiente, suelta
        out = self.correr("arrancar-check.py", yo="nueva")  # 4) /arrancar
        self.assertIn("SESIONES ANTERIORES SIN ARCHIVAR", out)
        for malo in ("RESOLVER ANTES DE ARCHIVAR", "NO ARCHIVAR", "Falta: serie", "su dueño"):
            self.assertNotIn(malo, out)

    # ---- Seguridad (revisión C117): un .git/config con core.fsmonitor NO se ejecuta desde estos scripts ----
    def test_fsmonitor_del_git_config_no_se_ejecuta(self):
        if os.name == "nt":
            self.skipTest("el señuelo es un script de shell")
        marca = self.t / "marca-fsmonitor"
        senuelo = self.t / "senuelo.sh"
        senuelo.write_text(f"#!/bin/sh\ntouch '{marca}'\n", encoding="utf-8")
        senuelo.chmod(0o755)
        wt = self.hija_wt("fs", "hija/fs")  # se prepara ANTES del señuelo: los git del propio test lo dispararían
        g(self.repo, "config", "core.fsmonitor", str(senuelo))
        g(self.repo, "status")
        self.assertTrue(marca.exists(), "control: sin el arreglo, git SÍ ejecuta el señuelo")
        marca.unlink()
        sh.bloqueos_det({"sessionId": "h", "worktreePath": str(wt)}, [])
        cr.volver(str(self.repo))
        cr.lineas_cierre(str(self.repo))
        self.reanudar()
        self.correr("cerrar-check.py")
        self.correr("arrancar-check.py")
        self.assertFalse(marca.exists(), "un fsmonitor declarado en .git/config se ejecutó")


if __name__ == "__main__":
    unittest.main()
