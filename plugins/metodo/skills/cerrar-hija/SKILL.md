---
name: cerrar-hija
description: "Cierre de una SESIÓN HIJA: una sesión que abrió otra sesión (la coordinadora) y que suele trabajar en la misma carpeta que ella y que otras hijas. La llama /metodo:cerrar sola cuando `sesion_hija.py detectar` dice MODO HIJA. Cierra completo (sesiones y ramas resueltas, lo durable a su lugar, handoff) sin pisar lo compartido: nunca escribe el REANUDAR.md de la carpeta, nunca reacomoda ni sube trabajo de otras sesiones, sube solo sus archivos, deja un TRASPASO para la coordinadora y termina sin abrir sesiones ni archivarse."
---

# /metodo:cerrar-hija — Cerrar una sesión hija sin pisar nada

Disparador: encadenado — el primer paso de `/metodo:cerrar` corre `sesion_hija.py detectar` y, con MODO HIJA, sigue esta skill
en lugar del resto del cierre; `cerrar-check.py` lo detecta solo y mide estos pasos. Prueba de disparo: `scripts/tests/test_sesion_hija.py`.

> ⛔ **Quién la invoca: el usuario**, al escribir `/cerrar` (o `/metodo:cerrar`) en una sesión hija. Claude no cierra por su cuenta.

## Por qué existe
El cierre normal es para la sesión dueña de la carpeta. En una hija que comparte carpeta pisaba tres cosas: el `REANUDAR.md`
(es del hilo principal), el trabajo sin subir de otras sesiones (`pull --rebase --autostash` lo reacomoda y le cambia la huella)
y la decisión de seguir o no (abrir otra sesión y archivarse es de la coordinadora). Este cierre es **igual de completo** que el normal y
cambia solo esas tres cosas.

## Regla de oro
**El último mensaje empieza con `CIERRE DE HIJA ✓ — traspaso: <ruta>`** (o `CIERRE DE HIJA ✗ — falta: …`). La app se lo reenvía a la
coordinadora, y su aviso automático lo reconoce y le pide verificar.

## Lo que NUNCA hace una hija en una carpeta compartida
- Escribir el `REANUDAR.md` de la carpeta (en la raíz o en `.claude/prompts/`). Con carpeta PROPIA (copia suya) sí deja el suyo ahí.
- `git pull`, `rebase`, `--autostash`, `stash`, `checkout`/`switch` de rama, `reset`, `merge`, `push` en la carpeta compartida.
- `git add -A`, `git add .`, `git commit -a`, ni subir trabajo de otra sesión.
- Reescribir líneas ajenas de `CLAUDE.md`, `PENDIENTES.md` o `handoffs/`: solo agrega al final.
- Abrir sesiones, archivarse ni archivar a nadie: eso lo decide la coordinadora.
Un freno automático (`freno-hija.py`) bloquea lo de git y el `REANUDAR.md` ajeno; esta lista vale igual sin él.

## Secuencia
0. **Detectar y sacar la foto** (antes de tocar nada):
   `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/sesion_hija.py" detectar` → copiá la línea. MODO NORMAL → volvé a `/metodo:cerrar` normal.
   `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/sesion_hija.py" foto <cada repo que tocaste>`: la foto de lo ajeno, contra la que se mide al final.
1. **Sesiones y ramas resueltas** (el Paso 0 del cierre normal, igual): tus hijas trabajando → esperá; informes sin leer → leelos;
   ramas sin subir, PR sin resolver, cambios tuyos sin guardar → resolvelos vos. Al usuario solo le llega lo que solo él decide.
2. **Lo durable a su lugar** (paso 3 del cierre normal, igual de riguroso): reglas al `CLAUDE.md` de la carpeta, decisiones y relato al handoff,
   lo pendiente a `PENDIENTES.md` (solo filas tuyas, ID estable). En archivos compartidos, solo agregás al final.
3. **Handoff** si tocaste 3 o más archivos o tomaste 2 o más decisiones: `handoffs/AAAA-MM-DD-tema.md`.
4. **Subir solo lo tuyo, sin tocar la carpeta compartida:**
   `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/sesion_hija.py" subir <repo> -m "cierre AAAA-MM-DD-tema"` → sube tus archivos (los que el registro de
   ediciones dice que tocaste) a una rama `hija/<nombre>-<fecha>`, armando el cambio aparte. Lo tuyo que el registro no vio va con
   `--incluir <ruta>` (si es de otra sesión, el programa lo rechaza). Después: `gh pr create --head <rama> --fill` y
   `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/unir-pr" <N>` (une solo si pasan los controles; si dice «Falta: …», va al traspaso).
   Si `subir` dice «cambió en GitHub mientras tanto», no fuerces: anotalo en el traspaso para la coordinadora.
5. **Traspaso a la coordinadora.** Escribí un borrador con estas secciones, todas con contenido real:
   `## Qué se hizo` (archivos, guardados, ramas, PR y el estado de sus controles consultado) · `## Qué sigue` (el próximo paso exacto) ·
   `## Decisiones de la persona` (cada una con su **cita textual entre «»** y la fecha, o «ninguna») · `## Pendientes` (qué, dónde, qué cuidado) ·
   `## Sesiones` (tus hijas y las independizadas: id, título, estado, quién las sigue) ·
   `## Continuación propuesta` («sí» con el pedido ya escrito para una sesión nueva, o «no, cerrar» con el porqué; proponés, no abrís nada).
   Después: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/sesion_hija.py" traspaso --borrador <archivo>` → escribe `.claude/prompts/TRASPASO-<fecha>-<nombre>.md`
   y una copia idéntica en la carpeta de notas del grupo de sesiones. Si dice «incompleto», completalo y repetí.
   Con carpeta propia: además dejá tu `REANUDAR.md` en tu carpeta, como el cierre normal.
6. **Comprobar:** `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/cerrar-check.py"` (detecta el modo hija solo): foto sin cambios, `REANUDAR.md` ajeno
   intacto, traspaso presente y sellado, nada tuyo sin subir. Si da ✗, resolvelo y repetilo. Pegá su salida.
7. **Terminar:** `CIERRE DE HIJA ✓ — traspaso: <ruta>` + 2-3 líneas en criollo (qué quedó, qué proponés) + «La sesión que me abrió lo
   verifica y decide si sigue». **No abras sesiones ni te archives.**

## Lado de la coordinadora
Cuando llega la nota `CIERRE DE HIJA ✓`, su aviso automático le pide: (1) `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/sesion_hija.py" recibir <id de la hija>`,
que verifica en el disco y en GitHub (lo que cuenta la hija no es la prueba); (2) con ✓, pasa los pendientes a su lista, decide continuar
(abre una sesión nueva con el traspaso como pedido) o cerrar, y archiva a la hija; con ✗, le manda a la hija qué falta y no archiva.
Las hijas de la hija que comparten carpeta se archivan con ella; las independizadas no: la coordinadora decide si las sigue.
