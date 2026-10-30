# rubro-marketing

## 0.4.0 — 2026-10-30
**18 agentes nuevos para vender y comunicar:** `pm-empresa` (jefe general de pyme), `pm-marketing-pyme`, `pm-ventas`, `estratega-de-negocio`, `estratega-de-contenido`, `especialista-cro`, `social-media-manager`, `guardian-de-marca`, `comunicaciones-y-prensa`, `creativo-de-anuncios`, `auditor-de-tracking`, `ecommerce-manager-ar`, `coach-de-discovery`, `redactor-de-propuestas`, `analista-de-pipeline`, `ejecutivo-de-cuentas`, `vendedor-whatsapp-b2b` y `soporte-al-cliente`. Cada uno cita sus fuentes y marca lo que no pudo verificar. Se aplican solos con la actualización.

## 0.3.0 — 2026-10-29
**4 agentes nuevos para vender y retener:** `especialista-seo`, `especialista-paid-media` (propone, no ejecuta cambios sin tu OK), `prospector-outbound` (clientes nuevos con motivo real, sin spam) y `customer-success` (salud de cuentas y prevención de bajas). Cada uno marca lo que no pudo verificar y cita sus fuentes. Se aplican solos con la actualización.

## 0.2.8 — 2026-10-22
**Dos skills nuevas para mails:** `email-html-mjml` (mails en HTML que se ven bien en Gmail y Outlook, armados con MJML) y `ecommerce-email-marketing-builder` (secuencias de mails para tiendas online: bienvenida, carrito abandonado, recompra). Se aplican solas con la actualización.


## 0.2.7 — 2026-10-18
- Sincronizadas skills desde ~/.claude/skills.


## 0.2.6 — 2026-10-11
- `claude-ecom`: ya no tiene la terminal aprobada de antemano (pregunta si la necesita; la skill solo lee y escribe archivos).

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
