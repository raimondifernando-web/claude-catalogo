Fuente: https://developers.openai.com/api/docs/guides/latest-model.md (consultada 2026-11-17)
- No acepta reasoning.effort: none; si usabas none (por ejemplo en gpt-6-sol), pasá a low.
- Para herramientas usá la Responses API: Chat Completions acepta el modelo, pero el tool calling requiere Responses; migrá las llamadas a funciones.
- Si el effort no es none, quitá temperature, top_p y top_logprobs (y logprobs en Chat Completions).
- Si cambiás el effort entre respuestas, usá items configuration_update en pedidos de un solo agente y dejá igual el reasoning.effort del request, para mantener el caché del prefijo.
- Admite delegar a subagentes con Responses Multi-agent (beta) y reutilizar razonamiento de turnos anteriores con reasoning.context en all_turns.
- Si se queda pidiendo aprobación antes de avanzar, probá la guía de iniciativa de OpenAI: está medida en Astra, así que evaluala en Sol.
- Fast mode admite residencia de datos en la UE; Ultrafast en Sol admite EE. UU. y UE, con procesamiento global.
- Al migrar desde GPT-5.5 o anterior, reemplazá prompt_cache_retention por prompt_cache_options.ttl con el valor "30m".
