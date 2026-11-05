"""Tests de privacidad.py (plugin metodo): lista de sensibles y aviso por planillas. Solo biblioteca estándar."""
import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path

AQUI = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("privacidad", str(AQUI.parent / "privacidad.py"))
P = importlib.util.module_from_spec(spec)
sys.modules["privacidad"] = P
spec.loader.exec_module(P)


class TestSensibles(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="priv-")).resolve()
        self.addCleanup(lambda: __import__("shutil").rmtree(str(self.tmp), True))
        self.previo = os.environ.get("METODO_SENSIBLES")
        self.addCleanup(self._volver)

    def _volver(self):
        if self.previo is None:
            os.environ.pop("METODO_SENSIBLES", None)
        else:
            os.environ["METODO_SENSIBLES"] = self.previo

    def _lista(self, texto):
        f = self.tmp / "s.txt"
        f.write_text(texto, encoding="utf-8")
        os.environ["METODO_SENSIBLES"] = str(f)

    def test_sin_archivo_o_vacio_no_hay_sensibles(self):
        os.environ["METODO_SENSIBLES"] = str(self.tmp / "nada.txt")
        self.assertEqual(P.leer_sensibles(), [])
        self._lista("# solo comentarios\n\n")
        self.assertIsNone(P.carpeta_sensible(self.tmp / "x"))

    def test_dentro_igual_y_contenedora(self):
        self._lista("%s | contrato\n" % (self.tmp / "a" / "b"))
        self.assertIn("contrato", P.carpeta_sensible(self.tmp / "a" / "b"))
        self.assertIn("contrato", P.carpeta_sensible(self.tmp / "a" / "b" / "c"))
        self.assertIn("contiene", P.carpeta_sensible(self.tmp / "a"))
        self.assertIsNone(P.carpeta_sensible(self.tmp / "a" / "bb"))        # prefijo de texto no es carpeta
        self.assertIsNone(P.carpeta_sensible(self.tmp / "otra"))

    def test_tilde_y_mayusculas(self):
        self._lista("~/Proyectos/Cliente | contrato\n")
        self.assertIn("contrato", P.carpeta_sensible(Path.home() / "proyectos" / "CLIENTE" / "app"))
        self.assertIn("contrato", P.carpeta_sensible("~/proyectos/cliente/app"))

    def test_acentos_nfd_y_nfc_son_la_misma_carpeta(self):
        import unicodedata
        nfc = unicodedata.normalize("NFC", "Nómina")
        nfd = unicodedata.normalize("NFD", "Nómina")
        self._lista("%s | contrato\n" % (self.tmp / nfc))
        self.assertIn("contrato", P.carpeta_sensible(self.tmp / nfd / "x"))

    def test_archivo_ilegible_falla_cerrado_y_ruta_suelta_va_a_casa(self):
        f = self.tmp / "s.txt"
        f.write_text("x | y\n", encoding="utf-8")
        os.environ["METODO_SENSIBLES"] = str(f)
        f.chmod(0)
        self.addCleanup(lambda: f.chmod(0o600))
        if os.access(f, os.R_OK):
            self.skipTest("este usuario lee igual (root)")
        self.assertIsNotNone(P.carpeta_sensible(self.tmp / "cualquiera"))
        f.chmod(0o600)
        f.write_text("Clientes/acme | c\n", encoding="utf-8")
        self.assertEqual(P.leer_sensibles()[0][0], (Path.home() / "Clientes" / "acme").resolve())

    def test_csv_en_latin1_y_nombres_tecnicos_sin_falsos_avisos(self):
        (self.tmp / "ventas.csv").write_bytes("nombre,tel\xe9fono\n".encode("latin-1"))
        (self.tmp / "cv_results.csv").write_text("score\n", encoding="utf-8")
        (self.tmp / "leaderboard.csv").write_text("score\n", encoding="utf-8")
        hall = P.planillas_con_personas(["ventas.csv", "cv_results.csv", "leaderboard.csv"], raiz=self.tmp)
        self.assertEqual(hall, ["ventas.csv"])

    def test_planillas(self):
        (self.tmp / "contactos.csv").write_text("x\n", encoding="utf-8")
        (self.tmp / "ventas.csv").write_text("nombre,Teléfono\n", encoding="utf-8")
        (self.tmp / "stock.csv").write_text("sku,cantidad\n", encoding="utf-8")
        hall = P.planillas_con_personas(["contactos.csv", "ventas.csv", "stock.csv", "codigo.py", "sueldos.xlsx"], raiz=self.tmp)
        self.assertEqual(hall, ["contactos.csv", "ventas.csv", "sueldos.xlsx"])
        self.assertIn("datos de personas", P.aviso_planillas(hall))
        self.assertIsNone(P.aviso_planillas([]))


if __name__ == "__main__":
    unittest.main()
