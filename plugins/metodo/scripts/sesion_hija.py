#!/usr/bin/env python3
"""sesion_hija.py — mecánica de cierre limpio para sesiones hijas de Claude Code.
Disparador: encadenado — lo llaman la skill cerrar-hija (lado hija), cerrar-check en modo hija y la orden que inyecta cierre-hijas.py en la coordinadora (recibir).

Qué hace: detecta si la sesión actual es hija o coordinada, saca una foto de los cambios y commits
de otras sesiones en el checkout compartido, sube únicamente los archivos propios creando el commit
remoto sin tocar el checkout ajeno, genera el archivo de traspaso estructurado para la coordinadora
y permite a la coordinadora verificar mecánicamente que todo esté a salvo antes de archivar.

Por qué existe: en un checkout compartido, el cierre tradicional pisa el REANUDAR.md de la madre,
hace pull/rebase afectando commits locales de otras sesiones, o intenta archivar dejando cosas a medias.
Este módulo aísla lo propio de lo ajeno y asegura que la hija entregue su trabajo de forma limpia y verificable.

Qué lee/escribe:
- Lee metadatos de sesiones de la app Claude (CLAUDE_SESIONES_DIR), registro de ediciones (ediciones.py),
  transcripciones en projects/*/<cliSessionId>.jsonl y objetos git.
- Escribe su estado en <CLAUDE_CONFIG_DIR>/state/cierre-hija/ (permisos 0700/0600), commits remotos vía git push,
  y los archivos de traspaso en .claude/prompts/TRASPASO-*.md y en side-session-notes.
- Nunca corre pull, rebase, stash, checkout, switch, reset, merge ni push forzado; nunca imprime contenidos ni variables.

Uso:  sesion_hija.py detectar [--json]          ¿esta sesión es hija? ¿la carpeta es compartida?
      sesion_hija.py foto <repo>...              foto de lo ajeno al EMPEZAR el cierre
      sesion_hija.py comparar                    ¿cambió algo ajeno desde la foto?
      sesion_hija.py subir <repo> -m "…" [--directo] [--rama R] [--incluir RUTA]... [--probar]
      sesion_hija.py traspaso --borrador <archivo.md>
      sesion_hija.py recibir <id de la hija> [--json]   (lo corre la coordinadora)
Pruebas: test_sesion_hija.py, test_cerrar_check_hija.py, test_freno_hija.py.
"""
import argparse
import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unicodedata

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
try:
    import hijas_sesiones as hs  # noqa: E402  (versión de ~/.claude/scripts)
except ImportError:
    import sesiones_hijas as hs  # noqa: E402  (kit del cliente: mismo módulo con otro nombre)
import ediciones as ed  # noqa: E402

def _g(repo, *a):
    """git sin fsmonitor ni hooks del repo; stdout recortado o None si falla (como hs.git, que el kit del cliente no trae)."""
    try:
        r = subprocess.run(["git", "-c", "core.fsmonitor=false", "-c", "core.hooksPath=" + os.devnull, "-C", repo, *a],
                           capture_output=True, text=True, timeout=60)
        return r.stdout.strip() if r.returncode == 0 else None
    except Exception:
        return None


def _raiz():
    if hasattr(hs, "raiz"):
        return hs.raiz()
    return (hs.carpeta_sesiones() if hasattr(hs, "carpeta_sesiones") else None) or os.path.join(
        os.path.expanduser("~"), "Library", "Application Support", "Claude", "claude-code-sessions")


def _mi_sesion(ses, respaldo):
    try:
        return hs.mi_sesion(ses, respaldo=respaldo)
    except TypeError:  # kit: mi_sesion(ses) no adivina
        return hs.mi_sesion(ses)


def _bloqueos(sesion, ses):
    """[(tipo, texto)] que impiden archivar `sesion` (informe sin entregar o sin leer, trabajo sin subir…)."""
    if hasattr(hs, "trabajo_det"):
        return [(k, t) for k, t in hs.trabajo_det(sesion, ses) if k in hs.BLOQUEA]
    return list(hs.bloqueos_det(sesion, ses))


DIRECTO = set()  # repos donde la norma es empujar a main sin PR: se anotan en <config de Claude>/metodo/subir-directo.txt (uno por línea)
# El REANUDAR.md de una carpeta vive en .claude/prompts/ o en la raíz: los dos son del hilo principal.
REANUDARES = (os.path.join(".claude", "prompts", "REANUDAR.md"), "REANUDAR.md")
SENSIBLE = re.compile(r"(^|/)\.env(\.|$)|\.(pem|key|p12|pfx)$|secret|token|password|contrase|credential|api[_-]?key", re.I)


def _estado_dir():
    d = os.path.join(ed.config_dir(), "state", "cierre-hija")
    os.makedirs(d, mode=0o700, exist_ok=True)
    try:
        os.chmod(d, 0o700)
    except OSError:
        pass
    return d


def _escribir_estado(ruta, contenido_str):
    _estado_dir()
    fd = os.open(ruta, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.chmod(ruta, 0o600)
    except OSError:
        pass
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(contenido_str)


def _limpiar_nombre(texto):
    if not texto:
        return "hija"
    norm = unicodedata.normalize("NFKD", texto)
    ascii_txt = norm.encode("ascii", "ignore").decode("ascii").lower()
    s = re.sub(r"[^a-z0-9]+", "-", ascii_txt).strip("-")
    return s[:40] or "hija"


def _arranco_con_arrancar(cli_id):
    """¿La sesión es la continuación de un hilo (la abrió /cerrar paso 13 o una sesión de proyecto con /arrancar)? Se mira el
    pedido con que arrancó: los primeros 3 mensajes de la persona en su transcripción."""
    if not cli_id:
        return False
    patron = os.path.join(ed.config_dir(), "projects", "*", f"{cli_id}.jsonl")
    for f in glob.glob(patron):
        vistos = 0
        try:
            with open(f, encoding="utf-8", errors="replace") as fh:
                for linea in fh:
                    try:
                        obj = json.loads(linea)
                    except ValueError:
                        continue
                    if obj.get("type") != "user" or obj.get("isSidechain") or obj.get("isMeta"):
                        continue
                    msg = obj.get("message")
                    c = msg.get("content") if isinstance(msg, dict) else msg
                    if isinstance(c, list):
                        c = " ".join(x.get("text", "") for x in c if isinstance(x, dict) and x.get("type") == "text")
                    t = (c or "").lower() if isinstance(c, str) else ""
                    if not t.strip() or t.lstrip().startswith("<local-command") or "tool_result" in t[:40]:
                        continue
                    if "/arrancar" in t or "skill arrancar" in t or "sesión abierta sola por /cerrar" in t:
                        return True
                    vistos += 1
                    if vistos >= 3:
                        break
        except OSError:
            continue
    return False


def _status(repo):
    """`git status --porcelain=v1 -z -uall` SIN recortar espacios (hs.git hace strip y se come el espacio inicial de « M ruta»)."""
    try:
        r = subprocess.run(["git", "--no-optional-locks", "-c", "core.fsmonitor=false", "-C", repo, "status", "--porcelain=v1", "-z", "-uall"],
                           capture_output=True, text=True, timeout=30)
        return r.stdout if r.returncode == 0 else ""
    except Exception:
        return ""


def _parse_status_z(raw_status):
    if not raw_status:
        return []
    items = raw_status.split("\0")
    files = []
    i = 0
    while i < len(items):
        item = items[i]
        i += 1
        if not item:
            continue
        status = item[:2]
        path = item[3:]
        if status[0] in "RC" or status[1] in "RC":
            if i < len(items):
                i += 1
        files.append((status, path))
    return files


def _repo_y_dueno(repo):
    url = _g(repo, "remote", "get-url", "origin") or ""
    m = re.search(r"[:/]([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?/?$", url)
    if m:
        return m.group(1), m.group(2)
    # remoto local (ruta de carpeta, también con barras de Windows): el nombre es la última carpeta, sin .git
    nombre = re.sub(r"\.git$", "", os.path.basename(url.replace("\\", "/").rstrip("/"))) or os.path.basename(repo)
    return "dueno", nombre


# ---------------- 1) detectar ----------------


def detectar():
    ses = hs.cargar()
    sid = ed.sid_actual()
    yo = None
    if sid:
        yo = next((s for s in ses if s.get("cliSessionId") == sid), None)
    if not yo:
        cur_pwd = os.path.realpath(os.getcwd())
        resp = [s for s in ses if os.path.realpath(s.get("cwd") or "") == cur_pwd]
        yo = _mi_sesion(ses, resp)

    if not yo:
        return {
            "modo": "normal",
            "motivo": "no encontré esta sesión",
            "sesion": None,
            "cli": sid,
            "titulo": None,
            "nombre": None,
            "padre": None,
            "padre_vivo": False,
            "carpeta": "compartida",
            "cwd": os.getcwd(),
            "notas_dir": None,
        }

    sf = yo.get("spawnedFrom")
    lateral = isinstance(sf, dict) and sf.get("sideSession") is True
    wt = yo.get("worktreePath")
    cur_pwd = os.path.realpath(os.getcwd())
    carpeta_propia = bool(wt) and (
        cur_pwd == os.path.realpath(wt) or cur_pwd.startswith(os.path.realpath(wt) + os.sep)
    )
    cli_id = yo.get("cliSessionId") or sid
    arranco = _arranco_con_arrancar(cli_id)
    lineage_detached = bool(yo.get("lineageDetached"))

    padre_id = hs.padre_de(yo)
    padre_ses = next((s for s in ses if s.get("sessionId") == padre_id), None) if padre_id else None
    padre_vivo = bool(padre_ses and not padre_ses.get("isArchived"))
    padre_titulo = padre_ses.get("title") if padre_ses else "?"

    base_notas = os.environ.get("CLAUDE_NOTAS_DIR") or os.path.join(
        os.path.dirname(_raiz()), "side-session-notes"
    )
    notas_dir = os.path.join(base_notas, padre_id) if padre_id else None

    nombre = _limpiar_nombre(str(sf.get("name")) if isinstance(sf, dict) and sf.get("name") else yo.get("title", ""))
    if nombre == "reanudar":
        nombre = "hija"

    carpeta = "propia" if carpeta_propia else "compartida"
    # ¿la carpeta donde se corre (la que mide cerrar-check) es la de esta sesión? Si no, el modo hija no se aplica a ella.
    suyas = [os.path.realpath(x) for x in (yo.get("cwd"), yo.get("originCwd"), wt) if x]
    en_su_carpeta = any(cur_pwd == x or cur_pwd.startswith(x.rstrip(os.sep) + os.sep) for x in suyas)

    if lateral and not lineage_detached:
        modo = "hija"
        motivo = "sesión lateral"
    elif lateral and lineage_detached and not carpeta_propia and not arranco:
        modo = "hija"
        motivo = "independizada en carpeta compartida"
    else:
        modo = "normal"
        if not lateral:
            motivo = "sesión principal"
        elif carpeta_propia:
            motivo = "carpeta propia (worktree)"
        elif arranco:
            motivo = "arrancó con /arrancar"
        else:
            motivo = "sesión normal"

    return {
        "modo": modo,
        "motivo": motivo,
        "sesion": yo.get("sessionId"),
        "cli": cli_id,
        "titulo": yo.get("title"),
        "nombre": nombre,
        "padre": padre_id,
        "padre_titulo": padre_titulo,
        "padre_vivo": padre_vivo,
        "carpeta": carpeta,
        "en_su_carpeta": en_su_carpeta,
        "cwd": yo.get("cwd") or os.getcwd(),
        "notas_dir": notas_dir,
    }


# ---------------- 2) foto ----------------


def foto(repos):
    det = detectar()
    cli = det.get("cli") or ed.sid_actual() or "sesion"
    ahora = time.time()
    reg = ed._registro(ahora)

    foto_datos = {"hora": ahora, "repos": {}}
    lineas = []

    for r in repos:
        repo_abs = os.path.abspath(r)
        # 1. commits sin subir en ramas con upstream
        ramas_out = _g(repo_abs, "for-each-ref", "--format=%(refname:short)|%(upstream:short)", "refs/heads")
        commits_repo = {}
        total_commits = 0
        if ramas_out:
            for l in ramas_out.splitlines():
                if not l.strip() or "|" not in l:
                    continue
                branch, upstream = l.strip().split("|", 1)
                if upstream:
                    revs = _g(repo_abs, "rev-list", f"{upstream}..{branch}")
                    if revs:
                        shas = [c.strip() for c in revs.splitlines() if c.strip()]
                        if shas:
                            commits_repo[branch] = shas
                            total_commits += len(shas)

        # 2. cambios sin guardar de otras sesiones
        cambios = _parse_status_z(_status(repo_abs))
        archivos_ajenos = {}

        for _, rel_p in cambios:
            abs_p = os.path.join(repo_abs, rel_p)
            norm_p = ed._norm(abs_p)
            en_mi_reg = bool(cli and cli in reg.get(norm_p, {}))
            clas_val = ed.clasificar([abs_p], cli, ahora=ahora).get(abs_p, ("mio", ""))[0]
            if clas_val == "ajeno" or not en_mi_reg:
                if not os.path.exists(abs_p):
                    h = "borrado"
                else:
                    h = _g(repo_abs, "hash-object", "--", abs_p)
                archivos_ajenos[rel_p] = h

        # 3. REANUDAR.md (raíz o .claude/prompts): es del hilo principal
        re_h = {r: _g(repo_abs, "hash-object", "--", os.path.join(repo_abs, r))
                for r in REANUDARES if os.path.isfile(os.path.join(repo_abs, r))}

        foto_datos["repos"][repo_abs] = {
            "commits": commits_repo,
            "archivos": archivos_ajenos,
            "reanudar": re_h,
        }
        lineas.append(
            f"✓ Foto de lo ajeno: {total_commits} commit(s) sin subir y "
            f"{len(archivos_ajenos)} archivo(s) sin guardar de otras sesiones en {r}"
        )

    ruta_foto = os.path.join(_estado_dir(), f"{cli}-foto.json")
    _escribir_estado(ruta_foto, json.dumps(foto_datos, indent=2, ensure_ascii=False))
    return True, lineas


# ---------------- 3) comparar ----------------


def comparar():
    det = detectar()
    cli = det.get("cli") or ed.sid_actual() or "sesion"
    ruta_foto = os.path.join(_estado_dir(), f"{cli}-foto.json")
    if not os.path.isfile(ruta_foto):
        return False, ["✗ No hay foto de lo ajeno: corré sesion_hija.py foto <repo> al EMPEZAR el cierre"]

    try:
        with open(ruta_foto, encoding="utf-8") as f:
            foto_datos = json.load(f)
    except Exception:
        return False, ["✗ No se pudo leer la foto de lo ajeno"]

    foto_hora = foto_datos.get("hora", 0)
    ahora = time.time()
    reg = ed._registro(ahora)

    ok = True
    lineas = []

    for repo_abs, d in foto_datos.get("repos", {}).items():
        # Commits
        for rama, shas in d.get("commits", {}).items():
            for sha in shas:
                if _g(repo_abs, "merge-base", "--is-ancestor", sha, rama) is not None:
                    lineas.append(f"✓ El commit ajeno {sha[:7]} sigue en {rama}")
                elif _mismo_cambio_sigue(repo_abs, sha, rama):
                    lineas.append(f"• El commit ajeno {sha[:7]} de {rama} cambió de huella pero su cambio sigue (lo reacomodó su dueña al subir)")
                else:
                    ok = False
                    lineas.append(f"✗ El commit ajeno {sha[:7]} de {rama} ya no está (¿pull --rebase / reset en la carpeta compartida?)")

        # Archivos ajenos
        for rel_p, old_h in d.get("archivos", {}).items():
            abs_p = os.path.join(repo_abs, rel_p)
            cur_h = _g(repo_abs, "hash-object", "--", abs_p) if os.path.exists(abs_p) else "borrado"
            if cur_h == old_h:
                lineas.append(f"✓ Archivo ajeno {rel_p} sin cambios")
            else:
                norm_p = ed._norm(abs_p)
                due = reg.get(norm_p, {})
                otras_despues = any(s != cli and t > (foto_hora - 1.0) for s, (t, _) in due.items())
                if otras_despues:
                    lineas.append(f"• Archivo ajeno {rel_p} modificado por otra sesión tras la foto")
                else:
                    ok = False
                    lineas.append(f"✗ El archivo ajeno {rel_p} cambió (¿se modificó sin registrar?)")

        # REANUDAR.md (raíz o .claude/prompts)
        viejos = d.get("reanudar") or {}
        if isinstance(viejos, str):  # foto de una versión anterior: solo .claude/prompts
            viejos = {REANUDARES[0]: viejos}
        for rel_re, old_re in viejos.items():
            re_path = os.path.join(repo_abs, rel_re)
            cur_re = _g(repo_abs, "hash-object", "--", re_path) if os.path.isfile(re_path) else None
            if cur_re == old_re:
                lineas.append(f"✓ {rel_re} sin cambios (es del hilo principal)")
                continue
            due = reg.get(ed._norm(os.path.abspath(re_path)), {})
            if any(x != cli and t > (foto_hora - 1.0) for x, (t, _) in due.items()):
                lineas.append(f"• {rel_re} lo cambió otra sesión después de la foto")
            else:
                ok = False
                lineas.append(f"✗ {rel_re} cambió y no es tuyo: es del hilo principal (dejalo como estaba)")

    return ok, lineas


def _patch_ids(repo, *revs_args):
    """{patch-id: sha} de los commits que da `git log -p <revs_args>`, en una sola tubería."""
    try:
        log = subprocess.run(["git", "-c", "core.fsmonitor=false", "-C", repo, "log", "-p", "--no-color", "--no-merges", *revs_args],
                             capture_output=True, timeout=60).stdout
        r = subprocess.run(["git", "-C", repo, "patch-id", "--stable"], input=log, capture_output=True, timeout=60).stdout
    except Exception:
        return {}
    return {l.split()[0]: l.split()[1] for l in r.decode("utf-8", "replace").splitlines() if len(l.split()) == 2}


def _mismo_cambio_sigue(repo, sha, rama):
    """El commit `sha` ya no es ancestro de `rama`, pero su mismo cambio (patch-id) está en `rama` o en su remoto:
    la sesión dueña lo reacomodó al subir (pull --rebase propio). No es algo que haya roto esta hija."""
    buscado = list(_patch_ids(repo, "-1", sha))
    if not buscado:
        return False
    refs = [r for r in (rama, f"origin/{rama}") if _g(repo, "rev-parse", "--verify", "-q", r)]
    return bool(refs) and buscado[0] in _patch_ids(repo, "--max-count=300", *refs)


# ---------------- 4) subir ----------------


def _git_idx(repo, idx_file, *args):
    """git con un índice TEMPORAL propio: arma el commit remoto sin tocar el índice compartido de la carpeta."""
    env = dict(os.environ, GIT_INDEX_FILE=idx_file)
    try:
        r = subprocess.run(["git", "-c", "core.fsmonitor=false", "-c", "core.hooksPath=" + os.devnull, "-C", repo, *args],
                           capture_output=True, text=True, env=env, timeout=60)
    except Exception:
        return None
    return r.stdout.strip() if r.returncode == 0 else None


def _push(repo, sha, ref):
    """Sube un commit a una rama remota, SIN forzar. Con la configuración normal de git (credenciales incluidas)."""
    try:
        r = subprocess.run(["git", "-c", "core.hooksPath=" + os.devnull, "-C", repo, "push", "-q", "origin", f"{sha}:{ref}"],
                           capture_output=True, text=True, timeout=120)
        return r.returncode == 0, (r.stderr or "").strip()[:300]
    except Exception as e:
        return False, type(e).__name__


def _construir_commit_remoto(repo_abs, base, mensaje, archivos, fuente="HEAD"):
    """Commit con `archivos` aplicados sobre `base`, armado en un índice temporal. `fuente` = un commit (se toma su
    contenido) o None (se toma el contenido del disco con hash-object -w, sin tocar el índice compartido). None si falla."""
    tmp_d = tempfile.mkdtemp(prefix="idx-hija-")
    idx_file = os.path.join(tmp_d, "index")
    try:
        if _git_idx(repo_abs, idx_file, "read-tree", base) is None:
            return None
        for rel_f in archivos:
            abs_f = os.path.join(repo_abs, rel_f)
            if fuente:
                ls_out = _g(repo_abs, "ls-tree", fuente, "--", rel_f)
                if ls_out:
                    modo, _tipo, blob = ls_out.split("\t")[0].split()
            else:
                ls_out = os.path.lexists(abs_f) or None
                if ls_out:  # (los enlaces simbólicos se rechazan antes, en subir)
                    modo = "100755" if os.access(abs_f, os.X_OK) else "100644"
                    blob = _g(repo_abs, "hash-object", "-w", "--", abs_f)
            if not ls_out:  # no está: es un borrado
                if _git_idx(repo_abs, idx_file, "update-index", "--force-remove", "--", rel_f) is None:
                    return None
                continue
            # forma de 3 argumentos: una ruta con comas no se confunde con el separador
            if not blob or _git_idx(repo_abs, idx_file, "update-index", "--add", "--cacheinfo", modo, blob, rel_f) is None:
                return None
        tree = _git_idx(repo_abs, idx_file, "write-tree")
        base_commit = _g(repo_abs, "rev-parse", f"{base}^{{commit}}")
        if not tree or not base_commit:
            return None
        return _git_idx(repo_abs, idx_file, "commit-tree", tree, "-p", base_commit, "-m", mensaje)
    finally:
        shutil.rmtree(tmp_d, ignore_errors=True)


def _directo_permitido(repo_abs):
    """Repos donde la norma es empujar a main sin PR. Lista: DIRECTO + <config>/metodo/subir-directo.txt + SUBIR_HIJA_DIRECTO."""
    extra = set()
    try:
        with open(os.path.join(ed.config_dir(), "metodo", "subir-directo.txt"), encoding="utf-8") as fh:
            extra = {l.strip() for l in fh if l.strip() and not l.startswith("#")}
    except OSError:
        pass
    permitidos = DIRECTO | extra | {x.strip() for x in os.environ.get("SUBIR_HIJA_DIRECTO", "").split(",") if x.strip()}
    nombre = _repo_y_dueno(repo_abs)[1]
    return nombre in permitidos, nombre, permitidos


def _blob(repo, ref, ruta):
    return _g(repo, "rev-parse", "-q", "--verify", f"{ref}:{ruta}")


def _otras_sesiones(reg, abs_p, sid):
    """Otras sesiones que editaron este archivo con herramientas de archivo (Edit/Write…)."""
    return [o for o, (_t, h) in reg.get(ed._norm(abs_p), {}).items() if o != sid and h in getattr(ed, "HERRAMIENTAS_ARCHIVO", ())]


def subir(repo, mensaje, rama=None, directo=False, incluir=(), probar=False):
    """Sube SOLO los archivos de esta sesión. Nunca pull/rebase/stash/checkout/reset ni push forzado.
    --directo (solo repos donde la norma es empujar a main): commit local de tus archivos + el mismo cambio sobre lo que
      hay en GitHub; el próximo pull de cualquier sesión descarta solo el commit local (el mismo cambio ya está arriba).
    Sin --directo (rama + PR): NO hay commit local (si no, la próxima subida de main de otra sesión lo llevaría a main sin
      PR). El cambio sale del disco a una rama propia; tus archivos nuevos quedan preparados (git add) para que, cuando se una
      el PR, el pull de cualquier sesión los absorba sin trabarse."""
    repo_abs = os.path.realpath(repo)
    det = detectar()
    sid = det.get("cli") or ed.sid_actual()
    if not sid:
        return 64, ["✗ No sé qué sesión sos (falta CLAUDE_CODE_SESSION_ID): no subo nada"]
    if directo:
        ok_dir, nombre_repo, permitidos = _directo_permitido(repo_abs)
        if not ok_dir:
            return 64, [f"✗ Subida directa a main no permitida en «{nombre_repo}» (solo {', '.join(sorted(permitidos))}): "
                        "repetí sin --directo y se sube a una rama propia para el PR. No toqué nada."]
    ahora = time.time()
    reg = ed._registro(ahora)
    cambios = _parse_status_z(_status(repo_abs))
    nuevos = {p for st, p in cambios if st == "??"}

    # a. Lo propio: lo que el registro anotó para ESTA sesión, + --incluir (si no es de otra sesión)
    propios = []
    for _, rel_p in cambios:
        if sid in reg.get(ed._norm(os.path.join(repo_abs, rel_p)), {}) and rel_p not in propios:
            propios.append(rel_p)
    for inc in incluir:
        abs_inc = os.path.realpath(inc if os.path.isabs(inc) else os.path.join(repo_abs, inc))
        if ed.clasificar([abs_inc], sid, ahora=ahora).get(abs_inc, ("mio", ""))[0] == "ajeno":
            return 3, [f"✗ {inc} es de otra sesión según el registro de ediciones: no se puede incluir"]
        rel_inc = os.path.relpath(abs_inc, repo_abs)
        if rel_inc.startswith(".."):
            return 64, [f"✗ {inc} está fuera del repo {repo_abs}"]
        if rel_inc not in propios:
            propios.append(rel_inc)
    for f in propios:
        if SENSIBLE.search(f):
            return 3, [f"✗ No subo {f}: tiene nombre de archivo de claves (.env, secret, token, password…)"]
        if os.path.islink(os.path.join(repo_abs, f)):
            return 3, [f"✗ No subo {f}: es un enlace simbólico (revisalo a mano)"]
        if os.path.basename(f) == "REANUDAR.md" and det.get("modo") == "hija" and det.get("carpeta") == "compartida":
            return 3, [f"✗ No subo {f}: el REANUDAR.md de una carpeta compartida es del hilo principal"]
        otras = _otras_sesiones(reg, os.path.join(repo_abs, f), sid)
        if otras:
            return 3, [f"✗ {f} también lo editó otra sesión ({', '.join(o[:8] for o in otras)}): juntalo con ella antes de subirlo"]
    if not propios:
        return 0, [f"✓ Nada propio para subir en {repo}"]

    # b. Base remota
    _g(repo_abs, "fetch", "-q", "origin")
    cur_branch = _g(repo_abs, "branch", "--show-current") or "main"
    base_sin_origin = cur_branch if _g(repo_abs, "rev-parse", "--verify", "-q", f"origin/{cur_branch}^{{commit}}") else "main"
    base = f"origin/{base_sin_origin}"
    if not _g(repo_abs, "rev-parse", "--verify", "-q", f"{base}^{{commit}}"):
        return 1, [f"✗ No encuentro {base} en {repo}: ¿el repo tiene remoto?"]

    # c. Conflicto ANTES de tocar nada: lo que hay en GitHub de cada archivo tiene que ser lo mismo de lo que partiste
    antes = _g(repo_abs, "rev-parse", "HEAD")

    def conflicto(base_ref):
        for f in propios:
            if _blob(repo_abs, base_ref, f) != _blob(repo_abs, antes, f):
                return f"✗ {f} cambió en GitHub mientras tanto: hay que juntarlo a mano (no subí nada ni toqué la carpeta)"
        return None

    c = conflicto(base)
    if c:
        return 4, [c]
    destino = base_sin_origin if directo else (rama or f"hija/{det.get('nombre') or 'hija'}-{time.strftime('%Y%m%d')}")
    if probar:
        return 0, [f"• Modo prueba: subiría {len(propios)} archivo(s) a {destino} sobre {base}: {', '.join(propios[:8])}"]

    # d. Solo --directo: commit LOCAL de lo tuyo (--only no se lleva lo que otras sesiones prepararon)
    local_sha = None
    if directo:
        for f in propios:
            if os.path.lexists(os.path.join(repo_abs, f)):
                if _g(repo_abs, "add", "--", f) is None:
                    return 1, [f"✗ No pude preparar {f}"]
            else:
                _g(repo_abs, "rm", "--cached", "-q", "--ignore-unmatch", "--", f)
        if _g(repo_abs, "commit", "-q", "--only", "--no-verify", "-m", mensaje, "--", *propios) is None:
            return 1, ["✗ No pude crear el commit local de tus archivos (¿no hay cambios reales?)"]
        local_sha = _g(repo_abs, "rev-parse", "HEAD")
        if not local_sha or local_sha == antes:
            return 1, ["✗ No se creó el commit local de tus archivos"]

    # e-f. Commit REMOTO sobre la base y subida sin forzar (si alguien subió a main en el medio: una vuelta más)
    R = None
    for vuelta in (1, 2):
        R = _construir_commit_remoto(repo_abs, base, mensaje, propios, fuente=local_sha)
        if not R:
            return 1, ["✗ No pude armar el commit para subir" + (f" (el local {local_sha[:7]} quedó)" if local_sha else " (no toqué nada)")]
        ok, err = _push(repo_abs, R, f"refs/heads/{destino}")
        if ok:
            break
        if not directo:
            return 5, [f"✗ GitHub rechazó la subida a {destino} (¿la rama ya existe con otro contenido? usá --rama): {err}. No toqué nada."]
        _g(repo_abs, "fetch", "-q", "origin")
        c = conflicto(base)
        if c or vuelta == 2:
            return (4 if c else 5), [c or f"✗ GitHub rechazó la subida a {destino}: {err}", f"• El commit local {local_sha[:7]} quedó en {cur_branch}"]
    _g(repo_abs, "fetch", "-q", "origin")
    preparados = []
    if not directo:  # los nuevos quedan preparados: sin esto, el pull de otra sesión se traba al unirse el PR («untracked … would be overwritten»)
        preparados = [f for f in propios if f in nuevos and os.path.lexists(os.path.join(repo_abs, f))]
        if preparados:
            _g(repo_abs, "add", "--", *preparados)

    # g. Registro de la subida (lo lee el traspaso y lo verifica la coordinadora)
    ruta_subidas = os.path.join(_estado_dir(), f"{sid}-subidas.json")
    try:
        lista = json.load(open(ruta_subidas, encoding="utf-8")) if os.path.isfile(ruta_subidas) else []
    except Exception:
        lista = []
    lista.append({"repo": repo_abs, "destino": destino, "sha": R, "local": local_sha, "archivos": propios, "hora": ahora,
                  "via": "directo" if directo else "rama"})
    _escribir_estado(ruta_subidas, json.dumps(lista, indent=2, ensure_ascii=False))
    if directo:
        lineas = [f"✓ Subido {R[:7]} a {destino} con {len(propios)} archivo(s) · tu commit local {local_sha[:7]} lo descarta solo "
                  "el próximo pull de cualquier sesión (el mismo cambio ya está en GitHub)"]
    else:
        dueno, rname = _repo_y_dueno(repo_abs)
        lineas = [f"✓ Subido {R[:7]} a la rama {destino} con {len(propios)} archivo(s), sin commit en la carpeta compartida",
                  f"• Abrí el PR: gh pr create --repo {dueno}/{rname} --head {destino} --base {base_sin_origin} --fill",
                  "• Tus archivos siguen en la carpeta como cambios sin guardar (" + (f"{len(preparados)} nuevo(s) preparados con git add; " if preparados else "")
                  + "cuando se una el PR, el pull de cualquier sesión los absorbe solo)"]
    return 0, lineas


# ---------------- 5) traspaso ----------------


def _validar_borrador(texto):
    lineas = texto.splitlines()
    secciones = {}
    sec_actual = None
    for l in lineas:
        m = re.match(r"^##\s+(.*)$", l)
        if m:
            sec_actual = m.group(1).strip()
            secciones[sec_actual] = []
        elif sec_actual is not None:
            secciones[sec_actual].append(l)

    requeridos = ["Qué se hizo", "Qué sigue", "Pendientes", "Sesiones", "Continuación propuesta"]
    faltan = []

    for req in requeridos:
        if req not in secciones:
            faltan.append(f"falta sección '## {req}'")
        else:
            c = "\n".join(secciones[req]).strip()
            if not c:
                faltan.append(f"la sección '## {req}' está vacía")

    sec_dec = [k for k in secciones if k.startswith("Decisiones de ")]
    if not sec_dec:
        faltan.append("falta sección '## Decisiones de ...'")
    else:
        dec_k = sec_dec[0]
        c_dec = "\n".join(secciones[dec_k]).strip()
        if not c_dec:
            faltan.append(f"la sección '## {dec_k}' está vacía")
        else:
            tiene_cita = bool(re.search(r"«[^»]+»", c_dec))
            tiene_ninguna = bool(re.search(r"\bninguna\b", c_dec, re.IGNORECASE))
            if not (tiene_cita or tiene_ninguna):
                faltan.append(f"la sección '## {dec_k}' debe tener al menos una cita entre «» o la palabra 'ninguna'")

    if faltan:
        return False, "; ".join(faltan)
    return True, ""


def traspaso(borrador_path):
    if not os.path.isfile(borrador_path):
        return False, [f"✗ No se encontró el borrador: {borrador_path}"]

    try:
        with open(borrador_path, encoding="utf-8") as f:
            contenido_borrador = f.read()
    except Exception as e:
        return False, [f"✗ Error al leer borrador: {e}"]

    ok, motivo = _validar_borrador(contenido_borrador)
    if not ok:
        return False, [f"✗ Traspaso incompleto: {motivo}"]

    det = detectar()
    hija_id = det.get("sesion") or "local_desconocida"
    cli_id = det.get("cli") or "cli_desconocido"
    padre_id = det.get("padre") or "coordinadora"
    titulo = det.get("titulo") or ""
    cwd = det.get("cwd") or os.getcwd()
    fecha = time.strftime("%Y-%m-%d")
    carpeta = det.get("carpeta") or "compartida"
    nombre = det.get("nombre") or "hija"

    if nombre == "reanudar":
        nombre = "hija"

    nombre_archivo = f"TRASPASO-{fecha}-{nombre}.md"
    if nombre_archivo == "REANUDAR.md":
        return False, ["✗ El archivo de traspaso nunca puede llamarse REANUDAR.md"]

    # Subidas
    ruta_subidas = os.path.join(_estado_dir(), f"{cli_id}-subidas.json")
    subidas = []
    if os.path.isfile(ruta_subidas):
        try:
            with open(ruta_subidas, encoding="utf-8") as f:
                subidas = json.load(f)
        except Exception:
            subidas = []

    # PRs de la sesión
    ses = hs.cargar()
    yo = next((s for s in ses if s.get("sessionId") == hija_id), None)
    prs = yo.get("prs", []) if yo else []

    header = f"<!-- traspaso de hija · {fecha} · hija {hija_id} · coordinadora {padre_id} · sesion_hija.py -->\n\n"
    meta = {
        "hija": hija_id,
        "cli": cli_id,
        "padre": padre_id,
        "titulo": titulo,
        "cwd": cwd,
        "fecha": fecha,
        "carpeta": carpeta,
        "subidas": subidas,
        "prs": prs,
    }
    bloque_json = "```json\n" + json.dumps(meta, indent=2, ensure_ascii=False) + "\n```\n\n"
    final_str = header + bloque_json + contenido_borrador.strip() + "\n"

    # Rutas
    ruta_cwd = os.path.join(cwd, ".claude", "prompts", nombre_archivo)
    notas_dir = det.get("notas_dir")
    if not notas_dir:
        base_notas = os.environ.get("CLAUDE_NOTAS_DIR") or os.path.join(
            os.path.dirname(_raiz()), "side-session-notes"
        )
        notas_dir = os.path.join(base_notas, padre_id)
    ruta_notas = os.path.join(notas_dir, nombre_archivo)

    os.makedirs(os.path.dirname(ruta_cwd), exist_ok=True)
    os.makedirs(os.path.dirname(ruta_notas), exist_ok=True)

    with open(ruta_cwd, "w", encoding="utf-8") as f:
        f.write(final_str)
    with open(ruta_notas, "w", encoding="utf-8") as f:
        f.write(final_str)

    sha12 = hashlib.sha256(final_str.encode("utf-8")).hexdigest()[:12]
    return True, [f"✓ Traspaso guardado en {ruta_cwd} y {ruta_notas} (sha256: {sha12})"]


def _reanudar_tocado_por(cli, carpeta):
    """Qué REANUDAR.md de `carpeta` anotó el registro de ediciones para la sesión `cli`."""
    if not cli:
        return []
    reg = ed._registro(time.time())
    return [r for r in REANUDARES if cli in reg.get(ed._norm(os.path.join(carpeta, r)), {})]


def _sin_subir_de(cli, carpeta):
    """Archivos que la sesión `cli` editó dentro de `carpeta` (registro de ediciones), que siguen con cambios sin guardar
    y cuyo contenido NO es el que hay en GitHub (origin de la rama actual, o origin/main). Lista de textos en criollo."""
    if not cli or not os.path.isdir(carpeta):
        return []
    reg = ed._registro(time.time())
    out, por_repo = [], {}
    raiz = ed._norm(carpeta)
    for ruta, sesiones in reg.items():
        if cli in sesiones and (ruta == raiz or ruta.startswith(raiz.rstrip(os.sep) + os.sep)):
            top = _g(ruta if os.path.isdir(ruta) else os.path.dirname(ruta), "rev-parse", "--show-toplevel")
            if top:
                por_repo.setdefault(top, []).append(ruta)
    for top, rutas in por_repo.items():
        sucios = {ed._norm(os.path.join(top, r)): r for _, r in _parse_status_z(_status(top))}
        rama = _g(top, "branch", "--show-current") or "main"
        base = f"origin/{rama}" if _g(top, "rev-parse", "--verify", "-q", f"origin/{rama}^{{commit}}") else "origin/main"
        for ruta in rutas:
            rel = sucios.get(ruta)
            if rel is None:
                continue  # sin cambios sin guardar: está en la rama (lo mide la parte de ramas)
            abs_f = os.path.join(top, rel)
            actual = _g(top, "hash-object", "--", abs_f) if os.path.exists(abs_f) else None
            if actual != _blob(top, base, rel):
                out.append(f"{rel} en {top} (cambios sin guardar que no están en GitHub)")
    return out


def _commits_locales_de(cli, carpeta):
    """Commits de la rama actual de `carpeta` que no están en GitHub (ni como el mismo cambio con otra huella) y que tocan
    archivos que la sesión `cli` editó: trabajo de la hija guardado pero no subido. Textos en criollo."""
    top = _g(carpeta, "rev-parse", "--show-toplevel") if cli and os.path.isdir(carpeta) else None
    if not top or not _g(top, "rev-parse", "--verify", "-q", "@{u}"):
        return []
    mios = {r for r, ses in ed._registro(time.time()).items() if cli in ses}
    out = []
    for sha in (_g(top, "rev-list", "--cherry-pick", "--right-only", "--no-merges", "@{u}...HEAD") or "").split():
        archivos = (_g(top, "show", "--name-only", "--format=", sha) or "").splitlines()
        suyos = [a for a in archivos if a and ed._norm(os.path.join(top, a)) in mios]
        if suyos:
            out.append(f"commit local {sha[:7]} con {', '.join(suyos[:3])} que no está en GitHub ({top})")
    return out


def chequeo_cierre(carpeta=None):
    """Lo que cerrar-check mide en MODO HIJA: [(True|False|None, texto)] (None = aviso «•»).
    Traspaso presente y sellado (copia idéntica en notas), REANUDAR.md ajeno intacto, foto de lo ajeno sin cambios,
    lo subido está en GitHub y no quedó nada tuyo sin subir."""
    det = detectar()
    carpeta = carpeta or det.get("cwd") or os.getcwd()
    cli, nombre = det.get("cli"), det.get("nombre") or "hija"
    res = []
    prompts = os.path.join(carpeta, ".claude", "prompts")
    trasp = sorted(glob.glob(os.path.join(glob.escape(prompts), f"TRASPASO-*-{glob.escape(nombre)}.md")))
    if not trasp:
        res.append((False, f"Falta el traspaso para la coordinadora: sesion_hija.py traspaso --borrador <archivo> (paso 5 de cerrar-hija)"))
    else:
        ultimo = trasp[-1]
        copia = os.path.join(det.get("notas_dir") or "", os.path.basename(ultimo))
        try:
            igual = os.path.isfile(copia) and open(ultimo, "rb").read() == open(copia, "rb").read()
        except OSError:
            igual = False
        res.append((True, f"Traspaso presente: {ultimo}"))
        res.append((igual, "Copia del traspaso en la carpeta de notas del grupo: idéntica" if igual
                    else f"La copia del traspaso en la carpeta de notas falta o difiere ({copia}): repetí sesion_hija.py traspaso"))
    if det.get("carpeta") == "compartida":
        t = _reanudar_tocado_por(cli, carpeta)
        res.append((not t, "No tocaste el REANUDAR.md de la carpeta (es del hilo principal)" if not t
                    else f"Editaste {', '.join(t)} de la carpeta compartida: es del hilo principal, devolvelo a como estaba"))
    ok, lineas = comparar()
    for l in lineas:
        if l.startswith("✗"):
            res.append((False, l[2:]))
        elif l.startswith("•"):
            res.append((None, l[2:]))
    if ok:
        res.append((True, "Foto de lo ajeno: nada de otras sesiones cambió por esta (commits y archivos intactos)"))
    ruta_sub = os.path.join(_estado_dir(), f"{cli}-subidas.json")
    try:
        subidas = json.load(open(ruta_sub, encoding="utf-8")) if os.path.isfile(ruta_sub) else []
    except Exception:
        subidas = []
    for sub in subidas:
        en = _g(sub["repo"], "merge-base", "--is-ancestor", sub["sha"], f"origin/{sub['destino']}") is not None
        res.append((en, f"Subido {sub['sha'][:7]} a {sub['destino']} ({len(sub.get('archivos', []))} archivo(s))" if en
                    else f"{sub['sha'][:7]} no está en origin/{sub['destino']} (¿falló la subida?)"))
    for falta in _sin_subir_de(cli, carpeta):
        res.append((False, f"Tuyo sin subir: {falta} → sesion_hija.py subir <repo> -m \"…\""))
    for falta in _commits_locales_de(cli, carpeta):
        res.append((False, f"Tuyo sin subir: {falta} → subilo con sesion_hija.py subir (o pedile a la coordinadora que lo suba)"))
    return res


# ---------------- 6) recibir ----------------


def recibir(sid_hija):
    ses = hs.cargar()
    hija = next((s for s in ses if s.get("sessionId") == sid_hija), None)
    if not hija:
        return False, [f"✗ No se encontró la sesión {sid_hija}"]

    sf = hija.get("spawnedFrom")
    nombre = _limpiar_nombre(str(sf.get("name")) if isinstance(sf, dict) and sf.get("name") else hija.get("title", ""))
    if nombre == "reanudar":
        nombre = "hija"

    lineas = []
    ok = True

    # a. Traspaso
    hija_cwd = hija.get("cwd") or os.getcwd()
    prompts_dir = os.path.join(hija_cwd, ".claude", "prompts")
    patron_trasp = os.path.join(glob.escape(prompts_dir), f"TRASPASO-*-{glob.escape(nombre)}.md")
    encontrados = sorted(glob.glob(patron_trasp))

    meta_json = {}
    if not encontrados:
        ok = False
        lineas.append(f"✗ Falta el archivo de traspaso en {prompts_dir}")
    else:
        ruta_cwd = encontrados[-1]
        archivo_nombre = os.path.basename(ruta_cwd)
        padre_id = hs.padre_de(hija)
        base_notas = os.environ.get("CLAUDE_NOTAS_DIR") or os.path.join(
            os.path.dirname(_raiz()), "side-session-notes"
        )
        ruta_notas = os.path.join(base_notas, padre_id or "", archivo_nombre)

        if not os.path.isfile(ruta_notas):
            ok = False
            lineas.append(f"✗ Falta la copia del traspaso en notas_dir ({ruta_notas})")
        else:
            try:
                c1 = open(ruta_cwd, "rb").read()
                c2 = open(ruta_notas, "rb").read()
                sha_c1 = hashlib.sha256(c1).hexdigest()
                sha_c2 = hashlib.sha256(c2).hexdigest()
                if sha_c1 != sha_c2:
                    ok = False
                    lineas.append("✗ Las dos copias del traspaso difieren (sha256 no coincide)")
                else:
                    texto_t = c1.decode("utf-8", errors="replace")
                    m_json = re.search(r"```json\s*\n(.*?)\n```", texto_t, re.DOTALL)
                    if m_json:
                        try:
                            meta_json = json.loads(m_json.group(1))
                        except Exception:
                            meta_json = {}
                        borrador_t = texto_t[m_json.end():].strip()
                    else:
                        borrador_t = texto_t.strip()
                    val_ok, val_mot = _validar_borrador(borrador_t)
                    if not val_ok:
                        ok = False
                        lineas.append(f"✗ Traspaso incompleto: {val_mot}")
                    else:
                        lineas.append(f"✓ Traspaso completo y verificado: {archivo_nombre}")
            except Exception as e:
                ok = False
                lineas.append(f"✗ Error al verificar copias de traspaso: {e}")

    # b. Subidas
    subidas = meta_json.get("subidas", [])
    for sub in subidas:
        repo = sub.get("repo")
        sha = sub.get("sha")
        destino = sub.get("destino")
        if repo and sha and destino:
            _g(repo, "fetch", "-q", "origin")
            is_anc = _g(repo, "merge-base", "--is-ancestor", sha, f"origin/{destino}")
            if is_anc is not None:
                lineas.append(f"✓ Commit {sha[:7]} subido a origin/{destino}")
            else:
                ok = False
                lineas.append(f"✗ Commit {sha[:7]} no está en GitHub (origin/{destino})")

    # c. Trabajo pendiente bloqueante. En carpeta compartida, los commits sin subir de la rama compartida pueden ser de
    # cualquier sesión (o la copia local de lo que la hija ya subió): no se le cuentan; se mide lo suyo en (c2).
    wt = hija.get("worktreePath")
    cur_pwd = os.path.realpath(hija_cwd)
    carpeta_propia = bool(wt) and (cur_pwd == os.path.realpath(wt) or cur_pwd.startswith(os.path.realpath(wt) + os.sep))
    top = _g(hija_cwd, "rev-parse", "--show-toplevel") if os.path.isdir(hija_cwd) else None
    rama_compartida = _g(hija_cwd, "branch", "--show-current") if top else None
    trab = _bloqueos(hija, ses)
    bloqueos = [t for k, t in trab if not (
        not carpeta_propia and k == "sin_subir" and rama_compartida and f"en {rama_compartida} sin subir" in t)]
    for d in hs.hijas_de(hija["sessionId"], ses):
        for k, t in _bloqueos(d, ses):
            bloqueos.append(f"descendiente «{d.get('title', '')}»: {t}")

    if bloqueos:
        ok = False
        for b in bloqueos:
            lineas.append(f"✗ Trabajo pendiente: {b}")
    else:
        lineas.append("✓ Sin trabajo pendiente bloqueante (hijas, informes, ramas)")
    # c2. Archivos que la hija editó y siguen distintos de lo que hay en GitHub (se perderían de vista al archivarla)
    for falta in _sin_subir_de(hija.get("cliSessionId"), hija_cwd) + _commits_locales_de(hija.get("cliSessionId"), hija_cwd):
        ok = False
        lineas.append(f"✗ Sin subir: {falta}")

    # d. Carpeta compartida: el REANUDAR.md (raíz o .claude/prompts) es del hilo principal y la hija no lo tocó
    if not carpeta_propia:
        tocados = _reanudar_tocado_por(hija.get("cliSessionId"), hija_cwd)
        if tocados:
            ok = False
            lineas.append(f"✗ La hija editó {', '.join(tocados)} de la carpeta compartida (es del hilo principal: revisá su cambio)")
        else:
            lineas.append("✓ El REANUDAR.md de la carpeta compartida no lo tocó la hija")

    # e. Independizadas
    for s in ses:
        if hs.padre_de(s) == hija["sessionId"] and s.get("lineageDetached"):
            lineas.append(f"• Independizada: «{s.get('title', '')}» ({s.get('sessionId')}): decidí si la adoptás")

    # f. PRs de la hija
    for p in hija.get("prs") or []:
        if isinstance(p, dict) and str(p.get("state", "")).upper() in ("OPEN", "DRAFT"):
            u = p.get("url") or p.get("prNumber") or ""
            lineas.append(f"• PR abierto: {u}")

    # Veredicto
    if ok:
        lineas.append(f"Hija lista para archivar ✓ → archive_session(\"{hija['sessionId']}\")")
    else:
        lineas.append("Falta: resolver los puntos marcados con ✗ antes de archivar ✗")

    return ok, lineas


# ---------------- CLI ----------------


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # Windows: la consola en cp1252 no puede escribir ✓/✗
    parser = argparse.ArgumentParser(description="sesion_hija — mecánica de cierre de sesión hija")
    subparsers = parser.add_subparsers(dest="subcomando")

    # detectar
    p_det = subparsers.add_parser("detectar")
    p_det.add_argument("--json", action="store_true", dest="como_json")

    # foto
    p_foto = subparsers.add_parser("foto")
    p_foto.add_argument("repos", nargs="+")

    # comparar
    subparsers.add_parser("comparar")

    # subir
    p_sub = subparsers.add_parser("subir")
    p_sub.add_argument("repo")
    p_sub.add_argument("-m", "--mensaje", required=True)
    p_sub.add_argument("--rama")
    p_sub.add_argument("--directo", action="store_true")
    p_sub.add_argument("--incluir", action="append", default=[])
    p_sub.add_argument("--probar", action="store_true")

    # traspaso
    p_trasp = subparsers.add_parser("traspaso")
    p_trasp.add_argument("--borrador", required=True)

    # recibir
    p_rec = subparsers.add_parser("recibir")
    p_rec.add_argument("id_hija")
    p_rec.add_argument("--json", action="store_true", dest="como_json")

    args = parser.parse_args()

    if args.subcomando == "detectar":
        d = detectar()
        if args.como_json:
            print(json.dumps(d, ensure_ascii=False))
        else:
            if d["modo"] == "hija":
                print(
                    f"MODO HIJA · carpeta {d['carpeta']} · coordinadora «{d.get('padre_titulo') or '?'}» "
                    f"({d.get('padre')}) · notas: {d.get('notas_dir')}"
                )
            else:
                print(f"MODO NORMAL · {d['motivo']}")
        sys.exit(0)

    elif args.subcomando == "foto":
        ok, lineas = foto(args.repos)
        for l in lineas:
            print(l)
        sys.exit(0 if ok else 1)

    elif args.subcomando == "comparar":
        ok, lineas = comparar()
        for l in lineas:
            print(l)
        sys.exit(0 if ok else 1)

    elif args.subcomando == "subir":
        codigo, lineas = subir(
            args.repo,
            args.mensaje,
            rama=args.rama,
            directo=args.directo,
            incluir=args.incluir,
            probar=args.probar,
        )
        for l in lineas:
            print(l)
        sys.exit(codigo)

    elif args.subcomando == "traspaso":
        ok, lineas = traspaso(args.borrador)
        for l in lineas:
            print(l)
        sys.exit(0 if ok else 1)

    elif args.subcomando == "recibir":
        ok, lineas = recibir(args.id_hija)
        if args.como_json:
            print(json.dumps({"ok": ok, "lineas": lineas}, ensure_ascii=False))
        else:
            for l in lineas:
                print(l)
        sys.exit(0 if ok else 1)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
