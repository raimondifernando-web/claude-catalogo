---
name: achicar-datos-grandes
description: >
  Usala cuando una herramienta, API o consulta devuelve datos enormes (más de ~20.000 caracteres
  de JSON, tablas, filas de Meta Ads, Google Ads, ERP/CRM, Shopify, Clarity, catálogos o logs) y
  hay que leerlos o calcular con ellos. Los recodifica sin perder ni una fila (Headroom, modo
  sin pérdida) para gastar menos tokens. No sirve para código ni texto corrido.
sync: no
---

# Achicar datos grandes

Reduce el costo de leer salidas de datos grandes, **sin perder nada**. Ahorro medido: 40-67 % en
listas de filas (JSON plano); 0 % en código y texto.

## Cuándo
- Una consulta devolvió (o va a devolver) más de ~20.000 caracteres de JSON/tabla/log y vas a leerla.
- Vas a traer datos por script, `curl` o API: guardalos en un archivo y achicalos **antes** de leerlos.
- Si el resultado de una herramienta ya quedó guardado en un archivo por ser grande: achicá el archivo, no lo leas crudo.

## Cuándo NO
- Código fuente, documentos, conversación: ahorra 0 %.
- Salidas chicas (<20.000 caracteres): no vale el paso.
- Si el resultado ya entró al contexto (una herramienta lo devolvió inline), no hay nada que achicar: la próxima vez guardalo a archivo.

## Cómo
1. Primera vez en la máquina: `bash ~/.claude/skills/achicar-datos-grandes/scripts/instalar.sh` (versión fija 0.40.0, entorno aislado en `~/.cache/headroom`, no toca nada más).
2. `python3 ~/.claude/skills/achicar-datos-grandes/scripts/achicar.py <datos.json> --salida <datos.achicado.txt>`
3. Leé el archivo achicado. Formato: columnas (`@campo=[valores…]`) en vez de una fila por registro; cada columna tiene todos los valores, en orden.
4. Mirá la línea final: `idéntico: True · revertidos: 0`. Si `revertidos` > 0 o no ahorró, usá el archivo original.

## Reglas (no se negocian)
- **Solo como script/librería.** Nunca `headroom wrap`, `headroom learn`, `headroom proxy`, ni `ANTHROPIC_BASE_URL` (rompe Remote Control y ve todo el tráfico).
- **Telemetría apagada siempre:** el script ya fija `HEADROOM_BEACON=off` y `HEADROOM_OFFLINE=true`. Nunca poner `DO_NOT_TRACK` en el `env` de `settings.json`.
- **Solo modo sin pérdida** (`densify`). El modo con pérdida de Headroom saca filas y deja marcadores `<<ccr:…>>`: si alguna vez aparece uno, el script devuelve el original. No lo uses con plata: un total calculado sobre filas ocultas es un número falso.
- **Datos de plata (gasto, ventas, M&A):** verificá igual. Recalculá un total desde el archivo achicado y compará con el original antes de informar un número.
- Versión fija: no actualizar sin auditoría (Mand. XVI). Origen: PyPI `headroom-ai==0.40.0` (Apache-2.0, `headroomlabs-ai/headroom`).
- Datos de clientes o privados: se achican localmente, no salen de la máquina (modo offline). Igual aplica el Mand. XXII.
