"""Tests del freno de la regla 22 (consultar-ecosistema.py + herramientas-para.py). Solo biblioteca estándar, sin red.

Correr desde la raíz del repo:
    python3 -m unittest discover -s plugins/metodo/scripts/tests -v
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent
HOOK = SCRIPTS / "consultar-ecosistema.sh"
UI = "Diseñá e implementá una interfaz web, un dashboard con gráficos y pantallas, creá index.html"


def correr(entrada, cfg, cwd, extra=None):
    env = dict(os.environ, CLAUDE_CONFIG_DIR=str(cfg), TMPDIR=str(cfg))
    env.pop("CONSULTAR_ECOSISTEMA_OFF", None)
    env.update(extra or {})
    d = dict(entrada, cwd=str(cwd))
    return subprocess.run(["bash", str(HOOK)], input=json.dumps(d), capture_output=True, text=True, env=env, timeout=20)


class TestFreno(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cfg = Path(self.tmp.name) / "cfg"
        self.cfg.mkdir()
        self.cwd = Path(self.tmp.name) / "proyecto"
        self.cwd.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def agente(self, prompt=UI):
        return {"tool_name": "Agent", "tool_input": {"prompt": prompt}}

    def test_frena_una_vez_con_la_receta(self):
        r = correr(self.agente(), self.cfg, self.cwd)
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn("Regla 22", r.stderr)
        self.assertIn("frontend-design", r.stderr)
        r2 = correr(self.agente(), self.cfg, self.cwd)  # reintento: pasa
        self.assertEqual(r2.returncode, 0)

    def test_archivo_nuevo_de_interfaz_frena_y_existente_no(self):
        nuevo = {"tool_name": "Write", "tool_input": {"file_path": str(self.cwd / "index.html"), "content": "<html>dashboard pantalla interfaz"}}
        self.assertEqual(correr(nuevo, self.cfg, self.cwd).returncode, 2)
        otra = Path(self.tmp.name) / "otra"
        otra.mkdir()
        (otra / "index.html").write_text("x")
        existente = {"tool_name": "Write", "tool_input": {"file_path": str(otra / "index.html"), "content": "dashboard pantalla interfaz"}}
        self.assertEqual(correr(existente, self.cfg, otra).returncode, 0)

    def test_lo_que_no_es_construir_no_frena(self):
        casos = [
            {"tool_name": "Write", "tool_input": {"file_path": str(self.cwd / "parser.py"), "content": "x"}},
            self.agente("Revisá y auditá el código, solo lectura"),
            {"tool_name": "Bash", "tool_input": {"command": "ls"}},
            self.agente("Creá un resumen de las reuniones del mes"),  # verbo de crear pero sin receta
        ]
        for c in casos:
            with self.subTest(c=c):
                self.assertEqual(correr(c, self.cfg, self.cwd).returncode, 0)

    def test_entrada_rota_o_apagado_dejan_pasar(self):
        env = dict(os.environ, CLAUDE_CONFIG_DIR=str(self.cfg), TMPDIR=str(self.cfg))
        r = subprocess.run(["bash", str(HOOK)], input="{no es json", capture_output=True, text=True, env=env, timeout=20)
        self.assertEqual(r.returncode, 0)
        self.assertEqual(correr(self.agente(), self.cfg, self.cwd, {"CONSULTAR_ECOSISTEMA_OFF": "1"}).returncode, 0)
        (self.cfg / "metodo").mkdir()
        (self.cfg / "metodo" / "consultar-ecosistema.apagado").write_text("")
        self.assertEqual(correr(self.agente(), self.cfg, self.cwd).returncode, 0)

    def test_receta_propia_gana_a_la_del_paquete(self):
        (self.cfg / "recetas").mkdir()
        (self.cfg / "recetas" / "ui-web.md").write_text("---\nname: ui-web\ntriggers: ui interfaz pantalla dashboard\n---\nRECETA PROPIA DE LA EMPRESA\n")
        r = correr(self.agente(), self.cfg, self.cwd)
        self.assertEqual(r.returncode, 2)
        self.assertIn("RECETA PROPIA DE LA EMPRESA", r.stderr)
        self.assertNotIn("frontend-design", r.stderr)

    def test_herramientas_para_sin_receta_lo_dice_y_no_rompe(self):
        env = dict(os.environ, CLAUDE_CONFIG_DIR=str(self.cfg), TMPDIR=str(self.cfg))
        r = subprocess.run([sys.executable, str(SCRIPTS / "herramientas-para.py"), "tema", "inexistente", "zzqq"],
                           capture_output=True, text=True, env=env, cwd=self.cwd, timeout=20)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Sin receta", r.stdout)


if __name__ == "__main__":
    unittest.main()
