#!/usr/bin/env python3
"""seguridad.py — chequeo de seguridad mensual de tus repositorios. Solo lectura: no cambia nada en ellos.

Qué mira en cada repositorio de tu lista (nunca muestra el valor de una clave: solo nombres, conteos y estados):
  REPO-001  la carpeta existe y es un repositorio git
  ENV-001   los archivos de claves (.env y parecidos) tienen permisos solo para vos (600)
  ENV-002   las claves que anotaste están (se cuentan por NOMBRE; el valor no se lee)
  GIT-001   el .gitignore deja afuera los archivos .env
  GIT-002   no hay archivos de claves guardados en el repositorio (.env, .pem, .key, id_rsa, credentials.json…)
  GH-001    el repositorio en GitHub es privado (o lo marcaste como público a propósito) y la dirección no lleva clave
  ACT-001   las acciones de GitHub están fijadas por su código de 40 caracteres, no por un nombre que puede cambiar
  ACT-002   cada flujo de GitHub declara sus permisos
  ACT-003   ningún flujo usa pull_request_target (deja correr código ajeno con tus permisos)
  DIST-001  si el repo es para repartir (marcado "distribucion"), no tiene ningún archivo .env

La lista de repositorios es tuya, en <config de Claude>/metodo/seguridad.json (si no existe, no hace nada):
  {"repos": [{"ruta": "~/mi-repo", "claves": ["NOMBRE_DE_LA_CLAVE"]},
             {"ruta": "~/otro-repo", "publico": true, "distribucion": true}]}
Para sumar uno sin editar a mano:  python3 seguridad.py agregar ~/mi-repo

Uso:
  python3 seguridad.py correr     corre el chequeo, deja el informe y una línea de resultado
  python3 seguridad.py agregar RUTA [--claves A,B] [--publico] [--distribucion]
Lo corre solo, una vez por mes y en segundo plano, seguridad-auto.sh (hook del paquete metodo).
"""
import datetime as dt
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

ESTADOS = ("PASS", "FLAG", "REVISAR", "NA")
SALTEAR = {".git", "node_modules", ".venv", "venv", "__pycache__", "graphify-out", ".next", "dist", "build"}
EJEMPLOS = {".env.example", ".env.sample", ".env.template", ".env.dist"}
QUE_ES = {
    "REPO-001": "no encontré la carpeta o no es un repositorio",
    "ENV-001": "archivos de claves con permisos abiertos",
    "ENV-002": "faltan claves que anotaste",
    "GIT-001": "el .gitignore no deja afuera los .env",
    "GIT-002": "hay archivos de claves guardados en el repositorio",
    "GH-001": "repositorio público o dirección con clave",
    "ACT-001": "acciones de GitHub sin fijar",
    "ACT-002": "flujos de GitHub sin permisos declarados",
    "ACT-003": "flujo con pull_request_target",
    "DIST-001": "archivos .env en un repo para repartir",
}


def base_config():
    return Path(os.environ.get("CLAUDE_CONFIG_DIR") or str(Path.home() / ".claude")) / "metodo"


def item(cid, estado, evidencia):
    return {"id": cid, "estado": estado, "evidencia": evidencia}


def git(raiz, *args):
    # -c core.fsmonitor=false: que un repo no pueda hacer correr un programa propio al consultarlo
    return subprocess.run(["git", "-c", "core.fsmonitor=false", "-C", str(raiz)] + list(args),
                          stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=60, check=False)


def es_archivo_de_claves(nombre):
    if nombre in EJEMPLOS:
        return False
    return nombre == ".env" or nombre.startswith(".env.") or nombre.endswith(".env")


def archivos_env(raiz, saltear=SALTEAR):
    hallados = []
    for carpeta, subcarpetas, archivos in os.walk(str(raiz), followlinks=False):
        subcarpetas[:] = [d for d in subcarpetas if d not in saltear]
        for a in archivos:
            p = Path(carpeta) / a
            if es_archivo_de_claves(a) and p.is_file() and not p.is_symlink():
                hallados.append(p)
    return hallados


def permisos_env(archivos):
    if not archivos:
        return item("ENV-001", "NA", "sin archivos de claves")
    bien = sum(stat.S_IMODE(p.stat().st_mode) & 0o077 == 0 for p in archivos)
    return item("ENV-001", "PASS" if bien == len(archivos) else "FLAG",
                "{}/{} archivo(s) de claves solo para vos".format(bien, len(archivos)))


def claves_por_nombre(archivos, nombres):
    if not nombres:
        return item("ENV-002", "NA", "no anotaste claves para buscar")
    cuenta = dict.fromkeys(nombres, 0)
    for p in archivos:
        with p.open("rb") as f:
            for linea in f:
                if b"=" not in linea:
                    continue
                # solo el nombre antes del «=»; el valor nunca se lee como texto ni se guarda
                nombre = linea.split(b"=", 1)[0].strip()
                if nombre.startswith(b"export "):
                    nombre = nombre[7:].strip()
                nombre = nombre.decode("ascii", "ignore")
                if nombre in cuenta:
                    cuenta[nombre] += 1
    faltan = [n for n in nombres if not cuenta[n]]
    return item("ENV-002", "FLAG" if faltan else "PASS",
                "están {}/{}".format(len(nombres) - len(faltan), len(nombres)) +
                ("; faltan: " + ", ".join(faltan) if faltan else ""))


def gitignore_env(raiz):
    if not (raiz / ".gitignore").is_file():
        return item("GIT-001", "FLAG", "no hay .gitignore")
    # le pregunta a git (respeta «!» y comodines); solo vale una regla de un .gitignore del proyecto
    r = git(raiz, "check-ignore", "-v", "--no-index", "--", ".env")
    salida = r.stdout.decode("utf-8", "replace") if r.returncode == 0 else ""
    regla = salida.split("\t", 1)[0]
    fuente, patron = regla.split(":", 1)[0], regla.split(":", 2)[-1]
    ok = bool(salida) and fuente.endswith(".gitignore") and not fuente.startswith("/") and not patron.startswith("!")
    return item("GIT-001", "PASS" if ok else "FLAG", "regla para .env presente" if ok else "sin regla para .env")


def guardados_sensibles(raiz):
    r = git(raiz, "ls-files", "-z")
    if r.returncode:
        return item("GIT-002", "REVISAR", "no pude consultar git")
    rutas = [x for x in r.stdout.decode("utf-8", "replace").split("\0") if x]
    def sensible(ruta):
        n = Path(ruta).name
        return (es_archivo_de_claves(n) or n.endswith((".key", ".pem", ".p12", ".pfx", ".jks")) or
                n.startswith(("id_rsa", "id_ed25519", "id_ecdsa")) or n == "credentials.json")
    n = sum(sensible(x) for x in rutas)
    return item("GIT-002", "FLAG" if n else "PASS", "{} archivo(s) de claves guardado(s) en el repositorio".format(n))


def github(raiz, publico_a_proposito):
    r = git(raiz, "remote", "get-url", "origin")
    if r.returncode:
        return item("GH-001", "NA", "sin dirección de GitHub")
    url = r.stdout.decode("utf-8", "replace").strip()   # nunca se muestra: puede traer una clave
    if re.search(r"(?i)^https?://[^/\s]*@", url):
        return item("GH-001", "FLAG", "la dirección del repositorio lleva usuario o clave incrustados")
    m = re.search(r"github\.com[:/]([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git)?/?$", url, re.IGNORECASE)
    if not m or not re.match(r"[A-Za-z0-9]", m.group(1)):
        return item("GH-001", "NA", "el repositorio no está en GitHub")
    try:
        p = subprocess.run(["gh", "repo", "view", "--json", "isPrivate", "--", m.group(1)], stdout=subprocess.PIPE,
                           stderr=subprocess.DEVNULL, timeout=30, check=False,
                           env=dict(os.environ, GH_PROMPT_DISABLED="1", GH_NO_UPDATE_NOTIFIER="1"))
        privado = json.loads(p.stdout.decode() or "{}").get("isPrivate") if p.returncode == 0 else None
    except (OSError, ValueError, subprocess.TimeoutExpired):
        privado = None
    if privado is None:
        return item("GH-001", "REVISAR", "no pude preguntarle a GitHub (¿falta gh o su sesión?)")
    if privado:
        return item("GH-001", "PASS", "repositorio privado")
    return item("GH-001", "PASS" if publico_a_proposito else "FLAG",
                "repositorio público" + (" (marcado a propósito)" if publico_a_proposito else ""))


def flujos(raiz):
    carpeta = raiz / ".github" / "workflows"
    archivos = sorted(list(carpeta.glob("*.yml")) + list(carpeta.glob("*.yaml"))) if carpeta.is_dir() else []
    if not archivos:
        return [item(c, "NA", "sin flujos de GitHub") for c in ("ACT-001", "ACT-002", "ACT-003")]
    sin_fijar = sin_permisos = con_target = 0
    for p in archivos:
        t = p.read_text(errors="ignore")
        sin_fijar += len(re.findall(r"(?m)^\s*(?:-\s*)?uses:\s*['\"]?(?!\./)[^@\s'\"]+@(?![0-9a-fA-F]{40}\b)\S+", t))
        sin_permisos += not re.search(r"(?m)^permissions\s*:", t)
        con_target += bool(re.search(r"(?m)^[^#\n]*\bpull_request_target\b", t))
    return [item("ACT-001", "FLAG" if sin_fijar else "PASS", "{} acción(es) sin fijar".format(sin_fijar)),
            item("ACT-002", "FLAG" if sin_permisos else "PASS",
                 "{}/{} flujo(s) sin permisos declarados".format(sin_permisos, len(archivos))),
            item("ACT-003", "FLAG" if con_target else "PASS", "{} flujo(s) con pull_request_target".format(con_target))]


def revisar_repo(spec):
    raiz = Path(os.path.expanduser(str(spec.get("ruta", "")))).resolve()
    nombre = str(spec.get("nombre") or raiz.name)
    if not raiz.is_dir() or git(raiz, "rev-parse", "--git-dir").returncode:
        return {"nombre": nombre, "items": [item("REPO-001", "FLAG", "no encontré la carpeta o no es un repositorio")]}
    env = archivos_env(raiz)
    claves = [str(c) for c in spec.get("claves", []) if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", str(c))]
    items = [item("REPO-001", "PASS", "repositorio encontrado"), permisos_env(env), claves_por_nombre(env, claves),
             gitignore_env(raiz), guardados_sensibles(raiz), github(raiz, bool(spec.get("publico"))), *flujos(raiz)]
    if spec.get("distribucion"):
        todos = archivos_env(raiz, saltear={".git", "node_modules"})   # dist/ y build/ son justo lo que se reparte
        items.append(item("DIST-001", "FLAG" if todos else "PASS", "{} archivo(s) .env".format(len(todos))))
    return {"nombre": nombre, "items": items}


def nombre_seguro(n):
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", n).strip(".-") or "repo"


def escribir(ruta, texto):
    fd, tmp = tempfile.mkstemp(dir=str(ruta.parent), prefix=".seguridad-")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(texto)
    os.chmod(tmp, 0o600)
    os.replace(tmp, str(ruta))


def informe(repo, fecha):
    tot = {e: sum(i["estado"] == e for i in repo["items"]) for e in ESTADOS}
    filas = ["| {} | {} | {} |".format(i["id"], i["estado"], i["evidencia"].replace("|", "/")) for i in repo["items"]]
    return "\n".join(["# Chequeo de seguridad — {} — {}".format(repo["nombre"], fecha), "",
                      "{} bien · {} ✗ · {} a revisar · {} no aplica".format(
                          tot["PASS"], tot["FLAG"], tot["REVISAR"], tot["NA"]), "",
                      "| Qué | Estado | Evidencia |", "|---|---|---|"] + filas) + "\n"


def leer_lista(cfg):
    datos = json.loads(cfg.read_text(encoding="utf-8"))
    repos = datos.get("repos") if isinstance(datos, dict) else None
    if not isinstance(repos, list) or not all(isinstance(r, dict) and r.get("ruta") for r in repos):
        raise ValueError("lista mal armada")
    return repos


def correr(cfg, salida):
    if not cfg.is_file():
        print("Chequeo de seguridad: no hay lista de repositorios ({}). No hice nada.".format(cfg))
        return 0
    salida.mkdir(parents=True, exist_ok=True)
    os.chmod(str(salida), 0o700)
    resultado = salida.parent / "seguridad.resultado"
    try:
        repos = leer_lista(cfg)
    except (ValueError, OSError):
        escribir(resultado, "la lista de repositorios tiene un error ✗ ({})\n".format(cfg))
        print("Chequeo de seguridad: la lista de repositorios tiene un error ✗ ({})".format(cfg))
        return 1
    fecha = dt.date.today().isoformat()
    carpeta = salida / fecha
    carpeta.mkdir(parents=True, exist_ok=True)
    os.chmod(str(carpeta), 0o700)
    revisados, usados = [], set()
    for spec in repos:
        try:
            r = revisar_repo(spec)
        except Exception:   # un repo que no se puede leer no frena a los demás
            r = {"nombre": str(spec.get("nombre") or Path(str(spec.get("ruta"))).name),
                 "items": [item("REPO-001", "REVISAR", "no pude revisarlo entero (permisos o archivos raros)")]}
        base = nombre_seguro(r["nombre"])
        archivo, n = base, 2
        while archivo in usados:
            archivo, n = "{}-{}".format(base, n), n + 1
        usados.add(archivo)
        escribir(carpeta / (archivo + ".md"), informe(r, fecha))
        revisados.append(r)
    escribir(carpeta / "resumen.json", json.dumps({"fecha": fecha, "repos": revisados}, ensure_ascii=False, indent=2) + "\n")
    fallas = [(r["nombre"], i["id"]) for r in revisados for i in r["items"] if i["estado"] == "FLAG"]
    if fallas:
        detalle = "; ".join("{}: {}".format(nombre_seguro(n)[:40], QUE_ES.get(cid, cid)) for n, cid in fallas[:3])
        mas = " y {} más".format(len(fallas) - 3) if len(fallas) > 3 else ""
        linea = "{} ✗ ({}{}). Informe: {}".format(len(fallas), detalle, mas, carpeta)
    else:
        linea = "ok {}".format(fecha)
    escribir(resultado, linea + "\n")
    print("Chequeo de seguridad: " + (linea if fallas else "{} repositorio(s), todo bien ✓".format(len(revisados))))
    return 0


def agregar(cfg, ruta, claves, publico, distribucion):
    raiz = Path(os.path.expanduser(ruta)).resolve()
    if not raiz.is_dir():
        print("Falta: no encuentro la carpeta {} ✗".format(raiz)); return 1
    malas = [c for c in claves if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", c)]
    if malas:
        print("Falta: los nombres de claves van sin valor, solo letras, números y _ ✗"); return 1
    repos = []
    if cfg.is_file():
        try:
            repos = leer_lista(cfg)
        except (ValueError, OSError):
            print("Falta: la lista {} tiene un error; no la toqué ✗".format(cfg)); return 1
    casa = str(Path.home().resolve())
    texto = str(raiz)
    texto = "~" + texto[len(casa):] if texto == casa or texto.startswith(casa + os.sep) else texto
    nuevo = {"ruta": texto}
    if claves: nuevo["claves"] = claves
    if publico: nuevo["publico"] = True
    if distribucion: nuevo["distribucion"] = True
    repos = [r for r in repos if Path(os.path.expanduser(str(r["ruta"]))).resolve() != raiz] + [nuevo]
    cfg.parent.mkdir(parents=True, exist_ok=True)
    escribir(cfg, json.dumps({"repos": repos}, ensure_ascii=False, indent=2) + "\n")
    print("Listo ✓ {} en la lista del chequeo de seguridad ({} repositorio(s))".format(raiz.name, len(repos)))
    return 0


def main(argv):
    if not argv or argv[0] not in ("correr", "agregar"):
        print(__doc__); return 2
    base = base_config()
    cfg = base / "seguridad.json"
    if argv[0] == "correr":
        return correr(cfg, base / "seguridad")
    args = argv[1:]
    if not args or args[0].startswith("--"):
        print("Uso: python3 seguridad.py agregar RUTA [--claves A,B] [--publico] [--distribucion]"); return 2
    claves = []
    if "--claves" in args:
        i = args.index("--claves")
        claves = [c.strip() for c in (args[i + 1] if i + 1 < len(args) else "").split(",") if c.strip()]
    return agregar(cfg, args[0], claves, "--publico" in args, "--distribucion" in args)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
