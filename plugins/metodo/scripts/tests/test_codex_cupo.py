"""codex-cupo: lee el cupo de Codex del plan gratis (ventana de 30 días) y de Plus (5 h y 7 días)."""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "codex-cupo"
CIERRE = ',"credits":{"has_credits":false,"unlimited":false,"balance":null}}}'


def linea(primary, secondary):
    def v(w):
        return "null" if w is None else '{"used_percent":%s,"window_minutes":%d,"resets_at":1}' % w
    return '{"payload":{"rate_limits":{"limit_id":"codex","primary":%s,"secondary":%s%s\n' % (v(primary), v(secondary), CIERRE)


@unittest.skipIf(os.name == "nt", "codex-cupo es un script de bash")
class TestCodexCupo(unittest.TestCase):
    def correr(self, *lineas):
        with tempfile.TemporaryDirectory() as home:
            if lineas:
                d = Path(home, ".codex", "sessions", "2026", "10", "25")
                d.mkdir(parents=True)
                (d / "r.jsonl").write_text("".join(lineas), encoding="utf-8")
            r = subprocess.run(["bash", str(SCRIPT)], env={"HOME": home, "PATH": os.environ["PATH"]},
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return r.returncode, r.stdout

    def test_plan_gratis_ventana_de_30_dias(self):
        self.assertEqual(self.correr(linea(("100.0", 43200), None))[0], 2)
        self.assertEqual(self.correr(linea(("10.0", 43200), None))[0], 0)

    def test_plus_toma_la_ventana_mas_llena(self):
        codigo, texto = self.correr(linea(("5.0", 300), ("75.0", 10080)))
        self.assertEqual(codigo, 1)
        self.assertIn("75%", texto)
        self.assertEqual(self.correr(linea(("95.0", 300), ("10.0", 10080)))[0], 2)
        self.assertEqual(self.correr(linea(("0.0", 300), ("0.0", 10080)))[0], 0)

    def test_usa_la_ultima_linea_del_registro(self):
        # el cupo vuelve a bajar al renovarse la ventana: manda la línea más nueva, no la más alta
        self.assertEqual(self.correr(linea(("99.0", 300), None), linea(("2.0", 300), None))[0], 0)

    def test_sin_registros_o_sin_dato(self):
        self.assertIn("sin registros", self.correr()[1])
        codigo, texto = self.correr(linea(None, None))
        self.assertEqual(codigo, 0)
        self.assertIn("desconocido", texto)

    def tope(self, fecha):
        return ('{"payload":{"message":"You\'ve hit your usage limit. Upgrade to Pro or try again at %s."}}\n' % fecha)

    def test_tope_de_5_horas_sin_porcentajes(self):
        # Plus agotado: el registro trae las ventanas vacías y el aviso real está en el mensaje
        vacio = linea(None, None)
        codigo, texto = self.correr(vacio, self.tope("Dec 31st, 2099 3:30 AM"))
        self.assertEqual(codigo, 2)
        self.assertIn("agotado hasta el 31/12 03:30", texto)
        # un tope viejo ya renovado no frena
        self.assertEqual(self.correr(vacio, self.tope("Jan 1st, 2020 3:30 AM"))[0], 0)
        # si después del tope hay una medición nueva, manda la nueva
        self.assertEqual(self.correr(self.tope("Dec 31st, 2099 3:30 AM"), linea(("2.0", 300), None))[0], 0)


if __name__ == "__main__":
    unittest.main()
