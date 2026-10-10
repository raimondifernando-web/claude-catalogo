---
name: pendientes
description: "Muestra la lista de pendientes de la carpeta de trabajo (.claude/PENDIENTES.md) en una tabla corta: ID, pendiente, prioridad, estado y quién; la prioridad 1 va primero y dice hace cuántos días se actualizó. Usala cuando el usuario escriba '/metodo:pendientes', '/pendientes', 'qué tengo pendiente', 'qué falta en este proyecto'. Solo lee: no cambia nada."
---

# /metodo:pendientes — Qué falta en esta carpeta

1. Corré (con la ruta real del plugin) `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/pendientes.py"` parado en la carpeta de trabajo.
   Si no tenés `CLAUDE_PLUGIN_ROOT`, buscalo con
   `find "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/plugins/cache/claude-catalogo/metodo" -name pendientes.py | sort -V | tail -1`.
2. Pegá la salida tal cual (tabla con la prioridad 1 primero). No la resumas ni la completes de memoria.
3. Si dice «Esta carpeta no tiene lista todavía», ofrecé crearla en el próximo `/metodo:cerrar` con la plantilla
   `templates/PENDIENTES.plantilla.md`; no la crees sin que lo pidan.
4. Para cambiar algo no se edita acá: se hace en el cierre (`/metodo:cerrar`, paso «pendientes del proyecto»).
