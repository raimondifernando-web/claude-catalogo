#!/usr/bin/env python3
"""Catálogo de modelos del radar: TODOS los modelos de TODAS las IA que seguimos, armado solo desde fuentes públicas.

Disparador: automático — `radar.py actualizar` (que lanza solo `radar.py hoy` al abrir sesión, una vez por día) y, cuando se
una el PR del robot (RADAR_CATALOGO=1 en `.github/workflows/radar.yml`), `scripts/radar-fuentes.py` todos los días. A mano:
`radar.py actualizar --directo`. Prueba de disparo: `scripts/tests/test_radar_modelos.py`.

Por qué existe: el radar viejo solo veía las familias para las que alguien había escrito una regla (un patrón por
familia). Un modelo o un proveedor nuevo era invisible hasta que una persona lo anotaba. Acá no hay reglas por modelo:
se baja lo que publican models.dev, OpenRouter y LiteLLM (más la página de modelos de la doc oficial cuando una IA no
está en esas fuentes, como ElevenLabs), se junta todo en `radar/MODELOS.json` y se compara con la corrida anterior. Todo
id que no estaba antes aparece como novedad, de cualquier proveedor seguido; y cualquier laboratorio nuevo en las fuentes
también.

Agregar una IA = una entrada en `fuentes_auto.proveedores` de RADAR.yaml (qué ids usa cada fuente para ese proveedor).
Nada más: los modelos nuevos de esa IA se descubren solos.

Este módulo no hace red por su cuenta salvo en `reconstruir` (recibe la función que baja). Solo biblioteca estándar.
Python 3.6+.
"""
import hashlib
import json
import re
from datetime import date, datetime, timedelta, timezone

DIAS_NUEVO = 14           # un modelo cuenta como «nuevo» en `hoy` durante este tiempo desde su fecha de alta
MAX_NOVEDADES_POR_TIPO = 8
UMBRAL_PRECIO = 0.20      # cambio de precio que se avisa (sube o baja)
UMBRAL_DESAPARECIDOS = 0.30   # si falta más de esto de un proveedor (y más de MIN_DESAPARECIDOS), es la fuente la que falló: no se da nada por retirado
MIN_DESAPARECIDOS = 3

TIPOS = {"chat": "chat", "image": "imagen", "embedding": "embeddings", "video": "video", "speech": "voz",
         "transcription": "transcripción", "reranking": "reordenar", "realtime": "tiempo real", "search": "búsqueda",
         "audio_speech": "voz", "audio_transcription": "transcripción", "image_generation": "imagen",
         "video_generation": "video", "rerank": "reordenar"}

CAMPOS = ("id", "proveedor", "nombre", "familia", "tipo", "estado", "alta", "retiro", "contexto", "salida_max",
          "entrada_usd", "salida_usd", "precio_nota", "razona", "herramientas", "entrada", "salida", "conocimiento",
          "resumen", "fuentes")


# --------------------------------------------------------------------------- #
# Utilidades
# --------------------------------------------------------------------------- #
def _huella(nombre):
    """Huella corta de un nombre de laboratorio: la lista de «ya vistos» se guarda así para que el catálogo público no repita
    en texto cientos de nombres de terceros que solo sirven para detectar uno nuevo (el nombre sale de la fuente del día)."""
    return hashlib.sha1(str(nombre).lower().encode("utf-8")).hexdigest()[:8]


def _clave(texto):
    """Clave para comparar nombres entre fuentes: «Eleven v4», «eleven_v4» y «eleven-v4» dan lo mismo."""
    return re.sub(r"[^a-z0-9]", "", str(texto or "").lower())


def _canon(mid):
    """Id canónico para juntar el mismo modelo entre fuentes (sin prefijo de proveedor; los puntos pasan a guiones:
    OpenRouter dice claude-haiku-5.5 y models.dev claude-haiku-5-5)."""
    return str(mid or "").strip().lower().split("/")[-1].replace(".", "-").replace("_", "-")


def _fecha(v):
    try:
        return datetime.strptime(str(v)[:10], "%Y-%m-%d").date().isoformat()
    except (ValueError, TypeError):
        return None


def _fecha_ts(v):
    try:
        return datetime.fromtimestamp(float(v), timezone.utc).date().isoformat()
    except (TypeError, ValueError, OverflowError, OSError):
        return None


def _num(v):
    if isinstance(v, bool) or v is None:
        return None
    try:
        return round(float(v), 6)
    except (TypeError, ValueError):
        return None


def _por_millon(v):
    """Precio por token → por millón. Se multiplica ANTES de redondear (0.00000015 por token son US$0.15 por millón)."""
    if isinstance(v, bool) or v is None:
        return None
    try:
        return round(float(v) * 1e6, 4)
    except (TypeError, ValueError):
        return None


def _texto(v, largo=240):
    s = re.sub(r"[\x00-\x1f\x7f`]+", " ", str(v or ""))
    return re.sub(r"\s+", " ", s).strip()[:largo] or None


def _lista_a_texto(v):
    if isinstance(v, (list, tuple)):
        v = ",".join(str(x) for x in v)
    return _texto(v, 60)


def _tipo(valor, salidas=None):
    if valor and str(valor) in TIPOS:
        return TIPOS[str(valor)]
    salidas = [str(s) for s in (salidas or [])]
    if "text" in salidas or not salidas:
        return "chat"
    return TIPOS.get(salidas[0], salidas[0])


# --------------------------------------------------------------------------- #
# Lectores de fuentes (reciben el JSON ya bajado; se prueban sin red)
# --------------------------------------------------------------------------- #
def desde_modelsdev(datos, prov):
    """{canon: registro parcial} de los ids de models.dev que le tocan a este proveedor."""
    ids = [str(x) for x in (prov.get("modelsdev") or [])]
    propios = {x.lower() for x in ids} | {str(x).lower() for x in (prov.get("openrouter") or [])} | {str(prov.get("id", "")).lower()}
    out = {}
    for pid in ids:
        entrada = (datos or {}).get(pid)
        modelos = entrada.get("models") if isinstance(entrada, dict) else None
        for mid, m in (modelos or {}).items():
            if not isinstance(m, dict):
                continue
            if "/" in str(mid) and str(mid).split("/")[0] not in ids:
                continue   # modelos de otro laboratorio que este proveedor solo revende: viven en el catálogo de su dueño
            cid = str(m.get("canonical_model_id") or "")
            dueno = cid.split("/")[0].lower() if "/" in cid else ""
            if dueno and dueno not in propios:
                continue   # lo publica otro laboratorio (p. ej. un DeepSeek dentro del listado de Mistral): vive en el catálogo de su dueño
            costo = m.get("cost") or {}
            lim = m.get("limit") or {}
            mod = m.get("modalities") or {}
            estado = m.get("status")
            r = {"id": str(mid), "nombre": _texto(m.get("name") or mid, 80), "familia": _texto(m.get("family"), 40),
                 "retiro": _fecha(m.get("deprecation_date") or m.get("retirement_date") or m.get("sunset_date")),
                 "tipo": _tipo(m.get("type"), mod.get("output")), "alta": _fecha(m.get("release_date")),
                 "contexto": _num(lim.get("context")), "salida_max": _num(lim.get("output")),
                 "entrada_usd": _num(costo.get("input")), "salida_usd": _num(costo.get("output")),
                 "razona": m.get("reasoning") if isinstance(m.get("reasoning"), bool) else None,
                 "herramientas": m.get("tool_call") if isinstance(m.get("tool_call"), bool) else None,
                 "entrada": _lista_a_texto(mod.get("input")), "salida": _lista_a_texto(mod.get("output")),
                 "conocimiento": _texto(m.get("knowledge"), 10), "resumen": _texto(m.get("description")),
                 "_viejo": estado == "deprecated", "_beta": estado in ("beta", "alpha"), "fuente": "models.dev"}
            out[_canon(mid)] = r
    return out


def desde_openrouter(datos, prov):
    prefijos = [str(x).lower() for x in (prov.get("openrouter") or [])]
    out = {}
    for m in (datos or {}).get("data", []) if isinstance(datos, dict) else []:
        mid = str(m.get("id", ""))
        pref, _, resto = mid.partition("/")
        if pref.lower() not in prefijos or not resto or ":" in resto:
            continue   # «:batch», «:free», «:thinking» son variantes de venta del mismo modelo, no modelos
        pr = m.get("pricing") or {}
        arq = m.get("architecture") or {}
        top = m.get("top_provider") or {}
        r = {"id": resto, "nombre": _texto(re.sub(r"^[^:]+:\s*", "", str(m.get("name") or resto)), 80),
             "tipo": _tipo(None, arq.get("output_modalities")), "alta": _fecha_ts(m.get("created")),
             "retiro": _fecha(m.get("expiration_date")),
             "contexto": _num(m.get("context_length") or top.get("context_length")), "salida_max": _num(top.get("max_completion_tokens")),
             "entrada_usd": _por_millon(pr.get("prompt")), "salida_usd": _por_millon(pr.get("completion")),
             "razona": True if "reasoning" in (m.get("supported_parameters") or []) else None,
             "herramientas": True if "tools" in (m.get("supported_parameters") or []) else None,
             "entrada": _lista_a_texto(arq.get("input_modalities")), "salida": _lista_a_texto(arq.get("output_modalities")),
             "conocimiento": _texto(m.get("knowledge_cutoff"), 10), "resumen": _texto(m.get("description")),
             "fuente": "OpenRouter"}
        out[_canon(resto)] = r
    return out


def desde_litellm(datos, prov):
    prefijos = [str(x).lower() + "/" for x in (prov.get("litellm") or [])]
    out = {}
    for nombre, v in (datos or {}).items() if isinstance(datos, dict) else []:
        if not isinstance(v, dict) or not any(str(nombre).lower().startswith(p) for p in prefijos):
            continue
        mid = str(nombre).split("/", 1)[1]
        modo = str(v.get("mode") or "")
        r = {"id": mid, "nombre": _texto(mid, 80), "tipo": _tipo(modo or None), "retiro": _fecha(v.get("deprecation_date")),
             "contexto": _num(v.get("max_input_tokens")), "salida_max": _num(v.get("max_output_tokens")),
             "entrada_usd": _por_millon(v.get("input_cost_per_token")), "salida_usd": _por_millon(v.get("output_cost_per_token")),
             "herramientas": True if v.get("supports_function_calling") else None,
             "razona": True if v.get("supports_reasoning") else None, "fuente": "LiteLLM"}
        meta = v.get("metadata") if isinstance(v.get("metadata"), dict) else {}
        if v.get("input_cost_per_character") is not None:
            r["precio_nota"] = "US$%s por millón de caracteres" % round(float(v["input_cost_per_character"]) * 1e6, 2)
        elif v.get("input_cost_per_second") is not None:
            r["precio_nota"] = "US$%s por hora de audio" % round(float(v["input_cost_per_second"]) * 3600, 2)
        elif v.get("input_cost_per_query") is not None:
            r["precio_nota"] = "US$%s por consulta" % v["input_cost_per_query"]
        if meta.get("notes"):
            r["resumen"] = _texto(meta["notes"])
        out[_canon(mid)] = r
    return out


def nombres_de_doc(texto, patron):
    """Nombres de modelo que lista una página de la doc oficial (patrón con UN grupo). Sin repetidos, en orden."""
    try:
        rx = re.compile(patron, re.M)
    except (re.error, TypeError):
        return []
    vistos, out = set(), []
    for n in rx.findall(texto or ""):
        n = _texto(n, 80)
        if n and _clave(n) not in vistos:
            vistos.add(_clave(n))
            out.append(n)
    return out


# --------------------------------------------------------------------------- #
# Armado del catálogo
# --------------------------------------------------------------------------- #
def _juntar(parciales):
    """Junta los registros de varias fuentes del mismo modelo: la primera que trae un dato manda (orden: models.dev,
    OpenRouter, LiteLLM); las demás solo completan lo que falta. `fuentes` lista todas las que lo conocen."""
    r = {}
    fuentes = []
    for p in parciales:
        fuentes.append(p.get("fuente"))
        for k, v in p.items():
            if k == "fuente":
                continue
            if r.get(k) is None and v is not None:
                r[k] = v
    for k in ("_viejo", "_beta"):
        r[k] = any(p.get(k) for p in parciales)
    r["fuentes"] = [f for f in fuentes if f]
    return r


def _es_alias_latest(mid):
    return bool(re.search(r"(^|[-_/])latest$", str(mid).lower()))


def _es_preview(mid, r):
    return bool(r.get("_beta")) or "preview" in str(mid).lower()


def _familia_derivada(mid):
    """Familia aproximada de un id que ninguna fuente agrupa («eleven_v4» y «eleven_v3» → «eleven»): se sacan los tokens
    que son versión, fecha o tamaño. Solo se usa para decidir cuál es el vigente; no se muestra como dato de la fuente."""
    toks = [x for x in re.split(r"[^a-z0-9]+", _canon(mid)) if x and not re.fullmatch(r"v?\d+[a-z]?|\d+[bm]|a\d+b|latest|preview", x)]
    return "-".join(toks) or None


def _version_id(mid):
    return tuple(int(x) for x in re.findall(r"\d+", _canon(mid))[:4])


def _estados(registros, hoy):
    """Marca el estado de cada modelo. vigente = el más nuevo de su (proveedor, familia, tipo) que no está retirado ni es
    vista previa; los demás de la familia quedan «anterior». Sin familia, cada modelo se juzga solo."""
    grupos = {}
    for r in registros:
        r["estado"] = None
        if r.get("_viejo"):
            r["estado"] = "viejo"
        elif r.get("retiro") and r["retiro"] <= hoy.isoformat():
            r["estado"] = "retirado"
        elif _es_alias_latest(r["id"]):
            r["estado"] = "alias"
        elif r.get("alta") and r["alta"] > hoy.isoformat():
            r["estado"] = "anunciado"   # todavía no salió: no desplaza al vigente de hoy
        else:
            fam = r.get("familia") or _familia_derivada(r["id"])
            if fam:
                grupos.setdefault((r["proveedor"], fam, r.get("tipo")), []).append(r)
            else:
                r["estado"] = "vista previa" if _es_preview(r["id"], r) else "vigente"
    for _, miembros in grupos.items():
        miembros.sort(key=lambda x: (x.get("alta") or "", _version_id(x["id"]), -len(x["id"])), reverse=True)
        elegido = False
        for r in miembros:
            if _es_preview(r["id"], r):
                r["estado"] = "vista previa" if not elegido else "anterior"
            elif not elegido:
                r["estado"], elegido = "vigente", True
            else:
                r["estado"] = "anterior"
        if not elegido:
            miembros[0]["estado"] = "vista previa"
    limite = (hoy - timedelta(days=365)).isoformat()   # en este rubro nada de hace más de un año es «el vigente»
    for r in registros:
        if r["estado"] in ("vigente", "vista previa") and r.get("alta") and r["alta"] < limite:
            r["estado"] = "anterior"
    return registros


BASICOS = ("id", "proveedor", "nombre", "familia", "tipo", "estado", "alta", "retiro", "fuentes")


def _limpiar(r):
    campos = CAMPOS if r.get("estado") in ("vigente", "vista previa", "anterior", None) else BASICOS
    return {k: r.get(k) for k in campos if r.get(k) is not None}


def construir(fuentes, proveedores, previo=None, hoy=None):
    """Arma el catálogo y devuelve (catalogo, novedades).

    fuentes: {"modelsdev": JSON crudo de models.dev, "openrouter": JSON crudo, "litellm": JSON crudo,
              "docs": {proveedor_id: [nombres]}}. Una fuente que falló va como None (no se toma por vacía).
    proveedores: lista `fuentes_auto.proveedores` de RADAR.yaml.
    previo: el catálogo de la corrida anterior (o None: primera vez, solo se fija la línea base).
    Los modelos de la corrida anterior que las fuentes ya no traen se conservan, marcados «retirado», salvo que parezca
    una falla de la fuente (falta más del 30 % de un proveedor)."""
    hoy = hoy or date.today()
    hoy_s = hoy.isoformat()
    previos = {(m.get("proveedor"), _canon(m.get("id"))): m for m in ((previo or {}).get("modelos") or []) if isinstance(m, dict)}
    novedades = {"nuevos": [], "precios": [], "retirados": [], "avisos": [], "proveedores": []}
    todos, por_proveedor = [], {}
    docs = fuentes.get("docs") or {}
    for prov in proveedores or []:
        pid = prov.get("id")
        if not pid:
            continue
        lecturas = []
        if fuentes.get("modelsdev") is not None:
            lecturas.append(desde_modelsdev(fuentes["modelsdev"], prov))
        if fuentes.get("openrouter") is not None:
            lecturas.append(desde_openrouter(fuentes["openrouter"], prov))
        if fuentes.get("litellm") is not None:
            lecturas.append(desde_litellm(fuentes["litellm"], prov))
        # LiteLLM trae modelos viejos sin fecha de todo el mundo: solo cuenta como fuente propia si el proveedor no figura en
        # models.dev ni OpenRouter (ElevenLabs); para los demás solo completa datos de modelos que ya conocen las otras dos.
        cubierto = bool(prov.get("modelsdev") or prov.get("openrouter"))
        claves = []
        for lec in lecturas:
            for c in lec:
                if c not in claves and not (cubierto and next(iter(lec.values()), {}).get("fuente") == "LiteLLM"):
                    claves.append(c)
        registros = []
        for c in claves:
            r = _juntar([lec[c] for lec in lecturas if c in lec])
            r["proveedor"] = pid
            registros.append(r)
        # Modelos que solo figuran en la doc oficial (p. ej. «Scribe v2 Realtime»): sin id de API, se anotan con su nombre.
        conocidas = {_clave(r["id"]) for r in registros} | {_clave(r.get("nombre")) for r in registros}
        for n in docs.get(pid) or []:
            if _clave(n) not in conocidas:
                registros.append({"id": n, "nombre": n, "proveedor": pid, "fuentes": ["doc oficial"], "_viejo": False, "_beta": False,
                                  "tipo": None, "resumen": "Figura en la doc oficial de %s; todavía no aparece en models.dev, OpenRouter ni LiteLLM." % (prov.get("nombre") or pid)})
        tuvo_datos = bool(registros)
        _estados(registros, hoy)
        # lo que estaba y las fuentes ya no traen
        actuales = {_canon(r["id"]) for r in registros}
        ya_retirados = [dict(m) for k, m in previos.items() if k[0] == pid and k[1] not in actuales and m.get("estado") == "retirado"]
        registros.extend(ya_retirados)   # un modelo retirado se queda en el catálogo (la historia no se borra)
        faltan = [m for k, m in previos.items() if k[0] == pid and k[1] not in actuales and m.get("estado") != "retirado"]
        previos_del_proveedor = [m for k, m in previos.items() if k[0] == pid]
        # si alguna fuente que este proveedor usa no respondió, lo que falta puede ser la fuente y no un retiro
        fuente_incompleta = any(fuentes.get(c) is None for c in ("modelsdev", "openrouter", "litellm") if prov.get(c))
        if faltan and tuvo_datos and not fuente_incompleta and len(faltan) <= max(MIN_DESAPARECIDOS, UMBRAL_DESAPARECIDOS * len(previos_del_proveedor)):
            for m in faltan:
                m = dict(m)
                m["estado"] = "retirado"
                registros.append(m)
                novedades["retirados"].append("Dejó de figurar en las fuentes: %s (%s)." % (m.get("nombre") or m.get("id"), prov.get("nombre") or pid))
        elif faltan and tuvo_datos and not fuente_incompleta:
            novedades["avisos"].append("A %s le faltan %d modelos en las fuentes de hoy (de %d); parece una falla de la fuente: los dejo como estaban." % (
                prov.get("nombre") or pid, len(faltan), len(previos_del_proveedor)))
            registros.extend(dict(m) for m in faltan)
        elif faltan:
            registros.extend(dict(m) for m in faltan)   # fuente caída, vacía o a medias: se conserva todo lo anterior tal cual
            novedades["avisos"].append("No pude leer todas las fuentes de modelos de %s; conservo los de la corrida anterior." % (prov.get("nombre") or pid))
        # novedades (solo si hay una corrida anterior con qué comparar)
        if previo:
            for r in registros:
                antes = previos.get((pid, _canon(r["id"])))
                nombre = "%s de %s" % (r.get("nombre") or r["id"], prov.get("nombre") or pid)
                if antes is None:
                    if r.get("estado") in ("vigente", "vista previa", None):
                        novedades["nuevos"].append("Modelo nuevo: %s (%s%s%s)." % (
                            nombre, r["id"], ", alta " + r["alta"] if r.get("alta") else "", _precio_corto(r)))
                    continue
                for campo, rotulo in (("entrada_usd", "entrada"), ("salida_usd", "salida")):
                    a, b = antes.get(campo), r.get(campo)
                    if a and b and abs(b - a) / a >= UMBRAL_PRECIO and r.get("estado") in ("vigente", "anterior"):
                        novedades["precios"].append("Cambió el precio de %s: %s US$%s → US$%s por millón." % (nombre, rotulo, a, b))
        por_proveedor[pid] = len(registros)
        todos.extend(registros)
    # Proveedores nuevos en las fuentes (laboratorios que nadie anotó): solo se anota la lista, sin regla alguna.
    vistos_md = sorted(str(k) for k in (fuentes.get("modelsdev") or {}).keys())
    vistos_or = sorted({str(m.get("id", "")).split("/")[0].lstrip("~").lower() for m in ((fuentes.get("openrouter") or {}).get("data") or []) if "/" in str(m.get("id", ""))})
    if previo and previo.get("vistos_modelsdev"):
        propios = {str(x) for p in (proveedores or []) for x in (p.get("modelsdev") or [])}
        nuevos = [p for p in vistos_md if _huella(p) not in set(previo["vistos_modelsdev"]) and p not in propios]
        if nuevos:
            novedades["proveedores"].append("Proveedores nuevos en models.dev: %s." % _recortar(nuevos))
    if previo and previo.get("vistos_openrouter"):
        propios = {str(x).lower() for p in (proveedores or []) for x in (p.get("openrouter") or [])}
        nuevos = [p for p in vistos_or if _huella(p) not in set(previo["vistos_openrouter"]) and p not in propios]
        if nuevos:
            novedades["proveedores"].append("Laboratorios nuevos en OpenRouter: %s." % _recortar(nuevos))
    orden = {p.get("id"): i for i, p in enumerate(proveedores or [])}
    todos.sort(key=lambda r: (orden.get(r["proveedor"], 99), r["proveedor"], -(int(r["alta"].replace("-", "")) if r.get("alta") else 0), r["id"]))
    h_md = sorted(_huella(p) for p in vistos_md) if fuentes.get("modelsdev") is not None else list((previo or {}).get("vistos_modelsdev") or [])
    h_or = sorted(_huella(p) for p in vistos_or) if fuentes.get("openrouter") is not None else list((previo or {}).get("vistos_openrouter") or [])
    catalogo = {"actualizado": hoy_s,
                "fuentes": "models.dev, OpenRouter, LiteLLM y la doc oficial de los proveedores que no están en esas fuentes",
                "proveedores": {p["id"]: {"nombre": p.get("nombre") or p["id"], "integrado": bool(p.get("integrado")),
                                          "modelos": por_proveedor.get(p["id"], 0)} for p in (proveedores or []) if p.get("id")},
                "vistos_modelsdev": h_md, "vistos_openrouter": h_or,
                "modelos": [_limpiar(r) for r in todos]}
    return catalogo, _aplanar(novedades, previo is None, catalogo)


def _precio_corto(r):
    if r.get("entrada_usd") is not None and r.get("salida_usd") is not None:
        return "; US$%s entrada / US$%s salida por millón" % (r["entrada_usd"], r["salida_usd"])
    return "; " + r["precio_nota"] if r.get("precio_nota") else ""


def _recortar(lista, n=12):
    return ", ".join(lista[:n]) + (" y %d más" % (len(lista) - n) if len(lista) > n else "")


def _aplanar(nov, primera_vez, catalogo):
    if primera_vez:
        return ["Línea base del catálogo de modelos: %d modelos de %d proveedores; desde acá se avisa de cada modelo o proveedor nuevo." % (
            len(catalogo["modelos"]), len(catalogo["proveedores"]))] + nov["avisos"]
    out = []
    for clave in ("nuevos", "precios", "retirados", "proveedores", "avisos"):
        lista = nov[clave]
        out.extend(lista[:MAX_NOVEDADES_POR_TIPO])
        if len(lista) > MAX_NOVEDADES_POR_TIPO:
            out.append("… y %d más del mismo tipo (están en MODELOS.json)." % (len(lista) - MAX_NOVEDADES_POR_TIPO))
    return out


def reconstruir(radar, traer, previo=None, hoy=None, avisar=print):
    """Baja las fuentes de `fuentes_auto` y arma el catálogo. `traer(url, como)` devuelve JSON (como='json') o texto.
    Si ninguna fuente de modelos responde, devuelve (None, [])."""
    fa = radar.get("fuentes_auto") or {}
    proveedores = fa.get("proveedores") or []
    fuentes = {"docs": {}}
    for clave in ("modelsdev", "openrouter", "litellm"):
        if fa.get(clave):
            try:
                fuentes[clave] = traer(fa[clave], "json")
            except Exception as ex:
                avisar("Aviso: no pude leer %s (%s); sigo con el resto." % (clave, type(ex).__name__))
                fuentes[clave] = None
        else:
            fuentes[clave] = None
    if all(fuentes.get(c) is None for c in ("modelsdev", "openrouter", "litellm")):
        return None, []
    for prov in proveedores:
        d = prov.get("docs_modelos")
        if isinstance(d, dict) and d.get("url") and d.get("patron"):
            try:
                fuentes["docs"][prov["id"]] = nombres_de_doc(traer(d["url"], "texto"), d["patron"])
            except Exception as ex:
                avisar("Aviso: no pude leer la doc de modelos de %s (%s)." % (prov.get("nombre") or prov.get("id"), type(ex).__name__))
    return construir(fuentes, proveedores, previo, hoy)


# --------------------------------------------------------------------------- #
# Archivo
# --------------------------------------------------------------------------- #
def a_texto(catalogo):
    """JSON con un modelo por línea (los cambios se ven bien en un diff y se lee rápido)."""
    cab = {k: v for k, v in catalogo.items() if k != "modelos"}
    filas = ",\n".join("  " + json.dumps(m, ensure_ascii=False, sort_keys=False) for m in catalogo.get("modelos") or [])
    cuerpo = json.dumps(cab, ensure_ascii=False, indent=1, sort_keys=False)
    return cuerpo[:-2].rstrip() + ',\n "modelos": [\n' + filas + "\n ]\n}\n"


def desde_texto(texto):
    d = json.loads(texto)
    if not isinstance(d, dict) or not isinstance(d.get("modelos"), list):
        raise ValueError("el catálogo de modelos no tiene la lista de modelos")
    return d


# --------------------------------------------------------------------------- #
# Consultas (lo que usan `hoy`, `ver`, `modelos` y `comparar`)
# --------------------------------------------------------------------------- #
def vigentes(catalogo, proveedor=None, tipo="chat"):
    """Modelos vigentes (más nuevo primero). tipo=None trae todos los tipos."""
    out = [m for m in (catalogo or {}).get("modelos") or []
           if m.get("estado") == "vigente" and (proveedor is None or m.get("proveedor") == proveedor)
           and (tipo is None or m.get("tipo") == tipo)]
    out.sort(key=lambda m: m.get("alta") or "", reverse=True)
    return out


def destacados(catalogo, proveedor, n=5):
    """Los `n` modelos vigentes más nuevos de un proveedor, de cualquier tipo salvo embeddings y reordenar."""
    c = [m for m in vigentes(catalogo, proveedor, None) if m.get("tipo") not in ("embeddings", "reordenar")]
    c.sort(key=lambda m: (m.get("alta") or "", _version_id(m["id"])), reverse=True)
    return c[:n]


def nuevos(catalogo, hoy=None, dias=DIAS_NUEVO):
    """Modelos vigentes o en vista previa con alta de los últimos `dias` días (de cualquier proveedor seguido)."""
    hoy = hoy or date.today()
    desde = (hoy - timedelta(days=dias)).isoformat()
    return sorted((m for m in (catalogo or {}).get("modelos") or []
                   if m.get("estado") in ("vigente", "vista previa") and desde <= (m.get("alta") or "") <= hoy.isoformat()
                   and m.get("tipo") == "chat"),
                  key=lambda m: m.get("alta") or "", reverse=True)


def dias_de(catalogo, hoy=None):
    try:
        return ((hoy or date.today()) - datetime.strptime(str((catalogo or {}).get("actualizado"))[:10], "%Y-%m-%d").date()).days
    except (ValueError, TypeError):
        return None


def buscar(catalogo, texto, proveedor=None):
    """Modelos que calzan con lo que escribió la persona: id exacto, nombre o parte; «opus» o «fable» traen su vigente
    primero. Devuelve lista ordenada (la mejor primera)."""
    q = _clave(texto)
    if not q:
        return []
    exactos, parciales = [], []
    for m in (catalogo or {}).get("modelos") or []:
        if proveedor and m.get("proveedor") != proveedor:
            continue
        ks = {_clave(m.get("id")), _clave(m.get("nombre")), _clave(_canon(m.get("id")))}
        if q in ks:
            exactos.append(m)
        elif any(q in k for k in ks):
            parciales.append(m)
    def peso(m):
        orden_estado = {"vigente": 0, "vista previa": 1, "anunciado": 2, "anterior": 3, "alias": 4, "viejo": 5, "retirado": 6}
        return (orden_estado.get(m.get("estado"), 6), -(int((m.get("alta") or "0").replace("-", "") or 0)), len(m.get("id", "")))
    return sorted(exactos, key=peso) + sorted(parciales, key=peso)


def _fmt_tokens(n):
    if not n:
        return None
    if n >= 1e6:
        return ("%.2f" % (n / 1e6)).rstrip("0").rstrip(".") + " millón"
    return "%d mil" % round(n / 1000)


FILAS = (("Proveedor", lambda m, nom: nom), ("Tipo", lambda m, nom: m.get("tipo")), ("Estado", lambda m, nom: m.get("estado")),
         ("Salió", lambda m, nom: m.get("alta")), ("Familia", lambda m, nom: m.get("familia")),
         ("Contexto (tokens)", lambda m, nom: _fmt_tokens(m.get("contexto"))),
         ("Respuesta máxima (tokens)", lambda m, nom: _fmt_tokens(m.get("salida_max"))),
         ("Precio entrada (por millón)", lambda m, nom: ("US$%s" % m["entrada_usd"]) if m.get("entrada_usd") is not None else m.get("precio_nota")),
         ("Precio salida (por millón)", lambda m, nom: ("US$%s" % m["salida_usd"]) if m.get("salida_usd") is not None else None),
         ("Razona paso a paso", lambda m, nom: {True: "sí", False: "no"}.get(m.get("razona"))),
         ("Usa herramientas", lambda m, nom: {True: "sí", False: "no"}.get(m.get("herramientas"))),
         ("Entiende", lambda m, nom: m.get("entrada")), ("Produce", lambda m, nom: m.get("salida")),
         ("Conocimiento hasta", lambda m, nom: m.get("conocimiento")), ("Se retira", lambda m, nom: m.get("retiro")))


def ficha(m, catalogo):
    nom = ((catalogo.get("proveedores") or {}).get(m.get("proveedor")) or {}).get("nombre") or m.get("proveedor")
    return [(rotulo, f(m, nom)) for rotulo, f in FILAS]


def comparar(catalogo, a, b):
    """Líneas para mostrar la comparación de dos modelos (ya resueltos con `buscar`). Solo datos de las fuentes:
    lo que no hay se dice «sin dato». Devuelve la lista de líneas."""
    fa, fb = dict(ficha(a, catalogo)), dict(ficha(b, catalogo))
    ancho = max(len(r) for r, _ in FILAS)
    lineas = ["%-*s  %-34s  %s" % (ancho, "", (a.get("nombre") or a["id"])[:34], b.get("nombre") or b["id"]),
              "%-*s  %-34s  %s" % (ancho, "id", a["id"][:34], b["id"])]
    for rotulo, _ in FILAS:
        va, vb = fa.get(rotulo), fb.get(rotulo)
        lineas.append("%-*s  %-34s  %s" % (ancho, rotulo, va if va is not None else "sin dato", vb if vb is not None else "sin dato"))
    return lineas


def diferencias(catalogo, a, b):
    """Una línea con lo que cambia entre dos modelos y otra con lo que es igual (solo datos que las dos fuentes traen)."""
    fa, fb = dict(ficha(a, catalogo)), dict(ficha(b, catalogo))
    dist, igual = [], []
    for rotulo, _ in FILAS[1:]:
        va, vb = fa.get(rotulo), fb.get(rotulo)
        if va is None or vb is None:
            continue
        (igual if va == vb else dist).append(rotulo.lower() if va == vb else "%s (%s contra %s)" % (rotulo.lower(), va, vb))
    for campo, rotulo in (("entrada_usd", "la entrada"), ("salida_usd", "la salida")):
        x, y = a.get(campo), b.get(campo)
        if x is None or y is None or x == y:
            continue
        mayor, menor = (b, a) if y > x else (a, b)
        if min(x, y) == 0:
            dist.append("%s es gratis en %s y cuesta US$%s en %s" % (rotulo, menor.get("nombre") or menor["id"], max(x, y), mayor.get("nombre") or mayor["id"]))
        else:
            dist.append("%s cuesta %sx más en %s" % (rotulo, round(max(x, y) / min(x, y), 1), mayor.get("nombre") or mayor["id"]))
    return ["Distinto: " + ("; ".join(dist) if dist else "nada de lo que traen las fuentes") + ".",
            "Igual: " + (", ".join(igual) if igual else "nada") + "."]
