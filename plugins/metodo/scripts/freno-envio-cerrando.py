#!/usr/bin/env python3
"""freno-envio-cerrando.py — control de envíos a sesiones en proceso de mudanza.

Disparador: automático (hook PreToolUse del plugin metodo, hooks/hooks.json, sobre SendMessage y la herramienta send_message de la app).
Se apaga con la variable CIERRE_MUDANZA=0 o con el archivo <config de Claude>/metodo/freno-envio-cerrando.apagado.

Por qué existe: si la sesión principal de una carpeta está cerrando (mudanza en curso) y otra sesión intenta
mandarle un mensaje por SendMessage (o por mcp__ccd_session_mgmt__send_message), el mensaje se perdería al
archivarse la sesión vieja. Este hook intercepta esos intentos y los deniega (deny) con un aviso en castellano que
dice dejar una carta en la carpeta (<carpeta>/.claude/cartas/, con `cartas.py dejar`), para que la sesión nueva la lea al arrancar.
Mira solo el destino y el estado de la mudanza: no lee ni guarda el contenido del mensaje.

Falla abierto: cualquier fallo, JSON inválido o excepción anota en hook.log y
deja pasar el mensaje (exit 0 sin imprimir nada), garantizando que nunca se trabe.
"""
import json
import os
import sys
import time

TOPE_LOG_BYTES = 200 * 1024


def _config():
    return os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(os.path.expanduser("~"), ".claude")


def _log(msg):
    """Anota un mensaje en <config de Claude>/state/cierre-mudanza/hook.log con límite de 200 KB."""
    try:
        cfg = _config()
        log_dir = os.path.join(cfg, "state", "cierre-mudanza")
        os.makedirs(log_dir, mode=0o700, exist_ok=True)
        log_file = os.path.join(log_dir, "hook.log")
        linea = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}\n"
        b_linea = linea.encode("utf-8")

        if os.path.isfile(log_file):
            tam = os.path.getsize(log_file)
            if tam + len(b_linea) > TOPE_LOG_BYTES:
                with open(log_file, "rb") as f:
                    contenido = f.read()
                # Truncar al inicio conservando los últimos 100 KB
                mitad = contenido[-(TOPE_LOG_BYTES // 2):]
                nl = mitad.find(b"\n")
                if nl != -1:
                    mitad = mitad[nl + 1:]
                with open(log_file, "wb") as f:
                    f.write(mitad)
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(linea)
    except Exception:
        pass


def main():
    # CIERRE_MUDANZA=0 o el archivo .apagado desactivan el hook (deja pasar siempre)
    if os.environ.get("CIERRE_MUDANZA") == "0" or os.path.exists(os.path.join(_config(), "metodo", "freno-envio-cerrando.apagado")):
        sys.exit(0)

    try:
        AQUI = os.path.dirname(os.path.realpath(__file__))
        if AQUI not in sys.path:
            sys.path.insert(0, AQUI)
        import cartas
        import cierre_estado
        import sesiones_hijas as hs
    except Exception as e:
        _log(f"Error importando módulos desde scripts: {e}")
        sys.exit(0)

    try:
        raw = sys.stdin.read()
        if not raw.strip():
            sys.exit(0)
        data = json.loads(raw)
    except Exception as e:
        _log(f"JSON roto o inválido por stdin: {e}")
        sys.exit(0)

    if not isinstance(data, dict):
        _log("Entrada JSON no es un diccionario")
        sys.exit(0)

    tool_name = data.get("tool_name")
    if tool_name not in ("SendMessage", "mcp__ccd_session_mgmt__send_message"):
        _log(f"Herramienta desconocida para este hook: {tool_name}")
        sys.exit(0)

    tool_input = data.get("tool_input")
    if not isinstance(tool_input, dict):
        _log("tool_input no es un dict")
        sys.exit(0)

    destino = tool_input.get("to") if tool_name == "SendMessage" else (tool_input.get("session_id") or tool_input.get("sessionId"))
    if not destino or not isinstance(destino, str):
        sys.exit(0)

    try:
        ses = hs.cargar()
        if destino == "parent":
            # una hija que le escribe a «parent»: se resuelve por quién la abrió (la sesión que manda es `session_id` = id del CLI)
            yo = next((x for x in ses if data.get("session_id") and data.get("session_id") in (x.get("cliSessionId"), x.get("sessionId"))), None)
            destino = hs.padre_de(yo) if yo else None
        if not destino or not destino.startswith("local_"):
            sys.exit(0)
        carpeta = cierre_estado.destino_congelado(destino, ses)
        if carpeta:
            motivo = (
                f"Esa sesión está cerrando (mudanza en curso). No le escribas a ella: "
                f"la sesión nueva lee las cartas de su carpeta al arrancar. Dejá el mensaje así: {cartas.comando(carpeta, 'una sesión')}"
            )
            salida = {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": motivo,
                }
            }
            print(json.dumps(salida))
            sys.exit(0)
    except Exception as e:
        _log(f"Excepción verificando destino congelado: {e}")
        sys.exit(0)

    sys.exit(0)


if __name__ == "__main__":
    main()
