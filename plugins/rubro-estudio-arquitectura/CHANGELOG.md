# rubro-estudio-arquitectura — qué cambia para vos

## 0.11.4 — 2026-09-22
- Sin cambios; acompaña al catálogo 0.11.4 (`metodo`: `settings.json` vuelve a viajar; los enganches de Graphify van al archivo local).

## 0.11.3 — 2026-09-22
- Sin cambios; acompaña al catálogo 0.11.3 (`metodo`: el mapa de Graphify nunca se sube).

## 0.11.2 — 2026-09-22
- Sin cambios; acompaña al catálogo 0.11.2 (`metodo`: el cierre sube solo lo de cada sesión).

## 0.11.1 — 2026-09-22
- Sin cambios; acompaña al catálogo 0.11.1 (`base-segura`: la cuenta de skills decía 12 y son 14; chequeo automático antes de publicar). Verificado: este paquete sí declara bien sus 26 skills y 5 agentes.

## 0.11.0 — 2026-09-22
- Sin cambios; acompaña al catálogo 0.11.0 (`base-segura`: `docs/GRAPHIFY.md`). Aplica al estudio cuando empiece a construir sus propias herramientas con Claude: el mapa es gratis sobre código, y el modo que entiende planos y PDFs es el caro — está medido en el documento.

## 0.10.1 — 2026-09-22
- **`designer`: mismo arreglo que en `base-segura`** — tenía anotado `claude-sonnet-4-6` (un modelo de fecha fija) y ahora dice `sonnet`, que es siempre el vigente.
- **`project-idea-validator` pasa a pensar con Opus** (antes Sonnet). Su trabajo es darte un go/no-go sobre una idea antes de que le pongas plata y meses encima: juzga, decide, y equivocarse ahí sale caro. Por las tres preguntas de la guía de ruteo le corresponde el modelo más capaz. En la práctica: te va a contestar un poco más lento y bastante mejor argumentado.
Para actualizar: `claude plugin update rubro-estudio-arquitectura@claude-catalogo`.

## 0.10.0 — 2026-09-22
- Sin cambios; acompaña al catálogo 0.10.0 (`base-segura`: la pregunta 1 del filtro pasa a tener tres caminos).

## 0.9.0 — 2026-09-22
- Sin cambios; acompaña al catálogo 0.9.0 (`metodo`: guía de ruteo de modelos + criterio en `/metodo:crear-agente`).

## 0.8.0 — 2026-09-22
- Sin cambios; acompaña al catálogo 0.8.0 (`base-segura`: `humanizalo` + `modo-directo`).

## 0.7.0 — 2026-09-22
- **La skill de marca ahora aplica TU marca, no la de Anthropic.** Sale `brand-guidelines` (era la skill interna de Anthropic para su propia marca: pintaba tus piezas con los colores de Anthropic) y entra **`identidad-visual-del-estudio`**: la primera vez te hace 6 preguntas de a una (colores, tipografías, logo, tono, qué no, firma), te muestra el archivo `identidad-visual.md` y lo guarda con tu confirmación; desde ahí, cada propuesta, presentación, página, imagen o posteo sale con la identidad del estudio. Si no sabés un color, le pasás una tarjeta o un PDF y lo saca de ahí; lo que propone Claude queda marcado «propuesta» hasta que lo confirmes. No necesita instalar nada, no pide claves y nada sale de tu computadora. Siguen 26 skills (sale una, entra una).
Para actualizar: `claude plugin update rubro-estudio-arquitectura@claude-catalogo`.

## 0.6.0 — 2026-09-21
- Sin cambios; acompaña al catálogo 0.6.0 (`base-segura`: `docs/CONECTORES.md`). Los conectores Canva/Excalidraw/ClickUp/Mapbox de `requisitos.md` siguen ahí; el resto (Gmail, Drive, Chrome, Mac, marketing) está en `docs/CONECTORES.md`.

## 0.5.0 — 2026-09-21
- Sin cambios; acompaña al catálogo 0.5.0 (`metodo`: `/arrancar` levanta `REANUDAR.md` sin pegar).

## 0.4.1 — 2026-09-21
- Sin cambios; acompaña al catálogo 0.4.1 (`metodo`: freno por archivos no-texto + `.gitignore` de fábrica).

## 0.4.0 — 2026-09-21
- Sin cambios; acompaña al catálogo 0.4.0 (`metodo`: sesiones en paralelo + cierre en un gesto).

## 0.3.0 — 2026-09-21
**9 skills nuevas** (17 → 26), pensadas para el día a día de un estudio, en español rioplatense y con Argentina por defecto (Código Civil y Comercial, rubros de cómputo local). Ninguna necesita instalar nada ni manda datos a ningún servicio: trabajan sobre lo que vos pegás o compartís.
- **Estudio:** `propuesta-de-honorarios` (alcance por etapa, entregables, plazos, honorarios sin cifras inventadas) · `pliego-especificaciones` (Generalidades · Materiales · Ejecución por rubro, con marcas "a verificar") · `informe-visita-de-obra` (de notas/fotos/audio a informe firmable: lo que viste, lo que te contaron, lo que interpretás). Adaptadas de `skills-for-architects` (MIT).
- **Obra:** `orden-de-cambio` (adicional con base contractual, delta de alcance, precios ítem a ítem, impacto en plazo) · `punch-list-obra` (pendientes numerados con ubicación, gremio y referencia al pliego) · `revision-de-presupuestos` (huecos de alcance, exclusiones, precios fuera de rango, comparación de cotizaciones). Adaptadas de `pm-claude-skills` (MIT).
- **Normativa:** `normativa-argentina` — responde "¿esto cumple?" **solo sobre los PDFs oficiales que le compartas** (municipal, provincial, CIRSOC, IRAM), citando artículo y archivo. Sin el PDF, te dice dónde conseguirlo. **Nunca inventa un artículo ni un valor.** Usa `pdf`/`markitdown` de `base-segura`.
- **Método del estudio (Lean, sin jerga):** `plan-semanal-estudio` (reunión de 15-20 min → plan de la semana por persona + mirada a 4-6 semanas; una tarea con algo que la frena no entra al plan) · `a3-decision` (ficha de una página para un problema que se repite o una decisión importante). Si tenés el conector de ClickUp, el plan semanal lee tus tareas; si no, pegás la lista.
- `docs/CAD-BIM.md` abre con el caso más común de un estudio argentino: **AutoCAD LT · ZWCAD · SketchUp**. Qué se puede hoy con cada uno, y por qué los conectores de AutoCAD LT y ZWCAD **solo corren en Windows** (AutoCAD LT para Mac no tiene AutoLISP). El camino que funciona en Mac y Windows a la vez es `ezdxf` sobre los DXF. SketchUp: nada seguro todavía.
- `requisitos.md`: conectores **ClickUp** (oficial, beta; lo autoriza el dueño de la cuenta) y **Mapbox** (oficial; token propio) + puntero a `docs/CAD-BIM.md`.
- **Nuevo `docs/CAD-BIM.md`:** qué conector existe para Revit (Autodesk sacó uno **oficial** para Revit 2027), Archicad, AutoCAD, Rhino, FreeCAD, Blender, QGIS, IFC, Speckle y Mapbox; qué pide cada uno y las 3 reglas (licencia propia, archivo de prueba, oficial gana a comunitario). No se instalan con el paquete: se activan uno por vez cuando el consultor lo indique. SketchUp queda fuera (sin conector seguro).
Para actualizar: `claude plugin update rubro-estudio-arquitectura@claude-catalogo`.

## 0.2.2 — 2026-09-21
- `notebooklm`: el protocolo `docs/NOTEBOOKLM-SEGURO.md` queda en **5 reglas obligatorias** (versión fija, iniciar sesión solo desde la ventana que abre la herramienta, carpeta local, nunca leer ni pegar ese archivo, saber revocar) y la **cuenta Google dedicada pasa a ser un refuerzo opcional**. Por qué: tu navegador ya guarda esas mismas cookies; lo que protege es el programa revisado y la copia local. Claude te pregunta una vez si aceptás las reglas y lo anota en tu `CLAUDE.md`.

## 0.2.1 — 2026-09-21
- **Nueva skill `notebooklm`** (manejar Google NotebookLM desde Claude: crear cuadernos, cargar fuentes, generar resúmenes y podcasts). Usa una librería **no oficial** que entra con la sesión de una cuenta Google guardada en tu computadora; por eso sale **con protocolo obligatorio**: `docs/NOTEBOOKLM-SEGURO.md` — cuenta Google dedicada (nunca la principal ni la de la empresa), versión fija, inicio de sesión solo desde la ventana que abre la herramienta, cómo cerrar sesión y revocar. Claude lo chequea antes de usarla.
- **Nueva skill `notebooklm-preparar`**: un "cerebro por proyecto" con Google NotebookLM, por el camino seguro. Claude elige y ordena las fuentes, arma el texto de contexto, redacta las preguntas y el pedido de salida (resumen, guía, podcast) y vos lo pegás en notebooklm.google.com. No instala nada ni usa tu cuenta de Google (las herramientas que lo automatizan necesitan tus cookies de sesión; por eso no las incluimos — ver `docs/RECURSOS.md` §5).

## 0.2.0 — 2026-09-21
- Sin cambios en las skills. `requisitos.md` suma la sección **Conectores de claude.ai**: Canva (diseños) y Excalidraw (diagramas a mano alzada), qué hacen, cómo se conectan y qué sale de tu computadora.

## 0.1.3 — 2026-09-21
- Sin cambios; acompaña al catálogo 0.1.3.

## 0.1.2 — 2026-09-21
- Sin cambios en las skills; acompaña al catálogo 0.1.2 (chequeo de carpetas huérfanas, ver `docs/CHEQUEO.md`).

## 0.1.1 — 2026-09-21
- **`requisitos.md`** (nuevo): qué necesita cada skill. 11 de las 15 no necesitan nada extra.
- **Aviso amable en vez de error** en `generate-image`, `transcribe`, `web-artifacts-builder` y `market-research-reports`: si falta un programa o una clave, Claude te avisa y te da la alternativa (por ejemplo, transcribir con Notas de Voz de Apple; prototipos simples en un solo archivo HTML).
- Aclarado en `market-research-reports` que la versión PDF con LaTeX y las skills auxiliares no están incluidas en este paquete: el informe sale en Markdown/Word.
Para actualizar: `claude plugin update rubro-estudio-arquitectura@claude-catalogo`.

## 0.1.0 — 2026-09-20
Primera versión. Es el pack de rubro (capa L2) para un estudio de arquitectura o profesión parecida. Se instala encima de `base-segura`.
- **15 skills**: decidir y cotizar (`founder-coach`, `pricing-strategy`), entender clientes y mercado (`customer-research`, `competitive-teardown`, `market-research-reports`, `pestel-analysis`), comunicar (`content-strategy`, `social-content`, `brand-guidelines`), presentar (`frontend-design`, `theme-factory`, `web-artifacts-builder`, `storyboard`). Dos **opcionales con clave paga propia**: `generate-image` (OpenRouter) y `transcribe` (OpenAI). Sin clave, simplemente no hacen nada.
- **5 agentes**: investigador de mercado, analista de negocio, validador de ideas, redactor técnico, diseñador.
Junto con `base-segura` (11 skills + 3 agentes) suma exactamente lo que tenía el kit v0.1 por zip: **26 skills + 8 agentes**. Nada se pierde al migrar.
