# Changelog — yfinance

## 0.1.0 (2026-11-25) — primera versión
- Plugin nuevo: registra el servidor MCP `yfmcp` **fijado en 0.14.1** (PyPI, MIT) con `.mcp.json`; sin `claude mcp add` a mano. Solo lectura, sin claves ni cuenta: precios, balances, estimaciones y precios objetivo de analistas, opciones, tenedores, noticias, fondos y screener de Yahoo Finanzas.
- Lo corre `uv` (que el actualizador del catálogo instala solo en `~/.local/bin`, versión y huella fijas) con `--python 3.12` y `--exclude-newer 2026-11-25`: las dependencias (yfinance, mcp, matplotlib…) quedan congeladas a esa fecha, no entra una versión nueva sin mirar. Se baja una sola vez, la primera vez que conecta (requiere internet esa vez).
- `scripts/yfinance-mcp`: busca `uv`; si falta, avisa en castellano y sale con error (no falla mudo). `scripts/tests/probar.sh`: pruebas herméticas con `uv` falso.
- No opera, no mueve plata y no es asesoramiento de inversión.
