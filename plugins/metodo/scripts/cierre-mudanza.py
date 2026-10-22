#!/usr/bin/env python3
"""cierre-mudanza — mudanza ordenada de la sesión de una carpeta (<carpeta>/.claude/cerrando.json).

Disparador: encadenado — lo corre /metodo:cerrar (Paso A al empezar y paso 10 al terminar); si el cierre se corta, /metodo:arrancar
y `cierre-mudanza.py estado` dicen en qué paso quedó. Se apaga con la variable CIERRE_MUDANZA=0 (el control de envíos deja pasar todo).

Por qué existe: la sesión principal de una carpeta es un puesto fijo, pero la app la ata a una sesión que tiene que cerrar cada tanto.
Cerrar bien es una mudanza con orden fijo, en una sola vuelta: congelar (desde ahí quien le escriba a la sesión que se va recibe el aviso
de dejar una carta en la carpeta) → abrir la sesión nueva y soltarla de esta → guardar → resolver las sesiones hijas → archivarse.
Este programa comprueba cada paso contra los datos que la app guarda en disco y avanza el estado; cada subcomando imprime ✓ o ✗
y sale con 0 (éxito) o 1 (fallo); los errores de uso salen con 64.

Uso:
  cierre-mudanza.py congelar [carpeta] [--vieja <id de esta sesión>]
  cierre-mudanza.py abierta <id_nuevo> [carpeta]
  cierre-mudanza.py guardado [carpeta]
  cierre-mudanza.py hijas [carpeta]
  cierre-mudanza.py archivar [carpeta]
  cierre-mudanza.py estado [carpeta]
  cierre-mudanza.py retomar [carpeta]      (igual que estado)
  cierre-mudanza.py cancelar [carpeta]     (descongela una mudanza que no pudo seguir)
"""
import os
import sys

DIR_SCRIPTS = os.path.dirname(os.path.realpath(__file__))
if DIR_SCRIPTS not in sys.path:
    sys.path.insert(0, DIR_SCRIPTS)

import cierre_estado  # noqa: E402
import sesiones_hijas as hs  # noqa: E402

EX_USO = 64

# Windows: la consola usa cp1252 y los ✓/✗ y acentos hacían caer el script; se fuerza UTF-8.
for _flujo in (sys.stdin, sys.stdout, sys.stderr):
    try:
        _flujo.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def uso(msg=None):
    if msg:
        sys.stderr.write("Error: {}\n".format(msg))
    sys.stderr.write(
        "Uso: cierre-mudanza.py <congelar|abierta|guardado|hijas|archivar|estado|retomar|cancelar> [argumentos...]\n"
    )
    sys.exit(EX_USO)


def sacar_opcion(args, nombre):
    """(valor, resto): saca `--nombre valor` de la lista de argumentos."""
    if nombre in args:
        i = args.index(nombre)
        if i + 1 < len(args):
            return args[i + 1], args[:i] + args[i + 2:]
        uso("a {} le falta el valor".format(nombre))
    return None, args


def terminar(ok, motivo):
    print(("✓ " if ok else "✗ ") + motivo)
    sys.exit(0 if ok else 1)


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    if not argv:
        uso()

    cmd = argv[0]
    args = argv[1:]

    if cmd == "congelar":
        vieja_id, args = sacar_opcion(args, "--vieja")
        carpeta = os.path.abspath(args[0]) if args else os.getcwd()
        ses = hs.cargar()
        if not vieja_id:
            vieja = hs.mi_sesion(ses)
            vieja_id = vieja.get("sessionId") if vieja else None
        if not vieja_id:
            print("✗ No pude saber cuál es esta sesión: pasá su id con --vieja <id> (lo da get_session(\"self\"))")
            sys.exit(1)
        try:
            d = cierre_estado.congelar(carpeta, vieja_id, ses)
        except ValueError as e:
            print("✗ {}".format(e))
            sys.exit(1)
        print("✓ Cierre congelado para {} en {}".format(vieja_id, d["carpeta"]))
        sys.exit(0)

    elif cmd == "abierta":
        if not args:
            uso("falta el ID de la sesión sucesora")
        id_nuevo = args[0]
        carpeta = os.path.abspath(args[1]) if len(args) > 1 else os.getcwd()
        ok, motivo = cierre_estado.marcar_abierta(carpeta, id_nuevo, hs.cargar())
        terminar(ok, motivo)

    elif cmd == "guardado":
        carpeta = os.path.abspath(args[0]) if args else os.getcwd()
        ok, motivo = cierre_estado.marcar_guardado(carpeta)
        terminar(ok, motivo)

    elif cmd == "hijas":
        carpeta = os.path.abspath(args[0]) if args else os.getcwd()
        ses = hs.cargar()
        for h in cierre_estado.hijas_pendientes(carpeta, ses):
            print("• {}".format(h["accion"]))
        ok, motivo = cierre_estado.marcar_hijas(carpeta, ses)
        terminar(ok, motivo)

    elif cmd == "archivar":
        carpeta = os.path.abspath(args[0]) if args else os.getcwd()
        ok, motivo = cierre_estado.marcar_archivando(carpeta)
        terminar(ok, motivo)

    elif cmd == "cancelar":
        carpeta = os.path.abspath(args[0]) if args else os.getcwd()
        if cierre_estado.cancelar(carpeta):
            print("✓ Mudanza cancelada: la carpeta ya no está congelada (los mensajes a la sesión vieja vuelven a pasar)")
        else:
            print("✓ No había mudanza en curso")
        sys.exit(0)

    elif cmd == "estado" or cmd == "retomar":
        carpeta = os.path.abspath(args[0]) if args else os.getcwd()
        ses = hs.cargar()
        cierre_estado.completar(carpeta, ses)  # si la vieja ya se archivó, lo cierra
        d = cierre_estado.leer(carpeta)
        if not d or not cierre_estado.vigente(d):
            print("Sin cierre en curso.")
            sys.exit(0)
        print("Paso actual: {}. Siguiente: {}".format(d["paso"], cierre_estado.siguiente(d, ses)))
        sys.exit(0)

    else:
        uso("subcomando desconocido '{}'".format(cmd))


if __name__ == "__main__":
    main()
