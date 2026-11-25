# rubro-finanzas-legal

## 0.5.0 — 2026-11-25
**7 skills nuevas de análisis de mercado, educativas y de solo lectura** (MIT, versión fijada de `himself65/finance-skills`, leídas enteras antes de entrar). Se aplican solas con la actualización; las llamás pidiendo algo del tema.
- `earnings-preview` (qué espera el mercado antes de un balance) y `earnings-recap` (cómo salió el resultado y qué cambió), `estimate-analysis` (estimaciones de analistas y sus revisiones), `stock-liquidity` (qué tan fácil es entrar y salir de una acción), `stock-correlation` (qué acciones se mueven juntas), `sepa-strategy` (método Minervini: te dice si una acción «cumple o no los criterios») y `options-payoff` (cómo paga una estrategia de opciones, con gráfico).
- **Reglas duras, escritas en cada skill (`NOTA-LOCAL.md`):** nada ejecuta ni arma órdenes, no se mueve plata, no se da consejo de inversión personalizado y no se piden claves; cierran con «análisis educativo, no asesoramiento de inversión». Los datos vienen de Yahoo y pueden tener errores: contrastar antes de decidir.
- **Python:** yfinance 1.8.0 necesita Python 3.10 o más y el de Apple es 3.9, así que cada skill trae la instrucción de correr su código con `uv` (que el actualizador instala solo). Si el plugin `yfinance` está conectado, las skills pueden usar sus herramientas sin Python.
- El plugin `yfinance` (nuevo en este catálogo) llega junto con esta actualización: el actualizador instala solo todos los paquetes del catálogo. Sus herramientas dan los datos sin Python.

## 0.4.1 — 2026-11-09
- Sincronizadas skills desde ~/.claude/skills.


## 0.4.0 — 2026-10-30
**3 agentes nuevos:** `oficial-de-cumplimiento-y-datos-ar` (bases de clientes y privacidad, Ley 25.326), `revisor-de-contratos` (semáforo de riesgos, solo lectura) y `redactor-de-sop` (procedimientos de una página). Orientativos: no reemplazan a un abogado. Se aplican solos con la actualización.

## 0.3.0 — 2026-10-29
**14 agentes nuevos de administración y operaciones para pymes argentinas:** `analista-fpa-y-tesoreria`, `asesor-legal-comercial-ar`, `cobranzas-y-pagos`, `conciliador`, `controller-de-cierre`, `pm-administracion-pyme`, `jefe-de-operaciones`, `jefe-de-logistica-ar`, `gestor-de-compras-y-proveedores`, `gestor-de-reclamos-y-devoluciones`, `planificador-de-inventario`, `onboarding-y-clima`, `reclutador`, `rrhh-generalista-ar`. Orientativos: no reemplazan a un contador ni a un abogado. Se aplican solos con la actualización.

## 0.2.0 — 2026-10-22
**Nuevo agente `contador-impositivo-ar`:** el especialista en la parte impositiva y contable de tu empresa (IVA, Ganancias, Ingresos Brutos y Convenio Multilateral, retenciones y percepciones, facturación electrónica, asientos y cierres). Prepara, ordena y revisa; no firma ni presenta: llega al contador matriculado con el problema claro, la norma citada y la pregunta precisa. Ninguna cifra de memoria: cada alícuota o vencimiento va con fuente oficial y fecha, o dice «no verificado». Se aplica solo con la actualización; lo llamás pidiendo algo de impuestos o de cierre contable.

## 0.1.1 — 2026-10-03
- requisitos.md real (qué necesita cada skill y qué pasa si falta).

## 0.1.0 — 2026-10-03
- Incorporación inicial de skills.
