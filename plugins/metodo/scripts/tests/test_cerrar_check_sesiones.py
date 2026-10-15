"""cerrar-check con varias sesiones a la vez: lo que editó OTRA sesión avisa («•») y no frena; lo tuyo, o lo de dueño desconocido, frena.

    python3 -m unittest discover -s plugins/metodo/scripts/tests -v
Todo en carpetas temporales; las sesiones A (la que cierra) y B (la otra) se simulan con el mismo hook que corre de verdad
(ediciones.py registrar) y con CLAUDE_CODE_SESSION_ID.
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

SCRIPTS = Path(__file__).resolve().parent.parent
CERRAR = SCRIPTS / "cerrar-check.py"
EDICIONES = SCRIPTS / "ediciones.py"
GENV = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
A, B = "aaaaaaaa-0000-4000-8000-000000000001", "bbbbbbbb-0000-4000-8000-000000000002"


def git(cwd, *a):
    subprocess.run(["git", "-C", str(cwd), *a], check=True, capture_output=True, env=GENV)


class Sesiones(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cfg = Path(self.tmp.name) / "config"
        self.repo = Path(self.tmp.name) / "repo"
        self.carpeta = self.repo / "a"
        self.carpeta.mkdir(parents=True)
        self.cfg.mkdir()
        for n in ("uno.md", "dos.md", "decisión final.md"):
            (self.carpeta / n).write_text("x\n", encoding="utf-8")
        git(self.repo, "init", "-q", "-b", "main")
        git(self.repo, "add", "-A")
        git(self.repo, "commit", "-q", "-m", "base")
        self.inicio_a = time.time() - 3600  # A abrió hace una hora
        self.transcripcion(A, self.inicio_a)
        self.hook(A, "Bash", command="ls")  # A ya trabajó: el hook la conoce (deja su marca)

    def tearDown(self):
        self.tmp.cleanup()

    def env(self, sid):
        e = dict(os.environ, CLAUDE_CONFIG_DIR=str(self.cfg))
        e.pop("CLAUDE_SESSION_ID", None)
        if sid:
            e["CLAUDE_CODE_SESSION_ID"] = sid
        else:
            e.pop("CLAUDE_CODE_SESSION_ID", None)
        return e

    def transcripcion(self, sid, t):
        d = self.cfg / "projects" / "x"
        d.mkdir(parents=True, exist_ok=True)
        ts = datetime.fromtimestamp(t, timezone.utc).isoformat().replace("+00:00", "Z")
        (d / f"{sid}.jsonl").write_text(json.dumps({"type": "queue-operation", "timestamp": ts}) + "\n", encoding="utf-8")

    def hook(self, sid, herramienta, **entrada):
        """Corre el hook real. file_path / command van en tool_input."""
        datos = {"session_id": sid, "cwd": str(self.carpeta), "tool_name": herramienta, "tool_input": entrada}
        r = subprocess.run([sys.executable, str(EDICIONES), "registrar"], input=json.dumps(datos), capture_output=True,
                           text=True, env=self.env(sid))
        self.assertEqual((r.returncode, r.stdout, r.stderr), (0, "", ""), "el hook no imprime ni frena")

    def edita(self, sid, nombre, texto):
        """La sesión `sid` edita un archivo con la herramienta Edit y el hook lo anota."""
        p = self.carpeta / nombre
        p.write_text(texto, encoding="utf-8")
        self.hook(sid, "Edit", file_path=str(p))

    def cierra(self, sid=A, *extra):
        r = subprocess.run([sys.executable, str(CERRAR), *extra], cwd=self.carpeta, capture_output=True, text=True,
                           encoding="utf-8", env=self.env(sid))
        return r.stdout

    def linea_git(self, out):
        return next(l for l in out.splitlines() if "versionados" in l)

    def avisos(self, out):
        return [l for l in out.splitlines() if "NO son de esta sesión" in l]

    # --- el caso del 2026-10-15: archivo sucio por otra sesión ---
    def test_lo_que_edito_otra_sesion_avisa_y_no_frena(self):
        self.edita(B, "uno.md", "cambio de B\n")
        out = self.cierra()
        self.assertTrue(self.linea_git(out).startswith("✓"), out)
        self.assertEqual(len(self.avisos(out)), 1, out)
        self.assertIn("uno.md", self.avisos(out)[0])
        self.assertIn("editado por otra sesión bbbbbbbb", self.avisos(out)[0])

    # --- el hueco del 2026-10-12: lo propio sin commitear tiene que seguir frenando ---
    def test_lo_que_edite_yo_frena(self):
        self.edita(A, "uno.md", "mi cambio\n")
        out = self.cierra()
        self.assertTrue(self.linea_git(out).startswith("✗"), out)
        self.assertIn("uno.md", self.linea_git(out))
        self.assertEqual(self.avisos(out), [], out)

    def test_cada_uno_lo_suyo(self):
        self.edita(A, "uno.md", "mío\n")
        self.edita(B, "dos.md", "de B\n")
        out = self.cierra()
        self.assertTrue(self.linea_git(out).startswith("✗"), out)
        self.assertIn("uno.md", self.linea_git(out))
        self.assertNotIn("dos.md", self.linea_git(out))
        self.assertIn("dos.md", self.avisos(out)[0])

    def test_si_los_dos_editaron_el_mismo_archivo_es_tuyo(self):
        self.edita(B, "uno.md", "de B\n")
        self.edita(A, "uno.md", "de A encima\n")
        self.assertTrue(self.linea_git(self.cierra()).startswith("✗"))

    # --- ediciones que el hook de Edit/Write no ve ---
    def test_sin_dueno_conocido_frena(self):
        (self.carpeta / "uno.md").write_text("lo cambió un comando que nadie anotó\n", encoding="utf-8")
        out = self.cierra()
        self.assertTrue(self.linea_git(out).startswith("✗"), out)
        self.assertIn("--ajeno", out)

    def test_otra_sesion_anoto_pero_alguien_lo_toco_despues_frena(self):
        self.edita(B, "uno.md", "de B\n")
        futuro = time.time() + 60  # yo lo cambié con un comando (sed, python) un minuto después de B, sin que el hook lo vea
        os.utime(self.carpeta / "uno.md", (futuro, futuro))
        self.assertTrue(self.linea_git(self.cierra()).startswith("✗"))

    def test_lo_que_otra_sesion_cambio_por_bash_no_alcanza_para_darlo_por_ajeno(self):
        # B lo anotó con Bash, pero un comando que nombra un archivo no prueba que lo haya cambiado B (podría haber sido A
        # con un script que el hook no vio): sin Edit/Write de otra sesión, es tuyo y frena
        (self.carpeta / "uno.md").write_text("sed -i de B\n", encoding="utf-8")
        self.hook(B, "Bash", command="sed -i '' 's/x/y/' uno.md")
        self.assertTrue((self.cfg / "state" / "ediciones" / f"{B}.jsonl").exists())
        self.assertTrue(self.linea_git(self.cierra()).startswith("✗"))

    def test_bash_de_mi_sesion_tambien_se_anota_y_frena(self):
        (self.carpeta / "uno.md").write_text("sed -i mío\n", encoding="utf-8")
        self.hook(A, "Bash", command="sed -i '' 's/x/y/' uno.md")
        self.assertTrue(self.linea_git(self.cierra()).startswith("✗"))

    def test_bash_que_solo_lee_un_archivo_que_cambio_antes_no_lo_adopta(self):
        (self.carpeta / "uno.md").write_text("cambió antes de que B corriera nada\n", encoding="utf-8")
        time.sleep(2.5)
        self.hook(B, "Bash", command="ls")
        self.hook(B, "Bash", command="cat uno.md")  # lo nombra pero no cambió mientras corría
        self.assertFalse((self.cfg / "state" / "ediciones" / f"{B}.jsonl").exists())

    # --- lo que ya estaba sucio antes de abrir esta sesión ---
    def test_sucio_de_antes_de_abrir_la_sesion_avisa(self):
        (self.carpeta / "uno.md").write_text("ya estaba así\n", encoding="utf-8")
        self.transcripcion(A, time.time() + 10)  # la sesión de A abrió DESPUÉS de que el archivo quedara así
        out = self.cierra()
        self.assertTrue(self.linea_git(out).startswith("✓"), out)
        self.assertIn("antes de abrir esta sesión", self.avisos(out)[0])

    def test_lo_anotado_por_mi_gana_aunque_la_fecha_sea_vieja(self):
        self.edita(A, "uno.md", "mío\n")
        antes = self.inicio_a - 600  # p. ej. `cp -p` que conserva una fecha vieja
        os.utime(self.carpeta / "uno.md", (antes, antes))
        self.assertTrue(self.linea_git(self.cierra()).startswith("✗"))

    def test_fecha_vieja_conservada_no_engana(self):
        # `cp -p`, `mv` o `rsync -a` dejan la fecha de modificación vieja, pero el cambio de ficha (ctime) es de ahora
        (self.carpeta / "uno.md").write_text("lo pisé yo con cp -p\n", encoding="utf-8")
        antes = self.inicio_a - 600
        os.utime(self.carpeta / "uno.md", (antes, antes))
        self.assertTrue(self.linea_git(self.cierra()).startswith("✗"))

    def test_nombre_con_acento_y_espacio(self):
        self.edita(B, "decisión final.md", "de B\n")
        out = self.cierra()
        self.assertTrue(self.linea_git(out).startswith("✓"), out)
        self.assertIn("NO son de esta sesión", out)
        self.edita(A, "decisión final.md", "ahora mío\n")
        self.assertTrue(self.linea_git(self.cierra()).startswith("✗"))

    # --- declarar a mano ---
    def test_ajeno_declarado_a_mano_avisa(self):
        (self.carpeta / "uno.md").write_text("no sé de quién\n", encoding="utf-8")
        out = self.cierra(A, "--ajeno", "uno.md")
        self.assertTrue(self.linea_git(out).startswith("✓"), out)
        self.assertIn("lo declaraste ajeno a mano", self.avisos(out)[0])

    def test_ajeno_declarado_no_le_gana_al_registro(self):
        # el registro dice que lo editó esta sesión: --ajeno no puede tapar algo propio
        self.edita(A, "uno.md", "mío\n")
        out = self.cierra(A, "--ajeno", "uno.md")
        self.assertTrue(self.linea_git(out).startswith("✗"), out)
        self.assertIn("uno.md", self.linea_git(out))

    def test_ajeno_declarado_solo_cubre_ese_archivo(self):
        (self.carpeta / "uno.md").write_text("a\n", encoding="utf-8")
        (self.carpeta / "dos.md").write_text("b\n", encoding="utf-8")
        out = self.cierra(A, "--ajeno", "uno.md")
        self.assertTrue(self.linea_git(out).startswith("✗"), out)
        self.assertIn("dos.md", self.linea_git(out))
        self.assertNotIn("uno.md", self.linea_git(out))

    # --- sin saber quién soy: como antes, todo es mío ---
    def test_sin_id_de_sesion_todo_frena(self):
        self.edita(B, "uno.md", "de B\n")
        out = self.cierra(None)
        self.assertTrue(self.linea_git(out).startswith("✗"), out)
        self.assertIn("No sé qué sesión sos", out)

    def test_si_el_registro_no_conoce_la_sesion_todo_es_mio(self):
        # p. ej. el hook no está instalado, o el id de la sesión cambió (/clear) y el hook anotó bajo otro: no se adivina
        self.edita(B, "uno.md", "de B\n")
        out = self.cierra("cccccccc-0000-4000-8000-000000000003")
        self.assertTrue(self.linea_git(out).startswith("✗"), out)

    # --- el hook ---
    def test_hook_aguanta_basura_y_ids_raros(self):
        for entrada in ("no es json", "{}", json.dumps({"session_id": "../../etc/x", "tool_name": "Edit", "tool_input": {"file_path": "/tmp/x"}})):
            r = subprocess.run([sys.executable, str(EDICIONES), "registrar"], input=entrada, capture_output=True, text=True, env=self.env(A))
            self.assertEqual((r.returncode, r.stdout, r.stderr), (0, "", ""))
        self.assertFalse((self.cfg / "state").exists() and any((self.cfg / "state" / "ediciones").glob("*.jsonl")))

    def test_hook_borra_registros_de_mas_de_14_dias(self):
        d = self.cfg / "state" / "ediciones"
        d.mkdir(parents=True, exist_ok=True)
        viejo = d / "cccccccc.jsonl"
        viejo.write_text("{}\n", encoding="utf-8")
        hace = time.time() - 15 * 86400
        os.utime(viejo, (hace, hace))
        os.utime(d / ".limpieza", (hace, hace))  # la limpieza corre una vez por día: que toque otra vez
        self.edita(B, "uno.md", "x\n")
        self.assertFalse(viejo.exists())
        self.assertTrue((d / f"{B}.jsonl").exists())


if __name__ == "__main__":
    unittest.main()
