"""test_freno_envio_cerrando.py — pruebas del hook PreToolUse freno-envio-cerrando.py.

Usa exclusivamente carpetas temporales (tempfile) y metadatos de sesiones falsos
a través de CLAUDE_SESIONES_DIR y CLAUDE_CONFIG_DIR. Prueba la invocación por
subprocess enviando JSON por stdin. Nunca toca la configuración real ni las sesiones de la app.
"""
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

AQUI = Path(__file__).resolve().parent.parent  # plugins/metodo/scripts
sys.path.insert(0, str(AQUI))

import cierre_estado  # noqa: E402


class TestFrenoEnvioCerrando(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.t = Path(os.path.realpath(self._tmp.name))
        self.raiz = self.t / "sesiones"
        (self.raiz / "a" / "b").mkdir(parents=True)
        self.home = self.t / "home"
        self.config_dir = self.home / ".claude"
        self.config_dir.mkdir(parents=True)
        self.carpeta = self.t / "proyecto"
        self.carpeta.mkdir(parents=True)

        self.hook_path = AQUI / "freno-envio-cerrando.py"
        self.assertTrue(self.hook_path.is_file(), f"No existe el hook en {self.hook_path}")

        os.environ["CLAUDE_SESIONES_DIR"] = str(self.raiz)
        os.environ["CLAUDE_CONFIG_DIR"] = str(self.config_dir)

    def tearDown(self):
        os.environ.pop("CLAUDE_SESIONES_DIR", None)
        os.environ.pop("CLAUDE_CONFIG_DIR", None)
        self._tmp.cleanup()

    def sesion(self, sid, titulo, **kw):
        """Crea o actualiza una sesión falsa en el directorio de sesiones simulado."""
        d = {
            "sessionId": sid,
            "cliSessionId": "cli-" + sid,
            "title": titulo,
            "cwd": str(self.carpeta),
            "lastActivityAt": int(time.time() * 1000),
            **kw,
        }
        p = self.raiz / "a" / "b" / f"local_{sid}.json"
        p.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
        return d

    def correr_hook(self, payload, env=None):
        """Ejecuta el hook pasando el payload JSON por stdin."""
        e = {
            **os.environ,
            "CLAUDE_CONFIG_DIR": str(self.config_dir),
            "CLAUDE_SESIONES_DIR": str(self.raiz),
            "PYTHONIOENCODING": "utf-8",
            **(env or {}),
        }
        r = subprocess.run(
            [sys.executable, str(self.hook_path)],
            input=payload,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=e,
        )
        return r.returncode, r.stdout.strip(), r.stderr.strip()

    def test_envio_vieja_congelada_ambas_herramientas(self):
        """Envío a la vieja congelada produce deny con motivo que nombra la carpeta (ambas herramientas)."""
        self.sesion("local_vieja", "Vieja principal", cwd=str(self.carpeta))
        cierre_estado.congelar(str(self.carpeta), "local_vieja")

        # 1. Herramienta SendMessage
        p1 = json.dumps({
            "tool_name": "SendMessage",
            "tool_input": {"to": "local_vieja", "message": "hola vieja"},
        })
        rc, out, _ = self.correr_hook(p1)
        self.assertEqual(rc, 0)
        self.assertTrue(out)
        data1 = json.loads(out)
        hso1 = data1["hookSpecificOutput"]
        self.assertEqual(hso1["permissionDecision"], "deny")
        self.assertIn(str(self.carpeta), hso1["permissionDecisionReason"])
        self.assertIn("cartas.py", hso1["permissionDecisionReason"])
        self.assertIn("dejar", hso1["permissionDecisionReason"])

        # 2. Herramienta mcp__ccd_session_mgmt__send_message
        p2 = json.dumps({
            "tool_name": "mcp__ccd_session_mgmt__send_message",
            "tool_input": {"session_id": "local_vieja", "message": "hola MCP"},
        })
        rc, out, _ = self.correr_hook(p2)
        self.assertEqual(rc, 0)
        self.assertTrue(out)
        data2 = json.loads(out)
        hso2 = data2["hookSpecificOutput"]
        self.assertEqual(hso2["permissionDecision"], "deny")
        self.assertIn(str(self.carpeta), hso2["permissionDecisionReason"])
        self.assertIn("cartas.py", hso2["permissionDecisionReason"])
        self.assertIn("dejar", hso2["permissionDecisionReason"])

    def test_hija_que_le_escribe_a_parent_tambien_se_frena(self):
        """Una hija que manda a «parent» (sin id) se resuelve por quién la abrió: si el padre está cerrando, deny."""
        self.sesion("local_vieja", "Vieja principal", cwd=str(self.carpeta))
        self.sesion("local_hija", "Hija", cwd=str(self.carpeta), spawnedFrom={"sessionId": "local_vieja"})
        cierre_estado.congelar(str(self.carpeta), "local_vieja")
        p = json.dumps({
            "tool_name": "mcp__ccd_session_mgmt__send_message",
            "session_id": "cli-local_hija",
            "tool_input": {"session_id": "parent", "message": "listo"},
        })
        rc, out, _ = self.correr_hook(p)
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(out)["hookSpecificOutput"]["permissionDecision"], "deny")
        # sin congelar → pasa
        (self.carpeta / ".claude" / "cerrando.json").unlink()
        rc, out, _ = self.correr_hook(p)
        self.assertEqual((rc, out), (0, ""))

    def test_envio_otra_sesion_sin_salida(self):
        """Envío a otra sesión no congelada deja pasar sin salida."""
        self.sesion("local_vieja", "Vieja", cwd=str(self.carpeta))
        self.sesion("local_otra", "Otra Viva", cwd=str(self.carpeta))
        cierre_estado.congelar(str(self.carpeta), "local_vieja")

        payload = json.dumps({
            "tool_name": "SendMessage",
            "tool_input": {"to": "local_otra", "message": "hola otra"},
        })
        rc, out, _ = self.correr_hook(payload)
        self.assertEqual(rc, 0)
        self.assertEqual(out, "")

    def test_envio_nombre_sin_local_sin_salida(self):
        """Envío a un destinatario que no empieza con 'local_' deja pasar sin salida."""
        self.sesion("local_vieja", "Vieja", cwd=str(self.carpeta))
        cierre_estado.congelar(str(self.carpeta), "local_vieja")

        for nombre in ("usuario", "PM", "remoto_123"):
            payload = json.dumps({
                "tool_name": "SendMessage",
                "tool_input": {"to": nombre, "message": "hola"},
            })
            rc, out, _ = self.correr_hook(payload)
            self.assertEqual(rc, 0)
            self.assertEqual(out, "")

    def test_json_roto_sin_salida_y_log(self):
        """JSON roto no frena (exit 0, sin salida) y anota en hook.log."""
        rc, out, _ = self.correr_hook("{ json invalido")
        self.assertEqual(rc, 0)
        self.assertEqual(out, "")

        log_path = self.config_dir / "state" / "cierre-mudanza" / "hook.log"
        self.assertTrue(log_path.is_file())
        contenido = log_path.read_text(encoding="utf-8")
        self.assertIn("JSON roto", contenido)

    def test_cierre_mudanza_desactivado_por_env(self):
        """CIERRE_MUDANZA=0 desactiva el hook (deja pasar siempre sin salida)."""
        self.sesion("local_vieja", "Vieja", cwd=str(self.carpeta))
        cierre_estado.congelar(str(self.carpeta), "local_vieja")

        payload = json.dumps({
            "tool_name": "SendMessage",
            "tool_input": {"to": "local_vieja", "message": "hola"},
        })
        rc, out, _ = self.correr_hook(payload, env={"CIERRE_MUDANZA": "0"})
        self.assertEqual(rc, 0)
        self.assertEqual(out, "")

    def test_apagado_por_archivo(self):
        """El archivo <config>/metodo/freno-envio-cerrando.apagado también lo desactiva."""
        self.sesion("local_vieja", "Vieja", cwd=str(self.carpeta))
        cierre_estado.congelar(str(self.carpeta), "local_vieja")
        payload = json.dumps({"tool_name": "SendMessage", "tool_input": {"to": "local_vieja", "message": "hola"}})
        rc, out, _ = self.correr_hook(payload)
        self.assertTrue(out)  # sin el archivo, frena
        (self.config_dir / "metodo").mkdir(parents=True)
        (self.config_dir / "metodo" / "freno-envio-cerrando.apagado").write_text("", encoding="utf-8")
        rc, out, _ = self.correr_hook(payload)
        self.assertEqual((rc, out), (0, ""))

    def test_estado_completo_o_viejo_sin_salida(self):
        """Estado 'completo' o con más de 24 horas deja pasar sin salida."""
        self.sesion("local_vieja", "Vieja", cwd=str(self.carpeta))
        d = cierre_estado.congelar(str(self.carpeta), "local_vieja")

        payload = json.dumps({
            "tool_name": "SendMessage",
            "tool_input": {"to": "local_vieja", "message": "hola"},
        })

        # Caso 1: estado marcado como 'completo'
        d["paso"] = "completo"
        cierre_estado.escribir(str(self.carpeta), d)
        rc, out, _ = self.correr_hook(payload)
        self.assertEqual(rc, 0)
        self.assertEqual(out, "")

        # Caso 2: estado con más de 24 horas (no vigente)
        d["paso"] = "congelado"
        d["desde"] = time.time() - 25 * 3600
        cierre_estado.escribir(str(self.carpeta), d)
        rc, out, _ = self.correr_hook(payload)
        self.assertEqual(rc, 0)
        self.assertEqual(out, "")


if __name__ == "__main__":
    unittest.main()
