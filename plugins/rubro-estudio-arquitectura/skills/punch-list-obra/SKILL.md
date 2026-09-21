---
name: punch-list-obra
description: >
  Convertí notas de recorrida, fotos o transcripciones de audio en una lista de pendientes de obra
  numerada, con ubicación, gremio responsable y referencia al pliego. Usala cuando te pidan armar un
  punch list, organizar las observaciones de la recorrida final, preparar la lista de terminaciones para
  recepción provisoria o definitiva, o distribuir pendientes a los contratistas. Disparadores:
  "punch list", "pendientes de obra", "recorrida", "lista de terminaciones", "recepción provisoria",
  "observaciones de la inspección", "cierre de obra".
version: "0.1.0"
origen: "adaptada de mohitagw15856/pm-claude-skills → pm-construction/punch-list-builder (MIT), 2026-09-21"
sync: si
user-invocable: true
---

# Skill: Punch list / Lista de pendientes de obra

"Arreglar pintura en pasillo" no cierra nada. Un ítem que cierra dice: *Planta baja, local 02, muro norte —
terminación de cielorraso no cumple pliego ET-05 (relleno y pintura); responsable: [empresa de revoques];
verificación: reaplicar masilla, lijar y pintar toda la sección; re-inspección bajo luz rasante.*
Esta skill convierte las notas desordenadas de la recorrida en eso: una lista numerada, asignada por gremio,
con referencia al pliego, que el director de obra puede firmar y los contratistas pueden ejecutar.

## Qué produce

- Una **lista de pendientes numerada**, agrupada por sector (nivel → local/ambiente)
- Por ítem: **ubicación, gremio, empresa responsable, referencia a pliego/plano, nivel de prioridad, criterio de aceptación**
- Flag de **posible débito técnico** en daños causados por otros gremios o retrabajos
- **Resumen por gremio** para distribuir listas acotadas a cada contratista
- **Vinculación con recepción**: ítems que bloquean la recepción provisoria, los que bloquean la definitiva, y los que pasan a garantía

## Inputs que necesitás

Pedí lo que falte; con notas crudas solas, armá la lista y etiquetá los campos inferidos con `[verificar]`:

- **Notas de la recorrida** — como vengan: viñetas, transcripción, epígrafes de fotos
- **Esquema de ubicaciones** — numeración de locales o sectores del proyecto (para que los ítems sean ubicables)
- **Lista de contratistas por gremio** — si no está, asignás por gremio y marcás empresa `[asignar]`
- **Secciones del pliego de especificaciones técnicas** disponibles para referenciar (mejora mucho la solidez)
- **Etapa del proyecto** — recorrida previa a recepción provisoria, recepción definitiva, o inspección de garantía; cambia la vara de exigencia

## Marco legal argentino

**Recepción provisoria y definitiva:**
El CCyC (arts. 1270-1273 — **verificar numeración vigente**) establece que el comitente puede
observar la obra al recibirla. La recepción provisoria con lista de observaciones no implica
conformidad con los defectos registrados; la definitiva libera al contratista de los que no estén
documentados. **Documentar todo en el acta de recepción y en el libro de obra.**

**Plazos de garantía:**
La responsabilidad por vicios aparentes prescribe al año desde la recepción; la de vicios ocultos
y ruina puede extenderse hasta 10 años según el CCyC (art. 1273 — **verificar con abogado**).
Clasificar los ítems según si son aparentes (detectables en la recorrida) u ocultos
(detectados después) importa para los plazos.

**Débito técnico entre contratistas:**
Cuando un gremio daña trabajo ya terminado de otro, el director de obra debe documentar la situación
en el libro de obra y notificar al causante. Sin evidencia escrita (foto + asiento), no hay débito.

## Niveles de prioridad

| Nivel | Definición | Consecuencia |
|---|---|---|
| **A — Bloquea recepción** | Seguridad, incumplimiento de normas (CIRSOC, IRAM, municipio), sistemas no funcionales, inspecciones faltantes | Bloquea la recepción provisoria / habilitación |
| **B — Bloquea aceptación** | No cumple contrato o pliego: producto incorrecto, terminación fuera de tolerancia, alcance incompleto | Bloquea la retención o el pago final de ese gremio |
| **C — Cosmético** | Retoques, ajustes, limpieza dentro de tolerancia del pliego | Seguimiento hasta cerrar, pero no retiene el avance de obra |

Los ítems nivel A van al tope del resumen — no los enterrés en la lista de un local.

**Un responsable por ítem.** "El contratista general coordina" no es un responsable. Cuando hay
superposición de gremios (¿quién rayó el marco — el pintor o el que instaló la carpintería?),
asignás al más probable y señalás la disputa.

**Flag de débito técnico.** Marcá como candidatos a débito: daños en trabajo terminado de otro gremio,
retrabajos de observaciones ya notificadas, ítems que un contratista ya fue instruido a corregir.
Anotá la evidencia disponible (foto, asiento en libro de obra, fecha de notificación previa).

## Formato de salida

### Lista de pendientes: [Obra] — [Fecha de recorrida, etapa, presentes]

**1. Resumen** — total de ítems por nivel y por gremio; lista completa de ítems nivel A.

**2. Ítems por sector** — tabla por área:

| # | Ubicación | Descripción del defecto | Ref. pliego/plano | Gremio | Empresa | Nivel | Débito técnico | Criterio de aceptación | Estado |
|---|---|---|---|---|---|---|---|---|---|

**3. Resúmenes por gremio** — extracto por empresa con n.º de ítem y campo de fecha límite.

**4. Candidatos a débito técnico** — n.º de ítem, fundamento, evidencia disponible / necesaria.

**5. Vinculación con recepción** — ítems que bloquean recepción provisoria; ítems que bloquean definitiva por gremio; ítems que pasan a período de garantía.

> **Regla de la casa:** mostrá esta lista y pedí confirmación antes de distribuirla a los contratistas.

*Documento de trabajo interno del estudio: no reemplaza el criterio del profesional responsable ni el asesoramiento legal.*

## Qué NO hace esta skill

- No hace seguimiento de ítems cerrados en el tiempo — necesitás un sheet o una app para eso.
- No genera el acta de recepción definitiva — eso es un documento separado que firma el comitente.
- No evalúa si los defectos dan lugar a resarcimiento económico — eso requiere criterio profesional y, en conflictos, abogado.
- No verifica si los plazos de garantía ya vencieron.

## Checklist de calidad

- [ ] Cada ítem tiene una ubicación inequívoca con la numeración del proyecto — nada de "el pasillo de la entrada"
- [ ] Un defecto por ítem — las notas compuestas están divididas para que cada una pueda cerrarse por separado
- [ ] Un responsable por ítem (o disputa explícita), nunca "varios" o vacío
- [ ] Referencia al pliego o plano donde existe; `[verificar]` donde se infirió
- [ ] Criterio de aceptación presente en cada ítem — qué aspecto tiene "terminado" en la re-inspección
- [ ] Los ítems nivel A aparecen en el resumen, no solo en la lista por local

## Anti-patrones

- No escribas ítems subjetivos ("quedó feo") — describí contra una tolerancia del pliego, un detalle del plano o el muestra aprobado
- No juntés cinco defectos en una línea — un ítem compuesto nunca cierra del todo
- No asignés ítems al "contratista general" como comodín — la lista llega al gremio que debe el trabajo
- No metás ítems nuevos encontrados después de la recorrida en la lista original sin fecha — van en un suplemento fechado
- No acuses débito técnico sin nombrar la evidencia — un cargo sin respaldo envenena la relación con el contratista
