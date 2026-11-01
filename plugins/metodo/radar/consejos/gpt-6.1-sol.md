Fuente: https://developers.openai.com/api/docs/guides/latest-model.md (consultada 2026-11-01)
- Usá reasoning.effort con low, medium (default), high, xhigh o max. No acepta none: si usabas none, pasá a low.
- Para herramientas, usá la Responses API. Chat Completions acepta el modelo, pero el tool calling requiere Responses.
- Si el effort no es none, quitá temperature, top_p y top_logprobs (y logprobs en Chat Completions).
- Si cambiás el effort entre respuestas, usá items configuration_update y dejá reasoning.effort del request igual: así se mantiene el caché del prefijo.
- Si el modelo se queda pidiendo aprobación antes de avanzar, usá la guía de iniciativa de OpenAI. Está medida en Astra, así que evaluala en Sol.
- Fast mode admite residencia de datos en la UE; Ultrafast en Sol admite US y UE, con procesamiento global.
- Al migrar desde GPT-5.5 o anterior, reemplazá prompt_cache_retention por prompt_cache_options.ttl con el valor "30m".
