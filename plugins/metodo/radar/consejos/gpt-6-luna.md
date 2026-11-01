Fuente: https://developers.openai.com/api/docs/guides/latest-model.md (consultada 2026-11-01)
- Acepta reasoning.effort: none. La guía lo describe para tareas enfocadas y de alto volumen.
- Con Chat Completions, el function calling solo anda con reasoning_effort: "none". Para razonar con herramientas, usá la Responses API.
- Si el effort no es none, quitá temperature, top_p y top_logprobs.
- Fast mode admite residencia de datos en la UE para Luna.
- Al migrar desde GPT-5.5 o anterior, reemplazá prompt_cache_retention por prompt_cache_options.ttl con el valor "30m".
