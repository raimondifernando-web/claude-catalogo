Fuente: https://ai.google.dev/gemini-api/docs/latest-model.md.txt (consultada 2026-11-01)
- Elegí thinking_level: low, medium (default) o high. Probá los tres y quedate con el más bajo que cumpla tu calidad.
- max_output_tokens es un límite duro para pensamiento más salida: si lo tenías en menos de 32.768, subilo.
- Para respuestas de más de 64K tokens, usá background: true con max_output_tokens mayor a 65.536 (hasta 1M). Sin ese valor, el servidor corta en 64K.
- Quitá temperature, top_p y top_k: el modelo los ignora.
- No uses caché explícita (cachedContents): no está soportada. La caché implícita viene activa para prompts de 4.096 tokens o más.
- Para mantener el estado de varios turnos o llamadas a funciones, usá previous_interaction_id.
- Para prompts difíciles, subí el timeout del cliente a 15 minutos o más, o usá background.
- Precio introductorio hasta el 30/11/2026: US$2 de entrada y US$10 de salida por millón; después, US$4 y US$20. El pensamiento se cobra como salida.
- No está disponible en el plan gratuito.
