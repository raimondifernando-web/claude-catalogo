#!/usr/bin/env python3
"""Actualizador del radar de modelos (lo corre `.github/workflows/radar.yml`; sin IA, sin claves, solo fuentes públicas).

Lee las fuentes abiertas, las compara con `plugins/metodo/radar/RADAR.yaml` y, SOLO si hay un cambio relevante, reescribe
el archivo y deja el motivo en un texto para el PR. Nunca mergea nada: lo aprueba una persona.

Qué cuenta como cambio relevante:
  - cambió el #1 de una categoría (rankings: modo `semanal` o `todo`);
  - se anunció el retiro de un modelo que algún plan nombra (LiteLLM, OpenRouter, models.dev: modo `diario` o `todo`);
  - el precio de un modelo nombrado subió más del 20%;
  - cambió la tabla de una página de retiros (se guarda un hash; la primera vez fija la línea base);
  - salió una versión más nueva de una familia de modelos que sigue el radar (models.dev y OpenRouter): se actualiza la
    sección `vigentes` (es un dato; el robot la puede escribir) y el PR avisa qué planes siguen en la versión vieja.
    El orden A/B/C NO se toca: lo decide una persona (spec §7);
  - cambió una guía oficial de prompting o de migración de Anthropic, OpenAI o Google (huella diaria del texto, sin IA).
    Los resúmenes de `plugins/metodo/radar/consejos/` NO los hace el robot: el aviso del PR dice qué comando correr;
  - huella diaria del índice de páginas de la doc de Claude Code, de las páginas de funciones y de los registros de cambios
    de Claude Code, Codex y Gemini CLI; el aviso del PR dice qué fila de FUNCIONES.md rehacer; este tipo de cambio no se
    publica solo.

Uso:
    radar-fuentes.py --modo diario|semanal|todo [--yaml RUTA] [--motivo RUTA] [--seco]
Sale siempre 0 (una fuente caída se avisa y se sigue). Si hay cambios, escribe `hay_cambios=true` en $GITHUB_OUTPUT.
Python 3.6+. Solo biblioteca estándar.
"""
import argparse
import hashlib
import importlib.util
import json
import os
import re
import sys
import urllib.parse
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
RADAR_PY = RAIZ / "plugins" / "metodo" / "scripts" / "radar.py"
YAML_POR_DEFECTO = RAIZ / "plugins" / "metodo" / "radar" / "RADAR.yaml"
SUBIDA_PRECIO = 1.20


def _radar_mod():
    spec = importlib.util.spec_from_file_location("radar", str(RADAR_PY))
    mod = importlib.util.module_from_spec(spec)
    sys.modules["radar"] = mod
    spec.loader.exec_module(mod)
    return mod


R = _radar_mod()


# --------------------------------------------------------------------------- #
# Lectores de fuentes (cada uno recibe el JSON/HTML ya bajado: se prueban sin red)
# --------------------------------------------------------------------------- #
def _por_millon(v):
    try:
        return round(float(v) * 1e6, 4) if v is not None else None
    except (TypeError, ValueError):
        return None


def _fecha(v):
    try:
        return datetime.strptime(str(v)[:10], "%Y-%m-%d").date().isoformat()
    except (ValueError, TypeError):
        return None


def leer_litellm(datos):
    """{modelo: {retiro, entrada, salida}} con precios por millón de tokens."""
    out = {}
    for nombre, v in (datos or {}).items():
        if not isinstance(v, dict):
            continue
        clave = nombre.split("/")[-1]
        info = {"retiro": _fecha(v.get("deprecation_date")), "entrada": _por_millon(v.get("input_cost_per_token")),
                "salida": _por_millon(v.get("output_cost_per_token"))}
        if clave not in out or (nombre == clave):  # el nombre sin prefijo de proveedor tiene prioridad
            out[clave] = info
    return out


def _fecha_de_timestamp(v):
    try:
        return datetime.fromtimestamp(float(v), timezone.utc).date().isoformat()
    except (TypeError, ValueError, OverflowError, OSError):
        return None


def leer_openrouter(datos):
    out = {}
    for m in (datos or {}).get("data", []):
        pr = m.get("pricing") or {}
        mid = str(m.get("id", ""))
        out[mid.split("/")[-1]] = {
            "retiro": _fecha(m.get("expiration_date")), "entrada": _por_millon(pr.get("prompt")),
            "salida": _por_millon(pr.get("completion")), "alta": _fecha_de_timestamp(m.get("created")),
            "proveedores": [mid.split("/")[0]] if "/" in mid else []}
    return out


def leer_modelsdev(datos):
    out = {}
    for pid, prov in (datos or {}).items():
        modelos = prov.get("models", {}) if isinstance(prov, dict) else {}
        for mid, m in modelos.items():
            if not isinstance(m, dict):
                continue
            costo = m.get("cost") or {}
            retiro = m.get("deprecation_date") or m.get("retirement_date") or m.get("sunset_date")
            clave = str(mid).split("/")[-1]
            alta = _fecha(m.get("release_date"))
            previa = out.get(clave) or {}
            out[clave] = {"retiro": _fecha(retiro), "entrada": costo.get("input"), "salida": costo.get("output"),
                          "alta": min([x for x in (alta, previa.get("alta")) if x], default=None),
                          "proveedores": sorted(set(previa.get("proveedores", [])) | {str(pid)})}
    return out


def leer_arena(filas, filtro=None):
    """Top 5 [(modelo, puntaje)] desde filas del servidor de datasets de Hugging Face ({"rows": [{"row": {...}}]})."""
    puntos = {}
    for f in (filas or {}).get("rows", []):
        r = f.get("row", f) if isinstance(f, dict) else {}
        if filtro and any(str(r.get(k)) != str(v) for k, v in filtro.items()):
            continue
        modelo = r.get("model_name") or r.get("model") or r.get("name")
        puntaje = next((r[k] for k in ("rating", "score", "elo", "arena_score") if isinstance(r.get(k), (int, float))), None)
        if modelo and puntaje is not None:
            puntos[modelo] = max(puntaje, puntos.get(modelo, puntaje))
    orden = sorted(puntos.items(), key=lambda kv: -kv[1])[:5]
    return [(m, round(p)) for m, p in orden]


def hash_tablas(html):
    """Hash estable del texto de las tablas de una página (lo único que importa de una página de retiros)."""
    tablas = re.findall(r"<table.*?</table>", html or "", re.S | re.I)
    if not tablas:
        return None
    texto = " ".join(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t)).strip() for t in tablas)
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()[:16]


def hash_texto(texto):
    """Huella del TEXTO de una guía (se baja la versión .md, sin menús ni scripts). Una página de error o vacía no cuenta."""
    t = re.sub(r"\s+", " ", texto or "").strip()
    return hashlib.sha256(t.encode("utf-8")).hexdigest()[:16] if len(t) >= 200 else None


RE_INDICE_SLUG = re.compile(r"\]\(https://code\.claude\.com/docs/en/([A-Za-z0-9_./-]+?)\.md\)")
RE_SLUG_VALIDO = re.compile(r"^[A-Za-z0-9_./-]{1,120}$")
RE_ATOM_VERSION = re.compile(r"<title>\s*v?(\d+\.\d+\.\d+)\s*</title>")
RE_GEMINI_VERSION = re.compile(r"Latest stable release:\s*v?(\d+\.\d+\.\d+)")


def slugs_de_indice(texto):
    """Lista ordenada sin repetidos de slugs de la doc de Claude Code desde llms.txt.
    Descarta whats-new/ y changelog. Si hay menos de 50 slugs devuelve None (lectura fallida)."""
    if not texto:
        return None
    encontrados = set()
    for s in RE_INDICE_SLUG.findall(texto):
        if s.startswith("whats-new/") or s == "changelog":
            continue
        if not RE_SLUG_VALIDO.match(s):
            continue
        encontrados.add(s)
    ordenados = sorted(encontrados)
    return ordenados if len(ordenados) >= 50 else None


def version_de_changelog(tipo, texto):
    """Extrae la versión 'x.y.z' según el tipo ('atom_estable' o 'gemini_latest')."""
    if not tipo or not texto:
        return None
    if tipo == "atom_estable":
        m = RE_ATOM_VERSION.search(texto)
        return m.group(1) if m else None
    if tipo == "gemini_latest":
        m = RE_GEMINI_VERSION.search(texto)
        return m.group(1) if m else None
    return None


def clave_version(version, corte=None, paso=None):
    """Clave de comparación para detectar versiones relevantes.
    Con corte=2 toma los 2 primeros enteros; si paso > 0 reemplaza el 3° por (3° // paso) y tiene 3 componentes."""
    if not version:
        return ()
    nums = tuple(int(x) for x in re.findall(r"\d+", str(version)))
    if not nums:
        return ()
    try:
        paso_int = int(paso) if paso is not None else None
    except (ValueError, TypeError):
        paso_int = None
    if paso_int and paso_int > 0:
        n0 = nums[0] if len(nums) > 0 else 0
        n1 = nums[1] if len(nums) > 1 else 0
        n2 = nums[2] if len(nums) > 2 else 0
        return (n0, n1, n2 // paso_int)
    if corte == 2:
        return (nums[0] if len(nums) > 0 else 0, nums[1] if len(nums) > 1 else 0)
    if corte:
        try:
            return nums[:int(corte)]
        except (ValueError, TypeError):
            pass
    return nums[:3]



# --------------------------------------------------------------------------- #
# Comparación
# --------------------------------------------------------------------------- #
def modelos_nombrados(radar):
    out = {}
    for c in radar.get("categorias") or []:
        for p in c.get("planes") or []:
            if p.get("modelo_api"):
                out.setdefault(p["modelo_api"], p.get("proveedor"))
    return out


def detectar_vigentes(radar, fuentes, hoy_s=None):
    """Último modelo de cada familia de `fuentes_auto.familias`, mirando models.dev y OpenRouter.
    Devuelve [{id, nombre, alias, modelo_api, alta, fuente}]. Una familia sin candidatos queda fuera (no se inventa nada).
    Un candidato solo vale si lo publica el proveedor de la familia (`proveedor`), calza el patrón anclado, no es una vista
    previa y trae una fecha de alta que no sea futura: lo que llega a las sesiones de los clientes pasa por estos filtros."""
    tope = R.a_fecha(hoy_s) or date.today()
    out = []
    for f in (radar.get("fuentes_auto") or {}).get("familias") or []:
        mejor = None
        for fuente, rotulo in (("modelsdev", "models.dev"), ("openrouter", "OpenRouter")):
            for mid, info in (fuentes.get(fuente) or {}).items():
                hit = R.familia_de(mid, [f])
                if not hit or not R.ID_MODELO.match(hit[2]) or "preview" in hit[2]:
                    continue
                if f.get("proveedor") and f["proveedor"] not in ((info or {}).get("proveedores") or []):
                    continue
                alta = R.a_fecha((info or {}).get("alta"))
                if alta is None or alta > tope + timedelta(days=1):
                    continue
                clave = (R._comparable(hit[1]), -len(hit[2]))   # misma versión: gana el id más corto
                if mejor is None or clave > mejor[0]:
                    mejor = (clave, hit[2], alta.isoformat(), rotulo)
        if mejor:
            fila = {"id": f.get("id"), "nombre": f.get("nombre") or f.get("id"), "modelo_api": mejor[1],
                    "alta": mejor[2], "fuente": mejor[3]}
            if f.get("alias"):
                fila["alias"] = f["alias"]
            out.append(fila)
    return out


def novedades_de_versiones(nuevo, fuentes, hoy_s):
    """Actualiza nuevo['vigentes'] si salió una versión más nueva. Devuelve los motivos para el PR (vacío si no hay novedad).
    Nunca baja una versión (si una fuente pierde un modelo, se queda lo ya anotado)."""
    familias = (nuevo.get("fuentes_auto") or {}).get("familias") or []
    if not familias:
        return []
    hallados = detectar_vigentes(nuevo, fuentes, hoy_s)
    if not hallados:
        return []
    previas = {f["id"]: f for f in ((nuevo.get("vigentes") or {}).get("familias") or []) if isinstance(f, dict) and f.get("id")}
    motivos, resultado, cambio = [], [], False
    orden = list(dict.fromkeys(f.get("id") for f in familias))
    for fila in hallados:
        vieja = previas.get(fila["id"])
        if vieja:
            a, b = R.familia_de(vieja.get("modelo_api"), familias), R.familia_de(fila["modelo_api"], familias)
            if a and b and b[1][0] > a[1][0] + 1:
                continue   # salto de más de una versión mayor: sospechoso, lo anota una persona
            if a and b and R._comparable(b[1]) <= R._comparable(a[1]):
                if R._comparable(b[1]) == R._comparable(a[1]) and not vieja.get("alta") and fila.get("alta"):
                    vieja["alta"] = fila["alta"]   # misma versión: solo se completa la fecha que faltaba
                    cambio = True
                continue
        resultado.append(fila)
        cambio = True
        motivos.append("Salió %s (%s%s; %s)%s." % (
            fila["modelo_api"], fila["nombre"], ", alta " + fila["alta"] if fila.get("alta") else "", fila["fuente"],
            ": antes figuraba %s" % vieja["modelo_api"] if vieja else " (familia nueva en la lista)"))
    if not cambio:
        return []
    mezcla = dict(previas)
    mezcla.update({f["id"]: f for f in resultado})
    nuevo["vigentes"] = {"actualizado": hoy_s, "familias": [mezcla[i] for i in orden if i in mezcla]}
    for a in R.planes_atrasados(nuevo):
        if any(a["vigente"] == f["modelo_api"] for f in resultado):
            motivos.append("El plan %s de «%s» sigue en %s y ya salió %s: el orden A/B/C se cambia a mano (spec §7)." % (
                a["plan"], a["categoria"], a["usa"], a["vigente"]))
    return motivos


COMANDO_CONSEJOS = ("Para resumir los consejos nuevos con la IA más barata: `python3 plugins/metodo/scripts/radar.py consejos --pedido "
                    "pedido-consejos.txt`, después `python3 plugins/metodo/scripts/delegar.py desarrollo . pedido-consejos.txt --archivo` "
                    "(elige Codex o Gemini según el cupo; si solo queda Claude, un subagente con model haiku y effort low; nunca Opus) y "
                    "revisar el resultado a mano (spec §9).")


def novedades_de_guias(nuevo, fuentes, hoy_s):
    """Compara la huella de cada guía de `fuentes_auto.guias`. Guarda la nueva y devuelve los motivos para el PR."""
    guias = (nuevo.get("fuentes_auto") or {}).get("guias") or {}
    motivos = []
    for gid, h in sorted((fuentes.get("guias") or {}).items()):
        entrada = guias.get(gid)
        if not isinstance(entrada, dict) or not h or entrada.get("hash") == h:
            continue
        nombre = "%s — %s" % (entrada.get("proveedor", gid), entrada.get("titulo", gid))
        if not entrada.get("hash"):
            motivos.append("Línea base de la guía «%s»: desde acá se avisa si cambia." % nombre)
        else:
            motivos.append("Cambió la guía oficial «%s» (%s): revisar si cambian los consejos de uso de `plugins/metodo/radar/consejos/`." % (
                nombre, entrada.get("url", "")))
            entrada["cambio"] = hoy_s   # marca que sobrevive aunque el PR se publique solo: `hoy` avisa hasta que se rehagan los resúmenes
        entrada["hash"] = h
    if any(m.startswith("Cambió la guía") for m in motivos):
        motivos.append(COMANDO_CONSEJOS)
    return motivos


def _formato_lista_slugs(slugs):
    if len(slugs) <= 8:
        return ", ".join(slugs)
    return ", ".join(slugs[:8]) + " y %d más" % (len(slugs) - 8)


def _podar_nuevas(nuevas, hoy_s):
    try:
        hoy_d = datetime.strptime(str(hoy_s)[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        hoy_d = date.today()
    limite = hoy_d - timedelta(days=60)
    resultado = []
    for item in nuevas or []:
        if not isinstance(item, str):
            continue
        partes = item.rsplit(" ", 1)
        if len(partes) == 2:
            try:
                f = datetime.strptime(partes[1], "%Y-%m-%d").date()
                if f < limite:
                    continue
            except (ValueError, TypeError):
                pass
        resultado.append(item)
    return resultado


def novedades_de_docs(nuevo, fuentes, hoy_s):
    """Compara índice, páginas de funciones y changelogs de `fuentes_auto.docs`.
    Devuelve los motivos para el PR y actualiza la sección en `nuevo`."""
    fa = nuevo.get("fuentes_auto") or {}
    docs = fa.get("docs")
    if not isinstance(docs, dict):
        return []
    f_docs = fuentes.get("docs")
    if not isinstance(f_docs, dict):
        return []
    motivos = []

    # 1) Índice de docs
    indice_cfg = docs.get("indice")
    f_indice = f_docs.get("indice")
    if isinstance(indice_cfg, dict) and isinstance(f_indice, list):
        if "nuevas" in indice_cfg:
            indice_cfg["nuevas"] = _podar_nuevas(indice_cfg.get("nuevas") or [], hoy_s)
        slugs_validos = [s for s in f_indice if isinstance(s, str) and RE_SLUG_VALIDO.match(s)]
        conocidas = list(indice_cfg.get("conocidas") or [])
        if not conocidas:
            indice_cfg["conocidas"] = sorted(set(slugs_validos))
            motivos.append("Línea base del índice de la doc oficial de Claude Code: %d páginas." % len(indice_cfg["conocidas"]))
        else:
            conocidas_set = set(conocidas)
            nuevos = [s for s in sorted(set(slugs_validos)) if s not in conocidas_set]
            if nuevos:
                indice_cfg["conocidas"] = sorted(conocidas_set | set(nuevos))
                nuevas_lista = list(indice_cfg.get("nuevas") or [])
                for s in nuevos:
                    nuevas_lista.append("%s %s" % (s, hoy_s))
                indice_cfg["nuevas"] = nuevas_lista
                motivos.append(
                    "Páginas nuevas en la doc oficial de Claude Code: %s. Revisar si hay una función que sumar a plugins/metodo/radar/FUNCIONES.md." %
                    _formato_lista_slugs(nuevos)
                )

    # 2) Páginas de funciones
    paginas = docs.get("paginas") or {}
    f_paginas = f_docs.get("paginas") or {}
    for pid, h in sorted(f_paginas.items()):
        entrada = paginas.get(pid)
        if not isinstance(entrada, dict) or not h or entrada.get("hash") == h:
            continue
        titulo = entrada.get("titulo", pid)
        if not entrada.get("hash"):
            motivos.append("Línea base de la página oficial «%s»: desde acá se avisa si cambia." % titulo)
        else:
            motivos.append("Cambió la página oficial «%s» (%s): rehacer su fila de plugins/metodo/radar/FUNCIONES.md." % (
                titulo, entrada.get("url", "")))
            entrada["cambio"] = hoy_s
        entrada["hash"] = h

    # 3) Changelogs
    changelogs = docs.get("changelogs") or {}
    f_changelogs = f_docs.get("changelogs") or {}
    for cid, ver_nueva in sorted(f_changelogs.items()):
        entrada = changelogs.get(cid)
        if not isinstance(entrada, dict) or not ver_nueva:
            continue
        titulo = entrada.get("titulo", cid)
        ver_guardada = entrada.get("version")
        if not ver_guardada:
            entrada["version"] = ver_nueva
            motivos.append("Línea base del registro de cambios de «%s»: v%s." % (titulo, ver_nueva))
        else:
            corte = entrada.get("corte")
            paso = entrada.get("paso")
            clave_guardada = clave_version(ver_guardada, corte, paso)
            clave_nueva = clave_version(ver_nueva, corte, paso)
            if clave_nueva > clave_guardada:   # un backport que aparece después no cuenta como novedad
                motivos.append("Nueva versión de «%s»: antes %s, ahora %s: leer qué funciones trae y actualizar plugins/metodo/radar/FUNCIONES.md." % (
                    titulo, ver_guardada, ver_nueva))
                entrada["version"] = ver_nueva
                entrada["cambio"] = hoy_s

    return motivos



def analizar(radar, fuentes, hoy_f=None):
    """radar: dict cargado. fuentes: {'litellm':{}, 'openrouter':{}, 'modelsdev':{}, 'arena':{cat:[(m,p)]}, 'paginas':{id:hash}}.
    Devuelve (radar_nuevo, motivos). Si motivos == [], radar_nuevo es igual al de entrada y no hay que tocar nada."""
    nuevo = json.loads(json.dumps(radar))
    motivos = []
    hoy_s = (hoy_f or date.today()).isoformat()
    nombrados = modelos_nombrados(nuevo)

    # 1) retiros y precios de los modelos que nombramos
    retiros = nuevo.setdefault("retiros", [])
    precios = nuevo.setdefault("precios_usd_por_millon", {})
    for modelo, prov in sorted(nombrados.items()):
        for fuente in ("litellm", "openrouter", "modelsdev"):
            info = (fuentes.get(fuente) or {}).get(modelo)
            if not info:
                continue
            f = info.get("retiro")
            if f:
                actual = next((r for r in retiros if r.get("modelo") == modelo), None)
                if actual is None:
                    retiros.append({"modelo": modelo, "proveedor": prov, "fecha": f, "tipo": "apagado",
                                    "nota": "Detectado por %s." % fuente, "fuente": fuente, "verificado": False})
                    motivos.append("Retiro anunciado de %s: se apaga el %s (%s)." % (modelo, f, fuente))
                elif actual.get("tipo", "apagado") != "apagado":
                    # teníamos solo «no antes de»: ahora hay fecha de apagado anunciada
                    motivos.append("Se anunció el apagado de %s: el %s (antes: %s %s) (%s)." % (
                        modelo, f, actual.get("tipo"), actual.get("fecha"), fuente))
                    actual.update({"tipo": "apagado", "fecha": f, "fuente": fuente, "verificado": False})
                elif actual.get("fecha") != f:
                    motivos.append("Cambió la fecha de retiro de %s: %s → %s (%s)." % (modelo, actual.get("fecha"), f, fuente))
                    actual["fecha"], actual["fuente"] = f, fuente
            ent, sal = info.get("entrada"), info.get("salida")
            previo = precios.get(modelo)
            if previo and ent is not None and sal is not None:
                sube = [(k, previo[k], v) for k, v in (("entrada", ent), ("salida", sal)) if previo.get(k) and v > previo[k] * SUBIDA_PRECIO]
                if sube:
                    motivos.append("Subió más del 20%% el precio de %s: %s (%s)." % (
                        modelo, ", ".join("%s US$%s → US$%s por millón" % s for s in sube), fuente))
                    precios[modelo] = {"entrada": ent, "salida": sal, "fecha": hoy_s}
            break  # la primera fuente que conoce el modelo manda; las demás solo la validan

    # 2) #1 de cada categoría
    for c in nuevo.get("categorias") or []:
        top = (fuentes.get("arena") or {}).get(c.get("id"))
        if not top:
            continue
        rk = c.setdefault("ranking", {})
        viejo = (rk.get("items") or [{}])[0].get("modelo")
        if top[0][0] != viejo:
            motivos.append("Cambió el #1 de «%s»: %s → %s (Arena)." % (c.get("nombre", c.get("id")), viejo or "sin dato", top[0][0]))
            rk.update({"fuente": "Arena (dataset en Hugging Face)", "fecha": hoy_s, "verificado": False,
                       "items": [{"puesto": i + 1, "modelo": m, "puntaje": p} for i, (m, p) in enumerate(top)]})

    # 3) tablas de las páginas de retiros
    paginas = ((nuevo.get("fuentes_auto") or {}).get("paginas_retiros")) or {}
    for pid, h in sorted((fuentes.get("paginas") or {}).items()):
        entrada = paginas.get(pid)
        if entrada is None or not h:
            continue
        if entrada.get("hash") != h:
            motivos.append("%s la tabla de la página de retiros de %s: revisarla a mano." % (
                "Línea base de" if not entrada.get("hash") else "Cambió", pid))
            entrada["hash"] = h

    # 4) versiones nuevas de las familias que sigue el radar
    motivos += novedades_de_versiones(nuevo, fuentes, hoy_s)

    # 5) guías oficiales de prompting y de migración (huella del texto)
    motivos += novedades_de_guias(nuevo, fuentes, hoy_s)

    # 6) vigía de la documentación oficial (índice, páginas de funciones y changelogs)
    motivos += novedades_de_docs(nuevo, fuentes, hoy_s)

    if not motivos:
        return radar, []
    nuevo["actualizado"] = hoy_s
    return nuevo, motivos


# --------------------------------------------------------------------------- #
# Red y programa principal
# --------------------------------------------------------------------------- #
def traer(url, como="json"):
    _, cuerpo = R.abrir(url, timeout=40)
    texto = cuerpo.decode("utf-8", "replace")
    return json.loads(texto) if como == "json" else texto


def _avisar_actions(texto):
    """En GitHub Actions el aviso sale como anotación visible (si no, una guía ilegible todos los días pasaría desapercibida)."""
    print(("::warning::" if os.environ.get("GITHUB_ACTIONS") == "true" else "") + texto)


def juntar(radar, modo, traer_fn=traer, avisar=_avisar_actions):
    fa = radar.get("fuentes_auto") or {}
    fuentes = {"paginas": {}, "guias": {}}
    if modo in ("diario", "todo"):
        for clave, lector in (("litellm", leer_litellm), ("openrouter", leer_openrouter), ("modelsdev", leer_modelsdev)):
            if fa.get(clave):
                try:
                    fuentes[clave] = lector(traer_fn(fa[clave]))
                except Exception as ex:
                    avisar("Aviso: no pude leer %s (%s); sigo con el resto." % (clave, type(ex).__name__))
        for pid, p in sorted((fa.get("paginas_retiros") or {}).items()):
            try:
                fuentes["paginas"][pid] = hash_tablas(traer_fn(p["url"], "texto"))
            except Exception as ex:
                avisar("Aviso: no pude leer la página de retiros de %s (%s)." % (pid, type(ex).__name__))
        fuentes["guias"] = {}
        for gid, g in sorted((fa.get("guias") or {}).items()):
            try:
                fuentes["guias"][gid] = hash_texto(traer_fn(g["url"], "texto"))
            except Exception as ex:
                avisar("Aviso: no pude leer la guía %s (%s)." % (gid, type(ex).__name__))
        if fa.get("docs"):
            docs_cfg = fa["docs"]
            docs_out = {"indice": None, "paginas": {}, "changelogs": {}}
            if isinstance(docs_cfg.get("indice"), dict) and docs_cfg["indice"].get("url"):
                try:
                    docs_out["indice"] = slugs_de_indice(traer_fn(docs_cfg["indice"]["url"], "texto"))
                except Exception as ex:
                    avisar("Aviso: no pude leer el índice de docs (%s)." % type(ex).__name__)
            for pid, p in sorted((docs_cfg.get("paginas") or {}).items()):
                if isinstance(p, dict) and p.get("url"):
                    try:
                        docs_out["paginas"][pid] = hash_texto(traer_fn(p["url"], "texto"))
                    except Exception as ex:
                        avisar("Aviso: no pude leer la página de docs %s (%s)." % (pid, type(ex).__name__))
            for cid, c in sorted((docs_cfg.get("changelogs") or {}).items()):
                if isinstance(c, dict) and c.get("url"):
                    try:
                        docs_out["changelogs"][cid] = version_de_changelog(c.get("tipo"), traer_fn(c["url"], "texto"))
                    except Exception as ex:
                        avisar("Aviso: no pude leer el changelog %s (%s)." % (cid, type(ex).__name__))
            fuentes["docs"] = docs_out
    if modo in ("semanal", "todo") and fa.get("arena"):
        fuentes["arena"] = {}
        for c in radar.get("categorias") or []:
            cfg = c.get("arena")
            if not cfg:
                continue
            url = fa["arena"] + "&config=" + urllib.parse.quote(str(cfg.get("config"))) + "&split=" + urllib.parse.quote(str(cfg.get("split", "latest")))
            try:
                top = leer_arena(traer_fn(url), cfg.get("filtro"))
                if top:
                    fuentes["arena"][c["id"]] = top
            except Exception as ex:
                avisar("Aviso: no pude leer Arena para «%s» (%s)." % (c.get("id"), type(ex).__name__))
    return fuentes


def main(argv=None):
    ap = argparse.ArgumentParser(description="Actualiza RADAR.yaml desde fuentes públicas; solo escribe si hay un cambio relevante.")
    ap.add_argument("--modo", choices=("diario", "semanal", "todo"), default="todo")
    ap.add_argument("--yaml", default=str(YAML_POR_DEFECTO))
    ap.add_argument("--motivo", help="archivo donde dejar el texto del PR")
    ap.add_argument("--seco", action="store_true", help="muestra los motivos pero no escribe nada")
    a = ap.parse_args(argv)
    ruta = Path(a.yaml)
    try:
        radar = R.leer_yaml(ruta)
        nuevo, motivos = analizar(radar, juntar(radar, a.modo, traer), date.today())
    except Exception as ex:
        print("No se pudo actualizar (%s: %s). No se toca nada." % (type(ex).__name__, ex))
        return 0
    if not motivos:
        print("Sin cambios relevantes (modo %s)." % a.modo)
        return 0
    for m in motivos:
        print("- " + m)
    if a.seco:
        return 0
    cab = "".join(l for l in ruta.read_text(encoding="utf-8").splitlines(True) if l.startswith("#"))
    ruta.write_text(cab + R.yaml_volcar(nuevo) + "\n", encoding="utf-8")
    ruta.with_name("RADAR.md").write_text(R.a_markdown(nuevo), encoding="utf-8")
    if a.motivo:
        Path(a.motivo).write_text("Cambios detectados en las fuentes públicas (modo %s):\n\n%s\n\n"
                                  "Este PR lo abrió una tarea programada, sin IA y sin claves. **Revisalo antes de aprobar**: "
                                  "lo marcado `verificado: false` sigue siendo «a verificar».\n" % (
                                      a.modo, "\n".join("- " + m for m in motivos)), encoding="utf-8")
    salida = os.environ.get("GITHUB_OUTPUT")
    if salida:
        with open(salida, "a", encoding="utf-8") as f:
            f.write("hay_cambios=true\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
