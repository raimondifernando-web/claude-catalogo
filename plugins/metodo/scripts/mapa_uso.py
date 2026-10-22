#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mapa_uso.py - Medición de uso real a partir de conversaciones (.jsonl) y contador interno de Claude Code.
Disparador: encadenado — lo usa mapa.py (el comando `mapa`).

Analiza historiales de conversaciones y skillUsage sin registrar firmas en el mapa de disco.
Python 3.9 estándar, sin librerías externas.
"""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Set, Tuple, Union

# Agentes que trae Claude Code de fábrica: no están en disco, pero se usan.
AGENTES_DE_FABRICA = {
    "general-purpose", "Explore", "Plan", "statusline-setup", "claude-code-guide",
    "claude", "output-style-setup",
}

# Skills y comandos que traen Claude Code o la app de fábrica (o por conector): aparecen en la lista de las
# sesiones, pero no existen como carpeta en ~/.claude. Lista tomada de la lista de skills de una sesión real.
SKILLS_DE_FABRICA = {
    "update-config", "keybindings-help", "code-review", "simplify", "fewer-permission-prompts", "loop",
    "claude-api", "workflow-authoring", "run", "plugin-authoring", "init", "security-review", "dataviz",
    "artifact-design", "artifact-diagramming", "artifact-capabilities",
    "anthropic-skills:consolidate-memory", "anthropic-skills:explain-usage",
    "anthropic-skills:schedule", "anthropic-skills:setup-claude",
}

COMANDOS_DE_FABRICA = {
    "/model", "/doctor", "/mcp", "/usage", "/skill-doctor", "/auto-mode-setup", "/clear",
    "/compact", "/help", "/config", "/memory", "/agents", "/permissions", "/hooks", "/context",
    "/cost", "/resume", "/status", "/review", "/init",
}

CATEGORIAS_USO = ("skills", "agents", "mcp_servers", "mcp_tools", "herramientas_nativas", "slash_commands")


def parse_iso_o_mtime(ts_val: Any, mtime_dt: datetime) -> datetime:
    """Parsea una marca de tiempo ISO de manera tolerante (Python 3.9+) o usa el mtime del archivo."""
    if ts_val and isinstance(ts_val, str):
        s = ts_val.strip()
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(s)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            pass
    elif isinstance(ts_val, (int, float)):
        try:
            if ts_val > 1e11:  # milisegundos
                return datetime.fromtimestamp(ts_val / 1000.0, tz=timezone.utc)
            return datetime.fromtimestamp(ts_val, tz=timezone.utc)
        except Exception:
            pass

    if mtime_dt.tzinfo is None:
        return mtime_dt.replace(tzinfo=timezone.utc)
    return mtime_dt


def es_conversacion_de_subagente(archivo: Path) -> bool:
    """Los .jsonl de subagentes y workflows viven bajo una carpeta `subagents/`."""
    return "subagents" in archivo.parts


def id_de_sesion(archivo: Path, es_sub: bool) -> str:
    """Sesión = el UUID de la conversación principal (los subagentes se atribuyen a su sesión madre)."""
    if es_sub:
        partes = archivo.parts
        i = partes.index("subagents")
        return partes[i - 1] if i > 0 else archivo.stem
    return archivo.stem


def texto_de_mensaje_usuario(record: Dict[str, Any]) -> str:
    """Texto plano de un mensaje de usuario (solo para detectar `<command-name>`; no se guarda)."""
    msg = record.get("message")
    c = msg.get("content") if isinstance(msg, dict) else record.get("content")
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        return " ".join(str(b.get("text") or "") for b in c if isinstance(b, dict) and b.get("type") == "text")
    return ""


def medir_uso_real(claude_dir: Path) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, int]]:
    """
    Lee ~/.claude/projects/**/*.jsonl y extrae únicamente frecuencias y fechas.
    NO retiene ningún texto de las conversaciones. Separa conversaciones principales
    (las que abre Fernando, ámbito "p") de las de subagentes/workflows (ámbito "s").
    Devuelve (stats_crudas, metricas). Las stats crudas guardan sets de sesiones y se
    serializan después con `serializar_uso`.
    """
    projects_dir = claude_dir / "projects"
    metricas: Dict[str, int] = {
        "archivos_jsonl_leidos": 0, "archivos_principales": 0, "archivos_subagentes": 0,
        "lineas_leidas": 0, "lineas_no_parseadas": 0,
    }
    stats: Dict[str, Dict[str, Dict[str, Any]]] = {c: {} for c in CATEGORIAS_USO}
    if not projects_dir.is_dir():
        return stats, metricas

    archivos = sorted(projects_dir.rglob("*.jsonl"), key=lambda p: str(p))
    ahora = datetime.now(timezone.utc)
    s30 = 30 * 86400
    s90 = 90 * 86400
    # `<command-name>/algo</command-name>` al comienzo de un mensaje de usuario
    regex_slash = re.compile(r"<command-name>\s*([^<\s]+)\s*</command-name>")

    def ambito_vacio(dt: datetime) -> Dict[str, Any]:
        return {"t": 0, "d30": 0, "d90": 0, "primera": dt, "ultima": dt, "ses": set()}

    def registrar(cat: str, nombre: str, dt: datetime, sesion: str, es_sub: bool) -> None:
        if not nombre:
            return
        d = stats[cat]
        it = d.get(nombre)
        if it is None:
            it = {"p": ambito_vacio(dt), "s": ambito_vacio(dt)}
            d[nombre] = it
        a = it["s" if es_sub else "p"]
        a["t"] += 1
        delta = (ahora - dt).total_seconds()
        if delta <= s30:
            a["d30"] += 1
        if delta <= s90:
            a["d90"] += 1
        a["ses"].add(sesion)
        if dt < a["primera"] or a["t"] == 1:
            a["primera"] = dt
        if dt > a["ultima"] or a["t"] == 1:
            a["ultima"] = dt

    for archivo in archivos:
        es_sub = es_conversacion_de_subagente(archivo)
        metricas["archivos_jsonl_leidos"] += 1
        metricas["archivos_subagentes" if es_sub else "archivos_principales"] += 1
        sesion = id_de_sesion(archivo, es_sub)
        try:
            mtime_dt = datetime.fromtimestamp(archivo.stat().st_mtime, tz=timezone.utc)
        except Exception:
            mtime_dt = ahora
        try:
            with open(archivo, "r", encoding="utf-8", errors="replace") as f:
                for linea in f:
                    metricas["lineas_leidas"] += 1
                    # Filtro rápido: solo interesan los tool_use y los comandos slash
                    if "tool_use" not in linea and "<command-name>" not in linea:
                        continue
                    try:
                        record = json.loads(linea)
                    except Exception:
                        metricas["lineas_no_parseadas"] += 1
                        continue
                    if not isinstance(record, dict):
                        continue
                    dt = parse_iso_o_mtime(record.get("timestamp") or record.get("time") or record.get("createdAt"), mtime_dt)

                    msg = record.get("message")
                    bloques = []
                    if isinstance(msg, dict) and isinstance(msg.get("content"), list):
                        bloques.extend(msg["content"])
                    if isinstance(record.get("content"), list):
                        bloques.extend(record["content"])
                    for b in bloques:
                        if not isinstance(b, dict) or b.get("type") != "tool_use":
                            continue
                        tool_name = str(b.get("name") or "")
                        inp = b.get("input") if isinstance(b.get("input"), dict) else {}
                        if tool_name == "Skill":
                            if inp.get("skill"):
                                registrar("skills", str(inp["skill"]), dt, sesion, es_sub)
                        elif tool_name in ("Agent", "Task"):
                            if inp.get("subagent_type"):
                                registrar("agents", str(inp["subagent_type"]), dt, sesion, es_sub)
                        elif tool_name.startswith("mcp__"):
                            partes = tool_name.split("__")
                            registrar("mcp_servers", partes[1] if len(partes) > 1 else tool_name, dt, sesion, es_sub)
                            registrar("mcp_tools", tool_name, dt, sesion, es_sub)
                        elif tool_name:
                            registrar("herramientas_nativas", tool_name, dt, sesion, es_sub)

                    # Slash commands: SOLO cuando el mensaje del usuario ARRANCA con la etiqueta
                    # (así no se cuentan las veces que una respuesta o un archivo la mencionan).
                    # Dentro de una conversación de subagente, el slash es la PRECARGA de una skill.
                    if "<command-name>" in linea and record.get("type") == "user":
                        texto = texto_de_mensaje_usuario(record).lstrip()
                        if texto.startswith(("<command-message>", "<command-name>")):
                            m = regex_slash.search(texto)
                            if m:
                                cmd = m.group(1).strip()
                                if not cmd.startswith("/"):
                                    cmd = "/" + cmd
                                # Un nombre de comando es corto y sin signos raros; lo demás (parámetros pegados) no entra al mapa.
                                if re.fullmatch(r"/[A-Za-z0-9_:.\-/]{1,64}", cmd):
                                    registrar("slash_commands", cmd, dt, sesion, es_sub)
        except Exception:
            metricas["lineas_no_parseadas"] += 1

    return stats, metricas


def serializar_uso(stats: Dict[str, Dict[str, Dict[str, Any]]]) -> Dict[str, Dict[str, Any]]:
    """Convierte las stats crudas en estructura JSON (sin sets). Dos ámbitos: principal y subagentes."""
    out: Dict[str, Dict[str, Any]] = {}
    for cat, items in stats.items():
        out[cat] = {}
        for nombre, v in sorted(items.items()):
            p, s = v["p"], v["s"]
            fechas_p = [p["primera"], p["ultima"]] if p["t"] else []
            fechas_s = [s["primera"], s["ultima"]] if s["t"] else []
            todas = fechas_p + fechas_s
            out[cat][nombre] = {
                "usos_total": p["t"] + s["t"], "usos_30d": p["d30"] + s["d30"], "usos_90d": p["d90"] + s["d90"],
                "usos_principal": p["t"], "usos_principal_30d": p["d30"], "usos_principal_90d": p["d90"],
                "usos_subagentes": s["t"], "usos_subagentes_30d": s["d30"], "usos_subagentes_90d": s["d90"],
                "primera_vez": min(todas).isoformat() if todas else None,
                "ultima_vez": max(todas).isoformat() if todas else None,
                "ultima_vez_principal": p["ultima"].isoformat() if p["t"] else None,
                "sesiones_principal": len(p["ses"]), "sesiones_subagentes": len(s["ses"]),
                "cantidad_sesiones": len(p["ses"] | s["ses"]),
            }
    return out


def _leer_json(ruta: Path) -> Any:
    """Lee un JSON de forma tolerante; devuelve None si falla."""
    try:
        with open(ruta, "r", encoding="utf-8", errors="replace") as f:
            return json.load(f)
    except Exception:
        return None


def leer_contador_interno_skills(home: Path) -> Dict[str, Dict[str, Any]]:
    """
    `skillUsage` de ~/.claude.json: el contador propio de Claude Code (cuenta tanto /slash como la herramienta Skill).
    SOLO nombre, cantidad y fecha: no se toca nada más de ese archivo.
    """
    d = _leer_json(home / ".claude.json")
    su = d.get("skillUsage") if isinstance(d, dict) else None
    out: Dict[str, Dict[str, Any]] = {}
    if isinstance(su, dict):
        for k, v in su.items():
            if isinstance(v, dict) and isinstance(v.get("usageCount"), int):
                ts = v.get("lastUsedAt")
                fecha = datetime.fromtimestamp(ts / 1000.0, tz=timezone.utc).isoformat() if isinstance(ts, (int, float)) else None
                out[str(k)] = {"usageCount": v["usageCount"], "ultima_vez": fecha}
    return out


def medir(
    claude_dir: Union[str, Path],
    home: Union[str, Path],
) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, int], Dict[str, Dict[str, Any]]]:
    """
    Firma pública: realiza la medición completa de uso real.
    Devuelve (stats_crudas, metricas, contador_interno).
    """
    c_dir = Path(claude_dir)
    h_dir = Path(home)
    stats, metricas = medir_uso_real(c_dir)
    contador = leer_contador_interno_skills(h_dir)
    return stats, metricas, contador


def a_json(
    stats: Dict[str, Any],
    metricas: Dict[str, Any],
    contador: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Convierte (stats, metricas, contador) a un dict 100 % serializable por json.dumps.

    Conversión de tipos:
      - Los conjuntos `set` de identificadores de sesión en `ses` se transforman en listas ordenadas `list`.
      - Los objetos `datetime` en `primera` y `ultima` se transforman en cadenas ISO 8601 (`str`).
    """
    stats_json: Dict[str, Any] = {}
    for cat, items in stats.items():
        stats_json[cat] = {}
        for nombre, amb in items.items():
            amb_json: Dict[str, Any] = {}
            for k in ("p", "s"):
                v = amb.get(k, {})
                primera = v.get("primera")
                ultima = v.get("ultima")
                ses = v.get("ses", set())
                amb_json[k] = {
                    "t": v.get("t", 0),
                    "d30": v.get("d30", 0),
                    "d90": v.get("d90", 0),
                    "primera": primera.isoformat() if isinstance(primera, datetime) else (str(primera) if primera else None),
                    "ultima": ultima.isoformat() if isinstance(ultima, datetime) else (str(ultima) if ultima else None),
                    "ses": sorted(list(ses)) if isinstance(ses, (set, list)) else [],
                }
            stats_json[cat][nombre] = amb_json

    return {
        "stats": stats_json,
        "metricas": dict(metricas),
        "contador": dict(contador),
    }


def de_json(d: Dict[str, Any]) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, int], Dict[str, Dict[str, Any]]]:
    """
    Inversa exacta de a_json: reconstruye la tupla (stats, metricas, contador).

    Conversión inversa:
      - Las listas de sesiones `ses` vuelven a ser conjuntos `set`.
      - Las cadenas ISO de `primera` y `ultima` vuelven a ser objetos `datetime` con tzinfo UTC.
    """
    stats_in = d.get("stats", {})
    metricas = dict(d.get("metricas", {}))
    contador = dict(d.get("contador", {}))

    ahora = datetime.now(timezone.utc)
    stats: Dict[str, Dict[str, Any]] = {c: {} for c in CATEGORIAS_USO}

    def _parse_fecha(v: Any) -> datetime:
        if isinstance(v, str):
            try:
                dt = datetime.fromisoformat(v)
                return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
            except Exception:
                pass
        return ahora

    for cat, items in stats_in.items():
        if cat not in stats:
            stats[cat] = {}
        for nombre, amb in items.items():
            amb_out: Dict[str, Any] = {}
            for k in ("p", "s"):
                v = amb.get(k, {})
                amb_out[k] = {
                    "t": v.get("t", 0),
                    "d30": v.get("d30", 0),
                    "d90": v.get("d90", 0),
                    "primera": _parse_fecha(v.get("primera")),
                    "ultima": _parse_fecha(v.get("ultima")),
                    "ses": set(v.get("ses", [])),
                }
            stats[cat][nombre] = amb_out

    return stats, metricas, contador
