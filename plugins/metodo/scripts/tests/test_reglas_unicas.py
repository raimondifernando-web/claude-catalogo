"""Pruebas de reglas-unicas.py: frena la regla repetida ANTES de guardarla y no estorba en lo demás.

Corre con CLAUDE_CONFIG_DIR en una carpeta temporal y con la carpeta de trabajo dentro de ella: nunca toca la ficha real.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "reglas-unicas.py"

REGLA = ("Antes de borrar algo que no está en el control de versiones leé su contenido completo, no solo la lista de "
         "nombres: si hay trabajo propio sin copia no lo borres y preguntá primero a la persona; lo regenerable como "
         "cachés y archivos temporales se borra sin preguntar, y siempre decí qué probaste y qué no.")


def correr(cfg, *args, entrada=None, cwd=None, extra_env=None):
    env = dict(os.environ, CLAUDE_CONFIG_DIR=str(cfg), HOME=str(cfg.parent))
    env.update(extra_env or {})
    return subprocess.run([sys.executable, str(SCRIPT), *args], input=entrada, env=env, cwd=str(cwd or cfg),
                          capture_output=True, text=True, encoding="utf-8")


def hook(cfg, archivo, contenido, herramienta="Write", **kw):
    h = {"tool_name": herramienta, "cwd": str(cfg), "tool_input": {"file_path": str(archivo), "content": contenido}}
    return correr(cfg, "hook", entrada=json.dumps(h), **kw)


class Base(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.cfg = Path(self.t.name) / ".claude"
        (self.cfg / "rules").mkdir(parents=True)
        (self.cfg / "rules" / "a.md").write_text("# A\n\n- " + REGLA + "\n", encoding="utf-8")

    def tearDown(self):
        self.t.cleanup()


class TestHook(Base):
    def test_frena_la_regla_copiada_en_otro_archivo(self):
        r = hook(self.cfg, self.cfg / "rules" / "b.md", "# B\n\n- " + REGLA + "\n")
        self.assertEqual(r.returncode, 2, r.stderr)
        self.assertIn("a.md", r.stderr)
        self.assertIn("UN solo lugar", r.stderr)

    def test_frena_aunque_cambien_el_formato_y_unas_palabras(self):
        v = REGLA.replace("leé su contenido completo", "leé su contenido entero").upper()
        r = hook(self.cfg, self.cfg / "CLAUDE.md", "| IX | " + v + " |\n")
        self.assertEqual(r.returncode, 2, r.stderr)

    def test_deja_pasar_un_puntero_corto(self):
        r = hook(self.cfg, self.cfg / "rules" / "b.md", "- Borrado seguro: ver rules/a.md (→ doc, buscar «borrar»)\n")
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_deja_pasar_una_regla_distinta(self):
        otra = ("Cuando el pedido menciona una carpeta del vault de Obsidian primero listá la carpeta y abrí dos notas "
                "hermanas para copiar el estilo del título y los enlaces, después contale a la persona dónde y con qué "
                "nombre vas a crear la nota y esperá su visto bueno antes de escribir nada en el vault.")
        r = hook(self.cfg, self.cfg / "rules" / "b.md", "- " + otra + "\n")
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_eco_a_proposito_pasa(self):
        r = hook(self.cfg, self.cfg / "rules" / "b.md", "- " + REGLA + " <!-- eco: la ficha del cliente la necesita entera -->\n")
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_archivo_que_no_es_de_reglas_no_se_mira(self):
        r = hook(self.cfg, self.cfg.parent / "notas.md", "- " + REGLA + "\n")
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_editar_sin_agregar_unidades_nuevas_pasa(self):
        a = self.cfg / "rules" / "a.md"
        h = {"tool_name": "Edit", "cwd": str(self.cfg), "tool_input": {"file_path": str(a), "old_string": "# A", "new_string": "# A renombrado"}}
        self.assertEqual(correr(self.cfg, "hook", entrada=json.dumps(h)).returncode, 0)

    def test_edit_que_agrega_la_copia_se_frena(self):
        b = self.cfg / "rules" / "b.md"
        b.write_text("# B\n\nTexto corto.\n", encoding="utf-8")
        h = {"tool_name": "Edit", "cwd": str(self.cfg), "tool_input": {"file_path": str(b), "old_string": "Texto corto.", "new_string": "- " + REGLA}}
        self.assertEqual(correr(self.cfg, "hook", entrada=json.dumps(h)).returncode, 2)

    def test_lo_que_ya_estaba_repetido_al_instalar_no_frena(self):
        (self.cfg / "rules" / "b.md").write_text("# B\n\n- " + REGLA + "\n", encoding="utf-8")     # ya repetida de antes
        r = hook(self.cfg, self.cfg / "rules" / "b.md", "# B\n\n- " + REGLA + "\n\n- Otra línea corta.\n")
        self.assertEqual(r.returncode, 0, r.stderr)                                                  # primera vez: crea la base sola
        self.assertTrue((self.cfg / "metodo" / "reglas-unicas-base.json").is_file())
        r = hook(self.cfg, self.cfg / "rules" / "c.md", "- " + REGLA + "\n")                          # pero una copia NUEVA sí frena
        self.assertEqual(r.returncode, 2, r.stderr)

    def test_error_propio_no_frena(self):
        r = correr(self.cfg, "hook", entrada="esto no es json")
        self.assertEqual(r.returncode, 0)

    def test_apagado_por_variable(self):
        r = hook(self.cfg, self.cfg / "rules" / "b.md", "- " + REGLA + "\n", extra_env={"REGLAS_UNICAS_OFF": "1"})
        self.assertEqual(r.returncode, 0)


class TestRevisar(Base):
    def test_lista_la_repetida_y_sale_1(self):
        (self.cfg / "rules" / "b.md").write_text("- " + REGLA + "\n", encoding="utf-8")
        r = correr(self.cfg, "revisar", "--cwd", str(self.cfg))
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("a.md", r.stdout)

    def test_limpio_sale_0(self):
        r = correr(self.cfg, "revisar", "--cwd", str(self.cfg))
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_base_deja_las_conocidas_sin_frenar(self):
        (self.cfg / "rules" / "b.md").write_text("- " + REGLA + "\n", encoding="utf-8")
        correr(self.cfg, "base", "--cwd", str(self.cfg))
        self.assertEqual(correr(self.cfg, "revisar", "--cwd", str(self.cfg)).returncode, 0)

    def test_el_bloque_del_metodo_cuenta_aparte_de_la_ficha(self):
        (self.cfg / "CLAUDE.md").write_text("# Yo\n\n<!-- reglas-del-metodo:inicio -->\n# Las 1 reglas\n1. " + REGLA +
                                            "\n<!-- reglas-del-metodo:fin -->\n", encoding="utf-8")
        r = correr(self.cfg, "revisar", "--cwd", str(self.cfg))
        self.assertEqual(r.returncode, 1, r.stdout)       # la regla del bloque ya vive en rules/a.md
        self.assertIn("reglas del método", r.stdout)


class TestAviso(Base):
    def test_primera_vez_calla_y_anota_la_base(self):
        (self.cfg / "rules" / "b.md").write_text("- " + REGLA + "\n", encoding="utf-8")        # repetida de antes
        r = correr(self.cfg, "aviso", "--cwd", str(self.cfg))
        self.assertEqual((r.returncode, r.stdout.strip()), (0, ""))
        self.assertTrue((self.cfg / "metodo" / "reglas-unicas-base.json").is_file())

    def test_avisa_una_repetida_nueva_y_despues_calla_una_semana(self):
        correr(self.cfg, "aviso", "--cwd", str(self.cfg))                                       # fija la base
        (self.cfg / "rules" / "c.md").write_text("- " + REGLA + "\n", encoding="utf-8")
        r = correr(self.cfg, "aviso", "--forzar", "--cwd", str(self.cfg))
        self.assertIn("escrita(s) en dos lugares", r.stdout)
        self.assertEqual(correr(self.cfg, "aviso", "--cwd", str(self.cfg)).stdout.strip(), "")  # misma semana: nada

    def test_avisa_la_ruta_rota(self):
        correr(self.cfg, "aviso", "--cwd", str(self.cfg))
        (self.cfg / "CLAUDE.md").write_text("Mirá `~/no-existe-reglas-unicas-xyz/doc.md` antes.\n", encoding="utf-8")
        r = correr(self.cfg, "aviso", "--forzar", "--cwd", str(self.cfg))
        self.assertIn("no-existe-reglas-unicas-xyz", r.stdout)

    def test_avisa_si_la_ficha_engorda(self):
        correr(self.cfg, "aviso", "--cwd", str(self.cfg))
        (self.cfg / "CLAUDE.md").write_text("x " * 3000, encoding="utf-8")
        r = correr(self.cfg, "aviso", "--forzar", "--cwd", str(self.cfg))
        self.assertIn("pesan", r.stdout)


if __name__ == "__main__":
    unittest.main()
