# 05 — Métricas núcleo y reglas de decisión

## Las cinco métricas

Escribí siempre la fórmula antes del número.

### 1. Tasa de ahorro real en USD

```
tasa_ahorro = (Σ ingresos_USD − Σ gastos_USD) / Σ ingresos_USD
```
Cada flujo convertido al TC de su propia fecha (ver `01-marco-medicion.md`).

Lectura: es la única métrica de comportamiento del conjunto. Todo lo demás es stock o precio.
Medila en ventanas de 12 meses móviles, no mensuales: con ingreso irregular, un mes aislado no
dice nada.

**Trampa frecuente:** una tasa de ahorro que sube sin que haya cambiado nada del comportamiento
suele ser atraso cambiario, no ahorro. Contrastá contra la variación del TC real del período antes
de felicitar a nadie.

### 2. Runway familiar

```
runway_meses = activos_líquidos_USD / gasto_comprimido_mensual_USD
```

Solo cuentan como líquidos los activos convertibles en menos de 30 días sin castigo relevante. El
equity de la empresa no es líquido. Un inmueble no es líquido. Un plazo fijo a 90 días es líquido
con descuento; declaralo.

### 3. Ratio de rigidez

```
rigidez = gasto_fijo_familiar_USD / ingreso_mínimo_esperado_USD
```

El denominador es el **piso** del ingreso, no el promedio. Es la métrica que anticipa el estrés
antes de que aparezca:

- `< 0,5` — hay margen real de maniobra.
- `0,5 – 0,8` — funciona, pero un mal trimestre obliga a tocar el colchón.
- `> 0,8` — el gasto fijo se come el piso del ingreso. Cualquier compromiso nuevo es riesgo puro.
- `> 1` — la familia depende de que los meses buenos financien los malos. Es sostenible mientras
  la suerte acompañe.

### 4. Yield neto real por activo

Para un inmueble en alquiler:

```
renta_neta_anual = renta_bruta_anual
                 − expensas y gastos a cargo del propietario
                 − impuestos (inmobiliario, tasas, Ingresos Brutos si corresponde)
                 − mantenimiento (usá 5–8% de la renta bruta si no hay dato)
                 − vacancia esperada (usá 1 mes cada 24–36 según el mercado)
                 − comisiones e incobrabilidad

yield_neto = renta_neta_anual_USD / valor_de_mercado_USD
```

El valor de mercado, no el de compra ni el fiscal. Un yield calculado sobre el precio de compra de
hace ocho años no mide nada.

**Yield y apreciación son dos números separados.** Sumarlos en una sola cifra oculta que uno es
flujo disponible y el otro es papel.

**Alquileres en ARS con ajuste por índice (ICL, IPC, o el que fije el contrato):** el yield en USD
no es estable, oscila con el tipo de cambio real. La renta ajusta por un índice de precios locales
mientras el valor del inmueble se mide en dólares, y esas dos cosas se mueven distinto.

Cómo tratarlo:
1. Proyectá la renta en ARS según la fórmula de ajuste del contrato y su frecuencia.
2. Convertí cada cobro futuro al MEP proyectado **de esa fecha**, en tres escenarios de TC.
3. Mostrá el yield en USD como un **rango**, nunca como un número único.

Un contrato en dólares no tiene este problema, pero tiene otro: el riesgo de que el inquilino no
pueda sostener el pago si su ingreso es en pesos. Registralo como mayor probabilidad de vacancia,
no lo ignores.

### 5. Concentración

Por activo y por moneda:
```
concentración_i = valor_activo_i / PN_total
HHI = Σ (participación_i)²        # 1,0 = todo en un activo
```

Y la que más importa en este perfil, la **exposición efectiva a la empresa**:
```
exposición_empresa = % del PN en la empresa + % del ingreso familiar que viene de la empresa
```

Ver `06-interfaz-empresa.md`. Cuando esa suma pasa de 100 (por ejemplo 60% del patrimonio + 80%
del ingreso), diversificar el 40% restante es cosmética: el riesgo dominante no está ahí.

Por moneda, mostrá activos y pasivos juntos: un patrimonio "dolarizado" con deuda en pesos
indexada tiene un descalce que la foto por activos no muestra.

## Reglas de decisión bajo alta inflación

### Cuándo el ahorro en ARS destruye valor

Condición aritmética:
```
(1 + tasa_efectiva_período) < (1 + inflación_esperada_período)
```

Pero la condición aritmética no alcanza, porque hay dos monedas de referencia posibles. La regla
operativa es de **correspondencia de monedas**:

> El ahorro se guarda en la moneda del gasto que va a financiar, con el plazo del horizonte de ese
> gasto.

- Gasto en ARS dentro de 30–90 días (colegio, expensas, impuestos) → instrumento en ARS
  remunerado. Dolarizarlo agrega riesgo de tipo de cambio a un dinero que ya tiene destino.
- Gasto en USD, o a más de 12 meses, o sin destino asignado → USD. El peso no es reserva de valor
  a ese plazo.
- Gasto indexado (alquiler, cuota UVA) → instrumento indexado por el mismo índice si existe;
  si no, el que más se le parezca, declarando la diferencia como riesgo residual.

Lo que la regla evita: la decisión binaria "dolarizo todo o no dolarizo nada", que es donde se
pierde plata en las dos direcciones.

### Criterios de dolarización

Antes de mover, chequeá tres cosas:

1. **Horizonte del dinero.** Sin destino y sin fecha, es de largo plazo por defecto → USD.
2. **Nivel del tipo de cambio real.** Comprar dólares con TC real muy alto (después de un salto)
   tiene un costo de oportunidad distinto que con TC real bajo. No es timing de mercado: es evitar
   convertir todo el excedente de un año en el peor momento.
3. **Costo friccional.** Comisiones, parking, plazos de liquidación. Sobre montos chicos y
   operaciones frecuentes, se come una porción relevante.

**Nunca recomiendes el instrumento.** Describí las propiedades que el dinero necesita (plazo,
moneda, liquidez, riesgo de crédito, tratamiento impositivo) y dejá que la persona elija con su
asesor.

### Fondo de emergencia con ingreso irregular

La regla genérica de "3 a 6 meses" fue pensada para un sueldo estable. Acá no aplica. Dimensionalo:

```
FE = gasto_comprimido_mensual_USD × meses_de_la_peor_racha_observada × factor_correlación
```

- **Peor racha observada**: la seguidilla más larga de meses con ingreso por debajo del gasto
  comprimido, en los últimos 24–36 meses. Si no hay historia, usá 6 meses y marcalo como supuesto
  débil.
- **Factor de correlación**:
  - `1,0` si el ingreso viene de fuentes independientes entre sí.
  - `1,5` si el ingreso familiar depende mayormente de una sola empresa.
  - `2,0` si además el patrimonio principal es esa misma empresa **y** hay deuda personal
    garantizada con activos familiares.

La lógica del factor: cuando el ingreso se corta, si el activo principal es la misma empresa, ese
activo también vale menos justo en ese momento y no se puede vender para cubrir el hueco. Las dos
cosas fallan juntas. Un fondo dimensionado como si fueran independientes queda corto exactamente
cuando se lo necesita.

**Dónde vive el FE:** líquido, en la moneda del gasto comprimido (que suele ser mayormente ARS),
con una porción en USD proporcional a la exposición del gasto. Y fuera del alcance operativo de la
empresa: si está en la cuenta de la sociedad, no es un fondo de emergencia, es capital de trabajo.
