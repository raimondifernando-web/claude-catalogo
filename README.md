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
| `base-segura` | L1 | Skills transversales (escritura, documentos, análisis) + agentes básicos + plantillas de `CLAUDE.md` | 0.1.3 |
| `metodo` | L3 | `/metodo:arrancar`, `/metodo:planear`, `/metodo:criticar` (sin adular), `/metodo:cerrar` (handoff + prompt de reanudación) + 10 reglas del método | 0.1.3 |
| `rubro-estudio-arquitectura` | L2 | Propuestas, cotización, presentación, investigación de mercado, contenido y diseño (15 skills + 5 agentes). Requiere `base-segura` | 0.1.3 |

Cada plugin tiene su `CHANGELOG.md` escrito en lenguaje del cliente ("qué cambia para vos").

## Qué necesita tu computadora (y cómo saberlo en 10 segundos)
Algunas skills usan programas de fondo (Python 3, markitdown, Node.js…) o claves de servicios pagos. Cada plugin trae un
`requisitos.md` en lenguaje simple (qué skill necesita qué, qué pasa si falta, cómo instalarlo en Mac), y las skills que
dependen de algo lo chequean antes de usarlo: si falta, Claude avisa y ofrece una alternativa en vez de tirar un error.
Para ver de una vez qué te falta: **`docs/CHEQUEO.md`** → un comando que devuelve OK / FALTA / OPCIONAL (no instala nada, no muestra claves).

**¿Y qué carpetas tenés sin respaldo?** Segundo chequeo en el mismo doc (`scripts/huerfanas.sh`): lista lo que está en tu computadora y en ningún repo ni nube, y sugiere el cajón (repo · nube · datos · borrar · gestor de claves). No mueve ni borra nada.

## Qué NO empaqueta un plugin (y por eso hay `templates/`)
- Tu `~/.claude/CLAUDE.md` global (reglas que aplican a todo): se copia una vez desde `plugins/base-segura/templates/CLAUDE-global.md`.
- El `CLAUDE.md` de tu empresa (quién sos, cómo trabajás): desde `templates/CLAUDE-empresa.md`, en tu carpeta de trabajo.
- Tus permisos de usuario y tus conectores (Gmail, Drive…): los autorizás vos, con tu cuenta.

## Seguridad
Antes de cada release: grep de datos/credenciales = 0, instalación de prueba en un HOME temporal, chequeo de seguridad del plugin.
Las skills de terceros conservan su licencia original (ver cada carpeta). Este repo: licencia MIT.
