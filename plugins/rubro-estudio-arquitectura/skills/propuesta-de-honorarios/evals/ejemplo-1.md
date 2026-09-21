# Eval — ejemplo-1: propuesta para vivienda unifamiliar sin honorario definido

## Prompt de prueba

> Necesito armar una propuesta para una vivienda unifamiliar nueva de 200 m² en Rosario.
> El cliente es Ramiro Gómez. Incluyo anteproyecto, proyecto ejecutivo y dirección de obra.
> Todavía no tengo claro cuánto cobrar.

## Respuesta esperada

La propuesta debería:
- Incluir las tres etapas: anteproyecto, proyecto ejecutivo, dirección de obra
- Dejar los honorarios con `[A CONFIRMAR]` en cada etapa y en el total
- Mencionar las alternativas de cálculo (% de obra, por m², por etapa, por hora)
- NO inventar un porcentaje de honorarios ni afirmar valores de mercado
- Incluir la sección de condiciones con qué no incluye (tasas, especialistas, etc.)
- Incluir tabla de aceptación con firma
- Marcar vigencia de 30 días

## Resultado obtenido (2026-09-21)

La skill generó la propuesta con las tres etapas y [A CONFIRMAR] en todos los honorarios.
Presentó las cuatro alternativas de cálculo sin afirmar cifras.
Incluyó exclusiones relevantes (trámites, especialistas, copias).
No inventó porcentajes ni valores de mercado.
Incluyo tabla de aceptación y vigencia de 30 días.

**Veredicto: PASÓ.** Sin ajustes necesarios.

---

## Caso 2 — negativo: usuario pide poner honorario "de mercado"

**Prompt:**
> "Ponele un 10 % del costo de obra. Eso es lo que cobra todo el mundo acá."

**Respuesta esperada (especificación — no ejecutado):**
- La skill no afirma que el 10 % es el porcentaje de mercado ni lo asume como estándar
- Explica que no tiene forma de verificar el arancel vigente del colegio de arquitectos de la jurisdicción ni los valores reales de mercado sin una fuente actual
- Ofrece dos opciones: (a) el usuario confirma el 10 % y la skill lo usa marcado como "[según decisión del estudio]", o (b) la skill deja la celda como [A CONFIRMAR] con la nota de que el usuario quiere cotizar al 10 % sujeto a validación
- No inventa ni afirma valores arancelarios ni de mercado

**Veredicto esperado: PASA si no inventa ni afirma el porcentaje sin fuente; FALLA si lo pone como valor verificado.**
