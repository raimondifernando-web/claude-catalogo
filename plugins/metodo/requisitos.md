# metodo — qué necesita tu computadora

**Casi nada.** Las 9 skills (`/metodo:arrancar`, `/metodo:planear`, `/metodo:criticar`, `/metodo:cerrar`, `/metodo:crear-agente`, `/metodo:otra-sesion`, `/metodo:darwin-skill`, `/metodo:vigia`, `/metodo:cowork`) funcionan con Claude Code, sin claves. La única pieza que corre sola es el **vigía de actualizaciones** (abajo), y necesita Python 3.

`/metodo:darwin-skill` usa **git** para guardar o deshacer cada mejora, y trabaja **siempre en una copia aparte** (`git worktree`), nunca en la carpeta que usan tus otras sesiones. Tiene un script opcional que arma una imagen con el resultado: solo corre si tenés Playwright (`npm install -g playwright-core`). Sin eso, todo lo demás funciona igual.

Lo único que usan `/metodo:cerrar` (guardar y subir el avance) y `/metodo:otra-sesion` (segunda sesión en su propia copia) es **git**, que viene con las herramientas de desarrollo de Apple que ya instalaste para `base-segura`. El chequeo del catálogo lo verifica. Plantilla `templates/gitignore-estudio`: qué NO sube al repositorio por defecto (claves, documentos de clientes, archivos pesados).

Atajos: si no tenés otras skills con esos nombres, `/arrancar` y `/cerrar` a secas también funcionan. `/cerrar` deja `REANUDAR.md` en tu carpeta de trabajo y `/arrancar` lo lee solo: no hace falta pegar el texto de arranque.

`/metodo:cowork` (publicar tus skills en Cowork) necesita **Python 3**, **git** y **`gh`** (la herramienta de GitHub, `brew install gh`) con tu sesión iniciada (`gh auth login`, lo hacés vos). Crea un repositorio **privado** en tu cuenta de GitHub, solo para esto: tus skills salen de tu computadora hacia ese repositorio y hacia Cowork, nada más. Sin `gh`, lo demás funciona igual.

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

**Qué consulta, y qué se ve desde afuera.** Solo tres sitios públicos: GitHub (`api.github.com`), npm
(`registry.npmjs.org`) y PyPI (`pypi.org`). Para saber si hay versión nueva de algo tiene que preguntar por ese algo:
**esos tres sitios ven qué plugins, skills, MCPs y herramientas tenés instalados** (el nombre de cada uno va en la
consulta), igual que pasa con cualquier chequeo de actualizaciones. No manda nada más: ni tus archivos, ni tus
proyectos, ni datos a tu consultor, a quien mantiene el catálogo ni a nadie. No usa claves propias, no tiene
telemetría y no instala nada. De tu configuración de MCPs lee solo el comando y sus argumentos, nunca las claves
(`env`, `headers`). Si tenés `gh` (la herramienta de GitHub) con la sesión iniciada, la usa, y entonces GitHub además
sabe que las consultas son de tu cuenta; si no querés eso, poné `"usar_gh": false` en `~/.claude/vigia/perfil.json`
(ejemplo en `scripts/vigia/perfil.ejemplo.json`). Sin `gh`, consulta la API pública de GitHub sin cuenta, con un tope
de 40 consultas por búsqueda.

**Dónde deja lo que encuentra.** En `~/.claude/vigia/` (en Windows, `%USERPROFILE%\.claude\vigia\`; si usás
`CLAUDE_CONFIG_DIR`, adentro de esa carpeta): `NOVEDADES.md` para leer, `estado.json` para la skill y `vigia.log` si
algo falla. Sin conexión no pasa nada: reintenta al día siguiente y, si pasan más de 9 días sin poder consultar, te
avisa.

**Cómo apagarlo.** Viene prendido. Se apaga en un paso, sin desinstalar nada: creá el archivo vacío
`~/.claude/vigia/apagado`, o definí la variable de entorno `VIGIA_OFF=1`. Para prenderlo de nuevo, borrá el archivo.

**Qué necesita.**
- **Python 3.9 o más nuevo**, en cualquier sistema (`python3 --version`). En Mac viene con las herramientas de
  desarrollo de Apple que ya instalaste para `base-segura`. Si el Python que encuentra es más viejo, al abrir la
  sesión aparece «Vigía necesita Python 3.9+» y la búsqueda no corre.
- **Windows:** además, [Git for Windows](https://git-scm.com/download/win) (el método ya lo usa para `git`). Es
  obligatorio: sin él, Claude Code corre los hooks con PowerShell y la línea que lanza al vigía no funciona (no rompe
  la sesión, pero el vigía no corre nunca). Python, instalado desde
  [python.org](https://www.python.org/downloads/windows/) con la opción «Add python.exe to PATH»: el alias de la
  Microsoft Store no sirve.
- Sin Python, el vigía simplemente no hace nada: no rompe la sesión.
