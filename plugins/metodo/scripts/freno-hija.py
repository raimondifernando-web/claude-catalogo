#!/usr/bin/env python3
"""freno-hija — una sesión HIJA que comparte carpeta no puede pisar lo de las demás (cierre de hijas, 2026-10-21).

Antes de cada comando de Bash y de cada escritura (Write/Edit/MultiEdit), si la sesión es hija y trabaja en una carpeta
compartida (lo mide sesion_hija.detectar con los datos de la app), BLOQUEA con una explicación en castellano:
  - en git: pull, rebase, --autostash, stash (salvo list/show), checkout/switch, reset, merge, restore, clean, add -A/--all/.,
    push (subir va por sesion_hija.py subir) y commit sin nombrar archivos (`git commit -- <rutas>` sí pasa);
    son los que reescriben o suben commits sin subir de otras sesiones o cambian archivos que otra sesión está editando;
  - también: commit --amend, cherry-pick, revert, update-ref, am, branch/tag que borran o pisan, worktree remove/move, add con comodines;
  - escribir el REANUDAR.md de la carpeta, con Write/Edit o con un comando (>, tee, cp, mv, sed -i, rm) (es del hilo principal; la
    hija deja un TRASPASO con sesion_hija.py traspaso).
Deja pasar todo lo demás, y también git sobre una carpeta temporal o el worktree propio de la sesión (`git -C <ruta>`).
Sesiones que no son hijas: no cambia nada. Es un guardarraíl, no un muro: la skill cerrar-hija dice lo mismo sin él.

Disparador: automático (hook PreToolUse, matcher Bash|Write|Edit|MultiEdit). Apagar: FRENO_HIJA=0 o el archivo
<config de Claude>/metodo/freno-hija.apagado. Si algo falla adentro, deja pasar (nunca traba una sesión).
Solo lee: los datos de sesiones de la app y el JSON del hook. No escribe nada. Sin red.
"""
import json
import os
import re
import shlex
import sys

AQUI = os.path.dirname(os.path.realpath(__file__))
TEMPORALES = ("/tmp/", "/private/tmp/", "/private/var/folders/", "/var/folders/")
PELIGRO = re.compile(r"^(pull|rebase|checkout|switch|reset|merge|restore|clean|cherry-pick|revert|update-ref|am|filter-branch|replace)$")
# opciones de `git commit` que llevan valor (lo que sigue no es una ruta)
CON_VALOR = {"-m", "--message", "-F", "--file", "-C", "--reuse-message", "-c", "--reedit-message", "-t", "--template",
             "--author", "--date", "--cleanup", "--fixup", "--squash", "--trailer", "-S", "--gpg-sign"}
REANUDAR_BASH = re.compile(r"(>>?|\btee\b|\bcp\b|\bmv\b|\bsed\s+-i|\bperl\s+-[a-z]*i|\brm\b|\btruncate\b)[^;&|]*REANUDAR\.md")
SEPARADORES = re.compile(r"(?:&&|\|\||;|\||\n|\(|\)|`|\$\()")


def config():
    return os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude")


def apagado():
    return os.environ.get("FRENO_HIJA") == "0" or os.path.exists(os.path.join(config(), "metodo", "freno-hija.apagado"))


def _dentro(ruta, base):
    try:
        r, b = os.path.realpath(ruta), os.path.realpath(base)
        return r == b or r.startswith(b.rstrip("/") + "/")
    except Exception:
        return False


def libre(ruta, cwd, propia):
    """Ruta donde la hija puede hacer lo que quiera con git: temporal o su worktree propio."""
    p = os.path.join(cwd, os.path.expanduser(ruta))
    real = os.path.realpath(p)
    if _dentro(real, cwd):
        return False  # la carpeta compartida misma (o algo adentro): nunca es libre, esté donde esté
    return real.startswith(TEMPORALES) or bool(propia and _dentro(real, propia))


def peligro_git(comando, cwd, propia):
    """Motivo (texto) si el comando corre una operación de git peligrosa en una carpeta compartida; None si pasa."""
    dir_actual = cwd  # se sigue el `cd` entre tramos (cd /tmp/copia && git pull sí pasa)
    for tramo in SEPARADORES.split(comando or ""):
        try:
            pal = shlex.split(tramo, comments=True)
        except ValueError:
            pal = tramo.split()
        while pal and re.match(r"^\w+=", pal[0]):
            pal = pal[1:]  # VAR=valor git …
        if pal and pal[0] in ("cd", "pushd"):
            dir_actual = os.path.join(dir_actual, os.path.expanduser(pal[1])) if len(pal) > 1 else os.path.expanduser("~")
            continue
        destino = dir_actual
        if not pal or os.path.basename(pal[0]) != "git":
            continue
        i, sub = 1, None
        while i < len(pal):
            a = pal[i]
            if a == "-C" and i + 1 < len(pal):
                destino = os.path.join(destino, os.path.expanduser(pal[i + 1]))
                i += 2
                continue
            if a in ("-c", "--git-dir", "--work-tree") and i + 1 < len(pal):
                i += 2
                continue
            if a.startswith("-"):
                i += 1
                continue
            sub = a
            break
        if sub is None or libre(destino, cwd, propia):
            continue
        resto = pal[i + 1:]
        if PELIGRO.match(sub):
            return f"`git {sub}`"
        if sub == "stash" and (not resto or resto[0] not in ("list", "show")):
            return "`git stash`"
        if "--autostash" in resto:
            return "`--autostash`"
        if sub == "add" and any(x in ("-A", "--all", ".", ":/", "-u", "--update") or any(c in x for c in "*?[") for x in resto):
            return "`git add` de todo o con comodines (se llevaría archivos de otras sesiones)"
        if sub == "branch" and any(x in ("-d", "-D", "--delete", "-f", "--force", "-m", "-M", "--move", "-c", "-C") for x in resto):
            return "`git branch` que borra, mueve o pisa ramas"
        if sub == "worktree" and resto[:1] in (["remove"], ["move"]):
            return "`git worktree " + resto[0] + "` (puede ser la copia de otra sesión)"
        if sub == "tag" and any(x in ("-d", "--delete", "-f", "--force") for x in resto):
            return "`git tag` que borra o pisa etiquetas"
        if sub == "push":
            return "`git push` (en la carpeta compartida subiría también commits de otras sesiones)"
        if sub == "commit":
            if "--amend" in resto:
                return "`git commit --amend` (reescribiría el último commit, que puede ser de otra sesión)"
            if any(x in ("-a", "--all") or re.match(r"^-[a-zA-Z]*a[a-zA-Z]*$", x) for x in resto):
                return "`git commit -a` (se llevaría los cambios de otras sesiones)"
            rutas, j = False, 0
            while j < len(resto):
                x = resto[j]
                if x == "--":
                    rutas = j + 1 < len(resto)
                    break
                if x in CON_VALOR:
                    j += 2
                    continue
                if not x.startswith("-"):
                    rutas = True
                    break
                j += 1
            if not rutas:
                return "`git commit` sin nombrar tus archivos (se llevaría lo que otras sesiones prepararon): `git commit -m \"…\" -- <tus rutas>`"
    return None


def es_reanudar(ruta, cwd):
    if not ruta or os.path.basename(ruta) != "REANUDAR.md":
        return False
    carpeta = os.path.realpath(os.path.dirname(os.path.join(cwd, ruta)))
    return carpeta in (os.path.realpath(cwd), os.path.realpath(os.path.join(cwd, ".claude", "prompts")))  # raíz o .claude/prompts


def negar(motivo):
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                             "permissionDecisionReason": motivo}}, ensure_ascii=False))


def main():
    if apagado():
        return 0
    try:
        datos = json.loads(sys.stdin.read() or "{}")
    except ValueError:
        return 0
    herramienta = datos.get("tool_name") or ""
    entrada = datos.get("tool_input") or {}
    cwd = datos.get("cwd") or os.getcwd()
    # Camino rápido: solo se miran los datos de la app si el pedido puede ser peligroso.
    if herramienta in ("Bash",):
        if not re.search(r"\bgit\b|REANUDAR\.md", entrada.get("command") or ""):
            return 0
    elif herramienta in ("Write", "Edit", "MultiEdit"):
        if not es_reanudar(entrada.get("file_path"), cwd):
            return 0
    else:
        return 0
    sid = datos.get("session_id")
    if sid:
        os.environ["CLAUDE_CODE_SESSION_ID"] = str(sid)
    sys.path.insert(0, AQUI)
    import sesion_hija  # noqa: E402
    viejo = os.getcwd()
    try:
        os.chdir(cwd)
        d = sesion_hija.detectar()
    finally:
        os.chdir(viejo)
    if d.get("modo") != "hija" or d.get("carpeta") != "compartida":
        return 0
    propia = None  # en carpeta compartida no hay worktree propio que liberar
    if herramienta == "Bash" and REANUDAR_BASH.search(entrada.get("command") or ""):
        negar("Frené un comando que escribe, mueve o borra un REANUDAR.md: sos una sesión hija en una carpeta compartida y ese "
              "archivo es del hilo principal. Tu traspaso va con `python3 <scripts>/sesion_hija.py traspaso --borrador <archivo>`.")
        return 0
    if herramienta == "Bash":
        m = peligro_git(entrada.get("command"), cwd, propia)
        if m:
            negar(f"Frené {m}: sos una sesión hija y esta carpeta la comparten otras sesiones. Esa operación de git reescribe commits "
                  "sin subir de otras sesiones o cambia archivos que están editando. Para guardar lo tuyo: "
                  "`python3 <scripts>/sesion_hija.py subir <repo> -m \"…\"` (sube solo tus archivos, sin tocar la carpeta). "
                  "Si de verdad hace falta, hacelo en un worktree aparte (`git worktree add <carpeta temporal> …`) o pedíselo a la coordinadora.")
    else:
        negar("Frené la escritura de REANUDAR.md: sos una sesión hija en una carpeta compartida y ese archivo es del hilo principal. "
              "Tu traspaso va con `python3 <scripts>/sesion_hija.py traspaso --borrador <archivo>` (skill cerrar-hija).")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)  # un fallo del freno nunca traba la sesión
