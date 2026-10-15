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
| `.claude/settings.json` | permisos de esa caja y qué paquetes activa | E A P | sí | sí | no | settings |
| `.claude/skills/` | habilidades para trabajar en esa caja | E A P | sí | no | no | skills |
| `.claude/agents/` | asistentes para trabajar en esa caja | E A P | sí | no | no | sub-agents |
| `.claude/rules/` | reglas por tema, que se leen cuando hacen falta | E A P | sí | no | no | memory |
| `.mcp.json` | conectores para trabajar en esa caja | E A P | sí | no | no | mcp |
| `docs/` | documentos | E A P | sí | no | no | — |
| `docs/PRD.md` | el documento vivo de la caja: qué es, para quién, cuándo está terminada y qué NO se hace. Si la caja tiene código, lleva además una sección técnica (cómo está armado: es el TRD) y un diagrama de flujo (cómo se mueve la persona por la app) | E A P | sí | sí | no | — |
| `docs/decisiones.md` | el registro de decisiones: cada una con fecha y el porqué, para no volver a discutirla | E A P | sí | sí | no | — |
| `docs/planes/` | un plan por etapa de trabajo, nombrado `AAAA-MM-DD-tema.md`; cuando la etapa termina, el plan se archiva | E A P | sí | sí | no | — |
| `.env.example` | qué claves hacen falta, sin los valores | E A P | sí | si hay .env | no | — |
| `.gitignore` | lo que no se sube a GitHub; en empresa y área, además, las carpetas de adentro | E A P | sí | sí | no | git |
| `plugins/<paquete>/` | el paquete: skills, agentes, avisos automáticos y conectores comunes (en el área, opcional) | E A | sí | no | sí | plugins-reference |
| `.claude-plugin/marketplace.json` | la vidriera: avisa que en esta caja hay un paquete para instalar | E A | sí | si hay paquete | no | plugin-marketplaces |
| `CLAUDE.local.md` | mis notas | E A P | no | no | sí | memory |
| `.claude/settings.local.json` | mis ajustes | E A P | no | no | no | settings |
| `.env` | las claves | E A P | no | no | no | — |

### Tres documentos vivos en toda caja
Toda caja (empresa, área y proyecto), tenga código o no, lleva los mismos tres documentos. Así, quien abre Claude en cualquier caja, aunque no sepa de desarrollo, sabe siempre **dónde guarda cada cosa y con qué nombre**; la sesión no tiene que adivinar ni decidir si algo «es desarrollo». En vez de seis documentos fijos (PRD, TRD, flujo de la app, UI/UX, esquema de datos, plan), son tres, que se mantienen al día:
- `docs/PRD.md`: qué es la caja, para quién, cuándo está terminada y qué NO se hace. Si hay código, suma la sección técnica (el TRD) y el diagrama de flujo de la app.
- `docs/decisiones.md`: el registro de decisiones, cada una con fecha y el porqué.
- `docs/planes/`: un plan por etapa, nombrado `AAAA-MM-DD-tema.md`; al terminar la etapa, el plan se archiva.

Lo demás no es un documento de texto: **el diseño de pantallas (UI/UX) son mockups** (Figma o HTML), no texto, y **el esquema de datos se genera desde el código, nunca a mano**.

**«Tiene código»** ya no decide si la caja lleva los tres documentos (los lleva siempre). Solo decide el contenido del PRD: con código, la plantilla incluye la sección técnica y el flujo de la app. Se decide con señales baratas, sin leer el código: la caja tiene `package.json`, `pyproject.toml`, `requirements.txt` o `Package.swift` en su raíz, o una carpeta `src/` o `app/` que contenga al menos un archivo de código (`.py`, `.js`, `.ts`, `.tsx`, `.jsx`, `.swift`, `.go`, `.rs`, `.java`, `.php`, `.rb`). Con una sola señal alcanza.

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
| R3 | `CLAUDE.md` con menos de 200 líneas | toda caja | aviso | pasar bloques a `.claude/rules/`: lo propone Claude, decidís vos |
| R4 | Tiene `.claude/settings.json` y es un JSON válido | toda caja | ✗ | `estructura.py arreglar` lo crea sin pisar nada |
| R5 | Tiene `.gitignore` | toda caja | ✗ | `estructura.py arreglar` lo crea sin pisar nada |
| R6 | `.env`, `.claude/settings.local.json` y `CLAUDE.local.md` no están en GitHub | toda caja | ✗ | sacarlo de GitHub sin borrarlo (`git rm --cached <archivo>`); si tenía claves, cambiarlas |
| R7 | Si hay `.env`, hay `.env.example` | toda caja | aviso | `estructura.py arreglar` crea el `.env.example` con los nombres, sin los valores |
| R8 | El repositorio no guarda las cajas de adentro (las ignora por patrón) | empresa y área | ✗ | llevar cada caja de adentro a su propio repositorio: es un cambio grande, se planifica con Claude antes de tocar nada |
| R9 | Cada skill (`.claude/skills/<nombre>/SKILL.md`) y cada agente (`.claude/agents/*.md`) tiene encabezado con `name` y `description` | toda caja | ✗ | agregar `name:` y `description:` al encabezado del archivo |
| R10 | Si la empresa o el área de arriba tiene paquete, `settings.json` lo activa | toda caja de adentro | aviso | activar el paquete en `.claude/settings.json` |
| R11 | `~/Proyectos/` no es un repositorio | raíz | ✗ | sacar el `.git` de la carpeta de proyectos, con respaldo: lo hace Claude con tu OK |
| R12 | Tiene los tres documentos vivos: `docs/PRD.md`, `docs/decisiones.md` y la carpeta `docs/planes/` (ver «Tres documentos vivos en toda caja») | toda caja | aviso | `estructura.py arreglar` los crea con instrucciones adentro (qué va, cómo se nombra, un ejemplo mínimo); el contenido lo completa el PM o la sesión con Claude, nunca se inventa |

**Excepciones:** lo que se decidió dejar así, con su motivo, no queda como ✗ para siempre: se anota en
`.estructura-excepciones.json` en la raíz del repositorio, una lista de
`{"regla": "R8", "ruta": "mi-caja", "motivo": "por qué se deja", "fecha": "AAAA-MM-DD"}` (`ruta` es la carpeta de la que
habla el aviso, relativa a esa raíz; `.` es la raíz misma). El control la muestra como `• excepción …` y no la cuenta como
falla. Sin motivo o sin fecha no vale (se ignora y se avisa). R6 y R11 no se pueden exceptuar.

El control **solo avisa**: nunca cambia nada solo. Para completar lo que falta: `estructura.py completar <carpeta>`, que
agrega lo que no está y nunca pisa un archivo existente.

**Cuándo corre (nadie tiene que acordarse):** al abrir sesión revisa la carpeta actual · al cerrar sesión también · una vez
por semana, la primera sesión recorre todas las carpetas de `~/Proyectos/`.

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
| .claude/settings.json | proyecto | .claude/settings.json | permisos del proyecto · activa el paquete de la empresa (y el del área, si hay) |
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
