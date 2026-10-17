"""Tests de verificar-modelo-hija.py (hook PostToolUse de start_session). Sin red.
    python3 -m unittest discover -s plugins/metodo/scripts/tests -v
"""
import json
import subprocess
import sys
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "verificar-modelo-hija.py"


def correr(entrada):
    r = subprocess.run([sys.executable, str(SCRIPT)], input=entrada if isinstance(entrada, str) else json.dumps(entrada),
                       capture_output=True, text=True, timeout=10)
    return r.returncode, r.stdout.strip()


class Test(unittest.TestCase):
    def test_modelo_pedido_da_la_orden(self):
        rc, out = correr({"tool_name": "mcp__ccd_session__start_session", "tool_input": {"model": "claude-opus-5-5"}})
        self.assertEqual(rc, 0)
        d = json.loads(out)["hookSpecificOutput"]
        self.assertEqual(d["hookEventName"], "PostToolUse")
        self.assertIn("set_session_model", d["additionalContext"])
        self.assertIn("claude-opus-5-5", d["additionalContext"])

    def test_sin_modelo_calla(self):
        self.assertEqual(correr({"tool_name": "mcp__ccd_session__start_session", "tool_input": {"prompt": "x"}}), (0, ""))

    def test_otra_herramienta_calla(self):
        self.assertEqual(correr({"tool_name": "Bash", "tool_input": {"model": "opus"}}), (0, ""))

    def test_basura_no_rompe(self):
        self.assertEqual(correr("no es json"), (0, ""))
        self.assertEqual(correr(""), (0, ""))
        self.assertEqual(correr({"tool_name": "x_start_session", "tool_input": {"model": "a b; rm"}}), (0, ""))


if __name__ == "__main__":
    unittest.main()
