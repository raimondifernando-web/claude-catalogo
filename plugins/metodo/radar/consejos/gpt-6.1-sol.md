Fuente: https://developers.openai.com/api/docs/guides/latest-model.md (consultada 2026-10-08)
- Para utilizar llamadas a herramientas (tool calling), es obligatorio usar la Responses API (Chat Completions solo admite peticiones sin herramientas).
- Configurar el esfuerzo de razonamiento con reasoning.effort (en Responses) o reasoning_effort (en Chat Completions) en low, medium (por defecto), high, xhigh o max.
- Los esfuerzos de razonamiento "none" y "minimal" no están soportados (si se migra desde un pedido con minimal, comenzar evaluando con low).
- Al usar esfuerzo de razonamiento, eliminar los parámetros temperature, top_p y top_logprobs (y en Chat Completions también logprobs).
- Para modificar el esfuerzo de razonamiento durante una conversación preservando el caché de prefijo, enviar un elemento configuration_update en el input.
- Es compatible con residencia de datos en la Unión Europea tanto en Fast mode como en Ultrafast mode (este último soporta EE. UU., UE y procesamiento global).
- Recomendado para programación compleja, computer use y tareas profesionales que busquen rendimiento cercano a Astra con menor costo.
