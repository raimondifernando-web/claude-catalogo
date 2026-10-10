#!/usr/bin/env bash
# consultar-ecosistema.sh — lanza el freno de la regla 22 (hook PreToolUse de Write|Agent|Task|Workflow).
# Pasa stdin/stderr y el código de salida tal cual (el 2 es el que frena). Sin python o sin el programa: deja pasar, sin ruido.
PY=$(command -v python3 2>/dev/null)
[ -z "$PY" ] && [ -x /usr/bin/python3 ] && PY=/usr/bin/python3
[ -z "$PY" ] && exit 0
if [ "$PY" = "/usr/bin/python3" ] && command -v xcode-select >/dev/null 2>&1 && ! xcode-select -p >/dev/null 2>&1; then exit 0; fi
DIR="${BASH_SOURCE[0]%/*}"
[ -f "$DIR/consultar-ecosistema.py" ] || exit 0
exec "$PY" "$DIR/consultar-ecosistema.py"
