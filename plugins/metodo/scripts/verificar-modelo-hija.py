#!/usr/bin/env python3
"""Hook PostToolUse de start_session: cuando se abre una sesión hija pidiendo un `model`, deja en el contexto la orden
exacta de comprobarlo y corregirlo. Motivo: start_session solo respeta un modelo igual o más barato que el de la sesión
que la abre; uno más caro se ignora EN SILENCIO y la hija arranca en el modelo de la madre (2026-10-17: pedida en Opus,
arrancó en Sonnet y gastó un turno equivocado). No hace falta saber el modelo de la madre: se verifica siempre que se pidió uno.
Nunca bloquea ni decide permisos; si algo falla, calla.
Disparador: automático (hook PostToolUse del plugin metodo, hooks/hooks.json, matcher mcp__ccd_session__start_session)."""
import json
import re
import sys

MODELO = re.compile(r"^[A-Za-z0-9._\[\]-]{1,64}$")


def mensaje(entrada):
    ti = entrada.get("tool_input")
    if not isinstance(ti, dict):
        return ""
    modelo = str(ti.get("model") or "").strip()
    if not modelo or not MODELO.match(modelo):
        return ""
    return (f"Pediste el modelo «{modelo}» para la sesión hija. start_session ignora en silencio un modelo más caro que el de esta sesión. "
            f"AHORA, antes de seguir: llamá get_session con el id que devolvió start_session; si su `model` no es «{modelo}», "
            f"llamá set_session_model(ese id, «{modelo}») y volvé a verificar con get_session (rige desde el próximo turno de la hija, "
            "así que hacelo antes de que termine el primero). No informes la hija como abierta hasta que el modelo coincida.")


def main():
    try:
        if sys.stdin is None or sys.stdin.isatty():
            return 0
        crudo = getattr(sys.stdin, "buffer", None)
        texto = crudo.read(1000000).decode("utf-8", "replace") if crudo else sys.stdin.read(1000000)
        entrada = json.loads(texto) if texto.strip() else {}
        if not isinstance(entrada, dict) or not str(entrada.get("tool_name", "")).endswith("start_session"):
            return 0
        msg = mensaje(entrada)
        if msg:
            print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": msg}}))
    except BaseException:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
