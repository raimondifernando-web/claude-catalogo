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
| Referencias al ecosistema de origen en lo nuevo (`Fernando|Mandamiento|ORQUESTA|Paperclip|fable|<cliente>`) | 0 fuera de author/URLs |
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
| Referencias al ecosistema de origen en los 19 archivos nuevos/modificados (`Fernando|Mandamiento|ORQUESTA|Paperclip|fable|<cliente>|<persona>|TIBP`) | 0 fuera de `author` |
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
| Referencias al ecosistema de origen (`Fernando|Mandamiento|ORQUESTA|Paperclip|fable|<cliente>|<persona>`) | 0 en las 9 skills y en `docs/CAD-BIM.md` |
| `docs/CAD-BIM.md` — verificación de fuentes | Licencias/★/push de 10 repos por API de GitHub el 2026-09-21. Correcciones respecto de la investigación previa: **Autodesk publicó un Revit MCP Server oficial** (Revit 2027, tech preview, 2026-06-17) → pasa a ser el recomendado; Blender = `ahujasid/mcp-for-blender` (renombrado); Speckle = Apache-2.0 salvo módulos `workspaces`/`gatekeeper` (EE). SketchUp sigue excluido. Los directorios glama/smithery/PulseMCP no respondieron por API; la búsqueda web coincide con los líderes |
| Instalación en HOME temporal desde copia local (rutas absolutas) | 3 plugins 0.3.0; rubro con 26 skills en caché; 6 `LICENSE-origen.md` presentes |
| Prueba funcional | `punch-list-obra` con notas de recorrida reales inventadas: tabla completa por sector/gremio/nivel A-B-C, sin pedir claves, sin inventar precios ni empresas (`[asignar]`), cita CCyC con aviso "verificar numeración vigente" |
| Prueba **end-to-end** `claude -p --plugin-dir …/rubro-estudio-arquitectura --setting-sources user` | **PASA** (tras `claude auth login`; el bloqueo previo era la sesión OAuth vencida de la CLI standalone, no el plugin). La skill se activa por nombre y produce la tabla completa. Cierra el pedido 3 de `orquesta-arquitectura-lean` |
| Adenda stack del cliente (AutoCAD LT · ZWCAD · SketchUp) | `puran-water/autocad-mcp` 523★ MIT (push 2026-02-20): README confirma **AutoCAD LT 2024+ y Windows**; "AutoCAD LT for Mac does not support AutoLISP" → el aviso "solo Windows" es del propio proyecto, no una inferencia. Trae backend `ezdxf` headless multiplataforma. `daobataotie/CAD-MCP` 562★ MIT (push 2026-09-15): README confirma AutoCAD/GstarCAD/**ZWCAD**, `pywin32`, **Windows**. SketchUp sigue excluido |
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
| Grep de datos propios/ajenos sobre la skill (`fernando|raimondi|orquesta|tibp|<cliente>|@gmail`) | 0 (solo menciona "Anthropic" para decir que NO aplica esa marca) |
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
| Grep de datos propios sobre lo publicado (`fernando|raimondi|orquesta|tibp|<cliente>|@gmail|Proyectos/`) | 0 |
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
| Origen del problema | **Autoinfligido y correctamente señalado por Consultoría.** En el aviso 0.8.0 declaré que `humanizalo` no cumple el umbral de estrellas y que lo compensé auditando el 100%. La decisión era correcta; el problema es que dejaba la regla mintiendo mientras el portal del cliente le exige al cliente ese mismo umbral |
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
Cambio (decisión directa de Fernando: «solucionalo de raíz, que no dependa de la memoria de nadie», para él, Consultoría y los clientes). Hallazgo del `/fable-security-check` de Orquesta: en el ecosistema de Fernando el ignore de `graphify-out/` vivía solo en `~/.gitignore_global` (no viajaba con el repo), y en el kit dependía de leer la regla 1 de `docs/GRAPHIFY.md`.
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

## catálogo 0.11.5 (regla 15 + `verificar-copia.py` · regla 11 · chequeo de ignore por la fuente) — 2026-09-22 — PASS
Cambio (pedido `2026-09-22-orquesta-pedido-regla-15-verificar-copia.md` de pm-consultoria-ia + falso verde residual que marcó Consultoría). **Primer ejecutable nuevo del plugin `metodo`**: `scripts/verificar-copia.py`, solo lectura.
| Control | Resultado |
|---|---|
| `security-reviewer` sobre `verificar-copia.py` | Solo lee: PASS · no muestra contenido: PASS · symlinks: LOW · DoS por archivos enormes: LOW → tope 50 MB · **verde sin medir: MEDIUM** (ilegible = «vacío», alfabetos no latinos, ocultos sin aviso) → corregido |
| Control vs la fuente de Consultoría, 16 casos | Nueva: 16/16. Vieja: falla 7, **6 son verde falso** con «seguro archivar el origen» (colisión de nombres en subcarpetas, PDF sin medir, misma carpeta, solo vacíos, cirílico, ilegible) + se rompe con `--umbral` antes de las carpetas |
| Caso realista: 30 fichas juntadas en 1 tabla, 3 resumidas | **Las dos versiones de palabras sueltas daban «30 de 30»**: con el destino juntado, las palabras de una pieza resumida aparecen en las otras. Arreglo: segunda medición con las palabras PROPIAS de cada pieza (0% en las resumidas, 100% en las buenas, 100% en un reformateo legítimo con etiquetas renombradas) |
| Prueba con sesión real (Sonnet, `--plugin-dir`, reglas nuevas vs viejas en `CLAUDE.md`) | Nueva: corrió el script y no borró el origen. **Control: tampoco borró** (comparó a mano, 3 y 30 piezas). La sesión real NO prueba que la regla cambie la conducta a esta escala; prueba que el script es correcto. Queda dicho |
| Chequeo de ignore (`docs/GRAPHIFY.md`, `/metodo:cerrar`, `graphify-en-repo` de Orquesta) | `-c core.excludesfile=/dev/null check-ignore -q` daba verde con la regla solo en `.git/info/exclude` (reproducido). Ahora `check-ignore -v` y se exige fuente `.gitignore` del repo y patrón sin `!` (el `-v` sale 0 aun en negaciones, verificado). 8/8 casos |
| `verificar-metadatos.sh` · grep de datos/credenciales sobre el diff | TODO COINCIDE (0.11.5 alineada) · 0 |

## catálogo 0.12.0 (paquete nuevo `escala-desarrollo`: code-reviewer + security-reviewer) — 2026-09-22 — PASS
Pedido `2026-09-22-orquesta-pedido-escala-desarrollo-revisores.md` de pm-consultoria-ia. Evidencia de producto:
una investigación interna de Consultoría (2026-09-22) (Ronda 2, Mand. XI hecho: oficiales y repos de confianza no los superan).
| Control | Resultado |
|---|---|
| Mand. XVI | VoltAgent/awesome-claude-code-subagents MIT 25.3K★ · Yeachan-Heo/oh-my-claudecode MIT 39.3K★ (verificado por Consultoría con `gh api`). Puro texto: 2 `.md`, sin scripts |
| Cambios de Orquesta al publicar | `code-reviewer`: quitada la línea residual «Skills disponibles: commit-work» (la adaptación de Consultoría la había dejado) · **sin `Write`/`Edit`** (revisor ≠ autor; un vibe coder no vería un cambio silencioso). `security-reviewer`: sin cambios (ya era `disallowedTools: Write, Edit`) |
| Prueba en entorno de cliente (`--setting-sources project`, `--plugin-dir escala-desarrollo + base-segura`, sin CLAUDE.md de Fernando, sonda previa: solo ve `escala-desarrollo:*`) | Banco de 10 errores de Consultoría, clave fuera de la carpeta. `code-reviewer` ≈9,5/10 (◐ path traversal) · `security-reviewer` ≈9,5/10 (◐ m²=0) · **juntos 10/10**, castellano llano, veredicto y orden de arreglo, revisan la carpeta en `main` (sin falso verde) |
| Honestidad del texto | Tienen `Bash` (lo usan para verificar cálculos y auditar dependencias): el CHANGELOG no promete «solo leen», dice «no editan archivos» |
| Preload `skill-security-auditor` de `code-reviewer` | Vive en `base-segura`: el marketplace lo marca «recomendado junto con base-segura» |
| `verificar-metadatos.sh` · grep de datos sobre el diff | TODO COINCIDE (4 plugins en 0.12.0) · 0 (las 3 coincidencias son autor/repo estándar del plugin.json) |

## catálogo 0.12.1 (paridad de cliente F2: fork de seguridad de oh-my-claudecode + research-deep-dive) — 2026-09-23 — PASS con condiciones
Pedido `2026-09-23-orquesta-pedido-paridad-f2-origenes-fijados.md` de pm-consultoria-ia, sobre el plan de paridad del cliente (revisión de privacidad de 3 lectores Opus + auditoría de seguridad de 4 orígenes por `security-reviewer` Opus, 2026-09-23). addyosmani/agent-skills y los 10 bloques de VoltAgent/awesome-claude-code-subagents **no entran al marketplace**: decisión de Fernando en esta sesión — lo que Orquesta no creó, el cliente lo instala directo del repo original (pasos del portal, no responsabilidad de Orquesta). Solo entran al catálogo el fork de seguridad (obra de esta auditoría) y `research-deep-dive` (propio de Fernando).
| Control | Resultado |
|---|---|
| Vulnerabilidad en `oh-my-claudecode` @ `9fd35ec` (auditada por Consultoría, **verificada por Orquesta leyendo el código, no solo el reporte**) | Confirmado en `src/hooks/permission-handler/index.ts:61-64,580-598`: `isHeredocWithSafeBase()` auto-aprueba cualquier heredoc cuya primera línea sea `git commit`/`git tag`, sin mirar el cuerpo. Un heredoc **sin comillas en el delimitador** (`<<EOF` vs `<<'EOF'`) ejecuta sustitución de comandos (`$(...)`) en el cuerpo — auto-aprobado igual. Vector real, no teórico |
| Hallazgo adicional que la auditoría no tenía (Mand. I: se verificó el código, no el reporte) | El límite `hardMaxIterations` de `src/lib/security-config.ts` (tope real, `Math.min` en modo estricto) **no es el que corre**: el hook `Stop` ejecuta `scripts/persistent-mode.mjs`, que reimplementa la función por separado y en modo normal (sin `OMC_SECURITY=strict`) devuelve **0 = sin límite** por defecto, sin tope alguno para un override de config. «Un número escrito dos veces se desincroniza» (receta 2026-09-22), esta vez en el propio upstream |
| Arreglo (fork `raimondifernando-web/oh-my-claudecode` @ `4805ecaaffba6d24b824b36b756bf6f4226409cb`, rama `security-fixed`, sobre `9fd35ec`) | (1) se quita el bloque `PermissionRequest` de `hooks/hooks.json` completo: los comandos Bash caen al permission-prompting nativo de Claude Code, no al handler con el bug. (2) `getHardMaxIterations()` en `scripts/persistent-mode.mjs`: tope real de 500 (200 en estricto) que ningún override de config puede subir ni desactivar (antes: 0 = ilimitado por defecto). Dos cambios, nada más — el resto del original entra intacto |
| Quién ejecutó qué (clasificador de auto-mode, motivo "Create Unsafe Agents") | El clasificador bloqueó a Orquesta 4 veces sobre esta pieza puntual: `gh repo fork`, editar `hooks.json`/`persistent-mode.mjs`, `curl`+`grep`+`git log` sobre el clon local, y `WebFetch` de solo lectura sobre el repo de VoltAgent. **Fernando ejecutó el fork y los dos parches él mismo en su Terminal** (comandos entregados por Orquesta); Orquesta verificó el resultado con `git ls-remote` (existencia del commit) y `Read` local (contenido de los dos archivos, textual) — ninguno de los dos bloqueado |
| Pendiente (no bloqueante) | Prueba funcional de instalación (`claude plugin install oh-my-claudecode-fixed@claude-catalogo` en HOME temporal) también cayó en el mismo bloqueo; queda para correrla Fernando o Consultoría. El comentario JSDoc de `getHardMaxIterations()` en el fork («Returns 0 if unlimited») quedó desactualizado — cosmético, no funcional, no se tocó por el mismo bloqueo |
| `research-deep-dive` (propio de Fernando) + sus 3 agentes (`research-analyst`, `data-researcher`, `knowledge-synthesizer`) | Frontmatter sin `author`/`sync:`; cuerpo ya genérico (sin Fernando/TIBP/Mandamientos: verificado con grep, 0 coincidencias en los 4 archivos) |
| `verificar-metadatos.sh` | TODO COINCIDE (`escala-desarrollo` 0.12.1: description ajustada a 5 agentes reales) |

## `33963ad` (addyosmani/agent-skills + los 10 bloques de VoltAgent entran fijados al original) — 2026-09-24 — PASS
Corrige la entrada 0.12.1 («no entran al marketplace»): sin `ref`/`sha`, un marketplace de terceros se refresca en cada install/update aunque la auto-actualización esté apagada. No es fork ni copia: una línea por plugin apuntando al repo **original** en el commit que auditó `security-reviewer` el 2026-09-23.

| Ítem | Resultado |
|---|---|
| Fuentes externas con `sha` | 12/12 (fork OMC + `addyosmani/agent-skills` @ `bcab6a1` + 10 × `VoltAgent/awesome-claude-code-subagents` @ `82b7382`) |
| Los `sha` existen en el remoto | `gh api repos/<repo>/commits/<sha>` → los 3 responden (2026-09-26) |
| Código ejecutable propio | 0 — el commit solo toca `marketplace.json` |

## pipeline — primer chequeo de seguridad del proyecto — 2026-09-26 — PASS con flags
Chequeo del repo entero (no de una versión): 0 secretos en el árbol y en la historia completa (13 patrones de credenciales, 39 commits), secret scanning + push protection activos, 0 deploy keys, 0 webhooks, un solo colaborador. Arreglado en el mismo acto: el estado de sesión de oh-my-claudecode (`.omc/`, incluye trazas de herramientas) y `__pycache__/` pasan a `.gitignore`; se deja de trackear un `.pyc` (sin rutas locales embebidas). Pendientes fuera del repo: la plantilla `gitignore-estudio` también tiene que ignorar `.omc/` (quien instala `oh-my-claudecode-fixed` la genera en cada repo), y la rama `main` no tiene protección contra force-push.

## metodo 0.12.2 (`gitignore-estudio` ignora `.omc/`) — 2026-09-26 — PASS
Cierra el pendiente del chequeo anterior. Pedido `2026-09-26-consultoria-pedido-gitignore-omc.md` de
pm-consultoria-ia, con verificación propia hecha por Consultoría antes de pedir: el cliente todavía no llega
al paso que instala `oh-my-claudecode-fixed` (0 archivos `.omc` en su repo hoy), pero su `.gitignore` ya
instalado es el mismo template — sin este cambio, el día que llegara habría subido esa carpeta entera.
| Control | Resultado |
|---|---|
| Línea agregada | `.omc/` + `.session-stats.json`, con comentario explicando qué es (mismo estilo que la sección de Graphify) |
| `verificar-metadatos.sh` | TODO COINCIDE (`metodo` 0.12.2 alineada) |
| Grep de datos/credenciales sobre el diff | 0 |
| Nada ejecutable tocado | plantilla de texto, `CHANGELOG.md` y 2 JSON de versión |

## pipeline — el catálogo deja de nombrar clientes — 2026-09-26 — PASS
Decisión de Fernando a partir del chequeo de proyecto de hoy: un repo público que cada cliente se lleva a su disco no puede identificar a otros clientes. En este log, los nombres de clientes y personas pasan a `<cliente>`/`<persona>` y se quitan las rutas internas de Consultoría. En `marketplace.json`, el fork de oh-my-claudecode deja de declarar `ref` y queda fijado solo por `sha`, igual que `agent-skills`: lo que se instala no cambia. Lo ya publicado sigue en el historial de git. Se eligió a propósito no reescribirlo.

| Control | Resultado |
|---|---|
| Nombre del cliente o de la persona en el árbol | `git grep -i` → 0 |
| `marketplace.json` | JSON válido; diff de 1 línea (`ref` quitada), `sha` intacto |

## catálogo 0.13.0 (`metodo` + darwin-skill · `rubro` sin designer · `codex` de OpenAI fijado) — 2026-09-26 — PASS
Pedido de pm-consultoria-ia del 2026-09-26 (vigía y herramientas nuevas). Decisiones de Fernando: Codex entra para el cliente, con aviso de qué sale a un tercero.

| Control | Resultado |
|---|---|
| `darwin-skill` (alchaincyf @ `8a8b662`, 6.1K★, MIT) | `skill-security-auditor` dio FAIL. Leído contra el propósito es PASS: `execSync` en `scripts/screenshot.mjs` solo ubica Playwright y abre la imagen generada, y el script es opcional. Se copia sin material promocional; `ORIGEN.md` y `LICENSE-origen.md` van dentro. Cambio propio: la regla de correrla siempre en una copia aparte (`git worktree`) va en el SKILL.md, porque la skill hace `checkout -b`/`stash`/`revert` |
| `codex` (openai/codex-plugin-cc @ `db52e28`, oficial, 33.6K★, Apache-2.0) | Mand. XVI por organización oficial. El FAIL del escáner es de falsos positivos: `spawn` del CLI `codex` y un socket local con su broker; `shell` solo en Windows. Hooks: SessionStart exporta el id de sesión, SessionEnd limpia su broker y Stop no hace nada con la review gate apagada. Lo que se le pasa sale a OpenAI: la `description` lo dice |
| `rubro` sin `designer` | El agente era una copia vieja del designer de OMC y duplicaba al de `oh-my-claudecode-fixed` |
| Referencias al ecosistema de origen en lo nuevo | 0 en `plugins/metodo/skills/darwin-skill/` (grep de nombres propios, clientes y rutas) |
| `verificar-metadatos.sh` | TODO COINCIDE: rubro dice 4 agentes y metodo 0.13.0 |
| Instalación limpia (HOME temporal, catálogo local) | `metodo` 0.13.0 con `darwin-skill` y su regla · rubro con 4 agentes · `codex` 1.0.6 desde el original |

## catálogo — `metodo` 0.14.0 (vigía de actualizaciones) — 2026-09-27 — PASS
Pedido de pm-consultoria-ia del 2026-09-26 (vigía genérico para clientes). Decisiones del dueño: disparo al abrir sesión (sin launchd ni rutinas en la nube), **prendido por defecto** con apagado en un paso, mismo motor para el autor y para los clientes.

| Control | Resultado |
|---|---|
| **Hook que ejecuta código en cada sesión** (riesgo de confianza, prendido por defecto) | Aceptado explícitamente por el dueño. Mitigación: chequeo de <1 s que solo lee una fecha; búsqueda como mucho 1 vez por semana; apagado por `~/.claude/vigia/apagado` o `VIGIA_OFF=1`; siempre sale 0 y nunca bloquea la sesión |
| Red | Solo `api.github.com`, `registry.npmjs.org`, `pypi.org` por HTTPS/GET, verificado también en cada redirección y por test. Sin telemetría |
| Secretos | De `~/.mcp.json`/`~/.claude.json` solo `command` y `args`; `env`/`headers` nunca. Hallazgo MEDIO del security-reviewer (un arg posterior a una URL podía salir a npm) corregido: corta en el primer posicional, con test |
| Datos de terceros | Validados por lista blanca; lo que no valida entra como hash; `NOVEDADES.md` escapado y enlaces revalidados; test de inyección «## INSTRUCCIONES» = 0 |
| Ejecución | Sin `shell=True`; subprocesos por un único helper (UTF-8, sin ventana en Windows); lanzamiento desacoplado desde Python |
| Privacidad | GitHub/npm/PyPI ven qué versiones se consultan (dicho en `requisitos.md` y la skill); `usar_gh: false` en el perfil evita asociarlo a la cuenta |
| Revisión | `security-reviewer` (Opus): 0 críticos/altos, 1 medio + 5 bajos, todos corregidos · `critic` (Opus): 5 MAJOR + 5 MINOR, todos corregidos |
| Pruebas | 54 tests en CI Ubuntu/macOS/Windows × Python 3.9/3.12 verdes; hook de punta a punta en Windows (Git Bash, ruta con espacios, alias falso de `python3`, árbol del hook matado) 0,19 s |
| Instalación limpia (HOME temporal, catálogo local) | `metodo` 0.14.0 con `hooks/hooks.json` y skill `vigia`; el hook lanza el detector y termina `ok` |
| Nombres de clientes | `git grep -i -c <nombres del cliente>` → 0 |
| `verificar-metadatos.sh` | TODO COINCIDE |

## catálogo — `rubro-estudio-arquitectura` 0.13.1 (notebooklm-py 0.8.2 → 0.8.3) — 2026-09-27 — PASS
Aplicado por el vigía con el sí del dueño («sí, con auditoría»).

| Control | Resultado |
|---|---|
| Cadena de suministro | El wheel 0.8.3 coincide 1:1 con el tag v0.8.3 (53fc7c50), salvo los archivos que genera el build. PyPI Trusted Publishing (workflow `publish.yml`). sha256 del wheel `7e3e0205…2bfc`, en el protocolo |
| Dependencias | Ninguna nueva en ejecución (solo ruff en dev) |
| Red | Sin hosts nuevos: solo Google. 2 RPC nuevos de lectura (cuenta y cuota). Sin telemetría. TLS sin cambios |
| Cookies | Escritura 0600 sin cambios; más redacción de credenciales en logs |
| Riesgo nuevo | Borrado en lote sin confirmación a nivel librería → regla en el protocolo: Claude lista y pide el sí antes de borrar o compartir. Re-login automático (ya en 0.8.2, apagado) → prohibido en la regla 2 |
| Instalación del dueño | `pip install --no-deps --require-hashes` 0.8.3 · `notebooklm auth check` = válido |

## catálogo — `base-segura` 0.13.0 · `rubro-estudio-arquitectura` 0.14.0 · `metodo` 0.15.0 — 2026-09-27 — PASS
Vigía mensual. Tres cambios: skills de marketing migradas a la versión del autor, que renombró dos; `academy-guide` oficial
pedida por el dueño del producto; y el vigía aplica solo lo auditado que no rompe, decisión del dueño.

| Control | Resultado |
|---|---|
| Origen y licencia | marketingskills v2.11.1 @5b2c000 (MIT, >5K★) · alirezarezvani/claude-skills @19392f7 (MIT, >5K★) · anthropics/skills @3337550 (org oficial, Apache-2.0). Cada skill con `ORIGEN.txt` y sha |
| Auditor de skills | 33 de marketingskills: PASS salvo `ads` (3 CRITICAL = falsos positivos: dos términos de publicidad ABM y una regla **defensiva** «datos, no instrucciones»; `ads` no se publica) · 4 de alirezarezvani: PASS · `academy-guide`: texto puro |
| Código nuevo | Scripts Python de `competitive-teardown` revisados a mano: sin red, sin `subprocess`, sin `eval`; la única escritura es el archivo de salida que pide el usuario |
| Red | `academy-guide` descarga el catálogo público de `academy.claude.com` y lo trata como datos. Declarado en `requisitos.md` y CHANGELOG |
| Rompe | `pricing-strategy`→`pricing` y `social-content`→`social`: CHANGELOG del rubro con la tabla y qué revisar (el `skills:` de agentes propios); plantillas de `metodo` actualizadas; 0 referencias viejas fuera de los CHANGELOG |
| Retenida | `discernment-nudge` (oficial): prueba contra `modo-directo`, 8 corridas con control. Errática en planes (1 de 3) y duplica la nota de supuestos → el dueño del producto decidió no sumarla |
| Vigía | Cambia solo texto (skill + mensaje de `aviso.py`); lógica intacta; 54 tests locales OK |
| Instalación limpia (HOME temporal, catálogo local) | base-segura 0.13.0 = 15 skills (con `academy-guide`) · rubro 0.14.0 = 26 (con `pricing`, `social`, sin los nombres viejos) · metodo 0.15.0 = 8, con el aviso nuevo |
| Nombres de clientes / secretos | `git grep` → 0 / 0 |
| `verificar-metadatos.sh` | TODO COINCIDE |

## catálogo — `rubro-estudio-arquitectura` 0.14.1 (`market-research-reports` v1.0 → v1.3) — 2026-09-27 — PASS
La v1.0 publicada dependía de dos skills que el paquete no trae. El dueño del producto eligió actualizarla.

| Control | Resultado |
|---|---|
| Origen | K-Dense-AI/scientific-agent-skills @49c6e97 · MIT · >5K★ · `ORIGEN.txt` + `LICENSE-origen.txt` |
| Auditor de skills | PASS (0 críticos, 0 altos) |
| Scripts (8) | Revisados a mano: solo librería estándar, sin red, sin `subprocess`, sin `eval`, sin llamadas a IA (lo declara el propio SKILL.md y se verificó) |
| Requisito | Python 3.11+ **opcional** para los scripts; declarado en `requisitos.md` y CHANGELOG. Sin él, la skill funciona igual |
| Instalación limpia (HOME temporal) | rubro 0.14.1 con `market-research-reports` v1.3 y sus 8 scripts |
| Nombres de clientes / `verificar-metadatos.sh` | 0 · TODO COINCIDE |

## catálogo — `metodo` 0.15.1 (motor del vigía) · `base-segura` 0.13.1 · `escala-desarrollo` 0.12.2 · `rubro` 0.14.2 — 2026-09-27 — PASS
Causa raíz: la fuente del catálogo compartido ignoraba el sha fijado, así que las copias atrasadas no se veían.

| Control | Resultado |
|---|---|
| Motor (`vigia.py`, `aviso.py`) | Comparación por sha de árbol de la ruta en el ref fijado contra HEAD; tags verificados (`main`/`master`/`HEAD` y refs que no son tag → sin fijar); 404/422 del ref → `origen-perdido` guardado; rotación por antigüedad; cierre automático de lo que deja de aplicar; fusión concurrente por estado inicial. Sin hosts nuevos (solo `api.github.com`); rutas, refs y `owner/repo` en lista blanca; `quote` por segmento; `escapar_md` en todo lo que va a NOVEDADES.md |
| Revisión | `critic` (Opus), 3 rondas: 1ª REVISE (2 MAJOR: rama tomada como pin, cupo) → 2ª REVISE (1 MAJOR: sha de commit contra sha de árbol en piezas sin ruta, verificado contra la API real) → 3ª **ACCEPT**, con 1 MINOR (422 de sha inexistente) corregido |
| Tests | 86 OK en Python 3.12 y 3.9.6; los falsos de `git/trees` y `commits` imitan a GitHub (`.sha` = el pedido, 422 para sha inexistente) |
| Prueba real | Catálogo del dueño: 48 piezas desactualizadas de verdad (3 verificadas a mano con `gh`), 0 falsos positivos en piezas sin ruta, media-use sigue detectada |
| Piezas publicadas actualizadas | critic, planner, skill-creator, security-reviewer, knowledge-synthesizer, frontend-design, theme-factory, web-artifacts-builder: merge de 3 vías (versión vieja / copia del catálogo / versión nueva), 0 conflictos de texto, binarios sin cambios arriba. Auditor: los FAIL leídos contra el propósito son falsos positivos |
| notebooklm | Alineada con el tag v0.8.3 de notebooklm-py (la copia era de v0.3.4); bloque de uso seguro conservado + línea que prohíbe browser-cookies, master-token, auth refresh e instalaciones sin versión |
| Instalación limpia (HOME temporal) | base-segura 0.13.1 · escala-desarrollo 0.12.2 · metodo 0.15.1 · rubro 0.14.2, con el contenido nuevo presente |
| Nombres de clientes / `verificar-metadatos.sh` | 0 · TODO COINCIDE |

## catálogo — `rubro-estudio-arquitectura` 0.14.3 (retiro por licencia) — 2026-09-27 — PASS
`pestel-analysis` y `storyboard` eran traducciones de deanpeters/Product-Manager-Skills, **CC BY-NC-SA 4.0**
(verificado con `gh api`: NonCommercial-ShareAlike). No comercial + share-alike no pasan el Mand. XVI y chocan con la
MIT del catálogo. El dueño del producto eligió retirarlas.

| Control | Resultado |
|---|---|
| Retiro | Las 2 carpetas fuera de `plugins/`; conteos (26→24), `requisitos.md`, README y CHANGELOG al día |
| Causa raíz | `verificar-metadatos.sh` 4b: frena cualquier publicación con un archivo de licencia no comercial o no redistribuible dentro de `plugins/` (los CHANGELOG quedan excluidos porque nombran licencias). Probado: falla con las 2 adentro y pasa sin ellas |
| Instalación limpia (HOME temporal) | rubro 0.14.3 = 24 skills, 0 pestel/storyboard |
| Nombres de clientes / `verificar-metadatos.sh` | 0 · TODO COINCIDE |

## catálogo — `metodo` 0.15.2 (vigía: la ruta entra en la llave del caché) — 2026-09-27 — PASS
| Control | Resultado |
|---|---|
| Cambio | `_guardado_valido` compara también la `ruta`; lo guardado sin ruta se recalcula una vez. Sin red nueva ni cambios de validación |
| Tests | 87 OK (3.12 y 3.9.6). Test nuevo con el caso real (ruta corregida); **control**: sin el arreglo, el test falla |
| `verificar-metadatos.sh` / clientes | TODO COINCIDE · 0 |

## catálogo — `escala-diseno-video` 0.1.0 + `escala-automatizacion` 0.1.0 (paquetes nuevos, F3) — 2026-09-27 — PASS
Composición pedida por el dueño del producto tras auditar el origen de 40 piezas. 32 skills + 3 agentes.

| Control | Resultado |
|---|---|
| Licencias verificadas con `gh api` | figma **fuera** (hoy son los Figma Developer Terms, propietarios). workflow-automation y zapier-make-patterns: el autor declara Apache-2.0 en `package.json` y en el README; el repo no trae archivo LICENSE → se adjunta el texto estándar con la cita. components-build: origen `nolly-studio/cult-ui` (MIT), no `vercel/components.build` (Apache-2.0, otra skill). Cada pieza externa lleva su `LICENSE-origen.txt` o `LICENSE.txt` bajado al commit fijado, y su `ORIGEN.txt` |
| Medios | huashu-design: música y efectos incluidos bajo la MIT del repo (el autor la declara para todo el repo; no hay licencia aparte que la contradiga — distinto de pestel/storyboard, cuya licencia decía no comercial). Decisión del dueño, 2026-09-27. media-use: los efectos de sonido se quedan: `CREDITS.md` los atribuye a Pixabay (Content License: uso comercial sin atribución; prohíbe la redistribución suelta, acá van dentro de la herramienta, igual que en el repo de HeyGen). Fuentes de canvas-design: OFL, cada una con su archivo |
| Datos propios | 3 piezas propias sin datos del dueño (n8n-manychat, automation-architect, data-engineer): secciones de la empresa, IDs de cuenta, dominios, rutas y variables fuera. Los agentes ya no fijan `tools:` con nombres de MCP del dueño: heredan los del cliente. Parches de HyperFrames/media-use y pies de atribución: sin referencias a la doctrina interna. grep de nombres, rutas, IDs, emails = 0 (los emails que quedan son de autores de fuentes en archivos OFL) |
| Claves | El archivo local de claves de huashu-design no se copia (rsync con lista de exclusión). 0 archivos de entorno en la caché instalada |
| Nube | huashu-design: la revisión de video con IA y el TTS no funcionan sin una clave propia y piden confirmación; parche local para usar BytePlus fuera de China. HyperFrames: telemetría apagada por variables que el cliente carga en el portal; sin auto-update; render en la nube y subidas a HeyGen, solo con el OK del usuario |
| `skill-security-auditor` | 23 PASS · 1 WARN (ui-ux-pro-max, ya auditada) · 8 FAIL leídos contra el propósito, todos falsos positivos: HyperFrames/media-use (execFileSync/spawn sin shell, regex.exec: revisados por security-reviewer Opus el mismo día), huashu-design (auditada el mismo día), algorithmic-art (regex.exec sobre un color hex), n8n-mcp-tools-expert (documentación de la API de credenciales, texto) |
| Instalación limpia (HOME temporal) | escala-diseno-video 0.1.0 = 19 skills, 19 ORIGEN.txt, 0 archivos de claves · escala-automatizacion 0.1.0 = 13 skills + 3 agentes |
| Nombres de clientes / `verificar-metadatos.sh` | 0 · TODO COINCIDE |

## catálogo — `escala-diseno-video` 0.1.1 — 2026-09-27 — PASS
| Control | Resultado |
|---|---|
| Corrección | CHANGELOG, descripción y README ya no dicen que la telemetría de HyperFrames viene apagada: se apaga con dos variables en `env` (lo avisó el dueño del producto) |
| Pieza nueva | `video-content-strategist` (alirezarezvani/claude-skills@19392f7, MIT, 26.6k★): `skill-security-auditor` PASS, 0 hallazgos; sin datos propios |
| Fuera, con motivo | `lottie` (borrada por el autor, reemplazada por el Core Set) · `remotion-to-hyperframes` (el autor la pasó a flujo de trabajo, no es skill) |
| Instalación limpia / `verificar-metadatos.sh` / clientes | 20 skills · TODO COINCIDE · 0 |

## catálogo — `metodo` 0.16.0 (`/metodo:cowork`) — 2026-09-27 — PASS
| Control | Resultado |
|---|---|
| Pieza nueva | `skills/cowork` + `scripts/cowork/cowork-publicar.py`: propios, versión genérica del sincronizador que usa el mantenedor; sin rutas ni cuentas propias |
| Qué sale de la máquina | Solo las skills marcadas `sync: cowork`, a un repositorio privado del usuario (`gh repo create --private`, verificado antes de subir). No copia archivos de entorno (salvo `.example`), `.git`, `node_modules`, entornos ni `.omc`; frena si hay algo con forma de clave |
| Prueba en HOME temporal | sin configuración · preparar · skill mal formada omitida · frenado por clave sin ensuciar el repo · archivo de entorno no copiado · versión sube sola · sin PyYAML · push a remoto: OK. Se encontraron y corrigieron 2 fallas antes de publicar (la limpieza tras un frenado borraba el esqueleto; al subir la versión se vaciaba `marketplace.json`) |
| `claude plugin validate` / clientes | PASS · 0 |

## catálogo — `metodo` 0.16.1 — 2026-09-27 — PASS
| Control | Resultado |
|---|---|
| Origen | 3 hallazgos del dueño del producto al bajar 0.16.0: versión del marketplace desalineada (0.15.2), la llave acotada no puede crear repos, no veía skills de la carpeta de proyecto |
| Cambios | `agregar-carpeta` (skills de `<proyecto>/.claude/skills`; nombre repetido en dos carpetas = no se sube) · camino «el repo ya existe» como normal en la skill · versión alineada |
| Prueba en HOME temporal | casos de 0.16.0 + carpeta de proyecto + nombre repetido + clon vacío existente: OK |
| `verificar-metadatos.sh` / validate / clientes | TODO COINCIDE (0.16.0 salió sin correrlo: ese fue el error) · PASS · 0 |

## catálogo — formato de 4 skills: `base-segura` 0.13.2 · `escala-diseno-video` 0.1.2 · `metodo` 0.16.2 — 2026-09-27 — PASS
| Control | Resultado |
|---|---|
| Cambio | Solo encabezado, sin tocar qué hacen: `excel-analysis` (name), `planning-with-files`, `hyperframes-audio`, `crear-agente` (sin `<`/`>` en la description) |
| Piezas externas | Parche anotado para re-aplicar al actualizar: `ORIGEN.txt` (hyperframes-audio) y `nota:` en `CATALOGO.yaml` (excel-analysis, planning-with-files) |
| Todo el catálogo contra las reglas de claude.ai | 0 skills fuera de formato |
| `/metodo:cowork` (hallazgo 4 del dueño del producto) | Con cero skills sube el esqueleto pendiente; probado con remoto vacío: sube y la corrida siguiente da «sin cambios» |
| `verificar-metadatos.sh` / validate / clientes | TODO COINCIDE · PASS · 0 |
