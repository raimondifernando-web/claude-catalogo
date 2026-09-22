# base-segura — qué cambia para vos

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
