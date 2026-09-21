---
name: plan-semanal-estudio
description: >
  Guía la reunión semanal del estudio (15-20 min) y produce el plan de la semana.
  Usala cuando necesitás armar el plan semanal, ver qué frena cada proyecto,
  preparar la reunión de equipo, definir compromisos, hacer el lookahead de las
  próximas semanas, o cuando alguien dice "qué hacemos esta semana", "Last Planner",
  "Lean", "lookahead", "compromisos", "qué frena el proyecto X".
  Salida: (a) plan de la semana por persona y (b) mirada a 4-6 semanas por proyecto.
version: "0.1.0"
origen: >
  Creada para el catálogo de Consultoría IA; modelo de datos inspirado en
  Last Planner System (LCI) y jeffersonbim/lean-planning-mcp (MIT).
sync: si
user-invocable: true
---

# Plan Semanal del Estudio

Guiás la reunión semanal. Sos quien toma notas y arma el documento — el equipo habla,
vos estructurás. Al final producís el plan listo para pegar en Drive o ClickUp.

## Antes de usar esta skill — requisitos

| Necesita | Cómo verificar | Si falta, hacé esto |
|---|---|---|
| Lista de tareas activas del estudio | Pegá la lista de tareas activas del estudio (puede ser texto dictado, un listado o las notas de la reunión); si tenés el conector de ClickUp u otra herramienta de tareas conectada, Claude la lee directo. No pidas ninguna clave. | Pedile al usuario que pegue o dicte los proyectos activos y qué está en proceso. |

---

## Paso 1 — Revisión de la semana anterior

Si hay notas de la semana anterior (plan, compromisos), pedílas o leelas del chat.
Si no hay nada anterior, saltás este paso sin avisar.

Para cada compromiso de la semana pasada, preguntá (en grupo, no uno por uno si el equipo
puede responder juntos):

> "¿Qué se cumplió de lo que habíamos prometido? ¿Qué no, y por qué?"

Registrá las causas de incumplimiento en la plantilla de plan. Las categorías son:
- **Cliente no definió** (falta definición, aprobación o firma del cliente)
- **Municipio/permiso** (trámite en curso, sin respuesta)
- **Especialista** (falta dato de estructuralista, instalaciones, topógrafo, etc.)
- **Material** (proveedor, cotización, muestra pendiente)
- **Prerequisito** (tarea anterior sin terminar dentro del estudio)
- **Estimación** (la tarea llevó más tiempo del previsto)
- **Cambio de alcance** (el cliente o el proyecto cambió)
- **Otro** (anotar qué)

⚠️ Las causas son para destrabar, no para evaluar personas. No son un registro de quién
falló — son un registro de qué sistema frenó el trabajo.

---

## Paso 2 — Lookahead: qué frena los próximos proyectos

Para cada proyecto activo, preguntá:

> "¿Qué tiene que estar listo en las próximas 4-6 semanas, y qué lo frena?"

Usá la plantilla de lookahead (`assets/plantilla-lookahead.md`). Para cada hito:
- ¿Qué falta para poder hacerlo? (restricción)
- ¿Quién la destraba y cuándo?

**Regla clave (Ballard, Last Planner System):** una tarea con una restricción abierta
no entra a los compromisos de la semana salvo que el equipo decida explícitamente tomarla
como riesgo. En ese caso, queda anotada como "compromiso con riesgo: [restricción abierta]".

Explicalo así si te preguntan: "Si algo te frena, no lo prometemos para esta semana — lo
dejamos en el lookahead y trabajamos para desbloquear primero. Si igual lo necesitamos esta
semana, lo anotamos como riesgo y lo vemos."

---

## Paso 3 — Compromisos de la semana

Cada persona del equipo dice:

> "Esta semana me comprometo a [qué] en [proyecto], listo para el [día]."

Registrá cada compromiso con: **quién · qué · proyecto · fecha de cierre**.

Antes de aceptar un compromiso:
1. ¿Tiene alguna restricción abierta de las identificadas en el Paso 2?
2. Si sí → recordar la regla: se puede comprometer igual si el equipo lo decide, pero queda
   anotado como riesgo.

---

## Paso 4 — Producir el documento

Generá el plan semanal en Markdown siguiendo `assets/plantilla-plan-semanal.md`.
Incluye:
- Fecha de la reunión
- Resumen de la semana anterior (qué se cumplió, causas de lo que no)
- Plan de la semana (compromisos por persona)
- Lookahead a 4-6 semanas por proyecto (hitos + restricciones + quién las destrava)

Antes de mostrar el resultado, decí: "Acá está el plan de la semana — revisalo y decime si
cambiás algo antes de que lo peguemos en Drive/ClickUp."

---

*Documento de trabajo interno del estudio: no reemplaza el criterio del profesional responsable ni el asesoramiento legal.*

## Qué NO hace esta skill

- **No evalúa personas.** Las causas de incumplimiento son para mejorar el sistema, no para
  juzgar a nadie. Si el tono de la reunión se vuelve "¿por qué no cumpliste?", esta skill
  no puede sostener eso — eso depende de quien lidera la reunión.
- **No reemplaza la reunión.** El valor está en la conversación del equipo, no en el
  documento. La skill estructura y registra; el estudio conversa.
- **No calcula el porcentaje de cumplimiento.** La columna "Se cumplió" y las causas registradas alcanzan para llevarlo en una planilla.
- **No arma el plan del proyecto hacia atrás desde la entrega.** Eso se hace aparte.

---

*Nota al pie — para quienes quieran la referencia técnica:*
*Esta skill implementa las 5 conversaciones del Last Planner System® (LCI): Should → Can →*
*Will → Did → Learn. La "regla de restricciones" es el principio de "shielding production"*
*(Ballard 1998). PPC (Percent Plan Complete) se lleva manualmente desde la columna "Se cumplió".*
