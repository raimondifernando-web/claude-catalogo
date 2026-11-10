#!/usr/bin/env python3
"""Pruebas del job resumen `controles` (C271b, 2026-11-10; análisis: Tech/docs/2026-11-10-pruebas-obligatorias-catalogo.md).

Cuidan cuatro cosas:
  1. la matriz de pruebas (`tests` y `hook-bash`) es IGUAL en controles.yml (PR) y vigia-tests.yml (después de unir);
  2. los nombres de los jobs siguen empezando como los lee la compuerta de `estable` (PRUEBAS en estable-avanzar.py);
  3. el detector `cambios` NUNCA da «no toca el plugin» por error: ante duda o fallo manda correr todo (se corre su script real);
  4. el resumen `controles` exige `success` de lo que tenía que correr: un job salteado por error no lo pone en verde
     (se corre su script real con todas las combinaciones de resultados).
Corridas: python3 -m unittest discover -s scripts/tests
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
CONTROLES = (RAIZ / ".github/workflows/controles.yml").read_text(encoding="utf-8")
VIGIA = (RAIZ / ".github/workflows/vigia-tests.yml").read_text(encoding="utf-8")
ESTABLE = (RAIZ / "scripts/estable-avanzar.py").read_text(encoding="utf-8")


def _sin_comentarios(lineas):
    return [l.rstrip() for l in lineas if l.strip() and not l.lstrip().startswith("#")]


def bloque_job(texto: str, job: str) -> list[str]:
    """Líneas del job `job` (sangría 2) dentro de `jobs:`."""
    lineas = texto.splitlines()
    ini = next(i for i, l in enumerate(lineas) if l == f"  {job}:")
    fin = len(lineas)
    for i in range(ini + 1, len(lineas)):
        if re.match(r"^  [A-Za-z0-9_-]+:\s*$", lineas[i]):
            fin = i
            break
    return lineas[ini + 1:fin]


def clave_job(bloque: list[str], clave: str) -> list[str]:
    """Líneas de la clave `clave` (sangría 4) de un job, sin comentarios de línea completa."""
    ini = next((i for i, l in enumerate(bloque) if re.match(rf"^    {re.escape(clave)}:", l)), None)
    if ini is None:
        return []
    fin = len(bloque)
    for i in range(ini + 1, len(bloque)):
        if re.match(r"^    [A-Za-z0-9_-]+:", bloque[i]):
            fin = i
            break
    return _sin_comentarios(bloque[ini:fin])


def script_despues_de(texto: str, marca: str) -> str:
    """Contenido del primer `run: |` que aparece después de la línea que contiene `marca`."""
    lineas = texto.splitlines()
    i0 = next(i for i, l in enumerate(lineas) if marca in l)
    i1 = next(i for i in range(i0, len(lineas)) if lineas[i].strip() == "run: |")
    sangria = len(lineas[i1]) - len(lineas[i1].lstrip())
    cuerpo = []
    for l in lineas[i1 + 1:]:
        if l.strip() and (len(l) - len(l.lstrip())) <= sangria:
            break
        cuerpo.append(l)
    return textwrap.dedent("\n".join(cuerpo)) + "\n"


def patron_de_cambios() -> str:
    m = re.search(r"^\s+PATRON: '(.*)'\s*$", CONTROLES, re.M)
    assert m, "no encuentro PATRON en controles.yml"
    return m.group(1)


def rutas_del_push() -> list[str]:
    lineas = VIGIA.splitlines()
    i0 = next(i for i, l in enumerate(lineas) if l.strip() == "paths:")
    rutas = []
    for l in lineas[i0 + 1:]:
        m = re.match(r'^\s+- "(.*)"\s*$', l)
        if not m:
            break
        rutas.append(m.group(1))
    return rutas


def glob_a_regex(g: str) -> str:
    return "^" + re.escape(g).replace(r"\*\*", ".*") + "$"


class MatrizIgual(unittest.TestCase):
    def test_tests_y_hook_son_iguales_en_los_dos_archivos(self):
        for job in ("tests", "hook-bash"):
            a, b = bloque_job(CONTROLES, job), bloque_job(VIGIA, job)
            for clave in ("name", "runs-on", "timeout-minutes", "strategy", "steps"):
                self.assertEqual(clave_job(a, clave), clave_job(b, clave), f"{job}: «{clave}» difiere entre controles.yml y vigia-tests.yml")
                self.assertTrue(clave_job(a, clave), f"{job}: falta «{clave}»")

    def test_los_nombres_de_job_son_los_que_lee_la_compuerta_de_estable(self):
        m = re.search(r"^PRUEBAS = \((.*)\)", ESTABLE, re.M)
        self.assertIsNotNone(m, "no encuentro PRUEBAS en estable-avanzar.py")
        prefijos = re.findall(r'"([^"]*)"', m.group(1))
        self.assertEqual(sorted(prefijos), sorted(["tests (", "comando del hook con bash ("]))
        for texto in (CONTROLES, VIGIA):
            nombres = [clave_job(bloque_job(texto, j), "name")[0] for j in ("tests", "hook-bash")]
            for p in prefijos:
                self.assertTrue(any(n.split(":", 1)[1].strip().startswith(p) for n in nombres), f"ningún job empieza con «{p}»")

    def test_vigia_tests_no_se_dispara_por_pull_request(self):
        self.assertNotRegex(VIGIA, r"(?m)^  pull_request:")
        self.assertRegex(VIGIA, r"(?m)^  push:")


class Estructura(unittest.TestCase):
    def test_el_resumen_se_llama_controles_siempre_corre_y_espera_a_todo(self):
        b = bloque_job(CONTROLES, "controles")
        self.assertEqual(clave_job(b, "name"), ["    name: controles"])
        self.assertEqual(clave_job(b, "if"), ["    if: ${{ always() }}"], "el resumen debe llevar `always()` (con `!cancelled()` se saltearía y un salteado cuenta como éxito)")
        needs = re.findall(r"[A-Za-z0-9-]+", clave_job(b, "needs")[0].split(":", 1)[1])
        self.assertEqual(sorted(needs), sorted(["cambios", "controles-mac", "tests", "hook-bash"]))

    def test_las_pruebas_esperan_a_cambios(self):
        for job in ("tests", "hook-bash"):
            b = bloque_job(CONTROLES, job)
            self.assertEqual(clave_job(b, "needs"), ["    needs: cambios"])
            self.assertIn("needs.cambios.outputs.metodo == 'true'", " ".join(clave_job(b, "if")))

    def test_cambios_baja_el_historial_completo(self):
        self.assertIn("fetch-depth: 0", "\n".join(bloque_job(CONTROLES, "cambios")))

    def test_ningun_job_nuevo_usa_secretos_ni_pull_request_target(self):
        self.assertNotIn("secrets.", CONTROLES)
        self.assertNotRegex(CONTROLES, r"(?m)^\s*pull_request_target:")


class PatronDeRutas(unittest.TestCase):
    CASOS = {
        "plugins/metodo/scripts/x.py": True,
        "plugins/metodo/.claude-plugin/plugin.json": True,
        "plugins/rubro-finanzas-legal/skills/a.md": False,
        "plugins/base-segura/x": False,
        "scripts/radar-fuentes.py": True,
        "scripts/radar-fuentes.pyc": False,
        "scripts/estable-avanzar.py": True,
        "scripts/controles.sh": True,
        "scripts/otro.sh": False,
        ".github/workflows/vigia-tests.yml": True,
        ".github/workflows/estable.yml": True,
        ".github/workflows/controles.yml": True,
        ".github/workflows/radar.yml": False,
        ".github/workflows/zona-sensible.yml": False,
        ".github/rulesets/x.json": True,
        ".github/rulesets/proteger-main.json": True,
        "docs/x.md": False,
        "README.md": False,
    }

    def test_casos_reales(self):
        pat = re.compile(patron_de_cambios())
        for ruta, esperado in self.CASOS.items():
            self.assertEqual(bool(pat.search(ruta)), esperado, ruta)

    def test_el_patron_dice_lo_mismo_que_las_rutas_de_vigia_tests(self):
        """Las rutas de `paths:` (glob) y el PATRON (regex) tienen que decidir igual para los mismos archivos."""
        pat = re.compile(patron_de_cambios())
        globs = [re.compile(glob_a_regex(g)) for g in rutas_del_push()]
        candidatos = list(self.CASOS) + [g.replace("**", "algo/mas.txt") for g in rutas_del_push()]
        for ruta in candidatos:
            self.assertEqual(bool(pat.search(ruta)), any(g.search(ruta) for g in globs), f"el patrón y los `paths` de vigia-tests no coinciden en: {ruta}")


@unittest.skipUnless(shutil.which("bash") and shutil.which("git"), "hace falta bash y git")
class DetectorDeCambios(unittest.TestCase):
    """Corre el script REAL del paso `dif` de controles.yml en un repo de juguete."""

    @classmethod
    def setUpClass(cls):
        cls.script = script_despues_de(CONTROLES, "id: dif")
        cls.patron = patron_de_cambios()

    def _repo(self, d: Path, archivo: str):
        def git(*a):
            return subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", "-c", "init.defaultBranch=main", *a],
                                  cwd=d, check=True, capture_output=True, text=True).stdout.strip()
        git("init")
        (d / "README.md").write_text("base\n")
        git("add", "-A"); git("commit", "-m", "base")
        base = git("rev-parse", "HEAD")
        ruta = d / archivo
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text("cambio\n")
        git("add", "-A"); git("commit", "-m", "cambio")
        return base, git("rev-parse", "HEAD")

    def _correr(self, archivo="docs/x.md", **cambia):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            base, cabeza = self._repo(d, archivo)
            env = {**os.environ, "EVENTO": "pull_request", "BASE": base, "CABEZA": cabeza, "PATRON": self.patron,
                   "GITHUB_OUTPUT": str(d / "salida.txt")}
            env.update(cambia)
            (d / "salida.txt").write_text("")
            for opciones in ("-e", "-eo pipefail"):   # así corre un `run:` de GitHub (sin shell: bash -e; con `shell: bash`: -eo pipefail)
                (d / "salida.txt").write_text("")
                r = subprocess.run(["bash", *opciones.split(), "-c", self.script], cwd=d, env=env, capture_output=True, text=True)
                self.assertEqual(r.returncode, 0, f"bash {opciones}: {r.stderr}")
                resultado = (d / "salida.txt").read_text().strip()
                if opciones == "-e":
                    primero = resultado
                else:
                    self.assertEqual(resultado, primero, "el resultado cambia con pipefail")
            return primero

    def test_solo_docs_no_corre_la_matriz(self):
        self.assertEqual(self._correr("docs/x.md"), "metodo=false")

    def test_tocar_el_plugin_corre_la_matriz(self):
        self.assertEqual(self._correr("plugins/metodo/a.py"), "metodo=true")

    def test_tocar_los_propios_controles_corre_la_matriz(self):
        self.assertEqual(self._correr(".github/workflows/controles.yml"), "metodo=true")
        self.assertEqual(self._correr("scripts/controles.sh"), "metodo=true")

    def test_base_inexistente_corre_todo(self):
        # el caso del checkout superficial: git no encuentra la base y diff falla
        self.assertEqual(self._correr("docs/x.md", BASE="0" * 40), "metodo=true")

    def test_sin_base_o_sin_cabeza_corre_todo(self):
        self.assertEqual(self._correr("docs/x.md", BASE=""), "metodo=true")
        self.assertEqual(self._correr("docs/x.md", CABEZA=""), "metodo=true")

    def test_el_robot_por_workflow_dispatch_corre_todo(self):
        self.assertEqual(self._correr("docs/x.md", EVENTO="workflow_dispatch", BASE="", CABEZA=""), "metodo=true")

    def test_patron_roto_corre_todo(self):
        self.assertEqual(self._correr("docs/x.md", PATRON="("), "metodo=true")

    def test_sin_diferencias_corre_todo(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            base, cabeza = self._repo(d, "docs/x.md")
            env = {**os.environ, "EVENTO": "pull_request", "BASE": cabeza, "CABEZA": cabeza, "PATRON": self.patron,
                   "GITHUB_OUTPUT": str(d / "o.txt")}
            (d / "o.txt").write_text("")
            subprocess.run(["bash", "-e", "-c", self.script], cwd=d, env=env, check=True, capture_output=True)
            self.assertEqual((d / "o.txt").read_text().strip(), "metodo=true")


@unittest.skipUnless(shutil.which("bash"), "hace falta bash")
class ResumenExigeSuccess(unittest.TestCase):
    """Corre el script REAL del paso «Resumen» con todas las combinaciones de resultados."""

    @classmethod
    def setUpClass(cls):
        cls.script = script_despues_de(CONTROLES, "name: Resumen")

    def _rc(self, cambios="success", metodo="true", mac="success", tests="success", hook="success"):
        env = {**os.environ, "CAMBIOS": cambios, "METODO": metodo, "MAC": mac, "TESTS": tests, "HOOK": hook}
        return subprocess.run(["bash", "-e", "-c", self.script], env=env, capture_output=True, text=True).returncode

    def test_todo_en_verde(self):
        self.assertEqual(self._rc(), 0)

    def test_pr_que_no_toca_el_plugin_con_la_matriz_salteada(self):
        self.assertEqual(self._rc(metodo="false", tests="skipped", hook="skipped"), 0)

    def test_cualquier_rojo_o_cancelado_falla(self):
        for campo in ("mac", "tests", "hook", "cambios"):
            for malo in ("failure", "cancelled"):
                self.assertEqual(self._rc(**{campo: malo}), 1, f"{campo}={malo}")

    def test_salteado_donde_tenia_que_correr_NO_es_verde(self):
        # el hueco que un `skipped` = éxito abriría: cambios dijo «correr» y la matriz no corrió
        self.assertEqual(self._rc(tests="skipped"), 1)
        self.assertEqual(self._rc(hook="skipped"), 1)
        self.assertEqual(self._rc(cambios="skipped"), 1)
        self.assertEqual(self._rc(mac="skipped"), 1)

    def test_si_cambios_no_dijo_true_o_false_falla(self):
        for raro in ("", "TRUE", "si", "null"):
            self.assertEqual(self._rc(metodo=raro), 1, repr(raro))

    def test_cambios_caido_falla_aunque_lo_demas_este_salteado(self):
        self.assertEqual(self._rc(cambios="failure", metodo="", tests="skipped", hook="skipped"), 1)


if __name__ == "__main__":
    unittest.main()
