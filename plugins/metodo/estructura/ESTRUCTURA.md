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
| `.env.example` | qué claves hacen falta, sin los valores | E A P | sí | si hay .env | no | — |
| `.gitignore` | lo que no se sube a GitHub; en empresa y área, además, las carpetas de adentro | E A P | sí | sí | no | git |
| `plugins/<paquete>/` | el paquete: skills, agentes, avisos automáticos y conectores comunes (en el área, opcional) | E A | sí | no | sí | plugins-reference |
| `.claude-plugin/marketplace.json` | la vidriera: avisa que en esta caja hay un paquete para instalar | E A | sí | si hay paquete | no | plugin-marketplaces |
| `CLAUDE.local.md` | mis notas | E A P | no | no | sí | memory |
| `.claude/settings.local.json` | mis ajustes | E A P | no | no | no | settings |
| `.env` | las claves | E A P | no | no | no | — |

Fuera de las cajas:

| Carpeta | Qué es | Comparte |
|---|---|---|
| `~/Proyectos/` | agrupa todas las cajas; no es un repositorio | no |
| `~/.claude/` | de cada persona: su `CLAUDE.md`, `settings.json`, `skills/`, `agents/` y la memoria de cada proyecto | no |
| `~/.claude.json` | los conectores personales (correo, calendario, Drive) | no |

## Reglas que revisa el control
| Id | Regla | Dónde | Si falla |
|---|---|---|---|
| R1 | Tiene `.git/` con un remoto (copia en GitHub) | toda caja | ✗ |
| R2 | Tiene `CLAUDE.md` | toda caja | ✗ |
| R3 | `CLAUDE.md` con menos de 200 líneas | toda caja | aviso |
| R4 | Tiene `.claude/settings.json` y es un JSON válido | toda caja | ✗ |
| R5 | Tiene `.gitignore` | toda caja | ✗ |
| R6 | `.env`, `.claude/settings.local.json` y `CLAUDE.local.md` no están en GitHub | toda caja | ✗ |
| R7 | Si hay `.env`, hay `.env.example` | toda caja | aviso |
| R8 | El repositorio no guarda las cajas de adentro (las ignora por patrón) | empresa y área | ✗ |
| R9 | Cada skill (`.claude/skills/<nombre>/SKILL.md`) y cada agente (`.claude/agents/*.md`) tiene encabezado con `name` y `description` | toda caja | ✗ |
| R10 | Si la empresa o el área de arriba tiene paquete, `settings.json` lo activa | toda caja de adentro | aviso |
| R11 | `~/Proyectos/` no es un repositorio | raíz | ✗ |

El control **solo avisa**: nunca cambia nada solo. Para completar lo que falta: `estructura.py completar <carpeta>`, que
agrega lo que no está y nunca pisa un archivo existente.

**Cuándo corre (nadie tiene que acordarse):** al abrir sesión revisa la carpeta actual · al cerrar sesión también · una vez
por semana, la primera sesión recorre todas las carpetas de `~/Proyectos/`.

## Ejemplo del dibujo
Personas: **Vos** (dueño, todo) · **Lucía** (socia, toda la Empresa A) · **Beto** (solo el área Ventas) · **Caro** (solo el
proyecto web). Quien trabaja en un área o un proyecto tiene acceso de lectura a las cajas de arriba, para que Claude lea sus
`CLAUDE.md`.

```
Empresa-A        empresa   empresa-a/empresa-a     vos lu be:lee ca:lee
  Ventas         area      empresa-a/ventas        vos lu be
    crm          proyecto  empresa-a/crm           vos lu be
    presupuestos proyecto  empresa-a/presupuestos  vos lu be
  Marketing      area      empresa-a/marketing     vos lu ca:lee
    web          proyecto  empresa-a/web           vos lu ca
    campañas     proyecto  empresa-a/campanas      vos lu
Empresa-B        empresa   empresa-b/empresa-b     vos
Personal         proyecto  vos/personal            vos
```

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
