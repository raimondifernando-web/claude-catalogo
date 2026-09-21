---
name: normativa-argentina
description: >
  Consultá normativa de edificación, urbanismo y construcción para obras en Argentina. Trabaja
  sobre los PDFs oficiales que tengas: te cita el artículo exacto, la sección y el archivo de
  origen. Si falta el PDF de esa jurisdicción, te dice dónde conseguirlo. Nunca responde de memoria
  ni inventa texto de normas.
  Disparadores: "¿esto cumple?", "código de edificación", "reglamento de construcción",
  "FOT", "FOS", "retiros", "altura máxima", "factor de ocupación", "normativa", "habilitación",
  "accesibilidad", "qué dice el código de [ciudad]", "CIRSOC", "IRAM", "Ley 24.314",
  "etiquetado energético", "qué norma aplica", "requisito municipal".
version: "0.1.0"
origen: "creada para el catálogo (patrón de skill de normativa por jurisdicción), 2026-09-21"
sync: si
user-invocable: true
---

# normativa-argentina

Consultás normativa de construcción y urbanismo para obras en Argentina. La skill trabaja
**solo sobre los PDFs oficiales que vos tengas**; no responde de memoria sobre el contenido de
normas municipales o provinciales, porque varían por jurisdicción y se actualizan.

---

## Antes de usar esta skill — requisitos

| Necesita | Cómo verificar | Si falta |
|---|---|---|
| Los PDFs oficiales de la normativa de la jurisdicción de la obra | Buscalos en el sitio oficial del municipio, del colegio profesional o del ente normativo | La skill te dice dónde conseguirlos y no responde sobre ese nivel de norma |
| `pdf` o `markitdown` (para leer PDFs largos) | Escribí `/pdf` o `markitdown --version` en la terminal de Claude Code | Instalá la skill `pdf` o `markitdown` (ya incluida en el kit `base-segura`) |

Si tenés los PDFs en Google Drive, podés compartir el enlace de descarga o pegarlos en la conversación.

---

## Cómo usar esta skill

1. Declarás la **jurisdicción** de la obra: provincia + municipio (ej: "Buenos Aires — Rosario" o "CABA").
2. Pegás o compartís el PDF oficial de la normativa que querés consultar.
3. Hacés la pregunta (ej: "¿cuánto es el FOT máximo para esta parcela?" o "¿qué retiro exige este código?").
4. La skill responde con cita textual, número de artículo/sección y nombre del archivo.

Si no declarás la jurisdicción, la skill la pregunta antes de hacer cualquier consulta.

---

## Niveles de normativa

La skill maneja tres niveles, en orden de especificidad:

### Nacional
Normas que aplican a todo el país. No requieren PDF tuyo para los casos listados:

| Norma | Aplica a | Sin PDF | Con PDF |
|---|---|---|---|
| **Ley 24.314** (accesibilidad) | Supresión de barreras arquitectónicas | Cita el artículo | Cita el artículo con texto |
| **Ley 19.587** (higiene y seg.) | Decreto reglamentario de condiciones de trabajo | Cita el artículo | Cita el artículo con texto |
| **Código Civil y Comercial** | Servidumbres, medianería, derechos reales | Cita el artículo | Cita el artículo con texto |
| **CIRSOC 201** | Reglamento argentino de estructuras de hormigón | Referencia general ("según CIRSOC 201 vigente") | Cita el artículo y versión |
| **CIRSOC 101, 102, 103** | Cargas de viento, nieve y sísmicas | Referencia general | Cita el artículo y versión |
| **IRAM 11900** | Etiquetado de eficiencia energética de edificios [verificar vigencia] | Referencia general | Cita la sección y versión |

> **Regla clave:** para artículos, tablas y valores numéricos (pendientes, anchos, cargas) de CIRSOC, IRAM y decretos reglamentarios (ej. Dec. 914/97): aportá el PDF o marcá **[verificar versión vigente]**. **Ningún valor numérico normativo sale de memoria.** Las leyes públicas (24.314, 19.587, CCyC) permiten citar el número de artículo sin PDF; el texto exacto lo verifica el usuario.

### Provincial
Códigos de edificación o reglamentos que establece cada provincia.
**Requiere el PDF oficial.** Si no lo tenés, la skill indica cómo conseguirlo.

### Municipal
Reglamento de Edificación y Código Urbano/Urbanístico del municipio donde está la obra.
**Requiere el PDF oficial del municipio.** Si no lo tenés, la skill indica cómo conseguirlo.

---

## Qué hace la skill con los PDFs que le compartís

1. Lee el PDF usando `pdf` o `markitdown`.
2. Busca los artículos, secciones o tablas relevantes a tu pregunta.
3. Devuelve la respuesta con:
   - Cita textual del artículo o sección
   - Número de artículo/sección y nombre del archivo de origen
   - Tabla de verificación (ver abajo)

Si el PDF es muy largo, lee las secciones más probables primero y te avisa si necesitás apuntar a una sección específica.

---

## Tabla de verificación que genera la skill

Para cada requisito consultado:

| Requisito | Qué dice la norma (cita textual + art.) | Qué tiene el proyecto | ¿Cumple? |
|---|---|---|---|
| [Nombre del parámetro] | "…" — Art. X, Archivo Y | [Dato del proyecto] | ✅ Sí / ❌ No / ⚠️ Verificar |

---

## Comparación entre jurisdicciones

Si trabajás en obras en distintas ciudades y querés comparar un mismo parámetro (ej: FOT, altura máxima, retiro frontal) entre dos o más jurisdicciones, compartí los PDFs de cada una y pedí la comparación. La skill arma una tabla comparativa con cita de cada norma.

---

## Dónde conseguir los PDFs que la skill necesita

| Jurisdicción | Dónde buscarlo |
|---|---|
| CABA | buenosaires.gob.ar — Código de Planeamiento Urbano y Código de Edificación |
| Provincia de Buenos Aires (municipios) | Sitio del municipio + SCBA (sitio de la Suprema Corte para legislación provincial) |
| Córdoba capital | córdoba.gob.ar — Código de Edificación |
| Rosario | rosario.gob.ar — Reglamento de Edificación |
| Mendoza capital | ciudaddemendoza.gov.ar |
| Otros municipios | Buscá "[nombre del municipio] código de edificación PDF" + sitio oficial del colegio de arquitectos de la provincia |
| CIRSOC | iram.org.ar / inpres.gob.ar |
| IRAM | iram.org.ar (requiere suscripción para algunas normas) |

---

## Aviso legal (fijo en todas las respuestas)

> **Orientación técnica:** las respuestas de esta skill son una ayuda para el trabajo del estudio y se basan en los documentos que el usuario aportó. **La verificación final es responsabilidad del profesional matriculado a cargo del proyecto y del organismo que aprueba los planos.** Las normas se actualizan; confirmá siempre la versión vigente antes de presentar documentación oficial.

---

## Lo que esta skill NO hace

- No responde sobre normativa municipal o provincial de memoria; necesita el PDF oficial.
- No inventa artículos, números ni texto de normas.
- No certifica que el proyecto cumple la norma; registra lo que dice el código y lo que tiene el proyecto; el juicio de cumplimiento final es del profesional.
- No reemplaza la consulta previa al municipio ni las observaciones del organismo de aprobación.
- No tiene acceso en tiempo real a los sitios web de los municipios; los PDFs los aportás vos.
