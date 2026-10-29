# Scrum

Fuente: *La Guía de Scrum 2020* (scrumguides.org; Schwaber y Sutherland, 2020). Scrum es un marco liviano para entregar valor
en **ciclos cortos con un objetivo**, con un equipo chico y revisión constante. Sirve para trabajo **en bloques con fecha**
(campañas, lanzamientos, proyectos con entregas) y cuando se necesita que el equipo se comprometa con algo cada 1-4 semanas.

## Las piezas (según la guía)

| Qué | Contenido |
|---|---|
| **Equipo Scrum** | Una sola unidad, típicamente de 10 personas o menos. Tres responsabilidades: **Developers** (quienes hacen el trabajo, sea cual sea), **Product Owner** (maximiza el valor y ordena el Product Backlog), **Scrum Master** (hace que Scrum funcione y mejora al equipo) |
| **Sprint** | Ciclo de duración fija, **un mes o menos**. Todo el trabajo ocurre dentro de un Sprint |
| **Eventos** | Sprint · Sprint Planning · Daily Scrum · Sprint Review · Sprint Retrospective |
| **Artefactos y su compromiso** | **Product Backlog** → Product Goal · **Sprint Backlog** → Sprint Goal · **Increment** → Definition of Done |

**Tiempos máximos (para un Sprint de un mes; más cortos si el Sprint es más corto):** Planning 8 h · Daily 15 min · Review 4 h ·
Retrospective 3 h. En la práctica, para un Sprint de 2 semanas: Planning ~2-3 h, Review ~1-2 h, Retro ~1-1,5 h.

## Cómo se corre un Sprint (paso a paso)

1. **Product Backlog**: lista ordenada de todo lo que podría hacerse, lo más importante arriba. La mantiene el Product Owner.
   Tiene un **Product Goal**: el objetivo de más largo plazo (puede ser un OKR).
2. **Sprint Planning**: se contesta *¿por qué este Sprint es valioso?* (el **Sprint Goal**, una frase), *¿qué se puede terminar?*
   (se elige del Product Backlog) y *¿cómo se hace?* (se parte en tareas). Lo elegido es el **Sprint Backlog**.
3. **Daily Scrum (15 min, todos los días, mismo lugar y hora)**: el equipo revisa si va hacia el Sprint Goal y ajusta el plan del día.
   No es un informe al jefe; es coordinación entre quienes hacen el trabajo.
4. **Sprint Review**: se muestra lo terminado a quienes dependen de eso, se recibe opinión y se ajusta el Product Backlog.
5. **Sprint Retrospective**: el equipo mira *cómo* trabajó (personas, proceso, herramientas) y elige **una a tres mejoras** para el
   próximo Sprint → `retrospectivas.md`.
6. **Increment + Definition of Done**: «terminado» significa que cumple una lista corta acordada (ej.: «publicada, revisada por quien
   aprueba y medida»). Lo que no cumple, no cuenta y vuelve al Backlog.

## Escribir bien un ítem del backlog

Un ítem de trabajo útil responde tres preguntas (formato **Por qué / Qué / Cómo sabemos que está hecho**):
- **Por qué**: a qué objetivo o KR aporta (sin esto, es una ocurrencia).
- **Qué**: lo que hay que hacer, en una o dos líneas; es un recordatorio para conversar, no una especificación.
- **Hecho cuando**: criterios que se pueden comprobar, en la forma **«Dado [situación], cuando [acción], entonces [resultado]»** si ayuda.

**Prueba INVEST** (6 preguntas): ¿es **I**ndependiente (se puede hacer sin esperar a otro)? ¿**N**egociable (el cómo se conversa)? ¿**V**aliosa (alguien lo nota)? ¿**E**stimable (se sabe más o menos cuánto lleva)? ¿**P**equeña (entra en un ciclo)? ¿**V**erificable (se puede probar que está hecho)? Si falla una, partilo o reescribilo.

**Partir un trabajo grande**: por paso del recorrido · por canal o cliente · por tipo de dato o de pieza · por operación (crear / editar / borrar) · **primero el camino feliz** y después los casos raros.
Ej. marketing: «campaña de lanzamiento» → «una pieza para un canal con un público» → «la misma en el segundo canal» → «medición».

**Si nadie sabe estimar** («ni idea»): primero una **investigación acotada** (*spike*: poco tiempo, una pregunta, una respuesta) y recién después se estima el trabajo.

## Capacidad y pronóstico

- **Comprometé menos que la capacidad total**: descontá vacaciones, feriados e imprevistos. Una regla empírica, sin respaldo, es llenar el 80-85 % de lo habitual y dejar un tramo opcional si sobra; ajustala con tu propia historia.
- **Pronosticá con un rango**, no con un número: mirá cuántas tareas terminadas por ciclo hubo en los últimos 4-6 ciclos y usá el **peor, el típico y el mejor**. Con pocos ciclos la confianza es baja; si cambió el equipo, empezá de nuevo.
- Antipatrón: planificar al 100 % de capacidad, o «estirar» como forma disimulada de sobrecargar.

## Cómo adaptarlo a un equipo que no es de software

- **Sprint de 1 o 2 semanas** (en software se usan 2; en campañas o ventas, 1-2 funciona mejor).
- **Product Owner** = quien decide qué importa más (el dueño de la campaña, de la cuenta o del proyecto). **Scrum Master** = quien
  cuida el método y destraba; puede ser una persona del equipo unas horas por semana.
- **Estimar**: no hacen falta puntos. Contá cuántas tareas chicas se terminaron por Sprint (→ `kanban.md`, throughput) y planificá con
  esa cifra. Si estimás, usá talles (chico/mediano/grande).
- **Equipo de una sola persona**: sigue valiendo: Sprint Goal semanal, tablero y una revisión del viernes.
- **Sprint Goal siempre**: sin una frase de objetivo, un Sprint es una lista de tareas. Es lo que lo distingue.

## Errores típicos

- **Sprint sin Sprint Goal** (lista de tareas con otro nombre).
- **Agregar trabajo a mitad de Sprint** sin sacar otro: se pierde el compromiso. Lo urgente de verdad se negocia con el Product Owner.
- **Daily como reunión de estado** para un jefe: se vuelve un trámite.
- **Retrospectiva sin acciones** o con más de tres: no se hace ninguna.
- **«Terminado» ambiguo**: sin Definition of Done, todo está «casi listo».
- **Usar la velocidad para comparar personas o equipos**: la destruye como herramienta de planificación.

## Cuándo no usar Scrum

Si el trabajo llega todo el tiempo y no hay objetivos por ciclo (soporte, pedidos sueltos) → `kanban.md`. Si hay una mezcla → `scrumban.md`.
