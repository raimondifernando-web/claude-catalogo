# Pedido — Radar de modelos, fase 1: investigación de fuentes (para la sesión en la nube)

Contexto: hoy cada sesión decide a mano qué IA usar (Claude, Codex de OpenAI, Gemini/Antigravity de Google) y las reglas se desactualizan. Objetivo final: un solo archivo que diga qué IA usar para cada tipo de
tarea, actualizado solo. Esta fase SOLO investiga fuentes; no instala nada ni escribe código.

## Qué investigar (con búsqueda web; citá URL y fecha de cada dato)
1. **Fuentes de ranking**, para cada una: quién la hace, qué mide (preferencia humana, código, agentes, precio,
   velocidad, uso real), cada cuánto se actualiza, si tiene API o datos descargables (JSON/CSV) y con qué licencia,
   y señales de confianza (organización, antigüedad, metodología pública, críticas conocidas).
   Mínimo: LMArena (confirmar dominio oficial: ¿arena.ai o lmarena.ai?), Artificial Analysis, SWE-bench (y Verified),
   Terminal-bench, Aider polyglot, OpenRouter rankings, y cualquier otra seria que encuentres (ej. de agentes de
   larga duración, de visión, de transcripción).
2. **Fuentes oficiales de cambios de modelos:** páginas de modelos/deprecaciones/precios de Anthropic, OpenAI y
   Google (Gemini): URL exacta, si tienen feed/RSS o JSON, y cómo detectar que un modelo se retira
   (caso real de hoy: `gemini-2.5-pro` dejó de estar disponible para usuarios nuevos sin aviso en nuestras reglas).
3. **Topes de cuentas gratuitas/baratas** que usamos para delegar, y cómo consultarlos sin gastar:
   ChatGPT gratis/Plus con Codex CLI (ventana de 30 días), Gemini API gratis (límites por modelo y por día),
   Antigravity CLI. Fuente oficial de cada límite.
4. **Mapa tarea → mejor opción hoy** (octubre 2026), con fuente: programar, revisar código/seguridad, investigar en la
   web, escribir en castellano, leer documentos largos, imágenes, transcribir audio, tareas mecánicas baratas.

## Entregable
`docs/specs/INVESTIGACION-radar-de-modelos.md` en castellano rioplatense, sin jerga innecesaria:
- Tabla de fuentes (columnas: fuente · qué mide · actualización · API/datos · licencia · confianza 1-5 · por qué).
- Tabla tarea → recomendada → alternativa → fuente/fecha.
- 2-3 opciones de cómo actualizarlo solo (qué consultar, cada cuánto, sin gastar cupo de IA), con recomendación.
- Lo dudoso marcado «a verificar».
Commit y push a la rama `orquesta/radar-modelos` (NO a main; este repo es público: nada de datos personales ni de clientes). No toques otros archivos.
