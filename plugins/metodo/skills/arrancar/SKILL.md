---
name: arrancar
description: "Protocolo de arranque de sesión: leer el estado, confirmar el rol y verificar el entorno ANTES de tocar nada. Usala cuando el usuario escriba 'arrancá', 'empecemos', 'seguimos', 'continuá donde quedamos', al abrir una sesión nueva (con o sin prompt de reanudación pegado), o al empezar a trabajar en un tema por primera vez. Es el espejo de /metodo:cerrar."
---

# /metodo:arrancar — Arrancar leyendo, no adivinando

Una sesión que arranca mal re-hace trabajo, vuelve a discutir decisiones tomadas y pisa lo que otra sesión
dejó. Este protocolo cuesta dos minutos y evita todo eso.

## Secuencia (en orden, antes de tocar NADA)

### 1. ¿Tengo contrato?
- **Si el usuario pegó un prompt de reanudación** (bloque `═══ PARTE A`): ese es tu contrato. Leelo entero.
  Tu ROL, tu alcance y tus reglas salen de ahí, no de tu intuición.
- **Si NO hay contrato**: reconstruilo ANTES de trabajar: `CLAUDE.md` de la carpeta de trabajo (quién es el
  usuario, cómo trabaja) + el último archivo en `handoffs/` (dónde quedó todo). Declarale al usuario el rol que
  asumís: "Voy a trabajar como [rol] sobre [tema]".

### 2. Leer el estado (no re-hacer, no re-discutir)
- Último handoff del tema en `handoffs/` de la carpeta de trabajo: qué se hizo, qué se decidió, qué falta.
- Las decisiones ya tomadas NO se reabren. Si creés que una está mal, lo decís una vez, con evidencia, y seguís.
- La lista **A VERIFICAR** del prompt (si hay): esas verificaciones son TUYAS, hacelas temprano.

### 3. Verificar el entorno (el archivo manda sobre la memoria)
- ¿La carpeta abierta es la de trabajo (`~/Documents/<Empresa>-Claude/`) y no otra?
- **Si el texto de arranque declara `Copia: <ruta> · Rama: <tema/fecha>`** (PARTE B): verificalo con `pwd` y
  `git branch --show-current`. **Si no coincide, PARÁ y avisá** — «Este texto es para la copia X en la rama Y, y
  estoy en Z. No trabajo en la copia equivocada: abrí la ventana en la carpeta correcta o dame el texto de esta.»
  No sigas con "ya que estoy": trabajar en la copia equivocada pisa a otra sesión.
- **Si no lo declara y hay otra sesión abierta sobre el mismo proyecto** (el usuario lo dice, o `git worktree list`
  muestra más de una copia): antes de tocar nada, proponé abrir esta sesión en su propia copia con
  `/metodo:otra-sesion`. Regla 11: una sesión, un tema, una copia.
- ¿Las herramientas que voy a usar están disponibles (plugins, conectores)? Si no: avisar, no simular.
- Cualquier número que vayas a usar ("hay N archivos", "son N clientes") se cuenta ahora, no se recuerda.

### 4. Confirmar y arrancar
Confirmale al usuario en 2-3 líneas: **"Leí el estado. El próximo paso es [X]. ¿Arrancamos?"**
Si el prompt ya trae el próximo paso definido y contexto suficiente, arrancá directo: la confirmación es
para alinear, no para pedir permiso de trabajar.

## Reglas del arranque
- **Nada de escribir antes del paso 3.** Ni "mejoras rápidas" ni limpiezas oportunistas fuera de lo pedido.
- **Si algo del estado contradice los archivos, ganan los archivos**, y lo avisás (el estado puede estar viejo; el disco no).
- **Si la carpeta de trabajo no tiene `CLAUDE.md`**, eso es lo primero: proponer crearlo (plantilla en `base-segura/templates/CLAUDE-empresa.md`).

## Qué NO es esta skill
No reemplaza a `/metodo:cerrar` (cierre), `/metodo:planear` (planificación) ni `/metodo:otra-sesion` (abrir una
segunda sesión sin pisarse). Es solo la apertura. Atajo: si no tenés otra skill llamada `arrancar`, `/arrancar` a secas
también la activa.
