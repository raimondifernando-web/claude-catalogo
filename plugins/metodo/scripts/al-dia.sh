#!/bin/bash
# al-dia.sh — deja el Claude Code del cliente al día con el catálogo de Fernando, de una sola vez.
# Se puede correr siempre: lo que ya está bien no se toca. No borra nada del usuario.
# Termina con UNA línea: «Todo al día ✓» o qué falta (para mandar captura).
# Todo va dentro de main(): si la descarga se corta a mitad, no se ejecuta nada.
main() {
set -u
local CC="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"   # carpeta de configuración de Claude (respeta CLAUDE_CONFIG_DIR)
local CAT=claude-catalogo REPO=raimondifernando-web/claude-catalogo
local BUZON="" AUTO=0
while [ $# -gt 0 ]; do case "$1" in --buzon) BUZON="${2:-}"; shift; [ $# -gt 0 ] && shift;; --auto) AUTO=1; shift;; *) shift;; esac; done
# --auto: lo corre solo el paquete metodo al abrir sesión (una vez por día), sin ventanas ni preguntas
# Instalar paquetes NUEVOS del catálogo también en --auto (1) o solo en la corrida a mano (0).
# Fernando, 2026-10-03: «todo se instala solo» (con 2FA y protección de main en el catálogo).
local AUTO_NUEVOS=1
if [ $AUTO -eq 1 ]; then
  export GIT_TERMINAL_PROMPT=0 GIT_SSH_COMMAND="ssh -o BatchMode=yes -o ConnectTimeout=15"
  export GIT_HTTP_LOW_SPEED_LIMIT=1000 GIT_HTTP_LOW_SPEED_TIME=60   # una descarga colgada falla en vez de esperar al tope
  sleep 90   # deja terminar de arrancar Claude Code (y su actualización automática) antes de tocar los paquetes
fi
local RES="$CC/metodo/al-dia.resultado"; mkdir -p "$CC/metodo"
if [ -n "$BUZON" ] && ! [[ $BUZON =~ ^[A-Za-z0-9-]+/[A-Za-z0-9_-][A-Za-z0-9._-]*$ ]]; then echo "✗ El nombre del buzón no es válido. Mandale esta captura a Fernando."; return 1; fi
local falta=() paquetes=() nuevos=()
N=""; T=""; LK=""
trap 'rm -f "${N:-}" "${T:-}"; [ -n "${LK:-}" ] && rm -rf "$LK"' EXIT
# Una sola puesta al día a la vez: la automática ya tomó el candado (al-dia-auto.sh); la manual lo toma acá.
if [ $AUTO -eq 0 ]; then
  local L="$CC/metodo/al-dia.corriendo" P
  if [ -d "$L" ]; then
    P=$(cat "$L/pid" 2>/dev/null)
    if { [ -n "$P" ] && kill -0 "$P" 2>/dev/null; } || { [ -z "$P" ] && [ -z "$(find "$L" -maxdepth 0 -mmin +1 2>/dev/null)" ]; }; then
      echo "Ya se está poniendo al día solo en este momento. Probá de nuevo en 10 minutos."; return 0
    fi
    mv "$L" "$L.viejo.$$" 2>/dev/null && rm -rf "$L.viejo.$$"   # candado de un proceso que ya no existe
  fi
  mkdir "$L" 2>/dev/null || { echo "Ya se está poniendo al día solo en este momento. Probá de nuevo en 10 minutos."; return 0; }
  echo $$ > "$L/pid"; LK="$L"
fi

echo "Poniendo Claude al día… (puede tardar unos minutos)"

# 1. Que la Terminal encuentre claude
if ! command -v claude >/dev/null 2>&1 && [ -x "$HOME/.local/bin/claude" ]; then
  grep -qsF '$HOME/.local/bin' ~/.zshrc || echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
  export PATH="$HOME/.local/bin:$PATH"
fi
if ! command -v claude >/dev/null 2>&1; then
  echo "✗ No encuentro Claude Code en esta Mac. Mandale esta captura a Fernando."; return 1
fi

# 2. El catálogo: agregarlo si falta y traer su versión nueva.
#    Se sigue la rama «estable» del catálogo: GitHub la adelanta sola a lo publicado hace 48 horas o más, así que si
#    alguien llegara a meter algo malo en el catálogo hay dos días para verlo y sacarlo antes de que llegue a una Mac.
#    Lo urgente se pasa a «estable» en el momento (lo hace Fernando). Mientras «estable» no exista, se sigue «main».
local RAMA=estable M="$CC/plugins/marketplaces/$CAT" CAMBIO=0 S="$CC/settings.json" KM="$CC/plugins/known_marketplaces.json" REF="" APAGADOS="" INSTALADOS="" RD=""
local IP="$CC/plugins/installed_plugins.json" MARCA="$CC/metodo/antes-de-estable.intento"
# Vuelve todo a como estaba antes del cambio de rama (configuración, copia del catálogo y paquetes), sin usar claude.
restaurar() {
  cp -p "$RD/settings.json" "$S" 2>/dev/null; cp -p "$RD/known_marketplaces.json" "$KM" 2>/dev/null; cp -p "$RD/installed_plugins.json" "$IP" 2>/dev/null
  [ -d "$RD/marketplace" ] && { rm -rf "$M"; cp -Rp "$RD/marketplace" "$M"; }
  find "$CC/plugins/cache/$CAT" -name .orphaned_at -delete 2>/dev/null   # que Claude no limpie los paquetes al arrancar
  echo "✗ No pude cambiar el catálogo de rama y lo dejé como estaba (copia en ${RD#$HOME/}). Mandale esta captura a Fernando." | tee "$RES"
}
[ -f "$S" ] && { [ -f "$S.antes-al-dia" ] || cp "$S" "$S.antes-al-dia"; }   # copia de la configuración, una sola vez, antes de tocar nada
# La rama tiene que existir con ese nombre exacto; si no se puede confirmar, no se agrega ni se cambia nada.
git ls-remote --heads "https://github.com/$REPO.git" "refs/heads/$RAMA" 2>/dev/null | grep -q "[[:space:]]refs/heads/$RAMA$" \
  || { [ $AUTO -eq 1 ] && return 0; echo "✗ No pude confirmar la rama estable del catálogo (¿internet?). Probá de nuevo en un rato."; return 1; }
if claude plugin marketplace list 2>/dev/null | grep -qF "$CAT"; then
  REF=$(/usr/bin/python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))[sys.argv[2]]["source"].get("ref",""))' "$KM" "$CAT" 2>/dev/null) || REF="?"
  # Ya estaba, siguiendo otra rama: se pasa a «estable» (también en la corrida automática, como mucho una vez por semana).
  # Claude no deja cambiar la rama de un catálogo instalado: hay que quitarlo y volver a agregarlo, y eso desinstala sus
  # paquetes. Antes se guarda una copia de todo; primero se reinstala metodo (el que mantiene todo al día) y, si no queda
  # andando, se restaura la copia y queda como estaba. Si no se puede leer en qué rama está, no se toca nada.
  if [ "$REF" != "$RAMA" ] && [ "$REF" != "?" ] && { [ $AUTO -eq 0 ] || [ -z "$(find "$MARCA" -mtime -7 2>/dev/null)" ]; }; then
    touch "$MARCA" 2>/dev/null
    RD="$CC/metodo/antes-de-estable-$(date +%Y%m%d-%H%M%S)"; local f ok=1
    mkdir -p "$RD" && chmod 700 "$RD" || ok=0
    for f in "$S" "$KM" "$IP"; do [ ! -f "$f" ] || cp -p "$f" "$RD/" || ok=0; done
    [ ! -d "$M" ] || cp -Rp "$M" "$RD/marketplace" || ok=0
    [ $ok -eq 1 ] || { [ $AUTO -eq 1 ] && return 0; echo "✗ No pude guardar la copia de tu configuración: no toqué nada. Mandale esta captura a Fernando."; return 1; }
    APAGADOS=$(/usr/bin/python3 -c 'import json,sys; print(" ".join(k for k,v in json.load(open(sys.argv[1])).get("enabledPlugins",{}).items() if v is False and k.endswith("@"+sys.argv[2])))' "$S" "$CAT" 2>/dev/null)
    INSTALADOS=$(/usr/bin/python3 -c 'import json,sys; print(" ".join(k.split("@")[0] for k in json.load(open(sys.argv[1])).get("plugins",{}) if k.endswith("@"+sys.argv[2])))' "$IP" "$CAT" 2>/dev/null)
    claude plugin marketplace remove "$CAT" >/dev/null 2>&1
    if claude plugin marketplace list 2>/dev/null | grep -qF "$CAT"; then
      falta+=("pasar el catálogo a la rama estable")                       # no se quitó: sigue todo como estaba
    elif claude plugin marketplace add "$REPO#$RAMA" >/dev/null 2>&1; then
      claude plugin install "metodo@$CAT" >/dev/null 2>&1 || claude plugin install "metodo@$CAT" >/dev/null 2>&1
      if claude plugin list 2>/dev/null | grep -A3 -E "❯ metodo@$CAT[[:space:]]*$" | grep -q "✔ enabled"; then CAMBIO=1
      else restaurar; return 1; fi
    else restaurar; return 1; fi
  fi
else
  claude plugin marketplace add "$REPO#$RAMA" >/dev/null 2>&1
fi
[ -f "$M/.claude-plugin/marketplace.json" ] || { echo "✗ No pude bajar el catálogo de Fernando. Mandale esta captura."; return 1; }

# 3. Actualización automática del catálogo (con copia de la configuración, una sola vez)
[ "$(plutil -extract "extraKnownMarketplaces.$CAT.autoUpdate" raw "$S" 2>/dev/null)" = "true" ] \
  || plutil -replace "extraKnownMarketplaces.$CAT.autoUpdate" -bool true "$S" 2>/dev/null
[ "$(plutil -extract "extraKnownMarketplaces.$CAT.autoUpdate" raw "$S" 2>/dev/null)" = "true" ] || falta+=("actualización automática")

# 4. Conexión con GitHub para los paquetes que vienen directo de GitHub (solo si hace falta)
if ! ssh -T -o BatchMode=yes -o ConnectTimeout=10 git@github.com 2>&1 | grep -q "successfully authenticated"; then
  if [ $AUTO -eq 1 ]; then
    export GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=url.https://github.com/.insteadOf GIT_CONFIG_VALUE_0=git@github.com:   # solo esta corrida
  elif ! git config --global --get-all url."https://github.com/".insteadOf 2>/dev/null | grep -qxF "git@github.com:"; then
    git config --global --add url."https://github.com/".insteadOf "git@github.com:"
    echo "· Ajusté la conexión con GitHub (HTTPS). Para deshacerlo: git config --global --unset-all url.https://github.com/.insteadOf"
  fi
fi

# 5. Todos los paquetes del catálogo: instalar los que falten, actualizar los demás
#    En --auto, un paquete NUEVO entra solo si vive dentro del catálogo (./plugins/…) o viene de afuera fijado por sha;
#    si no, queda para la próxima vez que se pegue el comando a mano.
fijo() { /usr/bin/python3 - "$M/.claude-plugin/marketplace.json" "$1" <<'PY' >/dev/null 2>&1
import json, re, sys
ps = [x for x in json.load(open(sys.argv[1]))["plugins"] if x.get("name") == sys.argv[2]]
s = (ps[0] if len(ps) == 1 else {}).get("source")      # nombre repetido: no se toma ninguno
ok = (isinstance(s, str) and s.startswith("./") and ".." not in s) or (
    isinstance(s, dict) and s.get("source") in ("github", "git-subdir", "url")
    and re.fullmatch(r"[0-9a-f]{40}", str(s.get("sha", "")))
    and (s.get("source") == "github" or str(s.get("url", "")).startswith("https://")))
sys.exit(0 if ok else 1)
PY
}
local i=0 n p lista okp=0
while n=$(plutil -extract "plugins.$i.name" raw "$M/.claude-plugin/marketplace.json" 2>/dev/null); do
  if [[ $n =~ ^[a-z0-9][a-z0-9-]*$ ]]; then paquetes+=("$n"); else falta+=("nombre de paquete inválido"); fi
  i=$((i+1))
done
[ ${#paquetes[@]} -gt 0 ] || falta+=("la lista de paquetes vino vacía")
lista=$(claude plugin list 2>/dev/null)
for p in ${paquetes[@]+"${paquetes[@]}"}; do
  if printf '%s\n' "$lista" | grep -qE "❯ $p@$CAT[[:space:]]*$"; then claude plugin update "$p@$CAT" >/dev/null 2>&1
  elif [ $AUTO -eq 1 ] && ! printf ' %s ' "$INSTALADOS" | grep -qF " $p " && { [ $AUTO_NUEVOS -eq 0 ] || ! fijo "$p"; }; then nuevos+=("$p")
  else claude plugin install "$p@$CAT" >/dev/null 2>&1; fi
done
lista=$(claude plugin list 2>/dev/null)
for p in ${paquetes[@]+"${paquetes[@]}"}; do
  if printf '%s\n' "$lista" | grep -A3 -E "❯ $p@$CAT[[:space:]]*$" | grep -q "✔ enabled"; then okp=$((okp+1))
  elif ! printf '%s\n' ${nuevos[@]+"${nuevos[@]}"} | grep -qx "$p"; then falta+=("$p"); fi
done

# 5a. Los paquetes que tenías apagados antes del cambio de rama quedan apagados; y el catálogo, en la rama estable
for p in $APAGADOS; do [[ $p =~ ^[a-z0-9][a-z0-9-]*@$CAT$ ]] && claude plugin disable "$p" >/dev/null 2>&1; done
[ "$(/usr/bin/python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))[sys.argv[2]]["source"].get("ref",""))' "$KM" "$CAT" 2>/dev/null)" = "$RAMA" ] \
  || [ "$REF" = "?" ] || falta+=("el catálogo no quedó en la rama estable")   # ilegible: no se tocó nada, no se avisa todos los días

# 5b. Herramientas de Apple (traen Python) y librerías de las skills de documentos e imágenes, con versiones fijas
#     markitdown pide Python 3.10 o más: va con uv (Astral), en su propio Python, sin contraseña.
#     --exclude-newer: también sus dependencias quedan congeladas a esa fecha (no entra una versión nueva sin mirar).
#     --with azure…==1.2.0b3: markitdown 0.1.8 pide una beta de esa librería y uv no instala betas solo (en la v5 fallaba).
local PY=/usr/bin/python3 UVV=0.12.19 MDV=0.1.8 UV="$HOME/.local/bin/uv"
grep -qsF '$HOME/.local/bin' ~/.zshrc || echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.zshrc
case ":$PATH:" in *":$HOME/.local/bin:"*) ;; *) export PATH="$HOME/.local/bin:$PATH";; esac
if ! xcode-select -p >/dev/null 2>&1; then
  if [ $AUTO -eq 1 ]; then falta+=("herramientas de Apple (se instalan en la llamada con Fernando)")
  else xcode-select --install >/dev/null 2>&1; falta+=("⟳ herramientas de Apple: en la ventana que se abrió tocá Instalar y esperá a que termine"); fi
else
  local QPY='import importlib.metadata as m,sys; q={"pandas":"2.3.3","openpyxl":"3.1.5","requests":"2.32.5","openai":"2.48.0"}; sys.exit(any(m.version(k)!=v for k,v in q.items()))'
  "$PY" -c "$QPY" 2>/dev/null || "$PY" -m pip install --user --quiet --disable-pip-version-check --no-warn-script-location --only-binary=:all: \
    pandas==2.3.3 openpyxl==3.1.5 requests==2.32.5 openai==2.48.0 >/dev/null 2>&1
  "$PY" -c 'import importlib.metadata as m,sys; q={"pandas":"2.3.3","openpyxl":"3.1.5","requests":"2.32.5","openai":"2.48.0"}; sys.exit(any(m.version(k)!=v for k,v in q.items()))' 2>/dev/null \
    || falta+=("librerías de Python")
  if [ ! -x "$UV" ]; then
    local UI; UI=$(mktemp)
    curl -LsSf -o "$UI" "https://astral.sh/uv/$UVV/install.sh" \
      && [ "$(shasum -a 256 "$UI" | cut -d' ' -f1)" = "61b349611f1b6e1ba33645f30c36da5287df2609dd7af8605d96a031435eb35b" ] \
      && env UV_NO_MODIFY_PATH=1 sh "$UI" >/dev/null 2>&1
    rm -f "$UI"
  fi
  if [ -x "$UV" ]; then
    "$UV" tool list 2>/dev/null | grep -qx "markitdown v$MDV" || "$UV" tool install --force --quiet --python 3.12 --exclude-newer 2026-10-01T00:00:00Z --with azure-ai-contentunderstanding==1.2.0b3 "markitdown[all]==$MDV" >/dev/null 2>&1
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
    npm install -g --silent --ignore-scripts --prefix "$NPMG" "@openai/codex@$CXV" >/dev/null 2>&1
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
  [ "$(plutil -extract env.HYPERFRAMES_NO_TELEMETRY raw "$S" 2>/dev/null)" = "1" ] || plutil -replace env.HYPERFRAMES_NO_TELEMETRY -string 1 "$S" 2>/dev/null
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
local RP; RP=$(ls -d "$CC"/plugins/cache/claude-catalogo/metodo/*/scripts/reglas.py 2>/dev/null | sort -V | tail -1)
local F="$M/plugins/metodo/templates/REGLAS-DEL-METODO.md" G="$CC/CLAUDE.md"
if [ -n "$RP" ]; then
  local RL; RL=$(/usr/bin/python3 "$RP" sincronizar 2>/dev/null)
  case "$RL" in *✗*) falta+=("reglas del método (tu ficha tiene algo distinto: no toqué nada)");; esac
  R=$(sed -n '1p' "$(dirname "$RP")/../templates/REGLAS-DEL-METODO.md" 2>/dev/null | grep -oE '[0-9]+' | head -1)
  F=""   # ya lo hizo reglas.py
fi
local I='<!-- reglas-del-metodo:inicio -->' E='<!-- reglas-del-metodo:fin -->' C L Z
[ -n "${R:-}" ] || R="?"
if [ -z "$F" ]; then :
elif [ -f "$F" ]; then
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
    mkdir -p "$CC"; { echo; cat "$N"; } >> "$G"
  fi
else falta+=("reglas del método (no llegó el paquete metodo)"); fi

# 6b. Buzón con Fernando (solo si el comando trae --buzon dueño/repo)
if [ -n "$BUZON" ]; then
  local BD="$HOME/${BUZON#*/}" BP
  [ -d "$BD/.git" ] || GIT_TERMINAL_PROMPT=0 git clone -q "https://github.com/$BUZON.git" "$BD" >/dev/null 2>&1
  if [ -d "$BD/.git" ] && [ "$(git -C "$BD" config --get remote.origin.url 2>/dev/null)" != "https://github.com/$BUZON.git" ]; then
    falta+=("buzón: la carpeta ~/${BUZON#*/} ya existe y es otro repositorio")
  elif [ -d "$BD/.git" ]; then
    BP=$(find "$CC/plugins/cache/claude-catalogo/metodo" -name buzon.py 2>/dev/null | sort -V | tail -1)
    if [ -n "$BP" ] && GIT_TERMINAL_PROMPT=0 /usr/bin/python3 "$BP" configurar --carpeta "$BD" --yo cliente >/dev/null 2>&1; then :
    else falta+=("configurar el buzón"); fi
  else
    falta+=("⟳ buzón: aceptá en GitHub el repositorio ${BUZON#*/} (te llegó un mail) y sumalo a tu llave")
  fi
fi

# 6c. Lista de repos del chequeo de seguridad mensual (paquete metodo): se arma sola, sin pasos a mano.
#     Suma los repos de GitHub que están en la carpeta personal (un nivel) y en ~/Proyectos, más el del buzón.
#     No mira Documentos, Escritorio ni Descargas (macOS pediría permiso). Solo agrega; nunca saca ni cambia lo que hay.
local SP; SP=$(ls -d "$CC"/plugins/cache/claude-catalogo/metodo/*/scripts/seguridad.py 2>/dev/null | sort -V | tail -1)
if [ -n "$SP" ] && xcode-select -p >/dev/null 2>&1; then
  local cand=() d u
  for d in "$HOME"/*/ "$HOME"/Proyectos/*/; do
    case "$d" in "$HOME/Documents/"|"$HOME/Desktop/"|"$HOME/Downloads/"|"$HOME/Library/"|"$HOME/Pictures/"|"$HOME/Movies/"|"$HOME/Music/") continue;; esac
    [ -d "$d/.git" ] || continue
    u=$(git -C "$d" config --get remote.origin.url 2>/dev/null)
    case "$u" in https://github.com/*|git@github.com:*) cand+=("${d%/}");; esac
  done
  local BJ="$CC/metodo/buzon.json" bc
  [ -f "$BJ" ] && bc=$(/usr/bin/python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("carpeta",""))' "$BJ" 2>/dev/null) && [ -n "$bc" ] && [ -d "$bc/.git" ] && cand+=("$bc")
  for d in ${cand[@]+"${cand[@]}"}; do
    /usr/bin/python3 - "$CC/metodo/seguridad.json" "$d" <<'PY' >/dev/null 2>&1 && /usr/bin/python3 "$SP" agregar "$d" >/dev/null 2>&1
import json, os, sys
from pathlib import Path
cfg, ruta = Path(sys.argv[1]), Path(sys.argv[2]).resolve()
if not cfg.is_file(): sys.exit(0)                      # no hay lista: agregar
try: repos = json.load(open(cfg)).get("repos", [])
except Exception: sys.exit(1)                         # lista rota: no tocar
sys.exit(1 if any(Path(os.path.expanduser(str(r.get("ruta","")))).resolve() == ruta for r in repos) else 0)
PY
  done
fi

# 7. Una sola línea final (también queda guardada para el aviso al abrir sesión)
echo
if [ ${#falta[@]} -eq 0 ]; then
  echo "ok $(date +%Y-%m-%d)" > "$RES"
  echo "Todo al día ✓  ($okp paquetes · $R reglas del método · Python, Node y Codex · actualización automática prendida)"
  echo "Cerrá Claude Code y volvé a abrirlo para que tome lo nuevo."
else
  local x rep=1
  for x in "${falta[@]}"; do [ "${x#⟳}" != "$x" ] || rep=0; done
  printf 'Falta: %s ✗\n' "$(printf '%s, ' "${falta[@]}" | sed 's/⟳ //g; s/, $//')" | tee "$RES"
  if [ $rep -eq 1 ]; then echo "Cuando lo hagas, pegá este mismo comando otra vez."
  else echo "Mandale esta captura a Fernando. No lo repitas hasta que te conteste."; fi
fi
}
main "$@"
