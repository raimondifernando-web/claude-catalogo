# claude-catalogo

Catálogo público de plugins para **Claude Code**, pensado para empresas y profesionales que arrancan con Claude
acompañados por una consultoría. Todo lo que hay acá es genérico: sin datos, sin credenciales, sin nombres de clientes.

## Cómo se instala (el cliente, en su máquina, con su cuenta)
```
claude plugin marketplace add raimondifernando-web/claude-catalogo
claude plugin install base-segura@claude-catalogo
claude plugin install rubro-estudio-arquitectura@claude-catalogo   # según el rubro
claude plugin install metodo@claude-catalogo                        # a las 2 semanas, o cuando duela
```
Actualizar más adelante: `claude plugin update base-segura@claude-catalogo` (o `/plugin` → Update dentro de Claude Code).

## Plugins
| Plugin | Capa | Qué es | Estado |
|---|---|---|---|
| `base-segura` | L1 | Skills transversales (escritura, documentos, análisis) + `humanizalo` (que tus textos no suenen a IA) + `modo-directo` (respuestas del largo que corresponde) + `skill-security-auditor` (auditar skills de afuera) + agentes básicos + plantillas de `CLAUDE.md` | 0.8.0 |
| `metodo` | L3 | `/metodo:arrancar`, `/metodo:planear`, `/metodo:criticar` (sin adular), `/metodo:cerrar` (handoff + prompt de reanudación + sube el avance en un solo gesto), `/metodo:crear-agente` (PM de empresa), `/metodo:otra-sesion` (dos sesiones a la vez sin pisarse) + 14 reglas del método. `/cerrar` deja `REANUDAR.md` y `/arrancar` lo levanta solo: no se pega nada | 0.8.0 |
| `rubro-estudio-arquitectura` | L2 | Propuestas y honorarios, pliegos, informes de visita, adicionales, punch list, revisión de presupuestos, normativa argentina sobre PDFs, plan semanal + ficha A3 (método), identidad visual del estudio (tu marca en cada pieza), investigación de mercado, contenido y diseño (26 skills + 5 agentes). Conectores CAD/BIM en `docs/CAD-BIM.md`. Requiere `base-segura` | 0.8.0 |

Cada plugin tiene su `CHANGELOG.md` escrito en lenguaje del cliente ("qué cambia para vos").

## Qué necesita tu computadora (y cómo saberlo en 10 segundos)
Algunas skills usan programas de fondo (Python 3, markitdown, Node.js…) o claves de servicios pagos. Cada plugin trae un
`requisitos.md` en lenguaje simple (qué skill necesita qué, qué pasa si falta, cómo instalarlo en Mac), y las skills que
dependen de algo lo chequean antes de usarlo: si falta, Claude avisa y ofrece una alternativa en vez de tirar un error.
Para ver de una vez qué te falta: **`docs/CHEQUEO.md`** → un comando que devuelve OK / FALTA / OPCIONAL (no instala nada, no muestra claves).

**¿Querés sumar una herramienta de afuera?** `docs/RECURSOS.md`: dónde buscar, el filtro de 5 preguntas y los repositorios de confianza; la auditoría la hace `skill-security-auditor` (base-segura).
**¿NotebookLM desde Claude?** `docs/NOTEBOOKLM-SEGURO.md`: 5 reglas obligatorias (versión fija, login desde la herramienta, copia local, no leer el archivo, saber revocar); cuenta dedicada opcional.
**¿Gmail, Calendar, Drive, Notion, Chrome, manejar la Mac, Meta Ads, Google Ads, Clarity, n8n?** `docs/CONECTORES.md`: qué es cada conector, qué pide, qué sale de tu computadora, en qué orden activarlos y las 3 reglas (lo autorizás vos · claves nunca en el chat · pagos y códigos siempre vos).
**¿Usás Revit, Archicad, AutoCAD, Rhino, FreeCAD, Blender o QGIS?** `docs/CAD-BIM.md`: qué conector existe para cada programa, qué pide y las 3 reglas antes de activar uno (licencia propia, archivo de prueba, oficial gana a comunitario).
**¿Hay que publicar una herramienta en internet?** `docs/HOSTING.md`: Vercel vs VPS para no técnicos, con el tope de gasto del día 1.

**¿Y qué carpetas tenés sin respaldo?** Segundo chequeo en el mismo doc (`scripts/huerfanas.sh`): lista lo que está en tu computadora y en ningún repo ni nube, y sugiere el cajón (repo · nube · datos · borrar · gestor de claves). No mueve ni borra nada.

## Qué NO empaqueta un plugin (y por eso hay `templates/`)
- Tu `~/.claude/CLAUDE.md` global (reglas que aplican a todo): se copia una vez desde `plugins/base-segura/templates/CLAUDE-global.md`.
- El `CLAUDE.md` de tu empresa (quién sos, cómo trabajás): desde `templates/CLAUDE-empresa.md`, en tu carpeta de trabajo.
- Tus permisos de usuario y tus conectores (Gmail, Drive…): los autorizás vos, con tu cuenta.

## Seguridad
Antes de cada release: grep de datos/credenciales = 0, instalación de prueba en un HOME temporal, chequeo de seguridad del plugin.
Las skills de terceros conservan su licencia original (ver cada carpeta). Este repo: licencia MIT.
