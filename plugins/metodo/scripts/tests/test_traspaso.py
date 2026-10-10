"""Tests de claude-md-check.py y contexto-reanudar.py (plugin metodo) y de su enchufe en arrancar/cerrar-check.

    python3 -m unittest discover -s plugins/metodo/scripts/tests -v
Todo en carpetas temporales; nunca se toca la configuración real.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

AQUI = Path(__file__).resolve().parent
S = AQUI.parent
MDCHECK, HOOK, ARRANCAR, CERRAR = (S / n for n in ("claude-md-check.py", "contexto-reanudar.py", "arrancar-check.py", "cerrar-check.py"))
GENV = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")

REANUDAR = """<!-- cierre {fecha}-prueba · lo escribe /metodo:cerrar -->
═══ PARTE A — CONTRATO ═══
ROL: asesor SECRETO-CONTRATO
═══ PARTE B — ESTADO ═══
Seguimos con la prueba.
Hecho esta sesión: algo.
De qué veníamos hablando: del presupuesto de la obra y si funcionó el cálculo.
PENDIENTES:
1. paso uno
Modelo para abrir: sonnet
Arrancá con /arrancar y confirmá: "Leí el estado."
"""


def git(cwd, *a):
    subprocess.run(["git", "-C", str(cwd), *a], check=True, capture_output=True, env=GENV)


def correr(script, *args, stdin=None, cwd=None):
    r = subprocess.run([sys.executable, str(script), *map(str, args)], input=stdin, capture_output=True, text=True,
                       timeout=60, cwd=cwd, env=dict(os.environ, CLAUDE_CONFIG_DIR=tempfile.gettempdir() + "/sin-config-xyz"))
    return r.returncode, r.stdout + r.stderr


class Base(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory()
        self.addCleanup(self._t.cleanup)
        self.raiz = Path(self._t.name).resolve()
        self.p = self.raiz / "mi proyecto con espacios"   # espacios a propósito
        self.p.mkdir()


class MdCheck(Base):
    def test_sin_claude_md(self):
        rc, out = correr(MDCHECK, self.p)
        self.assertEqual(rc, 0)
        self.assertIn("no hay en esta carpeta", out)

    def test_carpeta_inexistente(self):
        rc, out = correr(MDCHECK, self.raiz / "nada")
        self.assertEqual(rc, 0)
        self.assertIn("no existe", out)

    def test_chico_sin_git(self):
        (self.p / "CLAUDE.md").write_text("# hola\n| a | b |\n|---|---|\n| x | y |\n", encoding="utf-8")
        rc, out = correr(MDCHECK, self.p)
        self.assertEqual(rc, 0, out)
        self.assertIn("✓ CLAUDE.md pesa", out)

    def test_enorme_es_aviso_no_error(self):
        (self.p / "CLAUDE.md").write_text("linea de relleno de texto\n" * 5000, encoding="utf-8")
        rc, out = correr(MDCHECK, self.p)
        self.assertEqual(rc, 0, out)
        self.assertIn("no es un error", out)

    def test_fila_larga_falla(self):
        (self.p / "CLAUDE.md").write_text("| tema | " + "x" * 400 + " |\n", encoding="utf-8")
        rc, out = correr(MDCHECK, self.p)
        self.assertEqual(rc, 1, out)
        self.assertIn("✗", out)

    def test_puntero_roto_falla_y_bueno_pasa(self):
        (self.p / "docs").mkdir()
        (self.p / "docs" / "MAPA-DELEGACION-DETALLE.md").write_text("## Clave buena\n", encoding="utf-8")
        (self.p / "CLAUDE.md").write_text("| a | ver → doc, buscar «Clave buena» |\n", encoding="utf-8")
        self.assertEqual(correr(MDCHECK, self.p)[0], 0)
        (self.p / "CLAUDE.md").write_text("| a | ver → doc, buscar «No existe» |\n", encoding="utf-8")
        rc, out = correr(MDCHECK, self.p)
        self.assertEqual(rc, 1, out)

    def test_bytes_raros(self):
        (self.p / "CLAUDE.md").write_bytes(b"# t\xff\xfe\n| a | b |\n")
        self.assertEqual(correr(MDCHECK, self.p)[0], 0)

    def test_subcarpeta_de_repo_usa_el_de_la_raiz(self):
        git(self.p, "init", "-q", "-b", "main")
        (self.p / "CLAUDE.md").write_text("# raiz\n", encoding="utf-8")
        sub = self.p / "sub dir"
        sub.mkdir()
        rc, out = correr(MDCHECK, sub)
        self.assertIn("✓ CLAUDE.md pesa", out)

    def test_worktree(self):
        git(self.p, "init", "-q", "-b", "main")
        (self.p / "CLAUDE.md").write_text("# x\n", encoding="utf-8")
        git(self.p, "add", "CLAUDE.md")
        git(self.p, "commit", "-q", "-m", "x")
        wt = self.raiz / "copia aparte"
        git(self.p, "worktree", "add", "-q", "-b", "rama/x", str(wt))
        rc, out = correr(MDCHECK, wt)
        self.assertEqual(rc, 0, out)
        self.assertIn("✓ CLAUDE.md pesa", out)


class Hook(Base):
    def hook(self, cwd, source="startup", raw=None):
        return correr(HOOK, stdin=raw if raw is not None else json.dumps({"cwd": str(cwd), "source": source}))

    def escribir(self, fecha="2026-10-09", donde="REANUDAR.md"):
        f = self.p / donde
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(REANUDAR.format(fecha=fecha), encoding="utf-8")

    def test_sin_reanudar_no_imprime(self):
        rc, out = self.hook(self.p)
        self.assertEqual((rc, out), (0, ""))

    def test_reanudar_bueno_muestra_parte_b_sin_contrato(self):
        import datetime
        self.escribir(fecha=datetime.date.today().isoformat())
        rc, out = self.hook(self.p)
        self.assertEqual(rc, 0)
        self.assertIn("De qué veníamos hablando", out)
        self.assertIn("paso uno", out)
        self.assertNotIn("SECRETO-CONTRATO", out)
        self.assertNotIn("Arrancá con", out)
        self.assertNotIn("puede estar viejo", out)

    def test_reanudar_viejo_avisa(self):
        self.escribir(fecha="2020-01-01")
        self.assertIn("puede estar viejo", self.hook(self.p)[1])

    def test_ubicacion_alternativa(self):
        self.escribir(donde=".claude/prompts/REANUDAR.md")
        self.assertIn("paso uno", self.hook(self.p)[1])

    def test_sin_parte_b_no_imprime(self):
        (self.p / "REANUDAR.md").write_text("<!-- cierre 2026-10-09-x -->\nsolo texto\n", encoding="utf-8")
        self.assertEqual(self.hook(self.p), (0, ""))

    def test_stdin_basura_no_rompe(self):
        for raw in ("", "no es json", "[1,2]", "null"):
            rc, _ = self.hook(self.p, raw=raw)
            self.assertEqual(rc, 0)

    def test_resume_y_clear_no_hacen_nada(self):
        self.escribir()
        for src in ("resume", "clear"):
            self.assertEqual(self.hook(self.p, source=src), (0, ""))

    def test_reanudar_binario_no_rompe(self):
        (self.p / "REANUDAR.md").write_bytes(b"\xff\xfe\x00\x01" * 100)
        self.assertEqual(self.hook(self.p)[0], 0)

    def test_reanudar_enorme_se_recorta(self):
        (self.p / "REANUDAR.md").write_text("═══ PARTE B — ESTADO ═══\n" + "linea\n" * 500, encoding="utf-8")
        out = self.hook(self.p)[1]
        self.assertIn("recortado", out)
        self.assertLess(len(out.splitlines()), 50)


class Enchufe(Base):
    def test_arrancar_y_cerrar_corren_md_check_en_carpeta_rara(self):
        (self.p / "CLAUDE.md").write_text("# x\n", encoding="utf-8")
        for script in (ARRANCAR, CERRAR):
            rc, out = correr(script, self.p)
            self.assertIn("CLAUDE.md pesa", out, out)

    def test_md_check_roto_no_rompe_el_cierre(self):
        # carpeta sin CLAUDE.md y sin git: ambos checks siguen y dicen qué pasa
        for script in (ARRANCAR, CERRAR):
            rc, out = correr(script, self.p)
            self.assertIn("CLAUDE.md", out, out)

    def test_cerrar_verificacion_propia_y_ramas_mergeadas(self):
        git(self.p, "init", "-q", "-b", "main")
        (self.p / "a.txt").write_text("a", encoding="utf-8")
        git(self.p, "add", "a.txt")
        git(self.p, "commit", "-q", "-m", "a")
        git(self.p, "branch", "vieja/rama")
        rc, out = correr(CERRAR, self.p)
        self.assertIn("MANUAL (verificación propia)", out)
        self.assertIn("vieja/rama", out)
        self.assertNotIn("main,", out)

    def test_rama_sin_main_ni_master_no_rompe(self):
        git(self.p, "init", "-q", "-b", "trunk")
        (self.p / "a.txt").write_text("a", encoding="utf-8")
        git(self.p, "add", "a.txt")
        git(self.p, "commit", "-q", "-m", "a")
        rc, out = correr(CERRAR, self.p)
        self.assertIn("MANUAL (verificación propia)", out)
        self.assertNotIn("Traceback", out)


if __name__ == "__main__":
    unittest.main()
