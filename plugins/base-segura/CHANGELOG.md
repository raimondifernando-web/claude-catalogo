# base-segura — qué cambia para vos

## 0.1.0 — 2026-09-20
Primera versión. Es la "base segura" (capa L1): lo que cualquier empresa necesita el día 1, sin importar el rubro.
- **11 skills** para escribir, leer documentos, analizar y ordenar el trabajo (redacción clara, corrección, comunicación profesional, coautoría de documentos, diagramas, lectura de PDF/Word/Excel con markitdown, análisis de Excel, minutas de reuniones, planificación en archivos, handoff entre sesiones, creador de skills propias).
- **3 agentes**: investigador (`research-analyst`), abogado del diablo (`critic`), planificador (`planner`).
- **2 plantillas** en `templates/`: `CLAUDE-global.md` (10 reglas, va en `~/.claude/CLAUDE.md`) y `CLAUDE-empresa.md` (va en tu carpeta de trabajo). Un plugin no puede instalarlas solo: se copian una vez, guiado.
Lo del rubro (propuestas, precios, marketing, diseño) llega en un plugin aparte (`rubro-<tu rubro>`). El método completo (`/cerrar`, `/arrancar`, `/criticar`, `/planear`) llega cuando lo necesites (`metodo`).
