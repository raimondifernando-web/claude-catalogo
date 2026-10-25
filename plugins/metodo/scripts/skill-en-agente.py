#!/usr/bin/env python3
"""PreToolUse (Agent|Task): avisa cuando el pedido a un ayudante nombra una skill y ese ayudante
NO puede cargarla (su lista `tools:` no trae `Skill`). Regla 22: los subagentes no heredan skills, y
si además no tienen la herramienta, nombrarlas no alcanza y el fallo pasa en silencio.

Frena UNA vez por pedido (el mismo pedido reintentado pasa). Propone: (1) un ayudante del mismo
oficio que sí la carga, (2) pegar la guía: pasarle la ruta del SKILL.md para que lo lea con Read.
Disparador: automático (PreToolUse de Agent|Task). Se apaga con SKILL_EN_AGENTE_OFF=1.
Nunca rompe la sesión: ante cualquier error, deja pasar."""
import glob, hashlib, json, os, re, sys, tempfile, time

CFG = os.environ.get("CLAUDE_CONFIG_DIR", os.path.expanduser("~/.claude"))
# Ayudantes que trae Claude Code y no salen de ningún archivo (sin la herramienta Skill).
INTEGRADOS_SIN_SKILL = {"claude-code-guide", "statusline-setup"}


def _fm(path):
    try:
        t = open(path, encoding="utf-8", errors="ignore").read(6000)
    except OSError:
        return None
    m = re.match(r"---\r?\n(.*?)\r?\n---", t, re.S)
    if not m:
        return None
    fm = m.group(1)
    n = re.search(r"^name:\s*(.+)$", fm, re.M)
    if not n or not re.search(r"^description:", fm, re.M):
        return None
    tl = re.search(r"^tools:\s*(.*)$", fm, re.M)
    return n.group(1).strip().strip("\"'"), (tl.group(1).strip() if tl else "*")


def puede_skill(tools):
    return tools in ("*", "") or "Skill" in tools


def indice_agentes(cwd):
    """{nombre_corto: [(plugin_o_'', tools, ruta)]}"""
    idx = {}
    pats = [(CFG + "/agents/*.md", ""), (cwd + "/.claude/agents/*.md", "")]
    for p in glob.glob(CFG + "/plugins/cache/*/*/*"):
        plug = p.split(os.sep)[-3]
        pats += [(p + "/agents/**/*.md", plug), (p + "/*.md", plug)]
    for pat, plug in pats:
        for f in glob.glob(pat, recursive=True):
            r = _fm(f)
            if r:
                idx.setdefault(r[0], []).append((plug, r[1], f))
    return idx


def tools_de(idx, subagent):
    plug, _, nombre = subagent.rpartition(":")
    if nombre in INTEGRADOS_SIN_SKILL:
        return "Read", nombre
    cand = idx.get(nombre)
    if not cand:
        return None, nombre  # no lo conozco: no digo nada
    if plug:
        cand = [c for c in cand if c[0] == plug] or cand
    if any(puede_skill(c[1]) for c in cand) and not all(puede_skill(c[1]) for c in cand):
        return None, nombre  # ambiguo entre copias: no digo nada
    return cand[0][1], nombre


def skills_conocidas(cwd):
    rutas = {}
    for pat in (CFG + "/skills/*/SKILL.md", cwd + "/.claude/skills/*/SKILL.md",
                CFG + "/plugins/cache/*/*/*/skills/*/SKILL.md"):
        for f in glob.glob(pat):
            rutas.setdefault(os.path.basename(os.path.dirname(f)), f)
    return rutas


def skills_nombradas(prompt, conocidas):
    """Solo formas claras (precisión antes que cobertura): /nombre, `nombre`, 'skill nombre', 'nombre skill', Skill(nombre)."""
    hallo = set()
    for nom in conocidas:
        e = re.escape(nom)
        if (re.search(r"(?<![\w/.-])/(?:[\w-]+:)?" + e + r"(?![\w-])", prompt)
                or re.search(r"`(?:[\w-]+:)?" + e + r"`", prompt)
                or re.search(r"(?i)\bskills?\b[\s:`\"'(]{1,4}(?:[\w-]+:)?" + e + r"(?![\w-])", prompt)
                or re.search(r"(?i)(?<![\w-])" + e + r"[`\"']?\s+skill\b", prompt)
                or re.search(r"Skill\((?:[\w-]+:)?" + e + r"\)", prompt)):
            hallo.add(nom)
    return sorted(hallo)


def alternativas(idx, nombre):
    """Mismo oficio con Skill: mismo nombre corto en otro paquete, o genéricos con todas las herramientas."""
    alts = []
    for plug, tools, _ in idx.get(nombre, []):
        if puede_skill(tools):
            alts.append(f"{plug + ':' if plug else ''}{nombre}")
    return list(dict.fromkeys(alts))[:3] + ["general-purpose (carga cualquier skill)"]


def main():
    if os.environ.get("SKILL_EN_AGENTE_OFF"):
        return 0
    d = json.loads(sys.stdin.read() or "{}")
    if d.get("tool_name") not in ("Agent", "Task"):
        return 0
    ti = d.get("tool_input", {}) or {}
    cwd = d.get("cwd") or os.getcwd()
    sub = ti.get("subagent_type") or "general-purpose"
    prompt = str(ti.get("prompt", ""))
    if not prompt:
        return 0
    idx = indice_agentes(cwd)
    tools, nombre = tools_de(idx, sub)
    if tools is None or puede_skill(tools):
        return 0
    conocidas = skills_conocidas(cwd)
    nom = skills_nombradas(prompt, conocidas)
    if not nom:
        return 0
    # Si el pedido ya trae la ruta del SKILL.md (el ayudante la lee con Read), está resuelto.
    sin_ruta = [n for n in nom if conocidas[n] not in prompt and "SKILL.md" not in prompt]
    if not sin_ruta:
        return 0
    uid = getattr(os, "getuid", lambda: 0)()
    marca = os.path.join(tempfile.gettempdir(), "skill-en-agente-%s-%s" % (
        uid, hashlib.sha1((sub + prompt).encode()).hexdigest()[:12]))
    if os.path.exists(marca) and time.time() - os.path.getmtime(marca) < 3600:
        return 0  # ya avisé de este mismo pedido: lo dejo pasar
    open(marca, "w").write(str(time.time()))
    try:
        os.makedirs(CFG + "/logs", exist_ok=True)
        with open(CFG + "/logs/skill-en-agente.jsonl", "a") as f:
            f.write(json.dumps({"t": int(time.time()), "agente": sub, "skills": sin_ruta}) + "\n")
    except OSError:
        pass
    rutas = "; ".join(f"{n}: {conocidas[n]}" for n in sin_ruta)
    sys.stderr.write(
        f"⛔ El ayudante «{sub}» NO puede cargar skills (su lista de herramientas no trae Skill), y el pedido nombra: "
        f"{', '.join(sin_ruta)}. Sin la herramienta, nombrarlas no sirve y el fallo pasa en silencio.\n"
        f"Elegí UNA salida y reintentá:\n"
        f"  1) Otro ayudante del mismo oficio que sí las carga: {', '.join(alternativas(idx, nombre))}.\n"
        f"  2) Seguir con este, pero pegando la guía en el pedido: pasale la ruta para que la lea con Read → {rutas}\n"
        f"Es un aviso de UNA vez: si reintentás el mismo pedido, pasa.\n")
    return 2


try:
    sys.exit(main())
except SystemExit:
    raise
except Exception:
    sys.exit(0)
