# metodo — qué cambia para vos

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
