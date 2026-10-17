#!/usr/bin/env python3
"""Control del catálogo: ninguna pieza nueva puede exigirle un paso manual al cliente ni quedar fuera de Windows.

Disparador: encadenado — lo corre scripts/controles.sh (check obligatorio `controles` de cada PR a `main`). También a mano:
python3 scripts/pasos-manuales.py   (desde la raíz del catálogo; --raiz <carpeta> para probarlo en otra)

Regla de la casa: el cliente no corre nada a mano; todo se aplica solo, en Mac y en Windows. Dos cosas se frenan:
  A. En la ÚLTIMA entrada de cada plugins/*/CHANGELOG.md (lo que sale ahora), frases que le piden algo a la persona:
     «hay que correr / encender / prender / activar…», órdenes sueltas («corré», «pegá», «ejecutá», «encendé»…) y piezas que
     «vienen apagadas» o «apagadas por defecto». Si es legítimo (credenciales, decisión de la persona, algo de una sola vez),
     se deja por escrito en esa misma línea: «[manual-ok: motivo]».
  B. En plugins/*/hooks/hooks.json, comandos que usan herramientas de una sola plataforma (xcode-select, /usr/bin/python3,
     osascript, plutil, launchctl, pbcopy, afplay) y no traen la alternativa de Windows (`py -3`). Lo que ya estaba así antes
     de este control figura en scripts/pasos-manuales-excepciones.txt, con motivo; una entrada nueva ahí es zona sensible.

Solo LEE archivos del repo; sin red, sin POSIX (pathlib). Salida: 0 = limpio · 1 = hay hallazgos (los lista) · 2 = error.
"""
import argparse
import json
import re
import sys
from pathlib import Path

# A. frases que piden un paso manual (minúsculas; se busca sin distinguir mayúsculas)
FRASES = [
    (re.compile(r"hay que (?:correr|ejecutar|encender|prender|activar|pegar|instalar)"), "«hay que …»"),
    (re.compile(r"(?<![\w-])(?:corré|ejecutá|pegá|encendé|prendé|activá|instalá|escribí)(?![\w-])"), "una orden a la persona"),
    (re.compile(r"(?:viene|vienen)\s+\**\s*(?:apagad[oa]s?|desactivad[oa]s?)"), "viene apagado"),
    (re.compile(r"apagad[oa]s?\s+por\s+defecto|desactivad[oa]s?\s+por\s+defecto"), "apagado por defecto"),
]
MARCA_OK = re.compile(r"\[manual-ok:\s*\S[^\]]*\]", re.I)
# B. herramientas de una sola plataforma
SOLO_MAC = ("xcode-select", "/usr/bin/python3", "osascript", "plutil", "launchctl", "pbcopy", "pbpaste", "afplay", "defaults write")
ALTERNATIVA_WINDOWS = ("py -3", "py.exe")
EXCEPCIONES = "scripts/pasos-manuales-excepciones.txt"


def ultima_entrada(texto: str) -> list:
    """(número de línea, línea) de la primera sección `## ` del CHANGELOG, sin bloques de código."""
    res, dentro, en_codigo = [], False, False
    for n, linea in enumerate(texto.splitlines(), 1):
        if linea.startswith("## "):
            if dentro:
                break
            dentro = True
            continue
        if linea.lstrip().startswith("```"):
            en_codigo = not en_codigo
            continue
        if dentro and not en_codigo:
            res.append((n, linea))
    return res


def revisar_changelogs(raiz: Path) -> list:
    hallazgos = []
    for ch in sorted((raiz / "plugins").glob("*/CHANGELOG.md")):
        try:
            texto = ch.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            hallazgos.append(f"{ch.relative_to(raiz).as_posix()}: no se pudo leer ({e.__class__.__name__})")
            continue
        for n, linea in ultima_entrada(texto):
            if MARCA_OK.search(linea):
                continue
            bajo = re.sub(r"`[^`\n]*`", "", linea.lower())   # lo que va entre comillas invertidas es un comando citado, no una orden
            for patron, que in FRASES:
                if patron.search(bajo):
                    hallazgos.append(f"{ch.relative_to(raiz).as_posix()}:{n}: {que} → «{linea.strip()[:110]}» "
                                     "(el cliente no corre nada a mano: que se aplique solo, o dejá «[manual-ok: motivo]» si es legítimo)")
                    break
    return hallazgos


def cargar_excepciones(raiz: Path) -> set:
    ruta = raiz / EXCEPCIONES
    claves = set()
    if ruta.is_file():
        for linea in ruta.read_text(encoding="utf-8", errors="replace").splitlines():
            if linea.strip() and not linea.lstrip().startswith("#") and "=>" in linea:
                clave, _, motivo = linea.partition("=>")
                if motivo.strip():            # sin motivo escrito no vale
                    claves.add(clave.strip())
    return claves


def comandos_de_hooks(datos) -> list:
    """(evento, comando) de todos los hooks de tipo command de un hooks.json."""
    res = []
    hooks = datos.get("hooks", {}) if isinstance(datos, dict) else {}
    if not isinstance(hooks, dict):
        return res
    for evento, grupos in hooks.items():
        for grupo in grupos if isinstance(grupos, list) else []:
            for h in grupo.get("hooks", []) if isinstance(grupo, dict) else []:
                if isinstance(h, dict) and isinstance(h.get("command"), str):
                    res.append((evento, h["command"]))
    return res


def revisar_hooks(raiz: Path) -> list:
    hallazgos, excep = [], cargar_excepciones(raiz)
    for hj in sorted((raiz / "plugins").glob("*/hooks/hooks.json")):
        plugin = hj.parts[hj.parts.index("plugins") + 1] if "plugins" in hj.parts else hj.parent.parent.name
        try:
            datos = json.loads(hj.read_text(encoding="utf-8", errors="replace"))
        except ValueError:
            hallazgos.append(f"{hj.relative_to(raiz).as_posix()}: JSON inválido")
            continue
        for evento, cmd in comandos_de_hooks(datos):
            if any(a in cmd for a in ALTERNATIVA_WINDOWS):
                continue
            script = re.search(r"([\w.-]+\.(?:py|sh))", cmd)
            for herr in SOLO_MAC:
                if herr in cmd:
                    clave = f"{plugin}|{evento}|{herr}|{script.group(1) if script else '-'}"
                    if clave not in excep:
                        hallazgos.append(f"{hj.relative_to(raiz).as_posix()}: el hook de {evento} usa «{herr}» (solo Mac) sin alternativa para "
                                         f"Windows (`py -3`) → clave de excepción si es a propósito: {clave}")
    return hallazgos


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--raiz", default=str(Path(__file__).resolve().parent.parent), help="raíz del catálogo")
    args = ap.parse_args(argv)
    raiz = Path(args.raiz).resolve()
    if not (raiz / "plugins").is_dir():
        print(f"ERROR: {raiz} no tiene carpeta plugins/", file=sys.stderr)
        return 2
    hallazgos = revisar_changelogs(raiz) + revisar_hooks(raiz)
    for h in hallazgos:
        print("✗ " + h)
    print("pasos manuales: limpio ✓" if not hallazgos else f"pasos manuales: {len(hallazgos)} hallazgo(s)")
    return 1 if hallazgos else 0


if __name__ == "__main__":
    sys.exit(main())
