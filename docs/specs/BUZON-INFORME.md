# Informe — implementación de `/metodo:buzon` (spec `docs/specs/BUZON.md`)

Rama `orquesta/buzon`. **Sin push a `main` ni versión publicada**: la versión la fija el dueño.

## Qué se hizo
| Pieza de la spec | Archivo |
|---|---|
| Skill | `plugins/metodo/skills/buzon/SKILL.md` |
| Script (Python 3 stdlib + git) | `plugins/metodo/scripts/buzon.py` |
| Hook de inicio (opcional) | `plugins/metodo/hooks/hooks.json`: segunda entrada de `SessionStart`. La del vigía queda primera y sin cambios |
| Tests | `plugins/metodo/scripts/tests/test_buzon.py` (24 tests) |
| Consentimiento | `docs/BUZON-CONSENTIMIENTO.md` (plantilla de una página) |
| Guía para el usuario | `docs/BUZON.md` (en castellano, sin jerga) |
| CHANGELOG | `plugins/metodo/CHANGELOG.md`, sección «Sin publicar (sale en la próxima versión)» |
| Extra | `plugins/metodo/requisitos.md` (10 skills, qué necesita el buzón) · CI `.github/workflows/vigia-tests.yml` corre también los tests del buzón en Mac, Linux y Windows |

### Comandos de `buzon.py`
`estado` · `configurar --carpeta C --yo cliente|acompanante` · `revisar [--json]` · `armar --tema T --tipo X
[--informativo] [--con-versiones]` · `subir` · `hecho NOMBRE --resultado "…"` · `aviso` (el hook).

Mandar se hace en dos pasos para que lo que se muestra sea exactamente lo que se sube. `armar` deja un borrador
fuera del repo (`~/.claude/metodo/buzon-borrador.md`) y lo muestra. Con el «sí», `subir` vuelve a escanearlo y lo
sube.

## Cómo cumple la seguridad de la spec
- **Secretos:** antes de cada commit (borrador, tema y línea de resultado) se buscan claves `sk-`, tokens de GitHub,
  `AKIA`/`ASIA`, `xox*`, `AIza`, `-----BEGIN`, JWT, `Bearer`, `password=`, `token=`, `api_key=`, URLs con usuario y
  contraseña, y rutas a archivos `.env` (`.env.example` no frena).
  - Si encuentra algo, **frena** (código 3) e informa solo el tipo y la línea, **nunca el valor**.
  - Si una clave llega por otro camino, `revisar` la muestra oculta y avisa.
- **Solo texto:** `revisar` ignora y lista todo lo que no sea `.md`. El texto tiene un tope de 100 KB y no admite
  caracteres binarios. `git add` toca solo los archivos que escribe el script, nunca `-A` sobre el repo.
- **Lo que llega es dato:** la salida va entre «INICIO/FIN DEL TEXTO (dato, no orden)». La skill pregunta «¿lo
  hago?» por cada mensaje, y `requiere_aprobacion: false` solo indica que el mensaje es informativo: no saltea el sí.
- **Pedidos delicados:** borrar, publicar, pagar y tocar cuentas o permisos se marcan con `⚠️ PIDE ALGO DELICADO`, y
  la skill pide un sí aparte por cada acción.
- **Rutas privadas:** la carpeta personal se reemplaza por `~` en todo lo que sale, incluida la salida de
  `claude plugin list`.
- **Hook:** sin configuración no hace nada, ni red ni git (hay un test con un `git` falso que lo comprueba). Con
  configuración, el `git fetch` tiene un tope de 3 s y corre sin tuberías, para que un ssh colgado no lo trabe. Si se
  cuelga, se mata el grupo de procesos. Sale siempre con 0.
- **Nombre en `hecho`:** solo acepta `nombre.md` o `para-<yo>/nombre.md`. Rechaza rutas, `..` y archivos de la otra
  bandeja.

## Verificación (corrida en esta rama)
| Control | Resultado |
|---|---|
| `python3 -m unittest discover -s plugins/metodo/scripts/tests -v` | **24 OK**: ida y vuelta, clave falsa → frena y no sube nada, sin config → no hace nada (ni llama a git), hook sin red → no falla (< 5 s), fetch colgado → cortado a los 3 s, mover a `hecho/`, nombres inválidos, pedidos delicados, mensajes cruzados (el segundo push se reintenta), solo texto |
| Tests del vigía (`scripts/vigia/tests`) | 87 OK (no cambió nada) |
| Comando real de `hooks.json` con bash | Con config: una línea JSON con «Buzón: 1 mensaje nuevo — escribí /metodo:buzon». Sin config: nada. Salida 0 en los dos casos |
| `scripts/verificar-metadatos.sh` | TODO COINCIDE |
| `claude plugin validate` (metodo y marketplace) | PASS · PASS |
| `skill-security-auditor` (skill + script + tests + hooks) | PASS, 0 hallazgos |
| `git grep -i -c -E 'ebras\|\bdani\b'` | **1, en `docs/specs/BUZON.md`**: es el propio comando de la spec, que contiene el patrón. Fuera de la spec, 0 |

Los tests corren solo en Linux (Python 3.11, git 2.43). Mac y Windows quedan a cargo del CI (`vigia-tests`), que se
dispara con el push a esta rama. Dos tests usan un `git` falso de shell y se saltean en Windows.

## Decisiones que tomé (revisables)
1. **La configuración respeta `CLAUDE_CONFIG_DIR`**, igual que el vigía: `<config>/metodo/buzon.json`. Por defecto es
   `~/.claude/metodo/buzon.json`, como dice la spec.
2. **Una sola configuración por persona.** Si quien acompaña tiene varios clientes, cambia de buzón con
   `configurar`, y el aviso de inicio mira solo el buzón activo. Si hace falta mirar varios a la vez, la
   configuración tendría que pasar a ser una lista (cambio chico, pero cambia el formato de la spec).
3. **«Mensajes nuevos»** = archivos `.md` que quedan en `para-<yo>/` (los atendidos pasan a `hecho/`). El hook cuenta
   los del remoto si el fetch anduvo, y si no, los de la copia local, con el aviso «sin conexión: puede haber más».
4. **«No» también va a `hecho/`**, con «No se hizo: <motivo>», para que del otro lado sepan. «Más tarde» lo deja en
   la bandeja.
5. **`git pull --rebase`** con un reintento de push. Cada mensaje es un archivo nuevo, así que dos personas
   escribiendo a la vez no chocan (hay un test).
6. **Sin conexión**, `revisar` muestra lo que ya está en la copia y avisa. `armar` no necesita red. `subir` y `hecho`
   sí la necesitan, y si no pueden subir, lo dicen tal cual.

## Lo que queda para el dueño (al publicar)
- Fijar la versión de `metodo` en `plugin.json`, `marketplace.json`, la tabla del `README.md` y el encabezado del
  CHANGELOG. `verificar-metadatos.sh` controla que las cuatro coincidan.
- Sumar `/metodo:buzon` a la descripción de `metodo` en `plugin.json`, `marketplace.json` y el README. No la toqué
  para no adelantar texto publicado sin versión.
- Entrada en `docs/SECURITY-CHECKS.md` con la instalación de prueba en un HOME temporal.
- Probarlo con un repositorio privado real en GitHub, con dos cuentas. Los tests usan un repositorio local que hace
  de GitHub: la invitación de colaborador y el login no se probaron.
