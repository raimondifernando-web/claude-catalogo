"""Tests de arrancar-check.py y cerrar-check.py (plugin metodo). Solo biblioteca estándar + git, sin red.

Correr desde la raíz del repo:
    python3 -m unittest discover -s plugins/metodo/scripts/tests -v

Cada test arma una carpeta de proyecto temporal con su propio repo y su propia carpeta de configuración
(CLAUDE_CONFIG_DIR). Nunca se toca la configuración real.
"""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

AQUI = Path(__file__).resolve().parent
ARRANCAR = AQUI.parent / "arrancar-check.py"
CERRAR = AQUI.parent / "cerrar-check.py"

CIERRE = "<!-- cierre 2026-10-09-prueba · lo escribe /metodo:cerrar · lo lee /metodo:arrancar -->\n"
REANUDAR_OK = CIERRE + """═══ PARTE A — CONTRATO ═══
ROL: asesor del estudio
ALCANCE: presupuestos
═══ PARTE B — ESTADO ═══
Copia: carpeta única, sin copia
PENDIENTES (en este orden):
1. revisar el presupuesto
A VERIFICAR (si aplica): que exista la planilla
Arrancá con /arrancar y confirmá: "Leí el estado."
"""


def git(cwd, *a):
    subprocess.run(["git", "-C", str(cwd), *a], check=True, capture_output=True,
                   env=dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t",
                            GIT_COMMITTER_EMAIL="t@t"))


class ChecksTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name).resolve()
        self.proyecto = self.dir / "proyecto"
        self.proyecto.mkdir()
        self.config = self.dir / "config"
        self.config.mkdir()

    def correr(self, script, *args):
        env = dict(os.environ, CLAUDE_CONFIG_DIR=str(self.config))
        r = subprocess.run([sys.executable, str(script), *args], env=env, capture_output=True, text=True, timeout=60)
        return r.returncode, r.stdout

    def repo(self):
        git(self.proyecto, "init", "-q", "-b", "main")
        (self.proyecto / "REANUDAR.md").write_text(REANUDAR_OK, encoding="utf-8")
        git(self.proyecto, "add", "REANUDAR.md")
        git(self.proyecto, "commit", "-q", "-m", "cierre 2026-10-09-prueba")

    # ---- arrancar ----
    def test_arrancar_sin_reanudar_no_es_falla(self):
        rc, out = self.correr(ARRANCAR, str(self.proyecto))
        self.assertEqual(rc, 0, out)
        self.assertIn("sin contrato", out)
        self.assertIn("Arranque completo ✓", out)

    def test_arrancar_con_reanudar_y_a_verificar(self):
        self.repo()
        rc, out = self.correr(ARRANCAR, str(self.proyecto))
        self.assertEqual(rc, 0, out)
        self.assertIn("cierre 2026-10-09-prueba", out)
        self.assertIn("que exista la planilla", out)
        self.assertIn("MANUAL", out)

    def test_arrancar_reanudar_sin_fecha_falla(self):
        (self.proyecto / "REANUDAR.md").write_text("hola\n", encoding="utf-8")
        rc, out = self.correr(ARRANCAR, str(self.proyecto))
        self.assertEqual(rc, 1, out)
        self.assertIn("Falta:", out)

    def test_arrancar_rama_distinta_a_la_declarada_frena(self):
        self.repo()
        txt = CIERRE + f"Copia: {self.proyecto} · Rama: otra/rama\n"
        (self.proyecto / "REANUDAR.md").write_text(txt, encoding="utf-8")
        rc, out = self.correr(ARRANCAR, str(self.proyecto))
        self.assertEqual(rc, 1, out)
        self.assertIn("PARAR", out)

    def test_arrancar_rama_igual_a_la_declarada_pasa(self):
        self.repo()
        txt = CIERRE + f"Copia: {self.proyecto} · Rama: main\n"
        (self.proyecto / "REANUDAR.md").write_text(txt, encoding="utf-8")
        rc, out = self.correr(ARRANCAR, str(self.proyecto))
        self.assertEqual(rc, 0, out)
        self.assertIn("coinciden", out)

    def test_arrancar_lee_la_ultima_regla_del_metodo(self):
        cache = self.config / "plugins/cache/claude-catalogo/metodo/0.9.0/templates"
        cache.mkdir(parents=True)
        (cache / "REGLAS-DEL-METODO.md").write_text("1. uno\n2. dos\n21. veintiuno\n", encoding="utf-8")
        rc, out = self.correr(ARRANCAR, str(self.proyecto))
        self.assertIn("metodo 0.9.0 instalado · última regla numerada: 21", out)

    # ---- cerrar ----
    def test_cerrar_ok(self):
        self.repo()
        rc, out = self.correr(CERRAR, str(self.proyecto))
        self.assertIn("REANUDAR.md presente", out)
        self.assertIn("sin remoto", out)  # el repo de prueba no tiene remoto: eso es una falla real
        self.assertEqual(rc, 1, out)

    def test_cerrar_sin_reanudar_falla(self):
        rc, out = self.correr(CERRAR, str(self.proyecto))
        self.assertEqual(rc, 1, out)
        self.assertIn("REANUDAR.md", out)

    def test_cerrar_conteos_y_clave_sin_mostrar_el_valor(self):
        clave = "sk-" + "proj" + "X" * 30
        (self.proyecto / "REANUDAR.md").write_text(
            CIERRE + "Hay 12 archivos en la carpeta.\n" + f"clave={clave}\n", encoding="utf-8")
        rc, out = self.correr(CERRAR, str(self.proyecto))
        self.assertEqual(rc, 1, out)
        self.assertIn("líneas [2]", out)  # el conteo de memoria
        self.assertIn("clave", out)
        self.assertNotIn(clave, out)

    def test_cerrar_reanudar_largo_falla(self):
        (self.proyecto / "REANUDAR.md").write_text(CIERRE + "linea\n" * 80, encoding="utf-8")
        rc, out = self.correr(CERRAR, str(self.proyecto))
        self.assertEqual(rc, 1, out)
        self.assertIn("techo 60", out)

    def test_cerrar_cambios_sin_guardar_fallan(self):
        self.repo()
        (self.proyecto / "REANUDAR.md").write_text(REANUDAR_OK + "x\n", encoding="utf-8")
        rc, out = self.correr(CERRAR, str(self.proyecto))
        self.assertIn("sin guardar", out)
        self.assertIn(": REANUDAR.md", out)  # el nombre del primer archivo sale entero
        self.assertEqual(rc, 1, out)

    def test_cerrar_handoff_obligatorio_con_tres_archivos(self):
        self.repo()
        for n in "abc":
            (self.proyecto / f"{n}.txt").write_text(n, encoding="utf-8")
        git(self.proyecto, "add", "a.txt", "b.txt", "c.txt")
        git(self.proyecto, "commit", "-q", "-m", "tres")
        rc, out = self.correr(CERRAR, "2026-10-09-prueba", str(self.proyecto))
        self.assertIn("Falta el handoff", out)
        (self.proyecto / "handoffs").mkdir()
        (self.proyecto / "handoffs" / "2026-10-09-prueba.md").write_text("ok", encoding="utf-8")
        rc, out = self.correr(CERRAR, "2026-10-09-prueba", str(self.proyecto))
        self.assertIn("Handoff handoffs/2026-10-09-prueba.md presente", out)

    def test_cerrar_con_remoto_al_dia_pasa(self):
        self.repo()
        bare = self.dir / "remoto.git"
        subprocess.run(["git", "init", "-q", "--bare", str(bare)], check=True)
        git(self.proyecto, "remote", "add", "origin", str(bare))
        git(self.proyecto, "push", "-q", "-u", "origin", "main")
        rc, out = self.correr(CERRAR, str(self.proyecto))
        self.assertEqual(rc, 0, out)
        self.assertIn("Cierre completo ✓", out)

    def test_no_escriben_nada(self):
        self.repo()
        antes = sorted(p.name for p in self.proyecto.iterdir())
        self.correr(ARRANCAR, str(self.proyecto))
        self.correr(CERRAR, str(self.proyecto))
        self.assertEqual(antes, sorted(p.name for p in self.proyecto.iterdir()))


if __name__ == "__main__":
    unittest.main()
