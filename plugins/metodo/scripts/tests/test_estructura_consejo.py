#!/usr/bin/env python3
"""test_estructura_consejo.py — el revisor da consejos pensados (qué, cuánto cuesta, qué conviene), no órdenes mecánicas."""
from contextlib import redirect_stdout
from datetime import date, timedelta
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import estructura
import estructura_consejo as C

os.environ.setdefault("METODO_SIN_REFRESCO", "1")   # `semanal` lanza la medición del número «X de N» en segundo plano: no en las pruebas (en Windows deja la carpeta temporal tomada)


def _caja(td, lineas_claude=3, codigo=False):
    caja = Path(td) / "mi_proyecto"
    caja.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=caja, check=True)
    subprocess.run(["git", "remote", "add", "origin", "https://github.com/org/repo.git"], cwd=caja, check=True)
    (caja / "CLAUDE.md").write_text("# Proyecto\n" + "\n".join(f"Regla número {i}." for i in range(lineas_claude)) + "\n", encoding="utf-8")
    (caja / ".claude").mkdir()
    (caja / ".claude" / "settings.json").write_text("{}\n", encoding="utf-8")
    (caja / ".gitignore").write_text(".env\n.claude/settings.local.json\nCLAUDE.local.md\n", encoding="utf-8")
    if codigo:
        (caja / "package.json").write_text("{}\n", encoding="utf-8")
    return caja


def _aviso(caja):
    buf = io.StringIO()
    with redirect_stdout(buf):
        estructura.comando_revisar(carpeta_arg=str(caja), nivel_arg="proyecto", aviso=True)
    return buf.getvalue()


class Base(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.td = self._td.name
        self._env = os.environ.get("CLAUDE_PLUGIN_DATA")
        os.environ["CLAUDE_PLUGIN_DATA"] = str(Path(self.td) / "estado")
        iso = date.today().isocalendar()
        (Path(self.td) / "estado").mkdir()
        (Path(self.td) / "estado" / "semana-revisar.txt").write_text(f"{iso[0]}-W{iso[1]:02d}", encoding="utf-8")

    def tearDown(self):
        if self._env is None:
            os.environ.pop("CLAUDE_PLUGIN_DATA", None)
        else:
            os.environ["CLAUDE_PLUGIN_DATA"] = self._env
        self._td.cleanup()


class TestConsejos(unittest.TestCase):
    def test_cuatro_lineas_de_mas_no_mandan_a_hacer_nada(self):
        c = C.consejo("R3", "CLAUDE.md tiene 200 líneas o más (204 líneas)", {})
        self.assertEqual(c["accion"], "nada")
        self.assertNotIn("mover", c["conviene"].lower().split("nada")[0])

    def test_muchas_lineas_piden_sacar_antes_que_mover(self):
        c = C.consejo("R3", "CLAUDE.md tiene 200 líneas o más (420 líneas)", {})
        self.assertEqual(c["accion"], "sesion")
        self.assertIn("repetido, viejo o contradictorio", c["conviene"])
        self.assertIn("`paths:`", c["conviene"])        # rules solo para un tema o carpeta puntual
        self.assertIn("tokens en cada sesión", c["cuesta"])

    def test_documentos_vivos_solo_si_hay_codigo(self):
        self.assertEqual(C.consejo("R12", "faltan los documentos vivos: docs/PRD.md", {"codigo": False})["accion"], "nada")
        self.assertEqual(C.consejo("R12", "faltan los documentos vivos: docs/PRD.md", {"codigo": True})["accion"], "sesion")
        self.assertEqual(C.consejo("R16", "siguen sin completar: docs/PRD.md", {"codigo": False})["accion"], "nada")

    def test_pocas_rutas_rotas_no_valen_una_sesion(self):
        self.assertEqual(C.consejo("R13", "CLAUDE.md cita 2 ruta(s) que no existen: a, b", {})["accion"], "al_pasar")
        self.assertEqual(C.consejo("R13", "CLAUDE.md cita 6 ruta(s) que no existen: a, b", {})["accion"], "sesion")

    def test_todo_consejo_dice_las_tres_cosas(self):
        for r in ("R3", "R7", "R10", "R12", "R13", "R14", "R15", "R16", "R17", "R18", "R19", "R20", "R21", "R99"):
            c = C.consejo(r, "CLAUDE.md tiene 200 líneas o más (400 líneas)" if r == "R3" else f"{r} cita 5 ruta(s) tiene 5 conteo", {"codigo": True})
            for campo in ("que", "cuesta", "conviene"):
                self.assertTrue(c[campo].strip(), (r, campo))

    def test_agente_inexistente_rinde_mas_que_lineas_de_mas(self):
        a = C.consejo("R15", "CLAUDE.md nombra agente(s) que no existen: pm-x", {})
        b = C.consejo("R3", "CLAUDE.md tiene 200 líneas o más (300 líneas)", {})
        self.assertGreater(a["rinde"], b["rinde"])


class TestNecesitaDocumentos(Base):
    def test_caja_de_paso_no_los_necesita_y_la_de_codigo_si(self):
        paso = _caja(self.td)
        self.assertFalse(estructura.necesita_documentos(paso))
        (paso / "scripts").mkdir()
        for i in range(8):   # scripts sueltos no hacen un producto
            (paso / "scripts" / f"s{i}.py").write_text("x = 1\n", encoding="utf-8")
        self.assertFalse(estructura.necesita_documentos(paso))
        for i in range(5):   # código de aplicación a un nivel
            (paso / "backend").mkdir(exist_ok=True)
            (paso / "backend" / f"m{i}.py").write_text("x = 1\n", encoding="utf-8")
        self.assertTrue(estructura.necesita_documentos(paso))


class TestMemoria(unittest.TestCase):
    def test_no_repite_antes_de_una_semana_ni_mas_de_tres_veces(self):
        hoy = date(2026, 10, 17)
        m = {}
        self.assertTrue(C.toca_mostrar("R3:x", 300, m, hoy))
        C.anotar_visto("R3:x", 300, m, hoy)
        self.assertFalse(C.toca_mostrar("R3:x", 300, m, hoy + timedelta(days=3)))
        self.assertTrue(C.toca_mostrar("R3:x", 300, m, hoy + timedelta(days=8)))
        C.anotar_visto("R3:x", 300, m, hoy + timedelta(days=8))
        C.anotar_visto("R3:x", 300, m, hoy + timedelta(days=16))
        self.assertFalse(C.toca_mostrar("R3:x", 300, m, hoy + timedelta(days=30)))   # 3 veces: se calla

    def test_lo_descartado_vuelve_solo_si_empeora(self):
        hoy = date(2026, 10, 17)
        m = {"R3:x": {"descartado": hoy.isoformat(), "medida": 300}}
        self.assertFalse(C.toca_mostrar("R3:x", 320, m, hoy + timedelta(days=60)))
        self.assertTrue(C.toca_mostrar("R3:x", 500, m, hoy + timedelta(days=60)))     # creció más de la mitad
        self.assertTrue(C.toca_mostrar("R3:x", 300, m, hoy + timedelta(days=200)))    # a los 6 meses vuelve a preguntar


class TestAviso(Base):
    def test_cuatro_lineas_de_mas_el_aviso_calla(self):
        caja = _caja(self.td, lineas_claude=203)
        self.assertEqual(_aviso(caja).strip(), "")

    def test_aviso_con_costo_arreglo_y_sesion_secundaria(self):
        caja = _caja(self.td, lineas_claude=420)
        sal = _aviso(caja)
        self.assertIn("[R3:mi_proyecto]", sal)
        self.assertIn("Cuesta dejarlo así:", sal)
        self.assertIn("Conviene: mirá si hay algo repetido, viejo o contradictorio", sal)
        self.assertIn("no lo arregles en esta sesión", sal)
        self.assertIn("start_session", sal)
        self.assertNotIn("estructura.py arreglar", sal)

    def test_el_mismo_aviso_no_se_repite_en_la_sesion_siguiente(self):
        caja = _caja(self.td, lineas_claude=420)
        self.assertIn("R3", _aviso(caja))
        self.assertEqual(_aviso(caja).strip(), "")

    def test_descartar_lo_calla_y_el_brief_lo_omite(self):
        caja = _caja(self.td, lineas_claude=420)
        self.assertEqual(estructura.comando_descartar("R3:mi_proyecto"), 0)
        self.assertEqual(_aviso(caja).strip(), "")
        buf = io.StringIO()
        with redirect_stdout(buf):
            estructura.comando_brief(str(caja))
        self.assertIn("Nada que valga una sesión", buf.getvalue())
        self.assertEqual(estructura.comando_descartar("sin-clave"), 1)

    def test_brief_trae_costo_arreglo_y_limites(self):
        caja = _caja(self.td, lineas_claude=420)
        buf = io.StringIO()
        with redirect_stdout(buf):
            estructura.comando_brief(str(caja))
        t = buf.getvalue()
        for frag in ("Cuesta dejarlo así", "Qué conviene", "Hecho cuando", "sin push", "NO lo hagas"):
            self.assertIn(frag, t)

    def test_ordena_por_lo_que_mas_rinde(self):
        caja = _caja(self.td, lineas_claude=300)
        (caja / "CLAUDE.md").write_text((caja / "CLAUDE.md").read_text(encoding="utf-8") + "Delegá en `pm-inventado-xyz`.\n", encoding="utf-8")
        sal = _aviso(caja)
        if "R15" in sal:   # R15 solo existe si hay agentes instalados contra los que comparar
            self.assertLess(sal.index("R15"), sal.index("R3"))


class TestSemanal(Base):
    def test_la_pasada_semanal_solo_atiende_la_carpeta_de_la_sesion(self):
        raiz = Path(self.td) / "Proyectos"
        raiz.mkdir()
        mia = raiz / "mia"
        mia.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=mia, check=True)
        ajena = raiz / "ajena"
        ajena.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=ajena, check=True)
        (ajena / "CLAUDE.md").write_text("# Ajena\n" + "Regla.\n" * 420, encoding="utf-8")
        (Path(self.td) / "estado" / "semana-revisar.txt").unlink()   # primera sesión de la semana: recorre todo
        buf = io.StringIO()
        with redirect_stdout(buf):
            estructura.comando_revisar(carpeta_arg=str(mia), aviso=True, raiz_arg=str(raiz))
        sal = buf.getvalue()
        self.assertNotIn("[R3:ajena]", sal)                 # no manda a arreglar lo de otra carpeta
        self.assertIn("en otras carpetas", sal)

    def test_copias_de_terceros_no_dan_consejos(self):
        c = Path(self.td) / "sandbox" / "repo-ajeno"
        c.mkdir(parents=True)
        self.assertEqual(estructura._consejos_de([("aviso", "R3", "x", "CLAUDE.md tiene 200 líneas o más (900 líneas)", c, "proyecto")]), [])


if __name__ == "__main__":
    unittest.main()
