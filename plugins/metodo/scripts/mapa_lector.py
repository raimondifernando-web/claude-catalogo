#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mapa_lector.py - Lector del mapa del ecosistema Claude Code (~/.claude).
Disparador: encadenado — lo usa mapa.py (el comando `mapa`).

Recorre el disco registrando todo acceso mediante IO (mapa_io) y cruza
los metadatos de estructura con el uso real (mapa_uso).
Python 3.9 estándar, sin librerías externas.
"""

import argparse
import copy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from mapa_io import (
    IO,
    Entrada,
    crear_directorio,
    escribir_json,
    escribir_texto,
    io_por_defecto,
)
import mapa_uso


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
# 2. INVENTARIO MECÁNICO DESDE EL DISCO (CON IO)
# ==============================================================================

SALTAR_DIRS = {"node_modules", ".git", "__pycache__", ".venv", "venv", ".omc", ".build", ".pytest_cache", ".ruff_cache", ".mypy_cache"}
AGENTES_DE_FABRICA = mapa_uso.AGENTES_DE_FABRICA
SKILLS_DE_FABRICA = mapa_uso.SKILLS_DE_FABRICA
COMANDOS_DE_FABRICA = mapa_uso.COMANDOS_DE_FABRICA
CATEGORIAS_USO = mapa_uso.CATEGORIAS_USO


def con_tilde(ruta: Any, home: Optional[Union[str, Path]] = None) -> str:
    """Muestra una ruta con `~` en vez de la carpeta personal (el inventario no lleva el nombre de usuario)."""
    if not ruta:
        return ""
    if home is not None:
        return str(ruta).replace(str(home), "~")
    return str(ruta)


def cargar_patron_clientes(io: IO) -> Optional["re.Pattern[str]"]:
    """
    Patrón con los nombres de clientes/personas que NO deben salir del equipo (~/.claude/nombres-prohibidos.txt,
    una por línea, `#` = comentario). Si el archivo no existe, no se depura nada.
    """
    archivo = io.claude_dir / "nombres-prohibidos.txt"
    txt = io.leer_texto(archivo)
    if not txt:
        return None
    nombres = [l.strip() for l in txt.splitlines() if l.strip() and not l.strip().startswith("#")]
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


# Patrones de seguridad para tapar claves o credenciales sensibles
_PATRONES_CLAVES = [
    re.compile(r"-----BEGIN " + r"[A-Za-z0-9_\- ]*PRIVATE KEY-----"),
    re.compile(r"AK" + r"IA[0-9A-Z]{16}"),
    re.compile(r"gh" + r"[pousr]_[A-Za-z0-9]{36}"),
    re.compile(r"s" + r"k-[A-Za-z0-9_\-]{20,}"),
    re.compile(r"x" + r"ox[abpr]-"),
    re.compile(r"AI" + r"za[0-9A-Za-z_\-]{35}"),
    re.compile(r"(?:pass" + r"word|passwd|secret|token|api[_\-]?key)\s*[=:]\s*\S{8,}", re.IGNORECASE),
]


def tapar_claves(obj: Any) -> Any:
    """
    Recorre recursivamente listas/dicts y reemplaza por '[tapado]'
    las cadenas que contengan claves o credenciales sensibles.
    No cambia ninguna otra cadena.
    """
    if isinstance(obj, str):
        for pat in _PATRONES_CLAVES:
            if pat.search(obj):
                return "[tapado]"
        return obj
    if isinstance(obj, list):
        return [tapar_claves(x) for x in obj]
    if isinstance(obj, tuple):
        return tuple(tapar_claves(x) for x in obj)
    if isinstance(obj, dict):
        return {
            (tapar_claves(k) if isinstance(k, str) else k): tapar_claves(v)
            for k, v in obj.items()
        }
    return obj


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


def fecha_de(io: IO, ruta: Path) -> str:
    mt = io.mtime(ruta)
    if mt is not None:
        try:
            return datetime.fromtimestamp(mt, tz=timezone.utc).isoformat()
        except Exception:
            return ""
    return ""


def ficha_md(io: IO, ruta: Path, nombre_defecto: str) -> Dict[str, Any]:
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
        t_bytes = io.tamano(ruta)
        ficha["tamano_bytes"] = t_bytes if t_bytes is not None else 0
        ficha["fecha_modificacion"] = fecha_de(io, ruta)
        contenido = io.leer_texto(ruta)
        if contenido is not None:
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


def skills_en_dir(io: IO, base: Path) -> List[Path]:
    """Carpetas hijas directas de `base` que tienen SKILL.md (sigue symlinks)."""
    salida: List[Path] = []
    if not io.es_dir(base):
        return salida
    for e in io.listar(base):
        if e.nombre.startswith(".") or e.nombre in SALTAR_DIRS:
            continue
        if e.es_dir and io.es_archivo(e.ruta / "SKILL.md"):
            salida.append(e.ruta)
    return salida


def campos_uso_vacios() -> Dict[str, Any]:
    return {
        "usos_total": 0, "usos_30d": 0, "usos_90d": 0,
        "usos_principal": 0, "usos_subagentes": 0, "usos_slash": 0,
        "usos_principal_30d": 0, "usos_principal_90d": 0, "usos_subagentes_30d": 0, "usos_subagentes_90d": 0,
        "precargas_en_subagentes": 0,
        "primera_vez": None, "ultima_vez": None,
        "cantidad_sesiones": 0, "nunca_usado": True,
    }


def inventariar_skills_personales(io: IO) -> List[Dict[str, Any]]:
    """Inventaria ~/.claude/skills/*/SKILL.md (activas personales; _archivo y synced van aparte)."""
    skills_dir = io.claude_dir / "skills"
    items: List[Dict[str, Any]] = []
    for carpeta in skills_en_dir(io, skills_dir):
        if carpeta.name in ("_archivo", "synced"):
            continue
        f = ficha_md(io, carpeta / "SKILL.md", carpeta.name)
        item = {
            "nombre": f["nombre"],
            "carpeta": carpeta.name,
            "es_symlink": io.es_symlink(carpeta),
            "descripcion": f["descripcion"],
            "descripcion_bytes": f["descripcion_bytes"],
            "tamano_bytes": f["tamano_bytes"],
            "fecha_modificacion": f["fecha_modificacion"],
            "tiene_nota_local": io.existe(carpeta / "NOTA-LOCAL.md"),
            "cantidad_archivos": io.contar_archivos(carpeta),
            "precargada_por": [],
        }
        item.update(campos_uso_vacios())
        items.append(item)
    return items


def inventariar_skills_sincronizadas(io: IO) -> List[Dict[str, Any]]:
    """
    ~/.claude/skills/synced/<cuenta>/*/SKILL.md: skills que claude.ai/Cowork sincroniza
    (se invocan como `anthropic-skills:<nombre>`).
    """
    items: List[Dict[str, Any]] = []
    base = io.claude_dir / "skills" / "synced"
    if not io.es_dir(base):
        return items
    for e_cuenta in io.listar(base):
        if e_cuenta.nombre.startswith(".") or not e_cuenta.es_dir:
            continue
        for carpeta in skills_en_dir(io, e_cuenta.ruta):
            f = ficha_md(io, carpeta / "SKILL.md", carpeta.name)
            item = {
                "plugin": "anthropic-skills",
                "fuente": "skills/synced",
                "cargado": True,
                "nombre": f["nombre"],
                "invocacion": f"anthropic-skills:{f['nombre']}",
                "descripcion": f["descripcion"],
                "descripcion_bytes": f["descripcion_bytes"],
                "tamano_bytes": f["tamano_bytes"],
                "cantidad_archivos": io.contar_archivos(carpeta),
                "precargada_por": [],
            }
            item.update(campos_uso_vacios())
            items.append(item)
    return items


def inventariar_archivo(io: IO) -> Dict[str, Any]:
    """Lo archivado (no se carga): solo conteos y nombres."""
    res: Dict[str, Any] = {}
    sk = io.claude_dir / "skills-archive"
    res["skills_archive"] = sorted(p.name for p in skills_en_dir(io, sk))
    ag = io.claude_dir / "agents-archive"
    ag_list: List[str] = []
    if io.es_dir(ag):
        for e in io.listar(ag):
            if not e.es_dir and e.nombre.endswith(".md") and not e.nombre.startswith("."):
                ag_list.append(e.ruta.stem)
    res["agents_archive"] = sorted(ag_list)
    arch = io.claude_dir / "skills" / "_archivo"
    internas: List[str] = []
    if io.es_dir(arch):
        for e_grupo in io.listar(arch):
            if e_grupo.es_dir and not e_grupo.nombre.startswith("."):
                for s in skills_en_dir(io, e_grupo.ruta):
                    internas.append(f"{e_grupo.nombre}/{s.name}")
    res["skills__archivo"] = internas
    return res


def inventariar_agentes(io: IO) -> List[Dict[str, Any]]:
    """Inventaria ~/.claude/agents/*.md (agentes personales)."""
    agents_dir = io.claude_dir / "agents"
    items: List[Dict[str, Any]] = []
    if not io.es_dir(agents_dir):
        return items
    for e in io.listar(agents_dir):
        if e.es_dir or not e.nombre.endswith(".md") or e.nombre.startswith("."):
            continue
        agente_file = e.ruta
        f = ficha_md(io, agente_file, agente_file.stem)
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


def inventariar_hooks(io: IO) -> List[Dict[str, Any]]:
    """settings.json -> hooks (anidados: evento -> reglas -> hooks)."""
    data = io.leer_json(io.claude_dir / "settings.json")
    if not isinstance(data, dict):
        return []
    return hooks_desde_cfg(data.get("hooks"), "settings.json")


def inventariar_hooks_dir(io: IO, hooks_settings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Archivos de ~/.claude/hooks y si están registrados en settings.json."""
    base = io.claude_dir / "hooks"
    registrados = {h["script"] for h in hooks_settings if h.get("script")}
    items: List[Dict[str, Any]] = []
    if not io.es_dir(base):
        return items
    for e in io.listar(base):
        if e.nombre.startswith(".") or e.nombre in SALTAR_DIRS or e.es_dir:
            continue
        t_bytes = io.tamano(e.ruta)
        items.append({
            "nombre": e.nombre,
            "tamano_bytes": t_bytes if t_bytes is not None else 0,
            "registrado_en_settings": e.nombre in registrados,
        })
    return items


def inventariar_mods(io: IO) -> List[Dict[str, Any]]:
    """~/.claude/mods/*: agregados propios a la pantalla (con sus hooks)."""
    base = io.claude_dir / "mods"
    items: List[Dict[str, Any]] = []
    if not io.es_dir(base):
        return items
    for e_mod in io.listar(base):
        if e_mod.nombre.startswith(".") or not e_mod.es_dir:
            continue
        mod = e_mod.ruta
        pj = io.leer_json(mod / "plugin.json") or io.leer_json(mod / ".claude-plugin" / "plugin.json") or {}
        hk = io.leer_json(mod / "hooks" / "hooks.json")
        hooks = hooks_desde_cfg(hk, f"mod:{e_mod.nombre}") if hk else []
        modulos = modulos_desde_cfg(hk)
        items.append({
            "nombre": e_mod.nombre,
            "version": str(pj.get("version") or "") if isinstance(pj, dict) else "",
            "descripcion": str(pj.get("description") or "")[:300] if isinstance(pj, dict) else "",
            "hooks": len(hooks),
            "modulos": modulos,
            "cantidad_archivos": io.contar_archivos(mod),
        })
    return items


def inventariar_tareas_programadas(io: IO) -> List[Dict[str, Any]]:
    """~/.claude/scheduled-tasks/*/SKILL.md."""
    items: List[Dict[str, Any]] = []
    base = io.claude_dir / "scheduled-tasks"
    for carpeta in skills_en_dir(io, base):
        f = ficha_md(io, carpeta / "SKILL.md", carpeta.name)
        items.append({"nombre": f["nombre"], "carpeta": carpeta.name, "descripcion": f["descripcion"]})
    return items


def inventariar_recetas_y_otros(io: IO) -> Dict[str, Any]:
    """Recetas, templates y servidores MCP propios de ~/.claude (solo nombres)."""
    def nombres(base: Path, solo_md: bool = False) -> List[str]:
        if not io.es_dir(base):
            return []
        res = []
        for e in io.listar(base):
            if e.nombre.startswith("."):
                continue
            if solo_md:
                if not e.es_dir and e.nombre.endswith(".md"):
                    res.append(e.nombre)
            else:
                res.append(e.nombre)
        return sorted(res)

    return {
        "recetas": nombres(io.claude_dir / "recetas", solo_md=True),
        "templates": nombres(io.claude_dir / "templates", solo_md=False),
        "mcp_servers_propios": nombres(io.claude_dir / "mcp-servers", solo_md=False),
        "commands_globales": nombres(io.claude_dir / "commands", solo_md=True),
        "rules_globales": nombres(io.claude_dir / "rules", solo_md=True),
        "output_styles": nombres(io.claude_dir / "output-styles", solo_md=False),
    }


def inventariar_scripts(io: IO) -> List[Dict[str, Any]]:
    """
    Inventaria ~/.claude/scripts/*: archivos (tipo 'archivo') y carpetas (tipo 'carpeta').
    Para archivos: primera línea de comentario (# ...).
    Para carpetas: cantidad de archivos dentro y primera línea del README si existe.
    """
    scripts_dir = io.claude_dir / "scripts"
    items: List[Dict[str, Any]] = []
    if not io.es_dir(scripts_dir):
        return items

    for e in io.listar(scripts_dir):
        if e.nombre.startswith(".") or e.nombre in SALTAR_DIRS:
            continue
        f_path = e.ruta

        if not e.es_dir:  # archivo
            primer_comentario = ""
            tamano = io.tamano(f_path) or 0
            mtime = fecha_de(io, f_path)
            texto = io.leer_texto(f_path)
            if texto:
                for linea in texto.splitlines():
                    linea_strip = linea.strip()
                    if linea_strip.startswith("#"):
                        if linea_strip.startswith("#!"):
                            continue
                        primer_comentario = linea_strip.lstrip("#").strip()[:300]
                        break

            items.append({
                "nombre": e.nombre,
                "tipo": "archivo",
                "comentario": primer_comentario,
                "tamano_bytes": tamano,
                "fecha_modificacion": mtime,
                "cantidad_archivos": 1
            })

        else:  # carpeta
            primer_comentario = ""
            tamano = 0
            mtime = fecha_de(io, f_path)
            cantidad_archivos = io.contar_archivos(f_path)

            readme_file = None
            for cand in ("README.md", "README", "readme.md", "Readme.md", "readme.txt", "README.txt"):
                cand_path = f_path / cand
                if io.es_archivo(cand_path):
                    readme_file = cand_path
                    break
            if readme_file:
                rtxt = io.leer_texto(readme_file)
                if rtxt:
                    for linea in rtxt.splitlines():
                        linea_strip = linea.strip()
                        if linea_strip:
                            primer_comentario = linea_strip.lstrip("#").strip()[:300]
                            break

            items.append({
                "nombre": e.nombre,
                "tipo": "carpeta",
                "comentario": primer_comentario,
                "readme_primera_linea": primer_comentario,
                "cantidad_archivos": cantidad_archivos,
                "tamano_bytes": tamano,
                "fecha_modificacion": mtime
            })

    return items


def inventariar_permisos(io: IO) -> Dict[str, int]:
    """
    settings.json clave 'permissions': cuenta cantidad de reglas allow/deny/ask.
    REGLA DE SEGURIDAD: nunca guarda las reglas específicas.
    """
    conteo = {"allow": 0, "deny": 0, "ask": 0, "total": 0}
    data = io.leer_json(io.claude_dir / "settings.json")
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


def inventariar_ajustes(io: IO) -> Dict[str, Any]:
    """
    Otras claves de settings.json / settings.local.json. SOLO nombres de claves y conteos:
    nunca valores (el bloque env puede traer rutas o claves).
    """
    s = io.leer_json(io.claude_dir / "settings.json") or {}
    sl = io.leer_json(io.claude_dir / "settings.local.json") or {}
    sl_perms = sl.get("permissions") if isinstance(sl, dict) else None
    return {
        "claves_settings": sorted(s.keys()) if isinstance(s, dict) else [],
        "env_claves": sorted((s.get("env") or {}).keys()) if isinstance(s.get("env"), dict) else [],
        "tiene_statusline": bool(isinstance(s, dict) and s.get("statusLine")),
        "statusline_script": extraer_basename_script(str((s.get("statusLine") or {}).get("command") or "")) if isinstance(s.get("statusLine"), dict) else "",
        "settings_local_claves": sorted(sl.keys()) if isinstance(sl, dict) else [],
        "settings_local_permisos": len(sl_perms) if isinstance(sl_perms, (list, dict)) else 0,
        "mcp_habilitados_settings_local": sorted(lista_str(sl.get("enabledMcpjsonServers"))) if isinstance(sl, dict) else [],
        # solo los NOMBRES (la app reescribe ese archivo con fechas todo el tiempo y no deben rehacer el mapa)
        "mcp_necesitan_autenticacion": sorted(io.nombres_json(io.claude_dir / "mcp-needs-auth-cache.json", [], "claude:mcp_necesitan_autenticacion")),
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


def podar_recorrido_proyectos_claude(actual: str, dirs: List[str], prof_raiz: int) -> None:
    """Regla de poda para buscar carpetas .claude dentro de Proyectos (hasta 4 niveles)."""
    rel_parts = Path(actual).parts[prof_raiz:]
    # Descartar carpetas que empiezan con '.' (salvo exactamente '.claude') o con '_':
    # las copias temporales duplican las piezas del proyecto real.
    dirs[:] = sorted(
        d for d in dirs
        if d not in SALTAR_DIRS
        and d != "clientes"
        and (d == ".claude" or (not d.startswith(".") and not d.startswith("_")))
    )
    if len(rel_parts) >= 4:
        dirs[:] = []


def podar_recorrido_proyectos_mcp(actual: str, dirs: List[str], prof_raiz: int) -> None:
    """Regla de poda para buscar .mcp.json dentro de Proyectos (hasta 3 niveles, sin ocultos)."""
    dirs[:] = [d for d in dirs if d not in SALTAR_DIRS and d != "clientes" and not d.startswith(".")]
    if len(Path(actual).parts) - prof_raiz >= 3:
        dirs[:] = []


def inventariar_proyectos(io: IO, raiz: Union[str, Path], skills_personales: Optional[Set[str]] = None) -> List[Dict[str, Any]]:
    """
    Recorre ~/Proyectos buscando carpetas `.claude` (hasta 4 niveles, sin node_modules/.git
    ni carpetas llamadas `clientes`) y anota qué componentes propios de proyecto hay:
    skills, agentes, reglas, comandos, hooks. Solo nombres y conteos.
    """
    items: List[Dict[str, Any]] = []
    raiz_path = Path(raiz)
    if not io.es_dir(raiz_path):
        return items
    prof_raiz = len(raiz_path.parts)
    for actual, dirs, _files in io.caminar(raiz_path):
        podar_recorrido_proyectos_claude(actual, dirs, prof_raiz)
        if Path(actual).name != ".claude":
            continue
        dirs[:] = []  # no seguir dentro de .claude
        cdir = Path(actual)
        proyecto = cdir.parent
        rel = proyecto.relative_to(raiz_path).as_posix() if proyecto != raiz_path else "."
        skills = [p.name for p in skills_en_dir(io, cdir / "skills")]
        agentes = [e.ruta.stem for e in io.listar(cdir / "agents") if not e.es_dir and e.nombre.endswith(".md") and not e.nombre.startswith(".")] if io.es_dir(cdir / "agents") else []
        agentes.sort()
        reglas = [e.nombre for e in io.listar(cdir / "rules") if not e.es_dir and e.nombre.endswith(".md") and not e.nombre.startswith(".")] if io.es_dir(cdir / "rules") else []
        reglas.sort()
        comandos = [e.ruta.stem for e in io.listar(cdir / "commands") if not e.es_dir and e.nombre.endswith(".md") and not e.nombre.startswith(".")] if io.es_dir(cdir / "commands") else []
        comandos.sort()
        hooks: List[Dict[str, Any]] = []
        for nom in ("settings.json", "settings.local.json"):
            d = io.leer_json(cdir / nom)
            if isinstance(d, dict) and d.get("hooks"):
                hooks += hooks_desde_cfg(d.get("hooks"), f"{rel}/.claude/{nom}")
        pares: List[Tuple[str, int]] = []
        for s in skills:
            t_bytes = io.tamano(cdir / "skills" / s / "SKILL.md")
            pares.append((f"s:{s}", t_bytes if t_bytes is not None else 0))
        for a in agentes:
            t_bytes = io.tamano(cdir / "agents" / f"{a}.md")
            pares.append((f"a:{a}", t_bytes if t_bytes is not None else 0))
        for r in reglas:
            t_bytes = io.tamano(cdir / "rules" / r)
            pares.append((f"r:{r}", t_bytes if t_bytes is not None else 0))
        hooks_dir = cdir / "hooks"
        n_hooks_archivos = sum(1 for e in io.listar(hooks_dir) if not e.es_dir and not e.nombre.startswith(".")) if io.es_dir(hooks_dir) else 0
        en_comun = len(set(skills) & (skills_personales or set()))
        claude_md = proyecto / "CLAUDE.md"
        info_md = {}
        if io.es_archivo(claude_md):
            txt = io.leer_texto(claude_md)
            if txt is not None:
                info_md = {"bytes": io.tamano(claude_md) or 0, "lineas": txt.count("\n") + 1}
        items.append({
            "ruta": rel,
            "es_checkout_git": io.existe(proyecto / ".git"),
            "skills": skills,
            "agentes": agentes,
            "reglas": reglas,
            "comandos": comandos,
            "hooks": len(hooks),
            "hooks_eventos": sorted({h["evento"] for h in hooks}),
            "hooks_archivos": n_hooks_archivos,
            "skills_en_comun_con_personales": en_comun,
            "parece_copia_del_ecosistema": bool(skills) and len(skills) >= 20 and en_comun >= 0.5 * len(skills),
            "tiene_settings": io.es_archivo(cdir / "settings.json"),
            "tiene_settings_local": io.es_archivo(cdir / "settings.local.json"),
            "tiene_mcp_json": io.es_archivo(proyecto / ".mcp.json"),
            "claude_md": info_md,
            "huella": _huella_nombres(pares) if pares else "",
        })
    return items


def inventariar_carpetas(io: IO, raiz: Union[str, Path]) -> List[Dict[str, Any]]:
    """
    Inventaria las carpetas de proyecto (cajas) bajo ~/Proyectos.
    Devuelve lista de diccionarios ordenada por ruta (sin distinguir mayúsculas) con:
    ruta, ruta_tilde, nombre, grupo, area, nivel, tipo, es_checkout_git, tiene_claude_md, tiene_claude.
    Todo acceso al disco pasa por io.
    """
    raiz_path = io.expandir_ruta(raiz) if hasattr(io, "expandir_ruta") else Path(raiz)
    if not io.es_dir(raiz_path) or io.es_symlink(raiz_path):
        return []

    cajas_nivel1: List[Path] = []
    for e1 in io.listar(raiz_path):
        if e1.nombre.startswith((".", "_")):
            continue
        if io.es_symlink(e1.ruta) or not e1.es_dir:
            continue
        cajas_nivel1.append(e1.ruta)

    arbol: Dict[Path, Dict[Path, List[Path]]] = {}
    for c1 in cajas_nivel1:
        arbol[c1] = {}
        for e2 in io.listar(c1):
            if e2.nombre.startswith((".", "_")):
                continue
            if io.es_symlink(e2.ruta) or not e2.es_dir:
                continue
            if not (io.existe(e2.ruta / ".git") or io.es_archivo(e2.ruta / "CLAUDE.md")):
                continue
            c2 = e2.ruta
            arbol[c1][c2] = []
            for e3 in io.listar(c2):
                if e3.nombre.startswith((".", "_")):
                    continue
                if io.es_symlink(e3.ruta) or not e3.es_dir:
                    continue
                if io.existe(e3.ruta / ".git") or io.es_archivo(e3.ruta / "CLAUDE.md"):
                    arbol[c1][c2].append(e3.ruta)

    cajas_archivo: List[Path] = []
    p_archivo = raiz_path / "_archivo"
    if io.es_dir(p_archivo) and not io.es_symlink(p_archivo):
        for ea in io.listar(p_archivo):
            if ea.nombre.startswith((".", "_")):
                continue
            if io.es_symlink(ea.ruta) or not ea.es_dir:
                continue
            cajas_archivo.append(ea.ruta)

    items: List[Dict[str, Any]] = []

    def armar_ficha(
        p: Path,
        rel: str,
        nivel_arbol: int,
        tiene_cajas: bool,
        es_archivo: bool,
    ) -> Dict[str, Any]:
        nombre = p.name.replace("-", " ").replace("_", " ")
        partes = rel.split("/")
        if es_archivo or rel.startswith("_archivo/"):
            grupo = "Archivo"
            tipo = "archivo"
        elif rel.startswith("Personal/"):
            grupo = "Personal"
            tipo = "dormido"
        else:
            grupo = partes[0].replace("-", " ").replace("_", " ")
            tipo = "activo"

        area = partes[1].replace("-", " ").replace("_", " ") if len(partes) == 3 else ""

        if tiene_cajas:
            nivel = "empresa" if nivel_arbol == 1 else "area"
        else:
            nivel = "proyecto"

        return {
            "ruta": rel,
            "ruta_tilde": io.con_tilde(p).replace("\\", "/"),   # siempre con «/» (también en Windows)
            "nombre": nombre,
            "grupo": grupo,
            "area": area,
            "nivel": nivel,
            "tipo": tipo,
            "es_checkout_git": bool(io.existe(p / ".git")),
            "tiene_claude_md": bool(io.es_archivo(p / "CLAUDE.md")),
            "tiene_claude": bool(io.es_dir(p / ".claude")),
        }

    for c1, subcajas in arbol.items():
        tiene_cajas_c1 = bool(subcajas)
        rel1 = c1.name
        items.append(armar_ficha(c1, rel1, nivel_arbol=1, tiene_cajas=tiene_cajas_c1, es_archivo=False))

        for c2, subcajas3 in subcajas.items():
            tiene_cajas_c2 = bool(subcajas3)
            rel2 = f"{c1.name}/{c2.name}"
            items.append(armar_ficha(c2, rel2, nivel_arbol=2, tiene_cajas=tiene_cajas_c2, es_archivo=False))

            for c3 in subcajas3:
                rel3 = f"{c1.name}/{c2.name}/{c3.name}"
                items.append(armar_ficha(c3, rel3, nivel_arbol=3, tiene_cajas=False, es_archivo=False))

    for ca in cajas_archivo:
        rel_a = f"_archivo/{ca.name}"
        items.append(armar_ficha(ca, rel_a, nivel_arbol=2, tiene_cajas=False, es_archivo=True))

    items.sort(key=lambda x: x["ruta"].lower())
    return items


def inventariar_claude_md(io: IO) -> Dict[str, Any]:
    """Tamaño (bytes y líneas) del CLAUDE.md global y sus importados."""
    res: Dict[str, Any] = {}
    for nombre in ("CLAUDE.md", "CLAUDE-omc.md"):
        p = io.claude_dir / nombre
        if io.es_archivo(p):
            txt = io.leer_texto(p)
            if txt is not None:
                res[nombre] = {"bytes": io.tamano(p) or 0, "lineas": txt.count("\n") + 1}
    return res


def inventariar_memoria(io: IO) -> Dict[str, Any]:
    """
    Memoria automática por proyecto: ~/.claude/projects/<proyecto>/memory/*.md.
    SOLO conteos (la memoria es privada y no viaja a la nube). Las carpetas temporales
    (/private/tmp, scratch de pruebas) se cuentan aparte.
    """
    base = io.claude_dir / "projects"
    por_proyecto: Dict[str, int] = {}
    efimeros = 0
    if io.es_dir(base):
        for e_proy in io.listar(base):
            if not e_proy.es_dir:
                continue
            mem = e_proy.ruta / "memory"
            if not io.es_dir(mem):
                continue
            n = sum(1 for f in io.listar(mem) if not f.es_dir and f.nombre.endswith(".md") and f.nombre != "MEMORY.md")
            if n == 0:
                continue
            es_tmp = e_proy.nombre.startswith(("-private-", "-tmp-")) or "scratch" in e_proy.nombre
            if es_tmp:
                efimeros += n
            else:
                por_proyecto[e_proy.nombre] = n
    return {
        "entradas_por_proyecto": por_proyecto,
        "total_entradas": sum(por_proyecto.values()),
        "entradas_en_carpetas_efimeras": efimeros,
    }


def inventariar_rutinas(io: IO) -> Dict[str, Any]:
    """Rutinas registradas en ~/.cerebro/rutinas-fuentes.json: solo conteos de claves."""
    d = io.leer_json(io.home / ".cerebro" / "rutinas-fuentes.json")
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


def _rutas_declaradas(io: IO, ruta: Path, decl: Any) -> List[Path]:
    """Convierte una declaración de plugin.json (texto o lista) en rutas dentro del plugin."""
    salida: List[Path] = []
    ruta_real = io.real(ruta)
    for e in lista_str(decl):
        p = io.real(ruta / e)
        try:
            p.relative_to(ruta_real)
        except ValueError:
            continue
        salida.append(p)
    return salida


def componentes_de_plugin(io: IO, ruta: Path, nombre_plugin: str, cargado: bool, fuente: str) -> Dict[str, Any]:
    """
    Lee los componentes REALES de un plugin tal como Claude Code los carga:
      - skills:   plugin.json "skills" (lista de carpetas o carpeta) o, por defecto, skills/*/SKILL.md
      - agentes:  plugin.json "agents" (lista de .md) o, por defecto, agents/*.md.
                  Los .md sueltos en la raíz que NO están declarados se anotan aparte.
      - comandos: plugin.json "commands" o, por defecto, commands/*.md
      - hooks:    plugin.json "hooks" (inline o ruta) o hooks/hooks.json
      - mcp:      .mcp.json o plugin.json "mcpServers"
    """
    pj = io.leer_json(ruta / ".claude-plugin" / "plugin.json")
    if not isinstance(pj, dict):
        pj = io.leer_json(ruta / "plugin.json")
    if not isinstance(pj, dict):
        pj = {}
    nombre_plugin = str(pj.get("name") or nombre_plugin)

    # ---- skills ----
    skills: List[Dict[str, Any]] = []
    carpetas_skill: List[Path] = []
    if "skills" in pj and pj["skills"]:
        for p in _rutas_declaradas(io, ruta, pj["skills"]):
            if io.es_archivo(p / "SKILL.md"):
                carpetas_skill.append(p)
            else:
                carpetas_skill.extend(skills_en_dir(io, p))
    else:
        carpetas_skill = skills_en_dir(io, ruta / "skills")
    vistos: Set[str] = set()
    for c in carpetas_skill:
        if str(c) in vistos:
            continue
        vistos.add(str(c))
        f = ficha_md(io, c / "SKILL.md", c.name)
        item = {
            "plugin": nombre_plugin, "fuente": fuente, "cargado": cargado,
            "nombre": f["nombre"], "invocacion": f"{nombre_plugin}:{f['nombre']}",
            "descripcion": f["descripcion"], "descripcion_bytes": f["descripcion_bytes"],
            "tamano_bytes": f["tamano_bytes"], "cantidad_archivos": io.contar_archivos(c),
            "precargada_por": [],
        }
        item.update(campos_uso_vacios())
        skills.append(item)
    # SKILL.md que existen en el plugin pero que Claude Code no carga (anidados)
    skills_en_disco = 0
    try:
        for _r, ds, fs in io.caminar(ruta):
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
        for p in _rutas_declaradas(io, ruta, pj["agents"]):
            if io.es_archivo(p):
                archivos_agente.append(p)
            elif io.es_dir(p):
                for e in io.listar(p):
                    if not e.es_dir and e.nombre.endswith(".md"):
                        archivos_agente.append(e.ruta)
    else:
        d = ruta / "agents"
        if io.es_dir(d):
            archivos_agente = [e.ruta for e in io.listar(d) if not e.es_dir and e.nombre.endswith(".md") and not e.nombre.startswith(".")]
    agentes: List[Dict[str, Any]] = []
    for a in archivos_agente:
        f = ficha_md(io, a, a.stem)
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
    usados = {io.real(a) for a in archivos_agente}
    sueltos_no_declarados: List[str] = []
    for e in io.listar(ruta):
        if e.es_dir or not e.nombre.endswith(".md"):
            continue
        md = e.ruta
        if md.name.upper() in ("README.MD", "CHANGELOG.MD", "CLAUDE.MD", "AGENTS.MD", "LICENSE.MD", "CONTRIBUTING.MD",
                               "CONNECTORS.MD", "ACCESS.MD", "CONTEXT.MD", "REQUISITOS.MD", "PLUGIN_SETTINGS.MD",
                               "SECURITY.MD", "THIRDPARTYNOTICES.MD") or md.name.startswith("README"):
            continue
        if io.real(md) in usados:
            continue
        try:
            txt = io.leer_texto(md)
            if txt and parse_yaml_frontmatter(txt).get("name"):
                sueltos_no_declarados.append(md.name)
        except Exception:
            pass

    # ---- comandos ----
    archivos_cmd: List[Path] = []
    if "commands" in pj and pj["commands"]:
        for p in _rutas_declaradas(io, ruta, pj["commands"]):
            if io.es_archivo(p):
                archivos_cmd.append(p)
            elif io.es_dir(p):
                for e in io.listar(p):
                    if not e.es_dir and e.nombre.endswith(".md") and not e.nombre.startswith("."):
                        archivos_cmd.append(e.ruta)
    else:
        d = ruta / "commands"
        if io.es_dir(d):
            archivos_cmd = [e.ruta for e in io.listar(d) if not e.es_dir and e.nombre.endswith(".md") and not e.nombre.startswith(".")]
    comandos: List[Dict[str, Any]] = []
    vistos_cmd: Set[str] = set()
    for c in archivos_cmd:
        if c.stem in vistos_cmd:
            continue
        vistos_cmd.add(c.stem)
        f = ficha_md(io, c, c.stem)
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
        candidatos = _rutas_declaradas(io, ruta, decl_hooks) if decl_hooks else []
        candidatos += [ruta / "hooks" / "hooks.json", ruta / "hooks.json"]
        for h in candidatos:
            if io.es_archivo(h):
                cfg = io.leer_json(h)
                if cfg:
                    hooks = hooks_desde_cfg(cfg, nombre_plugin)
                    break
    for h in hooks:
        h["plugin"] = nombre_plugin
        h["cargado"] = cargado
    modulos: List[str] = []
    for cand in [ruta / "hooks" / "hooks.json", ruta / "hooks.json"]:
        if io.es_archivo(cand):
            modulos = modulos_desde_cfg(io.leer_json(cand))
            if modulos:
                break

    # ---- MCP ----
    srv: List[str] = []
    mj = pj.get("mcpServers")
    if isinstance(mj, dict):
        srv = nombres_mcp({"mcpServers": mj})
    else:
        for cand in _rutas_declaradas(io, ruta, mj) + [ruta / ".mcp.json"]:
            if io.es_archivo(cand):
                srv = nombres_mcp(io.leer_json(cand))
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


def inventariar_plugins(io: IO, habilitados: Dict[str, bool]) -> Dict[str, Any]:
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
    data = io.leer_json(io.claude_dir / "plugins" / "installed_plugins.json")
    plugins_dict: Dict[str, Any] = {}
    if isinstance(data, dict) and isinstance(data.get("plugins"), dict):
        plugins_dict = data["plugins"]
    rutas_instaladas: Set[str] = set()
    for clave, install_val in plugins_dict.items():
        nombre, marketplace = (clave.rsplit("@", 1) + [""])[:2] if "@" in clave else (clave, "")
        lst = install_val if isinstance(install_val, list) else [install_val]
        inst = next((i for i in lst if isinstance(i, dict) and i.get("installPath")), lst[0] if lst and isinstance(lst[0], dict) else {})
        ruta_str = str(inst.get("installPath") or "")
        ruta = io.real(io.expandir_ruta(ruta_str)) if ruta_str else None
        existe = bool(ruta and io.es_dir(ruta))
        cargado = bool(habilitados.get(clave))
        if existe and ruta is not None:
            rutas_instaladas.add(str(ruta))
        comp = componentes_de_plugin(io, ruta, nombre, cargado, "instalado") if existe and ruta is not None else {
            "version_declarada": "", "nombre_declarado": "", "nombre_efectivo": nombre, "skills": [], "agentes": [], "comandos": [], "hooks": [],
            "mcp": [], "modulos": [], "skills_en_disco": 0, "agentes_sueltos_no_declarados": []}
        meta = {
            "nombre": nombre, "nombre_en_claude": comp["nombre_efectivo"], "marketplace": marketplace, "clave": clave,
            "fuente": "instalado", "version": str(inst.get("version") or ""),
            "habilitado": cargado, "cargado": cargado,
            "ruta_existe": existe,
            # compat con la versión anterior del inventario:
            "ruta_instalacion": con_tilde(ruta, io.home),
        }
        agregar(meta, comp)

    # ---- sincronizados (claude.ai / Cowork) ----
    base = io.claude_dir / "plugins" / "synced"
    if io.es_dir(base):
        for e_cuenta in io.listar(base):
            if not e_cuenta.es_dir or e_cuenta.nombre.startswith("."):
                continue
            cuenta = e_cuenta.ruta
            manifiesto = io.leer_json(cuenta / "manifest.json") or {}
            por_nombre = {str(p.get("name")): p for p in manifiesto.get("plugins", []) if isinstance(p, dict)}
            for e_pdir in io.listar(cuenta):
                if not e_pdir.es_dir or e_pdir.nombre.startswith("."):
                    continue
                pdir = e_pdir.ruta
                pj = io.leer_json(pdir / ".claude-plugin" / "plugin.json") or io.leer_json(pdir / "plugin.json") or {}
                nombre_dir = re.sub(r"~g\d+$", "", e_pdir.nombre)
                nombre = str(pj.get("name") or nombre_dir) if isinstance(pj, dict) else nombre_dir
                mt = io.leer_json(cuenta / f"{e_pdir.nombre}.meta.json") or {}
                info = por_nombre.get(nombre) or por_nombre.get(nombre_dir) or {}
                comp = componentes_de_plugin(io, pdir, nombre, True, "sincronizado")
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
    cache = io.claude_dir / "plugins" / "cache"
    huerfanas = 0
    temporales = 0
    if io.es_dir(cache):
        for e_mkt in io.listar(cache):
            if e_mkt.nombre.startswith("temp_"):
                temporales += 1
                continue
            if not e_mkt.es_dir:
                continue
            for e_pl in io.listar(e_mkt.ruta):
                if not e_pl.es_dir:
                    continue
                for e_ver in io.listar(e_pl.ruta):
                    if e_ver.es_dir and str(io.real(e_ver.ruta)) not in rutas_instaladas:
                        huerfanas += 1
    out["cache"] = {"versiones_viejas_no_instaladas": huerfanas, "clones_temporales": temporales}
    return out


def inventariar_servidores_mcp(
    io: IO,
    plugins_mcp: List[Dict[str, Any]],
    ajustes: Dict[str, Any],
) -> Tuple[List[Dict[str, Any]], List[str]]:
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

    data = io.leer_json(io.home / ".mcp.json")
    if isinstance(data, dict) and isinstance(data.get("mcpServers"), dict):
        for n, v in data["mcpServers"].items():
            nuevo(str(n), "~/.mcp.json", not (isinstance(v, dict) and v.get("disabled") is True))
    sdata = io.leer_json(io.claude_dir / "settings.json")
    if isinstance(sdata, dict) and isinstance(sdata.get("mcpServers"), dict):
        for n, v in sdata["mcpServers"].items():
            nuevo(str(n), "settings.json", not (isinstance(v, dict) and v.get("disabled") is True))
    for m in plugins_mcp:
        nuevo(m["nombre"], f"plugin:{m['plugin']} ({m['fuente']})", bool(m["cargado"]), m["plugin"], m["id_en_uso"])

    # ~/.claude.json (alcance usuario y por proyecto) y config de Claude Desktop/Cowork: SOLO nombres
    cj_path = io.home / ".claude.json"
    for n in io.nombres_json(cj_path, ["mcpServers"], "mcp_servers_usuario"):
        nuevo(str(n), "~/.claude.json (usuario)", True)

    proyectos_claves = io.nombres_json(cj_path, ["projects"], "mcp_proyectos_claude_json")
    for ruta_p in proyectos_claves:
        srvs = io.nombres_json(cj_path, ["projects", ruta_p, "mcpServers"], f"proyectos.{ruta_p}.mcpServers")
        rel_p = str(ruta_p).replace(str(io.home) + "/Proyectos/", "") if "/Proyectos" in str(ruta_p) else Path(str(ruta_p)).name
        for n in srvs:
            nuevo(str(n), f"~/.claude.json (proyecto {rel_p})", True)

    dc_path = io.home / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    for n in io.nombres_json(dc_path, ["mcpServers"], "claude_desktop:mcpServers"):
        nuevo(str(n), "claude_desktop_config.json (Desktop/Cowork)", True)

    # .mcp.json de proyectos
    raiz = io.home / "Proyectos"
    proyectos_mcp: List[str] = []
    if io.es_dir(raiz):
        prof = len(raiz.parts)
        for actual, dirs, files in io.caminar(raiz):
            podar_recorrido_proyectos_mcp(actual, dirs, prof)
            if ".mcp.json" in files:
                rel = Path(actual).relative_to(raiz).as_posix()
                for n in nombres_mcp(io.leer_json(Path(actual) / ".mcp.json")):
                    nuevo(n, f"proyecto:{rel}/.mcp.json", True)
                    proyectos_mcp.append(f"{rel}:{n}")

    # servidores que settings.local.json habilita pero que no están definidos en ninguna parte del disco
    conocidos = {s["nombre"] for s in servidores}
    sin_definicion = sorted(n for n in habil_local if n not in conocidos)
    return servidores, sin_definicion


# ==============================================================================
# 3. CRUCE MECÁNICO (INVENTARIO + USO REAL)
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
# 4. RESUMEN Y GENERACIÓN DE REPORTES (JSON Y MARKDOWN)
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
    escribir_json(ruta_archivo, datos)


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

    escribir_texto(ruta_archivo, "\n".join(L))


# ==============================================================================
# 5. FUNCIONES PÚBLICAS Y EJECUCIÓN PRINCIPAL
# ==============================================================================

def leer_disco(io: IO, proyectos_dir: Union[str, Path]) -> Dict[str, Any]:
    """
    Recorre el disco e inventaria el ecosistema de Claude Code usando IO.
    Devuelve la estructura de inventario previa a la medición de uso real,
    incluyendo 'arranque' y 'resumen', sin 'generado_en' ni 'metricas_ejecucion'.
    """
    claude_dir = io.claude_dir
    settings = io.leer_json(claude_dir / "settings.json") or {}
    en_plugins = settings.get("enabledPlugins") if isinstance(settings, dict) else {}
    habilitados = {str(k): bool(v) for k, v in en_plugins.items()} if isinstance(en_plugins, dict) else {}
    marketplaces: List[str] = []
    extra_m = settings.get("extraKnownMarketplaces") if isinstance(settings, dict) else None
    if isinstance(extra_m, dict):
        marketplaces = sorted(str(k) for k in extra_m.keys())
    # solo los NOMBRES de los marketplaces (el archivo trae fechas de actualización que cambian solas)
    marketplaces_conocidos = sorted(io.nombres_json(claude_dir / "plugins" / "known_marketplaces.json", [], "claude:marketplaces_conocidos"))

    skills_personales = inventariar_skills_personales(io)
    agentes = inventariar_agentes(io)
    pl = inventariar_plugins(io, habilitados)
    skills_plugin = pl["skills_plugin"] + inventariar_skills_sincronizadas(io)
    hooks = inventariar_hooks(io)
    ajustes = inventariar_ajustes(io)
    servidores_mcp, mcp_sin_definicion = inventariar_servidores_mcp(io, pl["mcp_plugin"], ajustes)
    mods = inventariar_mods(io)
    hooks_mods: List[Dict[str, Any]] = []
    for md in mods:
        hk = io.leer_json(claude_dir / "mods" / md["nombre"] / "hooks" / "hooks.json")
        hooks_mods += hooks_desde_cfg(hk, f"mod:{md['nombre']}") if hk else []

    inv: Dict[str, Any] = {
        "directorio_claude": con_tilde(claude_dir, io.home),
        "skills_personales": skills_personales,
        "agentes": agentes,
        "plugins": pl["plugins"],
        "skills_plugin": skills_plugin,
        "agentes_plugin": pl["agentes_plugin"],
        "comandos_plugin": pl["comandos_plugin"],
        "hooks": hooks,
        "hooks_plugin": pl["hooks_plugin"],
        "hooks_mods": hooks_mods,
        "hooks_dir": inventariar_hooks_dir(io, hooks),
        "servidores_mcp": servidores_mcp,
        "mcp_habilitados_sin_definicion_en_disco": mcp_sin_definicion,
        "plugins_habilitados_settings": [{"nombre": k, "habilitado": v} for k, v in sorted(habilitados.items())],
        "marketplaces_conocidos": marketplaces_conocidos,
        "marketplaces_extra_settings": marketplaces,
        "cache_plugins": pl["cache"],
        "mods": mods,
        "tareas_programadas": inventariar_tareas_programadas(io),
        "scripts": inventariar_scripts(io),
        "permisos": inventariar_permisos(io),
        "ajustes": ajustes,
        "otros": inventariar_recetas_y_otros(io),
        "archivo": inventariar_archivo(io),
        "claude_md_global": inventariar_claude_md(io),
        "proyectos": inventariar_proyectos(io, proyectos_dir,
                                           {sk["nombre"] for sk in skills_personales} | {sk["carpeta"] for sk in skills_personales}),
        "carpetas": inventariar_carpetas(io, proyectos_dir),
        "memoria": inventariar_memoria(io),
        "rutinas_registradas": inventariar_rutinas(io),
    }
    inv["arranque"] = [h for h in hooks if h["evento"] == "SessionStart"] + \
                      [h for h in inv["hooks_plugin"] if h["evento"] == "SessionStart" and h["cargado"]] + \
                      [h for h in hooks_mods if h["evento"] == "SessionStart"]
    inv["resumen"] = armar_resumen(inv)
    return inv


def cerrar(
    inv_disco: Dict[str, Any],
    stats: Dict[str, Any],
    metricas: Dict[str, Any],
    contador: Dict[str, Any],
    io: IO,
) -> Dict[str, Any]:
    """
    Cruza el inventario de disco con las estadísticas de uso real, sin mutar inv_disco.
    Devuelve `inv` completo con 'generado_en' y 'metricas_ejecucion'.
    """
    inv = copy.deepcopy(inv_disco)
    metricas_out = copy.deepcopy(metricas)

    # 1. Cruce mecánico
    uso_sin = realizar_cruce_general(inv, stats)
    inv["uso_real"] = mapa_uso.serializar_uso(stats)
    inv["uso_sin_inventario"] = uso_sin
    inv["contador_interno_skills"] = contador

    for it in inv["skills_personales"]:
        it["contador_interno_claude"] = contador.get(it["nombre"])
    for it in inv["skills_plugin"]:
        it["contador_interno_claude"] = contador.get(it["invocacion"])

    # 2. Totales de uso que dependen del cruce
    def por_origen(items: List[Dict[str, Any]]) -> Dict[str, int]:
        c: Dict[str, int] = {}
        for it in items:
            c[it["origen_uso"]] = c.get(it["origen_uso"], 0) + 1
        return dict(sorted(c.items()))

    inv["resumen"]["skills_cargadas_por_origen_de_uso"] = por_origen(inv["skills_personales"] + [s for s in inv["skills_plugin"] if s["cargado"]])
    inv["resumen"]["agentes_cargados_por_origen_de_uso"] = por_origen(inv["agentes"] + [a for a in inv["agentes_plugin"] if a["cargado"]])
    inv["resumen"]["skills_cargadas_nunca_usadas"] = (
        sum(1 for s in inv["skills_personales"] if s["nunca_usado"]) +
        sum(1 for s in inv["skills_plugin"] if s["cargado"] and s["nunca_usado"])
    )
    inv["resumen"]["agentes_cargados_nunca_usados"] = (
        sum(1 for a in inv["agentes"] if a["nunca_usado"]) +
        sum(1 for a in inv["agentes_plugin"] if a["cargado"] and a["nunca_usado"])
    )

    # 3. Depuración de nombres de clientes y claves sensibles
    contador_depurados = [0]
    inv = depurar_clientes(inv, cargar_patron_clientes(io), contador_depurados)
    inv = tapar_claves(inv)
    metricas_out["textos_depurados_de_nombres_de_clientes"] = contador_depurados[0]

    inv["generado_en"] = datetime.now(timezone.utc).isoformat()
    inv["metricas_ejecucion"] = metricas_out
    return inv


def main():
    parser = argparse.ArgumentParser(
        description="Inventario mecánico y medición de uso del ecosistema Claude Code (~/.claude)."
    )
    parser.add_argument("--out", type=str, default="./inventario_resultado",
                        help="Carpeta de destino para inventario.json e inventario.md.")
    parser.add_argument("--solo-disco", action="store_true",
                        help="Omitir el análisis de conversaciones .jsonl para ejecución rápida.")
    parser.add_argument("--claude-dir", type=str, default=None,
                        help="Ruta base del directorio de Claude (default: ~/.claude).")
    parser.add_argument("--proyectos-dir", type=str, default=None,
                        help="Carpeta de proyectos donde buscar .claude de proyecto (default: ~/Proyectos).")
    args = parser.parse_args()

    io = io_por_defecto(args.claude_dir)
    proyectos_dir = io.expandir_ruta(args.proyectos_dir) if args.proyectos_dir else io.home / "Proyectos"
    out_dir = io.expandir_ruta(args.out)
    crear_directorio(out_dir)

    # 1. Recolección de disco
    inv_disco = leer_disco(io, proyectos_dir)

    # 2. Medición de uso real
    if not args.solo_disco:
        stats, metricas, contador = mapa_uso.medir(io.claude_dir, io.home)
    else:
        stats = {c: {} for c in CATEGORIAS_USO}
        metricas = {
            "archivos_jsonl_leidos": 0, "archivos_principales": 0, "archivos_subagentes": 0,
            "lineas_leidas": 0, "lineas_no_parseadas": 0, "solo_disco": True
        }
        contador = mapa_uso.leer_contador_interno_skills(io.home)

    metricas["solo_disco"] = args.solo_disco

    # 3. Cierre y cruce mecánico
    inv = cerrar(inv_disco, stats, metricas, contador, io)

    # 4. Salida
    json_salida = out_dir / "inventario.json"
    md_salida = out_dir / "inventario.md"
    ordenado = {k: inv[k] for k in sorted(inv.keys(), key=lambda x: (x not in ("generado_en", "directorio_claude", "metricas_ejecucion", "resumen"), x))}
    generar_reporte_json(ordenado, json_salida)
    generar_reporte_markdown(inv, md_salida)

    r = inv["resumen"]
    m = inv["metricas_ejecucion"]
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
    print(f"Conversaciones .jsonl     : {m['archivos_jsonl_leidos']} ({m['archivos_principales']} principales + {m['archivos_subagentes']} subagentes)")
    print(f"Líneas leídas / sin parsear: {m['lineas_leidas']} / {m['lineas_no_parseadas']}")
    print("=" * 66)
    print(f"Archivos generados en '{out_dir}': {json_salida.name}, {md_salida.name}")


if __name__ == "__main__":
    main()
