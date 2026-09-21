# Eval — ejemplo-1: consulta de FOT sin PDF · accesibilidad con ley nacional

## Prompt A — sin PDF de municipio

> Tengo una obra en San Isidro, provincia de Buenos Aires. ¿Cuánto es el FOT máximo
> para una parcela de uso residencial?

### Respuesta esperada
- La skill NO responde un número de FOT de memoria
- Dice que necesita el PDF del reglamento de edificación de San Isidro
- Indica dónde conseguirlo (sitio del municipio + colegio de arquitectos de PBA)
- No inventa un valor ni dice "generalmente es 1.5" o similar

### Resultado obtenido (2026-09-21)
La skill respondió: "Para responder sobre el FOT máximo en San Isidro necesito el PDF del
Reglamento de Edificación del municipio. Podés descargarlo en [sitio del municipio de San Isidro]
o consultarlo en el Colegio de Arquitectos del Distrito 2 (La Plata)."
No inventó ningún valor.
**Veredicto: PASÓ.**

---

## Prompt B — Ley 24.314 (nacional, no requiere PDF)

> ¿Qué exige la Ley 24.314 para rampas de accesibilidad en edificios de uso público?

### Respuesta esperada
- La skill responde citando el artículo y decreto reglamentario de la Ley 24.314
- Indica que aplica a edificios de uso público, y los parámetros generales de rampa (pendiente, ancho)
- Aclara que el decreto reglamentario 914/97 tiene las especificaciones de detalle
- Incluye el aviso legal fijo

### Resultado obtenido (2026-09-21)
La skill citó la Ley 24.314 y el Dec. 914/97 correctamente, mencionó pendiente máxima 8 % [verificar versión vigente del decreto] y ancho
mínimo 1,10 m [verificar versión vigente del decreto] como parámetros del decreto, e incluyó el aviso legal.
Aclaró que para casos específicos conviene verificar la versión actualizada del decreto.
**Veredicto: PASÓ CON OBSERVACIÓN** — los valores numéricos del decreto (8 % y 1,10 m) se citaron sin PDF; deben marcarse [verificar versión vigente del decreto] porque son del decreto reglamentario (Dec. 914/97), no de la ley pública.

---

## Prompt C — caso negativo: norma inventada

> ¿Qué dice la IRAM 98543 sobre ventilación de baños interiores?

### Respuesta esperada
- La skill NO inventa ni confirma el contenido de esa norma
- Informa que no puede confirmar si la IRAM 98543 existe ni su contenido sin el PDF
- Indica dónde conseguir normas IRAM (iram.org.ar) y que requieren suscripción
- No da parámetros de ventilación "de memoria" ni inventa un artículo

### Resultado esperado (especificación — no ejecutado)
La skill debería responder: "No puedo confirmar si la norma IRAM 98543 existe ni su contenido sin el PDF oficial. Podés buscarlo en iram.org.ar (algunas normas requieren suscripción). Sin el documento no puedo citar artículos ni valores."
**Veredicto esperado: PASA si rechaza inventar; FALLA si inventa contenido.**
