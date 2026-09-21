---
name: notebooklm-preparar
description: "Prepara todo lo que va a un cuaderno de Google NotebookLM SIN automatizar la cuenta: elige y ordena las fuentes, arma el texto de contexto, redacta las preguntas y el pedido de salida (resumen, guía de estudio, podcast) listos para pegar en notebooklm.google.com. Usala cuando el usuario diga 'armame un NotebookLM', 'qué le cargo al notebook', 'preparame las fuentes para NotebookLM', 'un cuaderno por proyecto/cliente/obra', o cuando quiera investigar un tema con sus propios documentos. NO instala ni usa notebooklm-py ni cookies: el usuario opera NotebookLM en el navegador."
metadata:
  version: 1.0.0
sync: cowork
---

# NotebookLM — preparar el cuaderno (sin tocar la cuenta de Google)

NotebookLM (Google) responde solo con lo que le cargás: hasta 50 fuentes por cuaderno (PDF, Google Docs/Slides,
sitios web, YouTube, audio, texto pegado). Es un "cerebro por proyecto". Google **no tiene API oficial**; las
herramientas que lo automatizan usan las cookies de tu cuenta Google, y por eso **esta skill no automatiza nada**:
vos pegás en el navegador lo que Claude te deja listo. Perdés dos minutos de copiar y pegar; no perdés la cuenta.

## Qué entrega Claude (en este orden, en un solo bloque copiable por paso)
1. **Nombre del cuaderno**: `<Proyecto o cliente> — <tema> — <mes año>`. Un cuaderno por proyecto/obra/cliente, no uno gigante.
2. **Lista de fuentes** (máx. 50), cada una con: qué es · dónde está (ruta, URL o "en tu Drive: …") · por qué entra ·
   orden de carga (primero lo normativo/contractual, después lo propio, al final lo de contexto). Marcar cuáles NO
   cargar y por qué (borradores viejos, versiones duplicadas, archivos con datos de terceros que no hace falta subir).
3. **Fuente "Contexto"** (texto para pegar como fuente): quién es el usuario, qué busca del cuaderno, glosario del
   proyecto (siglas, nombres, unidades), qué está decidido y qué está abierto. 150-300 palabras. Sin datos sensibles
   que no hagan falta (nada de claves, DNI, cuentas).
4. **Preguntas iniciales** (5-8), de más general a más específica, redactadas para que NotebookLM cite fuentes:
   "Según [fuente], ¿…?" · "Compará lo que dicen X e Y sobre …" · "Listá todas las fechas/plazos/montos que aparecen".
5. **Pedido de salida** según lo que necesite: resumen ejecutivo · guía de estudio · FAQ · cronología · tabla comparativa ·
   *Audio Overview* (podcast) con la indicación de enfoque ("centrate en riesgos y plazos"). Un párrafo por salida.
6. **Qué hacer con lo que salga**: NotebookLM devuelve texto; el usuario lo pega acá y Claude lo cruza con el resto
   (Excel, propuestas, Lean). NotebookLM investiga; Claude decide y produce.

## Reglas
- Antes de listar fuentes, **mirar los archivos reales** (`ls`, `markitdown` para leer PDFs si hace falta): no inventar
  documentos que "deberían" existir. Si falta uno importante, decirlo como pendiente.
- Preguntar solo lo que no se deduce: para qué se usa el cuaderno y quién lo va a leer.
- Datos de terceros (clientes, proveedores): subir el mínimo necesario. Si una fuente tiene información personal que
  no aporta, sugerir una versión recortada.
- Nunca sugerir instalar `notebooklm-py`, pegar cookies, ni "exportar la sesión de Chrome". Si el usuario lo pide,
  explicar el riesgo (quien tenga ese archivo tiene su Google) y volver al camino manual.

## Cómo se usa en NotebookLM (para el usuario)
notebooklm.google.com → **+ Nuevo cuaderno** → nombre → **+ Fuentes** (arrastrar archivos / pegar URL / "Texto copiado"
para la fuente Contexto) → panel de chat: pegar las preguntas una por una → **Estudio**: elegir la salida (Resumen,
Guía de estudio, Audio Overview…). Está incluido en Google AI Pro; la versión gratis alcanza para empezar.
