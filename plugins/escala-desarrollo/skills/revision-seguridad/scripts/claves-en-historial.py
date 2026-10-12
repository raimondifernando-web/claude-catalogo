#!/usr/bin/env python3
"""Busca claves y contraseñas escritas alguna vez en el historial de git, SIN imprimir nunca el valor completo.

Solo lee (corre `git log -p` y `git grep`); no modifica el repo ni la carpeta. Cada hallazgo muestra commit, fecha,
archivo, línea, tipo, el valor enmascarado (4 primeros caracteres + largo) y si el valor sigue en el commit actual.

Uso:  python3 claves-en-historial.py [carpeta]   (por defecto la carpeta actual)
Salida: una línea por hallazgo + un resumen. Sale 0 siempre que pudo mirar; 2 si no es un repo de git.
"""
import hashlib
import os
import re
import subprocess
import sys

MAX_COMMITS = 2000      # tope para repos enormes; el resumen avisa si se alcanzó
MAX_HALLAZGOS = 60      # tope de líneas de salida

PATRONES = [
    ("clave-aws", re.compile(r"\b(AKIA[0-9A-Z]{16})\b")),
    ("clave-privada", re.compile(r"(-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY-----)")),
    ("token-github", re.compile(r"\b(gh[pousr]_[A-Za-z0-9]{30,})\b")),
    ("token-slack", re.compile(r"\b(xox[baprs]-[A-Za-z0-9-]{10,})\b")),
    ("clave-stripe-o-similar", re.compile(r"\b(sk_(?:live|test)_[A-Za-z0-9_]{10,}|sk-[A-Za-z0-9]{20,})\b")),
    ("clave-google", re.compile(r"\b(AIza[0-9A-Za-z_\-]{35})\b")),
    ("asignacion-secreta", re.compile(
        r"""(?i)\b[\w.-]*(?:api[_-]?key|secret|token|passw(?:or)?d|contrase\w+|clave)[\w.-]*\s*[:=]\s*['"]([^'"\s]{8,})['"]""")),
]


def enmascarar(valor):
    return f"{valor[:4]}… ({len(valor)} caracteres)"


def git(cwd, *args):
    return subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True)


def sigue_en_head(cwd, valor):
    r = subprocess.run(["git", "-C", cwd, "grep", "-q", "-F", "-e", valor, "HEAD"], capture_output=True)
    return r.returncode == 0


def main():
    carpeta = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".")
    if git(carpeta, "rev-parse", "--git-dir").returncode != 0:
        print("SIN-HISTORIAL: esta carpeta no es un repositorio de git; no hay historial que revisar.")
        return 2
    cmd = ["git", "-C", carpeta, "log", "--all", "--no-color", "-p", "-U0", "--reverse",
           f"--max-count={MAX_COMMITS}", "--format=@@C %h %ad", "--date=short"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, errors="replace")
    commit = fecha = archivo = None
    linea = 0
    vistos = {}          # (archivo, huella) -> índice en hallazgos
    hallazgos = []       # dicts
    commits = 0
    for crudo in proc.stdout:
        t = crudo.rstrip("\n")
        if t.startswith("@@C "):
            _, commit, fecha = t.split(" ", 2)
            commits += 1
            continue
        if t.startswith("+++ "):
            archivo = t[6:] if t.startswith("+++ b/") else None
            continue
        if t.startswith("@@ "):
            m = re.search(r"\+(\d+)", t)
            linea = int(m.group(1)) - 1 if m else 0
            continue
        if t.startswith("+") and not t.startswith("+++"):
            linea += 1
            if archivo is None:
                continue
            for tipo, rx in PATRONES:
                for m in rx.finditer(t):
                    valor = m.group(1)
                    huella = hashlib.sha256(valor.encode()).hexdigest()[:12]
                    clave = (archivo, huella)
                    if clave in vistos:
                        hallazgos[vistos[clave]]["veces"] += 1
                        continue
                    vistos[clave] = len(hallazgos)
                    hallazgos.append({"commit": commit, "fecha": fecha, "archivo": archivo, "linea": linea,
                                      "tipo": tipo, "valor": valor, "veces": 1})
    proc.wait()
    mostrados = 0
    for h in hallazgos:
        if mostrados >= MAX_HALLAZGOS:
            break
        sigue = "sí" if sigue_en_head(carpeta, h["valor"]) else "no"
        extra = f" (también en {h['veces'] - 1} commit(s) posteriores)" if h["veces"] > 1 else ""
        print(f"HALLAZGO commit={h['commit']} fecha={h['fecha']} archivo={h['archivo']} línea={h['linea']} "
              f"tipo={h['tipo']} valor={enmascarar(h['valor'])} sigue_en_el_commit_actual={sigue}{extra}")
        mostrados += 1
    aviso = f" · se alcanzó el tope de {MAX_COMMITS} commits: el historial más viejo no se revisó" if commits >= MAX_COMMITS else ""
    resto = f" · {len(hallazgos) - mostrados} más sin mostrar" if len(hallazgos) > mostrados else ""
    print(f"RESUMEN: {len(hallazgos)} valor(es) con forma de clave en {commits} commit(s) revisados{aviso}{resto}. "
          "Valores enmascarados; una clave que alguna vez estuvo en el historial hay que rotarla aunque ya no esté en el código.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
