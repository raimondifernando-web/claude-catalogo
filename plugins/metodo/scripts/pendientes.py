#!/usr/bin/env python3
"""pendientes — imprime la lista .claude/PENDIENTES.md de la carpeta (o de la raíz de su repo) en una tabla corta.
SOLO LEE. Uso: pendientes.py [carpeta] [--prio1]   (--prio1: solo las de prioridad 1 abiertas, para /arrancar)"""
import importlib.util
import os
import re
import sys
from datetime import date

_aqui = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("pendientes_check", os.path.join(_aqui, "pendientes-check.py"))
chk = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(chk)


def filas(texto):
    out, modo, cab = [], "otro", False
    for l in texto.split("\n"):
        m = re.match(r"^##\s+(.*)$", l)
        if m:
            modo = "fila" if re.match(r"^[A-Z]\s*·", m.group(1)) else "otro"
            cab = False
            continue
        if modo != "fila" or not l.lstrip().startswith("|"):
            continue
        c = chk.celdas(l)
        if all(re.match(r"^:?-+:?$", x) for x in c):
            continue
        if not cab:
            cab = True
            continue
        if len(c) == chk.NCOL and re.match(r"^[A-Z]\d+$", c[0]):
            out.append(c)
    return out


def hace(ultima):
    try:
        d = (date.today() - date.fromisoformat(ultima)).days
    except Exception:
        return "sin fecha de actualización"
    if d <= 0:
        return "actualizada hoy"
    return f"actualizada hace {d} día(s)" + (" · puede estar vieja" if d > 7 else "")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    solo1 = "--prio1" in sys.argv
    cwd = os.path.abspath(args[0]) if args else os.getcwd()
    p = chk.buscar(cwd)
    if not p:
        print("Esta carpeta no tiene lista todavía." if not solo1 else "")
        return 0
    try:
        texto = open(p, encoding="utf-8").read()
    except Exception:
        print("No pude leer la lista de pendientes de esta carpeta.")
        return 0
    prob, _ids, ultima = chk.analizar(texto)
    fs = [f for f in filas(texto) if f[3] != "hecho"]
    if solo1:
        fs = [f for f in fs if f[2] == "1"]
        for f in fs[:3]:
            print(f"{f[0]} · {f[1][:80]} · {f[3]}")
        if len(fs) > 3:
            print(f"y {len(fs) - 3} más: /metodo:pendientes")
        return 0
    fs.sort(key=lambda f: (f[2], f[0]))
    print(f"Pendientes de esta carpeta ({hace(ultima)}):")
    print("| ID | Pendiente | Prio | Estado | Quién |")
    print("|---|---|---|---|---|")
    for f in fs:
        print(f"| {f[0]} | {f[1]} | {f[2]} | {f[3]} | {f[6]} |")
    if not fs:
        print("(nada abierto)")
    if prob:
        print("\nOjo, la lista tiene problemas de formato (se muestra igual): " + " | ".join(prob[:3]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
