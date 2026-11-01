Fuente: https://developers.openai.com/api/docs/guides/latest-model.md (consultada 2026-11-01)
- Acepta none, low, medium (default), high, xhigh y max. Arrancá en medium y subí solo si la mejora vale el tiempo y los tokens.
- Está pensado para razonamiento visual, uso preciso de la computadora y escritura clara: sirve para leer imágenes y pantallas, y para redactar.
- Si llamaba herramientas por Chat Completions, pasá esas llamadas a la Responses API.
- Al migrar desde GPT-5.6 Terra, compará ambos modelos con el mismo effort en imágenes y flujos reales.
- Si el effort no es none, quitá temperature, top_p y top_logprobs.
- Fast mode admite residencia de datos en la UE.
