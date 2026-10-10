#!/usr/bin/env python3
"""cerrar-check — comprobación mecánica del cierre de sesión (/metodo:cerrar). Gemelo de arrancar-check.py.

SOLO LEE: no escribe nada y nunca imprime valores (de un posible secreto solo el número de línea).
Una línea por chequeo (✓/✗) y cierra con «Cierre completo ✓» o «Falta: … ✗» (exit 0/1).
Lo que no se puede medir (que lo durable haya bajado a su archivo, el contrato del prompt) sale como línea MANUAL.

Uso: cerrar-check.py [slug] [carpeta]   (slug = YYYY-MM-DD-tema; default: el del REANUDAR · carpeta: la actual)
"""
import os
import re
import subprocess
import sys
from datetime import date

args = sys.argv[1:]
slug = args.pop(0) if args and re.match(r"\d{4}-\d{2}-\d{2}-", args[0]) else None
cwd = os.path.abspath(args[0]) if args else os.getcwd()
faltan = []


def git(*a):
    try:
        r = subprocess.run(["git", "-C", cwd, *a], capture_output=True, text=True, timeout=20)
        return r.stdout.strip() if r.returncode == 0 else None
    except Exception:
        return None


def linea(ok, texto, falta=None):
    print(("✓ " if ok else "✗ ") + texto)
    if not ok:
        faltan.append(falta or texto)


def leer(p):
    try:
        return open(p, encoding="utf-8", errors="replace").read()
    except OSError:
        return ""


# (b) REANUDAR: existe, encabezado, largo
reanudar = next((p for p in (os.path.join(cwd, "REANUDAR.md"), os.path.join(cwd, ".claude", "prompts", "REANUDAR.md"))
                 if os.path.isfile(p)), None)
texto = leer(reanudar) if reanudar else ""
if not texto:
    linea(False, f"No existe REANUDAR.md en {cwd} (paso 8 de /metodo:cerrar)", "REANUDAR.md")
else:
    m = re.match(r"\s*<!--\s*cierre\s+(\d{4}-\d{2}-\d{2}-\S+?)\s", texto)
    if m:
        linea(True, f"REANUDAR.md presente · cierre {m.group(1)}")
        if slug and slug != m.group(1):
            linea(False, f"El slug pedido ({slug}) no es el del REANUDAR ({m.group(1)})", "REANUDAR de otro cierre")
        slug = slug or m.group(1)
    else:
        linea(False, "REANUDAR.md sin la línea «<!-- cierre YYYY-MM-DD-tema …»", "REANUDAR sin ID de cierre")
    n = len(texto.splitlines())
    linea(n <= 60, f"REANUDAR mide {n} líneas (apuntá a 30-50, techo 60)",
          f"REANUDAR de {n} líneas: lo durable va al CLAUDE.md, no al prompt")

    # (c) conteos hardcodeados y pinta de secreto: solo número de línea
    contador = re.compile(r"(?<![\d.])\b\d+\s+(skills?|agentes?|PMs?|reglas|archivos|tests?|hooks?|plugins?|MCPs?|proyectos|pendientes|clientes)\b", re.I)
    secreto = re.compile(
        r"sk-[A-Za-z0-9_-]{16,}|Bearer\s+\S{12,}|gh[pousr]_[A-Za-z0-9]{20,}|xox[abprs]-\S{10,}|AKIA[0-9A-Z]{12,}|"
        r"(?i:token|clave|password|contraseña|secret|api[_-]?key)\s*[:=]\s*[\"']?[A-Za-z0-9_\-/+=]{16,}|"
        r"(?<![0-9a-fA-F])(?=[A-Za-z0-9]*[A-Za-z])(?=[A-Za-z0-9]*\d)[A-Za-z0-9]{32,}(?![A-Za-z0-9])"
    )
    cont, sec = [], []
    for i, l in enumerate(texto.splitlines(), 1):
        if contador.search(l):
            cont.append(i)
        if secreto.search(l):
            sec.append(i)
    linea(not cont, "Sin números de memoria en el REANUDAR" if not cont
          else f"Números de memoria en las líneas {cont} (va el comando que los cuenta, no el número)",
          f"conteos hardcodeados en REANUDAR (líneas {cont})")
    linea(not sec, "Sin pinta de clave en el REANUDAR" if not sec else f"Posible clave en las líneas {sec} (valor no mostrado)",
          f"posible clave en REANUDAR (líneas {sec}): sacarla")

# (d) repo con varias copias → Copia/Rama declaradas; (f) git
top = git("rev-parse", "--show-toplevel")
rama = git("branch", "--show-current")
if top is None:
    print(f"- Carpeta fuera de git ({cwd}): copia/rama, commits y subida no aplican")
else:
    wts = [l for l in (git("worktree", "list") or "").splitlines() if l.strip()]
    if len(wts) > 1 and texto:
        decl = re.findall(r"(?:Copia|Worktree):?\s*(\S+)\s*·\s*Rama:?\s*(\S+)", texto)
        linea(bool(decl), f"Repo con {len(wts)} copias: el REANUDAR declara Copia · Rama" if decl
              else f"Repo con {len(wts)} copias y el REANUDAR no declara «Copia: … · Rama: …» (regla 11)",
              "REANUDAR sin línea Copia · Rama (repo con varias copias)")
    else:
        print("✓ Repo de una sola copia: no hace falta declarar Copia/Rama")

    st = git("status", "--short") or ""
    mod = [l for l in st.splitlines() if not l.startswith("??")]
    sin = len([l for l in st.splitlines() if l.startswith("??")])
    linea(not mod, f"git: sin cambios versionados sin guardar ({sin} archivo(s) nuevos sin seguir, ajenos o por decidir)" if not mod
          else f"git: {len(mod)} archivo(s) versionados con cambios sin guardar: {', '.join(l.split(None, 1)[-1] for l in mod[:5])}",
          f"{len(mod)} archivo(s) sin guardar en {os.path.basename(top)}")
    cab = (git("status", "-sb") or "").splitlines()[:1]
    cab = cab[0] if cab else ""
    adelante = re.search(r"ahead (\d+)", cab)
    atras = re.search(r"behind (\d+)", cab)
    if "..." not in cab:
        linea(False, f"La rama {rama} no tiene remoto: el avance no se subió", "rama sin remoto (avance sin subir)")
    else:
        linea(not adelante, "Rama al día con el remoto (nada sin subir)" if not adelante
              else f"{adelante.group(1)} guardado(s) sin subir",
              f"{adelante.group(1) if adelante else 0} guardado(s) sin subir")
        if atras:
            print(f"• El remoto tiene {atras.group(1)} guardado(s) que no traés (pull --rebase --autostash antes de seguir)")
    ult = (git("show", "--stat", "--format=", "HEAD") or "").splitlines()
    nf = max(len(ult) - 1, 0)
    linea(nf <= 15, f"Último guardado toca {nf} archivo(s)" if nf <= 15
          else f"Último guardado toca {nf} archivos: ¿se coló un «git add -A»? (regla 13)",
          f"último guardado con {nf} archivos (¿add -A?)")

# (a) handoff (obligatorio con 3 o más archivos tocados hoy)
if slug:
    hoy = slug[:10]
    tocados = set()
    if top:
        out = git("log", f"--since={hoy} 00:00", "--name-only", "--format=") or ""
        tocados = {f for f in out.splitlines() if f.strip()}
    carpetas = [os.path.join(cwd, "handoffs"), os.path.join(top or cwd, "handoffs")]
    ho = next((os.path.join(c, slug + ".md") for c in carpetas if os.path.isfile(os.path.join(c, slug + ".md"))), None)
    if ho:
        linea(True, f"Handoff handoffs/{slug}.md presente")
    elif len(tocados) >= 3:
        linea(False, f"Falta el handoff {slug}.md y hay {len(tocados)} archivos tocados hoy (obligatorio desde 3)",
              "handoff obligatorio (3 o más archivos)")
    else:
        print(f"✓ Sin handoff: solo {len(tocados)} archivo(s) guardados hoy (obligatorio desde 3; "
              f"las decisiones las juzga la sesión)")

# (CLAUDE.md) peso, filas largas y punteros: lo mide claude-md-check.py (solo lee; si no se puede correr, lo dice)
try:
    _r = subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "claude-md-check.py"), cwd],
                        capture_output=True, text=True, timeout=20)
    for _l in _r.stdout.splitlines():
        print(_l)
        if _l.startswith("✗"):
            faltan.append("CLAUDE.md: " + _l[2:70])
except Exception as e:
    print(f"• CLAUDE.md: no se pudo correr claude-md-check ({type(e).__name__})")

# (pendientes del proyecto) formato de .claude/PENDIENTES.md y si el cierre es más nuevo que su última línea de «Cambios»
try:
    _r = subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "pendientes-check.py"), cwd],
                        capture_output=True, text=True, timeout=20)
    for _l in _r.stdout.splitlines():
        print(_l)
        if _l.startswith("✗"):
            faltan.append("PENDIENTES: " + _l[2:70])
except Exception as e:
    print(f"• PENDIENTES.md: no se pudo correr pendientes-check ({type(e).__name__})")

# (verificación propia) ramas ya mergeadas que quedaron vivas + línea de prueba del resultado (regla 1 del método)
try:
    if git("rev-parse", "--show-toplevel"):
        _base = next((b for b in ("main", "master") if git("rev-parse", "--verify", "--quiet", b)), None)
        if _base:
            _ya = []
            for _b in (git("branch", "--merged", _base) or "").splitlines():
                _b = _b.rstrip()
                # «*» = la rama actual y «+» = la de otra copia abierta: no se proponen para borrar
                _n = _b.strip()
                # fuera: la actual (*), las de otras copias (+), las protegidas y las recién creadas (mismo guardado que la base)
                if _b and not _b.lstrip().startswith(("*", "+")) and _n not in ("main", "master", _base, "estable", "stable", "develop", "dev") \
                        and not _n.startswith(("release", "hotfix")) and git("rev-parse", _n) != git("rev-parse", _base):
                    _ya.append(_n)
            if _ya:
                print(f"• Ramas ya mergeadas que siguen vivas: {', '.join(_ya[:5])} · probá el resultado y, recién ahí, borralas (o decí por qué quedan)")
except Exception:
    pass

print("• MANUAL (verificación propia): ¿qué PROBASTE del resultado de lo que hiciste hoy (que funciona, no que el comando salió "
      "sin error)? Una línea por cosa: qué corriste y qué viste en el disco. Lo no probado, dicho. Nada se limpia ni se da por "
      "«listo» sin eso (regla 1 del método)")
# (g) lo que solo puede hacer la sesión
print("• MANUAL (paso 3, lo durable): lo que esta sesión aprendió como regla permanente ya bajó al CLAUDE.md (o a su archivo), "
      "no solo al prompt — decí dónde fue cada cosa, o «nada»")
print("• MANUAL (paso 7, contrato): la PARTE A del prompt trae ROL · ALCANCE · REGLAS con contenido real "
      "(no una línea genérica) y la PARTE B los pendientes en orden")

print()
if faltan:
    print("Falta: " + " · ".join(faltan) + " ✗")
    sys.exit(1)
print("• MANUAL (paso 10, LO ÚLTIMO): en la app de escritorio, después del prompt y EN LA MISMA respuesta: start_session → detach → move → archive; no cierres el turno sin hacerlo o sin decir por qué no (en terminal o Cowork: «no aplica»)")
print("Cierre completo ✓ (más los ítems MANUAL, que reporta la sesión)")
