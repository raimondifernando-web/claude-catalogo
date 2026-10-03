# 03 — Flujo: ingresos y gastos

## Ingresos por origen

Un ingreso no se define por su monto sino por su **confiabilidad**. Registrá cada origen con
estas cinco columnas, porque el monto solo no permite decidir nada:

| Origen | Monto esperado | Rango observado (mín–máx) | Moneda | Frecuencia | Prob. de interrupción |
|---|---|---|---|---|---|

Perfiles típicos:

- **Sueldo en relación de dependencia** — baja volatilidad, alta previsibilidad, ARS con ajustes
  paritarios retrasados respecto de la inflación. Es el único ingreso que se puede tratar como
  piso.
- **Retiro de socio** — volatilidad media a alta. Depende del caja de la empresa y de una política
  que puede cambiar. Ver `06-interfaz-empresa.md`: la naturaleza contable del retiro cambia si es
  ingreso o no.
- **Dividendos** — volatilidad alta y frecuencia discreta (una o dos veces al año, o ninguna).
  Nunca los prorratees a mensual como si fueran sueldo: eso convierte un evento en una expectativa.
- **Rentas** — volatilidad media. Ojo con vacancia, mora e incobrabilidad: el ingreso bruto del
  contrato no es el ingreso esperado. Ver el cálculo de yield en `05-metricas-y-decision.md`.
- **Extraordinarios** (venta de un activo, un bonus, una herencia) — **no entran al flujo
  recurrente**. Van en una línea separada, abajo, y financian objetivos puntuales, no nivel de
  vida.

**El número que importa no es el promedio: es el piso.** Para todo lo que sea gasto fijo,
compromiso o cuota, trabajá contra el **ingreso mínimo esperado** — el percentil bajo de la
distribución, o directamente el peor mes de los últimos doce si no hay mejor dato. El promedio
sirve para proyectar ahorro; el piso sirve para decidir compromisos.

## Gastos: tres ejes simultáneos

Cada gasto lleva **tres etiquetas al mismo tiempo**. No se duplica el gasto: se lo etiqueta tres
veces. Las tres responden preguntas distintas y las tres se necesitan.

**Eje 1 — Naturaleza** (¿puedo dejar de pagarlo?)
- `fijo`: comprometido, no se puede bajar en el corto plazo sin romper algo (alquiler, colegio,
  prepaga, cuotas).
- `variable`: necesario pero de monto ajustable (supermercado, combustible, servicios).
- `discrecional`: se puede suspender sin consecuencia estructural (salidas, viajes, suscripciones).

Esta clasificación es la que define el **gasto comprimido**: fijo + un variable mínimo. Es la base
del fondo de emergencia y del runway.

**Eje 2 — Moneda de exposición** (¿qué le pasa a este gasto si se mueve el TC o el IPC?)
- `ARS`: sigue la inflación local con rezago (servicios regulados, salarios de personal doméstico).
- `USD`: nominado o atado al dólar (viajes, tecnología, algunos alquileres, importados).
- `indexado`: ajusta por índice contractual — ICL, IPC, UVA (alquileres, cuotas hipotecarias,
  algunos colegios).

Este eje es el que muestra por qué "gasté lo mismo" no significa nada: si el 40% del gasto está
atado al dólar, el gasto en USD es estable y en ARS explota, o al revés.

**Eje 3 — Titularidad** (¿de quién es este gasto?)
- `individual`: de A o de B, identificando cuál.
- `compartido`: del hogar, asignable según el criterio acordado (ver `04-dimension-familiar.md`).
- `dependientes`: atribuible a hijos u otras personas a cargo.

Este eje es el que permite una conversación de pareja con datos en vez de con percepciones.

## Ejemplo de codificación

| Gasto | Naturaleza | Moneda | Titularidad |
|---|---|---|---|
| Colegio | fijo | indexado | dependientes |
| Alquiler de la oficina personal | fijo | indexado | individual (A) |
| Supermercado | variable | ARS | compartido |
| Prepaga familiar | fijo | ARS (con aumentos > IPC por edad) | compartido |
| Suscripciones de streaming | discrecional | USD | compartido |
| Viaje anual | discrecional | USD | compartido |
| Terapia de A | fijo | ARS | individual (A) |

## Construcción del flujo mensual

```
flujo_neto_USD = Σ ingresos_USD (cada uno al TC de su fecha)
               − Σ gastos_USD (cada uno al TC de su fecha)
```

Y de ahí:
```
tasa_ahorro_real = flujo_neto_USD / Σ ingresos_USD
```

**Control de consistencia obligatorio:** el ahorro declarado tiene que coincidir con la variación
del saldo de activos líquidos del período, ajustada por movimientos patrimoniales.

```
Δ activos_líquidos_USD ≈ flujo_neto_USD ± movimientos no operativos
```

Si no cierra, hay gasto no registrado (lo habitual), un ingreso omitido, o un movimiento
patrimonial confundido con flujo (típicamente una devolución de aportes contada como ingreso).
**Decilo antes de presentar cualquier resultado.** Un flujo que no reconcilia contra saldos es un
flujo inventado, por prolijo que se vea.

## Estacionalidad

En Argentina hay meses estructuralmente caros: marzo (inicio escolar), julio y diciembre (medio
aguinaldo, fiestas, vacaciones), enero (vacaciones). Y el ingreso del emprendedor suele tener su
propia estacionalidad, muchas veces desfasada de la del gasto.

Un flujo mensual promedio oculta esto por completo. Cuando proyectes un año, hacelo mes a mes, o
al menos marcá los meses críticos y verificá que haya liquidez para cubrirlos.
