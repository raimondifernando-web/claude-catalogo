---
name: generate-image
description: Generate or edit images using AI models (FLUX, Gemini). Use for general-purpose image generation including photos, illustrations, artwork, visual assets, concept art, and any image that isn't a technical diagram or schematic. For flowcharts, circuits, pathways, and technical diagrams, use the scientific-schematics skill instead.
sync: cowork
---

## Antes de usar esta skill — requisitos (chequeo automático)

Esta skill necesita programas de fondo que no vienen con Claude Code. **Antes de ejecutar cualquier script, verificá con Bash** y, si falta algo, NO muestres el error de terminal: respondé con el mensaje indicado y ofrecé la alternativa.

| Necesita | Cómo verificar | Si falta, respondé |
|---|---|---|
| Python 3 | `command -v python3` | «Para esto hace falta instalar **Python 3 (Herramientas de línea de comandos de Apple)**. Está en tu portal, fase «Herramientas de base».» |
| librería `requests` | `python3 -c "import requests"` | «Para esto hace falta instalar **requests (librería de Python)**. Está en tu portal, fase «Herramientas de base».» |
| clave `OPENROUTER_API_KEY` (servicio pago del usuario) | `test -n "$OPENROUTER_API_KEY" || grep -qc "^OPENROUTER_API_KEY=" .env 2>/dev/null` | «Para esto hace falta instalar **una cuenta y clave de OpenRouter (ver portal, fase «Claves y servicios»)**. Está en tu portal, fase «Herramientas de base».» |

Nunca pidas que peguen la clave en el chat: se configura como variable de entorno o en `.env`, y solo verificás que exista.

El chequeo completo para el cliente es `bash ~/.claude/plugins/marketplaces/claude-catalogo/scripts/chequeo.sh` (ver `docs/CHEQUEO.md` del catálogo).

# Generate Image

Generate and edit high-quality images using OpenRouter's image generation models including FLUX.2 Pro and Gemini 3 Pro.

## When to Use This Skill

**Use generate-image for:**
- Photos and photorealistic images
- Artistic illustrations and artwork
- Concept art and visual concepts
- Visual assets for presentations or documents
- Image editing and modifications
- Any general-purpose image generation needs

**Use scientific-schematics instead for:**
- Flowcharts and process diagrams
- Circuit diagrams and electrical schematics
- Biological pathways and signaling cascades
- System architecture diagrams
- CONSORT diagrams and methodology flowcharts
- Any technical/schematic diagrams

## Quick Start

Use the `scripts/generate_image.py` script to generate or edit images:

```bash
# Generate a new image
python scripts/generate_image.py "A beautiful sunset over mountains"

# Edit an existing image
python scripts/generate_image.py "Make the sky purple" --input photo.jpg
```

This generates/edits an image and saves it as `generated_image.png` in the current directory.

## API Key Setup

**CRITICAL**: The script requires an OpenRouter API key. Before running, check if the user has configured their API key:

1. Look for a `.env` file in the project directory or parent directories
2. Check for `OPENROUTER_API_KEY=<key>` in the `.env` file
3. If not found, inform the user they need to:
   - Create a `.env` file with `OPENROUTER_API_KEY=your-api-key-here`
   - Or set the environment variable: `export OPENROUTER_API_KEY=your-api-key-here`
   - Get an API key from: https://openrouter.ai/keys

The script will automatically detect the `.env` file and provide clear error messages if the API key is missing.

## Model Selection

**Default model**: `google/gemini-3-pro-image-preview` (high quality, recommended)

**Available models for generation and editing**:
- `google/gemini-3-pro-image-preview` - High quality, supports generation + editing
- `black-forest-labs/flux.2-pro` - Fast, high quality, supports generation + editing

**Generation only**:
- `black-forest-labs/flux.2-flex` - Fast and cheap, but not as high quality as pro

Select based on:
- **Quality**: Use gemini-3-pro or flux.2-pro
- **Editing**: Use gemini-3-pro or flux.2-pro (both support image editing)
- **Cost**: Use flux.2-flex for generation only

## Common Usage Patterns

### Basic generation
```bash
python scripts/generate_image.py "Your prompt here"
```

### Specify model
```bash
python scripts/generate_image.py "A cat in space" --model "black-forest-labs/flux.2-pro"
```

### Custom output path
```bash
python scripts/generate_image.py "Abstract art" --output artwork.png
```

### Edit an existing image
```bash
python scripts/generate_image.py "Make the background blue" --input photo.jpg
```

### Edit with a specific model
```bash
python scripts/generate_image.py "Add sunglasses to the person" --input portrait.png --model "black-forest-labs/flux.2-pro"
```

### Edit with custom output
```bash
python scripts/generate_image.py "Remove the text from the image" --input screenshot.png --output cleaned.png
```

### Multiple images
Run the script multiple times with different prompts or output paths:
```bash
python scripts/generate_image.py "Image 1 description" --output image1.png
python scripts/generate_image.py "Image 2 description" --output image2.png
```

## Script Parameters

- `prompt` (required): Text description of the image to generate, or editing instructions
- `--input` or `-i`: Input image path for editing (enables edit mode)
- `--model` or `-m`: OpenRouter model ID (default: google/gemini-3-pro-image-preview)
- `--output` or `-o`: Output file path (default: generated_image.png)
- `--api-key`: OpenRouter API key (overrides .env file)

## Example Use Cases

### For Scientific Documents
```bash
# Generate a conceptual illustration for a paper
python scripts/generate_image.py "Microscopic view of cancer cells being attacked by immunotherapy agents, scientific illustration style" --output figures/immunotherapy_concept.png

# Create a visual for a presentation
python scripts/generate_image.py "DNA double helix structure with highlighted mutation site, modern scientific visualization" --output slides/dna_mutation.png
```

### For Presentations and Posters
```bash
# Title slide background
python scripts/generate_image.py "Abstract blue and white background with subtle molecular patterns, professional presentation style" --output slides/background.png

# Poster hero image
python scripts/generate_image.py "Laboratory setting with modern equipment, photorealistic, well-lit" --output poster/hero.png
```

### For General Visual Content
```bash
# Website or documentation images
python scripts/generate_image.py "Professional team collaboration around a digital whiteboard, modern office" --output docs/team_collaboration.png

# Marketing materials
python scripts/generate_image.py "Futuristic AI brain concept with glowing neural networks" --output marketing/ai_concept.png
```

## Error Handling

The script provides clear error messages for:
- Missing API key (with setup instructions)
- API errors (with status codes)
- Unexpected response formats
- Missing dependencies (requests library)

If the script fails, read the error message and address the issue before retrying.

## Notes

- Images are returned as base64-encoded data URLs and automatically saved as PNG files
- The script supports both `images` and `content` response formats from different OpenRouter models
- Generation time varies by model (typically 5-30 seconds)
- For image editing, the input image is encoded as base64 and sent to the model
- Supported input image formats: PNG, JPEG, GIF, WebP
- Check OpenRouter pricing for cost information: https://openrouter.ai/models

## Image Editing Tips

- Be specific about what changes you want (e.g., "change the sky to sunset colors" vs "edit the sky")
- Reference specific elements in the image when possible
- For best results, use clear and detailed editing instructions
- Both Gemini 3 Pro and FLUX.2 Pro support image editing through OpenRouter

## Integration with Other Skills

- **scientific-schematics**: Use for technical diagrams, flowcharts, circuits, pathways
- **generate-image**: Use for photos, illustrations, artwork, visual concepts
- **scientific-slides**: Combine with generate-image for visually rich presentations
- **latex-posters**: Use generate-image for poster visuals and hero images
