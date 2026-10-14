"""Pruebas de scripts/zona-sensible.py y scripts/nombres-en-ci.py (repos de git de juguete en una carpeta temporal)."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
ZONA = RAIZ / "scripts" / "zona-sensible.py"
NOMBRES = RAIZ / "scripts" / "nombres-en-ci.py"


def correr(cmd, cwd, env=None):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, env={**os.environ, **(env or {})})


class Repo:
    def __init__(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        for c in (["git", "init", "-q", "-b", "main"], ["git", "config", "user.email", "t@t"],
                  ["git", "config", "user.name", "t"], ["git", "config", "commit.gpgsign", "false"]):
            correr(c, self.d)

    def escribir(self, ruta, texto):
        p = self.d / ruta
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(texto)

    def commit(self, msg="c"):
        correr(["git", "add", "-A"], self.d)
        correr(["git", "commit", "-q", "-m", msg], self.d)
        return correr(["git", "rev-parse", "HEAD"], self.d).stdout.strip()

    def zona(self, base, head):
        return correr([sys.executable, str(ZONA), "--base", base, "--head", head], self.d)


def base_catalogo(r):
    r.escribir("README.md", "hola\n")
    r.escribir("plugins/metodo/.claude-plugin/plugin.json", json.dumps({"name": "metodo", "version": "1.0.0"}))
    r.escribir("plugins/metodo/hooks/hooks.json", json.dumps({"hooks": {"SessionStart": [{"hooks": [
        {"type": "command", "command": "python3 \"${CLAUDE_PLUGIN_ROOT}/scripts/radar.py\" hoy"},
        {"type": "command", "command": "python3 \"${CLAUDE_PLUGIN_ROOT}/scripts/vigia/aviso.py\""}]}]}}))
    r.escribir("plugins/metodo/scripts/radar.py", "import ayudas\nprint('hoy')\n")
    r.escribir("plugins/metodo/scripts/ayudas.py", "X = 1\n")
    r.escribir("plugins/metodo/scripts/otro.py", "print('a pedido')\n")
    r.escribir("plugins/metodo/scripts/vigia/aviso.py", "print('aviso')\n")
    r.escribir("plugins/metodo/scripts/vigia/vigia.py", "print('vigia')\n")
    r.escribir("plugins/metodo/skills/cerrar/SKILL.md", "cerrar\n")
    return r.commit("base")


class ZonaSensible(unittest.TestCase):
    def setUp(self):
        self.r = Repo()
        self.base = base_catalogo(self.r)

    def tearDown(self):
        self.r.tmp.cleanup()

    def cambio(self, ruta, texto="cambio\n"):
        self.r.escribir(ruta, texto)
        return self.r.zona(self.base, self.r.commit())

    def test_skill_no_es_sensible(self):
        out = self.cambio("plugins/metodo/skills/cerrar/SKILL.md")
        self.assertEqual(out.returncode, 0, out.stdout)

    def test_script_a_pedido_no_es_sensible(self):
        self.assertEqual(self.cambio("plugins/metodo/scripts/otro.py").returncode, 0)

    def test_hook_es_sensible(self):
        out = self.cambio("plugins/metodo/hooks/hooks.json", "{}")
        self.assertEqual(out.returncode, 10)
        self.assertIn("hooks.json", out.stdout)

    def test_script_que_ejecuta_un_hook(self):
        self.assertEqual(self.cambio("plugins/metodo/scripts/radar.py", "print(1)\n").returncode, 10)

    def test_modulo_que_importa_el_script_del_hook(self):
        out = self.cambio("plugins/metodo/scripts/ayudas.py", "X = 2\n")
        self.assertEqual(out.returncode, 10)
        self.assertIn("lo usa", out.stdout)

    def test_subcarpeta_entera_del_hook(self):
        self.assertEqual(self.cambio("plugins/metodo/scripts/vigia/vigia.py", "print(2)\n").returncode, 10)

    def test_controles_y_robots(self):
        self.assertEqual(self.cambio(".github/workflows/x.yml", "on: push\n").returncode, 10)
        self.assertEqual(self.cambio("scripts/al-dia.sh", "echo\n").returncode, 10)
        self.assertEqual(self.cambio("scripts/zona-sensible.py", "x\n").returncode, 10)

    def test_mcp(self):
        self.assertEqual(self.cambio("plugins/metodo/.mcp.json", "{}").returncode, 10)

    def test_manifiesto_solo_version_no_es_sensible(self):
        out = self.cambio("plugins/metodo/.claude-plugin/plugin.json",
                          json.dumps({"name": "metodo", "version": "1.1.0", "description": "nueva"}))
        self.assertEqual(out.returncode, 0, out.stdout)

    def test_manifiesto_que_suma_hooks_es_sensible(self):
        out = self.cambio("plugins/metodo/.claude-plugin/plugin.json",
                          json.dumps({"name": "metodo", "version": "1.1.0", "hooks": "./otros.json"}))
        self.assertEqual(out.returncode, 10)

    def test_hook_nuevo_que_llama_un_script_nuevo(self):
        self.r.escribir("plugins/metodo/scripts/nuevo.py", "print('nuevo')\n")
        self.r.escribir("plugins/metodo/hooks/hooks.json", json.dumps({"hooks": {"Stop": [{"hooks": [
            {"type": "command", "command": "python3 ${CLAUDE_PLUGIN_ROOT}/scripts/nuevo.py"}]}]}}))
        out = self.r.zona(self.base, self.r.commit())
        self.assertEqual(out.returncode, 10)
        self.assertIn("scripts/nuevo.py", out.stdout)


class NombresEnCI(unittest.TestCase):
    def setUp(self):
        self.r = Repo()
        self.r.escribir("a.md", "texto comun\n")
        self.base = self.r.commit("base")

    def tearDown(self):
        self.r.tmp.cleanup()

    def correr(self, lista, rango=""):
        cmd = [sys.executable, str(NOMBRES)] + (["--rango", rango] if rango else [])
        return correr(cmd, self.r.d, {"NOMBRES_PROHIBIDOS": lista})

    def test_sin_lista_frena(self):
        self.assertEqual(self.correr("").returncode, 2)

    def test_limpio(self):
        self.assertEqual(self.correr("acme corp\n").returncode, 0)

    def test_encuentra_sin_imprimir_el_nombre(self):
        self.r.escribir("b.md", "trabajo para Acme-Corp en obra\n")
        self.r.commit()
        out = self.correr("acme corp\n")
        self.assertEqual(out.returncode, 1)
        self.assertIn("b.md:1", out.stdout)
        self.assertNotIn("acme", out.stdout.lower())

    def test_palabra_entera(self):
        self.r.escribir("b.md", "acmecorpx\n")
        self.r.commit()
        self.assertEqual(self.correr("acme corp\n").returncode, 0)

    def test_mensaje_de_commit(self):
        self.r.escribir("b.md", "nada\n")
        head = self.r.commit("arreglo para ACME corp")
        out = self.correr("acme corp\n", f"{self.base}..{head}")
        self.assertEqual(out.returncode, 1)
        self.assertIn("mensaje de commit", out.stdout)


if __name__ == "__main__":
    unittest.main()
