# Scrumban

Scrumban no es un marco oficial con guía propia: es un **híbrido** (lo describió Corey Ladas hacia 2008) que toma el ritmo y las
reuniones de Scrum y le suma el tablero con **límite de trabajo en curso** y el flujo continuo de Kanban. Es lo que suele
terminar usando un equipo cuando le llega trabajo todo el tiempo **y** además tiene metas por período.
Decí siempre que es un híbrido y que la receta de abajo es una forma razonable de armarlo, no «la» definición.

## Cuándo conviene

- Entra trabajo continuo (pedidos, contenido, soporte) pero también hay metas por mes o trimestre.
- Scrum se siente rígido (el trabajo urgente rompe el Sprint) y Kanban solo se siente flojo (falta rumbo o ritmo).
- El equipo ya usa un tablero y quiere sumarle objetivos y revisiones por ciclo.

## La receta (de Scrum se queda…)

- **Ciclo corto** (1-2 semanas) con una **meta del ciclo**, una frase.
- **Revisión** al final: mostrar lo terminado y ajustar prioridades.
- **Retrospectiva** cada 2-4 ciclos (no hace falta cada uno) → `retrospectivas.md`.
- **Un responsable del orden** de lo que sigue (el «Product Owner»).

## …y de Kanban se toma

- **Tablero con límite de trabajo en curso** (`kanban.md`): es la regla que hace fluir.
- **Flujo continuo**: no se «cierra» el ciclo para empezar a trabajar en lo que llegó; se agrega al tablero si hay lugar.
- **Planificación bajo demanda**: en vez de una reunión larga de planificación al inicio del ciclo, se **repone** cuando se baja de
  un umbral. Ejemplo: cuando `Pendiente` baja de 3 tareas, se reúnen 15 minutos y se vuelve a llenar hasta 6.
- **Métricas de flujo** (Cycle Time, Throughput, Work Item Age) en lugar de puntos y velocidad.

## Armarlo en una hoja

| Pieza | Cómo queda |
|---|---|
| Tablero | `Pendiente (máx. 6) · En curso (límite por persona) · En revisión · Hecho` |
| Meta del ciclo | Una frase arriba del tablero, ligada a un KR si hay OKR |
| Reposición | Al bajar `Pendiente` de 3: 15 min para elegir las siguientes, ordenadas por prioridad |
| Revisión | Cada 1-2 semanas: qué se terminó, qué sigue, ¿se cumplió la meta? |
| Revisión de métricas | Una vez por mes: Cycle Time, Throughput y lo más viejo en curso |
| Carril urgente | Una fila aparte, con límite de 1: lo realmente urgente pasa adelante sin romper el resto |

## Errores típicos

- **Sumar todas las reuniones de Scrum y todas las reglas de Kanban**: queda más pesado que ambos. Elegí lo mínimo.
- **Carril urgente que se llena**: si todo es urgente, nada lo es; el límite de 1 existe para eso.
- **Sin meta de ciclo**: es solo Kanban con reuniones.
- **Sin límite de trabajo en curso**: es solo Scrum sin ciclo.

## Cuándo no usarlo

Si el equipo recién arranca con ágil, empezar por **uno solo**: Kanban si el trabajo es continuo, Scrum si es por bloques con fecha.
Pasar a Scrumban cuando el equipo ya vea el tablero y haga una revisión sostenida.
