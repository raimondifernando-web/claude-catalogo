# Automatizar un proceso

## Árbol de decisión
1. **¿El proceso se puede eliminar o simplificar?** Automatizar un proceso malo lo hace malo más rápido. Preguntá primero para qué existe cada paso.
2. **¿Vive dentro de la suite del cliente?**
   - Google Workspace: **Apps Script** (disparadores por hora o por evento sobre Sheets/Gmail/Calendar/Drive), **AppSheet** para formularios con lógica. 0 extra, los datos no salen de la suite.
   - Microsoft 365: **Power Automate** (flujos entre Outlook/Teams/Excel/SharePoint) y Power Apps. Confirmar que los conectores necesarios no sean "premium" en su plan.
3. **¿Cruza sistemas que la suite no puede leer o escribir bien?** Un sistema externo con una API simple (ej. leer tareas) todavía entra en Apps Script / Power Automate. Pasá a una plataforma de automatización (n8n, Make, Zapier) cuando hay **varios** sistemas externos, conectores listos que ahorran mucho código, o mensajería (WhatsApp). Elegí **una sola** y no mezcles. Entre n8n, Make y Zapier no hay un motivo probado para preferir una: sin evidencia, elegí la que el cliente ya usa o conoce; si no usa ninguna, la que tenga los conectores que necesita y el costo más bajo para su volumen.
4. **¿Lleva lógica pesada o procesamiento de archivos?** → un script chico en un lugar con dueño y registro, no una cadena de diez pasos visuales.

## Decisiones, motivo y cuándo NO aplican
| Decisión | Motivo | Cuándo NO aplica |
|---|---|---|
| **Una plataforma de automatización como centro, no varias** | Cada plataforma extra es otra cuenta, otra factura, otras claves y otro lugar donde buscar qué falló. Al elegir, compará precio por volumen de ejecuciones, si tiene versión autoalojada y qué conectores hacen falta | Si el cliente ya tiene un flujo funcionando en otra plataforma: no migrar por prolijidad |
| **Lo que se puede resolver con la suite, se resuelve ahí** | 0 costo extra, 0 claves nuevas, 0 datos fuera | Cuando el conector que falta no existe en la suite o es premium y más caro que la alternativa |
| **Versión fija en las herramientas de terceros** (no "la última" en cada arranque) | Una herramienta que se actualiza sola sin revisión puede cambiar de comportamiento o traer código nuevo sin que nadie lo mire | Servicios en la nube que el proveedor actualiza sí o sí (ahí compensás con monitoreo) |
| **Todo flujo que escribe en un sistema del negocio pide confirmación humana al principio** | Un flujo que escribe solo en la lista de clientes, en facturación o en publicidades puede romper datos a escala antes de que alguien lo note | Flujos que solo leen y arman un informe: ahí se puede dejar correr |
| **Tareas repetidas con cupo medible: vigilar el gasto** | Los bucles que corren solos gastan cupo o créditos sin avisar | Si el costo por vuelta es nulo y no hay tope que cuidar |
| **Claves dentro de Apps Script: en las propiedades del script, con el menor alcance posible** | Apps Script no tiene un gestor de secretos: cualquiera con permiso de edición del script puede leerlas | Flujos sin claves externas |

## Costo, riesgo y datos que salen (completar al recomendar)
| Opción | Costo | Riesgo principal | Datos que salen |
|---|---|---|---|
| Apps Script / AppSheet / Power Automate | 0 extra (confirmar plan) | Quien lo hizo se va y nadie lo entiende → documentar | Ninguno (suite) |
| Plataforma de automatización en la nube | cuota mensual por volumen | Datos pasan por un tercero; claves guardadas en la plataforma | Los datos que fluyen por cada paso |
| Autoalojada | servidor fijo + mantenimiento | Nadie la parchea | Quedan en tu servidor |

Siempre pedí: **qué dispara el flujo, qué escribe, qué pasa si falla (quién se entera) y quién lo mantiene.** Un flujo sin quien se entere de que falla es una bomba lenta.
