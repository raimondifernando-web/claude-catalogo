"""Pruebas de claves-en-historial.py: encuentra claves viejas y NUNCA imprime un valor completo."""
import os
import subprocess
import sys
import tempfile
import unittest

SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "claves-en-historial.py")
# Valores falsos armados en tiempo de ejecución: el repo no contiene ningún literal con forma de clave.
AWS = "AKIA" + "IOSFODNN7" + "EXAMPLE"
PASS = "prueba-clave" + "-vieja-98765"
STRIPE = "sk_" + "test_" + "PRUEBA0123456789abcdef"


def git(cwd, *args):
    subprocess.run(["git", "-C", cwd, *args], check=True, capture_output=True,
                   env={**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
                        "GIT_COMMITTER_EMAIL": "t@t"})


def correr(cwd):
    return subprocess.run([sys.executable, SCRIPT, cwd], capture_output=True, text=True)


class ClavesEnHistorial(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        git(self.d, "init", "-q")
        with open(os.path.join(self.d, "config.py"), "w") as f:
            f.write(f'AWS = "{AWS}"\nDB_PASSWORD = "{PASS}"\nPAGOS = "{STRIPE}"\n')
        git(self.d, "add", "."); git(self.d, "commit", "-q", "-m", "viejo")
        with open(os.path.join(self.d, "config.py"), "w") as f:
            f.write('import os\nAWS = os.environ["AWS"]\nPAGOS = "{}"\n'.format(STRIPE))   # la de pagos sigue
        git(self.d, "add", "."); git(self.d, "commit", "-q", "-m", "sin claves")

    def test_encuentra_y_enmascara(self):
        r = correr(self.d)
        self.assertEqual(r.returncode, 0)
        for completo in (AWS, PASS, STRIPE):
            self.assertNotIn(completo, r.stdout + r.stderr, "no debe imprimir un valor completo")
        self.assertIn("tipo=clave-aws", r.stdout)
        self.assertIn("valor=AKIA…", r.stdout)
        self.assertIn("tipo=asignacion-secreta", r.stdout)
        self.assertIn("RESUMEN: 3 valor(es)", r.stdout)

    def test_sigue_en_head(self):
        r = correr(self.d)
        aws = [l for l in r.stdout.splitlines() if "tipo=clave-aws" in l][0]
        pagos = [l for l in r.stdout.splitlines() if "tipo=clave-stripe-o-similar" in l][0]
        self.assertIn("sigue_en_el_commit_actual=no", aws)
        self.assertIn("sigue_en_el_commit_actual=sí", pagos)

    def test_no_es_repo(self):
        vacio = tempfile.mkdtemp()
        r = correr(vacio)
        self.assertEqual(r.returncode, 2)
        self.assertIn("SIN-HISTORIAL", r.stdout)

    def test_no_modifica_nada(self):
        antes = subprocess.run(["git", "-C", self.d, "status", "--porcelain"], capture_output=True, text=True).stdout
        correr(self.d)
        despues = subprocess.run(["git", "-C", self.d, "status", "--porcelain"], capture_output=True, text=True).stdout
        self.assertEqual(antes, despues)


if __name__ == "__main__":
    unittest.main()
