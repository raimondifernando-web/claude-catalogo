# paneles

## 0.5.4 — 2026-10-17
Retoques al panel «Uso y actividad»:
- **«Actividad» va en una barra de punta a punta** que separa el panel en dos.
- **Más compacto arriba:** sin huecos entre los bloques de Uso, para darle lugar a Actividad.
- **Sin textos repetidos:** el «nada trabajando» de la barra ya no aparece (queda «Nada activo.» en «Ahora»); con agentes corriendo se ve «● N trabajando».

## 0.5.3 — 2026-10-17
- **«Uso» y «Actividad» ahora son un solo panel, «Uso y actividad».** Arriba, lo de siempre (contexto, límites del plan, qué gastó más); abajo, la actividad de agentes, subagentes y skills. `/uso` y `/actividad` abren el mismo panel.
- **El detalle de colores del contexto (los puntitos) ahora se pliega:** arranca cerrado y se abre tocando «Detalle del contexto».
- Pruebas actualizadas (49).

## 0.5.2 — 2026-10-17
Arreglo en «Actividad»: ahora los agentes se ven encendidos mientras trabajan.
- Antes, el panel solo se enteraba de que un agente empezó por un aviso que no le llega a todos (los que lanza una skill o se reanudan con un mensaje terminaban sin haber avisado). Resultado: aparecían recién al terminar, o nunca. Ahora cada vez que un agente empieza un turno o usa una herramienta, el panel lo anota en ese momento y lo muestra en verde (sin preguntar cada tanto). Sigue guardando solo el tipo, nunca el pedido ni la descripción.
- El aviso «terminó» llega cuando el agente entrega su informe, aunque siga trabajando en segundo plano (un caso real: «terminó» a los 12 s y siguió 13 minutos). Ahora, si el agente vuelve a hacer algo después de esa parada, vuelve a verde hasta la parada final.
- Un agente anotado dos veces cuenta una sola. Pruebas nuevas (49 en total).

## 0.5.1 — 2026-10-16
Arreglo de seguridad: el panel único de 0.5.0 había perdido tres protecciones de 0.3.1/0.4.0.
- **git no ejecuta nada de la carpeta ajena.** Todas las llamadas a `git` vuelven a apagar `core.fsmonitor` y `core.untrackedCache` y a no tomar bloqueos opcionales. Sin esto, un repositorio ajeno con `core.fsmonitor=<comando>` ejecutaba ese comando en tu Mac al abrir el panel.
- **No sube a carpetas madre.** Busca la lista solo en la carpeta de la sesión y en la raíz de su repo, no en 3 niveles más arriba (podía mostrar la de otro proyecto o cliente).
- **Topes de tamaño.** Un `PENDIENTES.md` de más de 300.000 caracteres se corta, se leen como máximo 500 filas y 200 tareas: un archivo enorme ya no cuelga el panel.
- Pruebas nuevas para cada una (47 en total).

## 0.5.0 — 2026-10-16
- **Un solo panel, «Tareas y pendientes», en lugar de «Pendientes» y «Tareas».** Arriba, «ESTA SESIÓN» (las tareas de la sesión, con `.claude/tareas.json` o lo que la sesión anota); abajo, «PENDIENTES QUE ARRASTRAMOS» (`.claude/PENDIENTES.md`: prioridad 1 abierta, 2 y 3 plegadas). Lo que está en las dos listas se marca «en sesión» abajo; no se esconde. Se abre con `/tareas` (y `/pendientes`).
- Símbolos: ○ por hacer · ◐ en curso · ✋ espera algo tuyo · ✅ hecho · › / ⌄ detalle · ↳ espera a la de arriba.
- Tocar un pendiente despliega su detalle (de qué depende, qué desbloquea, esfuerzo, quién). Los «Cambios» salen de comparar con la versión anterior en git (solo lectura).
- Uso y Actividad no cambian. Si ya tenías abiertos los paneles viejos, se reemplazan solos al empezar una sesión nueva.
- Probado con 44 pruebas automáticas.

## 0.4.0 — 2026-10-16
- **Cuarto panel, «Actividad»** (`/actividad`): ves qué agente, subagente o skill se activó, a quién llamó cada uno y cuáles están trabajando ahora. Árbol por sesión: cada skill cuelga del agente que la usó y cada subagente de quien lo lanzó. El agente se dibuja como un Bicho, el subagente como una luciérnaga y la skill como una hoja de archivo (son instrucciones); verde y animado = trabajando, gris = terminó. En la terminal se ven como símbolos de texto.
- **Qué guarda (único panel que escribe):** un archivo por día y por sesión en `<carpeta de Claude>/actividad/` con tipo, nombre, hora, id corto de sesión y carpeta. Nunca el pedido, la descripción ni los argumentos. No manda nada afuera. Se registra solo, sin que nadie corra nada.
- Los paneles de Uso, Pendientes y Tareas no cambian.

## 0.3.1 — 2026-10-15
- **Pendientes y Tareas ya no suben a carpetas de afuera de tu repositorio.** Buscaban la lista hasta 3 carpetas más arriba y podían mostrar la de otro proyecto. Ahora miran solo la carpeta de la sesión y la raíz de su repo.

## 0.3.0 — 2026-10-14
Los tres paneles quedan iguales a los de Fernando.
- **Tareas ya no queda vacío.** Solo se actualizaba con un reloj interno que en la app puede no latir; ahora también se actualiza con cada mensaje y al terminar cada turno.
- **Los tres paneles se abren con tu mensaje.** Un panel que se abre solo no se dibuja en ventanas angostas; el que se abre como respuesta a tu mensaje, sí. Si cerrás un panel a mano, no se vuelve a abrir solo hasta que lo pidas con su comando (`/uso`, `/pendientes`, `/tareas`).
- **Carpeta que cambia.** Si la sesión quedó en una subcarpeta, Pendientes y Tareas buscan la lista en las carpetas de arriba (hasta 3 niveles) y el panel dice «Lista de <carpeta>».
- **Panel que no se vacía.** Si la app reinicia sus valores (otra sesión, /clear), los paneles se vuelven a llenar solos.
- **Uso y errores.** Si una lectura falla al arrancar, el panel igual se abre; un error al actualizar Pendientes ya no deja avisos sueltos.
- Probado con pruebas automáticas (41); falta confirmarlo abriendo una sesión nueva.

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
