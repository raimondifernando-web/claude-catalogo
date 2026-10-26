"""guias.py: pega el texto de las skills nombradas al pedido para Codex/Gemini. Config falsa; nunca toca IAs reales.
Correr: python3 -m unittest discover -s plugins/metodo/scripts/tests"""
import os
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_delegar as TD  # noqa: E402

AQUI = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AQUI))
import guias  # noqa: E402


class Base(TD.BaseDelegar):
    def skill(self, nombre, cuerpo, extra_fm=""):
        d = self.tmp / "config" / "skills" / nombre
        d.mkdir(parents=True, exist_ok=True)
        (d / "SKILL.md").write_text("---\nname: %s\ndescription: x\n%s---\n%s\n" % (nombre, extra_fm, cuerpo), encoding="utf-8")


class TestGuias(Base):
    def test_adjunta_la_nombrada_sin_el_encabezado(self):
        self.skill("mi-guia", "PASO UNO: hacelo bien")
        t, adj, av = guias.adjuntar("Hacé X con la skill mi-guia", repo=str(self.tmp))
        self.assertEqual(adj, ["mi-guia"])
        self.assertIn("PASO UNO", t)
        self.assertNotIn("description: x", t)
        self.assertTrue(t.rstrip().endswith("Hacé X con la skill mi-guia"))

    def test_extra_y_nombre_repetido_una_sola_vez(self):
        self.skill("mi-guia", "CUERPO")
        t, adj, _ = guias.adjuntar("usá /mi-guia", extra=["mi-guia"], repo=str(self.tmp))
        self.assertEqual(adj, ["mi-guia"])
        self.assertEqual(t.count("CUERPO"), 1)

    def test_sin_skill_nombrada_el_pedido_no_cambia(self):
        self.skill("mi-guia", "CUERPO")
        t, adj, av = guias.adjuntar("hacé el schema del archivo", repo=str(self.tmp))
        self.assertEqual((t, adj, av), ("hacé el schema del archivo", [], []))

    def test_skill_inexistente_avisa(self):
        t, adj, av = guias.adjuntar("hola", extra=["no-existe"], repo=str(self.tmp))
        self.assertEqual(adj, [])
        self.assertTrue(any("no existe" in a for a in av))

    def test_de_la_sesion_de_claude_no_se_adjunta(self):
        self.skill("cerrar", "CIERRE")
        t, adj, av = guias.adjuntar("después /cerrar", repo=str(self.tmp))
        self.assertEqual(adj, [])
        self.assertNotIn("CIERRE", t)

    def test_con_forma_de_clave_no_se_adjunta(self):
        self.skill("rara", "token: " + "A" * 40)
        t, adj, av = guias.adjuntar("usá /rara", repo=str(self.tmp))
        self.assertEqual(adj, [])
        self.assertTrue(any("forma de clave" in a for a in av))

    def test_avisa_si_usa_conectores(self):
        self.skill("con-mcp", "Llamá a mcp__notion__buscar")
        _, adj, av = guias.adjuntar("usá /con-mcp", repo=str(self.tmp))
        self.assertEqual(adj, ["con-mcp"])
        self.assertTrue(any("conectores" in a for a in av))

    def test_topes(self):
        self.skill("larga", "x" * 20000)
        t, adj, av = guias.adjuntar("usá /larga", repo=str(self.tmp))
        self.assertEqual(adj, ["larga"])
        self.assertLess(len(t.encode()), guias.TOPE_UNA + 1000)
        self.assertTrue(any("recortó" in a for a in av))

    def test_apagado(self):
        self.skill("mi-guia", "CUERPO")
        os.environ["GUIAS_OFF"] = "1"
        self.assertEqual(guias.adjuntar("usá /mi-guia", repo=str(self.tmp))[1], [])


@unittest.skipIf(TD.ES_WINDOWS, "scripts falsos de bash/sh")
class TestDeLaPuntaALaPunta(Base):
    def test_delegar_a_codex_con_pedido_que_nombra_una_skill_llega_con_la_guia(self):
        self.skill("mi-guia", "REGLA ESPECIAL: usá tabs")
        self.codex_falso()
        repo = self.crear_repo_git("repo-guia")
        cod, out, err = self.correr("desarrollo", str(repo), "Arreglá el formato (skill mi-guia)")
        self.assertEqual(cod, 0, err)
        recibido = (self.tmp / "codex_stdin.txt").read_text(encoding="utf-8")
        self.assertIn("REGLA ESPECIAL: usá tabs", recibido)
        self.assertIn("Arreglá el formato", recibido)
        self.assertIn("Guías adjuntas: mi-guia", out)

    def test_opcion_skills(self):
        self.skill("otra", "OTRA GUIA")
        self.codex_falso()
        repo = self.crear_repo_git("repo-guia2")
        cod, out, err = self.correr("desarrollo", str(repo), "hacé algo", "--skills", "otra")
        self.assertEqual(cod, 0, err)
        self.assertIn("OTRA GUIA", (self.tmp / "codex_stdin.txt").read_text(encoding="utf-8"))

    def test_como_programa_por_stdin(self):
        self.skill("mi-guia", "DESDE CLI")
        env = dict(os.environ, CLAUDE_CONFIG_DIR=str(self.tmp / "config"))
        r = subprocess.run([sys.executable, str(AQUI / "guias.py"), "adjuntar", "--skills", "mi-guia"], input="pedido", capture_output=True, text=True, env=env)
        self.assertEqual(r.returncode, 0)
        self.assertIn("DESDE CLI", r.stdout)
        self.assertIn("Guías adjuntas: mi-guia", r.stderr)


if __name__ == "__main__":
    unittest.main()
