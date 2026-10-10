#!/usr/bin/env python3
"""pendientes-check — valida .claude/PENDIENTES.md de la carpeta (o de la raíz de su repo).
SOLO LEE. Una línea ✓/✗. Si no hay lista, no aplica (✓). Exit 1 si hay problemas.
Uso: pendientes-check.py [carpeta]"""
import os
import re
import subprocess
import sys

NCOL = 8
ESTADO_OK = re.compile(r"^(pendiente|en curso|hecho|espera dato( de .+)?|espera OK( de .+)?)$", re.I)
ESTADOS_TXT = "pendiente · en curso · espera dato · espera OK · hecho"


def raiz(cwd):
    try:
        r = subprocess.run(["git", "-C", cwd, "rev-parse", "--show-toplevel"], capture_output=True, text=True, timeout=10)
        return r.stdout.strip() or cwd
    except Exception:
        return cwd


def celdas(linea):
    out, cur, code = [], "", False
    linea = linea.strip().replace("\\|", "\x00")
    for ch in linea.strip("|"):
        if ch == "`":
            code = not code
        if ch == "|" and not code:
            out.append(cur.strip())
            cur = ""
        else:
            cur += ch
    out.append(cur.strip())
    return [x.replace("\x00", "|") for x in out]


def buscar(cwd):
    top = raiz(cwd)
    for q in (os.path.join(cwd, ".claude", "PENDIENTES.md"), os.path.join(top, ".claude", "PENDIENTES.md")):
        if os.path.isfile(q):
            return q
    return ""


def analizar(texto):
    """→ (problemas, ids, ultima_fecha_de_cambios)"""
    prob, ids, donde = [], set(), {}
    modo, cab, ultima, libre = "otro", False, "", True
    for i, l in enumerate(texto.split("\n"), 1):
        if re.match(r"^(<{7}|>{7})", l):
            prob.append(f"marca de conflicto de git en la línea {i} (dos sesiones editaron lo mismo): resolverla a mano")
        if modo == "cambios":
            mc = re.match(r"^\s*(?:[-*|]\s*)?(\d{4}-\d{2}-\d{2})\b", l)
            if mc and mc.group(1) > ultima:
                ultima = mc.group(1)
        m = re.match(r"^##\s+(.*)$", l)
        if m:
            modo = "fila" if re.match(r"^[A-Z]\s*[·\-–—:.]\s*\S", m.group(1)) else ("cambios" if m.group(1).startswith("Cambios") else "otro")
            libre = m.group(1).startswith(("Hechos", "Fechas", "Cambios"))
            cab = False
            if modo == "fila" and not re.match(r"^[A-Z]\s*·", m.group(1)):
                prob.append(f"línea {i}: el título de sección tiene que ser «## {m.group(1)[0]} · Nombre» (con un punto medio ·)")
            continue
        if not l.lstrip().startswith("|"):
            continue
        c = celdas(l)
        if all(re.match(r"^:?-+:?$", x) for x in c):
            continue
        if modo == "otro" and not libre and re.match(r"^[A-Z]\d+$", c[0]):
            prob.append(f"línea {i}: hay una fila ({c[0]}) fuera de una sección «## A · Nombre»: el control no la cuenta")
            continue
        if modo != "fila":
            continue
        if not cab:
            cab = True
            if re.match(r"^[A-Z]\d+$", c[0]):
                prob.append(f"línea {i}: a la tabla le falta la fila de encabezado (| ID | Pendiente | …): {c[0]} se tomó como encabezado")
            continue
        if len(c) != NCOL:
            prob.append(f"{c[0]}: {len(c)} columnas (tienen que ser {NCOL})")
            continue
        if not re.match(r"^[A-Z]\d+$", c[0]):
            prob.append(f"línea {i}: «{c[0]}» no es un ID válido")
            continue
        if c[2] not in ("1", "2", "3"):
            prob.append(f"{c[0]}: prioridad «{c[2]}» no es 1, 2 ni 3")
        if not ESTADO_OK.match(c[3]):
            prob.append(f"{c[0]}: estado «{c[3]}» no es uno de: {ESTADOS_TXT}")
        if c[0] in ids:
            prob.append(f"{c[0]}: repetido (líneas {donde[c[0]]} y {i}): dos sesiones lo crearon a la vez, cambiale el número a la más nueva")
        ids.add(c[0])
        donde.setdefault(c[0], i)
    return prob, ids, ultima


def main():
    cwd = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.getcwd()
    p = buscar(cwd)
    if not p:
        print("✓ PENDIENTES.md: no hay en esta carpeta, nada que controlar")
        return 0
    try:
        texto = open(p, encoding="utf-8").read()
    except Exception as e:
        print(f"✗ PENDIENTES.md: no se pudo leer ({type(e).__name__})")
        return 1
    prob, ids, ultima = analizar(texto)
    if prob:
        print(f"✗ PENDIENTES.md tiene {len(prob)} problema(s): " + " | ".join(prob[:4]))
        return 1
    aviso = []
    rea = os.path.join(os.path.dirname(os.path.dirname(p)), ".claude", "prompts", "REANUDAR.md")
    if not ultima:
        aviso.append("«Cambios» no tiene ninguna línea fechada (AAAA-MM-DD): no se sabe cuándo se actualizó")
    elif os.path.isfile(rea):
        try:
            mr = re.search(r"cierre (\d{4}-\d{2}-\d{2})", open(rea, encoding="utf-8", errors="replace").read(400))
            cierre = mr.group(1) if mr else ""
            if cierre > ultima:
                aviso.append(f"el último cierre ({cierre}) es más nuevo que la última línea de «Cambios» ({ultima}): se cerró sin tocar la lista")
        except Exception:
            pass
    print(f"✓ PENDIENTES.md: {len(ids)} filas, formato correcto")
    for a in aviso:
        print("• AVISO PENDIENTES.md: " + a)
    return 0


if __name__ == "__main__":
    sys.exit(main())
