#!/usr/bin/env python3
"""Control de etiqueta de proyecto en agentes (Mand. III, C229, 2026-10-29).

Regla: un agente con datos, cuentas o sistemas de UNA empresa/proyecto lleva su tag al inicio de la description
(`[ACME] …`); un agente general no nombra a nadie. Falla (✗, salida 1) si:
  - un agente `pm-*` sin tag (un PM conoce UN proyecto), salvo los PM generales listados en el archivo de marcadores
    con `general: pm-xxx`;
  - un agente SIN tag nombra algún marcador de la lista (description, cuerpo o tools);
  - (modo --publico) un agente del catálogo público lleva tag de proyecto: ahí solo van agentes generales.
Disparador: automático — lo llama catalogo-check.sh en cada /cerrar (agentes de ~/.claude) y scripts/controles.sh del
catálogo en cada PR (modo --publico). Prueba de disparo: tests/test_agentes_etiqueta.py + correrlo a mano.

Uso: agentes-etiqueta.py [--agentes 'GLOB'] [--marcadores ARCHIVO] [--publico]
  El modo público toma además marcadores de la variable MARCADORES_PROYECTO (una expresión por línea; secreto, nunca
  se imprime el marcador, solo archivo y línea). Sin lista ni variable solo corre el control estructural.
"""
import argparse
import glob
import os
import re
import sys

TAG = re.compile(r"^\[[^\]\s][^\]]{0,30}\]\s*\S")
GENERICOS = [r"act_\d{6,}"]  # id de cuenta publicitaria: siempre es de alguien


def descripcion(texto):
    texto = texto.replace("\r\n", "\n")
    m = re.match(r"^---\n(.*?)\n---", texto, re.S)
    fm = m.group(1) if m else ""
    d = re.search(r'^description:[ \t]*(.*)$', fm, re.M)
    if not d:
        return ""
    v = d.group(1).strip()
    if v in ("", ">", "|", ">-", "|-", ">+", "|+"):  # bloque YAML: la descripción empieza en la línea de abajo
        resto = fm[d.end():].lstrip("\n").splitlines()
        v = next((l.strip() for l in resto if l.strip()), "") if resto and resto[0][:1] in " \t" else ""
    return v[1:].lstrip() if v[:1] in "\"'" else v


def cargar(lineas):
    pat, permitidos, generales = [], [], set()
    for l in lineas:
        l = l.strip()
        if not l or l.startswith("#"):
            continue
        if l.startswith("general:"):
            generales.add(l[8:].strip()); continue
        if l.startswith("!"):
            permitidos.append(re.compile(l[1:], re.I)); continue
        flags = 0 if l.startswith("cs:") else re.I
        l = l[3:] if l.startswith("cs:") else l
        pat.append(re.compile(r"(?<!\w)(?:" + l + r")(?!\w)", flags))
    return pat, permitidos, generales


def revisar(archivos, pat, permitidos, generales, publico, mostrar):
    fallas = []
    for f in sorted(archivos):
        n = os.path.basename(f)[:-3]
        texto = open(f, encoding="utf-8").read().replace("\r\n", "\n")
        con_tag = bool(TAG.match(descripcion(texto)))
        if publico and con_tag:
            fallas.append(f"{n}: agente con tag de proyecto en el catálogo público (solo van generales)")
            continue
        if con_tag:
            continue
        if n.startswith("pm-") and n not in generales and not publico:
            fallas.append(f"{n}: PM sin tag [PROYECTO] (un PM conoce UN proyecto; si es general, `general: {n}` en el archivo de marcadores)")
            continue
        for p in pat:  # el nombre del archivo también cuenta (un agente general no se llama como un proyecto)
            if p.search(n) and not n.startswith("pm-"):
                fallas.append(f"{n}: el nombre del agente es un marcador de proyecto y no lleva tag [PROYECTO]")
                break
        for i, l in enumerate(texto.splitlines(), 1):
            if l.startswith("name:"):
                continue
            for p in permitidos:
                l = p.sub("", l)
            for p in pat:
                m = p.search(l)
                if m:
                    cual = f" «{m.group(0)}»" if mostrar else ""
                    fallas.append(f"{n}:{i}: sin tag [PROYECTO] y nombra un marcador de proyecto/cliente{cual}")
                    break
            else:
                continue
            break
    return fallas


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--agentes", default=os.path.expanduser("~/.claude/agents/*.md"))
    ap.add_argument("--marcadores", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "marcadores-proyecto.txt"))
    ap.add_argument("--publico", action="store_true")
    a = ap.parse_args()
    lineas = []
    if os.path.isfile(a.marcadores):
        lineas += open(a.marcadores, encoding="utf-8").read().splitlines()
    lineas += os.environ.get("MARCADORES_PROYECTO", "").splitlines()
    lineas += [r"cs:" + g for g in GENERICOS]
    pat, permitidos, generales = cargar(lineas)
    sin_lista = len(pat) == len(GENERICOS)
    archivos = [f for f in glob.glob(a.agentes) if "/_" not in f]
    if not archivos:
        print("agentes-etiqueta: no hay agentes en", a.agentes); return 2
    fallas = revisar(archivos, pat, permitidos, generales, a.publico, mostrar=not a.publico)
    if a.publico and sin_lista:
        print("  (aviso) sin lista de marcadores (MARCADORES_PROYECTO): solo control estructural")
    for x in fallas:
        print("  ✗", x)
    print(f"== Etiqueta de proyecto en agentes: {'OK' if not fallas else str(len(fallas)) + ' falla(s)'} ({len(archivos)} revisados)")
    return 1 if fallas else 0


if __name__ == "__main__":
    sys.exit(main())
