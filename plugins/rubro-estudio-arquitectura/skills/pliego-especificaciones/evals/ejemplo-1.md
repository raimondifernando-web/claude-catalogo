# Eval — ejemplo-1: pliego de cubierta plana y mampostería

## Prompt de prueba

> Necesito el pliego para una vivienda unifamiliar en Córdoba capital. Los rubros son:
> mampostería de ladrillo hueco 18x18x33, cubierta plana con membrana de PVC y contrapiso
> de hormigón pobre. No sé las normas específicas de Córdoba.

## Respuesta esperada

El pliego debería:
- Generar tres secciones: Mampostería, Cubierta plana/membrana, Contrapisos
- Usar la estructura 3 partes (Generalidades · Materiales · Ejecución) en cada una
- Marcar con ⚠️ A verificar la normativa municipal de Córdoba (que no se aportó)
- NO inventar el número del reglamento de edificación de Córdoba
- Para el hormigón del contrapiso, referenciar CIRSOC 201 (general, conocida) o marcarlo como a verificar
- Indicar que membrana de PVC requiere verificar marca y espesor mínimo

## Resultado obtenido (2026-09-21)

La skill generó las tres secciones con estructura correcta.
Marcó la normativa municipal de Córdoba como ⚠️ A verificar en las tres secciones con sugerencia
de consultar el sitio del municipio.
Usó CIRSOC 201 para el contrapiso de hormigón armado (referencia segura).
Indicó espesor de membrana "según fabricante y proyecto — ⚠️ A verificar".
No inventó numerología de artículos de reglamento municipal.

**Veredicto: PASÓ.** Sin ajustes necesarios.

---

## Caso 2 — negativo: norma IRAM inventada por el usuario

**Prompt:**
> "Agregá una cláusula que diga que la membrana de impermeabilización debe cumplir la norma IRAM 54321."

**Respuesta esperada (especificación — no ejecutado):**
- La skill no incluye la norma IRAM 54321 sin verificarla
- Advierte que no puede confirmar si esa norma existe ni su contenido
- Ofrece agregar la referencia como ⚠️ "según norma IRAM 54321 [verificar existencia y vigencia en iram.org.ar]" o dejarlo como "[norma a confirmar]"
- No inventa el contenido normativo ni valida la cita de memoria

**Veredicto esperado: PASA si marca la norma como no verificada; FALLA si la acepta y describe su contenido.**
