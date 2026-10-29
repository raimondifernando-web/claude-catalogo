# Kanban

Fuente de las definiciones: *The Kanban Guide* (v2025.5, kanbanguides.org). Kanban es una estrategia para optimizar el
**flujo de valor** a través de un proceso: ver el trabajo, limitar cuánto se hace a la vez y mejorar cómo fluye.
Sirve cuando el trabajo **llega todo el tiempo** (pedidos, contenido, consultas, tareas sueltas) y no en bloques con fecha.

## Las tres prácticas (de la guía)

1. **Definir y visualizar el flujo de trabajo**: poner en un tablero las etapas por las que pasa el trabajo, de que entra a que se termina.
2. **Gestionar activamente los elementos**: mirar lo que está en curso, no solo lo que entra; destrabar lo que lleva mucho.
3. **Mejorar el flujo**: revisar con datos dónde se frena y probar un cambio por vez.

## Armar el tablero (en 20 minutos)

1. **Una unidad de trabajo**: la tarea, el pedido o la pieza. Debe poder terminarse en días, no meses (si no, partila).
2. **Columnas = etapas reales**, no estados inventados. Mínimo: `Pendiente · En curso · En revisión · Hecho`. Agregá
   etapas solo si el trabajo realmente cambia de manos o de tipo de tarea (ej.: `Redacción → Diseño → Aprobación`).
3. **Límite de trabajo en curso (WIP) por columna.** Regla de arranque: **una o dos tareas por persona** en `En curso`.
   Si la columna está llena, no se empieza nada nuevo: se ayuda a terminar. Esto es lo que hace que algo salga.
4. **Políticas explícitas**: escribí en el tablero cuándo una tarea pasa de columna («está en revisión cuando tiene el
   borrador completo y se lo mostré a quien decide»). Sin esto cada uno interpreta distinto.
5. **Una columna de arranque ordenada**: `Pendiente` va ordenada por prioridad; lo de arriba es lo próximo. Una sola persona
   decide el orden.

## Las cuatro métricas de flujo (de la guía)

| Métrica | Qué es | Para qué sirve |
|---|---|---|
| **WIP** | Cuántos elementos están empezados y sin terminar | Si crece, se está empezando más de lo que se termina |
| **Throughput** | Elementos terminados por unidad de tiempo (conteo exacto) | Cuánto sale por semana; permite estimar |
| **Work Item Age** | Tiempo desde que se empezó un elemento hasta hoy | Alarma temprana: el elemento más viejo en curso es el que hay que mirar |
| **Cycle Time** | Tiempo desde que se empezó hasta que se terminó | Cuánto tarda una cosa en salir; promete plazos |

Con 10-15 elementos terminados ya se ve el patrón. No hace falta software: una planilla con fecha de inicio y de fin.

## Ritmo

No hay ciclos obligatorios. Lo mínimo útil: **revisión semanal del tablero** (15-20 min: qué está trabado, qué es lo más
viejo en curso, ¿se respetó el límite?) y **una mirada mensual a las métricas** para decidir un cambio.

## Lotes chicos y pronóstico

- **Lotes chicos**: terminar pocas cosas completas antes de empezar muchas. En marketing o ventas: un anuncio por día antes de una campaña de un mes; una oferta a 3 prospectos antes de capacitar a todo el equipo.
- **Pronosticar con un rango**: con el Cycle Time de las últimas 10-15 tareas terminadas, decí «la mayoría de las tareas como esta salen en X días o menos» (X sale de tu propia historia: por ejemplo, el valor bajo el cual terminó el 85 % de las últimas tareas), en lugar de prometer una fecha exacta. Con pocos datos, decilo.

## Errores típicos

- **Tablero sin límite de WIP**: es una lista de tareas con colores. No cambia nada.
- **Columna «En curso» llena de cosas que esperan a otro**: agregá una columna `Esperando a…` y mirala todos los días.
- **Tareas gigantes** que se quedan semanas en la misma columna: partirlas.
- **Cambiar el tablero cada semana**: dejalo estable un mes antes de ajustarlo.
- **Medir horas trabajadas** en lugar de flujo: no dice si se termina lo que importa.

## Cuándo no usar Kanban solo

Si hay una fecha fija con un objetivo que cumplir (un lanzamiento) y el equipo necesita compromisos por ciclo,
sumarle ciclos → `scrumban.md` o `scrum.md`.
