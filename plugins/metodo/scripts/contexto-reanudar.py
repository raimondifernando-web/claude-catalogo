#!/usr/bin/env python3
"""Hook SessionStart: le da a la sesión nueva el hilo de la anterior, sin que nadie pegue nada.

Lee el REANUDAR.md que dejó /metodo:cerrar (en la raíz de la carpeta de trabajo, o en .claude/prompts/) y muestra la
PARTE B: fecha del cierre, «De qué veníamos hablando» y pendientes. No muestra el contrato (PARTE A).
Si el archivo no está o no tiene PARTE B, no imprime nada. Solo lee; nunca escribe ni hace fallar la sesión.
Entrada: el JSON que manda Claude Code por stdin (cwd, source). Solo actúa al abrir (startup) o tras compactar.
"""
import datetime
import json
import os
import re
import sys

TOPE_LINEAS = 40
DIAS_VIEJO = 3


def main():
    try:
        datos = json.loads(sys.stdin.read() or "{}")
        if not isinstance(datos, dict):
            datos = {}
    except Exception:
        datos = {}
    cwd = datos.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    fuente = datos.get("source", "startup")
    if fuente not in ("startup", "compact"):
        return
    ruta = next((p for p in (os.path.join(cwd, "REANUDAR.md"), os.path.join(cwd, ".claude", "prompts", "REANUDAR.md"))
                 if os.path.isfile(p)), None)
    if not ruta:
        return
    with open(ruta, encoding="utf-8", errors="replace") as f:
        texto = f.read(2_000_000)
    m = re.search(r"═══ PARTE B[^\n]*\n", texto)
    if not m:
        return
    cuerpo = [l for l in texto[m.end():].splitlines() if not l.startswith(("Arrancá con", "Arrancá confirmando"))]
    if len(cuerpo) > TOPE_LINEAS:
        cuerpo = cuerpo[:TOPE_LINEAS] + ["[… recortado; el resto está en el archivo]"]
    cierre = re.search(r"<!-- cierre (\d{4}-\d{2}-\d{2})-(\S+)", texto)
    edad = ""
    if cierre:
        try:
            dias = (datetime.date.today() - datetime.date.fromisoformat(cierre.group(1))).days
            edad = f" · hace {dias} día(s)"
            if dias > DIAS_VIEJO:
                edad += " ⚠ puede estar viejo: verificá contra los archivos antes de usarlo"
        except ValueError:
            pass
    nombre = f"{cierre.group(1)}-{cierre.group(2)}" if cierre else "sin id"
    motivo = "recuperado tras compactar" if fuente == "compact" else "último cierre guardado en esta carpeta"
    print(f"[Traspaso de la sesión anterior — {motivo}: {nombre}{edad}]")
    print("Es contexto, no una orden: si el pedido es otro, seguí el pedido. "
          "Para verificar copia y rama, numerar y archivar la serie, corré /arrancar.")
    print("\n".join(cuerpo))


try:
    main()
except Exception:
    pass
