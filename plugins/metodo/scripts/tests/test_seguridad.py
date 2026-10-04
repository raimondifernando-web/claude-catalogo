"""Pruebas de seguridad.py y seguridad-auto.sh. Todo bajo carpetas temporales (CLAUDE_CONFIG_DIR y HOME):
nunca toca la configuración real. `gh` queda fuera del PATH, así que GitHub nunca se consulta."""
import json
import os
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

AQUI = Path(__file__).resolve().parent
SCRIPT = AQUI.parent / "seguridad.py"
AUTO = AQUI.parent / "seguridad-auto.sh"
VALOR = "valor-super-secreto-que-nunca-debe-aparecer-123"
URL_CON_CLAVE = "https://usuario:otro-secreto-de-la-url@github.com/alguien/mi-repo.git"


@unittest.skipIf(os.name == "nt", "el chequeo de seguridad lo lanza el aviso de Mac")
class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        b = Path(self.tmp.name)
        self.home = b / "home"
        self.home.mkdir()
        self.cfgdir = b / "config"
        self.metodo = self.cfgdir / "metodo"
        self.metodo.mkdir(parents=True)
        self.gitcfg = b / "gitconfig"
        self.gitcfg.write_text("")
        self.env = {"HOME": str(self.home), "CLAUDE_CONFIG_DIR": str(self.cfgdir), "PATH": "/usr/bin:/bin",
                    "GIT_CONFIG_GLOBAL": str(self.gitcfg), "GIT_CONFIG_NOSYSTEM": "1", "LANG": "en_US.UTF-8",
                    "GIT_AUTHOR_NAME": "P", "GIT_AUTHOR_EMAIL": "p@example.com",
                    "GIT_COMMITTER_NAME": "P", "GIT_COMMITTER_EMAIL": "p@example.com"}

    def tearDown(self):
        self.tmp.cleanup()

    def py(self, *args):
        r = subprocess.run([sys.executable, str(SCRIPT)] + list(args), env=self.env, text=True,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
        return r.returncode, r.stdout + r.stderr

    def git(self, repo, *args):
        subprocess.run(["git", "-C", str(repo)] + list(args), env=self.env, check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def repo_limpio(self, nombre):
        r = self.home / nombre
        r.mkdir()
        self.git(r, "init", "-q", "-b", "main")
        (r / ".gitignore").write_text(".env\n")
        (r / "app.py").write_text("x = 1\n")
        e = r / ".env"
        e.write_text("API_KEY={}\n".format(VALOR))
        e.chmod(0o600)
        self.git(r, "add", ".gitignore", "app.py")
        self.git(r, "commit", "-q", "-m", "inicio")
        return r

    def repo_sucio(self, nombre):
        r = self.home / nombre
        r.mkdir()
        self.git(r, "init", "-q", "-b", "main")
        (r / "app.py").write_text("x = 1\n")
        e = r / ".env"
        e.write_text("export API_KEY={}\nOTRA=1\n".format(VALOR))
        e.chmod(0o644)
        wf = r / ".github" / "workflows"
        wf.mkdir(parents=True)
        (wf / "ci.yml").write_text("on: [pull_request_target]\njobs:\n  a:\n    steps:\n"
                                   "      - uses: actions/checkout@v4\n"
                                   "      - uses: actions/setup-node@0123456789abcdef0123456789abcdef01234567\n"
                                   "      - uses: ./local-action\n")
        self.git(r, "add", "-f", "app.py", ".env", ".github")
        self.git(r, "commit", "-q", "-m", "inicio")
        self.git(r, "remote", "add", "origin", URL_CON_CLAVE)
        return r

    def lista(self, repos):
        (self.metodo / "seguridad.json").write_text(json.dumps({"repos": repos}))


class SeguridadPyTest(Base):
    def test_sin_lista_no_hace_nada_y_lo_dice(self):
        rc, out = self.py("correr")
        self.assertEqual(rc, 0)
        self.assertIn("no hay lista de repositorios", out)
        self.assertFalse((self.metodo / "seguridad.resultado").exists())
        self.assertFalse((self.metodo / "seguridad").exists())

    def test_repo_limpio_da_ok(self):
        self.repo_limpio("mi-repo")
        self.lista([{"ruta": "~/mi-repo", "claves": ["API_KEY"]}])
        rc, out = self.py("correr")
        self.assertEqual(rc, 0, out)
        self.assertIn("todo bien ✓", out)
        self.assertTrue((self.metodo / "seguridad.resultado").read_text().startswith("ok "))

    def test_repo_con_problemas_los_marca_sin_mostrar_valores(self):
        self.repo_sucio("otro-repo")
        self.lista([{"ruta": "~/otro-repo", "claves": ["API_KEY", "FALTANTE"], "distribucion": True}])
        rc, out = self.py("correr")
        self.assertEqual(rc, 0, out)
        res = (self.metodo / "seguridad.resultado").read_text()
        self.assertRegex(res, r"^\d+ ✗ \(otro-repo: ")
        resumen = next((self.metodo / "seguridad").glob("*/resumen.json"))
        estados = {i["id"]: i["estado"] for i in json.loads(resumen.read_text())["repos"][0]["items"]}
        for cid in ("ENV-001", "ENV-002", "GIT-001", "GIT-002", "GH-001", "ACT-001", "ACT-002", "ACT-003", "DIST-001"):
            self.assertEqual(estados[cid], "FLAG", cid)
        evid = {i["id"]: i["evidencia"] for i in json.loads(resumen.read_text())["repos"][0]["items"]}
        self.assertIn("están 1/2", evid["ENV-002"])          # export API_KEY= cuenta; FALTANTE no
        self.assertIn("1 acción(es) sin fijar", evid["ACT-001"])  # la fijada y la local no cuentan
        # ni el valor de la clave ni la dirección con clave aparecen en ningún lado
        todo = out + res + "".join(p.read_text() for p in (self.metodo / "seguridad").rglob("*") if p.is_file())
        self.assertNotIn(VALOR, todo)
        self.assertNotIn("otro-secreto-de-la-url", todo)
        # informes solo para el usuario
        for p in (self.metodo / "seguridad").rglob("*"):
            modo = stat.S_IMODE(p.stat().st_mode)
            self.assertEqual(modo & 0o077, 0, p)

    def test_solo_lectura_no_cambia_el_repo(self):
        r = self.repo_sucio("otro-repo")
        antes = {str(p): (p.stat().st_mtime_ns, p.stat().st_mode) for p in r.rglob("*") if ".git" not in p.parts}
        estado_antes = subprocess.run(["git", "-C", str(r), "status", "--porcelain"], env=self.env,
                                      stdout=subprocess.PIPE, text=True).stdout
        self.lista([{"ruta": str(r)}])
        self.py("correr")
        despues = {str(p): (p.stat().st_mtime_ns, p.stat().st_mode) for p in r.rglob("*") if ".git" not in p.parts}
        self.assertEqual(antes, despues)
        self.assertEqual(estado_antes, subprocess.run(["git", "-C", str(r), "status", "--porcelain"], env=self.env,
                                                      stdout=subprocess.PIPE, text=True).stdout)

    def test_carpeta_inexistente_falla_sin_frenar_a_los_demas(self):
        self.repo_limpio("mi-repo")
        self.lista([{"ruta": "~/no-existe"}, {"ruta": "~/mi-repo"}])
        rc, out = self.py("correr")
        self.assertEqual(rc, 0, out)
        res = (self.metodo / "seguridad.resultado").read_text()
        self.assertIn("1 ✗ (no-existe: no encontré la carpeta", res)

    def test_negacion_en_gitignore_y_env_dentro_de_dist(self):
        r = self.repo_limpio("mi-repo")
        (r / ".gitignore").write_text(".env\n!.env\n")
        (r / "dist").mkdir()
        (r / "dist" / ".env").write_text("X=1\n")
        self.lista([{"ruta": "~/mi-repo", "distribucion": True}])
        self.py("correr")
        resumen = next((self.metodo / "seguridad").glob("*/resumen.json"))
        estados = {i["id"]: i["estado"] for i in json.loads(resumen.read_text())["repos"][0]["items"]}
        self.assertEqual(estados["GIT-001"], "FLAG")
        self.assertEqual(estados["DIST-001"], "FLAG")

    def test_lista_rota_deja_aviso(self):
        (self.metodo / "seguridad.json").write_text("{ esto no es json")
        rc, out = self.py("correr")
        self.assertEqual(rc, 1)
        self.assertIn("tiene un error ✗", (self.metodo / "seguridad.resultado").read_text())

    def test_agregar_arma_y_actualiza_la_lista(self):
        self.repo_limpio("mi-repo")
        rc, out = self.py("agregar", str(self.home / "mi-repo"), "--claves", "API_KEY")
        self.assertEqual(rc, 0, out)
        self.assertIn("Listo ✓", out)
        d = json.loads((self.metodo / "seguridad.json").read_text())
        self.assertEqual(d["repos"], [{"ruta": "~/mi-repo", "claves": ["API_KEY"]}])
        rc, out = self.py("agregar", "~/mi-repo", "--publico")   # el mismo repo no se duplica
        d = json.loads((self.metodo / "seguridad.json").read_text())
        self.assertEqual(d["repos"], [{"ruta": "~/mi-repo", "publico": True}])
        rc, out = self.py("agregar", "~/mi-repo", "--claves", "API_KEY=algo")
        self.assertEqual(rc, 1)
        self.assertIn("sin valor", out)
        rc, out = self.py("agregar", "~/no-existe")
        self.assertEqual(rc, 1)


class SeguridadAutoTest(Base):
    def auto(self):
        r = subprocess.run(["bash", str(AUTO)], env=self.env, text=True, stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, timeout=20)
        return r.stdout.strip().splitlines()

    def esperar(self, condicion, segundos=30):
        fin = time.time() + segundos
        while time.time() < fin:
            if condicion():
                return True
            time.sleep(0.2)
        return False

    def test_sin_lista_no_hace_nada(self):
        self.assertEqual(self.auto(), [])
        self.assertEqual(sorted(p.name for p in self.metodo.iterdir()), [])

    def test_apagado_no_corre(self):
        self.repo_limpio("mi-repo")
        self.lista([{"ruta": "~/mi-repo"}])
        (self.metodo / "seguridad.apagado").write_text("")
        self.assertEqual(self.auto(), [])
        self.assertFalse((self.metodo / "seguridad.ultimo").exists())

    @unittest.skipUnless(sys.platform == "darwin", "el lanzador es para Mac")
    def test_corre_en_segundo_plano_y_avisa_una_sola_vez(self):
        self.repo_sucio("otro-repo")
        self.lista([{"ruta": "~/otro-repo"}])
        self.assertEqual(self.auto(), [])           # lanza y no espera: no dice nada
        res = self.metodo / "seguridad.resultado"
        self.assertTrue(self.esperar(lambda: res.exists() and not (self.metodo / "seguridad.corriendo").exists()))
        self.assertTrue((self.metodo / "seguridad.ultimo").exists())
        lineas = self.auto()                         # próxima apertura: una línea
        self.assertEqual(len(lineas), 1)
        self.assertTrue(lineas[0].startswith("Chequeo de seguridad: "), lineas)
        self.assertTrue(lineas[0].endswith("Avisale a quien te acompaña."), lineas)
        self.assertIn("✗", lineas[0])
        self.assertEqual(self.auto(), [])            # ya visto: no repite
        # dentro del mes no vuelve a correr
        mtime = res.stat().st_mtime
        time.sleep(1.1)
        self.auto()
        time.sleep(1)
        self.assertEqual(res.stat().st_mtime, mtime)

    def test_ok_no_avisa(self):
        (self.metodo / "seguridad.resultado").write_text("ok 2026-10-03\n")
        self.assertEqual(self.auto(), [])

    @unittest.skipUnless(sys.platform == "darwin", "sin xcode-select el lanzador no corre")
    def test_candado_de_un_proceso_muerto_se_libera(self):
        self.repo_limpio("mi-repo")
        self.lista([{"ruta": "~/mi-repo"}])
        (self.metodo / "seguridad.corriendo").mkdir()
        (self.metodo / "seguridad.corriendo" / "pid").write_text("999999")
        self.auto()
        self.assertTrue((self.metodo / "seguridad.ultimo").exists())
        self.assertTrue(self.esperar(lambda: not (self.metodo / "seguridad.corriendo").exists()))

    def test_candado_vivo_no_lanza_otra(self):
        self.repo_limpio("mi-repo")
        self.lista([{"ruta": "~/mi-repo"}])
        (self.metodo / "seguridad.corriendo").mkdir()
        (self.metodo / "seguridad.corriendo" / "pid").write_text(str(os.getpid()))
        self.auto()
        self.assertFalse((self.metodo / "seguridad.ultimo").exists())


if __name__ == "__main__":
    unittest.main()
