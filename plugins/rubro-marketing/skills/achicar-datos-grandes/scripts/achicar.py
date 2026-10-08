#!/usr/bin/env python3
"""Achica un archivo de datos grandes (JSON, tabla, log) SIN perder nada.

Uso:  achicar.py <archivo> [--salida <archivo>]
Escribe el resultado en --salida (o a stdout) y un resumen por stderr.
Usa Headroom en modo `densify`: solo recodifica (p. ej. JSON -> tabla); si no puede
probar que es idéntico, devuelve el original. Nunca borra filas ni deja marcadores.
Si Headroom no está instalado, corre scripts/instalar.sh primero.
"""
import os, sys, json, argparse, subprocess

VENV_PY = os.path.expanduser("~/.cache/headroom/venv/bin/python")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("archivo")
    ap.add_argument("--salida")
    a = ap.parse_args()
    # Telemetría apagada y sin conexiones propias, siempre. Se relanza dentro del entorno aislado.
    env = dict(os.environ, HEADROOM_BEACON="off", HEADROOM_OFFLINE="true", ACHICAR_DENTRO="1")
    if not os.environ.get("ACHICAR_DENTRO"):
        if not os.path.exists(VENV_PY):
            sys.exit("Headroom no está instalado. Corré: bash " + os.path.join(os.path.dirname(__file__), "instalar.sh") + "  ✗")
        sys.exit(subprocess.call([VENV_PY, "-I", os.path.abspath(__file__)] + sys.argv[1:], env=env))
    from headroom import densify
    data = open(a.archivo, encoding="utf-8").read()
    prefijo, cuerpo, sufijo = "", data, ""
    try:  # {"data": [filas...], "paging": ...}: se achica la lista y el resto queda tal cual
        j = json.loads(data)
        if isinstance(j, dict):
            listas = [k for k, v in j.items() if isinstance(v, list) and len(v) > 20 and all(isinstance(x, dict) for x in v)]
            if len(listas) == 1:
                k = listas[0]
                resto = {x: y for x, y in j.items() if x != k}
                prefijo = f'[campo "{k}" abajo, formato compacto; resto: {json.dumps(resto, ensure_ascii=False)}]\n'
                cuerpo = json.dumps(j[k], ensure_ascii=False)
    except ValueError:
        pass
    msgs = [{"role": "user", "content": "datos"}, {"role": "tool", "tool_call_id": "x", "content": cuerpo}]
    r = densify(msgs, protect_recent=0)
    out = prefijo + next((m["content"] for m in r.messages if m.get("role") == "tool"), cuerpo)
    cuerpo_out = out[len(prefijo):]
    if cuerpo_out.startswith('"'):  # Headroom lo devuelve como texto JSON escapado: se desescapa para leerlo
        try:
            out = prefijo + json.loads(cuerpo_out)
        except ValueError:
            pass
    if "<<ccr:" in out:  # no debería pasar en modo sin pérdida; si pasa, no se usa
        out = data
        print("AVISO: apareció un marcador de recorte; se devuelve el original.", file=sys.stderr)
    if a.salida:
        open(a.salida, "w", encoding="utf-8").write(out)
    else:
        sys.stdout.write(out)
    print(f"tokens {r.tokens_before} -> {r.tokens_after} (ahorro {100*(1-r.tokens_after/max(r.tokens_before,1)):.0f}%) · idéntico: {r.lossless} · revertidos: {r.reverted_messages}", file=sys.stderr)

main()
