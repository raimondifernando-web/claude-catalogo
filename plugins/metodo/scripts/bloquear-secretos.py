#!/usr/bin/env python3
"""bloquear-secretos.py — freno PreToolUse de Bash: frena los comandos que MUESTRAN el valor de un secreto
(contraseña, llave, token) en pantalla, donde quedaría guardado en el historial de la sesión.

Contrato del hook: stdin = JSON {tool_name, tool_input:{command}}; exit 0 = deja pasar; exit 2 + stderr = frena.
Ante cualquier error NO frena (exit 0): nunca rompe Bash.

Cómo decide: parte el comando en comandos simples (respetando comillas, sin mirar comentarios ni cuerpos de
heredoc) y mira, para cada uno, el programa que corre y sus argumentos. Frena solo si un programa que IMPRIME
contenido (cat, sed, awk, jq, grep sin contar, python que abre el archivo…) recibe un archivo de secretos
(.env, llaves, .npmrc…), si se imprime una variable que parece secreta (SECRET, TOKEN, KEY…), o si se vuelca todo
el entorno. Mencionar ".env" o process.env.X en un texto o en un programa que no lo imprime NO frena.
"""
import json
import re
import sys

I = re.IGNORECASE
SECRETISH = (r"(?:SECRET|TOKEN|PASSWORD|PASSWD|API_?KEY|APIKEY|CREDENTIAL|PRIVATE_?KEY"
             r"|CLIENT_SECRET|ACCESS_KEY|AUTH_?TOKEN|BEARER)")
LECTORES = {"cat", "bat", "less", "more", "head", "tail", "nl", "tac", "xxd", "od", "strings", "view", "fold", "pr",
            "fmt", "awk", "gawk", "sed", "jq", "yq", "sort", "uniq", "cut", "paste", "column", "expand", "unexpand",
            "rev", "tr", "dd", "xargs", "base64", "hexdump"}
GREPS = {"grep", "egrep", "fgrep", "rg", "ag", "ack", "zgrep"}
INTERPRETES = {"python", "python2", "python3", "ruby", "perl", "node", "deno", "bun", "php"}
ECHOS = {"echo", "printf", "print"}
ENVOLTURAS = {"sudo", "command", "builtin", "time", "nohup", "nice", "exec", "stdbuf", "env"}
SUMIDEROS = {"wc", "sha1sum", "sha256sum", "sha512sum", "shasum", "md5", "md5sum", "cksum"}
SIN_VALOR = r"(?:example|sample|template|dist|defaults?|md)"
LOGIN_STDIN = ("--with-token", "--password-stdin")


def es_archivo_secreto(tok):
    """¿el argumento es (la ruta de) un archivo de secretos? Compara el nombre completo, no un pedazo de texto."""
    t = tok.strip("'\"<>")
    if not t or t.startswith("-"):
        return False
    base = t.rstrip("/").split("/")[-1]
    if re.fullmatch(r"\.env(?:\.[^/]*)?|.*\.env|\.env[*?\[].*", base, I):
        return not re.fullmatch(r"\.env\." + SIN_VALOR, base, I)
    if re.fullmatch(r"\.modal\.toml|.+\.(?:pem|key|p12|pfx)|id_rsa|id_ed25519|id_ecdsa|\.npmrc|\.netrc|"
                    r"credentials\.json|\.pgpass|\.htpasswd|secrets?\.(?:json|ya?ml|toml|env)", base, I):
        return True
    return bool(re.search(r"(?:^|/)gh(?:-claude)?/hosts\.yml$", t, I))


def sin_heredocs(cmd):
    """Saca los cuerpos de heredoc (<<EOF … EOF): es texto, no comandos."""
    out, lineas, i = [], cmd.split("\n"), 0
    while i < len(lineas):
        l = lineas[i]
        out.append(l)
        m = re.search(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1", l)
        i += 1
        if m:
            while i < len(lineas) and lineas[i].strip() != m.group(2):
                i += 1
            i += 1
    return "\n".join(out)


def partir(cmd):
    """→ lista de pipelines; cada pipeline = lista de etapas; cada etapa = lista de palabras.
    Respeta comillas y descarta comentarios (# al inicio de palabra, fuera de comillas)."""
    pipes, etapas, toks = [], [], []
    st = {"cur": "", "hay": False}

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
        elif ch == "&" and sig == "&":
            cerrar_pipe()
            i += 1
        elif ch == "&" and st["cur"][-1:] in (">", "<"):
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
    """→ (nombre, argumentos) saltando asignaciones VAR=x y envolturas (sudo, env…)."""
    j = 0
    while j < len(toks):
        t = toks[j]
        if re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", t) or t in ENVOLTURAS or (j > 0 and t.startswith("-") and toks[j - 1] in ENVOLTURAS):
            j += 1
        else:
            break
    if j >= len(toks):
        return "", []
    return toks[j].split("/")[-1], toks[j + 1:]


def stdout_a_archivo(args):
    return any(re.match(r"^(?:1?>>?|&>>?)(?!&)\S*$", a) for a in args)


def grep_solo_cuenta(args):
    for a in args:
        if a in ("--count", "--files-with-matches", "--files-without-match", "--quiet", "--silent"):
            return True
        if re.fullmatch(r"-[A-Za-z]+", a) and re.search(r"[clLq]", a):
            return True
    return False


def analizar_pipeline(etapas, razones, profundidad):
    progs = [programa(e) for e in etapas]
    for k, (nom, args) in enumerate(progs):
        if not nom:
            continue
        despues = progs[k + 1:]
        # lo que se imprime no llega a la pantalla si va a un archivo, a un contador/hash o a un inicio de sesión por stdin
        if stdout_a_archivo(args) or any(n in SUMIDEROS for n, _a in despues) \
                or any(n in ("gh", "docker") and any(x in a for x in LOGIN_STDIN) for n, a in despues):
            continue
        # bash -c "…" / eval "…": se mira el texto de adentro
        if nom in ("bash", "sh", "zsh", "dash") and "-c" in args:
            idx = args.index("-c")
            if idx + 1 < len(args) and profundidad < 3:
                razones.extend(analizar(args[idx + 1], profundidad + 1))
            continue
        if nom == "eval":
            if profundidad < 3:
                razones.extend(analizar(" ".join(args), profundidad + 1))
            continue
        archivos = [a for a in args if es_archivo_secreto(a)]
        archivos += [a.lstrip("<") for a in args if a.startswith("<") and not a.startswith("<<") and es_archivo_secreto(a)]
        if nom in LECTORES and archivos:
            razones.append(f"`{nom}` sobre «{archivos[0]}» muestra en pantalla el contenido de un archivo de secretos.")
        elif nom in GREPS and archivos and not grep_solo_cuenta(args):
            razones.append("buscar con grep dentro de un archivo de secretos muestra la línea con el valor. "
                           "Para saber si existe, usá `grep -c '^NOMBRE=' archivo` (cuenta, no muestra).")
        elif nom in INTERPRETES:
            texto = " ".join(args)
            abre = re.search(r"""['"][^'"\s]*(?:\.env(?:\.[A-Za-z]+)?|[\w.-]+\.(?:pem|key|p12|pfx)|id_rsa|id_ed25519|"""
                             r"""\.npmrc|\.netrc|credentials\.json|\.pgpass|\.htpasswd|secrets?\.(?:json|ya?ml|toml|env)|"""
                             r"""\.modal\.toml)['"]""", texto, I)
            if abre and re.search(r"open|read|File|IO\.|slurp|get_contents|load", texto, I) \
                    and re.search(r"print|puts|echo|console|log|write|dump|say|stdout", texto, I):
                razones.append("un programa de una línea (python, node…) que abre un archivo de secretos y lo imprime muestra su valor.")
            if re.search(r"(?:print|puts|echo|console\.\w+|printf|write|say)[^;\n]*"
                         r"(?:process\.env\.|os\.environ\W{0,3}|ENV\W{0,3}|getenv\W{0,3}|Deno\.env\.get\W{0,3})\w*" + SECRETISH,
                         texto, I):
                razones.append("ese programa imprime una variable de entorno que parece secreta (clave, token o contraseña).")
        elif nom in ECHOS:
            texto = " ".join(args)
            texto = re.sub(r"\$\{#[A-Za-z0-9_]+\}", "", texto)                                        # largo: seguro
            texto = re.sub(r"\$\{[A-Za-z0-9_]+:\s*-[1-4]\}|\$\{[A-Za-z0-9_]+:0:[1-4]\}", "", texto)  # 4 letras: seguro
            if re.search(r"\$\{?[A-Za-z0-9_]*" + SECRETISH, texto, I):
                razones.append(f"`{nom}` de una variable que parece secreta (clave, token o contraseña) la muestra en pantalla.")
        elif nom == "printenv":
            nombres = [a for a in args if not a.startswith("-")]
            if not nombres:
                razones.append("`printenv` sin nombre muestra TODO el entorno, con sus claves.")
            elif any(re.search(SECRETISH, a, I) for a in nombres):
                razones.append("`printenv` de una variable que parece secreta la muestra en pantalla.")
        elif nom == "export" and "-p" in args:
            razones.append("`export -p` lista todas las variables con su valor.")
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
    # `env` pelado (sin nada que lo siga) vuelca el entorno
    for e in etapas:
        if e and e[0] == "env" and len(e) == 1 and not (stdout_a_archivo(e) or any(n in SUMIDEROS for n, _a in progs)):
            razones.append("`env` sin argumentos muestra TODO el entorno, con sus claves.")


def analizar(cmd, profundidad=0):
    razones = []
    base = sin_heredocs(cmd)
    for pipeline in partir(base):
        analizar_pipeline(pipeline, razones, profundidad)
    if profundidad < 3:  # $( … ) y `…`: el comando de adentro también corre
        for m in re.finditer(r"\$\(([^()]*)\)|`([^`]*)`", base):
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
