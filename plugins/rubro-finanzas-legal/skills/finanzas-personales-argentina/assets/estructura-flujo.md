# Estructura canónica — Flujo mensual

## Hoja de parámetros (referenciada por todas las fórmulas)

| Mes | MEP promedio | MEP día de cobro | MEP día de pago tarjeta | IPC mensual |
|---|---|---|---|---|

Ningún tipo de cambio hardcodeado dentro del cálculo: siempre referencia a esta hoja.

## Ingresos

| Fecha | Origen | Tipo | Monto ARS | Monto USD | MEP usado | Recurrente | Notas |
|---|---|---|---|---|---|---|---|

- **Origen**: sueldo / retiro de socio / dividendo / renta / extraordinario
- **Tipo** (para retiros): sueldo / adelanto de utilidades / devolución de aportes / dividendo
  → ver `references/06-interfaz-empresa.md`. La devolución de aportes **no es ingreso**.
- **Recurrente**: sí / no. Los extraordinarios no entran al flujo base.

```
monto_usd = monto_ars / mep_de_la_fecha
```

## Perfil de volatilidad del ingreso (se recalcula cada 6 meses)

| Origen | Promedio 12m USD | Mínimo 12m | Máximo 12m | Meses en cero | Prob. de interrupción |
|---|---|---|---|---|---|

El **ingreso mínimo esperado** sale de acá y es el denominador del ratio de rigidez.

## Gastos

| Fecha | Concepto | Monto ARS | Monto USD | MEP usado | Naturaleza | Moneda expos. | Titularidad | Pagó | Corresponde a |
|---|---|---|---|---|---|---|---|---|---|

- **Naturaleza**: fijo / variable / discrecional
- **Moneda de exposición**: ARS / USD / indexado
- **Titularidad**: individual (A o B) / compartido / dependientes
- **Pagó** vs **Corresponde a**: dos columnas distintas. La diferencia acumulada es el saldo entre
  las partes.

## Resumen del mes

| Concepto | USD | Fórmula |
|---|---|---|
| Ingresos recurrentes | | Σ ingresos con recurrente = sí |
| Ingresos extraordinarios | | Σ ingresos con recurrente = no |
| Gasto fijo | | Σ gastos naturaleza = fijo |
| Gasto variable | | Σ gastos naturaleza = variable |
| Gasto discrecional | | Σ gastos naturaleza = discrecional |
| **Gasto comprimido** | | fijo + variable mínimo |
| **Flujo neto** | | ingresos − gastos |
| **Tasa de ahorro** | | flujo neto / ingresos |

## Reconciliación obligatoria

| Concepto | USD |
|---|---|
| Saldo líquido inicial | |
| + Flujo neto del período | |
| ± Movimientos patrimoniales (compra/venta de activos, devolución de aportes) | |
| = Saldo líquido esperado | |
| Saldo líquido real | |
| **Diferencia** | |

Si la diferencia no es cercana a cero, hay gasto no registrado, ingreso omitido o un movimiento
patrimonial confundido con flujo. **Se reporta antes que cualquier otro resultado.**

## Bloques CSV

```csv
fecha,origen,tipo,monto_ars,monto_usd,mep,recurrente,notas
```
```csv
fecha,concepto,monto_ars,monto_usd,mep,naturaleza,moneda_exposicion,titularidad,pago,corresponde_a
```
