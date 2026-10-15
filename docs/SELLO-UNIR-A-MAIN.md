# El sello para unir a `main` (metodo 0.41.0)

**En una frase:** antes la sesión *decía* «lo revisaron» y «la persona dijo que sí»; ahora el programa lo *comprueba él* y la sesión ya no tiene cómo afirmarlo.

## El problema
`unir-a-main` tenía tres opciones que cualquier sesión podía escribir: `--revisado-por`, `--ok-fernando`, `--sin-pruebas`. Una sesión engañada por un texto malicioso podía escribirlas sin que fueran ciertas. La única barrera era el permiso de la app, y ese «sí» no puede ser la defensa: nadie puede juzgar código a ojo cada vez.

## Cómo funciona ahora
Las tres opciones **ya no existen**. El programa hace él mismo, en este orden, y si algo falla no une:

1. **Solo repos de la lista** (`unir-a-main.txt`). Sin lista, no une nada.
2. **Mira qué archivos cambiaron** y los compara con una lista de «cosas que corren solas en la computadora» (tareas, hooks, instaladores, `.mcp.json`, `package.json`, `.husky`, `.envrc`, tareas del editor, y los programas a los que apuntan los hooks). Esa lista sale de `main` y del propio programa: **nunca de la rama** que se está juzgando.
3. **Corre las pruebas aisladas**: en una copia limpia, con el entorno vacío (sin claves, sin tu carpeta personal), **sin internet** y, en Mac, sin poder escribir fuera de la copia.
4. **Lanza a un revisor independiente** (otro Claude, sin herramientas, que solo ve el cambio real leído de git). Contesta verde, amarillo o rojo. **Solo puede endurecer**: rojo no une nunca; amarillo te pregunta; verde no reemplaza nada de lo anterior.
5. **Solo si hace falta, te pregunta a vos**, con una frase en criollo: qué toca y qué dijo el revisor. En Mac la pregunta es la **pantalla segura del sistema (Touch ID o tu contraseña)**: un botón común de ventana lo puede apretar otro programa o una sesión con permisos de accesibilidad; la pantalla de contraseña no. Cancelar o dejar vencer (3 minutos) es «no». Queda atada a ese commit. Se te pregunta cuando: toca algo que corre solo, el revisor dudó, no hay pruebas y hay código, o las pruebas no se pudieron aislar.
6. **Arma el sello**: un archivo con el commit exacto, el resumen (hash) del cambio que vio el revisor, las pruebas, el veredicto y tu OK. Se guarda dentro de `.git/sellos/` y su huella queda escrita en el commit de unión en `main`. Es un **rastro para auditar**, no una firma: quien pueda subir a `main` podría escribir un texto igual.

Además el programa se defiende de la propia sesión: se corre con `python3 -I`, **limpia el entorno** (no hereda variables de git, de Anthropic ni de Python), saca la carpeta personal de la cuenta del sistema (no de `$HOME`), usa siempre `~/.claude/unir-a-main.txt`, desactiva los hooks y filtros de git del repo, y compara mayúsculas y minúsculas sin distinguir (el disco de la Mac no distingue).

Para repos con GitHub (el catálogo): sigue igual, por PR; la etiqueta `ok-fernando-<commit>` solo la pone la persona.

**También te pregunta si:** la rama borra archivos de pruebas, hay archivos binarios o enlaces simbólicos/submódulos o cambios de permisos (el revisor no los puede leer), cambian instrucciones que siguen todas las sesiones (`CLAUDE.md`, skills, agentes y comandos de `~/.claude`), o el remoto tiene una dirección de subida distinta a la de bajada.

## Qué cubre y qué no (en criollo)
- **Cubre:** una sesión engañada que usa el programa por el camino normal. Ya no puede afirmar nada; todo lo comprueba el programa. Un cambio peligroso en lo que corre solo la frena, y si el revisor ve algo feo, no pasa ni con tu «sí».
- **No cubre:** una sesión que se saltea el programa y hace `git push` directo. Esa defensa no puede estar en la Mac: tiene que ser la regla de GitHub (rama protegida, solo por PR con checks). Para los repos que importan, activarla.
- **El revisor es una IA:** puede equivocarse o ser engañado por un texto dentro del cambio. Por eso decide poco: solo suma frenos, nunca quita los que ponen las reglas fijas.
- **Las pruebas no son un detector de maldad.** Un cambio malicioso puede traer sus propias pruebas «que pasan». Sirven contra roturas accidentales; el aislamiento (sin internet, sin leer tu carpeta personal, sin lanzar programas fuera) es lo que contiene el daño.
- **Aislamiento completo solo en Mac.** En otro sistema, el programa te pregunta antes de unir.
- **Pendiente fuera de este programa:** hoy la configuración de Claude (`~/.claude/settings.json`) deja a la sesión editar la copia viva de `unir-a-main` y de su lista de repos sin pasar por ningún control. Hay que cerrarlo ahí (pasarlo a «pedir permiso siempre»). Es una decisión de Fernando/Tech: este trabajo no toca esa configuración.

## Las otras correcciones de la revisión
- Los archivos que deciden cómo se corren las pruebas (`Makefile`, `package.json`, `conftest.py`, `.claude/pruebas.sh`…) ya no los puede cambiar la rama sin que te pregunten.
- Los paneles ya no suben a carpetas de afuera del repo: no pueden mostrar los pendientes de otro proyecto.
