# PENDIENTES — <proyecto>

> Lista propia de este proyecto. La mantiene `/metodo:cerrar`, la muestra `/metodo:arrancar` (los de prioridad 1) y se ve completa con `/metodo:pendientes`.
> **Cómo se edita:** cambiar la fila (prioridad, estado) y agregar una línea en «Cambios» al final, con fecha. Nunca renumerar:
> un ID cerrado pasa a «Hechos». Cada sesión toca solo SUS filas. Respetar el formato de las tablas (8 columnas).
>
> Prio = la cuenta impacto − esfuerzo (Bajo 1 · Medio 2 · Alto 3): 1 = Alta (más de 0) · 2 = Media (0) · 3 = Baja (menos de 0).
> Las fechas límite van en «Fechas», no en Prio. Esf. = Bajo/Medio/Alto: una tarea, Bajo hasta 1 h · Medio 1-3 h · Alto más de 3 h;
> un proyecto, Bajo hasta 2 días · Medio hasta 2 semanas · Alto más, o depende de otros. Impacto de una tarea, contra su proyecto
> (Alto = sin ella no se cumple · Medio = ayuda o ahorra tiempo · Bajo = mejora menor); el de un proyecto, contra tus objetivos.
> Proyecto = lleva días y varias tareas: su fila empieza con `Proyecto:` y lleva su propio estado; cada tarea suya dice
> `parte de <ID>` en «Depende de» (misma sección). Tarea = horas. Pasos de una tarea, en su texto: `Pasos: ☐ … ☑ …`.
> Estado (solo estos): pendiente · en curso · espera dato · espera OK · hecho. Quién: el nombre de la persona (o C = Claude).
> **Si hay más de una sesión en el proyecto (se pisan si no se cumple):** (1) antes de crear un ID, releé el archivo y usá
> el siguiente libre de la letra; (2) cada sesión toca solo SUS filas; (3) «Cambios» es append-only: se agrega al final,
> nunca se reescribe una línea ajena; (4) `git pull --rebase --autostash` antes de guardar la lista, y guardar por archivo
> (solo este). `pendientes-check.py` avisa de IDs repetidos y de marcas de conflicto (`<<<<<<<`).
> **Toda sesión que cierra deja una línea fechada en «Cambios»**, aunque sea «sin cambios»: así se sabe que está al día.
> Secciones: `## <Letra> · Nombre` (una letra por tema; el ID es letra + número, ej. A1).

## A · Tema principal
| ID | Pendiente | Prio | Estado | Depende de | Esf. | Quién | Origen |
|---|---|---|---|---|---|---|---|
| A1 | Ejemplo: borrá esta fila y escribí el primer pendiente real | 3 | pendiente | — | Bajo | C | plantilla |

## Fechas
| Fecha | Qué |
|---|---|
| 2099-01 | Ejemplo: borrá esta fila (formato AAAA-MM-DD, AAAA-MM-DD HH:MM o AAAA-MM) |

## Hechos
Los IDs cerrados van acá, con fecha y una línea de qué se hizo.

## Cambios
- AAAA-MM-DD · creada desde la plantilla.
