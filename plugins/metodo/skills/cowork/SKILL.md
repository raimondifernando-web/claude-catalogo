---
name: cowork
description: "Publica en Cowork (claude.ai) las skills propias que creaste en Claude Code, sin subirlas a mano: las copia a un repositorio privado tuyo en GitHub, las valida y las sube, y Cowork las toma de ahí. Usala cuando el usuario diga 'publicá mi skill en Cowork', 'quiero usar esta skill en Cowork', 'pasá mis skills a Cowork', 'actualizá Cowork', 'por qué no aparece mi skill en Cowork', o cuando termine de crear o cambiar una skill que también usa en Cowork."
---

# /metodo:cowork — Tus skills en Cowork, sin subirlas a mano

**El problema.** Cowork no lee las skills de tu computadora. Si las subís a mano desde la web, quedan como una copia
suelta: cambiás la skill en Claude Code y Cowork sigue con la vieja, sin avisar. Así se desactualizan en silencio.

**La solución.** Claude Code es la única fuente. Cada skill que quieras en Cowork lleva `sync: cowork` en el encabezado.
Esta skill la copia a **un repositorio privado tuyo** en GitHub y lo sube. Cowork tiene ese repositorio como
marketplace y toma la versión nueva.

Script: `${CLAUDE_PLUGIN_ROOT}/scripts/cowork/cowork-publicar.py` (Python 3). **Lo corrés vos, Claude**; el usuario
no toca la terminal.

## Primera vez (una sola vez por computadora)

1. **Verificá `gh`** con la sesión iniciada: `gh auth status`. Si no, pedile al usuario que corra `gh auth login`
   (lo hace él: es su cuenta).
2. **Nombre del repositorio.** Proponé `cowork-skills-<nombre corto del usuario o la empresa>`. Tiene que ser
   **privado** y **solo para esto**: Cowork lee el repositorio entero, así que no se mezcla con un proyecto de trabajo.
3. **Armalo.** Primero preguntá si el repositorio **ya existe** (es lo normal si su llave de GitHub es acotada:
   una llave que abre solo repos elegidos no puede crear repos nuevos; entonces el usuario lo crea vacío y privado
   desde la web y vos solo lo conectás).
   - **Ya existe (camino normal):**
     ```bash
     gh repo clone <cuenta>/cowork-skills-<nombre> ~/cowork-skills-<nombre>
     python3 "${CLAUDE_PLUGIN_ROOT}/scripts/cowork/cowork-publicar.py" preparar ~/cowork-skills-<nombre> skills-<nombre>
     ```
   - **No existe y su `gh` puede crear repos:**
     ```bash
     python3 "${CLAUDE_PLUGIN_ROOT}/scripts/cowork/cowork-publicar.py" preparar ~/cowork-skills-<nombre> skills-<nombre>
     gh repo create cowork-skills-<nombre> --private --source ~/cowork-skills-<nombre> --remote origin
     ```
     Si `gh repo create` falla por permisos, no insistas: pedile que lo cree vacío y privado desde la web y seguí por el
     camino de arriba.

   En los dos casos verificá que es privado: `gh repo view <cuenta>/cowork-skills-<nombre> --json visibility` →
   `PRIVATE`. Si no, pará. Si el repo ya tenía archivos que no son de esto, pará también: tiene que ser solo para Cowork.
4. **¿Dónde están sus skills?** El script busca en `~/.claude/skills`. Si las crea en la carpeta del proyecto
   (`<proyecto>/.claude/skills`, la que se guarda en su repo de trabajo), sumala una vez:
   `python3 .../cowork-publicar.py agregar-carpeta <proyecto>`. Si una skill con el mismo nombre está en las dos
   carpetas, no se sube ninguna hasta que quede una sola.
5. **Primera publicación:** marcá las skills (paso de abajo) y corré el script sin argumentos.
6. **El paso en Cowork lo hace el usuario** (vos no tenés acceso): Personalizar → Plugins → Añadir → Añadir
   marketplace → Añadir desde un repositorio → pegar la dirección del repositorio → activar la sincronización
   automática → instalar el plugin `skills-<nombre>`. Dale la dirección exacta (`gh repo view --json url -q .url`).
7. Si antes había subido skills a mano en Cowork, que las **desactive** (no las elimine: eliminar no tiene vuelta
   atrás) para que no queden dos copias.

## Cada vez que publica

1. **Marcar la skill:** agregá `sync: cowork` en el encabezado de su `SKILL.md` (en `~/.claude/skills/` o en la carpeta de proyecto agregada), entre los `---`.
   Solo skills propias del usuario; las de un plugin ya llegan a Cowork por su propio marketplace.
2. **Revisar antes de subir:** `python3 .../cowork-publicar.py --revisar`. Si alguna sale **OMITIDA**, explicale en
   criollo qué tiene y arreglalo con él. Una sola skill mal formada hace fallar la sincronización de **todas** en
   Cowork; por eso el script la saltea en vez de subirla.
3. **Publicar:** `python3 .../cowork-publicar.py`. Mirá la última línea:
   - `publicado (N skills)` → listo.
   - `sin cambios` → ya estaba al día.
   - `FRENADO` → hay un archivo con forma de clave. **No se sube nada.** Mostrale qué archivo es (nunca el valor) y
     sacá la clave de la skill antes de reintentar.
   - `ERROR al subir` → leé el mensaje; casi siempre es la sesión de `gh` vencida.
4. **Decile cómo verlo en Cowork:** si la sincronización automática no la trajo en unos minutos, Personalizar →
   Plugins → el marketplace → «Buscar actualizaciones».

## Reglas
- **Qué nunca sube:** archivos `.env` (salvo `.env.example`), carpetas `.git`, `node_modules`, entornos de Python,
  `.omc`. Frena si ve algo con forma de clave.
- **Datos del negocio:** antes de marcar una skill con números, clientes o contratos reales, preguntale al usuario si
  está de acuerdo con que viajen a Cowork. Si comparte Cowork con otras personas, ellas la van a ver.
- **Las skills que Cowork ya trae de fábrica no se publican** (gana la oficial; solo se detecta en Mac con Claude Desktop).
- El registro queda en `~/.claude/cowork/cowork.log`.
