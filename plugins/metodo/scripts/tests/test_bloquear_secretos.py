"""Tests del freno anti-secretos (bloquear-secretos.py). Solo biblioteca estándar, sin red, sin secretos reales:
todos los valores son marcadores inventados.

Correr desde la raíz del repo:
    python3 -m unittest discover -s plugins/metodo/scripts/tests -v
"""
import importlib.util
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

AQUI = Path(__file__).resolve().parent
SCRIPT = AQUI.parent / "bloquear-secretos.py"
WRAPPER = AQUI.parent / "bloquear-secretos.sh"
_spec = importlib.util.spec_from_file_location("bloquear_secretos", SCRIPT)
bs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bs)

# Comandos normales que NO se pueden frenar (incluye los dos falsos positivos de 2026-10-10).
DEBEN_PASAR = [
    "ls -la",
    "git status && git log --oneline | head -5",
    "git commit -m 'arreglo: ahora se lee el archivo .env y se avisa si falta'",
    "echo 'acordate de copiar .env.example a .env antes de arrancar'",
    "node -e \"console.log(process.env.NODE_ENV)\"",
    "node build.js --mode production  # usa process.env.NODE_ENV y process.env.API_TOKEN adentro",
    "python3 -c \"import os; x = os.environ.get('API_KEY'); print('definida' if x else 'falta')\"",
    "cat README.md",
    "cat .env.example",
    "ls -la .env",
    "test -f .env && echo existe",
    "wc -l .env",
    "cp .env .env.copia",
    "git check-ignore .env",
    "grep -c '^API_KEY=' .env",
    "grep -q '^API_KEY=' .env && echo si",
    "grep -l TOKEN .env",
    "sort .env | wc -l",
    "cat .env | sha256sum",
    "cat .env > /tmp/copia.txt",
    "echo \"largo=${#API_TOKEN} fin=${API_TOKEN: -4}\"",
    "echo $HOME",
    "echo $NODE_ENV",
    "env FOO=1 python3 script.py",
    "env | wc -l",
    "printenv HOME",
    "printenv PATH",
    "docker compose config --services",
    "docker compose up -d",
    "docker exec web ls /app",
    "gh pr list",
    "gh auth status",
    "gh auth login --with-token < token.txt",
    "export PATH=$PATH:/x",
    "cat <<'EOF' > nota.md\nNo hagas cat .env ni echo $API_TOKEN ni printenv\nEOF",
    "# cat .env\nls",
    "python3 -c \"print(open('README.md').read())\"",
    "sed -n '1,5p' config.yaml",
    "jq . package.json",
    "head -5 server.key.md",
    "curl -s -o /dev/null -w '%{http_code}' -H \"Authorization: Bearer $API_TOKEN\" https://example.com",
    "node server.js",
    "tail -f logs/app.log",
]

# Comandos que de verdad muestran un secreto: SÍ se frenan.
DEBEN_FRENARSE = [
    "cat .env",
    "cat ./proyecto/.env",
    "cat .env.local",
    "cat .env.production",
    "head -3 .env",
    "tail .env",
    "sed -n '1,5p' .env",
    "awk -F= '{print $2}' .env",
    "jq . credentials.json",
    "cut -d= -f2 .env",
    "sort .env",
    "less .env",
    "cat < .env",
    "cat ~/.ssh/id_rsa",
    "cat llave.pem",
    "cat .npmrc",
    "cat ~/.netrc",
    "cat secrets.yaml",
    "cat ~/.config/gh/hosts.yml",
    "grep API_KEY .env",
    "grep -n TOKEN .env.local",
    "rg SECRET .env",
    "python3 -c \"print(open('.env').read())\"",
    "node -e \"console.log(require('fs').readFileSync('.env','utf8'))\"",
    "ruby -e 'puts File.read(\".env\")'",
    "node -e \"console.log(process.env.API_TOKEN)\"",
    "python3 -c \"import os; print(os.environ['SECRET_KEY'])\"",
    "echo $API_TOKEN",
    "echo \"clave: ${STRIPE_SECRET_KEY}\"",
    "printf '%s' \"$CLIENT_SECRET\"",
    "printenv API_KEY",
    "printenv",
    "env",
    "env | sort",
    "export -p",
    "docker compose config",
    "docker-compose config",
    "docker exec web env",
    "git credential fill",
    "gh auth token",
    "bash -c 'cat .env'",
    "echo $(cat .env)",
    "echo `cat .env`",
    "cd proyecto && cat .env",
    "ls; cat .env",
    "cat .env | head",
    "FOO=1 cat .env",
    "sudo cat .env",
    "cat .env 2>&1",
    "cat .env*",
    "cat config/prod.env",
]


class BateriaTest(unittest.TestCase):
    def test_comandos_normales_pasan(self):
        for c in DEBEN_PASAR:
            with self.subTest(comando=c):
                self.assertEqual(bs.analizar(c), [], f"falso positivo: {c!r}")

    def test_comandos_peligrosos_se_frenan(self):
        for c in DEBEN_FRENARSE:
            with self.subTest(comando=c):
                self.assertTrue(bs.analizar(c), f"no frenó: {c!r}")


class ContratoTest(unittest.TestCase):
    def correr(self, payload, via=SCRIPT):
        cmd = [sys.executable, str(via)] if via == SCRIPT else ["bash", str(via)]
        return subprocess.run(cmd, input=payload if isinstance(payload, str) else json.dumps(payload),
                              capture_output=True, text=True, timeout=20)

    def test_frena_con_codigo_2_json_y_mensaje_claro(self):
        r = self.correr({"tool_name": "Bash", "tool_input": {"command": "cat .env"}})
        self.assertEqual(r.returncode, 2)
        j = json.loads(r.stdout)
        self.assertEqual(j["hookSpecificOutput"]["permissionDecision"], "deny")
        self.assertIn("contraseña", r.stderr)
        self.assertIn("grep -c", r.stderr)
        self.assertNotIn("Mandamiento", r.stderr)

    def test_deja_pasar_con_codigo_0_y_sin_salida(self):
        r = self.correr({"tool_name": "Bash", "tool_input": {"command": "ls -la"}})
        self.assertEqual((r.returncode, r.stdout, r.stderr), (0, "", ""))

    def test_otra_herramienta_no_se_mira(self):
        r = self.correr({"tool_name": "Read", "tool_input": {"command": "cat .env"}})
        self.assertEqual(r.returncode, 0)

    def test_entrada_rota_no_rompe(self):
        for basura in ("", "no es json", "{}", json.dumps({"tool_name": "Bash"}),
                       json.dumps({"tool_name": "Bash", "tool_input": None})):
            with self.subTest(entrada=basura):
                self.assertEqual(self.correr(basura).returncode, 0)

    def test_comando_raro_no_rompe(self):
        for c in ("'sin cerrar", "cat \"", "((", "$(", "`", "a" * 5000, "\x00\x01"):
            with self.subTest(comando=c[:20]):
                r = self.correr({"tool_name": "Bash", "tool_input": {"command": c}})
                self.assertIn(r.returncode, (0, 2))

    def test_envoltura_sh_mismo_resultado(self):
        r = self.correr({"tool_name": "Bash", "tool_input": {"command": "cat .env"}}, via=WRAPPER)
        self.assertEqual(r.returncode, 2)
        r = self.correr({"tool_name": "Bash", "tool_input": {"command": "ls"}}, via=WRAPPER)
        self.assertEqual(r.returncode, 0)

    def test_sin_python_avisa_y_deja_pasar(self):
        # PATH vacío: el envoltorio no encuentra python3 en el PATH; en /usr/bin sí puede haber uno (macOS), así que
        # solo se exige que no frene y no rompa
        env = dict(os.environ, PATH="/nonexistent")
        r = subprocess.run(["/bin/bash", str(WRAPPER)], input=json.dumps({"tool_name": "Bash", "tool_input": {"command": "ls"}}),
                           capture_output=True, text=True, env=env, timeout=20)
        self.assertEqual(r.returncode, 0)

    def test_hooks_json_lo_registra_para_bash_sin_o_true(self):
        hj = json.loads((AQUI.parent.parent / "hooks" / "hooks.json").read_text(encoding="utf-8"))
        pre = [b for b in hj["hooks"]["PreToolUse"] if b.get("matcher") == "Bash"]
        self.assertEqual(len(pre), 1)
        cmd = pre[0]["hooks"][0]["command"]
        self.assertIn("bloquear-secretos.sh", cmd)
        self.assertNotIn("|| true", cmd, "un `|| true` taparía el código 2 que frena")


if __name__ == "__main__":
    unittest.main()
