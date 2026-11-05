"""Datos de Producir en RADAR.yaml (paso 3 de las reglas multi-IA): `via` en todo plan, marcas de investigar y filas nuevas.
Solo biblioteca estándar, SIN red. Correr desde la raíz del repo:
    python3 -m unittest discover -s plugins/metodo/scripts/tests -p 'test_radar_producir_datos.py' -v
"""
import unittest

from test_radar import R, YAML_REAL

VIAS = {"comando", "conector", "api", "web"}


def real():
    return R.yaml_cargar(YAML_REAL.read_text(encoding="utf-8"))


class DatosProducir(unittest.TestCase):
    def test_todo_plan_trae_via_valida(self):
        for c in real()["categorias"]:
            for p in c["planes"]:
                self.assertIn(p.get("via"), VIAS, f"{c['id']} plan {p['plan']} sin via válida")

    def test_filas_de_producir_apuntan_a_categorias_existentes(self):
        r = real()
        ids = {c["id"] for c in r["categorias"]}
        filas = {f["id"]: f for f in r["ruteo_claude"]["producir"]}
        self.assertEqual(set(filas), {"imagen", "video", "voz", "transcribir", "investigar"})
        for f in filas.values():
            self.assertIn(f["categoria"], ids)
            self.assertTrue(f["palabras"])

    def test_investigar_marca_modo_rapido_con_citas_y_modo_a_fondo(self):
        c = next(c for c in real()["categorias"] if c["id"] == "investigacion_web")
        con_citas = [p for p in c["planes"] if p.get("citas")]
        con_fondo = [p for p in c["planes"] if p.get("fondo")]
        self.assertEqual([p["via"] for p in con_citas], ["conector"])
        self.assertTrue(con_fondo)


if __name__ == "__main__":
    unittest.main()
