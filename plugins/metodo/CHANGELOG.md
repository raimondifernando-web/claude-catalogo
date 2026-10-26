# metodo — qué cambia para vos

## 0.57.2 — 2026-10-26
**La numeración de sesiones ya respeta el emoji del título y las copias «(fork)».** Se aplica solo con la actualización; no hay nada que correr.
- **El problema:** si el título de la serie empezaba con un emoji («🧬 PROYECTO. 04»), la sesión nueva salía sin él («PROYECTO. 05») y el arranque no reconocía la serie: decía «sin serie numerada» y no archivaba la anterior. Lo mismo pasaba si el cierre lo hacía una copia llamada «… 04 (fork)».
- **Qué cambia:** la serie se reconoce por el nombre sin adornos al principio ni «(fork)» al final. El título nuevo conserva el emoji de la serie (y corrige el de una sesión que nació sin él), y las anteriores —incluidas las copias— se mandan a archivar. Anchos «03»→«04» y «99»→«100» siguen igual. `/cerrar` ahora pide abrir la sucesora con el mismo adorno.

## 0.57.1 — 2026-10-26
**El medidor de Codex ahora ve el tope de 5 horas del plan Plus.** Se aplica solo con la actualización; no hay nada que correr.
- **El problema:** cuando Plus se agota, Codex no deja porcentajes en su registro: deja solo el aviso «You've hit your usage limit … try again at <fecha>». El medidor decía «cupo desconocido» y dejaba lanzar trabajo que iba a fallar.
- **Qué cambia:** si lo último que dijo Codex es ese aviso, el medidor informa «agotado hasta <fecha>» y frena; pasada la fecha, vuelve a dejar lanzar. Si hay una medición más nueva, manda la nueva. El radar y `delegar.py` usan este mismo medidor, así que quedan arreglados. Con prueba nueva.

## 0.57.0 — 2026-10-25
**Cuando le pasás trabajo a Codex o a Gemini, ahora reciben las guías (skills) que el pedido nombra.** Se aplica solo con la actualización; no hay nada que correr.
- **El problema:** Codex y Gemini no ven tus skills; reciben solo el texto del pedido. Si decías «hacelo con la skill X», la otra IA no sabía qué decía X y trabajaba sin la guía.
- **Qué cambia:** `delegar.py` mira qué skills nombra el pedido (`/nombre`, «skill nombre») o cuáles pedís con `--skills a,b`, y pega su texto al principio del pedido (hasta 12 KB cada una, 24 KB en total). No instala nada en la otra IA. Si la guía usa conectores de Claude que la otra IA no tiene, te avisa y conviene que lo haga un agente de Claude. Las skills de la sesión (arrancar, cerrar…) y las que traen algo con forma de clave no se pegan. Se apaga con `GUIAS_OFF=1`.
- **Regla 22 y receta de arneses:** ahora dicen quién hace cada trabajo: diseño, seguridad, textos en castellano y todo lo que usa conectores van a su agente especialista de Claude; programar algo mecánico con una prueba clara va a Codex o Gemini con las guías pegadas.

## 0.56.0 — 2026-10-25
**Si le pedís una skill a un ayudante que no puede cargarla, Claude te avisa antes de perder el trabajo.** Se aplica solo con la actualización; no hay nada que correr.
- **El problema:** muchos ayudantes que vienen en paquetes de afuera (los de VoltAgent: swift-expert, python-pro, etc.) no tienen la herramienta para cargar skills. Si el pedido decía «usá la skill X», el ayudante volvía con «no pude cargarla» o, peor, seguía sin la guía y nadie se enteraba.
- **Qué cambia:** antes de abrir un ayudante, un aviso automático mira si el pedido nombra una skill y si ese ayudante puede cargarla. Si no puede, frena UNA vez y propone dos salidas: otro ayudante del mismo oficio que sí la carga, o pasarle la ruta de la guía para que la lea. Si reintentás el mismo pedido, pasa. Si el ayudante sí puede, no dice nada.
- **Regla 22 (más precisa):** ahora dice que antes de nombrar skills hay que mirar que el ayudante tenga la herramienta `Skill`. Se apaga con `SKILL_EN_AGENTE_OFF=1`.

## 0.55.1 — 2026-10-25
**El medidor de cupo de Codex ahora anda con cualquier plan (gratis o Plus).** Se aplica solo con la actualización; no hay nada que correr.
- **El problema:** `codex-cupo` solo sabía leer la ventana de 30 días del plan gratis. Con Plus, Codex mide por ventanas de 5 horas y de 7 días, así que el medidor no encontraba el dato y podía marcar «agotado» sin estarlo, frenando el reparto de trabajo.
- **Qué cambia:** toma la última medición de Codex y usa la ventana más llena de las que haya. El radar y `delegar.py` usan ese mismo medidor, así que quedan arreglados también. Con prueba para los dos tipos de registro.

## 0.55.0 — 2026-10-24
**Las reglas del método pesan la mitad en cada sesión: quedan todas, cada una en lo esencial.** Se aplica solo con la actualización; no hay nada que correr.
- **El problema:** el bloque de reglas va en tu `~/.claude/CLAUDE.md`, y ese archivo se lee entero al abrir cada sesión y cada vez que Claude lanza un ayudante. Con 25 reglas largas eran unos 21 KB (cerca de 9.000 unidades de texto) leídos una y otra vez antes de empezar a trabajar.
- **Qué cambia:** tu ficha lleva ahora la versión corta (unos 11 KB): cada regla en lo esencial, con todos sus números (umbrales de cupo, tope de vueltas, el 85 % de la copia, etc.). El texto completo, con ejemplos y comandos, queda en `REGLAS-DEL-METODO-COMPLETO.md` del paquete, y la versión corta dice cómo encontrarlo cuando una regla toca lo que vas a hacer.
- **Dos agregados:** la regla 2 suma la revisión de seguridad en los momentos de riesgo (antes de publicar o entregar una herramienta, después de tocar claves o servidores, al arrancar un proyecto), con informe sin valores y freno si hay algo grave. La regla 13 ya decía que hay que avisar por escrito a la otra sesión; la versión corta lo conserva.
- **Qué NO cambia:** los números de las reglas, lo tuyo fuera del bloque y la copia de respaldo que se guarda antes de cada cambio.

## 0.54.2 — 2026-10-22
**`mapa carpetas`: la lista de tus carpetas de proyecto, siempre al día.** Se aplica solo con la actualización; no hay nada que correr.
- **Qué te da:** `mapa carpetas` lista las carpetas reales de `~/Proyectos` (una línea por carpeta: tipo · grupo · nombre · ruta), con tipo (**activo**, **dormido** si cuelga de `Personal/`, **archivo** si está en `_archivo/`), grupo (la empresa o área de arriba) y un nombre legible. Con `--tipo`, `--grupo` o `--json` se filtra o se pasa a otro programa. Ninguna herramienta tiene que armar esa lista por su cuenta.
- **Qué cuenta como carpeta de proyecto:** la regla de siempre de la estructura (una carpeta con `.git` o con `CLAUDE.md`; en la raíz toda carpeta cuenta); no entran las que empiezan con `.` o `_` ni los enlaces, así que las copias de trabajo temporales y lo que ya se borró no aparecen.
- **Por qué importa para el rendimiento:** esas copias temporales ya no cuentan como cambio, así que el mapa se rehace menos (en el día de prueba con muchas sesiones en paralelo, 19 de 27 rehacer venían de copias de trabajo nuevas). La lista de proyectos con piezas de Claude (`proyectos`) tampoco las incluye.

## 0.54.1 — 2026-10-22
**La lista de pendientes calcula la prioridad con una cuenta que da más peso a lo que rinde, y el control avisa de dos descuidos.** Se aplica solo con la actualización; no hay nada que correr y tus listas siguen funcionando igual.
- **La cuenta:** la prioridad (Prio) sale de `2 × impacto − esfuerzo`, con Bajo 1 · Medio 2 · Alto 3 (antes era `impacto − esfuerzo`). Se sigue escribiendo el dígito: 1 = Alta (3 o más), 2 = Media (1 o 2), 3 = Baja (0 o menos). Así lo de impacto Alto sale Alta aunque cueste, y lo de impacto Bajo no sale Alta. La plantilla de la lista y el paso «Pendientes» de `/metodo:cerrar` ya lo explican.
- **Dos avisos nuevos en el control de la lista** (solo avisan, nunca frenan un cierre): una fila que dice `parte de X` cuando X no es un proyecto de la tabla (no existe, se cerró o no empieza con `Proyecto:`), y una tarea abierta con esfuerzo Alto («¿es un proyecto?»). Los valores viejos (chico, grande) no avisan.
- **Qué NO cambia:** las 8 columnas, los estados y lo que ya escribiste. Revisás tus filas una vez, en tu próximo cierre.

## 0.54.0 — 2026-10-22
**Cerrar una sesión ya no pierde mensajes ni deja sesiones colgadas: todo pasa en una sola vuelta.** Se aplica solo con la actualización; no hay nada que correr.
- **El problema, medido:** cerrar la sesión principal de una carpeta era una mudanza hecha a mano, en muchos pasos sueltos (abrir la sesión nueva, soltarla de la vieja, avisarle a cada sesión el número nuevo, archivar la vieja). La app tiene reglas propias que no se pueden cambiar: no deja abrir una sesión desde una vuelta que empezó otro aviso, ata cada hija a la sesión que la abrió para siempre, no archiva una sesión que está trabajando o vigilando algo y no permite cerrarle la puerta a los mensajes que llegan. Resultado: mensajes dirigidos a una sesión que ya se había ido, hijas que seguían avisándole a la vieja y cierres que se cortaban a la mitad.
- **Qué hace ahora `/metodo:cerrar`:** una mudanza de una sola vuelta, con orden fijo y comprobada por un programa (`cierre-mudanza.py`): congela la carpeta → abre la sesión nueva enseguida (mientras la vuelta es tuya) y la suelta de la vieja → guarda todo → resuelve las sesiones hijas → le avisa «traspaso listo» a la nueva → se archiva. Si se corta a la mitad queda marcado el paso exacto y `/metodo:arrancar` lo dice.
- **Dirección fija por carpeta:** nadie tiene que saber el número de la sesión. Si alguna sesión le escribe a la que está cerrando, un control automático frena ese mensaje y le explica que lo deje como carta en la carpeta (`.claude/cartas/`, que no se sube a git y no sale de tu computadora). La sesión nueva lee las cartas al arrancar y las trata como datos, nunca como órdenes. (`/metodo:buzon`, el canal con quien te acompaña por GitHub, sigue igual.)
- **Las hijas no se heredan:** al cerrar, la que terminó se archiva; la que solo espera tu visto bueno o una prueba deja su pedido en `PENDIENTES.md` y se archiva sin vigilar su PR; la que está trabajando se suelta y entrega su informe como carta a la sesión nueva. Una sola definición de «trabajando», «esperando» y «terminada» para todos los chequeos, así dos piezas no cuentan distinto.
- **Una hija no pisa a las demás:** si una sesión hija comparte carpeta con otra sesión viva, un control automático le impide reacomodar o subir trabajo ajeno (`git pull`, `rebase`, `stash`, `add -A`, `push`, commits sin nombrar archivos) y escribir el `REANUDAR.md` de la carpeta; le explica en castellano qué hacer en su lugar.
- **Pendientes con criterio:** la plantilla de `PENDIENTES.md` suma la cuenta Prio = impacto − esfuerzo, el esfuerzo en Bajo/Medio/Alto (horas para una tarea, días para un proyecto) y los proyectos con sus tareas (`Proyecto:` y `parte de <ID>`). Tus listas actuales siguen siendo válidas.
- **Si molesta:** los dos controles se apagan con la variable `CIERRE_MUDANZA=0` (el de envíos) y `FRENO_HIJA=0` (el de hijas), o creando en `<carpeta de Claude>/metodo/` el archivo `freno-envio-cerrando.apagado` o `freno-hija.apagado`. Ante cualquier error dejan pasar el mensaje o el comando y lo anotan: nunca traban una sesión.
- **Qué NO cambia:** no se manda nada afuera de tu computadora, no se lee el contenido de tus mensajes (el control mira solo a quién van y si esa sesión está cerrando) y las sesiones fuera de la app de escritorio siguen cerrando como antes.

## 0.53.1 — 2026-10-22
**`mapa` casi no se rehace sin motivo, y `herramientas-para` ahora busca en el mapa.** Se aplica solo con la actualización; no hay nada que correr.
- **El problema, medido en una computadora de trabajo real durante 3 horas:** el mapa se rehacía 41 veces de cada 45 consultas, casi siempre por cambios que no cambian nada del mapa: la marca `.git` de cada repositorio (cambia con cada commit), dos archivos que la app reescribe sola con fechas (`known_marketplaces.json` y `mcp-needs-auth-cache.json`) y carpetas temporales de copias de trabajo. Seguía dando el resultado correcto, pero gastaba un par de segundos de más.
- **Qué cambia:** el mapa ya no mira la fecha de esas cosas. Pregunta «¿existe?» donde solo importa eso, compara solo los nombres de los archivos que la app reescribe, y en `~/Proyectos` solo vigila lo que de verdad lee (carpetas `.claude` y archivos `.mcp.json` hasta la profundidad que mira). Medición después del arreglo: 0 rehacer en 26 consultas seguidas (antes 41 de 45).
- **`herramientas-para` busca en el mapa:** cuando vas a construir algo y `herramientas-para <tema>` te muestra «qué hay ya hecho», las skills y agentes salen de la misma lista que `mapa buscar`: siempre al día (una skill creada hace un minuto aparece) y sin duplicados de versiones viejas de plugins. Si el mapa no se puede leer, vuelve solo al recorrido de antes: nunca se queda sin contestar.
- **Qué NO cambia:** lo que ves en pantalla (mismo formato), las recetas, el freno de la regla 22 y el resultado del mapa (se comparó contra el programa anterior).

## 0.53.0 — 2026-10-22
**Nuevo comando `mapa`: te dice qué skills, agentes, conectores, reglas y programas tenés instalados, siempre al día y sin gastar IA.** Se aplica solo con la actualización; no hay nada que correr y no se instala nada que arranque solo.
- **Para qué sirve:** antes de armar algo, `mapa buscar <tema>` te muestra qué hay ya hecho (nombre, qué hace en una línea y dónde vive). `mapa` a secas da un resumen corto (cuántas piezas de cada tipo y las últimas que cambiaron); `mapa ver <pieza>` abre la ficha de una; `mapa --al-dia` dice si el mapa coincide con tu disco.
- **Cómo se mantiene fresco sin que nadie avise:** cada vez que lo consultás compara una «huella» de lo que miró la vez anterior (cuesta una décima de segundo); solo si algo cambió se rehace (unos 2 segundos). Detecta una skill nueva, un plugin instalado desde la app, un conector agregado, un proyecto nuevo con su carpeta `.claude`. No hay vigilantes ni tareas programadas.
- **Qué guarda y dónde:** una carpeta `mapa/` dentro de la carpeta de Claude, con permisos solo para vos. Solo nombres, descripciones y fechas: nunca claves, variables de entorno ni argumentos de los conectores, y tapa cualquier cosa con forma de clave. Dos sesiones a la vez no se pisan (candado y escritura a un archivo temporal que se renombra).
- **Qué NO cambia todavía:** nada de lo que ya usás. En una próxima versión `herramientas-para` y el aviso de piezas nuevas pasan a leer este mapa; hoy conviven.
- **Si molesta:** no hay nada que apagar; si no lo invocás, no corre.

## 0.52.0 — 2026-10-22
**Regla 13: cuando lo que hiciste lo usa otra sesión, se le avisa por escrito.** Si trabajás con varias sesiones a la vez, una puede cambiar algo que otra necesita (una regla, algo publicado). Ahora la regla 13 pide dejarle un aviso en su carpeta (`.claude/prompts/`, qué cambió y qué le toca hacer) y, si está abierta, un mensaje directo: la otra sesión no revisa su carpeta sola. Se aplica solo con la actualización; no hay nada que correr.

## 0.51.4 — 2026-10-21
**Antigravity (Gemini) ya no te abre el navegador de Google cuando vuelve la conexión o se despierta la computadora.** Se aplica solo con la actualización; no hay nada que correr.
- **El problema, medido:** `agy` renueva su permiso de Google cada hora. Si en ese momento no hay internet (la compu recién despierta, el wifi se cayó), en vez de esperar abría el login de Google en el navegador y se quedaba colgado. Pasó 29 veces en 16 días, con la sesión perfectamente vigente.
- **Qué cambia:** `radar.py` y `delegar.py` no llaman a `agy` si no hay conexión con Google. Si `agy` igual se cuelga o pide iniciar sesión, lo dejan en pausa un rato y no lo vuelven a llamar: 15 minutos si el registro de esa corrida muestra un error de red (lo habitual), 30 si no hay dato, 24 horas solo si pidió el navegador sin error de red. Si entrás a mano con `agy`, se reanuda solo, sin pasos extra.
- **Un solo aviso:** si queda en pausa, `radar.py hoy` te lo dice una vez; si de verdad hace falta volver a entrar a Google, abrís `agy` una vez y se reanuda solo [manual-ok: iniciar sesión en Google solo puede hacerlo la persona]. `delegar.py` sale con el código 75 y dice por qué en vez de abrir el navegador.
- **Qué NO cambia:** nada de tu sesión ni de tus claves; solo se mira si hay conexión y se anota la hora del último pedido de login en `~/.cerebro` (o en `~/.cache/metodo` si no existe).

## 0.51.3 — 2026-10-19
**Tus robots de GitHub no se comen los minutos del mes, y te enterás antes de llegar al tope.** Se aplica solo; no hay nada que correr.
- **Regla 25 (nueva):** un workflow de GitHub Actions nace barato y silencioso. En un repositorio privado GitHub cobra los minutos y, al llegar al tope del plan, los robots se frenan justo cuando hacen falta. Ahora todo workflow nuevo (o que se toca) corre en Linux, cancela la corrida vieja cuando llega una nueva, explica por qué tiene un reloj (`cron`) y no corre más seguido que cada hora, trae un tiempo máximo y no corre dos veces por cada cambio. Si algo no se puede, se deja escrito el motivo en el mismo archivo y se ve en el PR.
- **Lo comprueba solo:** el programa `workflow-lint.py` revisa los workflows que cambia cada PR (en el control `controles` del catálogo y, si tu repo lo usa, en el tuyo). Para revisar todo un repo a pedido: `workflow-lint.py --todo`.
- **Aviso temprano de minutos:** al arrancar cada sesión, `actions-consumo.py` te avisa cuando llevás el 60 %, el 80 % y el 90 % de los minutos del ciclo (una vez por escalón). Es una estimación hecha sumando las corridas de tus repos privados: la llave de Claude no puede leer la facturación de GitHub. Asume plan Pro (3.000 min) y que el ciclo se renueva el día 4; si tu plan o tu fecha son otros, se cambian con `ACTIONS_CUPO_MIN` y `ACTIONS_CICLO_DIA`. Si no tenés `gh` instalado o con sesión iniciada, no avisa nada.
- **Se prueba en un repo privado antes de desplegar.** Toda automatización de GitHub (un workflow, un ruleset, un script que instala algo en varios repos) se prueba primero de punta a punta en UN repo privado real, sin dejar restos, y recién con eso en verde se lleva a los demás: un repo público o una prueba local no reproducen lo que pasa en uno privado. El PR lo declara en una línea `Probado-en:` y el control lo exige cuando corresponde (`probado-en.py`).
- **Receta nueva `workflows-baratos`** (la muestra `herramientas-para` cuando vas a crear un workflow o un robot programado): cuándo no hace falta Actions, la plantilla mínima y qué hacer si ya estás cerca del tope. Subir de plan o poner un tope de gasto lo decidís vos, con el costo a la vista.

## 0.51.2 — 2026-10-19
**El panel «Tareas» de la derecha vuelve a llenarse y a ponerse en verde.** Se aplica solo: «Poner todo al día» (que corre sola una vez por día) agrega una línea a tu configuración; no tenés que correr nada. Rige para las sesiones **nuevas** (las que ya están abiertas no cambian).
- **El problema, medido:** con los modelos nuevos (Sonnet 5.5, Opus 5.5) Claude Code deja afuera las herramientas con las que Claude arma y tilda su lista de tareas. Sin ellas, el panel quedaba vacío en todas las sesiones y nada se ponía en verde. Medido en una sesión limpia: sin el ajuste no traía `TaskCreate`/`TaskUpdate`/`TaskList`; con el ajuste, sí.
- **Qué cambia:** `al-dia` deja prendida `CLAUDE_CODE_ENABLE_TODO_TOOLS=1` en la sección `env` de tu `settings.json` (con copia de cómo estaba, y queda en el aviso diario). Es una variable oficial de Claude Code que solo lee él.
- **Costo:** las definiciones de esas herramientas ocupan un poco de espacio en cada sesión.
- **Si molesta:** borrá esa línea de `env` en tu `settings.json`.

## 0.51.1 — 2026-10-19
**Cuando lanzás tareas en otras sesiones, la sesión principal ya no te llena de mensajes: a cada aviso de una sesión hija contesta con un solo mensaje corto y, cuando llegó la última, con un resumen fijo.** Se aplica solo con la actualización; no hay nada que correr.
- **El problema, medido:** después de un aviso de una sesión hija, la gente decía «no entiendo / resumime / me perdí» el 19 % de las veces (contra 8 % sin avisos). En todos esos casos la sesión había mandado varios mensajes seguidos, casi siempre largos y con palabras técnicas.
- **Qué hace ahora:** si todavía trabajan otras sesiones hijas, una sola línea («Llegó lo de X. Falta Y; por ahora no tenés que decidir nada»). Cuando llega la última, un bloque fijo que junta todo: **Resumen** (2-3 líneas, sin jerga) · **Mi sugerencia** (una) · **Qué tenés que decidir vos** (una pregunta con recomendación, o «Nada, no tenés que hacer nada»). Un aviso de plata, datos o algo que no se puede deshacer va antes y nunca se recorta.
- **No depende de que Claude se acuerde:** un programa (`cierre-hijas.py`) detecta el aviso, mira qué hijas siguen trabajando y da la orden en ese momento; al terminar el turno comprueba que el mensaje cumple y, si no, pide reescribirlo una sola vez. Cada intervención queda anotada en `<carpeta de Claude>/state/cierre-hijas/registro.jsonl`.
- **Si molesta:** se apaga con la variable `CIERRE_HIJAS=0` o creando el archivo `<carpeta de Claude>/metodo/cierre-hijas.apagado`. No toca ninguno de tus archivos.

## 0.51.0 — 2026-10-18
**Cada carpeta con código tiene ahora un lugar con nombre para cada documento de desarrollo, y el revisor de carpetas los vigila.** Se aplica solo con la actualización; no hay nada que correr.
- **Los seis documentos de desarrollo que se pidieron (PRD, TRD, flujo de la app, UI/UX, esquema de datos, plan) ya tienen su lugar:** `docs/PRD.md`, `docs/arquitectura.md` (cómo está armado), `docs/flujo-de-la-app.md`, `docs/diseno/` (pantallas como mockups), `docs/esquema/` (generado desde el código, nunca a mano) y `docs/planes/`. Más `README.md`, pruebas, `docs/operacion.md` (dónde corre, cómo se despliega y se vuelve atrás, respaldo) y las revisiones de seguridad en `.claude/security-checks/`. El PRD ahora dice quién lleva la carpeta, en qué estado está y dónde está su respaldo.
- **Siete avisos nuevos (R22 a R28), ninguno bloquea nada:** el archivo de permisos de la carpeta, si dice algo, tiene que estar subido a GitHub (hasta hoy el control miraba solo que existiera en tu disco); en una carpeta con código, que haya README, arquitectura, flujo de la app, claves de ejemplo y pruebas; en una carpeta que se despliega, que haya operación y una revisión de seguridad de menos de 90 días; que el PRD diga dueño, estado y respaldo; y que el esquema generado no esté viejo. Cada uno aparece con su costo y su arreglo, como los demás, y no se repite.
- **Arreglo de un punto ciego:** un PRD que era solo la plantilla pasaba como «completo» si tenía la sección técnica de ayuda. Ahora se compara contra el texto de la plantilla, la actual y la anterior.
- **Lo que no cambia:** el arreglo automático sigue creando solo los tres documentos de toda carpeta con producto propio. Los de desarrollo (arquitectura, flujo, README, claves de ejemplo) los deja en esqueleto `estructura.py arreglar --si`, cuando vos lo pedís; nunca se crean vacíos solos. Una carpeta sin código ni historia propia sigue sin recibir avisos de documentos.
- **Medir «terminado» en GitHub:** `estructura.py remoto` cuenta qué cajas tienen el molde completo en GitHub, no en la carpeta de tu computadora (que puede ir atrasada).
- **Carpetas nuevas:** el `.gitignore` que se crea ya incluye `!.claude/settings.json`, para que una lista global de ignorados de tu computadora no esconda ese archivo.

## 0.50.2 — 2026-10-17
**Al cerrar una sesión, ya no te pide correr un comando para unir el trabajo.** Se aplica solo con la actualización; no hay nada que correr.
- **El problema:** en un repo sin controles en GitHub, el cierre te dejaba un comando para pegar y unir tu trabajo, y era un pedido que nadie entendía.
- **El arreglo:** un programa nuevo (`unir-pr`) une el trabajo solo, o lo deja programado si hay controles. Solo te avisa si algo falló de verdad (conflicto, controles en rojo) o si el cambio toca algo que corre solo en tu compu, y lo dice en una línea.

## 0.50.1 — 2026-10-17
**Las sesiones que abre Claude ya no quedan en un modelo distinto del pedido sin que nadie se dé cuenta.** Se aplica solo con la actualización; no hay nada que correr.
- **El problema:** al abrir una sesión nueva pidiendo un modelo más caro que el de la sesión que la abre (por ejemplo, Opus desde una sesión en Sonnet), la herramienta lo ignora en silencio y la nueva arranca en el modelo equivocado.
- **El arreglo:** apenas Claude abre una sesión pidiendo un modelo, le llega la orden de comprobarlo y corregirlo antes del primer turno de la nueva. No bloquea nada ni te pide nada.

## 0.50.0 — 2026-10-17
**El revisor de carpetas deja de dar órdenes mecánicas y empieza a dar consejos pensados.** Se aplica solo con la actualización; no hay nada que correr.
- **Cada aviso dice tres cosas:** qué encontró, cuánto cuesta dejarlo así (tokens por sesión, riesgo, lo que se rompe) y el arreglo que conviene en ese caso. Ejemplo: con pocas líneas de más en el `CLAUDE.md` ya no dice «mové un bloque a otro archivo»: dice que no hace falta nada; con muchas, pide mirar primero si hay algo repetido, viejo o contradictorio para sacar, y solo manda a `.claude/rules/` un bloque que aplica a un tema o carpeta puntual.
- **Si arreglarlo cuesta más de lo que se gana, lo dice y calla.** Ya no pide documentos vivos (`PRD`, `decisiones`, `planes`) en carpetas sin código, ni crea documentos vacíos de forma automática: solo donde el proyecto los necesita.
- **No se arregla en la sesión principal.** Lo que vale la pena le llega a Claude como pedido de abrir UNA sesión secundaria (tarjeta lista para arrancar con un clic), con el brief armado por `estructura.py brief`.
- **No repite lo mismo todos los días:** un aviso no vuelve antes de 7 días ni más de 3 veces; lo que decidís no hacer se anota con `estructura.py descartar <clave>` y vuelve solo si empeora o a los 6 meses. Se muestran como mucho 3 consejos, ordenados por lo que más rinde, y los detalles chicos van juntos en una línea.
- **Lo que no cambia:** `estructura.py revisar` sin `--aviso` muestra todo como antes, y los errores obligatorios (sin `.gitignore`, secretos versionados…) se siguen mostrando.

## 0.49.4 — 2026-10-17
**El arreglo automático del orden de tus carpetas es más cuidadoso.** Se aplica solo con la actualización; no hay nada que correr.
- **Escribe solo donde puede:** el arreglo automático ahora solo modifica el `CLAUDE.md` de cada carpeta y documentos `.md` dentro de `docs/`. Antes tomaba como seguro todo lo que no figuraba en una lista de cosas delicadas; ahora es al revés: lo que no está en la lista corta de permitidos no se toca.
- **No trae de GitHub lo que puede ejecutarse solo:** si una carpeta atrasada recibiría un programa, un archivo ejecutable, un enlace, una carpeta oculta (como `.husky/` o `.vscode/`) o un script de Windows o Mac que arranca solo, no avanza: te llega como pregunta de sí/no. El arreglo nunca ejecuta los avisos automáticos de git (hooks) de tus carpetas.
- **«Verificado por» ya no acepta cualquier texto:** `estructura.py aplicar <id> --verificado-por` pide el nombre de una IA conocida (gemini, codex, claude, gpt, pal…) o «persona», y queda anotado como lo que es: una declaración de quien lo corre. Lo de juicio nunca se aplica solo.
- **Nunca demora el arranque más de lo previsto:** la pasada semanal tiene un tope total (20 s para revisar, 30 s en total), que ahora vale también dentro de cada carpeta. Lo que no llega a revisar queda para la próxima.

## 0.49.3 — 2026-10-17
**En Windows, los paquetes del catálogo también se actualizan solos.** Se aplica solo con la actualización; no hay nada que correr.
- **Antes:** la app de escritorio arranca Claude Code con la actualización automática apagada, y eso frenaba también la de los paquetes del catálogo. En Mac la puesta al día ya lo corregía; en Windows no.
- **Ahora** la puesta al día de Windows (una vez por día, en segundo plano) deja prendida `FORCE_AUTOUPDATE_PLUGINS=1` en la configuración de Claude Code si falta, y lo dice en una línea. Si usás la terminal en vez de la app, no cambia nada.
- **Lo que no hace:** no toca ninguna otra clave de tu configuración, no cambia nada si ya estaba prendida y, si el archivo de configuración está roto, no lo toca y avisa. Para apagarla, borrá esa línea de `env`.

## 0.49.2 — 2026-10-17
**El control de estructura dice la verdad y ahora mira también el equipo de cada carpeta.** Se aplica solo; no hay nada que hacer.
- **Antes:** «Estructura al día ✓» aparecía aunque hubiera avisos pendientes, y en el aviso de arranque podía leerse «Falta: 0 cosas». **Ahora** cuenta los avisos: sin nada pendiente dice «Estructura al día ✓»; con solo avisos dice «Sin errores, pero con N avisos pendientes ⚠»; con errores suma «Además: N avisos». El código de salida no cambia.
- **Reglas nuevas (R19 a R21 de `ESTRUCTURA.md`, solo lectura):** el PM que nombra el `CLAUDE.md` existe y no es una cáscara, y si una carpeta no nombra ningún PM pero hay uno que la cita, te lo señala · las skills que el PM precarga existen · los conectores que el `CLAUDE.md` dice usar están configurados y habilitados (configurar no es habilitar) y las herramientas `mcp__…` del PM existen. De las configuraciones solo toma nombres de servidor, nunca llaves ni valores; los conectores de la nube no se juzgan.
- **Para el catálogo:** un control nuevo en cada cambio (`scripts/pasos-manuales.py`) frena lo que dependa de que el cliente haga algo a mano (una pieza que sale desactivada, una orden en el changelog) o use herramientas de una sola plataforma en un hook sin alternativa para Windows.

## 0.49.1 — 2026-10-16
**El arreglo automático del orden de tus carpetas ahora viene ENCENDIDO.** Se aplica solo con la actualización; no hay nada que correr.
- **Antes (0.49.0)** venía apagado y había que encenderlo a mano. **Ahora** corre solo, una vez por semana, desde el aviso de arranque. Hace lo mismo que se describe en 0.49.0: solo lo seguro y reversible, un commit por arreglo, con registro y `estructura.py deshacer <id>`; nunca sube nada a GitHub, no toca un archivo con cambios sin guardar y no toca lo sensible (permisos, avisos automáticos, lo que corre solo).
- **Se apaga por escrito:** `estructura.py orden-config --apagar` deja `aplicar:false` en `metodo-orden.json` (carpeta de Claude) y queda apagado. `--encender` lo vuelve a prender; sin argumentos dice el estado («encendida por defecto», «encendida por vos» o «apagada por vos»).
- **Ante la duda, apagado:** si `metodo-orden.json` está roto o ilegible, no escribe nada en tus carpetas hasta que lo corrijas con `orden-config --encender`.

## 0.49.0 — 2026-10-16
**El orden de tus carpetas se puede arreglar solo, sin que tengas que acordarte.** Viene **apagado**: no cambia nada hasta que lo enciendas (`estructura.py orden-config --encender`). Mientras esté apagado, `estructura.py auto` solo te muestra qué haría.
- **Lo seguro y reversible se arregla solo,** con un commit por arreglo, una prueba que lo verifica, un registro y un comando para deshacerlo (`estructura.py deshacer <id>`): una ruta del `CLAUDE.md` que cambió de lugar, un documento del molde que falta, una carpeta que quedó atrás de GitHub. Nunca sube nada a GitHub y no toca un archivo que otra sesión esté editando.
- **Lo que pide criterio** lo decide Claude con evidencia del disco y lo confirma una segunda IA antes de aplicarlo.
- **Lo tuyo te llega como UNA pregunta de sí/no** (qué se encontró, qué se propone, por qué, con la recomendación). Nunca se arregla solo lo sensible (permisos, avisos automáticos, lo que corre solo), ni borrar o mover carpetas, ni una carpeta sin respaldo en GitHub.
- **Una vez por semana,** el aviso de arranque muestra tres líneas: «arreglé N cosas, nada pendiente».

## 0.48.0 — 2026-10-16
**El control de estructura ahora mira también lo que dicen los archivos, no solo que existan.** Se aplica solo; no hay nada que correr.
- **Antes:** el control avisaba si faltaba `CLAUDE.md` o un documento, pero un `CLAUDE.md` con rutas que ya no existen, un contador viejo o un texto de reanudación de hace un mes pasaban como «al día».
- **Ahora** (reglas R13 a R18 de `ESTRUCTURA.md`, sin IA, solo lee): las rutas que cita el `CLAUDE.md` existen · no hay conteos escritos a mano («40 skills») · los agentes `pm-…` que nombra existen · `docs/PRD.md` y `docs/decisiones.md` no son solo la plantilla · `.claude/PENDIENTES.md` tiene el formato que lee el panel · el texto de reanudación dice la rama y la carpeta correctas, no cita archivos inexistentes y su cierre no es de hace más de 30 días.
- **Cuándo corre (el mismo aviso de siempre):** al abrir cada sesión (la carpeta actual), la primera vez de cada semana recorre todas las cajas, y `/cerrar` lo muestra. Solo avisa y propone el arreglo; nunca cambia el contenido por su cuenta (`estructura.py arreglar` sigue creando únicamente lo que falta).
- Un aviso que en tu caso es a propósito se deja por escrito en `.estructura-excepciones.json`, con motivo y fecha, como cualquier otra regla.

## 0.47.2 — 2026-10-16
**`radar.py hoy` suma, en la línea de cupo, el estado y el saldo estimado del Puente Gemini si lo usás.** Se aplica solo; no hay nada que correr.
- **Antes:** el saldo del Puente Gemini solo se veía corriendo `puente-gemini estado`.
- **Ahora**, si existe `~/.cerebro/puente-gemini.json` (lo deja ese comando), la línea «Cupo:» agrega «Puente Gemini: apagado · saldo ~US$X (estimado)». El saldo es una estimación; el real está en AI Studio → Gasto.
- **Lo que no hace:** solo lee ese archivo; no usa internet ni toca claves. Si el archivo no existe (no usás el puente), no dice nada.

## 0.47.1 — 2026-10-16
**El recordatorio del nombre (0.47.0) queda más firme.** Se aplica solo; no hay nada que correr.
- Solo repite apodos normales: letras, espacios, punto, guion y apóstrofe, hasta 40 caracteres. Si la línea `Llamame:` trae otra cosa (comillas que cierran la frase, texto larguísimo o con forma de instrucción), no dice nada.
- Si la variable `CLAUDE_CONFIG_DIR` está definida pero vacía, usa tu carpeta de siempre (`~/.claude`) en vez de leer el `CLAUDE.md` de la carpeta de trabajo, que podría ser de un proyecto ajeno.
- Entiende fichas guardadas con marca BOM y no falla en consolas de Windows con acentos.

## 0.47.0 — 2026-10-16
**Claude te sigue llamando como pediste durante toda la sesión, no solo al abrirla.** Se aplica solo; no hay nada que correr.
- **Antes:** la regla 24 se mostraba una vez al abrir la sesión («Quién habla: …») y a medida que la conversación avanzaba Claude volvía a decir tu nombre formal o ninguno.
- **Ahora** en cada mensaje tuyo se le repite, en una línea, el nombre de tu línea `Llamame:` (la de tu ficha personal, `~/.claude/CLAUDE.md`). Lo hace el paquete mismo; no se toca tu configuración.
- **Lo que no hace:** solo lee esa ficha; no escribe nada ni usa internet. Si no hay línea `Llamame:`, o anotaste `Personas en esta computadora: …` (varias personas), no dice nada: nunca inventa un nombre. El ejemplo del bloque de reglas no cuenta como tu nombre.
- Para apagarlo: sacá el bloque `UserPromptSubmit` de `hooks/hooks.json` del paquete, o desinstalá `metodo`.

## 0.46.0 — 2026-10-15
**Cuando algo frena el cierre o el archivado, Claude hace el trabajo y recién después cierra; ya no te lo deja como tarea.** Se aplica solo; no hay nada que correr.
- **Antes:** si una sesión hija tenía algo pendiente, `/arrancar` decía `NO ARCHIVAR … resolver antes de archivar` y la tarea te quedaba a vos; `/cerrar` marcaba ✗ sin decir qué hacer.
- **Ahora** cada ✗ trae la acción exacta (pedirle a la hija que guarde y suba lo suyo, esperar a que termine, leer su informe) y la sesión la ejecuta, repite el chequeo y archiva. A la persona solo le llega, en una línea, lo que únicamente ella puede decidir.
- **La caché de herramientas (`.omc/`, `__pycache__`, `.DS_Store`) ya no cuenta como trabajo** en la copia de una hija: antes frenaba el archivado sin motivo.
- **Si `archive_session` va a ser rechazado** (cliente remoto abierto, informe en cola), el chequeo lo avisa de antemano con `⚠ si la app la rechaza: …`; y las sesiones ya archivadas no se mencionan.
- **Repo que no une solo** (no está en `~/.claude/unir-a-main.txt`): `/cerrar` lo dice **una vez** y deja el camino: abrir el PR, unirlo con `gh pr merge --squash --auto` (o dejarte UN comando si el repo no lo admite), volver a la rama base **sin perder el `REANUDAR.md`** (`cierre_repo.py volver`) y seguir con el paso de abrir la sesión siguiente y archivarse. Antes el cierre quedaba parado en la rama de cierre y saltaba ese paso.

## 0.45.0 — 2026-10-15
**Claude te llama como VOS pedís que te llamen, y sabe qué hacer si en la misma computadora trabajan varias personas.** Se aplica solo; no hay nada que correr.
- **Regla 24 (nueva):** en TU ficha personal (`~/.claude/CLAUDE.md`, la de tu computadora) va una línea `Llamame: …` con cómo querés que te llamen (un apodo, si querés). Claude nunca usa en su lugar tu nombre formal, el del correo ni el de git. Las fichas de las carpetas (que comparte el equipo) no llevan nombres de personas.
- **Al abrir cada sesión** aparece una línea: «Quién habla: …» con ese nombre, o «Falta cómo querés que te llame…» si no hay línea. Si falta, Claude te pregunta UNA vez «¿cómo querés que te llame?» y lo anota; no vuelve a preguntar.
- **Varias personas en la misma computadora:** anotá `Personas en esta computadora: Ana, Luis`. Claude pregunta quién es antes de saludar. Si cada persona tiene su propia computadora (o su propio usuario de la Mac), no hace falta nada: cada una tiene su ficha.
- **Lo que no puede hacer:** adivinar quién está del otro lado. Si dos personas comparten computadora **y** usuario, solo lo sabe si se lo decís.
- **Subagentes:** Claude pone tu nombre en el pedido que les arma, porque no lo heredan.
- Las reglas del método pasan de 23 a 24 (se ponen al día solas, como siempre).

## 0.44.0 — 2026-10-15
**Claude ya no te pregunta si archiva sesiones que terminaron.** Se aplica solo; no hay nada que correr.
- **Antes:** el texto de reanudación podía decir «ofrecer archivar estas sesiones» y la sesión nueva te lo preguntaba, aunque ya estuvieran archivadas: afirmaba un estado sin mirarlo.
- **Ahora** el estado se mide en el disco. `/arrancar` archiva solo las sesiones que cita el texto de reanudación y siguen abiertas sin trabajo pendiente, y no menciona las que ya estaban archivadas. Si una tiene un informe sin leer o cambios sin guardar queda sin archivar y se avisa como `NO ARCHIVAR` (la resuelve su dueña; no es una pregunta para vos).
- **Al cerrar,** `cerrar-check` lista las sesiones hijas que se archivan solas junto con la tuya y marca ✗ un texto de reanudación que ofrezca o afirme el archivado.
- Archivar es reversible desde la barra lateral; nada se elimina.

## 0.43.0 — 2026-10-15
**Si trabajás con varias sesiones de Claude a la vez, el cierre de una ya no se frena por el trabajo de otra.** Se aplica solo; no hay nada que correr.
- **Antes:** `/cerrar` marcaba ✗ cualquier archivo sin guardar de la carpeta, aunque lo estuviera editando OTRA sesión que sigue abierta. Una sesión ajena frenaba el cierre de todas.
- **Ahora** cada sesión anota (en `state/ediciones/`, dentro de tu carpeta de configuración de Claude, fuera de cualquier repositorio y sin salir de tu computadora) qué archivos tocó ella. Al cerrar, lo que dejaste vos sin guardar **sigue frenando** (✗); lo que dejó otra sesión sale como aviso (`• … NO son de esta sesión`, con cuál y hace cuánto) y no frena. También cuenta como ajeno lo que ya estaba sin guardar antes de que abrieras esta sesión.
- **Ante la duda, es tuyo y frena.** Cuenta como de otra sesión solo lo que esa otra sesión editó con las herramientas de edición de Claude y que nadie tocó después. Lo que otra sesión cambió con un comando (`sed`, un script, `codex`…) **no** alcanza para darlo por ajeno, porque un comando que nombra un archivo no prueba que lo haya cambiado: sale como tuyo y frena. Lo mismo si el archivo cambió después de la última anotación, si se copió con `cp -p`/`mv` conservando una fecha vieja, o si no se sabe de quién es.
- **`--ajeno <ruta>`** (en `cerrar-check.py`) sirve para lo que estás seguro de que no es de esta sesión y el registro no vio: mirá su cambio (`git diff`) y repetí el chequeo con esa opción; queda como aviso, a la vista. **No vale para un archivo que el registro dice que editaste vos.**
- **Si usaste `--ajeno`, el veredicto final lo dice** (`Cierre completo ✓ — OJO: N archivo(s) … declarados ajenos A MANO`), para que lo veas vos y no quede escondido.
- Si el registro todavía no conoce esta sesión (por ejemplo, recién se instaló el hook) o el programa no puede saber qué sesión sos (falta `CLAUDE_CODE_SESSION_ID`), todo lo sin guardar cuenta como tuyo, igual que antes.
- El registro se borra solo a los 14 días y queda legible solo para tu usuario. El anotador (`ediciones.py`) no muestra nada, no frena nada, no manda nada afuera y consulta git sin tomar su candado, así que no molesta a un commit de otra sesión.

## 0.42.0 — 2026-10-15
**Unir a `main` ya no depende de que alguien afirme que está todo bien: el programa lo comprueba.** Se aplica solo; no hay nada que correr. Explicación en una página: `docs/SELLO-UNIR-A-MAIN.md`.
- **Se acabaron las opciones que se afirmaban a mano.** `--revisado-por`, `--ok-fernando` y `--sin-pruebas` ya no existen: una sesión engañada podía escribirlas sin que fueran ciertas. Ahora `unir-a-main` se corre sin opciones y hace todo por su cuenta.
- **Revisor independiente lanzado por el programa:** otro Claude, sin herramientas, lee el cambio real. Rojo no une nunca; amarillo te pregunta; verde no alcanza si el cambio toca algo que corre solo.
- **Tu OK, solo cuando hace falta, con Touch ID o tu contraseña y atado al commit:** con una frase en criollo (qué toca y qué dijo el revisor). Cancelar es «no». Una pantalla segura que otro programa no puede apretar por vos. **Se te pregunta antes de correr las pruebas**, no después: nada de lo que trae la rama se ejecuta sin tu «sí» cuando hace falta.
- **El «main» contra el que se compara no se puede falsificar:** el programa baja el main real del remoto a una referencia propia y comprueba que coincida con lo que el remoto dice en ese momento. Antes, una sesión podía escribir un main falso en la copia local y colar un cambio sin revisar.
- **La configuración del repositorio (`.git/config`) se revisa antes de bajar o subir nada:** si trae algo que git ejecutaría (un comando de ssh, un asistente de contraseñas, un programa de firma, filtros o fusionadores), no se une hasta que una persona lo mire. La copia con la que se prueba se arma leyendo los archivos tal cual, sin filtros de git.
- **El aislamiento de las pruebas en Mac es más cerrado:** no se puede ejecutar nada desde la carpeta de la copia (ni un programa del sistema copiado ahí), no se pueden crear tareas en `launchd` ni escribir las preferencias del usuario. Probado: un `launchctl` copiado no arranca.
- **El programa se protege de la sesión:** se corre con `python3 -I` (también desde la primera línea del archivo), limpia el entorno, no usa variables que la sesión pueda cambiar, apaga los hooks de git del repo, exige encontrar `git` en un lugar fijo del sistema y no distingue mayúsculas al buscar archivos sensibles. Al revisor se le apagan los hooks de tu usuario.
- **Fuera de Mac, el programa nunca acepta un «sí» tecleado** (una sesión conoce el código que se pediría): lo que necesite tu OK va por PR.
- **También te consulta** si la rama borra pruebas, trae binarios, enlaces, ejecutables nuevos o cambios de permisos, o cambia instrucciones de `~/.claude` (`CLAUDE.md`, skills, agentes, comandos).
- **Más cosas que corren solas ahora te las consultan:** `.mcp.json` (y los programas a los que apunta), `.husky`, `.githooks`, `.envrc`, tareas del editor, `package.json`, `pytest.py` y parecidos que reemplazarían al programa de pruebas, los ajustes de Claude en cualquier carpeta y los programas a los que apuntan los hooks (leídos de `main`, no de la rama). El control de GitHub del catálogo (`zona-sensible`) aprende lo mismo, también en la raíz y en subcarpetas.
- **Cada unión deja un sello** (commit exacto, huella del cambio revisado, pruebas, veredicto, tu OK) guardado en el repo y referenciado en `main`.

## 0.41.1 — 2026-10-15
**Toda carpeta lleva los mismos tres documentos**, tenga código o no. Se aplica solo; no hay nada que correr.
- **Por qué:** antes el molde pedía `docs/PRD.md`, `docs/decisiones.md` y `docs/planes/` solo a los proyectos con código, y alguien que no programa no tiene cómo saber si lo suyo «es desarrollo». Ahora los tres están siempre, en toda carpeta (empresa, área y proyecto): la sesión sabe en cualquier lugar **dónde guardar cada cosa y con qué nombre**. `PRD.md` = qué es la carpeta, para quién, cuándo está terminada y qué NO se hace (si hay código, suma la parte técnica y el flujo de la app); `decisiones.md` = cada decisión con su fecha y el porqué; `planes/` = un plan por etapa, `AAAA-MM-DD-tema.md`, que se archiva al terminar.
- **El control avisa (R12):** si a una carpeta le falta alguno de los tres, lo dice (es un aviso, nunca frena nada). Se puede dejar así a propósito con una excepción escrita en `.estructura-excepciones.json`.
- **`estructura.py arreglar` los crea:** cada archivo nace con unas líneas de instrucciones (qué va ahí, cómo se nombra y un ejemplo mínimo), sin inventar contenido. Nunca pisa un archivo que ya existe.
- **El `CLAUDE.md` que arma `arreglar` ahora dice dónde va cada cosa** (decisión, plan de etapa, qué es la carpeta). La plantilla de `base-segura` suma la misma sección.

## 0.40.2 — 2026-10-15
Cierra los hallazgos de la revisión de seguridad de 0.40.1. Se aplica solo; no hay nada que correr.
- **El programa que une ramas a `main` (`unir-a-main`) ya no une nada si no existe la lista de repos permitidos.** Antes, sin esa lista, valía cualquier repo; en tu computadora esa lista no existe, así que no se une nada hasta que la crees a propósito.
- **Los textos que escribís al unir (quién revisó, motivo de «sin pruebas») se limpian:** sin saltos de línea ni caracteres de control, y con largo tope. Así no se puede forjar otra línea en el mensaje del commit.

## 0.40.1 — 2026-10-15
`/metodo:arrancar` sigue numerando la serie de sesiones aunque hayas **movido la carpeta del proyecto**. Se aplica solo; no hay nada que correr.
- **Antes:** al mover o renombrar una carpeta, las sesiones anteriores quedaban guardadas con la ruta vieja: la sesión nueva no las veía, quedaba sin número y la anterior sin archivar. **Ahora:** cuenta como de la misma serie una sesión cuya carpeta vieja ya no existe y se llamaba igual que la actual. Nunca une dos carpetas que existen. Si además cambiaste el nombre, podés anotar la mudanza en `mudanzas.json` (en la carpeta de configuración de Claude, formato `{"mudanzas":[{"de":"…","a":"…"}]}`) y también se encuentra.

## 0.40.0 — 2026-10-15
El control de estructura acepta **excepciones escritas**. Se aplica solo; no hay nada que correr.
- **Lo que se decidió dejar así ya no marca ✗ para siempre:** se anota en `.estructura-excepciones.json` (en la raíz del repositorio) con la regla, la carpeta, el motivo y la fecha. El control lo muestra como `• excepción …` y no lo cuenta en el «Falta: N cosas ✗». Una excepción sin motivo o sin fecha no vale (se ignora y avisa). R6 (claves en GitHub) y R11 (la raíz de proyectos no es un repositorio) no se pueden exceptuar. Funciona también en copias de trabajo (git worktree).

## 0.39.2 — 2026-10-14
Se aplica solo; no hay nada que correr.
- **La sesión nueva vuelve a su grupo de la barra lateral:** al cerrar, `/metodo:cerrar` abre la sesión siguiente y, si se olvidaba de devolverla al grupo donde estaba la anterior, quedaba suelta y había que arrastrarla a mano. Ahora `/metodo:arrancar` lo detecta y la mueve solo.

## 0.39.1 — 2026-10-14
Arreglos para que el método ande igual en Windows. Se aplica solo; no hay nada que correr.
- **Delegar en Windows:** `delegar.py --archivo` rechazaba cualquier pedido en la carpeta temporal («tiene que estar dentro del repo…») porque comparaba rutas con `\` contra rutas con `/`. Ahora compara igual en los tres sistemas.
- **Salida con acentos en Windows:** el informe de la cuarentena de skills (`⛔`) y el aviso de piezas sin disparador de `/cerrar` salían rotos o caían por la consola de Windows (cp1252); ahora fuerzan UTF-8 como el resto de los scripts.
- Sin cambios para Mac y Linux. Las pruebas automáticas dejan de depender de la máquina donde corren (un `python` suelto en Linux hacía fallar la de «sin Python»).

## 0.39.0 — 2026-10-14
**Unir el trabajo a `main` ya no te pide OK:** lo deciden los controles automáticos. Se aplica solo; no hay nada que correr.
- **`/metodo:cerrar` junta la rama a `main` solo** cuando el tema terminó: primero pide una revisión a alguien distinto de quien escribió el cambio (un agente revisor u otra IA) y después corre `scripts/unir-a-main`, que trae lo nuevo de `main`, corre las pruebas de tu repo y sube sin forzar nunca. Si algo falla (pruebas, conflicto), no une y te dice por qué.
- **Te sigue preguntando** solo cuando el cambio toca **lo que corre solo en tu computadora** (ajustes de Claude, hooks, tareas que arrancan solas, instaladores, robots de GitHub), cuando hay que **borrar o reescribir historia** y en las **decisiones del negocio**. Reglas 3 y 13 actualizadas.
- Cada unión deja escrito en `main` qué pruebas pasaron y quién revisó, para poder mirarlo después.

## 0.38.0 — 2026-10-14
La estructura de Claude incluye los **documentos de los proyectos con desarrollo**. Se aplica solo; no hay nada que correr.
- **Pocos documentos vivos, no seis:** `docs/PRD.md` (qué se construye, para quién, cuándo está terminado, qué NO se hace; adentro la parte técnica y el flujo de la app), `docs/decisiones.md` (cada decisión con fecha y porqué) y `docs/planes/` (un plan por etapa, se archiva al terminar). Las pantallas van como mockups y el esquema de datos se genera del código.
- **Aviso nuevo (R12):** si una carpeta de proyecto tiene código y le falta `docs/PRD.md`, el control lo avisa (nunca frena nada). `estructura.py arreglar` puede dejar la plantilla vacía con sus secciones; el contenido lo arma el PM del proyecto con Claude a partir del código.

## 0.37.0 — 2026-10-13
Llega la **estructura de Claude**: cómo se ordenan las carpetas y archivos cuando trabajás con varias empresas, áreas, proyectos y personas con distinto acceso. Se aplica solo; no hay nada que correr.
- **Una sola fuente:** `estructura/ESTRUCTURA.md` (el molde de cada carpeta, qué se comparte y qué no, y las reglas). El dibujo (`estructura/estructura.html`) se arma desde ahí, así que nunca queda viejo.
- **Control que avisa solo:** al abrir cada sesión revisa la carpeta en la que estás (si está todo bien, no dice nada); la primera sesión de cada semana recorre todas tus carpetas de proyectos; `/cerrar` también muestra lo que falta. Nunca cambia nada por su cuenta y no frena el cierre.
- **Te ayuda a arreglarlo:** cada aviso dice cómo se arregla, y `estructura.py arreglar` primero te muestra el plan y, con tu OK, crea lo que falta (`CLAUDE.md`, ajustes, `.gitignore`, ejemplo de claves solo con los nombres). Lo que toca GitHub o mueve carpetas no lo hace solo: te lo propone.
- **El radar vigila** las páginas oficiales de Claude Code que sostienen la estructura y avisa si cambian.

## 0.36.3 — 2026-10-13
Se aplica solo; no hay nada que correr.
- **`/cerrar` ya no se traba por cambios de otra sesión.** Si varias sesiones comparten una copia (un repo con una subcarpeta por proyecto), `cerrar-check` avisa con «•» los archivos sin guardar que están fuera de tu carpeta y sigue; los de tu carpeta siguen dando ✗. Así el cierre abre la sesión siguiente y archiva la vieja.

## 0.36.2 — 2026-10-13
`/cerrar` y `/arrancar` funcionan igual que en la computadora de quien te acompaña, y cuatro reglas del método quedan más completas. Se aplica solo; no hay nada que correr.
- **Cerrar sin abandonar a nadie.** `/cerrar` tiene un Paso 0: si abriste otras sesiones o ramas, no se cierra mientras una siga trabajando, tenga un resultado sin revisar o haya una rama sin juntar. `cerrar-check` imprime las ramas y copias abiertas.
- **Qué hace confiable a algo de afuera**, escrito en la regla 19 y en `buscar-skill-externa` (uno de tres caminos; el de «lo leí entero» solo vale si es puro texto).
- **`/arrancar` archiva solo las sesiones anteriores de la serie**, sin preguntar (se recuperan desde la barra lateral); si la sesión la abrió `/cerrar` y la app rechaza por «still working», se archiva sola al terminar. `/cerrar` ya se archivaba sin preguntar.
- **El vigía ya no deja la revisión «a medias» si un paquete apunta a un repositorio que se borró o se movió:** te lo muestra como aviso («origen perdido») y sigue con el resto.
- **Cupo:** equipos de varios agentes solo con tu OK y gasto estimado; revisiones en bucle con tope de 2 vueltas (regla 16).

## 0.36.1 — 2026-10-13
El freno de claves frena 4 maneras más de mostrar una clave en pantalla. Se aplica solo; no hay nada que correr.
- **Frena:** leer un archivo de claves desde dentro de un comando que lo expande (por ejemplo con `$(<archivo)`), listar todo el entorno con `env` sin un programa, pedirle a GitHub CLI que muestre su token (`gh auth status` con `-t`/`--show-token`) y pedirle al llavero de la Mac que muestre una contraseña (`security find-generic-password … -w`/`-g`).
- **Deja de frenar de más** un comando de búsqueda de GitHub que usaba la opción `-t` con otro significado.
- El freno puede dar algún aviso de más en comandos raros; si te frena algo legítimo, mandale la captura a quien te acompaña.

## 0.36.0 — 2026-10-13
Gemini (Antigravity) trabaja igual que en la computadora de quien te acompaña. Se aplica solo; no hay nada que correr.
- **Cuando `delegar.py` le pasa un trabajo a Gemini, Gemini trabaja sobre una copia de tu repo**, no sobre la carpeta real. La copia va en `~/.cache/metodo/agy-trabajo` (fuera de la configuración de Claude). Se puede cambiar con `METODO_AGY_TRABAJO`, pero no a tu carpeta personal, a una que la contenga, a una carpeta de llaves ni a una dentro del repo. Cada copia se borra al terminar; si una corrida se corta, la copia que quedó se borra sola al día siguiente (solo las que creó este programa: lleva una marca adentro). La copia no lleva la historia de git, ni accesos directos (enlaces) a otras carpetas, ni nada que parezca una clave: archivos de entorno, llaves, credenciales, historiales de la terminal y transcripts, ya sea por la carpeta en la que están (`secrets/`, `credentials/`, `keys/`, `private/`…), por el nombre (también en archivos de datos como `.properties`, `.xml`, `.plist`, `.csv`, y en copias `.bak`/`.old`/`.orig`) o por lo que tienen adentro (una clave privada o una llave con forma conocida en sus primeros 64 KB). Tampoco lleva la configuración de otras herramientas que traiga el repo (`.gemini/`, `.claude/`, `.codex/`, `.cursor/`, `.agents/`, `.antigravity/`), para que no se den permisos solas. Te dice cuántos quedaron afuera. Las plantillas (`.env.example` y parecidas) sí viajan, y también los archivos de código con «token» o «secret» en el nombre (`VerifyCsrfToken.php`, `tokenizer.py`) y los «design tokens» (`tokens.json`, `tokens.css`).
- **Lo que Gemini cambia vuelve a tu repo como un parche, solo en archivos comunes, y te muestra la lista completa de lo que vuelve** (leída del mismo parche que se aplica: nuevo, cambiado, borrado o solo permisos). No se trae nada si Gemini crea una carpeta `.git` o un archivo de repo (`HEAD`, `commondir`, `gitdir`), un enlace o un submódulo, o un nombre de archivo con caracteres invisibles; si toca la configuración o las instrucciones de Claude (`.claude/`, `CLAUDE.md`); si crea o cambia un `.gitignore`; si crea o cambia archivos en carpetas que git ignora (por ejemplo `node_modules/`), que no se verían en `git status` (y si eso aparece recién después de aplicarlo, se deshace); o si algo de lo que vuelve trae adentro una clave. Si toca archivos que pueden ejecutar programas o cambiar cómo se comportan git, tu editor u otros agentes (`.husky/`, `.githooks/`, `.vscode/`, `.github/`, `.gemini/`, `.codex/`, `.cursor/`, `.devcontainer/`, `.idea/`, `.roo/`, `.kiro/`, `.continue/`, `.windsurf/`, `.zed/`, `.junie/`, `AGENTS.md`, `GEMINI.md`, `.cursorrules`, `.windsurfrules`, `.clinerules`, `.aider*`, `.pre-commit-config.yaml`, `.gitattributes`, `.gitmodules`), se trae pero te lo muestra primero, en rojo: revisalo antes de correr nada. Si crea un archivo con nombre de clave, se descarta.
- **Mientras Gemini trabaja, git apunta a un repo que no puede existir y corre sin fsmonitor, hooks, diff externo ni paginador**: si Gemini arma un repo en su copia y corre git, git no lo usa. Esto vale para los comandos de git; no limita otros programas.
- **Si tu configuración de Antigravity tiene reglas amplias** (leer cualquier carpeta, escribir archivos, comandos, cualquier página, o una regla sin límite como `command` a secas), `delegar.py` te lo avisa en rojo al lanzarlo (mostrando solo la herramienta y el comodín) y sigue: con esas reglas, un repo con instrucciones escondidas podría hacerle leer más allá de la copia y mandar datos afuera. Si la configuración no se puede leer (por ejemplo, tiene comentarios), también te avisa en rojo. Lo decidís vos; para no ver el aviso, `METODO_AGY_SIN_AVISO_REGLAS=1`. Solo se lee el archivo, no se ejecuta Antigravity.
- **Antigravity siempre usa un modelo que existe.** Antes de lanzarlo se mira la lista de modelos que ofrece (`agy models`, solo lectura y solo si su cupo dio «ok»). Si el que recomienda el radar no está (por ejemplo, un Gemini Pro que Antigravity no tiene), usa el mejor Gemini disponible y te dice cuál y por qué; antes Antigravity elegía otro por su cuenta y devolvía una respuesta vacía. Si no ofrece ningún Gemini, no se lanza.
- **Si a Gemini se le niega una herramienta, termina en rojo y te dice qué hacer** (antes terminaba «bien» sin haber hecho nada). Pasa cuando corre sin pantalla y no hay quién apruebe. Qué hacer: dale los datos ya listos en el pedido en vez de pedirle comandos; y si lo que se le niega es leer su propia copia, probá con la carpeta de trabajo dentro de tus proyectos (`METODO_AGY_TRABAJO=~/Proyectos/sandbox/agy-trabajo`). No agregues reglas amplias para destrabarlo. Una respuesta larga que solo menciona esas palabras no cuenta como negación.
- **Una revisión que vuelve vacía o casi (menos de 200 caracteres) termina en rojo**, con la sugerencia de probar otro modelo; antes contaba como «hecho». Y a Gemini se le pide que, si el pedido ya trae todo lo que hay que revisar, responda sin usar herramientas.
- **El archivo del pedido** (`--archivo`) pasa por el mismo filtro de nombres y carpetas de claves, se abre sin seguir un enlace, tiene que ser tuyo y no puede traer adentro algo con forma de clave.
- **«Poner todo al día» ya no agrega reglas a Antigravity.** Gemini trabaja en una copia sin la historia de git, así que esas reglas no le sirven y solo abren riesgo. Lo único que hace: si tenés la regla `git -C *`, la saca (dejaba ejecutar programas), con copia de cómo estaba; y si tenés reglas amplias (cualquier página, leer carpetas enteras o tu carpeta personal, escribir, reglas sin límite, comandos con comodín o con un programa que ejecuta otros, como `python`, `bash`, `git`, `npm` o `make`), te avisa en una línea con qué hacer, sin tocarlas: decidís vos. No abre Antigravity. Además, todos sus pasos en Python ignoran los archivos `.py` que haya en la carpeta desde la que se corre.
- **Ya no se frena delegar por el nombre de la carpeta** (clientes, finanzas, personal…): podés delegar desde cualquier carpeta de proyecto. Siguen frenados tu carpeta personal entera, la raíz del disco, las carpetas de llaves y de configuración de tus herramientas (`~/.ssh`, `~/.aws`, `~/.azure`, `~/.oci`, `~/.config/gcloud`, `~/.config/op`, `~/.password-store`, `~/.claude` o la que marque `CLAUDE_CONFIG_DIR`, `~/.gemini`, `~/.codex` o `CODEX_HOME`, `GNUPGHOME`, `KUBECONFIG`, `~/.notebooklm`, chezmoi, el llavero…) y lo que marques con `METODO_NO_DELEGAR`.
- **Codex se salta si el repo tiene archivos de claves o de entorno, aunque git los ignore** (un `.env` en `.gitignore` cuenta): Codex trabaja sobre la carpeta real porque necesita correr tus tests con lo instalado, y ahí podría leerlos. El aviso lo dice; el trabajo pasa a Gemini, que usa la copia sin esos archivos, o a Claude en tu sesión. Para Codex se mira el nombre; en carpetas `key`, `keys` o `private` (como `storage/app/private/`) decide lo que tienen adentro.
- El pedido le llega a Gemini en la línea de comandos (Antigravity no lo acepta de otra forma sin pantalla): mientras corre, otra cuenta de la misma computadora podría verlo en la lista de procesos. No pongas claves en el pedido.
- **Lo que no se comprobó todavía:** todo esto se probó con un Antigravity simulado, no con el real; no se sabe si Antigravity lee configuración propia del proyecto (por eso no viaja), si respeta sus reglas en modo sin pantalla, ni si lee su copia sin reglas desde `~/.cache`. Tampoco se probó en Windows: `delegar.py` usa solo Python y debería andar igual, y el aviso sobre la configuración de Antigravity en la puesta al día está solo en la de Mac.

## 0.35.2 — 2026-10-13
Cierre de lo que quedó abierto en la revisión de seguridad de 0.35.0. Se aplica solo con `/plugin update`; no hay nada que correr.
- **«Poner todo al día» instala las librerías de Python con versión y huella fijas** (en el Python de Apple): si el archivo que sirve el repositorio público no es el esperado, no se instala nada. En otro Python quedan con versión fija pero sin huellas, y te lo avisa.
- **Una versión nueva de `metodo` o `paneles` no llega a los clientes sin su security check anotado.** La promoción a `estable` lo exige; quien promueve puede saltarlo a propósito, y queda registrado quién y por qué.
- **Prueba nueva con un repositorio que trae enlaces simbólicos:** confirma que la cuarentena no trae archivos de afuera.

## 0.35.1 — 2026-10-12
Arreglos de seguridad sobre lo que ya traía 0.35.0 (revisión de seguridad completa del paquete). No hay nada nuevo que aprender: se aplica solo con `/plugin update`.
- **Traer una skill de afuera a la cuarentena rechaza los enlaces simbólicos** (accesos directos que apuntan a otra carpeta): una skill ajena no puede hacer que la auditoría mire, o copie, archivos fuera de ella. Siguen andando `owner/repo`, `owner/repo@skill`, `github:` y las direcciones de GitHub.
- **El freno de claves cierra 7 maneras más de mostrar o sacar una clave.** Puede dar algún aviso de más en comandos que listan variables o leen archivos de claves.
- **«Poner todo al día» avisa en una línea cada vez que cambia permisos de tu configuración**, con la copia previa; antes algunos cambios pasaban sin aviso.
- **`/arrancar` solo toma como tuyo un `REANUDAR.md` que dejó `/cerrar` en ESTA computadora.** Si aparece uno que no (por ejemplo, llegó por GitHub desde tu otra computadora), te lo muestra y te pide que confirmes si es tuyo; con tu «sí» en el chat se usa igual y no te quedás sin arranque.
- **Windows (preparación, todavía no probado en una PC real):** los frenos buscan `python3`, `python` o `py`, y avisan una vez por día si no hay Python; el freno también mira PowerShell.
- Otros ajustes menores: marcas temporales que no siguen enlaces, comprobación del instalador en cada corrida, y la promoción a `estable` ahora mira todos los commits del tramo y no solo el último.

## 0.35.0 — 2026-10-12
- **Skills de afuera sin riesgo: `/metodo:buscar-skill-externa`.** Pedile a Claude «buscame una skill para X» o «instalá la skill Y»: busca en el registro público (solo lectura, sin instalar nada), te muestra cuáles ya tenés, trae la que elijas a una **cuarentena** (carpeta temporal, entorno vacío que no ve tus claves, instalador oficial fijado por versión y hash), la audita (archivos de prueba, `hooks.json`, instrucciones para otros agentes, descargar-y-ejecutar, texto oculto) y te hace un informe. **Recién con tu OK** se copia a tu carpeta de skills. La primera vez baja el instalador (necesita Node.js; si falta, te lo dice). Traer a la cuarentena: Mac y Linux (en Windows todavía no está probado: el programa lo dice y no hace nada; buscar sí funciona). Detalle en `requisitos.md`.
- **Un freno traba `npx skills add|update|check|remove`** contra tu carpeta de skills (el instalador de Vercel copia todo sin auditar). Se registra solo con el plugin; buscar con `find` o `list` sigue pasando. Se apaga desinstalando el plugin.
- **Regla 19** suma una frase: las skills de afuera entran solo por esa skill. `herramientas-para.py` te manda a ella cuando no hay nada instalado para un tema, y la lista de herramientas evaluadas suma el instalador de Vercel (qué se decidió y por qué).
- Prueba: `python3 -m unittest discover -s plugins/metodo/scripts/tests -p test_skills_externas.py` (7 pruebas, sin red; incluye una skill falsa maliciosa que el filtro bloquea).

## 0.34.0 — 2026-10-12
- **Regla 23: todo lo que creás tiene que tener quién lo ejecute.** Una skill, un agente, un script o un aviso sin nadie que lo dispare (ni un hook, ni una tarea programada, ni otra skill, ni palabras en su descripción que hagan que Claude lo use) es un cartel en una puerta cerrada: funciona solo si te acordás de pedirlo. Desde ahora, lo que creás nace con una línea `Disparador:` (quién lo llama y cuándo), se prueba en una sesión limpia antes de darlo por terminado y, si **revisa, audita o respalda** algo, se engancha a algo que ocurra solo. Está en `REGLAS-DEL-METODO.md` (se pone al día solo al abrir la sesión).
- **`/metodo:cerrar` te avisa si creaste hoy algo sin disparador.** Si en las últimas 36 horas hiciste (en tu configuración general o en la carpeta de trabajo) una skill, un agente o un script que nadie ejecuta, el cierre lo marca en rojo con el nombre y qué hacer. Lo más viejo sale solo como aviso, sin frenar nada.
- **`/metodo:crear-agente` suma el paso del disparador** (quién lo invoca, cómo probarlo) y el error típico «un agente que nadie invoca».
- **Programa nuevo `disparadores.py`** (junto a `radar.py`): mide todas tus piezas y dice cuáles no tienen quién las ejecute, aunque se nombren entre sí (dos piezas que solo se mencionan una a la otra no cuentan). Solo lee. `python3 disparadores.py --home`.

## 0.33.0 — 2026-10-12
- **Lista de herramientas que ya se evaluaron y se descartaron.** Antes de probar o instalar algo de afuera, Claude mira una lista corta con lo que ya se analizó: qué es, qué se decidió y cuándo, por qué (con las cifras medidas) y **qué tendría que cambiar para volver a mirarla**. Hoy trae cuatro: OmniRoute (portero de IA), Ponytail (reglas de «código mínimo»), Gbrain (cerebro con búsqueda) y claude-mem (memoria automática de sesiones). Si lo que querés probar está ahí, no hace falta repetir el análisis: se comprueba solo si cambió la condición.
- **Cómo la ves:** pedile a Claude «evaluá/instalá X» y, si hay una coincidencia, el freno de la regla 22 la trae **una sola vez** por carpeta cada 4 horas; o a mano con `herramientas-para.py herramientas rechazadas`. La regla 21 suma una línea que lo dice.
- La lista la mantiene tu consultor: no la edites. Si querés una propia, creá `<config de Claude>/recetas/herramientas-rechazadas.md` y esa gana.
- Límite: el freno mira cuando Claude lanza un agente o un trabajo largo; no mira los comandos sueltos de instalación (`claude plugin install …`).
- Se activa solo con `/plugin update`; no hay nada que correr.

## 0.32.5 — 2026-10-11
- **El freno de claves ahora también mira cuando Claude escribe.** Si Claude está por guardar en un archivo de claves (el de variables de entorno, una llave, un archivo de credenciales) algo que parece una clave de verdad, **te pregunta antes**; no bloquea ni corta el trabajo. Dejar los valores vacíos o de relleno (`changeme`, `<tu-clave>`) o escribir en los archivos de ejemplo sigue pasando sin preguntar. El mensaje nunca muestra la clave: solo el nombre de la variable y el número de línea. Lo que ya frenaba (leer o imprimir claves) sigue igual. Escribir con redirecciones de la terminal (`echo X=… > archivo`) todavía no se mira.
- **Funciona mejor en Windows.** Se arreglaron las pruebas automáticas de este paquete en Windows (lectura de textos con tildes, rutas de carpetas privadas, variables del sistema); si usás Windows, no tenés que hacer nada.

## 0.32.4 — 2026-10-11
- **«Poner todo al día» suma `claude-security`**, el plugin oficial de Anthropic para auditar la seguridad de un proyecto a fondo. Se instala de la fuente oficial (no viaja dentro de este catálogo) y **nunca se dispara solo**: escanear gasta mucho cupo, así que se pide a mano. Apaga solo su aviso de escaneo después de cada subida de cambios (variable propia del plugin, no toca nada tuyo). Mientras escanea puede correr comandos de `git` sin preguntar; el escaneo lo pedís vos, sobre tu propio código.

## 0.32.3 — 2026-10-11
- **`/metodo:arrancar` más liviano.** Pasa de muchas idas y vueltas a 3 (leer y chequear, poner el título, confirmar). El número de la sesión y las sesiones anteriores abiertas se calculan desde el disco, sin listar todas las sesiones de la app, que era lo más caro. Mantiene todo lo anterior: «de qué veníamos hablando», las líneas de pendientes y la excepción cuando te abre `/cerrar`.

## 0.32.2 — 2026-10-11
- **Receta nueva: arneses.** Antes de tocar automatismos, permisos o skills, Claude consulta las reglas de cómo configurarlos con seguridad (claves por referencia, nada aprobado de antemano en skills ajenas, avisos que se vean). Cada regla trae la página oficial de Claude Code de donde sale.

## 0.32.1 — 2026-10-11
- **Claude ya no puede leer ni editar las carpetas donde se guardan tus llaves** (SSH, GitHub, nube, llavero de la Mac). Los programas las siguen usando normalmente; la regla es solo para las herramientas de Claude. Se agrega sola al ponerte al día, sin tocar tus reglas y con copia previa de tu configuración (`settings.json.antes-arneses`).

## 0.32.0 — 2026-10-11
- **El freno de claves frena más casos.** Ahora también frena leer con la herramienta Read un archivo de claves (variables de entorno) o una llave, buscar con Grep dentro de esos archivos y mandar un archivo afuera con `curl -d @archivo`.
- Si el freno no puede correr (falta Python), avisa una vez por sesión y se ve en pantalla. Antes ese aviso no lo veía nadie.
- Menos frenos de más: los archivos de ejemplo (`sample.env`, `.env.local.example`) ya no se frenan.
- Solo Mac y Linux: en Windows, PowerShell no pasa por el freno (ver `requisitos.md`).

## 0.31.0 — 2026-10-10
- **Regla 22: antes de construir algo nuevo, Claude mira qué hay instalado para eso.** Si va a crear una pantalla, o a lanzar un agente o workflow que crea o diseña, primero consulta las recetas del método (qué skills y agentes usar, en qué orden y cuáles no). Un freno automático salta **una sola vez** por carpeta cada 4 horas, solo si hay receta para lo que va a hacer, y trae la receta en el mismo mensaje. Lo demás (leer, auditar, editar archivos que ya existen, scripts) pasa sin molestar.
- **Tres recetas incluidas:** pantallas web, documentos de oficina y seguridad con claves. Podés agregar las tuyas en `<config de Claude>/recetas/`: si se llama igual, la tuya gana.
- **Consulta a mano:** `herramientas-para.py <tema>` (junto a `radar.py`) muestra la receta y las skills y agentes instalados que coinciden. Solo lee, no usa red.
- Se activa solo con `/plugin update`; no hay nada que correr. Se apaga con `CONSULTAR_ECOSISTEMA_OFF=1` o creando `<config de Claude>/metodo/consultar-ecosistema.apagado`. Si falta Python, deja pasar sin ruido.

## 0.30.1 — 2026-10-10
- **El resumen de la sesión anterior solo se muestra si lo dejó tu propio `/cerrar`.** Antes, un archivo `REANUDAR.md` de un repositorio ajeno (clonado, descargado) podía hacerse pasar por uno tuyo copiando su primera línea y meter instrucciones en tu sesión. Ahora el último paso de `/cerrar` anota una huella del archivo en `reanudar-confiables.txt` (dentro de tu carpeta de configuración, solo si el archivo se acaba de escribir) y el arranque solo muestra los que están anotados. Si un `REANUDAR.md` no está anotado, te avisa en una línea y vos corrés `/arrancar`. Los cierres anteriores a esta versión no están anotados: en esas carpetas te va a avisar en cada apertura hasta el próximo `/cerrar`, y mientras tanto `/arrancar` lo lee igual.
- **`/cerrar` ya no se salta abrir la siguiente sesión por el cupo.** El cupo de Claude y «quiero seguir después» no son motivo para dejar de abrirla.
- `al-dia.sh` vuelve a poder ejecutarse directamente.
- Se activa solo con `/plugin update`; no hay nada que correr.

## 0.30.0 — 2026-10-10
- **Cada carpeta puede tener su lista de pendientes.** Vive en `.claude/PENDIENTES.md` (la plantilla viene en el plugin: `templates/PENDIENTES.plantilla.md`). `/metodo:cerrar` la actualiza al cerrar (tus filas, con un número que no cambia, y una línea con fecha en «Cambios» aunque no haya novedades). `/metodo:arrancar` te muestra hasta 3 pendientes de prioridad 1. Con `/metodo:pendientes` ves la lista completa en una tabla corta (ID · pendiente · prioridad · estado · quién), lo urgente primero y con «actualizada hace N días». Si la carpeta no tiene lista dice «Esta carpeta no tiene lista todavía»; ese comando no la crea: la crea `/metodo:cerrar` la primera vez que haya algo para anotar.
- **Si dos sesiones tocan la lista a la vez, se nota.** `cerrar-check` corre un control nuevo (`pendientes-check.py`, solo lee) que avisa de números repetidos, marcas de conflicto de git, estados mal escritos y cuando cerraste sin actualizar la lista. Sin lista, o en una carpeta sin git, dice que no aplica en vez de fallar.
- **Freno automático contra claves a la vista.** Un chequeo nuevo corre antes de cada comando que Claude lanza y lo frena si mostraría una contraseña, una llave o un token en pantalla (donde quedaría guardado en el historial): leer un archivo de claves (`.env`, llaves `.pem`, `.npmrc`…) con `cat`/`sed`/`awk`/`jq`, buscar adentro con `grep` sin contar, imprimir una variable que parece secreta, volcar todo el entorno. Te explica en castellano qué pasó y cómo verificarlo sin mostrarla (`grep -c` para saber si existe, un pedido que solo devuelva el estado para saber si anda, o mostrar solo el largo o las últimas 4 letras). **No frena** comandos normales: nombrar un archivo de claves en un texto o en un mensaje de commit, `process.env.NODE_ENV`, mirar si el archivo existe, contar sus líneas o copiarlo.
- Se activa solo con `/plugin update`; no hay nada que correr. Si Python no está, avisa y deja pasar (no rompe nada). Para apagarlo: sacá el plugin `metodo`.

## 0.29.0 — 2026-10-10
- **La sesión nueva sabe de qué venías hablando, aunque no escribas `/arrancar`.** Al abrir (o tras compactar) un programa chico, `contexto-reanudar.py`, lee el `REANUDAR.md` que dejó `/cerrar` y le muestra a la sesión la parte de estado: qué se hizo, **de qué veníamos hablando** y los pendientes. Solo lee: si no hay `REANUDAR.md` no muestra nada, y si el archivo tiene más de 3 días avisa que puede estar viejo. No muestra el contrato; para verificar copia y rama, numerar y archivar la serie sigue estando `/arrancar`. Se activa solo con `/plugin update`; no hay nada que correr.
- **`/cerrar` ahora deja «De qué veníamos hablando».** Son 3-4 líneas escritas mirando la conversación (no los archivos): el tema vivo, lo que pediste probar y lo que quedó sin responder. `/arrancar` lo dice primero en la confirmación, así «lo último que hiciste» tiene respuesta.
- **El prompt final de `/cerrar` se copia del archivo, no se vuelve a redactar.** Antes el chat podía salir más corto que el `REANUDAR.md` y se perdían cosas. Ahora es idéntico al archivo.
- **En la app de escritorio, `/cerrar` puede abrir la sesión siguiente sola.** Cuando todo dio ✓ y el avance está subido: emite el prompt completo y, en esa misma respuesta, abre la sesión nueva (que corre `/arrancar`), la separa de esta y archiva esta (se recupera desde la barra lateral). Si algo falla lo dice y queda la línea de siempre. En la terminal o en Cowork se saltea.
- **Control del `CLAUDE.md`.** Un programa nuevo, `claude-md-check.py`, corre dentro de `arrancar-check` y `cerrar-check`: dice cuánto pesa tu `CLAUDE.md` (si pasa de 30 KB es un aviso, no un error: la pregunta es qué bloque creció) y marca las filas de tabla larguísimas y los punteros a documentos que ya no existen. Sin `CLAUDE.md`, sin git o en una carpeta con espacios en el nombre, dice qué pasa en vez de fallar.
- **Regla 1 ampliada: verificá tu propio trabajo sin que te lo pidan.** Buscar cómo se prueba antes de decir «no hay tests»; unir y borrar nunca en el mismo paso (primero se prueba el resultado, recién después se borra lo sobrante); si ves un problema, parar y avisar aunque el pedido diga «está lista»; antes de borrar algo que no está en el control de versiones, leer qué contiene; decir qué se probó y qué no. Sigue siendo la regla 1, así que no cambia la cantidad (21): se actualiza sola en tu ficha global al abrir la sesión (con copia de la anterior).
- **`cerrar-check` suma dos cosas.** Avisa de las ramas ya unidas que siguen vivas (no propone borrar la actual ni las de otras copias abiertas) y agrega la pregunta «¿qué probaste del resultado?».
- Para apagarlo: sacá el plugin `metodo` (el aviso de apertura no tiene interruptor propio).

## 0.28.1 — 2026-10-09
- **«Poner todo al día» v10: puede archivar la sesión vieja de la serie sin frenarse.** Al abrir una sesión nueva, `/arrancar` archiva la sesión anterior de la misma serie (se puede desarchivar desde la barra lateral). En modo automático esa acción se frenaba por falta de permiso. Ahora «Poner todo al día» agrega solo esa línea (`mcp__ccd_session_mgmt__archive_session`) a los permisos de tu configuración, únicamente si falta. No toca ninguna otra clave, no pisa nada que ya tengas, deja antes una copia (`settings.json.antes-al-dia-permisos`) y escribe sobre una copia de trabajo que recién al final reemplaza el archivo: un corte a mitad no lo deja roto. Si no puede, lo dice en la línea final. Tu configuración puede quedar guardada con otro formato (en una línea y con las claves en otro orden); el contenido es el mismo.
- Para sacarlo: borrá esa línea de `permissions.allow` en tu configuración (la próxima puesta al día la vuelve a agregar; para que no lo haga, desinstalá el plugin `metodo`).

## 0.28.0 — 2026-10-09
- **Arrancar y cerrar ya no se pueden saltear pasos sin que se note.** Dos programas nuevos, `arrancar-check.py` y `cerrar-check.py`, hacen la comprobación mecánica: una línea ✓/✗ por paso y un cierre claro («Arranque completo ✓» / «Cierre completo ✓», o «Falta: … ✗»). Solo leen: no escriben nada, no usan internet y nunca muestran el valor de una clave (de una posible clave solo dicen en qué línea está). Por qué: se vio que una sesión puede olvidarse de un paso escrito (archivar la serie anterior, dejar el handoff, subir lo guardado) y nadie lo notaba; ahora la salida del programa se pega en la confirmación y lo que falta queda a la vista.
- **Al arrancar** mide: que exista el cierre anterior (`REANUDAR.md`) y su fecha, que la copia y la rama sean las que declara el texto de arranque (si no coinciden, frena), el estado de git, y qué versión del método y qué última regla tenés. Lista lo que quedó «A VERIFICAR» y deja como ítems MANUAL lo que solo puede hacer la sesión (numerar el título, ofrecer archivar la serie anterior, comparar el modelo con el ruteo del radar).
- **Al cerrar** mide: que `REANUDAR.md` tenga su línea de cierre y entre en un largo razonable, que no lleve números de memoria («hay 12 archivos») ni algo con pinta de clave, que el avance esté guardado y subido (y que el último guardado no se haya llevado de más: señal de un `git add -A`), que haya handoff si se tocaron 3 o más archivos, y que un repo con varias copias declare cuál es la suya. Deja como ítems MANUAL que lo durable haya bajado a su archivo y que el contrato del prompt tenga contenido real.
- `/metodo:arrancar` (paso 3 quater) y `/metodo:cerrar` (paso 8 bis) ahora exigen correrlos antes de confirmar y antes del prompt final; el prompt de reanudación sigue siendo el último mensaje del cierre. No hay que instalar ni correr nada a mano: viaja con el plugin.
- Para apagarlo: sacá esas dos líneas de las skills (o el plugin `metodo`). Si el programa no se puede correr, la sesión lo dice en vez de simularlo.

## 0.27.1 — 2026-10-09
- **El buzón ya no dice «no hay mensajes nuevos» cuando no pudo mirar.** Si tu copia estaba en una rama con otro nombre que la del buzón en GitHub (por ejemplo «master» y «main»), no traía nada y no avisaba. Ahora trae la rama del buzón igual, y si no puede traer lo nuevo dice «Falta: no pude traer lo nuevo de GitHub ✗» en vez de «no hay nada».

## 0.27.0 — 2026-10-09
- **Regla 21: antes de elegir un servicio técnico, los criterios.** Claude consulta la skill `decisiones-tecnicas` (base-segura) aunque nadie la nombre y aunque la decisión aparezca a mitad de otro trabajo; si la decisión es nueva, la anota en la ficha de la empresa.

## 0.26.0 — 2026-10-09
- **El método ahora conoce las funciones oficiales de Claude Code.** Hay un mapa (`radar/FUNCIONES.md`) con una fila por función (Mods, `/goal`, canales, rutinas, worktrees, subagentes con su `model` y `effort`, hooks, skills, plugins, `/loop`, ultracode, sesiones en la nube, tareas programadas…): qué es, cuándo conviene, cuándo no y el enlace a la doc oficial. Se consulta con `radar.py funciones <palabra>`.
- **El robot del radar vigila la documentación oficial.** Cada día mira si hay páginas nuevas en la doc de Claude Code, si cambió alguna de las páginas que respaldan el mapa y si salió una versión nueva de Claude Code, Codex o Gemini CLI. Si algo cambia, abre un pedido de cambio con el aviso y **no se publica solo**: lo revisa una persona. Un parche suelto no avisa.
- **Al abrir la sesión también te dice qué IA de otro proveedor conviene.** Una línea nueva con la mejor opción para imágenes, video, investigación en la web, transcripción, voz y tareas mecánicas baratas. Ahora son 5-6 líneas. Quien mantiene el catálogo recibe además un aviso si la doc cambió y el mapa quedó atrás (`radar.py funciones --pendientes`); a vos no te llega, porque no podrías rehacer la fila.
- **Control mensual del ruteo** (`scripts/control-ruteo.py`). Lee tus conversaciones guardadas, solo cuenta (nunca copia texto) y devuelve 3 líneas: qué modelo y esfuerzo usaron los subagentes, cuántas tareas fueron a Codex y a Gemini, y cuántas se hicieron con más modelo del que la tabla recomienda.
- Para apagarlo: sacá el plugin `metodo`. El control mensual no corre solo: se usa a mano.

## 0.25.0 — 2026-10-08
- **Cada sesión arranca sabiendo qué modelo, qué esfuerzo y qué IA conviene hoy.** Al abrir la sesión aparecen 4-5 líneas: qué modelo es hoy Haiku, Sonnet y Opus, un punto de partida de nivel y esfuerzo de Claude por tipo de tarea (cada «sí» a ¿hay que juzgar?, ¿el error sale caro?, ¿hay mucho contexto? lo sube un escalón), cuánto cupo queda en Claude, Codex y Gemini, y los avisos que importan. Lee solo archivos de tu computadora: no usa internet, no lanza ningún programa y tarda una fracción de segundo. Si algo falla, no muestra nada y la sesión abre igual. El cupo sale de lo que ya dejó anotado el Bicho; si no lo tenés, dice «sin dato» en vez de inventar.
- **El punto de partida sale de la evidencia del radar, no de criterio propio.** Cada fila de la tabla cita las mediciones independientes que la respaldan. Donde no hay medición (casi todo lo de esfuerzo, y los niveles de revisar, investigar y arquitectura) la fila queda marcada con «*» como provisoria y vale la política de modelos tal cual (no se baja un escalón por falta de datos, para no dejar corta una tarea donde el error sale caro). El control mensual va a mostrar si hubo que ajustarlas.
- **El radar se entera solo de los modelos nuevos.** El robot que actualiza el radar cada día ahora también mira si salió una versión más nueva de cada familia (Haiku, Sonnet, Opus, Fable, GPT, Gemini), solo si la publica el proveedor, con fecha de alta y sin vistas previas. Anota la última en `vigentes` y, si algún plan quedó atrás, lo avisa en el pedido de cambio y en la línea de aviso de cada sesión. Una versión nueva **no se publica sola**: el pedido de cambio queda abierto hasta que una persona lo revise (precios, rankings y retiros siguen automáticos). El orden A/B/C lo sigue decidiendo una persona. Corregido hoy: el plan C de «tareas mecánicas baratas» decía Haiku 4.5 y pasó a Haiku 5.5.
- **Consejos de uso de cada proveedor.** El robot vigila cada día seis guías oficiales (prompting y migración de Anthropic, OpenAI y Google) y avisa en el pedido de cambio cuando cambian. En `radar/consejos/` hay un resumen de hasta 10 líneas por modelo vigente, con la fuente arriba. Los resúmenes no los escribe el robot: `radar.py consejos --pedido` baja las guías y prepara el pedido para la IA más barata (Gemini o Codex con `delegar.py`; si solo queda Claude, Haiku con esfuerzo bajo; nunca Opus). Al abrir la sesión, una línea avisa cuando hay consejos nuevos, cuando una guía cambió y los resúmenes son anteriores (el aviso queda hasta que se rehagan) y, una vez por semana, cuando una skill de prompting instalada es de una generación anterior al modelo vigente (por ejemplo la de GPT 5.4 con GPT 6 vigente).
- **Recordatorio al delegar.** Cuando Claude abre un subagente o una sesión nueva, se suma una sola línea de contexto si falta el `model`, si pide más nivel o esfuerzo del que la tabla recomienda para esa tarea (con un escalón de tolerancia en las filas provisorias) y si Codex o Gemini tienen cupo libre. Llega junto al resultado de esa llamada, así que ayuda a las delegaciones que siguen. Es solo un recordatorio: nunca bloquea nada ni cambia lo que se pidió, y no se repite más de unas pocas veces por sesión.
- **Reglas 18 y 20.** La 18 ahora cubre también el modelo y el esfuerzo de Claude (se eligen con la tabla del radar, no de memoria). La 20 ya no dice «con Sonnet»: dice «con un modelo más barato que el tuyo» y manda a la tabla para saber cuál.
- Para apagarlo: sacá el plugin `metodo` o pedile a Claude que quite los dos hooks nuevos de `hooks/hooks.json`.


## 0.24.0 — 2026-10-08
- **«Poner todo al día» v9.** Instala NotebookLM (`notebooklm-py` 0.8.3) en su propio Python 3.12 con uv, desde el wheel verificado por su huella, índice fijo de PyPI, sin compilar código fuente y con dependencias congeladas al 2026-10-01, más su navegador (playwright chromium); no inicia sesión. Avisa una vez cuando cambia la plantilla de la ficha de la empresa. Corre el chequeo del equipo (solo lectura, tope de 60 s, con el Python de la Mac primero) y suma lo que falte a la línea final. Los avisos que no son fallas salen en una línea «Además: …» y `al-dia.aviso`, que se muestra una vez al abrir sesión.

## 0.23.0 — 2026-10-08
- **Regla 20: cuándo abrir otra sesión (con Sonnet) y cuándo seguir en la misma.** Claude propone una sesión aparte para trabajos medianos o grandes que no pisan archivos de otra sesión; la que deriva revisa lo entregado antes de darlo por hecho. Se suma sola a tus reglas del método (ya son 20).

## 0.22.5 — 2026-10-08
- **al-dia v8: en la app de escritorio los paquetes vuelven a actualizarse al abrir sesión.** La app arranca Claude Code con la actualización automática apagada, y eso frenaba también la de los paquetes del catálogo. «Poner todo al día» ahora deja prendida `FORCE_AUTOUPDATE_PLUGINS` en tu configuración (la lee solo Claude Code) y avisa si no pudo.

## 0.22.4 — 2026-10-08
- **Regla 16, tareas que se repiten solas:** cuándo usar `/loop` (vigilar algo, cada 15 minutos o más) y el «Ralph» del catálogo (repetir hasta que salga bien, siempre con tope de vueltas y solo con pruebas o informes que solo leen). Nunca un bucle que escriba solo en el sistema de gestión, las publicidades o la lista de clientes.

## 0.22.3 — 2026-10-07
- **«Poner todo al día» deja huashu-design listo para exportar a PDF, PPTX y video:** instala sus librerías cuando cambia el paquete y el navegador interno con el que exporta (con tiempo límite y una segunda forma de bajarlo, verificada contra Google, si el instalador se cuelga). La primera vez baja unos 300 MB. Además, la puesta al día automática vuelve a instalar las skills oficiales de diseño de interfaces y de crear skills (en 0.21.6 solo lo hacía la corrida a mano).

## 0.22.2 — 2026-10-07
- **Numerar sesiones también sin grupo:** al arrancar, la sesión nueva toma el número siguiente de la serie aunque tus sesiones no estén en ningún grupo de la barra lateral, o aunque alguna haya cambiado de grupo: la serie se arma por carpeta. Además respeta los ceros adelante y el separador que uses («PM - Estudio . 03» → «PM - Estudio . 04»).

## 0.22.1 — 2026-10-07
- **Avisos de inicio solo en las carpetas que elijas:** si tenés muchos proyectos y no querés ver los mensajes del vigía o del buzón en todas las sesiones, ahora podés limitarlos con el archivo opcional `<config de Claude>/metodo/avisos.json` (por ejemplo `{"vigia": ["~/Proyectos/Tech"], "buzon": ["~/Proyectos/Consultoria-IA"]}`). En esas carpetas o en cualquiera de sus subcarpetas te avisa; en las demás no te distrae, aunque el detector de fondo del vigía sigue corriendo igual para mantener las novedades al día. Sin ese archivo, sigue funcionando como siempre.

## 0.22.0 — 2026-10-07
- **Nombres prohibidos para cualquiera:** el control que frena la subida de clientes o personas a repositorios públicos o compartidos ya no depende de carpetas del autor. Ahora guarda tu lista en `<config de Claude>/metodo/nombres-prohibidos.txt`, con permisos solo para vos (600), y sumás nombres con `nombres-prohibidos agregar "<nombre>"` o pidiéndoselo a Claude. Si la lista no existe o está vacía, no te traba el push; y si el plugin se actualiza, el control busca solo la versión nueva. La regla 3 ahora le pide a Claude instalarlo antes de subir por primera vez un repositorio compartido.
- **Skills externas fáciles de actualizar:** el actualizador de skills ajenas (`skill-externa`) ahora se invoca directo desde el paquete instalado sin rutas fijas a la máquina del autor. Te permite tener skills copiadas de otros repositorios manteniendo tus reglas en `NOTA-LOCAL.md` y parches de código, para actualizar a versiones nuevas del autor sin perder lo tuyo ni fusionar a mano.

## 0.21.6 — 2026-10-06
- **«Poner todo al día» instala las skills oficiales de diseño de interfaces y de crear skills.** Antes cada una venía copiada en un paquete del catálogo, y si además tenías la oficial quedaban repetidas. Ahora se instala la oficial de Anthropic (`frontend-design` y `skill-creator`) y los paquetes `base-segura` y `rubro-estudio-arquitectura` ya no traen su copia: una sola pieza por función. Si ya las tenés instaladas, no cambia nada. Si algo no se pudo instalar, el cierre lo dice.

## 0.21.5 — 2026-10-05
- **El vigía te avisa si Google cambia el instalador de Antigravity.** Hasta ahora, si Google cambiaba ese instalador, «Poner todo al día» dejaba de instalarlo pero en segundo plano nadie se enteraba. Ahora el vigía (solo si tenés Antigravity instalado) compara el instalador publicado por Google con el que revisamos; si es distinto, te lo anota como novedad para que se lo reportes a quien mantiene el catálogo. No lo instala ni lo ejecuta: solo lo compara. Es el único sitio nuevo con el que habla el vigía (`antigravity.google`).

## 0.21.4 — 2026-10-05
- **El radar ya no abre el navegador de Antigravity.** Para medir el cupo de Gemini, el radar le preguntaba a Antigravity «¿cuánto te queda?»; si nunca habías entrado con tu cuenta de Google, eso abría una ventana pidiéndote que inicies sesión. Ahora solo le pregunta si ya lo usaste alguna vez (mira que exista su historial, sin abrirlo); si no, lo saltea y te dice «sin usar todavía». Para usarlo, corré `agy` una vez e iniciá sesión.

## 0.21.3 — 2026-10-05
- **Antigravity ya no se abre solo.** En la 0.21.2, probar el estado de Antigravity sin tener sesión iniciada podía abrir el navegador pidiéndote entrar con tu cuenta de Google. Ahora «Poner todo al día» no ejecuta Antigravity nunca: solo comprueba que esté firmado por Google (con la cadena de Apple completa). Y lo instala solamente cuando lo corrés a mano, nunca en la actualización automática de fondo. Si Google cambia su instalador, no se instala y lo dice, sin frenar el «Todo al día». Si se corta la instalación o la conexión, queda marcado con ⟳ para repetir el comando.

## 0.21.2 — 2026-10-05
- **«Poner todo al día» instala Antigravity (Gemini) de Google.** Va a tu carpeta de usuario, sin contraseña, con el instalador oficial de Google, que solo se corre si es exactamente el que revisamos (si Google lo cambia, no se corre y el mensaje te dice que le avises a Fernando). Cada día se vuelve a comprobar que el programa esté firmado por Google. Lo que le pases a Gemini sale a Google con tu cuenta y, en el plan gratis, Google puede usarlo para mejorar sus modelos: al instalarlo te lo avisa. Entrar con tu cuenta de Google se hace una vez, aparte.

## 0.21.1 — 2026-10-05
- **El radar y `delegar.py` saltean la IA que no está instalada o no tiene cuenta.** Antes, en una computadora sin Antigravity (`agy`) o con Codex instalado pero sin haber iniciado sesión (`codex login`), el radar decía «cupo desconocido», no la salteaba, `delegar.py` la elegía y fallaba. Ahora esa IA se salta igual que una con el cupo agotado, y la salida dice por qué («Antigravity: no está instalada», «Codex: sin sesión iniciada»). Si no queda ninguna otra, `delegar.py` te dice que lo hagas en la sesión de Claude.

## 0.21.0 — 2026-10-05
- **El radar ahora mide el cupo de Claude, de Codex y de Antigravity (Gemini), no solo el de Codex.** Antes siempre te decía «Claude» porque nunca veía que se te acababa o que el de Gemini estaba sin usar. Si el cupo de un plan está agotado, lo salta; si está alto, avisa «solo tareas chicas».
- **Nuevo: `delegar.py` (junto a `radar.py`).** Le das una categoría, la carpeta del repo y la tarea; mide el cupo, elige la IA que conviene dejando a Claude de coordinador, la ejecuta (Codex o Antigravity) y te deja el cambio sin guardar para que corras los tests y lo revises. Con `--revisar` solo lee y te da un informe.
- **Cuidados:** la primera vez pide una aceptación (`delegar.py --aceptar`) porque el código del repo viaja a OpenAI o a Google y los planes gratuitos pueden entrenar con lo que reciben; se niega en tu carpeta personal y en carpetas de Finanzas, Personal o clientes (se amplía con `METODO_NO_DELEGAR`); no ejecuta nada del repo (git sin hooks), corta la herramienta si pasa de una hora y avisa si toca la configuración del repo.
- La regla 18 del método y la skill `radar` explican cuándo usarlo. Un cupo sin usar es plata tirada.

## 0.20.1 — 2026-10-05
- «Poner todo al día» pasa solo a la rama estable también en la actualización automática (como mucho un intento por semana); antes guarda una copia de todo, instala metodo primero y, si algo falla, deja la configuración como estaba. Una descarga colgada ya no espera al tope de 30 minutos.

## 0.20.0 — 2026-10-04
- **Las actualizaciones del catálogo te llegan con dos días de demora, a propósito.** Ahora hay una rama «estable» que va 48 horas detrás de lo último que se publica. Si alguien llegara a meter algo malo, hay dos días para verlo y sacarlo antes de que llegue a tu computadora. Lo urgente se adelanta a mano, en el momento. Al pegar «Poner todo al día», tu catálogo pasa solo a esa rama: guarda antes una copia con fecha de tu configuración, deja apagado lo que tenías apagado y, si algo falla, vuelve a como estaba.
- **El vigía ya no propone actualizar por su cuenta los plugins de este catálogo:** esos llegan por la rama estable. Sigue avisando de todo lo demás.
- **«Poner todo al día» más firme.** Una sola puesta al día a la vez (la manual y la automática no se pisan). En modo automático, un paquete nuevo solo entra si es del propio catálogo o viene de afuera fijado a una versión exacta; si no, queda para cuando pegues el comando a mano.
- **markitdown arreglado:** en una computadora nueva fallaba al instalarse; ahora queda en una versión fija y funciona. Codex se instala sin correr scripts de instalación.
- La puesta al día automática corta lo que quede colgado pasados 30 minutos, y las copias de tu ficha global quedan con los mismos permisos que la ficha.
- **El buzón frena más tipos de clave:** además de las que ya reconocía, ahora no sube un mensaje que tenga algo con forma de clave de Stripe, Notion, Hugging Face, Figma, npm, GitLab o un bot de Telegram.

## 0.19.0 — 2026-10-03
- Regla 19: una pieza por función; antes de crear una skill o un agente, Claude se fija si ya existe uno que haga lo mismo. Nunca borra skills para hacer lugar. Te llega sola a tu ficha, sin tocar lo tuyo.
- **Nuevo: el mapa de tu código, a pedido.** Parado en un proyecto, le decís a Claude «mapeá este repo» y arma el mapa de Graphify en el orden seguro: el mapa nunca se sube, no toca la configuración general de tu computadora y guarda solo `.gitignore` y `CLAUDE.md`. Es el modo gratis (solo código, sin IA). Necesita Graphify 0.9.65, la versión revisada; si falta o tenés otra, te dice en una línea el comando para ponerla.
- **Nuevo: chequeo de seguridad mensual de tus repositorios.** Una vez por mes, en segundo plano, revisa los repos que anotaste: claves con permisos abiertos o guardadas en el repositorio, `.gitignore`, repositorio público, flujos de GitHub sin fijar. Solo mira, no cambia nada, y nunca muestra el valor de una clave. Si algo falla, al abrir Claude te aparece una línea: avisale a quien te acompaña. Para sumar un repo: «sumá este repo al chequeo de seguridad». Sin lista, no hace nada.
- El radar se actualiza solo cuando cambian las fuentes públicas, con controles: solo cambia la lista, pasa las pruebas antes y, si algo no cierra, espera a que lo revise una persona.

## 0.18.1 — 2026-10-03
- **El radar suma fuentes** (Design Arena, EQ-Bench, Open ASR y más pruebas de Artificial Analysis). Programar y escritura ya tienen el orden respaldado por dos rankings independientes. Cambia el orden donde los datos lo pedían: para transcribir, primero ElevenLabs; para documentos largos, primero Claude.

## 0.18.0 — 2026-10-03
- **Todo te llega solo.** Al abrir Claude Code, tus reglas del método se ponen al día solas. Una vez por día, sin que hagas nada y sin demorar el arranque, Claude instala los paquetes nuevos de Fernando y pone al día el resto. Si algo no se pudo, al abrir te aparece una sola línea con qué falta: mandásela a Fernando. «Poner todo al día» queda para la primera vez.

## 0.17.0 — 2026-10-03
- **Nuevo: `/metodo:radar`, qué IA conviene usar para cada cosa, con plan B y C.** Programar, revisar código, diseño, escribir en castellano, investigar en la web, documentos largos, imágenes, video, transcripción, voz, planillas, tareas baratas y agentes de tarea larga: cada una con un plan A, un B y un C. Le decís a Claude «¿qué uso para esto?» y te da el primero que esté disponible: si el A tiene el cupo de Codex agotado, el modelo ya se retiró o no admite datos privados, pasa al B y te avisa por qué.
- Regla 18: para elegir qué IA usar, consultá el radar; nunca de memoria.
- Cada tanto, el catálogo revisa fuentes públicas (rankings, precios y retiros de modelos) y propone cambios al radar; una persona los aprueba, nunca se aplican solos. Al arrancar, `/metodo:arrancar` avisa en una línea si el radar tiene más de 14 días o se acerca el retiro de un modelo que usamos.
- **Imparcial:** el orden no sale de preguntarle a una IA ni de lo que dice cada fabricante, sino de rankings de terceros. Mientras una categoría no tenga al menos 2 que lo respalden, te avisa «orden provisorio».
- Lo marcado «[a verificar]» viene de una investigación que todavía no se leyó de primera mano: sirve para decidir, no para citar como cifra.

## 0.16.6 — 2026-10-03
- Regla 17: lo que le pedís a otro, empaquetalo en un comando.
- **Nuevo: `/metodo:buzon`, para hablar con quien te acompaña sin copiar y pegar por WhatsApp.** Un repositorio privado de GitHub, solo para ustedes dos, hace de buzón. Le decís a Claude «revisá el buzón» y te muestra lo que te mandaron, uno por uno, y te pregunta «¿lo hago?»: nunca hace nada solo. Si algo te da error, «avisale que se trabó» y Claude arma el mensaje con el paso, el comando, el error completo y tus versiones, te lo muestra y lo sube solo si decís que sí.
- **Te cuida:** si un mensaje tiene algo con forma de clave, no lo sube. No viajan archivos, solo texto. Lo que pide borrar, publicar, pagar o tocar una cuenta se marca y pide un sí aparte.
- Al abrir Claude, si hay mensajes, aparece «Buzón: N mensajes nuevos». Si no lo configuraste, no hace nada. Cómo se arma y el consentimiento de una página: `docs/BUZON.md` y `docs/BUZON-CONSENTIMIENTO.md` del catálogo.

## 0.16.5 — 2026-10-03
- Regla 16: mirar el cupo (Claude y otras IA) antes de trabajo pesado; una tarea grande a la vez. `scripts/codex-cupo` mide el cupo de Codex sin red.

## 0.16.4 — 2026-09-28
- `/metodo:arrancar`: si quedaron abiertas sesiones anteriores del mismo grupo (por ejemplo «Ventas 6» y «Ventas 7» cuando abrís la 8), te pregunta en una línea si las archiva. Solo las archiva si decís que sí, se pueden recuperar cuando quieras y nunca se borran.

## 0.16.3 — 2026-09-28
- `/metodo:arrancar` le pone número a la sesión nueva en la app de escritorio. Si la anterior del mismo grupo se llamaba «Ventas 7», la nueva pasa a «Ventas 8». No toca un nombre que ya pusiste vos, y fuera de la app de escritorio no hace nada.

## 0.16.2 — 2026-09-27
- Formato: la descripción de `/metodo:crear-agente` cumple las reglas de claude.ai (hace lo mismo que antes).
- `/metodo:cowork`: la primera vez sube el repositorio aunque todavía no tengas ninguna skill marcada. Antes no subía nada y Cowork no podía agregarlo.

## 0.16.1 — 2026-09-27
- `/metodo:cowork` ahora encuentra también las skills que creás en la carpeta de tu proyecto (`<proyecto>/.claude/skills`), no solo en `~/.claude/skills`. Se suma una vez, a pedido. Si la misma skill está en las dos carpetas, no la sube hasta que quede una sola.
- Si tu llave de GitHub solo abre repositorios elegidos, no puede crear uno nuevo. Ahora el camino normal es: creás el repositorio vacío y privado desde la web, y Claude lo conecta.
- Corrección: el catálogo seguía anunciando la versión anterior de `metodo`, y la actualización podía no llegarte. Ya coincide.

## 0.16.0 — 2026-09-27
- **Nueva: `/metodo:cowork`, para usar tus skills propias en Cowork sin subirlas a mano.** Si subías una skill desde la web de Claude, quedaba como una copia suelta: la cambiabas en Claude Code y Cowork seguía con la vieja. Ahora le pedís a Claude «publicá mi skill en Cowork» y él la copia a un repositorio privado tuyo en GitHub, la revisa y la sube. Cowork la toma de ahí, siempre en la última versión.
- **Te cuida de dos errores:** si una skill está mal armada, no la sube y te dice qué tiene (una sola mal armada hacía fallar todas en Cowork). Si encuentra algo con forma de clave, no sube nada.
- **La primera vez hay un paso tuyo en Cowork:** agregar el repositorio como marketplace. Claude te da la dirección exacta. Necesita `gh` (la herramienta de GitHub) con tu sesión iniciada: detalle en `requisitos.md`.

## 0.15.2 — 2026-09-27
- Vigía: si corregís la ruta de origen de una pieza en tu catálogo, el aviso viejo se cierra en la corrida siguiente. Antes podía quedar colgado hasta 30 días.

## 0.15.1 — 2026-09-27
- **El vigía ahora ve lo que antes se le escapaba.** Si mantenés un catálogo propio de herramientas (para la mayoría de los usuarios no aplica), compara cada pieza contra la versión exacta de la que salió, mirando solo su carpeta. Antes solo notaba los cambios entre una corrida y la siguiente: una copia que ya estaba atrasada cuando la vio por primera vez nunca aparecía, y avisaba por cambios del repositorio que no tocaban la pieza.
- Lo que no declara de qué versión salió figura aparte, como «sin versión fijada», y no infla el número de novedades.
- Las novedades que dejan de aplicar (por ejemplo, porque ya actualizaste) se cierran solas.

## 0.15.0 — 2026-09-27
- **El vigía ya no te pregunta por lo que es seguro.** Si una herramienta que tenés instalada saca una versión nueva, Claude la revisa. Si pasa la revisión y no rompe nada, la actualiza y te cuenta qué cambió y cómo volver atrás. **Te pregunta solo** si la versión nueva cambia nombres o comandos (y te dice qué tuyo se ve afectado), si es una herramienta nueva o si hay un riesgo real (claves, costo, datos que salen). Lo que fija tu consultor sigue sin moverse: se lo reportás.
- Nuevo en la revisión: Claude compara lo que tenés instalado contra la versión nueva, no solo lo último que cambió. Así detecta cuando el autor renombró cosas en el medio.
- Plantillas de agentes: el ejemplo de skill del cotizador ahora dice `pricing` (antes `pricing-strategy`), por el cambio de nombre del rubro 0.14.0.

## 0.14.0 — 2026-09-27
- **Nuevo: el vigía de actualizaciones (`/metodo:vigia`).** Cuando algo de lo que instalaste (plugins, conectores MCP, herramientas de línea de comandos) saca una versión nueva, nadie te avisa. Ahora sí: al abrir una sesión, Claude te dice «Vigía: N novedades». Le pedís «revisá las novedades del vigía» y te propone como mucho 5, con sí o no. **Nunca instala nada solo.** Si una pieza la fijó tu consultor, no la movés vos: se la reportás.
- **Cómo funciona:** al abrir cada sesión corre un chequeo de menos de un segundo, que solo lee una fecha. La búsqueda de verdad se hace como mucho una vez por semana, en segundo plano, sin usar tu plan de Claude.
- **Qué consulta:** solo GitHub, npm y PyPI, para saber la última versión. Esos sitios ven qué herramientas consultás, como en cualquier chequeo de actualizaciones. No manda datos a nadie más, no usa tus claves y no lee las claves de tus conectores.
- **Viene prendido.** Para apagarlo: creá el archivo `~/.claude/vigia/apagado` (o `VIGIA_OFF=1`). Funciona en Mac, Linux y Windows. En Windows necesita Git for Windows y Python 3.9 o más nuevo: detalle en `requisitos.md`.

## 0.13.0 — 2026-09-26
- **Nueva: `/metodo:darwin-skill`, para revisar y mejorar tus skills.** Evalúa cada skill con una rúbrica de 9 puntos, prueba una mejora por vez, la hace juzgar por agentes independientes (el que la escribió no la califica) y te pide confirmación antes de quedarse con el cambio. Si no mejora, lo deshace. Es de un autor externo (alchaincyf/darwin-skill, 6.1K★, MIT), copiada del commit auditado.
- **Trae una regla de uso adentro:** guarda y deshace sus cambios con git, así que corre **siempre en una copia aparte** de tu carpeta. Si la usás donde trabajan otras sesiones, les cambiaría la rama o guardaría aparte el trabajo que no subieron. La regla está en la propia skill, así que viaja con ella.

## 0.12.2 — 2026-09-26
- **El `.gitignore` de fábrica (`gitignore-estudio`) ahora también ignora `.omc/`.** Si instalás
  `oh-my-claudecode-fixed`, esa carpeta guarda el estado de cada sesión y el registro de qué hizo —
  no es tu trabajo, y sin esta línea el primer `git add` la subía entera al repo.

## 0.12.0 — 2026-09-22
- Sin cambios; acompaña al catálogo 0.12.0 (paquete nuevo `escala-desarrollo`: dos revisores para tu app).

## 0.11.5 — 2026-09-22
- **Regla 15: copiar no es resumir, y el conteo no lo demuestra.** Cuando Claude pasa contenido de un lado a otro (una planilla a una base, PDFs a notas, fichas de clientes a otro sistema), puede devolver la misma cantidad de piezas, con la misma forma, pero resumidas o inventadas. Contar no lo delata. La regla pide verificar texto contra texto y no archivar ni borrar el original hasta que todo pase.
- **La medición viene con el kit: `scripts/verificar-copia.py`.** Solo lee. Por cada pieza del original mide qué parte de su texto aparece en la copia, y sale en rojo si alguna queda por debajo del 85%. También sale en rojo si hay archivos que no pudo medir (PDF, Word, Excel): esos se pasan antes a texto con `markitdown`, así nunca te dice «todo bien» sobre algo que no miró.
- **Regla 11 corregida:** decía que dos sesiones en la misma carpeta se pisan siempre. Desde 0.11.2 no es así: en la misma rama conviven, porque cada cierre sube solo lo suyo. La copia aparte (`/metodo:otra-sesion`) sigue siendo lo más prolijo. Hace falta de verdad solo si las sesiones usan ramas distintas o van a editar el mismo archivo a la vez.
- **`/metodo:cerrar` comprueba mejor que Graphify no se suba.** Antes podía dar por buena una regla escrita solo en la configuración interna de tu computadora, que no viaja con el proyecto. Ahora exige que la regla esté en el `.gitignore` del proyecto.
Para actualizar: `claude plugin update metodo@claude-catalogo`.

## 0.11.4 — 2026-09-22
- **Corrige un error de 0.11.3: tu `.claude/settings.json` vuelve a viajar con el proyecto.** En 0.11.3 el `.gitignore` de fábrica lo ignoraba entero para que no se subieran los enganches de Graphify. Pero ese archivo también lleva lo compartido del proyecto, como el catálogo pre-listado, que es lo que hace que una computadora nueva ya lo tenga declarado. Ignorarlo entero rompía eso. Lo detectó Consultoría antes del primer guardado de un cliente.
- **Ahora se parte en dos, como Claude Code ya lo prevé:** `.claude/settings.json` viaja (lo compartido) y `.claude/settings.local.json` no viaja (lo de esta computadora, incluidos los enganches de Graphify).
- **`/metodo:cerrar` hace la mudanza solo:** si Graphify dejó sus enganches en `settings.json`, los pasa a `settings.local.json` sin tocar nada más. Si tu `.gitignore` es el de 0.11.3, le saca la línea de `settings.json` y pone la de `settings.local.json`.
- Probado con una sesión real, simulando otra computadora: con 0.11.3 el catálogo pre-listado no llegaba nunca al repositorio; con 0.11.4 llega, sin los enganches de Graphify.
Para actualizar: `claude plugin update metodo@claude-catalogo`.

## 0.11.3 — 2026-09-22
- **Si usás Graphify, el mapa nunca se sube, aunque nadie se acuerde de la regla.** Graphify arma en tu carpeta un mapa (`graphify-out/`) con textos sacados de tus archivos, y agrega unos enganches de Claude que solo sirven en tu computadora. Hasta ahora, evitar que se subieran dependía de que leyeras la regla 1 de `docs/GRAPHIFY.md` antes de instalarlo.
- **El `.gitignore` de fábrica ya trae el bloque «Graphify».** Si arrancás una carpeta nueva con él, está cubierto desde el día uno.
- **Si tu carpeta ya tiene su `.gitignore`, `/metodo:cerrar` lo completa solo:** cuando ve un mapa de Graphify que tu proyecto no ignora, agrega el bloque, lo sube junto con tu trabajo y te lo cuenta en la confirmación. Sin preguntas.
- Se comprueba de forma que valga en cualquier computadora, no solo en la tuya: la regla queda escrita en el proyecto y viaja con él.
Para actualizar: `claude plugin update metodo@claude-catalogo`.

## 0.11.2 — 2026-09-22
- **`/metodo:cerrar` ahora sube solo lo que hizo esa sesión.** Antes subía todo lo que hubiera en la carpeta (`git add -A`). Si tenías dos ventanas de Claude abiertas en la misma carpeta, la primera que cerraba se llevaba el trabajo a medias de la otra y lo subía con su nombre y su descripción. Ahora cada sesión sube sus propios archivos. Si ve cambios que no son suyos, no los toca: te los lista («quedaron sin subir cambios que no son de esta sesión») y los sube la sesión que los hizo cuando cierre.
- **Podés trabajar con varias sesiones en la misma carpeta.** `/metodo:otra-sesion` sigue siendo lo más prolijo (cada sesión en su copia), pero ya no es condición para que el cierre salga bien. Lo único que no se puede separar es un mismo archivo editado por las dos a la vez: lo sube la primera que cierra, y la segunda te avisa.
- **`/metodo:otra-sesion`** aplica la misma regla al guardar antes de abrir la copia, y la **regla 13** de `REGLAS-DEL-METODO.md` lo dice explícito.
- Sin cambios en las frenadas de siempre: archivo con pinta de clave, documento o plano nuevo, conflicto, carpeta sin repositorio.
Para actualizar: `claude plugin update metodo@claude-catalogo`.

## 0.11.1 — 2026-09-22
- Sin cambios; acompaña al catálogo 0.11.1 (`base-segura`: cuenta de skills corregida + chequeo automático de metadatos antes de publicar).

## 0.11.0 — 2026-09-22
- Sin cambios; acompaña al catálogo 0.11.0 (`base-segura`: `docs/GRAPHIFY.md`).

## 0.10.1 — 2026-09-22
- Sin cambios; acompaña al catálogo 0.10.1 (corrección: los agentes de `base-segura` y `rubro-estudio-arquitectura` pasan a nombre genérico de modelo, como manda la guía de ruteo de 0.9.0).

## 0.10.0 — 2026-09-22
- Sin cambios; acompaña al catálogo 0.10.0 (`base-segura`: la pregunta 1 del filtro pasa a tener tres caminos).

## 0.9.0 — 2026-09-22
- **Nueva guía `templates/RUTEO-DE-MODELOS.md`: qué cerebro usa cada agente.** Claude viene en varios modelos y cada agente declara con cuál piensa. Hasta ahora eso se elegía a ojo, y se paga de las dos maneras: un agente que tiene que razonar puesto en un modelo chico entrega trabajo pobre, y uno que hace tareas mecánicas en el modelo caro te consume la cuota varias veces más rápido.
- **El criterio ya no es el tema de la tarea, son tres preguntas:** ¿hay que **juzgar o decidir**, o solo ejecutar algo ya decidido? · ¿**equivocarse sale caro**, o el error se ve enseguida? · ¿hay que **sostener mucho contexto** o muchos pasos encadenados? Se cuentan los sí: **0 → Haiku · 1 → Sonnet · 2 → Opus · 3 y tarea larga → Fable, pedido en el momento.** Ante la duda, el escalón de abajo: subir después es cambiar una palabra. Por qué cambió: «el modelo caro solo para temas legales o financieros» estaba mal planteado — un cálculo financiero trivial no necesita el modelo más capaz, y criticar un plan de trabajo sí, y no es ni legal ni financiero.
- **`/metodo:crear-agente` ahora aplica ese criterio** al preguntarte por el modelo del agente que estás creando, y te dice por qué. Antes proponía uno sin explicar de dónde salía.
- **Dos reglas nuevas para el `model:` de un agente:** siempre el **alias** (`haiku`, `sonnet`, `opus`, `fable`), **nunca** un número de versión tipo `claude-sonnet-4-6` — un número queda clavado y tu agente se queda atrás cuando sale un modelo nuevo, sin que nadie se entere. Y **Fable, el más capaz, no se le pone a ningún agente**: corre en el modelo más caro también cuando la tarea es trivial. Se pide en el momento: «usá fable para esto: …».
- **Un PM va en Sonnet**, aunque coordine cosas importantes: el razonamiento duro pasa en el especialista al que le delega.
Para actualizar: `claude plugin update metodo@claude-catalogo`.

## 0.8.0 — 2026-09-22
- Sin cambios; acompaña al catálogo 0.8.0 (`base-segura`: `humanizalo` + `modo-directo`).

## 0.7.0 — 2026-09-22
- Sin cambios; acompaña al catálogo 0.7.0 (`rubro-estudio-arquitectura`: `identidad-visual-del-estudio` reemplaza a `brand-guidelines`).

## 0.6.0 — 2026-09-21
- Sin cambios; acompaña al catálogo 0.6.0 (`base-segura`: `docs/CONECTORES.md`).

## 0.5.0 — 2026-09-21
**Ya no hace falta copiar y pegar el texto de arranque.**
- **`/cerrar` guarda el texto de arranque en `REANUDAR.md`**, en la raíz de tu carpeta de trabajo (lo ves en el Finder). Siempre es el último: cada cierre lo reemplaza. Sigue mostrándolo en el chat por si acaso.
- **`/arrancar` lo levanta solo.** Abrís Claude en la carpeta, escribís `/arrancar` y listo: lee `REANUDAR.md`, te dice de qué cierre es, verifica que estás en la carpeta y rama correctas, y arranca. Si pegás un texto igual, gana el pegado. Si no hay archivo, arranca como antes (CLAUDE.md + último handoff).
- Si trabajás con varias ventanas (`/metodo:otra-sesion`), cada copia tiene su propio `REANUDAR.md`.
- Probado: un cierre dejó el archivo (y entró al repositorio); una ventana nueva con `/arrancar` a secas lo levantó y hasta avisó que el archivo de trabajo tenía menos de lo que el handoff decía.
Para actualizar: `claude plugin update metodo@claude-catalogo`.

## 0.4.1 — 2026-09-21
- **`/metodo:cerrar` frena una vez si va a subir algo que no es texto.** Los `.md`, notas y handoffs suben sin preguntar, como en 0.4.0. Pero si entre los archivos nuevos hay un **PDF, un plano (DWG/DXF/SKP/RVT/PLN), una imagen, un Word/Excel, un comprimido o algo de más de 5 MB**, Claude los lista y pregunta una vez: «¿sí, no, o solo los de texto?». Por qué: un presupuesto de un cliente en PDF no tiene nombre de clave, pero tampoco debería subir al repositorio sin que alguien lo mire. Probado: con un `.md` y un PDF nuevos, frenó y no subió nada; con «solo los de texto», subió el `.md` y dejó el PDF afuera.
- **Nuevo `templates/gitignore-estudio`**: un `.gitignore` de fábrica que ignora claves, documentos de clientes y archivos pesados. `/metodo:cerrar` lo propone si la carpeta no tiene uno. Si querés versionar algún tipo (por ejemplo tus DXF), borrás esa línea.
Para actualizar: `claude plugin update metodo@claude-catalogo`.

## 0.4.0 — 2026-09-21
**Ahora podés tener dos sesiones a la vez sin pisarte, y cerrar es un solo gesto.**
- **Nueva `/metodo:otra-sesion`.** Cuando querés abrir otra ventana de Claude para otro tema del mismo proyecto (o dos personas trabajan a la vez), esta skill deja a cada sesión en **su propia copia de la carpeta y su propia rama**, y te entrega el texto de arranque para la ventana nueva. Por qué: dos ventanas sobre la misma carpeta se pisan los archivos aunque usen ramas distintas.
- **`/metodo:cerrar` en un solo gesto.** Antes preguntaba «¿lo guardo y lo subo?». Ahora **escribir el comando ya es el sí**: guarda, trae lo de las otras sesiones (`pull --rebase`), sube y te dice qué pasó. Frena y pregunta **solo** si aparece un archivo con pinta de clave, si hay un conflicto, o si la carpeta no es un repositorio. Lo único que sigue pidiendo «sí» es **juntar tu rama a `main`**, porque eso afecta a las demás sesiones. La regla 3 (confirmar antes de publicar) no cambia: la confirmación es el comando que escribiste.
- **`/metodo:arrancar` verifica copia y rama.** Si tu texto de arranque dice `Copia: … · Rama: …` y estás en otra carpeta, **para y te avisa** en vez de trabajar en el lugar equivocado. Si detecta más de una copia y tu texto no dice cuál es la tuya, te propone `/metodo:otra-sesion`.
- **Reglas 11-14** en `templates/REGLAS-DEL-METODO.md` (ahora son 14): una sesión-un tema-una copia · cada sesión sabe su alcance · cierre seguro entre sesiones (agregar al final, nunca reescribir; juntar a `main` de a uno) · ninguna sesión arranca sin preparación.
- Plantillas: el handoff lleva `Copia/rama` y una sección «Fuera de alcance que apareció»; el prompt de reanudación lleva `Copia · Rama` (PARTE B) y «Fuera de alcance (→ a quién)» (PARTE A).
- **Atajos `/arrancar` y `/cerrar`** (verificado): si no tenés otra skill con ese nombre, funcionan igual que `/metodo:arrancar` y `/metodo:cerrar`.
Para actualizar: `claude plugin update metodo@claude-catalogo`.

## 0.3.0 — 2026-09-21
- Sin cambios; acompaña al catálogo 0.3.0 (9 skills nuevas en `rubro-estudio-arquitectura` + `docs/CAD-BIM.md`).

## 0.2.2 — 2026-09-21
- Sin cambios; acompaña al catálogo 0.2.2.

## 0.2.1 — 2026-09-21
- Sin cambios; acompaña al catálogo 0.2.1.

## 0.2.0 — 2026-09-21
- **`/metodo:cerrar` ahora guarda tu avance en el repositorio**: al cerrar, si tu carpeta es un repo, te muestra qué cambió y te propone el comando para guardarlo y subirlo. Se ejecuta solo si decís «sí». Así quien te acompaña ve tu avance sin que tengas que saber git. Nunca sube archivos con pinta de clave o contraseña.
- **Nueva skill `/metodo:crear-agente`**: crea tu PM de empresa (`pm-<empresa>`, el que conoce tu negocio y reparte el trabajo) y especialistas, con dos plantillas nuevas en `templates/` (`pm-empresa.md`, `especialista.md`). Antes de crear busca si ya existe; nunca borra, archiva.
Para actualizar: `claude plugin update metodo@claude-catalogo`.

## 0.1.3 — 2026-09-21
- Sin cambios; acompaña al catálogo 0.1.3.

## 0.1.2 — 2026-09-21
- Sin cambios; acompaña al catálogo 0.1.2 (chequeo de carpetas huérfanas, ver `docs/CHEQUEO.md`).

## 0.1.1 — 2026-09-21
- **`requisitos.md`** (nuevo): confirma que este plugin no necesita nada extra. Sin cambios en las skills.

## 0.1.0 — 2026-09-20
Primera versión del método (capa L3). Se activa cuando duele: la primera vez que perdés una sesión sin registro, o a las dos semanas de uso.
- **`/metodo:arrancar`**: Claude lee tu `CLAUDE.md` y el último handoff antes de tocar nada, y te confirma el próximo paso.
- **`/metodo:planear`**: las 8 preguntas antes de cualquier plan (qué existe ya, qué es irreversible, qué NO se hace, cómo se verifica).
- **`/metodo:criticar`**: abogado del diablo. Prohibido arrancar con "buena idea": va directo a qué falla, cuándo, qué cuesta y la alternativa.
- **`/metodo:cerrar`**: guarda un handoff en `handoffs/` y te entrega el prompt para pegar en la próxima sesión. Solo lo invocás vos.
- **Plantillas**: `REGLAS-DEL-METODO.md` (10 reglas para tu `~/.claude/CLAUDE.md`) y `handoff.md` (formato del registro).
