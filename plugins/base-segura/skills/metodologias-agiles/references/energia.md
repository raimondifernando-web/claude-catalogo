# Cómo se mapea a Energía

Energía es la herramienta donde viven los objetivos y las tareas (sobre Obsidian o Notion). Su jerarquía es
**Objetivo → Resultado clave (KR) → Proyecto → Tarea (→ pasos para tachar)**. Esta skill escribe el texto; cargarlo en Energía lo
hace la persona o la sesión dueña de Energía. Si el proyecto no usa Energía, este archivo no aplica: usá `okr.md` y el método elegido.

## Qué es cada cosa

| En Energía | Qué es | Método de origen |
|---|---|---|
| **Objetivo** | Adónde se quiere llegar; se mide con un número, no es trabajo. Lleva título, nota, fechas y responsable | OKR (objetivo) |
| **Resultado clave** | El número que dice que se llegó. Lleva **inicio, actual, meta, unidad** (hasta 20 caracteres) y responsable | OKR (KR) |
| **Proyecto** | Lleva días y varias tareas; apunta a uno o más objetivos. Su impacto se mide **contra los KR** | Iniciativa / épica / apuesta (Shape Up) |
| **Tarea** | Se resuelve en horas; cuelga de un proyecto. Su impacto se mide **contra su proyecto** | Elemento del backlog / tarjeta del tablero |
| **Pasos** | Lista para tachar dentro de una tarea; sin prioridad ni estado propios. Si un paso necesita prioridad, es otra tarea | Subtareas |

## Estados y tablero Kanban

Energía ya trae las columnas de un tablero: **Sin empezar · En curso · En revisión · Hecho** (más Bitácora y Cancelado).
Una tarea «En revisión» es la que espera un dato o un visto bueno de otra persona, con al lado qué falta.
Lo que Energía **no** impone: **límite de trabajo en curso**. Es una práctica de Kanban (`kanban.md`) que el equipo se pone solo.

## Prioridad (la cuenta de Energía)

Cada nivel vale: Bajo = 1, Medio = 2, Alto = 3. **Puntaje = 2 × impacto − esfuerzo**: 3 o más → Alta · 1 o 2 → Media · 0 o menos → Baja.
- **Esfuerzo de una tarea**: Bajo hasta 1 h · Medio 1-3 h · Alto más de 3 h. **De un proyecto**: Bajo hasta 2 días · Medio hasta 2 semanas · Alto más.
- **Impacto de una tarea (contra su proyecto)**: Alto = sin ella el proyecto no se cumple · Medio = ayuda o ahorra tiempo · Bajo = mejora menor.
- **Impacto de un proyecto (contra los KR)**: Alto = mueve directo un KR · Medio = ayuda a uno o baja un riesgo chico · Bajo = mejora menor.
Si falta el impacto o el esfuerzo, la prioridad se elige a mano.

## Cómo traducir cada método

- **OKR** → el objetivo y sus KR van tal cual (`okr.md`, formato «Si el destino es Energía»).
- **Scrum** → no hay «Sprint» en Energía: el ciclo se expresa con las **fechas** de los proyectos y la **meta del ciclo** en la nota del objetivo.
  El Product Backlog son los proyectos y tareas en «Sin empezar», ordenados por prioridad.
- **Kanban / Scrumban** → los estados de Energía son las columnas; el límite de trabajo en curso se anota en la nota del objetivo o del proyecto.
- **Shape Up** → cada «apuesta» es un proyecto con fechas del ciclo de 6 semanas; las tareas de la apuesta cuelgan de él.
- **Teoría del cambio** → los **resultados** de la TdC son los KR; las **actividades y productos** son proyectos y tareas; los **supuestos** van en la nota del objetivo.
- **Retrospectiva** → las acciones salen como tareas (con dueño y fecha) en el proyecto o en una lista de mejora del equipo.

## Qué no hacer

- No escribir una **tarea** como resultado clave.
- No inventar el **inicio** de un KR: si no hay dato, `sin dato` y primera tarea «medirlo».
- No meter proyectos dentro del texto del objetivo: van aparte, atados al KR.
