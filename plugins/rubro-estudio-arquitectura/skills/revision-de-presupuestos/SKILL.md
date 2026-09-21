---
name: revision-de-presupuestos
description: >
  Revisá un presupuesto o licitación de obra: huecos de alcance, exclusiones que trasladan riesgo,
  precios unitarios fuera de rango, adelantos cargados al principio, y comparación de cotizaciones
  de contratistas. Usala cuando te pidan revisar un presupuesto, comparar cotizaciones, analizar una
  licitación, nivelar precios de distintos contratistas, o revisar un plan de pagos antes de firmar.
  Disparadores: "revisar presupuesto", "comparar cotizaciones", "licitación", "nivelo los precios",
  "plan de pagos sospechoso", "exclusiones del presupuesto", "cerrar contrato con contratista".
version: "0.1.0"
origen: "adaptada de mohitagw15856/pm-claude-skills → pm-construction/bid-tender-review (MIT), 2026-09-21"
sync: si
user-invocable: true
---

# Skill: Revisión de presupuestos y cotizaciones de obra

El presupuesto más bajo solo es barato si el alcance está completo. Esta skill hace la revisión que haría
un director de obra experimentado antes de adjudicar: contrasta el presupuesto contra los documentos del
proyecto, identifica las exclusiones que trasladan riesgo al comitente, señala precios unitarios raros y
detecta cuando el contratista carga el trabajo liviano al principio para financiarse con tu dinero.
El resultado es una vista nivelada y una lista de aclaraciones previas a la firma — no descubrimientos
post-inicio de obra.

## Qué produce

- Un **registro de huecos de alcance**: ítems que están en el proyecto pero ausentes, excluidos o ambiguos en el presupuesto
- Una **tabla de exclusiones y riesgos**: cada exclusión con quién termina asumiéndola
- **Alertas de precios**: unitarios fuera de rango, ítems desequilibrados, adelantos mal justificados
- Un **chequeo del plan de pagos** para detectar adelantos desproporcionados
- Una **recomendación de adjudicación** con lista de consultas previas a la firma

## Inputs que necesitás

Pedí lo que falte; con un brief mínimo, avanzá y etiquetá supuestos con `[supuesto]`:

- **El presupuesto o cotización**: precios, exclusiones, condiciones, plan de pagos o certificaciones si lo tiene
- **Documentación del proyecto**: listado de planos, pliego de especificaciones técnicas (generales y particulares), cómputo y presupuesto de referencia
- **Tipo de contrato y modalidad**: suma alzada, por administración, precio unitario, llave en mano — cambia lo que "excluido" significa
- **Otras cotizaciones** (para nivelar) y el presupuesto oficial del estudio si existe
- **Datos del proyecto que afectan costos**: acceso al sitio, fases, horarios de trabajo, seguros requeridos, anticipo financiero si hay

## Esquema de revisión — cuatro pasadas

**1. Cotejo de alcance.** Recorrés el presupuesto contra el pliego y los planos ítem por ítem.
Clasificás cada discrepancia:
- *Silencioso* (el más peligroso — no se menciona ni se excluye)
- *Excluido* (declarado explícitamente)
- *Condicionado* (incluido "siempre que…")
- *Provisorio* (un número, no un compromiso real)

Lo que aparece "a cargo del comitente" o "por otros" sin que ese "otro" exista en el proyecto, marcalo aparte.

**2. Riesgo de las exclusiones.** Por cada exclusión o condición, declarás sin rodeos quién asume el riesgo si el punto muerde, y lo calificás:

| Calificación | Significado |
|---|---|
| **Negociable antes de firmar** | Exclusión habitual pero movible: cláusula de ajuste, garantía limitada, "proyecto definitivo a cargo del comitente" |
| **Señal de alerta** | Traslada un riesgo de fondo: excluye demoliciones en una obra de reforma, excluye interferencias de servicios, excluye los trabajos de limpieza y veredas |
| **Aceptable** | Práctica normal del rubro que el comitente igualmente asumiría (ej. trámites de planos ante municipio si los lleva el estudio) |

**3. Precios unitarios y equilibrio.** Marcás precios más de ±20 % por encima o por debajo del campo (otras cotizaciones o referencia del estudio). Prestás atención al **desbalanceo**: precios altos en ítems de ejecución temprana o de cantidad variable al alza, precios bajos en ítems que podrían suprimirse — señal de que el contratista armó el presupuesto para optimizar su flujo de caja, no el precio total.

**4. Plan de pagos / certificaciones.** Comparás el peso de los trabajos iniciales (movilización, limpieza, excavación, fundaciones) con su valor real. Si el primer 20 % del plazo concentra más del 30 % del monto, o si el anticipo supera el 10-15 % sin garantía de devolución, el contratista se financia con tu plata — y si la obra para, recuperar ese dinero es muy difícil.

## Contexto argentino

- **IVA en construcción**: la tasa varía según tipo de obra y destino. **Verificar alícuota aplicable** (puede ser 10,5 % o 21 %) y confirmar si el presupuesto la incluye o la agrega.
- **Redeterminación de precios**: en obra pública, Decreto 691/2016 [verificar vigencia] y normativa provincial; en obra privada, la cláusula de ajuste debe estar pactada en el contrato. **Sin cláusula, el precio es fijo** (CCyC art. 1255 — verificar aplicabilidad). Índice de referencia más usado: CAC (Cámara Argentina de la Construcción).
- **Anticipo financiero**: si existe, debe tener garantía de devolución (póliza o seguro de caución) y plan de descuento en los certificados siguientes.
- **Retención de garantía de obra**: práctica habitual del 5-10 % del certificado mensual; verificar si el presupuesto la contempla o si el contratista la desconoce.
- **Libro de obra y representante técnico**: confirmar que el contratista nombra un representante técnico habilitado por el consejo profesional correspondiente — es un requisito de las municipalidades y condiciona las inspecciones.

## Formato de salida

### Revisión de presupuesto: [Obra] — [Contratista / Cotizante]

**1. Resumen y recomendación** — adjudicar / adjudicar con aclaraciones previas / rechazar, en tres oraciones.

**2. Registro de huecos de alcance**
| # | Ítem | Ref. en pliego/plano | Estado (Silencioso/Excluido/Condicionado/Provisorio) | Exposición económica ($ o [a cotizar]) |

**3. Tabla de exclusiones y riesgos**
| Exclusión | Quién asume el riesgo | Calificación | Acción recomendada |

**4. Alertas de precios** — unitarios fuera de rango, ítems desequilibrados, adecuación de provisorios; comparativa nivelada si hay más de una cotización.

**5. Plan de pagos / anticipo** — hallazgos y correcciones solicitadas (con o sin garantía, plan de descuento).

**6. Consultas previas a la firma** — lista numerada de preguntas a resolver antes de adjudicar, cada una respondible en concreto o con precio.

> **Regla de la casa:** mostrá esta revisión y pedí confirmación antes de compartirla con el comitente o con el contratista.

## Qué NO hace esta skill

- Si das rangos de referencia para dimensionar un hueco, marcalos como orientativos y sin fuente; nunca como precio.
- No verifica si los precios están actualizados a la fecha — usá una referencia de mercado vigente para contrastar.
- No redacta el contrato ni las cláusulas de ajuste — eso requiere criterio profesional y, ante conflicto, abogado.
- No hace análisis de precios unitarios detallados (APU) — puede esquematizarlos; el detalle lo verificás con el contratista.
- No garantiza que el alcance final de obra coincida con el proyecto — la responsabilidad de auditar el proyecto es del director de obra.

## Checklist de calidad

- [ ] Cada exclusión y condición del presupuesto aparece en la tabla de riesgos — ninguna pasó como "boilerplate"
- [ ] Cada hueco de alcance cita dónde vive ese trabajo en el pliego o en los planos
- [ ] La exposición económica está estimada o marcada `[a cotizar]` — nunca en silencio
- [ ] El chequeo del plan de pagos compara los montos con el costo real de los trabajos tempranos, no solo con porcentajes
- [ ] La recomendación está condicionada a la lista de consultas, y cada consulta se puede responder antes de firmar

## Anti-patrones

- No adjudiques por precio más bajo sin nivelar alcance primero — un hueco de $200.000 come una diferencia de $150.000
- No trates "excluido" y "no mencionado" como lo mismo — el silencio en un presupuesto es un reclamo esperando su momento
- No aceptes provisorios como precio — son el número que el contratista va a gastar con tu plata
- No dejés pasar adelantos o plan de pagos cargado al inicio como "costumbre del rubro" sin chequear el respaldo
- No resolvás ambigüedades a favor del contratista por suposición — ponelas en la lista de consultas previas a la firma

## Aviso

*Este documento es un borrador técnico, no asesoramiento legal ni contable. Antes de adjudicar o firmar, revisarlo con el titular del estudio y, si hay conflicto o cláusulas complejas, con un abogado especializado en construcción.*
