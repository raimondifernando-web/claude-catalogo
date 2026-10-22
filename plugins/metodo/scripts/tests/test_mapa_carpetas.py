#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_mapa_carpetas.py - Pruebas unitarias para la lista de carpetas de proyecto de ~/Proyectos.
Disparador: encadenado — lo llaman Energía y quien necesite la lista de carpetas

Verifica:
  1. Los campos de cada carpeta (ruta, nombre, grupo, area, nivel, tipo, flags) y orden por ruta.
  2. Filtros --tipo dormido, --tipo archivo, y --grupo.
  3. Borrar una carpeta desaparece en la consulta siguiente; crear una nueva aparece.
  4. Crear y borrar carpeta oculta no altera reconstrucciones; carpeta visible nueva suma 1.
  5. La lista proyectos (arneses) no contiene el .claude de .wt-copia.
  6. --json emite JSON válido y coincide con la salida de texto.
  7. Sin Proyectos imprime «ninguna carpeta coincide» y sale 0.
  8. mapa_io: prueba directa de obtener_nombres_relevantes en modo proyectos nivel 1.
  9. Función pública listar_carpetas API para otros programas.
  10. MAPA.md contiene la línea de conteo de carpetas de proyecto y no supera 4096 bytes.

Python 3.9 estándar, sin librerías externas.
"""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Dict, List, Optional, Tuple, Union
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mapa_io import IO, obtener_nombres_relevantes
import mapa
import mapa_lector


MAPA_SCRIPT = Path(mapa.__file__).resolve()


def crear_mundo_carpetas(home: Path) -> Tuple[Path, Path]:
    """Crea el mundo de carpetas para las pruebas según el enunciado."""
    claude_dir = home / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)
    (claude_dir / "settings.json").write_text(json.dumps({"enabledPlugins": {}}), encoding="utf-8")
    (claude_dir / "plugins").mkdir(parents=True, exist_ok=True)
    (claude_dir / "plugins" / "installed_plugins.json").write_text(json.dumps({"plugins": {}}), encoding="utf-8")
    (claude_dir / "plugins" / "known_marketplaces.json").write_text(json.dumps({}), encoding="utf-8")

    proyectos = home / "Proyectos"
    proyectos.mkdir(parents=True, exist_ok=True)

    # Empresa/ (CLAUDE.md) con Area/ (CLAUDE.md) con ProyA/ (.git) y ProyB/ (CLAUDE.md)
    empresa = proyectos / "Empresa"
    empresa.mkdir(parents=True, exist_ok=True)
    (empresa / "CLAUDE.md").write_text("# Empresa\nReglas empresa.", encoding="utf-8")

    area = empresa / "Area"
    area.mkdir(parents=True, exist_ok=True)
    (area / "CLAUDE.md").write_text("# Area\nReglas area.", encoding="utf-8")

    proy_a = area / "ProyA"
    proy_a.mkdir(parents=True, exist_ok=True)
    (proy_a / ".git").mkdir(parents=True, exist_ok=True)
    (proy_a / ".claude").mkdir(parents=True, exist_ok=True)
    (proy_a / ".claude" / "settings.json").write_text("{}", encoding="utf-8")

    # profunda Empresa/Area/ProyA/sub/ con .git (nivel 4 -> NO aparece)
    sub = proy_a / "sub"
    sub.mkdir(parents=True, exist_ok=True)
    (sub / ".git").mkdir(parents=True, exist_ok=True)

    proy_b = area / "ProyB"
    proy_b.mkdir(parents=True, exist_ok=True)
    (proy_b / "CLAUDE.md").write_text("# ProyB\nReglas proyecto B.", encoding="utf-8")

    # Empresa/src/ (sin .git ni CLAUDE.md -> no es caja)
    (empresa / "src").mkdir(parents=True, exist_ok=True)

    # Suelta/ (carpeta común de la raíz, sin nada -> sí es caja, nivel proyecto)
    (proyectos / "Suelta").mkdir(parents=True, exist_ok=True)

    # Personal/ con Salud/ (CLAUDE.md) -> dormido
    personal = proyectos / "Personal"
    personal.mkdir(parents=True, exist_ok=True)
    salud = personal / "Salud"
    salud.mkdir(parents=True, exist_ok=True)
    (salud / "CLAUDE.md").write_text("# Salud\nReglas salud.", encoding="utf-8")

    # _archivo/Viejo/ -> archivo
    archivo = proyectos / "_archivo"
    archivo.mkdir(parents=True, exist_ok=True)
    (archivo / "Viejo").mkdir(parents=True, exist_ok=True)

    # .wt-copia/ con .claude/ adentro (oculta -> NO aparece en carpetas ni en proyectos)
    wt = proyectos / ".wt-copia"
    wt.mkdir(parents=True, exist_ok=True)
    (wt / ".claude").mkdir(parents=True, exist_ok=True)
    (wt / ".claude" / "settings.json").write_text("{}", encoding="utf-8")

    # _otra/ (NO aparece)
    (proyectos / "_otra").mkdir(parents=True, exist_ok=True)

    # un enlace simbólico a una carpeta (NO aparece; tolerante si no deja crear enlaces)
    try:
        os.symlink(str(proyectos / "Suelta"), str(proyectos / "EnlaceSuelta"))
    except OSError:
        pass

    return claude_dir, proyectos


def ejecutar_mapa(args: List[str], home: Path, claude_dir: Path) -> subprocess.CompletedProcess:
    """Ejecuta mapa.py como subproceso usando el HOME y claude_dir de prueba."""
    cmd = [
        sys.executable,
        str(MAPA_SCRIPT),
        "--home", str(home),
        "--claude-dir", str(claude_dir),
        "--proyectos-dir", str(home / "Proyectos"),
    ] + args
    env = os.environ.copy()
    env["MAPA_HOME"] = str(home)
    env["CLAUDE_CONFIG_DIR"] = str(claude_dir)
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        timeout=15,
    )


class TestMapaCarpetas(unittest.TestCase):

    def test_01_campos_y_orden(self):
        """1. Los campos de cada una (ruta, nombre, grupo, area, nivel, tipo, flags) son los esperados; el orden es por ruta."""
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            claude_dir, proyectos = crear_mundo_carpetas(home)

            r = ejecutar_mapa(["carpetas", "--json"], home, claude_dir)
            self.assertEqual(r.returncode, 0, r.stderr)
            carpetas = json.loads(r.stdout)

            rutas = [c["ruta"] for c in carpetas]
            rutas_esperadas = [
                "_archivo/Viejo",
                "Empresa",
                "Empresa/Area",
                "Empresa/Area/ProyA",
                "Empresa/Area/ProyB",
                "Personal",
                "Personal/Salud",
                "Suelta",
            ]
            self.assertEqual(rutas, rutas_esperadas)

            # Comprobar que no aparecen carpetas excluidas
            self.assertNotIn("Empresa/src", rutas)
            self.assertNotIn(".wt-copia", rutas)
            self.assertNotIn("_otra", rutas)
            self.assertNotIn("EnlaceSuelta", rutas)
            self.assertNotIn("Empresa/Area/ProyA/sub", rutas)

            por_ruta = {c["ruta"]: c for c in carpetas}

            # 1. _archivo/Viejo
            v = por_ruta["_archivo/Viejo"]
            self.assertEqual(v["nombre"], "Viejo")
            self.assertEqual(v["grupo"], "Archivo")
            self.assertEqual(v["area"], "")
            self.assertEqual(v["nivel"], "proyecto")
            self.assertEqual(v["tipo"], "archivo")
            self.assertFalse(v["es_checkout_git"])
            self.assertFalse(v["tiene_claude_md"])
            self.assertFalse(v["tiene_claude"])
            self.assertEqual(v["ruta_tilde"], "~/Proyectos/_archivo/Viejo")

            # 2. Empresa
            e = por_ruta["Empresa"]
            self.assertEqual(e["nombre"], "Empresa")
            self.assertEqual(e["grupo"], "Empresa")
            self.assertEqual(e["area"], "")
            self.assertEqual(e["nivel"], "empresa")
            self.assertEqual(e["tipo"], "activo")
            self.assertFalse(e["es_checkout_git"])
            self.assertTrue(e["tiene_claude_md"])
            self.assertFalse(e["tiene_claude"])
            self.assertEqual(e["ruta_tilde"], "~/Proyectos/Empresa")

            # 3. Empresa/Area
            ea = por_ruta["Empresa/Area"]
            self.assertEqual(ea["nombre"], "Area")
            self.assertEqual(ea["grupo"], "Empresa")
            self.assertEqual(ea["area"], "")
            self.assertEqual(ea["nivel"], "area")
            self.assertEqual(ea["tipo"], "activo")
            self.assertFalse(ea["es_checkout_git"])
            self.assertTrue(ea["tiene_claude_md"])
            self.assertFalse(ea["tiene_claude"])
            self.assertEqual(ea["ruta_tilde"], "~/Proyectos/Empresa/Area")

            # 4. Empresa/Area/ProyA
            epa = por_ruta["Empresa/Area/ProyA"]
            self.assertEqual(epa["nombre"], "ProyA")
            self.assertEqual(epa["grupo"], "Empresa")
            self.assertEqual(epa["area"], "Area")
            self.assertEqual(epa["nivel"], "proyecto")
            self.assertEqual(epa["tipo"], "activo")
            self.assertTrue(epa["es_checkout_git"])
            self.assertFalse(epa["tiene_claude_md"])
            self.assertTrue(epa["tiene_claude"])
            self.assertEqual(epa["ruta_tilde"], "~/Proyectos/Empresa/Area/ProyA")

            # 5. Empresa/Area/ProyB
            epb = por_ruta["Empresa/Area/ProyB"]
            self.assertEqual(epb["nombre"], "ProyB")
            self.assertEqual(epb["grupo"], "Empresa")
            self.assertEqual(epb["area"], "Area")
            self.assertEqual(epb["nivel"], "proyecto")
            self.assertEqual(epb["tipo"], "activo")
            self.assertFalse(epb["es_checkout_git"])
            self.assertTrue(epb["tiene_claude_md"])
            self.assertFalse(epb["tiene_claude"])
            self.assertEqual(epb["ruta_tilde"], "~/Proyectos/Empresa/Area/ProyB")

            # 6. Personal
            p = por_ruta["Personal"]
            self.assertEqual(p["nombre"], "Personal")
            self.assertEqual(p["grupo"], "Personal")
            self.assertEqual(p["area"], "")
            self.assertEqual(p["nivel"], "empresa")
            self.assertEqual(p["tipo"], "activo")
            self.assertFalse(p["es_checkout_git"])
            self.assertFalse(p["tiene_claude_md"])
            self.assertFalse(p["tiene_claude"])
            self.assertEqual(p["ruta_tilde"], "~/Proyectos/Personal")

            # 7. Personal/Salud
            ps = por_ruta["Personal/Salud"]
            self.assertEqual(ps["nombre"], "Salud")
            self.assertEqual(ps["grupo"], "Personal")
            self.assertEqual(ps["area"], "")
            self.assertEqual(ps["nivel"], "proyecto")
            self.assertEqual(ps["tipo"], "dormido")
            self.assertFalse(ps["es_checkout_git"])
            self.assertTrue(ps["tiene_claude_md"])
            self.assertFalse(ps["tiene_claude"])
            self.assertEqual(ps["ruta_tilde"], "~/Proyectos/Personal/Salud")

            # 8. Suelta
            s = por_ruta["Suelta"]
            self.assertEqual(s["nombre"], "Suelta")
            self.assertEqual(s["grupo"], "Suelta")
            self.assertEqual(s["area"], "")
            self.assertEqual(s["nivel"], "proyecto")
            self.assertEqual(s["tipo"], "activo")
            self.assertFalse(s["es_checkout_git"])
            self.assertFalse(s["tiene_claude_md"])
            self.assertFalse(s["tiene_claude"])
            self.assertEqual(s["ruta_tilde"], "~/Proyectos/Suelta")

    def test_02_filtros_tipo_y_grupo(self):
        """2. mapa carpetas --tipo dormido solo trae Personal/Salud; --tipo archivo solo Viejo; --grupo filtra."""
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            claude_dir, _ = crear_mundo_carpetas(home)

            # --tipo dormido
            r_dormido = ejecutar_mapa(["carpetas", "--tipo", "dormido"], home, claude_dir)
            self.assertEqual(r_dormido.returncode, 0)
            lineas_d = [l.strip() for l in r_dormido.stdout.strip().splitlines() if l.strip()]
            self.assertEqual(len(lineas_d), 1)
            self.assertIn("Personal/Salud", lineas_d[0])
            self.assertTrue(lineas_d[0].startswith("dormido · Personal · Salud"))

            # --tipo archivo
            r_archivo = ejecutar_mapa(["carpetas", "--tipo", "archivo"], home, claude_dir)
            self.assertEqual(r_archivo.returncode, 0)
            lineas_a = [l.strip() for l in r_archivo.stdout.strip().splitlines() if l.strip()]
            self.assertEqual(len(lineas_a), 1)
            self.assertIn("_archivo/Viejo", lineas_a[0])
            self.assertTrue(lineas_a[0].startswith("archivo · Archivo · Viejo"))

            # --grupo filtra
            r_grupo = ejecutar_mapa(["carpetas", "--grupo", "Personal"], home, claude_dir)
            self.assertEqual(r_grupo.returncode, 0)
            lineas_g = [l.strip() for l in r_grupo.stdout.strip().splitlines() if l.strip()]
            self.assertEqual(len(lineas_g), 2)
            self.assertTrue(any("Personal/Salud" in l for l in lineas_g))
            self.assertTrue(any(l.endswith("~/Proyectos/Personal") for l in lineas_g))

            r_empresa = ejecutar_mapa(["carpetas", "--grupo", "Empresa"], home, claude_dir)
            self.assertEqual(r_empresa.returncode, 0)
            lineas_e = [l.strip() for l in r_empresa.stdout.strip().splitlines() if l.strip()]
            self.assertEqual(len(lineas_e), 4)
            self.assertFalse(any("Personal" in l for l in lineas_e))

    def test_03_borrar_y_crear_caja(self):
        """3. Borrar una carpeta -> desaparece en la consulta siguiente; crear una caja nueva -> aparece, sin hacer nada más."""
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            claude_dir, proyectos = crear_mundo_carpetas(home)

            r1 = ejecutar_mapa(["carpetas"], home, claude_dir)
            self.assertEqual(r1.returncode, 0)
            self.assertIn("Suelta", r1.stdout)

            # Borrar Suelta
            shutil.rmtree(proyectos / "Suelta")
            r2 = ejecutar_mapa(["carpetas"], home, claude_dir)
            self.assertEqual(r2.returncode, 0)
            self.assertNotIn("Suelta", r2.stdout)

            # Crear una caja nueva visible en la raíz
            nueva = proyectos / "Nueva"
            nueva.mkdir()
            (nueva / "CLAUDE.md").write_text("# Nueva", encoding="utf-8")
            r3 = ejecutar_mapa(["carpetas"], home, claude_dir)
            self.assertEqual(r3.returncode, 0)
            self.assertIn("Nueva", r3.stdout)

    def test_04_ocultas_no_suben_reconstrucciones_visible_si(self):
        """4. Crear y borrar .wt-otra (oculta) NO sube reconstrucciones de vigilancia.json; crear una carpeta visible nueva en la raíz SÍ lo sube exactamente 1."""
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            claude_dir, proyectos = crear_mundo_carpetas(home)

            r_ini = ejecutar_mapa(["carpetas"], home, claude_dir)
            self.assertEqual(r_ini.returncode, 0)
            vig_path = claude_dir / "mapa" / "vigilancia.json"
            vig1 = json.loads(vig_path.read_text(encoding="utf-8"))
            n_recon1 = vig1.get("reconstrucciones", 0)

            # Crear .wt-otra (oculta)
            wt_otra = proyectos / ".wt-otra"
            wt_otra.mkdir()
            r_oculta = ejecutar_mapa(["carpetas"], home, claude_dir)
            self.assertEqual(r_oculta.returncode, 0)
            vig2 = json.loads(vig_path.read_text(encoding="utf-8"))
            self.assertEqual(vig2.get("reconstrucciones", 0), n_recon1)

            # Borrar .wt-otra
            wt_otra.rmdir()
            r_borrar_oculta = ejecutar_mapa(["carpetas"], home, claude_dir)
            self.assertEqual(r_borrar_oculta.returncode, 0)
            vig3 = json.loads(vig_path.read_text(encoding="utf-8"))
            self.assertEqual(vig3.get("reconstrucciones", 0), n_recon1)

            # Crear carpeta visible nueva en la raíz
            visible = proyectos / "VisibleNueva"
            visible.mkdir()
            r_visible = ejecutar_mapa(["carpetas"], home, claude_dir)
            self.assertEqual(r_visible.returncode, 0)
            vig4 = json.loads(vig_path.read_text(encoding="utf-8"))
            self.assertEqual(vig4.get("reconstrucciones", 0), n_recon1 + 1)

    def test_05_proyectos_no_contiene_wt(self):
        """5. proyectos (arneses) NO contiene el .claude de .wt-copia."""
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            claude_dir, _ = crear_mundo_carpetas(home)

            ejecutar_mapa(["carpetas"], home, claude_dir)
            mapa_json = json.loads((claude_dir / "mapa" / "mapa.json").read_text(encoding="utf-8"))
            proyectos = mapa_json.get("proyectos", [])
            rutas_proy = [p.get("ruta", "") for p in proyectos]
            self.assertIn("Empresa/Area/ProyA", rutas_proy)
            for r in rutas_proy:
                self.assertNotIn(".wt-copia", r)

    def test_06_json_valido_y_coincide_con_texto(self):
        """6. --json es JSON válido y trae las mismas carpetas que la salida de texto."""
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            claude_dir, _ = crear_mundo_carpetas(home)

            r_json = ejecutar_mapa(["carpetas", "--json"], home, claude_dir)
            self.assertEqual(r_json.returncode, 0)
            datos_json = json.loads(r_json.stdout)
            self.assertIsInstance(datos_json, list)

            r_txt = ejecutar_mapa(["carpetas"], home, claude_dir)
            self.assertEqual(r_txt.returncode, 0)
            lineas_txt = [l.strip() for l in r_txt.stdout.strip().splitlines() if l.strip()]

            rutas_json = [c["ruta"] for c in datos_json]
            rutas_tilde_txt = [l.split(" · ")[-1].replace("~/Proyectos/", "") for l in lineas_txt]

            self.assertEqual(rutas_json, rutas_tilde_txt)

    def test_07_sin_proyectos_mensaje_y_salida_0(self):
        """7. Sin Proyectos (como un cliente): mapa carpetas imprime «ninguna carpeta coincide» y sale 0."""
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            claude_dir = home / ".claude"
            claude_dir.mkdir(parents=True)

            r = ejecutar_mapa(["carpetas"], home, claude_dir)
            self.assertEqual(r.returncode, 0)
            self.assertIn("ninguna carpeta coincide", r.stdout)

    def test_08_obtener_nombres_relevantes_directo(self):
        """8. mapa_io: prueba directa de obtener_nombres_relevantes: en modo proyectos, nivel 1, ignora '.wt-x/' y '_x/' pero no '_archivo/' ni '.claude/'."""
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            p_n1 = home / "Proyectos" / "N1"
            p_n1.mkdir(parents=True)
            (p_n1 / ".wt-x").mkdir()
            (p_n1 / "_x").mkdir()
            (p_n1 / "_archivo").mkdir()
            (p_n1 / ".claude").mkdir()
            (p_n1 / ".mcp.json").write_text("{}", encoding="utf-8")

            nombres = obtener_nombres_relevantes(p_n1, home)
            self.assertNotIn(".wt-x/", nombres)
            self.assertNotIn("_x/", nombres)
            self.assertIn("_archivo/", nombres)
            self.assertIn(".claude/", nombres)
            self.assertIn(".mcp.json", nombres)

    def test_09_api_listar_carpetas(self):
        """9. Función pública listar_carpetas devuelve las carpetas esperadas."""
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            claude_dir, proyectos = crear_mundo_carpetas(home)

            carpetas = mapa.listar_carpetas(claude_dir, home, proyectos)
            self.assertIsInstance(carpetas, list)
            rutas = [c["ruta"] for c in carpetas]
            self.assertIn("Empresa", rutas)
            self.assertIn("Empresa/Area/ProyA", rutas)
            self.assertIn("Personal/Salud", rutas)
            self.assertIn("_archivo/Viejo", rutas)
            self.assertNotIn(".wt-copia", rutas)

    def test_10_mapa_md_conteo_carpetas(self):
        """10. MAPA.md incluye la línea de conteo de carpetas de proyecto y mide <= 4096 bytes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            claude_dir, _ = crear_mundo_carpetas(home)

            ejecutar_mapa(["carpetas"], home, claude_dir)
            mapa_md_path = claude_dir / "mapa" / "MAPA.md"
            self.assertTrue(mapa_md_path.is_file())
            contenido = mapa_md_path.read_text(encoding="utf-8")
            self.assertLessEqual(len(contenido.encode("utf-8")), 4096)
            self.assertRegex(contenido, r"- Carpetas de proyecto: \d+ \(activas \d+, dormidas \d+, archivo \d+\)")


if __name__ == "__main__":
    unittest.main()
