#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""raices_agentes — la LISTA de carpetas donde viven los agentes propios de Fer (no solo ~/.claude/agents).

Disparador: encadenado — lo importan los programas que inventarían o controlan agentes (catalogo-check.sh, catalogo-sync.py,
  repetidos.py, disparadores.py, reglas-salud.py, agentes-etiqueta.py, aviso-piezas-nuevas.py, hooks/skill-en-agente.py);
  el plugin `metodo` (mapa_lector.py, disparadores.py, skill-en-agente.py) lleva su propia copia con el mismo formato para que
  funcione en la máquina del cliente. Prueba de disparo: scripts/tests/test_raices_agentes.py.
  A mano: `python3 raices_agentes.py` (raíces y cuántos agentes hay en cada una) · `--archivos` · `--nombres` · `--buscar <nombre>` · `--raices`.

Por qué (decisión de Fer, 2026-11-10): los PM y especialistas de un proyecto viven en `<proyecto>/.claude/agents/` y el kit de pyme en
una sola copia enlazada a las carpetas que lo usan; `~/.claude/agents/` queda para los especialistas generales. Cada programa que
antes leía solo `~/.claude/agents` lee ahora TODAS las raíces, así los conteos, el mapa, el portero y el catálogo ven todo.

Archivo: <config de Claude>/metodo/raices-agentes.txt — una ruta por línea, `~` (= la carpeta que contiene a la config) y comodines
permitidos, `#` comenta. Si falta, la única raíz es <config>/agents. La variable RAICES_AGENTES (rutas separadas por «:», en Windows por «;») manda sobre todo.
Todas las funciones aceptan `claude_dir` (por defecto ~/.claude): así las pruebas usan una config temporal sin tocar la real.
"""
import glob
import os

POR_DEFECTO = ["~/.claude/agents"]


def _cd(claude_dir=None):
    return os.path.abspath(os.path.expanduser(claude_dir or os.path.join("~", ".claude")))


def raices(claude_dir=None):
    """Carpetas de agentes existentes, en orden y sin repetir (dos rutas que apuntan al mismo lugar cuentan una vez)."""
    cd = _cd(claude_dir)
    home = os.path.dirname(cd)
    env = os.environ.get("RAICES_AGENTES")
    if env:
        lineas = [x for x in env.split(os.pathsep) if x.strip()]   # «:» en Mac/Linux, «;» en Windows
    else:
        lineas = [os.path.join(cd, "agents")]
        try:
            with open(os.path.join(cd, "metodo", "raices-agentes.txt"), encoding="utf-8") as f:
                leidas = [l.strip() for l in f if l.strip() and not l.lstrip().startswith("#")]
            if leidas:
                lineas = leidas
        except OSError:
            pass
    out, vistos = [], set()
    for patron in lineas:
        p = patron.replace("~", home, 1) if patron.startswith("~") else patron
        for d in sorted(glob.glob(p)) if any(c in p for c in "*?[") else [p]:
            real = os.path.realpath(d)          # la ruta real solo para no repetir (enlaces); se devuelve la ruta tal como se pidió
            if os.path.isdir(d) and real not in vistos:
                vistos.add(real)
                out.append(os.path.abspath(d))
    return out


def archivos(claude_dir=None):
    """Todos los agentes (*.md directo en cada raíz; las subcarpetas son enlaces al kit y se cuentan por su raíz real). Sin repetir."""
    out, vistos = [], set()
    for r in raices(claude_dir):
        for f in sorted(glob.glob(os.path.join(r, "*.md"))):
            real = os.path.realpath(f)
            if real not in vistos and os.path.isfile(real):
                vistos.add(real)
                out.append(f)
    return out


def nombres(claude_dir=None):
    return [os.path.basename(f)[:-3] for f in archivos(claude_dir)]


def buscar(nombre, claude_dir=None):
    """Ruta del agente <nombre>.md en la primera raíz que lo tenga, o None."""
    for r in raices(claude_dir):
        f = os.path.join(r, nombre + ".md")
        if os.path.isfile(f):
            return f
    return None


def raiz_de(ruta_agente, claude_dir=None):
    """Etiqueta corta de la raíz: 'personal' (<config>/agents), 'kit-pyme' (<config>/kit-pyme/agents) o 'proyecto:<carpeta>'."""
    cd = _cd(claude_dir)
    real = os.path.realpath(os.path.dirname(ruta_agente))
    if real == os.path.realpath(os.path.join(cd, "agents")):
        return "personal"
    if real == os.path.realpath(os.path.join(cd, "kit-pyme", "agents")):
        return "kit-pyme"
    home = os.path.realpath(os.path.dirname(cd))
    rel = real[len(home) + 1:] if real.startswith(home + os.sep) else real
    partes = [p for p in rel.split(os.sep) if p not in ("Proyectos", ".claude", "agents")]
    return "proyecto:" + "/".join(partes)


if __name__ == "__main__":
    import sys
    a = sys.argv[1:]
    if "--archivos" in a:
        print("\n".join(archivos()))
    elif "--nombres" in a:
        print("\n".join(nombres()))
    elif "--buscar" in a:
        r = buscar(a[a.index("--buscar") + 1])
        print(r or "")
        sys.exit(0 if r else 1)
    elif "--raices" in a:
        print("\n".join(raices()))
    else:
        for r in raices():
            print(f"{r}: {len(glob.glob(os.path.join(r, '*.md')))} agente(s)")
        print(f"Total sin repetir: {len(archivos())}")
