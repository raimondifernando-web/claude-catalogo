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
            "if '-p' in sys.argv and '/usage' in sys.argv:\n"
            "    sys.stdout.write(json.dumps({\n"
            "        'command': {'data': {'groups': [{'name': 'Gemini', 'buckets': [{'remaining_fraction': %f}]}]}}\n"
            "    }))\n"
            "    sys.exit(0)\n"
            "with open(%r, 'w', encoding='utf-8') as f:\n"
            "    json.dump(sys.argv[1:], f)\n"
            "with open(%r, 'w', encoding='utf-8') as f:\n"
            "    f.write(sys.stdin.read())\n"
            "if %r:\n"
            "    sys.stdout.write(%r)\n"
            "sys.exit(%d)\n"
        ) % (frac, str(args_file), str(stdin_file), bool(salida), salida, codigo)
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
        self.assertIn("── Cambios (revisalos y corré los tests) ──", out)
        self.assertIn("Todo al día ✓", out)

        args = json.loads((self.tmp / "agy_args.json").read_text(encoding="utf-8"))
        self.assertEqual(args[0:4], ["--model", "gemini-3.8-flash", "--effort", "high"])
        self.assertEqual(args[4:6], ["--mode", "accept-edits"])
        self.assertEqual(args[6:8], ["--add-dir", str(repo)])
        self.assertEqual(args[8], "-p")
        esperado_prompt = (
            "Tarea: hacé una función\n\nNO corras ningún comando. "
            "Editá solo lo pedido. No toques archivos de claves ni de variables de entorno. "
            "Respondé en castellano, corto: qué hiciste o qué encontraste."
        )
        self.assertEqual(args[9], esperado_prompt)

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

    def test_revisar_antigravity_mode_plan(self):
        self.cupo_codex_falso(2, "Codex: 95% del cupo mensual — NO lanzar")
        repo_sucio = self.crear_repo_git("repo-sucio-agy", sucio=True)
        cod, out, err = self.correr("desarrollo", str(repo_sucio), "analizá seguridad", "--revisar")
        self.assertEqual(cod, 0)
        self.assertIn("Plan elegido: Antigravity", out)
        self.assertNotIn("── Cambios (revisalos y corré los tests) ──", out)

        args = json.loads((self.tmp / "agy_args.json").read_text(encoding="utf-8"))
        self.assertEqual(args[4:6], ["--mode", "plan"])
        esperado_prompt = (
            "Tarea: analizá seguridad\n\nNO corras ningún comando. "
            "Solo leé y analizá; no edites nada. "
            "Respondé en castellano, corto: qué hiciste o qué encontraste."
        )
        self.assertEqual(args[9], esperado_prompt)


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
    def test_carpeta_privada_por_patrones_base(self):
        for nombre in ("Personal", "Finanzas", "Consultoria-Negocio", "clientes"):
            repo = self.crear_repo_git("%s/mi-repo" % nombre)
            cod, out, err = self.correr("desarrollo", str(repo), "tarea")
            self.assertEqual(cod, 65, "Falló en carpeta %s" % nombre)
            self.assertIn("No se delega en carpetas privadas", err)
            self.assertFalse((self.tmp / "codex_args.json").exists())

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

    def test_cli_agy_ausente_sale_con_67(self):
        self.cupo_codex_falso(2, "Codex: 95% del cupo mensual — NO lanzar")
        os.environ["RADAR_AGY_BIN"] = str(self.tmp / "agy-inexistente")
        repo = self.crear_repo_git("repo-sin-agy")
        cod, out, err = self.correr("desarrollo", str(repo), "tarea")
        self.assertEqual(cod, 67)
        self.assertIn("no está instalada", err)


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

    def test_carpeta_privada_sin_distinguir_mayusculas(self):
        self.assertTrue(D.es_carpeta_privada(Path("/Users/x/Proyectos/finanzas/app"))[0])
        self.assertTrue(D.es_carpeta_privada(Path("/Users/x/Proyectos/PERSONAL"))[0])
        self.assertFalse(D.es_carpeta_privada(Path("/Users/x/Proyectos/tienda"))[0])

    def test_arbol_sucio_ante_error_es_sucio(self):
        self.assertTrue(D.arbol_sucio(Path("/ruta/que/no/existe")))

    def test_carpeta_privada_por_la_ruta_escrita_y_no_solo_la_resuelta(self):
        # un enlace llamado /Personal que apunta a otra carpeta: la ruta resuelta no lo dice, la escrita sí
        self.assertTrue(D.es_carpeta_privada(Path(os.path.abspath("/Users/x/Personal/app")))[0])


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


if __name__ == "__main__":
    unittest.main()
