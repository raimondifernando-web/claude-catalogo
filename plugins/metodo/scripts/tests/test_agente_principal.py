"""agente-principal.py (la sesión principal de una carpeta arranca como su jefe de proyecto): fusión sin perder claves,
idempotencia, 0/1/varios PM, JSON roto, deshacer (y que no se vuelva a aplicar), variantes de `tools:`, copias de
trabajo (hijas), respeto de un `agent` ya elegido, git que no versiona el archivo, modo hook, rutas y BOM de Windows,
compatibilidad con Python 3.9.
Disparador: encadenado — python3 -m unittest discover -s plugins/metodo/scripts/tests."""
import ast
import contextlib
import importlib.util
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

RUTA = Path(__file__).resolve().parents[1] / "agente-principal.py"
_spec = importlib.util.spec_from_file_location("agente_principal", str(RUTA))
ap = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ap)

HAY_GIT = shutil.which("git") is not None


def pm_texto(nombre="pm-uno", tools=None, nl="\n"):
    cab = ["---", "name: %s" % nombre, "description: PM de prueba"]
    if tools is not None:
        cab += tools if isinstance(tools, list) else ["tools: %s" % tools]
    cab += ["---", "Cuerpo del PM."]
    return nl.join(cab) + nl


def lee(ruta):
    with open(ruta, encoding="utf-8") as f:
        return f.read()


def git(cwd, *args):
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", "-c", "commit.gpgsign=false"] + list(args),
                   cwd=cwd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


class Base(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.h = os.path.realpath(self.t.name)
        self.cfg = os.path.join(self.h, "cfg")
        os.makedirs(self.cfg)
        self.casa = os.path.join(self.h, "casa")
        os.makedirs(self.casa)
        self.viejo = {k: os.environ.get(k) for k in ("CLAUDE_CONFIG_DIR", "HOME", "USERPROFILE", "AGENTE_PRINCIPAL_OFF")}
        os.environ["CLAUDE_CONFIG_DIR"] = self.cfg
        os.environ["HOME"] = os.environ["USERPROFILE"] = self.casa
        os.environ.pop("AGENTE_PRINCIPAL_OFF", None)
        self.c = os.path.join(self.h, "Proyecto")
        os.makedirs(os.path.join(self.c, ".claude", "agents"))

    def tearDown(self):
        for k, v in self.viejo.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        self.t.cleanup()

    def pm(self, nombre="pm-uno", archivo=None, **kw):
        ruta = os.path.join(self.c, ".claude", "agents", (archivo or nombre) + ".md")
        with open(ruta, "w", encoding="utf-8", newline="") as f:
            f.write(pm_texto(nombre, **kw))
        return ruta

    def ajustes(self, nombre="settings.local.json"):
        return os.path.join(self.c, ".claude", nombre)

    def leer(self, ruta):
        with open(ruta, "rb") as f:
            return f.read().decode("utf-8-sig")

    def json_de(self, ruta):
        return json.loads(self.leer(ruta))

    def escribir(self, ruta, texto, bom=False):
        with open(ruta, "wb") as f:
            f.write((b"\xef\xbb\xbf" if bom else b"") + texto.encode("utf-8"))

    def cli(self, *args):
        """Corre main() y devuelve (código, salida)."""
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = ap.main(list(args))
        return rc, buf.getvalue()

    def hook(self, cwd=None, **extra):
        datos = {"cwd": cwd or self.c, "source": "startup"}
        datos.update(extra)
        buf = io.StringIO()
        viejo = sys.stdin
        sys.stdin = io.StringIO(json.dumps(datos))
        try:
            with contextlib.redirect_stdout(buf):
                ap.modo_hook()
        finally:
            sys.stdin = viejo
        return buf.getvalue()


class Fusion(Base):
    def test_agrega_agent_sin_perder_claves_ni_orden(self):
        self.pm()
        self.escribir(self.ajustes(), json.dumps({"permissions": {"allow": ["Bash(ls)"]}, "model": "sonnet", "ñ": "ü"}))
        rc, out = self.cli("--carpeta", self.c)
        self.assertEqual(rc, 0, out)
        d = self.json_de(self.ajustes())
        self.assertEqual(d["agent"], "pm-uno")
        self.assertEqual(d["permissions"], {"allow": ["Bash(ls)"]})
        self.assertEqual((d["model"], d["ñ"]), ("sonnet", "ü"))
        self.assertEqual(list(d)[:3], ["permissions", "model", "ñ"])
        self.assertTrue(out.rstrip().endswith("Todo al día ✓"), out)

    def test_crea_el_archivo_si_no_existe(self):
        self.pm()
        self.cli("--carpeta", self.c)
        self.assertEqual(self.json_de(self.ajustes()), {"agent": "pm-uno"})

    def test_no_toca_settings_json_versionable(self):
        self.pm()
        self.escribir(self.ajustes("settings.json"), '{"extraKnownMarketplaces": {}}')
        antes = self.leer(self.ajustes("settings.json"))
        self.cli("--carpeta", self.c)
        self.assertEqual(self.leer(self.ajustes("settings.json")), antes)

    def test_idempotente(self):
        self.pm(tools="Read, Grep")
        self.cli("--carpeta", self.c)
        a, b = self.leer(self.ajustes()), self.leer(os.path.join(self.c, ".claude", "agents", "pm-uno.md"))
        copias = sorted(os.listdir(os.path.join(self.cfg, "metodo", "agente-principal-copias")))
        r = ap.aplicar(self.c)
        self.assertFalse(r.cambio)
        self.assertEqual(self.leer(self.ajustes()), a)
        self.assertEqual(self.leer(os.path.join(self.c, ".claude", "agents", "pm-uno.md")), b)
        self.assertEqual(sorted(os.listdir(os.path.join(self.cfg, "metodo", "agente-principal-copias"))), copias)
        rc, out = self.cli("--carpeta", self.c)
        self.assertEqual(rc, 0)
        self.assertIn("ya está", out)

    def test_simular_no_escribe(self):
        self.pm(tools="Read")
        rc, out = self.cli("--simular", "--carpeta", self.c)
        self.assertEqual(rc, 0)
        self.assertFalse(os.path.exists(self.ajustes()))
        self.assertNotIn("Agent", self.leer(os.path.join(self.c, ".claude", "agents", "pm-uno.md")))
        self.assertFalse(os.path.exists(os.path.join(self.cfg, "metodo", "agente-principal.json")))
        self.assertIn("Solo miré", out)

    def test_bom_y_acentos_de_windows(self):
        self.pm()
        self.escribir(self.ajustes(), '{"nota": "acción ñ"}', bom=True)
        self.cli("--carpeta", self.c)
        d = self.json_de(self.ajustes())
        self.assertEqual(d["nota"], "acción ñ")
        self.assertEqual(d["agent"], "pm-uno")

    def test_usa_el_name_de_la_cabecera_no_el_nombre_del_archivo(self):
        self.pm(nombre="pm-de-verdad", archivo="pm-otro-nombre")
        self.cli("--carpeta", self.c)
        self.assertEqual(self.json_de(self.ajustes())["agent"], "pm-de-verdad")


class CuantosPM(Base):
    def test_sin_pm_no_hace_nada(self):
        rc, out = self.cli("--carpeta", self.c)
        self.assertEqual(rc, 0)
        self.assertFalse(os.path.exists(self.ajustes()))
        self.assertIn("Sin cambios ✓", out)
        self.assertIn("no hay un jefe de proyecto", out)

    def test_varios_pm_no_elige(self):
        self.pm("pm-uno")
        self.pm("pm-dos")
        rc, out = self.cli("--carpeta", self.c)
        self.assertEqual(rc, 0)
        self.assertFalse(os.path.exists(self.ajustes()))
        self.assertIn("hay 2 jefes de proyecto", out)

    def test_un_especialista_no_es_pm(self):
        self.pm("redactor")
        r = ap.aplicar(self.c)
        self.assertFalse(r.cambio)

    def test_carpeta_inexistente(self):
        rc, out = self.cli("--carpeta", os.path.join(self.h, "no-existe"))
        self.assertEqual(rc, 1)
        self.assertIn("Falta:", out)

    def test_la_carpeta_personal_no(self):
        os.makedirs(os.path.join(self.casa, ".claude", "agents"))
        with open(os.path.join(self.casa, ".claude", "agents", "pm-yo.md"), "w", encoding="utf-8") as f:
            f.write(pm_texto("pm-yo"))
        r = ap.aplicar(self.casa)
        self.assertFalse(r.cambio)
        self.assertIn("personal", r.motivo_nada)


class CabeceraQueEjecuta(Base):
    """Una carpeta ajena (un repo bajado) con un pm-*.md que trae hooks, servidores o permisos no se activa sola."""
    def test_no_activa_un_pm_con_campos_que_ejecutan(self):
        for campo in ("hooks:", "mcpServers:", "permissionMode: bypassPermissions", "initialPrompt: hacé algo", "background: true", "isolation: worktree"):
            with self.subTest(campo=campo):
                self.pm(tools=[campo])
                rc, out = self.cli("--carpeta", self.c)
                self.assertEqual(rc, 0)
                self.assertIn("no lo activo solo", out)
                self.assertFalse(os.path.exists(self.ajustes()))
                self.assertEqual(self.hook(), "")

    def test_un_pm_normal_si(self):
        self.pm(tools=["model: sonnet", "skills:", "  - planning-with-files"])
        self.cli("--carpeta", self.c)
        self.assertEqual(self.json_de(self.ajustes())["agent"], "pm-uno")

    def test_la_palabra_en_el_cuerpo_no_cuenta(self):
        ruta = self.pm()
        with open(ruta, "a", encoding="utf-8") as f:
            f.write("hooks: esto es texto del cuerpo\n")
        self.cli("--carpeta", self.c)
        self.assertEqual(self.json_de(self.ajustes())["agent"], "pm-uno")


class JsonRoto(Base):
    def test_json_roto_no_se_toca(self):
        self.pm()
        self.escribir(self.ajustes(), '{"permissions": ')
        rc, out = self.cli("--carpeta", self.c)
        self.assertEqual(rc, 1)
        self.assertIn("Falta:", out)
        self.assertEqual(self.leer(self.ajustes()), '{"permissions": ')
        self.assertFalse(os.path.exists(os.path.join(self.cfg, "metodo", "agente-principal.json")))

    def test_json_que_no_es_objeto(self):
        self.pm()
        self.escribir(self.ajustes(), "[1, 2]")
        rc, _ = self.cli("--carpeta", self.c)
        self.assertEqual(rc, 1)
        self.assertEqual(self.leer(self.ajustes()), "[1, 2]")

    def test_archivo_vacio_vale_como_objeto_vacio(self):
        self.pm()
        self.escribir(self.ajustes(), "")
        rc, _ = self.cli("--carpeta", self.c)
        self.assertEqual(rc, 0)
        self.assertEqual(self.json_de(self.ajustes()), {"agent": "pm-uno"})


class Herramientas(unittest.TestCase):
    def arreglar(self, tools, nl="\n"):
        return ap.arreglar_tools(pm_texto(tools=tools, nl=nl))[:3]

    def test_en_linea(self):
        t, cambio, _ = self.arreglar("Read, Grep")
        self.assertTrue(cambio)
        self.assertIn("tools: Read, Grep, Agent\n", t)

    def test_entre_corchetes(self):
        t, cambio, _ = self.arreglar("[Read, Grep]")
        self.assertTrue(cambio)
        self.assertIn("tools: [Read, Grep, Agent]\n", t)

    def test_lista_en_bloque(self):
        t, cambio, _ = self.arreglar(["tools:", "  - Read", "  - Grep"])
        self.assertTrue(cambio)
        self.assertIn("  - Read\n  - Grep\n  - Agent\n---", t)

    def test_ya_trae_agent(self):
        for v in ("Read, Agent", "Agent(pm-x), Read", "*", "[Read, Agent]"):
            self.assertFalse(self.arreglar(v)[1], v)
        self.assertFalse(self.arreglar(["tools:", "  - Read", "  - Agent"])[1])

    def test_sin_lista_hereda_todo(self):
        t, cambio, nota, sirve = ap.arreglar_tools(pm_texto())
        self.assertTrue(sirve)
        self.assertFalse(cambio)
        self.assertIn("hereda", nota)

    def test_entre_comillas_no_se_toca(self):
        self.assertFalse(self.arreglar('"Read, Grep"')[1])

    def test_conserva_finales_de_linea_windows(self):
        t, cambio, _ = self.arreglar("Read", nl="\r\n")
        self.assertTrue(cambio)
        self.assertIn("tools: Read, Agent\r\n", t)
        self.assertEqual(t.count("\n"), t.count("\r\n"))

    def test_sin_cabecera(self):
        self.assertFalse(ap.arreglar_tools("solo texto\n")[1])

    def test_aplicar_suma_agent_con_copia_afuera_del_proyecto(self):
        with tempfile.TemporaryDirectory() as t:
            h = os.path.realpath(t)
            viejo = os.environ.get("CLAUDE_CONFIG_DIR")
            os.environ["CLAUDE_CONFIG_DIR"] = os.path.join(h, "cfg")
            try:
                c = os.path.join(h, "P")
                os.makedirs(os.path.join(c, ".claude", "agents"))
                ruta = os.path.join(c, ".claude", "agents", "pm-uno.md")
                with open(ruta, "w", encoding="utf-8") as f:
                    f.write(pm_texto(tools="Read, Grep"))
                antes = lee(ruta)
                ap.aplicar(c)
                self.assertIn("Read, Grep, Agent", lee(ruta))
                self.assertEqual(sorted(os.listdir(os.path.join(c, ".claude"))), ["agents", "settings.local.json"])
                self.assertEqual(sorted(os.listdir(os.path.join(c, ".claude", "agents"))), ["pm-uno.md"])
                copias = [os.path.join(dp, f) for dp, _, fs in os.walk(os.path.join(h, "cfg")) for f in fs if ".md.antes." in f]
                self.assertEqual(len(copias), 1)
                self.assertEqual(lee(copias[0]), antes)
            finally:
                if viejo is None:
                    os.environ.pop("CLAUDE_CONFIG_DIR", None)
                else:
                    os.environ["CLAUDE_CONFIG_DIR"] = viejo


class Deshacer(Base):
    def test_saca_agent_y_deja_lo_demas(self):
        self.pm()
        self.escribir(self.ajustes(), json.dumps({"model": "sonnet"}))
        self.cli("--carpeta", self.c)
        rc, out = self.cli("--deshacer", "--carpeta", self.c)
        self.assertEqual(rc, 0, out)
        self.assertEqual(self.json_de(self.ajustes()), {"model": "sonnet"})

    def test_borra_el_archivo_que_creo_si_queda_vacio(self):
        self.pm()
        self.cli("--carpeta", self.c)
        self.assertTrue(os.path.exists(self.ajustes()))
        self.cli("--deshacer", "--carpeta", self.c)
        self.assertFalse(os.path.exists(self.ajustes()))

    def test_devuelve_la_lista_de_herramientas(self):
        ruta = self.pm(tools="Read, Grep")
        antes = self.leer(ruta)
        self.cli("--carpeta", self.c)
        self.assertNotEqual(self.leer(ruta), antes)
        self.cli("--deshacer", "--carpeta", self.c)
        self.assertEqual(self.leer(ruta), antes)

    def test_si_el_pm_cambio_despues_no_le_toca_las_herramientas(self):
        ruta = self.pm(tools="Read, Grep")
        self.cli("--carpeta", self.c)
        with open(ruta, "a", encoding="utf-8") as f:
            f.write("Una línea nueva de la persona.\n")
        editado = self.leer(ruta)
        rc, out = self.cli("--deshacer", "--carpeta", self.c)
        self.assertEqual(rc, 0)
        self.assertEqual(self.leer(ruta), editado)
        self.assertIn("cambió desde entonces", out)

    def test_no_saca_un_agent_que_puso_otra_persona(self):
        self.pm()
        self.escribir(self.ajustes(), json.dumps({"agent": "pm-uno", "x": 1}))
        self.cli("--carpeta", self.c)    # ya estaba: no aplica ni anota
        self.cli("--deshacer", "--carpeta", self.c)
        self.assertEqual(self.json_de(self.ajustes())["agent"], "pm-uno")

    def test_despues_de_deshacer_el_hook_no_lo_vuelve_a_poner(self):
        self.pm()
        self.assertIn("PRÓXIMA sesión", self.hook())
        self.cli("--deshacer", "--carpeta", self.c)
        self.assertEqual(self.hook(), "")
        self.assertFalse(os.path.exists(self.ajustes()))

    def test_pedido_explicito_vuelve_a_aplicar(self):
        self.pm()
        self.cli("--carpeta", self.c)
        self.cli("--deshacer", "--carpeta", self.c)
        rc, _ = self.cli("--carpeta", self.c)
        self.assertEqual(rc, 0)
        self.assertEqual(self.json_de(self.ajustes())["agent"], "pm-uno")

    def test_deshacer_sin_haber_aplicado_anota_el_rechazo(self):
        self.pm()
        rc, out = self.cli("--deshacer", "--carpeta", self.c)
        self.assertEqual(rc, 0)
        self.assertEqual(self.hook(), "")
        self.assertFalse(os.path.exists(self.ajustes()))


class YaElegido(Base):
    def test_respeta_agent_de_settings_json(self):
        self.pm()
        self.escribir(self.ajustes("settings.json"), json.dumps({"agent": "otro"}))
        r = ap.aplicar(self.c)
        self.assertFalse(r.cambio)
        self.assertIn("lo respeto", r.motivo_nada)
        self.assertFalse(os.path.exists(self.ajustes()))

    def test_respeta_agent_de_la_persona_en_su_config_global(self):
        self.pm()
        self.escribir(os.path.join(self.cfg, "settings.json"), json.dumps({"agent": "mi-agente"}))
        r = ap.aplicar(self.c)
        self.assertFalse(r.cambio)
        self.assertIn("mi-agente", r.motivo_nada)

    def test_mismo_agent_en_settings_json_no_duplica(self):
        self.pm()
        self.escribir(self.ajustes("settings.json"), json.dumps({"agent": "pm-uno"}))
        r = ap.aplicar(self.c)
        self.assertFalse(r.cambio)
        self.assertFalse(os.path.exists(self.ajustes()))


@unittest.skipUnless(HAY_GIT, "sin git")
class ConGit(Base):
    def repo(self):
        git(self.c, "init", "-q")
        git(self.c, "add", "-A")
        git(self.c, "commit", "-q", "-m", "i", "--allow-empty")

    def estado(self):
        r = subprocess.run(["git", "status", "--porcelain"], cwd=self.c, stdout=subprocess.PIPE, universal_newlines=True)
        return r.stdout

    def test_git_no_ve_el_archivo_de_ajustes(self):
        self.pm()
        self.repo()
        ap.aplicar(self.c)
        self.assertNotIn("settings.local.json", self.estado())
        ex = subprocess.run(["git", "rev-parse", "--git-path", "info/exclude"], cwd=self.c, stdout=subprocess.PIPE, universal_newlines=True).stdout.strip()
        self.assertIn(ap.PATRON_EXCLUDE, lee(os.path.join(self.c, ex)).splitlines())

    def test_no_repite_la_linea_en_exclude(self):
        self.pm()
        self.repo()
        ap.aplicar(self.c)
        ap.deshacer(self.c)
        ap.aplicar(self.c, forzar=True)
        ex = subprocess.run(["git", "rev-parse", "--git-path", "info/exclude"], cwd=self.c, stdout=subprocess.PIPE, universal_newlines=True).stdout.strip()
        self.assertEqual(lee(os.path.join(self.c, ex)).splitlines().count(ap.PATRON_EXCLUDE), 1)

    def test_si_el_archivo_esta_versionado_no_lo_toca(self):
        self.pm()
        self.escribir(self.ajustes(), '{"x": 1}')
        git(self.c, "init", "-q")
        git(self.c, "add", "-f", "-A")
        git(self.c, "commit", "-q", "-m", "i")
        r = ap.aplicar(self.c)
        self.assertFalse(r.cambio)
        self.assertIn("versionado", r.motivo_nada)
        self.assertEqual(self.json_de(self.ajustes()), {"x": 1})

    def test_en_copia_de_trabajo_no_aplica(self):
        self.pm()
        self.repo()
        wt = os.path.join(self.h, "copia")
        git(self.c, "worktree", "add", "-q", wt, "-b", "hija")
        r = ap.aplicar(wt)
        self.assertFalse(r.cambio)
        self.assertIn("copia de trabajo", r.motivo_nada)
        self.assertFalse(os.path.exists(os.path.join(wt, ".claude", "settings.local.json")))

    def test_hook_en_copia_de_trabajo_avisa_que_es_hija_si_heredo_pm(self):
        self.pm()
        self.repo()
        ap.aplicar(self.c)
        wt = os.path.join(self.h, "copia")
        git(self.c, "worktree", "add", "-q", wt, "-b", "hija")
        out = self.hook(cwd=wt)
        self.assertIn("HIJA", out)
        self.assertIn("pm-uno", out)
        self.assertNotIn("PRÓXIMA", out)

    def test_hook_en_copia_de_trabajo_con_agent_type(self):
        self.pm()
        self.repo()
        wt = os.path.join(self.h, "copia")
        git(self.c, "worktree", "add", "-q", wt, "-b", "hija")
        self.assertIn("pm-x", self.hook(cwd=wt, agent_type="pm-x"))
        self.assertEqual(self.hook(cwd=wt, agent_type="code-reviewer"), "")

    def test_hook_en_copia_de_trabajo_sin_pm_heredado_calla(self):
        self.pm()
        self.repo()
        wt = os.path.join(self.h, "copia")
        git(self.c, "worktree", "add", "-q", wt, "-b", "hija")
        self.assertEqual(self.hook(cwd=wt), "")

    def test_subcarpeta_de_un_repo_usa_su_propio_archivo(self):
        git(self.h, "init", "-q")
        self.pm()
        ap.aplicar(self.c)
        self.assertTrue(os.path.exists(self.ajustes()))
        self.assertFalse(os.path.exists(os.path.join(self.h, ".claude", "settings.local.json")))


class Hook(Base):
    def test_aplica_una_vez_y_avisa_en_criollo(self):
        self.pm()
        out = self.hook()
        self.assertIn("pm-uno", out)
        self.assertIn("PRÓXIMA sesión", out)
        self.assertIn("--deshacer", out)
        self.assertEqual(self.json_de(self.ajustes())["agent"], "pm-uno")
        self.assertEqual(self.hook(), "")     # la segunda vez calla

    def test_solo_al_abrir_una_sesion_nueva(self):
        self.pm()
        for fuente in ("resume", "clear", "compact", "fork"):
            self.assertEqual(self.hook(source=fuente), "", fuente)
        self.assertFalse(os.path.exists(self.ajustes()))

    def test_apagado_por_archivo_y_por_variable(self):
        self.pm()
        os.makedirs(os.path.join(self.cfg, "metodo"))
        open(os.path.join(self.cfg, "metodo", "agente-principal.apagado"), "w").close()
        self.assertEqual(self.hook(), "")
        os.remove(os.path.join(self.cfg, "metodo", "agente-principal.apagado"))
        os.environ["AGENTE_PRINCIPAL_OFF"] = "1"
        self.assertEqual(self.hook(), "")
        self.assertFalse(os.path.exists(self.ajustes()))

    def test_nunca_falla_ni_con_entrada_rota(self):
        viejo = sys.stdin
        sys.stdin = io.StringIO("esto no es json")
        try:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                ap.modo_hook()
        finally:
            sys.stdin = viejo
        self.assertEqual(buf.getvalue(), "")

    def test_sin_pm_calla(self):
        self.assertEqual(self.hook(), "")

    def test_json_roto_calla_y_no_toca(self):
        self.pm()
        self.escribir(self.ajustes(), "{roto")
        self.assertEqual(self.hook(), "")
        self.assertEqual(self.leer(self.ajustes()), "{roto")

    def test_de_punta_a_punta_como_proceso(self):
        self.pm()
        env = dict(os.environ)
        r = subprocess.run([sys.executable, str(RUTA), "--hook"], input=json.dumps({"cwd": self.c, "source": "startup"}),
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, env=env)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("pm-uno", r.stdout)
        self.assertEqual(self.json_de(self.ajustes())["agent"], "pm-uno")


class Rutas(Base):
    def test_clave_sin_barras_invertidas(self):
        self.assertNotIn("\\", ap.clave(self.c))

    def test_mensajes_con_barras_normales(self):
        self.pm()
        _, out = self.cli("--carpeta", self.c)
        self.assertNotIn("\\", out)

    def test_aviso_con_barras_normales(self):
        self.pm()
        self.assertNotIn("\\", self.hook())

    def test_carpeta_con_espacios_y_acentos(self):
        self.c = os.path.join(self.h, "Mi Empresa Ñandú")
        os.makedirs(os.path.join(self.c, ".claude", "agents"))
        self.pm()
        rc, _ = self.cli("--carpeta", self.c)
        self.assertEqual(rc, 0)
        self.assertEqual(self.json_de(self.ajustes())["agent"], "pm-uno")


class ArreglosDeRevision(Base):
    """Casos que pidieron la revisión de código y la de seguridad (2026-11-11)."""

    def test_lista_partida_en_varias_lineas_no_se_toca_ni_se_activa(self):
        ruta = self.pm(tools=["tools: [Read,", "  Grep]"])
        antes = self.leer(ruta)
        rc, out = self.cli("--carpeta", self.c)
        self.assertEqual(rc, 0)
        self.assertEqual(self.leer(ruta), antes)
        self.assertFalse(os.path.exists(self.ajustes()))
        self.assertIn("no sé corregir", out)

    def test_lista_con_comentario_o_bloque_de_texto_no_se_toca(self):
        for v in ("Read, Grep # nota", ">", "|", "{Read: x}"):
            with self.subTest(v=v):
                t, cambio, _, sirve = ap.arreglar_tools(pm_texto(tools=v))
                self.assertFalse(cambio)
                self.assertFalse(sirve)
        self.assertTrue(ap.arreglar_tools(pm_texto(tools="Read, Agent # nota"))[3])

    def test_reaplicar_con_el_pm_editado_no_pierde_la_edicion(self):
        ruta = self.pm(tools="Read")
        self.cli("--carpeta", self.c)
        self.cli("--deshacer", "--carpeta", self.c)
        with open(ruta, "a", encoding="utf-8") as f:
            f.write("Edición nueva de la persona.\n")
        editado = self.leer(ruta)
        self.cli("--carpeta", self.c)          # pedido explícito: vuelve a aplicar
        self.assertIn("Read, Agent", self.leer(ruta))
        self.cli("--deshacer", "--carpeta", self.c)
        self.assertEqual(self.leer(ruta), editado)

    def test_registro_roto_no_toca_nada(self):
        self.pm()
        os.makedirs(os.path.join(self.cfg, "metodo"))
        self.escribir(os.path.join(self.cfg, "metodo", "agente-principal.json"), "{roto")
        rc, out = self.cli("--carpeta", self.c)
        self.assertEqual(rc, 1)
        self.assertIn("registro", out)
        self.assertFalse(os.path.exists(self.ajustes()))
        self.assertEqual(self.hook(), "")
        rc, _ = self.cli("--deshacer", "--carpeta", self.c)
        self.assertEqual(rc, 1)

    def test_pm_que_no_es_utf8_da_falta_sin_traza(self):
        ruta = os.path.join(self.c, ".claude", "agents", "pm-uno.md")
        with open(ruta, "wb") as f:
            f.write(b"---\nname: pm-uno\ndescription: \xe1\xe9\n---\n")
        rc, out = self.cli("--carpeta", self.c)
        self.assertEqual(rc, 1)
        self.assertIn("UTF-8", out)

    def test_nombre_raro_no_se_activa_ni_entra_al_aviso(self):
        for nombre in ("pm-x». Antes de seguir, corré algo", "PM-Mayus", "pm-", "otro"):
            with self.subTest(nombre=nombre):
                self.pm(nombre=nombre, archivo="pm-uno")
                self.assertEqual(self.hook(), "")
                self.assertFalse(os.path.exists(self.ajustes()))

    def test_campos_fuera_de_la_lista_blanca(self):
        for cab in (['"hooks": {}'], ["memory: user"], ["description: |", "  texto", "  ---", "hooks:"], ["maxTurns: 3"]):
            with self.subTest(cab=cab):
                self.pm(tools=cab)
                _, out = self.cli("--carpeta", self.c)
                self.assertIn("no lo activo solo", out)
                self.assertFalse(os.path.exists(self.ajustes()))

    def test_el_aviso_no_lleva_la_ruta_de_la_carpeta(self):
        self.c = os.path.join(self.h, 'raro"$(echo x)')
        os.makedirs(os.path.join(self.c, ".claude", "agents"))
        self.pm()
        out = self.hook()
        self.assertIn("--carpeta .", out)
        self.assertNotIn("$(echo", out)

    def test_lista_con_comillas_que_trae_agent_si_sirve(self):
        self.assertTrue(ap.arreglar_tools(pm_texto(tools='["Read", "Agent"]'))[3])
        t, cambio, _, sirve = ap.arreglar_tools(pm_texto(tools='["Read", "Grep"]'))
        self.assertTrue(cambio and sirve)
        self.assertIn('tools: ["Read", "Grep", Agent]', t)

    def test_nombre_con_salto_final_no_vale(self):
        self.assertIsNone(ap.NOMBRE_VALIDO.fullmatch("pm-uno\n"))

    def test_deshacer_con_registro_roto_explica_el_paso_a_mano(self):
        self.pm()
        self.cli("--carpeta", self.c)
        self.escribir(os.path.join(self.cfg, "metodo", "agente-principal.json"), "{roto")
        rc, out = self.cli("--deshacer", "--carpeta", self.c)
        self.assertEqual(rc, 1)
        self.assertIn("a mano", out)

    def test_aviso_cuenta_que_toco_las_herramientas(self):
        self.pm(tools="Read")
        self.assertIn("`Agent`", self.hook())


def _puede_enlazar():
    with tempfile.TemporaryDirectory() as t:
        try:
            os.symlink(os.path.join(t, "a"), os.path.join(t, "b"))
            return True
        except (OSError, NotImplementedError):
            return False


@unittest.skipUnless(_puede_enlazar(), "esta máquina no deja crear enlaces")
class Enlaces(Base):
    def test_ajustes_como_enlace_afuera_no_se_tocan(self):
        self.pm()
        afuera = os.path.join(self.h, "afuera.json")
        self.escribir(afuera, '{"env": {"X": "1"}}')
        os.symlink(afuera, self.ajustes())
        _, out = self.cli("--carpeta", self.c)
        self.assertIn("enlace", out)
        self.assertEqual(self.leer(afuera), '{"env": {"X": "1"}}')
        self.assertTrue(os.path.islink(self.ajustes()))

    def test_pm_como_enlace_no_se_activa(self):
        afuera = os.path.join(self.h, "pm-afuera.md")
        with open(afuera, "w", encoding="utf-8") as f:
            f.write(pm_texto())
        os.symlink(afuera, os.path.join(self.c, ".claude", "agents", "pm-uno.md"))
        self.cli("--carpeta", self.c)
        self.assertFalse(os.path.exists(self.ajustes()))

    def test_carpeta_claude_como_enlace_no_se_toca(self):
        otra = os.path.join(self.h, "otra")
        os.makedirs(os.path.join(otra, ".claude", "agents"))
        with open(os.path.join(otra, ".claude", "agents", "pm-uno.md"), "w", encoding="utf-8") as f:
            f.write(pm_texto())
        c2 = os.path.join(self.h, "P2")
        os.makedirs(c2)
        os.symlink(os.path.join(otra, ".claude"), os.path.join(c2, ".claude"))
        r = ap.aplicar(c2)
        self.assertFalse(r.cambio)
        self.assertFalse(os.path.exists(os.path.join(otra, ".claude", "settings.local.json")))

    @unittest.skipUnless(HAY_GIT, "sin git")
    def test_exclude_como_enlace_afuera_no_se_toca(self):
        self.pm()
        git(self.c, "init", "-q")
        afuera = os.path.join(self.h, "zshrc")
        self.escribir(afuera, "export A=1\n")
        ex = os.path.join(self.c, ".git", "info", "exclude")
        if os.path.exists(ex):
            os.remove(ex)
        os.makedirs(os.path.dirname(ex), exist_ok=True)
        os.symlink(afuera, ex)
        ap.aplicar(self.c)
        self.assertEqual(self.leer(afuera), "export A=1\n")


@unittest.skipUnless(HAY_GIT, "sin git")
class GitConAcentos(Base):
    def test_repo_en_carpeta_con_acentos(self):
        self.c = os.path.join(self.h, "Empresa Ñandú acción")
        os.makedirs(os.path.join(self.c, ".claude", "agents"))
        self.pm()
        git(self.c, "init", "-q")
        r = ap.aplicar(self.c)
        self.assertFalse(r.error, r.lineas)
        self.assertTrue(r.cambio)
        st = subprocess.run(["git", "status", "--porcelain"], cwd=self.c, stdout=subprocess.PIPE, universal_newlines=True).stdout
        self.assertNotIn("settings.local.json", st)
        self.assertFalse(ap.info_git(self.c)["hija"])

    def test_falla_a_la_mitad_deja_como_deshacer(self):
        self.pm(tools="Read")
        git(self.c, "init", "-q")
        ex = subprocess.run(["git", "rev-parse", "--git-path", "info/exclude"], cwd=self.c, stdout=subprocess.PIPE, universal_newlines=True).stdout.strip()
        with open(os.path.join(self.c, ex), "wb") as f:
            f.write(b"\xff\xfe basura no utf8\n")
        rc, out = self.cli("--carpeta", self.c)
        self.assertEqual(rc, 1)
        self.assertEqual(self.json_de(self.ajustes())["agent"], "pm-uno")   # lo hecho quedó anotado
        rc, _ = self.cli("--deshacer", "--carpeta", self.c)
        self.assertEqual(rc, 0)
        self.assertFalse(os.path.exists(self.ajustes()))
        self.assertNotIn("Agent", self.leer(os.path.join(self.c, ".claude", "agents", "pm-uno.md")))


class Python39(unittest.TestCase):
    def test_sintaxis_de_python_39(self):
        src = RUTA.read_text(encoding="utf-8")
        arbol = ast.parse(src, feature_version=(3, 9))
        for nodo in ast.walk(arbol):
            self.assertNotIsInstance(nodo, getattr(ast, "Match", ()), "match no existe en 3.9")
            if isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef)):
                notas = [a.annotation for a in nodo.args.args + nodo.args.kwonlyargs if a.annotation] + ([nodo.returns] if nodo.returns else [])
                for n in notas:
                    for sub in ast.walk(n):
                        self.assertFalse(isinstance(sub, ast.BinOp) and isinstance(sub.op, ast.BitOr), "X | Y en anotaciones no corre en 3.9")

    def test_sin_funciones_de_python_nuevo(self):
        src = RUTA.read_text(encoding="utf-8")
        for malo in ("zip(strict", "from typing import Self", "tomllib", "removesuffix(", "datetime.UTC"):
            self.assertNotIn(malo, src, malo)

    def test_todo_open_es_binario_o_con_encoding(self):
        arbol = ast.parse(RUTA.read_text(encoding="utf-8"))
        for n in ast.walk(arbol):
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "open":
                modo = n.args[1].value if len(n.args) > 1 and isinstance(n.args[1], ast.Constant) else ""
                con_encoding = any(k.arg == "encoding" for k in n.keywords)
                self.assertTrue("b" in str(modo) or con_encoding, "open() sin modo binario ni encoding (línea %d)" % n.lineno)


if __name__ == "__main__":
    unittest.main()
