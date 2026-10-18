# claude-catalogo — PRD

> Documento vivo: qué es esta caja. Lo completa quien la lleva con Claude; no se inventa nada.

- Dueño: Tech (el rol que lleva la arquitectura del ecosistema); el producto lo decide Consultoría IA
- Estado: activa
- Respaldo: GitHub (repositorio público)
- Última revisión: 2026-10-18

## Qué es y para quién
Un catálogo público de plugins para Claude Code, pensado para empresas y profesionales que empiezan con Claude acompañados por una consultoría:
skills y agentes por rubro, un método de trabajo (`metodo`: arrancar, planear, cerrar, controles de carpetas y de seguridad) y paneles de la app.
Se instala con `claude plugin marketplace add …` y se actualiza solo siguiendo la rama `estable`.

## Cuándo está terminado
No termina: es un producto vivo. Cada versión está lista cuando pasan `controles` y `zona-sensible` en GitHub, el `CHANGELOG.md` del plugin
cuenta el cambio en lenguaje del cliente y `docs/SECURITY-CHECKS.md` tiene la línea del chequeo de esa versión.

## Qué NO se hace
- No se publican datos, credenciales, nombres de clientes ni de personas.
- No se une nada a `main` sin pasar por un PR con sus controles.
- No se le pide al cliente que corra comandos para estar al día: todo llega por la actualización automática.
