#!/usr/bin/env python3
"""test_estructura_molde.py — el molde completo: R22 (settings subido), R23-R26 y R28 (piezas de desarrollo), R27 (cabecera del PRD),
R16 (plantilla reconocida), `estructura.py remoto` (medir en GitHub) y que el bucle de orden NO cree los esqueletos solo."""
import io
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import date, timedelta
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import estructura as E  # noqa: E402
import estructura_orden as O  # noqa: E402


def _git(cwd, *a, check=True):
    return subprocess.run(["git", "-C", str(cwd), "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false", *a],
                          capture_output=True, text=True, check=check).stdout.strip()


CONTENIDO = '{"permissions": {"allow": ["Read"]}}\n'


def _caja(td, nombre="caja", codigo=False, settings="{}\n"):
    c = Path(td) / "proyectos" / nombre
    c.mkdir(parents=True)
    _git(c, "init", "-q", "-b", "main")
    (c / "CLAUDE.md").write_text("# Caja\n", encoding="utf-8")
    (c / ".claude").mkdir()
    (c / ".claude" / "settings.json").write_text(settings, encoding="utf-8")
    (c / ".gitignore").write_text(".env\n", encoding="utf-8")
    if codigo:
        (c / "package.json").write_text("{}\n", encoding="utf-8")
    return c


def _ids(hallazgos):
    return {r for _t, r, _m in hallazgos}


def _msg(hallazgos, regla):
    return [m for _t, r, m in hallazgos if r == regla]


class Entorno(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.td = self._td.name
        self._env = {k: os.environ.get(k) for k in ("GIT_CONFIG_GLOBAL", "CLAUDE_PLUGIN_DATA")}
        os.environ["CLAUDE_PLUGIN_DATA"] = str(Path(self.td) / "estado")

    def tearDown(self):
        for k, v in self._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        self._td.cleanup()

    def ignore_global(self, patron):
        """Simula la lista global de ignorados de la Mac de una persona."""
        lista = Path(self.td) / "ignore_global"
        lista.write_text(patron + "\n", encoding="utf-8")
        cfg = Path(self.td) / "gitconfig_global"
        cfg.write_text(f"[core]\n\texcludesFile = {lista.as_posix()}\n", encoding="utf-8")   # barras normales: también vale en Windows
        os.environ["GIT_CONFIG_GLOBAL"] = str(cfg)


class TestR22(Entorno):
    def test_settings_oculto_por_el_ignore_global_avisa_y_la_negacion_lo_arregla(self):
        self.ignore_global(".claude/settings.json")
        c = _caja(self.td, settings=CONTENIDO)
        h = E.revisar_caja(c, "proyecto")
        (m,) = _msg(h, "R22")
        self.assertIn("no está subido a GitHub", m)
        self.assertIn("global", m)
        # el arreglo documentado: la negación en el .gitignore de la caja le gana al ignore global, y entonces se puede subir
        (c / ".gitignore").write_text(".env\n!.claude/settings.json\n", encoding="utf-8")
        _git(c, "add", ".claude/settings.json", ".gitignore")   # sin -f: tiene que dejarlo entrar
        self.assertNotIn("R22", _ids(E.revisar_caja(c, "proyecto")))

    def test_settings_subido_no_avisa(self):
        c = _caja(self.td, settings=CONTENIDO)
        _git(c, "add", "-f", ".claude/settings.json")
        self.assertNotIn("R22", _ids(E.revisar_caja(c, "proyecto")))

    def test_settings_vacio_no_avisa_aunque_no_este_subido(self):
        self.ignore_global(".claude/settings.json")
        c = _caja(self.td)   # {}: no hay nada que compartir
        self.assertNotIn("R22", _ids(E.revisar_caja(c, "proyecto")))

    def test_sin_settings_no_dice_r22_sino_r4(self):
        c = _caja(self.td)
        (c / ".claude" / "settings.json").unlink()
        ids = _ids(E.revisar_caja(c, "proyecto"))
        self.assertIn("R4", ids)
        self.assertNotIn("R22", ids)

    def test_el_gitignore_nuevo_ya_trae_la_negacion(self):
        c = Path(self.td) / "nueva"
        c.mkdir()
        plan = {rel: cont for rel, cont, _ in E.plan_seguro(c, "proyecto")}
        self.assertIn("!.claude/settings.json", plan[".gitignore"])


class TestDesarrollo(Entorno):
    def test_sin_codigo_no_pide_piezas_de_desarrollo(self):
        c = _caja(self.td)
        self.assertEqual(E.revisar_desarrollo(c), [])

    def test_r23_con_codigo_pide_readme_arquitectura_flujo_y_claves(self):
        c = _caja(self.td, codigo=True)
        (m,) = _msg(E.revisar_desarrollo(c), "R23")
        for pieza in ("README.md", "docs/arquitectura.md", "docs/flujo-de-la-app.md", ".env.example"):
            self.assertIn(pieza, m)
        (c / "docs").mkdir()
        for rel in ("README.md", "docs/arquitectura.md", "docs/flujo-de-la-app.md", ".env.example"):
            (c / rel).write_text("x\n", encoding="utf-8")
        self.assertNotIn("R23", _ids(E.revisar_desarrollo(c)))

    def test_codigo_en_una_carpeta_tambien_cuenta(self):
        # la plataforma de finanzas tiene su código en servidor/, sin package.json ni src/
        c = _caja(self.td)
        (c / "servidor").mkdir()
        for i in range(5):
            (c / "servidor" / f"m{i}.py").write_text("x = 1\n", encoding="utf-8")
        self.assertFalse(E.tiene_codigo(c))
        self.assertTrue(E.hay_codigo_propio(c))
        self.assertIn("R23", _ids(E.revisar_desarrollo(c)))

    def test_el_codigo_de_una_caja_de_adentro_no_es_de_la_que_la_contiene(self):
        madre = _caja(self.td, nombre="madre")
        hija = madre / "hija"
        hija.mkdir()
        _git(hija, "init", "-q", "-b", "main")
        (hija / "Dockerfile").write_text("FROM x\n", encoding="utf-8")
        for i in range(6):
            (hija / f"m{i}.py").write_text("x = 1\n", encoding="utf-8")
        (hija / "tests").mkdir()
        (hija / "tests" / "test_a.py").write_text("x\n", encoding="utf-8")
        self.assertTrue(E.hay_codigo_propio(hija) and E.se_despliega(hija) and E.hay_pruebas(hija))
        self.assertFalse(E.hay_codigo_propio(madre))
        self.assertFalse(E.se_despliega(madre))
        self.assertFalse(E.hay_pruebas(madre))
        self.assertEqual(E.revisar_desarrollo(madre), [])

    def test_r24_pruebas_y_como_correrlas(self):
        c = _caja(self.td, codigo=True)
        self.assertIn("no se encontraron pruebas", _msg(E.revisar_desarrollo(c), "R24")[0])
        (c / "tests").mkdir()
        (c / "tests" / "test_a.py").write_text("x\n", encoding="utf-8")
        self.assertIn("dicen cómo correrlas", _msg(E.revisar_desarrollo(c), "R24")[0])
        (c / "README.md").write_text("Las pruebas se corren con `python3 -m unittest`.\n", encoding="utf-8")
        self.assertNotIn("R24", _ids(E.revisar_desarrollo(c)))

    def test_r25_operacion_para_lo_que_se_despliega(self):
        c = _caja(self.td)
        self.assertFalse(E.se_despliega(c))
        (c / "Dockerfile").write_text("FROM x\n", encoding="utf-8")
        self.assertTrue(E.se_despliega(c))
        self.assertIn("falta docs/operacion.md", _msg(E.revisar_desarrollo(c), "R25")[0])
        (c / "docs").mkdir()
        (c / "docs" / "operacion.md").write_text("# Operación\n## Dónde corre\n## Claves\n", encoding="utf-8")
        m = _msg(E.revisar_desarrollo(c), "R25")[0]
        self.assertIn("cómo se despliega", m)
        self.assertIn("datos y respaldo", m)
        (c / "docs" / "operacion.md").write_text(
            "# Operación\n## Dónde corre\n## Cómo se despliega\n## Claves\n## Datos y respaldo\n", encoding="utf-8")
        self.assertNotIn("R25", _ids(E.revisar_desarrollo(c)))

    def test_r26_revision_de_seguridad_reciente(self):
        c = _caja(self.td)
        (c / "vercel.json").write_text("{}\n", encoding="utf-8")
        self.assertIn("no hay ninguna revisión", _msg(E.revisar_desarrollo(c), "R26")[0])
        sc = c / ".claude" / "security-checks"
        sc.mkdir()
        vieja = date.today() - timedelta(days=E.DIAS_REVISION_SEGURIDAD + 10)
        (sc / f"{vieja.isoformat()}.md").write_text("PASS\n", encoding="utf-8")
        self.assertIn("más de", _msg(E.revisar_desarrollo(c), "R26")[0])
        (sc / f"{date.today().isoformat()}.md").write_text("PASS\n", encoding="utf-8")
        self.assertNotIn("R26", _ids(E.revisar_desarrollo(c)))

    def test_r28_esquema_generado_con_comando_y_fecha(self):
        c = _caja(self.td)
        (c / "docs" / "esquema").mkdir(parents=True)
        self.assertIn("R28", _ids(E.revisar_desarrollo(c)))
        (c / "docs" / "esquema" / "LEEME.md").write_text("Comando: python3 gen.py\nFecha: 2026-10-18\n", encoding="utf-8")
        self.assertNotIn("R28", _ids(E.revisar_desarrollo(c)))

    def test_r28_esquema_viejo_respecto_del_codigo(self):
        c = _caja(self.td)
        (c / "docs" / "esquema").mkdir(parents=True)
        (c / "docs" / "esquema" / "LEEME.md").write_text("Comando: python3 gen.py\nFecha: 2026-01-01\n", encoding="utf-8")
        (c / "app.py").write_text("x = 1\n", encoding="utf-8")
        _git(c, "add", "-f", "-A")
        _git(c, "commit", "-q", "-m", "codigo", check=True)
        m = _msg(E.revisar_desarrollo(c), "R28")
        self.assertTrue(m and "volver a generarlo" in m[0])


class TestContenido(Entorno):
    def test_r16_reconoce_la_plantilla_actual_y_la_anterior(self):
        c = _caja(self.td)
        (c / "docs").mkdir()
        # la plantilla nueva sin escribir
        (c / "docs" / "PRD.md").write_text(E.PLANTILLA_PRD.format(nombre="caja"), encoding="utf-8")
        (c / "docs" / "decisiones.md").write_text(E.PLANTILLA_DECISIONES.format(nombre="caja"), encoding="utf-8")
        self.assertIn("R16", _ids(E.revisar_contenido(c)))
        # la plantilla anterior (con la sección técnica adentro) también cuenta como sin escribir
        viejo = "# caja — PRD\n\n> Documento vivo.\n\n## Qué se construye y para quién\n\n## Cuándo está terminado\n\n## Qué NO se hace\n" + E.LEGADO_PRD_TECNICO
        (c / "docs" / "PRD.md").write_text(viejo, encoding="utf-8")
        self.assertIn("docs/PRD.md", _msg(E.revisar_contenido(c), "R16")[0])

    def test_r16_un_prd_escrito_no_avisa(self):
        c = _caja(self.td)
        (c / "docs").mkdir()
        (c / "docs" / "PRD.md").write_text(
            E.PLANTILLA_PRD.format(nombre="caja") + "\nEs una herramienta para ordenar los pedidos de los clientes de la tienda.\n", encoding="utf-8")
        (c / "docs" / "decisiones.md").write_text("# D\n\n## 2026-10-18 — Una sola planilla\nPorque tener dos planillas distintas se desfasaba y nadie sabía cuál era la verdadera.\n", encoding="utf-8")
        self.assertNotIn("R16", _ids(E.revisar_contenido(c)))

    def test_r27_cabecera_solo_cuando_el_prd_esta_escrito(self):
        c = _caja(self.td)
        (c / "docs").mkdir()
        # PRD sin escribir: no pide la cabecera (primero hay que escribirlo)
        (c / "docs" / "PRD.md").write_text(E.PLANTILLA_PRD.format(nombre="caja"), encoding="utf-8")
        self.assertNotIn("R27", _ids(E.revisar_contenido(c)))
        # PRD escrito sin cabecera
        (c / "docs" / "PRD.md").write_text("# PRD\n\nEs una herramienta para ordenar los pedidos de los clientes.\n", encoding="utf-8")
        (m,) = _msg(E.revisar_contenido(c), "R27")
        for etq in ("Dueño", "Estado", "Respaldo", "Última revisión"):
            self.assertIn(etq, m)
        # con la cabecera completa
        (c / "docs" / "PRD.md").write_text(
            "# PRD\n\n- Dueño: Fer\n- Estado: activa\n- **Respaldo:** GitHub\n- Última revisión: 2026-10-18\n\nEs una herramienta para ordenar los pedidos.\n",
            encoding="utf-8")
        self.assertNotIn("R27", _ids(E.revisar_contenido(c)))
        # una etiqueta vacía no cuenta
        (c / "docs" / "PRD.md").write_text(
            "# PRD\n\n- Dueño:\n- Estado: activa\n- Respaldo: GitHub\n- Última revisión: 2026-10-18\n\nEs una herramienta para ordenar los pedidos.\n",
            encoding="utf-8")
        self.assertIn("Dueño", _msg(E.revisar_contenido(c), "R27")[0])


class TestBucle(Entorno):
    def test_el_bucle_no_crea_solo_las_piezas_de_desarrollo(self):
        c = _caja(self.td, codigo=True)
        _git(c, "add", "-f", "-A")
        _git(c, "commit", "-q", "-m", "base")
        archivos = {h.get("archivo") for h in O.todos(Path(self.td) / "proyectos")}
        for rel in ("docs/arquitectura.md", "docs/flujo-de-la-app.md", "README.md", ".env.example",
                    ".claude/rules/donde-va-cada-cosa.md"):
            self.assertNotIn(rel, archivos)
        self.assertIn("docs/PRD.md", archivos)   # los tres documentos de toda caja con código sí, como antes


class TestRemoto(Entorno):
    def _con_origen(self, archivos):
        """Una caja cuyo remoto es un repositorio local con esos archivos en main."""
        origen = Path(self.td) / "origen.git"
        trabajo = Path(self.td) / "semilla"
        trabajo.mkdir()
        _git(trabajo, "init", "-q", "-b", "main")
        for rel, txt in archivos.items():
            f = trabajo / rel
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(txt, encoding="utf-8")
        _git(trabajo, "add", "-f", "-A")
        _git(trabajo, "commit", "-q", "-m", "semilla")
        subprocess.run(["git", "clone", "-q", "--bare", str(trabajo), str(origen)], check=True, capture_output=True)
        raiz = Path(self.td) / "proyectos"
        raiz.mkdir()
        caja = raiz / "caja"
        subprocess.run(["git", "clone", "-q", str(origen), str(caja)], check=True, capture_output=True)
        return raiz, caja

    def test_mide_lo_que_hay_en_github_y_no_en_la_carpeta(self):
        raiz, caja = self._con_origen({"CLAUDE.md": "# c\n", ".gitignore": "x\n", "docs/PRD.md": "p\n"})
        # la carpeta local tiene MÁS que GitHub (settings.json con contenido, solo en el disco): el remoto no lo ve
        (caja / ".claude").mkdir()
        (caja / ".claude" / "settings.json").write_text(CONTENIDO, encoding="utf-8")
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = E.comando_remoto(str(raiz), traer=True)
        sal = buf.getvalue()
        self.assertEqual(code, 0)
        self.assertIn("falta en GitHub", sal)
        self.assertIn(".claude/settings.json", sal)
        self.assertIn("docs/decisiones.md", sal)
        self.assertIn("1 cajas medidas · 0 con el molde completo · 0 con settings.json subido", sal)

    def test_caja_completa_en_github(self):
        raiz, _caja_dir = self._con_origen({"CLAUDE.md": "# c\n", ".gitignore": "x\n", ".claude/settings.json": "{}\n",
                                            "docs/PRD.md": "p\n", "docs/decisiones.md": "d\n", "docs/planes/README.md": "r\n"})
        buf = io.StringIO()
        with redirect_stdout(buf):
            E.comando_remoto(str(raiz), traer=False)
        self.assertIn("1 cajas medidas · 1 con el molde completo · 1 con settings.json subido", buf.getvalue())

    def test_sin_remoto_lo_dice(self):
        raiz = Path(self.td) / "proyectos"
        c = raiz / "caja"
        c.mkdir(parents=True)
        _git(c, "init", "-q", "-b", "main")
        (c / "CLAUDE.md").write_text("# c\n", encoding="utf-8")
        buf = io.StringIO()
        with redirect_stdout(buf):
            E.comando_remoto(str(raiz), traer=False)
        self.assertIn("no se pudo medir (sin remoto)", buf.getvalue())


class TestPlantillas(Entorno):
    def test_las_piezas_nuevas_traen_instrucciones_y_ningun_valor_de_clave(self):
        for nombre, txt in (("arquitectura", E.PLANTILLA_ARQUITECTURA), ("flujo", E.PLANTILLA_FLUJO), ("readme", E.PLANTILLA_README),
                            ("claves", E.PLANTILLA_ENV_EJEMPLO), ("mapa", E.DONDE_VA)):
            self.assertGreaterEqual(len(txt.splitlines()), 2, nombre)
        # cada pieza que el mapa nombra existe en el molde oficial
        molde = (SCRIPTS_DIR.parent / "estructura" / "ESTRUCTURA.md").read_text(encoding="utf-8")
        for pieza in ("docs/arquitectura.md", "docs/flujo-de-la-app.md", "docs/diseno/", "docs/esquema/", "docs/operacion.md",
                      "docs/specs/", ".claude/security-checks/", "tests/"):
            self.assertIn(pieza, molde, pieza)
            self.assertIn(pieza.rstrip("/"), E.DONDE_VA, pieza)

    def test_las_reglas_nuevas_estan_en_el_molde_oficial(self):
        molde = (SCRIPTS_DIR.parent / "estructura" / "ESTRUCTURA.md").read_text(encoding="utf-8")
        reglas = E.parsear_reglas(molde)
        for r in ("R22", "R23", "R24", "R25", "R26", "R27", "R28", "R29"):
            self.assertTrue(any(r in str(x) for x in reglas), r)


class TestRevisionExterna(Entorno):
    """Lo que encontró la revisión independiente (Gemini, 2026-10-18) y se comprobó a mano."""

    def test_r27_etiqueta_en_negrita_vacia_no_cuenta(self):
        c = _caja(self.td)
        (c / "docs").mkdir()
        (c / "docs" / "PRD.md").write_text(
            "# PRD\n\n- **Dueño:**\n- **Estado:** \n- **Respaldo:** GitHub\n- Última revisión: 2026-10-18\n\nEs una herramienta para ordenar los pedidos.\n",
            encoding="utf-8")
        m = _msg(E.revisar_contenido(c), "R27")[0]
        self.assertIn("Dueño", m)
        self.assertIn("Estado", m)
        self.assertNotIn("Respaldo", m)
        self.assertNotIn("Última", m)

    def test_r24_latest_no_es_una_prueba(self):
        c = _caja(self.td, codigo=True)
        (c / "tests").mkdir()
        (c / "tests" / "test_a.py").write_text("x\n", encoding="utf-8")
        (c / "README.md").write_text("Descargá the latest version.\n", encoding="utf-8")
        self.assertIn("dicen cómo correrlas", _msg(E.revisar_desarrollo(c), "R24")[0])

    def test_r25_titulos_sin_tilde_valen(self):
        c = _caja(self.td)
        (c / "Dockerfile").write_text("FROM x\n", encoding="utf-8")
        (c / "docs").mkdir()
        (c / "docs" / "operacion.md").write_text(
            "# Operacion\n## Donde corre\n## Como se despliega\n## Claves\n## Datos y respaldo\n", encoding="utf-8")
        self.assertNotIn("R25", _ids(E.revisar_desarrollo(c)))

    def test_r28_fecha_que_no_existe_en_el_calendario_avisa(self):
        c = _caja(self.td)
        (c / "docs" / "esquema").mkdir(parents=True)
        (c / "docs" / "esquema" / "LEEME.md").write_text("Comando: python3 gen.py\nFecha: 2026-13-45\n", encoding="utf-8")
        self.assertIn("R28", _ids(E.revisar_desarrollo(c)))

    def test_las_excepciones_escritas_valen_para_las_reglas_nuevas(self):
        c = _caja(self.td, codigo=True)
        self.assertIn("R23", _ids(E.revisar_caja(c, "proyecto")))
        (c / ".estructura-excepciones.json").write_text(
            '[{"regla": "R23", "ruta": ".", "motivo": "sin pantallas ni flujo por diseño", "fecha": "2026-10-18"}]', encoding="utf-8")
        h = E.revisar_caja(c, "proyecto")
        self.assertNotIn("R23", {r for t, r, _m in h if t == "aviso"})
        self.assertTrue(any(t == "excepcion" and r == "R23" for t, r, _m in h))

    @unittest.skipIf(sys.platform == "win32", "el hook de la prueba es un script de sh")
    def test_remoto_no_ejecuta_los_hooks_del_repositorio(self):
        origen = Path(self.td) / "origen"
        origen.mkdir()
        _git(origen, "init", "-q", "-b", "main")
        (origen / "CLAUDE.md").write_text("# c\n", encoding="utf-8")
        _git(origen, "add", "-A")
        _git(origen, "commit", "-q", "-m", "a")
        raiz = Path(self.td) / "proyectos"
        raiz.mkdir()
        caja = raiz / "caja"
        subprocess.run(["git", "clone", "-q", str(origen), str(caja)], check=True, capture_output=True)
        marca = Path(self.td) / "hook-corrio"
        hook = caja / ".git" / "hooks" / "reference-transaction"
        hook.write_text(f"#!/bin/sh\ntouch '{marca}'\n", encoding="utf-8")
        hook.chmod(0o755)
        (origen / "otro.md").write_text("x\n", encoding="utf-8")
        _git(origen, "add", "-A")
        _git(origen, "commit", "-q", "-m", "b")   # hay algo nuevo que traer: el fetch actualiza referencias
        buf = io.StringIO()
        with redirect_stdout(buf):
            E.comando_remoto(str(raiz), traer=True)
        self.assertFalse(marca.exists(), "el hook del repositorio corrió durante `remoto`")


if __name__ == "__main__":
    unittest.main()
