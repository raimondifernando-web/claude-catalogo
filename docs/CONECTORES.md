# Conectores y herramientas para cualquier negocio — qué existe, qué pide, qué sale de tu computadora

> Complementa a `plugins/base-segura/requisitos.md`. Nada de esto se instala con el catálogo: son **conectores** (Claude
> usa una herramienta tuya a través de tu cuenta) o **funciones de la app de Claude**. Se activan **uno por vez**, cuando
> lo necesités, y cada uno pide acceso a algo tuyo: por eso antes de conectar pesa doble la pregunta 5 del filtro de
> `docs/RECURSOS.md` («¿qué datos salen y hacia dónde?»). Verificado 2026-09-21.

## Las 3 reglas antes de conectar cualquier cosa
1. **Lo autorizás vos, desde tu cuenta.** Nadie conecta por vos; tu consultor te guía, vos hacés clic en *Conectar*.
2. **Claves y contraseñas nunca en el chat.** Si una herramienta pide una clave (token), la cargás vos donde corresponde.
   Claude solo verifica que exista.
3. **Pagos, transferencias y códigos de verificación (2FA): siempre vos.** Claude puede navegar, leer y preparar; nunca
   paga, nunca mueve plata, nunca tipea un código que te llegó al teléfono.

## A. Conectores oficiales de claude.ai (los que más rinden, para todos)
Cómo: **claude.ai → tu perfil → Configuración → Conectores → Explorar conectores** → buscá el nombre → *Conectar* →
iniciás sesión con tu cuenta y aceptás los permisos. Valen en Claude Code, Cowork y el chat; en Claude Code se ven con `/mcp`.

| Conector | Para qué en un negocio | Qué sale de tu computadora | Costo |
|---|---|---|---|
| **Gmail** | Buscar mails, resumir hilos, redactar respuestas (vos las mandás o le decís «mandá») | Claude lee tu correo **en tu cuenta**; los textos que resume pasan por Claude. No conectes una casilla compartida sin avisar a quien la usa | Tu cuenta Google |
| **Google Calendar** | Ver agenda, buscar huecos, crear eventos, preparar la semana | Tus eventos | Tu cuenta Google |
| **Google Drive** | Buscar y leer documentos, hojas y presentaciones; crear archivos | Lee lo que le pidas de tu Drive. Cuidado con carpetas de clientes con datos sensibles | Tu cuenta Google |
| **Notion** | Leer y escribir páginas y bases de datos: CRM liviano, seguimiento de proyectos | Tu espacio de Notion (el que autorices) | Tu cuenta Notion |
| **Canva** · **Excalidraw** | Diseños y diagramas (ver `rubro-estudio-arquitectura/requisitos.md`) | Lo que le pidas | Tu cuenta |
| **ClickUp** (beta) | Tareas del equipo; base de `plan-semanal-estudio` | Tus tareas | Tu cuenta |

## B. Funciones de la app de Claude (manejar la computadora y el navegador)
Son las herramientas **de más poder y más riesgo**: Claude hace clic y tipea en tu computadora. Por eso se activan a
conciencia, se usan con vos mirando, y **nunca para pagar ni para códigos de verificación** (regla 3).

| Función | Qué hace | Cómo se activa | Cuidados |
|---|---|---|---|
| **Claude in Chrome** (extensión oficial de Anthropic) | Navega en **tu Chrome**, con tus sesiones abiertas: completar formularios, leer páginas, comparar, descargar. Claude Code la usa cuando le pedís «hacelo en Chrome» | Chrome Web Store → *Claude in Chrome* → instalar → iniciar sesión con tu cuenta de Claude. En Claude Code aparece como `claude-in-chrome` | Ve todo lo que hay en la pestaña (incluidas tus cuentas abiertas). Si una página te pide contraseña, pago o código, **lo hacés vos**. Preferí una ventana de Chrome sin pestañas de banco/pagos mientras trabaja |
| **Uso de la computadora** (app de escritorio de Claude: *Computer use* / *Control your Mac*) | Ve la pantalla y maneja programas nativos de la Mac (Finder, Notas, Vista Previa, tu CAD…) con clics y teclado; en Mac también ejecuta AppleScript | App de Claude para Mac → Configuración → activar y **dar permiso app por app** (macOS pide Accesibilidad y Grabación de pantalla). Cada programa nuevo pide tu aprobación | Es literalmente alguien usando tu computadora. Tres límites que vienen de fábrica y no se levantan: **no** paga, **no** entra a cuentas con contraseña, **no** borra en forma permanente. Lo que ve en pantalla lo trata como datos, no como órdenes. Usalo con la pantalla a la vista |

## C. Herramientas de marketing y automatización (si hacés publicidad, medís tu web o automatizás)
| Herramienta | Qué es | Para qué | Cómo se conecta | Qué pide / cuidados |
|---|---|---|---|---|
| **Meta Ads** (Facebook/Instagram) | Conector oficial del directorio de claude.ai | Leer campañas, gasto, resultados; analizar creativos; preparar cambios (vos los aplicás en el Administrador de anuncios) | Conectores de claude.ai → *Meta Ads* → autorizás con tu cuenta de Meta | Acceso a tu cuenta publicitaria. Solo lectura y análisis: los cambios de presupuesto los hacés vos |
| **Google Ads** | `google-ads-mcp` (oficial de Google, Apache-2.0) | Consultar campañas, palabras clave, gasto y resultados (**solo lectura**) | Configuración técnica: proyecto en Google Cloud + acceso de desarrollador + tu cuenta de Google Ads. **La hace tu consultor con vos**, una vez | No modifica campañas (para eso, Google Ads Editor). Requiere Python 3 |
| **Microsoft Clarity** | `@microsoft/clarity-mcp-server` (oficial de Microsoft, MIT) | Mapas de calor, grabaciones de sesión y métricas de comportamiento de tu web | Cuenta gratis en clarity.microsoft.com → instalar el código en tu web → clave de API del proyecto → tu consultor la configura como variable de entorno | La clave es un secreto (regla 2). Clarity ya recibe los datos de tu web; el conector solo los lee |
| **n8n** (automatizaciones) | `n8n-mcp` (comunidad, 23k★, MIT, muy activo) + tu instancia de n8n | Que Claude diseñe, valide y arregle automatizaciones (mail → hoja → aviso; formulario → CRM…) | Necesitás una instancia de n8n (nube n8n.io o servidor propio) + clave de API de esa instancia; `npx -y n8n-mcp` | El conector puede **crear y modificar automatizaciones que corren solas**: probá en una automatización de prueba antes de tocar una en producción. La clave es secreto |
| **Firecrawl** (leer sitios web) | `firecrawl-mcp` (oficial de Firecrawl) | Leer y extraer contenido de páginas: competidores, proveedores, normativa publicada | `npx -y firecrawl-mcp` + clave de Firecrawl (hay plan gratis) | Las URLs que le pidas salen hacia Firecrawl |

## D. Lo que NO va al kit
- **Odoo** y cualquier sistema interno de una empresa en particular: es de esa empresa, no de un kit genérico.
- Conectores que piden tus **cookies de sesión** o **contraseñas en texto**: no pasan el filtro (`docs/RECURSOS.md` §5). NotebookLM es la excepción documentada, con su protocolo (`docs/NOTEBOOKLM-SEGURO.md`).

## Para el consultor
- Orden sugerido para un cliente nuevo: **A** (Gmail + Calendar + Drive el día 1; Notion si lo usa) → **B** (Chrome primero; uso de la computadora cuando ya confía en cómo trabaja Claude) → **C** solo si el negocio hace pauta / mide web / automatiza.
- Cada conector de **C** con clave: la carga el cliente como variable de entorno; el chequeo (`docs/CHEQUEO.md`) reporta si existe, nunca el valor. Sumar las líneas al `chequeo.sh` cuando el cliente los active.
- Fuentes verificadas 2026-09-21 por API de GitHub: `czlonkowski/n8n-mcp` 22.969★ MIT (push hoy) · `googleads/google-ads-mcp` 971★ Apache-2.0 (push hoy) · `microsoft/clarity-mcp-server` 116★ MIT (push 2026-02-24: lento; vigilar) · Claude in Chrome y uso de la computadora = producto de Anthropic · Meta Ads = conector del directorio oficial de claude.ai.
