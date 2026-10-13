#!/usr/bin/env python3
"""Delegador de tareas a IAs del plugin `metodo`.

Elige la mejor IA según el radar de modelos (en modo delegar, priorizando Codex y Antigravity sobre Claude Code),
con el cupo de cada una medido, y ejecuta la tarea en el repositorio indicado. Nunca corre tests ni hace commit:
eso lo hace quien delega, mirando el cambio.

Uso:
    delegar.py <categoria> <repo> <pedido> [--archivo] [--revisar] [--sensible] [--dry-run]
    delegar.py --aceptar            (una sola vez: acepta que el código del repo se envíe a Codex / Antigravity)

Argumentos:
    categoria     Categoría del radar (ej. desarrollo, revision).
    repo          Ruta al repositorio git donde trabajar.
    pedido        Texto de la tarea (hasta 100 KB). Con --archivo, la ruta de un archivo de texto con la tarea.

Opciones:
    --archivo     El pedido es la ruta de un archivo (se rechazan nombres de claves y más de 100 KB).
    --revisar     Modo solo lectura: análisis y revisión sin modificar archivos. Permite árbol de trabajo sucio.
    --sensible    Excluye planes que no admiten datos privados.
    --dry-run     Muestra el plan elegido y el comando que correría, sin ejecutarlo.
    --aceptar     Deja constancia (una vez) de que sabés que el código se envía a un tercero y que los planes
                  gratuitos pueden entrenar con lo enviado. Sin eso, delegar no ejecuta nada.

Códigos de salida:
    0   Éxito (tarea ejecutada o revisada).
    1   Sin plan disponible en el radar (cupos agotados, retiros, etc.).
    2   Categoría desconocida.
    3   El plan elegido es Claude Code (hacelo en esta sesión interactiva).
    64  Error de uso, repositorio inválido, pedido ilegible o modelo con forma rara.
    65  El repo es tu carpeta personal entera, la raíz del disco o una carpeta de llaves o de configuración de tus
        herramientas (~/.ssh, ~/.claude, ~/.gemini…), o lo marcaste con METODO_NO_DELEGAR.
    66  Árbol sucio al editar (git status no limpio sin --revisar).
    67  La CLI del plan elegido (codex o agy) no está instalada, o está dentro del repo, o Antigravity no ofrece ningún
        modelo Gemini «-high» (agy models): no se lo lanza para que no elija uno por su cuenta.
    68  Falta aceptar el envío del código a un tercero (corré una vez `delegar.py --aceptar`).
    69  Antigravity no pudo trabajar: sin pantalla se le negó una herramienta (el mensaje dice qué hacer).
    70  La herramienta (codex o agy) terminó con error; su código real va en el mensaje.
    72  La configuración local del repo trae filtros que ejecutan programas (filter.*.clean/smudge/process).
    71  La herramienta tocó .git/config o los hooks del repo (o Antigravity creó un .git o un enlace en su copia): no se trae
        nada; no confíes en ese repo hasta revisarlo. También si Antigravity tocó .claude/ en su copia.
    73  El cambio de Antigravity no se pudo traer (el repo real cambió mientras trabajaba, o el parche no aplica).
    74  En modo revisar, Antigravity devolvió una respuesta vacía o casi (menos de 200 caracteres): no es una revisión.
    124 La herramienta no terminó a tiempo (METODO_DELEGAR_TOPE, 3600 s por defecto) y se cortó con sus hijos.

Antigravity trabaja sobre una COPIA del repo: solo los archivos versionados o nuevos no ignorados, sin .git, sin archivos
de claves, de entorno, llaves, historiales ni transcripts (por la ruta, el nombre o lo que tienen adentro) y sin enlaces
simbólicos; corre con un entorno en el que git no ejecuta nada aunque plante un .git. Lo que edita vuelve al repo real
como parche, solo por archivos comunes, con la lista completa de lo que vuelve; si toca .claude/ o un CLAUDE.md, o crea
archivos en carpetas que git ignora, no se trae nada; si toca hooks, .vscode, .github, instrucciones de otros agentes o
atributos de git, se avisa en rojo. La copia va en ~/.cache/metodo/agy-trabajo (o METODO_AGY_TRABAJO). Si la
configuración de Antigravity tiene reglas amplias (leer cualquier carpeta, comandos, cualquier página), se avisa en rojo y
se sigue (METODO_AGY_SIN_AVISO_REGLAS=1 lo calla). Codex trabaja sobre la carpeta real (necesita correr los tests con lo instalado): si el repo tiene archivos
de claves o de entorno (aunque git los ignore), Codex se salta y pasa al plan siguiente.
El pedido le llega a agy como argumento de -p (agy no lee el pedido de la entrada estándar salvo en un modo stream-json
que no se usa): mientras corre, otros usuarios de la misma computadora lo podrían ver en la lista de procesos.

Límite conocido: la aceptación (--aceptar) es un freno para personas, no una defensa contra una sesión hostil (que podría
escribir el archivo a mano); la huella de .git no mira config.worktree ni los config de submódulos; /tmp es compartido;
con Codex, los enlaces simbólicos DENTRO del repo que apuntan a otra carpeta los sigue la herramienta; la búsqueda de
archivos de claves no mira adentro de las carpetas ignoradas enteras (node_modules, etc.). El sandbox de Codex puede leer
fuera del repo: no delegues desde un repo al que no le tengas confianza.

Python 3.6+. Solo biblioteca estándar.
"""
import argparse
import hashlib
import json
import os
import re
import signal
import subprocess
import sys

# Windows: la consola usa cp1252 y los ✓/✗ y acentos hacían caer el script; se fuerza UTF-8 en entrada y salida.
for _flujo in (sys.stdin, sys.stdout, sys.stderr):
    try:
        _flujo.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
import time
from pathlib import Path

AQUI = Path(__file__).resolve().parent
if str(AQUI) not in sys.path:
    sys.path.insert(0, str(AQUI))

import radar

TOPE_PEDIDO = 100 * 1024
MODELO_VALIDO = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
NOMBRES_DE_CLAVES = re.compile(r"(^\.env|\.pem$|\.key$|\.p12$|\.pfx$|\.keychain|^id_|credential|credencial|secret|token|\.npmrc$|\.netrc$|known_hosts|authorized_keys|pgpass|history|^config$|kubeconfig|\.git-credentials)", re.I)
# Archivos que nunca viajan a otra IA aunque estén versionados: claves, entorno, llaves, credenciales, historiales y
# transcripts. Las plantillas (.env.example, .env.sample, .env.template, .env.dist) sí viajan: están hechas para compartirse.
# 1) Cualquier tramo de la ruta que sea una de estas carpetas (o el archivo mismo). Los «débiles» (key, keys, private: p. ej.
#    storage/app/private/ de Laravel) quedan afuera de la copia de Gemini, pero no hacen saltar a Codex por sí solos: ahí
#    decide el barrido de contenido.
TRAMOS_SECRETOS = {"secret", "secrets", "credential", "credentials", "credencial", "credenciales", ".envs", ".ssh", ".aws",
                   ".azure", ".gnupg", ".kube", ".docker"}
TRAMOS_DEBILES = {"key", "keys", "private"}
PARES_SECRETOS = {(".config", "gh"), (".config", "gcloud"), (".claude", "projects")}
# 2) Nombres de archivo conocidos:
NOMBRE_SECRETO = re.compile(
    r"^(\.env(?!\.(example|sample|template|dist)$)(\..*)?|.+\.env|\.envrc|\.netrc|\.npmrc|\.pypirc|\.pgpass|\.git-credentials"
    r"|\.mcp\.json|\.claude\.json|id_(rsa|ed25519|ecdsa|dsa)[^/]*|known_hosts|authorized_keys|kubeconfig"
    r"|.*\.(pem|key|p12|p8|pfx|ppk|ovpn|tfvars|tfstate|tfstate\.backup|keystore|jks|kdbx|keychain(-db)?)"
    r"|client_secret.*\.json|service-account.*\.json|\.yarnrc\.yml|auth\.json|\.htpasswd|local\.settings\.json"
    r"|\.vault-token|\.my\.cnf|pip\.conf|\.zsh_history|\.bash_history|history\.jsonl|.*transcripts?.*\.(jsonl|json|txt|md))$",
    re.I)
# 3) token / secret / credential en el nombre, solo en archivos de datos o configuración (o sin extensión): token.json sí;
#    VerifyCsrfToken.php, tokenizer.py, tokens.css o tokens.json (los «design tokens») no.
NOMBRE_SENSIBLE = re.compile(r"token(?!s)|secret|credential|credencial", re.I)
EXT_DATOS = {"", ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf", ".txt", ".db"}
# 4) Contenido (los primeros 64 KB): claves privadas y llaves con forma conocida, aunque el archivo se llame de cualquier modo.
CONTENIDO_SECRETO = re.compile(
    rb"-----BEGIN [A-Z ]*PRIVATE KEY-----|(?<![A-Za-z0-9])AKIA[0-9A-Z]{16}(?![0-9A-Z])|(?<![A-Za-z0-9_])gh[pousr]_[A-Za-z0-9]{36}"
    rb"|(?<![A-Za-z0-9_-])sk-[A-Za-z0-9_-]{20,}|(?<![A-Za-z0-9])xox[abpr]-|(?<![A-Za-z0-9_])AIza[0-9A-Za-z_-]{35}"
    rb'|"private_key"\s*:')
TOPE_CONTENIDO = 64 * 1024
# Lo que imprime agy sin pantalla cuando se le niega una herramienta (no hay quién apruebe): antes terminaba «bien» sin hacer
# nada. Solo cuenta si la salida es corta o agy terminó con error (una respuesta larga puede citar esas palabras).
AGY_DENEGADO = re.compile(r"no output produced|auto-denied|requires the .* permission", re.I)
TOPE_SALIDA_DENEGADA = 600
# Archivos que, si Gemini los toca, pueden ejecutar programas o cambiar cómo se comportan git, el editor o Claude:
# .claude/ no se trae nunca (71); los demás se muestran antes, en rojo.
TRAMOS_CLAUDE = {".claude"}
NOMBRES_CLAUDE = {"claude.md", "claude.local.md"}   # instrucciones que Claude lee solo (en cualquier carpeta)
TRAMOS_DELICADOS = {".husky", ".githooks", ".vscode", ".gemini", ".codex", ".agents", ".cursor", ".devcontainer", ".idea",
                    ".github"}
NOMBRES_DELICADOS = {".gitattributes", ".gitmodules", "agents.md", "gemini.md"}
# git sin ejecutar nada del repo (un repo bajado de afuera puede traer core.fsmonitor, hooks o diff externo en su config)
GIT_SEGURO = ["git", "-c", "core.fsmonitor=false", "-c", "core.hooksPath=/dev/null", "-c", "diff.external=", "-c", "protocol.ext.allow=never"]


class ArgumentParserUso(argparse.ArgumentParser):
    """ArgumentParser que sale con 64 en errores de argumentos."""

    def error(self, message):
        sys.stderr.write("%s: error: %s\n" % (self.prog, message))
        self.print_usage(sys.stderr)
        sys.exit(64)


def git(repo, *args):
    """Corre git de forma segura sobre el repo. Devuelve el CompletedProcess (o None si git no se pudo ejecutar)."""
    env = dict(os.environ)
    env["GIT_OPTIONAL_LOCKS"] = "0"
    try:
        return subprocess.run(
            GIT_SEGURO + ["-C", str(repo)] + list(args),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL,
            universal_newlines=True, encoding="utf-8", env=env, timeout=60,
        )
    except (OSError, subprocess.SubprocessError):
        return None


def es_repo_git(ruta):
    """Verifica si la ruta corresponde a un repositorio git válido."""
    r = git(ruta, "rev-parse", "--is-inside-work-tree")
    return bool(r) and r.returncode == 0 and r.stdout.strip() == "true"


def raiz_del_repo(ruta):
    r = git(ruta, "rev-parse", "--show-toplevel")
    if r and r.returncode == 0 and r.stdout.strip():
        return Path(r.stdout.strip()).resolve()
    return Path(ruta).resolve()


CARPETAS_DE_LLAVES = [".ssh", ".aws", ".gnupg", ".config/gh", ".docker", ".kube", ".gemini", ".codex", ".claude",
                      "Library/Keychains", ".local/share/chezmoi"]
VARIABLES_DE_LLAVES = ["CLAUDE_CONFIG_DIR", "CODEX_HOME"]   # carpetas de configuración puestas en otro lugar


def _misma(a, b):
    """True si las dos rutas son la misma carpeta (sigue enlaces y los firmlinks de macOS); False si alguna no existe."""
    try:
        return os.path.samefile(str(a), str(b))
    except (OSError, ValueError):
        return False


def carpeta_de_llaves(ruta):
    """Descripción de la carpeta de llaves o de configuración de herramientas que contiene `ruta` (o que es), o None."""
    ruta_str = str(ruta).replace("\\", "/")
    ruta_slash = ruta_str.rstrip("/") + "/"
    casa = Path(str(Path.home().resolve()))
    for d in CARPETAS_DE_LLAVES:
        llaves = casa / d
        llaves_txt = str(llaves).replace("\\", "/").rstrip("/") + "/"
        if ruta_slash.lower().startswith(llaves_txt.lower()) or any(_misma(x, llaves) for x in [Path(ruta_str)] + list(Path(ruta_str).parents)):
            return "una carpeta de llaves o de configuración de tus herramientas (~/%s)" % d
    for var in VARIABLES_DE_LLAVES:
        valor = os.environ.get(var, "").strip()
        if not valor:
            continue
        try:
            llaves = Path(valor).expanduser().resolve()
        except (OSError, RuntimeError):
            continue
        llaves_txt = str(llaves).replace("\\", "/").rstrip("/") + "/"
        if ruta_slash.lower().startswith(llaves_txt.lower()) or any(_misma(x, llaves) for x in [Path(ruta_str)] + list(Path(ruta_str).parents)):
            return "la carpeta de configuración de una herramienta (%s=%s)" % (var, valor)
    return None


def es_carpeta_privada(repo_path):
    """(es_privada, motivo). Verifica rutas sensibles que no deben delegarse a planes externos."""
    repo_str = str(repo_path).replace("\\", "/")   # Windows: mismas comparaciones con «/»
    repo_slash = repo_str.rstrip("/") + "/"
    home = str(Path.home().resolve()).replace("\\", "/").rstrip("/") + "/"
    # Por alcance: tu carpeta personal entera, una que la contiene o la raíz del disco no son «un proyecto»: adentro hay de
    # todo (llaves, documentos, otras cuentas). Las carpetas de proyecto (clientes, finanzas, etc.) sí se delegan: las claves
    # y archivos de entorno quedan afuera igual (copia aislada en Antigravity; Codex se salta si los hay).
    # macOS no distingue mayúsculas de minúsculas en las rutas.
    if repo_slash in ("/", "//") or re.match(r"^[A-Za-z]:/$", repo_slash) or home.lower().startswith(repo_slash.lower()):
        return True, "tu carpeta personal entera o la raíz del disco: adentro hay de todo; delegá desde la carpeta del proyecto"
    # la misma carpeta por otro camino (en Mac, /System/Volumes/Data/Users/... es /Users/...)
    casa = Path(home)
    if any(_misma(repo_path, c) for c in [casa] + list(casa.parents)):
        return True, "tu carpeta personal entera o la raíz del disco: adentro hay de todo; delegá desde la carpeta del proyecto"
    # carpetas de llaves y de configuración de las herramientas (incluida la de Claude): ahí no se delega nunca
    llaves = carpeta_de_llaves(repo_path)
    if llaves:
        return True, "%s: ahí no se delega; delegá desde la carpeta del proyecto" % llaves

    extra = os.environ.get("METODO_NO_DELEGAR", "").strip()
    if extra:
        for p in extra.split(os.pathsep):
            p = p.strip()
            if not p:
                continue
            if p.lower() in repo_slash.lower():
                return True, "la marcaste para no delegar (METODO_NO_DELEGAR: %s)" % p
            try:
                p_res = str(Path(p).resolve()).replace("\\", "/")
                if repo_slash.lower().startswith(p_res.lower().rstrip("/") + "/"):
                    return True, "la marcaste para no delegar (METODO_NO_DELEGAR: %s)" % p
            except Exception:
                pass
    return False, None


def arbol_sucio(repo_path):
    """True si hay cambios sin confirmar en el árbol de trabajo (git status --porcelain)."""
    r = git(repo_path, "status", "--porcelain", "--no-ahead-behind")
    if r is None or r.returncode != 0:
        return True   # si no se pudo mirar, no se edita
    return bool(r.stdout.strip())


def _git_plano(repo_path, *args):
    """rev-parse y similares: no ejecutan nada del repo; sin los -c de seguridad (que cambian las rutas que devuelve)."""
    try:
        r = subprocess.run(["git", "-C", str(repo_path)] + list(args), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           stdin=subprocess.DEVNULL, universal_newlines=True, encoding="utf-8", timeout=60)
        return r.stdout.strip() if r.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def huella_git(repo_path):
    """Hash de .git/config (del repo y del común, si es un worktree) y de todos los hooks: si la herramienta los
    toca, lo vemos al terminar."""
    h = hashlib.sha256()
    base = Path(repo_path)
    rutas = []
    for que in ("--git-dir", "--git-common-dir"):
        d = _git_plano(repo_path, "rev-parse", que)
        if d:
            d = Path(d)
            rutas.append(d if d.is_absolute() else base / d)
    vistos = []
    for d in rutas:
        if d in vistos:
            continue
        vistos.append(d)
        archivos = [d / "config"] + (sorted(x for x in (d / "hooks").rglob("*") if x.is_file()) if (d / "hooks").is_dir() else [])
        for a in archivos:
            try:
                h.update(str(a).encode("utf-8", "replace") + b"\0" + (a.read_bytes() if a.is_file() else b"-") + b"\0")
            except OSError:
                h.update(b"?")
    return h.hexdigest()


FILTROS_PELIGROSOS = r"^filter\..*\.(clean|smudge|process)$"


def config_que_ejecuta_programas(repo_path):
    """Claves del config LOCAL del repo que git ejecutaría al comparar archivos (filtros clean/smudge/process). El resto
    (fsmonitor, hooks, diff externo, textconv) ya se neutraliza en GIT_SEGURO."""
    r = git(repo_path, "config", "--local", "--includes", "--name-only", "--get-regexp", FILTROS_PELIGROSOS)
    return r.stdout.split() if r and r.returncode == 0 else []


def es_secreto(rel, para_codex=False):
    """True si la ruta (relativa al repo) es de claves, entorno, llaves, credenciales, historiales o transcripts. Con
    para_codex, las carpetas «débiles» (key, keys, private) no cuentan por sí solas."""
    partes = [x for x in rel.replace("\\", "/").split("/") if x]
    if not partes:
        return False
    bajas = [x.lower() for x in partes]
    tramos = TRAMOS_SECRETOS if para_codex else TRAMOS_SECRETOS | TRAMOS_DEBILES
    if any(x in tramos for x in bajas) or any(par in PARES_SECRETOS for par in zip(bajas, bajas[1:])):
        return True
    nombre = partes[-1]
    if NOMBRE_SECRETO.match(nombre):
        return True
    return bool(NOMBRE_SENSIBLE.search(nombre)) and os.path.splitext(nombre)[1].lower() in EXT_DATOS


def contenido_secreto(ruta):
    """True si los primeros 64 KB del archivo traen una clave privada o una llave con forma conocida."""
    try:
        with open(ruta, "rb") as f:
            return bool(CONTENIDO_SECRETO.search(f.read(TOPE_CONTENIDO)))
    except OSError:
        return True   # si no se puede leer, no viaja


def tramos_delicados(rel):
    """'claude' si toca .claude/ o un CLAUDE.md; 'delicado' si toca hooks, editor, instrucciones de otros agentes, flujos de
    GitHub o atributos de git; None si no."""
    bajas = [x.lower() for x in rel.replace("\\", "/").split("/") if x]
    if any(x in TRAMOS_CLAUDE for x in bajas) or (bajas and bajas[-1] in NOMBRES_CLAUDE):
        return "claude"
    if any(x in TRAMOS_DELICADOS for x in bajas) or (bajas and bajas[-1] in NOMBRES_DELICADOS):
        return "delicado"
    return None


def archivos_de_claves(repo_path, tope=5):
    """Archivos (o carpetas ignoradas enteras) del repo con nombre de claves, entorno, llaves o transcripts, versionados,
    nuevos o ignorados. Se usa para saltar a Codex, que trabaja sobre la carpeta real."""
    r = git(repo_path, "ls-files", "-z", "--cached", "--others", "--ignored", "--exclude-standard", "--directory")
    r2 = git(repo_path, "ls-files", "-z", "--cached", "--others", "--exclude-standard")
    if r is None or r.returncode != 0 or r2 is None or r2.returncode != 0:
        return ["(no pude listar los archivos del repo)"]
    vistos = []
    for rel in sorted(set((r.stdout + "\0" + r2.stdout).split("\0"))):
        if not rel or rel in vistos:
            continue
        if es_secreto(rel, para_codex=True):
            vistos.append(rel)
        elif es_secreto(rel):   # solo por una carpeta key/keys/private: decide lo que tiene adentro
            ruta = os.path.join(str(repo_path), *rel.split("/"))
            if os.path.isfile(ruta) and not os.path.islink(ruta) and contenido_secreto(ruta):
                vistos.append(rel)
    return vistos[:tope]


def copia_aislada(repo_path, destinos):
    """Copia a cada destino los archivos versionados o nuevos no ignorados del repo, sin .git, sin archivos de claves o de
    entorno y sin enlaces simbólicos (ni archivos que, por una carpeta enlazada, caigan fuera del repo). Devuelve cuántos
    archivos de claves quedaron afuera: (por el nombre, por el contenido)."""
    import shutil
    r = git(repo_path, "ls-files", "-z", "--cached", "--others", "--exclude-standard")
    if r is None or r.returncode != 0:
        raise OSError("no pude listar los archivos del repo")
    raiz = os.path.realpath(str(repo_path)).rstrip(os.sep) + os.sep
    fuera = contenido = 0
    for d in destinos:
        os.makedirs(d)
    for rel in sorted(set(r.stdout.split("\0"))):
        if not rel:
            continue
        if es_secreto(rel):
            fuera += 1
            continue
        partes = rel.split("/")
        if any(x in ("", ".", "..") or x.lower() == ".git" for x in partes):
            continue
        src = os.path.join(str(repo_path), *partes)
        if os.path.islink(src) or not os.path.isfile(src) or not os.path.realpath(src).startswith(raiz):
            continue
        if contenido_secreto(src):
            contenido += 1
            continue
        for d in destinos:
            dst = os.path.join(d, *partes)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst, follow_symlinks=False)
    return fuera, contenido


def revisar_copia(trab):
    """(problema, claves): un .git, un repo pelado o un enlace simbólico en la copia (problema: no se trae nada) y los archivos con nombre
    de claves que creó la herramienta (se descartan: nunca vuelven al repo)."""
    claves = []
    for raiz, dirs, archivos in os.walk(trab):
        if "HEAD" in archivos and "objects" in dirs and "refs" in dirs:   # un repo sin la carpeta .git
            return os.path.relpath(raiz, trab).replace(os.sep, "/"), []
        for n in dirs + archivos:
            full = os.path.join(raiz, n)
            rel = os.path.relpath(full, trab).replace(os.sep, "/")
            if n.lower() == ".git" or os.path.islink(full):
                return rel, []
            if n in archivos and es_secreto(rel):
                claves.append(rel)
    return None, claves


def archivos_cambiados(base, trab):
    """Rutas relativas nuevas, borradas o distintas entre la copia original y la que editó la herramienta."""
    import filecmp

    def lista(raiz):
        out = set()
        for r, _dirs, archivos in os.walk(raiz):
            for n in archivos:
                out.add(os.path.relpath(os.path.join(r, n), raiz).replace(os.sep, "/"))
        return out
    a, b = lista(base), lista(trab)
    distintos = {x for x in a & b if not filecmp.cmp(os.path.join(base, x), os.path.join(trab, x), shallow=False)}
    return sorted((a ^ b) | distintos)


def rutas_ignoradas(repo_path, rutas):
    """Las rutas (relativas) que el repo real ignora (.gitignore): no aparecen en git status ni en git diff, así que un
    archivo que vuelva ahí (node_modules/.bin/…) pasaría sin que nadie lo vea. OSError si git falla."""
    if not rutas:
        return []
    env = dict(os.environ)
    env["GIT_OPTIONAL_LOCKS"] = "0"
    r = subprocess.run(GIT_SEGURO + ["-C", str(repo_path), "check-ignore", "--stdin", "-z"],
                       input="\0".join(rutas) + "\0", stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       universal_newlines=True, encoding="utf-8", errors="replace", env=env, timeout=60)
    if r.returncode == 1:
        return []
    if r.returncode != 0:
        raise OSError("git check-ignore falló: %s" % r.stderr[:200])
    return [x for x in r.stdout.split("\0") if x]


def diff_de_la_copia(tmp):
    """Parche (texto binario-seguro) entre tmp/base y tmp/trab, sin ejecutar nada que venga de un repo."""
    env = dict(os.environ)
    env["GIT_CEILING_DIRECTORIES"] = os.path.dirname(str(tmp))   # no buscar un repo en las carpetas de arriba
    env["GIT_OPTIONAL_LOCKS"] = "0"
    r = subprocess.run(GIT_SEGURO + ["-C", str(tmp), "--no-pager", "diff", "--no-index", "--binary", "--no-ext-diff",
                                     "--no-textconv", "base", "trab"],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL, env=env, timeout=300)
    if r.returncode not in (0, 1):
        raise OSError("git diff falló: %s" % r.stderr.decode("utf-8", "replace")[:200])
    return r.stdout


def carpeta_de_trabajo_agy():
    """Dónde va la copia aislada: METODO_AGY_TRABAJO o ~/.cache/metodo/agy-trabajo (solo para vos, fuera de la
    configuración de Claude). Borra las copias agy.* de más de 24 h que haya dejado una corrida cortada."""
    import shutil
    raiz = Path(os.environ.get("METODO_AGY_TRABAJO") or (Path.home() / ".cache" / "metodo" / "agy-trabajo"))
    raiz.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(str(raiz), 0o700)
    except OSError:
        pass
    limite = time.time() - 24 * 3600
    for d in raiz.glob("agy.*"):
        try:
            if d.is_dir() and not d.is_symlink() and d.stat().st_mtime < limite:
                shutil.rmtree(str(d), ignore_errors=True)
        except OSError:
            pass
    return raiz


def args_modelo_agy(plan):
    """Argumentos --model/--effort para `agy`. El radar usa ids de API («gemini-3.8-flash», «gemini-3.1-pro-preview»);
    `agy` pide el id sin «-preview» y un nivel de esfuerzo aparte (si el id ya trae -low/-medium/-high, no se agrega).
    El id y el esfuerzo se validan: el radar se baja de internet y no puede colar un argumento raro."""
    api = str(plan.get("modelo_api") or "").strip()
    if not api:
        return []
    if api.endswith("-preview"):
        api = api[: -len("-preview")]
    if not MODELO_VALIDO.match(api):
        raise ValueError("modelo con forma rara: %r" % api[:80])
    if api.endswith(("-low", "-medium", "-high")):
        return ["--model", api]
    esfuerzo = os.environ.get("METODO_AGY_ESFUERZO", "high").strip() or "high"
    if not MODELO_VALIDO.match(esfuerzo):
        raise ValueError("esfuerzo con forma rara: %r" % esfuerzo[:80])
    return ["--model", api, "--effort", esfuerzo]


# Antigravity no conoce todos los ids del radar (gemini-3.1-pro-preview → «gemini-3.1-pro-high» no existe): si se le pasa
# uno que no tiene, elige otro por su cuenta (GPT-OSS) y devuelve vacío. El modelo se confirma contra `agy models`.
MODELO_AGY_CONOCIDO = "gemini-3.8-flash-high"
ID_MODELO = re.compile(r"(?<![A-Za-z0-9._-])([a-z][a-z0-9]*(?:[.-][a-z0-9]+)+)(?![A-Za-z0-9._-])")
GEMINI_HIGH = re.compile(r"^gemini-([0-9]+(?:\.[0-9]+)*)-([a-z0-9.-]+-)?high$")
TOPE_REVISION_VACIA = 200


def modelos_agy(bin_cli, tope=30):
    """Ids que lista `agy models` (solo lectura), o None si no se pudo ejecutar o no se entendió la salida. Corre en una
    carpeta temporal vacía, en su propio grupo de procesos, y se corta entero si pasa el tope."""
    import tempfile
    carpeta = tempfile.mkdtemp(prefix="agy-modelos.")
    try:
        p = subprocess.Popen([bin_cli, "models"], cwd=carpeta, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                             stdin=subprocess.DEVNULL, universal_newlines=True, encoding="utf-8", errors="replace",
                             start_new_session=True)
    except OSError:
        os.rmdir(carpeta)
        return None
    try:
        out, _ = p.communicate(timeout=tope)
    except subprocess.TimeoutExpired:
        return None
    finally:
        _cortar_grupo(p)
        try:
            p.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass
        import shutil
        shutil.rmtree(carpeta, ignore_errors=True)
    if p.returncode != 0:
        return None
    ids = []
    for m in ID_MODELO.finditer(out or ""):
        x = m.group(1)
        if MODELO_VALIDO.match(x) and any(c.isdigit() for c in x) and x not in ids:
            ids.append(x)
    return ids or None


def mejor_gemini_high(ids):
    """El Gemini «-high» de versión más alta (a igual versión, «pro» antes que el resto)."""
    def clave(x):
        m = GEMINI_HIGH.match(x)
        return (tuple(int(n) for n in m.group(1).split(".")), "pro" in x)
    candidatos = [x for x in ids if GEMINI_HIGH.match(x)]
    return max(candidatos, key=clave) if candidatos else None


def resolver_modelo_agy(plan, bin_cli, consultar=True):
    """(argumentos --model, aviso o None). Nunca deja que agy elija el modelo: si el del radar no está en `agy models`,
    usa el mejor Gemini «-high» disponible y lo avisa; si la lista no se puede leer, uno conocido. (None, motivo) si
    Antigravity no ofrece ningún Gemini «-high». ValueError si el radar trae un id con forma rara."""
    pedido = args_modelo_agy(plan)
    candidato = (pedido[1] + "-" + pedido[3] if len(pedido) == 4 else pedido[1]) if pedido else None
    if not consultar:
        return ["--model", MODELO_AGY_CONOCIDO], ("no consulté la lista de modelos de Antigravity (su cupo no dio «ok»): "
                                                   "uso %s" % MODELO_AGY_CONOCIDO)
    ids = modelos_agy(bin_cli)
    if ids is None:
        return ["--model", MODELO_AGY_CONOCIDO], ("no pude leer la lista de modelos de Antigravity (agy models): uso %s"
                                                   % MODELO_AGY_CONOCIDO)
    if candidato in ids:
        return ["--model", candidato], None
    elegido = mejor_gemini_high(ids)
    if not elegido:
        return None, ("Antigravity no ofrece ningún modelo Gemini «-high» (agy models: %s); no lo lanzo para que no "
                      "elija uno por su cuenta" % ", ".join(ids[:6]))
    return ["--model", elegido], ("el modelo del radar (%s) no está en Antigravity; uso %s, el mejor Gemini disponible"
                                  % (candidato or "ninguno", elegido))


def binario_seguro(ruta, repo_path):
    """Ruta absoluta y ejecutable, fuera del repo (cwd de la herramienta: un ./codex plantado por el repo no corre)."""
    if not ruta:
        return None
    real = os.path.realpath(ruta)
    if not os.path.isabs(real) or not os.path.isfile(real) or not os.access(real, os.X_OK):
        return None
    base = str(Path(repo_path).resolve()).rstrip("/") + "/"
    if (real + "/").startswith(base):
        return None
    return real


def ruta_aceptacion():
    return radar.carpeta_metodo() / "delegar-aceptado.json"


def esta_aceptado():
    try:
        return json.loads(ruta_aceptacion().read_text(encoding="utf-8")).get("aceptado") is True
    except Exception:
        return False


def confirmar_interactivo():
    """Una persona, en una terminal: una sesión de IA (sin terminal) no puede darse el permiso sola."""
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        sys.stderr.write("--aceptar lo tiene que correr una persona en su terminal (no hay terminal interactiva acá).\n")
        return False
    print("El repo que delegues viaja a OpenAI (Codex) o a Google (Antigravity), menos las claves y los archivos de "
          "entorno, que delegar deja afuera; los planes gratuitos pueden entrenar con lo que reciben. Si un repo tiene "
          "datos que no pueden salir, no lo delegues (o ponelo en METODO_NO_DELEGAR).")
    return input("Escribí SI para aceptar: ").strip().upper() == "SI"


def aceptar():
    if not confirmar_interactivo():
        return 64
    ruta = ruta_aceptacion()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    tmp = ruta.with_name(ruta.name + ".tmp")
    tmp.write_text(json.dumps({"aceptado": True, "fecha": time.strftime("%Y-%m-%d")}), encoding="utf-8")
    os.chmod(str(tmp), 0o600)
    os.replace(str(tmp), str(ruta))
    print("Aceptado ✓  A partir de ahora delegar.py manda el código del repo que le indiques a Codex (OpenAI) o a "
          "Antigravity (Google), menos las claves y los archivos de entorno, y los planes gratuitos pueden entrenar con "
          "lo enviado. Para retirar el permiso, borrá %s." % ruta)
    return 0


def parsear_argumentos(argv=None):
    ap = ArgumentParserUso(
        prog="delegar.py",
        description="Delegador de tareas a IAs del plugin metodo.",
    )
    ap.add_argument("categoria", nargs="?", help="Categoría del radar (ej. desarrollo, revision)")
    ap.add_argument("repo", nargs="?", help="Ruta al repositorio git donde trabajar")
    ap.add_argument("pedido", nargs="?", help="Texto de la tarea (o la ruta de un archivo, con --archivo)")
    ap.add_argument("--archivo", action="store_true", help="El pedido es la ruta de un archivo de texto")
    ap.add_argument("--revisar", action="store_true", help="Modo solo lectura (no edita, permite árbol sucio)")
    ap.add_argument("--sensible", action="store_true", help="Excluye planes que no admiten datos privados")
    ap.add_argument("--dry-run", action="store_true", help="Muestra el plan elegido y el comando sin ejecutar")
    ap.add_argument("--aceptar", action="store_true", help="Acepta (una vez) el envío del código a un tercero")
    a = ap.parse_args(argv)
    if not a.aceptar and not (a.categoria and a.repo and a.pedido):
        ap.error("faltan argumentos: categoria, repo y pedido")
    return a


def bases_permitidas(repo_path):
    """El archivo del pedido tiene que estar en el repo o en una carpeta temporal (por la ruta real, siguiendo enlaces)."""
    import tempfile
    bases = [Path(repo_path).resolve(), Path(tempfile.gettempdir()).resolve(), Path("/tmp").resolve(), Path("/var/tmp").resolve()]
    return [str(b).rstrip("/") + "/" for b in bases]


def leer_pedido(args, repo_path):
    """(texto, error). El pedido es texto; solo es un archivo si se pidió con --archivo."""
    if not args.archivo:
        texto = args.pedido
    else:
        p = Path(args.pedido)
        real = Path(os.path.realpath(str(p)))
        escrito = Path(os.path.abspath(str(p)))
        if NOMBRES_DE_CLAVES.search(p.name) or NOMBRES_DE_CLAVES.search(real.name):
            return None, "«%s» parece un archivo de claves: no se manda." % p.name
        # mismo filtro que los archivos que viajan del repo: nombre y carpetas (secrets/, keys/…), medidos desde el repo o
        # la carpeta temporal donde está el pedido, por la ruta escrita y por la real (un enlace no lo saltea)
        for ruta in (escrito, real):
            txt = str(ruta).replace("\\", "/")
            base = next((b for b in bases_permitidas(repo_path) if (txt + "/").startswith(b)), None)
            rel = txt[len(base):] if base else ruta.name
            if es_secreto(rel):
                return None, "«%s» parece un archivo de claves (por el nombre o la carpeta en la que está): no se manda." % p.name
            if carpeta_de_llaves(ruta):
                return None, ("«%s» está en %s: parece un archivo de claves, no se manda."
                              % (p.name, carpeta_de_llaves(ruta)))
        if not any((str(real) + "/").startswith(b) for b in bases_permitidas(repo_path)):
            return None, "el archivo del pedido tiene que estar dentro del repo o en una carpeta temporal (no en «%s»)." % real.parent
        try:
            if not p.is_file() or p.stat().st_size > TOPE_PEDIDO:
                return None, "el archivo del pedido no existe o pasa de %d KB." % (TOPE_PEDIDO // 1024)
            texto = p.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            return None, "no pude leer el archivo del pedido (%s): no lo mando como texto." % e.__class__.__name__
    if len(texto.encode("utf-8")) > TOPE_PEDIDO:
        return None, "el pedido pasa de %d KB." % (TOPE_PEDIDO // 1024)
    return texto, None


def _cortar_grupo(p):
    """TERM al grupo de procesos de la herramienta y, si algo sigue vivo a los 3 s, KILL. Se llama siempre al salir."""
    for sig, espera in ((signal.SIGTERM, 3.0), (signal.SIGKILL, 0.5)):
        try:
            os.killpg(p.pid, sig)
        except (ProcessLookupError, PermissionError):
            return
        limite = time.time() + espera
        while time.time() < limite:
            try:
                os.killpg(p.pid, 0)
            except (ProcessLookupError, PermissionError):
                return
            time.sleep(0.1)


def entorno_git_neutro(carpeta):
    """Entorno para la herramienta: git no busca repos por encima de `carpeta` y, aunque la herramienta plante un .git en
    su copia, no ejecuta nada de su configuración (fsmonitor, hooks, diff externo, paginador)."""
    env = dict(os.environ)
    env["GIT_CEILING_DIRECTORIES"] = str(carpeta)
    env["GIT_DIR"] = os.path.join(str(carpeta), "no-existe")   # git no usa ningún repo, ni uno armado en la copia
    for k in ("GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_CONFIG_PARAMETERS", "GIT_OBJECT_DIRECTORY",
              "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_COMMON_DIR"):
        env.pop(k, None)
    forzado = [("core.fsmonitor", "false"), ("core.hooksPath", "/dev/null"), ("diff.external", ""), ("core.pager", "cat"),
               ("protocol.ext.allow", "never")]
    for k in [k for k in env if k.startswith(("GIT_CONFIG_KEY_", "GIT_CONFIG_VALUE_"))]:
        del env[k]
    env["GIT_CONFIG_COUNT"] = str(len(forzado))
    for i, (k, v) in enumerate(forzado):
        env["GIT_CONFIG_KEY_%d" % i] = k
        env["GIT_CONFIG_VALUE_%d" % i] = v
    return env


def ejecutar(cmd, cwd, entrada, tope, salida=None, env=None):
    """Corre la herramienta en su propio grupo de procesos y SIEMPRE corta el grupo entero al salir (al terminar, al
    vencer el tope, con Ctrl-C o ante cualquier error): ningún hijo queda editando en segundo plano. Devuelve el
    código de salida, o None si se cortó por tiempo. Con `salida` (una lista) junta ahí lo que imprimió la herramienta."""
    # SIGTERM / SIGHUP (cerrar la terminal, kill) también tienen que pasar por el `finally`: con start_new_session la
    # herramienta no recibe esas señales sola y quedaría editando en segundo plano
    anteriores = {}

    def _salir(signum, _frame):
        raise SystemExit(128 + signum)

    for sig in (signal.SIGTERM, signal.SIGHUP):
        try:
            anteriores[sig] = signal.signal(sig, _salir)
        except (ValueError, OSError):   # fuera del hilo principal no se pueden cambiar: queda el comportamiento normal
            pass
    p = subprocess.Popen(
        cmd, cwd=cwd, stdin=subprocess.PIPE if entrada is not None else subprocess.DEVNULL,
        universal_newlines=True, encoding="utf-8", errors="replace", start_new_session=True, env=env,
        **({"stdout": subprocess.PIPE, "stderr": subprocess.STDOUT} if salida is not None else {})
    )
    try:
        out, _ = p.communicate(input=entrada, timeout=tope)
        if salida is not None:
            salida.append(out or "")
        return p.returncode
    except subprocess.TimeoutExpired:
        return None
    finally:
        _cortar_grupo(p)
        try:
            p.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass
        for sig, viejo in anteriores.items():
            try:
                signal.signal(sig, viejo)
            except (ValueError, OSError, TypeError):
                pass


COPIA = "<copia aislada del repo>"


def reglas_amplias_agy():
    """Reglas de la configuración de Antigravity que dejan leer más allá de la copia, escribir, ejecutar o mandar datos a
    cualquier página sin preguntar. Solo lee el archivo (no ejecuta agy); [] si no existe o no se entiende."""
    ruta = Path.home() / ".gemini" / "antigravity-cli" / "settings.json"
    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        allow = datos.get("permissions", {}).get("allow", [])
    except (OSError, ValueError, AttributeError):
        return []
    if not isinstance(allow, list):
        return []
    out = []
    for r in allow:
        if not isinstance(r, str):
            continue
        if (r.startswith("read_file(") and "**" in r) or r.startswith(("write_file(", "command(")) \
                or (r.startswith("read_url(") and "*" in r):
            out.append(r)
    return out
MENSAJE_DENEGADO = (
    "Gemini no pudo trabajar: sin pantalla se le negó una herramienta y nadie la puede aprobar. Opciones: (1) poné lo "
    "que tiene que leer DENTRO del repo (no en otra carpeta); (2) no le pidas comandos (git, cat, tests…): dale los datos "
    "ya listos en el pedido (Gemini trabaja en una copia sin la historia de git: los comandos de git no le sirven); (3) si "
    "lo que se le niega es leer su propia copia, probá poner la carpeta de trabajo dentro de tus proyectos (por ejemplo "
    "METODO_AGY_TRABAJO=~/Proyectos/sandbox/agy-trabajo). No agregues reglas amplias a la configuración de Antigravity "
    "para destrabarlo, y nunca --dangerously-skip-permissions.\n"
)


def ejecutar_agy_aislado(cmd, repo_path, args, tope):
    """Antigravity sobre una copia del repo (sin .git, claves ni enlaces). Lo que edita vuelve como parche al repo real,
    solo por archivos comunes; si crea un .git o un enlace en la copia, no se trae nada."""
    import shutil
    import tempfile
    tmp = tempfile.mkdtemp(prefix="agy.", dir=str(carpeta_de_trabajo_agy()))
    try:
        base, trab = os.path.join(tmp, "base"), os.path.join(tmp, "trab")
        try:
            fuera, por_contenido = copia_aislada(repo_path, [base, trab])
        except OSError as e:
            sys.stderr.write("No pude armar la copia del repo para Gemini (%s). No se delegó nada.\n" % e)
            return 64
        if fuera or por_contenido:
            print("(no viajan a Gemini %d archivo(s) de claves o de entorno por el nombre y %d por lo que tienen adentro)"
                  % (fuera, por_contenido))
        amplias = [] if os.environ.get("METODO_AGY_SIN_AVISO_REGLAS") == "1" else reglas_amplias_agy()
        if amplias:
            rojo, fin = ("\033[31m", "\033[0m") if sys.stdout.isatty() else ("", "")
            print("%s✗ ATENCIÓN: tu configuración de Antigravity tiene reglas amplias (%s%s): un repo con instrucciones "
                  "escondidas podría hacerle leer más allá de la copia y mandar datos afuera. Sigo igual; para no ver este "
                  "aviso, METODO_AGY_SIN_AVISO_REGLAS=1.%s" % (rojo, ", ".join(amplias[:5]),
                                                               "…" if len(amplias) > 5 else "", fin))
        cmd = [trab if c == COPIA else c for c in cmd]
        antes = huella_git(repo_path)
        salida = []
        codigo = ejecutar(cmd, trab, None, tope, salida=salida, env=entorno_git_neutro(tmp))
        texto = "".join(salida)
        if texto:
            sys.stdout.write(texto if texto.endswith("\n") else texto + "\n")
        if huella_git(repo_path) != antes:
            sys.stderr.write(
                "ATENCIÓN: cambió .git/config o los hooks de «%s» mientras trabajaba Gemini (en una copia sin .git). No "
                "corras git en ese repo ni confíes en él hasta revisarlos a mano.\n" % args.repo)
            return 71
        if codigo is None:
            sys.stderr.write("La herramienta no terminó en %d s y se cortó (con sus procesos hijos). El repo real no se tocó.\n" % int(tope))
            return 124
        if AGY_DENEGADO.search(texto) and (codigo != 0 or len(texto.strip()) < TOPE_SALIDA_DENEGADA):
            sys.stderr.write(MENSAJE_DENEGADO)
            return 69
        if codigo != 0:
            sys.stderr.write("La herramienta terminó con error (código %d). El repo real no se tocó.\n" % codigo)
            return 70
        if args.revisar and len(texto.strip()) < TOPE_REVISION_VACIA:
            sys.stderr.write(
                "La revisión volvió vacía o casi (%d caracteres): no es una revisión. Probá otro modelo de Antigravity "
                "(mirá cuáles hay con «agy models») o pedí el informe con los datos ya puestos en el pedido.\n"
                % len(texto.strip()))
            return 74
        problema, claves = revisar_copia(trab)
        if problema:
            sys.stderr.write("Gemini creó «%s» (una carpeta .git o un enlace simbólico) en su copia: no traigo nada al repo.\n" % problema)
            return 71
        for rel in claves:   # un archivo de claves que haya creado Gemini nunca vuelve al repo
            os.unlink(os.path.join(trab, *rel.split("/")))
        if claves:
            print("(descarté %d archivo(s) con nombre de claves que creó Gemini: %s)" % (len(claves), ", ".join(claves[:3])))
        try:
            parche = diff_de_la_copia(tmp)
        except (OSError, subprocess.SubprocessError) as e:
            sys.stderr.write("No pude comparar la copia de Gemini (%s). El repo real no se tocó.\n" % e)
            return 73
        if args.revisar:
            if parche:
                print("Aviso: en modo revisar Gemini editó su copia (descartado; el repo real no se tocó).")
            return 0
        cambiados = archivos_cambiados(base, trab)
        de_claude = [x for x in cambiados if tramos_delicados(x) == "claude"]
        if de_claude:
            sys.stderr.write("Gemini tocó la configuración o las instrucciones de Claude en su copia (%s): no traigo nada al repo. Revisá el "
                             "pedido; si de verdad hace falta cambiarla, hacelo en esta sesión.\n" % ", ".join(de_claude[:3]))
            return 71
        vuelven = [x for x in cambiados if os.path.isfile(os.path.join(trab, *x.split("/")))]
        try:
            ignoradas = rutas_ignoradas(repo_path, vuelven)
        except (OSError, subprocess.SubprocessError) as e:
            sys.stderr.write("No pude comprobar qué archivos ignora el repo (%s): no traigo nada.\n" % e)
            return 73
        if ignoradas:
            sys.stderr.write("Gemini creó o cambió archivos en carpetas que git ignora (%s): no se verían en git status ni "
                             "en el diff, así que no traigo nada al repo.\n" % ", ".join(ignoradas[:5]))
            return 71
        delicados = [x for x in cambiados if tramos_delicados(x) == "delicado"]
        if arbol_sucio(repo_path):
            sys.stderr.write("El repo real cambió mientras trabajaba Gemini (tenía que tocar solo su copia): revisalo a "
                             "mano; no traje su cambio.\n")
            return 73
        if parche:
            ruta_parche = os.path.join(tmp, "cambios.patch")
            with open(ruta_parche, "wb") as f:
                f.write(parche)
            chk = git(repo_path, "apply", "-p2", "--check", ruta_parche)
            ok = chk is not None and chk.returncode == 0
            if ok:
                ap = git(repo_path, "apply", "-p2", ruta_parche)
                ok = ap is not None and ap.returncode == 0
            if not ok:
                sys.stderr.write("El cambio de Gemini no se pudo aplicar al repo (el repo real quedó como estaba).\n")
                return 73
        if delicados:
            rojo, fin = ("\033[31m", "\033[0m") if sys.stdout.isatty() else ("", "")
            print("%s✗ ATENCIÓN: Gemini cambió archivos que pueden ejecutar programas o cambiar cómo se comportan git o "
                  "tu editor: %s. Revisalo antes de correr nada.%s" % (rojo, ", ".join(delicados), fin))
        print("── Archivos que vuelven de la copia de Gemini (%d) ──" % len(cambiados))
        for x in cambiados:
            en_base = os.path.isfile(os.path.join(base, *x.split("/")))
            en_trab = os.path.isfile(os.path.join(trab, *x.split("/")))
            print("  %s %s" % ("cambiado" if en_base and en_trab else ("nuevo   " if en_trab else "borrado "), x))
        print("── Cambios (revisalos y corré los tests) ──")
        res_st = git(repo_path, "status", "--short", "--no-ahead-behind")
        if res_st and res_st.stdout:
            sys.stdout.write(res_st.stdout)
        res_df = git(repo_path, "diff", "--stat", "--no-ext-diff", "--no-textconv")
        if res_df and res_df.stdout:
            sys.stdout.write(res_df.stdout)
        print("Todo al día ✓")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main(argv=None):
    args = parsear_argumentos(argv)
    if args.aceptar:
        return aceptar()

    # 1. Chequeo de repositorio (64 uso)
    repo_path = Path(args.repo).resolve()
    if not repo_path.is_dir() or not es_repo_git(repo_path):
        sys.stderr.write("«%s» no es un repositorio git válido. delegar.py exige un repositorio git.\n" % args.repo)
        return 64

    # 2. Chequeo de alcance (65): la ruta resuelta, la escrita (un enlace) y la raíz del repo
    privada, motivo = es_carpeta_privada(repo_path)
    if not privada:
        privada, motivo = es_carpeta_privada(Path(os.path.abspath(args.repo)))
    if not privada:
        privada, motivo = es_carpeta_privada(raiz_del_repo(repo_path))
    if privada:
        sys.stderr.write(
            "No se delega en carpetas privadas: %s. Hacelo en esta sesión.\n" % motivo
        )
        return 65

    # 3. Cargar radar y buscar categoría (2 categoría desconocida)
    radar_data, _ = radar.cargar()
    cat = radar.buscar_categoria(radar_data, args.categoria)
    if not cat:
        print("No conozco la categoría «%s». Las que hay: %s" % (args.categoria, radar._ids(radar_data)))
        return 2

    # 4. Filtrar copia de la categoría solo con herramientas ejecutables (Codex, Antigravity, Claude Code)
    cat_copia = dict(cat)
    herramientas_validas = ("Codex", "Antigravity", "Claude Code")
    cat_copia["planes"] = [
        p for p in (cat.get("planes") or [])
        if any(str(p.get("herramienta", "")).startswith(h) for h in herramientas_validas)
    ]

    # 4b. Codex trabaja sobre la carpeta real: si el repo tiene archivos de claves o de entorno, se salta (Antigravity
    #     trabaja en una copia que los deja afuera; si no hay otra, le toca a Claude Code en esta sesión)
    saltados_antes = []
    if any(str(p.get("herramienta", "")).startswith("Codex") for p in cat_copia["planes"]):
        claves = archivos_de_claves(repo_path)
        if claves:
            motivo_codex = ("el repo tiene archivos de claves o de entorno (%s; cuentan aunque git los ignore) y Codex "
                            "trabaja sobre la carpeta real, donde podría leerlos" % ", ".join(claves[:3]))
            saltados_antes = [(p, motivo_codex) for p in cat_copia["planes"] if str(p.get("herramienta", "")).startswith("Codex")]
            cat_copia["planes"] = [p for p in cat_copia["planes"] if not str(p.get("herramienta", "")).startswith("Codex")]

    # 5. Elegir plan con modo delegar
    plan, saltados, cupos = radar.elegir(radar_data, cat_copia, sensible=args.sensible, delegar=True)
    saltados = saltados_antes + saltados

    # Si ningún plan quedó disponible (1)
    if plan is None:
        if saltados:
            detalle = "; ".join("%s (%s): %s" % (p.get("plan"), radar._nombre_plan(p), m) for p, m in saltados)
            print("Ningún plan disponible para «%s» ahora. Saltó: %s." % (cat.get("nombre", args.categoria), detalle))
        else:
            print("Ningún plan disponible para «%s» ahora." % cat.get("nombre", args.categoria))
        return 1

    # Imprimir línea previa obligatoria
    if saltados:
        motivos = "; ".join("%s (%s): %s" % (p.get("plan"), p.get("herramienta"), m) for p, m in saltados)
    else:
        motivos = "ninguno"
    print("Plan elegido: %s · saltó: %s" % (radar._nombre_plan(plan), motivos))

    # 6. Adaptador Claude Code (3)
    herramienta = str(plan.get("herramienta", ""))
    if herramienta.startswith("Claude Code"):
        print("El plan elegido es Claude Code: hacelo en esta sesión (cupo disponible).")
        return 3

    # 7. Aceptación del envío a un tercero (68) y árbol sucio al editar (66; con --revisar no se exige)
    if not args.dry_run and not esta_aceptado():
        sys.stderr.write(
            "Falta aceptar que el código de «%s» se envía a un tercero (%s). Viaja el repo entero menos las claves y los "
            "archivos de entorno, y los planes gratuitos pueden entrenar con lo enviado. Pedile a la persona que, si está de acuerdo, corra UNA vez en su "
            "terminal (no lo corras vos): python3 %s --aceptar\n" % (args.repo, "OpenAI" if herramienta.startswith("Codex") else "Google", Path(__file__).resolve())
        )
        return 68
    peligrosas = config_que_ejecuta_programas(repo_path)
    if peligrosas:
        sys.stderr.write(
            "El repo «%s» trae en su configuración programas que git ejecutaría al leerlo (%s). No se delega: "
            "revisá esa configuración o hacelo en esta sesión.\n" % (args.repo, ", ".join(peligrosas[:3]))
        )
        return 72
    if not args.revisar and arbol_sucio(repo_path):
        sys.stderr.write(
            "El árbol de trabajo en «%s» tiene cambios sin confirmar (o no se pudo leer).\n"
            "Para editar se exige un árbol limpio. Hacé commit o stash antes de delegar "
            "(o usá --revisar si solo querés análisis).\n" % args.repo
        )
        return 66

    # 8. Texto del pedido (64 si es ilegible o demasiado grande)
    pedido_texto, error = leer_pedido(args, repo_path)
    if error:
        sys.stderr.write("Pedido rechazado: %s\n" % error)
        return 64

    # 9. Construir comando según adaptador y verificar CLI instalada (67)
    prompt_mostrado = None
    if herramienta.startswith("Codex"):
        bin_cli = binario_seguro(radar._buscar_bin("codex", "RADAR_CODEX_BIN"), repo_path)
        if not bin_cli:
            sys.stderr.write("La CLI de Codex («codex») no está instalada, no se encuentra o está dentro del repo.\n")
            return 67
        cmd = [
            bin_cli,
            "exec",
            "-C",
            str(repo_path),
            "--sandbox",
            "read-only" if args.revisar else "workspace-write",
            "-",
        ]
        usa_stdin = True
    elif herramienta.startswith("Antigravity"):
        bin_cli = binario_seguro(radar._buscar_bin("agy", "RADAR_AGY_BIN"), repo_path)
        if not bin_cli:
            sys.stderr.write("La CLI de Antigravity («agy») no está instalada, no se encuentra o está dentro del repo.\n")
            return 67
        try:
            if args.dry_run:   # sin ejecutar nada: el modelo se confirma contra `agy models` al lanzar
                modelo, aviso_modelo = args_modelo_agy(plan), None
            else:
                cupo_ok = (cupos or {}).get("antigravity", ("sin_dato",))[0] == "ok"
                modelo, aviso_modelo = resolver_modelo_agy(plan, bin_cli, consultar=cupo_ok)
        except ValueError as e:
            sys.stderr.write("No se ejecuta: %s.\n" % e)
            return 64
        if modelo is None:
            sys.stderr.write("No se ejecuta: %s.\n" % aviso_modelo)
            return 67
        if aviso_modelo:
            print("Modelo: %s." % aviso_modelo)
        cmd = [bin_cli] + modelo
        cmd.extend(["--mode", "plan" if args.revisar else "accept-edits"])
        cmd.extend(["--add-dir", COPIA])   # la carpeta de la copia aislada se pone al ejecutar
        instruccion = (
            "Solo leé y analizá; no edites nada. Si el pedido ya trae todo lo que hay que revisar, no uses herramientas: "
            "respondé con el informe completo."
            if args.revisar
            else "Editá solo lo pedido. No toques archivos de claves ni de variables de entorno."
        )
        # «Tarea:» al principio: un pedido que empiece con «--» no puede leerse como opción
        prompt_completo = (
            "Tarea: " + pedido_texto
            + "\n\nTrabajás en una copia del repo (sin .git ni archivos de claves): leé y editá acá, con rutas relativas; "
            + "no edites nada fuera de esta carpeta. NO corras ningún comando. "
            + instruccion
            + " Respondé en castellano, corto: qué hiciste o qué encontraste."
        )
        cmd.extend(["-p", prompt_completo])
        prompt_mostrado = prompt_completo
        usa_stdin = False
    else:
        sys.stderr.write("Herramienta no soportada para delegar: «%s».\n" % herramienta)
        return 1

    # 10. Modo dry-run (el pedido se muestra recortado)
    if args.dry_run:
        mostrado = [c if c != prompt_mostrado else c[:200] + ("…" if len(c) > 200 else "") for c in cmd]
        print("Comando: %s" % " ".join(mostrado))
        return 0

    # 11. Ejecución con tope de tiempo (METODO_DELEGAR_TOPE, segundos; por defecto 1 hora) y vigilando .git
    try:
        tope = float(os.environ.get("METODO_DELEGAR_TOPE", "3600"))
    except ValueError:
        tope = 3600.0
    if herramienta.startswith("Antigravity"):
        return ejecutar_agy_aislado(cmd, repo_path, args, tope)
    antes = huella_git(repo_path)
    codigo = ejecutar(cmd, str(repo_path), pedido_texto if usa_stdin else None, tope)
    if huella_git(repo_path) != antes:
        sys.stderr.write(
            "ATENCIÓN: la herramienta modificó .git/config o los hooks de «%s». No corras git en ese repo ni confíes en él "
            "hasta revisarlos a mano.\n" % args.repo
        )
        return 71
    if codigo is None:
        sys.stderr.write("La herramienta no terminó en %d s y se cortó (con sus procesos hijos). Revisá el árbol con git status.\n" % int(tope))
        return 124
    if codigo != 0:
        sys.stderr.write("La herramienta terminó con error (código %d). Revisá el árbol con git status.\n" % codigo)
        return 70

    # 12. Al terminar adaptador que editó
    if not args.revisar:
        print("── Cambios (revisalos y corré los tests) ──")
        res_st = git(repo_path, "status", "--short", "--no-ahead-behind")
        if res_st and res_st.stdout:
            sys.stdout.write(res_st.stdout)
        res_df = git(repo_path, "diff", "--stat", "--no-ext-diff", "--no-textconv")
        if res_df and res_df.stdout:
            sys.stdout.write(res_df.stdout)
        print("Todo al día ✓")

    return 0


if __name__ == "__main__":
    sys.exit(main())
