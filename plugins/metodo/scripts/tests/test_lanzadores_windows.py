"""Tests de F3/F4 del security check 0.35.0: los lanzadores .sh de los hooks en Windows (Git Bash) y la herramienta PowerShell.

NO se puede probar en un Windows real desde acá. Estos tests simulan la rama de Windows en Mac/Linux con la variable METODO_SO_PRUEBA y un PATH falso
(un «python3» que sale con error, como el alias de la Microsoft Store, y un «py» que sí funciona), y comprueban que Mac/Linux siguen igual.

Correr desde la raíz del repo:
    python3 -m unittest discover -s plugins/metodo/scripts/tests -p "test_lanzadores_windows.py" -v
"""
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent
LANZADORES = {
    "bloquear-secretos": SCRIPTS / "bloquear-secretos.sh",
    "consultar-ecosistema": SCRIPTS / "consultar-ecosistema.sh",
    "skills-cli-tranca": SCRIPTS / "skills-externas" / "skills-cli-tranca.sh",
}
ARCHIVO = "." + "env"   # el nombre de un archivo de claves, armado por partes
BLOQUEA = {
    "bloquear-secretos": {"tool_name": "Bash", "tool_input": {"command": f"cat {ARCHIVO}"}},
    "consultar-ecosistema": {"tool_name": "Write", "tool_input": {"file_path": "/x/nuevo/index.html", "content": "<html>dashboard pantalla interfaz"}},
    "skills-cli-tranca": {"tool_name": "Bash", "tool_input": {"command": "npx skills add owner/repo"}},
}


def ejecutable(ruta, texto):
    ruta.write_text(texto)
    ruta.chmod(ruta.stat().st_mode | stat.S_IEXEC)


@unittest.skipIf(os.name == "nt", "simula Windows desde Mac/Linux con bash")
class LanzadoresEnWindows(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.d = Path(self.tmp.name)
        self.falso = self.d / "bin"
        self.falso.mkdir()
        # como el alias de la Microsoft Store: existe y sale con error. Se tapan los TRES nombres que prueba el sondeo (python3, python, py):
        # en Ubuntu hay un /usr/bin/python real que se colaba por el PATH y el freno encontraba Python (en Mac no existe, por eso pasaba ahí).
        for n in ("python3", "python", "py"):
            ejecutable(self.falso / n, "#!/bin/bash\nexit 9\n")

    def con_py_que_anda(self):
        ejecutable(self.falso / "py", f'#!/bin/bash\n[ "$1" = "-3" ] && shift\nexec "{sys.executable}" "$@"\n')

    def correr(self, nombre, payload):
        cfg = self.d / "cfg"
        cfg.mkdir(exist_ok=True)
        tmp = self.d / ("tmp-" + nombre)    # el aviso diario se anota en TMPDIR: uno por freno para que los tests no se pisen
        tmp.mkdir(exist_ok=True)
        env = {"PATH": f"{self.falso}:/usr/bin:/bin", "METODO_SO_PRUEBA": "MINGW64_NT-10.0", "TMPDIR": str(tmp), "CLAUDE_CONFIG_DIR": str(cfg),
               "HOME": str(self.d), "PYTHONIOENCODING": "ascii"}
        return subprocess.run(["/bin/bash", str(LANZADORES[nombre])], input=json.dumps(payload), capture_output=True, text=True,
                              encoding="utf-8", errors="replace", env=env, timeout=30)

    def test_con_python3_roto_y_py_3_que_anda_los_frenos_siguen_frenando(self):
        self.con_py_que_anda()
        for nombre in LANZADORES:
            with self.subTest(freno=nombre):
                r = self.correr(nombre, BLOQUEA[nombre])
                self.assertEqual(r.returncode, 2, r.stdout + r.stderr)

    def test_sin_ningun_python_deja_pasar_y_avisa_una_vez(self):
        for nombre in LANZADORES:
            with self.subTest(freno=nombre):
                r1 = self.correr(nombre, BLOQUEA[nombre])
                self.assertEqual(r1.returncode, 0, r1.stdout + r1.stderr)
                self.assertIn("no está activo", r1.stdout)
                self.assertIn("python3", r1.stdout)
                r2 = self.correr(nombre, dict(BLOQUEA[nombre], session_id="s1"))
                self.assertEqual(r2.returncode, 0)
                if nombre != "bloquear-secretos":   # este último avisa una vez por sesión (session_id), no por día
                    self.assertEqual(r2.stdout, "", "el aviso sale una sola vez por día")

    def test_la_rama_de_windows_no_se_activa_en_mac_ni_linux(self):
        # sin METODO_SO_PRUEBA y con un python3 falso que sale con error: en Mac/Linux se usa ESE python3 (la lógica de siempre) y no se prueba otro
        self.con_py_que_anda()
        env = {"PATH": f"{self.falso}:/usr/bin:/bin", "TMPDIR": str(self.d), "HOME": str(self.d)}
        r = subprocess.run(["/bin/bash", str(LANZADORES["skills-cli-tranca"])], input=json.dumps(BLOQUEA["skills-cli-tranca"]),
                           capture_output=True, text=True, env=env, timeout=30)
        self.assertNotEqual(r.returncode, 2, "en Mac/Linux no se hace el sondeo de python3/python/py -3 de Windows")

    def test_los_py_de_los_hooks_escriben_utf8_aunque_la_consola_no_lo_sea(self):
        # PYTHONIOENCODING=ascii hacía salir «auditor\xeda» (o caer el script); con UTF-8 forzado sale «auditoría»
        r = subprocess.run([sys.executable, str(SCRIPTS / "skills-externas" / "skills-cli-tranca.py")], input=json.dumps(BLOQUEA["skills-cli-tranca"]).encode(),
                           capture_output=True, env={**os.environ, "PYTHONIOENCODING": "ascii"}, timeout=30)
        self.assertEqual(r.returncode, 2)
        self.assertIn("auditoría", r.stderr.decode("utf-8"))

    def test_hooks_json_registra_powershell_en_los_dos_frenos(self):
        d = json.loads((SCRIPTS.parent / "hooks" / "hooks.json").read_text(encoding="utf-8"))
        pre = {g["hooks"][0]["command"].split("/")[-1].rstrip('"'): g["matcher"] for g in d["hooks"]["PreToolUse"]}
        self.assertIn("PowerShell", pre["bloquear-secretos.sh"].split("|"))
        self.assertIn("PowerShell", pre["skills-cli-tranca.sh"].split("|"))


@unittest.skipIf(os.name == "nt", "simula Windows desde Mac/Linux con bash")
class ReglasDenyEnWindows(unittest.TestCase):
    """F4: en Windows al-dia.sh no corre, así que ajustes-windows.py (lanzado por al-dia-auto.sh) agrega las reglas que bloquean las carpetas de llaves."""
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.d = Path(self.tmp.name)
        self.cfg = self.d / "cfg"
        self.cfg.mkdir()

    def aplicar(self, *args):
        return subprocess.run([sys.executable, str(SCRIPTS / "ajustes-windows.py"), *args], capture_output=True, text=True, encoding="utf-8",
                              env={**os.environ, "CLAUDE_CONFIG_DIR": str(self.cfg)}, timeout=30)

    def test_las_reglas_son_las_mismas_que_las_de_al_dia(self):
        import re
        al_dia = (SCRIPTS / "al-dia.sh").read_text(encoding="utf-8")
        bloque = al_dia[al_dia.index("for DR in"):al_dia.index("for DK in Read Edit")]
        de_al_dia = re.findall(r"'(~/[^']+)'", bloque)
        de_python = [r.split("(", 1)[1][:-1] for r in self.aplicar("--lista").stdout.split() if r.startswith("Read(")]
        self.assertEqual(de_al_dia, de_python)

    def test_agrega_lo_que_falta_sin_tocar_lo_demas_y_guarda_copia(self):
        original = {"model": "sonnet", "permissions": {"allow": ["Bash(ls)"], "deny": ["Read(~/.ssh/**)", "Bash(rm -rf /)"]}}
        (self.cfg / "settings.json").write_text(json.dumps(original), encoding="utf-8")
        r = self.aplicar()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        d = json.loads((self.cfg / "settings.json").read_text(encoding="utf-8"))
        self.assertEqual(d["model"], "sonnet")
        self.assertEqual(d["permissions"]["allow"], ["Bash(ls)"])
        self.assertIn("Bash(rm -rf /)", d["permissions"]["deny"])
        self.assertEqual(d["permissions"]["deny"].count("Read(~/.ssh/**)"), 1, "no duplica")
        for regla in ("Edit(~/.ssh/**)", "Read(~/.aws/**)", "Edit(~/.claude/backups/**)", "Read(~/.npmrc)"):
            self.assertIn(regla, d["permissions"]["deny"])
        self.assertEqual(d["env"]["HYPERFRAMES_NO_TELEMETRY"], "1")
        self.assertEqual(json.loads((self.cfg / "settings.json.antes-arneses").read_text(encoding="utf-8")), original)
        r2 = self.aplicar()                                    # segunda vez: nada que hacer, sin ruido
        self.assertEqual((r2.returncode, r2.stdout), (0, ""))

    def test_la_telemetria_ya_apagada_y_las_reglas_completas_no_cambian_nada(self):
        self.aplicar()
        antes = (self.cfg / "settings.json").read_text(encoding="utf-8")
        d = json.loads(antes); d["env"]["OTRA"] = "x"
        (self.cfg / "settings.json").write_text(json.dumps(d), encoding="utf-8")
        r = self.aplicar()
        self.assertEqual((r.returncode, r.stdout), (0, ""))
        self.assertEqual(json.loads((self.cfg / "settings.json").read_text(encoding="utf-8"))["env"], {"HYPERFRAMES_NO_TELEMETRY": "1", "FORCE_AUTOUPDATE_PLUGINS": "1", "OTRA": "x"})

    def test_settings_que_no_es_json_no_se_toca(self):
        (self.cfg / "settings.json").write_text("{esto no es json", encoding="utf-8")
        r = self.aplicar()
        self.assertEqual(r.returncode, 1)
        self.assertEqual((self.cfg / "settings.json").read_text(encoding="utf-8"), "{esto no es json")
        self.assertIn("✗", r.stdout)
        self.assertFalse((self.cfg / "settings.json.antes-arneses").exists())

    def leer_env(self):
        return json.loads((self.cfg / "settings.json").read_text(encoding="utf-8"))["env"]

    def test_actualizacion_de_paquetes_falta_la_clave_se_pone_y_avisa(self):
        self.aplicar()
        d = json.loads((self.cfg / "settings.json").read_text(encoding="utf-8"))
        del d["env"]["FORCE_AUTOUPDATE_PLUGINS"]; d["env"]["OTRA"] = "x"
        (self.cfg / "settings.json").write_text(json.dumps(d), encoding="utf-8")
        r = self.aplicar()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("FORCE_AUTOUPDATE_PLUGINS=1", r.stdout)
        self.assertEqual(self.leer_env(), {"HYPERFRAMES_NO_TELEMETRY": "1", "FORCE_AUTOUPDATE_PLUGINS": "1", "OTRA": "x"})

    def test_actualizacion_de_paquetes_ya_puesta_no_cambia_nada(self):
        self.aplicar()
        antes = (self.cfg / "settings.json").read_bytes()
        r = self.aplicar()
        self.assertEqual((r.returncode, r.stdout), (0, ""))
        self.assertEqual((self.cfg / "settings.json").read_bytes(), antes)

    def test_actualizacion_de_paquetes_con_valor_distinto_se_corrige_sin_tocar_otras_claves(self):
        (self.cfg / "settings.json").write_text(json.dumps({"env": {"FORCE_AUTOUPDATE_PLUGINS": "0", "OTRA": "x"}, "model": "sonnet"}), encoding="utf-8")
        self.assertEqual(self.aplicar().returncode, 0)
        d = json.loads((self.cfg / "settings.json").read_text(encoding="utf-8"))
        self.assertEqual((d["env"]["FORCE_AUTOUPDATE_PLUGINS"], d["env"]["OTRA"], d["model"]), ("1", "x", "sonnet"))

    def test_actualizacion_de_paquetes_sin_settings_se_crea(self):
        self.assertFalse((self.cfg / "settings.json").exists())
        r = self.aplicar()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(self.leer_env()["FORCE_AUTOUPDATE_PLUGINS"], "1")

    def test_en_env_solo_variables_con_prefijo_de_la_herramienta(self):
        self.aplicar()
        self.assertEqual(sorted(self.leer_env()), ["FORCE_AUTOUPDATE_PLUGINS", "HYPERFRAMES_NO_TELEMETRY"])

    def test_al_dia_auto_en_windows_aplica_las_reglas_una_vez_por_dia(self):
        falso = self.d / "bin"
        falso.mkdir()
        ejecutable(falso / "python3", "#!/bin/bash\nexit 9\n")
        ejecutable(falso / "py", f'#!/bin/bash\n[ "$1" = "-3" ] && shift\nexec "{sys.executable}" "$@"\n')
        env = {"PATH": f"{falso}:/usr/bin:/bin", "METODO_SO_PRUEBA": "MINGW64_NT-10.0", "HOME": str(self.d), "CLAUDE_CONFIG_DIR": str(self.cfg)}
        r = subprocess.run(["/bin/bash", str(SCRIPTS / "al-dia-auto.sh")], capture_output=True, text=True, encoding="utf-8", env=env, timeout=60)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("Agregué", r.stdout)
        d = json.loads((self.cfg / "settings.json").read_text(encoding="utf-8"))
        self.assertIn("Read(~/.ssh/**)", d["permissions"]["deny"])
        self.assertNotIn("Read(~/Library/Keychains/**)", d["permissions"]["deny"] if sys.platform != "darwin" else [])
        r2 = subprocess.run(["/bin/bash", str(SCRIPTS / "al-dia-auto.sh")], capture_output=True, text=True, encoding="utf-8", env=env, timeout=60)
        self.assertEqual((r2.returncode, r2.stdout), (0, ""), "una sola vez por día")


@unittest.skipIf(os.name == "nt", "usa rutas de Mac/Linux")
class PowerShellEnElFreno(unittest.TestCase):
    def correr(self, comando):
        return subprocess.run([sys.executable, str(SCRIPTS / "bloquear-secretos.py")],
                              input=json.dumps({"tool_name": "PowerShell", "tool_input": {"command": comando}}),
                              capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20)

    def test_powershell_se_frena_y_se_deja_pasar_lo_normal(self):
        self.assertEqual(self.correr(f"Get-Content {ARCHIVO}").returncode, 2)
        self.assertEqual(self.correr("Get-ChildItem Env:").returncode, 2)
        self.assertEqual(self.correr("Get-ChildItem").returncode, 0)
        self.assertEqual(self.correr("").returncode, 0)


if __name__ == "__main__":
    unittest.main()
