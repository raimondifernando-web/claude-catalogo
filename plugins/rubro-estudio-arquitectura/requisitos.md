# rubro-estudio-arquitectura — qué necesita tu computadora

Requiere tener instalado `base-segura` (y sus requisitos: ver `plugins/base-segura/requisitos.md`).
Esta tabla cubre solo lo que agrega este paquete. Para saber qué te falta: corré el chequeo (`docs/CHEQUEO.md`).

## Lo que NO necesita nada extra (11 de 15 skills)
`brand-guidelines` · `competitive-teardown` · `content-strategy` · `customer-research` · `founder-coach` ·
`frontend-design` · `pestel-analysis` · `pricing-strategy` · `social-content` · `storyboard` · `theme-factory`.
Funcionan con Claude Code solo.

## Lo que sí necesita algo

| Skill | Necesita | Si falta | Instalar (Mac) |
|---|---|---|---|
| `generate-image` (imágenes con IA) | **Python 3** + librería **requests** + **cuenta y clave de OpenRouter** (servicio pago, lo contratás vos) | No genera imágenes. Claude te avisa y te manda a la fase «Claves y servicios» del portal | `python3 -m pip install --user requests` · clave: crear cuenta en openrouter.ai y configurarla como variable de entorno `OPENROUTER_API_KEY` (tu consultor te guía; **nunca se pega en el chat**) |
| `transcribe` (audio → texto) | **Python 3** + librería **openai** + **cuenta y clave de OpenAI** (servicio pago) | No transcribe. Alternativa gratis: grabar con **Notas de Voz** de Apple, que transcribe sola, y pegar el texto | `python3 -m pip install --user openai` · clave `OPENAI_API_KEY` en platform.openai.com |
| `web-artifacts-builder` (prototipos web con React) | **Node.js 18+** y **pnpm** o **npm** | Para páginas simples Claude usa `frontend-design` (un solo archivo HTML, sin instalar nada). Solo hace falta para prototipos grandes con muchos componentes | Node.js LTS desde nodejs.org (instalador normal de Mac) · luego `corepack enable` |
| `market-research-reports` — informes de mercado | Nada para el informe en texto/Word | El informe sale en Markdown. Las figuras se hacen con `generate-image` o diagramas Mermaid. **La versión PDF con LaTeX y las skills `scientific-schematics`/`research-lookup` no están incluidas** en este paquete | Python 3 solo si querés correr el script de figuras (`xcode-select --install`) |

## En orden, para arrancar
1. Tener `base-segura` con sus 3 pasos hechos (Python 3, markitdown, pandas).
2. Si vas a usar imágenes con IA: cuenta en OpenRouter → clave → `python3 -m pip install --user requests`.
3. Si vas a transcribir reuniones: cuenta en OpenAI → clave → `python3 -m pip install --user openai`.
4. Node.js solo si tu consultor te lo indica (prototipos web complejos).
5. Corré el chequeo y pegá la captura en tu portal.

## Sobre las claves
Son tuyas, con tu tarjeta, con tu límite de gasto. Claude solo verifica que existan; nunca las lee ni las muestra.
Se guardan como variable de entorno del sistema (tu consultor te pasa el paso exacto).
