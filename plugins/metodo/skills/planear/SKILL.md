---
name: planear
description: "Las 8 preguntas que hay que responder ANTES de planificar un proyecto, una mejora o un cambio. No genera el plan: garantiza que el plan responda lo que separa un plan real de una expresión de deseo. Usala cuando el usuario diga 'planeá', 'armá un plan', 'cómo encararías', 'quiero hacer X', o para auditar un plan ya escrito ('revisá este plan')."
---

# /metodo:planear — Planificar con las premisas verificadas

Un plan no es una lista de pasos: es una lista de pasos **cuyas premisas fueron verificadas**. La mayoría
de los planes malos no fallan en los pasos; fallan en lo que asumieron sin chequear.

## Las 8 preguntas (responderlas TODAS antes de escribir el plan)
1. **¿Qué existe ya?** Buscar antes de proponer crear nada: en la carpeta de trabajo, en las herramientas
   instaladas, en lo que ya se hizo antes (handoffs). La mitad de los "hay que construir X" son "X ya existe y no lo encontraste".
2. **¿Qué está VERIFICADO y qué estoy ASUMIENDO?** Dos listas explícitas. Todo lo asumido se verifica ahora
   (suele alcanzar con mirar un archivo o hacer una pregunta) o entra al plan como riesgo con plan B.
3. **¿Cuál es el paso bloqueante?** El dato, acceso o decisión sin el cual todo lo demás es teoría. Si existe,
   el plan empieza ahí y el resto queda condicionado.
4. **¿Qué es irreversible?** Borrar, renombrar, publicar, enviar, pagar, migrar datos. Cada una se marca, se
   confirma con el usuario antes, y se piensa cómo volver atrás. Si no hay vuelta atrás: doble confirmación.
5. **¿Quién lo hace?** ¿Claude solo, con qué agente, o una persona? ¿Qué depende de un tercero (proveedor, cliente, contador)?
6. **¿Qué le pregunto al usuario y qué resuelvo solo?** Al usuario SOLO decisiones de negocio (prioridad,
   presupuesto, nombre, riesgo aceptable), con opciones cerradas y recomendación. Todo lo técnico se resuelve
   o va a una lista "A VERIFICAR". Si el plan tiene más de 3 preguntas para el usuario, probablemente 2 son técnicas disfrazadas.
7. **¿Cómo se VERIFICA el resultado?** Cada entregable con su prueba observable (un archivo que existe, un
   número que cambió, una captura). "Quedó bien" no es verificación. Si no podés escribir la prueba, el entregable está mal definido.
8. **¿Qué NO se hace?** Sección explícita de exclusiones. Es lo que frena que el alcance crezca solo y las
   "mejoras oportunistas" durante la ejecución.

## Formato del plan resultante
```
# Plan — [tema]
## Contexto            ← por qué, qué lo disparó, resultado esperado
## Verificado          ← lo chequeado contra archivos/datos reales
## Supuestos y riesgos ← lo NO verificado + plan B
## Trabajo a ejecutar  ← pasos, con el bloqueante primero; quién hace cada uno
## Qué NO se hace      ← exclusiones explícitas
## Verificación        ← prueba por entregable
```

## Reglas
- **Auditar un plan ajeno** = correr las 8 preguntas contra el plan: cada una sin respuesta es un hallazgo.
  Para crítica adversarial del plan completo → `/metodo:criticar`.
- El análisis profundo se puede delegar al agente `planner` (viene con `base-segura`); esta skill es el
  checklist de criterio, no el músculo.
- Un plan que el usuario aprobó se ejecuta sin volver a discutirlo. Pero aprobar un plan no es dar permiso
  para las acciones irreversibles que contiene: esas se confirman una por una cuando llegan.
