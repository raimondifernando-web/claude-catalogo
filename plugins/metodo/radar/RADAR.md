# Radar de modelos

> Generado desde `RADAR.yaml` (`radar.py md`). No se edita a mano. Última actualización: **2026-10-29**.
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
| Gemini Argon | gemini-4-argon | 2026-10-13 |
| GPT Terra | gpt-6.1-terra | 2026-10-26 |

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

Orden respaldado por 3 fuentes independientes.

| Plan | Herramienta | Por qué | Datos privados | Condiciones |
|---|---|---|---|---|
| A | Claude Code (Anthropic, Opus 5.5) | Primero en las tres fuentes: índice de agentes de programación de Artificial Analysis (Claude Code con Opus 5.5: 62), Terminal-Bench 4.0 (64,8%) y Arena WebDev (1810). Sonnet 5.5 rinde casi igual y cuesta menos (59, 61,8% y 1770): para lo rutinario. | sí |  |
| B | Codex (OpenAI, GPT-6.1 Sol) | Codex con GPT-6.1 Sol: 54 en el índice de Artificial Analysis (con GPT-6 Astra, 55), 58,2% en Terminal-Bench 4.0 (igual que Astra, a una quinta parte del costo en esa tabla) y 5.º en Arena WebDev (1751). Otro modelo encuentra otros errores. | sí | Con cuenta gratis, revisá la privacidad de la cuenta antes de mandar código privado. |
| C | Antigravity (Google, Gemini 4 Argon) [a verificar] | Gemini 4 Argon queda a un punto de Codex en el índice (53 contra 54) pero 11.º contra 5.º en Arena WebDev (1679 contra 1751): empate técnico, se deja B por tener más historia. Gemini 3.8 Flash, el modelo que figuraba acá, rinde mucho menos (Terminal-Bench 20%, Arena WebDev 37.º). Gemini 4 Carbon (59 en el índice, 4.º en WebDev) todavía no tiene acceso general: cuando salga es candidato a plan B. | no | Gemini 4 Argon en Antigravity es solo para suscriptores de Google AI Ultra (en la app de Gemini, desde AI Pro; por API, US$2/10 por millón hasta el 30/11/2026 y US$4/20 después, según Google). Con otra cuenta, Antigravity usa el mejor Gemini que tenga (delegar.py lo resuelve solo). En el plan gratis Google usa lo que mandás para mejorar sus productos: sin código privado ni datos de clientes. |

Ranking (Arena (dataset en Hugging Face), 2026-10-29): 1. Claude Opus 5.5 (Max); 2. GPT-6 Astra (Max); 3. Claude Sonnet 5.5 (xHigh); 4. Gemini 4 Carbon (High); 5. GPT-6.1 Sol (Max)

## Revisión de código y seguridad

Orden respaldado por 3 fuentes independientes.

| Plan | Herramienta | Por qué | Datos privados | Condiciones |
|---|---|---|---|---|
| A | Claude Code (Anthropic, Opus 5.5) | Mejor revisor en Qodo (F1 56,8%) y en el grupo de arriba en ironbee (55,1); en cross-review empata con Codex y queda a 0,05 de Gemini 4 Argon, con la mitad de falsas alarmas de Codex y la corrida más rápida (141 s). `/code-review` y `/security-review`. | sí |  |
| B | Antigravity (Google, Gemini 4 Argon) | El revisor más preciso: el 87% de lo que marca es un error real y casi no da falsas alarmas (5%). Gana en F1 a Codex de forma significativa (0,780 contra 0,707) y queda en el grupo 2 de ironbee, por encima de GPT-6.1 Sol (grupo 4). Se le escapan los errores que piden leer más allá del diff (acierta 75-83% en esos): usalo como segunda opinión, no solo. Sin ejecutar nada: `agy --mode plan -p=...`. | no | Gemini 4 Argon en Antigravity es solo para suscriptores de Google AI Ultra (en la app de Gemini, desde AI Pro; por API, US$2/10 por millón hasta el 30/11/2026 y US$4/20 después, según Google). Con otra cuenta, Antigravity usa el mejor Gemini que tenga (delegar.py lo resuelve solo). Con Gemini 3.8 Flash la revisión queda a la par de Codex (47,0% contra 46,6% en Qodo). En el plan gratis Google usa lo que mandás para mejorar sus productos: sin código privado ni datos de clientes. |
| C | Codex (OpenAI, GPT-6.1 Sol) | Encuentra casi todos los errores (Codex con GPT-6 Astra: 92% en cross-review) pero marca de más (48% de falsas alarmas); GPT-6.1 Sol queda en el grupo 4 de ironbee (F1 43,7) y los GPT-6 detrás de Claude en Qodo. Úsalo cuando el código es privado o cuando importa no dejar pasar nada: `codex exec --sandbox read-only`. | sí |  |

## Diseño (UI web, presentaciones)

Orden respaldado por 2 fuentes independientes.

| Plan | Herramienta | Por qué | Datos privados | Condiciones |
|---|---|---|---|---|
| A | Claude Code (Anthropic, Opus 5.5) [a verificar] | Primero en Arena WebDev (1810 contra 1773 de GPT-6 Astra) y en Design Arena (al 2026-10-03, no releída hoy); con la skill de diseño del plugin que corresponda. | sí |  |
| B | Codex (OpenAI, GPT-6.1 Sol) [a verificar] | GPT-6.1 Sol es 5.º en Arena WebDev (1751); GPT-6 Astra (también en Codex) es 2.º (1773) y 2.º en Design Arena: sirve de segunda opinión de diseño. | sí |  |
| C | Antigravity (Google, Gemini 4 Argon) [a verificar] | Gemini 4 Argon es 11.º en Arena WebDev (1679); Gemini 3.8 Flash, el que figuraba acá, 37.º (1583). Gemini 4 Carbon, 4.º (1768), todavía sin acceso general. Para bocetos; no para material de clientes. | no | Gemini 4 Argon en Antigravity es solo para suscriptores de Google AI Ultra (en la app de Gemini, desde AI Pro; por API, US$2/10 por millón hasta el 30/11/2026 y US$4/20 después, según Google). Con otra cuenta, Antigravity usa el mejor Gemini que tenga (delegar.py lo resuelve solo). En el plan gratis Google usa lo que mandás para mejorar sus productos: sin código privado ni datos de clientes. |

Ranking (Arena (dataset en Hugging Face), 2026-10-29): 1. Claude Opus 5.5 (Max); 2. GPT-6 Astra (Max); 3. Claude Sonnet 5.5 (xHigh); 4. Gemini 4 Carbon (High); 5. GPT-6.1 Sol (Max)

## Escritura en castellano

Orden PROVISORIO: hay 2 fuentes independientes, pero no todos los planes se apoyan en ellas.

| Plan | Herramienta | Por qué | Datos privados | Condiciones |
|---|---|---|---|---|
| A | Claude Code (Anthropic, Opus 5.5) | Claude es lo único que está arriba en las dos fuentes: en Arena (voto humano) Opus 5.5 es 1.º en escritura creativa y 7.º en español (1504; Opus 5 y Fable 5.1 lideran con 1520 y 1518), y en EQ-Bench los Claude ocupan 3.º, 4.º y 8.º. Sonnet 5.5 queda muy abajo en español (67.º, 1447): para volumen en castellano usá Opus. | sí |  |
| B | Codex (OpenAI, GPT-6.1 Sol) [a verificar] | A VERIFICAR. GPT-6.1 Sol es 62.º en Arena texto y 80.º en español, y no está entre los 30 primeros de EQ-Bench (que lidera GPT-6 Astra con 2177, pero Astra es 117.º en español de Arena). Las fuentes se contradicen con los GPT: se deja en B por falta de una segunda fuente en castellano. | sí |  |
| C | app web de Gemini (Google, Gemini 3.8 Flash) [a verificar] | A VERIFICAR. Arena (voto humano) lo ubica bien (Gemini 3.8 Flash: 9.º en texto, 14.º en español) y a Gemini 4 Argon mejor todavía (2.º en texto, 6.º en español, 3.º en creativa), pero EQ-Bench los pone al fondo (Argon 31.º, 1758; Flash 1748). Argon necesita Google AI Pro o Ultra en la app de Gemini. Si una segunda fuente en castellano confirma Arena, Argon pasa a plan B. | no | En el plan gratis Google usa lo que mandás para mejorar sus productos: sin código privado ni datos de clientes. |

Ranking (Arena (dataset en Hugging Face), 2026-10-29): 1. Gemini 4 Carbon (High); 2. Gemini 4 Argon (High); 3. Claude Opus 5.5 (High); 4. Claude Fable 5.1 (Max); 5. Claude Opus 5 (Max)

## Investigación web

Orden PROVISORIO: hay 3 fuentes independientes, pero no todos los planes se apoyan en ellas.

| Plan | Herramienta | Por qué | Datos privados | Condiciones |
|---|---|---|---|---|
| A | app web (ChatGPT deep research) (OpenAI, GPT-6 Astra) [a verificar] | 1.º en Arena búsqueda con GPT-5.6 Sol (1261); GPT-6 Astra, 7.º (1234). En BrowseComp está casi empatado con Claude y Perplexity (92,2 / 91,5 / 90,8 / 86): elegir por el cupo que quede. | sí |  |
| B | Codex (OpenAI, GPT-6.1 Sol) [a verificar] | Por consola: `codex --search exec --sandbox read-only`. Es lo que se puede automatizar desde una sesión. GPT-6.1 Sol es 8.º en Arena búsqueda (1233). | sí |  |
| C | app web (Gemini Deep Research) (Google, Deep Research (Google no dice qué modelo usa; reseñas: Gemini 3.1 Pro)) [a verificar] | A VERIFICAR. Es el peor ubicado de los medidos: Gemini 3.1 Pro con búsqueda es 15.º en Arena búsqueda (1209 contra 1261) y saca 72% en BrowseComp en la prueba de Parallel (contra 85-86% de GPT y Perplexity). Pero en DeepSearchQA le gana a Perplexity (77 contra 68%). Nadie midió el Deep Research de Google en BrowseComp. Gratis en la app con los planes de Google AI. | no | En el plan gratis Google usa lo que mandás para mejorar sus productos: sin código privado ni datos de clientes. |
| D | Perplexity (MCP oficial, desde una sesión de Claude) (Perplexity, Agent API (presets fast/medium/high; Sonar ya fue reemplazado)) [a verificar] | A VERIFICAR el lugar. Su buscador es el mejor medido por Artificial Analysis (BrowseComp 87 contra 74 del de OpenAI, mismo modelo; índice 80, empatado 1.º con Exa) y su Agent API saca 86% en BrowseComp en la prueba de Parallel (GPT-5.6 Sol: 85%); pero en DeepSearchQA queda en 68% (Gemini 77, GPT 85) y no figura en Arena búsqueda. Respuesta ya sintetizada y con citas (`perplexity_ask`, preset fast); `perplexity_search` da resultados crudos con fecha y dominio; `perplexity_research` es el profundo y caro. El MCP oficial (v1.0) ya corre sobre la Agent API. | sí | La API no entrena con lo que mandás por defecto; sin retención cero salvo acuerdo escrito. Claves y secretos nunca en la consulta. |

Ranking (Arena (dataset en Hugging Face), 2026-10-13): 1. gpt-5.6-sol-xhigh; 2. qwen3.8-max; 3. claude-opus-4-6-search; 4. gpt-5.5-search; 5. claude-fable-5.1-high

## Documentos largos

Orden PROVISORIO: hay 2 fuentes independientes, pero no todos los planes se apoyan en ellas.

| Plan | Herramienta | Por qué | Datos privados | Condiciones |
|---|---|---|---|---|
| A | Claude Code (Anthropic, Opus 5.5) | 85% en AA-LCR (el más alto de nuestros planes) y Claude llena el top de Arena documentos; Opus 5.5 lee hasta 1M de tokens. | sí |  |
| B | API / app web de Gemini (Google, Gemini 3.8 Flash) [a verificar] | A VERIFICAR. 1M de contexto y barato (US$0,75/3,75 por millón; precio de lanzamiento hasta el 31/12/2026, después se duplica, según reseñas): sirve para cargar el material. En AA-LCR saca 81% (Gemini 4 Argon, 80%: empate técnico) y GPT-6.1 Sol 83%: B por precio. Google mide a Argon mucho mejor en su propia prueba, que no cuenta para el orden. | no | Plan gratis: Google usa los datos. Con la API paga, mirá los términos (a verificar). |
| C | Codex (OpenAI, GPT-6.1 Sol) [a verificar] | 1M de contexto. 83% en AA-LCR, dos puntos sobre Gemini 3.8 Flash, pero a US$2/10 por millón. | sí |  |

Ranking (MRCR v2 a 1M (llm-stats), 2026-09-30): 1. Gemini 3.7 Flash

## Imágenes (generar y editar)

Orden PROVISORIO: hay 2 fuentes independientes, pero no todos los planes se apoyan en ellas.

| Plan | Herramienta | Por qué | Datos privados | Condiciones |
|---|---|---|---|---|
| A | app web (ChatGPT Images) (OpenAI, gpt-image-2.5) | Primero en Arena (texto a imagen 1427, edición 1517) y en Artificial Analysis, en las dos tablas. Claude no genera imágenes. | sí | No subas fotos de personas ni de clientes sin permiso. |
| B | app web de Gemini (Google, Nano Banana 2.1) [a verificar] | El mejor modelo de imágenes de Google: 5.º en Arena texto a imagen (1325) y 7.º en edición; cuesta una sexta parte por imagen que GPT Image 2.5 (Artificial Analysis). Nano Banana 2, el que figuraba acá, es 11.º (1266). Falta confirmar que la app de Gemini ya use el 2.1. | no | En el plan gratis Google usa lo que mandás para mejorar sus productos: sin código privado ni datos de clientes. |
| C | Adobe Firefly / Express (conector) (Adobe) [a verificar] | No figura en Arena ni en Artificial Analysis: sin medición independiente. Su ventaja es la licencia comercial clara. MAI-Image-2.6 y 2.7 de Microsoft rinden más que Nano Banana 2.1 en Arena (4.º en texto a imagen, 3.º en edición), pero no están integrados. | sí | Sin medición independiente: se usa por la licencia comercial, no por calidad. |

Ranking (Arena (dataset en Hugging Face), 2026-10-26): 1. GPT-Image-2.5 Sunburst; 2. GPT-Image-2.5 Flare; 3. GPT-Image-2 (Medium); 4. MAI-Image-2.6; 5. Gemini Nano Banana 2.1

## Imágenes (entender)

Orden PROVISORIO: hay 2 fuentes independientes, pero no todos los planes se apoyan en ellas.

| Plan | Herramienta | Por qué | Datos privados | Condiciones |
|---|---|---|---|---|
| A | Claude Code (Anthropic, Opus 5.5) | Primero en MMMU-Pro (87,7%) y 2.º en Arena visión (1321; el 1.º es Fable 5 con 1325, de pago aparte): entiende imágenes dentro de Claude Code. | sí |  |
| B | Codex (OpenAI, GPT-6.1 Sol) [a verificar] | A VERIFICAR. GPT-6.1 Sol saca 86,0% en MMMU-Pro, casi igual que Gemini 3.8 Flash (85,6%), pero es 29.º en Arena visión (1288). | sí |  |
| C | Antigravity (Google, Gemini 3.8 Flash) [a verificar] | A VERIFICAR. Arena visión lo pone 7.º (1315), 22 puestos sobre Codex, mientras MMMU-Pro los muestra empatados. Si una segunda fuente lo confirma, pasa a plan B. Gratis, como alternativa. | no | En el plan gratis Google usa lo que mandás para mejorar sus productos: sin código privado ni datos de clientes. |

Ranking (Arena (dataset en Hugging Face), 2026-10-29): 1. Claude Fable 5 (High); 2. Claude Opus 5.5 (High); 3. Claude Opus 5 (High); 4. Claude Fable 5.1 (Max); 5. Claude Opus 4.7

## Video

Orden PROVISORIO: hay 2 fuentes independientes, pero no todos los planes se apoyan en ellas.

| Plan | Herramienta | Por qué | Datos privados | Condiciones |
|---|---|---|---|---|
| A | app web de Gemini (Google, Gemini Omni 1.1 Flash) [a verificar] | A VERIFICAR el lugar. 1.º en Arena texto a video (1516) y 3.º en imagen a video de Artificial Analysis, pero 10.º en su texto a video (los diez primeros dentro de 46 puntos): las dos fuentes no coinciden arriba de todo. | no | Necesita un plan de Google AI para generar video en la app de Gemini. |
| B | API o plataformas con Wan 3.0 (Alibaba Model Studio; según reseñas, Runway y Pika) (Alibaba, Wan 3.0) [a verificar] | 1.º en texto a video de Artificial Analysis (1174) y 6.º en Arena (1476); 3.º en imagen a video en Arena y 4.º en Artificial Analysis. Reemplaza a Sora: OpenAI la discontinuó (app web el 2026-04-26, API el 2026-09-24). Para imagen a video, MiniMax H3 es 1.º en Arena y en Artificial Analysis (empatado). | no | Sin cuenta propia todavía: hay que contratarla. Proveedor chino: sin material de clientes. |
| C | Adobe Express (conector) (Adobe) [a verificar] | Cortes rápidos y redimensionado con el conector de Adobe (sin medición independiente). | sí | Sin medición independiente. |

Ranking (Arena (dataset en Hugging Face), 2026-09-22): 1. gemini-omni-1.1-flash; 2. gemini-omni-flash; 3. flux-3-video; 4. grok-imagine-video-1.5-agent; 5. dreamina-seedance-2.0-720p

## Transcripción de audio

Orden respaldado por 2 fuentes independientes.

| Plan | Herramienta | Por qué | Datos privados | Condiciones |
|---|---|---|---|---|
| A | API de ElevenLabs (ElevenLabs, Scribe v2) | 2,2% de error en Artificial Analysis (4.º entre todos) y 6.º en Open ASR; el mejor de nuestros tres. Ya no es el mejor del mercado: Fun-ASR de Alibaba (1,7%), MAI-Transcribe-2 de Microsoft (2,0%, en preview) y Voxtral Small de Mistral (2,1%) lo superan, pero ninguno está integrado. | sí |  |
| B | API de Gemini (Google, Gemini 3.5 Transcribe) [a verificar] | Segundo de nuestros tres (2,6% de error en Artificial Analysis), cerca de Scribe, pero cuesta más: US$5,00 por 1000 minutos contra US$3,67. | no | Plan gratis: Google usa los datos; con audios de clientes usá la API paga. |
| C | API de OpenAI (OpenAI, GPT Transcribe) [a verificar] | 3,3% de error y US$4,50 por 1000 minutos en Artificial Analysis. Ojo: los gpt-4o-*transcribe se apagan el 2027-02-26. | sí |  |
| D | API de Mistral (Mistral, Voxtral Small Transcribe 3) [a verificar] | 2,1% de error en Artificial Analysis (3.º entre todos); Voxtral Mini Transcribe 3 saca 2,2% a unos US$3,5 por 1000 minutos. Sin integración todavía y sin dato propio para castellano. | no | Sin revisar privacidad ni cuenta: hay que contratarla antes de usarlo. |

Ranking (Artificial Analysis, speech to text (a verificar), 2026-09-30): 1. ElevenLabs Scribe v2; 2. Gemini 3.5 Transcribe; 3. GPT Transcribe

## Voz (texto a voz)

Orden PROVISORIO: 1 de 2 fuentes independientes.

| Plan | Herramienta | Por qué | Datos privados | Condiciones |
|---|---|---|---|---|
| A | API de ElevenLabs (ElevenLabs, Eleven v4 / Eleven v4 Turbo) [a verificar] | 1.º y 2.º en la arena de voces de Artificial Analysis (Turbo 1334, v4 1321-1332); Gemini 3.8 Flash TTS queda unos 50 puntos abajo. Cuesta US$80 por millón de caracteres (Turbo, US$40). | sí | Orden a verificar: la tabla de Artificial Analysis no se pudo abrir directamente. |
| B | API de OpenAI (OpenAI, gpt-realtime-2.1-mini (reemplaza a tts-1)) [a verificar] | A VERIFICAR el lugar. Los modelos de voz de OpenAI (tts-1, tts-1-hd, gpt-4o-mini-tts) se apagan el 2027-01-06 y su reemplazo todavía no aparece medido en la arena. El mejor OpenAI que mide Artificial Analysis (TTS-1 HD, 1105) queda 170 puntos debajo de Gemini 3.8 Flash TTS. Si el reemplazo no mide mejor, Gemini pasa a plan B. | sí |  |
| C | API de Gemini (Google, Gemini 3.8 Flash TTS) [a verificar] | 4.º-5.º en la arena de Artificial Analysis (1275-1280) a US$16,50 por millón de caracteres, cinco veces menos que Eleven v4. Ojo: con las mismas voces para todos cae al 13.º; parte del puntaje son las voces que trae. | no | En el plan gratis Google usa lo que mandás para mejorar sus productos: sin código privado ni datos de clientes. |

## Datos y planillas

Orden PROVISORIO: hay 2 fuentes independientes, pero no todos los planes se apoyan en ellas.

| Plan | Herramienta | Por qué | Datos privados | Condiciones |
|---|---|---|---|---|
| A | Claude Code (Anthropic, Sonnet 5.5) | Lidera el Vals Index v2.2 (70,85%) y es 3.º en modelado de Excel (75,9%, a 0,8 del 1.º); 2.º en AnalystAgent de Artificial Analysis. Opus 5.5 si el cálculo es del negocio. | sí |  |
| B | Codex (OpenAI, GPT-6.1 Sol) [a verificar] | A VERIFICAR. Lee mejor documentos con números (GDP.pdf 31% contra 26% de Claude), pero en Vals queda 22.º en finanzas (55,8%), debajo de Gemini 3.8 Flash (60,5%); AutomationBench lo pone en 65%, sobre Flash (60%). GPT-6.1 Terra, de la misma familia, saca 73,3% en Excel a US$0,56 por prueba. | sí |  |
| C | API / app web de Gemini (Google, Gemini 3.8 Flash) [a verificar] | A VERIFICAR. 72,9% en modelado de Excel (8.º) y 60,5% en el índice de finanzas de Vals. Barato para volumen; Gemini 4 Argon rinde más (74,8% en Excel, 78% en AutomationBench) por US$2/10. | no | En el plan gratis Google usa lo que mandás para mejorar sus productos: sin código privado ni datos de clientes. |

## Tareas mecánicas baratas

Orden PROVISORIO: hay 3 fuentes independientes, pero no todos los planes se apoyan en ellas.

| Plan | Herramienta | Por qué | Datos privados | Condiciones |
|---|---|---|---|---|
| A | API de OpenAI (OpenAI, GPT-6 Luna) | US$0,10/0,50 por millón y lo más barato por tarea (US$0,07 en Artificial Analysis, tres veces menos que Haiku 5.5); rinde igual o mejor en Excel (70,0% contra 65,5%) y en revisión de código (43,7 contra 38,8). Haiku saca más en el índice (43 contra 38) y en terminal. | sí |  |
| B | API de Gemini (Google, Gemini Flash-Lite) [a verificar] | Con plan gratis (pero ver la condición). No figura en las fuentes consultadas hoy: a verificar contra Luna y Haiku. | no | En el plan gratis Google usa lo que mandás para mejorar sus productos: sin código privado ni datos de clientes. |
| C | Claude Code (Anthropic, Haiku 5.5) [a verificar] | Si tiene que quedar dentro de Claude Code: Haiku 5.5 (US$0,10/0,50 por millón hasta 100.000 tokens de prompt; después cuesta cinco veces más). El de mejor nota entre los baratos (43 en el índice), pero escribe unas tres veces más y cuesta US$0,21 por tarea. | sí |  |

## Agentes de tarea larga

Orden respaldado por 2 fuentes independientes.

| Plan | Herramienta | Por qué | Datos privados | Condiciones |
|---|---|---|---|---|
| A | Claude Code (Anthropic, Opus 5.5) | Primero en Arena Agent (20,9) y en Terminal-Bench 4.0 (64,8%). Fable 5.1 (más caro) ya no es el primero: 4.º en Arena Agent (13,4) y 5.º en Terminal-Bench (57,9%), debajo de Opus 5.5 y Sonnet 5.5. | sí |  |
| B | Codex (OpenAI, GPT-6.1 Sol) | 6.º en Arena Agent (12,5; GPT-6 Astra, 5.º con 13,0) y 58,2% en Terminal-Bench 4.0, igual que Astra y a menos de una quinta parte del costo en esa tabla. | sí |  |
| C | Antigravity (Google, Gemini 4 Argon) [a verificar] | 7.º en Arena Agent (10,7) y detrás de Codex en el índice de agentes. Gemini 4 Carbon es 2.º en Arena Agent (16,0) pero todavía no tiene acceso general: cuando salga pasa a plan B. Alternativa para tareas acotadas. | no | Gemini 4 Argon en Antigravity es solo para suscriptores de Google AI Ultra (en la app de Gemini, desde AI Pro; por API, US$2/10 por millón hasta el 30/11/2026 y US$4/20 después, según Google). Con otra cuenta, Antigravity usa el mejor Gemini que tenga (delegar.py lo resuelve solo). En el plan gratis Google usa lo que mandás para mejorar sus productos: sin código privado ni datos de clientes. |

Ranking (Arena Agent (dataset en Hugging Face; puntaje ×100), 2026-10-28): 1. Claude Opus 5.5 (Max); 2. Gemini 4 Carbon (High); 3. Claude Sonnet 5.5 (Max); 4. Claude Fable 5.1 (Max); 5. GPT-6 Astra (Max)

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
