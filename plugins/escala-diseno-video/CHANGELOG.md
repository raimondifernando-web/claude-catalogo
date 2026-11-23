# escala-diseno-video

## 0.1.11 — 2026-11-23
**Skill nueva: `anatomy`.** Arma figuras isométricas interactivas (un objeto físico que explica una idea técnica, con partes que se mueven y se pueden girar). Llega sola con el paquete; no hay nada que hacer.
- Pedile «explicame cómo funciona X con una figura interactiva». Para verificar el resultado usa Node 20.10+ y Chrome o Chromium; si no están, te lo dice.
- Origen: `github:wheresryan22/anatomy@1482e84` (MIT). Copia recortada: sin el programa que publicaba a una galería pública, sin pruebas ni PDFs de ejemplo.

## 0.1.10 — 2026-11-18
**Seis skills nuevas para animar páginas web (cinco de GSAP y un vocabulario de movimiento)**, la librería de animación más usada. Llegan solas con el paquete; no hay nada que hacer.
- `gsap-core` (base: movimientos, easing, respetar a quien pide menos movimiento), `gsap-scrolltrigger` (animar al hacer scroll, fijar secciones, parallax), `gsap-timeline` (secuencias), `gsap-plugins` (SplitText, DrawSVG, Flip, ScrollSmoother: todos gratis, también para uso comercial) y `gsap-performance` (que corra fluido).
- Son las skills oficiales de GreenSock, copiadas sin cambios (licencia MIT, incluida en cada carpeta). Solo texto: no instalan nada ni piden claves.
- `animation-vocabulary`: si describís un efecto sin saber cómo se llama («eso que rebota al abrirse»), te da el nombre exacto para pedírselo bien a Claude. Del autor Emil Kowalski, MIT, copia sin cambios.
- Cuándo se usan: cuando pedís una web con movimiento («que aparezca al hacer scroll», «animá el título»). No son para video: para eso siguen `hyperframes-*`.

## 0.1.9 — 2026-11-16
- Sincronizadas skills desde ~/.claude/skills.


## 0.1.8 — 2026-10-12
- **`frontend-ui-engineering` se mueve al plugin `agent-skills`** (mismo contenido, lo mantiene su autor y se actualiza solo). Este paquete lo declara como dependencia: se instala solo, no tenés que hacer nada. Antes quedaba repetida si ya tenías `agent-skills`.

## 0.1.6 — 2026-10-07
- `hyperframes-animation` al día con su autor: cómo hacer cortes de cámara y luz de relleno en escenas 3D, y cómo renderizar sin placa de video. Solo texto.

## 0.1.4 — 2026-09-28
- **Corrección importante:** para apagar la telemetría de HyperFrames alcanza con `HYPERFRAMES_NO_TELEMETRY=1`. La versión anterior pedía además `DO_NOT_TRACK=1`, pero Claude Code también lee esa variable, y con ella deja de funcionar **Remote Control**: no ves ni manejás tus sesiones desde el celular. **Si la cargaste, sacala** del bloque `env` de `~/.claude/settings.json` y reabrí la app.

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
