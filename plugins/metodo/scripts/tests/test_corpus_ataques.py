#!/usr/bin/env python3
"""Corpus de regresión de los frenos que corren en las máquinas de los clientes (C72).

Junta en un solo lugar, agrupados por freno y con el nombre del hallazgo que cubren, los casos de las revisiones de
seguridad de metodo 0.35.0 → 0.35.2 (docs/SECURITY-CHECKS.md, .claude/security-checks/2026-10-12.md y los commits de
arreglo cb6268c, 4e8c799, 9899ed9, cc1ee2c, 793950f, e666172, 9db2361, cd12c74, 0616e91), más el uso normal que tiene
que seguir pasando (para ver falsos positivos que le rompan el trabajo al cliente).

Regla: un hallazgo nuevo se suma acá como UN caso más, con su nombre. No se inventan variantes: cada caso sale de un
hallazgo documentado. Si un caso todavía no está arreglado en main, va con `conocido="…"`: se marca
`unittest.expectedFailure` (en unittest y en pytest, si un día pasa, la suite sale en rojo y avisa que hay que sacar
la marca). Se usa unittest y no pytest porque el CI corre `python -m unittest discover` en Mac, Linux y Windows.

Sin red, sin herramientas reales de otras IA, todo en carpetas temporales con datos falsos.
Correr: python3 -m unittest discover -s plugins/metodo/scripts/tests -p "test_corpus_ataques.py" -v
"""
import contextlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path

AQUI = Path(__file__).resolve().parent
SCRIPTS = AQUI.parent
RAIZ = SCRIPTS.parent.parent.parent
ES_WINDOWS = os.name == "nt"


def _cargar(nombre, ruta):
    spec = importlib.util.spec_from_file_location(nombre, str(ruta))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


BS = _cargar("corpus_bloquear_secretos", SCRIPTS / "bloquear-secretos.py")
EA = _cargar("corpus_estable_avanzar", RAIZ / "scripts" / "estable-avanzar.py")
DG = _cargar("corpus_delegar", SCRIPTS / "delegar.py")
TRANCA = SCRIPTS / "skills-externas" / "skills-cli-tranca.py"


def _agregar_casos(clase, prefijo, casos, probar):
    """Un método de test por caso: test_<prefijo>_<hallazgo>_<n>. `casos` = [(hallazgo, entrada, esperado, conocido)]."""
    usados = {}
    for hallazgo, entrada, esperado, conocido in casos:
        clave = hallazgo.lower().replace("-", "_").replace(" ", "_")
        usados[clave] = usados.get(clave, 0) + 1
        nombre = "test_%s_%s_%02d" % (prefijo, clave, usados[clave])

        def metodo(self, entrada=entrada, esperado=esperado, hallazgo=hallazgo):
            probar(self, entrada, esperado, hallazgo)

        metodo.__doc__ = "%s · %r → %s%s" % (hallazgo, entrada, esperado, (" · conocido: " + conocido) if conocido else "")
        if conocido:
            metodo = unittest.expectedFailure(metodo)
        setattr(clase, nombre, metodo)


FRENA, PASA = "frena", "pasa"

# =================================================================================================================== #
# 1) bloquear-secretos.py (hook PreToolUse: exit 2 + JSON «deny» = frena; exit 0 sin salida = pasa)
# =================================================================================================================== #
SECRETOS_BASH = [
    # F5 (check 0.35.0, 2026-10-12): vías que esquivaban el freno, arregladas en 793950f
    ("F5", "env | grep AWS", FRENA, None),
    ("F5", "printenv | grep -i tok", FRENA, None),
    ("F5", "cut -f1 .env", FRENA, None),
    ("F5", "awk '{print $1}' .env", FRENA, None),
    ("F5", "cut -d= -f1 llave.pem", FRENA, None),
    ("F5", "cat<.env", FRENA, None),
    ("F5", "cat .env>/dev/stderr", FRENA, None),
    ("F5", "git cat-file -p HEAD:.env", FRENA, None),
    ("F5", "git cat-file blob HEAD:config/.env.production", FRENA, None),
    ("F5", "tee /dev/null < .env", FRENA, None),
    ("F5", "cp .env /dev/stdout", FRENA, None),
    ("F5", "git diff -- .env", FRENA, None),
    ("F5", "git log -p -- .env", FRENA, None),
    ("F5", "git blame .env", FRENA, None),
    # M-1 (2.ª revisión): patrón sin ancla o sin «=», y todos los -e; arreglado en cb6268c
    ("M-1", "env | grep HOME", FRENA, None),
    ("M-1", "env | grep PATH", FRENA, None),
    ("M-1", "env | grep -e PATH -e TOKEN", FRENA, None),
    ("M-1", "env | grep -e ^PATH= -e TOKEN", FRENA, None),
    ("M-1", "env | grep -e^PATH= -eAWS", FRENA, None),
    ("M-1", "env | grep --regexp=^HOME= --regexp=AWS", FRENA, None),
    ("M-1", "env | grep ^LANGCHAIN_API_KEY=", FRENA, None),
    ("M-1", "env | grep ^DB_USER_PASSWORD=", FRENA, None),
    ("M-1", "env | grep ^HOMEBREW_GITHUB_API_TOKEN=", FRENA, None),
    ("M-1", "env | grep -f lista.txt", FRENA, None),
    ("M-1", "env | grep --file=lista.txt", FRENA, None),
    ("M-1", "env | grep -if lista.txt", FRENA, None),
    ("M-1", "printenv | grep -i ^home=x", FRENA, None),
    # Uso normal que tiene que seguir pasando (los de los arreglos F5 / M-1 y los del brief de C72)
    ("uso-normal", "env | grep -e ^PATH= -e ^HOME=", PASA, None),
    ("uso-normal", "env | grep -m1 ^HOME=", PASA, None),
    ("uso-normal", "env | grep -A 2 ^SHELL=", PASA, None),
    ("uso-normal", "env | grep --regexp=^LANG=", PASA, None),
    ("uso-normal", "env | grep ^NODE_OPTIONS=", PASA, None),
    ("uso-normal", "env | grep ^HOME=", PASA, None),
    ("uso-normal", "env | grep -c AWS", PASA, None),
    ("uso-normal", "env | grep -c ^PATH=", PASA, None),
    ("uso-normal", "cut -d= -f1 .env.local", PASA, None),
    ("uso-normal", "cut -d '=' -f 1 .env", PASA, None),
    ("uso-normal", "awk -F '=' '{print $1}' .env", PASA, None),
    ("uso-normal", "grep -c '^API_TOKEN=' .env", PASA, None),
    ("uso-normal", "git diff --stat -- .env", PASA, None),
    ("uso-normal", "git log --oneline -- .env", PASA, None),
    ("uso-normal", "cp .env .env.bak", PASA, None),
    ("uso-normal", "cat .env>copia.txt", PASA, None),
    ("uso-normal", "echo a>b.txt", PASA, None),
    ("uso-normal", "ls 2>&1", PASA, None),
    ("uso-normal", "git diff HEAD~1", PASA, None),
    ("uso-normal", "ls -la", PASA, None),
    ("uso-normal", "git status", PASA, None),
    ("uso-normal", "cat README.md", PASA, None),
    ("uso-normal", 'echo "hola"', PASA, None),
]

SECRETOS_POWERSHELL = [
    # F4 (check 0.35.0): la herramienta PowerShell de Windows no pasaba por ningún freno
    ("F4", "Get-Content .env", FRENA, None),
    ("F4", "gc .\\.env.local", FRENA, None),
    ("F4", "type .env", FRENA, None),
    ("F4", "Get-ChildItem Env:", FRENA, None),
    ("F4", "gci env:", FRENA, None),
    ("F4", "Get-ChildItem Env:API_TOKEN", FRENA, None),
    ("F4", "echo $env:API_TOKEN", FRENA, None),
    ("F4", "[Environment]::GetEnvironmentVariables()", FRENA, None),
    ("F4", 'powershell -Command "Get-Content .env"', FRENA, None),
    ("F4", "cmd /c type .env", FRENA, None),
    # L-3 (2.ª revisión): una cadena "$env:X" sola también se imprime; arreglado en 4e8c799
    ("L-3", '"$env:GITHUB_TOKEN"', FRENA, None),
    ("L-3", '"token: ${env:GITHUB_TOKEN}"', FRENA, None),
    ("L-3", 'ls; "$env:API_TOKEN"', FRENA, None),
    # Uso normal
    ("uso-normal", "'$env:GITHUB_TOKEN'", PASA, None),           # comillas simples no expanden
    ("uso-normal", '"$env:HOME"', PASA, None),
    ("uso-normal", '"largo=$($env:API_TOKEN.Length)"', PASA, None),
    ("uso-normal", "Get-Content README.md", PASA, None),
    ("uso-normal", "Get-Content .env.example", PASA, None),
    ("uso-normal", "Test-Path .env", PASA, None),
    ("uso-normal", "Get-Content .env | Measure-Object -Line", PASA, None),
    ("uso-normal", "Get-ChildItem Env: | Select-Object -ExpandProperty Name", PASA, None),
    ("uso-normal", "git status", PASA, None),
]


def _hook_secretos(herramienta, tool_input, cwd="/proyecto"):
    """Corre main() del freno con la misma entrada que le da Claude Code. → (código, salida estándar)."""
    entrada = json.dumps({"tool_name": herramienta, "tool_input": tool_input, "cwd": cwd})
    salida, errores, previo = io.StringIO(), io.StringIO(), sys.stdin
    try:
        sys.stdin = io.StringIO(entrada)
        with contextlib.redirect_stdout(salida), contextlib.redirect_stderr(errores):
            codigo = BS.main()
    finally:
        sys.stdin = previo
    return codigo, salida.getvalue()


def _probar_secretos(herramienta):
    def probar(self, comando, esperado, hallazgo):
        codigo, salida = _hook_secretos(herramienta, {"command": comando})
        if esperado == FRENA:
            self.assertEqual(codigo, 2, "%s: tendría que frenar: %r" % (hallazgo, comando))
            self.assertEqual(json.loads(salida)["hookSpecificOutput"]["permissionDecision"], "deny")
        else:
            self.assertEqual((codigo, salida), (0, ""), "%s: tendría que pasar: %r" % (hallazgo, comando))
    return probar


class CorpusSecretosBash(unittest.TestCase):
    """bloquear-secretos.py con la herramienta Bash."""


class CorpusSecretosPowerShell(unittest.TestCase):
    """bloquear-secretos.py con la herramienta PowerShell (Windows)."""


_agregar_casos(CorpusSecretosBash, "secretos_bash", SECRETOS_BASH, _probar_secretos("Bash"))
_agregar_casos(CorpusSecretosPowerShell, "secretos_ps", SECRETOS_POWERSHELL, _probar_secretos("PowerShell"))

# =================================================================================================================== #
# 2) skills-cli-tranca.py (hook PreToolUse de Bash: exit 2 = frena, exit 0 = pasa)
# =================================================================================================================== #
TRANCA_CASOS = [
    # F7 (check 0.35.0): el texto «cuarentena-skills» en cualquier parte eximía al instalador; arreglado en e666172
    ("F7", "npx skills add x -g # cuarentena-skills", FRENA, None),
    ("F7", "echo cuarentena-skills; npx skills add x", FRENA, None),
    ("F7", "npx skills add cuarentena-skills", FRENA, None),
    ("F7", "cuarentena-skills.sh x && npx skills add y", FRENA, None),
    # L-2 (2.ª revisión): la cuarentena con otro comando adentro no exime; arreglado en 9899ed9
    ("L-2", 'cuarentena-skills.sh "$(npx skills add x -g)"', FRENA, None),
    ("L-2", "bash cuarentena-skills.sh `npx skills add x`", FRENA, None),
    ("L-2", "cuarentena-skills.sh <(npx skills add x)", FRENA, None),
    ("L-2", "cuarentena-skills.sh a/b >(npx skills update)", FRENA, None),
    # Uso normal (buscar, listar y la cuarentena misma)
    ("uso-normal", "npx skills find n8n", PASA, None),
    ("uso-normal", "npx skills list", PASA, None),
    ("uso-normal", "npx skills --version", PASA, None),
    ("uso-normal", "ls ~/.claude/skills", PASA, None),
    ("uso-normal", "git commit -m 'arreglo'", PASA, None),
    ("uso-normal", "cuarentena-skills unclecatvn/agent-skills odoo-17", PASA, None),
    ("uso-normal", "python3 skills-buscar.py odoo", PASA, None),
    ("uso-normal", "bash /x/y/cuarentena-skills.sh owner/repo@skill", PASA, None),
    ("uso-normal", "SKILLS_X=1 bash cuarentena-skills.sh a/b mi-skill --dry-run", PASA, None),
]


def _probar_tranca(self, comando, esperado, hallazgo):
    r = subprocess.run([sys.executable, str(TRANCA)], input=json.dumps({"tool_input": {"command": comando}}),
                       capture_output=True, text=True, timeout=30)
    self.assertEqual(r.returncode, 2 if esperado == FRENA else 0, "%s: %r" % (hallazgo, comando))


class CorpusTranca(unittest.TestCase):
    """skills-cli-tranca.py: el freno del instalador de skills."""


_agregar_casos(CorpusTranca, "tranca", TRANCA_CASOS, _probar_tranca)

# =================================================================================================================== #
# 3) estable-avanzar.py: la compuerta de security check (funciones puras, sobre un repo git temporal)
# =================================================================================================================== #
# Títulos de docs/SECURITY-CHECKS.md. {v} = sha corto del commit que trae metodo 0.36.0; {v12} = 12 letras;
# {viejo} = commit que trae 0.35.0 (ancestro, otra versión); {w} = commit posterior que no es ancestro del candidato.
T = "### 2026-10-20 · %s (commit {v}) — %s"
CUBRE, NO_CUBRE = "cubre", "no cubre"
TITULOS = [
    # M2 (1.ª revisión, 9db2361): versión exacta o rango, un solo commit, ancestro, PASS
    ("M2", T % ("metodo 3.50.0", "PASS"), NO_CUBRE, None),
    ("M2", T % ("metodo 0.35.9", "PASS"), NO_CUBRE, None),
    ("M2", T % ("metodo 0.36.0", "FAIL"), NO_CUBRE, None),
    ("M2", T % ("metodo 0.36.0", "PASS a medias, FAIL en Windows"), NO_CUBRE, None),
    ("M2", T % ("metodo 0.36.0", "NO PASS"), NO_CUBRE, None),
    ("M2", T % ("metodo 0.36.0", "pendiente"), NO_CUBRE, None),
    ("M2", "### 2026-10-20 · metodo 0.36.0 — PASS", NO_CUBRE, None),
    ("M2", "### metodo 0.36.0 (commit {v}, commit {viejo}) — PASS", NO_CUBRE, None),
    ("M2", "### 2026-10-20 · metodo 0.36.0 (commit deadbeefdeadbeef) — PASS", NO_CUBRE, None),
    ("M2", "### 2026-10-20 · metodo 0.36.0 (commit {w}) — PASS", NO_CUBRE, None),
    ("M2", "```markdown\n" + T % ("metodo 0.36.0", "PASS") + "\n```", NO_CUBRE, None),
    ("M2", "~~~\n" + T % ("metodo 0.36.0", "PASS") + "\n~~~", NO_CUBRE, None),
    ("M2", T % ("metodo 0.35.1", "PASS") + "\n\nCondiciones para metodo 0.36.0 (commit {v}): ninguna — PASS", NO_CUBRE, None),
    # L6 (1.ª revisión, 9db2361): otro nombre que termina en «metodo» o versión con sufijo
    ("L6", T % ("escala-metodo 0.36.0", "PASS"), NO_CUBRE, None),
    ("L6", T % ("supermetodo 0.36.0", "PASS"), NO_CUBRE, None),
    ("L6", T % ("metodo 0.36.0-rc.1", "PASS"), NO_CUBRE, None),
    ("L6", T % ("metodo 0.36.0.1", "PASS"), NO_CUBRE, None),
    # M-2a (2.ª revisión, cc1ee2c): el commit revisado tiene que TRAER la versión
    ("M-2a", "### 2026-10-20 · metodo 0.36.0 (commit {viejo}) — PASS", NO_CUBRE, None),
    # M-2b (2.ª revisión): un rango no cubre versiones que el commit revisado no trae
    ("M-2b", T % ("metodo 0.35.0 → 0.40.0", "PASS"), NO_CUBRE, None),
    # M-2c (2.ª revisión): el veredicto va al final y el título no nombra FLAG / crítico / FAIL
    ("M-2c", T % ("metodo 0.36.0", "PASS — revisar mañana"), NO_CUBRE, None),
    ("M-2c", T % ("metodo 0.36.0", "17 PASS · 15 FLAG — PASS"), NO_CUBRE, None),
    ("M-2c", T % ("metodo 0.36.0", "PASS salvo un crítico — PASS"), NO_CUBRE, None),
    ("M-2c", T % ("metodo 0.36.0", "FAILED — PASS"), NO_CUBRE, None),
    ("M-2c", T % ("metodo 0.36.0", "PASS con condiciones (un critico abierto)"), NO_CUBRE, None),
    ("M-2c", T % ("metodo 0.36.0", "PASS?"), NO_CUBRE, None),
    # M-2d (2.ª revisión): un título dentro de un comentario HTML no cuenta
    ("M-2d", "<!--\n" + T % ("metodo 0.36.0", "PASS") + "\n-->", NO_CUBRE, None),
    ("M-2d", "<!-- " + T % ("metodo 0.36.0", "PASS") + " -->", NO_CUBRE, None),
    ("M-2d", "texto <!-- empieza\notra línea\n" + T % ("metodo 0.36.0", "PASS") + "\nsigue -->", NO_CUBRE, None),
    # Uso normal: los títulos bien escritos tienen que seguir cubriendo
    ("uso-normal", T % ("metodo 0.36.0", "PASS"), CUBRE, None),
    ("uso-normal", T % ("metodo 0.36.0", "PASS con condiciones   "), CUBRE, None),
    ("uso-normal", T % ("metodo 0.35.1 → 0.36.0", "PASS"), CUBRE, None),
    ("uso-normal", "## `metodo v0.35.1 -> v0.36.0` (commit `{v12}`) — PASS con condiciones", CUBRE, None),
    ("uso-normal", "<!-- nota\nvieja -->\n" + T % ("metodo 0.36.0", "PASS"), CUBRE, None),
]

# M1 / L7 (1.ª revisión, cd12c74): lo que se promueve falla cerrado si la versión no se puede leer o el catálogo no cuadra.
# (hallazgo, {ruta: contenido} que se agrega en el commit candidato, esperado)
PLUGIN = "plugins/metodo/.claude-plugin/plugin.json"
CATALOGO = ".claude-plugin/marketplace.json"


def _plugin(version):
    return json.dumps({"name": "metodo", "version": version})


def _catalogo(**entrada):
    return json.dumps({"name": "c", "plugins": [dict({"name": "metodo"}, **entrada)]})


VERSIONES = [
    ("M1", {PLUGIN: _plugin("0.36.0-rc.1")}, FRENA, None),
    ("M1", {PLUGIN: _plugin("0.36.0+fix")}, FRENA, None),
    ("M1", {PLUGIN: _plugin("v0.36.0")}, FRENA, None),
    ("M1", {PLUGIN: _plugin("0.36")}, FRENA, None),
    ("M1", {PLUGIN: "{roto"}, FRENA, None),
    ("M1", {PLUGIN: json.dumps({"name": "metodo"})}, FRENA, None),
    ("L7", {PLUGIN: _plugin("0.36.0"), CATALOGO: _catalogo(version="0.36.0", source={"source": "github", "repo": "otro/repo"})},
     FRENA, None),
    ("L7", {PLUGIN: _plugin("0.36.0"), CATALOGO: _catalogo(version="0.35.0", source="./plugins/metodo")}, FRENA, None),
    ("uso-normal", {PLUGIN: _plugin("0.36.0")}, PASA, None),
    ("uso-normal", {PLUGIN: _plugin("0.36.0"), CATALOGO: _catalogo(version="0.36.0", source="./plugins/metodo")}, PASA, None),
]

# Motivo de --sin-check: F14 (0616e91) no arma comandos de GitHub Actions; Info8 (9db2361) sin backticks; mínimo 10 letras.
MOTIVOS = [
    ("F14", "urgente de verdad\n::error::inventado", "sin-comandos", None),
    ("Info8", "urgente `rm -rf` de mentira", "sin-comandos", None),
    ("F14", "x", "rechazado", None),
    ("uso-normal", "arreglo urgente de un cliente", "igual", None),
]


def _git(cwd, *args):
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", GIT_CONFIG_NOSYSTEM="1")
    r = subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", "-c", "commit.gpgsign=false",
                        "-c", "core.hooksPath=" + os.devnull] + list(args),
                       cwd=str(cwd), env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    if r.returncode != 0:
        raise AssertionError("git %s: %s" % (" ".join(args), r.stderr))
    return r.stdout.strip()


def _commit(repo, archivos, mensaje):
    for ruta, contenido in archivos.items():
        destino = Path(repo) / ruta
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(contenido, encoding="utf-8")
        _git(repo, "add", ruta)
    _git(repo, "commit", "--quiet", "--allow-empty", "-m", mensaje)
    return _git(repo, "rev-parse", "HEAD")


class _RepoCompuerta(unittest.TestCase):
    """Repo temporal: `estable` trae metodo 0.35.0 y paneles 0.2.1; el candidato trae metodo 0.36.0."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.repo = Path(cls._tmp.name)
        _git(cls.repo, "init", "--quiet", "-b", "main")
        cls.viejo = _commit(cls.repo, {PLUGIN: _plugin("0.35.0"),
                                       "plugins/paneles/.claude-plugin/plugin.json": json.dumps({"name": "paneles", "version": "0.2.1"})},
                            "estable: metodo 0.35.0")
        cls.v = _commit(cls.repo, {PLUGIN: _plugin("0.36.0")}, "candidato: metodo 0.36.0")
        cls.w = _commit(cls.repo, {"docs/despues.md": "x"}, "posterior al candidato")

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()


def _probar_titulo(self, titulo, esperado, hallazgo):
    texto = titulo.format(v=self.v[:7], v12=self.v[:12], viejo=self.viejo[:7], w=self.w[:7])
    principal = _commit(self.repo, {"docs/SECURITY-CHECKS.md": "# Security checks\n\n" + texto + "\n"}, "check: " + hallazgo)
    faltan, _validados, _avisos = EA.sin_security_check(str(self.repo), self.viejo, self.v, principal)
    cubre = not faltan
    self.assertEqual(cubre, esperado == CUBRE, "%s: %r tendría que %s a metodo 0.36.0" % (hallazgo, texto, esperado))


def _probar_version(self, archivos, esperado, hallazgo):
    _git(self.repo, "checkout", "--quiet", "--detach", self.v)
    sha = _commit(self.repo, archivos, "candidato " + hallazgo)
    if esperado == FRENA:
        with self.assertRaises(EA.Frena, msg="%s: %r tendría que frenar" % (hallazgo, archivos)):
            EA.version_que_llega(str(self.repo), sha, "metodo")
    else:
        self.assertEqual(EA.version_que_llega(str(self.repo), sha, "metodo"), "0.36.0")


def _probar_motivo(self, motivo, esperado, hallazgo):
    limpio = EA.limpiar_motivo(motivo)
    if esperado == "rechazado":
        self.assertIsNone(limpio, hallazgo)
    elif esperado == "igual":
        self.assertEqual(limpio, motivo, hallazgo)
    else:
        self.assertIsNotNone(limpio, hallazgo)
        self.assertNotIn("::", limpio, hallazgo)
        self.assertNotIn("\n", limpio, hallazgo)
        self.assertNotIn("`", limpio, hallazgo)


class CorpusCompuertaTitulos(_RepoCompuerta):
    """estable-avanzar.py: qué título de security check cubre la versión que se promueve."""


class CorpusCompuertaVersiones(_RepoCompuerta):
    """estable-avanzar.py: la versión que llega a los clientes se lee o se frena (falla cerrado)."""


class CorpusCompuertaMotivo(unittest.TestCase):
    """estable-avanzar.py: el motivo de --sin-check no arma comandos de GitHub Actions."""


_agregar_casos(CorpusCompuertaTitulos, "compuerta_titulo", TITULOS, _probar_titulo)
_agregar_casos(CorpusCompuertaVersiones, "compuerta_version", VERSIONES, _probar_version)
_agregar_casos(CorpusCompuertaMotivo, "compuerta_motivo", MOTIVOS, _probar_motivo)

# =================================================================================================================== #
# 4) delegar.py: filtro del archivo del pedido (nombres de archivos de claves) y es_carpeta_privada (carpetas de llaves)
# =================================================================================================================== #
# metodo 0.35.2 en main. Otra sesión los endurece en la rama de 0.36.0: lo que hoy falla va con `conocido`; al unir esa
# rama, cada caso que empiece a pasar pone la suite en rojo hasta sacarle la marca.
PEND = "pendiente en main (0.35.2); lo arregla la rama de metodo 0.36.0"
PEDIDOS = [
    ("nombres-de-claves", "prod.env", FRENA, PEND),
    ("nombres-de-claves", ".env-prod", FRENA, None),
    ("nombres-de-claves", ".env_local", FRENA, None),
    ("nombres-de-claves", "client_secret_123.json", FRENA, None),
    ("nombres-de-claves", "AuthKey_ABC.p8", FRENA, PEND),
    ("nombres-de-claves", "servidor.ppk", FRENA, PEND),
    ("nombres-de-claves", "oficina.ovpn", FRENA, PEND),
    ("nombres-de-claves", "prod.tfvars", FRENA, PEND),
    ("nombres-de-claves", "terraform.tfstate", FRENA, PEND),
    ("nombres-de-claves", ".yarnrc.yml", FRENA, PEND),
    ("nombres-de-claves", "auth.json", FRENA, PEND),
    ("nombres-de-claves", ".htpasswd", FRENA, PEND),
    ("nombres-de-claves", ".vault-token", FRENA, None),
    ("nombres-de-claves", ".my.cnf", FRENA, PEND),
    ("nombres-de-claves", "pip.conf", FRENA, PEND),
    ("nombres-de-claves", ".zsh_history", FRENA, None),
    ("nombres-de-claves", "history.jsonl", FRENA, None),
    ("nombres-de-claves", ".ENV", FRENA, None),
    ("nombres-de-claves", "ID_RSA", FRENA, None),
    ("carpetas-de-llaves", "secrets/x.json", FRENA, PEND),
    ("carpetas-de-llaves", "credentials/pedido.txt", FRENA, PEND),
    ("carpetas-de-llaves", "keys/pedido.txt", FRENA, PEND),
    ("carpetas-de-llaves", "private/pedido.txt", FRENA, PEND),
    ("uso-normal", "pedido.txt", PASA, None),
    ("uso-normal", "docs/pedido.md", PASA, None),
]


def _probar_pedido(self, nombre, esperado, hallazgo):
    with tempfile.TemporaryDirectory() as d:
        repo = Path(d).resolve()
        archivo = repo / nombre
        archivo.parent.mkdir(parents=True, exist_ok=True)
        archivo.write_text("pedido de prueba, sin datos\n", encoding="utf-8")
        texto, error = DG.leer_pedido(types.SimpleNamespace(archivo=True, pedido=str(archivo)), repo)
    if esperado == FRENA:
        self.assertIsNone(texto, "%s: «%s» se mandaría" % (hallazgo, nombre))
        self.assertIn("archivo de claves", error or "")
    else:
        self.assertIsNone(error, "%s: «%s» tendría que poder mandarse" % (hallazgo, nombre))


class CorpusDelegarPedido(unittest.TestCase):
    """delegar.py --archivo: el archivo del pedido no puede ser un archivo de claves."""

    @unittest.skipIf(ES_WINDOWS, "enlaces simbólicos")
    def test_delegar_pedido_enlace_a_claves_01(self):
        """nombres-de-claves · un enlace con nombre inocente que apunta a un archivo de claves → frena."""
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d).resolve()
            (repo / "credentials.json").write_text("{}", encoding="utf-8")
            (repo / "pedido.txt").symlink_to(repo / "credentials.json")
            texto, error = DG.leer_pedido(types.SimpleNamespace(archivo=True, pedido=str(repo / "pedido.txt")), repo)
        self.assertIsNone(texto)
        self.assertIn("archivo de claves", error or "")


_agregar_casos(CorpusDelegarPedido, "delegar_pedido", PEDIDOS, _probar_pedido)

HOME = str(Path.home())
CARPETAS = [
    ("carpetas-de-llaves", os.path.join(HOME, ".ssh"), "privada", None),
    ("carpetas-de-llaves", os.path.join(HOME, ".aws"), "privada", None),
    ("carpetas-de-llaves", os.path.join(HOME, ".config", "gh"), "privada", None),
    ("carpetas-de-llaves", os.path.join(HOME, ".claude"), "privada", None),
    ("home-entero", HOME, "privada", None),
    ("home-entero", HOME + os.sep, "privada", None),
    ("uso-normal", os.path.join(HOME, "Proyectos", "un-proyecto"), "se puede", None),
]
if not ES_WINDOWS:
    CARPETAS += [
        ("home-entero", "/", "privada", None),
        ("home-entero", HOME.upper(), "privada", None),                       # Mac: mismas carpetas sin importar mayúsculas
        ("firmlink", "/System/Volumes/Data" + HOME, "privada", None),        # Mac: la misma carpeta personal por otra ruta
    ]


def _probar_carpeta(self, ruta, esperado, hallazgo):
    privada, _motivo = DG.es_carpeta_privada(Path(ruta))
    self.assertEqual(privada, esperado == "privada", "%s: %s tendría que ser %s" % (hallazgo, ruta, esperado))


class CorpusDelegarCarpeta(unittest.TestCase):
    """delegar.py: es_carpeta_privada no deja delegar la carpeta personal ni las carpetas de llaves."""

    def setUp(self):
        self._previo = os.environ.pop("METODO_NO_DELEGAR", None)

    def tearDown(self):
        if self._previo is not None:
            os.environ["METODO_NO_DELEGAR"] = self._previo


_agregar_casos(CorpusDelegarCarpeta, "delegar_carpeta", CARPETAS, _probar_carpeta)


if __name__ == "__main__":
    unittest.main()
