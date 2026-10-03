# Informe — Radar de modelos, fase 2 (construir)

Rama `orquesta/radar-modelos`, sin publicar. Spec: `RADAR-SPEC.md`. Datos iniciales: `INVESTIGACION-radar-de-modelos.md`.

## Qué se hizo
- `plugins/metodo/radar/RADAR.yaml` (+ `RADAR.md` generado): 14 categorías con plan A/B/C (herramienta, proveedor, modelo, por qué,
  fuente y fecha, `datos_privados`, condiciones, cómo ver el cupo), ranking, retiros y precios de los modelos nombrados.
  Lo «a verificar» de la investigación va con `verificado: false`; video y voz no tenían dato: van todos sin verificar.
- `plugins/metodo/scripts/radar.py`: `ver`, `elegir [--sensible]`, `json`, `html`, `md`, `actualizar` (caché local), `probar --si`
  (apagado por defecto), `aviso`. Stdlib, con un lector/escritor de YAML mínimo propio (no hay PyYAML). Para Codex llama a
  `scripts/codex-cupo` (>=90% salta; 70-89% avisa). Nunca falla el arranque; las claves del `probar` se leen por nombre de variable.
- `scripts/radar-fuentes.py` + `.github/workflows/radar.yml`: diario (retiros y precios: LiteLLM, OpenRouter, models.dev, hash de las
  tablas de las páginas de retiros) y semanal (Arena vía el servidor de datasets de Hugging Face). Solo escribe y abre PR con
  cambio relevante (nuevo #1, retiro de modelo nombrado, precio +20%, cambio de tabla). Acciones fijadas por sha, permisos
  `contents: write` y `pull-requests: write`, nunca mergea.
- Regla 18 en `REGLAS-DEL-METODO.md`; «17 reglas» → «18 reglas» en README, `plugin.json` y `marketplace.json`; skill
  `/metodo:radar`; paso 3 ter en `/metodo:arrancar` (una línea de aviso); entrada en el CHANGELOG bajo «Sin publicar».
  Versión del plugin sin tocar. `vigia-tests.yml` ahora también corre ante cambios del radar.

## Pruebas
- `test_radar.py`: 32 tests, sin red. Con `test_buzon.py`: 59 en `plugins/metodo/scripts/tests`, todos verdes. Vigía: 87 verdes.
- Cubre: A agotado → B, `--sensible` salta el gratis, modelo retirado y prueba vencida, sin red usa caché, JSON válido,
  `probar` sin imprimir la clave, análisis de fuentes (sin novedad no toca nada, #1, retiro, precio +20%/+10%, tabla),
  el programa principal solo escribe ante cambio, y el workflow (sha fijados, permisos, no mergea).
- `verificar-metadatos.sh` verde. `radar.py ver`, `html`, `json` y `md` corrieron bien. Filtro de nombres de clientes: 0.

## Dudas
1. **Falta habilitar** en el repo «Allow GitHub Actions to create pull requests», o el paso `gh pr create` falla.
2. `actualizado` solo cambia con un PR: si no hay novedades, tras 14 días `arrancar` avisa «radar viejo» aunque esté al día.
   Conviene un latido (p. ej. fecha de última revisión) o subir el umbral.
3. La primera corrida semanal abrirá un PR: los nombres de modelos de Arena difieren de los nuestros y se tomará como
   «cambió el #1». Las categorías y configs de Arena (`text`, `webdev`, `vision`, `text-to-image`, `text-to-video`) son
   supuestos sin verificar; con un config inexistente la fuente se salta con aviso. En una prueba en seco, 2 de 14 dieron error.
4. Epoch AI (CSV) no se implementó: no hay URL verificada. Falta cargar ranking de video, voz y las categorías sin fuente en Arena.
5. Los ids de API (`gpt-6.1-sol`, `gemini-3.5-transcribe`…) salen de la investigación y no se comprobaron; `probar --si` los contrasta.
6. Claude, Antigravity y las apps web no se pueden medir localmente: el radar nunca salta por cupo salvo Codex.
