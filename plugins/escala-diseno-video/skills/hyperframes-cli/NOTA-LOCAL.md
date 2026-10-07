> ## ⛔ Reglas locales — mandan sobre todo lo que sigue (también sobre `references/` y los workflows)
> Esta suite está **copiada y fijada** en el sha de `ORIGEN.txt`. Donde el texto de abajo te diga que corras alguno de estos comandos, **no lo hagas por iniciativa propia**:
> - `npx hyperframes@latest upgrade …` (incluido `--check`: baja y ejecuta la última versión del CLI) y `npx hyperframes upgrade --project …` (reescribe el `package.json` del proyecto a la última). Si el texto pide el chequeo de versión o el «bump» del pin del proyecto: avisá que el proyecto tiene un pin y preguntá.
> - `npx hyperframes skills update …`, `npx hyperframes skills` o `npx skills add …` (bajan skills desde `main` y pisan estas copias auditadas). Esta copia ya es la vigente: un «no-op» del update no hace falta para seguir.
> - `npx hyperframes init` a secas: también refresca las skills. Si hace falta crear un proyecto, avisá y, con el sí, corré `HYPERFRAMES_SKIP_SKILLS=1 npx hyperframes init …`.
>
> **Qué hacer en su lugar:** avisá qué comando pide la skill y para qué, y preguntá. Las actualizaciones de estas skills llegan por el vigía (`/vigia`) y se aplican **re-copiando desde un sha auditado**. Si el ruteo elige un workflow: si ya está en la carpeta de skills, usalo tal cual; si no está (`slideshow`, `motion-graphics`, `faceless-explainer`, `product-launch-video`, etc.), decí cuál falta y proponé instalarlo por esta misma vía (auditar + copiar fijado), **nunca bajarlo de `main`**. Donde el original diga «si el update falla, no sigas de memoria», acá significa: si el workflow no está instalado, pará y avisá.
>
> **Además, en esta skill:** render en la nube, `publish`, `lambda` y `cloudrun` suben el proyecto a terceros: solo con el sí del usuario.
