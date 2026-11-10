"""Pruebas de salud_conectores.py (plugin metodo). Biblioteca estándar; sin red. Nunca corre el `claude` real:
se pone un `claude` falso en el PATH y la configuración es una carpeta temporal (CLAUDE_CONFIG_DIR).

    python3 -m unittest discover -s plugins/metodo/scripts/tests -p 'test_salud_conectores.py' -v
"""
import json
import os
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

AQUI = Path(__file__).resolve().parent
SCRIPT = AQUI.parent / "salud_conectores.py"

SALIDA_FALSA = """Checking MCP server health…

n8n-oficial: https://x.example/mcp (HTTP) - ! Needs authentication
hostinger-tibp: https://h.example/mcp (HTTP) - ! Needs authentication
perplexity: bash /x/perplexity-mcp - ✔ Connected
plugin:productivity:gmail: https://g.example/mcp (HTTP) - ✗ Failed to connect
plugin:productivity:slack: https://s.example/mcp (HTTP) - ! Needs authentication
claude.ai Notion: https://notion.example/mcp (HTTP) - ✔ Connected
plugin:productivity:notion: https://notion.example/mcp (HTTP) - ✔ Connected
"""


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = Path(self.tmp.name)
        self.cfg, self.bin, self.cwd = t / "cfg", t / "bin", t / "proyecto"
        for d in (self.cfg / "state", self.cfg / "metodo", self.cfg / "projects" / "p", self.bin, self.cwd):
            d.mkdir(parents=True)
        falso = self.bin / "claude"
        if os.name != "nt":
            self._falso(falso, t)
        self.env = dict(os.environ, CLAUDE_CONFIG_DIR=str(self.cfg), PATH=str(self.bin) + os.pathsep + os.environ["PATH"])
        self.env.pop("SALUD_OFF", None)
        self.llamadas = t / "llamadas"

    def _falso(self, falso, t):
        falso.write_text("#!/bin/sh\necho x >> \"%s/llamadas\"\ncat <<'EOF'\n%s\nEOF\n" % (t, SALIDA_FALSA), encoding="utf-8")
        falso.chmod(falso.stat().st_mode | stat.S_IEXEC)

    def tearDown(self):
        self.tmp.cleanup()

    def correr(self, *args, entrada=""):
        return subprocess.run([sys.executable, str(SCRIPT), *args], input=entrada, capture_output=True, text=True, env=self.env, cwd=self.cwd, timeout=60)

    def transcripto(self, texto, edad_dias=1):
        f = self.cfg / "projects" / "p" / "s.jsonl"
        f.write_text(texto, encoding="utf-8")
        viejo = time.time() - edad_dias * 86400
        os.utime(f, (viejo, viejo))

    def n_llamadas(self):
        return len(self.llamadas.read_text(encoding="utf-8").split()) if self.llamadas.exists() else 0


class Parseo(Base):
    def test_estados_y_normalizacion(self):
        sys.path.insert(0, str(AQUI.parent))
        import salud_conectores as s
        lista = {c["nombre"]: c["estado"] for c in s.parsear_mcp_list(SALIDA_FALSA)}
        self.assertEqual(lista["n8n-oficial"], "auth")
        self.assertEqual(lista["perplexity"], "ok")
        self.assertEqual(lista["plugin:productivity:gmail"], "roto")
        self.assertNotIn("Checking MCP server health…", lista)       # línea que no entiendo: se ignora
        self.assertEqual(s.normalizar("plugin:productivity:google calendar"), "plugin_productivity_google_calendar")


@unittest.skipIf(os.name == "nt", "el claude falso es un script sh (no hay sh en Windows)")
class Aviso(Base):
    def test_sin_cache_no_imprime_y_lanza_refresco(self):
        r = self.correr("aviso", entrada=json.dumps({"source": "startup", "cwd": str(self.cwd)}))
        self.assertEqual(r.stdout, "")
        for _ in range(50):                                          # el refresco corre aparte: se espera a que escriba la caché
            if (self.cfg / "state" / "salud-ecosistema.json").exists():
                break
            time.sleep(0.2)
        self.assertTrue((self.cfg / "state" / "salud-ecosistema.json").exists(), "el refresco en segundo plano no escribió la caché")

    def test_solo_usados_y_una_linea_por_tema(self):
        self.transcripto('{"name":"mcp__n8n-oficial__search_workflows"}\n' * 3 + '{"name":"mcp__plugin_productivity_slack__x"}\n')
        # hostinger-tibp y gmail no se usan: no salen en el aviso; n8n-oficial y slack sí (los usó)
        self.correr("refrescar", "--cwd", str(self.cwd))
        r = self.correr("aviso", entrada=json.dumps({"source": "startup", "cwd": str(self.cwd)}))
        self.assertIn("Conectores por firmar (los usás): n8n-oficial, plugin:productivity:slack", r.stdout)
        self.assertNotIn("hostinger-tibp", r.stdout)
        self.assertNotIn("gmail", r.stdout)
        self.assertLessEqual(len(r.stdout.strip().splitlines()), 2)

    def test_aviso_no_corre_claude_ni_espera(self):
        self.correr("refrescar", "--cwd", str(self.cwd))
        antes = self.n_llamadas()
        t = time.time()
        self.correr("aviso", entrada=json.dumps({"source": "startup", "cwd": str(self.cwd)}))
        self.assertLess(time.time() - t, 3)
        self.assertEqual(self.n_llamadas(), antes, "con la caché al día, el aviso no debe llamar a `claude`")

    def test_silencio_si_nada_usado_o_apagado_o_no_es_startup(self):
        self.correr("refrescar", "--cwd", str(self.cwd))
        e = json.dumps({"source": "startup", "cwd": str(self.cwd)})
        self.assertEqual(self.correr("aviso", entrada=e).stdout, "")                      # nada usado: silencio
        self.transcripto('{"name":"mcp__n8n-oficial__x"}\n')
        self.correr("refrescar", "--cwd", str(self.cwd))
        est = json.loads((self.cfg / "state" / "salud-ecosistema.json").read_text(encoding="utf-8"))
        est["pesado"]["ts"] = 0                                                           # forzar uso viejo no cambia el aviso; probamos los otros frenos
        self.assertEqual(self.correr("aviso", entrada=json.dumps({"source": "compact", "cwd": str(self.cwd)})).stdout, "")
        (self.cfg / "metodo" / "salud.apagado").write_text("", encoding="utf-8")
        self.assertEqual(self.correr("aviso", entrada=e).stdout, "")

    def test_transcripto_viejo_no_cuenta_como_uso(self):
        self.transcripto('{"name":"mcp__n8n-oficial__x"}\n', edad_dias=45)
        self.correr("refrescar", "--cwd", str(self.cwd))
        r = self.correr("aviso", entrada=json.dumps({"source": "startup", "cwd": str(self.cwd)}))
        self.assertEqual(r.stdout, "")

    def test_sin_claude_en_el_path_no_inventa(self):
        (self.bin / "claude").unlink()
        self.env["PATH"] = str(self.bin)
        r = self.correr("refrescar", "--cwd", str(self.cwd))
        self.assertEqual(r.returncode, 0)
        r = self.correr("aviso", entrada=json.dumps({"source": "startup", "cwd": str(self.cwd)}))
        self.assertEqual(r.stdout, "")
        self.assertIn("sin dato", self.correr("informe", "--breve", "--cwd", str(self.cwd)).stdout)


@unittest.skipIf(os.name == "nt", "el claude falso es un script sh (no hay sh en Windows)")
class EnElAvisoDeApertura(Base):
    """El control viaja dentro de vigia/aviso.py (el aviso de apertura que ya existe): la prueba de disparo real."""

    def entorno(self):
        home = Path(self.tmp.name) / "home"
        (home / ".claude").mkdir(parents=True)
        env = {k: v for k, v in os.environ.items() if k not in ("GH_TOKEN", "GITHUB_TOKEN", "VIGIA_OFF", "SALUD_OFF")}
        env.update(HOME=str(home), USERPROFILE=str(home), CLAUDE_CONFIG_DIR=str(home / ".claude"), GH_CONFIG_DIR=str(home / ".gh-vacio"),
                   PYTHONDONTWRITEBYTECODE="1", VIGIA_SIN_CIRCUITO="1",
                   PATH=os.pathsep.join([str(self.bin), os.path.dirname(sys.executable), "/usr/bin", "/bin"]))
        return env, home / ".claude"

    def test_la_linea_sale_en_el_aviso_de_apertura(self):
        env, cfg = self.entorno()
        (cfg / "projects" / "p").mkdir(parents=True)
        (cfg / "projects" / "p" / "s.jsonl").write_text('{"name":"mcp__n8n-oficial__x"}\n', encoding="utf-8")
        aviso = AQUI.parent / "vigia" / "aviso.py"
        entrada = json.dumps({"cwd": str(self.cwd), "source": "startup", "session_id": "t1"})
        subprocess.run([sys.executable, str(AQUI.parent / "salud_conectores.py"), "refrescar", "--cwd", str(self.cwd)], env=env, timeout=60)
        r = subprocess.run([sys.executable, str(aviso)], input=entrada, env=env, capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0)
        self.assertIn("Conectores por firmar (los usás): n8n-oficial", json.loads(r.stdout)["systemMessage"])
        env["SALUD_OFF"] = "1"
        entrada2 = json.dumps({"cwd": str(self.cwd), "source": "startup", "session_id": "t2"})
        r = subprocess.run([sys.executable, str(aviso)], input=entrada2, env=env, capture_output=True, text=True, timeout=60)
        self.assertNotIn("Conectores por firmar", r.stdout)


class Seguridad(Base):
    def test_no_corre_mcp_list_dentro_de_carpeta_con_mcp_json_ajeno(self):
        sys.path.insert(0, str(AQUI.parent))
        import salud_conectores as s
        home = os.path.abspath(os.path.expanduser("~"))
        ajena = Path(self.tmp.name) / "repo-ajeno" / "sub"
        ajena.mkdir(parents=True)
        (Path(self.tmp.name) / "repo-ajeno" / ".mcp.json").write_text("{}", encoding="utf-8")
        self.assertEqual(s.carpeta_segura(str(ajena)), home)
        self.assertEqual(s.carpeta_segura(str(self.cwd)), os.path.abspath(str(self.cwd)))

    def test_uso_incremental_no_relee_archivos_sin_cambios(self):
        sys.path.insert(0, str(AQUI.parent))
        import salud_conectores as s
        os.environ["CLAUDE_CONFIG_DIR"] = str(self.cfg)
        self.transcripto('{"name":"mcp__n8n-oficial__x"}\n')
        u1, _ = s.contar_usos()
        f = self.cfg / "projects" / "p" / "s.jsonl"
        cache = json.loads((self.cfg / "state" / "salud-usos.json").read_text(encoding="utf-8"))
        cache["archivos"][str(f)][2]["n8n-oficial"] = 99      # si lo relee, vuelve a 1; si usa la caché, queda 99
        (self.cfg / "state" / "salud-usos.json").write_text(json.dumps(cache), encoding="utf-8")
        u2, _ = s.contar_usos()
        self.assertEqual(u1["n8n-oficial"], 1)
        self.assertEqual(u2["n8n-oficial"], 99)


@unittest.skipIf(os.name == "nt", "el claude falso es un script sh (no hay sh en Windows)")
class Duplicados(Base):
    def armar_plugin(self, nombre, skills, agentes):
        p = Path(self.tmp.name) / "plugins" / nombre
        for s in skills:
            (p / "skills" / s).mkdir(parents=True)
            (p / "skills" / s / "SKILL.md").write_text("---\nname: %s\n---\n" % s, encoding="utf-8")
        (p / "agents").mkdir(parents=True, exist_ok=True)
        for a in agentes:
            (p / "agents" / (a + ".md")).write_text("---\nname: %s\n---\n" % a, encoding="utf-8")
        return p

    def habilitar(self, plugins):
        (self.cfg / "settings.json").write_text(json.dumps({"enabledPlugins": {k: True for k in plugins}, "env": {"SECRETO": "no-leer"}}), encoding="utf-8")
        (self.cfg / "plugins").mkdir(exist_ok=True)
        (self.cfg / "plugins" / "installed_plugins.json").write_text(json.dumps(
            {"plugins": {k: [{"installPath": str(v)}] for k, v in plugins.items()}}))

    def propias(self):
        for s in ("a", "b", "c"):
            (self.cfg / "skills" / s).mkdir(parents=True, exist_ok=True)
            (self.cfg / "skills" / s / "SKILL.md").write_text("x", encoding="utf-8")
        (self.cfg / "agents").mkdir(exist_ok=True)
        (self.cfg / "agents" / "ag.md").write_text("x", encoding="utf-8")

    def test_paquete_que_repite_se_avisa_al_cambiar_la_lista_con_el_comando(self):
        self.propias()
        p = self.armar_plugin("rubro-x", ["a", "b", "c", "otra"], ["ag"])
        q = self.armar_plugin("limpio", ["zzz"], [])
        self.habilitar({"rubro-x@mercado": p, "limpio@mercado": q})
        self.correr("refrescar", "--cwd", str(self.cwd))
        e = json.dumps({"source": "startup", "cwd": str(self.cwd)})
        r = self.correr("aviso", entrada=e)
        self.assertIn("rubro-x@mercado", r.stdout)
        self.assertIn("claude plugin disable rubro-x@mercado", r.stdout)
        self.assertNotIn("limpio", r.stdout)
        self.assertNotIn("no-leer", r.stdout)
        self.assertNotIn("rubro-x", self.correr("aviso", entrada=e).stdout, "con la misma lista no se repite hasta pasada una semana")

    def test_el_propio_metodo_nunca_se_propone_apagar(self):
        self.propias()
        p = self.armar_plugin("metodo", ["a", "b", "c"], [])
        self.habilitar({"metodo@mercado": p})
        self.correr("refrescar", "--cwd", str(self.cwd))
        self.assertEqual(self.correr("aviso", entrada=json.dumps({"source": "startup", "cwd": str(self.cwd)})).stdout, "")

    def test_excepcion_escrita_calla_el_aviso(self):
        self.propias()
        p = self.armar_plugin("rubro-x", ["a", "b", "c"], [])
        self.habilitar({"rubro-x@mercado": p})
        (self.cfg / "metodo" / "salud-excepciones.txt").write_text("rubro-x@mercado  # se entrega al cliente a propósito\n", encoding="utf-8")
        self.correr("refrescar", "--cwd", str(self.cwd))
        self.assertEqual(self.correr("aviso", entrada=json.dumps({"source": "startup", "cwd": str(self.cwd)})).stdout, "")

    def test_una_coincidencia_suelta_no_alcanza(self):
        self.propias()
        p = self.armar_plugin("grande", ["a", "x1", "x2", "x3", "x4"], [])
        self.habilitar({"grande@mercado": p})
        self.correr("refrescar", "--cwd", str(self.cwd))
        self.assertNotIn("grande", self.correr("informe", "--cwd", str(self.cwd)).stdout)

    def test_informe_no_trata_dos_cuentas_del_mismo_proveedor_como_copia(self):
        self.correr("refrescar", "--cwd", str(self.cwd))
        sal = self.correr("informe", "--cwd", str(self.cwd)).stdout
        self.assertNotIn("repetido", sal)           # dos servidores con la misma URL (p. ej. dos Hostinger) no son copia
        self.assertIn("que no usás", sal)
        self.assertIn("no se apaga nada por desuso", sal)


if __name__ == "__main__":
    unittest.main()
