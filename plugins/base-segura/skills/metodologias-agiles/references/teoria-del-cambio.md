# Teoría del cambio y marco lógico

Se usa cuando hay que **explicar por qué una intervención cambiaría algo** y cómo se sabría: proyectos de impacto (social,
ambiental, comunitario, de turismo regenerativo), programas, subsidios, certificaciones, o cualquier apuesta de largo plazo donde
la cadena de causas no es obvia. No es una metodología ágil en sentido estricto; se incluye porque ordena el **por qué** que
después se convierte en OKR y en proyectos.

## Teoría del cambio (TdC)

Es un mapa, trazado **desde el final hacia atrás** (Carol Weiss y otros, desde los años 90): cambio de largo plazo → lo que tiene
que pasar antes → lo que se hace → en qué se está suponiendo algo.

### La cadena de resultados

```
Insumos → Actividades → Productos → Resultados → Impacto
(qué usamos) (qué hacemos) (qué entregamos) (qué cambia en las personas/el sistema) (el cambio de fondo y duradero)
```

- **Producto (output)**: lo que se entrega y se cuenta: «30 talleres dados».
- **Resultado (outcome)**: lo que **cambia** en alguien por eso: «los productores aplican la técnica».
- **Impacto**: el cambio de fondo, de largo plazo y con otros factores en juego.
Error clásico: reportar productos como si fueran resultados.

### Cómo armarla (7 pasos, en este orden)

1. **Impacto buscado**: el cambio de largo plazo, en una frase y con el sujeto que cambia («la comunidad vive de actividades que cuidan el humedal»).
2. **Para quién**: quiénes cambian (personas, organizaciones, ecosistema). Si es «todos», es vago.
3. **Resultados intermedios, hacia atrás**: ¿qué tiene que ser verdad antes para que pase el impacto? Y antes de eso, ¿qué? Seguí hasta llegar a algo que podés hacer vos.
4. **Actividades**: qué se hace para producir cada resultado.
5. **Supuestos**: en qué se apoya cada flecha. «Si los productores reciben capacitación, **suponemos** que tienen tiempo y capital para aplicarla.»
   Esto es lo más valioso de una TdC: dice qué hay que verificar.
6. **Indicadores y evidencia**: cómo se sabría que cada resultado ocurrió (número o señal observable) y de dónde sale el dato.
7. **Riesgos y qué podría romper la cadena**: qué haría fallar cada eslabón.

### Prueba rápida de calidad

- ¿Cada flecha tiene un *porque*? Si no, hay un salto mágico.
- ¿Los supuestos se pueden comprobar? Si no, convertilos en una pregunta a investigar.
- ¿Podés señalar el eslabón que, si falla, tira abajo todo?
- ¿Hay actividades que no conducen a ningún resultado? → candidatas a no hacerse.

## Marco lógico (la matriz)

Es la versión de **una tabla** de la TdC, usada por organismos de cooperación y financiadores (Enfoque del Marco Lógico, desde fines de los 60).
Útil cuando alguien pide formato ordenado para aprobar o auditar un proyecto.

| | Resumen narrativo | Indicadores | Medios de verificación | Supuestos |
|---|---|---|---|---|
| **Fin** (impacto) | El cambio de largo plazo al que contribuye | Cómo se mide | De dónde sale el dato | Condiciones externas para que el proyecto contribuya al fin |
| **Propósito** (resultado) | El cambio concreto que se logra | … | … | Lo que debe cumplirse para llegar al fin |
| **Componentes** (productos) | Lo que se entrega | … | … | Lo que debe cumplirse para llegar al propósito |
| **Actividades** | Lo que se hace | Recursos / presupuesto | Registros, facturas | Lo que debe cumplirse para producir los componentes |

**Se lee en vertical** (si hacemos las actividades *y* se cumplen los supuestos → hay componentes → … → fin) **y en horizontal**
(cada fila: qué, cómo se mide, de dónde sale el dato, qué puede fallar). Si una fila no tiene indicador o fuente, no se puede evaluar.

## Cómo se conecta con lo demás

- **TdC → OKR**: el **objetivo** del OKR sale del **resultado** o impacto que se quiere mover este ciclo; los **resultados clave**
  son los indicadores de esos resultados, con línea de base y meta (`okr.md`).
- **TdC → proyectos y tareas**: las **actividades** y **productos** son los proyectos y tareas (`energia.md`). Si una actividad no
  conduce a ningún resultado de la TdC, se marca «sin KR».
- **Supuestos → pruebas rápidas**: los supuestos más riesgosos se convierten en experimentos chicos (`otros-metodos.md`, Lean Startup).
- **Revisión**: cada 6-12 meses se vuelve a mirar la TdC con la evidencia: ¿se cumplieron los supuestos?

## Formato de salida

```
## Teoría del cambio — <proyecto>
Impacto buscado: <una frase> · Para quién: <sujeto>
Cadena: <resultado final> ← <resultado intermedio 2> ← <resultado intermedio 1> ← <actividades>
Supuestos (a verificar):
- A1: <supuesto> → cómo se comprueba: <…>
Indicadores: <resultado> → <métrica, inicio, meta, fuente>
Riesgos: <eslabón> → <qué lo rompe>
```
Si el destinatario pide marco lógico, completar la matriz de arriba.
