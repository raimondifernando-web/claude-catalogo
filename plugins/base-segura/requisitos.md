# base-segura — qué necesita tu computadora

Claude Code trae el "cerebro". Algunas skills además usan programas de fondo que hay que instalar una sola vez.
Esta tabla dice **qué skill necesita qué, qué pasa si falta y cómo instalarlo en Mac** (Windows: próximamente).
Para saber qué te falta sin adivinar: corré el chequeo (`docs/CHEQUEO.md`).

## Lo que NO necesita nada extra (8 de 12 skills)
`copy-editing` · `doc-coauthoring` · `meeting-insights-analyzer` · `planning-with-files` · `professional-communication` ·
`session-handoff` · `writing-clearly-and-concisely` · `skill-creator` (uso normal). Funcionan con Claude Code solo.

## Lo que sí necesita algo

| Skill | Necesita | Si falta | Instalar (Mac) |
|---|---|---|---|
| `markitdown` (leer PDF, Word, Excel, PowerPoint) | **Python 3** + **markitdown** | No puede abrir esos archivos. Claude te avisa: "hace falta instalar markitdown" | 1) `xcode-select --install` (Python 3, viene de Apple) · 2) `python3 -m pip install --user 'markitdown[all]'`. Si después Terminal dice "command not found: markitdown", está bien igual: Claude lo usa como `python3 -m markitdown` |
| `skill-security-auditor` (auditar una skill de afuera antes de instalarla) | **Python 3** (+ **git** solo si se audita por URL de GitHub; viene con las Herramientas de Apple) | Claude audita a mano leyendo la carpeta (menos exhaustivo) | `xcode-select --install` |
| `markitdown` — leer texto dentro de imágenes o PDF escaneados | **Tesseract** (OCR) — *opcional* | Lee todo lo demás; solo no reconoce texto en imágenes | `brew install tesseract` (requiere Homebrew: brew.sh) |
| `markitdown` — funciones con IA (`convert_with_ai.py`) | Clave de OpenAI u OpenRouter — *opcional, pago* | Convierte igual sin IA | Se configura como variable de entorno; **nunca se pega en el chat** |
| `excel-analysis` (tablas dinámicas, gráficos) | **Python 3** + librerías **pandas** y **openpyxl** | Claude te avisa y ofrece la alternativa: exportar a CSV o leer con `markitdown` | `python3 -m pip install --user pandas openpyxl` |
| `mermaid-diagrams` — exportar a imagen PNG/SVG | **Mermaid CLI** (`mmdc`, requiere Node.js) — *opcional* | **Los diagramas funcionan igual**: se ven en claude.ai, Notion, GitHub y Obsidian. Solo no genera el archivo de imagen | `npm install -g @mermaid-js/mermaid-cli` (requiere Node.js: nodejs.org) |
| `skill-creator` — evaluaciones avanzadas (`run_eval.py`) | Python 3 + `pyyaml` — *solo para usuarios avanzados* | Crear y editar skills funciona igual | `python3 -m pip install --user pyyaml` |

## En orden, para arrancar (10 minutos)
1. **Python 3**: abrí Terminal y pegá `xcode-select --install`. Aceptá la ventana de Apple. Es gratis y oficial.
2. **markitdown**: `python3 -m pip install --user 'markitdown[all]'`
3. **Excel**: `python3 -m pip install --user pandas openpyxl`
4. Corré el chequeo (`docs/CHEQUEO.md`) y pegá la captura en tu portal.

Lo demás (Tesseract, Mermaid CLI, claves) solo si vas a usar esas funciones puntuales — tu consultor te dice cuándo.

## Conectores y herramientas para tu negocio (no se instalan: se conectan)
Gmail, Google Calendar, Google Drive y Notion son **conectores oficiales de claude.ai**: se activan una vez desde
claude.ai → Configuración → Conectores, con tu cuenta, y valen en Claude Code, Cowork y el chat. Son lo que más rinde
el día 1. Después vienen **manejar Chrome y la computadora** (funciones de la app de Claude: mucho poder, se activan a
conciencia y nunca para pagar ni para códigos de verificación) y, si hacés publicidad o medís tu web, **Meta Ads,
Google Ads, Microsoft Clarity, n8n y Firecrawl**. Qué hace cada uno, qué sale de tu computadora, cómo se activa y en qué
orden conviene: **`docs/CONECTORES.md`**.

## Qué NO hace este plugin
No instala nada por su cuenta. Instalar programas en tu computadora es una decisión tuya, guiada por tu consultor.
