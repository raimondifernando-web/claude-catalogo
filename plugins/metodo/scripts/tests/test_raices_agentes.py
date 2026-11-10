"""raices_agentes: sin archivo = solo ~/.claude/agents; con archivo lee rutas, comodines y comentarios; un enlace al kit no duplica;
buscar() encuentra en cualquier raíz; raiz_de() etiqueta personal / kit-pyme / proyecto:<carpeta>; RAICES_AGENTES manda.
Disparador: encadenado — python3 -m unittest discover -s scripts/tests."""
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import raices_agentes as ra  # noqa: E402

AG = "---\nname: x\ndescription: x\n---\n"


class Raices(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.h = os.path.realpath(self.t.name)
        self.cd = os.path.join(self.h, ".claude")
        for d in (".claude/agents", ".claude/metodo", ".claude/kit-pyme/agents", "Proyectos/Uno/.claude/agents", "Proyectos/Dos/.claude/agents"):
            os.makedirs(os.path.join(self.h, d))
        self.w(".claude/agents/general.md")
        self.w(".claude/kit-pyme/agents/conciliador.md")
        self.w("Proyectos/Uno/.claude/agents/pm-uno.md")
        os.symlink(os.path.join(self.h, ".claude/kit-pyme/agents"), os.path.join(self.h, "Proyectos/Uno/.claude/agents/kit-pyme"))
        os.environ.pop("RAICES_AGENTES", None)

    def tearDown(self):
        os.environ.pop("RAICES_AGENTES", None)
        self.t.cleanup()

    def w(self, rel):
        with open(os.path.join(self.h, rel), "w", encoding="utf-8") as f:
            f.write(AG)

    def conf(self, texto):
        with open(os.path.join(self.h, ".claude/metodo/raices-agentes.txt"), "w", encoding="utf-8") as f:
            f.write(texto)

    def test_sin_archivo_solo_personal(self):
        self.assertEqual(ra.raices(claude_dir=self.cd), [os.path.join(self.h, ".claude/agents")])
        self.assertEqual([os.path.basename(x) for x in ra.archivos(claude_dir=self.cd)], ["general.md"])

    def test_archivo_con_comodines_y_comentarios(self):
        self.conf("# raíces\n~/.claude/agents\n~/.claude/kit-pyme/agents\n~/Proyectos/*/.claude/agents\n~/no-existe\n")
        r = [x.replace(self.h, "~") for x in ra.raices(claude_dir=self.cd)]
        self.assertEqual(r, ["~/.claude/agents", "~/.claude/kit-pyme/agents", "~/Proyectos/Dos/.claude/agents", "~/Proyectos/Uno/.claude/agents"])
        self.assertTrue(all(not x.startswith("/private") or self.h.startswith("/private") for x in ra.raices(claude_dir=self.cd)))  # sin resolver enlaces
        nombres = sorted(os.path.basename(x) for x in ra.archivos(claude_dir=self.cd))
        self.assertEqual(nombres, ["conciliador.md", "general.md", "pm-uno.md"])   # el enlace kit-pyme no duplica a conciliador

    def test_buscar_y_raiz_de(self):
        self.conf("~/.claude/agents\n~/.claude/kit-pyme/agents\n~/Proyectos/*/.claude/agents\n")
        self.assertTrue(ra.buscar("conciliador", claude_dir=self.cd).endswith("kit-pyme/agents/conciliador.md"))
        self.assertTrue(ra.buscar("pm-uno", claude_dir=self.cd).endswith("Uno/.claude/agents/pm-uno.md"))
        self.assertIsNone(ra.buscar("nadie", claude_dir=self.cd))
        self.assertEqual(ra.raiz_de(os.path.join(self.h, ".claude/agents/general.md"), claude_dir=self.cd), "personal")
        self.assertEqual(ra.raiz_de(os.path.join(self.h, ".claude/kit-pyme/agents/conciliador.md"), claude_dir=self.cd), "kit-pyme")
        self.assertEqual(ra.raiz_de(os.path.join(self.h, "Proyectos/Uno/.claude/agents/pm-uno.md"), claude_dir=self.cd), "proyecto:Uno")

    def test_variable_de_entorno_manda(self):
        self.conf("~/.claude/agents\n")
        os.environ["RAICES_AGENTES"] = os.path.join(self.h, "Proyectos/Dos/.claude/agents")
        self.assertEqual(ra.raices(claude_dir=self.cd), [os.path.join(self.h, "Proyectos/Dos/.claude/agents")])


if __name__ == "__main__":
    unittest.main()
