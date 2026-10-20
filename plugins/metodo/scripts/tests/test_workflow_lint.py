"""Tests de workflow-lint.py: las 5 reglas de «workflows baratos y silenciosos» (Mandamiento XXX), sin red.

Correr desde la raíz del repo:
    python3 -m unittest discover -s plugins/metodo/scripts/tests -p "test_workflow_lint.py" -v
"""
import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("workflow_lint", SCRIPTS / "workflow-lint.py")
wl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(wl)

BUENO = """name: x
on:
  pull_request:
    branches: [main]
concurrency:
  group: x-${{ github.ref }}
  cancel-in-progress: true
jobs:
  a:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - run: echo hola
"""


def reglas(texto, privado=True):
    return sorted({r for r, _ in wl.revisar(texto, privado)})


class T(unittest.TestCase):
    def test_bueno_pasa(self):
        self.assertEqual(reglas(BUENO), [])

    def test_sin_concurrencia_o_sin_cancelar(self):
        self.assertEqual(reglas(BUENO.replace("concurrency:", "xconc:")), ["concurrencia"])
        self.assertEqual(reglas(BUENO.replace("cancel-in-progress: true", "cancel-in-progress: false")), ["concurrencia"])

    def test_excepcion_con_motivo(self):
        ok = "# actions-ok: concurrencia escribe en el repo y no se puede cortar\n" + BUENO.replace("true", "false")
        self.assertEqual(reglas(ok), [])
        # sin motivo no vale
        self.assertEqual(reglas("# actions-ok: concurrencia\n" + BUENO.replace("true", "false")), ["concurrencia"])

    def test_so_solo_en_privados(self):
        mac = BUENO.replace("ubuntu-latest", "macos-latest")
        self.assertEqual(reglas(mac, privado=True), ["so"])
        self.assertEqual(reglas(mac, privado=False), [])
        self.assertEqual(reglas(BUENO.replace("ubuntu-latest", "${{ matrix.os }}") + "# x\n        os: [ubuntu-latest, windows-latest]\n"), ["so"])
        self.assertEqual(reglas(BUENO + "# usa macos-latest antes\n"), [])  # un comentario no cuenta

    def test_cron(self):
        base = BUENO.replace("pull_request:\n    branches: [main]", "schedule:\n    - cron: '%s' %s")
        self.assertEqual(reglas(base % ("0 9 * * *", "# 06:00 ART, refresca precios")), [])
        self.assertEqual(reglas(base % ("0 9 * * *", "")), ["cron"])                  # sin motivo
        self.assertEqual(reglas(base % ("*/10 * * * *", "# cada 10 min")), ["cron"])   # más seguido que cada hora
        self.assertEqual(reglas(base % ("0 */2 * * *", "# cada 2 h")), [])
        self.assertEqual(reglas("# actions-ok: cron monitoreo de caídas, no hay otro reloj\n" + base % ("*/10 * * * *", "# caídas")), [])
        self.assertEqual(wl.corridas_por_dia("*/15 * * * *"), 96)
        self.assertEqual(wl.corridas_por_dia("30 10 * * 1"), 1)
        self.assertEqual(wl.corridas_por_dia("0 8-18 * * 1-5"), 11)

    def test_timeout(self):
        self.assertEqual(reglas(BUENO.replace("    timeout-minutes: 5\n", "")), ["timeout"])

    def test_push_y_pull_request(self):
        dup = BUENO.replace("on:\n", "on:\n  push:\n")
        self.assertEqual(reglas(dup), ["push-pr"])
        filtrado = BUENO.replace("on:\n", "on:\n  push:\n    branches: [main]\n")
        self.assertEqual(reglas(filtrado), [])
        self.assertEqual(reglas(BUENO.replace("on:\n  pull_request:\n    branches: [main]", "on: [push, pull_request]")), ["push-pr"])
        solo_push = BUENO.replace("pull_request:\n    branches: [main]", "push:")
        self.assertEqual(reglas(solo_push), [])

    def test_hallazgos_de_la_revision(self):
        # so: un paso o artefacto que NOMBRA macos no es un runner; un comentario al final tampoco
        self.assertEqual(reglas(BUENO.replace("steps:\n", "steps:\n      - name: Build macos-tarball\n")), [])
        self.assertEqual(reglas(BUENO.replace("ubuntu-latest", "ubuntu-latest # antes macos-latest")), [])
        self.assertEqual(reglas(BUENO.replace("ubuntu-latest", "windows-2022")), ["so"])
        # concurrencia con expresión (main no se corta, los PR sí)
        self.assertEqual(reglas(BUENO.replace("true", "${{ github.ref != 'refs/heads/main' }}")), [])
        # timeout: el de un paso no reemplaza al del job
        sin_job = BUENO.replace("    timeout-minutes: 5\n    steps:\n      - run: echo hola", "    steps:\n      - run: echo hola\n        timeout-minutes: 5")
        self.assertEqual(reglas(sin_job), ["timeout"])
        # on con comentario, en lista, y branches con comodín
        self.assertEqual(reglas(BUENO.replace("on:\n", "on: # disparadores\n  push:\n")), ["push-pr"])
        self.assertEqual(reglas(BUENO.replace("on:\n  pull_request:\n    branches: [main]", "on:\n  - push\n  - pull_request")), ["push-pr"])
        self.assertEqual(reglas(BUENO.replace("on:\n", "on:\n  push:\n    branches: ['**']\n")), ["push-pr"])
        self.assertEqual(reglas(BUENO.replace("on:\n", "on:\n  push:\n    # branches\n")), ["push-pr"])
        # cron concentrado: cada 5 min durante una hora
        cron = BUENO.replace("pull_request:\n    branches: [main]", "schedule:\n    - cron: '*/5 14 * * *' # prueba")
        self.assertEqual(reglas(cron), ["cron"])

    def test_diff_sin_historia_falla_claro(self):
        with tempfile.TemporaryDirectory() as d:
            r = subprocess.run([sys.executable, str(SCRIPTS / "workflow-lint.py"), "--base", "0000000", "--head", "HEAD"],
                               cwd=d, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1)
            self.assertIn("no pude comparar", r.stdout)
            r = subprocess.run([sys.executable, str(SCRIPTS / "workflow-lint.py"), "--base", "--evil", "--head", "HEAD"],
                               cwd=d, capture_output=True, text=True)
            self.assertEqual(r.returncode, 2)  # argparse rechaza lo que parece una opción

    def test_modo_diff_y_codigo_de_salida(self):
        with tempfile.TemporaryDirectory() as d:
            def git(*a):
                return subprocess.run(["git", "-C", d, "-c", "user.email=t@t", "-c", "user.name=t", *a],
                                      capture_output=True, text=True, check=True).stdout.strip()
            git("init", "-q", "-b", "main")
            Path(d, "a.txt").write_text("x")
            git("add", "-A"); git("commit", "-qm", "b")
            base = git("rev-parse", "HEAD")
            wf = Path(d, ".github/workflows"); wf.mkdir(parents=True)
            (wf / "malo.yml").write_text(BUENO.replace("cancel-in-progress: true", "cancel-in-progress: false"))
            git("add", "-A"); git("commit", "-qm", "h")
            head = git("rev-parse", "HEAD")
            r = subprocess.run([sys.executable, str(SCRIPTS / "workflow-lint.py"), "--base", base, "--head", head],
                               cwd=d, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1, r.stdout)
            self.assertIn("malo.yml", r.stdout)
            r = subprocess.run([sys.executable, str(SCRIPTS / "workflow-lint.py"), "--todo"], cwd=d, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0)          # --todo es informe
            self.assertIn("concurrencia", r.stdout)


if __name__ == "__main__":
    unittest.main()
