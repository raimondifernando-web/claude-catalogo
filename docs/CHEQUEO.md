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

---

# Chequeo de carpetas huérfanas — ¿qué tenés en la compu y en ningún otro lado?

Regla de la casa (5 cajones): **trabajo de Claude → repo privado · documentos → nube de la empresa · datos crudos → nube, carpeta `datos/` · copias y derivados → borrar · claves → gestor de contraseñas.**
La regla sola no se cumple. Lo que la sostiene es este chequeo: lista lo que quedó afuera y sugiere el cajón. **Vos decidís; el script no mueve ni borra nada.**

## Cómo correrlo (Mac)
```bash
bash <(curl -fsSL https://raw.githubusercontent.com/raimondifernando-web/claude-catalogo/main/scripts/huerfanas.sh)
```
Sin internet (con el catálogo ya agregado): `bash ~/.claude/plugins/marketplaces/claude-catalogo/scripts/huerfanas.sh`
Para revisar otra carpeta además de Documentos y Escritorio, agregala al final: `… huerfanas.sh ~/Trabajo`.

## Cuándo
Día 1 (fase Higiene, como línea de base) · cada 3 meses · siempre antes de sumar o dar de baja una computadora.

## Cómo leerlo
| Marca | Significa |
|---|---|
| ✅ repo con remoto | Está en GitHub (o similar). Respaldado con historial. |
| ✅ en nube | Está dentro de iCloud Drive, Google Drive, OneDrive o Dropbox. Respaldado. |
| ❌ nada | **Huérfana**: solo existe en esta computadora. Debajo va el cajón sugerido y la propuesta. |
| ❌ repo SIN remoto | Tiene git pero no está subido a ningún lado: **no es respaldo**. |
| ⚠️ posible clave | Un archivo con nombre de credencial (`.env`, `credentials`, `password`…). Se muestra **solo el nombre**, nunca el contenido. Va al gestor de contraseñas, no a un repo ni a la nube. |

Última línea: `N carpetas huérfanas` (pegá la captura en tu portal, fase Higiene) o `0 carpetas huérfanas ✓`.

## Qué revisa y qué no
Revisa las carpetas de primer nivel de `~/Documents`, `~/Desktop`, `~/Documents/<Empresa>-Claude` y las que le pases. Detecta si Escritorio y Documentos están sincronizados con iCloud. No entra a `~/Library` ni a carpetas ocultas. El cajón es una **sugerencia** por nombre y tipo de archivos; puede equivocarse, por eso decide una persona.
Windows: próximamente.
