# yfinance — qué necesita tu computadora

- **Una Mac.** Windows: no probado.
- **`uv`** (de Astral): lo instala solo el actualizador del catálogo, en tu carpeta de usuario y sin contraseña. Si el actualizador no pudo instalarlo, te lo dice en su resumen; sin `uv` el servidor no conecta y el plugin no rompe nada más.
- **Internet:** la primera vez que conecta baja el servidor y sus paquetes (con Python 3.12 propio de `uv`); después usa lo guardado. Cada consulta va a Yahoo Finanzas.
- **Sin claves, sin cuenta, sin costo.** Los datos son de Yahoo, sin garantía de exactitud ni de tiempo real: contrastalos antes de decidir nada.
- **Qué no hace:** no compra, no vende, no se conecta a ningún broker ni mueve plata; no es asesoramiento de inversión.

## TradingView (no viene incluido)
TradingView tiene un conector oficial para Claude, pero es de **tu cuenta de claude.ai y exige tu propio plan de pago de TradingView** (con el plan Essential, 10 consultas por día; solo para uso personal). Este catálogo no puede entregarlo ni dar por hecho que tenés plan: quien tenga ese plan lo conecta desde los conectores de su claude.ai; el catálogo no lo hace por nadie. No se usan programas que leen TradingView por afuera (van contra sus términos): ver la receta `herramientas-rechazadas`.
