# _python-windows.sh — NO se ejecuta solo: los lanzadores de hooks (bloquear-secretos.sh, consultar-ecosistema.sh, skills-externas/skills-cli-tranca.sh)
# lo cargan con `.` SOLO cuando corren en Windows (Git Bash / MSYS / Cygwin). En Mac y Linux no se toca (F3 del security check 0.35.0).
# elegir_python_windows → deja en el arreglo PYC el primer Python 3 que de verdad corre: python3, python o «py -3».
#   El python3 de la Microsoft Store sale con error si no hay Python instalado; con el instalador de python.org solo existen python/py.
# avisar_una_vez_win "texto" → un aviso por día (JSON de hook) cuando no hay ningún Python: antes el freno quedaba apagado sin que nadie lo supiera.
elegir_python_windows() {
  PYC=()
  local c
  for c in "python3" "python" "py -3"; do
    if $c -c 'import sys; sys.exit(0 if sys.version_info[0] == 3 else 1)' >/dev/null 2>&1; then
      read -r -a PYC <<< "$c"
      return 0
    fi
  done
  return 1
}
avisar_una_vez_win() {
  local marca="${TMPDIR:-${TEMP:-/tmp}}/metodo-sin-python-$(date +%Y%m%d 2>/dev/null)"
  [ -e "$marca" ] && return 0
  ( set -o noclobber; : > "$marca" ) 2>/dev/null
  printf '{"systemMessage":"%s","hookSpecificOutput":{"hookEventName":"PreToolUse","additionalContext":"%s"}}\n' "$1" "$1"
}
