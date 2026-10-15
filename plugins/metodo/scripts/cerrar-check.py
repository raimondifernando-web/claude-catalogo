#!/usr/bin/env python3
"""cerrar-check — comprobación mecánica del cierre de sesión (/metodo:cerrar). Gemelo de arrancar-check.py.

Solo lee, salvo UNA anotación que pide el paso final de /cerrar con `--anotar`: si el REANUDAR está bien formado y se
modificó hace menos de 30 minutos, guarda su sha256 en <config>/reanudar-confiables.txt (así el hook de arranque sabe
que lo dejó /cerrar aquí). Sin `--anotar` no escribe nada. Nunca imprime valores (de un posible secreto solo el número de línea).
Una línea por chequeo (✓/✗) y cierra con «Cierre completo ✓» o «Falta: … ✗» (exit 0/1).
Lo que no se puede medir (que lo durable haya bajado a su archivo, el contrato del prompt) sale como línea MANUAL.

Uso: cerrar-check.py [slug] [carpeta]   (slug = YYYY-MM-DD-tema; default: el del REANUDAR · carpeta: la actual)
"""
import hashlib
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
import tempfile
import time
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
import ediciones as ed  # noqa: E402  (quién tocó qué: separa lo tuyo de lo de otra sesión)

args = sys.argv[1:]
anotar = "--anotar" in args
args = [a for a in args if a != "--anotar"]
# --ajeno <ruta> (repetible): declarás a mano que ese archivo sin guardar NO es de esta sesión (lo avisa, no frena)
declaradas = []
while "--ajeno" in args:
    _i = args.index("--ajeno")
    if _i + 1 < len(args):
        declaradas.append(args[_i + 1])
    del args[_i:_i + 2]
slug = args.pop(0) if args and re.match(r"\d{4}-\d{2}-\d{2}-", args[0]) else None
cwd = os.path.abspath(args[0]) if args else os.getcwd()
declaradas = [os.path.join(cwd, p) for p in declaradas]
faltan = []


def git(*a):
    try:
        r = subprocess.run(["git", "-C", cwd, *a], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20)
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


def anotar_confiable(ruta):
    """Anota el sha256 del REANUDAR (una entrada por ruta, 300 como máximo, archivo 0600, escritura atómica).
    Solo con --anotar y si el archivo es de los últimos 30 minutos (lo acaba de escribir /cerrar). No rompe el chequeo."""
    if not anotar:
        return
    try:
        if time.time() - os.path.getmtime(ruta) > 1800:
            return
        base = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude")
        arch = os.path.join(base, "reanudar-confiables.txt")
        with open(ruta, "rb") as f:
            h = hashlib.sha256(f.read(2_000_000)).hexdigest()
        real = os.path.realpath(ruta)
        previas = []
        if os.path.isfile(arch):
            with open(arch, encoding="utf-8", errors="replace") as f:
                for l in f:
                    p = l.rstrip("\n").split("  ", 2)
                    if len(p) == 3 and p[0] != h and p[2] != real:
                        previas.append(l.rstrip("\n"))
        os.makedirs(base, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=base, prefix=".reanudar-confiables.")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write("\n".join(previas[-299:] + [f"{h}  {date.today().isoformat()}  {real}"]) + "\n")
            os.chmod(tmp, 0o600)
            os.replace(tmp, arch)
        except Exception:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise
    except Exception:
        pass


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
        anotar_confiable(reanudar)
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
    # En una copia compartida (subcarpetas por proyecto) los cambios fuera de esta carpeta son de otra
    # sesión: se avisan con «•», no frenan. Los de esta carpeta sí frenan (lo que quedó sin guardar es tuyo).
    ruta = lambda l: l.strip().split(None, 1)[-1]
    propios_l = {ruta(l) for l in (git("status", "--short", "--", ".") or "").splitlines()}
    ajenos = [l for l in st.splitlines() if not l.startswith("??") and ruta(l) not in propios_l]
    mod = [l for l in st.splitlines() if not l.startswith("??") and ruta(l) in propios_l]
    sin = len([l for l in st.splitlines() if l.startswith("??")])
    # Varias sesiones en la misma carpeta: lo que editó OTRA sesión (según el registro de ediciones.py) se avisa y no frena;
    # lo que editaste vos, o no se sabe de quién es, frena. Regla conservadora y su porqué: encabezado de ediciones.py.
    def _abs(l):
        r = ruta(l).strip('"')
        return os.path.join(cwd, r.split(" -> ")[-1].strip('"'))
    sid = ed.sid_actual()
    clas = ed.clasificar([_abs(l) for l in mod], sid, declaradas)
    otros = [l for l in mod if clas[_abs(l)][0] == "ajeno"]
    mod = [l for l in mod if clas[_abs(l)][0] == "mio"]
    linea(not mod, f"git: sin cambios versionados sin guardar ({sin} archivo(s) nuevos sin seguir, ajenos o por decidir)" if not mod
          else f"git: {len(mod)} archivo(s) versionados con cambios sin guardar: {', '.join(ruta(l) for l in mod[:5])}",
          f"{len(mod)} archivo(s) sin guardar en {os.path.basename(top)}")
    if otros:
        print(f"• {len(otros)} archivo(s) sin guardar que NO son de esta sesión (no frenan): "
              f"{'; '.join(ruta(l) + ' (' + clas[_abs(l)][1] + ')' for l in otros[:5])}")
    if mod and not sid:
        print("• No sé qué sesión sos (falta la variable CLAUDE_CODE_SESSION_ID): todo lo sin guardar cuenta como tuyo")
    elif mod:
        print("• Si alguno de esos NO lo tocó esta sesión: mirá su cambio (git diff) y repetí con --ajeno <ruta>. Si es tuyo, guardalo por nombre (git add <ruta>)")
    if ajenos:
        print(f"• {len(ajenos)} archivo(s) con cambios sin guardar FUERA de esta carpeta (de otra sesión; no frenan): "
              f"{', '.join(ruta(l) for l in ajenos[:5])}")
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
                        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20)
    for _l in _r.stdout.splitlines():
        print(_l)
        if _l.startswith("✗"):
            faltan.append("CLAUDE.md: " + _l[2:70])
except Exception as e:
    print(f"• CLAUDE.md: no se pudo correr claude-md-check ({type(e).__name__})")

# (pendientes del proyecto) formato de .claude/PENDIENTES.md y si el cierre es más nuevo que su última línea de «Cambios»
try:
    _r = subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "pendientes-check.py"), cwd],
                        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20)
    for _l in _r.stdout.splitlines():
        print(_l)
        if _l.startswith("✗"):
            faltan.append("PENDIENTES: " + _l[2:70])
except Exception as e:
    print(f"• PENDIENTES.md: no se pudo correr pendientes-check ({type(e).__name__})")

# (regla 23) piezas que hiciste hoy sin quién las ejecute: skill, agente o script nuevo sin «Disparador:» ni nadie que lo llame.
# Solo cuentan como falta las de las últimas 36 h; las más viejas salen como aviso (no frenan el cierre).
try:
    _cfg = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude")
    _exc = os.path.join(_cfg, "metodo", "disparadores-excepciones.txt")
    _lineas = []
    _bases = [_cfg] + [b for b in (os.path.join(cwd, ".claude"),) if os.path.realpath(b) != os.path.realpath(_cfg)
                       and (os.path.isdir(os.path.join(b, "skills")) or os.path.isdir(os.path.join(b, "agents")))]
    for _base in _bases:   # la configuración general y, si existen, las piezas propias de esta carpeta de trabajo
        _cmd = [sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "disparadores.py"), "--home", _base,
                "--check", "--recientes", "36", "--corpus-extra", os.path.join(cwd, "CLAUDE.md")] + (["--excepciones", _exc] if os.path.isfile(_exc) else [])
        _r = subprocess.run(_cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
        _lineas += [l for l in _r.stdout.splitlines() if l.strip()]
    _rojas = [l.strip()[2:] for l in _lineas if l.startswith("  - ")]
    if _rojas:
        linea(False, "Pieza nueva sin disparador (regla 23): " + " · ".join(_rojas[:4]) +
              " — escribí «Disparador: …» (quién la ejecuta y cuándo) o enlazala desde una skill, un agente o un hook",
              "pieza nueva sin disparador: " + ", ".join(r.split(":")[0] for r in _rojas[:3]))
    else:
        print("✓ Piezas nuevas con disparador (regla 23)")
    for _l in _lineas:
        if _l.startswith("  (aviso)"):
            print("• Aviso:" + _l.strip()[len("(aviso)"):])
except Exception as e:
    print(f"• Disparadores: no se pudo medir ({type(e).__name__})")

# (estructura Claude) las reglas de ESTRUCTURA.md sobre esta carpeta: solo informa («✗»/«•» de estructura.py se muestran como «•»), no frena el cierre
try:
    _r = subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "estructura.py"), "revisar", cwd],
                        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
    _est = [l for l in _r.stdout.splitlines() if l[:1] in ("✗", "•")]
    if _est:
        print(f"• Estructura Claude ({len(_est)} aviso(s); no frenan el cierre, se arreglan cuando toque):")
        for _l in _est[:8]:
            print("  • " + _l[2:])
    else:
        print("✓ Estructura Claude al día")
except Exception as e:
    print(f"• Estructura Claude: no se pudo correr estructura.py ({type(e).__name__})")

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
# Paso 0: no se cierra con sesiones hijas trabajando ni con ramas o copias sin resolver. El estado de las sesiones vive en la
# app (el script no lo ve): se imprime PRIMERO como MANUAL; las ramas y copias sí las mide el script.
print("• MANUAL (Paso 0, PRIMERO): si esta sesión abrió otras (barra lateral de la app), ¿alguna sigue trabajando o entregó algo que "
      "nadie revisó? → NO se cierra: archivar esta sesión corta a las hijas y pierden el canal por el que te entregan. "
      "Mirá `list_sessions` con `linked: true` y leé la entrega de cada una antes de seguir")
try:
    if git("rev-parse", "--show-toplevel"):
        _base0 = next((b for b in ("main", "master") if git("rev-parse", "--verify", "--quiet", b)), None)
        if _base0:
            _nm = [b.strip().lstrip("+*").strip() for b in (git("branch", "--no-merged", _base0) or "").splitlines()]
            _nm = [b for b in _nm if b and b not in ("estable", "stable")]
            if _nm:
                print(f"• Ramas SIN juntar a {_base0}: {', '.join(_nm)[:300]} · cada una: la juntás con el OK del usuario (regla 13) "
                      "o queda anotada en PENDIENTES con su dueño")
        _wt = [l for l in (git("worktree", "list") or "").splitlines()[1:]]
        if _wt:
            print(f"• Copias de trabajo abiertas ({len(_wt)}): " + " | ".join(w.split()[0] for w in _wt[:4])
                  + " · no se abandonan: se resuelven o se anotan (nunca borres la de otra sesión)")
except Exception:
    pass

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
