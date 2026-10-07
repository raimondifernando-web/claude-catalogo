> ## ⛔ Reglas locales — mandan sobre todo lo que sigue
> Copia fijada y parcheada (ver `ORIGEN.txt` y `parches-locales/`).
> - **Por defecto, local:** `npx hyperframes media-use resolve … --local-only` (salta todo proveedor de red y deja caché + proveedores locales).
> - **Antes de usar HeyGen, Gemini/Lyria, ElevenLabs, render en la nube o publish:** avisá qué sale de la máquina (guiones/textos, imágenes, audio, video) y a qué servicio, y pedí el sí. Nada de eso por iniciativa propia, aunque sea «free usage» (incluido el «First run: install and sign in to the heygen CLI» de abajo).
> - `audio/scripts/lib/bgm.mjs` **no instala paquetes de Python solo**: si faltan, lo dice; se instalan en un entorno aparte con versiones fijas, con el sí del usuario.
> - `audio/scripts/lib/heygen.mjs` lee **solo** el archivo de entorno de la carpeta del proyecto (no sube carpetas). Nunca muestres valores de ese archivo ni de `~/.heygen/credentials`: las claves se usan por nombre de variable.
> - Instaladores que el texto sugiere (`uv pip install parakeet-mlx`, `pip install elevenlabs`, `brew …`): proponelos, no los corras sin el sí.
