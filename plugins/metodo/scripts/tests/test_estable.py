"""Pruebas de la rama `estable`: scripts/estable-avanzar.py (con un repo git local de mentira y la API de GitHub simulada
en un servidor local) y los controles estáticos de .github/workflows/estable.yml y .github/rulesets/*.json.

Correr desde la raíz del repo:
    python3 -m unittest discover -s plugins/metodo/scripts/tests -p 'test_estable.py' -v
Sin red real, sin credenciales: nada de esto toca GitHub.
"""
import base64
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import unittest
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent.parent.parent.parent
SCRIPT = RAIZ / "scripts" / "estable-avanzar.py"
WORKFLOW = RAIZ / ".github" / "workflows" / "estable.yml"
RULESETS = RAIZ / ".github" / "rulesets"
ES_WINDOWS = os.name == "nt"

# La «hora del servidor» de todas las pruebas.
AHORA = datetime(2026, 10, 5, 1, 0, 0, tzinfo=timezone.utc)


def cargar_script():
    spec = importlib.util.spec_from_file_location("estable_avanzar", str(SCRIPT))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def hora(horas_atras):
    return (AHORA - timedelta(hours=horas_atras)).strftime("%Y-%m-%dT%H:%M:%SZ")


def evento(sha, horas_atras, tipo="push", ref="refs/heads/main"):
    return {"before": "1" * 40, "after": sha, "ref": ref, "timestamp": hora(horas_atras), "activity_type": tipo}


# --------------------------------------------------------------------------- #
# Función pura (sin git ni red)
# --------------------------------------------------------------------------- #
class TestCandidato(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = cargar_script()

    def test_el_mas_nuevo_con_48_horas_o_mas(self):
        a, b, c = "a" * 40, "b" * 40, "c" * 40
        par = self.m.candidato_por_antiguedad([evento(c, 1), evento(b, 49), evento(a, 100)], AHORA, 48)
        self.assertEqual(par[1], b)

    def test_justo_en_el_limite_cuenta_y_un_segundo_antes_no(self):
        a = "a" * 40
        self.assertEqual(self.m.candidato_por_antiguedad([evento(a, 48)], AHORA, 48)[1], a)
        ev = evento(a, 48)
        ev["timestamp"] = (AHORA - timedelta(hours=48) + timedelta(seconds=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        self.assertIsNone(self.m.candidato_por_antiguedad([ev], AHORA, 48))

    def test_no_depende_del_orden_del_listado(self):
        a, b = "a" * 40, "b" * 40
        par = self.m.candidato_por_antiguedad([evento(a, 100), evento(b, 60)], AHORA, 48)
        self.assertEqual(par[1], b)

    def test_eventos_raros_se_ignoran(self):
        a = "a" * 40
        raros = [
            evento("b" * 40, 100, tipo="force_push"),             # tipo que no deja un commit nuevo
            evento("c" * 40, 100, tipo="branch_deletion"),
            evento("0" * 40, 100),                                # borrado: after todo ceros
            evento("d" * 40, 100, ref="refs/heads/otra"),         # otra rama
            evento("corto", 100),                                 # no es un sha de 40
            evento("E" * 40, 100),                                # mayúsculas: no es un sha de git válido para nosotros
            {"after": "f" * 40, "ref": "refs/heads/main", "activity_type": "push", "timestamp": "ayer"},
            "no soy un dict",
            evento(a, 100),
        ]
        self.assertEqual(self.m.candidato_por_antiguedad(raros, AHORA, 48)[1], a)

    def test_sin_eventos_viejos_no_hay_candidato(self):
        self.assertIsNone(self.m.candidato_por_antiguedad([evento("a" * 40, 47)], AHORA, 48))
        self.assertIsNone(self.m.candidato_por_antiguedad([], AHORA, 48))

    def test_el_mas_viejo(self):
        self.assertEqual(self.m.candidato_mas_viejo([evento("a" * 40, 10), evento("b" * 40, 30)])[1], "b" * 40)

    def test_hora_del_servidor(self):
        dt = self.m.hora_del_servidor("Mon, 05 Oct 2026 01:00:00 GMT")
        self.assertEqual(dt, AHORA)
        for malo in (None, "", "no es una fecha"):
            with self.assertRaises(self.m.Frena):
                self.m.hora_del_servidor(malo)

    def test_la_credencial_solo_va_a_api_github(self):
        self.assertEqual(self.m.cabeceras("https://api.github.com", "XYZ")["Authorization"], "Bearer XYZ")
        self.assertNotIn("Authorization", self.m.cabeceras("http://127.0.0.1:9", "XYZ"))
        self.assertNotIn("Authorization", self.m.cabeceras("https://api.github.com.otro.com", "XYZ"))
        self.assertNotIn("Authorization", self.m.cabeceras("https://api.github.com", None))

    def test_el_push_nunca_se_fuerza(self):
        texto = SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn("--force", texto)
        self.assertNotIn("force-with-lease", texto)
        self.assertNotRegex(texto, r'"\+refs/heads/estable:refs/heads')  # ningún push con refspec forzado


# --------------------------------------------------------------------------- #
# El script entero, con git local y API simulada
# --------------------------------------------------------------------------- #
class _Manejador(BaseHTTPRequestHandler):
    def log_message(self, *args):  # silencio
        pass

    def do_GET(self):  # noqa: N802
        srv = self.server
        srv.pedidos.append(self.path)
        if srv.redirigir and not self.path.startswith("/otro"):
            self.send_response_only(301)
            self.send_header("Location", "http://127.0.0.1:%d/otro" % srv.server_address[1])  # a donde SÍ hay respuesta buena
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if "/check-runs" in self.path:
            por_commit = getattr(srv, "pruebas_por_commit", {})
            sha = self.path.split("/commits/")[1].split("/")[0]
            cuerpo = json.dumps({"check_runs": por_commit.get(sha, srv.pruebas)}).encode("utf-8")
        else:
            cuerpo = json.dumps(srv.actividad).encode("utf-8")
        self.send_response_only(srv.estado)  # sin send_response: no agrega Date solo
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(cuerpo)))
        if srv.fecha is not None:
            self.send_header("Date", srv.fecha)
        self.end_headers()
        self.wfile.write(cuerpo)


@unittest.skipIf(ES_WINDOWS, "el workflow corre en Linux; las pruebas usan git y rutas de Mac/Linux")
class TestScript(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), _Manejador)
        cls.api = "http://127.0.0.1:%d" % cls.srv.server_address[1]
        cls.hilo = threading.Thread(target=cls.srv.serve_forever, daemon=True)
        cls.hilo.start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="estable test ")
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.remoto = self.dir / "remoto.git"
        self.srv.actividad, self.srv.estado, self.srv.redirigir, self.srv.pedidos = [], 200, False, []
        self.srv.pruebas = []   # check-runs que la API simulada devuelve para cualquier commit
        self.srv.pruebas_por_commit = {}   # sha -> check-runs, para los que difieren
        self.srv.fecha = format_datetime(AHORA, usegmt=True)
        self._git(self.dir, "init", "--quiet", "--bare", str(self.remoto))
        self._git(self.remoto, "symbolic-ref", "HEAD", "refs/heads/main")
        # Historia de main: c1..c5. Las fechas de commit son TRAMPA a propósito (ver test_usa_la_hora_del_servidor...).
        origen = self.dir / "origen"
        self._git(self.dir, "clone", "--quiet", str(self.remoto), str(origen))
        self.origen = origen
        self.c = {}
        fechas = {1: "2001-01-01T00:00:00Z", 2: "2001-01-02T00:00:00Z", 3: None, 4: "2001-01-03T00:00:00Z", 5: "2001-01-04T00:00:00Z"}
        for i in range(1, 6):
            self.c[i] = self._commit(origen, "c%d" % i, fechas[i])
        self._git(origen, "push", "--quiet", "origin", "HEAD:refs/heads/main")
        self._git(origen, "push", "--quiet", "origin", "%s:refs/heads/estable" % self.c[1])

    # -- ayudas --
    def _git(self, cwd, *args):
        env = dict(os.environ, GIT_TERMINAL_PROMPT="0", GIT_CONFIG_NOSYSTEM="1")
        r = subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false"] + list(args),
                           cwd=str(cwd), env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        self.assertEqual(r.returncode, 0, "git %s: %s" % (" ".join(args), r.stderr))
        return r.stdout.strip()

    def _commit(self, repo, nombre, fecha=None):
        (Path(repo) / (nombre + ".txt")).write_text(nombre, encoding="utf-8")
        self._git(repo, "add", nombre + ".txt")
        env_previo = {k: os.environ.get(k) for k in ("GIT_AUTHOR_DATE", "GIT_COMMITTER_DATE")}
        if fecha:
            os.environ["GIT_AUTHOR_DATE"] = os.environ["GIT_COMMITTER_DATE"] = fecha
        try:
            self._git(repo, "commit", "--quiet", "-m", nombre)
        finally:
            for k, v in env_previo.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
        return self._git(repo, "rev-parse", "HEAD")

    def _clon_de_trabajo(self, superficial=False, rama=None):
        trabajo = self.dir / "trabajo"
        if trabajo.exists():
            return trabajo
        extra = ["-b", rama] if rama else []
        if superficial:
            self._git(self.dir, "clone", "--quiet", "--depth", "1", *(extra + ["file://" + str(self.remoto), str(trabajo)]))
        else:
            self._git(self.dir, "clone", "--quiet", *(extra + [str(self.remoto), str(trabajo)]))
        return trabajo

    def _revert(self, sha):
        """Un commit nuevo en main que dice «This reverts commit <sha>.» (como git revert o el botón de GitHub)."""
        (self.origen / "revert.txt").write_text(sha + self._git(self.origen, "rev-parse", "HEAD"), encoding="utf-8")
        self._git(self.origen, "add", "revert.txt")
        self._git(self.origen, "commit", "--quiet", "-m", 'Revert "algo"', "-m", "This reverts commit %s." % sha)
        self._git(self.origen, "push", "--quiet", "origin", "HEAD:refs/heads/main")
        return self._git(self.origen, "rev-parse", "HEAD")

    def _estable_remoto(self):
        return self._git(self.remoto, "rev-parse", "refs/heads/estable")

    def _eventos_normales(self):
        # c1 hace 100 h, c2 60 h, c3 50 h (>= 48), c4 47 h, c5 1 h
        self.srv.actividad = [evento(self.c[5], 1), evento(self.c[4], 47), evento(self.c[3], 50),
                              evento(self.c[2], 60), evento(self.c[1], 100)]

    def correr(self, *args, superficial=False, api=None, rama=None, extra_env=None):
        trabajo = self._clon_de_trabajo(superficial, rama)
        salida, resumen = self.dir / "out.txt", self.dir / "resumen.md"
        env = {k: v for k, v in os.environ.items() if k not in ("GH_TOKEN", "GITHUB_TOKEN", "GITHUB_ACTIONS", "GITHUB_ACTOR")}
        env.update(GIT_TERMINAL_PROMPT="0", GITHUB_OUTPUT=str(salida), GITHUB_STEP_SUMMARY=str(resumen))
        env.update(extra_env or {})
        r = subprocess.run([sys.executable, str(SCRIPT), "--repo", "dueno/repo", "--api", api or self.api] + list(args),
                           cwd=str(trabajo), env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           universal_newlines=True, timeout=60)
        r.salida = salida.read_text(encoding="utf-8") if salida.exists() else ""
        r.resumen = resumen.read_text(encoding="utf-8") if resumen.exists() else ""
        return r

    # -- casos --
    def test_avanza_al_candidato_de_48_horas(self):
        self._eventos_normales()
        r = self.correr()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self._estable_remoto(), self.c[3])
        self.assertIn("movido=true", r.salida)
        self.assertIn("sha=" + self.c[3], r.salida)
        self.assertIn("movida a", r.resumen)

    def test_usa_la_hora_del_servidor_y_no_la_fecha_del_commit(self):
        # c4 tiene fecha de commit del año 2001 (parece viejísimo) pero el servidor dice que entró hace 47 h: no vale.
        # c3 tiene fecha de commit de hoy (parece nuevo) pero el servidor dice 50 h: es el candidato.
        self._eventos_normales()
        r = self.correr()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self._estable_remoto(), self.c[3])
        self.assertNotEqual(self._estable_remoto(), self.c[4])

    def test_nada_con_48_horas_no_mueve(self):
        self.srv.actividad = [evento(self.c[5], 1), evento(self.c[4], 47)]
        r = self.correr()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self._estable_remoto(), self.c[1])
        self.assertIn("movido=false", r.salida)
        self.assertIn("todavía", r.stdout)

    def test_corre_desde_el_checkout_de_estable(self):
        # El workflow hace checkout de `estable` (no de main): el script tiene que funcionar parado en esa rama.
        self._eventos_normales()
        r = self.correr(rama="estable")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self._estable_remoto(), self.c[3])
        trabajo = self.dir / "trabajo"
        self.assertEqual(self._git(trabajo, "branch", "--show-current"), "estable")   # su rama local no se toca
        self.assertEqual(self._git(trabajo, "rev-parse", "HEAD"), self.c[1])

    def test_empuja_por_la_url_de_push_del_remoto(self):
        # El workflow lee por HTTPS y empuja por SSH: pone `remote set-url --push`. El script tiene que empujar por el
        # NOMBRE del remoto (nunca por una URL propia) para que eso valga.
        espejo = self.dir / "espejo.git"
        self._git(self.dir, "clone", "--quiet", "--bare", str(self.remoto), str(espejo))
        trabajo = self._clon_de_trabajo()
        self._git(trabajo, "remote", "set-url", "--push", "origin", str(espejo))
        self._eventos_normales()
        r = self.correr()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self._git(espejo, "rev-parse", "refs/heads/estable"), self.c[3])   # se movió donde dice la URL de push
        self.assertEqual(self._estable_remoto(), self.c[1])                                # y no en la de lectura

    def test_el_manual_tambien_corre_desde_el_checkout_de_estable(self):
        r = self.correr("--sha", self.c[4], api="http://127.0.0.1:1", rama="estable")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self._estable_remoto(), self.c[4])

    def test_revert_pendiente_frena_el_avance(self):
        # c3 entraría a estable (50 h) pero main ya lo revirtió hace 10 h: no se avanza hasta que el revert también cumpla.
        c6 = self._revert(self.c[3])
        self.srv.actividad = [evento(c6, 10), evento(self.c[5], 20), evento(self.c[4], 30), evento(self.c[3], 50),
                              evento(self.c[2], 60), evento(self.c[1], 100)]
        r = self.correr()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)    # esperar no es un error
        self.assertEqual(self._estable_remoto(), self.c[1])
        self.assertIn("revertido", r.stdout)
        self.assertIn(self.c[3][:7], r.stdout)
        self.assertIn("movido=false", r.salida)

    def test_revert_de_algo_que_no_entra_no_frena(self):
        # c6 revierte c5, que NO entra a estable en esta corrida (el candidato es c3): no estorba.
        c6 = self._revert(self.c[5])
        self.srv.actividad = [evento(c6, 10), evento(self.c[5], 20), evento(self.c[4], 30), evento(self.c[3], 50),
                              evento(self.c[2], 60), evento(self.c[1], 100)]
        r = self.correr()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self._estable_remoto(), self.c[3])

    def test_cuando_el_revert_tambien_cumple_48_horas_el_avance_sigue(self):
        # El malo (c3) y su revert (c6) entran juntos: estable queda con los dos, sin pasar por un punto malo.
        c6 = self._revert(self.c[3])
        self.srv.actividad = [evento(c6, 50), evento(self.c[5], 98), evento(self.c[4], 99), evento(self.c[3], 100),
                              evento(self.c[2], 110), evento(self.c[1], 120)]
        r = self.correr()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self._estable_remoto(), c6)

    def test_el_manual_ignora_el_revert_pendiente(self):
        # «Pasalo ya» es una decisión de una persona: no se frena por un revert.
        self._revert(self.c[3])
        r = self.correr("--sha", self.c[3], api="http://127.0.0.1:1")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self._estable_remoto(), self.c[3])

    def test_atraso_de_mas_de_4_dias_sale_en_rojo(self):
        # El revert frena el avance y c3 ya lleva 100 h esperando (más de 96): la corrida avisa en rojo.
        c6 = self._revert(self.c[3])
        self.srv.actividad = [evento(c6, 10), evento(self.c[5], 20), evento(self.c[4], 30), evento(self.c[3], 100),
                              evento(self.c[2], 110), evento(self.c[1], 120)]
        r = self.correr()
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertEqual(self._estable_remoto(), self.c[1])
        self.assertIn("96 h", r.stdout)
        self.assertIn(self.c[3][:7], r.stdout)

    def test_sin_atraso_si_lo_que_espera_tiene_menos_de_4_dias(self):
        c6 = self._revert(self.c[3])
        self.srv.actividad = [evento(c6, 10), evento(self.c[5], 20), evento(self.c[4], 30), evento(self.c[3], 60),
                              evento(self.c[2], 70), evento(self.c[1], 120)]
        r = self.correr()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)   # lo único con 96 h o más es c1, que es estable; c3 y c2 esperan menos
        self.assertEqual(self._estable_remoto(), self.c[1])

    def test_ya_al_dia_no_empuja(self):
        self.srv.actividad = [evento(self.c[1], 100)]
        r = self.correr()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("ya está", r.stdout)
        self.assertEqual(self._estable_remoto(), self.c[1])

    def test_candidato_no_descendiente_no_mueve_y_termina_en_rojo(self):
        # estable apunta a un commit que NO está en la historia de main (alguien la movió por fuera del proceso).
        lateral = self.dir / "lateral"
        self._git(self.dir, "clone", "--quiet", str(self.remoto), str(lateral))
        self._git(lateral, "checkout", "--quiet", "-b", "otra", self.c[1])
        x = self._commit(lateral, "x")
        self._git(lateral, "push", "--quiet", "-f", "origin", "%s:refs/heads/estable" % x)
        self._eventos_normales()
        r = self.correr()
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertEqual(self._estable_remoto(), x)
        self.assertIn("no desciende de estable", r.stdout)
        self.assertIn("movido=false", r.salida)

    def test_candidato_que_no_es_ancestro_de_main_no_mueve(self):
        lateral = self.dir / "lateral"
        self._git(self.dir, "clone", "--quiet", str(self.remoto), str(lateral))
        self._git(lateral, "checkout", "--quiet", "-b", "otra", self.c[1])
        y = self._commit(lateral, "y")
        self._git(lateral, "push", "--quiet", "origin", "otra")      # y existe en el clon pero no está en main
        self.srv.actividad = [evento(y, 100)]
        r = self.correr()
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertEqual(self._estable_remoto(), self.c[1])
        self.assertIn("no es ancestro de main", r.stdout)

    def test_candidato_desconocido_no_mueve(self):
        self.srv.actividad = [evento("9" * 40, 100)]
        r = self.correr()
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertEqual(self._estable_remoto(), self.c[1])
        self.assertIn("no está en el clon", r.stdout)

    def test_sha_manual_mueve_sin_esperar_y_sin_consultar_la_api(self):
        r = self.correr("--sha", self.c[5], api="http://127.0.0.1:1")   # nadie escucha: si consultara la API, fallaría
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self._estable_remoto(), self.c[5])
        self.assertEqual(self.srv.pedidos, [])

    def test_sha_manual_con_el_mismo_control_de_ancestria(self):
        lateral = self.dir / "lateral"
        self._git(self.dir, "clone", "--quiet", str(self.remoto), str(lateral))
        self._git(lateral, "checkout", "--quiet", "-b", "otra", self.c[1])
        y = self._commit(lateral, "y")
        self._git(lateral, "push", "--quiet", "origin", "otra")
        r = self.correr("--sha", y)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertEqual(self._estable_remoto(), self.c[1])

    def test_sha_manual_mal_formado(self):
        for malo in ("abc123", "zz" * 20, self.c[3][:12], "main", "1" * 41):
            r = self.correr("--sha", malo)
            self.assertEqual(r.returncode, 2, (malo, r.stdout, r.stderr))
            self.assertEqual(self._estable_remoto(), self.c[1])

    def test_sha_manual_no_retrocede(self):
        self._git(self.origen, "push", "--quiet", "origin", "%s:refs/heads/estable" % self.c[4])
        r = self.correr("--sha", self.c[2])
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("retroceder", r.stdout)
        self.assertEqual(self._estable_remoto(), self.c[4])

    def test_promocion_manual_previa_no_se_deshace(self):
        # Después de «pasalo ya» estable queda por delante del candidato de 48 h: el automático no la retrocede y no falla.
        self._git(self.origen, "push", "--quiet", "origin", "%s:refs/heads/estable" % self.c[5])
        self._eventos_normales()
        r = self.correr()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self._estable_remoto(), self.c[5])
        self.assertIn("más adelante", r.stdout)

    def test_sin_encabezado_date_no_mueve(self):
        self._eventos_normales()
        self.srv.fecha = None
        r = self.correr()
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertEqual(self._estable_remoto(), self.c[1])
        self.assertIn("Date", r.stdout)

    def test_encabezado_date_ilegible_no_mueve(self):
        self._eventos_normales()
        self.srv.fecha = "ayer a la tarde"
        r = self.correr()
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertEqual(self._estable_remoto(), self.c[1])

    def test_api_caida_no_mueve(self):
        self._eventos_normales()
        self.srv.estado = 500
        r = self.correr()
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertEqual(self._estable_remoto(), self.c[1])

    def test_una_redireccion_no_se_sigue(self):
        self._eventos_normales()
        self.srv.redirigir = True
        r = self.correr()
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertEqual(self._estable_remoto(), self.c[1])
        self.assertEqual(len(self.srv.pedidos), 1)   # no fue a buscar la otra dirección

    def test_pide_la_actividad_de_main_con_100_por_pagina(self):
        self._eventos_normales()
        self.correr()
        self.assertEqual(self.srv.pedidos[0], "/repos/dueno/repo/activity?ref=refs/heads/main&per_page=100")

    # -- compuerta de pruebas (C26) --
    def _prueba(self, nombre, estado="completed", conclusion="success"):
        return {"name": nombre, "status": estado, "conclusion": conclusion}

    def test_pruebas_en_verde_dejan_pasar_y_se_anota(self):
        self._eventos_normales()
        self.srv.pruebas = [self._prueba("tests (ubuntu-latest, Python 3.12)"), self._prueba("comando del hook con bash (macos-latest)")]
        r = self.correr()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self._estable_remoto(), self.c[3])
        self.assertIn("2 en verde", r.resumen)
        self.assertTrue(any("/commits/%s/check-runs" % self.c[3] in p for p in self.srv.pedidos))

    def test_una_prueba_en_rojo_frena_y_termina_en_rojo(self):
        self._eventos_normales()
        self.srv.pruebas = [self._prueba("tests (ubuntu-latest, Python 3.12)"),
                            self._prueba("tests (windows-latest, Python 3.9)", conclusion="failure")]
        r = self.correr()
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertEqual(self._estable_remoto(), self.c[1])
        self.assertIn("en rojo", r.stdout)

    def test_commit_en_rojo_seguido_de_otro_sin_pruebas_no_pasa(self):  # F10
        self._eventos_normales()   # candidato c3; el rango estable(c1)..c3 es c2, c3
        self.srv.pruebas_por_commit = {self.c[2]: [self._prueba("tests (ubuntu-latest, Python 3.12)", conclusion="failure")], self.c[3]: []}
        r = self.correr()
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertEqual(self._estable_remoto(), self.c[1])
        self.assertIn("en rojo", r.stdout)

    def test_commit_en_rojo_arreglado_por_uno_posterior_en_verde_pasa(self):  # F10: el arreglo no queda frenado para siempre
        self._eventos_normales()
        self.srv.pruebas_por_commit = {self.c[2]: [self._prueba("tests (ubuntu-latest, Python 3.12)", conclusion="failure")],
                                       self.c[3]: [self._prueba("tests (ubuntu-latest, Python 3.12)")]}
        r = self.correr()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self._estable_remoto(), self.c[3])

    def test_pruebas_sin_terminar_no_mueven_pero_no_es_error(self):
        self._eventos_normales()
        self.srv.pruebas = [self._prueba("tests (ubuntu-latest, Python 3.12)", estado="in_progress", conclusion=None)]
        r = self.correr()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self._estable_remoto(), self.c[1])
        self.assertIn("todavía no terminaron", r.stdout)

    def test_sin_pruebas_registradas_pasa(self):
        self._eventos_normales()
        self.srv.pruebas = [self._prueba("radar (ubuntu-latest)", conclusion="failure")]   # otro workflow: no cuenta
        r = self.correr()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self._estable_remoto(), self.c[3])
        self.assertIn("ninguna registrada", r.resumen)

    def test_el_manual_no_consulta_las_pruebas(self):
        self.srv.pruebas = [self._prueba("tests (ubuntu-latest, Python 3.12)", conclusion="failure")]
        r = self.correr("--sha", self.c[2])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self._estable_remoto(), self.c[2])
        self.assertEqual(self.srv.pedidos, [])

    def test_sin_push_decide_pero_no_empuja(self):
        self._eventos_normales()
        r = self.correr("--sin-push")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self._estable_remoto(), self.c[1])
        self.assertIn("se movería", r.stdout)

    # -- compuerta de security check (F14 del check 0.35.0) --
    def _archivo(self, ruta, contenido, mensaje):
        """Commit en main que escribe `ruta` (relativa al repo) y lo empuja. Devuelve el sha."""
        destino = self.origen / ruta
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(contenido, encoding="utf-8")
        self._git(self.origen, "add", ruta)
        self._git(self.origen, "commit", "--quiet", "-m", mensaje)
        self._git(self.origen, "push", "--quiet", "origin", "HEAD:refs/heads/main")
        return self._git(self.origen, "rev-parse", "HEAD")

    def _version(self, paquete, version):
        return self._archivo("plugins/%s/.claude-plugin/plugin.json" % paquete,
                             json.dumps({"name": paquete, "version": version}), "%s %s" % (paquete, version))

    def _check(self, titulo, ruta="docs/SECURITY-CHECKS.md", cuerpo=""):
        previo = (self.origen / ruta).read_text(encoding="utf-8") if (self.origen / ruta).exists() else "# Checks\n"
        return self._archivo(ruta, previo + "\n%s\n%s\n" % (titulo, cuerpo), "check")

    def test_manual_sin_security_check_no_pasa(self):
        # El incidente: 0.32.0 → 0.35.0 llegaron a estable con un «pasalo ya» y sin check.
        v = self._version("metodo", "0.36.0")
        r = self.correr("--sha", v, api="http://127.0.0.1:1")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("falta el security check de metodo 0.36.0", r.stdout)
        self.assertIn("sin_check", r.stdout)                       # dice cómo forzar
        self.assertEqual(self._estable_remoto(), self.c[1])

    def test_automatico_sin_security_check_no_pasa(self):
        v = self._version("metodo", "0.36.0")
        self.srv.actividad = [evento(v, 50), evento(self.c[5], 60), evento(self.c[1], 100)]
        r = self.correr()
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("falta el security check de metodo 0.36.0", r.stdout)
        self.assertEqual(self._estable_remoto(), self.c[1])

    def _titulo(self, que, commit, veredicto="PASS"):
        return "### 2026-10-20 · %s (commit %s) — %s" % (que, commit[:7], veredicto)

    def _pasa(self, sha):
        r = self.correr("--sha", sha, api="http://127.0.0.1:1")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self._estable_remoto(), sha)
        return r

    def _no_pasa(self, sha):
        r = self.correr("--sha", sha, api="http://127.0.0.1:1")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("falta el security check", r.stdout)
        self.assertEqual(self._estable_remoto(), self.c[1])
        return r

    def test_check_anotado_despues_en_main_deja_pasar(self):
        v = self._version("metodo", "0.36.0")
        self._check(self._titulo("metodo 0.36.0", v))   # commit posterior: se lee de main, no del candidato
        r = self._pasa(v)
        self.assertIn("metodo 0.36.0 → «2026-10-20 · metodo 0.36.0 (commit %s) — PASS» en `docs/SECURITY-CHECKS.md` "
                      "(commit revisado `%s`)" % (v[:7], v[:7]), r.resumen)   # dice qué lo validó
        self.assertIn("sin_check=false", r.salida)

    def test_rango_en_el_titulo_cubre_y_se_compara_por_numero(self):
        v = self._version("metodo", "0.10.0")
        self._check(self._titulo("metodo 0.9.0 → 0.10.0 y paneles 0.3.0", v))   # 0.9.0 <= 0.10.0 por número (como texto, no)
        self._pasa(v)

    def test_rango_con_tope_que_el_commit_revisado_no_trae_no_cuenta(self):  # M-2b de la 2.ª revisión
        v = self._version("metodo", "0.36.0")
        self._check(self._titulo("metodo 0.35.0 → 0.40.0", v))   # cubriría 0.37…0.40 sin que nadie las revise
        self._no_pasa(v)

    def test_commit_revisado_con_otra_version_no_cuenta(self):  # M-2a de la 2.ª revisión
        viejo = self._version("metodo", "0.35.0")
        v = self._version("metodo", "0.36.0")
        self._check(self._titulo("metodo 0.36.0", viejo))   # ancestro, pero revisó 0.35.0
        self._no_pasa(v)

    def test_veredicto_que_no_esta_al_final_o_nombra_flag_critico_failed_no_cuenta(self):  # M-2c
        v = self._version("metodo", "0.36.0")
        for cola in ("PASS — revisar mañana", "17 PASS · 15 FLAG — PASS", "PASS salvo un crítico — PASS", "FAILED — PASS",
                     "PASS con condiciones (un critico abierto)", "PASS?"):
            self._check("### metodo 0.36.0 (commit %s) — %s" % (v[:7], cola))
        self._no_pasa(v)

    def test_veredicto_pass_con_condiciones_al_final_cuenta(self):  # M-2c
        v = self._version("metodo", "0.36.0")
        self._check("### metodo 0.36.0 (commit %s) — PASS con condiciones   " % v[:7])
        self._pasa(v)

    def test_titulo_dentro_de_un_comentario_html_no_cuenta(self):  # M-2d
        v = self._version("metodo", "0.36.0")
        self._check("<!--\n%s\n-->" % self._titulo("metodo 0.36.0", v))
        self._check("<!-- %s -->" % self._titulo("metodo 0.36.0", v))
        self._check("texto <!-- empieza\notra línea\n%s\nsigue -->" % self._titulo("metodo 0.36.0", v))
        self._no_pasa(v)

    def test_comentario_que_se_cierra_no_esconde_lo_que_sigue(self):  # M-2d, sin falsos negativos
        v = self._version("metodo", "0.36.0")
        self._check("<!-- nota\nvieja -->\n%s" % self._titulo("metodo 0.36.0", v))
        self._pasa(v)

    def test_estable_ilegible_no_traba_y_avisa(self):  # M-2b
        roto = self._archivo("plugins/metodo/.claude-plugin/plugin.json", "{roto", "estable con plugin.json roto")
        self._git(self.remoto, "update-ref", "refs/heads/estable", roto)
        v = self._version("metodo", "0.36.0")
        self._check(self._titulo("metodo 0.36.0", v))
        r = self.correr("--sha", v, api="http://127.0.0.1:1", extra_env={"GITHUB_ACTIONS": "true"})
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self._estable_remoto(), v)
        self.assertIn("::warning::estable: no se pudo leer metodo en estable", r.stdout)

    def test_estable_ilegible_y_sin_check_se_puede_forzar(self):  # M-2b
        roto = self._archivo("plugins/metodo/.claude-plugin/plugin.json", "{roto", "estable con plugin.json roto")
        self._git(self.remoto, "update-ref", "refs/heads/estable", roto)
        v = self._version("metodo", "0.36.0")
        r = self.correr("--sha", v, api="http://127.0.0.1:1")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("falta el security check de metodo 0.36.0", r.stdout)
        r = self.correr("--sha", v, "--sin-check", "urgente, estable estaba roto", api="http://127.0.0.1:1")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self._estable_remoto(), v)

    def test_lo_que_se_promueve_sigue_fallando_cerrado(self):  # M-2b: solo se perdona el estado viejo
        v = self._archivo("plugins/metodo/.claude-plugin/plugin.json", "{roto", "candidato roto")
        r = self.correr("--sha", v, "--sin-check", "esto no tiene que pasar", api="http://127.0.0.1:1")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertEqual(self._estable_remoto(), self.c[1])

    def test_rango_con_flecha_ascii_backticks_y_v(self):
        v = self._version("metodo", "0.36.0")
        self._check("## `metodo v0.35.1 -> v0.36.0` (commit `%s`) — PASS con condiciones" % v[:12])
        self._pasa(v)

    def test_check_de_otra_version_no_cubre(self):  # M2: exacta o rango, nunca «una más nueva» (un 3.50.0 tipeado mal lo apagaba)
        v = self._version("metodo", "0.36.0")
        self._check(self._titulo("metodo 3.50.0", v))
        self._check(self._titulo("metodo 0.35.9", v))
        self._no_pasa(v)

    def test_titulo_con_fail_o_sin_pass_no_cuenta(self):  # M2
        v = self._version("metodo", "0.36.0")
        self._check(self._titulo("metodo 0.36.0", v, "FAIL"))
        self._check(self._titulo("metodo 0.36.0", v, "PASS a medias, FAIL en Windows"))
        self._check(self._titulo("metodo 0.36.0", v, "NO PASS"))
        self._check("### 2026-10-20 · metodo 0.36.0 (commit %s) — pendiente" % v[:7])
        self._no_pasa(v)

    def test_titulo_sin_commit_o_con_dos_no_cuenta(self):  # M2
        v = self._version("metodo", "0.36.0")
        self._check("### 2026-10-20 · metodo 0.36.0 — PASS")
        self._check("### metodo 0.36.0 (commit %s, commit %s) — PASS" % (v[:7], self.c[1][:7]))
        self._no_pasa(v)

    def test_commit_revisado_que_no_es_ancestro_no_cuenta(self):  # M2
        v = self._version("metodo", "0.36.0")
        w = self._archivo("docs/despues.md", "x", "commit posterior al candidato")
        self._check(self._titulo("metodo 0.36.0", w))   # revisó algo que el candidato no tiene en su historia
        self._no_pasa(v)

    def test_commit_revisado_inexistente_no_cuenta(self):  # M2
        v = self._version("metodo", "0.36.0")
        self._check(self._titulo("metodo 0.36.0", "deadbeefdeadbeef"))
        self._no_pasa(v)

    def test_titulo_dentro_de_un_bloque_de_codigo_no_cuenta(self):  # M2
        v = self._version("metodo", "0.36.0")
        self._check("```markdown\n%s\n```" % self._titulo("metodo 0.36.0", v))
        self._check("~~~\n%s\n~~~" % self._titulo("metodo 0.36.0", v))
        self._no_pasa(v)

    def test_cambios_despues_del_commit_revisado_avisan(self):  # M2, refuerzo
        v = self._version("metodo", "0.36.0")
        w = self._archivo("plugins/metodo/scripts/agregado.py", "print(1)", "código después del check")
        self._check(self._titulo("metodo 0.36.0", v))
        r = self.correr("--sha", w, api="http://127.0.0.1:1", extra_env={"GITHUB_ACTIONS": "true"})
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("::warning::estable: hay cambios en plugins/metodo después del commit revisado", r.stdout)

    def test_otro_nombre_que_termina_en_metodo_no_cuenta(self):  # L6
        v = self._version("metodo", "0.36.0")
        self._check(self._titulo("escala-metodo 0.36.0", v))
        self._check(self._titulo("supermetodo 0.36.0", v))
        self._no_pasa(v)

    def test_version_con_sufijo_en_el_titulo_no_cuenta(self):
        v = self._version("metodo", "0.36.0")
        self._check(self._titulo("metodo 0.36.0-rc.1", v))
        self._check(self._titulo("metodo 0.36.0.1", v))
        self._no_pasa(v)

    def test_reporte_en_la_carpeta_de_checks_cuenta(self):
        v = self._version("metodo", "0.36.0")
        self._check("# Security check — claude-catalogo (metodo 0.36.0, commit %s) — 2026-10-20 — PASS" % v[:7],
                    ruta=".claude/security-checks/2026-10-20.md")
        self._pasa(v)

    def test_mencion_en_el_cuerpo_no_cuenta(self):
        v = self._version("metodo", "0.36.0")
        self._check(self._titulo("metodo 0.35.1", v), cuerpo="Condiciones para metodo 0.36.0 (commit %s): ninguna — PASS" % v[:7])
        self._no_pasa(v)

    def test_otro_paquete_con_el_mismo_numero_no_cubre(self):
        v = self._version("metodo", "0.3.0")
        self._check(self._titulo("paneles 0.3.0", v))
        self._no_pasa(v)

    def test_paneles_tambien_se_vigila(self):
        v = self._version("paneles", "0.3.0")
        r = self.correr("--sha", v, api="http://127.0.0.1:1")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("paneles 0.3.0", r.stdout)

    def test_otros_paquetes_no_piden_check(self):
        v = self._version("rubro-marketing", "9.9.9")
        r = self.correr("--sha", v, api="http://127.0.0.1:1")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("security check: no aplica", r.resumen)

    def test_misma_version_que_estable_no_pide_check(self):
        v = self._version("metodo", "0.36.0")
        self._git(self.remoto, "update-ref", "refs/heads/estable", v)   # ya está en estable (forzado antes)
        w = self._archivo("docs/otra-cosa.md", "x", "doc")
        r = self.correr("--sha", w, api="http://127.0.0.1:1")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self._estable_remoto(), w)

    def test_forzar_con_motivo_pasa_y_queda_registrado(self):
        v = self._version("metodo", "0.36.0")
        r = self.correr("--sha", v, "--sin-check", "arreglo urgente de un cliente", api="http://127.0.0.1:1",
                        extra_env={"GITHUB_ACTIONS": "true", "GITHUB_ACTOR": "fernando"})
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self._estable_remoto(), v)
        self.assertIn("::warning::estable: PROMOVIDO SIN SECURITY CHECK de metodo 0.36.0, por fernando. Motivo: arreglo urgente",
                      r.stdout)
        self.assertIn("PROMOVIDO SIN SECURITY CHECK", r.resumen)
        self.assertIn("Motivo: `arreglo urgente de un cliente`", r.resumen)   # Info8: entre backticks en el resumen
        self.assertIn("sin_check=true", r.salida)

    def test_motivo_con_backticks_no_rompe_el_resumen(self):  # Info8
        v = self._version("metodo", "0.36.0")
        r = self.correr("--sha", v, "--sin-check", "urgente `rm -rf` de mentira", api="http://127.0.0.1:1")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("Motivo: `urgente 'rm -rf' de mentira`", r.resumen)

    def test_forzar_sin_motivo_real_es_error_de_uso(self):
        v = self._version("metodo", "0.36.0")
        r = self.correr("--sha", v, "--sin-check", "x", api="http://127.0.0.1:1")
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)
        self.assertEqual(self._estable_remoto(), self.c[1])

    def test_el_motivo_no_arma_comandos_de_github(self):
        v = self._version("metodo", "0.36.0")
        r = self.correr("--sha", v, "--sin-check", "urgente de verdad\n::error::inventado", api="http://127.0.0.1:1",
                        extra_env={"GITHUB_ACTIONS": "true"})
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        comandos = [l for l in r.stdout.splitlines() if l.startswith("::")]
        self.assertEqual(len(comandos), 1, comandos)
        self.assertTrue(comandos[0].startswith("::warning::"))
        self.assertNotIn("::error::", comandos[0])

    def test_forzar_cuando_hay_check_no_anota_nada(self):
        v = self._version("metodo", "0.36.0")
        self._check(self._titulo("metodo 0.36.0", v))
        r = self.correr("--sha", v, "--sin-check", "por las dudas, igual", api="http://127.0.0.1:1")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn("PROMOVIDO SIN SECURITY CHECK", r.stdout + r.resumen)
        self.assertIn("sin_check=false", r.salida)

    # -- M1/L7 (revisión de la rama): falla cerrado --
    def _frena_manual(self, sha, texto):
        r = self.correr("--sha", sha, api="http://127.0.0.1:1")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn(texto, r.stdout)
        self.assertEqual(self._estable_remoto(), self.c[1])
        return r

    def test_version_que_no_es_x_y_z_frena(self):
        for raro in ("0.36.0-rc.1", "0.36.0+fix", "v0.36.0", "0.36"):
            with self.subTest(version=raro):
                v = self._version("metodo", raro)
                self._frena_manual(v, "versión que la compuerta no reconoce")

    def test_plugin_json_ilegible_o_sin_version_frena(self):
        v = self._archivo("plugins/metodo/.claude-plugin/plugin.json", "{roto", "roto")
        self._frena_manual(v, "no es JSON válido")
        w = self._archivo("plugins/metodo/.claude-plugin/plugin.json", json.dumps({"name": "metodo"}), "sin versión")
        self._frena_manual(w, "versión que la compuerta no reconoce")

    def test_carpeta_del_paquete_sin_plugin_json_frena(self):
        v = self._archivo("plugins/paneles/register.tsx", "x", "paneles sin manifiesto")
        self._frena_manual(v, "no tiene .claude-plugin/plugin.json")

    def _catalogo(self, entradas):
        return self._archivo(".claude-plugin/marketplace.json", json.dumps({"name": "c", "plugins": entradas}), "catálogo")

    def test_catalogo_que_apunta_afuera_frena(self):  # L7
        x = self._version("metodo", "0.36.0")
        self._check(self._titulo("metodo 0.36.0", x))
        v = self._catalogo([{"name": "metodo", "version": "0.36.0", "source": {"source": "github", "repo": "otro/repo"}}])
        self._frena_manual(v, "apunta a otra fuente")

    def test_catalogo_con_otra_version_frena(self):  # L7
        x = self._version("metodo", "0.36.0")
        self._check(self._titulo("metodo 0.36.0", x))
        v = self._catalogo([{"name": "metodo", "version": "0.35.0", "source": "./plugins/metodo"}])
        self._frena_manual(v, "no coincide con su plugin.json")

    def test_catalogo_coherente_pasa(self):  # L7
        x = self._version("metodo", "0.36.0")
        self._check(self._titulo("metodo 0.36.0", x))
        v = self._catalogo([{"name": "metodo", "version": "0.36.0", "source": "./plugins/metodo"},
                            {"name": "otro", "source": {"source": "github", "repo": "x/y"}}])   # los demás no se miran
        r = self.correr("--sha", v, api="http://127.0.0.1:1")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_codigo_cambiado_sin_subir_version_avisa_sin_frenar(self):  # M1, refuerzo
        v = self._version("metodo", "0.36.0")
        self._git(self.remoto, "update-ref", "refs/heads/estable", v)
        w = self._archivo("plugins/metodo/scripts/nuevo.py", "print('x')", "código sin versión nueva")
        r = self.correr("--sha", w, api="http://127.0.0.1:1", extra_env={"GITHUB_ACTIONS": "true"})
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("::warning::estable: cambió código de plugins/metodo", r.stdout)
        self.assertIn("sin subir la versión", r.resumen)

    def test_clon_superficial_se_rechaza(self):
        self._eventos_normales()
        r = self.correr(superficial=True)
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("superficial", r.stdout)
        self.assertEqual(self._estable_remoto(), self.c[1])

    def test_estable_inexistente_no_se_crea(self):
        self._git(self.remoto, "update-ref", "-d", "refs/heads/estable")
        self._eventos_normales()
        r = self.correr()
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("no existe", r.stdout)
        self.assertEqual(subprocess.run(["git", "-C", str(self.remoto), "rev-parse", "--verify", "-q", "refs/heads/estable"],
                                        stdout=subprocess.PIPE).returncode, 1)

    def test_arranque_imprime_el_commit_de_48_horas(self):
        self._eventos_normales()
        r = self.correr("--arranque")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(r.stdout.strip(), self.c[3])
        self.assertEqual(self._estable_remoto(), self.c[1])    # no empuja nada

    def test_arranque_sin_commits_de_48_horas_usa_el_mas_viejo_y_avisa(self):
        self.srv.actividad = [evento(self.c[5], 1), evento(self.c[4], 20)]
        r = self.correr("--arranque")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(r.stdout.strip(), self.c[4])
        self.assertIn("AVISO", r.stderr)

    def test_arranque_sin_actividad_falla(self):
        self.srv.actividad = []
        r = self.correr("--arranque")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertEqual(r.stdout.strip(), "")    # con --arranque, stdout lleva solo el sha: el error va por stderr
        self.assertIn("NO SE MOVIÓ", r.stderr)


# --------------------------------------------------------------------------- #
# Controles estáticos: workflow y rulesets
# --------------------------------------------------------------------------- #
class TestWorkflow(unittest.TestCase):
    def setUp(self):
        # Solo el código del workflow: los comentarios hablan de estas mismas cosas para explicarlas.
        lineas = WORKFLOW.read_text(encoding="utf-8").splitlines()
        self.texto = "\n".join(l for l in lineas if not l.lstrip().startswith("#"))

    def test_no_usa_pull_request_target(self):
        self.assertNotIn("pull_request_target", self.texto)

    def test_todas_las_actions_de_terceros_van_por_sha_de_40(self):
        usos = re.findall(r"^\s*-?\s*uses:\s*(\S+)", self.texto, re.M)
        self.assertTrue(usos)
        for uso in usos:
            self.assertRegex(uso, r"@[0-9a-f]{40}$", uso)

    def test_el_job_solo_lee_el_repositorio(self):
        # El push no usa la credencial del workflow: usa la clave de despliegue. Nada de escritura con el permiso del job.
        self.assertRegex(self.texto, r"(?m)^permissions:\s*\{\}\s*$")   # arriba: nada
        self.assertNotIn("contents: write", self.texto)
        self.assertNotIn("write-all", self.texto)
        self.assertEqual(self.texto.count("contents: read"), 1)
        self.assertNotIn("gh auth setup-git", self.texto)              # ya no se configura la credencial del workflow para git

    def _paso(self, nombre):
        """Texto de un paso (desde su `- name:` hasta el siguiente)."""
        partes = re.split(r"(?m)^      - ", self.texto)
        encontrados = [p for p in partes if p.startswith("name: " + nombre)]
        self.assertEqual(len(encontrados), 1, nombre)
        return encontrados[0]

    def test_el_job_usa_el_environment_estable(self):
        self.assertRegex(self.texto, r"(?m)^    environment:\s*estable\b")

    def test_el_secreto_solo_llega_al_paso_que_prepara_ssh(self):
        usos = re.findall(r"\$\{\{\s*secrets\.([A-Za-z0-9_]+)\s*\}\}", self.texto)
        self.assertEqual(usos, ["ESTABLE_DEPLOY_KEY"])          # el único secreto, una sola vez
        self.assertIn("secrets.ESTABLE_DEPLOY_KEY", self._paso("Preparar el push por SSH"))
        self.assertNotIn("secrets.", self._paso("Avanzar estable"))
        self.assertNotIn("ESTABLE_DEPLOY_KEY", self._paso("Avanzar estable"))
        # y nunca se imprime: solo se escribe a un archivo; sin echo, sin cat, sin trazas de bash
        for linea in self.texto.splitlines():
            if "ESTABLE_DEPLOY_KEY" in linea and "printf" in linea:
                self.assertRegex(linea, r'>\s*"\$d/id"\s*$')
            if "ESTABLE_DEPLOY_KEY" in linea and "::error::" not in linea:
                self.assertNotRegex(linea, r"\b(echo|cat|tee|set -x)\b")
        self.assertNotRegex(self.texto, r"set -[a-z]*x")

    def test_ssh_con_servidores_fijados_y_sin_preguntar(self):
        paso = self._paso("Preparar el push por SSH")
        self.assertIn("StrictHostKeyChecking=yes", paso)
        self.assertIn("UserKnownHostsFile=", paso)
        self.assertIn("IdentitiesOnly=yes", paso)
        self.assertNotIn("StrictHostKeyChecking=no", self.texto)
        self.assertNotIn("ssh-keyscan", self.texto)               # las claves del servidor no se piden en el momento
        self.assertIn('git remote set-url --push origin "git@github.com:${REPO}.git"', paso)
        self.assertIn("git config core.sshCommand", paso)          # solo para este repositorio: sin variables globales

    def test_las_claves_de_github_fijadas_son_las_publicadas(self):
        # Huellas oficiales (docs.github.com/authentication/.../githubs-ssh-key-fingerprints).
        publicadas = {
            "ssh-rsa": "uNiVztksCsDhcc0u9e8BujQXVUpKZIDTMczCvj3tD2s",
            "ecdsa-sha2-nistp256": "p2QAMXNIC1TJYWeIOttrVc98/R1BUFWu3/LiyKgUfQM",
            "ssh-ed25519": "+DiY3wvvV6TuJJhbpZisF/zLDA0zPMSvHdkr4UvCOqU",
        }
        lineas = re.findall(r"(?m)^\s*github\.com (ssh-[a-z0-9]+|ecdsa-sha2-nistp256) ([A-Za-z0-9+/=]+)\s*$", self.texto)
        self.assertEqual(sorted(t for t, _ in lineas), sorted(publicadas))   # exactamente esas tres, ni una más
        for tipo, clave in lineas:
            huella = base64.b64encode(hashlib.sha256(base64.b64decode(clave)).digest()).decode().rstrip("=")
            self.assertEqual(huella, publicadas[tipo], tipo)

    @unittest.skipIf(ES_WINDOWS, "el paso es de bash")
    def test_el_paso_de_ssh_escribe_la_clave_con_permiso_600_y_configura_git(self):
        paso = self._paso("Preparar el push por SSH")
        codigo = paso.split("run: |\n", 1)[1]
        codigo = "\n".join(l[10:] if l.startswith(" " * 10) else l for l in codigo.splitlines()) + "\n"
        with tempfile.TemporaryDirectory(prefix="estable ssh ") as tmp:
            repo, runner = Path(tmp) / "repo", Path(tmp) / "runner"
            repo.mkdir()
            runner.mkdir()
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            subprocess.run(["git", "-C", str(repo), "remote", "add", "origin", "https://github.com/dueno/repo"], check=True)
            env = dict(os.environ, RUNNER_TEMP=str(runner), REPO="dueno/repo", ESTABLE_DEPLOY_KEY="CLAVE DE PRUEBA\nSEGUNDA LINEA")
            r = subprocess.run(["bash", "-c", codigo], cwd=str(repo), env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               universal_newlines=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            carpeta = runner / "estable-ssh"
            self.assertEqual(oct(carpeta.stat().st_mode & 0o777), "0o700")
            self.assertEqual(oct((carpeta / "id").stat().st_mode & 0o777), "0o600")
            self.assertEqual((carpeta / "id").read_text(encoding="utf-8"), "CLAVE DE PRUEBA\nSEGUNDA LINEA\n")
            self.assertEqual(len((carpeta / "known_hosts").read_text(encoding="utf-8").splitlines()), 3)
            self.assertNotIn("CLAVE DE PRUEBA", r.stdout + r.stderr)             # nunca se imprime
            cfg = subprocess.run(["git", "-C", str(repo), "config", "core.sshCommand"], stdout=subprocess.PIPE,
                                 universal_newlines=True).stdout
            self.assertIn("StrictHostKeyChecking=yes", cfg)
            self.assertIn(str(carpeta / "known_hosts"), cfg)
            # Sin la configuración global del que corre la prueba (puede reescribir git@github.com: a https, como hace al-dia).
            limpio = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
            push = subprocess.run(["git", "-C", str(repo), "remote", "get-url", "--push", "origin"], stdout=subprocess.PIPE,
                                  env=limpio, universal_newlines=True).stdout.strip()
            fetch = subprocess.run(["git", "-C", str(repo), "remote", "get-url", "origin"], stdout=subprocess.PIPE,
                                   env=limpio, universal_newlines=True).stdout.strip()
            self.assertEqual(push, "git@github.com:dueno/repo.git")
            self.assertEqual(fetch, "https://github.com/dueno/repo")             # leer sigue siendo por HTTPS
            # sin el secreto, falla sin dejar nada
            env["ESTABLE_DEPLOY_KEY"] = ""
            runner2 = Path(tmp) / "runner2"
            runner2.mkdir()
            env["RUNNER_TEMP"] = str(runner2)
            r = subprocess.run(["bash", "-c", codigo], cwd=str(repo), env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               universal_newlines=True)
            self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
            self.assertFalse((runner2 / "estable-ssh").exists())

    def test_al_final_se_borra_la_clave_aunque_falle_algo(self):
        paso = self._paso("Borrar la clave del runner")
        self.assertIn("if: always()", paso)
        self.assertIn("rm -rf", paso)

    def test_disparos(self):
        self.assertRegex(self.texto, r"(?m)^\s+- cron:")
        self.assertIn("workflow_dispatch:", self.texto)
        self.assertRegex(self.texto, r"(?m)^\s+sha:\s*$")

    def test_el_sha_manual_entra_por_env_y_no_dentro_del_codigo(self):
        for n, linea in enumerate(self.texto.splitlines(), 1):
            if "github.event.inputs" in linea or "inputs.sha" in linea or "inputs.sin_check" in linea:
                self.assertRegex(linea, r"^\s+(SHA_MANUAL|MOTIVO_SIN_CHECK):\s*\$\{\{",
                                 "línea %d: la entrada va a una variable de entorno" % n)

    def test_sin_check_es_una_entrada_explicita_y_tolera_el_script_viejo(self):
        # F14: forzar sin security check es posible solo a propósito (entrada aparte) y no rompe mientras estable
        # todavía tenga el script sin la compuerta (el workflow es de main; el script, de estable).
        self.assertRegex(self.texto, r"(?m)^\s+sin_check:\s*$")
        paso = self._paso("Avanzar estable")
        self.assertIn("MOTIVO_SIN_CHECK: ${{ github.event.inputs.sin_check }}", paso)
        self.assertIn("grep -q -- '--sin-check'", paso)
        self.assertIn('args+=(--sin-check "$MOTIVO_SIN_CHECK")', paso)
        self.assertNotRegex(paso, r"echo[^\n]*MOTIVO_SIN_CHECK")   # el motivo no se imprime desde bash (lo limpia el script)

    def test_solo_corre_sobre_main(self):
        self.assertIn("github.ref == 'refs/heads/main'", self.texto)

    def test_el_checkout_es_de_estable_no_de_main(self):
        # El script que decide es código que ya esperó 48 h: lo recién publicado en main no cambia la lógica de promoción.
        self.assertRegex(self.texto, r"(?m)^\s+ref:\s*estable\b")
        self.assertNotRegex(self.texto, r"(?m)^\s+ref:\s*(?!estable\b)\S+")

    def test_historial_completo_y_sin_credencial_guardada(self):
        self.assertIn("fetch-depth: 0", self.texto)
        self.assertIn("persist-credentials: false", self.texto)

    def test_una_corrida_a_la_vez(self):
        self.assertIn("concurrency:", self.texto)
        self.assertIn("cancel-in-progress: false", self.texto)


class TestRulesets(unittest.TestCase):
    ARCHIVOS = ("estable-intocable.json", "proteger-estable.json", "tags-estable.json", "ramas-estable.json")
    # En un repositorio personal GitHub no deja poner a GitHub Actions como excepción (422): la única excepción posible
    # es una clave de despliegue (deploy key), y su actor_id va en null.
    CLAVE_DE_DESPLIEGUE = {"actor_id": None, "actor_type": "DeployKey", "bypass_mode": "always"}

    def cargar(self, nombre):
        return json.loads((RULESETS / nombre).read_text(encoding="utf-8"))

    def tipos(self, rs):
        return sorted(r["type"] for r in rs["rules"])

    def test_estable_intocable_nadie_la_borra_ni_la_fuerza(self):
        rs = self.cargar("estable-intocable.json")
        self.assertEqual(rs["target"], "branch")
        self.assertEqual(rs["enforcement"], "active")
        self.assertEqual(rs["conditions"]["ref_name"], {"include": ["refs/heads/estable"], "exclude": []})
        self.assertEqual(self.tipos(rs), ["deletion", "non_fast_forward"])
        self.assertEqual(rs["bypass_actors"], [])    # ni siquiera GitHub Actions: sin excepciones

    def test_proteger_estable_solo_una_clave_de_despliegue_la_crea_o_la_mueve(self):
        rs = self.cargar("proteger-estable.json")
        self.assertEqual(rs["target"], "branch")
        self.assertEqual(rs["enforcement"], "active")
        self.assertEqual(rs["conditions"]["ref_name"], {"include": ["refs/heads/estable"], "exclude": []})
        self.assertEqual(self.tipos(rs), ["creation", "update"])
        self.assertEqual(rs["bypass_actors"], [self.CLAVE_DE_DESPLIEGUE])   # nadie más (sin administradores ni roles exentos)

    def test_tags_con_estable_en_el_nombre_prohibidos_sin_excepciones(self):
        rs = self.cargar("tags-estable.json")
        self.assertEqual(rs["target"], "tag")
        self.assertEqual(rs["enforcement"], "active")
        self.assertEqual(rs["conditions"]["ref_name"]["include"], ["refs/tags/*estable*"])
        self.assertEqual(self.tipos(rs), ["creation", "deletion", "update"])
        self.assertEqual(rs["bypass_actors"], [])

    def test_otras_ramas_con_estable_en_el_nombre_no_se_pueden_crear(self):
        rs = self.cargar("ramas-estable.json")
        self.assertEqual(rs["target"], "branch")
        self.assertEqual(rs["enforcement"], "active")
        self.assertEqual(rs["conditions"]["ref_name"]["include"], ["refs/heads/*estable*"])
        self.assertEqual(rs["conditions"]["ref_name"]["exclude"], ["refs/heads/estable"])
        self.assertEqual(self.tipos(rs), ["creation"])
        self.assertEqual(rs["bypass_actors"], [])

    def test_nombres_distintos_y_solo_uno_con_excepcion(self):
        todos = [self.cargar(n) for n in self.ARCHIVOS]
        self.assertEqual(len({r["name"] for r in todos}), len(self.ARCHIVOS))
        con_excepcion = [r["name"] for r in todos if r["bypass_actors"]]
        self.assertEqual(con_excepcion, ["proteger-estable"])

    def test_ningun_ruleset_nombra_a_github_actions_como_excepcion(self):
        for n in self.ARCHIVOS:
            for actor in self.cargar(n)["bypass_actors"]:
                self.assertNotEqual(actor["actor_type"], "Integration", n)
                self.assertNotIn(15368, [actor.get("actor_id")], n)

    def test_no_queda_el_ruleset_viejo_sin_partir(self):
        self.assertFalse((RULESETS / "estable.json").exists())
        self.assertEqual(sorted(p.name for p in RULESETS.glob("*.json")), sorted(self.ARCHIVOS))


if __name__ == "__main__":
    unittest.main()
