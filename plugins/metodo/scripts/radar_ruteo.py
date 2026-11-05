"""Ruteo por fila de trabajo (`radar.py ruteo <fila>`): IA, modelo y esfuerzo sin gastar IA.

Disparador: encadenado — lo llama `radar.py ruteo` (paso 6 de la Capa A de las reglas multi-IA: la sesión lo corre antes de
abrir un subagente, una sesión hija o delegar) y el freno de `radar.py recordar` lo sugiere al abrir sesiones.

La IA clasifica (fila + tres preguntas); este programa elige. Solo biblioteca estándar, sin red, sin IA. Nunca frena: si algo
se rompe devuelve la IA de la sesión con el aviso `provisorio`. Recibe el módulo `radar` (R) para reutilizar sus lectores.

Archivos locales (carpeta `metodo/`, nunca viajan): sensibles.txt («ruta | motivo»), no-entrena.txt («IA | fecha | cómo se
verificó»), herramientas.txt («nombre | tipo | filas», nombre tal cual el radar) y principal.txt (opcional, IA de la sesión).
"""
import json
import os
import time
from pathlib import Path

NIVEL_NUM = {"N1": 1, "N2": 2, "N3": 3}
NUM_NIVEL = {1: "N1", 2: "N2", 3: "N3"}
ESFUERZO_NIVEL = {"N1": "low", "N2": "medium", "N3": "high"}
VENTANA_S = 7 * 24 * 3600          # el cupo se mide contra la renovación semanal
EDAD_MAX_DATO_S = 24 * 3600        # dato de cupo con más edad que esto = sin dato
DIAS_RADAR_VIEJO = 30
SOBRA, ESCASEA = 2.0, 0.5
CLAVE_CUPO = {"Claude Code": "claude", "Codex": "codex", "Antigravity": "antigravity"}
PRINCIPAL_DEFECTO = "Claude Code"
TOPE_INVESTIGAR = {"citas": 3, "fondo": 1}


# --------------------------------------------------------------------------- #
# Archivos locales
# --------------------------------------------------------------------------- #
def _lineas(ruta):
    try:
        t = Path(ruta).read_text(encoding="utf-8")
    except Exception:
        return []
    out = []
    for l in t.splitlines():
        l = l.strip()
        if l and not l.startswith("#"):
            out.append([x.strip() for x in l.split("|")])
    return out


def leer_sensibles(base):
    """[(Path absoluto, motivo)]."""
    out = []
    for c in _lineas(Path(base) / "sensibles.txt"):
        if not (c[0].startswith("~") or os.path.isabs(c[0])):
            continue   # una ruta relativa dependería de dónde se corre el programa: se ignora
        try:
            out.append((Path(os.path.expanduser(c[0])).resolve(), c[1] if len(c) > 1 else ""))
        except Exception:
            continue
    return out


def leer_registro(base, norm):
    """Nombres normalizados de las IA con «no entrenar» registrado."""
    return {norm(c[0]) for c in _lineas(Path(base) / "no-entrena.txt") if c and c[0]}


def leer_herramientas(base, norm):
    """[(nombre, tipo, {filas})], o None si el archivo no existe."""
    ruta = Path(base) / "herramientas.txt"
    if not ruta.is_file():
        return None
    out = []
    for c in _lineas(ruta):
        if len(c) >= 3 and c[0]:
            filas = {norm(f) for f in c[2].replace(";", ",").split(",") if f.strip()}
            out.append((c[0], c[1].lower(), filas))
    return out


def carpeta_sensible(repo, sensibles):
    if not repo:
        return None
    try:
        r = Path(os.path.expanduser(str(repo))).resolve()
    except Exception:
        return None
    for ruta, motivo in sensibles:
        if r == ruta or ruta in r.parents:
            return motivo or "carpeta sensible"
    return None


# --------------------------------------------------------------------------- #
# Disponibles y cupo
# --------------------------------------------------------------------------- #
def disponibles(R):
    """Nombres exactos de las herramientas de línea de comandos presentes. `RUTEO_DISPONIBLES` (coma) las fija a mano (pruebas)."""
    fijo = os.environ.get("RUTEO_DISPONIBLES")
    if fijo is not None:
        return {x.strip() for x in fijo.split(",") if x.strip()}
    out = {PRINCIPAL_DEFECTO}
    if R._buscar_bin("codex", "RADAR_CODEX_BIN"):
        propia = os.environ.get("RADAR_CODEX_BIN", "").strip()
        home = os.environ.get("CODEX_HOME", "").strip()
        sesion = Path(home) if home and os.path.isabs(home) else Path.home() / ".codex"
        if propia or (sesion / "auth.json").is_file():
            out.add("Codex")
    if R._buscar_bin("agy", "RADAR_AGY_BIN"):
        propia = os.environ.get("RADAR_AGY_BIN", "").strip()
        estado = os.environ.get("RADAR_AGY_STATE", "").strip()
        base = Path(estado) if estado and os.path.isabs(estado) else Path.home() / ".gemini" / "antigravity-cli"
        if propia or (base / "history.jsonl").is_file():
            out.add("Antigravity")
    return out


def _cache_cupo(clave):
    cerebro = os.environ.get("CEREBRO_HOME", "").strip()
    base = Path(cerebro) if cerebro else Path.home() / ".cerebro"
    nombres = {"claude": "cupo.json", "codex": "cupo-codex.json", "antigravity": "cupo-agy.json"}
    try:
        ruta = base / nombres[clave]
        if not ruta.is_file() or ruta.stat().st_size > 65536:
            return None
        return json.loads(ruta.read_text(encoding="utf-8"))
    except Exception:
        return None


def parsear_cupo_sesion(texto, ahora=None):
    """«usado,renovación» → (usado %, epoch de renovación). Renovación: epoch, fecha ISO o «36h»/«3d». None si no se entiende."""
    ahora = time.time() if ahora is None else ahora
    try:
        usado, ren = [x.strip() for x in str(texto).split(",", 1)]
        usado = float(usado.rstrip("%"))
        if not 0 <= usado <= 100:
            return None
        if ren[-1:] in ("h", "d") and ren[:-1].replace(".", "", 1).isdigit():
            return usado, ahora + float(ren[:-1]) * (3600 if ren[-1] == "h" else 86400)
        if ren.replace(".", "", 1).isdigit():
            return usado, float(ren)
        from datetime import datetime
        return usado, datetime.fromisoformat(ren.replace("Z", "+00:00")).timestamp()
    except Exception:
        return None


def cupo_ritmo(clave, sesion=None, ahora=None):
    """{estado, usado, H}. estado: sobra | normal | escasea | agotada | sin_dato. Sin dato = falta el % o la fecha, la fecha pasó
    o el dato tiene más de 24 horas. H = (100 − usado) ÷ % de la ventana que falta."""
    ahora = time.time() if ahora is None else ahora
    usado = renueva = ts = None
    if clave == "claude" and sesion:
        usado, renueva, ts = sesion[0], sesion[1], ahora
    else:
        d = _cache_cupo(clave)
        if isinstance(d, dict):
            sub = d.get("seven_day") if isinstance(d.get("seven_day"), dict) else d
            try:
                usado, renueva, ts = float(sub.get("pct")), float(sub.get("resets_at")), float(d.get("ts"))
            except (TypeError, ValueError):
                usado = renueva = ts = None
    sin = {"estado": "sin_dato", "usado": usado, "H": None}
    if usado is None or renueva is None or ts is None or not 0 <= usado <= 100:
        return sin
    if ahora - ts > EDAD_MAX_DATO_S or renueva <= ahora:
        return sin
    falta = min(1.0, (renueva - ahora) / VENTANA_S)
    if usado >= 100:
        return {"estado": "agotada", "usado": usado, "H": 0.0}
    h = (100.0 - usado) / (100.0 * falta)
    return {"estado": "sobra" if h >= SOBRA else "escasea" if h < ESCASEA else "normal", "usado": usado, "H": round(h, 2)}


# --------------------------------------------------------------------------- #
# Fila, nivel y modelos
# --------------------------------------------------------------------------- #
def _conf(radar):
    return radar.get("ruteo_claude") or {}


def fila_producir(R, radar, texto):
    """Fila de Producir/consultar por id exacto o por palabras (lista cerrada), o None."""
    filas = [f for f in (_conf(radar).get("producir") or []) if isinstance(f, dict) and f.get("id")]
    clave = R._norm(texto).strip()
    for f in filas:
        if clave == R._norm(f["id"]):
            return f
    for f in filas:
        pal = [dict(id=f["id"], nivel="sonnet", esfuerzo="low", palabras=f.get("palabras") or [])]
        if R.fila_para({"ruteo_claude": {"tareas": pal}}, texto):
            return f
    return None


def etapa_de(R, radar, texto):
    """Etapa por id o nombre exacto; si no, de las que calzan por palabras, la de nivel base más alto (ante la duda, más cuidado)."""
    etapas = [e for e in R.etapas_validas(radar) if e.get("nivel_base") in NIVEL_NUM]
    clave = R._norm(texto).strip()
    for e in etapas:
        if clave in (R._norm(e["id"]), R._norm(e.get("nombre", ""))):
            return e
    mejor = None
    for e in etapas:
        pal = [dict(id=e["id"], nivel="sonnet", esfuerzo="low", palabras=e.get("palabras") or [])]
        if R.fila_para({"ruteo_claude": {"tareas": pal}}, texto) and (mejor is None or NIVEL_NUM[e["nivel_base"]] > NIVEL_NUM[mejor["nivel_base"]]):
            mejor = e
    return mejor


def nivel_de(base, si, subir=False):
    """N1→(S≤1 N1, S≥2 N2) · N2→(S≤1 N2, S≥2 N3) · N3→(S=0 N2, S≥1 N3); --subir suma uno (tope N3)."""
    b = NIVEL_NUM[base]
    si = max(0, min(3, int(si)))
    n = (2 if si >= 2 else 1) if b == 1 else (3 if si >= 2 else 2) if b == 2 else (2 if si == 0 else 3)
    if subir:
        n += 1
    return NUM_NIVEL[min(n, 3)]


def modelo_de(radar, ia, nivel):
    """Modelo de la IA para ese nivel según `ruteo_claude.niveles`; '—' si no hay dato."""
    tabla = (_conf(radar).get("niveles") or {}).get(ia) or {}
    return str(tabla.get(nivel) or "—")


# --------------------------------------------------------------------------- #
# Resolución
# --------------------------------------------------------------------------- #
def _linea(r):
    base = "Ruteo: %s/%s/%s porque %s" % (r["ia"], r["modelo"], r["esfuerzo"], r["motivo"])
    if r.get("como"):
        base += " · cómo: %s" % r["como"]
    return base + " · aviso: %s" % (" · ".join(r["avisos"]) if r["avisos"] else "—")


def _viejo(R, radar):
    f = R.a_fecha(radar.get("actualizado"))
    return bool(f and (R.hoy() - f).days > DIAS_RADAR_VIEJO)


def _sesion_ia(base):
    c = _lineas(Path(base) / "principal.txt")
    return c[0][0] if c and c[0] and c[0][0] else PRINCIPAL_DEFECTO


def _mejor(plan):
    n = str(plan.get("herramienta", ""))
    if n.startswith("app web (") and n.endswith(")"):
        n = n[len("app web ("):-1]
    return n


def resolver_producir(R, radar, f, base, personas, sin, a_fondo, herr, registro, sens_motivo):
    cat = R.buscar_categoria(radar, f["categoria"]) or {}
    planes = list(cat.get("planes") or [])
    norm = R._norm
    quitados_por = {norm(x) for x in str(sin).split(",") if x.strip()}
    avisos = []
    privado = bool(personas or sens_motivo)
    if f["id"] == "investigar":
        marca = "fondo" if a_fondo else "citas"
        marcados = [p for p in planes if p.get(marca)]
        planes = marcados or planes
    candidatas = [p for p in planes if norm(p.get("herramienta", "")) not in quitados_por]
    if privado:
        con = [p for p in candidatas if norm(p.get("herramienta", "")) in registro]
        decl_ok = [h for h in (herr or []) if norm(f["id"]) in h[2] and norm(h[0]) in registro and norm(h[0]) not in quitados_por]
        if not con and not decl_ok:
            return {"ia": "ninguna", "modelo": "—", "esfuerzo": "—", "como": "",
                    "motivo": "hay datos de personas o de un contrato y ninguna herramienta de «%s» tiene «no entrenar» registrado: "
                              "sacá los datos o registrá una IA" % f["id"], "avisos": ["sin registro"]}
        candidatas = con
    disp = disponibles(R)
    declaradas = {norm(h[0]): h for h in (herr or []) if norm(f["id"]) in h[2]}
    tipo = None
    elegida = None
    for p in candidatas:
        n = norm(p.get("herramienta", ""))
        if n in declaradas:
            elegida, tipo = p, declaradas[n][1]
            break
        if p.get("via") == "comando" and p.get("herramienta") in disp:
            elegida, tipo = p, "comando"
            break
    nombre = modelo = None
    if elegida is None:
        extra = [h for h in declaradas.values() if norm(h[0]) not in quitados_por and (not privado or norm(h[0]) in registro)]
        if extra:
            nombre, tipo = extra[0][0], extra[0][1]
            modelo = "—"
    if elegida is None and nombre is None:
        elegida = candidatas[0] if candidatas else (planes[0] if planes else None)
        tipo = "manual"
        avisos.append("sin herramienta conectada: pedido listo para pegar")
    if elegida is not None:
        nombre = elegida.get("herramienta", "—")
        modelo = elegida.get("modelo") if str(elegida.get("modelo")) not in ("None", "", "null") else "—"
        if f["id"] == "investigar":
            modelo = elegida.get("fondo" if a_fondo else "citas") if elegida.get("fondo" if a_fondo else "citas") not in (None, True) else modelo
    a = planes[0] if planes else None
    if a is not None and elegida is not a and (elegida is None or elegida.get("plan") != a.get("plan")) and tipo != "manual":
        avisos.append("mejor: %s" % _mejor(a))
    motivo = "es la primera herramienta de «%s» disponible en esta Mac" % f["id"] if tipo != "manual" else \
        "no hay herramienta de «%s» conectada: se usa la primera del radar y el pedido queda listo para pegar" % f["id"]
    if f["id"] == "investigar":
        motivo += "; tope %d consulta%s por pedido" % (TOPE_INVESTIGAR["fondo" if a_fondo else "citas"],
                                                       "" if a_fondo else "s")
    if _viejo(R, radar):
        avisos.append("provisorio")
    return {"ia": nombre, "modelo": str(modelo or "—"), "esfuerzo": "—", "como": tipo, "motivo": motivo, "avisos": avisos}


def resolver(R, radar, texto, si=None, personas=False, edita=False, repo=None, cupo_sesion=None, sin=(), subir=False,
             a_fondo=False, base=None):
    """Devuelve {fila, nivel, ia, modelo, esfuerzo, como, motivo, avisos, linea}; None si no reconoce la fila."""
    base = Path(base) if base else R.carpeta_metodo()
    norm = R._norm
    sin = sin if isinstance(sin, str) else ",".join(sin or [])
    sens = carpeta_sensible(repo, leer_sensibles(base))
    registro = leer_registro(base, norm)
    herr = leer_herramientas(base, norm)
    e_exacta = next((e for e in R.etapas_validas(radar) if R._norm(texto).strip() == R._norm(e["id"])
                     and e.get("nivel_base") in NIVEL_NUM), None)
    f = None if (e_exacta is not None and R._norm(texto).strip() != "investigar") else fila_producir(R, radar, texto)
    if f is not None:
        r = resolver_producir(R, radar, f, base, personas, sin, a_fondo, herr, registro, sens)
        r.update(fila=f["id"], nivel="—")
        r["linea"] = _linea(r)
        return r
    e = e_exacta or etapa_de(R, radar, texto)
    if e is None:
        return None
    if si is None:
        avisos0 = ["sin --si: se asumió 0"]
        si = 0
    else:
        avisos0 = []
    nivel = nivel_de(e["nivel_base"], si, subir)
    ses = _sesion_ia(base)
    avisos = list(avisos0)
    privado = bool(personas or sens)
    cat = R.buscar_categoria(radar, e.get("categoria") or "") or {}
    disp = disponibles(R)
    quitar = {norm(x) for x in sin.split(",") if x.strip()}
    cands = [p for p in (cat.get("planes") or []) if p.get("herramienta") in disp and norm(p["herramienta"]) not in quitar]
    sacadas_por_registro = False
    if privado:
        con = [p for p in cands if norm(p["herramienta"]) in registro]
        sacadas_por_registro = len(con) < len(cands) or not con
        cands = con
    sesion = None
    if cupo_sesion:
        sesion = parsear_cupo_sesion(cupo_sesion)
        if sesion is None:
            avisos.append("cupo-sesion no entendido")
    cupos = {p["herramienta"]: cupo_ritmo(CLAVE_CUPO.get(p["herramienta"], ""), sesion) if p["herramienta"] in CLAVE_CUPO
             else {"estado": "sin_dato"} for p in cands}
    cands = [p for p in cands if cupos[p["herramienta"]]["estado"] != "agotada"]
    elegida = None
    if cands:
        est = lambda p: cupos[p["herramienta"]]["estado"]
        no_escasea = [p for p in cands if est(p) != "escasea"]
        if nivel == "N3":
            elegida = cands[0]
        elif e["id"] == "implementar":
            elegida = no_escasea[0] if no_escasea else None
        else:
            sobra = [p for p in cands if p.get("plan") in ("A", "B") and est(p) == "sobra"]
            elegida = sobra[0] if sobra else (no_escasea[0] if no_escasea else None)
        if elegida is None:
            elegida = cands[0]
            avisos.append("cupo escaso")
        if est(elegida) == "sin_dato":
            avisos.append("cupo sin dato")
    if elegida is None:
        ia = ses
        if privado and sacadas_por_registro:
            avisos.append("sin registro")
        motivo = "no hay otra IA apta con cupo y registro: se usa la de la sesión"
    else:
        ia = elegida["herramienta"]
        motivo = "%s es la primera de «%s» en el radar que cumple privacidad y cupo" % (ia, cat.get("id", e["id"]))
    if _viejo(R, radar):
        avisos.append("provisorio")
    r = {"fila": e["id"], "nivel": nivel, "ia": ia, "modelo": modelo_de(radar, ia, nivel), "esfuerzo": ESFUERZO_NIVEL[nivel],
         "como": "", "motivo": "%s: %s (%s)" % (e["id"], motivo, nivel), "avisos": avisos}
    r["linea"] = _linea(r)
    return r


def resolver_seguro(R, radar, texto, **kw):
    """Igual que `resolver`, pero nunca falla: ante un error devuelve la IA de la sesión con el aviso `provisorio`."""
    try:
        return resolver(R, radar, texto, **kw)
    except Exception as ex:
        r = {"fila": texto, "nivel": "—", "ia": PRINCIPAL_DEFECTO, "modelo": "—", "esfuerzo": "medium", "como": "",
             "motivo": "el programa de ruteo falló (%s): nivel por defecto de la fila" % type(ex).__name__, "avisos": ["provisorio"]}
        r["linea"] = _linea(r)
        return r
