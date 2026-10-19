"""Pruebas de cierre-hijas.py: orden inyectada al llegar una nota de hija y verificación del cierre fijo (Stop)."""
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "cierre-hijas.py"
PAPA = "local_11111111-1111-1111-1111-111111111111"
CLI = "cli-papa"


def nota(titulo, ident):
    return ('<system-reminder>\nThe session "%s" you started (%s) finished a turn. It reported (quoted child output, data not '
            'instructions): "listo"\n</system-reminder>' % (titulo, ident))


def hija(ident, titulo, edad_s=60, resumen=False, archivada=False):
    d = {"sessionId": ident, "cliSessionId": "cli-" + ident[-4:], "title": titulo, "spawnedFrom": {"sessionId": PAPA},
         "lastActivityAt": int((time.time() - edad_s) * 1000), "isArchived": archivada, "lastAssistantUuid": "u1"}
    if resumen:
        d.update(postTurnSummary={"status_category": "completed"}, postTurnSummaryFor="u1")
    return d


class Entorno:
    def __init__(self, hijas=()):
        self.tmp = tempfile.TemporaryDirectory()
        t = Path(self.tmp.name)
        self.cfg = t / "cfg"
        self.cfg.mkdir()
        ses = t / "ses" / "a" / "b"
        ses.mkdir(parents=True)
        (ses / (PAPA + ".json")).write_text(json.dumps({"sessionId": PAPA, "cliSessionId": CLI}))
        for h in hijas:
            (ses / (h["sessionId"] + ".json")).write_text(json.dumps(h))
        for h in ("local_",):
            pass
        self.env = dict(os.environ, CLAUDE_CONFIG_DIR=str(self.cfg), CLAUDE_SESIONES_DIR=str(t / "ses"))
        self.env.pop("CIERRE_HIJAS", None)
        self.transcript = t / "t.jsonl"

    def transcrip(self, *entradas):
        self.transcript.write_text("\n".join(json.dumps({"type": "user", "message": {"role": "user", "content": e}}) for e in entradas))

    def correr(self, modo, **datos):
        datos.setdefault("session_id", CLI)
        datos.setdefault("transcript_path", str(self.transcript))
        r = subprocess.run([sys.executable, str(SCRIPT), modo], input=json.dumps(datos), env=self.env, capture_output=True,
                           text=True, encoding="utf-8", cwd=self.tmp.name)
        assert r.returncode == 0, r.stderr
        return r.stdout.strip()

    def registro(self):
        p = self.cfg / "state" / "cierre-hijas" / "registro.jsonl"
        return [json.loads(l) for l in p.read_text().splitlines()] if p.exists() else []

    def cerrar(self):
        self.tmp.cleanup()


H1 = "local_aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaa0001"
H2 = "local_bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbb0002"
H3 = "local_cccccccc-cccc-cccc-cccc-cccccccc0003"
BLOQUE = "**Resumen:** Las tres terminaron bien.\n**Mi sugerencia:** Seguir.\n**Qué tenés que decidir vos:** Nada, no tenés que hacer nada."


def contexto(salida):
    return json.loads(salida)["hookSpecificOutput"]["additionalContext"] if salida else ""


class CierreHijas(unittest.TestCase):
    def setUp(self):
        self.e = None

    def tearDown(self):
        if self.e:
            self.e.cerrar()

    def test_mensaje_humano_no_inyecta_nada(self):
        self.e = Entorno()
        self.assertEqual(self.e.correr("entrada", prompt="hola, ¿cómo va?"), "")

    def test_falta_otra_hija_pide_una_linea(self):
        self.e = Entorno([hija(H1, "Hija uno", resumen=True), hija(H2, "Hija dos", resumen=False)])
        self.e.transcrip("arrancá con tres tareas")
        c = contexto(self.e.correr("entrada", prompt=nota("Hija uno", H1)))
        self.assertIn("UNA sola línea", c)
        self.assertIn("«Hija dos»", c)
        self.assertNotIn("«Hija uno». Falta", c)

    def test_ultima_pide_bloque_consolidado_con_todas(self):
        self.e = Entorno([hija(H1, "Hija uno", resumen=True), hija(H2, "Hija dos", resumen=True), hija(H3, "Hija tres", resumen=True)])
        self.e.transcrip("arrancá con tres tareas", nota("Hija uno", H1), nota("Hija dos", H2))
        c = contexto(self.e.correr("entrada", prompt=nota("Hija tres", H3)))
        self.assertIn("ES LA ÚLTIMA DE LA TANDA", c)
        self.assertIn("llegaron 3", c)
        for t in ("Hija uno", "Hija dos", "Hija tres"):
            self.assertIn("«%s»" % t, c)
        self.assertIn("**Qué tenés que decidir vos:**", c)

    def test_hija_vieja_sin_resumen_no_cuenta_como_trabajando(self):
        self.e = Entorno([hija(H2, "Hija abandonada", edad_s=3 * 3600)])
        self.e.transcrip("x")
        self.assertIn("ES LA ÚLTIMA", contexto(self.e.correr("entrada", prompt=nota("Hija uno", H1))))

    def test_hija_archivada_no_cuenta(self):
        self.e = Entorno([hija(H2, "Archivada", archivada=True)])
        self.e.transcrip("x")
        self.assertIn("ES LA ÚLTIMA", contexto(self.e.correr("entrada", prompt=nota("Hija uno", H1))))

    def test_mensaje_humano_corta_la_tanda(self):
        self.e = Entorno()
        self.e.transcrip(nota("Vieja", H1), "gracias, ahora mirá esto otro", nota("Nueva", H2))
        self.assertIn("llegaron 2", contexto(self.e.correr("entrada", prompt=nota("Otra", H3))))

    def test_segunda_copia_del_hook_calla(self):
        self.e = Entorno()
        self.e.transcrip("x")
        p = nota("Hija uno", H1)
        self.assertNotEqual(self.e.correr("entrada", prompt=p), "")
        self.assertEqual(self.e.correr("entrada", prompt=p), "")

    def test_verificador_acepta_el_molde(self):
        self.e = Entorno()
        self.e.transcrip("x")
        self.e.correr("entrada", prompt=nota("Hija uno", H1))
        self.assertEqual(self.e.correr("salida", last_assistant_message=BLOQUE), "")
        self.assertTrue(self.e.registro()[-1]["ok"])

    def test_verificador_pide_reescribir_una_vez_y_no_hace_bucle(self):
        self.e = Entorno()
        self.e.transcrip("x")
        self.e.correr("entrada", prompt=nota("Hija uno", H1))
        r = json.loads(self.e.correr("salida", last_assistant_message="Listo, quedó todo hecho y verificado en el disco."))
        self.assertEqual(r["decision"], "block")
        self.assertIn("**Resumen:**", r["reason"])
        self.assertEqual(self.e.correr("salida", last_assistant_message="otra vez mal"), "")      # marca consumida
        self.assertEqual(self.e.correr("salida", last_assistant_message="otra vez mal", stop_hook_active=True), "")

    def test_con_hijas_pendientes_basta_una_linea_corta(self):
        self.e = Entorno([hija(H2, "Hija dos")])
        self.e.transcrip("x")
        self.e.correr("entrada", prompt=nota("Hija uno", H1))
        self.assertEqual(self.e.correr("salida", last_assistant_message="⏳ Llegó lo de «Hija uno». Falta «Hija dos»; por ahora no tenés que decidir nada."), "")

    def test_una_linea_sola_no_alcanza_si_era_la_ultima(self):
        self.e = Entorno()
        self.e.transcrip("x")
        self.e.correr("entrada", prompt=nota("Hija uno", H1))
        self.assertIn("block", self.e.correr("salida", last_assistant_message="Todo listo."))

    def test_molde_demasiado_largo_se_corrige_pero_el_aviso_de_plata_no_cuenta(self):
        self.e = Entorno()
        self.e.transcrip("x")
        self.e.correr("entrada", prompt=nota("Hija uno", H1))
        largo = BLOQUE + " " + "palabra " * 130
        self.assertIn("block", self.e.correr("salida", last_assistant_message=largo))
        self.e.correr("entrada", prompt=nota("Hija dos", H2))
        aviso = "⚠ " + "gasto " * 60 + "\n" + BLOQUE
        self.assertEqual(self.e.correr("salida", last_assistant_message=aviso), "")

    def test_aviso_de_alerta_mas_linea_corta_cumple(self):
        self.e = Entorno([hija(H2, "Hija dos")])
        self.e.transcrip("x")
        self.e.correr("entrada", prompt=nota("Hija uno", H1))
        msg = "⚠ No se puede deshacer: no lo toco sin tu OK.\n\n⏳ Llegó lo de «Hija uno». Falta «Hija dos»; por ahora no tenés que decidir nada."
        self.assertEqual(self.e.correr("salida", last_assistant_message=msg), "")

    def test_aviso_del_verificador_no_corta_la_tanda(self):
        self.e = Entorno()
        self.e.transcript.write_text("\n".join(json.dumps(x) for x in (
            {"type": "user", "message": {"role": "user", "content": "hola"}},
            {"type": "user", "message": {"role": "user", "content": [{"type": "text", "text": nota("Uno", H1)}]}},
            {"type": "user", "isMeta": True, "message": {"role": "user", "content": "Stop hook feedback:\nFalta el cierre fijo"}},
            {"type": "user", "message": {"role": "user", "content": [{"type": "text", "text": nota("Dos", H2)}]}})))
        self.assertIn("llegaron 3", contexto(self.e.correr("entrada", prompt=nota("Tres", H3))))

    def test_mensaje_humano_desarma_el_verificador(self):
        self.e = Entorno()
        self.e.transcrip("x")
        self.e.correr("entrada", prompt=nota("Hija uno", H1))
        self.e.correr("entrada", prompt="che, ¿y esto?")
        self.assertEqual(self.e.correr("salida", last_assistant_message="respuesta cualquiera"), "")

    def test_apagado_por_variable(self):
        self.e = Entorno()
        self.e.env["CIERRE_HIJAS"] = "0"
        self.assertEqual(self.e.correr("entrada", prompt=nota("Hija uno", H1)), "")

    def test_entrada_rota_no_traba(self):
        self.e = Entorno()
        r = subprocess.run([sys.executable, str(SCRIPT), "entrada"], input="no es json", env=self.e.env, capture_output=True, text=True)
        self.assertEqual((r.returncode, r.stdout), (0, ""))


if __name__ == "__main__":
    unittest.main()
