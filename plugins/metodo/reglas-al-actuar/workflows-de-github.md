---
herramientas: Write|Edit|MultiEdit
patron: \.github[/\\]workflows[/\\]
---
Vas a escribir un workflow de GitHub Actions: texto completo de la regla 25 del método.

25. **Un workflow de GitHub Actions nace barato y silencioso** (en repos privados GitHub cobra los minutos; al tope, los robots se frenan): solo Linux; `concurrency:` con `cancel-in-progress: true`; cada `cron:` con su motivo y no más seguido que cada hora; `timeout-minutes` en todo job; no `push` y `pull_request` a la vez. Excepción escrita en el archivo: `# actions-ok: <regla> <motivo>` (lo controla `scripts/workflow-lint.py` en el check `controles`). Un reloj externo no dispara corridas vacías. Rojo = roto: nada falla a propósito para esperar algo. `actions-consumo.py` avisa al 60/80/90 % de los minutos; desde el 80 % no se suman robots ni crons. Toda automatización de GitHub (workflow, ruleset, instalador en varios repos) se prueba ANTES de punta a punta en un repo PRIVADO real, sin dejar restos, y recién en verde se despliega (si el repo de prueba falla, no se sigue con los otros); el PR lleva `Probado-en: <repo privado> (<qué corriste>)`.
