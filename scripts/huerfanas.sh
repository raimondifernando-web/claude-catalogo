#!/usr/bin/env bash
# huerfanas.sh — ¿qué carpetas tuyas no están respaldadas en ningún lado?
# Uso:  bash <(curl -fsSL https://raw.githubusercontent.com/raimondifernando-web/claude-catalogo/main/scripts/huerfanas.sh) [carpeta-extra ...]
#   o:  bash ~/.claude/plugins/marketplaces/claude-catalogo/scripts/huerfanas.sh [carpeta-extra ...]
# Revisa las carpetas de primer nivel de ~/Documents, ~/Desktop, ~/Documents/<Empresa>-Claude y las que le pases.
# Una carpeta es HUÉRFANA si (a) no es un repo git con remoto y (b) no está dentro de una nube activa.
# NUNCA mueve, borra ni instala nada. No abre archivos: si ve un archivo con nombre de clave, dice el nombre, jamás el contenido.
set -u

# ---------- nubes activas ----------
ICLOUD="$HOME/Library/Mobile Documents/com~apple~CloudDocs"
real() { (cd -P "$1" 2>/dev/null && pwd -P); }
same_dir() { [ -d "$1" ] && [ -d "$2" ] && [ "$(real "$1")" = "$(real "$2")" ]; }
# Escritorio y Documentos en iCloud: por enlace real o por la preferencia de Finder
icloud_pref() { [ -d "$ICLOUD" ] && [ "$(defaults read com.apple.finder "$1" 2>/dev/null)" = "1" ]; }
nubes=()
[ -d "$ICLOUD" ] && nubes+=("$ICLOUD")
for c in "$HOME"/Library/CloudStorage/*/; do [ -d "$c" ] && nubes+=("${c%/}"); done
DOCS_EN_ICLOUD=0; DESK_EN_ICLOUD=0
{ same_dir "$HOME/Documents" "$ICLOUD/Documents" || icloud_pref FXICloudDriveDocuments; } && DOCS_EN_ICLOUD=1
{ same_dir "$HOME/Desktop" "$ICLOUD/Desktop" || icloud_pref FXICloudDriveDesktop; } && DESK_EN_ICLOUD=1

en_nube() { # ¿la ruta está dentro de alguna nube?
  local p="$1"
  case "$p" in "$HOME/Documents"/*) [ $DOCS_EN_ICLOUD = 1 ] && return 0;; "$HOME/Desktop"/*) [ $DESK_EN_ICLOUD = 1 ] && return 0;; esac
  for n in "${nubes[@]:-}"; do [ -n "$n" ] && case "$p" in "$n"/*) return 0;; esac; done
  return 1
}
repo_con_remoto() { git -C "$1" rev-parse --show-toplevel >/dev/null 2>&1 && [ -n "$(git -C "$1" remote 2>/dev/null)" ]; }
repo_sin_remoto() { git -C "$1" rev-parse --show-toplevel >/dev/null 2>&1 && [ -z "$(git -C "$1" remote 2>/dev/null)" ]; }

# ---------- cajón sugerido (heurísticas simples, decide una persona) ----------
sugerir() {
  local d="$1" nombre; nombre=$(basename "$d" | tr 'A-Z' 'a-z')
  local total docs datos
  total=$(find "$d" -type f -not -name .DS_Store 2>/dev/null | head -2000 | wc -l | tr -d ' ')
  docs=$(find "$d" -type f \( -iname '*.pdf' -o -iname '*.docx' -o -iname '*.doc' -o -iname '*.pptx' -o -iname '*.key' -o -iname '*.pages' -o -iname '*.numbers' \) 2>/dev/null | head -2000 | wc -l | tr -d ' ')
  datos=$(find "$d" -type f \( -iname '*.csv' -o -iname '*.json' -o -iname '*.xlsx' -o -iname '*.xls' -o -iname '*.db' -o -iname '*.sqlite' \) 2>/dev/null | head -2000 | wc -l | tr -d ' ')
  case "$nombre" in *backup*|*copia*|*old*|*viejo*|*_archivo*|*archive*|*.bak*) echo "derivado/copia|borrar (si ya existe en otro lado)"; return;; esac
  if [ -d "$d/.git" ]; then echo "trabajo de Claude|repo privado (conectar remoto)"; return; fi
  if [ "$total" -eq 0 ]; then echo "vacía|borrar"; return; fi
  if [ "$datos" -gt 0 ] && [ $((datos*2)) -ge "$total" ]; then echo "datos crudos|nube, carpeta datos/ (nunca git)"; return; fi
  if [ "$docs" -gt 0 ] && [ $((docs*2)) -ge "$total" ]; then echo "documentos|nube de la empresa"; return; fi
  if [ -f "$d/CLAUDE.md" ] || [ -f "$d/README.md" ] || find "$d" -maxdepth 2 -type f \( -iname '*.md' -o -iname '*.py' -o -iname '*.js' -o -iname '*.html' \) 2>/dev/null | head -1 | grep -q .; then echo "trabajo de Claude|repo privado"; return; fi
  echo "documentos|nube de la empresa"
}
posibles_secretos() { # solo nombres, nunca contenido
  find "$1" -maxdepth 3 -type f \( -name '.env' -o -name '.env.*' -o -iname '*.pem' -o -iname 'id_rsa*' -o -iname 'id_ed25519*' -o -iname '*credential*' -o -iname '*contrase*' -o -iname '*password*' -o -iname '*apikey*' -o -iname '*api_key*' -o -iname '*token*' -o -iname '*secret*' \) -not -path '*/node_modules/*' -not -path '*/.git/*' -not -iname '*.py' -not -iname '*.js' -not -iname '*.ts' -not -iname '*.md' -not -iname '*.html' 2>/dev/null | head -5
}

# ---------- raíces a revisar ----------
raices=("$HOME/Documents" "$HOME/Desktop")
for e in "$HOME"/Documents/*-Claude "$HOME"/Documents/*-claude; do [ -d "$e" ] && raices+=("$e"); done
for a in "$@"; do [ -d "$a" ] && raices+=("${a%/}"); done

echo
echo "Chequeo de carpetas huérfanas — $(date '+%Y-%m-%d %H:%M') · usuario: $(whoami)"
echo "Nubes activas detectadas:"
[ -d "$ICLOUD" ] && echo "  ☁️  iCloud Drive$( [ $DOCS_EN_ICLOUD = 1 ] && printf ' (Documentos sincronizados)')$( [ $DESK_EN_ICLOUD = 1 ] && printf ' (Escritorio sincronizado)')"
for c in "$HOME"/Library/CloudStorage/*/; do [ -d "$c" ] && echo "  ☁️  $(basename "$c")"; done
[ ${#nubes[@]} -eq 0 ] && echo "  (ninguna — todo lo que no esté en un repo con remoto está huérfano)"
echo

huerfanas=0; revisadas=0; secretos=0
for raiz in "${raices[@]}"; do
  [ -d "$raiz" ] || continue
  echo "── $raiz"
  for d in "$raiz"/*/; do
    d=${d%/}; [ -d "$d" ] || continue
    nombre=$(basename "$d"); case "$nombre" in .*|node_modules|Library) continue;; esac
    [ -L "$d" ] && continue
    revisadas=$((revisadas+1))
    tam=$(du -sh "$d" 2>/dev/null | cut -f1)
    if repo_con_remoto "$d"; then
      printf '  ✅ %-34s %6s  repo con remoto\n' "$nombre" "$tam"
    elif en_nube "$d"; then
      printf '  ✅ %-34s %6s  en nube\n' "$nombre" "$tam"
    else
      huerfanas=$((huerfanas+1))
      IFS='|' read -r cajon propuesta <<<"$(sugerir "$d")"
      estado="nada"; repo_sin_remoto "$d" && estado="repo SIN remoto (no es respaldo)"
      printf '  ❌ %-34s %6s  %s\n' "$nombre" "$tam" "$estado"
      printf '        cajón sugerido: %s → %s\n' "$cajon" "$propuesta"
    fi
    # Claves fuera de lugar: se revisa SIEMPRE, también en repos y en nube (una clave en la nube sigue estando mal)
    s=$(posibles_secretos "$d")
    if [ -n "$s" ]; then secretos=$((secretos+1)); echo "        ⚠️  posible clave fuera de lugar (solo el nombre): $(echo "$s" | sed "s|$d/||" | tr '\n' ' ')"; fi
  done
done
echo
echo "Revisadas: $revisadas carpetas."
if [ "$huerfanas" -eq 0 ]; then echo "0 carpetas huérfanas ✓"; else echo "$huerfanas carpetas huérfanas — están en tu computadora y en ningún otro lado. Copiá esta pantalla y pegala en tu portal (fase Higiene). Vos decidís el cajón; este chequeo no mueve ni borra nada."; fi
[ "$secretos" -gt 0 ] && echo "⚠️  $secretos carpeta(s) con archivos que parecen claves (estén o no respaldadas): van al gestor de contraseñas, nunca a un repo ni a la nube."
echo
