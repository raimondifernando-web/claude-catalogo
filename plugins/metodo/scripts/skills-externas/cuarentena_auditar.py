#!/usr/bin/env python3
"""cuarentena_auditar.py <carpeta-work-de-la-cuarentena> — PROTOTIPO. Solo lectura sobre la cuarentena y sobre ~/.claude.
Para cada skill traída a <work>/.claude/skills/<n>: auditor oficial nuestro + controles extra + comparación con lo que ya tenemos
+ auditorías públicas de skills.sh. Escribe un informe en Markdown por stdout. No instala nada ni toca el ecosistema.
Disparador: lo corre cuarentena-skills justo después de traer los candidatos (paso 3 del flujo)."""
import glob, importlib.util, json, os, re, subprocess, sys, urllib.parse, urllib.request
from pathlib import Path

HOME = Path.home()
CFG = Path(os.environ.get("CLAUDE_CONFIG_DIR") or HOME / ".claude")


def _primero(*candidatos):
    for c in candidatos:
        for x in sorted(glob.glob(str(c))):
            if Path(x).is_file():
                return Path(x)
    return None


# El auditor oficial (skill skill-security-auditor) vive en ~/.claude/skills o, en un cliente, en la caché de un plugin.
AUDITOR = _primero(CFG / "skills/skill-security-auditor/scripts/skill_security_auditor.py",
                   CFG / "plugins/cache/*/*/*/skills/skill-security-auditor/scripts/skill_security_auditor.py")
# repetidos.py (comparación por descripción) es opcional: se indica con REPETIDOS_PY; si no está, se compara por nombre.
REPETIDOS = _primero(os.environ.get("REPETIDOS_PY") or "/no-existe", Path(__file__).resolve().parent / "repetidos.py")
CODE = {".py", ".sh", ".bash", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".rb", ".pl", ".ps1", ".bat", ".swift", ".go", ".rs"}
TEXT = {".md", ".txt", ".json", ".yaml", ".yml", ".csv", ".xml", ".html", ".css", ".svg", ".toml", ""}
# Archivos que un test runner / gestor de paquetes ejecutaría solo (vector Gecko). Los que corren código bloquean siempre;
# `package.json` y `*.config.<json|yaml|toml>` solo bloquean si pueden ejecutar algo (ver peligroso_por_contenido).
TESTISH = re.compile(r"(\.test\.|\.spec\.|^conftest\.py$|^__tests__$|^tests?$|\.config\.(js|cjs|mjs|ts|py)$|^pyproject\.toml$|^Makefile$|^setup\.py$|^tox\.ini$)")


def peligroso_por_contenido(p):
    """package.json solo es un riesgo si declara scripts/bin/dependencias (npm podría ejecutarlos); como dato puro no."""
    if p.name != "package.json":
        return None
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return "package.json ilegible o inválido"
    claves = [k for k in ("scripts", "bin", "dependencies", "devDependencies", "optionalDependencies", "peerDependencies") if d.get(k)]
    return f"package.json con {', '.join(claves)} (npm podría ejecutarlo)" if claves else None


PIPE_SH = re.compile(r"(curl|wget)[^\n|]*\|\s*(sudo\s+)?(ba|z)?sh|base64\s+(-d|--decode)[^\n]*\|\s*(ba|z)?sh|\beval\s*\$\(", re.I)
INSTALL = re.compile(r"\b(npm (i|install)|pip3? install|brew install|npx [@\w/.-]+|curl [^\n]*-o|apt(-get)? install|gem install|go install|cargo install)\b")
SECRETISH = re.compile(r"\b([A-Z][A-Z0-9_]*(API_KEY|TOKEN|SECRET|PASSWORD)[A-Z0-9_]*)\b")
URL = re.compile(r"https?://([A-Za-z0-9.-]+)")


def sh(cmd):
    return subprocess.run(cmd, capture_output=True, text=True).stdout


def frontmatter(texto):
    m = re.match(r"---\n(.*?)\n---", texto, re.S)
    if not m:
        return None, "sin encabezado"
    try:
        import yaml
        d = yaml.safe_load(m.group(1))
        return (d if isinstance(d, dict) else None), (None if isinstance(d, dict) else "encabezado no es un mapa")
    except Exception as e:
        return None, f"YAML inválido: {str(e)[:80]}"


def cargar_repetidos():
    if REPETIDOS is None:
        return None
    spec = importlib.util.spec_from_file_location("repetidos_mod", REPETIDOS)
    mod = importlib.util.module_from_spec(spec)
    sys.modules['repetidos_mod'] = mod
    spec.loader.exec_module(mod)
    return mod


class _Pz:
    def __init__(self, name, origin):
        self.name, self.origin, self.description = name, origin, ""


def locales(rep):
    if rep is None:  # sin repetidos.py: solo nombres de skills ya instaladas
        out = [_Pz(p.parent.name, "personal") for p in CFG.glob("skills/*/SKILL.md")]
        out += [_Pz(p.parent.name, "plugin") for p in CFG.glob("plugins/cache/*/*/*/skills/*/SKILL.md")]
        return out
    piezas = list(rep.recolectar_skills_personales(set()))
    try:
        piezas += rep.recolectar_piezas_de_plugins(rep.leer_settings())
    except Exception:
        pass
    return piezas


def parecidas(rep, cand, piezas, n=3):
    if rep is None or cand is None:
        return []
    textos = [rep.tokenizar(p.name + " " + p.description) for p in piezas] + [rep.tokenizar(cand.name + " " + cand.description)]
    vec = rep.construir_vectores_tfidf(textos)
    c = vec[-1]
    out = sorted(((rep.similitud_coseno(c, vec[i]), piezas[i]) for i in range(len(piezas))), key=lambda x: -x[0])[:n]
    return [(round(s, 2), p.name, p.origin) for s, p in out]


def publicas(source, skill):
    try:
        u = "https://www.skills.sh/tele/audit?" + urllib.parse.urlencode({"source": source, "skills": skill})
        d = json.load(urllib.request.urlopen(u, timeout=15)).get(skill, {})
        return " ".join(f"{k}:{v.get('risk')}" for k, v in d.items()) or "sin datos"
    except Exception:
        return "n/d"


def auditar(skill_dir, lock, rep, piezas):
    nombre = skill_dir.name
    bloquea, leer, info = [], [], []
    archivos = [p for p in skill_dir.rglob("*") if p.is_file() or p.is_symlink()]
    # 1) controles estructurales
    for p in archivos:
        rel = p.relative_to(skill_dir)
        if p.is_symlink():
            bloquea.append(f"symlink: {rel} -> {os.readlink(p)}")
        elif any(TESTISH.search(part) for part in rel.parts):
            bloquea.append(f"archivo de pruebas/config que un test runner ejecutaría solo (vector Gecko): {rel}")
        elif peligroso_por_contenido(p):
            bloquea.append(f"{peligroso_por_contenido(p)} (vector Gecko): {rel}")
        elif p.suffix.lower() in CODE:
            leer.append(f"código ejecutable: {rel} ({p.stat().st_size} B)")
        elif p.suffix.lower() not in TEXT:
            bloquea.append(f"archivo no-texto: {rel}")
        if p.name.startswith(".") and p.name != ".gitkeep":
            leer.append(f"archivo oculto: {rel}")
        if p.name in ("CLAUDE.md", "AGENTS.md", "GEMINI.md", ".cursorrules"):
            leer.append(f"archivo de instrucciones para agentes dentro de la skill: {rel}")
        if p.name in ("hooks.json", "settings.json", "settings.local.json", ".mcp.json"):
            bloquea.append(f"configuración que cambiaría el comportamiento del agente: {rel}")
    skill_md = skill_dir / "SKILL.md"
    texto = skill_md.read_text(encoding="utf-8", errors="replace") if skill_md.is_file() else ""
    fm, err = frontmatter(texto)
    if not skill_md.is_file():
        bloquea.append("no tiene SKILL.md")
    elif err:
        bloquea.append(f"encabezado de SKILL.md: {err} (rompe el marketplace: catalogo-check lo frenaría)")
    else:
        desc = str(fm.get("description", ""))
        if len(desc) > 1024:
            bloquea.append(f"description de {len(desc)} caracteres (>1024)")
        if fm.get("name") and fm["name"] != nombre:
            leer.append(f"name del encabezado ({fm['name']}) ≠ carpeta ({nombre})")
        at = str(fm.get("allowed-tools", ""))
        if re.search(r"\bBash\b(?!\()", at):
            leer.append(f"allowed-tools con Bash sin restringir: {at}")
    # 2) texto completo: patrones peligrosos, instalaciones, hosts, secretos
    corpus = ""
    for p in archivos:
        if p.is_file() and not p.is_symlink() and p.suffix.lower() in TEXT | CODE:
            corpus += f"\n#### {p.relative_to(skill_dir)}\n" + p.read_text(encoding="utf-8", errors="replace")
    for m in PIPE_SH.finditer(corpus):
        bloquea.append(f"descarga-y-ejecuta / eval: «{m.group(0)[:70]}»")
    inst = sorted(set(m.group(0) for m in INSTALL.finditer(corpus)))
    if inst:
        leer.append("instrucciones de instalar cosas: " + "; ".join(inst[:6]))
    hosts = sorted(set(h.lower().rstrip(".") for h in URL.findall(corpus)))
    if hosts:
        info.append(f"{len(hosts)} dominios mencionados: " + ", ".join(hosts[:12]) + (" …" if len(hosts) > 12 else ""))
    sec = sorted(set(m.group(1) for m in SECRETISH.finditer(corpus)))
    if sec:
        leer.append("pide/menciona credenciales (por nombre): " + ", ".join(sec[:6]))
    # 3) auditor oficial nuestro (lee cada hallazgo contra el propósito: acá solo se listan)
    salida = re.sub(r"\x1b\[[0-9;]*m", "", sh(["python3", "-I", str(AUDITOR), str(skill_dir)])) if AUDITOR else ""
    veredicto = re.search(r"Verdict:\s*(\S+\s*\S*)", salida)
    hall = re.findall(r"^(?:🔴|🟡) (\w+) \[([A-Z-]+)\] (\S+?)(?::(\d+))?\s*$", salida, re.M)
    hall_txt = [f"{sev} {cat} en {Path(f).name}{':' + l if l else ''}" for sev, cat, f, l in hall]
    # 4) repetidos
    pieza = rep.construir_pieza_skill(skill_md, "cuarentena") if (rep and skill_md.is_file()) else None
    par = parecidas(rep, pieza, piezas) if pieza else []
    mismo_nombre = [p.origin for p in piezas if p.name == nombre]
    # 5) tamaño
    tot = sum(p.stat().st_size for p in archivos if p.is_file() and not p.is_symlink())
    src = lock.get(nombre, {}).get("source", "?")
    pub = publicas(src, nombre) if src != "?" else "n/d"
    solo_texto = not any(p.suffix.lower() in CODE for p in archivos if p.is_file())
    if bloquea:
        dec = "NO ENTRA (bloqueo automático)"
    elif leer or hall_txt:
        dec = "ENTRA SOLO TRAS LECTURA HUMANA de lo marcado"
    else:
        dec = "LIMPIA para el siguiente paso (lectura + OK de la persona)"
    r = [f"### {nombre}  ·  fuente `{src}`", f"**Decisión del filtro:** {dec}",
         f"- Tipo: {'puro texto (puede ir por camino 3 de XVI si se lee entero)' if solo_texto else 'CON CÓDIGO (necesita camino 1 o 2 de XVI)'} · {len(archivos)} archivos · {tot/1024:.0f} KB ≈ {tot//4//1000} K tokens para leerla entera",
         f"- Auditor `skill-security-auditor`: {veredicto.group(1).strip() if veredicto else ('NO ENCONTRADO: solo valen los controles de esta cuarentena' if not AUDITOR else '?')}" + (" — hallazgos: " + "; ".join(hall_txt[:6]) if hall_txt else ""),
         f"- Auditorías públicas skills.sh (orientativas, discrepan): {pub}"]
    for b in bloquea:
        r.append(f"- ⛔ {b}")
    for l in leer:
        r.append(f"- 👁 leer: {l}")
    for i in info:
        r.append(f"- ℹ {i}")
    r.append(f"- Ya tenemos con el mismo nombre: {', '.join(mismo_nombre) if mismo_nombre else 'no'}")
    r.append("- Más parecidas (coseno de descripción): " + "; ".join(f"{n} ({o}) {s}" for s, n, o in par))
    return "\n".join(r)


def main():
    work = Path(sys.argv[1])
    lock = json.loads((work / "skills-lock.json").read_text()).get("skills", {}) if (work / "skills-lock.json").is_file() else {}
    rep = cargar_repetidos()
    piezas = locales(rep)
    dirs = sorted(p for p in (work / ".claude/skills").iterdir() if p.is_dir() or p.is_symlink())
    print(f"# Informe de cuarentena — {len(dirs)} skill(s) · comparadas contra {len(piezas)} piezas locales" + ("" if rep else " (solo por nombre)") + "\n")
    for d in dirs:
        print(auditar(d, lock, rep, piezas) + "\n")


if __name__ == "__main__":
    main()
