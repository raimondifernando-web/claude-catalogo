# 07 — Datos de entrada: qué pedir antes de calcular

Principio: **cuando falta un dato crítico, pedilo; no lo estimes en silencio.** Un supuesto
declarado se puede corregir; uno tácito se propaga por todo el análisis y nadie se entera hasta
que la decisión ya se tomó.

Pedí en un bloque, no de a uno. Y pedí solo lo que el análisis en cuestión necesita: una lista de
veinte preguntas para responder "¿cuánto puedo gastar este mes?" no es rigor, es fricción.

## Set mínimo por tipo de análisis

### "¿Cuánto puedo gastar?" / presupuesto

Crítico:
- Ingreso de los últimos 6–12 meses, mes a mes (no el promedio: la serie).
- Gasto fijo mensual actual y su moneda de exposición.
- Saldo de activos líquidos hoy.
- Compromisos comprometidos a futuro conocidos (cuotas, colegio, un viaje pago).

Se puede suponer declarándolo: proporción de gasto variable y discrecional, inflación proyectada.

### Balance / patrimonio neto

Crítico:
- Listado de activos con **valor de mercado hoy** y moneda.
- Listado de pasivos con saldo, moneda, indexación y qué activo los garantiza.
- Para el equity en empresas: valuación de referencia y su origen, % de participación, si controla
  o no la distribución de utilidades.
- Régimen patrimonial del matrimonio, si aplica.

No se puede suponer: la valuación de la empresa. Si no la hay, mostrá el balance con y sin ese
activo y decilo.

### Tasa de ahorro / flujo

Crítico:
- Ingresos y gastos del período **con fecha**, o al menos la fecha modal de cada uno.
- MEP de esas fechas.
- Saldo de activos líquidos al inicio y al final del período (para reconciliar).

Sin el saldo inicial y final no podés validar nada y el resultado no es auditable. Pedilo.

### Fondo de emergencia

Crítico:
- Gasto comprimido mensual (fijo + variable mínimo).
- Serie de ingresos de 24–36 meses, para identificar la peor racha.
- Origen del ingreso: ¿cuánto viene de la misma empresa que constituye el patrimonio principal?

### Yield de un inmueble

Crítico:
- Valor de mercado hoy (no el de compra ni el fiscal).
- Renta bruta y **fórmula de ajuste del contrato** (índice, frecuencia, moneda).
- Gastos a cargo del propietario: expensas, impuestos, seguros.

Se puede suponer declarándolo: mantenimiento (5–8% de la renta bruta) y vacancia (1 mes cada
24–36).

### Análisis familiar / de pareja

Crítico:
- Ingresos de cada persona por separado.
- Criterio de asignación de gastos compartidos vigente, si existe alguno.
- Objetivos de cada uno con monto, fecha y prioridad declarada por su titular.
- Dependientes: cantidad, edades, gastos asociados actuales y escalones previsibles.

No supongas prioridades. Si no las tenés, la salida es la tabla de objetivos vacía para que la
completen ellos, no una tabla completada por vos.

## Cómo pedir

Formato que funciona:

> Antes de calcular necesito cuatro datos. Sin ellos el resultado sería una estimación mía
> presentada como si fuera tuya:
>
> 1. …
> 2. …
>
> Si alguno no lo tenés a mano, decime cuál y lo trabajo como supuesto explícito, marcado en el
> output.

## Inconsistencias a chequear siempre, antes de calcular

Revisá esto en los datos que te den y **señalá lo que encuentres antes de mostrar cualquier
resultado**:

- Flujos sin moneda o sin fecha.
- Ahorro declarado que no coincide con la variación del saldo líquido.
- Gasto familiar declarado muy por debajo del consumo observable → probable mezcla con la empresa
  (ver `06-interfaz-empresa.md`).
- Ingreso "mensual" que en realidad es un promedio de una serie muy dispersa.
- Un activo valuado al costo de adquisición en un contexto de alta inflación.
- Equity de la empresa a valor libro o a precio de venta esperado sin descuento.
- Un mismo importe contado dos veces: por ejemplo, el ahorro de alquiler de la vivienda propia
  contado como renta del activo **y** como menor gasto.
- Deuda de la empresa con garantía personal que no figura en el balance personal.
