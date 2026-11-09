---
herramientas: Bash|PowerShell|mcp__ccd_session__start_session
patron: ^mcp__ccd_session__start_session|git\s+worktree\s+add|copias-de-trabajo\s+nueva
---
Vas a abrir otra sesión o copia de trabajo: texto completo de las reglas 11 y 20 del método.

11. **Una sesión, un tema.** Varias sesiones pueden compartir carpeta y rama (cada cierre sube solo lo suyo, regla 13); lo más prolijo es copia y rama propias `<tema>/<AAAA-MM-DD>`, nunca `main` (salvo en un repo propio de un solo tema, donde se puede trabajar en `main`; `/metodo:otra-sesion`). Es obligatorio cuando necesitan ramas distintas o van a editar el mismo archivo a la vez. Ramas cortas y cambios chicos (se unen en horas, no días); las uniones hacen cola y prueban la combinación con el `main` nuevo. Antes de abrir una sesión hija que va a editar código, corré `scripts/ramas-que-pisan <archivos que va a tocar>` (nunca dos sobre el mismo archivo grande), y creá su copia con `scripts/copias-de-trabajo nueva <tema>` (queda DENTRO del proyecto, en `.worktrees/`).

20. **¿Seguir acá o abrir otra sesión?** Trabajo mediano o grande, que no toca archivos de otra sesión y se hace con un nivel más barato (el ruteo de la regla 18): proponé una sesión aparte, con el pedido completo (qué hacer, qué archivos, cómo se sabe que está hecho, qué no tocar, qué necesita tu «sí») y su línea «Ruteo:». Una etapa del trabajo es una sola elección: sus tareas la heredan; no se abre una sesión por tarea. Al volver, revisá lo que entregó antes de decir «hecho»: lo que cuenta la otra sesión es su relato, no la prueba. No para preguntas, arreglos chicos ni si pisaría archivos ajenos. Copia aparte del proyecto: `/metodo:otra-sesion`.
