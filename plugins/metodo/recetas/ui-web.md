---
name: ui-web
triggers: ui ux interfaz pantalla pantallas dashboard tablero landing prototipo prototipos mockup diseño design html css frontend web app visual grafico graficos charts dataviz
---
Receta para construir pantallas web (interfaces, tableros, landings).
1. **Antes de escribir una sola línea de estilo**, cargá con la herramienta Skill las que tengas instaladas de esta lista, en este orden: `frontend-design` (dirección estética y tipografía) → `dataviz` (colores y reglas de gráficos) → `ui-design-system` (tokens como variables CSS). Si una no está, seguí con las otras y decilo en una línea.
2. **Quién construye:** un agente de frontend (por ejemplo `frontend-developer`) más la skill `frontend-ui-engineering` (accesible y responsive). Mirá qué agentes tenés con `/agents`.
3. **Un subagente NO hereda las skills de esta sesión:** nombralas por nombre en SU prompt («cargá con la herramienta Skill: …») y comprobá en el resultado que las usó.
4. **Antes de mostrar el resultado:** revisalo con `design:design-critique` y `design:accessibility-review` si las tenés, y sacá capturas en escritorio y celular con `webapp-testing`.
5. **Costo (regla 16):** borradores con datos inventados en un modelo barato; el modelo grande solo para la revisión final; varios agentes a la vez solo con tu «sí» y el costo estimado.
