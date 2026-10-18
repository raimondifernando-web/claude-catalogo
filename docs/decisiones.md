# claude-catalogo — Decisiones

> Registro de decisiones: cada una con su fecha y el porqué, para no volver a discutirla.
> Se agrega al final, una por bloque, la más nueva abajo. Nunca se borra una vieja: si cambia, se anota la nueva.

## 2026-10-05 — Los clientes siguen una rama `estable`, 48 horas detrás de `main`
Porque un error publicado llega a muchas computadoras a la vez; las 48 horas dan tiempo a verlo y frenarlo. Lo urgente y revisado se promueve a mano.

## 2026-10-14 — A `main` solo por PR con controles automáticos, sin pedir OK en cada cambio
Porque el OK humano en cada versión frenaba y no agregaba seguridad real. Decide la máquina (`controles` y `zona-sensible`); el OK de una persona queda
solo para lo que corre solo en la computadora de quien instala. Reemplaza la regla anterior de «todo push al catálogo lleva OK».

## 2026-10-18 — Esta carpeta cumple el molde como cualquier otra
Porque el control que se le exige a las carpetas de los clientes tiene que valer acá primero. `scripts/controles.sh` mide lo obligatorio del molde
de este repositorio (CLAUDE.md, .gitignore, PRD, decisiones y planes).
