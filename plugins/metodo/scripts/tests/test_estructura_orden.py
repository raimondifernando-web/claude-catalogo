#!/usr/bin/env python3
"""test_estructura_orden.py — el bucle de orden (C140): grupos 1/2/3, registro, deshacer, resumen, apagado por defecto."""
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

    def test_documento_vivo_que_falta_se_crea_y_se_commitea(self):
        c = _caja(self.td)
        hs = [h for h in O.todos(self.raiz()) if h["tipo"] == "doc_vivo"]
        self.assertTrue(hs)
        for h in hs:
            e = O.aplicar_uno(h)
            self.assertEqual(e["estado"], "aplicado")
        self.assertTrue((c / "docs" / "PRD.md").is_file())
        self.assertEqual(_git(c, "status", "--porcelain"), "")

    def test_no_nunca_crea_lo_que_ya_esta_en_github(self):
        c = _caja(self.td)
        (c / "docs" / "PRD.md").write_text("ya está en el remoto " * 5, encoding="utf-8")
        _git(c, "add", "-A")
        _git(c, "commit", "-q", "-m", "prd")
        _git(c, "update-ref", "refs/remotes/origin/main", "HEAD")
        _git(c, "rm", "-q", "--cached", "docs/PRD.md")
        (c / "docs" / "PRD.md").unlink()
        _git(c, "commit", "-q", "-m", "se perdió en la copia local")
        faltan = [h["archivo"] for h in O.todos(self.raiz()) if h["tipo"] == "doc_vivo"]
        self.assertNotIn("docs/PRD.md", faltan)


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
    def test_apagado_por_defecto_y_se_enciende_con_el_comando(self):
        self.assertFalse(O.aplicar_encendido())
        with redirect_stdout(io.StringIO()):
            O.comando_config(True, False)
        self.assertTrue(O.aplicar_encendido())
        with redirect_stdout(io.StringIO()):
            O.comando_config(False, True)
        self.assertFalse(O.aplicar_encendido())

    def test_semanal_apagado_no_cambia_nada(self):
        c = _caja(self.td)
        self.mover(c)
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
        sens = [x for x in O.todos(self.raiz()) if x["tipo"] == "archivo_sensible"]
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


if __name__ == "__main__":
    unittest.main()
