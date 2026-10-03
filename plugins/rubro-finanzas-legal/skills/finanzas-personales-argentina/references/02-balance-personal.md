# 02 — Balance personal y familiar

El balance responde una pregunta: **cuánto vale lo que tengo, en dólares, hoy, si tuviera que
tomar una decisión**. No es un inventario de orgullo ni una foto contable.

## Las dos dimensiones de clasificación

Cada activo se clasifica simultáneamente en dos ejes. La matriz que sale es lo que muestra la
verdadera situación:

|  | **Productivo** (genera flujo) | **Improductivo** (no genera flujo) |
|---|---|---|
| **Líquido** (convertible en < 30 días sin castigo) | Plazo fijo, fondo money market, bonos con mercado | Dólares en efectivo o caja de ahorro |
| **Ilíquido** (> 30 días, o castigo relevante) | Inmueble alquilado, equity en empresa que distribuye | Vivienda propia, auto, obras, equipamiento |

Lecturas típicas de esta matriz:

- Mucho **ilíquido improductivo** con poco líquido: patrimonio alto y fragilidad alta. Se ve
  próspero y no puede afrontar tres meses malos.
- Todo en **ilíquido productivo**: el flujo depende de que los activos sigan funcionando. Un
  inquilino que se va o una empresa que deja de distribuir corta el ingreso y no hay colchón.
- La **vivienda propia es improductiva** aunque ahorre un alquiler. Ese ahorro se registra como
  menor gasto en el flujo, no como renta del activo. Contarlo de las dos formas es doble conteo.

## Pasivos

Clasificá por moneda y por indexación, porque determinan quién gana con la inflación:

- **ARS a tasa fija**: la inflación te lo licúa. Es un activo disfrazado de deuda mientras la
  tasa real sea negativa.
- **ARS indexado (UVA, ICL, IPC)**: no se licúa. Se comporta como deuda real.
- **USD**: el riesgo es el tipo de cambio. Si el ingreso es en ARS, un salto cambiario multiplica
  la carga en términos de tu capacidad de pago.

Para cada pasivo registrá: saldo, moneda, indexación, tasa, cuota mensual, plazo remanente, y
**qué activo lo garantiza**. Esa última columna es la que muestra el riesgo real: una deuda
garantizada con la vivienda familiar no es equivalente a una sin garantía, aunque el monto sea
igual.

## Patrimonio neto

```
PN_USD = Σ activos_USD − Σ pasivos_USD
```

Presentalo siempre con su composición, no solo el total. El total dice poco; la composición dice
todo.

## Individual vs común

En una pareja o familia hay tres masas patrimoniales, y conviene mostrarlas separadas antes de
consolidar:

1. Patrimonio individual de A
2. Patrimonio individual de B
3. Patrimonio común

Consolidar de entrada oculta desequilibrios que después aparecen en decisiones concretas (quién
aporta cuánto a un objetivo, qué pasa ante una separación o un fallecimiento). Mostrá la apertura
y después el consolidado.

El **régimen patrimonial del matrimonio** cambia la lectura: en Argentina el Código Civil y
Comercial admite comunidad de ganancias (el régimen por defecto) o separación de bienes por
convención prematrimonial. Cuál rige determina qué es común y qué no. No des asesoramiento
legal — no sos abogado — pero preguntá cuál es el régimen, porque sin ese dato el balance
familiar está mal armado. Si la persona no lo sabe, marcalo como dato faltante y sugerí
consultarlo con un profesional.

## Equity en empresas propias

Es el punto donde más se rompe un balance personal, porque es el activo más grande y el peor
medido.

**Reglas duras:**

- **Nunca a valor libro.** El patrimonio contable de una empresa no dice nada sobre lo que vale.
- **Nunca al valor de venta esperado sin descuento.** Y si hay un proceso de venta abierto y no
  cerrado, no entra al balance como si estuviera cerrado.
- **Esta skill no valúa la empresa.** La valuación es input externo (`ma-apparel-argentina`
  hace eso). Acá recibís un valor y lo ajustás para que sea comparable con el resto del
  patrimonio personal.

**El ajuste:**

```
valor_en_balance = valuación_100% × participación × (1 − DLOM) × (1 − DLOC)
```

- **DLOM** (descuento por iliquidez): rango habitual **20–35%**. Refleja que no hay mercado, que
  vender lleva meses o años y que el resultado es incierto. Usá el extremo alto si no hay proceso
  de venta en curso ni comprador identificado.
- **DLOC** (descuento por falta de control): rango habitual **10–30%**, aplicable **solo si la
  participación es minoritaria o no permite decidir la distribución de utilidades**. Si la persona
  controla la empresa, no corresponde.

Los rangos son órdenes de magnitud, no verdades: declaralos como supuesto y mostrá el patrimonio
con el descuento alto y el bajo. La diferencia entre ambos suele ser el dato más informativo del
balance.

**Presentación obligatoria:** mostrá el PN con y sin el equity de la empresa. Son dos números que
responden dos preguntas distintas: "cuánto valgo" y "con cuánto puedo contar". Si la persona solo
ve el primero, va a tomar decisiones de gasto contra un activo que no puede vender.

## Escrituras pendientes y otros activos de titularidad dudosa

Un inmueble con boleto y sin escritura, un aporte a un emprendimiento sin instrumentar, un
préstamo a un familiar sin documento: registralos, pero en una sección aparte con su
probabilidad de recupero declarada. No los sumes al PN principal sin marca.
