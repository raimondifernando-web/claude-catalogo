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

# Los valores de afuera (rutas, nombres) entran a Python como argumentos, nunca dentro del código:
# un nombre de carpeta con comillas no puede ejecutar nada (hallazgo security-reviewer 2026-09-22).
campo() { python3 - "$1" "$2" <<'PY'
import json,sys
try: print(json.load(open(sys.argv[1])).get(sys.argv[2],''))
except Exception: sys.exit(3)
PY
}
en_marketplace() { python3 - "$1" <<'PY'
import json,sys
d=json.load(open('.claude-plugin/marketplace.json'))
print(next((x.get('version') for x in d.get('plugins',[]) if x.get('name')==sys.argv[1]),'AUSENTE'))
PY
}

echo "== 0. Nombres de carpetas: solo minúsculas, números y guiones"
raros=$(find plugins -mindepth 1 -print | grep -cvE '^[A-Za-z0-9._/ -]+$')
if [ "$raros" != "0" ]; then
  rojo "hay $raros ruta(s) con caracteres raros (comillas, control, saltos de línea): revisar a mano, no se sigue"
  echo "$fallos desajuste(s) — NO publicar hasta corregir"; exit 1
fi
for p in plugins/*/; do
  basename "$p" | grep -qE '^[a-z0-9-]+$' || { rojo "nombre de plugin inválido"; echo "NO publicar"; exit 1; }
done
ok "nombres limpios"

echo "== 1. Números declarados en description vs contenido real"
for p in plugins/*/; do
  n=$(basename "$p")
  desc=$(campo "$p.claude-plugin/plugin.json" description) || { rojo "$n: plugin.json ilegible"; continue; }
  for par in "skills:skills" "agentes:agents" "plantillas:templates"; do
    palabra=${par%%:*}; carpeta=${par##*:}
    declarado=$(printf '%s' "$desc" | grep -oE "[0-9]+ $palabra" | head -1 | grep -oE '^[0-9]+')
    [ -z "$declarado" ] && continue
    real=$(find "$p$carpeta" -mindepth 1 -maxdepth 1 2>/dev/null | wc -l | tr -d ' ')
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
  v=$(campo "$p.claude-plugin/plugin.json" version) || { rojo "$n: plugin.json ilegible"; continue; }
  vm=$(en_marketplace "$n")
  [ "$v" != "$vm" ] && rojo "$n: plugin.json=$v marketplace.json=$vm" || ok "$n: $v"
done

echo "== 5. Cada skill declarada tiene su SKILL.md"
for p in plugins/*/skills/*/; do
  [ -d "$p" ] || continue
  [ -f "$p/SKILL.md" ] || rojo "sin SKILL.md: $p"
done
[ "$fallos" -eq 0 ] && ok "skills revisadas"

echo
if [ "$fallos" -eq 0 ]; then echo "TODO COINCIDE — se puede publicar"; exit 0
else echo "$fallos desajuste(s) — NO publicar hasta corregir"; exit 1; fi
