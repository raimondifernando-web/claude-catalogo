#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""claude_api_base — núcleo de claude-api.py (paquete metodo): llave por referencia, límites y gasto POR PERSONA, filtros de
claves y la llamada HTTP a la Messages API. Solo biblioteca estándar (sin SDK, sin pip): anda igual en Mac, Windows y Linux, Python 3.9+.

Disparador: encadenado — lo importa claude-api.py; no se corre solo.

Cada persona usa SU llave y SU crédito. Nada de esto sale de su computadora salvo el pedido a la API.
- Llave: en el almacén de credenciales del sistema, nunca en un archivo ni en el chat:
    macOS   → Llavero (comando /usr/bin/security; al guardar, ES el sistema el que pide la llave oculta, el programa nunca la ve)
    Windows → Administrador de credenciales (credencial genérica «metodo-claude-api», API CredWrite/CredRead de advapi32)
    Linux   → libsecret (comando secret-tool), y si no hay, último recurso: variable de entorno METODO_CLAUDE_API_KEY
  Nunca ANTHROPIC_API_KEY: esa variable la lee Claude Code y cambia con qué cuenta entra (doc oficial, «Authentication»).
- Límites: <config de Claude>/metodo/claude-api.json (crédito de partida, tope por corrida, tope por día). Sin archivo se crea con
  valores conservadores.
- Gasto: <config de Claude>/metodo/claude-api/gasto.jsonl, sin la llave. Antes de llamar se RESERVA el peor caso (con candado), así
  dos sesiones a la vez no pasan juntas el tope; al terminar se anota el gasto real y la reserva se cierra.
Prueba: scripts/tests/test_claude_api_clientes.py (API, almacén y radar falsos; en Windows, también el Administrador de credenciales real).
"""
import contextlib, datetime, getpass, http.client, json, math, os, re, shutil, socket, stat, subprocess, sys, tempfile, time
import unicodedata, urllib.error, urllib.request
from urllib.parse import urlparse

AQUI = os.path.dirname(os.path.realpath(__file__))
if AQUI not in sys.path:
    sys.path.insert(0, AQUI)
import guias          # noqa: E402  (mismas formas de clave que el resto del paquete)
import privacidad     # noqa: E402  (carpetas sensibles y planillas con datos de personas: regla 18)

PROGRAMA = os.path.join(AQUI, "claude-api.py")   # claude-api.py lo pisa con su ruta real
ETIQUETA = "metodo: llave de la API de Claude"
VAR_LLAVE = "METODO_CLAUDE_API_KEY"               # último recurso (Linux sin almacén); nunca ANTHROPIC_API_KEY
API_URL = "https://api.anthropic.com"
API_VERSION = "2026-10-21"
# US$ por millón de tokens (entrada, salida). Precios públicos de Anthropic (platform.claude.com/docs/en/about-claude/pricing,
# verificados 2026-10-29). Si cambian: actualizar acá y en CHANGELOG; un modelo sin precio frena con salida 69.
PRECIOS = {"claude-opus-5-5": (4.0, 20.0), "claude-sonnet-5-5": (2.0, 10.0), "claude-haiku-5-5": (0.10, 0.50)}
PRECIOS_HAIKU_LARGO = (0.50, 2.50)                # Haiku 5.5 con más de 100.000 tokens de entrada
LIMITES_DEF = {"credito_usd": 20.0, "tope_corrida_usd": 5.0, "tope_diario_usd": 20.0}
LIMITES_MAX = {"credito_usd": 100000.0, "tope_corrida_usd": 100.0, "tope_diario_usd": 1000.0}   # solo para frenar un error de tipeo
NOMBRES_LIMITE = {"credito": "credito_usd", "corrida": "tope_corrida_usd", "dia": "tope_diario_usd", "día": "tope_diario_usd"}
TOPE_PEDIDO = 100 * 1024
ESPERAS = [5, 15]
ALIAS = ("haiku", "sonnet", "opus")
ESFUERZOS = ("low", "medium", "high")
ID_MODELO = re.compile(r"^claude-[a-z0-9][a-z0-9.-]{1,60}$")
FORMA_LLAVE = re.compile(r"^sk-ant-(?!admin)[A-Za-z0-9_-]{20,}$")    # nunca una llave de administración de la organización
CLAVE_FORMA = re.compile(r"sk-ant-[A-Za-z0-9_-]{10,}")
CANDADO_VIEJO = 60          # segundos: un candado más viejo quedó de una corrida que murió
CANDADO_ESPERA = 15


class Salida(Exception):
    def __init__(self, codigo, mensaje):
        super().__init__(mensaje)
        self.codigo, self.mensaje = codigo, mensaje


def err(*partes):
    print(*partes, file=sys.stderr)


def usd(x):
    return "US$%.4f" % x


# ---------------------------------------------------------------------------------------------- rutas
def config_claude():
    return os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude")


def modo_prueba():
    """Las variables que cambian dónde están los límites, el gasto o el «no entrenar» valen SOLO en pruebas (con un servidor local):
    así una sesión no puede dejar el gasto en cero ni saltear la privacidad con una variable."""
    return bool(os.environ.get("METODO_CLAUDE_API_URL"))


def _de_prueba(var):
    return os.environ.get(var) if modo_prueba() else None


def casa():
    return _de_prueba("METODO_CLAUDE_API_HOME") or os.path.join(config_claude(), "metodo", "claude-api")


def archivo_limites():
    return _de_prueba("METODO_CLAUDE_API_CONFIG") or os.path.join(config_claude(), "metodo", "claude-api.json")


def norm(p):
    """Ruta comparable en cualquier sistema: barras /, sin barra final, NFC y sin distinguir mayúsculas (macOS y Windows no las distinguen)."""
    return unicodedata.normalize("NFC", str(p)).replace("\\", "/").rstrip("/").casefold()


def rel_dentro(ruta, base):
    """Ruta relativa (con /) si `ruta` está dentro de `base` (o es la misma); None si no. Puro texto: vale para rutas de Windows."""
    r, b = norm(ruta), norm(base)
    if r == b:
        return ""
    if r.startswith(b + "/"):
        return unicodedata.normalize("NFC", str(ruta)).replace("\\", "/")[len(b) + 1:]
    return None


def comando_guardar():
    """El único paso manual, listo para pegar en una terminal (ruta real de este programa y de este Python)."""
    py = sys.executable or ("py" if os.name == "nt" else "python3")
    linea = '"%s" "%s" --guardar-llave' % (py, os.path.realpath(PROGRAMA))
    return "& " + linea if os.name == "nt" else linea     # en PowerShell (la terminal de Windows) una línea que empieza con comillas necesita «&»


# ---------------------------------------------------------------------------------------------- límites por persona
def leer_limites():
    """(límites, creado). Sin archivo: valores por defecto y se crea (creado=True). Archivo roto: frena (no se adivina)."""
    ruta = archivo_limites()
    if not os.path.exists(ruta):
        datos = dict(LIMITES_DEF)
        try:
            escribir_limites(datos)
        except OSError:
            pass
        return datos, True
    try:
        with open(ruta, encoding="utf-8-sig") as f:
            crudo = json.load(f)
        if not isinstance(crudo, dict):
            raise ValueError
    except (OSError, ValueError):
        raise Salida(64, "Falta: el archivo de límites %s está roto; corregilo o borralo (vuelve con los valores por defecto) ✗" % ruta)
    datos = {}
    for k, def_ in LIMITES_DEF.items():
        v = crudo.get(k, def_)
        try:
            v = float(v)
        except (TypeError, ValueError):
            raise Salida(64, "Falta: en %s, «%s» no es un número ✗" % (ruta, k))
        if not (math.isfinite(v) and 0 < v <= LIMITES_MAX[k]):
            raise Salida(64, "Falta: en %s, «%s» tiene que estar entre 0 y %.0f ✗" % (ruta, k, LIMITES_MAX[k]))
        datos[k] = v
    return datos, False


def escribir_limites(datos):
    ruta = archivo_limites()
    carpeta = os.path.dirname(os.path.abspath(ruta))
    os.makedirs(carpeta, exist_ok=True)
    cuerpo = dict(datos)
    cuerpo["_nota"] = ("Límites de claude-api.py (paquete metodo), en dólares. credito_usd = lo que cargaste en tu cuenta de la API desde que "
                       "usás este programa (subilo cuando recargues); tope_corrida_usd = lo más que puede costar una corrida (peor caso); "
                       "tope_diario_usd = lo más por día entre todas las sesiones. Búsquedas web y código no cuentan para los topes, sí para "
                       "el crédito. Cambialos con: claude-api.py --limites corrida=10 dia=40 credito=100")
    fd, tmp = tempfile.mkstemp(prefix=".claude-api.", dir=carpeta)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(cuerpo, f, ensure_ascii=False, indent=2)
            f.write("\n")
        os.replace(tmp, ruta)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def confirmar_en_terminal(texto):
    """Para SUBIR un límite: pide escribir una palabra al azar, leída de la terminal (no de la entrada estándar). Sube la vara para que
    una sesión no lo haga sola; NO es una barrera absoluta (una IA con una terminal de verdad podría escribirla): es una regla de conducta."""
    palabra = "".join(__import__("random").SystemRandom().choice("abcdefghjkmnpqrstuvwxyz") for _ in range(5))
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        return False                     # sin una terminal de verdad no se pregunta (y no se queda colgado esperando)
    try:
        if os.name == "nt":
            ent, sal = open("CONIN$", "r", encoding="utf-8", errors="replace"), open("CONOUT$", "w", encoding="utf-8", errors="replace")
        else:
            ent = sal = open("/dev/tty", "r+", encoding="utf-8", errors="replace")
    except OSError:
        return False
    try:
        sal.write("%s\nPara confirmar que lo decidís vos, escribí «%s» y Enter: " % (texto, palabra))
        sal.flush()
        return ent.readline().strip().lower() == palabra
    finally:
        for f in {ent, sal}:
            try:
                f.close()
            except OSError:
                pass


def cambiar_limites(pedidos, puede_subir):
    """pedidos: ['corrida=10', 'dia=40', ...]. Bajar lo puede cualquiera; SUBIR pide la confirmación de la persona en su terminal
    (puede_subir: True/False o una función que recibe el texto a confirmar y devuelve True si la persona lo confirmó)."""
    actuales, _ = leer_limites()
    nuevos = dict(actuales)
    for p in pedidos:
        nombre, _, valor = p.partition("=")
        k = NOMBRES_LIMITE.get(nombre.strip().lower())
        if not k:
            raise Salida(64, "Falta: «%s» no es un límite; los que hay: corrida, dia, credito (ej.: --limites corrida=10) ✗" % nombre.strip())
        try:
            v = float(valor.strip().replace(",", "."))
        except ValueError:
            raise Salida(64, "Falta: «%s» necesita un número en dólares (ej.: %s=10) ✗" % (nombre.strip(), nombre.strip()))
        if not (math.isfinite(v) and 0 < v <= LIMITES_MAX[k]):
            raise Salida(64, "Falta: «%s» tiene que estar entre 0 y %.0f ✗" % (nombre.strip(), LIMITES_MAX[k]))
        nuevos[k] = v
    sube = [k for k in nuevos if nuevos[k] > actuales[k]]
    if sube:
        texto = "Vas a SUBIR: " + ", ".join("%s de US$%.2f a US$%.2f" % (k, actuales[k], nuevos[k]) for k in sube)
        ok = puede_subir(texto) if callable(puede_subir) else bool(puede_subir)
        if not ok:
            raise Salida(64, "Falta: SUBIR un límite es plata y lo decide la persona: que lo corra ella en su terminal y confirme (bajar sí se puede desde acá) ✗")
    escribir_limites(nuevos)
    return nuevos


# ---------------------------------------------------------------------------------------------- privacidad (regla 18)
def claude_con_no_entrenar():
    """True si la persona registró a Claude con «no entrenar» en <config>/metodo/no-entrena.txt (línea «Claude | fecha | cómo»).
    El programa NUNCA lo registra solo: es una decisión de privacidad de cada persona o empresa."""
    arch = _de_prueba("METODO_NO_ENTRENA") or os.path.join(config_claude(), "metodo", "no-entrena.txt")
    try:
        with open(arch, encoding="utf-8-sig", errors="replace") as f:
            for l in f:
                l = l.strip()
                if l and not l.startswith("#") and l.split("|")[0].strip().casefold().startswith("claude"):
                    return True
    except OSError:
        pass
    return False


def frenar_si_sensible(ruta, que="la carpeta"):
    if claude_con_no_entrenar():
        return
    archivo = _de_prueba("METODO_SENSIBLES") or os.path.join(config_claude(), "metodo", "sensibles.txt")   # la variable, solo en pruebas
    m = privacidad.carpeta_sensible(ruta, lista=privacidad.leer_sensibles(archivo))
    if m:
        raise Salida(65, "Falta: %s «%s» es %s. No se manda a la API mientras Claude no figure con «no entrenar» en tu no-entrena.txt "
                         "(decisión tuya; ver la skill usar-credito-api) ✗" % (que, ruta, m))


def planillas_con_personas(rutas):
    return [] if claude_con_no_entrenar() else privacidad.planillas_con_personas(rutas, raiz="")


def avisar_planillas(rutas):
    m = privacidad.aviso_planillas(planillas_con_personas(rutas))
    if m:
        err(m)


# ---------------------------------------------------------------------------------------------- secretos (por nombre y por contenido)
TRAMOS_SECRETOS = {"secret", "secrets", "credential", "credentials", "credencial", "credenciales", ".envs", ".ssh", ".aws",
                   ".azure", ".gnupg", ".kube", ".docker"}
TRAMOS_DEBILES = {"key", "keys", "private"}
PARES_SECRETOS = {(".config", "gh"), (".config", "gcloud"), (".claude", "projects"), ("microsoft", "credentials"), ("microsoft", "protect")}
NOMBRE_SECRETO = re.compile(
    r"^(\.env(?![._-](example|sample|template|dist)$)([._-].*)?|.+\.env|\.envrc|\.netrc|\.npmrc|\.pypirc|\.pgpass|\.git-credentials"
    r"|\.mcp\.json|\.claude\.json|\.credentials\.json|settings\.local\.json|id_(rsa|ed25519|ecdsa|dsa)[^/]*|known_hosts|authorized_keys|kubeconfig"
    r"|.*\.(pem|key|p12|p8|pfx|ppk|ovpn|tfvars|tfstate|tfstate\.backup|keystore|jks|kdbx|keychain(-db)?)"
    r"|client_secret.*\.json|service-account.*\.json|\.yarnrc\.yml|auth\.json|\.htpasswd|local\.settings\.json"
    r"|\.vault-token|\.my\.cnf|pip\.conf|\.zsh_history|\.bash_history|consolehost_history\.txt|history\.jsonl|.*transcripts?.*\.(jsonl|json|txt|md))$",
    re.I)
NOMBRE_SENSIBLE = re.compile(r"token(?!s)|secret|credential|credencial", re.I)
EXT_DATOS = {"", ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf", ".txt", ".db", ".properties", ".xml", ".plist",
             ".config", ".csv", ".sqlite", ".sqlite3", ".hcl", ".json5"}
EXT_COPIA = {".bak", ".old", ".orig"}
TRAMOS_NO_COPIAR = {".gemini", ".agents", ".antigravity", ".codex", ".cursor"}
CONTENIDO_EXTRA = (rb"-----BEGIN [A-Z ]*PRIVATE KEY BLOCK-----|(?<![A-Za-z0-9])APP_USR-[0-9]{8,}-|(?<![A-Za-z0-9_])EAA[A-Za-z0-9]{40,}"
                   rb"|(?<![A-Za-z0-9_])GOCSPX-[A-Za-z0-9_-]{20,}|(?<![A-Za-z0-9_])SG\.[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}"
                   rb"|(?<![A-Za-z0-9_])shpat_[A-Za-z0-9]{20,}|://[^/\s:@]{1,64}:[^/\s@]{3,}@")
CONTENIDO_SECRETO = re.compile(guias.CONTENIDO_SECRETO.pattern + b"|" + CONTENIDO_EXTRA)
CARPETAS_DE_LLAVES = [".ssh", ".aws", ".gnupg", ".config/gh", ".docker", ".kube", ".gemini", ".codex", "Library/Keychains",
                      ".config/gcloud", ".azure", ".oci", ".password-store", ".config/op", ".notebooklm", ".local/share/keyrings",
                      "AppData/Roaming/Microsoft/Credentials", "AppData/Local/Microsoft/Credentials", "AppData/Roaming/Microsoft/Protect",
                      "AppData/Roaming/gcloud"]
CONFIG_CLAUDE = re.compile(r"^(settings.*\.json|launch\.json|mcp.*\.json)(\.(bak|old|orig))?$", re.I)


def es_secreto(rel, debiles=True):
    partes = [x for x in str(rel).replace("\\", "/").split("/") if x]
    if not partes:
        return False
    bajas = [x.lower() for x in partes]
    tramos = TRAMOS_SECRETOS | TRAMOS_DEBILES if debiles else TRAMOS_SECRETOS
    if any(x in tramos for x in bajas) or any(p in PARES_SECRETOS for p in zip(bajas, bajas[1:])):
        return True
    nombre = partes[-1]
    if NOMBRE_SECRETO.match(nombre):
        return True
    raiz, ext = os.path.splitext(nombre)
    if ext.lower() in EXT_COPIA:
        if NOMBRE_SECRETO.match(raiz):
            return True
        ext = os.path.splitext(raiz)[1]
    return bool(NOMBRE_SENSIBLE.search(nombre)) and ext.lower() in EXT_DATOS


def no_se_copia(rel):
    """Config de otras herramientas, y dentro de .claude/ lo que es configuración (hooks/, settings*, launch, mcp), no notas."""
    bajas = [x.casefold() for x in str(rel).replace("\\", "/").split("/") if x]
    if any(x in TRAMOS_NO_COPIAR for x in bajas) or ".git" in bajas:
        return True
    if ".claude" in bajas:
        despues = bajas[bajas.index(".claude") + 1:]
        if "hooks" in despues[:-1] or (despues and CONFIG_CLAUDE.match(despues[-1])):
            return True
    return False


def motivo_nombre(rel, raiz=""):
    efectivo = ".claude/" + rel if os.path.basename(str(raiz).replace("\\", "/").rstrip("/")) == ".claude" else rel
    if es_secreto(efectivo):
        return "nombre de archivo de claves o entornos"
    if no_se_copia(efectivo) or CONFIG_CLAUDE.match(os.path.basename(str(rel).replace("\\", "/"))):
        return "configuración de herramientas"
    return None


def en_carpeta_de_llaves(real):
    """True si `real` (ruta absoluta resuelta) está en una carpeta de llaves de la persona, o en su carpeta de Claude privada."""
    rel = rel_dentro(real, os.path.realpath(os.path.expanduser("~")))
    if rel is None:
        return False
    if es_secreto(rel, debiles=False):
        return True
    rel_n = norm(rel) + "/"
    return any(rel_n.startswith(norm(d) + "/") for d in CARPETAS_DE_LLAVES)


def leer_pedido(ruta):
    """El pedido es texto de la persona: archivo común, suyo, ≤100 KB, sin forma de clave. Igual en Mac, Linux y Windows."""
    for r in (os.path.abspath(ruta), os.path.realpath(ruta)):
        if es_secreto(os.path.basename(r)) or en_carpeta_de_llaves(r):
            raise Salida(64, "Falta: «%s» parece un archivo de claves o está en una carpeta de llaves: no se manda ✗" % os.path.basename(ruta))
    sin_seguir = getattr(os, "O_NOFOLLOW", 0)
    if not sin_seguir and os.path.islink(ruta):
        raise Salida(64, "Falta: el pedido es un enlace simbólico: no se sigue ✗")
    try:
        fd = os.open(ruta, os.O_RDONLY | sin_seguir | getattr(os, "O_BINARY", 0))
    except OSError as e:
        raise Salida(64, "Falta: no pude abrir el pedido (%s; un enlace simbólico no se sigue) ✗" % e.__class__.__name__)
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or st.st_size > TOPE_PEDIDO:
            raise Salida(64, "Falta: el pedido no es un archivo común o pasa de %d KB ✗" % (TOPE_PEDIDO // 1024))
        if hasattr(os, "getuid") and st.st_uid != os.getuid():
            raise Salida(64, "Falta: el archivo del pedido no es tuyo: no lo mando ✗")
        crudo = os.read(fd, TOPE_PEDIDO + 1)
    finally:
        os.close(fd)
    if CONTENIDO_SECRETO.search(crudo):
        raise Salida(64, "Falta: el pedido trae algo con forma de clave: no se manda ✗")
    try:
        return crudo.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise Salida(64, "Falta: el pedido no es texto UTF-8 ✗")


# ---------------------------------------------------------------------------------------------- mensaje, tokens y precios
def cierre(texto):
    for etiqueta in ("archivo", "diff", "pedido"):
        texto = texto.replace("</" + etiqueta, "<\\/" + etiqueta)
    return texto


def nombre_etiqueta(rel):
    return re.sub(r'[<>"\r\n]', "_", str(rel))


def estimar_tokens(*textos):
    """Por exceso a propósito: bytes/1,5 (el texto denso llega a ~1,5 bytes por token)."""
    return math.ceil(sum(len(t.encode("utf-8")) for t in textos) / 1.5) + 300


def precio(modelo, tokens_entrada):
    if modelo == "claude-haiku-5-5" and tokens_entrada > 100000:
        return PRECIOS_HAIKU_LARGO
    if modelo not in PRECIOS:
        raise Salida(69, "Falta: no tengo un precio verificado para «%s»; hace falta una versión nueva del paquete metodo ✗" % modelo)
    return PRECIOS[modelo]


def costo(modelo, t_in, t_out):
    p_in, p_out = precio(modelo, t_in)
    return t_in * p_in / 1e6 + t_out * p_out / 1e6


def modelo_del_radar(alias):
    """El id vigente del alias, del radar del mismo paquete (nunca fijo en el código)."""
    ruta = os.environ.get("METODO_CLAUDE_API_RADAR") or os.path.join(AQUI, "radar.py")
    if not os.path.isfile(ruta):
        raise Salida(69, "Falta: no encuentro radar.py del paquete metodo; sin el radar no elijo modelo ✗")
    try:
        p = subprocess.run([sys.executable, ruta, "json", "--stdout"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
        datos = json.loads(p.stdout.decode("utf-8"))
    except Exception as e:
        raise Salida(69, "Falta: el radar no respondió (%s) ✗" % e.__class__.__name__)
    for f in datos.get("vigentes") or []:
        if isinstance(f, dict) and f.get("alias") == alias and ID_MODELO.match(str(f.get("modelo_api", ""))):
            return f["modelo_api"]
    raise Salida(69, "Falta: el radar no da un modelo vigente para «%s» ✗" % alias)


# ---------------------------------------------------------------------------------------------- gasto (con reserva y candado)
def _registro():
    return os.path.join(casa(), "gasto.jsonl")


def _num(reg, k):
    try:
        v = float(reg.get(k) or 0)
    except (TypeError, ValueError):
        return 0.0
    return v if math.isfinite(v) and v >= 0 else 0.0


def leer_registros():
    regs = []
    try:
        with open(_registro(), encoding="utf-8") as f:
            for linea in f:
                try:
                    d = json.loads(linea)
                except ValueError:
                    continue
                if isinstance(d, dict):
                    regs.append(d)
    except FileNotFoundError:
        pass
    except OSError:
        raise Salida(68, "Falta: no pude leer el registro de gasto (%s); sin él no se puede controlar el tope ✗" % _registro())
    return regs


def resumen(hoy=None):
    """Totales del registro. Una reserva sin cerrar (corrida cortada de golpe) cuenta su peor caso: más vale de más que de menos.
    Para el tope diario cuentan solo los TOKENS de hoy; búsquedas y código cuentan solo para el crédito."""
    hoy = hoy or datetime.date.today().isoformat()
    regs = leer_registros()
    cerradas = {str(r.get("reserva")) for r in regs if r.get("tipo") != "reserva" and r.get("reserva")}
    s = {"total": 0.0, "llamadas": 0, "hoy_tokens": 0.0, "abiertas": 0,
         "herr": {"corridas": 0, "busquedas": 0, "lecturas": 0, "usd_busquedas": 0.0, "usd_codigo": 0.0}}
    for r in regs:
        es_reserva = r.get("tipo") == "reserva"
        if es_reserva and str(r.get("id")) in cerradas:
            continue
        s["abiertas"] += 1 if es_reserva else 0
        s["llamadas"] += 0 if es_reserva else 1
        s["total"] += _num(r, "usd")
        if str(r.get("fecha", "")).startswith(hoy):
            s["hoy_tokens"] += _num(r, "usd_tokens") if "usd_tokens" in r else _num(r, "usd")
            if not es_reserva and "herramientas" in r:
                h = s["herr"]
                h["corridas"] += 1
                h["busquedas"] += int(_num(r, "busquedas"))
                h["lecturas"] += int(_num(r, "lecturas"))
                h["usd_busquedas"] += _num(r, "usd_busquedas")
                h["usd_codigo"] += _num(r, "usd_codigo_peor")
    return s


def _escribir_linea(reg):
    os.makedirs(casa(), mode=0o700, exist_ok=True)
    fd = os.open(_registro(), os.O_WRONLY | os.O_APPEND | os.O_CREAT | getattr(os, "O_BINARY", 0), 0o600)
    try:
        os.write(fd, (json.dumps(reg, ensure_ascii=False) + "\n").encode("utf-8"))
    finally:
        os.close(fd)


@contextlib.contextmanager
def candado():
    """Un solo proceso a la vez entre «mirar cuánto se gastó» y «reservar»: dos sesiones paralelas no pasan juntas el tope."""
    os.makedirs(casa(), mode=0o700, exist_ok=True)
    ruta = os.path.join(casa(), "gasto.candado")
    fin = time.time() + CANDADO_ESPERA
    marca = ("%d-%s" % (os.getpid(), os.urandom(6).hex())).encode("ascii")
    while True:
        try:
            fd = os.open(ruta, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            try:
                os.write(fd, marca)
            finally:
                os.close(fd)
            break
        except FileExistsError:
            try:
                if time.time() - os.path.getmtime(ruta) > CANDADO_VIEJO:
                    viejo = ruta + ".viejo-" + marca.decode("ascii")
                    os.replace(ruta, viejo)        # atómico: nos llevamos el candado vencido y nadie más lo borra
                    os.remove(viejo)
                    continue
            except OSError:
                pass
            if time.time() > fin:
                raise Salida(68, "Falta: otra corrida está anotando su gasto hace rato; probá de nuevo en un minuto ✗")
            time.sleep(0.1)
    try:
        yield
    finally:
        try:
            with open(ruta, "rb") as f:
                es_mio = f.read() == marca
            if es_mio:
                os.remove(ruta)
        except OSError:
            pass


def reservar(peor_tokens, extra, limites, motivo="claude-api"):
    """Frena si el día o el crédito no alcanzan y, si alcanzan, deja la reserva del peor caso. Devuelve el id de la reserva."""
    with candado():
        s = resumen()
        if s["hoy_tokens"] + peor_tokens > limites["tope_diario_usd"]:
            raise Salida(68, "Falta: tu tope diario (US$%.2f) no alcanza: hoy van %s y esta corrida podría costar hasta %s. Esperá a mañana "
                             "o que la persona lo suba (--limites dia=N, en su terminal) ✗" % (limites["tope_diario_usd"], usd(s["hoy_tokens"]), usd(peor_tokens)))
        if s["total"] + peor_tokens + extra > limites["credito_usd"]:
            raise Salida(68, "Falta: tu crédito anotado no alcanza (gastado %s + peor caso %s > US$%.2f). Si recargaste saldo en la consola de "
                             "Anthropic, que la persona lo suba (--limites credito=N, en su terminal) ✗" % (usd(s["total"]), usd(peor_tokens + extra), limites["credito_usd"]))
        rid = "%x%s" % (int(time.time() * 1000), os.urandom(4).hex())
        _escribir_linea({"tipo": "reserva", "id": rid, "fecha": datetime.datetime.now().isoformat(timespec="seconds"),
                         "usd": round(peor_tokens + extra, 6), "usd_tokens": round(peor_tokens, 6), "nota": motivo})
    return rid


def anotar_gasto(modelo, t_in, t_out, gasto, destino, nota="", reserva=None, **extra):
    """Gasto real de una corrida (cierra su reserva). Nunca la llave."""
    reg = {"fecha": datetime.datetime.now().isoformat(timespec="seconds"), "modelo": modelo, "tokens_in": int(t_in or 0),
           "tokens_out": int(t_out or 0), "usd": round(gasto, 6), "salida": destino or "", "nota": nota}
    if reserva:
        reg["reserva"] = reserva
    reg.update({k: v for k, v in extra.items() if k not in reg})
    try:
        with candado():
            _escribir_linea(reg)
    except Salida:
        _escribir_linea(reg)       # sin candado antes que sin anotar: la plata se anota siempre


# ---------------------------------------------------------------------------------------------- la llave (por referencia)
def servicio():
    return os.environ.get("METODO_CLAUDE_API_SERVICIO") or "metodo-claude-api"


def cuenta():
    return os.environ.get("METODO_CLAUDE_API_CUENTA") or "llave"


def almacen():
    """macos · windows · secret-tool · variable. METODO_CLAUDE_API_ALMACEN lo fuerza (pruebas, o Linux sin almacén)."""
    forz = (os.environ.get("METODO_CLAUDE_API_ALMACEN") or "").strip().lower()
    if forz == "variable" or (forz in ("macos", "windows", "secret-tool") and modo_prueba()):
        return forz
    if sys.platform == "darwin":
        return "macos"
    if os.name == "nt":
        return "windows"
    if shutil.which("secret-tool"):
        return "secret-tool"
    return "variable"


def nombre_almacen(a=None):
    a = a or almacen()
    return {"macos": "el Llavero de macOS", "windows": "el Administrador de credenciales de Windows",
            "secret-tool": "el llavero del sistema (libsecret)", "variable": "la variable de entorno %s (último recurso)" % VAR_LLAVE}[a]


def _security():
    return _de_prueba("METODO_CLAUDE_API_SECURITY") or "/usr/bin/security"


def _win():
    import ctypes
    from ctypes import wintypes

    class FILETIME(ctypes.Structure):
        _fields_ = [("dwLowDateTime", wintypes.DWORD), ("dwHighDateTime", wintypes.DWORD)]

    class CREDENTIAL(ctypes.Structure):
        _fields_ = [("Flags", wintypes.DWORD), ("Type", wintypes.DWORD), ("TargetName", wintypes.LPWSTR), ("Comment", wintypes.LPWSTR),
                    ("LastWritten", FILETIME), ("CredentialBlobSize", wintypes.DWORD), ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)),
                    ("Persist", wintypes.DWORD), ("AttributeCount", wintypes.DWORD), ("Attributes", ctypes.c_void_p),
                    ("TargetAlias", wintypes.LPWSTR), ("UserName", wintypes.LPWSTR)]

    adv = ctypes.WinDLL("advapi32", use_last_error=True)
    adv.CredReadW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(ctypes.POINTER(CREDENTIAL))]
    adv.CredReadW.restype = wintypes.BOOL
    adv.CredWriteW.argtypes = [ctypes.POINTER(CREDENTIAL), wintypes.DWORD]
    adv.CredWriteW.restype = wintypes.BOOL
    adv.CredDeleteW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD]
    adv.CredDeleteW.restype = wintypes.BOOL
    adv.CredFree.argtypes = [ctypes.c_void_p]
    adv.CredFree.restype = None
    return ctypes, CREDENTIAL, adv


CRED_TYPE_GENERIC, CRED_PERSIST_LOCAL_MACHINE = 1, 2


def win_leer(objetivo):
    ctypes, CREDENTIAL, adv = _win()
    p = ctypes.POINTER(CREDENTIAL)()
    if not adv.CredReadW(objetivo, CRED_TYPE_GENERIC, 0, ctypes.byref(p)):
        return ""
    try:
        n = int(p.contents.CredentialBlobSize)
        crudo = ctypes.string_at(ctypes.cast(p.contents.CredentialBlob, ctypes.c_void_p).value, n) if n else b""
    finally:
        adv.CredFree(p)
    return crudo.decode("utf-16-le", "replace")


def win_escribir(objetivo, valor):
    ctypes, CREDENTIAL, adv = _win()
    datos = valor.encode("utf-16-le")
    buf = (ctypes.c_ubyte * len(datos)).from_buffer_copy(datos)
    c = CREDENTIAL()
    c.Type, c.Persist = CRED_TYPE_GENERIC, CRED_PERSIST_LOCAL_MACHINE
    c.TargetName, c.UserName, c.Comment = objetivo, cuenta(), ETIQUETA
    c.CredentialBlobSize = len(datos)
    c.CredentialBlob = ctypes.cast(buf, ctypes.POINTER(ctypes.c_ubyte))
    ok = adv.CredWriteW(ctypes.byref(c), 0)
    codigo = ctypes.get_last_error()
    ctypes.memset(buf, 0, len(datos))
    if not ok:
        raise Salida(66, "Falta: Windows no dejó guardar la llave en el Administrador de credenciales (error %d) ✗" % codigo)


def win_borrar(objetivo):
    ctypes, _C, adv = _win()
    return bool(adv.CredDeleteW(objetivo, CRED_TYPE_GENERIC, 0))


def _leer_del_almacen(a):
    if a == "variable":
        return (os.environ.get(VAR_LLAVE) or "").strip()
    try:
        if a == "macos":
            r = subprocess.run([_security(), "find-generic-password", "-s", servicio(), "-a", cuenta(), "-w"],
                               stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=30)
            return r.stdout.decode("utf-8", "replace").strip() if r.returncode == 0 else ""
        if a == "secret-tool":
            r = subprocess.run([shutil.which("secret-tool") or "secret-tool", "lookup", "service", servicio(), "account", cuenta()],
                               stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=30)
            return r.stdout.decode("utf-8", "replace").strip() if r.returncode == 0 else ""
        if a == "windows":
            return win_leer(servicio()).strip()
    except (OSError, subprocess.SubprocessError, ValueError, AttributeError):
        return ""
    return ""


def leer_llave():
    """La llave, leída en el último momento. Nunca se imprime, guarda ni va en argumentos. Si falta: UNA línea con el único paso."""
    a = almacen()
    llave = _leer_del_almacen(a)
    if not llave:
        if a == "variable":
            raise Salida(66, "Falta: no hay llave de la API de Claude. En esta computadora no hay llavero del sistema: instalá libsecret "
                             "(secret-tool) y corré, vos, en tu terminal: %s — o, como último recurso, definí la variable %s en tu perfil ✗" % (comando_guardar(), VAR_LLAVE))
        raise Salida(66, "Falta: todavía no guardaste tu llave de la API de Claude. Es una sola vez y la hacés vos (no Claude), en una terminal: "
                         "%s — te la pide oculta y la guarda en %s ✗" % (comando_guardar(), nombre_almacen(a)))
    if llave.startswith("sk-ant-admin"):
        raise Salida(66, "Falta: lo guardado en %s es una llave de ADMINISTRACIÓN de la organización; guardá una llave de API común "
                         "(console.anthropic.com → API Keys): %s ✗" % (nombre_almacen(a), comando_guardar()))
    if not FORMA_LLAVE.match(llave):
        raise Salida(66, "Falta: lo guardado en %s no tiene forma de llave de la API de Claude (empieza con sk-ant-); volvé a guardarla: %s ✗" % (nombre_almacen(a), comando_guardar()))
    return llave


def hay_llave():
    try:
        leer_llave()
        return True
    except Salida:
        return False


def guardar_llave(tty, pedir=getpass.getpass):
    """El único paso manual. Lo corre la persona en una terminal: la llave se pide oculta y nunca se imprime ni queda en el historial.
    Sin terminal (lo intenta una IA o un programa) se niega."""
    if not tty:
        raise Salida(64, "Falta: guardar la llave lo hace la persona, en una terminal (así nunca pasa por el chat ni por una IA): %s ✗" % comando_guardar())
    a = almacen()
    if a == "variable":
        raise Salida(66, "Falta: esta computadora no tiene llavero del sistema. Instalá libsecret (paquete libsecret-tools o similar) y repetí; "
                         "como último recurso, definí la variable %s en tu perfil (queda en texto plano: preferí el llavero) ✗" % VAR_LLAVE)
    if a == "macos":
        # El que pide la llave (oculta, dos veces) es el propio /usr/bin/security: este programa nunca la ve al guardarla.
        err("Pegá tu llave de la API de Claude cuando el sistema la pida (no se ve al escribir; la pide dos veces).")
        r = subprocess.run([_security(), "add-generic-password", "-U", "-s", servicio(), "-a", cuenta(), "-l", ETIQUETA, "-w"], timeout=600)
        if r.returncode != 0:
            raise Salida(66, "Falta: el Llavero no guardó la llave (¿no coincidieron las dos veces?). Repetí: %s ✗" % comando_guardar())
    else:
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("error", getpass.GetPassWarning)    # si la terminal no puede ocultar lo escrito, no se pide
            try:
                uno = pedir("Pegá tu llave de la API de Claude (no se ve al escribir): ").strip()
                dos = pedir("Pegala de nuevo para confirmar: ").strip()
            except getpass.GetPassWarning:
                raise Salida(64, "Falta: esta terminal no puede ocultar lo que escribís; abrí una terminal común (Terminal, PowerShell) y repetí ✗")
        if not uno or uno != dos:
            raise Salida(64, "Falta: las dos veces no coinciden (o quedó vacía); repetí: %s ✗" % comando_guardar())
        if uno.startswith("sk-ant-admin"):
            raise Salida(64, "Falta: esa es una llave de ADMINISTRACIÓN de la organización; acá va una llave de API común (console.anthropic.com → API Keys). No se guardó nada ✗")
        if not FORMA_LLAVE.match(uno):
            raise Salida(64, "Falta: eso no tiene forma de llave de la API de Claude (empieza con sk-ant-); no se guardó nada ✗")
        if a == "windows":
            win_escribir(servicio(), uno)
        else:
            r = subprocess.run([shutil.which("secret-tool") or "secret-tool", "store", "--label", ETIQUETA, "service", servicio(),
                                "account", cuenta()], input=uno.encode("utf-8"), stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, timeout=120)
            if r.returncode != 0:
                raise Salida(66, "Falta: el llavero del sistema no guardó la llave (¿hay una sesión gráfica o D-Bus?) ✗")
        uno = dos = None
    leer_llave()    # comprueba que quedó y que tiene forma de llave, sin mostrarla
    return a


# ---------------------------------------------------------------------------------------------- API
class _SinRedireccion(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


ABRIR = urllib.request.build_opener(urllib.request.ProxyHandler({}), _SinRedireccion)   # sin proxies ni redirecciones: la llave no se desvía


def url_api():
    u = os.environ.get("METODO_CLAUDE_API_URL")
    if not u:
        if os.environ.get("SSL_CERT_FILE") or os.environ.get("SSL_CERT_DIR") or os.environ.get("SSLKEYLOGFILE"):
            raise Salida(64, "Falta: SSL_CERT_FILE/SSL_CERT_DIR/SSLKEYLOGFILE están puestas (cambian en quién confía la conexión o la dejan escrita); sacalas para este comando ✗")
        return API_URL
    p = urlparse(u)
    if p.scheme != "http" or p.hostname not in ("127.0.0.1", "localhost"):
        raise Salida(64, "Falta: METODO_CLAUDE_API_URL solo puede apuntar a 127.0.0.1 o localhost (para pruebas; la llave nunca va a otro lado) ✗")
    return u.rstrip("/")


def guardia_local(llave):
    if os.environ.get("METODO_CLAUDE_API_URL") and not llave.startswith("sk-ant-prueba-"):
        raise Salida(64, "Falta: contra un servidor local solo viaja una llave de prueba (sk-ant-prueba-…) ✗")


def limpiar(texto, llave):
    texto = str(texto)
    if llave:
        texto = texto.replace(llave, "[clave]")
    return CLAVE_FORMA.sub("[clave]", texto)


def evento_texto(res, d, evento):
    tipo = d.get("type") or evento
    if tipo == "message_start":
        u = (d.get("message") or {}).get("usage") or {}
        res["t_in"] = int(u.get("input_tokens") or 0)
        res["t_out"] = max(res["t_out"], int(u.get("output_tokens") or 0))
    elif tipo == "content_block_delta" and (d.get("delta") or {}).get("type") == "text_delta":
        res["texto"] += d["delta"].get("text", "")
    elif tipo == "message_delta":
        u = d.get("usage") or {}
        res["t_out"] = max(res["t_out"], int(u.get("output_tokens") or 0))
        if u.get("input_tokens"):
            res["t_in"] = int(u["input_tokens"])
        res["stop"] = (d.get("delta") or {}).get("stop_reason") or res["stop"]
        res["categoria"] = ((d.get("delta") or {}).get("stop_details") or {}).get("category") or res["categoria"]
    elif tipo == "error":
        e = d.get("error") or {}
        res["error"] = "%s · %s" % (e.get("type", "error"), e.get("message", "sin detalle"))


def una_llamada(llave, cuerpo, manejador=None, res=None):
    """(status, resultado). Lanza Salida ante error de red o HTTP (con .status y .reintentable si todavía no llegó nada)."""
    guardia_local(llave)
    req = urllib.request.Request(url_api() + "/v1/messages", data=json.dumps(cuerpo).encode("utf-8"), method="POST", headers={
        "content-type": "application/json", "x-api-key": llave, "anthropic-version": API_VERSION,
        "accept": "text/event-stream", "user-agent": "metodo-claude-api/1"})
    if res is None:
        res = {"texto": "", "t_in": 0, "t_out": 0, "stop": None, "categoria": None, "error": None}
    manejador = manejador or evento_texto
    try:
        resp = ABRIR.open(req, timeout=180)
    except urllib.error.HTTPError as e:
        try:
            info = json.loads(e.read().decode("utf-8", "replace")).get("error", {})
        except Exception:
            info = {}
        falla = Salida(67, "HTTP %d · %s · %s" % (e.code, info.get("type", "error"), info.get("message", "sin detalle")))
        falla.status, falla.reintentable = e.code, e.code in (429, 500, 502, 503, 529)
        raise falla
    except (urllib.error.URLError, OSError) as e:
        falla = Salida(67, "no pude conectar con la API (%s)" % e.__class__.__name__)
        razon = getattr(e, "reason", e)
        # solo se reintenta si el pedido seguro NO salió; un corte después de mandarlo podría cobrarse dos veces
        falla.status, falla.reintentable = 0, isinstance(razon, (socket.gaierror, ConnectionRefusedError))
        raise falla
    status = resp.status
    evento = None
    try:
        for crudo in resp:
            linea = crudo.decode("utf-8", "replace").rstrip("\r\n")
            if linea.startswith("event:"):
                evento = linea[6:].strip()
            elif linea.startswith("data:"):
                try:
                    d = json.loads(linea[5:].strip())
                except ValueError:
                    continue
                if not isinstance(d, dict):
                    continue
                try:
                    manejador(res, d, evento)
                except (ValueError, TypeError, AttributeError, KeyError):
                    continue
    except (OSError, urllib.error.URLError, http.client.HTTPException) as e:
        res["error"] = "se cortó la conexión a mitad de la respuesta (%s)" % e.__class__.__name__
    return status, res


def llamar(llave, modelo, esfuerzo, sistema, mensaje, max_salida):
    cuerpo = {"model": modelo, "max_tokens": max_salida, "stream": True, "system": sistema,
              "output_config": {"effort": esfuerzo}, "messages": [{"role": "user", "content": mensaje}]}
    for intento in range(len(ESPERAS) + 1):
        try:
            return una_llamada(llave, cuerpo)
        except Salida as e:
            if getattr(e, "reintentable", False) and intento < len(ESPERAS):
                time.sleep(ESPERAS[intento])
                continue
            nuevo = Salida(e.codigo, limpiar(e.mensaje, llave))
            nuevo.status, nuevo.reintentable = getattr(e, "status", 0), getattr(e, "reintentable", False)
            raise nuevo
