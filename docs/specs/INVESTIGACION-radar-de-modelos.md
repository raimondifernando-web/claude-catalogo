# Investigación — Radar de modelos, fase 1: fuentes

> Pedido: `docs/specs/PEDIDO-radar-de-modelos.md`. Consultado el **2026-10-03**. Solo investigación: no se instaló
> nada ni se escribió código.

## En cinco líneas
1. Hay **fuentes abiertas y gratis** para armar el radar sin gastar cupo de IA. Las mejores son el dataset de Arena
   (CC-BY-4.0), los CSV de Epoch AI (CC-BY) y la lista de precios y retiros de LiteLLM (MIT, verificada a mano).
2. **Ningún proveedor tiene un RSS de retiros.** OpenAI es el único que expone la fecha de apagado en su API
   (`shutdown_date`). Anthropic y Google la publican solo en una tabla de su documentación.
3. **El caso `gemini-2.5-pro` no lo detecta ninguna lista.** Google lo bloqueó para usuarios nuevos sin retirarlo, y
   el modelo sigue figurando como vigente. Solo se ve probándolo con la cuenta propia.
4. Hoy (octubre de 2026), en general: **Claude Opus 5.5** para programar, revisar y escribir; **Codex (GPT-6.1 Sol)**
   para la segunda revisión y la investigación web; **Gemini 3.8 Flash** para documentos enormes y volumen barato.
5. Recomendación para actualizarlo solo: una **tarea programada en GitHub** que lea las fuentes abiertas una vez por
   semana y **proponga** los cambios en un PR. Una persona los aprueba.

## Cómo se hizo y cuánto confiar
- Búsqueda web en cuatro frentes, en paralelo. **El proxy de este entorno bloqueó la lectura directa** de casi todas
  las páginas oficiales y de los rankings: arena.ai, artificialanalysis.ai, swebench.com, tbench.ai, openai.com,
  developers.openai.com, ai.google.dev, antigravity.google, openrouter.ai, models.dev y huggingface.co (descargas).
- **Leído directo:**
  - Documentación de Anthropic (modelos, retiros y precios).
  - Spec OpenAPI oficial de OpenAI en GitHub.
  - Discovery doc de la API de Gemini.
  - JSON de LiteLLM: lo bajé y comprobé los precios y las fechas de retiro que se citan abajo.
  - Ficha del dataset de Arena en Hugging Face.
  - Repositorios de GitHub de SWE-bench, Aider, Terminal-Bench y METR.
  - CSV del Open ASR Leaderboard.
- **Lo demás sale de fragmentos del buscador** acotados a los dominios oficiales. Lo que no se pudo leer de primera
  mano dice **«a verificar»**: antes de usar una cifra textual, hay que abrir la página.

---

## 1. Fuentes de ranking

Confianza: 5 = metodología pública, datos abiertos y sin conflictos de interés; 1 = no sirve para decidir.

| Fuente | Qué mide | Actualización | API / datos | Licencia | Confianza | Por qué |
|---|---|---|---|---|---|---|
| **Arena** (ex LMArena, ex Chatbot Arena) — **arena.ai** | Preferencia humana a ciegas: texto, visión, webdev, búsqueda, documentos, agentes, imagen y video | Diaria | Dataset `lmarena-ai/leaderboard-dataset` en Hugging Face, con ranking `latest` e histórico `full` por categoría | **CC-BY-4.0** (leído en la ficha) | 4 | Método público y datos abiertos. Pero mide gusto, no corrección, y la empresa le vende evaluaciones a los mismos labs que rankea |
| **Artificial Analysis** | Índice de inteligencia (agentes, código, general, ciencia), precio, velocidad, latencia, voz a texto e imagen | Continua | Data API gratis con clave: 1.000 consultas por día, atribución obligatoria | Términos propios; redistribución **a verificar** | 4 | La más completa en precio y velocidad. El índice cambia de versión seguido (v4.1 → 4.3), así que no sirve para comparar en el tiempo |
| **SWE-bench Verified** (Princeton/Stanford) | Arreglar issues reales de GitHub (Python) | Irregular | `leaderboards.json` en GitHub y datasets en HF | MIT (código) | 2 | Saturado y contaminado: OpenAI dejó de reportarlo en feb-2026 (**a verificar**) y METR mostró que muchos parches «aprobados» no se aceptarían |
| **SWE-Bench Pro** (Scale) | Lo mismo, más difícil, con parte privada | Irregular (V2: 2026-09-22) | Split público en HF (**a verificar**) | **a verificar** | 3 | Menos contaminado. Scale le provee datos a los labs |
| **Terminal-Bench** (Stanford + Laude Institute) — tbench.ai | Agentes trabajando en una terminal (modelo + herramienta) | Por envíos | Repo en GitHub | Apache-2.0 | 4 | Lo más parecido a usar Claude Code o Codex. Conviven las versiones 2.0, 2.1 y 4.0, que no son comparables. Muchos envíos son del fabricante: filtrar los «verified» |
| **Aider Polyglot** — aider.chat | Editar código en 6 lenguajes | **Abandonado** (último cambio 2025-10-04) | YAML en GitHub | Apache-2.0 | 1 | No incluye ningún modelo de 2026. Sirve solo como histórico |
| **OpenRouter Rankings** | **Uso real** (tokens procesados), no calidad | Diaria | `GET /api/v1/models` (precios y fecha de vencimiento); rankings por API con clave | Términos de OpenRouter (**a verificar**) | 3 | Buena señal de uso y de precio. La sesgan los modelos gratis o en promoción |
| **METR** (time horizon) | Qué tan larga es la tarea que un agente completa (al 50%) | Por modelo | `METR/eval-analysis-public` en GitHub | **a verificar** | 4 | Lo mejor para tareas largas (frontera pública ≈12 h, may-2026). La misma METR publica sus límites |
| **Epoch AI** (Benchmarking Hub + ECI) | Agregado de más de 50 benchmarks | Continua (CSV del 2026-10-03) | CSV descargables y `pip install epochai` | **CC-BY** | 4 | Datos abiertos y metodología seria. FrontierMath tuvo financiamiento de OpenAI (**a verificar**) |
| **LiveCodeBench** | Programación competitiva, filtrable por fecha (evita contaminación) | Continua | GitHub | **a verificar** | 3 | Útil para código puro, no para trabajo agéntico |
| **LiveBench** | Preguntas que se renuevan | Mensual en teoría | Datasets en HF | **a verificar** | 2 | Los datos públicos son de 2025-04: parece parado (**a verificar**) |
| **Vals.ai** | Índice de tareas de negocio (finanzas, legal, impuestos, código) | Continua | No hay datos descargables | — | 3 | Al ser privados, contaminan menos pero se pueden auditar menos. Es una empresa comercial |
| **Open ASR Leaderboard** (Hugging Face + NVIDIA) | Transcripción: error por palabra (WER) y velocidad | Frecuente (versión 2026-10-02) | CSV en HF, incluye evaluaciones multilingües con español | **a verificar** | 4 | Abierto y reproducible. Cubre sobre todo modelos abiertos |
| **Artificial Analysis — Speech to Text** | Transcripción comercial (WER) | Continua | Data API (con atribución) | Términos propios | 4 | La que compara las APIs pagas (Gemini, OpenAI, ElevenLabs) |

**Dominio de Arena:** el oficial es **arena.ai**. El proyecto se rebautizó «Arena» el 2026-01-28 y lmarena.ai
redirige ahí (fuente: Wikipedia y prensa; la redirección no la pude comprobar, **a verificar**). El dataset sigue en
la organización `lmarena-ai` de Hugging Face.

**Críticas para tener presentes:**
- «The Leaderboard Illusion» (Cohere Labs y otros, 2025): https://arxiv.org/abs/2504.20879. Respuesta de Arena:
  https://arena.ai/blog/our-response
- OpenAI sobre SWE-bench Verified: https://openai.com/index/why-we-no-longer-evaluate-swe-bench-verified/ (**a verificar**)
- METR sobre los parches de SWE-bench:
  https://metr.org/notes/2026-03-10-many-swe-bench-passing-prs-would-not-be-merged-into-main/

**Contradicción sin resolver (a verificar):** ¿quién es el #1 de Arena en texto?
- Según un agente que leyó el dataset de HF (2026-10-02, con control de estilo): **gemini-4-argon-high** con 1525 puntos.
- Según el posteo oficial de Arena en X (≈2026-09-25): **Claude Opus 5.5 (High)** con 1509 puntos.
- Pueden ser vistas o fechas distintas. No pude abrir el dataset (formato parquet, descarga bloqueada) ni la web para
  desempatar. El dataset trae una columna de **categoría**, así que el filtro de idioma (español) se podría leer de
  ahí (**a verificar**).

---

## 2. Fuentes oficiales de cambios de modelos

### Anthropic (Claude) — leído directo
| Qué | Dónde |
|---|---|
| Modelos | https://platform.claude.com/docs/en/about-claude/models/overview |
| Retiros | https://platform.claude.com/docs/en/about-claude/model-deprecations |
| Precios | https://platform.claude.com/docs/en/about-claude/pricing |
| Novedades | https://platform.claude.com/docs/en/release-notes/overview (sin RSS) |
| API | `GET https://api.anthropic.com/v1/models` (pide clave y no consume tokens) |

- **La API no trae fecha de retiro.** La única fuente es la tabla «Model status» de la página de retiros: estado
  Active/Legacy/Deprecated/Retired, con fechas. Anthropic avisa con al menos 60 días, por correo y en esa página.
- **Vigentes:**
  - Fable 5.1 (`claude-fable-5-1`, US$10/50 por millón de tokens de entrada/salida)
  - Opus 5.5 (`claude-opus-5-5`, 4/20)
  - Sonnet 5.5 (`claude-sonnet-5-5`, 2/10)
  - Haiku 4.5 (`claude-haiku-4-5-20251001`, 1/5)
  - Los precios coinciden con LiteLLM.
- **Retiros anunciados:**
  - `claude-sonnet-4-5-20250929` se apaga el **2026-11-30** (LiteLLM coincide).
  - `claude-opus-4-5-20251101`: no antes del 2026-11-24.
  - `claude-haiku-4-5-20251001`: no antes del 2026-10-15, aunque **no está marcado como deprecado**.

### OpenAI — fragmentos oficiales + spec en GitHub
| Qué | Dónde |
|---|---|
| Modelos | https://developers.openai.com/api/docs/models (**a verificar**) |
| Retiros | https://developers.openai.com/api/docs/deprecations |
| Precios | https://developers.openai.com/api/docs/pricing (**a verificar**) |
| Novedades | https://developers.openai.com/api/docs/changelog |
| API | `GET https://api.openai.com/v1/models` (pide clave y no consume tokens) |

- **Es el único que da el retiro por API.** El spec oficial
  (https://raw.githubusercontent.com/openai/openai-openapi/master/openapi.yaml) define el campo **`shutdown_date`** en
  cada modelo: la fecha de apagado, o vacío si no está anunciada.
- **Vigentes (a verificar):**
  - GPT-6 Astra (US$10/50)
  - GPT-6.1 Sol (2/10; modelo por defecto de Codex)
  - GPT-6 Sol (2/10)
  - GPT-6 Luna (0,10/0,50)
  - Los precios de Sol y Luna coinciden con LiteLLM.
- **Retiros anunciados:**
  - **2026-12-11:** `gpt-5-2025-08-07`, gpt-5-mini, gpt-5-nano, gpt-5-pro, o3 y o3-pro. LiteLLM coincide para
    gpt-5. El reemplazo aparece distinto según el fragmento (**a verificar**).
  - **2027-02-26:** `whisper-1` y los `gpt-4o-*transcribe`.

### Google (Gemini) — fragmentos oficiales + discovery doc
| Qué | Dónde |
|---|---|
| Modelos | https://ai.google.dev/gemini-api/docs/models |
| Retiros | https://ai.google.dev/gemini-api/docs/deprecations |
| Precios | https://ai.google.dev/gemini-api/docs/pricing |
| Novedades | https://ai.google.dev/gemini-api/docs/changelog (sin RSS, **a verificar**) |
| Ciclo de vida en Vertex | https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/model-versions |
| API | `GET https://generativelanguage.googleapis.com/v1beta/models` (pide clave y no consume tokens) |

- **La API no trae fecha de retiro**: lo comprobé en el discovery doc del 2026-10-02.
- **Vigentes:**
  - `gemini-3.8-flash` (estable desde 2026-09-02, US$0,75/3,75; LiteLLM coincide)
  - `gemini-3.5-flash-lite`
  - `gemini-3.1-pro-preview`, que sigue en preview
  - **No hay Gemini 3.5 Pro público** (**a verificar**).
  - Hay reportes de que el precio de 3.6–3.8 Flash se duplica el 2027-01-01 (**a verificar**).

### El caso `gemini-2.5-pro`
- **Qué dice Google** (changelog del 2026-09-18, por fragmento, **a verificar**): limita los modelos 2.5 (Pro, Flash
  y Flash-Lite) a quienes ya los usaban. Dice que «no están deprecados» y que, para proyectos nuevos, se usen 3.5
  Flash-Lite o 3.8 Flash. No define qué es «haberlos usado».
- **Qué ve un proyecto nuevo:** un error 404 «This model models/gemini-2.5-pro is no longer available to new users.
  Please update your code to use models/gemini-3.1-pro-preview». Hay reportes en GitHub desde agosto de 2026, antes
  del aviso oficial.
- **Fechas contradictorias:**
  - Developer API: la página de retiros dijo primero 2026-06-17, después **2026-10-16**, y hoy no da fecha.
  - Vertex: apagado el **2026-10-20**. Esto está confirmado en LiteLLM: `gemini-2.5-pro` tiene 2026-10-20 y
    `gemini/gemini-2.5-pro` no tiene fecha.
- **Lección para el radar:** la lista de modelos y la página de retiros no alcanzan. Un modelo puede seguir «vigente»
  y no andar para una cuenta nueva. Solo lo detecta una prueba con la cuenta propia: `countTokens` no factura, pero que
  devuelva el mismo 404 es **a verificar**. Conviene guardar el texto del error, porque además sugiere el reemplazo.
- **Gemini CLI:** desde el 2026-06-18 no atiende cuentas personales y Google indica pasarse a Antigravity CLI.

### Agregadores legibles por máquina (para validar)
| Fuente | Qué da | Licencia |
|---|---|---|
| **LiteLLM** — https://raw.githubusercontent.com/BerriAI/litellm/main/model_prices_and_context_window.json | 4.473 modelos (bajado 2026-10-03), con precio por token y `deprecation_date` | MIT |
| **models.dev** — https://models.dev/api.json | Estado (`deprecated`), fechas y costos | MIT |
| **OpenRouter** — `GET https://openrouter.ai/api/v1/models` | Precios y `expiration_date` | Términos de OpenRouter (**a verificar**) |

**Cómo detectar un retiro sin gastar cupo:**
1. Comparar cada día el listado `/v1/models` de los tres proveedores: no consume tokens, pero pide clave. En OpenAI,
   además, leer `shutdown_date`.
2. Leer las tablas de las páginas de retiros de los tres (y la de Vertex) y compararlas entre sí.
3. Validar contra `deprecation_date` de LiteLLM y `expiration_date` de OpenRouter.
4. Para lo que usamos de verdad: una prueba gratis por modelo con la cuenta propia (caso `gemini-2.5-pro`).

---

## 3. Topes de las cuentas gratis o baratas (y cómo mirarlos sin gastar)

| Cuenta | Tope | Cómo consultarlo sin gastar | Fuente / fecha |
|---|---|---|---|
| **Codex con ChatGPT gratis (y Go)** | Incluido «por tiempo limitado». OpenAI no publica la cifra. Es **una sola ventana de 30 días**: no hay ventana de 5 h ni semanal. Eso lo muestran los datos que devuelve el sistema, no el centro de ayuda (**a verificar**) | `/status` dentro de Codex. Panel `chatgpt.com/codex/settings/usage`. El último evento `token_count` → `rate_limits` en `~/.codex/sessions/…/rollout-*.jsonl` (campo `window_minutes` = 43200) | help.openai.com/en/articles/11369540 · hilo «Usage quotas changed to monthly?» en community.openai.com (2026-10-03) |
| **Codex con ChatGPT Plus** | Una ventana de **5 h** y un **tope semanal** encima. Mensajes estimados cada 5 h: Astra 5–45, GPT-6.1 Sol 15–160, Luna 350–3.000. Son estimaciones, no topes fijos. Las tareas en la nube gastan más | `/status` (muestra el % que queda de cada ventana y cuándo se reinicia) y el panel de uso | help.openai.com/en/articles/20001516 · help.openai.com/en/articles/11369540 (2026-10-03, **a verificar** cifras) |
| **Gemini API gratis** | Por **proyecto**, no por clave. El tope diario se reinicia a la medianoche del Pacífico. Las cifras por modelo ya no están en una tabla pública: se ven en AI Studio. Cifras de terceros: 3.8 Flash ≈20 por día, Flash-Lite ≈500 por día (**a verificar**). Pro no tiene plan gratis (**a verificar**) | `aistudio.google.com/usage?tab=rate-limit` (límites y consumo de 28 días) | ai.google.dev/gemini-api/docs/rate-limits · /pricing (2026-10-03) |
| **Antigravity (IDE) y Antigravity CLI (`agy`)** | Plan Free con **cuota semanal** (ya no cada 5 h; eso quedó para los pagos). Flash y Pro comparten un solo cupo, que se descuenta según el precio de API. Modelos del Free: Gemini 3.6–3.8 Flash, 3.1 Pro, Claude Sonnet y Opus 4.6, gpt-oss-120b | **`/usage`** (o `/quota`) en el CLI: muestra lo que queda por modelo **sin hacer ningún pedido al modelo** | antigravity.google/docs/plans · antigravity.google/docs/cli/commands/usage (2026-10-03) |
| **Gemini CLI** | Desde el 2026-06-18 **no atiende cuentas personales**. Solo anda con una clave de la Gemini API (y su plan gratis) o con Code Assist de empresa | `/stats` en el CLI; con clave, el panel de AI Studio | developers.google.com/gemini-code-assist/docs/deprecations/code-assist-individuals (2026-10-03) |
| **Claude Pro / Max** (referencia) | Sesión que se reinicia **cada 5 h** y un **tope semanal**. Claude.ai, la app y Claude Code comparten el cupo. Max da 5× o 20× el de Pro | **`/usage`** en Claude Code; en claude.ai, Settings > Usage | support.claude.com/en/articles/11647753 · code.claude.com/docs/en/costs (2026-10-03) |

**Ojo con la Gemini API gratis:** según los términos y la tabla de precios, Google **usa esos datos para mejorar sus
productos**, y pueden leerlos revisores humanos (ai.google.dev/gemini-api/terms, **a verificar** textual). **No
delegar ahí código privado, datos de clientes ni nada sensible.**

---

## 4. Mapa tarea → mejor opción hoy (octubre de 2026)

Entre lo que ya usamos: Claude (suscripción), Codex (cuenta de ChatGPT) y Gemini/Antigravity (gratis o barato).

| Tarea | Recomendada | Alternativa | Fuente / fecha |
|---|---|---|---|
| **Programar** | Claude **Opus 5.5** en Claude Code (Sonnet 5.5 para lo rutinario) | **GPT-6.1 Sol** en Codex. Gratis: Gemini 3.8 Flash en Antigravity | Terminal-Bench 4.0: Opus 5.5 66,4% vs GPT-6 Astra 57,9% (anthropic.com/news/claude-opus-5-5, 2026-09-22, dato del fabricante). Arena WebDev: Opus 5.5 #1, GPT-6 Astra #2 (dataset de Arena, 2026-10-01, **a verificar**) |
| **Revisar código / seguridad** | Claude Code `/code-review` + `/security-review` con Opus 5.5 | **Segunda revisión en Codex** (un modelo distinto encuentra otros errores) | CR-bench (arXiv 2603.23448, mar-2026): Claude Code 32,1% vs Codex 20,1% (**a verificar**). Bug Hunt Bench (2026-09-15): GPT-6 Astra lidera al máximo esfuerzo (**a verificar**) |
| **Investigar en la web** | **ChatGPT deep research** (GPT-6 Astra) | Claude Research (Opus 5.5) para sintetizar. Gemini Deep Research (5 informes gratis por mes) | BrowseComp (README de steel-dev en GitHub, leído 2026-10-03): GPT-5.6 Sol 92,2%, Astra 91,5%, Opus 5 90,8%. **Casi empatados**: elegir por el cupo que quede |
| **Escribir en castellano** | Claude **Opus 5.5** (Sonnet 5.5 para volumen) | GPT-6.1 Sol | Arena texto general: Opus 5.5 #1 (posteo oficial de Arena en X, ≈2026-09-25), en contradicción con la lectura del dataset (ver § 1). **No hay dato del filtro «Spanish»: a verificar** |
| **Leer documentos largos** | **Gemini 3.8 Flash** (1M de contexto, barato) para cargar el material | Opus 5.5 (1M de contexto) para analizarlo dentro de Claude Code | Los tres tienen 1M de contexto (fichas, sep-2026). MRCR v2 a 1M: Gemini 3.7 Flash 97% (llm-stats, **a verificar**). Precio de 3.8 Flash en LiteLLM, 2026-10-03 |
| **Imágenes: generar y editar** | **ChatGPT Images** (gpt-image-2.5) | Nano Banana 2 (Gemini 3.1 Flash Image), gratis en la app de Gemini | Arena texto-a-imagen y edición: gpt-image-2.5 #1 (2026-09-24 y 09-29, **a verificar**). Claude no genera imágenes |
| **Imágenes: entender** | Claude Opus 5.5 / Fable | GPT-6.1 Sol, Gemini 3.8 Flash | Arena visión: Claude Fable 5 #1 (dataset de Arena, 2026-10-02, **a verificar**) |
| **Transcribir audio** | **Gemini 3.5 Transcribe** (Gemini API) | GPT Transcribe (OpenAI). Fuera de los tres: ElevenLabs Scribe v2 es el mejor de las APIs comerciales | Artificial Analysis STT: Scribe v2 2,2%, Gemini 3.5 Transcribe 2,6%, GPT Transcribe 3,3% de error (sep-2026, **a verificar**). **Sin dato propio para castellano.** Claude no transcribe |
| **Tareas mecánicas baratas** | **GPT-6 Luna** (US$0,10/0,50 por millón) | Gemini Flash-Lite (con plan gratis, pero ver el ojo de § 3). **Haiku 4.5** si tiene que quedar dentro de Claude Code | Precios en LiteLLM (Luna, Haiku) y en claude.com/pricing (2026-10-03). Flash-Lite 3.1/3.5: US$0,25–0,30 de entrada (**a verificar**) |

Reparto que sale de la tabla: **Claude** programa, revisa y escribe. **Codex** hace la segunda revisión, la
investigación profunda y las imágenes. **Gemini** carga los documentos enormes, transcribe y hace volumen barato,
nunca con datos sensibles en el plan gratis.

---

## 5. Cómo actualizarlo solo (sin gastar cupo de IA)

Las tres opciones leen datos, comparan y **proponen**. Ninguna usa IA ni cambia una regla sin que alguien lo apruebe
(regla 3 del método).

### Opción A — Tarea programada en GitHub, en el catálogo (recomendada)
- **Qué consulta:**
  - Dataset de Arena en HF (categorías texto, webdev, visión, imagen, documentos y búsqueda).
  - CSV de Epoch AI.
  - JSON de LiteLLM (precios y `deprecation_date`).
  - models.dev.
  - `GET /api/v1/models` de OpenRouter.
  - Las tres páginas de retiros, comparando la tabla con la vez anterior.
- **Sin claves:** son todas fuentes públicas, así que no hace falta guardar secretos en un repo público.
- **Cada cuánto:** retiros y precios, todos los días. Rankings, una vez por semana.
- **Qué hace:** si cambia el #1 de una categoría que usamos, si se anuncia el retiro de un modelo nombrado en
  nuestras reglas o si un precio sube más del 20%, abre un PR con el diff de un archivo único (por ejemplo
  `RADAR.md`) y el motivo.
- **Cómo llega a los clientes:** con la actualización normal del plugin, que el vigía ya avisa.
- **A favor:** un solo lugar, auditable, sin red en la compu del cliente, y las licencias (CC-BY y MIT) permiten
  usar los datos citando la fuente.
- **En contra:** no ve lo que depende de cada cuenta (el caso `gemini-2.5-pro`).

### Opción B — Chequeo local, dentro del vigía
- **Qué hace:** cada semana, en la compu de cada uno, lista `/v1/models` con las claves propias y hace la prueba
  gratis de los modelos que nombran las reglas.
- **A favor:** es lo único que detecta «no disponible para tu cuenta».
- **En contra:** necesita claves en cada computadora y red desde la compu del cliente, y repite la misma búsqueda en
  cada una.

### Opción C — Una sola fuente comercial: Data API de Artificial Analysis
- **Qué hace:** una sola consulta (gratis, 1.000 por día, con clave y atribución) trae índices, precio y velocidad.
- **A favor:** la más simple.
- **En contra:** depende de una empresa, el índice cambia de versión, la redistribución está **a verificar** y no
  cubre los retiros.

### Recomendación
**A como base**, y de **B solo la prueba de disponibilidad**, opcional y apagada por defecto, para los 3–5 modelos que
nombran nuestras reglas. Los **topes de cupo** se miran localmente con los comandos que no gastan nada (`/usage` en
Claude Code y en Antigravity CLI, `/status` en Codex, el panel de AI Studio), junto con `scripts/codex-cupo` y la
regla 16 que ya existen. C queda como validación cruzada, si sus términos lo permiten.

---

## 6. Pendiente de verificar a mano (estaba bloqueado desde acá)
- arena.ai/leaderboard: el #1 de texto (§ 1), el filtro de idioma español, webdev, visión e imagen. Y si lmarena.ai
  redirige.
- artificialanalysis.ai: términos de la Data API (redistribución), speech-to-text y top del índice.
- developers.openai.com: modelos, precios, retiros (reemplazo de gpt-5) y el anuncio de apagados del 2026-10-23.
- ai.google.dev: rate limits del plan gratis por modelo, la nota del changelog del 2026-09-18 sobre los 2.5, la fecha
  real de retiro de `gemini-2.5-pro` y de 2.5 Flash-Lite, los precios de Flash-Lite y los términos de uso de datos.
- help.openai.com: la ventana de 30 días de Codex gratis y las cifras de mensajes de Plus.
- swebench.com y labs.scale.com: top actual de Verified y de Pro.
- Si `countTokens` de Gemini devuelve el 404 de «new users» (sirve para la prueba gratis de la opción B).
- Licencias: OpenRouter, METR, Open ASR, LiveCodeBench y LiveBench.
