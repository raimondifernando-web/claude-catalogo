#!/usr/bin/env python3
"""skills-buscar <tema en inglés> — descubrimiento de solo lectura (no instala nada, no usa npx, no escribe nada).
Consulta la API pública de skills.sh, cruza con lo que ya tenemos y con las auditorías públicas.
Disparador: B (herramientas-para lo sugiere cuando no hay pieza local; la skill vigia §3 lo corre en el descubrimiento mensual) + C (la persona: «buscame una skill para X» → skill buscar-skill-externa).
Pasar 1-2 palabras clave en INGLÉS y genéricas: la consulta sale a skills.sh (nunca nombres de clientes ni de tu empresa)."""
import json, os, re, sys, glob, urllib.request, urllib.parse, time
HOME=os.path.expanduser("~")
CFG=os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(HOME,".claude")
CAT=os.environ.get("CATALOGO_YAML","")   # opcional: lista de piezas con su origen (la usa quien mantiene un catálogo propio)
OFICIALES={"anthropics","microsoft","google","vercel","vercel-labs","openai","github","n8n-io","shopify","firecrawl","getsentry","stripe","supabase","cloudflare","hashicorp","figma","notion"}  # orientativo, NO es confianza (Mand. XVI)
def get(url):
    return json.load(urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"skills-buscar/1.0"}),timeout=20))
def locales():
    n=set()
    for p in glob.glob(CFG+"/skills/*/"): n.add(os.path.basename(p.rstrip("/")))
    for p in glob.glob(CFG+"/plugins/cache/*/*/*/skills/*/"): n.add(os.path.basename(p.rstrip("/")))
    return n
def origenes():
    o=set()
    try:
        for l in open(CAT,encoding="utf-8"):
            for m in re.finditer(r'origen:\s*"github:([^/"]+/[^/@"]+)',l): o.add(m.group(1).lower())
    except OSError: pass
    return o
def main():
    q=" ".join(a for a in sys.argv[1:] if not a.startswith("--")); n=int(os.environ.get("N","8"))
    t=time.time()
    r=get("https://skills.sh/api/search?"+urllib.parse.urlencode({"q":q,"limit":20}))
    sk=sorted(r.get("skills",[]),key=lambda s:-s.get("installs",0))[:n]
    loc,org=locales(),origenes()
    print(f"[{len(r.get('skills',[]))} resultados para «{q}»; mostrando {len(sk)}; consulta {time.time()-t:.1f}s; solo lectura]")
    for s in sk:
        src=s.get("source","");name=s["name"]
        if name in loc: est="YA TENEMOS (mismo nombre)"
        elif src.lower() in org: est="YA TENEMOS (misma fuente en CATALOGO)"
        else: est="nueva"
        try:
            a=get("https://www.skills.sh/tele/audit?"+urllib.parse.urlencode({"source":src,"skills":s.get("skillId",name)})).get(s.get("skillId",name),{})
            au=" ".join(f"{k}:{v.get('risk')}" for k,v in a.items()) or "sin auditoría"
        except Exception: au="auditoría n/d"
        of="org-conocida" if src.split("/")[0].lower() in OFICIALES else "autor-externo"
        print(f"- {src}@{name} · {s.get('installs',0)} inst · {est} · {of} · {au}")
    print("Nada se instaló. Un candidato 'nueva' entra SOLO por la cuarentena (cuarentena-skills): leer lo marcado, auditar y recién con el OK de la persona se promueve.")
if __name__=="__main__":
    main()
