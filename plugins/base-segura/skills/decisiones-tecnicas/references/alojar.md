# Alojar una web o herramienta

Precios: verificá siempre en la página oficial (cambian). Los números de acá son de orden de magnitud, no de lista.

## Árbol de decisión (en este orden, parás en el primero que alcanza)
1. **¿Hace falta ponerla en internet?** Un informe, una presentación o una página HTML suelta se comparten desde la nube del cliente
   o como Artifact de Claude: costo 0, sin servidor. → No contrates hosting.
2. **¿Sirve lo que ya incluye su suite?**
   - Google Workspace: **Google Sites** (web informativa, sin código) · **Apps Script** como web app o **AppSheet** (herramienta interna con datos) · Forms para formularios.
   - Microsoft 365: **SharePoint** (sitio interno) · **Power Apps** / Forms (herramienta o formulario) · Power Automate para los avisos.
   → 0 de licencia extra si el plan lo incluye (confirmalo); el tiempo de mantenimiento no es 0. Límite: diseño limitado. Trampas: Sites con dominio propio va en `www.` (el dominio pelado necesita un reenvío en el registrador); revisá en la consola que se permita publicar sitios y formularios hacia afuera de la organización.

**Criterio de corte que suele decidir: ¿quién cambia un texto mañana?** Si la respuesta es «solo Claude con un despliegue», eso es un costo de mantenimiento y hay que decirlo.
3. **¿Es una web de marca que va a editar alguien no técnico?** → **creador de sitios sin código** (tipo Squarespace, Wix, Framer): cuota fija, sin repositorio, el estudio cambia textos solo. Verificá plan comercial, dominio propio y si se puede exportar el contenido.
4. **¿Es una web/tablero a medida que Claude arma y querés olvidarte del servidor?** → hosting administrado tipo **Vercel** (se le da el repositorio y publica solo).
5. **¿Tiene que correr algo permanente** (automatizaciones, base de datos, contenedores) **o querés precio fijo?** → **VPS** (ej. Hostinger KVM), con alguien técnico al inicio.

## Decisiones, motivo y cuándo NO aplican
| Decisión | Motivo / incidente | Cuándo NO aplica |
|---|---|---|
| **Hosting administrado: tope de gasto duro el día 1** (pausar proyectos al llegar al tope) | Una cuenta tenía el límite de gasto *deshabilitado*: sin techo. El único aviso fue el mail del proveedor sobre la cuota incluida, que avisa pero no frena. Un repositorio publicado desde varios proyectos y sin filtro de builds multiplicó los despliegues por cada cambio, y un caché apagado hizo descargar todo en cada visita: la proyección fue de **más de diez veces la cuota incluida** a los pocos días. Los avisos por mail no frenan nada; solo el límite duro | Si usás el plan gratis personal (sin cobro por uso). Ojo: ese plan suele ser **solo uso no comercial** |
| **Un proyecto de hosting por repositorio, con filtro de builds** (que solo despliegue cuando cambia lo suyo) | El incidente anterior: N proyectos construyendo el mismo repo = N builds por cambio | Un repositorio con un solo proyecto y pocos cambios |
| **VPS cuando el precio fijo importa más que la comodidad** | Cobro por adelantado y sin sorpresas; sirve para cosas que corren siempre. El costo oculto es operativo: **nadie lo parchea ni le hace copias por vos** | Si nadie técnico puede mantenerlo: una máquina sin dueño es un riesgo. Entonces, hosting administrado |
| **Verificar que el proveedor acepte los medios de pago del cliente antes de elegirlo** | Un proveedor elegido por precio se descartó porque **no aceptaba tarjetas emitidas en Argentina**; se perdió tiempo en una migración a medias | Si el cliente tiene tarjeta internacional o pago por otro canal |
| **Lo publicado es público salvo que se proteja** | Un tablero con nombres de clientes o precios internos queda abierto a quien tenga el link | Contenido pensado para ser público |
| **GPU o cómputo pesado en la nube bajo demanda, no en la computadora del usuario** | Un modelo que necesitaba GPU dedicada corrió varias veces más lento en la computadora, que no la tiene; la nube bajo demanda cobra solo por uso | Procesos livianos; o datos que no pueden salir de la oficina (ahí se evalúa otra cosa, ver `ia-externa.md`) |

## Costo, riesgo y datos que salen (completar al recomendar)
| Opción | Costo orden de magnitud | Riesgo principal | Datos que salen |
|---|---|---|---|
| Lo que incluye la suite | 0 extra (confirmar plan) | Límites de diseño; depender de la suite | Quedan en la suite del cliente |
| Hosting administrado | cuota por usuario + uso variable | Factura variable → exige tope | Código y archivos publicados en un tercero |
| VPS | fijo mensual bajo | Sin mantenimiento = vulnerable | Todo lo que alojes, en un tercero |
