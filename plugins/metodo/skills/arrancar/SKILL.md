---
name: arrancar
description: "Protocolo de arranque de sesión: leer el estado, confirmar el rol y verificar el entorno ANTES de tocar nada. Usala cuando el usuario escriba 'arrancá', 'empecemos', 'seguimos', 'continuá donde quedamos', al abrir una sesión nueva (con o sin prompt de reanudación pegado), o al empezar a trabajar en un tema por primera vez. Es el espejo de /metodo:cerrar."
---

# /metodo:arrancar — Arrancar leyendo, no adivinando

Una sesión que arranca mal re-hace trabajo, vuelve a discutir decisiones tomadas y pisa lo que otra sesión dejó. Este protocolo cuesta dos minutos y evita todo eso.

**Cuidá el cupo:** cada llamada al modelo relee todo lo que ya está en la conversación, así que lo caro son las vueltas y lo que queda cargado. Por eso el arranque son **3 vueltas** (leer y chequear · título · confirmar), y **no se pide la lista completa de sesiones de la app** (`list_sessions`: decenas de miles de caracteres de todas las carpetas): el chequeo ya calcula lo que hace falta desde el disco. Tampoco releas archivos largos "por las dudas".

## Vuelta 1 — en UN mensaje, todo en paralelo, antes de tocar nada
1. Leé **`REANUDAR.md` en la carpeta de trabajo** (la carpeta donde está abierta esta ventana; si es una copia de `/metodo:otra-sesion`, la de esa copia — cada una tiene el suyo). Si el usuario pegó un texto de arranque (bloque `═══ PARTE A`), gana el pegado.
2. Corré `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/arrancar-check.py"` (en Windows, `py -3`). Solo lee: una línea ✓/✗ por paso (cierre anterior, copia y rama contra lo declarado, estado de git, método instalado) y calcula el título nuevo y las sesiones anteriores abiertas. **Prohibido confirmar sin haberlo corrido** (las sesiones se saltaban pasos escritos; esto los vuelve visibles). Si no se puede correr, decilo: no lo simules.
3. Corré `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/radar.py" aviso` (Windows: `py -3`). Si imprime una línea («Radar: el radar de modelos tiene N días…», «se retira X el …»), sumala tal cual a la confirmación. Si no imprime nada, no digas nada. Nunca falla ni espera la red: si da error, seguí sin avisar.
4. Si vas a numerar y las herramientas de sesiones de la app (`ccd_session_mgmt`) vienen diferidas, cargá `set_session_title` y `archive_session` con `ToolSearch` (`select:mcp__ccd_session_mgmt__set_session_title,mcp__ccd_session_mgmt__archive_session`) en este mismo mensaje. Si no existen (terminal, Cowork, otra máquina), saltá la numeración sin avisar.

## Con lo leído (sin más llamadas)
- **Contrato.** Con texto de arranque, la PARTE A es tu contrato: tu rol, alcance y reglas salen de ahí, no de tu intuición. Decile al usuario de dónde lo tomaste y de cuándo es («Levanté el cierre del [fecha-tema] de `REANUDAR.md`»); si es viejo para el ritmo del proyecto, avisalo: el estado puede haber cambiado y los archivos mandan. Sin contrato (no hay archivo ni texto pegado; no lo inventes): reconstruilo con el `CLAUDE.md` de la carpeta de trabajo + el último archivo de `handoffs/`, y declará «Voy a trabajar como [rol] sobre [tema]».
- **De qué veníamos hablando.** Si la PARTE B trae esa línea, es lo primero que decís en la confirmación («Veníamos con …»): es la memoria de la charla anterior, y «lo último que hiciste» del usuario se refiere a eso. Si no la trae (cierre viejo), leé la sección final del último handoff antes de contestar cualquier pregunta sobre «lo anterior»; nunca respondas «en esta sesión no hice nada» sin haberlo mirado.
- **Estado.** Las decisiones ya tomadas NO se reabren (si creés que una está mal, lo decís una vez, con evidencia, y seguís). Leé el último handoff del tema solo si el texto lo cita o lo necesitás. Los ítems **A VERIFICAR** del texto son TUYOS: ejecutalos temprano.
- **Entorno (el archivo manda sobre la memoria).** El chequeo compara `pwd` y rama contra el `Copia: <ruta> · Rama: <tema/fecha>` de la PARTE B. Si dice ✗ → **PARÁ y avisá**: «Este texto es para la copia X en la rama Y, y estoy en Z. No trabajo en la copia equivocada: abrí la ventana en la carpeta correcta o dame el texto de esta.» Trabajar en la copia equivocada pisa a otra sesión. Si no declara copia y hay otra sesión abierta sobre el mismo proyecto (el chequeo avisa si `git worktree list` muestra más de una), proponé abrir ésta con `/metodo:otra-sesion` (regla 11). Además: ¿las herramientas que vas a usar están disponibles? (si no, avisá, no simules); cualquier número que uses, contalo ahora.

## Vuelta 2 — en UN mensaje, en paralelo (solo si el entorno está bien)
- **Título** (app de escritorio): si el chequeo trae una línea `TÍTULO:`, ejecutala (`set_session_title("self", …)`: ya calculado desde la misma carpeta y la misma serie, con el mismo ancho: «03»→«04», «99»→«100»). Si dice que la sesión ya está numerada, no la toques (alguien la nombró). Si dice «sin serie», no inventes una. Mencioná el nombre nuevo en la confirmación.
- Los probes de **A VERIFICAR**.
- **Sesiones anteriores abiertas:** si el chequeo lista `SESIONES ANTERIORES SIN ARCHIVAR`, no las archives por tu cuenta: sumá una línea a la confirmación («Hay N sesiones anteriores de "<base>" abiertas (<n1>, <n2>…). ¿Las archivo? Se pueden recuperar cuando quieras.») y archivá (`archive_session`) **solo si el usuario dice que sí**. Nunca elimines una sesión. La app rechaza sola las que están trabajando.
  **Excepción:** si te abrió un `/cerrar` (tu brief dice «Sesión abierta sola por /cerrar») y la app rechaza archivar la anterior por «still working», es lo esperado: `/cerrar` se archiva ella misma al terminar su turno. No insistas: dejá una línea «la anterior se archiva sola» y, al confirmar, verificá que ya no figure; si sigue ahí, ofrecé archivarla como en la regla de arriba (con el sí del usuario).

## Vuelta 3 — confirmar y arrancar
Pegá solo las líneas ✓/✗ del chequeo y, debajo, **una línea por cada ítem MANUAL y por cada A VERIFICAR con su resultado real** (incluida la del modelo: «este paso pide X, estás en Y»). Si termina en «Falta: … ✗», resolvelo y volvé a correrlo. Si la carpeta (o la raíz de su repo) tiene `.claude/PENDIENTES.md`, corré `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/pendientes.py" --prio1` (si no tenés `CLAUDE_PLUGIN_ROOT`, buscá el script con `find "${CLAUDE_CONFIG_DIR:-$HOME/.claude}/plugins/cache/claude-catalogo/metodo" -name pendientes.py | sort -V | tail -1`) y sumá lo que imprime (hasta 3 líneas de prioridad 1 abiertas; si hay más, «y N más: /metodo:pendientes»). Si no hay archivo, no digas nada. Después, en 2-3 líneas: **«Leí el estado. El próximo paso es [X]. ¿Arrancamos?»** Si el texto ya trae el próximo paso definido y contexto suficiente, arrancá directo: la confirmación es para alinear, no para pedir permiso de trabajar.

## Reglas del arranque
- **Nada de escribir antes de resolver el entorno.** Ni "mejoras rápidas" ni limpiezas oportunistas fuera de lo pedido.
- **Si algo del estado contradice los archivos, ganan los archivos**, y lo avisás (el estado puede estar viejo; el disco no).
- **Si la carpeta de trabajo no tiene `CLAUDE.md`**, eso es lo primero: proponer crearlo (plantilla en `base-segura/templates/CLAUDE-empresa.md`).

## Qué NO es esta skill
No reemplaza a `/metodo:cerrar` (cierre), `/metodo:planear` (planificación) ni `/metodo:otra-sesion` (abrir una segunda sesión sin pisarse). Es solo la apertura. Atajo: si no tenés otra skill llamada `arrancar`, `/arrancar` a secas también la activa.
