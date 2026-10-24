#!/bin/bash
# Pruebas del plugin perplexity. Hermética: HOME temporal, `security`, `node` y `npm` falsos, clave FALSA (nunca la real).
# Uso: /bin/bash probar.sh      (bash 3.2 de macOS)
# Disparador: manual declarada (pruebas del plugin; las corre quien cambia el plugin, y antes de publicar).
AQUI="$(cd "$(dirname "$0")/.." && pwd)"          # …/plugins/perplexity/scripts
RAIZ="$(cd "$AQUI/.." && pwd)"
T="$(mktemp -d /tmp/perplexity-prueba.XXXXXX)" || exit 1; trap 'rm -rf "$T"' EXIT
FAKE="pplx-FALSA0000000000000000PRUEBA"
export HOME="$T/home"; export CLAUDE_CONFIG_DIR="$T/home/.claude"; mkdir -p "$HOME" || exit 1
export PERPLEXITY_PRUEBA=1 PERPLEXITY_LLAVERO_SERVICIO="local.perplexity.prueba-$$" CLAUDE_PLUGIN_DATA="$T/datos"
STUBS="$T/stubs"; mkdir -p "$STUBS"; export STUB_STORE="$T/llavero.txt" STUB_LOG="$T/node.log" STUB_NPM="$T/npm.log"
cat > "$STUBS/security" <<'S'
#!/bin/bash
# llavero falso: un archivo con la clave
case "$1" in
  find-generic-password) [ -s "$STUB_STORE" ] || exit 44; case " $* " in *" -w "*) cat "$STUB_STORE";; esac; exit 0 ;;
  delete-generic-password) rm -f "$STUB_STORE"; exit 0 ;;
  -i) while IFS= read -r l; do case "$l" in add-generic-password*) printf '%s\n' "${l##* -w }" > "$STUB_STORE";; esac; done; exit 0 ;;
esac
exit 1
S
cat > "$STUBS/node" <<'S'
#!/bin/bash
{ echo "ARGS=$*"; echo "CWD=$PWD"; if [ -n "$PERPLEXITY_API_KEY" ]; then echo "KEY_SET=yes"; else echo "KEY_SET=no"; fi
  [ "$PERPLEXITY_API_KEY" = "$FAKE_ESPERADA" ] && echo "KEY_MATCH=yes" || echo "KEY_MATCH=no"; } > "$STUB_LOG"
S
cat > "$STUBS/npm" <<'S'
#!/bin/bash
[ -n "$STUB_NPM_FALLA" ] && exit 1
echo "ARGS=$* CWD=$PWD" >> "$STUB_NPM"
mkdir -p "$PWD/node_modules/@perplexity-ai/mcp-server/dist" && : > "$PWD/node_modules/@perplexity-ai/mcp-server/dist/index.js"
S
chmod +x "$STUBS/security" "$STUBS/node" "$STUBS/npm" || exit 1; export FAKE_ESPERADA="$FAKE" PERPLEXITY_SECURITY="$STUBS/security"
SOLO="$STUBS:/usr/bin:/bin"
[ "$(PATH="$SOLO" command -v node)" = "$STUBS/node" ] && [ -x "$PERPLEXITY_SECURITY" ] || { echo "los falsos no están activos ✗ (no sigo: podría tocar el llavero real)"; exit 1; }
n=0; mal=0
ok()  { n=$((n+1)); echo "  ✓ $1"; }
no()  { n=$((n+1)); mal=$((mal+1)); echo "  ✗ $1"; }
chk() { if eval "$2"; then ok "$1"; else no "$1"; fi; }

echo "[1] formato"
for f in "$RAIZ/.claude-plugin/plugin.json" "$RAIZ/.mcp.json" "$RAIZ/hooks/hooks.json"; do
  chk "JSON válido: ${f#$RAIZ/}" "/usr/bin/python3 -c 'import json,sys; json.load(open(sys.argv[1]))' '$f'"; done
chk "bash 3.2 lee perplexity-mcp" "/bin/bash -n '$AQUI/perplexity-mcp'"
chk "bash 3.2 lee perplexity-clave" "/bin/bash -n '$AQUI/perplexity-clave'"
chk "sin «latest» ni npx -y en el envoltorio" "! grep -v '^#' '$AQUI/perplexity-mcp' '$RAIZ/.mcp.json' | grep -qiE 'latest|npx'"
chk "el .mcp.json apunta al envoltorio del plugin" "grep -q 'CLAUDE_PLUGIN_ROOT}/scripts/perplexity-mcp' '$RAIZ/.mcp.json'"
chk "el hook llama a --aviso" "grep -q 'perplexity-clave.* --aviso' '$RAIZ/hooks/hooks.json'"
chk "cada pieza trae su línea Disparador:" "for f in '$AQUI/perplexity-mcp' '$AQUI/perplexity-clave' '$RAIZ/skills/perplexity/SKILL.md' '$AQUI/tests/probar.sh'; do grep -q 'Disparador:' \"\$f\" || exit 1; done"

echo "[2] sin la clave"
rm -f "$STUB_STORE" "$STUB_LOG" "$STUB_NPM"
SAL="$(PATH="$SOLO" /bin/bash "$AQUI/perplexity-mcp" 2>&1 >/dev/null)"; RC=$?
chk "el servidor sale con error (no queda colgado)" "[ $RC -eq 1 ]"
chk "dice «Perplexity: falta la clave» y el comando" "echo \"\$SAL\" | grep -q 'Perplexity: falta la clave' && echo \"\$SAL\" | grep -q 'perplexity-clave'"
chk "no llegó a bajar ni lanzar nada" "[ ! -e '$STUB_LOG' ] && [ ! -e '$STUB_NPM' ]"
SAL="$(PATH="$SOLO" /bin/bash "$AQUI/perplexity-clave" --estado)"; RC=$?
chk "--estado: «Falta: …✗» y código 1" "echo \"\$SAL\" | grep -q '^Falta: la clave de Perplexity ✗' && [ $RC -eq 1 ]"
rm -f "$CLAUDE_CONFIG_DIR/metodo/perplexity-aviso"
SAL="$(PATH="$SOLO" /bin/bash "$AQUI/perplexity-clave" --aviso)"
chk "--aviso: avisa «Perplexity: falta la clave» con el comando" "echo \"\$SAL\" | grep -q '^Perplexity: falta la clave' && echo \"\$SAL\" | grep -q 'perplexity-clave'"
SAL2="$(PATH="$SOLO" /bin/bash "$AQUI/perplexity-clave" --aviso)"
chk "--aviso: segunda vez el mismo día, silencio" "[ -z \"\$SAL2\" ]"
printf '19990101' > "$CLAUDE_CONFIG_DIR/metodo/perplexity-aviso"
SAL3="$(PATH="$SOLO" /bin/bash "$AQUI/perplexity-clave" --aviso)"
chk "--aviso: al otro día vuelve a avisar" "echo \"\$SAL3\" | grep -q 'falta la clave'"

echo "[3] poner la clave (falsa) por tubería"
SAL="$(printf '%s\n' "$FAKE" | PATH="$SOLO" /bin/bash "$AQUI/perplexity-clave" 2>&1)"; RC=$?
chk "cierra con «Perplexity ✓»" "echo \"\$SAL\" | grep -q 'Perplexity ✓' && [ $RC -eq 0 ]"
chk "la salida NO contiene la clave" "! echo \"\$SAL\" | grep -q '$FAKE'"
chk "quedó en el llavero (falso)" "grep -q '$FAKE' '$STUB_STORE'"
SAL="$(printf 'corta\n' | PATH="$SOLO" /bin/bash "$AQUI/perplexity-clave" 2>&1)"; RC=$?
chk "clave demasiado corta: rechaza" "echo \"\$SAL\" | grep -q '^Falta:' && [ $RC -eq 1 ]"
SAL="$(printf 'pplx con espacios y simbolos \$\$\$ 0123456789\n' | PATH="$SOLO" /bin/bash "$AQUI/perplexity-clave" 2>&1)"; RC=$?
chk "caracteres raros: rechaza" "echo \"\$SAL\" | grep -q '^Falta:' && [ $RC -eq 1 ]"
SAL="$(printf '\n' | PATH="$SOLO" /bin/bash "$AQUI/perplexity-clave" 2>&1)"; RC=$?
chk "vacía: rechaza" "echo \"\$SAL\" | grep -q '^Falta:' && [ $RC -eq 1 ]"
chk "la rechazada no pisó la buena" "grep -q '$FAKE' '$STUB_STORE'"

echo "[4] con la clave"
SAL="$(PATH="$SOLO" /bin/bash "$AQUI/perplexity-clave" --estado)"; RC=$?
chk "--estado: «Perplexity ✓» y código 0" "echo \"\$SAL\" | grep -q '^Perplexity ✓' && [ $RC -eq 0 ]"
rm -f "$CLAUDE_CONFIG_DIR/metodo/perplexity-aviso"
SAL="$(PATH="$SOLO" /bin/bash "$AQUI/perplexity-clave" --aviso)"
chk "--aviso: silencio total" "[ -z \"\$SAL\" ]"
rm -f "$STUB_LOG" "$STUB_NPM"; (cd /tmp && PATH="$SOLO" /bin/bash "$AQUI/perplexity-mcp" >/dev/null 2>&1)
chk "la primera vez instala EXACTO el lock, sin scripts (npm ci --ignore-scripts)" "grep -q 'ARGS=ci --ignore-scripts .*--registry https://registry.npmjs.org/' '$STUB_NPM'"
chk "lanza el servidor ya instalado (node …/mcp-server/dist/index.js)" "grep -q 'ARGS=.*node_modules/@perplexity-ai/mcp-server/dist/index.js' '$STUB_LOG'"
chk "desde la carpeta raíz (no hereda .npmrc de un proyecto)" "grep -qx 'CWD=/' '$STUB_LOG'"
chk "le pasa la clave por variable de entorno" "grep -qx 'KEY_SET=yes' '$STUB_LOG' && grep -qx 'KEY_MATCH=yes' '$STUB_LOG'"
chk "la clave no quedó en los logs" "! grep -q '$FAKE' '$STUB_LOG' '$STUB_NPM'"
rm -f "$STUB_NPM"; PATH="$SOLO" /bin/bash "$AQUI/perplexity-mcp" >/dev/null 2>&1
chk "la segunda vez NO vuelve a instalar" "[ ! -e '$STUB_NPM' ]"
echo x >> "$T/datos/.lock-ok"; PATH="$SOLO" /bin/bash "$AQUI/perplexity-mcp" >/dev/null 2>&1
chk "si el lock instalado no coincide, reinstala" "[ -e '$STUB_NPM' ]"
rm -rf "$T/datos"; SAL="$(STUB_NPM_FALLA=1 PATH="$SOLO" /bin/bash "$AQUI/perplexity-mcp" 2>&1 >/dev/null)"; RC=$?
chk "si no hay internet: lo dice en castellano y sale con error" "echo \"\$SAL\" | grep -q 'no pude bajar el servidor' && [ $RC -eq 1 ]"
rm -rf "$T/datos"; STUB_NPM_FALLA=1 PATH="$SOLO" /bin/bash "$AQUI/perplexity-mcp" >/dev/null 2>&1
chk "una instalación fallida NO deja la marca de listo" "[ ! -e '$T/datos/.lock-ok' ] && [ ! -d '$T/datos.lock' ]"
mkdir "$T/datos.lock"; SAL="$(PERPLEXITY_ESPERA=2 PATH="$SOLO" /bin/bash "$AQUI/perplexity-mcp" 2>&1 >/dev/null)"
chk "con otra instalación en curso espera y avisa si no termina (sin pisarla)" "[ -d '$T/datos.lock' ]"
rmdir "$T/datos.lock" 2>/dev/null
chk "el lock fija 1.3.0 y todo paquete trae integrity" "/usr/bin/python3 -c \"import json,sys;d=json.load(open('$RAIZ/runtime/package-lock.json'));p=d['packages'];assert p['node_modules/@perplexity-ai/mcp-server']['version']=='1.3.0';assert all('integrity' in v for k,v in p.items() if k)\""
chk "servicio de llavero raro: rechazado" "PERPLEXITY_LLAVERO_SERVICIO='x -w y' PATH='$SOLO' /bin/bash '$AQUI/perplexity-clave' --estado | grep -q 'inválido'"

echo "[5] borrar y sin Node"
SAL="$(PATH="$SOLO" /bin/bash "$AQUI/perplexity-clave" --borrar)"
chk "--borrar: clave fuera del llavero" "echo \"\$SAL\" | grep -q 'borrada' && [ ! -s '$STUB_STORE' ]"
printf '%s\n' "$FAKE" > "$STUB_STORE"; rm -f "$STUBS/node"
export PERPLEXITY_PATH_EXTRA=""   # para que no encuentre el node real de esta Mac
if true; then
  SAL="$(PATH="$STUBS:/usr/bin:/bin" /bin/bash "$AQUI/perplexity-mcp" 2>&1 >/dev/null)"; RC=$?
  chk "sin node: dice «falta Node» y sale con error" "echo \"\$SAL\" | grep -q 'Perplexity: falta Node' && [ $RC -eq 1 ]"
  SAL="$(PATH="$STUBS:/usr/bin:/bin" /bin/bash "$AQUI/perplexity-clave" --estado)"
  chk "--estado sin node: «Falta: Node»" "echo \"\$SAL\" | grep -q '^Falta: Node'"
fi

echo "[6] la clave falsa no está escrita en ningún archivo del plugin"
chk "ni en scripts, ni en JSON, ni en la skill" "! grep -rq 'pplx-' '$RAIZ' --include='*' --exclude='probar.sh'"
echo; if [ $mal -eq 0 ]; then echo "TODO BIEN ✓ ($n pruebas)"; else echo "HAY ERRORES ✗ ($mal de $n)"; exit 1; fi
