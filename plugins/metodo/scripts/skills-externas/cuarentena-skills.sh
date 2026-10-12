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
CLI=${SKILLS_CLI:-$CLI_DIR/node_modules/skills}
if [ "$DRY" = 1 ] && [ ! -d "$CLI" ]; then
  echo "[dry-run] el CLI skills@$VERSION_FIJA todavía no está instalado: se instalaría (npm ci --ignore-scripts) en $CLI_DIR · traería «${FUENTE}» (skill: $SKILL) a una cuarentena temporal y la auditaría. No toqué la red ni el disco."
  exit 0
fi
[ -f "$CLI/package.json" ] || { echo "Falta: el CLI no está instalado en $CLI ✗"; exit 1; }
v=$(node -p "require('$CLI/package.json').version")
[ "$v" = "$VERSION_FIJA" ] || { echo "Falta: skills@$v instalada, la fijada es $VERSION_FIJA ✗"; exit 1; }
h=$(node -p "require('$CLI_DIR/package-lock.json').packages['node_modules/skills'].integrity")
[ "$h" = "$HASH_FIJO" ] || { echo "Falta: el hash de skills@$VERSION_FIJA no coincide con el verificado ✗"; exit 1; }
if [ "$DRY" = 1 ]; then
  echo "[dry-run] CLI skills@$v con hash verificado ✓ · traería «${FUENTE}» (skill: $SKILL) a una cuarentena temporal y la auditaría. No toqué la red ni el disco."
  exit 0
fi
NODO=$(command -v node); GIT=$(command -v git)
# sha del repo ANTES de traer (el CLI no lo expone; su computedHash es de contenido): solo si la fuente es de GitHub
REPO_URL=""
if [[ "$FUENTE" =~ ^https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/?$ ]]; then REPO_URL="${FUENTE%/}"; REPO_URL="${REPO_URL%.git}.git"
elif [[ "$FUENTE" =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ ]] && [ ! -e "$FUENTE" ]; then REPO_URL="https://github.com/$FUENTE.git"
fi
sha_remoto() { [ -n "$REPO_URL" ] && env -i PATH="$(dirname "$GIT"):/usr/bin:/bin" GIT_TERMINAL_PROMPT=0 GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null "$GIT" ls-remote "$REPO_URL" HEAD 2>/dev/null | cut -f1 || true; }
SHA_ANTES=$(sha_remoto)
Q=$(mktemp -d "${TMPDIR:-/tmp}/cuarentena-skills.XXXXXX"); mkdir "$Q/home" "$Q/work" "$Q/tmp"
t0=$(date +%s)
cd "$Q/work"
# entorno vacío: el CLI no ve ninguna variable tuya (ni claves, ni GITHUB_TOKEN); git sin configuración global
env -i PATH="$(dirname "$NODO"):$(dirname "$GIT"):/usr/bin:/bin" HOME="$Q/home" TMPDIR="$Q/tmp" DISABLE_TELEMETRY=1 NO_COLOR=1 CI=1 \
    GIT_TERMINAL_PROMPT=0 GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null GIT_LFS_SKIP_SMUDGE=1 \
    node "$CLI/bin/cli.mjs" add "$FUENTE" -s "$SKILL" -a claude-code --copy -y --json > "$Q/instalacion.json" 2> "$Q/instalacion.err" \
    || { echo "El CLI falló ✗"; tail -5 "$Q/instalacion.err"; echo "(cuarentena: $Q)"; exit 2; }
[ -d "$Q/work/.claude/skills" ] || { echo "No trajo nada ✗ (cuarentena: $Q)"; exit 2; }
SHA_DESPUES=$(sha_remoto)
echo "Traídas a cuarentena en $(( $(date +%s) - t0 )) s: $(ls "$Q/work/.claude/skills" | wc -l | tr -d ' ') skill(s) → $Q"
{
  if [ -n "$SHA_ANTES" ] && [ "$SHA_ANTES" = "$SHA_DESPUES" ]; then echo "<!-- sha fijado: $SHA_ANTES (git ls-remote HEAD antes y después coinciden) -->"; printf '**sha del repo (para CATALOGO origen:):** `%s`\n' "$SHA_ANTES"
  elif [ -n "$REPO_URL" ]; then printf '**sha del repo: NO se pudo fijar** (antes=`%s` · después=`%s`): repetir la traída antes de promover.\n' "${SHA_ANTES:-?}" "${SHA_DESPUES:-?}"
  else echo "**sha del repo:** fuente que no es de GitHub; fijar a mano antes de promover."; fi
  echo
  python3 -I "$AQUI/cuarentena_auditar.py" "$Q/work"
  python3 -I "$AQUI/barrido.py" "$Q/work/.claude/skills"
} > "$Q/informe.md"
echo "Informe: $Q/informe.md  ·  Nada se instaló en ~/.claude ni ~/.agents."
echo "Siguiente paso (SOLO con el OK de la persona en el chat): leer lo marcado y promover a mano (ver la skill buscar-skill-externa, paso 7). Borrar cuarentena: rm -r $Q"
