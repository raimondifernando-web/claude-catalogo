#!/bin/bash
# cuarentena-skills <fuente> [skill|'*'] [--dry-run] — trae skills de la comunidad a una CUARENTENA descartable y las audita. NO promueve nada.
# Disparador: lo corre la skill buscar-skill-externa cuando la persona elige un candidato (C: a pedido; B: la sugiere herramientas-para).
#             La promoción a ~/.claude es un paso aparte (M) y lo decide la persona con un OK en el chat.
# Qué hace: CLI oficial `skills` con versión y hash fijos · HOME, TMPDIR y carpeta de trabajo temporales · entorno vacío (sin claves)
#           · telemetría apagada SOLO en este comando · instala con --copy (sin symlinks) en <cuarentena>/work/.claude/skills
#           · auditor + controles extra + barrido de texto + comparación con lo que ya tenemos → informe.md.
#           El ecosistema vivo (~/.claude, ~/.agents) no se toca.
# --dry-run: valida versión/hash del CLI y muestra qué haría, sin tocar la red ni crear nada.
set -euo pipefail
DRY=0; ARGS=()
for a in "$@"; do case "$a" in --dry-run) DRY=1 ;; *) ARGS+=("$a") ;; esac; done
FUENTE=${ARGS[0]:?Uso: cuarentena-skills <owner/repo|ruta|url> [skill|*] [--dry-run]}; SKILL=${ARGS[1]:-*}
AQUI=$(cd "$(dirname "$0")" && pwd)
# Windows (Git Bash / MSYS / Cygwin): el aislamiento de esta cuarentena (env -i, rutas, TMPDIR) todavía NO está probado ahí. Falla claro, no a medias.
case "${CUARENTENA_SO:-$(uname -s 2>/dev/null)}" in
  MINGW*|MSYS*|CYGWIN*) echo "Falta: traer una skill a la cuarentena todavía no está probado en Windows ✗ (buscar sí funciona: skills-buscar.py). Pedile a quien te acompaña que la traiga desde una Mac o Linux."; exit 1 ;;
esac
VERSION_FIJA=1.7.2
HASH_FIJO='sha512-j+GzyF/oNahsjjjup6y3lJpFkC1lQjIkf4kAMXICA1hboBqi0fAGXAGoE4x9FRZiP1br/YE9+L3/Tqq6PIAe0A=='
# El CLI vive junto a este script (cli/) si ya está instalado ahí (Tech); si no, se instala UNA vez, con scripts apagados, en <config de Claude>/metodo/cuarentena-cli
# (la carpeta de un plugin se reemplaza en cada actualización). Siempre contra package-lock.json: npm verifica el hash.
CLI_DIR="$AQUI/cli"
if [ ! -d "$CLI_DIR/node_modules/skills" ]; then
  CLI_DIR="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/metodo/cuarentena-cli"
  if [ ! -d "$CLI_DIR/node_modules/skills" ] && [ "$DRY" = 0 ]; then
    command -v npm >/dev/null 2>&1 || { echo "Falta: Node.js (npm) para traer el instalador de skills ✗ (instalá Node y repetí)"; exit 1; }
    mkdir -p "$CLI_DIR" && cp "$AQUI/cli/package.json" "$AQUI/cli/package-lock.json" "$CLI_DIR/" \
      && (cd "$CLI_DIR" && npm ci --ignore-scripts --no-audit --no-fund >/dev/null 2>&1) \
      || { echo "Falta: no pude instalar el CLI skills@$VERSION_FIJA en $CLI_DIR ✗"; exit 1; }
  fi
fi
CLI="$CLI_DIR/node_modules/skills"   # F12: sin override por variable de entorno (SKILLS_CLI permitía apuntar a otro CLI sin que se revisara su hash)
if [ "$DRY" = 1 ] && [ ! -d "$CLI" ]; then
  echo "[dry-run] el CLI skills@$VERSION_FIJA todavía no está instalado: se instalaría (npm ci --ignore-scripts) en $CLI_DIR · traería «${FUENTE}» (skill: $SKILL) a una cuarentena temporal y la auditaría. No toqué la red ni el disco."
  exit 0
fi
[ -f "$CLI/package.json" ] || { echo "Falta: el CLI no está instalado en $CLI ✗"; exit 1; }
v=$(node -p "require('$CLI/package.json').version")
[ "$v" = "$VERSION_FIJA" ] || { echo "Falta: skills@$v instalada, la fijada es $VERSION_FIJA ✗"; exit 1; }
h=$(node -p "require('$CLI_DIR/package-lock.json').packages['node_modules/skills'].integrity")
[ "$h" = "$HASH_FIJO" ] || { echo "Falta: el hash de skills@$VERSION_FIJA no coincide con el verificado ✗"; exit 1; }
# F12: el hash de arriba es el ANOTADO en package-lock.json, no el del contenido instalado. La primera vez (justo después de `npm ci`, que sí verifica la integridad) se guarda la
# huella de todo node_modules; en cada corrida se vuelve a calcular: si algo se modificó después, se frena. (Un CLI que ya estaba instalado sin huella la recibe en su primera corrida.)
arbol_sha() { python3 -I -c 'import hashlib,os,sys
h=hashlib.sha256()
for d,ds,fs in os.walk(sys.argv[1]):
    ds.sort()
    for f in sorted(fs):
        p=os.path.join(d,f)
        if f==".package-lock.json" and d==sys.argv[1]: continue
        h.update(os.path.relpath(p,sys.argv[1]).encode()+b"\0")
        h.update((os.readlink(p).encode() if os.path.islink(p) else open(p,"rb").read())+b"\0")
print(h.hexdigest())' "$1"; }
MARCA="$CLI_DIR/.arbol-sha256"
HUELLA=$(arbol_sha "$CLI_DIR/node_modules") || { echo "Falta: no pude calcular la huella del CLI instalado ✗"; exit 1; }
if [ -f "$MARCA" ]; then
  [ "$(cat "$MARCA")" = "$HUELLA" ] || { echo "Falta: el CLI instalado en $CLI_DIR cambió desde que se verificó ✗ (borrá esa carpeta para reinstalarlo desde package-lock.json)"; exit 1; }
elif [ "$DRY" = 0 ]; then
  printf '%s\n' "$HUELLA" > "$MARCA" 2>/dev/null || true
fi
if [ "$DRY" = 1 ]; then
  echo "[dry-run] CLI skills@$v con hash verificado ✓ · traería «${FUENTE}» (skill: $SKILL) a una cuarentena temporal y la auditaría. No toqué la red ni el disco."
  exit 0
fi
NODO=$(command -v node); GIT=$(command -v git)
# --- Qué fuente es (mismas formas que acepta el CLI): owner/repo · owner/repo/subcarpeta · owner/repo@skill · github:… · gitlab:… · URL de GitHub (con /tree/<rama>/<subcarpeta>)
#     · URL https/ssh de git · carpeta local · cualquiera con #rama. REPO_URL/REF/SUB/ATSK se calculan acá; el sha del repo se lee del clon auditado
#     (L-4: `git rev-parse HEAD` antes de borrar .git; ls-remote podía dar otro commit que el que se trajo).
REPO_URL=""; REF=""; SUB=""; ATSK=""; OWNER_REPO=""; LOCAL=0
GH_BASE="${CUARENTENA_GITHUB_BASE:-https://github.com}"   # solo las pruebas lo cambian (para clonar de un repo local sin red)
F="$FUENTE"
if [ -e "$F" ] || [ -L "$F" ]; then LOCAL=1
else
  if [[ "$F" == *'#'* ]]; then REF="${F#*#}"; F="${F%%#*}"; [[ "$REF" == *'@'* ]] && { ATSK="${REF#*@}"; REF="${REF%%@*}"; }; fi
  case "$F" in github:*) F="${F#github:}" ;; gitlab:*) F="https://gitlab.com/${F#gitlab:}" ;; esac
  if [[ "$F" =~ ^https://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)/?$ ]] || [[ "$F" =~ ^https://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)/(tree|blob)/([^/]+)(/(.+))?$ ]]; then
    OWNER_REPO="${BASH_REMATCH[1]}/${BASH_REMATCH[2]%.git}"
    [[ "$F" == */tree/* || "$F" == */blob/* ]] && { REF="${BASH_REMATCH[4]}"; SUB="${BASH_REMATCH[6]:-}"; }
  elif [[ "$F" =~ ^([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)@([^/]+)$ ]]; then OWNER_REPO="${BASH_REMATCH[1]}/${BASH_REMATCH[2]}"; ATSK="${BASH_REMATCH[3]}"
  elif [[ "$F" =~ ^([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)(/(.+))?$ ]]; then OWNER_REPO="${BASH_REMATCH[1]}/${BASH_REMATCH[2]}"; SUB="${BASH_REMATCH[4]:-}"
  fi
  if [ -n "$OWNER_REPO" ]; then REPO_URL="$GH_BASE/${OWNER_REPO%.git}.git"
  elif [[ "$F" =~ ^(https://|ssh://|git@) ]]; then REPO_URL="$F"
  fi
fi
[ -z "$SUB" ] || case "/$SUB/" in */../*|//*) echo "Subcarpeta no válida ✗ ($SUB)"; exit 2 ;; esac
[[ "$REF" == -* ]] && { echo "Rama/etiqueta no válida ✗"; exit 2; }
[ "$SKILL" = '*' ] && [ -n "$ATSK" ] && SKILL="$ATSK"
SHA_CLON=""
Q=$(mktemp -d "${TMPDIR:-/tmp}/cuarentena-skills.XXXXXX"); mkdir "$Q/home" "$Q/work" "$Q/tmp"
t0=$(date +%s)
# F1 (security check 0.35.0): el CLI copia con --copy DESREFERENCIANDO los enlaces simbólicos (traería archivos de tu máquina). Por eso el repo se baja ACÁ
# (git clone sin --recurse-submodules / cp -RP sin seguir enlaces: vale igual para fuentes remotas y locales), se BORRAN todos los enlaces simbólicos
# (quedan listados en enlaces.txt) y recién entonces el CLI lee esa copia local, que ya no tiene ninguno que seguir.
ENL="$Q/enlaces.txt"; : > "$ENL"
if [ "$LOCAL" = 1 ]; then
  { [ ! -L "$FUENTE" ] && [ -d "$FUENTE" ]; } || { echo "La fuente tiene que ser una carpeta real (no un enlace simbólico) ✗ (cuarentena: $Q)"; exit 2; }
  mkdir "$Q/src" && cp -RP "$FUENTE/." "$Q/src/" || { echo "No pude copiar la fuente ✗ (cuarentena: $Q)"; exit 2; }
elif [ -n "$REPO_URL" ]; then
  PERMITIR_FILE=never; [ -n "${CUARENTENA_GITHUB_BASE:-}" ] && PERMITIR_FILE=always
  env -i PATH="$(dirname "$GIT"):/usr/bin:/bin" HOME="$Q/home" GIT_TERMINAL_PROMPT=0 GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null GIT_LFS_SKIP_SMUDGE=1 \
      "$GIT" -c protocol.file.allow=$PERMITIR_FILE clone --quiet --depth 1 ${REF:+--branch "$REF"} "$REPO_URL" "$Q/src" 2> "$Q/clone.err" \
    || { echo "No pude bajar la fuente ✗"; tail -3 "$Q/clone.err"; echo "(cuarentena: $Q)"; exit 2; }
else
  echo "Fuente no reconocida ✗ (usar owner/repo, owner/repo@skill, una URL de git o una carpeta local)"; exit 2
fi
if [ -n "$REPO_URL" ]; then
  SHA_CLON=$(env -i PATH="$(dirname "$GIT"):/usr/bin:/bin" GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null "$GIT" -C "$Q/src" rev-parse HEAD 2>/dev/null) || SHA_CLON=""
  [[ "$SHA_CLON" =~ ^[0-9a-f]{40}$ ]] || SHA_CLON=""
fi
rm -rf "$Q/src/.git"
# L-5: una línea JSON por enlace (un nombre con salto de línea no rompe la lista); se borran sin seguirlos.
python3 -I - "$Q/src" "$ENL" <<'PY' || { echo "No pude revisar los enlaces de la fuente ✗ (cuarentena: $Q)"; exit 2; }
import json, os, sys
raiz, salida = sys.argv[1], sys.argv[2]
with open(salida, "w", encoding="utf-8") as f:
    for d, dirs, files in os.walk(raiz):            # no entra en carpetas que son enlaces (followlinks=False)
        for n in sorted(dirs + files):
            p = os.path.join(d, n)
            if os.path.islink(p):
                f.write(json.dumps({"ruta": os.path.relpath(p, raiz), "destino": os.readlink(p)}, ensure_ascii=True) + "\n")
                os.unlink(p)
        dirs[:] = [n for n in dirs if os.path.isdir(os.path.join(d, n))]
PY
export CUARENTENA_ENLACES="$ENL"
[ -s "$ENL" ] && echo "Aviso: la fuente traía $(wc -l < "$ENL" | tr -d ' ') enlace(s) simbólico(s); se borraron antes de copiar (lista en el informe)."
RAIZ="$Q/src${SUB:+/$SUB}"
[ -d "$RAIZ" ] || { echo "La subcarpeta «$SUB» no existe en la fuente ✗ (cuarentena: $Q)"; exit 2; }
cd "$Q/work"
# entorno vacío: el CLI no ve ninguna variable tuya (ni claves, ni GITHUB_TOKEN); git sin configuración global
env -i PATH="$(dirname "$NODO"):$(dirname "$GIT"):/usr/bin:/bin" HOME="$Q/home" TMPDIR="$Q/tmp" DISABLE_TELEMETRY=1 NO_COLOR=1 CI=1 \
    GIT_TERMINAL_PROMPT=0 GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null GIT_LFS_SKIP_SMUDGE=1 \
    node "$CLI/bin/cli.mjs" add "$RAIZ" -s "$SKILL" -a claude-code --copy -y --json > "$Q/instalacion.json" 2> "$Q/instalacion.err" \
    || { echo "El CLI falló ✗"; tail -5 "$Q/instalacion.err"; echo "(cuarentena: $Q)"; exit 2; }
[ -d "$Q/work/.claude/skills" ] || { echo "No trajo nada ✗ (cuarentena: $Q)"; exit 2; }
echo "Traídas a cuarentena en $(( $(date +%s) - t0 )) s: $(ls "$Q/work/.claude/skills" | wc -l | tr -d ' ') skill(s) → $Q"
{
  if [ -n "$SHA_CLON" ]; then echo "<!-- sha fijado: $SHA_CLON (git rev-parse HEAD del clon auditado) -->"; printf '**sha del repo (para CATALOGO origen:):** `%s`\n' "$SHA_CLON"
  elif [ -n "$REPO_URL" ]; then echo "**sha del repo: NO se pudo leer del clon**: repetir la traída antes de promover."
  else echo "**sha del repo:** fuente que no es de GitHub; fijar a mano antes de promover."; fi
  echo
  CUARENTENA_FUENTE="$OWNER_REPO" python3 -I "$AQUI/cuarentena_auditar.py" "$Q/work"
  python3 -I "$AQUI/barrido.py" "$Q/work/.claude/skills"
} > "$Q/informe.md"
echo "Informe: $Q/informe.md  ·  Nada se instaló en ~/.claude ni ~/.agents."
echo "Siguiente paso (SOLO con el OK de la persona en el chat): leer lo marcado y promover a mano (ver la skill buscar-skill-externa, paso 7). Borrar cuarentena: rm -r $Q"
