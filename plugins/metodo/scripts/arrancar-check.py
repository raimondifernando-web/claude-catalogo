#!/usr/bin/env python3
"""arrancar-check — comprobación mecánica del arranque de sesión (/metodo:arrancar).

SOLO LEE: no escribe nada ni muestra valores de archivos de claves. Una línea por paso (✓/✗) y cierra con
«Arranque completo ✓» o «Falta: … ✗» (exit 0/1). Lo que el script no puede hacer (numerar la sesión, archivar la
serie anterior) sale como línea MANUAL para que la sesión tenga que reportarlo.

Uso: arrancar-check.py [carpeta]   (default: la carpeta actual)
"""
import os
import re
import subprocess
import sys

CONFIG = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude")
cwd = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.getcwd()
faltan = []


def git(*args):
    try:
        r = subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True, timeout=15)
        return r.stdout.strip() if r.returncode == 0 else None
    except Exception:
        return None


def linea(ok, texto, falta=None):
    print(("✓ " if ok else "✗ ") + texto)
    if not ok:
        faltan.append(falta or texto)


# (a) REANUDAR.md (raíz de la carpeta de trabajo; también se acepta .claude/prompts/) y fecha de cierre
reanudar = next((p for p in (os.path.join(cwd, "REANUDAR.md"), os.path.join(cwd, ".claude", "prompts", "REANUDAR.md"))
                 if os.path.isfile(p)), None)
texto = ""
if reanudar:
    texto = open(reanudar, encoding="utf-8", errors="replace").read()
    m = re.match(r"\s*<!--\s*cierre\s+(\d{4}-\d{2}-\d{2}\S*)", texto)
    if m:
        linea(True, f"REANUDAR.md presente · cierre {m.group(1)}")
    else:
        linea(False, "REANUDAR.md sin la línea «<!-- cierre YYYY-MM-DD-tema …»", "REANUDAR sin fecha de cierre")
else:
    print("- No hay REANUDAR.md en esta carpeta: arrancás «sin contrato» (paso 1 de /metodo:arrancar)")

# (b) copia / rama contra lo declarado
rama = git("branch", "--show-current")
top = git("rev-parse", "--show-toplevel")
if rama is None:
    print(f"✓ Carpeta fuera de git ({cwd}): copia y rama no aplican")
elif texto:
    decl = re.findall(r"(?:Copia|Worktree):?\s*(\S+)\s*·\s*Rama:?\s*(\S+)", texto)
    coincide = any(
        os.path.realpath(os.path.abspath(os.path.expanduser(w.strip("`")))) == os.path.realpath(top or cwd)
        and r.strip("`") == rama
        for w, r in decl
    )
    if coincide:
        linea(True, f"Copia y rama coinciden con lo declarado ({rama})")
    elif not decl:
        linea(True, f"El REANUDAR no declara Copia/Rama; estás en {rama} (ok si es carpeta única)")
    else:
        linea(False, f"Estás en {top} · {rama}; el REANUDAR declara {decl}",
              "copia/rama no coinciden: PARAR y avisar a quien te acompaña (regla 11)")
else:
    print(f"- Rama {rama}: sin REANUDAR no hay contra qué comparar")

# (c) estado git
if rama is not None:
    st = git("status", "--short")
    n = len(st.splitlines()) if st else 0
    print(f"✓ git status: {n} archivo(s) con cambios sin guardar")
    otras = [l for l in (git("worktree", "list") or "").splitlines() if l.strip()]
    if len(otras) > 1:
        print(f"• Hay {len(otras)} copias de este repo abiertas (git worktree list): confirmá que esta es la tuya (regla 11)")

# (d) método instalado y última regla
base = os.path.join(CONFIG, "plugins", "cache", "claude-catalogo", "metodo")
vers = []
if os.path.isdir(base):
    vers = sorted((d for d in os.listdir(base) if re.fullmatch(r"\d+(\.\d+)*", d)),
                  key=lambda v: [int(x) for x in v.split(".")])
if vers:
    reglas = os.path.join(base, vers[-1], "templates", "REGLAS-DEL-METODO.md")
    try:
        nums = [int(x) for x in re.findall(r"^(\d+)\.\s", open(reglas, encoding="utf-8").read(), re.M)]
        linea(bool(nums), f"metodo {vers[-1]} instalado · última regla numerada: {max(nums) if nums else '?'}",
              "REGLAS-DEL-METODO sin reglas")
    except OSError:
        linea(False, f"metodo {vers[-1]}: falta templates/REGLAS-DEL-METODO.md", "REGLAS-DEL-METODO.md ausente")
else:
    print("- metodo no figura en el caché de plugins (instalación de otro tipo): no se mide la última regla")

# (e) A VERIFICAR: solo listarlo
if texto:
    m = re.search(r"^A VERIFICAR[^\n:]*:\s*(.*?)(?=^\S[^\n]*:|\Z)", texto, re.M | re.S)
    if m and m.group(1).strip():
        print("• PENDIENTE DE VERIFICAR POR LA SESIÓN (el script no lo ejecuta):")
        for l in m.group(1).strip().splitlines():
            print("    " + l.strip())
    else:
        print("• A VERIFICAR: el REANUDAR no trae bloque")

# Pasos que solo puede hacer la sesión
print("• MANUAL (paso 3 bis): si tenés las herramientas de sesiones de la app, numerar el título «<base> N+1» y "
      "ofrecer archivar la serie anterior; si no, «no aplica»")
print("• MANUAL (modelo): mirá el próximo paso, compará con el ruteo que mostró el radar al abrir y decile a quien te "
      "acompaña en UNA línea: «este paso pide X, estás en Y». Si no coinciden, proponé cambiar ANTES de empezar "
      "(después se pierde la caché)")

print()
if faltan:
    print("Falta: " + " · ".join(faltan) + " ✗")
    sys.exit(1)
print("Arranque completo ✓ (más los ítems MANUAL y A VERIFICAR, que reporta la sesión)")
