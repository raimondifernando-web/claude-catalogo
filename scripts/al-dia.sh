#!/bin/bash
# al-dia.sh — deja el Claude Code del cliente al día con el catálogo de Fernando, de una sola vez.
# Se puede correr siempre: lo que ya está bien no se toca. No borra nada del usuario.
# Termina con UNA línea: «Todo al día ✓» o qué falta (para mandar captura).
# Todo va dentro de main(): si la descarga se corta a mitad, no se ejecuta nada.
main() {
set -u
local CAT=claude-catalogo REPO=raimondifernando-web/claude-catalogo
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

# 7. Una sola línea final
echo
if [ ${#falta[@]} -eq 0 ]; then
  echo "Todo al día ✓  ($okp paquetes · $R reglas del método · actualización automática prendida)"
  echo "Cerrá Claude Code y volvé a abrirlo para que tome lo nuevo."
else
  printf 'Falta: %s ✗\n' "$(printf '%s, ' "${falta[@]}" | sed 's/, $//')"
  echo "Mandale esta captura a Fernando. No lo repitas hasta que te conteste."
fi
}
main "$@"
