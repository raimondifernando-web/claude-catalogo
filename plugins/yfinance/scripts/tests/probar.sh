#!/bin/bash
# Pruebas del plugin yfinance. Hermética: HOME temporal y `uv` FALSO (nunca baja ni corre nada de internet).
# Uso: /bin/bash probar.sh      (bash 3.2 de macOS)
# Disparador: manual declarada (pruebas del plugin; las corre quien cambia el plugin, y antes de publicar).
AQUI="$(cd "$(dirname "$0")/.." && pwd)"
T="$(mktemp -d /tmp/yfinance-prueba.XXXXXX)" || exit 1; trap 'rm -rf "$T"' EXIT
export HOME="$T/home"; mkdir -p "$HOME/.local/bin" || exit 1
fallos=0; ok() { echo "  ok     $1"; }; mal() { echo "  FALLA  $1"; fallos=$((fallos+1)); }
cat > "$T/uv" <<'S'
#!/bin/bash
echo "ARGS=$*" > "$STUB_LOG"; echo "CWD=$PWD" >> "$STUB_LOG"
S
chmod +x "$T/uv"; export STUB_LOG="$T/uv.log"
# 1) con uv: lo llama con la versión fijada, la fecha de congelado, Python 3.12 y parado en «/»
YFINANCE_UV="$T/uv" /bin/bash "$AQUI/yfinance-mcp"
grep -q 'ARGS=tool run --quiet --python 3.12 --exclude-newer 2026-11-25T00:00:00Z yfmcp==0.14.1$' "$STUB_LOG" && ok "uv tool run con versión y fecha fijas" || mal "argumentos de uv: $(cat "$STUB_LOG" 2>/dev/null)"
grep -q '^CWD=/$' "$STUB_LOG" && ok "corre desde /" || mal "no corre desde /"
# 2) sin uv: avisa en castellano y sale con error (no falla mudo)
out=$(YFINANCE_UV="$T/no-existe" PATH="/usr/bin:/bin" /bin/bash "$AQUI/yfinance-mcp" 2>&1); rc=$?
[ $rc -ne 0 ] && echo "$out" | grep -q 'falta «uv»' && ok "sin uv: aviso en castellano y salida con error" || mal "sin uv: rc=$rc out=$out"
# 3) .mcp.json válido y apunta al script del plugin
python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); a=d["mcpServers"]["yfinance"]; assert a["command"]=="bash" and a["args"][0].endswith("/scripts/yfinance-mcp")' "$AQUI/../.mcp.json" && ok ".mcp.json válido" || mal ".mcp.json"
# 4) ninguna orden de compra/venta ni clave en el plugin
if grep -rIniE 'order|broker|api[_-]?key|token|password' "$AQUI/../.mcp.json" "$AQUI/yfinance-mcp" >/dev/null; then mal "aparece orden/broker/clave en el plugin"; else ok "sin órdenes, brokers ni claves"; fi
[ $fallos -eq 0 ] && echo "Todo al día ✓" || { echo "Falta: $fallos prueba(s) ✗"; exit 1; }
