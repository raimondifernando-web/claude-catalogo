#!/usr/bin/env python3
"""estructura_consejo.py — de un hallazgo mecánico del revisor a un consejo pensado.

Disparador: encadenado — lo llama estructura.py en el modo `revisar --aviso` (aviso de apertura de sesión, hooks.json),
en `estructura.py brief` y en `estructura.py descartar`. No se corre a mano.

Un hallazgo («CLAUDE.md pasó 4 líneas del límite») no dice si vale la pena arreglarlo. Este módulo le agrega tres cosas:
  qué encontró · cuánto cuesta dejarlo así · el arreglo que conviene en ESE caso,
y decide la acción: «sesion» (vale una sesión secundaria) · «al_pasar» (2 minutos si ya estás en ese archivo; no vale una
sesión) · «nada» (cuesta más arreglarlo de lo que se gana: no manda hacer nada).
También recuerda lo ya mostrado o decidido, para no repetir el mismo aviso todos los días, y ordena por lo que más rinde.

No usa IA ni la red. Solo LEE las carpetas; lo único que escribe es su archivo de memoria (`avisos-vistos.json`) en la
carpeta de estado del plugin. Sin POSIX: pathlib puro (Windows).
"""
from datetime import date
import json
import os
from pathlib import Path
import re
import tempfile

TOKENS_POR_LINEA = 12          # una línea de Markdown pesa unos 12 tokens
UMBRAL_R3_NADA = 260           # hasta acá (50-60 líneas de más) no vale tocar nada
DIAS_ENTRE_REPETICIONES = 7    # el mismo aviso no vuelve antes de una semana
MAX_VECES = 3                  # y no se muestra más de tres veces si nadie lo atiende
DIAS_DESCARTADO = 180          # lo decidido «no hacer» vuelve a preguntar recién a los 6 meses (o si empeora)
CARPETAS_AJENAS = {"sandbox", "_archivo", ".copias-de-trabajo", "node_modules"}   # copias de terceros o viejas: no son de nadie
MAX_CONSEJOS = 3               # como mucho tres consejos completos por aviso

_NUM = re.compile(r"\d+")


def _n(patron: str, msg: str, defecto: int = 0) -> int:
    m = re.search(patron, msg)
    return int(m.group(1)) if m else defecto


def _miles(n: int) -> str:
    return f"{n:,}".replace(",", ".")


def consejo(r_id: str, msg: str, ctx: dict) -> dict:
    """Consejo para un hallazgo de tipo «aviso». ctx: {"codigo": bool, "nivel": str}.
    Devuelve {accion, que, cuesta, conviene, hecho, rinde, medida}. Nunca falla: lo desconocido es «al_pasar»."""
    codigo = bool(ctx.get("codigo"))
    que, cuesta, conviene, hecho = msg, "poco, pero no es nada.", "revisarlo cuando abras ese archivo por otra razón.", "el aviso ya no sale."
    accion, rinde, medida = "al_pasar", 20, 0

    if r_id == "R3":
        n = _n(r"\((\d+) líneas\)", msg, 200)
        extra = max(n - 199, 1)
        que = f"CLAUDE.md tiene {n} líneas ({extra} de más sobre la guía de 200)"
        cuesta = (f"unos {_miles(n * TOKENS_POR_LINEA)} tokens en cada sesión que se abre acá (cada línea de más suma ~{TOKENS_POR_LINEA}); "
                  "sobre el límite no se rompe nada, solo se carga de más y las reglas del fondo pesan menos.")
        medida = n
        if n < UMBRAL_R3_NADA:
            accion = "nada"
            conviene = (f"nada: {extra} líneas de más cuestan menos que abrir una sesión para sacarlas. Si algún día tocás el archivo, "
                        "borrá lo repetido o viejo que veas.")
        else:
            accion, rinde = "sesion", min(95, 30 + extra // 4)
            conviene = ("mirá si hay algo repetido, viejo o contradictorio para sacar (lo que ya dice otro archivo, lo que el repositorio "
                        "ya muestra solo, datos que cambian). Solo si queda un bloque que aplica a un tema o carpeta puntual, "
                        "pasalo a `.claude/rules/` con `paths:` (así se carga solo cuando se toca eso). Nunca «mover por mover».")
            hecho = "menos de 200 líneas SIN perder ninguna regla vigente (se compara el antes y el después), o motivo escrito de por qué queda así."
    elif r_id == "R12":
        faltan = msg.split(":", 1)[-1].strip()
        que = f"faltan documentos vivos ({faltan})"
        if codigo:
            accion, rinde = "sesion", 35
            cuesta = ("cada sesión nueva tiene que redescubrir qué se decidió y por qué (lectura de código, preguntas repetidas); "
                      "en un proyecto con código eso se paga seguido.")
            conviene = ("crear SOLO los que se vayan a usar y con contenido real: `docs/PRD.md` si hay producto que describir, "
                        "`docs/decisiones.md` si ya hay decisiones tomadas, `docs/planes/` recién cuando haya un plan. "
                        "Nada de plantillas vacías.")
            hecho = "cada documento creado tiene contenido real; los que no hacen falta quedan sin crear y se anota por qué (`estructura.py descartar`)."
        else:
            accion = "nada"
            cuesta = "ninguno que se note: sin código ni historia propia, un documento vacío es un archivo más que nadie lee."
            conviene = "nada. Se crean cuando la carpeta tenga algo que registrar (un producto, una decisión, un plan)."
    elif r_id == "R16":
        que = "docs/PRD.md o docs/decisiones.md siguen siendo solo la plantilla"
        if codigo:
            accion, rinde = "sesion", 25
            cuesta = "un archivo que parece completo y está vacío: la sesión lo lee, no encuentra nada y pierde tiempo."
            conviene = "completarlo con lo que de verdad se sabe (nunca inventar), o borrarlo si todavía no hay nada que decir."
            hecho = "cada plantilla está completada con datos reales o eliminada."
        else:
            accion = "nada"
            cuesta = "ninguno: la carpeta no tiene código ni historia que documentar todavía."
            conviene = "nada por ahora."
    elif r_id == "R13":
        n = _n(r"cita (\d+) ruta", msg, 1)
        que = msg.replace("CLAUDE.md cita", "el CLAUDE.md cita")
        medida = n
        cuesta = ("la sesión que siga esa ruta la busca, no la encuentra y gasta una búsqueda (unos miles de tokens) o trabaja sobre "
                  "el archivo equivocado.")
        conviene = ("escribir la ruta completa (`~/Proyectos/<carpeta>/…`) si el archivo vive en otra carpeta, o sacar la mención si "
                    "era historia. Lo decide quien lleva la carpeta.")
        if n <= 2:
            accion, rinde = "al_pasar", 15
            conviene += " Son pocas: no vale una sesión aparte, corregilas cuando abras ese archivo."
        else:
            accion, rinde = "sesion", 40 + min(n, 20)
            hecho = "las rutas del aviso existen o ya no están mencionadas."
    elif r_id == "R14":
        n = _n(r"tiene (\d+) conteo", msg, 1)
        que = msg.replace("CLAUDE.md tiene", "el CLAUDE.md tiene")
        medida = n
        cuesta = "cuando el número queda viejo, la sesión lo toma por cierto (Mand. I: «verificar antes de afirmar»)."
        if n <= 2:
            accion = "nada"
            conviene = "nada por ahora: son pocos y se desactualizan despacio. Si uno ya está mal, cambialo por el comando que lo cuenta."
        else:
            accion, rinde = "al_pasar", 25
            conviene = "reemplazar cada número por el comando que lo cuenta (por ejemplo `ls … | wc -l`)."
    elif r_id == "R15":
        que = msg
        accion, rinde = "sesion", 85
        cuesta = "una sesión puede intentar delegar en un agente que no existe y quedarse sin ejecutar ese trabajo."
        conviene = ("corregir el nombre (lo más común: un typo o un agente renombrado). Crear el agente solo si de verdad falta, "
                    "con la skill `agent-creator`, nunca a mano.")
        hecho = "todos los `pm-…` que nombra el CLAUDE.md existen."
    elif r_id == "R17":
        que = msg
        rinde = 30
        cuesta = "el panel de pendientes no puede leer esas filas: parecen no existir."
        conviene = "corregir las filas que indica el aviso (`pendientes-check.py` las marca una por una)."
    elif r_id == "R18":
        que = msg
        if "Worktree" in msg or "Rama" in msg:
            rinde = 60
            cuesta = "la próxima sesión puede arrancar en la carpeta o rama equivocada."
            conviene = "se arregla solo en el próximo `/cerrar`. Si la rama está mal y no vas a cerrar pronto, corregí esa línea a mano."
        else:
            accion = "nada"
            cuesta = "bajo: el texto de reanudación queda viejo, pero el próximo `/cerrar` lo reescribe entero."
            conviene = "nada: se renueva solo en el próximo cierre. No hace falta una sesión."
    elif r_id == "R19":
        que = msg
        rinde = 35
        if "cáscara" in msg:
            cuesta = "el PM casi no dice cómo trabajar: la sesión improvisa en vez de seguir el método de la carpeta."
            conviene = ("el cuerpo del PM vive en `~/.claude/agents/` y lo mantiene Tech con `agent-creator`: no lo reescribas desde esta "
                        "carpeta; avisale a Tech.")
        else:
            cuesta = "una sesión no sabe a quién delegar el trabajo de esta carpeta."
            conviene = "una línea en el CLAUDE.md que nombre al PM (`pm-…`). Dos minutos, hacela cuando abras el archivo."
    elif r_id == "R20":
        que = msg
        cuesta = "el PM arranca sin una skill que cree tener: trabaja sin ese método sin avisar."
        conviene = "quitar la skill que no existe del encabezado del PM, o instalarla (lo hace Tech: el PM vive en `~/.claude/agents/`)."
    elif r_id == "R21":
        que = msg
        accion, rinde = "sesion", 45
        cuesta = "la sesión cree tener un conector que no está habilitado y falla en el momento en que lo necesita."
        conviene = ("decidir cuál es la verdad: si se usa, configurarlo y habilitarlo (configurar ≠ habilitar); si no se usa por MCP, "
                    "aclararlo en el CLAUDE.md («se usa por script/API»). Sin llaves en el chat.")
        hecho = "cada conector que cita el CLAUDE.md está habilitado o aclarado como «por script/API»."
    elif r_id == "R22":
        que = "el archivo de permisos y paquetes de la caja (`.claude/settings.json`) no está subido a GitHub"
        accion, rinde = "sesion", 55
        cuesta = ("existe solo en esta Mac: otra persona, la nube o una Mac nueva arrancan esta carpeta sin sus permisos ni su paquete, "
                  "y R10 (activar el paquete de arriba) no se cumple donde importa.")
        conviene = ("agregar la línea `!.claude/settings.json` al `.gitignore` de la caja (le gana al ignore global de esta Mac), "
                    "mirar que el archivo no tenga claves (en `env`) y subirlo. No hace falta tocar la configuración global.")
        hecho = "`git ls-files .claude/settings.json` lo muestra, sin claves adentro."
    elif r_id == "R23":
        que = msg
        accion, rinde = "sesion", 45
        cuesta = ("quien abre la caja (otra persona, la nube, una sesión nueva) no encuentra cómo se levanta, cómo está armada ni qué claves necesita, "
                  "y lo redescubre leyendo código en cada sesión.")
        conviene = ("escribir SOLO los que se vayan a usar y con contenido real, a partir del código (nunca inventar): `estructura.py arreglar --si` "
                    "deja los esqueletos con instrucciones. Si algo no aplica (no hay pantallas, no usa claves), anotarlo con `estructura.py descartar`.")
        hecho = "cada archivo tiene contenido real o se anotó por qué no hace falta."
    elif r_id == "R24":
        que = msg
        accion, rinde = "al_pasar", 30
        cuesta = "sin pruebas, un cambio se rompe en silencio; sin el comando, cada sesión busca cómo se corren."
        conviene = "una línea en el README o el CLAUDE.md con el comando que las corre. Si no hay pruebas, empezar por lo que más plata o datos mueve."
    elif r_id == "R25":
        que = msg
        accion, rinde = "sesion", 40
        cuesta = "si algo se cae de noche, nadie sabe dónde corre, cómo se vuelve atrás ni dónde está el respaldo; se paga en horas y a veces en datos."
        conviene = "completar `docs/operacion.md` con lo que de verdad hay (dónde corre, cómo se despliega y se vuelve atrás, nombres de claves y vencimientos, dónde están los datos y la última restauración probada). Sin valores de claves."
        hecho = "las cuatro partes están y dicen cosas verificadas."
    elif r_id == "R26":
        que = msg
        accion, rinde = "sesion", 50
        cuesta = "una caja que corre en internet o usa claves sin revisión reciente acumula riesgo sin que nadie lo vea; los escáneres de secretos de GitHub no son gratis en repos privados."
        conviene = "correr el chequeo de seguridad de la caja y guardar el informe (sin valores de claves) en `.claude/security-checks/AAAA-MM-DD.md`."
        hecho = "hay un informe de menos de 90 días."
    elif r_id == "R27":
        que = msg
        accion, rinde = "al_pasar", 15
        cuesta = "nadie sabe quién lleva la caja, si sigue viva ni dónde está su respaldo; se descubre tarde, cuando hace falta."
        conviene = "agregar las líneas faltantes (Dueño, Estado, Respaldo, Última revisión) la próxima vez que abras el PRD."
    elif r_id == "R28":
        que = msg
        accion, rinde = "al_pasar", 20
        cuesta = "un esquema viejo parece verdadero y no lo es: la sesión decide sobre datos que ya cambiaron."
        conviene = "volver a generarlo con el comando que dice el LEEME (el esquema sale del código, nunca a mano)."
    elif r_id == "R7":
        que = msg
        cuesta = "quien clone la carpeta no sabe qué variables necesita."
        conviene = "`estructura.py arreglar` crea el `.env.example` con los nombres (nunca los valores)."
    elif r_id == "R10":
        que = msg
        cuesta = "la carpeta no recibe el paquete de arriba: trabaja sin esas skills."
        conviene = "activar el paquete en `.claude/settings.json`."

    return dict(accion=accion, que=que, cuesta=cuesta, conviene=conviene, hecho=hecho, rinde=rinde, medida=medida)


# ------------------------------------------------------------------ memoria: no repetir lo ya mostrado o decidido
def archivo_memoria() -> Path:
    base = os.environ.get("CLAUDE_PLUGIN_DATA")
    return (Path(base) if base else Path.home() / ".claude" / "metodo-estado") / "avisos-vistos.json"


def cargar() -> dict:
    try:
        d = json.loads(archivo_memoria().read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def guardar(d: dict):
    """Escritura atómica (varias sesiones a la vez no dejan el archivo a medio escribir)."""
    ruta = archivo_memoria()
    try:
        ruta.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=str(ruta.parent), prefix=".avisos-", suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=1)
        os.replace(tmp, ruta)
    except OSError:
        pass


def _dias(desde: str, hoy: date) -> int:
    try:
        return (hoy - date.fromisoformat(desde)).days
    except (TypeError, ValueError):
        return 10**6


def empeoro(medida: int, antes: int) -> bool:
    """Creció de forma que justifica volver a avisar (más de la mitad y al menos 40 de diferencia)."""
    return bool(antes) and medida > antes * 1.5 and medida - antes >= 40


def toca_mostrar(clave: str, medida: int, memoria: dict, hoy: date) -> bool:
    e = memoria.get(clave)
    if not e:
        return True
    if empeoro(medida, e.get("medida", 0)):
        return True
    if e.get("descartado"):
        return _dias(e["descartado"], hoy) > DIAS_DESCARTADO
    if e.get("veces", 0) >= MAX_VECES:
        return False
    return _dias(e.get("visto"), hoy) >= DIAS_ENTRE_REPETICIONES


def anotar_visto(clave: str, medida: int, memoria: dict, hoy: date):
    e = memoria.setdefault(clave, {})
    e["veces"] = e.get("veces", 0) + 1 if not (e.get("descartado") or empeoro(medida, e.get("medida", 0))) else 1
    e["visto"] = hoy.isoformat()
    e["medida"] = medida
    e.pop("descartado", None)


def descartar(clave: str, hoy: date = None) -> bool:
    """Deja anotado «decidí no hacerlo». Devuelve False si no se pudo."""
    if not clave or ":" not in clave:
        return False
    hoy = hoy or date.today()
    memoria = cargar()
    e = memoria.setdefault(clave, {})
    e["descartado"] = hoy.isoformat()
    e.setdefault("medida", 0)
    guardar(memoria)
    return True


def clave_de(r_id: str, nombre: str) -> str:
    return f"{r_id}:{nombre}"


# ------------------------------------------------------------------ texto del aviso y del brief
def lineas_consejo(clave: str, nombre: str, c: dict) -> list:
    return [f"• [{clave}] {nombre}: {c['que']}.",
            f"    Cuesta dejarlo así: {c['cuesta']}",
            f"    Conviene: {c['conviene']}"]


def armar_brief(carpeta_nombre: str, ruta: str, consejos: list, errores: list) -> str:
    """Texto listo para pegar en `start_session` (tarjeta «own_initiative») de una sesión secundaria."""
    l = [f"Brief — ordenar la carpeta «{carpeta_nombre}» ({ruta})",
         "Objetivo: dejarla más liviana y sin información rota. Es la lista que armó el revisor con su costo y su arreglo; "
         "si algo cuesta más de lo que rinde, decilo y NO lo hagas (`estructura.py descartar <clave>` lo deja anotado).", ""]
    n = 0
    for e in errores:
        n += 1
        l.append(f"{n}. FALTA (obligatorio): {e}")
    for clave, c in consejos:
        n += 1
        l += [f"{n}. [{clave}] {c['que']}.", f"   Cuesta dejarlo así: {c['cuesta']}", f"   Qué conviene: {c['conviene']}"]
        if c.get("hecho"):
            l.append(f"   Hecho cuando: {c['hecho']}")
    l += ["", "No toques: nada fuera de esta carpeta; sin push; sin mover ni borrar carpetas; commit solo de lo tuyo por pathspec.",
          "Al terminar: corré `estructura.py revisar` en la carpeta y contá en 3 líneas qué arreglaste, qué decidiste no hacer y por qué."]
    return "\n".join(l)
