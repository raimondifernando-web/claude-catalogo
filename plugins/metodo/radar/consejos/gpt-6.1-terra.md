Fuente: https://developers.openai.com/api/docs/guides/latest-model.md (consultada 2026-11-17)
- Está pensado para razonamiento visual y escritura: sirve para leer imágenes y para redactar.
- Acepta reasoning.effort: none (a diferencia de Astra y Sol).
- Si llamabas herramientas por Chat Completions, pasá esas llamadas a la Responses API: el tool calling requiere Responses.
- Al migrar desde GPT-5.6 Terra, compará ambos modelos con el mismo effort sobre imágenes y flujos reales.
- Si el effort no es none, quitá temperature, top_p y top_logprobs.
- Fast mode admite residencia de datos en la UE.
- Al migrar desde GPT-5.5 o anterior, reemplazá prompt_cache_retention por prompt_cache_options.ttl con el valor "30m".
