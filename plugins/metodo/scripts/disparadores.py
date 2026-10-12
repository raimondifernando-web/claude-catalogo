#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""disparadores.py — ¿quién ejecuta cada pieza? (Mand. XXIX / regla 23 del método)
Disparador: catalogo-check.sh lo corre en cada /cerrar (paso de integridad, con --check) y el vigía mensual; a mano: disparadores.py --home

Recorre las piezas que hacen algo (skills, agentes, scripts, comandos) y mide su DISPARADOR real:
  A automático  = hook, rutina programada (launchd / tarea programada / robot de GitHub)
  B encadenado  = otra skill, agente, script o instrucción cargada en cada sesión la nombra
  C intención   = solo su descripción hace que el modelo la use cuando la persona lo pide
  D nadie       = ninguna de las anteriores  → HUÉRFANA
Una pieza de CONTROL (revisar, auditar, verificar, respaldar, sincronizar, vigilar) que es solo C
también es huérfana: depende de que una persona se acuerde. Es el caso que originó la regla.

Uso:
  disparadores.py --home [~/.claude]              auditoría de ~/.claude (+ ~/Proyectos/*/CLAUDE.md como instrucciones)
  disparadores.py --catalogo <carpeta-con-plugins> auditoría de un catálogo de plugins
  ... --scripts-extra <carpeta> --corpus-extra <ruta>   (repetibles) scripts propios a medir / textos que también pueden nombrar piezas
  ... --check [--excepciones archivo]             solo imprime lo ROJO que no está en excepciones; sale 1 si hay
  ... --json                                      salida máquina
Solo lee; Python 3.9+; PyYAML opcional."""
import argparse, glob, json, os, re, sys

HOME = os.path.expanduser("~")
# «Disparador: …» al principio de una línea (en negrita, comentario de script o encabezado); los dos puntos son obligatorios.
DECLARADO = r"^[#>\s*\"'-]*Disparador\**\s*:\**\s*(\S.*)$"
CONTROL_NOMBRE = re.compile(r"(?<![a-z])(revis|audit(?!or)|check|verific|segur|security|backup|respald|sync|sincron|vigia|gate|escane|valid)", re.I)   # al comienzo de una palabra: «delegate», «async» o «aggregate» no cuentan
TRIGGER_LANG = re.compile(r"(?:\b(?:usala|usalo|usar|us[aá] (?:esta|este|cuando)|use when|use this|use it|use for|invoc|invoke|"
                          r"triggers? on|trigger|cuando|when (?:the|you|a|an|user)|siempre|always|"
                          r"si (?:el usuario|la persona|piden|te piden)|antes de|despu[eé]s de|al (?:abrir|cerrar|crear|publicar)|disparadores?|palabras clave|trigger words|should be used|used when|used for|triggered|perfect for|ideal para|sirve para)\b|触发)", re.I)
EXENTO_ARCHIVO = re.compile(r"(^test_|_test\.py$|\.bak$|\.antes-|\.reemplazado$|^__pycache__$|^\.|\.json$|\.md$|\.txt$|\.plist$)")


def leer(p, tope=400_000):
    try:
        with open(p, encoding="utf-8", errors="ignore") as f:
            return f.read(tope)
    except Exception:
        return ""


def frontmatter(texto):
    if not texto.startswith("---"):
        return {}
    cabeza = texto.split("---", 2)
    if len(cabeza) < 3:
        return {}
    try:
        import yaml
        d = yaml.safe_load(cabeza[1])
        return d if isinstance(d, dict) else {}
    except Exception:
        return frontmatter_simple(cabeza[1])


def frontmatter_simple(bloque):
    """Sin PyYAML: «clave: valor», y los valores en varias líneas (> o |, o con sangría) se juntan en la clave anterior."""
    d, clave = {}, None
    for l in bloque.splitlines():
        m = re.match(r"^([A-Za-z_-]+):\s*(.*)$", l)
        if m:
            clave, v = m.group(1), m.group(2).strip()
            d[clave] = "" if v in (">", "|", ">-", "|-") else v.strip('"').strip("'")
        elif clave and l.startswith((" ", "\t")) and l.strip():
            d[clave] = (d[clave] + " " + l.strip()).strip()
    return d


def archivos_texto(raiz, exts=(".md", ".py", ".sh", ".json", ".yaml", ".yml", ".plist", ".txt", ".js", ".ts", ".html")):
    for d, ds, fs in os.walk(raiz):
        ds[:] = [x for x in ds if x not in (".git", "node_modules", "__pycache__", "graphify-out")]
        for f in fs:
            if f.endswith(exts) or "." not in f:
                yield os.path.join(d, f)


class Pieza:
    def __init__(self, tipo, nombre, ruta, ambito, desc="", fm=None):
        self.tipo, self.nombre, self.ruta, self.ambito, self.desc = tipo, nombre, ruta, ambito, desc
        self.fm = fm or {}
        self.refs = {}          # clase -> set(origen)
        self.referrers = set()  # ids de las OTRAS piezas que la nombran
        self.ref_externa = False  # la nombra algún archivo que no es de ninguna pieza (se toma como armado, para no inventar rojos)
        self.armada = False     # ¿alguien con disparador real puede llegar hasta ella?
        self.uso = 0
        self.declarado = ""     # línea «Disparador:» si existe
        self.manual_por_diseno = False

    @property
    def id(self):
        return f"{self.tipo}:{self.nombre}"

    def agrega(self, clase, origen):
        self.refs.setdefault(clase, set()).add(origen)


def patrones(p):
    n = re.escape(p.nombre)
    if p.tipo in ("skill", "agent", "command"):
        base = [rf"(?<![\w/.:-])/{n}(?![\w-])", rf"`{n}`", rf"'{n}'", rf"(?:skill|skills|agente|agent|subagent_type:)\s*[`\"']?(?:[\w-]+:)?{n}(?![\w-])",
                rf"^\s*-\s*(?:[\w-]+:)?{n}\s*(?:#.*)?$", rf"[\w-]+:{n}(?![\w-])", rf"\"{n}\"", rf"(?<=Skill\()\s*{n}"]
    else:
        base = [rf"(?<![\w.-]){n}(?![\w-])"]
        stem = p.nombre.rsplit(".", 1)[0]
        if stem != p.nombre and len(stem) >= 8:      # «datos-grandes-control» sin el .py
            base.append(rf"(?<![\w.-]){re.escape(stem)}(?![\w-])")
    return [re.compile(b, re.M) for b in base]


# Archivos que LISTAN piezas (inventarios, manifiestos, registros): nombrarla ahí no la dispara.
INVENTARIOS = ("ORQUESTA.md", "BITACORA.md", "CATALOGO.yaml", "EQUIVALENCIAS.json", "marketplace.json", "plugin.json", "README.md",
               "inventario.json", "inventario.md", "RADAR.yaml", "RADAR.md", "FUNCIONES.md", "requisitos.md", "PENDIENTES.md", "kit_excepciones.json",
               "sync-paperclip-agents", "sync-paperclip-agents.v1.bak", "aviso-piezas-nuevas.py", "disparadores-excepciones.txt", "disparadores.py",
               "test_disparadores.py", "catalogo-sync.py", "catalogo-check.sh", "repetidos.py", "cowork-sync", "build_cloud_kit.py")


def clasificar_origen(ruta, home, catalogo):
    """Qué clase de referencia es un archivo (A automática / B encadenada / D documento / I inventario)."""
    ruta = ruta.replace("\\", "/")                      # Windows: todas las comparaciones usan «/»
    r = ruta.replace(home.replace("\\", "/"), "~") if home else ruta
    b = ruta.rsplit("/", 1)[-1]
    if b in INVENTARIOS or "/docs/" in r or "/handoffs/" in r:
        return "I"
    if b.startswith("test_") or "/tests/" in r:        # un test que nombra una pieza no la dispara
        return "I"
    if b in ("hooks.json", "settings.json", "settings.local.json") or "/hooks/" in r or "/.git/hooks/" in ruta:
        return "A"
    if "LaunchAgents" in r or "scheduled-tasks" in r or "rutinas-fuentes" in r or "/.github/workflows/" in r:
        return "A"
    if b in ("CLAUDE.md", "CLAUDE-omc.md", "MANDAMIENTOS.md", "ORQUESTA.md", "METODO-FABLE.md", "REGLAS-DEL-METODO.md") or "/recetas/" in r or "/rules/" in r:
        return "D"
    return "B"


def juntar_piezas(home, catalogo, scripts_extra=()):
    piezas = []
    def skills_en(carpeta, ambito):
        for sk in sorted(glob.glob(os.path.join(carpeta, "*", "SKILL.md"))):
            t = leer(sk); fm = frontmatter(t)
            p = Pieza("skill", os.path.basename(os.path.dirname(sk)), sk, ambito, str(fm.get("description", "")), fm)
            p.manual_por_diseno = str(fm.get("disable-model-invocation", "")).lower() == "true"
            m = re.search(DECLARADO, t, re.M | re.I)
            p.declarado = m.group(1).strip() if m else ""
            piezas.append(p)
    def agentes_en(carpeta, ambito):
        for ag in sorted(glob.glob(os.path.join(carpeta, "*.md"))):
            t = leer(ag); fm = frontmatter(t)
            p = Pieza("agent", os.path.basename(ag)[:-3], ag, ambito, str(fm.get("description", "")), fm)
            m = re.search(DECLARADO, t, re.M | re.I)
            p.declarado = m.group(1).strip() if m else ""
            piezas.append(p)
    def scripts_en(carpeta, ambito):
        if not os.path.isdir(carpeta):
            return
        for e in sorted(os.listdir(carpeta)):
            if EXENTO_ARCHIVO.search(e) or e in ("tests", "__pycache__"):
                continue
            ruta = os.path.join(carpeta, e)
            t = leer(ruta, 4000) if os.path.isfile(ruta) else ""
            if os.path.isfile(ruta) and not (os.access(ruta, os.X_OK) or e.endswith((".py", ".sh")) or leer(ruta, 30).startswith("#!")):
                continue
            p = Pieza("script", e, ruta, ambito, "")
            m = re.search(DECLARADO, t, re.M | re.I)
            p.declarado = m.group(1).strip() if m else ""
            piezas.append(p)
    def comandos_en(carpeta, ambito):
        for c in sorted(glob.glob(os.path.join(carpeta, "*.md"))):
            t = leer(c); fm = frontmatter(t)
            p = Pieza("command", os.path.basename(c)[:-3], c, ambito, str(fm.get("description", "")), fm)
            p.manual_por_diseno = True   # un comando /x es manual por naturaleza: necesita quien lo recuerde
            m = re.search(DECLARADO, t, re.M | re.I)
            p.declarado = m.group(1).strip() if m else ""
            piezas.append(p)
    if home:
        skills_en(os.path.join(home, "skills"), "personal")
        agentes_en(os.path.join(home, "agents"), "personal")
        scripts_en(os.path.join(home, "scripts"), "personal")
        comandos_en(os.path.join(home, "commands"), "personal")
        for h in sorted(glob.glob(os.path.join(home, "hooks", "*"))):
            e = os.path.basename(h)
            if os.path.isfile(h) and not EXENTO_ARCHIVO.search(e):
                piezas.append(Pieza("hookfile", e, h, "personal"))
    if catalogo:
        for pl in sorted(glob.glob(os.path.join(catalogo, "plugins", "*"))):
            nom = os.path.basename(pl)
            skills_en(os.path.join(pl, "skills"), f"catalogo:{nom}")
            agentes_en(os.path.join(pl, "agents"), f"catalogo:{nom}")
            scripts_en(os.path.join(pl, "scripts"), f"catalogo:{nom}")
            comandos_en(os.path.join(pl, "commands"), f"catalogo:{nom}")
        scripts_en(os.path.join(catalogo, "scripts"), "catalogo:raiz")
    for d in scripts_extra:
        scripts_en(d, "extra:" + os.path.basename(os.path.dirname(os.path.abspath(d))) + "/" + os.path.basename(d))
    vistos, unicas = set(), []
    for p in piezas:                      # una pieza que aparece por dos caminos (enlace simbólico) se mide una vez
        k = (p.ambito, p.id, os.path.realpath(p.ruta))
        if k not in vistos:
            vistos.add(k); unicas.append(p)
    return unicas


EXCLUIR_RAIZ = ("/projects/", "/plugins/", "/skills-archive", "/handoffs/", "/paperclip", "/shell-snapshots", "/file-history", "/todos",
                "/statsig", "/ide/", "/telemetry", "/backups", "/vigia/", "/skills/_archivo", "/sessions/", "/BITACORA", "/history",
                "/cache/", "/agents-archive", "/mods/", "/scheduled-tasks-archive", "/_archivo", "/session-env/", "/plans/",
                "/.omc/", "/teams/", "/dev-mods/", "/metodo/")


def corpus(home, catalogo, corpus_extra=()):
    """(ruta, texto, clase) de todo lo que puede nombrar a una pieza."""
    fuentes = []
    if home:
        raices = [home]
        extra = [os.path.join(HOME, "Library", "LaunchAgents"), os.path.join(HOME, ".cerebro", "rutinas-fuentes.json")]
        for r in raices:
            for f in archivos_texto(r):
                rel = f[len(r):].replace("\\", "/")
                # solo carpetas de PRIMER nivel de ~/.claude (datos, cachés, historiales); una skill llamada «vigia» o «metodo» sí cuenta
                if any(rel.startswith(x) for x in EXCLUIR_RAIZ) or "/.git/" in rel or "/node_modules/" in rel:
                    continue
                fuentes.append(f)
        if os.path.realpath(home) == os.path.realpath(os.path.join(HOME, ".claude")):   # fuentes de la máquina: solo para el ~/.claude real
            for e in extra:
                if os.path.isdir(e):
                    fuentes += [os.path.join(e, x) for x in os.listdir(e) if x.endswith(".plist")]
                elif os.path.isfile(e):
                    fuentes.append(e)
            fuentes += glob.glob(os.path.join(HOME, "Proyectos", "*", ".claude", "settings*.json")) + glob.glob(os.path.join(HOME, "Proyectos", "*", ".claude", "*.sh"))
            repos = [home] + glob.glob(os.path.join(HOME, "Proyectos", "*")) + glob.glob(os.path.join(HOME, "Proyectos", "*", "*"))
            for r in repos:                       # hooks de git (pre-push, pre-commit…): también son disparadores automáticos
                for h in glob.glob(os.path.join(r, ".git", "hooks", "*")):
                    if os.path.isfile(h) and not h.endswith(".sample"):
                        fuentes.append(h)
            for c in glob.glob(os.path.join(HOME, "Proyectos", "*", "CLAUDE.md")) + glob.glob(os.path.join(HOME, "Proyectos", "*", ".claude", "rules", "*.md")):
                fuentes.append(c)
    if catalogo:
        for f in archivos_texto(catalogo):
            if "/CHANGELOG" in f.replace("\\", "/"):
                continue
            fuentes.append(f)
    for d in corpus_extra:
        if os.path.isfile(d):
            fuentes.append(d)
        else:
            fuentes += list(archivos_texto(d))
    vistos, out = set(), []
    for f in fuentes:
        if f in vistos or not os.path.isfile(f):
            continue
        vistos.add(f)
        out.append((f, leer(f), clasificar_origen(f, home, catalogo)))
    return out


def medir(home, catalogo, uso_json=None, scripts_extra=(), corpus_extra=()):
    piezas = juntar_piezas(home, catalogo, scripts_extra)
    textos = corpus(home, catalogo, corpus_extra)
    uso = {}
    if uso_json and os.path.isfile(uso_json):
        with open(uso_json, encoding="utf-8") as f:
            u = json.load(f).get("uso_real", {})
        for k in ("skills", "agents"):
            for n, d in u.get(k, {}).items():
                uso[("skill" if k == "skills" else "agent", n)] = d.get("usos_total", 0)
        for n, d in u.get("slash_commands", {}).items():
            uso.setdefault(("skill", n.lstrip("/")), d.get("usos_total", 0))
    duenos = []   # (prefijo, pieza): a qué pieza pertenece cada archivo
    for q in piezas:
        pref = os.path.dirname(q.ruta) + os.sep if q.tipo == "skill" else (q.ruta + os.sep if os.path.isdir(q.ruta) else q.ruta)
        duenos.append((pref, q))
    duenos.sort(key=lambda x: -len(x[0]))

    def dueno_de(ruta):
        for pref, q in duenos:
            if ruta == pref or ruta.startswith(pref):
                return q
        return None

    for p in piezas:
        propio = os.path.dirname(p.ruta) if p.tipo in ("skill",) else p.ruta
        pats = patrones(p)
        for ruta, t, clase in textos:
            if ruta == p.ruta or ruta.startswith(propio + os.sep) or (p.tipo == "script" and os.path.isdir(p.ruta) and ruta.startswith(p.ruta + os.sep)):
                continue
            if p.tipo == "hookfile" and clase != "A":
                clase = "A" if os.path.basename(ruta) == "settings.json" else clase
            if p.nombre.rsplit(".", 1)[0] not in t:        # filtro barato antes de las expresiones regulares (sin la extensión)
                continue
            if clase == "I":
                continue
            if any(pt.search(t) for pt in pats):
                p.agrega(clase, ruta.replace(HOME, "~"))
                if clase == "B":
                    q = dueno_de(ruta)
                    if q is None:
                        p.ref_externa = True
                    elif q is not p:
                        p.referrers.add(q.id)
        p.uso = uso.get((p.tipo, p.nombre), 0)
    armar(piezas)
    return piezas


def es_control(p):
    return bool(CONTROL_NOMBRE.search(p.nombre))


def desc_con_disparadores(p):
    return bool(p.desc) and bool(TRIGGER_LANG.search(p.desc)) and len(p.desc) >= 20


ARMADAS = set()   # ids de las piezas armadas (lo llena armar())


def armar(piezas):
    """Punto fijo: una pieza está «armada» si algo con disparador real puede llegar hasta ella. Dos piezas que solo se
    nombran entre sí (un ciclo sin entrada) NO quedan armadas: es el caso /revision-seguridad ↔ security-reviewer."""
    por_id = {p.id: p for p in piezas}
    for p in piezas:
        p.armada = bool(p.refs.get("A") or p.declarado or p.refs.get("D")
                        or (p.tipo in ("skill", "agent") and not p.manual_por_diseno and not es_control(p)
                            and (desc_con_disparadores(p) or p.uso > 0)))
    cambio = True
    while cambio:
        cambio = False
        for p in piezas:
            if not p.armada and (p.ref_externa or any(por_id[r].armada for r in p.referrers if r in por_id)):
                p.armada = True
                cambio = True
    ARMADAS.clear()
    ARMADAS.update(p.id for p in piezas if p.armada)


def veredicto(p):
    """(letra, motivo). A automático · M declarado · B encadenado a algo armado · R solo recordado por un documento ·
    C solo por intención · C! control que solo arranca si alguien se acuerda · D nadie. Rojo = D y C!."""
    if p.tipo == "hookfile":
        return ("A", "registrado en settings.json") if p.refs.get("A") else ("D", "archivo de hook que ningún settings lo registra")
    if p.refs.get("A"):
        return "A", "automático: " + ", ".join(sorted(os.path.basename(x) for x in p.refs["A"])[:3])
    if p.declarado:
        return "M", "declarado: " + p.declarado[:80]
    if (p.ref_externa or any(r in ARMADAS for r in p.referrers)):
        return "B", f"encadenada por {len(p.referrers) + int(p.ref_externa)} pieza(s) con disparador"
    if p.refs.get("D"):
        return "R", "solo la recuerda un documento: " + ", ".join(sorted(os.path.basename(x) for x in p.refs["D"])[:2])
    if p.tipo in ("skill", "agent"):
        if p.manual_por_diseno:
            return "D", "manual por diseño y nadie la enlaza"
        if desc_con_disparadores(p) or p.uso > 0:
            if es_control(p):
                ciclo = " (solo la nombran piezas que tampoco tienen disparador)" if p.referrers else ""
                return "C!", "control que solo arranca si alguien se acuerda de pedirlo" + ciclo + ": enganchalo a un hook, una rutina o un paso del cierre"
            return "C", "por intención" + (" (usada %d veces)" % p.uso if p.uso else "")
        return "D", "descripción sin disparadores claros y nadie con disparador la enlaza"
    if p.tipo == "command":
        return "D", "comando manual que nadie con disparador enlaza"
    return "D", "script que ningún hook, rutina, skill o documento con disparador nombra"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--home", nargs="?", const=os.path.join(HOME, ".claude"))
    ap.add_argument("--catalogo")
    ap.add_argument("--uso", help="inventario.json con el uso real medido en las conversaciones (opcional; suma «usada N veces» como evidencia)")
    ap.add_argument("--scripts-extra", action="append", default=[], help="carpeta de scripts propios a medir (repetible)")
    ap.add_argument("--corpus-extra", action="append", default=[], help="carpeta o archivo cuyo texto también puede nombrar piezas (repetible)")
    ap.add_argument("--recientes", type=float, help="con --check: solo cuentan como rojo las piezas tocadas en las últimas N horas (las más viejas salen como aviso)")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--excepciones")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--todo", action="store_true", help="lista también las que sí tienen disparador")
    a = ap.parse_args()
    if not a.home and not a.catalogo and not a.scripts_extra:
        ap.error("falta --home o --catalogo")
    piezas = medir(a.home, a.catalogo, a.uso, a.scripts_extra, a.corpus_extra)
    exc = set()
    if a.excepciones and os.path.isfile(a.excepciones):
        with open(a.excepciones, encoding="utf-8") as f:
            exc = {l.split("|")[0].strip() for l in f if l.strip() and not l.startswith("#")}
    filas = []
    for p in piezas:
        letra, motivo = veredicto(p)
        filas.append({"id": p.id, "ambito": p.ambito, "letra": letra, "motivo": motivo, "uso": p.uso,
                      "refs": {k: sorted(v)[:4] for k, v in p.refs.items()}, "ruta": p.ruta.replace(HOME, "~")})
    rojas = [f for f in filas if f["letra"] in ("D", "C!") and f["id"] not in exc and f"{f['ambito']}/{f['id']}" not in exc]
    if a.json:
        print(json.dumps(filas, ensure_ascii=False, indent=1)); return 0
    if a.check:
        viejas = []
        if a.recientes is not None:
            import time
            corte = time.time() - a.recientes * 3600
            def mtime(f):
                try:
                    return os.path.getmtime(os.path.expanduser(f["ruta"]))
                except OSError:
                    return 0
            viejas = [f for f in rojas if mtime(f) < corte]
            rojas = [f for f in rojas if mtime(f) >= corte]
        for f in rojas:
            print(f"  - {f['ambito']}/{f['id']}: {f['motivo']}")
        if viejas:
            print(f"  (aviso) {len(viejas)} pieza(s) más antiguas también sin disparador: " + ", ".join(f['id'] for f in viejas[:6]) + (" …" if len(viejas) > 6 else ""))
        n = len(rojas)
        print(f"== Disparador: {'OK' if not n else f'{n} pieza(s) sin disparador (declarar «Disparador:» o enlazarla; ver Mand. XXIX)'}")
        return 1 if n else 0
    cuenta = {}
    for f in filas:
        cuenta[(f["ambito"].split(":")[0], f["letra"])] = cuenta.get((f["ambito"].split(":")[0], f["letra"]), 0) + 1
    print(f"Piezas medidas: {len(filas)}")
    for k in sorted(cuenta):
        print(f"  {k[0]:9s} {k[1]}: {cuenta[k]}")
    for f in filas:
        if f["letra"] in ("D", "R", "C!") or a.todo:
            print(f"{f['letra']} {f['ambito']:34s} {f['id']:45s} uso={f['uso']:<4} {f['motivo']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
