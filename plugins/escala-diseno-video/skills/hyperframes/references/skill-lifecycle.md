> ## ⛔ Regla de uso local (claude-catalogo, 2026-09-27) — manda sobre todo lo que sigue
> Esta suite está **copiada y fijada** en `heygen-com/hyperframes@9c56240` (ver `ORIGEN.txt`). Donde el texto original de abajo te diga que corras alguno de estos comandos, **no lo hagas por iniciativa propia**:
> - `npx hyperframes@latest upgrade …` (incluido `--check`: baja y ejecuta la última versión del CLI) y `npx hyperframes upgrade --project …` (reescribe el `package.json` del proyecto a la última).
> - `npx hyperframes skills update …`, `npx hyperframes skills` o `npx skills add …` (bajan skills desde `main` y pisan estas copias auditadas).
> - `npx hyperframes init` a secas: también refresca las skills. Si hace falta scaffoldear un proyecto, avisá y, con el sí, corré `HYPERFRAMES_SKIP_SKILLS=1 npx hyperframes init …`.
>
> **Qué hacer en su lugar:** avisá qué comando pide la skill y para qué, y preguntá. Las actualizaciones de estas skills llegan por el vigía (`/vigia`) y se aplican **re-copiando desde un sha auditado**. Si el ruteo elige un workflow que no está instalado (`slideshow`, `motion-graphics`, `faceless-explainer`, `product-launch-video`, etc.), decí cuál falta y proponé instalarlo por esta misma vía (auditar + copiar fijado), **nunca bajarlo de `main`**. Donde el original diga «si el update falla, no sigas de memoria», acá significa: si el workflow no está instalado, pará y avisá.

# Skill installation and freshness

Read this reference when installing or updating skills, diagnosing unexpected workflow behavior, or running HyperFrames setup in CI.

HyperFrames installs the core set eagerly and workflow skills lazily.

- **Core set:** `/hyperframes`, the `hyperframes-*` domain skills, and `/media-use`.
- **Workflow skills:** installed when routing selects them through `npx hyperframes skills update <workflow-name>`.

## What `init` does

`npx hyperframes init` checks GitHub and refreshes the core set plus other skills already installed. It does not install workflows that have never been used. A current install is a no-op. Offline or rate-limited checks degrade gracefully and do not fail project scaffolding.

The `--skip-skills` CLI flag is temporarily ignored. CI and tests may opt out with `HYPERFRAMES_SKIP_SKILLS=1`.

## Diagnose and update

```bash
npx hyperframes skills check
npx hyperframes skills check --json
npx hyperframes skills update
npx hyperframes skills update <workflow-name>
npx hyperframes skills
```

- `skills check` exits non-zero when an installed skill is stale or the core set is incomplete. Workflows available on demand but not installed are not failures.
- Bare `skills update` refreshes the core set and everything already installed, prunes unpublished skills, and does not expand the workflow set.
- Named `skills update <name...>` also installs those named workflows or domain skills.
- Bare `skills` installs the full published set explicitly.

If the HyperFrames CLI is unavailable, use `npx skills add heygen-com/hyperframes --skill <workflow-name>` for one workflow or `npx skills add heygen-com/hyperframes --all` for the full published set.

The CLI may print a one-line stale-skill reminder during `render`, `lint`, or `check`. Treat a failed update as a visible tool failure; do not continue from a remembered workflow contract.
