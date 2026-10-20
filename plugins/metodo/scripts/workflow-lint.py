#!/usr/bin/env python3
"""workflow-lint: que un workflow de GitHub Actions nazca barato y silencioso (2026-10-19). Solo stdlib, sin red.

Disparador: automático — paso «Workflows baratos» del check `controles` de cada repo (corre en todo PR que agrega
o cambia un archivo de `.github/workflows/`); también lo corre `scripts/controles.sh` del catálogo. Manual:
`python3 workflow-lint.py --todo [--publico]` audita todos los workflows del repo parado (informe, no frena).

Por qué existe: un repo PRIVADO gasta minutos de Actions (Linux ×1, Windows ×2, macOS ×10) y el plan trae un
tope mensual (Pro = 3.000). El 2026-10-19 se llegó al 90 % por robots que arrancan por reloj o por n8n, sin
cancelar corridas viejas. Las 5 reglas (cada una se puede saltear con un motivo escrito en el propio archivo):

  concurrencia  el workflow declara `concurrency:` con `cancel-in-progress: true` (una corrida nueva cancela la vieja).
  so            repo privado: nada de macOS ni Windows (cuestan ×10 y ×2).
  cron          cada `cron:` lleva un comentario con el motivo y no corre más seguido que cada hora.
  timeout       todo job con `runs-on` trae `timeout-minutes` (un colgado no se come 360 min).
  push-pr       no se dispara por `push` y por `pull_request` a la vez sin filtrar ramas (corre dos veces por cambio).

Excepción legítima: una línea `# actions-ok: <regla> <motivo de al menos 5 letras>` en el archivo.
Ejemplo: `# actions-ok: concurrencia escribe en el repo: dos corridas no se pueden cancelar a la mitad`.

Salida: 0 sin infracciones, 1 con infracciones (con `--todo` siempre 0: es informe). Textos en criollo.
Nota de alcance (declarada): lee TEXTO, no entiende YAML; un workflow armado con anclas o `fromJSON` raro puede
engañarlo. Es una red de prevención, no una prueba formal.
"""
import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

REGLAS = ("concurrencia", "so", "cron", "timeout", "push-pr")
OK = re.compile(r"^[ \t]*#[ \t]*actions-ok:[ \t]*(\S+)[ \t]+(\S.{3,})$", re.M)
CRON = re.compile(r"^(?P<ind>[ \t]*)-?[ \t]*cron:[ \t]*['\"]?(?P<expr>[^'\"#\n]+?)['\"]?[ \t]*(?P<com>#.*)?$")


def _sin_comentario(linea):
    """Saca el comentario del final de una línea (` # …`), respetando que `#` dentro de comillas no cuenta."""
    comilla = None
    for i, c in enumerate(linea):
        if c in "'\"":
            comilla = None if comilla == c else (comilla or c)
        elif c == "#" and comilla is None and (i == 0 or linea[i - 1] in " \t"):
            return linea[:i].rstrip()
    return linea


def excepciones(texto):
    return {m.group(1).lower() for m in OK.finditer(texto)}


def _campo(campo, minimo, maximo):
    vals = set()
    for parte in campo.split(","):
        paso = 1
        if "/" in parte:
            parte, p = parte.split("/", 1)
            paso = max(int(p), 1)
        if parte in ("*", ""):
            a, b = minimo, maximo
        elif "-" in parte:
            a, b = (int(x) for x in parte.split("-", 1))
        else:
            a = int(parte)
            b = maximo if paso > 1 else a
        vals.update(range(a, b + 1, paso))
    return vals


def corridas_por_dia(expr):
    """Cuántas veces por día arranca una expresión cron de 5 campos (ignora día de semana/mes: cuenta lo peor)."""
    campos = expr.split()
    if len(campos) != 5:
        return None
    try:
        return len(_campo(campos[0], 0, 59)) * len(_campo(campos[1], 0, 23))
    except ValueError:
        return None


def bloque_on(texto):
    """Devuelve (líneas del bloque `on:`) o None. Soporta `on:`, `"on":` y la forma corta `on: [a, b]`."""
    lineas = texto.splitlines()
    for i, l in enumerate(lineas):
        if re.match(r"""^["']?on["']?:""", l):
            resto = _sin_comentario(l.split(":", 1)[1]).strip()
            if resto:
                return [_sin_comentario(l)]
            fin = i + 1
            while fin < len(lineas) and (not lineas[fin].strip() or lineas[fin][0] in " \t#"):
                fin += 1
            return lineas[i:fin]
    return None


def revisar(texto, privado=True):
    """Lista de (regla, mensaje) con las infracciones de un workflow, ya sin las excepciones declaradas."""
    ok = excepciones(texto)
    malas = []

    def mala(regla, msg):
        if regla not in ok:
            malas.append((regla, msg))

    # concurrencia
    if not re.search(r"^[ \t]*concurrency:", texto, re.M) or \
            not re.search(r"cancel-in-progress:[ \t]*(?:true|\$\{\{.+\}\})", texto, re.I):
        mala("concurrencia", "no cancela la corrida vieja: agregá `concurrency:` con `group:` y `cancel-in-progress: true` "
             "(si escribe en algo y no se puede cortar a la mitad, `# actions-ok: concurrencia <por qué>`)")
    # so
    if privado:
        for l in texto.splitlines():
            l = _sin_comentario(l)
            if re.search(r"runs-on|\bos\b|\brunners?\b|^\s*-\s*['\"]?(?:macos|windows)-", l, re.I):
                m = re.search(r"(?i)\b((?:macos|windows)-[\w.]+)\b", l)
                if m:
                    mala("so", f"usa {m.group(1)} en un repo privado (macOS gasta ×10, Windows ×2): dejá solo ubuntu "
                         "(o `# actions-ok: so <por qué hace falta>`)")
                    break
    # cron
    lineas = texto.splitlines()
    for i, l in enumerate(lineas):
        m = CRON.match(l)
        if not m or "cron:" not in l or l.lstrip().startswith("#"):
            continue
        previa = lineas[i - 1].strip() if i else ""
        motivo = (m.group("com") or "").strip("# ").strip()
        if len(motivo) < 3 and not (previa.startswith("#") and len(previa.strip("# ")) >= 5):
            mala("cron", f"cron `{m.group('expr').strip()}` sin motivo: escribí al lado `# <para qué corre y por qué a esa hora>`")
        expr = m.group("expr").strip()
        n = corridas_por_dia(expr)
        por_hora = len(_campo(expr.split()[0], 0, 59)) if n else 0   # veces por hora dentro de cada hora activa
        if (n and n > 24) or por_hora > 1:
            mala("cron", f"cron `{m.group('expr').strip()}` corre {n} veces por día (más seguido que cada hora): "
                 "bajalo o declará `# actions-ok: cron <por qué>`")
    # timeout (a nivel de job: misma sangría que `runs-on`; un timeout de un paso no cuenta)
    sang = [len(m.group(1)) for m in re.finditer(r"^([ \t]+)runs-on:", texto, re.M)]
    if sang:
        n_to = len([1 for m in re.finditer(r"^([ \t]+)timeout-minutes:", texto, re.M) if len(m.group(1)) == sang[0]])
        if len(sang) > n_to:
            mala("timeout", f"{len(sang) - n_to} job(s) sin `timeout-minutes` (un colgado puede gastar hasta 360 min)")
    # push + pull_request
    on = bloque_on(texto)
    if on:
        bloque = "\n".join(on)
        corto = re.match(r"""^["']?on["']?:\s*\[(.*)\]""", on[0]) if len(on) == 1 else None
        if len(on) == 1 and not corto:  # `on: push` (un solo evento)
            corto = re.match(r"""^["']?on["']?:\s*(\w+)\s*$""", on[0])
        bloque = "\n".join(_sin_comentario(x) for x in on)
        eventos = {e.strip().strip("'\"") for e in corto.group(1).split(",")} if corto else \
            set(re.findall(r"(?m)^[ \t]{1,4}([a-z_]+):", bloque)) | set(re.findall(r"(?m)^[ \t]+-[ \t]*([a-z_]+)[ \t]*$", bloque))
        if "push" in eventos and ({"pull_request", "pull_request_target"} & eventos):
            filtrado = False
            for k, l in enumerate(on):
                m = re.match(r"^([ \t]+)push:", l)
                if m:
                    sangria = len(m.group(1))
                    sub = []
                    for l2 in on[k + 1:]:
                        if l2.strip() and len(l2) - len(l2.lstrip()) <= sangria:
                            break
                        sub.append(l2)
                    sub_txt = "\n".join(_sin_comentario(x) for x in sub)
                    filtrado = bool(re.search(r"(?m)^\s*(?:branches|tags):", sub_txt)) and \
                        not re.search(r"""(?m)^\s*branches:\s*\[?\s*['"]?\*""", sub_txt)
            if corto or not filtrado:
                mala("push-pr", "corre por `push` y por `pull_request` a la vez: cada cambio corre dos veces. Dejá solo "
                     "`pull_request` (y `push` solo a `main`: `branches: [main]`)")
    return malas


def archivos_a_mirar(args):
    if args.todo:
        return sorted(Path(".github/workflows").glob("*.y*ml"))
    if args.base or args.head:
        ref = re.compile(r"^[0-9A-Za-z][0-9A-Za-z_./-]*$")
        if not (args.base and args.head and ref.match(args.base) and ref.match(args.head)):
            print("::error::workflow-lint: faltan BASE y HEAD (o no son referencias de git válidas)")
            sys.exit(1)
        r = subprocess.run(["git", "diff", "--name-only", f"--diff-filter={'A' if args.solo_nuevos else 'AM'}", "-z",
                            f"{args.base}...{args.head}", "--", ".github/workflows"], capture_output=True, text=True)
        if r.returncode != 0:
            print("::error::workflow-lint: no pude comparar BASE...HEAD (¿falta historia? el checkout necesita fetch-depth: 0)")
            sys.exit(1)
        return [Path(p) for p in r.stdout.split("\0") if p.endswith((".yml", ".yaml"))]
    return [Path(p) for p in args.archivos]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("archivos", nargs="*")
    ap.add_argument("--base")
    ap.add_argument("--head")
    ap.add_argument("--todo", action="store_true", help="audita todo .github/workflows (informe, no frena)")
    ap.add_argument("--solo-nuevos", action="store_true", help="con --base/--head: mira solo los workflows AGREGADOS (no los modificados)")
    ap.add_argument("--publico", action="store_true", help="repo público: no gasta minutos, se salta la regla `so`")
    args = ap.parse_args(argv)
    if not (args.todo or args.archivos or args.base or args.head):  # modo check de GitHub: BASE y HEAD llegan por entorno
        args.base, args.head = os.environ.get("BASE"), os.environ.get("HEAD")
    privado = not args.publico and os.environ.get("REPO_PRIVADO", "true").lower() != "false"
    total = 0
    for ruta in archivos_a_mirar(args):
        if not ruta.is_file():
            continue
        for regla, msg in revisar(ruta.read_text(encoding="utf-8", errors="replace"), privado):
            total += 1
            print(f"::error file={ruta}::[workflow-lint · {regla}] {msg}")
    if total:
        print(f"workflow-lint: {total} infracción(es). Reglas y excepciones: ver el encabezado de workflow-lint.py "
              "o el Mandamiento XXX.")
    else:
        print("workflow-lint: sin infracciones.")
    return 0 if args.todo else (1 if total else 0)


if __name__ == "__main__":
    sys.exit(main())
