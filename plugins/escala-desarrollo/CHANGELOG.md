# escala-desarrollo — qué cambia para vos

## 0.12.1 — 2026-09-23
- **Nueva skill `research-deep-dive`**: para cuando necesitás una investigación a fondo sobre un tema, mercado, competidor o tecnología (no una consulta rápida). Coordina 3 agentes en cadena: uno busca y sintetiza, el segundo valida con fuentes primarias y datos duros, el tercero arma el informe final accionable. Pedilo con «investigación profunda sobre X».
- Incluye los 3 agentes que usa: `research-analyst`, `data-researcher`, `knowledge-synthesizer`.

## 0.12.0 — 2026-09-22
- **Paquete nuevo, para cuando empezás a hacer tus propias herramientas con Claude.** Si le pedís a Claude que te arme una app (un presupuestador, una planilla web, un formulario), el código lo escribe él y vos no lo podés leer. Estos dos revisores lo leen por vos antes de que la uses con clientes.
- **`code-reviewer`** encuentra lo que se rompe o calcula mal. En la prueba detectó un descuento que se aplicaba solo en un 21%, así que cada presupuesto con descuento salía más caro de lo prometido. Mostró cuánto se cobraba de más, con ejemplos.
- **`security-reviewer`** encuentra lo que te expone: claves escritas en el código, la app abierta a cualquiera en el wifi, datos de clientes (DNI, teléfono) guardados sin protección o enviados a un servicio externo.
- **Usá los dos juntos.** Sobre una app de prueba con 10 errores plantados, juntos encontraron los 10. Revisan la carpeta entera (no hace falta saber de ramas ni de git), explican cada problema por sus consecuencias y cierran con qué arreglar hoy, qué esta semana y qué antes de que la use otra persona.
- **Están hechos para revisar, no para cambiar tu código.** No tienen permiso para editar archivos. Pueden correr comandos para comprobar lo que encuentran (por ejemplo, calcular un total), pero te informan y no arreglan. Si querés que Claude aplique un arreglo, se lo pedís aparte.
- Cómo pedirlo: «revisá mi app de la carpeta X con code-reviewer y security-reviewer».
Para instalar: `claude plugin install escala-desarrollo@claude-catalogo`.
