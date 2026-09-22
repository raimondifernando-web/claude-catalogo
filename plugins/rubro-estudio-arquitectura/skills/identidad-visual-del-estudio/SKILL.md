---
name: identidad-visual-del-estudio
description: "Aplicá la identidad visual DEL ESTUDIO (colores, tipografías, logo, tono) a cualquier pieza que Claude produzca: presentaciones, páginas, informes, fichas, imágenes, posteos. La identidad se guarda una vez en `identidad-visual.md` de la carpeta de trabajo y se reutiliza siempre. Usala cuando el usuario diga 'con la marca del estudio', 'nuestros colores', 'que se vea como nosotros', 'aplicá la identidad', 'poné el logo', 'con nuestra tipografía', o cuando pida una pieza para un cliente o para redes. Reemplaza a `brand-guidelines` (que aplica la marca de Anthropic, no la del usuario)."
version: "0.1.0"
origen: "propia (Consultoría IA, 2026-09-21). Reemplaza a brand-guidelines del catálogo, que aplicaba la marca de Anthropic."
sync: si
---

# identidad-visual-del-estudio — que todo se vea como el estudio, no como Claude

Una pieza que sale del estudio (propuesta, presentación, informe, posteo) tiene que verse **del estudio**: sus colores,
sus tipografías, su logo, su forma de hablar. Esta skill guarda esa identidad una vez y la aplica siempre, sin que
el usuario tenga que repetirla en cada pedido.

## Antes de usar esta skill — requisitos
| Necesita | Cómo verificar | Si falta, respondé |
|---|---|---|
| El archivo `identidad-visual.md` en la carpeta de trabajo | `ls identidad-visual.md` | «Todavía no tengo la identidad del estudio guardada. Te hago 6 preguntas y la dejo en `identidad-visual.md`» (ver paso 1) |
| El logo (opcional) | `ls assets/logo*` o la ruta que diga el archivo | Trabajá sin logo y anotá «logo: pendiente» |

Nada más. No pide claves ni cuentas. Nada sale de la computadora.

## Paso 1 — Si no existe `identidad-visual.md`: crearlo (una sola vez)
Preguntá **de a una**, en este orden, y aceptá «no sé» (anotá «a definir»):
1. **Colores**: el principal, uno o dos secundarios, y el de fondo. Si el usuario no sabe el código, pedile una foto o
   un PDF donde estén (tarjeta, web, presentación anterior) y sacalos de ahí; si no hay nada, proponé una paleta sobria
   de 3 colores y marcala «propuesta».
2. **Tipografías**: títulos y texto. Si no sabe, mirá un documento del estudio; si no hay, proponé un par (una para
   títulos, una para texto) que exista en Mac y en Google Docs, y marcalo «propuesta».
3. **Logo**: dónde está el archivo (SVG o PNG con fondo transparente, ideal). Si no hay, «pendiente».
4. **Tono**: cómo le habla el estudio a un cliente (cercano / formal / técnico) y 2-3 palabras que los definen.
5. **Qué NO**: colores, efectos o estilos que el estudio no usa nunca (ej. degradados, sombras, mayúsculas sostenidas).
6. **Firma**: nombre completo del estudio, ciudad, web, mail y teléfono como van en las piezas.

Escribí `identidad-visual.md` con la plantilla de `assets/identidad-visual.md` y mostrásela. **Antes de guardar,
confirmá** (regla 3 de la casa). Sugerí guardarla en el repositorio con el resto del trabajo.

## Paso 2 — Aplicar la identidad a una pieza
1. Leé `identidad-visual.md` completo. Los valores salen **de ahí**, nunca de memoria ni de otra marca.
2. Aplicá según el tipo de pieza:
   - **Documento / informe / propuesta** (Word, PDF, Markdown): título con la tipografía de títulos y el color
     principal; texto con la tipografía de texto; logo arriba a la izquierda o en la portada; firma al final.
   - **Presentación**: fondo del color de fondo; títulos en color principal; un solo color de acento por lámina; logo
     chico en la misma esquina en todas las láminas.
   - **Página web / Artifact / HTML**: definí los colores como variables (`--principal`, `--secundario`, `--fondo`,
     `--texto`) y las tipografías una sola vez arriba; el resto las usa. Si la tipografía no es gratuita ni está en
     Google Fonts, usá la alternativa que diga el archivo.
   - **Imagen / render / posteo**: pasale al generador de imágenes o a `social-content` los colores en palabras y en
     código, el tono, y «sin texto» si el logo va aparte.
3. Respetá la sección **Qué NO** como prohibiciones, no como sugerencias.
4. Si la pieza es para un **cliente del estudio** con su propia marca (ej. un informe para una empresa), la identidad
   del estudio va en firma y portada; el contenido del cliente no se «pinta» con los colores del estudio salvo pedido.

## Paso 3 — Cerrar
- Decí qué aplicaste (colores, tipografías, logo, firma) y qué quedó «a definir» o «propuesta».
- Si el usuario cambió algo durante el trabajo («el azul más oscuro»), preguntá si lo guardás en
  `identidad-visual.md` para la próxima. Confirmación antes de escribir.

## Qué NO hace
- No inventa una marca nueva sin decirlo: lo propuesto va marcado «propuesta».
- No aplica la marca de Anthropic, de Claude ni de ninguna otra empresa.
- No sube el logo ni la identidad a ningún servicio externo.
