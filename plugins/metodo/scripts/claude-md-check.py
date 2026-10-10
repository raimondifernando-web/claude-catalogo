#!/usr/bin/env python3
"""claude-md-check — control mecánico del CLAUDE.md del proyecto. Lo llaman arrancar-check.py y cerrar-check.py.

SOLO LEE. Una línea ✓/✗/• por control sobre el CLAUDE.md de la carpeta (o, si no hay, el de la raíz del repo):
  1. Tamaño: AVISO, no falla. Pasa de 30 KB → la pregunta no es bajar bytes sino qué bloque creció y si merece archivo aparte.
  2. Filas de tabla de más de 350 caracteres sin puntero «→ doc, buscar «clave»».
  3. Cada puntero «→ doc, buscar «clave»» apunta a un doc que existe y donde la clave se encuentra.
     Cada «(regla automática: .claude/rules/X.md)» apunta a una regla que existe y tiene `paths:`.
Sin CLAUDE.md, sin git o sin tablas con punteros: lo que no aplica sale ✓/• con un mensaje claro. Nunca inventa ni falla
por una carpeta rara (rutas con espacios, CLAUDE.md enorme o con bytes raros). Exit 1 solo si un control falla.
Uso: claude-md-check.py [carpeta]   (default: la carpeta actual)
"""
import os
import re
import subprocess
import sys

TOPE = 30_000
FILA_MAX = 350
LEER_MAX = 5_000_000   # un CLAUDE.md más grande se mide por tamaño pero no se analiza línea por línea

cwd = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.getcwd()
fallas = []


def linea(ok, texto):
    print(("✓ " if ok else "✗ ") + texto)
    if not ok:
        fallas.append(texto)


def main():
    if not os.path.isdir(cwd):
        print(f"• CLAUDE.md: la carpeta {cwd} no existe, nada que controlar")
        return
    try:
        top = subprocess.run(["git", "-C", cwd, "rev-parse", "--show-toplevel"],
                             capture_output=True, text=True, timeout=10).stdout.strip() or cwd
    except Exception:
        top = cwd
    base = next((d for d in (cwd, top) if os.path.isfile(os.path.join(d, "CLAUDE.md"))), None)
    if base is None:
        print("✓ CLAUDE.md: no hay en esta carpeta, nada que controlar (si es una carpeta de trabajo, conviene crearlo)")
        return
    md = os.path.join(base, "CLAUDE.md")
    try:
        n = os.path.getsize(md)
        with open(md, "rb") as f:
            raw = f.read(LEER_MAX)
    except OSError as e:
        print(f"• CLAUDE.md: no se pudo leer ({type(e).__name__}); no se mide")
        return
    texto = raw.decode("utf-8", errors="replace")
    kb = f"{n:,}".replace(",", ".")
    tope_kb = f"{TOPE:,}".replace(",", ".")
    if n <= TOPE:
        print(f"✓ CLAUDE.md pesa {kb} B (referencia {tope_kb} B)")
    else:
        print(f"• CLAUDE.md pesa {kb} B (referencia {tope_kb} B): no es un error. La pregunta no es bajar bytes sino "
              f"qué bloque creció y si merece su propio archivo (lo que se carga siempre cuesta en cada sesión)")
    if n > LEER_MAX:
        print("• CLAUDE.md es muy grande: se midió el peso pero no se analizaron sus tablas")
        return

    puntero = re.compile(r"→\s*doc,\s*buscar\s*«([^»]+)»")
    regla = re.compile(r"regla automática:\s*(\.claude/rules/[\w.-]+\.md)")
    doc_m = re.search(r"grep -n '<clave>' (\S+?\.md)", texto)
    doc_rel = doc_m.group(1) if doc_m else "docs/MAPA-DELEGACION-DETALLE.md"
    doc_path = os.path.join(base, doc_rel)
    try:
        doc_txt = open(doc_path, encoding="utf-8", errors="replace").read() if os.path.isfile(doc_path) else None
    except OSError:
        doc_txt = None

    largas, sin_doc, sin_clave, punteros = [], False, [], 0
    reglas_ok, reglas_mal = 0, []
    for ln in texto.splitlines():
        if not ln.startswith("|") or re.match(r"^\|[\s:|-]+\|?$", ln):
            continue
        r = regla.search(ln)
        if r:
            rp = os.path.join(base, r.group(1))
            try:
                ok = os.path.isfile(rp) and re.search(r"^paths:", open(rp, encoding="utf-8", errors="replace").read(), re.M)
            except OSError:
                ok = False
            if ok:
                reglas_ok += 1
            else:
                reglas_mal.append(r.group(1))
            continue
        m = puntero.search(ln)
        if m:
            punteros += 1
            if doc_txt is None:
                sin_doc = True
            elif m.group(1) not in doc_txt:
                sin_clave.append(m.group(1))
        elif len(ln) > FILA_MAX:
            partes = ln.split("|")
            largas.append((partes[1] if len(partes) > 1 else ln).strip()[:50])

    linea(not largas, f"Filas de tabla ≤ {FILA_MAX} caracteres o con puntero al doc" if not largas
          else f"{len(largas)} fila(s) de tabla de más de {FILA_MAX} caracteres sin puntero (conviene mandar el detalle a un doc): "
               + " · ".join(largas[:6]))
    if punteros == 0:
        print("✓ Punteros al doc: este CLAUDE.md no usa")
    elif sin_doc:
        linea(False, f"Hay {punteros} puntero(s) pero no existe {doc_rel}")
    else:
        linea(not sin_clave, f"{punteros} puntero(s) al doc, todos con su clave en {doc_rel}" if not sin_clave
              else f"Puntero(s) cuya clave no está en {doc_rel}: " + " · ".join(sin_clave[:6]))
    if reglas_ok or reglas_mal:
        linea(not reglas_mal, f"{reglas_ok} regla(s) automática(s), todas existen y llevan `paths:`" if not reglas_mal
              else "Regla(s) automática(s) que no existen o no tienen `paths:`: " + " · ".join(dict.fromkeys(reglas_mal)))


try:
    main()
except Exception as e:  # un control nunca rompe el arranque ni el cierre
    print(f"• CLAUDE.md: no se pudo controlar ({type(e).__name__})")
sys.exit(1 if fallas else 0)
