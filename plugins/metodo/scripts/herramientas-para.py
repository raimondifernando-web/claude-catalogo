#!/usr/bin/env python3
"""herramientas-para.py <tema…> — qué hay instalado para lo que vas a construir.

Primero muestra las RECETAS cuyo tema coincide: las del paquete (recetas/*.md junto a este programa) y las propias
de la persona (<config de Claude>/recetas/*.md; si hay una con el mismo nombre, gana la propia). Después, las skills
y agentes instalados cuya descripción coincide. Solo lee: no usa red, no gasta cupo y no escribe nada salvo una marca
de 4 horas en la carpeta temporal para que el freno (consultar-ecosistema.py) no vuelva a saltar en esa carpeta.
"""
import glob, hashlib, os, re, sys, time, unicodedata

# Windows: la consola usa cp1252; se fuerza UTF-8 en la salida.
for _flujo in (sys.stdin, sys.stdout, sys.stderr):
    try:
        _flujo.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HOME = os.path.expanduser("~")
CFG = os.environ.get("CLAUDE_CONFIG_DIR", os.path.join(HOME, ".claude"))
AQUI = os.path.dirname(os.path.abspath(__file__))
RECETAS_PAQUETE = os.path.join(os.path.dirname(AQUI), "recetas")
STOP = set("de la el los las un una y o a en para con por que se del al lo su sus es como mas pero esto esta the and for with to of in on an is".split())

SIN = {"pantalla": "screen ui interface", "pantallas": "screens ui interface", "grafico": "chart graph dataviz",
       "graficos": "charts graphs dataviz", "diseno": "design visual", "interfaz": "interface ui",
       "tablero": "dashboard", "seguridad": "security", "planilla": "spreadsheet excel", "informe": "report",
       "automatizar": "automation workflow", "automatizacion": "automation workflow", "datos": "data",
       "base": "database", "correo": "email", "mail": "email", "contenido": "content", "publicidad": "ads advertising",
       "anuncios": "ads", "precio": "pricing", "precios": "pricing", "buscador": "search seo"}


def norm(s):
    s = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def toks(s, sinonimos=True):
    t = {t for t in re.findall(r"[a-z0-9]{3,}", norm(s)) if t not in STOP}
    if sinonimos:
        for k in list(t):
            if k in SIN:
                t |= set(SIN[k].split())
    return t


def front(path):
    try:
        t = open(path, encoding="utf-8", errors="replace").read()
    except OSError:
        return {}, ""
    m = re.match(r"---\n(.*?)\n---\n?(.*)", t, re.S)
    if not m:
        return {}, t
    meta = {}
    for l in m.group(1).splitlines():
        k, sep, v = l.partition(":")
        if sep and not l.startswith((" ", "#")):
            meta[k.strip()] = v.strip().strip('"')
    return meta, m.group(2)


def marca_path(cwd):
    h = hashlib.sha1(os.path.realpath(cwd).encode()).hexdigest()[:12]
    uid = os.getuid() if hasattr(os, "getuid") else "u"
    return os.path.join(os.environ.get("TMPDIR", "/tmp") if os.name != "nt" else os.environ.get("TEMP", "."),
                        f"consulta-ecosistema-{uid}-{h}")


def marcar(cwd):
    try:
        open(marca_path(cwd), "w").write(str(time.time()))
    except OSError:
        pass


def recetas(q, minimo=1, estricto=False):
    vistas = {}
    for carpeta in (RECETAS_PAQUETE, os.path.join(CFG, "recetas")):  # la propia pisa a la del paquete
        for p in sorted(glob.glob(os.path.join(carpeta, "*.md"))):
            if os.path.basename(p).startswith("_"):
                continue
            meta, cuerpo = front(p)
            nombre = meta.get("name", os.path.basename(p)[:-3])
            vistas[nombre] = (meta, cuerpo)
    out = []
    for nombre, (meta, cuerpo) in vistas.items():
        hit = q & toks(meta.get("triggers", "") + " " + nombre, sinonimos=not estricto)
        if len(hit) >= minimo:
            out.append((len(hit), nombre, cuerpo.strip()))
    return sorted(out, key=lambda x: -x[0])


def piezas(q):
    cand = {}
    pats = [("skill", os.path.join(CFG, "skills", "*", "SKILL.md")),
            ("agente", os.path.join(CFG, "agents", "*.md")),
            ("skill", os.path.join(CFG, "plugins", "cache", "*", "*", "*", "skills", "*", "SKILL.md")),
            ("agente", os.path.join(CFG, "plugins", "cache", "*", "*", "*", "agents", "*.md"))]
    for tipo, pat in pats:
        for p in glob.glob(pat):
            meta, _ = front(p)
            nombre = meta.get("name") or os.path.basename(os.path.dirname(p) if tipo == "skill" else p[:-3])
            d = meta.get("description", "")
            sc = 3 * len(q & toks(nombre)) + len(q & toks(d))
            if sc and (tipo, nombre) not in cand:
                cand[(tipo, nombre)] = (sc, d)
    return sorted(cand.items(), key=lambda kv: -kv[1][0])


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        return
    solo = args[0] == "--solo-recetas"   # modo del freno: sin marca y sin piezas
    if solo:
        args = args[1:]
    # el freno exige 2 palabras LITERALES del pedido (los sinónimos no suman: «diseño de la fachada» no es una pantalla)
    q = toks(" ".join(args), sinonimos=not solo)
    if not solo:
        marcar(os.getcwd())
    rs = recetas(q, 2 if solo else 1, estricto=solo)
    if rs:
        print("══ RECETAS (el método las dejó escritas: seguilas antes de armar nada) ══")
        for _, n, c in rs[:2]:
            print(f"\n## {n}\n{c}\n")
    elif solo:
        return
    else:
        print("(Sin receta para ese tema: abajo solo coincidencias por descripción.)\n")
    if solo:
        return
    print("══ Otras piezas instaladas que coinciden (no leídas enteras: verificá la descripción antes de usarlas) ══")
    pz = piezas(q)
    for tipo in ("skill", "agente"):
        for (t, n), (sc, d) in [x for x in pz if x[0][0] == tipo][:6]:
            print(f"- {t} `{n}` — {d[:150]}")
    if not rs and not pz:
        print("Nada instalado para eso. Probá /metodo:buscar-skill-externa (buscar <tema en inglés>) antes de crear (regla 19).")
    print("\nSi tenés que desviarte de la receta, decilo en una línea y por qué.")


main()
