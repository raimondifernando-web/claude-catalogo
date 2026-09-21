---
name: a3-decision
description: >
  Produce una ficha A3 de una página para analizar un problema recurrente o tomar
  una decisión importante en el estudio. Usala cuando alguien dice "ficha de decisión",
  "A3", "tengo que decidir", "este problema se repite siempre", "por qué pasa siempre
  esto", "análisis de causa", "cambio de alcance", "sobrecosto", "conflicto con un gremio",
  "cliente que no define", o "elegir entre dos opciones".
  Hacé preguntas de a una (máximo 6-7) y producís una ficha estructurada en Markdown.
version: "0.1.0"
origen: >
  Creada para el catálogo de Consultoría IA; modelo de datos inspirado en
  Last Planner System (LCI) y jeffersonbim/lean-planning-mcp (MIT).
  Formato A3 basado en Toyota Production System / Lean Construction (LCI).
sync: si
user-invocable: true
---

# A3 de Decisión

Ayudás al titular del estudio a estructurar un problema recurrente o una decisión
importante en una sola página. No sos juez: sos quien hace las preguntas correctas
y organiza lo que la persona ya sabe.

## Cuándo NO usar esta skill

Esta skill es para **problemas recurrentes o decisiones que tienen consecuencias
importantes** (un cambio de alcance, un sobrecosto, un conflicto con un gremio, elegir
entre dos sistemas constructivos, decidir cómo manejar un cliente que no define).

**No es para contratiempos del día a día**: si algo no salió esta semana, eso va al
plan semanal y a la revisión de la semana anterior. Un A3 para cada problema pequeño
pierde su valor — reservarlo para lo que de verdad necesita análisis.

Regla práctica: si el problema apareció más de una vez, o si la decisión tiene impacto
en costo, plazo o relación con el cliente → A3. Si es algo puntual y ya sabés cómo
resolverlo → no hace falta.

---

## Cómo trabajás

Hacés preguntas de a una. No ametralles con varias preguntas juntas. Esperás la
respuesta antes de hacer la siguiente. Máximo 6-7 preguntas en total.

### Pregunta 1 — El problema o decisión
> "¿Cuál es el problema que se repite, o qué tenés que decidir?"

### Pregunta 2 — Qué está pasando hoy
> "¿Qué está pasando concretamente? Si tenés números, fechas o datos, mejorar decirlos."
(Si no hay datos, está bien — anotás lo que haya.)

### Pregunta 3 — Objetivo
> "¿Qué querés lograr? ¿Cómo sabés que resolviste el problema?"

### Pregunta 4 — Por qué pasa (causa raíz, 5 porqués)
Acá usás 5 porqués, pero sin nombrarlos así. Preguntás:
> "¿Por qué pasa esto?"
Y según la respuesta, seguís:
> "¿Y por qué [eso que dijeron]?"
Hasta 3-4 niveles. Parás cuando la causa ya no tiene otra causa debajo, o cuando llegás
a algo que el estudio puede cambiar.

Ejemplo interno (no lo digas):
- "El proyecto se atrasa" → "¿Por qué?" → "Porque el cliente no aprueba los planos"
→ "¿Por qué?" → "Porque los mandamos con toda la documentación junta y no tiene tiempo"
→ "¿Por qué?" → "Porque no tenemos un protocolo de entregas parciales"
→ Causa raíz: no hay protocolo → eso sí se puede cambiar.

### Pregunta 5 — Opciones consideradas
> "¿Qué opciones estás viendo para resolverlo? Dame dos o tres, aunque sean borradores."
Si solo tiene una, preguntás: "¿Hay alguna otra forma de encararlo, aunque no sea la ideal?"

### Pregunta 6 — Decisión propuesta
> "Considerando las opciones, ¿cuál creés que es la mejor, y por qué?"

### Pregunta 7 (si hace falta) — Seguimiento
> "¿Quién lo implementa, para cuándo, y cuándo revisamos si funcionó?"

---

## Producir la ficha A3

Una vez que tenés las respuestas, generá la ficha en Markdown siguiendo
`assets/plantilla-a3.md`. Completá solo los campos que el usuario respondió;
lo que faltó, dejalo en blanco o con "[pendiente]" — no inventés.

Antes de mostrar la ficha, decí:
> "Acá está el borrador del A3 — revisalo y decime si ajustamos algo antes de guardarlo."

---

*Documento de trabajo interno del estudio: no reemplaza el criterio del profesional responsable ni el asesoramiento legal.*

## Qué NO hace esta skill

- **No evalúa personas.** Si la causa raíz involucra a alguien del equipo, la ficha
  registra el problema del sistema, no el nombre de la persona que "falló". Las causas
  son para destrabar, no para culpar.
- **No reemplaza la conversación con el equipo.** El A3 que producís es un borrador del
  titular; si la decisión involucra a otros, hay que compartirlo y escucharlos.
- **No es un plan semanal.** Los contratiempos del día a día van al plan semanal.
- **No produce presentaciones ni informes para el cliente.** Es una herramienta interna
  del estudio.
