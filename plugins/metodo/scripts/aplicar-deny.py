#!/usr/bin/env python3
"""aplicar-deny.py — agrega a <config de Claude>/settings.json las reglas `permissions.deny` que impiden que las herramientas de Claude lean o editen los lugares
donde se guardan las llaves (SSH, nube, GitHub, llavero…). Las MISMAS reglas que al-dia.sh aplica en Mac con plutil; este programa existe para Windows, donde
al-dia.sh no corre (F4 del security check 0.35.0). Funciona en cualquier sistema.
Disparador: automático, una vez por día, desde al-dia-auto.sh (solo en Windows; en Mac lo hace al-dia.sh).
Solo agrega lo que falta; no toca nada más del archivo (el formato JSON puede cambiar de sangría). Copia previa en settings.json.antes-arneses (una sola vez),
escritura en un archivo temporal que reemplaza al original solo si queda JSON válido. Si settings.json no se puede leer como JSON, NO lo toca.
Uso: aplicar-deny.py [--lista]   (--lista imprime las reglas y sale)"""
import json
import os
import sys
import tempfile

for _flujo in (sys.stdout, sys.stderr):
    try:
        _flujo.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Mismas rutas que la lista de al-dia.sh (hay una prueba que compara las dos). ~/Library/Keychains/** es solo de macOS.
RUTAS = ['~/.ssh/**', '~/.aws/**', '~/.config/gh/**', '~/.config/gh-claude/**', '~/.config/git/credentials', '~/.git-credentials',
         '~/.netrc', '~/.npmrc', '~/.pypirc', '~/.docker/config.json', '~/.kube/**', '~/.config/gcloud/**', '~/.modal.toml',
         '~/.notebooklm/**', '~/Library/Keychains/**', '~/.claude/.credentials.json', '~/.claude.json', '~/.claude.json.backup*',
         '~/.claude/backups/**']
SOLO_MAC = {'~/Library/Keychains/**'}
ACCIONES = ('Read', 'Edit')


def reglas(es_mac):
    return [f"{a}({r})" for r in RUTAS if es_mac or r not in SOLO_MAC for a in ACCIONES]


def main(argv):
    es_mac = sys.platform == "darwin"
    if "--lista" in argv:
        print("\n".join(reglas(True)))
        return 0
    base = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude")
    ruta = os.path.join(base, "settings.json")
    try:
        if os.path.exists(ruta):
            with open(ruta, encoding="utf-8") as f:
                datos = json.load(f)
        else:
            datos = {}
        if not isinstance(datos, dict):
            raise ValueError("no es un objeto JSON")
        permisos = datos.setdefault("permissions", {})
        if not isinstance(permisos, dict):
            raise ValueError("permissions no es un objeto")
        deny = permisos.setdefault("deny", [])
        if not isinstance(deny, list):
            raise ValueError("permissions.deny no es una lista")
    except (OSError, ValueError) as e:
        print(f"✗ No toqué {ruta}: no se puede leer como JSON ({type(e).__name__}). Falta: bloqueo de las carpetas de llaves")
        return 1
    faltan = [r for r in reglas(es_mac) if r not in deny]
    if not faltan:
        return 0
    tmp = None
    try:
        os.makedirs(base, exist_ok=True)
        previa = ruta + ".antes-arneses"
        if os.path.exists(ruta) and not os.path.exists(previa):
            with open(ruta, "rb") as f, open(previa, "wb") as g:
                g.write(f.read())
        deny.extend(faltan)
        fd, tmp = tempfile.mkstemp(dir=base, prefix=".settings.", suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(datos, f, indent=2, ensure_ascii=False)
            f.write("\n")
        with open(tmp, encoding="utf-8") as f:   # se vuelve a leer antes de reemplazar
            if not set(faltan) <= set(json.load(f)["permissions"]["deny"]):
                raise ValueError("la copia no quedó completa")
        os.replace(tmp, ruta)
    except (OSError, ValueError, KeyError) as e:
        if tmp and os.path.exists(tmp):
            os.remove(tmp)
        print(f"✗ No pude agregar el bloqueo de las carpetas de llaves ({type(e).__name__}); {ruta} no se modificó")
        return 1
    print(f"· Agregué {len(faltan)} reglas a {ruta} para que Claude no pueda leer ni editar tus carpetas de llaves (SSH, nube, GitHub…). Copia en settings.json.antes-arneses")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
