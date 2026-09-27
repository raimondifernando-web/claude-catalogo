"""Tests del vigía (detector + hook). Solo biblioteca estándar, sin red real.

Correr desde la raíz del repo:
    python3 -m unittest discover -s plugins/metodo/scripts/vigia/tests -v

Cada test usa un HOME temporal: nunca se lee ni se escribe la configuración real.
"""
import importlib.util
import io
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

AQUI = Path(__file__).resolve().parent
DIR_VIGIA = AQUI.parent
PLUGIN = DIR_VIGIA.parent.parent
VIGIA_PY = DIR_VIGIA / "vigia.py"
AVISO_PY = DIR_VIGIA / "aviso.py"
HOOKS_JSON = PLUGIN / "hooks" / "hooks.json"
ES_WINDOWS = os.name == "nt"


def cargar_modulo(nombre, ruta):
    spec = importlib.util.spec_from_file_location(nombre, str(ruta))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[nombre] = mod  # dataclasses lo necesita registrado
    spec.loader.exec_module(mod)
    return mod


vigia = cargar_modulo("vigia", VIGIA_PY)
aviso = cargar_modulo("aviso", AVISO_PY)

SHA_A = "a" * 40
SHA_B = "b" * 40
SHA_C = "c" * 40
SHA_D = "d" * 40


def iso(dt):
    return dt.isoformat(timespec="seconds")


def ahora():
    return datetime.now(timezone.utc)


# --------------------------------------------------------------------------- #
# Red simulada
# --------------------------------------------------------------------------- #


class RespuestaFalsa:
    def __init__(self, datos):
        self._crudo = json.dumps(datos).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self, n=-1):
        return self._crudo


class OpenerFalso:
    """Reemplaza al opener de urllib: registra cada URL y responde desde un mapa."""

    def __init__(self, respuestas=None, error=None):
        self.respuestas = respuestas or {}
        self.error = error
        self.urls = []

    def open(self, req, timeout=None):
        url = req.full_url
        self.urls.append(url)
        if self.error is not None:
            raise self.error
        if url in self.respuestas:
            valor = self.respuestas[url]
            if isinstance(valor, Exception):
                raise valor
            return RespuestaFalsa(valor)
        raise urllib.error.HTTPError(url, 404, "Not Found", {}, io.BytesIO(b"{}"))


GH = "https://api.github.com/"


def respuestas_completas():
    info = lambda owner: {"default_branch": "main", "owner": {"login": owner}, "stargazers_count": 10, "fork": False}
    return {
        GH + "repos/otro/externo": info("otro"),
        GH + f"repos/otro/externo/compare/{SHA_A}...main": {"ahead_by": 2, "commits": [{"sha": SHA_C}]},
        GH + "repos/duenio/catalogo": info("duenio"),
        GH + f"repos/duenio/catalogo/compare/{SHA_B}...main": {"ahead_by": 0, "commits": []},
        GH + "repos/duenio/skills": info("duenio"),
        GH + "repos/duenio/skills/git/trees/main?recursive=1": {"tree": [{"path": "skills/s1", "type": "tree", "sha": SHA_D}]},
        "https://registry.npmjs.org/paquete-mcp/latest": {"version": "1.1.0"},
    }


# --------------------------------------------------------------------------- #
# Base: HOME temporal
# --------------------------------------------------------------------------- #


class ConHomeTemporal(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="vigia test ")
        self.home = Path(self._tmp.name) / "home con espacios"
        self.home.mkdir()
        self._env_previo = {k: os.environ.get(k) for k in ("HOME", "USERPROFILE", "VIGIA_PERFIL", "VIGIA_OFF")}
        os.environ["HOME"] = str(self.home)
        os.environ["USERPROFILE"] = str(self.home)
        os.environ.pop("VIGIA_PERFIL", None)
        os.environ.pop("VIGIA_OFF", None)
        self.dir_vigia = self.home / ".claude" / "vigia"

    def tearDown(self):
        for k, v in self._env_previo.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        # Si un test lanzó el detector desacoplado, se espera a que termine: si no, el
        # hijo recrearía la carpeta temporal después de borrada, y en Windows no se
        # puede borrar una carpeta que otro proceso tiene abierta.
        limite = time.monotonic() + 30
        if (self.dir_vigia / "lanzamiento.json").exists():
            while time.monotonic() < limite and not self._detector_termino():
                time.sleep(0.2)
        while (self.dir_vigia / ".lock").exists() and time.monotonic() < limite:
            time.sleep(0.2)
        for _ in range(20):
            try:
                self._tmp.cleanup()
                return
            except OSError:
                time.sleep(0.5)
        shutil.rmtree(self._tmp.name, ignore_errors=True)

    # -- helpers --
    def _detector_termino(self):
        try:
            log = (self.dir_vigia / "vigia.log").read_text(encoding="utf-8")
        except OSError:
            return False
        return any(marca in log for marca in (" fin: ", "no toca correr", "ya hay una corrida", " caído:"))

    def escribir(self, relativa, datos):
        ruta = self.home / relativa
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text(json.dumps(datos) if not isinstance(datos, str) else datos, encoding="utf-8")
        return ruta

    def estado(self):
        ruta = self.dir_vigia / "estado.json"
        try:
            return json.loads(ruta.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None  # no existe todavía, o sigue el archivo roto de un test

    def fixtures_completas(self):
        ubic = self.home / ".claude/plugins/marketplaces/mi-catalogo"
        self.escribir(
            ".claude/plugins/known_marketplaces.json",
            {"mi-catalogo": {"source": {"source": "github", "repo": "duenio/catalogo"}, "installLocation": str(ubic)}},
        )
        self.escribir(
            ".claude/plugins/marketplaces/mi-catalogo/.claude-plugin/marketplace.json",
            {
                "plugins": [
                    {"name": "externo", "source": {"source": "github", "repo": "otro/externo", "sha": SHA_A}},
                    {"name": "local", "source": "./plugins/local"},
                    {"name": "fijado-no-instalado", "source": {"source": "github", "repo": "nadie/nada", "sha": SHA_A}},
                ]
            },
        )
        self.escribir(
            ".claude/plugins/installed_plugins.json",
            {"plugins": {"externo@mi-catalogo": [{"gitCommitSha": SHA_A}], "local@mi-catalogo": [{"gitCommitSha": SHA_B}]}},
        )
        self.escribir(".claude/skills-lock.json", {"skills": {"s1": {"source": "duenio/skills", "skillPath": "skills/s1/SKILL.md"}}})
        self.escribir(
            ".mcp.json",
            {
                "mcpServers": {
                    "m1": {"command": "npx", "args": ["-y", "paquete-mcp@1.0.0"], "env": {"TOKEN": "sk-secreto-123"}},
                    "m2": {"command": "npx", "args": ["--api-key", "sk-otro-456", "-y"], "headers": {"Authorization": "sk-h"}},
                }
            },
        )

    def correr(self, argv=(), opener=None, ejecutables=None):
        """Corre el detector en este proceso, sin herramientas externas y con red simulada."""
        opener = opener if opener is not None else OpenerFalso(respuestas_completas())
        ejecutables = ejecutables or {}
        with mock.patch.object(vigia, "_OPENER", opener), mock.patch.object(
            vigia, "encontrar_ejecutable", lambda nombre, extras=(): ejecutables.get(nombre)
        ):
            rc = vigia.main(list(argv))
        self.assertEqual(rc, 0)
        return opener


# --------------------------------------------------------------------------- #
# Detector
# --------------------------------------------------------------------------- #


class TestDetector(ConHomeTemporal):
    def test_sin_gh_usa_https_y_encuentra_novedades(self):
        self.fixtures_completas()
        with mock.patch("subprocess.run", side_effect=AssertionError("no debe correr procesos")):
            self.correr()
        e = self.estado()
        self.assertEqual(e["estado"], "ok", e["degradado"])
        self.assertEqual(e["github"]["modo"], "https")
        self.assertLessEqual(e["github"]["pedidos"], vigia.LIMITE_LLAMADAS_GH_SIN_GH)
        self.assertIn(f"plugin:externo@{SHA_C[:7]}", e["novedades"])
        self.assertIn("mcp:m1@1.1.0", e["novedades"])
        self.assertIsNotNone(e["ultima_corrida"])
        self.assertTrue((self.dir_vigia / "NOVEDADES.md").exists())

    def test_secretos_de_mcp_nunca_salen(self):
        self.fixtures_completas()
        opener = self.correr()
        volcado = (self.dir_vigia / "estado.json").read_text(encoding="utf-8")
        volcado += (self.dir_vigia / "NOVEDADES.md").read_text(encoding="utf-8")
        volcado += " ".join(opener.urls)
        for secreto in ("sk-secreto-123", "sk-otro-456", "sk-h"):
            self.assertNotIn(secreto, volcado)

    def test_hosts_permitidos_en_una_corrida_completa(self):
        self.fixtures_completas()
        self.escribir(".claude/vigia/perfil.json", {"clis": {"npm": ["algo-cli"], "pipx": ["otra-cli"]}})
        opener = self.correr()
        self.assertTrue(opener.urls)
        for url in opener.urls:
            host = vigia.urllib.parse.urlsplit(url).hostname
            self.assertIn(host, vigia.HOSTS_PERMITIDOS, url)

    def test_sin_red_queda_degradado_no_caido(self):
        self.fixtures_completas()
        opener = self.correr(opener=OpenerFalso(error=urllib.error.URLError("sin conexión")))
        e = self.estado()
        self.assertEqual(e["estado"], "degradado")
        self.assertTrue(e["ok"])
        self.assertEqual(e["errores"], [])
        self.assertTrue(any("sin red" in d for d in e["degradado"]))
        self.assertIsNotNone(e["ultima_corrida"])
        # Un host caído no se vuelve a probar en la misma corrida.
        self.assertLessEqual(len(opener.urls), 2)

    def test_cupo_agotado(self):
        self.fixtures_completas()
        self.correr(["--limite-github", "1"])
        e = self.estado()
        self.assertEqual(e["estado"], "degradado")
        self.assertTrue(any("cupo" in d for d in e["degradado"]), e["degradado"])
        self.assertEqual(e["github"]["pedidos"], 1)

    def test_limite_de_la_api_publica(self):
        self.fixtures_completas()
        error = urllib.error.HTTPError(GH, 403, "Forbidden", {"X-RateLimit-Remaining": "0"}, io.BytesIO(b"{}"))
        self.correr(opener=OpenerFalso(error=error))
        e = self.estado()
        self.assertEqual(e["estado"], "degradado")
        self.assertTrue(any("cupo" in d for d in e["degradado"]), e["degradado"])

    def test_sin_perfil_sin_errores(self):
        self.correr()
        e = self.estado()
        self.assertEqual(e["estado"], "ok")
        self.assertEqual(e["degradado"], [])
        self.assertEqual(e["errores"], [])
        self.assertFalse(e["descubrimiento_pendiente"])

    def test_perfil_roto_no_frena(self):
        self.escribir(".claude/vigia/perfil.json", "{esto no es json")
        self.correr()
        e = self.estado()
        self.assertEqual(e["estado"], "degradado")
        self.assertTrue(any("perfil" in d for d in e["degradado"]))

    def test_perfil_de_ejemplo_valida_sin_avisos(self):
        perfil, avisos = vigia.cargar_perfil(DIR_VIGIA / "perfil.ejemplo.json", True)
        self.assertEqual(avisos, [])
        self.assertTrue(perfil["clis"]["npm"])
        texto = (DIR_VIGIA / "perfil.ejemplo.json").read_text(encoding="utf-8")
        self.assertNotRegex(texto, r"/Users/|C:\\\\Users")

    def test_cli_no_disponible_es_degradado_nunca_error(self):
        self.escribir(".claude/vigia/perfil.json", {"clis": {"brew": ["gh"], "uv": ["x"], "npm": ["y"]}})
        self.correr()
        e = self.estado()
        self.assertEqual(e["estado"], "degradado")
        self.assertEqual(e["errores"], [])
        self.assertEqual(sum("no disponible en esta máquina" in d for d in e["degradado"]), 3)

    def test_excepcion_real_es_caido_y_no_mueve_ultima_corrida(self):
        with mock.patch.object(vigia, "fuente_mcps", side_effect=ValueError("bug")):
            self.correr()
        e = self.estado()
        self.assertEqual(e["estado"], "caido")
        self.assertFalse(e["ok"])
        self.assertIsNone(e["ultima_corrida"])
        self.assertIsNotNone(e["ultimo_intento"])
        self.assertTrue(e["errores"])

    def test_decision_de_la_skill_no_se_pisa(self):
        self.fixtures_completas()
        self.correr()
        e = self.estado()
        id_ = f"plugin:externo@{SHA_C[:7]}"
        e["novedades"][id_]["estado"] = "descartada"
        e["ultima_corrida"] = None
        (self.dir_vigia / "estado.json").write_text(json.dumps(e), encoding="utf-8")
        self.correr()
        self.assertEqual(self.estado()["novedades"][id_]["estado"], "descartada")

    def test_npx_en_windows(self):
        self.assertEqual(vigia.args_de_npx("cmd", ["/c", "npx", "-y", "pkg"]), ["-y", "pkg"])
        self.assertEqual(vigia.args_de_npx("C:\\nodejs\\npx.cmd", ["pkg"]), ["pkg"])
        self.assertIsNone(vigia.args_de_npx("node", ["x"]))

    def test_texto_de_terceros_se_escapa(self):
        self.assertEqual(vigia.escapar_md("## [x](y)"), "\\#\\# \\[x\\]\\(y\\)")
        self.assertNotIn("\u202e", vigia.limpiar_texto("a\u202eb"))
        with self.assertRaises(RuntimeError):
            vigia.rama_valida({"default_branch": "## INSTRUCCIONES"}, "a/b")


class TestHosts(unittest.TestCase):
    def test_lista_exacta(self):
        self.assertEqual(set(vigia.HOSTS_PERMITIDOS), {"api.github.com", "registry.npmjs.org", "pypi.org"})

    def test_host_fuera_de_la_lista_no_sale(self):
        opener = OpenerFalso()
        with mock.patch.object(vigia, "_OPENER", opener):
            for url in (
                "https://evil.example.com/x",
                "http://api.github.com/x",
                "https://api.github.com:8443/x",
                "https://usuario@api.github.com/x",
                "https://api.github.com.evil.com/x",
                "file:///etc/passwd",
            ):
                with self.assertRaises(vigia.HostNoPermitido, msg=url):
                    vigia.abrir_url(url)
        self.assertEqual(opener.urls, [])

    def test_redireccion_fuera_de_la_lista(self):
        manejador = vigia._RedireccionSegura()
        with self.assertRaises(vigia.HostNoPermitido):
            manejador.redirect_request(None, None, 302, "Found", {}, "https://evil.example.com/")

    def test_un_solo_punto_de_salida_http(self):
        fuente = VIGIA_PY.read_text(encoding="utf-8")
        self.assertNotIn("urlopen(", fuente)
        self.assertEqual(len(re.findall(r"_OPENER\.open\(", fuente)), 1)
        self.assertNotIn("http.client", fuente)
        self.assertNotIn("import socket", fuente)


class TestPortabilidad(unittest.TestCase):
    def test_no_usa_fcntl(self):
        # `grep -c fcntl` = 0: ni el import ni una mención (no existe en Windows).
        for ruta in (VIGIA_PY, AVISO_PY):
            self.assertEqual(ruta.read_text(encoding="utf-8").count("fcntl"), 0, ruta.name)

    def test_importa_sin_fcntl(self):
        codigo = (
            "import sys, importlib.util; sys.modules['fcntl'] = None\n"
            "for n in ('vigia', 'aviso'):\n"
            "    s = importlib.util.spec_from_file_location(n, sys.argv[1] + '/' + n + '.py')\n"
            "    m = importlib.util.module_from_spec(s); sys.modules[n] = m; s.loader.exec_module(m)\n"
            "print('ok')\n"
        )
        r = subprocess.run([sys.executable, "-c", codigo, str(DIR_VIGIA)], capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("ok", r.stdout)

    def test_hooks_json(self):
        datos = json.loads(HOOKS_JSON.read_text(encoding="utf-8"))
        hook = datos["hooks"]["SessionStart"][0]["hooks"][0]
        self.assertEqual(hook["type"], "command")
        self.assertLessEqual(hook["timeout"], 5)
        self.assertIn('"${CLAUDE_PLUGIN_ROOT}/scripts/vigia/aviso.py"', hook["command"])
        for interprete in ("python3 ", "python ", "py -3 "):
            self.assertIn(interprete, hook["command"])
        self.assertTrue(hook["command"].rstrip().endswith("|| true"))


# --------------------------------------------------------------------------- #
# Lock y puerta de 7 días
# --------------------------------------------------------------------------- #


def entorno_hermetico(home, path_extra=()):
    """Entorno para subprocesos: HOME temporal y sin credenciales de GitHub."""
    env = dict(os.environ)
    for k in ("GH_TOKEN", "GITHUB_TOKEN", "GH_ENTERPRISE_TOKEN", "GH_HOST", "VIGIA_OFF", "VIGIA_PERFIL"):
        env.pop(k, None)
    env["HOME"] = str(home)
    env["USERPROFILE"] = str(home)
    env["GH_CONFIG_DIR"] = str(Path(home) / ".gh-vacio")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    base = [str(p) for p in path_extra] + [os.path.dirname(sys.executable)]
    if ES_WINDOWS:
        base.append(os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32"))
    else:
        base += ["/usr/bin", "/bin"]
    env["PATH"] = os.pathsep.join(base)
    return env


class TestLock(ConHomeTemporal):
    def test_segundo_no_toma_y_no_espera(self):
        ruta = self.dir_vigia / ".lock"
        a, b = vigia.LockVigia(ruta), vigia.LockVigia(ruta)
        self.assertTrue(a.tomar())
        t0 = time.monotonic()
        self.assertFalse(b.tomar())
        self.assertLess(time.monotonic() - t0, 0.5)
        b.soltar()  # soltar sin tenerlo no borra el de otro
        self.assertTrue(ruta.exists())
        a.soltar()
        self.assertFalse(ruta.exists())

    def test_lock_vencido_se_retoma(self):
        ruta = self.dir_vigia / ".lock"
        ruta.parent.mkdir(parents=True)
        viejo = ahora() - timedelta(minutes=vigia.MINUTOS_VENCE_LOCK + 1)
        ruta.write_text(json.dumps({"pid": 999999, "desde": iso(viejo), "token": "x"}), encoding="utf-8")
        lock = vigia.LockVigia(ruta)
        self.assertTrue(lock.tomar())
        lock.soltar()

    def test_dos_procesos_el_segundo_sale_enseguida(self):
        codigo = (
            "import sys, time, importlib.util\n"
            "s = importlib.util.spec_from_file_location('vigia', sys.argv[1])\n"
            "m = importlib.util.module_from_spec(s); sys.modules['vigia'] = m; s.loader.exec_module(m)\n"
            "l = m.LockVigia(m.resolver_rutas().lock)\n"
            "assert l.tomar()\n"
            "print('tomado', flush=True)\n"
            "time.sleep(6)\n"
            "l.soltar()\n"
        )
        env = entorno_hermetico(self.home)
        a = subprocess.Popen([sys.executable, "-c", codigo, str(VIGIA_PY)], env=env, stdout=subprocess.PIPE, text=True)
        try:
            self.assertEqual(a.stdout.readline().strip(), "tomado")
            t0 = time.monotonic()
            b = subprocess.run([sys.executable, str(VIGIA_PY)], env=env, capture_output=True, text=True, timeout=30)
            dura = time.monotonic() - t0
            self.assertEqual(b.returncode, 0, b.stderr)
            self.assertIn("ya hay una corrida", b.stdout)
            self.assertLess(dura, 3.0)
            self.assertIsNone(self.estado())  # el segundo no corrió
        finally:
            a.kill()
            a.wait()
            a.stdout.close()
            (self.dir_vigia / ".lock").unlink()  # quedó del proceso matado


class TestPuerta(ConHomeTemporal):
    def poner_estado(self, dias_ultima=None, horas_intento=None):
        e = {"version": 2, "estado": "ok", "novedades": {}, "base": {}}
        e["ultima_corrida"] = iso(ahora() - timedelta(days=dias_ultima)) if dias_ultima is not None else None
        e["ultimo_intento"] = iso(ahora() - timedelta(hours=horas_intento)) if horas_intento is not None else None
        self.escribir(".claude/vigia/estado.json", e)
        return e

    def test_no_corre_si_fue_hace_menos_de_7_dias(self):
        antes = self.poner_estado(dias_ultima=2, horas_intento=48)
        self.correr(["--si-toca"])
        self.assertEqual(self.estado()["ultima_corrida"], antes["ultima_corrida"])
        self.assertEqual(self.estado()["ultimo_intento"], antes["ultimo_intento"])

    def test_no_corre_si_hubo_intento_en_24h(self):
        antes = self.poner_estado(dias_ultima=8, horas_intento=2)
        self.correr(["--si-toca"])
        self.assertEqual(self.estado()["ultima_corrida"], antes["ultima_corrida"])

    def test_corre_si_toca(self):
        antes = self.poner_estado(dias_ultima=8, horas_intento=30)
        self.correr(["--si-toca"])
        self.assertNotEqual(self.estado()["ultima_corrida"], antes["ultima_corrida"])

    def test_a_mano_corre_siempre(self):
        antes = self.poner_estado(dias_ultima=1, horas_intento=1)
        self.correr()
        self.assertNotEqual(self.estado()["ultima_corrida"], antes["ultima_corrida"])


# --------------------------------------------------------------------------- #
# Hook de aviso
# --------------------------------------------------------------------------- #


class TestAviso(ConHomeTemporal):
    def estado_viejo(self, novedades=3):
        return self.escribir(
            ".claude/vigia/estado.json",
            {
                "estado": "ok",
                "ultima_corrida": iso(ahora() - timedelta(days=10)),
                "novedades": {f"x{i}": {"estado": "nueva"} for i in range(novedades)},
            },
        )

    def correr_aviso(self, env_extra=None, ruta=AVISO_PY, path_extra=()):
        env = entorno_hermetico(self.home, path_extra)
        env.update(env_extra or {})
        t0 = time.monotonic()
        r = subprocess.run([sys.executable, str(ruta)], env=env, capture_output=True, text=True, timeout=30)
        return r, time.monotonic() - t0

    def test_apagado_por_archivo(self):
        self.estado_viejo()
        (self.dir_vigia / "apagado").write_text("", encoding="utf-8")
        r, _ = self.correr_aviso()
        self.assertEqual((r.returncode, r.stdout), (0, ""))
        self.assertFalse((self.dir_vigia / "lanzamiento.json").exists())

    def test_apagado_por_env(self):
        self.estado_viejo()
        r, _ = self.correr_aviso({"VIGIA_OFF": "1"})
        self.assertEqual((r.returncode, r.stdout), (0, ""))
        self.assertFalse((self.dir_vigia / "lanzamiento.json").exists())

    def test_hook_en_menos_de_1s_avisa_y_lanza(self):
        self.estado_viejo()
        r, dura = self.correr_aviso()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertLess(dura, 1.0, f"el hook tardó {dura:.2f} s")
        salida = json.loads(r.stdout)
        self.assertIn("3 novedad", salida["systemMessage"])
        # Recién lanzado: dice «corriendo», no alarma «sin correr».
        self.assertIn("corriendo", salida["systemMessage"])
        self.assertNotIn("sin correr", salida["systemMessage"])
        self.assertEqual(salida["hookSpecificOutput"]["hookEventName"], "SessionStart")
        self.assertTrue((self.dir_vigia / "lanzamiento.json").exists())

    def test_estado_ilegible_no_rompe(self):
        self.escribir(".claude/vigia/estado.json", "{roto")
        r, _ = self.correr_aviso()
        self.assertEqual(r.returncode, 0)
        self.assertIn("no pude leer", json.loads(r.stdout)["systemMessage"])
        # El detector lanzado aparta el archivo roto y arranca de cero.
        self.assertIsNotNone(self.esperar_ultima_corrida().get("ultima_corrida"))
        self.assertTrue(list(self.dir_vigia.glob("estado.json.corrupto-*")))

    def test_mensajes(self):
        n = ahora()
        sano = {"estado": "ok", "ultima_corrida": iso(n - timedelta(days=2)), "novedades": {}}
        self.assertIsNone(aviso.armar_mensaje(sano, n, None, None))
        degradado = dict(sano, estado="degradado")
        self.assertIsNone(aviso.armar_mensaje(degradado, n, None, None))
        caido = dict(sano, estado="caido", errores=["ValueError: x"])
        self.assertIn("caído", aviso.armar_mensaje(caido, n, None, None)[0])
        viejo = dict(sano, ultima_corrida=iso(n - timedelta(days=12)))
        self.assertIn("sin correr hace 12", aviso.armar_mensaje(viejo, n, None, None)[0])
        corriendo = aviso.armar_mensaje(viejo, n, n - timedelta(minutes=10), None)[0]
        self.assertIn("corriendo", corriendo)
        self.assertNotIn("sin correr", corriendo)
        self.assertIsNone(aviso.armar_mensaje(None, n, None, None))  # primera vez: silencio
        nunca = aviso.armar_mensaje(None, n, n - timedelta(days=2), n - timedelta(days=12))
        self.assertIn("nunca terminó", nunca[0])

    def test_puerta_del_hook(self):
        n = ahora()
        self.assertTrue(aviso.debe_lanzar({}, n, None))
        self.assertFalse(aviso.debe_lanzar({"ultima_corrida": iso(n - timedelta(days=3))}, n, None))
        self.assertFalse(aviso.debe_lanzar({"ultima_corrida": iso(n - timedelta(days=8))}, n, n - timedelta(hours=5)))
        self.assertTrue(aviso.debe_lanzar({"ultima_corrida": iso(n - timedelta(days=8))}, n, n - timedelta(hours=25)))

    def _bin_lento(self):
        """Un `uv` falso que tarda 3 s: hace que el detector siga vivo después del hook."""
        bindir = Path(self._tmp.name) / "bin falso"
        bindir.mkdir()
        if ES_WINDOWS:
            (bindir / "uv.bat").write_text("@echo off\r\nping -n 4 127.0.0.1 >nul\r\n", encoding="utf-8")
        else:
            uv = bindir / "uv"
            uv.write_text("#!/bin/sh\nsleep 3\n", encoding="utf-8")
            uv.chmod(0o755)
        self.escribir(".claude/vigia/perfil.json", {"clis": {"uv": ["cualquier-cosa"]}})
        return bindir

    def esperar_ultima_corrida(self, segundos=30):
        limite = time.monotonic() + segundos
        while time.monotonic() < limite:
            e = self.estado()
            if e and e.get("ultima_corrida"):
                return e
            time.sleep(0.2)
        return self.estado()

    def test_hijo_desacoplado_sigue_vivo_tras_terminar_el_padre(self):
        bindir = self._bin_lento()
        env = entorno_hermetico(self.home, [bindir])
        extra = {} if ES_WINDOWS else {"start_new_session": True}
        t0 = time.monotonic()
        padre = subprocess.Popen(
            [sys.executable, str(AVISO_PY)], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **extra
        )
        padre.communicate(timeout=10)
        self.assertEqual(padre.returncode, 0)
        self.assertLess(time.monotonic() - t0, 1.5)
        if not ES_WINDOWS:
            # Lo que haría Claude Code al cerrar: matar el grupo del hook. El hijo está
            # en su propia sesión y no se entera.
            try:
                os.killpg(padre.pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass
        e = self.estado()
        self.assertTrue(e is None or not e.get("ultima_corrida"), "el detector no debería haber terminado todavía")
        e = self.esperar_ultima_corrida()
        self.assertIsNotNone(e and e.get("ultima_corrida"), "el detector desacoplado no terminó")

    def test_ruta_con_espacios(self):
        destino = Path(self._tmp.name) / "plugins con espacios" / "metodo"
        (destino / "scripts" / "vigia").mkdir(parents=True)
        (destino / "hooks").mkdir()
        for f in (VIGIA_PY, AVISO_PY):
            shutil.copy(str(f), str(destino / "scripts" / "vigia" / f.name))
        shutil.copy(str(HOOKS_JSON), str(destino / "hooks" / "hooks.json"))
        if ES_WINDOWS:
            # El comando real del hook con Git Bash se prueba en el CI (paso aparte).
            r, _ = self.correr_aviso(ruta=destino / "scripts" / "vigia" / "aviso.py")
        else:
            comando = json.loads(HOOKS_JSON.read_text(encoding="utf-8"))["hooks"]["SessionStart"][0]["hooks"][0]["command"]
            env = entorno_hermetico(self.home)
            env["CLAUDE_PLUGIN_ROOT"] = str(destino)
            r = subprocess.run(["bash", "-c", comando], env=env, capture_output=True, text=True, timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip(), "")  # primera vez: no hay nada que decir
        e = self.esperar_ultima_corrida()
        self.assertIsNotNone(e and e.get("ultima_corrida"), "el detector no arrancó desde la ruta con espacios")


if __name__ == "__main__":
    unittest.main()
