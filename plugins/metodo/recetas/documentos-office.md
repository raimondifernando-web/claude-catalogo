---
name: documentos-office
triggers: word docx excel xlsx powerpoint pptx pdf planilla presentacion informe documento hoja calculo
---
Receta para armar documentos de oficina (Word, Excel, PowerPoint, PDF).
1. Cargá con la herramienta Skill la que corresponde al formato: `docx`, `xlsx`, `pptx` o `pdf` (las de Anthropic). Si el origen viene en otro formato, pasalo a texto antes con `markitdown`.
2. Para analizar una planilla usá `excel-analysis`; para un texto que sale a un tercero, pasalo por `humanizalo` antes de mostrarlo.
3. Un subagente NO hereda estas skills: nombralas en SU prompt y comprobá en el resultado que las usó.
4. Si el documento reemplaza a otro, no borres el original hasta comparar el contenido texto contra texto (regla 15).
