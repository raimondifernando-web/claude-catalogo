---
name: informe-visita-de-obra
description: >
  Convertí tus notas, fotos o audio de una visita de obra en un informe estructurado y firmable.
  Separa lo que viste directamente, lo que te contaron, lo que interpretás, las limitaciones y los
  próximos pasos. Listo para el libro de obra o para mandarle al cliente.
  Disparadores: "informe de visita", "acta de obra", "estuve en obra", "visita de inspección",
  "qué encontré en obra", "resumen de visita", "informe de avance", "libro de obra".
version: "0.1.0"
origen: "adaptada de AlpacaLabsLLC/skills-for-architects → site-visit-report (MIT), 2026-09-21"
sync: si
user-invocable: true
---

# informe-visita-de-obra

Generás un informe de visita de obra estructurado a partir de lo que tengas: notas en texto,
descripciones de fotos, audio transcripto, o un listado desordenado de observaciones.

**No necesitás ninguna herramienta instalada.** Pegá tus notas directamente en el chat.

---

## Cómo usar esta skill

1. Describí la obra y la visita (fecha, dirección, quiénes estaban, para qué fuiste).
2. Pegá tus notas, fotos (descripción o nombre de archivo), o el audio transcripto.
3. La skill arma el informe y te lo muestra antes de finalizar.
4. Si algo no cierra o falta información, te pregunta; si es un dato menor, lo marca como "a confirmar".

**Regla de la casa:** antes de dar el informe por terminado, lo ves completo y confirmás.

---

## Qué separa el informe

| Sección | Qué va ahí |
|---|---|
| **Observaciones directas** | Lo que viste o percibiste vos en persona |
| **Información de terceros** | Lo que te contaron los presentes (propietario, capataz, contratista) |
| **Interpretaciones** | Inferencias tuyas, siempre con base en lo observado |
| **Limitaciones** | Zonas sin acceso, trabajos cubiertos, falta de documentación |
| **Próximos pasos** | Acciones concretas derivadas de la visita |

---

## Datos que necesito para armar el informe

Si no los incluiste en tus notas, te pregunto:

- **Fecha de la visita**
- **Obra / proyecto** (nombre, dirección o referencia)
- **Presentes** (nombres y roles; si no sabés, poné "no registrado")
- **Propósito de la visita** (inspección de avance, reunión con contratista, relevamiento, etc.)
- **Condiciones** (clima si aplica, si había trabajo activo, acceso a todas las áreas o no)

---

## Estructura del informe generado

Usá la plantilla en `assets/plantilla-informe-visita.md`.

```
# Informe de visita de obra — [Obra]

**Fecha de visita:** AAAA-MM-DD
**Creado:** AAAA-MM-DD
**Revisión:** Sin revisiones | AAAA-MM-DD — [qué cambió]
**Obra / ubicación:** [Nombre y dirección]
**Propósito:** [Por qué se hizo la visita]
**Condiciones:** [Clima, actividad en obra, acceso]
**Elaborado por:** [Profesional responsable]
**Presentes:** [Nombre — rol]

---

## Observaciones directas

### O1 — [Etiqueta corta]
- **Ubicación:** [Sector o área]
- **Observación:** [Descripción objetiva]
- **Fuente:** [Nota propia / foto adjunta / etc.]

## Información de terceros

### R1 — [Etiqueta corta]
- **Manifestó:** [Qué dijo]
- **Quién:** [Nombre o rol]
- **Estado:** Información reportada; no verificada de forma independiente

## Interpretaciones

### I1 — [Etiqueta corta]
- **Interpretación:** [Inferencia acotada]
- **Base:** [O# que la sostienen]
- **Estado:** Interpretación; requiere verificación; no es un dictamen de cumplimiento

## Limitaciones de acceso y visibilidad

- [Área sin acceso / trabajos cubiertos / falta de documentación / equipamiento]
- Usar "No observado"; nunca "Sin problemas observados" cuando no se pudo verificar

## Problemas para revisar

### P1 — [Etiqueta corta]
- **Descripción:** [Qué requiere seguimiento]
- **Prioridad:** Alta / Media / Baja
- **Acción propuesta:** [Qué hacer]

## Próximos pasos

| # | Acción | Responsable | Para cuándo |
|---|---|---|---|
| 1 | | | |
```

---

## Advertencia profesional

Este informe es un registro de visita para uso interno del estudio y comunicación con el cliente.
**No certifica cumplimiento normativo, estructural, de seguridad ni contractual.**
La verificación final corresponde al profesional responsable de obra y a los organismos de aprobación.

---

## Lo que esta skill NO hace

- No inventa contenido de fotos a partir de nombres de archivo; si no describís la foto, la deja en blanco.
- No certifica código ni normativa de ningún tipo.
- No modifica datos de obra (fechas, materiales, medidas) si no los aportás vos.
- No reemplaza el libro de obra oficial ni las actas legales.
