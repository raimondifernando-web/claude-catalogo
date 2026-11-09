---
herramientas: Bash|PowerShell
patron: gh\s+repo\s+(create|fork)|git\s+remote\s+add
---
Vas a crear o conectar un repo: antes de subir por primera vez uno que ve otra gente, instalá el control de nombres prohibidos (`scripts/nombres-prohibidos`) y preguntá qué clientes o personas no tienen que salir (regla 3).

3. **Confirmar antes de lo irreversible** (borrar, mover, renombrar, enviar, publicar, pagar): mostrá qué vas a hacer y esperá el OK. Unir a `main` no lo es: lo deciden los controles automáticos (con las pruebas de CADA proyecto que el cambio toca: si una falla no se une y la sesión misma las arregla —o las escribe si faltan— y reintenta, hasta 3 vueltas, sin preguntarle nada técnico a la persona; el código sin pruebas se dice en voz alta, nunca se une en silencio) (`scripts/unir-a-main`: pruebas aisladas + un revisor independiente que lanza el propio programa, sin opciones que la sesión pueda afirmar; con checks en GitHub, PR + `gh pr merge --squash --auto`). El OK sigue para lo que corre solo en tu computadora (ajustes de Claude, hooks, tareas, instaladores, robots), borrar o reescribir historia y decisiones del negocio. Antes de subir por primera vez un repo que ve otra gente, instalá el control de nombres prohibidos (`scripts/nombres-prohibidos`) y preguntá qué clientes o personas no tienen que salir.
