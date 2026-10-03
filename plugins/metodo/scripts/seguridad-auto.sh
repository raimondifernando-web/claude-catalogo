#!/bin/bash
# seguridad-auto.sh — lo llama el hook SessionStart del paquete metodo. Nunca demora el arranque:
# 1) si el último chequeo de seguridad encontró algo, lo dice UNA vez, en una línea;
# 2) una vez por mes corre seguridad.py en segundo plano: proceso aparte, sin terminal, tope de 15 minutos y una sola
#    corrida a la vez. Solo lee tus repositorios: no cambia nada en ellos.
# Sin la lista <config de Claude>/metodo/seguridad.json no hace nada. Se apaga creando <config de Claude>/metodo/seguridad.apagado.
D="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/metodo"; [ -d "$D" ] || exit 0
S="$(cd "$(dirname "$0")" && pwd)/seguridad.py"; R="$D/seguridad.resultado"; L="$D/seguridad.corriendo"; V="$D/seguridad.visto"
if [ -f "$R" ] && ! grep -q '^ok ' "$R" && [ "$R" -nt "$V" -o ! -f "$V" ]; then
  echo "Chequeo de seguridad: $(head -1 "$R" | tr -d '\000-\037\177' | cut -c1-400) Avisale a quien te acompaña."; touch "$V"
fi
[ -f "$D/seguridad.json" ] || exit 0
[ -f "$D/seguridad.apagado" ] && exit 0
xcode-select -p >/dev/null 2>&1 || exit 0   # sin las herramientas de Apple, python3 abriría su ventana
if [ -d "$L" ]; then   # candado: si el proceso que lo tomó ya no existe, se libera
  P=$(cat "$L/pid" 2>/dev/null)
  if [ -n "$P" ]; then kill -0 "$P" 2>/dev/null || rm -rf "$L"
  elif [ -n "$(find "$L" -maxdepth 0 -mmin +1 2>/dev/null)" ]; then rm -rf "$L"; fi   # sin pid: solo si es viejo
fi
if [ -z "$(find "$D/seguridad.ultimo" -mmin -43200 2>/dev/null)" ] && [ -f "$S" ] && mkdir "$L" 2>/dev/null; then
  touch "$D/seguridad.ultimo"
  /usr/bin/python3 - "$S" "$L" "$D/seguridad.log" "$R" <<'PY' >/dev/null 2>&1 || rm -rf "$L"
import os, sys, time
s, l, log, res = sys.argv[1:5]
if os.fork(): sys.exit(0)
os.setsid()                                   # sin terminal: nadie puede pedir datos en la pantalla del usuario
fd = os.open(log, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600); os.fchmod(fd, 0o600)
os.dup2(os.open(os.devnull, os.O_RDONLY), 0); os.dup2(fd, 1); os.dup2(fd, 2)
inicio = time.time()
open(os.path.join(l, "pid"), "w").write(str(os.getpid()))   # el supervisor toma el candado antes de lanzar
pid = os.fork()
if pid == 0:
    os.execv("/usr/bin/perl", ["perl", "-e", "alarm 900; exec @ARGV", "/usr/bin/python3", s, "correr"])
_, estado = os.waitpid(pid, 0)
try:
    hecho = os.path.getmtime(res) >= inicio
except OSError:
    hecho = False
if estado != 0 and not hecho:                 # se cortó o falló sin dejar resultado: que se vea al abrir
    import tempfile
    t_fd, t_tmp = tempfile.mkstemp(dir=os.path.dirname(res), prefix=".seguridad-")
    with os.fdopen(t_fd, "w") as f:
        f.write("el chequeo no terminó ✗ (detalle en %s)\n" % log)
    os.replace(t_tmp, res)
import shutil; shutil.rmtree(l, ignore_errors=True)
PY
fi
exit 0
