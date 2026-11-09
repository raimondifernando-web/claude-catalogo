#!/usr/bin/env python3
"""portero — hook UserPromptSubmit, sin IA: ante un pedido de trabajo avisa qué skill, agente o conector del ecosistema encaja.

Qué hace: lee el JSON del hook (stdin: prompt, session_id, cwd), cruza las palabras del pedido contra un índice compacto
(~/.claude/mapa/portero-indice.json, armado desde ~/.claude/mapa/mapa.json) e imprime UNA línea (≤220 caracteres) por stdout:
  Para esto: skill xlsx · agente analista-de-bi (sonnet) · conector Notion
Si la mejor pieza está en un plugin apagado agrega cómo prenderla o cómo leerla; si parece tarea y no hay nada que encaje,
sugiere /metodo:buscar-skill-externa una sola vez por sesión. Es un aviso consultivo (stdout con código 0), nunca frena nada.
Calla ante: pedidos de menos de 25 caracteres, "/comando", confirmaciones (sí/ok/dale…), etiquetas de sistema, pedidos que ya
nombran una skill o agente, o con el apagado puesto. El texto del pedido no sale de acá ni se guarda: el registro lleva solo
≤6 palabras normalizadas.

Archivos: índice ~/.claude/mapa/portero-indice.json (se rehace solo si mapa.json es más nuevo) · sinónimos opcionales
~/.claude/mapa/portero-sinonimos.json ({"palabra": ["pieza", …]}) · estado por sesión ~/.claude/state/portero/<sesión>.json ·
registro ~/.claude/state/portero/registro.jsonl (formato fijo, lo lee el ciclo semanal) · errores en errores.log.

Disparador: automático (UserPromptSubmit). Apagado: PORTERO_OFF=1 o ~/.claude/state/portero/apagado
Probar: echo '{"prompt":"armame un Excel de gastos del mes","session_id":"x","cwd":"/tmp"}' | python3 "${CLAUDE_PLUGIN_ROOT}/scripts/portero.py"
Pruebas: python3 -m unittest discover -s plugins/metodo/scripts/tests -p "test_portero.py" -v (desde la raíz del repo)
"""
import glob
import importlib.util
import json
import math
import os
import re
import subprocess
import sys
import unicodedata
from datetime import datetime, timezone

HOME = os.path.expanduser("~")
CFG = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(HOME, ".claude")
MAPA_DIR = os.path.join(CFG, "mapa")
MAPA_JSON = os.path.join(MAPA_DIR, "mapa.json")
INDICE = os.path.join(MAPA_DIR, "portero-indice.json")
SINONIMOS = os.path.join(MAPA_DIR, "portero-sinonimos.json")
ESTADO = os.environ.get("PORTERO_ESTADO") or os.path.join(CFG, "state", "portero")

UMBRAL = 5.0          # puntaje de texto mínimo para sugerir una pieza
MAX_LINEA = 220
MIN_PEDIDO = 25
VERSION_INDICE = 2

ETIQUETAS = ("<task-notification", "<command-", "<cross-session-message", "<system-reminder", "<side-sessions-event", "<ci-monitor-event", "<agent-message", "<local-command")
CONFIRMA = {"si", "ok", "okay", "dale", "listo", "no", "gracias", "perfecto", "bueno", "genial", "adelante", "hecho",
            "vale", "claro", "seguime", "segui", "continua", "continuar", "buenisimo", "joya", "barbaro", "muchas",
            "por", "favor", "entendido", "exacto", "correcto", "bien", "todo", "eso", "esa", "ese", "yes", "thanks"}
VERBOS_TAREA = {"armar", "armame", "arma", "armalo", "crear", "crea", "creame", "hacer", "haceme", "hace", "analizar",
                "analiza", "analizame", "revisar", "revisa", "revisame", "escribir", "escribi", "escribime", "disenar",
                "disena", "disename", "calcular", "calcula", "calculame", "buscar", "busca", "buscame", "investigar",
                "investiga", "implementar", "implementa", "arreglar", "arregla", "arreglame", "generar", "genera",
                "preparar", "prepara", "redactar", "redacta", "redactame", "construir", "construi", "optimizar",
                "optimiza", "auditar", "audita", "convertir", "convierte", "exportar", "exporta", "mejorar", "mejora",
                "actualizar", "actualiza", "migrar", "migra", "planificar", "planifica", "traducir", "traduci",
                "resumir", "resumi", "armemos", "hagamos", "necesito", "quiero", "build", "create", "write",
                "analyze", "review", "design", "fix", "implement", "make", "generate"}
GENERICAS = {"usar", "uso", "cuando", "when", "use", "user", "para", "this", "that", "with", "quiero", "necesito",
             "puedes", "podes", "poder", "hacer", "algo", "cosa", "cosas", "tambien", "ahora", "favor", "mas",
             "tengo", "tenes", "tiene", "esta", "este", "estos", "estas", "todo", "toda", "todos", "todas", "nuevo",
             "nueva", "otro", "otra", "como", "pero", "porque", "luego", "antes", "despues", "mismo", "misma",
             "cada", "cual", "donde", "quien", "hay", "ser", "son", "fue", "van", "vamos", "sobre", "entre", "momento",
             "hora", "horas", "dia", "dias", "vez", "veces"}

_PALABRAS_VACIAS = {"de", "la", "el", "los", "las", "un", "una", "unos", "unas", "para", "con", "por", "sin", "sobre",
                    "entre", "tras", "hacia", "desde", "hasta", "del", "al", "que", "como", "cual", "cuales", "the",
                    "and", "for", "with", "from", "that", "this", "these", "those", "into", "onto", "about"}


def _normalizar_local(texto):
    if not texto:
        return ""
    nfd = unicodedata.normalize("NFD", str(texto).lower())
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn")


def _extraer_local(tema):
    tokens = re.findall(r"[a-z0-9_-]+", _normalizar_local(tema))
    palabras = [t for t in tokens if len(t) >= 3 and t not in _PALABRAS_VACIAS]
    if not palabras and tokens:
        palabras = [t for t in tokens if t not in _PALABRAS_VACIAS]
    return palabras


def _cargar_mapa_py():
    """normalizar_texto / extraer_palabras_busqueda de mapa.py (plugin metodo, la versión más nueva); sin él, copia local."""
    try:
        propio = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mapa.py")
        rutas = [propio] if os.path.isfile(propio) else []
        rutas += glob.glob(os.path.join(CFG, "plugins", "cache", "claude-catalogo", "metodo", "*", "scripts", "mapa.py"))

        def ver(r):
            m = re.search(r"metodo[/\\](\d+(?:\.\d+)*)[/\\]", r)
            return tuple(int(x) for x in m.group(1).split(".")) if m else (0,)
        if rutas:
            r = rutas[0] if rutas[0] == propio else sorted(rutas, key=ver)[-1]
            sp = importlib.util.spec_from_file_location("mapa_portero", r)
            mod = importlib.util.module_from_spec(sp)
            sp.loader.exec_module(mod)
            return mod.normalizar_texto, mod.extraer_palabras_busqueda
    except Exception as e:
        log_error("cargar mapa.py: %r" % e)
    return _normalizar_local, _extraer_local


normalizar_texto, extraer_palabras_busqueda = _normalizar_local, _extraer_local


def raiz(p):
    """Quita el plural básico para que 'reportes' y 'reporte' coincidan."""
    return p[:-1] if len(p) > 4 and p.endswith("s") and not p.endswith("ss") else p


def palabras(texto):
    out = []
    for p in extraer_palabras_busqueda(texto):
        for q in re.split(r"[-_]", p):
            if len(q) >= 3 and q not in GENERICAS and q not in _PALABRAS_VACIAS:
                out.append(raiz(q))
    return out


# Las descripciones de muchas piezas están en inglés: alias mínimos para los pedidos en castellano (el resto lo aprenden los sinónimos).
ALIAS = {"mail": ["email"], "correo": ["email"], "presentacion": ["slide", "presentation"], "anuncio": ["ads", "ad"],
         "planilla": ["spreadsheet", "excel"], "seguridad": ["security"], "informe": ["report"], "diseno": ["design"],
         "traduccion": ["translation"], "factura": ["invoice"], "vuelo": ["flight"], "mapa": ["map"],
         "grafico": ["chart"], "reunion": ["meeting"], "contrato": ["contract"], "licitacion": ["tender"]}


def expandir(qw):
    extra = []
    for w in qw:
        extra += ALIAS.get(w, [])
    return qw + extra


SEGURO = re.compile(r"[A-Za-z0-9_:.\-/~ ]+")
MODELO = re.compile(r"[a-z0-9.\-]{1,30}")
TOPE_LOG = 1024 * 1024


def seguro(texto):
    """Lista blanca para todo lo que se imprime y viene de mapa.json (plugins de terceros): sin saltos de línea ni símbolos."""
    return isinstance(texto, str) and SEGURO.fullmatch(texto) is not None


def asegurar_dir(ruta):
    os.makedirs(ruta, mode=0o700, exist_ok=True)


def rotar(ruta):
    try:
        if os.path.getsize(ruta) > TOPE_LOG:
            os.replace(ruta, ruta + ".1")
    except OSError:
        pass


def anexar(ruta, texto):
    """Agrega una línea a un archivo privado (0600), rotándolo a .1 al pasar 1 MB."""
    asegurar_dir(os.path.dirname(ruta))
    rotar(ruta)
    fd = os.open(ruta, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
    with os.fdopen(fd, "a", encoding="utf-8") as f:
        f.write(texto)


def escribir_privado(ruta, texto):
    asegurar_dir(os.path.dirname(ruta))
    fd = os.open(ruta, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(texto)


def log_error(msg):
    try:
        anexar(os.path.join(ESTADO, "errores.log"),
               "%s %s\n" % (datetime.now(timezone.utc).isoformat(timespec="seconds"), str(msg)[:300].replace("\n", " ")))
    except Exception:
        pass


# ---------------------------------------------------------------- índice

def _puede_skill(herramientas):
    """Misma regla que skill-en-agente.py: sin lista (o '*') carga skills; con lista, solo si trae Skill."""
    if not herramientas:
        return True
    if isinstance(herramientas, str):
        herramientas = [herramientas]
    return any(h in ("*", "Skill") for h in herramientas) or any("All" in str(h) for h in herramientas)


def _ruta_agente(plugin, archivo, rutas_plugin):
    base = rutas_plugin.get(plugin)
    if not base:
        return ""
    base = os.path.expanduser(base)
    for pat in (os.path.join(base, "agents", archivo), os.path.join(base, "agents", "**", archivo), os.path.join(base, archivo)):
        hit = glob.glob(pat, recursive=True)
        if hit:
            return hit[0].replace(HOME, "~", 1)
    return os.path.join(base, "agents", archivo).replace(HOME, "~", 1)


def construir_indice():
    with open(MAPA_JSON, encoding="utf-8") as f:
        m = json.load(f)
    rutas_plugin = {p.get("nombre"): p.get("ruta_instalacion", "") for p in m.get("plugins", [])}
    piezas = []

    def add(tipo, nombre, corto, desc, usos, **extra):
        pal = []
        vistas = set()
        for w in palabras(desc):
            if w not in vistas:
                vistas.add(w)
                pal.append(w)
            if len(pal) >= 30:
                break
        nom = sorted(set(palabras(corto) + palabras(nombre)))
        piezas.append(dict(t=tipo, n=nombre, c=corto, nw=nom, w=pal, u=int(usos or 0), **extra))

    for s in m.get("skills_personales", []):
        add("skill", s["nombre"], s["nombre"], s.get("descripcion", ""), s.get("usos_90d"), k=True, p="")
    for a in m.get("agentes", []):
        add("agente", a["nombre"], a["nombre"], a.get("descripcion", ""), a.get("usos_90d"), k=True, p="",
            md=a.get("modelo") or "", sk=_puede_skill(a.get("herramientas")), pm=bool(a.get("es_pm")))
    for s in m.get("skills_plugin", []):
        corto = s["nombre"]
        add("skill", s.get("invocacion") or "%s:%s" % (s.get("plugin"), corto), corto, s.get("descripcion", ""),
            s.get("usos_90d"), k=bool(s.get("cargado", True)), p=s.get("plugin", ""))
    for a in m.get("agentes_plugin", []):
        corto = a["nombre"]
        cargado = bool(a.get("cargado", True))
        extra = {} if cargado else {"r": _ruta_agente(a.get("plugin", ""), a.get("archivo", ""), rutas_plugin)}
        add("agente", a.get("invocacion") or "%s:%s" % (a.get("plugin"), corto), corto, a.get("descripcion", ""),
            a.get("usos_90d"), k=cargado, p=a.get("plugin", ""), md=a.get("modelo") or "",
            sk=_puede_skill(a.get("herramientas")), pm=False, **extra)
    vistos = set()
    for s in m.get("servidores_mcp", []):
        nom = (s.get("nombre") or "").strip()
        clave = nom.lower()
        if len(nom) < 3 or clave in ("mcp", "memory") or clave in vistos or not s.get("habilitado"):
            continue
        vistos.add(clave)
        add("mcp", nom, nom, "", s.get("usos_90d"), k=True, p=s.get("plugin", ""))
    # frecuencia de documento (para pesar por rareza); las piezas sin nombre propio útil no suman
    df = {}
    for p in piezas:
        for w in set(p["nw"]) | set(p["w"]):
            df[w] = df.get(w, 0) + 1
    nombres = sorted({p["c"].lower() for p in piezas} | {p["n"].lower() for p in piezas})
    indice = {"v": VERSION_INDICE, "mapa_mtime": os.path.getmtime(MAPA_JSON), "N": len(piezas), "df": df,
              "piezas": piezas, "nombres": nombres}
    tmp = INDICE + ".tmp%d" % os.getpid()
    escribir_privado(tmp, json.dumps(indice, ensure_ascii=False, separators=(",", ":")))
    os.replace(tmp, INDICE)
    return indice


def indice_valido(ind):
    try:
        if not (isinstance(ind, dict) and isinstance(ind["N"], int) and isinstance(ind["df"], dict)
                and isinstance(ind["piezas"], list) and isinstance(ind["nombres"], list)):
            return False
        for p in ind["piezas"]:
            if not (isinstance(p["n"], str) and isinstance(p["c"], str) and isinstance(p["nw"], list)
                    and isinstance(p["w"], list) and p["t"] in ("skill", "agente", "mcp")):
                return False
        return True
    except (KeyError, TypeError):
        return False


def cargar_indice():
    mapa_ok = os.path.isfile(MAPA_JSON)
    if not mapa_ok:
        # una sola vez por carpeta de estado: pedirle a `mapa` que lo genere
        marca = os.path.join(ESTADO, "intento-mapa")
        if not os.path.exists(marca):
            escribir_privado(marca, "")
            propio = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mapa.py")
            lanzador = propio if os.path.isfile(propio) else os.path.join(CFG, "scripts", "mapa")
            if os.path.isfile(lanzador):
                try:
                    subprocess.run([sys.executable, lanzador, "actualizar"], timeout=25, capture_output=True)
                except Exception as e:
                    log_error("mapa actualizar: %s" % e)
            mapa_ok = os.path.isfile(MAPA_JSON)
        if not mapa_ok and not os.path.isfile(INDICE):
            return None
    if mapa_ok and (not os.path.isfile(INDICE) or os.path.getmtime(MAPA_JSON) > os.path.getmtime(INDICE)):
        try:
            return construir_indice()
        except Exception as e:
            log_error("construir índice: %s" % e)
    try:
        with open(INDICE, encoding="utf-8") as f:
            ind = json.load(f)
        if not indice_valido(ind):
            log_error("índice con forma inválida: se reconstruye")
            try:
                os.remove(INDICE)
            except OSError:
                pass
            return construir_indice() if mapa_ok else None
        if ind.get("v") != VERSION_INDICE and mapa_ok:
            return construir_indice()
        return ind
    except Exception as e:
        log_error("leer índice: %s" % e)
        return None


# ---------------------------------------------------------------- puntaje

def puntuar(ind, qw, sinonimos, ya, cwd_words=frozenset()):
    N = max(ind["N"], 1)
    df = ind["df"]
    tope_df = max(12, int(N * 0.10))
    pesos = {}
    for w in set(qw):
        d = df.get(w, 0)
        if d == 0 or d > tope_df:
            continue
        pesos[w] = math.log((N + 1) / (d + 1))
    resultados = {"skill": [], "agente": [], "mcp": []}
    sin_por_pieza = {}
    for w in set(qw):
        for pieza in sinonimos.get(w, ()):
            if isinstance(pieza, str) and pieza:
                sin_por_pieza.setdefault(pieza.lower(), []).append(w)
    for p in ind["piezas"]:
        if p["n"] in ya or not seguro(p["n"]) or (p.get("p", "") and not seguro(p["p"])):
            continue
        nw = set(p["nw"])
        dw = set(p["w"])
        s = 0.0
        hit = []
        en_nombre = False
        raro_en_nombre = False
        for w, idf in pesos.items():
            if w in nw:
                s += 2.0 * idf
                hit.append(w)
                en_nombre = True
                raro_en_nombre = raro_en_nombre or idf >= 3.5
            elif w in dw:
                s += idf
                hit.append(w)
        sin = False
        for clave in {p["c"].lower(), p["n"].lower()}:
            for w in sin_por_pieza.get(clave, ()):
                s += 6.0
                hit.append(w)
                sin = True
        # una sola palabra suelta no alcanza (salvo sinónimo aprendido): evita sugerir por coincidencias casuales
        propia_o_usada = p["p"] == "" or p.get("u", 0) > 0
        if len(set(hit)) < 2 and not sin and not (raro_en_nombre and propia_o_usada):
            continue
        if p["p"] and not p.get("u") and not sin and (len(set(hit)) < 3 or not en_nombre):
            continue           # una pieza de plugin que nunca se usó necesita 3 coincidencias y una en el nombre
        if p["t"] == "mcp" and (not en_nombre or p.get("u", 0) <= 0):
            continue
        if p.get("pm") and not (en_nombre or (cwd_words & nw)):
            continue           # un jefe de proyecto solo si el pedido lo nombra o se trabaja en su carpeta
        if cwd_words & nw and p["t"] == "agente":
            s += 4.0           # el agente del proyecto de esta carpeta (pm-explorer en Explorer)
        if s <= 0:
            continue
        resultados[p["t"]].append((s, p, hit))
    return resultados


def mejor(lista):
    """Mejor pieza; ante un duplicado (copia fr-cowork:/rubro-*:/escala-*: de una propia) gana la propia y luego la cargada."""
    if not lista:
        return None
    lista.sort(key=lambda x: (-round(x[0], 3), 0 if x[1]["p"] == "" else 1, 0 if x[1]["k"] else 1))
    top = lista[0]
    # si hay una copia propia del mismo nombre corto con puntaje parecido, mostrar la propia
    for s, p, h in lista:
        if p["c"] == top[1]["c"] and p["p"] == "" and s >= top[0] * 0.8:
            return (s, p, h)
    return top


def con_uso(s, p):
    """El uso real a 90 días desempata; las piezas de plugin nunca usadas pesan menos que las propias."""
    base = s + 0.8 * math.log1p(p.get("u", 0))
    return base * (0.85 if p["p"] and not p.get("u") else 1.0)


def linea_para(ind, qw, sinonimos, ya, cwd_words=frozenset()):
    res = puntuar(ind, qw, sinonimos, ya, cwd_words)
    elegidas = {}
    mejor_puntaje = 0.0
    hits = []
    for tipo, lista in res.items():
        # el puntaje de texto decide el umbral; el uso desempata entre candidatas parecidas
        cand = [(con_uso(s, p), p, h, s) for s, p, h in lista if s >= UMBRAL]
        if not cand:
            continue
        cand.sort(key=lambda x: (-x[0], 0 if x[1]["p"] == "" else 1, 0 if x[1]["k"] else 1))
        top = cand[0]
        for c in cand:
            if c[1]["c"] == top[1]["c"] and c[1]["p"] == "" and c[3] >= top[3] * 0.8:
                top = c
                break
        elegidas[tipo] = top
        mejor_puntaje = max(mejor_puntaje, top[3])
        hits += top[2]
    if not elegidas:
        return None
    partes, sugeridas, extra = [], [], []
    if "skill" in elegidas:
        _, p, _, _ = elegidas["skill"]
        partes.append("skill %s" % p["n"])
        sugeridas.append({"nombre": p["n"], "tipo": "skill"})
        if not p["k"] and p["p"]:
            extra.append("plugin %s apagado acá: /plugin enable %s" % (p["p"], p["p"]))
            sugeridas[-1]["tipo"] = "plugin"
    if "agente" in elegidas:
        _, p, _, _ = elegidas["agente"]
        det = p.get("md") or ""
        det = det if MODELO.fullmatch(det) else ""
        if not p.get("sk", True):
            det = (det + ", sin skills").strip(", ")
        partes.append("agente %s%s" % (p["n"], " (%s)" % det if det else ""))
        sugeridas.append({"nombre": p["n"], "tipo": "agente"})
        if not p["k"]:
            if p["p"]:
                extra.append("plugin %s apagado acá: /plugin enable %s" % (p["p"], p["p"]))
            sugeridas[-1]["tipo"] = "plugin"
    if "mcp" in elegidas:
        _, p, _, _ = elegidas["mcp"]
        partes.append("conector %s" % p["n"])
        sugeridas.append({"nombre": p["n"], "tipo": "mcp"})
    linea = "Para esto: " + " · ".join(partes)
    for e in extra:
        if len(linea) + 3 + len(e) <= MAX_LINEA:
            linea += " · " + e
        elif extra.index(e) == 0:
            linea = linea[:MAX_LINEA - 3 - len(e)].rstrip(" ·") + " · " + e if len(e) < 120 else linea
    return linea[:MAX_LINEA], sugeridas, mejor_puntaje, hits


# ---------------------------------------------------------------- hook

def es_confirmacion(texto):
    toks = re.findall(r"[a-z0-9]+", _normalizar_local(texto))
    return bool(toks) and all(t in CONFIRMA for t in toks)


def nombra_pieza(texto, nombres):
    t = texto.lower()
    for m in re.finditer(r"(?:\bskill|\bagente|\bagent)\s+[`«\"']?([\w:.-]+)", t):
        if m.group(1) in nombres or m.group(1).split(":")[-1] in nombres:
            return True
    for m in re.finditer(r"(?<![\w/])/([\w:.-]+)", t):
        if m.group(1) in nombres or m.group(1).split(":")[-1] in nombres:
            return True
    for n in nombres:
        if "-" in n and len(n) >= 8 and n in t:
            return True
    return False


def leer_estado(sesion):
    try:
        with open(os.path.join(ESTADO, "%s.json" % sesion), encoding="utf-8") as f:
            e = json.load(f)
        return {"sugeridas": list(e.get("sugeridas", [])), "hueco": bool(e.get("hueco"))}
    except Exception:
        return {"sugeridas": [], "hueco": False}


def guardar_estado(sesion, est):
    escribir_privado(os.path.join(ESTADO, "%s.json" % sesion), json.dumps(est))


def registrar(sesion, cwd, pal, sugeridas, puntaje, hueco):
    fila = {"fecha": datetime.now(timezone.utc).isoformat(timespec="seconds"), "sesion": sesion, "carpeta": cwd,
            "palabras": pal[:6], "sugeridas": sugeridas, "puntaje": round(puntaje, 2), "hueco": hueco}
    anexar(os.path.join(ESTADO, "registro.jsonl"), json.dumps(fila, ensure_ascii=False) + "\n")


def main():
    global normalizar_texto, extraer_palabras_busqueda
    if os.environ.get("PORTERO_OFF") == "1" or os.path.exists(os.path.join(ESTADO, "apagado")):
        return
    try:
        datos = json.loads(sys.stdin.read() or "{}")
    except Exception:
        return
    prompt = datos.get("prompt") or ""
    if not isinstance(prompt, str):
        return
    prompt = prompt[:2000]
    p = prompt.strip()
    if len(p) < MIN_PEDIDO or p.startswith("/") or any(e in prompt for e in ETIQUETAS) or es_confirmacion(p):
        return
    sesion = re.sub(r"[^\w.-]", "_", str(datos.get("session_id") or "sin-sesion"))[:80]
    cwd = str(datos.get("cwd") or "")
    normalizar_texto, extraer_palabras_busqueda = _cargar_mapa_py()
    ind = cargar_indice()
    if not ind:
        return
    if nombra_pieza(p, set(ind["nombres"])):
        return
    sinonimos = {}
    try:
        with open(SINONIMOS, encoding="utf-8") as f:
            sinonimos = {normalizar_texto(k): v for k, v in json.load(f).items()}
    except Exception:
        pass
    qw = list(dict.fromkeys(expandir(palabras(p))))[:60]
    est = leer_estado(sesion)
    cwd_words = set(palabras(os.path.basename(cwd.rstrip("/")))) if cwd else set()
    res = linea_para(ind, qw, sinonimos, set(est["sugeridas"]), cwd_words)
    if res:
        linea, sugeridas, puntaje, hits = res
        est["sugeridas"] += [s["nombre"] for s in sugeridas]
        guardar_estado(sesion, est)
        registrar(sesion, cwd, list(dict.fromkeys(hits)), sugeridas, puntaje, False)
        print(linea)
        return
    toks = set(re.findall(r"[a-z0-9]+", _normalizar_local(p)))
    if toks & VERBOS_TAREA and not est["hueco"]:
        est["hueco"] = True
        guardar_estado(sesion, est)
        registrar(sesion, cwd, [], [], 0.0, True)
        print("Sin pieza para esto: /metodo:buscar-skill-externa")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # nunca una excepción hacia afuera
        log_error(repr(e))
    sys.exit(0)
