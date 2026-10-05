#!/usr/bin/env python3
"""Avanza la rama `estable` del catálogo (lo corre `.github/workflows/estable.yml`; sin IA, sin claves propias).

Los clientes siguen `estable`, no `main`: lo que entra a `main` llega a las Macs de los clientes recién 48 h después.
Eso da tiempo para notar (y revertir) algo malo que haya entrado por una cuenta o una sesión comprometida.

Cómo decide:
  - Candidato por antigüedad: `GET /repos/{repo}/activity?ref=refs/heads/main&per_page=100` y, de ese listado, el `after` más
    nuevo cuyo `timestamp` tenga >= 48 h respecto del encabezado `Date` de ESA MISMA respuesta (hora del servidor).
    Nunca la fecha de un commit (la pone quien commitea) ni el reloj de esta máquina. Sin `Date` válido no se mueve nada.
  - Con `--sha` («pasalo ya», lo urgente): ese commit, sin espera y sin consultar la API, pero con el mismo control de
    ancestría. Lo dispara una persona con `gh workflow run estable.yml -f sha=<40 hex>`.
  - Solo avance rápido: `estable` se mueve únicamente a un commit que desciende de su valor actual Y es ancestro de `main`
    (`git merge-base --is-ancestor`, con el historial completo). Si no, no se mueve y el trabajo termina en rojo.
  - El push es normal, sin forzar: si `estable` cambió mientras tanto, git lo rechaza.

Qué NO hace: no borra, no retrocede, no crea la rama (la crea `.claude/publicar-estable.sh`, con `--arranque`).

PROCEDIMIENTO DE EMERGENCIA (si entró algo malo a `main`):
  1. Frenar el avance al instante:   gh workflow disable estable.yml
  2. Revertir el commit malo en `main`.
  3. Reactivar recién 48 h DESPUÉS del revert:   gh workflow enable estable.yml
  Por qué: si el commit malo y su revert se separan menos de 48 h, a las 48 h del malo `estable` podría quedar justo entre
  los dos. Con el workflow apagado `estable` se queda donde estaba (antes del commit malo). Mientras tanto, lo urgente
  y bueno se promueve a mano con `-f sha=`.
  Límites conocidos: el listado trae hasta 100 eventos; si en 48 h entraron más, no hay candidato y no se mueve (falla
  seguro). El detalle de qué actor puede empujar a `estable` lo fijan los rulesets de `.github/rulesets/`.

Uso:
    estable-avanzar.py [--repo dueño/repo] [--sha SHA40] [--horas 48] [--remoto origin] [--sin-push]
    estable-avanzar.py --arranque          # imprime el commit inicial para crear `estable` (no empuja nada)
Salida: 0 = movió o no había nada que mover; 1 = no pudo decidir o algo no cuadra (no se mueve nada); 2 = uso incorrecto.
En GitHub Actions escribe el resumen en $GITHUB_STEP_SUMMARY y `movido`/`sha` en $GITHUB_OUTPUT.
Python 3.9+. Solo biblioteca estándar.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

REPO_POR_DEFECTO = "raimondifernando-web/claude-catalogo"
API_POR_DEFECTO = "https://api.github.com"
HORAS_POR_DEFECTO = 48
PRINCIPAL = "main"
ESTABLE = "estable"
PATRON_SHA = re.compile(r"^[0-9a-f]{40}$")
PATRON_REPO = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
PATRON_REMOTO = re.compile(r"^[A-Za-z0-9_.-]+$")
CEROS = "0" * 40
# Solo eventos que dejan un commit nuevo en main. Todo lo demás (force_push, borrados) se ignora: ignorar un evento
# nunca adelanta el candidato, solo lo deja en uno más viejo.
TIPOS_DE_EVENTO = ("push", "pr_merge", "merge_queue_merge", "branch_creation")


class SinMovimiento(Exception):
    """No hay nada que mover y está bien (salida 0)."""


class Frena(Exception):
    """No se pudo decidir o algo no cuadra: no se mueve nada y el trabajo termina en rojo (salida 1)."""


# --------------------------------------------------------------------------- #
# API de GitHub (hora del servidor)
# --------------------------------------------------------------------------- #
class _SinRedirecciones(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):  # noqa: D401
        return None  # una redirección nunca se sigue: la credencial no viaja a otro host


def cabeceras(api, credencial):
    h = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "estable-avanzar (claude-catalogo)",
    }
    if credencial and api.rstrip("/") == API_POR_DEFECTO:  # solo a api.github.com, nunca a otro host
        h["Authorization"] = "Bearer " + credencial
    return h


def pedir_actividad(repo, api, credencial=None, timeout=30):
    """Devuelve (lista de eventos, valor del encabezado Date)."""
    url = "%s/repos/%s/activity?ref=refs/heads/%s&per_page=100" % (api.rstrip("/"), repo, PRINCIPAL)
    req = urllib.request.Request(url, headers=cabeceras(api, credencial))
    try:
        with urllib.request.build_opener(_SinRedirecciones).open(req, timeout=timeout) as r:
            fecha = r.headers.get("Date")
            datos = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise Frena("la API respondió HTTP %s: no se mueve nada" % e.code)
    except (urllib.error.URLError, OSError, ValueError) as e:
        raise Frena("no se pudo leer la actividad de main (%s): no se mueve nada" % type(e).__name__)
    if not isinstance(datos, list):
        raise Frena("la API no devolvió una lista de eventos: no se mueve nada")
    return datos, fecha


def hora_del_servidor(fecha):
    if not fecha:
        raise Frena("la respuesta de la API no trae el encabezado Date: sin hora del servidor no se mueve nada")
    try:
        dt = parsedate_to_datetime(fecha)
    except (TypeError, ValueError, IndexError):
        raise Frena("el encabezado Date no se pudo leer (%r): no se mueve nada" % fecha[:60])
    if dt is None:
        raise Frena("el encabezado Date no se pudo leer (%r): no se mueve nada" % fecha[:60])
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _leer_hora(texto):
    if not isinstance(texto, str):
        return None
    for formato in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S.%fZ"):
        try:
            return datetime.strptime(texto, formato).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def eventos_validos(actividad):
    """[(hora, sha)] de los eventos de main que dejan un commit; descarta lo raro en silencio."""
    salida = []
    for e in actividad:
        if not isinstance(e, dict):
            continue
        if e.get("activity_type") not in TIPOS_DE_EVENTO or e.get("ref") != "refs/heads/" + PRINCIPAL:
            continue
        sha, hora = e.get("after"), _leer_hora(e.get("timestamp"))
        if not isinstance(sha, str) or not PATRON_SHA.match(sha) or sha == CEROS or hora is None:
            continue
        salida.append((hora, sha))
    return salida


def candidato_por_antiguedad(actividad, ahora, horas):
    """El `after` más nuevo con >= `horas` de antigüedad respecto de `ahora` (hora del servidor), o None."""
    limite = ahora - timedelta(hours=horas)
    elegibles = [(h, s) for h, s in eventos_validos(actividad) if h <= limite]
    if not elegibles:
        return None
    return max(elegibles, key=lambda par: par[0])


def candidato_mas_viejo(actividad):
    validos = eventos_validos(actividad)
    return min(validos, key=lambda par: par[0]) if validos else None


# --------------------------------------------------------------------------- #
# git
# --------------------------------------------------------------------------- #
def git(args, cwd):
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0")
    return subprocess.run(["git"] + list(args), cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          universal_newlines=True)


def git_ok(args, cwd, error):
    r = git(args, cwd)
    if r.returncode != 0:
        raise Frena("%s: %s" % (error, (r.stderr or r.stdout).strip()[:300]))
    return r.stdout.strip()


def es_ancestro(a, b, cwd):
    r = git(["merge-base", "--is-ancestor", a, b], cwd)
    if r.returncode == 0:
        return True
    if r.returncode == 1:
        return False
    raise Frena("git no pudo comparar %s con %s: %s" % (a[:7], b[:7], (r.stderr or "").strip()[:200]))


def preparar_clon(cwd, remoto, exigir_estable):
    """Trae main (y estable) y devuelve (sha de main, sha de estable o None)."""
    if git_ok(["rev-parse", "--is-shallow-repository"], cwd, "no se pudo leer el clon") == "true":
        raise Frena("el clon es superficial: sin el historial completo no se puede comprobar la ancestría")
    git_ok(["fetch", "--quiet", "--no-tags", remoto, "+refs/heads/%s:refs/remotes/%s/%s" % (PRINCIPAL, remoto, PRINCIPAL)],
           cwd, "no se pudo traer main")
    principal = git_ok(["rev-parse", "--verify", "refs/remotes/%s/%s^{commit}" % (remoto, PRINCIPAL)], cwd, "main no existe")
    actual = None
    if exigir_estable:
        r = git(["fetch", "--quiet", "--no-tags", remoto,
                 "+refs/heads/%s:refs/remotes/%s/%s" % (ESTABLE, remoto, ESTABLE)], cwd)
        if r.returncode != 0:
            raise Frena("la rama estable no existe en el remoto (la crea publicar-estable.sh): %s" % (r.stderr or "").strip()[:200])
        actual = git_ok(["rev-parse", "--verify", "refs/remotes/%s/%s^{commit}" % (remoto, ESTABLE)], cwd, "estable no existe")
    return principal, actual


def _existe_commit(sha, cwd):
    return git(["cat-file", "-e", sha + "^{commit}"], cwd).returncode == 0


# --------------------------------------------------------------------------- #
# Decisión
# --------------------------------------------------------------------------- #
def decidir(cwd, principal, actual, candidato, manual):
    """Aplica los controles de ancestría. Devuelve el sha a empujar o levanta SinMovimiento / Frena."""
    if not _existe_commit(candidato, cwd):
        raise Frena("el commit %s no está en el clon: no se mueve nada" % candidato[:7])
    if candidato == actual:
        raise SinMovimiento("estable ya está en %s" % candidato[:7])
    if not es_ancestro(candidato, principal, cwd):
        raise Frena("%s no es ancestro de main: no se mueve nada" % candidato[:7])
    if es_ancestro(candidato, actual, cwd):
        if manual:
            raise Frena("%s está detrás de estable (%s): retroceder no se hace" % (candidato[:7], actual[:7]))
        raise SinMovimiento("estable (%s) ya está más adelante que el candidato %s (promoción manual): no se mueve"
                            % (actual[:7], candidato[:7]))
    if not es_ancestro(actual, candidato, cwd):
        raise Frena("%s no desciende de estable (%s): divergen, no se mueve nada" % (candidato[:7], actual[:7]))
    return candidato


# --------------------------------------------------------------------------- #
# Salida
# --------------------------------------------------------------------------- #
def decir(texto, destino=None):
    print("estable: " + texto, file=destino or sys.stdout, flush=True)


def anotar_resumen(lineas):
    ruta = os.environ.get("GITHUB_STEP_SUMMARY")
    if ruta:
        try:
            with open(ruta, "a", encoding="utf-8") as f:
                f.write("### estable\n\n" + "\n".join("- " + l for l in lineas) + "\n")
        except OSError:
            pass


def anotar_salida(movido, sha):
    ruta = os.environ.get("GITHUB_OUTPUT")
    if ruta:
        try:
            with open(ruta, "a", encoding="utf-8") as f:
                f.write("movido=%s\nsha=%s\n" % ("true" if movido else "false", sha or ""))
        except OSError:
            pass


def _hace(ahora, hora):
    return "%.1f h" % ((ahora - hora).total_seconds() / 3600.0)


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def main(argv=None):
    ap = argparse.ArgumentParser(description="Avanza la rama estable (solo avance rápido).")
    ap.add_argument("--repo", default=REPO_POR_DEFECTO)
    ap.add_argument("--sha", default=None, help="«pasalo ya»: commit completo (40 hex) de main, sin esperar")
    ap.add_argument("--horas", type=int, default=HORAS_POR_DEFECTO)
    ap.add_argument("--remoto", default="origin")
    ap.add_argument("--api", default=API_POR_DEFECTO, help=argparse.SUPPRESS)  # solo para las pruebas
    ap.add_argument("--sin-push", action="store_true", help="decide y cuenta, pero no empuja")
    ap.add_argument("--arranque", action="store_true", help="imprime el commit con el que crear estable; no empuja")
    a = ap.parse_args(argv)

    if not PATRON_REPO.match(a.repo) or not PATRON_REMOTO.match(a.remoto) or a.horas < 1:
        print("estable: uso incorrecto (repo, remoto u horas inválidos)", file=sys.stderr)
        return 2
    manual = None
    if a.sha is not None and a.sha.strip() != "":
        manual = a.sha.strip().lower()
        if not PATRON_SHA.match(manual):
            print("estable: --sha tiene que ser el commit completo (40 caracteres hexadecimales)", file=sys.stderr)
            return 2
    if manual and a.arranque:
        print("estable: --sha y --arranque no se combinan", file=sys.stderr)
        return 2

    cwd = os.getcwd()
    log = sys.stderr if a.arranque else sys.stdout   # con --arranque, stdout lleva solo el sha
    credencial = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    resumen = []
    try:
        principal, actual = preparar_clon(cwd, a.remoto, exigir_estable=not a.arranque)
        resumen.append("main: `%s`" % principal[:7])

        if a.arranque:
            actividad, fecha = pedir_actividad(a.repo, a.api, credencial)
            ahora = hora_del_servidor(fecha)
            par = candidato_por_antiguedad(actividad, ahora, a.horas)
            if par is None:
                par = candidato_mas_viejo(actividad)
                if par is None:
                    raise Frena("main no tiene actividad registrada: no hay con qué crear estable")
                print("estable: AVISO: ningún commit de main cumple %d h; se usa el más viejo disponible (%s, hace %s)"
                      % (a.horas, par[1][:7], _hace(ahora, par[0])), file=sys.stderr)
            if not _existe_commit(par[1], cwd) or not es_ancestro(par[1], principal, cwd):
                raise Frena("%s no es un commit de main: no se crea estable" % par[1][:7])
            print(par[1])
            return 0

        if manual:
            candidato = manual
            resumen.append("candidato manual («pasalo ya»): `%s`" % candidato[:7])
        else:
            actividad, fecha = pedir_actividad(a.repo, a.api, credencial)
            ahora = hora_del_servidor(fecha)
            par = candidato_por_antiguedad(actividad, ahora, a.horas)
            if par is None:
                raise SinMovimiento("ningún commit de main tiene %d h todavía (hora del servidor %s): no se mueve"
                                    % (a.horas, ahora.strftime("%Y-%m-%d %H:%M:%SZ")))
            candidato = par[1]
            resumen.append("candidato por antigüedad: `%s` (entró a main hace %s según el servidor)"
                           % (candidato[:7], _hace(ahora, par[0])))
        resumen.append("estable actual: `%s`" % actual[:7])

        destino = decidir(cwd, principal, actual, candidato, bool(manual))
        if a.sin_push:
            resumen.append("`--sin-push`: se movería a `%s` (no se empujó)" % destino[:7])
            decir("se movería de %s a %s (--sin-push: no se empujó)" % (actual[:7], destino[:7]), log)
            anotar_resumen(resumen)
            anotar_salida(False, destino)
            return 0
        r = git(["push", a.remoto, "%s:refs/heads/%s" % (destino, ESTABLE)], cwd)
        if r.returncode != 0:
            raise Frena("el push de estable fue rechazado (¿se movió mientras tanto, o falta permiso?): %s"
                        % (r.stderr or "").strip()[:300])
        resumen.append("**movida a `%s`**" % destino[:7])
        decir("movida de %s a %s" % (actual[:7], destino[:7]), log)
        anotar_resumen(resumen)
        anotar_salida(True, destino)
        return 0
    except SinMovimiento as e:
        decir(str(e), log)
        resumen.append("sin cambios: %s" % e)
        anotar_resumen(resumen)
        anotar_salida(False, None)
        return 0
    except Frena as e:
        motivo = " ".join(str(e).split())   # una sola línea: lo que viene de git o de la API nunca arma comandos del workflow
        if os.environ.get("GITHUB_ACTIONS"):
            print("::error::estable: %s" % motivo)
        decir("NO SE MOVIÓ: %s" % motivo, log)
        resumen.append("**no se movió**: %s" % motivo)
        anotar_resumen(resumen)
        anotar_salida(False, None)
        return 1


if __name__ == "__main__":
    sys.exit(main())
