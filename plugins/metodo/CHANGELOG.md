# metodo — qué cambia para vos

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
