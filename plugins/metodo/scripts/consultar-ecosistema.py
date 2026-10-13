#!/usr/bin/env python3
"""PreToolUse (Write|Agent|Workflow): frena UNA vez por carpeta cada 4 h cuando se va a construir algo que tiene
receta (regla 22 del método) y entrega la receta en el mismo mensaje. Precisión antes que cobertura: si ninguna
receta coincide, no dice nada. Solo lee; nunca decide permisos y nunca rompe la sesión: ante cualquier error, deja pasar.
Apagar: CONSULTAR_ECOSISTEMA_OFF=1 o crear <config de Claude>/metodo/consultar-ecosistema.apagado."""
import json, os, re, subprocess, sys, time

# Windows: la consola usa cp1252 y los acentos / ⛔ hacían caer el script (UnicodeEncodeError); se fuerza UTF-8 en entrada y salida.
for _flujo in (sys.stdin, sys.stdout, sys.stderr):
    try:
        _flujo.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

CFG = os.environ.get("CLAUDE_CONFIG_DIR", os.path.expanduser("~/.claude"))
AQUI = os.path.dirname(os.path.abspath(__file__))
TTL = 4 * 3600
EXT = {".html", ".css", ".scss", ".tsx", ".jsx", ".vue", ".svelte", ".swift"}
VERBOS = re.compile(r"(cre[aá]|constru|arm[aá]|implement|dise[nñ]|prototip|desarroll|build|create|design|develop|evalu|instal|adopt|install)", re.I)


def main():
    if os.environ.get("CONSULTAR_ECOSISTEMA_OFF") or os.path.exists(os.path.join(CFG, "metodo", "consultar-ecosistema.apagado")):
        return 0
    d = json.loads(sys.stdin.read() or "{}")
    tool, ti = d.get("tool_name", ""), d.get("tool_input", {}) or {}
    cwd = d.get("cwd") or os.getcwd()
    if tool == "Write":
        p = ti.get("file_path", "")
        if os.path.splitext(p)[1].lower() not in EXT or f"{os.sep}.claude{os.sep}" in p or os.path.exists(p):
            return 0  # solo archivos NUEVOS de interfaz, fuera de .claude/
        texto = p + " " + str(ti.get("content", ""))[:600]
    elif tool in ("Agent", "Task", "Workflow"):
        texto = " ".join(str(ti.get(k, "")) for k in ("description", "prompt", "script"))[:6000]
        if not VERBOS.search(texto):
            return 0
    else:
        return 0
    marca = _marca(cwd)
    if os.path.exists(marca) and not os.path.islink(marca) and time.time() - os.path.getmtime(marca) < TTL:
        return 0
    r = subprocess.run([sys.executable, os.path.join(AQUI, "herramientas-para.py"), "--solo-recetas", texto[:1500]],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10, cwd=cwd)
    if "══ RECETAS" not in r.stdout:
        return 0  # sin receta para esto: no se molesta
    try:
        _escribir_marca(marca)
    except OSError:
        pass
    sys.stderr.write("⛔ Regla 22 del método — ya hay una receta para lo que vas a construir. Es un freno de UNA vez "
                     "(no vuelve en 4 h en esta carpeta): leela, aplicala (los subagentes NO heredan skills: "
                     "nombralas en SU prompt) y reintentá la misma acción.\n\n" + r.stdout[:5500])
    return 2


def _escribir_marca(ruta):
    """F9 (security check 0.35.0): la marca vive en una carpeta temporal compartida con nombre predecible. Se abre con O_NOFOLLOW y permisos 0600:
    si alguien dejó ahí un enlace simbólico, la escritura falla en vez de pisar el archivo al que apunta."""
    fd = os.open(ruta, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(str(time.time()))


def _marca(cwd):
    import hashlib
    h = hashlib.sha1(os.path.realpath(cwd).encode()).hexdigest()[:12]
    uid = os.getuid() if hasattr(os, "getuid") else "u"
    base = os.environ.get("TMPDIR", "/tmp") if os.name != "nt" else os.environ.get("TEMP", ".")
    return os.path.join(base, f"consulta-ecosistema-{uid}-{h}")


try:
    sys.exit(main())
except SystemExit:
    raise
except Exception:
    sys.exit(0)
