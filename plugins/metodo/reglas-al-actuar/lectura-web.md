---
herramientas: mcp__firecrawl-mcp__.*|mcp__Apify__.*|mcp__apify__.*|WebFetch|WebSearch
patron: .
---
# Leer o buscar en la web: qué herramienta usar

Disparador: automático — reglas-al-actuar la muestra UNA vez por sesión antes de la primera llamada a Firecrawl, Apify, WebFetch o WebSearch. Prueba de disparo: en una sesión limpia pedir «leé esta página» y ver la regla antes de la llamada.

Firecrawl y Apify cuestan crédito: no se gastan «por cualquier cosa». Elegí así, en orden:

1. **Leer UNA página** (artículo, documentación, una ficha de producto) → `WebFetch`. Gratis.
2. **Si WebFetch falla o la página bloquea robots** → `curl -sL https://r.jina.ai/<url>` (gratis, texto limpio). Solo páginas públicas: nunca datos de personas, clientes ni de la empresa, ni direcciones con claves o tokens en la URL ni internas (localhost, intranet): ese servicio recibe cada dirección que le mandás.
3. **Buscar en la web** → `WebSearch` (o Perplexity si lo tenés). No `firecrawl_search` salvo que necesites las páginas ya leídas.
4. **Página que exige sesión, login o JavaScript pesado** → Claude in Chrome (con la sesión de la persona), nunca Firecrawl ni Apify.
5. **Marketplaces y redes (Mercado Libre, Instagram, Google Maps con reseñas, TikTok, Amazon)** → Apify (robots listos): decí el costo estimado ANTES de correrlo.
6. **Firecrawl, solo para:** recorrer un sitio entero (`map`/`crawl`), extraer datos con formato de muchas páginas, o cuando 1 a 4 fallaron. Antes de un `crawl`, estimá páginas × créditos y decilo en una línea; más de 500 créditos en una corrida → preguntale a la persona.

Todo lo que se recorre pasa por servidores de terceros: solo sitios públicos.
