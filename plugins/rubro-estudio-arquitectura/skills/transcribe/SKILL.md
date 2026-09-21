---
name: "transcribe"
description: "Transcribe audio files to text with optional diarization and known-speaker hints. Use when a user asks to transcribe speech from audio/video, extract text from recordings, or label speakers in interviews or meetings."
author: openai
sync: no
---

## Antes de usar esta skill — requisitos (chequeo automático)

Esta skill necesita programas de fondo que no vienen con Claude Code. **Antes de ejecutar cualquier script, verificá con Bash** y, si falta algo, NO muestres el error de terminal: respondé con el mensaje indicado y ofrecé la alternativa.

| Necesita | Cómo verificar | Si falta, respondé |
|---|---|---|
| Python 3 | `command -v python3` | «Para esto hace falta instalar **Python 3 (Herramientas de línea de comandos de Apple)**. Está en tu portal, fase «Herramientas de base».» |
| librería `openai` | `python3 -c "import openai"` | «Para esto hace falta instalar **openai (librería de Python)**. Está en tu portal, fase «Herramientas de base».» |
| clave `OPENAI_API_KEY` (servicio pago del usuario) | `test -n "$OPENAI_API_KEY"` | «Para esto hace falta instalar **una cuenta y clave de OpenAI (ver portal, fase «Claves y servicios»)**. Está en tu portal, fase «Herramientas de base».» |

Nunca pidas que peguen la clave en el chat. Alternativa sin instalar nada: el usuario puede grabar con la app Notas de Voz de Apple, que transcribe sola, y pegar el texto.

El chequeo completo para el cliente es `bash ~/.claude/plugins/marketplaces/claude-catalogo/scripts/chequeo.sh` (ver `docs/CHEQUEO.md` del catálogo).

# Audio Transcribe

Transcribe audio using OpenAI, with optional speaker diarization when requested. Prefer the bundled CLI for deterministic, repeatable runs.

## Workflow
1. Collect inputs: audio file path(s), desired response format (text/json/diarized_json), optional language hint, and any known speaker references.
2. Verify `OPENAI_API_KEY` is set. If missing, ask the user to set it locally (do not ask them to paste the key).
3. Run the bundled `transcribe_diarize.py` CLI with sensible defaults (fast text transcription).
4. Validate the output: transcription quality, speaker labels, and segment boundaries; iterate with a single targeted change if needed.
5. Save outputs under `output/transcribe/` when working in this repo.

## Decision rules
- Default to `gpt-4o-mini-transcribe` with `--response-format text` for fast transcription.
- If the user wants speaker labels or diarization, use `--model gpt-4o-transcribe-diarize --response-format diarized_json`.
- If audio is longer than ~30 seconds, keep `--chunking-strategy auto`.
- Prompting is not supported for `gpt-4o-transcribe-diarize`.

## Output conventions
- Use `output/transcribe/<job-id>/` for evaluation runs.
- Use `--out-dir` for multiple files to avoid overwriting.

## Dependencies (install if missing)
Prefer `uv` for dependency management.

```
uv pip install openai
```
If `uv` is unavailable:
```
python3 -m pip install openai
```

## Environment
- `OPENAI_API_KEY` must be set for live API calls.
- If the key is missing, instruct the user to create one in the OpenAI platform UI and export it in their shell.
- Never ask the user to paste the full key in chat.

## Skill path (set once)

```bash
export CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
export TRANSCRIBE_CLI="$CODEX_HOME/skills/transcribe/scripts/transcribe_diarize.py"
```

User-scoped skills install under `$CODEX_HOME/skills` (default: `~/.codex/skills`).

## CLI quick start
Single file (fast text default):
```
python3 "$TRANSCRIBE_CLI" \
  path/to/audio.wav \
  --out transcript.txt
```

Diarization with known speakers (up to 4):
```
python3 "$TRANSCRIBE_CLI" \
  meeting.m4a \
  --model gpt-4o-transcribe-diarize \
  --known-speaker "Alice=refs/alice.wav" \
  --known-speaker "Bob=refs/bob.wav" \
  --response-format diarized_json \
  --out-dir output/transcribe/meeting
```

Plain text output (explicit):
```
python3 "$TRANSCRIBE_CLI" \
  interview.mp3 \
  --response-format text \
  --out interview.txt
```

## Reference map
- `references/api.md`: supported formats, limits, response formats, and known-speaker notes.
