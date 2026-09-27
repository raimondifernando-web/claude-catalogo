# escala-diseno-video — qué necesita tu computadora

Recomendado junto con `base-segura` (ver `plugins/base-segura/requisitos.md`). Esta tabla cubre solo lo que agrega este
paquete. Para saber qué te falta: corré el chequeo (`docs/CHEQUEO.md`).

## Lo que NO necesita nada extra
`estilo-de-marca` · `frontend-ui-engineering` · `components-build` · `ui-design-system` · `algorithmic-art` (arte generativo
en un HTML que abrís en el navegador). Funcionan con Claude Code solo.

## Lo que sí necesita algo

| Skill | Necesita | Si falta | Instalar (Mac) |
|---|---|---|---|
| `huashu-design` (presentaciones, prototipos, animaciones) | **Node.js 18+**. Para exportar a PDF, PPTX o video: sus librerías (`playwright`, `pptxgenjs`, `pdf-lib`, `sharp`) y **ffmpeg** | Arma el HTML igual y lo abrís en el navegador. Lo que no hace es exportar a PDF/PPTX/MP4 | Node.js LTS desde nodejs.org · `brew install ffmpeg` · en la carpeta de la skill: `npm install` y `npx playwright install chromium` (Claude te lo propone la primera vez) |
| `huashu-design` — revisión de video con IA / voz en la nube | **Clave propia** de BytePlus ModelArk o Volcano (servicio pago) | No revisa en la nube. Queda la revisión por capturas, que corre en tu computadora | La clave la configurás vos como variable de entorno; **nunca se pega en el chat**. Sube el video o el texto a un tercero: no la uses con material confidencial |
| Set de HyperFrames (`hyperframes`, `-core`, `-animation`, `-creative`, `-keyframes`, `-audio`, `-cli`, `-registry`, `general-video`) | **Node.js 22+** y **ffmpeg** | No renderiza video | Node.js 22 LTS desde nodejs.org · `brew install ffmpeg`. **Apagar la telemetría:** agregá `HYPERFRAMES_NO_TELEMETRY=1` y `DO_NOT_TRACK=1` al bloque `env` de tu `~/.claude/settings.json` (tu consultor te guía) |
| `media-use` (voz, música y efectos para los videos) | Lo mismo que HyperFrames. Para voz de HeyGen: **cuenta y clave de HeyGen** (pago). Para música con IA local: Python 3 | Sin clave de HeyGen usa las opciones locales. Si falta un paquete de Python, lo avisa y no lo instala solo | La clave de HeyGen va en el archivo de entorno de la carpeta del proyecto, nunca en el chat |
| `slack-gif-creator` (GIFs animados) | **Python 3** + `pillow`, `imageio`, `imageio-ffmpeg`, `numpy` | No genera GIFs | `python3 -m pip install --user pillow imageio imageio-ffmpeg numpy` |
| `canvas-design` (afiches y gráfica en PDF/PNG) | **Python 3** (trae sus propias fuentes) | Claude te lo avisa y propone un HTML en su lugar | Viene con la Mac; si no, desde python.org |
| `ui-ux-pro-max` (inteligencia de diseño de UI) | **Python 3** para su buscador de estilos y paletas | Usa las guías de texto, sin el buscador | Viene con la Mac |

## En orden, para arrancar
1. Node.js LTS (nodejs.org) y `brew install ffmpeg`.
2. Si vas a hacer video con HyperFrames: las dos variables de telemetría en `~/.claude/settings.json`.
3. Lo demás, cuando Claude lo pida la primera vez.
