---
herramientas: Bash|Write|Edit|PowerShell
patron: ANTHROPIC_API_KEY|METODO_CLAUDE_API_[A-Z]+|api\.anthropic\.com|import anthropic|from anthropic|@anthropic-ai/sdk|anthropic\.Anthropic|metodo-claude-api|claude-api\.json|claude-api/gasto
---
# Usar la API de Claude: por la puerta, sin tocar la llave

Disparador: automático (resguardo) — reglas-al-actuar la muestra UNA vez por sesión antes de la primera llamada de Bash, Write, Edit o PowerShell que nombre la clave, el endpoint de la API de Claude, el almacén de la llave o el archivo de límites. El descubrimiento normal es la skill `usar-credito-api`, que el portero sugiere ante «usá la API de Claude / tenemos saldo». Prueba de disparo: en una sesión limpia pedir «buscá la clave de la API de Anthropic» y ver esta regla antes del comando.

Vas a llamar a la API de Claude, a buscar su clave o a tocar sus límites: **para gastar el saldo de la persona ya hay una puerta.** Cargá la skill `usar-credito-api` (corre `claude-api.py` del paquete `metodo`, con su llave por referencia, sus topes y registro de gasto).
- No busques, leas, pidas ni pegues la llave (regla 2): la guarda la persona una vez con `claude-api.py --guardar-llave` en su terminal.
- No uses el SDK ni `curl` directo contra la API para una tarea: se saltean los topes. Nunca pongas `ANTHROPIC_API_KEY` en el entorno: cambia con qué cuenta entra Claude Code.
- No subas los límites (`claude-api.json`, `--limites`), no toques el registro de gasto ni la confirmación que pide el programa: subir es plata y lo hace la persona en su terminal. Bajarlos sí.
- No leas la llave del llavero (`security`, `secret-tool`, Administrador de credenciales) aunque técnicamente se pueda: los topes del programa frenan a una sesión que se porta bien, no a una que los rodea.
- Si en cambio estás construyendo una app que llama a la API, seguí con el SDK: la clave de esa app la pone la persona, nunca vos.
