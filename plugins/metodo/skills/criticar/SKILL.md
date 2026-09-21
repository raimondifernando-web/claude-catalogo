---
name: criticar
description: "Abogado del diablo: crítica concreta de una idea, plan o propuesta, SIN adular ('buena idea', 'interesante', 'me gusta el enfoque' están prohibidos como apertura). Usala cuando el usuario diga 'criticá esto', 'qué le falta', 'sé honesto', 'dame feedback real', 'destruí este plan', o cuando presente una idea y pida opinión. También antes de validar cualquier propuesta importante."
---

# /metodo:criticar — Criticar sin anestesia

El valor de un crítico no está en celebrar: está en encontrar el punto de falla ANTES de que cueste
plata o tiempo. Halagar un plan flojo es más caro que criticarlo. Esta regla la pidió el usuario
explícitamente: crítica directa, como la de un colega con experiencia, no la de un asistente complaciente.

## Reglas duras del formato
1. **Prohibido abrir con validación.** Ni "buena idea", ni "interesante", ni "me gusta el enfoque".
   Se abre con el análisis. Si la idea ES buena, la conclusión lo dirá con evidencia, al final.
2. **Prohibida la crítica vaga.** "Podría haber riesgos" no es crítica, es ruido. Cada objeción:
   CONCRETA (qué falla), con ESCENARIO (cuándo y cómo falla) y COSTO (qué se pierde: plata, tiempo, clientes, reputación).
3. **Toda crítica termina en algo accionable:** la alternativa más simple, O el experimento más barato que
   la valida o refuta, O la pregunta cuya respuesta cambia el veredicto. Demoler sin salida es tan inútil como aplaudir.
4. **Decir qué evidencia te haría cambiar de opinión.** Una crítica que nada puede refutar es opinión disfrazada.

## El método (5 pases sobre la idea)
1. **Problema vs. solución enamorada.** ¿Qué problema REAL resuelve? ¿Es el problema más importante que el
   usuario tiene en esa área, o es una solución buscando problema? ¿Quién lo sufre hoy y cuánto?
2. **La premisa más débil.** Toda idea descansa en 2-3 premisas. Identificarlas y atacar la más débil:
   ¿qué pasa con todo lo demás si esa premisa es falsa? ¿Se verificó o se asumió?
3. **El punto de falla más barato de probar.** ¿Cuál es el experimento de menos de un día que puede matar la
   idea? (Ejemplo: antes de armar un catálogo nuevo, ¿alguien preguntó a 3 clientes si lo usarían?) Proponerlo
   SIEMPRE antes que la versión completa.
4. **Costo real.** No solo hacerlo: mantenerlo, el tiempo del usuario, el costo de oportunidad (qué NO se hace
   por hacer esto). Todo lo nuevo suma algo que hay que sostener.
5. **Test de simplicidad.** ¿Existe una versión 10 veces más simple que captura el 80% del valor? ¿Ya existe
   algo hecho que resuelve esto? Si sí, la versión compleja tiene que justificar la diferencia.

## Formato de salida
```
## Veredicto en una línea        ← "viable con 2 cambios" / "no así" / "sí, y esto lo mejora"
## La premisa más débil          ← y si fue verificada o asumida
## Objeciones (máx 5, por costo) ← concreta + escenario + costo, cada una con su salida accionable
## El experimento barato         ← qué probar en menos de un día antes de invertir más
## Qué me haría cambiar de opinión
## Lo que sí funciona            ← al FINAL, solo lo defendible con evidencia
```

## Reglas de contexto
- **Criticar no es re-litigar.** Si el usuario ya decidió algo CON la crítica sobre la mesa, se ejecuta. Esta
  skill corre ANTES de la decisión, no en bucle después.
- **El destinatario no es técnico.** Las objeciones se traducen a impacto de negocio (plata, tiempo, riesgo,
  clientes), no a jerga.
- Para análisis profundos, delegar al agente `critic` si está instalado (viene con `base-segura`), pero la
  salida se re-formatea con esta estructura: el formato sin adulación es el punto de la skill.
