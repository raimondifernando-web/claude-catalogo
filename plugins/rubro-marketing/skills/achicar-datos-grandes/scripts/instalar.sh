#!/bin/bash
# Instala Headroom (versión fija, solo el núcleo) en un entorno aislado. Se puede repetir sin romper nada.
set -e
VER="0.40.0"
VENV="$HOME/.cache/headroom/venv"
export HEADROOM_BEACON=off HEADROOM_OFFLINE=false
command -v uv >/dev/null || { echo "Falta: uv (brew install uv)  ✗"; exit 1; }
if [ -x "$VENV/bin/python" ] && "$VENV/bin/python" -I -c "import importlib.metadata as m,sys;sys.exit(m.version('headroom-ai')!='$VER')" 2>/dev/null; then
  echo "Headroom $VER ya instalado ✓"; exit 0
fi
mkdir -p "$HOME/.cache/headroom"
uv venv -q --python 3.12 "$VENV"
uv pip install -q --python "$VENV/bin/python" "headroom-ai==$VER"
echo "Headroom $VER instalado en $VENV ✓"
