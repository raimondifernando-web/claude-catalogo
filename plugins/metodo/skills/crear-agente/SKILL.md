---
name: crear-agente
description: "Crea, modifica o archiva agentes en ~/.claude/agents/ (o en .claude/agents/ de la carpeta de trabajo). Usala cuando el usuario diga 'quiero un agente para X', 'creá un PM para mi empresa', 'un especialista en X', 'modificá el agente Y', o cuando una tarea se repite y siempre necesita el mismo rol y contexto. Usala TAMBIÉN cuando la pregunta sea qué modelo lleva un agente: 'qué modelo le pongo', '¿opus o sonnet?', 'está bien el modelo de este agente', 'qué modelo usan mis agentes', 'esto necesita opus', 'conviene fable acá' — el criterio está en templates/RUTEO-DE-MODELOS.md y no se contesta de memoria. Trae la plantilla de PM de empresa (pm-<empresa>) y la de especialista. Antes de crear, busca si ya existe."
---

# /metodo:crear-agente — Un agente por rol, no por capricho

Un **agente** es un Claude con un rol fijo: sabe de un tema, trabaja con un criterio y se le puede delegar.
Un **PM de empresa** (`pm-<empresa>`) es el agente que conoce TU negocio y reparte el trabajo a los
especialistas. Los **especialistas** (`cotizador`, `redactor-propuestas`, `investigador-mercado`, …) saben de
una disciplina y sirven para cualquier empresa.

## Antes de crear: 4 preguntas (en este orden)
1. **¿Ya existe?** `ls ~/.claude/agents/ .claude/agents/ 2>/dev/null` y los agentes que traen los plugins
   instalados (`/agents`). Si existe uno parecido, se ajusta ese; no se duplica.
2. **¿Hace falta un agente, o alcanza con una skill?** Si es un procedimiento ("cómo cotizar"), es una
   **skill** (`skill-creator`). Si es un **rol** que necesita contexto propio, criterio y delegar, es un agente.
3. **¿Es PM o especialista?** Si el nombre empieza con `pm-`, conoce UNA empresa/proyecto y coordina. Si no,
   domina UNA disciplina y sirve para cualquiera. Sin mezclas: un PM no ejecuta lo que un especialista hace mejor.
4. **¿Qué modelo?** Se elige por **el trabajo que pide la tarea, no por el tema**. Contá los sí:
   - ¿Hay que **juzgar o decidir**, o solo ejecutar algo ya decidido?
   - ¿**Equivocarse sale caro**, o el error pasa inadvertido?
   - ¿Hay que **sostener mucho contexto** o muchos pasos encadenados?

   **0 sí → `haiku` · 1 sí → `sonnet` · 2 sí → `opus` · 3 sí y tarea larga y autónoma → `fable`, pero a pedido,
   nunca en el frontmatter.** Ante la duda entre dos escalones, el de abajo: subir después es cambiar una
   palabra. **Un PM va en `sonnet`**, aunque coordine cosas importantes: el razonamiento duro pasa en el
   especialista al que le delega, y un PM en `opus` paga caro cada ida y vuelta.

   Dos reglas que no se negocian: **siempre alias** (`haiku`/`sonnet`/`opus`/`fable`/`inherit`), **nunca un ID
   de versión** como `claude-sonnet-4-6` (queda clavado y no sigue a los modelos nuevos); y **`fable` no se
   clava en ningún agente** — corre en el modelo más caro también para la versión trivial de su tarea, así que
   se pide en el momento («usá fable para esto: …»).

   El detalle, con lo que cuesta cada uno y cómo queda repartido: `templates/RUTEO-DE-MODELOS.md`.

## Dónde se guarda
- Agente **personal** (sirve en todas tus carpetas): `~/.claude/agents/<nombre>.md`
- Agente **de esta empresa/carpeta**: `.claude/agents/<nombre>.md` dentro de la carpeta de trabajo (así viaja
  con el repositorio y lo ve quien te acompaña).
Nombre en minúsculas con guiones. Un archivo por agente.

## Formato (lo mínimo que funciona)
```yaml
---
name: pm-miempresa
description: "Cuándo usar este agente, en una frase que empiece por el caso de uso (máx. 250 caracteres)"
model: sonnet
skills:            # opcional: skills que ya tiene que conocer al arrancar
  - pricing-strategy
---
# (acá va el rol, en criollo: qué sabe, cómo trabaja, a quién delega)
```
Campos opcionales útiles: `tools:` (lista blanca de herramientas; si un agente solo lee, sacale `Write` y
`Edit`), `disallowedTools:` (lista negra; no combinar con `tools:`), `effort:` (`low|medium|high`).

## Proceso
1. **Capturar la intención** (preguntá solo lo que falta): ¿qué empresa o disciplina? ¿PM o especialista?
   ¿qué hace bien y qué NO hace? ¿qué skills tiene que conocer? ¿a quién delega?
2. **Escribir el archivo** con la plantilla que corresponda:
   - PM de empresa → `templates/pm-empresa.md`
   - Especialista → `templates/especialista.md`
   Sin datos sensibles en el cuerpo: nada de claves, contraseñas, ni datos de clientes. El contexto del negocio
   va en el `CLAUDE.md` de la carpeta; el agente lo lee de ahí.
3. **Verificar**: `ls` del archivo; en una sesión nueva, `/agents` lo lista; probalo con una tarea real chica.
4. **Registrar**: una línea en el `CLAUDE.md` de la carpeta ("Agentes: `pm-miempresa` → coordina; …") para que
   la próxima sesión sepa que existe. Sin esto, el agente queda huérfano.

## Modificar
Leé el archivo actual entero antes de tocarlo. Cambiá solo lo que cambia. Si le sacás una skill o una
herramienta, decí por qué en el mensaje.

## Archivar (nunca borrar)
`mkdir -p ~/.claude/agents-archive && mv ~/.claude/agents/<nombre>.md ~/.claude/agents-archive/`
Y sacá la línea del `CLAUDE.md`. Un agente archivado se puede volver a traer; uno borrado, no.

## Errores típicos
- Crear un agente para cada tarea → termina con 30 agentes que nadie usa. Regla: si en 2 semanas no lo
  invocaste 3 veces, archivalo.
- PM que hace de todo → se convierte en un chat genérico. El PM **deriva**; si no tiene a quién derivar, primero
  se crea el especialista.
- Pegar el contexto del negocio dentro del agente → se desactualiza y se duplica. Va en `CLAUDE.md`; el agente
  dice "leé CLAUDE.md antes de actuar".
