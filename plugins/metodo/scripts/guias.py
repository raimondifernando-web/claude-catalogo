#!/usr/bin/env python3
"""guias.py: adjunta al pedido para OTRA IA (Codex, Gemini) el texto de las skills que el pedido nombra.

Codex y Gemini no ven las skills de Claude: reciben solo el texto del pedido. Este programa mira qué skills nombra
el pedido (o cuáles se piden con --skills) y pega su SKILL.md al principio, con tope de tamaño. Sirve para las dos IA
sin instalar nada en ellas. Lo usan delegar.py, agy-delegar e ia-en-rama (cada uno con su opción --skills).

Uso como programa:  guias.py adjuntar [--skills a,b] [--repo RUTA] < pedido.txt   → pedido final por stdout,
                    resumen («Guías adjuntas: …») por stderr. Siempre sale 0 (ante un problema devuelve el pedido tal cual).
Como módulo:        adjuntar(texto, extra=(), repo=None) → (texto_final, adjuntas, avisos)
Formas que cuentan como «nombrar» una skill: /nombre, `nombre`, «skill nombre», «nombre skill», Skill(nombre).
No se adjuntan: skills de la sesión de Claude (arrancar, cerrar…), skills con forma de clave adentro, ni más de TOPE_TOTAL.
Se apaga con GUIAS_OFF=1.
Disparador: encadenado a delegar.py / agy-delegar / ia-en-rama (cada delegación lo corre sola; probado en tests/test_guias.py)."""
import glob
import os
import re
import sys

TOPE_UNA = 12 * 1024      # una guía
TOPE_TOTAL = 24 * 1024    # todas juntas
SOLO_SESION_CLAUDE = {"arrancar", "cerrar", "fable-start", "vigia", "pendientes", "radar", "cowork", "buzon", "otra-sesion",
                      "planear", "criticar", "crear-agente", "session-handoff", "schedule", "loop", "darwin-skill",
                      "buscar-skill-externa", "fable-plan", "fable-critic", "fable-fixer"}
FORMA_DE_CLAVE = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY|\bsk-[A-Za-z0-9]{20,}|\bghp_[A-Za-z0-9]{20,}|"
                            r"(?i:api[_-]?key|secret|token)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{24,}")
USA_CONECTORES = re.compile(r"mcp__|Claude in Chrome|\bconector(es)?\b|\bMCP\b")


def skills_conocidas(repo=None):
    cfg = os.environ.get("CLAUDE_CONFIG_DIR", os.path.expanduser("~/.claude"))
    rutas = {}
    pats = [cfg + "/skills/*/SKILL.md"]
    if repo:
        pats.append(os.path.join(repo, ".claude", "skills", "*", "SKILL.md"))
    pats.append(cfg + "/plugins/cache/*/*/*/skills/*/SKILL.md")
    for pat in pats:
        for f in sorted(glob.glob(pat), reverse=True):  # la versión más nueva primero
            rutas.setdefault(os.path.basename(os.path.dirname(f)), f)
    return rutas


def nombradas(texto, conocidas):
    hallo = set()
    for nom in conocidas:
        e = re.escape(nom)
        if (re.search(r"(?<![\w/.-])/(?:[\w-]+:)?" + e + r"(?![\w-])", texto)
                or re.search(r"`(?:[\w-]+:)?" + e + r"`", texto)
                or re.search(r"(?i)\bskills?\b[\s:`\"'(]{1,4}(?:[\w-]+:)?" + e + r"(?![\w-])", texto)
                or re.search(r"(?i)(?<![\w-])" + e + r"[`\"']?\s+skill\b", texto)
                or re.search(r"Skill\((?:[\w-]+:)?" + e + r"\)", texto)):
            hallo.add(nom)
    return sorted(hallo)


def _cuerpo(ruta):
    with open(ruta, encoding="utf-8", errors="replace") as f:
        t = f.read()
    m = re.match(r"---\r?\n.*?\r?\n---\r?\n", t, re.S)
    return t[m.end():] if m else t


def adjuntar(texto, extra=(), repo=None):
    """(texto_final, [adjuntas], [avisos]). Nunca lanza: ante un error devuelve el texto como vino."""
    if os.environ.get("GUIAS_OFF"):
        return texto, [], []
    try:
        conocidas = skills_conocidas(repo)
        avisos, pedidas = [], []
        for n in extra:
            n = n.strip()
            if not n:
                continue
            if n in conocidas:
                pedidas.append(n)
            else:
                avisos.append("la skill «%s» no existe: no se adjunta" % n)
        for n in nombradas(texto, conocidas):
            if n not in pedidas:
                pedidas.append(n)
        bloques, adjuntas, total = [], [], 0
        for n in pedidas:
            if n in SOLO_SESION_CLAUDE:
                avisos.append("«%s» es de la sesión de Claude: no se adjunta" % n)
                continue
            cuerpo = _cuerpo(conocidas[n]).strip()
            if FORMA_DE_CLAVE.search(cuerpo):
                avisos.append("«%s» tiene algo con forma de clave: no se adjunta" % n)
                continue
            if USA_CONECTORES.search(cuerpo):
                avisos.append("«%s» usa conectores de Claude que esta IA no tiene: conviene que lo haga un agente de Claude" % n)
            if len(cuerpo.encode()) > TOPE_UNA:
                cuerpo = cuerpo.encode()[:TOPE_UNA].decode("utf-8", "ignore") + "\n[…guía recortada por tamaño]"
                avisos.append("«%s» se recortó a %d KB" % (n, TOPE_UNA // 1024))
            if total + len(cuerpo.encode()) > TOPE_TOTAL:
                avisos.append("«%s» no entra (tope de %d KB de guías)" % (n, TOPE_TOTAL // 1024))
                continue
            total += len(cuerpo.encode())
            adjuntas.append(n)
            bloques.append("=== GUÍA «%s» (seguí estas instrucciones para lo que toca a la tarea) ===\n%s\n=== FIN DE LA GUÍA «%s» ===" % (n, cuerpo, n))
        if not bloques:
            return texto, [], avisos
        return "\n\n".join(bloques) + "\n\n=== TAREA ===\n" + texto, adjuntas, avisos
    except Exception as e:  # nunca rompe la delegación
        return texto, [], ["no pude adjuntar guías (%s): el pedido sale tal cual" % e.__class__.__name__]


def resumen(adjuntas, avisos):
    partes = []
    if adjuntas:
        partes.append("Guías adjuntas: " + ", ".join(adjuntas))
    partes += ["Aviso de guías: " + a for a in avisos]
    return "\n".join(partes)


def main(argv):
    if len(argv) < 2 or argv[1] != "adjuntar":
        sys.stderr.write("Uso: guias.py adjuntar [--skills a,b] [--repo RUTA] < pedido.txt\n")
        return 64
    extra, repo, i = [], None, 2
    while i < len(argv):
        if argv[i] == "--skills" and i + 1 < len(argv):
            extra = argv[i + 1].split(","); i += 2
        elif argv[i] == "--repo" and i + 1 < len(argv):
            repo = argv[i + 1]; i += 2
        else:
            sys.stderr.write("Opción desconocida: %s\n" % argv[i]); return 64
    texto = sys.stdin.read()
    final, adj, avisos = adjuntar(texto, extra, repo)
    sys.stdout.write(final)
    r = resumen(adj, avisos)
    if r:
        sys.stderr.write(r + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
