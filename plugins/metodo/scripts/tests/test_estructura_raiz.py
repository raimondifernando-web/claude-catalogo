#!/usr/bin/env python3
"""test_estructura_raiz.py — el molde de raíz (docs/2026-10-18-molde-raiz.md): al nacer (`nueva`), al guardar (`exigir` y su enganche en
unir-pr), al cerrar (`exigir --contenido`, línea «Molde» de cerrar-check) y el número único «X de N» (`remoto`, resumen semanal)."""
import importlib.machinery
import importlib.util
import io
import json
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
import estructura_molde as M  # noqa: E402
import estructura_orden as O  # noqa: E402

COMPLETA = {"CLAUDE.md", ".gitignore", "docs/PRD.md", "docs/decisiones.md", "docs/planes/README.md"}
ESCRITO = ("Es una herramienta para ordenar los pedidos de los clientes de la tienda y avisar cuando uno se atrasa.\n")


def _git(cwd, *a, check=True):
    return subprocess.run(["git", "-C", str(cwd), "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false", *a],
                          capture_output=True, text=True, check=check).stdout.strip()


def _correr(fn, *a, **k):
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = fn(*a, **k)
    return rc, buf.getvalue()


class Base(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.td = Path(self._td.name)
        self.estado = self.td / "estado"
        self._env = {k: os.environ.get(k) for k in ("GIT_AUTHOR_NAME", "GIT_AUTHOR_EMAIL", "GIT_COMMITTER_NAME", "GIT_COMMITTER_EMAIL",
                                                    "METODO_SIN_REFRESCO", "CLAUDE_CONFIG_DIR", "GIT_CONFIG_GLOBAL")}
        for k, v in (("GIT_AUTHOR_NAME", "t"), ("GIT_COMMITTER_NAME", "t"), ("GIT_AUTHOR_EMAIL", "t@t"), ("GIT_COMMITTER_EMAIL", "t@t"),
                     ("METODO_SIN_REFRESCO", "1")):
            os.environ[k] = v
        os.environ["CLAUDE_CONFIG_DIR"] = str(self.td / "config")

    def tearDown(self):
        for k, v in self._env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        self._td.cleanup()

    def caja(self, nombre="caja", archivos=None, fecha=None):
        """Un repo con esos archivos en un commit; `fecha` (AAAA-MM-DD) fecha el commit (para probar «caja vieja»)."""
        c = self.td / nombre
        c.mkdir()
        _git(c, "init", "-q", "-b", "main")
        for rel, txt in (archivos if archivos is not None else {a: "x\n" for a in COMPLETA}).items():
            f = c / rel
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(txt, encoding="utf-8")
        _git(c, "add", "-f", "-A")
        env = dict(os.environ)
        if fecha:
            env["GIT_AUTHOR_DATE"] = env["GIT_COMMITTER_DATE"] = f"{fecha}T12:00:00"
        subprocess.run(["git", "-C", str(c), "commit", "-q", "-m", "base"], env=env, capture_output=True, check=True)
        return c

    def exigir(self, c, **k):
        return _correr(E.comando_exigir, repo_arg=str(c), estado_arg=str(self.estado), **k)


class TestMotor(Base):
    def leer_de(self, d):
        return lambda ruta: d.get(ruta)

    def test_caja_completa_no_tiene_faltas_de_estructura(self):
        archivos = {a: "x\n" for a in COMPLETA}
        m = M.medir(set(archivos), self.leer_de(archivos))
        self.assertEqual(m["duras"] + m["estructura"], [])

    def test_las_faltas_duras_y_de_estructura(self):
        m = M.medir({"README.md"}, lambda r: None)
        self.assertEqual({f["regla"] for f in m["duras"]}, {"R2", "R5"})
        self.assertEqual({f["regla"] for f in m["estructura"]}, {"R12"})
        self.assertEqual(len(m["estructura"]), 3)

    def test_archivos_personales_versionados_son_falta_dura_y_no_se_exceptuan(self):
        exc = json.dumps([{"regla": "R6", "ruta": ".", "motivo": "x", "fecha": "2026-10-18"}])
        d = {a: "x\n" for a in COMPLETA}
        d[M.ARCHIVO_EXCEPCIONES] = exc
        d[".env"] = "K=v\n"
        m = M.medir(set(d), self.leer_de(d))
        self.assertEqual([f["regla"] for f in m["duras"]], ["R6"])

    def test_con_codigo_se_piden_las_piezas_de_desarrollo(self):
        d = {a: "x\n" for a in COMPLETA}
        d["package.json"] = "{}\n"
        m = M.medir(set(d), self.leer_de(d))
        self.assertTrue(m["codigo"])
        self.assertEqual({f["que"].split()[-1] for f in m["estructura"] if f["regla"] == "R23"},
                         {"README.md", "docs/arquitectura.md", "docs/flujo-de-la-app.md", ".env.example"})

    def test_el_codigo_de_scripts_o_tests_no_cuenta_pero_el_de_servidor_si(self):
        solo_scripts = {f"scripts/a{i}.py" for i in range(8)} | {f"tests/t{i}.py" for i in range(8)}
        self.assertFalse(M.hay_codigo_en_arbol(solo_scripts))
        self.assertTrue(M.hay_codigo_en_arbol({f"servidor/m{i}.py" for i in range(5)}))
        self.assertTrue(M.hay_codigo_en_arbol({"src/app.py"}))

    def test_excepcion_con_motivo_fecha_y_plazo(self):
        hoy = date(2026, 10, 18)
        ok = json.dumps([{"regla": "R12", "ruta": ".", "motivo": "caja de paso", "fecha": "2026-10-18", "vence": "2026-12-01"}])
        v, _ = M.parsear_excepciones(ok, hoy)
        self.assertEqual(list(v), ["R12"])
        vencida = json.dumps([{"regla": "R12", "ruta": ".", "motivo": "caja de paso", "fecha": "2026-08-01", "vence": "2026-10-01"}])
        v, avisos = M.parsear_excepciones(vencida, hoy)
        self.assertEqual(v, {})
        self.assertIn("venció", avisos[0])
        sin_motivo = json.dumps([{"regla": "R12", "ruta": ".", "fecha": "2026-10-18"}])
        self.assertEqual(M.parsear_excepciones(sin_motivo, hoy)[0], {})

    def test_contenido_la_plantilla_con_la_cabecera_llena_sigue_sin_estar_escrita(self):
        prd = E.PLANTILLA_PRD.format(nombre="x").replace("- Dueño:\n", "- Dueño: Fer\n").replace("- Estado:\n", "- Estado: activa\n") \
            .replace("- Respaldo:\n", "- Respaldo: GitHub\n").replace("- Última revisión:\n", "- Última revisión: 2026-10-18\n")
        d = {a: "x\n" for a in COMPLETA}
        d["docs/PRD.md"] = prd
        m = M.medir(set(d), self.leer_de(d))
        self.assertTrue(any(f["regla"] == "R16" and "PRD" in f["que"] for f in m["contenido"]))

    def test_por_confirmar_no_cuenta_como_contenido(self):
        cabecera = "- Dueño: Fer\n- Estado: activa\n- Respaldo: GitHub\n- Última revisión: 2026-10-18\n"
        d = {a: "x\n" for a in COMPLETA}
        d["docs/PRD.md"] = "# PRD\n\n" + cabecera + "\nPor confirmar: qué es esta caja y para quién la usan los clientes.\n"
        m = M.medir(set(d), self.leer_de(d))
        self.assertTrue(any(f["regla"] == "R16" and "PRD" in f["que"] for f in m["contenido"]))
        # escrito de verdad: ya no hay faltas de contenido
        d["docs/PRD.md"] = "# PRD\n\n" + cabecera + "\n" + ESCRITO
        d["docs/decisiones.md"] = "# D\n\n## 2026-10-18 — Una sola planilla\nPorque tener dos planillas distintas se desfasaba y nadie sabía cuál valía.\n"
        m = M.medir(set(d), self.leer_de(d))
        self.assertEqual(m["contenido"], [])
        self.assertTrue(M.esta_completa(m))


class TestNueva(Base):
    def test_una_caja_nueva_nace_completa_y_pasa_el_molde(self):
        destino = self.td / "mi-caja"
        rc, sal = _correr(E.comando_nueva, str(destino), "proyecto", False, "Fer")
        self.assertEqual(rc, 0)
        self.assertIn("Pasa el molde", sal)
        self.assertIn("gh repo create", sal)
        for rel in COMPLETA | {".claude/settings.json"}:
            self.assertTrue((destino / rel).is_file() or rel == "docs/planes/README.md", rel)
        self.assertEqual(_git(destino, "status", "--porcelain"), "")   # todo quedó en el primer commit
        prd = (destino / "docs/PRD.md").read_text(encoding="utf-8")
        self.assertIn("- Dueño: Fer", prd)
        self.assertIn("- Estado: activa", prd)
        self.assertIn(date.today().isoformat(), prd)
        rc, _ = self.exigir(destino)
        self.assertEqual(rc, 0)

    def test_con_codigo_trae_las_piezas_de_desarrollo(self):
        destino = self.td / "app"
        rc, _ = _correr(E.comando_nueva, str(destino), "proyecto", True, "")
        self.assertEqual(rc, 0)
        for rel in ("README.md", "docs/arquitectura.md", "docs/flujo-de-la-app.md", ".env.example", ".claude/rules/donde-va-cada-cosa.md"):
            self.assertTrue((destino / rel).is_file(), rel)
        self.assertIn("Por confirmar", (destino / "docs/PRD.md").read_text(encoding="utf-8"))   # sin dueño: queda a la vista

    def test_el_gitignore_de_una_caja_nueva_deja_viajar_el_settings(self):
        destino = self.td / "x"
        _correr(E.comando_nueva, str(destino))
        self.assertIn("!.claude/settings.json", (destino / ".gitignore").read_text(encoding="utf-8"))

    def test_no_pisa_una_carpeta_que_ya_tiene_cosas(self):
        destino = self.td / "ocupada"
        destino.mkdir()
        (destino / "mio.txt").write_text("importante\n", encoding="utf-8")
        rc, sal = _correr(E.comando_nueva, str(destino))
        self.assertEqual(rc, 1)
        self.assertEqual((destino / "mio.txt").read_text(encoding="utf-8"), "importante\n")
        self.assertFalse((destino / "CLAUDE.md").exists())

    def test_el_mismo_programa_que_crea_es_el_que_mide(self):
        # si alguien cambia la plantilla y rompe el molde, esta prueba lo agarra: nace completa o no nace
        destino = self.td / "y"
        _correr(E.comando_nueva, str(destino), "area", True, "Fer")
        archivos, leer, _ = E.arbol_de_commit(destino, "HEAD")
        m = M.medir(archivos, leer)
        self.assertEqual(m["duras"] + m["estructura"], [])


class TestExigir(Base):
    def test_una_caja_incompleta_se_frena_con_el_comando_que_lo_arregla(self):
        c = self.caja(archivos={"CLAUDE.md": "# x\n"})
        rc, sal = self.exigir(c)
        self.assertEqual(rc, 1)
        self.assertIn("R5", sal)
        self.assertIn("R12", sal)
        self.assertIn("estructura.py arreglar --si", sal)

    def test_una_caja_completa_pasa(self):
        rc, sal = self.exigir(self.caja())
        self.assertEqual(rc, 0)
        self.assertIn("Molde ✓", sal)

    def test_una_caja_vieja_tiene_plazo_de_30_dias_y_despues_frena(self):
        vieja = (date.today() - timedelta(days=200)).isoformat()
        c = self.caja(archivos={"CLAUDE.md": "# x\n", ".gitignore": ".env\n"}, fecha=vieja)
        rc, sal = self.exigir(c)
        self.assertEqual(rc, 0)
        self.assertIn("plazo hasta", sal)
        estado = json.loads((self.estado / "molde-arrastre.json").read_text(encoding="utf-8"))
        (clave, e), = estado.items()
        self.assertEqual(e["vence"], (date.today() + timedelta(days=E.DIAS_ARRASTRE)).isoformat())
        # 29 días después sigue pasando; 31 días después frena
        rc, _ = self.exigir(c, hoy_arg=(date.today() + timedelta(days=29)).isoformat())
        self.assertEqual(rc, 0)
        rc, sal = self.exigir(c, hoy_arg=(date.today() + timedelta(days=31)).isoformat())
        self.assertEqual(rc, 1)
        self.assertIn("R12", sal)

    def test_una_caja_nueva_no_tiene_plazo(self):
        c = self.caja(archivos={"CLAUDE.md": "# x\n", ".gitignore": ".env\n"})   # primer commit de hoy
        rc, _ = self.exigir(c)
        self.assertEqual(rc, 1)
        self.assertFalse((self.estado / "molde-arrastre.json").exists())

    def test_lo_duro_no_tiene_plazo_ni_en_una_caja_vieja(self):
        vieja = (date.today() - timedelta(days=200)).isoformat()
        c = self.caja(archivos={"docs/PRD.md": "x\n", "docs/decisiones.md": "x\n", "docs/planes/README.md": "x\n"}, fecha=vieja)
        rc, sal = self.exigir(c)
        self.assertEqual(rc, 1)
        self.assertIn("R2", sal)

    def test_una_excepcion_escrita_con_motivo_deja_pasar_y_la_vencida_no(self):
        hoy = date.today()
        exc = lambda vence: json.dumps([{"regla": "R12", "ruta": ".", "motivo": "caja de paso", "fecha": hoy.isoformat(), "vence": vence}])
        base = {"CLAUDE.md": "# x\n", ".gitignore": ".env\n"}
        c = self.caja("a", archivos={**base, M.ARCHIVO_EXCEPCIONES: exc((hoy + timedelta(days=60)).isoformat())})
        rc, sal = self.exigir(c)
        self.assertEqual(rc, 0)
        self.assertIn("excepción R12", sal)
        c2 = self.caja("b", archivos={**base, M.ARCHIVO_EXCEPCIONES: exc((hoy - timedelta(days=1)).isoformat())})
        rc, sal = self.exigir(c2)
        self.assertEqual(rc, 1)
        self.assertIn("venció", sal)

    def test_un_error_del_control_nunca_frena(self):
        rc, sal = _correr(E.comando_exigir, commit="no-existe", repo_arg=str(self.caja()), estado_arg=str(self.estado))
        self.assertEqual(rc, 2)
        self.assertIn("no frena", sal)
        rc, sal = _correr(E.comando_exigir, repo_arg=str(self.td), estado_arg=str(self.estado))   # ni siquiera es un repo
        self.assertEqual(rc, 2)

    def test_el_cierre_exige_contenido_solo_en_cajas_con_producto(self):
        # sin producto (ni código ni historia): la estructura alcanza
        c = self.caja("paso")
        rc, _ = self.exigir(c, contenido=True)
        self.assertEqual(rc, 0)
        # con código: el PRD en plantilla frena el CIERRE (no la unión)
        d = {a: "x\n" for a in COMPLETA}
        d.update({"package.json": "{}\n", "README.md": "x\n", "docs/arquitectura.md": "x\n", "docs/flujo-de-la-app.md": "x\n", ".env.example": "x\n"})
        c2 = self.caja("app", archivos=d)
        rc, sal = self.exigir(c2)
        self.assertEqual(rc, 0)   # unir: pasa
        rc, sal = self.exigir(c2, contenido=True)
        self.assertEqual(rc, 1)   # cerrar: falta escribirlo
        self.assertIn("R16", sal)
        self.assertIn("paso 3 bis", sal)

    def test_el_cierre_pasa_cuando_los_documentos_estan_escritos(self):
        d = {a: "x\n" for a in COMPLETA}
        d.update({"package.json": "{}\n", "README.md": "x\n", "docs/arquitectura.md": "x\n", "docs/flujo-de-la-app.md": "x\n", ".env.example": "x\n"})
        d["docs/PRD.md"] = "# PRD\n\n- Dueño: Fer\n- Estado: activa\n- Respaldo: GitHub\n- Última revisión: 2026-10-18\n\n" + ESCRITO
        d["docs/decisiones.md"] = "# D\n\n## 2026-10-18 — Una sola planilla\nPorque tener dos planillas distintas se desfasaba y nadie sabía cuál valía.\n"
        rc, sal = self.exigir(self.caja("app2", archivos=d), contenido=True)
        self.assertEqual(rc, 0, sal)

    def test_exigir_lee_el_commit_no_la_carpeta(self):
        c = self.caja()
        (c / "docs" / "PRD.md").unlink()   # borrado en el disco pero SIN commitear: el commit sigue completo
        rc, _ = self.exigir(c)
        self.assertEqual(rc, 0)
        _git(c, "rm", "-q", "docs/PRD.md")
        _git(c, "commit", "-q", "-m", "saco el PRD")
        rc, _ = self.exigir(c)
        self.assertEqual(rc, 1)


class TestUnirPr(Base):
    """El enganche en unir-pr: trae pull/N/head y mide ese commit (con un origen local, sin tocar GitHub)."""

    def cargar(self):
        ruta = SCRIPTS_DIR / "unir-pr"
        loader = importlib.machinery.SourceFileLoader("unir_pr", str(ruta))
        mod = importlib.util.module_from_spec(importlib.util.spec_from_loader("unir_pr", loader))
        loader.exec_module(mod)
        return mod

    def repo_con_pr(self, archivos, nombre="trabajo"):
        origen = self.td / f"{nombre}-origen.git"
        trabajo = self.caja(nombre, archivos=archivos)
        subprocess.run(["git", "clone", "-q", "--bare", str(trabajo), str(origen)], check=True, capture_output=True)
        _git(trabajo, "remote", "add", "origin", str(origen))
        _git(trabajo, "push", "-q", "origin", "HEAD:refs/pull/7/head")
        return trabajo

    def medir_pr(self, carpeta, repo_pedido=None):
        m = self.cargar()
        cwd = os.getcwd()
        try:
            os.chdir(carpeta)
            return m.molde(7, repo_pedido)
        finally:
            os.chdir(cwd)

    def test_el_pr_incompleto_frena_y_el_completo_pasa(self):
        frena, texto = self.medir_pr(self.repo_con_pr({"CLAUDE.md": "# x\n"}, "incompleto"))
        self.assertTrue(frena)
        self.assertIn("R12", texto)
        frena, texto = self.medir_pr(self.repo_con_pr({a: "x\n" for a in COMPLETA}, "completo"))
        self.assertFalse(frena, texto)
        self.assertIn("Molde ✓", texto)

    def test_un_pr_de_otro_repositorio_no_se_mide(self):
        frena, texto = self.medir_pr(self.repo_con_pr({"CLAUDE.md": "# x\n"}, "ajeno"), "alguien/otro-repo")
        self.assertFalse(frena)
        self.assertIn("otro repositorio", texto)

    def test_las_excepciones_al_molde_son_zona_sensible_en_unir_pr(self):
        m = self.cargar()
        import fnmatch
        self.assertTrue(any(fnmatch.fnmatch(".estructura-excepciones.json", p) for p in m.SENSIBLE))
        self.assertTrue(any(fnmatch.fnmatch("sub/.estructura-excepciones.json", p) for p in m.SENSIBLE))


class TestNumero(Base):
    def origen(self, nombre, archivos):
        o = self.caja(nombre + "-semilla", archivos=archivos)
        bare = self.td / (nombre + ".git")
        subprocess.run(["git", "clone", "-q", "--bare", str(o), str(bare)], check=True, capture_output=True)
        raiz = self.td / "proyectos"
        raiz.mkdir(exist_ok=True)
        subprocess.run(["git", "clone", "-q", str(bare), str(raiz / nombre)], check=True, capture_output=True)
        return raiz

    def test_el_numero_cuenta_cajas_completas_en_github_y_se_guarda(self):
        escritos = {a: "x\n" for a in COMPLETA}
        escritos["docs/PRD.md"] = "# PRD\n\n- Dueño: Fer\n- Estado: activa\n- Respaldo: GitHub\n- Última revisión: 2026-10-18\n\n" + ESCRITO
        escritos["docs/decisiones.md"] = "# D\n\n## 2026-10-18 — Una sola planilla\nPorque tener dos planillas distintas se desfasaba y nadie sabía cuál valía.\n"
        raiz = self.origen("completa", escritos)
        self.origen("incompleta", {"CLAUDE.md": "# x\n"})   # otra caja en la misma raíz
        rc, sal = _correr(E.comando_remoto, str(raiz), True, True, 0, str(self.estado))
        self.assertIn("1 de 2 cajas completas (en GitHub)", sal)
        guardado = json.loads((self.estado / "molde-numero.json").read_text(encoding="utf-8"))
        self.assertEqual((guardado["completas"], guardado["total"]), (1, 2))
        self.assertIn("Cajas completas: 1 de 2", E.numero_guardado(str(self.estado)))

    def test_un_numero_viejo_no_se_muestra(self):
        (self.estado).mkdir()
        viejo = (date.today() - timedelta(days=30)).isoformat()
        (self.estado / "molde-numero.json").write_text(json.dumps({"fecha": viejo, "completas": 3, "total": 9}), encoding="utf-8")
        self.assertIsNone(E.numero_guardado(str(self.estado)))

    def test_el_resumen_semanal_trae_el_numero(self):
        self.estado.mkdir()
        (self.estado / "molde-numero.json").write_text(
            json.dumps({"fecha": date.today().isoformat(), "completas": 7, "total": 32}), encoding="utf-8")
        os.environ["CLAUDE_CONFIG_DIR"] = str(self.td / "x")
        (self.td / "x" / "metodo-estado").mkdir(parents=True)
        (self.td / "x" / "metodo-estado" / "molde-numero.json").write_text(
            json.dumps({"fecha": date.today().isoformat(), "completas": 7, "total": 32}), encoding="utf-8")
        lineas = O.resumen_semanal(str(self.td), [])
        self.assertEqual(len(lineas), 4)
        self.assertIn("7 de 32", lineas[3])


class TestRevisionExternaRaiz(Base):
    """Lo que encontró la revisión independiente (2026-10-18) y se comprobó."""

    def test_vence_null_o_roto_no_borra_la_excepcion_sin_avisar(self):
        hoy = date(2026, 10, 18)
        nulo = json.dumps([{"regla": "R12", "ruta": ".", "motivo": "en curso", "fecha": "2026-10-18", "vence": None}])
        self.assertEqual(list(M.parsear_excepciones(nulo, hoy)[0]), ["R12"])
        roto = json.dumps([{"regla": "R12", "ruta": ".", "motivo": "en curso", "fecha": "2026-10-18", "vence": "mañana"}])
        v, avisos = M.parsear_excepciones(roto, hoy)
        self.assertEqual(v, {})
        self.assertIn("vence", avisos[0])

    def test_una_carpeta_test_no_cuenta_como_codigo(self):
        self.assertFalse(M.hay_codigo_en_arbol({f"test/t{i}.py" for i in range(8)} | {f"__tests__/t{i}.js" for i in range(8)}))

    def test_un_estado_corrupto_nunca_frena_la_union(self):
        vieja = (date.today() - timedelta(days=200)).isoformat()
        c = self.caja(archivos={"CLAUDE.md": "# x\n", ".gitignore": ".env\n"}, fecha=vieja)
        self.estado.mkdir()
        clave = E._identidad_de_caja(c)
        (self.estado / "molde-arrastre.json").write_text(json.dumps({clave: "corrupto"}), encoding="utf-8")
        rc, sal = self.exigir(c)
        self.assertEqual(rc, 2, sal)
        self.assertIn("no frena", sal)

    def test_una_carpeta_sin_repositorio_en_github_no_impide_guardar_el_numero(self):
        escritos = {a: "x\n" for a in COMPLETA}
        raiz = TestNumero.origen(self, "con-remoto", escritos)
        suelta = raiz / "solo-local"
        suelta.mkdir()
        _git(suelta, "init", "-q", "-b", "main")
        (suelta / "CLAUDE.md").write_text("# x\n", encoding="utf-8")
        rc, sal = _correr(E.comando_remoto, str(raiz), True, True, 0, str(self.estado))
        self.assertIn("1 sin repositorio en GitHub", sal)
        self.assertTrue((self.estado / "molde-numero.json").is_file())

    def test_si_se_acaba_el_tiempo_no_se_guarda_un_numero_a_medias(self):
        raiz = TestNumero.origen(self, "una", {a: "x\n" for a in COMPLETA})
        TestNumero.origen(self, "dos", {a: "x\n" for a in COMPLETA})
        rc, sal = _correr(E.comando_remoto, str(raiz), False, True, 1e-9, str(self.estado))   # tope de tiempo ridículo
        self.assertIn("sin poder medir", sal)
        self.assertFalse((self.estado / "molde-numero.json").exists())

    def test_el_comando_para_github_no_usa_sustitucion_de_shell(self):
        destino = self.td / "sin-dueno"
        rc, sal = _correr(E.comando_nueva, str(destino))
        self.assertNotIn("$(", sal)
        self.assertIn('gh repo create "sin-dueno"', sal)

    def test_el_fetch_en_segundo_plano_nunca_pregunta(self):
        env = E.entorno_sin_preguntas()
        self.assertEqual(env["GIT_TERMINAL_PROMPT"], "0")
        self.assertEqual(env["GCM_INTERACTIVE"], "never")
        self.assertIn("BatchMode=yes", env["GIT_SSH_COMMAND"])


class TestExenta(Base):
    """Una carpeta que el dueño dejó FUERA del molde (campo de pruebas): ni se revisa ni se cuenta, ella ni lo de adentro."""

    def armar(self, excepcion):
        raiz = self.td / "proyectos"
        madre = raiz / "madre"
        madre.mkdir(parents=True)
        _git(madre, "init", "-q", "-b", "main")
        (madre / "CLAUDE.md").write_text("# madre\n", encoding="utf-8")
        sandbox = madre / "sandbox"
        (sandbox / "herramienta").mkdir(parents=True)
        (sandbox / "CLAUDE.md").write_text("# pruebas\n", encoding="utf-8")
        _git(sandbox / "herramienta", "init", "-q", "-b", "main")   # una herramienta de terceros clonada adentro
        (sandbox / "herramienta" / "CLAUDE.md").write_text("# ajena\n", encoding="utf-8")
        if excepcion is not None:
            (madre / ".estructura-excepciones.json").write_text(json.dumps(excepcion), encoding="utf-8")
        return raiz

    def nombres(self, raiz):
        return {str(c.relative_to(raiz)) for c, _n, _p in E.descubrir_cajas(raiz)}

    def test_sin_excepcion_el_campo_de_pruebas_se_revisa(self):
        self.assertEqual(self.nombres(self.armar(None)), {"madre", "madre/sandbox", "madre/sandbox/herramienta"})

    def test_exenta_saca_la_carpeta_y_todo_lo_de_adentro(self):
        raiz = self.armar([{"regla": "EXENTA", "ruta": "sandbox", "motivo": "campo de pruebas descartable", "fecha": "2026-10-18"}])
        self.assertEqual(self.nombres(raiz), {"madre"})

    def test_exenta_sin_motivo_o_con_otra_ruta_no_vale(self):
        raiz = self.armar([{"regla": "EXENTA", "ruta": "sandbox", "fecha": "2026-10-18"},
                           {"regla": "EXENTA", "ruta": "otra", "motivo": "x", "fecha": "2026-10-18"}])
        self.assertIn("madre/sandbox", self.nombres(raiz))

    def test_exenta_vencida_deja_de_valer(self):
        ayer = (date.today() - timedelta(days=1)).isoformat()
        raiz = self.armar([{"regla": "EXENTA", "ruta": "sandbox", "motivo": "x", "fecha": "2026-10-01", "vence": ayer}])
        self.assertIn("madre/sandbox", self.nombres(raiz))

    def test_lo_exento_no_aparece_ni_en_el_control_ni_en_el_numero(self):
        raiz = self.armar([{"regla": "EXENTA", "ruta": "sandbox", "motivo": "campo de pruebas", "fecha": "2026-10-18"}])
        rc, sal = _correr(E.comando_revisar, todas=True, raiz_arg=str(raiz))
        self.assertIn("madre", sal)                # la caja de arriba sí se revisa
        self.assertNotIn("madre/sandbox", sal)     # la carpeta exenta (y lo de adentro) no
        rc, sal = _correr(E.comando_remoto, str(raiz), False, False, 0, str(self.estado))
        self.assertNotIn("madre/sandbox", sal)


class TestCerrarCheck(Base):
    def test_cerrar_check_tiene_la_linea_del_molde_y_frena_si_falta_algo(self):
        c = self.caja("cierre", archivos={"CLAUDE.md": "# x\n"})
        r = subprocess.run([sys.executable, str(SCRIPTS_DIR / "cerrar-check.py"), str(c)], capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=120,
                           env={**os.environ, "CLAUDE_CONFIG_DIR": str(self.td / "config")})
        self.assertIn("Molde de la caja", r.stdout)
        self.assertIn("✗ Molde de la caja", r.stdout)
        self.assertEqual(r.returncode, 1)
        self.assertIn("paso 3 bis", r.stdout)

    def test_el_paso_3_bis_esta_en_la_skill_y_tiene_su_disparador(self):
        skill = (SCRIPTS_DIR.parent / "skills" / "cerrar" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("3 bis", skill)
        self.assertIn("docs/decisiones.md", skill)
        self.assertIn("Por confirmar", skill)
        self.assertIn("Disparador:", skill)


if __name__ == "__main__":
    unittest.main()
