"""Pruebas de reglas-al-actuar.py: frena una vez por sesión+ayudante+regla, borra marcas al compactar, se apaga."""
import json
import os
import subprocess
import sys
import tempfile
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))
PROG = os.path.join(os.path.dirname(AQUI), "reglas-al-actuar.py")


def correr(cfg, datos, *args, env_extra=None):
    env = dict(os.environ, CLAUDE_CONFIG_DIR=cfg)
    env.pop("REGLAS_AL_ACTUAR_OFF", None)
    env.update(env_extra or {})
    p = subprocess.run([sys.executable, PROG, *args], input=json.dumps(datos), capture_output=True,
                       text=True, encoding="utf-8", env=env, timeout=20)
    return p.returncode, p.stderr


def bash(cmd, sesion="s1", agente=None, cwd=None):
    d = {"hook_event_name": "PreToolUse", "session_id": sesion, "tool_name": "Bash",
         "tool_input": {"command": cmd}, "cwd": cwd or tempfile.gettempdir()}
    if agente:
        d["agent_id"] = agente
    return d


class ReglasAlActuar(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cfg = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def test_frena_una_vez_y_despues_deja_pasar(self):
        rc, err = correr(self.cfg, bash("git push origin main --force"))
        self.assertEqual(rc, 2)
        self.assertIn("historia-y-borrados", err)
        self.assertIn("Nunca `--force`", err)
        rc, _ = correr(self.cfg, bash("git push origin main --force"))
        self.assertEqual(rc, 0)

    def test_comando_comun_no_frena(self):
        rc, err = correr(self.cfg, bash("git status"))
        self.assertEqual((rc, err), (0, ""))

    def test_otro_ayudante_y_otra_sesion_tambien_la_leen(self):
        self.assertEqual(correr(self.cfg, bash("git reset --hard HEAD"))[0], 2)
        self.assertEqual(correr(self.cfg, bash("git reset --hard HEAD", agente="agent-1"))[0], 2)
        self.assertEqual(correr(self.cfg, bash("git reset --hard HEAD", sesion="s2"))[0], 2)

    def test_compactar_borra_la_marca(self):
        self.assertEqual(correr(self.cfg, bash("gh pr merge 3 --squash --auto"))[0], 2)
        correr(self.cfg, {"hook_event_name": "SessionStart", "session_id": "s1", "source": "compact"})
        self.assertEqual(correr(self.cfg, bash("gh pr merge 3 --squash --auto"))[0], 2)

    def test_ruta_de_ajustes_frena_en_write(self):
        d = {"hook_event_name": "PreToolUse", "session_id": "s1", "tool_name": "Write",
             "tool_input": {"file_path": "/u/x/.claude/settings.json", "content": "{}"}}
        rc, err = correr(self.cfg, d)
        self.assertEqual(rc, 2)
        self.assertIn("ajustes-de-claude", err)

    def test_regla_del_usuario_gana_y_se_suma(self):
        d = os.path.join(self.cfg, "reglas-al-actuar")
        os.makedirs(d)
        with open(os.path.join(d, "probar-workflow.md"), "w", encoding="utf-8") as f:
            f.write("---\nherramientas: Bash\npatron: gh\\s+workflow\\s+run\n---\nTexto propio.\n")
        rc, err = correr(self.cfg, bash("gh workflow run estable.yml"))
        self.assertEqual(rc, 2)
        self.assertIn("Texto propio.", err)

    def aprobar(self, proy):
        os.makedirs(os.path.join(self.cfg, "metodo"), exist_ok=True)
        with open(os.path.join(self.cfg, "metodo", "reglas-al-actuar-proyectos.txt"), "a", encoding="utf-8") as f:
            f.write(proy + "\n")

    def test_regla_de_proyecto_sin_aprobar_no_vale(self):
        with tempfile.TemporaryDirectory() as proy:
            os.makedirs(os.path.join(proy, ".claude", "reglas-al-actuar"))
            with open(os.path.join(proy, ".claude", "reglas-al-actuar", "x.md"), "w", encoding="utf-8") as f:
                f.write("---\nherramientas: Bash\npatron: hacer-algo\n---\nDel proyecto.\n")
            self.assertEqual(correr(self.cfg, bash("hacer-algo ya", cwd=proy))[0], 0)

    def test_proyecto_no_pisa_una_regla_del_paquete(self):
        with tempfile.TemporaryDirectory() as proy:
            self.aprobar(proy)
            os.makedirs(os.path.join(proy, ".claude", "reglas-al-actuar"))
            with open(os.path.join(proy, ".claude", "reglas-al-actuar", "historia-y-borrados.md"), "w", encoding="utf-8") as f:
                f.write("---\nherramientas: Bash\npatron: nunca-coincide\n---\nApagada.\n")
            rc, err = correr(self.cfg, bash("git reset --hard", cwd=proy))
            self.assertEqual(rc, 2)
            self.assertNotIn("Apagada.", err)

    def test_patron_explosivo_de_proyecto_se_ignora(self):
        with tempfile.TemporaryDirectory() as proy:
            self.aprobar(proy)
            os.makedirs(os.path.join(proy, ".claude", "reglas-al-actuar"))
            with open(os.path.join(proy, ".claude", "reglas-al-actuar", "mala.md"), "w", encoding="utf-8") as f:
                f.write("---\nherramientas: Bash\npatron: (a+)+$\n---\nMala.\n")
            self.assertEqual(correr(self.cfg, bash("aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaab", cwd=proy))[0], 0)

    def test_regla_del_proyecto(self):
        with tempfile.TemporaryDirectory() as proy:
            self.aprobar(proy)
            os.makedirs(os.path.join(proy, ".claude", "reglas-al-actuar"))
            with open(os.path.join(proy, ".claude", "reglas-al-actuar", "x.md"), "w", encoding="utf-8") as f:
                f.write("---\nherramientas: Bash\npatron: hacer-algo\n---\nDel proyecto.\n")
            rc, err = correr(self.cfg, bash("hacer-algo ya", cwd=proy))
            self.assertEqual(rc, 2)
            self.assertIn("Del proyecto.", err)

    def test_llamadas_en_paralelo_frenan_una_sola_vez(self):
        env = dict(os.environ, CLAUDE_CONFIG_DIR=self.cfg)
        env.pop("REGLAS_AL_ACTUAR_OFF", None)
        datos = json.dumps(bash("git reset --hard HEAD", sesion="par"))
        ps = [subprocess.Popen([sys.executable, PROG], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, text=True, encoding="utf-8", env=env) for _ in range(6)]
        rcs = []
        for p in ps:
            p.communicate(datos, timeout=20)
            rcs.append(p.returncode)
        self.assertEqual(sorted(rcs), [0, 0, 0, 0, 0, 2])

    def test_regla_del_proyecto_va_rotulada_y_con_tope(self):
        with tempfile.TemporaryDirectory() as proy:
            self.aprobar(proy)
            os.makedirs(os.path.join(proy, ".claude", "reglas-al-actuar"))
            with open(os.path.join(proy, ".claude", "reglas-al-actuar", "y.md"), "w", encoding="utf-8") as f:
                f.write("---\nherramientas: Bash\npatron: algo-largo\n---\n" + "z" * 20000 + "\n")
            rc, err = correr(self.cfg, bash("algo-largo", cwd=proy))
            self.assertEqual(rc, 2)
            self.assertIn("aprobó la carpeta", err)
            self.assertLess(err.count("z"), 9000)

    def test_apagado(self):
        rc, _ = correr(self.cfg, bash("git reset --hard"), env_extra={"REGLAS_AL_ACTUAR_OFF": "1"})
        self.assertEqual(rc, 0)
        os.makedirs(os.path.join(self.cfg, "metodo"))
        open(os.path.join(self.cfg, "metodo", "reglas-al-actuar.apagado"), "w").close()
        self.assertEqual(correr(self.cfg, bash("git reset --hard"))[0], 0)

    def test_puente_se_retira_si_el_plugin_lo_trae(self):
        inst = os.path.join(self.cfg, "plugin-metodo")
        os.makedirs(os.path.join(inst, "scripts"))
        open(os.path.join(inst, "scripts", "reglas-al-actuar.py"), "w").close()
        os.makedirs(os.path.join(self.cfg, "plugins"))
        with open(os.path.join(self.cfg, "plugins", "installed_plugins.json"), "w") as f:
            json.dump({"plugins": {"metodo@claude-catalogo": [{"installPath": inst}]}}, f)
        self.assertEqual(correr(self.cfg, bash("git reset --hard"), "--puente")[0], 0)
        self.assertEqual(correr(self.cfg, bash("git reset --hard"))[0], 2)

    def test_entrada_rota_deja_pasar(self):
        env = dict(os.environ, CLAUDE_CONFIG_DIR=self.cfg)
        p = subprocess.run([sys.executable, PROG], input="no es json", capture_output=True, text=True, encoding="utf-8", env=env)
        self.assertEqual(p.returncode, 0)


if __name__ == "__main__":
    unittest.main()
