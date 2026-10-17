"""Pruebas de scripts/pasos-manuales.py (C150): nada nuevo puede exigirle un paso manual al cliente ni quedar fuera de Windows."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
SCRIPT = RAIZ / "scripts" / "pasos-manuales.py"
sys.path.insert(0, str(RAIZ / "scripts"))
import importlib.util

_spec = importlib.util.spec_from_file_location("pasos_manuales", SCRIPT)
pm = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pm)


def hooks(*comandos):
    return json.dumps({"hooks": {"SessionStart": [{"hooks": [{"type": "command", "command": c} for c in comandos]}]}})


class Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.r = Path(self.tmp.name)
        (self.r / "plugins" / "p" / "hooks").mkdir(parents=True)
        (self.r / "scripts").mkdir()

    def changelog(self, cuerpo):
        (self.r / "plugins" / "p" / "CHANGELOG.md").write_text(f"# p\n\n## 2.0.0 — 2026-10-17\n{cuerpo}\n\n## 1.0.0\nViene apagado, corré esto.\n", encoding="utf-8")

    def hooks(self, texto):
        (self.r / "plugins" / "p" / "hooks" / "hooks.json").write_text(texto, encoding="utf-8")

    def correr(self):
        return subprocess.run([sys.executable, str(SCRIPT), "--raiz", str(self.r)], capture_output=True, text=True)


class TestChangelog(Fixture):
    def test_viene_apagado_frena(self):
        self.changelog("Viene apagado: no cambia nada hasta que lo enciendas.")
        out = self.correr()
        self.assertEqual(out.returncode, 1)
        self.assertIn("viene apagado", out.stdout)

    def test_apagado_por_defecto_frena(self):
        self.changelog("- La función X queda apagada por defecto.")
        self.assertEqual(self.correr().returncode, 1)

    def test_orden_a_la_persona_frena(self):
        self.changelog("- Para usarlo, corré el comando de instalación.")
        self.assertEqual(self.correr().returncode, 1)

    def test_hay_que_correr_frena(self):
        self.changelog("- Después hay que correr el script.")
        self.assertEqual(self.correr().returncode, 1)

    def test_se_aplica_solo_pasa(self):
        self.changelog("Se aplica solo; no hay nada que correr.\n- Ahora el arreglo corre solo, una vez por semana.\n- Ejecuta `estructura.py auto` y activa la regla.")
        out = self.correr()
        self.assertEqual(out.returncode, 0, out.stdout)

    def test_comando_citado_entre_comillas_pasa(self):
        self.changelog("- Se apaga con `corré` esto no cuenta si es un comando citado.")
        self.assertEqual(self.correr().returncode, 0)

    def test_marca_manual_ok_permite(self):
        self.changelog("- Corré `gh auth login` una vez (credenciales de la persona). [manual-ok: las credenciales las pone siempre la persona]")
        self.assertEqual(self.correr().returncode, 0)

    def test_solo_mira_la_ultima_entrada(self):
        self.changelog("- Todo bien.")   # la 1.0.0 del fixture dice «Viene apagado, corré»: no cuenta
        self.assertEqual(self.correr().returncode, 0)

    def test_bloque_de_codigo_no_cuenta(self):
        self.changelog("```\ncorré esto\n```\n- Todo bien.")
        self.assertEqual(self.correr().returncode, 0)


class TestHooks(Fixture):
    def test_herramienta_de_mac_sin_alternativa_frena(self):
        self.hooks(hooks('xcode-select -p && /usr/bin/python3 "${CLAUDE_PLUGIN_ROOT}/scripts/reglas.py" sincronizar || true'))
        out = self.correr()
        self.assertEqual(out.returncode, 1)
        self.assertIn("p|SessionStart|xcode-select|reglas.py", out.stdout)
        self.assertIn("p|SessionStart|/usr/bin/python3|reglas.py", out.stdout)

    def test_con_alternativa_de_windows_pasa(self):
        self.hooks(hooks('osascript -e x 2>/dev/null || py -3 "${CLAUDE_PLUGIN_ROOT}/scripts/a.py" || true'))
        self.assertEqual(self.correr().returncode, 0)

    def test_patron_python3_python_py_pasa(self):
        self.hooks(hooks('python3 "${CLAUDE_PLUGIN_ROOT}/scripts/a.py" || python "${CLAUDE_PLUGIN_ROOT}/scripts/a.py" || py -3 "${CLAUDE_PLUGIN_ROOT}/scripts/a.py" || true'))
        self.assertEqual(self.correr().returncode, 0)

    def test_excepcion_con_motivo_pasa(self):
        self.hooks(hooks('xcode-select -p && "${CLAUDE_PLUGIN_ROOT}/scripts/reglas.py"'))
        (self.r / pm.EXCEPCIONES).write_text("p|SessionStart|xcode-select|reglas.py => deuda conocida, se arregla en otra tarea\n", encoding="utf-8")
        self.assertEqual(self.correr().returncode, 0)

    def test_excepcion_sin_motivo_no_vale(self):
        self.hooks(hooks('xcode-select -p && "${CLAUDE_PLUGIN_ROOT}/scripts/reglas.py"'))
        (self.r / pm.EXCEPCIONES).write_text("p|SessionStart|xcode-select|reglas.py =>   \n", encoding="utf-8")
        self.assertEqual(self.correr().returncode, 1)

    def test_json_roto_frena_sin_romper(self):
        self.hooks("{no es json")
        out = self.correr()
        self.assertEqual(out.returncode, 1)
        self.assertIn("JSON inválido", out.stdout)

    def test_sin_carpeta_plugins_es_error(self):
        (self.r / "plugins" / "p" / "hooks" / "hooks.json").unlink(missing_ok=True)
        import shutil
        shutil.rmtree(self.r / "plugins")
        self.assertEqual(self.correr().returncode, 2)


class TestElCatalogoReal(unittest.TestCase):
    def test_el_catalogo_de_este_repo_pasa(self):
        out = subprocess.run([sys.executable, str(SCRIPT)], capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stdout)

    def test_disparo_lo_corre_controles_sh(self):
        """Mand. XXIX: el control no depende de que alguien se acuerde: controles.sh (check obligatorio de cada PR) lo llama."""
        self.assertIn("scripts/pasos-manuales.py", (RAIZ / "scripts" / "controles.sh").read_text(encoding="utf-8"))
        self.assertIn("scripts/controles.sh", (RAIZ / ".github" / "workflows" / "controles.yml").read_text(encoding="utf-8"))

    def test_es_zona_sensible(self):
        src = (RAIZ / "scripts" / "zona-sensible.py").read_text(encoding="utf-8")
        self.assertIn("scripts/pasos-manuales.py", src)
        self.assertIn("scripts/pasos-manuales-excepciones.txt", src)


if __name__ == "__main__":
    unittest.main()
