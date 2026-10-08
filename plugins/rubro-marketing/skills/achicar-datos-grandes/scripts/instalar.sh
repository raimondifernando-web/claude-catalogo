#!/bin/bash
# Instala Headroom (versión fija, solo el núcleo) en un entorno aislado. Se puede repetir sin romper nada.
# Todo viene de requisitos.txt con hashes (--require-hashes): si algún archivo no coincide, no instala.
set -e
VER="0.40.0"
VENV="${HEADROOM_VENV:-$HOME/.cache/headroom/venv}"
AQUI="$(cd "$(dirname "$0")" && pwd)"
export HEADROOM_BEACON=off HEADROOM_OFFLINE=false
UV="$(command -v uv || true)"
[ -z "$UV" ] && [ -x "$HOME/.local/bin/uv" ] && UV="$HOME/.local/bin/uv"
[ -z "$UV" ] && [ -x /opt/homebrew/bin/uv ] && UV=/opt/homebrew/bin/uv
if [ -z "$UV" ]; then echo "Falta uv: corré «Poner todo al día» (lo instala) y repetí  ✗"; exit 1; fi
if [ -x "$VENV/bin/python" ] && "$VENV/bin/python" -I -c "import importlib.metadata as m,sys;sys.exit(m.version('headroom-ai')!='$VER')" 2>/dev/null; then
  echo "Headroom $VER ya instalado ✓"; exit 0
fi
mkdir -p "$(dirname "$VENV")"
"$UV" venv -q --python 3.12 "$VENV" 2>/dev/null || "$UV" venv -q "$VENV"
"$UV" pip install -q --python "$VENV/bin/python" --require-hashes -r "$AQUI/requisitos.txt"
echo "Headroom $VER instalado y verificado por hash en $VENV ✓"
