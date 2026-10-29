#!/usr/bin/env python3
"""Pruebas de scripts/agentes-etiqueta.py (control de etiqueta de proyecto en agentes). Corridas: python3 -m unittest discover -s scripts/tests
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "agentes-etiqueta.py"
MARC = "ACME\nACME[ _-]?CORP\ncs:Zeta\npm-(finanzas|bicho)\ngeneral: pm-empresa\n!Zeta Perez\n"


def correr(agentes: dict[str, str], publico=False, marc=MARC, env=None):
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        (d / "a").mkdir()
        for n, t in agentes.items():
            (d / "a" / f"{n}.md").write_text(t)
        (d / "m.txt").write_text(marc)
        cmd = [sys.executable, str(SCRIPT), "--agentes", str(d / "a" / "*.md"), "--marcadores", str(d / "m.txt")]
        if publico:
            cmd.append("--publico")
        r = subprocess.run(cmd, capture_output=True, text=True, env={**os.environ, "MARCADORES_PROYECTO": "", **(env or {})})
        return r.returncode, r.stdout


def ag(nombre, desc, cuerpo=""):
    return f'---\nname: {nombre}\ndescription: "{desc}"\nmodel: sonnet\n---\n{cuerpo}\n'


class TestPrivado(unittest.TestCase):
    def test_sin_tag_con_marcador_falla(self):
        rc, out = correr({"seo": ag("seo", "Especialista SEO", "Trabajamos para ACME con Odoo")})
        self.assertEqual(rc, 1); self.assertIn("seo:", out)

    def test_marcador_en_description_sin_tag_falla(self):
        rc, _ = correr({"seo": ag("seo", "SEO de ACME CORP")})
        self.assertEqual(rc, 1)

    def test_con_tag_pasa(self):
        rc, _ = correr({"seo": ag("seo", "[ACME] SEO de la marca", "Datos de ACME, ACME CORP")})
        self.assertEqual(rc, 0)

    def test_generico_limpio_pasa(self):
        rc, _ = correr({"seo": ag("seo", "Especialista SEO", "Auditá un sitio de cualquier pyme")})
        self.assertEqual(rc, 0)

    def test_falso_positivo_fer_y_palabras_parecidas(self):
        cuerpo = "Ejemplo: Fer pide un informe. Una ferretería vende acmex y ACMES no existe. Zeta Perez es un ejemplo."
        rc, out = correr({"g": ag("g", "Generico", cuerpo)})
        self.assertEqual(rc, 0, out)

    def test_zeta_sensible_a_mayusculas(self):
        rc, _ = correr({"g": ag("g", "Generico", "hola Zeta")})
        self.assertEqual(rc, 1)
        rc, _ = correr({"g": ag("g", "Generico", "zetas y zeta")})
        self.assertEqual(rc, 0)

    def test_pm_de_proyecto_sin_tag_falla_aunque_no_nombre_nada(self):
        rc, out = correr({"pm-acme": ag("pm-acme", "PM de Acme", "")})
        self.assertEqual(rc, 1); self.assertIn("PM sin tag", out)

    def test_pm_con_tag_pasa_y_pm_general_pasa(self):
        rc, _ = correr({"pm-acme": ag("pm-acme", "[ACME] PM de Acme"), "pm-empresa": ag("pm-empresa", "Jefe general")})
        self.assertEqual(rc, 0)

    def test_nombre_propio_del_pm_no_cuenta_como_marcador(self):
        rc, _ = correr({"pm-bicho": ag("pm-bicho", "[Bicho] PM del Bicho", "")})
        self.assertEqual(rc, 0)

    def test_generico_nombra_pm_de_proyecto_falla(self):
        rc, _ = correr({"g": ag("g", "Generico", "derivá a pm-finanzas")})
        self.assertEqual(rc, 1)

    def test_id_de_cuenta_publicitaria_siempre_falla(self):
        rc, _ = correr({"g": ag("g", "Generico", "cuenta act_12345678")}, marc="")
        self.assertEqual(rc, 1)

    def test_tag_mal_formado_no_cuenta(self):
        rc, _ = correr({"g": ag("g", "[] Algo", "ACME")})
        self.assertEqual(rc, 1)


class TestEvasiones(unittest.TestCase):
    def test_description_en_bloque_con_tag_pasa(self):
        rc, out = correr({"s": '---\nname: s\ndescription: >\n  [ACME] Especialista\n  seguido\nmodel: sonnet\n---\nACME\n'})
        self.assertEqual(rc, 0, out)

    def test_description_en_bloque_sin_tag_falla(self):
        rc, _ = correr({"s": '---\nname: s\ndescription: |\n  Especialista\nmodel: sonnet\n---\nACME\n'})
        self.assertEqual(rc, 1)

    def test_crlf(self):
        rc, out = correr({"s": ag("s", "[ACME] SEO", "ACME").replace("\n", "\r\n")})
        self.assertEqual(rc, 0, out)

    def test_marcador_compuesto_con_guion_y_mayusculas(self):
        for cuerpo in ("ACME-prod", "cliente-acme", "ACT_12345678"):
            rc, _ = correr({"g": ag("g", "Generico", cuerpo)}, marc="ACME\n")
            self.assertEqual(rc, 1 if "act" not in cuerpo.lower() else 0, cuerpo)
        rc, _ = correr({"g": ag("g", "Generico", "ACT_12345678")}, marc="")
        self.assertEqual(rc, 0)  # los ids son en minúscula (act_…): el patrón es sensible a mayúsculas a propósito

    def test_pm_general_con_prefijo_comun_no_se_confunde(self):
        rc, _ = correr({"g": ag("g", "Generico", "derivá a pm-marketing-pyme")}, marc="pm-(marketing)(?![-\\w])\n")
        self.assertEqual(rc, 0)
        rc, _ = correr({"g": ag("g", "Generico", "derivá a pm-marketing")}, marc="pm-(marketing)(?![-\\w])\n")
        self.assertEqual(rc, 1)

    def test_nombre_de_archivo_es_marcador(self):
        rc, _ = correr({"acme": ag("acme", "Generico", "texto")})
        self.assertEqual(rc, 1)

    def test_sin_lista_ignora_comentarios(self):
        rc, out = correr({"g": ag("g", "Generico")}, publico=True, marc="# solo un comentario\n\n")
        self.assertIn("sin lista", out)


class TestPublico(unittest.TestCase):
    def test_tag_de_proyecto_en_publico_falla(self):
        rc, out = correr({"seo": ag("seo", "[TU-EMPRESA] SEO")}, publico=True)
        self.assertEqual(rc, 1); self.assertIn("público", out)

    def test_publico_no_imprime_el_marcador(self):
        rc, out = correr({"g": ag("g", "Generico", "datos de ACME")}, publico=True)
        self.assertEqual(rc, 1); self.assertNotIn("ACME", out)

    def test_publico_con_lista_en_variable(self):
        rc, _ = correr({"g": ag("g", "Generico", "cliente Zeta")}, publico=True, marc="", env={"MARCADORES_PROYECTO": "Zeta"})
        self.assertEqual(rc, 1)

    def test_publico_limpio_pasa(self):
        rc, _ = correr({"g": ag("g", "Generico", "texto")}, publico=True)
        self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()
