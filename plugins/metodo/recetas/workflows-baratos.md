---
name: workflows-baratos
triggers: workflow workflows github actions cron n8n ci minutos matriz runner robot programado schedule dispatch automatizacion
---
Receta para crear o tocar un workflow de GitHub Actions (regla 25). En un repo PRIVADO se pagan los minutos (Linux ×1, Windows ×2, macOS ×10) y el plan trae un tope por mes; al llegar, los robots se frenan. El 2026-10-19 un ecosistema chico llegó al 90 % por corridas de 1 minuto disparadas desde afuera, sin cancelar las viejas.
1. **Primero preguntate si hace falta Actions.** Algo que corre por reloj y no necesita el repo (consultar una API, mandar un aviso) vive mejor en n8n o en un servidor chico, donde no se paga por corrida. Actions es para lo que toca el código del repo.
2. **Plantilla mínima:** `runs-on: ubuntu-latest`, `timeout-minutes: 10`, y arriba `concurrency:` con `group: <nombre>-${{ github.ref }}` y `cancel-in-progress: true`. Si el workflow escribe en algo y no se puede cortar a la mitad, `false` con `# actions-ok: concurrencia <por qué>`.
3. **Cron:** una línea `# <para qué y por qué a esa hora>` al lado y nunca más seguido que cada hora. No sumes un reloj si ya lo dispara n8n o un webhook.
4. **Quien despacha no manda corridas vacías:** cada corrida cobra 1 minuto mínimo aunque no haya nada que hacer. Antes de despachar, el que dispara mira si hay trabajo (un pedido nuevo, una transferencia pendiente).
5. **Un solo disparador por cambio:** `pull_request` para revisar; `push` solo a `main` (`branches: [main]`). Los dos a la vez corren todo dos veces.
6. **Pruebas pesadas** (instalar dependencias, bajar caché, correr 20 min): `cache` en el setup, corré solo lo que cambió (`paths:`), y lo largo semanal o a mano antes que diario.
7. **Rojo = roto.** Nada que falle a propósito para esperar un OK: cada fallo manda un mail. Si necesitás esperar una aprobación, que quede pendiente, no en error.
8. **Cómo se comprueba:** el check `controles` corre `workflow-lint.py` en cada PR; a mano, `python3 <metodo>/scripts/workflow-lint.py --todo` audita todo el repo. Tus minutos: `python3 <metodo>/scripts/actions-consumo.py --informe` (estimado; el aviso sale solo al abrir la sesión desde el 60 %).
9. **Si ya estás cerca del tope:** primero se optimiza (puntos 1-6); pagar más o fijar un tope de gasto lo decide la persona, con el costo a la vista.
