# Requisitos — paneles

| Panel | Necesita | Sin eso |
|---|---|---|
| Uso | La app de escritorio de Claude Code (los paneles se dibujan a la derecha) | En la terminal se ve una versión en texto |
| Pendientes | Un archivo `.claude/PENDIENTES.md` en la carpeta (o en la raíz de su repo) con las tablas de 8 columnas | Dice «Esta carpeta no tiene lista de pendientes todavía» y no hace nada más |

No piden claves, no escriben archivos y no mandan datos afuera. El panel «Pendientes» usa `git` (solo lectura) para mostrar qué cambió; sin git, sigue funcionando y lo avisa.
