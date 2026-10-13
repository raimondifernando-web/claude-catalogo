#!/usr/bin/env bash
# consultar-ecosistema.sh — lanza el freno de la regla 22 (hook PreToolUse de Write|Agent|Task|Workflow).
# Pasa stdin/stderr y el código de salida tal cual (el 2 es el que frena). Sin python o sin el programa: deja pasar, sin ruido (en Windows avisa una vez por día).
# Windows (F3): ruta con barras invertidas normalizada y python3 / python / «py -3» probados de verdad (ver _python-windows.sh). Mac y Linux: igual que siempre.
SRC="${BASH_SOURCE[0]//\\//}"
case "$SRC" in */*) DIR="${SRC%/*}" ;; *) DIR=. ;; esac
case "${METODO_SO_PRUEBA:-$(uname -s 2>/dev/null)}" in
  MINGW*|MSYS*|CYGWIN*)
    . "$DIR/_python-windows.sh" 2>/dev/null || exit 0
    [ -f "$DIR/consultar-ecosistema.py" ] || exit 0
    if elegir_python_windows; then exec env PYTHONUTF8=1 "${PYC[@]}" "$DIR/consultar-ecosistema.py"; fi
    avisar_una_vez_win "Aviso: el freno de la regla 22 no está activo en esta sesión (no encontré Python: python3, python ni py -3)."
    exit 0 ;;
esac
PY=$(command -v python3 2>/dev/null)
[ -z "$PY" ] && [ -x /usr/bin/python3 ] && PY=/usr/bin/python3
[ -z "$PY" ] && exit 0
if [ "$PY" = "/usr/bin/python3" ] && command -v xcode-select >/dev/null 2>&1 && ! xcode-select -p >/dev/null 2>&1; then exit 0; fi
[ -f "$DIR/consultar-ecosistema.py" ] || exit 0
exec "$PY" "$DIR/consultar-ecosistema.py"
