---
name: otra-sesion
description: "Abrir una segunda sesión de Claude sobre el mismo proyecto sin que se pisen: crea una copia propia de la carpeta (git worktree) con su rama, y entrega el texto de arranque para la ventana nueva. Usala cuando el usuario diga 'quiero abrir otra sesión / otra ventana para X mientras sigo con Y', 'vamos a trabajar dos a la vez', 'otra persona va a trabajar en esto al mismo tiempo', o cuando /metodo:arrancar detecte más de una copia del proyecto."
---

# /metodo:otra-sesion — Dos sesiones a la vez sin pisarse

El problema que resuelve: dos ventanas de Claude sobre **la misma carpeta** pueden convivir en la misma rama (cada
cierre sube solo lo suyo), pero **no en ramas distintas** — cambiar de rama reescribe el disco para las dos — ni
editando el mismo archivo a la vez. Y si nadie le dice a la segunda sesión cuál es
su tema, termina haciendo el trabajo de la primera. Esta skill deja a cada sesión en **su propia copia, su propia
rama y con su propio texto de arranque** (reglas 11 y 12 del método).

## Antes de usar esta skill — requisitos
| Necesita | Cómo verificar | Si falta, respondé |
|---|---|---|
| Que la carpeta de trabajo sea un repositorio git | `git rev-parse --is-inside-work-tree` | «Sin repositorio no se puede separar el trabajo de dos sesiones. Lo creamos primero: es el paso Higiene de tu portal (`git init` + primer guardado). ¿Lo hacemos ahora?» |
| `git` instalado | `git --version` | Viene con las herramientas de desarrollo de Apple; el chequeo del catálogo (`docs/CHEQUEO.md`) ya lo verifica |

Sin claves. Nada sale de la computadora: crear la copia es local; subir la rama lo hace `/metodo:cerrar` al final.

## Secuencia (mostrar y ejecutar solo con «sí»)
1. **Verificá** que estás en un repositorio (tabla de arriba) y que el árbol está limpio o con cambios guardados
   (`git status --short`). Si hay cambios sin guardar de la sesión actual, primero proponé guardarlos
   (`git add <los archivos que tocó esta sesión> && git commit -m "avance antes de abrir otra sesión"`); la copia
   nueva parte de lo último guardado. **Nunca `git add -A`:** si ya hay otra sesión en esta carpeta, se llevaría su
   trabajo a medias. Si `git status` muestra cambios que no son de esta sesión, dejalos como están y avisalo.
2. **Pedí el tema en una palabra** (ej. `cotizacion-lopez`, `obra-rivera`). Con eso armás:
   - **Rama:** `<tema>/<AAAA-MM-DD>` (fecha de hoy, `date +%F`).
   - **Copia:** carpeta hermana `../<carpeta>-<tema>` (ej. `~/Documents/Estudio-Claude-cotizacion-lopez`).
3. **Mostrá y proponé** los dos comandos, y ejecutá el primero solo con «sí»:
   ```
   git worktree add ../<carpeta>-<tema> -b <tema>/<AAAA-MM-DD>
   ```
   y para la ventana nueva (esto lo hace el usuario, en una Terminal nueva o en la app):
   ```
   cd ../<carpeta>-<tema> && claude
   ```
   Verificá con `git worktree list`: tienen que aparecer las dos copias, cada una con su rama.
4. **Entregá el texto de arranque de la segunda sesión**, listo para pegar en la ventana nueva (plantilla abajo).
   Es lo más importante del paso: sin ese texto la sesión nueva no sabe su tema ni su límite.
5. **Avisale al usuario cómo termina:** cuando el tema esté listo, en esa ventana escribe `/metodo:cerrar`: sube la
   rama, ofrece juntarla a `main` (con «sí», de a una sesión por vez) y ofrece borrar la copia
   (`git worktree remove ../<carpeta>-<tema>`, con «sí»). **Nunca se borra la copia de otra sesión.**

## Plantilla del texto de arranque para la segunda sesión
````
═══ PARTE A — CONTRATO ═══
ROL: [el mismo rol del proyecto, acotado al tema: "trabajás la cotización López para el estudio…"]
ALCANCE: SOLO <tema>. Carpeta de trabajo: <ruta de la copia>.
Fuera de alcance (→ a quién): todo lo que no sea <tema> → la sesión principal del proyecto (anotarlo, no hacerlo).
REGLAS: verificar antes de afirmar · secretos nunca en el chat · confirmar antes de borrar/enviar/publicar ·
no adular · leer CLAUDE.md y el último handoff antes de tocar nada · en CLAUDE.md y handoffs agregar al final,
nunca reescribir (hay otra sesión abierta).

═══ PARTE B — ESTADO ═══
Sesión nueva para <tema>, abierta desde la sesión principal el AAAA-MM-DD.
Copia: <ruta de la copia> · Rama: <tema>/<AAAA-MM-DD>
Contexto mínimo: [2-3 líneas: qué es el tema, qué hay hecho, dónde está lo que necesita]
PENDIENTES (en este orden):
1. [primer paso concreto del tema]
2. ...
Arrancá con /metodo:arrancar: verificá que estás en la copia y la rama de arriba (pwd + git branch --show-current)
y confirmá: "Leí el estado. El próximo paso es [X]. ¿Arrancamos?"
````

## Reglas
- **Una sesión, un tema, una copia** (regla 11). Si el usuario quiere una tercera sesión, se repite la skill con otro tema.
- **La sesión principal sigue en su carpeta y su rama**; no se mueve nada de lo que ya tenía abierto.
- **Nunca `--force`, nunca `reset --hard`, nunca borrar copias ajenas.** Si algo falla, mostrá el error tal cual.
- Si la segunda sesión la va a usar **otra persona** en otra computadora, la copia no sirve (es local): en ese caso
  la otra persona clona el repositorio y trabaja en su rama `<tema>/<fecha>`; las reglas 12 y 13 aplican igual.

## Qué NO es esta skill
No es para dos proyectos distintos (cada proyecto ya tiene su carpeta). No sube nada por sí sola: subir y juntar a
`main` es de `/metodo:cerrar`. No reemplaza a `/metodo:arrancar`: la ventana nueva igual arranca con esa.
