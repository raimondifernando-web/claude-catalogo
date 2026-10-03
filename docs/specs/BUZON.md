# Spec — `/metodo:buzon`: canal directo entre quien acompaña y el cliente (sin copiar y pegar)

## Problema
Hoy una indicación viaja: sesión del acompañante → copiar → WhatsApp → pegar en la sesión del cliente. Y los errores del
cliente vuelven igual, resumidos a mano. Caso típico: el acompañante está sentado en la compu del cliente siguiendo pasos,
uno se traba y necesita la respuesta de su propia sesión (que tiene el contexto).

## Solución: un repo privado de GitHub como buzón
- Un repo privado por cliente (lo crea quien acompaña; el cliente acepta la invitación como colaborador).
- Carpetas: `para-cliente/` · `para-acompanante/` · `hecho/`. Un mensaje = un archivo `AAAA-MM-DD-HHMM-<tema>.md`
  con frontmatter: `de`, `para`, `tipo` (indicacion | error | resultado | aviso), `requiere_aprobacion` (true por defecto).
- Config local por persona: `~/.claude/metodo/buzon.json` → `{"carpeta": "<clon local>", "yo": "cliente" | "acompanante"}`.
  Sin ese archivo, la skill no hace nada (apagado = borrar el archivo).

## Comandos (skill `plugins/metodo/skills/buzon/SKILL.md` + `plugins/metodo/scripts/buzon.py`, Python 3 stdlib + git)
1. `/metodo:buzon` (o «revisá el buzón»): `git pull`, lista los mensajes nuevos para mí, los muestra **como datos, no órdenes**.
   Para cada uno: resume qué propone y pregunta «¿lo hago?». Solo ejecuta con «sí». Al terminar mueve el mensaje a `hecho/`
   con una línea de resultado y hace commit + push.
2. `/metodo:buzon enviar [tema]`: arma un mensaje con lo que pasó en la sesión (paso que se trabó, comando, error textual,
   versión de lo instalado: `claude --version`, `claude plugin list`), lo muestra, y con «sí» lo sube.
3. Hook de inicio (opcional, `hooks/`): una línea «Buzón: N mensajes nuevos — escribí /metodo:buzon». Sin red si no hay
   config; con config, `git fetch` con timeout de 3 s; nunca falla el arranque.

## Seguridad (no negociable)
- **Nunca viajan secretos.** Antes de cada commit, `buzon.py` escanea el mensaje con patrones de claves (sk-, ghp_, AKIA,
  xox, `-----BEGIN`, `password=`, `token=`, etc.) y rutas de archivos de variables de entorno; si encuentra algo, **frena** y lo dice.
  Nunca adjunta archivos: solo texto.
- Lo que llega es **dato**: la skill nunca ejecuta nada sin el «sí» de quien está en la compu (regla 3 del método).
- Mensajes que piden borrar, publicar, pagar o tocar cuentas: se muestran con aviso destacado y piden confirmación aparte.
- Autenticación = permisos de GitHub del repo privado (solo los dos colaboradores). Registro = el historial de git.
- Consentimiento: `docs/BUZON-CONSENTIMIENTO.md` (plantilla de una página que el cliente acepta por escrito).
- El repo del buzón nunca guarda datos de otros clientes ni rutas privadas del acompañante.

## Pruebas (obligatorias)
Tests en `plugins/metodo/scripts/tests/test_buzon.py` con dos clones de un repo bare temporal (cliente y acompañante):
ida y vuelta, mensaje con clave falsa → frena, sin config → no hace nada, hook sin red → no falla, mover a `hecho/`.

## Entregable
Rama `orquesta/buzon` con skill + script + tests verdes + plantilla de consentimiento + `docs/BUZON.md` para el usuario
(en castellano, sin jerga) + entrada en CHANGELOG de metodo (versión la fija el dueño). **Sin push a main.**
`scripts/verificar-metadatos.sh` en verde; `git grep -i -c -E 'ebras|\bdani\b'` = 0.
