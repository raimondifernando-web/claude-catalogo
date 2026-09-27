# metodo — qué necesita tu computadora

**Casi nada.** Las 8 skills (`/metodo:arrancar`, `/metodo:planear`, `/metodo:criticar`, `/metodo:cerrar`, `/metodo:crear-agente`, `/metodo:otra-sesion`, `/metodo:darwin-skill`, `/metodo:vigia`) funcionan con Claude Code, sin claves. La única pieza que corre sola es el **vigía de actualizaciones** (abajo), y necesita Python 3.

`/metodo:darwin-skill` usa **git** para guardar o deshacer cada mejora, y trabaja **siempre en una copia aparte** (`git worktree`), nunca en la carpeta que usan tus otras sesiones. Tiene un script opcional que arma una imagen con el resultado: solo corre si tenés Playwright (`npm install -g playwright-core`). Sin eso, todo lo demás funciona igual.

Lo único que usan `/metodo:cerrar` (guardar y subir el avance) y `/metodo:otra-sesion` (segunda sesión en su propia copia) es **git**, que viene con las herramientas de desarrollo de Apple que ya instalaste para `base-segura`. El chequeo del catálogo lo verifica. Plantilla `templates/gitignore-estudio`: qué NO sube al repositorio por defecto (claves, documentos de clientes, archivos pesados).

Atajos: si no tenés otras skills con esos nombres, `/arrancar` y `/cerrar` a secas también funcionan. `/cerrar` deja `REANUDAR.md` en tu carpeta de trabajo y `/arrancar` lo lee solo: no hace falta pegar el texto de arranque.

Si igual querés ver el estado de tu equipo, corré el chequeo del catálogo (`docs/CHEQUEO.md`).

## El vigía de actualizaciones

**Qué hace.** Te avisa cuando sale una versión nueva de algo que tenés instalado (plugins, skills, MCPs y, si lo
pedís, algunas herramientas de línea de comandos). No instala ni actualiza nada: solo mira y anota. Cuando aparece
«Vigía: N novedades» al abrir Claude, pedile «revisá las novedades del vigía» y `/metodo:vigia` te propone qué conviene
y pregunta antes de tocar nada. Si una novedad es de una pieza que tu catálogo fija a una versión revisada, no la
movés vos: se la pasás a tu consultor.

**Cuándo corre.** Al abrir cada sesión, un chequeo de menos de un segundo lee su estado y, si hace falta, te avisa.
La búsqueda de versiones nuevas corre **como mucho una vez por semana**, en segundo plano: la sesión no la espera y no
gasta tokens (no usa IA).

**Qué consulta.** Solo tres sitios públicos: GitHub (`api.github.com`), npm (`registry.npmjs.org`) y PyPI (`pypi.org`).
No manda datos tuyos a nadie, no usa claves, no tiene telemetría y no instala nada. De tu configuración de MCPs lee
solo el comando y sus argumentos, nunca las claves (`env`, `headers`). Si tenés `gh` (la herramienta de GitHub)
iniciada, la usa; si no, consulta la API pública de GitHub sin cuenta, con un tope de 40 consultas por búsqueda.

**Dónde deja lo que encuentra.** En `~/.claude/vigia/` (en Windows, `%USERPROFILE%\.claude\vigia\`): `NOVEDADES.md`
para leer, `estado.json` para la skill y `vigia.log` si algo falla.

**Cómo apagarlo.** Viene prendido. Se apaga en un paso, sin desinstalar nada: creá el archivo vacío
`~/.claude/vigia/apagado`, o definí la variable de entorno `VIGIA_OFF=1`. Para prenderlo de nuevo, borrá el archivo.

**Qué necesita.**
- **Mac y Linux:** Python 3.9 o más nuevo (`python3 --version`). En Mac viene con las herramientas de desarrollo de
  Apple que ya instalaste para `base-segura`.
- **Windows:** [Git for Windows](https://git-scm.com/download/win) (el método ya lo usa para `git`) y
  [Python 3](https://www.python.org/downloads/windows/) (3.9 o más nuevo) instalado desde python.org, con la opción
  «Add python.exe to PATH». El alias de la Microsoft Store no sirve: si es lo único que hay, el vigía no corre (la
  sesión sigue normal, sin avisos).
- Sin Python, el vigía simplemente no hace nada: no rompe la sesión.
