"""Archivado de sesiones hijas (metodo 0.44.0): nadie le pregunta a la persona si las archiva.

    python3 -m unittest discover -s plugins/metodo/scripts/tests -v
Todo con sesiones FALSAS en carpetas temporales (CLAUDE_SESIONES_DIR); nunca toca las sesiones reales.
"""
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SCRIPTS))
import sesiones_hijas as sh  # noqa: E402

GENV = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
U = {k: "local_" + v for k, v in {"arch": "11111111-1111-4111-8111-111111111111", "libre": "22222222-2222-4222-8222-222222222222",
                                    "ocup": "33333333-3333-4333-8333-333333333333"}.items()}


class Archivado(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = Path(os.path.realpath(self.tmp.name))
        self.raiz, self.repo, self.cfg = t / "ses", t / "repo", t / "cfg"
        (self.raiz / "a" / "b").mkdir(parents=True)
        (self.repo / ".claude" / "prompts").mkdir(parents=True)
        self.cfg.mkdir()
        (self.repo / "README.md").write_text("x\n", encoding="utf-8")
        for c in (("init", "-q", "-b", "main"), ("add", "-A"), ("commit", "-q", "-m", "base")):
            subprocess.run(["git", "-C", str(self.repo), *c], check=True, capture_output=True, env=GENV)
        os.environ["CLAUDE_SESIONES_DIR"] = str(self.raiz)

    def tearDown(self):
        os.environ.pop("CLAUDE_SESIONES_DIR", None)
        self.tmp.cleanup()

    def sesion(self, sid, titulo, **kw):
        d = {"sessionId": sid, "cliSessionId": "cli-" + sid, "title": titulo, "cwd": str(self.repo),
             "lastActivityAt": int(time.time() * 1000), **kw}
        (self.raiz / "a" / "b" / f"local_{sid}.json").write_text(json.dumps(d), encoding="utf-8")

    def reanudar(self, cuerpo):
        (self.repo / ".claude" / "prompts" / "REANUDAR.md").write_text("<!-- cierre 2026-10-15-x -->\n" + cuerpo, encoding="utf-8")

    def correr(self, script, yo="yo"):
        env = dict(GENV, HOME=str(self.tmp.name), CLAUDE_SESIONES_DIR=str(self.raiz), CLAUDE_CONFIG_DIR=str(self.cfg),
                   CLAUDE_CODE_SESSION_ID="cli-" + yo)
        r = subprocess.run([sys.executable, str(SCRIPTS / script)], cwd=self.repo, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env)
        return r.stdout + r.stderr

    def test_libreria_clasifica_y_calla_lo_archivado(self):
        self.sesion("madre", "Madre")
        self.sesion(U["arch"], "Ya archivada", isArchived=True, spawnedFrom={"sessionId": "madre"})
        self.sesion(U["libre"], "Libre", spawnedFrom={"sessionId": "madre"})
        self.sesion(U["ocup"], "Ocupada", spawnedFrom={"sessionId": "madre"}, sideSessionReportOwed=True)
        ses = sh.cargar()
        libres, ret = sh.clasificar(sh.hijas_de("madre", ses), ses)
        self.assertEqual([h["title"] for h, _ in libres], ["Libre"])
        self.assertEqual([h["title"] for h, _ in ret], ["Ocupada"])
        citadas = sh.citadas_en(f"{U['arch']} {U['libre']}", ses)
        self.assertEqual([h["title"] for h in citadas], ["Libre"])  # la archivada no figura

    def test_frases_de_ofrecer_archivar(self):
        self.assertTrue(sh.reanudar_afirma_archivado("Ofrecer archivarlas (solo con el sí de F)."))
        self.assertTrue(sh.reanudar_afirma_archivado("siguen en la barra lateral"))
        self.assertEqual(sh.reanudar_afirma_archivado("Hecho: arreglé el archivo de configuración"), [])

    def test_recorrido_cerrar_arrancar_sin_preguntas(self):
        self.sesion("yo", "Serie - 2")
        self.sesion(U["arch"], "Ya archivada", isArchived=True)
        self.sesion(U["libre"], "Hija libre")
        self.sesion(U["ocup"], "Hija ocupada", sideSessionReportOwed=True)
        self.reanudar(f"Hecho\nSesiones: {U['arch']}, {U['libre']} y {U['ocup']}.\n")
        out = self.correr("arrancar-check.py")
        self.assertIn(f"{U['libre']} «Hija libre»", out)
        self.assertIn("sin preguntarle a nadie", out)
        self.assertIn(f"NO ARCHIVAR «Hija ocupada» ({U['ocup']})", out)
        self.assertNotIn(U["arch"], out)
        self.assertNotIn("Ofrecer", out)
        self.assertNotIn("¿archivo", out.lower())

    def test_cerrar_frena_si_el_reanudar_ofrece_archivar_y_lista_hijas(self):
        self.sesion("yo", "Madre")
        self.sesion("h1", "Hija uno", spawnedFrom={"sessionId": "yo"})
        self.reanudar("Hecho\nSiguen en la barra lateral. Ofrecer archivarlas.\n")
        out = self.correr("cerrar-check.py")
        self.assertIn("✗ REANUDAR ofrece/afirma archivar sesiones", out)
        self.assertIn("HIJAS A ARCHIVAR (sin preguntarle a nadie): h1 «Hija uno»", out)
        self.reanudar("Hecho\nTodo unido.\n")
        out = self.correr("cerrar-check.py")
        self.assertIn("✓ REANUDAR no pregunta ni afirma estados de archivado", out)


if __name__ == "__main__":
    unittest.main()
