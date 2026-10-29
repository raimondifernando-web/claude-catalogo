# Priorización

Cómo decidir **qué va primero** cuando hay más para hacer que tiempo. Sirve para elegir entre proyectos o iniciativas grandes y para ordenar un backlog.
Si el trabajo va a **Energía**, la prioridad de cada ítem ya sale de su cuenta (`2 × impacto − esfuerzo`, ver `energia.md`) y **no se reemplaza**: estos
marcos son para cuando alguien pide otro por nombre o la decisión es de otro tipo (varios proyectos compitiendo por el mismo equipo).

## Cómo elegir el marco

| Si necesitás… | Usá | Por qué |
|---|---|---|
| Ordenar tu semana | **Eisenhower** | Solo separa urgente de importante |
| Una lista corta de opciones, rápido | **Impacto vs. esfuerzo** (2×2) | Lo de mucho impacto y poco esfuerzo, primero |
| Ordenar muchas ideas con poca información | **ICE** | Tres puntajes de 1 a 10: Impacto, Confianza, Facilidad |
| Ordenar muchas ideas con datos de alcance | **RICE** | (Alcance × Impacto × Confianza) ÷ Esfuerzo |
| Acordar el alcance de un proyecto con fecha fija | **MoSCoW** | Debe · Debería · Podría · No esta vez |
| Cuando lo que importa es el tiempo (qué pierde más si se demora) | **Costo de demora (WSJF)** | Ver abajo |
| Decisiones grandes con varios criterios | **Matriz ponderada** | Cada criterio con peso; opciones con puntaje |
| Entender qué valora el cliente | **Kano** | Básicas · de desempeño · de deleite |
| Elegir qué necesidad del cliente atacar | **Puntaje de oportunidad** | Importancia alta y satisfacción baja = oportunidad |

Regla: **usá uno solo por decisión** y escribí cómo puntuaste. Hay variantes de casi todos; aclará cuál usaste.

## Los marcos, en una mirada

- **Eisenhower**: cuatro cuadrantes. *Urgente e importante* → hacerlo ya. *Importante, no urgente* → agendarlo (aquí vive lo que cambia las cosas). *Urgente, no importante* → delegarlo. *Ni lo uno ni lo otro* → eliminarlo.
- **ICE**: Impacto × Confianza × Facilidad. La **confianza** castiga las ideas sin evidencia. Rápido, pero los puntajes son opinión: puntuar entre varios.
- **RICE**: Alcance (a cuánta gente llega en un período) × Impacto (qué tanto mueve a cada una) × Confianza (%) ÷ Esfuerzo (tiempo de trabajo). Pide números de alcance; si no los hay, usá ICE.
- **MoSCoW**: *Debe* = sin esto el proyecto no sirve · *Debería* · *Podría* · *No esta vez*. **Tope a los «Debe»**: si todo es «Debe», no se priorizó. Como regla empírica sin respaldo, que los «Debe» no ocupen más de la mitad o poco más del esfuerzo; ajustalo con tu historia.
- **Costo de demora ÷ duración (WSJF)**: se hace primero lo que **más pierde por cada semana que se demora, por cada unidad de trabajo que cuesta**. El **costo de demora** suma tres cosas: valor para el cliente o el negocio + urgencia (¿hay fecha o ventana?) + lo que baja de riesgo o abre de oportunidad. Luego **se divide por la duración** (más largo = número más grande).
  **Ojo con el error más común**: si el tamaño se puntúa «al revés» (grande = 1) y aun así se divide, se favorece lo grande. La fórmula correcta: *más trabajo → número más alto de duración → menor prioridad*.
- **Matriz ponderada**: 3-5 criterios (impacto, costo, riesgo, alineación con objetivos…), cada uno con un peso que suma 100 %; cada opción puntúa de 1 a 5 en cada criterio. La suma ponderada ordena. Los pesos se **acuerdan antes** de mirar las opciones.
- **Kano**: no ordena trabajo: clasifica qué espera el cliente. *Básicas*: se dan por hechas (no suman si están, restan si faltan). *De desempeño*: más es mejor. *De deleite*: no las esperan; sorprenden.
- **Puntaje de oportunidad**: preguntá a clientes qué tan **importante** es una necesidad y qué tan **satisfechos** están hoy. Gran importancia + baja satisfacción = hueco para actuar.

## Equilibrar apuestas (tres horizontes)

Para no gastar todo en lo inmediato: separar una parte del esfuerzo para **lo que hoy da resultados** (la mayor parte), **lo que viene a continuación** (una parte menor) y **apuestas nuevas** (la menor). Una referencia habitual es 70 / 20 / 10; es una pauta, no un dato: ajustala al negocio.

## Trampas

- **Inflar puntajes** para que gane mi proyecto: puntuar entre varias personas y discutir las diferencias.
- **Quien patrocina empuja el suyo**: que puntúe otra persona o que se vea el puntaje de todos.
- **Parálisis**: si dos opciones puntúan casi igual, da lo mismo; elegí una y avanzá.
- **Confianza falsa**: si no hay evidencia, primero un experimento chico (`otros-metodos.md`, Lean Startup).
- **Los números ordenan la conversación, no deciden solos.**

## Salida

```
## Priorización — <decisión> · marco usado: <…>
| Opción | Criterio 1 | Criterio 2 | … | Puntaje | Orden |
Supuestos: <qué se supuso en los puntajes> · Quién puntuó: <…>
Decisión: <qué va primero y por qué> · Lo que queda afuera: <…>
```
