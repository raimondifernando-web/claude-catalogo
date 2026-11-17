Fuente: https://platform.claude.com/docs/en/models/opus-5-5/migration-guide.md (consultada 2026-11-17)
- Usá el ID claude-opus-5-5, sin fecha. Cuesta US$4 de entrada y US$20 de salida por millón (Opus 5: 5 y 25).
- El pensamiento no se puede apagar: thinking con disabled o enabled da error 400. Quitá el campo y, si querías menos pensamiento, bajá el effort.
- El effort es lo único que controla la profundidad: cinco niveles de low a max, default medium (en Opus 5 era high). Fijalo explícito y rehacé tu prueba de niveles.
- max_tokens cubre pensamiento más texto; con xhigh o max, partí de 64k.
- Las respuestas empiezan con bloques thinking: leé el texto por type y devolvé esos bloques sin modificar en los loops de herramientas. Llegan vacíos por defecto; para el resumen poné display: "summarized".
- tool_choice any o tool da error 400: usá auto con herramientas strict o salida estructurada. Tampoco mandes temperature, top_p, top_k ni prefill.
- El texto entre llamadas a herramientas ahora llega como bloques thinking: para mostrarlo como avance poné display: "updates" (beta) o "summarized".
- Mantené el historial solo para agregar (sin editar system, tools ni turnos anteriores); un cambio de modelo o fallback puede dejar al otro sin esos bloques de pensamiento.
- Manejá stop_reason: "refusal" (categorías más amplias que en Opus 5, como bio) y configurá fallback. No entra en Priority Tier.
