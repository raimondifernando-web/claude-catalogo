#!/usr/bin/env bash
# Verifica que lo que el catálogo DICE coincida con lo que CONTIENE.
# Nace de tres errores reales ya publicados (2026-09-22):
#   1) base-segura decía "12 skills" y tenía 14 (0.8.0 sumó dos y nadie tocó el plugin.json)
#   2) agentes con ID de modelo clavado (claude-opus-4-6) en vez de alias   -> 0.10.1
#   3) versiones desfasadas entre marketplace.json y los plugin.json
# Se corre ANTES de cada release. Sale 1 si algo no coincide.
set -uo pipefail
cd "$(dirname "$0")/.." || exit 2
fallos=0
rojo() { printf '  FALLA  %s\n' "$1"; fallos=$((fallos+1)); }
ok()   { printf '  ok     %s\n' "$1"; }

echo "== 1. Números declarados en description vs contenido real"
for p in plugins/*/; do
  n=$(basename "$p")
  desc=$(python3 -c "import json;print(json.load(open('$p.claude-plugin/plugin.json')).get('description',''))")
  for par in "skills:skills" "agentes:agents" "plantillas:templates"; do
    palabra=${par%%:*}; carpeta=${par##*:}
    declarado=$(printf '%s' "$desc" | grep -oE "[0-9]+ $palabra" | head -1 | grep -oE '^[0-9]+')
    [ -z "$declarado" ] && continue
    real=$(ls "$p$carpeta" 2>/dev/null | wc -l | tr -d ' ')
    if [ "$declarado" != "$real" ]; then
      rojo "$n: description dice $declarado $palabra, hay $real"
    else
      ok "$n: $real $palabra"
    fi
  done
done

echo "== 2. Modelos de agentes: alias siempre, nunca un ID de versión (Mand. III)"
clavados=$(grep -rhE '^model:[[:space:]]*claude-[a-z]+-[0-9]' plugins/*/agents/ 2>/dev/null | wc -l | tr -d ' ')
if [ "$clavados" != "0" ]; then
  rojo "hay $clavados agente(s) con ID de versión en model:"
  grep -rlE '^model:[[:space:]]*claude-[a-z]+-[0-9]' plugins/*/agents/ 2>/dev/null | sed 's/^/         /'
else
  ok "0 IDs clavados"
fi
enfable=$(grep -rlE '^model:[[:space:]]*fable' plugins/*/agents/ 2>/dev/null | wc -l | tr -d ' ')
[ "$enfable" != "0" ] && rojo "hay agente(s) con model: fable (Mand. III: nunca en frontmatter)" || ok "0 agentes en fable"

echo "== 3. El modelo no se declara en la description (queda desactualizado en dos lugares)"
endesc=$(grep -rlE '^description:.*\((Opus|Sonnet|Haiku|Fable)\)' plugins/*/agents/ 2>/dev/null | wc -l | tr -d ' ')
[ "$endesc" != "0" ] && rojo "hay $endesc agente(s) que declaran el modelo en la description" || ok "0 descriptions con modelo"

echo "== 4. Versiones alineadas entre marketplace.json y cada plugin.json"
for p in plugins/*/; do
  n=$(basename "$p")
  v=$(python3 -c "import json;print(json.load(open('$p.claude-plugin/plugin.json'))['version'])")
  vm=$(python3 -c "
import json;d=json.load(open('.claude-plugin/marketplace.json'))
print(next((x.get('version') for x in d.get('plugins',[]) if x.get('name')=='$n'),'AUSENTE'))")
  [ "$v" != "$vm" ] && rojo "$n: plugin.json=$v marketplace.json=$vm" || ok "$n: $v"
done

echo "== 5. Cada skill declarada tiene su SKILL.md"
for p in plugins/*/skills/*/; do
  [ -d "$p" ] || continue
  [ -f "$p/SKILL.md" ] || rojo "sin SKILL.md: $p"
done
ok "skills revisadas"

echo
if [ "$fallos" -eq 0 ]; then echo "TODO COINCIDE — se puede publicar"; exit 0
else echo "$fallos desajuste(s) — NO publicar hasta corregir"; exit 1; fi
