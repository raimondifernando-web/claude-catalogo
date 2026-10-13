"""Tests de F8 del security check 0.35.0: al-dia.sh fija las librerías de Python con sus dependencias y avisa los cambios de ajustes.

No corre al-dia.sh entero (tocaría ~/.zshrc, uv, Node, la configuración de Claude): recorta el bloque de Python y lo corre con un
«python3» falso que anota con qué lo llamaron. Sin red.

Correr desde la raíz del repo:
    python3 -m unittest discover -s plugins/metodo/scripts/tests -p "test_al_dia.py" -v
"""
import os
import re
import stat
import subprocess
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


class AlDiaAvisaCambios(unittest.TestCase):
    def test_cambios_de_ajustes_y_permisos_van_al_aviso_diario(self):
        # En --auto el echo no lo ve nadie: tienen que quedar en avisos (al-dia.aviso, que se muestra al abrir sesión).
        self.assertRegex(TEXTO, r'FORCE_AUTOUPDATE_PLUGINS -string 1 "\$S" 2>/dev/null \\\n\s+&& avisos\+=\(')
        self.assertRegex(TEXTO, r'mv "\$AT" "\$S" && avisos\+=\("agregué a tu settings.json el permiso')


if __name__ == "__main__":
    unittest.main()
