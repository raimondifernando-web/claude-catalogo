# 06 — Interfaz con las finanzas de la empresa

Esta skill **no analiza la empresa**. La recibe como input. Este archivo define qué input necesitás,
cómo interpretarlo y cómo medir el riesgo que la empresa introduce en el patrimonio personal.

Si la conversación deriva hacia el análisis de la empresa en sí —valuación, márgenes, EBITDA,
cobranzas, runway del negocio— pasá la posta a la skill correspondiente y volvé cuando tengas el
dato que necesitás.

## Variables empresariales que alimentan el flujo personal

Pedí estas seis. Sin ellas el flujo personal de un socio es adivinanza:

1. **Política de retiro declarada**: monto, frecuencia, y bajo qué condición se suspende.
2. **Retiro efectivo histórico**: 12 a 24 meses, mes a mes. La distancia entre política y efectivo
   es el dato más informativo de los seis.
3. **Capacidad de pago**: cuánto puede distribuir la empresa sin comprometer su operación. Viene
   de la empresa, no lo estimes vos.
4. **Estacionalidad del caja del negocio**: cuándo puede distribuir y cuándo no.
5. **Compromisos personales atados a la empresa**: avales, garantías personales sobre deuda
   societaria, inmuebles familiares hipotecados por el negocio.
6. **Procesos en curso** que cambien el cuadro: venta, incorporación de socios, capitalización.

## Qué es un retiro: el árbol de decisión

Esta es la distinción que más ensucia los balances personales, porque tres cosas distintas salen
de la misma cuenta bancaria y el extracto las muestra iguales.

**Preguntá siempre: ¿contra qué se imputa este retiro?**

| Naturaleza | Qué es | Efecto en el flujo | Efecto en el balance |
|---|---|---|---|
| **Sueldo / honorarios** | Contraprestación por trabajo. Gasto de la empresa | **Ingreso genuino.** Entra al flujo recurrente | Solo sube el efectivo |
| **Adelanto de utilidades** | Anticipo contra una utilidad que todavía no se declaró | **Ingreso condicional.** Entra al flujo, pero marcado | Si al cierre no hay utilidad suficiente, se convierte en **deuda del socio con la empresa** → aparece un pasivo personal |
| **Devolución de aportes / reducción de capital** | Recuperás plata que ya era tuya | **NO es ingreso.** Es conversión de activo | Baja el equity, sube el efectivo. **El PN no cambia** |
| **Dividendo formalmente declarado** | Distribución de utilidad aprobada | **Ingreso genuino, no recurrente** | Sube el efectivo, baja el equity por la utilidad distribuida |

Por qué importa tanto: **contar una devolución de aportes como ingreso infla la tasa de ahorro y
hace creer que hay un excedente que no existe.** La persona ve que "ahorró" USD 20.000 en el año
cuando en realidad movió USD 20.000 de un bolsillo ilíquido a uno líquido, sin crear nada. Sobre
ese espejismo se toman decisiones de gasto que después no se sostienen.

El adelanto de utilidades tiene el problema simétrico: se siente como ingreso durante todo el año
y puede terminar siendo deuda en diciembre. Marcalo siempre como condicional, y en el escenario
conservador tratalo como pasivo.

Si la persona no sabe contra qué se imputan sus retiros, ese es el hallazgo: no es un problema de
cálculo, es un problema de registro, y hay que resolverlo antes de seguir.

## Préstamos entre la persona y la empresa

Van en las dos direcciones y las dos veces se olvidan de registrar.

**Persona → empresa** (le presté plata al negocio):
Es un **activo personal**, pero su cobrabilidad es la de la empresa. Registralo con la misma vara
que el equity: si la empresa está apretada, ese crédito no vale su valor nominal. Aplicá un
descuento declarado y no lo cuentes como líquido.

**Empresa → persona** (saqué plata y quedó como cuenta particular):
Es un **pasivo personal real**, aunque no haya papel, aunque nadie lo reclame y aunque
"total es mi empresa". Tres razones:
- Si aparece un socio nuevo o un comprador, se reclama.
- Impositivamente puede tratarse como disposición de fondos a favor del socio, con consecuencias.
- En un proceso de venta, sale a la superficie como ajuste.

Regla: **si está en la cuenta particular del socio, va como pasivo en el balance personal.** Sin
excepciones y sin discutir la intención.

## Riesgo de correlación

El punto más importante de este archivo.

Cuando el ingreso familiar y el activo principal dependen de la misma empresa, la diversificación
del resto del patrimonio es en gran medida aparente. No son dos exposiciones: es una sola, contada
dos veces.

```
exposición_efectiva = (valor_empresa_en_balance / PN_total)
                    + (ingreso_proveniente_de_la_empresa / ingreso_familiar_total)
```

Escala de lectura (sobre 200 posibles):

- `< 60` — la empresa es una parte del cuadro.
- `60 – 100` — exposición alta. Vale la pena que la persona la vea escrita.
- `100 – 150` — el patrimonio familiar **es** la empresa, con decoración alrededor.
- `> 150` — cualquier discusión de asignación de activos sobre el resto del patrimonio es marginal
  frente a esta concentración.

**Escenario obligatorio en toda proyección de una familia en esta situación:**

> *La empresa deja de distribuir durante 12 meses y su valuación cae 40%.*

No es pesimismo: es el escenario en que las dos exposiciones fallan juntas, que es como fallan en
la realidad. Si el plan sobrevive a eso, es un plan. Si no, la conversación es sobre concentración,
no sobre presupuesto.

**Sobre una venta de empresa en proceso:** hasta el closing no es flujo. Entra a la proyección
como escenario con probabilidad declarada, con su timing incierto y su estructura (earnout, pagos
diferidos, retenciones en garantía) explicitada, porque el "precio" y el "efectivo que llega" rara
vez son el mismo número ni llegan el mismo día. El escenario conservador se construye **sin** la
venta.

## Separación patrimonio personal / empresarial

### Señales de mezcla, en orden de frecuencia

1. Gastos personales pagados con tarjeta o cuenta de la empresa, sin imputar a cuenta particular.
2. Ingresos personales (una renta, una venta particular) cobrados en la cuenta de la sociedad.
3. Una sola cuenta bancaria operando ambos mundos.
4. Activos personales usados como garantía de deuda societaria sin registro ni contraprestación.
5. Activos de la empresa en uso personal exclusivo (vehículo, inmueble) sin imputación.
6. Personal doméstico o servicios familiares liquidados por la empresa.

### Por qué importa acá

Tres consecuencias, en orden de gravedad práctica:

- **Distorsiona los dos análisis.** El gasto familiar aparece más bajo de lo que es y el resultado
  de la empresa también. Las dos fotos quedan mal y las decisiones se toman sobre ambas.
- **Erosiona la protección patrimonial.** La separación entre persona y sociedad depende, entre
  otras cosas, de que se comporten como cosas separadas.
- **Aparece en cualquier proceso de venta o incorporación de socios** como ajuste, y en ese momento
  se discute con menos margen del que había antes.

### Cómo detectarla en los registros

- Reconciliá el gasto familiar declarado contra el consumo real observable (tarjetas, débitos,
  transferencias). El hueco suele ser exactamente lo que paga la empresa.
- Revisá la cuenta particular del socio: movimientos frecuentes de montos chicos indican consumo
  personal imputado; montos grandes y esporádicos indican retiros.
- Buscá gastos que en el flujo familiar simplemente no aparecen (combustible, telefonía, seguros,
  viajes). Si no están, alguien más los paga.

**Cuando detectes mezcla, no la corrijas en silencio ni sigas calculando.** Decila primero,
cuantificala si podés, y aclará que hasta normalizarla el flujo familiar está subestimado en ese
monto. Es un hallazgo, no un detalle.
