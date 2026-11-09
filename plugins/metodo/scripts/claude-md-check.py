#!/usr/bin/env python3
"""claude-md-check — control mecánico del CLAUDE.md del proyecto. Lo llaman arrancar-check.py y cerrar-check.py.

SOLO LEE. Una línea ✓/✗/• por control sobre el CLAUDE.md de la carpeta (o, si no hay, el de la raíz del repo):
  1. Tamaño: AVISO, no falla. Pasa de 30 KB → la pregunta no es bajar bytes sino qué bloque creció y si merece archivo aparte.
  2. Filas de tabla de más de 350 caracteres sin puntero «→ doc, buscar «clave»».
  3. Cada puntero «→ doc, buscar «clave»» apunta a un doc que existe y donde la clave se encuentra.
     Cada «(regla automática: .claude/rules/X.md)» apunta a una regla que existe y tiene `paths:`.
  4. Peso al arrancar (AVISO, nunca falla): suma lo que Claude Code carga al abrir una sesión en esta carpeta (ficha
     personal con sus @importados, CLAUDE.md del proyecto, reglas sin `paths:` de usuario y de proyecto, índice MEMORY.md)
     y compara con un presupuesto por capa (TOPES_ARRANQUE). Si una capa se pasa, nombra su bloque más grande y a dónde
     va: regla que carga sola al actuar (`reglas-al-actuar/`), regla con `paths:`, o doc con puntero. Nunca «borralo».
Sin CLAUDE.md, sin git o sin tablas con punteros: lo que no aplica sale ✓/• con un mensaje claro. Nunca inventa ni falla
por una carpeta rara (rutas con espacios, CLAUDE.md enorme o con bytes raros). Exit 1 solo si un control falla.
Uso: claude-md-check.py [carpeta]   (default: la carpeta actual)
"""
import os
import re
import subprocess
import sys

# Windows: la consola usa cp1252 y los ✓/✗ y acentos hacían caer el script; se fuerza UTF-8 en entrada y salida.
for _flujo in (sys.stdin, sys.stdout, sys.stderr):
    try:
        _flujo.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

TOPE = 30_000
FILA_MAX = 350
LEER_MAX = 5_000_000   # un CLAUDE.md más grande se mide por tamaño pero no se analiza línea por línea

# Presupuesto al arrancar (bytes; ~0,45 tokens por byte). Avisa, no frena (regla R7 de la casa).
TOPES_ARRANQUE = {"ficha personal": 40_000, "CLAUDE.md del proyecto": TOPE, "reglas sin paths": 3_000,
                  "MEMORY.md": 13_000, "total": 86_000}
MEMORIA_LINEAS = 110

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
                             capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10).stdout.strip() or cwd
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
    try:
        peso_al_arrancar(base)
    except Exception as e:  # el aviso de peso nunca rompe el control
        print(f"• Peso al arrancar: no se pudo medir ({type(e).__name__})")
    if n > LEER_MAX:
        print("• CLAUDE.md es muy grande: se midió el peso pero no se analizaron sus tablas")
        return

    puntero = re.compile(r"→\s*doc,\s*buscar\s*«([^»]+)»")
    regla = re.compile(r"regla automática:\s*(\.claude/rules/[\w.-]+\.md)")
    doc_m = re.search(r"grep -n '<clave>' (\S+?\.md)", texto)
    doc_rel = doc_m.group(1) if doc_m else None   # sin doc declarado, los punteros no se pueden verificar
    doc_path = os.path.join(base, doc_rel) if doc_rel else None
    try:
        doc_txt = open(doc_path, encoding="utf-8", errors="replace").read() if doc_path and os.path.isfile(doc_path) else None
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

    if largas:   # estilo, no error: nunca traba un arranque ni un cierre
        print(f"• {len(largas)} fila(s) de tabla de más de {FILA_MAX} caracteres (conviene mandar el detalle a un doc aparte): "
              + " · ".join(largas[:6]))
    else:
        print(f"✓ Filas de tabla ≤ {FILA_MAX} caracteres o con puntero al doc")
    if punteros == 0:
        print("✓ Punteros al doc: este CLAUDE.md no usa")
    elif doc_rel is None:
        print(f"• {punteros} puntero(s) «→ doc, buscar»: el CLAUDE.md no declara en qué archivo (grep -n '<clave>' <archivo>.md), no se verifican")
    elif sin_doc:
        linea(False, f"Hay {punteros} puntero(s) pero no existe {doc_rel}")
    else:
        linea(not sin_clave, f"{punteros} puntero(s) al doc, todos con su clave en {doc_rel}" if not sin_clave
              else f"Puntero(s) cuya clave no está en {doc_rel}: " + " · ".join(sin_clave[:6]))
    if reglas_ok or reglas_mal:
        linea(not reglas_mal, f"{reglas_ok} regla(s) automática(s), todas existen y llevan `paths:`" if not reglas_mal
              else "Regla(s) automática(s) que no existen o no tienen `paths:`: " + " · ".join(dict.fromkeys(reglas_mal)))


def _leer(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read(LEER_MAX)
    except OSError:
        return ""


def _con_importados(path):
    """Texto de una ficha más sus @importados de un nivel (los @import no ahorran: cargan juntos)."""
    t = _leer(path)
    extra = ""
    for m in re.finditer(r"(?m)^@(\S+)\s*$", t):
        ruta = os.path.expanduser(m.group(1))
        if not os.path.isabs(ruta):
            ruta = os.path.join(os.path.dirname(path), ruta)
        extra += _leer(ruta)
    return t + extra


def _sin_paths(carpeta):
    total, n = 0, 0
    for raiz, _d, archivos in os.walk(carpeta):
        for a in archivos:
            if a.endswith(".md"):
                t = _leer(os.path.join(raiz, a))
                if not re.match(r"---\s*\n(?:.*\n)*?paths:", t):
                    total += len(t.encode("utf-8"))
                    n += 1
    return total, n


def _bloque_mayor(texto):
    partes = re.split(r"(?m)^(?=#{1,3} )", texto)
    mejor = max(partes, key=lambda s: len(s.encode("utf-8")), default="")
    return (mejor.splitlines() or ["(sin títulos)"])[0][:60], len(mejor.encode("utf-8"))


def peso_al_arrancar(base):
    cfg = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude")
    global_t = _con_importados(os.path.join(cfg, "CLAUDE.md"))
    proy_t = _leer(os.path.join(base, "CLAUDE.md")) + _leer(os.path.join(base, ".claude", "CLAUDE.md"))
    r1, n1 = _sin_paths(os.path.join(cfg, "rules"))
    r2, n2 = _sin_paths(os.path.join(base, ".claude", "rules"))
    slug = re.sub(r"[^A-Za-z0-9]", "-", os.path.abspath(base))
    mem = _leer(os.path.join(cfg, "projects", slug, "memory", "MEMORY.md"))
    capas = {"ficha personal": (len(global_t.encode("utf-8")), global_t),
             "CLAUDE.md del proyecto": (len(proy_t.encode("utf-8")), proy_t),
             "reglas sin paths": (r1 + r2, ""), "MEMORY.md": (len(mem.encode("utf-8")), mem)}
    total = sum(v[0] for v in capas.values())
    kb = lambda b: f"{b / 1000:.1f}".replace(".", ",") + " KB"
    resumen = " · ".join(f"{k} {kb(v[0])}" for k, v in capas.items())
    pasadas = [k for k, v in capas.items() if v[0] > TOPES_ARRANQUE[k]]
    mem_lineas = len(mem.splitlines())
    if mem_lineas > MEMORIA_LINEAS and "MEMORY.md" not in pasadas:
        pasadas.append("MEMORY.md")
    if not pasadas and total <= TOPES_ARRANQUE["total"]:
        print(f"✓ Peso al arrancar {kb(total)} ≈ {int(total * 0.45 / 1000)}k tokens (presupuesto {kb(TOPES_ARRANQUE['total'])}): {resumen}")
        return
    print(f"• Peso al arrancar {kb(total)} ≈ {int(total * 0.45 / 1000)}k tokens (presupuesto {kb(TOPES_ARRANQUE['total'])}): {resumen}. "
          "No es un error: lo que se carga siempre lo paga cada sesión.")
    for k in pasadas:
        if k == "reglas sin paths":
            print(f"  • {k}: {n1 + n2} archivo(s) se cargan siempre; si cuidan una acción, van a `reglas-al-actuar/`; si son de una carpeta, llevan `paths:`")
        elif k == "MEMORY.md":
            print(f"  • {k}: {mem_lineas} líneas; el índice lleva una línea corta por memoria (≤120 caracteres), el detalle en su archivo")
        else:
            titulo, b = _bloque_mayor(capas[k][1])
            print(f"  • {k} ({kb(capas[k][0])}, tope {kb(TOPES_ARRANQUE[k])}): el bloque más grande es «{titulo}» ({kb(b)}). "
                  "Lo que cuida una acción va a `reglas-al-actuar/`; lo de una carpeta, a una regla con `paths:`; los pasos, a un doc con puntero. No se borra nada.")


try:
    main()
except Exception as e:  # un control nunca rompe el arranque ni el cierre
    print(f"• CLAUDE.md: no se pudo controlar ({type(e).__name__})")
sys.exit(1 if fallas else 0)
