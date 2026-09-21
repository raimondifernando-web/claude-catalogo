# NotebookLM desde Claude — protocolo de uso seguro

> Para la skill `notebooklm` (paquete `rubro-estudio-arquitectura`), que usa la librería no oficial `notebooklm-py`.
> Revisado 2026-09-21 sobre el código de la versión 0.8.2: se conecta solo a dominios de Google, guarda las cookies
> en tu computadora con permisos de solo-tu-usuario y no manda datos al autor. **El riesgo no es el código: es la
> llave.** La librería funciona con la sesión (cookies) de una cuenta Google. Quien tenga ese archivo, tiene esa cuenta.

## La regla que hace todo lo demás posible
**Se usa ÚNICAMENTE con una cuenta Google dedicada** (ej. `notebooklm.<empresa>@gmail.com`) que no tenga Gmail en uso,
ni Drive con documentos, ni pagos, ni sea la cuenta de tu empresa. Si esa cuenta se filtra, se pierde un cuaderno. Nada más.
Con tu cuenta principal o la de la empresa: **no**, aunque "sea un rato".

## Pasos (una vez)
1. **Crear la cuenta dedicada** (gratis, gmail.com). Contraseña en tu gestor de contraseñas, **verificación en dos pasos activada**,
   sin número de recuperación compartido con la cuenta principal si podés evitarlo. Si vas a usar funciones Pro, contratá
   Google AI Pro **en esa cuenta**. Sin Pro, la versión gratis alcanza para empezar.
2. **Instalar fijando la versión** (no "la última"): `python3 -m pip install --user 'notebooklm-py[browser]==0.8.2'` y luego
   `python3 -m playwright install chromium`. Cada vez que se actualice, tu consultor la vuelve a revisar antes.
3. **Iniciar sesión SOLO con el navegador que abre la herramienta**: `notebooklm login` → se abre una ventana → entrás con la
   cuenta dedicada. ⛔ Nunca `notebooklm login --browser-cookies chrome` (copia la sesión de tu Chrome de todos los días,
   con la cuenta que tengas abierta) ni ninguna opción con "master token" (una llave que no vence).
4. **Verificar**: `notebooklm auth check` tiene que mostrar solo dominios `google.com` y `notebooklm.google.com`.

## Reglas de uso
- Las fuentes que subís quedan en esa cuenta. Subí lo necesario para el cuaderno; si un documento vive en el Drive de la empresa,
  compartilo con la cuenta dedicada solo en modo lectura o subí una copia.
- La carpeta `~/.notebooklm/` **no va a la nube ni a backups compartidos** (no moverla a Drive/iCloud, excluirla de Time Machine
  si el disco de backup lo usa más gente). FileVault (cifrado del disco) encendido.
- Nunca pegar el contenido de esa carpeta en un chat, un issue o un mail. Claude tampoco lo lee: solo corre `auth check`.
- Cuando termina un proyecto largo o si sospechás algo raro: `notebooklm logout` + en la cuenta Google → Seguridad → *Tus dispositivos*
  → cerrar sesión en todos. Eso invalida cualquier copia de las cookies.

## Lo que sigue siendo cierto aunque hagas todo esto
- Es **no oficial**: Google puede cambiar algo y la herramienta deja de andar hasta que el autor la arregle. Plan B siempre disponible:
  la skill `notebooklm-preparar` te deja todo listo para pegarlo a mano en notebooklm.google.com.
- Automatizar un servicio sin API va contra la letra de los términos de Google. El riesgo práctico es bajo y lo asumís vos, no tu consultor.
  Con la cuenta dedicada, lo peor que pasa es que Google cierre **esa** cuenta.

## Chequeo rápido (para Claude, antes de usar la skill)
| Verificar | Cómo | Si falla |
|---|---|---|
| Herramienta instalada | `command -v notebooklm \|\| python3 -c "import notebooklm"` | «Falta instalar notebooklm-py — ver `docs/NOTEBOOKLM-SEGURO.md`» |
| Hay sesión y es sana | `notebooklm auth check` (solo status, no imprimir cookies) | «Hay que iniciar sesión con la cuenta dedicada: `notebooklm login`» |
| Es la cuenta dedicada | Preguntar al usuario una vez y anotarlo en el `CLAUDE.md` de la carpeta ("NotebookLM: cuenta dedicada ✓") | Si es la principal: parar, `notebooklm logout`, y seguir con `notebooklm-preparar` hasta que exista la dedicada |
