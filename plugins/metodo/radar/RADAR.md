# Radar de modelos

> Generado desde `RADAR.yaml` (`radar.py md`). No se edita a mano. Última actualización: **2026-10-10**.
> `[a verificar]` = dato de la investigación que todavía no se leyó de primera mano.

Para elegir: `radar.py elegir <categoría>`; si falta el plan A te devuelve el B o el C.

## Modelos vigentes

Último modelo de cada familia (lo escribe el robot; el orden A/B/C de abajo es a mano).

| Familia | Modelo | Alta |
|---|---|---|
| Claude Haiku | claude-haiku-5-5 | 2026-10-07 |
| Claude Sonnet | claude-sonnet-5-5 | 2026-09-28 |
| Claude Opus | claude-opus-5-5 | 2026-09-22 |
| Claude Fable | claude-fable-5-1 | 2026-09-01 |
| GPT Sol | gpt-6.1-sol | 2026-09-29 |
| GPT Astra | gpt-6-astra | 2026-09-03 |
| GPT Luna | gpt-6-luna | 2026-09-22 |
| Gemini Flash | gemini-3.8-flash | 2026-09-02 |
| Gemini Flash-Lite | gemini-3.5-flash-lite | 2026-07-21 |
| Gemini Pro | gemini-3.1-pro | 2026-02-19 |

## Ruteo de Claude por tipo de tarea

Punto de partida de nivel y esfuerzo de Claude por tipo de tarea. Cada fila cita la evidencia INDEPENDIENTE de este mismo radar que la respalda (spec §7). Donde no hay medición, la fila queda verificado: false y vale el valor por defecto de la política de modelos tal cual (0 «sí» a ¿hay que juzgar o decidir?, ¿equivocarse sale caro?, ¿hay mucho contexto? = haiku/low · 1 = sonnet/medium · 2 = opus/high · 3 = fable/xhigh): se baja un escalón solo cuando hay duda entre dos, no por falta de datos. Si la tarea tiene más «sí» de los que supone la fila, se sube un escalón por cada uno. Fable solo a pedido, max solo a pedido. Lo escribe una persona a mano: el robot no lo toca.

| Tarea | Nivel | Esfuerzo | ¿Otra IA? |
|---|---|---|---|
| Buscar, contar, listar, mover, renombrar o resumir algo ya decidido | haiku | low | tareas_baratas |
| Implementar algo acotado: un arreglo claro, un script, una función, tests | sonnet | low | desarrollo |
| Revisar un cambio o dar una segunda opinión | sonnet | medium | revision |
| Planillas, conciliaciones y análisis de datos | sonnet | low | datos_planillas |
| Investigar en la web y juntar fuentes | sonnet | low | investigacion_web |
| Arquitectura, seguridad, dinero o algo irreversible (planear en Claude; la revisión puede ir a otra IA) | opus | high | revision |

## Desarrollo (programar)

Orden respaldado por 2 fuentes independientes.

| Plan | Herramienta | Por qué | Datos privados | Condiciones |
|---|---|---|---|---|
| A | Claude Code (Anthropic, Opus 5.5) [a verificar] | Primero en el índice de agentes de programación de Artificial Analysis (Claude Code). Sonnet 5.5 para lo rutinario: en ese índice rinde igual. | sí |  |
| B | Codex (OpenAI, GPT-6.1 Sol) [a verificar] | Codex con GPT-6 Astra es el 1° de Terminal-Bench (58,2%) y Codex con GPT-6.1 Sol queda 4° en el índice de Artificial Analysis (63): otro modelo encuentra otros errores. | sí | Con cuenta gratis, revisá la privacidad de la cuenta antes de mandar código privado. |
| C | Antigravity (Google, Gemini 3.8 Flash) [a verificar] | Gratis, pero en Terminal-Bench rinde mucho menos (Gemini 3.8 Flash: 19,1%): solo tareas acotadas. | no | En el plan gratis Google usa lo que mandás para mejorar sus productos: sin código privado ni datos de clientes. |

Ranking (Arena (dataset en Hugging Face), 2026-10-05): 1. claude-opus-5.5-max; 2. gpt-6-astra-max; 3. claude-sonnet-5.5-xhigh; 4. gpt-6.1-sol-max; 5. claude-fable-5.1-max

## Revisión de código y seguridad

Orden PROVISORIO: 0 de 2 fuentes independientes.

| Plan | Herramienta | Por qué | Datos privados | Condiciones |
|---|---|---|---|---|
| A | Claude Code (Anthropic, Opus 5.5) [a verificar] | /code-review y /security-review con Opus 5.5; CR-bench: Claude Code 32,1% contra Codex 20,1% (a verificar). | sí |  |
| B | Codex (OpenAI, GPT-6.1 Sol) [a verificar] | Segunda revisión con un modelo distinto: `codex exec --sandbox read-only`. Encuentra errores que el primero no ve. | sí |  |
| C | Antigravity (Google, Gemini 3.1 Pro) [a verificar] | Revisión estática sin ejecutar nada: `agy --mode plan -p=...`. | no | En el plan gratis Google usa lo que mandás para mejorar sus productos: sin código privado ni datos de clientes. |

## Diseño (UI web, presentaciones)

Orden PROVISORIO: hay 2 fuentes independientes, pero no todos los planes se apoyan en ellas.

| Plan | Herramienta | Por qué | Datos privados | Condiciones |
|---|---|---|---|---|
| A | Claude Code (Anthropic, Opus 5.5) [a verificar] | Primero en Arena WebDev y en Design Arena; con la skill de diseño del plugin que corresponda. | sí |  |
| B | Codex (OpenAI, GPT-6.1 Sol) [a verificar] | GPT-6.1 Sol es 4° en Arena WebDev; GPT-6 Astra (también en Codex) es 2° en Arena WebDev y en Design Arena: sirve para una segunda propuesta. | sí |  |
| C | Antigravity (Google, Gemini 3.8 Flash) [a verificar] | Gratis para bocetos; no para material de clientes. | no | En el plan gratis Google usa lo que mandás para mejorar sus productos: sin código privado ni datos de clientes. |

Ranking (Arena (dataset en Hugging Face), 2026-10-05): 1. claude-opus-5.5-max; 2. gpt-6-astra-max; 3. claude-sonnet-5.5-xhigh; 4. gpt-6.1-sol-max; 5. claude-fable-5.1-max

## Escritura en castellano

Orden respaldado por 2 fuentes independientes.

| Plan | Herramienta | Por qué | Datos privados | Condiciones |
|---|---|---|---|---|
| A | Claude Code (Anthropic, Opus 5.5) [a verificar] | Claude está en el grupo de arriba en las dos: Arena texto 4° (empate técnico con el 1°, Gemini 4 Argon) y EQ-Bench 7° con Opus 5.5 (Fable 5.1 es 2° si el texto lo vale). Sin dato del filtro en castellano. | sí |  |
| B | Codex (OpenAI, GPT-6.1 Sol) [a verificar] | GPT-6 Astra es el 1° de EQ-Bench y GPT-6 Sol el 4°: buena segunda voz. | sí |  |
| C | app web de Gemini (Google, Gemini 3.8 Flash) [a verificar] | Gratis, pero en EQ-Bench queda bastante más abajo (1748 contra 2050 de Opus 5.5): para borradores sin datos sensibles. | no | En el plan gratis Google usa lo que mandás para mejorar sus productos: sin código privado ni datos de clientes. |

Ranking (Arena (dataset en Hugging Face), 2026-10-05): 1. gemini-4-argon-high; 2. claude-opus-5.5-high; 3. claude-fable-5.1-max; 4. claude-opus-5-max; 5. claude-opus-4-6-high

## Investigación web

Orden PROVISORIO: 1 de 2 fuentes independientes.

| Plan | Herramienta | Por qué | Datos privados | Condiciones |
|---|---|---|---|---|
| A | app web (ChatGPT deep research) (OpenAI, GPT-6 Astra) [a verificar] | BrowseComp: casi empatado con Sonnet/Opus (92,2 / 91,5 / 90,8): elegir por el cupo que quede. | sí |  |
| B | Codex (OpenAI, GPT-6.1 Sol) [a verificar] | Por consola: `codex --search exec --sandbox read-only`. Es lo que se puede automatizar desde una sesión. | sí |  |
| C | app web (Gemini Deep Research) (Google, Gemini 3.8 Flash) [a verificar] | 5 informes gratis por mes. | no | En el plan gratis Google usa lo que mandás para mejorar sus productos: sin código privado ni datos de clientes. |

Ranking (BrowseComp (README de steel-dev), 2026-10-03): 1. GPT-5.6 Sol; 2. GPT-6 Astra; 3. Claude Opus 5

## Documentos largos

Orden PROVISORIO: hay 2 fuentes independientes, pero no todos los planes se apoyan en ellas.

| Plan | Herramienta | Por qué | Datos privados | Condiciones |
|---|---|---|---|---|
| A | Claude Code (Anthropic, Opus 5.5) [a verificar] | Los 5 primeros de Arena documentos son Claude (Opus 5 y Fable 5.1 arriba); Opus 5.5 lee hasta 1M de tokens. | sí |  |
| B | API / app web de Gemini (Google, Gemini 3.8 Flash) [a verificar] | 1M de contexto y barato (US$0,75/3,75 por millón): sirve para cargar el material. | no | Plan gratis: Google usa los datos. Con la API paga, mirá los términos (a verificar). |
| C | Codex (OpenAI, GPT-6.1 Sol) [a verificar] | 1M de contexto. | sí |  |

Ranking (MRCR v2 a 1M (llm-stats), 2026-09-30): 1. Gemini 3.7 Flash

## Imágenes (generar y editar)

Orden PROVISORIO: hay 2 fuentes independientes, pero no todos los planes se apoyan en ellas.

| Plan | Herramienta | Por qué | Datos privados | Condiciones |
|---|---|---|---|---|
| A | app web (ChatGPT Images) (OpenAI, gpt-image-2.5) [a verificar] | Primero en Arena y en Artificial Analysis, texto a imagen y edición. Claude no genera imágenes. | sí | No subas fotos de personas ni de clientes sin permiso. |
| B | app web de Gemini (Google, Nano Banana 2 (Gemini 3.1 Flash Image)) [a verificar] | Gratis en la app de Gemini. | no | En el plan gratis Google usa lo que mandás para mejorar sus productos: sin código privado ni datos de clientes. |
| C | Adobe Firefly / Express (conector) (Adobe) [a verificar] | Sin dato en la investigación: alternativa con licencia comercial clara (a verificar). | sí | A completar en la próxima revisión. |

## Imágenes (entender)

Orden PROVISORIO: hay 2 fuentes independientes, pero no todos los planes se apoyan en ellas.

| Plan | Herramienta | Por qué | Datos privados | Condiciones |
|---|---|---|---|---|
| A | Claude Code (Anthropic, Opus 5.5) [a verificar] | Primero en MMMU-Pro (88%) y Claude arriba en Arena visión (Fable 5 1°): entiende imágenes dentro de Claude Code. | sí |  |
| B | Codex (OpenAI, GPT-6.1 Sol) [a verificar] | Alternativa. | sí |  |
| C | Antigravity (Google, Gemini 3.8 Flash) [a verificar] | Alternativa gratis. | no | En el plan gratis Google usa lo que mandás para mejorar sus productos: sin código privado ni datos de clientes. |

Ranking (Arena (dataset en Hugging Face), 2026-10-05): 1. claude-fable-5-high; 2. claude-opus-5-high; 3. claude-fable-5.1-max; 4. claude-opus-4-7; 5. gemini-3.8-flash-high

## Video

Orden PROVISORIO: hay 2 fuentes independientes, pero no todos los planes se apoyan en ellas.

| Plan | Herramienta | Por qué | Datos privados | Condiciones |
|---|---|---|---|---|
| A | app web de Gemini (Google, Gemini Omni Flash) [a verificar] | Gemini Omni es 1° en Arena texto a video y 3° en imagen a video de Artificial Analysis (Wan 3.0 y MiniMax H3 encabezan ahí, pero no están en apps que usamos). | no | Pendiente de verificar. |
| B | app web (Sora) (OpenAI, Sora (a verificar)) [a verificar] | Sin dato en la investigación. | no | Pendiente de verificar. |
| C | Adobe Express (conector) (Adobe) [a verificar] | Cortes rápidos y redimensionado con el conector de Adobe (a verificar). | sí | Pendiente de verificar. |

## Transcripción de audio

Orden PROVISORIO: hay 2 fuentes independientes, pero no todos los planes se apoyan en ellas.

| Plan | Herramienta | Por qué | Datos privados | Condiciones |
|---|---|---|---|---|
| A | API de ElevenLabs (ElevenLabs, Scribe v2) [a verificar] | Menos errores que Gemini y OpenAI en las dos fuentes (Scribe v2: 2,2% en Artificial Analysis, 6° en Open ASR). | sí |  |
| B | API de Gemini (Google, Gemini 3.5 Transcribe) [a verificar] | Muy cerca de Scribe (2,6% de error en Artificial Analysis) y más barato si ya usás Gemini. | no | Plan gratis: Google usa los datos; con audios de clientes usá la API paga. |
| C | API de OpenAI (OpenAI, GPT Transcribe) [a verificar] | 3,3% de error. Ojo: los gpt-4o-*transcribe se apagan el 2027-02-26. | sí |  |

Ranking (Artificial Analysis, speech to text (a verificar), 2026-09-30): 1. ElevenLabs Scribe v2; 2. Gemini 3.5 Transcribe; 3. GPT Transcribe

## Voz (texto a voz)

Orden PROVISORIO: 1 de 2 fuentes independientes.

| Plan | Herramienta | Por qué | Datos privados | Condiciones |
|---|---|---|---|---|
| A | API de ElevenLabs (ElevenLabs) [a verificar] | Eleven v4 es el 1° del ranking de voz de Artificial Analysis. | sí | Pendiente de verificar. |
| B | API de OpenAI (OpenAI) [a verificar] | Sin dato en la investigación. | sí | Pendiente de verificar. |
| C | API de Gemini (Google) [a verificar] | Gemini 3.8 Flash TTS es 4° en Artificial Analysis. | no | En el plan gratis Google usa lo que mandás para mejorar sus productos: sin código privado ni datos de clientes. |

## Datos y planillas

Orden PROVISORIO: 1 de 2 fuentes independientes.

| Plan | Herramienta | Por qué | Datos privados | Condiciones |
|---|---|---|---|---|
| A | Claude Code (Anthropic, Sonnet 5.5) [a verificar] | Sonnet 5.5 es 2° en el test de análisis de datos de Artificial Analysis (57,5%); Opus 5.5 si el cálculo es delicado. | sí |  |
| B | Codex (OpenAI, GPT-6.1 Sol) [a verificar] | GPT-6.1 Sol es 2° leyendo documentos con números (GDP.pdf, 32%). | sí |  |
| C | API / app web de Gemini (Google, Gemini 3.8 Flash) [a verificar] | Barato para volumen. | no | En el plan gratis Google usa lo que mandás para mejorar sus productos: sin código privado ni datos de clientes. |

## Tareas mecánicas baratas

Orden PROVISORIO: 1 de 2 fuentes independientes.

| Plan | Herramienta | Por qué | Datos privados | Condiciones |
|---|---|---|---|---|
| A | API de OpenAI (OpenAI, GPT-6 Luna) [a verificar] | US$0,10/0,50 por millón: lo más barato. | sí |  |
| B | API de Gemini (Google, Gemini Flash-Lite) [a verificar] | Con plan gratis (pero ver la condición). | no | En el plan gratis Google usa lo que mandás para mejorar sus productos: sin código privado ni datos de clientes. |
| C | Claude Code (Anthropic, Haiku 5.5) [a verificar] | Si tiene que quedar dentro de Claude Code: Haiku 5.5, el más barato de Claude (US$0,10 de entrada y US$0,50 de salida por millón de tokens, en prompts de hasta 100 mil tokens). | sí |  |

## Agentes de tarea larga

Orden PROVISORIO: hay 2 fuentes independientes, pero no todos los planes se apoyan en ellas.

| Plan | Herramienta | Por qué | Datos privados | Condiciones |
|---|---|---|---|---|
| A | Claude Code (Anthropic, Opus 5.5) [a verificar] | Claude arriba en Arena Agent; Fable 5.1 (más caro) es el primero si la tarea lo vale. | sí |  |
| B | Codex (OpenAI, GPT-6.1 Sol) [a verificar] | GPT-6.1 Sol es 5° en Arena Agent; Codex con GPT-6 Astra es 1° en Terminal-Bench. | sí |  |
| C | Antigravity (Google, Gemini 3.1 Pro) [a verificar] | Alternativa gratis para tareas acotadas. | no | En el plan gratis Google usa lo que mandás para mejorar sus productos: sin código privado ni datos de clientes. |

## Retiros

| Modelo | Proveedor | Fecha | Tipo | Nota |
|---|---|---|---|---|
| claude-sonnet-4-5-20250929 | Anthropic | 2026-11-30 | apagado | Reemplazo: Sonnet 5.5. |
| claude-opus-4-5-20251101 | Anthropic | 2026-11-24 | no_antes | No se retira antes de esta fecha. |
| claude-haiku-4-5-20251001 | Anthropic | 2026-10-15 | no_antes | No se retira antes de esta fecha; no figura como deprecado. |
| gpt-5-2025-08-07 | OpenAI | 2026-12-11 | apagado | También gpt-5-mini, gpt-5-nano, gpt-5-pro, o3 y o3-pro. El reemplazo figura distinto según la fuente. |
| gpt-4o-transcribe | OpenAI | 2027-02-26 | apagado | También whisper-1 y los demás gpt-4o-*transcribe. |
| gemini-2.5-pro | Google | 2026-10-20 | restringido | Vertex: se apaga el 2026-10-20. En la Developer API ya no está disponible para cuentas nuevas (error 404) sin estar deprecado: solo lo detecta `radar.py probar`. |
| gemini-3.5-flash-lite | Google | 2027-07-21 | apagado | Detectado por litellm. |
