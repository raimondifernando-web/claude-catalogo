Fuente: https://ai.google.dev/gemini-api/docs/latest-model.md.txt (consultada 2026-11-17)
- Es un modelo de razonamiento profundo, más eficiente que Gemini 4 Carbon: respuestas más rápidas y menos tokens por turno.
- El pensamiento se elige con thinking_level: low, medium (default) o high.
- Contexto unificado de 1M tokens; salida de 64K por defecto, y hasta 1M con long decode.
- Quitá temperature, top_p y top_k: los modelos Gemini 4 ignoran los valores propios y la guía avisa que más adelante darán error 400.
- Precio de lanzamiento hasta el 30 de noviembre: US$2 de entrada y US$10 de salida por millón; la guía descargada no trae el precio posterior.
- Acepta texto, imágenes, audio, video y PDF, con búsqueda de Google, ejecución de código, llamadas a funciones, uso de computadora y salidas estructuradas.
