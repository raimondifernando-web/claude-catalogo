# Graphify — el mapa de tu código, para que Claude no lo lea entero cada vez

> Herramienta externa (`Graphify-Labs/graphify`, Apache-2.0, 120.000 estrellas), revisada el 2026-09-22
> sobre el código de la versión 0.9.65. **No es una skill de este catálogo**: es un programa aparte que se
> instala una vez y deja un mapa dentro de cada proyecto. Igual que con NotebookLM, acá va el protocolo.

## El problema que resuelve (y por qué te va a pasar)
Cuando le pedís a Claude que entienda un proyecto, abre archivo por archivo hasta hacerse una idea. En una
carpeta chica no se nota. En un proyecto que **vos mismo fuiste construyendo con Claude durante meses**, sí:
cada pregunta vuelve a leer medio proyecto, y eso se paga en tiempo y en cuota. El problema no aparece el
primer día — aparece cuando la herramienta ya te funciona y se hizo grande.

Graphify recorre el proyecto una vez y arma un **mapa**: qué archivo llama a cuál, qué depende de qué, qué
partes forman un bloque. Claude consulta el mapa en vez de abrir todo.

## Lo que mide de verdad (no lo que promete)
La página de la herramienta promete **71,5x menos tokens**. Medido sobre un proyecto real de 352 archivos
de código, con la misma pregunta de arquitectura:

| | Sin el mapa | Con el mapa |
|---|---|---|
| Lo que consume | 4.584.928 | **2.831.312** |
| Lo que sale | USD 2,60 | **USD 1,65** |
| Lo que tarda | 32 segundos | 173 segundos |

**Ahorro real: 38%, no 71 veces.** Sirve, pero no es magia, y se paga con espera: lee menos, pero piensa
más veces seguidas. Conviene cuando le dejás a Claude un trabajo largo; molesta si estás esperando de a una.
(Una corrida de cada una, no un promedio: tomá la dirección, no el decimal.)

## Los dos modos — y cuál usar
Esta es **la** decisión de la herramienta, y la que te puede salir cara si la pasás por alto.

| | Modo mapa de código | Modo con IA |
|---|---|---|
| Comando | `graphify update .` | `/graphify .` dentro de Claude |
| Qué entiende | Solo código | Además documentos, PDF, imágenes, video |
| Qué tarda | **8 segundos** | 13 minutos y subiendo |
| Qué cuesta | **nada, cero** | **USD 12 medidos — y no llegó a terminar** |

**Usá siempre `graphify update .`** El modo con IA manda tus archivos a Claude en tandas y lo pagás vos.
Puede valer la pena algún día sobre una carpeta de documentos puntual, con la decisión tomada y sabiendo el
precio. Nunca por costumbre y nunca automático.

## Las 5 reglas (obligatorias)
1. **El bloque «Graphify» va al `.gitignore` DEL PROYECTO antes de la primera corrida.** El mapa
   (`graphify-out/`) incluye comentarios y textos sacados de tu código, y la herramienta recomienda subirlo al
   repositorio. Y escribe sus enganches en `.claude/settings.json`, que es el archivo que **viaja** con el proyecto
   (ahí va lo compartido, como el catálogo pre-listado): en otra computadora sin Graphify darían error. Van a
   `.claude/settings.local.json`, que no viaja — Graphify lo soporta, y Claude Code los ejecuta igual desde ahí.
   El `.gitignore` de fábrica del kit ya trae el bloque. Tiene que estar en el `.gitignore` del proyecto, no en
   una configuración general de tu computadora: así viaja con el proyecto a cualquier máquina. Si igual se te
   pasa, `/metodo:cerrar` lo detecta y lo agrega solo.
2. **Instalar siempre parado dentro del proyecto**, con `graphify install --project`. Así toca únicamente esa
   carpeta. Verificado: de este modo **no toca nada de tu configuración general**.
3. **Nunca `--strict`.** Es el único modo que puede negarle a Claude el permiso de abrir un archivo.
4. **Sobre carpetas que no son tuyas** (lo que te mandó un cliente o bajaste de internet): solo el modo mapa
   de código. El texto de un documento ajeno puede terminar copiado dentro del informe que Claude después lee
   como si fuera documentación tuya. Es acotado, pero el camino existe.
5. **Empezá por un proyecto de prueba**, no por el que estás usando para trabajar.

## Qué te deja en la máquina, y cómo se saca
Deja el programa, y dentro del proyecto una carpeta con el mapa más dos enganches que hacen que Claude lo
consulte antes de buscar. Si además corrés `graphify hook install`, cada vez que guardes cambios el mapa se
rehace solo en segundo plano (se corta solo a los 10 minutos, no se queda colgado).

Se saca entero: `graphify uninstall` deja la configuración y los enganches como estaban; `graphify uninstall
--purge` borra además el mapa; y `uv tool uninstall graphifyy` saca el programa.

## Lo más fácil: «mapeá este repo»
Con el paquete `metodo` (0.19.0 o más), parado en tu proyecto le pedís a Claude **«mapeá este repo»** y corre
`metodo/scripts/graphify-en-repo`: hace los pasos de abajo en el orden seguro (regla en el `.gitignore` del proyecto,
comprobación, instalación en la carpeta, mapa gratis, enganches a `settings.local.json`) y guarda solo `.gitignore` y
`CLAUDE.md`, por nombre. No toca la configuración general de git de tu computadora y no sube nada. Exige Graphify
**0.9.65**, la versión revisada acá: con otra, para y te dice el comando para ponerla. Termina en una línea («Listo ✓» o
«Falta: … ✗»).
Lo que queda fijado es Graphify; las librerías que trae adentro las elige el instalador (`uv`) al instalar. Es un riesgo
aceptado y anotado (revisión de seguridad de `metodo` 0.19.0): el código revisado es el de Graphify 0.9.65.

## Instalar a mano
```
uv tool install graphifyy==0.9.65  # una sola vez en la computadora (la versión revisada)
cd <tu proyecto>
# regla 1, antes que nada: si tu .gitignore no es el de fábrica del kit, copiale el bloque «Graphify»
git check-ignore -v graphify-out/x .claude/settings.local.json
#   ↑ tiene que listar las dos, y CADA línea empezar con `.gitignore:` (o `<carpeta>/.gitignore:`).
#     Si empieza con `.git/info/exclude` o con una ruta que arranca en `/`, la regla vale solo en esta
#     computadora: no viaja con el repo. Si el patrón empieza con `!`, NO está ignorado. En los tres casos: rojo.
graphify install --project          # regla 2
graphify update .                   # el mapa, gratis
# y los enganches a settings.local.json: lo hace /metodo:cerrar solo en el próximo cierre
```
