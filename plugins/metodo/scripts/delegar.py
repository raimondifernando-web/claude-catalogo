#!/usr/bin/env python3
"""Delegador de tareas a IAs del plugin `metodo`.

Elige la mejor IA según el radar de modelos (en modo delegar, priorizando Codex y Antigravity sobre Claude Code)
y ejecuta la tarea directamente en el repositorio indicado.

Uso:
    delegar.py <categoria> <repo> <pedido> [--revisar] [--sensible] [--dry-run]

Argumentos:
    categoria     Categoría del radar (ej. desarrollo, revision).
    repo          Ruta al repositorio git donde trabajar.
    pedido        Texto de la tarea o ruta a un archivo con las instrucciones.

Opciones:
    --revisar     Modo solo lectura: análisis y revisión sin modificar archivos.
                  Permite árbol de trabajo sucio (sandbox read-only / mode plan).
    --sensible    Excluye planes que no admiten datos privados.
    --dry-run     Muestra el plan elegido y el comando que correría, sin ejecutarlo.

Códigos de salida:
    0   Éxito (tarea ejecutada o revisada).
    1   Sin plan disponible en el radar (cupos agotados, retiros, etc.).
    2   Categoría desconocida.
    3   El plan elegido es Claude Code (hacelo en esta sesión interactiva).
    64  Error de uso o repositorio inválido (no es un repo git).
    65  Carpeta privada (/Finanzas, /Personal, /Consultoria-Negocio, /clientes/ o METODO_NO_DELEGAR).
    66  Árbol sucio al editar (git status no limpio sin --revisar).
    67  La CLI del plan elegido (codex o agy) no está instalada.
    124 La herramienta no terminó a tiempo (METODO_DELEGAR_TOPE, 3600 s por defecto) y se cortó.

Python 3.6+. Solo biblioteca estándar.
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
if str(AQUI) not in sys.path:
    sys.path.insert(0, str(AQUI))

import radar


class ArgumentParserUso(argparse.ArgumentParser):
    """ArgumentParser que sale con 64 en errores de argumentos."""

    def error(self, message):
        sys.stderr.write("%s: error: %s\n" % (self.prog, message))
        self.print_usage(sys.stderr)
        sys.exit(64)


def es_repo_git(ruta):
    """Verifica si la ruta corresponde a un repositorio git válido."""
    try:
        r = subprocess.run(
            ["git", "-C", str(ruta), "rev-parse", "--is-inside-work-tree"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            encoding="utf-8",
        )
        return r.returncode == 0 and r.stdout.strip() == "true"
    except Exception:
        return False


def es_carpeta_privada(repo_path):
    """(es_privada, motivo). Verifica rutas sensibles que no deben delegarse a planes externos."""
    repo_str = str(repo_path)
    repo_slash = repo_str + "/"
    patrones_base = ["/Finanzas", "/Personal", "/Consultoria-Negocio", "/clientes/"]
    for pat in patrones_base:
        # macOS no distingue mayúsculas de minúsculas en las rutas: /finanzas es la misma carpeta
        if pat.lower() in repo_slash.lower():
            return True, pat

    extra = os.environ.get("METODO_NO_DELEGAR", "").strip()
    if extra:
        for p in extra.split(":"):
            p = p.strip()
            if not p:
                continue
            if p.lower() in repo_slash.lower():
                return True, p
            try:
                p_res = str(Path(p).resolve())
                if repo_slash.lower().startswith(p_res.lower().rstrip("/") + "/"):
                    return True, p
            except Exception:
                pass
    return False, None


def arbol_sucio(repo_path):
    """True si hay cambios sin confirmar en el árbol de trabajo (git status --porcelain)."""
    try:
        r = subprocess.run(
            ["git", "-C", str(repo_path), "status", "--porcelain"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            encoding="utf-8",
        )
        return r.returncode != 0 or bool(r.stdout.strip())
    except Exception:
        return True   # si no se pudo mirar, no se edita


def args_modelo_agy(plan):
    """Argumentos --model/--effort para `agy`. El radar usa ids de API («gemini-3.8-flash», «gemini-3.1-pro-preview»);
    `agy` pide el id sin «-preview» y un nivel de esfuerzo aparte (si el id ya trae -low/-medium/-high, no se agrega)."""
    api = str(plan.get("modelo_api") or "").strip()
    if not api:
        return []
    if api.endswith("-preview"):
        api = api[: -len("-preview")]
    if api.endswith(("-low", "-medium", "-high")):
        return ["--model", api]
    esfuerzo = os.environ.get("METODO_AGY_ESFUERZO", "high").strip() or "high"
    return ["--model", api, "--effort", esfuerzo]


def parsear_argumentos(argv=None):
    ap = ArgumentParserUso(
        prog="delegar.py",
        description="Delegador de tareas a IAs del plugin metodo.",
    )
    ap.add_argument("categoria", help="Categoría del radar (ej. desarrollo, revision)")
    ap.add_argument("repo", help="Ruta al repositorio git donde trabajar")
    ap.add_argument("pedido", help="Texto de la tarea o ruta a archivo con instrucciones")
    ap.add_argument("--revisar", action="store_true", help="Modo solo lectura (no edita, permite árbol sucio)")
    ap.add_argument("--sensible", action="store_true", help="Excluye planes que no admiten datos privados")
    ap.add_argument("--dry-run", action="store_true", help="Muestra el plan elegido y el comando sin ejecutar")
    return ap.parse_args(argv)


def main(argv=None):
    args = parsear_argumentos(argv)

    # 1. Chequeo de repositorio (64 uso)
    repo_path = Path(args.repo).resolve()
    if not repo_path.is_dir() or not es_repo_git(repo_path):
        sys.stderr.write("«%s» no es un repositorio git válido. delegar.py exige un repositorio git.\n" % args.repo)
        return 64

    # 2. Chequeo de carpeta privada (65)
    privada, motivo = es_carpeta_privada(repo_path)
    if privada:
        sys.stderr.write(
            "No se delega en carpetas privadas (coincide con «%s»). "
            "Los planes gratuitos pueden entrenar con lo enviado. "
            "Hacelo en esta sesión.\n" % motivo
        )
        return 65

    # 3. Cargar radar y buscar categoría (2 categoría desconocida)
    radar_data, _ = radar.cargar()
    cat = radar.buscar_categoria(radar_data, args.categoria)
    if not cat:
        print("No conozco la categoría «%s». Las que hay: %s" % (args.categoria, radar._ids(radar_data)))
        return 2

    # 4. Filtrar copia de la categoría solo con herramientas ejecutables (Codex, Antigravity, Claude Code)
    cat_copia = dict(cat)
    herramientas_validas = ("Codex", "Antigravity", "Claude Code")
    cat_copia["planes"] = [
        p for p in (cat.get("planes") or [])
        if any(str(p.get("herramienta", "")).startswith(h) for h in herramientas_validas)
    ]

    # 5. Elegir plan con modo delegar
    plan, saltados, _ = radar.elegir(radar_data, cat_copia, sensible=args.sensible, delegar=True)

    # Si ningún plan quedó disponible (1)
    if plan is None:
        if saltados:
            detalle = "; ".join("%s (%s): %s" % (p.get("plan"), radar._nombre_plan(p), m) for p, m in saltados)
            print("Ningún plan disponible para «%s» ahora. Saltó: %s." % (cat.get("nombre", args.categoria), detalle))
        else:
            print("Ningún plan disponible para «%s» ahora." % cat.get("nombre", args.categoria))
        return 1

    # Imprimir línea previa obligatoria
    if saltados:
        motivos = "; ".join("%s (%s): %s" % (p.get("plan"), p.get("herramienta"), m) for p, m in saltados)
    else:
        motivos = "ninguno"
    print("Plan elegido: %s · saltó: %s" % (radar._nombre_plan(plan), motivos))

    # 6. Adaptador Claude Code (3)
    herramienta = str(plan.get("herramienta", ""))
    if herramienta.startswith("Claude Code"):
        print("El plan elegido es Claude Code: hacelo en esta sesión (cupo disponible).")
        return 3

    # 7. Chequeo de árbol sucio al editar (66; con --revisar no se exige)
    if not args.revisar and arbol_sucio(repo_path):
        sys.stderr.write(
            "El árbol de trabajo en «%s» tiene cambios sin confirmar.\n"
            "Para editar se exige un árbol limpio. Hacé commit o stash antes de delegar "
            "(o usá --revisar si solo querés análisis).\n" % args.repo
        )
        return 66

    # 8. Obtener texto del pedido (desde archivo o argumento directo)
    pedido_arg = args.pedido
    try:
        p_obj = Path(pedido_arg)
        if p_obj.is_file():
            pedido_texto = p_obj.read_text(encoding="utf-8")
        else:
            pedido_texto = pedido_arg
    except OSError:
        pedido_texto = pedido_arg

    # 9. Construir comando según adaptador y verificar CLI instalada (67)
    if herramienta.startswith("Codex"):
        bin_cli = radar._buscar_bin("codex", "RADAR_CODEX_BIN")
        if not bin_cli or not Path(bin_cli).is_file():
            sys.stderr.write("La CLI de Codex («codex») no está instalada o no se encuentra en el PATH.\n")
            return 67
        cmd = [
            bin_cli,
            "exec",
            "-C",
            str(repo_path),
            "--sandbox",
            "read-only" if args.revisar else "workspace-write",
            "-",
        ]
        usa_stdin = True
    elif herramienta.startswith("Antigravity"):
        bin_cli = radar._buscar_bin("agy", "RADAR_AGY_BIN")
        if not bin_cli or not Path(bin_cli).is_file():
            sys.stderr.write("La CLI de Antigravity («agy») no está instalada o no se encuentra en el PATH.\n")
            return 67
        cmd = [bin_cli] + args_modelo_agy(plan)
        cmd.extend(["--mode", "plan" if args.revisar else "accept-edits"])
        cmd.extend(["--add-dir", str(repo_path)])
        instruccion = (
            "Solo leé y analizá; no edites nada."
            if args.revisar
            else "Editá solo lo pedido. No toques archivos de claves ni de variables de entorno."
        )
        prompt_completo = (
            pedido_texto
            + "\n\nNO corras ningún comando. "
            + instruccion
            + " Respondé en castellano, corto: qué hiciste o qué encontraste."
        )
        cmd.extend(["-p", prompt_completo])
        usa_stdin = False
    else:
        sys.stderr.write("Herramienta no soportada para delegar: «%s».\n" % herramienta)
        return 1

    # 10. Modo dry-run
    if args.dry_run:
        print("Comando: %s" % " ".join(cmd))
        return 0

    # 11. Ejecución del adaptador, con tope de tiempo (METODO_DELEGAR_TOPE, segundos; por defecto 1 hora)
    try:
        tope = float(os.environ.get("METODO_DELEGAR_TOPE", "3600"))
    except ValueError:
        tope = 3600.0
    try:
        if usa_stdin:
            r = subprocess.run(
                cmd,
                input=pedido_texto,
                cwd=str(repo_path),
                universal_newlines=True,
                encoding="utf-8",
                timeout=tope,
            )
        else:
            r = subprocess.run(cmd, cwd=str(repo_path), timeout=tope)
    except subprocess.TimeoutExpired:
        sys.stderr.write("La herramienta no terminó en %d s y se cortó. Revisá el árbol con git status.\n" % int(tope))
        return 124

    if r.returncode != 0:
        return r.returncode

    # 12. Al terminar adaptador que editó
    if not args.revisar:
        print("── Cambios (revisalos y corré los tests) ──")
        res_st = subprocess.run(
            ["git", "-C", str(repo_path), "status", "--short"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            encoding="utf-8",
        )
        if res_st.stdout:
            sys.stdout.write(res_st.stdout)

        res_df = subprocess.run(
            ["git", "-C", str(repo_path), "diff", "--stat"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            encoding="utf-8",
        )
        if res_df.stdout:
            sys.stdout.write(res_df.stdout)

        print("Todo al día ✓")

    return 0


if __name__ == "__main__":
    sys.exit(main())
