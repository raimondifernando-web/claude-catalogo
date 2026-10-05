#!/usr/bin/env python3
"""Delegador de tareas a IAs del plugin `metodo`.

Elige la mejor IA según el radar de modelos (en modo delegar, priorizando Codex y Antigravity sobre Claude Code),
con el cupo de cada una medido, y ejecuta la tarea en el repositorio indicado. Nunca corre tests ni hace commit:
eso lo hace quien delega, mirando el cambio.

Uso:
    delegar.py <categoria> <repo> <pedido> [--archivo] [--revisar] [--sensible] [--dry-run]
    delegar.py --aceptar            (una sola vez: acepta que el código del repo se envíe a Codex / Antigravity)

Argumentos:
    categoria     Categoría del radar (ej. desarrollo, revision).
    repo          Ruta al repositorio git donde trabajar.
    pedido        Texto de la tarea (hasta 100 KB). Con --archivo, la ruta de un archivo de texto con la tarea.

Opciones:
    --archivo     El pedido es la ruta de un archivo (se rechazan nombres de claves y más de 100 KB).
    --revisar     Modo solo lectura: análisis y revisión sin modificar archivos. Permite árbol de trabajo sucio.
    --sensible    Excluye planes que no admiten datos privados.
    --dry-run     Muestra el plan elegido y el comando que correría, sin ejecutarlo.
    --aceptar     Deja constancia (una vez) de que sabés que el código se envía a un tercero y que los planes
                  gratuitos pueden entrenar con lo enviado. Sin eso, delegar no ejecuta nada.

Códigos de salida:
    0   Éxito (tarea ejecutada o revisada).
    1   Sin plan disponible en el radar (cupos agotados, retiros, etc.).
    2   Categoría desconocida.
    3   El plan elegido es Claude Code (hacelo en esta sesión interactiva).
    64  Error de uso, repositorio inválido, pedido ilegible o modelo con forma rara.
    65  Carpeta privada (/Finanzas, /Personal, /Consultoria-Negocio, /clientes/, METODO_NO_DELEGAR) o repo = tu carpeta personal.
    66  Árbol sucio al editar (git status no limpio sin --revisar).
    67  La CLI del plan elegido (codex o agy) no está instalada, o está dentro del repo.
    68  Falta aceptar el envío del código a un tercero (corré una vez `delegar.py --aceptar`).
    70  La herramienta (codex o agy) terminó con error; su código real va en el mensaje.
    71  La herramienta tocó .git/config o los hooks del repo: no confíes en ese repo hasta revisarlo.
    124 La herramienta no terminó a tiempo (METODO_DELEGAR_TOPE, 3600 s por defecto) y se cortó con sus hijos.

Límite conocido: los enlaces simbólicos DENTRO del repo que apuntan a otra carpeta los sigue la herramienta; el
filtro de carpetas privadas mira la ruta del repo, no lo que hay adentro. El sandbox de solo lectura de Codex puede
leer fuera del repo: no delegues desde un repo al que no le tengas confianza.

Python 3.6+. Solo biblioteca estándar.
"""
import argparse
import hashlib
import json
import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path

AQUI = Path(__file__).resolve().parent
if str(AQUI) not in sys.path:
    sys.path.insert(0, str(AQUI))

import radar

TOPE_PEDIDO = 100 * 1024
MODELO_VALIDO = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
NOMBRES_DE_CLAVES = re.compile(r"(^\.env|\.pem$|\.key$|\.p12$|\.pfx$|^id_|credencial|secret|token|\.npmrc$|\.netrc$)", re.I)
# git sin ejecutar nada del repo (un repo bajado de afuera puede traer core.fsmonitor, hooks o diff externo en su config)
GIT_SEGURO = ["git", "-c", "core.fsmonitor=false", "-c", "core.hooksPath=/dev/null", "-c", "diff.external=", "-c", "protocol.ext.allow=never"]


class ArgumentParserUso(argparse.ArgumentParser):
    """ArgumentParser que sale con 64 en errores de argumentos."""

    def error(self, message):
        sys.stderr.write("%s: error: %s\n" % (self.prog, message))
        self.print_usage(sys.stderr)
        sys.exit(64)


def git(repo, *args):
    """Corre git de forma segura sobre el repo. Devuelve el CompletedProcess (o None si git no se pudo ejecutar)."""
    env = dict(os.environ)
    env["GIT_OPTIONAL_LOCKS"] = "0"
    try:
        return subprocess.run(
            GIT_SEGURO + ["-C", str(repo)] + list(args),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL,
            universal_newlines=True, encoding="utf-8", env=env, timeout=60,
        )
    except (OSError, subprocess.SubprocessError):
        return None


def es_repo_git(ruta):
    """Verifica si la ruta corresponde a un repositorio git válido."""
    r = git(ruta, "rev-parse", "--is-inside-work-tree")
    return bool(r) and r.returncode == 0 and r.stdout.strip() == "true"


def raiz_del_repo(ruta):
    r = git(ruta, "rev-parse", "--show-toplevel")
    if r and r.returncode == 0 and r.stdout.strip():
        return Path(r.stdout.strip()).resolve()
    return Path(ruta).resolve()


def es_carpeta_privada(repo_path):
    """(es_privada, motivo). Verifica rutas sensibles que no deben delegarse a planes externos."""
    repo_str = str(repo_path)
    repo_slash = repo_str.rstrip("/") + "/"
    home = str(Path.home().resolve()).rstrip("/") + "/"
    # tu carpeta personal entera (o la raíz del disco) no es «un proyecto»: adentro hay de todo
    if repo_slash.lower() in (home.lower(), "/"):
        return True, "carpeta personal o raíz del disco"
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
    r = git(repo_path, "status", "--porcelain", "--no-ahead-behind")
    if r is None or r.returncode != 0:
        return True   # si no se pudo mirar, no se edita
    return bool(r.stdout.strip())


def huella_git(repo_path):
    """Hash de .git/config y de los hooks: si la herramienta los toca, lo vemos al terminar."""
    h = hashlib.sha256()
    for que in ("config", "hooks"):
        r = git(repo_path, "rev-parse", "--git-path", que)
        if not r or r.returncode != 0:
            continue
        p = Path(r.stdout.strip())
        if not p.is_absolute():
            p = Path(repo_path) / p
        archivos = [p] if p.is_file() else sorted(x for x in p.rglob("*") if x.is_file()) if p.is_dir() else []
        for a in archivos:
            try:
                h.update(str(a).encode("utf-8", "replace") + b"\0" + a.read_bytes() + b"\0")
            except OSError:
                h.update(b"?")
    return h.hexdigest()


def args_modelo_agy(plan):
    """Argumentos --model/--effort para `agy`. El radar usa ids de API («gemini-3.8-flash», «gemini-3.1-pro-preview»);
    `agy` pide el id sin «-preview» y un nivel de esfuerzo aparte (si el id ya trae -low/-medium/-high, no se agrega).
    El id y el esfuerzo se validan: el radar se baja de internet y no puede colar un argumento raro."""
    api = str(plan.get("modelo_api") or "").strip()
    if not api:
        return []
    if api.endswith("-preview"):
        api = api[: -len("-preview")]
    if not MODELO_VALIDO.match(api):
        raise ValueError("modelo con forma rara: %r" % api[:80])
    if api.endswith(("-low", "-medium", "-high")):
        return ["--model", api]
    esfuerzo = os.environ.get("METODO_AGY_ESFUERZO", "high").strip() or "high"
    if not MODELO_VALIDO.match(esfuerzo):
        raise ValueError("esfuerzo con forma rara: %r" % esfuerzo[:80])
    return ["--model", api, "--effort", esfuerzo]


def binario_seguro(ruta, repo_path):
    """Ruta absoluta y ejecutable, fuera del repo (cwd de la herramienta: un ./codex plantado por el repo no corre)."""
    if not ruta:
        return None
    real = os.path.realpath(ruta)
    if not os.path.isabs(real) or not os.path.isfile(real) or not os.access(real, os.X_OK):
        return None
    base = str(Path(repo_path).resolve()).rstrip("/") + "/"
    if (real + "/").startswith(base):
        return None
    return real


def ruta_aceptacion():
    return radar.carpeta_metodo() / "delegar-aceptado.json"


def esta_aceptado():
    try:
        return json.loads(ruta_aceptacion().read_text(encoding="utf-8")).get("aceptado") is True
    except Exception:
        return False


def aceptar():
    ruta = ruta_aceptacion()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    tmp = ruta.with_name(ruta.name + ".tmp")
    tmp.write_text(json.dumps({"aceptado": True, "fecha": time.strftime("%Y-%m-%d")}), encoding="utf-8")
    os.chmod(str(tmp), 0o600)
    os.replace(str(tmp), str(ruta))
    print("Aceptado ✓  A partir de ahora delegar.py manda el código del repo que le indiques a Codex (OpenAI) o a "
          "Antigravity (Google), y los planes gratuitos pueden entrenar con lo enviado. Nunca delegues datos privados "
          "ni claves. Para retirar el permiso, borrá %s." % ruta)
    return 0


def parsear_argumentos(argv=None):
    ap = ArgumentParserUso(
        prog="delegar.py",
        description="Delegador de tareas a IAs del plugin metodo.",
    )
    ap.add_argument("categoria", nargs="?", help="Categoría del radar (ej. desarrollo, revision)")
    ap.add_argument("repo", nargs="?", help="Ruta al repositorio git donde trabajar")
    ap.add_argument("pedido", nargs="?", help="Texto de la tarea (o la ruta de un archivo, con --archivo)")
    ap.add_argument("--archivo", action="store_true", help="El pedido es la ruta de un archivo de texto")
    ap.add_argument("--revisar", action="store_true", help="Modo solo lectura (no edita, permite árbol sucio)")
    ap.add_argument("--sensible", action="store_true", help="Excluye planes que no admiten datos privados")
    ap.add_argument("--dry-run", action="store_true", help="Muestra el plan elegido y el comando sin ejecutar")
    ap.add_argument("--aceptar", action="store_true", help="Acepta (una vez) el envío del código a un tercero")
    a = ap.parse_args(argv)
    if not a.aceptar and not (a.categoria and a.repo and a.pedido):
        ap.error("faltan argumentos: categoria, repo y pedido")
    return a


def leer_pedido(args):
    """(texto, error). El pedido es texto; solo es un archivo si se pidió con --archivo."""
    if not args.archivo:
        texto = args.pedido
    else:
        p = Path(args.pedido)
        if NOMBRES_DE_CLAVES.search(p.name):
            return None, "«%s» parece un archivo de claves: no se manda." % p.name
        try:
            if not p.is_file() or p.stat().st_size > TOPE_PEDIDO:
                return None, "el archivo del pedido no existe o pasa de %d KB." % (TOPE_PEDIDO // 1024)
            texto = p.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as e:
            return None, "no pude leer el archivo del pedido (%s): no lo mando como texto." % e.__class__.__name__
    if len(texto.encode("utf-8")) > TOPE_PEDIDO:
        return None, "el pedido pasa de %d KB." % (TOPE_PEDIDO // 1024)
    return texto, None


def ejecutar(cmd, cwd, entrada, tope):
    """Corre la herramienta en su propio grupo de procesos; al vencer el tope se corta el grupo entero (los hijos
    también). Devuelve el código de salida, o None si se cortó por tiempo."""
    p = subprocess.Popen(
        cmd, cwd=cwd, stdin=subprocess.PIPE if entrada is not None else subprocess.DEVNULL,
        universal_newlines=True, encoding="utf-8", start_new_session=True,
    )
    try:
        p.communicate(input=entrada, timeout=tope)
        return p.returncode
    except subprocess.TimeoutExpired:
        for sig in (signal.SIGTERM, signal.SIGKILL):
            try:
                os.killpg(p.pid, sig)
            except (ProcessLookupError, PermissionError):
                pass
            try:
                p.wait(timeout=5)
                break
            except subprocess.TimeoutExpired:
                continue
        return None


def main(argv=None):
    args = parsear_argumentos(argv)
    if args.aceptar:
        return aceptar()

    # 1. Chequeo de repositorio (64 uso)
    repo_path = Path(args.repo).resolve()
    if not repo_path.is_dir() or not es_repo_git(repo_path):
        sys.stderr.write("«%s» no es un repositorio git válido. delegar.py exige un repositorio git.\n" % args.repo)
        return 64

    # 2. Chequeo de carpeta privada (65): la ruta resuelta, la escrita (un enlace llamado /Personal) y la raíz del repo
    privada, motivo = es_carpeta_privada(repo_path)
    if not privada:
        privada, motivo = es_carpeta_privada(Path(os.path.abspath(args.repo)))
    if not privada:
        privada, motivo = es_carpeta_privada(raiz_del_repo(repo_path))
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

    # 7. Aceptación del envío a un tercero (68) y árbol sucio al editar (66; con --revisar no se exige)
    if not args.dry_run and not esta_aceptado():
        sys.stderr.write(
            "Falta aceptar que el código de «%s» se envía a un tercero (%s). Los planes gratuitos pueden entrenar con lo "
            "enviado: nunca datos privados ni claves. Si el usuario está de acuerdo, corré una vez: "
            "python3 %s --aceptar\n" % (args.repo, "OpenAI" if herramienta.startswith("Codex") else "Google", Path(__file__).resolve())
        )
        return 68
    if not args.revisar and arbol_sucio(repo_path):
        sys.stderr.write(
            "El árbol de trabajo en «%s» tiene cambios sin confirmar (o no se pudo leer).\n"
            "Para editar se exige un árbol limpio. Hacé commit o stash antes de delegar "
            "(o usá --revisar si solo querés análisis).\n" % args.repo
        )
        return 66

    # 8. Texto del pedido (64 si es ilegible o demasiado grande)
    pedido_texto, error = leer_pedido(args)
    if error:
        sys.stderr.write("Pedido rechazado: %s\n" % error)
        return 64

    # 9. Construir comando según adaptador y verificar CLI instalada (67)
    prompt_mostrado = None
    if herramienta.startswith("Codex"):
        bin_cli = binario_seguro(radar._buscar_bin("codex", "RADAR_CODEX_BIN"), repo_path)
        if not bin_cli:
            sys.stderr.write("La CLI de Codex («codex») no está instalada, no se encuentra o está dentro del repo.\n")
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
        bin_cli = binario_seguro(radar._buscar_bin("agy", "RADAR_AGY_BIN"), repo_path)
        if not bin_cli:
            sys.stderr.write("La CLI de Antigravity («agy») no está instalada, no se encuentra o está dentro del repo.\n")
            return 67
        try:
            cmd = [bin_cli] + args_modelo_agy(plan)
        except ValueError as e:
            sys.stderr.write("No se ejecuta: %s.\n" % e)
            return 64
        cmd.extend(["--mode", "plan" if args.revisar else "accept-edits"])
        cmd.extend(["--add-dir", str(repo_path)])
        instruccion = (
            "Solo leé y analizá; no edites nada."
            if args.revisar
            else "Editá solo lo pedido. No toques archivos de claves ni de variables de entorno."
        )
        # «Tarea:» al principio: un pedido que empiece con «--» no puede leerse como opción
        prompt_completo = (
            "Tarea: " + pedido_texto
            + "\n\nNO corras ningún comando. "
            + instruccion
            + " Respondé en castellano, corto: qué hiciste o qué encontraste."
        )
        cmd.extend(["-p", prompt_completo])
        prompt_mostrado = prompt_completo
        usa_stdin = False
    else:
        sys.stderr.write("Herramienta no soportada para delegar: «%s».\n" % herramienta)
        return 1

    # 10. Modo dry-run (el pedido se muestra recortado)
    if args.dry_run:
        mostrado = [c if c != prompt_mostrado else c[:200] + ("…" if len(c) > 200 else "") for c in cmd]
        print("Comando: %s" % " ".join(mostrado))
        return 0

    # 11. Ejecución con tope de tiempo (METODO_DELEGAR_TOPE, segundos; por defecto 1 hora) y vigilando .git
    try:
        tope = float(os.environ.get("METODO_DELEGAR_TOPE", "3600"))
    except ValueError:
        tope = 3600.0
    antes = huella_git(repo_path)
    codigo = ejecutar(cmd, str(repo_path), pedido_texto if usa_stdin else None, tope)
    if huella_git(repo_path) != antes:
        sys.stderr.write(
            "ATENCIÓN: la herramienta modificó .git/config o los hooks de «%s». No corras git en ese repo ni confíes en él "
            "hasta revisarlos a mano.\n" % args.repo
        )
        return 71
    if codigo is None:
        sys.stderr.write("La herramienta no terminó en %d s y se cortó (con sus procesos hijos). Revisá el árbol con git status.\n" % int(tope))
        return 124
    if codigo != 0:
        sys.stderr.write("La herramienta terminó con error (código %d). Revisá el árbol con git status.\n" % codigo)
        return 70

    # 12. Al terminar adaptador que editó
    if not args.revisar:
        print("── Cambios (revisalos y corré los tests) ──")
        res_st = git(repo_path, "status", "--short", "--no-ahead-behind")
        if res_st and res_st.stdout:
            sys.stdout.write(res_st.stdout)
        res_df = git(repo_path, "diff", "--stat", "--no-ext-diff", "--no-textconv")
        if res_df and res_df.stdout:
            sys.stdout.write(res_df.stdout)
        print("Todo al día ✓")

    return 0


if __name__ == "__main__":
    sys.exit(main())
