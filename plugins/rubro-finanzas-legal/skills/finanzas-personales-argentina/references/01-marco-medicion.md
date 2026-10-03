# 01 — Marco de medición

## La unidad de cuenta es el USD MEP

Toda cifra patrimonial y todo flujo se expresa en dólar MEP. El peso sirve para operar; no sirve
para medir, porque una unidad que pierde valor no puede ser la vara con la que medís si ganaste.

Por qué MEP y no oficial ni blue: el MEP es el tipo de cambio al que la persona efectivamente
puede convertir su excedente por vía legal y bancarizada. Es el precio real de la decisión de
ahorro. El oficial no está disponible para atesoramiento sin restricciones, y el informal no es
la referencia de quien opera con cuenta bancaria y comprobantes.

Si la persona opera con otro tipo de cambio (CCL porque el destino es una cuenta del exterior,
por ejemplo), usá ese, pero declaralo como supuesto y mantenelo constante en todo el análisis.

## Conversión de flujos: al tipo de cambio del momento del flujo

```
flujo_USD = flujo_ARS / MEP_de_la_fecha_del_flujo
```

Nunca al promedio del período. La razón es estructural, no una preferencia estética: los ingresos
y los gastos no están distribuidos igual dentro del mes. Un retiro que entra el día 3 y un gasto
de tarjeta que se paga el día 28 enfrentan tipos de cambio distintos, y con devaluación mensual
de 3–8% la diferencia entre convertir al TC real y al promedio es del mismo orden que la tasa de
ahorro que estás tratando de medir. El error se come el resultado.

Cuando la persona te da un total mensual sin desagregar por fecha, decíselo: el número va a tener
un error del orden de la mitad de la variación mensual del TC. Si igual hay que avanzar, usá el
TC de la fecha modal del flujo (día de cobro del ingreso, día de vencimiento de la tarjeta) y
declaralo como supuesto.

Para stocks (saldos, valuaciones de activos) se usa el TC de la fecha de corte, no el de cada
movimiento.

## Las tres tasas de rendimiento y cuándo usar cada una

Son tres números distintos que responden tres preguntas distintas. Mezclarlos es el error más
frecuente y el más caro.

**Nominal en ARS** — cuántos pesos más tengo.
```
r_nominal = (valor_final_ARS / valor_inicial_ARS) − 1
```
Solo sirve para comparar contra otra tasa nominal del mismo período. Nunca como conclusión.

**Real en ARS** — cuánto más puedo comprar en Argentina.
```
r_real_ars = (1 + r_nominal) / (1 + inflación_período) − 1
```
Es la respuesta correcta cuando el dinero se va a gastar en pesos, en el país, en el corto plazo:
un colegio, un alquiler en ARS, el supermercado.

**Real en USD** — cuánto más valgo medido en la unidad de reserva.
```
r_real_usd = (valor_final_ARS / MEP_final) / (valor_inicial_ARS / MEP_inicial) − 1
```
Es la respuesta correcta para patrimonio, ahorro de largo plazo y cualquier gasto futuro en
dólares. Es la métrica por defecto de esta skill.

Para horizontes mayores a un año, descontá además la inflación de Estados Unidos, o el "real en
USD" sigue siendo nominal:
```
r_real_usd_deflactado = (1 + r_real_usd) / (1 + inflación_USA_período) − 1
```

## Por qué real ARS y real USD no coinciden

Porque el IPC y el MEP no se mueven juntos. Cuando el tipo de cambio real se atrasa —el MEP sube
menos que los precios— el rendimiento medido en dólares parece extraordinario y el medido en
pesos es mediocre. Cuando se corrige, pasa lo inverso, de golpe.

La consecuencia práctica: un período corto de atraso cambiario produce tasas de ahorro en USD
espectaculares que no son ahorro sino precio relativo. Cuando midas un período donde el TC real
se movió fuerte, decilo. La lectura honesta es "esto es en parte precio relativo, no
necesariamente comportamiento".

Regla de presentación: si mostrás rendimiento, mostrá las tres columnas o aclarás cuál estás
usando. Nunca una tabla con algunas filas en nominal ARS y otras en real USD.

## Fuentes y su retraso

- **IPC INDEC**: se publica alrededor de mediados del mes siguiente. Para el mes en curso no hay
  dato: usá una proyección declarada como supuesto, o relevamientos privados aclarando la fuente.
- **MEP**: dato diario de mercado. Para fechas pasadas, el de la fecha; para proyecciones,
  escenario declarado.
- **Inflación de EE.UU. (CPI)**: relevante solo en horizontes plurianuales.

Cuando uses un dato que no tenés a mano y no podés buscar, escribí el placeholder visible
(`[IPC julio 2026 = X%]`) en vez de inventar el valor. Un hueco marcado es corregible; un número
inventado, no.
