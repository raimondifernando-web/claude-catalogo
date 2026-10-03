# El buzón: hablar con quien te acompaña sin copiar y pegar

> Para la skill `/metodo:buzon` (paquete `metodo`). Es opcional: si no lo armás, no hace nada.

## Para qué sirve
Hoy, cuando quien te acompaña te manda una indicación, la copia de su Claude, te la pasa por WhatsApp y vos la pegás
en el tuyo. Cuando a vos algo te da error, hacés lo mismo al revés, y en el camino se pierden pedazos del mensaje.

Con el buzón, **tu Claude y el de quien te acompaña se dejan mensajes en una carpeta compartida**. Vos le decís a
Claude «revisá el buzón» o «avisale que se trabó» y él se encarga de traer o mandar el mensaje completo, sin resumir.

## Cómo funciona, en simple
- Es un **repositorio privado de GitHub** (una carpeta en internet con historial), **uno por cliente**. Solo entran
  dos personas: vos y quien te acompaña.
- Adentro hay tres carpetas: `para-cliente` (lo que te mandan), `para-acompanante` (lo que mandás vos) y `hecho`
  (lo que ya se atendió, con una línea que dice qué pasó).
- Cada mensaje es un archivo de texto con fecha, hora y tema. Nada más: **no viajan archivos, solo texto**.
- Todo queda registrado: cada mensaje y cada respuesta quedan en el historial del repositorio, con fecha y autor.

## Qué hace Claude con lo que llega
- **Te lo muestra y te pregunta «¿lo hago?».** Nunca hace nada solo, aunque el mensaje diga «hacelo ya».
  Respondés sí, no o más tarde.
- Si el mensaje pide **borrar, publicar, pagar o tocar una cuenta**, te lo marca con un aviso y te pide un sí
  aparte para cada cosa.
- Cuando terminó (o si dijiste que no), lo pasa a `hecho` con una línea de resultado, para que del otro lado sepan.

## Qué NUNCA viaja por el buzón
- **Claves, contraseñas ni códigos.** Antes de subir cualquier mensaje, Claude lo revisa. Si encuentra algo con forma
  de clave, **frena y no sube nada**. Si alguien te pide una clave por el buzón, la respuesta es no: las claves las
  ponés vos, en tu computadora.
- **Archivos.** Ni planillas, ni planos, ni documentos. Si hace falta uno, se manda por el canal de siempre.
- **Rutas de tu computadora.** Donde diría la carpeta de tu usuario, el mensaje dice `~`.
- **Cosas de otros clientes.** Cada cliente tiene su propio buzón.

## Cómo se arma (una sola vez)
1. Leés y aceptás por escrito el consentimiento (`docs/BUZON-CONSENTIMIENTO.md`). Es una página.
2. Quien te acompaña crea el repositorio privado y te invita. Te llega un correo de GitHub: **aceptás la
   invitación**. Si no tenés cuenta de GitHub, la creás (es gratis).
3. Le decís a Claude: «configurá el buzón». Él baja la carpeta a tu computadora y deja todo listo. Si te pide
   iniciar sesión en GitHub, eso lo hacés vos.
4. Prueba: quien te acompaña te manda un aviso de prueba y vos le decís a Claude «revisá el buzón».

## El día a día
- Al abrir Claude, si hay algo para vos, aparece una línea: **«Buzón: 2 mensajes nuevos — escribí /metodo:buzon»**.
  Si no hay nada, no aparece nada.
- «revisá el buzón» o `/metodo:buzon` → te muestra los mensajes uno por uno y te pregunta.
- «avisale que se trabó el paso 4» o `/metodo:buzon enviar` → Claude arma el mensaje con el paso, el comando, el error
  completo y las versiones de lo que tenés instalado, **te lo muestra**, y lo sube solo si le decís que sí.

## Qué necesita tu computadora
**git** y **Python 3** (los mismos que ya usa el método; ver `requisitos.md` del plugin `metodo`), una cuenta de
GitHub y conexión a internet para mandar y traer. Sin conexión, el aviso al abrir cuenta lo que ya tenías y te lo
dice; lo que no se pudo subir sale la próxima vez.

## Cómo se apaga
Le decís a Claude «apagá el buzón»: borra el archivo de configuración (`~/.claude/metodo/buzon.json`) y listo, deja de
avisar y de conectarse. Para cerrarlo del todo, quien te acompaña archiva o borra el repositorio, y vos podés salir
de él desde GitHub (en el repositorio: Settings → quitarte como colaborador) y borrar la carpeta de tu computadora.
