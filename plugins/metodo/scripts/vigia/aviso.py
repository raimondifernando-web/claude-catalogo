#!/usr/bin/env python3
"""Hook SessionStart del vigía (plugin `metodo`).

Al abrir una sesión de Claude Code hace dos cosas, en menos de un segundo:

1. Avisa, solo si hay algo: novedades sin revisar, el vigía caído (estado `caido`), que
   no se pudo lanzar, o que lleva más de 9 días sin una corrida con red (alarma de
   hombre muerto: si el detector se rompe o no tiene conexión, el silencio no puede
   parecer «todo bien»). Si hubo un intento en la última hora dice «vigía corriendo»
   en vez de alarmar. Sano y sin novedades → no imprime nada.
2. Si la última corrida completa tiene más de 7 días (o no hubo ninguna) y no hubo un
   intento en las últimas 24 h, lanza `vigia.py --si-toca` DESACOPLADO y vuelve
   enseguida: la sesión no espera la búsqueda.

Apagado: `VIGIA_OFF=1` o el archivo `<config>/vigia/apagado` → sale sin hacer nada.
`<config>` es $CLAUDE_CONFIG_DIR si está definida; si no, ~/.claude.

Código de salida: siempre 0, salvo un caso: si este intérprete es anterior a Python 3.9
sale con 1, para que la cadena de hooks.json (python3 || python || py -3) pruebe el
siguiente. Un código distinto de 0 y de 2 en SessionStart es un error NO bloqueante:
la sesión sigue igual. Si no queda otro intérprete que probar, además avisa
«Vigía necesita Python 3.9+». Escrito para poder correr (y avisar) desde Python 3.6.

Argumento opcional: la posición de este intérprete en la cadena (1, 2 o 3).
"""
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

DIAS_ENTRE_CORRIDAS = 7
HORAS_ESPERA_TRAS_INTENTO = 24
DIAS_ALARMA = 9
HORAS_CORRIENDO = 1
# Intérpretes que prueba hooks.json, en orden.
CADENA = ("python3", "python", "py")


def dir_vigia():
    propia = os.environ.get("CLAUDE_CONFIG_DIR", "").strip()
    base = Path(propia).expanduser() if propia else Path.home() / ".claude"
    return base / "vigia"


def parsear_fecha(valor):
    if not isinstance(valor, str) or not valor:
        return None
    try:
        dt = datetime.strptime(valor.replace("Z", "+00:00")[:25], "%Y-%m-%dT%H:%M:%S%z")
    except ValueError:
        try:
            dt = datetime.fromisoformat(valor.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def iso(dt):
    return dt.isoformat(timespec="seconds")


def apagado():
    if os.environ.get("VIGIA_OFF", "").strip() == "1":
        return True
    return (dir_vigia() / "apagado").exists()


def leer_json(ruta):
    """None si no existe; {} si no es un objeto. Si está roto, levanta la excepción."""
    if not ruta.exists():
        return None
    with open(str(ruta), "r", encoding="utf-8") as f:
        datos = json.load(f)
    return datos if isinstance(datos, dict) else {}


def leer_lanzamientos():
    try:
        return leer_json(dir_vigia() / "lanzamiento.json") or {}
    except Exception:
        return {}


def escribir_lanzamientos(datos):
    try:
        d = dir_vigia()
        d.mkdir(parents=True, exist_ok=True)
        tmp = d / ".lanzamiento.json.tmp-{}".format(os.getpid())
        tmp.write_text(json.dumps(datos), encoding="utf-8")
        os.replace(str(tmp), str(d / "lanzamiento.json"))
    except Exception:
        pass


def ultimo_intento(estado, lanzamientos):
    fechas = [f for f in (parsear_fecha(estado.get("ultimo_intento")), parsear_fecha(lanzamientos.get("ultimo"))) if f]
    return max(fechas) if fechas else None


def debe_lanzar(estado, ahora, intento):
    ultima = parsear_fecha(estado.get("ultima_corrida"))
    if ultima and ahora - ultima < timedelta(days=DIAS_ENTRE_CORRIDAS):
        return False
    if intento and ahora - intento < timedelta(hours=HORAS_ESPERA_TRAS_INTENTO):
        return False
    return True


def lanzar_detector(ahora, lanzamientos):
    """Lanza vigia.py en segundo plano, separado de la sesión. La marca se escribe
    ANTES del Popen (si el lanzamiento falla, la espera de 24 h igual corre) y el
    error, si lo hay, queda anotado para avisarlo."""
    marca = dict(lanzamientos)
    marca["primero"] = lanzamientos.get("primero") or iso(ahora)
    marca["ultimo"] = iso(ahora)
    escribir_lanzamientos(marca)

    script = Path(__file__).resolve().parent / "vigia.py"
    cmd = [sys.executable, str(script), "--si-toca"]
    comunes = dict(
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
        cwd=str(Path.home()),  # no retener la carpeta del plugin (en Windows la bloquearía)
    )
    try:
        if not script.is_file():
            raise OSError("no está vigia.py junto a aviso.py")
        if os.name == "nt":
            # Sin DETACHED_PROCESS: con CREATE_NO_WINDOW no se abre ninguna ventana negra.
            flags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000) | getattr(
                subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200
            )
            breakaway = getattr(subprocess, "CREATE_BREAKAWAY_FROM_JOB", 0x01000000)
            try:
                subprocess.Popen(cmd, creationflags=flags | breakaway, **comunes)
            except OSError:
                # El job del proceso padre no permite salirse: se lanza igual, sin BREAKAWAY.
                subprocess.Popen(cmd, creationflags=flags, **comunes)
        else:
            subprocess.Popen(cmd, start_new_session=True, **comunes)
    except Exception as exc:
        marca["ultimo_error_lanzamiento"] = {"fecha": iso(ahora), "detalle": "{}: {}".format(type(exc).__name__, exc)[:140]}
        escribir_lanzamientos(marca)
        return False
    if "ultimo_error_lanzamiento" in marca:
        del marca["ultimo_error_lanzamiento"]
        escribir_lanzamientos(marca)
    return True


def armar_mensaje(estado, ahora, intento, lanzamientos):
    """(visible, contexto) o None si no hay nada que decir."""
    primer_lanzamiento = parsear_fecha(lanzamientos.get("primero"))
    corriendo = bool(intento and ahora - intento < timedelta(hours=HORAS_CORRIENDO))
    accionables = []
    informativos = []

    error_lanz = lanzamientos.get("ultimo_error_lanzamiento")
    if isinstance(error_lanz, dict):
        accionables.append("⚠️ Vigía: no se pudo lanzar la búsqueda ({})".format(str(error_lanz.get("detalle", ""))[:140]))

    if estado is None:
        # Nunca terminó una corrida. Solo alarma si lleva días así.
        if not accionables and primer_lanzamiento and ahora - primer_lanzamiento > timedelta(days=DIAS_ALARMA) and not corriendo:
            accionables.append("⚠️ Vigía: nunca terminó una corrida (revisá vigia.log)")
    else:
        if estado.get("estado") == "caido":
            err = (estado.get("errores") or ["sin detalle"])[0]
            accionables.append("⚠️ Vigía caído en la última corrida: {}".format(str(err)[:140]))

        # Referencia: la última corrida CON RED (una corrida sin conexión no cuenta).
        ultima = (
            parsear_fecha(estado.get("ultima_corrida_con_red"))
            or parsear_fecha(estado.get("ultima_corrida"))
            or primer_lanzamiento
        )
        if ultima:
            dias = (ahora - ultima).days
            if dias > DIAS_ALARMA:
                if corriendo:
                    informativos.append("🔭 Vigía corriendo (la última búsqueda completa fue hace {} días)".format(dias))
                elif estado.get("estado") != "caido":
                    accionables.append(
                        "⚠️ Vigía sin una búsqueda completa hace {} días (última: {:%Y-%m-%d}; ¿hay conexión?)".format(dias, ultima)
                    )

        novedades = estado.get("novedades") or {}
        nuevas = [k for k, v in novedades.items() if isinstance(v, dict) and v.get("estado") == "nueva"]
        if nuevas:
            accionables.append("🔭 Vigía: {} novedad(es) sin revisar".format(len(nuevas)))
        if estado.get("descubrimiento_pendiente") is True:
            accionables.append("🔭 Vigía: toca la búsqueda mensual de herramientas nuevas")

    if not accionables and not informativos:
        return None
    partes = accionables + informativos
    visible = " · ".join(partes)
    if accionables:
        visible += " — pedile a Claude «revisá las novedades del vigía»"
    contexto = (
        "Aviso del vigía de actualizaciones (plugin metodo): " + " · ".join(partes) + ". "
        + (
            "Al terminar de arrancar, ofrecé revisarlo con la skill `vigia` "
            "(aplica solo lo auditado que no rompe; lo nuevo, lo que rompe o lo riesgoso se pregunta)."
            if accionables
            else "No hace falta hacer nada."
        )
    )
    return visible, contexto


def emitir(mensaje):
    salida = {
        "systemMessage": mensaje[0],
        "hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": mensaje[1]},
    }
    # ASCII puro: la consola de Windows puede no ser UTF-8.
    sys.stdout.write(json.dumps(salida, ensure_ascii=True) + "\n")
    sys.stdout.flush()


def queda_otro_interprete(posicion):
    """¿Hay, más adelante en la cadena de hooks.json, otro intérprete distinto de este?
    Los alias de la Microsoft Store (carpeta WindowsApps) no cuentan."""
    propio = os.path.realpath(sys.executable)
    for nombre in CADENA[posicion:]:
        ruta = shutil.which(nombre)
        if ruta and "windowsapps" not in ruta.lower() and os.path.realpath(ruta) != propio:
            return True
    return False


def python_viejo(posicion):
    """Python < 3.9: el detector no corre. Sale 1 para que la cadena pruebe el
    siguiente intérprete; si no queda ninguno, avisa (una vez por sesión)."""
    if not queda_otro_interprete(posicion):
        emitir((
            "⚠️ Vigía necesita Python 3.9+ (este es {}.{}); la búsqueda de novedades no corre.".format(*sys.version_info[:2]),
            "El vigía de actualizaciones (plugin metodo) no corre porque Python es anterior a 3.9. "
            "Si el usuario pregunta, ver requisitos.md del plugin metodo.",
        ))
    return 1


def principal():
    if apagado():
        return 0
    try:
        posicion = int(sys.argv[1]) if len(sys.argv) > 1 else len(CADENA)
    except ValueError:
        posicion = len(CADENA)
    if sys.version_info < (3, 9):
        return python_viejo(posicion)

    ahora = datetime.now(timezone.utc)
    lanzamientos = leer_lanzamientos()

    mensaje = None
    estado = None
    try:
        estado = leer_json(dir_vigia() / "estado.json")
    except Exception as exc:
        mensaje = (
            "⚠️ Vigía: no pude leer su estado ({}).".format(type(exc).__name__),
            "El estado del vigía de actualizaciones está ilegible: ofrecé revisarlo con la skill `vigia`.",
        )
        estado = {}

    intento = ultimo_intento(estado or {}, lanzamientos)
    try:
        if debe_lanzar(estado or {}, ahora, intento):
            lanzar_detector(ahora, lanzamientos)
            intento = ahora  # recién lanzado: el aviso dice «corriendo», no «sin correr»
            lanzamientos = leer_lanzamientos()
    except Exception:
        pass

    if mensaje is None:
        try:
            mensaje = armar_mensaje(estado, ahora, intento, lanzamientos)
        except Exception as exc:
            mensaje = (
                "⚠️ Vigía: no pude leer su estado ({}).".format(type(exc).__name__),
                "El estado del vigía de actualizaciones está ilegible: ofrecé revisarlo con la skill `vigia`.",
            )
    if mensaje:
        emitir(mensaje)
    return 0


if __name__ == "__main__":
    codigo = 0
    try:
        codigo = principal()
    except BaseException:
        codigo = 0
    sys.exit(codigo)
