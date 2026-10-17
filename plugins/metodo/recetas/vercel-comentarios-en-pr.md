---
name: vercel-comentarios-en-pr
triggers: vercel comentario comentarios bot pr pull request autofix auto-fix monorepo proyectos ruido review vercel[bot]
---
Receta Vercel + Auto-fix (2026-10-17, Tech). Fuentes oficiales leídas ese día: vercel.com/docs/git/vercel-for-github (sección «Silence GitHub comments»), vercel.com/docs/project-configuration/git-configuration (sección Legacy), code.claude.com/docs/en/desktop (sección «Auto-fix CI & address comments»).

**Problema.** Cada proyecto Vercel conectado a un repo comenta en cada PR y edita ese comentario en cada cambio de estado. Un monorepo con N proyectos = N comentarios editados muchas veces. El Auto-fix de Claude Desktop atiende comentarios nuevos de «un GitHub App» (lo dice la doc), así que cada edición despierta a la sesión por nada. Pasó con 4 proyectos y PR 69 a 75.

**Qué NO sirve (probado).** `"github": {"silent": true}` en `vercel.json`: la doc lo marca deprecado y en prueba real (PR de prueba, 4 proyectos) el comentario apareció igual. Auto-fix de Claude: la doc no trae ninguna opción para ignorar bots; no hay arreglo de ese lado.

**Qué sirve.** Ajuste por proyecto en el panel de Vercel: proyecto → Settings → Git → «Connected Git Repository» → apagar el interruptor de comentarios en pull requests. Repetir en CADA proyecto del repo. Los despliegues de vista previa siguen funcionando. Opcional en la misma pantalla: apagar `deployment_status` (otro ruido en el PR; antes revisar que ningún GitHub Action dependa de ese evento) y, en monorepos, el estado de commit consolidado.
Por API (probado el 2026-10-17 en 4 proyectos: la respuesta pasó de `onPullRequest: true` a `false`): `echo '{"gitComments":{"onPullRequest":false,"onCommit":false}}' | vercel api /v9/projects/<proyecto> -X PATCH --input -`. Para ver el estado: `vercel api /v9/projects/<proyecto>` (campo `gitComments`). Se deshace con `true`. Cambia la configuración del proyecto: pedir el sí a quien lo administre.
Limitaciones (doc): no se puede apagar por rama. El MCP de Vercel (`update_project`) no expone este ajuste.

**Checklist para un cliente.** 1) Contar proyectos Vercel conectados al repo. 2) Apagar los comentarios en cada uno (lo hace quien administra Vercel). 3) Abrir un PR de prueba y comprobar con `gh pr view <n> --json comments` que no hay autor `vercel`. 4) Si igual llega ruido de otro bot, ese ajuste es de esa herramienta; Claude Desktop no filtra bots.
