"""Tests del radar de modelos (plugin metodo). Solo biblioteca estándar, SIN red (fuentes simuladas).

Correr desde la raíz del repo:
    python3 -m unittest discover -s plugins/metodo/scripts/tests -v
"""
import contextlib
import importlib.util
import io
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
from pathlib import Path

AQUI = Path(__file__).resolve().parent
PLUGIN = AQUI.parent.parent
RAIZ = PLUGIN.parent.parent
RADAR_PY = AQUI.parent / "radar.py"
FUENTES_PY = RAIZ / "scripts" / "radar-fuentes.py"
YAML_REAL = PLUGIN / "radar" / "RADAR.yaml"
WORKFLOW = RAIZ / ".github" / "workflows" / "radar.yml"


def cargar_modulo(nombre, ruta):
    spec = importlib.util.spec_from_file_location(nombre, str(ruta))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[nombre] = mod
    spec.loader.exec_module(mod)
    return mod


R = cargar_modulo("radar", RADAR_PY)
FU = cargar_modulo("radar_fuentes", FUENTES_PY)
ES_WINDOWS = os.name == "nt"


def plan(letra, herramienta="Claude Code", api=None, privados=True, cupo=None, **extra):
    d = {"plan": letra, "herramienta": herramienta, "proveedor": "X", "modelo": "m" + letra, "modelo_api": api,
         "por_que": "porque " + letra, "datos_privados": privados, "cupo": cupo, "verificado": True}
    d.update(extra)
    return d


def radar_de_prueba(**extra):
    r = {"actualizado": "2026-10-03",
         "categorias": [{"id": "desarrollo", "nombre": "Desarrollo", "planes": [
             plan("A", "Codex", "modelo-a", True, "codex"),
             plan("B", "Antigravity", "modelo-b", False),
             plan("C", "Claude Code", "modelo-c", True)],
             "ranking": {"items": [{"puesto": 1, "modelo": "viejo", "puntaje": 1}]}}],
         "retiros": [], "precios_usd_por_millon": {"modelo-c": {"entrada": 10, "salida": 50}},
         "fuentes_auto": {"paginas_retiros": {"anthropic": {"url": "https://x", "hash": "abc"}}}}
    r.update(extra)
    return r


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="radar-test-"))
        self.addCleanup(shutil.rmtree, str(self.tmp), True)
        self.env_previo = dict(os.environ)
        self.addCleanup(self._restaurar)
        os.environ["CLAUDE_CONFIG_DIR"] = str(self.tmp / "config")
        os.environ["RADAR_HOY"] = "2026-10-10"
        os.environ.pop("RADAR_PROBAR", None)
        os.environ["CEREBRO_HOME"] = str(self.tmp / "cerebro")
        # aislado del cupo REAL de la máquina que corre los tests
        self.cupo_falso(0, "Codex: cupo desconocido (sin dato en los registros recientes)")
        self.claude_falso(0, "Current session: 0% used\n")
        self.agy_falso(0, json.dumps({"command": {"data": {"groups": [{"name": "Gemini", "buckets": [{"remaining_fraction": 1.0}]}]}}}))

    def _restaurar(self):
        os.environ.clear()
        os.environ.update(self.env_previo)

    def cupo_falso(self, codigo, texto):
        ruta = self.tmp / "codex-cupo-falso"
        ruta.write_text("#!/bin/bash\necho '%s'\nexit %d\n" % (texto, codigo))
        os.environ["RADAR_CODEX_CUPO"] = str(ruta)

    def claude_falso(self, codigo, texto):
        ruta = self.tmp / "claude-falso"
        if texto:
            contenido = "#!/bin/sh\ncat << 'EOF'\n%s\nEOF\nexit %d\n" % (texto, codigo)
        else:
            contenido = "#!/bin/sh\nexit %d\n" % codigo
        ruta.write_text(contenido, encoding="utf-8")
        ruta.chmod(0o755)
        os.environ["RADAR_CLAUDE_BIN"] = str(ruta)
        return ruta

    def agy_falso(self, codigo, texto):
        ruta = self.tmp / "agy-falso"
        if texto:
            contenido = "#!/bin/sh\ncat << 'EOF'\n%s\nEOF\nexit %d\n" % (texto, codigo)
        else:
            contenido = "#!/bin/sh\nexit %d\n" % codigo
        ruta.write_text(contenido, encoding="utf-8")
        ruta.chmod(0o755)
        os.environ["RADAR_AGY_BIN"] = str(ruta)
        return ruta

    def correr(self, *args):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            codigo = R.main(list(args))
        return codigo, out.getvalue()


@unittest.skipIf(ES_WINDOWS, "codex-cupo es un script de bash")
class TestElegir(Base):
    def test_elegir_salta_a_agotado_y_va_al_b(self):
        self.cupo_falso(2, "Codex: 93% del cupo mensual — NO lanzar")
        radar = radar_de_prueba()
        plan_, saltados, _ = R.elegir(radar, radar["categorias"][0], False, prueba={})
        self.assertEqual(plan_["plan"], "B")
        self.assertEqual(saltados[0][0]["plan"], "A")
        self.assertIn("cupo agotado", saltados[0][1])
        self.assertIn("93%", saltados[0][1])

    def test_con_cupo_ok_queda_el_a(self):
        self.cupo_falso(0, "Codex: 10% del cupo mensual — OK")
        radar = radar_de_prueba()
        plan_, saltados, _ = R.elegir(radar, radar["categorias"][0], False, prueba={})
        self.assertEqual(plan_["plan"], "A")
        self.assertEqual(saltados, [])

    def test_cupo_desconocido_no_salta(self):
        self.cupo_falso(0, "Codex: cupo desconocido (sin dato en los registros recientes)")
        radar = radar_de_prueba()
        plan_, _, _ = R.elegir(radar, radar["categorias"][0], False, prueba={})
        self.assertEqual(plan_["plan"], "A")

    def test_sensible_salta_el_gratis(self):
        self.cupo_falso(2, "Codex: 95% — NO lanzar")
        radar = radar_de_prueba()
        radar["categorias"][0]["planes"][0]["cupo"] = None
        radar["categorias"][0]["planes"][0]["datos_privados"] = False
        radar["categorias"][0]["planes"][0]["condiciones"] = "plan gratis"
        plan_, saltados, _ = R.elegir(radar, radar["categorias"][0], sensible=True, prueba={})
        self.assertEqual(plan_["plan"], "C")
        self.assertEqual([p["plan"] for p, _ in saltados], ["A", "B"])
        self.assertTrue(all("datos privados" in m for _, m in saltados))

    def test_modelo_retirado_y_prueba_no_disponible(self):
        radar = radar_de_prueba(retiros=[{"modelo": "modelo-a", "fecha": "2026-10-05", "tipo": "apagado"}])
        radar["categorias"][0]["planes"][0]["cupo"] = None
        prueba = {"modelo-b": {"disponible": False, "motivo": "404 cuentas nuevas", "fecha": "2026-10-08"}}
        plan_, saltados, _ = R.elegir(radar, radar["categorias"][0], False, prueba=prueba)
        self.assertEqual(plan_["plan"], "C")
        self.assertIn("se apagó el 2026-10-05", saltados[0][1])
        self.assertIn("404", saltados[1][1])

    def test_retiro_de_otra_fecha_o_no_antes_no_salta(self):
        radar = radar_de_prueba(retiros=[{"modelo": "modelo-a", "fecha": "2026-12-01", "tipo": "apagado"},
                                         {"modelo": "modelo-b", "fecha": "2026-10-01", "tipo": "no_antes"}])
        radar["categorias"][0]["planes"][0]["cupo"] = None
        plan_, _, _ = R.elegir(radar, radar["categorias"][0], False, prueba={})
        self.assertEqual(plan_["plan"], "A")

    def test_prueba_vieja_se_ignora(self):
        radar = radar_de_prueba()
        radar["categorias"][0]["planes"][0]["cupo"] = None
        prueba = {"modelo-a": {"disponible": False, "motivo": "x", "fecha": "2026-01-01"}}
        plan_, _, _ = R.elegir(radar, radar["categorias"][0], False, prueba=prueba)
        self.assertEqual(plan_["plan"], "A")

    def test_ninguno_disponible_sale_con_1(self):
        radar = radar_de_prueba()
        for p in radar["categorias"][0]["planes"]:
            p["datos_privados"] = False
            p["cupo"] = None
        os.environ["CLAUDE_CONFIG_DIR"] = str(self.tmp / "config")
        plan_, saltados, _ = R.elegir(radar, radar["categorias"][0], sensible=True, prueba={})
        self.assertIsNone(plan_)
        self.assertEqual(len(saltados), 3)


@unittest.skipIf(ES_WINDOWS, "scripts de sh")
class TestLectoresCupo(Base):
    def test_codex_salida_real_ok_alto_agotado(self):
        self.cupo_falso(0, "Codex: 15% del cupo mensual — OK")
        self.assertEqual(R.cupo_codex(), ("ok", "Codex: 15% del cupo mensual — OK"))
        self.cupo_falso(1, "Codex: 75% del cupo mensual — ALTO")
        self.assertEqual(R.cupo_codex(), ("alto", "Codex: 75% del cupo mensual — ALTO"))
        self.cupo_falso(2, "Codex: 95% del cupo mensual — NO lanzar")
        self.assertEqual(R.cupo_codex(), ("agotado", "Codex: 95% del cupo mensual — NO lanzar"))

    def test_codex_salida_vacia_y_rota(self):
        self.cupo_falso(0, "")
        self.assertEqual(R.cupo_codex(), ("desconocido", "Codex: cupo desconocido"))
        self.cupo_falso(0, "Codex: cupo desconocido (sin registros)")
        self.assertEqual(R.cupo_codex(), ("desconocido", "Codex: cupo desconocido"))
        os.environ["RADAR_CODEX_CUPO"] = str(self.tmp / "inexistente")
        self.assertEqual(R.cupo_codex(), ("desconocido", "Codex: cupo desconocido"))

    def test_claude_salida_real_cli(self):
        salida_ok = (
            "Current session: 28% used · resets Oct 5 at 11:59am (America/Cordoba)\n"
            "Current week (all models): 45% used · resets Oct 10 at 11:59am\n"
        )
        self.claude_falso(0, salida_ok)
        self.assertEqual(R.cupo_claude(), ("ok", "Claude: 45% usado"))

        salida_alto = (
            "Current session: 72% used · resets Oct 5 at 11:59am\n"
            "Current week (all models): 20% used · resets Oct 10\n"
        )
        self.claude_falso(0, salida_alto)
        self.assertEqual(R.cupo_claude(), ("alto", "Claude: 72% usado"))

        salida_agotado = (
            "Current session: 30% used\n"
            "Current week (all models): 93% used · resets Oct 10\n"
        )
        self.claude_falso(0, salida_agotado)
        self.assertEqual(R.cupo_claude(), ("agotado", "Claude: 93% usado"))

    def test_claude_salida_real_cupo_json(self):
        cerebro_dir = self.tmp / "cerebro"
        cerebro_dir.mkdir(parents=True, exist_ok=True)
        cupo_json = cerebro_dir / "cupo.json"
        # Datos frescos (< 900s)
        datos = {"five_hour": {"pct": 25}, "seven_day": {"pct": 82}, "ts": time.time()}
        cupo_json.write_text(json.dumps(datos), encoding="utf-8")
        # El archivo cupo.json gana sobre la CLI
        self.claude_falso(0, "Current session: 10% used\n")
        self.assertEqual(R.cupo_claude(), ("alto", "Claude: 82% usado"))

        # Si ts es viejo (> 900s), se ignora cupo.json y se ejecuta la CLI
        datos["ts"] = time.time() - 1000
        cupo_json.write_text(json.dumps(datos), encoding="utf-8")
        self.assertEqual(R.cupo_claude(), ("ok", "Claude: 10% usado"))

    def test_claude_salida_vacia_y_rota(self):
        self.claude_falso(0, "")
        self.assertEqual(R.cupo_claude(), ("desconocido", "Claude: cupo desconocido"))
        self.claude_falso(1, "error inesperado")
        self.assertEqual(R.cupo_claude(), ("desconocido", "Claude: cupo desconocido"))
        self.claude_falso(0, "salida no esperada")
        self.assertEqual(R.cupo_claude(), ("desconocido", "Claude: cupo desconocido"))
        os.environ["RADAR_CLAUDE_BIN"] = str(self.tmp / "inexistente")
        self.assertEqual(R.cupo_claude(), ("desconocido", "Claude: cupo desconocido"))

    def test_antigravity_salida_real(self):
        def json_agy(rem_gemini, rem_otros=0.01):
            return json.dumps({
                "command": {
                    "data": {
                        "groups": [
                            {"name": "Gemini 2.5 Pro", "buckets": [{"remaining_fraction": rem_gemini}]},
                            {"name": "Claude and GPT models", "buckets": [{"remaining_fraction": rem_otros}]}
                        ]
                    }
                }
            })
        # 100 * (1 - 0.8) = 20% -> ok (el grupo Claude and GPT se ignora)
        self.agy_falso(0, json_agy(0.80))
        self.assertEqual(R.cupo_antigravity(), ("ok", "Antigravity: 20% usado"))

        # 100 * (1 - 0.25) = 75% -> alto
        self.agy_falso(0, json_agy(0.25))
        self.assertEqual(R.cupo_antigravity(), ("alto", "Antigravity: 75% usado"))

        # 100 * (1 - 0.05) = 95% -> agotado
        self.agy_falso(0, json_agy(0.05))
        self.assertEqual(R.cupo_antigravity(), ("agotado", "Antigravity: 95% usado"))

    def test_antigravity_salida_vacia_y_rota(self):
        self.agy_falso(0, "")
        self.assertEqual(R.cupo_antigravity(), ("desconocido", "Antigravity: cupo desconocido"))
        self.agy_falso(1, "error interno")   # sin sesión iniciada o con error: el plan se salta
        self.assertEqual(R.cupo_antigravity()[0], "no_disponible")
        self.agy_falso(0, json.dumps({"status": "ERROR", "error": "no hay sesión"}))
        self.assertEqual(R.cupo_antigravity()[0], "no_disponible")
        self.agy_falso(0, "{esto no es json")
        self.assertEqual(R.cupo_antigravity(), ("desconocido", "Antigravity: cupo desconocido"))
        self.agy_falso(0, json.dumps({"command": {"data": {"groups": []}}}))
        self.assertEqual(R.cupo_antigravity(), ("desconocido", "Antigravity: cupo desconocido"))
        os.environ["RADAR_AGY_BIN"] = str(self.tmp / "inexistente")   # no instalada: el plan se salta
        self.assertEqual(R.cupo_antigravity(), ("no_disponible", "Antigravity: no está instalada"))

    def test_antigravity_sin_usar_no_se_ejecuta(self):
        """Sin su historial, `agy -p /usage` abriría el navegador para iniciar sesión: no se lo llama."""
        marca = self.tmp / "agy-fue-llamado"
        bin_dir = self.tmp / "bin"
        bin_dir.mkdir()
        agy = bin_dir / "agy"
        agy.write_text("#!/bin/sh\ntouch '%s'\ncat << 'EOF'\n%s\nEOF\n" % (marca, json.dumps(
            {"command": {"data": {"groups": [{"name": "Gemini", "buckets": [{"remaining_fraction": 0.5}]}]}}})), encoding="utf-8")
        agy.chmod(0o755)
        os.environ.pop("RADAR_AGY_BIN", None)
        os.environ["PATH"] = str(bin_dir) + os.pathsep + os.environ.get("PATH", "")
        estado = self.tmp / "agy-estado"
        estado.mkdir()
        os.environ["RADAR_AGY_STATE"] = str(estado)
        nivel, texto = R.cupo_antigravity()
        self.assertEqual(nivel, "no_disponible")
        self.assertIn("sin usar", texto)
        self.assertFalse(marca.exists(), "se llamó a agy sin historial")
        (estado / "history.jsonl").write_text("", encoding="utf-8")   # ya se usó: ahora sí se le pregunta
        self.assertEqual(R.cupo_antigravity(), ("ok", "Antigravity: 50% usado"))
        self.assertTrue(marca.exists())

    def test_codex_no_instalada_o_sin_sesion_se_salta(self):
        os.environ.pop("RADAR_CODEX_CUPO", None)
        os.environ["RADAR_CODEX_BIN"] = str(self.tmp / "codex-inexistente")
        self.assertEqual(R.cupo_codex(), ("no_disponible", "Codex: no está instalada"))
        falso = self.tmp / "codex-falso"
        falso.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        falso.chmod(0o755)
        os.environ["RADAR_CODEX_BIN"] = str(falso)
        os.environ["CODEX_HOME"] = str(self.tmp / "codex-home-vacio")
        nivel, texto = R.cupo_codex()
        self.assertEqual(nivel, "no_disponible")
        self.assertIn("codex login", texto)

    def test_motivo_salto_dice_por_que_no_esta_disponible(self):
        radar = radar_de_prueba()
        os.environ["RADAR_AGY_BIN"] = str(self.tmp / "inexistente")
        p = plan("X", "Antigravity", cupo="antigravity")
        m = R.motivo_salto(p, radar, False, {}, {})
        self.assertIn("no disponible", m)
        self.assertIn("no está instalada", m)


@unittest.skipIf(ES_WINDOWS, "scripts de sh")
class TestMotivoSaltoPorNivel(Base):
    def test_motivo_salto_niveles(self):
        radar = radar_de_prueba()
        for tipo, fn_falso, prefijo in (
            ("codex", lambda cod, txt: self.cupo_falso(cod, txt), "Codex:"),
            ("claude", lambda cod, txt: self.claude_falso(cod, txt), "Claude:"),
            ("antigravity", lambda cod, txt: self.agy_falso(cod, txt), "Antigravity:"),
        ):
            p = plan("X", "Herramienta", cupo=tipo)

            # Nivel ok -> no salta
            if tipo == "codex":
                fn_falso(0, "%s 10%% usado" % prefijo)
            elif tipo == "claude":
                fn_falso(0, "Current session: 10% used\n")
            else:
                fn_falso(0, json.dumps({"command": {"data": {"groups": [{"name": "Gemini", "buckets": [{"remaining_fraction": 0.9}]}]}}}))
            cache = {}
            self.assertIsNone(R.motivo_salto(p, radar, False, {}, cache))
            self.assertEqual(cache[tipo][0], "ok")

            # Nivel alto -> NO salta (incluyendo claude)
            if tipo == "codex":
                fn_falso(1, "%s 75%% usado" % prefijo)
            elif tipo == "claude":
                fn_falso(0, "Current session: 75% used\n")
            else:
                fn_falso(0, json.dumps({"command": {"data": {"groups": [{"name": "Gemini", "buckets": [{"remaining_fraction": 0.25}]}]}}}))
            cache = {}
            self.assertIsNone(R.motivo_salto(p, radar, False, {}, cache))
            self.assertEqual(cache[tipo][0], "alto")

            # Nivel agotado -> SÍ salta con "cupo agotado (%s)"
            if tipo == "codex":
                fn_falso(2, "%s 95%% usado" % prefijo)
            elif tipo == "claude":
                fn_falso(0, "Current session: 95% used\n")
            else:
                fn_falso(0, json.dumps({"command": {"data": {"groups": [{"name": "Gemini", "buckets": [{"remaining_fraction": 0.05}]}]}}}))
            cache = {}
            m = R.motivo_salto(p, radar, False, {}, cache)
            self.assertIsNotNone(m)
            self.assertIn("cupo agotado", m)
            self.assertEqual(cache[tipo][0], "agotado")

            # Nivel desconocido -> no salta
            if tipo == "codex":
                fn_falso(0, "Codex: cupo desconocido")
            else:
                fn_falso(0, "")
            cache = {}
            self.assertIsNone(R.motivo_salto(p, radar, False, {}, cache))
            self.assertEqual(cache[tipo][0], "desconocido")


@unittest.skipIf(ES_WINDOWS, "scripts de sh")
class TestElegirDelegar(Base):
    def setUp(self):
        super().setUp()
        self.cat = {
            "id": "programar",
            "nombre": "Programar",
            "planes": [
                plan("A", "Claude Code", "m-a", True, "claude"),
                plan("B", "Codex", "m-b", True, "codex"),
                plan("C", "Antigravity", "m-c", True, "antigravity"),
            ]
        }
        self.radar = {"actualizado": "2026-10-05", "categorias": [self.cat], "retiros": []}
        self.claude_falso(0, "Current session: 10% used\n")
        self.cupo_falso(0, "Codex: 10% del cupo — OK")
        self.agy_falso(0, json.dumps({"command": {"data": {"groups": [{"name": "Gemini", "buckets": [{"remaining_fraction": 0.9}]}]}}}))

    def test_delegar_false_mantiene_orden_original(self):
        p, saltados, _ = R.elegir(self.radar, self.cat, delegar=False)
        self.assertEqual(p["plan"], "A")
        self.assertEqual(p["herramienta"], "Claude Code")
        self.assertEqual(saltados, [])

    def test_delegar_true_antepone_no_claude_y_pospone_claude(self):
        # Con delegar=True, B (Codex) va antes que A (Claude Code)
        p, saltados, _ = R.elegir(self.radar, self.cat, delegar=True)
        self.assertEqual(p["plan"], "B")
        self.assertEqual(p["herramienta"], "Codex")
        self.assertEqual(saltados, [])

        # Si B está agotado, pasa a C (Antigravity)
        self.cupo_falso(2, "Codex: 95% — NO lanzar")
        p, saltados, _ = R.elegir(self.radar, self.cat, delegar=True)
        self.assertEqual(p["plan"], "C")
        self.assertEqual(p["herramienta"], "Antigravity")
        self.assertEqual(len(saltados), 1)
        self.assertEqual(saltados[0][0]["plan"], "B")

        # Si B y C están agotados, cae en A (Claude Code)
        self.agy_falso(0, json.dumps({"command": {"data": {"groups": [{"name": "Gemini", "buckets": [{"remaining_fraction": 0.02}]}]}}}))
        p, saltados, _ = R.elegir(self.radar, self.cat, delegar=True)
        self.assertEqual(p["plan"], "A")
        self.assertEqual(p["herramienta"], "Claude Code")
        self.assertEqual(len(saltados), 2)
        self.assertEqual([s[0]["plan"] for s in saltados], ["B", "C"])

    def test_cmd_elegir_delegar_y_aviso_alto(self):
        cache_dir = self.tmp / "config" / "metodo" / "radar"
        cache_dir.mkdir(parents=True, exist_ok=True)
        (cache_dir / "RADAR.yaml").write_text(R.yaml_volcar(self.radar), encoding="utf-8")

        # Sin --delegar: elige Plan A
        cod, out = self.correr("elegir", "programar")
        self.assertEqual(cod, 0)
        self.assertIn("plan A", out)

        # Con --delegar: elige Plan B (Codex)
        cod, out = self.correr("elegir", "programar", "--delegar")
        self.assertEqual(cod, 0)
        self.assertIn("plan B", out)

        # Aviso con nivel "alto" generalizado (para cualquier cupo, p. ej. Codex en alto)
        self.cupo_falso(1, "Codex: 78% del cupo mensual — ALTO")
        cod, out = self.correr("elegir", "programar", "--delegar")
        self.assertEqual(cod, 0)
        self.assertIn("plan B", out)
        self.assertIn("Ojo: Codex: 78%", out)
        self.assertIn("solo tareas chicas", out)

        # Aviso con nivel "alto" para Claude cuando se elige Plan A
        self.claude_falso(0, "Current session: 74% used\n")
        cod, out = self.correr("elegir", "programar")
        self.assertEqual(cod, 0)
        self.assertIn("plan A", out)
        self.assertIn("Ojo: Claude: 74% usado", out)
        self.assertIn("solo tareas chicas", out)


class TestDatosReales(Base):
    def test_el_radar_empaquetado_tiene_las_14_categorias_con_a_b_c(self):
        radar = R.leer_yaml(YAML_REAL)
        ids = [c["id"] for c in radar["categorias"]]
        self.assertEqual(len(ids), 14)
        for esperado in ("desarrollo", "revision", "diseno", "escritura", "investigacion_web", "documentos_largos",
                         "imagenes_generar", "imagenes_entender", "video", "transcripcion", "voz_tts", "datos_planillas",
                         "tareas_baratas", "agentes_largos"):
            self.assertIn(esperado, ids)
        for c in radar["categorias"]:
            self.assertEqual([p["plan"] for p in c["planes"]], ["A", "B", "C"], c["id"])
            for p in c["planes"]:
                for campo in ("herramienta", "proveedor", "por_que", "fuente", "fecha", "como_ver_cupo", "verificado"):
                    self.assertIn(campo, p, "%s %s" % (c["id"], p["plan"]))
                self.assertIsInstance(p["verificado"], bool)
        self.assertTrue(radar["retiros"])
        self.assertTrue(any(not p["verificado"] for c in radar["categorias"] for p in c["planes"]))

    def test_yaml_ida_y_vuelta(self):
        radar = R.leer_yaml(YAML_REAL)
        self.assertEqual(R.yaml_cargar(R.yaml_volcar(radar)), radar)

    def test_yaml_casos_borde(self):
        d = {"a": "x: y", "b": "- no", "c": "#no", "d": "true", "e": "10", "f": None, "g": [], "h": {}, "i": [1, "dos", {"k": "v"}],
             "j": "con \"comillas\" y ñ", "k": "2026-10-03", "l": 0.5, "m": ["a, b"], "n": [{"x": 1, "y": [{"z": "w"}]}]}
        self.assertEqual(R.yaml_cargar(R.yaml_volcar(d)), d)
        self.assertEqual(R.yaml_cargar("a: [1, 2, 'x']  # comentario\nb: http://u.rl/p#frag\n"), {"a": [1, 2, "x"], "b": "http://u.rl/p#frag"})

    def test_sin_clientes_ni_rutas_privadas(self):
        patron = re.compile("(?i)" + "eb" + "ras|\\b" + "da" + "ni\\b|/Us" + "ers/")
        for ruta in (YAML_REAL, YAML_REAL.with_name("RADAR.md"), RADAR_PY, FUENTES_PY, WORKFLOW, AQUI / "test_radar.py",
                     PLUGIN / "skills" / "radar" / "SKILL.md"):
            self.assertIsNone(patron.search(ruta.read_text(encoding="utf-8")), str(ruta))


class TestComandos(Base):
    def test_ver_y_elegir_con_datos_reales(self):
        codigo, salida = self.correr("ver")
        self.assertEqual(codigo, 0)
        self.assertIn("desarrollo", salida)
        codigo, salida = self.correr("ver", "revisión")
        self.assertEqual(codigo, 0)
        self.assertIn("datos privados", salida)
        codigo, salida = self.correr("elegir", "inexistente")
        self.assertEqual(codigo, 2)
        codigo, salida = self.correr("elegir", "desarrollo", "--sensible")
        self.assertEqual(codigo, 0)
        self.assertIn("plan A", salida)

    def test_json_valido(self):
        destino = self.tmp / "radar.json"
        codigo, _ = self.correr("json", "--salida", str(destino))
        self.assertEqual(codigo, 0)
        datos = json.loads(destino.read_text(encoding="utf-8"))
        self.assertEqual(len(datos["categorias"]), 14)
        self.assertEqual(len(datos["categorias"][0]["planes"]), 3)
        for k in ("actualizado", "retiros", "avisos"):
            self.assertIn(k, datos)
        codigo, salida = self.correr("json", "--stdout")
        self.assertEqual(json.loads(salida)["actualizado"], datos["actualizado"])

    def test_html_y_md(self):
        codigo, _ = self.correr("html", "--salida", str(self.tmp / "r.html"))
        self.assertEqual(codigo, 0)
        self.assertIn("<h1>Radar de modelos</h1>", (self.tmp / "r.html").read_text(encoding="utf-8"))
        self.correr("md", "--salida", str(self.tmp / "r.md"))
        self.assertIn("## Retiros", (self.tmp / "r.md").read_text(encoding="utf-8"))

    def test_aviso_viejo_y_retiro_proximo(self):
        radar = radar_de_prueba(actualizado="2026-09-01",
                                retiros=[{"modelo": "modelo-b", "fecha": "2026-11-01", "tipo": "apagado"}])
        linea = R.aviso_linea(radar)
        self.assertIn("39 días", linea)
        self.assertIn("modelo-b", linea)
        radar = radar_de_prueba(actualizado="2026-10-09")
        self.assertEqual(R.aviso_linea(radar), "")

    def test_aviso_no_envejece_si_actualizar_confirmo(self):
        radar = radar_de_prueba(actualizado="2026-09-01")
        self.assertIn("días", R.aviso_linea(radar))
        ok, _ = R.actualizar(lambda url, *a, **k: (200, YAML_REAL.read_bytes()))
        self.assertTrue(ok)
        linea = R.aviso_linea(radar)
        self.assertNotIn("corré", linea)
        # pero si los datos publicados no se mueven hace más de un mes, igual avisa
        self.assertIn("no cambian hace 39 días", linea)
        self.assertEqual(R.aviso_linea(radar_de_prueba(actualizado="2026-09-20")), "")

    def test_fabricante_no_cuenta_para_el_orden(self):
        c = {"evidencia": [{"fuente": "blog propio", "tipo": "fabricante"},
                           {"fuente": "ranking A", "tipo": "independiente"}]}
        self.assertEqual(R.respaldo(c), (1, False))
        self.assertIn("PROVISORIO", R.texto_respaldo(c))
        c["evidencia"].append({"fuente": "ranking B", "tipo": "independiente"})
        c["planes"] = [{"plan": "A", "respaldo": ["ranking A"]}, {"plan": "B", "respaldo": ["blog propio"]}]
        self.assertEqual(R.respaldo(c), (2, False))   # B se apoya solo en el fabricante
        c["planes"][1]["respaldo"] = ["ranking B"]
        self.assertEqual(R.respaldo(c), (2, True))
        self.assertEqual(R.respaldo({}), (0, False))

    def test_aviso_nunca_falla(self):
        carpeta = self.tmp / "config" / "metodo" / "radar"
        carpeta.mkdir(parents=True)
        (carpeta / "RADAR.yaml").write_text("esto: [no es\n  yaml: : :", encoding="utf-8")
        codigo, _ = self.correr("aviso")
        self.assertEqual(codigo, 0)

    def test_por_consola_como_lo_corre_la_skill(self):
        env = dict(os.environ)
        for args, esperado in ((["ver"], 0), (["elegir", "escritura"], 0), (["aviso"], 0), (["elegir", "zzz"], 2)):
            r = subprocess.run([sys.executable, str(RADAR_PY)] + args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
            self.assertEqual(r.returncode, esperado, (args, r.stderr.decode()))


class TestRedSimulada(Base):
    def test_sin_red_usa_la_cache(self):
        def sin_red(*a, **k):
            raise urllib.error.URLError("sin red")
        ok, msg = R.actualizar(sin_red)
        self.assertFalse(ok)
        self.assertIn("lo último guardado", msg)
        # la caché más nueva que el plugin gana; sin red sigue sirviendo
        cache = self.tmp / "config" / "metodo" / "radar"
        cache.mkdir(parents=True)
        nuevo = R.leer_yaml(YAML_REAL)
        nuevo["actualizado"] = "2030-01-01"
        nuevo["nota"] = "de la caché"
        (cache / "RADAR.yaml").write_text(R.yaml_volcar(nuevo), encoding="utf-8")
        radar, origen = R.cargar()
        self.assertEqual((origen, radar["nota"]), ("caché", "de la caché"))
        self.assertFalse(R.actualizar(sin_red)[0])
        self.assertEqual(R.cargar()[1], "caché")

    def test_cache_vieja_no_pisa_al_plugin(self):
        cache = self.tmp / "config" / "metodo" / "radar"
        cache.mkdir(parents=True)
        viejo = R.leer_yaml(YAML_REAL)
        viejo["actualizado"] = "2020-01-01"
        (cache / "RADAR.yaml").write_text(R.yaml_volcar(viejo), encoding="utf-8")
        self.assertEqual(R.cargar()[1], "plugin")

    def test_actualizar_guarda_lo_bajado_y_rechaza_basura(self):
        texto = YAML_REAL.read_bytes()
        ok, _ = R.actualizar(lambda url, *a, **k: (200, texto))
        self.assertTrue(ok)
        self.assertTrue((self.tmp / "config" / "metodo" / "radar" / "RADAR.yaml").exists())
        ok, _ = R.actualizar(lambda url, *a, **k: (200, b"<html>no es yaml</html>"))
        self.assertFalse(ok)

    def test_probar_marca_lo_que_no_esta_sin_imprimir_la_clave(self):
        clave = "clave-falsa-" + "Z" * 20
        os.environ["GEMINI_API_KEY"] = clave
        os.environ["ANTHROPIC_API_KEY"] = clave
        os.environ.pop("OPENAI_API_KEY", None)

        def falso(url, cabeceras=None, datos=None, timeout=0):
            if "anthropic" in url:
                return 200, json.dumps({"data": [{"id": "claude-opus-5-5"}]}).encode()
            if "countTokens" in url:
                raise urllib.error.HTTPError(url, 404, "no longer available to new users", {}, None)
            return 200, json.dumps({"models": [{"name": "models/gemini-3.8-flash"}, {"name": "models/gemini-3.1-pro-preview"}]}).encode()
        radar = R.leer_yaml(YAML_REAL)
        res = R.probar(radar, falso)
        self.assertTrue(res["claude-opus-5-5"]["disponible"])
        self.assertFalse(res["claude-sonnet-5-5"]["disponible"])
        self.assertFalse(res["gemini-3.8-flash"]["disponible"])
        self.assertIn("cuentas nuevas", res["gemini-3.8-flash"]["motivo"])
        self.assertNotIn("gpt-6-luna", res)  # sin clave de OpenAI no se prueba
        self.assertNotIn(clave, json.dumps(res))

    def test_probar_esta_apagado_por_defecto(self):
        antes = R.probar
        R.probar = lambda *a, **k: self.fail("no debería correr")
        try:
            codigo, salida = self.correr("probar")
        finally:
            R.probar = antes
        self.assertEqual(codigo, 0)
        self.assertIn("apagada por defecto", salida)
        self.assertFalse((self.tmp / "config" / "metodo" / "radar-probe.json").exists())

    def test_la_prueba_guardada_hace_saltar_el_plan(self):
        (self.tmp / "config" / "metodo").mkdir(parents=True)
        (self.tmp / "config" / "metodo" / "radar-probe.json").write_text(json.dumps(
            {"claude-opus-5-5": {"disponible": False, "motivo": "prueba", "fecha": "2026-10-09"}}), encoding="utf-8")
        codigo, salida = self.correr("elegir", "escritura")
        self.assertEqual(codigo, 0)
        self.assertIn("Saltó", salida)
        self.assertIn("plan B", salida)


class TestFuentes(Base):
    def fuentes(self, **k):
        d = {"litellm": {}, "openrouter": {}, "modelsdev": {}, "arena": {}, "paginas": {}}
        d.update(k)
        return d

    def test_sin_novedades_no_cambia_nada(self):
        radar = radar_de_prueba()
        nuevo, motivos = FU.analizar(radar, self.fuentes(
            litellm={"modelo-c": {"retiro": None, "entrada": 10.5, "salida": 52}},
            arena={"desarrollo": [("viejo", 5), ("otro", 4)]}, paginas={"anthropic": "abc"}))
        self.assertEqual(motivos, [])
        self.assertIs(nuevo, radar)

    def test_cambia_el_numero_uno(self):
        nuevo, motivos = FU.analizar(radar_de_prueba(), self.fuentes(arena={"desarrollo": [("nuevo", 9), ("viejo", 8)]}))
        self.assertEqual(len(motivos), 1)
        self.assertIn("viejo → nuevo", motivos[0])
        self.assertEqual(nuevo["categorias"][0]["ranking"]["items"][0]["modelo"], "nuevo")
        self.assertNotEqual(nuevo["actualizado"], "2026-09-01")

    def test_retiro_de_un_modelo_nombrado_y_no_de_otros(self):
        nuevo, motivos = FU.analizar(radar_de_prueba(), self.fuentes(openrouter={
            "modelo-b": {"retiro": "2026-12-31", "entrada": None, "salida": None},
            "modelo-ajeno": {"retiro": "2026-11-01", "entrada": None, "salida": None}}))
        self.assertEqual(len(motivos), 1)
        self.assertIn("modelo-b", motivos[0])
        self.assertEqual([r["modelo"] for r in nuevo["retiros"]], ["modelo-b"])

    def test_precio_sube_mas_del_20_por_ciento(self):
        _, motivos = FU.analizar(radar_de_prueba(), self.fuentes(litellm={"modelo-c": {"retiro": None, "entrada": 13, "salida": 50}}))
        self.assertEqual(len(motivos), 1)
        self.assertIn("20%", motivos[0])
        _, motivos = FU.analizar(radar_de_prueba(), self.fuentes(litellm={"modelo-c": {"retiro": None, "entrada": 11.9, "salida": 40}}))
        self.assertEqual(motivos, [])

    def test_no_antes_pasa_a_apagado_cuando_se_anuncia(self):
        radar = radar_de_prueba(retiros=[{"modelo": "modelo-c", "fecha": "2026-10-15", "tipo": "no_antes"}])
        nuevo, motivos = FU.analizar(radar, self.fuentes(litellm={"modelo-c": {"retiro": "2026-12-01", "entrada": None, "salida": None}}))
        self.assertTrue(any("apagado de modelo-c" in m for m in motivos), motivos)
        r = next(r for r in nuevo["retiros"] if r["modelo"] == "modelo-c")
        self.assertEqual((r["tipo"], r["fecha"]), ("apagado", "2026-12-01"))

    def test_cambio_en_la_tabla_de_retiros(self):
        nuevo, motivos = FU.analizar(radar_de_prueba(), self.fuentes(paginas={"anthropic": "otro"}))
        self.assertEqual(len(motivos), 1)
        self.assertEqual(nuevo["fuentes_auto"]["paginas_retiros"]["anthropic"]["hash"], "otro")

    def test_lectores(self):
        lite = FU.leer_litellm({"anthropic/m1": {"deprecation_date": "2026-11-30", "input_cost_per_token": 2e-6, "output_cost_per_token": 1e-5},
                                "m2": {"input_cost_per_token": 1e-7}, "roto": 5})
        self.assertEqual(lite["m1"], {"retiro": "2026-11-30", "entrada": 2.0, "salida": 10.0})
        self.assertIsNone(lite["m2"]["retiro"])
        orr = FU.leer_openrouter({"data": [{"id": "x/m3", "expiration_date": "2026-12-01", "pricing": {"prompt": "0.000001", "completion": "0.000002"}}]})
        self.assertEqual(orr["m3"]["retiro"], "2026-12-01")
        arena = FU.leer_arena({"rows": [{"row": {"model_name": "a", "rating": 1500}}, {"row": {"model_name": "b", "rating": 1600}},
                                         {"row": {"model_name": "c", "rating": 1400, "cat": "z"}}]})
        self.assertEqual(arena[0], ("b", 1600))
        self.assertEqual(FU.leer_arena({"rows": [{"row": {"model_name": "c", "rating": 1, "cat": "z"}}]}, {"cat": "q"}), [])
        t = "<table><tr><td>a</td></tr></table>"
        self.assertEqual(FU.hash_tablas("<p>x</p>" + t), FU.hash_tablas(t + "<p>otro</p>"))
        self.assertIsNone(FU.hash_tablas("<p>sin tablas</p>"))

    def test_una_fuente_caida_no_frena_el_resto(self):
        radar = radar_de_prueba(fuentes_auto={"litellm": "https://a", "openrouter": "https://b", "paginas_retiros": {}})
        avisos = []

        def traer(url, como="json"):
            if "a" == url[-1]:
                raise OSError("caída")
            return {"data": [{"id": "x/modelo-b", "expiration_date": "2026-12-31"}]}
        f = FU.juntar(radar, "diario", traer, avisos.append)
        self.assertEqual(len(avisos), 1)
        self.assertIn("modelo-b", f["openrouter"])

    def test_programa_principal_escribe_solo_ante_cambio_relevante(self):
        yaml_tmp = self.tmp / "RADAR.yaml"
        yaml_tmp.write_text("# cabecera\n" + R.yaml_volcar(radar_de_prueba()) + "\n", encoding="utf-8")
        motivo = self.tmp / "motivo.md"
        salida_gh = self.tmp / "gh_output"
        os.environ["GITHUB_OUTPUT"] = str(salida_gh)
        FU.traer, original = (lambda url, como="json": {"rows": [{"row": {"model_name": "viejo", "rating": 5}}]}), FU.traer
        try:
            radar = R.leer_yaml(yaml_tmp)
            radar["categorias"][0]["arena"] = {"config": "text", "split": "latest"}
            radar["fuentes_auto"]["arena"] = "https://x/rows?a=b"
            yaml_tmp.write_text("# cabecera\n" + R.yaml_volcar(radar) + "\n", encoding="utf-8")
            antes = yaml_tmp.read_text(encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()) as out:
                FU.main(["--modo", "semanal", "--yaml", str(yaml_tmp), "--motivo", str(motivo)])
            self.assertIn("Sin cambios relevantes", out.getvalue())
            self.assertEqual(yaml_tmp.read_text(encoding="utf-8"), antes)
            self.assertFalse(motivo.exists())
            self.assertFalse(salida_gh.exists())
            FU.traer = lambda url, como="json": {"rows": [{"row": {"model_name": "nuevo", "rating": 9}}]}
            with contextlib.redirect_stdout(io.StringIO()):
                FU.main(["--modo", "semanal", "--yaml", str(yaml_tmp), "--motivo", str(motivo)])
            self.assertTrue(yaml_tmp.read_text(encoding="utf-8").startswith("# cabecera"))
            self.assertEqual(R.leer_yaml(yaml_tmp)["categorias"][0]["ranking"]["items"][0]["modelo"], "nuevo")
            self.assertIn("nuevo", motivo.read_text(encoding="utf-8"))
            self.assertIn("hay_cambios=true", salida_gh.read_text())
            self.assertTrue((self.tmp / "RADAR.md").exists())
        finally:
            FU.traer = original


class TestWorkflow(unittest.TestCase):
    def setUp(self):
        self.texto = WORKFLOW.read_text(encoding="utf-8")

    def test_acciones_fijadas_por_sha(self):
        usos = re.findall(r"^\s*-?\s*uses:\s*(\S+)", self.texto, re.M)
        self.assertTrue(usos)
        for u in usos:
            self.assertRegex(u, r"@[0-9a-f]{40}$", u)

    def test_permisos_minimos(self):
        bloque = re.search(r"^permissions:\n((?:[ ]+\S.*\n)+)", self.texto, re.M).group(1)
        permisos = dict(re.findall(r"^\s+([\w-]+):\s*(\w+)", bloque, re.M))
        self.assertEqual(permisos, {"contents": "write", "pull-requests": "write"})

    def test_sin_claves_ni_secretos_propios_y_publica_solo_con_guardias(self):
        # Decisión del dueño 2026-10-03: se publica solo, pero únicamente si pasan las guardias.
        self.assertNotRegex(self.texto, r"secrets\.(?!GITHUB_TOKEN)")
        self.assertNotIn("--auto", self.texto)
        self.assertIn("persist-credentials: false", self.texto)  # la credencial no está mientras se leen terceros
        self.assertIn("RADAR\\.(yaml|md)", self.texto)  # guardia: solo datos del radar
        self.assertIn("antes / 2", self.texto)  # guardia: no borra más de la mitad
        merge = self.texto.index("gh pr merge")
        self.assertLess(self.texto.index('if [ "$publicar" = si ]'), merge)  # solo publica con las guardias en verde
        self.assertLess(self.texto.index("unittest discover"), merge)  # y después de los tests
        self.assertIn("hay_cambios == 'true'", self.texto)  # el PR solo se arma ante un cambio relevante
        self.assertIn("43 6 * * 1", self.texto)  # semanal
        self.assertIn("17 6 * * *", self.texto)  # diario


if __name__ == "__main__":
    unittest.main()
