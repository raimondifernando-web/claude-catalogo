# 08 — Dónde viven los números

Un balance personal no es un documento: es algo que se recalcula todos los meses con tipo de
cambio nuevo, inflación nueva e ingresos nuevos. Por eso, antes de producir un artefacto que la
persona va a mantener en el tiempo, hay que saber dónde lo va a guardar. La respuesta no cambia
el cálculo; cambia la forma del entregable.

## Cuándo preguntar

**Preguntá** antes de generar algo que persiste: balance, flujo mensual recurrente, tablero de
objetivos, seguimiento de fondo de emergencia.

**No preguntes** para consultas puntuales que se abren y se cierran en la conversación: "¿cuánto
puedo gastar este mes?", "¿el plazo fijo me ganó a la inflación?", "¿cómo calculo el yield?".
Ahí respondés en el chat y listo.

Preguntá **una sola vez por conversación** y recordá la respuesta. Volver a preguntar cada vez es
molesto y sugiere que no estás siguiendo el hilo.

Formulación sugerida:

> Esto lo vas a querer actualizar cada mes. ¿Dónde te sirve que viva: una planilla (Sheets/Excel),
> Obsidian, Notion, o por ahora te lo dejo en el chat y después vemos?

## Qué entregar según el destino

### Planilla (Sheets / Excel)

Es el destino natural del **motor de cálculo**: el recálculo mensual con TC e inflación variables
es aritmética viva, y una planilla lo hace sola.

Entregá:
- Estructura de columnas explícita, una fila por movimiento o por activo.
- **Fórmulas escritas en sintaxis de planilla**, no solo el resultado. Ejemplo: si la columna E es
  monto en ARS y la F es el MEP de la fecha, la columna G es `=E2/F2`.
- Una hoja de parámetros separada (MEP por fecha, IPC por mes, supuestos) para que las fórmulas
  la referencien y no haya números hardcodeados en el medio del cálculo.
- Bloque CSV pegable al final, para que no tenga que tipear.

### Obsidian

Es el destino natural del **registro de decisiones y del criterio**: por qué se dolarizó en tal
momento, qué se acordó en la revisión de pareja de octubre, qué supuesto se usó y por qué. Los
números los recalculás vos; el vault guarda el razonamiento.

Entregá:
- Markdown con frontmatter YAML (`fecha`, `tipo`, `mep`, `ipc_mes`, `pn_usd`) para que sea
  consultable con Dataview.
- Tablas markdown nativas.
- Una nota por corte temporal (`2026-08 balance.md`), no una nota gigante que se sobrescribe: la
  serie histórica es el activo más valioso.
- Enlaces `[[ ]]` entre la nota de números y la nota de decisión que la originó.

### Notion

Destino razonable si ya vive ahí el resto de la operación personal, y bueno para lo relacional:
activos ↔ objetivos ↔ aportes mensuales.

Entregá:
- Definición de bases de datos con propiedades y tipos, y las relaciones entre ellas.
- Vistas sugeridas (por moneda, por titularidad, por horizonte).
- Contenido inicial en tabla markdown, que Notion importa razonablemente bien.

### Todavía nada

Entregá en el chat: tablas markdown legibles, y al pie un bloque CSV de la misma información por
si después decide migrar. No armes una infraestructura que no pidió.

## Regla transversal

Sea cual sea el destino, **la estructura de datos es la misma**. Las estructuras canónicas están
en `assets/`:

- `assets/estructura-balance.md`
- `assets/estructura-flujo.md`
- `assets/plantilla-revision-pareja.md`

Lo que cambia entre destinos es la presentación y el mecanismo de recálculo, nunca los campos ni
las fórmulas. Si te encontrás cambiando la estructura para que entre en una herramienta, la
herramienta está mandando sobre el análisis y eso es al revés.
