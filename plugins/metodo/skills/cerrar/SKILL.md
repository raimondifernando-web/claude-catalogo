---
name: cerrar
description: "Cierre de sesión en un solo gesto: guarda un handoff (qué se hizo, qué se decidió, qué falta), sube el avance al repositorio sin volver a preguntar (invocarla ya es el consentimiento) y SIEMPRE termina entregando el prompt de reanudación copiable para la próxima sesión. SOLO la invoca el usuario (escribe '/metodo:cerrar' o '/cerrar', 'cerrá', 'cerrar sesión', 'terminamos', 'guardá y cerrá'); Claude nunca la ejecuta por iniciativa propia, solo la PROPONE al terminar el trabajo."
---

# /metodo:cerrar — Cerrar dejando la cadena escrita

> ⛔ **Quién la invoca: el usuario, siempre.** Claude no ejecuta esta skill por su cuenta, ni aunque "cerrar"
> figure como paso de un plan aprobado. Al terminar el trabajo, confirma lo hecho en 2-3 líneas y **ofrece**
> cerrar ("¿cerramos con /metodo:cerrar?"). La invocación es del usuario.

El problema que resuelve: una sesión que cierra sin dejar registro obliga a la siguiente a arrancar ciega,
re-hacer trabajo y volver a discutir lo decidido. Por eso el cierre tiene **un entregable que no se puede
saltear: el prompt de reanudación copiable**, que el usuario pega al abrir la próxima sesión.

## ⛔ Regla de oro
**El ÚLTIMO mensaje de la sesión SIEMPRE es el prompt de reanudación copiable** (en la app de escritorio, el paso 10 sigue en esa misma
respuesta: son llamadas, no un mensaje nuevo). Pase lo que pase
con los demás pasos, nunca termines sin emitir ese bloque.

## Secuencia
1. **Fecha + tema.** Fecha de hoy (`date +%F`) y tema en minúsculas con guiones. El archivo del handoff se
   llama `handoffs/YYYY-MM-DD-tema.md` dentro de la carpeta de trabajo (crear `handoffs/` si no existe).
2. **Relevá el trabajo real**, mirando los archivos, no la memoria: qué se creó o modificó, qué decisiones
   se tomaron, qué quedó a medias.
3. **Bajar lo durable a su lugar ANTES de escribir el prompt.** Si esta sesión aprendió una regla permanente
   ("los presupuestos siempre en USD", "a este cliente no se le manda mail los viernes"), va al `CLAUDE.md`
   de la carpeta de trabajo, no solo al prompt. Un cambio que vive solo en el prompt se pierde en dos sesiones.
   En `CLAUDE.md` y en `handoffs/` **agregá al final, no reescribas**: otra sesión puede estar cerrando a la vez y
   una reescritura le pisa lo suyo (regla 13).
4. **Handoff** (obligatorio si se modificaron 3 o más archivos o se tomaron 2 o más decisiones): escribí
   `handoffs/YYYY-MM-DD-tema.md` con la plantilla `metodo/templates/handoff.md`: estado, decisiones (con el
   porqué), próximos pasos en orden, dudas abiertas.
5. **Guardá y subí el avance (si la carpeta de trabajo es un repo git) — sin volver a preguntar.** Verificá con
   `git rev-parse --is-inside-work-tree` y `git remote -v`. Si es un repo, mirá `git status --short`, ejecutá en
   orden y reportá el resultado real (`git log --oneline -1`):
   ```
   git add <los archivos que creó o modificó ESTA sesión> && git commit -m "cierre YYYY-MM-DD-tema" \
     && git pull --rebase --autostash && git push
   ```
   - **Subí solo lo de esta sesión, nunca `git add -A` ni `git add .`** Puede haber otra sesión abierta en esta
     misma carpeta (se puede trabajar así, aunque exista `/metodo:otra-sesion`): `add -A` se lleva lo que la otra
     dejó a medias y lo sube con el nombre y la descripción de esta. Armá la lista con lo que hiciste en la sesión
     (los archivos que editaste, el handoff, `REANUDAR.md`, lo que agregaste a `CLAUDE.md`). Si `git status` muestra
     cambios que esta sesión **no** hizo, no los subas ni los descartes: listalos en la confirmación («Quedaron sin
     subir cambios que no son de esta sesión: [lista] — los sube la sesión que los hizo») y en la PARTE B, y seguí.
     No es una frenada: es el comportamiento por defecto, y lo ajeno queda intacto.
   - **Escribir `/metodo:cerrar` ya es el consentimiento** para guardar y subir: el usuario lo pidió al invocar el
     comando, así que no vuelvas a preguntar «¿lo subo?». La regla 3 del método (confirmar antes de publicar) se
     cumple con la invocación misma; volver a preguntar es fricción, no seguridad.
   - Si la sesión está en una copia con rama propia (regla 11), `push` sube **la rama**, no `main`
     (`git push -u origin <rama>` la primera vez).
   - **Parás y preguntás SOLO en cuatro casos:** (a) `git status` muestra un archivo con pinta de clave o contraseña
     (archivos de entorno `.env`, `*.pem`, `*token*`, `*secret*`, `*password*`): **no lo agregues**, avisá y sugerí
     `.gitignore`; (b) entre los archivos **nuevos** (`??` en `git status --short`) hay alguno que **no es texto**
     — PDF, planos (`.dwg`, `.dxf`, `.skp`, `.rvt`, `.pln`), imágenes, Word/Excel/PowerPoint, comprimidos, audio/video —
     o pesa más de 5 MB: los archivos de texto suben igual sin preguntar, pero **esos los listás y preguntás una vez**:
     «Estos N archivos van a subir al repositorio: [lista]. ¿Sí, no, o solo los de texto?». Con «no» o «solo texto»
     los excluís del `add` (y proponé sumarlos al `.gitignore`); el resto del cierre sigue igual. Por qué: un PDF de
     un cliente o un plano pesado no tienen nombre de clave, pero tampoco deberían subir sin que alguien los mire;
     (c) el `pull --rebase` da conflicto: mostralo tal cual y **no fuerces** (`git rebase --abort` deja todo como
     estaba; el commit queda local); (d) la carpeta no es repo: saltá este paso y anotá en el prompt «carpeta sin
     repositorio».
   - Si la carpeta no tiene `.gitignore`, proponé crear el de fábrica del kit (`metodo/templates/gitignore-estudio`):
     ignora por defecto claves, documentos de clientes y archivos pesados; el usuario puede sacar lo que sí quiera
     versionar.
   - **Graphify, sin preguntar.** Dos arreglos automáticos, que se avisan en la confirmación:
     1. Si existe `graphify-out/` y el repo no la ignora **por sí solo** — `git check-ignore -v graphify-out/graph.json`
        no lista nada, o la línea NO empieza con `.gitignore:` / `<carpeta>/.gitignore:` (si empieza con
        `.git/info/exclude` o con `/`, la regla es de esta computadora y no viaja), o el patrón empieza con `!` —, agregá al `.gitignore` los bloques «Configuración de Claude de ESTA
        computadora» y «Graphify» del `.gitignore` de fábrica, y sumá el `.gitignore` a lo que subís. Lo mismo
        si el `.gitignore` tiene la línea `.claude/settings.json` (la traía el de fábrica de la versión 0.11.3):
        **sacala** y poné `.claude/settings.local.json` en su lugar — `settings.json` tiene que poder viajar.
     2. Si `.claude/settings.json` tiene enganches de Graphify (`grep -q graphify .claude/settings.json`), mudalos
        a `.claude/settings.local.json` con este bloque exacto (no lo reescribas a mano: toca solo los enganches
        de Graphify y deja todo lo demás, como el catálogo pre-listado, donde está):
        ```
        python3 - .claude/settings.json .claude/settings.local.json <<'PY'
        import json, sys, os
        src, dst = sys.argv[1], sys.argv[2]
        s = json.load(open(src)); pre = s.get("hooks", {}).get("PreToolUse", [])
        g = [h for h in pre if "graphify" in json.dumps(h)]
        if g:
            d = json.load(open(dst)) if os.path.exists(dst) else {}
            dp = d.setdefault("hooks", {}).setdefault("PreToolUse", []); dp += [h for h in g if h not in dp]
            json.dump(d, open(dst, "w"), indent=2)
            s["hooks"]["PreToolUse"] = [h for h in pre if h not in g]
            if not s["hooks"]["PreToolUse"]: del s["hooks"]["PreToolUse"]
            if not s["hooks"]: del s["hooks"]
            json.dump(s, open(src, "w"), indent=2)
        PY
        ```
        Si después `.claude/settings.json` quedó vacío (`{}`) y no estaba guardado en el repo, no lo subas.
        Si tiene contenido (el catálogo pre-listado, permisos del proyecto), subilo: es lo que tiene que viajar.
     Por qué: `.claude/settings.json` viaja con el proyecto y lleva lo compartido; los enganches de Graphify y el
     mapa son de esta computadora. Se prueba con `core.excludesfile=/dev/null` para que valga en cualquier
     computadora, no solo en esta.
   - Si `push` falla por otra razón (sin internet, sin remoto), decilo tal cual: el commit quedó local y el prompt
     de reanudación lleva «PENDIENTE: subir cambios».
   - Nunca `--force`, nunca `reset --hard`, nunca borrar ni reescribir historial.
   - **Juntar la rama a `main` es otra cosa y SÍ se pregunta**, porque afecta a las demás sesiones: si estás en una
     rama propia, al final ofrecé «¿Junto esta rama a `main`? Se hace de a una sesión por vez» y ejecutalo solo con
     «sí». Desde una copia, `main` suele estar en uso en la carpeta principal y `git checkout main` falla; por eso
     el camino es traer `main` a tu rama y empujar el avance rápido:
     `git fetch origin && git merge origin/main && git push origin HEAD:main`
     (si `git merge origin/main` da conflicto, mostralo y no fuerces; el push a `main` solo entra si es avance
     rápido — nunca `--force`). Después ofrecé borrar la copia (`git worktree remove <ruta>`),
     también con «sí»; nunca borres copias de otra sesión.
6. **Confirmá al usuario** en 2-3 líneas qué quedó hecho y dónde (incluida la subida al repo, si se hizo).
7. **Validá el prompt antes de emitirlo:** tiene las dos partes; la PARTE A trae rol, alcance y reglas con
   contenido real (no una línea genérica); la PARTE B trae lo hecho, «De qué veníamos hablando» (de la CONVERSACIÓN, no de git), los pendientes en orden **con su
   detalle (qué, dónde, qué cuidado)** y el puntero al handoff; no tiene números de memoria; entra en 30-50 líneas. Si se pasa, no recortes borrando: es señal de
   que algo durable quedó sin bajar al `CLAUDE.md` (paso 3).
8. **Guardalo en `REANUDAR.md`, en la raíz de la carpeta de trabajo**, para que la próxima ventana arranque con
   `/arrancar` sin pegar nada. Es el mismo bloque completo (PARTE A + PARTE B) que vas a emitir, con una primera
   línea `<!-- cierre YYYY-MM-DD-tema · lo escribe /metodo:cerrar · lo lee /metodo:arrancar -->`. **Sobrescribí
   siempre**: ese archivo es "el último", no un historial (el historial son los `handoffs/`). Si estás en una copia
   de `/metodo:otra-sesion`, va en la raíz de esa copia. Hacelo **antes** del paso 5 para que entre en el mismo
   guardado; si ya guardaste, un guardado chico aparte. Nunca con claves adentro (el prompt no las tiene).
8 bis. **Comprobá el cierre:** cuando ya subiste el avance (paso 5) y guardaste `REANUDAR.md` (paso 8), corré
   `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/cerrar-check.py"` (en Windows, `py -3`; opcional: el id del cierre, o la
   carpeta). Solo lee y nunca muestra valores: una línea ✓/✗ por chequeo (REANUDAR con id y largo razonable, sin
   números de memoria ni pinta de clave, avance subido, handoff si tocaste 3 o más archivos). **Prohibido dar el cierre
   por terminado sin haberlo corrido.** Pegale al usuario su salida tal cual y, debajo, **una línea por cada ítem MANUAL
   con su resultado real**. Si dice «Falta: … ✗», resolvelo y volvé a correrlo. Después sigue el paso 9: el prompt
   de reanudación sigue siendo el último mensaje.
9. **⛔ EMITÍ EL PROMPT DE REANUDACIÓN COPIABLE.** Es el último mensaje de la sesión. **La única fuente es el
   archivo del paso 8: el chat NO se redacta de nuevo, se COPIA de él** (vista en la práctica: la sesión emitió en el chat
   unas 14 líneas mientras el archivo tenía 35; faltaban «Hecho esta sesión» y el detalle de los pendientes). Procedimiento
   obligatorio:
   a. Releé el `REANUDAR.md` recién escrito (no confíes en lo que recordás haber escrito).
   b. Pegá ese texto **carácter por carácter** dentro del bloque de código, sin la línea `<!-- cierre … -->`.
      Prohibido resumir, acortar, reordenar o «limpiar». Si algo está mal, se corrige en el ARCHIVO y se vuelve a copiar;
      nunca se edita solo la copia del chat.
   c. Si el archivo no existe o no se pudo escribir, recién ahí armás el bloque con la plantilla y avisás «no quedó guardado».
   Aunque ya esté guardado, se emite igual: si el archivo se pierde o la ventana se abre en otra carpeta, el chat es el
   respaldo, y por eso tiene que ser idéntico. Cerrá con una línea afuera del bloque: «Guardado en `REANUDAR.md`. La próxima
   vez, abrí Claude en esta carpeta y escribí `/arrancar`: no hace falta pegar nada.»
10. **Abrí la sesión siguiente sola (solo en la app de escritorio).** Condiciones: `cerrar-check` dio todo ✓, el avance
   está subido y existen las herramientas de sesiones de la app (`start_session`, `detach_session`, `archive_session`;
   búscalas con ToolSearch si vienen diferidas). Si no existen (terminal, Cowork, otra máquina) → salteá este paso y
   decilo en una línea; el usuario abre la ventana y escribe `/arrancar`.
   **NO termines el turno después del prompt** (vista en la práctica: una sesión cerró en el paso 9 y nunca abrió la
   siguiente). El `REANUDAR.md` ya está en disco y subido antes del paso 9, así que la sesión nueva no puede leer algo a
   medias. Orden: escribí el prompt del paso 9 y su línea «Guardado en…» y, en ESA MISMA respuesta, sin dejar de trabajar,
   seguí con una línea («Abrí <título>; archivo esta.») y las llamadas (`start_session`, `detach_session`,
   `move_sessions`, `archive_session`). Pasá siempre `use_worktree: false`: la sesión nueva trabaja en la MISMA carpeta (si esta está en una copia con rama propia, omitirlo la crearía en otra y `/arrancar` frenaría por copia equivocada). Nunca cierres tu respuesta sin haber hecho este paso o sin decir por qué no.
   - `start_session` con `initiation: "user_asked"` (el `/cerrar` que escribió el usuario es el pedido), `context: "fresh"`,
     `cwd` = la carpeta actual, `model` = el de la línea «Modelo para abrir» de la PARTE B (por defecto el mismo que usás),
     `title` = el título siguiente de la serie (mismo ancho: «03» → «04»), `prompt`: «Ejecutá la skill /arrancar en esta
     carpeta.» y `background`: «Sesión abierta sola por /cerrar del cierre <slug>; el estado está en REANUDAR.md, que
     /arrancar levanta.». Una sola llamada.
   - **Enseguida, `detach_session(<id nuevo>)`**: `start_session` crea la nueva como sesión HIJA, colgada de esta en la barra
     lateral, y al archivar esta se archivaría junto con ella. Si esta sesión tiene grupo en la barra lateral
     (`get_session("self")`), después `move_sessions([<id nuevo>], group_id = el de esta)`. Si el detach falla, decilo.
   - **Archivate al final:** la nueva NO puede archivar esta (mientras corre /arrancar, esta sigue «trabajando» y la app
     rechaza el archivado). Si `start_session` + detach salieron bien, la ÚLTIMA llamada del cierre es
     `archive_session("self")`. Si la app la rechaza por «still working», es normal: queda abierta y `/arrancar` de la sesión nueva ofrece archivarla (con el sí del usuario). El `/cerrar` del usuario es su OK; es reversible desde la barra lateral. Si algo falló
     antes, no te archives.
   - Si la llamada falla o la app la rechaza, decilo tal cual y dejá la línea de siempre (`/arrancar` a mano).

## Plantilla del prompt de reanudación
````
═══ PARTE A — CONTRATO ═══
ROL: [cómo tiene que trabajar Claude en este tema: rol, para quién, con qué criterio]
ALCANCE: [qué toca esta sesión y qué NO; qué carpeta de trabajo]
Fuera de alcance (→ a quién): [lo que apareció y no era de esta sesión → a qué sesión o persona va]
REGLAS: [las que aplican acá: verificar antes de afirmar · secretos nunca en el chat · confirmar antes de
borrar/enviar/publicar · no adular · leer CLAUDE.md y el último handoff antes de tocar nada]

═══ PARTE B — ESTADO ═══
Seguimos con [tema]. Último cierre: YYYY-MM-DD-tema (handoffs/YYYY-MM-DD-tema.md).
Copia: <ruta> · Rama: <tema/fecha>   (o «carpeta única, sin copia»)
Hecho esta sesión: [derivado de los archivos, no de memoria]
De qué veníamos hablando: [3-4 líneas escritas mirando la CONVERSACIÓN (no git): el tema vivo al cerrar, lo que el usuario
pidió probar o mirar, y lo que quedó sin responder. Si su última pregunta es «¿funcionó X?», X va nombrado. Sin esto la
sesión nueva no sabe a qué se refiere «lo último que hiciste».]
PENDIENTES (en este orden):
1. [próximo paso exacto, con detalle: qué, dónde, qué cuidado]
2. ...
A VERIFICAR (si aplica): [dudas técnicas que Claude resuelve solo al arrancar]
Modelo para abrir: [alias: haiku, sonnet u opus] (lo usa el paso 10)
Arrancá con /arrancar (o /metodo:arrancar) y confirmá: "Leí el estado. El próximo paso es [X]. ¿Arrancamos?"
````

## Notas
- Si el usuario dice solo "cerrá", asumí cierre completo. Si dice "cerrá rápido", saltá el handoff largo
  pero **igual emití el prompt de reanudación** (regla de oro).
- Si la conversación ya es muy larga, sugerí cerrar aunque el usuario no lo pida.
- El paso 5 (guardar y subir) existe para que quien te acompaña vea tu avance sin que tengas que saber git.
  Se ejecuta sin volver a preguntar porque **vos ya lo pediste al escribir el comando**; las únicas frenadas son
  las cuatro del paso 5 (archivo con pinta de clave · archivo nuevo que no es texto o pesa mucho · conflicto ·
  carpeta sin repo).
- Atajo: si no tenés otra skill llamada `cerrar`, `/cerrar` a secas también la activa.
- Si hay otra sesión abierta sobre el mismo proyecto, el orden de cierre no importa: cada una sube su rama y la
  junta a `main` de a una (regla 13). La segunda que junte hace `pull --rebase` y trae lo de la primera.
- Si las dos sesiones están en la **misma carpeta** (sin copia), también funciona: cada una sube solo sus
  archivos (paso 5). Lo único que no se puede separar es un mismo archivo editado por las dos: lo sube la primera
  que cierra, y la segunda lo avisa en su confirmación.
