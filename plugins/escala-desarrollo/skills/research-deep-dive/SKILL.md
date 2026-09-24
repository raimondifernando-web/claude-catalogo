---
name: "research-deep-dive"
description: "When the user wants an exhaustive investigation on a topic, market, territory, technology, competitor, or opportunity. Use when the user says 'investigación profunda', 'research exhaustivo', 'analizar X a fondo', 'quiero entender [tema] en detalle', 'dame todo sobre', 'investigá en profundidad', or 'necesito saber todo sobre'. This is a multi-agent chain: research-analyst searches and synthesizes → data-researcher validates with primary sources and hard data → knowledge-synthesizer consolidates into an actionable report. NOT for quick lookups or single-source queries (use research-analyst directly for those)."
license: MIT
metadata:
  version: 1.0.0
  category: research
origen: adaptado por Consultoría 2026-09-22 · publicado por Orquesta 2026-09-23 junto con sus 3 agentes (research-analyst, data-researcher, knowledge-synthesizer)
---

# Research Deep Dive — Skill Chain

Sos el orquestador de una cadena de investigación multi-agente de 3 etapas. Tu rol es coordinar a los agentes en secuencia, pasando el output de cada uno como input al siguiente, y entregar un informe final consolidado.

## Cuándo usar esta skill chain

Actívala cuando el usuario pida una investigación profunda, exhaustiva o con datos verificados sobre cualquier tema. Keywords: "investigación profunda", "research exhaustivo", "analizar X a fondo", "quiero entender [tema] en detalle".

## Chain de ejecución

### Etapa 1 — research-analyst
**Objetivo:** Búsqueda multi-fuente + síntesis preliminar

Invocar al agente `research-analyst` con el tema completo del usuario. El agente debe:
- Buscar en múltiples fuentes (web, papers, informes de industria)
- Identificar los ángulos principales del tema
- Producir una síntesis preliminar con los hallazgos más relevantes
- Listar preguntas abiertas y gaps de información detectados

### Etapa 2 — data-researcher
**Objetivo:** Validación con fuentes primarias y datos concretos

Invocar al agente `data-researcher` con el output de Etapa 1. El agente debe:
- Validar los hallazgos con fuentes primarias (papers, estudios, datos oficiales)
- Agregar métricas concretas, números y estadísticas verificables
- Identificar contradicciones o información desactualizada en la síntesis previa
- Profundizar en los gaps detectados en Etapa 1

### Etapa 3 — knowledge-synthesizer
**Objetivo:** Informe final accionable

Invocar al agente `knowledge-synthesizer` con los outputs de Etapas 1 y 2. El agente debe:
- Consolidar todos los hallazgos en un informe estructurado
- Extraer patrones, tendencias e insights accionables
- Priorizar la información por relevancia e impacto
- Producir recomendaciones concretas basadas en la evidencia

## Output esperado

Informe estructurado con:
- Resumen ejecutivo (3-5 bullets)
- Hallazgos principales con fuentes
- Datos y métricas clave
- Insights accionables priorizados
- Gaps de información restantes (si los hay)

## Notas operativas

- Si el usuario no especificó el objetivo del research, preguntá antes de arrancar: ¿para qué decisión o proyecto necesitás este research?
- Cada etapa puede tomar tiempo — informale al usuario el progreso entre etapas
- Requiere los 3 agentes (`research-analyst`, `data-researcher`, `knowledge-synthesizer`) incluidos en este plugin.
