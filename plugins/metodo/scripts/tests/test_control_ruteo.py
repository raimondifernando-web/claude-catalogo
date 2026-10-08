"""Tests de control-ruteo.py (plugin metodo).

Solo biblioteca estándar, SIN red. Transcripts falsos en tempfile.
Correr desde la raíz del repo:
    python3 -m unittest discover -s plugins/metodo/scripts/tests -p 'test_control_ruteo.py' -v
"""
import contextlib
import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

AQUI = Path(__file__).resolve().parent
if str(AQUI) not in sys.path:
    sys.path.insert(0, str(AQUI))

from test_radar import Base, R

CONTROL_RUTEO_PY = AQUI.parent / "control-ruteo.py"


def cargar_modulo(nombre, ruta):
    spec = importlib.util.spec_from_file_location(nombre, str(ruta))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[nombre] = mod
    spec.loader.exec_module(mod)
    return mod


CR = cargar_modulo("control_ruteo", CONTROL_RUTEO_PY)


class TestControlRuteo(Base):
    """Batería de pruebas unitarias para control-ruteo.py."""

    def test_cuenta_modelos_y_esfuerzos_agent_y_start_session(self):
        """1) Cuenta modelos y esfuerzos de Agent y start_session."""
        carpeta = self.tmp / "projects" / "p1"
        carpeta.mkdir(parents=True, exist_ok=True)
        archivo = carpeta / "transcript.jsonl"

        entradas = [
            {"timestamp": "2026-10-08T10:00:00Z", "message": {"content": [
                {"type": "tool_use", "name": "Agent", "input": {"model": "claude-3-5-sonnet-20241022", "effort": "medium"}}
            ]}},
            {"timestamp": "2026-10-08T10:05:00Z", "message": {"content": [
                {"type": "tool_use", "name": "Task", "input": {"model": "claude-3-5-haiku-20241022", "effort": "low"}}
            ]}},
            {"timestamp": "2026-10-08T10:10:00Z", "message": {"content": [
                {"type": "tool_use", "name": "project_start_session", "input": {"model": "claude-3-opus", "effort": "high"}}
            ]}},
            {"timestamp": "2026-10-08T10:15:00Z", "message": {"content": [
                {"type": "tool_use", "name": "start_session", "input": {"model": "", "effort": ""}}
            ]}},
            {"timestamp": "2026-10-08T10:20:00Z", "message": {"content": [
                {"type": "tool_use", "name": "Agent", "input": {"model": "fable-preview", "effort": "max"}}
            ]}},
            {"timestamp": "2026-10-08T10:25:00Z", "message": {"content": [
                {"type": "tool_use", "name": "Agent", "input": {"model": "gpt-4o", "effort": "xhigh"}}
            ]}},
        ]

        with open(archivo, "w", encoding="utf-8") as f:
            for e in entradas:
                f.write(json.dumps(e) + "\n")

        ahora = datetime(2026, 10, 8, 12, 0, 0)
        res = CR.medir(self.tmp / "projects", dias=30, radar=None, ahora=ahora)

        self.assertEqual(res["subagentes"], 6)
        self.assertEqual(res["modelos"]["sonnet"], 1)
        self.assertEqual(res["modelos"]["haiku"], 1)
        self.assertEqual(res["modelos"]["opus"], 1)
        self.assertEqual(res["modelos"]["fable"], 1)
        self.assertEqual(res["modelos"]["sin_model"], 1)
        self.assertEqual(res["modelos"]["otro"], 1)

        self.assertEqual(res["esfuerzos"]["medium"], 1)
        self.assertEqual(res["esfuerzos"]["low"], 1)
        self.assertEqual(res["esfuerzos"]["high"], 1)
        self.assertEqual(res["esfuerzos"]["sin_effort"], 1)
        self.assertEqual(res["esfuerzos"]["max"], 1)
        self.assertEqual(res["esfuerzos"]["xhigh"], 1)

    def test_cuenta_codex_y_gemini_delegar_bash(self):
        """2) Cuenta Codex y Gemini/delegar con comandos Bash falsos (incluye uno que no coincide)."""
        carpeta = self.tmp / "projects" / "p2"
        carpeta.mkdir(parents=True, exist_ok=True)
        archivo = carpeta / "transcript.jsonl"

        entradas = [
            # Gemini o delegar (3 casos)
            {"timestamp": "2026-10-08T10:00:00Z", "message": {"content": [
                {"type": "tool_use", "name": "Bash", "input": {"command": "agy-delegar tareas_baratas repo 'pedido'"}}
            ]}},
            {"timestamp": "2026-10-08T10:05:00Z", "message": {"content": [
                {"type": "tool_use", "name": "Bash", "input": {"command": "agy --model gemini-2.5-pro 'pedido'"}}
            ]}},
            {"timestamp": "2026-10-08T10:10:00Z", "message": {"content": [
                {"type": "tool_use", "name": "Bash", "input": {"command": "python3 delegar.py desarrollo repo 'pedido'"}}
            ]}},
            # Codex (3 casos)
            {"timestamp": "2026-10-08T10:15:00Z", "message": {"content": [
                {"type": "tool_use", "name": "Bash", "input": {"command": "codex exec 'revisar el diff'"}}
            ]}},
            {"timestamp": "2026-10-08T10:20:00Z", "message": {"content": [
                {"type": "tool_use", "name": "Bash", "input": {"command": "codex --search exec 'probar'"}}
            ]}},
            {"timestamp": "2026-10-08T10:25:00Z", "message": {"content": [
                {"type": "tool_use", "name": "Bash", "input": {"command": "codex-rescue"}}
            ]}},
            # Ambos a la vez (suma a gemini_o_delegar y a codex)
            {"timestamp": "2026-10-08T10:30:00Z", "message": {"content": [
                {"type": "tool_use", "name": "Bash", "input": {"command": "agy-delegar && codex exec 'ambos'"}}
            ]}},
            # Agent con subagent_type codex (suma a codex)
            {"timestamp": "2026-10-08T10:35:00Z", "message": {"content": [
                {"type": "tool_use", "name": "Agent", "input": {"subagent_type": "codex-reviewer", "model": "haiku"}}
            ]}},
            # Comando que no coincide con ninguno
            {"timestamp": "2026-10-08T10:40:00Z", "message": {"content": [
                {"type": "tool_use", "name": "Bash", "input": {"command": "git status -s"}}
            ]}},
        ]

        with open(archivo, "w", encoding="utf-8") as f:
            for e in entradas:
                f.write(json.dumps(e) + "\n")

        ahora = datetime(2026, 10, 8, 12, 0, 0)
        res = CR.medir(self.tmp / "projects", dias=30, radar=None, ahora=ahora)

        self.assertEqual(res["gemini_o_delegar"], 4)
        self.assertEqual(res["codex"], 5)

    def test_sobredimensionado(self):
        """3) Sobredimensionado según radar chico a mano."""
        carpeta = self.tmp / "projects" / "p3"
        carpeta.mkdir(parents=True, exist_ok=True)
        archivo = carpeta / "transcript.jsonl"

        radar_prueba = {
            "ruteo_claude": {
                "tareas": [
                    {"id": "buscar", "corto": "buscar", "nivel": "haiku", "esfuerzo": "low", "palabras": ["buscar"]}
                ]
            }
        }

        entradas = [
            # Caso 1: description 'buscar archivos', model 'opus' -> sobredimensionado
            {"timestamp": "2026-10-08T10:00:00Z", "message": {"content": [
                {"type": "tool_use", "name": "Agent", "input": {"description": "buscar archivos", "model": "opus"}}
            ]}},
            # Caso 2: description 'buscar archivos', model 'haiku', effort 'low' -> no sobredimensionado
            {"timestamp": "2026-10-08T10:05:00Z", "message": {"content": [
                {"type": "tool_use", "name": "Agent", "input": {"description": "buscar archivos", "model": "haiku", "effort": "low"}}
            ]}},
            # Caso 3: description 'buscar archivos', model 'haiku', effort 'high' -> sobredimensionado por esfuerzo
            {"timestamp": "2026-10-08T10:10:00Z", "message": {"content": [
                {"type": "tool_use", "name": "Agent", "input": {"description": "buscar archivos", "model": "haiku", "effort": "high"}}
            ]}},
            # Caso 4: sesión derivada con title que no matchea palabras -> no medido
            {"timestamp": "2026-10-08T10:15:00Z", "message": {"content": [
                {"type": "tool_use", "name": "start_session", "input": {"title": "cocinar pizza", "model": "opus"}}
            ]}},
        ]

        with open(archivo, "w", encoding="utf-8") as f:
            for e in entradas:
                f.write(json.dumps(e) + "\n")

        ahora = datetime(2026, 10, 8, 12, 0, 0)
        res = CR.medir(self.tmp / "projects", dias=30, radar=radar_prueba, ahora=ahora)

        self.assertEqual(res["medidos"], 3)
        self.assertEqual(res["sobredimensionados"], 2)

    def test_ventana_dias_excluye_entradas_viejas(self):
        """4) La ventana de días excluye entradas viejas."""
        carpeta = self.tmp / "projects" / "p4"
        carpeta.mkdir(parents=True, exist_ok=True)

        # Archivo con timestamps ISO explícitos
        archivo1 = carpeta / "t1.jsonl"
        entradas1 = [
            {"timestamp": "2026-10-05T12:00:00Z", "message": {"content": [
                {"type": "tool_use", "name": "Agent", "input": {"model": "haiku"}}
            ]}},
            {"timestamp": "2026-08-01T12:00:00Z", "message": {"content": [
                {"type": "tool_use", "name": "Agent", "input": {"model": "opus"}}
            ]}},
        ]
        with open(archivo1, "w", encoding="utf-8") as f:
            for e in entradas1:
                f.write(json.dumps(e) + "\n")

        # Archivo sin timestamps, pero con mtime antiguo
        archivo_viejo = carpeta / "t_viejo.jsonl"
        with open(archivo_viejo, "w", encoding="utf-8") as f:
            f.write(json.dumps({"message": {"content": [{"type": "tool_use", "name": "Agent", "input": {"model": "sonnet"}}]}}) + "\n")
        mtime_viejo = (datetime(2026, 8, 1, 12, 0, 0)).timestamp()
        os.utime(str(archivo_viejo), (mtime_viejo, mtime_viejo))

        # Archivo sin timestamps, con mtime reciente
        archivo_reciente = carpeta / "t_reciente.jsonl"
        with open(archivo_reciente, "w", encoding="utf-8") as f:
            f.write(json.dumps({"message": {"content": [{"type": "tool_use", "name": "Agent", "input": {"model": "haiku"}}]}}) + "\n")
        mtime_reciente = (datetime(2026, 10, 7, 12, 0, 0)).timestamp()
        os.utime(str(archivo_reciente), (mtime_reciente, mtime_reciente))

        ahora = datetime(2026, 10, 10, 12, 0, 0)
        res = CR.medir(carpeta, dias=30, radar=None, ahora=ahora)

        self.assertEqual(res["subagentes"], 2)
        self.assertEqual(res["modelos"]["haiku"], 2)
        self.assertEqual(res["modelos"]["opus"], 0)
        self.assertEqual(res["modelos"]["sonnet"], 0)

    def test_linea_json_rota_y_archivo_vacio_no_rompen(self):
        """5) Línea JSON rota y archivo vacío no rompen."""
        carpeta = self.tmp / "projects" / "p5"
        carpeta.mkdir(parents=True, exist_ok=True)

        archivo_vacio = carpeta / "vacio.jsonl"
        archivo_vacio.write_text("", encoding="utf-8")

        archivo_rotas = carpeta / "rotas.jsonl"
        contenido = (
            '{"incompleto":\n'
            'esto no es un json para nada\n'
            '{"timestamp": "2026-10-08T10:00:00Z", "message": {"content": [{"type": "tool_use", "name": "Agent", "input": {"model": "haiku", "effort": "low"}}]}}\n'
            '   \n'
            '{"evento_valido_pero_sin_message": 1}\n'
        )
        archivo_rotas.write_text(contenido, encoding="utf-8")

        ahora = datetime(2026, 10, 8, 12, 0, 0)
        res = CR.medir(carpeta, dias=30, radar=None, ahora=ahora)

        self.assertEqual(res["subagentes"], 1)
        self.assertEqual(res["modelos"]["haiku"], 1)
        self.assertEqual(res["esfuerzos"]["low"], 1)
        self.assertEqual(res["ilegibles"], 0)

    def test_privacidad_nada_de_salida_contiene_datos_sensibles(self):
        """6) PRIVACIDAD: ninguna frase ni ruta del directorio aparece en la salida."""
        carpeta = self.tmp / "projects" / "p6_privacidad"
        carpeta.mkdir(parents=True, exist_ok=True)
        archivo = carpeta / "transcript.jsonl"

        frase_secreta = "SECRETO_CONFIDENCIAL_CLAVE_XYZ_987654321"

        entradas = [
            {"timestamp": "2026-10-08T10:00:00Z", "message": {"content": [
                {"type": "tool_use", "name": "Agent", "input": {
                    "prompt": "Por favor procesar " + frase_secreta,
                    "description": "Buscar el " + frase_secreta,
                    "model": "haiku"
                }},
                {"type": "tool_use", "name": "Bash", "input": {
                    "command": "echo '" + frase_secreta + "'"
                }}
            ]}}
        ]

        with open(archivo, "w", encoding="utf-8") as f:
            for e in entradas:
                f.write(json.dumps(e) + "\n")

        ahora = datetime(2026, 10, 8, 12, 0, 0)
        datos = CR.medir(carpeta, dias=30, radar=None, ahora=ahora)

        # 1. Comprobación en resumen
        lineas = CR.resumen(datos, 30)
        texto_resumen = "\n".join(lineas)
        self.assertNotIn(frase_secreta, texto_resumen)
        self.assertNotIn(str(carpeta), texto_resumen)
        self.assertNotIn("p6_privacidad", texto_resumen)

        # 2. Comprobación en CLI modo normal
        out_normal = io.StringIO()
        with contextlib.redirect_stdout(out_normal):
            cod_normal = CR.main(["--carpeta", str(carpeta)])
        self.assertEqual(cod_normal, 0)
        salida_normal = out_normal.getvalue()
        self.assertNotIn(frase_secreta, salida_normal)
        self.assertNotIn(str(carpeta), salida_normal)
        self.assertNotIn("p6_privacidad", salida_normal)

        # 3. Comprobación en CLI modo --json
        out_json = io.StringIO()
        with contextlib.redirect_stdout(out_json):
            cod_json = CR.main(["--carpeta", str(carpeta), "--json"])
        self.assertEqual(cod_json, 0)
        salida_json = out_json.getvalue()
        self.assertNotIn(frase_secreta, salida_json)
        self.assertNotIn(str(carpeta), salida_json)
        self.assertNotIn("p6_privacidad", salida_json)

    def test_carpeta_inexistente_linea_unica_y_codigo_0(self):
        """7) Carpeta inexistente imprime línea única y sale con 0."""
        ruta_inexistente = self.tmp / "carpeta_que_no_existe_jamas_1234"
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            codigo = CR.main(["--carpeta", str(ruta_inexistente)])

        self.assertEqual(codigo, 0)
        lineas = out.getvalue().strip().splitlines()
        self.assertEqual(len(lineas), 1)
        self.assertEqual(lineas[0], "Control del ruteo: no hay transcripts para medir.")

    def test_resumen_exactamente_tres_lineas(self):
        """8) El resumen tiene exactamente 3 líneas en todas las variantes."""
        # Variante A: caso normal medido con desvíos
        datos_a = {
            "subagentes": 42,
            "modelos": {"sonnet": 25, "haiku": 10, "opus": 5, "sin_model": 2},
            "esfuerzos": {"medium": 20, "low": 12, "sin_effort": 10},
            "codex": 3,
            "gemini_o_delegar": 7,
            "medidos": 30,
            "sobredimensionados": 6,
            "ilegibles": 0
        }
        res_a = CR.resumen(datos_a, 30)
        self.assertEqual(len(res_a), 3)
        self.assertEqual(
            res_a[0],
            "Control del ruteo (últimos 30 días): 42 subagentes o sesiones derivadas · modelos: sonnet 25, haiku 10, opus 5, sin_model 2 · esfuerzo: medium 20, low 12, sin_effort 10."
        )
        self.assertEqual(res_a[1], "A otras IA: Codex 3 · Gemini o delegar.py 7.")
        self.assertEqual(res_a[2], "Sobredimensionados según el ruteo: 6 de 30 medidos (20 %).")

        # Variante B: sin medibles
        datos_b = dict(datos_a)
        datos_b["medidos"] = 0
        datos_b["sobredimensionados"] = 0
        res_b = CR.resumen(datos_b, 30)
        self.assertEqual(len(res_b), 3)
        self.assertEqual(res_b[2], "Sobredimensionados: sin datos medibles.")

        # Variante C: radar no cargó (sobredimensionados es None)
        datos_c = dict(datos_a)
        datos_c["sobredimensionados"] = None
        res_c = CR.resumen(datos_c, 30)
        self.assertEqual(len(res_c), 3)
        self.assertEqual(res_c[2], "Sobredimensionados: no se pudo leer el ruteo.")

        # Variante D: todo en cero
        datos_d = {
            "subagentes": 0,
            "modelos": {},
            "esfuerzos": {},
            "codex": 0,
            "gemini_o_delegar": 0,
            "medidos": 0,
            "sobredimensionados": 0,
            "ilegibles": 0
        }
        res_d = CR.resumen(datos_d, 30)
        self.assertEqual(len(res_d), 3)
        self.assertEqual(res_d[0], "Control del ruteo (últimos 30 días): 0 subagentes o sesiones derivadas · modelos: sin datos · esfuerzo: sin datos.")
        self.assertEqual(res_d[1], "A otras IA: Codex 0 · Gemini o delegar.py 0.")
        self.assertEqual(res_d[2], "Sobredimensionados: sin datos medibles.")


if __name__ == "__main__":
    unittest.main()
