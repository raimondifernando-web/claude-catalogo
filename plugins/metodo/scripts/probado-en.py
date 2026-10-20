#!/usr/bin/env python3
"""probado-en: una automatización de GitHub se prueba ANTES en un repo PRIVADO real, de punta a punta (regla 25). 2026-10-19.

Disparador: automático — paso «Probado en un repo privado» del check `controles` (todo PR) y `scripts/controles.sh` del
catálogo. Solo stdlib. Manual: `PR_BODY="…" python3 probado-en.py --base <sha> --head <sha>`.

Por qué existe: el control `zona-sensible` se instaló en 12 repos privados habiéndolo probado solo en el catálogo
PÚBLICO (allá un repo se lee sin credencial; en uno privado falló con «could not read Username»), y la prueba final del
script dejaba restos (rama, PR, etiqueta) que chocaban con la corrida siguiente. Un repo público y las pruebas locales
NO reproducen lo que pasa en uno privado.

Qué exige: si el PR toca (a) workflows en un repo PÚBLICO, (b) `.github/rulesets/`, (c) plantillas de `controles-repo/`
o (d) un script de instalación masiva (`activar-*`, `instalar-*`), la descripción del PR trae una línea
`Probado-en: <repo privado real> (<qué se corrió, de punta a punta>)`. Es una declaración visible, como `Revisado-por`:
no demuestra la prueba, pero obliga a decir dónde se hizo, y quien aprueba la ve. En un repo privado que es el propio
destino no hace falta: el PR corre ahí mismo.
La prueba de punta a punta: sin restos (limpia lo que crea aunque falle), se puede repetir, y si el repo de prueba
falla NO se sigue con los demás.

Salida: 0 sin exigencia o con la línea; 1 si falta. Textos en criollo.
"""
import os
import re
import subprocess
import sys

NO_VALE = {"ninguno", "no", "n/a", "-", "nada", "nadie", "<repo>", "publico", "público", "catalogo", "catálogo"}
INSTALADOR = re.compile(r"(^|/)(activar|instalar)[-_\w.]*\.(py|sh)$")


def exigencia(archivos, repo_privado):
    """Primera razón por la que este PR necesita `Probado-en`, o None."""
    for a in archivos:
        if a.startswith(".github/rulesets/"):
            return f"toca un ruleset ({a})"
        if "/controles-repo/" in "/" + a:
            return f"toca las plantillas de controles ({a})"
        if INSTALADOR.search(a):
            return f"toca un script de instalación masiva ({a})"
        if a.startswith(".github/workflows/") and a.endswith((".yml", ".yaml")) and not repo_privado:
            return f"toca un workflow en un repo público ({a}), donde no se reproduce lo que pasa en uno privado"
    return None


def declaracion(cuerpo):
    m = re.search(r"^Probado-en:[ \t]*(\S.*)$", cuerpo or "", re.M)
    if not m:
        return None
    v = m.group(1).strip()
    return None if v.lower() in NO_VALE or len(v) < 10 else v


def main():
    args = sys.argv[1:]
    base = args[args.index("--base") + 1] if "--base" in args else os.environ.get("BASE", "")
    head = args[args.index("--head") + 1] if "--head" in args else os.environ.get("HEAD", "")
    ref = re.compile(r"^[0-9A-Za-z][0-9A-Za-z_./-]*$")
    if not (ref.match(base) and ref.match(head)):
        print("::error::probado-en: faltan BASE y HEAD válidos")
        return 1
    if os.environ.get("PR_AUTOR", "").endswith("[bot]"):
        print("PR de un robot: no se exige Probado-en")
        return 0
    r = subprocess.run(["git", "diff", "--name-only", "-z", f"{base}...{head}"], capture_output=True, text=True)
    if r.returncode != 0:
        print("::error::probado-en: no pude comparar BASE...HEAD (el checkout necesita fetch-depth: 0)")
        return 1
    privado = os.environ.get("REPO_PRIVADO", "true").lower() != "false"
    razon = exigencia([a for a in r.stdout.split("\0") if a], privado)
    if not razon:
        print("probado-en: este PR no toca automatizaciones de GitHub que pidan prueba previa")
        return 0
    v = declaracion(os.environ.get("PR_BODY", ""))
    if v:
        print("Probado-en declarado:", v[:100])
        return 0
    print(f"::error::este PR {razon}. Probalo ANTES de punta a punta en un repo PRIVADO real (que no deje restos y que se "
          "pueda repetir) y agregá a la descripción una línea «Probado-en: <repo privado> (<qué corriste>)». "
          "Un repo público o las pruebas locales no alcanzan.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
