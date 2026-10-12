# escala-desarrollo

## 0.14.4 — 2026-10-12
- **`/escala-desarrollo:revision-seguridad` se activa sola con más pedidos.** Claude la usa cuando le pedís revisar la seguridad, auditar el código, buscar vulnerabilidades o claves sueltas, hacer un pentest liviano o «chequear que sea seguro antes de publicar», también si lo decís de forma indirecta («me preocupa que roben datos», «¿se puede publicar sin riesgos?»). En las pruebas la usó en todas esas frases y en ninguna que no era de seguridad.
- **Si pedís el revisor de seguridad directamente** (sin pasar por el comando), su informe termina con una línea destacada: «NO CORRIERON ESCÁNERES — esta revisión está incompleta», con el comando que falta correr. Así nunca queda la sensación de que se revisó todo cuando no se corrieron los escáneres.

## 0.14.3 — 2026-10-12
- **Comando nuevo: `/escala-desarrollo:revision-seguridad`.** El revisor de seguridad no puede ejecutar nada (por diseño), así que los escáneres los corre **tu sesión, y vos aprobás cada comando**: `npm audit` (si hay `package-lock.json`), `pip-audit -r requirements.txt` (si hay) y una búsqueda de claves en el historial de git. Después le pasa todo al revisor, que lo analiza junto con el código y lo resume en «Qué escáneres corrieron y qué dijeron».
- **Las claves nunca se muestran completas:** la búsqueda en el historial tapa cada valor (4 caracteres y el largo) y avisa si la clave sigue en el código; una clave que estuvo en el historial hay que rotarla aunque ya no esté.
- Si una herramienta no está instalada, lo dice y no inventa el resultado. No instala nada ni toca tus archivos. Necesita `python3` para la parte del historial; `npm` y `pip-audit` son opcionales (solo se usan si tu proyecto los necesita).

## 0.14.2 — 2026-10-12
- **`security-reviewer` ahora es solo lectura de verdad.** Antes tenía desactivado escribir y editar archivos, pero podía ejecutar comandos (y por ahí modificar cosas). Ahora solo lee y busca, y te entrega el informe con el arreglo propuesto. Usa el método de seguridad del creador de `agent-skills` (`security-and-hardening`), que se instala solo como dependencia y se actualiza sola. Lo llamás igual que antes.
- **Qué cambia en la práctica:** como no ejecuta comandos ni tiene internet, **no puede correr `npm audit` / `pip-audit` (vulnerabilidades de las librerías) ni buscar claves en el historial de git**. Lo dice en su informe («Qué no pude comprobar») y te pide que le pegues la salida de esos comandos si querés que la analice. Nunca repite una clave completa en el informe.

## 0.14.1 — 2026-10-12
- **`code-reviewer` ahora es solo lectura de verdad.** Antes decía que no editaba archivos, pero podía sobrescribirlos ejecutando comandos; en una prueba lo hizo. Ahora no tiene permiso de escribir **ni de ejecutar comandos**: lee, busca y te entrega el informe con el arreglo propuesto. Como no ejecuta nada, para revisar cambios recientes indicale los archivos o pegale el diff.
- Usa el método de revisión del creador de `agent-skills` (cinco ejes, severidades Critical/Required/Optional/Nit, veredicto), que se actualiza solo. Ese plugin se instala solo como dependencia: no tenés que hacer nada. Lo llamás igual que antes.

## 0.14.0 — 2026-10-03
- **Agente nuevo: `scientific-literature-researcher`.** Busca estudios publicados (revistas, PubMed, arXiv) y te arma una respuesta apoyada en evidencia: qué método usó cada estudio, con cuántos casos y qué límites tiene. Lo llamás pidiéndoselo a Claude, por ejemplo «que scientific-literature-researcher busque qué dicen los estudios sobre X». Busca en la web abierta, sin servicios pagos.

## 0.13.0 — 2026-10-03
- **8 agentes nuevos.** Para construir: `python-pro`, `javascript-pro`, `sql-pro`, `data-analyst`, `prompt-engineer` y `documentation-engineer`. Para decidir: `product-manager` (qué hacer primero) y `technology-scout` (¿lo hago o lo compro?, qué herramienta conviene). Los llamás pidiéndoselo a Claude, por ejemplo «que python-pro arme el script» o «technology-scout: ¿qué uso para X?».

## 0.12.3 — 2026-10-03
- Sincronizadas skills desde ~/.claude/skills.


## 0.12.2 — 2026-09-27
- `security-reviewer` y `knowledge-synthesizer` pasan a la versión nueva de sus autores. El revisor de seguridad ahora siempre cierra con el informe completo (alcance, nivel de riesgo, hallazgos y checklist), aunque haya ido anotando cosas en el camino. Se usan igual que antes.

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
