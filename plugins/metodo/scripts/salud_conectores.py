#!/usr/bin/env python3
"""salud_conectores — avisa, en UNA línea, de conectores (MCP) con el permiso vencido o caídos que SÍ usás, y de paquetes
(plugins) que repiten piezas tuyas. Nunca apaga nada solo, no lee claves ni `~/.claude.json`, y calla si no hay nada accionable.

Disparador: automático — lo llama el aviso de apertura del plugin (hooks/hooks.json → vigia/aviso.py → aviso_lineas; también `salud_conectores.py aviso` a mano). Solo lee una caché
  (<100 ms); si está vieja lanza `refrescar` en segundo plano sin esperarlo. Encadenado: el ciclo semanal de arneses de Fer
  y `informe` a mano. Apagar: `<config>/metodo/salud.apagado` o SALUD_OFF=1 (el aviso de apertura entero se apaga además con VIGIA_OFF=1).
  Prueba de disparo: scripts/tests/test_salud_conectores.py (con un `claude` falso en el PATH; nunca el real).

Subcomandos:
  aviso [stdin: JSON del hook]   imprime 0-2 líneas, solo al abrir (source=startup)
  refrescar [--cwd RUTA]         mide: `claude mcp list` desde esa carpeta + uso de 30 días en los transcripts + paquetes
                                 duplicados; escribe <config>/state/salud-ecosistema.json (atómico, con lock)
  informe [--breve] [--refrescar] [--cwd RUTA]   texto completo (--breve: líneas para el informe semanal)

Qué mide (todo local):
  · estado de cada servidor: la salida de `claude mcp list` (✔ Connected / ! Needs authentication / ✗ Failed). La CLI hace el
    chequeo; este script no abre archivos de claves ni de configuración de servidores.
  · uso: cuenta llamadas «mcp__<servidor>__…» en los transcripts modificados en los últimos 30 días (solo cuenta, no guarda texto).
  · duplicados: nombres de skills/agentes de los plugins habilitados que ya existen entre las piezas propias (solo nombres;
    de settings.json se lee SOLO la clave enabledPlugins). NO compara destinos de servidores: dos cuentas del mismo proveedor
    (p. ej. dos Hostinger) comparten URL y no son copia.
  · límite conocido: `claude mcp list` no muestra los conectores de claude.ai (los administra la app); esos quedan fuera.
Excepciones de duplicados: <config>/metodo/salud-excepciones.txt (`plugin@mercado  # motivo`).
"""
import datetime
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

TTL_ESTADO = 6 * 3600          # el estado de los conectores se vuelve a medir cada 6 h
TTL_PESADO = 24 * 3600         # uso en transcripts y duplicados: cada 24 h
DIAS_USO = 30
TOPE_SEGUNDOS_USO = 150        # el recorrido de transcripts corta aquí y marca «parcial»
MAX_CARPETAS = 30
NOMBRE_LIMPIO = re.compile(r"^[A-Za-z0-9._:@ -]{1,80}$")
ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
RX_USO = re.compile(rb'"name"\s*:\s*"mcp__([A-Za-z0-9_.\-]+?)__')


def config():
    return os.path.abspath(os.path.expanduser(os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join("~", ".claude")))


def _ruta(nombre):
    return os.path.join(config(), "state", nombre)


def leer_json(ruta, defecto):
    try:
        with open(ruta, encoding="utf-8") as f:
            v = json.load(f)
        return v if isinstance(v, type(defecto)) else defecto
    except (OSError, ValueError):
        return defecto


def escribir_json(ruta, datos):
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(ruta), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False)
        os.replace(tmp, ruta)
    except OSError:
        try:
            os.unlink(tmp)
        except OSError:
            pass


def apagado():
    return bool(os.environ.get("SALUD_OFF")) or os.path.exists(os.path.join(config(), "metodo", "salud.apagado"))


# ── estado de los servidores (claude mcp list) ───────────────────────────────
def normalizar(nombre):
    """Como arma Claude el nombre de herramienta: plugin:a:b → plugin_a_b; todo lo no alfanumérico → «_»."""
    return re.sub(r"[^A-Za-z0-9_-]", "_", nombre)


def parsear_mcp_list(texto):
    """[{nombre, destino, estado}] con estado ok | auth | roto | otro. Línea que no entiendo: se ignora (nunca cuenta como verde)."""
    out = []
    for linea in ANSI.sub("", texto or "").splitlines():
        m = re.match(r"^(?P<n>\S.*?): (?P<d>.+) - (?P<e>\S.*)$", linea.strip())
        if not m:
            continue
        e = m.group("e").lower()
        if "needs auth" in e or "authenticat" in e:
            est = "auth"
        elif "connected" in e and "not" not in e and "fail" not in e:
            est = "ok"
        elif "fail" in e or "✗" in e or "error" in e:
            est = "roto"
        else:
            est = "otro"
        nombre = m.group("n").strip()
        if not NOMBRE_LIMPIO.match(nombre):
            continue                       # un nombre con signos raros nunca llega al contexto de Claude
        out.append({"nombre": nombre, "destino": m.group("d").strip(), "estado": est})
    return out


def _settings_ajeno(carpeta):
    """¿La carpeta trae ajustes de proyecto que cambian qué servidores arranca o con qué entorno? (se mira el texto, sin interpretarlo)"""
    for nombre in ("settings.json", "settings.local.json"):
        try:
            with open(os.path.join(carpeta, ".claude", nombre), encoding="utf-8", errors="replace") as f:
                t = f.read(200000)
        except OSError:
            continue
        if any(k in t for k in ("enableAllProjectMcpServers", "enabledMcpjsonServers", "mcpServers", '"env"')):
            return True
    return False


def _carpeta_propia(propia):
    """¿Está dentro de una carpeta que la persona declaró suya en <config>/metodo/salud-carpetas-propias.txt (una ruta por línea)?"""
    try:
        with open(os.path.join(config(), "metodo", "salud-carpetas-propias.txt"), encoding="utf-8") as f:
            lineas = [l.split("#", 1)[0].strip() for l in f]
    except OSError:
        return False
    for l in lineas:
        if not l:
            continue
        try:
            base = os.path.realpath(os.path.expanduser(l))
            if os.path.commonpath([propia, base]) == base:
                return True
        except (OSError, ValueError):
            continue
    return False


def carpeta_segura(cwd):
    """`claude mcp list` NO pide confirmar la confianza de la carpeta y arranca los servidores locales de su `.mcp.json`:
    desde una carpeta ajena podría ejecutar código sin tu permiso. Por eso solo se corre dentro de la carpeta de trabajo si ni ella ni
    sus carpetas madre (ya resueltos los enlaces simbólicos) tienen `.mcp.json`, y la carpeta no trae ajustes que cambien servidores o
    entorno; si no, se corre desde tu carpeta personal (se pierden los servidores propios de esa carpeta). Las carpetas que declarás tuyas
    en <config>/metodo/salud-carpetas-propias.txt se saltean esa revisión."""
    home = os.path.realpath(os.path.expanduser("~"))
    try:
        propia = os.path.realpath(cwd) if cwd else ""
    except (OSError, ValueError):
        propia = ""
    if not propia or not os.path.isdir(propia):
        return home
    if _carpeta_propia(propia):
        return propia                      # carpeta que la propia persona declaró suya: ahí sí vale ver sus servidores de proyecto
    if _settings_ajeno(propia):
        return home
    d = propia
    while d and d != home:                 # tu carpeta personal tiene el `.mcp.json` que armaste vos: no cuenta como ajeno
        if os.path.exists(os.path.join(d, ".mcp.json")):
            return home
        padre = os.path.dirname(d)
        if padre == d:
            break
        d = padre
    return propia


def ejecutable_claude(cwd=None):
    """Ruta de `claude`, nunca una que viva dentro de la carpeta del proyecto: en Windows `which` mira primero la carpeta actual y un
    `claude.cmd` de un repo ajeno se ejecutaría solo."""
    viejo = os.environ.get("NoDefaultCurrentDirectoryInExePath")
    os.environ["NoDefaultCurrentDirectoryInExePath"] = "1"
    try:
        exe = shutil.which("claude")
    finally:
        if viejo is None:
            os.environ.pop("NoDefaultCurrentDirectoryInExePath", None)
        else:
            os.environ["NoDefaultCurrentDirectoryInExePath"] = viejo
    if not exe:
        return None
    try:
        real = os.path.realpath(exe)
        for c in (cwd, os.getcwd()):
            if c:
                c = os.path.realpath(c)
                if os.path.commonpath([real, c]) == c and c != os.path.realpath(os.path.expanduser("~")):
                    return None
    except (OSError, ValueError):
        return None
    return exe


def correr_mcp_list(cwd):
    exe = ejecutable_claude(cwd)           # en Windows encuentra claude.cmd
    if not exe:
        return None
    try:
        r = subprocess.run([exe, "mcp", "list"], capture_output=True, text=True, encoding="utf-8", errors="replace",
                           timeout=90, cwd=carpeta_segura(cwd), stdin=subprocess.DEVNULL)
    except (OSError, subprocess.SubprocessError):
        return None
    lista = parsear_mcp_list(r.stdout)
    return lista or None


# ── uso en transcripts ───────────────────────────────────────────────────────
def contar_usos(dias=DIAS_USO, tope=TOPE_SEGUNDOS_USO):
    """({id_normalizado: llamadas}, parcial) en los transcripts con mtime dentro de la ventana. Solo cuenta, nunca guarda texto.
    Incremental: guarda el conteo por archivo (ruta, tamaño, mtime) y solo relee lo que cambió; si se corta por tiempo, lo ya
    contado queda guardado y la próxima corrida sigue."""
    base = os.path.join(config(), "projects")
    corte = time.time() - dias * 86400
    inicio = time.time()
    cache_ruta = _ruta("salud-usos.json")
    viejo = leer_json(cache_ruta, {}).get("archivos", {})
    nuevo, parcial = {}, False
    for raiz, _dirs, archivos in os.walk(base):
        for a in archivos:
            if not a.endswith(".jsonl"):
                continue
            ruta = os.path.join(raiz, a)
            try:
                st = os.stat(ruta)
            except OSError:
                continue
            if st.st_mtime < corte:
                continue
            previo = viejo.get(ruta)
            if isinstance(previo, list) and len(previo) == 3 and previo[0] == st.st_mtime and previo[1] == st.st_size:
                nuevo[ruta] = previo
                continue
            if parcial:
                continue
            cuentas = {}
            try:
                with open(ruta, "rb") as f:
                    cola = b""
                    while True:
                        trozo = f.read(8 << 20)
                        if not trozo:
                            break
                        datos = cola + trozo
                        for m in RX_USO.finditer(datos):
                            k = m.group(1).decode("utf-8", "replace")
                            cuentas[k] = cuentas.get(k, 0) + 1
                        cola = datos[-200:]      # un nombre cortado entre dos trozos se completa con la cola (puede repetir 1 vez: tolerable)
            except OSError:
                continue
            nuevo[ruta] = [st.st_mtime, st.st_size, cuentas]
            if time.time() - inicio > tope:
                parcial = True
    escribir_json(cache_ruta, {"archivos": nuevo})
    total = {}
    for _m, _t, cuentas in nuevo.values():
        for k, v in cuentas.items():
            total[k] = total.get(k, 0) + v
    return total, parcial


# ── paquetes duplicados ──────────────────────────────────────────────────────
def _nombres_md(carpeta):
    try:
        return {f[:-3] for f in os.listdir(carpeta) if f.endswith(".md")}
    except OSError:
        return set()


def _nombres_skills(carpeta):
    try:
        return {d for d in os.listdir(carpeta) if os.path.isfile(os.path.join(carpeta, d, "SKILL.md"))}
    except OSError:
        return set()


def _agentes_propios():
    cfg = config()
    lineas = []
    try:
        with open(os.path.join(cfg, "metodo", "raices-agentes.txt"), encoding="utf-8") as f:
            lineas = [l.strip() for l in f if l.strip() and not l.lstrip().startswith("#")]
    except OSError:
        pass
    raices = []
    home = os.path.dirname(cfg)
    for l in lineas or [os.path.join(cfg, "agents")]:
        p = l.replace("~", home, 1) if l.startswith("~") else l
        import glob
        raices += glob.glob(p) if any(c in p for c in "*?[") else [p]
    out = set()
    for r in raices:
        out |= _nombres_md(r)
    return out


def _excepciones():
    out = set()
    try:
        with open(os.path.join(config(), "metodo", "salud-excepciones.txt"), encoding="utf-8") as f:
            for l in f:
                l = l.split("#", 1)[0].strip()
                if l:
                    out.add(l)
    except OSError:
        pass
    return out


def plugins_habilitados():
    """{clave: carpeta} de los plugins habilitados e instalados. De settings.json se lee SOLO enabledPlugins."""
    cfg = config()
    ajustes = leer_json(os.path.join(cfg, "settings.json"), {})
    habil = ajustes.get("enabledPlugins")
    habil = {k for k, v in habil.items() if v} if isinstance(habil, dict) else set()
    inst = leer_json(os.path.join(cfg, "plugins", "installed_plugins.json"), {}).get("plugins", {})
    out = {}
    if isinstance(inst, dict):
        for clave in habil:
            filas = inst.get(clave)
            if isinstance(filas, list) and filas and isinstance(filas[0], dict) and os.path.isdir(filas[0].get("installPath", "")):
                out[clave] = filas[0]["installPath"]
    return out


def duplicados_de_paquetes():
    propias_skills = _nombres_skills(os.path.join(config(), "skills"))
    propios_agentes = _agentes_propios()
    exc = _excepciones()
    out = []
    for clave, carpeta in sorted(plugins_habilitados().items()):
        if clave in exc or clave.split("@")[0] in exc or clave.split("@")[0] == "metodo":
            continue                    # «metodo» es quien trae este control: nunca se propone apagarlo
        if not NOMBRE_LIMPIO.match(clave):
            continue
        sk, ag = _nombres_skills(os.path.join(carpeta, "skills")), _nombres_md(os.path.join(carpeta, "agents"))
        total = len(sk) + len(ag)
        rep = sorted(n for n in ((sk & propias_skills) | (ag & propios_agentes)) if NOMBRE_LIMPIO.match(n))
        n = len(rep)
        if n >= 3 or (n >= 2 and n * 2 >= total):
            out.append({"plugin": clave, "n": n, "total": total, "ejemplos": rep[:5]})
    return out


# ── refresco ─────────────────────────────────────────────────────────────────
def refrescar(cwd):
    lock = _ruta("salud-ecosistema.lock")
    os.makedirs(os.path.dirname(lock), exist_ok=True)
    try:
        if os.path.exists(lock) and time.time() - os.path.getmtime(lock) >= 600:
            os.unlink(lock)                # candado viejo (un refresco que murió)
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)      # atómico: solo uno lo crea; no sigue enlaces
        os.close(fd)
    except OSError:
        return 0
    try:
        est = leer_json(_ruta("salud-ecosistema.json"), {})
        ahora = time.time()
        lista = correr_mcp_list(cwd)
        carpetas = est.get("carpetas") if isinstance(est.get("carpetas"), dict) else {}
        carpetas[cwd or ""] = {"ts": ahora, "conectores": lista, "sin_dato": lista is None}
        if len(carpetas) > MAX_CARPETAS:
            for k in sorted(carpetas, key=lambda k: carpetas[k].get("ts", 0))[:len(carpetas) - MAX_CARPETAS]:
                carpetas.pop(k, None)
        est["carpetas"] = carpetas
        pesado = est.get("pesado") if isinstance(est.get("pesado"), dict) else {}
        if ahora - pesado.get("ts", 0) > TTL_PESADO:
            usos, parcial = contar_usos()
            est["pesado"] = {"ts": ahora, "usos": usos, "parcial": parcial, "duplicados": duplicados_de_paquetes()}
        escribir_json(_ruta("salud-ecosistema.json"), est)
    finally:
        try:
            os.unlink(lock)
        except OSError:
            pass
    return 0


def lanzar_refresco(cwd):
    """Segundo plano, sin esperar y sin ventana."""
    cmd = [sys.executable, os.path.abspath(__file__), "refrescar", "--cwd", cwd or ""]
    kw = {"stdin": subprocess.DEVNULL, "stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL, "cwd": os.path.expanduser("~")}   # nunca dentro de la carpeta del proyecto
    if os.name == "nt":
        kw["creationflags"] = 0x00000008 | 0x08000000      # DETACHED_PROCESS | CREATE_NO_WINDOW
    else:
        kw["start_new_session"] = True
    try:
        subprocess.Popen(cmd, **kw)
    except (OSError, ValueError):
        pass


# ── clasificación ────────────────────────────────────────────────────────────
def clasificar(entrada, usos):
    """Separa los conectores de una carpeta: (auth_usados, rotos_usados, auth_no_usados, rotos_no_usados)."""
    a_u, r_u, a_n, r_n = [], [], [], []
    for c in entrada.get("conectores") or []:
        if c["estado"] not in ("auth", "roto"):
            continue
        usado = usos.get(normalizar(c["nombre"]), 0) > 0
        destino = {("auth", True): a_u, ("roto", True): r_u, ("auth", False): a_n, ("roto", False): r_n}[(c["estado"], usado)]
        destino.append(c["nombre"])
    return a_u, r_u, a_n, r_n


def _corto(nombres, n=4):
    nombres = sorted(nombres)
    return ", ".join(nombres[:n]) + (f" y {len(nombres) - n} más" if len(nombres) > n else "")


def _agrupar_plugins(nombres):
    """plugin:productivity:gmail ×10 → «productivity (10)»; los demás, por nombre."""
    g, otros = {}, []
    for n in nombres:
        p = n.split(":")
        if n.startswith("plugin:") and len(p) >= 3:
            g[p[1]] = g.get(p[1], 0) + 1
        else:
            otros.append(n)
    return [f"{k} ({v})" for k, v in sorted(g.items())] + sorted(otros)


# ── aviso (hook) ─────────────────────────────────────────────────────────────
def aviso_lineas(cwd, fuente="startup"):
    """[(texto visible, contexto para Claude)] — 0 a 2 líneas, solo lee la caché (<100 ms). Si está vieja, lanza el refresco aparte."""
    if apagado() or fuente != "startup":
        return []
    est = leer_json(_ruta("salud-ecosistema.json"), {})
    carpetas = est.get("carpetas") if isinstance(est.get("carpetas"), dict) else {}
    entrada = carpetas.get(cwd) or {}
    pesado = est.get("pesado") if isinstance(est.get("pesado"), dict) else {}
    ahora = time.time()
    if ahora - entrada.get("ts", 0) > TTL_ESTADO or ahora - pesado.get("ts", 0) > TTL_PESADO:
        lanzar_refresco(cwd)
    lineas = []
    if entrada and ahora - entrada.get("ts", 0) < 3 * 86400 and pesado:
        a_u, r_u, _a, _r = clasificar(entrada, pesado.get("usos") or {})
        if a_u:
            t = f"Conectores por firmar (los usás): {_corto(a_u)} → escribí /mcp y firmá cada uno."
            lineas.append((t, t))
        if r_u:
            t = f"Conectores caídos que usás: {_corto(r_u)} → escribí /mcp para ver el motivo."
            lineas.append((t, t))
    dups = pesado.get("duplicados") or []
    hoy = datetime.date.today()
    firma = ",".join(d["plugin"] for d in dups)
    previo = est.get("avisado_duplicados") if isinstance(est.get("avisado_duplicados"), dict) else {}
    try:
        dias = (hoy - datetime.date.fromisoformat(previo.get("fecha", "2000-01-01"))).days
    except ValueError:
        dias = 99
    if dups and (previo.get("firma") != firma or dias >= 7):       # una línea cuando cambia la lista y un recordatorio por semana, no todos los días
        d = dups[0]
        resto = f" (y {len(dups) - 1} paquete(s) más)" if len(dups) > 1 else ""
        vis = f"Paquete duplicado: «{d['plugin']}» repite {d['n']} piezas tuyas ({', '.join(d['ejemplos'][:3])}…){resto}."
        ctx = vis + f" Ofrecele a la persona apagarlo y, con su sí, corré: claude plugin disable {d['plugin']}"
        lineas.append((vis, ctx))
        est["avisado_duplicados"] = {"firma": firma, "fecha": hoy.isoformat()}
        escribir_json(_ruta("salud-ecosistema.json"), est)
    return lineas[:2]


def cmd_aviso():
    """A mano o desde un hook propio: imprime el texto. (En el plugin lo llama vigia/aviso.py con aviso_lineas.)"""
    try:
        datos = json.loads(sys.stdin.read() or "{}")
        datos = datos if isinstance(datos, dict) else {}
    except ValueError:
        datos = {}
    cwd = datos.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    lineas = aviso_lineas(cwd, datos.get("source", "startup"))
    if lineas:
        print("\n".join(c for _v, c in lineas))
    return 0


# ── informe ──────────────────────────────────────────────────────────────────
def lineas_informe(cwd, breve):
    est = leer_json(_ruta("salud-ecosistema.json"), {})
    pesado = est.get("pesado") if isinstance(est.get("pesado"), dict) else {}
    carpetas = est.get("carpetas") if isinstance(est.get("carpetas"), dict) else {}
    entrada = carpetas.get(cwd) or (max(carpetas.values(), key=lambda e: e.get("ts", 0)) if carpetas else {})
    if not entrada or not pesado:
        return ["conectores: sin dato (no corrió `claude mcp list` o todavía no hay medición)"]
    if entrada.get("sin_dato"):
        return ["conectores: sin dato (`claude mcp list` no respondió)"]
    a_u, r_u, a_n, r_n = clasificar(entrada, pesado.get("usos") or {})
    out = []
    if a_u:
        out.append(f"conectores sin firmar que SÍ usás: {_corto(a_u, 8)} → /mcp")
    if r_u:
        out.append(f"conectores caídos que SÍ usás: {_corto(r_u, 8)} → /mcp")
    if a_n:
        out.append(f"conectores sin firmar que no usás en {DIAS_USO} d: {len(a_n)} ({_corto(_agrupar_plugins(a_n), 6)}); no se apaga nada por desuso")
    if r_n:
        out.append(f"conectores caídos que no usás en {DIAS_USO} d: {len(r_n)} ({_corto(_agrupar_plugins(r_n), 6)})")
    for d in pesado.get("duplicados") or []:
        out.append(f"paquete «{d['plugin']}» repite {d['n']} de sus {d['total']} piezas con las tuyas ({', '.join(d['ejemplos'][:3])}…) → claude plugin disable {d['plugin']}")
    if pesado.get("parcial"):
        out.append("uso de conectores: medición parcial (se cortó por tiempo)")
    if not out:
        out.append("conectores y paquetes: sin hallazgos ✓")
    return out if not breve else out[:8]


def main():
    a = sys.argv[1:]
    cmd = a[0] if a else "informe"
    cwd = a[a.index("--cwd") + 1] if "--cwd" in a and a.index("--cwd") + 1 < len(a) else (os.getcwd() if cmd != "aviso" else "")
    try:
        if cmd == "aviso":
            return cmd_aviso()
        if cmd == "refrescar":
            return refrescar(cwd)
        if cmd == "informe":
            if "--refrescar" in a:
                refrescar(cwd)
            print("\n".join(lineas_informe(cwd, "--breve" in a)))
            return 0
        print(__doc__)
        return 2
    except Exception as e:      # un fallo de este control nunca debe romper la apertura de una sesión
        if cmd == "informe":
            print(f"salud_conectores con error: {type(e).__name__}: {str(e)[:100]}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
