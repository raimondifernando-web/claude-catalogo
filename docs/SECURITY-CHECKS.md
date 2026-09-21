# Chequeos de seguridad por release

## base-segura 0.1.0 — 2026-09-20 — PASS
| Control | Resultado | Evidencia |
|---|---|---|
| Grep de datos/credenciales (`thisisbp|raimondifernando-?[^-]|act_\d{6,}|@gmail|@thisisbp|api_key="<20+ chars>"|sk-…`) | 0 hits | corrido sobre el plugin instalado en HOME temporal |
| Placeholders tipo `api_key="your-openrouter-api-key"` en `markitdown` | son placeholders, no valores | inspección línea por línea |
| Hooks / MCP servers / settings en el plugin | ninguno | `claude plugin details` → Hooks (0), MCP (0) |
| Código que corre al instalar | ninguno (los scripts corren solo al invocar la skill) | inventario `find -perm -u+x` |
| Llamadas de red en scripts | solo `openrouter.ai` (opcional, clave del usuario), `localhost`, Google Fonts en un HTML de reporte | grep `http|requests|urllib` |
| Symlinks | 0 | `find -type l` |
| Instalación en HOME temporal (`HOME=$(mktemp -d)`) | 11 skills + 3 agentes, enabled, ~1.163 tok always-on | `claude plugin install base-segura@claude-catalogo` |

## rubro-estudio-arquitectura 0.1.0 — 2026-09-20 — PASS
| Control | Resultado |
|---|---|
| Grep de datos/credenciales (mismo patrón) | 0 hits |
| Hooks / MCP / settings | ninguno; nada corre al instalar |
| Claves pagas | `generate-image` (OPENROUTER_API_KEY) y `transcribe` (OPENAI_API_KEY) las lee de variables de entorno del usuario; sin clave no operan. Documentado en CHANGELOG y plugin.json |
| Instalación en HOME temporal (local y desde GitHub) | 15 skills + 5 agentes, enabled |

## metodo 0.1.0 — 2026-09-20 — PASS
| Control | Resultado |
|---|---|
| Contenido | 4 skills de texto (sin scripts), 2 plantillas. Sin hooks, MCP, settings ni código ejecutable |
| Grep de datos/credenciales y de referencias al ecosistema de origen (`Fernando|Mandamiento|ORQUESTA|Paperclip|fable`) | 0 hits fuera de author/homepage |
| Instalación en HOME temporal desde GitHub | 4 skills, enabled |

## base-segura 0.1.1 · rubro-estudio-arquitectura 0.1.1 · metodo 0.1.1 — 2026-09-21 — PASS
Cambio: requisitos declarados (`requisitos.md` por plugin), bloque de chequeo previo en 7 SKILL.md, `scripts/chequeo.sh` + `docs/CHEQUEO.md`. Sin skills nuevas.
| Control | Resultado |
|---|---|
| Grep de datos/credenciales (mismo patrón) | 0 hits reales (los únicos matches son el propio patrón en este archivo y el usuario de GitHub en URLs del repo) |
| Referencias al ecosistema de origen en lo nuevo (`Fernando|Mandamiento|ORQUESTA|Paperclip|fable|EBRAS`) | 0 fuera de author/URLs |
| `scripts/chequeo.sh` | solo lectura: `command -v`, `python3 -c import`, `test -n "$VAR"`/`grep -q` sobre nombre de variable. No instala, no escribe, no imprime valores de claves. Sin llamadas de red. `bash -n` OK |
| Bloques de chequeo en SKILL.md | comandos de verificación idénticos a los del script; instruyen a no pedir claves por chat |
| Hooks / MCP / settings / symlinks | ninguno / 0 |
| Instalación en HOME temporal desde copia local (rutas absolutas) | 3 plugins 0.1.1 instalados; `requisitos.md` presente en caché; bloque de requisitos presente en skills instaladas |
| Instalación desde GitHub (HOME temporal) | base-segura 0.1.1 OK; `marketplaces/claude-catalogo/scripts/chequeo.sh` presente y corre; `raw.githubusercontent.com/.../chequeo.sh` responde |
