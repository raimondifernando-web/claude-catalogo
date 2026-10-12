# paneles

## 0.2.1 — 2026-10-11
- **El panel Tareas se arma solo.** Además de lo que anota la sesión, muestra lo que sale de `.claude/PENDIENTES.md` y de git: lo que está «en curso» (▶), lo urgente (prioridad 1) y lo nuevo de esta semana (○), y lo que se cerró desde la versión anterior del archivo, hasta 2 días atrás (✓ tachado). Si la misma tarea está también en `tareas.json`, manda PENDIENTES. Sin lista de pendientes, el panel funciona como antes. Nadie tiene que acordarse de actualizarlo.

## 0.2.0 — 2026-10-11
- Tercer panel, **Tareas**: las tareas de la sesión en vivo (lo hecho se tacha). Se alimenta de lo que la sesión anota con sus herramientas de tareas, o de `.claude/tareas.json` de la carpeta si existe. Se abre solo y con `/tareas`.
- Arreglo: los paneles podían nacer vacíos al abrir una sesión nueva (se arreglaban solos recién cuando cambiaba el archivo). Ahora cada sesión empieza de cero. Probable causa, no reproducida en las pruebas automáticas: confirmar abriendo una sesión nueva.

## 0.1.0 — 2026-10-10
- Primera versión. Dos paneles a la derecha de la app, que se abren solos al empezar una sesión:
  - **Uso**: cuánto contexto llevás gastado (partido por categoría), cuánto te queda del cupo del plan y qué comando gastó más en la sesión. Se abre también con `/uso`.
  - **Pendientes**: la lista de `.claude/PENDIENTES.md` de la carpeta donde trabajás (o de la raíz de su repo): lo que va ya, lo de esta semana, los cambios y la próxima fecha. Se abre también con `/pendientes`. Si la carpeta no tiene lista, lo dice en castellano.
- Solo leen: no escriben archivos ni mandan nada a internet.
