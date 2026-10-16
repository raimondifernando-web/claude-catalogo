# Requisitos — paneles

| Panel | Necesita | Sin eso |
|---|---|---|
| Uso | La app de escritorio de Claude Code (los paneles se dibujan a la derecha) | En la terminal se ve una versión en texto |
| Tareas | Nada (usa las tareas de la sesión; opcional `.claude/tareas.json`) | Dice «Sin tareas todavía» |
| Pendientes | Un archivo `.claude/PENDIENTES.md` en la carpeta (o en la raíz de su repo) con las tablas de 8 columnas | Dice «Esta carpeta no tiene lista de pendientes todavía» y no hace nada más |
| Actividad | Nada (se alimenta sola de los agentes y skills que usás) | Dice «Nada activo» y «Todavía nada hoy» |

No piden claves y no mandan datos afuera. Uso, Pendientes y Tareas no escriben archivos; Actividad guarda un registro liviano (tipo, nombre, hora, id de sesión y carpeta; nunca contenido) en `actividad/` dentro de tu carpeta de Claude, y sus archivos de más de 90 días se pueden borrar sin perder nada. El panel «Pendientes» usa `git` (solo lectura) para mostrar qué cambió; sin git, sigue funcionando y lo avisa.
