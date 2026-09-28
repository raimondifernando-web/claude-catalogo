#!/usr/bin/env python3
"""cowork-publicar — publica tus skills de Claude Code en Cowork, sin subirlas a mano.

Cowork instala plugins desde un repositorio de GitHub (marketplace). Este script copia cada skill tuya que tenga
`sync: cowork` en el encabezado a un repositorio PRIVADO tuyo, lo valida y lo sube. Cowork lo toma de ahí.
Claude Code queda como la única fuente: si cambiás la skill en Code y volvés a publicar, Cowork recibe la nueva.

Uso (lo corre Claude a pedido, con /metodo:cowork):
  cowork-publicar.py preparar <carpeta> <nombre-plugin>   arma el repo local la primera vez
  cowork-publicar.py                                       arma, verifica y sube si cambió algo
  cowork-publicar.py --dry-run                             arma y verifica, no sube
  cowork-publicar.py --revisar                             solo lista qué skills pasan y cuáles no

Configuración: <CLAUDE_CONFIG_DIR o ~/.claude>/cowork/config.json  {"repo": "<carpeta local>", "plugin": "<nombre>"}
Nunca sube archivos de entorno ni carpetas de estado, y frena si encuentra algo con forma de clave.
"""
import glob, json, os, re, shutil, subprocess, sys, time

BASE = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude")
SKILLS = os.path.join(BASE, "skills")
DIR = os.path.join(BASE, "cowork")
CONFIG = os.path.join(DIR, "config.json")
LOCK = os.path.join(DIR, ".lock")
LOG = os.path.join(DIR, "cowork.log")
EXCLUIR_DIRS = {".git", "__pycache__", "node_modules", ".omc", ".venv", "venv"}
CLAVES = re.compile(r"(sk-[A-Za-z0-9]{24,}|ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|AKIA[0-9A-Z]{16}"
                    r"|xox[bp]-\d{6,}-[A-Za-z0-9-]{10,}|-----BEGIN [A-Z ]*PRIVATE KEY)")
PERMITIDOS = {"name", "description", "license", "allowed-tools", "metadata", "compatibility", "sync"}


def log(msg):
    linea = f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {msg}"
    print(linea)
    os.makedirs(DIR, exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(linea + "\n")


def leer(p):
    return open(p, encoding="utf-8").read()


def cabecera(txt):
    return txt.split("\n---", 1)[0][4:] if txt.startswith("---") else ""


def encabezado(txt):
    """Lee el encabezado YAML. Con PyYAML si está; si no, un lector mínimo de claves de una línea."""
    cab = cabecera(txt)
    try:
        import yaml
        d = yaml.safe_load(cab)
        return d if isinstance(d, dict) else None
    except ImportError:
        d = {}
        for m in re.finditer(r"^([A-Za-z-]+):\s*(.*)$", cab, re.M):
            v = m.group(2).strip()
            if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
                v = v[1:-1]
            d[m.group(1)] = v
        return d or None


def skills_cowork():
    if not os.path.isdir(SKILLS):
        return
    for n in sorted(os.listdir(SKILLS)):
        p = os.path.join(SKILLS, n, "SKILL.md")
        if not n.startswith(("_", ".")) and os.path.isfile(p) and re.search(r"^sync:\s*cowork\s*$", cabecera(leer(p)), re.M):
            yield n


def nativas_de_cowork():
    """Skills que Cowork ya trae de fábrica: no se publican (gana la oficial). Solo Mac con Claude Desktop; en otro
    sistema devuelve vacío y no pasa nada."""
    ms = sorted(glob.glob(os.path.expanduser(
        "~/Library/Application Support/Claude/local-agent-mode-sessions/skills-plugin/*/*/manifest.json")), key=os.path.getmtime)
    try:
        return {s["name"] for s in json.load(open(ms[-1], encoding="utf-8")).get("skills", [])
                if s.get("creatorType") == "anthropic"} if ms else set()
    except Exception:
        return set()


def problemas(n):
    """Reglas de claude.ai para skills de plugin. UNA skill que no cumple hace fallar la sincronización de TODO el
    marketplace, por eso la que no cumple se saltea y se avisa."""
    txt = leer(os.path.join(SKILLS, n, "SKILL.md"))
    try:
        d = encabezado(txt)
    except Exception as e:
        return [f"encabezado inválido ({str(e).splitlines()[0][:60]})"]
    if not d:
        return ["sin encabezado"]
    p = []
    if d.get("name") != n or not re.fullmatch(r"[a-z0-9-]{1,64}", str(d.get("name", ""))):
        p.append(f"name {d.get('name')!r}: tiene que ser igual a la carpeta, en minúsculas y con guiones")
    desc = str(d.get("description") or "")
    if not desc:
        p.append("falta description")
    elif len(desc) > 1024:
        p.append(f"description de {len(desc)} caracteres (máximo 1024)")
    if "<" in desc or ">" in desc:
        p.append("description con < o >")
    if desc.lstrip().startswith(("[", "{")):
        p.append("description que empieza con [ o {")
    if re.search(r"\\u[0-9a-fA-F]{4}", cabecera(txt)):
        p.append("encabezado con escapes \\uXXXX (escribir el carácter directo)")
    extra = set(d) - PERMITIDOS
    if extra:
        log(f"aviso {n}: campos que Cowork no usa: {', '.join(sorted(extra))} (conviene moverlos a metadata)")
    return p


def copiar(origen, destino):
    for raiz, dirs, archivos in os.walk(origen, followlinks=True):
        dirs[:] = [d for d in dirs if d not in EXCLUIR_DIRS]
        rel = os.path.relpath(raiz, origen)
        os.makedirs(os.path.join(destino, rel), exist_ok=True)
        for a in archivos:
            if (a.startswith(".env") and not a.endswith(".example")) or a == ".DS_Store":
                continue
            shutil.copy2(os.path.join(raiz, a), os.path.join(destino, rel, a))


def git(repo, *args):
    return subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True)


def preparar(carpeta, plugin):
    if not re.fullmatch(r"[a-z0-9-]{1,64}", plugin):
        print("El nombre del plugin va en minúsculas y con guiones (ej. skills-estudio)."); return 1
    carpeta = os.path.abspath(os.path.expanduser(carpeta))
    os.makedirs(os.path.join(carpeta, ".claude-plugin"), exist_ok=True)
    os.makedirs(os.path.join(carpeta, "plugins", plugin, ".claude-plugin"), exist_ok=True)
    mk = os.path.join(carpeta, ".claude-plugin", "marketplace.json")
    if not os.path.exists(mk):
        json.dump({"name": f"{plugin}-privado", "owner": {"name": plugin}, "metadata": {"version": "1.0.0"},
                   "plugins": [{"name": plugin, "source": f"./plugins/{plugin}", "version": "1.0.0",
                                "description": "Skills propias publicadas desde Claude Code."}]},
                  open(mk, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    pj = os.path.join(carpeta, "plugins", plugin, ".claude-plugin", "plugin.json")
    if not os.path.exists(pj):
        json.dump({"name": plugin, "version": "1.0.0", "description": "Skills propias publicadas desde Claude Code."},
                  open(pj, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    gi = os.path.join(carpeta, ".gitignore")
    if not os.path.exists(gi):
        open(gi, "w", encoding="utf-8").write(".env*\n!.env.example\n.DS_Store\n__pycache__/\n")
    if not os.path.isdir(os.path.join(carpeta, ".git")):
        git(carpeta, "init", "-q", "-b", "main")
    # Primer commit con el esqueleto: si una publicación se frena, la limpieza no lo borra.
    git(carpeta, "add", "-A")
    if git(carpeta, "status", "--porcelain").stdout.strip():
        git(carpeta, "commit", "-q", "-m", "esqueleto del marketplace de Cowork")
    os.makedirs(DIR, exist_ok=True)
    json.dump({"repo": carpeta, "plugin": plugin}, open(CONFIG, "w", encoding="utf-8"), indent=2)
    log(f"preparado {carpeta} (plugin {plugin})")
    return 0


def main():
    if len(sys.argv) >= 2 and sys.argv[1] == "preparar":
        if len(sys.argv) != 4:
            print(__doc__); return 1
        return preparar(sys.argv[2], sys.argv[3])
    try:
        cfg = json.load(open(CONFIG, encoding="utf-8"))
        repo, plugin = cfg["repo"], cfg["plugin"]
    except Exception:
        print(f"Falta la configuración ({CONFIG}). Primero: cowork-publicar.py preparar <carpeta> <nombre-plugin>")
        return 1
    nativas = nativas_de_cowork()
    nombres, omitidas = [], []
    for n in skills_cowork():
        if n in nativas:
            log(f"omitida {n}: Cowork ya la trae de fábrica"); continue
        prob = problemas(n)
        (omitidas.append(f"{n}: {'; '.join(prob)}") if prob else nombres.append(n))
    for o in omitidas:
        log(f"OMITIDA {o}")
    if "--revisar" in sys.argv:
        log(f"revisión: {len(nombres)} pasan, {len(omitidas)} omitidas"); return 0
    if not os.path.isdir(os.path.join(repo, ".git")):
        log(f"ERROR: no existe el repositorio local {repo}"); return 1
    os.makedirs(DIR, exist_ok=True)
    try:
        os.mkdir(LOCK)
    except FileExistsError:
        if time.time() - os.path.getmtime(LOCK) < 600:
            log("otra publicación en curso: salgo"); return 0
        os.rmdir(LOCK); os.mkdir(LOCK)
    try:
        tiene_remoto = bool(git(repo, "remote").stdout.strip())
        if tiene_remoto:
            git(repo, "pull", "--rebase", "--autostash", "-q")
        destino = os.path.join(repo, "plugins", plugin, "skills")
        shutil.rmtree(destino, ignore_errors=True)
        for n in nombres:
            copiar(os.path.join(SKILLS, n), os.path.join(destino, n))
        sospechosos = []
        for raiz, _, archivos in os.walk(destino):
            for a in archivos:
                p = os.path.join(raiz, a)
                try:
                    if CLAVES.search(open(p, encoding="utf-8", errors="ignore").read()):
                        sospechosos.append(os.path.relpath(p, destino))
                except OSError:
                    pass
        if sospechosos:
            log(f"FRENADO: {len(sospechosos)} archivo(s) con forma de clave: {', '.join(sospechosos[:5])}")
            git(repo, "checkout", "--", "plugins"); git(repo, "clean", "-fdq", "plugins")
            return 2
        git(repo, "add", "-A", "plugins")
        if not git(repo, "status", "--porcelain").stdout.strip():
            log(f"sin cambios ({len(nombres)} skills)"); return 0
        # Cowork exige versión para aceptar el marketplace: sube sola en cada publicación.
        v = int(git(repo, "rev-list", "--count", "HEAD").stdout.strip() or "0") + 1
        for rel in (f"plugins/{plugin}/.claude-plugin/plugin.json", ".claude-plugin/marketplace.json"):
            ruta = os.path.join(repo, rel)
            nuevo = re.sub(r'"version": "1\.0\.\d+"', f'"version": "1.0.{v}"', leer(ruta))  # leer ANTES de abrir en "w"
            open(ruta, "w", encoding="utf-8").write(nuevo)
        git(repo, "add", "-A")
        if "--dry-run" in sys.argv:
            log(f"dry-run: habría publicado {len(nombres)} skills")
            git(repo, "reset", "-q"); git(repo, "checkout", "--", "."); git(repo, "clean", "-fdq", "plugins"); return 0
        git(repo, "commit", "-q", "-m", f"publicado desde Claude Code: {len(nombres)} skills")
        if not tiene_remoto:
            log(f"guardado local ({len(nombres)} skills); falta conectar el repositorio de GitHub"); return 0
        r = git(repo, "push", "-q", "-u", "origin", "HEAD")
        log(f"publicado ({len(nombres)} skills)" if r.returncode == 0 else f"ERROR al subir: {r.stderr.strip()[:200]}")
        return r.returncode
    finally:
        os.rmdir(LOCK)


if __name__ == "__main__":
    sys.exit(main())
