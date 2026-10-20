#!/usr/bin/env bash
# Controles obligatorios para unir a `main` (check `controles` del ruleset `proteger-main`).
# Disparador: encadenado — lo corre .github/workflows/controles.yml en cada PR a main (y cuando el robot del radar
# pide sus controles). También a mano antes de abrir un PR: bash scripts/controles.sh
# Decisión del dueño (2026-10-14): unir a `main` lo deciden estas pruebas, no un OK humano. Su OK queda para la zona
# sensible (scripts/zona-sensible.py), que es un check aparte.
set -uo pipefail
cd "$(dirname "$0")/.." || exit 2
fallos=0
paso() {
  local nombre=$1; shift
  echo "== $nombre"
  if "$@"; then echo "   ok"; else echo "   FALLA: $nombre"; fallos=$((fallos+1)); fi
}
paso "metadatos (lo que el catálogo dice = lo que contiene)" bash scripts/verificar-metadatos.sh
paso "pruebas del vigía" python3 -m unittest discover -s plugins/metodo/scripts/vigia/tests
paso "pruebas del método (buzón, radar, estable, checks)" python3 -m unittest discover -s plugins/metodo/scripts/tests
paso "pasos manuales / Windows (nada exige que el cliente corra algo a mano)" python3 scripts/pasos-manuales.py
paso "pruebas de los controles" python3 -m unittest discover -s scripts/tests
# Regla 25: los workflows que este PR agrega o cambia nacen baratos y silenciosos (el catálogo es público: la regla de sistema operativo no corre).
BASE_WL="$(git merge-base origin/main HEAD 2>/dev/null || true)"
if [ -n "$BASE_WL" ] && [ "$BASE_WL" != "$(git rev-parse HEAD)" ]; then
  paso "workflows baratos y silenciosos (regla 25)" python3 plugins/metodo/scripts/workflow-lint.py --publico --base "$BASE_WL" --head HEAD
fi
# En GitHub este control va en un paso aparte y ANTES (controles.yml): así las pruebas del PR nunca ven el secreto.
if [ -z "${SIN_NOMBRES:-}" ]; then
  paso "nombres de clientes (lista en el secreto NOMBRES_PROHIBIDOS)" python3 scripts/nombres-en-ci.py ${RANGO:+--rango "$RANGO"}
fi
if [ "$fallos" -eq 0 ]; then
  echo "CONTROLES OK ✓"
else
  echo "$fallos control(es) fallaron: no se une a main"
  exit 1
fi
