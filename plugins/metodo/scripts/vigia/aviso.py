#!/usr/bin/env python3
"""Hook SessionStart del vigía (plugin `metodo`).

Al abrir una sesión de Claude Code hace dos cosas, en menos de un segundo:

1. Avisa, solo si hay algo: novedades sin revisar, el vigía caído (estado `caido`),
   o sin correr hace más de 9 días (alarma de hombre muerto: si el detector se rompe,
   el silencio no puede parecer «todo bien»). Si hubo un intento en la última hora dice
   «vigía corriendo» en vez de alarmar. Sano y sin novedades → no imprime nada.
2. Si la última corrida completa tiene más de 7 días (o no hubo ninguna) y no hubo un
   intento en las últimas 24 h, lanza `vigia.py --si-toca` DESACOPLADO y vuelve
   enseguida: la sesión no espera la búsqueda.

Apagado: `VIGIA_OFF=1` o el archivo `~/.claude/vigia/apagado` → sale sin hacer nada.
Nunca falla la sesión: todo va en try/except y siempre sale con código 0.

Escrito para correr hasta con Python 3.6 (el detector necesita 3.9: si el intérprete
es más viejo, avisa pero no lanza nada).
"""
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

DIAS_ENTRE_CORRIDAS = 7
HORAS_ESPERA_TRAS_INTENTO = 24
DIAS_ALARMA = 9
HORAS_CORRIENDO = 1


def dir_vigia():
    return Path.home() / ".claude" / "vigia"


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


def apagado():
    if os.environ.get("VIGIA_OFF", "").strip() == "1":
        return True
    return (dir_vigia() / "apagado").exists()


def leer_json(ruta):
    """None si no existe; {} si está ilegible (se avisa aparte)."""
    if not ruta.exists():
        return None
    with open(str(ruta), "r", encoding="utf-8") as f:
        datos = json.load(f)
    return datos if isinstance(datos, dict) else {}


def leer_lanzamientos():
    try:
        datos = leer_json(dir_vigia() / "lanzamiento.json") or {}
    except Exception:
        datos = {}
    return parsear_fecha(datos.get("primero")), parsear_fecha(datos.get("ultimo"))


def ultimo_intento(estado, ultimo_lanzamiento):
    fechas = [f for f in (parsear_fecha(estado.get("ultimo_intento")), ultimo_lanzamiento) if f]
    return max(fechas) if fechas else None


def debe_lanzar(estado, ahora, intento):
    ultima = parsear_fecha(estado.get("ultima_corrida"))
    if ultima and ahora - ultima < timedelta(days=DIAS_ENTRE_CORRIDAS):
        return False
    if intento and ahora - intento < timedelta(hours=HORAS_ESPERA_TRAS_INTENTO):
        return False
    return True


def lanzar_detector(ahora, primero):
    """Lanza vigia.py en segundo plano, separado de la sesión, y anota el lanzamiento."""
    script = Path(__file__).resolve().parent / "vigia.py"
    if not script.is_file() or sys.version_info < (3, 9):
        return False
    cmd = [sys.executable, str(script), "--si-toca"]
    comunes = dict(
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
        cwd=str(Path.home()),  # no retener la carpeta del plugin (en Windows la bloquearía)
    )
    if os.name == "nt":
        flags = (
            getattr(subprocess, "DETACHED_PROCESS", 0x00000008)
            | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200)
            | getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
        )
        breakaway = getattr(subprocess, "CREATE_BREAKAWAY_FROM_JOB", 0x01000000)
        try:
            subprocess.Popen(cmd, creationflags=flags | breakaway, **comunes)
        except OSError:
            # El job del proceso padre no permite salirse: se lanza igual, sin BREAKAWAY.
            subprocess.Popen(cmd, creationflags=flags, **comunes)
    else:
        subprocess.Popen(cmd, start_new_session=True, **comunes)

    try:
        d = dir_vigia()
        d.mkdir(parents=True, exist_ok=True)
        marca = {"primero": (primero or ahora).isoformat(timespec="seconds"), "ultimo": ahora.isoformat(timespec="seconds")}
        tmp = d / ".lanzamiento.json.tmp-{}".format(os.getpid())
        tmp.write_text(json.dumps(marca), encoding="utf-8")
        os.replace(str(tmp), str(d / "lanzamiento.json"))
    except Exception:
        pass
    return True


def armar_mensaje(estado, ahora, intento, primer_lanzamiento):
    """(visible, contexto) o None si no hay nada que decir."""
    if estado is None:
        # Nunca terminó una corrida. Solo alarma si lleva días así.
        if primer_lanzamiento and ahora - primer_lanzamiento > timedelta(days=DIAS_ALARMA):
            if intento and ahora - intento < timedelta(hours=HORAS_CORRIENDO):
                return None
            aviso = "⚠️ Vigía: nunca terminó una corrida (revisá ~/.claude/vigia/vigia.log)"
            return aviso, "Aviso del vigía de actualizaciones: " + aviso + ". Ofrecé revisarlo con la skill `vigia`."
        return None

    accionables = []
    informativos = []

    if estado.get("estado") == "caido":
        err = (estado.get("errores") or ["sin detalle"])[0]
        accionables.append("⚠️ Vigía caído en la última corrida: {}".format(str(err)[:140]))

    ultima = parsear_fecha(estado.get("ultima_corrida")) or primer_lanzamiento
    if ultima:
        dias = (ahora - ultima).days
        if dias > DIAS_ALARMA:
            if intento and ahora - intento < timedelta(hours=HORAS_CORRIENDO):
                informativos.append("🔭 Vigía corriendo (la última búsqueda completa fue hace {} días)".format(dias))
            elif estado.get("estado") != "caido":
                accionables.append("⚠️ Vigía sin correr hace {} días (última: {:%Y-%m-%d})".format(dias, ultima))

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
            "(nunca aplicar nada sin el sí del usuario)."
            if accionables
            else "No hace falta hacer nada."
        )
    )
    return visible, contexto


def principal():
    if apagado():
        return
    ahora = datetime.now(timezone.utc)
    primero, ultimo = leer_lanzamientos()

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

    intento = ultimo_intento(estado or {}, ultimo)
    try:
        if debe_lanzar(estado or {}, ahora, intento) and lanzar_detector(ahora, primero):
            intento = ahora  # recién lanzado: el aviso dice «corriendo», no «sin correr»
            primero = primero or ahora
    except Exception:
        pass

    if mensaje is None:
        try:
            mensaje = armar_mensaje(estado, ahora, intento, primero)
        except Exception as exc:
            mensaje = (
                "⚠️ Vigía: no pude leer su estado ({}).".format(type(exc).__name__),
                "El estado del vigía de actualizaciones está ilegible: ofrecé revisarlo con la skill `vigia`.",
            )

    if mensaje:
        salida = {
            "systemMessage": mensaje[0],
            "hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": mensaje[1]},
        }
        # ASCII puro: la consola de Windows puede no ser UTF-8.
        sys.stdout.write(json.dumps(salida, ensure_ascii=True) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    try:
        principal()
    except BaseException:
        pass
    sys.exit(0)
