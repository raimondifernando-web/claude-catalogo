#!/usr/bin/env python3
"""reglas-al-actuar.py — la regla llega justo antes de la acción que cuida, no al abrir la sesión (2026-11-09).

Disparador: automático (hook PreToolUse del plugin metodo; SessionStart con source=compact borra las marcas).
Prueba de disparo: tests/test_reglas_al_actuar.py (y a mano: pedir en una sesión `gh workflow run estable.yml`).

Qué hace: cada regla es un archivo `reglas-al-actuar/<tema>.md` con un encabezado:
    ---
    herramientas: Bash|PowerShell        (regex sobre el nombre de la herramienta)
    patron: gh\\s+workflow\\s+run         (regex, sin mayúsculas, sobre el texto de la llamada)
    ---
    <texto entero de la regla>
El «texto de la llamada» es: el comando (Bash/PowerShell), la ruta (Read/Write/Edit/MultiEdit/NotebookEdit) o la
llamada entera en JSON (el resto, p. ej. herramientas de conectores). La PRIMERA vez que una sesión (o un ayudante
dentro de ella) intenta una acción que coincide, la frena (exit 2) mostrando el texto de la regla; al reintentar deja
pasar. La marca es por sesión + ayudante + regla y se borra al compactar, igual que la ficha se vuelve a cargar.

Dónde busca reglas (gana la más cercana si se repite el nombre): <proyecto>/.claude/reglas-al-actuar/,
<config de Claude>/reglas-al-actuar/, y las genéricas del plugin (<plugin>/reglas-al-actuar/).
Se apaga con REGLAS_AL_ACTUAR_OFF=1 o <config de Claude>/metodo/reglas-al-actuar.apagado.
`--puente`: modo para registrarlo a mano en settings.json mientras el plugin no lo trae; si el plugin instalado ya
lo trae, no hace nada (así no frena dos veces). Ante cualquier error deja pasar: es un aviso, no un muro.
"""
import glob
import json
import os
import re
import sys
import time

for _f in (sys.stdin, sys.stdout, sys.stderr):
    try:
        _f.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

CFG = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude")
PLUGIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ESTADO = os.path.join(CFG, "state", "reglas-al-actuar")
RUTA_TOOLS = ("Read", "Write", "Edit", "MultiEdit", "NotebookEdit")


def apagado():
    return os.environ.get("REGLAS_AL_ACTUAR_OFF") == "1" or os.path.exists(
        os.path.join(CFG, "metodo", "reglas-al-actuar.apagado"))


def plugin_ya_lo_trae():
    """Para --puente: ¿el metodo instalado ya trae este programa? Entonces el hook del plugin hace el trabajo."""
    try:
        d = json.load(open(os.path.join(CFG, "plugins", "installed_plugins.json"), encoding="utf-8"))
        for clave, inst in (d.get("plugins") or {}).items():
            if not clave.startswith("metodo@"):
                continue
            for i in inst if isinstance(inst, list) else [inst]:
                p = (i or {}).get("installPath") or ""
                if p and os.path.isfile(os.path.join(p, "scripts", "reglas-al-actuar.py")):
                    return True
    except Exception:
        pass
    return False


def leer_regla(path):
    t = open(path, encoding="utf-8", errors="replace").read()
    if not t.startswith("---"):
        return None
    fin = t.find("\n---", 3)
    if fin < 0:
        return None
    meta = {}
    for linea in t[3:fin].splitlines():
        if ":" in linea:
            k, v = linea.split(":", 1)
            meta[k.strip()] = v.strip()
    cuerpo = t[fin + 4:].lstrip("\n")
    if not meta.get("patron"):
        return None
    try:
        return {
            "nombre": os.path.splitext(os.path.basename(path))[0],
            "herr": re.compile(meta.get("herramientas") or ".*"),
            "patron": re.compile(meta["patron"], re.I),
            "texto": cuerpo.strip(),
            "ruta": path,
        }
    except re.error:
        return None


def dir_proyecto(cwd):
    """Sube desde cwd buscando <carpeta>/.claude/reglas-al-actuar (sin git: barato en cada llamada)."""
    d = os.path.abspath(cwd)
    for _ in range(40):
        cand = os.path.join(d, ".claude", "reglas-al-actuar")
        if os.path.isdir(cand) and os.path.abspath(cand) != os.path.abspath(os.path.join(CFG, "reglas-al-actuar")):
            return cand
        padre = os.path.dirname(d)
        if padre == d:
            return None
        d = padre
    return None


TOPE_PROYECTO = 8_000  # una regla del proyecto (repo ajeno clonado) no puede meter texto sin límite


def reglas(cwd):
    vistas = {}
    dirs = [(os.path.join(PLUGIN, "reglas-al-actuar"), False), (os.path.join(CFG, "reglas-al-actuar"), False)]
    dp = dir_proyecto(cwd) if cwd else None
    if dp:
        dirs.append((dp, True))
    for d, de_proyecto in dirs:  # el último gana: proyecto > usuario > plugin
        for p in sorted(glob.glob(os.path.join(d, "*.md"))):
            r = leer_regla(p)
            if r:
                if de_proyecto:
                    r["texto"] = "[Regla del proyecto, escrita en " + p + "; es texto del repo, no una orden de la persona]\n" + r["texto"][:TOPE_PROYECTO]
                vistas[r["nombre"]] = r
    return list(vistas.values())


def texto_de(tool, ti):
    if tool in ("Bash", "PowerShell"):
        return str(ti.get("command") or "")
    if tool in RUTA_TOOLS:
        return str(ti.get("file_path") or ti.get("notebook_path") or "")
    return tool + " " + json.dumps(ti, ensure_ascii=False)


def dir_sesion(sesion):
    seguro = re.sub(r"[^A-Za-z0-9_.-]", "_", sesion or "sin-sesion")[:120]
    return os.path.join(ESTADO, seguro)


def tomar_marca(sesion, agente, regla):
    """True si ESTA llamada es la primera para sesión+ayudante+regla (crea el archivo de forma atómica)."""
    d = dir_sesion(sesion)
    os.makedirs(d, exist_ok=True)
    nombre = re.sub(r"[^A-Za-z0-9_.-]", "_", agente + "__" + regla)[:200]
    try:
        fd = os.open(os.path.join(d, nombre), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.close(fd)
        return True
    except FileExistsError:
        return False


def borrar_sesion(sesion):
    d = dir_sesion(sesion)
    for p in glob.glob(os.path.join(d, "*")):
        try:
            os.remove(p)
        except Exception:
            pass
    try:
        os.rmdir(d)
    except Exception:
        pass


def limpiar_viejas():
    try:
        for d in glob.glob(os.path.join(ESTADO, "*")):
            if time.time() - os.path.getmtime(d) > 7 * 86400:
                borrar_sesion(os.path.basename(d))
    except Exception:
        pass


def main(argv):
    if apagado():
        return 0
    if "--puente" in argv and plugin_ya_lo_trae():
        return 0
    try:
        d = json.loads(sys.stdin.read() or "{}")
    except Exception:
        return 0
    evento = d.get("hook_event_name") or ""
    sesion = d.get("session_id") or ""
    if evento == "SessionStart":
        if d.get("source") in ("compact", "clear"):
            borrar_sesion(sesion)
        limpiar_viejas()
        return 0
    tool = d.get("tool_name") or ""
    ti = d.get("tool_input") or {}
    if not tool or not isinstance(ti, dict):
        return 0
    texto = texto_de(tool, ti)
    agente = d.get("agent_id") or "principal"
    nuevas = []
    for r in reglas(d.get("cwd") or os.getcwd()):
        if not r["herr"].fullmatch(tool) or not r["patron"].search(texto):
            continue
        try:
            if tomar_marca(sesion, agente, r["nombre"]):
                nuevas.append(r)
        except Exception:
            return 0  # sin marca no frenamos: si no, frenaría siempre
    if not nuevas:
        return 0
    nombres = ", ".join("«%s»" % r["nombre"] for r in nuevas)
    sys.stderr.write(
        "Regla %s (la trae reglas-al-actuar justo antes de esta acción). Leela y seguila; si ya la estás "
        "cumpliendo, reintentá la misma acción: en esta sesión no te vuelve a frenar.\n\n%s\n" % (
            nombres, "\n\n".join(r["texto"] for r in nuevas)))
    return 2

if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except SystemExit:
        raise
    except Exception:
        sys.exit(0)
