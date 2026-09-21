---
name: propuesta-de-honorarios
description: >
  Redactá una propuesta de servicios profesionales para un proyecto de arquitectura: alcance por
  etapa, entregables, plazos, honorarios y condiciones. Sin cifras inventadas; cuando el usuario
  no define el monto, la skill muestra las alternativas de cálculo y deja el número en blanco.
  Registra versiones para no perder lo que ya se acordó.
  Disparadores: "propuesta de honorarios", "presupuesto de honorarios", "propuesta de servicios",
  "cómo cobro", "qué incluyo en la propuesta", "contrato de servicios", "carta propuesta",
  "propuesta para el cliente", "etapas y honorarios".
version: "0.1.0"
origen: "adaptada de AlpacaLabsLLC/skills-for-architects → proposal (MIT), 2026-09-21"
sync: si
user-invocable: true
---

# propuesta-de-honorarios

Redactás una propuesta de servicios profesionales lista para enviar al cliente, o un borrador
para revisar internamente. La skill estructura el alcance por etapas, los entregables, los
honorarios y las condiciones de contratación.

**No inventa cifras.** Si no definiste los honorarios, te muestra las alternativas de cálculo
y deja el número en blanco con la marca `[A CONFIRMAR]`.

---

## Cómo usar esta skill

1. Describí el proyecto: tipo de obra, superficie, ubicación, etapas que querés incluir.
2. Si ya tenés el honorario o cómo lo querés calcular, decíselo.
3. La skill arma el borrador y te lo muestra antes de darlo por terminado.
4. Podés pedirle que genere una nueva versión (Rev. 02, Rev. 03) sin perder las anteriores.

**Regla de la casa:** antes de dar la propuesta por terminada o mandarla al cliente, la revisás y confirmás.

---

## Etapas habituales de servicios

| Etapa | Descripción habitual |
|---|---|
| Anteproyecto | Programa, partido, plantas y vistas esquemáticas, informe de factibilidad |
| Proyecto ejecutivo | Planos de arquitectura, estructura e instalaciones para obra; planillas, detalles |
| Documentación para trámites | Planos municipales, visados, gestiones ante colegios y organismos |
| Dirección de obra | Seguimiento periódico, órdenes de servicio, certificaciones |
| Dirección ejecutiva | Seguimiento continuo, coordinación de subcontratistas |
| Asesoramiento / consultoría | Visitas puntuales, informes, revisión de proyectos de terceros |

Si el proyecto tiene etapas distintas, la skill las adapta.

---

## Alternativas de cálculo de honorarios

La skill no afirma cifras de mercado. Sí muestra las alternativas:

- **Porcentaje del presupuesto de obra:** X% sobre el presupuesto final de la obra (completá el % según tu criterio y las tablas orientativas del colegio de tu provincia).
- **Por m² construido:** $_______ / m² (según tipo de obra y complejidad).
- **Por etapa cerrada:** monto fijo por etapa acordada entre las partes.
- **Por hora:** $_______ / hora de trabajo profesional.

> Los colegios profesionales de cada provincia publican tablas orientativas de honorarios mínimos
> sugeridos. Consultá el de tu jurisdicción antes de fijar el valor. Esta skill no cita cifras
> porque varían por provincia, tipo de obra y actualización periódica.

---

## Estructura de la propuesta generada

Usá la plantilla en `assets/plantilla-propuesta.md`.

```
# Propuesta de servicios profesionales
## [Título del proyecto]

**Fecha:** AAAA-MM-DD
**Versión:** Rev. 01
**Para:** [Nombre del cliente]
**De:** [Estudio / Profesional]
**Válida hasta:** [Fecha o "30 días desde la fecha"]

---

### Descripción del proyecto
[Tipo de obra, ubicación, superficie aproximada, descripción]

---

### Alcance de servicios

#### Etapa 1 — [Nombre]
- **Entregables:** [Lista de lo que se entrega]
- **Plazo estimado:** [Semanas / meses desde el inicio]
- **Honorarios:** [Monto · % · m² · o [A CONFIRMAR]]

#### Etapa 2 — [Nombre]
[...]

---

### Condiciones de contratación

**Honorarios totales:** [Suma de etapas o [A CONFIRMAR]]
**Forma de pago:** [Cuotas por avance de etapas / % al inicio / a convenir]
**Ajuste:** [Cómo se actualiza si cambia el presupuesto de obra o el plazo]
**Qué no incluye esta propuesta:**
- Trámites, tasas y sellados ante organismos públicos
- Honorarios de calculistas, especialistas o consultores externos
- Copias, impresiones y gastos de envío
- [Otros]
**Vigencia:** Esta propuesta es válida por [30 días] desde su fecha.

---

### Aceptación

| | Nombre | Firma | Fecha |
|---|---|---|---|
| Comitente | | | |
| Profesional | | | |

---
*Versión Rev. 01 — [fecha]. Versiones anteriores: ninguna.*
```

---

## Control de versiones

Cuando emitís una nueva versión:
- Se agrega la línea "Versiones anteriores: Rev. XX — [fecha] — [motivo del cambio]" al pie.
- El contenido anterior queda registrado; no se sobreescribe.

---

## Advertencia

Esta propuesta es un instrumento de negociación y contratación entre privados.
**No es asesoramiento legal ni financiero.** Antes de firmarla, consultá con un abogado si
el encargo involucra montos significativos, obra pública, o condiciones no habituales.
Los honorarios que figuren en esta propuesta son los acordados entre las partes;
esta skill no certifica que sean los mínimos arancelarios ni que cumplan ninguna exigencia colegial.

---

## Lo que esta skill NO hace

- No inventa cifras de honorarios ni de obra.
- No afirma qué porcentaje cobra el mercado ni cuál es el mínimo del colegio.
- No envía la propuesta ni la sube a ninguna plataforma.
- No reemplaza un contrato de locación de obra o de servicios.
