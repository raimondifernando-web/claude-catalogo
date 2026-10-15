#!/usr/bin/env python3
"""¿Este cambio toca lo que CORRE SOLO en la Mac del cliente (o los controles que lo cuidan)?

Disparador: encadenado — lo corre .github/workflows/zona-sensible.yml en cada PR a `main` (y cuando se le pone o
saca una etiqueta). También a mano: python3 scripts/zona-sensible.py --base origin/main --head HEAD

Decisión del dueño (2026-10-14): unir a `main` ya no necesita su OK; lo deciden las pruebas (check `controles`).
Su OK queda SOLO para lo que se ejecuta sin que nadie lo pida en la computadora del cliente: hooks, lo que esos
hooks llaman, servidores MCP, el instalador, los manifiestos que cambian qué se ejecuta, skills que se dan permisos
o hooks propios, y los propios controles (si un PR pudiera cambiar sus controles sin OK, no servirían).

Salida: 0 = no toca la zona sensible · 10 = la toca (lista de archivos y motivo) · 2 = error (nunca pasa en silencio).
Solo LEE objetos de git (`git show`, `git diff`): nunca ejecuta código del PR. Por eso puede correr con
`pull_request_target` (la versión de este script que corre es siempre la de `main`).
Nombres de archivo: siempre con `-z` y sin detección de renombres (un renombre cuenta como borrar + crear, así un
archivo sensible movido a otra carpeta igual se ve).
"""
import argparse
import fnmatch
import json
import re
import subprocess
import sys

# Rutas que siempre son zona sensible (patrones fnmatch sobre la ruta del repo; «*» cruza carpetas).
FIJAS = [
    (".github/*", "los controles y robots del repositorio"),
    ("scripts/al-dia.sh", "el instalador del cliente"),
    ("scripts/estable-avanzar.py", "el robot que pasa cambios a `estable`"),
    ("scripts/radar-fuentes.py", "lo corre un robot con permiso de escritura"),
    ("scripts/verificar-metadatos.sh", "un control obligatorio"),
    ("scripts/controles.sh", "un control obligatorio"),
    ("scripts/zona-sensible.py", "un control obligatorio"),
    ("scripts/nombres-en-ci.py", "un control obligatorio"),
    ("scripts/disparadores-excepciones.txt", "afloja un control obligatorio"),
    ("scripts/tests/*", "las pruebas de los controles"),
    ("plugins/*/scripts/tests/*", "pruebas que corre el control obligatorio"),
    ("plugins/*/scripts/*/tests/*", "pruebas que corre el control obligatorio"),
    ("plugins/*/scripts/unir-a-main", "el control de unión de los repos del cliente"),
    ("plugins/*/scripts/nombres-prohibidos", "instala un hook de git en la Mac del cliente"),
    ("plugins/*/hooks/*", "un hook: corre solo en la Mac del cliente"),
    ("plugins/*/.mcp.json", "un servidor MCP: corre solo en la Mac del cliente"),
    ("plugins/*/.lsp.json", "un servidor de lenguaje: corre solo en la Mac del cliente"),
    ("plugins/*/settings.json", "ajustes que el plugin aplica solo"),
    ("plugins/*/bin/*", "programas que el plugin pone a mano de Claude"),
    # Lo que corre solo al abrir una carpeta, al instalar o al commitear, en la raíz o en cualquier subcarpeta
    # (2026-10-15, medios 3 y 4 de la revisión de metodo 0.40.1). Cada patrón va en las dos formas: en la raíz y con `*/`.
    (".mcp.json", "un servidor MCP: corre solo"), ("*/.mcp.json", "un servidor MCP: corre solo"),
    (".claude/settings*.json", "ajustes de Claude (permisos, hooks)"),
    ("*/.claude/settings*.json", "ajustes de Claude (permisos, hooks)"),
    (".claude/hooks/*", "un hook"), ("*/.claude/hooks/*", "un hook"),
    (".claude/commands/*", "un comando de Claude (puede ejecutar programas)"),
    ("*/.claude/commands/*", "un comando de Claude (puede ejecutar programas)"),
    (".claude/agents/*", "un agente de Claude"), ("*/.claude/agents/*", "un agente de Claude"),
    (".claude/rules/*", "reglas que Claude sigue"), ("*/.claude/rules/*", "reglas que Claude sigue"),
    (".husky/*", "un hook de git"), ("*/.husky/*", "un hook de git"),
    (".githooks/*", "un hook de git"), ("*/.githooks/*", "un hook de git"),
    (".git-hooks/*", "un hook de git"), ("*/.git-hooks/*", "un hook de git"),
    (".pre-commit-config.yaml", "un hook de git"), ("*/.pre-commit-config.yaml", "un hook de git"),
    (".envrc", "se ejecuta solo al entrar a la carpeta (direnv)"),
    ("*/.envrc", "se ejecuta solo al entrar a la carpeta (direnv)"),
    (".vscode/tasks.json", "una tarea del editor que puede correr al abrir la carpeta"),
    ("*/.vscode/tasks.json", "una tarea del editor que puede correr al abrir la carpeta"),
    (".vscode/settings.json", "ajustes del editor (pueden correr programas)"),
    ("*/.vscode/settings.json", "ajustes del editor (pueden correr programas)"),
    (".devcontainer/*", "se ejecuta al abrir la carpeta en un contenedor"),
    ("*/.devcontainer/*", "se ejecuta al abrir la carpeta en un contenedor"),
    ("package.json", "scripts de npm (postinstall, prepare) que corren al instalar"),
    ("*/package.json", "scripts de npm (postinstall, prepare) que corren al instalar"),
    (".gitmodules", "trae código de otro repositorio"), (".gitattributes", "cambia cómo git trata los archivos"),
    ("*/.gitattributes", "cambia cómo git trata los archivos"),
]
# Archivos que declaran qué comandos corren solos fuera de un plugin: se leen en base y en head para ver a qué scripts
# del repo apuntan (esos scripts también son zona sensible).
DECLARAN_FUERA_DE_PLUGINS = ("settings.json", "settings.local.json", ".mcp.json")
# Campos de primer nivel de los manifiestos que cambian en cada versión sin cambiar qué se ejecuta.
CAMPOS_INOCUOS = {"version", "description"}
RAIZ_PLUGIN = re.compile(r"\$\{?CLAUDE_PLUGIN_ROOT\}?/([A-Za-z0-9._/-]+)")
IMPORT = re.compile(r"^\s*(?:from|import)\s+([A-Za-z_]\w*)", re.M)
# Una skill, comando o agente que se da hooks, servidores, permisos o ejecuta algo al cargarse.
PODERES = re.compile(r"^\+\s*(hooks|mcpServers|allowed-tools|allowedTools|permissionMode|disallowedTools)\s*:"
                     r"|^\+.*!`", re.M)
CARPETAS_CON_PODERES = ("plugins/*/skills/*", "plugins/*/commands/*", "plugins/*/agents/*")


def git(*args, ok=(0,)):
    r = subprocess.run(["git", *args], capture_output=True, text=True, errors="surrogateescape")
    if r.returncode not in ok:
        print(f"zona-sensible: falló git {' '.join(args)}: {r.stderr.strip()}")
        raise SystemExit(2)
    return r


def existe(sha, ruta):
    return git("cat-file", "-e", f"{sha}:{ruta}", ok=(0, 1, 128)).returncode == 0


def mostrar(sha, ruta):
    """Contenido de `ruta` en `sha`, o None si la ruta no existe. Cualquier otro error de git frena (exit 2)."""
    if not existe(sha, ruta):
        return None
    return git("show", f"{sha}:{ruta}").stdout


def archivos(sha):
    return {p for p in git("ls-tree", "-r", "-z", "--name-only", sha).stdout.split("\0") if p}


def archivos_de_hooks(sha, todos):
    """hooks/hooks.json de cada plugin y los archivos de hooks que declare su plugin.json (campo `hooks`)."""
    out = {p for p in todos if fnmatch.fnmatch(p, "plugins/*/hooks/hooks.json")}
    for pj in (p for p in todos if fnmatch.fnmatch(p, "plugins/*/.claude-plugin/plugin.json")):
        plugin = "/".join(pj.split("/")[:2])
        try:
            decl = json.loads(mostrar(sha, pj) or "{}").get("hooks")
        except (ValueError, AttributeError):
            continue
        for d in ([decl] if isinstance(decl, str) else decl if isinstance(decl, list) else []):
            if isinstance(d, str):
                cand = f"{plugin}/{d.lstrip('./')}"
                if cand in todos:
                    out.add(cand)
    return sorted(out)


def ejecutados_por_hooks(sha, todos):
    """Archivos que los hooks de `sha` ejecutan, más lo que esos archivos llaman de su misma carpeta (un nivel):
    cualquier archivo hermano cuyo nombre aparezca en el código (con o sin extensión, p. ej. `codex-cupo`) y los
    módulos que importa."""
    out = {}
    for hj in archivos_de_hooks(sha, todos):
        plugin = "/".join(hj.split("/")[:2])
        out[hj] = "declara hooks: corre solo en la Mac del cliente"
        texto = mostrar(sha, hj) or ""
        for rel in RAIZ_PLUGIN.findall(texto):
            ruta = f"{plugin}/{rel.rstrip('/')}"
            carpeta = ruta.rsplit("/", 1)[0]
            if carpeta.count("/") >= 3:  # plugins/<p>/scripts/<sub>/x: la subcarpeta entera es del hook
                out[carpeta + "/*"] = f"lo ejecuta un hook ({hj})"
            out[ruta] = f"lo ejecuta un hook ({hj})"
            fuente = mostrar(sha, ruta) or ""
            palabras = set(re.findall(r"[A-Za-z0-9_.-]+", fuente))
            mods = {m + ".py" for m in IMPORT.findall(fuente)} if ruta.endswith(".py") else set()
            for cand in todos:
                if cand == ruta or cand.rsplit("/", 1)[0] != carpeta:
                    continue
                nombre = cand.rsplit("/", 1)[1]
                if nombre in palabras or nombre in mods:
                    out[cand] = f"lo usa {ruta}, que corre en un hook"
    return out


def ejecutados_por_ajustes(sha, todos):
    """Scripts del repo a los que apuntan los comandos (`command`, y `args` de los servidores MCP) de
    `.claude/settings*.json` y `.mcp.json` fuera de los plugins: corren solos en la Mac de quien abre la carpeta."""
    out = {}
    for decl in sorted(todos):
        nombre = decl.rsplit("/", 1)[-1]
        if nombre not in DECLARAN_FUERA_DE_PLUGINS or decl.startswith("plugins/"):
            continue
        if nombre != ".mcp.json" and not (decl.startswith(".claude/") or "/.claude/" in decl):
            continue
        try:
            datos = json.loads(mostrar(sha, decl) or "{}")
        except ValueError:
            continue
        comandos = []

        def recorrer(x):
            if isinstance(x, dict):
                for k, v in x.items():
                    if k == "command" and isinstance(v, str):
                        comandos.append(v)
                    elif k == "args" and isinstance(v, list):
                        comandos.extend(a for a in v if isinstance(a, str))
                    else:
                        recorrer(v)
            elif isinstance(x, list):
                for v in x:
                    recorrer(v)
        recorrer(datos)
        # carpeta del proyecto a la que son relativos los comandos: la que contiene a `.claude/` o al `.mcp.json`
        base = decl[:-len(".mcp.json")] if nombre == ".mcp.json" else decl.rsplit(".claude/", 1)[0]
        for c in comandos:
            for tok in re.findall(r"[A-Za-z0-9._/${}~-]+", c.replace('"', "").replace("'", "")):
                t = re.sub(r"^(\$\{?CLAUDE_PROJECT_DIR\}?|\.)/", "", tok)
                for cand in (t, base + t):
                    if cand in todos:
                        out[cand] = f"lo ejecuta solo un comando declarado en {decl}"
                        carpeta = cand.rsplit("/", 1)[0] if "/" in cand else ""
                        if carpeta and carpeta not in ("plugins",):
                            out[carpeta + "/*"] = f"lo ejecuta solo un comando declarado en {decl}"
    return out


def sin_inocuos(obj, es_marketplace):
    """Saca versión y descripción SOLO de primer nivel (y de cada plugin del marketplace y de su `metadata`):
    un servidor MCP o una fuente que se llame `version` adentro de otra clave sigue contando."""
    if not isinstance(obj, dict):
        return obj
    limpio = {k: v for k, v in obj.items() if k not in CAMPOS_INOCUOS}
    if es_marketplace:
        if isinstance(limpio.get("plugins"), list):
            limpio["plugins"] = [{k: v for k, v in p.items() if k not in CAMPOS_INOCUOS} if isinstance(p, dict) else p
                                 for p in limpio["plugins"]]
        if isinstance(limpio.get("metadata"), dict):
            limpio["metadata"] = {k: v for k, v in limpio["metadata"].items() if k not in CAMPOS_INOCUOS}
    return limpio


def manifiesto_cambia_lo_que_corre(base, head, ruta):
    a, b = mostrar(base, ruta), mostrar(head, ruta)
    if a is None or b is None:
        return True  # nace o desaparece un manifiesto: siempre se mira
    try:
        mk = ruta.endswith("marketplace.json")
        return sin_inocuos(json.loads(a), mk) != sin_inocuos(json.loads(b), mk)
    except ValueError:
        return True  # JSON roto: que lo mire una persona


def con_poderes(base, head):
    """Skills, comandos o agentes cuyas líneas AGREGADAS les dan hooks, servidores, permisos o ejecución al cargar."""
    out = {}
    diff = git("diff", "-U0", "--no-renames", "--no-color", f"{base}...{head}", "--", *CARPETAS_CON_PODERES).stdout
    actual = None
    for linea in diff.splitlines():
        if linea.startswith("+++ "):
            actual = linea[6:] if linea.startswith("+++ b/") else None
        elif actual and PODERES.match(linea):
            out[actual] = "una skill, comando o agente que se da hooks, servidores, permisos o ejecuta algo al cargarse"
    return out


def revisar(base, head):
    cambiados = [p for p in git("diff", "--name-only", "-z", "--no-renames", f"{base}...{head}").stdout.split("\0") if p]
    reglas = list(FIJAS)
    for sha in (base, head):  # lo que los hooks ejecutaban antes Y después
        reglas += list(ejecutados_por_hooks(sha, archivos(sha)).items())
        reglas += list(ejecutados_por_ajustes(sha, archivos(sha)).items())
    hallazgos = {}
    for p in cambiados:
        if not re.fullmatch(r"[A-Za-z0-9._/@+ -]+", p):
            hallazgos[p] = "nombre de archivo con caracteres raros: que lo mire una persona"
            continue
        if p.endswith(".claude-plugin/plugin.json") or p.endswith(".claude-plugin/marketplace.json"):
            if manifiesto_cambia_lo_que_corre(base, head, p):
                hallazgos[p] = "el manifiesto cambia algo más que versión o descripción (hooks, fuentes, comandos)"
            continue
        for patron, motivo in reglas:
            if p == patron or fnmatch.fnmatch(p, patron):
                hallazgos[p] = motivo
                break
    hallazgos.update({p: m for p, m in con_poderes(base, head).items() if p not in hallazgos})
    return cambiados, hallazgos


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--base", required=True)
    ap.add_argument("--head", required=True)
    a = ap.parse_args()
    for sha in (a.base, a.head):
        git("rev-parse", "--verify", "--quiet", f"{sha}^{{commit}}")
    cambiados, hallazgos = revisar(a.base, a.head)
    if not hallazgos:
        print(f"zona-sensible: no ✓ ({len(cambiados)} archivo(s); nada de lo que corre solo en la Mac del cliente)")
        return 0
    print(f"zona-sensible: SÍ — {len(hallazgos)} archivo(s) de lo que corre solo en la Mac del cliente:")
    for p in sorted(hallazgos):
        print(f"  · {p!r} — {hallazgos[p]}" if not re.fullmatch(r"[A-Za-z0-9._/@+ -]+", p)
              else f"  · {p} — {hallazgos[p]}")
    return 10


if __name__ == "__main__":
    sys.exit(main())
