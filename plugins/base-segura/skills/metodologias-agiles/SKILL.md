---
name: metodologias-agiles
description: |
  Metodologías ágiles y de gestión de objetivos para cualquier PM, en castellano: elegir y aplicar OKR, Scrum, Kanban,
  Scrumban, Shape Up, Lean Startup, Design Sprint, teoría del cambio y marco lógico, y armar retrospectivas. USAR SIEMPRE
  que pidan o mencionen: «metodología ágil», «OKR / objetivos y resultados clave / KR», «Scrum», «sprint», «backlog»,
  «Kanban», «tablero», «límite de trabajo en curso / WIP», «Scrumban», «Shape Up», «Lean», «teoría del cambio», «marco
  lógico», «retrospectiva», «priorizar / RICE / ICE / MoSCoW», «riesgos / pre-mortem», «RACI / quién decide»,
  «acta de proyecto», «informe de estado», «cómo organizo el trabajo del equipo», «cómo planifico el trimestre», «cómo
  priorizo y hago seguimiento», o pidan revisar OKR o un tablero que ya existen. Sirve para equipos de marketing, ventas, finanzas,
  operaciones, consultoría, proyectos de impacto y personales, no solo software. No instala herramientas ni inventa
  números: si falta un dato, lo pide o lo marca «sin dato».
sync: cowork
---

**Disparador:** por intención (las frases de la `description`). Los agentes `pm-*` la nombran en su ficha: como los
subagentes no heredan skills, si no se carga con la herramienta Skill se lee este archivo con Read.

# Metodologías ágiles: elegir el método y usar solo lo que hace falta

Un método ordena el trabajo para que el equipo vea qué sigue, termine lo que empezó y aprenda. **Usá la menor dosis
de método que resuelva el problema**: un equipo de tres personas con un tablero y una reunión semanal no necesita un
Scrum completo. Si el método agrega más reuniones y papeles de los que quita, se está usando mal.

## Cómo trabajar

1. **Entender la situación** (máximo 3 preguntas, una por vez; si ya está claro, no preguntes): ¿qué trabajo es (campañas,
   ventas, un proyecto, tareas que entran todo el tiempo)? ¿cuántas personas y con qué ritmo? ¿qué duele hoy (no se sabe
   qué sigue, todo queda a medias, no se sabe si se avanza, se trabaja mucho pero no cambia nada)?
2. **Elegir el método** con la tabla de abajo y decir en una frase por qué. Si dos sirven, recomendar uno.
3. **Abrir solo el archivo del método elegido** (`references/`). No cargues los demás.
4. **Entregar algo usable hoy**: el tablero con sus columnas, los objetivos con sus números, el calendario del ciclo, la
   agenda de la retro. No una clase de teoría.
5. **Decir los supuestos** y qué dato falta. Nunca inventes una línea de base, una velocidad ni una meta.

## Qué método para qué problema

| Si lo que pasa es… | Método | Archivo |
|---|---|---|
| No está claro adónde queremos llegar este trimestre/semestre, o no se puede medir | **OKR** | `references/okr.md` |
| Hay que explicar por qué una intervención cambiaría algo (impacto social, ambiental, de largo plazo) | **Teoría del cambio** + marco lógico | `references/teoria-del-cambio.md` |
| Trabajo en bloques con fecha: campañas, lanzamientos, proyectos con entregas cada 1-4 semanas | **Scrum** | `references/scrum.md` |
| Trabajo que entra todo el tiempo (pedidos, contenido, soporte, tareas sueltas) y hay que ordenar el flujo | **Kanban** | `references/kanban.md` |
| Mezcla de las dos: entra trabajo continuo pero también hay metas y reuniones por ciclo | **Scrumban** | `references/scrumban.md` |
| Proyectos grandes y difusos que se atascan; equipo chico y autónomo | **Shape Up** | `references/otros-metodos.md` |
| Hay que probar una idea o negocio nuevo con poco gasto | **Lean Startup** o **Design Sprint** | `references/otros-metodos.md` |
| El equipo repite los mismos problemas, o hay que mejorar cómo se trabaja | **Retrospectiva** y chequeo de salud | `references/retrospectivas.md` |
| Hay más para hacer que tiempo y hay que decidir qué va primero | **Priorización** (ICE, RICE, MoSCoW, costo de demora…) | `references/priorizacion.md` |
| Un proyecto o lanzamiento importante: qué puede salir mal | **Riesgos** y pre-mortem | `references/riesgos.md` |
| Nadie sabe quién decide, o se discute a quién escalar | **RACI**, decisiones y cambios de alcance | `references/roles-y-decisiones.md` |
| Hay que arrancar un proyecto de acuerdo o informar a quien decide | **Acta** e **informe a quien decide** | `references/plantillas-gestion.md` |
| Piden «lo ágil» en general o comparar métodos | Principios y mapa de métodos | `references/agil-general.md` |
| El resultado va a Energía (objetivo → resultado clave → proyecto → tarea) | Mapeo | `references/energia.md` |

Atajo de decisión: **¿el trabajo llega en bloques con fecha o llega siempre?** Bloques → Scrum. Siempre → Kanban. Las dos
cosas → Scrumban. **¿Se sabe qué número tiene que moverse?** No → OKR primero. **¿Hay un cambio social o de largo plazo que
justificar?** → Teoría del cambio.

## Cómo se combinan

- **Teoría del cambio** dice *por qué* y *cómo* cambiaría el mundo. **OKR** dice *qué número* se mueve este ciclo.
- **Scrum, Kanban, Scrumban o Shape Up** organizan *cómo* se hace el trabajo que mueve esos números.
- **Retrospectiva** mejora el método mismo. Se usa con cualquiera de los anteriores.
- Lo que se hace (proyectos, tareas) **nunca** va escrito dentro de un resultado clave: va aparte, atado al KR que mueve.

## Cómo adaptar un método pensado para software

Casi todos nacieron en software. Para otras áreas: cambiá «incremento de producto» por «algo terminado que alguien puede
usar o ver» (una campaña publicada, un informe entregado, un cliente atendido); la «demo» pasa a ser mostrar lo terminado a
quien depende de eso; los puntos de historia casi nunca hacen falta (alcanza con contar tareas terminadas por semana);
y el equipo puede ser de una sola persona: el método sigue sirviendo con tablero, ciclo corto y revisión.

## Errores que conviene frenar

- **Ceremonia sin propósito**: reuniones que nadie usa para decidir. Quitá la que no cambia nada.
- **Todo en curso a la vez**: sin límite de trabajo en curso nada se termina. Es el error más común.
- **Métrica que mide esfuerzo**: horas o tareas hechas en lugar de resultados.
- **Método como disfraz**: llamar «sprint» a una lista de tareas sin objetivo ni fin.
- **Cambiar de método cada mes**: probar uno al menos 3 ciclos antes de juzgarlo.
- **Un solo método para todo**: OKR y Kanban conviven; no compiten.

## Al devolver una revisión

Decir qué se cambió y por qué, una línea por cambio; lo que estaba bien, decir que está bien. No reescribir todo para
imponer un método: ajustar lo mínimo.
