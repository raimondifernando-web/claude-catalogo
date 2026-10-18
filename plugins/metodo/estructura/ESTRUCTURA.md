# Estructura Claude — la fuente de la verdad

Este archivo dice cómo se ordenan las carpetas y archivos de Claude cuando una persona trabaja con varias empresas, áreas y
proyectos, y con gente que tiene distinto acceso. **Es el único que se edita.** El dibujo (`estructura.html`) y el control
que revisa las carpetas (`scripts/estructura.py`) se arman leyendo este archivo: si cambia acá, cambian los dos.

Cada regla sale de la documentación oficial de Claude Code (sección **Fuentes**). Cuando una de esas páginas cambia, el radar
avisa y se revisa este archivo.

## La idea en cuatro líneas
1. **Cada caja es un repositorio en GitHub.** Empresa, área y proyecto: cada uno el suyo. El acceso se da en GitHub,
   repositorio por repositorio; cada persona descarga solo las cajas a las que tiene acceso.
2. **Todas las cajas tienen el mismo molde**, porque en cualquiera se puede abrir Claude a trabajar.
3. **Solo dos cosas bajan a las cajas de adentro:** las reglas (`CLAUDE.md`) y el paquete de la empresa, que cada caja
   activa en su `settings.json`. Los permisos, las skills y los agentes no bajan solos.
4. **`~/Proyectos/` agrupa todo y no es un repositorio.** `~/.claude/` es de cada persona y no va a GitHub de la empresa.

## Niveles
| Nivel | Qué es | Tiene cajas adentro |
|---|---|---|
| empresa | una empresa; su repositorio vive en la organización de GitHub de esa empresa | sí |
| area | un área de la empresa | sí |
| proyecto | un trabajo concreto; también lo personal | no |

## El molde
Columnas: **Niveles** (E empresa, A área, P proyecto) · **Comparte** (sí = va a GitHub; no = solo en la compu de cada
persona) · **Obligatorio** (sí · no · condición) · **Baja** (llega a las cajas de adentro) · **Fuente** (página oficial).

| Archivo | Qué es | Niveles | Comparte | Obligatorio | Baja | Fuente |
|---|---|---|---|---|---|---|
| `.git/` | la conexión con GitHub (carpeta oculta): sabe de qué repositorio vino y adónde subir; se crea al descargar | E A P | — | sí, con remoto | no | git |
| `CLAUDE.md` | reglas de esa caja | E A P | sí | sí | sí | memory |
| `.claude/settings.json` | permisos de esa caja y qué paquetes activa; **tiene que estar subido a GitHub**: si queda solo en el disco, no llega a otra persona, a la nube ni a una Mac nueva | E A P | sí | sí | no | settings |
| `.claude/skills/` | habilidades para trabajar en esa caja | E A P | sí | no | no | skills |
| `.claude/agents/` | asistentes para trabajar en esa caja | E A P | sí | no | no | sub-agents |
| `.claude/rules/` | reglas por tema, que se leen cuando hacen falta | E A P | sí | no | no | memory |
| `.mcp.json` | conectores para trabajar en esa caja | E A P | sí | no | no | mcp |
| `docs/` | documentos | E A P | sí | no | no | — |
| `docs/PRD.md` | el documento vivo de la caja: quién la lleva, en qué estado está (activa, dormida o archivada), dónde está su respaldo, qué es, para quién, cuándo está terminada y qué NO se hace | E A P | sí | sí | no | — |
| `docs/decisiones.md` | el registro de decisiones: cada una con fecha y el porqué, para no volver a discutirla | E A P | sí | sí | no | — |
| `docs/planes/` | un plan por etapa de trabajo, nombrado `AAAA-MM-DD-tema.md`; cuando la etapa termina, el plan se archiva | E A P | sí | sí | no | — |
| `docs/arquitectura.md` | cómo está armado por dentro (es el TRD): piezas, dependencias, dónde corre | E A P | sí | si hay código | no | — |
| `docs/flujo-de-la-app.md` | cómo se mueve la persona por la app, paso a paso, en un diagrama | E A P | sí | si hay código | no | — |
| `docs/diseno/` | el diseño de pantallas: mockups (HTML) y enlaces a Figma; nunca texto | E A P | sí | no (si hay pantallas) | no | — |
| `docs/esquema/` | el esquema de datos y el contrato de la API, generados desde el código, con el comando que los genera y la fecha | E A P | sí | no (si hay base de datos o API) | no | — |
| `docs/operacion.md` | dónde corre, cómo se despliega y se vuelve atrás, qué claves usa (solo los nombres), dónde están los datos y su respaldo | E A P | sí | si se despliega | no | — |
| `docs/specs/` | una especificación por funcionalidad, `AAAA-MM-DD-tema.md` (qué debe hacer; los pasos van en `planes/`) | E A P | sí | no | no | — |
| `README.md` | para personas: qué es y cómo se levanta y se prueba | E A P | sí | si hay código | no | — |
| `tests/` | las pruebas; el README o el `CLAUDE.md` dice cómo correrlas | E A P | sí | si hay código | no | — |
| `.claude/security-checks/` | registro de las revisiones de seguridad, `AAAA-MM-DD.md`, sin valores de claves | E A P | sí | si se despliega o usa claves | no | — |
| `.claude/rules/donde-va-cada-cosa.md` | el mapa de la caja: dónde se guarda cada pieza y con qué nombre | E A P | sí | no (recomendado si hay código) | no | memory |
| `.claude/PENDIENTES.md` | la lista de pendientes de la caja; la crea y mantiene `/pendientes`, no se escribe a mano | E A P | sí | no | no | — |
| `.claude/prompts/REANUDAR.md` | el texto de reanudación de la sesión; lo deja `/cerrar`, no se escribe a mano | E A P | sí | no | no | — |
| `.env.example` | qué claves hacen falta, sin los valores | E A P | sí | si hay .env o si hay código | no | — |
| `.gitignore` | lo que no se sube a GitHub; en empresa y área, además, las carpetas de adentro | E A P | sí | sí | no | git |
| `plugins/<paquete>/` | el paquete: skills, agentes, avisos automáticos y conectores comunes (en el área, opcional) | E A | sí | no | sí | plugins-reference |
| `.claude-plugin/marketplace.json` | la vidriera: avisa que en esta caja hay un paquete para instalar | E A | sí | si hay paquete | no | plugin-marketplaces |
| `CLAUDE.local.md` | mis notas | E A P | no | no | sí | memory |
| `.claude/settings.local.json` | mis ajustes | E A P | no | no | no | settings |
| `.env` | las claves | E A P | no | no | no | — |

### Los documentos de cada caja
Los seis documentos de desarrollo que se pidieron (PRD, TRD, flujo de la app, UI/UX, esquema de datos, plan) tienen **cada uno su lugar, con nombre fijo**. Así, quien abre Claude en cualquier caja sabe **dónde guarda cada cosa y con qué nombre**, sin decidir si algo «es desarrollo». Tres son para toda caja; el resto, para la que tiene código:
- `docs/PRD.md` (toda caja): quién la lleva, estado, respaldo, qué es, para quién, cuándo está terminada y qué NO se hace.
- `docs/decisiones.md` (toda caja): el registro de decisiones, cada una con fecha y el porqué.
- `docs/planes/` (toda caja): un plan por etapa, nombrado `AAAA-MM-DD-tema.md`; al terminar la etapa, el plan se archiva.
- `docs/arquitectura.md` (caja con código): el TRD, cómo está armado por dentro.
- `docs/flujo-de-la-app.md` (caja con código): el flujo de la app, en un diagrama (Mermaid, que GitHub dibuja solo) o en pasos.
- `docs/diseno/` (si hay pantallas): el diseño de pantallas son **mockups** (HTML o Figma), nunca texto.
- `docs/esquema/` (si hay base de datos o API): el esquema de datos **se genera desde el código, nunca a mano**; un `LEEME.md` dice con qué comando y cuándo se generó.

Que un documento tenga lugar no obliga a llenarlo de golpe: **los documentos de toda caja se crean cuando la caja tiene algo que registrar** (el aviso de apertura calla en una caja sin código ni historia propia), y los de desarrollo, cuando hay código. Nada se crea vacío solo: el bucle de orden crea los tres de toda caja (donde hay producto), y las piezas de desarrollo las pide la persona con `estructura.py arreglar --si`.

**«Tiene código»** decide qué piezas de desarrollo se piden. Se decide con señales baratas, sin leer el código: la caja tiene `package.json`, `pyproject.toml`, `requirements.txt` o `Package.swift` en su raíz, o una carpeta `src/` o `app/` con código, o al menos cinco archivos de código (`.py`, `.js`, `.ts`, `.tsx`, `.jsx`, `.swift`, `.go`, `.rs`, `.java`, `.php`, `.rb`) a dos niveles, sin contar `scripts/`, `docs/` ni `tests/`. Con una sola señal alcanza.

**Piezas por caso** (opcionales, con nombre fijo para que no se inventen otros): `CHANGELOG.md` si otras personas instalan o usan lo que sale de la caja · `SECURITY.md` y `LICENSE` si el repositorio es público · `.github/workflows/` (pruebas y robots) si hay código y despliegue · `CODEOWNERS` solo cuando más de una persona escribe en la caja · alertas de dependencias (se prenden en GitHub; no son un archivo).

Fuera de las cajas:

| Carpeta | Qué es | Comparte |
|---|---|---|
| `~/Proyectos/` | agrupa todas las cajas; no es un repositorio | no |
| `~/.claude/` | de cada persona: su `CLAUDE.md`, `settings.json`, `skills/`, `agents/` y la memoria de cada proyecto | no |
| `~/.claude.json` | los conectores personales (correo, calendario, Drive) | no |

## Reglas que revisa el control
| Id | Regla | Dónde | Si falla | Cómo se arregla |
|---|---|---|---|---|
| R1 | Tiene `.git/` con un remoto (copia en GitHub) | toda caja | ✗ | crear el repositorio y su copia en GitHub: lo hace Claude con tu OK |
| R2 | Tiene `CLAUDE.md` | toda caja | ✗ | `estructura.py arreglar` lo crea sin pisar nada |
| R3 | `CLAUDE.md` con menos de 200 líneas | toda caja | aviso | mirar si hay algo repetido, viejo o contradictorio para sacar; solo un bloque que aplica a un tema o carpeta puntual va a `.claude/rules/` con `paths:`. Con pocas líneas de más no se hace nada (el aviso lo dice) |
| R4 | Tiene `.claude/settings.json` y es un JSON válido | toda caja | ✗ | `estructura.py arreglar` lo crea sin pisar nada |
| R5 | Tiene `.gitignore` | toda caja | ✗ | `estructura.py arreglar` lo crea sin pisar nada |
| R6 | `.env`, `.claude/settings.local.json` y `CLAUDE.local.md` no están en GitHub | toda caja | ✗ | sacarlo de GitHub sin borrarlo (`git rm --cached <archivo>`); si tenía claves, cambiarlas |
| R7 | Si hay `.env`, hay `.env.example` | toda caja | aviso | `estructura.py arreglar` crea el `.env.example` con los nombres, sin los valores |
| R8 | El repositorio no guarda las cajas de adentro (las ignora por patrón) | empresa y área | ✗ | llevar cada caja de adentro a su propio repositorio: es un cambio grande, se planifica con Claude antes de tocar nada |
| R9 | Cada skill (`.claude/skills/<nombre>/SKILL.md`) y cada agente (`.claude/agents/*.md`) tiene encabezado con `name` y `description` | toda caja | ✗ | agregar `name:` y `description:` al encabezado del archivo |
| R10 | Si la empresa o el área de arriba tiene paquete, `settings.json` lo activa | toda caja de adentro | aviso | activar el paquete en `.claude/settings.json` |
| R11 | `~/Proyectos/` no es un repositorio | raíz | ✗ | sacar el `.git` de la carpeta de proyectos, con respaldo: lo hace Claude con tu OK |
| R12 | Tiene los tres documentos vivos: `docs/PRD.md`, `docs/decisiones.md` y la carpeta `docs/planes/` (ver «Tres documentos vivos en toda caja») | toda caja | aviso | solo importa si la caja tiene código (sin código no se avisa ni se crean vacíos); `estructura.py arreglar` los crea con instrucciones adentro y el contenido lo completa el PM o la sesión con Claude, nunca se inventa |
| R13 | Las rutas que cita el `CLAUDE.md` entre comillas (`docs/…`, `scripts/…`, `~/…`) existen | toda caja | aviso | corregir la ruta o sacar la mención; si la ruta es de otra caja, escribirla completa. Lo decide quien lleva la caja |
| R14 | El `CLAUDE.md` no tiene conteos escritos a mano («12 agentes», «40 skills»): se desactualizan | toda caja | aviso | reemplazar el número por el comando que lo cuenta (por ejemplo, contarlo con `ls`) |
| R15 | Los agentes `pm-…` que nombra el `CLAUDE.md` existen | toda caja | aviso | corregir el nombre o crear el agente |
| R16 | `docs/PRD.md` y `docs/decisiones.md` están completados: se compara con las líneas de la plantilla (la actual y la anterior), no solo con títulos y citas | toda caja | aviso | completarlos con la sesión de la caja: nunca se inventa el contenido |
| R17 | `.claude/PENDIENTES.md`, si existe, tiene el formato que lee el panel (8 columnas, estados válidos, sin IDs repetidos) | toda caja | aviso | corregir las filas que indica el aviso (las mide `pendientes-check.py`) |
| R18 | `.claude/prompts/REANUDAR.md`, si existe, es coherente: la rama y la carpeta que dice son las de la caja, las rutas que cita existen, no pasa de 120 líneas y su cierre no tiene más de 30 días | toda caja | aviso | volver a cerrar la sesión con `/cerrar` (reescribe el texto de reanudación) |
| R19 | El PM de la caja: el `pm-…` que nombra el `CLAUDE.md` existe y su cuerpo no es una cáscara (menos de 15 líneas con contenido); y si la caja no nombra ningún PM y hay uno instalado que cita su carpeta, se lo señala | toda caja | aviso | nombrar al PM en el `CLAUDE.md`, o completar el cuerpo del agente con `agent-creator` |
| R20 | Las skills que el PM precarga (`skills:` de su encabezado) existen | toda caja | aviso | quitar la que no existe del encabezado del PM o instalarla (`skills: []` es válido: es una decisión) |
| R21 | Los conectores: si el `CLAUDE.md` dice usar un MCP o conector, está configurado y habilitado (configurar ≠ habilitar), y las herramientas `mcp__…` del PM existen. Solo mira nombres, nunca llaves; los conectores de la nube no se juzgan | toda caja | aviso | configurar y habilitar el conector, o aclarar en el `CLAUDE.md` que se usa por script o API |
| R22 | `.claude/settings.json`, si tiene contenido (permisos, paquetes, hooks; un `{}` vacío no tiene nada que compartir), está subido a GitHub: existir en el disco no alcanza, y lo común es que lo oculte una lista global de ignorados de la Mac | toda caja | aviso | agregar `!.claude/settings.json` al `.gitignore` de la caja (le gana al ignore global, sin tocar la configuración de la Mac), mirar que no tenga claves (en `env`) y subirlo |
| R23 | Si la caja tiene código: tiene `README.md`, `docs/arquitectura.md`, `docs/flujo-de-la-app.md` y `.env.example` | caja con código | aviso | `estructura.py arreglar --si` deja los esqueletos con instrucciones; el contenido lo escribe la sesión de la caja a partir del código, nunca se inventa |
| R24 | Si tiene código: hay pruebas y el README o el `CLAUDE.md` dice cómo correrlas | caja con código | aviso | escribir el comando |
| R25 | Si la caja se despliega (`Dockerfile`, `vercel.json`, `fly.toml`, un workflow de despliegue, un `.plist`…): existe `docs/operacion.md` con sus cuatro partes (dónde corre · cómo se despliega · claves · datos y respaldo) | caja que se despliega | aviso | completarlo con la sesión de la caja |
| R26 | Si se despliega o usa claves: hay una revisión de seguridad registrada en `.claude/security-checks/` de menos de 90 días | caja que se despliega o usa claves | aviso | correr el chequeo de seguridad y guardar el informe, sin valores de claves |
| R27 | El PRD ya completado dice Dueño, Estado, Respaldo y Última revisión | toda caja | aviso | agregar las cuatro líneas |
| R28 | Si existe `docs/esquema/`: su `LEEME.md` dice «Comando:» y «Fecha:», y el código no cambió más de 30 días después de esa fecha | caja con esquema | aviso | volver a generarlo con ese comando |

**Excepciones:** lo que se decidió dejar así, con su motivo, no queda como ✗ para siempre: se anota en
`.estructura-excepciones.json` en la raíz del repositorio, una lista de
`{"regla": "R8", "ruta": "mi-caja", "motivo": "por qué se deja", "fecha": "AAAA-MM-DD"}` (`ruta` es la carpeta de la que
habla el aviso, relativa a esa raíz; `.` es la raíz misma; `vence` es opcional: pasada esa fecha, la excepción deja de valer sola). El control la muestra como `• excepción …` y no la cuenta como
falla. Sin motivo o sin fecha no vale (se ignora y se avisa). R6 y R11 no se pueden exceptuar.

**«Terminado» se mide en GitHub, no en la carpeta de la Mac:** `estructura.py remoto` hace `git fetch` de cada caja y cuenta qué hay en la rama principal del repositorio; `revisar` mira la carpeta del disco, que puede ir atrasada.

El control (`revisar`) **solo avisa**; lo que se arregla solo es el *bucle de orden* de abajo, y únicamente donde la persona lo encendió. Para completar lo que falta: `estructura.py completar <carpeta>`, que
agrega lo que no está y nunca pisa un archivo existente.

**El aviso de apertura aconseja, no ordena** (desde 0.50.0). Cada aviso dice tres cosas: qué encontró, cuánto cuesta dejarlo así (tokens por sesión, riesgo, lo que se rompe) y el arreglo que conviene en ESE caso. Si arreglarlo cuesta más de lo que se gana (por ejemplo, 4 líneas de más en el `CLAUDE.md`, o documentos vivos en una carpeta sin código), lo dice y **no manda hacer nada**: el aviso calla. Lo que vale se ordena por lo que más rinde y se muestran como mucho 3; los detalles chicos se juntan en una línea. Un mismo aviso no vuelve antes de 7 días ni más de 3 veces, y lo que se decidió no hacer se anota con `estructura.py descartar <clave>` (vuelve solo si empeora o a los 6 meses). **Nunca se arregla en la sesión principal:** el aviso le pide a Claude una sesión secundaria (tarjeta `start_session` «own_initiative») con el brief de `estructura.py brief`, para que la persona la arranque con un clic. `estructura.py revisar` sin `--aviso` sigue mostrando todo, sin filtrar.

### El bucle de orden: se arregla solo, en tres grupos
Encendido por defecto (desde 0.49.1): corre solo, sin que nadie lo active. Se apaga por escrito con `estructura.py orden-config --apagar` (queda `aplicar:false` en `metodo-orden.json`, en la carpeta de Claude) y se vuelve a encender con `--encender`; sin argumentos muestra el estado. Si ese archivo está roto o ilegible, queda APAGADO (ante la duda no escribe). Apagado, `estructura.py auto` solo muestra qué haría. Cada hallazgo cae en un grupo:
1. **Seguro y reversible** — se aplica solo, un commit por arreglo, con una prueba que lo verifica, registro (`orden/registro.jsonl` en la carpeta de estado) y comando para deshacer (`estructura.py deshacer <id>`). Nunca hace push. Hoy: una ruta de `CLAUDE.md` que git muestra renombrada se reescribe con la ruta nueva · un documento vivo que falta se crea con su plantilla (si ya está en GitHub, no se crea: lo que falta es traerlo) · una caja atrasada que solo necesita avanzar (sin cambios propios) avanza. No toca un archivo con cambios sin guardar (puede estar editándolo otra sesión) ni un repositorio a mitad de una operación. **Solo escribe en una lista de permitidos** (desde 0.49.4): el `CLAUDE.md` de la caja y documentos `.md` dentro de `docs/`; cualquier otra ruta no se toca. Nunca ejecuta hooks de git (corre con `core.hooksPath` apuntando a una carpeta vacía).
2. **De juicio** — lo decide Claude con la evidencia del disco y la confirma una segunda IA; solo se aplica con `estructura.py aplicar <id> --verificado-por <IA>`. `<IA>` es de una lista cerrada (gemini, codex, gpt, claude, opus, sonnet, haiku, pal, persona; admite variantes como `claude-opus` o `gemini-3.8-flash`) y queda en el registro como `verificacion: declarada`: es una **declaración** de quien corre el comando, no un control (el programa no puede comprobar que otra IA lo vio). Por eso la pasada automática nunca aplica este grupo. Hoy: una ruta que no existe, sin renombrado en git, pero con un único archivo del mismo nombre en la caja.
3. **De la persona** — nunca se aplica solo. Llega como UNA pregunta de sí/no: qué se encontró, qué se propone y por qué, con la recomendación. Siempre acá: todo lo sensible (hooks, `settings`, `.mcp.json`, `.github/`, instaladores, lo que corre solo), borrar o mover carpetas, una caja sin repositorio, claves versionadas, las decisiones de negocio. Una caja atrasada cuyo avance traería algo que puede correr solo (carpeta o archivo con punto salvo `.gitignore`, un ejecutable, un enlace, un submódulo, scripts `.sh`/`.ps1`/`.bat`/`.plist` y similares) también cae acá.
La primera vez de cada semana, el aviso de arranque corre el bucle (si está encendido) y muestra un resumen de 3 líneas: «arreglé N cosas, nada pendiente». **Tope total:** 20 s para revisar (vale también dentro de cada caja: ninguna llamada a git pasa de ese límite) y no empieza un arreglo pasados 30 s (un arreglo ya empezado termina: cortar un guardado a la mitad dejaría la carpeta trabada); lo que no llega a revisar queda para la próxima. Las lecturas de git van con `--no-optional-locks`, así un corte por tiempo no deja la carpeta trabada.

**Cuándo corre (nadie tiene que acordarse):** al abrir sesión revisa la carpeta actual · al cerrar sesión también · una vez
por semana, la primera sesión recorre todas las carpetas de `~/Proyectos/`.

## Las garantías: que toda caja tenga SIEMPRE lo que le corresponde
Un aviso informa y depende de que alguien lo lea. Estas tres garantías no dependen de eso (diseño y crítica: `docs/2026-10-18-molde-raiz.md` del repositorio de Tech):
1. **Al nacer.** `estructura.py nueva <carpeta> [--nivel empresa|area|proyecto] [--codigo] [--dueno "…"]` crea la caja con el molde completo: carpeta, git, `CLAUDE.md` con «dónde se guarda cada cosa», `.gitignore`, los tres documentos con la cabecera del PRD, si hay código README, arquitectura, flujo y claves de ejemplo, y el primer commit. Comprueba que pasa `exigir` y deja **un comando** para crear el repositorio en GitHub. Es la única herramienta de caja nueva.
2. **Al guardar.** `estructura.py exigir` mide el commit que se va a unir. Lo corren, antes de unir, `unir-a-main` y `unir-pr` (con el programa del plugin instalado, nunca el de la rama que se juzga) y `scripts/controles.sh` en el catálogo. **Frena solo por existencia** y dice qué falta y el comando que lo arregla (casi siempre `estructura.py arreglar --si`):
   - **Duro, siempre:** `CLAUDE.md` (R2), `.gitignore` (R5), ningún archivo personal versionado: `.env`, `.claude/settings.local.json`, `CLAUDE.local.md` (R6, no se exceptúa).
   - **De estructura, con plazo para lo que ya existía:** los tres documentos (R12) y, si hay código, `README.md`, `docs/arquitectura.md`, `docs/flujo-de-la-app.md` y `.env.example` (R23). Una caja cuyo primer commit tiene más de 7 días tiene **30 días** desde la primera vez que el control la ve (anotado en la carpeta de estado de la computadora, no en el repositorio); una caja nacida con `nueva` no tiene plazo.
   - **De contenido, nunca frena una unión:** PRD y decisiones escritos (R16; las líneas «Por confirmar» y la cabecera no cuentan) y la cabecera del PRD (R27). Cuentan para «completa» y los deja escritos el cierre.
   - Si el control falla por dentro, avisa y **no frena**. Cambiar `.estructura-excepciones.json` dentro de una rama es zona sensible (pide el OK de la persona), porque si no la propia rama podría saltearse la regla.
3. **Al cerrar.** El paso 3 bis de `/cerrar` deja `docs/decisiones.md` y `docs/planes/` al día con lo hecho en la sesión y **escribe** el PRD si seguía siendo plantilla (hechos comprobables; lo que no se sabe va como «Por confirmar»). `cerrar-check` lo comprueba (`estructura.py exigir --contenido`): en una caja con producto propio, un PRD o unas decisiones en plantilla hacen que el cierre no esté completo.

**El número único.** `estructura.py remoto --numero` cuenta cuántas cajas están **completas en GitHub** (duro + estructura + contenido, medido en `origin/main` tras un `git fetch` sin hooks): «7 de 32 cajas completas». Se guarda y lo muestran el resumen semanal del arranque (que lo refresca en segundo plano la primera apertura de cada semana) y `cerrar-check`.

## Ejemplo del dibujo
Personas: **Vos** (dueño, todo) · **Lucía** (socia, toda la Empresa A) · **Beto** (solo el área Ventas) · **Caro** (solo el
proyecto web). Quien trabaja en un área o un proyecto tiene acceso de lectura a las cajas de arriba, para que Claude lea sus
`CLAUDE.md`.

Las marcas al final de cada línea indican cómo se muestra la caja en el dibujo: `[completa]` muestra todos los archivos del molde, `[nota: …]` muestra esa aclaración, y `[resumen]` muestra solo el título.

```
Empresa-A        empresa   empresa-a/empresa-a     vos lu be:lee ca:lee    [completa]
  Ventas         area      empresa-a/ventas        vos lu be               [completa]
    crm          proyecto  empresa-a/crm           vos lu be               [completa]
    presupuestos proyecto  empresa-a/presupuestos  vos lu be               [nota: Igual que crm por dentro.]
  Marketing      area      empresa-a/marketing     vos lu ca:lee           [nota: Por dentro, igual que Ventas.]
    web          proyecto  empresa-a/web           vos lu ca               [resumen]
    campañas     proyecto  empresa-a/campanas      vos lu                  [resumen]
Empresa-B        empresa   empresa-b/empresa-b     vos                     [nota: Otra empresa tuya. Mismo esquema: áreas y proyectos adentro.]
Personal         proyecto  vos/personal            vos                     [nota: Lo tuyo. Nadie más entra. Por dentro, igual que un proyecto.]
```

## Personas del ejemplo
| Clave | Nombre | Rol |
|---|---|---|
| vos | Vos | Dueño. Entra a todo. |
| lu | Lucía | Socia. Toda la Empresa A. |
| be | Beto | Solo el área Ventas. |
| ca | Caro | Solo el proyecto web. |

## Contenido de ~/.claude/
Archivos de cada persona en su computadora:

| Archivo | Qué es |
|---|---|
| `CLAUDE.md` | quién soy y cómo trabajo |
| `settings.json` | mis permisos y plugins |
| `skills/` | mis habilidades para cualquier proyecto |
| `agents/` | mis asistentes especializados |
| `projects/…/memory/` | lo que Claude aprende solo, uno por proyecto |
| `~/.claude.json` | mis conectores: correo, calendario, Drive |

## Textos del dibujo por nivel
Textos que muestra el dibujo para cada nivel. El molde define qué archivos existen, en qué niveles y si bajan o se comparten; las frases del dibujo salen de esta tabla.

| Archivo | Nivel | Etiqueta | Descripción |
|---|---|---|---|
| .git/ | empresa | .git/ | la conexión con GitHub (carpeta oculta): sabe de qué repositorio vino y adónde subir. Se crea sola al descargar |
| .git/ | area | .git/ | la conexión con GitHub (carpeta oculta): sabe de qué repositorio vino y adónde subir. Se crea sola al descargar |
| .git/ | proyecto | .git/ | la conexión con GitHub (carpeta oculta): sabe de qué repositorio vino y adónde subir. Se crea sola al descargar |
| CLAUDE.md | empresa | CLAUDE.md | reglas de la empresa: Claude las lee solo en todo lo de adentro |
| CLAUDE.md | area | CLAUDE.md | reglas del área: se suman a las de la empresa |
| CLAUDE.md | proyecto | CLAUDE.md | reglas del proyecto: qué es y cómo se trabaja |
| .claude/settings.json | empresa | .claude/settings.json | permisos para trabajar acá · activa el paquete de la empresa |
| .claude/settings.json | area | .claude/settings.json | permisos para trabajar acá · activa el paquete de la empresa |
| .claude/settings.json | proyecto | .claude/settings.json | permisos del proyecto · activa el paquete de la empresa (y el del área, si hay) · tiene que estar subido a GitHub |
| .claude/skills/ | empresa | .claude/skills/ | habilidades para trabajar acá |
| .claude/skills/ | area | .claude/skills/ | habilidades para trabajar acá |
| .claude/skills/ | proyecto | .claude/skills/ | habilidades para trabajar acá |
| .claude/agents/ | empresa | .claude/agents/ | asistentes para trabajar acá |
| .claude/agents/ | area | .claude/agents/ | asistentes para trabajar acá |
| .claude/agents/ | proyecto | .claude/agents/ | asistentes para trabajar acá |
| .claude/rules/ | empresa | .claude/rules/ | reglas por tema, que se leen cuando hacen falta |
| .claude/rules/ | area | .claude/rules/ | reglas por tema, que se leen cuando hacen falta |
| .claude/rules/ | proyecto | .claude/rules/ | reglas por tema, que se leen cuando hacen falta |
| .mcp.json | empresa | .mcp.json | conectores para trabajar acá |
| .mcp.json | area | .mcp.json | conectores para trabajar acá |
| .mcp.json | proyecto | .mcp.json | conectores para trabajar acá |
| docs/ | empresa | docs/ | documentos |
| docs/ | area | docs/ | documentos |
| docs/ | proyecto | docs/ | documentos |
| .env.example | empresa | .env.example | qué claves hacen falta, sin los valores |
| .env.example | area | .env.example | qué claves hacen falta, sin los valores |
| .env.example | proyecto | .env.example | qué claves hacen falta, sin los valores |
| docs/PRD.md | empresa | docs/PRD.md | qué es la empresa, para quién, cuándo está terminada y qué NO se hace |
| docs/PRD.md | area | docs/PRD.md | qué es el área, para quién, cuándo está terminada y qué NO se hace |
| docs/PRD.md | proyecto | docs/PRD.md | qué es, para quién, cuándo está terminado y qué NO se hace; con código, suma la sección técnica y el diagrama de flujo de la app |
| docs/decisiones.md | empresa | docs/decisiones.md | cada decisión con su fecha y el porqué |
| docs/decisiones.md | area | docs/decisiones.md | cada decisión con su fecha y el porqué |
| docs/decisiones.md | proyecto | docs/decisiones.md | cada decisión con su fecha y el porqué |
| docs/planes/ | empresa | docs/planes/ | un plan por etapa (AAAA-MM-DD-tema.md); al terminar, se archiva |
| docs/planes/ | area | docs/planes/ | un plan por etapa (AAAA-MM-DD-tema.md); al terminar, se archiva |
| docs/planes/ | proyecto | docs/planes/ | un plan por etapa (AAAA-MM-DD-tema.md); al terminar, se archiva. Las pantallas van como mockups y el esquema de datos sale del código |
| docs/arquitectura.md | proyecto | docs/arquitectura.md | cómo está armado por dentro (TRD): piezas, dependencias, dónde corre. Si hay código |
| docs/arquitectura.md | empresa | docs/arquitectura.md | cómo está armado por dentro (TRD): piezas, dependencias, dónde corre. Si hay código |
| docs/arquitectura.md | area | docs/arquitectura.md | cómo está armado por dentro (TRD): piezas, dependencias, dónde corre. Si hay código |
| docs/flujo-de-la-app.md | proyecto | docs/flujo-de-la-app.md | cómo se mueve la persona por la app, en un diagrama. Si hay código |
| docs/flujo-de-la-app.md | empresa | docs/flujo-de-la-app.md | cómo se mueve la persona por la app, en un diagrama. Si hay código |
| docs/flujo-de-la-app.md | area | docs/flujo-de-la-app.md | cómo se mueve la persona por la app, en un diagrama. Si hay código |
| docs/diseno/ | proyecto | docs/diseno/ | las pantallas como mockups (HTML o Figma), nunca texto |
| docs/diseno/ | empresa | docs/diseno/ | las pantallas como mockups (HTML o Figma), nunca texto |
| docs/diseno/ | area | docs/diseno/ | las pantallas como mockups (HTML o Figma), nunca texto |
| docs/esquema/ | proyecto | docs/esquema/ | esquema de datos y API generados desde el código, con comando y fecha |
| docs/esquema/ | empresa | docs/esquema/ | esquema de datos y API generados desde el código, con comando y fecha |
| docs/esquema/ | area | docs/esquema/ | esquema de datos y API generados desde el código, con comando y fecha |
| docs/operacion.md | proyecto | docs/operacion.md | dónde corre, cómo se despliega y se vuelve atrás, claves (nombres) y respaldo |
| docs/operacion.md | empresa | docs/operacion.md | dónde corre, cómo se despliega y se vuelve atrás, claves (nombres) y respaldo |
| docs/operacion.md | area | docs/operacion.md | dónde corre, cómo se despliega y se vuelve atrás, claves (nombres) y respaldo |
| docs/specs/ | proyecto | docs/specs/ | una especificación por funcionalidad (AAAA-MM-DD-tema.md) |
| docs/specs/ | empresa | docs/specs/ | una especificación por funcionalidad (AAAA-MM-DD-tema.md) |
| docs/specs/ | area | docs/specs/ | una especificación por funcionalidad (AAAA-MM-DD-tema.md) |
| README.md | proyecto | README.md | para personas: qué es y cómo se levanta y se prueba. Si hay código |
| README.md | empresa | README.md | para personas: qué es y cómo se levanta y se prueba. Si hay código |
| README.md | area | README.md | para personas: qué es y cómo se levanta y se prueba. Si hay código |
| tests/ | proyecto | tests/ | las pruebas y cómo correrlas. Si hay código |
| tests/ | empresa | tests/ | las pruebas y cómo correrlas. Si hay código |
| tests/ | area | tests/ | las pruebas y cómo correrlas. Si hay código |
| .claude/security-checks/ | proyecto | .claude/security-checks/ | registro de revisiones de seguridad, sin valores de claves |
| .claude/security-checks/ | empresa | .claude/security-checks/ | registro de revisiones de seguridad, sin valores de claves |
| .claude/security-checks/ | area | .claude/security-checks/ | registro de revisiones de seguridad, sin valores de claves |
| .claude/rules/donde-va-cada-cosa.md | proyecto | .claude/rules/donde-va-cada-cosa.md | el mapa de la caja: dónde va cada pieza |
| .claude/rules/donde-va-cada-cosa.md | empresa | .claude/rules/donde-va-cada-cosa.md | el mapa de la caja: dónde va cada pieza |
| .claude/rules/donde-va-cada-cosa.md | area | .claude/rules/donde-va-cada-cosa.md | el mapa de la caja: dónde va cada pieza |
| .claude/PENDIENTES.md | empresa | .claude/PENDIENTES.md | la lista de pendientes (la mantiene /pendientes) |
| .claude/PENDIENTES.md | area | .claude/PENDIENTES.md | la lista de pendientes (la mantiene /pendientes) |
| .claude/PENDIENTES.md | proyecto | .claude/PENDIENTES.md | la lista de pendientes (la mantiene /pendientes) |
| .claude/prompts/REANUDAR.md | empresa | .claude/prompts/REANUDAR.md | el texto de reanudación (lo deja /cerrar) |
| .claude/prompts/REANUDAR.md | area | .claude/prompts/REANUDAR.md | el texto de reanudación (lo deja /cerrar) |
| .claude/prompts/REANUDAR.md | proyecto | .claude/prompts/REANUDAR.md | el texto de reanudación (lo deja /cerrar) |
| .gitignore | empresa | .gitignore | no guarda las carpetas de adentro (cada una tiene su repositorio) |
| .gitignore | area | .gitignore | no guarda las carpetas de los proyectos |
| .gitignore | proyecto | .gitignore | lo que no se sube a GitHub |
| plugins/<paquete>/ | empresa | plugins/kit-empresa/ <span class="q">+ .claude-plugin/</span> | el paquete de la empresa: skills, agentes, avisos automáticos y conectores que usan todos |
| plugins/<paquete>/ | area | plugins/kit-ventas/ <span class="q">(opcional)</span> | paquete del área, si sus proyectos comparten skills o agentes |
| .claude-plugin/marketplace.json | empresa | — | — |
| .claude-plugin/marketplace.json | area | — | — |
| CLAUDE.local.md | empresa | CLAUDE.local.md | mis notas |
| CLAUDE.local.md | area | CLAUDE.local.md | mis notas |
| CLAUDE.local.md | proyecto | CLAUDE.local.md | mis notas |
| .claude/settings.local.json | empresa | .claude/settings.local.json | mis ajustes |
| .claude/settings.local.json | area | .claude/settings.local.json | mis ajustes |
| .claude/settings.local.json | proyecto | .claude/settings.local.json | mis ajustes |
| .env | empresa | .env | las claves |
| .env | area | .env | las claves |
| .env | proyecto | .env | las claves |

## Pie del dibujo
Cada caja es un repositorio en GitHub, y el acceso se da en GitHub, repositorio por repositorio. En la computadora, cada carpeta es la copia de su repositorio y se conecta por su `.git/`. Cada persona descarga solo los repositorios donde está su punto: Beto nunca tiene Marketing ni Empresa-B, porque no las puede descargar. Los puntos huecos son para que Claude lea las reglas de la empresa o del área, aunque esa persona trabaje solo en un proyecto.

Todas las cajas tienen los mismos archivos (empresa, área y proyecto), porque en cualquiera se puede abrir Claude a trabajar. Lo que está en `.claude/` rige solo cuando trabajás en esa caja. Lo marcado con `↓ llega a lo de adentro` es lo único que pasa a las cajas de adentro: las reglas (`CLAUDE.md`) y el paquete, que cada caja activa en su `settings.json`. Lo verde no se sube a GitHub.


## Fuentes
Documentación oficial de Claude Code, verificada el 2026-10-13. Si una cambia, se revisa este archivo.

| Clave | Página | Qué sostiene |
|---|---|---|
| memory | https://code.claude.com/docs/en/memory.md | `CLAUDE.md` se lee desde la carpeta de arranque hacia arriba; `CLAUDE.local.md` igual; `.claude/rules/`; menos de 200 líneas |
| settings | https://code.claude.com/docs/en/settings.md | `settings.json` se lee solo de la carpeta de arranque, sin herencia; `settings.local.json` personal |
| skills | https://code.claude.com/docs/en/skills.md | las skills se buscan hacia arriba solo hasta la raíz del repositorio |
| sub-agents | https://code.claude.com/docs/en/sub-agents.md | los agentes, igual: hasta la raíz del repositorio |
| mcp | https://code.claude.com/docs/en/mcp.md | `.mcp.json` del proyecto; `~/.claude.json` personal |
| plugins-reference | https://code.claude.com/docs/en/plugins-reference.md | un paquete lleva skills, agentes, avisos y conectores; no lleva `CLAUDE.md` ni permisos |
| plugin-marketplaces | https://code.claude.com/docs/en/plugin-marketplaces.md | `.claude-plugin/marketplace.json`; el repositorio puede ser privado |
| large-codebases | https://code.claude.com/docs/en/large-codebases.md | reglas por carpeta y qué no se hereda |
