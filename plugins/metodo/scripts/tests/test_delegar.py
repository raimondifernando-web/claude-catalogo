"""Tests de delegar.py (plugin metodo). Solo biblioteca estándar, SIN red ni CLIs reales.

Correr desde la raíz del repo:
    python3 -m unittest discover -s plugins/metodo/scripts/tests -v
"""
import contextlib
import importlib.util
import io
import json
import os
import shutil
import signal
import threading
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

AQUI = Path(__file__).resolve().parent
SCRIPTS = AQUI.parent
DELEGAR_PY = SCRIPTS / "delegar.py"
RADAR_PY = SCRIPTS / "radar.py"
ES_WINDOWS = os.name == "nt"


def cargar_modulo(nombre, ruta):
    spec = importlib.util.spec_from_file_location(nombre, str(ruta))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[nombre] = mod
    spec.loader.exec_module(mod)
    return mod


R = cargar_modulo("radar", RADAR_PY)
D = cargar_modulo("delegar", DELEGAR_PY)


# Lo que lista hoy `agy models` (2026-10-13): no hay ningún Gemini Pro. FAKE_AGY_MODELOS la cambia; «falla» = exit 1.
MODELOS_AGY = ("gemini-3.8-flash-high\ngemini-3.8-flash-medium\ngemini-3.8-flash-low\nclaude-opus-5-5-high\n"
               "claude-sonnet-5-5-high\ngpt-oss-120b-medium\n")
RESPUESTA_MODELOS = (
    "if len(sys.argv) > 1 and sys.argv[1] == 'models':\n"
    "    import os\n"
    "    if os.environ.get('FAKE_AGY_MODELOS_MARCA'):\n"
    "        open(os.environ['FAKE_AGY_MODELOS_MARCA'], 'w').write('x')\n"
    "    m = os.environ.get('FAKE_AGY_MODELOS', %r)\n"
    "    if m == 'falla':\n"
    "        sys.exit(1)\n"
    "    sys.stdout.write(m); sys.exit(0)\n" % MODELOS_AGY)
INFORME_LARGO = "Informe: " + "revisé el código y no encontré problemas graves en esta parte. " * 5


def plan(letra, herramienta="Claude Code", api=None, privados=True, cupo=None, **extra):
    d = {
        "plan": letra,
        "herramienta": herramienta,
        "proveedor": "ProveedorX",
        "modelo": "m" + letra,
        "modelo_api": api,
        "por_que": "porque " + letra,
        "datos_privados": privados,
        "cupo": cupo,
        "verificado": True,
    }
    d.update(extra)
    return d


def radar_de_prueba(**extra):
    r = {
        "actualizado": "2099-01-01",
        "categorias": [
            {
                "id": "desarrollo",
                "nombre": "Desarrollo",
                "planes": [
                    plan("A", "Claude Code", "claude-opus-5-5", True, "claude"),
                    plan("B", "Codex", "gpt-6.1-sol", True, "codex"),
                    plan("C", "Antigravity", "gemini-3.8-flash", False, "antigravity"),
                ],
            },
            {
                "id": "revision",
                "nombre": "Revisión",
                "planes": [
                    plan("A", "Claude Code", "claude-opus-5-5", True, "claude"),
                    plan("B", "Codex", "gpt-6.1-sol", True, "codex"),
                ],
            },
        ],
        "retiros": [],
    }
    r.update(extra)
    return r


class BaseDelegar(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="delegar-test-")).resolve()
        self.addCleanup(shutil.rmtree, str(self.tmp), True)
        self.env_previo = dict(os.environ)
        self.addCleanup(self._restaurar)

        os.environ["CLAUDE_CONFIG_DIR"] = str(self.tmp / "config")
        self.aceptar_envio()
        os.environ["RADAR_HOY"] = "2026-10-10"
        os.environ.pop("RADAR_PROBAR", None)
        os.environ["CEREBRO_HOME"] = str(self.tmp / "cerebro")
        os.environ.pop("METODO_NO_DELEGAR", None)
        os.environ["METODO_AGY_TRABAJO"] = str(self.tmp / "agy-trabajo")   # nunca la carpeta real (~/.cache)
        # nunca la configuración real de Antigravity de esta computadora (~/.gemini): una carpeta personal falsa
        self.casa_real = Path.home().resolve()
        (self.tmp / "casa-de-prueba").mkdir()
        os.environ["HOME"] = str(self.tmp / "casa-de-prueba")
        os.environ.pop("METODO_AGY_SIN_AVISO_REGLAS", None)

        # Escribir radar en la caché del perfil para que radar.cargar() use nuestros datos de prueba
        self.radar = radar_de_prueba()
        cache_dir = self.tmp / "config" / "metodo" / "radar"
        cache_dir.mkdir(parents=True, exist_ok=True)
        (cache_dir / "RADAR.yaml").write_text(R.yaml_volcar(self.radar), encoding="utf-8")

        # Cupos iniciales: todos disponibles (ok)
        self.cupo_codex_falso(0, "Codex: 10% del cupo mensual — OK")
        self.set_cupo_claude(10)
        self.agy_rem_fraction = 0.90

        # CLIs falsas por defecto
        self.codex_falso()
        self.agy_falso()

    def _restaurar(self):
        os.environ.clear()
        os.environ.update(self.env_previo)

    def cupo_codex_falso(self, codigo=0, texto="Codex: 10% del cupo mensual — OK"):
        ruta = self.tmp / "codex-cupo-falso"
        ruta.write_text("#!/bin/bash\necho '%s'\nexit %d\n" % (texto, codigo), encoding="utf-8")
        ruta.chmod(0o755)
        os.environ["RADAR_CODEX_CUPO"] = str(ruta)
        return ruta

    def set_cupo_claude(self, pct=10):
        cerebro = self.tmp / "cerebro"
        cerebro.mkdir(parents=True, exist_ok=True)
        datos = {"five_hour": {"pct": pct}, "seven_day": {"pct": pct}, "ts": time.time()}
        (cerebro / "cupo.json").write_text(json.dumps(datos), encoding="utf-8")

    def aceptar_envio(self):
        ruta = self.tmp / "config" / "metodo" / "delegar-aceptado.json"
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text('{"aceptado": true}', encoding="utf-8")

    def codex_falso(self, codigo=0, salida=""):
        ruta = self.tmp / "codex-falso"
        args_file = self.tmp / "codex_args.json"
        stdin_file = self.tmp / "codex_stdin.txt"
        contenido = (
            "#!/usr/bin/env python3\n"
            "import sys, json\n"
            "with open(%r, 'w', encoding='utf-8') as f:\n"
            "    json.dump(sys.argv[1:], f)\n"
            "with open(%r, 'w', encoding='utf-8') as f:\n"
            "    f.write(sys.stdin.read())\n"
            "if %r:\n"
            "    sys.stdout.write(%r)\n"
            "sys.exit(%d)\n"
        ) % (str(args_file), str(stdin_file), bool(salida), salida, codigo)
        ruta.write_text(contenido, encoding="utf-8")
        ruta.chmod(0o755)
        os.environ["RADAR_CODEX_BIN"] = str(ruta)
        return ruta

    def agy_falso(self, codigo=0, salida="", rem_fraction=None):
        if rem_fraction is not None:
            self.agy_rem_fraction = rem_fraction
        ruta = self.tmp / "agy-falso"
        args_file = self.tmp / "agy_args.json"
        stdin_file = self.tmp / "agy_stdin.txt"
        frac = getattr(self, "agy_rem_fraction", 0.90)
        contenido = (
            "#!/usr/bin/env python3\n"
            "import sys, json\n"
            "import os\n"
            "if '-p' in sys.argv and '/usage' in sys.argv and os.environ.get('FAKE_AGY_USAGE') == 'roto':\n"
            "    sys.stdout.write('sin datos'); sys.exit(0)\n"
            "if '-p' in sys.argv and '/usage' in sys.argv:\n"
            "    sys.stdout.write(json.dumps({\n"
            "        'command': {'data': {'groups': [{'name': 'Gemini', 'buckets': [{'remaining_fraction': %f}]}]}}\n"
            "    }))\n"
            "    sys.exit(0)\n"
            + RESPUESTA_MODELOS +
            "with open(%r, 'w', encoding='utf-8') as f:\n"
            "    json.dump(sys.argv[1:], f)\n"
            "with open(%r, 'w', encoding='utf-8') as f:\n"
            "    f.write(sys.stdin.read())\n"
            "if %r:\n"
            "    sys.stdout.write(%r)\n"
            "elif 'plan' in sys.argv:\n"
            "    sys.stdout.write(%r)\n"
            "sys.exit(%d)\n"
        ) % (frac, str(args_file), str(stdin_file), bool(salida), salida, INFORME_LARGO, codigo)
        ruta.write_text(contenido, encoding="utf-8")
        ruta.chmod(0o755)
        os.environ["RADAR_AGY_BIN"] = str(ruta)
        return ruta

    def crear_repo_git(self, nombre="repo", sucio=False):
        repo_dir = self.tmp / nombre
        repo_dir.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "init", str(repo_dir)], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        subprocess.run(["git", "-C", str(repo_dir), "config", "user.name", "Test"], check=True)
        subprocess.run(["git", "-C", str(repo_dir), "config", "user.email", "test@example.com"], check=True)
        subprocess.run(["git", "-C", str(repo_dir), "config", "commit.gpgsign", "false"], check=True)
        archivo = repo_dir / "README.md"
        archivo.write_text("linea 1\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(repo_dir), "add", "."], check=True)
        subprocess.run(["git", "-C", str(repo_dir), "commit", "-m", "init"], check=True)
        if sucio:
            archivo.write_text("linea 1 modificada\n", encoding="utf-8")
        return repo_dir

    def correr(self, *args):
        out = io.StringIO()
        err = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                codigo = D.main(list(args))
            except SystemExit as ex:
                codigo = ex.code
        return codigo, out.getvalue(), err.getvalue()


@unittest.skipIf(ES_WINDOWS, "scripts falsos de bash/sh")
class TestFallos(BaseDelegar):
    def test_herramienta_con_error_devuelve_70_y_no_su_codigo(self):
        self.codex_falso(codigo=3)   # 3 es el código reservado de «le toca a Claude»: no se puede devolver tal cual
        repo = self.crear_repo_git("repo-falla")
        cod, out, err = self.correr("desarrollo", str(repo), "hacé algo")
        self.assertEqual(cod, 70)
        self.assertIn("código 3", err)

    def test_pedido_ilegible_no_se_manda_como_texto(self):
        repo = self.crear_repo_git("repo-ilegible")
        pedido = self.tmp / "pedido-ilegible.txt"
        pedido.write_bytes(b"\xff\xfe\x00no es utf-8")
        cod, out, err = self.correr("desarrollo", str(repo), str(pedido), "--archivo")
        self.assertEqual(cod, 64)
        self.assertIn("no lo mando como texto", err)


@unittest.skipIf(ES_WINDOWS, "scripts falsos de bash/sh")
class TestAdaptadores(BaseDelegar):
    def test_adaptador_codex_argumentos_y_stdin(self):
        repo = self.crear_repo_git("repo-codex")
        cod, out, err = self.correr("desarrollo", str(repo), "arreglá el bug")
        self.assertEqual(cod, 0)
        self.assertIn("Plan elegido: Codex (ProveedorX, mB)", out)
        self.assertIn("── Cambios (revisalos y corré los tests) ──", out)
        self.assertIn("Todo al día ✓", out)

        args = json.loads((self.tmp / "codex_args.json").read_text(encoding="utf-8"))
        esperado = ["exec", "-C", str(repo), "--sandbox", "workspace-write", "-"]
        self.assertEqual(args, esperado)

        stdin = (self.tmp / "codex_stdin.txt").read_text(encoding="utf-8")
        self.assertEqual(stdin, "arreglá el bug")

    def test_adaptador_antigravity_argumentos(self):
        # Codex agotado -> elige Antigravity
        self.cupo_codex_falso(2, "Codex: 95% del cupo mensual — NO lanzar")
        repo = self.crear_repo_git("repo-agy")
        cod, out, err = self.correr("desarrollo", str(repo), "hacé una función")
        self.assertEqual(cod, 0)
        self.assertIn("Plan elegido: Antigravity (ProveedorX, mC)", out)
        self.assertIn("Gemini no cambió nada en su copia.", out)              # el agy falso no edita nada
        self.assertIn("Todo al día ✓", out)
        self.assertNotIn("reglas amplias", out)                                # no leyó la configuración real

        args = json.loads((self.tmp / "agy_args.json").read_text(encoding="utf-8"))
        # el id del radar + el esfuerzo, confirmado contra `agy models`: un solo --model, agy nunca elige
        self.assertEqual(args[0:2], ["--model", "gemini-3.8-flash-high"])
        self.assertNotIn("Modelo:", out)
        self.assertEqual(args[2:4], ["--mode", "accept-edits"])
        # trabaja sobre una copia aislada (en la carpeta de trabajo del método), nunca sobre el repo real
        self.assertEqual(args[4], "--add-dir")
        self.assertNotEqual(args[5], str(repo))
        self.assertTrue(args[5].startswith(str(self.tmp / "agy-trabajo") + os.sep), args[5])
        self.assertTrue(args[5].endswith(os.sep + "trab"))
        self.assertFalse(Path(args[5]).exists(), "la copia temporal se borra al terminar")
        self.assertEqual(args[6], "-p")
        esperado_prompt = (
            "Tarea: hacé una función\n\n"
            "Trabajás en una copia del repo (sin .git ni archivos de claves): leé y editá acá, con rutas relativas; "
            "no edites nada fuera de esta carpeta. NO corras ningún comando. "
            "Editá solo lo pedido. No toques archivos de claves ni de variables de entorno. "
            "Respondé en castellano, corto: qué hiciste o qué encontraste."
        )
        self.assertEqual(args[7], esperado_prompt)

    def test_adaptador_claude_code(self):
        # Codex y Antigravity agotados -> le toca a Claude Code
        self.cupo_codex_falso(2, "Codex: 95% del cupo mensual — NO lanzar")
        self.agy_falso(rem_fraction=0.02)  # 98% usado -> agotado
        repo = self.crear_repo_git("repo-claude")
        cod, out, err = self.correr("desarrollo", str(repo), "pensá la arquitectura")
        self.assertEqual(cod, 3)
        self.assertIn("Plan elegido: Claude Code (ProveedorX, mA)", out)
        self.assertIn("El plan elegido es Claude Code: hacelo en esta sesión (cupo disponible).", out)
        self.assertFalse((self.tmp / "codex_args.json").exists())
        self.assertFalse((self.tmp / "agy_args.json").exists())


@unittest.skipIf(ES_WINDOWS, "scripts falsos de bash/sh")
class TestDryRun(BaseDelegar):
    def test_dry_run_muestra_comando_y_no_ejecuta(self):
        repo = self.crear_repo_git("repo-dry")
        cod, out, err = self.correr("desarrollo", str(repo), "hacé tal cosa", "--dry-run")
        self.assertEqual(cod, 0)
        self.assertIn("Plan elegido: Codex (ProveedorX, mB)", out)
        self.assertIn("Comando:", out)
        self.assertIn("exec", out)
        self.assertIn("--sandbox workspace-write", out)
        # Asegurar que no ejecutó la CLI ni imprimió el resumen de cambios
        self.assertFalse((self.tmp / "codex_args.json").exists())
        self.assertNotIn("Todo al día ✓", out)


@unittest.skipIf(ES_WINDOWS, "scripts falsos de bash/sh")
class TestModeloYEsfuerzo(BaseDelegar):
    """--modelo / --esfuerzo: Codex recibe -m y -c model_reasoning_effort; Antigravity el id con el nivel. Todo con CLIs falsas."""

    def cache_codex(self):
        home = self.tmp / "codex-home"
        home.mkdir()
        (home / "auth.json").write_text("{}", encoding="utf-8")
        datos = {"models": [
            {"slug": "gpt-6-sol", "supported_reasoning_levels": [{"effort": "low"}, {"effort": "medium"}, {"effort": "high"}]},
            {"slug": "gpt-6-luna", "supported_reasoning_levels": [{"effort": "low"}, {"effort": "medium"}]},
        ]}
        (home / "models_cache.json").write_text(json.dumps(datos), encoding="utf-8")
        os.environ["CODEX_HOME"] = str(home)

    def args_codex(self):
        return json.loads((self.tmp / "codex_args.json").read_text(encoding="utf-8"))

    def test_sin_flags_codex_queda_igual(self):
        repo = self.crear_repo_git("repo-m0")
        self.assertEqual(self.correr("desarrollo", str(repo), "x")[0], 0)
        self.assertEqual(self.args_codex(), ["exec", "-C", str(repo), "--sandbox", "workspace-write", "-"])

    def test_codex_recibe_modelo_y_esfuerzo(self):
        self.cache_codex()
        repo = self.crear_repo_git("repo-m1")
        cod, out, err = self.correr("desarrollo", str(repo), "x", "--modelo", "gpt-6-sol", "--esfuerzo", "high")
        self.assertEqual(cod, 0, err)
        self.assertEqual(self.args_codex(), ["exec", "-m", "gpt-6-sol", "-c", 'model_reasoning_effort="high"',
                                             "-C", str(repo), "--sandbox", "workspace-write", "-"])

    def test_codex_modelo_inexistente_no_se_lanza_y_lista_los_que_hay(self):
        self.cache_codex()
        repo = self.crear_repo_git("repo-m2")
        cod, out, err = self.correr("desarrollo", str(repo), "x", "--modelo", "gpt-6.1-sol")
        self.assertEqual(cod, 64)
        self.assertIn("gpt-6-luna", err)
        self.assertFalse((self.tmp / "codex_args.json").exists())

    def test_codex_esfuerzo_que_el_modelo_no_admite(self):
        self.cache_codex()
        repo = self.crear_repo_git("repo-m3")
        cod, out, err = self.correr("desarrollo", str(repo), "x", "--modelo", "gpt-6-luna", "--esfuerzo", "max")
        self.assertEqual(cod, 64)
        self.assertIn("Admite: low, medium", err)

    def test_valores_con_forma_rara_se_rechazan(self):
        repo = self.crear_repo_git("repo-m4")
        self.assertEqual(self.correr("desarrollo", str(repo), "x", "--esfuerzo", "furioso")[0], 64)
        self.assertEqual(self.correr("desarrollo", str(repo), "x", "--modelo", "a b;rm -rf")[0], 64)
        self.assertFalse((self.tmp / "codex_args.json").exists())

    def test_dry_run_muestra_los_flags_sin_ejecutar(self):
        self.cache_codex()
        repo = self.crear_repo_git("repo-m5")
        cod, out, err = self.correr("desarrollo", str(repo), "x", "--modelo", "gpt-6-luna", "--esfuerzo", "low", "--dry-run")
        self.assertEqual(cod, 0)
        self.assertIn("-m gpt-6-luna", out)
        self.assertIn("model_reasoning_effort", out)
        self.assertFalse((self.tmp / "codex_args.json").exists())

    def test_antigravity_modelo_pedido_con_esfuerzo(self):
        self.cupo_codex_falso(2, "Codex: 95% del cupo mensual — NO lanzar")
        repo = self.crear_repo_git("repo-m6")
        cod, out, err = self.correr("desarrollo", str(repo), "x", "--modelo", "gemini-3.8-flash", "--esfuerzo", "medium")
        self.assertEqual(cod, 0, err)
        args = json.loads((self.tmp / "agy_args.json").read_text(encoding="utf-8"))
        self.assertEqual(args[0:2], ["--model", "gemini-3.8-flash-medium"])

    def test_antigravity_solo_esfuerzo_cambia_el_del_radar(self):
        self.cupo_codex_falso(2, "Codex: 95% del cupo mensual — NO lanzar")
        repo = self.crear_repo_git("repo-m7")
        self.assertEqual(self.correr("desarrollo", str(repo), "x", "--esfuerzo", "low")[0], 0)
        args = json.loads((self.tmp / "agy_args.json").read_text(encoding="utf-8"))
        self.assertEqual(args[0:2], ["--model", "gemini-3.8-flash-low"])

    def test_antigravity_modelo_inexistente_no_se_reemplaza(self):
        self.cupo_codex_falso(2, "Codex: 95% del cupo mensual — NO lanzar")
        repo = self.crear_repo_git("repo-m8")
        cod, out, err = self.correr("desarrollo", str(repo), "x", "--modelo", "gemini-9-inventado")
        self.assertEqual(cod, 64)
        self.assertIn("gemini-3.8-flash-high", err)          # muestra los que sí hay
        self.assertFalse((self.tmp / "agy_args.json").exists())


@unittest.skipIf(ES_WINDOWS, "scripts falsos de bash/sh")
class TestRevisar(BaseDelegar):
    def test_revisar_codex_sandbox_read_only_y_arbol_sucio_permitido(self):
        repo_sucio = self.crear_repo_git("repo-sucio-codex", sucio=True)
        cod, out, err = self.correr("desarrollo", str(repo_sucio), "analizá posibles bugs", "--revisar")
        self.assertEqual(cod, 0)
        self.assertIn("Plan elegido: Codex", out)
        self.assertNotIn("── Cambios (revisalos y corré los tests) ──", out)

        args = json.loads((self.tmp / "codex_args.json").read_text(encoding="utf-8"))
        esperado = ["exec", "-C", str(repo_sucio), "--sandbox", "read-only", "-"]
        self.assertEqual(args, esperado)

    def test_antigravity_que_pidio_login_no_se_lanza_75(self):
        """Con la marca «necesita login» (o sin red) delegar no ejecuta agy: sin sesión abriría el navegador de Google.
        Sin red el radar no sabe el cupo (no salta el plan) y la guarda de delegar corta con 75."""
        self.cupo_codex_falso(2, "Codex: 95% del cupo mensual — NO lanzar")
        repo = self.crear_repo_git("repo-agy-login", sucio=True)
        R.agy_marcar_login()   # el radar ya no lo ofrece: el plan se salta y, sin otro, le toca a Claude (3), con el motivo a la vista
        cod, out, err = self.correr("desarrollo", str(repo), "analizá seguridad", "--revisar")
        self.assertEqual(cod, 3)
        self.assertIn("en pausa", err + out)
        self.assertFalse((self.tmp / "agy_args.json").exists(), "se ejecutó agy con la marca puesta")
        R._marca_agy().unlink()
        os.environ["RADAR_AGY_RED"] = "no"
        cod, out, err = self.correr("desarrollo", str(repo), "analizá seguridad", "--revisar")
        self.assertEqual(cod, 75)
        self.assertIn("sin red", err + out)

    def test_revisar_antigravity_mode_plan(self):
        self.cupo_codex_falso(2, "Codex: 95% del cupo mensual — NO lanzar")
        repo_sucio = self.crear_repo_git("repo-sucio-agy", sucio=True)
        cod, out, err = self.correr("desarrollo", str(repo_sucio), "analizá seguridad", "--revisar")
        self.assertEqual(cod, 0)
        self.assertIn("Plan elegido: Antigravity", out)
        self.assertNotIn("── Cambios (revisalos y corré los tests) ──", out)

        args = json.loads((self.tmp / "agy_args.json").read_text(encoding="utf-8"))
        self.assertEqual(args[2:4], ["--mode", "plan"])
        esperado_prompt = (
            "Tarea: analizá seguridad\n\n"
            "Trabajás en una copia del repo (sin .git ni archivos de claves): leé y editá acá, con rutas relativas; "
            "no edites nada fuera de esta carpeta. NO corras ningún comando. "
            "Solo leé y analizá; no edites nada. Si el pedido ya trae todo lo que hay que revisar, no uses herramientas: "
            "respondé con el informe completo. "
            "Respondé en castellano, corto: qué hiciste o qué encontraste."
        )
        self.assertEqual(args[7], esperado_prompt)


@unittest.skipIf(ES_WINDOWS, "scripts falsos de bash/sh")
class TestArbolSucio(BaseDelegar):
    def test_arbol_sucio_al_editar_sale_con_66(self):
        repo_sucio = self.crear_repo_git("repo-sucio-editar", sucio=True)
        cod, out, err = self.correr("desarrollo", str(repo_sucio), "modificá cosas")
        self.assertEqual(cod, 66)
        self.assertIn("cambios sin confirmar", err)
        self.assertFalse((self.tmp / "codex_args.json").exists())


@unittest.skipIf(ES_WINDOWS, "scripts falsos de bash/sh")
class TestCarpetaPrivada(BaseDelegar):
    def test_carpetas_de_proyecto_ya_no_se_frenan_por_el_nombre(self):
        # Decisión de Fernando (2026-10-13): clientes/, Finanzas, Personal y cualquier carpeta de proyecto se delegan; las
        # claves y archivos de entorno quedan afuera igual (copia aislada en Antigravity, Codex se salta si los hay).
        for nombre in ("Personal", "Finanzas", "Consultoria-Negocio", "clientes"):
            repo = self.crear_repo_git("%s/mi-repo" % nombre)
            cod, out, err = self.correr("desarrollo", str(repo), "tarea")
            self.assertEqual(cod, 0, "Falló en carpeta %s: %s" % (nombre, err))
            self.assertTrue((self.tmp / "codex_args.json").exists())
            (self.tmp / "codex_args.json").unlink()

    def test_carpeta_privada_por_metodo_no_delegar(self):
        repo = self.crear_repo_git("repo-confidencial")
        os.environ["METODO_NO_DELEGAR"] = "/otra/ruta:" + str(repo)
        cod, out, err = self.correr("desarrollo", str(repo), "tarea")
        self.assertEqual(cod, 65)
        self.assertIn("No se delega en carpetas privadas", err)
        self.assertFalse((self.tmp / "codex_args.json").exists())


@unittest.skipIf(ES_WINDOWS, "scripts falsos de bash/sh")
class TestCliAusente(BaseDelegar):
    def test_cli_codex_ausente_sale_con_67(self):
        os.environ["RADAR_CODEX_BIN"] = str(self.tmp / "codex-inexistente")
        repo = self.crear_repo_git("repo-sin-codex")
        cod, out, err = self.correr("desarrollo", str(repo), "tarea")
        self.assertEqual(cod, 67)
        self.assertIn("no está instalada", err)

    def test_agy_no_instalada_se_salta_y_pasa_al_plan_siguiente(self):
        # Codex agotado y Antigravity sin instalar: ya no se elige una herramienta que va a fallar; queda Claude
        self.cupo_codex_falso(2, "Codex: 95% del cupo mensual — NO lanzar")
        os.environ["RADAR_AGY_BIN"] = str(self.tmp / "agy-inexistente")
        repo = self.crear_repo_git("repo-sin-agy")
        cod, out, err = self.correr("desarrollo", str(repo), "tarea")
        self.assertEqual(cod, 3)
        self.assertIn("no disponible", out)
        self.assertIn("no está instalada", out)

    def test_codex_sin_sesion_se_salta_y_se_elige_antigravity(self):
        os.environ.pop("RADAR_CODEX_CUPO", None)
        os.environ["CODEX_HOME"] = str(self.tmp / "codex-home-vacio")   # sin «codex login»
        repo = self.crear_repo_git("repo-codex-sin-sesion")
        cod, out, err = self.correr("desarrollo", str(repo), "tarea")
        self.assertEqual(cod, 0)
        self.assertIn("Plan elegido: Antigravity", out)
        self.assertIn("codex login", out)


@unittest.skipIf(ES_WINDOWS, "scripts falsos de bash/sh")
class TestErroresDeUsoYCategoria(BaseDelegar):
    def test_categoria_desconocida_sale_con_2(self):
        repo = self.crear_repo_git("repo-cat")
        cod, out, err = self.correr("categoria_inexistente", str(repo), "tarea")
        self.assertEqual(cod, 2)
        self.assertIn("No conozco la categoría «categoria_inexistente»", out)

    def test_sin_plan_disponible_sale_con_1(self):
        # Todos los cupos agotados
        self.cupo_codex_falso(2, "Codex: 95% del cupo mensual — NO lanzar")
        self.agy_falso(rem_fraction=0.02)  # 98% agotado
        self.set_cupo_claude(95)  # 95% agotado
        repo = self.crear_repo_git("repo-sin-plan")
        cod, out, err = self.correr("desarrollo", str(repo), "tarea")
        self.assertEqual(cod, 1)
        self.assertIn("Ningún plan disponible para «Desarrollo» ahora", out)

    def test_repo_no_git_sale_con_64(self):
        no_git = self.tmp / "no_es_git"
        no_git.mkdir(parents=True, exist_ok=True)
        cod, out, err = self.correr("desarrollo", str(no_git), "tarea")
        self.assertEqual(cod, 64)

    def test_argumentos_faltantes_sale_con_64(self):
        cod, out, err = self.correr("desarrollo")
        self.assertEqual(cod, 64)


@unittest.skipIf(ES_WINDOWS, "scripts falsos de bash/sh")
class TestCodexAgotadoEligeAntigravity(BaseDelegar):
    def test_con_codex_agotado_se_elige_antigravity(self):
        self.cupo_codex_falso(2, "Codex: 95% del cupo mensual — NO lanzar")
        repo = self.crear_repo_git("repo-codex-agotado")
        cod, out, err = self.correr("desarrollo", str(repo), "arreglá la función")
        self.assertEqual(cod, 0)
        self.assertIn("Plan elegido: Antigravity (ProveedorX, mC)", out)
        self.assertIn("saltó: B (Codex): cupo agotado", out)
        self.assertTrue((self.tmp / "agy_args.json").exists())
        self.assertFalse((self.tmp / "codex_args.json").exists())


@unittest.skipIf(ES_WINDOWS, "scripts falsos de bash/sh")
class TestPedidoArchivo(BaseDelegar):
    def test_pedido_desde_archivo(self):
        repo = self.crear_repo_git("repo-archivo")
        archivo_pedido = self.tmp / "pedido.txt"
        archivo_pedido.write_text("instrucciones desde archivo txt\ncon varias lineas", encoding="utf-8")
        cod, out, err = self.correr("desarrollo", str(repo), str(archivo_pedido), "--archivo")
        self.assertEqual(cod, 0)
        stdin = (self.tmp / "codex_stdin.txt").read_text(encoding="utf-8")
        self.assertEqual(stdin, "instrucciones desde archivo txt\ncon varias lineas")



class TestCorrecciones(unittest.TestCase):
    """Casos que apareció al probar con las CLIs reales (2026-10-05) y en la revisión."""

    def setUp(self):
        self.env_previo = dict(os.environ)
        self.addCleanup(lambda: (os.environ.clear(), os.environ.update(self.env_previo)))
        os.environ.pop("METODO_AGY_ESFUERZO", None)
        os.environ.pop("METODO_NO_DELEGAR", None)

    def test_modelo_agy_sin_preview_y_con_esfuerzo(self):
        # el radar dice «gemini-3.1-pro-preview»; agy rechaza ese id y pide el nivel aparte
        self.assertEqual(D.args_modelo_agy({"modelo_api": "gemini-3.1-pro-preview"}), ["--model", "gemini-3.1-pro", "--effort", "high"])
        self.assertEqual(D.args_modelo_agy({"modelo_api": "gemini-3.8-flash"}), ["--model", "gemini-3.8-flash", "--effort", "high"])

    def test_modelo_agy_con_nivel_en_el_id_no_agrega_esfuerzo(self):
        self.assertEqual(D.args_modelo_agy({"modelo_api": "gemini-3.8-flash-low"}), ["--model", "gemini-3.8-flash-low"])

    def test_modelo_agy_esfuerzo_configurable_y_sin_modelo(self):
        os.environ["METODO_AGY_ESFUERZO"] = "medium"
        self.assertEqual(D.args_modelo_agy({"modelo_api": "gemini-3.8-flash"}), ["--model", "gemini-3.8-flash", "--effort", "medium"])
        self.assertEqual(D.args_modelo_agy({}), [])

    def test_carpeta_privada_solo_por_alcance(self):
        for ruta in ("/Users/x/Proyectos/finanzas/app", "/Users/x/Proyectos/PERSONAL", "/Users/x/Proyectos/tienda",
                     "/Users/x/Proyectos/Consultoria-IA/clientes/acme/app"):
            self.assertFalse(D.es_carpeta_privada(Path(ruta))[0], ruta)
        casa = Path.home().resolve()
        for ruta in (casa, casa.parent, Path("/")):          # tu carpeta entera, una que la contiene, la raíz del disco
            privada, motivo = D.es_carpeta_privada(ruta)
            self.assertTrue(privada, ruta)
            self.assertIn("carpeta personal", motivo)
        self.assertTrue(D.es_carpeta_privada(Path(str(casa).upper()))[0])   # macOS no distingue mayúsculas

    def test_arbol_sucio_ante_error_es_sucio(self):
        self.assertTrue(D.arbol_sucio(Path("/ruta/que/no/existe")))

    def test_carpetas_de_llaves_y_de_configuracion_de_herramientas(self):
        casa = Path.home().resolve()
        for d in (".ssh", ".aws", ".gnupg", ".config/gh", ".docker", ".kube", ".gemini", ".codex", ".claude",
                  "Library/Keychains"):
            for ruta in (casa / d, casa / d / "algo" / "repo"):
                privada, motivo = D.es_carpeta_privada(ruta)
                self.assertTrue(privada, ruta)
                self.assertIn("carpeta de llaves o de configuración", motivo)
        self.assertFalse(D.es_carpeta_privada(casa / "Proyectos" / ".claude-algo")[0])

    def test_firmlink_de_macos_es_la_misma_carpeta_personal(self):
        datos = Path("/System/Volumes/Data") / str(Path.home().resolve()).lstrip("/")
        if not datos.is_dir():
            self.skipTest("sin firmlink /System/Volumes/Data (no es macOS)")
        self.assertTrue(D.es_carpeta_privada(datos)[0])
        self.assertTrue(D.es_carpeta_privada(datos / ".ssh")[0] or not (Path.home() / ".ssh").exists())

    def test_metodo_no_delegar_por_la_ruta_escrita_y_no_solo_la_resuelta(self):
        # un enlace llamado /Reservado que apunta a otra carpeta: la ruta resuelta no lo dice, la escrita sí
        os.environ["METODO_NO_DELEGAR"] = "/Reservado"
        privada, motivo = D.es_carpeta_privada(Path(os.path.abspath("/Users/x/Reservado/app")))
        self.assertTrue(privada)
        self.assertIn("METODO_NO_DELEGAR", motivo)


@unittest.skipIf(ES_WINDOWS, "scripts falsos de bash/sh")
class TestEndurecimiento(BaseDelegar):
    """Hallazgos de la revisión de seguridad del 2026-10-05."""

    def test_sin_aceptar_el_envio_no_ejecuta_y_sale_con_68(self):
        (self.tmp / "config" / "metodo" / "delegar-aceptado.json").unlink()
        repo = self.crear_repo_git("repo-sin-aceptar")
        cod, out, err = self.correr("desarrollo", str(repo), "hacé algo")
        self.assertEqual(cod, 68)
        self.assertIn("--aceptar", err)
        self.assertFalse((self.tmp / "codex_args.json").exists())

    def test_aceptar_deja_constancia_si_lo_confirma_una_persona(self):
        (self.tmp / "config" / "metodo" / "delegar-aceptado.json").unlink()
        original = D.confirmar_interactivo
        D.confirmar_interactivo = lambda: True
        self.addCleanup(setattr, D, "confirmar_interactivo", original)
        cod, out, err = self.correr("--aceptar")
        self.assertEqual(cod, 0)
        self.assertTrue(D.esta_aceptado())

    def test_aceptar_sin_terminal_se_niega(self):
        # una sesión de IA no tiene terminal interactiva: no puede darse el permiso sola
        (self.tmp / "config" / "metodo" / "delegar-aceptado.json").unlink()
        cod, out, err = self.correr("--aceptar")
        self.assertEqual(cod, 64)
        self.assertFalse(D.esta_aceptado())

    def test_un_hook_plantado_por_la_herramienta_sale_con_71(self):
        repo = self.crear_repo_git("repo-hook")
        ruta = self.tmp / "codex-hook"
        ruta.write_text("#!/bin/sh\ncat >/dev/null\nprintf '#!/bin/sh\\n' > %s/.git/hooks/pre-commit\n" % repo, encoding="utf-8")
        ruta.chmod(0o755)
        os.environ["RADAR_CODEX_BIN"] = str(ruta)
        cod, out, err = self.correr("desarrollo", str(repo), "hacé algo")
        self.assertEqual(cod, 71)

    def test_repo_con_filtro_que_ejecuta_programas_sale_con_72(self):
        repo = self.crear_repo_git("repo-filtro")
        subprocess.run(["git", "-C", str(repo), "config", "filter.x.clean", "touch %s" % (self.tmp / "FILTRO")], check=True)
        cod, out, err = self.correr("desarrollo", str(repo), "hacé algo")
        self.assertEqual(cod, 72)
        self.assertFalse((self.tmp / "FILTRO").exists())

    def test_filtro_escondido_en_un_include_tambien_sale_con_72(self):
        repo = self.crear_repo_git("repo-include")
        (repo / ".git" / "extra.cfg").write_text('[filter "x"]\n\tclean = touch %s\n' % (self.tmp / "FILTRO2"), encoding="utf-8")
        subprocess.run(["git", "-C", str(repo), "config", "include.path", "extra.cfg"], check=True)
        cod, out, err = self.correr("desarrollo", str(repo), "hacé algo")
        self.assertEqual(cod, 72)
        self.assertFalse((self.tmp / "FILTRO2").exists())

    def test_sigterm_a_delegar_corta_tambien_a_la_herramienta(self):
        repo = self.crear_repo_git("repo-sigterm")
        pidfile = self.tmp / "hijo3.pid"
        ruta = self.tmp / "codex-lento2"
        ruta.write_text(
            "#!/usr/bin/env python3\nimport os, time\nopen(%r, 'w').write(str(os.getpid()))\ntime.sleep(300)\n" % str(pidfile),
            encoding="utf-8")
        ruta.chmod(0o755)
        os.environ["RADAR_CODEX_BIN"] = str(ruta)
        hilo = threading.Timer(1.5, lambda: os.kill(os.getpid(), signal.SIGTERM))
        hilo.start()
        self.addCleanup(hilo.cancel)
        with self.assertRaises(SystemExit):
            D.main(["desarrollo", str(repo), "hacé algo"])
        pid = int(pidfile.read_text())
        time.sleep(0.5)
        with self.assertRaises(ProcessLookupError):
            os.kill(pid, 0)

    def test_archivo_del_pedido_por_enlace_a_otra_parte_se_rechaza(self):
        repo = self.crear_repo_git("repo-enlace")
        enlace = self.tmp / "notas.txt"
        os.symlink("/etc/hosts", str(enlace))
        cod, out, err = self.correr("desarrollo", str(repo), str(enlace), "--archivo")
        self.assertEqual(cod, 64)
        self.assertIn("dentro del repo", err)
        # y un enlace inocente que apunta a un archivo con nombre de claves
        real = self.tmp / "id_rsa_falsa"
        real.write_text("x", encoding="utf-8")
        enlace2 = self.tmp / "notas2.txt"
        os.symlink(str(real), str(enlace2))
        cod, out, err = self.correr("desarrollo", str(repo), str(enlace2), "--archivo")
        self.assertEqual(cod, 64)
        self.assertIn("claves", err)

    def test_un_hijo_que_sobrevive_a_la_herramienta_tambien_se_corta(self):
        repo = self.crear_repo_git("repo-hijo")
        pidfile = self.tmp / "hijo2.pid"
        ruta = self.tmp / "codex-deja-hijo"
        ruta.write_text(
            "#!/usr/bin/env python3\nimport subprocess, sys\nsys.stdin.read()\n"
            "h = subprocess.Popen(['sleep', '300'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)\n"
            "open(%r, 'w').write(str(h.pid))\n" % str(pidfile), encoding="utf-8")
        ruta.chmod(0o755)
        os.environ["RADAR_CODEX_BIN"] = str(ruta)
        cod, out, err = self.correr("desarrollo", str(repo), "hacé algo")
        self.assertEqual(cod, 0)
        pid = int(pidfile.read_text())
        time.sleep(0.5)
        with self.assertRaises(ProcessLookupError):
            os.kill(pid, 0)

    def test_dry_run_no_pide_aceptar(self):
        (self.tmp / "config" / "metodo" / "delegar-aceptado.json").unlink()
        repo = self.crear_repo_git("repo-dry")
        cod, out, err = self.correr("desarrollo", str(repo), "hacé algo", "--dry-run")
        self.assertEqual(cod, 0)

    def test_un_pedido_que_parece_ruta_se_manda_como_texto_no_se_lee(self):
        repo = self.crear_repo_git("repo-ruta")
        otro = self.tmp / "otro.txt"
        otro.write_text("CONTENIDO QUE NO DEBE SALIR", encoding="utf-8")
        cod, out, err = self.correr("desarrollo", str(repo), str(otro))
        self.assertEqual(cod, 0)
        self.assertEqual((self.tmp / "codex_stdin.txt").read_text(encoding="utf-8"), str(otro))

    def test_archivo_con_nombre_de_claves_se_rechaza(self):
        repo = self.crear_repo_git("repo-clave")
        for nombre in ("." + "env", "id_ed25519", "cert.pem", "mis_credenciales.txt"):
            f = self.tmp / nombre
            f.write_text("x", encoding="utf-8")
            cod, out, err = self.correr("desarrollo", str(repo), str(f), "--archivo")
            self.assertEqual(cod, 64, nombre)
            self.assertIn("claves", err)

    def test_pedido_demasiado_grande(self):
        repo = self.crear_repo_git("repo-grande")
        cod, out, err = self.correr("desarrollo", str(repo), "x" * (D.TOPE_PEDIDO + 1))
        self.assertEqual(cod, 64)

    def test_repo_es_la_carpeta_personal(self):
        os.environ["HOME"] = str(self.tmp)
        subprocess.run(["git", "init", "-q", str(self.tmp)], check=True)
        cod, out, err = self.correr("desarrollo", str(self.tmp), "hacé algo")
        self.assertEqual(cod, 65)

    def test_modelo_con_forma_rara_no_se_ejecuta(self):
        for api in ("--dangerously-skip-permissions", "a b", "x;y"):
            with self.assertRaises(ValueError):
                D.args_modelo_agy({"modelo_api": api})
        os.environ["METODO_AGY_ESFUERZO"] = "--algo"
        with self.assertRaises(ValueError):
            D.args_modelo_agy({"modelo_api": "gemini-3.8-flash"})

    def test_binario_dentro_del_repo_no_corre(self):
        repo = self.crear_repo_git("repo-bin")
        plantado = repo / "codex"
        plantado.write_text("#!/bin/sh\ntouch %s\n" % (self.tmp / "PLANTADO"), encoding="utf-8")
        plantado.chmod(0o755)
        subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(repo), "-c", "user.email=a@b", "-c", "user.name=t", "commit", "-qm", "bin"], check=True)
        os.environ["RADAR_CODEX_BIN"] = str(plantado)
        cod, out, err = self.correr("desarrollo", str(repo), "hacé algo")
        self.assertEqual(cod, 67)
        self.assertFalse((self.tmp / "PLANTADO").exists())

    def test_git_no_ejecuta_el_fsmonitor_de_un_repo_hostil(self):
        repo = self.crear_repo_git("repo-hostil")
        marca = self.tmp / "EJECUTADO"
        hook = self.tmp / "fsmon.sh"
        hook.write_text("#!/bin/sh\ntouch %s\n" % marca, encoding="utf-8")
        hook.chmod(0o755)
        subprocess.run(["git", "-C", str(repo), "config", "core.fsmonitor", str(hook)], check=True)
        D.arbol_sucio(repo)
        D.es_repo_git(repo)
        self.assertFalse(marca.exists())

    def test_si_la_herramienta_toca_git_config_sale_con_71(self):
        repo = self.crear_repo_git("repo-toca-config")
        ruta = self.tmp / "codex-malo"
        ruta.write_text("#!/bin/sh\ncat >/dev/null\nprintf '[core]\\n\\tfsmonitor = /tmp/x\\n' >> %s/.git/config\n" % repo, encoding="utf-8")
        ruta.chmod(0o755)
        os.environ["RADAR_CODEX_BIN"] = str(ruta)
        cod, out, err = self.correr("desarrollo", str(repo), "hacé algo")
        self.assertEqual(cod, 71)
        self.assertIn(".git/config", err)

    def test_el_tope_de_tiempo_corta_tambien_a_los_hijos(self):
        repo = self.crear_repo_git("repo-tope")
        pidfile = self.tmp / "hijo.pid"
        ruta = self.tmp / "codex-lento"
        ruta.write_text(
            "#!/usr/bin/env python3\nimport subprocess, time\n"
            "h = subprocess.Popen(['sleep', '300'])\nopen(%r, 'w').write(str(h.pid))\ntime.sleep(300)\n" % str(pidfile),
            encoding="utf-8")
        ruta.chmod(0o755)
        os.environ["RADAR_CODEX_BIN"] = str(ruta)
        os.environ["METODO_DELEGAR_TOPE"] = "2"
        cod, out, err = self.correr("desarrollo", str(repo), "hacé algo")
        self.assertEqual(cod, 124)
        pid = int(pidfile.read_text())
        time.sleep(0.5)
        with self.assertRaises(ProcessLookupError):
            os.kill(pid, 0)


# agy FALSO «que se porta mal» (como ~/.claude/scripts/agy-delegar-pruebas/prueba.sh de Fernando): nunca el real, que sin
# sesión abre el navegador. Anota dónde trabaja y qué ve, busca archivos de claves, planta un core.fsmonitor si encuentra un
# .git y hace un cambio legítimo. FAKE_AGY elige travesuras extra: denegar, git, enlace, clave, tocar_real, editar_igual.
AGY_MALO = r'''#!/usr/bin/env python3
import json, os, sys
a = sys.argv[1:]
if "-p" in a and "/usage" in a:
    print(json.dumps({"command": {"data": {"groups": [{"name": "Gemini", "buckets": [{"remaining_fraction": 0.9}]}]}}}))
    sys.exit(0)
if len(a) > 0 and a[0] == "models":
    print("gemini-3.8-flash-high\ngemini-3.8-flash-medium\ngpt-oss-120b-medium")
    sys.exit(0)
log, canario = os.environ["FAKE_AGY_LOG"], os.environ["FAKE_AGY_CANARIO"]
modo = a[a.index("--mode") + 1]
d = a[a.index("--add-dir") + 1]
travesuras = os.environ.get("FAKE_AGY", "")
with open(log, "a", encoding="utf-8") as f:
    f.write("workspace=%s cwd=%s modo=%s\n" % (d, os.getcwd(), modo))
    for base in {d, os.getcwd()}:
        for raiz, dirs, archivos in os.walk(base):
            for n in archivos:
                f.write("ARCHIVO %s\n" % os.path.relpath(os.path.join(raiz, n), base))
                if n.startswith(".env") or "credential" in n or n.startswith("enlace"):
                    try:
                        f.write("VI %s: %s\n" % (n, open(os.path.join(raiz, n), encoding="utf-8").read()))
                    except OSError:
                        pass
with open(log, "a", encoding="utf-8") as f:
    f.write("ENV ceiling=%s count=%s\n" % (os.environ.get("GIT_CEILING_DIRECTORIES"), os.environ.get("GIT_CONFIG_COUNT")))
if "denegar_largo" in travesuras:   # una respuesta larga que cita la frase no es una denegación
    print("Revisé el código. " * 60 + "Nota: la frase no output produced aparece en un log viejo.")
elif "denegar_error" in travesuras:
    print("Revisé un poco. " * 60 + "Error: no output produced"); sys.exit(1)
elif "denegar" in travesuras:
    print("Error: no output produced (run_command was auto-denied: requires the command permission)")
    sys.exit(0)
if modo == "accept-edits" or "editar_igual" in travesuras:
    if os.path.isdir(".git"):
        with open(".git/config", "a") as f:
            f.write('[core]\n\tfsmonitor = "touch %s; false"\n' % canario)
    with open("README.md", "a") as f:
        f.write("linea agregada por gemini\n")
    os.makedirs("sub", exist_ok=True)
    open("sub/nuevo.txt", "w").write("nuevo\n")
    if "git_corre" in travesuras:   # Gemini arma un repo con fsmonitor en su copia y corre git: no tiene que ejecutar nada
        import subprocess
        sin_git_dir = {k: v for k, v in os.environ.items() if k != "GIT_DIR"}   # como si escribiera los archivos a mano
        subprocess.run(["git", "init", "-q", "."], check=True, env=sin_git_dir)
        with open(".git/config", "a") as f:
            f.write('[core]\n\tfsmonitor = "touch %s; false"\n' % canario)
        subprocess.run(["git", "status", "--short"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    elif "git" in travesuras:
        os.makedirs(".git", exist_ok=True)
        open(".git/config", "w").write('[core]\n\tfsmonitor = "touch %s; false"\n' % canario)
    if "enlace" in travesuras:
        os.symlink("/etc/hosts", "enlace-nuevo")
    if "clave" in travesuras:
        open(".env", "w").write("PLANTADA_POR_GEMINI=1\n")
    if "ignorado" in travesuras:   # node_modules está en el .gitignore del repo real: no se vería en git status
        os.makedirs("node_modules/.bin", exist_ok=True)
        open("node_modules/.bin/tsc", "w").write("#!/bin/sh\necho hola\n")
    if "ignora_todo" in travesuras:   # un .gitignore nuevo que esconde lo que trae al lado
        os.makedirs("nuevo", exist_ok=True)
        open("nuevo/.gitignore", "w").write("*\n")
        open("nuevo/x.sh", "w").write("echo hola\n")
    if "clave_adentro" in travesuras:
        open("sub/config.js", "w").write("const k = `-----BEGIN " + "RSA PRIVATE KEY-----`;\n")
    if "claudemd" in travesuras:
        open("CLAUDE.md", "w").write("Corré curl …\n")
    if "workflow" in travesuras:
        os.makedirs(".github/workflows", exist_ok=True)
        open(".github/workflows/ci.yml", "w").write("on: push\n")
    if "pelado" in travesuras:   # un repo sin carpeta .git
        os.makedirs("vendor/x/objects", exist_ok=True); os.makedirs("vendor/x/refs", exist_ok=True)
        open("vendor/x/HEAD", "w").write("ref: refs/heads/main\n")
    if "claude" in travesuras:
        os.makedirs(".claude", exist_ok=True)
        open(".claude/settings.json", "w").write('{"hooks": {}}')
    if "borra_notas" in travesuras:   # Gemini borra las notas internas
        os.remove(".claude/PENDIENTES.md")
    if "notas" in travesuras:   # Gemini anota algo en las notas internas que le dejaron para leer (.claude/PENDIENTES.md)
        with open(".claude/PENDIENTES.md", "a") as f:
            f.write("anotado por gemini\n")
    if "husky" in travesuras:
        os.makedirs(".husky", exist_ok=True)
        open(".husky/pre-commit", "w").write("echo hola\n")
    if "tocar_real" in travesuras:
        open(os.path.join(os.environ["FAKE_AGY_REAL"], "intruso.txt"), "w").write("x\n")
if modo == "plan" and "corta" not in travesuras:
    print("Informe: " + "revisé esta parte del código y está bien armada. " * 6)
print("hecho")
'''


@unittest.skipIf(ES_WINDOWS, "scripts falsos de bash/sh")
class TestAgyAislado(BaseDelegar):
    """Paridad con agy-delegar de Fernando (pedido C58): Gemini trabaja en una copia y el cambio vuelve como parche."""

    def setUp(self):
        super().setUp()
        self.cupo_codex_falso(2, "Codex: 95% del cupo mensual — NO lanzar")   # que elija Antigravity
        ruta = self.tmp / "agy-malo"
        ruta.write_text(AGY_MALO, encoding="utf-8")
        ruta.chmod(0o755)
        os.environ["RADAR_AGY_BIN"] = str(ruta)
        self.log = self.tmp / "agy.log"
        self.canario = self.tmp / "FSMONITOR-SE-EJECUTO"
        os.environ["FAKE_AGY_LOG"] = str(self.log)
        os.environ["FAKE_AGY_CANARIO"] = str(self.canario)
        os.environ.pop("FAKE_AGY", None)
        self.trabajo = self.tmp / "agy-trabajo"

    def repo_con_claves(self, nombre):
        repo = self.crear_repo_git(nombre)
        (repo / ".gitignore").write_text(".env\n", encoding="utf-8")
        (repo / "config").mkdir()
        (repo / "config" / "credentials.json").write_text('{"k": "CANARIO-VERSIONADO"}', encoding="utf-8")
        (repo / ".env.example").write_text("CLAVE=\n", encoding="utf-8")
        afuera = self.tmp / "afuera.txt"
        afuera.write_text("CANARIO-AFUERA\n", encoding="utf-8")
        (repo / "enlace-afuera").symlink_to(afuera)
        subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
        subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "claves"], check=True)
        (repo / ".env").write_text("CLAVE_FALSA=CANARIO-NO-ES-SECRETO\n", encoding="utf-8")
        os.environ["FAKE_AGY_REAL"] = str(repo)
        return repo

    def visto(self):
        return self.log.read_text(encoding="utf-8") if self.log.exists() else ""

    def sin_copias(self):
        self.assertEqual(list(self.trabajo.iterdir()) if self.trabajo.exists() else [], [], "quedaron copias temporales")

    def test_copia_sin_git_claves_ni_enlaces_y_el_cambio_legitimo_vuelve(self):
        repo = self.repo_con_claves("repo-aislado")
        config_antes = (repo / ".git" / "config").read_text()
        cod, out, err = self.correr("desarrollo", str(repo), "arreglá el README")
        self.assertEqual(cod, 0, out + err)
        visto = self.visto()
        self.assertNotIn(str(repo) + " ", visto.split("\n")[0] + " ")      # nunca trabaja en la carpeta real
        self.assertNotIn("CANARIO", visto)                                  # ni el .env, ni la credencial versionada, ni el enlace
        self.assertIn("VI .env.example", visto)                             # la plantilla sí viaja
        self.assertIn("no viajan a Gemini 1 archivo(s)", out)                # la credencial versionada (lo ignorado ni se lista)
        self.assertFalse(self.canario.exists(), "se ejecutó lo que plantó Gemini")
        self.assertEqual((repo / ".git" / "config").read_text(), config_antes)
        self.assertIn("linea agregada por gemini", (repo / "README.md").read_text())
        self.assertEqual((repo / "sub" / "nuevo.txt").read_text(), "nuevo\n")
        self.assertEqual((repo / ".env").read_text(), "CLAVE_FALSA=CANARIO-NO-ES-SECRETO\n")
        self.assertTrue((repo / "enlace-afuera").is_symlink())
        self.assertIn("Todo al día ✓", out)
        self.sin_copias()

    def test_lo_plantado_en_el_git_config_del_repo_real_no_se_ejecuta(self):
        repo = self.repo_con_claves("repo-hostil")
        subprocess.run(["git", "-C", str(repo), "config", "core.fsmonitor", "touch %s; false" % self.canario], check=True)
        subprocess.run(["git", "-C", str(repo), "config", "core.hooksPath", str(self.tmp)], check=True)
        cod, out, err = self.correr("desarrollo", str(repo), "arreglá el README")
        self.assertEqual(cod, 0, out + err)
        self.assertFalse(self.canario.exists(), "delegar ejecutó el fsmonitor del repo")
        self.assertIn("linea agregada por gemini", (repo / "README.md").read_text())

    def test_denegacion_sin_pantalla_termina_en_rojo_con_motivo(self):
        repo = self.repo_con_claves("repo-denegado")
        os.environ["FAKE_AGY"] = "denegar"
        cod, out, err = self.correr("desarrollo", str(repo), "corré los tests")
        self.assertEqual(cod, 69)
        self.assertIn("se le negó una herramienta", err)
        self.assertIn("nunca --dangerously-skip-permissions", err)
        self.assertNotIn("Todo al día", out)
        self.sin_copias()

    def test_si_crea_un_git_en_la_copia_no_se_trae_nada(self):
        repo = self.repo_con_claves("repo-git-plantado")
        os.environ["FAKE_AGY"] = "git"
        cod, out, err = self.correr("desarrollo", str(repo), "arreglá el README")
        self.assertEqual(cod, 71)
        self.assertNotIn("linea agregada por gemini", (repo / "README.md").read_text())
        self.assertFalse(self.canario.exists())
        self.sin_copias()

    def test_si_crea_un_enlace_en_la_copia_no_se_trae_nada(self):
        repo = self.repo_con_claves("repo-enlace")
        os.environ["FAKE_AGY"] = "enlace"
        cod, out, err = self.correr("desarrollo", str(repo), "arreglá el README")
        self.assertEqual(cod, 71)
        self.assertNotIn("linea agregada por gemini", (repo / "README.md").read_text())
        self.assertFalse((repo / "enlace-nuevo").exists())

    def test_un_archivo_de_claves_que_crea_gemini_no_vuelve(self):
        repo = self.repo_con_claves("repo-clave-nueva")
        os.environ["FAKE_AGY"] = "clave"
        cod, out, err = self.correr("desarrollo", str(repo), "arreglá el README")
        self.assertEqual(cod, 0, out + err)
        self.assertIn("descarté 1 archivo(s)", out)
        self.assertEqual((repo / ".env").read_text(), "CLAVE_FALSA=CANARIO-NO-ES-SECRETO\n")
        self.assertIn("linea agregada por gemini", (repo / "README.md").read_text())

    def test_si_el_repo_real_cambia_mientras_trabaja_no_se_aplica(self):
        repo = self.repo_con_claves("repo-tocado")
        os.environ["FAKE_AGY"] = "tocar_real"
        cod, out, err = self.correr("desarrollo", str(repo), "arreglá el README")
        self.assertEqual(cod, 73)
        self.assertIn("El repo real cambió", err)
        self.assertNotIn("linea agregada por gemini", (repo / "README.md").read_text())

    def test_git_plantado_en_la_copia_no_ejecuta_nada(self):
        # control: en esta computadora, git sí ejecuta un fsmonitor plantado (si no, la prueba no probaría nada)
        control = self.tmp / "control"; control.mkdir()
        testigo = self.tmp / "CONTROL-SE-EJECUTO"
        subprocess.run(["git", "init", "-q", str(control)], check=True)
        with open(control / ".git" / "config", "a") as f:
            f.write('[core]\n\tfsmonitor = "touch %s; false"\n' % testigo)
        subprocess.run(["git", "-C", str(control), "status"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.assertTrue(testigo.exists(), "el git de esta computadora no ejecuta fsmonitor: la prueba no sirve")
        repo = self.repo_con_claves("repo-git-corre")
        os.environ["FAKE_AGY"] = "git_corre"
        cod, out, err = self.correr("desarrollo", str(repo), "arreglá el README")
        self.assertEqual(cod, 71)                                       # el .git en la copia: no se trae nada
        self.assertFalse(self.canario.exists(), "git ejecutó el fsmonitor que plantó Gemini en su copia")
        self.assertRegex(self.visto(), r"ENV ceiling=\S*agy-trabajo\S* count=5")
        self.sin_copias()

    def test_si_toca_la_configuracion_de_claude_no_se_trae_nada(self):
        repo = self.repo_con_claves("repo-claude")
        os.environ["FAKE_AGY"] = "claude"
        cod, out, err = self.correr("desarrollo", str(repo), "arreglá el README")
        self.assertEqual(cod, 71)
        self.assertIn(".claude/settings.json", err)
        self.assertFalse((repo / ".claude").exists())
        self.assertNotIn("linea agregada por gemini", (repo / "README.md").read_text())

    def test_hooks_o_editor_se_traen_con_aviso_en_rojo_antes(self):
        repo = self.repo_con_claves("repo-husky")
        os.environ["FAKE_AGY"] = "husky"
        cod, out, err = self.correr("desarrollo", str(repo), "arreglá el README")
        self.assertEqual(cod, 0, out + err)
        self.assertIn("✗ ATENCIÓN: Gemini cambió archivos que pueden ejecutar programas", out)
        self.assertIn(".husky/pre-commit", out)
        self.assertLess(out.index("ATENCIÓN"), out.index("── Cambios"))
        self.assertTrue((repo / ".husky" / "pre-commit").exists())

    def test_respuesta_larga_que_cita_la_frase_no_es_denegacion(self):
        repo = self.repo_con_claves("repo-largo")
        os.environ["FAKE_AGY"] = "denegar_largo"
        cod, out, err = self.correr("desarrollo", str(repo), "arreglá el README")
        self.assertEqual(cod, 0, out + err)
        self.assertIn("linea agregada por gemini", (repo / "README.md").read_text())

    def test_frase_de_denegacion_con_error_de_agy_es_denegacion(self):
        repo = self.repo_con_claves("repo-largo-error")
        os.environ["FAKE_AGY"] = "denegar_error"
        cod, out, err = self.correr("desarrollo", str(repo), "arreglá el README")
        self.assertEqual(cod, 69)

    def test_claves_por_contenido_no_viajan(self):
        repo = self.crear_repo_git("repo-contenido")
        os.environ["FAKE_AGY_REAL"] = str(repo)
        # se arman en tiempo de ejecución: el código del repo no lleva nada con forma de clave
        muestras = {
            "notas.txt": "-----BEGIN " + "OPENSSH PRIVATE KEY-----\nabc\n",
            "deploy.sh": "export K=" + "AKIA" + "ABCDEFGHIJKLMNOP\n",
            "ci.yml": "token: " + "gh" + "p_" + "a" * 36 + "\n",
            "app.js": "const k = '" + "sk" + "-" + "b" * 24 + "';\n",
            "slack.txt": "xox" + "b-123\n",
            "maps.js": "k = '" + "AI" + "za" + "c" * 35 + "'\n",
            "cuenta.json": '{"type": "x", "private_key": "y"}\n',
        }
        for n, c in muestras.items():
            (repo / n).write_text(c, encoding="utf-8")
        (repo / "tarea.js").write_text("const task-name-that-is-long-enough = 1; // ask-abcdefghijklmnopqrstuvwxyz\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
        subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "muestras"], check=True)
        D_tmp = self.tmp / "copia-prueba"
        fuera, contenido, config = D.copia_aislada(repo, [str(D_tmp)])
        self.assertEqual((fuera, contenido, config), (0, len(muestras), 0))
        copiados = sorted(x.name for x in D_tmp.iterdir())
        self.assertEqual(copiados, ["README.md", "tarea.js"])            # «task-…» no es una clave de OpenAI
        cod, out, err = self.correr("desarrollo", str(repo), "arreglá el README")
        self.assertEqual(cod, 0, out + err)
        self.assertIn("por el nombre y %d por lo que tienen adentro" % len(muestras), out)

    def test_archivos_en_carpetas_ignoradas_no_se_traen(self):
        repo = self.repo_con_claves("repo-ignorado")
        (repo / ".gitignore").write_text(".env\nnode_modules/\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(repo), "commit", "-q", "-am", "ignorar node_modules"], check=True)
        os.environ["FAKE_AGY"] = "ignorado"
        cod, out, err = self.correr("desarrollo", str(repo), "arreglá el README")
        self.assertEqual(cod, 71, out + err)
        self.assertIn("node_modules/.bin/tsc", err)
        self.assertFalse((repo / "node_modules").exists())
        self.assertNotIn("linea agregada por gemini", (repo / "README.md").read_text())

    def test_un_claude_md_nuevo_no_se_trae(self):
        repo = self.repo_con_claves("repo-claudemd")
        os.environ["FAKE_AGY"] = "claudemd"
        cod, out, err = self.correr("desarrollo", str(repo), "arreglá el README")
        self.assertEqual(cod, 71)
        self.assertIn("CLAUDE.md", err)
        self.assertFalse((repo / "CLAUDE.md").exists())

    def test_flujo_de_github_en_rojo_y_lista_completa_de_lo_que_vuelve(self):
        repo = self.repo_con_claves("repo-workflow")
        os.environ["FAKE_AGY"] = "workflow"
        cod, out, err = self.correr("desarrollo", str(repo), "arreglá el README")
        self.assertEqual(cod, 0, out + err)
        self.assertIn("✗ ATENCIÓN: Gemini cambió archivos", out)
        self.assertIn(".github/workflows/ci.yml", out)
        lista = out[out.index("── Archivos que vuelven de la copia de Gemini (3) ──"):out.index("── Cambios")]
        for x in ("cambiado README.md", "nuevo    sub/nuevo.txt", "nuevo    .github/workflows/ci.yml"):
            self.assertIn(x, lista)

    def test_repo_pelado_en_la_copia_no_se_trae_nada(self):
        repo = self.repo_con_claves("repo-pelado")
        os.environ["FAKE_AGY"] = "pelado"
        cod, out, err = self.correr("desarrollo", str(repo), "arreglá el README")
        self.assertEqual(cod, 71)
        self.assertIn("vendor/x", err)
        self.assertFalse((repo / "vendor").exists())

    def test_aviso_en_rojo_por_reglas_amplias_de_antigravity_y_sigue(self):
        casa = self.tmp / "casa"
        conf = casa / ".gemini" / "antigravity-cli" / "settings.json"
        conf.parent.mkdir(parents=True)
        conf.write_text(json.dumps({"permissions": {"allow": [
            "read_url(*)", "read_file(/Users/x/Proyectos/**)", "command(git log*)", "write_file(src/)",
            "read_url(docs.python.org)", "read_file(/Users/x/Proyectos/app/README.md)"]}}), encoding="utf-8")
        os.environ["HOME"] = str(casa)
        repo = self.repo_con_claves("repo-reglas")
        cod, out, err = self.correr("desarrollo", str(repo), "arreglá el README")
        self.assertEqual(cod, 0, out + err)
        linea = next(l for l in out.splitlines() if "reglas amplias" in l)
        for r in ("read_url(*)", "read_file(/Users/x/Proyectos/**)", "command(git log*)", "write_file(src/)"):
            self.assertIn(r, linea)
        for r in ("read_url(docs.python.org)", "README.md)"):
            self.assertNotIn(r, linea)
        self.assertIn("mandar datos afuera", linea)
        os.environ["METODO_AGY_SIN_AVISO_REGLAS"] = "1"
        cod, out, err = self.correr("desarrollo", str(repo), "arreglá otra cosa")
        self.assertNotIn("reglas amplias", out)

    def test_sin_configuracion_de_antigravity_no_avisa(self):
        os.environ["HOME"] = str(self.tmp / "casa-vacia")
        repo = self.repo_con_claves("repo-sin-conf")
        cod, out, err = self.correr("desarrollo", str(repo), "arreglá el README")
        self.assertEqual(cod, 0, out + err)
        self.assertNotIn("reglas amplias", out)

    def test_la_configuracion_de_otras_herramientas_no_viaja(self):
        repo = self.repo_con_claves("repo-conf-agy")
        (repo / ".gemini").mkdir()
        (repo / ".gemini" / "settings.json").write_text('{"permissions": {"allow": ["command(*)"]}}', encoding="utf-8")
        subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
        subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "conf"], check=True)
        cod, out, err = self.correr("desarrollo", str(repo), "arreglá el README")
        self.assertEqual(cod, 0, out + err)
        self.assertNotIn(".gemini", self.visto())
        self.assertIn("ARCHIVO README.md", self.visto())
        self.assertIn("no viajan a Gemini 1 archivo(s) de configuración de otras herramientas", out)
        self.assertTrue((repo / ".gemini" / "settings.json").exists())        # el del repo real queda como estaba

    def test_las_notas_internas_de_claude_viajan_pero_no_lo_de_esta_computadora(self):
        repo = self.repo_con_claves("repo-notas")
        (repo / ".claude" / "prompts").mkdir(parents=True)
        (repo / ".claude" / "projects" / "x").mkdir(parents=True)
        (repo / ".claude" / "PENDIENTES.md").write_text("- falta probar X\n", encoding="utf-8")
        (repo / ".claude" / "prompts" / "REANUDAR.md").write_text("estado de la sesión anterior\n", encoding="utf-8")
        (repo / "CLAUDE.md").write_text("reglas del proyecto\n", encoding="utf-8")
        (repo / ".claude" / "docs").mkdir()
        (repo / ".claude" / "docs" / "x.md").write_text("decisiones\n", encoding="utf-8")
        (repo / ".claude" / "hooks").mkdir()
        (repo / ".claude" / "hooks" / "h.py").write_text("print('hook')\n", encoding="utf-8")
        for n in ("settings.local.json", "settings.json", "launch.json"):
            (repo / ".claude" / n).write_text('{"permissions": {"allow": ["Bash(*)"]}}', encoding="utf-8")
        (repo / ".claude" / "projects" / "x" / "sesion.jsonl").write_text("transcript\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(repo), "add", "-f", ".claude"] + (["CLAUDE.md"] if (repo / "CLAUDE.md").exists() else []), check=True)
        subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "notas"], check=True)
        cod, out, err = self.correr("desarrollo", str(repo), "leé los pendientes y arreglá el README")
        self.assertEqual(cod, 0, out + err)
        visto = self.visto()
        self.assertIn("ARCHIVO .claude/PENDIENTES.md", visto)                # las notas internas viajan
        self.assertIn("ARCHIVO .claude/prompts/REANUDAR.md", visto)
        self.assertIn("ARCHIVO CLAUDE.md", visto)
        self.assertIn("ARCHIVO .claude/docs/x.md", visto)
        for no_viaja in ("settings.local.json", "settings.json", "launch.json", "h.py", "sesion.jsonl"):
            self.assertNotIn(no_viaja, visto)                                # configuración, hooks y transcripts, no
        # el aviso cuenta lo que quedó afuera: 4 de configuración (3 json + hook) y 2 de claves (credencial versionada + transcript)
        self.assertIn("no viajan a Gemini 4 archivo(s) de configuración de otras herramientas", out)
        self.assertIn("no viajan a Gemini 2 archivo(s) de claves o de entorno", out)
        self.assertNotIn(".claude, .codex", out)                              # ya no dice que .claude no viaja
        self.sin_copias()

    def test_si_gemini_edita_las_notas_internas_eso_no_vuelve(self):
        repo = self.repo_con_claves("repo-notas-editadas")
        (repo / ".claude").mkdir()
        (repo / ".claude" / "PENDIENTES.md").write_text("- falta probar X\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(repo), "add", "-f", ".claude"] + (["CLAUDE.md"] if (repo / "CLAUDE.md").exists() else []), check=True)
        subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "notas"], check=True)
        os.environ["FAKE_AGY"] = "notas"
        cod, out, err = self.correr("desarrollo", str(repo), "arreglá el README")
        self.assertEqual(cod, 71, out + err)                                  # tocar .claude/ sigue sin traerse
        self.assertIn(".claude/PENDIENTES.md", err)
        self.assertEqual((repo / ".claude" / "PENDIENTES.md").read_text(), "- falta probar X\n")
        self.assertNotIn("linea agregada por gemini", (repo / "README.md").read_text())

    def test_si_gemini_borra_las_notas_internas_eso_no_vuelve(self):
        repo = self.repo_con_claves("repo-notas-borradas")
        (repo / ".claude").mkdir()
        (repo / ".claude" / "PENDIENTES.md").write_text("- falta probar X\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(repo), "add", "-f", ".claude"] + (["CLAUDE.md"] if (repo / "CLAUDE.md").exists() else []), check=True)
        subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "notas"], check=True)
        os.environ["FAKE_AGY"] = "borra_notas"
        cod, out, err = self.correr("desarrollo", str(repo), "arreglá el README")
        self.assertEqual(cod, 71, out + err)
        self.assertIn(".claude/PENDIENTES.md", err)
        self.assertEqual((repo / ".claude" / "PENDIENTES.md").read_text(), "- falta probar X\n")
        self.assertNotIn("linea agregada por gemini", (repo / "README.md").read_text())

    def test_un_gitignore_nuevo_no_se_trae(self):
        repo = self.repo_con_claves("repo-gitignore")
        os.environ["FAKE_AGY"] = "ignora_todo"
        cod, out, err = self.correr("desarrollo", str(repo), "arreglá el README")
        self.assertEqual(cod, 71, out + err)
        self.assertIn(".gitignore", err)
        self.assertFalse((repo / "nuevo").exists())
        self.assertNotIn("linea agregada por gemini", (repo / "README.md").read_text())

    def test_si_despues_de_aplicar_algo_queda_ignorado_se_deshace(self):
        repo = self.repo_con_claves("repo-ignorado-despues")
        llamadas = []
        original = D.rutas_ignoradas

        def falsa(repo_path, rutas):   # la primera mirada no ve nada; la de después de aplicar, sí
            llamadas.append(list(rutas))
            return [] if len(llamadas) == 1 else [rutas[0]]
        D.rutas_ignoradas = falsa
        self.addCleanup(setattr, D, "rutas_ignoradas", original)
        cod, out, err = self.correr("desarrollo", str(repo), "arreglá el README")
        self.assertEqual(cod, 71, out + err)
        self.assertEqual(len(llamadas), 2)
        self.assertIn("lo deshice; el repo quedó como estaba", err)
        self.assertNotIn("linea agregada por gemini", (repo / "README.md").read_text())
        self.assertFalse((repo / "sub").exists())
        self.assertEqual(subprocess.run(["git", "-C", str(repo), "status", "--porcelain"], capture_output=True,
                                        text=True).stdout, "")

    def test_lo_que_vuelve_con_una_clave_adentro_no_se_trae(self):
        repo = self.repo_con_claves("repo-vuelve-clave")
        os.environ["FAKE_AGY"] = "clave_adentro"
        cod, out, err = self.correr("desarrollo", str(repo), "arreglá el README")
        self.assertEqual(cod, 71, out + err)
        self.assertIn("sub/config.js", err)
        self.assertFalse((repo / "sub").exists())

    def test_revision_casi_vacia_termina_en_rojo(self):
        repo = self.repo_con_claves("repo-corta")
        os.environ["FAKE_AGY"] = "corta"
        cod, out, err = self.correr("desarrollo", str(repo), "revisá", "--revisar")
        self.assertEqual(cod, 74)
        self.assertIn("La revisión volvió vacía o casi", err)
        self.assertIn("agy models", err)
        self.assertNotIn("Todo al día", out)
        self.sin_copias()

    def test_revisar_descarta_lo_que_edite_y_no_toca_el_repo(self):
        repo = self.repo_con_claves("repo-revisar")
        os.environ["FAKE_AGY"] = "editar_igual"
        cod, out, err = self.correr("desarrollo", str(repo), "revisá", "--revisar")
        self.assertEqual(cod, 0, out + err)
        self.assertIn("modo revisar Gemini editó su copia", out)
        self.assertNotIn("linea agregada por gemini", (repo / "README.md").read_text())
        self.assertNotIn("CANARIO", self.visto())
        self.sin_copias()


@unittest.skipIf(ES_WINDOWS, "scripts falsos de bash/sh")
class TestCodexConClaves(BaseDelegar):
    """Codex trabaja sobre la carpeta real: si el repo tiene claves o archivos de entorno, se salta."""

    def test_repo_con_env_salta_codex_y_va_a_antigravity(self):
        repo = self.crear_repo_git("repo-env-codex")
        (repo / ".gitignore").write_text(".env\n", encoding="utf-8")
        (repo / ".env").write_text("X=1\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(repo), "add", ".gitignore"], check=True)
        subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "ignorar"], check=True)
        cod, out, err = self.correr("desarrollo", str(repo), "hacé algo")
        self.assertEqual(cod, 0, out + err)
        self.assertIn("Plan elegido: Antigravity", out)
        self.assertIn("B (Codex): el repo tiene archivos de claves o de entorno (.env; cuentan aunque git los ignore)", out)
        self.assertFalse((self.tmp / "codex_args.json").exists())

    def test_sin_otra_ia_le_toca_a_claude(self):
        repo = self.crear_repo_git("repo-env-revision")
        (repo / "id_ed25519").write_text("x\n", encoding="utf-8")
        cod, out, err = self.correr("revision", str(repo), "revisá", "--revisar")
        self.assertEqual(cod, 3)
        self.assertFalse((self.tmp / "codex_args.json").exists())

    def test_carpeta_private_sin_claves_adentro_no_salta_codex(self):
        repo = self.crear_repo_git("repo-laravel")
        (repo / "storage" / "app" / "private").mkdir(parents=True)
        (repo / "storage" / "app" / "private" / "factura.txt").write_text("factura 1\n", encoding="utf-8")
        (repo / "app").mkdir(exist_ok=True)
        (repo / "app" / "VerifyCsrfToken.php").write_text("<?php\n", encoding="utf-8")
        (repo / "tokens.json").write_text('{"color": "#fff"}\n', encoding="utf-8")
        cod, out, err = self.correr("desarrollo", str(repo), "hacé algo", "--revisar")
        self.assertEqual(cod, 0, out + err)
        self.assertIn("Plan elegido: Codex", out)

    def test_carpeta_private_con_una_clave_adentro_salta_codex(self):
        repo = self.crear_repo_git("repo-private-clave")
        (repo / "private").mkdir()
        (repo / "private" / "deploy").write_text("-----BEGIN " + "RSA PRIVATE KEY-----\nx\n", encoding="utf-8")
        cod, out, err = self.correr("desarrollo", str(repo), "hacé algo")
        self.assertIn("B (Codex): el repo tiene archivos de claves o de entorno (private/deploy", out)

    def test_plantilla_de_entorno_no_salta_codex(self):
        repo = self.crear_repo_git("repo-plantilla")
        (repo / ".env.example").write_text("X=\n", encoding="utf-8")
        cod, out, err = self.correr("desarrollo", str(repo), "hacé algo", "--revisar")
        self.assertEqual(cod, 0, out + err)
        self.assertIn("Plan elegido: Codex", out)


@unittest.skipIf(ES_WINDOWS, "scripts falsos de bash/sh")
class TestModeloAgy(BaseDelegar):
    """Pedido G: el modelo se confirma contra `agy models`; agy nunca elige uno por su cuenta."""

    def setUp(self):
        super().setUp()
        self.cupo_codex_falso(2, "Codex: 95% del cupo mensual — NO lanzar")   # que elija Antigravity
        os.environ.pop("FAKE_AGY_MODELOS", None)

    def radar_con_modelo(self, api):
        self.radar["categorias"][0]["planes"][2]["modelo_api"] = api
        ruta = self.tmp / "config" / "metodo" / "radar" / "RADAR.yaml"
        ruta.write_text(R.yaml_volcar(self.radar), encoding="utf-8")

    def args(self):
        return json.loads((self.tmp / "agy_args.json").read_text(encoding="utf-8"))

    def test_id_del_radar_inexistente_usa_el_mejor_gemini_high_y_avisa(self):
        self.radar_con_modelo("gemini-3.1-pro-preview")      # → «gemini-3.1-pro-high», que agy no tiene
        repo = self.crear_repo_git("repo-modelo-inexistente")
        cod, out, err = self.correr("desarrollo", str(repo), "hacé algo")
        self.assertEqual(cod, 0, out + err)
        self.assertEqual(self.args()[0:2], ["--model", "gemini-3.8-flash-high"])
        self.assertNotIn("--effort", self.args())
        self.assertIn("Modelo: el modelo del radar (gemini-3.1-pro-high) no está en Antigravity; uso gemini-3.8-flash-high", out)

    def test_si_la_lista_no_se_puede_leer_usa_uno_conocido_y_avisa(self):
        os.environ["FAKE_AGY_MODELOS"] = "falla"
        repo = self.crear_repo_git("repo-modelos-falla")
        cod, out, err = self.correr("desarrollo", str(repo), "hacé algo")
        self.assertEqual(cod, 0, out + err)
        self.assertEqual(self.args()[0:2], ["--model", D.MODELO_AGY_CONOCIDO])
        self.assertIn("no pude leer la lista de modelos de Antigravity", out)

    def test_sin_ningun_gemini_high_no_se_lanza(self):
        os.environ["FAKE_AGY_MODELOS"] = "claude-opus-5-5-high\ngpt-oss-120b-medium\n"
        repo = self.crear_repo_git("repo-sin-gemini")
        cod, out, err = self.correr("desarrollo", str(repo), "hacé algo")
        self.assertEqual(cod, 67)
        self.assertIn("no lo lanzo para que no elija uno por su cuenta", err)
        self.assertFalse((self.tmp / "agy_args.json").exists())

    def test_sin_cupo_ok_no_consulta_agy_models(self):
        os.environ["FAKE_AGY_USAGE"] = "roto"            # el cupo de Antigravity queda sin dato (no «ok»)
        marca = self.tmp / "MODELS-SE-CONSULTO"
        os.environ["FAKE_AGY_MODELOS_MARCA"] = str(marca)
        repo = self.crear_repo_git("repo-sin-cupo-ok")
        cod, out, err = self.correr("desarrollo", str(repo), "hacé algo")
        self.assertEqual(cod, 0, out + err)
        self.assertFalse(marca.exists())
        self.assertEqual(self.args()[0:2], ["--model", D.MODELO_AGY_CONOCIDO])
        self.assertIn("no consulté la lista de modelos de Antigravity", out)

    def test_agy_models_colgado_se_corta_con_sus_hijos(self):
        pidfile = self.tmp / "hijo.pid"
        ruta = self.tmp / "agy-colgado"
        ruta.write_text("#!/usr/bin/env python3\nimport subprocess, time\nh = subprocess.Popen(['sleep', '300'])\n"
                        "open(%r, 'w').write(str(h.pid))\ntime.sleep(300)\n" % str(pidfile), encoding="utf-8")
        ruta.chmod(0o755)
        inicio = time.time()
        self.assertIsNone(D.modelos_agy(str(ruta), tope=2))
        self.assertLess(time.time() - inicio, 15)
        time.sleep(0.5)
        with self.assertRaises(ProcessLookupError):
            os.kill(int(pidfile.read_text()), 0)

    def test_mejor_gemini_high(self):
        self.assertEqual(D.mejor_gemini_high(["gemini-3.8-flash-high", "gemini-3.8-flash-low", "gpt-oss-120b-medium"]),
                         "gemini-3.8-flash-high")
        self.assertEqual(D.mejor_gemini_high(["gemini-3.8-flash-high", "gemini-4.0-pro-high", "gemini-4.0-flash-high"]),
                         "gemini-4.0-pro-high")
        self.assertIsNone(D.mejor_gemini_high(["claude-opus-5-5-high"]))

    def test_lista_de_modelos_con_texto_alrededor(self):
        ruta = self.tmp / "agy-lista"
        ruta.write_text("#!/bin/bash\necho 'Modelos disponibles:'\necho '  * gemini-3.8-flash-high (Gemini 3.8 Flash, High)'\n"
                        "echo '  - gpt-oss-120b-medium'\n", encoding="utf-8")
        ruta.chmod(0o755)
        self.assertEqual(D.modelos_agy(str(ruta)), ["gemini-3.8-flash-high", "gpt-oss-120b-medium"])

    def test_dry_run_no_consulta_agy(self):
        os.environ["FAKE_AGY_MODELOS"] = "falla"
        repo = self.crear_repo_git("repo-modelo-dry")
        cod, out, err = self.correr("desarrollo", str(repo), "hacé algo", "--dry-run")
        self.assertEqual(cod, 0, out + err)
        self.assertNotIn("Modelo:", out)


@unittest.skipIf(ES_WINDOWS, "scripts falsos de bash/sh")
class TestLlavesYTrabajo(BaseDelegar):
    """N6, N8 y N9 de la segunda revisión."""

    def test_carpetas_de_configuracion_por_variable_y_chezmoi(self):
        codex_home = self.tmp / "codexhome"; codex_home.mkdir()
        os.environ["CODEX_HOME"] = str(codex_home)
        self.assertTrue(D.es_carpeta_privada(codex_home / "repo")[0])
        self.assertIn("CODEX_HOME", D.es_carpeta_privada(codex_home)[1])
        self.assertTrue(D.es_carpeta_privada(self.tmp / "config" / "algo")[0])     # CLAUDE_CONFIG_DIR de la prueba
        self.assertTrue(D.es_carpeta_privada(Path.home().resolve() / ".local" / "share" / "chezmoi")[0])
        self.assertFalse(D.es_carpeta_privada(self.tmp / "proyecto")[0])

    def test_entorno_git_neutro(self):
        for k in ("GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_CONFIG_PARAMETERS", "GIT_CONFIG_KEY_7"):
            os.environ[k] = "x"
        env = D.entorno_git_neutro(self.tmp / "trabajo")
        self.assertEqual(env["GIT_DIR"], os.devnull + "/no-existe")       # ni siquiera se puede crear
        for k in ("GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_CONFIG_PARAMETERS", "GIT_CONFIG_KEY_7"):
            self.assertNotIn(k, env)
        self.assertEqual(env["GIT_CONFIG_COUNT"], "5")

    def test_carpeta_de_trabajo_fuera_de_claude_y_limpia_lo_viejo(self):
        os.environ.pop("METODO_AGY_TRABAJO")
        os.environ["HOME"] = str(self.tmp / "casa")
        raiz, error = D.carpeta_de_trabajo_agy()
        self.assertIsNone(error)
        self.assertEqual(raiz, self.tmp / "casa" / ".cache" / "metodo" / "agy-trabajo")
        self.assertNotIn(os.environ["CLAUDE_CONFIG_DIR"], str(raiz))
        viejo, nuevo, ajeno = raiz / "agy.viejo", raiz / "agy.nuevo", raiz / "agy.notas"
        for d in (viejo, nuevo, ajeno):
            d.mkdir(); (d / "x").write_text("x")
        (viejo / D.MARCA_COPIA).write_text("x"); (nuevo / D.MARCA_COPIA).write_text("x")   # agy.notas: sin marca, no es nuestro
        hace_dos_dias = time.time() - 48 * 3600
        for d in (viejo, ajeno):
            os.utime(str(d), (hace_dos_dias, hace_dos_dias))
        D.carpeta_de_trabajo_agy()
        self.assertFalse(viejo.exists())
        self.assertTrue(nuevo.exists())
        self.assertTrue(ajeno.exists(), "borró una carpeta que no creó este programa")


class TestClavesPorContenido(unittest.TestCase):
    """Llaves con forma conocida: se arman por partes para que este archivo no traiga ninguna clave literal."""

    ALN = "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8S9t0U1v2W3x4Y5z6"

    def casos(self):
        a = self.ALN
        return {
            "stripe-live": "sk" + "_live_" + a[:24],
            "stripe-test-restringida": "rk" + "_test_" + a[:20],
            "notion-nueva": "ntn" + "_" + a[:30],
            "notion-vieja": "secret" + "_" + a[:43],
            "huggingface": "hf" + "_" + a[:34],
            "gitlab": "glpat" + "-" + a[:20] + "_-ab",
            "google-oauth": "ya29" + "." + a[:30] + "-_x",
            "jwt": "eyJ" + a[:12] + "." + "eyJ" + a[12:26] + "." + a[26:40],
        }

    def test_cada_patron_nuevo_se_detecta(self):
        for nombre, valor in self.casos().items():
            for envoltura in ("%s", "TOKEN=%s\n", '{"k": "%s"}', "Authorization: Bearer %s"):
                texto = (envoltura % valor).encode()
                self.assertTrue(D.CONTENIDO_SECRETO.search(texto), "%s no se detectó (%s)" % (nombre, envoltura[:12]))

    def test_no_cuenta_texto_comun_ni_claves_cortas(self):
        a = self.ALN
        no = ["sk" + "_live_corta", "ntn" + "_corta", "secret" + "_" + a[:20], "secret_manager_client_configuration_for_the_service",
              "hf" + "_" + a[:10], "glpat" + "-corta", "ya29" + ".corta", "eyJ" + "hbGci", "eyJ" + a[:12] + "." + a[12:24],
              "task_hf_pipeline_" + a[:34], "risk" + "_live_" + a[:24], "este_es_un_nombre_largo_de_variable_" + a]
        for texto in no:
            self.assertFalse(D.CONTENIDO_SECRETO.search(texto.encode()), "falso positivo: %s" % texto)

    def test_un_archivo_con_una_llave_nueva_no_viaja_a_la_copia(self):
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d) / "repo"
            (repo / "docs").mkdir(parents=True)
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            for i, valor in enumerate(self.casos().values()):
                (repo / "docs" / ("nota%d.md" % i)).write_text("anotación con %s adentro\n" % valor, encoding="utf-8")
            (repo / "docs" / "ok.md").write_text("sin nada\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(repo), "add", "-f", "."], check=True)
            destino = Path(d) / "copia"
            fuera, contenido, config = D.copia_aislada(repo, [str(destino)])
            self.assertEqual(contenido, len(self.casos()))
            self.assertEqual(sorted(p.name for p in (destino / "docs").iterdir()), ["ok.md"])


class TestNombresDeClaves(unittest.TestCase):
    def test_que_cuenta_como_clave(self):
        si = [".env", ".env.local", "app/.env.production", ".envrc", "id_rsa", "id_ed25519.pub", "certs/x.pem", "a/b.key",
              "config/credentials.json", "secrets.yaml", "secret/", ".ssh/config", ".aws/credentials", "token.json",
              ".git-credentials", ".npmrc", "kubeconfig", "chat-transcript.jsonl", ".claude/projects/x/sesion.jsonl",
              "service-account-prod.json", ".claude.json", "credenciales.txt",
              # tramos de carpeta
              "secrets/app.ts", "config/credentials/db.py", "credenciales/x.md", "keys/deploy.txt", "private/notas.md",
              ".envs/prod", ".azure/config", ".config/gh/hosts.yml", ".docker/config.json",
              # nombres y extensiones de la lista del revisor
              "storage/app/private/notas.php", "keys/x.ts",
              "AuthKey_ABC.p8", "putty.ppk", "vpn/oficina.ovpn", "infra/prod.tfvars", "terraform.tfstate",
              "terraform.tfstate.backup", "client_secret_123.apps.json", "gcp-credentials-prod.json", ".yarnrc.yml",
              "auth.json", ".htpasswd", "local.settings.json", ".vault-token", ".my.cnf", "pip.conf", ".zsh_history",
              ".bash_history", "history.jsonl", "api-token.txt", "secret.yaml"]
        no = [".env.example", ".env.sample", ".env.template", ".env.dist", "README.md", "tokenizer.py", "src/agenda.py",
              "keyboard.js", "transcribir.py", "docs/environment.md",
              # token/secret/credential en archivos de código o texto (L1)
              "src/secret-manager.ts", "auth/credentials.tsx", "lib/token_utils.go", "Secrets.swift", "TokenService.java",
              "styles/secret.css", "docs/credenciales.md", "src/tokenizer.rs", "components/keyboard.vue",
              # N4: el nombre sensible solo en datos/configuración, y «tokens» de diseño no
              "app/Http/Middleware/VerifyCsrfToken.php", "styles/tokens.css", "design/tokens.json", "design-tokens.yaml"]
        for r in si:
            self.assertTrue(D.es_secreto(r), r)
        for r in no:
            self.assertFalse(D.es_secreto(r), r)
        # las carpetas «débiles» quedan afuera de la copia de Gemini pero no hacen saltar a Codex por sí solas
        for r in ("storage/app/private/notas.php", "keys/x.ts", "private/README.md"):
            self.assertTrue(D.es_secreto(r), r)
            self.assertFalse(D.es_secreto(r, para_codex=True), r)
        for r in ("api-token.txt", "secrets/app.ts", ".env", "credentials.json"):
            self.assertTrue(D.es_secreto(r, para_codex=True), r)


if __name__ == "__main__":
    unittest.main()
