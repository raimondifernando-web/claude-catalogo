---
name: radar
description: "Radar de modelos: dice qué IA conviene usar para cada tarea (programar, revisar código, diseño, escribir en castellano, investigar en la web, documentos largos, imágenes, video, transcripción, voz, planillas, tareas baratas, agentes de tarea larga), con un plan A, un B y un C por si el A no está disponible (cupo agotado, modelo retirado, sin datos privados). Usala cuando el usuario diga 'qué modelo uso para esto', 'qué IA me conviene', '/metodo:radar', 'se me acabó el cupo, qué uso', 'mostrame el ranking', 'plan B', o antes de delegar trabajo a Codex, Gemini o cualquier otra IA, o cuando al arrancar aparezca 'Radar: …'."
---

# /metodo:radar — Qué IA usar para cada cosa (y qué usar si no está)

**El problema.** Elegir modelo «de memoria» se desactualiza en semanas: sale uno nuevo, se retira otro, se te acaba
el cupo de uno y no sabés cuál sigue. **La solución.** Un archivo único, `radar/RADAR.yaml`, con tres planes ordenados por
categoría (A, B, C), el ranking de la fuente principal y los retiros anunciados. Lo mantiene un PR automático del
catálogo que una persona aprueba; vos solo lo consultás.

Script: `${CLAUDE_PLUGIN_ROOT}/scripts/radar.py` (Python 3, sin instalar nada). **Lo corrés vos, Claude**; el usuario no toca la
terminal. En los ejemplos, `radar` quiere decir `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/radar.py"` (en Windows, `py -3`).

## Cuándo usar cada comando
- **`radar elegir <categoría>`** — *antes de delegar o de cambiar de herramienta.* Devuelve el primer plan disponible y dice
  en una línea qué saltó y por qué. Con **`--sensible`** si el trabajo lleva código privado, datos de clientes o nada que
  deba salir de la empresa: salta los planes gratis que usan lo que mandás para entrenar.
- **`delegar <categoría> <repo> <pedido.txt> [--revisar]`** — *cuando hay que mandar trabajo acotado a otra IA* (programar un
  arreglo, revisar un repo). Es `scripts/delegar.py`, no el radar: elige con el radar poniendo a Claude último, mide el
  cupo de Claude, Codex y Antigravity, ejecuta con la herramienta del plan (Codex o Antigravity) y deja el cambio sin
  commitear. Si el plan elegido es Claude, sale con código 3: lo hacés en esta sesión. Se niega en carpetas con datos
  privados o de clientes. Tests y revisión del cambio los hacés vos.
- **`radar ver [categoría]`** — *cuando el usuario quiere mirar el ranking.* Sin categoría, el resumen A/B/C de todas; con
  categoría, el detalle (por qué, condiciones, cómo ver el cupo, fuente y fecha).
- **`radar html`** — una página local para mirarlo en el navegador (`<config>/metodo/radar.html`).
- **`radar actualizar`** — baja la última versión publicada. Sin red, sigue con lo último guardado.
- **`radar probar --si`** — *opcional.* Prueba gratis, con las claves del usuario (por variable de entorno, nunca se
  muestran), que los modelos nombrados existen para su cuenta. Detecta el caso «el modelo figura pero tu cuenta ya no lo
  puede usar». Si el usuario no lo pidió, no lo corras.

## Cómo se usa lo que devuelve
1. Si el plan que te da **no es el A**, decíselo al usuario en una línea (qué saltó y por qué) antes de usar el B o el C.
2. Si dice **[a verificar]**, el dato viene de una investigación que no se leyó de primera mano: usalo para decidir, no lo
   cites como cifra textual.
3. Respetá las **condiciones** del plan (por ejemplo, «sin datos privados en el plan gratis»). Si el trabajo es sensible y
   el comando dice que ningún plan alcanza, parás y preguntás.
4. El radar **no gasta cupo**: mide solo el de Claude (`/usage`), Codex (`scripts/codex-cupo`) y Antigravity (`agy -p /usage`), los
   tres sin llamar a ningún modelo, y salta un plan con el cupo agotado. Para los demás no hay forma local de medir: el
   radar no los salta, avisá si el usuario sabe que se acabó.
5. Nunca elijas un modelo de memoria cuando el radar tiene la respuesta.

## Qué no hace
No instala herramientas, no usa claves salvo en `probar`, no cambia ninguna regla por su cuenta y no manda datos a ningún
lado. La regla 18 del método dice cuándo consultarlo.
