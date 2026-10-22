"""Cierre de sesiones en una vuelta, de punta a punta: mudanza + control de envíos + cartas + arrancar-check + registro en hooks.json.

Todo con sesiones FALSAS en carpetas temporales (CLAUDE_SESIONES_DIR, CLAUDE_CONFIG_DIR); nunca toca las sesiones ni los ajustes reales,
nunca abre la app ni corre `agy`. Correr:
    python3 -m unittest discover -s plugins/metodo/scripts/tests -v
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent
PLUGIN = SCRIPTS.parent
sys.path.insert(0, str(SCRIPTS))
import cartas  # noqa: E402
import cierre_estado  # noqa: E402
import sesiones_hijas as sh  # noqa: E402

GENV = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")


class PuntaAPunta(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = Path(os.path.realpath(self.tmp.name))
        self.raiz, self.carpeta, self.cfg = t / "ses", t / "proyecto", t / "cfg"
        (self.raiz / "a" / "b").mkdir(parents=True)
        (self.carpeta / ".claude" / "prompts").mkdir(parents=True)
        self.cfg.mkdir()
        (self.carpeta / "README.md").write_text("x\n", encoding="utf-8")
        for c in (("init", "-q", "-b", "main"), ("add", "README.md"), ("commit", "-q", "-m", "base")):
            subprocess.run(["git", "-C", str(self.carpeta), *c], check=True, capture_output=True, env=GENV)
        os.environ["CLAUDE_SESIONES_DIR"] = str(self.raiz)

    def tearDown(self):
        os.environ.pop("CLAUDE_SESIONES_DIR", None)
        try:
            self.tmp.cleanup()
        except OSError:  # Windows: git deja el repo temporal tomado un instante; es solo limpieza
            pass

    def sesion(self, sid, titulo, **kw):
        d = {"sessionId": sid, "cliSessionId": "cli-" + sid, "title": titulo, "cwd": str(self.carpeta),
             "lastActivityAt": int(time.time() * 1000), **kw}
        (self.raiz / "a" / "b" / ("local_" + sid + ".json")).write_text(json.dumps(d), encoding="utf-8")
        return d

    def env(self, yo=None, **extra):
        e = {k: v for k, v in os.environ.items() if k not in ("CLAUDE_CODE_SESSION_ID", "CLAUDE_SESSION_ID")}
        e.update(GENV, HOME=str(self.tmp.name), USERPROFILE=str(self.tmp.name), CLAUDE_SESIONES_DIR=str(self.raiz),
                 CLAUDE_CONFIG_DIR=str(self.cfg), PYTHONIOENCODING="utf-8", ACTIONS_CONSUMO_OFF="1", **extra)
        if yo:
            e["CLAUDE_CODE_SESSION_ID"] = "cli-" + yo
        return e

    def correr(self, script, *args, yo=None, entrada=None, **extra):
        r = subprocess.run([sys.executable, str(SCRIPTS / script), *args], cwd=str(self.carpeta), input=entrada, capture_output=True,
                           text=True, encoding="utf-8", errors="replace", env=self.env(yo, **extra), timeout=180)
        return r.returncode, r.stdout + r.stderr

    def test_mudanza_completa_con_carta_y_arranque(self):
        # la sesión que cierra y las que dependen de ella
        self.sesion("local_vieja", "Principal - 1")
        self.sesion("local_otra", "Otra sesión viva")
        # 1. congela (Paso A): la sesión se detecta por la variable de entorno que pone la app
        rc, out = self.correr("cierre-mudanza.py", "congelar", yo="local_vieja")
        self.assertEqual(rc, 0, out)
        # 2. mientras está congelada, un mensaje a la vieja se frena y explica cómo dejar una carta
        pedido = json.dumps({"tool_name": "SendMessage", "session_id": "cli-local_otra", "tool_input": {"to": "local_vieja", "message": "hola"}})
        rc, out = self.correr("freno-envio-cerrando.py", entrada=pedido)
        decision = json.loads(out)["hookSpecificOutput"]
        self.assertEqual(decision["permissionDecision"], "deny")
        self.assertIn("cartas.py", decision["permissionDecisionReason"])
        # 3. quien escribe deja la carta (con el comando exacto del aviso)
        rc, out = self.correr("cartas.py", "dejar", str(self.carpeta), "otra sesión", "revisá el PR 12 cuando arranques")
        self.assertEqual(rc, 0, out)
        # 4. se abre la sucesora, suelta de la vieja, y avanza el estado
        self.sesion("local_nueva", "Principal - 2", spawnedFrom={"sessionId": "local_vieja"}, lineageDetached=True)
        rc, out = self.correr("cierre-mudanza.py", "abierta", "local_nueva")
        self.assertEqual(rc, 0, out)
        reanudar = self.carpeta / ".claude" / "prompts" / "REANUDAR.md"
        reanudar.write_text("<!-- cierre 2026-10-22-prueba -->\nhecho\n", encoding="utf-8")
        d = cierre_estado.leer(str(self.carpeta))
        os.utime(str(reanudar), (d["desde"] + 5, d["desde"] + 5))
        self.assertEqual(self.correr("cierre-mudanza.py", "guardado")[0], 0)
        self.assertEqual(self.correr("cierre-mudanza.py", "hijas")[0], 0)
        rc, out = self.correr("cierre-mudanza.py", "archivar")
        self.assertEqual(rc, 0, out)
        # 5. la vieja se archiva; la sucesora arranca: cierra la mudanza y ve la carta
        self.sesion("local_vieja", "Principal - 1", isArchived=True)
        rc, out = self.correr("arrancar-check.py", yo="local_nueva")
        self.assertIn("Mudanza: el cierre anterior quedó completo", out)
        self.assertIn("CARTAS: 1 sin leer", out)
        self.assertIn("revisá el PR 12", out)
        self.assertEqual(cierre_estado.leer(str(self.carpeta))["paso"], "completo")
        # 6. con la mudanza completa, el control de envíos deja pasar de nuevo
        rc, out = self.correr("freno-envio-cerrando.py", entrada=pedido)
        self.assertEqual((rc, out.strip()), (0, ""))
        # 7. las cartas se leen una sola vez
        rc, out = self.correr("cartas.py", "leer", str(self.carpeta))
        self.assertIn("revisá el PR 12", out)
        self.assertEqual(cartas.contar(str(self.carpeta)), 0)

    def test_cerrar_check_manda_a_cierre_mudanza_para_las_hijas(self):
        self.sesion("yo", "Madre")
        self.sesion("h1", "Hija uno", spawnedFrom={"sessionId": "yo"})
        (self.carpeta / ".claude" / "prompts" / "REANUDAR.md").write_text("<!-- cierre 2026-10-22-x -->\nHecho\nTodo unido.\n", encoding="utf-8")
        rc, out = self.correr("cerrar-check.py", yo="yo")
        self.assertIn("HIJAS A ARCHIVAR (sin preguntarle a nadie): h1 «Hija uno»", out)
        self.assertIn("cierre-mudanza.py hijas", out)

    def test_una_sola_definicion_de_trabajando(self):
        """cierre-hijas, la mudanza y arrancar-check usan sesiones_hijas.estado: la misma hija da el mismo estado en los tres."""
        ahora = int(time.time() * 1000)
        trabajando = {"sessionId": "h", "lastActivityAt": ahora, "spawnedFrom": {"sessionId": "yo"}}
        self.assertEqual(sh.estado(trabajando), "trabajando")
        con_resumen = dict(trabajando, postTurnSummary="listo", postTurnSummaryFor="u1", lastAssistantUuid="u1")
        self.assertEqual(sh.estado(con_resumen), "terminada")
        self.assertEqual(sh.estado(dict(con_resumen, prs=[{"state": "OPEN"}])), "esperando")
        # cierre-hijas.hijas_trabajando mide con la misma función
        import importlib.util
        spec = importlib.util.spec_from_file_location("cierre_hijas_mod", str(SCRIPTS / "cierre-hijas.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        self.sesion("yo", "Madre")
        self.sesion("local_h1", "Hija trabajando", spawnedFrom={"sessionId": "yo"})
        self.sesion("local_h2", "Hija con resumen", spawnedFrom={"sessionId": "yo"}, postTurnSummary="listo", postTurnSummaryFor="u1", lastAssistantUuid="u1")
        self.assertEqual(mod.hijas_trabajando("cli-yo", set()), ["Hija trabajando"])


class Registro(unittest.TestCase):
    """Los dos controles viajan con el plugin: quedan registrados en hooks.json y su script existe (nada que correr a mano)."""

    def setUp(self):
        self.hooks = json.loads((PLUGIN / "hooks" / "hooks.json").read_text(encoding="utf-8"))["hooks"]

    def entradas(self, script):
        out = []
        for evento, grupos in self.hooks.items():
            for g in grupos:
                for h in g.get("hooks", []):
                    if script in h.get("command", ""):
                        out.append((evento, g.get("matcher"), h))
        return out

    def test_freno_de_envios_registrado_como_pretooluse(self):
        e = self.entradas("freno-envio-cerrando.py")
        self.assertEqual(len(e), 1)
        evento, matcher, h = e[0]
        self.assertEqual(evento, "PreToolUse")
        self.assertEqual(set(matcher.split("|")), {"SendMessage", "mcp__ccd_session_mgmt__send_message"})
        self.assertEqual(h["timeout"], 5)
        self.assertTrue((SCRIPTS / "freno-envio-cerrando.py").is_file())

    def test_freno_de_hijas_registrado_como_pretooluse(self):
        e = self.entradas("freno-hija.py")
        self.assertEqual(len(e), 1)
        evento, matcher, h = e[0]
        self.assertEqual(evento, "PreToolUse")
        self.assertEqual(set(matcher.split("|")), {"Bash", "PowerShell", "Write", "Edit", "MultiEdit"})
        self.assertEqual(h["timeout"], 5)
        self.assertTrue((SCRIPTS / "freno-hija.py").is_file())

    def test_comandos_con_alternativa_para_windows_y_que_fallan_abiertos(self):
        for script in ("freno-envio-cerrando.py", "freno-hija.py"):
            cmd = self.entradas(script)[0][2]["command"]
            self.assertIn("python3 ", cmd)
            self.assertIn("py -3 ", cmd)
            self.assertTrue(cmd.rstrip().endswith("|| true"), cmd)  # si no hay Python, deja pasar
            self.assertIn("${CLAUDE_PLUGIN_ROOT}/scripts/" + script, cmd)

    def test_la_descripcion_nombra_los_dos_controles(self):
        d = json.loads((PLUGIN / "hooks" / "hooks.json").read_text(encoding="utf-8"))["description"]
        for frase in ("freno-envio-cerrando.py", "freno-hija.py", "CIERRE_MUDANZA=0", "FRENO_HIJA=0"):
            self.assertIn(frase, d)

    def test_toda_pieza_nueva_declara_su_disparador(self):
        for nombre in ("cartas.py", "cierre_estado.py", "cierre-mudanza.py", "freno-envio-cerrando.py", "freno-hija.py"):
            texto = (SCRIPTS / nombre).read_text(encoding="utf-8")
            self.assertTrue(re.search(r"^[#>\s*\"'-]*Disparador\**\s*:", texto, re.M), nombre)

    def test_nada_de_rutas_ni_nombres_propios_en_lo_nuevo(self):
        # armadas por partes: este mismo archivo no puede contener esos nombres (el catálogo público no nombra clientes ni personas)
        prohibidas = ("/Us" + "ers/", "~/.cla" + "ude", "~/Proy" + "ectos", "Fer" + "nando", "Fer ", "Da" + "ni", "EB" + "RAS", "TI" + "BP")
        for nombre in ("cartas.py", "cierre_estado.py", "cierre-mudanza.py", "freno-envio-cerrando.py", "freno-hija.py"):
            texto = (SCRIPTS / nombre).read_text(encoding="utf-8")
            for p in prohibidas:
                self.assertNotIn(p, texto, "{} contiene {!r}".format(nombre, p))


if __name__ == "__main__":
    unittest.main()
