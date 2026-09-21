# NotebookLM desde Claude — protocolo de uso seguro

> Para la skill `notebooklm` (paquete `rubro-estudio-arquitectura`), que usa la librería no oficial `notebooklm-py`.
> Revisado 2026-09-21 sobre el código de la versión 0.8.2: se conecta solo a dominios de Google, guarda las cookies
> en tu computadora con permisos de solo-tu-usuario y no manda datos al autor. **El riesgo no es el código: es la
> llave.** La librería funciona con la sesión (cookies) de una cuenta Google. Quien tenga ese archivo, tiene esa cuenta.

## Poner las cosas en su lugar
Tu navegador ya guarda esas mismas cookies de tu cuenta, en tu computadora, todos los días. La herramienta **no crea un
riesgo nuevo de tipo**: agrega una segunda copia de la llave y se la da a un programa de un tercero. Por eso lo que importa es
(a) que el programa sea el revisado y no cambie solo, (b) que esa copia no salga de tu máquina, (c) saber revocar en un minuto.
Con eso se puede usar con tu cuenta de siempre. **Las 5 reglas de abajo son obligatorias.** La cuenta dedicada
(`notebooklm.<empresa>@gmail.com`, sin Gmail ni Drive en uso) es un **refuerzo opcional**: conviene cuando la computadora la usa
más gente, no la controlás vos, o preferís que la llave valga poco. Si la usás, compartí los cuadernos entre las dos cuentas.

## Las 5 reglas (obligatorias)
1. **Versión fija y revisada.** `python3 -m pip install --user 'notebooklm-py[browser]==0.8.2'` y `python3 -m playwright install chromium`.
   No se actualiza "a la última": cada versión nueva la revisa tu consultor antes.
2. **Iniciar sesión solo desde la ventana que abre la herramienta**: `notebooklm login` → se abre un navegador → entrás con tu cuenta.
   ⛔ Nunca `notebooklm login --browser-cookies …` (copia la sesión de tu Chrome de todos los días) ni ninguna opción con
   "master token" (una llave que no vence).
3. **La carpeta `~/.notebooklm/` se queda en tu máquina.** No en Drive/iCloud, no en un backup que comparta más gente. Cifrado del
   disco (FileVault) encendido y sesión de la Mac con contraseña.
4. **Nunca pegar, mandar ni leer ese archivo** en un chat, mail o issue. Claude tampoco lo lee: solo corre `notebooklm auth check`.
5. **Saber revocar.** Si perdés la máquina, cambiás de computadora o ves algo raro: `notebooklm logout` + en tu cuenta Google →
   Seguridad → *Tus dispositivos* → cerrar sesión. La copia muere ahí.

## Verificar (una vez, y cada tanto)
`notebooklm auth check` tiene que mostrar solo dominios `google.com` / `notebooklm.google.com`. Tu cuenta Google con
**verificación en dos pasos** y la contraseña en tu gestor de contraseñas.

## Lo que sigue siendo cierto aunque hagas todo esto
- Es **no oficial**: Google puede cambiar algo y la herramienta deja de andar hasta que el autor la arregle. Plan B siempre disponible:
  la skill `notebooklm-preparar` te deja todo listo para pegarlo a mano en notebooklm.google.com.
- Automatizar un servicio sin API va contra la letra de los términos de Google. El riesgo práctico es bajo y lo asumís vos, informado;
  tu consultor lo deja por escrito.

## Chequeo rápido (para Claude, antes de usar la skill)
| Verificar | Cómo | Si falla |
|---|---|---|
| Herramienta instalada | `command -v notebooklm \|\| python3 -c "import notebooklm"` | «Falta instalar notebooklm-py — ver `docs/NOTEBOOKLM-SEGURO.md`» |
| Hay sesión y es sana | `notebooklm auth check` (solo status, no imprimir cookies) | «Hay que iniciar sesión: `notebooklm login`» |
| Reglas aceptadas | Preguntar una vez: «¿Leíste las 5 reglas de NOTEBOOKLM-SEGURO.md y las aceptás?» y anotarlo en el `CLAUDE.md` de la carpeta («NotebookLM: 5 reglas aceptadas ✓ <fecha>») | Hasta entonces: `notebooklm-preparar` (camino manual) |
