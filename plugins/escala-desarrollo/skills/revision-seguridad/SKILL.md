---
name: revision-seguridad
description: "Revisión de seguridad completa de tu app, en dos pasos: primero corre en tu sesión, pidiéndote aprobación comando por comando, los escáneres que apliquen a tu proyecto (npm audit, pip-audit y una búsqueda de claves en el historial de git con los valores tapados); después le pasa esa salida al revisor de seguridad de solo lectura, que la analiza junto con el código. Usala antes de publicar o entregar una herramienta, o cuando pidas «revisá la seguridad»."
argument-hint: "[carpeta del proyecto; por defecto la actual]"
---

# Revisión de seguridad con escáneres

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
