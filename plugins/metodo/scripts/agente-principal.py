#!/usr/bin/env python3
"""agente-principal.py — hace que la sesión principal de UNA carpeta arranque COMO su jefe de proyecto (PM).

Qué hace (ajuste oficial `"agent": "<nombre>"` de Claude Code):
  1. Busca `<carpeta>/.claude/agents/pm-*.md`. Si hay exactamente uno, pone `"agent": "<nombre del PM>"` en
     `<carpeta>/.claude/settings.local.json` (el archivo PERSONAL de la carpeta: no se versiona ni viaja a otras
     computadoras, y no pisa `.claude/settings.json`, que el kit puede versionar). Fusiona sin perder claves.
  2. Si el PM trae una lista `tools:` de una línea sin `Agent`, se la suma (un agente principal solo delega con
     `Agent`). Si la lista tiene otra forma y no trae `Agent`, no lo activa: un PM que no puede delegar no sirve.
  3. 0 PM o varios PM → no hace nada y lo dice. Si ya hay un `agent` elegido (por la persona o por otro), lo respeta.
  4. Nunca actúa en una copia de trabajo (git worktree = sesión hija) ni en la carpeta personal (`~`).
  5. Carpeta ajena (un repo bajado de internet): no activa solo un PM cuya cabecera trae algo fuera de la lista
     blanca (hooks, servidores, permisos, primer mensaje, memoria…), ni con un `name:` raro, ni si `.claude`, la
     carpeta de agentes, el PM, el archivo de ajustes o `.git/info/exclude` son enlaces que apuntan afuera.

Por qué `settings.local.json` y no `settings.json` (medido 2026-11-11 con sesiones reales; receta `arneses` E2):
  • `settings.json` versionado → las copias de trabajo lo traen y todas las hijas arrancan como PM.
  • `settings.local.json` en la raíz de un repo → Claude Code lo lee desde la raíz del repo en toda copia de trabajo
    y subcarpeta, así que en una carpeta que ES la raíz también lo heredan las hijas. Por eso el modo `--hook`
    le suma a toda copia de trabajo que heredó un PM una línea: «sos hija, ejecutá vos lo que te asignaron».
  • En una SUBCARPETA de un repo se escribe en la subcarpeta: hoy Claude Code también lo lee de ahí (la ubicación
    anterior a 2.1.211). Si eso cambia, el ajuste deja de verse sin romper nada: es una fila de «si cambia» de E2.
  • Es el archivo personal y no choca con el `settings.json` versionado del kit.

Uso (siempre termina con «Todo al día ✓», «Sin cambios ✓ …» o «Falta: … ✗»):
  agente-principal.py [--carpeta X]            aplica en X (por defecto, la carpeta actual)
  agente-principal.py --simular                muestra qué haría, sin escribir nada
  agente-principal.py --deshacer               lo saca y deja anotado que esa carpeta NO lo quiere (no se vuelve a aplicar)
  agente-principal.py --hook                   modo del hook SessionStart: lee el JSON de Claude por stdin, solo habla si
                                               cambió algo (una vez), nunca falla ni demora la sesión (tope 3,5 s)

Disparador: automático (hook SessionStart de metodo, solo al abrir una sesión nueva) + por intención («sacá el jefe de
proyecto de esta carpeta» → `--deshacer`). Apagar todo: crear `<config de Claude>/metodo/agente-principal.apagado` o
`AGENTE_PRINCIPAL_OFF=1`. Copias previas y registro: `<config de Claude>/metodo/agente-principal*`.
Compatible con Windows (UTF-8, rutas con «/», sin depender de fechas de carpetas) y Python 3.9.
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

for _flujo in (sys.stdin, sys.stdout, sys.stderr):
    try:
        _flujo.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ARCHIVO_AJUSTES = "settings.local.json"
PATRON_EXCLUDE = "**/.claude/settings.local.json"
NOMBRE_VALIDO = re.compile(r"^pm-[a-z0-9][a-z0-9-]{0,62}$")
# Lista BLANCA de campos de la cabecera de un PM que se activa solo. Todo lo demás (hooks, mcpServers, permissionMode,
# initialPrompt, background, isolation, memory, …) puede ejecutar cosas, cambiar permisos o dejar recuerdos en otros
# proyectos cuando el agente corre como sesión principal.
CAMPOS_PERMITIDOS = ("name", "description", "model", "tools", "disallowedTools", "skills", "color", "effort")
TOPE_HOOK = 3.5   # segundos; el hook tiene 5 en hooks.json


class Problema(Exception):
    """Algo que impide terminar: se informa con «Falta: … ✗» (o silencio, en el hook)."""


class GitLento(Exception):
    """git no contestó a tiempo: en el hook se calla (nunca se adivina si es una copia de trabajo)."""


_LIMITE = [None]   # hora (monotonic) en que se acaba el tiempo del hook; None = sin tope


# ───────────────────────── rutas y archivos ─────────────────────────
def config_dir():
    return os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude")


def _dir_metodo():
    return os.path.join(config_dir(), "metodo")


def _real(p):
    return os.path.realpath(p)


def _barra(p):
    return p.replace("\\", "/")


def clave(carpeta):
    """Identificador estable de una carpeta (sin barras invertidas ni mayúsculas en Windows)."""
    return _barra(os.path.normcase(_real(carpeta)))


def _adentro(ruta, base):
    """True si `ruta` no es un enlace simbólico y su ruta real queda dentro de `base` (o es `base`)."""
    if os.path.islink(ruta):
        return False
    r, b = os.path.normcase(_real(ruta)), os.path.normcase(_real(base))
    return r == b or r.startswith(b.rstrip("/\\") + os.sep)


def leer_texto(ruta):
    """Texto UTF-8 (con o sin BOM). Un archivo que no es UTF-8 → Problema (nunca un error crudo)."""
    try:
        with open(ruta, "rb") as f:
            return f.read().decode("utf-8-sig")
    except UnicodeDecodeError:
        raise Problema("%s no está en UTF-8: no lo toco" % _barra(ruta))


def escribir_texto(ruta, texto):
    """Escritura atómica: archivo temporal en la misma carpeta y reemplazo; conserva los permisos del original."""
    d = os.path.dirname(ruta)
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".ap-", suffix=".tmp", dir=d)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(texto.encode("utf-8"))
        if os.path.exists(ruta):
            shutil.copymode(ruta, tmp)
        else:
            os.chmod(tmp, 0o600)
        os.replace(tmp, ruta)
    except Exception:
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise


def leer_json(ruta):
    """(dict, None) | (None, motivo). Archivo vacío = {}. Si no es un objeto JSON válido, no se toca."""
    if not os.path.isfile(ruta):
        return {}, None
    try:
        crudo = leer_texto(ruta)
        d = json.loads(crudo) if crudo.strip() else {}
    except (OSError, ValueError, Problema) as e:
        return None, "no se puede leer como JSON (%s)" % type(e).__name__
    if not isinstance(d, dict):
        return None, "no es un objeto JSON"
    return d, None


def escribir_json(ruta, d):
    escribir_texto(ruta, json.dumps(d, indent=2, ensure_ascii=False) + "\n")
    chequeo, _ = leer_json(ruta)   # valida lo escrito
    if chequeo != d:
        raise Problema("lo escrito en %s no coincide" % _barra(ruta))


def hash_texto(t):
    return hashlib.sha256(t.encode("utf-8")).hexdigest()


# ───────────────────────── git (todo opcional) ─────────────────────────
def _git(args, cwd):
    """(código, salida) o (None, '') si no hay git. Nunca pregunta nada ni abre ventanas. `core.fsmonitor=false`: un
    repo ajeno no puede hacer correr su programa de monitoreo. Salida siempre en UTF-8 (Windows usa otra página)."""
    env = dict(os.environ, GIT_OPTIONAL_LOCKS="0", GIT_TERMINAL_PROMPT="0")
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
    tope = 5.0
    if _LIMITE[0] is not None:
        tope = _LIMITE[0] - time.monotonic()
        if tope <= 0:
            raise GitLento()
    try:
        r = subprocess.run(["git", "-c", "core.fsmonitor=false", "-c", "core.quotePath=false", "-C", cwd] + args,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="utf-8", errors="replace",
                           timeout=tope, env=env, creationflags=flags)
        return r.returncode, r.stdout.strip()
    except subprocess.TimeoutExpired:
        raise GitLento()
    except (OSError, subprocess.SubprocessError):
        return None, ""


def info_git(carpeta):
    """{'repo', 'hija', 'raiz', 'raiz_principal', 'git_comun'}.
    hija = copia de trabajo enlazada (git worktree): su .git no es el .git común. Sin git instalado, una carpeta cuyo
    `.git` es un archivo (así marca git una copia de trabajo) igual cuenta como hija."""
    rc, gd = _git(["rev-parse", "--git-dir"], carpeta)
    if rc != 0 or not gd:
        hija = os.path.isfile(os.path.join(carpeta, ".git"))
        return {"repo": False, "hija": hija, "raiz": None, "raiz_principal": None, "git_comun": None}
    _, cd = _git(["rev-parse", "--git-common-dir"], carpeta)
    _, top = _git(["rev-parse", "--show-toplevel"], carpeta)
    gd_r = _real(os.path.join(carpeta, gd))
    cd_r = _real(os.path.join(carpeta, cd or gd))
    hija = os.path.normcase(gd_r) != os.path.normcase(cd_r)
    principal = os.path.dirname(cd_r) if os.path.basename(cd_r) == ".git" else None
    return {"repo": True, "hija": hija, "raiz": _real(top) if top else None, "raiz_principal": principal, "git_comun": cd_r}


def esta_versionado(carpeta, ruta):
    return _git(["ls-files", "--error-unmatch", "--", ruta], carpeta)[0] == 0


def esta_ignorado(carpeta, ruta):
    return _git(["check-ignore", "-q", "--", ruta], carpeta)[0] == 0


def asegurar_ignorado(carpeta, ruta, gi):
    """Si el archivo no está ignorado por git, suma el patrón a .git/info/exclude (local, no se versiona).
    Devuelve True si agregó la línea. Si `exclude` (o su carpeta) es un enlace o queda fuera del .git, no lo toca."""
    if not gi.get("repo") or not gi.get("git_comun") or esta_ignorado(carpeta, ruta):
        return False
    rc, p = _git(["rev-parse", "--git-path", "info/exclude"], carpeta)
    if rc != 0 or not p:
        return False
    destino = os.path.join(carpeta, p)
    for tramo in (destino, os.path.dirname(destino)):
        if os.path.lexists(tramo) and not _adentro(tramo, gi["git_comun"]):
            raise Problema(".git/info/exclude es un enlace que apunta afuera: no lo toco, así que git podría ver %s "
                           "(agregalo a .gitignore)" % ARCHIVO_AJUSTES)
    actual = leer_texto(destino) if os.path.isfile(destino) else ""
    if PATRON_EXCLUDE in actual.splitlines():
        return False
    nuevo = actual + ("" if (not actual or actual.endswith("\n")) else "\n") + PATRON_EXCLUDE + "\n"
    escribir_texto(destino, nuevo)
    return True


# ───────────────────────── el PM de la carpeta ─────────────────────────
def _frontmatter(texto):
    """(índice de línea donde empieza, donde termina, líneas) de la cabecera `---`, o None.
    La cabecera abre y cierra SOLO con una línea exacta `---` (sin sangría): un `  ---` dentro de un texto no la corta."""
    lineas = texto.splitlines(True)
    if not lineas or lineas[0].rstrip("\r\n") != "---":
        return None
    for i in range(1, len(lineas)):
        if lineas[i].rstrip("\r\n") == "---":
            return 1, i, lineas
    return None


def nombre_del_agente(texto, ruta):
    """El `agent` se llama por el campo `name:` de la cabecera; si falta, por el nombre del archivo."""
    fm = _frontmatter(texto)
    if fm:
        a, b, lineas = fm
        for ln in lineas[a:b]:
            m = re.match(r"^name:\s*(.+?)\s*$", ln.rstrip("\r\n"))
            if m:
                v = m.group(1).strip().strip("'\"")
                if v:
                    return v
    return os.path.splitext(os.path.basename(ruta))[0]


def pms_de(carpeta):
    d = os.path.join(carpeta, ".claude", "agents")
    if not os.path.isdir(d):
        return []
    return sorted(os.path.join(d, n) for n in os.listdir(d)
                  if n.startswith("pm-") and n.endswith(".md") and os.path.isfile(os.path.join(d, n)))


def cabecera_rara(texto):
    """Lista de lo que hace que este PM NO se active solo (vacía = cabecera normal)."""
    fm = _frontmatter(texto)
    if not fm:
        return ["no tiene cabecera"]
    a, b, lineas = fm
    raro = []
    for ln in lineas[a:b]:
        s = ln.rstrip("\r\n")
        if not s.strip() or s.lstrip().startswith("#"):
            continue
        if s[0] in " \t" or s.startswith("- "):
            continue   # sigue el valor del campo anterior (texto en varias líneas, lista)
        m = re.match(r"^([A-Za-z_][\w-]*)\s*:", s)
        if not m:
            raro.append("una línea que no es «campo: valor»")
        elif m.group(1) not in CAMPOS_PERMITIDOS:
            raro.append("el campo «%s»" % m.group(1))
    return raro


_LISTA_SIMPLE = re.compile(r"^[A-Za-z0-9_*().:/\-\"' ]+(,[A-Za-z0-9_*().:/\-\"' ]+)*$")


def arreglar_tools(texto):
    """→ (texto nuevo, cambió?, nota, sirve?). `sirve` = False si la lista no trae `Agent` y no se puede arreglar.
    Solo se tocan listas de UNA línea simples (`A, B` o `[A, B]`) o en bloque (`- A`); con comentarios, `>`, `|`, `{`
    o corchetes abiertos no se toca nada."""
    fm = _frontmatter(texto)
    if not fm:
        return texto, False, "sin cabecera", True
    a, b, lineas = fm
    idx = None
    for i in range(a, b):
        if re.match(r"^tools\s*:", lineas[i]):
            idx = i
            break
    if idx is None:
        return texto, False, "hereda todas las herramientas", True
    nl = "\r\n" if lineas[idx].endswith("\r\n") else "\n"
    valor = re.match(r"^tools\s*:\s*(.*?)\s*$", lineas[idx].rstrip("\r\n")).group(1)
    if valor:
        if valor == "*":
            return texto, False, "ya trae Agent", True
        if valor.startswith("[") and valor.endswith("]") and _LISTA_SIMPLE.match(valor[1:-1].strip() or "x"):
            items = [x.strip() for x in valor[1:-1].split(",") if x.strip()]
            forma = "corchetes"
        elif _LISTA_SIMPLE.match(valor) and valor[0] not in "\"'":
            items = [x.strip() for x in valor.split(",") if x.strip()]
            forma = "linea"
        else:
            return texto, False, "su lista de herramientas tiene una forma que no sé corregir", \
                any(re.match(r"^Agent\b", x.strip().strip("\"'")) for x in re.split(r"[,\[\]]", valor.split("#")[0]))
        if any(re.match(r"^Agent\b", x.strip("\"'")) for x in items):
            return texto, False, "ya trae Agent", True
        nuevo = ("[" + ", ".join(items + ["Agent"]) + "]") if forma == "corchetes" else ", ".join(items + ["Agent"])
        lineas[idx] = "tools: " + nuevo + nl
        return "".join(lineas), True, "le faltaba Agent (se suma)", True
    # lista en bloque:   tools:\n  - Read\n  - Grep
    j, ultimo, sangria = idx + 1, None, "  "
    while j < b:
        s = lineas[j].rstrip("\r\n")
        mi = re.match(r"^(\s*)-\s+([A-Za-z0-9_*().:/\-]+)\s*$", s)
        if mi:
            if re.match(r"^Agent\b", mi.group(2)):
                return texto, False, "ya trae Agent", True
            ultimo, sangria = j, mi.group(1)
            j += 1
        elif not s.strip():
            j += 1
        elif re.match(r"^\s*-", s) or s.lstrip().startswith("#"):
            return texto, False, "su lista de herramientas tiene una forma que no sé corregir", False
        else:
            break
    if ultimo is None:
        return texto, False, "su lista de herramientas tiene una forma que no sé corregir", False
    lineas.insert(ultimo + 1, sangria + "- Agent" + nl)
    return "".join(lineas), True, "le faltaba Agent (se suma)", True


def agente_ya_elegido(carpeta, gi):
    """(nombre, archivo) del primer `agent` que ya está elegido en los ajustes que Claude lee para esta carpeta."""
    candidatos = [os.path.join(carpeta, ".claude", "settings.json"),
                  os.path.join(carpeta, ".claude", ARCHIVO_AJUSTES)]
    if gi.get("raiz") and os.path.normcase(gi["raiz"]) != os.path.normcase(_real(carpeta)):
        candidatos.append(os.path.join(gi["raiz"], ".claude", ARCHIVO_AJUSTES))
    candidatos.append(os.path.join(config_dir(), "settings.json"))
    for c in candidatos:
        d, _ = leer_json(c)
        if d and isinstance(d.get("agent"), str) and d["agent"].strip():
            return d["agent"].strip(), c
    return None, None


# ───────────────────────── registro (con candado: varias sesiones abren a la vez) ─────────────────────────
def _ruta_estado():
    return os.path.join(_dir_metodo(), "agente-principal.json")


class Candado:
    """Candado de carpeta (mkdir es atómico en Mac, Linux y Windows). Uno viejo (> 60 s) se considera abandonado."""
    def __init__(self):
        self.ruta = os.path.join(_dir_metodo(), "agente-principal.candado")

    def __enter__(self):
        os.makedirs(_dir_metodo(), exist_ok=True)
        fin = time.monotonic() + 2.0
        if _LIMITE[0] is not None:
            fin = min(fin, _LIMITE[0])
        while True:
            try:
                os.mkdir(self.ruta)
                return self
            except FileExistsError:
                try:
                    if time.time() - os.stat(self.ruta).st_mtime > 60:
                        os.rmdir(self.ruta)
                        continue
                except OSError:
                    pass
                if time.monotonic() > fin:
                    raise Problema("otra sesión está usando el registro; probá de nuevo en un rato")
                time.sleep(0.05)

    def __exit__(self, *exc):
        try:
            os.rmdir(self.ruta)
        except OSError:
            pass
        return False


def leer_estado():
    """El registro; si existe y está roto → Problema (nunca se reinicia en silencio: perdería un «no lo quiero»)."""
    ruta = _ruta_estado()
    if not os.path.exists(ruta):
        return {"carpetas": {}}
    d, motivo = leer_json(ruta)
    if not isinstance(d, dict) or not isinstance(d.get("carpetas", {}), dict):
        raise Problema("el registro %s está roto (%s): no toco nada" % (_barra(ruta), motivo or "formato"))
    d.setdefault("carpetas", {})
    return d


def anotar(k, entrada):
    """Relee el registro bajo candado y guarda SOLO la entrada de esta carpeta (no pisa lo de otra sesión)."""
    with Candado():
        est = leer_estado()
        est["carpetas"][k] = entrada
        escribir_json(_ruta_estado(), est)


def _copia(ruta, k, etiqueta):
    """Copia previa FUERA del proyecto (no ensucia git ni la carpeta), con nombre único: nunca pisa una anterior."""
    d = os.path.join(_dir_metodo(), "agente-principal-copias", hashlib.sha256(k.encode("utf-8")).hexdigest()[:12])
    os.makedirs(d, exist_ok=True)
    sello = datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    destino = os.path.join(d, "%s.%s" % (etiqueta, sello))
    shutil.copyfile(ruta, destino)
    return destino


def _ahora():
    return datetime.datetime.now().replace(microsecond=0).isoformat()


# ───────────────────────── acciones ─────────────────────────
class Resultado:
    def __init__(self):
        self.lineas = []
        self.cambio = False         # escribió algo
        self.cambio_tools = False   # le sumó Agent al PM
        self.error = False
        self.nombre = None
        self.motivo_nada = None

    def d(self, t):
        self.lineas.append(t)


def _chequeos_de_carpeta(carpeta, gi, r):
    """Lo que hace que una carpeta no se toque. Devuelve (ruta del PM, texto, nombre) o None (con r.motivo_nada)."""
    if os.path.normcase(carpeta) == os.path.normcase(_real(os.path.expanduser("~"))):
        r.motivo_nada = "es tu carpeta personal: acá no se elige un jefe de proyecto"
        return None
    if gi["hija"]:
        r.motivo_nada = "es una copia de trabajo (sesión hija): el jefe de proyecto es de la sesión principal"
        return None
    for tramo in (os.path.join(carpeta, ".claude"), os.path.join(carpeta, ".claude", "agents")):
        if os.path.lexists(tramo) and not _adentro(tramo, carpeta):
            r.motivo_nada = "%s es un enlace que apunta afuera de la carpeta: no lo toco" % _barra(os.path.relpath(tramo, carpeta))
            return None
    pms = pms_de(carpeta)
    if not pms:
        r.motivo_nada = "no hay un jefe de proyecto (pm-*.md) en %s/.claude/agents" % _barra(carpeta)
        return None
    if len(pms) > 1:
        r.motivo_nada = ("hay %d jefes de proyecto en .claude/agents: no elijo por vos; poné `\"agent\"` a mano en %s"
                         % (len(pms), ARCHIVO_AJUSTES))
        return None
    pm = pms[0]
    if not _adentro(pm, carpeta):
        r.motivo_nada = "el jefe de proyecto es un enlace que apunta afuera de la carpeta: no lo activo solo"
        return None
    texto = leer_texto(pm)
    nombre = nombre_del_agente(texto, pm)
    if not NOMBRE_VALIDO.fullmatch(nombre):
        r.motivo_nada = "el `name:` de %s no es un nombre simple (pm-letras-números-y-guiones): no lo activo solo" % os.path.basename(pm)
        return None
    raro = cabecera_rara(texto)
    if raro:
        r.motivo_nada = ("la cabecera de %s trae %s (puede ejecutar cosas o cambiar permisos): no lo activo solo; si es tuyo "
                         "y lo querés así, poné `\"agent\": \"%s\"` a mano en %s" % (os.path.basename(pm), ", ".join(raro[:3]), nombre, ARCHIVO_AJUSTES))
        return None
    return pm, texto, nombre


def aplicar(carpeta, simular=False, forzar=False, gi=None):
    r = Resultado()
    if not os.path.isdir(carpeta):
        r.error = True
        r.d("✗ la carpeta no existe: %s" % _barra(carpeta))
        return r
    carpeta = _real(carpeta)
    k = clave(carpeta)
    try:
        gi = gi or info_git(carpeta)
        hallado = _chequeos_de_carpeta(carpeta, gi, r)
        if not hallado:
            return r
        pm, texto_pm, nombre = hallado
        r.nombre = nombre
        previo = leer_estado()["carpetas"].get(k, {})
        if previo.get("estado") == "deshecho" and not forzar:
            r.motivo_nada = "en esta carpeta pediste volver a la sesión normal (se respeta)"
            return r
        elegido, donde = agente_ya_elegido(carpeta, gi)
        destino = os.path.join(carpeta, ".claude", ARCHIVO_AJUSTES)
        if elegido and elegido != nombre:
            r.motivo_nada = "ya hay un agente elegido («%s» en %s): lo respeto" % (elegido, _barra(donde))
            return r
        if os.path.lexists(destino) and not _adentro(destino, carpeta):
            r.motivo_nada = "%s es un enlace que apunta afuera de la carpeta: no lo toco" % ARCHIVO_AJUSTES
            return r
        if gi["repo"] and os.path.exists(destino) and esta_versionado(carpeta, destino):
            r.motivo_nada = "%s está versionado en git: no lo toco" % ARCHIVO_AJUSTES
            return r
        ajustes, motivo = leer_json(destino)
        if ajustes is None:
            raise Problema("%s %s: no lo toco" % (_barra(destino), motivo))
        nuevo_pm, cambia_tools, nota_tools, sirve = arreglar_tools(texto_pm)
        if not sirve:
            r.motivo_nada = ("%s: %s y no trae `Agent` (sin esa herramienta no puede delegar): no lo activo; sacale la lista "
                             "`tools:` o sumale `Agent`" % (os.path.basename(pm), nota_tools))
            return r
        ya = ajustes.get("agent") == nombre or elegido == nombre   # ya arranca así (acá o en otro archivo)
        r.d("%s %s → %s · %s · herramientas: %s" % ("✓" if (ya and not cambia_tools) else "•", _barra(carpeta), nombre,
                                                    "ya está" if ya else "se agrega «agent»", nota_tools))
        if simular:
            return r
        if ya and not cambia_tools:
            if os.path.exists(destino) and asegurar_ignorado(carpeta, destino, gi):   # repara lo que quedó a medias
                r.d("• sumé %s a lo que git no versiona en esta copia" % ARCHIVO_AJUSTES)
            return r
        # Registro antes de cada paso: si algo falla a la mitad, «deshacer» sabe qué hubo.
        entrada = dict(previo) if previo.get("estado") == "aplicado" else {}
        entrada.update({"estado": "aplicado", "agent": nombre, "fecha": _ahora()})
        entrada.setdefault("creado", not os.path.exists(destino))
        anotar(k, entrada)
        if cambia_tools:   # 1) el PM: suma Agent (copia previa afuera del proyecto)
            entrada["pm_tools"] = {"archivo": pm, "copia": _copia(pm, k, os.path.basename(pm) + ".antes"),
                                   "hash_despues": hash_texto(nuevo_pm)}
            anotar(k, entrada)
            escribir_texto(pm, nuevo_pm)
            r.cambio = r.cambio_tools = True
        if not ya:         # 2) los ajustes personales de la carpeta (fusiona sin perder claves)
            if os.path.exists(destino):
                entrada["copia_ajustes"] = _copia(destino, k, ARCHIVO_AJUSTES + ".antes")
            entrada["puso_agent"] = True
            anotar(k, entrada)
            ajustes["agent"] = nombre
            escribir_json(destino, ajustes)
            r.cambio = True
        if asegurar_ignorado(carpeta, destino, gi):   # 3) que git no lo versione
            entrada["exclude"] = True
            anotar(k, entrada)
    except GitLento:
        if not r.cambio:
            raise
        r.error = True   # ya quedó escrito: se avisa igual (el hook lo cuenta) y la próxima vez se repara el resto
        r.d("✗ git no contestó a tiempo; el ajuste quedó puesto pero falta confirmar que git no lo versione")
    except (OSError, ValueError, Problema) as e:
        r.error = True
        r.d("✗ no pude terminar: %s" % e)
    return r


def deshacer(carpeta):
    r = Resultado()
    if not os.path.isdir(carpeta):
        r.error = True
        r.d("✗ la carpeta no existe: %s" % _barra(carpeta))
        return r
    carpeta = _real(carpeta)
    k = clave(carpeta)
    destino = os.path.join(carpeta, ".claude", ARCHIVO_AJUSTES)
    try:
        entrada = leer_estado()["carpetas"].get(k)
        if os.path.lexists(destino) and not _adentro(destino, carpeta):
            raise Problema("%s es un enlace que apunta afuera de la carpeta: no lo toco" % ARCHIVO_AJUSTES)
        if entrada and entrada.get("estado") == "aplicado":
            ajustes, motivo = leer_json(destino)
            if ajustes is None:
                raise Problema("%s %s: no lo toco" % (_barra(destino), motivo))
            if entrada.get("puso_agent") and ajustes.get("agent") == entrada.get("agent"):
                del ajustes["agent"]
                if not ajustes and entrada.get("creado"):
                    os.remove(destino)
                    r.d("↩ borré %s (lo había creado yo y quedó vacío)" % _barra(destino))
                else:
                    escribir_json(destino, ajustes)
                    r.d("↩ saqué «agent» de %s (lo demás quedó igual)" % _barra(destino))
            pt = entrada.get("pm_tools")
            if pt and os.path.isfile(pt["archivo"]):
                if hash_texto(leer_texto(pt["archivo"])) == pt["hash_despues"] and os.path.isfile(pt["copia"]):
                    escribir_texto(pt["archivo"], leer_texto(pt["copia"]))
                    r.d("↩ el jefe de proyecto vuelve a su lista de herramientas anterior")
                else:
                    r.d("• el jefe de proyecto cambió desde entonces: no le toco las herramientas")
        else:
            ajustes, _ = leer_json(destino)
            if ajustes and isinstance(ajustes.get("agent"), str):
                r.d("• «agent» de %s no lo puse yo: no lo saco solo (sacalo de ese archivo si no lo querés)" % _barra(destino))
            else:
                r.d("• no había aplicado nada acá")
            r.d("• queda anotado que esta carpeta no lo quiere: no se vuelve a aplicar solo")
        anotar(k, {"estado": "deshecho", "fecha": _ahora()})
        r.cambio = True
    except (OSError, ValueError, Problema) as e:
        r.error = True
        r.d("✗ no pude deshacer: %s" % e)
        r.d("• a mano: sacá la línea «\"agent\": …» de %s (y, si querés, la línea `Agent` de la lista `tools:` del PM)" % _barra(destino))
    return r


# ───────────────────────── modo hook ─────────────────────────
def _agente_de(ruta):
    d, _ = leer_json(ruta)
    v = d.get("agent") if d else None
    return v if isinstance(v, str) else None


def aviso_hija(carpeta, datos, gi):
    """Línea para una copia de trabajo que heredó un jefe de proyecto: ahí la sesión es hija y ejecuta."""
    if not gi["hija"]:
        return None
    heredado = datos.get("agent_type") if isinstance(datos.get("agent_type"), str) else None
    if not heredado:
        cands = [os.path.join(carpeta, ".claude", "settings.json"), os.path.join(carpeta, ".claude", ARCHIVO_AJUSTES)]
        if gi.get("raiz_principal"):
            cands += [os.path.join(gi["raiz_principal"], ".claude", ARCHIVO_AJUSTES),
                      os.path.join(gi["raiz_principal"], ".claude", "settings.json")]
        for c in cands:
            a = _agente_de(c)
            if a:
                heredado = a
                break
    if not heredado or not NOMBRE_VALIDO.fullmatch(heredado):
        return None
    return ("Aviso de metodo (copia de trabajo): esta sesión es una HIJA: hace ella misma la tarea que le asignaron "
            "(editar, probar, entregar). Si arrancaste como «%s» por heredarlo de la carpeta principal, ese rol es de la "
            "sesión principal: acá los agentes y las skills ayudan, no reemplazan que la hija ejecute." % heredado)


def aviso_aplicado(nombre, cambio_tools):
    """`nombre` ya está validado (NOMBRE_VALIDO). El comando usa `--carpeta .`: ninguna ruta ajena entra al texto."""
    script = _barra(os.path.abspath(__file__))
    if re.search(r"[\"'`$\\;&|<>\n]", script):
        comando = "el programa agente-principal.py de metodo con --deshacer --carpeta ."
    else:
        comando = "python3 \"%s\" --deshacer --carpeta . (en Windows: py -3 en vez de python3)" % script
    extra = " (y a su ficha le sumé la herramienta `Agent`, para que pueda delegar: queda como cambio para guardar)" if cambio_tools else ""
    return ("Aviso de metodo (decíselo a la persona UNA sola vez, en una frase y en criollo, y seguí con lo que te pida): "
            "en esta carpeta, desde la PRÓXIMA sesión, vas a arrancar como «%s», el jefe de proyecto de la carpeta: reparte el "
            "trabajo en agentes y skills en vez de hacerlo todo él%s. Si la persona prefiere la sesión de siempre, que te lo pida "
            "(«sacá el jefe de proyecto de esta carpeta») y lo deshacés vos corriendo, parado en esta carpeta: %s"
            % (nombre, extra, comando))


def modo_hook():
    """Nunca falla ni demora: cualquier problema = silencio."""
    try:
        if os.environ.get("AGENTE_PRINCIPAL_OFF") or os.path.exists(os.path.join(_dir_metodo(), "agente-principal.apagado")):
            return
        datos = {}
        if not sys.stdin.isatty():
            try:
                datos = json.loads(sys.stdin.read() or "{}")
            except ValueError:
                datos = {}
        if not isinstance(datos, dict) or datos.get("source", "startup") != "startup":
            return
        carpeta = datos.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
        if not isinstance(carpeta, str) or not os.path.isdir(carpeta):
            return
        _LIMITE[0] = time.monotonic() + TOPE_HOOK
        carpeta = _real(carpeta)
        gi = info_git(carpeta)
        hija = aviso_hija(carpeta, datos, gi)
        if hija:
            print(hija)
            return
        r = aplicar(carpeta, gi=gi)
        if r.cambio and r.nombre and NOMBRE_VALIDO.fullmatch(r.nombre):
            print(aviso_aplicado(r.nombre, r.cambio_tools))
    except Exception:
        return
    finally:
        _LIMITE[0] = None


# ───────────────────────── línea de comandos ─────────────────────────
def main(argv=None):
    ap = argparse.ArgumentParser(description="La sesión principal de la carpeta arranca como su jefe de proyecto (PM).")
    ap.add_argument("--carpeta", default=None, help="carpeta del proyecto (por defecto, la actual)")
    ap.add_argument("--simular", action="store_true", help="muestra qué haría, sin escribir nada")
    ap.add_argument("--deshacer", action="store_true", help="lo saca y anota que esta carpeta no lo quiere")
    ap.add_argument("--hook", action="store_true", help="modo hook SessionStart (silencioso)")
    a = ap.parse_args(argv)
    if a.hook:
        modo_hook()
        return 0
    carpeta = a.carpeta or os.getcwd()
    try:
        r = deshacer(carpeta) if a.deshacer else aplicar(carpeta, simular=a.simular, forzar=True)
    except GitLento:
        print("Falta: git no contestó a tiempo ✗")
        return 1
    for ln in r.lineas:
        print(ln)
    if r.error:
        print("Falta: revisar lo de arriba ✗")
        return 1
    if r.motivo_nada:
        print("Sin cambios ✓ (%s)" % r.motivo_nada)
        return 0
    print("Solo miré, no cambié nada ✓ (sin --simular lo aplico)" if a.simular else "Todo al día ✓")
    return 0


if __name__ == "__main__":
    sys.exit(main())
