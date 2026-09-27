# escala-automatizacion — qué necesita tu computadora

Recomendado junto con `base-segura` (ver `plugins/base-segura/requisitos.md`). Para saber qué te falta: corré el chequeo
(`docs/CHEQUEO.md`).

## Lo que NO necesita nada extra
`workflow-automation` · `zapier-make-patterns` · `ci-cd-and-automation` · los 3 agentes. Ayudan a diseñar y revisar; lo que
se construye después vive en la herramienta que elijas.

## Lo que sí necesita algo

| Skill | Necesita | Si falta | Instalar |
|---|---|---|---|
| Las 7 de n8n (`n8n-*`) | Una **instancia de n8n** (n8n Cloud, pago, o instalada en un servidor). Opcional: el **conector MCP de n8n** para que Claude lea y valide tus flujos | Claude te arma el flujo en JSON y lo importás a mano | n8n.io → Cloud, o tu consultor te ayuda a instalarlo. Conector: ver `docs/CONECTORES.md` |
| `n8n-manychat` | Lo de arriba + **cuenta de ManyChat** (Pro para la API) y la página de Instagram o el número de WhatsApp conectados | No puede enviar mensajes | La clave de ManyChat se carga como credencial dentro de n8n, **nunca en el chat** |
| `entra-app-registration` | Una cuenta de **Microsoft 365 / Entra ID** con permiso de administrador para registrar apps | Te explica los pasos, pero no los podés completar | Lo autoriza el administrador de Microsoft 365 de tu empresa |
| `mcp-builder` (construir tu propio conector) | **Node.js 18+** o **Python 3.10+**, según el lenguaje que elijas | No puede probar el conector | Node.js LTS desde nodejs.org |
