# Otros métodos y herramientas que un PM usa

Cada sección es corta a propósito: alcanza para **aplicar el método hoy**. Todas están escritas para equipos que no son de software.
Índice: Shape Up · Lean Startup y Lean Canvas · Design Sprint · Trabajos por hacer (JTBD) · Métrica que importa · Árbol de oportunidades. (Pre-mortem y riesgos: `riesgos.md`. Priorización: `priorizacion.md`.)

---

## Shape Up (Basecamp, 2019)

Para **proyectos grandes y difusos** que se atascan, en equipos chicos y autónomos. Ciclos de **6 semanas** seguidos de **2 semanas de enfriamiento**
(sin proyectos nuevos: se arreglan cosas, se explora, se descansa). Tres ideas centrales:

1. **Dar forma antes de apostar.** Alguien arma un **pitch** de 5 partes: **problema** (qué duele y a quién), **apetito** (cuánto tiempo *vale* este problema,
   no cuánto «tardaría»), **solución** (el trazo grueso, no el detalle), **agujeros de conejo** (los puntos donde el equipo se puede perder y cómo evitarlos) y **no-gos** (lo
   que expresamente se deja afuera).
2. **Apetito en vez de estimación.** El tiempo es la restricción fija; lo que se ajusta es el alcance. Un proyecto de 2 semanas y uno de 6 resuelven el mismo
   problema de maneras distintas.
3. **Interruptor automático (circuit breaker).** Si al terminar el ciclo no se terminó, **no se prolonga solo**: se vuelve a decidir si se reapuesta (con un nuevo apetito) o se abandona. Evita proyectos eternos.

**La apuesta**: cada ciclo, quien decide elige 1 a 3 pitches y se los entrega a un equipo chico, que decide cómo hacerlo. No hay lista infinita de pendientes: lo no elegido
se descarta o se vuelve a proponer.

**Gráfico de colina** (para seguir un proyecto con incertidumbre): cada tarea o parte del trabajo está **cuesta arriba** (todavía averiguando cómo hacerlo) o **cuesta abajo**
(ejecutando lo ya sabido). Si algo lleva más de dos semanas cuesta arriba, es una alarma: se corta el alcance o se pide ayuda.

*Opinión del método* (presentarla como opción, no como norma): no mantener un backlog y evitar reuniones fijas.

Salida mínima: `Pitch — problema · apetito · solución (trazo grueso) · agujeros de conejo · no-gos`.

---

## Lean Startup (Eric Ries, 2011) y Lean Canvas

Para **probar una idea nueva con poco gasto**: una oferta de consultoría, un producto, un servicio, una experiencia turística. Se trata de **aprender lo más rápido posible
qué es verdad**, antes de invertir.

**Ciclo construir → medir → aprender**, planificado al revés: primero *qué querés saber*, después *qué medir* y al final *qué construir* para obtener ese dato.

**Supuestos de salto de fe**: lo que tiene que ser verdad para que la idea funcione (que el problema duele, que pagarían, que nos encuentran, que repiten).
Listalos y **probá primero el más riesgoso**.

**La versión mínima (MVP)** es la forma más barata de aprender, no un producto chico. Tipos que funcionan sin software:
- **Concierge**: se hace a mano, con atención personalizada, para 3-5 clientes reales.
- **Mago de Oz**: parece automático pero lo hace una persona por detrás.
- **Prueba de humo**: una página o aviso que ofrece algo y mide cuántos dicen que sí.
- **Pieza por pieza**: se ensambla con herramientas existentes, sin construir nada propio.

**Escalera de validación** (de menos a más confiable): opinan que es buena idea → dicen que lo usarían → se anotan o dan sus datos → pagan una seña → lo usan de verdad y vuelven.
Quedarse en los primeros escalones es engañarse.

**Pivotar o perseverar**: decidí **antes de empezar** qué resultado te haría cambiar de rumbo (de segmento de cliente, de necesidad, de canal o de forma de cobrar) y qué te haría seguir.
Sin esa regla, cualquier dato se interpreta a favor.

**Lotes chicos**: probar con 3 clientes antes de armarlo para 30; un anuncio por día en lugar de una campaña de un mes; una oferta con 3 prospectos antes de capacitar a todo el equipo.

### Lean Canvas (Ash Maurya)
Una hoja con 9 casillas para poner la idea en limpio y ver qué no está probado:
1. **Problema** (los 3 principales y cómo se resuelven hoy) · 2. **Segmentos de clientes** (empezá por los primeros, los que más sufren) · 3. **Propuesta de valor** (una frase) ·
4. **Solución** · 5. **Canales** · 6. **Ingresos** · 7. **Costos** · 8. **Métricas clave** · 9. **Ventaja difícil de copiar**.
Úsalo para **detectar hipótesis**, no como plan terminado. Lo útil: marcá las 2-3 casillas más riesgosas y diseñá un experimento chico para cada una (entrevistas, prueba de humo, venta a mano).

---

## Design Sprint (Google Ventures, 2016)

**Cinco días** para pasar de un problema a un prototipo probado con 5 personas reales. **Pesado**: pide un equipo chico (alrededor de 5-7) y una persona con poder de decisión (el «Decidor») disponible toda la semana.

| Día | Qué se hace |
|---|---|
| Lunes | Mapear el problema, elegir a quién y qué parte atacar |
| Martes | Cada persona esboza soluciones **por separado** (sin discutir en grupo) |
| Miércoles | Se decide: se mira lo esbozado y el Decidor elige; se arma el guion de la prueba |
| Jueves | Se arma un prototipo creíble (una **fachada**: puede ser un guion o un juego de roles si es un servicio) |
| Viernes | Se prueba con 5 personas, una por una, y se buscan patrones |

**Cuándo sí**: una decisión grande y riesgosa, un equipo trabado en el debate, un problema claro pero sin solución. **Cuándo no**: no hay Decidor toda la semana, no se sabe qué problema atacar,
la idea ya está probada o es chica (alcanza con un experimento de Lean Startup). Con 5 usuarios ya aparecen los patrones.

---

## Trabajos por hacer (Jobs to be Done, JTBD)

Idea: la gente no compra un producto: lo **contrata para progresar en una situación concreta**. Sirve para entender por qué compran (marketing, ventas B2B, consultoría).

**Frase del trabajo**: «**Cuando** [situación], **quiero** [lo que busca], **para** [el resultado que espera]». Describe la situación, no al cliente.

**Tres dimensiones**: **funcional** (lo que necesita lograr), **emocional** (cómo quiere sentirse), **social** (cómo quiere que lo vean).

**Cuatro fuerzas** de un cambio de proveedor o de hábito:
- **Empujón**: lo que molesta de la situación actual.
- **Atracción**: lo que seduce de la nueva opción.
- **Ansiedad**: miedo a que no funcione o a lo desconocido.
- **Hábito**: lo cómodo de seguir como está.
Se cambia cuando **empujón + atracción** pesan más que **ansiedad + hábito**. Para vender, a menudo conviene **bajar la ansiedad** más que subir la atracción.

**Competidor no obvio**: lo que la persona hace hoy en lugar de comprar (una planilla, hacerlo a mano, **no hacer nada**).

**Entrevista por línea de tiempo**: pedirle a un cliente reciente que reconstruya, paso a paso, cuándo empezó a pensar en cambiar, qué probó, qué lo frenó y qué lo decidió.
**Siempre hechos pasados reales, nunca «¿lo comprarías?»**: la gente es mala prediciendo y buena contando lo que ya hizo.

---

## La métrica que importa (métrica norte)

Elegí **una** métrica que mejor diga si el cliente recibe valor, y **3-5 métricas de entrada** que la mueven. No reemplaza a los OKR: un OKR puede moverla.

**7 criterios para validarla**: fácil de entender · centrada en el cliente (no en tu facturación) · refleja valor que se **sostiene** · alineada con la visión · numérica · accionable (el equipo puede moverla) · se adelanta a los ingresos.

**Cuatro reglas prácticas:**
1. **Razones, no totales.** «Total de usuarios» siempre sube y no dice nada; «% que vuelve a los 30 días» sí.
2. **Cada métrica con su contramétrica** (es el KR vigilante de `okr.md`): crecimiento de altas ↔ retención; velocidad de venta ↔ devoluciones; costo por cliente nuevo ↔ valor del cliente por canal.
3. **Línea en la arena**, escrita **antes**: el valor que querés alcanzar, la fecha y **qué vas a hacer si no se alcanza**. Evita justificar después.
4. **Etapa antes que optimización**: no tiene sentido gastar en atraer gente si los que llegan no vuelven. Ordená: ¿les importa? → ¿vuelven? → ¿recomiendan? → ¿pagan lo suficiente? → ¿se puede escalar?

No copies cifras de «referencia» de otras empresas: cada negocio tiene la suya, y se mide con **su** línea de base.

---

## Árbol de oportunidades

Une un **resultado clave** con las ideas, para no saltar de un número directo a una solución. Cuatro niveles:
1. **Resultado deseado** (un KR: «subir de X a Y»).
2. **Oportunidades**: necesidades, dolores o deseos del cliente que, si se atienden, mueven ese resultado. Se descubren **escuchando a clientes cómo les va**, no preguntándoles qué construir.
3. **Soluciones**: **al menos 3 por oportunidad** antes de elegir una; la primera idea casi nunca es la mejor.
4. **Experimentos**: la prueba más barata de que esa solución mueve la oportunidad.
Se prioriza **oportunidades** (¿cuál es más importante y está peor atendida?), no funciones. En Energía: el KR es la raíz; los proyectos son soluciones elegidas; las tareas, los experimentos.

---

## Pre-mortem, riesgos y priorización

Tienen archivo propio: **pre-mortem y registro de riesgos** en `riesgos.md`; **marcos de priorización** (ICE, RICE, MoSCoW, costo de demora, Kano…) en `priorizacion.md`.
