# Requisitos — paneles

| Panel | Necesita | Sin eso |
|---|---|---|
| Uso | La app de escritorio de Claude Code (los paneles se dibujan a la derecha) | En la terminal se ve una versión en texto |
| Tareas y pendientes | Nada obligatorio: arriba van las tareas de la sesión (opcional `.claude/tareas.json`); abajo, `.claude/PENDIENTES.md` de la carpeta (o la raíz de su repo) con las tablas de 8 columnas | Sin tareas dice «Sin tareas todavía»; sin lista dice «Esta carpeta no tiene lista de pendientes todavía» |
| Actividad | Nada (se alimenta sola de los agentes y skills que usás) | Dice «Nada activo» y «Todavía nada hoy» |

No piden claves y no mandan datos afuera. Uso y Tareas y pendientes no escriben archivos; Actividad guarda un registro liviano (tipo, nombre, hora, id de sesión y carpeta; nunca contenido) en `actividad/` dentro de tu carpeta de Claude, y sus archivos de más de 90 días se pueden borrar sin perder nada. El panel «Tareas y pendientes» usa `git` (solo lectura) para mostrar qué cambió; sin git, sigue funcionando y lo avisa.
