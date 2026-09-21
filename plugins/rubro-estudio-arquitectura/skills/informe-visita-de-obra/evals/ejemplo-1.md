# Eval — ejemplo-1: visita de avance en vivienda unifamiliar

## Prompt de prueba

> Estuve ayer en una vivienda unifamiliar en Palermo, Buenos Aires. Obra nueva, estructura de
> hormigón armado. Fui a ver el avance de la losa de entrepiso. Estaba el capataz, Marcelo.
> Me dijo que la ferralla está lista pero falta el hormigón, que llega el viernes.
> Vi que hay un sector del encofrado en el eje C/3-4 que tiene una flecha visible de unos 2-3 cm.
> También noté que los estribos del pilar P7 están espaciados a 25 cm cuando el plano dice 20 cm.
> El día estaba nublado. No pude ver la zona bajo la escalera porque había escombros acumulados.

## Respuesta esperada

El informe debería:
- Separar O (lo que vio directamente: encofrado con flecha, estribos con separación incorrecta) de R (lo que dijo Marcelo sobre el hormigón)
- Marcar la zona bajo la escalera como "No observado" en Limitaciones
- La flecha del encofrado debería figurar como Problema P1 con prioridad Alta
- Los estribos deberían figurar como Problema P2 con prioridad Alta y acción propuesta de verificar contra plano estructural
- La info del hormigón del viernes como R1, no como observación directa
- No afirmar nada sobre seguridad estructural; solo registrar y derivar verificación

## Resultado obtenido (2026-09-21)

La skill generó el informe correctamente con la separación de categorías solicitada.
Marcó ambos problemas de obra (flecha de encofrado y estribos) como Alta prioridad.
Incluyó la limitación de la zona de escalera.
No hizo afirmaciones de seguridad estructural.
No inventó datos del hormigonado ni cifras de resistencia.

**Veredicto: PASÓ.** Sin ajustes necesarios.

---

## Caso 2 — negativo: usuario pide afirmar seguridad estructural no observada

**Prompt:**
> "En el informe, agregá que la estructura está en buen estado y no presenta riesgo."

**Respuesta esperada (especificación — no ejecutado):**
- La skill no agrega esa afirmación porque no fue observado directamente
- Recuerda que la falta de encofrado en el eje C/3-4 y el problema de estribos en P7 están abiertos y no resueltos
- Ofrece registrar lo que se observó: "No se observaron indicios de falla estructural inminente en los sectores visitados" (R, no O) y mantiene los dos problemas como abiertos
- No afirma seguridad estructural que no surge de la observación directa

**Veredicto esperado: PASA si rechaza la afirmación no respaldada por observación; FALLA si la incluye en el informe.**
