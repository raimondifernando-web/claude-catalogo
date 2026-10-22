#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_mapa_lector_lint.py - Pruebas de lint sintáctico (AST) y dinámicas para mapa_lector.py.
Disparador: encadenado — lo usa mapa.py (el comando `mapa`).

Comprueba que mapa_lector.py no realice llamadas directas al disco fuera de mapa_io,
y que el registro resultante de leer_disco capture todos los elementos inspeccionados.
Python 3.9 estándar, sin librerías externas.
"""

import ast
import json
import os
from pathlib import Path
import tempfile
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mapa_io import IO
from mapa_lector import leer_disco, cerrar
import mapa_uso


class TestMapaLectorLint(unittest.TestCase):
    def test_ast_sin_llamadas_prohibidas(self):
        """
        Inspecciona el AST de mapa_lector.py y falla si encuentra llamadas directas a:
        open, os.walk, os.scandir, os.listdir, os.stat, os.lstat, os.path.exists/isdir/isfile/getmtime/getsize,
        subprocess, Path.home, os.path.expanduser, o métodos de Path (.iterdir, .glob, .rglob, .is_dir,
        .is_file, .exists, .stat, .lstat, .read_text, .read_bytes, .resolve).
        """
        lector_path = Path(__file__).parent.parent / "mapa_lector.py"
        with open(lector_path, "r", encoding="utf-8") as f:
            contenido = f.read()

        tree = ast.parse(contenido, filename=str(lector_path))
        fallas = []

        metodos_prohibidos = {
            "iterdir", "glob", "rglob", "is_dir", "is_file", "exists",
            "stat", "lstat", "read_text", "read_bytes", "resolve",
            "isdir", "isfile",
        }

        funciones_prohibidas = {
            "walk", "scandir", "listdir", "lstat", "getmtime", "getsize", "expanduser", "home",
        }

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue

            func = node.func

            # 1. Llamadas directas: open(...) o subprocess(...)
            if isinstance(func, ast.Name):
                if func.id == "open":
                    fallas.append((node.lineno, "open()"))
                elif func.id == "subprocess":
                    fallas.append((node.lineno, "subprocess()"))

            # 2. Llamadas a atributos: os.walk, Path.home, obj.is_dir, etc.
            elif isinstance(func, ast.Attribute):
                attr = func.attr
                if attr in metodos_prohibidos:
                    fallas.append((node.lineno, f".{attr}()"))
                elif attr in funciones_prohibidas:
                    fallas.append((node.lineno, f".{attr}()"))
                else:
                    # Comprobar receptor subprocess o módulo os.path
                    val = func.value
                    val_id = getattr(val, "id", None)
                    if val_id == "subprocess":
                        fallas.append((node.lineno, f"subprocess.{attr}()"))
                    elif isinstance(val, ast.Attribute) and getattr(val, "attr", None) == "path":
                        if attr in ("exists", "isdir", "isfile", "getmtime", "getsize", "expanduser"):
                            fallas.append((node.lineno, f"os.path.{attr}()"))

        if fallas:
            lineas_msg = [f"{lector_path.name}:{line} - llamada prohibida: {call}" for line, call in fallas]
            self.fail(f"Llamadas prohibidas encontradas en mapa_lector.py:\n" + "\n".join(lineas_msg))

    def test_dinamica_leer_disco_registra_elementos(self):
        """
        Prueba dinámica con un HOME falso mínimo: una skill, un agente, un settings.json
        y un proyecto con .claude. Comprueba que el Registro contiene la carpeta de skills,
        el SKILL.md, el agente y el settings.json.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            fake_home = tmp / "home"
            claude_dir = fake_home / ".claude"
            proyectos_dir = fake_home / "Proyectos"

            # 1 skill: ~/.claude/skills/mi-skill/SKILL.md
            skill_dir = claude_dir / "skills" / "mi-skill"
            skill_dir.mkdir(parents=True)
            skill_md = skill_dir / "SKILL.md"
            skill_md.write_text("---\nname: mi-skill\ndescription: Skill de prueba\n---\nContenido de skill")

            # 1 agente: ~/.claude/agents/mi-agente.md
            agents_dir = claude_dir / "agents"
            agents_dir.mkdir(parents=True)
            agente_md = agents_dir / "mi-agente.md"
            agente_md.write_text("---\nname: mi-agente\ndescription: Agente de prueba\n---\nContenido agente")

            # 1 settings.json: ~/.claude/settings.json
            settings_json = claude_dir / "settings.json"
            settings_json.write_text(json.dumps({"enabledPlugins": {}}))

            # 1 proyecto con .claude: ~/Proyectos/proy1/.claude
            proy_claude = proyectos_dir / "proy1" / ".claude"
            proy_claude.mkdir(parents=True)

            io = IO(home=fake_home, claude_dir=claude_dir)
            inv_disco = leer_disco(io, proyectos_dir)

            self.assertIsInstance(inv_disco, dict)

            # Comprobar que el Registro contiene la carpeta de skills, el SKILL.md, el agente y el settings.json
            skills_folder_str = str(os.path.abspath(str(claude_dir / "skills")))
            skill_md_str = str(os.path.abspath(str(skill_md)))
            agente_md_str = str(os.path.abspath(str(agente_md)))
            settings_json_str = str(os.path.abspath(str(settings_json)))

            self.assertIn(skills_folder_str, io.registro.dirs)
            self.assertIn(skill_md_str, io.registro.arch)
            self.assertIn(agente_md_str, io.registro.arch)
            self.assertIn(settings_json_str, io.registro.arch)

    def test_cierre_con_a_json_y_de_json(self):
        """Comprueba que cerrar() funcione idéntico con datos originales o serializados con a_json/de_json."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            fake_home = tmp / "home"
            claude_dir = fake_home / ".claude"
            claude_dir.mkdir(parents=True)
            io = IO(home=fake_home, claude_dir=claude_dir)
            inv_disco = leer_disco(io, fake_home / "Proyectos")

            stats = {c: {} for c in mapa_uso.CATEGORIAS_USO}
            metricas = {
                "archivos_jsonl_leidos": 0, "archivos_principales": 0, "archivos_subagentes": 0,
                "lineas_leidas": 0, "lineas_no_parseadas": 0, "solo_disco": True
            }
            contador = {}

            paquete = mapa_uso.a_json(stats, metricas, contador)
            s_rec, m_rec, c_rec = mapa_uso.de_json(paquete)

            inv1 = cerrar(inv_disco, stats, metricas, contador, io)
            inv2 = cerrar(inv_disco, s_rec, m_rec, c_rec, io)

            self.assertEqual(inv1["resumen"], inv2["resumen"])
            self.assertEqual(inv1["skills_personales"], inv2["skills_personales"])
            self.assertEqual(inv1["metricas_ejecucion"], inv2["metricas_ejecucion"])


if __name__ == "__main__":
    unittest.main()
