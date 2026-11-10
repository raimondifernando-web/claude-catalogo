"""CANARIO, NO UNIR: falla solo en Windows para comprobar que el resumen `controles` frena la unión."""
import sys
import unittest


class CanarioWindows(unittest.TestCase):
    def test_rojo_solo_en_windows(self):
        self.assertNotEqual(sys.platform, "win32", "canario: Windows rojo a propósito")


if __name__ == "__main__":
    unittest.main()
