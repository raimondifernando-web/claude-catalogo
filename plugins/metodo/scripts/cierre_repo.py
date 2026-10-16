#!/usr/bin/env python3
"""cierre_repo — qué hace /cerrar con el repositorio de la carpeta según cómo se une a main (metodo 0.46.0).

Dos modos: «auto» (el repo está en ~/.claude/unir-a-main.txt: lo une `unir-a-main` solo, con los controles) y «pr» (cualquier otro:
se abre un PR y, si el repo tiene controles en GitHub, se une con `gh pr merge --squash --auto`; si no, la persona recibe UN comando).
Antes, en un repo «pr» el cierre se frenaba o quedaba a medias en la rama de cierre; ahora dice una vez qué hacer.

Uso:  cierre_repo.py estado [carpeta]             imprime lo que cerrar-check muestra (nada si el repo une solo)
      cierre_repo.py volver [carpeta] [--a RAMA]  vuelve a la rama base conservando el REANUDAR.md del cierre (único comando que escribe)
Disparador: encadenado — `cerrar-check.py` llama a lineas_cierre() en cada /cerrar (imprime «REPO SIN UNIÓN AUTOMÁTICA»), y el paso de unión de /metodo:cerrar
ejecuta `volver`. Probado: tests/test_cierre_sin_pendientes.py (test_e_*).
La lista de «auto» solo se LEE para avisar; no autoriza nada (la autorización la da `unir-a-main`, con su propia lista).
"""
import os
import re
import subprocess
import sys

for _flujo in (sys.stdin, sys.stdout, sys.stderr):  # Windows: consola cp1252
    try:
        _flujo.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

REANUDAR = os.path.join(".claude", "prompts", "REANUDAR.md")
RUIDO = re.compile(r"(^|/)(\.omc|__pycache__|\.pytest_cache|node_modules)(/|$)|(^|/)\.DS_Store$")


def git(repo, *a):
    try:
        r = subprocess.run(["git", "-c", "core.fsmonitor=false", "-c", "core.hooksPath=" + os.devnull, "-C", repo, *a], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=20)
        return r.stdout.strip() if r.returncode == 0 else None
    except Exception:
        return None


def lista_auto():
    p = os.environ.get("CIERRE_REPO_LISTA") or os.path.join(os.path.expanduser("~"), ".claude", "unir-a-main.txt")
    try:
        with open(p, encoding="utf-8") as f:
            return {l.strip() for l in f if l.strip() and not l.lstrip().startswith("#")}
    except OSError:
        return set()


def url_origin(repo):
    return git(repo, "remote", "get-url", "origin")


def nombre_repo(repo):
    m = re.search(r"[:/\\]([^/:\\]+?)(?:\.git)?/?$", url_origin(repo) or "")
    return m.group(1) if m else None


def dueno_repo(repo):
    m = re.search(r"github\.com[:/]([^/]+)/", url_origin(repo) or "")
    return m.group(1) if m else None


def modo(repo):
    n = nombre_repo(repo)
    if not n:
        return "sin-remoto", None
    return ("auto" if n in lista_auto() else "pr"), n


def base(repo):
    b = git(repo, "symbolic-ref", "-q", "--short", "refs/remotes/origin/HEAD")
    if b:
        return b.split("/", 1)[-1]
    for c in ("origin/main", "main", "origin/master", "master"):
        if git(repo, "rev-parse", "--verify", "-q", c + "^{commit}"):
            return c.split("/", 1)[-1]
    return None


def lineas_cierre(repo):
    m, n = modo(repo)
    if m in ("auto", "sin-remoto"):
        return []
    rama, b = git(repo, "branch", "--show-current"), base(repo)
    slug = f"{dueno_repo(repo)}/{n}" if dueno_repo(repo) else n
    out = [f"• REPO SIN UNIÓN AUTOMÁTICA: «{n}» no está en ~/.claude/unir-a-main.txt → une por PR. Hacelo VOS, en este orden: "
           f"(1) push de la rama y `gh pr create --fill --repo {slug}` si no hay PR; (2) bind_pr + set_monitor(auto_fix) si la app los tiene; "
           f"(3) `gh pr merge <N> --squash --auto --repo {slug}`; si GitHub no lo admite (el repo no tiene controles), dejale a la persona UN solo comando en el chat: "
           f"`gh pr merge <N> --squash --repo {slug}` y en el REANUDAR «ese repo une por PR; el cierre queda en el PR <N>»; "
           f"(4) `cierre_repo.py volver` (no te quedes en la rama de cierre); (5) seguí con el paso 10: abrir la sesión siguiente y archivarte"]
    if rama and b and rama != b:
        out.append(f"• RAMA DE CIERRE: estás en «{rama}», no en «{b}» → al terminar el PR: `python3 cierre_repo.py volver` (está junto a cerrar-check.py)")
    return out


def _leer(ruta):
    try:
        with open(ruta, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return None


def volver(repo, a=None):
    """(ok, texto). Cambia a la rama base sin perder el REANUDAR.md del cierre; se niega si algo se perdería."""
    rama, b = git(repo, "branch", "--show-current"), a or base(repo)
    if not rama or not b:
        return False, "no pude saber en qué rama estás o cuál es la base"
    if rama == b:
        return True, f"ya estás en «{b}»"
    if git(repo, "rev-parse", "--verify", "-q", f"refs/remotes/origin/{rama}") is None or git(repo, "rev-list", "--count", f"origin/{rama}..{rama}") != "0":
        return False, f"«{rama}» tiene commits que no están en GitHub: subila (git push) antes de volver"
    st = git(repo, "--no-optional-locks", "status", "--short", "-uall") or ""
    sucios = [l for l in st.splitlines() if l.strip() and not l.startswith("??") and not RUIDO.search(l.strip().split(None, 1)[-1])]
    if sucios:
        return False, f"hay {len(sucios)} archivo(s) versionados sin guardar ({sucios[0].strip()[:60]}…): guardalos (commit) antes de volver"
    ruta = os.path.join(repo, REANUDAR)
    guardado = _leer(ruta)
    r = subprocess.run(["git", "-c", "core.fsmonitor=false", "-c", "core.hooksPath=" + os.devnull, "-C", repo, "checkout", "-q", b], capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        return False, f"git checkout {b} falló: {r.stderr.strip()[:160]}"
    if guardado is not None and _leer(ruta) != guardado:
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(guardado)
    return True, f"volví a «{b}»; el REANUDAR.md del cierre quedó en la carpeta (sin guardar a propósito: es el que lee /arrancar)"


def main(argv):
    if not argv or argv[0] not in ("estado", "volver"):
        print(__doc__)
        return 2
    cmd, resto = argv[0], list(argv[1:])
    a = None
    if "--a" in resto:
        i = resto.index("--a")
        a = resto[i + 1] if i + 1 < len(resto) else None
        del resto[i:i + 2]
    repo = os.path.abspath(resto[0]) if resto else os.getcwd()
    if cmd == "estado":
        for l in lineas_cierre(repo):
            print(l)
        return 0
    ok, txt = volver(repo, a)
    print(("✓ " if ok else "✗ ") + txt)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
