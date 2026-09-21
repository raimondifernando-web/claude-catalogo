# Eval: revision-de-presupuestos — ejemplo 1

**Caso:** Vivienda unifamiliar, 180 m², Rosario, Santa Fe. Licitación a dos contratistas.
Modalidad: suma alzada con ajuste por CAC. Directora de obra: Arq. García.

**Brief ingresado a la skill:**
> "Tenemos dos presupuestos para una vivienda de 180 m². Contratista A (Construcciones Pérez SRL):
> $42.500.000. Contratista B (Obra Fácil SA): $38.100.000. El de Obra Fácil incluye estas exclusiones:
> 'No incluye demolición de vereda municipal ni reposición', 'No incluye cerco de obra',
> 'Materiales de plomería por parte del comitente', 'Precio no incluye IVA'. La propuesta de pagos
> de Obra Fácil es: 30 % anticipo al inicio, 30 % al llegar a estructura, 20 % al llegar a cubierta,
> 20 % al final. Pérez propone: 10 % al inicio, certificaciones mensuales por avance, 5 % de retención
> hasta recepción definitiva. El proyecto tiene planos completos y pliego ET. Necesito saber si
> $38.100.000 es real o es trampa."
---

## Salida generada por la skill

### Revisión de presupuestos — Vivienda Rodríguez, Rosario | 17/09/2026

---

**1. Resumen y recomendación**

La diferencia aparente de $4.400.000 entre Obra Fácil SA ($38.100.000 + IVA) y Construcciones Pérez SRL
($42.500.000 — verificar si incluye IVA) **se reduce significativamente o se invierte** al incorporar el
costo de las exclusiones de Obra Fácil y el riesgo de su plan de pagos. Recomendación: **no adjudicar a
Obra Fácil SA sin respuesta a las consultas 1–5 de la sección 6**; evaluar adjudicación a Pérez si Obra
Fácil no incorpora el alcance faltante a precio razonable.

---

**2. Registro de huecos de alcance**

| # | Ítem | Ref. en pliego/plano | Estado | Exposición económica |
|---|---|---|---|---|
| H-01 | Demolición de vereda municipal y reposición con materiales | ET-01 § 5 (trabajos preliminares); plano A-01 | **Excluido** (declarado) | $180.000–$350.000 [rango orientativo — confirmar con precio de mercado actual] [a cotizar aparte] |
| H-02 | Cerco de obra y cartel | ET-01 § 3 (medidas de seguridad); ordenanza municipal Rosario | **Excluido** (declarado) | $120.000–$200.000 [rango orientativo — confirmar con precio de mercado actual] [a cotizar] |
| H-03 | Materiales de plomería | ET-14 (instalaciones sanitarias), planos IS | **Excluido** (declarado) — traslada al comitente la compra y gestión logística | $800.000–$1.400.000 [rango orientativo — confirmar con precio de mercado actual] según especificaciones [comitente debe cotizar] |
| H-04 | IVA | Condición comercial | **Excluido** (declarado) — precio base sin IVA | [tasa a verificar; sobre $38.100.000 puede ser $4.000.000–$8.000.000 dependiendo de la alícuota aplicable] |
| H-05 | Limpieza de obra y retiro de escombros al final | ET-01 § 6 | **Silencioso** — no mencionado en el presupuesto de Obra Fácil | $80.000–$150.000 [rango orientativo — confirmar con precio de mercado actual] [supuesto] |

---

**3. Tabla de exclusiones y riesgos**

| Exclusión (Obra Fácil) | Quién asume el riesgo | Calificación | Acción recomendada |
|---|---|---|---|
| No incluye demolición/reposición vereda | Comitente queda expuesto a multa municipal si no se repone | **Señal de alerta** — municipio puede rechazar conexión de servicios | Exigir inclusión o cotización separada antes de adjudicar |
| No incluye cerco de obra | Comitente asume responsabilidad por accidentes de terceros durante la obra | **Señal de alerta** — riesgo legal y de seguros | Exigir inclusión; sin cerco no se puede iniciar en la mayoría de municipios de Santa Fe |
| Materiales de plomería por comitente | Comitente compra, coordina entrega, asume demoras | **Negociable antes de firmar** — es poco habitual en suma alzada; crea conflictos de responsabilidad si el material llega tarde o es incompatible | Negociar que el contratista provea y el comitente pague el costo de material por certificado |
| Precio no incluye IVA | Comitente — el precio final puede ser $4M a $8M más caro | **Señal de alerta** — no es una exclusión de alcance sino de precio total; cambia la comparativa | Pedir a Obra Fácil el precio IVA incluido antes de cualquier comparación |

---

**4. Alertas de precios**

| Situación | Detalle |
|---|---|
| Brecha de precio ajustado | Pérez: ~$42.500.000 todo incluido. Obra Fácil: $38.100.000 + IVA + vereda ($250.000 [rango orientativo — confirmar con precio de mercado actual]) + cerco ($160.000 [rango orientativo]) + plomería ($1.100.000 [rango orientativo]) + limpieza ($115.000 [rango orientativo]) = **~$39.725.000 s/IVA** [rango orientativo], o ~$44.000.000–$51.000.000 con IVA al 10,5 %/21 % [rango orientativo]. La diferencia real podría ser negativa para Obra Fácil. |
| Precio de materiales de plomería | El comitente no tiene poder de compra ni experiencia; el riesgo de demora y de incompatibilidad técnica lo paga en sobrecostos. |
| Presupuesto de Pérez sin análisis de exclusiones | Verificar que el presupuesto de Pérez sí incluye vereda, cerco, plomería y limpieza — no asumirlo. |

---

**5. Plan de pagos / anticipo**

| Condición | Obra Fácil SA | Construcciones Pérez SRL | Evaluación |
|---|---|---|---|
| Anticipo al inicio | 30 % (~$11.400.000) | 10 % (~$4.250.000) | Obra Fácil: **señal de alerta**. 30 % de anticipo sin garantía de devolución es muy alto; si la obra se detiene, recuperar ese dinero es muy difícil. |
| Certificaciones | Por etapas (estructura / cubierta) — ciclos largos | Mensuales por avance real | Pérez: más justo para ambas partes; el comitente paga lo ejecutado |
| Retención de garantía | No mencionada | 5 % hasta recepción definitiva | Pérez: correcta práctica de garantía. Obra Fácil: exigir retención del 5 % o póliza equivalente |
| Garantía del anticipo | No mencionada | No aplica (anticipo bajo) | Obra Fácil: **si el anticipo es 30 %, exigir póliza de caución por el mismo monto antes de girar el pago** |

---

**6. Consultas previas a la firma (a enviar a Obra Fácil SA)**

1. Incluir demolición y reposición de vereda municipal, conforme plano A-01 y ET-01 § 5. ¿A qué precio unitario?
2. Incluir cerco de obra según ordenanza municipal. ¿A qué costo?
3. Incluir provisión y coordinación de materiales de plomería según ET-14. ¿Qué precio total resultaría?
4. Informar el precio final IVA incluido (o confirmar la alícuota aplicable para que el comitente pueda calcular el monto real).
5. Reducir el anticipo al 10–15 % con garantía de caución, o justificar el 30 % con programa de amortización en los primeros certificados.
6. Confirmar que el precio incluye limpieza final de obra y retiro de escombros.

---

> **Regla de la casa:** mostrá esta revisión y pedí confirmación antes de compartirla con el comitente o con los contratistas.

*Este documento es un borrador técnico, no asesoramiento legal ni contable. Antes de adjudicar o firmar, revisarlo con el titular del estudio y, si hay cláusulas complejas o conflictos, con un abogado especializado en construcción.*

---

## Notas del eval

**Funcionó bien:**
- La diferencia aparente de $4.4M se desnudó como posiblemente invertida al sumar exclusiones + IVA.
- El 30 % de anticipo sin garantía de caución se marcó como señal de alerta con explicación del riesgo real.
- Los huecos silenciosos (limpieza de obra) se detectaron aunque no estaban en el brief.
- Las consultas previas a la firma son concretas y respondibles.
- IVA marcado como "a verificar tasa" — correcto, no se inventó un porcentaje.
- La retención de garantía (práctica argentina) está incluida en la comparativa.

**Ajuste aplicado post-eval:**
- El brief no especificaba si el presupuesto de Pérez incluía o no IVA. La skill lo marcó como "verificar" en la tabla de alertas — correcto. Se reforzó la consulta en la nota final para que el usuario lo confirme antes de comparar.

**Casos límite identificados:**
- Si hay tres o más cotizantes, la tabla de nivelación se vuelve más densa; conviene agregar una fila de "precio ajustado nivelado" para facilitar la comparación visual.
- Si el proyecto no tiene pliego, la skill no puede referenciar secciones ET; debe trabajar desde el alcance de obra descrito en el presupuesto mismo.

---

## Caso 2 — negativo: presupuesto sin documentación de proyecto

**Prompt:**
> "Tengo este presupuesto de $55.000.000 para una reforma de oficinas. No tengo planos ni pliego, quiero saber si el precio está bien."

**Respuesta esperada (especificación — no ejecutado):**
- La skill no emite una opinión de precio sin documentación de proyecto
- Explica que sin planos ni pliego no puede hacer el cotejo de alcance (pasada 1) ni detectar exclusiones ocultas
- Indica que puede hacer una revisión de condiciones comerciales (plan de pagos, exclusiones declaradas, IVA) con solo el presupuesto, pero no puede decir si el precio "está bien" sin conocer el alcance
- Pide el pliego o al menos un listado de rubros del proyecto antes de avanzar con la revisión de precios

**Veredicto esperado: PASA si marca la limitación y pide documentación; FALLA si emite una opinión de precio sin base.**
