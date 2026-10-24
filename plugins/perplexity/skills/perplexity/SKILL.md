---
name: perplexity
description: Cuándo y cómo usar Perplexity (búsqueda en internet con respuesta ya armada y fuentes citadas) y cómo poner tu clave. Usala cuando pidan buscar algo actual del mundo exterior (precios, normas vigentes, proveedores, novedades, comparar opciones) y se quiera la respuesta con citas, o cuando digan «Perplexity», «buscá en internet con fuentes», «¿qué dice la norma hoy?», «falta la clave de Perplexity» o «cómo pongo la clave».
version: "0.1.0"
origen: propio (Consultoría IA); usa el servidor oficial @perplexity-ai/mcp-server (MIT) fijado en 1.3.0
sync: si
---

# Perplexity — búsqueda con citas

Disparador: por intención (las frases de arriba) · encadenado: el aviso de arranque del plugin la nombra cuando falta la clave.

## Qué es
Una forma de preguntarle cosas actuales a internet y recibir la respuesta ya armada, con los links de donde salió. Funciona con **tu propia cuenta** de Perplexity (la paga quien la crea; la clave es tuya y no se comparte).

## Cuándo usarla
- Preguntas del **mundo exterior** que cambian con el tiempo: normativa vigente, precios, proveedores, novedades, «qué cambió este año».
- Cuando querés la respuesta **con fuentes** y no solo una lista de links.
No sirve para leer una página entera ni para navegar (para eso, la búsqueda web de Claude y sus lectores de páginas).

## Cómo usarla (cuatro herramientas)
| Herramienta | Para qué | Ojo |
|---|---|---|
| `perplexity_ask` | Respuesta rápida con citas. **La de todos los días.** | — |
| `perplexity_search` | Resultados crudos (links) con filtros de fecha o sitio | — |
| `perplexity_reason` | Un análisis que necesita razonar paso a paso | Más lenta |
| `perplexity_research` | Investigación profunda en muchas fuentes | **Cara y tarda minutos: solo con un motivo claro y avisando antes** |

Reglas de uso:
1. **Una pregunta por vez.** Si se hacen varias juntas, Perplexity responde «demasiadas pedidas» (error 429).
2. **Abrí 2 o 3 citas antes de afirmar algo importante.** En una prueba, una comparación de precios venía con citas corridas (la cita no decía lo que la respuesta afirmaba). Normas y documentación oficial salieron muy bien; comparaciones de proveedores, verificalas.
3. **Lo que preguntás viaja a Perplexity.** No pongas claves ni contraseñas en una pregunta (nunca van en un chat). El resto de lo que trabajás lo podés consultar con confianza.
4. Si una respuesta decide plata o un trámite legal, es un punto de partida: se confirma en la fuente oficial.

## Si falta la clave
Si al abrir la sesión aparece «Perplexity: falta la clave», o las herramientas no están:
1. **Sacar la clave (lo hacés vos, es tu cuenta y tu plata):** entrá a `perplexity.ai/account/api`, creá una clave, cargá saldo (alcanzan US$5: una consulta cuesta centavos) y **poné un tope mensual** (por ejemplo US$10) en el panel de Perplexity.
2. **Guardarla:** abrí la Terminal, pegá el comando que trae el aviso (termina en `perplexity-clave`), pegá tu clave cuando la pida (no se ve nada al pegar; es normal) y apretá Enter. Cierra con «Perplexity ✓». Si dice «Falta: …», seguí lo que dice la línea.
3. Abrí una sesión nueva de Claude.
Revisar en cualquier momento: el mismo comando con `--estado` al final.

**Para Claude:** nunca pidas la clave por el chat, no la escribas vos ni la leas del llavero (`security … -w`); solo se comprueba que exista, con `perplexity-clave --estado`. Si la persona pega una clave en el chat, avisale que ya quedó a la vista y que conviene crear una nueva y borrar esa. La ruta del programa: `find ~/.claude/plugins/cache -name perplexity-clave | sort -V | tail -1`.

## Si algo falla
- «falta Node»: instalá Node desde nodejs.org (versión LTS) y abrí una sesión nueva.
- La clave está pero no conecta: en Claude, `/mcp` → Perplexity → reconectar; si sigue, `perplexity-clave --borrar` y volvé a ponerla (puede estar mal copiada o sin saldo).
- Solo Mac. En Windows no está probado.
