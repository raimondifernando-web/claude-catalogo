#!/usr/bin/env python3
"""Control del servidor: ningún nombre de cliente o persona en el catálogo público.

Disparador: encadenado — lo corre .github/workflows/zona-sensible.yml (check `zona-sensible`) en cada PR a `main`,
con la versión de `main` de este archivo y SIN ejecutar código del PR: lee el PR con `git ls-tree` / `git show`.
Así el secreto nunca está en un proceso donde corre código del PR.
Es el par del control local `nombres-prohibidos` (pre-push en la Mac del dueño). La lista NUNCA está en el repo (es
público): llega en el secreto de Actions NOMBRES_PROHIBIDOS, una palabra o frase por línea. Compara sin mayúsculas y
por palabra entera (las mismas reglas que el control local). Nunca imprime la lista ni la palabra: solo archivo y
línea (o «mensaje de commit <sha>», «título o descripción del PR»).

Uso: NOMBRES_PROHIBIDOS=... python3 scripts/nombres-en-ci.py --arbol <sha> [--rango <base>..<head>]
     (sin --arbol revisa la copia de trabajo, para usarlo a mano). PR_TEXTO (opcional): título + descripción del PR.
Salida: 0 = limpio · 1 = encontró algo · 2 = falta la lista o falló git (nunca se deja pasar en silencio).
"""
import argparse
import os
import re
import subprocess
import sys

MAX_BYTES = 5_000_000


def partes(lista, sep):
    return [sep.join(re.escape(p) for p in re.split(r"[-\s_]+", n)) for n in lista]


def patron(lista):
    return re.compile(r"(?<![A-Za-z0-9])(" + "|".join(partes(lista, r"[-\s_.]*")) + r")(?![A-Za-z0-9])", re.I)


def git(*args):
    r = subprocess.run(["git", *args], capture_output=True)
    if r.returncode != 0:
        print(f"nombres-en-ci: falló git {' '.join(args)}")
        sys.exit(2)
    return r.stdout


def textos(datos):
    """El archivo leído como UTF-8 y, si parece UTF-16 (tiene NUL), también como UTF-16."""
    yield datos.decode("utf-8", "replace")
    if b"\0" in datos[:8192]:
        for cod in ("utf-16", "utf-16-le", "utf-16-be"):
            try:
                yield datos.decode(cod)
            except UnicodeDecodeError:
                pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arbol", default="", help="sha a revisar sin sacarlo a disco (lo usa el robot)")
    ap.add_argument("--rango", default="", help="base..head: también revisa los mensajes de esos commits")
    a = ap.parse_args()
    lista = sorted({l.split("#", 1)[0].strip().lower()
                    for l in os.environ.get("NOMBRES_PROHIBIDOS", "").splitlines() if l.split("#", 1)[0].strip()})
    if not lista:
        print("nombres-en-ci: falta el secreto NOMBRES_PROHIBIDOS (vacío): no se puede controlar, no se une")
        return 2
    rx = patron(lista)
    hallazgos = []
    if a.arbol:
        rutas = [p for p in git("ls-tree", "-r", "-z", "--name-only", a.arbol).split(b"\0") if p]
    else:
        rutas = [p for p in git("ls-files", "-z").split(b"\0") if p]
    for cruda in rutas:
        ruta = cruda.decode("utf-8", "replace")
        if rx.search(ruta):  # primero el nombre: un PDF o una imagen con el nombre del cliente también cuenta
            hallazgos.append(f"{ruta} (en el nombre del archivo)")
        if a.arbol:
            tam = int(git("cat-file", "-s", f"{a.arbol}:{ruta}").strip() or 0)
            if tam > MAX_BYTES:
                continue
            datos = git("cat-file", "blob", f"{a.arbol}:{ruta}")
        else:
            if not os.path.isfile(cruda) or os.path.getsize(cruda) > MAX_BYTES:
                continue
            datos = open(cruda, "rb").read()
        for texto in textos(datos):
            vistos = [f"{ruta}:{n}" for n, linea in enumerate(texto.splitlines(), 1) if rx.search(linea)]
            if vistos:
                hallazgos += vistos
                break
    if a.rango:
        for bloque in git("log", "--format=%H%x00%B%x01", a.rango).decode("utf-8", "replace").split("\x01"):
            sha, _, cuerpo = bloque.strip().partition("\0")
            if sha and rx.search(cuerpo):
                hallazgos.append(f"mensaje de commit {sha[:12]}")
    if rx.search(os.environ.get("PR_TEXTO", "")):
        hallazgos.append("título o descripción del PR (al unir con squash pasa al mensaje en main)")
    if hallazgos:
        print(f"nombres-en-ci: {len(hallazgos)} aparición(es) de nombres que no pueden salir en el catálogo público:")
        for h in hallazgos[:50]:
            print(f"  · {h}")
        return 1
    print(f"nombres-en-ci: limpio ✓ ({len(lista)} nombres revisados)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
