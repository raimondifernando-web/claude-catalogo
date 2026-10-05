"""Pruebas de la rama `estable`: scripts/estable-avanzar.py (con un repo git local de mentira y la API de GitHub simulada
en un servidor local) y los controles estáticos de .github/workflows/estable.yml y .github/rulesets/*.json.

Correr desde la raíz del repo:
    python3 -m unittest discover -s plugins/metodo/scripts/tests -p 'test_estable.py' -v
Sin red real, sin credenciales: nada de esto toca GitHub.
"""
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

    def _clon_de_trabajo(self, superficial=False):
        trabajo = self.dir / "trabajo"
        if trabajo.exists():
            return trabajo
        if superficial:
            self._git(self.dir, "clone", "--quiet", "--depth", "1", "file://" + str(self.remoto), str(trabajo))
        else:
            self._git(self.dir, "clone", "--quiet", str(self.remoto), str(trabajo))
        return trabajo

    def _estable_remoto(self):
        return self._git(self.remoto, "rev-parse", "refs/heads/estable")

    def _eventos_normales(self):
        # c1 hace 100 h, c2 60 h, c3 50 h (>= 48), c4 47 h, c5 1 h
        self.srv.actividad = [evento(self.c[5], 1), evento(self.c[4], 47), evento(self.c[3], 50),
                              evento(self.c[2], 60), evento(self.c[1], 100)]

    def correr(self, *args, superficial=False, api=None):
        trabajo = self._clon_de_trabajo(superficial)
        salida, resumen = self.dir / "out.txt", self.dir / "resumen.md"
        env = {k: v for k, v in os.environ.items() if k not in ("GH_TOKEN", "GITHUB_TOKEN", "GITHUB_ACTIONS")}
        env.update(GIT_TERMINAL_PROMPT="0", GITHUB_OUTPUT=str(salida), GITHUB_STEP_SUMMARY=str(resumen))
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
        self.assertEqual(self.srv.pedidos, ["/repos/dueno/repo/activity?ref=refs/heads/main&per_page=100"])

    def test_sin_push_decide_pero_no_empuja(self):
        self._eventos_normales()
        r = self.correr("--sin-push")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self._estable_remoto(), self.c[1])
        self.assertIn("se movería", r.stdout)

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

    def test_permiso_de_escritura_solo_en_el_job(self):
        self.assertRegex(self.texto, r"(?m)^permissions:\s*\{\}\s*$")   # arriba: nada
        self.assertEqual(self.texto.count("contents: write"), 1)
        self.assertNotIn("write-all", self.texto)
        self.assertNotRegex(self.texto, r"(?m)^permissions:\s*\n\s+contents: write")  # no a nivel de workflow

    def test_disparos(self):
        self.assertRegex(self.texto, r"(?m)^\s+- cron:")
        self.assertIn("workflow_dispatch:", self.texto)
        self.assertRegex(self.texto, r"(?m)^\s+sha:\s*$")

    def test_el_sha_manual_entra_por_env_y_no_dentro_del_codigo(self):
        for n, linea in enumerate(self.texto.splitlines(), 1):
            if "github.event.inputs" in linea or "inputs.sha" in linea:
                self.assertRegex(linea, r"^\s+SHA_MANUAL:\s*\$\{\{", "línea %d: la entrada va a una variable de entorno" % n)

    def test_solo_corre_sobre_main(self):
        self.assertIn("github.ref == 'refs/heads/main'", self.texto)

    def test_historial_completo_y_sin_credencial_guardada(self):
        self.assertIn("fetch-depth: 0", self.texto)
        self.assertIn("persist-credentials: false", self.texto)

    def test_una_corrida_a_la_vez(self):
        self.assertIn("concurrency:", self.texto)
        self.assertIn("cancel-in-progress: false", self.texto)


class TestRulesets(unittest.TestCase):
    def cargar(self, nombre):
        return json.loads((RULESETS / nombre).read_text(encoding="utf-8"))

    def tipos(self, rs):
        return sorted(r["type"] for r in rs["rules"])

    def test_estable_sin_borrado_sin_force_y_solo_actions_empuja(self):
        rs = self.cargar("estable.json")
        self.assertEqual(rs["target"], "branch")
        self.assertEqual(rs["enforcement"], "active")
        self.assertEqual(rs["conditions"]["ref_name"]["include"], ["refs/heads/estable"])
        self.assertEqual(self.tipos(rs), ["deletion", "non_fast_forward", "update"])
        # GitHub Actions = integración 15368; nadie más (sin admins ni roles exentos).
        self.assertEqual(rs["bypass_actors"], [{"actor_id": 15368, "actor_type": "Integration", "bypass_mode": "always"}])

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

    def test_nombres_distintos(self):
        nombres = [self.cargar(n)["name"] for n in ("estable.json", "tags-estable.json", "ramas-estable.json")]
        self.assertEqual(len(set(nombres)), 3)


if __name__ == "__main__":
    unittest.main()
