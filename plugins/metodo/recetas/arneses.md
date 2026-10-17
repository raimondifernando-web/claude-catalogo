---
name: arneses
triggers: arnes arneses harness hook hooks permisos permissions deny allowed-tools sandbox settings frenar freno secretos claude-md subagente subagentes skill skills listado configurar proteger
---
Receta arneses (2026-10-11). Cada regla lleva su fuente oficial; verificada contra la página el 2026-10-11.
«Arnés» = todo lo que rodea al modelo (hooks, permisos, instrucciones, skills, sandbox). Antes de configurar uno, leé la regla que toca. Si una página oficial cambia, la regla se re-cuestiona y la receta se actualiza con el catálogo; nada se aplica solo. Secretos en general: receta `seguridad-y-secretos`.

**Barreras (secretos y permisos)**
- A1. Un freno de texto sobre Bash no alcanza: las herramientas de archivos (Read, Grep) lo esquivan. Las reglas `deny` de Read/Edit cubren las herramientas de archivos, comandos como `cat/head/tail/sed/tee` y las redirecciones; no cubren un comando que lee sin nombrar el archivo. Fuente: code.claude.com/docs/en/permissions.md (sección Read and Edit).
- A2. Una regla de Bash compara el texto del comando, no el programa: otra forma de invocarlo la esquiva. No es una frontera de seguridad. Fuente: permissions.md (sección Bash).
- A3. Orden de evaluación: deny, luego ask, luego allow; un `allow` no abre una excepción dentro de un `deny`. Fuente: permissions.md.
- A4. Para esconder credenciales a los comandos (archivos y variables): sandbox con `credentials` / `filesystem.denyRead`. Por defecto el sandbox deja leer `~/.ssh` y `~/.aws/credentials`. Probar antes: puede cortar git/gh. Fuente: sandboxing.md.
- A5. Medido (no oficial, 2026-10-11): una regla `deny` sobre los archivos de entorno también rompe `grep -c '^VAR=' <archivo>`, la forma segura de verificar que una variable existe. Por eso esos archivos van al freno (hook) y los otros almacenes de llaves (`~/.ssh`, etc.) a `deny`.
- A6. Un hook no ve lo que entra por `@archivo` en el prompt (no hay llamada a herramienta). Dos salidas: una regla `deny Read(...)` para esas rutas, o `CLAUDE_CODE_DISABLE_FILE_MENTIONS=1` (Claude recibe solo la ruta y la lee con sus herramientas, así que los hooks `Read` sí corren; pide Claude Code ≥ 2.1.299; se ignora en settings de proyecto y locales: va en el shell, los settings de usuario o los gestionados). Fuente: hooks.md (PreToolUse).
- A7. En Windows con PowerShell los comandos llegan por otra herramienta: el matcher debe ser `Bash|PowerShell`; un freno solo de Bash no ve nada. Fuente: hooks.md.

**Hooks y avisos**
- B1. Un hook que sale con 0 no le muestra su stderr a Claude: un aviso por stderr no lo ve nadie. Para avisar a la persona: `systemMessage` en JSON. Fuente: hooks.md (exit codes y JSON output).
- B2. Para que un hook que falla bloquee la acción en vez de dejarla pasar: `onFailure: "block"` (pide Claude Code ≥ 2.1.295). Fuente: hooks.md.
- B3. Los hooks son deterministas («valen decida lo que decida Claude»); el CLAUDE.md es consultivo. Lo que no puede fallar va a un hook; lo que orienta, al CLAUDE.md. Fuente: best-practices.md.
- B4. Hooks declarados en el encabezado de una skill quedan activos el resto de la sesión una vez invocada; revisar que apunten a archivos que existen. Fuente: hooks.md («Hooks in skills and agents»).

**Skills y paquetes**
- C1. `allowed-tools` en una skill aprueba esas herramientas sin preguntar durante el turno, y una skill puede darse permisos amplios a sí misma: revisarlo en las ajenas y limitarlo (`Bash(programa *)`, no `Bash`). Fuente: skills.md.
- C2. Un paquete (plugin) no puede traer reglas `deny` por su `settings.json`: solo `agent` y `subagentStatusLine` hacen efecto. Las reglas de bloqueo se entregan por otra vía (instalador o ajustes del usuario). Fuente: plugins-reference.md.
- C3. El listado de skills tiene un tope (por defecto 1 % de la ventana): pasado el tope se conservan los nombres y se pierden descripciones, y Claude elige peor. Fuente: settings-reference.md (`skillListingBudgetFraction`).

**Instrucciones y costo**
- D1. CLAUDE.md: menos de 200 líneas; lo de una carpeta, a una regla con `paths:`; MEMORY.md carga solo las primeras 200 líneas o 25 KB. Fuente: memory.md.
- D2. Las reglas con `paths:` y los CLAUDE.md anidados se vuelven a cargar a demanda tras compactar; el CLAUDE.md de la raíz se re-inyecta. Las reglas de usuario en `~/.claude/rules/` valen para todos los proyectos. Fuente: memory.md.
- D3. Todo subagente propio carga los CLAUDE.md salvo que tenga `omitClaudeMd: true` (pide ≥ 2.1.271; Explore y Plan tampoco los cargan). Con `omitClaudeMd` igual entran los de política gestionada y el CLAUDE.md de un subdirectorio cuando trabaja con archivos de ahí; la sesión principal sí tiene todo, así que una regla que el subagente deba cumplir se repite en el pedido. Para especialistas de solo lectura, apagarlo ahorra contexto. Fuente: sub-agents.md.

**Cómo se usa**
1. Si vas a tocar hooks, permisos, skills ajenas, CLAUDE.md o sandbox, leé la regla del bloque.
2. Si algo quita o restringe: propuesta con tabla «qué pierde cada uno» y OK de la persona antes de aplicar. Lo que solo agrega protección se puede aplicar y avisar.
