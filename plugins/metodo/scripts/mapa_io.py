#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mapa_io.py - Operaciones de entrada/salida y registro de firmas para el mapa.
Disparador: encadenado — lo usa mapa.py (el comando `mapa`).

Encapsula todo acceso al sistema de archivos para el inventario del mapa de Claude Code,
registrando cada archivo leído y carpeta listada para detección de cambios.
Python 3.9 estándar, sin librerías externas.
"""

from collections import namedtuple
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union


def firma(p: Union[str, Path]) -> str:
    """
    Firma lstat de un archivo o carpeta en formato '{st_mtime_ns}:{st_size}'.
    Si no existe devuelve 'ausente'. Con cualquier otro error OSError devuelve 'ERR:{errno}'.
    Nunca levanta excepción.
    """
    try:
        st = os.lstat(str(p))
        return f"{st.st_mtime_ns}:{st.st_size}"
    except FileNotFoundError:
        return "ausente"
    except OSError as e:
        return f"ERR:{e.errno}"


def firma_tipo(p: Union[str, Path]) -> str:
    """
    Firma de EXISTENCIA y tipo (siguiendo enlaces): 'T:dir', 'T:file', 'T:none' o 'T:otro'.
    Es lo que se registra cuando el lector solo pregunta «¿existe? ¿es carpeta? ¿es archivo?»: la fecha de esa ruta
    no le importa (la de `.git` cambia con cada commit, la de `plugins/cache` con cada actualización de la app).
    """
    try:
        if os.path.isdir(str(p)):
            return "T:dir"
        if os.path.isfile(str(p)):
            return "T:file"
        return "T:otro" if os.path.lexists(str(p)) else "T:none"
    except OSError:
        return "T:none"


Entrada = namedtuple("Entrada", ["nombre", "ruta", "es_dir"])


class Registro(dict):
    """
    Registro serializable a JSON (dict) que contiene:
      - arch: dict ruta(str absoluta) -> firma (str)
      - dirs: dict ruta(str absoluta) -> [firma, [nombres]]
      - contenido: dict clave(str) -> huella(str)
    """

    def __init__(
        self,
        arch: Optional[Dict[str, str]] = None,
        dirs: Optional[Dict[str, List[Any]]] = None,
        contenido: Optional[Dict[str, str]] = None,
        fuentes: Optional[Dict[str, Any]] = None,
    ):
        super().__init__()
        self["arch"] = dict(arch) if arch is not None else {}
        self["dirs"] = dict(dirs) if dirs is not None else {}
        self["contenido"] = dict(contenido) if contenido is not None else {}
        # clave de contenido -> [ruta absoluta del JSON, [claves anidadas]]; se guarda para poder recalcular sin adivinar
        self["fuentes"] = dict(fuentes) if fuentes is not None else {}
        # Mapping interno clave -> (ruta_archivo_abs, list_claves_json) para recalcular huellas
        self._fuentes: Dict[str, Tuple[str, List[str]]] = {}

    @property
    def arch(self) -> Dict[str, str]:
        return self["arch"]

    @arch.setter
    def arch(self, val: Dict[str, str]) -> None:
        self["arch"] = val

    @property
    def dirs(self) -> Dict[str, List[Any]]:
        return self["dirs"]

    @dirs.setter
    def dirs(self, val: Dict[str, List[Any]]) -> None:
        self["dirs"] = val

    @property
    def contenido(self) -> Dict[str, str]:
        return self["contenido"]

    @contenido.setter
    def contenido(self, val: Dict[str, str]) -> None:
        self["contenido"] = val

    def mezclar(self, otro: Union["Registro", Dict[str, Any]]) -> "Registro":
        """Suma otro Registro a este."""
        if isinstance(otro, dict):
            otro_arch = otro.get("arch", {})
            otro_dirs = otro.get("dirs", {})
            otro_cont = otro.get("contenido", {})
            self.arch.update(otro_arch)
            self.dirs.update(otro_dirs)
            self.contenido.update(otro_cont)
            if hasattr(otro, "_fuentes"):
                self._fuentes.update(getattr(otro, "_fuentes"))
            elif "_fuentes" in otro:
                self._fuentes.update(otro["_fuentes"])
        return self


def es_modo_proyectos(p: Union[str, Path], home: Union[str, Path]) -> bool:
    """
    Devuelve True si `p` está dentro de home/'Proyectos' y NINGÚN componente de su ruta es '.claude'.
    """
    p_abs = Path(os.path.abspath(str(p)))
    home_abs = Path(os.path.abspath(str(home)))
    proy_base = home_abs / "Proyectos"
    try:
        p_abs.relative_to(proy_base)
        return ".claude" not in p_abs.parts
    except ValueError:
        return False


def _nivel_en_proyectos(p: Union[str, Path], home: Union[str, Path]) -> int:
    """Cuántos niveles bajo home/Proyectos está `p` (Proyectos = 0). -1 si no está ahí."""
    try:
        rel = Path(os.path.abspath(str(p))).relative_to(Path(os.path.abspath(str(home))) / "Proyectos")
    except ValueError:
        return -1
    return len(rel.parts)


def obtener_nombres_relevantes(p: Union[str, Path], home: Union[str, Path]) -> List[str]:
    """
    Devuelve los nombres que, si cambian, cambian el mapa:
    - MODO PROYECTOS (bajo ~/Proyectos y fuera de un .claude): el lector solo busca carpetas `.claude` (hasta 4 niveles)
      y archivos `.mcp.json` (hasta 3). Entonces: nivel 0-2 → subcarpetas (con '/') y `.mcp.json`; nivel 3 → solo `.claude/`
      y `.mcp.json` (lo demás no se recorre: antes cada carpeta temporal de una copia de trabajo rehacía el mapa);
      nivel 4 o más → nada (solo cuenta su propio nombre, que ya vigila su padre).
    - Fuera de ese modo: todos los nombres (carpetas con '/'), menos las marcas ocultas que la app pone y saca sola
      (p. ej. `.in_use` en cada plugin cargado), salvo `.claude`, `.claude-plugin` y `.mcp.json`.
    Usa follow_symlinks=False para determinar si es carpeta.
    """
    p_str = os.path.abspath(str(p))
    if not os.path.isdir(p_str):
        return []
    modo_proy = es_modo_proyectos(p_str, home)
    nivel = _nivel_en_proyectos(p_str, home) if modo_proy else -1
    if modo_proy and nivel >= 4:
        return []
    nombres: List[str] = []
    try:
        with os.scandir(p_str) as it:
            for de in it:
                try:
                    es_dir = de.is_dir(follow_symlinks=False)
                except OSError:
                    es_dir = False
                nombre = de.name
                if modo_proy:
                    if nombre == ".mcp.json" and not es_dir:
                        nombres.append(nombre)
                    elif es_dir and (nivel < 3 or nombre == ".claude"):
                        nombres.append(f"{nombre}/")
                    continue
                if nombre.startswith(".") and nombre not in (".claude", ".claude-plugin", ".mcp.json"):
                    continue
                nombres.append(f"{nombre}/" if es_dir else nombre)
    except OSError:
        return []
    return sorted(nombres)


def huella_claves(nombres: List[str]) -> str:
    """Calcula el sha1 de los nombres ordenados, unidos por salto de línea."""
    unido = "\n".join(sorted(nombres))
    return hashlib.sha1(unido.encode("utf-8")).hexdigest()


def extraer_claves_json(ruta: Union[str, Path], ruta_claves: Union[str, List[str], Tuple[str, ...]]) -> List[str]:
    """Extrae las claves de un dict anidado en un archivo JSON sin tocar 'arch'."""
    p_str = os.path.abspath(str(ruta))
    try:
        with open(p_str, "r", encoding="utf-8", errors="replace") as f:
            data = json.load(f)
    except Exception:
        return []

    if isinstance(ruta_claves, str):
        claves = [ruta_claves]
    else:
        claves = list(ruta_claves)

    for k in claves:
        if isinstance(data, dict):
            data = data.get(k)
        else:
            return []

    if isinstance(data, dict):
        return sorted(str(k) for k in data.keys())
    return []


class IO:
    """
    Manejo centralizado de E/S con registro de firmas lstat y huellas de contenido.
    No llama a Path.home() ni a os.path.expanduser('~').
    """

    def __init__(
        self,
        home: Union[str, Path],
        claude_dir: Union[str, Path],
        registro: Optional[Registro] = None,
    ):
        self.home = Path(os.path.abspath(str(home)))
        self.claude_dir = Path(os.path.abspath(str(claude_dir)))
        self.registro = registro if registro is not None else Registro()

    def expandir_ruta(self, p: Union[str, Path]) -> Path:
        """Expande rutas que inicien con ~ usando self.home."""
        s = str(p)
        if s == "~":
            return self.home
        if s.startswith("~/"):
            return self.home / s[2:]
        return Path(os.path.abspath(s))

    def real(self, p: Union[str, Path]) -> Path:
        """Devuelve la ruta canónica en disco sin invocar .resolve() en mapa_lector."""
        return Path(os.path.realpath(str(p)))

    def con_tilde(self, p: Any) -> str:
        """Sustituye self.home por ~ en una ruta."""
        if not p:
            return ""
        return str(p).replace(str(self.home), "~")

    def leer_texto(self, p: Union[str, Path]) -> Optional[str]:
        """Lee archivo de texto en utf-8 (errors='replace'); registra en arch."""
        p_abs = os.path.abspath(str(p))
        self.registro.arch[p_abs] = firma(p_abs)
        try:
            with open(p_abs, "r", encoding="utf-8", errors="replace") as f:
                return f.read()
        except OSError:
            return None

    def leer_json(self, p: Union[str, Path]) -> Any:
        """Lee archivo JSON de forma tolerante; registra en arch."""
        p_abs = os.path.abspath(str(p))
        self.registro.arch[p_abs] = firma(p_abs)
        try:
            with open(p_abs, "r", encoding="utf-8", errors="replace") as f:
                return json.load(f)
        except Exception:
            return None

    def existe(self, p: Union[str, Path]) -> bool:
        """Comprueba existencia siguiendo enlaces; registra en arch."""
        p_abs = os.path.abspath(str(p))
        self.registro.arch.setdefault(p_abs, firma_tipo(p_abs))
        return os.path.exists(p_abs)

    def es_archivo(self, p: Union[str, Path]) -> bool:
        """Comprueba si es archivo siguiendo enlaces; registra en arch."""
        p_abs = os.path.abspath(str(p))
        self.registro.arch.setdefault(p_abs, firma_tipo(p_abs))
        return os.path.isfile(p_abs)

    def es_dir(self, p: Union[str, Path]) -> bool:
        """Comprueba si es directorio siguiendo enlaces; registra en arch."""
        p_abs = os.path.abspath(str(p))
        self.registro.arch.setdefault(p_abs, firma_tipo(p_abs))
        return os.path.isdir(p_abs)

    def es_symlink(self, p: Union[str, Path]) -> bool:
        """Comprueba si es enlace simbólico; registra en arch."""
        p_abs = os.path.abspath(str(p))
        self.registro.arch.setdefault(p_abs, firma_tipo(p_abs) if not os.path.islink(p_abs) else "T:link")
        return os.path.islink(p_abs)

    def mtime(self, p: Union[str, Path]) -> Optional[float]:
        """Devuelve fecha de modificación (st_mtime) en segundos; registra en arch."""
        p_abs = os.path.abspath(str(p))
        self.registro.arch[p_abs] = firma(p_abs)
        try:
            return os.stat(p_abs).st_mtime
        except OSError:
            return None

    def tamano(self, p: Union[str, Path]) -> Optional[int]:
        """Devuelve tamaño en bytes; registra en arch."""
        p_abs = os.path.abspath(str(p))
        self.registro.arch[p_abs] = firma(p_abs)
        try:
            return os.stat(p_abs).st_size
        except OSError:
            return None

    def listar(self, p: Union[str, Path]) -> List[Entrada]:
        """
        Lista el contenido directo de un directorio.
        Devuelve List[Entrada] ordenada por nombre ([] si no existe).
        Registra dirs[p] = [firma_carpeta, huella_de_nombres_relevantes] (la huella, no la lista: el registro pesa 5 veces menos).
        """
        p_abs = os.path.abspath(str(p))
        f_dir = firma(p_abs)
        if not os.path.isdir(p_abs):
            self.registro.dirs[p_abs] = [f_dir, huella_claves([])]
            return []

        nombres_rel = obtener_nombres_relevantes(p_abs, self.home)
        self.registro.dirs[p_abs] = [f_dir, huella_claves(nombres_rel)]

        entradas: List[Entrada] = []
        try:
            with os.scandir(p_abs) as it:
                for de in it:
                    try:
                        es_d = de.is_dir(follow_symlinks=True)
                    except OSError:
                        es_d = False
                    entradas.append(Entrada(nombre=de.name, ruta=Path(de.path), es_dir=es_d))
        except OSError:
            return []

        entradas.sort(key=lambda e: e.nombre)
        return entradas

    def caminar(self, raiz: Union[str, Path], podar: Any = None):
        """
        Generador topdown igual que os.walk(raiz) sin seguir enlaces a carpetas.
        `dirs` se puede modificar en el lugar para podar.
        Registra dirs[actual] por cada carpeta que realmente se lista.
        """
        raiz_abs = os.path.abspath(str(raiz))
        if not os.path.isdir(raiz_abs):
            self.registro.dirs[raiz_abs] = [firma(raiz_abs), huella_claves([])]
            return

        def _walk(actual_dir: str):
            f_act = firma(actual_dir)
            nombres_rel = obtener_nombres_relevantes(actual_dir, self.home)
            self.registro.dirs[actual_dir] = [f_act, huella_claves(nombres_rel)]

            dirs_list: List[str] = []
            files_list: List[str] = []
            try:
                with os.scandir(actual_dir) as it:
                    for de in it:
                        try:
                            es_d = de.is_dir(follow_symlinks=False)
                        except OSError:
                            es_d = False
                        if es_d:
                            dirs_list.append(de.name)
                        else:
                            files_list.append(de.name)
            except OSError:
                return

            dirs_list.sort()
            files_list.sort()

            if podar is not None:
                try:
                    podar(actual_dir, dirs_list, files_list)
                except TypeError:
                    podar(dirs_list)

            yield actual_dir, dirs_list, files_list

            for d in list(dirs_list):
                sub = os.path.join(actual_dir, d)
                if os.path.isdir(sub) and not os.path.islink(sub):
                    yield from _walk(sub)

        yield from _walk(raiz_abs)

    def contar_archivos(self, p: Union[str, Path]) -> int:
        """
        Cuenta archivos no ocultos recursivamente.
        Registra en dirs todas las carpetas que recorre.
        """
        p_abs = os.path.abspath(str(p))
        if not os.path.isdir(p_abs):
            self.registro.dirs[p_abs] = [firma(p_abs), huella_claves([])]
            return 0
        total = 0
        for _actual, _dirs, files in self.caminar(p_abs):
            for f in files:
                if not f.startswith("."):
                    total += 1
        return total

    def nombres_json(
        self,
        p: Union[str, Path],
        ruta_claves: Union[str, List[str], Tuple[str, ...]],
        clave_registro: str,
    ) -> List[str]:
        """
        Extrae exclusivamente nombres de claves de un dict anidado dentro de un JSON.
        NO registra arch[p]; registra contenido[clave_registro] = sha1(nombres).
        Nunca guarda valores.
        """
        p_abs = os.path.abspath(str(p))
        claves_list = [ruta_claves] if isinstance(ruta_claves, str) else list(ruta_claves)
        nombres = extraer_claves_json(p_abs, claves_list)
        huella = huella_claves(nombres)
        self.registro.contenido[clave_registro] = huella
        self.registro._fuentes[clave_registro] = (p_abs, claves_list)
        self.registro["fuentes"][clave_registro] = [p_abs, claves_list]
        return nombres


def cambios(registro: Registro, home: Union[str, Path]) -> List[Tuple[str, str]]:
    """
    Compara un Registro guardado contra el disco actual y devuelve la lista de diferencias:
      - por cada arch: si firma(p) != guardada -> ("archivo", p)
      - por cada dir: si firma(p) != guardada, se vuelven a leer los nombres relevantes
        (misma regla de modo proyectos) y solo si difieren -> ("carpeta", p)
      - por cada contenido: se recalcula la huella con el mismo código que nombres_json ->
        si difiere -> ("contenido", clave)
    """
    home_abs = Path(os.path.abspath(str(home)))
    difs: List[Tuple[str, str]] = []

    # 1. Archivos
    for p, f_guardada in sorted(registro.arch.items()):
        actual = firma_tipo(p) if f_guardada.startswith("T:") else firma(p)
        if f_guardada == "T:link":
            actual = "T:link" if os.path.islink(p) else firma_tipo(p)
        if actual != f_guardada:
            difs.append(("archivo", p))

    # 2. Carpetas
    for p, val in sorted(registro.dirs.items()):
        f_guardada, huella_nombres_guardada = val[0], val[1]
        # En Windows (NTFS) la fecha de una carpeta se actualiza con retraso o no se actualiza al agregar/borrar un archivo:
        # no sirve de aviso. Ahí siempre se vuelven a leer los nombres (cuesta unos cientos de ms más; en Mac/Linux alcanza la fecha).
        if sys.platform == "win32" or firma(p) != f_guardada:
            nombres_actuales = obtener_nombres_relevantes(p, home_abs)
            if huella_claves(nombres_actuales) != huella_nombres_guardada:
                difs.append(("carpeta", p))

    # 3. Contenido
    fuentes = dict(getattr(registro, "_fuentes", {}))
    for _k, _v in (registro.get("fuentes") or {}).items():      # las guardadas en vigilancia.json
        if isinstance(_v, (list, tuple)) and len(_v) == 2:
            fuentes.setdefault(_k, (_v[0], list(_v[1])))
    for clave, huella_guardada in sorted(registro.contenido.items()):
        if clave in fuentes:
            p_abs, ruta_claves = fuentes[clave]
            nombres = extraer_claves_json(p_abs, ruta_claves)
            huella_actual = huella_claves(nombres)
        else:
            p_abs = None
            ruta_claves = []
            if clave in ("mcpServers", "mcp_servers_usuario"):
                p_abs = str(home_abs / ".claude.json")
                ruta_claves = ["mcpServers"]
            elif clave == "mcp_proyectos_claude_json":
                p_abs = str(home_abs / ".claude.json")
                ruta_claves = ["projects"]
            elif clave.startswith("proyectos.") and clave.endswith(".mcpServers"):
                ruta_p = clave[len("proyectos."):-len(".mcpServers")]
                p_abs = str(home_abs / ".claude.json")
                ruta_claves = ["projects", ruta_p, "mcpServers"]
            elif clave in ("claude_desktop:mcpServers", "desktop:mcpServers"):
                p_abs = str(home_abs / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json")
                ruta_claves = ["mcpServers"]

            if p_abs is not None:
                nombres = extraer_claves_json(p_abs, ruta_claves)
                huella_actual = huella_claves(nombres)
            else:
                huella_actual = huella_guardada

        if huella_actual != huella_guardada:
            difs.append(("contenido", clave))

    return difs


def escribir_texto(ruta: Union[str, Path], texto: str) -> None:
    """Escribe texto en un archivo en codificación utf-8."""
    p_abs = os.path.abspath(str(ruta))
    with open(p_abs, "w", encoding="utf-8") as f:
        f.write(texto)


def escribir_json(ruta: Union[str, Path], datos: Any) -> None:
    """Escribe datos estructurados en formato JSON con indentación 1."""
    p_abs = os.path.abspath(str(ruta))
    with open(p_abs, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=1)


def crear_directorio(ruta: Union[str, Path]) -> None:
    """Crea un directorio y sus padres si no existen."""
    p_abs = os.path.abspath(str(ruta))
    os.makedirs(p_abs, exist_ok=True)


def io_por_defecto(claude_dir: Optional[Union[str, Path]] = None) -> IO:
    """Crea una instancia de IO usando el HOME del usuario."""
    home = Path(os.path.expanduser("~"))
    c_dir = Path(claude_dir) if claude_dir else home / ".claude"
    return IO(home=home, claude_dir=c_dir)
