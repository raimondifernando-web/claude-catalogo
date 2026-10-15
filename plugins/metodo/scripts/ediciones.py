#!/usr/bin/env python3
"""ediciones.py — quién tocó qué: registro por sesión + clasificador «tuyo / ajeno» para cerrar-check.
Disparador: automático (hook PostToolUse de metodo/hooks/hooks.json anota cada archivo que edita una sesión); lo lee cerrar-check en cada /cerrar.

Para qué: con varias sesiones a la vez sobre las mismas carpetas, cerrar-check frenaba (✗) por archivos sin guardar que eran
de OTRA sesión, y esa otra sesión seguía trabajando: el cierre de una frenaba el de todas. Con este registro cada sesión sabe
qué archivos tocó ella: lo suyo sin guardar sigue frenando; lo de otra sesión se avisa («•») y no frena.

Registro: <config de Claude>/state/ediciones/<id de sesión>.jsonl, una línea por edición: {"t": segundos, "p": ruta, "h": herramienta}.
Vive fuera de cualquier repositorio (no se versiona). Cada sesión escribe SOLO su archivo: nadie pisa a nadie. Se borra lo de más de 14 días.
Qué anota: Edit/Write/MultiEdit/NotebookEdit (la ruta exacta) y Bash (los archivos sin guardar que el comando nombra y que
cambiaron mientras corría). No anota lo que un comando cambia sin nombrarlo (p. ej. un script que arma la ruta por dentro).

Cómo se clasifica un archivo versionado con cambios sin guardar (CONSERVADOR: ante la duda es TUYO y frena):
  1. lo anotó esta sesión                                                → tuyo
  2. cambió por última vez ANTES de abrirse esta sesión                  → ajeno (no pudiste ser vos)
  3. lo anotó otra sesión y nadie lo tocó después de esa anotación       → ajeno
  4. cualquier otro caso (sin dueño conocido; p. ej. un comando que el registro no vio) → tuyo
  Lo que sabés que no es tuyo y el registro no vio se declara a mano: cerrar-check --ajeno <ruta>.
Si no se sabe cuál es esta sesión (falta CLAUDE_CODE_SESSION_ID), todo cuenta como tuyo: igual que antes de existir esto.

Uso (lo llama el hook, no una persona):  ediciones.py registrar   (lee el JSON del hook por la entrada estándar; nunca imprime ni frena)
Python 3.9+, sin dependencias."""
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime

DIAS = 14            # cuánto se guarda el registro de una sesión
TOLERANCIA = 2.0     # segundos de margen entre la fecha del archivo y la hora del aviso del hook
HERRAMIENTAS_ARCHIVO = ("Edit", "Write", "MultiEdit", "NotebookEdit")


def config_dir():
    return os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude")


def dir_registro():
    return os.path.join(config_dir(), "state", "ediciones")


def sid_valido(s):
    """El id viene de afuera (JSON del hook, entorno): se usa de nombre de archivo, así que solo letras, números, - y _."""
    return s if isinstance(s, str) and re.fullmatch(r"[A-Za-z0-9_-]{1,80}", s) else None


def sid_actual():
    for var in ("CLAUDE_CODE_SESSION_ID", "CLAUDE_SESSION_ID"):
        s = sid_valido(os.environ.get(var))
        if s:
            return s
    return None


def _norm(p):
    return os.path.normcase(os.path.realpath(p))


def _git(repo, *a):
    try:
        r = subprocess.run(["git", "-C", repo, *a], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10)
        return r.stdout if r.returncode == 0 else None
    except Exception:
        return None


def inicio_sesion(sid):
    """Cuándo abrió esta sesión (segundos), leído de la primera línea con fecha de su transcripción. None si no se encuentra."""
    import glob
    for f in glob.glob(os.path.join(config_dir(), "projects", "*", sid + ".jsonl")):
        try:
            with open(f, encoding="utf-8", errors="replace") as fh:
                for _, linea in zip(range(30), fh):
                    try:
                        ts = json.loads(linea).get("timestamp")
                    except ValueError:
                        continue
                    if isinstance(ts, str):
                        return datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
        except (OSError, ValueError):
            continue
    return None


# ---------- escribir (lo llama el hook) ----------

def _sucios(repo):
    """Archivos versionados con cambios sin guardar de ese repo, como rutas absolutas."""
    top = (_git(repo, "rev-parse", "--show-toplevel") or "").strip()
    out = _git(repo, "status", "--porcelain=v1", "-z", "-uno")
    if not top or out is None:
        return []
    partes, res, i = out.split("\0"), [], 0
    while i < len(partes):
        e = partes[i]
        i += 1
        if len(e) < 4:
            continue
        if e[0] in "RC":
            i += 1  # con -z, tras un renombrado viene la ruta de origen
        res.append(os.path.join(top, e[3:]))
    return res


def _tocados_por_bash(cmd, cwd, desde, hasta):
    repos = {_norm(r): r for r in (cwd, config_dir()) if os.path.isdir(r)}
    vistos, res = set(), []
    for r in repos.values():
        for f in _sucios(r):
            n = _norm(f)
            nombre = os.path.basename(f)
            if n in vistos or len(nombre) < 3 or nombre not in cmd:
                continue
            vistos.add(n)
            try:
                m = os.path.getmtime(f)
            except OSError:
                m = None  # borrado: si el comando lo nombra, se anota
            if m is None or desde - TOLERANCIA <= m <= hasta + TOLERANCIA:
                res.append(f)
    return res


def registrar(entrada):
    """Anota en el archivo de la sesión lo que acaba de tocar. Nunca imprime ni lanza error."""
    sid = sid_valido(entrada.get("session_id"))
    if not sid:
        return
    ti = entrada.get("tool_input") or {}
    cwd = entrada.get("cwd") if isinstance(entrada.get("cwd"), str) else os.getcwd()
    herr = entrada.get("tool_name") or ""
    ahora = time.time()
    d = dir_registro()
    os.makedirs(d, exist_ok=True)
    marca = os.path.join(d, sid + ".t")
    try:
        previo = float(open(marca).read())
    except (OSError, ValueError):
        previo = None
    rutas = []
    if herr in HERRAMIENTAS_ARCHIVO:
        p = ti.get("file_path") or ti.get("notebook_path")
        if isinstance(p, str) and p:
            rutas.append(os.path.join(cwd, p))
    elif herr == "Bash" and isinstance(ti.get("command"), str):
        desde = previo if previo else max(inicio_sesion(sid) or 0, ahora - 600)
        rutas += _tocados_por_bash(ti["command"], cwd, desde, ahora)
    if rutas:
        with open(os.path.join(d, sid + ".jsonl"), "a", encoding="utf-8") as fh:
            for p in rutas:
                fh.write(json.dumps({"t": round(ahora, 3), "p": _norm(p), "h": herr}, ensure_ascii=False) + "\n")
    with open(marca, "w") as fh:
        fh.write(str(ahora))
    _limpiar(d, ahora)


def _limpiar(d, ahora):
    """Una vez por día borra los registros de sesiones sin actividad hace más de DIAS días."""
    tope = os.path.join(d, ".limpieza")
    try:
        if ahora - os.path.getmtime(tope) < 86400:
            return
    except OSError:
        pass
    for f in os.listdir(d):
        p = os.path.join(d, f)
        try:
            if f != ".limpieza" and ahora - os.path.getmtime(p) > DIAS * 86400:
                os.remove(p)
        except OSError:
            pass
    with open(tope, "w") as fh:
        fh.write("")


# ---------- leer (lo llama cerrar-check) ----------

def _registro(ahora):
    """{ruta: {id de sesión: última vez que la anotó}} de todas las sesiones, solo de los últimos DIAS días."""
    res = {}
    d = dir_registro()
    try:
        archivos = os.listdir(d)
    except OSError:
        return res
    for f in archivos:
        if not f.endswith(".jsonl"):
            continue
        sid = f[:-6]
        try:
            with open(os.path.join(d, f), encoding="utf-8", errors="replace") as fh:
                for linea in fh:
                    try:
                        e = json.loads(linea)
                        t, p = float(e["t"]), str(e["p"])
                    except (ValueError, KeyError, TypeError):
                        continue
                    if ahora - t <= DIAS * 86400:
                        res.setdefault(p, {})[sid] = max(t, res.get(p, {}).get(sid, 0))
        except OSError:
            continue
    return res


def _hace(seg):
    m = int(seg // 60)
    return "hace menos de 1 min" if m < 1 else f"hace {m} min" if m < 120 else f"hace {m // 60} h"


def clasificar(rutas, sid, declaradas=(), nombres=None, ahora=None):
    """{ruta: ("mio" | "ajeno", motivo)}. `rutas` = absolutas; `declaradas` = las que la persona dijo a mano que no son suyas;
    `nombres` = {id de sesión: título} si se sabe (solo para mostrar). Ver la regla en el encabezado."""
    ahora = ahora or time.time()
    nombres = nombres or {}
    decl = {_norm(p) for p in declaradas}
    reg = _registro(ahora) if sid else {}
    inicio = inicio_sesion(sid) if sid else None
    res = {}
    for ruta in rutas:
        n = _norm(ruta)
        due = reg.get(n, {})
        try:
            m = os.path.getmtime(ruta)
        except OSError:
            m = None
        if n in decl:
            res[ruta] = ("ajeno", "lo declaraste ajeno a mano")
        elif not sid:
            res[ruta] = ("mio", "no sé qué sesión sos")
        elif sid in due:
            res[ruta] = ("mio", "lo editaste en esta sesión")
        elif inicio and m is not None and m < inicio - TOLERANCIA:
            res[ruta] = ("ajeno", "ya estaba sin guardar antes de abrir esta sesión")
        elif due and (m is None or m <= max(due.values()) + TOLERANCIA):
            otra, t = max(due.items(), key=lambda kv: kv[1])
            quien = f"«{nombres[otra]}»" if nombres.get(otra) else "otra sesión " + otra[:8]
            res[ruta] = ("ajeno", f"editado por {quien} {_hace(ahora - t)}")
        else:
            res[ruta] = ("mio", "sin dueño conocido")
    return res


if __name__ == "__main__":
    if sys.argv[1:2] == ["registrar"]:
        try:
            registrar(json.load(sys.stdin))
        except Exception:
            pass  # un hook que anota no puede frenar nunca el trabajo
    sys.exit(0)
