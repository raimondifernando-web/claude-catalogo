# rubro-marketing

## 0.2.5 — 2026-10-08
- `achicar-datos-grandes`: la explicación del formato achicado estaba mal (decía que cada columna trae todos los valores; en realidad `@campo` es un diccionario de valores únicos y cada fila lleva el índice). Corregida en la skill y escrita dentro de cada archivo achicado para que no se lea mal un total.

## 0.2.4 — 2026-10-08
- `achicar-datos-grandes` para instalaciones por plugin: las rutas de los scripts ya no dependen de `~/.claude/skills/`, el instalador encuentra `uv` aunque la app no vea `~/.local/bin` (y si falta dice «corré Poner todo al día»), y todo se instala verificado por hash (`requisitos.txt`).

## 0.2.3 — 2026-10-08
- Skill nueva `achicar-datos-grandes`: cuando una consulta devuelve miles de filas (Ads, tienda, ERP/CRM, logs), las recodifica sin perder ninguna para gastar menos tokens (40-67 % medido en listas de filas; 0 % en código y texto). Usa Headroom 0.40.0 en un entorno aparte, con telemetría apagada y sin conexión propia. La primera vez corre un instalador de un comando.


## 0.2.2 — 2026-10-07
- 5 skills al día con su autor (v2.11.18): `ads`, `ai-seo`, `launch`, `programmatic-seo` y `site-architecture` suman guías nuevas (plataformas para armar sitios, migraciones, revisión antes de lanzar un sitio, WebMCP). Solo texto.

## 0.2.1 — 2026-10-06
- Sincronizadas skills desde ~/.claude/skills.


## 0.2.0 — 2026-10-03
- **Nuevo agente `marketing-analyst`:** mide qué canal te trae clientes, cuánto te cuesta cada uno y dónde conviene poner la plata. Pedile a Claude «que marketing-analyst mire mis campañas».

## 0.1.1 — 2026-10-03
- requisitos.md real (qué necesita cada skill y qué pasa si falta).

## 0.1.0 — 2026-10-03
- Incorporación inicial de skills.
