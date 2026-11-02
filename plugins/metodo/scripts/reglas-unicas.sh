#!/usr/bin/env bash
# reglas-unicas.sh — lanza el freno de reglas repetidas (hook PreToolUse de Write|Edit|MultiEdit del paquete metodo).
# Busca python de forma robusta, le pasa la entrada y devuelve su código de salida solo si es 2 (el que frena).
# Cualquier otra cosa —no hay python, error propio, macOS sin herramientas de línea de comandos— deja pasar sin ruido:
# es un guardarraíl, nunca un muro. Disparador: automático (hooks/hooks.json, antes de cada edición).
ENTRADA=$(</dev/stdin)
SRC="${BASH_SOURCE[0]//\\//}"
case "$SRC" in */*) DIR="${SRC%/*}" ;; *) DIR=. ;; esac
[ "$(uname -s 2>/dev/null)" = "Darwin" ] && ! xcode-select -p >/dev/null 2>&1 && exit 0   # sin esto macOS abre un cartel pidiendo instalar herramientas
for py in python3 python; do
  command -v "$py" >/dev/null 2>&1 || continue
  printf '%s' "$ENTRADA" | "$py" "$DIR/reglas-unicas.py" hook
  r=$?
  [ "$r" -eq 2 ] && exit 2
  [ "$r" -eq 0 ] && exit 0
done
exit 0
