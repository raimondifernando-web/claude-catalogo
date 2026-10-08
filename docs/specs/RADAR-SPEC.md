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
PR con el diff de `RADAR.yaml` y el motivo, y lo publica solo si pasa las guardias (solo datos del radar, tests OK, no borra más de la mitad; credencial de escritura solo en el último paso). Si una falla, el PR queda para una persona. Decisión del dueño 2026-10-03: «automático con protecciones». Sin IA, sin claves.

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
   que arma o revisa el radar). Meta: el script ordena con reglas fijas sobre esos datos. **Hoy (2026-10-03) el A/B/C
   se escribe a mano**, así que una categoría sale de «provisorio» solo si cada plan cita en `respaldo:` una evidencia
   independiente de la categoría (lo controla `respaldo()` en `radar.py`).
2. **Datos del fabricante no cuentan para el orden** (blogs, model cards, anuncios propios). Solo sirven para
   precios, ids y fechas de retiro. Campo `tipo: independiente | fabricante` en cada `evidencia`; el orden usa solo independientes.
3. **Mínimo dos fuentes independientes por categoría.** Con una sola, el plan queda `verificado: false` y lo dice.
4. **Conflictos de interés declarados** por fuente (ej. Arena vende evaluaciones a los labs que rankea; Scale le da datos
   a los labs) en la tabla de fuentes.
5. **La evidencia propia pesa más** cuando exista (el Cerebro mide costo, éxito y tiempo en tareas reales del usuario).
6. Revisión cruzada: los datos los confirma alguien distinto de quien los cargó, comparando contra la fuente (link y fecha
   por dato).

## 8. Modelos vigentes, ruteo y sesión (2026-10-08)
Pedido del dueño: que cada sesión elija modelo, esfuerzo e IA con datos del día y no de memoria (se sobredimensionaba y el
radar seguía diciendo «Haiku 4.5» cuando ya había un Haiku nuevo).

1. **`vigentes`** (lo escribe el robot; es un dato, no un orden). `fuentes_auto.familias` lista las familias a seguir
   (`id`, `nombre`, `alias` opcional, `patron` con UN grupo = la versión, `puntos_a_guion` para los ids de Claude que
   OpenRouter escribe con puntos). `scripts/radar-fuentes.py` toma de models.dev y OpenRouter el id más nuevo de cada familia
   (misma versión: gana el id más corto) y lo guarda en `vigentes.familias[]` con `modelo_api`, `alta` y `fuente`.
   Solo acepta ids que calcen el patrón anclado; **nunca baja una versión** (si una fuente pierde un modelo, queda lo anotado);
   un id raro (`:thinking`, `@eu`, `-latest`, con saltos de línea) no entra. Si una familia sube, el PR dice «Salió X» y, por
   cada plan que sigue en la versión vieja, «el plan C de … sigue en …: el orden A/B/C se cambia a mano». **Ese orden no lo
   toca el robot (§7).** Los ids y precios de Claude se verifican con la skill `claude-api`, nunca de memoria.
2. **`ruteo_claude`** (a mano, por PR). `tareas[]`: `id`, `corto`, `tarea`, `nivel` (haiku|sonnet|opus|fable), `esfuerzo`
   (low|medium|high|xhigh|max), `otra_ia` (id de una categoría del radar, o null) y `palabras` (raíces para reconocer la tarea
   en el pedido; sin tildes; una raíz de 4+ letras calza por prefijo). Criterio = las 3 preguntas de la política de modelos:
   ninguna «sí» → haiku/low · una → sonnet/medium · dos → opus/high · tres y tarea larga → fable/xhigh, solo a pedido (no se
   rutea) · `max` solo a pedido. Ante la duda, el de abajo y medir.
3. **`radar.py hoy`** (hook SessionStart). 4-5 líneas en castellano simple: modelos vigentes por alias · ruteo resumido ·
   cupo de las 3 IA · aviso (radar viejo, retiro próximo, planes con modelo viejo) · recordatorio de poner `model`/`effort`.
   **Sin red y sin comandos lentos**: el cupo sale de cachés locales (`cupo.json`, `cupo-codex.json`, `cupo-agy.json` en
   `$CEREBRO_HOME` o `~/.cerebro`, que deja el Bicho; un dato más viejo que 3 h —24 h para Codex— cuenta como «sin dato») y,
   solo para Codex, de su lector local (`codex-cupo`, milisegundos). Nunca corre `claude -p /usage` ni `agy`. Sin caché dice
   «sin dato»; no inventa. Nunca falla el arranque (salida 0 y vacía ante cualquier error).
   Lo que se imprime al contexto sale **limpio**: ids que calcen `^[a-z0-9][a-z0-9._-]{1,63}$`, textos sin saltos de línea,
   comillas invertidas ni caracteres de control, con largo máximo.
4. **`radar.py recordar`** (hook PreToolUse, matcher `Agent|Task|mcp__ccd_session__start_session`). Lee el JSON del hook por
   stdin y, si corresponde, devuelve `hookSpecificOutput.additionalContext` con UNA línea: falta `model`, se pidió más nivel
   que el de la fila del ruteo que calza con la tarea, o más esfuerzo; ofrece Codex/Gemini si tienen cupo. Con varias filas
   que calzan manda la de nivel más alto (prefiere callar a retar de más). Tope por sesión (1 aviso «sin model», 3 de «sobra»;
   estado en `<config>/metodo/ruteo-recordado.json`, se limpia a los 3 días). **No devuelve `permissionDecision`, `updatedInput`
   ni sale con código 2: no puede bloquear ni cambiar nada.** Verificado contra la doc oficial de hooks (2026-10-08): PreToolUse
   acepta `additionalContext` sin decisión de permiso; llega junto al resultado de la herramienta, es decir que **recuerda
   para las delegaciones siguientes, no frena la que ya salió**.
5. **Fuera de este paso**: el control mensual de lo realmente elegido (se mide desde los transcripts) es del paso 5 del plan.

