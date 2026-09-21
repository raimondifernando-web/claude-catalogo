# rubro-estudio-arquitectura — qué cambia para vos

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
