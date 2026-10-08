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
radar seguía diciendo «Haiku 4.5» cuando ya había un Haiku nuevo). Condición: costar lo mínimo (robot sin IA ni claves; `hoy`
y el recordatorio sin red, sin IA, en menos de 1 s y con 5 líneas o menos).

1. **`vigentes`** (lo escribe el robot; es un dato, no un orden). `fuentes_auto.familias` lista las familias a seguir
   (`id`, `nombre`, `proveedor`, `alias` opcional, `patron` con UN grupo = la versión, `puntos_a_guion` para los ids de Claude
   que OpenRouter escribe con puntos). `scripts/radar-fuentes.py` toma de models.dev y OpenRouter el id más nuevo de cada familia
   (misma versión: gana el id más corto) y lo guarda en `vigentes.familias[]` con `modelo_api`, `alta` y `fuente`.
   Un candidato solo vale si: lo publica el `proveedor` de la familia (no un revendedor), calza el patrón anclado (versión de
   1-2 dígitos, así una fecha no se lee como versión), no es una vista previa, trae fecha de alta que no sea futura y no salta
   más de una versión mayor sobre lo anotado. **Nunca baja una versión** (si una fuente pierde un modelo, queda lo anotado).
   Si una familia sube, el PR dice «Salió X» y, por cada plan que sigue en la versión vieja, «el plan C de … sigue en …: el orden
   A/B/C se cambia a mano». **Ese orden no lo toca el robot (§7).** Los ids y precios de Claude se verifican con la skill
   `claude-api`, nunca de memoria. Riesgo conocido: lo que llega a `vigentes` termina en el contexto de cada sesión; los filtros
   de arriba lo reducen a ids con forma `claude-haiku-5-5`, y además **una versión nueva no se publica sola**: si el diff cambia
   `vigentes:` (o toca `radar/consejos/`), `radar.yml` abre el PR pero no lo fusiona y queda para revisión humana (decisión del dueño,
   2026-10-08). Precios, rankings y retiros siguen automáticos.
2. **`ruteo_claude`** (a mano, por PR). `tareas[]`: `id`, `corto`, `tarea`, `nivel` (haiku|sonnet|opus|fable), `esfuerzo`
   (low|medium|high|xhigh|max), `otra_ia` (id de una categoría del radar, o null), `palabras` (para reconocer la tarea en
   el pedido; sin tildes; una palabra calza entera o con un sufijo corto —«plata» no calza con «plataforma», «count» no con «country»—;
   si termina en `*` es una raíz libre: `revis*` calza con revisar, revisión y revisando), `verificado`,
   `evidencia[]` y `sin_dato`. **El nivel y el esfuerzo salen de la evidencia que ya tiene el radar (pedido del dueño,
   2026-10-08)**: cada `evidencia` apunta (`categoria` + `fuente`) a una evidencia `tipo: independiente` de esa categoría
   (§7.2: lo del fabricante no cuenta). Lo que no tiene evidencia no se inventa: la fila queda `verificado: false`, `sin_dato`
   dice qué falta y vale el valor por defecto de la política de modelos **tal cual** (0 «sí» → haiku/low · 1 → sonnet/medium · 2 →
   opus/high · 3 → fable/xhigh; fable y max, solo a pedido). No se baja un escalón por falta de datos —dejaría subequipadas justo las
   tareas donde el error sale caro—; se baja solo cuando hay duda entre dos escalones. La tabla es el **punto de partida**: si la
   tarea tiene más «sí» de los que supone la fila (¿juzgar o decidir?, ¿el error sale caro?, ¿mucho contexto?), se sube un escalón por
   cada uno. Hoy ninguna fila es `verificado: true`: las mediciones
   independientes que hay (Artificial Analysis, Arena) solo traen variantes xhigh y max y no comparan medium ni low. Con evidencia
   respaldada por 2 fuentes independientes la fila pasa a `verificado: true`. Las filas
   provisorias se marcan con `*` en `hoy` y el recordatorio les tolera un escalón de más.
3. **`radar.py hoy`** (hook SessionStart). 4-5 líneas en castellano simple: modelos vigentes por alias · punto de partida de
   nivel/esfuerzo · cupo de las 3 IA · aviso (radar viejo, retiro próximo, planes con modelo viejo, consejos nuevos, skills de
   prompting viejas) · recordatorio de poner `model`/`effort`.
   **Sin red y sin lanzar programas**: el cupo sale de cachés locales (`cupo.json`, `cupo-codex.json`, `cupo-agy.json` en
   `$CEREBRO_HOME` o `~/.cerebro`, que deja el Bicho; más de 30 min —24 h para Codex— cuenta como «sin dato»). Nunca corre
   `codex-cupo`, `claude -p /usage` ni `agy`. Sin caché dice «sin dato»; no inventa. Solo lee: el RADAR.yaml, las cachés,
   la carpeta `radar/consejos/` y los NOMBRES de las carpetas de skills (`skills/*-prompting`, `plugins/cache/*/*/*/skills/*-prompting`).
   Nunca falla el arranque (salida 0 y vacía ante cualquier error). Lo que se imprime al contexto sale **limpio**: ids que calcen
   `^[a-z0-9][a-z0-9._-]{1,63}$`, textos de una sola línea sin comillas invertidas ni caracteres de control, con largo máximo
   por línea (700) y por cantidad de filas (12).
4. **`radar.py recordar`** (hook PreToolUse, matcher exacto `Agent|Task|mcp__ccd_session__start_session`). Lee el JSON del hook
   por stdin y, si corresponde, devuelve `hookSpecificOutput.additionalContext` con UNA línea: falta `model`, se pidió más nivel
   que el de la fila del ruteo que calza con la tarea, o más esfuerzo; ofrece Codex/Gemini si tienen cupo (caché). Con varias filas
   que calzan manda la de nivel más alto (prefiere callar a retar de más). Tope por sesión (1 aviso «sin model», 3 de «sobra»;
   estado en `<config>/metodo/ruteo-recordado.json`, se limpia a los 3 días). Ante entrada vacía o rara, no dice nada.
   **No devuelve `permissionDecision`, `updatedInput` ni sale con código 2: no puede bloquear ni cambiar nada.** Verificado contra
   la doc oficial de hooks (2026-10-08): PreToolUse acepta `additionalContext` sin decisión de permiso; llega junto al resultado de
   la herramienta, es decir que **recuerda para las delegaciones siguientes, no frena la que ya salió**.
5. **Fuera de este paso**: el control mensual de lo realmente elegido (se mide desde los transcripts) es del paso 5 del plan.

## 9. Consejos de uso de cada proveedor (2026-10-08)
Pedido del dueño: que el radar también siga lo que cada proveedor aconseja cuando sale un modelo nuevo. Cuesta lo mínimo: el
robot no usa IA, y los resúmenes los escribe la IA más barata que alcance, nunca Opus.

**Qué vigila el robot (huella diaria del texto, igual que las páginas de retiros).** `fuentes_auto.guias`, cada una con
`proveedor`, `titulo`, `url` y `hash`; las URLs se verificaron abriéndolas (2026-10-08) y son las versiones `.md` de cada página,
sin menús, así que la huella no se mueve por cosas ajenas al texto:
Anthropic: *Prompting best practices* y el índice de *guías de migración por modelo* (un modelo nuevo agrega un enlace) ·
OpenAI: *Using GPT-6* (modelos y guía del último, `latest-model`) y *Prompt engineering* · Google: *Novedades y migración del último
Gemini* (`latest-model`) y *Prompt design strategies*. Si cambia una huella, el PR `radar/auto` dice «Cambió la guía oficial …» y
qué comando correr, y el robot anota `cambio: AAAA-MM-DD` en la guía. **Esa marca es la que sobrevive** cuando el PR se publica solo:
`radar.py consejos` y la línea de aviso de `hoy` dicen «la guía X cambió el … y los resúmenes son anteriores» hasta que se rehacen los
resúmenes de ese proveedor con fecha de consulta igual o posterior (se apaga sola). La primera vez fija la línea base. Una guía que no se pudo leer se ignora ese día (nunca borra la huella).

**Qué hay en `radar/consejos/`.** Un archivo por modelo vigente: `<modelo_api>.md`. Primera línea
`Fuente: <URL> (consultada AAAA-MM-DD)`; después de 1 a 10 líneas que empiezan con `- `, cada una con UNA cosa concreta que cambia
en cómo usar ese modelo. Solo lo que dicen las guías. Si la guía no trae nada propio del modelo, una línea que lo dice. Lo controla
un test del formato y el largo de los que existan; que falte alguno lo dice `radar.py consejos` (un test que lo exigiera frenaría al robot
justo cuando sale un modelo nuevo).

**Cómo se mantienen los consejos.**
1. `python3 plugins/metodo/scripts/radar.py consejos` → estado: qué modelos vigentes no tienen resumen y qué skills de prompting
   instaladas quedaron viejas. No usa red ni IA.
2. `python3 plugins/metodo/scripts/radar.py consejos --pedido pedido-consejos.txt` (`--todo` para rehacer todos) → limpia
   `radar/consejos/_guias/` (ignorada por git), baja las guías generales y las más nuevas de cada proveedor que enlazan los índices (hasta
   5 por proveedor) y deja el texto del pedido con solo lo que bajó. Es el único paso que usa red: solo `https` hacia
   `platform.claude.com`, `developers.openai.com` y `ai.google.dev` (lo impone el código, también con un YAML manipulado), con ids de
   guía `[a-z0-9_]`. Si no baja ninguna guía, no escribe el pedido.
3. `python3 plugins/metodo/scripts/delegar.py desarrollo . pedido-consejos.txt --archivo` → `delegar.py` elige Codex o Gemini
   según el cupo (las guías son públicas: no hay datos privados). Si solo queda Claude (código de salida 3): un subagente con
   `model: haiku` y `effort: low` que lea los mismos archivos. **Nunca Opus.**
4. Revisar cada archivo contra su fuente (una persona o un revisor que no sea quien lo escribió) y commitear por pathspec. El robot
   nunca reescribe estos archivos.

**Qué ve cada sesión.** `radar.py hoy` suma, en la línea de aviso, «hay consejos de uso nuevos para X (resumen en <ruta>)» cuando un
resumen tiene 14 días o menos, y «la skill codex:gpt-5-4-prompting es de la versión 5.4 y la vigente es 6.1: actualizala o apagala»
cuando una skill `gpt|gemini|claude-<versión>-prompting` instalada es de una generación (versión mayor) anterior al modelo vigente de su
marca (regla 19: una sola pieza por función; gana la oficial del fabricante). Como esa skill suele venir de un plugin oficial y no se
puede arreglar de un día para otro, el aviso sale **una vez por semana** (única cosa que `hoy` escribe: `<config>/metodo/avisos-radar.json`,
solo la fecha del último aviso); `radar.py consejos` la muestra siempre. No se inyecta la guía entera.
