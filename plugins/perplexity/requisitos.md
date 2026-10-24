# perplexity — qué necesita tu computadora

- **Una Mac** (la clave se guarda en el llavero de macOS). Windows: no probado.
- **Node.js** (trae `node` y `npm`): nodejs.org, versión LTS. El servidor oficial de Perplexity (versión fija 1.3.0, con todos sus paquetes fijados por huella en `runtime/package-lock.json`) se baja una sola vez, la primera vez que conecta, a la carpeta de datos del plugin; requiere internet esa vez.
- **Tu propia cuenta de Perplexity con clave de API** (`perplexity.ai/account/api`) y saldo prepago. **No viene incluida y no se comparte**: la crea y la paga cada persona. Poné un tope mensual en el panel de Perplexity.
- **Qué sale de tu computadora:** cada pregunta que se le hace a Perplexity viaja a Perplexity y a sus proveedores de modelos. No pongas claves, contraseñas ni datos privados de clientes en una pregunta.
- **La clave:** la escribís vos, una vez, con `perplexity-clave` (la ruta la muestra el aviso de arranque). Queda solo en el llavero de la Mac: no se guarda en archivos ni en el repositorio, y Claude nunca la ve.
- Sin la clave el plugin no rompe nada: el servidor no conecta y el aviso de arranque te dice cómo ponerla (una vez por día).
