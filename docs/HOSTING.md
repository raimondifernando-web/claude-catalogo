# HOSTING para no técnicos — dónde poner una herramienta web y cuánto cuesta

> Para cuando Claude te arma una página, un tablero o una herramienta y hay que ponerla en internet.
> Precios verificados en las páginas oficiales el 2026-09-21; **volvé a mirarlos antes de contratar** (cambian).
> Decisión típica: **empezar en Vercel Pro con tope de gasto puesto el día 1**; pasar a un VPS solo si hay razón.

## 1. Primero: ¿hace falta hosting?
| Lo que tenés | Dónde va | Costo |
|---|---|---|
| Un documento, informe o presentación | Tu nube de siempre (Drive, Notion) | 0 |
| Una página HTML sola (un archivo), para mostrar a alguien | **Artifact de Claude** (se comparte con link) o un archivo en tu nube | 0 |
| Algo que la gente usa todos los días, con datos que cambian, o con un dominio propio | **Hosting** (abajo) | desde USD 20/mes |

## 2. Las dos opciones que recomendamos
| | **Vercel** (Pro) | **VPS** (ej. Hostinger KVM) |
|---|---|---|
| Qué es | Le das el repositorio de GitHub y él publica solo cada vez que cambia algo | Una computadora alquilada en la nube donde instalás vos (o tu consultor) lo que haga falta |
| Para qué sirve | Páginas, tableros, herramientas web modernas (lo que Claude suele generar) | Programas que corren todo el tiempo (automatizaciones, bases de datos, contenedores Docker) |
| Precio | **USD 20/mes por persona** (plan Pro). El plan gratis (Hobby) es **solo para uso personal, no comercial**: para una empresa no vale | **KVM 1: USD 6,49/mes promo → USD 11,99 al renovar**; KVM 2: 8,99 → 14,99. Se paga por adelantado, precio fijo |
| El riesgo | **Cobra por uso además de la cuota**: si la herramienta tiene mucho tráfico o un error la hace trabajar de más, la factura sube sola. Por eso el paso 3 es obligatorio | Precio fijo: no hay sorpresa en la factura. El riesgo es otro: **nadie lo actualiza ni lo protege por vos** (parches, contraseñas, copias) |
| Quién lo mantiene | Vercel (seguridad, actualizaciones, copias) | Vos o tu consultor. Es una máquina más para cuidar |
| Facilidad | Alta: sin terminal, sin servidores | Media-baja: requiere alguien técnico al menos al inicio |

## 3. El día 1 en Vercel: tope de gasto (obligatorio)
Vercel arranca con un presupuesto por defecto de **USD 200 de uso bajo demanda** con avisos por mail; el aviso no frena nada.
Hay que poner un **límite duro** que pause los proyectos al llegar al tope:
1. Vercel → tu equipo → *Settings* → *Billing* → *Spend Management*.
2. Fijá un presupuesto bajo (USD 20-30 alcanza para empezar) y activá **"pause all projects"** al 100 %.
3. Activá las notificaciones (mail + SMS).
Resultado: en el peor caso la herramienta se apaga y te llega un aviso; **nunca** una factura de cientos de dólares.
Esto se decide el día que se crea la cuenta, no "después".

## 4. Qué queda expuesto (en cualquiera de las dos)
- **Lo que publicás es público** salvo que le pongas contraseña o login. Un tablero con nombres de clientes o precios internos
  necesita acceso restringido antes de subirlo; pedíselo a Claude ("protegé esta página con acceso").
- **Las claves** (de OpenAI, Google, etc.) se cargan en el panel del hosting como *variables de entorno*, nunca dentro del
  código ni en el chat. Si una clave quedó en el repositorio, se cambia (se "rota"), no alcanza con borrarla.
- **El repositorio** en GitHub: privado por defecto. Público solo si es una decisión.
- **Disponibilidad**: si la herramienta importa, un monitor gratuito (ej. UptimeRobot) te avisa cuando se cae. El monitor
  avisa caídas, **no gastos**: para eso está el tope del paso 3.

## 5. Cómo se decide en 30 segundos
- ¿Es una web/tablero que hizo Claude, y quiero olvidarme del servidor? → **Vercel Pro + tope de gasto**.
- ¿Necesito que corra algo permanente (automatizaciones, base de datos, Docker) o quiero precio fijo? → **VPS**, con tu consultor.
- ¿Es para uso propio, sin empresa, para probar? → Vercel Hobby (gratis), sabiendo que no es para uso comercial.
- ¿Tarjeta argentina? Algunos proveedores no la aceptan (Hetzner, por ejemplo, no). Vercel y Hostinger sí al 2026-09-21.
