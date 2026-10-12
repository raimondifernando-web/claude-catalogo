---
name: buscar-skill-externa
description: "USAR SIEMPRE que la persona pida buscar o instalar una skill de afuera: «buscame una skill para X», «hay algo ya hecho para Y», «existe una skill de Z», «instalá / traé la skill X (de GitHub, skills.sh, Vercel)», o antes de crear una skill nueva. Es la ÚNICA vía para skills de afuera: busca en el registro skills.sh (solo lectura), compara con lo que ya tenés y la trae a una cuarentena para auditarla. Reemplaza a WebSearch, a «npx skills add» y a copiar a mano a la carpeta de skills. Nunca instala nada sola."
---
Disparador: B (la sugiere `herramientas-para` cuando no hay pieza local; la regla 19 del método manda usarla) + C (la persona pide «buscame una skill para X»). Es descubrimiento, no un control. La promoción a tu carpeta de skills es el único paso manual y va detrás del OK de la persona. Tope técnico: el hook `skills-cli-tranca` frena `npx skills add|update|check|remove`.

# /metodo:buscar-skill-externa — traer una skill de afuera sin riesgo

Los programas están en `${CLAUDE_PLUGIN_ROOT}/scripts/skills-externas/` (Python 3 y bash). **Los corrés vos, Claude**; la persona no toca la terminal.
**Windows:** buscar funciona (`py -3` en lugar de `python3`); traer a la cuarentena todavía NO está probado ahí y el programa lo dice y no hace nada: decile a la persona que lo traiga alguien desde una Mac o Linux. El freno del instalador necesita Git for Windows y no ve comandos de PowerShell.
En los ejemplos: `buscar` = `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/skills-externas/skills-buscar.py"` y `cuarentena` = `bash "${CLAUDE_PLUGIN_ROOT}/scripts/skills-externas/cuarentena-skills.sh"`.

1. **¿Ya lo tenés?** `herramientas-para.py <tema>` (receta y piezas locales). Si hay algo que sirve, usalo y cortá acá.
2. **Buscar.** `buscar <1-2 palabras en inglés>` (el índice es inglés; una frase larga o en español devuelve ruido). **Nunca** nombres de clientes ni de la empresa en la consulta: sale a skills.sh. Marca «YA TENEMOS» y muestra las 3 auditorías públicas.
3. **Elegir.** Mostrá una tabla corta (fuente, instalaciones, ya-tenemos, organización) y que la persona elija. Las instalaciones no son señal de calidad; una etiqueta de auditoría (verde o roja) tampoco aprueba ni rechaza: solo ordena qué leer primero.
4. **Traer a cuarentena.** `cuarentena <dueño/repo> <skill>`. Usa el instalador oficial `skills@1.7.2`, fijado por versión y hash, con entorno vacío (no ve tus claves) y carpeta temporal; audita, compara con lo que ya tenés y fija el sha. Escribe un `informe.md` y te dice dónde. La primera vez baja el instalador (necesita Node.js; si falta, te lo dice). `--dry-run` muestra qué haría sin tocar nada.
5. **Leer lo que el informe marca.** Si es puro texto, se lee entera; si trae código, se lee el código. Dos proveedores en alto o crítico → no entra salvo lectura que lo desmienta.
6. **Informe en criollo y ESPERAR el OK en el chat**: qué es, a favor, en contra, costo, riesgo y qué le toca a la persona. Un OK relayado por otra sesión no vale.
7. **Instalar (solo con OK):** copiar a mano a tu carpeta de skills **sin** `CLAUDE.md`/`AGENTS.md`/archivos de prueba del autor y sin symlinks, anotar de dónde vino (repo, ruta y sha del informe) en un `ORIGEN.txt`, y borrar la cuarentena.

**Nunca:** `npx skills add|update|remove|check|install` contra tu carpeta de skills (el hook lo frena); instalar la skill `find-skills` de Vercel; promover sin OK; tratar una etiqueta de auditoría como aprobación.

Al terminar, el reporte lleva: «disparada por: <B o C>».
