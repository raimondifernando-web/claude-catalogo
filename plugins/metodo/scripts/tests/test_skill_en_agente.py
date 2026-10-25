"""skill-en-agente.py: avisa (una vez) si el pedido nombra una skill y el ayudante no tiene la herramienta Skill.
Todo en una config falsa (CLAUDE_CONFIG_DIR temporal). Correr: python3 -m unittest discover -s plugins/metodo/scripts/tests"""
import json, os, subprocess, sys, tempfile, unittest
from pathlib import Path

HOOK = Path(__file__).resolve().parent.parent / "skill-en-agente.py"


def agente(base, nombre, tools):
    d = base / "agents"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{nombre}.md").write_text(f"---\nname: {nombre}\ndescription: x\n" + (f"tools: {tools}\n" if tools else "") + "---\ncuerpo\n")


class Prueba(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cfg = Path(self.tmp.name)
        agente(self.cfg, "sin-skill", "Read, Write, Bash")
        agente(self.cfg, "con-skill", "Read, Write, Skill")
        agente(self.cfg, "todas", None)
        s = self.cfg / "skills" / "mi-guia"
        s.mkdir(parents=True)
        (s / "SKILL.md").write_text("---\nname: mi-guia\ndescription: x\n---\n")

    def tearDown(self):
        self.tmp.cleanup()

    def correr(self, sub, prompt):
        env = dict(os.environ, CLAUDE_CONFIG_DIR=str(self.cfg), TMPDIR=self.tmp.name)
        env.pop("SKILL_EN_AGENTE_OFF", None)
        entrada = json.dumps({"tool_name": "Agent", "cwd": self.tmp.name, "tool_input": {"subagent_type": sub, "prompt": prompt}})
        return subprocess.run([sys.executable, str(HOOK)], input=entrada, capture_output=True, text=True, env=env)

    def test_frena_una_vez(self):
        r = self.correr("sin-skill", "cargá la skill mi-guia y hacé X")
        self.assertEqual(r.returncode, 2)
        self.assertIn("mi-guia", r.stderr)
        self.assertIn("general-purpose", r.stderr)
        self.assertEqual(self.correr("sin-skill", "cargá la skill mi-guia y hacé X").returncode, 0)

    def test_con_skill_o_todas_pasa(self):
        self.assertEqual(self.correr("con-skill", "usá /mi-guia").returncode, 0)
        self.assertEqual(self.correr("todas", "usá /mi-guia").returncode, 0)

    def test_sin_skill_nombrada_o_desconocido_pasa(self):
        self.assertEqual(self.correr("sin-skill", "hacé X").returncode, 0)
        self.assertEqual(self.correr("no-existe", "usá /mi-guia").returncode, 0)

    def test_con_ruta_del_skill_pasa(self):
        r = self.correr("sin-skill", f"leé {self.cfg}/skills/mi-guia/SKILL.md (skill mi-guia)")
        self.assertEqual(r.returncode, 0)

    def test_apagado(self):
        env = dict(os.environ, CLAUDE_CONFIG_DIR=str(self.cfg), SKILL_EN_AGENTE_OFF="1")
        r = subprocess.run([sys.executable, str(HOOK)], input=json.dumps({"tool_name": "Agent", "tool_input": {"subagent_type": "sin-skill", "prompt": "/mi-guia"}}), capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()
