#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_mapa.py - Pruebas unitarias para el comando mapa.py.
Disparador: encadenado — lo corre el suite de pruebas del plugin metodo.

Verifica:
  1. Skill nueva -> detectada en buscar; modificación y borrado.
  2. Plugin instalado desde la app -> detectado en buscar.
  3. Consultas sucesivas sin cambios -> reconstrucciones no sube; sube 1 con cambio.
  4. Concurrencia: dos mapa a la vez -> reconstrucciones sube 1 sola vez y JSON válidos.
  5. Entorno sin Proyectos ni .cerebro (modo cliente) -> sin errores.
  6. Fuga de credenciales -> claves falsas nunca aparecen en mapa/ ni en salida.
  6b. Conservación de uso al reconstruir disco -> mapa-uso.json se preserva.
  6c. Enlaces rotos -> tolerante a symlinks inexistentes y detecta cambios.
  7. Escritura atómica -> ante excepción los archivos viejos quedan intactos y candado libre.
  8. tapar_claves -> casos positivos para cada patrón y negativos.
  9. mapa --al-dia -> código 0 tras armar y código 1 tras modificar archivo.
  10. mapa sin-registrar -> cruce bidireccional con CATALOGO.yaml.

Python 3.9 estándar, sin librerías externas.
"""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import unittest

# Asegurar importación de mapa_lector, mapa_io, mapa_uso y mapa
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mapa_io import IO, Registro, escribir_json, firma
import mapa
import mapa_lector
import mapa_uso


MAPA_SCRIPT = Path(mapa.__file__).resolve()


def crear_mundo_minimo(home: Path) -> Tuple[Path, Path]:
    """Crea una estructura mínima de entorno en un HOME falso para pruebas."""
    claude_dir = home / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)

    # skills/uno/SKILL.md
    skill_uno = claude_dir / "skills" / "uno"
    skill_uno.mkdir(parents=True, exist_ok=True)
    (skill_uno / "SKILL.md").write_text(
        "---\nname: uno\ndescription: Primera skill para pruebas del mapa\n---\n# Uno\nContenido de skill uno.",
        encoding="utf-8",
    )

    # agents/a1.md
    agents_dir = claude_dir / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    (agents_dir / "a1.md").write_text(
        "---\nname: a1\ndescription: Agente de prueba a1\n---\n# Agente a1",
        encoding="utf-8",
    )

    # settings.json
    (claude_dir / "settings.json").write_text(
        json.dumps({
            "permissions": {"allow": ["Read", "Write"], "deny": [], "ask": []},
            "enabledPlugins": {},
        }),
        encoding="utf-8",
    )

    # rules/r1.md
    rules_dir = claude_dir / "rules"
    rules_dir.mkdir(parents=True, exist_ok=True)
    (rules_dir / "r1.md").write_text("# Regla 1\nRegla de prueba global.", encoding="utf-8")

    # plugins/installed_plugins.json
    plugins_dir = claude_dir / "plugins"
    plugins_dir.mkdir(parents=True, exist_ok=True)
    (plugins_dir / "installed_plugins.json").write_text(
        json.dumps({"plugins": {}}),
        encoding="utf-8",
    )
    (plugins_dir / "known_marketplaces.json").write_text(
        json.dumps({}),
        encoding="utf-8",
    )

    # Proyecto <home>/Proyectos/P/.claude/skills/pv/SKILL.md
    proy_skill = home / "Proyectos" / "P" / ".claude" / "skills" / "pv"
    proy_skill.mkdir(parents=True, exist_ok=True)
    (proy_skill / "SKILL.md").write_text(
        "---\nname: pv\ndescription: Skill de proyecto P\n---\n# PV",
        encoding="utf-8",
    )

    # <home>/.mcp.json
    (home / ".mcp.json").write_text(
        json.dumps({"mcpServers": {"srv_local": {"command": "echo"}}}),
        encoding="utf-8",
    )

    # <home>/.claude.json
    (home / ".claude.json").write_text(
        json.dumps({
            "mcpServers": {"srv_usuario": {"command": "echo"}},
            "skillUsage": {},
        }),
        encoding="utf-8",
    )

    # <home>/Library/Application Support/Claude/claude_desktop_config.json
    desktop_cfg = home / "Library" / "Application Support" / "Claude"
    desktop_cfg.mkdir(parents=True, exist_ok=True)
    (desktop_cfg / "claude_desktop_config.json").write_text(
        json.dumps({"mcpServers": {"srv_desktop": {"command": "echo"}}}),
        encoding="utf-8",
    )

    return claude_dir, home / "Proyectos"


def ejecutar_mapa(args: list, home: Path, claude_dir: Path) -> subprocess.CompletedProcess:
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
        env=env,
        timeout=15,
    )


class TestMapa(unittest.TestCase):

    def test_01_skill_ciclo_de_vida(self):
        """1. Skill nueva -> detectada en buscar; modificación y borrado."""
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            claude_dir, _ = crear_mundo_minimo(home)

            # Búsqueda inicial: no existe
            r0 = ejecutar_mapa(["buscar", "automatizar"], home, claude_dir)
            self.assertEqual(r0.returncode, 0)
            self.assertIn('nada coincide con "automatizar"', r0.stdout)

            # Crear skill nueva
            skill_nueva = claude_dir / "skills" / "nueva"
            skill_nueva.mkdir(parents=True)
            (skill_nueva / "SKILL.md").write_text(
                "---\nname: nueva\ndescription: Skill creada para automatizar tareas\n---\n# Nueva",
                encoding="utf-8",
            )

            # Buscarla -> debe aparecer
            r1 = ejecutar_mapa(["buscar", "automatizar"], home, claude_dir)
            self.assertEqual(r1.returncode, 0)
            self.assertIn("nueva", r1.stdout)
            self.assertIn("automatizar tareas", r1.stdout)

            # Modificar su descripción
            (skill_nueva / "SKILL.md").write_text(
                "---\nname: nueva\ndescription: Descripcion modificada completamente\n---\n# Nueva mod",
                encoding="utf-8",
            )
            r2 = ejecutar_mapa(["buscar", "modificada"], home, claude_dir)
            self.assertEqual(r2.returncode, 0)
            self.assertIn("nueva", r2.stdout)
            self.assertIn("modificada completamente", r2.stdout)

            # Borrarla -> debe desaparecer
            shutil.rmtree(skill_nueva)
            r3 = ejecutar_mapa(["buscar", "modificada"], home, claude_dir)
            self.assertEqual(r3.returncode, 0)
            self.assertIn('nada coincide con "modificada"', r3.stdout)

    def test_02_plugin_instalado_desde_app(self):
        """2. Plugin instalado desde la app en cache -> aparece en buscar."""
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            claude_dir, _ = crear_mundo_minimo(home)

            cache_plugin = claude_dir / "plugins" / "cache" / "mkt1" / "plugin-calc" / "1.0.0"
            cache_plugin.mkdir(parents=True)
            (cache_plugin / ".claude-plugin").mkdir(parents=True)
            (cache_plugin / ".claude-plugin" / "plugin.json").write_text(
                json.dumps({"name": "plugin-calc", "version": "1.0.0", "description": "Calculadora"}),
                encoding="utf-8",
            )

            skill_pl = cache_plugin / "skills" / "sumar"
            skill_pl.mkdir(parents=True)
            (skill_pl / "SKILL.md").write_text(
                "---\nname: sumar\ndescription: Herramienta de suma aritmetica\n---\n# Sumar",
                encoding="utf-8",
            )

            # Registrar en installed_plugins.json
            (claude_dir / "plugins" / "installed_plugins.json").write_text(
                json.dumps({
                    "plugins": {
                        "plugin-calc@mkt1": [{"installPath": str(cache_plugin), "version": "1.0.0"}]
                    }
                }),
                encoding="utf-8",
            )
            # Habilitar en settings.json
            (claude_dir / "settings.json").write_text(
                json.dumps({"enabledPlugins": {"plugin-calc@mkt1": True}}),
                encoding="utf-8",
            )

            r = ejecutar_mapa(["buscar", "aritmetica"], home, claude_dir)
            self.assertEqual(r.returncode, 0)
            self.assertIn("sumar", r.stdout)
            self.assertIn("plugin-calc", r.stdout)

    def test_03_contador_reconstrucciones(self):
        """3. Sin cambios -> reconstrucciones no sube; con cambio -> sube exactamente 1."""
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            claude_dir, _ = crear_mundo_minimo(home)

            # Primer run: construye
            r1 = ejecutar_mapa(["resumen"], home, claude_dir)
            self.assertEqual(r1.returncode, 0)
            vig1 = json.loads((claude_dir / "mapa" / "vigilancia.json").read_text(encoding="utf-8"))
            n1 = vig1.get("reconstrucciones", 0)
            self.assertEqual(n1, 1)

            # Segundo run sin cambios: no debe subir
            r2 = ejecutar_mapa(["resumen"], home, claude_dir)
            self.assertEqual(r2.returncode, 0)
            vig2 = json.loads((claude_dir / "mapa" / "vigilancia.json").read_text(encoding="utf-8"))
            n2 = vig2.get("reconstrucciones", 0)
            self.assertEqual(n2, 1)

            # Tocar archivo existente
            skill_uno = claude_dir / "skills" / "uno" / "SKILL.md"
            skill_uno.write_text(skill_uno.read_text(encoding="utf-8") + "\n# Modificacion extra", encoding="utf-8")

            # Tercer run: sube exactamente 1
            r3 = ejecutar_mapa(["resumen"], home, claude_dir)
            self.assertEqual(r3.returncode, 0)
            vig3 = json.loads((claude_dir / "mapa" / "vigilancia.json").read_text(encoding="utf-8"))
            n3 = vig3.get("reconstrucciones", 0)
            self.assertEqual(n3, 2)

    def test_04_concurrencia_candado(self):
        """4. Dos mapa a la vez -> reconstrucciones sube 1 sola vez y JSON válidos."""
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            claude_dir, _ = crear_mundo_minimo(home)

            # Run inicial
            ejecutar_mapa(["resumen"], home, claude_dir)

            # Tocar archivo para provocar reconstrucción
            skill_uno = claude_dir / "skills" / "uno" / "SKILL.md"
            skill_uno.write_text(skill_uno.read_text(encoding="utf-8") + "\n# Cambio concurrente", encoding="utf-8")

            cmd = [
                sys.executable, str(MAPA_SCRIPT),
                "--home", str(home),
                "--claude-dir", str(claude_dir),
                "--proyectos-dir", str(home / "Proyectos"),
                "resumen",
            ]
            env = os.environ.copy()
            env["MAPA_HOME"] = str(home)
            env["CLAUDE_CONFIG_DIR"] = str(claude_dir)

            p1 = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)
            p2 = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env)

            out1, err1 = p1.communicate(timeout=15)
            out2, err2 = p2.communicate(timeout=15)

            self.assertEqual(p1.returncode, 0, f"Error p1: {err1}")
            self.assertEqual(p2.returncode, 0, f"Error p2: {err2}")

            # Comprobar que subió a exactamente 2
            vig = json.loads((claude_dir / "mapa" / "vigilancia.json").read_text(encoding="utf-8"))
            self.assertEqual(vig.get("reconstrucciones"), 2)

            # Validar que todos los archivos JSON sean legibles y válidos
            json.loads((claude_dir / "mapa" / "mapa.json").read_text(encoding="utf-8"))
            json.loads((claude_dir / "mapa" / "mapa-disco.json").read_text(encoding="utf-8"))

    def test_05_carpeta_sin_proyectos_ni_cerebro(self):
        """5. Carpeta sin Proyectos ni .cerebro -> finaliza sin traza de error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            claude_dir = home / ".claude"
            claude_dir.mkdir(parents=True)
            skill = claude_dir / "skills" / "s1"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text("---\nname: s1\ndescription: Test\n---\n", encoding="utf-8")

            # mapa / mapa resumen
            r1 = ejecutar_mapa([], home, claude_dir)
            self.assertEqual(r1.returncode, 0, r1.stderr)
            self.assertNotIn("Traceback", r1.stderr)

            # mapa buscar x
            r2 = ejecutar_mapa(["buscar", "x"], home, claude_dir)
            self.assertEqual(r2.returncode, 0, r2.stderr)
            self.assertNotIn("Traceback", r2.stderr)

            # mapa sin-registrar
            r3 = ejecutar_mapa(["sin-registrar"], home, claude_dir)
            self.assertEqual(r3.returncode, 0, r3.stderr)
            self.assertIn("sin catálogo que cruzar", r3.stdout)
            self.assertNotIn("Traceback", r3.stderr)

            # mapa --al-dia
            r4 = ejecutar_mapa(["--al-dia"], home, claude_dir)
            self.assertEqual(r4.returncode, 0, r4.stderr)
            self.assertIn("✓ mapa al día", r4.stdout)
            self.assertNotIn("Traceback", r4.stderr)

    def test_06_fuga_de_claves_falsas(self):
        """6. Claves falsas plantadas -> NO aparecen en mapa/ ni en salida de comandos."""
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            claude_dir, _ = crear_mundo_minimo(home)

            clave_falsa = "CLAVE-FALSA-123"

            # Inyectar clave falsa en env de .mcp.json
            (home / ".mcp.json").write_text(
                json.dumps({"mcpServers": {"srv1": {"env": {"SECRETO": clave_falsa}}}}),
                encoding="utf-8",
            )
            # Inyectar en env de .claude.json
            (home / ".claude.json").write_text(
                json.dumps({"mcpServers": {"srv2": {"env": {"TOKEN": clave_falsa}}}}),
                encoding="utf-8",
            )
            # Inyectar en config de escritorio
            desktop_file = home / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
            desktop_file.write_text(
                json.dumps({"mcpServers": {"srv3": {"env": {"KEY": clave_falsa}}}}),
                encoding="utf-8",
            )

            # Ejecutar comandos de consulta
            r_res = ejecutar_mapa(["resumen"], home, claude_dir)
            self.assertNotIn(clave_falsa, r_res.stdout)
            self.assertNotIn(clave_falsa, r_res.stderr)

            r_bus = ejecutar_mapa(["buscar", "srv1"], home, claude_dir)
            self.assertNotIn(clave_falsa, r_bus.stdout)
            self.assertNotIn(clave_falsa, r_bus.stderr)

            r_ver = ejecutar_mapa(["ver", "srv1"], home, claude_dir)
            self.assertNotIn(clave_falsa, r_ver.stdout)
            self.assertNotIn(clave_falsa, r_ver.stderr)

            r_json = ejecutar_mapa(["--json"], home, claude_dir)
            self.assertNotIn(clave_falsa, r_json.stdout)

            # Verificar el contenido de los archivos guardados en mapa/
            mapa_dir = claude_dir / "mapa"
            for arch in mapa_dir.iterdir():
                if arch.is_file():
                    contenido = arch.read_text(encoding="utf-8", errors="replace")
                    self.assertNotIn(clave_falsa, contenido, f"Fuga de clave en archivo {arch.name}")

    def test_06b_conservacion_de_uso_al_editar_skill(self):
        """6b. Editar una skill -> el mapa se rehace y el uso guardado sigue igual."""
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            claude_dir, _ = crear_mundo_minimo(home)

            # Agregar skill dos
            skill_dos = claude_dir / "skills" / "dos"
            skill_dos.mkdir(parents=True)
            (skill_dos / "SKILL.md").write_text(
                "---\nname: dos\ndescription: Segunda skill\n---\n# Dos",
                encoding="utf-8",
            )

            # Primer armado
            ejecutar_mapa(["resumen"], home, claude_dir)

            # Crear mapa-uso.json con datos mínimos para skill uno
            ahora = datetime.now(timezone.utc)
            stats = {c: {} for c in mapa_uso.CATEGORIAS_USO}
            stats["skills"]["uno"] = {
                "p": {"t": 10, "d30": 5, "d90": 10, "primera": ahora, "ultima": ahora, "ses": {"s1"}},
                "s": {"t": 0, "d30": 0, "d90": 0, "primera": ahora, "ultima": ahora, "ses": set()},
            }
            uso_data = mapa_uso.a_json(stats, {"archivos_jsonl_leidos": 1}, {})
            uso_data["medido_en"] = ahora.isoformat()
            (claude_dir / "mapa" / "mapa-uso.json").write_text(
                json.dumps(uso_data),
                encoding="utf-8",
            )

            # Editar skill dos
            (skill_dos / "SKILL.md").write_text(
                "---\nname: dos\ndescription: Segunda skill modificada\n---\n# Dos mod",
                encoding="utf-8",
            )

            # Ejecutar consulta para disparar la reconstrucción
            r = ejecutar_mapa(["resumen"], home, claude_dir)
            self.assertEqual(r.returncode, 0)

            # Verificar en mapa.json que skill uno mantiene sus usos y dos queda nunca_usado
            mapa_json = json.loads((claude_dir / "mapa" / "mapa.json").read_text(encoding="utf-8"))
            por_nom = {s["nombre"]: s for s in mapa_json.get("skills_personales", [])}

            self.assertIn("uno", por_nom)
            self.assertEqual(por_nom["uno"]["usos_total"], 10)
            self.assertFalse(por_nom["uno"]["nunca_usado"])

            self.assertIn("dos", por_nom)
            self.assertEqual(por_nom["dos"]["usos_total"], 0)
            self.assertTrue(por_nom["dos"]["nunca_usado"])

    def test_06c_enlaces_rotos_en_skills(self):
        """6c. Enlace roto en skills/ no rompe mapa; crear y borrar enlace es detectado."""
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            claude_dir, _ = crear_mundo_minimo(home)

            ejecutar_mapa(["resumen"], home, claude_dir)
            r_aldia1 = ejecutar_mapa(["--al-dia"], home, claude_dir)
            self.assertEqual(r_aldia1.returncode, 0)

            # Crear enlace roto
            enlace_roto = claude_dir / "skills" / "enlace_huerfano"
            try:
                os.symlink(str(home / "destino_inexistente"), str(enlace_roto))
            except OSError:
                return  # Si el filesystem no permite symlinks, omitir

            # mapa --al-dia debe dar 1 (detectó el cambio)
            r_aldia2 = ejecutar_mapa(["--al-dia"], home, claude_dir)
            self.assertEqual(r_aldia2.returncode, 1)
            self.assertIn("✗ mapa viejo:", r_aldia2.stdout)

            # mapa no se cae al ejecutarse con el enlace roto
            r_rec = ejecutar_mapa(["resumen"], home, claude_dir)
            self.assertEqual(r_rec.returncode, 0)

            # mapa --al-dia vuelve a estar al día
            r_aldia3 = ejecutar_mapa(["--al-dia"], home, claude_dir)
            self.assertEqual(r_aldia3.returncode, 0)

            # Borrar el enlace roto -> detectado
            os.unlink(str(enlace_roto))
            r_aldia4 = ejecutar_mapa(["--al-dia"], home, claude_dir)
            self.assertEqual(r_aldia4.returncode, 1)

    def test_07_escritura_atomica_y_candado_libre(self):
        """7. Simulación de excepción en reconstrucción -> archivos previos intactos y candado libre."""
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            claude_dir, proyectos_dir = crear_mundo_minimo(home)

            # Armar inicialmente
            ejecutar_mapa(["resumen"], home, claude_dir)

            vig_orig = (claude_dir / "mapa" / "vigilancia.json").read_text(encoding="utf-8")
            mapa_orig = (claude_dir / "mapa" / "mapa.json").read_text(encoding="utf-8")

            # Tocar archivo para provocar reconstrucción
            (claude_dir / "skills" / "uno" / "SKILL.md").write_text("# Modificacion", encoding="utf-8")

            # Mock de leer_disco para provocar excepción
            orig_leer_disco = mapa_lector.leer_disco

            def fallo_leer_disco(io, proy):
                raise RuntimeError("Fallo forzado para prueba de atomicidad")

            mapa_lector.leer_disco = fallo_leer_disco
            mapa.mapa_lector.leer_disco = fallo_leer_disco

            try:
                with self.assertRaises(SystemExit) as cm:
                    mapa.asegurar_al_dia(claude_dir, home, proyectos_dir)
                self.assertEqual(cm.exception.code, 1)
            finally:
                mapa_lector.leer_disco = orig_leer_disco
                mapa.mapa_lector.leer_disco = orig_leer_disco

            # Archivos anteriores deben conservarse intactos
            self.assertEqual((claude_dir / "mapa" / "vigilancia.json").read_text(encoding="utf-8"), vig_orig)
            self.assertEqual((claude_dir / "mapa" / "mapa.json").read_text(encoding="utf-8"), mapa_orig)

            # El candado debe quedar completamente libre (se adquiere sin bloqueo)
            candado = mapa.CandadoMapa(claude_dir / "mapa")
            self.assertTrue(candado.adquirir())
            candado.liberar()

    def test_08_tapar_claves(self):
        """8. tapar_claves: casos positivos para cada patrón y negativos."""
        # Armar cadenas por partes para cumplir la regla estricta contra claves literales
        clave_pem = "-----BEGIN " + "RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA..."
        clave_akia = "AK" + "IA" + "1234567890ABCDEF"
        clave_gh = "gh" + "p_" + "a" * 36
        clave_sk = "s" + "k-" + "a" * 24
        clave_slack = "x" + "oxb-1234567890-abcdef"
        clave_aiza = "AI" + "za" + "Sy" + "A" * 33
        clave_pass = "pass" + "word=" + "miclavesecreta123"
        clave_passwd = "pass" + "wd: " + "miclavesecreta123"
        clave_secret = "sec" + "ret = " + "miclavesecreta123"
        clave_token = "tok" + "en: " + "miclavesecreta123"
        clave_api = "api" + "_key=" + "miclavesecreta123"

        # Casos positivos
        self.assertEqual(mapa_lector.tapar_claves(clave_pem), "[tapado]")
        self.assertEqual(mapa_lector.tapar_claves(clave_akia), "[tapado]")
        self.assertEqual(mapa_lector.tapar_claves(clave_gh), "[tapado]")
        self.assertEqual(mapa_lector.tapar_claves(clave_sk), "[tapado]")
        self.assertEqual(mapa_lector.tapar_claves(clave_slack), "[tapado]")
        self.assertEqual(mapa_lector.tapar_claves(clave_aiza), "[tapado]")
        self.assertEqual(mapa_lector.tapar_claves(clave_pass), "[tapado]")
        self.assertEqual(mapa_lector.tapar_claves(clave_passwd), "[tapado]")
        self.assertEqual(mapa_lector.tapar_claves(clave_secret), "[tapado]")
        self.assertEqual(mapa_lector.tapar_claves(clave_token), "[tapado]")
        self.assertEqual(mapa_lector.tapar_claves(clave_api), "[tapado]")

        # Estructura anidada
        datos_anidados = {
            "nombre": "skill1",
            "detalles": [clave_sk, "texto limpio"],
            "meta": {"clave": clave_akia}
        }
        tapado = mapa_lector.tapar_claves(datos_anidados)
        self.assertEqual(tapado["nombre"], "skill1")
        self.assertEqual(tapado["detalles"][0], "[tapado]")
        self.assertEqual(tapado["detalles"][1], "texto limpio")
        self.assertEqual(tapado["meta"]["clave"], "[tapado]")

        # Caso negativo
        texto_limpio = "Este es un texto regular sin secretos ni claves privadas."
        self.assertEqual(mapa_lector.tapar_claves(texto_limpio), texto_limpio)

    def test_09_mapa_al_dia(self):
        """9. mapa --al-dia: ✓ tras armar, ✗ tras tocar un SKILL.md."""
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            claude_dir, _ = crear_mundo_minimo(home)

            # Sin armar -> código 1
            r0 = ejecutar_mapa(["--al-dia"], home, claude_dir)
            self.assertEqual(r0.returncode, 1)
            self.assertIn("✗ mapa sin armar", r0.stdout)

            # Armar
            ejecutar_mapa(["resumen"], home, claude_dir)

            # Al día -> código 0
            r1 = ejecutar_mapa(["--al-dia"], home, claude_dir)
            self.assertEqual(r1.returncode, 0)
            self.assertIn("✓ mapa al día", r1.stdout)

            # Tocar SKILL.md
            (claude_dir / "skills" / "uno" / "SKILL.md").write_text("# Cambio", encoding="utf-8")

            # Viejo -> código 1
            r2 = ejecutar_mapa(["--al-dia"], home, claude_dir)
            self.assertEqual(r2.returncode, 1)
            self.assertIn("✗ mapa viejo:", r2.stdout)

    def test_07b_vigilancia_se_escribe_al_final(self):
        """Si la reconstrucción muere después de leer el disco, la huella vieja queda: la próxima consulta rehace."""
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            claude_dir, proyectos_dir = crear_mundo_minimo(home)
            ejecutar_mapa(["resumen"], home, claude_dir)
            vig_orig = (claude_dir / "mapa" / "vigilancia.json").read_text(encoding="utf-8")
            (claude_dir / "skills" / "uno" / "SKILL.md").write_text("# Modificacion", encoding="utf-8")
            orig_cerrar = mapa_lector.cerrar

            def fallo_cerrar(*a, **k):
                raise RuntimeError("Fallo forzado en el cruce")

            mapa.mapa_lector.cerrar = fallo_cerrar
            try:
                with self.assertRaises(SystemExit):
                    mapa.asegurar_al_dia(claude_dir, home, proyectos_dir)
            finally:
                mapa.mapa_lector.cerrar = orig_cerrar
            self.assertEqual((claude_dir / "mapa" / "vigilancia.json").read_text(encoding="utf-8"), vig_orig)
            r = ejecutar_mapa(["--al-dia"], home, claude_dir)
            self.assertEqual(r.returncode, 1)  # sigue «viejo»: la próxima consulta rehace

    def test_07c_mapa_disco_sin_nombres_de_clientes_ni_claves(self):
        """mapa-disco.json también sale depurado (no solo mapa.json)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            claude_dir, proyectos_dir = crear_mundo_minimo(home)
            (claude_dir / "nombres-prohibidos.txt").write_text("ClienteSecreto\n", encoding="utf-8")
            clave = "s" + "k-" + "a" * 24
            (claude_dir / "skills" / "uno" / "SKILL.md").write_text(
                "---\nname: uno\ndescription: Conector de ClienteSecreto con " + clave + "\n---\n", encoding="utf-8")
            ejecutar_mapa(["resumen"], home, claude_dir)
            for nombre in ("mapa-disco.json", "mapa.json", "vigilancia.json", "MAPA.md"):
                texto = (claude_dir / "mapa" / nombre).read_text(encoding="utf-8")
                self.assertNotIn("ClienteSecreto", texto, nombre)
                self.assertNotIn(clave, texto, nombre)

    def test_10_sin_registrar_catalogo(self):
        """10. mapa sin-registrar: cruce bidireccional con CATALOGO.yaml."""
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            claude_dir, _ = crear_mundo_minimo(home)

            # Agregar skill dos en disco
            skill_dos = claude_dir / "skills" / "dos"
            skill_dos.mkdir(parents=True)
            (skill_dos / "SKILL.md").write_text(
                "---\nname: dos\ndescription: Skill dos\n---\n# Dos",
                encoding="utf-8",
            )

            # Armar mapa de disco
            ejecutar_mapa(["resumen"], home, claude_dir)

            # CATALOGO.yaml registra 'uno' y 'fantasma' (que no está en disco)
            catalogo_yaml = home / "CATALOGO.yaml"
            catalogo_yaml.write_text(
                "skills:\n"
                "  uno: {\n"
                "    estado: si,\n"
                "    vive: local\n"
                "  }\n"
                "  fantasma: {\n"
                "    estado: si,\n"
                "    vive: local\n"
                "  }\n",
                encoding="utf-8",
            )

            r = ejecutar_mapa(["sin-registrar", "--catalogo", str(catalogo_yaml)], home, claude_dir)
            self.assertEqual(r.returncode, 0)

            # 'dos' no está en catálogo -> sin registrar
            self.assertIn("sin registrar", r.stdout)
            self.assertIn("dos", r.stdout)

            # 'fantasma' está en catálogo pero no en disco -> registrada que ya no está
            self.assertIn("registrada que ya no está", r.stdout)
            self.assertIn("fantasma", r.stdout)

    def test_10b_sin_registrar_vive_en_el_catalogo(self):
        """Las piezas con `vive: catalogo` (agentes y skills) se buscan en el repo del catálogo; solo la que falta se avisa."""
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            claude_dir, _ = crear_mundo_minimo(home)
            plugins = home / "Proyectos" / "Tech" / "claude-catalogo" / "plugins" / "p"
            (plugins / "agents").mkdir(parents=True)
            (plugins / "agents" / "revisor.md").write_text("---\nname: revisor\n---\n", encoding="utf-8")
            (plugins / "skills" / "sk").mkdir(parents=True)
            (plugins / "skills" / "sk" / "SKILL.md").write_text("---\nname: sk\n---\n", encoding="utf-8")
            ejecutar_mapa(["resumen"], home, claude_dir)
            catalogo_yaml = home / "CATALOGO.yaml"
            catalogo_yaml.write_text(
                "skills:\n"
                "  uno: {estado: si, vive: local}\n"
                "  revisor: {estado: si, vive: catalogo}\n"
                "  sk: {estado: si, vive: catalogo}\n"
                "  perdido: {estado: si, vive: catalogo}\n",
                encoding="utf-8",
            )
            r = ejecutar_mapa(["sin-registrar", "--catalogo", str(catalogo_yaml)], home, claude_dir)
            self.assertEqual(r.returncode, 0)
            self.assertIn("perdido", r.stdout)
            self.assertNotIn("revisor", r.stdout)
            self.assertNotIn("- sk", r.stdout)

    def test_11_error_de_uso_codigo_64(self):
        """Error de subcomando o argumento inválido imprime en español y sale 64."""
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir)
            claude_dir, _ = crear_mundo_minimo(home)

            r = ejecutar_mapa(["subcomando_inexistente"], home, claude_dir)
            self.assertEqual(r.returncode, 64)
            self.assertIn("mapa: error de uso:", r.stderr)


if __name__ == "__main__":
    unittest.main()
