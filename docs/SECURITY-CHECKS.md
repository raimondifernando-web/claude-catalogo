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
