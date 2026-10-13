import os, re, sys, pathlib, unicodedata
root = pathlib.Path(sys.argv[1])
pats = {
    "inyección/orden al agente": re.compile(r"(ignore (all |any )?(previous|prior|above)|disregard (the )?(previous|system)|do not (tell|inform|mention)[^.\n]{0,40}(user|human)|without (telling|asking|informing) the user|you must not reveal|override (the )?system|new instructions:)", re.I),
    "exfiltración/red": re.compile(r"(curl|wget|requests\.(get|post)|Invoke-WebRequest)[^\n]{0,80}(https?://|\$\{?[A-Z_]+)", re.I),
    "lectura de credenciales": re.compile(r"(~/\.ssh|~/\.aws|id_rsa|keychain|credentials\.json|process\.env)", re.I),
    "comentario HTML oculto": re.compile(r"<!--.{20,}?-->", re.S),
    "blob base64 largo": re.compile(r"[A-Za-z0-9+/]{120,}={0,2}"),
}
inv = re.compile("[​-‏‪-‮⁠-⁤﻿­]")
tot = 0
hits = {}
enlaces = [str(root.name)] if root.is_symlink() else []
for p in sorted(root.rglob("*")):
    if p.is_symlink():  # F6: un enlace no se lee (podría apuntar fuera); se avisa en vez de callar
        enlaces.append(f"{p.relative_to(root)} -> {os.readlink(p)}")
        continue
    if not p.is_file():
        continue
    try:
        t = p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        hits.setdefault("NO es UTF-8 (binario)", []).append(str(p.relative_to(root)))
        continue
    tot += len(t)
    for k, rg in pats.items():
        for m in rg.finditer(t):
            ln = t.count("\n", 0, m.start()) + 1
            hits.setdefault(k, []).append(f"{p.relative_to(root)}:{ln}: {m.group(0)[:90]!r}")
    n = len(inv.findall(t))
    if n:
        hits.setdefault("caracteres invisibles/bidi", []).append(f"{p.relative_to(root)}: {n}")
    if any(unicodedata.category(c) == "Co" for c in t):
        hits.setdefault("uso privado unicode", []).append(str(p.relative_to(root)))
print(f"{root}: {tot/1024:.0f} KB recorridos por el barrido")
for k, v in hits.items():
    print(f"  [{k}] {len(v)}")
    for x in v[:8]:
        print("     ", x)
if enlaces:
    print(f"  [ENLACES SIMBÓLICOS: no se leyeron, el barrido NO cubre lo que apuntan] {len(enlaces)}")
    for x in enlaces[:8]:
        print("     ", x)
if not hits and not enlaces:
    print("  sin hallazgos")
