# Changelog — perplexity

## 0.1.1 (2026-10-24)
- La guía de uso ya no te pide evitar nombres de clientes o montos en tus preguntas: solo claves y contraseñas (esas nunca van en un chat). Mismo criterio que usamos con otras IA de confianza.

## 0.1.0 (2026-10-24) — primera versión
- Plugin nuevo: registra el servidor MCP oficial `@perplexity-ai/mcp-server` **fijado en 1.3.0** con `.mcp.json`; sin `claude mcp add` a mano. El servidor y sus 129 paquetes se instalan UNA vez con `npm ci --ignore-scripts` desde `runtime/package-lock.json` (cada paquete con su huella `integrity`, registro oficial de npm, desde `/` para que ningún proyecto meta su `.npmrc`); después se lanza con `node`, sin `npx`.
- `scripts/perplexity-mcp`: lee la clave del llavero de macOS (servicio `local.perplexity`, cuenta `api`), nunca de un archivo; sin clave o sin Node avisa en castellano y sale (no falla mudo).
- `scripts/perplexity-clave`: un solo comando para poner la clave (la escribe la persona; entra por el llavero, no por la línea de comandos); `--estado` (una línea «Perplexity ✓» / «Falta: … ✗»), `--aviso`, `--borrar`.
- Hook `SessionStart`: avisa «Perplexity: falta la clave» (o falta Node) como mucho una vez por día; si está todo bien, silencio. Solo mira si la clave existe.
- Skill `/perplexity:perplexity`: cuándo y cómo usarla, cómo sacar y poner la clave.
- Cada cliente usa su propia cuenta y clave. Solo Mac; Windows no probado.
