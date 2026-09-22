#!/usr/bin/env python3
"""Verifica una copia/migración comparando TEXTO contra la fuente, no cantidades.

Por qué: una migración hecha por agentes puede devolver la misma cantidad de piezas
—y hasta la misma forma— con el contenido resumido o inventado. El conteo es justo
lo que no lo delata. Esto mide, por cada pieza del origen, qué proporción de sus
palabras aparece en el resultado, y aparte qué proporción de sus palabras PROPIAS
(las que no están en ninguna otra pieza): la cobertura de una pieza es la menor de las dos.

Uso:
    python3 verificar-copia.py <carpeta-origen> <carpeta-destino> [--umbral 85]

Salida: una línea por pieza que no pasa, y un resumen. Código 1 si algo falla.
No modifica nada: solo lee.

Límites (dichos, para que nadie los descubra tarde):
- Mide palabras, no orden: detecta resúmenes e invenciones, no un texto reordenado.
- Solo lee texto (.md, .txt, .csv, .json, .html…). Un PDF, Word o Excel del origen
  NO se puede medir: cuenta como «no medido» y el resultado es rojo. Pasalo antes a
  texto (skill markitdown del kit) y corré de nuevo sobre esa versión.
"""
import argparse, re, sys, unicodedata
from collections import Counter
from pathlib import Path

LEER = {".md", ".txt", ".csv", ".json", ".yaml", ".yml", ".html", ".xml", ".rst", ".org"}
TOPE = 50 * 1024 * 1024  # más grande que esto no se lee entero en memoria: cuenta como «no medido»


def normalizar(t):
    t = unicodedata.normalize("NFKD", t.lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return set(re.findall(r"\w{3,}", t))  # \w: también cirílico, griego, etc. — si no, contarían como vacíos


def leer(p):
    """None si no se pudo leer: un error NO puede pasar por archivo vacío (daría verde sin medir)."""
    try:
        return p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return None


def piezas(carpeta):
    """Devuelve (texto, no_medibles, ocultos). La clave es la ruta relativa SIN extensión:
    dos 'notas.md' en subcarpetas distintas son dos piezas, no una que pisa a la otra."""
    texto, no_medibles, ocultos = {}, [], 0
    raiz = Path(carpeta)
    for p in sorted(raiz.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(raiz)
        if any(parte.startswith(".") for parte in rel.parts):
            ocultos += 1; continue
        if p.suffix.lower() in LEER and p.stat().st_size <= TOPE:
            texto[str(rel.with_suffix("")).lower()] = p
        else:
            no_medibles.append(rel)
    return texto, no_medibles, ocultos


def buscar_par(clave, destino, por_nombre):
    """Mismo camino relativo → ese. Si no, mismo nombre de archivo y único → ese. Si no, ninguno."""
    if clave in destino:
        return destino[clave]
    candidatos = por_nombre.get(Path(clave).name, [])
    return candidatos[0] if len(candidatos) == 1 else None


def main():
    ap = argparse.ArgumentParser(description="Verifica una copia comparando texto contra la fuente.")
    ap.add_argument("origen")
    ap.add_argument("destino")
    ap.add_argument("--umbral", type=int, default=85, help="%% mínimo de palabras del original (1-100)")
    a = ap.parse_args()

    if not 1 <= a.umbral <= 100:
        print("✗ El umbral va de 1 a 100."); return 1
    o, d = Path(a.origen), Path(a.destino)
    if not o.is_dir():
        print(f"✗ No existe la carpeta de origen: {o}"); return 1
    if d.exists() and o.resolve() == d.resolve():
        print("✗ Origen y destino son la misma carpeta: así todo da 100% y no prueba nada."); return 1

    origen, no_medibles, ocultos = piezas(o)
    destino, _, _ = piezas(d) if d.is_dir() else ({}, [], 0)
    if not origen and not no_medibles:
        print(f"✗ No encontré archivos en {o}"); return 1

    por_nombre = {}
    for clave, p in destino.items():
        por_nombre.setdefault(Path(clave).name, []).append(p)
    # el destino puede tener todo junto en menos archivos: sin par, se compara contra TODO el destino
    texto_destino_total = normalizar(" ".join(leer(p) or "" for p in destino.values()))

    malas, vacias, ilegibles, ok = [], [], [], 0
    textos = {}
    for clave, p in origen.items():
        crudo = leer(p)
        if crudo is None:
            ilegibles.append(clave); continue
        palabras = normalizar(crudo)
        if not palabras:
            vacias.append(clave); continue
        textos[clave] = palabras
    # Palabras PROPIAS de cada pieza = las que no aparecen en ninguna otra del origen (teléfono, expediente,
    # montos). Si el destino juntó todo en un archivo, las palabras comunes de una pieza resumida aparecen en
    # las demás y la cobertura general da verde igual (probado: 30 fichas, 3 resumidas → «30 de 30»).
    # Las propias no: es lo primero que se pierde al resumir, y un reformateo legítimo no las toca.
    veces = Counter(w for s in textos.values() for w in s)
    for clave, palabras in textos.items():
        par = buscar_par(clave, destino, por_nombre)
        contra = normalizar(leer(par) or "") if par else texto_destino_total
        cobertura = 100.0 * len(palabras & contra) / len(palabras)
        propias = {w for w in palabras if veces[w] == 1}
        if propias:
            cobertura = min(cobertura, 100.0 * len(propias & contra) / len(propias))
        if cobertura < a.umbral:
            malas.append((clave, cobertura, "par encontrado" if par else "sin par en el destino"))
        else:
            ok += 1

    total = len(origen) + len(no_medibles)
    print(f"Piezas en el origen: {total}  ·  archivos de texto en el destino: {len(destino)}")
    if total == len(destino):
        print("⚠️  Las cantidades coinciden. Eso NO es garantía: mirá la cobertura de abajo.")
    print(f"Umbral de coincidencia de texto: {a.umbral}%\n")

    for clave, c, estado in sorted(malas, key=lambda x: x[1]):
        print(f"  ✗ {clave}: {c:.0f}% del texto original aparece en el resultado  ({estado})")
    for clave in ilegibles:
        print(f"  ? {clave}: no se pudo leer (permisos o archivo dañado), no se midió")
    for r in no_medibles:
        print(f"  ? {r}: no se pudo medir (no es texto, o pesa más de 50 MB): pasalo a texto con markitdown y corré de nuevo")
    for clave in vacias:
        print(f"  · {clave}: vacío en el origen, no hay texto que comparar")
    if ocultos:
        print(f"  · {ocultos} archivo(s) oculto(s) (nombre o carpeta que empieza con punto) no se miraron")

    print(f"\n{ok} de {total} piezas pasan el umbral.")
    no_medibles += ilegibles
    if ok == 0 and not malas and not no_medibles:
        print("⛔ No hubo ninguna pieza con texto para comparar: no se verificó nada."); return 1
    if malas or no_medibles:
        if malas:
            print(f"⛔ {len(malas)} por debajo: rehacelas copiando el texto, no resumiéndolo.")
        if no_medibles:
            print(f"⛔ {len(no_medibles)} sin medir: hasta que no se midan, la copia NO está verificada.")
        print("   NO borres ni archives el origen hasta que todas pasen.")
        return 1
    print("✓ Todas las piezas conservan el texto original. Recién ahora es seguro archivar el origen.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
