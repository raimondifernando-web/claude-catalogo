#!/usr/bin/env python3
"""Consumo de minutos de GitHub Actions del ciclo (solo repos PRIVADOS; los públicos no gastan). 2026-10-19.

Disparador: encadenado — `--aviso` lo llama el arranque de sesión (`arrancar-check.py` en el kit; `fallos-tecnicos.py`
en la config de Tech) y, si el cache tiene más de 3 h, lanza la medición en segundo plano. Manual: `--informe`.

Por qué existe: GitHub trae un tope mensual de minutos para repos privados (Pro = 3.000; Linux ×1, Windows ×2,
macOS ×10) y avisa tarde (75/90/100 %) y por mail. La llave limitada de Claude NO lee la facturación (403), así que
se mide sumando los jobs de cada corrida (por job, redondeado hacia arriba): es una ESTIMACIÓN; el 2026-10-19
coincidió con el aviso del 90 % de GitHub.

Avisa desde el 60 % (temprano), 80 % (alto: no sumar robots nuevos) y 90 % (crítico: congelar), una vez por escalón
en cada ciclo, y siempre desde el 90 %. El dueño sale de `gh api user`; si falta `gh` o su sesión, calla.

Configurable por entorno: ACTIONS_CUPO_MIN (3000 = plan Pro; Free = 2000) y ACTIONS_CICLO_DIA (día del mes en que
se renueva; default 4, INFERIDO del aviso del 90 % del 2026-10-19: confirmarlo en GitHub → Settings → Billing and
licensing). Cache en `$CEREBRO_HOME` (o `~/.cerebro`) si existe; si no, `<config de Claude>/metodo/`.
Solo guarda números y nombres de workflows, nunca secretos.

Uso: actions-consumo.py [--informe | --aviso]   (sin argumentos: mide y actualiza el cache)
"""
import datetime as dt
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor

HOME = os.path.expanduser("~")
CONFIG = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(HOME, ".claude")
_CEREBRO = os.environ.get("CEREBRO_HOME") or os.path.join(HOME, ".cerebro")
DIR = _CEREBRO if os.path.isdir(_CEREBRO) else os.path.join(CONFIG, "metodo")
ARCHIVO = os.path.join(DIR, "actions-consumo.json")
MARCA = os.path.join(DIR, "actions-consumo-aviso.json")
GH_CONFIG = os.environ.get("ACTIONS_GH_CONFIG") or (
    os.path.join(HOME, ".config/gh-claude") if os.path.isdir(os.path.join(HOME, ".config/gh-claude")) else "")
CUPO = int(os.environ.get("ACTIONS_CUPO_MIN", "3000"))
CICLO_DIA = min(max(int(os.environ.get("ACTIONS_CICLO_DIA", "4") or 4), 1), 28)  # 1-28: existe en todos los meses
TTL_H = 3
ESCALONES = ((90, "CRÍTICO: congelar robots y workflows nuevos"), (80, "ALTO: no sumar robots ni crons nuevos"),
             (60, "aviso temprano"))


def inicio_ciclo(hoy):
    d = hoy.date().replace(day=CICLO_DIA)
    if d > hoy.date():  # todavía rige el ciclo del mes anterior
        d = (d.replace(day=1) - dt.timedelta(days=1)).replace(day=CICLO_DIA)
    return d


def gh(args):
    env = dict(os.environ, GH_PROMPT_DISABLED="1")
    if GH_CONFIG:
        env["GH_CONFIG_DIR"] = GH_CONFIG
    r = subprocess.run(["gh"] + args, capture_output=True, text=True, timeout=60, env=env)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or "error").strip().splitlines()[0][:120])
    return r.stdout


def jsonl(args, jq):
    out = gh(["api", "--paginate"] + args + ["--jq", jq])
    return [json.loads(l) for l in out.splitlines() if l.strip()]


def parse(s):
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))


def mult(labels):
    t = " ".join(labels or ["ubuntu"]).lower()
    return 10 if "mac" in t else 2 if "win" in t else 1


RUN_JQ = ".workflow_runs[]|{id,name,event,created_at,status}"


def runs_repo(owner, repo, desde):
    ruta = f"repos/{owner}/{repo}/actions/runs?per_page=100&created="
    runs = jsonl([ruta + f">={desde}"], RUN_JQ)
    if len(runs) >= 1000:  # la API corta en 1000: se parte por día
        runs, dia = [], dt.date.fromisoformat(desde)
        while dia <= dt.date.today():
            runs += jsonl([ruta + f"{dia}T00:00:00Z..{dia}T23:59:59Z"], RUN_JQ)
            dia += dt.timedelta(days=1)
    return runs


def minutos_run(owner, repo, run_id):
    jobs = jsonl([f"repos/{owner}/{repo}/actions/runs/{run_id}/jobs?per_page=100"],
                 ".jobs[]|{started_at,completed_at,conclusion,labels}")
    m = 0
    for j in jobs:
        if not j["started_at"] or not j["completed_at"] or j["conclusion"] == "skipped":
            continue
        s = (parse(j["completed_at"]) - parse(j["started_at"])).total_seconds()
        if s > 0:
            m += math.ceil(s / 60) * mult(j["labels"])
    return m


def actualizar():
    hoy = dt.datetime.now(dt.timezone.utc)
    ini = inicio_ciclo(hoy)
    desde = ini.isoformat()
    try:
        cache = json.load(open(ARCHIVO, encoding="utf-8"))
        if cache.get("desde") != desde:
            cache = {"runs": {k: v for k, v in cache.get("runs", {}).items() if v["d"] >= desde}}
    except Exception:
        cache = {}
    runs = cache.get("runs", {})  # "repo/id" -> {"m": min, "w": workflow, "e": evento, "d": dia, "r": repo}
    owner = os.environ.get("ACTIONS_OWNER") or gh(["api", "user", "--jq", ".login"]).strip()
    repos = [r["name"] for r in json.loads(gh(["repo", "list", owner, "--limit", "200", "--json", "name,isPrivate"]))
             if r["isPrivate"]]

    def listar(repo):
        try:
            return repo, runs_repo(owner, repo, desde)
        except Exception:
            return repo, None

    with ThreadPoolExecutor(8) as ex:
        listados = list(ex.map(listar, repos))
    pendientes = [(repo, x, f"{repo}/{x['id']}") for repo, rs in listados if rs is not None for x in rs
                  if f"{repo}/{x['id']}" not in runs and x["status"] == "completed"]

    def medir(p):
        repo, x, k = p
        try:
            return k, {"m": minutos_run(owner, repo, x["id"]), "w": x["name"], "e": x["event"],
                       "d": x["created_at"][:10], "r": repo}
        except Exception:
            return k, None

    with ThreadPoolExecutor(12) as ex:
        for k, v in ex.map(medir, pendientes):
            if v:
                runs[k] = v
    runs = {k: v for k, v in runs.items() if v["d"] >= desde}
    total = sum(v["m"] for v in runs.values())
    renueva = (ini.replace(day=1) + dt.timedelta(days=32)).replace(day=CICLO_DIA)
    dias_ciclo = (renueva - ini).days
    dias_pasados = (hoy - dt.datetime.combine(ini, dt.time(), dt.timezone.utc)).total_seconds() / 86400
    cache = {"ts": hoy.timestamp(), "desde": desde, "cupo": CUPO, "total": total,
             "proyeccion": round(total / max(dias_pasados, 1) * dias_ciclo), "runs": runs,
             "renueva": renueva.isoformat()}
    os.makedirs(DIR, exist_ok=True)
    tmp = ARCHIVO + ".tmp"
    json.dump(cache, open(tmp, "w", encoding="utf-8"))
    try:
        os.chmod(tmp, 0o600)
    except OSError:
        pass
    os.replace(tmp, ARCHIVO)
    return cache


def informe(c):
    def top(clave, n=8):
        acc = {}
        for v in c["runs"].values():
            acc[v[clave]] = acc.get(v[clave], 0) + v["m"]
        return sorted(acc.items(), key=lambda z: -z[1])[:n]
    print(f"Actions ciclo desde {c['desde']}: {c['total']} de {c['cupo']} min ({round(100 * c['total'] / c['cupo'])} %), "
          f"proyección {c['proyeccion']} min, se renueva el {c['renueva']} (estimado por jobs).")
    for t, k in (("por repo", "r"), ("por workflow", "w"), ("por disparador", "e")):
        print(f"  {t}: " + " · ".join(f"{a} {b}" for a, b in top(k)))


def linea_aviso(c, ya_avisado=None):
    """Texto del aviso según el escalón (60/80/90 %) o None. `ya_avisado` = escalón ya mostrado en este ciclo."""
    pct = 100 * c["total"] / max(c.get("cupo", CUPO), 1)
    for piso, texto in ESCALONES:
        if pct >= piso:
            if ya_avisado is not None and piso <= ya_avisado and piso < 90:
                return None
            return (f"GitHub Actions al {int(pct)} % ({c['total']} de {c.get('cupo', CUPO)} min del ciclo; "
                    f"proyección {c.get('proyeccion', '?')}; se renueva el {c.get('renueva', '?')}) — {texto}. "
                    "Detalle: actions-consumo.py --informe", piso)
    return None


def aviso():
    """Imprime el aviso (si corresponde) y lanza la medición en segundo plano si el cache está viejo. Nunca falla."""
    try:
        c = json.load(open(ARCHIVO, encoding="utf-8"))
    except Exception:
        c = {}
    # No se lanza la medición si la config vive en una carpeta temporal (pruebas): un proceso suelto trabaría su borrado en Windows.
    en_temporal = os.path.realpath(DIR).startswith(os.path.realpath(tempfile.gettempdir()))
    if shutil.which("gh") and not en_temporal and time.time() - float(c.get("ts", 0)) > TTL_H * 3600:
        try:
            extra = {"creationflags": 0x00000008 | 0x00000200} if os.name == "nt" else {"start_new_session": True}
            subprocess.Popen([sys.executable, os.path.abspath(__file__)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             stdin=subprocess.DEVNULL, cwd=HOME, **extra)   # cwd=HOME: no deja trabada la carpeta de quien lo llamó
        except Exception:
            pass
    if not c.get("total") and c.get("total") != 0:
        return
    try:
        marca = json.load(open(MARCA, encoding="utf-8"))
    except Exception:
        marca = {}
    ya = marca.get("piso") if marca.get("desde") == c.get("desde") else None
    r = linea_aviso(c, ya)
    if r:
        print(r[0])
        try:
            json.dump({"desde": c.get("desde"), "piso": r[1]}, open(MARCA, "w", encoding="utf-8"))
        except OSError:
            pass


if __name__ == "__main__":
    try:
        if "--aviso" in sys.argv:
            aviso()
        else:
            c = actualizar()
            if "--informe" in sys.argv:
                informe(c)
    except Exception as e:
        if "--aviso" not in sys.argv:
            print(f"actions-consumo: no pude medir ({type(e).__name__}: {e})", file=sys.stderr)
            sys.exit(1)
