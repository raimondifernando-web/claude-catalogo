#!/usr/bin/env python3
"""estructura_equipo.py — R19-R21 del control de estructura: el EQUIPO que dice tener cada caja.

Disparador: encadenado — lo llama estructura.py (revisar_contenido) en cada pasada de `revisar`, que arranca solo desde el
aviso de apertura de sesión (hooks.json) y desde /cerrar. No se corre a mano.

R19  el PM que nombra el CLAUDE.md existe y su cuerpo no es una cáscara (Mand. XXIV); si la caja no nombra ningún PM y hay
     uno instalado que cita su carpeta, se lo señala.
R20  las skills que el PM precarga (`skills:` de su encabezado) existen.
R21  los conectores (MCP) que el CLAUDE.md dice usar están configurados y habilitados, y las herramientas `mcp__…` de su PM
     existen. Configurar ≠ habilitar. Los conectores de la nube (Gmail, Meta Ads, Vercel…) no se ven en disco: no se juzgan.

Solo LEE. De las configuraciones de MCP toma NOMBRES de servidor: nunca valores, llaves ni tokens. Sin POSIX: pathlib puro.
"""
import json
import re
from pathlib import Path

MIN_LINEAS_CUERPO = 15       # un PM con menos contenido que esto es una cáscara
MAX_EJEMPLOS = 4
# Conectores que viven en la nube de la cuenta (no hay nada en disco que los delate): jamás se juzgan.
NUBE = {"gmail", "calendar", "drive", "vercel", "figma", "meta", "slack", "canva", "claude", "chrome", "google",
        "microsoft", "outlook", "teams", "sharepoint", "spotify", "shopify", "adobe", "hubspot", "linear"}
PALABRAS = {"para", "que", "con", "del", "como", "propio", "propios", "oficial", "pendiente", "pendientes", "esta", "este",
            "est", "una", "uno", "los", "las", "por", "sin", "hay", "dice", "cada", "todo", "toda", "otro", "otra",
            "server", "servers", "servidor", "servidores", "tools", "tool", "nuevo", "nueva", "solo", "desde",
            "habilitado", "habilitados", "read-only", "readonly", "write", "only", "local", "remoto", "remota", "nube", "configurado", "configurados", "instalado", "conectado", "conectados"}
_HISTORICA = re.compile(r"(?i)\b(?:archivad[oa]|retirad[oa]|desinstalad[oa]|ya no|antes\b|hist[oó]ric)")


def _lee(ruta: Path) -> str:
    try:
        return ruta.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _norm(nombre: str) -> str:
    """Como Claude Code arma el nombre de un servidor en `mcp__<servidor>__<herramienta>`."""
    return re.sub(r"[^a-z0-9]+", "_", nombre.lower()).strip("_")


def _cadena(carpeta: Path):
    p = carpeta
    for _ in range(4):
        yield p
        p = p.parent


def _home() -> Path:
    return Path.home() / ".claude"


# ---------------------------------------------------------------- agentes, encabezado y cuerpo
def agentes(carpeta: Path) -> dict:
    """nombre -> ruta, de la carpeta de Claude, las cajas de arriba y los plugins instalados."""
    res = {}
    dirs = [_home() / "agents"] + [p / ".claude" / "agents" for p in _cadena(carpeta)]
    for d in dirs:
        if d.is_dir():
            for f in d.glob("*.md"):
                res.setdefault(f.stem, f)
    cache = _home() / "plugins" / "cache"
    if cache.is_dir():
        for f in cache.glob("*/*/*/agents/*.md"):
            res.setdefault(f.stem, f)
    return res


def partir_agente(texto: str):
    """(encabezado: dict nombre->texto crudo, cuerpo). Lee solo claves de primer nivel del encabezado."""
    m = re.match(r"\A---\r?\n(.*?)\r?\n---\r?\n?(.*)\Z", texto, re.S)
    if not m:
        return {}, texto
    enc, claves, actual = {}, [], None
    for linea in m.group(1).splitlines():
        if linea.lstrip().startswith("#"):
            continue
        linea = re.sub(r"\s+#.*$", "", linea)
        k = re.match(r"^([A-Za-z_][\w-]*)\s*:\s*(.*)$", linea)
        if k:
            actual = k.group(1)
            enc[actual] = k.group(2).strip()
        elif actual and linea.strip():
            enc[actual] += "\n" + linea.strip()
    return enc, m.group(2)


def _lista(crudo: str) -> list:
    """Una lista del encabezado: `[a, b]`, `a, b` o elementos `- a` en líneas."""
    if not crudo:
        return []
    items = []
    for parte in re.split(r"[\n,]", crudo.strip().strip("[]")):
        parte = parte.strip().lstrip("-").strip().strip("'\"")
        if parte:
            items.append(parte)
    return items


def lineas_de_contenido(cuerpo: str) -> int:
    return sum(1 for l in cuerpo.splitlines() if l.strip() and not l.lstrip().startswith(("#", "<!--")))


# ---------------------------------------------------------------- skills conocidas
def skills_conocidas(carpeta: Path) -> set:
    nombres = set()
    dirs = [_home() / "skills"] + [p / ".claude" / "skills" for p in _cadena(carpeta)]
    for d in dirs:
        if d.is_dir():
            nombres.update(x.name for x in d.iterdir() if x.is_dir())
    cache = _home() / "plugins" / "cache"
    if cache.is_dir():
        nombres.update(x.name for x in cache.glob("*/*/*/skills/*") if x.is_dir())
    return nombres


# ---------------------------------------------------------------- conectores configurados
def _claves_mcp(ruta: Path) -> list:
    """Solo los NOMBRES de servidor de un JSON de configuración (`mcpServers` o claves de primer nivel)."""
    try:
        datos = json.loads(_lee(ruta) or "{}")
    except ValueError:
        return []
    if not isinstance(datos, dict):
        return []
    srv = datos.get("mcpServers")
    if isinstance(srv, dict):
        return list(srv.keys())
    return [k for k, v in datos.items() if isinstance(v, dict) and ("command" in v or "url" in v or "type" in v)]


def conectores(carpeta: Path) -> dict:
    """{'configurados': {nombre normalizado: nombre}, 'habilitados': set o None, 'de_proyecto': set}.
    `habilitados` es None si nadie declaró la lista (entonces no se juzga la habilitación)."""
    conf, de_proyecto = {}, set()
    for p in _cadena(carpeta):
        for n in _claves_mcp(p / ".mcp.json"):
            conf[_norm(n)] = n
            de_proyecto.add(_norm(n))
    for n in _claves_mcp(Path.home() / ".mcp.json"):
        conf[_norm(n)] = n
        de_proyecto.add(_norm(n))
    for n in _claves_mcp(Path.home() / ".claude.json"):
        conf[_norm(n)] = n
    cache = _home() / "plugins" / "cache"
    if cache.is_dir():
        for f in cache.glob("*/*/*/.mcp.json"):
            for n in _claves_mcp(f):
                conf[_norm(n)] = n
    habil = None
    for nombre in ("settings.local.json", "settings.json"):
        for base in [_home()] + [p / ".claude" for p in _cadena(carpeta)]:
            try:
                datos = json.loads(_lee(base / nombre) or "{}")
            except ValueError:
                continue
            lista = datos.get("enabledMcpjsonServers") if isinstance(datos, dict) else None
            if isinstance(lista, list):
                habil = (habil or set()) | {_norm(str(x)) for x in lista}
    return {"configurados": conf, "habilitados": habil, "de_proyecto": de_proyecto}


_CITA_MCP = re.compile(r"(?i)\b(?:mcp|conectores?)\s+(?:de\s+|del\s+)?[`\"“]?([a-z][a-z0-9_.-]{3,})")
_CITA_HERR = re.compile(r"\bmcp__([A-Za-z0-9][A-Za-z0-9_-]*?)(?:__|$)")
_UUID = re.compile(r"^[0-9a-f]{8}[-_][0-9a-f]{4}")


def _es_de_nube(servidor: str) -> bool:
    s = _norm(servidor)
    return bool(_UUID.match(servidor)) or s.startswith(("claude_ai", "plugin_", "ccd_", "ide")) or s in NUBE


# ---------------------------------------------------------------- reglas
_EQUIPO_DICHO = re.compile(r"(?im)^[\s>*_#-]*equipo[\s*_]*(?::|$)|^[\s>*_#-]*sin\s+pm\b")


def revisar(carpeta: Path, texto: str) -> list:
    """R19-R21 y R29 de una caja. `texto` = su CLAUDE.md sin las líneas históricas. Retorna [(tipo, id, mensaje)]."""
    h = []
    if not texto.strip():
        return h
    todos = agentes(carpeta)
    citados = sorted(set(re.findall(r"\bpm-[a-z0-9]+(?:-[a-z0-9]+)*\b", texto)))
    existentes = [x for x in citados if x in todos]

    # R19
    huecos = []
    for pm in existentes:
        _, cuerpo = partir_agente(_lee(todos[pm]))
        n = lineas_de_contenido(cuerpo)
        if n < MIN_LINEAS_CUERPO:
            huecos.append(f"{pm} ({n} líneas)")
    if huecos:
        h.append(("aviso", "R19", "el PM que nombra el CLAUDE.md es una cáscara (su cuerpo casi no dice nada): "
                  + ", ".join(huecos[:MAX_EJEMPLOS])))
    if not citados and todos:
        nombre = carpeta.name
        if len(nombre) >= 4:
            duenos = []
            padre = carpeta.parent.name
            # la cita tiene que ser una RUTA de esta carpeta («Padre/Carpeta»), no la palabra suelta
            patron = re.escape(padre) + "/" + re.escape(nombre) + r"\b" if padre != "Proyectos" else r"Proyectos/" + re.escape(nombre) + r"\b"
            for pm, ruta in todos.items():
                if pm.startswith("pm-") and ruta.is_file():
                    _, cuerpo = partir_agente(_lee(ruta))
                    if re.search(r"(?<![\w-])" + patron, cuerpo):
                        duenos.append(pm)
            if duenos:
                h.append(("aviso", "R19", "el CLAUDE.md no nombra ningún PM y hay uno que cita esta carpeta: "
                          + ", ".join(sorted(duenos)[:MAX_EJEMPLOS]) + " → nombralo para que una sesión sepa a quién delegar"))

    # R29: la caja tiene que decir quién es su equipo (R19 solo juzga lo que se nombra)
    if not citados and not _EQUIPO_DICHO.search(texto) and not any(i == "R19" for _t, i, _m in h):
        h.append(("aviso", "R29", "el CLAUDE.md no dice quién es el equipo de esta caja (ningún pm-… ni una línea «Equipo:») → "
                  "agregá «Equipo: pm-<empresa> + los especialistas que usa» o «Equipo: sin PM (motivo)»"))

    # R20
    conocidas = skills_conocidas(carpeta)
    if conocidas:
        faltan = []
        for pm in existentes:
            enc, _ = partir_agente(_lee(todos[pm]))
            for sk in _lista(enc.get("skills", "")):
                base = sk.split(":")[-1]
                if sk not in conocidas and base not in conocidas:
                    faltan.append(f"{pm}→{sk}")
        if faltan:
            h.append(("aviso", "R20", f"el PM precarga {len(faltan)} skill(s) que no existen: "
                      + ", ".join(faltan[:MAX_EJEMPLOS]) + (" …" if len(faltan) > MAX_EJEMPLOS else "")))

    # R21
    con = conectores(carpeta)
    conf, habil = con["configurados"], con["habilitados"]
    citas = set()
    for linea in texto.splitlines():
        if _HISTORICA.search(linea):
            continue
        for m in _CITA_MCP.finditer(linea):
            t = m.group(1).rstrip(".-_")
            if t.lower() not in PALABRAS and not _es_de_nube(t):
                citas.add(t)
    sin_config, sin_habilitar = [], []
    for t in sorted(citas):
        nt = _norm(t)
        coinciden = [k for k in conf if nt == k or nt in k or k in nt]
        if not coinciden:
            sin_config.append(t)
        elif habil is not None and all(k in con["de_proyecto"] and k not in habil for k in coinciden):
            sin_habilitar.append(t)
    if sin_config:
        h.append(("aviso", "R21", "el CLAUDE.md cita conector(es) sin MCP configurado: " + ", ".join(sin_config[:MAX_EJEMPLOS])
                  + " → configuralo o aclará que se usa por script/API"))
    if sin_habilitar:
        h.append(("aviso", "R21", "conector(es) configurado(s) pero no habilitado(s): " + ", ".join(sin_habilitar[:MAX_EJEMPLOS])
                  + " (configurar ≠ habilitar)"))
    if conf:   # sin ninguna configuración legible no hay con qué comparar
        rotas = []
        for pm in existentes:
            enc, _ = partir_agente(_lee(todos[pm]))
            for herr in _lista(enc.get("tools", "")):
                m = _CITA_HERR.match(herr)
                if m and not _es_de_nube(m.group(1)) and _norm(m.group(1)) not in conf:
                    rotas.append(f"{pm}→{herr}")
        if rotas:
            h.append(("aviso", "R21", "su PM lista herramienta(s) de un MCP que no existe en la configuración: "
                      + ", ".join(rotas[:MAX_EJEMPLOS]) + (" …" if len(rotas) > MAX_EJEMPLOS else "")))
    return h
