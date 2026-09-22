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
**El ÚLTIMO mensaje de la sesión SIEMPRE es el prompt de reanudación copiable.** Pase lo que pase con los
demás pasos, nunca termines sin emitir ese bloque.

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
   contenido real (no una línea genérica); la PARTE B trae lo hecho, los pendientes en orden y el puntero al
   handoff; no tiene números de memoria; entra en 30-50 líneas. Si se pasa, no recortes borrando: es señal de
   que algo durable quedó sin bajar al `CLAUDE.md` (paso 3).
8. **Guardalo en `REANUDAR.md`, en la raíz de la carpeta de trabajo**, para que la próxima ventana arranque con
   `/arrancar` sin pegar nada. Es el mismo bloque completo (PARTE A + PARTE B) que vas a emitir, con una primera
   línea `<!-- cierre YYYY-MM-DD-tema · lo escribe /metodo:cerrar · lo lee /metodo:arrancar -->`. **Sobrescribí
   siempre**: ese archivo es "el último", no un historial (el historial son los `handoffs/`). Si estás en una copia
   de `/metodo:otra-sesion`, va en la raíz de esa copia. Hacelo **antes** del paso 5 para que entre en el mismo
   guardado; si ya guardaste, un guardado chico aparte. Nunca con claves adentro (el prompt no las tiene).
9. **⛔ EMITÍ EL PROMPT DE REANUDACIÓN COPIABLE** con la plantilla de abajo. Es el último mensaje. Aunque ya
   quedó guardado, se emite igual: si el archivo se pierde o la ventana se abre en otra carpeta, el chat es el
   respaldo. Cerrá con una línea afuera del bloque: «Guardado en `REANUDAR.md`. La próxima vez, abrí Claude en
   esta carpeta y escribí `/arrancar`: no hace falta pegar nada.»

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
PENDIENTES (en este orden):
1. [próximo paso exacto]
2. ...
A VERIFICAR (si aplica): [dudas técnicas que Claude resuelve solo al arrancar]
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
