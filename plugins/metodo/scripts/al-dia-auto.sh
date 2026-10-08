#!/bin/bash
# al-dia-auto.sh — lo llama el hook SessionStart del paquete metodo. Nunca demora el arranque:
# 1) si la puesta al día automática dejó un aviso nuevo, lo dice una vez, en una línea;
# 2) una vez por día corre «Poner todo al día» (al-dia.sh --auto) en segundo plano: proceso aparte, sin terminal,
#    con tope de 30 minutos y una sola corrida a la vez. Se apaga creando <config de Claude>/metodo/al-dia.apagado.
D="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/metodo"; mkdir -p "$D" 2>/dev/null || exit 0
S="$(cd "$(dirname "$0")" && pwd)/al-dia.sh"; R="$D/al-dia.resultado"; L="$D/al-dia.corriendo"; V="$D/al-dia.visto"
if [ -f "$R" ] && ! grep -q '^ok ' "$R" && [ "$R" -nt "$V" -o ! -f "$V" ]; then
  echo "Puesta al día automática: $(head -1 "$R" | tr -d '\000-\037\177' | cut -c1-400) Si dice ✗, avisale a Fernando."; touch "$V"
fi
A="$D/al-dia.aviso"   # novedades que no son fallas (ej. plantilla nueva de tu ficha): una sola vez
if [ -f "$A" ] && [ "$A" -nt "$D/al-dia.aviso.visto" -o ! -f "$D/al-dia.aviso.visto" ]; then
  echo "Puesta al día: $(head -1 "$A" | tr -d '\000-\037\177' | cut -c1-400)"; touch "$D/al-dia.aviso.visto"
fi
[ -f "$D/al-dia.apagado" ] && exit 0
xcode-select -p >/dev/null 2>&1 || exit 0   # sin las herramientas de Apple, python3 abriría su ventana: se instalan en la llamada
if [ -d "$L" ]; then   # candado: si el proceso que lo tomó ya no existe, se libera
  P=$(cat "$L/pid" 2>/dev/null)
  if { [ -n "$P" ] && ! kill -0 "$P" 2>/dev/null; } || { [ -z "$P" ] && [ -n "$(find "$L" -maxdepth 0 -mmin +1 2>/dev/null)" ]; }; then
    mv "$L" "$L.viejo.$$" 2>/dev/null && rm -rf "$L.viejo.$$"   # sin pid: solo si quedó viejo; mv para no borrar uno recién tomado
  fi
fi
if [ -z "$(find "$D/al-dia.ultimo" -mmin -1200 2>/dev/null)" ] && [ -f "$S" ] && mkdir "$L" 2>/dev/null; then
  touch "$D/al-dia.ultimo"
  /usr/bin/python3 - "$S" "$L" "$D/al-dia.log" <<'PY' >/dev/null 2>&1 || rm -rf "$L"
import os, sys, time, signal
s, l, log = sys.argv[1:4]
if os.fork(): sys.exit(0)
os.setsid()                                   # sin terminal: nadie puede pedir datos en la pantalla del usuario
open(os.path.join(l, "pid"), "w").write(str(os.getpid()))   # el candado tiene dueño antes de lanzar nada
fd = os.open(log, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600); os.fchmod(fd, 0o600)
os.dup2(os.open(os.devnull, os.O_RDONLY), 0); os.dup2(fd, 1); os.dup2(fd, 2)
pid = os.fork()
if pid == 0:
    os.execv("/bin/bash", ["/bin/bash", s, "--auto"])
fin = time.time() + 1800                      # tope de 30 minutos para TODO el grupo (claude, npm, curl…)
while True:
    if os.waitpid(pid, os.WNOHANG)[0]: break
    if time.time() > fin:
        signal.signal(signal.SIGTERM, signal.SIG_IGN)   # el supervisor sobrevive al aviso para poder rematar
        try: os.killpg(os.getpgid(0), signal.SIGTERM)
        except Exception: pass
        time.sleep(10)
        try: os.killpg(os.getpgid(0), signal.SIGKILL)   # también mata a este proceso: el candado lo libera la próxima sesión
        except Exception: pass
        break
    time.sleep(5)
import shutil; shutil.rmtree(l, ignore_errors=True)
PY
fi
exit 0
