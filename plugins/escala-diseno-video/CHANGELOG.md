# escala-diseno-video — qué cambia para vos

## 0.1.3 — 2026-09-28
- **Set de video de HyperFrames al día** con la versión nueva del autor (`93ab289`). Lo que cambia para vos: la transcripción de audio (`media-use`) avisa mejor cuando falla y puede usar el modelo Parakeet del propio CLI si lo instalás (son unos 640 MB, te lo pregunta antes). Las demás skills solo suman una nota para un modo nuevo, «plugin», que este paquete no usa.
- Siguen igual las reglas propias: no se actualizan solas, lo local va primero y te pregunta antes de mandar algo a un servicio en la nube.

## 0.1.2 — 2026-09-27
- Formato: la descripción de `hyperframes-audio` cumple las reglas de claude.ai (hace lo mismo que antes). Así también se puede usar en Cowork.

## 0.1.1 — 2026-09-27
- **Corrección:** la 0.1.0 decía que HyperFrames venía con la telemetría apagada. No es así: se apaga cuando cargás `HYPERFRAMES_NO_TELEMETRY=1` y `DO_NOT_TRACK=1` en el bloque `env` de tu `~/.claude/settings.json` (paso del portal; detalle en `requisitos.md`).
- **Nueva skill `video-content-strategist`:** estrategia de video para redes y YouTube (qué publicar, guiones, ganchos, formatos). No necesita nada extra.

## 0.1.0 — 2026-09-27
- **Paquete nuevo, para hacer piezas visuales con Claude** sin saber diseño: presentaciones que se usan como un PowerPoint, animaciones y videos cortos (MP4/GIF), prototipos de pantallas en los que se puede hacer clic, infografías y arte generativo.
- **`huashu-design`** (con su música de fondo y efectos de sonido): trabaja como un estudio. Antes de hacer nada te muestra 3 direcciones distintas y elegís. También evalúa un diseño que ya tengas y te dice qué corregir primero. La revisión de video con IA en la nube **no funciona hasta que cargues una clave propia** del servicio. Sube el video a un tercero, así que no la uses con material confidencial.
- **Set de video de HyperFrames** (10 skills): viene sin actualizaciones automáticas. Nada se sube a HeyGen ni se renderiza en la nube sin tu OK.
- **`estilo-de-marca`**: toma el sistema visual de una marca de referencia y construye con él.
- **UI**: `ui-ux-pro-max`, `ui-design-system`, `components-build` y `frontend-ui-engineering` para diseñar y construir interfaces.
- **Arte y gráfica** (Anthropic): `canvas-design`, `algorithmic-art` y `slack-gif-creator`.
- Cada pieza externa trae su `ORIGEN.txt` (de dónde viene, commit fijado y qué se le cambió) y la licencia de su autor.
