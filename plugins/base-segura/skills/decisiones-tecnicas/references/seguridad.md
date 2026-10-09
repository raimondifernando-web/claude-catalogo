# Seguridad: claves, publicar y vigilar

## Reglas fijas (no negociables en ningún cliente)
| Regla | Motivo / incidente | Cuándo NO aplica |
|---|---|---|
| **Secretos por referencia, nunca por valor.** Se habla del *nombre* de la variable; el valor lo escribe la persona dueña, directo en el panel o archivo de claves, nunca en el chat | Dos claves se filtraron por vectores prevenibles: un comando que *volcó todo el entorno* a pantalla, y una contraseña pegada en el chat. Los transcripts guardan todo sin redacción: **un secreto visto una vez se da por comprometido** y solo se arregla rotándolo | Credenciales de prueba de una app propia en desarrollo local |
| **Verificar que existe o que funciona, sin mostrarlo**: contar la línea (`grep -c`), o probar una llamada que devuelva solo el estado | Mostrar el valor "para chequear" es la forma de filtrarlo | Siempre aplica |
| **Si una clave se expuso: rotar**, no borrar. Borrar el archivo o el mensaje no la des-expone | Queda en historial, caché y registros | Siempre aplica |
| **Las claves van como variables de entorno del hosting o gestor de contraseñas**, nunca dentro del código ni de un repositorio, ni "por un rato" | Un repositorio publicado o compartido con la clave adentro la entrega | Siempre aplica |
| **Chequeo de seguridad antes de publicar** una herramienta pública, y de nuevo después de tocar claves o infraestructura | El primer chequeo de un repositorio entero encontró cosas que nadie había mirado (estado de sesión de herramientas dentro del repo, ramas sin protección) | Prototipos locales que nadie más ve |
| **Repositorio privado por defecto; público es una decisión** | Lo público se indexa y se copia | Código que se quiere abierto |
| **Lo instalado de afuera se filtra**: oficial del fabricante, o muy usado, o alguien leyó todo el contenido (solo si es texto puro); licencia permisiva; actividad reciente; versión fijada | Piezas con código que pide credenciales de sesión o guarda tokens en texto plano se frenaron antes de entregar | Siempre aplica |

## Monitoreo
- **Un monitor de disponibilidad gratuito** (tipo UptimeRobot) avisa cuando una URL se cae. Motivo: nadie se entera de una caída hasta que un cliente se queja. Verificá que el plan gratis permita uso comercial (las páginas oficiales a veces se contradicen).
- **No avisa gastos.** Para eso está el tope de `costos.md`. Son dos controles distintos; no los confundas.
- Antes de agregar un monitor: ¿qué URLs importan de verdad y quién recibe el aviso? Un monitor sin destinatario no existe.
- Cuándo NO aplica: herramientas que solo usa una persona en su compu; ahí alcanza con que ella note que no anda.

## Accesos (motivo: el daño de una cuenta comprometida es tan grande como lo que esa cuenta puede tocar)
- Una cuenta por persona; sin cuentas compartidas (si no, no se sabe quién hizo qué ni se puede sacar a uno solo).
- Verificación en dos pasos en la cuenta de administración de la suite, el hosting y el repositorio.
- Una clave de acceso con **permisos mínimos y alcance a un solo repositorio** antes que una llave amplia.
- Si el proveedor no da permisos mínimos, el límite lo pone la confirmación humana en cada acción o el propio código.
- Cuando alguien deja el equipo: lista de qué cuentas y claves tenía. Sin lista, no se puede revocar.

## Datos que salen a terceros
Toda herramienta de afuera es un destino posible de datos. Al recomendar cualquier cosa, escribí a quién le llegan qué datos. Si la respuesta es "no sé", la recomendación todavía no está lista.
