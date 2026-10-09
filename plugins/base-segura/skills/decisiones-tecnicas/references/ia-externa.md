# IA externa con datos del cliente

## Principio
**Antes de elegir proveedor, decidí qué datos pueden salir.** El orden correcto es: clasificar los datos → elegir el nivel de proveedor → recién ahí el modelo.
Todo prompt, imagen o archivo que se manda a una IA de terceros sale de la oficina y puede quedar en sus registros.

## Clasificación rápida de datos
| Tipo | Ejemplos | Puede salir a una IA externa |
|---|---|---|
| **Público / ya publicado** | Folletos, web, normativa pública | Sí |
| **Interno no sensible** | Borradores sin nombres, plantillas | Sí, en planes que no entrenen con los datos |
| **Confidencial del negocio** | Presupuestos, precios, contratos, planos de clientes | Solo con **acuerdo/política que lo permita** y el "sí" explícito del cliente; mejor, no |
| **Personal o regulado** | Datos de personas, financieros, claves | **No**, salvo proveedor con garantías contractuales verificadas y decisión del dueño |

## Decisiones, motivo y cuándo NO aplican
| Decisión | Motivo | Cuándo NO aplica |
|---|---|---|
| **Los planes gratuitos o de consumo pueden entrenar con lo que mandás**: nunca datos de clientes ahí | Es la condición habitual de los planes sin costo, y está escrita en sus términos | Un plan con la opción de no entrenar activada y verificada |
| **Primero la IA que el cliente ya paga, pero verificando su tipo**: plan de consumo (individual) o de empresa (equipo/organización), y la opción de entrenamiento | La regla de oro vale para la IA, pero «ya lo pagamos» no dice qué pasa con los datos. Los planes de empresa suelen excluir el entrenamiento por contrato; los individuales, por una opción que hay que revisar | Datos públicos |
| **Verificá el tipo de cuenta antes de mandar a comprar un plan de IA** | Los planes de IA de consumo de un proveedor no se venden a cuentas de su suite empresarial; mandar a abrir una cuenta personal aparte rompe el trabajo con los archivos de la empresa. Pasó dos veces antes de verificarlo | Cliente sin suite, con cuenta personal |
| **Un gateway que reúne varios modelos (una clave, muchos proveedores) = un tercero más**: prompts e imágenes pasan por él y por el modelo final | Configurar privacidad (sin proveedores que entrenen), retención cero cuando el modelo la ofrece, tope mensual en la clave | Uso con datos públicos |
| **Herramientas no oficiales que usan las cookies o sesión de una cuenta**: solo con un protocolo explícito y cuenta con reglas | El riesgo es la *llave*: si se filtra, abre toda la cuenta de Google. Versión fija, nunca extraer cookies del navegador | Cuando existe una vía oficial equivalente: usar la oficial |
| **Mandar lo mínimo**: recortar, anonimizar o resumir antes de enviar | Menos datos fuera = menos daño si algo se filtra | Cuando el valor está justo en el detalle y el cliente lo autorizó |
| **Elegir el proveedor desde un radar actualizado, no de memoria** | Los modelos y cupos cambian cada pocas semanas | Siempre aplica |
| **IA dentro de la suite del cliente (Gemini en Workspace, Copilot en Microsoft 365) tiene reglas de datos propias**: leerlas antes de asumir que "queda adentro" | Que el producto esté dentro de la suite no significa que el contrato sea el mismo que el del resto | Plan empresa con acuerdo de datos verificado |

## Qué escribir en la recomendación
`Datos que salen: <qué tipo, de la tabla> → <a quién> · Entrena con los datos: <sí/no/a confirmar> · Retención: <...> · Se necesita el sí del cliente: <sí/no>`
Si el dato es confidencial o personal: **frená y pedí la decisión del dueño** antes de seguir.
