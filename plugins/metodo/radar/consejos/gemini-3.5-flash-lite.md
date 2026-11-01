Fuente: https://ai.google.dev/gemini-api/docs/whats-new-gemini-3.6.md.txt (consultada 2026-11-01)
- Usá el ID gemini-3.5-flash-lite.
- Reemplazá thinking_budget por thinking_level. Para extracción, clasificación o ruteo de alto volumen, dejá minimal (el default).
- Para subagentes con llamadas a herramientas, código o pasos de razonamiento, subí thinking_level a medium o high, para que no corte antes de tiempo.
- Quitá temperature, top_p y top_k: están deprecados y la API los ignora.
- No termines la petición con un turno model (prefill): da error 400. Usá system_instruction o salida estructurada.
- Si aparece Malformed_Function_Call con texto antes de la herramienta, revisá los workarounds de la guía.
- Mantené las thought signatures en los turnos de herramientas, requisito de Gemini 3.x.
- Soporta Computer Use como herramienta integrada y mejora la ejecución de código, búsqueda y MCP en flujos de agentes.
