#!/usr/bin/env bash
# bloquear-secretos.sh — lanza el freno anti-secretos (hook PreToolUse de Bash).
# Busca python3 de forma robusta y pasa stdin/stdout/stderr y el código de salida tal cual (el 2 es el que frena).
# Si no hay python o falta el programa, avisa y deja pasar: no rompe Bash (y nunca devuelve un 2 por error), pero no queda callado.
PY=$(command -v python3 2>/dev/null)
[ -z "$PY" ] && [ -x /usr/bin/python3 ] && PY=/usr/bin/python3
[ -z "$PY" ] && { echo "[bloquear-secretos] aviso: no encontré python3, el freno anti-secretos no está activo en esta sesión" >&2; exit 0; }
# En una Mac sin las herramientas de línea de comandos, /usr/bin/python3 es un aviso de instalación: no lo lanzamos en cada comando
if [ "$PY" = "/usr/bin/python3" ] && command -v xcode-select >/dev/null 2>&1 && ! xcode-select -p >/dev/null 2>&1; then
  echo "[bloquear-secretos] aviso: falta instalar Python (herramientas de línea de comandos), el freno anti-secretos no está activo" >&2; exit 0
fi
DIR="${BASH_SOURCE[0]%/*}"
[ -f "$DIR/bloquear-secretos.py" ] || { echo "[bloquear-secretos] aviso: falta bloquear-secretos.py, el freno anti-secretos no está activo" >&2; exit 0; }
exec "$PY" "$DIR/bloquear-secretos.py"
