# Ágil en general: principios y mapa de métodos

«Ágil» no es un método: es una forma de pensar el trabajo, nacida en software (el *Manifiesto Ágil*, 2001) y copiada después a casi cualquier
área. Los métodos concretos (Scrum, Kanban, Shape Up…) son maneras de aplicarla.

## Los 4 valores del Manifiesto

Se valora **más** lo de la izquierda, sin despreciar lo de la derecha:
1. **Las personas y cómo interactúan** más que los procesos y las herramientas.
2. **Lo que funciona** (algo terminado y usable) más que la documentación exhaustiva.
3. **Colaborar con quien recibe el trabajo** más que negociar contratos.
4. **Responder al cambio** más que seguir un plan al pie de la letra.

## Ideas que se repiten en todos los métodos

- **Entregar en ciclos cortos** algo terminado y usable, y aprender de lo que pasa.
- **Visibilidad**: que todos vean qué se hace, quién y cuánto falta (un tablero basta).
- **Limitar lo que se hace a la vez**: terminar antes que empezar.
- **Priorizar con un criterio claro** y una sola persona que decide el orden.
- **Feedback rápido** de quien usa o recibe el resultado.
- **Mejorar el método mismo** con retrospectivas (`retrospectivas.md`).
- **Equipos chicos con autonomía** y objetivos claros (`okr.md`).

## Mapa de métodos

| Método | Qué es | Nació en | Sirve cuando | Archivo |
|---|---|---|---|---|
| **Scrum** | Ciclos fijos (Sprint) con meta, roles y 5 reuniones | Software, 1990s | Trabajo en bloques con fecha | `scrum.md` |
| **Kanban** | Tablero con límite de trabajo en curso y métricas de flujo | Producción Toyota → software | Trabajo que llega todo el tiempo | `kanban.md` |
| **Scrumban** | Híbrido: ciclos y metas de Scrum + tablero y límites de Kanban | Software, ~2008 | Trabajo continuo con metas por ciclo | `scrumban.md` |
| **Shape Up** | Ciclos de 6 semanas, apuestas con tiempo fijo, 2 semanas de enfriamiento | Basecamp, 2019 | Proyectos grandes y difusos, equipos chicos y autónomos | `otros-metodos.md` |
| **Lean Startup** | Construir-medir-aprender con la versión más chica que enseñe algo | Emprendimiento, 2011 | Probar una idea nueva con poco gasto | `otros-metodos.md` |
| **Design Sprint** | 5 días para pasar de un problema a un prototipo probado | Google Ventures, 2016 | Decidir rápido si una idea vale | `otros-metodos.md` |
| **XP (Extreme Programming)** | Prácticas de ingeniería: pares, pruebas automáticas, integración continua | Software, 1990s | Solo equipos de programación | (no se desarrolla) |
| **Escalado (SAFe, LeSS…)** | Coordinar muchos equipos ágiles | Empresas grandes | Decenas de personas o más | (no se desarrolla) |
| **OKR** | Objetivos con resultados medibles por ciclo | Intel/Google | Dar rumbo medible | `okr.md` |
| **Teoría del cambio** | Mapa de por qué una intervención cambiaría algo | Evaluación de programas | Impacto de largo plazo | `teoria-del-cambio.md` |

## Cómo elegir (resumen)

1. ¿Se sabe qué número tiene que moverse? No → **OKR** primero.
2. ¿El trabajo llega en bloques con fecha? **Scrum**. ¿Llega siempre? **Kanban**. ¿Las dos? **Scrumban**.
3. ¿Proyecto grande y difuso, equipo autónomo? **Shape Up**.
4. ¿Idea nueva que hay que probar barato? **Lean Startup** o **Design Sprint**.
5. ¿Cambio social o de largo plazo a justificar? **Teoría del cambio**.
6. Siempre sumar **retrospectivas**.

## Empezar sin morir en el intento

1. **Empezá por lo más chico**: un tablero con límite de trabajo en curso y una reunión semanal de 20 minutos ya es ser ágil.
2. **Un método a la vez**, y probarlo al menos 3 ciclos antes de cambiarlo.
3. **Sumá una pieza cuando duela no tenerla** (metas → OKR; ritmo → ciclos; mejora → retro), no por completitud.
4. **Medí el flujo** (cuántas cosas se terminan por semana, cuánto tardan) antes de medir velocidad o puntos.
5. **Nunca uses la métrica de un método para evaluar personas**: la rompe.

## Señales de que «lo ágil» está funcionando

- Se sabe en 30 segundos qué se está haciendo y qué sigue.
- Se termina más de lo que se empieza.
- Las reuniones terminan con una decisión.
- Cada ciclo se ve algo terminado que alguien usa o mira.
- El equipo cambia el método cuando no le sirve.

## Señales de que se volvió ceremonia

- Reuniones que nadie usa para decidir; tableros que nadie mira.
- «Sprints» de lista de tareas sin meta.
- Estimaciones que se discuten más que el trabajo.
- Todo es urgente.
- Se mide a las personas con las métricas del método.
