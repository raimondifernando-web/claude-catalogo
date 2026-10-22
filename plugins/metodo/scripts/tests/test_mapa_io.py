#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_mapa_io.py - Pruebas unitarias para el módulo mapa_io.py.
Disparador: encadenado — lo usa mapa.py (el comando `mapa`).

Verifica firma lstat, Registro serializable, listar, modo proyectos,
detección de cambios y nombres_json sin fugas de valores confidenciales.
Python 3.9 estándar, sin librerías externas.
"""

import json
import os
from pathlib import Path
import tempfile
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mapa_io import IO, Registro, cambios, firma, huella_claves


class TestMapaIO(unittest.TestCase):
    def test_firma_archivo_normal(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            f_norm = tmp / "normal.txt"
            f_norm.write_text("prueba de contenido")
            sig = firma(f_norm)
            self.assertRegex(sig, r"^\d+:\d+$")

    def test_firma_archivo_ausente(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            f_aus = tmp / "inexistente.txt"
            self.assertEqual(firma(f_aus), "ausente")

    def test_firma_enlace_roto(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            f_roto = tmp / "enlace_roto"
            try:
                os.symlink(tmp / "destino_inexistente", f_roto)
            except OSError:
                return  # Si el sistema de archivos no permite symlinks, omitir

            sig = firma(f_roto)
            # No debe levantar excepción: es una firma válida o empieza con ERR:
            self.assertTrue(sig.startswith("ERR:") or ":" in sig)

    def test_listar_registra_y_cambios(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            home = tmp / "home"
            d = home / "carpeta"
            d.mkdir(parents=True)
            f1 = d / "f1.txt"
            f1.write_text("uno")

            io = IO(home=home, claude_dir=home / ".claude")
            entradas = io.listar(d)
            self.assertEqual(len(entradas), 1)
            self.assertEqual(entradas[0].nombre, "f1.txt")

            d_str = os.path.abspath(str(d))
            self.assertIn(d_str, io.registro.dirs)
            self.assertEqual(io.registro.dirs[d_str][1], huella_claves(["f1.txt"]))

            # Al no haber modificaciones, cambios() debe ser lista vacía
            self.assertEqual(cambios(io.registro, home), [])

            # Crear un archivo nuevo en la carpeta listada hace que cambios() devuelva ("carpeta", ruta)
            f2 = d / "f2.txt"
            f2.write_text("dos")
            difs = cambios(io.registro, home)
            self.assertIn(("carpeta", d_str), difs)

    def test_modo_proyectos_y_archivos_irrelevantes(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            home = tmp / "home"
            proy_x = home / "Proyectos" / "X"
            proy_x.mkdir(parents=True)

            io = IO(home=home, claude_dir=home / ".claude")
            io.listar(proy_x)
            proy_x_str = os.path.abspath(str(proy_x))

            # Bajo home/Proyectos/X (sin .claude en la ruta) crear un archivo cualquiera -> NO cuenta
            (proy_x / "build.log").write_text("log temporal")
            self.assertEqual(cambios(io.registro, home), [])

            # Modificar la fecha de la carpeta SIN cambiar nombres relevantes -> NO cuenta
            os.utime(proy_x, (1000000, 1000000))
            self.assertEqual(cambios(io.registro, home), [])

            # Crear una subcarpeta -> cuenta
            sub = proy_x / "submodulo"
            sub.mkdir()
            difs = cambios(io.registro, home)
            self.assertIn(("carpeta", proy_x_str), difs)

            # Crear .mcp.json -> cuenta
            sub.rmdir()
            io2 = IO(home=home, claude_dir=home / ".claude")
            io2.listar(proy_x)
            (proy_x / ".mcp.json").write_text("{}")
            difs2 = cambios(io2.registro, home)
            self.assertIn(("carpeta", proy_x_str), difs2)

            # Dentro de home/Proyectos/X/.claude/skills crear un archivo -> cuenta
            skills_dir = proy_x / ".claude" / "skills"
            skills_dir.mkdir(parents=True)
            io3 = IO(home=home, claude_dir=home / ".claude")
            io3.listar(skills_dir)
            skills_dir_str = os.path.abspath(str(skills_dir))

            (skills_dir / "otro.txt").write_text("contenido")
            difs3 = cambios(io3.registro, home)
            self.assertIn(("carpeta", skills_dir_str), difs3)

    def test_nombres_json_seguridad_y_cambios(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            home = tmp / "home"
            home.mkdir(parents=True)
            cfg_path = home / ".claude.json"
            cfg_path.write_text(json.dumps({
                "mcpServers": {
                    "srv1": {
                        "env": {"TOKEN": "CLAVE-FALSA-123"},
                        "args": ["--secret", "password123"]
                    }
                }
            }))

            io = IO(home=home, claude_dir=home / ".claude")
            nombres = io.nombres_json(cfg_path, ["mcpServers"], "mcp_usuario")
            self.assertEqual(nombres, ["srv1"])

            # Comprobar que cambios() no detecta diferencias iniciales
            self.assertEqual(cambios(io.registro, home), [])

            # Cambiar token/valor sin cambiar nombres -> cambios() vacío
            cfg_path.write_text(json.dumps({
                "mcpServers": {
                    "srv1": {
                        "env": {"TOKEN": "OTRO-TOKEN-MODIFICADO"},
                        "args": ["--secret", "otro_secreto"]
                    }
                }
            }))
            self.assertEqual(cambios(io.registro, home), [])

            # Agregar un nombre de servidor -> ("contenido", clave)
            cfg_path.write_text(json.dumps({
                "mcpServers": {
                    "srv1": {"env": {}},
                    "srv2": {"env": {}}
                }
            }))
            difs = cambios(io.registro, home)
            self.assertIn(("contenido", "mcp_usuario"), difs)

            # Comprobar que el Registro serializado con json.dumps NO contiene ningún valor confidencial
            serializado = json.dumps(io.registro)
            self.assertNotIn("CLAVE-FALSA-123", serializado)
            self.assertNotIn("password123", serializado)
            self.assertNotIn("OTRO-TOKEN-MODIFICADO", serializado)

    def test_caminar_con_poda_en_el_lugar(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            raiz = tmp / "raiz"
            (raiz / "sub1").mkdir(parents=True)
            (raiz / "sub1" / "archivo1.txt").write_text("1")
            (raiz / "ignorar").mkdir(parents=True)
            (raiz / "ignorar" / "archivo2.txt").write_text("2")

            io = IO(home=tmp, claude_dir=tmp / ".claude")
            visitados = []
            for actual, dirs, _files in io.caminar(raiz):
                visitados.append(os.path.basename(actual))
                dirs[:] = [d for d in dirs if d != "ignorar"]

            self.assertIn("raiz", visitados)
            self.assertIn("sub1", visitados)
            self.assertNotIn("ignorar", visitados)

            raiz_str = os.path.abspath(str(raiz))
            self.assertIn(raiz_str, io.registro.dirs)

    def test_registro_mezclar(self):
        r1 = Registro(arch={"/a": "1"}, dirs={"/d1": ["1", ["x"]]}, contenido={"k1": "h1"})
        r2 = Registro(arch={"/b": "2"}, dirs={"/d2": ["2", ["y"]]}, contenido={"k2": "h2"})
        r1.mezclar(r2)
        self.assertIn("/a", r1.arch)
        self.assertIn("/b", r1.arch)
        self.assertIn("/d1", r1.dirs)
        self.assertIn("/d2", r1.dirs)
        self.assertIn("k1", r1.contenido)
        self.assertIn("k2", r1.contenido)


if __name__ == "__main__":
    unittest.main()
