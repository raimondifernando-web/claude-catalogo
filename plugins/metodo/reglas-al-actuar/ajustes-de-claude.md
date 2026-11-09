---
herramientas: Write|Edit|MultiEdit|Bash|PowerShell
patron: \.claude[/\\]settings(\.local)?\.json|\.claude[/\\]hooks[/\\]
---
Vas a cambiar los ajustes o los avisos automáticos (hooks) de Claude en esta computadora (regla 3: lo que corre solo en tu computadora lleva el OK de la persona).
1. Pedí el OK en el chat para ESE cambio, diciendo en criollo qué va a pasar distinto.
2. Antes de tocar, copia del archivo (`settings.json.antes-<tema>`); después, verificá que el JSON sigue válido y que el cambio hace lo que tenía que hacer.
3. En el `env` nunca va una variable general (`DO_NOT_TRACK`, `CI`, `NODE_ENV`): Claude Code también las lee y puede apagar funciones sin que nadie lo note.
4. Si el sistema te frena escribirlo, no le busques la vuelta: dejale a la persona UN comando para pegar que hace la copia, el cambio y termina en «Todo al día ✓».
