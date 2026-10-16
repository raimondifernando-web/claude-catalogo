#!/usr/bin/env python3
"""estructura_orden — el bucle de orden que se arregla solo (C140). Lo usa estructura.py (subcomandos auto, aplicar, deshacer, resumen, orden-config).

Disparador: automático — estructura.py revisar --aviso lo llama la primera vez de cada semana (el aviso de arranque ya instalado);
a mano: estructura.py auto | aplicar | deshacer | resumen | orden-config.

Tres grupos (decisión del dueño, 2026-10-16):
  1. SEGURO Y REVERSIBLE: se aplica solo (si la persona lo encendió con `orden-config --encender`; apagado por defecto).
     Un commit por arreglo, prueba que lo verifica, registro y comando de deshacer. Nunca hace push.
       · ruta movida: el CLAUDE.md cita una ruta que git muestra renombrada → se reescribe con la ruta nueva
       · documentos vivos que faltan (esqueleto de docs/PRD.md, decisiones.md, planes/)
       · caja atrasada respecto de GitHub que solo necesita avanzar (fast-forward, árbol limpio)
  2. DE JUICIO: lo decide Claude con evidencia del disco y la verifica una segunda IA; se aplica con
     `estructura.py aplicar <id> --verificado-por <IA>` (sin ese dato no se aplica).
       · ruta citada que no existe, sin renombrado en git, pero hay UN solo archivo con ese nombre en la caja
  3. DE LA PERSONA: nunca se aplica solo; llega como UNA pregunta de sí/no (qué se encontró, qué se propone, por qué).
       · cualquier cosa sensible (hooks, settings, .mcp.json, .github/, lo que corre solo), borrar o mover carpetas,
         caja sin repositorio, claves versionadas, decisiones de negocio
Nunca borra ni mueve nada. Solo lee la carpeta de la persona y escribe archivos de texto de las cajas en las que está encendido.
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

for _flujo in (sys.stdin, sys.stdout, sys.stderr):
    try:
        _flujo.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import estructura as E

SENSIBLES = (".claude/settings", ".claude/hooks", "hooks/", ".mcp.json", ".github/", "launchd", ".plist",
             "settings.json", "settings.local", "instalar", "install", "crontab", ".env", "CLAUDE.local")
SEMANA = 7


# ---------------------------------------------------------------- estado y config
def dir_config() -> Path:
    c = os.environ.get("CLAUDE_CONFIG_DIR")
    return Path(c) if c else Path.home() / ".claude"


def dir_estado() -> Path:
    d = os.environ.get("CLAUDE_PLUGIN_DATA")
    base = Path(d) if d else dir_config() / "metodo-estado"
    return base / "orden"


def archivo_config() -> Path:
    return dir_config() / "metodo-orden.json"


def aplicar_encendido() -> bool:
    """Apagado por defecto: solo corre solo donde la persona lo encendió (orden-config --encender)."""
    try:
        return bool(json.loads(archivo_config().read_text(encoding="utf-8")).get("aplicar"))
    except (OSError, ValueError):
        return False


def es_sensible(rel: str) -> bool:
    r = rel.replace("\\", "/")
    return any(s in r for s in SENSIBLES)


def registrar(entrada: dict):
    d = dir_estado()
    d.mkdir(parents=True, exist_ok=True)
    with open(d / "registro.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(entrada, ensure_ascii=False) + "\n")


def leer_registro() -> list:
    try:
        out = []
        for l in (dir_estado() / "registro.jsonl").read_text(encoding="utf-8").splitlines():
            try:
                out.append(json.loads(l))
            except ValueError:
                pass
        return out
    except OSError:
        return []


def _id(*partes) -> str:
    return hashlib.sha1("|".join(partes).encode("utf-8")).hexdigest()[:8]


# ---------------------------------------------------------------- git
def git(caja, *args):
    return E.ejecutar_git(*args, cwd=caja)


def arbol_ocupado(caja: Path) -> str:
    """Motivo por el que NO se toca la caja ahora (otra sesión o git a mitad de algo), o ''."""
    g = caja / ".git"
    if not g.is_dir():
        return "no es un repositorio"
    for marca in ("index.lock", "MERGE_HEAD", "rebase-merge", "rebase-apply", "CHERRY_PICK_HEAD"):
        if (g / marca).exists():
            return f"git está a mitad de algo ({marca})"
    return ""


def archivo_limpio(caja: Path, rel: str) -> bool:
    code, out = git(caja, "status", "--porcelain", "--", rel)
    return code == 0 and not out.strip()


def renombrados(caja: Path) -> dict:
    """{ruta_vieja: ruta_nueva} según la historia de git (relativas a la raíz del repo), la más reciente gana."""
    code, out = git(caja, "log", "-M", "--diff-filter=R", "--name-status", "--format=", "-n", "3000")
    mapa = {}
    if code != 0:
        return mapa
    for l in out.splitlines():
        p = l.split("\t")
        if len(p) == 3 and p[0].startswith("R"):
            mapa.setdefault(p[1], p[2])   # el log va del más nuevo al más viejo
    return mapa


def raiz_repo(caja: Path) -> Path:
    code, top = git(caja, "rev-parse", "--show-toplevel")
    return Path(top) if code == 0 and top else caja


# ---------------------------------------------------------------- hallazgos
def _rel(destino: Path, base: Path) -> str:
    """Ruta de `destino` relativa a `base`, resolviendo los dos (en macOS /var es /private/var)."""
    return os.path.relpath(str(destino.resolve()), str(base.resolve())).replace("\\", "/")


def _nueva_ruta(tok: str, caja: Path, top: Path, mapa: dict):
    """La ruta nueva de `tok` si git la muestra renombrada y existe, o None."""
    for base in dict.fromkeys([caja, top]):
        viejo = os.path.relpath(str((base / tok).resolve()), str(top.resolve())).replace("\\", "/")
        actual, visto = viejo, set()
        while actual in mapa and actual not in visto:
            visto.add(actual)
            actual = mapa[actual]
        if actual == viejo or tok.endswith("/"):   # solo archivos con renombrado exacto; las carpetas se deciden aparte
            continue
        if (top / actual).exists():
            nuevo = _rel(top / actual, base)
            return nuevo
    return None


def _unico_con_el_mismo_nombre(caja: Path, tok: str):
    nombre = tok.rstrip("/").rsplit("/", 1)[-1]
    if not nombre or tok.endswith("/"):
        return None
    code, out = git(caja, "ls-files")
    if code != 0:
        return None
    iguales = [l for l in out.splitlines() if l.rsplit("/", 1)[-1] == nombre]
    return iguales[0] if len(iguales) == 1 else None


def hallazgos_caja(caja: Path, nivel: str) -> list:
    """[dict] con id, grupo, tipo, caja, y lo necesario para aplicar o preguntar."""
    h = []
    nombre = caja.name
    claude = caja / "CLAUDE.md"
    top = raiz_repo(caja)
    if claude.is_file() and (caja / ".git").is_dir():
        faltan = E.rutas_citadas_que_faltan(E._lee(claude), caja)
        if faltan:
            mapa = renombrados(caja)
            for tok in faltan:
                if tok.startswith("~/"):
                    continue
                nueva = _nueva_ruta(tok, caja, top, mapa)
                if nueva and nueva != tok:
                    h.append(dict(id=_id(nombre, "ruta", tok, nueva), grupo=1, tipo="ruta_movida", caja=str(caja), nombre=nombre,
                                  archivo="CLAUDE.md", antes=tok, despues=nueva,
                                  evidencia=f"git muestra que «{tok}» se renombró a «{nueva}» y esa ruta existe"))
                    continue
                cand = _unico_con_el_mismo_nombre(caja, tok)
                if cand:
                    rel = _rel(top / cand, caja)
                    h.append(dict(id=_id(nombre, "cand", tok, rel), grupo=2, tipo="ruta_candidata", caja=str(caja), nombre=nombre,
                                  archivo="CLAUDE.md", antes=tok, despues=rel,
                                  evidencia=f"«{tok}» no existe y no hay renombrado en git, pero hay UN solo archivo llamado igual: «{rel}»"))
    # documentos vivos y demás esqueletos aditivos
    try:
        plan = E.plan_seguro(caja, nivel)
    except Exception:
        plan = []
    for rel, contenido, regla in plan:
        if es_sensible(rel):
            h.append(dict(id=_id(nombre, "sens", rel), grupo=3, tipo="archivo_sensible", caja=str(caja), nombre=nombre, archivo=rel,
                          evidencia=f"falta {rel}, que es de los que cambian lo que corre solo o los permisos"))
        elif regla == "R12" and (caja / ".git").is_dir() and not _esta_en_el_remoto(caja, rel):
            h.append(dict(id=_id(nombre, "doc", rel), grupo=1, tipo="doc_vivo", caja=str(caja), nombre=nombre, archivo=rel,
                          contenido=contenido, evidencia=f"falta {rel} (documento vivo del molde)"))
    # estructura que solo la persona decide
    for tipo, r_id, msg in E.revisar_caja(caja, nivel):   # con las excepciones escritas ya descontadas
        if tipo == "error" and r_id in ("R1", "R6", "R8"):
            h.append(dict(id=_id(nombre, "est", r_id, msg), grupo=3, tipo="estructura_" + r_id, caja=str(caja), nombre=nombre,
                          evidencia=msg))
    # caja atrasada que solo necesita avanzar
    if (caja / ".git").is_dir():
        al_dia = _plan_al_dia(caja)
        if al_dia:
            h.append(al_dia)
    return h


def _esta_en_el_remoto(caja: Path, rel: str) -> bool:
    """Si el archivo ya está en la rama principal de GitHub, lo que falta es traerlo (caja atrasada), no crearlo."""
    for ref in ("origin/HEAD", "origin/main", "origin/master"):
        code, _ = git(caja, "cat-file", "-e", f"{ref}:{rel}")
        if code == 0:
            return True
    return False


def _plan_al_dia(caja: Path):
    code, rama = git(caja, "branch", "--show-current")
    c2, ppal = git(caja, "symbolic-ref", "-q", "--short", "refs/remotes/origin/HEAD")
    ppal = ppal.replace("origin/", "") if c2 == 0 and ppal else "main"
    if code != 0 or rama != ppal:
        return None
    c3, atras = git(caja, "rev-list", "--count", f"HEAD..origin/{ppal}")
    c4, delante = git(caja, "rev-list", "--count", f"origin/{ppal}..HEAD")
    c5, sucio = git(caja, "status", "--porcelain", "--untracked-files=no")
    if (c3, c4, c5) != (0, 0, 0) or not atras.isdigit() or atras == "0" or delante != "0" or sucio.strip():
        return None
    return dict(id=_id(caja.name, "aldia", atras), grupo=1, tipo="caja_atrasada", caja=str(caja), nombre=caja.name,
                rama=ppal, atras=int(atras), evidencia=f"la copia está {atras} cambio(s) atrás de GitHub y no tiene nada propio sin subir")


def todos(raiz: Path) -> list:
    out = []
    for c_path, c_nivel, _parent in E.descubrir_cajas(raiz):
        if c_path.name.startswith("."):
            continue
        try:
            out.extend(hallazgos_caja(c_path, c_nivel))
        except Exception as e:   # un hallazgo roto no tapa a los demás
            out.append(dict(id=_id(c_path.name, "err"), grupo=2, tipo="no_se_pudo_revisar", caja=str(c_path), nombre=c_path.name,
                            evidencia=f"no se pudo revisar ({type(e).__name__})"))
    return out


# ---------------------------------------------------------------- aplicar
def _commit(caja: Path, rutas: list, mensaje: str):
    code, _ = git(caja, "add", "--", *rutas)
    if code != 0:
        return None
    code, out = git(caja, "commit", "-q", "-m", mensaje + "\n\nAutomático (metodo, orden de carpetas). Deshacer: estructura.py deshacer", "--", *rutas)
    if code != 0:
        return None
    c2, sha = git(caja, "rev-parse", "HEAD")
    return sha if c2 == 0 else None


def aplicar_uno(h: dict, verificado_por: str = "") -> dict:
    """Aplica UN hallazgo. Devuelve la entrada del registro (estado aplicado / omitido / fallo)."""
    caja = Path(h["caja"])
    base = dict(id=h["id"], fecha=datetime.now().isoformat(timespec="seconds"), caja=h["caja"], tipo=h["tipo"], grupo=h["grupo"],
                evidencia=h.get("evidencia", ""), verificado_por=verificado_por)
    if h["grupo"] == 3:
        return dict(base, estado="omitido", motivo="es de la persona: nunca se aplica solo")
    if h["grupo"] == 2 and not verificado_por:
        return dict(base, estado="omitido", motivo="falta --verificado-por (segunda IA)")
    ocupado = arbol_ocupado(caja)
    if ocupado:
        return dict(base, estado="omitido", motivo=ocupado)
    t = h["tipo"]
    if t in ("ruta_movida", "ruta_candidata"):
        rel = h["archivo"]
        if es_sensible(rel):
            return dict(base, estado="omitido", motivo="archivo sensible")
        if not archivo_limpio(caja, rel):
            return dict(base, estado="omitido", motivo=f"{rel} tiene cambios sin guardar (puede estar editándolo otra sesión)")
        f = caja / rel
        antes_txt = E._lee(f)
        nuevo_txt = antes_txt.replace(f"`{h['antes']}`", f"`{h['despues']}`")
        if nuevo_txt == antes_txt:
            return dict(base, estado="omitido", motivo="la ruta ya no aparece")
        f.write_text(nuevo_txt, encoding="utf-8")
        if h["antes"] in E.rutas_citadas_que_faltan(nuevo_txt, caja):   # prueba que lo verifica
            f.write_text(antes_txt, encoding="utf-8")
            return dict(base, estado="fallo", motivo="la verificación no pasó; se restauró el texto")
        sha = _commit(caja, [rel], f"orden: {rel} cita {h['despues']} en vez de {h['antes']}")
        if not sha:
            f.write_text(antes_txt, encoding="utf-8")
            return dict(base, estado="fallo", motivo="no se pudo commitear; se restauró el texto")
        return dict(base, estado="aplicado", commit=sha, antes=h["antes"], despues=h["despues"],
                    deshacer=f"git -C {caja} revert --no-edit {sha}")
    if t == "doc_vivo":
        rel = h["archivo"]
        if (caja / rel).exists():
            return dict(base, estado="omitido", motivo="ya existe")
        E.crear_nuevo(caja, rel, h["contenido"])
        if not (caja / rel).exists():
            return dict(base, estado="fallo", motivo="no se pudo crear")
        sha = _commit(caja, [rel], f"orden: agrega {rel} (documento vivo del molde)")
        if not sha:
            return dict(base, estado="fallo", motivo="no se pudo commitear")
        return dict(base, estado="aplicado", commit=sha, despues=rel, deshacer=f"git -C {caja} revert --no-edit {sha}")
    if t == "caja_atrasada":
        c0, previo = git(caja, "rev-parse", "HEAD")
        code, _ = git(caja, "merge", "-q", "--ff-only", f"origin/{h['rama']}")
        c1, atras = git(caja, "rev-list", "--count", f"HEAD..origin/{h['rama']}")
        if code != 0 or atras != "0":
            return dict(base, estado="fallo", motivo="no pudo avanzar")
        return dict(base, estado="aplicado", commit=previo, antes=previo[:8], despues="origin/" + h["rama"],
                    deshacer=f"git -C {caja} reset --keep {previo}")
    return dict(base, estado="omitido", motivo="tipo sin arreglo automático")


def pregunta_de_la_persona(hs: list) -> str:
    """UNA pregunta de sí/no, en criollo: qué se encontró, qué se propone, por qué."""
    if not hs:
        return ""
    h = hs[0]
    mas = f" (y {len(hs) - 1} más parecidas; las veo después de esta)" if len(hs) > 1 else ""
    t = h["tipo"]
    if t == "archivo_sensible":
        prop, por = f"crear {h['archivo']} con los permisos mínimos", "toca lo que se ejecuta solo en tu compu, por eso no lo hago sin tu sí"
    elif t == "estructura_R1":
        prop, por = "crear su repositorio privado en GitHub y subir la carpeta", "sin esa copia, un error en la compu te hace perder el trabajo"
    elif t == "estructura_R6":
        prop, por = "sacar el archivo de GitHub sin borrarlo de tu compu y cambiar las claves que tenga", "no tiene que estar donde otros lo ven"
    else:
        prop, por = "planificar el cambio con vos antes de tocar nada", "mueve carpetas y no se arregla de un golpe"
    return (f"En «{h['nombre']}» encontré: {h['evidencia']}.\nPropongo: {prop}.\nPorque: {por}.{mas}\n"
            f"Mi recomendación: sí. ¿Lo hago? (sí / no)")


# ---------------------------------------------------------------- comandos
def comando_auto(raiz_arg=None, aplicar=False, silencioso=False) -> int:
    raiz = Path(raiz_arg).resolve() if raiz_arg else Path.home() / "Proyectos"
    hs = todos(raiz)
    g1 = [h for h in hs if h["grupo"] == 1]
    g2 = [h for h in hs if h["grupo"] == 2]
    g3 = [h for h in hs if h["grupo"] == 3]
    aplicados = 0
    if aplicar:
        for h in g1:
            e = aplicar_uno(h)
            registrar(e)
            if e["estado"] == "aplicado":
                aplicados += 1
            if not silencioso:
                print(("✓ " if e["estado"] == "aplicado" else "• ") + f"{h['nombre']}: {h['evidencia']} → {e['estado']}"
                      + (f" ({e['motivo']})" if e.get("motivo") else ""))
    elif not silencioso:
        for h in g1:
            print(f"→ [grupo 1, se aplicaría solo] {h['nombre']}: {h['evidencia']}")
    if not silencioso:
        for h in g2:
            print(f"? [grupo 2, juicio] {h['id']} {h['nombre']}: {h['evidencia']}  → estructura.py aplicar {h['id']} --verificado-por <IA>")
        if g3:
            print("\n" + pregunta_de_la_persona(g3))
        print(f"Resumen: {len(g1)} seguro(s) · {len(g2)} de juicio · {len(g3)} para vos" + (f" · aplicados {aplicados}" if aplicar else ""))
    return 0


def comando_aplicar(id_: str, verificado_por: str, raiz_arg=None) -> int:
    raiz = Path(raiz_arg).resolve() if raiz_arg else Path.home() / "Proyectos"
    for h in todos(raiz):
        if h["id"] == id_:
            e = aplicar_uno(h, verificado_por)
            registrar(e)
            print(f"{e['estado']}: {h['evidencia']}" + (f" ({e['motivo']})" if e.get("motivo") else ""))
            return 0 if e["estado"] == "aplicado" else 1
    print(f"No encuentro el hallazgo {id_} (puede que ya esté arreglado).")
    return 1


def comando_deshacer(id_: str) -> int:
    for e in reversed(leer_registro()):
        if e.get("id") == id_ and e.get("estado") == "aplicado":
            caja = Path(e["caja"])
            ocupado = arbol_ocupado(caja)
            if ocupado:
                print(f"No se puede deshacer ahora: {ocupado}")
                return 1
            if e["tipo"] == "caja_atrasada":
                code, out = git(caja, "reset", "--keep", e["commit"])
            else:
                code, out = git(caja, "revert", "--no-edit", e["commit"])
            if code != 0:
                print(f"No se pudo deshacer: {out[:200]}")
                return 1
            registrar(dict(id=id_, fecha=datetime.now().isoformat(timespec="seconds"), caja=e["caja"], tipo=e["tipo"], grupo=e["grupo"],
                           estado="deshecho"))
            print(f"Deshecho: {e['tipo']} en {caja.name}.")
            return 0
    print(f"No hay un arreglo aplicado con id {id_}.")
    return 1


def resumen_semanal(raiz_arg=None) -> list:
    """3 líneas: «arreglé N cosas, nada pendiente»."""
    desde = (datetime.now() - timedelta(days=SEMANA)).isoformat(timespec="seconds")
    reg = [e for e in leer_registro() if e.get("fecha", "") >= desde]
    hechos = [e for e in reg if e.get("estado") == "aplicado"]
    deshechos = {e["id"] for e in reg if e.get("estado") == "deshecho"}
    hechos = [e for e in hechos if e["id"] not in deshechos]
    raiz = Path(raiz_arg).resolve() if raiz_arg else Path.home() / "Proyectos"
    try:
        hs = todos(raiz)
    except Exception:
        hs = []
    quedan2 = sum(1 for h in hs if h["grupo"] == 2)
    quedan3 = [h for h in hs if h["grupo"] == 3]
    por_tipo = {}
    for e in hechos:
        por_tipo[e["tipo"]] = por_tipo.get(e["tipo"], 0) + 1
    l1 = f"Orden de carpetas: arreglé {len(hechos)} cosa(s) esta semana" + (
        " (" + ", ".join(f"{n} {t.replace('_', ' ')}" for t, n in por_tipo.items()) + ")" if hechos else "") + "."
    l2 = (f"Quedan {quedan2} de juicio que decido con evidencia y una segunda IA." if quedan2 else "Nada de juicio pendiente.")
    l3 = (f"Tenés {len(quedan3)} pregunta(s) de sí/no (te las hago de a una)." if quedan3 else "Nada pendiente para vos.")
    return [l1, l2, l3]


def comando_resumen(raiz_arg=None) -> int:
    for l in resumen_semanal(raiz_arg):
        print(l)
    return 0


def comando_config(encender: bool, apagar: bool) -> int:
    if encender == apagar:
        print("Aplicación automática: " + ("ENCENDIDA" if aplicar_encendido() else "apagada") + f" ({archivo_config()}). Usá --encender o --apagar.")
        return 0
    archivo_config().parent.mkdir(parents=True, exist_ok=True)
    try:
        cfg = json.loads(archivo_config().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        cfg = {}
    cfg["aplicar"] = bool(encender)
    archivo_config().write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    print("Aplicación automática " + ("ENCENDIDA" if encender else "apagada") + ". Todo al día ✓")
    return 0


def semanal(raiz: Path):
    """Lo que corre la primera vez de cada semana, desde el aviso de arranque. Nunca rompe el arranque."""
    try:
        if aplicar_encendido():
            comando_auto(str(raiz), aplicar=True, silencioso=True)
        for l in resumen_semanal(str(raiz)):
            print(l)
    except Exception:
        pass
