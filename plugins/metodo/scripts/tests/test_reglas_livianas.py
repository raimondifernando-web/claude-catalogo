"""Control anti-engorde (2026-11-09): reglas cortas del método ≤ 500 B, y aviso de peso al arrancar sin fallar."""
import os
import re
import subprocess
import sys
import tempfile
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))
METODO = os.path.dirname(os.path.dirname(AQUI))
TOPE_REGLA = 500


class ReglasCortas(unittest.TestCase):
    def test_cada_regla_corta_entra_en_500_bytes(self):
        t = open(os.path.join(METODO, "templates", "REGLAS-DEL-METODO.md"), encoding="utf-8").read()
        largas = []
        for parte in re.split(r"\n(?=\d+\. \*\*)", t)[1:]:
            cuerpo = re.split(r"\n\n## ", parte)[0].strip()
            if len(cuerpo.encode("utf-8")) > TOPE_REGLA:
                largas.append((cuerpo.split(".", 1)[0], len(cuerpo.encode("utf-8"))))
        self.assertEqual(largas, [], "Reglas cortas de más de %d B: el detalle va a REGLAS-DEL-METODO-COMPLETO.md "
                                     "o a reglas-al-actuar/ (llega solo al actuar)" % TOPE_REGLA)

    def test_reglas_al_actuar_tienen_encabezado_valido(self):
        d = os.path.join(METODO, "reglas-al-actuar")
        for a in sorted(os.listdir(d)):
            t = open(os.path.join(d, a), encoding="utf-8").read()
            m = re.match(r"---\nherramientas: (.+)\npatron: (.+)\n---\n", t)
            self.assertTrue(m, a)
            re.compile(m.group(1))
            re.compile(m.group(2))
            self.assertNotRegex(t.lower(), "eb" + "ras|\\b" + "da" + "ni\\b", a)


class PesoAlArrancar(unittest.TestCase):
    def test_avisa_y_no_falla(self):
        with tempfile.TemporaryDirectory() as cfg, tempfile.TemporaryDirectory() as proy:
            open(os.path.join(cfg, "CLAUDE.md"), "w").write("# Ficha\n" + "x" * 45_000 + "\n")
            open(os.path.join(proy, "CLAUDE.md"), "w").write("# Proyecto\nhola\n")
            p = subprocess.run([sys.executable, os.path.join(METODO, "scripts", "claude-md-check.py"), proy],
                               capture_output=True, text=True, encoding="utf-8", env=dict(os.environ, CLAUDE_CONFIG_DIR=cfg, PYTHONUTF8="1"))
            self.assertEqual(p.returncode, 0, p.stdout)
            self.assertIn("Peso al arrancar", p.stdout)
            self.assertIn("ficha personal", p.stdout)
            self.assertIn("No se borra nada", p.stdout)


if __name__ == "__main__":
    unittest.main()
