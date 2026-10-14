#!/usr/bin/env python3
"""Control del servidor: ningún nombre de cliente o persona en el catálogo público.

Disparador: encadenado — lo corre scripts/controles.sh (check `controles` de cada PR a `main`).
Es el par del control local `nombres-prohibidos` (pre-push en la Mac del dueño): si alguien sube saltándose el local,
este lo frena en GitHub. La lista NUNCA está en el repo (es público): llega en el secreto de Actions
NOMBRES_PROHIBIDOS, una palabra o frase por línea. Compara sin mayúsculas y por palabra entera (las mismas reglas
que el control local). Nunca imprime la lista ni la palabra: solo archivo y línea (o «mensaje de commit <sha>»).

Uso: NOMBRES_PROHIBIDOS=... python3 scripts/nombres-en-ci.py [--rango <base>..<head>]
Salida: 0 = limpio · 1 = encontró algo · 2 = falta la lista o falló git (nunca se deja pasar en silencio).
"""
import argparse
import os
import re
import subprocess
import sys

MAX_BYTES = 2_000_000


def partes(lista, sep):
    return [sep.join(re.escape(p) for p in re.split(r"[-\s_]+", n)) for n in lista]


def patron(lista):
    return re.compile(r"(?<![A-Za-z0-9])(" + "|".join(partes(lista, r"[-\s_.]*")) + r")(?![A-Za-z0-9])", re.I)


def git(*args):
    r = subprocess.run(["git", *args], capture_output=True)
    if r.returncode != 0:
        print(f"nombres-en-ci: falló git {' '.join(args)}", file=sys.stderr)
        sys.exit(2)
    return r.stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rango", default="", help="base..head: también revisa los mensajes de esos commits")
    a = ap.parse_args()
    lista = sorted({l.split("#", 1)[0].strip().lower()
                    for l in os.environ.get("NOMBRES_PROHIBIDOS", "").splitlines() if l.split("#", 1)[0].strip()})
    if not lista:
        print("nombres-en-ci: falta el secreto NOMBRES_PROHIBIDOS (vacío): no se puede controlar, no se une")
        return 2
    rx = patron(lista)
    hallazgos = []
    for ruta in git("ls-files", "-z").decode("utf-8", "replace").split("\0"):
        if not ruta or not os.path.isfile(ruta) or os.path.getsize(ruta) > MAX_BYTES:
            continue
        datos = open(ruta, "rb").read()
        if b"\0" in datos[:8192]:
            continue  # binario
        for n, linea in enumerate(datos.decode("utf-8", "replace").splitlines(), 1):
            if rx.search(linea):
                hallazgos.append(f"{ruta}:{n}")
        if rx.search(ruta):
            hallazgos.append(f"{ruta} (en el nombre del archivo)")
    if a.rango:
        for bloque in git("log", "--format=%H%x00%B%x01", a.rango).decode("utf-8", "replace").split("\x01"):
            sha, _, cuerpo = bloque.strip().partition("\0")
            if sha and rx.search(cuerpo):
                hallazgos.append(f"mensaje de commit {sha[:12]}")
    if hallazgos:
        print(f"nombres-en-ci: {len(hallazgos)} aparición(es) de nombres que no pueden salir en el catálogo público:")
        for h in hallazgos[:50]:
            print(f"  · {h}")
        return 1
    print(f"nombres-en-ci: limpio ✓ ({len(lista)} nombres revisados)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
