#!/usr/bin/env python3
"""Control mensual del ruteo de modelos en Claude Code.

Solo lectura. Lee los transcripts (*.jsonl) bajo la carpeta de proyectos
y cuenta el uso de modelos, esfuerzos, delegaciones a otras IA y sobredimensionamiento.
Nunca imprime ni guarda texto de conversaciones ni rutas de proyectos.
"""
import argparse
import json
import os
import re
import sys
import time
import unicodedata
from datetime import datetime
from pathlib import Path

# Constantes de niveles y esfuerzos
NIVELES = {"haiku": 1, "sonnet": 2, "opus": 3, "fable": 4}
ESFUERZOS = {"low": 1, "medium": 2, "high": 3, "xhigh": 4, "max": 5}

# Intentar importar radar del mismo directorio
AQUI = Path(__file__).resolve().parent
if str(AQUI) not in sys.path:
    sys.path.insert(0, str(AQUI))

try:
    import radar as _radar_mod
except Exception:
    _radar_mod = None

if _radar_mod is not None:
    NIVELES = getattr(_radar_mod, "NIVELES", NIVELES)
    ESFUERZOS = getattr(_radar_mod, "ESFUERZOS", ESFUERZOS)

# Patrones para identificar delegación a otras IA
RE_GEMINI = re.compile(r"agy-delegar|\bagy\s+(?:-|--)|delegar\.py")
RE_CODEX = re.compile(r"\bcodex\s+(?:--\S+\s+)*exec\b|codex-rescue")


def _norm(t):
    """Normaliza texto a minúsculas sin acentos ni signos."""
    t = unicodedata.normalize("NFD", str(t).lower())
    return re.sub(r"[^a-z0-9]+", " ", "".join(c for c in t if unicodedata.category(c) != "Mn")).strip()


def _ruteo_filas(radar):
    """Obtiene las filas válidas del ruteo de Claude."""
    if _radar_mod is not None and hasattr(_radar_mod, "ruteo_filas"):
        try:
            return _radar_mod.ruteo_filas(radar)
        except Exception:
            pass
    out = []
    if isinstance(radar, dict):
        for t in ((radar.get("ruteo_claude") or {}).get("tareas") or []):
            if isinstance(t, dict) and t.get("nivel") in NIVELES and t.get("esfuerzo") in ESFUERZOS:
                out.append(t)
    return out


def _fila_para(radar, texto):
    """Encuentra la fila del ruteo que mejor calza con el texto descriptivo."""
    if _radar_mod is not None and hasattr(_radar_mod, "fila_para"):
        try:
            return _radar_mod.fila_para(radar, texto)
        except Exception:
            pass
    if not isinstance(radar, dict):
        return None
    norm = " %s " % _norm(texto)
    palabras = norm.split()
    elegida = None
    for t in _ruteo_filas(radar):
        for kw in t.get("palabras") or []:
            raiz = str(kw).endswith("*")
            k = _norm(str(kw).rstrip("*"))
            if not k:
                continue
            if " " in k:
                hit = (" %s " % k) in norm
            elif raiz:
                hit = any(w.startswith(k) for w in palabras)
            elif len(k) < 4:
                hit = k in palabras
            elif len(k) <= 5:
                hit = any(w in (k, k + "s", k + "es") for w in palabras)
            else:
                tope = len(k) + (4 if len(k) < 8 else 6)
                hit = any(w.startswith(k) and len(w) <= tope for w in palabras)
            if hit:
                clave = (NIVELES[t["nivel"]], ESFUERZOS[t["esfuerzo"]])
                if elegida is None or clave > elegida[0]:
                    elegida = (clave, t)
                break
    return elegida[1] if elegida else None


def _clasificar_modelo(texto):
    """Clasifica el modelo por alias: haiku, sonnet, opus, fable, sin_model u otro."""
    if texto is None:
        return "sin_model"
    s = str(texto).strip().lower()
    if not s:
        return "sin_model"
    if "haiku" in s:
        return "haiku"
    if "sonnet" in s:
        return "sonnet"
    if "opus" in s:
        return "opus"
    if "fable" in s:
        return "fable"
    return "otro"


def _clasificar_esfuerzo(texto):
    """Clasifica el nivel de esfuerzo o devuelve sin_effort / otro."""
    if texto is None:
        return "sin_effort"
    s = str(texto).strip().lower()
    if not s:
        return "sin_effort"
    if s in ("low", "medium", "high", "xhigh", "max"):
        return s
    return "otro"


def _parsear_iso(ts_str):
    """Parsea una marca de tiempo ISO a timestamp POSIX flotante."""
    if not isinstance(ts_str, str):
        if isinstance(ts_str, (int, float)):
            return float(ts_str)
        return None
    s = ts_str.strip()
    if not s:
        return None
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
        return dt.timestamp()
    except (ValueError, TypeError):
        pass
    try:
        if len(s) >= 10:
            dt = datetime.strptime(s[:10], "%Y-%m-%d")
            return dt.timestamp()
    except Exception:
        pass
    return None


def carpeta_defecto():
    """Ruta por defecto de proyectos de Claude Code."""
    if _radar_mod is not None and hasattr(_radar_mod, "carpeta_config"):
        try:
            return _radar_mod.carpeta_config() / "projects"
        except Exception:
            pass
    propia = os.environ.get("CLAUDE_CONFIG_DIR", "").strip()
    base = Path(propia) if propia else Path.home() / ".claude"
    return base / "projects"


def medir(carpeta, dias, radar, ahora=None):
    """Recorre los transcripts en carpeta y cuenta modelos, esfuerzos, delegaciones y desvíos."""
    if ahora is None:
        ahora_ts = time.time()
    elif isinstance(ahora, (int, float)):
        ahora_ts = float(ahora)
    elif isinstance(ahora, datetime):
        ahora_ts = ahora.timestamp()
    else:
        ahora_ts = time.time()

    limite_ts = ahora_ts - (dias * 86400)

    res = {
        "subagentes": 0,
        "modelos": {
            "haiku": 0,
            "sonnet": 0,
            "opus": 0,
            "fable": 0,
            "sin_model": 0,
            "otro": 0,
        },
        "esfuerzos": {
            "low": 0,
            "medium": 0,
            "high": 0,
            "xhigh": 0,
            "max": 0,
            "sin_effort": 0,
            "otro": 0,
        },
        "codex": 0,
        "gemini_o_delegar": 0,
        "medidos": 0,
        "sobredimensionados": None if radar is None else 0,
        "ilegibles": 0,
    }

    base = Path(carpeta)
    if not base.is_dir():
        return res

    try:
        archivos = list(base.rglob("*.jsonl"))
    except OSError:
        res["ilegibles"] += 1
        return res

    for p in archivos:
        try:
            if not p.is_file():
                continue
            mtime = p.stat().st_mtime
        except OSError:
            res["ilegibles"] += 1
            continue

        try:
            with open(p, "r", encoding="utf-8") as f:
                lineas = f.readlines()
        except (OSError, UnicodeError):
            res["ilegibles"] += 1
            continue

        for linea in lineas:
            linea_s = linea.strip()
            if not linea_s:
                continue
            try:
                obj = json.loads(linea_s)
            except Exception:
                continue
            if not isinstance(obj, dict):
                continue

            ts_raw = obj.get("timestamp")
            ts_parsed = _parsear_iso(ts_raw) if ts_raw is not None else None
            ts_linea = ts_parsed if ts_parsed is not None else mtime

            if ts_linea < limite_ts:
                continue

            msg = obj.get("message")
            if not isinstance(msg, dict):
                continue
            content = msg.get("content")
            if not isinstance(content, list):
                continue

            for block in content:
                if not isinstance(block, dict):
                    continue
                if block.get("type") != "tool_use":
                    continue

                name = str(block.get("name") or "")
                inp = block.get("input")
                if not isinstance(inp, dict):
                    inp = {}

                # a) Subagentes / sesiones derivadas
                es_subagente = name in ("Agent", "Task")
                es_derivada = name.endswith("start_session")

                if es_subagente or es_derivada:
                    res["subagentes"] += 1
                    m_cls = _clasificar_modelo(inp.get("model"))
                    res["modelos"][m_cls] = res["modelos"].get(m_cls, 0) + 1
                    e_cls = _clasificar_esfuerzo(inp.get("effort"))
                    res["esfuerzos"][e_cls] = res["esfuerzos"].get(e_cls, 0) + 1

                    # c) Sobredimensionados
                    if radar is not None and m_cls in ("haiku", "sonnet", "opus"):
                        desc = inp.get("description") if es_subagente else inp.get("title")
                        if desc and str(desc).strip():
                            fila = _fila_para(radar, str(desc))
                            if fila is not None and isinstance(fila, dict):
                                res["medidos"] += 1
                                fn = str(fila.get("nivel") or "")
                                fe = str(fila.get("esfuerzo") or "")
                                u_niv = NIVELES.get(m_cls, 0)
                                f_niv = NIVELES.get(fn, 0)
                                es_sobredim = False
                                if u_niv > f_niv:
                                    es_sobredim = True
                                elif u_niv == f_niv and e_cls in ESFUERZOS:
                                    if ESFUERZOS[e_cls] > ESFUERZOS.get(fe, 0):
                                        es_sobredim = True
                                if es_sobredim:
                                    res["sobredimensionados"] += 1

                # b) Delegación a otra IA
                if name == "Bash":
                    cmd = str(inp.get("command") or "")
                    if RE_GEMINI.search(cmd):
                        res["gemini_o_delegar"] += 1
                    if RE_CODEX.search(cmd):
                        res["codex"] += 1

                if name == "Agent":
                    subagent_type = str(inp.get("subagent_type") or block.get("subagent_type") or "")
                    if "codex" in subagent_type.lower():
                        res["codex"] += 1

    return res


def resumen(datos, dias):
    """Devuelve exactamente 3 líneas resumiendo las métricas en castellano rioplatense."""
    subagentes = datos.get("subagentes", 0)
    modelos = datos.get("modelos") or {}
    esfuerzos = datos.get("esfuerzos") or {}

    mod_items = [f"{k} {v}" for k, v in sorted(modelos.items(), key=lambda x: (-x[1], x[0])) if v > 0]
    mod_str = ", ".join(mod_items) if mod_items else "sin datos"

    esf_items = [f"{k} {v}" for k, v in sorted(esfuerzos.items(), key=lambda x: (-x[1], x[0])) if v > 0]
    esf_str = ", ".join(esf_items) if esf_items else "sin datos"

    linea1 = (
        f"Control del ruteo (últimos {dias} días): {subagentes} subagentes o sesiones derivadas "
        f"· modelos: {mod_str} · esfuerzo: {esf_str}."
    )

    codex = datos.get("codex", 0)
    gemini = datos.get("gemini_o_delegar", 0)
    linea2 = f"A otras IA: Codex {codex} · Gemini o delegar.py {gemini}."

    sobredim = datos.get("sobredimensionados")
    medidos = datos.get("medidos", 0)

    if sobredim is None:
        linea3 = "Sobredimensionados: no se pudo leer el ruteo."
    elif medidos == 0:
        linea3 = "Sobredimensionados: sin datos medibles."
    else:
        pct = round(100.0 * sobredim / medidos)
        linea3 = f"Sobredimensionados según el ruteo: {sobredim} de {medidos} medidos ({pct} %)."

    return [linea1, linea2, linea3]


def main(argv=None):
    """Punto de entrada de la CLI. Siempre devuelve 0."""
    try:
        parser = argparse.ArgumentParser(description="Control mensual del ruteo de modelos en Claude Code.")
        parser.add_argument("--dias", type=int, default=30, help="Ventana de días a considerar (por defecto 30).")
        parser.add_argument("--carpeta", type=str, default=None, help="Ruta a la carpeta de proyectos.")
        parser.add_argument("--json", action="store_true", help="Imprime el dict de números en vez del resumen.")
        args = parser.parse_args(argv)

        carpeta = Path(args.carpeta) if args.carpeta else carpeta_defecto()

        if not carpeta.is_dir():
            print("Control del ruteo: no hay transcripts para medir.")
            return 0

        hay_transcripts = False
        try:
            for p in carpeta.rglob("*.jsonl"):
                if p.is_file():
                    hay_transcripts = True
                    break
        except Exception:
            hay_transcripts = False

        if not hay_transcripts:
            print("Control del ruteo: no hay transcripts para medir.")
            return 0

        radar_obj = None
        if _radar_mod is not None and hasattr(_radar_mod, "cargar"):
            try:
                radar_obj, _ = _radar_mod.cargar()
            except Exception:
                radar_obj = None

        datos = medir(carpeta, args.dias, radar_obj)

        if args.json:
            print(json.dumps(datos, ensure_ascii=False, indent=2))
        else:
            lineas = resumen(datos, args.dias)
            print("\n".join(lineas))
        return 0
    except SystemExit as e:
        return e.code if isinstance(e.code, int) and e.code == 0 else 0
    except Exception:
        return 0


if __name__ == "__main__":
    sys.exit(main())
