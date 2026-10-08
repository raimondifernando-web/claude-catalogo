Fuente: https://developers.openai.com/api/docs/guides/latest-model.md (consultada 2026-10-08)
- Soporta el esfuerzo de razonamiento "none" (GPT-6 Astra y GPT-6.1 Sol no): si tu pedido actual lo usa, se puede mantener.
- Llamadas a funciones en Chat Completions solo con reasoning_effort "none"; para razonar con herramientas, usar la Responses API.
- Con un esfuerzo distinto de "none", sacar temperature, top_p y top_logprobs (y logprobs en Chat Completions).
- Fast mode admite residencia de datos en la UE.
