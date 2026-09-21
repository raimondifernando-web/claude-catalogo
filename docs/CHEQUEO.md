# Chequeo de requisitos — un comando y listo

¿Tu computadora tiene lo que las skills necesitan? Este comando lo revisa **sin instalar ni modificar nada** y sin mostrar ninguna clave.
Devuelve una lista con ✅ OK · ❌ FALTA · ⚪ OPCIONAL y, para cada cosa que falta, el comando exacto para instalarla.

## Cómo correrlo (Mac)
1. Abrí la app **Terminal** (Spotlight → escribí "Terminal").
2. Pegá esta línea y apretá Enter:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/raimondifernando-web/claude-catalogo/main/scripts/chequeo.sh)
```

Si ya tenés el catálogo agregado, también funciona sin internet:

```bash
bash ~/.claude/plugins/marketplaces/claude-catalogo/scripts/chequeo.sh
```

3. Sacale una captura a la pantalla (⌘⇧4) y pegala en tu portal, fase **«Herramientas de base»**.

## Cómo leerlo
| Marca | Qué significa | Qué hacés |
|---|---|---|
| ✅ OK | Está instalado | Nada |
| ❌ FALTA | Lo usan varias skills; sin esto fallan | Corré el comando que aparece debajo (o pedile a tu consultor) |
| ⚪ OPCIONAL | Solo para una función puntual (leer imágenes escaneadas, exportar diagramas a PNG, imágenes con IA, transcribir audio) | Solo si vas a usar esa función |

## Qué revisa
1. **Base**: Claude Code, el catálogo agregado, qué plugins tenés instalados.
2. **Herramientas de base**: Python 3, pip, markitdown, pandas/openpyxl.
3. **Opcionales**: Tesseract, Mermaid CLI, Node.js, pnpm/npm, requests, openai.
4. **Claves de servicios pagos**: solo verifica que `OPENROUTER_API_KEY` / `OPENAI_API_KEY` existan. **Nunca muestra el valor.**

El detalle de qué skill necesita qué está en `plugins/<plugin>/requisitos.md`.

## Windows
Próximamente. Mientras tanto, tu consultor te pasa los pasos.
