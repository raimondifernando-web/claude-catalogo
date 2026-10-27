"""cierre_estado.py — estado en disco y transiciones para la mudanza de sesión (.claude/cerrando.json).

Disparador: encadenado — lo usan cierre-mudanza.py (lo corre /metodo:cerrar, Paso A y paso 10), freno-envio-cerrando.py (hook de
envíos, automático) y arrancar-check.py (lo corre /metodo:arrancar: cierra la mudanza anterior y lee las cartas).

Por qué existe: una sesión con puesto fijo (la sesión principal de una carpeta) tiene que cerrar cada tanto
y ser reemplazada por otra en la misma carpeta (cwd). La mudanza de una vuelta sigue un orden fijo:
  congelar → abierta → guardado → hijas → archivando → completo.
Este módulo administra el archivo <carpeta>/.claude/cerrando.json de manera atómica, verifica cada
paso contra los metadatos de la app de Claude y determina la siguiente instrucción para el modelo.
Es el único estado nuevo que persiste la mudanza.
"""
import json
import os
import sys
import time

# Asegurar que se importan los módulos hermanos de scripts/
_AQUI = os.path.dirname(os.path.realpath(__file__))
if _AQUI not in sys.path:
    sys.path.insert(0, _AQUI)

import cartas  # noqa: E402
import sesiones_hijas as hs  # noqa: E402

ORDEN = ["congelado", "abierta", "guardado", "hijas", "archivando", "completo"]
VIGENCIA_S = 24 * 3600


def ruta(carpeta):
    """Ruta al archivo <carpeta>/.claude/cerrando.json."""
    return os.path.join(carpeta, ".claude", "cerrando.json")


def leer(carpeta):
    """Lee y valida el estado en <carpeta>/.claude/cerrando.json.

    Devuelve dict con el estado si es válido. Si el archivo no existe, el JSON
    está roto o faltan campos obligatorios, devuelve None. Nunca lanza excepciones.
    """
    try:
        p = ruta(carpeta)
        if not os.path.isfile(p):
            return None
        with open(p, "r", encoding="utf-8") as f:
            d = json.load(f)
        if not isinstance(d, dict):
            return None
        # Validar campos obligatorios y tipos esperados
        if "vieja" not in d or not isinstance(d["vieja"], str):
            return None
        if "sucesora" not in d or (d["sucesora"] is not None and not isinstance(d["sucesora"], str)):
            return None
        if d.get("paso") not in ORDEN:
            return None
        if "desde" not in d or not isinstance(d["desde"], (int, float)):
            return None
        if "carpeta" not in d or not isinstance(d["carpeta"], str):
            return None
        return d
    except Exception:
        return None


def escribir(carpeta, d):
    """Escribe atómicamente el estado en <carpeta>/.claude/cerrando.json con modo 0o600."""
    dir_claude = os.path.join(carpeta, ".claude")
    os.makedirs(dir_claude, mode=0o700, exist_ok=True)
    try:
        os.chmod(dir_claude, 0o700)
    except OSError:
        pass
    dest = ruta(carpeta)
    pid = os.getpid()
    ahora_ms = int(time.time() * 1000)
    tmp = os.path.join(dir_claude, f".cerrando.{pid}.{ahora_ms}.tmp")
    contenido = json.dumps(d, ensure_ascii=False, indent=2) + "\n"
    fd = os.open(tmp, os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(contenido)
        try:
            os.chmod(tmp, 0o600)
        except OSError:
            pass
        os.replace(tmp, dest)
        try:
            os.chmod(dest, 0o600)
        except OSError:
            pass
    except Exception:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except OSError:
            pass
        raise


def vigente(d, ahora=None):
    """True si d existe, paso != 'completo' y tiene menos de 24 h (VIGENCIA_S).

    Un estado viejo (> 24 h) no frena nada.
    """
    if not d or not isinstance(d, dict):
        return False
    if d.get("paso") == "completo":
        return False
    desde = d.get("desde")
    if not isinstance(desde, (int, float)):
        return False
    ahora_s = time.time() if ahora is None else ahora
    if (ahora_s - desde) >= VIGENCIA_S or (ahora_s - desde) < -60:
        return False
    return True


def congelar(carpeta, vieja, ses=None):
    """Crea el estado inicial con paso 'congelado' y deja carta en el buzón.

    Si ya hay uno vigente con OTRA vieja → lanza ValueError.
    Con la misma vieja → lo devuelve tal cual (idempotente).
    """
    d_actual = leer(carpeta)
    if d_actual and vigente(d_actual):
        if d_actual.get("vieja") == vieja:
            return d_actual
        # la mudanza anterior produjo a esta sesión, o su vieja ya murió: si nadie la marcó «completo», no puede trabar la siguiente
        s_ant = next((x for x in (ses or []) if isinstance(x, dict) and x.get("sessionId") == d_actual.get("vieja")), None)
        muerta = ses is not None and (s_ant is None or bool(s_ant.get("isArchived")))
        if d_actual.get("sucesora") != vieja and not muerta:
            raise ValueError(f"ya hay un cierre en curso de {d_actual['vieja']} (si fue un error: cierre-mudanza.py cancelar)")

    ahora = int(time.time())
    real = os.path.realpath(carpeta)
    d = {
        "vieja": vieja,
        "sucesora": None,
        "paso": "congelado",
        "desde": ahora,
        "carpeta": real,
    }
    escribir(carpeta, d)
    return d


def cancelar(carpeta):
    """Descongela: deja el estado en 'completo' con la marca cancelado (para una mudanza que no pudo seguir). True si había una vigente."""
    d = leer(carpeta)
    if not d or not vigente(d):
        return False
    d["paso"] = "completo"
    d["cancelado"] = True
    escribir(carpeta, d)
    return True


def marcar_abierta(carpeta, sucesora_id, ses):
    """Verifica la sucesora contra `ses` y la guarda con paso 'abierta'.

    Verificaciones:
      - Sucesora existe en `ses` y no está archivada.
      - Su cwd u originCwd coincide con esta carpeta.
      - Está suelta (padre_de(s) is None o s.lineageDetached is True).
    Devuelve (ok, motivo).
    """
    d = leer(carpeta)
    if not d or not vigente(d):
        return False, "no hay cierre en curso"
    if ORDEN.index(d["paso"]) < ORDEN.index("congelado"):
        return False, f"paso inválido: {d['paso']}"
    if d["paso"] not in ("congelado", "abierta"):
        if d.get("sucesora") == sucesora_id:
            return True, f"sesión sucesora '{sucesora_id}' ya registrada"
        return False, f"el cierre ya está en paso '{d['paso']}'"

    s = next((x for x in ses if isinstance(x, dict) and x.get("sessionId") == sucesora_id), None)
    if not s:
        return False, f"no encontré la sesión '{sucesora_id}' en los metadatos de la app"
    if s.get("isArchived"):
        return False, f"la sesión '{sucesora_id}' está archivada"

    real_carp = d.get("carpeta") or os.path.realpath(carpeta)
    cwds = {os.path.realpath(x) for x in (s.get("cwd"), s.get("originCwd")) if x}
    if real_carp not in cwds:
        return False, f"la sesión '{sucesora_id}' no pertenece a esta carpeta ({carpeta})"

    padre = hs.padre_de(s)
    suelta = (padre is None) or bool(s.get("lineageDetached"))
    if not suelta:
        return False, f'sigue colgada de la vieja: detach_session("{sucesora_id}") ANTES de archivarte'

    d["sucesora"] = sucesora_id
    d["paso"] = "abierta"
    escribir(carpeta, d)
    return True, f"sesión sucesora '{sucesora_id}' verificada y suelta"


def marcar_guardado(carpeta):
    """Exige paso >= 'abierta' y REANUDAR.md fresco (mtime >= d['desde']).

    Guarda paso 'guardado' y devuelve (ok, motivo).
    """
    d = leer(carpeta)
    if not d or not vigente(d):
        return False, "no hay cierre en curso"
    if ORDEN.index(d["paso"]) < ORDEN.index("abierta"):
        return False, f"el paso actual es '{d['paso']}'; debe estar en 'abierta' antes de marcar guardado"

    # /cerrar lo deja en la raíz de la carpeta; también se acepta .claude/prompts/ (como arrancar-check)
    candidatos = [os.path.join(carpeta, "REANUDAR.md"), os.path.join(carpeta, ".claude", "prompts", "REANUDAR.md")]
    existentes = [c for c in candidatos if os.path.isfile(c)]
    if not existentes:
        return False, f"no existe {candidatos[0]}"

    if max(os.path.getmtime(c) for c in existentes) < d["desde"]:
        return False, "el REANUDAR.md no se actualizó desde que se congeló"

    if d["paso"] == "abierta":
        d["paso"] = "guardado"
        escribir(carpeta, d)
    return True, "REANUDAR.md actualizado y verificado"


def hijas_pendientes(carpeta, ses):
    """Descendientes vivas (no archivadas) de la vieja según spawnedFrom, salvo la sucesora.

    Devuelve lista de dicts: {id, titulo, estado, accion}.
    """
    d = leer(carpeta)
    if not d:
        return []
    vieja = d.get("vieja")
    sucesora = d.get("sucesora")
    if not vieja:
        return []
    carp_real = d.get("carpeta") or os.path.realpath(carpeta)

    vistos = {vieja}
    cola = [vieja]
    descendientes = []
    while cola:
        p = cola.pop(0)
        for s in ses:
            if not isinstance(s, dict):
                continue
            sid = s.get("sessionId")
            if not sid or sid in vistos:
                continue
            if hs.padre_de(s) == p:
                vistos.add(sid)
                if s.get("lineageDetached"):
                    # soltada con detach_session: ya no es hija (ni sus propias hijas cuelgan de la vieja)
                    continue
                cola.append(sid)
                if not s.get("isArchived") and sid != sucesora:
                    descendientes.append(s)

    resultado = []
    for h in descendientes:
        sid = h["sessionId"]
        titulo = h.get("title", "")
        est = hs.estado(h)
        bloqueos = hs.bloqueos_de(h, ses)
        if bloqueos and est != "trabajando":
            # trabajo sin guardar o informe sin leer: se resuelve ANTES de terminarla (Paso 0 de /cerrar)
            accion = " | ".join(hs.acciones_de(h, ses))
        elif est == "terminada":
            accion = f'archive_session("{sid}")'
        elif est == "esperando":
            accion = (
                f'SendMessage a {sid}: "dejá tu pedido y el PR en {carp_real}/.claude/PENDIENTES.md '
                f'(sin vigilar el PR) y archivate; cualquier aviso mío, dejalo con: '
                f'{cartas.comando(carp_real)}" y después archive_session'
            )
        elif est == "trabajando":
            accion = (
                f'detach_session("{sid}") y SendMessage a {sid}: "ya no dependés de la sesión que cierra; '
                f'cuando termines, dejá tu informe con: {cartas.comando(carp_real)}. Sigue la carpeta compartida: nada de git pull/rebase/stash/add -A/push ahí (guardá solo tus rutas; subí desde una copia propia)"'
            )
        else:
            accion = f'archive_session("{sid}")'

        resultado.append({
            "id": sid,
            "titulo": titulo,
            "estado": est,
            "accion": accion,
            "bloqueos": bloqueos if est != "trabajando" else [],
        })
    return resultado


def marcar_hijas(carpeta, ses):
    """Exige paso >= 'guardado'. Ok solo si ninguna hija viva está 'terminada' o 'esperando'.

    Las 'trabajando' no frenan si ya tienen lineageDetached=True. Paso 'hijas'.
    """
    d = leer(carpeta)
    if not d or not vigente(d):
        return False, "no hay cierre en curso"
    if ORDEN.index(d["paso"]) < ORDEN.index("guardado"):
        return False, f"el paso actual es '{d['paso']}'; debe estar en 'guardado' antes de marcar hijas"

    pend = hijas_pendientes(carpeta, ses)
    for h in pend:
        est = h["estado"]
        sid = h["id"]
        tit = h.get("titulo", "")
        if h.get("bloqueos"):
            return False, f'hija «{tit}» ({sid}) tiene trabajo sin resolver: {"; ".join(h["bloqueos"])}'
        if est == "terminada":
            return False, f'hija «{tit}» ({sid}) está terminada pero no archivada: archive_session("{sid}")'
        elif est == "esperando":
            return False, f'hija «{tit}» ({sid}) está esperando: resolver antes de archivar'
        elif est == "trabajando":
            s_dict = next((x for x in ses if isinstance(x, dict) and x.get("sessionId") == sid), None)
            if not s_dict or not s_dict.get("lineageDetached"):
                return False, f'hija «{tit}» ({sid}) sigue trabajando pero está colgada: detach_session("{sid}")'

    if d["paso"] == "guardado":
        d["paso"] = "hijas"
        escribir(carpeta, d)
    return True, "hijas resueltas y verificadas"


def marcar_archivando(carpeta):
    """Exige paso >= 'hijas'. Pasa a 'archivando'.

    Después de esto lo único que queda es archive_session("self").
    """
    d = leer(carpeta)
    if not d or not vigente(d):
        return False, "no hay cierre en curso"
    if ORDEN.index(d["paso"]) < ORDEN.index("hijas"):
        return False, f"el paso actual es '{d['paso']}'; debe estar en 'hijas' antes de marcar archivando"

    if d["paso"] == "hijas":
        d["paso"] = "archivando"
        escribir(carpeta, d)
    return True, 'Ahora sí: archive_session("self") y terminá tu respuesta.'


def completar(carpeta, ses):
    """Lo llama la sucesora al arrancar.

    Si hay estado y la vieja figura archivada (o ya no existe) en `ses`,
    pasa a 'completo' y devuelve True. Si no, False.
    """
    d = leer(carpeta)
    if not d:
        return False
    vieja = d.get("vieja")
    if not vieja or not ses:
        return False  # sin datos de la app no se puede saber si la vieja se archivó: no se adivina
    s_vieja = next((x for x in ses if isinstance(x, dict) and x.get("sessionId") == vieja), None)
    if s_vieja is None or bool(s_vieja.get("isArchived")):
        d["paso"] = "completo"
        escribir(carpeta, d)
        return True
    return False


def destino_congelado(destino_id, ses, ahora=None):
    """Si destino_id es la 'vieja' de un estado vigente en su carpeta (cwd/originCwd),

    devuelve la carpeta real. Si no, None. Nunca lanza excepciones.
    """
    try:
        if not destino_id or not isinstance(destino_id, str):
            return None
        s = next((x for x in ses if isinstance(x, dict) and x.get("sessionId") == destino_id), None)
        if not s:
            return None
        carpetas = []
        for k in ("cwd", "originCwd"):
            c = s.get(k)
            if c and isinstance(c, str) and c not in carpetas:
                carpetas.append(c)
        for carp in carpetas:
            d = leer(carp)
            if d and vigente(d, ahora=ahora) and d.get("vieja") == destino_id:
                return d.get("carpeta") or os.path.realpath(carp)
        return None
    except Exception:
        return None


def siguiente(d, ses=None):
    """La próxima instrucción en una línea según el paso actual."""
    if not d or not isinstance(d, dict):
        return "Sin cierre en curso."
    paso = d.get("paso")
    carp = d.get("carpeta", "")
    if paso == "congelado":
        return f"abrí la sesión nueva con start_session en {carp}, ejecutá detach_session(<id nuevo>) y corré: cierre-mudanza.py abierta <id nuevo>"
    elif paso == "abierta":
        return f"actualizá el REANUDAR.md de {carp} (el que escribe /cerrar) y corré: cierre-mudanza.py guardado"
    elif paso == "guardado":
        return f"resolvé las sesiones hijas y corré: cierre-mudanza.py hijas"
    elif paso == "hijas":
        return f"corré: cierre-mudanza.py archivar (después: avisale «traspaso listo» a la sucesora y archive_session(\"self\"))"
    elif paso == "archivando":
        return 'mandá «traspaso listo» a la sucesora (send_message), después archive_session("self") y terminá tu respuesta'
    elif paso == "completo":
        return "cierre completo"
    return "paso desconocido"
