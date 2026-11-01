#!/usr/bin/env python3
"""guia_modelos.py — arma la guía «qué modelo y qué esfuerzo usar» desde el radar del propio paquete.

La guía se carga sola en las sesiones (la ficha global la importa con `@GUIA-MODELOS.md`, ver reglas.py) y se rearma cuando
cambia el radar: lee solo el RADAR.yaml y el MODELOS.json que ya trae el paquete (o la copia más nueva que bajó `radar.py
actualizar`). No usa red, no escribe nada que no sea su archivo y no lleva datos personales: precios, ids y rankings son del
radar (datos de terceros); la política (escalones, alias en `model:`) es la del método.

Uso:  guia_modelos.py            imprime la guía
      guia_modelos.py --probar   autoprueba con datos de mentira

Disparador: encadenado al arranque de sesión — reglas.py (hook SessionStart del paquete metodo) la rearma al abrir cada sesión
y la escribe solo si cambió el radar. Manual: `python3 guia_modelos.py`.
"""
import importlib.util
import re
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
MARCA = "<!-- guia-modelos del paquete metodo: se arma sola desde el radar, no editar a mano -->"

# (id del radar, alias, escalón, para qué) — de barato a caro
CLAUDE = [
    ("claude-haiku-5-5", "haiku", "0 sí", "buscar, contar, listar, mover o resumir algo ya decidido"),
    ("claude-sonnet-5-5", "sonnet", "1 sí", "implementar algo acotado, planillas y datos, investigar en la web, revisar"),
    ("claude-opus-5-5", "opus", "2 sí", "arquitectura, seguridad, plata o algo irreversible; juzgar y decidir"),
    ("claude-fable-5-1", "fable", "3 sí", "SOLO si la persona lo pide: tarea larga y autónoma donde errar sale muy caro"),
]


def corto(n, tope=34):
    n = re.sub(r"\s+", " ", str(n or "")).strip()
    return n if len(n) <= tope else n[:tope - 1] + "…"


def plan_corto(p):
    herr = corto(re.sub(r"\s*\(.*", "", str(p.get("herramienta") or "")), 28)
    modelo = (" (%s)" % corto(p.get("modelo"), 24)) if p.get("modelo") else ""
    sin = " [sin medición independiente]" if "sin dato independiente" in str(p.get("por_que") or "").lower() else ""
    return "%s %s%s%s" % (p.get("plan"), herr, modelo, sin)


def ranking_lineas(radar):
    out = []
    for c in (radar or {}).get("categorias") or []:
        planes = [p for p in c.get("planes") or [] if p.get("plan")]
        if not planes:
            continue
        rk = c.get("ranking") or {}
        items = rk.get("items") or []
        top = " · ".join("%s %s" % (i.get("puesto"), corto(i.get("modelo"))) for i in items[:3])
        marca = " [a verificar]" if rk.get("verificado") is False else ""
        fuente = corto(re.sub(r"\s*\(.*?\)", "", str(rk.get("fuente") or "")), 40)
        linea = "- %s — planes: %s" % (corto(c.get("nombre") or c.get("id"), 40), "; ".join(plan_corto(p) for p in planes))
        linea += (" — ranking %s %s%s: %s" % (fuente, rk.get("fecha"), marca, top)) if top else " — sin ranking cargado todavía"
        out.append(linea)
    return out


def usd(x):
    return ("%g" % x) if x is not None else "?"


def armar(modelos, radar=None, fecha="", con_etapas=False):
    """Texto de la guía. `modelos` = lista del catálogo; `radar` = RADAR.yaml leído; `fecha` = la del radar (no la de hoy,
    así el texto solo cambia cuando cambia el radar); `con_etapas` = el paquete trae `radar.py ruteo <etapa>`."""
    por_id = {m.get("id"): m for m in modelos if isinstance(m, dict)}
    caro = por_id.get("claude-opus-5-5")
    filas = []
    for mid, alias, _escalon, para in CLAUDE:
        m = por_id.get(mid)
        if not m or m.get("estado") != "vigente":
            filas.append("- **%s** (`%s`): el radar no lo da como vigente; mirá `radar.py ver` antes de usarlo." % (alias, mid))
            continue
        extra = ""
        if alias == "fable" and caro and caro.get("entrada_usd"):
            extra = ", %.1f× el precio de Opus" % (m["entrada_usd"] / caro["entrada_usd"])
        filas.append("- **%s** `%s` (US$%s entrada / US$%s salida por millón%s) — %s." % (
            alias, mid, usd(m.get("entrada_usd")), usd(m.get("salida_usd")), extra, para))
    otras = ranking_lineas(radar)
    sec_otras = []
    if otras:
        sec_otras = ["**Quién rinde mejor en qué (radar, %s; los puestos son datos de terceros, no opinión de la sesión):**" % fecha,
                     *otras,
                     "Hay IA mejores que Claude en algunas tareas: el plan A es la primera opción y B/C/D las alternativas. "
                     "El ranking mide modelos; el plan es la herramienta. Para el detalle de cada plan: `radar.py elegir <categoría>`; "
                     "no inventes puestos que acá no figuren.", ""]
    etapas = []
    if con_etapas:
        etapas = ["**Por etapa del trabajo** (explorar, investigar, planear, implementar, probar, revisar, seguridad, documentar, cierre): "
                  "antes de cada tarea, sesión hija o subagente, `radar.py ruteo <etapa>` decide IA, modelo y esfuerzo con el cupo de hoy "
                  "(si toca datos privados, `--sensible`: se queda en Claude).", ""]
    return "\n".join([
        MARCA,
        "# Guía de modelos y esfuerzo — todas las sesiones",
        "Antes de elegir modelo o esfuerzo (sesión, subagente, agente, tarea delegada), usá esta guía; la persona no tiene que pedirlo. "
        "Se arma sola con el radar del método (datos del %s)." % (fecha or "paquete"),
        "Para comparar dos modelos: `radar.py comparar <A> <B>`. Para otra IA (Gemini, Codex, Perplexity…): `radar.py elegir <categoría>`. "
        "`radar.py` es la skill /metodo:radar.",
        "",
        "**Modelos de Claude (precios del radar):**",
        *filas,
        "",
        *sec_otras,
        "**Cómo elegir (3 preguntas):** ¿hay que juzgar o decidir? ¿equivocarse sale caro? ¿hay mucho contexto? "
        "0 «sí» = Haiku · 1 = Sonnet · 2 = Opus · 3 = Fable (solo a pedido). Ante duda entre dos, el más barato; "
        "si la tarea tiene más «sí» de los que supone la fila, subí un escalón por cada uno.",
        "",
        *etapas,
        "**Esfuerzo** (doc oficial de Anthropic): `low` rápido y barato · `medium` equilibrado · `high` calidad alta · "
        "`xhigh` trabajo largo y autónomo · `max` sin tope de gasto, solo a pedido. Anthropic usa por defecto `medium` en "
        "Opus 5.5 y Haiku 5.5, y `high` en Sonnet 5.5 y Fable 5.1. Bajá a `low` solo en tareas mecánicas: Haiku en `low` a veces "
        "corta antes de terminar en agentes largos, ahí usá `medium`. Si el resultado sale flojo, subí un escalón antes de cambiar de modelo.",
        "",
        "**Reglas fijas:** en `model:` de agentes y skills va SIEMPRE el alias (`haiku`/`sonnet`/`opus`), nunca un id de versión; "
        "`fable` no se clava en un agente. Los precios, ids y capacidades se consultan en el radar o con la skill `claude-api`, "
        "nunca de memoria. Cambiar de modelo a mitad de sesión pierde la caché: el cambio se hace en sesión nueva.",
        "",
    ])


def _cargar_radar():
    spec = importlib.util.spec_from_file_location("radar_guia", str(AQUI / "radar.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def texto_actual():
    """Guía armada con los datos del radar instalado, o None si no hay datos válidos (entonces no se pisa nada)."""
    radar_mod = _cargar_radar()
    radar, _ = radar_mod.cargar()
    catalogo, _ = radar_mod.cargar_modelos()
    modelos = (catalogo or {}).get("modelos") or []
    if not any(isinstance(m, dict) and m.get("id") == "claude-opus-5-5" for m in modelos):
        return None
    fecha = str((catalogo or {}).get("actualizado") or (radar or {}).get("actualizado") or "")[:10]
    return armar(modelos, radar, fecha, con_etapas=hasattr(radar_mod, "cmd_ruteo"))


def probar():
    falso = [{"id": "claude-opus-5-5", "estado": "vigente", "entrada_usd": 4.0, "salida_usd": 20.0},
             {"id": "claude-fable-5-1", "estado": "vigente", "entrada_usd": 10.0, "salida_usd": 50.0},
             {"id": "claude-haiku-5-5", "estado": "retirado"}]
    t = armar(falso, fecha="2000-01-01")
    assert t.startswith(MARCA) and "2.5× el precio de Opus" in t and "no lo da como vigente" in t
    assert "`claude-sonnet-5-5`" in t and "US$4 entrada / US$20 salida" in t and "SOLO si la persona lo pide" in t
    assert "Quién rinde mejor" not in t and "radar.py ruteo" not in t
    assert not re.search(r"Fer\b|Mandamiento|TIBP|\bPM\b", t)  # nada personal: es para cualquier cliente
    radar = {"categorias": [{"id": "desarrollo", "nombre": "Desarrollo",
                             "planes": [{"plan": "A", "herramienta": "Claude Code", "modelo": "Opus 5.5"}],
                             "ranking": {"fuente": "Arena", "fecha": "2000-01-01", "verificado": False,
                                         "items": [{"puesto": 1, "modelo": "X"}, {"puesto": 2, "modelo": "Y"}]}},
                            {"id": "video", "nombre": "Video", "planes": [{"plan": "A", "herramienta": "Gemini"}]}]}
    t2 = armar(falso, radar, "2000-01-01", con_etapas=True)
    assert "[a verificar]" in t2 and "1 X" in t2 and "sin ranking cargado todavía" in t2 and "radar.py ruteo" in t2
    assert armar(falso, radar, "2000-01-01") == armar(falso, radar, "2000-01-01")  # estable: sin fecha de hoy
    print("Todo al día ✓ (autoprueba)")


def main(argv):
    if "--probar" in argv:
        probar()
        return 0
    t = texto_actual()
    if t is None:
        print("Falta: el radar instalado no trae a Opus; no armo la guía. ✗")
        return 1
    print(t)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
