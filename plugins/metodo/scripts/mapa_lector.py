#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
inventario.py - Inventario mecánico, determinista y seguro del ecosistema de Claude Code (~/.claude)
                junto con la medición de uso real a partir de conversaciones (.jsonl).

Uso:
    python3 inventario.py --out <carpeta_destino> [--solo-disco] [--claude-dir <ruta_a_.claude>]

Compatibilidad: Python 3.9+ estándar, sin librerías externas.
"""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys
from typing import Any, Dict, List, Optional, Set, Tuple


# ==============================================================================
# 0. REGLAS DE SEGURIDAD Y FILTRADO
# ==============================================================================
# NUNCA copiar al resultado variables de entorno, claves, tokens, argumentos de línea
# de comandos de servidores MCP ni ningún texto de las conversaciones.
# Solo números, fechas, nombres y metadatos públicos de estructura.

def limpiar_texto_linea(texto: str) -> str:
    """Elimina saltos de línea y caracteres de control para tablas Markdown."""
    if not texto:
        return ""
    return texto.replace("\r", " ").replace("\n", " ").replace("|", "\\|").strip()


def formatear_fecha(iso_str: Optional[str]) -> str:
    """Formatea una fecha ISO a formato legible YYYY-MM-DD HH:MM o guion si no existe."""
    if not iso_str:
        return "-"
    try:
        # Simplificar fecha ISO para tablas
        return iso_str[:16].replace("T", " ")
    except Exception:
        return str(iso_str)


# ==============================================================================
# 1. PARSER TOLERANTE DE YAML FRONTMATTER (Hecho a mano, sin PyYAML)
# ==============================================================================

def parse_yaml_frontmatter(contenido: str) -> Dict[str, Any]:
    """
    Parsea de forma manual y tolerante el bloque frontmatter YAML entre '---'.
    Soporta comillas, listas YAML y descripciones multilínea.
    """
    resultado: Dict[str, Any] = {}
    if not contenido:
        return resultado

    lineas = contenido.splitlines()
    start_idx = -1
    for i, line in enumerate(lineas):
        if line.strip() == "---":
            start_idx = i
            break

    if start_idx == -1:
        return resultado

    end_idx = -1
    for i in range(start_idx + 1, len(lineas)):
        if lineas[i].strip() == "---":
            end_idx = i
            break

    if end_idx == -1:
        return resultado

    bloque = lineas[start_idx + 1:end_idx]

    def limpiar_valor(v: str) -> str:
        s = v.strip()
        if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
            s = s[1:-1]
        return s.strip()

    clave_actual: Optional[str] = None
    buffer_multilinea: List[str] = []
    en_bloque = False  # dentro de un bloque `>` o `|`: las líneas "- x" son texto, no lista

    def consolidar_clave():
        nonlocal clave_actual, buffer_multilinea
        if clave_actual:
            if buffer_multilinea:
                unido = " ".join([l.strip() for l in buffer_multilinea if l.strip()])
                resultado[clave_actual] = limpiar_valor(unido)
        clave_actual = None
        buffer_multilinea = []

    for linea in bloque:
        stripped = linea.strip()
        if not stripped or stripped.startswith("#"):
            continue

        # Detección de nueva clave "clave:"
        if not linea.startswith(" ") and not linea.startswith("\t") and ":" in linea and not stripped.startswith("-"):
            consolidar_clave()
            en_bloque = False
            partes = linea.split(":", 1)
            k = partes[0].strip()
            v = partes[1].strip() if len(partes) > 1 else ""

            # Indicadores multilínea de YAML
            if v in (">", "|", ">-", "|-"):
                clave_actual = k
                buffer_multilinea = []
                en_bloque = True
            elif v:
                if (v.startswith('"') and not v.endswith('"')) or (v.startswith("'") and not v.endswith("'")):
                    clave_actual = k
                    buffer_multilinea = [v]
                else:
                    # Chequear si es una lista en línea tipo [a, b]
                    if v.startswith("[") and v.endswith("]"):
                        elementos = [limpiar_valor(x) for x in v[1:-1].split(",") if limpiar_valor(x)]
                        resultado[k] = elementos
                    else:
                        resultado[k] = limpiar_valor(v)
            else:
                clave_actual = k
                buffer_multilinea = []
        else:
            # Línea de continuación o elemento de lista
            if clave_actual:
                if stripped.startswith("- ") and not en_bloque:
                    item = limpiar_valor(stripped[2:])
                    if clave_actual not in resultado or not isinstance(resultado[clave_actual], list):
                        resultado[clave_actual] = []
                    resultado[clave_actual].append(item)
                else:
                    buffer_multilinea.append(stripped)

    consolidar_clave()

    # Recortar description a 300 caracteres
    if "description" in resultado and isinstance(resultado["description"], str):
        resultado["description"] = resultado["description"][:300]

    return resultado


# ==============================================================================
# 2. INVENTARIO MECÁNICO DESDE EL DISCO
# ==============================================================================

SALTAR_DIRS = {"node_modules", ".git", "__pycache__", ".venv", "venv"}
# Agentes que trae Claude Code de fábrica: no están en disco, pero se usan.
AGENTES_DE_FABRICA = {
    "general-purpose", "Explore", "Plan", "statusline-setup", "claude-code-guide",
    "claude", "output-style-setup",
}


def con_tilde(ruta: Any) -> str:
    """Muestra una ruta con `~` en vez de la carpeta personal (el inventario no lleva el nombre de usuario)."""
    return str(ruta).replace(str(Path.home()), "~") if ruta else ""


def cargar_patron_clientes(claude_dir: Path) -> Optional["re.Pattern[str]"]:
    """
    Patrón con los nombres de clientes/personas que NO deben salir del equipo (~/.claude/nombres-prohibidos.txt,
    una por línea, `#` = comentario). Si el archivo no existe, no se depura nada.
    """
    archivo = claude_dir / "nombres-prohibidos.txt"
    try:
        nombres = [l.strip() for l in archivo.read_text(encoding="utf-8", errors="replace").splitlines()
                   if l.strip() and not l.strip().startswith("#")]
    except Exception:
        return None
    if not nombres:
        return None
    return re.compile(r"\b(?:" + "|".join(re.escape(n) for n in sorted(nombres, key=len, reverse=True)) + r")\b", re.IGNORECASE)


def depurar_clientes(obj: Any, patron: Optional["re.Pattern[str]"], contador: List[int]) -> Any:
    """Recorre el inventario y reemplaza por `<cliente>` cualquier nombre de la lista de prohibidos."""
    if patron is None:
        return obj
    if isinstance(obj, str):
        nuevo, n = patron.subn("<cliente>", obj)
        contador[0] += n
        return nuevo
    if isinstance(obj, list):
        return [depurar_clientes(x, patron, contador) for x in obj]
    if isinstance(obj, dict):
        return {depurar_clientes(k, patron, contador) if isinstance(k, str) else k: depurar_clientes(v, patron, contador) for k, v in obj.items()}
    return obj


def leer_json(ruta: Path) -> Any:
    """Lee un JSON de forma tolerante; devuelve None si no se puede."""
    try:
        with open(ruta, "r", encoding="utf-8", errors="replace") as f:
            return json.load(f)
    except Exception:
        return None


def lista_str(v: Any) -> List[str]:
    """Convierte None / texto / lista en lista de textos."""
    if v is None:
        return []
    if isinstance(v, str):
        return [v]
    if isinstance(v, list):
        return [str(x) for x in v if isinstance(x, (str, int, float))]
    return []


def parse_tools(v: Any) -> List[str]:
    """`tools:` puede ser una lista YAML o un texto separado por comas."""
    if isinstance(v, list):
        return [str(x).strip() for x in v if str(x).strip()]
    if isinstance(v, str):
        return [x.strip() for x in v.split(",") if x.strip()]
    return []


def fecha_de(ruta: Path) -> str:
    try:
        return datetime.fromtimestamp(ruta.stat().st_mtime, tz=timezone.utc).isoformat()
    except Exception:
        return ""


def ficha_md(ruta: Path, nombre_defecto: str) -> Dict[str, Any]:
    """
    Lee el frontmatter de un SKILL.md / agente .md. Devuelve solo metadatos:
    nombre, descripción (recortada a 300), bytes de la descripción completa, tamaño,
    modelo, herramientas y skills que el agente precarga.
    """
    ficha: Dict[str, Any] = {
        "nombre": nombre_defecto, "descripcion": "", "descripcion_bytes": 0,
        "tamano_bytes": 0, "fecha_modificacion": "", "modelo": "",
        "herramientas": [], "skills_precargadas": [], "frontmatter_ok": False,
    }
    try:
        ficha["tamano_bytes"] = ruta.stat().st_size
        ficha["fecha_modificacion"] = fecha_de(ruta)
        with open(ruta, "r", encoding="utf-8", errors="replace") as f:
            contenido = f.read()
        fm = parse_yaml_frontmatter(contenido)
        # parse_yaml_frontmatter recorta a 300; para el peso real se mide aparte
        desc_completa = _descripcion_completa(contenido)
        ficha["frontmatter_ok"] = bool(fm)
        ficha["nombre"] = str(fm.get("name") or nombre_defecto)
        ficha["descripcion"] = str(fm.get("description") or "")[:300]
        ficha["descripcion_bytes"] = len((desc_completa or str(fm.get("description") or "")).encode("utf-8"))
        ficha["modelo"] = str(fm.get("model") or "")
        ficha["herramientas"] = parse_tools(fm.get("tools"))
        ficha["skills_precargadas"] = parse_tools(fm.get("skills"))
    except Exception:
        pass
    return ficha


def _descripcion_completa(contenido: str) -> str:
    """Devuelve la descripción SIN recortar (solo para medir su peso en bytes)."""
    lineas = contenido.splitlines()
    try:
        ini = next(i for i, l in enumerate(lineas) if l.strip() == "---")
        fin = next(i for i in range(ini + 1, len(lineas)) if lineas[i].strip() == "---")
    except StopIteration:
        return ""
    partes: List[str] = []
    en_desc = False
    for l in lineas[ini + 1:fin]:
        if not en_desc:
            if l.startswith("description:"):
                en_desc = True
                resto = l.split(":", 1)[1].strip()
                if resto not in (">", "|", ">-", "|-"):
                    partes.append(resto)
            continue
        if l.startswith((" ", "\t")) or not l.strip():
            partes.append(l.strip())
        else:
            break
    texto = " ".join(p for p in partes if p).strip()
    if len(texto) >= 2 and texto[0] == texto[-1] and texto[0] in "\"'":
        texto = texto[1:-1]
    return texto


def skills_en_dir(base: Path) -> List[Path]:
    """Carpetas hijas directas de `base` que tienen SKILL.md (sigue symlinks)."""
    salida: List[Path] = []
    if not base.is_dir():
        return salida
    try:
        hijos = sorted(base.iterdir(), key=lambda p: p.name)
    except Exception:
        return salida
    for h in hijos:
        if h.name.startswith(".") or h.name in SALTAR_DIRS:
            continue
        if h.is_dir() and (h / "SKILL.md").is_file():
            salida.append(h)
    return salida


def contar_archivos(carpeta: Path) -> int:
    try:
        return sum(1 for p in carpeta.rglob("*") if p.is_file() and not p.name.startswith("."))
    except Exception:
        return 0


def campos_uso_vacios() -> Dict[str, Any]:
    return {
        "usos_total": 0, "usos_30d": 0, "usos_90d": 0,
        "usos_principal": 0, "usos_subagentes": 0, "usos_slash": 0,
        "usos_principal_30d": 0, "usos_principal_90d": 0, "usos_subagentes_30d": 0, "usos_subagentes_90d": 0,
        "precargas_en_subagentes": 0,
        "primera_vez": None, "ultima_vez": None,
        "cantidad_sesiones": 0, "nunca_usado": True,
    }


def inventariar_skills_personales(claude_dir: Path) -> List[Dict[str, Any]]:
    """Inventaria ~/.claude/skills/*/SKILL.md (activas personales; _archivo y synced van aparte)."""
    skills_dir = claude_dir / "skills"
    items: List[Dict[str, Any]] = []
    for carpeta in skills_en_dir(skills_dir):
        if carpeta.name in ("_archivo", "synced"):
            continue
        f = ficha_md(carpeta / "SKILL.md", carpeta.name)
        item = {
            "nombre": f["nombre"],
            "carpeta": carpeta.name,
            "es_symlink": carpeta.is_symlink(),
            "descripcion": f["descripcion"],
            "descripcion_bytes": f["descripcion_bytes"],
            "tamano_bytes": f["tamano_bytes"],
            "fecha_modificacion": f["fecha_modificacion"],
            "tiene_nota_local": (carpeta / "NOTA-LOCAL.md").exists(),
            "cantidad_archivos": contar_archivos(carpeta),
            "precargada_por": [],
        }
        item.update(campos_uso_vacios())
        items.append(item)
    return items


def inventariar_skills_sincronizadas(claude_dir: Path) -> List[Dict[str, Any]]:
    """
    ~/.claude/skills/synced/<cuenta>/*/SKILL.md: skills que claude.ai/Cowork sincroniza
    (se invocan como `anthropic-skills:<nombre>`).
    """
    items: List[Dict[str, Any]] = []
    base = claude_dir / "skills" / "synced"
    if not base.is_dir():
        return items
    for cuenta in sorted(base.iterdir(), key=lambda p: p.name):
        if cuenta.name.startswith(".") or not cuenta.is_dir():
            continue
        for carpeta in skills_en_dir(cuenta):
            f = ficha_md(carpeta / "SKILL.md", carpeta.name)
            item = {
                "plugin": "anthropic-skills",
                "fuente": "skills/synced",
                "cargado": True,
                "nombre": f["nombre"],
                "invocacion": f"anthropic-skills:{f['nombre']}",
                "descripcion": f["descripcion"],
                "descripcion_bytes": f["descripcion_bytes"],
                "tamano_bytes": f["tamano_bytes"],
                "cantidad_archivos": contar_archivos(carpeta),
                "precargada_por": [],
            }
            item.update(campos_uso_vacios())
            items.append(item)
    return items


def inventariar_archivo(claude_dir: Path) -> Dict[str, Any]:
    """Lo archivado (no se carga): solo conteos y nombres."""
    res: Dict[str, Any] = {}
    sk = claude_dir / "skills-archive"
    res["skills_archive"] = sorted(p.name for p in skills_en_dir(sk))
    ag = claude_dir / "agents-archive"
    res["agents_archive"] = sorted(p.stem for p in ag.glob("*.md")) if ag.is_dir() else []
    arch = claude_dir / "skills" / "_archivo"
    internas: List[str] = []
    if arch.is_dir():
        for grupo in sorted(arch.iterdir(), key=lambda p: p.name):
            if grupo.is_dir() and not grupo.name.startswith("."):
                for s in skills_en_dir(grupo):
                    internas.append(f"{grupo.name}/{s.name}")
    res["skills__archivo"] = internas
    return res


def inventariar_agentes(claude_dir: Path) -> List[Dict[str, Any]]:
    """Inventaria ~/.claude/agents/*.md (agentes personales)."""
    agents_dir = claude_dir / "agents"
    items: List[Dict[str, Any]] = []
    if not agents_dir.is_dir():
        return items
    for agente_file in sorted(agents_dir.glob("*.md"), key=lambda p: p.name):
        if not agente_file.is_file() or agente_file.name.startswith("."):
            continue
        f = ficha_md(agente_file, agente_file.stem)
        item = {
            "nombre": f["nombre"],
            "archivo": agente_file.name,
            "descripcion": f["descripcion"],
            "descripcion_bytes": f["descripcion_bytes"],
            "modelo": f["modelo"],
            "herramientas": f["herramientas"],
            "skills_precargadas": f["skills_precargadas"],
            "es_pm": f["nombre"].startswith("pm-") or agente_file.stem.startswith("pm-"),
            "tamano_bytes": f["tamano_bytes"],
            "fecha_modificacion": f["fecha_modificacion"],
        }
        item.update(campos_uso_vacios())
        items.append(item)
    return items


# ------------------------------------------------------------------------------
# Hooks (settings.json, plugins, mods)
# ------------------------------------------------------------------------------

def extraer_basename_script(cmd_str: str) -> str:
    """
    Extrae únicamente el nombre de archivo (basename) del script en una orden de hook.
    REGLA DE SEGURIDAD: nunca devuelve argumentos ni la orden completa.
    """
    if not cmd_str or not isinstance(cmd_str, str):
        return ""
    tokens = [t.strip("\"'") for t in cmd_str.strip().split()]
    if not tokens:
        return ""
    script_exts = (".sh", ".py", ".bash", ".zsh", ".js", ".mjs", ".cjs", ".ts", ".rb", ".pl", ".php")
    for t in tokens:
        if "=" in t and not t.startswith("-") and "/" not in t.split("=", 1)[0]:
            continue
        if any(t.lower().endswith(ext) for ext in script_exts):
            return Path(t).name
    for t in tokens:
        if ("/" in t) and not t.startswith("-") and not Path(t).name.lower().startswith(("python", "node", "bash", "sh")):
            return Path(t).name
    return Path(tokens[0]).name


def hooks_desde_cfg(cfg: Any, origen: str) -> List[Dict[str, Any]]:
    """
    Aplana un bloque `hooks` (el de settings.json o el de un hooks.json de plugin):
        {evento: [ {matcher, hooks: [ {type, command, ...}, ... ]}, ... ]}
    Solo guarda evento, matcher, tipo y el nombre del script (nunca la orden entera).
    """
    items: List[Dict[str, Any]] = []
    if not isinstance(cfg, dict):
        return items
    if isinstance(cfg.get("hooks"), dict):  # hooks.json de plugin: {"description", "hooks": {...}, "modules": [...]}
        cfg = cfg["hooks"]
    for evento, reglas in cfg.items():
        if not isinstance(reglas, list):
            continue
        for regla in reglas:
            if not isinstance(regla, dict):
                continue
            matcher = str(regla.get("matcher") or "*")
            internos = regla.get("hooks")
            if not isinstance(internos, list):
                internos = [regla]  # formato plano antiguo
            for h in internos:
                if not isinstance(h, dict):
                    continue
                tipo = str(h.get("type") or "command")
                cmd = str(h.get("command") or h.get("script") or "")
                items.append({
                    "evento": str(evento),
                    "matcher": matcher,
                    "tipo": tipo,
                    "script": extraer_basename_script(cmd) if cmd else "",
                    "async": bool(h.get("async")),
                    "origen": origen,
                })
    return items


def modulos_desde_cfg(cfg: Any) -> List[str]:
    """`modules` de un hooks.json: módulos de interfaz (paneles, avisos) que cargan los mods/plugins. Solo basename."""
    if isinstance(cfg, dict) and isinstance(cfg.get("modules"), list):
        return sorted(Path(str(m)).name for m in cfg["modules"] if isinstance(m, str))
    return []


def inventariar_hooks(claude_dir: Path) -> List[Dict[str, Any]]:
    """settings.json -> hooks (anidados: evento -> reglas -> hooks)."""
    data = leer_json(claude_dir / "settings.json")
    if not isinstance(data, dict):
        return []
    return hooks_desde_cfg(data.get("hooks"), "settings.json")


def inventariar_hooks_dir(claude_dir: Path, hooks_settings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Archivos de ~/.claude/hooks y si están registrados en settings.json."""
    base = claude_dir / "hooks"
    registrados = {h["script"] for h in hooks_settings if h.get("script")}
    items: List[Dict[str, Any]] = []
    if not base.is_dir():
        return items
    for p in sorted(base.iterdir(), key=lambda x: x.name):
        if p.name.startswith(".") or p.name in SALTAR_DIRS or not p.is_file():
            continue
        items.append({
            "nombre": p.name,
            "tamano_bytes": p.stat().st_size,
            "registrado_en_settings": p.name in registrados,
        })
    return items


def inventariar_mods(claude_dir: Path) -> List[Dict[str, Any]]:
    """~/.claude/mods/*: agregados propios a la pantalla (con sus hooks)."""
    base = claude_dir / "mods"
    items: List[Dict[str, Any]] = []
    if not base.is_dir():
        return items
    for mod in sorted(base.iterdir(), key=lambda p: p.name):
        if mod.name.startswith(".") or not mod.is_dir():
            continue
        pj = leer_json(mod / "plugin.json") or leer_json(mod / ".claude-plugin" / "plugin.json") or {}
        hk = leer_json(mod / "hooks" / "hooks.json")
        hooks = hooks_desde_cfg(hk, f"mod:{mod.name}") if hk else []
        modulos = modulos_desde_cfg(hk)
        items.append({
            "nombre": mod.name,
            "version": str(pj.get("version") or "") if isinstance(pj, dict) else "",
            "descripcion": str(pj.get("description") or "")[:300] if isinstance(pj, dict) else "",
            "hooks": len(hooks),
            "modulos": modulos,
            "cantidad_archivos": contar_archivos(mod),
        })
    return items


def inventariar_tareas_programadas(claude_dir: Path) -> List[Dict[str, Any]]:
    """~/.claude/scheduled-tasks/*/SKILL.md."""
    items: List[Dict[str, Any]] = []
    base = claude_dir / "scheduled-tasks"
    for carpeta in skills_en_dir(base):
        f = ficha_md(carpeta / "SKILL.md", carpeta.name)
        items.append({"nombre": f["nombre"], "carpeta": carpeta.name, "descripcion": f["descripcion"]})
    return items


def inventariar_recetas_y_otros(claude_dir: Path) -> Dict[str, Any]:
    """Recetas, templates y servidores MCP propios de ~/.claude (solo nombres)."""
    def nombres(base: Path, patron: str = "*") -> List[str]:
        if not base.is_dir():
            return []
        return sorted(p.name for p in base.glob(patron) if not p.name.startswith("."))
    return {
        "recetas": nombres(claude_dir / "recetas", "*.md"),
        "templates": nombres(claude_dir / "templates"),
        "mcp_servers_propios": nombres(claude_dir / "mcp-servers"),
        "commands_globales": nombres(claude_dir / "commands", "*.md"),
        "rules_globales": nombres(claude_dir / "rules", "*.md"),
        "output_styles": nombres(claude_dir / "output-styles"),
    }


def inventariar_scripts(claude_dir: Path) -> List[Dict[str, Any]]:
    """
    Inventaria ~/.claude/scripts/*: archivos (tipo 'archivo') y carpetas (tipo 'carpeta').
    Para archivos: primera línea de comentario (# ...).
    Para carpetas: cantidad de archivos dentro y primera línea del README si existe.
    """
    scripts_dir = claude_dir / "scripts"
    items: List[Dict[str, Any]] = []
    if not scripts_dir.is_dir():
        return items

    for f_path in sorted(scripts_dir.iterdir(), key=lambda p: p.name):
        if f_path.name.startswith(".") or f_path.name in SALTAR_DIRS:
            continue

        if f_path.is_file():
            primer_comentario = ""
            try:
                stat = f_path.stat()
                tamano = stat.st_size
                mtime = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
                with open(f_path, "r", encoding="utf-8", errors="replace") as sf:
                    for linea in sf:
                        linea_strip = linea.strip()
                        if linea_strip.startswith("#"):
                            if linea_strip.startswith("#!"):
                                continue
                            primer_comentario = linea_strip.lstrip("#").strip()[:300]
                            break
            except Exception:
                tamano = 0
                mtime = ""

            items.append({
                "nombre": f_path.name,
                "tipo": "archivo",
                "comentario": primer_comentario,
                "tamano_bytes": tamano,
                "fecha_modificacion": mtime,
                "cantidad_archivos": 1
            })

        elif f_path.is_dir():
            primer_comentario = ""
            tamano = 0
            mtime = fecha_de(f_path)
            cantidad_archivos = contar_archivos(f_path)

            readme_file = None
            for cand in ("README.md", "README", "readme.md", "Readme.md", "readme.txt", "README.txt"):
                cand_path = f_path / cand
                if cand_path.is_file():
                    readme_file = cand_path
                    break
            if readme_file:
                try:
                    with open(readme_file, "r", encoding="utf-8", errors="replace") as rf:
                        for linea in rf:
                            linea_strip = linea.strip()
                            if linea_strip:
                                primer_comentario = linea_strip.lstrip("#").strip()[:300]
                                break
                except Exception:
                    pass

            items.append({
                "nombre": f_path.name,
                "tipo": "carpeta",
                "comentario": primer_comentario,
                "readme_primera_linea": primer_comentario,
                "cantidad_archivos": cantidad_archivos,
                "tamano_bytes": tamano,
                "fecha_modificacion": mtime
            })

    return items


def inventariar_permisos(claude_dir: Path) -> Dict[str, int]:
    """
    settings.json clave 'permissions': cuenta cantidad de reglas allow/deny/ask.
    REGLA DE SEGURIDAD: nunca guarda las reglas específicas.
    """
    conteo = {"allow": 0, "deny": 0, "ask": 0, "total": 0}
    data = leer_json(claude_dir / "settings.json")
    perms = data.get("permissions") if isinstance(data, dict) else None
    if isinstance(perms, dict):
        for k in ("allow", "deny", "ask"):
            val = perms.get(k)
            if isinstance(val, (list, dict)):
                conteo[k] += len(val)
    conteo["total"] = conteo["allow"] + conteo["deny"] + conteo["ask"]
    return conteo


def _claves_dict(d: Any) -> List[str]:
    return [str(k) for k in d.keys()] if isinstance(d, dict) else []


def inventariar_ajustes(claude_dir: Path) -> Dict[str, Any]:
    """
    Otras claves de settings.json / settings.local.json. SOLO nombres de claves y conteos:
    nunca valores (el bloque env puede traer rutas o claves).
    """
    s = leer_json(claude_dir / "settings.json") or {}
    sl = leer_json(claude_dir / "settings.local.json") or {}
    sl_perms = sl.get("permissions") if isinstance(sl, dict) else None
    return {
        "claves_settings": sorted(s.keys()) if isinstance(s, dict) else [],
        "env_claves": sorted((s.get("env") or {}).keys()) if isinstance(s.get("env"), dict) else [],
        "tiene_statusline": bool(isinstance(s, dict) and s.get("statusLine")),
        "statusline_script": extraer_basename_script(str((s.get("statusLine") or {}).get("command") or "")) if isinstance(s.get("statusLine"), dict) else "",
        "settings_local_claves": sorted(sl.keys()) if isinstance(sl, dict) else [],
        "settings_local_permisos": len(sl_perms) if isinstance(sl_perms, (list, dict)) else 0,
        "mcp_habilitados_settings_local": sorted(lista_str(sl.get("enabledMcpjsonServers"))) if isinstance(sl, dict) else [],
        "mcp_necesitan_autenticacion": sorted(_claves_dict(leer_json(claude_dir / "mcp-needs-auth-cache.json"))),
    }


# ------------------------------------------------------------------------------
# Proyectos (~/Proyectos/**/.claude), CLAUDE.md, memoria
# ------------------------------------------------------------------------------

def _huella_nombres(pares: List[Tuple[str, int]]) -> str:
    import hashlib
    h = hashlib.sha1()
    for n, t in sorted(pares):
        h.update(f"{n}:{t};".encode("utf-8"))
    return h.hexdigest()[:12]


def inventariar_proyectos(raiz: Path, skills_personales: Optional[Set[str]] = None) -> List[Dict[str, Any]]:
    """
    Recorre ~/Proyectos buscando carpetas `.claude` (hasta 4 niveles, sin node_modules/.git
    ni carpetas llamadas `clientes`) y anota qué componentes propios de proyecto hay:
    skills, agentes, reglas, comandos, hooks. Solo nombres y conteos.
    """
    items: List[Dict[str, Any]] = []
    if not raiz.is_dir():
        return items
    prof_raiz = len(raiz.parts)
    for actual, dirs, _files in os.walk(raiz):
        rel_parts = Path(actual).parts[prof_raiz:]
        dirs[:] = sorted(d for d in dirs if d not in SALTAR_DIRS and d != "clientes")
        if len(rel_parts) >= 4:
            dirs[:] = []
        if Path(actual).name != ".claude":
            continue
        dirs[:] = []  # no seguir dentro de .claude
        cdir = Path(actual)
        proyecto = cdir.parent
        rel = str(proyecto.relative_to(raiz)) if proyecto != raiz else "."
        skills = [p.name for p in skills_en_dir(cdir / "skills")]
        agentes = sorted(p.stem for p in (cdir / "agents").glob("*.md")) if (cdir / "agents").is_dir() else []
        reglas = sorted(p.name for p in (cdir / "rules").glob("*.md")) if (cdir / "rules").is_dir() else []
        comandos = sorted(p.stem for p in (cdir / "commands").glob("*.md")) if (cdir / "commands").is_dir() else []
        hooks: List[Dict[str, Any]] = []
        for nom in ("settings.json", "settings.local.json"):
            d = leer_json(cdir / nom)
            if isinstance(d, dict) and d.get("hooks"):
                hooks += hooks_desde_cfg(d.get("hooks"), f"{rel}/.claude/{nom}")
        pares: List[Tuple[str, int]] = []
        for s in skills:
            try:
                pares.append((f"s:{s}", (cdir / "skills" / s / "SKILL.md").stat().st_size))
            except Exception:
                pares.append((f"s:{s}", 0))
        for a in agentes:
            pares.append((f"a:{a}", (cdir / "agents" / f"{a}.md").stat().st_size))
        for r in reglas:
            pares.append((f"r:{r}", (cdir / "rules" / r).stat().st_size))
        hooks_dir = cdir / "hooks"
        n_hooks_archivos = sum(1 for p in hooks_dir.iterdir() if p.is_file() and not p.name.startswith(".")) if hooks_dir.is_dir() else 0
        en_comun = len(set(skills) & (skills_personales or set()))
        claude_md = proyecto / "CLAUDE.md"
        info_md = {}
        if claude_md.is_file():
            try:
                txt = claude_md.read_text(encoding="utf-8", errors="replace")
                info_md = {"bytes": claude_md.stat().st_size, "lineas": txt.count("\n") + 1}
            except Exception:
                pass
        items.append({
            "ruta": rel,
            "es_checkout_git": (proyecto / ".git").exists(),
            "skills": skills,
            "agentes": agentes,
            "reglas": reglas,
            "comandos": comandos,
            "hooks": len(hooks),
            "hooks_eventos": sorted({h["evento"] for h in hooks}),
            "hooks_archivos": n_hooks_archivos,
            "skills_en_comun_con_personales": en_comun,
            "parece_copia_del_ecosistema": bool(skills) and len(skills) >= 20 and en_comun >= 0.5 * len(skills),
            "tiene_settings": (cdir / "settings.json").is_file(),
            "tiene_settings_local": (cdir / "settings.local.json").is_file(),
            "tiene_mcp_json": (proyecto / ".mcp.json").is_file(),
            "claude_md": info_md,
            "huella": _huella_nombres(pares) if pares else "",
        })
    return items


def inventariar_claude_md(claude_dir: Path) -> Dict[str, Any]:
    """Tamaño (bytes y líneas) del CLAUDE.md global y sus importados."""
    res: Dict[str, Any] = {}
    for nombre in ("CLAUDE.md", "CLAUDE-omc.md"):
        p = claude_dir / nombre
        if p.is_file():
            try:
                txt = p.read_text(encoding="utf-8", errors="replace")
                res[nombre] = {"bytes": p.stat().st_size, "lineas": txt.count("\n") + 1}
            except Exception:
                pass
    return res


def inventariar_memoria(claude_dir: Path) -> Dict[str, Any]:
    """
    Memoria automática por proyecto: ~/.claude/projects/<proyecto>/memory/*.md.
    SOLO conteos (la memoria es privada y no viaja a la nube). Las carpetas temporales
    (/private/tmp, scratch de pruebas) se cuentan aparte.
    """
    base = claude_dir / "projects"
    por_proyecto: Dict[str, int] = {}
    efimeros = 0
    if base.is_dir():
        for proy in sorted(base.iterdir(), key=lambda p: p.name):
            mem = proy / "memory"
            if not mem.is_dir():
                continue
            n = sum(1 for f in mem.glob("*.md") if f.name != "MEMORY.md")
            if n == 0:
                continue
            es_tmp = proy.name.startswith(("-private-", "-tmp-")) or "scratch" in proy.name
            if es_tmp:
                efimeros += n
            else:
                por_proyecto[proy.name] = n
    return {
        "entradas_por_proyecto": por_proyecto,
        "total_entradas": sum(por_proyecto.values()),
        "entradas_en_carpetas_efimeras": efimeros,
    }


def leer_contador_interno_skills() -> Dict[str, Dict[str, Any]]:
    """
    `skillUsage` de ~/.claude.json: el contador propio de Claude Code (cuenta tanto /slash como la herramienta Skill).
    SOLO nombre, cantidad y fecha: no se toca nada más de ese archivo.
    """
    d = leer_json(Path.home() / ".claude.json")
    su = d.get("skillUsage") if isinstance(d, dict) else None
    out: Dict[str, Dict[str, Any]] = {}
    if isinstance(su, dict):
        for k, v in su.items():
            if isinstance(v, dict) and isinstance(v.get("usageCount"), int):
                ts = v.get("lastUsedAt")
                fecha = datetime.fromtimestamp(ts / 1000.0, tz=timezone.utc).isoformat() if isinstance(ts, (int, float)) else None
                out[str(k)] = {"usageCount": v["usageCount"], "ultima_vez": fecha}
    return out


def inventariar_rutinas() -> Dict[str, Any]:
    """Rutinas registradas en ~/.cerebro/rutinas-fuentes.json: solo conteos de claves."""
    d = leer_json(Path.home() / ".cerebro" / "rutinas-fuentes.json")
    if not isinstance(d, dict):
        return {}
    return {k: (len(v) if isinstance(v, (list, dict)) else None) for k, v in d.items() if isinstance(v, (list, dict))}


# ------------------------------------------------------------------------------
# Plugins: instalados (installed_plugins.json) + sincronizados (plugins/synced)
# ------------------------------------------------------------------------------

def nombres_mcp(data: Any) -> List[str]:
    """Nombres de servidores en un .mcp.json ({"mcpServers": {...}} o plano). NUNCA env/args/urls."""
    if not isinstance(data, dict):
        return []
    srv = data.get("mcpServers") if isinstance(data.get("mcpServers"), dict) else data
    return sorted(str(k) for k, v in srv.items() if isinstance(v, dict))


def _rutas_declaradas(ruta: Path, decl: Any) -> List[Path]:
    """Convierte una declaración de plugin.json (texto o lista) en rutas dentro del plugin."""
    salida: List[Path] = []
    for e in lista_str(decl):
        p = (ruta / e).resolve()
        try:
            p.relative_to(ruta.resolve())
        except ValueError:
            continue
        salida.append(p)
    return salida


def componentes_de_plugin(ruta: Path, nombre_plugin: str, cargado: bool, fuente: str) -> Dict[str, Any]:
    """
    Lee los componentes REALES de un plugin tal como Claude Code los carga:
      - skills:   plugin.json "skills" (lista de carpetas o carpeta) o, por defecto, skills/*/SKILL.md
      - agentes:  plugin.json "agents" (lista de .md) o, por defecto, agents/*.md.
                  Los .md sueltos en la raíz que NO están declarados se anotan aparte.
      - comandos: plugin.json "commands" o, por defecto, commands/*.md
      - hooks:    plugin.json "hooks" (inline o ruta) o hooks/hooks.json
      - mcp:      .mcp.json o plugin.json "mcpServers"
    """
    pj = leer_json(ruta / ".claude-plugin" / "plugin.json")
    if not isinstance(pj, dict):
        pj = leer_json(ruta / "plugin.json")
    if not isinstance(pj, dict):
        pj = {}
    # Claude Code nombra los componentes con el `name` de plugin.json (no con la clave de instalación)
    nombre_plugin = str(pj.get("name") or nombre_plugin)

    # ---- skills ----
    skills: List[Dict[str, Any]] = []
    carpetas_skill: List[Path] = []
    if "skills" in pj and pj["skills"]:
        for p in _rutas_declaradas(ruta, pj["skills"]):
            if (p / "SKILL.md").is_file():
                carpetas_skill.append(p)
            else:
                carpetas_skill.extend(skills_en_dir(p))
    else:
        carpetas_skill = skills_en_dir(ruta / "skills")
    vistos: Set[str] = set()
    for c in carpetas_skill:
        if str(c) in vistos:
            continue
        vistos.add(str(c))
        f = ficha_md(c / "SKILL.md", c.name)
        item = {
            "plugin": nombre_plugin, "fuente": fuente, "cargado": cargado,
            "nombre": f["nombre"], "invocacion": f"{nombre_plugin}:{f['nombre']}",
            "descripcion": f["descripcion"], "descripcion_bytes": f["descripcion_bytes"],
            "tamano_bytes": f["tamano_bytes"], "cantidad_archivos": contar_archivos(c),
            "precargada_por": [],
        }
        item.update(campos_uso_vacios())
        skills.append(item)
    # SKILL.md que existen en el plugin pero que Claude Code no carga (anidados)
    skills_en_disco = 0
    try:
        for r, ds, fs in os.walk(ruta):
            ds[:] = [d for d in ds if d not in SALTAR_DIRS and not d.startswith(".")]
            if "SKILL.md" in fs:
                skills_en_disco += 1
    except Exception:
        pass

    # ---- agentes ----
    archivos_agente: List[Path] = []
    declarados = False
    if "agents" in pj and pj["agents"]:
        declarados = True
        for p in _rutas_declaradas(ruta, pj["agents"]):
            if p.is_file():
                archivos_agente.append(p)
            elif p.is_dir():
                archivos_agente.extend(sorted(p.glob("*.md")))
    else:
        d = ruta / "agents"
        if d.is_dir():
            archivos_agente = sorted(x for x in d.glob("*.md") if not x.name.startswith("."))
    agentes: List[Dict[str, Any]] = []
    for a in archivos_agente:
        f = ficha_md(a, a.stem)
        item = {
            "plugin": nombre_plugin, "fuente": fuente, "cargado": cargado,
            "nombre": f["nombre"], "archivo": a.name, "invocacion": f"{nombre_plugin}:{f['nombre']}",
            "descripcion": f["descripcion"], "descripcion_bytes": f["descripcion_bytes"],
            "modelo": f["modelo"], "herramientas": f["herramientas"],
            "skills_precargadas": f["skills_precargadas"],
            "tamano_bytes": f["tamano_bytes"], "declarado": True,
        }
        item.update(campos_uso_vacios())
        agentes.append(item)
    usados = {a.resolve() for a in archivos_agente}
    sueltos_no_declarados: List[str] = []
    for md in sorted(ruta.glob("*.md")):
        if md.name.upper() in ("README.MD", "CHANGELOG.MD", "CLAUDE.MD", "AGENTS.MD", "LICENSE.MD", "CONTRIBUTING.MD",
                               "CONNECTORS.MD", "ACCESS.MD", "CONTEXT.MD", "REQUISITOS.MD", "PLUGIN_SETTINGS.MD",
                               "SECURITY.MD", "THIRDPARTYNOTICES.MD") or md.name.startswith("README"):
            continue
        if md.resolve() in usados:
            continue
        try:
            if parse_yaml_frontmatter(md.read_text(encoding="utf-8", errors="replace")).get("name"):
                sueltos_no_declarados.append(md.name)
        except Exception:
            pass

    # ---- comandos ----
    archivos_cmd: List[Path] = []
    if "commands" in pj and pj["commands"]:
        for p in _rutas_declaradas(ruta, pj["commands"]):
            if p.is_file():
                archivos_cmd.append(p)
            elif p.is_dir():
                archivos_cmd.extend(sorted(x for x in p.glob("*.md") if not x.name.startswith(".")))
    else:
        d = ruta / "commands"
        if d.is_dir():
            archivos_cmd = sorted(x for x in d.glob("*.md") if not x.name.startswith("."))
    comandos: List[Dict[str, Any]] = []
    vistos_cmd: Set[str] = set()
    for c in archivos_cmd:
        if c.stem in vistos_cmd:
            continue
        vistos_cmd.add(c.stem)
        f = ficha_md(c, c.stem)
        item = {
            "comando": f"/{nombre_plugin}:{c.stem}", "plugin": nombre_plugin, "fuente": fuente,
            "cargado": cargado, "nombre_corto": c.stem, "archivo": c.name,
            "descripcion": f["descripcion"], "descripcion_bytes": f["descripcion_bytes"],
        }
        item.update(campos_uso_vacios())
        comandos.append(item)

    # ---- hooks ----
    hooks: List[Dict[str, Any]] = []
    decl_hooks = pj.get("hooks")
    if isinstance(decl_hooks, dict):
        hooks = hooks_desde_cfg(decl_hooks, nombre_plugin)
    else:
        candidatos = _rutas_declaradas(ruta, decl_hooks) if decl_hooks else []
        candidatos += [ruta / "hooks" / "hooks.json", ruta / "hooks.json"]
        for h in candidatos:
            if h.is_file():
                cfg = leer_json(h)
                if cfg:
                    hooks = hooks_desde_cfg(cfg, nombre_plugin)
                    break
    for h in hooks:
        h["plugin"] = nombre_plugin
        h["cargado"] = cargado
    modulos: List[str] = []
    for cand in [ruta / "hooks" / "hooks.json", ruta / "hooks.json"]:
        if cand.is_file():
            modulos = modulos_desde_cfg(leer_json(cand))
            if modulos:
                break

    # ---- MCP ----
    srv: List[str] = []
    mj = pj.get("mcpServers")
    if isinstance(mj, dict):
        srv = nombres_mcp({"mcpServers": mj})
    else:
        for cand in _rutas_declaradas(ruta, mj) + [ruta / ".mcp.json"]:
            if cand.is_file():
                srv = nombres_mcp(leer_json(cand))
                if srv:
                    break
    mcp = [{"plugin": nombre_plugin, "nombre": n, "id_en_uso": f"plugin_{nombre_plugin}_{n}",
            "cargado": cargado, "fuente": fuente} for n in srv]

    return {
        "version_declarada": str(pj.get("version") or ""),
        "nombre_declarado": str(pj.get("name") or ""),
        "nombre_efectivo": nombre_plugin,
        "skills": skills, "agentes": agentes, "comandos": comandos, "hooks": hooks, "mcp": mcp,
        "modulos": modulos,
        "skills_en_disco": skills_en_disco,
        "agentes_sueltos_no_declarados": sueltos_no_declarados,
    }


def inventariar_plugins(claude_dir: Path, habilitados: Dict[str, bool]) -> Dict[str, Any]:
    """
    Plugins INSTALADOS (installed_plugins.json) y SINCRONIZADOS (plugins/synced/<cuenta>/*,
    los de claude.ai/Cowork: no figuran en enabledPlugins pero se cargan en las sesiones).
    Devuelve listas separadas por tipo de componente.
    """
    out: Dict[str, Any] = {
        "plugins": [], "skills_plugin": [], "agentes_plugin": [], "comandos_plugin": [],
        "hooks_plugin": [], "mcp_plugin": [],
    }

    def agregar(meta: Dict[str, Any], comp: Dict[str, Any]) -> None:
        meta.update({
            "n_skills": len(comp["skills"]), "n_agentes": len(comp["agentes"]),
            "n_comandos": len(comp["comandos"]), "n_hooks": len(comp["hooks"]), "n_mcp": len(comp["mcp"]),
            "skills": sorted(s["nombre"] for s in comp["skills"]),
            "agents": sorted(a["nombre"] for a in comp["agentes"]),
            "commands": sorted(c["comando"] for c in comp["comandos"]),
            "hooks": sorted(f"{h['evento']}:{h['script']}" for h in comp["hooks"]),
            "mcp": sorted(m["nombre"] for m in comp["mcp"]),
            "modulos": comp["modulos"], "n_modulos": len(comp["modulos"]),
            "tiene_hooks": bool(comp["hooks"]),
            "skills_en_disco": comp["skills_en_disco"],
            "skills_en_disco_no_cargadas": max(0, comp["skills_en_disco"] - len(comp["skills"])),
            "agentes_sueltos_no_declarados": comp["agentes_sueltos_no_declarados"],
        })
        out["plugins"].append(meta)
        out["skills_plugin"].extend(comp["skills"])
        out["agentes_plugin"].extend(comp["agentes"])
        out["comandos_plugin"].extend(comp["comandos"])
        out["hooks_plugin"].extend(comp["hooks"])
        out["mcp_plugin"].extend(comp["mcp"])

    # ---- instalados ----
    data = leer_json(claude_dir / "plugins" / "installed_plugins.json")
    plugins_dict: Dict[str, Any] = {}
    if isinstance(data, dict) and isinstance(data.get("plugins"), dict):
        plugins_dict = data["plugins"]
    rutas_instaladas: Set[str] = set()
    for clave, install_val in plugins_dict.items():
        nombre, marketplace = (clave.rsplit("@", 1) + [""])[:2] if "@" in clave else (clave, "")
        lst = install_val if isinstance(install_val, list) else [install_val]
        inst = next((i for i in lst if isinstance(i, dict) and i.get("installPath")), lst[0] if lst and isinstance(lst[0], dict) else {})
        ruta_str = str(inst.get("installPath") or "")
        ruta = Path(os.path.expanduser(ruta_str)).resolve() if ruta_str else None
        existe = bool(ruta and ruta.is_dir())
        cargado = bool(habilitados.get(clave))
        if existe and ruta is not None:
            rutas_instaladas.add(str(ruta))
        comp = componentes_de_plugin(ruta, nombre, cargado, "instalado") if existe and ruta is not None else {
            "version_declarada": "", "nombre_declarado": "", "nombre_efectivo": nombre, "skills": [], "agentes": [], "comandos": [], "hooks": [],
            "mcp": [], "modulos": [], "skills_en_disco": 0, "agentes_sueltos_no_declarados": []}
        meta = {
            "nombre": nombre, "nombre_en_claude": comp["nombre_efectivo"], "marketplace": marketplace, "clave": clave,
            "fuente": "instalado", "version": str(inst.get("version") or ""),
            "habilitado": cargado, "cargado": cargado,
            "ruta_existe": existe,
            # compat con la versión anterior del inventario:
            "ruta_instalacion": con_tilde(ruta),
        }
        agregar(meta, comp)

    # ---- sincronizados (claude.ai / Cowork) ----
    base = claude_dir / "plugins" / "synced"
    if base.is_dir():
        for cuenta in sorted(base.iterdir(), key=lambda p: p.name):
            if not cuenta.is_dir() or cuenta.name.startswith("."):
                continue
            manifiesto = leer_json(cuenta / "manifest.json") or {}
            por_nombre = {str(p.get("name")): p for p in manifiesto.get("plugins", []) if isinstance(p, dict)}
            for pdir in sorted(cuenta.iterdir(), key=lambda p: p.name):
                if not pdir.is_dir() or pdir.name.startswith("."):
                    continue
                pj = leer_json(pdir / ".claude-plugin" / "plugin.json") or leer_json(pdir / "plugin.json") or {}
                nombre_dir = re.sub(r"~g\d+$", "", pdir.name)
                nombre = str(pj.get("name") or nombre_dir) if isinstance(pj, dict) else nombre_dir
                mt = leer_json(pdir.parent / f"{pdir.name}.meta.json") or {}
                info = por_nombre.get(nombre) or por_nombre.get(nombre_dir) or {}
                comp = componentes_de_plugin(pdir, nombre, True, "sincronizado")
                meta = {
                    "nombre": nombre, "nombre_en_claude": nombre, "marketplace": str(mt.get("marketplace_name") or info.get("marketplaceName") or ""),
                    "clave": f"{nombre}@sincronizado", "fuente": "sincronizado",
                    "version": str(info.get("version") or comp["version_declarada"] or ""),
                    "habilitado": None, "cargado": True,
                    "nota": "Sincronizado desde claude.ai/Cowork: no figura en enabledPlugins; sus skills aparecen en la lista de las sesiones.",
                    "ruta_existe": True, "ruta_instalacion": "",
                }
                agregar(meta, comp)

    # ---- instalaciones viejas / clones temporales en la caché ----
    cache = claude_dir / "plugins" / "cache"
    huerfanas = 0
    temporales = 0
    if cache.is_dir():
        for mkt in cache.iterdir():
            if mkt.name.startswith("temp_"):
                temporales += 1
                continue
            if not mkt.is_dir():
                continue
            for pl in mkt.iterdir():
                if not pl.is_dir():
                    continue
                for ver in pl.iterdir():
                    if ver.is_dir() and str(ver.resolve()) not in rutas_instaladas:
                        huerfanas += 1
    out["cache"] = {"versiones_viejas_no_instaladas": huerfanas, "clones_temporales": temporales}
    return out


def inventariar_servidores_mcp(claude_dir: Path, plugins_mcp: List[Dict[str, Any]],
                               ajustes: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Servidores MCP: ~/.mcp.json, settings.json ('mcpServers'), .mcp.json de proyectos y los de
    plugins (instalados y sincronizados). REGLA DE SEGURIDAD: solo nombres y estado. NUNCA env,
    args ni urls.
    """
    servidores: List[Dict[str, Any]] = []
    habil_local = set(ajustes.get("mcp_habilitados_settings_local", []))
    necesitan_auth = {x.lower() for x in ajustes.get("mcp_necesitan_autenticacion", [])}

    def nuevo(nombre: str, origen: str, habilitado: bool, plugin: str = "", id_en_uso: str = "") -> None:
        s = {"nombre": nombre, "origen": origen, "plugin": plugin, "id_en_uso": id_en_uso or nombre,
             "habilitado": habilitado, "habilitado_en_settings_local": nombre in habil_local,
             "sin_autenticar": bool(plugin and f"plugin:{plugin}:{nombre}".lower() in necesitan_auth) or nombre.lower() in necesitan_auth}
        s.update(campos_uso_vacios())
        servidores.append(s)

    data = leer_json(Path.home() / ".mcp.json")
    if isinstance(data, dict) and isinstance(data.get("mcpServers"), dict):
        for n, v in data["mcpServers"].items():
            nuevo(str(n), "~/.mcp.json", not (isinstance(v, dict) and v.get("disabled") is True))
    sdata = leer_json(claude_dir / "settings.json")
    if isinstance(sdata, dict) and isinstance(sdata.get("mcpServers"), dict):
        for n, v in sdata["mcpServers"].items():
            nuevo(str(n), "settings.json", not (isinstance(v, dict) and v.get("disabled") is True))
    for m in plugins_mcp:
        nuevo(m["nombre"], f"plugin:{m['plugin']} ({m['fuente']})", bool(m["cargado"]), m["plugin"], m["id_en_uso"])
    # ~/.claude.json (alcance usuario y por proyecto) y config de Claude Desktop/Cowork: SOLO nombres
    cj = leer_json(Path.home() / ".claude.json")
    if isinstance(cj, dict):
        if isinstance(cj.get("mcpServers"), dict):
            for n in cj["mcpServers"].keys():
                nuevo(str(n), "~/.claude.json (usuario)", True)
        proy = cj.get("projects")
        if isinstance(proy, dict):
            for ruta_p, pv in proy.items():
                if isinstance(pv, dict) and isinstance(pv.get("mcpServers"), dict):
                    rel_p = str(ruta_p).replace(str(Path.home()) + "/Proyectos/", "") if "/Proyectos" in str(ruta_p) else Path(str(ruta_p)).name
                    for n in pv["mcpServers"].keys():
                        nuevo(str(n), f"~/.claude.json (proyecto {rel_p})", True)
    dc = leer_json(Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json")
    if isinstance(dc, dict) and isinstance(dc.get("mcpServers"), dict):
        for n in dc["mcpServers"].keys():
            nuevo(str(n), "claude_desktop_config.json (Desktop/Cowork)", True)
    # .mcp.json de proyectos
    raiz = Path.home() / "Proyectos"
    proyectos_mcp: List[str] = []
    if raiz.is_dir():
        prof = len(raiz.parts)
        for actual, dirs, files in os.walk(raiz):
            dirs[:] = [d for d in dirs if d not in SALTAR_DIRS and d != "clientes" and not d.startswith(".")]
            if len(Path(actual).parts) - prof >= 3:
                dirs[:] = []
            if ".mcp.json" in files:
                rel = str(Path(actual).relative_to(raiz))
                for n in nombres_mcp(leer_json(Path(actual) / ".mcp.json")):
                    nuevo(n, f"proyecto:{rel}/.mcp.json", True)
                    proyectos_mcp.append(f"{rel}:{n}")
    # servidores que settings.local.json habilita pero que no están definidos en ninguna parte del disco
    conocidos = {s["nombre"] for s in servidores}
    sin_definicion = sorted(n for n in habil_local if n not in conocidos)
    return servidores, sin_definicion


# ==============================================================================
# 3. MEDICIÓN DE USO REAL (CONVERSACIONES .JSONL)
# ==============================================================================

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


# Skills y comandos que traen Claude Code o la app de fábrica (o por conector): aparecen en la lista de las
# sesiones, pero no existen como carpeta en ~/.claude. Lista tomada de la lista de skills de una sesión real.
SKILLS_DE_FABRICA = {
    "update-config", "keybindings-help", "code-review", "simplify", "fewer-permission-prompts", "loop",
    "claude-api", "workflow-authoring", "run", "plugin-authoring", "init", "security-review", "dataviz",
    "artifact-design", "artifact-diagramming", "artifact-capabilities",
    "anthropic-skills:consolidate-memory", "anthropic-skills:explain-usage",
    "anthropic-skills:schedule", "anthropic-skills:setup-claude",
}
COMANDOS_DE_FABRICA = {"/model", "/doctor", "/mcp", "/usage", "/skill-doctor", "/auto-mode-setup", "/clear",
                       "/compact", "/help", "/config", "/memory", "/agents", "/permissions", "/hooks", "/context",
                       "/cost", "/resume", "/status", "/review", "/init"}

CATEGORIAS_USO = ("skills", "agents", "mcp_servers", "mcp_tools", "herramientas_nativas", "slash_commands")


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


# ==============================================================================
# 4. CRUCE MECÁNICO (INVENTARIO + USO REAL)
# ==============================================================================

def aplicar_uso(item: Dict[str, Any], entradas: List[Tuple[Dict[str, Any], bool]]) -> None:
    """
    Suma al ítem el uso de una o más fuentes. Cada fuente es (stats_crudas, es_slash).
      - Skill tool / Agent / MCP: lo que pasó en conversaciones principales va a `usos_principal`
        y lo de subagentes a `usos_subagentes`.
      - /slash: en conversaciones principales es un pedido de Fernando (`usos_principal` y `usos_slash`);
        dentro de subagentes es la PRECARGA de la skill y NO cuenta como uso: va a `precargas_en_subagentes`.
    """
    fechas: List[datetime] = []
    ses: Set[str] = set()
    for e, es_slash in entradas:
        p, s = e["p"], e["s"]
        if p["t"]:
            item["usos_principal"] += p["t"]
            item["usos_principal_30d"] += p["d30"]
            item["usos_principal_90d"] += p["d90"]
            item["usos_30d"] += p["d30"]
            item["usos_90d"] += p["d90"]
            item["usos_total"] += p["t"]
            fechas += [p["primera"], p["ultima"]]
            ses |= p["ses"]
            if es_slash:
                item["usos_slash"] += p["t"]
        if s["t"]:
            if es_slash:
                item["precargas_en_subagentes"] += s["t"]
            else:
                item["usos_subagentes"] += s["t"]
                item["usos_subagentes_30d"] += s["d30"]
                item["usos_subagentes_90d"] += s["d90"]
                item["usos_30d"] += s["d30"]
                item["usos_90d"] += s["d90"]
                item["usos_total"] += s["t"]
                fechas += [s["primera"], s["ultima"]]
                ses |= s["ses"]
    if item["usos_total"] > 0:
        item["nunca_usado"] = False
        previas = [datetime.fromisoformat(x) for x in (item["primera_vez"], item["ultima_vez"]) if x]
        todas = fechas + previas
        item["primera_vez"] = min(todas).isoformat()
        item["ultima_vez"] = max(todas).isoformat()
        item["cantidad_sesiones"] = max(item["cantidad_sesiones"], len(ses))


def clasificar_uso(item: Dict[str, Any]) -> None:
    """Etiqueta el origen del uso: `principal` (Fernando), `solo_subagentes`, `solo_precarga` o `sin_uso`."""
    if item.get("usos_principal", 0) > 0:
        item["origen_uso"] = "principal"
    elif item.get("usos_subagentes", 0) > 0:
        item["origen_uso"] = "solo_subagentes"
    elif item.get("precargas_en_subagentes", 0) > 0:
        item["origen_uso"] = "solo_precarga"
    else:
        item["origen_uso"] = "sin_uso"


def realizar_cruce_general(inv: Dict[str, Any], stats: Dict[str, Dict[str, Dict[str, Any]]]) -> Dict[str, Any]:
    """
    Cruza el inventario con el uso real. Resuelve nombres con prefijo de plugin (`plugin:nombre`),
    suma el uso por Skill tool y por `/slash`, y devuelve lo que NO se pudo asignar a nada del disco.
    """
    u_skill = stats["skills"]
    u_slash = stats["slash_commands"]
    u_agent = stats["agents"]
    u_mcp = stats["mcp_servers"]

    skills_p = inv["skills_personales"]
    skills_pl = inv["skills_plugin"]
    cmds = inv["comandos_plugin"]
    ag_p = inv["agentes"]
    ag_pl = inv["agentes_plugin"]
    mcp = inv["servidores_mcp"]

    def por_nombre(items: List[Dict[str, Any]], clave: str) -> Dict[str, List[Dict[str, Any]]]:
        d: Dict[str, List[Dict[str, Any]]] = {}
        for it in items:
            d.setdefault(it[clave], []).append(it)
        return d

    # ---- skills ----
    idx_sk_p = por_nombre(skills_p, "nombre")
    for k, v in por_nombre(skills_p, "carpeta").items():
        actual = idx_sk_p.setdefault(k, [])
        actual.extend(x for x in v if not any(x is y for y in actual))
    idx_sk_full = por_nombre(skills_pl, "invocacion")
    idx_sk_bare: Dict[str, List[Dict[str, Any]]] = {}
    for s in skills_pl:
        idx_sk_bare.setdefault(s["nombre"], []).append(s)
    idx_cmd = por_nombre(cmds, "comando")
    idx_cmd_bare = por_nombre(cmds, "nombre_corto")

    def preferir_cargados(lista: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        cargados = [x for x in lista if x.get("cargado", True)]
        return cargados or lista

    asignado_skill: Set[str] = set()
    asignado_slash: Set[str] = set()

    def destinos_skill(nombre: str) -> List[Dict[str, Any]]:
        if nombre in idx_sk_p:
            return idx_sk_p[nombre]
        if nombre in idx_sk_full:
            return preferir_cargados(idx_sk_full[nombre])
        if ":" not in nombre and len(set(x["plugin"] for x in idx_sk_bare.get(nombre, []))) == 1:
            return preferir_cargados(idx_sk_bare[nombre])
        return []

    acum: Dict[int, Tuple[Dict[str, Any], List[Tuple[Dict[str, Any], bool]]]] = {}

    def sumar(item: Dict[str, Any], entrada: Dict[str, Any], es_slash: bool) -> None:
        k = id(item)
        if k not in acum:
            acum[k] = (item, [])
        _, lst = acum[k]
        if any(entrada is e for e, _s in lst):
            return
        lst.append((entrada, es_slash))

    for nombre, entrada in u_skill.items():
        dest = destinos_skill(nombre)
        if dest:
            asignado_skill.add(nombre)
            for it in dest:
                sumar(it, entrada, False)
    for nombre, entrada in u_slash.items():
        n = nombre.lstrip("/")
        dest = destinos_skill(n)
        if not dest:
            dcmd = idx_cmd.get("/" + n, [])
            if not dcmd and ":" not in n and len(set(x["plugin"] for x in idx_cmd_bare.get(n, []))) == 1:
                dcmd = idx_cmd_bare[n]
            dest = preferir_cargados(dcmd) if dcmd else []
        if dest:
            asignado_slash.add(nombre)
            for it in dest:
                sumar(it, entrada, True)

    # ---- agentes ----
    idx_ag_p = por_nombre(ag_p, "nombre")
    idx_ag_full = por_nombre(ag_pl, "invocacion")
    idx_ag_bare: Dict[str, List[Dict[str, Any]]] = {}
    for a in ag_pl:
        idx_ag_bare.setdefault(a["nombre"], []).append(a)
    asignado_agent: Set[str] = set()
    for nombre, entrada in u_agent.items():
        dest: List[Dict[str, Any]] = []
        if nombre in idx_ag_p:
            dest = idx_ag_p[nombre]
        elif nombre in idx_ag_full:
            dest = preferir_cargados(idx_ag_full[nombre])
        elif ":" not in nombre and len(set(x["plugin"] for x in idx_ag_bare.get(nombre, []))) == 1:
            dest = preferir_cargados(idx_ag_bare[nombre])
        if dest:
            asignado_agent.add(nombre)
            for it in dest:
                sumar(it, entrada, False)

    # ---- servidores MCP ----
    idx_mcp: Dict[str, List[Dict[str, Any]]] = {}
    for s in mcp:
        idx_mcp.setdefault(s["id_en_uso"], []).append(s)
    asignado_mcp: Set[str] = set()
    for nombre, entrada in u_mcp.items():
        # un mismo servidor puede estar definido en dos lugares (ej. Claude Code y Cowork): el uso se asigna a uno solo
        dest = preferir_cargados(idx_mcp.get(nombre, []))[:1] if idx_mcp.get(nombre) else []
        if dest:
            asignado_mcp.add(nombre)
            for it in dest:
                sumar(it, entrada, False)

    for item, lst in acum.values():
        # una misma skill puede aportar por dos vías (Skill tool + /slash): se suman las dos
        aplicar_uso(item, lst)

    for lista in (skills_p, skills_pl, cmds, ag_p, ag_pl, mcp):
        for it in lista:
            clasificar_uso(it)

    # ---- skills precargadas por agentes ----
    todos_agentes = [(a["nombre"], a) for a in ag_p] + [(a["invocacion"], a) for a in ag_pl if a.get("cargado", True)]
    for nom_ag, ag in todos_agentes:
        for sk in ag.get("skills_precargadas", []):
            dest = destinos_skill(sk)
            for it in dest:
                if nom_ag not in it["precargada_por"]:
                    it["precargada_por"].append(nom_ag)
    for lista in (skills_p, skills_pl):
        for it in lista:
            it["precargada_por"].sort()
            it["uso_solo_por_precarga_o_subagente"] = bool(it["usos_principal"] == 0 and (it["usos_subagentes"] > 0 or it["precargas_en_subagentes"] > 0))

    # ---- lo que tiene uso pero no se pudo asignar a nada del disco ----
    def resto(cat: str, asignados: Set[str]) -> Dict[str, Any]:
        return {n: {"usos_total": v["p"]["t"] + v["s"]["t"], "usos_principal": v["p"]["t"], "usos_subagentes": v["s"]["t"],
                    "ultima_vez": max(x["ultima"] for x in (v["p"], v["s"]) if x["t"]).isoformat()}
                for n, v in sorted(stats[cat].items()) if n not in asignados}

    sin = {
        "skills": resto("skills", asignado_skill),
        "slash_commands": resto("slash_commands", asignado_slash),
        "agents": resto("agents", asignado_agent),
        "mcp_servers": resto("mcp_servers", asignado_mcp),
    }
    por_proyecto: Dict[str, List[str]] = {}
    for p in inv["proyectos"]:
        for sk in p["skills"]:
            por_proyecto.setdefault(sk, []).append(p["ruta"])
    candidatos_sk: Dict[str, List[str]] = {}
    for s_ in skills_pl:
        candidatos_sk.setdefault(s_["nombre"], []).append(s_["invocacion"])
    candidatos_ag: Dict[str, List[str]] = {}
    for a_ in ag_pl:
        candidatos_ag.setdefault(a_["nombre"], []).append(a_["invocacion"])
    for cat in ("skills", "slash_commands"):
        for n, v in sin[cat].items():
            base = n.lstrip("/")
            v["de_fabrica"] = base in SKILLS_DE_FABRICA or n in COMANDOS_DE_FABRICA
            v["existe_en_proyectos"] = sorted(set(por_proyecto.get(base, [])))[:6]
            v["posibles_en_plugins"] = sorted(candidatos_sk.get(base, []))
    for n in list(sin["agents"]):
        sin["agents"][n]["de_fabrica"] = n in AGENTES_DE_FABRICA
        sin["agents"][n]["posibles_en_plugins"] = sorted(candidatos_ag.get(n, []))
    for n in list(sin["mcp_servers"]):
        sin["mcp_servers"][n]["conector_externo"] = bool(re.match(r"^[0-9a-f]{8}-[0-9a-f]{4}-", n) or n.startswith("claude_ai"))
    return sin


# ==============================================================================
# 5. RESUMEN Y GENERACIÓN DE REPORTES (JSON Y MARKDOWN)
# ==============================================================================

def armar_resumen(inv: Dict[str, Any]) -> Dict[str, Any]:
    """Totales derivados de las listas (nunca a mano). Distingue 'en disco' de 'cargado'."""
    plugins = inv["plugins"]
    inst = [p for p in plugins if p["fuente"] == "instalado"]
    sinc = [p for p in plugins if p["fuente"] == "sincronizado"]
    sk_pl = inv["skills_plugin"]
    ag_pl = inv["agentes_plugin"]
    cmds = inv["comandos_plugin"]
    hk_pl = inv["hooks_plugin"]
    mcp = inv["servidores_mcp"]

    def bytes_desc(items: List[Dict[str, Any]]) -> int:
        return sum(int(i.get("descripcion_bytes", 0)) + len(str(i.get("nombre", ""))) for i in items)

    sk_cargadas_pl = [s for s in sk_pl if s["cargado"]]
    ag_cargados_pl = [a for a in ag_pl if a["cargado"]]
    sk_total_cargadas = len(inv["skills_personales"]) + len(sk_cargadas_pl)
    ag_total_cargados = len(inv["agentes"]) + len(ag_cargados_pl)
    por_origen: Dict[str, int] = {}
    for s in mcp:
        k = s["origen"].split(":")[0].split(" ")[0]
        por_origen[k] = por_origen.get(k, 0) + 1
    return {
        # --- claves que ya existían ---
        "total_skills_personales": len(inv["skills_personales"]),
        "total_agentes": len(inv["agentes"]),
        "total_plugins": len(plugins),
        "total_comandos_plugin": len(cmds),
        "total_hooks": len(inv["hooks"]),
        "total_servidores_mcp": len(mcp),
        "total_scripts": len(inv["scripts"]),
        "total_permisos": inv["permisos"],
        # --- desglose nuevo ---
        "plugins_instalados": len(inst),
        "plugins_instalados_habilitados": sum(1 for p in inst if p["habilitado"]),
        "plugins_instalados_apagados": sum(1 for p in inst if not p["habilitado"]),
        "plugins_sincronizados_claude_ai": len(sinc),
        "skills_plugin_en_disco": len(sk_pl),
        "skills_plugin_cargadas": len(sk_cargadas_pl),
        "skills_plugin_cargadas_instaladas": sum(1 for s in sk_cargadas_pl if s["fuente"] == "instalado"),
        "skills_plugin_cargadas_sincronizadas": sum(1 for s in sk_cargadas_pl if s["fuente"] == "sincronizado"),
        "skills_anthropic_synced": sum(1 for s in sk_pl if s["fuente"] == "skills/synced"),
        "skills_cargadas_total": sk_total_cargadas,
        "agentes_plugin_en_disco": len(ag_pl),
        "agentes_plugin_cargados": len(ag_cargados_pl),
        "agentes_cargados_total": ag_total_cargados,
        "comandos_plugin_cargados": sum(1 for c in cmds if c["cargado"]),
        "hooks_settings": len(inv["hooks"]),
        "hooks_plugin_total": len(hk_pl),
        "hooks_plugin_cargados": sum(1 for h in hk_pl if h["cargado"]),
        "hooks_mods": sum(m["hooks"] for m in inv["mods"]),
        "modulos_de_interfaz_mods": sum(len(m["modulos"]) for m in inv["mods"]),
        "modulos_de_interfaz_plugins_cargados": sum(p["n_modulos"] for p in inv["plugins"] if p["cargado"]),
        "hooks_archivos_en_hooks_dir": len(inv["hooks_dir"]),
        "mods": len(inv["mods"]),
        "tareas_programadas": len(inv["tareas_programadas"]),
        "servidores_mcp_por_origen": por_origen,
        "servidores_mcp_cargados": sum(1 for s in mcp if s["habilitado"]),
        "servidores_mcp_sin_autenticar": sum(1 for s in mcp if s["habilitado"] and s["sin_autenticar"]),
        "proyectos_con_componentes_propios": sum(1 for p in inv["proyectos"] if p["skills"] or p["agentes"] or p["reglas"] or p["comandos"] or p["hooks"]),
        "skills_de_proyecto_total": sum(len(p["skills"]) for p in inv["proyectos"]),
        "proyectos_que_parecen_copias_del_ecosistema": sorted(p["ruta"] for p in inv["proyectos"] if p["parece_copia_del_ecosistema"]),
        "skills_de_proyecto_nombres_distintos": len({n for p in inv["proyectos"] for n in p["skills"]}),
        "agentes_de_proyecto_total": sum(len(p["agentes"]) for p in inv["proyectos"]),
        "reglas_de_proyecto_total": sum(len(p["reglas"]) for p in inv["proyectos"]),
        "memoria_total_entradas": inv["memoria"]["total_entradas"],
        "archivado_skills": len(inv["archivo"]["skills_archive"]) + len(inv["archivo"]["skills__archivo"]),
        "archivado_agentes": len(inv["archivo"]["agents_archive"]),
        # peso aproximado de la lista de skills y agentes que Claude carga en cada sesión (bytes de nombre+descripción)
        "peso_descripciones_bytes": {
            "skills_personales": bytes_desc(inv["skills_personales"]),
            "skills_plugin_cargadas": bytes_desc(sk_cargadas_pl),
            "agentes_personales": bytes_desc(inv["agentes"]),
            "agentes_plugin_cargados": bytes_desc(ag_cargados_pl),
        },
    }


def generar_reporte_json(datos: Dict[str, Any], ruta_archivo: Path):
    """Escribe el archivo inventario.json estructurado y formateado."""
    with open(ruta_archivo, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=1)


def generar_reporte_markdown(datos: Dict[str, Any], ruta_archivo: Path):
    """Escribe inventario.md en español: totales, plugins, tablas por usos, nunca usados y ranking."""
    L: List[str] = []
    r = datos["resumen"]
    m = datos["metricas_ejecucion"]

    L.append("# Inventario del Ecosistema Claude Code y Medición de Uso Real")
    L.append("")
    L.append(f"- **Generado el:** {datos.get('generado_en', '-')}")
    L.append(f"- **Conversaciones .jsonl analizadas:** {m.get('archivos_jsonl_leidos', 0)} "
             f"({m.get('archivos_principales', 0)} principales + {m.get('archivos_subagentes', 0)} de subagentes/workflows)")
    L.append(f"- **Líneas leídas:** {m.get('lineas_leidas', 0)} (no parseadas: {m.get('lineas_no_parseadas', 0)})")
    if m.get("solo_disco"):
        L.append("- **Modo:** `--solo-disco` (medición de conversaciones omitida)")
    L.append("- **Cómo leer el uso:** `principal` = conversaciones que abre Fernando; `subagentes` = lo que hacen los agentes por su cuenta "
             "(no es un pedido de Fernando). `Precargas` = veces que un agente cargó la skill al arrancar (un `/slash` dentro de una conversación de subagente: "
             "NO cuenta como uso). `Total` = Fernando + Subagentes.")
    L.append("")

    L.append("## Totales: lo que hay en disco y lo que se carga")
    L.append("")
    L.append("| Familia | En disco | Cargado en sesiones |")
    L.append("| :--- | :---: | :---: |")
    L.append(f"| Skills personales (`~/.claude/skills`) | {r['total_skills_personales']} | {r['total_skills_personales']} |")
    L.append(f"| Skills de plugins | {r['skills_plugin_en_disco']} | {r['skills_plugin_cargadas']} "
             f"({r['skills_plugin_cargadas_instaladas']} instalados + {r['skills_plugin_cargadas_sincronizadas']} sincronizados + {r['skills_anthropic_synced']} `anthropic-skills`) |")
    L.append(f"| **Skills en total** | {r['total_skills_personales'] + r['skills_plugin_en_disco']} | **{r['skills_cargadas_total']}** |")
    L.append(f"| Agentes personales (`~/.claude/agents`) | {r['total_agentes']} | {r['total_agentes']} |")
    L.append(f"| Agentes de plugins | {r['agentes_plugin_en_disco']} | {r['agentes_plugin_cargados']} |")
    L.append(f"| **Agentes en total** | {r['total_agentes'] + r['agentes_plugin_en_disco']} | **{r['agentes_cargados_total']}** |")
    L.append(f"| Plugins instalados | {r['plugins_instalados']} | {r['plugins_instalados_habilitados']} encendidos ({r['plugins_instalados_apagados']} apagados) |")
    L.append(f"| Plugins sincronizados de claude.ai/Cowork | {r['plugins_sincronizados_claude_ai']} | {r['plugins_sincronizados_claude_ai']} |")
    L.append(f"| Comandos de plugins | {r['total_comandos_plugin']} | {r['comandos_plugin_cargados']} |")
    L.append(f"| Hooks en `settings.json` | {r['hooks_settings']} | {r['hooks_settings']} |")
    L.append(f"| Hooks de plugins | {r['hooks_plugin_total']} | {r['hooks_plugin_cargados']} |")
    L.append(f"| Servidores MCP | {r['total_servidores_mcp']} | {r['servidores_mcp_cargados']} ({r['servidores_mcp_sin_autenticar']} sin autenticar) |")
    L.append(f"| Scripts propios | {r['total_scripts']} | - |")
    L.append(f"| Mods (agregados a la pantalla) | {r['mods']} | {r['mods']} |")
    L.append(f"| Tareas programadas (`scheduled-tasks`) | {r['tareas_programadas']} | - |")
    perms = datos["permisos"]
    L.append(f"| Reglas de permisos | {perms['total']} (allow {perms['allow']}, deny {perms['deny']}, ask {perms['ask']}) | - |")
    L.append(f"| Skills / agentes / reglas de proyecto | {r['skills_de_proyecto_total']} / {r['agentes_de_proyecto_total']} / {r['reglas_de_proyecto_total']} | solo en ese proyecto |")
    L.append(f"| Memoria automática (entradas, sin carpetas efímeras) | {r['memoria_total_entradas']} | - |")
    L.append(f"| Archivado (no se carga) | {r['archivado_skills']} skills · {r['archivado_agentes']} agentes | 0 |")
    pd = r["peso_descripciones_bytes"]
    L.append("")
    L.append(f"Peso de nombre+descripción que Claude lista en cada sesión (bytes, estimación por defecto de lo que cuesta el menú): "
             f"skills personales {pd['skills_personales']:,} · skills de plugins {pd['skills_plugin_cargadas']:,} · "
             f"agentes personales {pd['agentes_personales']:,} · agentes de plugins {pd['agentes_plugin_cargados']:,}.")
    L.append("")

    # Plugins
    L.append("## Plugins (instalados y sincronizados)")
    L.append("")
    L.append("| Plugin | Origen | Cargado | Skills | Agentes | Comandos | Hooks | MCP |")
    L.append("| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |")
    for p in sorted(datos["plugins"], key=lambda x: (-(x["n_skills"] + x["n_agentes"]), x["nombre"])):
        cargado = "sí" if p["cargado"] else "no"
        L.append(f"| `{p['nombre']}` | {p['fuente']} · {limpiar_texto_linea(p['marketplace'])} | {cargado} | {p['n_skills']} | {p['n_agentes']} | {p['n_comandos']} | {p['n_hooks']} | {p['n_mcp']} |")
    L.append("")

    def tabla_estandar(items: List[Dict[str, Any]], titulo: str, col_nombre: str = "nombre",
                       col_desc: str = "descripcion", extra: Optional[str] = None):
        L.append(f"## {titulo}")
        L.append("")
        if not items:
            L.append("_No se encontraron elementos registrados._\n")
            return
        cab = "| Nombre | Total | Fernando | Subagentes | Precargas | 30d | Última vez |" + (f" {extra} |" if extra else "") + " Descripción |"
        L.append(cab)
        L.append("| :--- | :---: | :---: | :---: | :---: | :---: | :---: |" + (" :--- |" if extra else "") + " :--- |")
        for it in sorted(items, key=lambda x: (-x.get("usos_total", 0), str(x.get(col_nombre, "")))):
            nom = limpiar_texto_linea(str(it.get(col_nombre, "-")))
            desc = limpiar_texto_linea(str(it.get(col_desc, "")))
            desc = desc[:90] + ("..." if len(desc) > 90 else "")
            extra_v = ""
            if extra == "Precargada por":
                extra_v = " " + (", ".join(it.get("precargada_por", [])[:4]) or "-") + " |"
            L.append(f"| `{nom}` | {it.get('usos_total', 0)} | {it.get('usos_principal', 0)} | {it.get('usos_subagentes', 0)} | "
                     f"{it.get('precargas_en_subagentes', 0)} | {it.get('usos_30d', 0)} | {formatear_fecha(it.get('ultima_vez'))} |{extra_v} {desc} |")
        L.append("")

    tabla_estandar(datos["skills_personales"], "Skills personales", extra="Precargada por")
    tabla_estandar([s for s in datos["skills_plugin"] if s["cargado"]], "Skills de plugins cargados", col_nombre="invocacion", extra="Precargada por")
    tabla_estandar(datos["agentes"], "Agentes personales")
    tabla_estandar([a for a in datos["agentes_plugin"] if a["cargado"]], "Agentes de plugins cargados", col_nombre="invocacion")
    tabla_estandar([c for c in datos["comandos_plugin"] if c["cargado"]], "Comandos de plugins cargados", col_nombre="comando")
    tabla_estandar(datos["servidores_mcp"], "Servidores MCP")

    uso_nativas = datos["uso_real"].get("herramientas_nativas", {})
    if uso_nativas:
        L.append("## Herramientas nativas (uso real)")
        L.append("")
        L.append("| Herramienta | Total | Fernando | Subagentes | 30d | Última vez |")
        L.append("| :--- | :---: | :---: | :---: | :---: | :---: |")
        for n, v in sorted(uso_nativas.items(), key=lambda kv: (-kv[1]["usos_total"], kv[0])):
            L.append(f"| `{n}` | {v['usos_total']} | {v['usos_principal']} | {v['usos_subagentes']} | {v['usos_30d']} | {formatear_fecha(v.get('ultima_vez'))} |")
        L.append("")

    L.append("## Scripts propios (`~/.claude/scripts`)")
    L.append("")
    if datos["scripts"]:
        L.append("| Nombre | Tipo | Tamaño | Fecha | Primer comentario |")
        L.append("| :--- | :---: | :---: | :---: | :--- |")
        for sc in sorted(datos["scripts"], key=lambda x: x.get("nombre", "")):
            L.append(f"| `{limpiar_texto_linea(sc['nombre'])}` | {sc['tipo']} | {sc.get('tamano_bytes', 0)} | "
                     f"{formatear_fecha(sc.get('fecha_modificacion'))} | {limpiar_texto_linea(sc.get('comentario', ''))[:100]} |")
    else:
        L.append("_No se encontraron scripts propios._")
    L.append("")

    L.append("## Hooks de `settings.json`")
    L.append("")
    L.append("| Evento | Matcher | Tipo | Script |")
    L.append("| :--- | :--- | :--- | :--- |")
    for hk in datos["hooks"]:
        L.append(f"| `{hk['evento']}` | `{limpiar_texto_linea(hk['matcher'])}` | {hk['tipo']} | `{hk['script'] or '-'}` |")
    L.append("")
    L.append("## Lo que corre al abrir una sesión (`SessionStart`)")
    L.append("")
    L.append("| Origen | Script | En segundo plano |")
    L.append("| :--- | :--- | :---: |")
    for h in datos["arranque"]:
        L.append(f"| {limpiar_texto_linea(h['origen'])} | `{h['script'] or '-'}` | {'sí' if h['async'] else 'no'} |")
    L.append("")
    L.append("## Hooks de plugins cargados")
    L.append("")
    L.append("| Plugin | Evento | Matcher | Script |")
    L.append("| :--- | :--- | :--- | :--- |")
    for hk in datos["hooks_plugin"]:
        if hk["cargado"]:
            L.append(f"| `{hk['plugin']}` | `{hk['evento']}` | `{limpiar_texto_linea(hk['matcher'])}` | `{hk['script'] or '-'}` |")
    L.append("")

    L.append("## Proyectos con componentes propios (`~/Proyectos/**/.claude`)")
    L.append("")
    L.append("| Proyecto | Skills | Agentes | Reglas | Comandos | Hooks | CLAUDE.md (bytes) | Nota |")
    L.append("| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |")
    for p in datos["proyectos"]:
        if p["skills"] or p["agentes"] or p["reglas"] or p["comandos"] or p["hooks"]:
            L.append(f"| `{p['ruta']}` | {len(p['skills'])} | {len(p['agentes'])} | {len(p['reglas'])} | {len(p['comandos'])} | {p['hooks']} | {p['claude_md'].get('bytes', '-')} | {'copia del ecosistema' if p['parece_copia_del_ecosistema'] else ''} |")
    L.append("")

    L.append("## Memoria automática (solo conteos)")
    L.append("")
    L.append("| Proyecto | Entradas |")
    L.append("| :--- | :---: |")
    for k, v in sorted(datos["memoria"]["entradas_por_proyecto"].items(), key=lambda kv: -kv[1]):
        L.append(f"| `{k}` | {v} |")
    L.append("")

    L.append("## Nunca usados (por categoría; solo ítems cargados)")
    L.append("")
    categorias = [
        ("Skills personales", datos["skills_personales"], "nombre"),
        ("Skills de plugins", [s for s in datos["skills_plugin"] if s["cargado"]], "invocacion"),
        ("Agentes personales", datos["agentes"], "nombre"),
        ("Agentes de plugins", [a for a in datos["agentes_plugin"] if a["cargado"]], "invocacion"),
        ("Comandos de plugins", [c for c in datos["comandos_plugin"] if c["cargado"]], "comando"),
        ("Servidores MCP", [s for s in datos["servidores_mcp"] if s["habilitado"]], "id_en_uso"),
    ]
    for titulo_cat, items_cat, k_nom in categorias:
        nunca = [x for x in items_cat if x.get("nunca_usado", True)]
        L.append(f"### {titulo_cat}: {len(nunca)} de {len(items_cat)} sin ningún uso")
        for n_it in sorted(nunca, key=lambda x: str(x.get(k_nom, ""))):
            L.append(f"- `{n_it.get(k_nom, '-')}`")
        L.append("")

    L.append("## Uso sin nada en disco que le corresponda")
    L.append("")
    for cat, d in datos["uso_sin_inventario"].items():
        L.append(f"- **{cat}:** {len(d)} nombres (ver `uso_sin_inventario.{cat}` en el JSON)")
    L.append("")

    L.append("## Los 20 más usados (conversaciones de Fernando)")
    L.append("")
    ranking: List[Dict[str, Any]] = []
    for etiqueta, lista, k in (("Skill personal", datos["skills_personales"], "nombre"),
                               ("Skill de plugin", datos["skills_plugin"], "invocacion"),
                               ("Agente", datos["agentes"], "nombre"),
                               ("Agente de plugin", datos["agentes_plugin"], "invocacion"),
                               ("Comando de plugin", datos["comandos_plugin"], "comando"),
                               ("Servidor MCP", datos["servidores_mcp"], "id_en_uso")):
        for it in lista:
            if it.get("usos_principal", 0) > 0:
                ranking.append({"tipo": etiqueta, "nombre": it[k], "p": it["usos_principal"], "s": it["usos_subagentes"], "u": it.get("ultima_vez")})
    for n, v in uso_nativas.items():
        if v["usos_principal"] > 0:
            ranking.append({"tipo": "Herramienta nativa", "nombre": n, "p": v["usos_principal"], "s": v["usos_subagentes"], "u": v.get("ultima_vez")})
    L.append("| # | Categoría | Nombre | Fernando | Subagentes | Última vez |")
    L.append("| :---: | :--- | :--- | :---: | :---: | :---: |")
    for i, e in enumerate(sorted(ranking, key=lambda x: (-x["p"], x["nombre"]))[:20], 1):
        L.append(f"| {i} | {e['tipo']} | `{e['nombre']}` | {e['p']} | {e['s']} | {formatear_fecha(e['u'])} |")
    L.append("")

    with open(ruta_archivo, "w", encoding="utf-8") as f:
        f.write("\n".join(L))


# ==============================================================================
# 6. EJECUCIÓN PRINCIPAL Y AUTOCONTROL POR CONSOLA
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Inventario mecánico y medición de uso del ecosistema Claude Code (~/.claude)."
    )
    parser.add_argument("--out", type=str, default="./inventario_resultado",
                        help="Carpeta de destino para inventario.json e inventario.md.")
    parser.add_argument("--solo-disco", action="store_true",
                        help="Omitir el análisis de conversaciones .jsonl para ejecución rápida.")
    parser.add_argument("--claude-dir", type=str, default=str(Path.home() / ".claude"),
                        help="Ruta base del directorio de Claude (default: ~/.claude).")
    parser.add_argument("--proyectos-dir", type=str, default=str(Path.home() / "Proyectos"),
                        help="Carpeta de proyectos donde buscar .claude de proyecto (default: ~/Proyectos).")
    args = parser.parse_args()

    claude_dir = Path(os.path.expanduser(args.claude_dir)).resolve()
    out_dir = Path(os.path.expanduser(args.out)).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. Recolección de disco
    settings = leer_json(claude_dir / "settings.json") or {}
    en_plugins = settings.get("enabledPlugins") if isinstance(settings, dict) else {}
    habilitados = {str(k): bool(v) for k, v in en_plugins.items()} if isinstance(en_plugins, dict) else {}
    marketplaces: List[str] = []
    extra_m = settings.get("extraKnownMarketplaces") if isinstance(settings, dict) else None
    if isinstance(extra_m, dict):
        marketplaces = sorted(str(k) for k in extra_m.keys())
    conocidos = leer_json(claude_dir / "plugins" / "known_marketplaces.json")
    marketplaces_conocidos = sorted(conocidos.keys()) if isinstance(conocidos, dict) else []

    skills_personales = inventariar_skills_personales(claude_dir)
    agentes = inventariar_agentes(claude_dir)
    pl = inventariar_plugins(claude_dir, habilitados)
    skills_plugin = pl["skills_plugin"] + inventariar_skills_sincronizadas(claude_dir)
    hooks = inventariar_hooks(claude_dir)
    ajustes = inventariar_ajustes(claude_dir)
    servidores_mcp, mcp_sin_definicion = inventariar_servidores_mcp(claude_dir, pl["mcp_plugin"], ajustes)
    mods = inventariar_mods(claude_dir)
    hooks_mods: List[Dict[str, Any]] = []
    for md in mods:
        hk = leer_json(claude_dir / "mods" / md["nombre"] / "hooks" / "hooks.json")
        hooks_mods += hooks_desde_cfg(hk, f"mod:{md['nombre']}") if hk else []

    # 2. Medición de uso real
    if not args.solo_disco:
        stats, metricas = medir_uso_real(claude_dir)
    else:
        stats = {c: {} for c in CATEGORIAS_USO}
        metricas = {"archivos_jsonl_leidos": 0, "archivos_principales": 0, "archivos_subagentes": 0,
                    "lineas_leidas": 0, "lineas_no_parseadas": 0}
    metricas["solo_disco"] = args.solo_disco

    inv: Dict[str, Any] = {
        "generado_en": datetime.now(timezone.utc).isoformat(),
        "directorio_claude": con_tilde(claude_dir),
        "metricas_ejecucion": metricas,
        "skills_personales": skills_personales,
        "agentes": agentes,
        "plugins": pl["plugins"],
        "skills_plugin": skills_plugin,
        "agentes_plugin": pl["agentes_plugin"],
        "comandos_plugin": pl["comandos_plugin"],
        "hooks": hooks,
        "hooks_plugin": pl["hooks_plugin"],
        "hooks_mods": hooks_mods,
        "hooks_dir": inventariar_hooks_dir(claude_dir, hooks),
        "servidores_mcp": servidores_mcp,
        "mcp_habilitados_sin_definicion_en_disco": mcp_sin_definicion,
        "plugins_habilitados_settings": [{"nombre": k, "habilitado": v} for k, v in sorted(habilitados.items())],
        "marketplaces_conocidos": marketplaces_conocidos,
        "marketplaces_extra_settings": marketplaces,
        "cache_plugins": pl["cache"],
        "mods": mods,
        "tareas_programadas": inventariar_tareas_programadas(claude_dir),
        "scripts": inventariar_scripts(claude_dir),
        "permisos": inventariar_permisos(claude_dir),
        "ajustes": ajustes,
        "otros": inventariar_recetas_y_otros(claude_dir),
        "archivo": inventariar_archivo(claude_dir),
        "claude_md_global": inventariar_claude_md(claude_dir),
        "proyectos": inventariar_proyectos(Path(os.path.expanduser(args.proyectos_dir)).resolve(),
                                           {sk["nombre"] for sk in skills_personales} | {sk["carpeta"] for sk in skills_personales}),
        "memoria": inventariar_memoria(claude_dir),
        "rutinas_registradas": inventariar_rutinas(),
    }
    inv["arranque"] = [h for h in hooks if h["evento"] == "SessionStart"] + \
                      [h for h in inv["hooks_plugin"] if h["evento"] == "SessionStart" and h["cargado"]] + \
                      [h for h in hooks_mods if h["evento"] == "SessionStart"]
    inv["resumen"] = armar_resumen(inv)
    contador = leer_contador_interno_skills()

    # 3. Cruce mecánico
    uso_sin = realizar_cruce_general(inv, stats)
    inv["uso_real"] = serializar_uso(stats)
    inv["uso_sin_inventario"] = uso_sin
    inv["contador_interno_skills"] = contador
    for it in inv["skills_personales"]:
        it["contador_interno_claude"] = contador.get(it["nombre"])
    for it in inv["skills_plugin"]:
        it["contador_interno_claude"] = contador.get(it["invocacion"])
    # Totales de uso que dependen del cruce
    def por_origen(items: List[Dict[str, Any]]) -> Dict[str, int]:
        c: Dict[str, int] = {}
        for it in items:
            c[it["origen_uso"]] = c.get(it["origen_uso"], 0) + 1
        return dict(sorted(c.items()))
    inv["resumen"]["skills_cargadas_por_origen_de_uso"] = por_origen(inv["skills_personales"] + [s for s in inv["skills_plugin"] if s["cargado"]])
    inv["resumen"]["agentes_cargados_por_origen_de_uso"] = por_origen(inv["agentes"] + [a for a in inv["agentes_plugin"] if a["cargado"]])
    inv["resumen"]["skills_cargadas_nunca_usadas"] = (
        sum(1 for s in inv["skills_personales"] if s["nunca_usado"]) +
        sum(1 for s in inv["skills_plugin"] if s["cargado"] and s["nunca_usado"]))
    inv["resumen"]["agentes_cargados_nunca_usados"] = (
        sum(1 for a in inv["agentes"] if a["nunca_usado"]) +
        sum(1 for a in inv["agentes_plugin"] if a["cargado"] and a["nunca_usado"]))

    # 3b. Depuración: ningún nombre de cliente de la lista de prohibidos sale en los archivos
    contador_depurados = [0]
    inv = depurar_clientes(inv, cargar_patron_clientes(claude_dir), contador_depurados)
    inv["metricas_ejecucion"]["textos_depurados_de_nombres_de_clientes"] = contador_depurados[0]

    # 4. Salida
    json_salida = out_dir / "inventario.json"
    md_salida = out_dir / "inventario.md"
    ordenado = {k: inv[k] for k in sorted(inv.keys(), key=lambda x: (x not in ("generado_en", "directorio_claude", "metricas_ejecucion", "resumen"), x))}
    generar_reporte_json(ordenado, json_salida)
    generar_reporte_markdown(inv, md_salida)

    r = inv["resumen"]
    print("=" * 66)
    print("        RESUMEN DEL INVENTARIO DEL ECOSISTEMA CLAUDE")
    print("=" * 66)
    print(f"Skills personales         : {r['total_skills_personales']}")
    print(f"Skills de plugins         : {r['skills_plugin_en_disco']} en disco · {r['skills_plugin_cargadas']} cargadas")
    print(f"Skills cargadas (total)   : {r['skills_cargadas_total']}")
    print(f"Agentes personales        : {r['total_agentes']}")
    print(f"Agentes de plugins        : {r['agentes_plugin_en_disco']} en disco · {r['agentes_plugin_cargados']} cargados")
    print(f"Plugins                   : {r['plugins_instalados']} instalados ({r['plugins_instalados_habilitados']} encendidos) + {r['plugins_sincronizados_claude_ai']} sincronizados")
    print(f"Comandos de plugin        : {r['total_comandos_plugin']}")
    print(f"Hooks settings / plugins  : {r['hooks_settings']} / {r['hooks_plugin_cargados']} cargados")
    print(f"Servidores MCP            : {r['total_servidores_mcp']}")
    print(f"Scripts                   : {r['total_scripts']}")
    print(f"Memoria (entradas)        : {r['memoria_total_entradas']}")
    print("-" * 66)
    print(f"Conversaciones .jsonl     : {metricas['archivos_jsonl_leidos']} ({metricas['archivos_principales']} principales + {metricas['archivos_subagentes']} subagentes)")
    print(f"Líneas leídas / sin parsear: {metricas['lineas_leidas']} / {metricas['lineas_no_parseadas']}")
    print("=" * 66)
    print(f"Archivos generados en '{out_dir}': {json_salida.name}, {md_salida.name}")


if __name__ == "__main__":
    main()
