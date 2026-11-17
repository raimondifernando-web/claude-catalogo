Fuente: https://ai.google.dev/gemini-api/docs/prompting-strategies.md.txt (consultada 2026-11-17)
- Quitá temperature, top_p y top_k: los modelos Gemini 3.6 o posteriores ignoran los valores propios y la guía avisa que más adelante darán error 400.
- Para consultas que dependen de la fecha, la guía de Gemini 3 Flash recomienda agregar a la instrucción de sistema que use la fecha y el año actuales al armar búsquedas (y que es 2026).
- Para que responda solo con lo que le das, la guía de Gemini 3 Flash propone una instrucción de sistema de «asistente estrictamente limitado al contexto», que diga que lo no mencionado no está disponible.
- De la familia Gemini 3: instrucciones directas, con delimitadores consistentes (etiquetas XML o encabezados Markdown, uno solo por prompt), y las reglas críticas, el rol y el formato al inicio o en la instrucción de sistema.
- Por defecto responde directo y eficiente: si querés más detalle o tono conversacional, pedilo explícitamente.
- En contextos largos, poné primero los datos y al final la pregunta, con una frase de enlace como «Con base en la información anterior…».
- Ya razona por su cuenta: no hace falta pedirle que detalle los pasos; para problemas difíciles basta con «pensá muy bien antes de responder», a costa de más tokens de pensamiento.
