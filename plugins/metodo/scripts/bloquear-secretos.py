#!/usr/bin/env python3
"""bloquear-secretos.py — freno PreToolUse de Bash, Read y Grep: frena lo que MUESTRA el valor de un secreto
(contraseña, llave, token) en pantalla, donde quedaría guardado en el historial de la sesión, y los comandos que
MANDAN un archivo de secretos a otra máquina (curl -d @.env).

Contrato del hook: stdin = JSON {tool_name, tool_input, cwd}; exit 0 = deja pasar; exit 2 + stderr = frena.
Ante cualquier error NO frena (exit 0): nunca rompe nada. Es un guardarraíl, no un muro: el muro son las reglas
`deny` de permisos y el sandbox (docs oficiales de permisos y sandbox; un paquete no puede traer reglas `deny`).

Read: frena si `file_path` (o el archivo al que apunta, si es un enlace) es un archivo de secretos. Grep: solo en
modo «content» (el único que muestra líneas) sobre un archivo o un glob de secretos; «files_with_matches» y «count»
pasan, igual que `grep -l` y `grep -c` en Bash.

Cómo decide: parte el comando en comandos simples (respetando comillas, sin mirar comentarios) y mira, para cada
uno, el programa que corre y sus argumentos. Frena solo si un programa que IMPRIME contenido (cat, sed, awk, jq,
grep sin contar, python que abre el archivo…) recibe un archivo de secretos (.env, llaves, .npmrc…), si se imprime
una variable que parece secreta (SECRET, TOKEN, KEY…), o si se vuelca todo el entorno. Mencionar ".env" o
process.env.X en un texto o en un programa que no lo imprime NO frena. El cuerpo de un heredoc se mira solo si lo
recibe una shell (bash <<X) o un intérprete (python - <<X); si lo recibe cat o un archivo, es texto.

Write / Edit / MultiEdit: NO bloquean. Si el archivo es de secretos (no una plantilla .example) y lo que se va a
escribir tiene forma de clave REAL (prefijos conocidos como ghp_, sk-, AKIA…, bloques de llave privada, o una variable
que parece secreta con un valor largo y variado), el freno PREGUNTA (permissionDecision «ask»): la persona decide en
el momento. Valores vacíos, de relleno (changeme, your_key, <token>, ${VAR}) o locales pasan. El valor nunca aparece
en el mensaje: solo el nombre de la variable y el número de línea.

Límites conocidos (no se cubren): escribir el archivo con redirecciones de Bash (echo X=… > archivo), buscar con grep -r o la herramienta Grep sobre una carpeta sin nombrar el archivo,
find -exec, ssh a otra máquina, una copia del archivo con otro nombre, y Windows: los comandos de PowerShell no
pasan por acá (el freno es solo para Mac y Linux).
"""
import json
import os
import re
import sys

# Windows: la consola usa cp1252 y los ✓/✗ y acentos hacían caer el script; se fuerza UTF-8 en entrada y salida.
for _flujo in (sys.stdin, sys.stdout, sys.stderr):
    try:
        _flujo.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

I = re.IGNORECASE
SECRETISH = (r"(?:SECRET|TOKEN|PASSWORD|PASSWD|API_?KEY|APIKEY|CREDENTIAL|PRIVATE_?KEY|CLIENT_SECRET|ACCESS_KEY"
             r"|AUTH_?TOKEN|BEARER|[A-Z0-9]_KEY\b|\bPASS\b|_PASS\b|_PWD\b)")
SUFIJO_NO_SECRETO = re.compile(r"_(?:FILE|PATH|DIR|NAME|URL|ID|LEN|COUNT)$", I)
LECTORES = {"cat", "bat", "less", "more", "head", "tail", "nl", "tac", "xxd", "od", "strings", "view", "fold", "pr",
            "fmt", "awk", "gawk", "sed", "jq", "yq", "sort", "uniq", "cut", "paste", "column", "expand", "unexpand",
            "rev", "tr", "dd", "xargs", "base64", "hexdump", "diff", "comm", "join", "tee"}
GREPS = {"grep", "egrep", "fgrep", "rg", "ag", "ack", "zgrep"}
INTERPRETES = {"python", "python2", "python3", "ruby", "perl", "node", "deno", "bun", "php"}
SHELLS = {"bash", "sh", "zsh", "dash"}
ECHOS = {"echo", "printf", "print"}
ENVOLTURAS = {"sudo", "command", "builtin", "time", "nohup", "nice", "exec", "stdbuf", "env", "timeout", "xcrun"}
PALABRAS = {"then", "do", "else", "elif", "if", "while", "until", "fi", "!", "{", "}", "case", "esac", "function"}
SUMIDEROS = {"wc", "sha1sum", "sha256sum", "sha512sum", "shasum", "md5", "md5sum", "cksum"}
SUBIDAS = {"curl", "wget", "http", "https", "xh"}  # programas que pueden mandar un archivo a otra máquina
# $( … ) cuya salida se guarda (VAR=$(…), export VAR=$(…)) o se carga (export $(…), eval "$(…)", source <(…)): no se muestra
SIN_SALIDA = re.compile(r"^\s*(?:(?:export|declare|local|readonly|typeset)\s+(?:-\w+\s+)*)?[A-Za-z_]\w*=[\"']?$"
                        r"|^\s*(?:export|eval|source|\.)\s+[\"']?<?$")
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
        # plantillas sin valores: .env.example, .env.local.example, sample.env, example.env
        return not (re.fullmatch(r"\.env\." + SIN_VALOR, base, I) or re.search(r"\." + SIN_VALOR + r"$", base, I)
                    or re.fullmatch(SIN_VALOR + r"\.env", base, I))
    if re.fullmatch(r"\.modal\.toml|.+\.(?:pem|key|p12|pfx)|id_rsa|id_ed25519|id_ecdsa|\.npmrc|\.netrc|\.pypirc|"
                    r"\.envrc|\.git-credentials|\.?credentials\.json|\.pgpass|\.htpasswd|secrets?\.(?:json|ya?ml|toml|env)",
                    base, I):
        return True
    # almacenes de credenciales conocidos (lista basada en el ejemplo oficial settings-hipaa.json de Anthropic)
    return bool(re.search(r"(?:^|/)gh(?:-claude)?/hosts\.yml$|(?:^|/)\.aws/credentials$|(?:^|/)\.docker/config\.json$"
                          r"|(?:^|/)\.config/git/credentials$|(?:^|/)\.notebooklm/.|(?:^|/)Library/Keychains/."
                          r"|(?:^|/)\.config/gcloud/(?:credentials\.db|access_tokens\.db|"
                          r"application_default_credentials\.json|legacy_credentials/)", t, I))


def es_ruta_secreta(ruta, cwd=""):
    """Read/Grep: ¿la ruta, o el archivo al que apunta si es un enlace, es un archivo de secretos?
    Acepta rutas relativas (se resuelven contra `cwd`) y separadores de Windows."""
    if not isinstance(ruta, str) or not ruta.strip():
        return False
    ruta = ruta.strip().replace("\\", "/")
    if es_archivo_secreto(ruta):
        return True
    try:
        completa = os.path.expanduser(ruta)
        if not os.path.isabs(completa):
            completa = os.path.join(cwd or os.getcwd(), completa)
        real = os.path.realpath(completa).replace("\\", "/")
    except (OSError, ValueError):
        return False
    return es_archivo_secreto(real)


def glob_secreto(patron):
    """Grep: ¿el glob apunta a archivos de secretos? (`.env*`, `**/.env`, `*.pem`, `{.env,.env.local}`…)"""
    if not isinstance(patron, str) or not patron.strip():
        return False
    return any(p and es_archivo_secreto(p) for p in re.split(r"[/{},]", patron.replace("\\", "/")))


def subida_secreta(args):
    """curl/wget/httpie: ¿manda el contenido de un archivo de secretos? (-d @.env, -F f=@.env, -T .env…)"""
    for k, a in enumerate(args):
        if "@" in a and es_archivo_secreto(a.split("@", 1)[1].split(";")[0]):
            return True
        if a in ("-T", "--upload-file", "--post-file", "--body-file") and k + 1 < len(args) \
                and es_archivo_secreto(args[k + 1]):
            return True
        m = re.match(r"^--(?:upload-file|post-file|body-file)=(.+)$", a)
        if m and es_archivo_secreto(m.group(1)):
            return True
    return False


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
            aritmetica = "((" in reciente and "))" not in reciente.split("((")[-1]
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
        elif ch in "<>" and st["sub"] == 0 and st["cur"] and not st["cur"].isdigit() and st["cur"][-1] not in "<>&" \
                and sig not in ("<", "(", "&"):
            cerrar_tok()   # `cat<.env` y `cat .env>/dev/stderr` (sin espacios) se leen como `cat < .env` y `cat .env > /dev/stderr`
            st["cur"] = ch
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
            j += 2 if previo in ("sudo", "env") and t in ("-u", "-g", "-h", "-p", "-C", "-D", "-R", "-T", "-S") else 1
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


VARIABLES_INOFENSIVAS = {"path", "home", "user", "logname", "shell", "lang", "language", "pwd", "oldpwd", "term", "editor", "visual",
                         "tmpdir", "hostname", "node_env", "shlvl", "display", "tz", "pythonpath", "node_path", "virtual_env",
                         "claude_config_dir", "claude_plugin_root", "claude_project_dir"}


def patron_inofensivo(p):
    """¿el patrón de un grep sobre el entorno solo puede traer variables que no son secretas? Solo vale (a) el nombre de una variable
    de la lista cerrada (PATH, HOME…), o (b) un nombre EXACTO anclado (`^NOMBRE=` / `NOMBRE=`) que no parezca secreto.
    Un pedazo suelto como `AWS` o `tok` también trae AWS_SECRET_ACCESS_KEY=… o GH_TOKEN=… (F5 del security check 0.35.0)."""
    t = (p or "").lstrip("^").rstrip("=")
    if t.lower() in VARIABLES_INOFENSIVAS:
        return True
    return bool(re.fullmatch(r"\^?[A-Za-z_][A-Za-z0-9_]{2,}=", p or "")) and not re.search(SECRETISH, t, I)


def solo_filtra(despues):
    """¿la salida pasa por un grep que solo cuenta o que busca una variable que no es secreta?"""
    for n, a in despues:
        if n in GREPS:
            p = patron_grep(a)
            invierte = any(re.fullmatch(r"-[A-Za-z]*v[A-Za-z]*|--invert-match", x) for x in a)
            if grep_solo_cuenta(a) or (patron_inofensivo(p) and not invierte):
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


def git_muestra_secreto(args):
    """git show / cat-file / diff / log -p / blame / grep / annotate sobre un archivo de secretos (`HEAD:.env`, `-- .env`, `.env`)."""
    sub = next((x for x in args if not x.startswith("-")), "")
    if sub not in ("show", "cat-file", "diff", "log", "blame", "annotate", "grep", "diff-tree", "whatchanged", "format-patch"):
        return False
    if any(re.fullmatch(r"--(?:stat|name-only|name-status|numstat|shortstat|summary|quiet|check|exit-code)|-q|-s", x) for x in args):
        return False
    if sub == "log" and not any(x in ("-p", "-u", "--patch", "--cc", "-c") or re.fullmatch(r"-[A-Za-z]*p[A-Za-z]*", x) for x in args):
        return False
    return any(es_archivo_secreto(x.split(":")[-1].lstrip("/")) or es_archivo_secreto(x) for x in args[1:] if not x.startswith("-"))


def todos_env(archivos):
    """Los nombres-de-variable (cut/awk) solo son seguros en archivos de variables: en una llave .pem las líneas no tienen «=» y se mostrarían enteras."""
    return all(re.fullmatch(r"\.env(?:\.[^/]*)?|.*\.env", a.strip("'\"").rstrip("/").split("/")[-1], I) for a in archivos)


def solo_nombres(nom, args):
    """cut/awk que muestran SOLO el nombre de cada variable: exigen el delimitador «=» (sin él, cut usa TAB y awk espacios, y la línea KEY=valor sale entera)."""
    if nom == "cut":
        delim = any(a in ("-d=", "--delimiter==") for a in args) or any(a == "-d" and args[k + 1:k + 2] == ["="] for k, a in enumerate(args))
        campo = any(a == "-f1" for a in args) or any(a == "-f" and args[k + 1:k + 2] == ["1"] for k, a in enumerate(args))
        return delim and campo
    delim = any(a == "-F=" for a in args) or any(a == "-F" and args[k + 1:k + 2] == ["="] for k, a in enumerate(args))
    return delim and any(re.fullmatch(r"\{\s*print\s+\$1\s*\}", a) for a in args)


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
        # mandar un archivo de secretos a otra máquina: se frena aunque la salida vaya a un archivo
        if nom in SUBIDAS and subida_secreta(args):
            razones.append(f"`{nom}` manda a otra máquina el contenido de un archivo de secretos.")
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
                texto_eval = " ".join(args)
                if not re.fullmatch(r"\s*(?:\$\([^()]*\)|`[^`]*`)\s*", texto_eval):  # eval "$(cmd)" solo carga lo que imprime cmd
                    razones.extend(analizar(texto_eval, profundidad + 1))
            continue
        archivos = [a for a in args if es_archivo_secreto(a)] + [f for f in stdin if es_archivo_secreto(f)]
        if nom in LECTORES and archivos:
            inofensivo = (nom == "sed" and any(re.fullmatch(r"-[A-Za-z]*i.*|--in-place.*", a) for a in args)) \
                or (nom in ("cut", "awk") and solo_nombres(nom, args) and todos_env(archivos))
            if not inofensivo:
                razones.append(f"`{nom}` sobre «{archivos[0]}» muestra en pantalla el contenido de un archivo de secretos.")
        elif nom in GREPS and archivos and not grep_solo_cuenta(args):
            razones.append("buscar con grep dentro de un archivo de secretos muestra la línea con el valor. "
                           "Para saber si existe, usá `grep -c '^NOMBRE=' archivo` (cuenta, no muestra).")
        elif nom == "git" and git_muestra_secreto(args):
            razones.append("este comando de git muestra el contenido de un archivo de secretos (show, cat-file, diff, log -p, blame…).")
        elif nom == "cp" and archivos and any(a in DESTINOS_PANTALLA for a in args):
            razones.append("`cp` de un archivo de secretos a la pantalla (/dev/stdout, /dev/stderr…) muestra su contenido.")
        elif nom in INTERPRETES:
            razones.extend(razones_interprete(" ".join(args) + "\n" + cuerpo, args))
        elif nom in ECHOS:
            texto = " ".join(args)
            texto = re.sub(r"\$\{#[A-Za-z0-9_]+\}", "", texto)                                        # largo: seguro
            texto = re.sub(r"\$\{[A-Za-z0-9_]+:\s*-[1-4]\}|\$\{[A-Za-z0-9_]+:0:[1-4]\}", "", texto)  # 4 letras: seguro
            va_a_otro_programa = any(n in ("pbcopy", "vercel", "wrangler") or (n == "gh" and "secret" in a) for n, a in despues)
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


def analizar_lectura(herramienta, ti, cwd):
    """Read y Grep: las herramientas de archivos de Claude, que el análisis de comandos de Bash no ve."""
    if herramienta == "Read":
        ruta = ti.get("file_path") or ""
        if es_ruta_secreta(ruta, cwd):
            nombre = str(ruta).replace("\\", "/").rstrip("/").split("/")[-1] or ruta
            return [f"leer «{nombre}» muestra el contenido de un archivo de secretos."]
        return []
    # Grep: solo «content» muestra líneas; «files_with_matches» (el de siempre) y «count» no muestran valores
    if (ti.get("output_mode") or "files_with_matches") != "content":
        return []
    if es_ruta_secreta(ti.get("path") or "", cwd) or glob_secreto(ti.get("glob") or ""):
        return ["buscar en modo «content» dentro de un archivo de secretos muestra la línea con el valor. "
                "Para saber si existe, buscá en modo «count» o «files_with_matches»."]
    return []


CLAVE_CONOCIDA = (
    (r"-----BEGIN (?:[A-Z]+ )*PRIVATE KEY-----", "un bloque de llave privada"),
    (r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,}|\bgithub_pat_[A-Za-z0-9_]{30,}", "una clave de GitHub"),
    (r"\bglpat-[A-Za-z0-9_-]{16,}", "una clave de GitLab"),
    (r"\bsk-ant-[A-Za-z0-9_-]{20,}|\bsk-(?:proj-|live-)?[A-Za-z0-9_-]{32,}", "una clave de API (sk-…)"),
    (r"\b(?:sk|rk|pk)_live_[A-Za-z0-9]{16,}", "una clave live de Stripe"),
    (r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b", "una clave de acceso de AWS"),
    (r"\bxox[abprs]-[A-Za-z0-9-]{10,}", "un token de Slack"),
    (r"\bAIza[0-9A-Za-z_-]{35}\b", "una clave de Google"),
    (r"\bshp(?:at|ca|pa|ss)_[A-Za-z0-9]{24,}", "un token de Shopify"),
    (r"\bEAA[A-Za-z0-9]{60,}", "un token de Meta"),
    (r"\beyJ[A-Za-z0-9_-]{8,}\.eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}", "un token JWT"),
)
ASIGNACION = re.compile(r"""^\s*(?:export\s+)?["']?([A-Za-z_][\w.-]*)["']?\s*[:=]\s*(.*?)\s*,?\s*$""")
RELLENO = re.compile(r"""^(?:|x+|\*+|\.+|-+|_+|0+|changeme|change[-_]?me|todo|tbd|null|none|nil|undefined|true|false
    |dummy|test|secret|password|pass|token|key|replace[-_ ]?me|<[^>]*>|\$\{?[^}]*\}?|\{\{.*\}\}|%[^%]*%)$""", I | re.X)
RELLENO_EN_MEDIO = re.compile(r"example|placeholder|change[-_]?me|your[-_ ]|my[-_ ]?(?:key|token|secret)|dummy|fake|sample"
                              r"|xxxx|\.\.\.|localhost|127\.0\.0\.1|insert|replace|ejemplo|reemplaz|pon[-_ ]?aca|tu[-_ ]?(?:clave|token)|complet", I)
URL_CON_CLAVE = re.compile(r"\b[a-z][a-z0-9+.-]*://([^:/@\s]+):([^@\s]+)@([^/\s:?#]+)", I)


def entropia(v):
    from math import log2
    return -sum(v.count(c) / len(v) * log2(v.count(c) / len(v)) for c in set(v)) if v else 0.0


def es_valor_real(valor):
    """¿el valor de una variable que parece secreta tiene pinta de ser real y no de relleno? (heurística)"""
    v = valor.strip().strip("'\"").strip()
    if not v or RELLENO.match(v) or RELLENO_EN_MEDIO.search(v) or re.search(r"\s", v):
        return False
    clases = sum(bool(re.search(r, v)) for r in (r"[a-z]", r"[A-Z]", r"\d", r"[^A-Za-z0-9]"))
    return (len(v) >= 16 and clases >= 2 and entropia(v) >= 3.0) or (len(v) >= 10 and clases >= 3 and entropia(v) >= 3.0)


def claves_reales(texto):
    """→ lista de (n.º de línea, descripción SIN el valor) de lo que parece una clave real dentro del texto."""
    hallazgos = []
    for n, linea in enumerate(str(texto).splitlines(), 1):
        motivo = ""
        for patron, nombre in CLAVE_CONOCIDA:
            m = re.search(patron, linea)
            if m and not RELLENO_EN_MEDIO.search(m.group(0)):
                motivo = f"algo con forma de {nombre}"
                break
        if not motivo:
            u = URL_CON_CLAVE.search(linea)
            if u and not re.search(r"localhost|127\.0\.0\.1|\[::1\]|\.local$|\.test$", u.group(3), I) \
                    and es_valor_real(u.group(2)) and not RELLENO_EN_MEDIO.search(u.group(0)):
                motivo = "una dirección con usuario y contraseña de un servidor que no es local"
        if not motivo:
            a = ASIGNACION.match(linea)
            if a and re.search(SECRETISH, a.group(1), I) and not SUFIJO_NO_SECRETO.search(a.group(1)):
                valor = a.group(2)
                if valor[:1] not in ("'", '"'):
                    valor = re.split(r"\s+#", valor)[0]
                if es_valor_real(valor):
                    motivo = f"un valor que parece real en la variable {a.group(1)}"
        if motivo:
            hallazgos.append((n, motivo))
    return hallazgos


def textos_escritos(herramienta, ti):
    """Lo que Write / Edit / MultiEdit van a dejar en el archivo (solo lo nuevo)."""
    if herramienta == "Write":
        return [ti.get("content")]
    if herramienta == "Edit":
        return [ti.get("new_string")]
    return [e.get("new_string") for e in (ti.get("edits") or []) if isinstance(e, dict)]


def analizar_escritura(herramienta, ti, cwd):
    """Write / Edit / MultiEdit sobre un archivo de secretos: solo si lo escrito parece una clave real. → motivos.
    Las plantillas (.example, .sample…) no son archivos de secretos para es_ruta_secreta: pasan sin mirar nada."""
    if not es_ruta_secreta(ti.get("file_path") or "", cwd):
        return []
    motivos = []
    for t in textos_escritos(herramienta, ti):
        if isinstance(t, str):
            motivos += [f"línea {n}: {m}" for n, m in claves_reales(t)]
    return motivos[:10]


def preguntar(ti, motivos):
    nombre = str(ti.get("file_path") or "").replace("\\", "/").rstrip("/").split("/")[-1]
    texto = [f"Estás por escribir en «{nombre}» (un archivo de secretos) algo que parece una clave real:"]
    texto += ["  · " + m for m in motivos]
    texto += ["", "Si es un valor de relleno, dejalo vacío o poné `changeme` / `<tu-clave>`. Si es una clave de verdad, "
              "la carga la persona dueña de la cuenta, directamente en el archivo: Claude no la escribe "
              "(el texto de esta acción queda guardado en el historial de la conversación). ¿Seguimos igual?"]
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "ask",
                                             "permissionDecisionReason": "\n".join(texto)}}))


def main():
    try:
        data = json.loads(sys.stdin.read())
        herramienta = data.get("tool_name")
        ti = data.get("tool_input") or {}
        if herramienta == "Bash":
            cmd = ti.get("command") or ""
            if not cmd.strip():
                return 0
            razones = analizar(cmd)
        elif herramienta in ("Read", "Grep"):
            razones = analizar_lectura(herramienta, ti, data.get("cwd") or "")
        elif herramienta in ("Write", "Edit", "MultiEdit"):
            motivos = analizar_escritura(herramienta, ti, data.get("cwd") or "")
            if motivos:
                preguntar(ti, motivos)
            return 0
        else:
            return 0
    except Exception:
        return 0
    if not razones:
        return 0
    texto = ["Frené esta acción porque puede mostrar una contraseña, una llave o un token en pantalla "
             "(y quedaría guardado en el historial de la conversación) o mandarlo a otra máquina:"]
    texto += ["  · " + r for r in razones]
    texto += ["",
              "Formas seguras:",
              "  · ¿existe la variable? → grep -c '^NOMBRE=' archivo   (cuenta, no muestra el valor)",
              "  · ¿qué variables tiene? → cut -d= -f1 archivo   (solo los nombres)",
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
