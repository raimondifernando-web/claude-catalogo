#!/usr/bin/env python3
"""Actualizador del radar de modelos (lo corre `.github/workflows/radar.yml`; sin IA, sin claves, solo fuentes públicas).

Lee las fuentes abiertas, las compara con `plugins/metodo/radar/RADAR.yaml` y, SOLO si hay un cambio relevante, reescribe
el archivo y deja el motivo en un texto para el PR. Nunca mergea nada: lo aprueba una persona.

Qué cuenta como cambio relevante:
  - cambió el #1 de una categoría (rankings: modo `semanal` o `todo`);
  - se anunció el retiro de un modelo que algún plan nombra (LiteLLM, OpenRouter, models.dev: modo `diario` o `todo`);
  - el precio de un modelo nombrado subió más del 20%;
  - cambió la tabla de una página de retiros (se guarda un hash; la primera vez fija la línea base).

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
from datetime import date, datetime
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


def leer_openrouter(datos):
    out = {}
    for m in (datos or {}).get("data", []):
        pr = m.get("pricing") or {}
        out[str(m.get("id", "")).split("/")[-1]] = {
            "retiro": _fecha(m.get("expiration_date")), "entrada": _por_millon(pr.get("prompt")),
            "salida": _por_millon(pr.get("completion"))}
    return out


def leer_modelsdev(datos):
    out = {}
    for prov in (datos or {}).values():
        modelos = prov.get("models", {}) if isinstance(prov, dict) else {}
        for mid, m in modelos.items():
            if not isinstance(m, dict):
                continue
            costo = m.get("cost") or {}
            retiro = m.get("deprecation_date") or m.get("retirement_date") or m.get("sunset_date")
            out[str(mid).split("/")[-1]] = {"retiro": _fecha(retiro), "entrada": costo.get("input"), "salida": costo.get("output")}
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
                elif actual.get("fecha") != f and actual.get("tipo", "apagado") == "apagado":
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


def juntar(radar, modo, traer_fn=traer, avisar=print):
    fa = radar.get("fuentes_auto") or {}
    fuentes = {"paginas": {}}
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
