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
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace", timeout=30)


@unittest.skipIf(ES_WINDOWS, "reglas.py es para Mac")
class ReglasTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cfg = Path(self.tmp.name) / "config"
        self.cfg.mkdir()
        self.ficha = self.cfg / "CLAUDE.md"

    def tearDown(self):
        self.tmp.cleanup()

    def test_plantilla_tiene_24_reglas(self):
        primera = PLANTILLA.read_text(encoding="utf-8").splitlines()[0]
        self.assertEqual(primera, "# Las 25 reglas del método")
        self.assertIn("\n19. **Una pieza por función; buscar antes de crear.**", PLANTILLA.read_text(encoding="utf-8"))

    def test_bloque_viejo_entre_marcas_se_actualiza_sin_tocar_lo_propio(self):
        viejo = [reglas.INI, "# Las 18 reglas del método", "", "1. regla vieja", reglas.FIN]
        propio_arriba = ["# Mi ficha", "Lo mío de arriba: no se toca.", ""]
        propio_abajo = ["", "## Lo mío de abajo", "- tampoco se toca"]
        self.ficha.write_text("\n".join(propio_arriba + viejo + propio_abajo) + "\n", encoding="utf-8")

        r = correr(self.cfg)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Reglas del método actualizadas a 24 ✓", r.stdout)

        texto = self.ficha.read_text(encoding="utf-8").splitlines()
        self.assertEqual(texto[:3], propio_arriba)
        self.assertEqual(texto[-3:], propio_abajo)
        a, b = texto.index(reglas.INI), texto.index(reglas.FIN)
        self.assertEqual(texto[a:b + 1], reglas.bloque_nuevo(PLANTILLA))
        self.assertIn("# Las 25 reglas del método", texto)
        self.assertTrue(any(l.startswith("19. **Una pieza por función") for l in texto))
        self.assertEqual(len(list(self.cfg.glob("CLAUDE.md.antes-reglas-*"))), 1)

        # segunda vez: no cambia nada y no dice nada
        r2 = correr(self.cfg)
        self.assertNotIn("Reglas del método", r2.stdout)   # ya al día: no repite el aviso (la línea del nombre sí sale en cada arranque)
        self.assertEqual(len(list(self.cfg.glob("CLAUDE.md.antes-reglas-*"))), 1)

    def test_ficha_sin_reglas_las_agrega_al_final(self):
        self.ficha.write_text("Lo mío.\n", encoding="utf-8")
        r = correr(self.cfg)
        self.assertIn("Reglas del método agregadas (24) ✓", r.stdout)
        texto = self.ficha.read_text(encoding="utf-8")
        self.assertTrue(texto.startswith("Lo mío.\n"))
        self.assertIn(reglas.INI, texto)

    def test_marcas_incompletas_no_toca(self):
        original = "Lo mío.\n" + reglas.INI + "\n# Las 18 reglas del método\n"
        self.ficha.write_text(original, encoding="utf-8")
        r = correr(self.cfg)
        self.assertIn("✗", r.stdout)
        self.assertEqual(self.ficha.read_text(encoding="utf-8"), original)


@unittest.skipIf(ES_WINDOWS, "reglas.py es para Mac")
class NombreTest(unittest.TestCase):
    def ficha(self, texto):
        d = tempfile.TemporaryDirectory(); self.addCleanup(d.cleanup)
        f = Path(d.name) / "CLAUDE.md"
        if texto is not None:
            f.write_text(texto, encoding="utf-8")
        return f

    def test_campo_presente(self):
        self.assertIn("Quién habla: Ana.", reglas.aviso_nombre(self.ficha("# Yo\nLlamame: Ana\n")))

    def test_campo_con_negritas_y_vineta(self):
        self.assertIn("Quién habla: Fer.", reglas.aviso_nombre(self.ficha("- **Llamame:** Fer\n")))

    def test_nombre_formal_distinto_usa_el_preferido(self):
        s = reglas.aviso_nombre(self.ficha("- **Nombre:** Fernando Raimondi\n- **Llamame:** Fer\n"))
        self.assertIn("Quién habla: Fer.", s)
        self.assertNotIn("Fernando", s)

    def test_solo_nombre_formal_no_alcanza_pregunta(self):
        s = reglas.aviso_nombre(self.ficha("- **Nombre:** Fernando Raimondi\nMe llamo: Fernando\n"))
        self.assertIn("Falta cómo querés que te llame", s)
        self.assertIn("¿cómo querés que te llame?", s)

    def test_campo_ausente_pregunta_una_vez_y_guarda(self):
        f = self.ficha("# Mi ficha\n")
        self.assertIn("Falta cómo querés que te llame", reglas.aviso_nombre(f))
        with open(f, "a", encoding="utf-8") as fh:      # lo que hace Claude después de preguntar
            fh.write("Llamame: Lu\n")
        reglas.sincronizar(PLANTILLA, f)                # el bloque de reglas se reescribe: la línea sobrevive
        self.assertIn("Quién habla: Lu.", reglas.aviso_nombre(f))
        self.assertNotIn("Falta", reglas.aviso_nombre(f))

    def test_varias_personas_pregunta_quien_es(self):
        s = reglas.aviso_nombre(self.ficha("Personas en esta computadora: Ana, Luis y Marta\n"))
        self.assertIn("trabajan 3 (Ana, Luis, Marta)", s)
        self.assertIn("Preguntá quién es ANTES", s)

    def test_sin_ficha_avisa_que_falta(self):
        self.assertIn("Falta cómo querés que te llame", reglas.aviso_nombre(self.ficha(None)))

    def test_el_ejemplo_dentro_del_bloque_no_cuenta(self):
        s = reglas.aviso_nombre(self.ficha("\n".join([reglas.INI, "# Las 25 reglas del método", "Llamame: Ejemplo", reglas.FIN]) + "\n"))
        self.assertIn("Falta cómo querés que te llame", s)

    def test_arranque_completo_imprime_la_linea(self):
        d = tempfile.TemporaryDirectory(); self.addCleanup(d.cleanup)
        (Path(d.name) / "CLAUDE.md").write_text("Llamame: Ana\n", encoding="utf-8")
        r = correr(d.name)
        self.assertIn("Quién habla: Ana.", r.stdout)



if __name__ == "__main__":
    unittest.main()
