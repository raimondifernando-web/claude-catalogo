# 04 — Dimensión familiar

Una familia no es un agente único con una función de utilidad. Son dos o más personas con
historias distintas con el dinero, tolerancias al riesgo distintas y objetivos que compiten por
el mismo flujo. Un análisis que las promedia produce números correctos y decisiones que no se
sostienen.

## Horizontes de gasto asociados a hijos

Los gastos de hijos son la categoría más previsible del presupuesto familiar y la peor provisionada,
porque son grandes, discretos y lejanos: se ven venir durante años y llegan igual de golpe.

Tres familias de horizonte:

| Tipo | Ejemplos | Horizonte | Moneda del gasto |
|---|---|---|---|
| **Recurrente creciente** | Colegio, actividades, ropa | Mensual, sube por escalón etario | Indexado |
| **Escalón previsible** | Cambio de nivel escolar, universidad, primer auto | 3–15 años | Indexado o USD |
| **Contingente** | Salud, tratamientos, apoyo escolar | Impredecible en timing, acotado en monto | ARS / USD |

**Cómo se provisionan:** un objetivo de gasto futuro necesita tres definiciones antes de cualquier
número — **monto** (en la moneda en que se va a pagar), **fecha**, y **quién lo financia**.

```
aporte_mensual = monto_objetivo_USD / meses_hasta_la_fecha
```

Esa es la versión sin rendimiento, y es la correcta para arrancar: agregarle rendimiento esperado
es una forma elegante de aportar menos hoy contra un supuesto que puede no cumplirse. Si querés
mostrar el efecto del rendimiento, mostralo como escenario aparte, no como base.

**La moneda de la provisión sigue a la moneda del gasto**, no a la preferencia de quien ahorra.
Una universidad que se paga en pesos indexados no se provisiona en dólares sin asumir riesgo de
tipo de cambio; una maestría en el exterior sí.

## Gastos compartidos: criterios de asignación

Hay tres criterios y ninguno es objetivamente correcto. El daño no lo hace elegir mal: lo hace no
haber elegido, porque entonces cada uno asume el suyo en silencio y la discusión aparece meses
después disfrazada de otra cosa.

| Criterio | Cómo funciona | Cuándo tiene sentido | Qué tensiona |
|---|---|---|---|
| **Mitades** | 50/50 sin importar el ingreso | Ingresos similares | Con ingresos dispares, el de menor ingreso queda sin margen de ahorro propio |
| **Proporcional al ingreso** | Cada uno aporta el mismo % de su ingreso | Ingresos dispares | Si un ingreso es volátil, el aporte varía mes a mes; hay que definir contra qué ingreso se calcula |
| **Por uso** | Cada uno paga lo que consume | Convivencia con economías separadas | Alto costo de administración; los gastos de hijos y de hogar no se dejan asignar |

**Lo que hay que registrar siempre, sea cual sea el criterio:** quién **pagó** y a quién le
**corresponde**. Son dos columnas distintas. La diferencia acumulada entre ambas es el saldo entre
las partes, y explicitarlo evita que el desequilibrio se convierta en resentimiento sin datos.

Cuando el ingreso de uno es volátil (retiros de socio), definí contra qué se calcula la proporción:
el ingreso del mes hace que el aporte salte, el ingreso mínimo esperado da estabilidad y genera
excedente a repartir después. La segunda opción suele funcionar mejor, pero es una decisión de la
pareja, no tuya.

## Objetivos conjuntos vs individuales

Armá siempre esta tabla antes de recomendar nada:

| Objetivo | Titular | Monto (USD) | Fecha | Prioridad de A | Prioridad de B |
|---|---|---|---|---|---|

Cuando dos objetivos compiten por el mismo flujo, **no elijas por ellos**. Mostrá el costo de
oportunidad explícito:

> "Con un excedente de USD 1.200/mes: si priorizan el anticipo de la casa, llegan en 26 meses y
> el fondo de estudios de Tomi queda en cero. Si reparten 60/40, la casa pasa a 43 meses y el
> fondo llega a USD 5.800. Si priorizan el fondo, la casa sale del horizonte de 5 años."

Tres opciones, tres consecuencias, ninguna recomendación. La decisión es de ellos; el aporte tuyo
es hacer visible el trade-off que estaba implícito.

Una tensión frecuente y difícil: uno de los dos tiene la mayor parte de su patrimonio en una
empresa propia y quiere reinvertir; el otro necesita previsibilidad. No es un desacuerdo sobre
números, es un desacuerdo sobre riesgo. Nombralo así — ayuda más que cualquier cálculo.

## Cobertura ante contingencias

La pregunta concreta: **si mañana se interrumpe el ingreso principal, ¿cuánto dura la familia sin
cambiar de vida, y cuánto sin romperse?**

Dos números, no uno:

```
runway_sin_cambios  = activos_líquidos_USD / gasto_total_mensual_USD
runway_comprimido   = activos_líquidos_USD / gasto_comprimido_mensual_USD
```

donde `gasto_comprimido = fijo + variable mínimo` (ver `03-flujo-y-gastos.md`).

Y una tercera pieza que casi nunca está: **el orden de compresión**. Qué se suspende primero,
segundo y tercero, decidido en frío. Una familia que ya discutió el orden ejecuta en dos semanas;
una que no, pierde dos meses discutiendo mientras el colchón se consume.

Revisá también qué pasivos tienen cuota fija que no se puede comprimir y qué garantías están
comprometidas: ahí es donde una interrupción de ingreso se transforma en pérdida patrimonial.

Si hay dependientes, la contingencia incluye el caso de fallecimiento o incapacidad del proveedor
principal. Esto excede lo financiero (hay componentes legales y de seguros), pero **el flujo
familiar sin ese ingreso es calculable y hay que calcularlo**. Presentarlo con sobriedad, sin
dramatismo, como un número más.

## Cómo presentar los números para una conversación de pareja

Un informe para análisis individual y uno para una conversación de pareja no se parecen. El
segundo tiene que sostener una charla difícil sin que nadie quede en posición de acusado.

Reglas:

1. **Todo en USD y en montos redondos.** Nadie discute bien con seis cifras significativas.
2. **Sin jerga.** "Cuánto nos queda por mes" y no "flujo neto operativo".
3. **Una tabla por decisión**, no un tablero completo. El tablero es para vos; la tabla es para
   ellos.
4. **Separá visualmente lo que sabemos de lo que suponemos.** Gran parte de las discusiones de
   pareja sobre dinero son en realidad discusiones sobre supuestos que cada uno tenía distintos y
   nunca dijo.
5. **Mostrá el trade-off, no el veredicto.** Tres opciones con consecuencias, no una recomendación.
6. **Nunca atribuyas el desvío a una persona.** "El gasto discrecional creció 30%" y no "vos
   gastaste 30% más". El dato es el mismo; la conversación que habilita, no.
7. **Cerrá con preguntas abiertas.** "¿Qué querríamos poder hacer dentro de tres años que hoy no
   podemos?" mueve más que cualquier tabla.

Ver `assets/plantilla-revision-pareja.md` para la estructura de reunión.
