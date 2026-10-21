"""cerrar-check.py en MODO HIJA (metodo 0.52.0): una hija en carpeta compartida no escribe ni se mide por el REANUDAR.md (es del hilo
principal); se mide su TRASPASO, que lo ajeno siga intacto y que lo suyo esté subido. La sesión que no es hija cierra como siempre.

Disparo probado acá: `cerrar-check` (el paso 8 bis de /metodo:cerrar) detecta solo a la hija por los datos de la app y cambia de camino.
Todo en carpetas temporales: HOME falso con su ~/.claude y su carpeta de trabajo (con remoto «bare»), sesiones falsas
(CLAUDE_SESIONES_DIR) y registro de ediciones armado con el hook real. Nunca toca ~/.claude, sesiones ni GitHub reales.
Correr: python3 tests/test_cerrar_check_hija.py
"""
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from datetime import datetime, timezone
from pathlib import Path

AQUI = Path(__file__).resolve().parent.parent
CERRAR, EDICIONES, HIJA_PY = AQUI / "cerrar-check.py", AQUI / "ediciones.py", AQUI / "sesion_hija.py"
GENV = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t",
            GIT_CONFIG_GLOBAL="/dev/null", GIT_CONFIG_NOSYSTEM="1")
M, H = "aaaaaaaa-0000-4000-8000-00000000000a", "bbbbbbbb-0000-4000-8000-00000000000b"
SLUG = "2026-10-21-prueba"


def git(cwd, *a):
    return subprocess.run(["git", "-C", str(cwd), *a], check=True, capture_output=True, text=True, env=GENV).stdout.strip()


class CerrarCheckHija(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = Path(self.tmp.name).resolve()
        self.home, self.ses, self.notas = t / "home", t / "ses" / "x" / "y", t / "notas"
        self.cfg, self.obra = self.home / ".claude", self.home / "Proyectos" / "Estudio"
        for d in (self.cfg / "projects" / "p", self.obra / ".claude" / "prompts", self.ses, self.notas):
            d.mkdir(parents=True)
        (self.cfg / "CLAUDE.md").write_text("x\n", encoding="utf-8")
        (self.obra / "docs.md").write_text("x\n", encoding="utf-8")
        self.reanudar = self.obra / ".claude" / "prompts" / "REANUDAR.md"
        self.reanudar.write_text(f"<!-- cierre {SLUG} -->\nHecho\n", encoding="utf-8")
        for repo in (self.cfg, self.obra):
            git(repo, "init", "-q", "-b", "main")
            git(repo, "add", "-A")
            git(repo, "commit", "-q", "-m", "base")
        git(t, "init", "-q", "--bare", "-b", "main", str(t / "remoto.git"))
        git(self.obra, "remote", "add", "origin", str(t / "remoto.git"))
        git(self.obra, "push", "-q", "-u", "origin", "main")
        for sid, extra in ((M, {}), (H, {"spawnedFrom": {"sessionId": "local_" + M, "sideSession": True, "sharedFolder": True,
                                                            "name": "prueba"}})):
            d = {"sessionId": "local_" + sid, "cliSessionId": sid, "title": sid[:4], "cwd": str(self.obra), "isArchived": False,
                 "lastActivityAt": int(time.time() * 1000), **extra}
            (self.ses / f"local_{sid}.json").write_text(json.dumps(d), encoding="utf-8")
            ts = datetime.fromtimestamp(time.time() - 3600, timezone.utc).isoformat().replace("+00:00", "Z")
            (self.cfg / "projects" / "p" / f"{sid}.jsonl").write_text(json.dumps({"timestamp": ts}) + "\n", encoding="utf-8")
            self.hook(sid, "Bash", command="ls")

    def tearDown(self):
        self.tmp.cleanup()

    def env(self, sid):
        e = dict(GENV, HOME=str(self.home), CLAUDE_SESIONES_DIR=str(self.ses.parent.parent), CLAUDE_NOTAS_DIR=str(self.notas),
                 CLAUDE_CODE_SESSION_ID=sid, SUBIR_HIJA_DIRECTO="remoto")
        for v in ("CLAUDE_CONFIG_DIR", "CLAUDE_SESSION_ID"):
            e.pop(v, None)
        return e

    def hook(self, sid, herramienta, **entrada):
        datos = {"session_id": sid, "cwd": str(self.obra), "tool_name": herramienta, "tool_input": entrada}
        subprocess.run([sys.executable, str(EDICIONES), "registrar"], input=json.dumps(datos), capture_output=True, text=True,
                       env=self.env(sid), check=True)

    def hija(self, *a):
        return subprocess.run([sys.executable, str(HIJA_PY), *a], cwd=self.obra, capture_output=True, text=True, env=self.env(H))

    def cierra(self, sid):
        return subprocess.run([sys.executable, str(CERRAR), SLUG], cwd=self.obra, capture_output=True, text=True, encoding="utf-8",
                              env=self.env(sid)).stdout

    def trabajo_de_la_hija(self):
        (self.obra / "nuevo.md").write_text("de la hija\n", encoding="utf-8")
        self.hook(H, "Write", file_path=str(self.obra / "nuevo.md"))

    def borrador(self):
        b = self.home / "borrador.md"
        b.write_text("## Qué se hizo\nX\n## Qué sigue\nY\n## Decisiones de la persona\n«dale» (2026-10-21)\n## Pendientes\nninguno\n"
                     "## Sesiones\nninguna\n## Continuación propuesta\nno, cerrar\n", encoding="utf-8")
        return str(b)

    def test_hija_completa_da_verde_en_lo_suyo(self):
        self.assertIn("MODO HIJA", self.hija("detectar").stdout)
        self.hija("foto", str(self.obra))
        self.trabajo_de_la_hija()
        r = self.hija("subir", str(self.obra), "-m", "cierre de prueba", "--directo")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.hija("traspaso", "--borrador", self.borrador()).returncode, 0)
        out = self.cierra(H)
        self.assertIn("• MODO HIJA", out)
        self.assertIn("✓ Traspaso presente", out)
        self.assertIn("✓ No tocaste el REANUDAR.md", out)
        self.assertIn("✓ Foto de lo ajeno", out)
        self.assertNotIn("No existe", out)
        self.assertNotIn("✗ Falta el traspaso", out)
        self.assertEqual(self.reanudar.read_text(encoding="utf-8"), f"<!-- cierre {SLUG} -->\nHecho\n")

    def test_hija_sin_traspaso_ni_subir_frena(self):
        self.hija("foto", str(self.obra))
        self.trabajo_de_la_hija()
        out = self.cierra(H)
        self.assertIn("✗ Falta el traspaso", out)
        self.assertIn("✗ Tuyo sin subir: nuevo.md", out)

    def test_hija_que_pisa_el_reanudar_frena(self):
        self.hija("foto", str(self.obra))
        self.reanudar.write_text("pisado\n", encoding="utf-8")
        self.hook(H, "Edit", file_path=str(self.reanudar))
        out = self.cierra(H)
        self.assertIn("✗ Editaste", out)

    def test_la_coordinadora_cierra_como_siempre(self):
        out = self.cierra(M)
        self.assertNotIn("MODO HIJA", out)
        self.assertIn("✓ REANUDAR.md presente", out)


if __name__ == "__main__":
    unittest.main()
