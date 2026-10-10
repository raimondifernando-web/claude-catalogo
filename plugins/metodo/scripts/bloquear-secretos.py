#!/usr/bin/env python3
"""bloquear-secretos.py — freno PreToolUse de Bash: frena los comandos que MUESTRAN el valor de un secreto
(contraseña, llave, token) en pantalla, donde quedaría guardado en el historial de la sesión.

Contrato del hook: stdin = JSON {tool_name, tool_input:{command}}; exit 0 = deja pasar; exit 2 + stderr = frena.
Ante cualquier error NO frena (exit 0): nunca rompe Bash.

Cómo decide: parte el comando en comandos simples (respetando comillas, sin mirar comentarios) y mira, para cada
uno, el programa que corre y sus argumentos. Frena solo si un programa que IMPRIME contenido (cat, sed, awk, jq,
grep sin contar, python que abre el archivo…) recibe un archivo de secretos (.env, llaves, .npmrc…), si se imprime
una variable que parece secreta (SECRET, TOKEN, KEY…), o si se vuelca todo el entorno. Mencionar ".env" o
process.env.X en un texto o en un programa que no lo imprime NO frena. El cuerpo de un heredoc se mira solo si lo
recibe una shell (bash <<X) o un intérprete (python - <<X); si lo recibe cat o un archivo, es texto.

Límites conocidos (no se cubren): buscar con grep -r sin nombrar el archivo, find -exec, ssh a otra máquina.
"""
import json
import re
import sys

I = re.IGNORECASE
SECRETISH = (r"(?:SECRET|TOKEN|PASSWORD|PASSWD|API_?KEY|APIKEY|CREDENTIAL|PRIVATE_?KEY|CLIENT_SECRET|ACCESS_KEY"
             r"|AUTH_?TOKEN|BEARER|[A-Z0-9]_KEY\b|\bPASS\b|_PASS\b|_PWD\b)")
SUFIJO_NO_SECRETO = re.compile(r"_(?:FILE|PATH|DIR|NAME|URL|ID|LEN|COUNT)$", I)
LECTORES = {"cat", "bat", "less", "more", "head", "tail", "nl", "tac", "xxd", "od", "strings", "view", "fold", "pr",
            "fmt", "awk", "gawk", "sed", "jq", "yq", "sort", "uniq", "cut", "paste", "column", "expand", "unexpand",
            "rev", "tr", "dd", "xargs", "base64", "hexdump", "diff", "comm", "join"}
GREPS = {"grep", "egrep", "fgrep", "rg", "ag", "ack", "zgrep"}
INTERPRETES = {"python", "python2", "python3", "ruby", "perl", "node", "deno", "bun", "php"}
SHELLS = {"bash", "sh", "zsh", "dash"}
ECHOS = {"echo", "printf", "print"}
ENVOLTURAS = {"sudo", "command", "builtin", "time", "nohup", "nice", "exec", "stdbuf", "env", "timeout", "xcrun"}
PALABRAS = {"then", "do", "else", "elif", "if", "while", "until", "fi", "!", "{", "}", "case", "esac", "function"}
SUMIDEROS = {"wc", "sha1sum", "sha256sum", "sha512sum", "shasum", "md5", "md5sum", "cksum"}
SIN_SALIDA = re.compile(r"^\s*(?:[A-Za-z_][A-Za-z0-9_]*=|export\b|eval\b|declare\b|local\b|readonly\b|typeset\b|source\b|\.\s|set\b|\[\[?\s|test\b)")
SIN_VALOR = r"(?:example|sample|template|dist|defaults?|md)"
LOGIN_STDIN = ("--with-token", "--password-stdin")
DESTINOS_PANTALLA = ("/dev/stderr", "/dev/stdout", "/dev/tty", "/dev/fd/1", "/dev/fd/2")


def es_archivo_secreto(tok):
    """¿el argumento es (la ruta de) un archivo de secretos? Compara el nombre completo, no un pedazo de texto."""
    t = tok.strip("'\"<>")
    if not t or t.startswith("-"):
        return False
    base = t.rstrip("/").split("/")[-1]
    if re.fullmatch(r"\.env(?:\.[^/]*)?|.*\.env|\.env[*?\[].*", base, I):
        return not re.fullmatch(r"\.env\." + SIN_VALOR, base, I)
    if re.fullmatch(r"\.modal\.toml|.+\.(?:pem|key|p12|pfx)|id_rsa|id_ed25519|id_ecdsa|\.npmrc|\.netrc|\.pypirc|"
                    r"\.envrc|\.git-credentials|credentials\.json|\.pgpass|\.htpasswd|secrets?\.(?:json|ya?ml|toml|env)", base, I):
        return True
    return bool(re.search(r"(?:^|/)gh(?:-claude)?/hosts\.yml$|(?:^|/)\.aws/credentials$", t, I))


def extraer_heredocs(cmd):
    """→ (texto sin cuerpos de heredoc, lista de cuerpos). Cada `<<X` pasa a `<<__HDn__`. Respeta comillas,
    comentarios, `<<<` y la aritmética `$((1<<B))`."""
    out, cuerpos, pend, q, i, n = [], [], [], "", 0, len(cmd)
    while i < n:
        ch = cmd[i]
        sig = cmd[i + 1] if i + 1 < n else ""
        if q:
            out.append(ch)
            if ch == q:
                q = ""
            elif ch == "\\" and q == '"' and sig:
                out.append(sig)
                i += 1
        elif ch in "'\"":
            q = ch
            out.append(ch)
        elif ch == "\\" and sig:
            out.append(ch + sig)
            i += 2
            continue
        elif ch == "#" and (i == 0 or cmd[i - 1] in " \t\n;&|("):
            while i < n and cmd[i] != "\n":
                i += 1
            continue
        elif ch == "<" and sig == "<" and cmd[i + 2:i + 3] != "<" and (i == 0 or cmd[i - 1] != "<"):
            reciente = "".join(out[-40:])
            aritmetica = "$((" in reciente and "))" not in reciente.split("$((")[-1]
            m = None if aritmetica else re.match(r"<<(-?)\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\2", cmd[i:])
            if m:
                cuerpos.append("")
                pend.append((len(cuerpos) - 1, m.group(3), bool(m.group(1))))
                out.append(f"<<__HD{len(cuerpos) - 1}__")
                i += m.end()
                continue
            out.append(ch)
        elif ch == "\n" and pend:
            out.append(ch)
            i += 1
            for idx, delim, quita in pend:
                lineas = []
                while i < n:
                    j = cmd.find("\n", i)
                    j = n if j < 0 else j
                    linea = cmd[i:j]
                    i = j + 1
                    if (linea.strip() if quita else linea) == delim:
                        break
                    lineas.append(linea)
                cuerpos[idx] = "\n".join(lineas)
            pend = []
            continue
        else:
            out.append(ch)
        i += 1
    return "".join(out), cuerpos


def partir(cmd):
    """→ lista de pipelines; cada pipeline = lista de etapas; cada etapa = lista de palabras.
    Respeta comillas; descarta comentarios; ( ) { } if/then/do separan o se saltean."""
    pipes, etapas, toks = [], [], []
    st = {"cur": "", "hay": False, "sub": 0}

    def cerrar_tok():
        if st["hay"] or st["cur"]:
            toks.append(st["cur"])
        st["cur"], st["hay"] = "", False

    def cerrar_etapa():
        nonlocal toks
        cerrar_tok()
        if toks:
            etapas.append(toks)
        toks = []

    def cerrar_pipe():
        nonlocal etapas
        cerrar_etapa()
        if etapas:
            pipes.append(etapas)
        etapas = []

    q, i, n = "", 0, len(cmd)
    while i < n:
        ch = cmd[i]
        sig = cmd[i + 1] if i + 1 < n else ""
        if q:
            if ch == q:
                q = ""
            elif ch == "\\" and q == '"' and sig:
                st["cur"] += sig
                i += 1
            else:
                st["cur"] += ch
        elif ch in "'\"":
            q, st["hay"] = ch, True
        elif ch == "\\" and sig:
            st["cur"] += sig
            i += 1
        elif ch == "#" and not st["cur"] and not st["hay"]:
            while i < n and cmd[i] != "\n":
                i += 1
            continue
        elif ch in " \t":
            cerrar_tok()
        elif ch in "\n;":
            cerrar_pipe()
        elif ch == "(":
            if st["cur"].endswith("$") or st["sub"] > 0:
                st["cur"] += ch
                st["sub"] += 1
            else:
                cerrar_pipe()
        elif ch == ")":
            if st["sub"] > 0:
                st["cur"] += ch
                st["sub"] -= 1
            else:
                cerrar_pipe()
        elif ch == "&" and sig == "&":
            cerrar_pipe()
            i += 1
        elif ch == "&" and (sig == ">" or st["cur"][-1:] in (">", "<")):
            st["cur"] += ch
        elif ch == "&":
            cerrar_pipe()
        elif ch == "|" and sig == "|":
            cerrar_pipe()
            i += 1
        elif ch == "|":
            cerrar_etapa()
        else:
            st["cur"] += ch
        i += 1
    cerrar_pipe()
    return pipes


def programa(toks):
    """→ (nombre en minúscula, argumentos) saltando VAR=x, redirecciones iniciales, palabras de control y envolturas."""
    j = 0
    while j < len(toks):
        t = toks[j]
        previo = toks[j - 1] if j else ""
        if re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", t) or (t in ENVOLTURAS and j + 1 < len(toks)) or t in PALABRAS:
            j += 1
        elif t in ("<", ">", ">>") or re.match(r"^\d*[<>]", t) and not re.match(r"^[<>]\S", t):
            j += 2 if t in ("<", ">", ">>") else 1
        elif re.match(r"^<[^<]\S*$", t):
            j += 1
        elif j > 0 and previo in ENVOLTURAS and (t.startswith("-") or re.fullmatch(r"\d+[smhd]?", t)):
            j += 2 if previo == "sudo" and t in ("-u", "-g", "-h", "-p", "-C", "-D", "-R", "-T") else 1
        else:
            break
    if j >= len(toks):
        return "", []
    return toks[j].split("/")[-1].lower(), toks[j + 1:]


def entradas_stdin(toks):
    """Archivos que entran por `< archivo` / `<archivo` en cualquier lugar de la etapa."""
    out = []
    for k, t in enumerate(toks):
        if t == "<" and k + 1 < len(toks):
            out.append(toks[k + 1])
        elif re.match(r"^<[^<]\S*$", t):
            out.append(t[1:])
    return out


def stdout_fuera_de_pantalla(toks):
    """¿la salida de la etapa va a un archivo (y no a /dev/stderr, /dev/tty…)?"""
    for k, a in enumerate(toks):
        m = re.match(r"^(?:1?>>?|&>>?)(.*)$", a)
        if m and not a.startswith(("1>&", ">&")):
            destino = m.group(1) or (toks[k + 1] if k + 1 < len(toks) else "")
            if destino and destino not in DESTINOS_PANTALLA and not destino.startswith("&"):
                return True
    return False


def grep_solo_cuenta(args):
    for a in args:
        if a in ("--count", "--files-with-matches", "--files-without-match", "--quiet", "--silent"):
            return True
        if re.fullmatch(r"-[A-Za-z]+", a) and re.search(r"[clLq]", a):
            return True
    return False


def patron_grep(args):
    for a in args:
        if not a.startswith("-"):
            return a
    return ""


def solo_filtra(despues):
    """¿la salida pasa por un grep que busca algo que no es secreto, o solo cuenta?"""
    for n, a in despues:
        if n in GREPS:
            p = patron_grep(a)
            if grep_solo_cuenta(a) or (re.fullmatch(r"[\^A-Za-z0-9_$]+", p or "") and not re.search(SECRETISH, p, I)):
                return True
    return False


def razones_interprete(texto, args):
    out = []
    abre = re.search(r"""['"][^'"\s]*(?:\.env(?:\.[A-Za-z]+)?|[\w.-]+\.(?:pem|key|p12|pfx)|id_rsa|id_ed25519|"""
                     r"""\.npmrc|\.netrc|credentials\.json|\.pgpass|\.htpasswd|secrets?\.(?:json|ya?ml|toml|env)|"""
                     r"""\.modal\.toml)['"]""", texto, I)
    imprime = re.search(r"print|puts|echo|console|log|write|dump|say|stdout", texto, I)
    lee = re.search(r"open|read|File|IO\.|slurp|get_contents", texto, I)
    if abre and ((lee and imprime) or any(a in ("-p", "-pe") for a in args)):
        out.append("un programa de una línea (python, node…) que abre un archivo de secretos y lo imprime muestra su valor.")
    elif any(re.fullmatch(r"-[a-z]*[np][a-z]*", a) for a in args) and any(es_archivo_secreto(a) for a in args):
        out.append("este programa lee e imprime línea por línea un archivo de secretos.")
    if re.search(r"(?:print|puts|echo|console\.\w+|printf|write|say)[^;\n]*"
                 r"(?:process\.env\.|os\.environ\W{0,3}|ENV\W{0,3}|getenv\W{0,3}|Deno\.env\.get\W{0,3})\w*" + SECRETISH,
                 texto, I):
        out.append("ese programa imprime una variable de entorno que parece secreta (clave, token o contraseña).")
    return out


def nombres_secretos(texto):
    """Variables $X / ${X} del texto cuyo nombre parece secreto (y no termina en _FILE, _PATH…)."""
    hallados = []
    for m in re.finditer(r"\$\{?([A-Za-z_][A-Za-z0-9_]*)", texto):
        nombre = m.group(1)
        if re.search(SECRETISH, nombre, I) and not SUFIJO_NO_SECRETO.search(nombre):
            hallados.append(nombre)
    return hallados


def analizar_pipeline(etapas, razones, profundidad, cuerpos):
    progs = [programa(e) for e in etapas]
    for k, (nom, args) in enumerate(progs):
        toks = etapas[k]
        despues = progs[k + 1:]
        stdin = entradas_stdin(toks)
        if nom == "done":  # bucle que lee un archivo de secretos: while read l; do …; done < archivo
            if any(es_archivo_secreto(f) for f in stdin):
                razones.append("un bucle que lee línea por línea un archivo de secretos puede mostrar sus valores.")
            continue
        if not nom:
            continue
        # lo que se imprime no llega a la pantalla si va a un archivo, a un contador/hash o a un inicio de sesión por stdin
        if stdout_fuera_de_pantalla(toks) or any(n in SUMIDEROS for n, _a in despues) \
                or any(n in ("gh", "docker") and any(x in a for x in LOGIN_STDIN) for n, a in despues):
            continue
        heredocs = [int(m.group(1)) for a in args for m in [re.fullmatch(r"<<__HD(\d+)__", a)] if m]
        cuerpo = "\n".join(cuerpos[h] for h in heredocs if h < len(cuerpos))
        # bash -c "…" / eval "…" / bash <<X: se mira el texto de adentro
        if nom in SHELLS:
            if profundidad < 3:
                for idx, a in enumerate(args):
                    if re.fullmatch(r"-[a-z]*c[a-z]*", a) and idx + 1 < len(args):
                        razones.extend(analizar(args[idx + 1], profundidad + 1))
                if cuerpo:
                    razones.extend(analizar(cuerpo, profundidad + 1))
            continue
        if nom == "eval":
            if profundidad < 3:
                razones.extend(analizar(re.sub(r"\$\([^()]*\)|`[^`]*`", "", " ".join(args)), profundidad + 1))
            continue
        archivos = [a for a in args if es_archivo_secreto(a)] + [f for f in stdin if es_archivo_secreto(f)]
        if nom in LECTORES and archivos:
            inofensivo = (nom == "sed" and any(re.fullmatch(r"-[A-Za-z]*i.*|--in-place.*", a) for a in args)) \
                or (nom == "cut" and any(re.fullmatch(r"-f\s*1|-f1", a) for a in args)) \
                or (nom == "awk" and any(re.fullmatch(r"\{\s*print\s+\$1\s*\}", a) for a in args))
            if not inofensivo:
                razones.append(f"`{nom}` sobre «{archivos[0]}» muestra en pantalla el contenido de un archivo de secretos.")
        elif nom in GREPS and archivos and not grep_solo_cuenta(args):
            razones.append("buscar con grep dentro de un archivo de secretos muestra la línea con el valor. "
                           "Para saber si existe, usá `grep -c '^NOMBRE=' archivo` (cuenta, no muestra).")
        elif nom == "git" and [x for x in args if not x.startswith("-")][:1] == ["show"] \
                and any(":" in a and es_archivo_secreto(a.split(":")[-1]) for a in args):
            razones.append("`git show` de un archivo de secretos muestra su contenido.")
        elif nom in INTERPRETES:
            razones.extend(razones_interprete(" ".join(args) + "\n" + cuerpo, args))
        elif nom in ECHOS:
            texto = " ".join(args)
            texto = re.sub(r"\$\{#[A-Za-z0-9_]+\}", "", texto)                                        # largo: seguro
            texto = re.sub(r"\$\{[A-Za-z0-9_]+:\s*-[1-4]\}|\$\{[A-Za-z0-9_]+:0:[1-4]\}", "", texto)  # 4 letras: seguro
            va_a_otro_programa = bool(despues) and not any(n in LECTORES or n in ("tee", "cat") for n, _a in despues)
            if nombres_secretos(texto) and not va_a_otro_programa:
                razones.append(f"`{nom}` de una variable que parece secreta (clave, token o contraseña) la muestra en pantalla.")
        elif nom in ("printenv", "env", "set", "declare", "typeset", "export"):
            opciones = [a for a in args if a.startswith("-")]
            nombres = [a for a in args if not a.startswith("-")]
            volcado = (nom in ("printenv", "env", "set") and not nombres and not any(re.match(r"^[A-Za-z_]+=", a) for a in args)) \
                or (nom == "export" and "-p" in args) or (nom in ("declare", "typeset") and not nombres and ("-p" in opciones or "-x" in opciones))
            if volcado:
                if not solo_filtra(despues):
                    razones.append(f"`{nom}` sin nombre muestra TODAS las variables del entorno, con sus claves.")
            elif nom == "printenv" and any(re.search(SECRETISH, a, I) for a in nombres):
                razones.append("`printenv` de una variable que parece secreta la muestra en pantalla.")
        elif nom in ("docker", "docker-compose"):
            a = [x for x in args if not x.startswith("-")]
            if (nom == "docker-compose" and a[:1] == ["config"]) or (nom == "docker" and a[:2] == ["compose", "config"]):
                if not any(re.fullmatch(r"--(?:services|images|volumes|profiles|hash|quiet|help|format)(?:=.*)?", x) for x in args):
                    razones.append("`docker compose config` escribe todo el entorno ya resuelto, con las claves. Usá `--services`.")
            if nom == "docker" and a[:1] == ["exec"] and "env" in a[1:]:
                razones.append("`docker exec … env` muestra el entorno del contenedor, con sus claves.")
        elif nom == "git" and [x for x in args if not x.startswith("-")][:2] == ["credential", "fill"]:
            razones.append("`git credential fill` muestra credenciales en claro.")
        elif nom == "gh" and [x for x in args if not x.startswith("-")][:2] == ["auth", "token"]:
            razones.append("`gh auth token` muestra el token de GitHub en claro.")


def analizar(cmd, profundidad=0):
    razones = []
    base, cuerpos = extraer_heredocs(cmd)
    for pipeline in partir(base):
        analizar_pipeline(pipeline, razones, profundidad, cuerpos)
    if profundidad < 3:  # $( … ) y `…`: el comando de adentro también corre, salvo que su salida se guarde o se cargue
        for m in re.finditer(r"\$\(([^()]*)\)|`([^`]*)`", base):
            inicio = max(base.rfind(";", 0, m.start()), base.rfind("\n", 0, m.start()), base.rfind("&", 0, m.start()),
                         base.rfind("|", 0, m.start()), base.rfind("(", 0, m.start() - 1))
            if SIN_SALIDA.match(base[inicio + 1:m.start()]):
                continue
            razones.extend(analizar(m.group(1) or m.group(2) or "", profundidad + 1))
    out = []
    for r in razones:
        if r not in out:
            out.append(r)
    return out


def main():
    try:
        data = json.loads(sys.stdin.read())
        if data.get("tool_name") != "Bash":
            return 0
        cmd = (data.get("tool_input") or {}).get("command") or ""
        if not cmd.strip():
            return 0
        razones = analizar(cmd)
    except Exception:
        return 0
    if not razones:
        return 0
    texto = ["Frené este comando porque puede mostrar una contraseña, una llave o un token en pantalla "
             "(y quedaría guardado en el historial de la conversación):"]
    texto += ["  · " + r for r in razones]
    texto += ["",
              "Formas seguras:",
              "  · ¿existe la variable? → grep -c '^NOMBRE=' archivo   (cuenta, no muestra el valor)",
              "  · ¿anda la llave? → probala con un pedido que solo devuelva el estado (curl -s -o /dev/null -w '%{http_code}' …)",
              "  · ¿cuál es? → mostrá solo el largo o las últimas 4 letras: echo \"largo=${#NOMBRE} …${NOMBRE: -4}\"",
              "Las claves las carga la persona dueña de la cuenta; Claude no las lee ni las escribe. "
              "Si de verdad hace falta verlas, pedíselo a ella."]
    motivo = "\n".join(texto)
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                             "permissionDecisionReason": motivo}}))
    sys.stderr.write(motivo + "\n")
    return 2


if __name__ == "__main__":
    sys.exit(main())
