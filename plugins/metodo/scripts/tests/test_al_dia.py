"""Tests de F8 del security check 0.35.0: al-dia.sh fija las librerías de Python con sus dependencias y avisa los cambios de ajustes.

No corre al-dia.sh entero (tocaría ~/.zshrc, uv, Node, la configuración de Claude): recorta el bloque de Python y lo corre con un
«python3» falso que anota con qué lo llamaron. Sin red.

Correr desde la raíz del repo:
    python3 -m unittest discover -s plugins/metodo/scripts/tests -p "test_al_dia.py" -v
"""
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent
RAIZ = SCRIPTS.parent.parent.parent
AL_DIA = SCRIPTS / "al-dia.sh"
TEXTO = AL_DIA.read_text(encoding="utf-8")
CUATRO = {"pandas": "2.3.3", "openpyxl": "3.1.5", "requests": "2.32.5", "openai": "2.48.0"}

# «python3» falso: -c con version_info → sale según FAKE_VER; -c con importlib → 0 solo si ya «instaló»; -m pip → anota y «instala».
PY_FALSO = r"""#!/bin/bash
D="$(dirname "$0")"
if [ "$1" = "-c" ]; then
  case "$2" in
    *version_info*) [ "$FAKE_VER" = "3.9" ] && exit 0 || exit 1;;
    *importlib*) [ -f "$D/instalado" ] && exit 0 || exit 1;;
  esac
  exit 0
fi
if [ "$1" = "-m" ] && [ "$2" = "pip" ]; then
  printf '%s\n' "$@" > "$D/pip-args"
  prev=""; for a in "$@"; do [ "$prev" = "-r" ] && cp "$a" "$D/pip-req"; prev="$a"; done
  echo "salida de pip de prueba"
  [ -n "${FAKE_PIP_FALLA:-}" ] && exit 1
  touch "$D/instalado"; exit 0
fi
exit 0
"""


def bloque_python():
    ini = TEXTO.index("  local CPY=")
    fin = TEXTO.index('    rm -f "$RQ4"\n  fi\n', ini) + len('    rm -f "$RQ4"\n  fi\n')
    return TEXTO[ini:fin]


def heredoc_req():
    return TEXTO[TEXTO.index("<<'REQ'\n") + len("<<'REQ'\n"):TEXTO.index("\nREQ\n")].splitlines()


class AlDiaCopias(unittest.TestCase):
    def test_las_dos_copias_son_identicas(self):
        # El portal baja scripts/al-dia.sh y el paquete trae el de plugins/metodo: si difieren, el cliente corre otro código.
        self.assertEqual((RAIZ / "scripts" / "al-dia.sh").read_bytes(), AL_DIA.read_bytes())


class AlDiaPythonFijado(unittest.TestCase):
    def test_lista_con_version_y_huella_en_cada_linea(self):
        lineas = heredoc_req()
        self.assertGreaterEqual(len(lineas), 20)
        for l in lineas:
            self.assertRegex(l, r"^[a-z0-9][a-z0-9.-]*==[0-9][^ ]* (--hash=sha256:[0-9a-f]{64} ?)+$")
        nombres = {l.split("==")[0] for l in lineas}
        self.assertEqual(len(nombres), len(lineas), "paquete repetido")
        for k, v in CUATRO.items():
            self.assertIn(f"{k}=={v} ", "\n".join(lineas) + " ")
        # dependencias que antes quedaban sueltas
        for dep in ("numpy", "urllib3", "certifi", "pydantic", "httpx"):
            self.assertIn(dep, nombres)

    def test_las_cuatro_del_otro_python_son_las_de_la_lista(self):
        cuatro = re.search(r"printf '%s\\n' ((?:[a-z]+==[0-9.]+ ?)+) > \"\$RQ4\"", TEXTO).group(1).split()
        self.assertEqual(dict(x.split("==") for x in cuatro), CUATRO)

    def correr(self, ver, ya_instalado=False, pip_falla=False):
        d = Path(tempfile.mkdtemp())
        py = d / "python3"
        py.write_text(PY_FALSO)
        py.chmod(py.stat().st_mode | stat.S_IEXEC)
        if ya_instalado:
            (d / "instalado").touch()
        guion = ("f() {\n  local avisos=() falta=() PY=%s CC=%s HOME=%s x\n%s\n  for x in ${avisos[@]+\"${avisos[@]}\"}; do echo \"AVISO:$x\"; done\n"
                 "  for x in ${falta[@]+\"${falta[@]}\"}; do echo \"FALTA:$x\"; done\n}\nf\n") % (py, d / "cc", d, bloque_python())
        (d / "cc" / "metodo").mkdir(parents=True)
        env = {**os.environ, "FAKE_VER": ver, **({"FAKE_PIP_FALLA": "1"} if pip_falla else {})}
        r = subprocess.run(["/bin/bash", "-c", guion], capture_output=True, text=True, env=env, timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        args = (d / "pip-args").read_text().split("\n") if (d / "pip-args").exists() else None
        req = (d / "pip-req").read_text().splitlines() if (d / "pip-req").exists() else None
        self.log = d / "cc" / "metodo" / "al-dia-pip.log"
        return r.stdout, args, req

    def test_python_39_instala_con_huellas_todas_las_dependencias(self):
        out, args, req = self.correr("3.9")
        self.assertIn("--require-hashes", args)
        self.assertIn("--only-binary=:all:", args)
        self.assertEqual(req, heredoc_req())
        self.assertNotIn("AVISO:", out)
        self.assertNotIn("FALTA:", out)
        self.assertIn("salida de pip de prueba", self.log.read_text())     # L4: la salida de pip queda guardada

    def test_python_39_con_pip_que_falla_lo_dice(self):
        out, args, _ = self.correr("3.9", pip_falla=True)
        self.assertIn("--require-hashes", args)
        self.assertIn("FALTA:librerías de Python (detalle en cc/metodo/al-dia-pip.log)", out)

    def test_otro_python_instala_las_cuatro_y_avisa(self):
        out, args, req = self.correr("3.12")
        self.assertNotIn("--require-hashes", args)
        self.assertEqual(sorted(req), sorted(f"{k}=={v}" for k, v in CUATRO.items()))
        self.assertIn("AVISO:tu Python de Apple no es el 3.9", out)
        self.assertNotIn("FALTA:", out)

    def test_otro_python_con_pip_que_falla_no_dice_instalé(self):  # L3
        out, _, _ = self.correr("3.12", pip_falla=True)
        self.assertNotIn("AVISO:", out)
        self.assertIn("FALTA:librerías de Python (tu Python de Apple no es el 3.9 y pip falló", out)

    def test_ya_tenia_las_cuatro_pero_no_las_dependencias_fijadas_reinstala(self):  # L4
        # El control mira las 28 de la lista: el python3 falso responde «no» a cualquier control mientras no haya instalado.
        out, args, req = self.correr("3.9")
        self.assertIsNotNone(args)
        self.assertEqual(len(req), len(heredoc_req()))

    def test_ya_instaladas_no_llama_a_pip(self):
        out, args, _ = self.correr("3.9", ya_instalado=True)
        self.assertIsNone(args)
        self.assertNotIn("FALTA:", out)


def tramo(ini, fin):
    i = TEXTO.index(ini)
    return TEXTO[i:TEXTO.index(fin, i)]


@unittest.skipUnless(sys.platform == "darwin" and shutil.which("plutil"), "al-dia.sh es de Mac: usa plutil")
class AlDiaAjustesL5(unittest.TestCase):
    """L5: settings.json se edita sobre una copia, se valida, queda una copia con fecha y se respeta el enlace simbólico."""
    BLOQUE = tramo("# 3. Actualización automática del catálogo y ajustes", "# 4. Conexión con GitHub") + \
        tramo("# 5c. Datos de uso de HyperFrames", "# 5d.")

    def correr(self, carpeta, settings):
        guion = ("f() {\n  local CAT=claude-catalogo S=%s avisos=() falta=() x\n  SR=''; AT=''\n%s\n"
                 "  for x in ${avisos[@]+\"${avisos[@]}\"}; do echo \"AVISO:$x\"; done\n"
                 "  for x in ${falta[@]+\"${falta[@]}\"}; do echo \"FALTA:$x\"; done\n}\nf\n") % (settings, self.BLOQUE)
        r = subprocess.run(["/bin/bash", "-c", guion], capture_output=True, text=True, cwd=carpeta, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout

    def test_enlace_simbolico_copia_con_fecha_y_aviso(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            real = d / "real" / "settings.json"; real.parent.mkdir()
            original = json.dumps({"model": "sonnet", "env": {"OTRA": "x"},   # como lo deja `claude plugin marketplace add`
                                   "extraKnownMarketplaces": {"claude-catalogo": {"source": {"source": "github", "repo": "x/y"}}}})
            real.write_text(original)
            enlace = d / "cc" / "settings.json"; enlace.parent.mkdir(); enlace.symlink_to(real)
            out = self.correr(d, enlace)
            self.assertNotIn("FALTA:", out, out)
            self.assertTrue(enlace.is_symlink(), "el enlace tiene que seguir siendo un enlace")
            datos = json.loads(real.read_text())
            self.assertEqual(datos["env"]["FORCE_AUTOUPDATE_PLUGINS"], "1")
            self.assertEqual(datos["env"]["OTRA"], "x")
            self.assertTrue(datos["extraKnownMarketplaces"]["claude-catalogo"]["autoUpdate"])
            self.assertIn("mcp__ccd_session_mgmt__archive_session", datos["permissions"]["allow"])
            self.assertEqual(len(datos["permissions"]["deny"]), 38)
            copias = list(real.parent.glob("settings.json.antes-al-dia-*"))
            self.assertEqual(len(copias), 1, copias)                        # una sola copia por corrida, antes del primer cambio
            self.assertEqual(copias[0].read_text(), original)
            avisos = [l for l in out.splitlines() if l.startswith("AVISO:")]
            self.assertGreaterEqual(len(avisos), 5)                         # cada cambio queda en el aviso diario
            for a in avisos:
                self.assertIn("(copia de cómo estaba: %s)" % copias[0].name, a)
            self.assertEqual(list(d.rglob("*.tmp.*")), [])                  # no quedan temporales
            # segunda corrida: nada que cambiar, ni avisos ni copias nuevas
            out2 = self.correr(d, enlace)
            self.assertNotIn("AVISO:", out2)
            self.assertEqual(len(list(real.parent.glob("settings.json.antes-al-dia-*"))), 1)

    def test_archivo_roto_no_se_reemplaza(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            s = d / "settings.json"; s.write_text("{esto no es json")
            out = self.correr(d, s)
            self.assertEqual(s.read_text(), "{esto no es json")
            self.assertIn("FALTA:actualización de paquetes en la app", out)
            self.assertNotIn("AVISO:", out)
            self.assertEqual(list(d.glob("*.tmp.*")), [])

    def test_el_trap_borra_los_temporales_de_ajustes(self):
        linea = next(l for l in TEXTO.splitlines() if l.startswith("trap "))
        self.assertIn('"${AT:-}"', linea)
        self.assertIn('rm -f "$SR".tmp.*', linea)

    def test_no_queda_escritura_directa_de_settings(self):
        self.assertIsNone(re.search(r'plutil -(replace|insert|remove)[^|\n]*"\$S"', TEXTO))


class AlDiaConfiguracionAntigravity(unittest.TestCase):
    """C58 (revisión): al-dia NO escribe reglas en Antigravity; solo saca `git -C *` y avisa de las amplias, sin ejecutar agy."""
    BLOQUE = tramo("# Configuración de Antigravity: NO se le agrega ninguna regla.", "# 5h.")

    def setUp(self):
        self.d = Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, str(self.d), True)
        self.agy = self.d / "bin" / "agy"; self.agy.parent.mkdir()
        self.marca = self.d / "AGY-SE-EJECUTO"
        self.agy.write_text("#!/bin/bash\ntouch %s\n" % self.marca); self.agy.chmod(0o755)
        self.conf = self.d / ".gemini" / "antigravity-cli" / "settings.json"

    def correr(self, agb=None, cwd=None):
        agb = str(self.agy) if agb is None else agb
        guion = ("f() {\n  local avisos=() falta=() HOME=%s AGB=%s T='' x\n%s\n"
                 "  for x in ${avisos[@]+\"${avisos[@]}\"}; do echo \"AVISO:$x\"; done\n"
                 "  for x in ${falta[@]+\"${falta[@]}\"}; do echo \"FALTA:$x\"; done\n}\nf\n") % (self.d, agb, self.BLOQUE)
        r = subprocess.run(["/bin/bash", "-c", guion], capture_output=True, text=True, timeout=60, cwd=cwd)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse(self.marca.exists(), "al-dia NO puede ejecutar agy (sin sesión abre el navegador)")
        return r.stdout

    def test_no_escribe_reglas_y_saca_git_C_una_vez(self):
        self.conf.parent.mkdir(parents=True)
        original = json.dumps({"model": "x", "permissions": {"allow": ["command(git -C *)", "command(npm test)"]}})
        self.conf.write_text(original)
        out = self.correr()
        datos = json.loads(self.conf.read_text())
        self.assertEqual(datos, {"model": "x", "permissions": {"allow": ["command(npm test)"]}})   # nada agregado
        copias = list(self.conf.parent.glob("settings.json.antes-al-dia-*"))
        self.assertEqual(len(copias), 1); self.assertEqual(copias[0].read_text(), original)
        avisos = [l for l in out.splitlines() if l.startswith("AVISO:")]
        self.assertEqual(len(avisos), 1, out)
        self.assertIn("saqué la regla «git -C *»", avisos[0])
        self.assertIn("copia de cómo estaba: %s" % copias[0].name, avisos[0])
        self.assertNotIn("FALTA:", out)
        self.assertEqual(list(self.conf.parent.glob(".settings.json.tmp.*")), [])
        out2 = self.correr()                                              # segunda corrida: nada que hacer ni avisar
        self.assertNotIn("AVISO:", out2); self.assertNotIn("FALTA:", out2)
        self.assertEqual(len(list(self.conf.parent.glob("settings.json.antes-al-dia-*"))), 1)

    def test_avisa_de_las_reglas_amplias_sin_tocarlas(self):
        self.conf.parent.mkdir(parents=True)
        amplias = ["read_url(*)", "command(*)", "command(git *)", "command(git -C*)", "command(git diff*)",
                   "command(git show*)", "command(git log*)", "command(ls*)",
                   # N1 de la segunda revisión
                   "read_file(/Users/x/Proyectos/**)", "read_file(~/notas)", "read_file(/Users/x/a.txt)",
                   "read_url(https://*.example.com)", "write_file(src/)", "command(python3 tarea.py)",
                   "command(node x.js)", "command(/bin/bash -c hola)", "command(regex:npm run .*)"]
        acotadas = ["command(git log -1 --oneline)", "command(git diff --stat)", "command(npm test)",
                    "read_url(docs.python.org)", "read_file(src/app.py)"]
        original = json.dumps({"permissions": {"allow": amplias + acotadas}})
        self.conf.write_text(original)
        out = self.correr()
        self.assertEqual(self.conf.read_text(), original)                 # no se toca
        self.assertEqual(list(self.conf.parent.glob("settings.json.antes-al-dia-*")), [])
        avisos = [l for l in out.splitlines() if l.startswith("AVISO:")]
        self.assertEqual(len(avisos), 1, out)
        for r in amplias:
            self.assertIn(r, avisos[0])
        for r in acotadas:
            self.assertNotIn(r, avisos[0])
        self.assertIn("borralas de ~/.gemini/antigravity-cli/settings.json", avisos[0])

    def test_saca_git_C_y_avisa_de_las_demas_amplias(self):
        self.conf.parent.mkdir(parents=True)
        self.conf.write_text(json.dumps({"permissions": {"allow": ["command(git -C *)", "read_url(*)"]}}))
        out = self.correr()
        self.assertEqual(json.loads(self.conf.read_text())["permissions"]["allow"], ["read_url(*)"])
        avisos = [l for l in out.splitlines() if l.startswith("AVISO:")]
        self.assertEqual(len(avisos), 2, out)
        self.assertIn("read_url(*)", avisos[1]); self.assertNotIn("git -C", avisos[1])

    def test_enlace_simbolico_edita_el_archivo_real(self):
        real = self.d / "dotfiles" / "agy.json"; real.parent.mkdir()
        real.write_text(json.dumps({"permissions": {"allow": ["command(git -C *)"]}}))
        self.conf.parent.mkdir(parents=True); self.conf.symlink_to(real)
        out = self.correr()
        self.assertTrue(self.conf.is_symlink())
        self.assertEqual(json.loads(real.read_text())["permissions"]["allow"], [])
        self.assertIn("AVISO:Antigravity: saqué", out)

    def test_sin_configuracion_o_sin_agy_no_hace_nada(self):
        out = self.correr()
        self.assertFalse(self.conf.exists(), "no se crea la configuración: agy nunca se abrió")
        self.assertNotIn("AVISO:", out); self.assertNotIn("FALTA:", out)
        self.conf.parent.mkdir(parents=True); self.conf.write_text('{"permissions": {"allow": ["command(git -C *)"]}}')
        out = self.correr(agb="")
        self.assertEqual(self.conf.read_text(), '{"permissions": {"allow": ["command(git -C *)"]}}')
        self.assertNotIn("AVISO:", out)

    def test_configuracion_vacia_o_sin_permisos_no_hace_nada(self):
        self.conf.parent.mkdir(parents=True); self.conf.write_text('{"model": "x"}')
        out = self.correr()
        self.assertEqual(self.conf.read_text(), '{"model": "x"}')
        self.assertNotIn("AVISO:", out); self.assertNotIn("FALTA:", out)

    def test_configuracion_rota_no_se_toca(self):
        self.conf.parent.mkdir(parents=True); self.conf.write_text("{esto no es json")
        out = self.correr()
        self.assertEqual(self.conf.read_text(), "{esto no es json")
        self.assertIn("FALTA:configuración de Antigravity", out)
        self.assertEqual([x.name for x in self.conf.parent.iterdir()], ["settings.json"])

    def test_un_json_py_plantado_en_la_carpeta_no_se_ejecuta(self):
        planta = self.d / "proyecto-hostil"; planta.mkdir()
        testigo = self.d / "JSON-PLANTADO-SE-EJECUTO"
        (planta / "json.py").write_text("open(%r, 'w').write('x')\nfrom json import *\n" % str(testigo))
        # control: sin -I, el Python de Apple sí carga el json.py de la carpeta (si no, la prueba no probaría nada)
        subprocess.run(["/usr/bin/python3", "-", "x"], input="import json\n", text=True, cwd=planta, capture_output=True)
        self.assertTrue(testigo.exists(), "el control no cargó el json.py plantado: la prueba no sirve")
        testigo.unlink()
        self.conf.parent.mkdir(parents=True)
        self.conf.write_text(json.dumps({"permissions": {"allow": ["command(git -C *)"]}}))
        out = self.correr(cwd=planta)
        self.assertFalse(testigo.exists(), "al-dia cargó el json.py de la carpeta desde la que se corrió")
        self.assertIn("AVISO:Antigravity: saqué", out)

    def test_el_bloque_no_escribe_reglas_allow_ni_deny(self):
        # la única escritura de allow es filtrar (sacar git -C); deny no se toca
        self.assertEqual(re.findall(r'\["allow"\]\s*=.*', self.BLOQUE), ['["allow"] = [r for r in allow if r not in SACAR]'])
        self.assertNotRegex(self.BLOQUE, r'\.(append|extend|insert)\(|setdefault\(|"deny"')


class AlDiaPythonAislado(unittest.TestCase):
    """N3: ningún Python con código en línea carga módulos plantados en la carpeta desde la que se corre al-dia."""

    def test_toda_llamada_en_linea_lleva_menos_I(self):
        for archivo in (AL_DIA, SCRIPTS / "al-dia-auto.sh"):
            texto = archivo.read_text(encoding="utf-8")
            self.assertGreater(len(re.findall(r"/usr/bin/python3 -I (-c|-) ", texto)), 0, archivo.name)
            self.assertEqual(re.findall(r"/usr/bin/python3 (?!-I )(-c|-) ", texto), [], archivo.name)

    def test_el_python_con_librerias_corre_parado_en_la_raiz(self):
        self.assertIn('pyd() { ( cd / && "$PY" "$@" ); }', TEXTO)
        self.assertEqual(re.findall(r'"\$PY" -[cm]', TEXTO), [])


class AlDiaAvisaCambios(unittest.TestCase):
    def test_cambios_de_ajustes_y_permisos_van_al_aviso_diario(self):
        # En --auto el echo no lo ve nadie: tienen que quedar en avisos (al-dia.aviso, que se muestra al abrir sesión).
        self.assertRegex(TEXTO, r'\|\| ajustar "prendí la actualización automática de paquetes en la app \(FORCE_AUTOUPDATE_PLUGINS=1[^"]*" e_force')
        self.assertRegex(TEXTO, r'\|\| ajustar "agregué a tu settings.json el permiso \$AP[^"]*" e_archivar')
        self.assertIn('avisos+=("$1${CAJ:+ (copia de cómo estaba: $CAJ)}")', TEXTO)


if __name__ == "__main__":
    unittest.main()
