---
name: cerrar
description: "Cierre de sesión en un paso: guarda un handoff (qué se hizo, qué se decidió, qué falta) y SIEMPRE termina entregando el prompt de reanudación copiable para la próxima sesión. SOLO la invoca el usuario (escribe '/metodo:cerrar', 'cerrá', 'cerrar sesión', 'terminamos', 'guardá y cerrá'); Claude nunca la ejecuta por iniciativa propia, solo la PROPONE al terminar el trabajo."
---

# /metodo:cerrar — Cerrar dejando la cadena escrita

> ⛔ **Quién la invoca: el usuario, siempre.** Claude no ejecuta esta skill por su cuenta, ni aunque "cerrar"
> figure como paso de un plan aprobado. Al terminar el trabajo, confirma lo hecho en 2-3 líneas y **ofrece**
> cerrar ("¿cerramos con /metodo:cerrar?"). La invocación es del usuario.

El problema que resuelve: una sesión que cierra sin dejar registro obliga a la siguiente a arrancar ciega,
re-hacer trabajo y volver a discutir lo decidido. Por eso el cierre tiene **un entregable que no se puede
saltear: el prompt de reanudación copiable**, que el usuario pega al abrir la próxima sesión.

## ⛔ Regla de oro
**El ÚLTIMO mensaje de la sesión SIEMPRE es el prompt de reanudación copiable.** Pase lo que pase con los
demás pasos, nunca termines sin emitir ese bloque.

## Secuencia
1. **Fecha + tema.** Fecha de hoy (`date +%F`) y tema en minúsculas con guiones. El archivo del handoff se
   llama `handoffs/YYYY-MM-DD-tema.md` dentro de la carpeta de trabajo (crear `handoffs/` si no existe).
2. **Relevá el trabajo real**, mirando los archivos, no la memoria: qué se creó o modificó, qué decisiones
   se tomaron, qué quedó a medias.
3. **Bajar lo durable a su lugar ANTES de escribir el prompt.** Si esta sesión aprendió una regla permanente
   ("los presupuestos siempre en USD", "a este cliente no se le manda mail los viernes"), va al `CLAUDE.md`
   de la carpeta de trabajo, no solo al prompt. Un cambio que vive solo en el prompt se pierde en dos sesiones.
4. **Handoff** (obligatorio si se modificaron 3 o más archivos o se tomaron 2 o más decisiones): escribí
   `handoffs/YYYY-MM-DD-tema.md` con la plantilla `metodo/templates/handoff.md`: estado, decisiones (con el
   porqué), próximos pasos en orden, dudas abiertas.
5. **Confirmá al usuario** en 2-3 líneas qué quedó hecho y dónde.
6. **Validá el prompt antes de emitirlo:** tiene las dos partes; la PARTE A trae rol, alcance y reglas con
   contenido real (no una línea genérica); la PARTE B trae lo hecho, los pendientes en orden y el puntero al
   handoff; no tiene números de memoria; entra en 30-50 líneas. Si se pasa, no recortes borrando: es señal de
   que algo durable quedó sin bajar al `CLAUDE.md` (paso 3).
7. **⛔ EMITÍ EL PROMPT DE REANUDACIÓN COPIABLE** con la plantilla de abajo. Es el último mensaje.

## Plantilla del prompt de reanudación
````
═══ PARTE A — CONTRATO ═══
ROL: [cómo tiene que trabajar Claude en este tema: rol, para quién, con qué criterio]
ALCANCE: [qué toca esta sesión y qué NO; qué carpeta de trabajo]
REGLAS: [las que aplican acá: verificar antes de afirmar · secretos nunca en el chat · confirmar antes de
borrar/enviar/publicar · no adular · leer CLAUDE.md y el último handoff antes de tocar nada]

═══ PARTE B — ESTADO ═══
Seguimos con [tema]. Último cierre: YYYY-MM-DD-tema (handoffs/YYYY-MM-DD-tema.md).
Hecho esta sesión: [derivado de los archivos, no de memoria]
PENDIENTES (en este orden):
1. [próximo paso exacto]
2. ...
A VERIFICAR (si aplica): [dudas técnicas que Claude resuelve solo al arrancar]
Arrancá con /metodo:arrancar y confirmá: "Leí el estado. El próximo paso es [X]. ¿Arrancamos?"
````

## Notas
- Si el usuario dice solo "cerrá", asumí cierre completo. Si dice "cerrá rápido", saltá el handoff largo
  pero **igual emití el prompt de reanudación** (regla de oro).
- Si la conversación ya es muy larga, sugerí cerrar aunque el usuario no lo pida.
