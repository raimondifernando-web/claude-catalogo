#!/usr/bin/env python3
"""Cierre fijo cuando una sesión primaria recibe notas de sesiones hijas (metodo 0.51.1).

Problema: cada nota de una hija abre un turno nuevo y la primaria contestaba con varios mensajes seguidos, largos y con jerga;
la persona se marea. Aquí: (a) `entrada` (hook UserPromptSubmit) detecta que el mensaje es una nota de hija e inyecta la orden
de contestar con UN solo mensaje final de forma fija; (b) `salida` (hook Stop) verifica ese mensaje y, si falta el molde, pide
reescribirlo UNA vez. No depende de que el modelo «se acuerde»: lo inyecta y lo comprueba el programa.

Molde (negritas, no títulos):  **Resumen:** · **Mi sugerencia:** · **Qué tenés que decidir vos:** (o «Nada, no tenés que hacer nada.»).
Si todavía trabajan otras hijas de esta sesión, el molde es UNA línea corta («⏳ Llegó lo de …; falta …»).

Solo LEE el disco de la app (claude-code-sessions/*/*/local_*.json) y el transcript; escribe solo su estado en
<config de Claude>/state/cierre-hijas/ (marca por sesión + registro). Sin red. Nada con nombres de personas.
Disparador: automático (hooks UserPromptSubmit y Stop del plugin metodo, hooks/hooks.json). Apagar: variable CIERRE_HIJAS=0
o el archivo <config de Claude>/metodo/cierre-hijas.apagado.
"""
import glob
import hashlib
import json
import os
import re
import sys
import time

NOTA = re.compile(r"you started \((local_[0-9a-f-]+)\)\s+finished a turn|side-sessions-event", re.I)
TITULO = re.compile(r'The session "(.+?)" you started', re.S)
ID_LOCAL = re.compile(r"local_[0-9a-f]{8}-[0-9a-f-]{27}")
VIGENCIA_S = 30 * 60        # una marca armada por `entrada` vale 30 min
HIJA_ACTIVA_S = 20 * 60     # una hija sin resumen de turno y con actividad más nueva que esto se cuenta como «trabajando»
TOPE_PALABRAS = 120         # el molde pide ≤ 70; el verificador solo corrige si se pasa de esto (el aviso ⚠ no cuenta)
ETIQUETAS = (r"resumen\s*:", r"sugerencia\s*:", r"decidir\s+vos\s*:")


def base():
    return os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude")


def apagado():
    return os.environ.get("CIERRE_HIJAS") == "0" or os.path.exists(os.path.join(base(), "metodo", "cierre-hijas.apagado"))


def estado_dir():
    d = os.path.join(base(), "state", "cierre-hijas")
    os.makedirs(d, exist_ok=True)
    return d


def seguro(s):
    return re.sub(r"[^0-9A-Za-z_-]", "_", s or "x")[:80]


def registrar(**kw):
    """Una línea por intervención (mide cuántas veces el verificador tuvo que corregir)."""
    try:
        kw["t"] = int(time.time())
        with open(os.path.join(estado_dir(), "registro.jsonl"), "a", encoding="utf-8") as fh:
            fh.write(json.dumps(kw, ensure_ascii=False) + "\n")
    except OSError:
        pass


def texto_de(msg):
    c = (msg or {}).get("content")
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        return " ".join(x.get("text", "") for x in c if isinstance(x, dict) and x.get("type") == "text")
    return ""


def es_humano(texto):
    t = (texto or "").lstrip()
    return bool(t) and not t.startswith("<") and not t.startswith("[SYSTEM") and not NOTA.search(t)


def titulo_y_id(texto):
    m = TITULO.search(texto)
    i = ID_LOCAL.search(texto)
    return (m.group(1).strip() if m else None, i.group(0) if i else None)


def tanda(transcript, prompt_actual):
    """Notas de hijas desde el último mensaje HUMANO: [(título, id)]. Incluye la actual (el transcript puede ir atrasado)."""
    notas = []
    try:
        with open(transcript, encoding="utf-8") as fh:
            lineas = fh.read().splitlines()
    except (OSError, TypeError, UnicodeDecodeError):
        lineas = []
    previas = []
    for ln in reversed(lineas):
        try:
            o = json.loads(ln)
        except ValueError:
            continue
        if o.get("type") != "user" or o.get("isSidechain"):
            continue
        t = texto_de(o.get("message"))
        if not t.strip() or o.get("isMeta") or t.lstrip().startswith("Stop hook feedback"):
            continue                # el aviso del propio verificador (Stop) entra al transcript como mensaje «meta»: no corta la tanda
        if NOTA.search(t):
            previas.append(titulo_y_id(t))
        elif es_humano(t):
            break
    previas.reverse()
    actual = titulo_y_id(prompt_actual)
    if not any(p[1] and p[1] == actual[1] for p in previas) and not (actual[1] is None and previas and previas[-1][0] == actual[0]):
        previas.append(actual)
    return previas


def carpeta_sesiones():
    h = os.path.expanduser("~")
    for c in (os.environ.get("CLAUDE_SESIONES_DIR", ""), os.path.join(os.environ.get("APPDATA", ""), "Claude", "claude-code-sessions"),
              os.path.join(h, "Library", "Application Support", "Claude", "claude-code-sessions"),
              os.path.join(h, ".config", "Claude", "claude-code-sessions")):
        if c and os.path.isdir(c):
            return c
    return None


def hijas_trabajando(cli_id, ya_llegaron):
    """Hijas vivas de ESTA sesión que todavía no entregaron nota: [título]. Medido en el disco de la app; aproximado."""
    raiz = carpeta_sesiones()
    if not raiz or not cli_id:
        return []
    ses = []
    for f in glob.glob(os.path.join(raiz, "*", "*", "local_*.json")):
        try:
            with open(f, encoding="utf-8") as fh:
                d = json.load(fh)
        except (OSError, ValueError):
            continue
        if d.get("sessionId"):
            ses.append(d)
    yo = next((s for s in ses if s.get("cliSessionId") == cli_id), None)
    if not yo:
        return []
    ahora = time.time() * 1000
    out = []
    for s in ses:
        sf = s.get("spawnedFrom")
        if not (isinstance(sf, dict) and sf.get("sessionId") == yo["sessionId"]):
            continue
        if s.get("isArchived") or s.get("lineageDetached") or s["sessionId"] in ya_llegaron:
            continue
        resumen_listo = bool(s.get("postTurnSummary")) and s.get("postTurnSummaryFor") == s.get("lastAssistantUuid")
        reciente = (ahora - (s.get("lastActivityAt") or 0)) < HIJA_ACTIVA_S * 1000
        if reciente and not resumen_listo:
            out.append(s.get("title") or s["sessionId"])
    return out


def comillas(xs):
    return ", ".join("«%s»" % x for x in xs if x)


def orden(llegaron, faltan):
    ya = comillas([t for t, _ in llegaron])
    if faltan:
        return (
            "NOTA DE SESIÓN HIJA (la n.º %d desde el último mensaje de la persona: %s). Todavía trabajan: %s.\n"
            "Contestá con UNA sola línea de hasta 30 palabras, sin tablas ni listas ni títulos, con este molde: "
            "«⏳ Llegó lo de «<hija>». Falta(n) «<hija>»; por ahora no tenés que decidir nada.» Sin texto entre herramientas: si necesitás "
            "verificar algo, hacelo callado y escribí solo el mensaje final. Excepciones: (1) si la nota trae un aviso de plata, datos o algo "
            "irreversible, ponelo antes, en una línea que empiece con ⚠; (2) si trae una decisión de la persona que no puede esperar a las demás, "
            "usá el molde completo (**Resumen:** / **Mi sugerencia:** / **Qué tenés que decidir vos:**)."
            % (len(llegaron), ya, comillas(faltan)))
    return (
        "NOTA DE SESIÓN HIJA — ES LA ÚLTIMA DE LA TANDA (llegaron %d desde el último mensaje de la persona: %s). Cerrá con UN solo mensaje final "
        "que cubra TODAS las notas juntas, no una por una. Nada de texto entre herramientas (si verificás algo, hacelo callado). "
        "Molde EXACTO, en negritas, sin títulos ni tablas, 70 palabras como tope en total:\n"
        "**Resumen:** qué pasó, 2-3 líneas, sin jerga (nada de hashes, números de PR, «main», «commit», rutas ni nombres de herramientas).\n"
        "**Mi sugerencia:** una sola.\n"
        "**Qué tenés que decidir vos:** una pregunta, con tu recomendación; si no hay nada, escribí «Nada, no tenés que hacer nada.»\n"
        "Si hace falta detalle, guardalo en un archivo y nombralo en una frase. Si hay un aviso de plata, datos o algo irreversible, va ANTES "
        "en una línea que empiece con ⚠ (nunca se recorta)." % (len(llegaron), ya))


def entrada(datos):
    prompt = datos.get("prompt") or ""
    sid = seguro(datos.get("session_id"))
    marca = os.path.join(estado_dir(), "armado-%s.json" % sid)
    if not NOTA.search(prompt):
        try:
            os.remove(marca)        # llegó un mensaje de la persona: el verificador ya no aplica a este turno
        except OSError:
            pass
        return 0
    huella = hashlib.sha1(prompt.encode("utf-8", "replace")).hexdigest()
    try:
        with open(marca, encoding="utf-8") as fh:
            previa = json.load(fh)
        if previa.get("huella") == huella and time.time() - previa.get("t", 0) < 120:
            return 0                # la segunda copia del hook (ajustes + plugin) no repite la orden
    except (OSError, ValueError):
        pass
    llegaron = tanda(datos.get("transcript_path"), prompt)
    faltan = hijas_trabajando(datos.get("session_id"), {i for _, i in llegaron if i})
    tmp = marca + ".%d.tmp" % os.getpid()
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump({"huella": huella, "t": time.time(), "faltan": len(faltan), "llegaron": len(llegaron)}, fh)
    os.replace(tmp, marca)
    registrar(ev="entrada", sesion=sid, llegaron=len(llegaron), faltan=len(faltan))
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": orden(llegaron, faltan)}}, ensure_ascii=False))
    return 0


def cumple(texto, faltan):
    t = texto or ""
    sin_aviso = "\n".join(l for l in t.splitlines() if "⚠" not in l).strip()   # el aviso de plata/datos/irreversible va antes y no cuenta
    palabras = len(sin_aviso.split())
    if all(re.search(e, sin_aviso, re.I) for e in ETIQUETAS):
        return palabras <= TOPE_PALABRAS
    return bool(faltan) and 0 < palabras <= 40 and "\n\n" not in sin_aviso


def salida(datos):
    if datos.get("stop_hook_active"):
        return 0
    sid = seguro(datos.get("session_id"))
    marca = os.path.join(estado_dir(), "armado-%s.json" % sid)
    reclamo = marca + ".%d.claim" % os.getpid()
    try:
        os.rename(marca, reclamo)   # atómico: si dos copias del hook corren a la vez, solo una verifica
    except OSError:
        return 0
    try:
        with open(reclamo, encoding="utf-8") as fh:
            m = json.load(fh)
    finally:
        try:
            os.remove(reclamo)
        except OSError:
            pass
    if time.time() - m.get("t", 0) > VIGENCIA_S:
        return 0
    faltan = m.get("faltan", 0)
    ok = cumple(datos.get("last_assistant_message"), faltan)
    registrar(ev="salida", sesion=sid, ok=ok, palabras=len((datos.get("last_assistant_message") or "").split()))
    if ok:
        return 0
    razon = (
        "Falta el cierre fijo para la nota de hija. Reescribí AHORA tu mensaje final como UN solo mensaje, sin disculpas ni explicar que lo "
        "reescribís. " + ("Todavía trabajan otras hijas: UNA línea de hasta 30 palabras («⏳ Llegó lo de «X». Falta(n) «Y»; por ahora no tenés que decidir nada.»). "
                          if faltan else
                          "Molde exacto, 70 palabras como tope: **Resumen:** (2-3 líneas, sin jerga) / **Mi sugerencia:** (una) / "
                          "**Qué tenés que decidir vos:** (una pregunta con tu recomendación, o «Nada, no tenés que hacer nada.»). ")
        + "Un aviso de plata, datos o algo irreversible va antes, en una línea con ⚠.")
    print(json.dumps({"decision": "block", "reason": razon}, ensure_ascii=False))
    return 0


def main():
    if len(sys.argv) < 2 or apagado():
        return 0
    try:
        datos = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        return 0
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    return {"entrada": entrada, "salida": salida}.get(sys.argv[1], lambda d: 0)(datos)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)     # un fallo del aviso nunca debe trabar la sesión
