#!/bin/bash
# ordenar-mi-claude.sh — ordena las carpetas de trabajo de Claude: una carpeta madre (~/Proyectos) con una por área.
# Se corre una vez, en la Terminal, con la app de Claude cerrada. Es seguro repetirlo: lo que ya está hecho no se toca.
# No borra nada. Antes de cambiar un archivo, guarda una copia al lado (.antes-ordenar-<fecha>).

main() {
set -u
local RAIZ="${ORDENAR_RAIZ:-$HOME/Proyectos}"
local NOMBRE_EMPRESA="${ORDENAR_EMPRESA:-}"
local ACOMP="${ORDENAR_ACOMPANANTE:-tu acompañante técnico}"
local G="$HOME/.claude/CLAUDE.md"
local FECHA; FECHA=$(date +%Y%m%d-%H%M%S)
local falta=()

# --- 1. Frenos: si algo no está en condiciones, no se toca nada ---
if ! command -v git >/dev/null 2>&1; then
  echo "Falta: esta Mac no tiene git (avisale a $ACOMP) ✗"; return 1
fi
if [ "${ORDENAR_PRUEBA:-0}" != 1 ] && { pgrep -x claude >/dev/null 2>&1 || pgrep -xi "Claude" >/dev/null 2>&1; }; then
  echo "Falta: cerrá la app de Claude del todo (Cmd+Q) y volvé a correrlo ✗"; return 1
fi
if [ -n "$NOMBRE_EMPRESA" ]; then
  case "$NOMBRE_EMPRESA" in */*|.|..) echo "Falta: el nombre de carpeta no es válido ✗"; return 1;; esac
else
  # Buscar sola la carpeta de la empresa: un repo «<algo>-Claude» (no Mi-Claude, no copias) en la carpeta personal o en $RAIZ
  local d n=0 encontrada=""
  for d in "$HOME"/*-Claude "$RAIZ"/*-Claude; do
    [ -d "$d/.git" ] || continue
    [ "${d##*/}" = "Mi-Claude" ] && continue
    case " $encontrada " in *" ${d##*/} "*) continue;; esac
    encontrada="$encontrada ${d##*/}"; n=$((n+1))
  done
  if [ $n -eq 0 ]; then echo "Falta: no encuentro la carpeta de la empresa (una carpeta «…-Claude») ✗"; return 1; fi
  if [ $n -gt 1 ]; then echo "Falta: hay varias carpetas «…-Claude» (${encontrada# }): avisale a $ACOMP ✗"; return 1; fi
  NOMBRE_EMPRESA="${encontrada# }"
fi
local VIEJA="$HOME/$NOMBRE_EMPRESA" NUEVA="$RAIZ/$NOMBRE_EMPRESA"

local ya_mudada=0
if [ -e "$NUEVA" ] && [ ! -e "$VIEJA" ]; then
  ya_mudada=1
elif [ -e "$NUEVA" ] && [ -e "$VIEJA" ]; then
  echo "Falta: hay dos carpetas $NOMBRE_EMPRESA (una en tu carpeta personal y otra en $RAIZ): no toco nada ✗"; return 1
elif [ ! -e "$VIEJA" ]; then
  echo "Falta: no encuentro la carpeta $NOMBRE_EMPRESA ✗"; return 1
elif [ -n "$(git -C "$VIEJA" status --porcelain --untracked-files=no 2>/dev/null)" ]; then
  # Solo cuentan los archivos que git ya sigue: un .DS_Store suelto no frena
  echo "Falta: tenés cambios sin guardar en $NOMBRE_EMPRESA: cerrá las sesiones con /cerrar y volvé a correrlo ✗"; return 1
fi

# --- 2. Mudanza de la carpeta de la empresa ---
mkdir -p "$RAIZ" || { echo "Falta: no pude crear $RAIZ ✗"; return 1; }
if [ $ya_mudada -eq 0 ]; then
  mv "$VIEJA" "$NUEVA" || { echo "Falta: no pude mover $NOMBRE_EMPRESA (no toqué nada más) ✗"; return 1; }
fi

# Copias de trabajo (/otra-sesion) que git reconoce como suyas y siguen en la carpeta personal: se mudan al lado.
# Va fuera del «if» para reintentar las que hayan quedado afuera en una corrida anterior.
local HOMEP; HOMEP=$(cd "$HOME" && pwd -P)
local w bwt
while IFS= read -r w; do
  [ -n "$w" ] || continue
  [ -d "$w" ] || continue
  [ "$(cd "$w/.." && pwd -P)" = "$HOMEP" ] || continue
  bwt="${w##*/}"
  # Si el nombre ya está usado en $RAIZ, usar el primero libre (<copia>-2, -3…): git la reconecta igual
  if [ -e "$RAIZ/$bwt" ]; then
    local k=2; while [ -e "$RAIZ/$bwt-$k" ]; do k=$((k+1)); done; bwt="$bwt-$k"
  fi
  mv "$w" "$RAIZ/$bwt" || { falta+=("no pude mover la copia $bwt"); continue; }
  git -C "$NUEVA" worktree repair "$RAIZ/$bwt" >/dev/null 2>&1 || falta+=("no pude reconectar la copia $bwt")
done <<EOF_COPIAS
$(git -C "$NUEVA" worktree list --porcelain 2>/dev/null | sed -n 's/^worktree //p')
EOF_COPIAS
git -C "$NUEVA" worktree repair >/dev/null 2>&1 || true

# --- 3. Carpetas nuevas (nunca pisan nada) ---
escribir_si_falta() {  # $1 = archivo; el contenido llega por la entrada
  if [ -e "$1" ]; then cat >/dev/null; return 0; fi
  if cat > "$1.tmp.$$" && [ -s "$1.tmp.$$" ] && mv "$1.tmp.$$" "$1"; then return 0; fi
  rm -f "$1.tmp.$$"; return 1
}
if mkdir -p "$RAIZ/Mi-Claude" 2>/dev/null; then
  [ -d "$RAIZ/Mi-Claude/.git" ] || git -C "$RAIZ/Mi-Claude" init -q || falta+=("no pude preparar el historial de Mi-Claude")
  escribir_si_falta "$RAIZ/Mi-Claude/CLAUDE.md" <<EOF || falta+=("no pude escribir la ficha de Mi-Claude")
# Mi Claude

Esta carpeta la ve $ACOMP.

## Para qué es
- Instalar, actualizar y arreglar lo de Claude, Cowork y el buzón.
- Herramientas generales que no son de la empresa.

## Qué NO va acá
- Trabajo de la empresa: va en $NUEVA.
- Vida personal: va en $RAIZ/Personal.
EOF
else falta+=("no pude crear $RAIZ/Mi-Claude"); fi

if mkdir -p "$RAIZ/Personal" 2>/dev/null; then
  escribir_si_falta "$RAIZ/Personal/CLAUDE.md" <<EOF || falta+=("no pude escribir la ficha de Personal")
# Personal

Tu vida fuera de la empresa.
Esta carpeta es para vos: no la subas a ningún repositorio compartido ni la copies a la carpeta de la empresa.

## Reglas
- No muevas acá nada de la empresa.
EOF
else falta+=("no pude crear $RAIZ/Personal"); fi

[ -f "$RAIZ/CLAUDE.md" ] && falta+=("la carpeta madre tiene una ficha propia: conviene sacarla")

# Cowork: si su configuración apunta a la carpeta vieja, apuntarla a la nueva (decide Python; copia antes; escritura segura)
local CW="$HOME/.claude/cowork/config.json"
if [ -f "$CW" ]; then
  if python3 - "$CW" "$VIEJA" "$NUEVA" "$CW.antes-ordenar-$FECHA" <<'EOF_PY'
import json, os, shutil, sys
f, v, n, copia = sys.argv[1:5]
c = json.load(open(f, encoding="utf-8"))
if "carpetas" in c:
    nuevas = [n + x[len(v):] if x == v or x.startswith(v + "/") else x for x in c["carpetas"]]
    if nuevas != c["carpetas"]:
        c["carpetas"] = nuevas
        shutil.copy2(f, copia)
        t = f + ".tmp"
        with open(t, "w", encoding="utf-8") as h:
            json.dump(c, h, indent=2, ensure_ascii=False)
        os.replace(t, f)
EOF_PY
  then :; else falta+=("no pude apuntar Cowork a la carpeta nueva (quedó como estaba)"); fi
fi

# --- 4. Ficha global: bloque de áreas y reglas de carpetas al principio (no toca lo que ya escribiste) ---
if ! grep -qxF '<!-- quien-soy:inicio -->' "$G" 2>/dev/null; then
  mkdir -p "${G%/*}" || falta+=("no pude crear la carpeta de tu ficha")
  local B="$G.antes-ordenar-$FECHA" T="$G.tmp.$$"
  if [ -f "$G" ] && { ! cp "$G" "$B" || ! cmp -s "$G" "$B"; }; then
    falta+=("no pude hacer la copia de tu ficha: no la toqué")
  elif {
      cat <<EOF
<!-- quien-soy:inicio -->
## Mis áreas (una carpeta cada una, dentro de $RAIZ)
- Empresa: $NUEVA (la ve $ACOMP)
- Mi Claude: $RAIZ/Mi-Claude (instalar, actualizar, arreglar; la ve $ACOMP)
- Personal: $RAIZ/Personal (solo mía, no se sube)
## Reglas de carpetas
- Nunca abras una sesión en $RAIZ (la carpeta madre): elegí siempre la carpeta del área.
- Un tema de la empresa va dentro de su carpeta; algo que no es de la empresa va en su propia carpeta al lado.
- Nada de Personal se copia a una carpeta que se sube a GitHub.
<!-- quien-soy:fin -->

EOF
      if [ -f "$G" ]; then cat "$G"; fi
    } > "$T" && [ -s "$T" ] && mv "$T" "$G"; then :
  else rm -f "$T"; falta+=("no pude actualizar tu ficha (quedó como estaba)"); fi
fi

# Aviso: archivos de configuración de la empresa que todavía nombran la carpeta vieja
local viejas
viejas=$(grep -rlF "$VIEJA/" "$NUEVA/.claude" --include='*.json' 2>/dev/null | grep -vc '\.antes-ordenar-')
[ "${viejas:-0}" -gt 0 ] && falta+=("$viejas archivo(s) de configuración de $NOMBRE_EMPRESA todavía nombran la carpeta vieja: avisale a $ACOMP")

# --- 5. Cierre ---
echo
echo "Carpeta de la empresa: $NUEVA"
echo "Ahora: abrí Claude, elegí $NUEVA y escribí /arrancar. La primera vez Claude te pregunta si confiás en la carpeta: decile que sí."
if [ ${#falta[@]} -eq 0 ]; then
  echo "Todo ordenado ✓"; return 0
fi
local str="" item
for item in "${falta[@]}"; do str="${str:+$str; }$item"; done
echo "Falta: $str ✗"
return 1
}

main "$@"
