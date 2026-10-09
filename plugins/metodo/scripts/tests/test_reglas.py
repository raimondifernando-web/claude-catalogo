"""Pruebas de reglas.py: el bloque de reglas se pone al día solo y no toca lo propio del usuario.

Corre con CLAUDE_CONFIG_DIR apuntando a una carpeta temporal: nunca toca la ficha real.
"""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

AQUI = Path(__file__).resolve().parent
SCRIPT = AQUI.parent / "reglas.py"
PLANTILLA = AQUI.parent.parent / "templates" / "REGLAS-DEL-METODO.md"

sys.path.insert(0, str(AQUI.parent))
ES_WINDOWS = os.name == "nt"
if not ES_WINDOWS:   # reglas.py usa fcntl: el aviso que lo llama es solo para Mac
    import reglas  # noqa: E402


def correr(config_dir):
    env = dict(os.environ, CLAUDE_CONFIG_DIR=str(config_dir))
    env.pop("CLAUDE_PLUGIN_ROOT", None)
    return subprocess.run([sys.executable, str(SCRIPT), "sincronizar"], env=env,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=30)


@unittest.skipIf(ES_WINDOWS, "reglas.py es para Mac")
class ReglasTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cfg = Path(self.tmp.name) / "config"
        self.cfg.mkdir()
        self.ficha = self.cfg / "CLAUDE.md"

    def tearDown(self):
        self.tmp.cleanup()

    def test_plantilla_tiene_19_reglas(self):
        primera = PLANTILLA.read_text(encoding="utf-8").splitlines()[0]
        self.assertEqual(primera, "# Las 21 reglas del método")
        self.assertIn("\n19. **Una pieza por función; buscar antes de crear.**", PLANTILLA.read_text(encoding="utf-8"))

    def test_bloque_viejo_entre_marcas_se_actualiza_sin_tocar_lo_propio(self):
        viejo = [reglas.INI, "# Las 18 reglas del método", "", "1. regla vieja", reglas.FIN]
        propio_arriba = ["# Mi ficha", "Lo mío de arriba: no se toca.", ""]
        propio_abajo = ["", "## Lo mío de abajo", "- tampoco se toca"]
        self.ficha.write_text("\n".join(propio_arriba + viejo + propio_abajo) + "\n", encoding="utf-8")

        r = correr(self.cfg)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Reglas del método actualizadas a 21 ✓", r.stdout)

        texto = self.ficha.read_text(encoding="utf-8").splitlines()
        self.assertEqual(texto[:3], propio_arriba)
        self.assertEqual(texto[-3:], propio_abajo)
        a, b = texto.index(reglas.INI), texto.index(reglas.FIN)
        self.assertEqual(texto[a:b + 1], reglas.bloque_nuevo(PLANTILLA))
        self.assertIn("# Las 21 reglas del método", texto)
        self.assertTrue(any(l.startswith("19. **Una pieza por función") for l in texto))
        self.assertEqual(len(list(self.cfg.glob("CLAUDE.md.antes-reglas-*"))), 1)

        # segunda vez: no cambia nada y no dice nada
        r2 = correr(self.cfg)
        self.assertEqual(r2.stdout, "")
        self.assertEqual(len(list(self.cfg.glob("CLAUDE.md.antes-reglas-*"))), 1)

    def test_ficha_sin_reglas_las_agrega_al_final(self):
        self.ficha.write_text("Lo mío.\n", encoding="utf-8")
        r = correr(self.cfg)
        self.assertIn("Reglas del método agregadas (21) ✓", r.stdout)
        texto = self.ficha.read_text(encoding="utf-8")
        self.assertTrue(texto.startswith("Lo mío.\n"))
        self.assertIn(reglas.INI, texto)

    def test_marcas_incompletas_no_toca(self):
        original = "Lo mío.\n" + reglas.INI + "\n# Las 18 reglas del método\n"
        self.ficha.write_text(original, encoding="utf-8")
        r = correr(self.cfg)
        self.assertIn("✗", r.stdout)
        self.assertEqual(self.ficha.read_text(encoding="utf-8"), original)


if __name__ == "__main__":
    unittest.main()
