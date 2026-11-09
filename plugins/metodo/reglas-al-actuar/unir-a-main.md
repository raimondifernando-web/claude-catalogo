---
herramientas: Bash|PowerShell
patron: gh\s+pr\s+merge|\bunir-a-main\b|git\s+push\s+\S+\s+(HEAD:)?(main|master)\b
---
Vas a unir trabajo a `main` (regla 3 y regla 13 del método).
1. Antes: las pruebas de CADA proyecto que el cambio toca. Si fallan, arreglá el código (nunca la prueba) y reintentá; si faltan, escribilas. Hasta 3 vueltas, sin preguntarle nada técnico a la persona; después, una frase con qué prueba falla.
2. Lo revisa alguien distinto del autor (otro agente o el revisor que lanza `unir-a-main`).
3. Con controles en GitHub: PR + `gh pr merge --squash --auto`; nunca push directo ni `--force`.
4. Lo que corre solo en la computadora de la persona (hooks, ajustes, instaladores) lleva además su OK para ESE cambio.
5. Antes de subir: `git pull --rebase --autostash`, y solo los archivos tuyos (nunca `git add -A`).

Texto completo de las reglas 3 y 13 del método:

3. **Confirmar antes de lo irreversible** (borrar, mover, renombrar, enviar, publicar, pagar): mostrá qué vas a hacer y esperá el OK. Unir a `main` no lo es: lo deciden los controles automáticos (con las pruebas de CADA proyecto que el cambio toca: si una falla no se une y la sesión misma las arregla —o las escribe si faltan— y reintenta, hasta 3 vueltas, sin preguntarle nada técnico a la persona; el código sin pruebas se dice en voz alta, nunca se une en silencio) (`scripts/unir-a-main`: pruebas aisladas + un revisor independiente que lanza el propio programa, sin opciones que la sesión pueda afirmar; con checks en GitHub, PR + `gh pr merge --squash --auto`). El OK sigue para lo que corre solo en tu computadora (ajustes de Claude, hooks, tareas, instaladores, robots), borrar o reescribir historia y decisiones del negocio. Antes de subir por primera vez un repo que ve otra gente, instalá el control de nombres prohibidos (`scripts/nombres-prohibidos`) y preguntá qué clientes o personas no tienen que salir.

13. **Cierre seguro entre sesiones.** Id `AAAA-MM-DD-tema`. En archivos compartidos cada sesión agrega al final, nunca edita líneas ajenas. Sube solo los archivos que tocó (nunca `git add -A`). Antes de subir: `git pull --rebase --autostash`. Juntar a `main` es un evento al cerrar, de a una sesión por vez, sin pedir OK si pasan los controles (regla 3). Nunca `--force`, nunca `reset --hard`. Si lo que hiciste lo usa otra sesión, **avisale por escrito en su carpeta** (`<carpeta>/.claude/prompts/AAAA-MM-DD-<origen>-aviso-<tema>.md`: qué cambió y qué le toca hacer) y, si está abierta, además con un mensaje directo: la otra sesión no revisa su carpeta sola.
