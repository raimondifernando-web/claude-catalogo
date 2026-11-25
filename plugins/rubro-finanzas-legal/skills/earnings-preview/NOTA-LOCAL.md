# Nota local — manda sobre el SKILL.md del autor

## Python (por qué el «Step 1» del autor puede fallar)
yfinance 1.8.0 necesita Python 3.10 o más. El Python que trae el sistema en la Mac (el de Apple) es 3.9 y `pip` NO lo instala. Si el chequeo del Step 1 dice `YFINANCE_NOT_INSTALLED` o `DEPS_MISSING`, no uses el bloque de `pip`: ejecutá cada bloque de Python de esta skill con uv (el kit lo instala en `~/.local/bin/uv`; si falta, decilo en una línea y no instales nada por tu cuenta):

```
~/.local/bin/uv run --quiet --python 3.12 --with yfinance==1.8.0 --with pandas --with numpy --exclude-newer 2026-11-25T00:00:00Z python - <<'PY'
# …el bloque de Python de la skill…
PY
```
Si el servidor MCP «yfinance» (plugin yfinance) está conectado, sus herramientas dan los mismos datos sin Python.

## Reglas duras del paquete
Solo lectura y análisis: nada ejecuta ni arma órdenes, no se mueve plata, no se da consejo de inversión personalizado (qué comprar o vender, cuánto) y no se piden claves. Cierre con «análisis educativo, no asesoramiento de inversión». Datos de Yahoo sin garantía de exactitud: contrastar antes de decidir.
