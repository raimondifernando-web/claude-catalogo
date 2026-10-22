#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mapa.py - Único lector del mapa de arneses (skills, agentes, comandos, hooks, reglas, MCP, etc.) de Claude Code.
Disparador: encadenado — lo llaman herramientas-para, la tarea diaria del mapa y las sesiones que necesitan saber qué piezas hay (por intención: «¿qué hay para …?»).

El mapa se construye bajo demanda (on-demand) cuando alguien lo consulta, comparando
la huella guardada contra el disco en ~0,1 s y reconstruyendo solo si hubo cambios.

Uso:
  mapa [resumen]                                Imprime MAPA.md y estado calculado al momento
  mapa buscar <tema...>                         Busca hasta 25 piezas que coincidan con el tema
  mapa ver <pieza>                              Muestra la ficha completa de una pieza
  mapa sin-registrar [--catalogo RUTA]          Cruza piezas locales con el catálogo compartido
  mapa --al-dia (o mapa al-dia)                 Verifica si el mapa en disco está actualizado
  mapa --json                                   Emite mapa.json completo por stdout para programas
  mapa actualizar [--con-uso] [--out DIR]       Fuerza reconstrucción del mapa y opcionalmente mide uso

Python 3.9 estándar, sin librerías externas.
"""

import argparse
import copy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
from typing import Any, Dict, List, Optional, Set, Tuple, Union
import unicodedata

# Importación de módulos hermanos en el mismo directorio
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from mapa_io import IO, Registro, cambios, crear_directorio
import mapa_lector
import mapa_uso

try:
    import fcntl
    TIENE_FCNTL = True
except ImportError:
    fcntl = None
    TIENE_FCNTL = False


# ==============================================================================
# CANDADO Y ESCRITURA ATÓMICA
# ==============================================================================

class CandadoMapa:
    """
    Candado de exclusión mutua para reconstruir el mapa.
    Intenta fcntl.flock exclusivo con reintentos cada 100 ms hasta 30 s de tope.
    Si no hay fcntl, usa mkdir atómico con vencimiento de 60 s.
    Pasado el tope de 30 s, continúa sin candado (nunca se cuelga).
    """

    def __init__(self, mapa_dir: Path, tope_segundos: float = 30.0):
        self.mapa_dir = Path(mapa_dir)
        self.archivo_candado = self.mapa_dir / "candado"
        self.dir_candado = self.mapa_dir / "candado.lockdir"
        self.tope = tope_segundos
        self.fd: Optional[int] = None
        self.adquirido_flock = False
        self.adquirido_mkdir = False

    def adquirir(self) -> bool:
        inicio = time.time()
        os.makedirs(self.mapa_dir, mode=0o700, exist_ok=True)

        if TIENE_FCNTL:
            try:
                self.fd = os.open(str(self.archivo_candado), os.O_CREAT | os.O_RDWR, 0o600)
            except OSError:
                self.fd = None

            if self.fd is not None:
                while True:
                    try:
                        fcntl.flock(self.fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                        self.adquirido_flock = True
                        return True
                    except (BlockingIOError, OSError):
                        if (time.time() - inicio) >= self.tope:
                            return False
                        time.sleep(0.1)

        # Fallback sin fcntl: mkdir atómico
        while True:
            try:
                os.mkdir(str(self.dir_candado))
                self.adquirido_mkdir = True
                return True
            except FileExistsError:
                try:
                    mtime = os.stat(str(self.dir_candado)).st_mtime
                    if (time.time() - mtime) > 60.0:
                        try:
                            os.rmdir(str(self.dir_candado))
                            continue
                        except OSError:
                            pass
                except OSError:
                    pass

                if (time.time() - inicio) >= self.tope:
                    return False
                time.sleep(0.1)
            except OSError:
                if (time.time() - inicio) >= self.tope:
                    return False
                time.sleep(0.1)

    def liberar(self) -> None:
        if self.adquirido_flock and self.fd is not None:
            try:
                if TIENE_FCNTL and fcntl is not None:
                    fcntl.flock(self.fd, fcntl.LOCK_UN)
            except OSError:
                pass
            try:
                os.close(self.fd)
            except OSError:
                pass
            self.fd = None
            self.adquirido_flock = False
        elif self.fd is not None:
            try:
                os.close(self.fd)
            except OSError:
                pass
            self.fd = None

        if self.adquirido_mkdir:
            try:
                os.rmdir(str(self.dir_candado))
            except OSError:
                pass
            self.adquirido_mkdir = False

    def __enter__(self):
        self.adquirir()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.liberar()



def _hora_local(iso: Optional[str]) -> str:
    """Fecha ISO (UTC) → «AAAA-MM-DD HH:MM» en la hora de esta computadora (para quien lee el mapa)."""
    if not iso:
        return "-"
    try:
        return datetime.fromisoformat(str(iso)).astimezone().strftime("%Y-%m-%d %H:%M")
    except Exception:
        return str(iso)[:16].replace("T", " ")


def escribir_archivo_atomico(ruta_destino: Path, contenido: Union[str, bytes]) -> None:
    """
    Escribe un archivo de forma atómica en ruta_destino usando un archivo temporal
    en la misma carpeta con permisos 0600 y os.replace.
    """
    directorio = ruta_destino.parent
    os.makedirs(directorio, mode=0o700, exist_ok=True)
    try:
        os.chmod(directorio, 0o700)
    except OSError:
        pass

    prefijo = f".tmp_{ruta_destino.name}_"
    fd, tmp_ruta_str = tempfile.mkstemp(prefix=prefijo, dir=str(directorio))
    tmp_path = Path(tmp_ruta_str)
    try:
        os.fchmod(fd, 0o600)
    except (AttributeError, OSError):
        try:
            os.chmod(tmp_path, 0o600)
        except OSError:
            pass

    try:
        with os.fdopen(fd, "wb") as f:
            if isinstance(contenido, str):
                f.write(contenido.encode("utf-8"))
            else:
                f.write(contenido)
            f.flush()
            try:
                os.fsync(f.fileno())
            except OSError:
                pass
        # En Windows el reemplazo falla si otro proceso tiene el destino abierto un instante: se reintenta.
        for intento in range(6):
            try:
                os.replace(tmp_path, ruta_destino)
                break
            except PermissionError:
                if intento == 5:
                    raise
                time.sleep(0.05)
    except Exception:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
        raise


def escribir_json_atomico(ruta_destino: Path, datos: Any) -> None:
    """Serializa y escribe JSON de forma atómica con permisos 0600."""
    contenido = json.dumps(datos, ensure_ascii=False, indent=1)
    escribir_archivo_atomico(ruta_destino, contenido)


# ==============================================================================
# GESTIÓN DE VIGILANCIA Y RECONSTRUCCIÓN
# ==============================================================================

def leer_vigilancia(mapa_dir: Path) -> Optional[Dict[str, Any]]:
    """Lee y valida vigilancia.json. Devuelve None si falta, está corrupto o version != 1."""
    ruta = mapa_dir / "vigilancia.json"
    if not ruta.is_file():
        return None
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            datos = json.load(f)
        if isinstance(datos, dict) and datos.get("version") == 1 and "registro" in datos:
            return datos
        return None
    except Exception:
        return None


def obtener_registro_de_vigilancia(vig: Dict[str, Any]) -> Registro:
    """Reconstruye la instancia Registro a partir del dict guardado en vigilancia.json."""
    reg_dict = vig.get("registro", {})
    return Registro(
        arch=reg_dict.get("arch"),
        dirs=reg_dict.get("dirs"),
        contenido=reg_dict.get("contenido"),
    )


def armar_mapa_md(inv: Dict[str, Any], huella: str) -> str:
    """
    Construye el contenido de MAPA.md (índice corto, <= 4096 bytes).
    Primera línea: # Mapa de arneses · huella <hex> · generado <AAAA-MM-DD HH:MM>
    Segunda línea: instrucción fija.
    Luego: conteo por tipo y últimos 10 cambiados.
    """
    r = inv.get("resumen", {})
    gen_iso = inv.get("generado_en") or datetime.now(timezone.utc).isoformat()
    fecha_fmt = _hora_local(gen_iso)

    lineas = [
        f"# Mapa de arneses · huella {huella} · generado {fecha_fmt}",
        "Se consulta con `mapa` (buscar, ver, sin-registrar, --al-dia). No se abre este archivo a mano ni se rehace a mano.",
        "",
        "## Conteo por tipo",
        f"- Skills personales: {r.get('total_skills_personales', 0)}",
        f"- Skills de plugins cargadas: {r.get('skills_plugin_cargadas', 0)}",
        f"- Agentes: {r.get('total_agentes', 0)}",
        f"- Agentes de plugins: {r.get('agentes_plugin_cargados', 0)}",
        f"- Comandos: {r.get('comandos_plugin_cargados', r.get('total_comandos_plugin', 0))}",
        f"- Hooks: {r.get('hooks_settings', 0) + r.get('hooks_plugin_cargados', 0)}",
        f"- Conectores MCP: {r.get('servidores_mcp_cargados', r.get('total_servidores_mcp', 0))}",
        f"- Scripts: {r.get('total_scripts', 0)}",
        f"- Reglas: {r.get('reglas_de_proyecto_total', 0) + len(inv.get('otros', {}).get('rules_globales', []))}",
        f"- Tareas programadas: {r.get('tareas_programadas', 0)}",
        f"- Plugins instalados: {r.get('plugins_instalados', 0)}",
        "",
        "## Últimos 10 cambiados",
    ]

    cambiados: List[Tuple[str, str, str]] = []
    for s in inv.get("skills_personales", []):
        f = s.get("fecha_modificacion")
        if f:
            cambiados.append(("skill personal", s.get("nombre", ""), f))
    for a in inv.get("agentes", []):
        f = a.get("fecha_modificacion")
        if f:
            cambiados.append(("agente", a.get("nombre", ""), f))
    for sc in inv.get("scripts", []):
        f = sc.get("fecha_modificacion")
        if f:
            cambiados.append(("script", sc.get("nombre", ""), f))
    for s in inv.get("skills_plugin", []):
        f = s.get("fecha_modificacion")
        if f:
            cambiados.append(("skill de plugin", s.get("invocacion", s.get("nombre", "")), f))
    for a in inv.get("agentes_plugin", []):
        f = a.get("fecha_modificacion")
        if f:
            cambiados.append(("agente de plugin", a.get("invocacion", a.get("nombre", "")), f))

    cambiados.sort(key=lambda x: str(x[2]), reverse=True)
    ultimos = cambiados[:10]

    if not ultimos:
        lineas.append("_Sin cambios registrados._")
    else:
        for tipo, nombre, f_str in ultimos:
            fecha_legible = _hora_local(f_str) if f_str else "-"
            lineas.append(f"- {tipo} · {nombre} · {fecha_legible}")

    lineas.append("")
    resultado = "\n".join(lineas)

    # Si se pasa de 4096 bytes, recortar la sección más larga (Últimos 10 cambiados)
    if len(resultado.encode("utf-8")) > 4096:
        while len(resultado.encode("utf-8")) > 4096 and ultimos:
            ultimos.pop()
            lineas_recortadas = lineas[:15] + [
                f"- {t} · {n} · {(_hora_local(f) if f else '-')}" for t, n, f in ultimos
            ] + [""]
            resultado = "\n".join(lineas_recortadas)

    return resultado


def ejecutar_reconstruccion(
    claude_dir: Path,
    home: Path,
    proyectos_dir: Path,
    reconstrucciones: int,
    stats_uso: Optional[Dict[str, Any]] = None,
    metricas_uso: Optional[Dict[str, Any]] = None,
    contador_uso: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Reconstruye el mapa en el orden estricto de seguridad:
    1. IO nuevo con registro fresco
    2. mapa_lector.leer_disco
    3. cruzar con el uso guardado (o vacío)
    4. escribir mapa-disco.json (depurado: sin nombres de clientes ni claves), mapa.json y MAPA.md
    5. escribir vigilancia.json AL FINAL: es la marca de «terminé». Si el proceso muere antes, queda la huella
       vieja y la próxima consulta rehace (nunca queda una huella nueva con archivos viejos).
    """
    mapa_dir = claude_dir / "mapa"
    os.makedirs(mapa_dir, mode=0o700, exist_ok=True)
    io = IO(home=home, claude_dir=claude_dir)

    # 1. Leer disco
    inv_disco = mapa_lector.leer_disco(io, proyectos_dir)

    # 4. Obtener uso guardado (o argumentos pasados, o vacío)
    if stats_uso is None:
        ruta_uso = mapa_dir / "mapa-uso.json"
        if ruta_uso.is_file():
            try:
                with open(ruta_uso, "r", encoding="utf-8") as f:
                    uso_json = json.load(f)
                stats_uso, metricas_uso, contador_uso = mapa_uso.de_json(uso_json)
            except Exception:
                stats_uso = None

        if stats_uso is None:
            stats_uso = {c: {} for c in mapa_uso.CATEGORIAS_USO}
            metricas_uso = {
                "archivos_jsonl_leidos": 0, "archivos_principales": 0, "archivos_subagentes": 0,
                "lineas_leidas": 0, "lineas_no_parseadas": 0, "sin_medir": True
            }
            contador_uso = {}

    # 5. Cruzar con mapa_lector.cerrar (lee nombres-prohibidos.txt: queda en el registro)
    inv_completo = mapa_lector.cerrar(inv_disco, stats_uso, metricas_uso, contador_uso, io)

    # 6. Escribir los archivos del mapa; vigilancia.json va ÚLTIMO
    inv_disco_data = mapa_lector.tapar_claves(
        mapa_lector.depurar_clientes(copy.deepcopy(inv_disco), mapa_lector.cargar_patron_clientes(io), [0])
    )
    inv_disco_data["generado_en"] = datetime.now(timezone.utc).isoformat()
    escribir_json_atomico(mapa_dir / "mapa-disco.json", inv_disco_data)
    escribir_json_atomico(mapa_dir / "mapa.json", inv_completo)
    huella = hashlib.sha1(json.dumps(io.registro, sort_keys=True).encode("utf-8")).hexdigest()[:10]
    escribir_archivo_atomico(mapa_dir / "MAPA.md", armar_mapa_md(inv_completo, huella))
    vig_data = {
        "version": 1,
        "huella": huella,
        "generado_en": datetime.now(timezone.utc).isoformat(),
        "reconstrucciones": reconstrucciones,
        "registro": io.registro,
    }
    escribir_json_atomico(mapa_dir / "vigilancia.json", vig_data)

    return inv_completo


def asegurar_al_dia(claude_dir: Path, home: Path, proyectos_dir: Path) -> None:
    """
    Algoritmo asegurar_al_dia:
    1. Lee vigilancia.json; si falta o version != 1 -> reconstruir.
    2. cambios(registro, home). Lista vacía -> al día, devuelve sin hacer nada más.
    3. Toma candado (flock exclusivo, 30 s tope). Con candado tomado, doble chequeo.
    4. Reconstruye atómicamente; suma 1 al contador `reconstrucciones`.
    """
    mapa_dir = claude_dir / "mapa"
    vig = leer_vigilancia(mapa_dir)

    if vig is not None:
        reg = obtener_registro_de_vigilancia(vig)
        difs = cambios(reg, home)
        if not difs and (mapa_dir / "mapa.json").is_file() and (mapa_dir / "MAPA.md").is_file():
            return

    # Si hay que reconstruir: tomar el candado
    with CandadoMapa(mapa_dir):
        vig_candado = leer_vigilancia(mapa_dir)
        if vig_candado is not None:
            reg_candado = obtener_registro_de_vigilancia(vig_candado)
            difs_candado = cambios(reg_candado, home)
            if not difs_candado and (mapa_dir / "mapa.json").is_file() and (mapa_dir / "MAPA.md").is_file():
                return

        reconstrucciones_ant = (vig_candado or vig or {}).get("reconstrucciones", 0)
        reconstrucciones = reconstrucciones_ant + 1

        try:
            ejecutar_reconstruccion(
                claude_dir=claude_dir,
                home=home,
                proyectos_dir=proyectos_dir,
                reconstrucciones=reconstrucciones,
            )
        except Exception as e:
            sys.stderr.write(f"mapa: no pude rehacer: {e}\n")
            sys.exit(1)


# ==============================================================================
# SUBCOMANDOS
# ==============================================================================

PALABRAS_VACIAS = {
    "de", "la", "el", "los", "las", "un", "una", "unos", "unas",
    "para", "con", "por", "sin", "sobre", "entre", "tras", "hacia",
    "desde", "hasta", "del", "al", "que", "como", "cual", "cuales",
    "the", "and", "for", "with", "from", "that", "this", "these",
    "those", "into", "onto", "about",
}


def normalizar_texto(texto: str) -> str:
    """Normaliza texto a minúsculas y sin acentos diacríticos."""
    if not texto:
        return ""
    nfd = unicodedata.normalize("NFD", str(texto).lower())
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn")


def extraer_palabras_busqueda(tema: str) -> List[str]:
    """Partición en palabras de >= 3 letras ignorando palabras vacías."""
    norm = normalizar_texto(tema)
    tokens = re.findall(r"[a-z0-9_-]+", norm)
    palabras = [t for t in tokens if len(t) >= 3 and t not in PALABRAS_VACIAS]
    if not palabras and tokens:
        palabras = [t for t in tokens if t not in PALABRAS_VACIAS]
    return palabras


def comando_resumen(claude_dir: Path, home: Path, proyectos_dir: Path) -> None:
    """Subcomando resumen (por defecto): imprime MAPA.md y líneas dinámicas."""
    asegurar_al_dia(claude_dir, home, proyectos_dir)
    mapa_dir = claude_dir / "mapa"

    ruta_md = mapa_dir / "MAPA.md"
    if ruta_md.is_file():
        try:
            with open(ruta_md, "r", encoding="utf-8") as f:
                print(f.read().rstrip())
        except OSError:
            pass

    # Líneas calculadas en el momento:
    # 1. sin registrar: N (si aplica)
    catalogo_path = home / "Proyectos" / "Tech" / "claude-skills-shared" / "CATALOGO.yaml"
    if catalogo_path.is_file():
        sin_reg, _ = calcular_sin_registrar(claude_dir, home, catalogo_path)
        if sin_reg:
            print(f"sin registrar: {len(sin_reg)} (ver `mapa sin-registrar`)")

    # 2. uso medido el <fecha> o uso sin medir
    ruta_uso = mapa_dir / "mapa-uso.json"
    if ruta_uso.is_file():
        try:
            with open(ruta_uso, "r", encoding="utf-8") as f:
                uso_data = json.load(f)
            medido = uso_data.get("medido_en")
            if medido:
                print(f"uso medido el {_hora_local(medido)}")
            else:
                print("uso sin medir")
        except Exception:
            print("uso sin medir")
    else:
        print("uso sin medir")


def recolectar_piezas_para_busqueda(inv: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extrae todas las piezas buscables del inventario estructurado."""
    piezas: List[Dict[str, Any]] = []

    # 1. Skills personales
    for s in inv.get("skills_personales", []):
        piezas.append({
            "tipo": "skill personal",
            "nombre": s.get("nombre", ""),
            "descripcion": s.get("descripcion", ""),
            "donde_vive": f"~/.claude/skills/{s.get('carpeta', s.get('nombre', ''))}",
            "raw": s,
        })

    # 2. Skills de plugin cargadas
    for s in inv.get("skills_plugin", []):
        if s.get("cargado", True):
            piezas.append({
                "tipo": "skill de plugin",
                "nombre": s.get("invocacion", s.get("nombre", "")),
                "descripcion": s.get("descripcion", ""),
                "donde_vive": f"plugin:{s.get('plugin', '')}",
                "raw": s,
            })

    # 3. Agentes
    for a in inv.get("agentes", []):
        piezas.append({
            "tipo": "agente",
            "nombre": a.get("nombre", ""),
            "descripcion": a.get("descripcion", ""),
            "donde_vive": f"~/.claude/agents/{a.get('archivo', a.get('nombre', '') + '.md')}",
            "raw": a,
        })

    # 4. Agentes de plugin cargados
    for a in inv.get("agentes_plugin", []):
        if a.get("cargado", True):
            piezas.append({
                "tipo": "agente de plugin",
                "nombre": a.get("invocacion", a.get("nombre", "")),
                "descripcion": a.get("descripcion", ""),
                "donde_vive": f"plugin:{a.get('plugin', '')}",
                "raw": a,
            })

    # 5. Comandos de plugin cargados
    for c in inv.get("comandos_plugin", []):
        if c.get("cargado", True):
            piezas.append({
                "tipo": "comando",
                "nombre": c.get("comando", ""),
                "descripcion": c.get("descripcion", ""),
                "donde_vive": f"plugin:{c.get('plugin', '')}",
                "raw": c,
            })

    # 6. Servidores MCP
    for m in inv.get("servidores_mcp", []):
        piezas.append({
            "tipo": "servidor MCP",
            "nombre": m.get("nombre", ""),
            "descripcion": m.get("origen", ""),
            "donde_vive": m.get("origen", ""),
            "raw": m,
        })

    # 7. Scripts
    for sc in inv.get("scripts", []):
        piezas.append({
            "tipo": "script",
            "nombre": sc.get("nombre", ""),
            "descripcion": sc.get("comentario", ""),
            "donde_vive": f"~/.claude/scripts/{sc.get('nombre', '')}",
            "raw": sc,
        })

    # 8. Tareas programadas
    for tp in inv.get("tareas_programadas", []):
        piezas.append({
            "tipo": "tarea programada",
            "nombre": tp.get("nombre", ""),
            "descripcion": tp.get("descripcion", ""),
            "donde_vive": f"~/.claude/scheduled-tasks/{tp.get('carpeta', tp.get('nombre', ''))}",
            "raw": tp,
        })

    # 9. Recetas
    for r in inv.get("otros", {}).get("recetas", []):
        piezas.append({
            "tipo": "receta",
            "nombre": r,
            "descripcion": "",
            "donde_vive": f"~/.claude/recetas/{r}",
            "raw": {"nombre": r},
        })

    # 10. Reglas globales
    for r in inv.get("otros", {}).get("rules_globales", []):
        piezas.append({
            "tipo": "regla",
            "nombre": r,
            "descripcion": "",
            "donde_vive": f"~/.claude/rules/{r}",
            "raw": {"nombre": r},
        })

    # 11. Plugins instalados
    for p in inv.get("plugins", []):
        piezas.append({
            "tipo": "plugin",
            "nombre": p.get("nombre", ""),
            "descripcion": p.get("descripcion", ""),
            "donde_vive": p.get("fuente", "") + (f" · {p.get('marketplace')}" if p.get("marketplace") else ""),
            "raw": p,
        })

    return piezas


def comando_buscar(tema_lista: List[str], claude_dir: Path, home: Path, proyectos_dir: Path) -> None:
    """Subcomando buscar: lista hasta 25 piezas que coinciden con el tema."""
    asegurar_al_dia(claude_dir, home, proyectos_dir)
    tema = " ".join(tema_lista).strip()
    palabras = extraer_palabras_busqueda(tema)

    if not palabras:
        print(f'nada coincide con "{tema}"')
        sys.exit(0)

    ruta_mapa = claude_dir / "mapa" / "mapa.json"
    if not ruta_mapa.is_file():
        print(f'nada coincide con "{tema}"')
        sys.exit(0)

    try:
        with open(ruta_mapa, "r", encoding="utf-8") as f:
            inv = json.load(f)
    except Exception:
        print(f'nada coincide con "{tema}"')
        sys.exit(0)

    piezas = recolectar_piezas_para_busqueda(inv)
    coincidencias: List[Tuple[int, Dict[str, Any]]] = []

    for item in piezas:
        nombre_norm = normalizar_texto(item["nombre"])
        desc_norm = normalizar_texto(item["descripcion"])

        score = 0
        for p in palabras:
            if p in nombre_norm:
                score += 3
            if p in desc_norm:
                score += 1

        if score > 0:
            coincidencias.append((score, item))

    if not coincidencias:
        print(f'nada coincide con "{tema}"')
        sys.exit(0)

    coincidencias.sort(key=lambda x: (-x[0], x[1]["nombre"].lower()))
    coincidencias = coincidencias[:25]

    for _sc, item in coincidencias:
        tipo = item["tipo"]
        nombre = item["nombre"]
        desc = item["descripcion"]
        donde = item["donde_vive"]

        if desc:
            desc_limpia = desc.replace("\r", " ").replace("\n", " ").strip()
            if len(desc_limpia) > 110:
                desc_corta = desc_limpia[:107] + "..."
            else:
                desc_corta = desc_limpia
            print(f"{tipo} · {nombre} — {desc_corta} · {donde}")
        else:
            print(f"{tipo} · {nombre} — · {donde}")


def formatear_ficha_ver(tipo: str, item: Dict[str, Any]) -> str:
    """Formatea la ficha completa de una pieza en texto legible, truncando listas a 20."""
    lineas = [f"[{tipo}] {item.get('nombre') or item.get('comando') or 'sin_nombre'}"]
    lineas.append("-" * 50)
    for k in sorted(item.keys()):
        v = item[k]
        if isinstance(v, list):
            lineas.append(f"  {k} ({len(v)} elementos):")
            for elem in v[:20]:
                lineas.append(f"    - {elem}")
            if len(v) > 20:
                lineas.append(f"    ... ({len(v) - 20} más truncados)")
        elif isinstance(v, dict):
            lineas.append(f"  {k}:")
            for sub_k in sorted(v.keys())[:20]:
                lineas.append(f"    {sub_k}: {v[sub_k]}")
            if len(v) > 20:
                lineas.append(f"    ... ({len(v) - 20} más truncados)")
        else:
            lineas.append(f"  {k}: {v}")
    return "\n".join(lineas)


def comando_ver(pieza: str, claude_dir: Path, home: Path, proyectos_dir: Path) -> None:
    """Subcomando ver: muestra ficha completa de una pieza."""
    asegurar_al_dia(claude_dir, home, proyectos_dir)
    ruta_mapa = claude_dir / "mapa" / "mapa.json"
    if not ruta_mapa.is_file():
        print(f'No se encontró ninguna pieza que coincida con "{pieza}".')
        sys.exit(0)

    try:
        with open(ruta_mapa, "r", encoding="utf-8") as f:
            inv = json.load(f)
    except Exception:
        print(f'No se encontró ninguna pieza que coincida con "{pieza}".')
        sys.exit(0)

    piezas = recolectar_piezas_para_busqueda(inv)
    # Agregar mods y proyectos si no estaban
    for md in inv.get("mods", []):
        piezas.append({"tipo": "mod", "nombre": md.get("nombre", ""), "descripcion": md.get("descripcion", ""), "raw": md})
    for pr in inv.get("proyectos", []):
        piezas.append({"tipo": "proyecto", "nombre": pr.get("ruta", ""), "descripcion": "", "raw": pr})

    q = pieza.strip().lower()

    # 1. Coincidencia exacta
    exactos = []
    for it in piezas:
        n = str(it.get("nombre", "")).lower()
        raw = it.get("raw", {})
        invoc = str(raw.get("invocacion", "")).lower()
        cmd = str(raw.get("comando", "")).lower()
        if q == n or (invoc and q == invoc) or (cmd and q == cmd):
            exactos.append(it)

    candidatos = exactos
    # 2. Si no hay exacto, por contener
    if not candidatos:
        for it in piezas:
            n = str(it.get("nombre", "")).lower()
            raw = it.get("raw", {})
            invoc = str(raw.get("invocacion", "")).lower()
            cmd = str(raw.get("comando", "")).lower()
            if q in n or (invoc and q in invoc) or (cmd and q in cmd):
                candidatos.append(it)

    if not candidatos:
        print(f'No se encontró ninguna pieza que coincida con "{pieza}".')
        sys.exit(0)

    for it in candidatos:
        print(formatear_ficha_ver(it["tipo"], it["raw"]))
        print()


def calcular_sin_registrar(
    claude_dir: Path,
    home: Path,
    catalogo_path: Path,
) -> Tuple[List[str], List[str]]:
    """
    Cruza el disco con CATALOGO.yaml:
    Devuelve (sin_registrar, registradas_que_ya_no_estan).
    """
    if not catalogo_path.is_file():
        return [], []

    try:
        contenido = catalogo_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return [], []

    regex_conocidos = re.compile(r"^\s{2}([A-Za-z0-9_.-]+):\s*\{", re.MULTILINE)
    conocidos = set(regex_conocidos.findall(contenido))

    # Cargar mapa-disco.json o mapa.json
    mapa_dir = claude_dir / "mapa"
    ruta_disco = mapa_dir / "mapa-disco.json"
    if not ruta_disco.is_file():
        ruta_disco = mapa_dir / "mapa.json"

    inv_disco: Dict[str, Any] = {}
    if ruta_disco.is_file():
        try:
            with open(ruta_disco, "r", encoding="utf-8") as f:
                inv_disco = json.load(f)
        except Exception:
            pass

    skills_p = inv_disco.get("skills_personales", [])
    agentes_p = inv_disco.get("agentes", [])

    locales: Set[str] = set()
    for s in skills_p:
        nom = s.get("nombre") or s.get("carpeta")
        if nom and not nom.startswith((".", "_")):
            locales.add(nom)
    for a in agentes_p:
        nom = a.get("nombre") or a.get("archivo", "").replace(".md", "")
        if nom and not nom.startswith((".", "_")):
            locales.add(nom)

    # 1. Skills y agentes locales que no están en conocidos
    sin_registrar = sorted(n for n in locales if n not in conocidos)

    # 2. Dirección inversa
    bloques_entradas = re.split(r"(?=\n\s{2}[A-Za-z0-9_.-]+:\s*\{)", contenido)
    repo_catalogo = home / "Proyectos" / "Tech" / "claude-catalogo"
    archivos_catalogo_repo: Optional[Set[str]] = None

    def obtener_archivos_catalogo() -> Set[str]:
        nonlocal archivos_catalogo_repo
        if archivos_catalogo_repo is not None:
            return archivos_catalogo_repo
        res_set: Set[str] = set()
        # Intentar subprocess con timeout de 5 s
        try:
            r = subprocess.run(
                ["git", "ls-tree", "-r", "--name-only", "origin/main", "plugins"],
                cwd=str(repo_catalogo),
                capture_output=True,
                text=True,
                timeout=5,
            )
            if r.returncode == 0 and r.stdout:
                for line in r.stdout.splitlines():
                    res_set.add(line.strip())
        except Exception:
            pass

        if not res_set and (repo_catalogo / "plugins").is_dir():
            try:
                for root, _dirs, files in os.walk(str(repo_catalogo / "plugins")):
                    for f in files:
                        p_rel = os.path.relpath(os.path.join(root, f), str(repo_catalogo))
                        res_set.add(p_rel)
            except Exception:
                pass

        archivos_catalogo_repo = res_set
        return archivos_catalogo_repo

    registradas_que_ya_no_estan: List[str] = []

    for bloque in bloques_entradas:
        m = regex_conocidos.search(bloque)
        if not m:
            continue
        nom = m.group(1)

        # estado: no se ignoran
        if re.search(r"\bestado\s*:\s*no\b", bloque, re.IGNORECASE):
            continue

        # vive: catalogo
        if re.search(r"\bvive\s*:\s*catalogo\b", bloque, re.IGNORECASE):
            archivos_cat = obtener_archivos_catalogo()
            # misma regla que usaba aviso-piezas-nuevas: una skill es una carpeta skills/<nom>/, un agente es agents/<nom>.md
            encontrado = any(
                f"/skills/{nom}/" in "/" + p or p.endswith(f"/agents/{nom}.md")
                for p in archivos_cat
            )
            if not encontrado:
                registradas_que_ya_no_estan.append(nom)
        else:
            # el resto se busca en las skills y agentes personales del mapa
            if nom not in locales:
                registradas_que_ya_no_estan.append(nom)

    registradas_que_ya_no_estan.sort()
    return sin_registrar, registradas_que_ya_no_estan


def comando_sin_registrar(claude_dir: Path, home: Path, proyectos_dir: Path, catalogo_arg: Optional[str]) -> None:
    """Subcomando sin-registrar: cruza con CATALOGO.yaml."""
    catalogo_path = (
        Path(os.path.abspath(catalogo_arg))
        if catalogo_arg
        else home / "Proyectos" / "Tech" / "claude-skills-shared" / "CATALOGO.yaml"
    )

    if not catalogo_path.is_file():
        print("sin catálogo que cruzar")
        sys.exit(0)

    asegurar_al_dia(claude_dir, home, proyectos_dir)

    sin_registrar, registradas_que_ya_no_estan = calcular_sin_registrar(claude_dir, home, catalogo_path)

    if sin_registrar:
        print(f"sin registrar ({len(sin_registrar)}):")
        for s in sin_registrar:
            print(f"  - {s}")

    if registradas_que_ya_no_estan:
        print(f"registrada que ya no está ({len(registradas_que_ya_no_estan)}):")
        for r in registradas_que_ya_no_estan:
            print(f"  - {r}")

    if not sin_registrar and not registradas_que_ya_no_estan:
        print("✓ todo registrado y en disco")


def comando_al_dia(claude_dir: Path, home: Path) -> None:
    """Subcomando --al-dia / al-dia: verifica el estado sin reconstruir."""
    mapa_dir = claude_dir / "mapa"
    vig = leer_vigilancia(mapa_dir)
    if vig is None:
        print("✗ mapa sin armar")
        sys.exit(1)

    reg = obtener_registro_de_vigilancia(vig)
    difs = cambios(reg, home)
    if not difs:
        huella = vig.get("huella", "-")
        generado = _hora_local(vig.get("generado_en"))
        print(f"✓ mapa al día (huella {huella}, generado {generado})")
        sys.exit(0)
    else:
        tipo, ruta = difs[0]
        primer_cambio = f"{tipo} {ruta}"
        print(f"✗ mapa viejo: {len(difs)} cambio(s), p. ej. {primer_cambio}")
        sys.exit(1)


def comando_json(claude_dir: Path, home: Path, proyectos_dir: Path) -> None:
    """Subcomando --json: emite mapa.json por stdout."""
    asegurar_al_dia(claude_dir, home, proyectos_dir)
    ruta_mapa = claude_dir / "mapa" / "mapa.json"
    try:
        with open(ruta_mapa, "r", encoding="utf-8") as f:
            contenido = f.read()
        sys.stdout.write(contenido)
        if not contenido.endswith("\n"):
            sys.stdout.write("\n")
    except OSError as e:
        sys.stderr.write(f"mapa: no pude leer mapa.json: {e}\n")
        sys.exit(1)


def comando_actualizar(
    claude_dir: Path,
    home: Path,
    proyectos_dir: Path,
    con_uso: bool,
    out_dir_arg: Optional[str],
) -> None:
    """Subcomando actualizar: fuerza reconstrucción y opcionalmente mide uso y escribe en DIR."""
    mapa_dir = claude_dir / "mapa"
    with CandadoMapa(mapa_dir):
        vig = leer_vigilancia(mapa_dir)
        reconstrucciones = (vig.get("reconstrucciones", 0) if vig else 0) + 1

        stats = None
        metricas = None
        contador = None

        if con_uso:
            stats, metricas, contador = mapa_uso.medir(claude_dir, home)
            uso_dict = mapa_uso.a_json(stats, metricas, contador)
            uso_dict["medido_en"] = datetime.now(timezone.utc).isoformat()
            escribir_json_atomico(mapa_dir / "mapa-uso.json", uso_dict)

        try:
            inv = ejecutar_reconstruccion(
                claude_dir=claude_dir,
                home=home,
                proyectos_dir=proyectos_dir,
                reconstrucciones=reconstrucciones,
                stats_uso=stats,
                metricas_uso=metricas,
                contador_uso=contador,
            )
        except Exception as e:
            sys.stderr.write(f"mapa: no pude rehacer: {e}\n")
            sys.exit(1)

        if out_dir_arg:
            out_dir = Path(os.path.abspath(out_dir_arg))
            crear_directorio(out_dir)
            ordenado = {k: inv[k] for k in sorted(inv.keys(), key=lambda x: (x not in ("generado_en", "directorio_claude", "metricas_ejecucion", "resumen"), x))}
            mapa_lector.generar_reporte_json(ordenado, out_dir / "inventario.json")
            mapa_lector.generar_reporte_markdown(inv, out_dir / "inventario.md")

    print("Mapa al día ✓")


# ==============================================================================
# CLI PARSER
# ==============================================================================

class ParserEspanol(argparse.ArgumentParser):
    """ArgumentParser que responde en español y sale con código 64 ante error de uso."""

    def error(self, message):
        sys.stderr.write(f"mapa: error de uso: {message}\n")
        sys.exit(64)


def obtener_directorios(
    claude_dir_arg: Optional[str] = None,
    home_arg: Optional[str] = None,
    proyectos_dir_arg: Optional[str] = None,
) -> Tuple[Path, Path, Path]:
    home_str = home_arg or os.environ.get("MAPA_HOME") or os.path.expanduser("~")
    home = Path(os.path.abspath(home_str))

    if claude_dir_arg:
        claude_dir = Path(os.path.abspath(claude_dir_arg))
    elif os.environ.get("CLAUDE_CONFIG_DIR"):
        claude_dir = Path(os.path.abspath(os.environ["CLAUDE_CONFIG_DIR"]))
    else:
        claude_dir = home / ".claude"

    if proyectos_dir_arg:
        proyectos_dir = Path(os.path.abspath(proyectos_dir_arg))
    else:
        proyectos_dir = home / "Proyectos"

    return claude_dir, home, proyectos_dir


def main(argv: Optional[List[str]] = None) -> None:
    if argv is None:
        argv = sys.argv[1:]

    # Parser base para opciones comunes
    padre = ParserEspanol(add_help=False)
    padre.add_argument("--claude-dir", type=str, default=None, help="Directorio base de Claude Code")
    padre.add_argument("--home", type=str, default=None, help="Directorio HOME para pruebas")
    padre.add_argument("--proyectos-dir", type=str, default=None, help="Directorio de proyectos")

    parser = ParserEspanol(
        prog="mapa",
        description="Lector del mapa de arneses de Claude Code.",
        parents=[padre],
    )
    parser.add_argument("--al-dia", action="store_true", dest="flag_al_dia", help="Verifica si el mapa está al día")
    parser.add_argument("--json", action="store_true", dest="flag_json", help="Emite mapa.json por stdout")

    subparsers = parser.add_subparsers(dest="subcomando")

    # Subcomando resumen
    subparsers.add_parser("resumen", parents=[padre], help="Muestra MAPA.md y estado calculado")

    # Subcomando buscar
    sub_buscar = subparsers.add_parser("buscar", parents=[padre], help="Busca piezas que coinciden con el tema")
    sub_buscar.add_argument("tema", nargs="+", help="Palabras clave para la búsqueda")

    # Subcomando ver
    sub_ver = subparsers.add_parser("ver", parents=[padre], help="Muestra ficha completa de una pieza")
    sub_ver.add_argument("pieza", help="Nombre o identificador de la pieza")

    # Subcomando sin-registrar
    sub_sin = subparsers.add_parser("sin-registrar", parents=[padre], help="Cruza piezas locales con CATALOGO.yaml")
    sub_sin.add_argument("--catalogo", type=str, default=None, help="Ruta alternativa a CATALOGO.yaml")

    # Subcomando al-dia
    subparsers.add_parser("al-dia", parents=[padre], help="Verifica si el mapa está al día")

    # Subcomando actualizar
    sub_act = subparsers.add_parser("actualizar", parents=[padre], help="Fuerza reconstrucción del mapa")
    sub_act.add_argument("--con-uso", action="store_true", help="Mide uso real antes de reconstruir")
    sub_act.add_argument("--out", type=str, default=None, help="Carpeta destino para inventario.json/md")

    args = parser.parse_args(argv)

    claude_dir, home, proyectos_dir = obtener_directorios(
        claude_dir_arg=getattr(args, "claude_dir", None),
        home_arg=getattr(args, "home", None),
        proyectos_dir_arg=getattr(args, "proyectos_dir", None),
    )

    if args.flag_al_dia or args.subcomando == "al-dia":
        comando_al_dia(claude_dir, home)
    elif args.flag_json:
        comando_json(claude_dir, home, proyectos_dir)
    elif args.subcomando == "buscar":
        comando_buscar(args.tema, claude_dir, home, proyectos_dir)
    elif args.subcomando == "ver":
        comando_ver(args.pieza, claude_dir, home, proyectos_dir)
    elif args.subcomando == "sin-registrar":
        comando_sin_registrar(claude_dir, home, proyectos_dir, args.catalogo)
    elif args.subcomando == "actualizar":
        comando_actualizar(claude_dir, home, proyectos_dir, args.con_uso, args.out)
    else:  # resumen o sin subcomando
        comando_resumen(claude_dir, home, proyectos_dir)


if __name__ == "__main__":
    main()
