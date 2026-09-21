# rubro-estudio-arquitectura — qué necesita tu computadora

Requiere tener instalado `base-segura` (y sus requisitos: ver `plugins/base-segura/requisitos.md`).
Esta tabla cubre solo lo que agrega este paquete. Para saber qué te falta: corré el chequeo (`docs/CHEQUEO.md`).

## Lo que NO necesita nada extra (12 de 17 skills)
`brand-guidelines` · `competitive-teardown` · `content-strategy` · `customer-research` · `founder-coach` ·
`frontend-design` · `pestel-analysis` · `pricing-strategy` · `social-content` · `storyboard` · `theme-factory` ·
`notebooklm-preparar` (te deja listo qué cargar y qué preguntar en notebooklm.google.com; vos lo pegás en el navegador — no instala nada ni toca tu cuenta de Google).
Funcionan con Claude Code solo.

## Lo que sí necesita algo

| Skill | Necesita | Si falta | Instalar (Mac) |
|---|---|---|---|
| `generate-image` (imágenes con IA) | **Python 3** + librería **requests** + **cuenta y clave de OpenRouter** (servicio pago, lo contratás vos) | No genera imágenes. Claude te avisa y te manda a la fase «Claves y servicios» del portal | `python3 -m pip install --user requests` · clave: crear cuenta en openrouter.ai y configurarla como variable de entorno `OPENROUTER_API_KEY` (tu consultor te guía; **nunca se pega en el chat**) |
| `transcribe` (audio → texto) | **Python 3** + librería **openai** + **cuenta y clave de OpenAI** (servicio pago) | No transcribe. Alternativa gratis: grabar con **Notas de Voz** de Apple, que transcribe sola, y pegar el texto | `python3 -m pip install --user openai` · clave `OPENAI_API_KEY` en platform.openai.com |
| `web-artifacts-builder` (prototipos web con React) | **Node.js 18+** y **pnpm** o **npm** | Para páginas simples Claude usa `frontend-design` (un solo archivo HTML, sin instalar nada). Solo hace falta para prototipos grandes con muchos componentes | Node.js LTS desde nodejs.org (instalador normal de Mac) · luego `corepack enable` |
| `notebooklm` (manejar Google NotebookLM desde Claude) | **Python 3** + `notebooklm-py` **versión fija** + navegador Playwright + **una cuenta Google dedicada** (obligatoria, ver `docs/NOTEBOOKLM-SEGURO.md`) | No automatiza; Claude usa `notebooklm-preparar` y vos pegás en el navegador | `python3 -m pip install --user 'notebooklm-py[browser]==0.8.2'` · `python3 -m playwright install chromium` · `notebooklm login` con la cuenta dedicada |
| `market-research-reports` — informes de mercado | Nada para el informe en texto/Word | El informe sale en Markdown. Las figuras se hacen con `generate-image` o diagramas Mermaid. **La versión PDF con LaTeX y las skills `scientific-schematics`/`research-lookup` no están incluidas** en este paquete | Python 3 solo si querés correr el script de figuras (`xcode-select --install`) |

## En orden, para arrancar
1. Tener `base-segura` con sus 3 pasos hechos (Python 3, markitdown, pandas).
2. Si vas a usar imágenes con IA: cuenta en OpenRouter → clave → `python3 -m pip install --user requests`.
3. Si vas a transcribir reuniones: cuenta en OpenAI → clave → `python3 -m pip install --user openai`.
4. Node.js solo si tu consultor te lo indica (prototipos web complejos).
5. Corré el chequeo y pegá la captura en tu portal.

## Conectores de claude.ai que suman a este rubro (no se instalan: se conectan)
Un **conector** es una herramienta que Claude usa a través de tu cuenta en ese servicio. No se instala nada en tu
computadora: se activa una vez desde claude.ai y vale en Claude Code, Cowork y el chat. Cómo: **claude.ai → tu perfil
→ Configuración → Conectores → Explorar conectores** → buscá el nombre → *Conectar* → iniciás sesión con tu cuenta
del servicio y aceptás los permisos. Luego, en Claude Code, se ve con `/mcp`.

| Conector | Para qué en un estudio | Qué sale de tu computadora | Costo |
|---|---|---|---|
| **Canva** (oficial, `mcp.canva.com`) | Buscar, crear, completar y exportar diseños de tu Canva: presentaciones de propuesta, posteos, láminas | Claude lee y crea diseños **en tu cuenta de Canva**; lo que le pidas (textos, imágenes) pasa por Canva. No pidas que suba planos o datos de clientes que no quieras en Canva | Cuenta Canva (gratis o Pro, la tuya) |
| **Excalidraw** (oficial, `mcp.excalidraw.com`) | Diagramas "a mano alzada": esquemas de proceso, organigramas, flujos de obra, bocetos de ideas | El contenido del diagrama se genera en el servicio de Excalidraw; no accede a tus archivos | Gratis |

Alternativa sin conector: `mermaid-diagrams` (base-segura) hace diagramas en texto que se ven en Notion, GitHub y Obsidian.
Regla: un conector pide acceso a una cuenta tuya → antes de conectar, la pregunta 5 del filtro (`docs/RECURSOS.md`) pesa doble.

## Sobre las claves
Son tuyas, con tu tarjeta, con tu límite de gasto. Claude solo verifica que existan; nunca las lee ni las muestra.
Se guardan como variable de entorno del sistema (tu consultor te pasa el paso exacto).
