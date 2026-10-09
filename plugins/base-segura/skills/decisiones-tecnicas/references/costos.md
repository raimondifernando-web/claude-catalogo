# Costos: topes y sorpresas

## Principio
**Todo servicio que cobra por uso lleva un tope duro configurado el día que se crea la cuenta, no "después".**
Un aviso por mail no es un tope: avisa, no frena. El tope es lo que pausa el servicio.

## Lista de control al recomendar un servicio de pago
| Pregunta | Qué anotar |
|---|---|
| ¿La cuota es fija o hay cobro por uso además? | Fija = predecible. Variable = exige tope |
| ¿Existe un límite duro (pausar/cortar al llegar a X)? ¿Está activado? | Dónde se configura, qué monto sugerido, quién lo activa |
| ¿Hay aviso por mail y por mensaje al 50/80/100 %? | Quién lo recibe |
| ¿Qué pasa al llegar al tope (se apaga el servicio, se degrada)? | Aceptable o no para el negocio |
| ¿El plan gratis permite uso comercial? | Muchos planes gratis son solo personales |
| ¿Cuándo renueva y a qué precio? | Promos de primer período que suben al renovar |
| ¿Hay tarjeta aceptada? | Ver `alojar.md` |

## Decisiones, motivo y cuándo NO aplican
| Decisión | Motivo | Cuándo NO aplica |
|---|---|---|
| **Tope duro en hosting, IA por API y plataformas de automatización** | El incidente de hosting (ver `alojar.md`): límite deshabilitado + builds multiplicados + caché apagado → cobro sin techo; el mail del proveedor sobre la cuota avisó, pero no frenó nada | Planes de precio fijo sin cobro por uso |
| **Aviso a más de una persona** | Un único destinatario de vacaciones = nadie se entera | Empresa de una persona |
| **Mirar el gasto diario los primeros días de un servicio nuevo**, y la curva: pareja = automatización; picos = tráfico humano | La forma de la curva descartó hipótesis antes de leer código; y los sospechosos obvios (tareas programadas) resultaron costar centavos | Siempre aplica |
| **Clave de API con tope mensual propio y prepago sin recarga automática** | Un flujo seguía llamando a la IA para resúmenes que ya nadie leía; el prepago sin recarga acota el daño | Gasto mayor y previsto, con presupuesto aprobado |
| **Preferir precio fijo (VPS, plan por usuario) cuando el uso es parejo y predecible** | Lo que se puede presupuestar se puede aprobar | Uso muy variable o picos raros: pagar por uso sale más barato |
| **Revisar suscripciones olvidadas cada tanto** | Se acumulan cuentas de pruebas | Siempre aplica |
| **No se baja la seguridad para ahorrar** | En el incidente de hosting, la optimización obvia era sacar archivos del control de acceso; ese control era la contraseña de los tableros. Se logró el mismo ahorro con caché solo en el navegador del usuario ya autenticado | Siempre aplica |
| **Una cosa por vez en una intervención urgente** | Mezclar el arreglo de costos con una actualización de dependencias hace imposible saber cuál rompió algo después | Si la dependencia es la causa del problema |

## Formato en la recomendación
`Costo: <fijo> + <variable estimado: cómo se calculó o "a confirmar"> · Tope sugerido: <monto> · Quién lo activa y dónde: <panel>`
Si no se puede estimar el variable, decilo y recomendá empezar con tope bajo.
