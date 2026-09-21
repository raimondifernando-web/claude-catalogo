#!/usr/bin/env bash
# chequeo.sh — ¿qué le falta a esta computadora para usar los plugins del catálogo?
# Uso:  bash <(curl -fsSL https://raw.githubusercontent.com/raimondifernando-web/claude-catalogo/main/scripts/chequeo.sh)
#   o:  bash ~/.claude/plugins/marketplaces/claude-catalogo/scripts/chequeo.sh
# No instala nada, no modifica nada, no muestra el valor de ninguna clave. Solo dice OK / FALTA / OPCIONAL.
set -u

ok=0; falta=0; opc=0
r() { # r <estado> <nombre> <para qué> [cómo instalar]
  case "$1" in
    OK)       ok=$((ok+1));   printf '  ✅ OK       %-28s %s\n' "$2" "$3";;
    FALTA)    falta=$((falta+1)); printf '  ❌ FALTA    %-28s %s\n' "$2" "$3"; [ -n "${4:-}" ] && printf '              → instalar: %s\n' "$4";;
    OPCIONAL) opc=$((opc+1)); printf '  ⚪ OPCIONAL %-28s %s\n' "$2" "$3"; [ -n "${4:-}" ] && printf '              → si lo querés: %s\n' "$4";;
  esac
}
have() { command -v "$1" >/dev/null 2>&1; }
py() { have python3 && python3 -c "import $1" >/dev/null 2>&1; }
envset() { [ -n "${!1:-}" ] || grep -qs "^$1=" ./.env 2>/dev/null; }

echo
echo "Chequeo de requisitos — catálogo claude-catalogo — $(date '+%Y-%m-%d %H:%M')"
echo "Equipo: $(uname -s) $(uname -m) · usuario: $(whoami)"
echo

echo "1) Base (los plugins no funcionan sin esto)"
if have claude; then r OK "claude" "Claude Code $(claude --version 2>/dev/null | head -1)"; else r FALTA "claude" "Claude Code" "https://claude.com/claude-code"; fi
if [ -d "$HOME/.claude/plugins/marketplaces/claude-catalogo" ]; then r OK "marketplace" "claude-catalogo agregado"; else r FALTA "marketplace" "el catálogo no está agregado" "claude plugin marketplace add raimondifernando-web/claude-catalogo"; fi
for p in base-segura rubro-estudio-arquitectura metodo; do
  if grep -qs "\"$p@claude-catalogo\"" "$HOME/.claude/plugins/installed_plugins.json" "$HOME/.claude/settings.json" 2>/dev/null; then r OK "plugin $p" "instalado"; else r OPCIONAL "plugin $p" "no instalado" "claude plugin install $p@claude-catalogo"; fi
done
echo

echo "2) Herramientas de base (las usan varias skills)"
if have python3 && python3 -c 'import sys; sys.exit(0 if sys.version_info>=(3,9) else 1)'; then r OK "python3" "$(python3 --version 2>&1)"; else r FALTA "python3" "Python 3 — lo usan markitdown, excel-analysis, transcribe, generate-image" "xcode-select --install   (Mac: instala las Herramientas de línea de comandos de Apple)"; fi
if have python3 && python3 -m pip --version >/dev/null 2>&1; then r OK "pip" "instalador de librerías de Python"; else r FALTA "pip" "instalador de librerías de Python" "python3 -m ensurepip --user"; fi
if have markitdown || py markitdown; then r OK "markitdown" "leer PDF/Word/Excel/PowerPoint (base-segura)"; else r FALTA "markitdown" "leer PDF/Word/Excel/PowerPoint (base-segura)" "python3 -m pip install --user 'markitdown[all]'"; fi
if py pandas && py openpyxl; then r OK "pandas+openpyxl" "analizar Excel (base-segura)"; else r FALTA "pandas+openpyxl" "analizar Excel (base-segura)" "python3 -m pip install --user pandas openpyxl"; fi
echo

echo "3) Opcionales (solo para funciones puntuales)"
if have notebooklm || py notebooklm; then r OK "notebooklm-py" "NotebookLM desde Claude (rubro) — con las 5 reglas de docs/NOTEBOOKLM-SEGURO.md"; else r OPCIONAL "notebooklm-py" "NotebookLM desde Claude (rubro) — leer antes docs/NOTEBOOKLM-SEGURO.md" "python3 -m pip install --user 'notebooklm-py[browser]==0.8.2' && python3 -m playwright install chromium"; fi
if have tesseract; then r OK "tesseract" "leer texto dentro de imágenes escaneadas (markitdown)"; else r OPCIONAL "tesseract" "leer texto dentro de imágenes escaneadas (markitdown)" "brew install tesseract   (requiere Homebrew: https://brew.sh)"; fi
if have mmdc; then r OK "mermaid-cli" "exportar diagramas a PNG (mermaid-diagrams)"; else r OPCIONAL "mermaid-cli" "exportar diagramas a PNG; sin esto los diagramas se ven igual en claude.ai" "npm install -g @mermaid-js/mermaid-cli   (requiere Node.js)"; fi
if have node; then r OK "node" "Node.js $(node -v) — web-artifacts-builder (rubro)"; else r OPCIONAL "node" "Node.js — solo para web-artifacts-builder (rubro)" "https://nodejs.org (versión LTS)"; fi
if have pnpm || have npm; then r OK "pnpm/npm" "gestor de paquetes de Node"; else r OPCIONAL "pnpm/npm" "gestor de paquetes de Node (viene con Node.js)" "corepack enable"; fi
if py requests; then r OK "requests" "librería para generate-image (rubro)"; else r OPCIONAL "requests" "librería para generate-image (rubro)" "python3 -m pip install --user requests"; fi
if py openai; then r OK "openai (lib)" "librería para transcribe (rubro)"; else r OPCIONAL "openai (lib)" "librería para transcribe (rubro)" "python3 -m pip install --user openai"; fi
echo

echo "4) Claves de servicios pagos (solo se verifica que existan; nunca se muestran)"
if envset OPENROUTER_API_KEY; then r OK "OPENROUTER_API_KEY" "generate-image (rubro)"; else r OPCIONAL "OPENROUTER_API_KEY" "generate-image (rubro): sin clave no genera imágenes" "crear cuenta en openrouter.ai → portal, fase «Claves y servicios»"; fi
if envset OPENAI_API_KEY; then r OK "OPENAI_API_KEY" "transcribe (rubro)"; else r OPCIONAL "OPENAI_API_KEY" "transcribe (rubro): sin clave no transcribe audio" "crear cuenta en platform.openai.com → portal, fase «Claves y servicios»"; fi
echo

echo "Resumen: $ok OK · $falta FALTA · $opc OPCIONAL"
if [ "$falta" -gt 0 ]; then
  echo "Hay $falta requisito(s) que faltan. Copiá esta pantalla (o sacale una captura) y pegala en tu portal, fase «Herramientas de base»."
else
  echo "Todo lo esencial está. Los OPCIONAL solo hacen falta si usás esas funciones."
fi
echo
