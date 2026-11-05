#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""reglas-unicas.py — una regla, un solo hogar: frena al escribir una regla que ya vive en otro archivo.

Disparador: automático — el hook PreToolUse (Write|Edit) del paquete `metodo` lo llama con `hook` antes de cada edición
de un archivo de reglas · encadenado — `revisar` lo corre arrancar-check/controles · manual: reglas-unicas.py revisar

Por qué existe: el detector que mira DESPUÉS (reglas-salud.py) encontró la misma regla en la ficha global, en
MANDAMIENTOS, en rules/ y en el paquete del método. Una regla repetida deriva: se corrige en un lado y queda vieja en el
otro, y las sesiones cargan el texto dos veces. Este control actúa ANTES: el cambio que agrega una regla ya escrita en
otro archivo no se guarda hasta que la regla quede en un solo lugar (el otro lado lleva un puntero corto).

Cómo decide (sin IA, solo lee): parte los archivos de reglas en unidades (fila de tabla, ítem de lista, párrafo) de al
menos 30 palabras, y dos unidades de archivos distintos son «la misma regla» si comparten la mayor parte de su texto
(tramos de 5 palabras seguidos) o casi todos sus comandos y rutas entre comillas invertidas. Un puntero corto
(«→ ver MANDAMIENTOS.md §XV») nunca cuenta. Parafraseos con otras palabras y otros comandos no los ve: eso lo mira la
revisión con IA de reglas-salud.py.

Salida de emergencia visible: una unidad que termina en `<!-- eco: motivo -->` es un eco a propósito y se ignora.
Los duplicados que ya existían al instalar se anotan en la base (<config>/metodo/reglas-unicas-base.json) y no frenan
a nadie; lo que se agrega DESPUÉS sí. La base se crea sola la primera vez (el usuario no corre nada).

Segunda revisión (mismo hook): una REGLA no ordena por nombre de IA. «Codex primero», «usá Gemini», «mandalo a Antigravity»
frenan al guardarse; el orden de las IA vive en el radar (que cambia por semana), no en las reglas (que casi no cambian).
Solo mira las líneas nuevas o cambiadas; una línea que describe sin ordenar («Codex no ve tus skills») pasa; una orden a
propósito termina en `<!-- ia-ok: motivo -->`.

Uso:
  reglas-unicas.py hook                    (lo llama Claude Code; lee el JSON del hook por la entrada estándar)
  reglas-unicas.py revisar [--todo] [--cwd DIR]   lista los duplicados (sale 1 si hay alguno fuera de la base)
  reglas-unicas.py aviso [--forzar]        una vez por semana, solo si hay algo: repetidas nuevas, ficha que engorda, rutas rotas
  reglas-unicas.py ordenes [--archivos A B…]   lista las órdenes por nombre de IA (sale 1 si hay alguna); sin --archivos, tus reglas
  reglas-unicas.py base                    anota los duplicados de hoy como conocidos
Variables: CLAUDE_CONFIG_DIR (default ~/.claude) · REGLAS_UNICAS_OFF=1 apaga el hook.
Python 3.8+, solo librería estándar. Nunca bloquea por un error propio (si algo falla, deja pasar)."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import unicodedata
from pathlib import Path

for _f in (sys.stdin, sys.stdout, sys.stderr):
    try:
        _f.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

MIN_PALABRAS = 30          # una unidad más corta es un puntero o un título, no una regla
SHINGLE = 5                # tramos de 5 palabras seguidas
UMBRAL_TEXTO = 0.55        # parte de la unidad MÁS CORTA que aparece idéntica en la otra
UMBRAL_CODIGO = 0.75       # parte de los comandos/rutas de la más corta que están en la otra
MIN_CODIGO = 3             # y al menos tantos comandos/rutas distintos en común
LEER_MAX = 2_000_000
INI = "<!-- reglas-del-metodo:inicio -->"
FIN = "<!-- reglas-del-metodo:fin -->"
ECO = re.compile(r"<!--\s*eco\s*:", re.I)
CODIGO_COMUN = {"main", "git", "true", "false", "none", "null", "claude", "python3", "bash", "sh"}


# ---- órdenes por nombre de IA. El nombre va solo: «codex-cupo», «agy-delegar» o «gemini.json» son programas/archivos, no un nombre.
_IA = r"(?:codex|gemini|antigravity|openai|chatgpt|gpt-?\d[\w.]*|perplexity|grok|deepseek|mistral|copilot|kimi|qwen)"
NOMBRE_IA = r"(?<![A-Za-z0-9_\-/.])" + _IA + r"(?![A-Za-z0-9_\-]|\.[A-Za-z])"
_ORDEN = r"(?:primero|siempre|antes que|por defecto|de entrada|preferentemente|prioridad|en primer lugar)"


def _verbo(raiz: str, tildada: str) -> str:
    """Imperativo con voseo (usá), infinitivo (usar) y con pronombre (usalo). No el presente («esto usa X», «pasa lo mismo») ni
    sustantivos (usuario, uso, paso, correo, pedido)."""
    return rf"{raiz}(?:{tildada}|ar|alo|ala|alos|alas)"


_VERBOS = "|".join([_verbo("us", "á"), _verbo("mand", "á"), _verbo("deleg", "á"), _verbo("deriv", "á"), _verbo("envi", "á|ía"),
                    _verbo("pas", "á"), _verbo("implement", "á"), _verbo("revis", "á"), _verbo("corr", "é"), _verbo("ped", "í"),
                    r"pedir(?:le|les)?", r"hacelo", r"vuelv(?:e|an)\s+(?:a|al)", r"va(?:n)?\s+(?:a|al)", r"qued(?:a|an|á)\s+(?:en|con)"])
_VERBO = r"(?<![A-Za-zÁ-úñ])(?:" + _VERBOS + r")(?![A-Za-zÁ-úñ])"
_SEP = r"[\s:()\-–>=]{1,6}"
ORDEN_IA = [
    re.compile(NOMBRE_IA + r"(?:\s*[/,y]\s*" + _IA + r")*" + _SEP + _ORDEN, re.I),          # «Codex primero», «Gemini: siempre»
    re.compile(_ORDEN + r"\s+(?:a\s+|con\s+|en\s+)?(?:la\s+)?(?:IA\s+)?" + NOMBRE_IA, re.I),     # «primero Codex»
    re.compile(_VERBO + r"[^.;\n]{0,40}?" + NOMBRE_IA, re.I),                                   # «usá Codex», «va a Codex/Gemini»
]
NEGACION = re.compile(r"\b(?:nunca|jam[aá]s|no|ni|evit[aá]\w*|prohib\w+|sin)\b", re.I)
IA_OK = re.compile(r"<!--\s*ia-ok\s*:", re.I)
_ITEM = re.compile(r"(?:[-*+]|\d+[.)])\s")


def _con_orden(texto: str) -> bool:
    """True si hay una orden por nombre de IA que no está negada (una PROHIBICIÓN —«nunca uses X con datos…»— no es una orden)."""
    for r in ORDEN_IA:
        for m in r.finditer(texto):
            if not NEGACION.search(texto[max(0, m.start() - 25):m.start() + 6]):
                return True
    return False


def _normal(linea: str) -> str:
    """Línea sin viñeta ni numeración, con espacios únicos: un cambio de formato no la vuelve «nueva»."""
    return re.sub(r"\s+", " ", _ITEM.sub("", linea.strip(), count=1)).strip()


def ordenes_ia(texto: str) -> list:
    """[(n° de línea, texto)] con una orden por nombre de IA. Une las líneas partidas de un mismo ítem, mira también los títulos,
    ignora bloques de código y las líneas con `ia-ok`."""
    out, fence, buf, ini = [], False, [], 0

    def cerrar():
        nonlocal buf
        if buf:
            u = " ".join(buf)
            if not IA_OK.search(u) and _con_orden(u):
                out.append((ini, _normal(u)))
        buf = []

    for i, linea in enumerate(texto.splitlines(), 1):
        s = linea.strip()
        if s.startswith("```"):
            cerrar()
            fence = not fence
            continue
        if fence or not s:
            cerrar()
            continue
        if s.startswith(("#", "|", ">")) or _ITEM.match(s):
            cerrar()
            ini = i
            buf = [s.lstrip("#").strip() if s.startswith("#") else s]
            if s.startswith(("#", "|")):
                cerrar()
        else:
            if not buf:
                ini = i
            buf.append(s)
    cerrar()
    return out


def mensaje_ordenes(lineas: list) -> str:
    out = ["Una regla no ordena por nombre de IA: el orden de las IA cambia por semana y vive en el radar, no en las reglas."]
    for _n, l in lineas[:3]:
        out.append("  • «" + (l[:110] + ("…" if len(l) > 110 else "")) + "»")
    out.append("Qué hacer: escribí la regla sin el nombre («lo decide el radar», `radar.py ruteo …`). Si la orden por nombre es a "
               "propósito, terminá la línea con `<!-- ia-ok: motivo -->`. No se guardó el cambio.")
    return "\n".join(out)


def config_dir() -> Path:
    return Path(os.environ.get("CLAUDE_CONFIG_DIR") or (Path.home() / ".claude"))


def leer(p: Path) -> str:
    try:
        if p.stat().st_size > LEER_MAX:
            return ""
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _palabras(t: str) -> list:
    t = unicodedata.normalize("NFD", t.lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.findall(r"[a-z0-9ñ_.\-/]+", t.replace("ñ", "n"))


def _codigos(t: str) -> set:
    return {c.strip().lower() for c in re.findall(r"`([^`\n]{3,80})`", t) if c.strip().lower() not in CODIGO_COMUN}


class Unidad:
    __slots__ = ("archivo", "linea", "texto", "huella", "shingles", "codigos", "eco")

    def __init__(self, archivo: str, linea: int, texto: str):
        self.archivo, self.linea, self.texto = archivo, linea, texto
        pal = _palabras(texto)
        self.huella = hashlib.sha1(" ".join(pal).encode()).hexdigest()[:12]
        self.shingles = {" ".join(pal[i:i + SHINGLE]) for i in range(max(0, len(pal) - SHINGLE + 1))}
        self.codigos = _codigos(texto)
        self.eco = bool(ECO.search(texto))

    def resumen(self, n: int = 90) -> str:
        t = re.sub(r"\s+", " ", re.sub(r"^[|\s>*#\-\d.]+", "", self.texto)).strip()
        return t[:n] + ("…" if len(t) > n else "")



def unidades(texto: str, archivo: str, sin_bloque_metodo: bool = False) -> list:
    """Parte el texto en filas de tabla, ítems de lista y párrafos con al menos MIN_PALABRAS palabras."""
    if sin_bloque_metodo and INI in texto and FIN in texto:
        a, b = texto.index(INI), texto.index(FIN) + len(FIN)
        texto = texto[:a] + ("\n" * texto[a:b].count("\n")) + texto[b:]      # conserva la numeración de líneas
    out, buf, ini, fence = [], [], 0, False

    def cerrar():
        nonlocal buf
        if buf:
            u = " ".join(x.strip() for x in buf)
            if len(_palabras(u)) >= MIN_PALABRAS:
                out.append(Unidad(archivo, ini, u))
        buf = []

    for i, linea in enumerate(texto.splitlines(), 1):
        s = linea.strip()
        if s.startswith("```"):
            cerrar()
            fence = not fence
            continue
        if fence or not s or s.startswith("#") or s.startswith(">") or s.lower().startswith("disparador:") or re.fullmatch(r"[|\-: ]+", s):
            cerrar()
            continue
        nueva = s.startswith("|") or bool(re.match(r"(?:[-*+]|\d+[.)])\s", s))
        if nueva or not buf:
            cerrar()
            ini = i
        buf.append(s)
        if s.startswith("|"):
            cerrar()
    cerrar()
    return out


def misma_regla(a: Unidad, b: Unidad) -> bool:
    if a.huella == b.huella:
        return True
    if a.eco or b.eco:
        return False
    ch, gr = (a, b) if len(a.shingles) <= len(b.shingles) else (b, a)
    if ch.shingles and len(ch.shingles & gr.shingles) / len(ch.shingles) >= UMBRAL_TEXTO:
        return True
    ch, gr = (a, b) if len(a.codigos) <= len(b.codigos) else (b, a)
    comun = ch.codigos & gr.codigos
    return len(comun) >= MIN_CODIGO and len(comun) / len(ch.codigos) >= UMBRAL_CODIGO


def archivos_de_reglas(cfg: Path, cwd: Path) -> list:
    """Lo que carga una sesión como reglas: ficha global (+ MANDAMIENTOS), rules/ globales, y el CLAUDE.md y rules/ del proyecto."""
    vistos, out = set(), []

    def sumar(p: Path):
        try:
            r = p.resolve()
        except OSError:
            return
        if r not in vistos and p.is_file():
            vistos.add(r)
            out.append(p)

    for n in ("CLAUDE.md", "MANDAMIENTOS.md"):
        sumar(cfg / n)
    for p in sorted((cfg / "rules").rglob("*.md")) if (cfg / "rules").is_dir() else []:
        sumar(p)
    d, home = cwd, Path.home()
    for _ in range(8):
        sumar(d / "CLAUDE.md")
        sumar(d / ".claude" / "CLAUDE.md")
        if (d / ".claude" / "rules").is_dir():
            for p in sorted((d / ".claude" / "rules").rglob("*.md")):
                sumar(p)
        if d == home or d.parent == d or (d / ".git").exists():
            break
        d = d.parent
    return out


def es_archivo_de_reglas(p: Path, cfg: Path) -> bool:
    n = p.name
    if n in ("CLAUDE.md", "MANDAMIENTOS.md", "REGLAS-DEL-METODO.md"):
        return True
    return n.endswith(".md") and "rules" in p.parts and (".claude" in p.parts or cfg in p.parents)


def corpus(archivos: list, cfg: Path) -> list:
    """Unidades de todos los archivos. El bloque del método de la ficha cuenta como un solo hogar: se lee entero aparte."""
    out = []
    for a in archivos:
        t = leer(a)
        if a.resolve() == (cfg / "CLAUDE.md").resolve() and INI in t:
            out += unidades(t, str(a), sin_bloque_metodo=True)
            a_, b_ = t.index(INI), t.index(FIN) + len(FIN) if FIN in t else len(t)
            bloque = ("\n" * t[:a_].count("\n")) + t[a_:b_]
            out += unidades(bloque, str(a) + " (reglas del método)")
        else:
            out += unidades(t, str(a))
    return out


def hallar(us: list) -> list:
    """Pares (a, b) de unidades de lugares distintos que son la misma regla. Usa un índice de tramos para no comparar todo con todo."""
    idx, cand = {}, set()
    for i, u in enumerate(us):
        for s in u.shingles:
            idx.setdefault(s, []).append(i)
    for lst in idx.values():
        if 1 < len(lst) <= 6:
            for x in range(len(lst)):
                for y in range(x + 1, len(lst)):
                    cand.add((lst[x], lst[y]))
    cod = {}
    for i, u in enumerate(us):
        for c in u.codigos:
            cod.setdefault(c, []).append(i)
    for lst in cod.values():
        if 1 < len(lst) <= 6:
            for x in range(len(lst)):
                for y in range(x + 1, len(lst)):
                    cand.add((lst[x], lst[y]))
    return [(us[i], us[j]) for i, j in sorted(cand) if us[i].archivo != us[j].archivo and misma_regla(us[i], us[j])]


def clave(a: Unidad, b: Unidad) -> str:
    return "|".join(sorted((a.huella + "@" + a.archivo, b.huella + "@" + b.archivo)))


def ruta_base(cfg: Path) -> Path:
    return cfg / "metodo" / "reglas-unicas-base.json"


def cargar_base(cfg: Path):
    try:
        return set(json.loads(ruta_base(cfg).read_text(encoding="utf-8")).get("conocidos", []))
    except (OSError, ValueError):
        return None


def leer_peso_base(cfg: Path):
    try:
        return int(json.loads(ruta_base(cfg).read_text(encoding="utf-8")).get("peso") or 0) or None
    except (OSError, ValueError, TypeError):
        return None


def guardar_base(cfg: Path, pares: list, peso=None) -> None:
    ruta = ruta_base(cfg)
    peso = peso if peso is not None else leer_peso_base(cfg)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    tmp = ruta.with_suffix(".tmp")
    tmp.write_text(json.dumps({"conocidos": sorted(clave(a, b) for a, b in pares), "peso": peso,
                               "nota": "duplicados que ya existían; no frenan. Se resuelven dejando un puntero en uno de los dos lados."},
                              ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    os.replace(tmp, ruta)


def corto(ruta: str) -> str:
    return ruta.replace(str(Path.home()), "~")


def mensaje(nuevas: list) -> str:
    out = ["Una regla vive en UN solo lugar, y esta ya está escrita en otro archivo:"]
    for u, otra in nuevas[:3]:
        out.append(f"  • «{u.resumen()}»\n    ya está en {corto(otra.archivo)}:{otra.linea}")
    out.append("Qué hacer: dejá la regla completa en un solo archivo y en el otro una línea corta con puntero "
               "(«→ ver <archivo> §…»). Si de verdad tiene que estar en los dos, terminá la línea con "
               "`<!-- eco: motivo -->`. No se guardó el cambio.")
    return "\n".join(out)


def nuevo_texto(h: dict, actual: str) -> str:
    ti = h.get("tool_input") or {}
    if "content" in ti:
        return ti["content"]
    if "old_string" in ti and "new_string" in ti:
        o, n = ti["old_string"], ti["new_string"]
        return actual.replace(o, n) if ti.get("replace_all") else actual.replace(o, n, 1)
    return actual


def cmd_hook() -> int:
    if os.environ.get("REGLAS_UNICAS_OFF") == "1":
        return 0
    try:
        h = json.loads(sys.stdin.read() or "{}")
        ti = h.get("tool_input") or {}
        if h.get("tool_name") not in ("Write", "Edit", "MultiEdit") or not ti.get("file_path"):
            return 0
        cfg = config_dir()
        p = Path(os.path.expanduser(ti["file_path"]))
        if not es_archivo_de_reglas(p, cfg):
            return 0
        actual = leer(p) if p.is_file() else ""
        propuesto = nuevo_texto(h, actual)
        if propuesto == actual:
            return 0
        previas_l = {_normal(x) for x in actual.splitlines()}
        nuevas_ia = [(n, l) for n, l in ordenes_ia(propuesto) if l not in previas_l]
        if nuevas_ia:
            sys.stderr.write(mensaje_ordenes(nuevas_ia) + "\n")
            return 2
        cwd = Path(h.get("cwd") or os.getcwd())
        otros = [a for a in archivos_de_reglas(cfg, cwd) if a.resolve() != p.resolve()]
        base = cargar_base(cfg)
        if base is None:                       # primera vez: lo que ya había queda como conocido, sin pedirle nada al usuario
            try:
                guardar_base(cfg, hallar(corpus(otros + ([p] if p.is_file() else []), cfg)))
            except OSError:
                pass
            base = cargar_base(cfg) or set()
        previas = {u.huella for u in unidades(actual, str(p))}
        nuevas_u = [u for u in unidades(propuesto, str(p)) if u.huella not in previas and not u.eco]
        if not nuevas_u:
            return 0
        resto = corpus(otros, cfg)
        choques = []
        for u in nuevas_u:
            for o in resto:
                if o.archivo != u.archivo and clave(u, o) not in base and misma_regla(u, o):
                    choques.append((u, o))
                    break
        if not choques:
            return 0
        sys.stderr.write(mensaje(choques) + "\n")
        return 2
    except Exception:                          # un error propio nunca frena el trabajo
        return 0


def cmd_revisar(todo: bool, cwd: Path) -> int:
    cfg = config_dir()
    pares = hallar(corpus(archivos_de_reglas(cfg, cwd), cfg))
    base = cargar_base(cfg) or set()
    nuevos = [(a, b) for a, b in pares if clave(a, b) not in base]
    ver = pares if todo else nuevos
    print(f"Reglas repetidas: {len(pares)} en total · {len(pares) - len(nuevos)} conocidas · {len(nuevos)} nuevas")
    for a, b in ver:
        marca = "nueva" if clave(a, b) not in base else "conocida"
        print(f"  [{marca}] «{a.resumen(70)}»\n      {corto(a.archivo)}:{a.linea}  ↔  {corto(b.archivo)}:{b.linea}")
    if nuevos:
        print(f"✗ {len(nuevos)} regla(s) repetida(s) sin resolver: dejá la completa en un solo archivo y un puntero en el otro")
        return 1
    print("✓ ninguna regla repetida nueva")
    return 0


PESO_MAX = 40_000          # una ficha + reglas que cargan siempre y pasan de esto: la pregunta es qué bloque creció
CRECE = 1.10               # o crecieron más de 10 % desde la primera vez que se midió
SEMANA = 7 * 86400


def peso_fijo(cfg: Path) -> int:
    """Bytes de lo que carga TODA sesión: la ficha global y las reglas globales sin `paths:`."""
    total = 0
    for a in [cfg / "CLAUDE.md"] + (sorted((cfg / "rules").rglob("*.md")) if (cfg / "rules").is_dir() else []):
        t = leer(a)
        if a.name == "CLAUDE.md" or not re.search(r"^paths\s*:", t.split("\n---", 1)[0], re.M):
            total += len(t.encode("utf-8"))
    return total


def rutas_rotas(cfg: Path) -> list:
    """Rutas «~/…» que la ficha global y sus reglas citan entre comillas invertidas y no existen."""
    rotas = []
    for a in [cfg / "CLAUDE.md"] + (sorted((cfg / "rules").rglob("*.md")) if (cfg / "rules").is_dir() else []):
        for ruta in re.findall(r"`(~/[^`\s*<>{}\[\]$|&…]+)`", leer(a)):
            r = ruta.rstrip(".,;:)")
            if "AAAA" in r or "YYYY" in r:
                continue
            if not Path(os.path.expanduser(r)).exists() and r not in rotas:
                rotas.append(r)
    return rotas


def cmd_aviso(cwd: Path, forzar: bool) -> int:
    """Una vez por semana, en silencio salvo que haya algo: reglas repetidas nuevas, ficha que engorda, rutas rotas. Solo lee."""
    try:
        cfg = config_dir()
        marca = cfg / "metodo" / "reglas-unicas.visto"
        if not forzar and marca.is_file() and time.time() - marca.stat().st_mtime < SEMANA:
            return 0
        pares = hallar(corpus(archivos_de_reglas(cfg, cwd), cfg))
        peso = peso_fijo(cfg)
        base = cargar_base(cfg)
        if base is None:                                   # primera vez: se anota cómo está hoy y no se avisa nada
            guardar_base(cfg, pares, peso)
            base = cargar_base(cfg) or set()
        nuevas = [(a, b) for a, b in pares if clave(a, b) not in base]
        partes = []
        if nuevas:
            partes.append(f"{len(nuevas)} regla(s) escrita(s) en dos lugares (la primera: «{nuevas[0][0].resumen(60)}» en {corto(nuevas[0][0].archivo)} y {corto(nuevas[0][1].archivo)})")
        b0 = leer_peso_base(cfg)
        if peso > PESO_MAX or (b0 and peso > b0 * CRECE):
            partes.append(f"tu ficha y reglas de entrada pesan {peso // 1000} KB" + (f" (eran {b0 // 1000} KB)" if b0 else ""))
        rotas = rutas_rotas(cfg)
        if rotas:
            partes.append(f"cita(n) una ruta que ya no existe: {rotas[0]}" + (f" y {len(rotas) - 1} más" if len(rotas) > 1 else ""))
        marca.parent.mkdir(parents=True, exist_ok=True)
        marca.write_text(time.strftime("%Y-%m-%d"), encoding="utf-8")
        if partes:
            print("Reglas: " + "; ".join(partes) + ". Dejá cada regla en un solo archivo (con un puntero en el otro). Detalle: reglas-unicas.py revisar")
    except Exception:
        pass
    return 0


def cmd_ordenes(archivos: list, cwd: Path) -> int:
    """Lista las órdenes por nombre de IA. Sin archivos: los de reglas de esta computadora. Sale 1 si encuentra alguna."""
    cfg = config_dir()
    rutas = [Path(a) for a in archivos] if archivos else archivos_de_reglas(cfg, cwd)
    n = 0
    for r in rutas:
        for num, l in ordenes_ia(leer(r)):
            n += 1
            print(f"  {corto(str(r))}:{num}  «{l[:110]}»")
    if n:
        print(f"✗ {n} orden(es) por nombre de IA en reglas: el orden de las IA lo da el radar, no la regla")
        return 1
    print("✓ ninguna orden por nombre de IA en las reglas")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="una regla, un solo hogar")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("hook")
    p = sub.add_parser("revisar")
    p.add_argument("--todo", action="store_true")
    p.add_argument("--cwd", type=Path, default=Path.cwd())
    p = sub.add_parser("aviso")
    p.add_argument("--forzar", action="store_true", help="ignorar el «una vez por semana»")
    p.add_argument("--cwd", type=Path, default=Path.cwd())
    p = sub.add_parser("ordenes")
    p.add_argument("--archivos", nargs="*", default=[])
    p.add_argument("--cwd", type=Path, default=Path.cwd())
    p = sub.add_parser("base")
    p.add_argument("--cwd", type=Path, default=Path.cwd())
    a = ap.parse_args(argv)
    if a.cmd == "hook":
        return cmd_hook()
    if a.cmd == "revisar":
        return cmd_revisar(a.todo, a.cwd)
    if a.cmd == "aviso":
        return cmd_aviso(a.cwd, a.forzar)
    if a.cmd == "ordenes":
        return cmd_ordenes(a.archivos, a.cwd)
    if a.cmd == "base":
        cfg = config_dir()
        pares = hallar(corpus(archivos_de_reglas(cfg, a.cwd), cfg))
        guardar_base(cfg, pares, peso_fijo(cfg))
        print(f"Base fijada: {len(pares)} repetida(s) conocida(s) ✓")
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
