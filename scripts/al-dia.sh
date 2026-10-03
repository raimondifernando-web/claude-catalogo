#!/bin/bash
# al-dia.sh — deja el Claude Code del cliente al día con el catálogo de Fernando, de una sola vez.
# Se puede correr siempre: lo que ya está bien no se toca. No borra nada del usuario.
# Termina con UNA línea: «Todo al día ✓» o qué falta (para mandar captura).
# Todo va dentro de main(): si la descarga se corta a mitad, no se ejecuta nada.
main() {
set -u
local CAT=claude-catalogo REPO=raimondifernando-web/claude-catalogo
local BUZON=""
while [ $# -gt 0 ]; do case "$1" in --buzon) BUZON="${2:-}"; shift; [ $# -gt 0 ] && shift;; *) shift;; esac; done
if [ -n "$BUZON" ] && ! [[ $BUZON =~ ^[A-Za-z0-9-]+/[A-Za-z0-9_-][A-Za-z0-9._-]*$ ]]; then echo "✗ El nombre del buzón no es válido. Mandale esta captura a Fernando."; return 1; fi
local falta=() paquetes=()
N=""; T=""
trap 'rm -f "${N:-}" "${T:-}"' EXIT

echo "Poniendo Claude al día… (puede tardar unos minutos)"

# 1. Que la Terminal encuentre claude
if ! command -v claude >/dev/null 2>&1 && [ -x "$HOME/.local/bin/claude" ]; then
  grep -qsF '$HOME/.local/bin' ~/.zshrc || echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
  export PATH="$HOME/.local/bin:$PATH"
fi
if ! command -v claude >/dev/null 2>&1; then
  echo "✗ No encuentro Claude Code en esta Mac. Mandale esta captura a Fernando."; return 1
fi

# 2. El catálogo: agregarlo si falta y traer su versión nueva
claude plugin marketplace list 2>/dev/null | grep -qF "$CAT" || claude plugin marketplace add "$REPO" >/dev/null 2>&1
claude plugin marketplace update "$CAT" >/dev/null 2>&1 || falta+=("no pude traer la versión nueva del catálogo")
local M="$HOME/.claude/plugins/marketplaces/$CAT"
[ -f "$M/.claude-plugin/marketplace.json" ] || { echo "✗ No pude bajar el catálogo de Fernando. Mandale esta captura."; return 1; }

# 3. Actualización automática del catálogo (con copia de la configuración, una sola vez)
local S="$HOME/.claude/settings.json"
[ -f "$S" ] && { [ -f "$S.antes-al-dia" ] || cp "$S" "$S.antes-al-dia"; }
plutil -replace "extraKnownMarketplaces.$CAT.autoUpdate" -bool true "$S" 2>/dev/null
[ "$(plutil -extract "extraKnownMarketplaces.$CAT.autoUpdate" raw "$S" 2>/dev/null)" = "true" ] || falta+=("actualización automática")

# 4. Conexión con GitHub para los paquetes que vienen directo de GitHub (solo si hace falta)
if ! ssh -T -o BatchMode=yes -o ConnectTimeout=10 git@github.com 2>&1 | grep -q "successfully authenticated"; then
  if ! git config --global --get-all url."https://github.com/".insteadOf 2>/dev/null | grep -qxF "git@github.com:"; then
    git config --global --add url."https://github.com/".insteadOf "git@github.com:"
    echo "· Ajusté la conexión con GitHub (HTTPS). Para deshacerlo: git config --global --unset-all url.https://github.com/.insteadOf"
  fi
fi

# 5. Todos los paquetes del catálogo: instalar los que falten, actualizar los demás
local i=0 n p lista okp=0
while n=$(plutil -extract "plugins.$i.name" raw "$M/.claude-plugin/marketplace.json" 2>/dev/null); do
  if [[ $n =~ ^[a-z0-9][a-z0-9-]*$ ]]; then paquetes+=("$n"); else falta+=("nombre de paquete inválido"); fi
  i=$((i+1))
done
[ ${#paquetes[@]} -gt 0 ] || falta+=("la lista de paquetes vino vacía")
lista=$(claude plugin list 2>/dev/null)
for p in ${paquetes[@]+"${paquetes[@]}"}; do
  if printf '%s\n' "$lista" | grep -qE "❯ $p@$CAT[[:space:]]*$"; then claude plugin update "$p@$CAT" >/dev/null 2>&1
  else claude plugin install "$p@$CAT" >/dev/null 2>&1; fi
done
lista=$(claude plugin list 2>/dev/null)
for p in ${paquetes[@]+"${paquetes[@]}"}; do
  if printf '%s\n' "$lista" | grep -A3 -E "❯ $p@$CAT[[:space:]]*$" | grep -q "✔ enabled"; then okp=$((okp+1)); else falta+=("$p"); fi
done

# 5b. Herramientas de Apple (traen Python) y librerías de las skills de documentos e imágenes, con versiones fijas
#     markitdown pide Python 3.10 o más: va con uv (Astral), en su propio Python, sin contraseña.
local PY=/usr/bin/python3 UVV=0.12.19 MDV=0.1.8 UV="$HOME/.local/bin/uv"
grep -qsF '$HOME/.local/bin' ~/.zshrc || echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
case ":$PATH:" in *":$HOME/.local/bin:"*) ;; *) export PATH="$HOME/.local/bin:$PATH";; esac
if ! xcode-select -p >/dev/null 2>&1; then
  xcode-select --install >/dev/null 2>&1
  falta+=("⟳ herramientas de Apple: en la ventana que se abrió tocá Instalar y esperá a que termine")
else
  "$PY" -m pip install --user --quiet --disable-pip-version-check --no-warn-script-location --only-binary=:all: \
    pandas==2.3.3 openpyxl==3.1.5 requests==2.32.5 openai==2.48.0 >/dev/null 2>&1
  "$PY" -c 'import importlib.metadata as m,sys; q={"pandas":"2.3.3","openpyxl":"3.1.5","requests":"2.32.5","openai":"2.48.0"}; sys.exit(any(m.version(k)!=v for k,v in q.items()))' 2>/dev/null \
    || falta+=("librerías de Python")
  [ -x "$UV" ] || curl -LsSf "https://astral.sh/uv/$UVV/install.sh" | env UV_NO_MODIFY_PATH=1 sh >/dev/null 2>&1
  if [ -x "$UV" ]; then
    "$UV" tool list 2>/dev/null | grep -qx "markitdown v$MDV" || "$UV" tool install --force --quiet --python 3.12 "markitdown[all]==$MDV" >/dev/null 2>&1
    "$UV" tool list 2>/dev/null | grep -qx "markitdown v$MDV" || falta+=("markitdown")
  else falta+=("markitdown (no pude instalar uv)"); fi
fi

# 5e. Node.js en tu carpeta de usuario (sin contraseña): descarga oficial de nodejs.org, versión fija, huella verificada
local NODEV=v24.21.0 NA ND NT NSHA NPMG="$HOME/.local/share/npm-global"
case "$(uname -m)" in
  arm64) NA=arm64; NSHA=bed7eea5325e1108f32ce5228ddd6a5f0f08a499ee42aa7442aea583702f6057;;
  *)     NA=x64;   NSHA=1462cb3b3046b815cf8ea436d3da450ec1a9f11dac7e5a46b0ada5305d7e8097;;
esac
ND="$HOME/.local/share/node-$NODEV-darwin-$NA"
if ! command -v node >/dev/null 2>&1; then
  if [ ! -x "$ND/bin/node" ]; then
    NT=$(mktemp -d)
    if curl -fsSL -o "$NT/n.tgz" "https://nodejs.org/dist/$NODEV/node-$NODEV-darwin-$NA.tar.gz" \
       && [ "$(shasum -a 256 "$NT/n.tgz" | cut -d' ' -f1)" = "$NSHA" ]; then
      mkdir -p "$HOME/.local/share" && tar -xzf "$NT/n.tgz" -C "$HOME/.local/share"
    fi
    rm -rf "$NT"
  fi
  if [ -x "$ND/bin/node" ]; then
    mkdir -p "$HOME/.local/bin"
    for b in node npm npx; do ln -sf "$ND/bin/$b" "$HOME/.local/bin/$b"; done
  fi
fi
command -v node >/dev/null 2>&1 || falta+=("Node.js (no pude instalarlo solo)")

# 5f. Codex de OpenAI (la misma versión que usa Fernando). Lo que le pases sale a OpenAI con TU cuenta de ChatGPT.
local CXV=0.158.0
if command -v node >/dev/null 2>&1; then
  if [ "$(codex --version 2>/dev/null)" != "codex-cli $CXV" ]; then
    npm install -g --silent --prefix "$NPMG" "@openai/codex@$CXV" >/dev/null 2>&1
    if [ -x "$NPMG/bin/codex" ] && { [ ! -e "$HOME/.local/bin/codex" ] || [ "$(readlink "$HOME/.local/bin/codex")" = "$NPMG/bin/codex" ]; }; then
      ln -sf "$NPMG/bin/codex" "$HOME/.local/bin/codex"
    fi
  fi
  if [ "$(codex --version 2>/dev/null)" = "codex-cli $CXV" ]; then
    codex login status >/dev/null 2>&1 || echo "· Codex instalado. Para usarlo, una vez: en la Terminal escribí  codex login  (con tu cuenta de ChatGPT). Lo que le pases sale a OpenAI."
  else falta+=("Codex"); fi
fi

# 5c. Datos de uso de HyperFrames: apagados (solo esa variable; nunca una general como DO_NOT_TRACK)
if [ -f "$S" ]; then
  plutil -extract env json -o /dev/null "$S" >/dev/null 2>&1 || plutil -insert env -dictionary "$S" 2>/dev/null
  plutil -replace env.HYPERFRAMES_NO_TELEMETRY -string 1 "$S" 2>/dev/null
  if plutil -extract env.DO_NOT_TRACK raw "$S" >/dev/null 2>&1; then
    plutil -remove env.DO_NOT_TRACK "$S" && echo "· Quité DO_NOT_TRACK de tu configuración (cortaba Remote Control). Copia en settings.json.antes-al-dia"
  fi
  [ "$(plutil -extract env.HYPERFRAMES_NO_TELEMETRY raw "$S" 2>/dev/null)" = "1" ] || falta+=("apagar datos de uso de HyperFrames")
fi

# 5d. Figma oficial de Anthropic (la conexión con tu cuenta se hace aparte, con /mcp)
claude plugin marketplace list 2>/dev/null | grep -qF claude-plugins-official || claude plugin marketplace add anthropics/claude-plugins-official >/dev/null 2>&1
claude plugin list 2>/dev/null | grep -qE "❯ figma@claude-plugins-official[[:space:]]*$" || claude plugin install figma@claude-plugins-official >/dev/null 2>&1
claude plugin list 2>/dev/null | grep -A3 -E "❯ figma@claude-plugins-official[[:space:]]*$" | grep -q "✔ enabled" || falta+=("figma")

# 6. Reglas del método en la ficha global (entre marcas; lo tuyo no se toca)
local F="$M/plugins/metodo/templates/REGLAS-DEL-METODO.md" G="$HOME/.claude/CLAUDE.md"
local I='<!-- reglas-del-metodo:inicio -->' E='<!-- reglas-del-metodo:fin -->' R="?" C L Z
if [ -f "$F" ]; then
  N=$(mktemp); T=$(mktemp)
  { echo "$I"; sed -n '1p' "$F"; sed -n '5,$p' "$F"; echo "$E"; } > "$N"
  R=$(sed -n '1p' "$F" | grep -oE '[0-9]+' | head -1); C="$G.antes-reglas-$(date +%Y%m%d-%H%M%S)"
  local ni=0 ne=0
  [ -f "$G" ] && { ni=$(grep -cxF "$I" "$G"); ne=$(grep -cxF "$E" "$G"); }
  if [ "$ni" -gt 0 ] || [ "$ne" -gt 0 ]; then
    if [ "$ni" -ne 1 ] || [ "$ne" -ne 1 ]; then
      falta+=("reglas del método (las marcas de tu ficha están incompletas: no toqué nada)")
    elif [ "$(awk -v i="$I" -v e="$E" '$0==i{f=1} f{print} $0==e{f=0}' "$G")" != "$(cat "$N")" ]; then
      if cp "$G" "$C" && awk -v i="$I" -v e="$E" -v nf="$N" '$0==i{while((getline l<nf)>0)print l; f=1; next} f&&$0==e{f=0; next} !f' "$C" > "$T" && [ -s "$T" ]; then
        cat "$T" > "$G"
      else falta+=("reglas del método (no pude guardar: no toqué nada)"); fi
    fi
  elif L=$(grep -nE '^# Las [0-9]+ reglas del método' "$G" 2>/dev/null | head -1 | cut -d: -f1); [ -n "$L" ]; then
    Z=$(awk -v s="$L" 'NR>s && index($0,"Lo corre quien verifica, no el mismo agente que hizo la copia."){print NR; exit}' "$G")
    if [ -z "$Z" ] || awk -v a="$L" -v b="$Z" 'NR>a && NR<=b' "$G" | grep -v '^$' | grep -vxF -f <(grep -v '^$' "$N") | grep -q .; then
      falta+=("reglas del método (tu ficha tiene algo distinto: no toqué nada)")
    elif cp "$G" "$C" && { awk -v a="$L" 'NR<a' "$C"; cat "$N"; awk -v b="$Z" 'NR>b' "$C"; } > "$T" && [ -s "$T" ]; then
      cat "$T" > "$G"
    else falta+=("reglas del método (no pude guardar: no toqué nada)"); fi
  else
    mkdir -p "$HOME/.claude"; { echo; cat "$N"; } >> "$G"
  fi
else falta+=("reglas del método (no llegó el paquete metodo)"); fi

# 6b. Buzón con Fernando (solo si el comando trae --buzon dueño/repo)
if [ -n "$BUZON" ]; then
  local BD="$HOME/${BUZON#*/}" BP
  [ -d "$BD/.git" ] || GIT_TERMINAL_PROMPT=0 git clone -q "https://github.com/$BUZON.git" "$BD" >/dev/null 2>&1
  if [ -d "$BD/.git" ] && [ "$(git -C "$BD" config --get remote.origin.url 2>/dev/null)" != "https://github.com/$BUZON.git" ]; then
    falta+=("buzón: la carpeta ~/${BUZON#*/} ya existe y es otro repositorio")
  elif [ -d "$BD/.git" ]; then
    BP=$(find "$HOME/.claude/plugins/cache/claude-catalogo/metodo" -name buzon.py 2>/dev/null | sort -V | tail -1)
    if [ -n "$BP" ] && GIT_TERMINAL_PROMPT=0 /usr/bin/python3 "$BP" configurar --carpeta "$BD" --yo cliente >/dev/null 2>&1; then :
    else falta+=("configurar el buzón"); fi
  else
    falta+=("⟳ buzón: aceptá en GitHub el repositorio ${BUZON#*/} (te llegó un mail), sumalo a tu llave e invitá a Fernando")
  fi
fi

# 7. Una sola línea final
echo
if [ ${#falta[@]} -eq 0 ]; then
  echo "Todo al día ✓  ($okp paquetes · $R reglas del método · Python, Node y Codex · actualización automática prendida)"
  echo "Cerrá Claude Code y volvé a abrirlo para que tome lo nuevo."
else
  local x rep=1
  for x in "${falta[@]}"; do [ "${x#⟳}" != "$x" ] || rep=0; done
  printf 'Falta: %s ✗\n' "$(printf '%s, ' "${falta[@]}" | sed 's/⟳ //g; s/, $//')"
  if [ $rep -eq 1 ]; then echo "Cuando lo hagas, pegá este mismo comando otra vez."
  else echo "Mandale esta captura a Fernando. No lo repitas hasta que te conteste."; fi
fi
}
main "$@"
