---
name: revision-seguridad
description: "Revisión de seguridad completa de tu app o proyecto. Usala SIEMPRE que pidan revisar la seguridad, hacer una revisión o auditoría de seguridad, auditar el código o el proyecto, buscar vulnerabilidades, contraseñas o claves sueltas, secretos o tokens en el código o en el historial, hacer un pentest liviano, o chequear que algo sea seguro antes de publicar, entregar, subir a producción o hacer un deploy (incluso si lo piden de forma indirecta, como «me preocupa que roben datos» o «¿se puede publicar sin riesgos?»), aunque no nombren escáneres. Corre en tu sesión, con tu aprobación comando por comando, los escáneres que apliquen (npm audit, pip-audit y una búsqueda de claves en el historial de git, con los valores tapados) y después le pasa esa salida al revisor de seguridad de solo lectura, que la analiza junto con el código. Es la forma correcta de revisar seguridad: el revisor por sí solo no puede ejecutar escáneres."
argument-hint: "[carpeta del proyecto; por defecto la actual]"
---

# Revisión de seguridad con escáneres

**Disparador:** por intención + encadenada. (1) La `description` trae las frases con las que se la pide (medido: 10 de 10 con frases normales y 4 de 5 con frases indirectas, sin falsos positivos). (2) El `security-reviewer`, si lo llaman sin salida de escáneres, cierra con la línea «NO CORRIERON ESCÁNERES» que nombra este comando. Límite honesto: no es automática; si la persona delega a mano en el revisor, la skill no corre sola y solo queda a la vista el cierre del revisor.

El revisor (`escala-desarrollo:security-reviewer`) es de **solo lectura**: no puede ejecutar nada. Por eso los escáneres los corrés **vos, acá, en la sesión principal**, donde la persona ve cada comando y lo aprueba; después le pasás la salida al revisor para que la analice.

## Reglas (no negociables)
- **No pre-apruebes nada.** No uses `allowed-tools`: cada comando se le pide a la persona con el permiso normal. Corré **un comando por vez**. Si rechaza uno, seguí sin él y anotá «no corrió: rechazado».
- **Solo lectura:** no instales nada, no crees archivos de lock (`npm install`, `pip install`), no modifiques el proyecto.
- **Comandos simples:** un comando por llamada, tal cual está escrito abajo, **sin `cd`, sin `&&`, sin `;` y sin pipes**. La sesión ya está parada en la carpeta del proyecto; si te pidieron otra carpeta, avisale a la persona que abra la sesión ahí en vez de armar comandos compuestos (esos se bloquean).
- **Secretos:** nunca copies al chat ni al revisor el valor completo de una clave. El script de historial ya devuelve los valores tapados (4 caracteres + largo): usalo tal cual. Si otro comando llegara a mostrar una clave, tapala vos antes de pasarla.
- **Si una herramienta no está instalada, decilo.** Si el comando responde «command not found», escribí «no corrió: no está instalado <herramienta>» y cómo instalarlo; **no inventes resultados** ni los reemplaces por una suposición.
- Trabajá solo dentro de la carpeta del proyecto (argumento, o la carpeta actual).

## Paso 1 · Detectar qué aplica (sin ejecutar escáneres todavía)
Mirá la carpeta (con listados de archivos, no con escáneres) y armá la lista:
| Si hay… | Corre… |
|---|---|
| `package-lock.json` | `npm audit` |
| `package.json` **sin** lock | no corre: `npm audit` necesita el lock y crearlo escribe archivos. Anotalo. |
| `requirements.txt` (o `requirements-*.txt`) | `pip-audit -r requirements.txt` |
| solo `pyproject.toml`/`Pipfile`/`poetry.lock` | no corre solo: anotá qué comando le correspondería y que lo corra la persona si quiere |
| carpeta de git (`git rev-parse --git-dir` funciona) | búsqueda de claves en el historial (script de abajo) |
Mostrale a la persona la lista («voy a correr A, B y C; te pedirá aprobación cada uno») antes de empezar.

## Paso 2 · Correr de a uno
1. **npm:** `npm audit`. Un código de salida distinto de 0 quiere decir «encontró problemas», no «falló».
2. **Python:** `pip-audit -r requirements.txt`.
3. **Historial de git:** `python3 "${CLAUDE_SKILL_DIR}/scripts/claves-en-historial.py"` (sin argumentos: revisa la carpeta actual; necesita `python3`). Solo lee el historial y muestra cada hallazgo con commit, archivo, línea, tipo, valor tapado y si sigue en el código actual.
Si la salida de un escáner es enorme, quedate con el resumen y las vulnerabilidades más graves; no la recortes con pipes.
Guardá, para cada escáner: qué comando, si corrió o no (y por qué no), y su salida.

## Paso 3 · Pasarle todo al revisor
Llamá a la herramienta Agent **una vez** con `subagent_type: escala-desarrollo:security-reviewer` y un pedido que incluya:
- la carpeta a revisar y qué archivos mirar primero (los de código y configuración que detectaste);
- «Estos son los resultados de escáneres que corrió la sesión principal con aprobación del usuario; integralos en tu sección *Qué escáneres corrieron y qué dijeron*»;
- la salida de cada escáner **tal cual** (tapada), y la lista de los que **no corrieron** con el motivo.
No le pases valores completos de claves.

## Paso 4 · Entregar
Mostrá el informe del revisor completo. Después, en 3 líneas y en castellano simple: qué es lo más urgente, qué escáneres corrieron y cuáles no. **No apliques arreglos** por tu cuenta: preguntá si quiere que los hagas, y recordá que una clave que estuvo en el historial hay que **rotarla** aunque ya no esté en el código.
