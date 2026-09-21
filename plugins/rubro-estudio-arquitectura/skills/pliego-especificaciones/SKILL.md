---
name: pliego-especificaciones
description: >
  De una lista de materiales, rubros o productos a un pliego de especificaciones técnicas particulares.
  Estructura de tres partes (Generalidades · Materiales · Ejecución) por rubro, con marcas "a verificar"
  donde faltan datos o normas inciertas. Usa los rubros de un cómputo argentino, no CSI MasterFormat.
  Disparadores: "pliego de especificaciones", "especificaciones técnicas", "memoria descriptiva",
  "qué especificación pongo", "cómo especifico el material", "ET particulares", "ETP",
  "especificar la cubierta", "especificar la estructura", "especificar el piso".
version: "0.1.0"
origen: "adaptada de AlpacaLabsLLC/skills-for-architects → spec-writer (MIT), 2026-09-21"
sync: si
user-invocable: true
---

# pliego-especificaciones

A partir de una lista de materiales, productos o rubros, generás un pliego de especificaciones
técnicas particulares (ETP) con la estructura de tres partes por rubro y marcas explícitas donde
falta información o donde la norma requiere verificación.

**No necesitás ninguna herramienta instalada.** Pegá tu lista directamente en el chat.

---

## Cómo usar esta skill

1. Pegá tu lista de materiales, rubros o productos (puede ser desordenada).
2. Indicá el tipo de obra y su destino (vivienda, comercial, industrial, etc.) si lo sabés.
3. Si tenés una norma o marca específica que querés incluir, mencionala.
4. La skill redacta el pliego, te lo muestra y espera tu confirmación antes de darlo por terminado.

**Regla de la casa:** antes de dar el pliego por terminado, lo revisás y confirmás.

---

## Rubros del cómputo argentino que maneja esta skill

La skill usa los rubros habituales de un cómputo de obra en Argentina. Si tu lista usa otros
nombres, los mapea automáticamente:

| Grupo | Rubros habituales |
|---|---|
| Trabajos preliminares | Demoliciones, limpieza de terreno, obrador, cerco de obra |
| Movimiento de suelos | Excavación, relleno y compactación, perfilado |
| Estructura | Hormigón armado (HºAº), estructura metálica, premoldeados |
| Mampostería | Muros de ladrillo, bloque, cerámico |
| Aislaciones | Hidrófuga, térmica, acústica |
| Cubiertas | Cubierta plana, inclinada, membrana, chapa, teja |
| Revoques | Grueso, fino, impermeable, proyectado |
| Contrapisos | Contrapiso sobre terreno, sobre losa |
| Pisos y revestimientos | Cerámico, porcelanato, madera, hormigón alisado |
| Carpinterías | Aluminio, madera, metálica, herrajes, vidrios |
| Instalación sanitaria | Desagüe cloacal, pluvial, agua fría y caliente |
| Instalación eléctrica | Baja tensión, tableros, iluminación |
| Instalación de gas | Circuito de gas, artefactos |
| Termomecánica / HVAC | Climatización, ventilación mecánica |
| Pintura | Interior, exterior, antihumedad |
| Varios y terminaciones | Cielorrasos, muebles fijos, equipamiento |

---

## Estructura de cada sección

Cada rubro sigue la estructura de tres partes:

```
## [Número] — [Nombre del rubro]

### Parte 1: Generalidades

**Alcance:** [Qué trabajo incluye este rubro]
**Documentos relacionados:** [Planos, planillas, otros rubros del pliego]
**Normas aplicables:** [IRAM / CIRSOC / reglamento municipal — solo las que el usuario aportó
  o que son de conocimiento seguro; si hay duda, marcar ⚠️ A VERIFICAR]

### Parte 2: Materiales

| Componente | Especificación | Marca/modelo orientativo | Estado |
|---|---|---|---|
| [Material] | [Características técnicas] | [Marca o "a definir"] | ✅ Confirmado / ⚠️ A verificar |

### Parte 3: Ejecución

**Condiciones previas:** [Qué tiene que estar listo antes de empezar este rubro]
**Procedimiento:** [Pasos de ejecución; en viñetas si hay más de 3 pasos]
**Tolerancias:** [Planitud, niveles, espesores, etc.; si no se definieron: ⚠️ A verificar]
**Verificación y ensayos:** [Cómo se comprueba la correcta ejecución]
**Entrega:** [Condición de recepción del rubro terminado]
```

---

## Marcas que usa el pliego

- `✅ Confirmado` — dato verificado o aportado por el usuario
- `⚠️ A verificar` — falta datos, hay que confirmar con el fabricante, el calculista o la normativa
- `> [A DEFINIR]` — el usuario no eligió este elemento todavía

---

## Normas: política de la skill

Esta skill **no inventa normas ni números de artículo**. Solo referencia normativa cuando:
- El usuario la aportó explícitamente, o
- Es de aplicación general y conocida con certeza (ej. CIRSOC 201 para hormigón armado, IRAM 11900 para etiquetado energético, Ley 24.314 para accesibilidad).

Si la norma específica del municipio o provincia requiere verificación, lo marca con `⚠️ A verificar`
y sugiere dónde buscarla.

---

## Advertencia profesional

Este pliego es un borrador de trabajo para el estudio. **No es un pliego licitatorio ni certifica
cumplimiento normativo.** Antes de incluirlo en un llamado a licitación, un contrato o una presentación
ante un organismo, revisalo con el criterio profesional y las normas vigentes en la jurisdicción de la obra.

---

## Lo que esta skill NO hace

- No inventa normas ni números de artículo; si no las conoce con certeza, marca `⚠️ A verificar`.
- No usa la numeración CSI MasterFormat (esa es para el mercado anglosajón).
- No genera computos de cantidades ni presupuestos.
- No certifica que el material cumple la norma; registra lo que el usuario indicó.
