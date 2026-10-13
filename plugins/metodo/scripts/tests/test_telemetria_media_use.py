"""F15 del security check 0.35.0: ¿HYPERFRAMES_NO_TELEMETRY=1 apaga de verdad la telemetría de media-use (escala-diseno-video)?
Se carga telemetry.mjs con un fetch falso y se cuenta cuántas veces intenta salir a internet (nunca sale: el fetch es de mentira).
Se saltea si no hay Node.js. Correr desde la raíz del repo:
    python3 -m unittest discover -s plugins/metodo/scripts/tests -p "test_telemetria_media_use.py" -v
"""
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[4]
TELEMETRIA = RAIZ / "plugins/escala-diseno-video/skills/media-use/scripts/lib/telemetry.mjs"
PRUEBA = """
import { track } from %r;
let llamadas = 0;
globalThis.fetch = async () => { llamadas++; return {}; };
await track('prueba', {});
console.log(llamadas);
"""


@unittest.skipUnless(shutil.which("node") and TELEMETRIA.is_file(), "hace falta Node.js y el plugin escala-diseno-video")
class TelemetriaMediaUse(unittest.TestCase):
    def llamadas(self, **variables):
        with tempfile.TemporaryDirectory() as d:
            js = Path(d) / "prueba.mjs"
            js.write_text(PRUEBA % TELEMETRIA.as_uri(), encoding="utf-8")
            entorno = {k: v for k, v in os.environ.items() if k not in ("CI", "NODE_ENV", "DO_NOT_TRACK", "HYPERFRAMES_NO_TELEMETRY", "MEDIA_USE_TELEMETRY_HOST")}
            entorno.update(HOME=d, USERPROFILE=d, **variables)   # HOME falso: no escribe en ~/.hyperframes
            r = subprocess.run(["node", str(js)], capture_output=True, text=True, env=entorno, timeout=60)
            self.assertEqual(r.returncode, 0, r.stderr)
            return int(r.stdout.strip().splitlines()[-1])

    def test_control_sin_la_variable_intenta_enviar(self):
        self.assertGreaterEqual(self.llamadas(), 1)

    def test_con_hyperframes_no_telemetry_no_envia_nada(self):
        self.assertEqual(self.llamadas(HYPERFRAMES_NO_TELEMETRY="1"), 0)


if __name__ == "__main__":
    unittest.main()
