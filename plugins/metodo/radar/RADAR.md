# Radar de modelos

> Generado desde `RADAR.yaml` (`radar.py md`). No se edita a mano. Última actualización: **2026-10-03**.
> `[a verificar]` = dato de la investigación que todavía no se leyó de primera mano.

Para elegir: `radar.py elegir <categoría>`; si falta el plan A te devuelve el B o el C.

## Desarrollo (programar)

| Plan | Herramienta | Por qué | Datos privados | Condiciones |
|---|---|---|---|---|
| A | Claude Code (Anthropic, Opus 5.5) [a verificar] | El mejor en Terminal-Bench 4.0 (66,4% contra 57,9% de GPT-6 Astra; dato del fabricante). Sonnet 5.5 para lo rutinario. | sí |  |
| B | Codex (OpenAI, GPT-6.1 Sol) [a verificar] | Segundo mejor para programar y el modelo por defecto de Codex; otro modelo encuentra otros errores. | sí | Con cuenta gratis, revisá la privacidad de la cuenta antes de mandar código privado. |
| C | Antigravity (Google, Gemini 3.8 Flash) [a verificar] | Gratis y alcanza para tareas acotadas. | no | En el plan gratis Google usa lo que mandás para mejorar sus productos: sin código privado ni datos de clientes. |

## Revisión de código y seguridad

| Plan | Herramienta | Por qué | Datos privados | Condiciones |
|---|---|---|---|---|
| A | Claude Code (Anthropic, Opus 5.5) [a verificar] | /code-review y /security-review con Opus 5.5; CR-bench: Claude Code 32,1% contra Codex 20,1% (a verificar). | sí |  |
| B | Codex (OpenAI, GPT-6.1 Sol) [a verificar] | Segunda revisión con un modelo distinto: `codex exec --sandbox read-only`. Encuentra errores que el primero no ve. | sí |  |
| C | Antigravity (Google, Gemini 3.1 Pro) [a verificar] | Revisión estática sin ejecutar nada: `agy --mode plan -p=...`. | no | En el plan gratis Google usa lo que mandás para mejorar sus productos: sin código privado ni datos de clientes. |

## Diseño (UI web, presentaciones)

| Plan | Herramienta | Por qué | Datos privados | Condiciones |
|---|---|---|---|---|
| A | Claude Code (Anthropic, Opus 5.5) [a verificar] | Primero en Arena WebDev (a verificar); con la skill de diseño del plugin que corresponda. | sí |  |
| B | Codex (OpenAI, GPT-6.1 Sol) [a verificar] | Segundo en Arena WebDev con GPT-6 Astra (a verificar); sirve para una segunda propuesta. | sí |  |
| C | Antigravity (Google, Gemini 3.8 Flash) [a verificar] | Gratis para bocetos; no para material de clientes. | no | En el plan gratis Google usa lo que mandás para mejorar sus productos: sin código privado ni datos de clientes. |

## Escritura en castellano

| Plan | Herramienta | Por qué | Datos privados | Condiciones |
|---|---|---|---|---|
| A | Claude Code (Anthropic, Opus 5.5) [a verificar] | Primero en Arena texto según el posteo oficial (hay una lectura del dataset que dice otra cosa); Sonnet 5.5 para volumen. Sin dato del filtro «Spanish». | sí |  |
| B | Codex (OpenAI, GPT-6.1 Sol) [a verificar] | Alternativa sólida en texto. | sí |  |
| C | app web de Gemini (Google, Gemini 3.8 Flash) [a verificar] | Para borradores sin datos sensibles. | no | En el plan gratis Google usa lo que mandás para mejorar sus productos: sin código privado ni datos de clientes. |

Ranking (Arena texto (contradictorio: a verificar), 2026-09-25): 1. Claude Opus 5.5 (High)

## Investigación web

| Plan | Herramienta | Por qué | Datos privados | Condiciones |
|---|---|---|---|---|
| A | app web (ChatGPT deep research) (OpenAI, GPT-6 Astra) [a verificar] | BrowseComp: casi empatado con Sonnet/Opus (92,2 / 91,5 / 90,8): elegir por el cupo que quede. | sí |  |
| B | Codex (OpenAI, GPT-6.1 Sol) [a verificar] | Por consola: `codex --search exec --sandbox read-only`. Es lo que se puede automatizar desde una sesión. | sí |  |
| C | app web (Gemini Deep Research) (Google, Gemini 3.8 Flash) [a verificar] | 5 informes gratis por mes. | no | En el plan gratis Google usa lo que mandás para mejorar sus productos: sin código privado ni datos de clientes. |

Ranking (BrowseComp (README de steel-dev), 2026-10-03): 1. GPT-5.6 Sol; 2. GPT-6 Astra; 3. Claude Opus 5

## Documentos largos

| Plan | Herramienta | Por qué | Datos privados | Condiciones |
|---|---|---|---|---|
| A | API / app web de Gemini (Google, Gemini 3.8 Flash) [a verificar] | 1M de contexto y barato (US$0,75/3,75 por millón): sirve para cargar el material. | no | Plan gratis: Google usa los datos. Con la API paga, mirá los términos (a verificar). |
| B | Claude Code (Anthropic, Opus 5.5) [a verificar] | 1M de contexto para analizar dentro de Claude Code. | sí |  |
| C | Codex (OpenAI, GPT-6.1 Sol) [a verificar] | 1M de contexto. | sí |  |

Ranking (MRCR v2 a 1M (llm-stats), 2026-09-30): 1. Gemini 3.7 Flash

## Imágenes (generar y editar)

| Plan | Herramienta | Por qué | Datos privados | Condiciones |
|---|---|---|---|---|
| A | app web (ChatGPT Images) (OpenAI, gpt-image-2.5) [a verificar] | Primero en Arena texto-a-imagen y edición (a verificar). Claude no genera imágenes. | sí | No subas fotos de personas ni de clientes sin permiso. |
| B | app web de Gemini (Google, Nano Banana 2 (Gemini 3.1 Flash Image)) [a verificar] | Gratis en la app de Gemini. | no | En el plan gratis Google usa lo que mandás para mejorar sus productos: sin código privado ni datos de clientes. |
| C | Adobe Firefly / Express (conector) (Adobe) [a verificar] | Sin dato en la investigación: alternativa con licencia comercial clara (a verificar). | sí | A completar en la próxima revisión. |

## Imágenes (entender)

| Plan | Herramienta | Por qué | Datos privados | Condiciones |
|---|---|---|---|---|
| A | Claude Code (Anthropic, Opus 5.5) [a verificar] | Primero en Arena visión con Claude Fable 5 (a verificar); Opus 5.5 entiende imágenes dentro de Claude Code. | sí |  |
| B | Codex (OpenAI, GPT-6.1 Sol) [a verificar] | Alternativa. | sí |  |
| C | Antigravity (Google, Gemini 3.8 Flash) [a verificar] | Alternativa gratis. | no | En el plan gratis Google usa lo que mandás para mejorar sus productos: sin código privado ni datos de clientes. |

## Video

| Plan | Herramienta | Por qué | Datos privados | Condiciones |
|---|---|---|---|---|
| A | app web de Gemini (Google, Veo (a verificar)) [a verificar] | Sin dato en la investigación: pendiente de cargar desde el ranking de video de Arena. | no | Pendiente de verificar. |
| B | app web (Sora) (OpenAI, Sora (a verificar)) [a verificar] | Sin dato en la investigación. | no | Pendiente de verificar. |
| C | Adobe Express (conector) (Adobe) [a verificar] | Cortes rápidos y redimensionado con el conector de Adobe (a verificar). | sí | Pendiente de verificar. |

## Transcripción de audio

| Plan | Herramienta | Por qué | Datos privados | Condiciones |
|---|---|---|---|---|
| A | API de Gemini (Google, Gemini 3.5 Transcribe) [a verificar] | 2,6% de error por palabra en inglés (Artificial Analysis); sin dato propio en castellano. | no | Plan gratis: Google usa los datos; con audios de clientes usá la API paga. |
| B | API de OpenAI (OpenAI, GPT Transcribe) [a verificar] | 3,3% de error. Ojo: los gpt-4o-*transcribe se apagan el 2027-02-26. | sí |  |
| C | API de ElevenLabs (ElevenLabs, Scribe v2) [a verificar] | El mejor de las APIs comerciales (2,2%), pero es un proveedor aparte. | sí |  |

Ranking (Artificial Analysis, speech to text (a verificar), 2026-09-30): 1. ElevenLabs Scribe v2; 2. Gemini 3.5 Transcribe; 3. GPT Transcribe

## Voz (texto a voz)

| Plan | Herramienta | Por qué | Datos privados | Condiciones |
|---|---|---|---|---|
| A | API de ElevenLabs (ElevenLabs) [a verificar] | Sin dato en la investigación: es la herramienta de voz conectada hoy (a verificar contra el ranking de TTS de Arena). | sí | Pendiente de verificar. |
| B | API de OpenAI (OpenAI) [a verificar] | Sin dato en la investigación. | sí | Pendiente de verificar. |
| C | API de Gemini (Google) [a verificar] | Sin dato en la investigación. | no | En el plan gratis Google usa lo que mandás para mejorar sus productos: sin código privado ni datos de clientes. |

## Datos y planillas

| Plan | Herramienta | Por qué | Datos privados | Condiciones |
|---|---|---|---|---|
| A | Claude Code (Anthropic, Sonnet 5.5) [a verificar] | Alcanza para planillas y análisis; Opus 5.5 si el cálculo es delicado. Sin dato de ranking propio (a verificar). | sí |  |
| B | Codex (OpenAI, GPT-6.1 Sol) [a verificar] | Alternativa. | sí |  |
| C | API / app web de Gemini (Google, Gemini 3.8 Flash) [a verificar] | Barato para volumen. | no | En el plan gratis Google usa lo que mandás para mejorar sus productos: sin código privado ni datos de clientes. |

## Tareas mecánicas baratas

| Plan | Herramienta | Por qué | Datos privados | Condiciones |
|---|---|---|---|---|
| A | API de OpenAI (OpenAI, GPT-6 Luna) [a verificar] | US$0,10/0,50 por millón: lo más barato. | sí |  |
| B | API de Gemini (Google, Gemini Flash-Lite) [a verificar] | Con plan gratis (pero ver la condición). | no | En el plan gratis Google usa lo que mandás para mejorar sus productos: sin código privado ni datos de clientes. |
| C | Claude Code (Anthropic, Haiku 4.5) [a verificar] | Si tiene que quedar dentro de Claude Code. Ojo: no se retira antes del 2026-10-15. | sí |  |

## Agentes de tarea larga

| Plan | Herramienta | Por qué | Datos privados | Condiciones |
|---|---|---|---|---|
| A | Claude Code (Anthropic, Opus 5.5) [a verificar] | Mejor en Terminal-Bench 4.0; para tareas de horas conviene METR time horizon (a verificar). | sí |  |
| B | Codex (OpenAI, GPT-6.1 Sol) [a verificar] | Agente de consola con sandbox; buen segundo. | sí |  |
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
