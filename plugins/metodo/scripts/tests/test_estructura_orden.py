#!/usr/bin/env python3
"""test_estructura_orden.py — el bucle de orden (C140): grupos 1/2/3, registro, deshacer, resumen, encendido por defecto."""
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import estructura_orden as O  # noqa: E402


def _git(cwd, *a):
    return subprocess.run(["git", "-C", str(cwd), "-c", "user.name=t", "-c", "user.email=t@t", *a],
                          capture_output=True, text=True, check=True).stdout.strip()


def _caja(td, nombre="caja"):
    c = Path(td) / "proyectos" / nombre
    c.mkdir(parents=True)
    _git(c, "init", "-q", "-b", "main")
    (c / "CLAUDE.md").write_text("# Caja\nVer `docs/origen.md`.\n", encoding="utf-8")
    (c / "docs").mkdir()
    (c / "docs" / "origen.md").write_text("contenido del documento que se va a mover " * 3, encoding="utf-8")
    _git(c, "add", "-A")
    _git(c, "commit", "-q", "-m", "base")
    return c


class Base(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.td = self._td.name
        claves = ("CLAUDE_PLUGIN_DATA", "CLAUDE_CONFIG_DIR", "GIT_AUTHOR_NAME", "GIT_AUTHOR_EMAIL", "GIT_COMMITTER_NAME", "GIT_COMMITTER_EMAIL")
        self._env = {k: os.environ.get(k) for k in claves}
        for k, v in (("GIT_AUTHOR_NAME", "t"), ("GIT_COMMITTER_NAME", "t"), ("GIT_AUTHOR_EMAIL", "t@t"), ("GIT_COMMITTER_EMAIL", "t@t")):
            os.environ[k] = v   # el runner de CI no tiene identidad de git; el commit automático la necesita
        os.environ["CLAUDE_PLUGIN_DATA"] = str(Path(self.td) / "estado")
        os.environ["CLAUDE_CONFIG_DIR"] = str(Path(self.td) / "config")

    def tearDown(self):
        for k, v in self._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        self._td.cleanup()

    def raiz(self):
        return Path(self.td) / "proyectos"

    def mover(self, c):
        _git(c, "mv", "docs/origen.md", "docs/destino.md")
        _git(c, "commit", "-q", "-m", "mueve el documento")


class TestGrupo1(Base):
    def test_ruta_movida_se_reescribe_con_commit_registro_y_deshacer(self):
        c = _caja(self.td)
        self.mover(c)
        hs = [h for h in O.todos(self.raiz()) if h["tipo"] == "ruta_movida"]
        self.assertEqual(len(hs), 1)
        self.assertEqual(hs[0]["despues"], "docs/destino.md")
        antes = _git(c, "rev-list", "--count", "HEAD")
        e = O.aplicar_uno(hs[0])
        O.registrar(e)
        self.assertEqual(e["estado"], "aplicado")
        self.assertIn("docs/destino.md", (c / "CLAUDE.md").read_text(encoding="utf-8"))
        self.assertEqual(int(_git(c, "rev-list", "--count", "HEAD")), int(antes) + 1)  # un commit por arreglo
        self.assertEqual(_git(c, "status", "--porcelain"), "")
        self.assertIn("deshacer", e["deshacer"])
        with redirect_stdout(io.StringIO()):
            self.assertEqual(O.comando_deshacer(e["id"]), 0)
        self.assertIn("docs/origen.md", (c / "CLAUDE.md").read_text(encoding="utf-8"))

    def test_no_toca_un_archivo_con_cambios_sin_guardar(self):
        c = _caja(self.td)
        self.mover(c)
        (c / "CLAUDE.md").write_text("# Caja\nVer `docs/origen.md`. Otra sesión escribe acá.\n", encoding="utf-8")
        h = next(h for h in O.todos(self.raiz()) if h["tipo"] == "ruta_movida")
        e = O.aplicar_uno(h)
        self.assertEqual(e["estado"], "omitido")
        self.assertIn("sin guardar", e["motivo"])
        self.assertIn("Otra sesión", (c / "CLAUDE.md").read_text(encoding="utf-8"))

    def test_no_toca_si_git_esta_a_mitad_de_algo(self):
        c = _caja(self.td)
        self.mover(c)
        h = next(h for h in O.todos(self.raiz()) if h["tipo"] == "ruta_movida")
        (c / ".git" / "index.lock").write_text("", encoding="utf-8")
        self.assertEqual(O.aplicar_uno(h)["estado"], "omitido")

    def test_sin_codigo_no_se_crean_documentos_vacios(self):
        _caja(self.td)   # solo un CLAUDE.md y un documento: nada que registrar todavía
        self.assertEqual([h for h in O.todos(self.raiz()) if h["tipo"] == "doc_vivo"], [])

    def test_documento_vivo_que_falta_se_crea_y_se_commitea(self):
        c = _caja(self.td)
        (c / "package.json").write_text("{}\n", encoding="utf-8")   # con código, los documentos vivos sí hacen falta
        _git(c, "add", "-A")
        _git(c, "commit", "-q", "-m", "codigo")
        hs = [h for h in O.todos(self.raiz()) if h["tipo"] == "doc_vivo"]
        self.assertTrue(hs)
        for h in hs:
            e = O.aplicar_uno(h)
            self.assertEqual(e["estado"], "aplicado")
        self.assertTrue((c / "docs" / "PRD.md").is_file())
        self.assertEqual(_git(c, "status", "--porcelain"), "")

    def test_no_nunca_crea_lo_que_ya_esta_en_github(self):
        c = _caja(self.td)
        (c / "package.json").write_text("{}\n", encoding="utf-8")
        (c / "docs" / "PRD.md").write_text("ya está en el remoto " * 5, encoding="utf-8")
        _git(c, "add", "-A")
        _git(c, "commit", "-q", "-m", "prd")
        _git(c, "update-ref", "refs/remotes/origin/main", "HEAD")
        _git(c, "rm", "-q", "--cached", "docs/PRD.md")
        (c / "docs" / "PRD.md").unlink()
        _git(c, "commit", "-q", "-m", "se perdió en la copia local")
        faltan = [h["archivo"] for h in O.todos(self.raiz()) if h["tipo"] == "doc_vivo"]
        self.assertNotIn("docs/PRD.md", faltan)


class TestReanudarUnLugar(Base):
    """El REANUDAR.md vive en UN lugar (.claude/prompts/). El que dejó una versión vieja en la raíz se mueve solo, con copia y deshacer."""
    TEXTO = "<!-- cierre 2026-10-27-prueba -->\n═══ PARTE B — ESTADO ═══\nacentos: áéíóú ñ\r\nlínea final sin salto"

    def caja_con_raiz(self, guardado=True):
        c = _caja(self.td)
        (c / "REANUDAR.md").write_bytes(self.TEXTO.encode("utf-8"))
        if guardado:
            _git(c, "add", "REANUDAR.md")
            _git(c, "commit", "-q", "-m", "cierre viejo")
        return c

    def hallazgos(self):
        return [h for h in O.todos(self.raiz()) if h["tipo"] == "reanudar_en_raiz"]

    def test_el_desorden_viejo_se_ve_y_el_arreglo_lo_mueve_byte_a_byte(self):
        c = self.caja_con_raiz()
        hs = self.hallazgos()
        self.assertEqual((len(hs), hs[0]["grupo"]), (1, 1))            # con el desorden viejo: hallazgo seguro y reversible
        antes = int(_git(c, "rev-list", "--count", "HEAD"))
        e = O.aplicar_uno(hs[0])
        O.registrar(e)
        self.assertEqual(e["estado"], "aplicado", e)
        self.assertFalse((c / "REANUDAR.md").exists())
        self.assertEqual((c / ".claude" / "prompts" / "REANUDAR.md").read_bytes(), self.TEXTO.encode("utf-8"))
        self.assertEqual(int(_git(c, "rev-list", "--count", "HEAD")), antes + 1)     # un solo commit
        self.assertEqual(_git(c, "status", "--porcelain"), "")
        self.assertEqual(self.hallazgos(), [])                                        # con el arreglo: nada que mover

    def test_deshacer_devuelve_la_raiz_y_no_se_vuelve_a_mover_solo(self):
        c = self.caja_con_raiz()
        e = O.aplicar_uno(self.hallazgos()[0])
        O.registrar(e)
        with redirect_stdout(io.StringIO()):
            self.assertEqual(O.comando_deshacer(e["id"]), 0)
        self.assertEqual((c / "REANUDAR.md").read_bytes(), self.TEXTO.encode("utf-8"))
        self.assertFalse((c / ".claude" / "prompts" / "REANUDAR.md").exists())
        self.assertEqual(O.aplicar_uno(self.hallazgos()[0])["estado"], "omitido")    # lo deshecho no se repite solo

    def test_sin_guardar_en_git_o_con_cambios_no_se_toca(self):
        c = self.caja_con_raiz(guardado=False)
        self.assertEqual(self.hallazgos(), [])                                        # no está en git: no se podría deshacer
        _git(c, "add", "REANUDAR.md"); _git(c, "commit", "-q", "-m", "x")
        (c / "REANUDAR.md").write_bytes(b"editado a mano\n")
        self.assertEqual(self.hallazgos(), [])

    def test_si_el_lugar_nuevo_ya_esta_ocupado_no_adivina(self):
        c = self.caja_con_raiz()
        (c / ".claude" / "prompts").mkdir(parents=True)
        (c / ".claude" / "prompts" / "REANUDAR.md").write_text("otro", encoding="utf-8")
        self.assertEqual(self.hallazgos(), [])
        self.assertEqual((c / "REANUDAR.md").read_bytes(), self.TEXTO.encode("utf-8"))

    def test_si_el_lugar_nuevo_esta_ignorado_no_se_intenta(self):
        c = self.caja_con_raiz()
        (c / ".gitignore").write_text(".claude/prompts/\n", encoding="utf-8")
        _git(c, "add", ".gitignore"); _git(c, "commit", "-q", "-m", "ignora")
        self.assertEqual(self.hallazgos(), [])

    def test_si_otra_sesion_ocupa_el_lugar_nuevo_justo_ahora_no_se_le_borra(self):
        c = self.caja_con_raiz()
        h = self.hallazgos()[0]
        (c / ".claude" / "prompts").mkdir(parents=True)
        ajeno = c / ".claude" / "prompts" / "REANUDAR.md"
        ajeno.write_text("de otra sesion", encoding="utf-8")   # aparece después de detectar el hallazgo
        e = O.aplicar_uno(h)
        self.assertNotEqual(e["estado"], "aplicado")
        self.assertEqual(ajeno.read_text(encoding="utf-8"), "de otra sesion")
        self.assertEqual((c / "REANUDAR.md").read_bytes(), self.TEXTO.encode("utf-8"))

    def test_si_el_commit_falla_la_raiz_queda_como_estaba(self):
        c = self.caja_con_raiz()
        h = self.hallazgos()[0]
        (c / ".gitignore").write_text(".claude/prompts/\n", encoding="utf-8")        # git no deja agregar el lugar nuevo
        e = O.aplicar_uno(h)
        self.assertEqual(e["estado"], "fallo")
        self.assertEqual((c / "REANUDAR.md").read_bytes(), self.TEXTO.encode("utf-8"))
        self.assertFalse((c / ".claude" / "prompts" / "REANUDAR.md").exists())
        self.assertEqual(_git(c, "ls-files", "REANUDAR.md"), "REANUDAR.md")

    def test_si_la_carpeta_del_camino_es_un_enlace_no_escribe(self):
        if os.name == "nt":
            self.skipTest("enlaces simbólicos no disponibles sin permisos en Windows")
        c = self.caja_con_raiz()
        afuera = Path(self.td) / "afuera"
        afuera.mkdir()
        (c / ".claude").symlink_to(afuera, target_is_directory=True)
        e = O.aplicar_uno(self.hallazgos()[0])
        self.assertEqual(e["estado"], "omitido")
        self.assertEqual(list(afuera.iterdir()), [])

    def test_el_control_R18_ahora_revisa_tambien_el_de_la_raiz(self):
        import estructura
        c = self.caja_con_raiz()
        (c / "REANUDAR.md").write_text(self.TEXTO + "\nMirá `docs/no-existe-nada.md`.\n", encoding="utf-8")
        r18 = [m for _t, r, m in estructura.revisar_contenido(c) if r == "R18"]
        self.assertTrue(r18 and "no existen" in r18[0], r18)

    def test_un_solo_punto_conoce_la_ruta(self):
        import reanudar_ruta as RR
        d = Path(self.td) / "k"
        self.assertIsNone(RR.buscar(d))
        d.mkdir()
        (d / "REANUDAR.md").write_text("v", encoding="utf-8")
        self.assertEqual(RR.buscar(d), RR.ruta_vieja(d))
        (d / ".claude" / "prompts").mkdir(parents=True)
        (d / ".claude" / "prompts" / "REANUDAR.md").write_text("n", encoding="utf-8")
        self.assertEqual(RR.buscar(d), RR.ruta(d))


class TestGrupo2y3(Base):
    def test_grupo2_pide_la_verificacion_de_una_segunda_ia(self):
        c = _caja(self.td)
        (c / "CLAUDE.md").write_text("# Caja\nVer `docs/otro.md`.\n", encoding="utf-8")
        (c / "docs" / "sub").mkdir()
        (c / "docs" / "sub" / "otro.md").write_text("texto " * 20, encoding="utf-8")
        _git(c, "add", "-A")
        _git(c, "commit", "-q", "-m", "otro está en una subcarpeta")
        h = next(h for h in O.todos(self.raiz()) if h["tipo"] == "ruta_candidata")
        self.assertEqual(h["grupo"], 2)
        self.assertEqual(O.aplicar_uno(h)["estado"], "omitido")            # sin verificación no se aplica
        e = O.aplicar_uno(h, verificado_por="gemini")
        self.assertEqual(e["estado"], "aplicado")
        self.assertEqual(e["verificado_por"], "gemini")
        self.assertIn("docs/sub/otro.md", (c / "CLAUDE.md").read_text(encoding="utf-8"))

    def test_grupo3_nunca_se_aplica_y_la_pregunta_es_una(self):
        h = dict(id="x", grupo=3, tipo="estructura_R1", caja="/tmp/x", nombre="mi-caja", evidencia="no tiene .git/ ni remoto en GitHub")
        self.assertEqual(O.aplicar_uno(h)["estado"], "omitido")
        q = O.pregunta_de_la_persona([h])
        self.assertIn("mi-caja", q)
        self.assertIn("Propongo", q)
        self.assertIn("Porque", q)
        self.assertIn("recomendación", q)
        self.assertEqual(q.count("¿"), 1)

    def test_lo_sensible_siempre_es_grupo3(self):
        for rel in (".claude/settings.json", "hooks/x.py", ".mcp.json", ".github/workflows/a.yml", "instalar.sh"):
            self.assertTrue(O.es_sensible(rel), rel)
        self.assertFalse(O.es_sensible("docs/PRD.md"))


class TestEncendidoYResumen(Base):
    def _escribir_cfg(self, texto):
        O.archivo_config().parent.mkdir(parents=True, exist_ok=True)
        O.archivo_config().write_text(texto, encoding="utf-8")

    def test_sin_archivo_esta_encendido_por_defecto(self):
        self.assertFalse(O.archivo_config().exists())
        self.assertEqual(O.estado_encendido(), (True, "encendida por defecto"))
        self.assertTrue(O.aplicar_encendido())

    def test_archivo_sin_la_clave_esta_encendido(self):
        self._escribir_cfg("{}")
        self.assertEqual(O.estado_encendido(), (True, "encendida por defecto"))

    def test_aplicar_false_apaga_y_aplicar_true_enciende(self):
        self._escribir_cfg('{"aplicar": false}')
        self.assertEqual(O.estado_encendido(), (False, "apagada por vos"))
        self._escribir_cfg('{"aplicar": true}')
        self.assertEqual(O.estado_encendido(), (True, "encendida por vos"))

    def test_archivo_roto_o_raro_queda_apagado(self):
        for txt in ("{no es json", "", "[]", '"hola"', '{"aplicar": "si"}', '{"aplicar": null}', '{"aplicar": 0}'):
            self._escribir_cfg(txt)
            self.assertFalse(O.aplicar_encendido(), txt)

    def test_archivo_ilegible_queda_apagado(self):
        O.archivo_config().parent.mkdir(parents=True, exist_ok=True)
        O.archivo_config().mkdir()   # un directorio donde va el archivo: leerlo da error de sistema
        self.assertFalse(O.aplicar_encendido())

    def test_los_comandos_apagan_y_encienden_y_dicen_cual_es_el_caso(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            O.comando_config(False, False)
        self.assertIn("ENCENDIDA (encendida por defecto)", buf.getvalue())
        with redirect_stdout(io.StringIO()):
            O.comando_config(False, True)
        self.assertEqual(json.loads(O.archivo_config().read_text(encoding="utf-8")), {"aplicar": False})
        self.assertFalse(O.aplicar_encendido())
        buf = io.StringIO()
        with redirect_stdout(buf):
            O.comando_config(False, False)
        self.assertIn("APAGADA (apagada por vos)", buf.getvalue())
        with redirect_stdout(io.StringIO()):
            O.comando_config(True, False)
        self.assertEqual(json.loads(O.archivo_config().read_text(encoding="utf-8")), {"aplicar": True})
        self.assertTrue(O.aplicar_encendido())

    def test_encender_sobre_un_archivo_roto_lo_reescribe(self):
        self._escribir_cfg("[1,2]")
        with redirect_stdout(io.StringIO()):
            O.comando_config(True, False)
        self.assertTrue(O.aplicar_encendido())

    def test_semanal_sin_archivo_arregla_solo(self):
        c = _caja(self.td)
        self.mover(c)
        with redirect_stdout(io.StringIO()):
            O.semanal(self.raiz())
        self.assertIn("docs/destino.md", (c / "CLAUDE.md").read_text(encoding="utf-8"))

    def test_semanal_apagado_no_cambia_nada(self):
        c = _caja(self.td)
        self.mover(c)
        with redirect_stdout(io.StringIO()):
            O.comando_config(False, True)
        antes = _git(c, "rev-parse", "HEAD")
        with redirect_stdout(io.StringIO()):
            O.semanal(self.raiz())
        self.assertEqual(_git(c, "rev-parse", "HEAD"), antes)

    def test_semanal_encendido_arregla_y_resume_en_tres_lineas(self):
        c = _caja(self.td)
        self.mover(c)
        with redirect_stdout(io.StringIO()):
            O.comando_config(True, False)
        buf = io.StringIO()
        with redirect_stdout(buf):
            O.semanal(self.raiz())
        lineas = buf.getvalue().strip().splitlines()
        self.assertEqual(len(lineas), 3)
        self.assertIn("arreglé", lineas[0])
        self.assertIn("docs/destino.md", (c / "CLAUDE.md").read_text(encoding="utf-8"))
        reg = O.leer_registro()
        self.assertTrue(any(e["estado"] == "aplicado" for e in reg))

    def test_deshacer_un_id_inexistente_no_rompe(self):
        with redirect_stdout(io.StringIO()):
            self.assertEqual(O.comando_deshacer("no-existe"), 1)


class TestRevisionIndependiente(Base):
    """Hallazgos de la revisión de Gemini (2026-10-16): ramas, deshacer repetido, pérdida de commits."""

    def test_no_toca_si_la_caja_esta_en_otra_rama(self):
        c = _caja(self.td)
        self.mover(c)
        h = next(h for h in O.todos(self.raiz()) if h["tipo"] == "ruta_movida")
        _git(c, "checkout", "-q", "-b", "feature/algo")
        e = O.aplicar_uno(h)
        self.assertEqual(e["estado"], "omitido")
        self.assertIn("rama", e["motivo"])
        self.assertIn("docs/origen.md", (c / "CLAUDE.md").read_text(encoding="utf-8"))

    def test_deshacer_dos_veces_no_repite(self):
        c = _caja(self.td)
        self.mover(c)
        h = next(h for h in O.todos(self.raiz()) if h["tipo"] == "ruta_movida")
        e = O.aplicar_uno(h)
        O.registrar(e)
        with redirect_stdout(io.StringIO()):
            self.assertEqual(O.comando_deshacer(e["id"]), 0)
            commits = _git(c, "rev-list", "--count", "HEAD")
            self.assertEqual(O.comando_deshacer(e["id"]), 1)
        self.assertEqual(_git(c, "rev-list", "--count", "HEAD"), commits)

    def test_deshacer_un_conflicto_deja_la_carpeta_limpia(self):
        c = _caja(self.td)
        self.mover(c)
        h = next(h for h in O.todos(self.raiz()) if h["tipo"] == "ruta_movida")
        e = O.aplicar_uno(h)
        O.registrar(e)
        (c / "CLAUDE.md").write_text("# Caja\nTexto totalmente distinto escrito después.\n", encoding="utf-8")
        _git(c, "commit", "-q", "-am", "cambio posterior")
        with redirect_stdout(io.StringIO()):
            self.assertEqual(O.comando_deshacer(e["id"]), 1)
        self.assertFalse((c / ".git" / "REVERT_HEAD").exists())
        self.assertEqual(_git(c, "status", "--porcelain"), "")

    def test_semanal_apagado_y_sin_historia_no_recorre_nada(self):
        _caja(self.td)
        with redirect_stdout(io.StringIO()):
            O.comando_config(False, True)
        buf = io.StringIO()
        with redirect_stdout(buf):
            O.semanal(self.raiz())
        self.assertEqual(buf.getvalue(), "")


class TestRevisionDeSeguridad(Base):
    """Hallazgos del revisor de seguridad (2026-10-16): lo sensible que trae GitHub, enlaces, deshecho que no vuelve."""

    def test_una_caja_atrasada_que_trae_algo_sensible_pasa_al_grupo_3(self):
        c = _caja(self.td)
        origen = Path(self.td) / "remoto"
        subprocess.run(["git", "clone", "-q", str(c), str(origen)], check=True)
        (origen / ".claude").mkdir()
        (origen / ".claude" / "settings.json").write_text("{}", encoding="utf-8")
        _git(origen, "add", "-f", "-A")
        _git(origen, "commit", "-q", "-m", "settings ajeno")
        _git(c, "remote", "add", "origin", str(origen))
        _git(c, "fetch", "-q", "origin")
        _git(c, "branch", "-q", "--set-upstream-to=origin/main", "main")
        _git(c, "remote", "set-head", "origin", "main")
        sens = [x for x in O.todos(self.raiz()) if x["tipo"] == "caja_atrasada_sensible"]
        self.assertTrue(sens)
        self.assertEqual(sens[0]["grupo"], 3)
        self.assertFalse([x for x in O.todos(self.raiz()) if x["tipo"] == "caja_atrasada"])

    def test_no_escribe_a_traves_de_un_enlace(self):
        c = _caja(self.td)
        self.mover(c)
        h = next(h for h in O.todos(self.raiz()) if h["tipo"] == "ruta_movida")
        fuera = Path(self.td) / "fuera.md"
        fuera.write_text("# Caja\nVer `docs/origen.md`.\n", encoding="utf-8")
        (c / "CLAUDE.md").unlink()
        os.symlink(fuera, c / "CLAUDE.md")
        e = O.aplicar_uno(h)
        self.assertEqual(e["estado"], "omitido")
        self.assertIn("docs/origen.md", fuera.read_text(encoding="utf-8"))

    def test_lo_deshecho_no_se_vuelve_a_aplicar_solo(self):
        c = _caja(self.td)
        self.mover(c)
        h = next(h for h in O.todos(self.raiz()) if h["tipo"] == "ruta_movida")
        e = O.aplicar_uno(h)
        O.registrar(e)
        with redirect_stdout(io.StringIO()):
            O.comando_deshacer(e["id"])
        h2 = next(h for h in O.todos(self.raiz()) if h["tipo"] == "ruta_movida")
        self.assertEqual(O.aplicar_uno(h2)["estado"], "omitido")

    def test_el_comando_de_deshacer_es_el_seguro_y_el_commit_es_mecanico(self):
        c = _caja(self.td)
        self.mover(c)
        h = next(h for h in O.todos(self.raiz()) if h["tipo"] == "ruta_movida")
        e = O.aplicar_uno(h)
        self.assertTrue(e["deshacer"].startswith("estructura.py deshacer "))
        self.assertNotIn("git ", e["deshacer"])
        self.assertTrue(O._sha_valido(e["commit"]))
        self.assertFalse(O._sha_valido("--abort"))

    def test_las_lineas_historicas_del_claude_md_no_se_tocan(self):
        c = _caja(self.td)
        (c / "CLAUDE.md").write_text("# Caja\nVer `docs/origen.md`.\nAntes: `docs/origen.md` era el documento viejo.\n", encoding="utf-8")
        _git(c, "commit", "-q", "-am", "historia")
        self.mover(c)
        h = next(h for h in O.todos(self.raiz()) if h["tipo"] == "ruta_movida")
        O.aplicar_uno(h)
        txt = (c / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertIn("Ver `docs/destino.md`", txt)
        self.assertIn("Antes: `docs/origen.md` era", txt)


def _atrasada(td, c, archivo, contenido="x\n", ejecutable=False):
    """Deja la caja `c` un commit atrás de un remoto que agrega `archivo`."""
    origen = Path(td) / "remoto"
    subprocess.run(["git", "clone", "-q", str(c), str(origen)], check=True)
    f = origen / archivo
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(contenido, encoding="utf-8")
    _git(origen, "add", "-f", "--", archivo)
    if ejecutable:
        _git(origen, "update-index", "--chmod=+x", "--", archivo)
    _git(origen, "commit", "-q", "-m", "trae " + archivo)
    _git(c, "remote", "add", "origin", str(origen))
    _git(c, "fetch", "-q", "origin")
    _git(c, "branch", "-q", "--set-upstream-to=origin/main", "main")
    _git(c, "remote", "set-head", "origin", "main")


class TestC152Permitidos(Base):
    """(a) Lo que el bucle escribe va por lista de permitidos; lo que trae GitHub, por «puede correr solo» amplio."""

    def test_solo_escribe_claude_md_y_md_de_docs(self):
        for rel in ("CLAUDE.md", "docs/PRD.md", "docs/planes/README.md", "docs\\decisiones.md"):
            self.assertTrue(O.puede_escribir(rel), rel)
        for rel in ("README.md", "src/app.py", "docs/a.py", "docs/hooks/x.md", "../docs/a.md", "docs/../x.md",
                    "/abs/docs/a.md", "C:/x/docs/a.md", ".claude/x.md", "docs/.oculto/a.md", "Makefile", "",
                    "sub/CLAUDE.md", "docs/instalar.md"):
            self.assertFalse(O.puede_escribir(rel), rel)

    def test_un_documento_fuera_de_la_lista_no_se_crea(self):
        c = _caja(self.td)
        for rel in ("scripts/arranque.md", "Makefile", "hooks/x.md"):
            h = dict(id="x" + rel, grupo=1, tipo="doc_vivo", caja=str(c), nombre="caja", archivo=rel, contenido="hola\n")
            e = O.aplicar_uno(h)
            self.assertEqual(e["estado"], "omitido", rel)
            self.assertFalse((c / rel).exists(), rel)

    def test_una_ruta_movida_solo_toca_el_claude_md(self):
        c = _caja(self.td)
        (c / "run.py").write_text("`docs/origen.md`\n", encoding="utf-8")
        _git(c, "add", "run.py")
        _git(c, "commit", "-q", "-m", "script")
        h = dict(id="y", grupo=1, tipo="ruta_movida", caja=str(c), nombre="caja", archivo="run.py",
                 antes="docs/origen.md", despues="docs/destino.md")
        self.assertEqual(O.aplicar_uno(h)["estado"], "omitido")
        self.assertIn("docs/origen.md", (c / "run.py").read_text(encoding="utf-8"))

    def test_docs_como_enlace_no_se_escribe(self):
        c = _caja(self.td)
        afuera = Path(self.td) / "afuera"
        afuera.mkdir()
        try:
            (c / "docs" / "sub").symlink_to(afuera, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("este sistema no deja crear enlaces")
        h = dict(id="z", grupo=1, tipo="doc_vivo", caja=str(c), nombre="caja", archivo="docs/sub/x.md", contenido="hola\n")
        self.assertEqual(O.aplicar_uno(h)["estado"], "omitido")
        self.assertFalse((afuera / "x.md").exists())

    def test_lo_que_puede_correr_solo_es_sensible(self):
        for rel in (".husky/pre-commit", ".vscode/tasks.json", ".devcontainer/devcontainer.json", ".gitattributes",
                    "scripts/arranque.ps1", "tools\\x.bat", "LaunchAgents/com.x.plist", "deploy.sh", "a/.envrc",
                    "Startup/x.lnk", "etc/systemd/x.service"):
            self.assertTrue(O.es_sensible(rel), rel)
        for rel in (".gitignore", "src/app.py", "docs/a.md", "README.md"):
            self.assertFalse(O.es_sensible(rel), rel)

    def test_caja_atrasada_que_trae_un_ejecutable_es_pregunta(self):
        c = _caja(self.td)
        _atrasada(self.td, c, "herramientas/correr", "#!/bin/sh\necho hola\n", ejecutable=True)
        hs = O.todos(self.raiz())
        self.assertFalse([x for x in hs if x["tipo"] == "caja_atrasada"])
        s = [x for x in hs if x["tipo"] == "caja_atrasada_sensible"]
        self.assertEqual(len(s), 1)
        self.assertEqual(s[0]["grupo"], 3)
        q = O.pregunta_de_la_persona(s)
        self.assertIn("traer los cambios de GitHub", q)
        self.assertIn("herramientas/correr", q)

    def test_caja_atrasada_con_codigo_comun_sigue_avanzando_sola(self):
        c = _caja(self.td)
        _atrasada(self.td, c, "src/app.py", "print('hola')\n")
        h = next(x for x in O.todos(self.raiz()) if x["tipo"] == "caja_atrasada")
        self.assertEqual(h["grupo"], 1)
        self.assertEqual(O.aplicar_uno(h)["estado"], "aplicado")
        self.assertTrue((c / "src" / "app.py").exists())

    def test_el_bucle_no_ejecuta_hooks_de_git(self):
        c = _caja(self.td)
        marca = Path(self.td) / "corrio-un-hook"
        hooks = c / "ganchos"
        hooks.mkdir()
        cuerpo = "#!/bin/sh\necho x > '" + marca.as_posix() + "'\n"
        for nombre in ("post-commit", "pre-commit", "post-merge"):
            (hooks / nombre).write_text(cuerpo, encoding="utf-8")
            os.chmod(hooks / nombre, 0o755)
        _git(c, "config", "core.hooksPath", str(hooks))
        # control: un commit común SÍ corre el hook (si no, la prueba no probaría nada)
        (c / "docs" / "control.md").write_text("control\n", encoding="utf-8")
        _git(c, "add", "docs/control.md")
        _git(c, "commit", "-q", "-m", "control")
        if not marca.exists():
            self.skipTest("en este sistema git no corre hooks de prueba")
        marca.unlink()
        self.mover(c)
        marca.unlink(missing_ok=True)
        h = next(x for x in O.todos(self.raiz()) if x["tipo"] == "ruta_movida")
        self.assertEqual(O.aplicar_uno(h)["estado"], "aplicado")
        self.assertFalse(marca.exists(), "el bucle corrió un hook de git")


class TestC152Revision(Base):
    """Hallazgos de la revisión independiente de 0.49.4 (Gemini, 2026-10-17)."""

    def test_si_otra_sesion_hizo_el_mismo_arreglo_no_se_le_devuelve_el_texto_viejo(self):
        from unittest import mock
        c = _caja(self.td)
        self.mover(c)
        h = next(x for x in O.todos(self.raiz()) if x["tipo"] == "ruta_movida")

        def la_otra_sesion_commitea_primero(caja, rutas, mensaje):
            _git(caja, "add", "--", *rutas)
            _git(caja, "commit", "-q", "-m", "lo mismo, desde la otra sesión")
            return None   # al commit de esta sesión no le queda nada que guardar
        with mock.patch.object(O, "_commit", side_effect=la_otra_sesion_commitea_primero):
            e = O.aplicar_uno(h)
        self.assertEqual(e["estado"], "omitido")
        self.assertIn("docs/destino.md", (c / "CLAUDE.md").read_text(encoding="utf-8"))
        self.assertEqual(_git(c, "status", "--porcelain"), "")

    def test_extensiones_de_windows_que_se_ejecutan(self):
        for rel in ("a.url", "b.hta", "c.wsf", "d.scr", "e.cpl", "f.com", "docs\\x.ps1"):
            self.assertTrue(O.es_sensible(rel), rel)

    def test_carpeta_sin_hooks_va_con_barras_normales(self):
        self.assertNotIn("\\", O._sin_hooks())


class TestC152Verificador(Base):
    """(b) --verificado-por: lista cerrada, se registra como declaración, nada automático aplica el grupo 2."""

    def _candidata(self):
        c = _caja(self.td)
        (c / "CLAUDE.md").write_text("# Caja\nVer `docs/otro.md`.\n", encoding="utf-8")
        (c / "docs" / "sub").mkdir()
        (c / "docs" / "sub" / "otro.md").write_text("texto " * 20, encoding="utf-8")
        _git(c, "add", "-A")
        _git(c, "commit", "-q", "-m", "otro está en una subcarpeta")
        return c

    def test_lista_cerrada(self):
        for v in ("gemini", "Codex", "claude-opus", "gemini-3.8-flash", "persona", "pal", " gpt "):
            self.assertTrue(O.verificador_valido(v), v)
        for v in ("", "x", "ok", "yo", "geminis", "gemini; rm -rf", "otra ia", "g" * 50, None, 3):
            self.assertFalse(O.verificador_valido(v), v)

    def test_texto_libre_no_aplica_y_lo_conocido_queda_como_declaracion(self):
        c = self._candidata()
        h = next(x for x in O.todos(self.raiz()) if x["tipo"] == "ruta_candidata")
        self.assertEqual(O.aplicar_uno(h, verificado_por="ok")["estado"], "omitido")
        self.assertNotIn("docs/sub/otro.md", (c / "CLAUDE.md").read_text(encoding="utf-8"))
        e = O.aplicar_uno(h, verificado_por="gemini")
        self.assertEqual(e["estado"], "aplicado")
        self.assertEqual(e["verificacion"], "declarada")

    def test_el_comando_rechaza_texto_libre_y_avisa_que_es_declaracion(self):
        c = self._candidata()
        h = next(x for x in O.todos(self.raiz().resolve()) if x["tipo"] == "ruta_candidata")   # el comando resuelve la raíz
        buf = io.StringIO()
        with redirect_stdout(buf):
            self.assertEqual(O.comando_aplicar(h["id"], "listo", raiz_arg=str(self.raiz())), 1)
        self.assertIn("no es una IA conocida", buf.getvalue())
        self.assertNotIn("docs/sub/otro.md", (c / "CLAUDE.md").read_text(encoding="utf-8"))
        buf = io.StringIO()
        with redirect_stdout(buf):
            self.assertEqual(O.comando_aplicar(h["id"], "codex", raiz_arg=str(self.raiz())), 0)
        self.assertIn("declaración", buf.getvalue())

    def test_la_pasada_semanal_nunca_aplica_el_grupo_2(self):
        c = self._candidata()
        antes = _git(c, "log", "-1", "--format=%H", "--", "CLAUDE.md")
        with redirect_stdout(io.StringIO()):
            O.semanal(self.raiz())   # puede crear documentos del molde (grupo 1), nunca tocar el CLAUDE.md (grupo 2)
        self.assertEqual(_git(c, "log", "-1", "--format=%H", "--", "CLAUDE.md"), antes)
        self.assertNotIn("docs/sub/otro.md", (c / "CLAUDE.md").read_text(encoding="utf-8"))


class TestC152Tope(Base):
    """(c) Tope de tiempo TOTAL: ninguna llamada a git pasa del tope, también dentro de una caja."""

    def test_ninguna_llamada_a_git_pasa_del_tope(self):
        from unittest import mock
        import estructura as E
        for i in range(3):
            c = _caja(self.td, f"caja{i}")
            self.mover(c)
        vistos = []
        real = E.subprocess.run

        def espia(cmd, **kw):
            if cmd and cmd[0] == "git":
                vistos.append(kw.get("timeout"))
            return real(cmd, **kw)
        with mock.patch.object(E.subprocess, "run", side_effect=espia):
            O.todos(self.raiz(), tope_segundos=3)
        self.assertTrue(vistos)
        self.assertTrue(all(t is not None and t <= 3 for t in vistos), vistos)
        self.assertIsNone(E.LIMITE_GIT)   # el tope no queda pegado para lo que venga después

    def test_una_caja_lenta_corta_la_pasada_sin_hallazgos_a_medias(self):
        from unittest import mock
        import time as _t
        import estructura as E
        for i in range(3):
            c = _caja(self.td, f"caja{i}")
            self.mover(c)
        real = E.revisar_caja

        def lenta(*a, **k):
            _t.sleep(0.6)
            return real(*a, **k)
        t0 = _t.monotonic()
        with mock.patch.object(E, "revisar_caja", side_effect=lenta):
            hs = O.todos(self.raiz(), tope_segundos=0.3)
        self.assertLess(_t.monotonic() - t0, 3)
        self.assertEqual(hs, [])   # la caja cortada a la mitad no deja su ruta_movida suelta
        self.assertIsNone(E.LIMITE_GIT)

    def test_pasado_el_tope_total_no_empieza_arreglos(self):
        from unittest import mock
        c = _caja(self.td)
        self.mover(c)
        antes = _git(c, "rev-parse", "HEAD")
        buf = io.StringIO()
        with mock.patch.object(O, "TOPE_TOTAL", 0), redirect_stdout(buf):
            O.semanal(self.raiz())
        self.assertEqual(_git(c, "rev-parse", "HEAD"), antes)
        self.assertEqual(len(buf.getvalue().strip().splitlines()), 3)   # el resumen igual sale


if __name__ == "__main__":
    unittest.main()
