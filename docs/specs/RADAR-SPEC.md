# Spec — Radar de modelos (fase 2: construir)

Base: `docs/specs/INVESTIGACION-radar-de-modelos.md` (fuentes, mapa y opción A recomendada + prueba de disponibilidad de B).

## Pedido del dueño (textual, 2026-10-03)
«Necesito poder ver ese ranking de qué conviene usar para cada cosa, no es lo mismo desarrollo que diseño que otras
cosas, y el sistema también tiene que saber cuál es el plan B y C en caso de que el A no esté disponible.»

## 1. Archivo único: `plugins/metodo/radar/RADAR.yaml` (+ `RADAR.md` generado, para leer)
Por **categoría**, tres planes ordenados. Categorías mínimas:
desarrollo · revisión de código y seguridad · diseño (UI/web, presentaciones) · escritura en castellano ·
investigación web · documentos largos · imágenes (generar/editar) · imágenes (entender) · video · transcripción ·
voz (TTS) · datos y planillas · tareas mecánicas baratas · agentes de tarea larga.
Cada plan: `herramienta` (Claude Code / Codex / Antigravity / app web / API), `proveedor`, `modelo` (alias si existe),
`por_que` (1 línea), `fuente` (URL) y `fecha`, `condiciones` (ej. «no datos sensibles: el plan gratis entrena con lo
que mandás»), `como_ver_cupo` (comando que no gasta: `/usage`, `/status`, `codex-cupo`…).
Más: `actualizado` (fecha), `ranking` por categoría (top 5 de la fuente principal, para la vista), y `retiros`
(modelos nombrados con fecha de apagado).

## 2. `plugins/metodo/scripts/radar.py` (Python 3 stdlib)
- `radar.py ver [categoria]` → tabla legible (A/B/C con por qué y condiciones).
- `radar.py elegir <categoria> [--sensible]` → devuelve el PRIMER plan disponible: salta los que tengan el cupo agotado
  (para Codex usa la misma lectura de `scripts/codex-cupo`; para el resto, si no hay forma local de medir, no salta),
  los marcados no disponibles por la última prueba, y con `--sensible` los que no admiten datos privados. Dice qué
  saltó y por qué, en una línea.
- `radar.py json` → exporta `radar.json` para la vista del Bicho (categorías, planes, ranking, retiros, fecha).
- `radar.py probar` (opcional, apagado por defecto): prueba gratis de disponibilidad de los modelos nombrados con las
  claves del usuario por referencia (variables de entorno, nunca se imprimen); guarda el resultado local.
Nunca falla el arranque; sin red, usa lo último guardado.

## 3. Actualización automática (opción A de la investigación)
`.github/workflows/radar.yml` + `scripts/radar-fuentes.py`: semanal (rankings) y diario (retiros/precios), SOLO fuentes
públicas sin clave (dataset de Arena en HF, CSV de Epoch, JSON de LiteLLM, models.dev, OpenRouter /models, páginas de
retiros). Si cambia el #1 de una categoría, se anuncia el retiro de un modelo nombrado o un precio sube >20% → abre un
PR con el diff de `RADAR.yaml` y el motivo. **Nunca mergea solo.** Sin IA, sin claves.

## 4. Lo que leen las sesiones
- Regla 18 del método (texto corto): «Para elegir qué IA usar, consultá `radar.py elegir <categoría>`; si el plan A no
  está, usá el B o el C que te devuelve. Nunca de memoria.»
- `/metodo:arrancar` muestra en una línea si el radar tiene más de 14 días o hay un retiro próximo de un modelo usado.

## 5. Vista en el Bicho
`radar.json` es la fuente de la pantalla «Radar» del Bicho (hito M4 del Cerebro): una tarjeta por categoría con A/B/C,
el ranking top 5 y los avisos de retiro. Hasta que exista M4: `radar.py html` genera una página local simple
(`~/.claude/metodo/radar.html`) para mirarlo ya.

## 6. Pruebas
Tests con fuentes simuladas (sin red): elegir salta A agotado → B; `--sensible` salta el gratis; sin red usa caché;
json válido; el workflow arma el PR solo ante cambios relevantes. `verificar-metadatos.sh` verde; 0 nombres de clientes.
Rama `orquesta/radar-modelos`, sin publicar.

## 7. Imparcialidad (pedido del dueño, 2026-10-03: «debe ser imparcial; si le preguntás a Claude te va a decir que es el mejor, lo mismo a Gemini»)
1. **Ningún modelo opina el orden.** El A/B/C sale de datos de terceros, nunca de preguntarle a una IA (tampoco a la
   que arma o revisa el radar). El script ordena con reglas fijas y reproducibles sobre esos datos.
2. **Datos del fabricante no cuentan para el orden** (blogs, model cards, anuncios propios). Solo sirven para
   precios, ids y fechas de retiro. Campo `tipo_fuente: independiente | fabricante`; el orden usa solo independientes.
3. **Mínimo dos fuentes independientes por categoría.** Con una sola, el plan queda `verificado: false` y lo dice.
4. **Conflictos de interés declarados** por fuente (ej. Arena vende evaluaciones a los labs que rankea; Scale le da datos
   a los labs) en la tabla de fuentes.
5. **La evidencia propia pesa más** cuando exista (el Cerebro mide costo, éxito y tiempo en tareas reales del usuario).
6. Revisión cruzada: los datos los confirma alguien distinto de quien los cargó, comparando contra la fuente (link y fecha
   por dato).
