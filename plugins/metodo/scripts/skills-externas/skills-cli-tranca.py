#!/usr/bin/env python3
"""skills-cli-tranca — hook PreToolUse(Bash) (regla 19 del método).
Frena `npx skills add|update|check|remove|...` (el instalador de Vercel) contra tu carpeta de skills: lo que se trae de afuera entra por
la cuarentena (cuarentena-skills.sh), no por el instalador directo. `find`, `list`, `--help` y `--version` pasan (no instalan nada).
Disparador: A (hook PreToolUse sobre Bash; lo registra solo el plugin, o el instalador de quien mantiene el ecosistema).
Falla conocida: también frena el texto de un comando que nombre esa instrucción (por ejemplo un mensaje de commit); se rodea escribiéndolo
distinto o pasando el mensaje por archivo. No ve un alias ni un script que llame al instalador por dentro: es un cinturón, no un sandbox.
Salida: código 2 + mensaje por stderr = bloquear (convención de hooks de Claude Code)."""
import json, re, sys

INSTALA = re.compile(r"(?:^|[\s;&|(`])(?:npx|pnpx|bunx|pnpm dlx|yarn dlx)\s+(?:-y\s+|--yes\s+)?skills(?:@[\w.\-]+)?\s+(add|a|install|i|update|upgrade|check|remove|rm|r|experimental_install|experimental_sync)\b"
                     r"|(?:^|[\s;&|(`])skills\s+(add|install|update|upgrade|remove|experimental_install|experimental_sync)\b"
                     r"|add-skill\s+\S")
try:
    cmd = (json.load(sys.stdin).get("tool_input") or {}).get("command", "")
except Exception:
    sys.exit(0)
if INSTALA.search(cmd) and "cuarentena-skills" not in cmd:
    sys.stderr.write("BLOQUEADO (skills-cli-tranca): el instalador `skills` no se usa contra tu carpeta de skills. "
                     "Para traer una skill de afuera: /metodo:buscar-skill-externa (cuarentena + auditoría), y recién con tu OK se copia. "
                     "Buscar sí se puede: `skills-buscar` o `npx skills find`.\n")
    sys.exit(2)
sys.exit(0)
