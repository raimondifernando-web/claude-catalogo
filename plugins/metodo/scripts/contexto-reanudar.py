#!/usr/bin/env python3
"""Hook SessionStart: le da a la sesión nueva el hilo de la anterior, sin que nadie pegue nada.

Lee el REANUDAR.md que dejó /metodo:cerrar (en la raíz de la carpeta de trabajo, o en .claude/prompts/) y muestra la
PARTE B: fecha del cierre, «De qué veníamos hablando» y pendientes. No muestra el contrato (PARTE A).
Si el archivo no está o no tiene PARTE B, no imprime nada. Si no lo dejó /cerrar en esta máquina (ver `confiable`), solo avisa. Solo lee; nunca escribe ni hace fallar la sesión.
Entrada: el JSON que manda Claude Code por stdin (cwd, source). Solo actúa al abrir (startup) o tras compactar.
"""
import datetime
import hashlib
import json
import os
import re
import sys

TOPE_LINEAS = 40
DIAS_VIEJO = 3


def confiable(crudo):
    """¿Este REANUDAR.md lo dejó /cerrar en ESTA máquina? `cerrar-check --anotar` anota el sha256 del archivo en
    <config>/reanudar-confiables.txt; un archivo de un repo clonado nunca está ahí aunque copie la cabecera.
    Recibe los mismos bytes que se van a mostrar (no vuelve a abrir el archivo)."""
    try:
        base = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude")
        h = hashlib.sha256(crudo).hexdigest()
        with open(os.path.join(base, "reanudar-confiables.txt"), encoding="utf-8", errors="replace") as f:
            return any(l.split()[:1] == [h] for l in f)
    except Exception:
        return False


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
    with open(ruta, "rb") as f:
        crudo = f.read(2_000_000)
    texto = crudo.decode("utf-8", errors="replace")
    m = re.search(r"═══ PARTE B[^\n]*\n", texto)
    # solo un archivo que dejó /cerrar (lleva su línea de cierre): un REANUDAR.md ajeno, de un repo clonado, no se inyecta
    if not m or not re.match(r"\s*<!--\s*cierre\s", texto):
        return
    if not confiable(crudo):
        print("[Hay un REANUDAR.md en esta carpeta que no dejó /cerrar en esta máquina, así que no lo muestro "
              "(podría venir de un repo ajeno). Corré /arrancar y leelo vos.]")
        return
    cuerpo = [l for l in texto[m.end():].splitlines() if not l.startswith(("Arrancá con", "Arrancá confirmando"))]
    if len(cuerpo) > TOPE_LINEAS:
        cuerpo = cuerpo[:TOPE_LINEAS] + ["[… recortado; el resto está en el archivo]"]
    cierre = re.search(r"<!-- cierre (\d{4}-\d{2}-\d{2})-(\S+?)(?=\s|-->|$)", texto)
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
