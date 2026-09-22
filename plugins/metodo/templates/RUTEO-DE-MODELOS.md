# Ruteo de modelos — qué cerebro usa cada agente

> Guía del paquete `metodo`. La usa `/metodo:crear-agente` al elegir el modelo de un agente nuevo,
> y sirve para revisar los que ya tenés. Última revisión: 2026-09-22.

## Por qué existe este documento

Cada agente declara en su archivo con qué modelo piensa. Hoy esa elección se hace a ojo, y eso tiene dos
consecuencias que se pagan: un agente que razona en un modelo chico entrega trabajo pobre, y un agente
que hace tareas mecánicas en un modelo caro consume el límite de uso varias veces más rápido.

El criterio viejo ("modelo caro solo para temas legales o financieros") estaba mal planteado: **el tema de
la tarea no dice cuánto cerebro pide**. Un cálculo financiero trivial no necesita el modelo más capaz, y
criticar un plan de trabajo —que no es ni legal ni financiero— sí. Lo que manda es el tipo de trabajo mental.

## El criterio: tres preguntas

Ante cualquier agente o tarea, contá los "sí":

| | Pregunta | Por qué importa |
|---|---|---|
| 1 | **¿Hay que juzgar o decidir**, o solo ejecutar algo ya decidido? | Elegir entre opciones, criticar y planificar es donde un modelo más capaz cambia el resultado; ejecutar lo ya definido, no. |
| 2 | **¿Equivocarse sale caro, o el error pasa inadvertido?** | Un error en un listado se ve al instante. Un error en una propuesta a un cliente aparece tarde y ya costó. |
| 3 | **¿Hay que sostener mucho contexto o muchos pasos encadenados?** | Es donde los modelos chicos pierden el hilo a mitad de camino. |

**0 sí → Haiku · 1 sí → Sonnet · 2 sí → Opus · 3 sí y además tarea larga y autónoma → Fable, a pedido.**

Ante la duda entre dos escalones, **elegí el de abajo y medí**: subir después es un cambio de una palabra;
haber corrido seis meses en el modelo caro no se recupera.

## Qué cuesta cada uno

Precios de la API por millón de tokens (entrada/salida, ref. 2026-06):

| Modelo | Precio | Contra Sonnet |
|---|---|---|
| Fable 5.1 | $10 / $50 | 5× |
| Opus 5 | $5 / $25 | 2,5× |
| Sonnet 5 | $2 / $10 | — |
| Haiku 4.5 | $1 / $5 | 0,5× |

Con una suscripción no se paga por token: se consume cuota. La proporción es la misma — un agente en Opus
gasta tu semana 2,5 veces más rápido que en Sonnet para el mismo trabajo.

## Cómo se escribe

En el frontmatter del agente, **siempre con alias**, nunca con un ID de versión:

```yaml
---
name: mi-agente
description: ...
model: sonnet     # ✅ sigue solo al modelo vigente de esa familia
---
```

```yaml
model: claude-sonnet-4-6   # ❌ queda clavado en esa versión para siempre
```

Un ID fijo envejece: cuando sale un modelo nuevo, el agente se queda atrás y nadie va a editar cincuenta
archivos a mano para enterarse. El alias se actualiza solo.

Valores válidos: `haiku`, `sonnet`, `opus`, `fable`, `inherit` (usa el modelo de la conversación) o un ID
completo. Si se omite el campo, Claude Code elige por su propio orden de resolución.

## Fable: a pedido, no en el frontmatter

Fable es el modelo más capaz y cuesta el doble que Opus. **No se clava en ningún agente**, y el motivo es
concreto: un agente con `model: fable` corre en Fable *siempre*, también para la versión trivial de su
tarea. El mismo agente que revisa una decisión de treinta mil dólares revisa un texto de tres párrafos.

Se pide en el momento, para la ocasión que lo justifica:

```
Usá fable para esto: [la decisión grande]
```

Excepción posible: un agente cuyo único trabajo sean decisiones de ese tamaño. Si alguna vez existe, se
clava en Fable y se escribe al lado por qué.

## Cómo queda repartido

| Tier | Qué tipo de agente | Ejemplos |
|---|---|---|
| **Opus** | Juzga, planifica o decide, y el error sale caro: crítica, planificación, análisis legal y financiero, evaluación de riesgo. | `critic`, `planner`, `legal-advisor`, `risk-manager`, analistas financieros |
| **Sonnet** | El caballo de batalla: ejecutar, escribir, investigar, revisar, coordinar. Todos los PM. | la mayoría, incluido `pm-<empresa>` |
| **Haiku** | Mecánico: buscar, listar, clasificar, formatear, chequear. | `explore`, `writer`, chequeos |
| **Fable** | No se asigna. Se invoca. | — |

**Un PM va en Sonnet, no en Opus.** Coordina y delega: el razonamiento duro pasa en el especialista al que
le pasa el trabajo, no en él. Un PM en Opus consume caro en cada mensaje de ida y vuelta.

## Al delegar, el modelo se puede forzar

Un agente corre en el modelo de su frontmatter y no puede cambiarlo solo. Quien delega sí puede: al invocar
un agente se le puede pasar el modelo para esa vez. Por eso conviene rutear bajo por defecto y subir cuando
la ocasión lo pide, en lugar de al revés.

## Qué revisar cada tanto

- Que ningún agente tenga un ID de versión en `model:` (salieron modelos nuevos y quedaron atrás).
- Que los precios de este documento sigan vigentes.
- Que ningún agente nuevo haya entrado en Opus sin responder que sí a dos de las tres preguntas.
