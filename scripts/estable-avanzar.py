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
  - En automático, no avanza si algún commit que entraría a `estable` fue revertido después en `main` («This reverts commit
    <sha>» en `candidato..main`): espera a que el revert también cumpla las 48 h. Así no se queda entre el malo y su revert.
  - Alarma de atraso: si algún commit de `main` lleva más de 4 días (96 h) sin entrar a `estable`, la corrida sale en rojo.
  - Compuerta de security check (F14 del check 0.35.0), en automático Y en «pasalo ya»: si el commit a promover cambia la
    versión de `metodo` o `paneles` (lo que corre en las máquinas de los clientes) respecto de `estable`, esa versión tiene
    que estar en un TÍTULO (línea con `#`, fuera de bloques de código) de `docs/SECURITY-CHECKS.md` o de
    `.claude/security-checks/*.md`, leídos de `main` (el check se puede anotar después), que tenga TODO esto (M2):
    el paquete con la versión exacta o un rango que la incluya («metodo 0.36.0», «metodo 0.35.1 → 0.36.0», también `v0.36.0`
    o entre backticks), «commit <sha>» del código revisado, que tiene que ser ancestro del commit a promover o el mismo y traer
    la versión más alta del título, y el veredicto al final («— PASS» o «— PASS con condiciones»), sin FLAG, «crítico» ni FAIL.
    No cuentan los títulos dentro de bloques de código ni de comentarios HTML. Si `estable` tiene un plugin.json ilegible,
    se avisa y se trata como paquete nuevo (lo que se promueve sigue fallando cerrado). Si falta, no se mueve y la corrida sale en rojo. Salida explícita: `--sin-check "<motivo>"`
    (en el workflow: `-f sin_check=...`) promueve igual y lo deja anotado en el resumen de la corrida, en un aviso de GitHub y
    en `sin_check=true` de la salida.
    Falla cerrado (M1/L7): plugin.json ilegible, sin versión o con versión que no es X.Y.Z, o un bloque del catálogo
    (.claude-plugin/marketplace.json) de metodo/paneles que apunte a otra fuente o declare otra versión → no se mueve.
    Avisa sin frenar: código de metodo/paneles cambiado sin subir la versión, o cambios después del commit revisado.
    Queda FUERA de la compuerta: los demás paquetes del catálogo, los de afuera fijados por sha, `scripts/` de la raíz
    (al-dia.sh lo baja el portal por su huella) y `.github/`.
    Qué es y qué no: controla el PROCESO (que no se olvide el check antes de que algo llegue a los clientes). NO frena a quien
    ya puede empujar a `main`: esa persona también puede escribir el título. Contra eso están las 48 h y los rulesets.
  - Este script corre desde el checkout de la propia rama `estable` (ver el workflow): el código que decide ya esperó 48 h.
    Trae `main` por su cuenta.

Qué NO hace: no borra, no retrocede, no crea la rama (la crea `.claude/publicar-estable.sh`, en el commit recién publicado).
`--arranque` queda como herramienta suelta (imprime el commit de ≥ 48 h); el publicador ya no lo usa: ese commit es viejo.

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
    estable-avanzar.py [--repo dueño/repo] [--sha SHA40] [--horas 48] [--remoto origin] [--sin-push] [--sin-check MOTIVO]
    estable-avanzar.py --arranque          # imprime el commit inicial para crear `estable` (no empuja nada)
Salida: 0 = movió o no había nada que mover (incluye esperar por un revert); 1 = no pudo decidir, algo no cuadra o hay atraso
de más de 4 días (no se mueve nada); 2 = uso incorrecto.
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
PATRON_REVERT = re.compile(r"This reverts commit ([0-9a-f]{40})")
HORAS_ATRASO = 96   # 4 días: si algo de main espera más que eso y estable no lo tomó, la corrida sale en rojo
CEROS = "0" * 40
# Compuerta de pruebas (C26): en automático, un commit solo se promueve si las pruebas que GitHub registró para él
# no están en rojo ni sin terminar. Sin ninguna prueba registrada (commit que no tocó nada probado) pasa.
PRUEBAS = ("tests (", "comando del hook con bash (")   # nombres de los jobs de vigia-tests.yml
BUENAS = ("success", "skipped", "neutral")
# Solo eventos que dejan un commit nuevo en main. Todo lo demás (force_push, borrados) se ignora: ignorar un evento
# nunca adelanta el candidato, solo lo deja en uno más viejo.
TIPOS_DE_EVENTO = ("push", "pr_merge", "merge_queue_merge", "branch_creation")
# Compuerta de security check (F14): paquetes cuyo código corre en las máquinas de los clientes, y dónde se anotan los checks.
VIGILADOS = ("metodo", "paneles")
DOC_CHECKS = "docs/SECURITY-CHECKS.md"
CARPETA_CHECKS = ".claude/security-checks/"
PATRON_VERSION = re.compile(r"\d+\.\d+\.\d+")
# M2/L6: «metodo 0.36.0» o «metodo 0.35.1 → 0.36.0» (también con «->», «v0.36.0» o entre backticks), nunca «escala-metodo» ni «0.36.0-rc».
PATRON_ENTRADA = re.compile(r"(?<![\w-])(%s)\s+v?(\d+\.\d+\.\d+)(?:\s*(?:→|->)\s*v?(\d+\.\d+\.\d+))?(?![\w+-]|\.\d)"
                            % "|".join(VIGILADOS))
PATRON_COMMIT_CHECK = re.compile(r"(?<![\w-])commit\s+([0-9a-f]{7,40})(?![0-9A-Za-z])")
# 2.ª revisión (M-2c): el veredicto va AL FINAL del título («— PASS» o «— PASS con condiciones») y el título no puede nombrar FLAG,
# «crítico/a» ni FAIL/FAILED en ninguna parte («17 PASS · 15 FLAG» o «PASS salvo un crítico» no cuentan).
PATRON_PASS = re.compile(r"(?<![\w-])PASS(?:\s+con\s+condiciones)?\s*$")
PATRON_FAIL = re.compile(r"(?<![\w-])(?:FAIL(?:ED)?|NO\s+PASS|FLAGS?)(?![\w-])|cr[íi]tic", re.IGNORECASE)
PATRON_TITULO = re.compile(r"^ {0,3}#{1,6}\s")
MOTIVO_MINIMO = 10   # «x» no es un motivo: la salida tiene que quedar explicada


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


def pruebas_del_commit(repo, api, credencial, sha, timeout=30):
    """Devuelve (rojas, pendientes, total): las pruebas de vigia-tests registradas para ese commit."""
    url = "%s/repos/%s/commits/%s/check-runs?per_page=100" % (api.rstrip("/"), repo, sha)
    req = urllib.request.Request(url, headers=cabeceras(api, credencial))
    try:
        with urllib.request.build_opener(_SinRedirecciones).open(req, timeout=timeout) as r:
            datos = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise Frena("la API respondió HTTP %s al pedir las pruebas de %s: no se mueve nada" % (e.code, sha[:7]))
    except (urllib.error.URLError, OSError, ValueError) as e:
        raise Frena("no se pudieron leer las pruebas de %s (%s): no se mueve nada" % (sha[:7], type(e).__name__))
    corridas = datos.get("check_runs") if isinstance(datos, dict) else None
    if not isinstance(corridas, list):
        raise Frena("la API no devolvió las pruebas de %s: no se mueve nada" % sha[:7])
    mias = [c for c in corridas if isinstance(c, dict) and str(c.get("name", "")).startswith(PRUEBAS)]
    pendientes = [c["name"] for c in mias if c.get("status") != "completed"]
    rojas = [c["name"] for c in mias if c.get("status") == "completed" and c.get("conclusion") not in BUENAS]
    return rojas, pendientes, len(mias)


TOPE_COMMITS_A_MIRAR = 40   # commits del rango estable..candidato cuyas pruebas se consultan (de más nuevo a más viejo)


def pruebas_del_rango(repo, api, credencial, cwd, actual, destino):
    """F10 (security check 0.35.0): mirar solo el commit candidato dejaba pasar «un commit en rojo seguido de otro sin pruebas». Acá manda el
    commit MÁS NUEVO del rango estable..candidato que tenga pruebas registradas: si ese está en rojo (o sin terminar) no se mueve, aunque
    el candidato no haya corrido pruebas; si un commit posterior las corrió en verde (el arreglo), pasa. Devuelve (rojas, pendientes, total, sha)."""
    r = git(["rev-list", "--topo-order", "--max-count=%d" % TOPE_COMMITS_A_MIRAR, "%s..%s" % (actual, destino)], cwd)
    if r.returncode != 0:
        raise Frena("git no pudo listar los commits que entrarían a estable: %s" % (r.stderr or "").strip()[:200])
    for sha in r.stdout.split() or [destino]:
        rojas, pendientes, total = pruebas_del_commit(repo, api, credencial, sha)
        if total:
            return rojas, pendientes, total, sha
    return [], [], 0, None


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
    if not manual:
        revertido = revertido_despues(cwd, actual, candidato, principal)
        if revertido:
            raise SinMovimiento("el commit %s, que entraría a estable, fue revertido en main por %s (todavía sin 48 h): "
                                "no se mueve hasta que el revert también cumpla" % (revertido[0][:7], revertido[1][:7]))
    return candidato


def revertido_despues(cwd, actual, candidato, principal):
    """(commit revertido, commit que lo revierte) si algún commit que entraría a estable (actual..candidato) fue
    revertido DESPUÉS del candidato (candidato..main), buscando «This reverts commit <sha>» en los mensajes; si no, None.
    Así estable no queda parada entre un commit malo y su revert."""
    r = git(["rev-list", "%s..%s" % (actual, candidato)], cwd)
    if r.returncode != 0:
        raise Frena("git no pudo listar los commits que entrarían a estable: %s" % (r.stderr or "").strip()[:200])
    entran = set(r.stdout.split())
    if not entran:
        return None
    r = git(["log", "-z", "--format=%H%n%B", "%s..%s" % (candidato, principal)], cwd)
    if r.returncode != 0:
        raise Frena("git no pudo leer los commits nuevos de main: %s" % (r.stderr or "").strip()[:200])
    for registro in r.stdout.split("\0"):
        if not registro.strip():
            continue
        sha_revert = registro.split("\n", 1)[0].strip()
        for reverted in PATRON_REVERT.findall(registro):
            if reverted in entran:
                return reverted, sha_revert
    return None


def _una_linea(texto, tope=60):
    """Texto de un archivo del repo para un mensaje: una línea, sin «::» (no arma comandos de GitHub), recortado."""
    return " ".join(str(texto).replace("::", ": :").split())[:tope]


def _existe(cwd, sha, ruta):
    return git(["cat-file", "-e", "%s:%s" % (sha, ruta)], cwd).returncode == 0


def _leer_json(cwd, sha, ruta):
    """El JSON de `ruta` en ese commit, o None si el archivo no está. Si está pero no se puede leer: Frena (falla cerrado)."""
    if not _existe(cwd, sha, ruta):
        return None
    r = git(["show", "%s:%s" % (sha, ruta)], cwd)
    if r.returncode != 0:
        raise Frena("no se pudo leer %s en %s: no se mueve nada" % (ruta, sha[:7]))
    try:
        return json.loads(r.stdout)
    except ValueError:
        raise Frena("%s en %s no es JSON válido: no se puede saber qué versión llega a los clientes, no se mueve nada" % (ruta, sha[:7]))


def version_del_paquete(cwd, sha, paquete):
    """Versión de plugins/<paquete>/.claude-plugin/plugin.json en ese commit; None solo si el paquete no existe ahí.
    M1 (revisión de la rama): falla CERRADO. Si el archivo está pero es ilegible, no tiene versión, o la versión no es X.Y.Z
    exacto (0.36.0-rc.1, 0.36.0+fix), frena: antes eso contaba como «no hay versión nueva» y pasaba sin check.
    Solo lee el archivo con git: el código del commit nunca se ejecuta."""
    ruta = "plugins/%s/.claude-plugin/plugin.json" % paquete
    datos = _leer_json(cwd, sha, ruta)
    if datos is None:
        if _existe(cwd, sha, "plugins/%s" % paquete):
            raise Frena("plugins/%s existe en %s pero no tiene .claude-plugin/plugin.json: no se puede saber su versión, no se mueve nada"
                        % (paquete, sha[:7]))
        return None
    v = datos.get("version") if isinstance(datos, dict) else None
    if not isinstance(v, str) or not PATRON_VERSION.fullmatch(v):
        raise Frena("%s en %s tiene una versión que la compuerta no reconoce (%r; tiene que ser X.Y.Z): no se mueve nada"
                    % (ruta, sha[:7], _una_linea(v, 40)))
    return v


def bloque_del_catalogo(cwd, sha, paquete):
    """L7: la entrada de `paquete` en .claude-plugin/marketplace.json de ese commit, o None si no está listado.
    Falla cerrado si el catálogo es ilegible."""
    datos = _leer_json(cwd, sha, ".claude-plugin/marketplace.json")
    if datos is None:
        return None
    entradas = datos.get("plugins") if isinstance(datos, dict) else None
    if not isinstance(entradas, list):
        raise Frena(".claude-plugin/marketplace.json en %s no tiene la lista de plugins: no se mueve nada" % sha[:7])
    propias = [e for e in entradas if isinstance(e, dict) and e.get("name") == paquete]
    if len(propias) > 1:
        raise Frena("%s aparece %d veces en el catálogo de %s: no se mueve nada" % (paquete, len(propias), sha[:7]))
    return propias[0] if propias else None


def version_que_llega(cwd, sha, paquete):
    """La versión de `paquete` que reciben los clientes en ese commit (plugin.json), controlando su bloque del catálogo (L7):
    la fuente tiene que ser la carpeta del propio repo (si apuntara afuera, la compuerta no estaría revisando lo que se instala)
    y, si el catálogo declara versión, tiene que coincidir con plugin.json."""
    v = version_del_paquete(cwd, sha, paquete)
    entrada = bloque_del_catalogo(cwd, sha, paquete)
    if entrada is None:
        return v
    fuente = entrada.get("source")
    if fuente != "./plugins/%s" % paquete:
        raise Frena("en el catálogo de %s, %s apunta a otra fuente (%r) en vez de ./plugins/%s: la compuerta no puede revisar código de "
                    "afuera, no se mueve nada" % (sha[:7], paquete, _una_linea(json.dumps(fuente), 80), paquete))
    if v is None:
        raise Frena("%s está en el catálogo de %s pero no existe plugins/%s/.claude-plugin/plugin.json: no se mueve nada"
                    % (paquete, sha[:7], paquete))
    vc = entrada.get("version")
    if vc is not None and vc != v:
        raise Frena("en %s la versión de %s del catálogo (%r) no coincide con su plugin.json (%s): no se mueve nada"
                    % (sha[:7], paquete, _una_linea(vc, 40), v))
    return v


def _titulos(texto):
    """Las líneas de título de un markdown que se leen de verdad: fuera de bloques de código (``` o ~~~) y fuera de comentarios
    HTML <!-- … -->, también de varias líneas (M-2d). Un comentario dentro de una línea se borra antes de mirarla."""
    en_codigo, en_comentario = None, False
    for linea in texto.splitlines():
        if en_comentario:
            if "-->" not in linea:
                continue
            linea = linea.split("-->", 1)[1]
            en_comentario = False
        if en_codigo is None:
            linea = re.sub(r"<!--.*?-->", "", linea)
            if "<!--" in linea:
                linea, en_comentario = linea.split("<!--", 1)[0], True
        marca = linea.lstrip()[:3]
        if marca in ("```", "~~~"):
            en_codigo = None if en_codigo == marca else (en_codigo or marca)
            continue
        if en_codigo is None and PATRON_TITULO.match(linea):
            yield linea


def checks_anotados(cwd, sha):
    """Los checks anotados en ese commit (docs/SECURITY-CHECKS.md y .claude/security-checks/*.md), uno por paquete nombrado en
    un TÍTULO que cumple TODO: paquete + versión exacta o rango, «commit <sha>» (uno solo), veredicto PASS al final y nada de
    FLAG / crítico / FAIL. Una mención en el cuerpo no cuenta, ni un título en un bloque de código o en un comentario HTML.
    Devuelve [{paquete, desde, hasta, commit, archivo, titulo}]."""
    archivos = [DOC_CHECKS]
    r = git(["ls-tree", "-r", "--name-only", sha, "--", CARPETA_CHECKS], cwd)
    if r.returncode == 0:
        archivos += [a for a in r.stdout.splitlines() if a.endswith(".md")]
    anotados = []
    for archivo in archivos:
        r = git(["show", "%s:%s" % (sha, archivo)], cwd)
        if r.returncode != 0:
            continue
        for linea in _titulos(r.stdout):
            titulo = linea.replace("`", "").rstrip()
            commits = PATRON_COMMIT_CHECK.findall(titulo)
            if len(commits) != 1 or not PATRON_PASS.search(titulo) or PATRON_FAIL.search(titulo):
                continue
            for paquete, desde, hasta in PATRON_ENTRADA.findall(titulo):
                hasta = hasta or desde
                if _tupla(desde) <= _tupla(hasta):
                    anotados.append({"paquete": paquete, "desde": desde, "hasta": hasta, "commit": commits[0],
                                     "archivo": archivo, "titulo": _una_linea(titulo.lstrip("# "), 90)})
    return anotados


def _tupla(version):
    return tuple(int(x) for x in version.split("."))


def sin_security_check(cwd, actual, destino, principal):
    """(faltan, validados, avisos) para lo que entraría a estable de metodo/paneles. La versión nueva queda cubierta solo por un
    check anotado en main que la nombre (exacta o dentro de un rango), cuyo commit revisado sea ancestro del commit a promover o el
    mismo y TRAIGA la versión más alta del título (M-2a/b: así un rango no cubre versiones futuras que nadie revisó).
    `avisos` no frena: código cambiado sin subir la versión, cambios después del commit revisado, o un estable ilegible (M-2b)."""
    anotados = checks_anotados(cwd, principal)
    faltan, validados, avisos = [], [], []
    for paquete in VIGILADOS:
        nueva = version_que_llega(cwd, destino, paquete)       # lo que se promueve: falla cerrado
        try:
            vieja = version_que_llega(cwd, actual, paquete)
        except Frena as e:                                     # M-2b: el estado viejo de estable no traba la promoción
            avisos.append("no se pudo leer %s en estable (%s): se lo trata como paquete nuevo" % (paquete, _una_linea(e, 160)))
            vieja = None
        if not nueva:
            continue
        if nueva == vieja:
            if git(["diff", "--quiet", actual, destino, "--", "plugins/%s" % paquete], cwd).returncode == 1:
                avisos.append("cambió código de plugins/%s entre estable y %s sin subir la versión (%s): no se pide check, pero miralo"
                              % (paquete, destino[:7], nueva))
            continue
        bueno = None
        for a in anotados:
            if a["paquete"] != paquete or not _tupla(a["desde"]) <= _tupla(nueva) <= _tupla(a["hasta"]):
                continue
            r = git(["rev-parse", "--verify", "--quiet", a["commit"] + "^{commit}"], cwd)
            revisado = r.stdout.strip()
            if r.returncode != 0 or not PATRON_SHA.match(revisado) or not es_ancestro(revisado, destino, cwd):
                continue
            try:
                trae = version_del_paquete(cwd, revisado, paquete)
            except Frena:
                continue
            if trae == a["hasta"]:
                bueno = (a, revisado)
                break
        if bueno is None:
            faltan.append("%s %s" % (paquete, nueva))
            continue
        a, revisado = bueno
        validados.append("%s %s → «%s» en `%s` (commit revisado `%s`)" % (paquete, nueva, a["titulo"], a["archivo"], revisado[:7]))
        if git(["diff", "--quiet", revisado, destino, "--", "plugins/%s" % paquete], cwd).returncode == 1:
            avisos.append("hay cambios en plugins/%s después del commit revisado (%s..%s): el check no los cubre, miralos"
                          % (paquete, revisado[:7], destino[:7]))
    return faltan, validados, avisos


def limpiar_motivo(texto):
    """Una sola línea, sin comandos de GitHub Actions ni caracteres de control; None si no alcanza como motivo."""
    if texto is None:
        return None
    t = "".join(c if c.isprintable() else " " for c in texto).replace("::", ": :").replace("`", "'")
    t = " ".join(t.split())[:300]
    return t if len(t) >= MOTIVO_MINIMO else None


def controlar_atraso(cwd, actividad, ahora, final):
    """Alarma: si algún commit de main lleva más de HORAS_ATRASO esperando y estable (en `final`) no lo tiene, algo la
    frenó en silencio (un revert pendiente, una divergencia…) y hay que mirarlo."""
    par = candidato_por_antiguedad(actividad, ahora, HORAS_ATRASO)
    if par is not None and not es_ancestro(par[1], final, cwd):
        raise Frena("hay commits de main (hasta %s, de hace %s) que llevan más de %d h sin entrar a estable (que está en %s): "
                    "hay que mirar por qué" % (par[1][:7], _hace(ahora, par[0]), HORAS_ATRASO, final[:7]))


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


def anotar_salida(movido, sha, sin_check=False):
    ruta = os.environ.get("GITHUB_OUTPUT")
    if ruta:
        try:
            with open(ruta, "a", encoding="utf-8") as f:
                f.write("movido=%s\nsha=%s\nsin_check=%s\n" % ("true" if movido else "false", sha or "",
                                                                "true" if sin_check else "false"))
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
    ap.add_argument("--sin-check", default=None, metavar="MOTIVO",
                    help="promueve aunque falte el security check de metodo/paneles; queda anotado con el motivo")
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
    motivo_sin_check = None
    if a.sin_check is not None and a.sin_check.strip() != "":
        motivo_sin_check = limpiar_motivo(a.sin_check)
        if motivo_sin_check is None or a.arranque:
            print("estable: --sin-check necesita un motivo de al menos %d letras (y no va con --arranque)" % MOTIVO_MINIMO,
                  file=sys.stderr)
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

        actividad = ahora = None
        sin_mover = None      # motivo por el que no se mueve (no es un error), si lo hay
        destino = None
        forzado = False       # se promovió con --sin-check sobre una versión sin security check
        resumen.append("estable actual: `%s`" % actual[:7])
        try:
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
            destino = decidir(cwd, principal, actual, candidato, bool(manual))
            if not manual:
                rojas, pendientes, total, de_quien = pruebas_del_rango(a.repo, a.api, credencial, cwd, actual, destino)
                if rojas:
                    raise Frena("las pruebas de %s (último commit con pruebas entre estable y %s) están en rojo (%s): no se mueve hasta que main tenga un commit en verde"
                                % (de_quien[:7], destino[:7], ", ".join(rojas[:3])))
                if pendientes:
                    raise SinMovimiento("las pruebas de %s todavía no terminaron (%d): se reintenta en la próxima corrida"
                                        % (de_quien[:7], len(pendientes)))
                resumen.append("pruebas de `%s`: %s" % ((de_quien or destino)[:7], "%d en verde" % total if total else "ninguna registrada"))
            faltan, validados, avisos_check = sin_security_check(cwd, actual, destino, principal)
            for aviso_check in avisos_check:
                resumen.append("⚠️ %s" % aviso_check)
                if os.environ.get("GITHUB_ACTIONS"):
                    print("::warning::estable: %s" % aviso_check)
                decir(aviso_check, log)
            if faltan and not motivo_sin_check:
                raise Frena("falta el security check de %s (lo que corre en las máquinas de los clientes): corré /fable-security-check y "
                            "anotalo con un título que diga «%s (commit <sha revisado>) — PASS» en %s o en %s (el commit tiene que estar "
                            "en la historia del que se promueve), o forzá a propósito con -f sin_check=\"<motivo>\" (queda registrado)"
                            % (", ".join(faltan), faltan[0], DOC_CHECKS, CARPETA_CHECKS))
            if faltan:
                forzado = True
                quien = " ".join(os.environ.get("GITHUB_ACTOR", "").split())[:40] or "?"
                aviso = "PROMOVIDO SIN SECURITY CHECK de %s, por %s. Motivo: %s" % (", ".join(faltan), quien, motivo_sin_check)
                resumen.append("**⚠️ PROMOVIDO SIN SECURITY CHECK de %s, por %s.** Motivo: `%s`" % (", ".join(faltan), quien, motivo_sin_check))
                if os.environ.get("GITHUB_ACTIONS"):
                    print("::warning::estable: %s" % aviso)
                decir(aviso, log)
            else:
                resumen.append("security check: %s (main `%s`)" % ("; ".join(validados), principal[:7]) if validados
                               else "security check: no aplica (sin versión nueva de %s)" % " ni ".join(VIGILADOS))
        except SinMovimiento as e:
            sin_mover = e
        if actividad is not None:     # solo en automático: hay una hora del servidor con la que medir el atraso
            controlar_atraso(cwd, actividad, ahora, destino or actual)
        if sin_mover is not None:
            raise sin_mover
        if a.sin_push:
            resumen.append("`--sin-push`: se movería a `%s` (no se empujó)" % destino[:7])
            decir("se movería de %s a %s (--sin-push: no se empujó)" % (actual[:7], destino[:7]), log)
            anotar_resumen(resumen)
            anotar_salida(False, destino, forzado)
            return 0
        r = git(["push", a.remoto, "%s:refs/heads/%s" % (destino, ESTABLE)], cwd)
        if r.returncode != 0:
            raise Frena("el push de estable fue rechazado (¿se movió mientras tanto, o falta permiso?): %s"
                        % (r.stderr or "").strip()[:300])
        resumen.append("**movida a `%s`**" % destino[:7])
        decir("movida de %s a %s" % (actual[:7], destino[:7]), log)
        anotar_resumen(resumen)
        anotar_salida(True, destino, forzado)
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
