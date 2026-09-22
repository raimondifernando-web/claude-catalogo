# metodo — qué cambia para vos

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
