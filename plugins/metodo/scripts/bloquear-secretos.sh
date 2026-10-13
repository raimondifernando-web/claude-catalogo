#!/usr/bin/env bash
# bloquear-secretos.sh — lanza el freno anti-secretos (hook PreToolUse de Bash, Read y Grep).
# Busca python3 de forma robusta y pasa la entrada, la salida y el código de salida tal cual (el 2 es el que frena).
# Si no hay python o falta el programa, deja pasar (no rompe nada y nunca devuelve un 2 por error) y AVISA UNA VEZ por
# sesión con JSON por la salida estándar: «systemMessage» lo ve la persona y «additionalContext», Claude.
# Un aviso por stderr con salida 0 no lo ve nadie («Claude never sees stderr from a hook that exits 0», docs de hooks).
# Solo usa cosas de bash (sin cat/sed/dirname), para que el aviso salga aunque el PATH venga vacío.
ENTRADA=$(</dev/stdin)
avisar() {
  local sid="" marca
  if [[ $ENTRADA =~ \"session_id\"[[:space:]]*:[[:space:]]*\"([A-Za-z0-9._-]+)\" ]]; then sid=${BASH_REMATCH[1]}; fi
  [ -n "$sid" ] || sid="dia-$(date +%Y%m%d 2>/dev/null)"
  marca="${TMPDIR:-/tmp}/bloquear-secretos-aviso-${UID}-$sid"
  # F9: si la marca es un enlace simbólico (alguien lo dejó en la carpeta temporal compartida) no se escribe: `: >` pisaría el archivo al que apunta
  if [ ! -L "$marca" ]; then
    [ -e "$marca" ] && exit 0
    ( set -o noclobber; : > "$marca" ) 2>/dev/null
  fi
  printf '{"systemMessage":"%s","hookSpecificOutput":{"hookEventName":"PreToolUse","additionalContext":"%s"}}\n' "$1" "$1"
  exit 0
}
PY=$(command -v python3 2>/dev/null)
[ -z "$PY" ] && [ -x /usr/bin/python3 ] && PY=/usr/bin/python3
[ -z "$PY" ] && avisar "Aviso: el freno anti-secretos no está activo en esta sesión (no encontré python3). Las claves pueden quedar a la vista."
# En una Mac sin las herramientas de línea de comandos, /usr/bin/python3 es un aviso de instalación: no lo lanzamos en cada comando
if [ "$PY" = "/usr/bin/python3" ] && command -v xcode-select >/dev/null 2>&1 && ! xcode-select -p >/dev/null 2>&1; then
  avisar "Aviso: el freno anti-secretos no está activo (falta instalar las herramientas de línea de comandos de Apple, que traen Python)."
fi
case "${BASH_SOURCE[0]}" in */*) DIR="${BASH_SOURCE[0]%/*}" ;; *) DIR=. ;; esac
[ -f "$DIR/bloquear-secretos.py" ] || avisar "Aviso: el freno anti-secretos no está activo (falta bloquear-secretos.py en el paquete)."
printf '%s' "$ENTRADA" | "$PY" "$DIR/bloquear-secretos.py"
