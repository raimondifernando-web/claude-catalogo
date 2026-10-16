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
VARIOS = re.compile(r"^\s*(?:[-*]\s*)?Personas en esta computadora\s*:")


def nombre(ficha: Path) -> str:
    try:
        lineas = ficha.read_text(encoding="utf-8").splitlines()
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
            return m.group(1)
    return ""


def main() -> int:
    base = Path(os.environ.get("CLAUDE_CONFIG_DIR", str(Path.home() / ".claude")))
    n = nombre(base / "CLAUDE.md")
    if n:
        print("Llamá al usuario «{}» por su nombre en esta respuesta (regla 24).".format(n))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
