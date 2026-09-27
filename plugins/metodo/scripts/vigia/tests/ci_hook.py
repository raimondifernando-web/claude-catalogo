"""Prueba de punta a punta del hook, como lo corre Claude Code (la usa el CI en
ubuntu, macos y windows; también corre en una Mac a mano).

    python plugins/metodo/scripts/vigia/tests/ci_hook.py --bash <ruta a bash>

Qué verifica, con el comando REAL de hooks/hooks.json, desde rutas con espacios:
1. Un `python3` falso primero en el PATH (como el alias de la Microsoft Store: escribe
   en stderr y sale 9009): la cadena cae al siguiente intérprete y el aviso sale UNA vez.
2. El hook tarda menos de 1,5 s aunque lance el detector.
3. Se mata el árbol del proceso que corrió el hook (POSIX: el grupo; Windows:
   taskkill /F /T) mientras el detector todavía trabaja (un `uv` falso lo demora ~3 s).
4. Después de eso el detector termina solo y escribe el estado: estaba desacoplado.
No usa red real ni credenciales: HOME temporal, sin token de GitHub.
"""
import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ES_WINDOWS = os.name == "nt"
PLUGIN = Path(__file__).resolve().parents[3]
LIMITE_HOOK = 1.5


def fallar(msg):
    print("FALLA: " + msg)
    sys.exit(1)


def posix(ruta):
    return str(ruta).replace("\\", "/")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bash", default=shutil.which("bash"))
    args = ap.parse_args()
    if not args.bash:
        fallar("no encontré bash")

    tmp = Path(tempfile.mkdtemp(prefix="vigia ci "))
    base = tmp / "carpeta con espacios"
    casa = base / "home con espacios"
    raiz = base / "metodo"
    fake = base / "bin falso"
    (casa / ".claude" / "vigia").mkdir(parents=True)
    (raiz / "scripts").mkdir(parents=True)
    fake.mkdir()
    shutil.copytree(str(PLUGIN / "scripts" / "vigia"), str(raiz / "scripts" / "vigia"))
    shutil.copytree(str(PLUGIN / "hooks"), str(raiz / "hooks"))

    vigia_dir = casa / ".claude" / "vigia"
    estado_ruta = vigia_dir / "estado.json"
    estado_ruta.write_text(json.dumps({
        "estado": "ok", "ultima_corrida": "2020-01-01T00:00:00+00:00",
        "novedades": {"x": {"estado": "nueva"}},
    }), encoding="utf-8")
    (vigia_dir / "perfil.json").write_text(json.dumps({"clis": {"uv": ["cualquier-cosa"]}}), encoding="utf-8")

    # python3 falso (lo encuentra bash) y uv lento (lo encuentra el detector).
    marca_py3 = base / "python3-falso-usado"
    py3 = fake / "python3"
    py3.write_text(
        "#!/bin/sh\necho 'Python was not found; run without arguments to install from the Microsoft Store' >&2\n"
        "touch \"{}\"\nexit 9009\n".format(posix(marca_py3)), encoding="utf-8")
    py3.chmod(0o755)
    if ES_WINDOWS:
        (fake / "uv.bat").write_text("@echo off\r\nping -n 4 127.0.0.1 >nul\r\n", encoding="utf-8")
    else:
        uv = fake / "uv"
        uv.write_text("#!/bin/sh\nsleep 3\n", encoding="utf-8")
        uv.chmod(0o755)

    comando = json.loads((PLUGIN / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    comando = comando["hooks"]["SessionStart"][0]["hooks"][0]["command"]

    env = dict(os.environ)
    for k in ("GH_TOKEN", "GITHUB_TOKEN", "GH_HOST", "VIGIA_OFF", "VIGIA_PERFIL", "CLAUDE_CONFIG_DIR"):
        env.pop(k, None)
    env.update({
        "CLAUDE_PLUGIN_ROOT": str(raiz),  # en Windows, con barras invertidas y letra de unidad
        "HOME": str(casa), "USERPROFILE": str(casa),
        "GH_CONFIG_DIR": str(casa / ".gh-vacio"),
        "PATH": str(fake) + os.pathsep + env.get("PATH", ""),
        "SALIDA_HOOK": posix(base / "salida.txt"), "FIN_HOOK": posix(base / "fin.txt"),
    })
    # El proceso que corre el hook queda vivo después (como el de Claude Code) para poder matarlo.
    envoltorio = "{ " + comando + '; } > "$SALIDA_HOOK"; echo fin > "$FIN_HOOK"; sleep 60'
    extra = {} if ES_WINDOWS else {"start_new_session": True}
    t0 = time.monotonic()
    p = subprocess.Popen([args.bash, "-c", envoltorio], env=env, stdin=subprocess.DEVNULL, **extra)
    fin = base / "fin.txt"
    while not fin.exists() and time.monotonic() - t0 < 20:
        time.sleep(0.01)
    dura = time.monotonic() - t0
    if not fin.exists():
        p.kill()
        fallar("el hook no terminó en 20 s")

    # Matar el árbol del hook con el detector todavía trabajando.
    if ES_WINDOWS:
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)], capture_output=True)
    else:
        os.killpg(p.pid, signal.SIGKILL)
    p.wait(timeout=10)
    antes = json.loads(estado_ruta.read_text(encoding="utf-8"))

    salida = (base / "salida.txt").read_text(encoding="utf-8")
    print("duración del hook: {:.2f} s".format(dura))
    print("salida: " + salida.strip()[:300])
    if dura >= LIMITE_HOOK:
        fallar("el hook tardó {:.2f} s (límite {} s)".format(dura, LIMITE_HOOK))
    if salida.count("systemMessage") != 1:
        fallar("el aviso tenía que salir exactamente una vez")
    if not marca_py3.exists():
        fallar("no se probó el python3 falso: la prueba de la cadena no es válida")
    if not antes.get("ultima_corrida", "").startswith("2020"):
        fallar("el detector terminó antes de matar el árbol: la prueba de desacople no es válida")

    limite = time.monotonic() + 60
    estado = antes
    while time.monotonic() < limite:
        try:
            estado = json.loads(estado_ruta.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            estado = {}
        if estado.get("ultima_corrida") and not estado["ultima_corrida"].startswith("2020"):
            break
        time.sleep(0.5)
    log = (vigia_dir / "vigia.log").read_text(encoding="utf-8") if (vigia_dir / "vigia.log").exists() else ""
    print(log)
    if not estado.get("ultima_corrida") or estado["ultima_corrida"].startswith("2020"):
        fallar("el detector no sobrevivió a que mataran el árbol del hook")
    if estado.get("estado") == "caido":
        fallar("el detector quedó caído: {}".format(estado.get("errores")))
    if log.count(" inicio: ") != 1:
        fallar("el detector tenía que correr exactamente una vez")
    time.sleep(1)
    shutil.rmtree(str(tmp), ignore_errors=True)
    print("OK: aviso único, hook {:.2f} s, detector desacoplado terminó con estado '{}'".format(dura, estado.get("estado")))


if __name__ == "__main__":
    main()
