#!/usr/bin/env python3
"""Regla 24: en cada mensaje de la persona repite cómo llamarla. Solo lee la ficha personal de ESTA computadora
(<config de Claude>/CLAUDE.md, línea «Llamame:»); no escribe nada ni usa red.
Sin esa línea, o con varias personas en la computadora («Personas en esta computadora:»), no dice nada: nunca inventa un nombre.
Disparador: automático (hook UserPromptSubmit del plugin metodo, hooks/hooks.json)."""
import os
import re
import sys
from pathlib import Path

INI = "<!-- reglas-del-metodo:inicio -->"
FIN = "<!-- reglas-del-metodo:fin -->"
NOMBRE = re.compile(r"^\s*(?:[-*]\s*)?Llamame\s*:\s*(\S.*?)\s*$")
PERMITIDO = re.compile(r"[\w .'’-]{1,40}")
VARIOS = re.compile(r"^\s*(?:[-*]\s*)?Personas en esta computadora\s*:")


def nombre(ficha: Path) -> str:
    try:
        lineas = ficha.read_text(encoding="utf-8-sig").splitlines()
    except (OSError, UnicodeDecodeError):
        return ""
    if INI in lineas and FIN in lineas and lineas.index(INI) < lineas.index(FIN):
        lineas = lineas[:lineas.index(INI)] + lineas[lineas.index(FIN) + 1:]   # el ejemplo del bloque de reglas no cuenta
    lineas = [l.replace("*", "") for l in lineas]
    if any(VARIOS.match(l) for l in lineas):
        return ""
    for l in lineas:
        m = NOMBRE.match(l)
        if m and not m.group(1).startswith(("<", "…", "...")):
            n = m.group(1)
            return n if PERMITIDO.fullmatch(n) else ""   # un apodo normal; nada con forma de instrucción, comillas o largo
    return ""


def main() -> int:
    base = Path(os.environ.get("CLAUDE_CONFIG_DIR") or str(Path.home() / ".claude"))   # vacía = la de siempre, nunca la carpeta de trabajo
    n = nombre(base / "CLAUDE.md")
    if n:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")   # consola de Windows en cp1252
        print("Llamá al usuario «{}» por su nombre en esta respuesta (regla 24).".format(n))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
