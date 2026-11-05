"""Ruteo por fila (`radar.py ruteo <fila> --si N ...`): niveles, cupo por ritmo, privacidad, `--sin`, `--subir`, Producir e investigar.
Cubre los casos de la prueba ciega de docs/2026-11-05-analisis-reglas-multi-ia.md que decide el PROGRAMA (los 10 de la Capa A y
las 6 de Producir). Los «atajos» (tipografía, color en un CSS, etapa con 15 tareas) los decide la sesión antes de llamar al
programa: acá se prueba su contraparte (nivel N1/N2 que daría el programa). Solo biblioteca estándar, SIN red. Correr desde la raíz:
    python3 -m unittest discover -s plugins/metodo/scripts/tests -p 'test_ruteo_filas.py' -v
"""
import contextlib
import io
import json
import os
import re
import tempfile
import time
import unittest
from pathlib import Path

from test_radar import R

RE_LINEA = re.compile(r"^Ruteo: .+/.+/.+ porque .+ · aviso: .+$")


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = Path(self.tmp.name)
        self.conf, self.cerebro = t / "conf", t / "cerebro"
        (self.conf / "metodo").mkdir(parents=True)
        self.cerebro.mkdir()
        self.sens = t / "carpeta-sensible"
        self.sens.mkdir()
        self.env = {"CLAUDE_CONFIG_DIR": str(self.conf), "CEREBRO_HOME": str(self.cerebro),
                    "RUTEO_DISPONIBLES": "Claude Code,Codex,Antigravity"}
        self._viejo = {k: os.environ.get(k) for k in self.env}
        os.environ.update(self.env)
        self.m = self.conf / "metodo"

    def tearDown(self):
        for k, v in self._viejo.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        self.tmp.cleanup()

    def escribir(self, nombre, texto):
        (self.m / nombre).write_text(texto, encoding="utf-8")

    def cupo(self, archivo, usado, dias_para_renovar=3.5, edad_h=0.0, formato="plano"):
        ahora = time.time()
        d = {"ts": ahora - edad_h * 3600}
        sub = {"pct": usado, "resets_at": ahora + dias_para_renovar * 86400}
        if formato == "plano":
            d.update(sub)
        else:
            d["seven_day"] = sub
        (self.cerebro / archivo).write_text(json.dumps(d), encoding="utf-8")

    def correr(self, *args):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            codigo = R.main(["ruteo", *args, "--json"])
        self.assertEqual(codigo, 0, buf.getvalue())
        return json.loads(buf.getvalue())

    def texto(self, *args):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            R.main(["ruteo", *args])
        return buf.getvalue().strip()


class Niveles(Base):
    def test_tabla_de_niveles(self):
        import radar_ruteo as RR
        esperado = {("N1", 0): "N1", ("N1", 1): "N1", ("N1", 2): "N2", ("N1", 3): "N2",
                    ("N2", 0): "N2", ("N2", 1): "N2", ("N2", 2): "N3", ("N2", 3): "N3",
                    ("N3", 0): "N2", ("N3", 1): "N3", ("N3", 3): "N3"}
        for (base, si), n in esperado.items():
            self.assertEqual(RR.nivel_de(base, si), n, (base, si))

    def test_subir_suma_un_nivel_con_tope_n3(self):
        import radar_ruteo as RR
        self.assertEqual(RR.nivel_de("N1", 0, subir=True), "N2")
        self.assertEqual(RR.nivel_de("N2", 1, subir=True), "N3")
        self.assertEqual(RR.nivel_de("N3", 3, subir=True), "N3")

    def test_esfuerzo_sigue_al_nivel(self):
        self.assertEqual(self.correr("explorar", "--si", "0")["esfuerzo"], "low")
        self.assertEqual(self.correr("implementar", "--si", "1")["esfuerzo"], "medium")
        self.assertEqual(self.correr("seguridad", "--si", "1")["esfuerzo"], "high")


class Cupo(Base):
    def test_ritmo_sobra_normal_escasea_agotada_y_sin_dato(self):
        import radar_ruteo as RR
        casos = [(10, 2, "sobra"), (36, 2.66, "normal"), (80, 3.5, "escasea"), (100, 3.5, "agotada")]
        for usado, dias, estado in casos:
            self.cupo("cupo-codex.json", usado, dias)
            self.assertEqual(RR.cupo_ritmo("codex")["estado"], estado, (usado, dias))
        self.cupo("cupo-codex.json", 10, 3.5, edad_h=30)
        self.assertEqual(RR.cupo_ritmo("codex")["estado"], "sin_dato")          # más de 24 horas
        self.cupo("cupo-codex.json", 100, -1)
        self.assertEqual(RR.cupo_ritmo("codex")["estado"], "sin_dato")          # la renovación ya pasó: no queda «agotada»
        (self.cerebro / "cupo-codex.json").write_text("{}", encoding="utf-8")
        self.assertEqual(RR.cupo_ritmo("codex")["estado"], "sin_dato")          # falta el % y la fecha
        (self.cerebro / "cupo-codex.json").unlink()
        self.assertEqual(RR.cupo_ritmo("codex")["estado"], "sin_dato")          # sin archivo

    def test_formato_con_ventanas_usa_la_semanal(self):
        import radar_ruteo as RR
        self.cupo("cupo-agy.json", 29, 2, formato="ventanas")
        self.assertEqual(RR.cupo_ritmo("antigravity")["estado"], "sobra")

    def test_cupo_sesion_reemplaza_la_cache_de_claude(self):
        import radar_ruteo as RR
        self.assertEqual(RR.parsear_cupo_sesion("36,2d")[0], 36.0)
        self.assertIsNone(RR.parsear_cupo_sesion("mucho"))
        self.assertIsNone(RR.parsear_cupo_sesion("150,2d"))
        r = self.correr("implementar", "--si", "1", "--cupo-sesion", "90,6d")   # H = 10 ÷ 85 → escasea
        self.assertEqual(r["ia"], "Codex")                                      # primera que no escasea
        r = self.correr("implementar", "--si", "1", "--cupo-sesion", "30,3d")
        self.assertEqual(r["ia"], "Claude Code")

    def test_n1_n2_no_implementar_va_al_plan_a_o_b_con_sobra(self):
        self.cupo("cupo-codex.json", 5, 2)                        # Codex sobra (plan B de escritura)
        r = self.correr("documentar", "--si", "0", "--cupo-sesion", "40,3d")
        self.assertEqual(r["ia"], "Codex")
        self.assertEqual(r["modelo"], "gpt-6.1-terra")
        self.assertEqual(r["esfuerzo"], "medium")

    def test_n3_toma_siempre_la_primera(self):
        self.cupo("cupo-codex.json", 1, 3.5)                      # Codex sobra, pero N3 no mira el cupo
        r = self.correr("seguridad", "--si", "2", "--cupo-sesion", "40,3d")
        self.assertEqual((r["ia"], r["modelo"], r["esfuerzo"]), ("Claude Code", "opus", "high"))

    def test_todas_escasean_toma_la_primera_con_aviso(self):
        os.environ["RUTEO_DISPONIBLES"] = "Claude Code,Codex"
        self.cupo("cupo-codex.json", 90, 6)
        r = self.correr("implementar", "--si", "1", "--cupo-sesion", "95,6d")
        self.assertEqual(r["ia"], "Claude Code")
        self.assertIn("cupo escaso", r["avisos"])

    def test_agotada_con_dato_vigente_se_saca(self):
        self.cupo("cupo-codex.json", 100, 3)
        r = self.correr("documentar", "--si", "0", "--cupo-sesion", "95,6d")
        self.assertNotEqual(r["ia"], "Codex")


class Privacidad(Base):
    def test_resumir_pdf_de_un_cliente_queda_en_la_sesion_sin_registro(self):
        r = self.correr("leer", "--si", "0", "--personas")
        self.assertEqual((r["ia"], r["modelo"], r["esfuerzo"]), ("Claude Code", "sonnet", "medium"))
        self.assertIn("sin registro", r["avisos"])

    def test_contrato_en_carpeta_sensible_n3_sin_registro(self):
        self.escribir("sensibles.txt", "%s | contrato de confidencialidad\n" % self.sens)
        r = self.correr("leer", "--si", "2", "--repo", str(self.sens / "sub"))
        self.assertEqual((r["ia"], r["modelo"], r["esfuerzo"]), ("Claude Code", "opus", "high"))
        self.assertIn("sin registro", r["avisos"])

    def test_con_registro_la_ia_registrada_si_es_candidata(self):
        self.escribir("no-entrena.txt", "Codex | 2026-11-05 | tilde puesto\n")
        self.cupo("cupo-codex.json", 5, 2)
        r = self.correr("documentar", "--si", "0", "--personas", "--cupo-sesion", "40,3d")
        self.assertEqual(r["ia"], "Codex")
        self.assertNotIn("sin registro", r["avisos"])

    def test_fuera_de_carpeta_sensible_no_filtra(self):
        self.escribir("sensibles.txt", "%s | contrato\n" % self.sens)
        self.cupo("cupo-codex.json", 5, 2)
        r = self.correr("documentar", "--si", "0", "--repo", self.tmp.name, "--cupo-sesion", "40,3d")
        self.assertEqual(r["ia"], "Codex")


class CasosDeLaPruebaCiega(Base):
    def test_programar_funcion_con_pruebas(self):
        r = self.correr("implementar", "--si", "0", "--edita", "--cupo-sesion", "40,3d")
        self.assertEqual((r["ia"], r["modelo"], r["esfuerzo"]), ("Claude Code", "sonnet", "medium"))

    def test_analisis_de_30_archivos_con_codex_agotado(self):
        self.cupo("cupo-codex.json", 100, 3)
        r = self.correr("planear", "--si", "2")
        self.assertEqual((r["ia"], r["modelo"], r["esfuerzo"], r["nivel"]), ("Claude Code", "opus", "high", "N3"))

    def test_cliente_sin_codex_ni_gemini(self):
        os.environ["RUTEO_DISPONIBLES"] = "Claude Code"
        r = self.correr("implementar", "--si", "1")
        self.assertEqual((r["ia"], r["modelo"], r["esfuerzo"]), ("Claude Code", "sonnet", "medium"))
        self.assertIn("cupo sin dato", r["avisos"])

    def test_sumar_importes_es_n1_y_la_plata_no_sube_el_modelo(self):
        r = self.correr("calcular", "--si", "1")
        self.assertEqual((r["nivel"], r["modelo"], r["esfuerzo"]), ("N1", "haiku", "low"))

    def test_cambios_chicos_dan_nivel_barato(self):
        self.assertEqual(self.correr("explorar", "--si", "0")["nivel"], "N1")

    def test_sin_ia_apta_cae_en_la_principal(self):
        self.escribir("principal.txt", "Claude Code\n")
        r = self.correr("implementar", "--si", "1", "--sin", "Claude Code")
        self.assertEqual(r["ia"], "Codex")
        os.environ["RUTEO_DISPONIBLES"] = "Claude Code"
        r = self.correr("implementar", "--si", "1", "--sin", "Claude Code")
        self.assertEqual(r["ia"], "Claude Code")                     # nadie más: la de la sesión

    def test_sin_saca_la_ia_y_subir_sube_el_nivel(self):
        r = self.correr("implementar", "--si", "1", "--sin", "Claude Code")
        self.assertNotEqual(r["ia"], "Claude Code")
        r = self.correr("implementar", "--si", "1", "--subir")
        self.assertEqual((r["nivel"], r["modelo"], r["esfuerzo"]), ("N3", "opus", "high"))


class Producir(Base):
    def setUp(self):
        super().setUp()
        self.escribir("herramientas.txt", "Adobe Firefly / Express (conector) | conector | imagen\n"
                      "Adobe Express (conector) | conector | video\n"
                      "Hugging Face | conector | imagen, voz\n"
                      "Perplexity (MCP oficial, desde una sesión de Claude) | conector | investigar\n")

    def test_imagen_para_un_posteo(self):
        r = self.correr("imagen")
        self.assertEqual((r["ia"], r["como"]), ("Adobe Firefly / Express (conector)", "conector"))
        self.assertIn("mejor: ChatGPT Images", r["avisos"])

    def test_video_y_voz_son_dos_elecciones(self):
        v = self.correr("video")
        self.assertEqual((v["ia"], v["como"]), ("Adobe Express (conector)", "conector"))
        self.assertIn("mejor: app web de Gemini", v["avisos"])
        o = self.correr("voz en off")
        self.assertEqual((o["ia"], o["como"]), ("Hugging Face", "conector"))
        self.assertTrue(any(a.startswith("mejor: API de ElevenLabs") for a in o["avisos"]))

    def test_transcribir_sin_herramienta_sale_manual_con_el_plan_a(self):
        r = self.correr("transcribir")
        self.assertEqual((r["ia"], r["modelo"], r["como"]), ("API de ElevenLabs", "Scribe v2", "manual"))

    def test_investigar_con_citas_y_a_fondo(self):
        r = self.correr("investigar")
        self.assertEqual((r["modelo"], r["como"]), ("perplexity_ask", "conector"))
        self.assertIn("tope 3", r["motivo"])
        f = self.correr("investigar", "--a-fondo")
        self.assertEqual(f["modelo"], "perplexity_research")
        self.assertIn("tope 1", f["motivo"])

    def test_banner_con_foto_y_nombre_de_un_cliente_da_ninguna(self):
        r = self.correr("imagen", "--personas")
        self.assertEqual(r["ia"], "ninguna")
        self.assertIn("sin registro", r["avisos"])

    def test_con_registro_la_herramienta_declarada_vale(self):
        self.escribir("no-entrena.txt", "Adobe Firefly / Express (conector) | 2026-11-05 | contrato\n")
        r = self.correr("imagen", "--personas")
        self.assertEqual(r["ia"], "Adobe Firefly / Express (conector)")

    def test_sin_archivo_de_herramientas_todo_sale_manual(self):
        (self.m / "herramientas.txt").unlink()
        r = self.correr("imagen")
        self.assertEqual(r["como"], "manual")

    def test_sin_pasa_a_la_siguiente(self):
        r = self.correr("imagen", "--sin", "Adobe Firefly / Express (conector)")
        self.assertEqual(r["ia"], "Hugging Face")


class RevisionIndependiente(Base):
    """Hallazgos de la revisión del 2026-11-05: texto libre, ids exactos, --sin y privacidad."""
    def test_sumar_importes_de_una_planilla_es_calcular_n1(self):
        r = self.correr("sumar importes de una planilla", "--si", "1")
        self.assertEqual((r["fila"], r["nivel"]), ("calcular", "N1"))

    def test_revisar_seguridad_de_un_script_toma_la_fila_mas_cuidadosa(self):
        r = self.correr("revisar seguridad de un script", "--si", "1")
        self.assertEqual((r["fila"], r["nivel"], r["modelo"]), ("seguridad", "N3", "opus"))

    def test_id_exacto_de_etapa_gana_a_producir(self):
        self.assertEqual(self.correr("planear", "--si", "1")["fila"], "planear")
        self.assertEqual(self.correr("implementar", "--si", "1")["fila"], "implementar")

    def test_a_fondo_ya_no_es_palabra_de_investigar(self):
        self.assertNotEqual(self.correr("planear a fondo la migración", "--si", "1")["fila"], "investigar")

    def test_sin_compara_nombres_enteros(self):
        self.escribir("herramientas.txt", "Adobe Firefly / Express (conector) | conector | imagen\n")
        self.assertEqual(self.correr("imagen", "--sin", "Adobe")["ia"], "Adobe Firefly / Express (conector)")

    def test_privacidad_mas_sin_nunca_cae_en_manual(self):
        self.escribir("no-entrena.txt", "Adobe Firefly / Express (conector) | 2026-11-05 | contrato\n")
        self.escribir("herramientas.txt", "Adobe Firefly / Express (conector) | conector | imagen\n")
        r = self.correr("imagen", "--personas", "--sin", "Adobe Firefly / Express (conector)")
        self.assertEqual((r["ia"], r["como"]), ("ninguna", ""))

    def test_sin_si_avisa_que_asumio_cero(self):
        self.assertIn("sin --si: se asumió 0", self.correr("implementar")["avisos"])

    def test_ruta_relativa_en_sensibles_se_ignora(self):
        import radar_ruteo as RR
        self.escribir("sensibles.txt", "relativa/carpeta | x\n%s | y\n" % self.sens)
        self.assertEqual(len(RR.leer_sensibles(self.m)), 1)

    def test_agotada_saca_a_codex_y_elige_otra(self):
        self.cupo("cupo-codex.json", 100, 3)
        r = self.correr("documentar", "--si", "0", "--cupo-sesion", "95,6d")
        self.assertEqual(r["ia"], "Claude Code")

    def test_bordes_del_ritmo(self):
        import radar_ruteo as RR
        ahora = 1_000_000.0
        for usado, dias, estado in ((50, 3.5, "normal"), (0, 3.5, "sobra"), (80, 3.5, "escasea"), (75, 3.5, "normal")):
            self.cupo("cupo-codex.json", usado, dias)
            d = json.loads((self.cerebro / "cupo-codex.json").read_text())
            d["ts"], d["resets_at"] = ahora, ahora + dias * 86400
            (self.cerebro / "cupo-codex.json").write_text(json.dumps(d))
            self.assertEqual(RR.cupo_ritmo("codex", ahora=ahora + 1)["estado"], estado, (usado, dias))


class Salida(Base):
    def test_la_linea_ruteo_se_conserva_para_el_freno(self):
        for fila in ("implementar --si 1", "imagen", "transcribir"):
            linea = self.texto(*fila.split())
            self.assertRegex(linea, RE_LINEA)
            self.assertTrue(R.RE_LINEA_RUTEO.search(linea))

    def test_json_trae_los_campos(self):
        r = self.correr("implementar", "--si", "1")
        for k in ("fila", "nivel", "ia", "modelo", "esfuerzo", "motivo", "avisos", "linea"):
            self.assertIn(k, r)

    def test_nunca_frena_si_el_programa_falla(self):
        import radar_ruteo as RR
        r = RR.resolver_seguro(R, {"ruteo_claude": "roto"}, "implementar")
        self.assertEqual((r["ia"], r["avisos"]), ("Claude Code", ["provisorio"]))

    def test_fila_desconocida_devuelve_2(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            self.assertEqual(R.main(["ruteo", "bailar el tango"]), 2)


if __name__ == "__main__":
    unittest.main()
