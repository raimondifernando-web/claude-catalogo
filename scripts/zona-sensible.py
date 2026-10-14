#!/usr/bin/env python3
"""¿Este cambio toca lo que CORRE SOLO en la Mac del cliente (o los controles que lo cuidan)?

Disparador: encadenado — lo corre .github/workflows/zona-sensible.yml en cada PR a `main` (y cuando se le pone o
saca la etiqueta `ok-fernando`). También a mano: python3 scripts/zona-sensible.py --base origin/main --head HEAD

Decisión del dueño (2026-10-14): unir a `main` ya no necesita su OK; lo deciden las pruebas (check `controles`).
Su OK queda SOLO para lo que se ejecuta sin que nadie lo pida en la computadora del cliente: hooks, lo que esos
hooks llaman, servidores MCP, el instalador, los manifiestos que declaran hooks o fuentes, y los propios controles
(si un PR pudiera cambiar sus controles sin OK, los controles no servirían).

Salida: 0 = no toca la zona sensible · 10 = la toca (lista de archivos y motivo) · 2 = error.
Solo LEE objetos de git (`git show`, `git diff`): nunca ejecuta código del PR. Por eso puede correr con
`pull_request_target` (la versión de este script que corre es siempre la de `main`).
"""
import argparse
import fnmatch
import json
import re
import subprocess
import sys

# Rutas que siempre son zona sensible (patrones fnmatch sobre la ruta del repo).
FIJAS = [
    (".github/*", "los controles y robots del repositorio"),
    ("scripts/al-dia.sh", "el instalador del cliente"),
    ("scripts/estable-avanzar.py", "el robot que pasa cambios a `estable`"),
    ("scripts/verificar-metadatos.sh", "un control obligatorio"),
    ("scripts/controles.sh", "un control obligatorio"),
    ("scripts/zona-sensible.py", "un control obligatorio"),
    ("scripts/nombres-en-ci.py", "un control obligatorio"),
    ("scripts/disparadores-excepciones.txt", "afloja un control obligatorio"),
    ("scripts/tests/*", "las pruebas de los controles"),
    ("plugins/*/hooks/*", "un hook: corre solo en la Mac del cliente"),
    ("plugins/*/.mcp.json", "un servidor MCP: corre solo en la Mac del cliente"),
    ("plugins/*/.lsp.json", "un servidor de lenguaje: corre solo en la Mac del cliente"),
    ("plugins/*/settings.json", "ajustes que el plugin aplica solo"),
    ("plugins/*/bin/*", "programas que el plugin pone a mano de Claude"),
]
# Campos de los manifiestos que cambian en cada versión sin cambiar qué se ejecuta.
CAMPOS_INOCUOS = {"version", "description"}
RAIZ_PLUGIN = re.compile(r"\$\{?CLAUDE_PLUGIN_ROOT\}?/([A-Za-z0-9._/-]+)")
IMPORT = re.compile(r"^\s*(?:from|import)\s+([A-Za-z_]\w*)", re.M)


def git(*args, ok=(0,)):
    r = subprocess.run(["git", *args], capture_output=True, text=True)
    if r.returncode not in ok:
        raise SystemExit(f"zona-sensible: falló git {' '.join(args)}: {r.stderr.strip()}")
    return r


def mostrar(sha, ruta):
    r = git("show", f"{sha}:{ruta}", ok=(0, 128))
    return r.stdout if r.returncode == 0 else None


def archivos(sha):
    return set(git("ls-tree", "-r", "--name-only", sha).stdout.split())


def archivos_de_hooks(sha, todos):
    """hooks/hooks.json de cada plugin y los archivos de hooks que declare su plugin.json (campo `hooks`)."""
    out = {p for p in todos if fnmatch.fnmatch(p, "plugins/*/hooks/hooks.json")}
    for pj in (p for p in todos if fnmatch.fnmatch(p, "plugins/*/.claude-plugin/plugin.json")):
        plugin = "/".join(pj.split("/")[:2])
        try:
            decl = json.loads(mostrar(sha, pj) or "{}").get("hooks")
        except ValueError:
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


def sin_inocuos(obj):
    if isinstance(obj, dict):
        return {k: sin_inocuos(v) for k, v in obj.items() if k not in CAMPOS_INOCUOS}
    if isinstance(obj, list):
        return [sin_inocuos(x) for x in obj]
    return obj


def manifiesto_cambia_lo_que_corre(base, head, ruta):
    a, b = mostrar(base, ruta), mostrar(head, ruta)
    if a is None or b is None:
        return True  # nace o desaparece un manifiesto: siempre se mira
    try:
        return sin_inocuos(json.loads(a)) != sin_inocuos(json.loads(b))
    except ValueError:
        return True  # JSON roto: que lo mire una persona


def revisar(base, head):
    cambiados = [p for p in git("diff", "--name-only", f"{base}...{head}").stdout.splitlines() if p]
    reglas = list(FIJAS)
    for sha in (base, head):  # lo que los hooks ejecutaban antes Y después
        reglas += list(ejecutados_por_hooks(sha, archivos(sha)).items())
    hallazgos = {}
    for p in cambiados:
        if p.endswith(".claude-plugin/plugin.json") or p == ".claude-plugin/marketplace.json":
            if manifiesto_cambia_lo_que_corre(base, head, p):
                hallazgos[p] = "el manifiesto cambia algo más que versión o descripción (hooks, fuentes, comandos)"
            continue
        for patron, motivo in reglas:
            if p == patron or fnmatch.fnmatch(p, patron):
                hallazgos[p] = motivo
                break
    return cambiados, hallazgos


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--base", required=True)
    ap.add_argument("--head", required=True)
    a = ap.parse_args()
    cambiados, hallazgos = revisar(a.base, a.head)
    if not hallazgos:
        print(f"zona-sensible: no ✓ ({len(cambiados)} archivo(s); nada de lo que corre solo en la Mac del cliente)")
        return 0
    print(f"zona-sensible: SÍ — {len(hallazgos)} archivo(s) de lo que corre solo en la Mac del cliente:")
    for p in sorted(hallazgos):
        print(f"  · {p} — {hallazgos[p]}")
    return 10


if __name__ == "__main__":
    sys.exit(main())
