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

`<config>` es $CLAUDE_CONFIG_DIR si está definida; si no, ~/.claude.
Códigos de salida: 0 bien · 1 no hay ningún plan disponible / error de uso · 2 categoría desconocida.
Python 3.6+. Solo biblioteca estándar.
"""
import argparse
import html as _html
import json
import os
import re
import subprocess
import sys
import unicodedata
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RADAR_EMPAQUETADO = AQUI.parent / "radar" / "RADAR.yaml"
CODEX_CUPO = AQUI / "codex-cupo"
URL_PUBLICADO = "https://raw.githubusercontent.com/raimondifernando-web/claude-catalogo/main/plugins/metodo/radar/RADAR.yaml"
DIAS_VIEJO = 14
DIAS_RETIRO_AVISO = 45
DIAS_PRUEBA_VALIDA = 30
TIMEOUT_RED = 20
MAX_BYTES = 8 * 1024 * 1024

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
def cupo_codex():
    """(nivel, texto). nivel: ok | alto | agotado | desconocido. Usa la misma lectura que `codex-cupo`."""
    script = os.environ.get("RADAR_CODEX_CUPO", "").strip() or str(CODEX_CUPO)
    try:
        r = subprocess.run(["bash", script], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
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
    if plan.get("cupo") == "codex":
        if "codex" not in cache_cupo:
            cache_cupo["codex"] = cupo_codex()
        nivel, texto = cache_cupo["codex"]
        if nivel == "agotado":
            return "cupo agotado (%s)" % texto
    return None


def elegir(radar, categoria, sensible=False, prueba=None):
    prueba = cargar_prueba() if prueba is None else prueba
    cache, saltados = {}, []
    for plan in categoria.get("planes") or []:
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


def texto_categoria(c):
    out = ["%s (%s)" % (c.get("nombre", c.get("id")), c.get("id"))]
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


def aviso_linea(radar):
    partes = []
    f = a_fecha(radar.get("actualizado"))
    if f is None or (hoy() - f).days > DIAS_VIEJO:
        partes.append("el radar de modelos tiene %s (corré «radar.py actualizar»)" % (
            "fecha desconocida" if f is None else "%d días" % (hoy() - f).days))
    prox = retiros_proximos(radar)
    if prox:
        r, donde = prox[0]
        partes.append("se retira %s el %s y lo usa el plan %s%s" % (
            r["modelo"], r["fecha"], donde[0], " (+%d más)" % (len(prox) - 1) if len(prox) > 1 else ""))
    return "Radar: " + "; ".join(partes) if partes else ""


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
        } for c in radar.get("categorias") or []],
        "retiros": radar.get("retiros") or [],
        "avisos": [aviso] if aviso else [],
    }


def _esc_tabla(t):
    return str(t or "").replace("|", "\\|")


def a_markdown(radar):
    out = ["# Radar de modelos", "",
           "> Generado desde `RADAR.yaml` (`radar.py md`). No se edita a mano. Última actualización: **%s**." % radar.get("actualizado", "?"),
           "> `[a verificar]` = dato de la investigación que todavía no se leyó de primera mano.", "",
           "Para elegir: `radar.py elegir <categoría>`; si falta el plan A te devuelve el B o el C.", ""]
    for c in radar.get("categorias") or []:
        out += ["## %s" % c.get("nombre", c.get("id")), "", "| Plan | Herramienta | Por qué | Datos privados | Condiciones |",
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
        tarjetas.append("<section><h2>%s</h2><ol type=\"A\">%s</ol>%s</section>" % (e(str(c.get("nombre", c.get("id")))), filas, extra))
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
        destino.write_text(cuerpo.decode("utf-8"), encoding="utf-8")
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
                if ex.code == 404:
                    resultado[m] = {"disponible": False, "motivo": "404: no disponible para cuentas nuevas", "fecha": fecha}
                    continue
            except Exception:
                pass
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
    plan, saltados, cache = elegir(radar, c, a.sensible)
    if a.json:
        print(json.dumps({"categoria": c["id"], "plan": plan, "saltados": [{"plan": p.get("plan"), "motivo": m} for p, m in saltados]},
                         ensure_ascii=False))
        return 0 if plan else 1
    if plan is None:
        print("Ningún plan disponible para «%s» ahora. Saltó: %s." % (c["nombre"], "; ".join(
            "%s (%s): %s" % (p.get("plan"), _nombre_plan(p), m) for p, m in saltados)))
        return 1
    print("Usá el plan %s para «%s»: %s%s. %s" % (plan.get("plan"), c["nombre"], _nombre_plan(plan), marca(plan), plan.get("por_que", "")))
    if saltados:
        print("Saltó: " + "; ".join("%s (%s): %s" % (p.get("plan"), p.get("herramienta"), m) for p, m in saltados) + ".")
    if plan.get("condiciones"):
        print("Condiciones: " + plan["condiciones"])
    if plan.get("cupo") == "codex" and cache.get("codex") and cache["codex"][0] == "alto":
        print("Ojo: " + cache["codex"][1] + " (solo tareas chicas).")
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


def main(argv=None):
    ap = argparse.ArgumentParser(prog="radar.py", description="Radar de modelos: qué IA usar para cada cosa, con plan B y C.")
    sub = ap.add_subparsers(dest="cmd")
    s = sub.add_parser("ver"); s.add_argument("categoria", nargs="?"); s.set_defaults(f=cmd_ver)
    s = sub.add_parser("elegir"); s.add_argument("categoria"); s.add_argument("--sensible", action="store_true")
    s.add_argument("--json", action="store_true"); s.set_defaults(f=cmd_elegir)
    s = sub.add_parser("json"); s.add_argument("--salida"); s.add_argument("--stdout", action="store_true"); s.set_defaults(f=cmd_json)
    s = sub.add_parser("html"); s.add_argument("--salida"); s.set_defaults(f=cmd_html)
    s = sub.add_parser("md"); s.add_argument("--salida"); s.set_defaults(f=cmd_md)
    sub.add_parser("actualizar").set_defaults(f=cmd_actualizar)
    s = sub.add_parser("probar"); s.add_argument("--si", action="store_true"); s.set_defaults(f=cmd_probar)
    sub.add_parser("aviso").set_defaults(f=cmd_aviso)
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
