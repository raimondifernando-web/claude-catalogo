---
herramientas: Bash|PowerShell
patron: git\s+push\b.*(--force|\s-f\b)|git\s+reset\s+--hard|filter-branch|filter-repo|gh\s+repo\s+delete|\brm\s+(-\S*\s+)*-\S*[rR]|git\s+clean\b|\s-delete\b|Remove-Item\b.*-Recurse
---
Vas a borrar algo o a reescribir la historia (regla 3 y regla 13 del método).
1. Nunca `--force` ni `reset --hard`: si hace falta reacomodar, una rama nueva o un commit que deshace.
2. Antes de borrar, mirá qué hay (contenido, no solo el nombre). Trabajo propio sin copia: preguntá. Lo regenerable (cachés, compilados) se borra sin preguntar.
3. Borrar o reescribir historia y borrar un repo lleva el OK de la persona en el chat, para ESA acción, con lo que se pierde dicho en criollo. Preferí la Papelera a borrar de verdad.
4. Primero el cambio, después la prueba del resultado; recién ahí se borra lo sobrante. Nunca aplicar y borrar en el mismo comando.
