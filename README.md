# claude-catalogo

Catálogo público de plugins para **Claude Code**, pensado para empresas y profesionales que arrancan con Claude
acompañados por una consultoría. Todo lo que hay acá es genérico: sin datos, sin credenciales, sin nombres de clientes.

## Cómo se instala (el cliente, en su máquina, con su cuenta)
```
claude plugin marketplace add raimondifernando-web/claude-catalogo
claude plugin install base-segura@claude-catalogo
```
Actualizar más adelante: `claude plugin update base-segura@claude-catalogo` (o `/plugin` → Update dentro de Claude Code).

## Plugins
| Plugin | Capa | Qué es | Estado |
|---|---|---|---|
| `base-segura` | L1 | Skills transversales (escritura, documentos, análisis) + agentes básicos + plantillas de `CLAUDE.md` | 0.1.0 |
| `metodo` | L3 | `/cerrar`, `/arrancar`, `/criticar`, `/planear`, handoffs | pendiente |
| `rubro-estudio-arquitectura` | L2 | Propuestas, cotización, presentación, investigación de mercado | pendiente |

Cada plugin tiene su `CHANGELOG.md` escrito en lenguaje del cliente ("qué cambia para vos").

## Qué NO empaqueta un plugin (y por eso hay `templates/`)
- Tu `~/.claude/CLAUDE.md` global (reglas que aplican a todo): se copia una vez desde `plugins/base-segura/templates/CLAUDE-global.md`.
- El `CLAUDE.md` de tu empresa (quién sos, cómo trabajás): desde `templates/CLAUDE-empresa.md`, en tu carpeta de trabajo.
- Tus permisos de usuario y tus conectores (Gmail, Drive…): los autorizás vos, con tu cuenta.

## Seguridad
Antes de cada release: grep de datos/credenciales = 0, instalación de prueba en un HOME temporal, chequeo de seguridad del plugin.
Las skills de terceros conservan su licencia original (ver cada carpeta). Este repo: licencia MIT.
