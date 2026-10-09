---
name: decisiones-tecnicas
description: "Antes de contratar, instalar o armar cualquier servicio técnico (poner una web o herramienta en internet, automatizar un proceso, guardar datos en una base, manejar claves, vigilar gastos, usar una IA externa con datos del cliente), aplicá los criterios de stack que ya se decidieron y se pagaron caros en otros lados. Lee primero la ficha y las cuentas del cliente y recomienda lo que ya paga antes de sumar servicios, con costo, riesgo y datos que salen a terceros. Usala cuando alguien diga 'quiero una web', 'quiero automatizar', 'dónde lo pongo', 'qué base de datos', 'qué herramienta uso', 'cuánto va a costar' o 'es seguro mandar esto a una IA'."
version: "0.1.0"
origen: "propia (criterios destilados de decisiones de infraestructura reales, genericizados)"
sync: si
---

# Decisiones técnicas — criterios, no recetas

Esta skill te da el **por qué** detrás de las elecciones de herramientas, para que no arranques de cero ni elijas por moda.
Una receta ("usá X") se vence en meses; un criterio ("elegí lo que ya pagás, poné tope de gasto el día 1") sigue sirviendo.
Por eso cada criterio trae el incidente o motivo que lo originó **y cuándo NO aplica** («siempre aplica» cuando no hay excepción).

**Son recomendaciones de peso alto: ya se analizaron y se pagaron en casos reales.** Decidís vos con lo que sabés de
este cliente, pero apartate de una recomendación solo con una razón concreta de su caso (su stack, su presupuesto, sus
datos), y decila en voz alta: «No sigo X porque <razón del cliente>». Sin esa razón, va la recomendación.

## Regla de oro
**Primero lo que el cliente ya paga. Recién después, un servicio nuevo.** Cada servicio nuevo es una cuenta más, una factura más,
una clave más y un lugar más adonde pueden salir datos. Si lo que ya tiene alcanza, usar eso es la respuesta correcta aunque sea menos moderno.

## Antes de recomendar nada (obligatorio, en este orden)
1. **Leé la ficha del cliente** (`CLAUDE.md` del proyecto, `clientes/<c>/CONTEXTO.md` o similar) y su inventario de cuentas
   (`CUENTAS.md` si existe). Buscá: suite de oficina (Google Workspace / Microsoft 365 / otra), plan contratado, sistemas que ya usa
   (gestión de tareas, contabilidad, ERP), nivel técnico de quien lo va a mantener, tarjeta/medios de pago, **qué datos maneja**
   (clientes, contratos, planos, personales).
2. **Si la ficha no lo dice, preguntá una sola vez, junto**, las pocas cosas que cambian la respuesta (suite, plan, quién mantiene, datos sensibles). No supongas.
3. **Mapeá el pedido a un área** (tabla de abajo) y abrí el `references/` de esa área. No recomiendes de memoria.
4. **Presentá 1 recomendación + 1 alternativa**, nunca un menú de seis. Con el formato de salida (más abajo).
5. **Verificá los precios** antes de dar cifras: cambian. Si no los verificaste en la fuente oficial en esta sesión, decí "precio a confirmar" y la fecha de tu última referencia.

## Áreas y dónde mirar
| El pedido toca… | Abrí | Criterio central en una línea |
|---|---|---|
| Poner una web o herramienta en internet | `references/alojar.md` | ¿Hace falta hosting? Primero lo que ya incluye su suite; si hay que sumar, tope de gasto el día 1 |
| Automatizar un proceso | `references/automatizar.md` | Lo que ya tiene (Apps Script / Power Automate) antes de plataformas nuevas; pocas piezas, una sola dueña |
| Guardar y consultar datos | `references/datos.md` | La planilla alcanza hasta que deja de alcanzar; no migrar por anticipado |
| Claves, publicar con seguridad, vigilar caídas | `references/seguridad.md` | Secretos por referencia; chequeo de seguridad antes de publicar; monitoreo avisa caídas, no gastos |
| Gastos que pueden dispararse | `references/costos.md` | Todo servicio que cobra por uso lleva tope duro el día 1 |
| Mandar datos a una IA externa | `references/ia-externa.md` | Decidir qué datos salen antes de elegir proveedor |

Si el pedido toca varias áreas ("web con formulario que guarda datos y manda mail"), recorré las áreas en ese orden: datos → alojar → automatizar → IA externa → seguridad → costos.

## Qué te ofrece la suite del cliente (mirá esto antes de sumar algo)
| Si el cliente tiene… | Ya incluye (verificá en su plan) | Sirve para |
|---|---|---|
| **Google Workspace** | Sheets, Forms, Docs, Drive, Sites, Apps Script, AppSheet (según plan), Gmail, Calendar | web informativa simple (Sites), formularios, planillas con lógica, avisos por mail, informes automáticos |
| **Microsoft 365** | Excel, Forms, SharePoint (sitios), Power Automate, Power Apps (según plan), Outlook, Teams | sitio interno, flujos entre mail/Teams/Excel, formularios, apps internas |
| Ninguna de las dos | Hay que elegir con `references/` | partir del costo fijo más bajo y sin nada que mantener |

"Según plan" importa: las licencias varían (algunas funciones de AppSheet o Power Apps piden un plan o complemento). Confirmalo en la consola de administración del cliente o en la página oficial antes de prometerlo.

## Formato de salida (siempre)
```
Pedido: <lo que pidió, en una línea>
Lo que ya tenés: <de la ficha/CUENTAS: qué cubre total o parcialmente>
Recomendación: <opción> — <por qué, en una frase>
  Costo: <fijo/mes, variable, o 0 extra> (fuente y fecha, o "a confirmar")
  Riesgo principal: <el que más duele si pasa>
  Datos que salen a terceros: <qué datos, a quién, o "ninguno: queda en tu suite">
  Quién lo cambia mañana: <persona y si necesita a Claude o a alguien técnico>
  Cuándo deja de servir / cómo salir: <señal concreta y si se pueden exportar los datos>
Alternativa: <opción> — <cuándo la elegiría en vez de la anterior>
Antes de arrancar: <tope de gasto / chequeo de seguridad / acceso restringido, lo que aplique>
```
Si el costo o los datos que salen no se pueden decir, **no recomiendes todavía**: averiguá primero.

## Lo que esta skill NO hace
- No contrata, no paga, no crea cuentas y no carga claves: eso lo hace el cliente; las claves nunca pasan por el chat. Vos preparás el paso a paso.
- No decide por el cliente cuando el dato sensible está en juego: mostrás qué sale y esperás su "sí".
- No promete cifras de precio ni de plan sin fuente. Dice "a confirmar".
- No reemplaza al consultor en lo caro o irreversible (migrar datos, cambiar de proveedor de mail, abrir puertos): lo marca "llevarlo a llamada".
- No sabe qué eligió otro cliente ni el negocio de nadie más: trabaja con la ficha de este cliente.

## Antes de usar esta skill — requisitos
| Necesita | Cómo verificar | Si falta, respondé |
|---|---|---|
| Ficha del cliente legible | Existe `CLAUDE.md` o `CONTEXTO.md` en la carpeta | "No encuentro la ficha. Contame suite de oficina, plan, quién mantiene lo técnico y qué datos sensibles manejás, y sigo" |
| Nada instalado | — | La skill es solo criterio: no ejecuta nada |
| Acceso a internet (opcional) | Poder consultar páginas oficiales | "No pude verificar precios hoy: te doy el criterio y marco los números como a confirmar" |

## Cómo se mantiene
Los criterios nacen de decisiones reales con su incidente (ver cada `references/`). Cuando aparece una decisión nueva con motivo
verificable, se agrega al área que corresponda con: decisión · motivo · cuándo NO aplica. Los precios no se guardan acá: se verifican cada vez.
