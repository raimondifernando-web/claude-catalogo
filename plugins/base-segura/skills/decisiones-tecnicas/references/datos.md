# Guardar y consultar datos

## Árbol de decisión
1. **¿Cuántas personas la usan y cuántos registros hay?** Una planilla compartida alcanza para un equipo chico y miles de filas.
2. **Planilla (Sheets / Excel) con estructura disciplinada** (una fila = un registro, columnas fijas, validación de datos, una pestaña de datos y otra de informes). → Primera opción siempre.
3. **Formularios + planilla** para cargar datos con control (Forms). Sigue en la suite.
4. **AppSheet / Power Apps** cuando hace falta una pantalla de carga propia, permisos distintos por persona o uso desde el celular en obra. Datos siguen en la suite.
5. **Base de datos de verdad** (Postgres, etc.) solo si hay: varias personas escribiendo a la vez con conflictos, relaciones entre tablas que la planilla no soporta, volumen que la hace lenta, o una herramienta que la necesita. Con alguien técnico a cargo y copias de seguridad.

## Decisiones, motivo y cuándo NO aplican
| Decisión | Motivo | Cuándo NO aplica |
|---|---|---|
| **No migrar a una base de datos por anticipado** | Una base es otro servidor, otra clave, otra copia de seguridad y otro lugar de fuga. Se paga el costo de operar algo que la planilla resolvía | Cuando ya aparecieron las señales (conflictos de escritura, lentitud, relaciones complejas) |
| **Una fuente de verdad por dato** | Un dato copiado en tres planillas se desincroniza; después nadie sabe cuál es el correcto | Copias de solo lectura para informes, marcadas como derivadas |
| **Copiar no es resumir: verificar texto contra texto al pasar datos de un lado a otro** | Se puede devolver la misma cantidad de filas con contenido recortado o inventado; el conteo no delata el error | Datos descartables |
| **Datos crudos y pesados, a la nube del cliente; no a git** | Los repositorios son para trabajo de Claude, no para planillas gigantes o extractos con datos personales | Siempre aplica |
| **Copias de seguridad desde el día 0, probadas** | Una copia que nunca se restauró es una esperanza, no una copia | Siempre aplica |

## Costo, riesgo y datos que salen
| Opción | Costo | Riesgo | Datos que salen |
|---|---|---|---|
| Planilla en la suite | 0 extra | Se rompe por edición manual descuidada | Ninguno |
| AppSheet/Power Apps | puede requerir licencia por usuario (confirmar) | Dependencia del producto | Ninguno si el conector es de la suite |
| Base de datos administrada | cuota mensual | Mantenimiento, claves, copias | Todo, a un tercero |
