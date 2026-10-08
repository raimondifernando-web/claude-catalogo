#!/usr/bin/env python3
"""Radar de modelos del plugin `metodo`: qué IA conviene usar para cada cosa, con plan A, B y C.

La respuesta vive en un archivo único, `plugins/metodo/radar/RADAR.yaml` (lo mantiene un PR automático del catálogo,
que una persona aprueba). Este script lo lee y contesta, sin gastar cupo de IA y sin red (salvo `actualizar` y `probar`).

Comandos (los corre Claude desde la skill `radar`; el usuario no toca la terminal):
    ver [categoria]                      tabla legible: A/B/C con por qué y condiciones (sin categoría: el resumen)
    elegir <categoria> [--sensible]      el PRIMER plan disponible. Salta: cupo agotado (Codex se mide con codex-cupo),
                                         modelo retirado o que la última prueba marcó no disponible, y con --sensible
                                         los que no admiten datos privados. Dice qué saltó y por qué.
    json [--salida RUTA | --stdout]      exporta radar.json (para la pantalla «Radar» del Bicho)
    html [--salida RUTA]                 página local simple para mirarlo ya (<config>/metodo/radar.html)
    md [--salida RUTA]                   regenera RADAR.md (el que se lee en GitHub)
    actualizar                           baja el RADAR.yaml publicado y lo guarda como caché local; sin red, queda lo último
    probar [--si]                        OPCIONAL, apagado por defecto: prueba gratis de que los modelos nombrados andan
                                         con TUS claves (variables de entorno, por nombre; nunca se imprimen)
    aviso                                una línea si el radar tiene más de 14 días o hay un retiro próximo de un modelo
                                         que usamos; nunca falla el arranque
    hoy                                  5-6 líneas para empezar la sesión: modelos vigentes, ruteo por tipo de tarea, cupo de
                                         las 3 IA y avisos. SIN red y SIN comandos lentos (solo cachés locales); nunca falla
    consejos [--pedido RUTA] [--todo]    estado de los resúmenes de consejos de uso (radar/consejos/<modelo>.md, ≤10 líneas con la
                                         fuente arriba). --pedido baja las guías oficiales y deja el texto para que la IA más
                                         barata escriba los que faltan (con --todo, todos). No usa IA por sí mismo
    recordar                             (lo llama el hook PreToolUse de Agent / start_session; lee el JSON del hook por stdin)
                                         agrega una línea de contexto si al delegar falta el modelo o sobra nivel/esfuerzo.
                                         NUNCA bloquea ni decide permisos: solo recuerda
    funciones [palabras ...] [--pendientes] mapa de funciones oficiales de Claude Code (FUNCIONES.md) o cambios pendientes
                                         de la doc oficial. Nunca falla

`<config>` es $CLAUDE_CONFIG_DIR si está definida; si no, ~/.claude.
Códigos de salida: 0 bien · 1 no hay ningún plan disponible / error de uso · 2 categoría desconocida.
Python 3.6+. Solo biblioteca estándar.
"""
import argparse
import html as _html
import json
import os
import re
import shutil
import subprocess
import tempfile
import sys
import time
import unicodedata
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RADAR_EMPAQUETADO = AQUI.parent / "radar" / "RADAR.yaml"
CODEX_CUPO = AQUI / "codex-cupo"
CONSEJOS_DIR = AQUI.parent / "radar" / "consejos"
FUNCIONES_MD = AQUI.parent / "radar" / "FUNCIONES.md"
ETIQUETAS_OTRA_IA = {
    "imagenes_generar": "imágenes",
    "investigacion_web": "investigar en la web",
    "video": "video",
    "transcripcion": "transcribir audio",
    "voz_tts": "voz",
    "tareas_baratas": "tareas mecánicas baratas",
}
DIAS_CONSEJO_NUEVO = 14
MAX_LINEAS_CONSEJO = 10
URL_PUBLICADO = "https://raw.githubusercontent.com/raimondifernando-web/claude-catalogo/main/plugins/metodo/radar/RADAR.yaml"
DIAS_VIEJO = 14
DIAS_SIN_CAMBIOS = 30   # datos publicados sin moverse en un mes: el actualizador automático puede estar roto
MIN_INDEPENDIENTES = 2   # spec §7.3: con menos, el orden A/B/C de la categoría es provisorio
DIAS_RETIRO_AVISO = 45
DIAS_PRUEBA_VALIDA = 30
TIMEOUT_RED = 20
MAX_BYTES = 32 * 1024 * 1024   # models.dev ya pesa ~5 MB

# Claves por referencia: solo el NOMBRE de la variable de entorno. El valor nunca se imprime ni se guarda.
CLAVES = {"Anthropic": "ANTHROPIC_API_KEY", "OpenAI": "OPENAI_API_KEY", "Google": "GEMINI_API_KEY"}


# --------------------------------------------------------------------------- #
# YAML mínimo (el subconjunto que usa RADAR.yaml): mapas, listas, escalares, [a, b] y {}.
# --------------------------------------------------------------------------- #
def _sin_comentario(linea):
    comilla = None
    for i, c in enumerate(linea):
        if comilla:
            if c == comilla and linea[i - 1] != "\\":
                comilla = None
        elif c in "\"'" and (i == 0 or linea[i - 1] in " \t-:[,{"):
            comilla = c
        elif c == "#" and (i == 0 or linea[i - 1] in " \t"):
            return linea[:i]
    return linea


def _partir_kv(texto):
    """'clave: valor' → (clave, valor) o None. Los dos puntos deben ir seguidos de espacio o fin."""
    if texto[:1] in "\"'[{":
        return None
    for i, c in enumerate(texto):
        if c == ":" and (i + 1 == len(texto) or texto[i + 1] == " "):
            return texto[:i].strip(), texto[i + 1:].strip()
    return None


def _partir_plano(texto):
    partes, actual, nivel, comilla = [], "", 0, None
    for c in texto:
        if comilla:
            actual += c
            if c == comilla:
                comilla = None
        elif c in "\"'":
            comilla = c
            actual += c
        elif c in "[{":
            nivel += 1
            actual += c
        elif c in "]}":
            nivel -= 1
            actual += c
        elif c == "," and nivel == 0:
            partes.append(actual)
            actual = ""
        else:
            actual += c
    if actual.strip():
        partes.append(actual)
    return partes


def _escalar(t):
    t = t.strip()
    if t == "" or t in ("~", "null", "Null", "NULL"):
        return None
    if t in ("true", "True"):
        return True
    if t in ("false", "False"):
        return False
    if t[0] == '"':
        return json.loads(t)
    if t[0] == "'":
        return t[1:-1].replace("''", "'")
    if t == "[]":
        return []
    if t == "{}":
        return {}
    if t[0] == "[" and t[-1] == "]":
        return [_escalar(p) for p in _partir_plano(t[1:-1])]
    if re.fullmatch(r"-?\d+", t):
        return int(t)
    if re.fullmatch(r"-?\d+\.\d+", t):
        return float(t)
    return t


def yaml_cargar(texto):
    lineas = []
    for crudo in texto.splitlines():
        s = _sin_comentario(crudo).rstrip()
        if s.strip():
            lineas.append([len(s) - len(s.lstrip(" ")), s.strip()])
    if not lineas:
        return {}
    valor, i = _bloque(lineas, 0, lineas[0][0])
    if i != len(lineas):
        raise ValueError("YAML mal formado cerca de: " + lineas[i][1][:60])
    return valor


def _es_item(texto):
    return texto == "-" or texto.startswith("- ")


def _bloque(L, i, ind):
    return _lista(L, i, ind) if _es_item(L[i][1]) else _mapa(L, i, ind)


def _lista(L, i, ind):
    out = []
    while i < len(L) and L[i][0] == ind and _es_item(L[i][1]):
        resto = L[i][1][1:].lstrip()
        if not resto:
            i += 1
            if i < len(L) and L[i][0] > ind:
                v, i = _bloque(L, i, L[i][0])
            else:
                v = None
            out.append(v)
        elif _partir_kv(resto):
            L[i] = [ind + (len(L[i][1]) - len(resto)), resto]
            v, i = _mapa(L, i, L[i][0])
            out.append(v)
        else:
            out.append(_escalar(resto))
            i += 1
    return out, i


def _mapa(L, i, ind):
    out = {}
    while i < len(L) and L[i][0] == ind and not _es_item(L[i][1]):
        kv = _partir_kv(L[i][1])
        if kv is None:
            raise ValueError("se esperaba «clave: valor» y llegó: " + L[i][1][:60])
        clave, resto = kv
        i += 1
        if resto == "":
            if i < len(L) and (L[i][0] > ind or (L[i][0] == ind and _es_item(L[i][1]))):
                out[clave], i = _bloque(L, i, L[i][0])
            else:
                out[clave] = None
        else:
            out[clave] = _escalar(resto)
    return out, i


_PLANO = re.compile(r"^[A-Za-z0-9_./+-][A-Za-z0-9_./+ -]*$")
_RESERVADO = re.compile(r"^(true|false|null|~|yes|no|on|off)$", re.I)


def _dump_escalar(v):
    if v is None:
        return "null"
    if v is True:
        return "true"
    if v is False:
        return "false"
    if isinstance(v, (int, float)):
        return repr(v)
    s = str(v)
    if (_PLANO.match(s) and not _RESERVADO.match(s) and s == s.strip() and not re.fullmatch(r"-?[\d.]+", s)
            and not s.startswith("- ")):
        return s
    return json.dumps(s, ensure_ascii=False)


def _dump_vacio(v):
    return "[]" if isinstance(v, list) else "{}" if isinstance(v, dict) else _dump_escalar(v)


def yaml_volcar(valor, ind=0):
    pad = " " * ind
    out = []
    if isinstance(valor, dict):
        for k, v in valor.items():
            if isinstance(v, (dict, list)) and v:
                out.append("{}{}:".format(pad, k))
                out.append(yaml_volcar(v, ind + 2))
            else:
                out.append("{}{}: {}".format(pad, k, _dump_vacio(v)))
    elif isinstance(valor, list):
        for v in valor:
            if isinstance(v, dict) and v:
                sub = yaml_volcar(v, ind + 2).split("\n")
                out.append(pad + "- " + sub[0].lstrip())
                out.extend(sub[1:])
            elif isinstance(v, (dict, list)) and v:
                out.append(pad + "-")
                out.append(yaml_volcar(v, ind + 2))
            else:
                out.append("{}- {}".format(pad, _dump_vacio(v)))
    else:
        out.append(pad + _dump_escalar(valor))
    return "\n".join(out)


# --------------------------------------------------------------------------- #
# Lugares, fechas y carga
# --------------------------------------------------------------------------- #
def carpeta_config():
    propia = os.environ.get("CLAUDE_CONFIG_DIR", "").strip()
    return Path(propia) if propia else Path.home() / ".claude"


def carpeta_metodo():
    return carpeta_config() / "metodo"


def hoy():
    falso = os.environ.get("RADAR_HOY", "").strip()
    if falso:
        try:
            return datetime.strptime(falso, "%Y-%m-%d").date()
        except ValueError:
            pass
    return date.today()


def a_fecha(texto):
    try:
        return datetime.strptime(str(texto)[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def leer_yaml(ruta):
    return yaml_cargar(Path(ruta).read_text(encoding="utf-8"))


def cargar():
    """Devuelve (radar, origen). Usa la copia bajada con `actualizar` si es más nueva que la que viene en el plugin;
    si algo falla, la del plugin. Un archivo roto en la caché nunca tira el comando."""
    radar, origen = None, "plugin"
    if RADAR_EMPAQUETADO.exists():
        radar = leer_yaml(RADAR_EMPAQUETADO)
    cache = carpeta_metodo() / "radar" / "RADAR.yaml"
    try:
        if cache.exists():
            c = leer_yaml(cache)
            if isinstance(c, dict) and c.get("categorias") and (
                    radar is None or (a_fecha(c.get("actualizado")) or date.min) > (a_fecha(radar.get("actualizado")) or date.min)):
                radar, origen = c, "caché"
    except Exception:
        pass
    if radar is None:
        raise SystemExit("No encuentro el RADAR.yaml del plugin. Reinstalá el plugin `metodo`.")
    return radar, origen


def _norm(t):
    t = unicodedata.normalize("NFD", str(t).lower())
    return re.sub(r"[^a-z0-9]+", " ", "".join(c for c in t if unicodedata.category(c) != "Mn")).strip()


def buscar_categoria(radar, texto):
    n = _norm(texto)
    cats = radar.get("categorias") or []
    for c in cats:
        if n in (_norm(c.get("id", "")), _norm(c.get("nombre", ""))):
            return c
    cand = [c for c in cats if n and (_norm(c.get("id", "")).startswith(n) or n in _norm(c.get("nombre", "")))]
    return cand[0] if len(cand) == 1 else None


# --------------------------------------------------------------------------- #
# Disponibilidad
# --------------------------------------------------------------------------- #
def _buscar_bin(nombre, var_env):
    """Ruta absoluta y ejecutable de la CLI, o None. Una variable o un PATH con rutas relativas no cuentan: la
    herramienta se ejecuta con el repo del usuario como carpeta actual y no puede encontrarse un binario ahí."""
    def bueno(ruta):
        try:
            real = os.path.realpath(ruta)
            return real if os.path.isabs(real) and os.path.isfile(real) and os.access(real, os.X_OK) else None
        except (OSError, ValueError):
            return None

    propia = os.environ.get(var_env, "").strip()
    if propia:
        return bueno(propia) if os.path.isabs(propia) else None
    w = shutil.which(nombre)
    if w and os.path.isabs(w):
        r = bueno(w)
        if r:
            return r
    for c in (Path.home() / ".local" / "bin" / nombre, Path("/opt/homebrew/bin") / nombre, Path("/usr/local/bin") / nombre):
        r = bueno(str(c))
        if r:
            return r
    return None


def _pct_valido(v):
    """Porcentaje entre 0 y 100, o None (un cupo.json ajeno no puede hacer ver «ok» con -1 o nan)."""
    try:
        x = float(v)
    except (ValueError, TypeError):
        return None
    return x if 0.0 <= x <= 100.0 else None


def cupo_codex():
    """(nivel, texto). nivel: ok | alto | agotado | desconocido | no_disponible. Usa la misma lectura que `codex-cupo`.
    `no_disponible` = la CLI no está instalada o no tiene sesión iniciada (`codex login`): el plan se salta."""
    script = os.environ.get("RADAR_CODEX_CUPO", "").strip()
    if not script:   # con el lector reemplazado (pruebas) no se mira el equipo
        if not _buscar_bin("codex", "RADAR_CODEX_BIN"):
            return "no_disponible", "Codex: no está instalada"
        codex_home = os.environ.get("CODEX_HOME", "").strip()
        sesion = Path(codex_home) if codex_home and os.path.isabs(codex_home) else Path.home() / ".codex"
        if not (sesion / "auth.json").is_file():   # solo se mira que exista, nunca se abre
            return "no_disponible", "Codex: sin sesión iniciada (falta «codex login»)"
        script = str(CODEX_CUPO)
    try:
        r = subprocess.run(["bash", script], stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL,
                           cwd=tempfile.gettempdir(), timeout=10)
        texto = r.stdout.decode("utf-8", "replace").strip().splitlines()
        texto = texto[-1] if texto else "Codex: cupo desconocido"
        if r.returncode == 2:
            return "agotado", texto
        if r.returncode == 1:
            return "alto", texto
        if r.returncode == 0 and "desconocido" not in texto and "sin registros" not in texto:
            return "ok", texto
    except Exception:
        pass
    return "desconocido", "Codex: cupo desconocido"


def cupo_claude():
    """(nivel, texto). nivel: ok | alto | agotado | desconocido."""
    cerebro = os.environ.get("CEREBRO_HOME", "").strip()
    ruta_json = Path(cerebro) / "cupo.json" if cerebro else Path.home() / ".cerebro" / "cupo.json"
    try:
        if ruta_json.is_file() and ruta_json.stat().st_size < 65536:
            datos = json.loads(ruta_json.read_text(encoding="utf-8"))
            ts = float(datos.get("ts", 0))
            if 0 <= (time.time() - ts) < 900:
                pcts = []
                for k in ("five_hour", "seven_day"):
                    sub = datos.get(k)
                    if isinstance(sub, dict) and _pct_valido(sub.get("pct")) is not None:
                        pcts.append(_pct_valido(sub.get("pct")))
                if pcts:
                    max_pct = max(pcts)
                    nivel = "agotado" if max_pct >= 90 else "alto" if max_pct >= 70 else "ok"
                    return nivel, "Claude: %d%% usado" % round(max_pct)
    except Exception:
        pass

    bin_claude = _buscar_bin("claude", "RADAR_CLAUDE_BIN")
    if not bin_claude:
        return "desconocido", "Claude: cupo desconocido"

    try:
        r = subprocess.run(
            [bin_claude, "-p", "/usage", "--output-format", "text", "--no-session-persistence", "--setting-sources", "user",
             "--settings", '{"disableAllHooks":true}'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
            cwd=tempfile.gettempdir(),
            timeout=30
        )
        if r.returncode != 0:
            return "desconocido", "Claude: cupo desconocido"
        salida = r.stdout.decode("utf-8", "replace")
        pcts = []
        for linea in salida.splitlines():
            linea_s = linea.strip()
            if linea_s.startswith("Current session:") or linea_s.startswith("Current week (all models):"):
                m = re.search(r"(\d+(?:\.\d+)?)\s*%", linea_s)
                if m:
                    pcts.append(float(m.group(1)))
        if pcts:
            max_pct = max(pcts)
            nivel = "agotado" if max_pct >= 90 else "alto" if max_pct >= 70 else "ok"
            return nivel, "Claude: %d%% usado" % round(max_pct)
    except Exception:
        pass
    return "desconocido", "Claude: cupo desconocido"


def cupo_antigravity():
    """(nivel, texto). nivel: ok | alto | agotado | desconocido | no_disponible.
    `no_disponible` = la CLI no está instalada o `agy -p /usage` falla (sin sesión iniciada): el plan se salta."""
    bin_agy = _buscar_bin("agy", "RADAR_AGY_BIN")
    if not bin_agy:
        return "no_disponible", "Antigravity: no está instalada"
    # `agy -p /usage` SIN sesión iniciada abre el navegador para que el usuario entre con su cuenta de Google (pasó el
    # 2026-10-05). Para no abrirlo nunca, solo se le pregunta si ya se usó alguna vez (su historial existe; solo se mira que
    # exista, nunca se abre). Una ruta puesta a mano en RADAR_AGY_BIN (pruebas) se usa tal cual.
    if not os.environ.get("RADAR_AGY_BIN", "").strip():
        estado = os.environ.get("RADAR_AGY_STATE", "").strip()
        base = Path(estado) if estado and os.path.isabs(estado) else Path.home() / ".gemini" / "antigravity-cli"
        if not (base / "history.jsonl").is_file():
            return "no_disponible", "Antigravity: sin usar todavía (corré «agy» una vez e iniciá sesión)"

    try:
        r = subprocess.run(
            [bin_agy, "-p", "/usage", "--output-format", "json"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
            cwd=tempfile.gettempdir(),
            timeout=30
        )
        if r.returncode != 0:
            return "no_disponible", "Antigravity: sin sesión iniciada o con error (corré «agy» una vez e iniciá sesión)"
        raiz = json.loads(r.stdout.decode("utf-8", "replace"))
        if isinstance(raiz, dict) and str(raiz.get("status", "")).upper() == "ERROR":
            return "no_disponible", "Antigravity: sin sesión iniciada o con error (corré «agy» una vez e iniciá sesión)"
        grupos = raiz.get("command", {}).get("data", {}).get("groups", [])
        if not isinstance(grupos, list):
            return "desconocido", "Antigravity: cupo desconocido"
        usados = []
        for g in grupos:
            if isinstance(g, dict) and str(g.get("name", "")).startswith("Gemini"):
                buckets = g.get("buckets", [])
                if isinstance(buckets, list):
                    for b in buckets:
                        if isinstance(b, dict):
                            rem = b.get("remaining_fraction")
                            if isinstance(rem, (int, float)):
                                usados.append(100.0 * (1.0 - float(rem)))
        if usados:
            max_usado = max(usados)
            nivel = "agotado" if max_usado >= 90 else "alto" if max_usado >= 70 else "ok"
            return nivel, "Antigravity: %d%% usado" % round(max_usado)
    except Exception:
        pass
    return "desconocido", "Antigravity: cupo desconocido"


def cargar_prueba():
    try:
        return json.loads((carpeta_metodo() / "radar-probe.json").read_text(encoding="utf-8"))
    except Exception:
        return {}


def retiro_de(radar, modelo_api):
    for r in radar.get("retiros") or []:
        if modelo_api and r.get("modelo") == modelo_api:
            return r
    return None


def motivo_salto(plan, radar, sensible, prueba, cache_cupo):
    """Motivo por el que este plan no se puede usar ahora, o None si está disponible."""
    if sensible and not plan.get("datos_privados"):
        return "no admite datos privados" + (": " + plan["condiciones"] if plan.get("condiciones") else "")
    api = plan.get("modelo_api")
    r = retiro_de(radar, api)
    if r and r.get("tipo", "apagado") == "apagado":
        f = a_fecha(r.get("fecha"))
        if f and f <= hoy():
            return "el modelo %s se apagó el %s" % (api, r["fecha"])
    p = prueba.get(api) if api else None
    if p and p.get("disponible") is False:
        f = a_fecha(p.get("fecha"))
        if f is None or (hoy() - f).days <= DIAS_PRUEBA_VALIDA:
            return "la última prueba (%s) lo marcó no disponible: %s" % (p.get("fecha", "?"), p.get("motivo", "sin detalle"))
    lectores = {"codex": cupo_codex, "claude": cupo_claude, "antigravity": cupo_antigravity}
    tipo_cupo = plan.get("cupo")
    if tipo_cupo in lectores:
        if tipo_cupo not in cache_cupo:
            cache_cupo[tipo_cupo] = lectores[tipo_cupo]()
        nivel, texto = cache_cupo[tipo_cupo]
        if nivel == "agotado":
            return "cupo agotado (%s)" % texto
        if nivel == "no_disponible":   # sin instalar o sin cuenta: se pasa al plan siguiente, con el motivo a la vista
            return "no disponible (%s)" % texto
    return None


def elegir(radar, categoria, sensible=False, prueba=None, delegar=False):
    prueba = cargar_prueba() if prueba is None else prueba
    cache, saltados = {}, []
    planes = categoria.get("planes") or []
    if delegar:
        no_claude = [p for p in planes if not str(p.get("herramienta", "")).startswith("Claude Code")]
        claude = [p for p in planes if str(p.get("herramienta", "")).startswith("Claude Code")]
        planes = no_claude + claude
    for plan in planes:
        m = motivo_salto(plan, radar, sensible, prueba, cache)
        if m is None:
            return plan, saltados, cache
        saltados.append((plan, m))
    return None, saltados, cache


def _nombre_plan(p):
    modelo = p.get("modelo")
    return "%s (%s%s)" % (p.get("herramienta", "?"), p.get("proveedor", "?"), ", " + modelo if modelo else "")


# --------------------------------------------------------------------------- #
# Presentación
# --------------------------------------------------------------------------- #
def marca(p):
    return "" if p.get("verificado") else " [a verificar]"


def respaldo(c):
    """Cuántas fuentes independientes respaldan el orden A/B/C de la categoría (spec §7.2-3). Las del fabricante
    (`tipo: fabricante`) no cuentan: sirven para precios, ids y retiros, nunca para el orden."""
    indep = [ev for ev in c.get("evidencia") or [] if str(ev.get("tipo", "")).strip() == "independiente"]
    nombres = {str(ev.get("fuente", "")).strip() for ev in indep}
    # §7.1: el A/B/C todavía se escribe a mano. Para no ser provisorio, CADA plan tiene que citar en `respaldo`
    # alguna evidencia independiente de la categoría; contar fuentes sueltas no alcanza.
    planes = c.get("planes") or []
    citados = all(any(str(x).strip() in nombres for x in (p.get("respaldo") or [])) for p in planes) if planes else False
    return len(indep), len(indep) >= MIN_INDEPENDIENTES and citados


def texto_respaldo(c):
    n, ok = respaldo(c)
    if ok:
        return "Orden respaldado por %d fuentes independientes." % n
    if n >= MIN_INDEPENDIENTES:
        return "Orden PROVISORIO: hay %d fuentes independientes, pero no todos los planes se apoyan en ellas." % n
    return "Orden PROVISORIO: %d de %d fuentes independientes." % (n, MIN_INDEPENDIENTES)


def texto_categoria(c):
    out = ["%s (%s)" % (c.get("nombre", c.get("id")), c.get("id")), "  " + texto_respaldo(c)]
    for p in c.get("planes") or []:
        out.append("  %s  %s%s" % (p.get("plan", "?"), _nombre_plan(p), marca(p)))
        if p.get("por_que"):
            out.append("      por qué: " + p["por_que"])
        out.append("      datos privados: %s" % ("sí" if p.get("datos_privados") else "NO"))
        if p.get("condiciones"):
            out.append("      condiciones: " + p["condiciones"])
        if p.get("como_ver_cupo"):
            out.append("      ver cupo: " + p["como_ver_cupo"])
        if p.get("fuente"):
            out.append("      fuente: %s (%s)" % (p["fuente"], p.get("fecha", "sin fecha")))
    for ev in c.get("evidencia") or []:
        out.append("  evidencia (%s): %s — %s (%s)%s" % (
            ev.get("tipo", "?"), ev.get("fuente", "?"), ev.get("dice", ""), ev.get("fecha", "sin fecha"),
            "; conflicto: " + ev["conflicto"] if ev.get("conflicto") else ""))
    rk = c.get("ranking") or {}
    if rk.get("items"):
        out.append("  Ranking (%s, %s)%s:" % (rk.get("fuente", "?"), rk.get("fecha", "?"), "" if rk.get("verificado") else " [a verificar]"))
        for it in rk["items"][:5]:
            out.append("    %s. %s%s" % (it.get("puesto", "?"), it.get("modelo", "?"),
                                         " — %s" % it["puntaje"] if it.get("puntaje") not in (None, "") else ""))
    return "\n".join(out)


def retiros_proximos(radar, dias=DIAS_RETIRO_AVISO):
    """Retiros dentro de `dias` (o vencidos hace poco) de modelos que algún plan nombra."""
    usados = {}
    for c in radar.get("categorias") or []:
        for p in c.get("planes") or []:
            if p.get("modelo_api"):
                usados.setdefault(p["modelo_api"], []).append("%s %s" % (c.get("id"), p.get("plan")))
    out = []
    for r in radar.get("retiros") or []:
        f = a_fecha(r.get("fecha"))
        if r.get("tipo") == "no_antes":
            continue  # «no se retira antes de…» no es un retiro anunciado
        if f and r.get("modelo") in usados and hoy() - timedelta(days=30) <= f <= hoy() + timedelta(days=dias):
            out.append((r, usados[r["modelo"]]))
    return out


def ultima_comprobacion():
    """Fecha en que `actualizar` bajó bien el radar publicado (aunque no trajera cambios), o None."""
    try:
        return a_fecha((carpeta_metodo() / "radar" / "comprobado").read_text(encoding="utf-8").strip())
    except Exception:
        return None


def aviso_linea(radar):
    partes = []
    # Viejo = nadie lo comprobó en DIAS_VIEJO días. Si los datos no cambiaron pero `actualizar` confirmó que es lo
    # último publicado, no es viejo: sin esto, cualquier quincena tranquila disparaba el aviso para siempre.
    datos = a_fecha(radar.get("actualizado"))
    f = max((x for x in (datos, ultima_comprobacion()) if x), default=None)
    if f is None or (hoy() - f).days > DIAS_VIEJO:
        partes.append("el radar de modelos tiene %s (corré «radar.py actualizar»)" % (
            "fecha desconocida" if f is None else "%d días" % (hoy() - f).days))
    elif datos and (hoy() - datos).days > DIAS_SIN_CAMBIOS:
        partes.append("los datos del radar no cambian hace %d días: tomalo con cuidado" % (hoy() - datos).days)
    prox = retiros_proximos(radar)
    if prox:
        r, donde = prox[0]
        partes.append("se retira %s el %s y lo usa el plan %s%s" % (
            r["modelo"], r["fecha"], donde[0], " (+%d más)" % (len(prox) - 1) if len(prox) > 1 else ""))
    return "Radar: " + "; ".join(partes) if partes else ""


# --------------------------------------------------------------------------- #
# Modelos vigentes, ruteo por tipo de tarea, `hoy` y el recordatorio al delegar
# --------------------------------------------------------------------------- #
NIVELES = {"haiku": 1, "sonnet": 2, "opus": 3, "fable": 4}
ESFUERZOS = {"low": 1, "medium": 2, "high": 3, "xhigh": 4, "max": 5}
ID_MODELO = re.compile(r"^[a-z0-9][a-z0-9._-]{1,63}$")
EDAD_MAX_CUPO = {"claude": 1800, "codex": 24 * 3600, "antigravity": 1800}   # segundos
CACHE_CUPO = {"claude": "cupo.json", "codex": "cupo-codex.json", "antigravity": "cupo-agy.json"}
MAX_AVISOS_POR_SESION = {"generico": 1, "sobra": 3}


def _tupla_version(texto):
    try:
        return tuple(int(x) for x in re.split(r"[.-]", str(texto)))
    except ValueError:
        return None


def _comparable(v):
    return tuple(v) + (0,) * (3 - len(v))


def familia_de(modelo_api, familias):
    """(familia, versión, id normalizado) si el modelo pertenece a una familia de `fuentes_auto.familias`, o None.
    Cada familia trae un `patron` con UN grupo: la versión («5-5», «6.1»). Los ids con puntos de Claude (OpenRouter
    dice claude-haiku-5.5) se pasan a guiones con `puntos_a_guion` para que coincidan con los de la API."""
    m_norm = str(modelo_api or "").strip().lower().split("/")[-1]
    for f in familias or []:
        if not isinstance(f, dict) or not f.get("patron"):
            continue
        cand = m_norm.replace(".", "-") if f.get("puntos_a_guion") else m_norm
        try:
            m = re.fullmatch(f["patron"], cand)
        except re.error:
            continue
        if m and m.groups():
            v = _tupla_version(m.group(1))
            if v:
                return f, v, cand
    return None


def vigentes_por_familia(radar):
    return {f["id"]: f for f in ((radar.get("vigentes") or {}).get("familias") or []) if isinstance(f, dict) and f.get("id")}


def modelo_de_alias(radar, alias):
    """Id del modelo vigente de un alias de Claude (haiku/sonnet/opus/fable), o None. Solo devuelve ids de forma válida."""
    for f in vigentes_por_familia(radar).values():
        if f.get("alias") == alias and ID_MODELO.match(str(f.get("modelo_api", ""))):
            return f["modelo_api"]
    return None


def planes_atrasados(radar):
    """Planes cuyo modelo es de una versión anterior a la vigente de su familia (solo avisa: el orden A/B/C se cambia a mano)."""
    familias = (radar.get("fuentes_auto") or {}).get("familias") or []
    vig = vigentes_por_familia(radar)
    out = []
    for c in radar.get("categorias") or []:
        for p in c.get("planes") or []:
            usa = familia_de(p.get("modelo_api"), familias)
            nuevo = vig.get(usa[0].get("id")) if usa else None
            if not nuevo:
                continue
            hay = familia_de(nuevo.get("modelo_api"), familias)
            if hay and _comparable(hay[1]) > _comparable(usa[1]):
                out.append({"categoria": c.get("nombre") or c.get("id"), "plan": p.get("plan"),
                            "usa": p.get("modelo_api"), "vigente": nuevo.get("modelo_api")})
    return out


def _limpio(texto, largo=60):
    """Texto de una sola línea y sin caracteres de control (lo que va al contexto de la sesión no trae formato ajeno)."""
    s = re.sub(r"[\x00-\x1f\x7f`]+", " ", str(texto or ""))
    return re.sub(r"\s+", " ", s).strip()[:largo]


def ruteo_filas(radar):
    """Filas válidas de `ruteo_claude.tareas` (nivel y esfuerzo dentro de los valores conocidos)."""
    out = []
    for t in ((radar.get("ruteo_claude") or {}).get("tareas") or []):
        if isinstance(t, dict) and t.get("nivel") in NIVELES and t.get("esfuerzo") in ESFUERZOS:
            out.append(t)
    return out


def fila_para(radar, texto):
    """La fila del ruteo que mejor calza con el texto de la tarea. Con varias, la de nivel más alto (el recordatorio
    prefiere callar antes que retar de más)."""
    norm = " %s " % _norm(texto)
    palabras = norm.split()
    elegida = None
    for t in ruteo_filas(radar):
        for kw in t.get("palabras") or []:
            raiz = str(kw).endswith("*")
            k = _norm(str(kw).rstrip("*"))
            if not k:
                continue
            if " " in k:
                hit = (" %s " % k) in norm
            elif raiz:   # «revis*»: cualquier palabra que empiece así
                hit = any(w.startswith(k) for w in palabras)
            elif len(k) < 4:
                hit = k in palabras
            elif len(k) <= 5:   # palabra corta: solo ella o su plural («plata» no calza con «plataforma», «code» no con «codex»)
                hit = any(w in (k, k + "s", k + "es") for w in palabras)
            else:   # palabra + sufijo corto: «count» no calza con «country»
                tope = len(k) + (4 if len(k) < 8 else 6)
                hit = any(w.startswith(k) and len(w) <= tope for w in palabras)
            if hit:
                clave = (NIVELES[t["nivel"]], ESFUERZOS[t["esfuerzo"]])
                if elegida is None or clave > elegida[0]:
                    elegida = (clave, t)
                break
    return elegida[1] if elegida else None


def _cupo_de_cache(clave):
    """Porcentaje usado leído de la caché local (la deja el Bicho), o None si falta, es vieja o no es válida."""
    cerebro = os.environ.get("CEREBRO_HOME", "").strip()
    base = Path(cerebro) if cerebro else Path.home() / ".cerebro"
    try:
        ruta = base / CACHE_CUPO[clave]
        if not ruta.is_file() or ruta.stat().st_size > 65536:
            return None
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        edad = time.time() - float(datos.get("ts", 0))
        if not 0 <= edad <= EDAD_MAX_CUPO[clave]:
            return None
        pcts = [_pct_valido(datos.get("pct"))]
        for k in ("five_hour", "seven_day"):
            sub = datos.get(k)
            if isinstance(sub, dict):
                pcts.append(_pct_valido(sub.get("pct")))
        pcts = [x for x in pcts if x is not None]
        return max(pcts) if pcts else None
    except Exception:
        return None


def _nivel_pct(x):
    return "agotado" if x >= 90 else "alto" if x >= 70 else "ok"


def cupos_rapidos():
    """{clave: (nivel, porcentaje|None)} de las 3 IA leyendo SOLO cachés locales (las deja el Bicho). No lanza ningún programa:
    sin caché, o con una vieja, queda «sin dato». nivel: ok | alto | agotado | sin_dato."""
    out = {}
    for clave in ("claude", "codex", "antigravity"):
        x = _cupo_de_cache(clave)
        out[clave] = (_nivel_pct(x), x) if x is not None else ("sin_dato", None)
    return out


def _texto_cupo(nombre, nivel, pct):
    if nivel == "sin_dato":
        return "%s sin dato" % nombre
    nota = {"agotado": " (agotado)", "alto": " (solo tareas chicas)"}.get(nivel, "")
    return "%s %d%%%s" % (nombre, round(pct), nota)


MAX_FILAS_RUTEO = 12


def ruteo_en_una_linea(radar):
    """Filas del ruteo agrupadas por nivel/esfuerzo. Un «*» marca el grupo con alguna fila sin dato independiente (provisoria)."""
    grupos = []
    for t in ruteo_filas(radar)[:MAX_FILAS_RUTEO]:
        clave = "%s/%s" % (t["nivel"], t["esfuerzo"])
        provisoria = t.get("verificado") is not True
        for g in grupos:
            if g[0] == clave:
                g[1].append(_limpio(t.get("corto") or t.get("id")))
                g[2] = g[2] or provisoria
                break
        else:
            grupos.append([clave, [_limpio(t.get("corto") or t.get("id"))], provisoria])
    grupos.sort(key=lambda g: (NIVELES[g[0].split("/")[0]], ESFUERZOS[g[0].split("/")[1]]))
    return " · ".join("%s%s = %s" % (c, "*" if prov else "", ", ".join(x)) for c, x, prov in grupos)


def otras_ia_linea(radar):
    """El plan A de cada categoría que Claude no cubre (proveedor distinto de Anthropic). Vacío si no corresponde."""
    try:
        partes = []
        for c in (radar.get("categorias") or []):
            if not isinstance(c, dict):
                continue
            plan_a = next((p for p in (c.get("planes") or []) if isinstance(p, dict) and p.get("plan") == "A"), None)
            if not plan_a:
                continue
            prov = str(plan_a.get("proveedor") or "").strip()
            if not prov or prov.lower() == "anthropic":
                continue
            cid = str(c.get("id") or "")
            etiqueta = ETIQUETAS_OTRA_IA.get(cid)
            if not etiqueta:
                etiqueta = _limpio(c.get("nombre", cid), 30).lower()
            mod = str(plan_a.get("modelo") or plan_a.get("herramienta") or "").strip()
            if plan_a.get("verificado") is not True:
                mod += "*"
            partes.append("%s = %s (%s)" % (etiqueta, mod, prov))
            if len(partes) >= 8:
                break
        if not partes:
            return ""
        return ("Otras IA (el plan A de cada categoría que Claude no cubre; * = sin verificar): %s. "
                "Con datos privados o de clientes: `radar.py elegir <categoría> --sensible`." % " · ".join(partes))
    except Exception:
        return ""


def hoy_lineas(radar, cupos=None):
    """Las líneas de `radar.py hoy`. Sin red, sin comandos lentos."""
    cupos = cupos or cupos_rapidos()
    lineas = []
    modelos = [(a, modelo_de_alias(radar, a)) for a in ("haiku", "sonnet", "opus")]
    modelos = ["%s = %s" % (a.capitalize(), m) for a, m in modelos if m]
    lineas.append("Radar de hoy (datos del %s). Modelos vigentes: %s." % (
        _limpio(radar.get("actualizado", "?"), 10), " · ".join(modelos) if modelos else "sin lista en el radar"))
    ruteo = ruteo_en_una_linea(radar)
    if ruteo:
        lineas.append("Nivel/esfuerzo por tipo de tarea: %s (* = sin medición independiente: vale la política de modelos). Si la tarea tiene más "
                      "«sí» de los que supone la fila (¿hay que juzgar o decidir?, ¿equivocarse sale caro?, ¿hay mucho contexto?), subí un escalón por cada uno." % ruteo)
    nombres = (("claude", "Claude"), ("codex", "Codex"), ("antigravity", "Gemini"))
    libres = [n for k, n in nombres if k != "claude" and cupos.get(k, ("sin_dato",))[0] == "ok"]
    linea = "Cupo: " + " · ".join(_texto_cupo(n, *cupos.get(k, ("sin_dato", None))) for k, n in nombres) + "."
    if libres:
        linea += " Con cupo libre: %s; %s revisiones y trabajo acotado con delegar.py." % (
            " y ".join(libres), "mandale" if len(libres) == 1 else "mandales")
    lineas.append(linea)
    otra = otras_ia_linea(radar)
    if otra:
        lineas.append(otra)
    avisos = []
    base = _limpio(aviso_linea(radar), 300)
    if base:
        avisos.append(base[len("Radar: "):] if base.startswith("Radar: ") else base)
    estado = consejos_estado(radar)
    nuevos = [e for e in estado if e["nuevo"]]
    if nuevos:
        avisos.append("hay consejos de uso nuevos para %s (resumen en %s)" % (
            ", ".join(e["modelo"] for e in nuevos[:3]), _limpio(CONSEJOS_DIR, 160)))
    for prov, titulo, cambio in guias_cambiadas_sin_resumir(radar, estado)[:2]:
        avisos.append("la guía «%s — %s» cambió el %s y sus resúmenes de consejos son anteriores (radar.py consejos)" % (prov, titulo, cambio))
    for nombre, v, vig in _skills_viejas_para_hoy(radar)[:2]:
        avisos.append("la skill %s es de la versión %s y la vigente es %s: actualizala o apagala" % (_limpio(nombre, 60), v, vig))
    for a in planes_atrasados(radar)[:2]:
        avisos.append("salió %s y el plan %s de «%s» sigue en %s" % (
            _limpio(a["vigente"], 64), _limpio(a["plan"], 2), _limpio(a["categoria"], 40), _limpio(a["usa"], 64)))
    try:
        if not avisa_funciones_pendientes():
            raise LookupError   # el cliente recibe RADAR.yaml por la caché pero FUNCIONES.md viaja con el plugin: no se le puede pedir que lo rehaga
        rev_func, _ = cargar_funciones()
        pend = funciones_pendientes(radar, rev_func)
        if pend:
            avisos.append("hay %d cambios en la doc oficial de Claude Code que FUNCIONES.md todavía no refleja (radar.py funciones --pendientes)" % len(pend))
    except Exception:
        pass
    if avisos:
        lineas.append("Aviso: " + "; ".join(avisos) + ".")
    lineas.append("Al abrir un subagente o una sesión: poné `model` y `effort` según este ruteo y lo acotado mandalo a la IA con cupo "
                  "(regla 18: `radar.py elegir <categoría>`). Antes de armar algo a mano, mirá si Claude Code ya lo trae: `radar.py funciones <palabra>`.")
    return [_limpio(x, 700) for x in lineas]


def cmd_hoy(_a):
    try:
        radar, _ = cargar()
        print("\n".join(hoy_lineas(radar)))
    except BaseException:
        pass   # un fallo del radar nunca puede romper el arranque
    return 0


def _rango_modelo(texto):
    t = str(texto or "").lower()
    for nombre in ("haiku", "sonnet", "opus", "fable", "mythos"):
        if nombre in t:
            return NIVELES.get(nombre, NIVELES["fable"]), nombre
    return None, None


def _ya_se_dijo(sesion, tipo):
    """True si en esa sesión ya se mostró el máximo de avisos de ese tipo; si no, lo cuenta. Si la nota local no anda, avisa igual."""
    ruta = carpeta_metodo() / "ruteo-recordado.json"
    try:
        try:
            estado = json.loads(ruta.read_text(encoding="utf-8"))
        except Exception:
            estado = {}
        ahora = time.time()
        estado = {k: v for k, v in estado.items() if isinstance(v, dict) and ahora - v.get("t", 0) < 3 * 86400}
        s = estado.setdefault(_limpio(sesion or "sin-sesion", 80), {"t": ahora})
        if s.get(tipo, 0) >= MAX_AVISOS_POR_SESION[tipo]:
            return True
        s[tipo] = s.get(tipo, 0) + 1
        s["t"] = ahora
        tmp = ruta.with_name("%s.%d.tmp" % (ruta.name, os.getpid()))
        escribir(tmp, json.dumps(dict(list(estado.items())[-200:]), ensure_ascii=False))
        os.replace(str(tmp), str(ruta))
    except Exception:
        pass
    return False


def recordatorio_ruteo(radar, entrada, cupos=None):
    """Texto de recordatorio para un Agent / start_session, o '' si no hay nada que decir. No decide nada."""
    ti = entrada.get("tool_input") if isinstance(entrada.get("tool_input"), dict) else {}
    texto = " ".join(str(ti.get(k) or "") for k in ("description", "title")) + " " + str(ti.get("prompt") or "")[:300]
    fila = fila_para(radar, texto)
    pedido, nombre_pedido = _rango_modelo(ti.get("model"))
    esfuerzo = str(ti.get("effort") or "").strip().lower()
    partes, tipo = [], "sobra"
    if fila:
        holgura = 0 if fila.get("verificado") is True else 1   # fila sin dato independiente: se tolera un escalón de más
        ok_nivel = NIVELES[fila["nivel"]] + holgura
        if pedido and pedido > ok_nivel:
            partes.append("pediste %s y para «%s» el ruteo de hoy dice %s (%s)" % (
                nombre_pedido, _limpio(fila.get("corto") or fila.get("id")), fila["nivel"],
                modelo_de_alias(radar, fila["nivel"]) or "alias " + fila["nivel"]))
        if ESFUERZOS.get(esfuerzo, 0) > ESFUERZOS[fila["esfuerzo"]] + holgura:
            partes.append("esfuerzo %s: para eso el ruteo dice %s" % (esfuerzo, fila["esfuerzo"]))
    if not partes and not pedido:
        tipo = "generico"
        if fila:
            partes.append("sin `model` explícito (hereda el de la sesión o el del agente); para «%s» el ruteo de hoy dice %s/%s" % (
                _limpio(fila.get("corto") or fila.get("id")), fila["nivel"], fila["esfuerzo"]))
        else:
            partes.append("sin `model` explícito (hereda el de la sesión o el del agente); ruteo de hoy: %s" % ruteo_en_una_linea(radar))
    if not partes or _ya_se_dijo(entrada.get("session_id"), tipo):
        return ""
    msg = "Ruteo del radar: " + "; ".join(partes) + "."
    cupos = cupos or cupos_rapidos()
    libres = [n for k, n in (("codex", "Codex"), ("antigravity", "Gemini")) if cupos.get(k, ("sin_dato",))[0] == "ok"]
    if fila and fila.get("otra_ia") and libres:
        msg += " %s tiene cupo: probá `delegar.py %s <repo> <pedido> --archivo` antes de gastar Claude." % (
            " y ".join(libres), _limpio(fila["otra_ia"], 30))
    return msg


def cmd_recordar(_a):
    """Hook PreToolUse de Agent / start_session. Nunca bloquea: no devuelve permissionDecision ni sale con 2."""
    try:
        if sys.stdin is None or sys.stdin.isatty():
            return 0
        crudo = getattr(sys.stdin, "buffer", None)
        texto = crudo.read(1000000).decode("utf-8", "replace") if crudo else sys.stdin.read(1000000)
        if not texto.strip():
            return 0
        entrada = json.loads(texto)
        if not isinstance(entrada, dict) or not isinstance(entrada.get("tool_input"), dict) or not entrada["tool_input"]:
            return 0
        radar, _ = cargar()
        msg = recordatorio_ruteo(radar, entrada)
        if msg:
            print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": msg}}))
    except BaseException:
        pass
    return 0


# --------------------------------------------------------------------------- #
# Consejos de uso por modelo (spec §9) y skills de prompting viejas
# --------------------------------------------------------------------------- #
def _fecha_consejo(texto):
    m = re.search(r"consultada\s+(\d{4}-\d{2}-\d{2})", texto or "")
    return a_fecha(m.group(1)) if m else None


def consejos_estado(radar, carpeta=None):
    """Por cada modelo vigente: si tiene resumen en radar/consejos/<modelo>.md, de qué fecha y si es reciente."""
    carpeta = Path(carpeta) if carpeta else CONSEJOS_DIR
    out = []
    for f in vigentes_por_familia(radar).values():
        api = str(f.get("modelo_api", ""))
        if not ID_MODELO.match(api):
            continue
        ruta, fecha = carpeta / (api + ".md"), None
        try:
            if ruta.is_file() and ruta.stat().st_size < 20000:
                fecha = _fecha_consejo(ruta.read_text(encoding="utf-8")[:400])
        except Exception:
            pass
        out.append({"modelo": api, "familia": f["id"], "ruta": ruta, "existe": ruta.is_file(), "fecha": fecha,
                    "nuevo": bool(fecha and 0 <= (hoy() - fecha).days <= DIAS_CONSEJO_NUEVO)})
    return out


def skills_de_prompting_viejas(radar, base=None):
    """Skills `<gpt|gemini|claude>-<versión>-prompting` instaladas de una generación anterior a la vigente de esa marca (se
    compara solo la versión mayor: gpt-5-4 contra GPT 6.1 sí; gpt-6 contra 6.1 no). Solo mira nombres de carpeta.
    Devuelve [(nombre, versión de la skill, versión vigente)]."""
    base = Path(base) if base else carpeta_config()
    vigentes = {}
    for f in vigentes_por_familia(radar).values():
        hit = familia_de(f.get("modelo_api"), (radar.get("fuentes_auto") or {}).get("familias") or [])
        marca = str(f.get("modelo_api", "")).split("-")[0]
        if hit and (marca not in vigentes or _comparable(hit[1]) > _comparable(vigentes[marca])):
            vigentes[marca] = hit[1]
    out = {}
    for patron in ("skills/*-prompting", "plugins/cache/*/*/*/skills/*-prompting"):
        try:
            carpetas = sorted(base.glob(patron))[:200]
        except Exception:
            continue
        for c in carpetas:
            m = re.fullmatch(r"(gpt|gemini|claude)-(\d{1,2}(?:[.-]\d{1,2})?)-prompting", c.name)
            if not m or m.group(1) not in vigentes:
                continue
            v = _tupla_version(m.group(2))
            if v and v[0] < vigentes[m.group(1)][0]:
                partes = c.relative_to(base).parts
                nombre = "%s:%s" % (partes[3], c.name) if partes[0] == "plugins" and len(partes) > 3 else c.name
                out[nombre] = (nombre, ".".join(map(str, v)), ".".join(map(str, vigentes[m.group(1)])))
    return sorted(out.values())


DIAS_ENTRE_AVISOS_SKILLS = 7


def _skills_viejas_para_hoy(radar):
    """Las skills viejas que toca avisar hoy: como mucho una vez por semana (no se pueden arreglar de un día para otro)."""
    viejas = skills_de_prompting_viejas(radar)
    if not viejas:
        return []
    ruta = carpeta_metodo() / "avisos-radar.json"
    try:
        try:
            estado = json.loads(ruta.read_text(encoding="utf-8"))
        except Exception:
            estado = {}
        ultimo = a_fecha(estado.get("skills_viejas"))
        if ultimo and 0 <= (hoy() - ultimo).days < DIAS_ENTRE_AVISOS_SKILLS:
            return []
        escribir(ruta, json.dumps({"skills_viejas": hoy().isoformat()}))
    except Exception:
        pass
    return viejas


PROVEEDOR_DE_MODELO = {"Anthropic": "claude-", "OpenAI": "gpt-", "Google": "gemini-"}


def guias_cambiadas_sin_resumir(radar, estado):
    """Guías que el robot vio cambiar (`cambio: AAAA-MM-DD`) después de la fecha de los resúmenes de ese proveedor.
    Devuelve [(proveedor, título, fecha del cambio)]. Es la marca que sobrevive cuando el PR del robot se publica solo."""
    out = []
    for g in ((radar.get("fuentes_auto") or {}).get("guias") or {}).values():
        cambio, prefijo = a_fecha(g.get("cambio")), PROVEEDOR_DE_MODELO.get(g.get("proveedor"))
        if not cambio or not prefijo:
            continue
        propios = [e for e in estado if e["modelo"].startswith(prefijo)]
        if any(e["fecha"] is None or e["fecha"] < cambio for e in propios):
            out.append((_limpio(g.get("proveedor"), 20), _limpio(g.get("titulo"), 60), cambio.isoformat()))
    return sorted(out)


def texto_pedido_consejos(radar, modelos, carpeta_guias, extras=()):
    """Texto del pedido para la IA barata. `extras`: [(url, nombre de archivo)] de guías por modelo que se bajaron aparte."""
    guias = (radar.get("fuentes_auto") or {}).get("guias") or {}
    filas = ["- %s — %s (%s): archivo %s/%s.md" % (g.get("proveedor"), g.get("titulo"), g.get("url"), carpeta_guias, gid)
             for gid, g in sorted(guias.items())]
    filas += ["- Guía de un modelo (%s): archivo %s/%s" % (url, carpeta_guias, nombre) for url, nombre in extras]
    pedir = "\n".join("- plugins/metodo/radar/consejos/%s.md" % m for m in modelos)
    return ("Tarea: escribir resúmenes cortos de CÓMO USAR cada modelo, a partir de las guías oficiales de prompting y de migración "
            "que ya están bajadas como archivos de texto (leelas desde el disco; no uses internet).\n\n"
            "Archivos a crear (uno por modelo; si existen, reemplazalos):\n%s\n\n"
            "Guías (leé solo estas):\n%s\n\n"
            "Formato exacto de cada archivo:\n"
            "  - Línea 1: `Fuente: <URL de la guía de donde sale> (consultada %s)`\n"
            "  - Después, de 3 a %d líneas, cada una empieza con `- ` y dice UNA cosa concreta que cambia en cómo usar ESE modelo "
            "(qué conviene escribir o configurar, qué dejó de andar, qué esfuerzo o parámetro usar, qué evitar).\n"
            "Reglas: máximo %d líneas en total después de la Fuente; solo lo que dicen las guías, sin inventar ni completar de memoria; "
            "si las guías no dicen nada propio de ese modelo, una sola línea `- La guía oficial no trae consejos propios para este "
            "modelo; ver la guía de la familia.` más la fuente; castellano simple; no copies párrafos enteros; no escribas claves ni "
            "datos personales. No toques ningún otro archivo y no corras comandos.\n" % (
                pedir, "\n".join(filas), hoy().isoformat(), MAX_LINEAS_CONSEJO, MAX_LINEAS_CONSEJO))


# Guías por modelo que las páginas índice apuntan (se bajan junto con las generales para que la IA las lea del disco).
_ENLACES_POR_MODELO = (
    re.compile(r"https://platform\.claude\.com/docs/en/models/([a-z0-9-]{2,40})/migration-guide"),
    re.compile(r"/api/docs/guides/latest-model/([a-z0-9.-]{2,40})\.md"),
    re.compile(r"https://ai\.google\.dev/gemini-api/docs/whats-new-gemini-([0-9][0-9.]{0,6}[0-9])"),
)
MAX_GUIAS_POR_MODELO = 5   # por proveedor
HOSTS_GUIAS = ("platform.claude.com", "developers.openai.com", "ai.google.dev")


def _url_de_guia_valida(url):
    m = re.fullmatch(r"https://([a-z0-9.-]+)/[A-Za-z0-9._/%-]{1,300}", str(url or ""))
    return bool(m) and m.group(1) in HOSTS_GUIAS and ".." not in str(url)


def guias_por_modelo(textos):
    """[(url, nombre de archivo)] de las guías por modelo que enlazan las generales: las más nuevas de cada proveedor."""
    por_host = {}
    for texto in textos:
        for patron in _ENLACES_POR_MODELO:
            for m in patron.finditer(texto):
                url = m.group(0)
                if url.startswith("/"):
                    url = "https://developers.openai.com" + url
                if "ai.google.dev" in url:
                    url += ".md.txt"      # Google sirve el texto así
                elif not url.endswith(".md"):
                    url += ".md"
                if not _url_de_guia_valida(url):
                    continue
                host = url.split("/")[2]
                nombre = re.sub(r"[^a-z0-9.-]+", "_", "%s_%s" % (host.split(".")[-2], m.group(1))) + ".md"
                orden = [int(x) for x in re.findall(r"\d+", m.group(1))]
                por_host.setdefault(host, {})[url] = (orden, nombre)
    out = []
    for host in sorted(por_host):
        nuevas = sorted(por_host[host].items(), key=lambda kv: kv[1][0], reverse=True)[:MAX_GUIAS_POR_MODELO]
        out += [(url, nombre) for url, (_, nombre) in nuevas]
    return out


def cmd_consejos(a):
    radar, _ = cargar()
    estado = consejos_estado(radar)
    faltan = [e for e in estado if not e["existe"]]
    print("Consejos de uso (%s): %d de %d modelos vigentes tienen resumen." % (CONSEJOS_DIR, len(estado) - len(faltan), len(estado)))
    for e in estado:
        print("  %-24s %s" % (e["modelo"], ("al %s" % e["fecha"]) if e["fecha"] else ("sin fecha" if e["existe"] else "FALTA")))
    for prov, titulo, cambio in guias_cambiadas_sin_resumir(radar, estado):
        print("  guía cambiada: «%s — %s» cambió el %s y los resúmenes de %s son anteriores: rehacerlos con --todo" % (prov, titulo, cambio, prov))
    for nombre, v, vig in skills_de_prompting_viejas(radar):
        print("  skill vieja: %s es de la versión %s y la vigente es %s: actualizala o apagala (regla 19)" % (nombre, v, vig))
    if not a.pedido:
        if faltan or a.todo:
            print("Para que la IA más barata los escriba: radar.py consejos --pedido pedido-consejos.txt%s" % (" --todo" if a.todo else ""))
        return 0
    modelos = [e["modelo"] for e in (estado if a.todo else faltan)]
    if not modelos:
        print("No falta ninguno (con --todo se rehacen todos).")
        return 0
    carpeta = CONSEJOS_DIR / "_guias"
    carpeta.mkdir(parents=True, exist_ok=True)
    for viejo in carpeta.glob("*.md"):   # solo lo que bajó este comando en otra corrida: nunca una guía vieja en el pedido nuevo
        try:
            viejo.unlink()
        except OSError:
            pass
    ok, textos, generales = 0, [], {}
    for gid, g in sorted(((radar.get("fuentes_auto") or {}).get("guias") or {}).items()):
        if not re.fullmatch(r"[a-z0-9_]{1,40}", str(gid)) or not _url_de_guia_valida(g.get("url")):
            print("Aviso: la guía %s no tiene un id o una dirección válidos; la salteo." % _limpio(gid, 40))
            continue
        try:
            _, cuerpo = abrir(g["url"], timeout=40)
            (carpeta / ("%s.md" % gid)).write_bytes(cuerpo[:3000000])
            textos.append(cuerpo[:3000000].decode("utf-8", "replace"))
            generales[gid] = g
            ok += 1
        except Exception as ex:
            print("Aviso: no pude bajar la guía %s (%s)." % (gid, type(ex).__name__))
    if not ok:
        print("No se pudo bajar ninguna guía: no escribo el pedido (la IA inventaría de memoria). Probá de nuevo con internet.")
        return 1
    extras = []
    for url, nombre in guias_por_modelo(textos):
        try:
            _, cuerpo = abrir(url, timeout=40)
            (carpeta / nombre).write_bytes(cuerpo[:3000000])
            extras.append((url, nombre))
        except Exception as ex:
            print("Aviso: no pude bajar %s (%s)." % (url, type(ex).__name__))
    ruta = Path(a.pedido)
    try:
        mostrar = os.path.relpath(str(carpeta))
        if mostrar.startswith(".."):
            mostrar = str(carpeta)
    except ValueError:
        mostrar = str(carpeta)
    sin_bajar = len((radar.get("fuentes_auto") or {}).get("guias") or {}) - len(generales)
    ruta.write_text(texto_pedido_consejos(dict(radar, fuentes_auto={"guias": generales}), modelos, mostrar, extras), encoding="utf-8")
    print("Listo: %d guías bajadas en %s y el pedido para %d modelo(s) en %s." % (ok + len(extras), carpeta, len(modelos), ruta))
    if sin_bajar:
        print("OJO: %d guía(s) general(es) no se pudieron bajar y no están en el pedido; los resúmenes pueden quedar incompletos." % sin_bajar)
    print("Siguiente: python3 plugins/metodo/scripts/delegar.py desarrollo . %s --archivo   (elige Codex o Gemini según el cupo; "
          "si solo queda Claude: un subagente con model haiku y effort low; nunca Opus). Después revisá cada archivo contra su fuente." % ruta)
    return 0


def a_json(radar):
    aviso = aviso_linea(radar)
    campos = ("plan", "herramienta", "proveedor", "modelo", "modelo_api", "por_que", "fuente", "fecha", "condiciones",
              "datos_privados", "como_ver_cupo", "verificado")
    return {
        "actualizado": radar.get("actualizado"),
        "generado": hoy().isoformat(),
        "categorias": [{
            "id": c.get("id"), "nombre": c.get("nombre"),
            "planes": [{k: p.get(k) for k in campos} for p in c.get("planes") or []],
            "ranking": c.get("ranking") or {},
            "evidencia": c.get("evidencia") or [],
            "respaldado": respaldo(c)[1],
        } for c in radar.get("categorias") or []],
        "retiros": radar.get("retiros") or [],
        "vigentes": (radar.get("vigentes") or {}).get("familias") or [],
        "ruteo_claude": ruteo_filas(radar),
        "avisos": [aviso] if aviso else [],
    }


def _esc_tabla(t):
    return str(t or "").replace("|", "\\|")


def a_markdown(radar):
    out = ["# Radar de modelos", "",
           "> Generado desde `RADAR.yaml` (`radar.py md`). No se edita a mano. Última actualización: **%s**." % radar.get("actualizado", "?"),
           "> `[a verificar]` = dato de la investigación que todavía no se leyó de primera mano.", "",
           "Para elegir: `radar.py elegir <categoría>`; si falta el plan A te devuelve el B o el C.", ""]
    vig = (radar.get("vigentes") or {}).get("familias") or []
    if vig:
        out += ["## Modelos vigentes", "", "Último modelo de cada familia (lo escribe el robot; el orden A/B/C de abajo es a mano).", "",
                "| Familia | Modelo | Alta |", "|---|---|---|"]
        for f in vig:
            out.append("| %s | %s | %s |" % (_esc_tabla(f.get("nombre") or f.get("id")), _esc_tabla(f.get("modelo_api")), _esc_tabla(f.get("alta"))))
        out.append("")
    if ruteo_filas(radar):
        out += ["## Ruteo de Claude por tipo de tarea", "", (radar.get("ruteo_claude") or {}).get("nota", ""), "",
                "| Tarea | Nivel | Esfuerzo | ¿Otra IA? |", "|---|---|---|---|"]
        for t in ruteo_filas(radar):
            out.append("| %s | %s | %s | %s |" % (_esc_tabla(t.get("tarea") or t.get("corto")), t["nivel"], t["esfuerzo"],
                                                   _esc_tabla(t.get("otra_ia") or "-")))
        out.append("")
    for c in radar.get("categorias") or []:
        out += ["## %s" % c.get("nombre", c.get("id")), "", texto_respaldo(c), "", "| Plan | Herramienta | Por qué | Datos privados | Condiciones |",
                "|---|---|---|---|---|"]
        for p in c.get("planes") or []:
            out.append("| %s | %s%s | %s | %s | %s |" % (
                p.get("plan"), _esc_tabla(_nombre_plan(p)), marca(p), _esc_tabla(p.get("por_que")),
                "sí" if p.get("datos_privados") else "no", _esc_tabla(p.get("condiciones"))))
        rk = c.get("ranking") or {}
        if rk.get("items"):
            out += ["", "Ranking (%s, %s): " % (rk.get("fuente", "?"), rk.get("fecha", "?")) + "; ".join(
                "%s. %s" % (i.get("puesto"), i.get("modelo")) for i in rk["items"][:5])]
        out.append("")
    if radar.get("retiros"):
        out += ["## Retiros", "", "| Modelo | Proveedor | Fecha | Tipo | Nota |", "|---|---|---|---|---|"]
        for r in radar["retiros"]:
            out.append("| %s | %s | %s | %s | %s |" % (r.get("modelo"), r.get("proveedor"), r.get("fecha"), r.get("tipo", "apagado"),
                                                       _esc_tabla(r.get("nota"))))
        out.append("")
    return "\n".join(out)


def a_html(radar):
    e = _html.escape
    tarjetas = []
    for c in radar.get("categorias") or []:
        filas = "".join("<li><b>%s</b> %s%s<br><small>%s%s</small></li>" % (
            e(str(p.get("plan"))), e(_nombre_plan(p)), "" if p.get("verificado") else " <i>(a verificar)</i>",
            e(p.get("por_que") or ""), "" if p.get("datos_privados") else " — <u>sin datos privados</u>") for p in c.get("planes") or [])
        rk = c.get("ranking") or {}
        top = "".join("<li>%s</li>" % e(str(i.get("modelo"))) for i in (rk.get("items") or [])[:5])
        extra = "<p><small>Ranking: %s</small></p><ol>%s</ol>" % (e(str(rk.get("fuente", "?"))), top) if top else ""
        tarjetas.append("<section><h2>%s</h2><p><small>%s</small></p><ol type=\"A\">%s</ol>%s</section>" % (
            e(str(c.get("nombre", c.get("id")))), e(texto_respaldo(c)), filas, extra))
    ret = "".join("<li>%s — %s (%s)</li>" % (e(str(r.get("modelo"))), e(str(r.get("fecha"))), e(str(r.get("tipo", "apagado"))))
                  for r in radar.get("retiros") or [])
    aviso = aviso_linea(radar)
    return ("<!doctype html><html lang=\"es\"><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
            "<title>Radar de modelos</title><style>body{font:16px system-ui;margin:1rem auto;max-width:60rem;padding:0 1rem}"
            "main{display:grid;grid-template-columns:repeat(auto-fill,minmax(18rem,1fr));gap:1rem}"
            "section{border:1px solid #8884;border-radius:8px;padding:.5rem 1rem}h2{font-size:1.1rem}li{margin:.4rem 0}</style>"
            "<h1>Radar de modelos</h1><p>Actualizado: %s</p>%s<main>%s</main><h2>Retiros</h2><ul>%s</ul></html>" % (
                e(str(radar.get("actualizado", "?"))), "<p><b>%s</b></p>" % e(aviso) if aviso else "", "".join(tarjetas), ret))


# --------------------------------------------------------------------------- #
# Red (solo actualizar y probar). `abrir` se reemplaza en los tests.
# --------------------------------------------------------------------------- #
def abrir(url, cabeceras=None, datos=None, timeout=TIMEOUT_RED):
    req = urllib.request.Request(url, data=datos, headers=dict({"User-Agent": "metodo-radar"}, **(cabeceras or {})))
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read(MAX_BYTES)


def actualizar(abrir_url=None):
    abrir_url = abrir_url or abrir
    destino = carpeta_metodo() / "radar" / "RADAR.yaml"
    try:
        _, cuerpo = abrir_url(URL_PUBLICADO)
        nuevo = yaml_cargar(cuerpo.decode("utf-8"))
        if not (isinstance(nuevo, dict) and nuevo.get("categorias")):
            raise ValueError("el archivo bajado no tiene categorías")
        destino.parent.mkdir(parents=True, exist_ok=True)
        # escritura atómica: otra sesión en paralelo nunca lee el archivo a medias
        tmp = destino.with_name(".RADAR.yaml.%d.tmp" % os.getpid())
        tmp.write_text(cuerpo.decode("utf-8"), encoding="utf-8")
        os.replace(tmp, destino)
        (destino.parent / "comprobado").write_text(hoy().isoformat(), encoding="utf-8")
        return True, "Radar actualizado (datos del %s)." % nuevo.get("actualizado", "?")
    except Exception as ex:
        return False, "Sin red o sin archivo nuevo (%s): sigo con lo último guardado." % type(ex).__name__


def probar(radar, abrir_url=None, entorno=None):
    """Prueba gratis (listar modelos no gasta cupo; Gemini además countTokens). Devuelve {modelo_api: resultado}.
    Las claves se leen por nombre de variable y no se imprimen ni se guardan."""
    abrir_url = abrir_url or abrir
    entorno = os.environ if entorno is None else entorno
    nombrados = {}
    for c in radar.get("categorias") or []:
        for p in c.get("planes") or []:
            if p.get("modelo_api") and p.get("proveedor") in CLAVES:
                nombrados[p["modelo_api"]] = p["proveedor"]
    resultado, fecha = {}, hoy().isoformat()
    listas = {}
    for prov in sorted(set(nombrados.values())):
        clave = entorno.get(CLAVES[prov], "")
        if not clave:
            continue
        try:
            if prov == "Anthropic":
                _, cuerpo = abrir_url("https://api.anthropic.com/v1/models?limit=1000",
                                      {"x-api-key": clave, "anthropic-version": "2023-06-01"})
                listas[prov] = {m.get("id") for m in json.loads(cuerpo).get("data", [])}
            elif prov == "OpenAI":
                _, cuerpo = abrir_url("https://api.openai.com/v1/models", {"Authorization": "Bearer " + clave})
                listas[prov] = {m.get("id") for m in json.loads(cuerpo).get("data", [])}
            else:
                _, cuerpo = abrir_url("https://generativelanguage.googleapis.com/v1beta/models?pageSize=1000",
                                      {"x-goog-api-key": clave})
                listas[prov] = {m.get("name", "").split("/")[-1] for m in json.loads(cuerpo).get("models", [])}
        except Exception as ex:
            listas[prov] = None
            for m, p in nombrados.items():
                if p == prov:
                    resultado[m] = {"disponible": None, "motivo": "no pude consultar (%s)" % type(ex).__name__, "fecha": fecha}
    for m, prov in sorted(nombrados.items()):
        if m in resultado or listas.get(prov) is None:
            continue
        if m not in listas[prov]:
            resultado[m] = {"disponible": False, "motivo": "no figura en la lista de modelos de tu cuenta", "fecha": fecha}
            continue
        if prov == "Google":
            try:
                abrir_url("https://generativelanguage.googleapis.com/v1beta/models/%s:countTokens" % m,
                          {"x-goog-api-key": entorno[CLAVES[prov]], "Content-Type": "application/json"},
                          json.dumps({"contents": [{"parts": [{"text": "hola"}]}]}).encode())
            except urllib.error.HTTPError as ex:
                # solo el 404 prueba que no está; cualquier otro error (401, 403, 429…) no prueba nada, ni que anda
                motivo = "404: no disponible para cuentas nuevas" if ex.code == 404 else "error %d al probarlo" % ex.code
                resultado[m] = {"disponible": False if ex.code == 404 else None, "motivo": motivo, "fecha": fecha}
                continue
            except Exception as ex:
                resultado[m] = {"disponible": None, "motivo": "no pude probarlo (%s)" % type(ex).__name__, "fecha": fecha}
                continue
        resultado[m] = {"disponible": True, "motivo": "ok", "fecha": fecha}
    return resultado


# --------------------------------------------------------------------------- #
# Comandos
# --------------------------------------------------------------------------- #
def escribir(ruta, texto):
    ruta = Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(texto, encoding="utf-8")


def _ids(radar):
    return ", ".join(x["id"] for x in radar["categorias"])


def cmd_ver(a):
    radar, origen = cargar()
    if a.categoria:
        c = buscar_categoria(radar, a.categoria)
        if not c:
            print("No conozco la categoría «%s». Las que hay: %s" % (a.categoria, _ids(radar)))
            return 2
        print(texto_categoria(c))
        return 0
    print("Radar de modelos — actualizado %s (%s)" % (radar.get("actualizado", "?"), origen))
    for c in radar["categorias"]:
        pl = {p.get("plan"): p for p in c.get("planes") or []}
        print("  %-24s A: %s | B: %s | C: %s" % ((c["id"],) + tuple(_nombre_plan(pl[k]) if k in pl else "-" for k in "ABC")))
    linea = aviso_linea(radar)
    if linea:
        print(linea)
    return 0


def cmd_elegir(a):
    radar, _ = cargar()
    c = buscar_categoria(radar, a.categoria)
    if not c:
        print("No conozco la categoría «%s». Las que hay: %s" % (a.categoria, _ids(radar)))
        return 2
    plan, saltados, cache = elegir(radar, c, a.sensible, delegar=getattr(a, "delegar", False))
    if a.json:
        print(json.dumps({"categoria": c["id"], "plan": plan, "respaldado": respaldo(c)[1], "saltados": [{"plan": p.get("plan"), "motivo": m} for p, m in saltados]},
                         ensure_ascii=False))
        return 0 if plan else 1
    if plan is None:
        print("Ningún plan disponible para «%s» ahora. Saltó: %s." % (c["nombre"], "; ".join(
            "%s (%s): %s" % (p.get("plan"), _nombre_plan(p), m) for p, m in saltados)))
        return 1
    print("Usá el plan %s para «%s»: %s%s. %s" % (plan.get("plan"), c["nombre"], _nombre_plan(plan), marca(plan), plan.get("por_que", "")))
    if saltados:
        print("Saltó: " + "; ".join("%s (%s): %s" % (p.get("plan"), p.get("herramienta"), m) for p, m in saltados) + ".")
    if not respaldo(c)[1]:
        print(texto_respaldo(c))
    if plan.get("condiciones"):
        print("Condiciones: " + plan["condiciones"])
    cupo = plan.get("cupo")
    if cupo and cache.get(cupo) and cache[cupo][0] == "alto":
        print("Ojo: " + cache[cupo][1] + " (solo tareas chicas).")
    if plan.get("como_ver_cupo"):
        print("Ver cupo: " + plan["como_ver_cupo"])
    return 0


def cmd_json(a):
    radar, _ = cargar()
    texto = json.dumps(a_json(radar), ensure_ascii=False, indent=2) + "\n"
    if a.stdout:
        sys.stdout.write(texto)
    else:
        ruta = Path(a.salida) if a.salida else carpeta_metodo() / "radar.json"
        escribir(ruta, texto)
        print("Listo: " + str(ruta))
    return 0


def cmd_html(a):
    radar, _ = cargar()
    ruta = Path(a.salida) if a.salida else carpeta_metodo() / "radar.html"
    escribir(ruta, a_html(radar))
    print("Listo: " + str(ruta))
    return 0


def cmd_md(a):
    radar, _ = cargar()
    ruta = Path(a.salida) if a.salida else RADAR_EMPAQUETADO.with_name("RADAR.md")
    escribir(ruta, a_markdown(radar))
    print("Listo: " + str(ruta))
    return 0


def cmd_actualizar(_a):
    print(actualizar()[1])
    return 0


def cmd_probar(a):
    if not (a.si or os.environ.get("RADAR_PROBAR") == "1"):
        print("La prueba está apagada por defecto. Para correrla: «radar.py probar --si» (usa tus claves por variable de "
              "entorno; no gasta cupo).")
        return 0
    radar, _ = cargar()
    sin = [v for v in CLAVES.values() if not os.environ.get(v)]
    res = probar(radar)
    previo = cargar_prueba()
    previo.update(res)
    escribir(carpeta_metodo() / "radar-probe.json", json.dumps(previo, ensure_ascii=False, indent=2) + "\n")
    for m, r in sorted(res.items()):
        print("  %-32s %s — %s" % (m, {True: "anda", False: "NO anda", None: "?"}[r["disponible"]], r["motivo"]))
    if sin:
        print("Sin probar por falta de la variable: " + ", ".join(sin))
    return 0


def cmd_aviso(_a):
    try:
        radar, _ = cargar()
        linea = aviso_linea(radar)
        if linea:
            print(linea)
    except BaseException:
        pass
    return 0


# --------------------------------------------------------------------------- #
# Mapa de funciones oficiales de Claude Code (FUNCIONES.md)
# --------------------------------------------------------------------------- #
def cargar_funciones(ruta=None):
    """Devuelve (revisado, filas). revisado es la fecha YYYY-MM-DD (str o None).
    filas es [{"funcion", "que", "conviene", "no", "doc"}, ...]. Nunca lanza."""
    try:
        p = Path(ruta) if ruta else FUNCIONES_MD
        if not p.is_file():
            return None, []
        texto = p.read_text(encoding="utf-8")
        m = re.search(r"Revisado contra la doc oficial el (\d{4}-\d{2}-\d{2})", texto)
        revisado = m.group(1) if m else None
        filas = []
        for linea in texto.splitlines():
            s = linea.strip()
            if not s.startswith("|"):
                continue
            celdas = [c.strip() for c in s.split("|")]
            if celdas and celdas[0] == "":
                celdas = celdas[1:]
            if celdas and celdas[-1] == "":
                celdas = celdas[:-1]
            if len(celdas) < 5:
                continue
            if celdas[0].lower() in ("función", "funcion") or all(set(c) <= {"-", ":"} for c in celdas):
                continue
            filas.append({
                "funcion": celdas[0],
                "que": celdas[1],
                "conviene": celdas[2],
                "no": celdas[3],
                "doc": celdas[4],
            })
        return revisado, filas
    except Exception:
        return None, []


def avisa_funciones_pendientes():
    """El aviso de FUNCIONES.md desactualizado es para quien mantiene el catálogo: corre desde un clon del repo, o tiene
    RADAR_AVISAR_FUNCIONES=1, o el archivo <config>/metodo/avisar-funciones. A un cliente no le sirve (no puede rehacer la fila)."""
    try:
        return bool(os.environ.get("RADAR_AVISAR_FUNCIONES") or (AQUI.parent.parent.parent / ".git").exists()
                    or (carpeta_metodo() / "avisar-funciones").exists())
    except Exception:
        return False


def funciones_pendientes(radar, revisado):
    """Cambios en la doc oficial posteriores a `revisado`. Lista de textos cortos. Nunca lanza."""
    try:
        docs = (radar.get("fuentes_auto") or {}).get("docs")
        if not isinstance(docs, dict):
            return []
        f_rev = a_fecha(revisado)
        out = []

        nuevas = (docs.get("indice") or {}).get("nuevas") or []
        for item in nuevas:
            if not isinstance(item, str):
                continue
            partes = item.strip().rsplit(None, 1)
            if len(partes) != 2:
                continue
            slug, f_str = partes
            f = a_fecha(f_str)
            if f and (f_rev is None or f > f_rev):
                out.append("página nueva: %s (%s)" % (slug, f.isoformat()))

        paginas = docs.get("paginas") or {}
        if isinstance(paginas, dict):
            for pid, p in paginas.items():
                if not isinstance(p, dict) or not p.get("cambio"):
                    continue
                f = a_fecha(p.get("cambio"))
                if f and (f_rev is None or f > f_rev):
                    titulo = str(p.get("titulo") or pid)
                    out.append("cambió la página: %s (%s)" % (titulo, f.isoformat()))

        changelogs = docs.get("changelogs") or {}
        if isinstance(changelogs, dict):
            for cid, cl in changelogs.items():
                if not isinstance(cl, dict) or not cl.get("cambio"):
                    continue
                f = a_fecha(cl.get("cambio"))
                if f and (f_rev is None or f > f_rev):
                    titulo = str(cl.get("titulo") or cid)
                    version = str(cl.get("version") or "?")
                    out.append("nueva versión de %s: %s (%s)" % (titulo, version, f.isoformat()))

        return out
    except Exception:
        return []


def cmd_funciones(a):
    if getattr(a, "pendientes", False):
        try:
            radar, _ = cargar()
        except BaseException:
            radar = {}
        revisado, _ = cargar_funciones()
        pend = funciones_pendientes(radar, revisado)
        if pend:
            for p in pend:
                print(p)
        else:
            print("Nada pendiente: FUNCIONES.md está al día con la doc.")
        return 0

    revisado, filas = cargar_funciones()
    palabras = [w for w in (getattr(a, "palabras", None) or []) if w.strip()]
    palabras_norm = [_norm(w) for w in palabras if _norm(w)]
    if not palabras_norm:
        for f in filas:
            print(f["funcion"])
        print("%d funciones (revisado %s)." % (len(filas), revisado or "sin fecha"))
        return 0

    coincidencias = []
    for f in filas:
        celdas_norm = [_norm(f.get(k, "")) for k in ("funcion", "que", "conviene", "no", "doc")]
        if all(any(p in c for c in celdas_norm) for p in palabras_norm):
            coincidencias.append(f)

    if not coincidencias:
        print("No hay una función con esas palabras. Probá `radar.py funciones` para ver la lista.")
        return 0

    for f in coincidencias:
        print("▸ %s: %s" % (f["funcion"], f["que"]))
        print("  Conviene: %s" % f["conviene"])
        print("  No conviene: %s" % f["no"])
        print("  Doc: %s" % f["doc"])
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="radar.py", description="Radar de modelos: qué IA usar para cada cosa, con plan B y C.")
    sub = ap.add_subparsers(dest="cmd")
    s = sub.add_parser("ver"); s.add_argument("categoria", nargs="?"); s.set_defaults(f=cmd_ver)
    s = sub.add_parser("elegir"); s.add_argument("categoria"); s.add_argument("--sensible", action="store_true")
    s.add_argument("--delegar", action="store_true")
    s.add_argument("--json", action="store_true"); s.set_defaults(f=cmd_elegir)
    s = sub.add_parser("json"); s.add_argument("--salida"); s.add_argument("--stdout", action="store_true"); s.set_defaults(f=cmd_json)
    s = sub.add_parser("html"); s.add_argument("--salida"); s.set_defaults(f=cmd_html)
    s = sub.add_parser("md"); s.add_argument("--salida"); s.set_defaults(f=cmd_md)
    sub.add_parser("actualizar").set_defaults(f=cmd_actualizar)
    s = sub.add_parser("probar"); s.add_argument("--si", action="store_true"); s.set_defaults(f=cmd_probar)
    sub.add_parser("aviso").set_defaults(f=cmd_aviso)
    sub.add_parser("hoy").set_defaults(f=cmd_hoy)
    s = sub.add_parser("consejos"); s.add_argument("--pedido"); s.add_argument("--todo", action="store_true"); s.set_defaults(f=cmd_consejos)
    sub.add_parser("recordar").set_defaults(f=cmd_recordar)
    s = sub.add_parser("funciones"); s.add_argument("palabras", nargs="*"); s.add_argument("--pendientes", action="store_true"); s.set_defaults(f=cmd_funciones)
    a = ap.parse_args(argv)
    if not getattr(a, "f", None):
        ap.print_help()
        return 1
    try:
        return a.f(a)
    except SystemExit:
        raise
    except Exception as ex:
        print("El radar no pudo (%s: %s)." % (type(ex).__name__, ex))
        return 1


if __name__ == "__main__":
    sys.exit(main())
