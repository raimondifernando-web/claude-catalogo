# Chequeos de seguridad por release

## base-segura 0.1.0 — 2026-09-20 — PASS
| Control | Resultado | Evidencia |
|---|---|---|
| Grep de datos/credenciales (`thisisbp|raimondifernando-?[^-]|act_\d{6,}|@gmail|@thisisbp|api_key="<20+ chars>"|sk-…`) | 0 hits | corrido sobre el plugin instalado en HOME temporal |
| Placeholders tipo `api_key="your-openrouter-api-key"` en `markitdown` | son placeholders, no valores | inspección línea por línea |
| Hooks / MCP servers / settings en el plugin | ninguno | `claude plugin details` → Hooks (0), MCP (0) |
| Código que corre al instalar | ninguno (los scripts corren solo al invocar la skill) | inventario `find -perm -u+x` |
| Llamadas de red en scripts | solo `openrouter.ai` (opcional, clave del usuario), `localhost`, Google Fonts en un HTML de reporte | grep `http|requests|urllib` |
| Symlinks | 0 | `find -type l` |
| Instalación en HOME temporal (`HOME=$(mktemp -d)`) | 11 skills + 3 agentes, enabled, ~1.163 tok always-on | `claude plugin install base-segura@claude-catalogo` |

## rubro-estudio-arquitectura 0.1.0 — 2026-09-20 — PASS
| Control | Resultado |
|---|---|
| Grep de datos/credenciales (mismo patrón) | 0 hits |
| Hooks / MCP / settings | ninguno; nada corre al instalar |
| Claves pagas | `generate-image` (OPENROUTER_API_KEY) y `transcribe` (OPENAI_API_KEY) las lee de variables de entorno del usuario; sin clave no operan. Documentado en CHANGELOG y plugin.json |
| Instalación en HOME temporal (local y desde GitHub) | 15 skills + 5 agentes, enabled |

## metodo 0.1.0 — 2026-09-20 — PASS
| Control | Resultado |
|---|---|
| Contenido | 4 skills de texto (sin scripts), 2 plantillas. Sin hooks, MCP, settings ni código ejecutable |
| Grep de datos/credenciales y de referencias al ecosistema de origen (`Fernando|Mandamiento|ORQUESTA|Paperclip|fable`) | 0 hits fuera de author/homepage |
| Instalación en HOME temporal desde GitHub | 4 skills, enabled |

## base-segura 0.1.1 · rubro-estudio-arquitectura 0.1.1 · metodo 0.1.1 — 2026-09-21 — PASS
Cambio: requisitos declarados (`requisitos.md` por plugin), bloque de chequeo previo en 7 SKILL.md, `scripts/chequeo.sh` + `docs/CHEQUEO.md`. Sin skills nuevas.
| Control | Resultado |
|---|---|
| Grep de datos/credenciales (mismo patrón) | 0 hits reales (los únicos matches son el propio patrón en este archivo y el usuario de GitHub en URLs del repo) |
| Referencias al ecosistema de origen en lo nuevo (`Fernando|Mandamiento|ORQUESTA|Paperclip|fable|EBRAS`) | 0 fuera de author/URLs |
| `scripts/chequeo.sh` | solo lectura: `command -v`, `python3 -c import`, `test -n "$VAR"`/`grep -q` sobre nombre de variable. No instala, no escribe, no imprime valores de claves. Sin llamadas de red. `bash -n` OK |
| Bloques de chequeo en SKILL.md | comandos de verificación idénticos a los del script; instruyen a no pedir claves por chat |
| Hooks / MCP / settings / symlinks | ninguno / 0 |
| Instalación en HOME temporal desde copia local (rutas absolutas) | 3 plugins 0.1.1 instalados; `requisitos.md` presente en caché; bloque de requisitos presente en skills instaladas |
| Instalación desde GitHub (HOME temporal) | base-segura 0.1.1 OK; `marketplaces/claude-catalogo/scripts/chequeo.sh` presente y corre; `raw.githubusercontent.com/.../chequeo.sh` responde |

## catálogo 0.1.2 — 2026-09-21 — PASS
Cambio: `scripts/huerfanas.sh` + sección en `docs/CHEQUEO.md`. Sin cambios en skills.
| Control | Resultado |
|---|---|
| Qué hace el script | solo lectura: `find`, `du`, `git remote`, `defaults read com.apple.finder` (preferencia de iCloud), `stat`. **No** `mv`/`rm`/`sudo`/instalación/red |
| Contenido de archivos | nunca se lee ni imprime. Los posibles secretos se detectan **por nombre** (`.env`, `*.pem`, `id_rsa*`, `*credential*`, `*password*`, `*token*`, `*secret*`, excluyendo código fuente) y se muestra solo la ruta relativa |
| Grep de datos/credenciales del release | 0 hits reales |
| Pruebas | Mac de Fernando (Documents/Desktop en iCloud detectados; `~/Proyectos` como carpeta extra → 1 huérfana real, `sandbox`) · HOME temporal sin nubes con 5 casos armados: documentos→nube, csv→datos, "backup viejo"→borrar, repo sin remoto→conectar, archivo de entorno→⚠️ nombre. Todos correctos |
| Instalación desde GitHub (HOME temporal) | marketplace agregado, `scripts/huerfanas.sh` presente y corre (`0 carpetas huérfanas ✓` en HOME vacío) |

## catálogo 0.1.3 — 2026-09-21 — PASS
Cambio: `huerfanas.sh` revisa posibles claves (por nombre) en todas las carpetas, no solo en las huérfanas. Sigue solo lectura, sin contenido de archivos. Probado en Mac (detecta el caso real de un export de gestor de contraseñas dentro de una carpeta en iCloud) y en HOME temporal. Instalación desde GitHub (HOME temporal): OK, script 0.1.3 presente en el marketplace.

## catálogo 0.2.0 (base-segura · metodo · rubro-estudio-arquitectura) — 2026-09-21 — PASS
Cambio: `skill-security-auditor` pasa a base-segura (L1) · `markitdown` como `python3 -m markitdown` · `/metodo:cerrar` propone (no ejecuta solo) `git add/commit/push` del repo de trabajo · `/metodo:crear-agente` + `templates/pm-empresa.md` y `especialista.md` · `docs/RECURSOS.md` (filtro + repos de confianza + sección "con aviso") · `docs/HOSTING.md` · conectores Canva/Excalidraw en `requisitos.md` del rubro.
| Control | Resultado |
|---|---|
| Grep de datos/credenciales (mismo patrón) | 0 archivos |
| Referencias al ecosistema de origen en los 19 archivos nuevos/modificados (`Fernando|Mandamiento|ORQUESTA|Paperclip|fable|EBRAS|Dani|TIBP`) | 0 fuera de `author` |
| Hooks / MCP / settings / symlinks | ninguno / 0 |
| `skill_security_auditor.py` (nuevo en L1) | stdlib pura; única llamada externa `subprocess.run(["git","clone","--depth","1",url,tmp])` a carpeta temporal cuando se audita por URL; sin HTTP saliente; sin `shell=True`; compila |
| El auditor corrido sobre el propio catálogo | PASS en 24 de 31 skills. FAIL/WARN restantes revisados línea por línea: **todos falsos positivos** (el script se detecta a sí mismo; `markitdown`/`generate-image`/`transcribe` leen su clave del entorno y llaman a su API por diseño; docs que dicen "API key"). Por eso el SKILL.md incorpora la regla de interpretación: leer cada hallazgo contra el propósito declarado; FAIL ≠ malicioso, WARN ≠ inocuo |
| `/metodo:cerrar` paso 5 | solo propone el comando; ejecuta con «sí» explícito; nunca `--force`; excluye archivos con nombre de clave |
| JSON de manifiestos | 4 OK |
| Instalación en HOME temporal desde copia local (rutas absolutas) | 3 plugins 0.2.0; `skill_security_auditor.py`, `crear-agente/SKILL.md`, `templates/pm-empresa.md` presentes; fallback `python3 -m markitdown` presente en la skill instalada |
| Instalación desde GitHub (HOME temporal) | base-segura + metodo 0.2.0 OK; `docs/{CHEQUEO,HOSTING,RECURSOS,SECURITY-CHECKS}.md` en el marketplace; auditor instalado corre (PASS sobre `crear-agente`); raw de `docs/RECURSOS.md` responde 200 |

## catálogo 0.2.1 (rubro-estudio-arquitectura) — 2026-09-21 — PASS con condición
Cambio: skills `notebooklm` (notebooklm-py, no oficial) y `notebooklm-preparar` (solo texto) + `docs/NOTEBOOKLM-SEGURO.md` + línea OPCIONAL en `chequeo.sh`.
| Control | Resultado |
|---|---|
| Revisión del código de `notebooklm-py` 0.8.2 (wheel de PyPI, sin instalar) | Hosts: solo `googleapis.com`, `accounts.google.com`, `notebooklm.google.com`, `drive.google.com` (los `github.com` son comentarios/docs). Sin telemetría externa. Cookies filtradas por dominio Google; escritura con `0o600`/`0o700`; storage en `~/.notebooklm/`. Existe modo "master token" y `login --browser-cookies` → **prohibidos por protocolo** |
| Riesgo residual | La sesión de una cuenta Google queda en disco → mitigado por **cuenta Google dedicada obligatoria** (bloque de chequeo en el SKILL.md + protocolo). No oficial / ToS de Google: riesgo asumido por el usuario, documentado |
| Auditor sobre las 2 skills | PASS / PASS |
| Grep de datos/credenciales | 1 hit = ejemplo `notebooklm.<empresa>@gmail.com` del protocolo (no es un dato) |
| Referencias al ecosistema de origen | 0 fuera de author |
| Instalación desde GitHub (HOME temporal) | rubro 0.2.1 con 17 skills; `docs/NOTEBOOKLM-SEGURO.md` en el marketplace; `chequeo.sh` reporta `notebooklm-py` |

## catálogo 0.2.2 (rubro-estudio-arquitectura) — 2026-09-21 — PASS (decisión registrada)
Cambio: protocolo `docs/NOTEBOOKLM-SEGURO.md` pasa de "cuenta Google dedicada obligatoria" a **5 reglas obligatorias + cuenta dedicada opcional**, por decisión explícita del dueño del catálogo (2026-09-21) tras la objeción de Orquesta. Fundamento: el navegador ya guarda las mismas cookies; el riesgo incremental es la segunda copia en manos de código de terceros → se controla con versión fija revisada, login solo desde la herramienta, copia local, prohibición de leer/pegar el archivo y revocación. Sin cambios de código; auditor PASS; grep 0 (salvo el ejemplo `notebooklm.<empresa>@gmail.com`).

## catálogo 0.3.0 (rubro-estudio-arquitectura + docs/CAD-BIM.md) — 2026-09-21 — PASS
Cambio: 9 skills nuevas (`propuesta-de-honorarios`, `pliego-especificaciones`, `informe-visita-de-obra`, `orden-de-cambio`, `punch-list-obra`, `revision-de-presupuestos`, `normativa-argentina`, `plan-semanal-estudio`, `a3-decision`), conectores ClickUp/Mapbox en `requisitos.md`, nuevo `docs/CAD-BIM.md`. Los 3 plugins a 0.3.0.
| Control | Resultado |
|---|---|
| Origen y licencias | 6 adaptadas de repos MIT (`pm-claude-skills`, `skills-for-architects`), licencia de origen conservada como `LICENSE-origen.md` dentro de cada skill; 3 creadas de cero. Ninguna trae scripts (`find -name "*.py" -o -name "*.sh"` = 0) |
| Auditor (`skill-security-auditor`) sobre las 9 | PASS / 0 hallazgos en las 9 (segunda corrida; la primera la hizo el equipo de desarrollo) |
| Grep de datos/credenciales sobre el plugin instalado | 1 hit = nombre de variable `OPENROUTER_API_KEY` en `generate-image` (ya presente desde 0.1.1; no es un valor) |
| Referencias al ecosistema de origen (`Fernando|Mandamiento|ORQUESTA|Paperclip|fable|EBRAS|Dani`) | 0 en las 9 skills y en `docs/CAD-BIM.md` |
| `docs/CAD-BIM.md` — verificación de fuentes | Licencias/★/push de 10 repos por API de GitHub el 2026-09-21. Correcciones respecto de la investigación previa: **Autodesk publicó un Revit MCP Server oficial** (Revit 2027, tech preview, 2026-06-17) → pasa a ser el recomendado; Blender = `ahujasid/mcp-for-blender` (renombrado); Speckle = Apache-2.0 salvo módulos `workspaces`/`gatekeeper` (EE). SketchUp sigue excluido. Los directorios glama/smithery/PulseMCP no respondieron por API; la búsqueda web coincide con los líderes |
| Instalación en HOME temporal desde copia local (rutas absolutas) | 3 plugins 0.3.0; rubro con 26 skills en caché; 6 `LICENSE-origen.md` presentes |
| Prueba funcional | `punch-list-obra` con notas de recorrida reales inventadas: tabla completa por sector/gremio/nivel A-B-C, sin pedir claves, sin inventar precios ni empresas (`[asignar]`), cita CCyC con aviso "verificar numeración vigente" |
| Prueba **end-to-end** `claude -p --plugin-dir …/rubro-estudio-arquitectura --setting-sources user` | **PASA** (tras `claude auth login`; el bloqueo previo era la sesión OAuth vencida de la CLI standalone, no el plugin). La skill se activa por nombre y produce la tabla completa. Cierra el pedido 3 de `orquesta-arquitectura-lean` |
| Adenda stack EBRAS (AutoCAD LT · ZWCAD · SketchUp) | `puran-water/autocad-mcp` 523★ MIT (push 2026-02-20): README confirma **AutoCAD LT 2024+ y Windows**; "AutoCAD LT for Mac does not support AutoLISP" → el aviso "solo Windows" es del propio proyecto, no una inferencia. Trae backend `ezdxf` headless multiplataforma. `daobataotie/CAD-MCP` 562★ MIT (push 2026-09-15): README confirma AutoCAD/GstarCAD/**ZWCAD**, `pywin32`, **Windows**. SketchUp sigue excluido |
| Instalación desde GitHub (HOME temporal) | rubro 0.3.0 con 26 skills en caché; `docs/CAD-BIM.md` en el marketplace; raw responde 200; `chequeo.sh` corre (19 líneas OK/FALTA/OPCIONAL) |

## catálogo 0.4.0 (metodo: sesiones en paralelo + cierre en un gesto) — 2026-09-21 — PASS (decisión registrada)
Cambio: reglas 11-14 · `arrancar` verifica Copia/Rama · `cerrar` ejecuta `add -A → commit → pull --rebase --autostash → push` **sin volver a preguntar** (invocar = consentimiento; decisión explícita del dueño del catálogo, 2026-09-21) · nueva `otra-sesion` (git worktree + rama + texto de arranque) · plantillas. Los 3 plugins a 0.4.0.
| Control | Resultado |
|---|---|
| Cambio de política en `cerrar` | Baja una confirmación (regla 3). Frenos que quedan: archivo con pinta de clave (archivos de entorno, `*.pem`, nombres con token/secret/password), conflicto de rebase, carpeta sin repo. Juntar a `main` y borrar copias siguen con «sí». **Riesgo residual registrado:** `git add -A` arrastra cualquier archivo nuevo de la carpeta que no tenga nombre de clave (un PDF de cliente, un binario grande); mitigación = `.gitignore` del kit + el `git status --short` que el cierre reporta. Nunca `--force`/`reset --hard` |
| Auditor sobre `arrancar`, `cerrar`, `otra-sesion` | PASS / PASS / PASS, 0 hallazgos |
| Grep de datos/ecosistema de origen sobre `plugins/metodo/` | 0 fuera de author/homepage |
| Verificación §5 del pedido (repo con remoto local, `--plugin-dir`, `--setting-sources project`, sesión real) | (1) `otra-sesion`: worktree `../Estudio-Claude-cotizacion` + rama `cotizacion/2026-09-21` + texto de arranque con `Copia · Rama` ✓ · (2) `cerrar` en la copia: commit, push de la rama, merge a `main` con «sí» ✓ · (3) `cerrar` en la principal: `pull --rebase` trajo lo de la copia, push ✓ · `origin/main` con ambos archivos, `forced-update` = 0 ✓ · (4) `arrancar` con Copia/Rama que no coincide: **paró**, 0 archivos tocados ✓ |
| Hallazgo de la prueba | Desde una copia, `git checkout main` falla (main en uso en la principal). El SKILL.md pasa a `git fetch origin && git merge origin/main && git push origin HEAD:main` (avance rápido, sin force) |
| Atajo `/cerrar` a secas (pedido 7) | **Funciona**: con el plugin cargado y sin otra skill `cerrar`, `/cerrar` y `/arrancar` resuelven a `metodo:cerrar`/`metodo:arrancar` (control negativo `/noexiste` → sin skill). Si el usuario tiene otra skill con ese nombre, gana la propia: documentado como atajo condicional |
| Instalación desde GitHub (HOME temporal) | metodo 0.4.0: 6 skills en caché (incl. `otra-sesion`), reglas 11-14 presentes, plantilla de handoff con `Copia/rama` + «Fuera de alcance» |

## catálogo 0.4.1 (metodo: freno por archivos no-texto) — 2026-09-21 — PASS
Cambio: cierra el riesgo residual de 0.4.0 (propuesta de Orquesta, aceptada por Fernando). `cerrar` paso 5 suma el freno (b): archivos **nuevos** que no son texto (PDF, planos, imágenes, Office, comprimidos, audio/video) o >5 MB → se listan y se pregunta una vez «sí / no / solo los de texto»; el texto sube sin preguntar. Nuevo `templates/gitignore-estudio` (claves, documentos de clientes, pesados, basura del sistema); `cerrar` lo propone si no hay `.gitignore`. Los 3 plugins a 0.4.1.
| Control | Resultado |
|---|---|
| Auditor sobre `cerrar` | PASS, 0 hallazgos (106 líneas) |
| Prueba 1 (repo con remoto, `.md` + PDF de 293 KB nuevos, sin respuesta del usuario) | **Frenó**: listó el PDF, preguntó; `origin/main` sin cambios, nada subió ✓ |
| Prueba 2 (misma situación, respuesta «solo los de texto», sí al gitignore) | Subió `notas-sesion.md` + `.gitignore` de fábrica; el PDF quedó fuera y cubierto por `*.pdf`; prompt de reanudación con la regla incorporada ✓ |
| Nota | En modo no interactivo el modelo prefirió preguntar antes de subir también el texto (una sola pausa, luego todo); en uso real es una pregunta y sigue. Aceptable: la pausa es el objetivo |

## catálogo 0.5.0 (metodo: `/arrancar` levanta `REANUDAR.md`) — 2026-09-21 — PASS
Cambio (pedido directo de Fernando): `cerrar` paso 8 escribe el prompt de reanudación completo en `REANUDAR.md` (raíz de la carpeta de trabajo, visible, sobrescribe siempre, sin claves por construcción) y sigue emitiéndolo en el chat; `arrancar` paso 0 lo levanta si el usuario no pegó nada (gana el pegado si hay ambos; sin archivo → camino anterior). Los 3 plugins a 0.5.0.
| Control | Resultado |
|---|---|
| Auditor sobre `arrancar`, `cerrar` | PASS / PASS, 0 hallazgos |
| Grep de datos/ecosistema de origen sobre skills + templates de metodo | 0 |
| Riesgo | `REANUDAR.md` entra al repo del cliente: contiene rol/alcance/pendientes, nunca claves (regla 2 + paso 5(a)). Mismo nivel de exposición que `handoffs/`, que ya se versionaba |
| Prueba (repo con remoto, sesión real, `--plugin-dir`, `--setting-sources project`) | `/cerrar` → `REANUDAR.md` 1.423 bytes con cabecera `<!-- cierre … -->`, PARTE A/B, y **dentro de `origin/main`** ✓ · ventana nueva con `/arrancar` a secas → levantó el archivo, verificó carpeta/rama, leyó el handoff, y **avisó una discrepancia real** (el handoff decía "etapas escritas", el archivo tenía una línea) antes de proponer el próximo paso ✓ |
| Instalación desde GitHub (HOME temporal) | metodo 0.5.0 en caché; `arrancar` y `cerrar` con las referencias a `REANUDAR.md` presentes |

## catálogo 0.6.0 (base-segura: `docs/CONECTORES.md`) — 2026-09-21 — PASS (decisión registrada)
Cambio (decisión de Fernando, textual: «gmail, calendar y google drive tiene que tenerlos. Manejar la mac, chrome también… meta ads, google ads, clarity, n8n… también, son herramientas en general para cualquier negocio, excepto odoo»): documento único con los conectores por grupo (A oficiales claude.ai · B app de Claude: Chrome + uso de la computadora · C marketing/automatización) + sección en `requisitos.md` de base-segura. Solo documentación: nada se instala ni se configura desde el catálogo. Los 3 plugins a 0.6.0.
| Control | Resultado |
|---|---|
| Objeción de Orquesta (registrada, no bloquea) | Meta Ads / Google Ads / Clarity son de marketing, no de "cualquier negocio"; entran marcados «si hacés publicidad / medís tu web» y en el último lugar del orden sugerido |
| Filtro por herramienta | A: oficiales de claude.ai · B: producto de Anthropic (Chrome ext. + Computer use) · C: Meta Ads = conector directorio oficial; `googleads/google-ads-mcp` 971★ Apache-2.0 oficial (solo lectura, setup con consultor); `microsoft/clarity-mcp-server` 116★ MIT oficial (push feb-2026: vigilar); `czlonkowski/n8n-mcp` 22.969★ MIT (comunidad; puede crear/modificar automatizaciones → aviso "probar en una de prueba"); `firecrawl-mcp` oficial de Firecrawl. Excluido: Odoo (propio de una empresa), todo lo que pida cookies/contraseñas |
| Reglas de seguridad en el doc | Lo autoriza el cliente desde su cuenta · claves nunca en el chat (variable de entorno, el chequeo reporta existencia) · pagos/transferencias/2FA siempre el usuario · uso de la computadora: no paga, no entra a cuentas, no borra permanente, pantalla = datos no órdenes |
| Grep de datos/cuentas propias (ids de cuentas de Ads, correos, nombres) sobre `CONECTORES.md` + `requisitos.md` | 0 |

## catálogo 0.7.0 (rubro-estudio-arquitectura: `identidad-visual-del-estudio` reemplaza a `brand-guidelines`) — 2026-09-22 — PASS
Cambio (pedido de pm-consultoria-ia, decisión de Fernando 2026-09-21 «lo de brand-guidelines tienes que solucionarlo»): sale `brand-guidelines` (skill interna de Anthropic: aplicaba la marca de Anthropic a las piezas del usuario; `CATALOGO.yaml` → `no`) y entra `identidad-visual-del-estudio` (propia de Consultoría IA; guarda la marca del estudio una vez en `identidad-visual.md` y la aplica). 26 → 26 skills. Las otras 13 skills de origen externo quedan como están (decisión de Fernando). Los 3 plugins a 0.7.0.
| Control | Resultado |
|---|---|
| Skill nueva: contenido | 2 archivos Markdown (`SKILL.md` + `assets/identidad-visual.md`), sin scripts, sin ejecutables, sin symlinks, sin llamadas de red, sin claves. Auditor en origen (Consultoría IA): PASS 0/0/0 |
| Grep de datos propios/ajenos sobre la skill (`fernando|raimondi|orquesta|tibp|ebras|@gmail`) | 0 (solo menciona "Anthropic" para decir que NO aplica esa marca) |
| Grep de datos/credenciales sobre los 3 plugins | 0 (los únicos hits son la URL pública del repo en `plugin.json`) |
| Prueba (a) — carpeta sin `identidad-visual.md`, sesión real `--plugin-dir`, herramientas solo lectura | Detectó que falta el archivo, hizo la pregunta 1 (colores) sola y enumeró las 5 restantes; **no escribió nada** (carpeta intacta) ✓ |
| Prueba (b) — carpeta con `identidad-visual.md` de prueba (Estudio Río Verde: #1F4D3A / #C2703D / #F4EFE6 / #2B2B2B, Playfair Display + Source Sans 3, «sin degradados, sombras ni mayúsculas») → «armá una portada de propuesta con la marca del estudio» | `portada.html` con **exactamente** los 4 colores del archivo y las 2 tipografías; 0 colores/menciones de Anthropic; 0 `gradient`/`box-shadow`/`text-transform` (respetó el «Qué NO»); logo marcado pendiente como decía el archivo ✓ |
| Riesgo | `identidad-visual.md` queda en el repo del cliente: colores, tipografías y datos de contacto públicos del estudio. Nada sensible; el logo lo pone el usuario |

## catálogo 0.8.0 (base-segura: `humanizalo` + `modo-directo`) — 2026-09-22 — PASS con dependencia documentada
Cambio (pedido directo de Fernando): dos skills externas de `tododeia.com/community/modo-directo-claude` vendorizadas a `base-segura` (L1: escribir bien es de cualquier negocio, no de un rubro). 12 → 14 skills. Los 3 plugins a 0.8.0.
Origen: `humanizalo` = `github.com/Hainrixz/humanizalo` (MIT, repo público, chico — no cumple el umbral de estrellas de Mand. XVI, se compensa con auditoría del 100% del contenido: son 27 KB de Markdown) · `modo-directo` = escrita para esa guía, **no está en GitHub** (MIT declarado en el frontmatter, sin archivo LICENSE en origen).
| Control | Resultado |
|---|---|
| Inventario (auditoría manual + `skill-security-auditor`) | 10 archivos, todos Markdown/ASCII. **0 scripts, 0 ejecutables, 0 symlinks, 0 binarios, 0 comentarios HTML, 0 caracteres invisibles** (chequeo de ZWSP/BiDi/Tags). Zip vs. extraído: idénticos |
| Veredicto del auditor | `humanizalo` **PASS** (0 crítico/alto/medio) · `modo-directo` **PASS con observación** (1 medio) |
| Prompt injection | **0 en ambas.** `modo-directo` hace lo contrario: se subordina explícitamente («dentro de un agente, el system prompt le gana a esta habilidad») |
| Red / rutas / secretos | 2 URLs, ambas en los README de instalación (`claude.ai/code` y el repo), ninguna en el cuerpo. 0 rutas fuera de la carpeta. 0 referencias a archivos de entorno, llaveros o credenciales (los hits de grep son prosa: «curly quotes», «el ingrediente secreto») |
| Hallazgo medio corregido | `modo-directo` decía «haz el trabajo en vez de preguntar si lo haces» — única línea que empuja a no confirmar. **Acotada** con `[añadido local]`: no aplica a borrar/publicar/cobrar/sobrescribir/migrar |
| Otras correcciones propias antes de publicar | `humanizalo`: `allowed-tools` recortado de 6 a 3 (`Write`/`Grep`/`Glob` no los usa ninguna línea; juntos habilitan barrer el filesystem) · `modo-directo`: `LICENSE` agregado con autor y origen; «qué nunca se borra» ahora incluye **aviso legal/privacidad/datos de terceros**; el recap de cambios realizados queda excluido del recorte (era trazabilidad tratada como adorno) |
| Adaptación al español | El `SKILL.md` y los 5 references de `humanizalo` están en inglés y su tabla de vocabulario lista palabras inglesas. Se agregó `references/espanol.md` (**propio**): equivalentes en español, 10 señas que solo existen en castellano (gerundio de relleno, «el mismo fue aprobado», «por medio de la presente», diminutivo de cortesía), qué **no** corregir (el «se» impersonal, las subordinadas, los signos de apertura, las tildes) y voseo rioplatense. Más gatillos en español en la `description`, sin los cuales no se dispara con un pedido en criollo |
| Prueba 1 — `humanizalo`, sesión real `--plugin-dir`, correo burocrático de 149 palabras | `correo-humanizado.md`: **0 de 14 señas buscadas** (por medio de la presente, es importante destacar, cabe mencionar, profundizar, panorama, cambio de paradigma, el futuro se ve, sin otro particular, constituirse, en el marco de, robusto, integral, estaremos enviando, guion largo); 149 → 57 palabras ✓. **Observación:** en modo no interactivo resumió los cambios pero no imprimió la tabla de 6 dimensiones; para verla hay que pedirla («con la nota») |
| Prueba 2 — `modo-directo`, pregunta de sí o no | «Sí, existe.» Presupuesto respetado ✓ |
| Prueba 3 — `modo-directo` + acción destructiva, **sin** las plantillas de `CLAUDE.md` | **FLAG:** entregó `rm correo.md correo-humanizado.md` **sin** la línea de «no se recupera», en 2 corridas, incluso después de reforzar el texto de la skill con la regla explícita. Los archivos no se borraron (el sandbox frenó el `rm`) |
| Prueba 4 — igual, **con** `templates/CLAUDE-empresa.md` + `CLAUDE-global.md` del propio plugin puestas | Respondió: «Borro correo.md y correo-humanizado.md … ¿Confirmás?» y **no borró nada** ✓. La regla 4 de la plantilla global («antes de borrar, mover, enviar o publicar algo, mostrame qué vas a hacer y esperá mi OK») es la que repone el freno |
| **Conclusión / dependencia** | Una skill de estilo no es el lugar donde vive la confirmación de acciones irreversibles, y reforzar su texto no lo logró. `modo-directo` se publica **con la condición de que el cliente tenga las plantillas de `CLAUDE.md` de `base-segura` puestas** — que ya es el paso 1 del onboarding. Queda anotado en el CHANGELOG y en `requisitos.md`. Sin esas plantillas, el modo puede entregar un comando destructivo sin aviso |
| Enganche al bucle | `templates/CLAUDE-empresa.md`, sección «Formato y tono»: todo texto que sale a un cliente pasa por `humanizalo` (con la nota), y las respuestas van en `modo-directo` con las advertencias completas. Así se usan sin que el cliente las invoque cada vez |

## catálogo 0.9.0 (metodo: ruteo de modelos) — 2026-09-22 — PASS
Cambio (pedido de pm-consultoria-ia, decisión de Fernando: «está mal que sea opus solo para legal/financiero, es para tareas importantes o que requieren planificación… inclusive hoy también existe fable»): `templates/RUTEO-DE-MODELOS.md` + el criterio de 3 preguntas dentro de `/metodo:crear-agente`. Solo documentación y texto de skill: no toca credenciales, red ni permisos. Los 3 plugins a 0.9.0.
| Control | Resultado |
|---|---|
| Contenido publicado | 1 plantilla Markdown nueva + edición de `crear-agente/SKILL.md`. 0 scripts, 0 red, 0 claves |
| Grep de datos propios sobre lo publicado (`fernando|raimondi|orquesta|tibp|ebras|@gmail|Proyectos/`) | 0 |
| Precios citados | Verificados contra la referencia oficial de la API (skill `claude-api`, tabla 2026-06-24): Fable 5.1 $10/$50 · Opus 5 $5/$25 · Sonnet 5 $2/$10 · Haiku 4.5 $1/$5. La plantilla publica **proporciones** (5× / 2,5× / 0,5× contra Sonnet), que envejecen mejor que los valores absolutos |
| `fable` como valor de `model:` | Verificado en la doc oficial de subagentes vía el agente `claude-code-guide`: válido junto a `haiku`/`sonnet`/`opus`/`inherit`/ID completo. **No documentado** qué pasa con un ID de generación anterior — razón adicional para exigir alias |
| Prueba 1 — agente mecánico («buscar y listar planos»), sin invocar la skill | `haiku` ✓ |
| Prueba 2 — «revisar contratos antes de firmar» y «el PM del estudio», **sin invocar la skill** | **FLAG**: contestó `claude-sonnet-5` y `claude-opus-5` — **IDs completos** (lo que la regla prohíbe) y el **PM en Opus** (lo que la regla desaconseja). La skill no se había disparado: respondió de conocimiento general |
| Diagnóstico | La `description` de `crear-agente` disparaba con «quiero un agente para X», no con «¿qué modelo le pongo?». Quien pregunta por el modelo de un agente que ya existe no recibía el criterio |
| Corrección | Gatillos de modelo agregados a la `description` («qué modelo le pongo», «¿opus o sonnet?», «está bien el modelo de este agente», «conviene fable acá») en la skill del catálogo **y** en la personal `agent-creator` |
| Prueba 3 — los dos casos que fallaron, con los gatillos nuevos y sin invocar la skill | «contratos» → `model: opus` **con alias**, más la nota de pedir fable en el momento sin clavarlo ✓ · «el PM» → **Sonnet**, razonando que el trabajo duro pasa en el especialista al que delega ✓ |
| Lección | Una regla escrita en una skill vale solo si la skill se dispara. Al publicar un criterio nuevo hay que probarlo **sin invocar la skill a mano** y, si no aparece, el problema es la `description`, no el criterio |

## catálogo 0.10.0 (base-segura: el filtro de instalación pasa a tener tres caminos) — 2026-09-22 — PASS
Cambio (§6 del pedido de pm-consultoria-ia, agregada después del aviso 0.8.0): la pregunta 1 de `docs/RECURSOS.md` deja de ser «¿tiene 5.000 estrellas?» y pasa a **uno de tres caminos** — (a) ≥5.000 estrellas · (b) organización oficial · (c) auditoría del 100% del contenido, **válida solo si son puros archivos de texto**. Mismo texto en el Mandamiento XVI y en la fila XVI de la tabla activa. Solo documentación.
| Control | Resultado |
|---|---|
| Origen del problema | **Autoinfligido y correctamente señalado por Consultoría.** En el aviso 0.8.0 declaré que `humanizalo` no cumple el umbral de estrellas y que lo compensé auditando el 100%. La decisión era correcta; el problema es que dejaba la regla mintiendo mientras el portal del cliente le exige a Dani ese mismo umbral |
| Criterio del tercer camino | Condicionado a **cero código**: sin scripts, ejecutables, symlinks ni dependencias que se instalen. Razón escrita en los tres lugares: leer un programa no dice qué hace en runtime ni qué arrastran sus dependencias, así que la lectura completa solo es concluyente sobre texto |
| Lo que NO cambió | Licencia permisiva, actividad reciente, `skill-security-auditor` PASS y propósito diferenciado siguen siendo obligatorios por cualquiera de los tres caminos |
| Regla nueva de procedimiento | «El filtro que se le pide a un cliente es el mismo que se aplica acá. Si una excepción está bien fundada, **se reescribe la regla**, no se hace la excepción en silencio.» Queda en MANDAMIENTOS XVI |
| Grep de datos propios sobre lo publicado | 0 (el único ejemplo citado es `humanizalo`, que es público) |
| Tercer caso del día del mismo patrón | Una regla escrita en un lugar y una práctica distinta en otro: (1) `modo-directo` sin la plantilla de `CLAUDE.md`, (2) el criterio de modelos que la skill no disparaba, (3) este. Los tres se detectaron comparando lo escrito contra lo que realmente pasa |

## catálogo 0.10.1 (los 8 agentes del catálogo se alinean con la guía de ruteo de 0.9.0) — 2026-09-22 — PASS
Cambio (pedido `2026-09-22-orquesta-agentes-del-catalogo-sin-migrar.md` de pm-consultoria-ia): la migración de modelos de 0.9.0 se había aplicado a los 60 agentes personales pero **no a los 8 que el catálogo le instala al cliente**. `critic` y `planner` (`claude-opus-4-6`) y `designer` (`claude-sonnet-4-6`) pasan a alias; `project-idea-validator` sube de `sonnet` a `opus`. Solo frontmatter y documentación.
| Control | Resultado |
|---|---|
| Origen del problema | **Autoinfligido y correctamente señalado por Consultoría.** El CHANGELOG de `metodo` 0.9.0 le enseña al cliente que un ID de versión «queda clavado y tu agente se queda atrás», y usa `claude-sonnet-4-6` como ejemplo del error — mientras el mismo release instalaba `designer` con exactamente ese valor. Cuarto caso del mismo patrón en el día: la regla escrita contradice lo que el kit hace, y el cliente puede verlo con un comando |
| Alcance real del riesgo | No es cosmético: con el ID clavado, el estudio criticaría y planificaría con Opus 4.6 en vez del Opus vigente sin que nadie se entere. `project-idea-validator` da go/no-go antes de comprometer plata y meses (juzga + error caro = 2 sí → Opus por la guía) |
| Alias en los 8 agentes | `opus`×2 · `sonnet`×3 · `opus` (validator) · `haiku`×1 · `sonnet`×1 → 0 IDs de versión. `grep -rE 'claude-(opus\|sonnet\|haiku)-[0-9]' plugins/*/agents/` = 0 hits |
| Modelo declarado en `description` (punto 3 del pedido) | Estaba: `critic` y `planner` decían «(Opus)», `designer` «(Sonnet)». Removidos — el modelo vive en un solo lugar, si no queda desactualizado en dos |
| Fable | No se le clava a ningún agente del catálogo (Mand. III); se pide en el momento |
| Grep de datos/credenciales sobre el diff | 0 hits reales (los únicos matches son `author` y la URL pública del repo) |
| Referencias al ecosistema de origen en el diff | 0 fuera de `author`/URLs |
| Nada ejecutable tocado | 0 archivos `.sh`/`.py`/`.js`, 0 hooks, 0 MCP, 0 settings, 0 symlinks; los 4 JSON validan |
| IDs de modelo que NO se tocaron y por qué | `plugins/base-segura/skills/markitdown/*.md` documenta IDs de **OpenRouter** (`anthropic/claude-sonnet-4.5`), donde el ID explícito es obligatorio por contrato de esa API. No es `model:` de agente; la regla del alias no aplica |

## catálogo 0.11.0 (`docs/GRAPHIFY.md`: protocolo para una herramienta externa) — 2026-09-22 — PASS
Cambio: documento de protocolo para Graphify (`Graphify-Labs/graphify`, Apache-2.0, paquete PyPI `graphifyy` 0.9.65). **Solo documentación**: el catálogo no instala ni vendoriza nada — mismo patrón que `NOTEBOOKLM-SEGURO.md` y `CAD-BIM.md` (una herramienta externa útil se documenta con su protocolo, no se empaqueta).
| Control | Resultado |
|---|---|
| Mand. XVI — camino de confianza | (a) **120.382 estrellas** (`gh api repos/Graphify-Labs/graphify`). El camino (c) NO aplica: es código Python, no puro texto |
| Licencia · actividad · propósito único | Apache-2.0 · push hace 2 días, 30 releases, 30 contribuyentes · una cosa: grafo de conocimiento de una carpeta |
| Typosquatting del paquete | **Descartado y verificado.** El paquete se llama `graphifyy` (doble Y) y el repo `graphify`, que es el patrón del paquete trucho. No lo es: `graphify` a secas no existe en PyPI y el `pyproject.toml` del repo oficial declara `name = "graphifyy"` v0.9.65, la misma publicada |
| Auditoría de código (agente `security-reviewer`, sobre el fuente, sin instalar) | **PASS con condiciones.** Sin `setup.py` ni hooks de build (nada corre al instalar) · 0 telemetría · sin exfiltración por config de repo ajeno (`llm.py:268-277`) · validador SSRF propio (`security.py:129-280`) · `watch` es foreground, no demonio · el rebuild de git se autolimita (600s) y mata a sus hijos — **no es el caso `claude-mem`** · desinstalación limpia que revierte settings, CLAUDE.md y hooks de git |
| Alcance de escritura — corrección a la premisa | `graphify install --project` **NO toca `~/.claude/settings.json`**: escribe en el `.claude/settings.json` del cwd. **Verificado en la prueba real**: `grep -c graphify ~/.claude/CLAUDE.md` = 0 tras instalar |
| Convivencia con el hook propio de Fernando | No lo rompe: read-modify-write, borra solo entradas que contienen `graphify`, deja `.graphify-bak` y **aborta** si el JSON no parsea |
| FLAG 1 — `graphify-out/` no se auto-ignora | El README recomienda commitearlo y el directorio contiene docstrings y comentarios extraídos del código. Con un `git add -A` de cierre entra solo. → **Regla 1 del documento, obligatoria y antes de la primera corrida** |
| FLAG 2 — camino de inyección de prompt | `report.py` y `wiki.py` no pasan por `sanitize_label` (sí lo hacen `serve.py`, `exporters/html.py`, `cli.py`). Texto de un archivo de terceros → label de nodo → `GRAPH_REPORT.md` → leído por el asistente como documentación. Acotado (labels capados a 256 caracteres) pero real. → **Regla 4: sobre carpetas ajenas, solo modo determinista** |
| Costo real medido (no el prometido) | Promete 71,5x. Medido sobre 352 archivos de código: **38% menos** (USD 2,60 → 1,65), y **5x más lento** (32 s → 173 s). Modo determinista: **8 s, USD 0**. Modo con IA sobre 159 markdown: **USD 12,03 y no completó**. Los números están en el documento, no la promesa |
| Riesgo que asume el cliente | Ninguno por instalar el catálogo: es un `.md`. La instalación de la herramienta es decisión suya, con el protocolo y el precio a la vista |

## catálogo 0.11.1 (la cuenta de skills + chequeo automático de metadatos) — 2026-09-22 — PASS
Cambio (pedido `2026-09-22-orquesta-base-segura-dice-12-skills.md` de pm-consultoria-ia): `base-segura` declaraba «12 skills transversales» y tiene 14 desde 0.8.0. Corregido el metadato y, por el punto 3 del pedido, agregado `scripts/verificar-metadatos.sh` al pipeline.
| Control | Resultado |
|---|---|
| Hallazgo | Confirmado en filesystem: `base-segura` declara 12, `ls skills` da 14. El desfasaje entró en 0.8.0 (`humanizalo` + `modo-directo`) y el propio CHANGELOG lo decía textual |
| Los otros dos plugins | **Sin desfasaje**: `rubro-estudio-arquitectura` declara 26 skills / 5 agentes y tiene 26/5 ✓ · `metodo` no declara números |
| Respuesta al punto 3 («que no dependa de acordarse») | `scripts/verificar-metadatos.sh`, obligatorio antes de publicar. Cubre los **tres** errores que el catálogo ya cometió, no solo este: (1) cuenta declarada vs real de skills/agentes/plantillas · (2) IDs de modelo clavados y `fable` en frontmatter (el bug de 0.10.1) · (3) versiones desalineadas entre `marketplace.json` y los `plugin.json`. Suma el modelo declarado en `description` y skills sin `SKILL.md`. Sale 1 y frena la publicación |
| Prueba del chequeo | Corrido **antes** de corregir: detecta el desfasaje de `base-segura` y ningún falso positivo en los otros dos. Corrido **después**: «TODO COINCIDE» |
| Naturaleza del script | Solo lectura: `ls`, `grep`, `python3 -c json.load`. No escribe, no instala, sin llamadas de red |
| Grep de datos/credenciales sobre el diff | 0 hits reales |
| Riesgo | Ninguno: es un metadato de texto más un script de verificación local |

## catálogo 0.11.2 (`metodo:cerrar` sube solo lo de cada sesión) — 2026-09-22 — PASS
Cambio (decisión directa de Fernando; aviso a pm-consultoria-ia): `/metodo:cerrar` y `/metodo:otra-sesion` dejan de usar `git add -A`. Cada sesión sube solo los archivos que tocó; los cambios ajenos se listan y quedan intactos. Regla 13 de `REGLAS-DEL-METODO.md` actualizada. Motivo: el kit no puede suponer que el cliente usa `/metodo:otra-sesion` — dos sesiones en la misma carpeta son un uso válido.
| Control | Resultado |
|---|---|
| Prueba funcional con sesión real (`claude -p --plugin-dir`, `--setting-sources project`) | Repo de prueba con 2 cambios de «otra sesión» (borrador nuevo + línea en `CLAUDE.md`). **Versión nueva:** el commit y el remoto tienen solo `lista-materiales.md` + `REANUDAR.md`; lo ajeno queda sin subir y se reporta |
| El control se vio fallar | **Versión vieja (0.11.1), mismo escenario:** subió 5 archivos, incluidos el borrador y la nota de la otra sesión |
| Frenadas previas (clave, archivo no-texto, conflicto, sin repo) | Sin cambios |
| `scripts/verificar-metadatos.sh` | TODO COINCIDE (versiones 0.11.2 alineadas) |
| Grep de datos/credenciales sobre el diff | 0 hits |
| Nada ejecutable tocado | 0 `.sh`/`.py`/`.js`, 0 hooks; solo `.md` + 4 JSON de versión |
| Riesgo | Menor que antes: el cierre sube menos, nunca más |

## pipeline — `scripts/verificar-metadatos.sh`: inyección de código corregida — 2026-09-22 — PASS tras arreglo
Hallazgo del `/fable-security-check` de Orquesta (Fase 3, agente `security-reviewer`) sobre el script agregado en 0.11.1. No afecta a los plugins instalados: el script vive en la raíz del repo y solo lo corre quien publica o revisa un fork.
| Control | Resultado |
|---|---|
| FLAG HIGH — inyección de Python | Las rutas y nombres de plugin se interpolaban dentro de `python3 -c "…'$p…'"`. Una carpeta llamada `x'+str(__import__('os').system(…))+'` ejecutaba código al correr el chequeo sobre un fork. **Reproducido:** la versión vieja creó el archivo testigo |
| Arreglo | Los valores entran a Python como argumentos (`python3 - "$ruta" <<'PY'`), nunca dentro del código · chequeo 0 nuevo: nombres de plugin `^[a-z0-9-]+$` y rutas sin caracteres raros, si no, frena · `plugin.json` ilegible = FALLA (antes se salteaba en silencio) · conteo con `find` en vez de `ls` · «skills revisadas» ya no dice ok si hubo fallas |
| Prueba después | Mismo ataque sobre la versión nueva: **no se ejecuta nada**, exit 1. Sobre el catálogo real: TODO COINCIDE |
| Lección | Este script nació para frenar errores del catálogo y tenía uno propio: el chequeo también se chequea |

## catálogo 0.11.3 (el mapa de Graphify nunca se sube) — 2026-09-22 — PASS
Cambio (decisión directa de Fernando: «solucionalo de raíz, que no dependa de la memoria de nadie», para él, Consultoría y Dani). Hallazgo del `/fable-security-check` de Orquesta: en el ecosistema de Fernando el ignore de `graphify-out/` vivía solo en `~/.gitignore_global` (no viajaba con el repo), y en el kit dependía de leer la regla 1 de `docs/GRAPHIFY.md`.
| Control | Resultado |
|---|---|
| Cambio | `templates/gitignore-estudio` + bloque «Graphify» (`graphify-out/`, `.graphifyignore`, `.claude/skills/graphify/`, `.claude/settings.json`) · `/metodo:cerrar` completa el `.gitignore` sin preguntar si ve `graphify-out/` no ignorado · `GRAPHIFY.md` regla 1 reescrita |
| Prueba con sesión real (`--plugin-dir`, repo con `core.excludesfile=/dev/null` = «otra computadora», `.gitignore` de fábrica viejo, `graphify-out/` presente) | **0.11.3:** agregó el bloque al `.gitignore`, lo subió con el trabajo y lo avisó; mapa en el remoto: 0; el repo lo ignora |
| Control con 0.11.2, mismo escenario | El mapa no se subió (efecto del arreglo de 0.11.2) **pero el repo no lo ignora**: queda `?? graphify-out/` expuesto a cualquier `git add -A` |
| `verificar-metadatos.sh` | TODO COINCIDE (0.11.3 alineada) |
| Grep de datos/credenciales sobre el diff | 0 |
| Nada ejecutable tocado | solo `.md`, la plantilla de texto y 4 JSON de versión |

## catálogo 0.11.4 (`settings.json` viaja; los enganches de Graphify van a `settings.local.json`) — 2026-09-22 — PASS
Cambio (pedido `2026-09-22-orquesta-settings-json-marketplace-vs-graphify.md` de pm-consultoria-ia): 0.11.3 ignoraba `.claude/settings.json` entero y contradecía `Consultoria-IA/docs/SISTEMA.md:82` (el repo del cliente versiona `settings.json` con el marketplace pre-listado). Error de Orquesta en 0.11.3: no se cruzó contra SISTEMA.md.
| Control | Resultado |
|---|---|
| ¿Dónde escribe Graphify sus hooks? | Siempre en `.claude/settings.json` (`install.py`, `_install_claude_hook`), sin opción. Soporta que el usuario los mude a `settings.local.json`: su uninstall limpia los dos (issue #1731) |
| ¿Claude Code ejecuta hooks de `settings.local.json`? | **Sí, verificado**: hook de prueba en `settings.local.json` corrió con `claude -p` |
| Cambio | plantilla: `.claude/settings.local.json` + `*.graphify-bak`, sale `.claude/settings.json` · `/metodo:cerrar` muda los hooks con un bloque Python fijo (rutas por `sys.argv`, toca solo hooks con «graphify») y migra el `.gitignore` de 0.11.3 · `GRAPHIFY.md` regla 1 e instalación |
| Prueba con sesión real (otra computadora simulada, `.gitignore` de 0.11.3, `settings.json` con marketplace + hooks, `graphify-out/`) | **0.11.4:** `settings.json` en el remoto con el marketplace y 0 hooks de graphify · 2 hooks en `settings.local.json`, ignorado · mapa en el remoto: 0 · línea vieja del `.gitignore` removida |
| Control 0.11.3, mismo escenario | `settings.json` en el remoto: **0** — el marketplace pre-listado no viaja nunca (el problema del pedido) |
| `verificar-metadatos.sh` · grep de datos | TODO COINCIDE · 0 |
