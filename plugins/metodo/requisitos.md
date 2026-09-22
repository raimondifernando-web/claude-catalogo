# metodo — qué necesita tu computadora

**Casi nada.** Las 6 skills (`/metodo:arrancar`, `/metodo:planear`, `/metodo:criticar`, `/metodo:cerrar`, `/metodo:crear-agente`, `/metodo:otra-sesion`) son solo texto: funcionan con Claude Code, sin programas de fondo, sin claves.

Lo único que usan `/metodo:cerrar` (guardar y subir el avance) y `/metodo:otra-sesion` (segunda sesión en su propia copia) es **git**, que viene con las herramientas de desarrollo de Apple que ya instalaste para `base-segura`. El chequeo del catálogo lo verifica. Plantilla `templates/gitignore-estudio`: qué NO sube al repositorio por defecto (claves, documentos de clientes, archivos pesados).

Atajos: si no tenés otras skills con esos nombres, `/arrancar` y `/cerrar` a secas también funcionan. `/cerrar` deja `REANUDAR.md` en tu carpeta de trabajo y `/arrancar` lo lee solo: no hace falta pegar el texto de arranque.

Si igual querés ver el estado de tu equipo, corré el chequeo del catálogo (`docs/CHEQUEO.md`).
