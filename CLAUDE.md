# claude-catalogo

Catálogo público de plugins para Claude Code (ver `README.md`). Todo lo que hay acá es genérico: **sin datos, sin credenciales y sin
nombres de personas ni de clientes** (ni en changelogs, ni en ramas, ni en descripciones).

## Cómo se trabaja
- **A `main` solo por PR.** Antes de abrirlo: `bash scripts/controles.sh` (metadatos, pruebas y el molde de esta caja). GitHub exige los checks
  `controles` y `zona-sensible`; el segundo pide el OK del dueño cuando el cambio toca lo que corre solo en la computadora de quien instala
  (hooks y lo que llaman, `settings.json`, instaladores, `.github/`, los controles).
- **Los clientes siguen la rama `estable`**, que avanza a lo publicado 48 horas después (`estable.yml`). No se toca a mano.
- **Versiones:** cada plugin tiene su `CHANGELOG.md` en lenguaje del cliente («qué cambia para vos»); `scripts/verificar-metadatos.sh`
  comprueba que `marketplace.json`, cada `plugin.json` y la fila del `README.md` digan la misma versión. Los plugins suben juntos.
- **Chequeo de seguridad:** cada versión publicada deja su línea en `docs/SECURITY-CHECKS.md`.

## El molde de las carpetas
La fuente única de cómo se ordena una caja (archivos obligatorios, opcionales y qué baja a las de adentro) es
`plugins/metodo/estructura/ESTRUCTURA.md`; el control es `plugins/metodo/scripts/estructura.py`. Esta carpeta es una caja más: lleva
`docs/PRD.md`, `docs/decisiones.md` y `docs/planes/`.

## Dónde se guarda cada cosa
- Qué es esta caja y qué NO se hace → `docs/PRD.md`
- Una decisión, con fecha y el porqué → `docs/decisiones.md`
- El plan de una etapa → `docs/planes/AAAA-MM-DD-tema.md` (al terminar, se archiva)
- Chequeos de seguridad por versión → `docs/SECURITY-CHECKS.md`
