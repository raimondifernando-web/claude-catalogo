# Enrutador de IA — spec (2026-10-05)

**Problema (medido):** el radar ya dice qué IA conviene por categoría, pero (1) solo mide el cupo de Codex: Claude y
Antigravity figuran siempre «disponibles», y (2) solo *recomienda*: nadie ejecuta. Resultado: el plan A (Claude) se usa
para todo, Codex se agota y Gemini queda en 7 % de uso semanal. Una regla en un `CLAUDE.md` no alcanza; hace falta una
pieza que mida, elija y ejecute, y que la usen las sesiones, el Bicho y los clientes (Consultoría IA).

## Piezas (todo en `plugins/metodo/scripts/`, solo biblioteca estándar, Python 3.6+)
1. **Lectores de cupo** en `radar.py` (junto a `cupo_codex`), mismo contrato `(nivel, texto)` con nivel
   `ok | alto | agotado | desconocido`; umbrales: ≥70 % usado → `alto` (solo tareas chicas), ≥90 % → `agotado`.
   - `cupo_claude()`: `claude -p /usage --output-format text --no-session-persistence --settings '{"disableAllHooks":true}'`
     (0 tokens, 30 s de tope); se toma el MAYOR % entre «Current session» y «Current week (all models)». Antes se mira
     `$CEREBRO_HOME/cupo.json` (`~/.cerebro/cupo.json`) si el campo `ts` tiene menos de 15 min.
   - `cupo_antigravity()`: `agy -p "/usage" --output-format json` (0 tokens); grupo cuyo nombre empieza con «Gemini»
     (o el que corresponda al modelo del plan, ver abajo); % usado = `100 × (1 − remaining_fraction)`, el mayor entre
     ventanas. El grupo «Claude and GPT models» es otro cupo (de Google), no se mezcla.
   - `motivo_salto` usa el lector que diga `plan["cupo"]` (`claude | codex | antigravity`); `agotado` salta el plan.
     Un lector que no encuentra la CLI devuelve `desconocido` (no salta, pero tampoco se ofrece como ejecutable).
2. **Modo delegar** en `elegir`: `elegir(..., delegar=True)` ordena los planes disponibles poniendo los de
   herramienta distinta de Claude Code primero (en el orden A/B/C del radar) y Claude Code al final. Motivo: Claude es
   el coordinador y su cupo es el más caro; delegar lo acotado a Codex/Antigravity mientras tengan cupo.
3. **`delegar.py`** (nuevo): `delegar.py <categoria> <repo> <pedido.txt> [--revisar] [--sensible] [--dry-run]`.
   - elige con `elegir(delegar=True)`; `--sensible` pasa el filtro de datos privados del radar; además se niega en
     rutas que contengan `/Finanzas`, `/Personal`, `/Consultoria-Negocio`, `/clientes/` (lista ampliable con la
     variable `METODO_NO_DELEGAR`, rutas separadas por `:`), porque los planes gratuitos pueden entrenar con lo enviado.
   - exige repo git; para editar, árbol limpio (si no, sale con 66 y dice qué hacer).
   - adaptadores: **codex** → `codex exec -C <repo> --sandbox workspace-write -` (con `--revisar`: `--sandbox read-only`),
     pedido por stdin; **antigravity** → `agy --model <modelo del plan> --mode accept-edits|plan --add-dir <repo> -p "<pedido>\n\nNO corras ningún comando…"`
     (como `~/.claude/scripts/agy-delegar`, que es la versión de Orquesta); **claude** → no ejecuta: imprime
     «el plan elegido es Claude Code: hacelo en esta sesión» y sale con 3.
   - al terminar: `git status --short` + `git diff --stat` y «Todo al día ✓»; nunca corre tests ni commitea.
   - códigos: 0 bien · 1 sin plan disponible · 2 categoría desconocida · 3 le toca a Claude · 64 uso · 65 carpeta
     privada · 66 árbol sucio · 67 la CLI del plan elegido no está instalada · 70 la herramienta terminó con error (no se devuelve su código: podría chocar con los reservados) · 124 no terminó a tiempo (`METODO_DELEGAR_TOPE`, 1 h).
4. **Distribución:** plugin `metodo` → clientes (rama `estable`, 48 h). Las reglas del método (`reglas.py`) y la skill
   `radar` pasan a decir «delegá con `delegar.py`» en vez de «elegí de memoria». Orquesta: `~/.claude/scripts/agy-delegar`
   queda como atajo y la regla XXVII apunta a `delegar.py`.
5. **Bicho:** ya muestra las tres barras (Claude, Codex, Gemini); no cambia.

## Fuera de alcance (a propósito)
- Usar los modelos Claude/GPT-OSS que ofrece `agy` con el cupo de Google: falta verificar términos y calidad.
- Cambiar el orden A/B/C del radar (sale de fuentes independientes, no de opinión).

## Pruebas (en `scripts/tests/`, sin red ni CLIs reales: se simulan con scripts falsos en un directorio temporal)
Cada lector con salida real, vacía y rota; `motivo_salto` por nivel; `elegir(delegar=True)`; `delegar.py` con CLIs
falsos (codex, agy) para los 3 adaptadores, `--dry-run`, árbol sucio, carpeta privada, CLI ausente.

## Endurecimiento (revisión de seguridad 2026-10-05, antes de publicar)
`git` siempre con `-c core.fsmonitor=false -c core.hooksPath=/dev/null -c diff.external=` y sin bloqueos opcionales; hash de
`.git/config` y hooks antes y después de la herramienta (cambió → código 71). El pedido es TEXTO; solo es archivo con
`--archivo` (rechaza nombres de claves y más de 100 KB). Primera vez: `delegar.py --aceptar` (código 68 mientras tanto).
Se bloquea el repo igual a la carpeta personal o a `/`, y se mira también la raíz del repo y la ruta tal como se escribió.
`modelo_api` y el esfuerzo se validan con `^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$`; los binarios solo valen con ruta absoluta,
ejecutables y fuera del repo; los lectores de cupo corren en una carpeta neutra, sin entrada y con `--setting-sources user`;
`cupo.json` se lee con tope de 64 KB y porcentajes entre 0 y 100; al vencer el tiempo se corta el grupo de procesos entero.
Límite conocido: enlaces simbólicos dentro del repo y lectura fuera del repo del sandbox de solo lectura de Codex.
