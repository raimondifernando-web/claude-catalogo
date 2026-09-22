# base-segura — qué cambia para vos

## 0.10.0 — 2026-09-22
- **Cambia la primera pregunta del filtro de seguridad** (`docs/RECURSOS.md`), la que decide si se puede instalar algo de afuera. Antes era una sola: «¿tiene 5.000 estrellas?». Ahora alcanza con **uno** de tres caminos: **(a)** lo usa mucha gente (≥5.000 estrellas), **(b)** es de una organización oficial (Anthropic, Microsoft, Google, Vercel, Cursor), **o (c)** alguien leyó el contenido entero — y este último vale **solo si son puros archivos de texto**, sin nada que se ejecute ni se instale. Con código adentro no hay atajo: hace falta (a) o (b), porque leer un programa no te dice qué hace cuando corre.
- **Por qué cambió, dicho sin vueltas:** la skill `humanizalo` que entró en 0.8.0 **no llega a las 5.000 estrellas ni es de una organización oficial**. La pusimos igual, después de leer sus 27 KB de texto completos y auditarla. La decisión fue correcta —en algo que es solo texto, leerlo entero prueba más que contar estrellas—, pero dejaba la regla diciendo una cosa y nuestra práctica haciendo otra. Si te pedimos un criterio, lo cumplimos nosotros primero: cuando la excepción está bien fundada, **se corrige la regla**, no se hace la excepción por lo bajo.
- Las otras cuatro preguntas (licencia, que esté vivo, que haga una sola cosa, qué accesos pide) no cambian.
Para actualizar: `claude plugin update base-segura@claude-catalogo`.

## 0.9.0 — 2026-09-22
- Sin cambios; acompaña al catálogo 0.9.0 (`metodo`: guía de ruteo de modelos + criterio en `/metodo:crear-agente`).

## 0.8.0 — 2026-09-22
**Dos skills nuevas** (12 → 14), las dos sobre cómo suena Claude, y las dos gratis y de licencia MIT. Ninguna instala nada ni manda datos a ningún lado: son archivos de texto.
- **`humanizalo`** — que lo que escribe no se note escrito por una máquina. Revisa el texto contra **40 señas** concretas (el guion largo, «no es solo X, es Y», «en conclusión esto representa un cambio de paradigma», «espero que te sirva»), lo reescribe con voz propia, **se pone nota del 1 al 10 en 6 cosas** y no te lo entrega hasta pasar 42 de 60 o haber intentado 3 veces. Te muestra la nota y qué cambió. Para correos a clientes, propuestas, textos de la web y posteos. De `Hainrixz/humanizalo`; le agregamos la lista de señas **en español** (`references/espanol.md`: «profundizar», «panorama», «el mismo fue aprobado», «por medio de la presente», voseo) porque la original traía solo las inglesas.
- **`modo-directo`** — que te contesten lo que preguntaste. El largo lo fija **tu pregunta**: un sí o no se contesta en una línea; un «cómo hago» con el comando y listo; un «explicame» se extiende lo que haga falta. Sirve también al revés: le pegás un correo largo o un documento y te lo deja en lo esencial, diciéndote **qué quitó y de cuántas palabras a cuántas quedó**. Se apaga con «modo normal», y para una sola respuesta con «extendete».
- **Lo que nunca se recorta, aunque pidas respuestas cortas:** las advertencias de plata, de seguridad, de datos personales y de cosas que no se pueden deshacer; los supuestos; de dónde salió un número; y la lista de lo que se cambió cuando hubo cambios. Eso lo revisamos y lo reforzamos antes de publicarlas (ver `docs/SECURITY-CHECKS.md`).
- **Importante:** `modo-directo` cuenta con que tengas puestas las dos plantillas de `CLAUDE.md` de este paquete (el paso 1 del arranque). Lo probamos: **sin** ellas, a un «borrá estos archivos» te puede tirar el comando sin avisarte que no se recupera; **con** ellas, te pregunta antes y no borra nada. Si todavía no copiaste las plantillas, hacelo antes de usar el modo.
- **Quedan enganchadas en la plantilla `CLAUDE-empresa.md`**, en «Formato y tono»: si copiás la plantilla, Claude ya humaniza lo que va a un cliente y te contesta corto sin que se lo pidas cada vez.
Para actualizar: `claude plugin update base-segura@claude-catalogo`.

## 0.7.0 — 2026-09-22
- Sin cambios; acompaña al catálogo 0.7.0 (`rubro-estudio-arquitectura`: `identidad-visual-del-estudio` reemplaza a `brand-guidelines`).

## 0.6.0 — 2026-09-21
- **Nuevo `docs/CONECTORES.md`** + sección en `requisitos.md`: las herramientas que Claude puede usar en cualquier negocio y cómo se activan, en tres grupos. **A.** Conectores oficiales de claude.ai: Gmail, Google Calendar, Google Drive, Notion (más Canva, Excalidraw, ClickUp). **B.** Funciones de la app de Claude: **Claude in Chrome** (navega en tu Chrome) y **uso de la computadora** (maneja programas de la Mac) — mucho poder, se activan a conciencia, y nunca para pagar ni para códigos de verificación. **C.** Si hacés publicidad, medís tu web o automatizás: Meta Ads (conector oficial), Google Ads (oficial de Google, solo lectura), Microsoft Clarity (oficial), n8n, Firecrawl. Para cada uno: qué pide, qué sale de tu computadora, cuidados. Con orden sugerido para arrancar (A el día 1 → B → C solo si aplica). Por qué: el kit tenía las skills pero no decía cómo conectar Claude a las herramientas que ya usás.

## 0.5.0 — 2026-09-21
- Sin cambios; acompaña al catálogo 0.5.0 (`metodo`: `/arrancar` levanta `REANUDAR.md` sin pegar).

## 0.4.1 — 2026-09-21
- Sin cambios; acompaña al catálogo 0.4.1 (`metodo`: freno por archivos no-texto + `.gitignore` de fábrica).

## 0.4.0 — 2026-09-21
- Sin cambios; acompaña al catálogo 0.4.0 (`metodo`: sesiones en paralelo + cierre en un gesto).

## 0.3.0 — 2026-09-21
- Sin cambios; acompaña al catálogo 0.3.0 (9 skills nuevas en `rubro-estudio-arquitectura` + `docs/CAD-BIM.md`).

## 0.2.2 — 2026-09-21
- Sin cambios; acompaña al catálogo 0.2.2.

## 0.2.1 — 2026-09-21
- Sin cambios; acompaña al catálogo 0.2.1.

## 0.2.0 — 2026-09-21
- **Nueva skill `skill-security-auditor`**: antes de instalar una skill de afuera, Claude la audita (qué hace, qué archivos toca, qué comandos corre, qué claves pide) y da un veredicto PASS / WARN / FAIL. Con esto podés sumar recursos de los repositorios de confianza sin tu consultor al lado (`docs/RECURSOS.md` del catálogo). Necesita Python 3 (ya lo tenés si hiciste el paso 1 de `requisitos.md`).
- **`markitdown` sin "command not found"**: si el comando no quedó en el PATH (pasa con `pip install --user`), Claude lo usa como `python3 -m markitdown`. No tenés que arreglar nada.
Para actualizar: `claude plugin update base-segura@claude-catalogo`.

## 0.1.3 — 2026-09-21
- Chequeo de carpetas huérfanas: el aviso ⚠️ de posibles claves ahora se revisa en **todas** las carpetas, también las que ya están en nube o en un repo (una contraseña en la nube sigue estando mal). Sin cambios en las skills.

## 0.1.2 — 2026-09-21
- **Chequeo de carpetas huérfanas** (`scripts/huerfanas.sh`, ver `docs/CHEQUEO.md`): qué carpetas tuyas están solo en esta computadora, con el cajón sugerido. No mueve ni borra. Sin cambios en las skills.

## 0.1.1 — 2026-09-21
Nada nuevo para aprender; esta versión te dice **qué necesita tu computadora** antes de que algo falle.
- **`requisitos.md`** (nuevo, en la carpeta del plugin): qué skill necesita qué programa de fondo, qué pasa si falta y el comando exacto para Mac. 8 de las 11 skills no necesitan nada.
- **Aviso amable en vez de error**: `markitdown`, `excel-analysis` y `mermaid-diagrams` ahora chequean primero si tienen lo que necesitan. Si falta, Claude te dice "hace falta instalar X, está en tu portal" y te ofrece una alternativa, en vez de mostrarte un error de terminal.
- **Chequeo con un comando**: `docs/CHEQUEO.md` del catálogo → pegás una línea en Terminal y te dice OK / FALTA / OPCIONAL de todo.
Para actualizar: `claude plugin update base-segura@claude-catalogo`.

## 0.1.0 — 2026-09-20
Primera versión. Es la "base segura" (capa L1): lo que cualquier empresa necesita el día 1, sin importar el rubro.
- **11 skills** para escribir, leer documentos, analizar y ordenar el trabajo (redacción clara, corrección, comunicación profesional, coautoría de documentos, diagramas, lectura de PDF/Word/Excel con markitdown, análisis de Excel, minutas de reuniones, planificación en archivos, handoff entre sesiones, creador de skills propias).
- **3 agentes**: investigador (`research-analyst`), abogado del diablo (`critic`), planificador (`planner`).
- **2 plantillas** en `templates/`: `CLAUDE-global.md` (10 reglas, va en `~/.claude/CLAUDE.md`) y `CLAUDE-empresa.md` (va en tu carpeta de trabajo). Un plugin no puede instalarlas solo: se copian una vez, guiado.
Lo del rubro (propuestas, precios, marketing, diseño) llega en un plugin aparte (`rubro-<tu rubro>`). El método completo (`/cerrar`, `/arrancar`, `/criticar`, `/planear`) llega cuando lo necesites (`metodo`).
