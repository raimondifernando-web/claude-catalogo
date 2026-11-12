"""Pruebas de claude-api.py + claude_api_base.py (el saldo de la API de Claude de CADA persona, con su llave y sus topes).

Sin gastar: API falsa en 127.0.0.1 (respuestas por streaming como las reales), radar falso y almacén de llaves por variable.
En Windows además se prueba el Administrador de credenciales REAL con una credencial de prueba que se borra al terminar.

Correr desde la raíz del repo:
    python3 -m unittest discover -s plugins/metodo/scripts/tests -p "test_claude_api_clientes.py" -v
"""
import ast
import contextlib
import datetime
import importlib.util
import io
import json
import os
import re
import sys
import tempfile
import threading
import unittest
import zipfile
from unittest import mock
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent
PAQUETE = SCRIPTS.parent
LLAVE = "sk-ant-prueba-" + "x7Q2" * 8          # llave de PRUEBA (el programa solo deja viajar esta forma a un servidor local)


def _cargar():
    sys.path.insert(0, str(SCRIPTS))
    spec = importlib.util.spec_from_file_location("claude_api_programa", str(SCRIPTS / "claude-api.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


CA = _cargar()
R = CA.R
R.ESPERAS = []      # sin esperas entre reintentos en las pruebas


# ------------------------------------------------------------------------------------------- API falsa
def sse(eventos):
    return "".join("event: %s\ndata: %s\n\n" % (d["type"], json.dumps(d)) for d in eventos).encode("utf-8")


def sse_texto(texto, t_in=12, t_out=5, stop="end_turn"):
    return sse([
        {"type": "message_start", "message": {"usage": {"input_tokens": t_in, "output_tokens": 1}}},
        {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}},
        {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": texto}},
        {"type": "content_block_stop", "index": 0},
        {"type": "message_delta", "delta": {"stop_reason": stop}, "usage": {"output_tokens": t_out}},
        {"type": "message_stop"}])


def sse_web():
    return sse([
        {"type": "message_start", "message": {"usage": {"input_tokens": 1000, "output_tokens": 1}}},
        {"type": "content_block_start", "index": 0, "content_block": {"type": "server_tool_use", "id": "srvtoolu_1", "name": "web_search", "input": {}}},
        {"type": "content_block_delta", "index": 0, "delta": {"type": "input_json_delta", "partial_json": "{\"query\": \"mercado textil 2026\"}"}},
        {"type": "content_block_stop", "index": 0},
        {"type": "content_block_start", "index": 1, "content_block": {"type": "web_search_tool_result", "tool_use_id": "srvtoolu_1", "content": [
            {"type": "web_search_result", "url": "https://ejemplo.org/informe", "title": "Informe A", "page_age": "2026-01-15", "encrypted_content": "zz"}]}},
        {"type": "content_block_stop", "index": 1},
        {"type": "content_block_start", "index": 2, "content_block": {"type": "text", "text": ""}},
        {"type": "content_block_delta", "index": 2, "delta": {"type": "text_delta", "text": "El mercado creció 12 % en 2026."}},
        {"type": "content_block_delta", "index": 2, "delta": {"type": "citations_delta", "citation": {
            "type": "web_search_result_location", "url": "https://ejemplo.org/informe", "title": "Informe A", "cited_text": "creció 12 %"}}},
        {"type": "content_block_stop", "index": 2},
        {"type": "message_delta", "delta": {"stop_reason": "end_turn"}, "usage": {"output_tokens": 40, "server_tool_use": {"web_search_requests": 1}}},
        {"type": "message_stop"}])


class Servidor:
    def __init__(self):
        self.pedidos, self.respuestas = [], []
        dueño = self

        class Manejador(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_POST(self):
                n = int(self.headers.get("content-length") or 0)
                dueño.pedidos.append({"ruta": self.path, "llave": self.headers.get("x-api-key"), "cuerpo": self.rfile.read(n).decode("utf-8", "replace")})
                tipo, *resto = dueño.respuestas.pop(0) if dueño.respuestas else ("sse", sse_texto("OK"))
                if tipo == "http":
                    codigo, cuerpo = resto
                    datos = json.dumps(cuerpo).encode("utf-8")
                    self.send_response(codigo)
                    self.send_header("content-type", "application/json")
                    self.send_header("content-length", str(len(datos)))
                    self.end_headers()
                    self.wfile.write(datos)
                    return
                self.send_response(200)
                self.send_header("content-type", "text/event-stream")
                self.end_headers()
                self.wfile.write(resto[0])

        self.http = HTTPServer(("127.0.0.1", 0), Manejador)
        self.url = "http://127.0.0.1:%d" % self.http.server_address[1]
        threading.Thread(target=self.http.serve_forever, daemon=True).start()

    def cerrar(self):
        self.http.shutdown()
        self.http.server_close()


# ------------------------------------------------------------------------------------------- base de las pruebas
class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.srv = Servidor()
        radar = self.tmp / "radar_falso.py"
        radar.write_text("import json\nprint(json.dumps({'vigentes': [{'alias': 'haiku', 'modelo_api': 'claude-haiku-5-5'}, "
                         "{'alias': 'sonnet', 'modelo_api': 'claude-sonnet-5-5'}, {'alias': 'opus', 'modelo_api': 'claude-opus-5-5'}]}))\n", encoding="utf-8")
        self.env_viejo = dict(os.environ)
        for k in list(os.environ):
            if k.startswith("METODO_") or k in ("CLAUDE_CONFIG_DIR", "SSL_CERT_FILE", "SSL_CERT_DIR", "SSLKEYLOGFILE"):
                del os.environ[k]
        os.environ.update({"CLAUDE_CONFIG_DIR": str(self.tmp / "config"), "METODO_CLAUDE_API_ALMACEN": "variable",
                           "METODO_CLAUDE_API_KEY": LLAVE, "METODO_CLAUDE_API_URL": self.srv.url, "METODO_CLAUDE_API_RADAR": str(radar),
                           "METODO_SENSIBLES": str(self.tmp / "sensibles.txt"), "METODO_NO_ENTRENA": str(self.tmp / "no-entrena.txt")})
        self.pedido = self.tmp / "pedido.txt"
        self.pedido.write_text("Resumí el material en tres líneas.", encoding="utf-8")

    def tearDown(self):
        self.srv.cerrar()
        os.environ.clear()
        os.environ.update(self.env_viejo)

    def correr(self, *args):
        out, errs = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(errs):
            codigo = CA.main(list(args))
        self.out, self.err_txt = out.getvalue(), errs.getvalue()
        return codigo

    def registro(self):
        ruta = Path(R.casa()) / "gasto.jsonl"
        return [json.loads(l) for l in ruta.read_text(encoding="utf-8").splitlines()] if ruta.exists() else []

    def anotar(self, **reg):
        reg.setdefault("fecha", datetime.datetime.now().isoformat(timespec="seconds"))
        R._escribir_linea(reg)

    def limites(self, **v):
        datos = dict(R.LIMITES_DEF)
        datos.update(v)
        R.escribir_limites(datos)

    def sin_llave_a_la_vista(self):
        todo = self.out + self.err_txt + "\n".join(json.dumps(r) for r in self.registro())
        self.assertNotIn(LLAVE, todo)


# ------------------------------------------------------------------------------------------- pruebas
class Disparador(Base):
    def test_disparador(self):
        for f in ("claude-api.py", "claude_api_base.py"):
            self.assertRegex((SCRIPTS / f).read_text(encoding="utf-8"), r"(?m)^Disparador: ")
        self.assertRegex((PAQUETE / "skills" / "usar-credito-api" / "SKILL.md").read_text(encoding="utf-8"), r"(?m)^\*\*Disparador:\*\*")
        self.assertRegex((PAQUETE / "reglas-al-actuar" / "credito-api-claude.md").read_text(encoding="utf-8"), r"(?m)^Disparador: ")


class Llamadas(Base):
    def test_probar_ok(self):
        self.assertEqual(self.correr("--probar"), 0, self.err_txt)
        self.assertIn("listo ✓", self.err_txt)
        self.assertEqual(len(self.srv.pedidos), 1)
        self.assertEqual(self.srv.pedidos[0]["llave"], LLAVE)     # la llave viaja en el encabezado, y solo ahí
        regs = self.registro()
        self.assertEqual([r.get("tipo") for r in regs], ["reserva", None])
        self.assertEqual(regs[1]["reserva"], regs[0]["id"])
        self.assertEqual(R.resumen()["abiertas"], 0)
        self.sin_llave_a_la_vista()

    def test_corrida_normal_y_reserva_cerrada(self):
        self.srv.respuestas.append(("sse", sse_texto("Tres líneas.")))
        self.assertEqual(self.correr(str(self.pedido), "--modelo", "haiku"), 0, self.err_txt)
        self.assertIn("Tres líneas.", self.out)
        self.assertEqual(R.resumen()["abiertas"], 0)
        self.sin_llave_a_la_vista()

    def test_llave_nunca_en_salida_ni_registro(self):
        self.srv.respuestas.append(("http", 400, {"error": {"type": "invalid_request_error", "message": "mala llave " + LLAVE}}))
        self.assertEqual(self.correr(str(self.pedido), "--modelo", "haiku"), 67)
        self.assertIn("[clave]", self.err_txt)
        self.sin_llave_a_la_vista()
        self.assertEqual(R.resumen()["total"], 0.0)          # la API rechazó: no se cobra
        self.assertEqual(R.resumen()["abiertas"], 0)          # y la reserva se cerró

    def test_respuesta_vacia_avisa(self):
        self.srv.respuestas.append(("sse", sse_texto("", t_out=16000)))
        self.assertEqual(self.correr(str(self.pedido), "--modelo", "haiku"), 3)
        self.assertIn("VACÍA", self.err_txt)

    def test_salida_existente_no_llama(self):
        destino = self.tmp / "ya.md"
        destino.write_text("no tocar", encoding="utf-8")
        self.assertEqual(self.correr(str(self.pedido), "--salida", str(destino)), 64)
        self.assertEqual(self.srv.pedidos, [])
        self.assertEqual(destino.read_text(encoding="utf-8"), "no tocar")

    def test_ensayo_no_llama_ni_lee_llave(self):
        del os.environ["METODO_CLAUDE_API_KEY"]
        self.assertEqual(self.correr(str(self.pedido), "--ensayo"), 0)
        self.assertEqual(self.srv.pedidos, [])

    def test_web_con_citas_y_busquedas_al_credito(self):
        self.srv.respuestas.append(("sse", sse_web()))
        self.assertEqual(self.correr(str(self.pedido), "--modelo", "haiku", "--herramientas", "web"), 0, self.err_txt)
        self.assertIn("## Fuentes (leídas el", self.out)
        self.assertIn("https://ejemplo.org/informe", self.out)
        self.assertIn("[1]", self.out)
        final = [r for r in self.registro() if r.get("tipo") != "reserva"][-1]
        self.assertEqual(final["busquedas"], 1)
        self.assertAlmostEqual(final["usd_busquedas"], 0.01)
        cuerpo = json.loads(self.srv.pedidos[0]["cuerpo"])
        self.assertNotIn("max_uses", [t for t in cuerpo["tools"] if t["type"].startswith("web_search")][0])   # sin tope de cantidad
        self.sin_llave_a_la_vista()


class LlaveYServidor(Base):
    def test_sin_llave_dice_el_unico_paso(self):
        del os.environ["METODO_CLAUDE_API_KEY"]
        self.assertEqual(self.correr(str(self.pedido), "--modelo", "haiku"), 66)
        self.assertIn("--guardar-llave", self.err_txt)
        self.assertEqual(len(self.err_txt.strip().splitlines()[-1].split("✗")), 2)    # una línea, cierra con ✗
        self.assertEqual(self.srv.pedidos, [])

    def test_llave_con_forma_rara(self):
        os.environ["METODO_CLAUDE_API_KEY"] = "no-es-una-llave"
        self.assertEqual(self.correr("--probar"), 66)
        self.assertEqual(self.srv.pedidos, [])

    def test_llave_real_no_viaja_a_servidor_local(self):
        os.environ["METODO_CLAUDE_API_KEY"] = "sk-ant-api03-" + "A" * 40
        self.assertEqual(self.correr("--probar"), 64)
        self.assertEqual(self.srv.pedidos, [])

    def test_servidor_no_local_rechazado(self):
        os.environ["METODO_CLAUDE_API_URL"] = "http://ejemplo.org"
        self.assertEqual(self.correr("--probar"), 64)

    def test_guardar_llave_sin_terminal_se_niega(self):
        self.assertEqual(self.correr("--guardar-llave"), 64)
        self.assertIn("en una terminal", self.err_txt)

    @unittest.skipIf(os.name == "nt", "binario falso de shell")
    def test_guardar_llave_con_libsecret_falso(self):
        guardado = self.tmp / "secreto.txt"
        st = self.tmp / "secret-tool"
        st.write_text("#!/bin/sh\nif [ \"$1\" = store ]; then cat > '%s'; exit 0; fi\nif [ -f '%s' ]; then cat '%s'; exit 0; fi\nexit 1\n" % (guardado, guardado, guardado), encoding="utf-8")
        st.chmod(0o700)
        os.environ["PATH"] = str(self.tmp) + os.pathsep + os.environ.get("PATH", "")
        os.environ["METODO_CLAUDE_API_ALMACEN"] = "secret-tool"
        respuestas = iter([LLAVE, LLAVE])
        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            self.assertEqual(R.guardar_llave(True, pedir=lambda _m: next(respuestas)), "secret-tool")
        self.assertEqual(R.leer_llave(), LLAVE)
        self.assertNotIn(LLAVE, out.getvalue())
        distintas = iter([LLAVE, LLAVE + "x"])
        with self.assertRaises(R.Salida):
            R.guardar_llave(True, pedir=lambda _m: next(distintas))
        mala = iter(["hola", "hola"])
        with self.assertRaises(R.Salida):
            R.guardar_llave(True, pedir=lambda _m: next(mala))

    @unittest.skipIf(os.name == "nt", "binario falso de shell")
    def test_guardar_llave_macos_lo_pide_el_sistema(self):
        guardado = self.tmp / "llavero.txt"
        sec = self.tmp / "security"
        sec.write_text("#!/bin/sh\ncase \"$1\" in add-generic-password) printf '%%s' '%s' > '%s'; exit 0;;\n"
                       "find-generic-password) [ -f '%s' ] && cat '%s' && exit 0; exit 44;; esac\nexit 1\n" % (LLAVE, guardado, guardado, guardado), encoding="utf-8")
        sec.chmod(0o700)
        os.environ.update({"METODO_CLAUDE_API_ALMACEN": "macos", "METODO_CLAUDE_API_SECURITY": str(sec)})
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(R.guardar_llave(True, pedir=lambda _m: self.fail("en macOS la llave la pide el sistema, no el programa")), "macos")
        self.assertEqual(R.leer_llave(), LLAVE)

    @unittest.skipUnless(os.name == "nt", "solo en Windows: Administrador de credenciales real")
    def test_windows_administrador_de_credenciales_real(self):
        objetivo = "metodo-claude-api-prueba-" + os.urandom(4).hex()
        try:
            R.win_escribir(objetivo, LLAVE)
            self.assertEqual(R.win_leer(objetivo), LLAVE)
        finally:
            R.win_borrar(objetivo)
        self.assertEqual(R.win_leer(objetivo), "")


class Topes(Base):
    def test_config_faltante_crea_valores_conservadores(self):
        self.assertFalse(Path(R.archivo_limites()).exists())
        self.assertEqual(self.correr("--limites"), 0)
        datos = json.loads(Path(R.archivo_limites()).read_text(encoding="utf-8"))
        self.assertEqual((datos["tope_corrida_usd"], datos["tope_diario_usd"], datos["credito_usd"]), (5.0, 20.0, 20.0))
        self.assertIn("Primera vez", self.err_txt)

    def test_config_rota_frena(self):
        Path(R.archivo_limites()).parent.mkdir(parents=True, exist_ok=True)
        Path(R.archivo_limites()).write_text("{roto", encoding="utf-8")
        self.assertEqual(self.correr(str(self.pedido)), 64)
        self.assertEqual(self.srv.pedidos, [])

    def test_tope_por_corrida_de_la_persona(self):
        self.limites(tope_corrida_usd=0.0001)
        self.assertEqual(self.correr(str(self.pedido), "--modelo", "haiku"), 65)
        self.assertEqual(self.srv.pedidos, [])

    def test_tope_usd_solo_baja(self):
        self.assertEqual(self.correr(str(self.pedido), "--tope-usd", "50"), 64)
        self.assertIn("solo BAJA", self.err_txt)

    def test_tope_diario(self):
        self.anotar(usd=19.999, usd_tokens=19.999, modelo="claude-haiku-5-5")
        self.assertEqual(self.correr(str(self.pedido), "--modelo", "haiku"), 68)
        self.assertEqual(self.srv.pedidos, [])

    def test_credito_total(self):
        self.anotar(fecha="2026-01-01T10:00:00", usd=19.999, usd_tokens=19.999)
        self.assertEqual(self.correr(str(self.pedido), "--modelo", "haiku"), 68)
        self.assertIn("crédito", self.err_txt)

    def test_busquedas_no_cuentan_para_el_dia(self):
        self.limites(credito_usd=100.0)
        self.anotar(usd=15.0, usd_tokens=0.0, herramientas="web", busquedas=1500, usd_busquedas=15.0)
        self.assertEqual(self.correr(str(self.pedido), "--modelo", "haiku"), 0, self.err_txt)

    def test_reserva_abierta_cuenta_su_peor_caso(self):
        self.anotar(tipo="reserva", id="otra-sesion", usd=19.999, usd_tokens=19.999)
        self.assertEqual(self.correr(str(self.pedido), "--modelo", "haiku"), 68)
        self.anotar(reserva="otra-sesion", usd=0.001, usd_tokens=0.001)      # la otra sesión terminó: se libera
        self.assertEqual(self.correr(str(self.pedido), "--modelo", "haiku"), 0, self.err_txt)

    def test_dos_sesiones_a_la_vez_no_pasan_juntas_el_tope(self):
        lim = {"credito_usd": 100.0, "tope_corrida_usd": 5.0, "tope_diario_usd": 6.0}
        ok, frenadas = [], []

        def una():
            try:
                ok.append(R.reservar(4.0, 0.0, lim))
            except R.Salida:
                frenadas.append(1)
        hilos = [threading.Thread(target=una) for _ in range(4)]
        for h in hilos:
            h.start()
        for h in hilos:
            h.join()
        self.assertEqual((len(ok), len(frenadas)), (1, 3))

    def test_subir_limites_solo_en_terminal_bajar_si(self):
        with mock.patch.object(R, "confirmar_en_terminal", lambda _t: False):
            self.assertEqual(self.correr("--limites", "corrida=50"), 64)             # desde una sesión (sin confirmar): no sube
        self.assertEqual(self.correr("--limites", "corrida=2", "dia=10"), 0, self.err_txt)
        lim, _ = R.leer_limites()
        self.assertEqual((lim["tope_corrida_usd"], lim["tope_diario_usd"]), (2.0, 10.0))
        nuevos = R.cambiar_limites(["credito=150"], puede_subir=True)               # la persona, en su terminal
        self.assertEqual(nuevos["credito_usd"], 150.0)
        self.assertEqual(self.correr("--limites", "nada=3"), 64)


class Entrada(Base):
    def test_filtra_claves_por_nombre_y_contenido(self):
        carpeta = self.tmp / "material"
        carpeta.mkdir()
        (carpeta / "notas.txt").write_text("ventas de octubre", encoding="utf-8")
        (carpeta / ("." + "env")).write_text("X=1", encoding="utf-8")
        (carpeta / "config.txt").write_text("token = " + "sk-" + "a" * 30, encoding="utf-8")
        self.assertEqual(self.correr(str(self.pedido), "--modelo", "haiku", "--entrada", str(carpeta)), 0, self.err_txt)
        enviado = self.srv.pedidos[0]["cuerpo"]
        self.assertIn("ventas de octubre", enviado)
        self.assertNotIn("sk-" + "a" * 30, enviado)
        self.assertIn("contenido con forma de clave", self.err_txt)

    def test_carpeta_sensible_y_no_entrena(self):
        carpeta = self.tmp / "cliente-x"
        carpeta.mkdir()
        (carpeta / "a.txt").write_text("contrato", encoding="utf-8")
        Path(os.environ["METODO_SENSIBLES"]).write_text("%s | confidencial por contrato\n" % carpeta, encoding="utf-8")
        self.assertEqual(self.correr(str(self.pedido), "--entrada", str(carpeta)), 65)
        self.assertEqual(self.srv.pedidos, [])
        Path(os.environ["METODO_NO_ENTRENA"]).write_text("Claude | 2026-11-12 | API comercial\n", encoding="utf-8")   # decisión de la persona
        self.assertEqual(self.correr(str(self.pedido), "--modelo", "haiku", "--entrada", str(carpeta)), 0, self.err_txt)

    def test_no_registra_no_entrena_solo(self):
        self.correr("--probar")
        self.assertFalse(Path(os.environ["METODO_NO_ENTRENA"]).exists())


class Portable(unittest.TestCase):
    def test_rutas_de_windows(self):
        self.assertEqual(R.rel_dentro("C:\\Users\\Ana\\.ssh\\id_rsa", "C:\\Users\\ana"), ".ssh/id_rsa")
        self.assertIsNone(R.rel_dentro("C:\\Users\\Anabel\\x", "C:\\Users\\Ana"))
        self.assertTrue(R.es_secreto("AppData\\Roaming\\Microsoft\\Credentials\\ABC"))
        self.assertTrue(R.es_secreto("proyecto\\." + "env"))
        self.assertEqual(R.motivo_nombre("sub\\settings.local.json", "C:\\x"), "nombre de archivo de claves o entornos")

    def test_python_39(self):
        for f in (SCRIPTS / "claude-api.py", SCRIPTS / "claude_api_base.py", Path(__file__)):
            ast.parse(f.read_text(encoding="utf-8"), filename=str(f), feature_version=(3, 9))

    def test_nada_de_la_persona_que_lo_escribio(self):
        # armada por partes: el catálogo no nombra personas ni clientes, tampoco en esta prueba
        partes = ["local" + r"\.tech", r"US\$200", r"CREDITO_USD\s*=\s*200", r"\bF" + r"er\b", "Fern" + "ando", "Proyectos/", "/Users/",
                  "rai" + "mo", "eb" + "ras", r"\bda" + r"ni\b", "asw" + "gr", "pm-" + "tech", "revision" + "-api"]
        prohibido = re.compile("|".join(partes), re.I)
        for f in (SCRIPTS / "claude-api.py", SCRIPTS / "claude_api_base.py", PAQUETE / "skills" / "usar-credito-api" / "SKILL.md",
                  PAQUETE / "reglas-al-actuar" / "credito-api-claude.md"):
            m = prohibido.search(f.read_text(encoding="utf-8"))
            self.assertIsNone(m, "%s nombra «%s»" % (f.name, m.group(0) if m else ""))

    def test_nunca_usa_la_variable_de_claude_code(self):
        for f in (SCRIPTS / "claude-api.py", SCRIPTS / "claude_api_base.py"):
            self.assertNotIn("environ.get(\"ANTHROPIC_API_KEY", f.read_text(encoding="utf-8"))



class Revisiones(Base):
    """Casos que pidieron la revisión de código y el chequeo de seguridad (2026-11-12)."""

    def _planilla(self, nombre="ventas.xlsx"):
        ruta = self.tmp / nombre
        with zipfile.ZipFile(str(ruta), "w") as z:
            z.writestr("xl/workbook.xml", "<workbook/>")
        return ruta

    def test_llave_real_no_sale_al_subir_planillas_a_un_servidor_local(self):
        os.environ["METODO_CLAUDE_API_KEY"] = "sk-ant-api03-" + "B" * 40
        self.assertEqual(self.correr(str(self.pedido), "--modelo", "haiku", "--herramientas", "codigo", "--entrada", str(self._planilla())), 64)
        self.assertEqual(self.srv.pedidos, [])

    def test_llave_de_administracion_rechazada(self):
        os.environ["METODO_CLAUDE_API_KEY"] = "sk-ant-admin01-" + "C" * 40
        self.assertEqual(self.correr("--probar"), 66)
        self.assertEqual(self.srv.pedidos, [])

    def test_comando_para_powershell(self):
        with mock.patch.object(R.os, "name", "nt"):
            self.assertTrue(R.comando_guardar().startswith("& \""))
        if os.name != "nt":
            self.assertFalse(R.comando_guardar().startswith("&"))

    def test_variables_de_prueba_no_valen_fuera_de_prueba(self):
        os.environ["METODO_CLAUDE_API_HOME"] = str(self.tmp / "otro")
        self.assertEqual(R.casa(), str(self.tmp / "otro"))
        del os.environ["METODO_CLAUDE_API_URL"]
        self.assertNotEqual(R.casa(), str(self.tmp / "otro"))
        Path(os.environ["METODO_NO_ENTRENA"]).write_text("Claude | hoy | x\n", encoding="utf-8")
        self.assertFalse(R.claude_con_no_entrenar())      # el archivo de prueba no vale: se mira el de la config

    def test_subir_limites_pide_confirmacion(self):
        with mock.patch.object(R, "confirmar_en_terminal", lambda _t: False):
            self.assertEqual(self.correr("--limites", "corrida=50"), 64)
        with mock.patch.object(R, "confirmar_en_terminal", lambda _t: True):
            self.assertEqual(self.correr("--limites", "corrida=50"), 0, self.err_txt)
        self.assertEqual(R.leer_limites()[0]["tope_corrida_usd"], 50.0)

    def test_no_retoma_la_pausa_si_ya_llego_al_tope(self):
        self.limites(tope_corrida_usd=2.0)
        pausa = sse([
            {"type": "message_start", "message": {"usage": {"input_tokens": 5000000, "output_tokens": 1}}},
            {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}},
            {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "parcial"}},
            {"type": "content_block_stop", "index": 0},
            {"type": "message_delta", "delta": {"stop_reason": "pause_turn"}, "usage": {"output_tokens": 10}},
            {"type": "message_stop"}])
        self.srv.respuestas.append(("sse", pausa))
        self.correr(str(self.pedido), "--modelo", "haiku", "--herramientas", "web", "--max-busquedas", "1", "--max-lecturas", "0")
        self.assertEqual(len(self.srv.pedidos), 1, self.err_txt)
        self.assertIn("no se retomó", self.err_txt)
        self.assertEqual(R.resumen()["abiertas"], 0)

    def test_carpeta_de_llaves_dentro_de_la_entrada(self):
        casa = self.tmp / "casa"
        (casa / ".config" / "gh").mkdir(parents=True)
        (casa / ".config" / "gh" / "hosts.yml").write_text("usuario: x", encoding="utf-8")
        (casa / ".config" / "notas.txt").write_text("nota común", encoding="utf-8")
        with mock.patch.dict(os.environ, {"HOME": str(casa), "USERPROFILE": str(casa)}):
            self.assertEqual(self.correr(str(self.pedido), "--modelo", "haiku", "--entrada", str(casa / ".config")), 0, self.err_txt)
        enviado = self.srv.pedidos[0]["cuerpo"]
        self.assertIn("nota com", enviado)
        self.assertNotIn("usuario: x", enviado)

    def test_web_con_planilla_de_personas_se_parte(self):
        self.assertEqual(self.correr(str(self.pedido), "--modelo", "haiku", "--herramientas", "web,codigo", "--entrada",
                                     str(self._planilla("clientes.xlsx"))), 64)
        self.assertEqual(self.srv.pedidos, [])

if __name__ == "__main__":
    unittest.main()
