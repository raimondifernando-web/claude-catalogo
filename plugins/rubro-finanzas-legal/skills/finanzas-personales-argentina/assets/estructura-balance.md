# Estructura canónica — Balance personal y familiar

Campos mínimos. La presentación se adapta al destino (ver `references/08-destino-de-datos.md`);
los campos no.

## Parámetros del corte

| Parámetro | Valor | Fuente |
|---|---|---|
| Fecha de corte | | |
| MEP a la fecha | | |
| Régimen patrimonial | comunidad / separación / no aplica | |

## Activos

| Activo | Titular | Valor ARS | Valor USD | Liquidez | Productivo | Genera (USD/año) | Notas |
|---|---|---|---|---|---|---|---|

- **Titular**: A / B / común
- **Liquidez**: líquido (< 30 días sin castigo) / ilíquido
- **Productivo**: sí / no
- **Genera**: flujo anual neto en USD, 0 si es improductivo

## Equity en empresas propias (sección separada)

| Empresa | Valuación 100% (USD) | % participación | ¿Controla distribución? | DLOM | DLOC | Valor en balance |
|---|---|---|---|---|---|---|

```
valor_en_balance = valuación_100% × participación × (1 − DLOM) × (1 − DLOC)
```
DLOM 20–35%. DLOC 10–30%, solo si NO controla. Origen de la valuación, declarado.

## Pasivos

| Pasivo | Titular | Saldo USD | Moneda | Indexación | Tasa | Cuota mensual USD | Garantía |
|---|---|---|---|---|---|---|---|

## Activos de titularidad o cobrabilidad dudosa (no suman al PN principal)

| Concepto | Valor nominal USD | Prob. de recupero | Valor esperado | Notas |
|---|---|---|---|---|

## Resultado

| Concepto | A | B | Común | Total |
|---|---|---|---|---|
| Activos líquidos | | | | |
| Activos ilíquidos (sin empresa) | | | | |
| Equity en empresas | | | | |
| **Total activos** | | | | |
| Pasivos | | | | |
| **Patrimonio neto** | | | | |
| **PN sin equity en empresas** | | | | |

## Indicadores del corte

| Indicador | Fórmula | Valor |
|---|---|---|
| % líquido | líquidos / activos totales | |
| % en empresa | equity / PN | |
| Exposición efectiva a la empresa | % PN empresa + % ingreso empresa | |
| Concentración por moneda | activos y pasivos por moneda | |
| HHI por activo | Σ (participación_i)² | |

## Bloque CSV

```csv
activo,titular,valor_ars,valor_usd,liquidez,productivo,genera_usd_anual,notas
```
```csv
pasivo,titular,saldo_usd,moneda,indexacion,tasa,cuota_mensual_usd,garantia
```
