"""estructura_molde — el motor del molde: mide un ÁRBOL de archivos (el de un commit, el de `origin/main` o el de una carpeta)
contra lo que toda caja tiene que tener. Es lo que usan `estructura.py exigir` (el freno de `unir-a-main` y `unir-pr`),
`estructura.py remoto` (el número «X de N cajas completas») y `cerrar-check`.

Disparador: encadenado — lo importa `estructura.py`; no se corre solo.

Tres niveles (ver docs/2026-10-18-molde-raiz.md):
  · duro        siempre frena: CLAUDE.md (R2), .gitignore (R5), ningún archivo personal versionado (R6, no exceptuable)
  · estructura  frena (con arrastre para lo que ya existía): los tres documentos (R12) y, si hay código, README, arquitectura,
                flujo de la app y claves de ejemplo (R23). Solo mira que EXISTAN: se arreglan en segundos con un comando.
  · contenido   nunca frena un merge; cuenta para «completa»: PRD y decisiones escritos (R16), cabecera del PRD (R27).
Solo biblioteca estándar. No ejecuta nada del árbol que mide: solo lee nombres y el texto de unos pocos archivos.
"""
import json
import re
from datetime import date

PERSONALES = (".env", ".claude/settings.local.json", "CLAUDE.local.md")
DOCUMENTOS_VIVOS = ("docs/PRD.md", "docs/decisiones.md")
PIEZAS_DE_CODIGO = ("README.md", "docs/arquitectura.md", "docs/flujo-de-la-app.md", ".env.example")
SENALES_CODIGO = ("package.json", "pyproject.toml", "requirements.txt", "Package.swift")
EXTENSIONES_CODIGO = (".py", ".js", ".ts", ".tsx", ".jsx", ".swift", ".go", ".rs", ".java", ".php", ".rb")
CARPETAS_QUE_NO_CUENTAN = ("node_modules", "venv", ".venv", "dist", "build", "__pycache__", "graphify-out", "scripts", "docs", "tests")
ARCHIVO_EXCEPCIONES = ".estructura-excepciones.json"
NO_EXCEPTUABLES = ("R6",)
COMANDO_ARREGLO = "estructura.py arreglar --si"


def hay_codigo_en_arbol(archivos) -> bool:
    """El mismo criterio que `hay_codigo_propio` de estructura.py, sobre nombres de archivo (sin tocar el disco): una señal en la
    raíz, código dentro de src/ o app/, o al menos 5 archivos de código a dos niveles sin contar scripts/, docs/ ni tests/."""
    archivos = set(archivos)
    if any(s in archivos for s in SENALES_CODIGO):
        return True
    cuenta = 0
    for a in archivos:
        partes = a.split("/")
        if not a.lower().endswith(EXTENSIONES_CODIGO):
            continue
        if partes[0] in ("src", "app"):
            return True
        if len(partes) <= 3 and not any(p in CARPETAS_QUE_NO_CUENTAN or p.startswith(".") for p in partes[:-1]):
            cuenta += 1
    return cuenta >= 5


def parsear_excepciones(texto: str, hoy: date = None):
    """(vigentes, avisos). vigentes = {regla: motivo} para la raíz del repositorio («ruta» «.»); una excepción necesita regla, motivo y
    fecha, y si trae `vence` (AAAA-MM-DD) deja de valer pasada esa fecha. R6 no se puede exceptuar."""
    hoy = hoy or date.today()
    vigentes, avisos = {}, []
    try:
        datos = json.loads(texto) if texto else []
    except ValueError:
        return {}, [f"{ARCHIVO_EXCEPCIONES} no es un JSON válido: se ignoran sus excepciones"]
    if not isinstance(datos, list):
        return {}, [f"{ARCHIVO_EXCEPCIONES} tiene que ser una lista: se ignoran sus excepciones"]
    for e in datos:
        if not isinstance(e, dict):
            continue
        regla = str(e.get("regla", "")).strip().upper()
        ruta = str(e.get("ruta", "")).strip().strip("/") or "."
        motivo, fecha, vence = str(e.get("motivo", "")).strip(), str(e.get("fecha", "")).strip(), str(e.get("vence", "")).strip()
        if ruta != "." or not re.fullmatch(r"R\d+", regla) or regla in NO_EXCEPTUABLES:
            continue
        if not motivo or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", fecha):
            continue
        if vence:
            try:
                if date.fromisoformat(vence) < hoy:
                    avisos.append(f"la excepción de {regla} venció el {vence}: ya no vale")
                    continue
            except ValueError:
                continue
        vigentes[regla] = motivo
    return vigentes, avisos


def _falta(regla, que, arreglo=COMANDO_ARREGLO):
    return {"regla": regla, "que": que, "arreglo": arreglo}


def medir(archivos, leer, hoy: date = None) -> dict:
    """Mide un árbol. `archivos`: conjunto de rutas (con «/»); `leer(ruta)` devuelve el texto o None.
    Devuelve {"duras": [...], "estructura": [...], "contenido": [...], "exceptuadas": [...], "avisos": [...], "codigo": bool}.
    Cada elemento: {"regla", "que", "arreglo"}. Lo exceptuado (con motivo, fecha y sin vencer) pasa a «exceptuadas»."""
    import estructura as E   # las plantillas y el criterio de «escrito» viven ahí (una sola fuente)
    hoy = hoy or date.today()
    archivos = set(archivos)
    vigentes, avisos = parsear_excepciones(leer(ARCHIVO_EXCEPCIONES) or "", hoy)
    codigo = hay_codigo_en_arbol(archivos)
    duras, estructura, contenido = [], [], []

    if "CLAUDE.md" not in archivos:
        duras.append(_falta("R2", "falta CLAUDE.md"))
    if ".gitignore" not in archivos:
        duras.append(_falta("R5", "falta .gitignore"))
    for p in PERSONALES:
        if p in archivos:
            duras.append(_falta("R6", f"{p} está versionado (es personal y puede llevar claves)", f"git rm --cached {p} (sin borrarlo); si tenía claves, cambiarlas"))

    for rel in DOCUMENTOS_VIVOS:
        if rel not in archivos:
            estructura.append(_falta("R12", f"falta {rel}"))
    if not any(a.startswith("docs/planes/") for a in archivos):
        estructura.append(_falta("R12", "falta docs/planes/ (con al menos un archivo)"))
    if codigo:
        for rel in PIEZAS_DE_CODIGO:
            if rel not in archivos:
                estructura.append(_falta("R23", f"la caja tiene código y falta {rel}"))

    for rel in DOCUMENTOS_VIVOS:
        if rel in archivos:
            texto = leer(rel) or ""
            if len(E._sin_instrucciones(texto)) < 40:
                contenido.append(_falta("R16", f"{rel} sigue siendo la plantilla (sin texto propio)", "escribirlo con lo que de verdad se sabe (el cierre lo hace); nunca se inventa"))
    if "docs/PRD.md" in archivos and not any(f["regla"] == "R16" and "PRD" in f["que"] for f in contenido):
        texto = leer("docs/PRD.md") or ""
        sin = [etq for etq in ("Dueño", "Estado", "Respaldo", "Última revisión") if not E._etiqueta_con_valor(texto, etq)]
        if sin:
            contenido.append(_falta("R27", "docs/PRD.md no dice: " + ", ".join(sin), "agregar esas líneas al PRD (el cierre las deja)"))

    exceptuadas = []
    def filtrar(lista):
        quedan = []
        for f in lista:
            if f["regla"] in vigentes:
                exceptuadas.append({**f, "motivo": vigentes[f["regla"]]})
            else:
                quedan.append(f)
        return quedan
    return {"duras": filtrar(duras), "estructura": filtrar(estructura), "contenido": filtrar(contenido),
            "exceptuadas": exceptuadas, "avisos": avisos, "codigo": codigo}


def esta_completa(m: dict) -> bool:
    """«Completa» = nada duro, nada de estructura y nada de contenido por resolver."""
    return not (m["duras"] or m["estructura"] or m["contenido"])
