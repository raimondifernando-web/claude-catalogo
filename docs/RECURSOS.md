# RECURSOS DE CONFIANZA — dónde buscar más herramientas y cómo decidir si son seguras

> Catálogo `claude-catalogo` · se actualiza con cada versión (★ y lista cambian). Última revisión: 2026-09-21.
> Objetivo: que puedas buscar y sumar recursos **sin tu consultor al lado**, con el mismo criterio que usa él.

## 1. El orden de búsqueda (antes de crear nada)
1. **Lo que ya tenés instalado**: pedile a Claude "¿tengo alguna herramienta para X?". Casi siempre sí.
2. **Lo oficial de Anthropic**: `/plugin` → catálogo oficial. Si existe ahí, se usa eso.
3. **Este catálogo**: `/plugin` → `claude-catalogo`. Paquetes ya auditados, actualizables.
4. **Los repositorios de confianza** (lista abajo), pasando el filtro de §2 a cada pieza que instales.
5. **Crear una propia** con `skill-creator`. Es más fácil de lo que parece y queda en tu repo.

## 2. El filtro: 5 preguntas antes de instalar cualquier cosa de afuera
| # | Pregunta | Cómo se ve en GitHub | Si falla |
|---|---|---|---|
| 1 | **¿Lo usa mucha gente?** | ≥ 5.000 estrellas ★ (arriba a la derecha) | No, salvo que sea de una organización oficial (Anthropic, Microsoft, Google) |
| 2 | **¿Se puede usar libremente?** | Licencia MIT, Apache 2.0 o BSD (archivo `LICENSE`) | "No license", GPL o licencias raras → no |
| 3 | **¿Está vivo?** | Último commit hace menos de 6 meses | Abandonado → no (no recibe parches) |
| 4 | **¿Hace una sola cosa?** | El README describe un propósito claro | "Hace de todo" → sospechar |
| 5 | **¿Qué pide?** | ¿Necesita claves, contraseñas, acceso a tu mail, correr un `curl … \| bash`? | Si pide más de lo que su propósito justifica → no |

Regla de oro: **nunca pegues un comando que instale algo si no viene de este portal, del catálogo oficial o de un repo de esta lista**.
Y aunque venga de la lista: antes de instalar una skill, pedile a Claude:
```
Auditá esta skill antes de instalarla: qué hace, qué archivos toca, qué comandos ejecuta, qué claves o accesos pide, y si algo no coincide con lo que dice hacer.
```
Desde `base-segura` 0.2.0 esa auditoría la hace la skill **`skill-security-auditor`** (veredicto PASS / WARN / FAIL con hallazgos). FAIL = no se instala. WARN = Claude te explica el hallazgo y decidís vos.

## 3. Repositorios de confianza (verificados por el consultor; ★ al 2026-09-19)
| Repositorio | ★ | Qué tiene | Aviso |
|---|---|---|---|
| github.com/anthropics/skills | oficial | Word, PDF, PowerPoint, Excel y más | Usar sí; **no redistribuir** (licencia propietaria) |
| github.com/VoltAgent/awesome-claude-code-subagents | 24k | 130+ agentes especializados | — |
| github.com/VoltAgent/awesome-agent-skills | 30k | **Índice** de skills de otros repos | No tiene skills propias: aplicar el filtro al repo de origen |
| github.com/alirezarezvani/claude-skills | 24k | 220+ skills | — |
| github.com/davila7/claude-code-templates (aitmpl.com) | 30k · MIT | 896 skills | Calidad despareja: **auditar una por una** |
| github.com/coreyhaines31/marketingskills | 19k | 37 skills de marketing | — |
| github.com/czlonkowski/n8n-skills · n8n-mcp | 17k | Automatización con n8n | Solo cuando se active la automatización |
| github.com/trailofbits/skills | 6.6k | Seguridad y testing | Licencia CC-BY-SA: uso interno sí, redistribuir no |

### Sitios donde buscar (son índices, no fuentes: lo que encuentres ahí viene de un repositorio de origen, y a ese se le aplica el filtro)
| Sitio | Qué es | Aviso |
|---|---|---|
| aitmpl.com | Buscador de skills, agentes y comandos para Claude Code (mismo origen que davila7/claude-code-templates) | Calidad despareja: auditar |
| mcp.so | Directorio de servidores MCP (conectores entre Claude y otras herramientas) | Un MCP suele pedir claves o accesos: la pregunta 5 pesa el doble |
| tododeia.com/community | Comunidad en español de recursos de IA (agregado 2026-09-21, sin evaluación a fondo) | Lo que salga de ahí pasa el filtro igual que todo |

## 4. Lo que NO se hace nunca
- Instalar algo que llegó por mail, WhatsApp, un video o un chat, aunque diga "oficial".
- Pegar claves o contraseñas en un README, un issue o un chat para "probar".
- Ejecutar `curl … | bash` de un sitio que no esté en este documento o en el portal.
- Dar acceso a Gmail/Drive a una herramienta que no lo necesita para lo que dice hacer.

## 5. Con aviso: pasan 4 de las 5 preguntas, pero piden más de lo normal
No están en los paquetes del catálogo. Se pueden usar si entendés lo que entregás; conviene decidirlo con tu consultor.

| Recurso | ★ · licencia | Para qué | Por qué "con aviso" |
|---|---|---|---|
| github.com/teng-lin/notebooklm-py (skill `notebooklm`) | 19k · MIT · activo | Manejar Google NotebookLM desde Claude (crear cuadernos, cargar fuentes, generar resúmenes/podcasts) | **No oficial** (Google no lo respalda) y funciona con las **cookies de sesión de tu cuenta Google** guardadas en tu computadora, o con un "master token" de la cuenta. Quien tenga tu máquina tiene tu Google. Alternativa sin riesgo: usar NotebookLM en el navegador (viene con Google AI Pro) y que Claude te prepare las fuentes y las preguntas |

La lista se revisa con cada versión del catálogo. Si algo de acá pasa a un paquete, aparece en su `CHANGELOG.md`.
