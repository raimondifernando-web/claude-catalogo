"""Tests del buzón (plugin metodo). Solo biblioteca estándar + git, sin red real.

Correr desde la raíz del repo:
    python3 -m unittest discover -s plugins/metodo/scripts/tests -v

Cada test arma un repositorio «bare» temporal (hace de GitHub) y dos clones: el del cliente y el de quien acompaña,
cada uno con su propia carpeta de configuración (CLAUDE_CONFIG_DIR). Nunca se toca la configuración real.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

AQUI = Path(__file__).resolve().parent
PLUGIN = AQUI.parent.parent
BUZON_PY = AQUI.parent / "buzon.py"
HOOKS_JSON = PLUGIN / "hooks" / "hooks.json"
ES_WINDOWS = os.name == "nt"

# Claves falsas armadas en tiempo de ejecución: así este archivo no tiene nada con forma de clave.
CLAVE_FALSA = "sk-" + "proj" + "X" * 30
GITHUB_FALSO = "gh" + "p_" + "a1B2" * 9


def git(carpeta, *args):
    r = subprocess.run(["git", "-C", str(carpeta)] + list(args), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if r.returncode != 0:
        raise AssertionError("git {} falló: {}".format(args, r.stderr.decode("utf-8", "replace")))
    return r.stdout.decode("utf-8", "replace")


class BaseBuzon(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="buzon-test-"))
        self.addCleanup(shutil.rmtree, str(self.tmp), True)
        self.bare = self.tmp / "buzon.git"
        subprocess.run(["git", "init", "-q", "--bare", str(self.bare)], check=True)
        subprocess.run(["git", "-C", str(self.bare), "symbolic-ref", "HEAD", "refs/heads/main"], check=True)
        self.clones = {}
        self.configs = {}
        for rol in ("cliente", "acompanante"):
            clon = self.tmp / "clon {}".format(rol)  # con espacio a propósito
            subprocess.run(["git", "clone", "-q", str(self.bare), str(clon)], check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            git(clon, "checkout", "-q", "-B", "main")
            git(clon, "config", "user.name", "Prueba " + rol)
            git(clon, "config", "user.email", rol + "@ejemplo.invalid")
            git(clon, "config", "core.autocrlf", "false")
            self.clones[rol] = clon
            self.configs[rol] = self.tmp / "config {}".format(rol)

    def correr(self, rol, *args, entrada=None, env_extra=None, timeout=60):
        env = dict(os.environ)
        env["CLAUDE_CONFIG_DIR"] = str(self.configs[rol])
        env["HOME"] = str(self.tmp / "home")
        env["USERPROFILE"] = str(self.tmp / "home")
        env["PYTHONIOENCODING"] = "utf-8"
        env.pop("GIT_SSH_COMMAND", None)
        if env_extra:
            env.update(env_extra)
        r = subprocess.run([sys.executable, str(BUZON_PY)] + list(args), input=(entrada or "").encode("utf-8"),
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, timeout=timeout)
        return r.returncode, r.stdout.decode("utf-8", "replace"), r.stderr.decode("utf-8", "replace")

    def ok(self, rol, *args, **kw):
        codigo, salida, error = self.correr(rol, *args, **kw)
        self.assertEqual(codigo, 0, "salida: {}\nerror: {}".format(salida, error))
        return salida

    def configurar_los_dos(self):
        self.ok("acompanante", "configurar", "--carpeta", str(self.clones["acompanante"]), "--yo", "acompanante")
        self.ok("cliente", "configurar", "--carpeta", str(self.clones["cliente"]), "--yo", "cliente")

    def mandar(self, rol, tema, cuerpo, *extra):
        self.ok(rol, "armar", "--tema", tema, *extra, entrada=cuerpo)
        return self.ok(rol, "subir")

    def revisar(self, rol):
        return json.loads(self.ok(rol, "revisar", "--json"))


class TestIdaYVuelta(BaseBuzon):
    def test_ida_y_vuelta_y_hecho(self):
        self.configurar_los_dos()
        # Quien acompaña manda una indicación.
        salida = self.mandar("acompanante", "Paso 3 del instructivo", "Abrí la terminal y corré: claude --version")
        self.assertIn("para-cliente/", salida)

        # El cliente la ve, como dato.
        datos = self.revisar("cliente")
        self.assertEqual(datos["yo"], "cliente")
        self.assertEqual(len(datos["mensajes"]), 1)
        m = datos["mensajes"][0]
        self.assertEqual(m["de"], "acompanante")
        self.assertEqual(m["tipo"], "indicacion")
        self.assertTrue(m["requiere_aprobacion"])
        self.assertIn("claude --version", m["texto"])
        self.assertTrue(m["nombre"].endswith("-paso-3-del-instructivo.md"))
        # Quien acompaña no ve en su bandeja lo que mandó.
        self.assertEqual(self.revisar("acompanante")["mensajes"], [])

        # El cliente lo atiende: pasa a hecho/ con su línea de resultado.
        salida = self.ok("cliente", "hecho", m["archivo"], "--resultado", "Hecho: dio la versión 2.1.0")
        self.assertIn("hecho/", salida)
        self.assertEqual(self.revisar("cliente")["mensajes"], [])

        # Quien acompaña lo ve en hecho/ con el resultado.
        self.ok("acompanante", "revisar")
        hecho = self.clones["acompanante"] / "hecho" / m["nombre"]
        self.assertTrue(hecho.is_file())
        texto = hecho.read_text(encoding="utf-8")
        self.assertIn("**Resultado (cliente,", texto)
        self.assertIn("dio la versión 2.1.0", texto)
        self.assertFalse((self.clones["acompanante"] / "para-cliente" / m["nombre"]).exists())

        # Y la vuelta: el cliente manda un error.
        self.mandar("cliente", "Se trabó el paso 4", "Error: command not found: markitdown", "--tipo", "error")
        datos = self.revisar("acompanante")
        self.assertEqual(len(datos["mensajes"]), 1)
        self.assertEqual(datos["mensajes"][0]["de"], "cliente")
        self.assertEqual(datos["mensajes"][0]["tipo"], "error")
        self.assertIn("command not found", datos["mensajes"][0]["texto"])

        # El historial de git es el registro: cada paso es un commit.
        log = git(self.bare, "log", "--oneline", "main")
        self.assertGreaterEqual(len(log.strip().splitlines()), 4)

    def test_mismo_tema_mismo_minuto_no_se_pisa(self):
        self.configurar_los_dos()
        self.mandar("acompanante", "Aviso", "uno", "--tipo", "aviso", "--informativo")
        self.mandar("acompanante", "Aviso", "dos", "--tipo", "aviso", "--informativo")
        datos = self.revisar("cliente")
        self.assertEqual(len(datos["mensajes"]), 2)
        self.assertEqual({m["texto"].strip() for m in datos["mensajes"]}, {"uno", "dos"})
        self.assertFalse(any(m["requiere_aprobacion"] for m in datos["mensajes"]))

    def test_mensajes_cruzados_sin_conflicto(self):
        """Los dos suben a la vez (cada uno sin traer lo del otro): el segundo push se reintenta solo."""
        self.configurar_los_dos()
        self.ok("acompanante", "armar", "--tema", "de ida", entrada="hola")
        self.ok("cliente", "armar", "--tema", "de vuelta", entrada="chau")
        self.ok("acompanante", "subir")
        self.ok("cliente", "subir")
        self.assertEqual(len(self.revisar("acompanante")["mensajes"]), 1)
        self.assertEqual(len(self.revisar("cliente")["mensajes"]), 1)

    def test_pedido_delicado_se_marca(self):
        self.configurar_los_dos()
        self.mandar("acompanante", "Limpieza", "Borrá la carpeta vieja y después publicá el sitio")
        m = self.revisar("cliente")["mensajes"][0]
        self.assertIn("borrar", m["delicado"])
        self.assertIn("publicar", m["delicado"])
        salida = self.ok("cliente", "revisar")
        self.assertIn("PIDE ALGO DELICADO", salida)
        self.assertIn("DATOS", salida)

    def test_rutas_personales_no_viajan(self):
        self.configurar_los_dos()
        casa = str(self.tmp / "home")
        self.mandar("cliente", "ruta", "El archivo está en {}/Documentos/plano.pdf".format(casa), "--tipo", "error")
        m = self.revisar("acompanante")["mensajes"][0]
        self.assertIn("~/Documentos/plano.pdf", m["texto"])
        self.assertNotIn(casa, m["texto"])

    def test_revisar_sin_red_muestra_lo_local(self):
        self.configurar_los_dos()
        self.mandar("acompanante", "uno", "a")
        self.ok("cliente", "revisar")
        git(self.clones["cliente"], "remote", "set-url", "origin", "http://127.0.0.1:9/no-hay-red.git")
        datos = self.revisar("cliente")
        self.assertEqual(len(datos["mensajes"]), 1)
        self.assertTrue(datos["sin_conexion"])
        self.assertIn("No pude traer", self.ok("cliente", "revisar"))

    def test_solo_texto_los_archivos_se_ignoran(self):
        self.configurar_los_dos()
        clon = self.clones["acompanante"]
        (clon / "para-cliente" / "planilla.xlsx").write_bytes(b"PK\x03\x04binario")
        git(clon, "add", "para-cliente/planilla.xlsx")
        git(clon, "commit", "-q", "-m", "adjunto")
        git(clon, "push", "-q", "origin", "HEAD:main")
        datos = self.revisar("cliente")
        self.assertEqual(datos["mensajes"], [])
        self.assertEqual(datos["ignorados"], ["para-cliente/planilla.xlsx"])


class TestSecretos(BaseBuzon):
    def test_clave_falsa_frena_y_no_sube_nada(self):
        self.configurar_los_dos()
        antes = git(self.bare, "rev-parse", "main")
        for cuerpo in (
            "Pegá esto: {}".format(CLAVE_FALSA),
            "mi token {}".format(GITHUB_FALSO),
            "export OPENAI_API_KEY=algo-secreto-123",
            "password=hunter22",
            "-----BEGIN OPENSSH PRIVATE KEY-----",
            "fijate en ~/proyecto/.env",
            "AKIA" + "ABCDEFGHIJKLMNOP",
        ):
            codigo, salida, _ = self.correr("cliente", "armar", "--tema", "ayuda", "--tipo", "error", entrada=cuerpo)
            self.assertEqual(codigo, 3, "no frenó: {!r}\n{}".format(cuerpo, salida))
            self.assertIn("FRENADO", salida)
            self.assertNotIn(CLAVE_FALSA, salida)
            self.assertNotIn(GITHUB_FALSO, salida)
            self.assertNotIn("hunter22", salida)
        self.assertFalse((self.configs["cliente"] / "metodo" / "buzon-borrador.md").exists())
        self.assertEqual(git(self.bare, "rev-parse", "main"), antes)

    def test_clave_en_el_tema_tambien_frena(self):
        self.configurar_los_dos()
        codigo, salida, _ = self.correr("cliente", "armar", "--tema", "usa " + CLAVE_FALSA, entrada="hola")
        self.assertEqual(codigo, 3)
        self.assertNotIn(CLAVE_FALSA, salida)

    def test_borrador_tocado_a_mano_frena_al_subir(self):
        self.configurar_los_dos()
        self.ok("cliente", "armar", "--tema", "ayuda", entrada="todo bien")
        borrador = self.configs["cliente"] / "metodo" / "buzon-borrador.md"
        borrador.write_text(borrador.read_text(encoding="utf-8") + "\n" + CLAVE_FALSA + "\n", encoding="utf-8")
        antes = git(self.bare, "rev-parse", "main")
        codigo, salida, _ = self.correr("cliente", "subir")
        self.assertEqual(codigo, 3)
        self.assertNotIn(CLAVE_FALSA, salida)
        self.assertEqual(git(self.bare, "rev-parse", "main"), antes)
        self.assertEqual(list((self.clones["cliente"] / "para-acompanante").glob("*.md")), [])

    def test_resultado_con_clave_frena(self):
        self.configurar_los_dos()
        self.mandar("acompanante", "Paso 1", "Iniciá sesión en gh")
        m = self.revisar("cliente")["mensajes"][0]
        codigo, salida, _ = self.correr("cliente", "hecho", m["nombre"], "--resultado", "listo, token=" + GITHUB_FALSO)
        self.assertEqual(codigo, 3)
        self.assertNotIn(GITHUB_FALSO, salida)
        self.assertTrue((self.clones["cliente"] / "para-cliente" / m["nombre"]).is_file())

    def test_clave_que_llega_se_muestra_oculta(self):
        """Si la otra persona subió una clave sin pasar por el script, se avisa y no se muestra."""
        self.configurar_los_dos()
        clon = self.clones["acompanante"]
        (clon / "para-cliente" / "2026-10-03-1200-a-mano.md").write_text(
            "---\nde: acompanante\npara: cliente\ntipo: aviso\n---\n\nusá {}\n".format(CLAVE_FALSA), encoding="utf-8")
        git(clon, "add", "-A")
        git(clon, "commit", "-q", "-m", "a mano")
        git(clon, "push", "-q", "origin", "HEAD:main")
        m = self.revisar("cliente")["mensajes"][0]
        self.assertTrue(m["trae_clave"])
        self.assertNotIn(CLAVE_FALSA, m["texto"])
        self.assertNotIn(CLAVE_FALSA, self.ok("cliente", "revisar"))

    def test_textos_normales_no_frenan(self):
        self.configurar_los_dos()
        for cuerpo in ("Copiá .env.example y completalo vos", "El environment de prueba anda",
                       "Usá tu clave en el llavero, no la pegues acá", "Error: invalid token (expired)"):
            codigo, salida, _ = self.correr("cliente", "armar", "--tema", "ok", entrada=cuerpo)
            self.assertEqual(codigo, 0, "frenó de más: {!r}\n{}".format(cuerpo, salida))


class TestSinConfig(BaseBuzon):
    def test_sin_config_no_hace_nada(self):
        for args in (["estado"], ["revisar"], ["subir"], ["hecho", "x.md", "--resultado", "y"]):
            codigo, salida, _ = self.correr("cliente", *args)
            self.assertEqual(codigo, 0, args)
            self.assertIn("Buzón apagado", salida)
        codigo, salida, _ = self.correr("cliente", "armar", "--tema", "t", entrada="hola")
        self.assertEqual(codigo, 0)
        self.assertIn("Buzón apagado", salida)
        # Nada escrito: ni configuración, ni borrador, ni commits.
        self.assertFalse(self.configs["cliente"].exists())
        self.assertEqual(git(self.clones["cliente"], "status", "--porcelain"), "")

    def test_hook_sin_config_no_imprime_nada(self):
        codigo, salida, error = self.correr("cliente", "aviso")
        self.assertEqual((codigo, salida, error), (0, "", ""))

    @unittest.skipIf(ES_WINDOWS, "git falso con script de shell")
    def test_sin_config_no_llama_a_git(self):
        falsos = self.tmp / "bin"
        falsos.mkdir()
        marca = self.tmp / "git-llamado"
        (falsos / "git").write_text("#!/bin/sh\ntouch '{}'\nexit 1\n".format(marca))
        (falsos / "git").chmod(0o755)
        env = {"PATH": str(falsos) + os.pathsep + os.environ.get("PATH", "")}
        for args in (["aviso"], ["revisar"], ["estado"]):
            self.correr("cliente", *args, env_extra=env)
        self.assertFalse(marca.exists())

    def test_config_rota_avisa_sin_romper_el_hook(self):
        d = self.configs["cliente"] / "metodo"
        d.mkdir(parents=True)
        (d / "buzon.json").write_text('{"carpeta": "/no/existe", "yo": "cliente"}', encoding="utf-8")
        codigo, salida, _ = self.correr("cliente", "aviso")
        self.assertEqual(codigo, 0)
        self.assertIn("Buz", json.loads(salida)["systemMessage"])
        codigo, salida, _ = self.correr("cliente", "revisar")
        self.assertEqual(codigo, 1)
        self.assertIn("ERROR", salida)


class TestHook(BaseBuzon):
    def test_hook_cuenta_los_mensajes(self):
        self.configurar_los_dos()
        codigo, salida, _ = self.correr("cliente", "aviso")
        self.assertEqual((codigo, salida), (0, ""))  # sin mensajes, silencio
        self.mandar("acompanante", "uno", "a")
        self.mandar("acompanante", "dos", "b")
        codigo, salida, _ = self.correr("cliente", "aviso")
        self.assertEqual(codigo, 0)
        datos = json.loads(salida)
        self.assertEqual(datos["systemMessage"], "Buzón: 2 mensajes nuevos — escribí /metodo:buzon")
        self.assertEqual(datos["hookSpecificOutput"]["hookEventName"], "SessionStart")
        # El hook solo mira: no trae nada a la copia ni hace commits.
        self.assertEqual(list((self.clones["cliente"] / "para-cliente").glob("*.md")), [])

    def test_hook_sin_red_no_falla(self):
        self.configurar_los_dos()
        self.mandar("acompanante", "uno", "a")
        self.ok("cliente", "revisar")  # el mensaje ya está en la copia del cliente
        git(self.clones["cliente"], "remote", "set-url", "origin", "http://127.0.0.1:9/no-hay-red.git")
        inicio = time.monotonic()
        codigo, salida, _ = self.correr("cliente", "aviso")
        self.assertEqual(codigo, 0)
        self.assertLess(time.monotonic() - inicio, 5)
        datos = json.loads(salida)
        self.assertIn("1 mensaje nuevo", datos["systemMessage"])
        self.assertIn("sin conexión", datos["systemMessage"])

    @unittest.skipIf(ES_WINDOWS, "git falso con script de shell")
    def test_hook_corta_el_fetch_colgado_a_los_3_segundos(self):
        self.configurar_los_dos()
        real = shutil.which("git")
        falsos = self.tmp / "bin"
        falsos.mkdir()
        (falsos / "git").write_text(
            '#!/bin/sh\nfor a in "$@"; do [ "$a" = fetch ] && exec sleep 30; done\nexec "{}" "$@"\n'.format(real))
        (falsos / "git").chmod(0o755)
        env = {"PATH": str(falsos) + os.pathsep + os.environ.get("PATH", "")}
        inicio = time.monotonic()
        codigo, _, _ = self.correr("cliente", "aviso", env_extra=env, timeout=20)
        duracion = time.monotonic() - inicio
        self.assertEqual(codigo, 0)
        self.assertLess(duracion, 4.5)

    def test_hook_con_git_ausente_no_falla(self):
        self.configurar_los_dos()
        vacio = self.tmp / "sin-nada"
        vacio.mkdir()
        codigo, _, error = self.correr("cliente", "aviso", env_extra={"PATH": str(vacio)})
        self.assertEqual(codigo, 0)
        self.assertEqual(error, "")

    def test_hooks_json_tiene_el_buzon_sin_tocar_el_vigia(self):
        datos = json.loads(HOOKS_JSON.read_text(encoding="utf-8"))
        inicio = datos["hooks"]["SessionStart"]
        self.assertIn("vigia/aviso.py", inicio[0]["hooks"][0]["command"])
        comandos = [h["command"] for bloque in inicio for h in bloque["hooks"]]
        buzon = [c for c in comandos if "buzon.py" in c]
        self.assertEqual(len(buzon), 1)
        self.assertIn("aviso", buzon[0])
        self.assertTrue(buzon[0].rstrip().endswith("|| true"))


class TestHecho(BaseBuzon):
    def test_mover_a_hecho_valida_el_nombre(self):
        self.configurar_los_dos()
        self.mandar("acompanante", "Paso 1", "hacé esto")
        m = self.revisar("cliente")["mensajes"][0]
        for malo in ("../hecho/" + m["nombre"], "para-acompanante/" + m["nombre"], "/etc/passwd", ".gitkeep",
                     "no-existe.md"):
            codigo, salida, _ = self.correr("cliente", "hecho", malo, "--resultado", "x")
            self.assertEqual(codigo, 1, malo)
            self.assertIn("ERROR", salida)
        # Sin resultado no se mueve.
        codigo, _, _ = self.correr("cliente", "hecho", m["nombre"], "--resultado", "   ")
        self.assertEqual(codigo, 1)
        # Por nombre solo (sin carpeta) también funciona.
        self.ok("cliente", "hecho", m["nombre"], "--resultado", "no se hizo: el cliente dijo que no")
        self.assertTrue((self.clones["cliente"] / "hecho" / m["nombre"]).is_file())
        # Dos veces, no.
        codigo, _, _ = self.correr("cliente", "hecho", m["nombre"], "--resultado", "otra vez")
        self.assertEqual(codigo, 1)

    def test_solo_se_agregan_los_archivos_del_buzon(self):
        """Un archivo suelto en la copia (por ejemplo, un borrador personal) nunca entra al commit."""
        self.configurar_los_dos()
        (self.clones["cliente"] / "notas-privadas.txt").write_text("privado", encoding="utf-8")
        self.mandar("cliente", "consulta", "¿cómo sigo?")
        archivos = git(self.bare, "ls-tree", "-r", "--name-only", "main")
        self.assertNotIn("notas-privadas.txt", archivos)


if __name__ == "__main__":
    unittest.main()
