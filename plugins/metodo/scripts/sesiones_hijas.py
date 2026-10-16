"""sesiones_hijas — lo que arrancar-check.py y cerrar-check.py miden sobre las sesiones hijas (metodo 0.44.0).

SOLO LEE los datos que la app de escritorio guarda en disco (claude-code-sessions/*/*/local_*.json) y git. Nunca archiva nada:
archivar lo hace la sesión con `archive_session`, sin preguntarle a la persona. Por qué existe: un texto de arranque (REANUDAR)
que dice «ofrecer archivar estas sesiones» afirma un estado que cambia, y la persona terminaba decidiendo algo que no es suyo.
El estado real se mide acá; el REANUDAR no lo afirma.
"""
import glob
import json
import os
import re
import subprocess
import time

UUID = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
VIEJO_DIAS = 14
FRASE_ARCHIVAR = re.compile(
    r"ofrecer\s+archivar|archivarlas?\b|siguen\s+en\s+la\s+barra\s+lateral|(?:solo|sólo)\s+con\s+el\s+s[ií]\s+de|¿(?:las\s+)?archivo", re.I)


def carpeta_sesiones():
    h = os.path.expanduser("~")
    for c in (os.environ.get("CLAUDE_SESIONES_DIR", ""), os.path.join(os.environ.get("APPDATA", ""), "Claude", "claude-code-sessions"),
              os.path.join(h, "Library", "Application Support", "Claude", "claude-code-sessions"),
              os.path.join(h, ".config", "Claude", "claude-code-sessions")):
        if c and os.path.isdir(c):
            return c
    return None


def cargar(raiz=None):
    """Todas las sesiones de la app (archivadas incluidas). Lista vacía si no hay app."""
    raiz = raiz or carpeta_sesiones()
    ses = []
    for f in glob.glob(os.path.join(raiz, "*", "*", "local_*.json")) if raiz else []:
        try:
            with open(f, encoding="utf-8") as fh:
                d = json.load(fh)
        except (OSError, ValueError):
            continue
        if d.get("sessionId"):
            ses.append(d)
    return ses


def mi_sesion(ses):
    """La sesión actual: CLAUDE_CODE_SESSION_ID / CLAUDE_SESSION_ID; si no se sabe, None (no se adivina)."""
    por_cli = {s.get("cliSessionId"): s for s in ses}
    for var in ("CLAUDE_CODE_SESSION_ID", "CLAUDE_SESSION_ID"):
        v = os.environ.get(var)
        if v and v in por_cli:
            return por_cli[v]
    return None


def padre_de(s):
    sf = s.get("spawnedFrom")
    return sf.get("sessionId") if isinstance(sf, dict) else (sf if isinstance(sf, str) else None)


def hijas_de(sid, ses, excluir=()):
    """Descendientes vivas (hijas, nietas…) de `sid`: sin detach y sin PR abierto propio. `excluir` saca a una sesión y a su rama (p. ej. la actual)."""
    out, vistos, cola = [], {sid, *excluir}, [sid]
    while cola:
        p = cola.pop(0)
        for s in ses:
            if padre_de(s) == p and s["sessionId"] not in vistos and not s.get("lineageDetached") and not s.get("isArchived") \
                    and not any(isinstance(x, dict) and str(x.get("state", "")).upper() in ("OPEN", "DRAFT") for x in s.get("prs") or []):
                vistos.add(s["sessionId"])
                out.append(s)
                cola.append(s["sessionId"])
    return out


# Caché de herramientas que no es trabajo de nadie (C127): una copia propia que solo tiene esto cuenta como limpia.
RUIDO = re.compile(r"(^|/)(\.omc|__pycache__|\.pytest_cache|node_modules)(/|$)|(^|/)\.DS_Store$")

# Qué hace la sesión SOLA con cada pendiente de una hija (C127): nada de esto es una pregunta para la persona.
ACCIONES = {
    "sin_guardar": 'SendMessage a la hija: «guardá (commit) lo tuyo, subí tu rama y avisame "listo"»; esperá a que termine su turno',
    "informe_debido": "esperá a que entregue (la app te avisa cuando termina su turno) o pedíselo con SendMessage; si tarda, ScheduleWakeup, nunca una tarea para la persona",
    "informe_sin_leer": "leé su informe (get_session) y pasá lo que sirva a PENDIENTES.md; recién ahí archivá",
}


def bloqueos_det(h, ses):
    """[(tipo, texto)]: motivos por los que NO conviene archivar `h` todavía. Se resuelven solos (ACCIONES)."""
    out = []
    dias = (time.time() * 1000 - (h.get("lastActivityAt") or time.time() * 1000)) / 86400000
    if h.get("sideSessionReportOwed") and dias <= VIEJO_DIAS:
        out.append(("informe_debido", "todavía no entregó su informe"))
    padre = next((s for s in ses if s["sessionId"] == padre_de(h)), None)
    if padre and any(n.get("sessionId") == h["sessionId"] for n in padre.get("queuedSideSessionNotes") or []):
        out.append(("informe_sin_leer", "su informe llegó pero nadie lo leyó"))
    wt = h.get("worktreePath")
    if wt and os.path.isdir(wt):
        try:
            st = subprocess.run(["git", "-C", wt, "--no-optional-locks", "status", "--short", "-uall"], capture_output=True, text=True,
                                encoding="utf-8", errors="replace", timeout=20).stdout
        except Exception:
            st = ""
        sucios = [l for l in st.splitlines() if l.strip() and not RUIDO.search(l.strip().split(None, 1)[-1].split(" -> ")[-1].strip('"'))]
        if sucios:
            out.append(("sin_guardar", f"su copia propia tiene {len(sucios)} cambio(s) sin guardar ({wt})"))
    return out


def bloqueos_de(h, ses):
    return [t for _k, t in bloqueos_det(h, ses)]


def acciones_de(h, ses):
    """[«<qué> → <hacelo vos>»] para que la sesión resuelva sola lo que frena a `h`."""
    return [f"{t} → {ACCIONES[k]}" for k, t in bloqueos_det(h, ses)]


def pistas_archivar(s):
    """Por qué la app puede rechazar archivar `s` aunque no tenga trabajo pendiente, medido en el disco. [] = nada visible."""
    out = []
    if s.get("steeredByRemoteClient"):
        out.append("tiene un cliente remoto abierto (otra pantalla la está usando): cerrá esa ventana o esperá")
    if s.get("queuedSideSessionNotes"):
        out.append("tiene un informe en cola sin leer: leelo (get_session) y reintentá")
    return out


def clasificar(sesiones, ses):
    """(libres, retenidas): libres = sin trabajo ni informe pendiente → se archivan sin preguntar."""
    libres, ret = [], []
    for h in sesiones:
        b = bloqueos_de(h, ses)
        (ret if b else libres).append((h, b))
    return libres, ret


def reanudar_afirma_archivado(texto):
    return [m.group(0) for m in FRASE_ARCHIVAR.finditer(texto or "")]


def citadas_en(texto, ses, excluir=()):
    """Sesiones VIVAS cuyo id aparece en el texto. Las ya archivadas no se mencionan."""
    ids = set(re.findall(r"local_" + UUID, texto or ""))
    return [s for s in ses if s["sessionId"] in ids and not s.get("isArchived") and s["sessionId"] not in excluir]
