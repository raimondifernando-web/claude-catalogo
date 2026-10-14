#!/usr/bin/env python3
"""estructura.py — dibujo, control y completar, generados desde ESTRUCTURA.md.

Fuente única de la verdad: ESTRUCTURA.md (plugins/metodo/estructura/ESTRUCTURA.md).
El molde, los niveles, las reglas y el ejemplo del dibujo se leen dinámicamente de ese archivo.

Detección automática de nivel:
1. Si se pasa el argumento `--nivel`, se utiliza ese nivel explícito ('empresa', 'area' o 'proyecto').
2. Si la carpeta se encuentra dentro de la raíz de proyectos (`--raiz` o `~/Proyectos`):
   - Si contiene subdirectorios que a su vez contienen cajas hijas adentro: se clasifica como 'empresa'.
   - Si contiene subdirectorios que son cajas hojas (sin cajas adentro): se clasifica como 'area'.
   - Si no contiene subdirectorios con cajas adentro (o es hoja): se clasifica como 'proyecto'
     (aplica tanto a proyectos dentro de un área como a repositorios personales en la raíz).
3. Si la carpeta se revisa de forma aislada y no se puede inferir su jerarquía: se asume 'proyecto'.

Disparador: automático (SessionStart del plugin metodo con --aviso; la primera sesión de cada semana recorre todas las carpetas) · encadenado (cerrar-check)

Subcomandos:
- dibujo [--salida RUTA] [--origen RUTA]
- revisar [CARPETA] [--todas] [--nivel empresa|area|proyecto] [--aviso] [--raiz RUTA] [--origen RUTA]
- completar CARPETA --nivel empresa|area|proyecto [--origen RUTA]
- arreglar [CARPETA] [--todas] [--raiz RUTA] [--origen RUTA] [--si]   (sin --si solo muestra el plan)
"""
import argparse
from datetime import date
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

# Windows: la consola usa cp1252 y los ✓/✗ y acentos hacían caer el script; se fuerza UTF-8 en entrada y salida.
for _flujo in (sys.stdin, sys.stdout, sys.stderr):
    try:
        _flujo.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


# ==============================================================================
# 1. PARSEO DE ESTRUCTURA.md
# ==============================================================================

def extraer_seccion(md_texto: str, titulo: str) -> str:
    """Extrae el contenido bajo '## <titulo>' hasta el próximo '## ' o fin de archivo."""
    patron = rf"^##\s+{re.escape(titulo)}\s*$"
    partes = re.split(patron, md_texto, flags=re.MULTILINE)
    if len(partes) < 2:
        return ""
    contenido = partes[1]
    siguiente = re.split(r"^##\s+", contenido, flags=re.MULTILINE)
    return siguiente[0].strip()


def parsear_tabla_md(texto: str):
    """Parsea una tabla en formato Markdown a una lista de diccionarios."""
    filas = [line.strip() for line in texto.splitlines() if line.strip().startswith("|")]
    if len(filas) < 3:
        return []
    encabezados = [c.strip().strip("`") for c in filas[0].split("|")[1:-1]]
    resultado = []
    for fila in filas[2:]:
        celdas = [c.strip() for c in fila.split("|")[1:-1]]
        if len(celdas) >= len(encabezados):
            resultado.append({encabezados[i]: celdas[i] for i in range(len(encabezados))})
    return resultado


def parsear_niveles(md_texto: str):
    """Devuelve dict con la definición de cada nivel."""
    sec = extraer_seccion(md_texto, "Niveles")
    filas = parsear_tabla_md(sec)
    res = {}
    for f in filas:
        nivel = f.get("Nivel", "").strip().lower()
        res[nivel] = {
            "que_es": f.get("Qué es", "").strip(),
            "tiene_cajas": "sí" in f.get("Tiene cajas adentro", "").lower(),
        }
    return res


def parsear_molde(md_texto: str):
    """Devuelve la lista de elementos del molde."""
    sec = extraer_seccion(md_texto, "El molde")
    filas = parsear_tabla_md(sec)
    molde = []
    for f in filas:
        archivo = f.get("Archivo", "").strip().strip("`")
        niveles_raw = f.get("Niveles", "").split()
        molde.append({
            "archivo": archivo,
            "que_es": f.get("Qué es", "").strip(),
            "niveles": niveles_raw,
            "comparte": f.get("Comparte", "").strip(),
            "obligatorio": f.get("Obligatorio", "").strip(),
            "baja": f.get("Baja", "").strip(),
            "fuente": f.get("Fuente", "").strip(),
        })
    return molde


def parsear_reglas(md_texto: str):
    """Devuelve las reglas de control R1-R12."""
    sec = extraer_seccion(md_texto, "Reglas que revisa el control")
    filas = parsear_tabla_md(sec)
    reglas = []
    for f in filas:
        reglas.append({
            "id": f.get("Id", "").strip(),
            "regla": f.get("Regla", "").strip(),
            "donde": f.get("Dónde", "").strip(),
            "si_falla": f.get("Si falla", "").strip(),
            "arreglo": f.get("Cómo se arregla", "").strip(),
        })
    return reglas


def cargar_arreglos(origen_arg=None) -> dict:
    """Mapa Id de regla -> «Cómo se arregla», leído de ESTRUCTURA.md (nunca escrito a mano acá)."""
    try:
        md = resolver_origen_md(origen_arg).read_text(encoding="utf-8", errors="replace")
    except (OSError, FileNotFoundError):
        return {}
    return {r["id"]: r["arreglo"] for r in parsear_reglas(md) if r["id"] and r["arreglo"]}


def parsear_personas(md_texto: str):
    """Devuelve la lista de personas para la tarjeta izquierda."""
    sec = extraer_seccion(md_texto, "Personas del ejemplo")
    filas = parsear_tabla_md(sec)
    if filas:
        return filas
    # Fallback si no está la tabla: personas estándar del texto
    return [
        {"Clave": "vos", "Nombre": "Vos", "Rol": "Dueño. Entra a todo."},
        {"Clave": "lu", "Nombre": "Lucía", "Rol": "Socia. Toda la Empresa A."},
        {"Clave": "be", "Nombre": "Beto", "Rol": "Solo el área Ventas."},
        {"Clave": "ca", "Nombre": "Caro", "Rol": "Solo el proyecto web."},
    ]


def parsear_contenido_claude(md_texto: str):
    """Devuelve los archivos que viven en ~/.claude/."""
    sec = extraer_seccion(md_texto, "Contenido de ~/.claude/")
    filas = parsear_tabla_md(sec)
    if filas:
        return [(f.get("Archivo", "").strip().strip("`"), f.get("Qué es", "").strip()) for f in filas]
    return [
        ("CLAUDE.md", "quién soy y cómo trabajo"),
        ("settings.json", "mis permisos y plugins"),
        ("skills/", "mis habilidades para cualquier proyecto"),
        ("agents/", "mis asistentes especializados"),
        ("projects/…/memory/", "lo que Claude aprende solo, uno por proyecto"),
        ("~/.claude.json", "mis conectores: correo, calendario, Drive"),
    ]


def parsear_textos_nivel(md_texto: str):
    """Devuelve diccionario {(archivo, nivel): (etiqueta, descripcion)}."""
    sec = extraer_seccion(md_texto, "Textos del dibujo por nivel")
    filas = parsear_tabla_md(sec)
    res = {}
    for f in filas:
        arch = f.get("Archivo", "").strip().strip("`")
        niv = f.get("Nivel", "").strip().lower()
        etiq = f.get("Etiqueta", "").strip().replace("`", "")
        desc = f.get("Descripción", "").strip().replace("`", "")
        res[(arch, niv)] = {"etiqueta": etiq, "descripcion": desc}
    return res


def parsear_pie(md_texto: str):
    """Devuelve los párrafos del pie del dibujo."""
    sec = extraer_seccion(md_texto, "Pie del dibujo")
    parrafos = [p.strip() for p in sec.split("\n\n") if p.strip()]
    return parrafos


def parsear_ejemplo(md_texto: str):
    """Parsea el bloque de código del ejemplo del dibujo en un árbol jerárquico."""
    sec = extraer_seccion(md_texto, "Ejemplo del dibujo")
    m = re.search(r"```(?:\w+)?\n(.*?)```", sec, re.DOTALL)
    if not m:
        return []
    bloque = m.group(1)
    lineas = bloque.splitlines()
    nodos = []
    stack = []

    for l in lineas:
        if not l.strip():
            continue
        indent = len(l) - len(l.lstrip())
        texto = l.strip()

        modo = "completa"
        m_marca = re.search(r"\[(.*?)\]\s*$", texto)
        if m_marca:
            modo = m_marca.group(1).strip()
            texto = texto[:m_marca.start()].strip()

        partes = texto.split()
        if len(partes) < 4:
            continue
        nombre = partes[0]
        nivel = partes[1].lower()
        repo = partes[2]
        accesos = partes[3:]

        nodo = {
            "nombre": nombre,
            "nivel": nivel,
            "repo": repo,
            "accesos": accesos,
            "modo": modo,
            "hijos": [],
        }

        while stack and stack[-1][0] >= indent:
            stack.pop()

        if stack:
            stack[-1][1]["hijos"].append(nodo)
        else:
            nodos.append(nodo)

        stack.append((indent, nodo))

    return nodos


def resolver_origen_md(ruta_origen=None) -> Path:
    """Encuentra la ruta a ESTRUCTURA.md."""
    if ruta_origen:
        p = Path(ruta_origen).resolve()
        if p.is_file():
            return p
    # Relativo a este script: ../estructura/ESTRUCTURA.md
    p_rel = Path(__file__).resolve().parent.parent / "estructura" / "ESTRUCTURA.md"
    if p_rel.is_file():
        return p_rel
    # Relativo a directorio actual
    p_cwd = Path.cwd() / "plugins" / "metodo" / "estructura" / "ESTRUCTURA.md"
    if p_cwd.is_file():
        return p_cwd
    raise FileNotFoundError("No se encontró ESTRUCTURA.md")


# ==============================================================================
# 2. GENERADOR DEL DIBUJO (HTML)
# ==============================================================================

CSS_PLANTILLA = """\
:root{color-scheme:light;--bg:#F4F3F0;--card:#FFFFFF;--line:#D6D3CC;--ink:#1D1C1A;--ink2:#5E5A53;
  --vos:#1F6FB2;--lu:#7A4BB0;--be:#C0731A;--ca:#2E8B57;--mac:#2E7D4F}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){color-scheme:dark;--bg:#121212;--card:#1C1C1B;--line:#3A3936;--ink:#ECE9E3;--ink2:#A8A39A;
  --vos:#6FAEE6;--lu:#B996E3;--be:#E9A55C;--ca:#6DCB97;--mac:#7FCB9C}}
:root[data-theme="dark"]{color-scheme:dark;--bg:#121212;--card:#1C1C1B;--line:#3A3936;--ink:#ECE9E3;--ink2:#A8A39A;
  --vos:#6FAEE6;--lu:#B996E3;--be:#E9A55C;--ca:#6DCB97;--mac:#7FCB9C}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.45 -apple-system,system-ui,sans-serif}
main{max-width:1100px;margin:0 auto;padding:24px 16px 40px}
h1{font-size:22px;margin:0 0 16px}
.f{font:600 13.5px/1.4 ui-monospace,'SF Mono',Menlo,monospace}
.q{color:var(--ink2);font-size:12.5px;font-weight:400}
.wrap{display:grid;grid-template-columns:260px 1fr;gap:16px;align-items:start}
.box{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px 12px}
.ttl{display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap}
.kids{display:grid;gap:10px;margin-top:10px;padding-left:14px;border-left:2px dashed var(--line)}
.row{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
.lvl1{border-width:2px}
.dots{display:flex;gap:4px}
.d{width:14px;height:14px;border-radius:50%;border:2px solid var(--c);background:var(--c)}
.d.r{background:transparent}
.vos{--c:var(--vos)}.lu{--c:var(--lu)}.be{--c:var(--be)}.ca{--c:var(--ca)}
.people .p{display:flex;gap:8px;align-items:flex-start;padding:7px 0;border-top:1px solid var(--line)}
.people .p:first-of-type{border-top:0}
.people .d{flex:none;margin-top:3px}
.people b{display:block;font-size:14px}
.key{display:flex;gap:14px;flex-wrap:wrap;margin-top:10px;padding-top:8px;border-top:1px solid var(--line);font-size:12.5px;color:var(--ink2)}
.key span{display:flex;gap:6px;align-items:center}
.key .d{--c:var(--ink2)}
.file{display:flex;justify-content:space-between;gap:8px;padding:3px 0;border-top:1px solid var(--line);font-size:12.5px}
.file .mono{font:12.5px ui-monospace,'SF Mono',Menlo,monospace}
.lock{color:var(--mac);font-weight:600}
.cfg{margin-top:12px}
.ghs{display:flex;flex-wrap:wrap;align-items:center;gap:6px 10px;margin:-10px -12px 8px;padding:6px 12px;border-radius:9px 9px 0 0;background:#24292F;color:#F6F8FA;font-size:12px}
.ghl{font-weight:700}
.ghr{font:12px ui-monospace,'SF Mono',Menlo,monospace}
.gha{margin-left:auto;display:flex;gap:6px;align-items:center}
.ghs .d{width:12px;height:12px}
.ghs .d.r{background:#24292F}
.ghkey b{display:inline;font-size:inherit}
.ghkey{padding:8px 0;border-top:1px solid var(--line);margin-top:4px}
.ghkey .mono{font:12px ui-monospace,'SF Mono',Menlo,monospace}
.addr{font:400 11.5px ui-monospace,'SF Mono',Menlo,monospace;color:var(--ink2);margin-left:6px}
.link{background:color-mix(in srgb,var(--ink2) 10%,transparent);border-radius:5px;padding:4px 6px;border-top:0}
.grp{margin:10px 0 2px;font-size:11.5px;font-weight:700;letter-spacing:.04em;text-transform:uppercase;color:var(--ink2)}
.cfg .file{flex-direction:column;gap:0}
.down{display:inline-block;margin-left:6px;font-size:11px;font-weight:700;color:var(--vos);white-space:nowrap}
.foot{margin:16px 0 0;font-size:14px}
.foot .mono{font:13px ui-monospace,'SF Mono',Menlo,monospace}
@media (max-width:820px){.wrap{grid-template-columns:minmax(0,1fr)}.row{grid-template-columns:minmax(0,1fr)}}\
"""


def _generar_dots(accesos):
    dots = []
    for a in accesos:
        if ":lee" in a:
            p = a.split(":")[0]
            dots.append(f'<span class="d r {p}"></span>')
        else:
            dots.append(f'<span class="d {a}"></span>')
    return f'<span class="dots">{"".join(dots)}</span>'


def _generar_ghs(repo, accesos):
    return (
        f'<div class="ghs"><span class="ghl">⇅ GitHub</span><span class="ghr">{repo}</span>'
        f'<span class="gha">acceso {_generar_dots(accesos)}</span></div>'
    )


def _generar_archivos_caja(nivel, molde, textos_nivel, tiene_hijos, indent_str="        "):
    nivel_letra = {"empresa": "E", "area": "A", "proyecto": "P"}.get(nivel, "P")
    lineas = []

    # 1. .git/ link especial si está en el molde
    git_row = next((r for r in molde if r["archivo"] == ".git/"), None)
    if git_row:
        custom_git = textos_nivel.get((".git/", nivel))
        if custom_git and custom_git.get("descripcion") and custom_git["descripcion"] != "—":
            desc = custom_git["descripcion"]
            etiqueta = custom_git["etiqueta"] if (custom_git.get("etiqueta") and custom_git["etiqueta"] != "—") else ".git/"
        else:
            desc = git_row["que_es"]
            etiqueta = ".git/"
        etiqueta = etiqueta.replace("`", "")
        desc = desc.replace("`", "")
        lineas.append(f'{indent_str}<div class="file link"><span class="mono">{etiqueta}</span><span class="q">{desc}</span></div>')

    # 2. Se comparte (va a GitHub)
    lineas.append(f'{indent_str}<div class="grp">Se comparte (va a GitHub)</div>')
    for r in molde:
        if r["archivo"] == ".git/":
            continue
        if r["comparte"] == "sí" and nivel_letra in r["niveles"]:
            custom = textos_nivel.get((r["archivo"], nivel))
            if custom:
                etiqueta = custom["etiqueta"]
                desc = custom["descripcion"]
                if etiqueta == "—":
                    continue
            else:
                etiqueta = r["archivo"]
                desc = r["que_es"]

            etiqueta = etiqueta.replace("`", "")
            desc = desc.replace("`", "")
            down_tag = ' <span class="down">↓ llega a lo de adentro</span>' if (r["baja"] == "sí" and tiene_hijos) else ''
            lineas.append(f'{indent_str}<div class="file"><span class="mono">{etiqueta}</span><span class="q">{desc}{down_tag}</span></div>')

    # 3. Solo en mi compu
    lineas.append(f'{indent_str}<div class="grp">Solo en mi compu</div>')
    for r in molde:
        if r["comparte"] == "no" and nivel_letra in r["niveles"]:
            custom = textos_nivel.get((r["archivo"], nivel))
            if custom and custom["etiqueta"] != "—":
                etiqueta = custom["etiqueta"]
                desc = custom["descripcion"]
            else:
                etiqueta = r["archivo"]
                desc = r["que_es"]
            etiqueta = etiqueta.replace("`", "")
            desc = desc.replace("`", "")
            lineas.append(f'{indent_str}<div class="file"><span class="mono">{etiqueta}</span><span class="lock">{desc}</span></div>')

    return "\n".join(lineas)


def _generar_nodo_html(nodo, molde, textos_nivel, es_lvl1=False, estilo_extra=None, indent="      "):
    lineas = []
    clases = "box lvl1" if es_lvl1 else "box"
    attr_style = f' style="{estilo_extra}"' if estilo_extra else ''
    lineas.append(f'{indent}<div class="{clases}"{attr_style}>')

    # Cabecera GitHub
    lineas.append(f'{indent}  {_generar_ghs(nodo["repo"], nodo["accesos"])}')

    # Título de la caja
    nombre = nodo["nombre"]
    nivel = nodo["nivel"]
    if nivel == "area":
        ttl_html = f'<span class="f">{nombre}/ <span class="q">área</span></span>'
    elif nivel == "proyecto" and nodo["modo"] == "completa":
        ttl_html = f'<span class="f">{nombre}/</span><span class="q">proyecto</span>'
    else:
        ttl_html = f'<span class="f">{nombre}/</span>'
    lineas.append(f'{indent}  <div class="ttl">{ttl_html}</div>')

    # Contenido según modo
    modo = nodo["modo"]
    if modo == "completa":
        tiene_hijos = bool(nodo["hijos"])
        archivos_html = _generar_archivos_caja(nivel, molde, textos_nivel, tiene_hijos, indent_str=indent + "  ")
        lineas.append(archivos_html)
        if tiene_hijos:
            # Si todos los hijos no tienen hijos propios (como crm y presupuestos en Ventas), contenedor kids row
            hijos_son_hojas = all(not h["hijos"] for h in nodo["hijos"])
            kids_class = "kids row" if hijos_son_hojas else "kids"
            lineas.append(f'{indent}  <div class="{kids_class}">')
            for h in nodo["hijos"]:
                if not hijos_son_hojas:
                    lineas.append("")
                estilo_h = "grid-column:1/-1" if (h["modo"] == "completa" and hijos_son_hojas) else None
                lineas.append(_generar_nodo_html(h, molde, textos_nivel, es_lvl1=False, estilo_extra=estilo_h, indent=indent + "    "))
            if not hijos_son_hojas:
                lineas.append("")
            lineas.append(f'{indent}  </div>')
    elif modo.startswith("nota:"):
        nota_texto = modo[5:].strip()
        lineas.append(f'{indent}  <div class="q">{nota_texto}</div>')
        if nodo["hijos"]:
            lineas.append(f'{indent}  <div class="kids row">')
            for h in nodo["hijos"]:
                lineas.append(_generar_nodo_html(h, molde, textos_nivel, es_lvl1=False, indent=indent + "    "))
            lineas.append(f'{indent}  </div>')
    elif modo == "resumen":
        pass

    lineas.append(f'{indent}</div>')
    return "\n".join(lineas)


def generar_dibujo_html(md_texto: str) -> str:
    """Genera el HTML completo a partir del contenido de ESTRUCTURA.md."""
    molde = parsear_molde(md_texto)
    personas = parsear_personas(md_texto)
    contenido_claude = parsear_contenido_claude(md_texto)
    textos_nivel = parsear_textos_nivel(md_texto)
    pie_parrafos = parsear_pie(md_texto)
    nodos = parsear_ejemplo(md_texto)

    # 1. Bloque personas
    lineas_personas = []
    for p in personas:
        clave = p.get("Clave", "").strip()
        nom = p.get("Nombre", "").strip()
        rol = p.get("Rol", "").strip()
        lineas_personas.append(f'      <div class="p"><span class="d {clave}"></span><div><b>{nom}</b><span class="q">{rol}</span></div></div>')
    html_personas = "\n".join(lineas_personas)

    # 2. Bloque ~/.claude/
    lineas_claude = []
    for arch, que_es in contenido_claude:
        lineas_claude.append(f'      <div class="file"><span class="mono">{arch}</span><span class="q">{que_es}</span></div>')
    html_claude = "\n".join(lineas_claude)

    # 3. Bloque cajas bajo ~/Proyectos/
    # El primer nodo (Empresa-A) va directo en kids; los siguientes raíz (Empresa-B, Personal) van en un row
    nodo_completo = nodos[0] if nodos else None
    resto_nodos = nodos[1:] if len(nodos) > 1 else []

    html_nodo_completo = _generar_nodo_html(nodo_completo, molde, textos_nivel, es_lvl1=True, indent="      ") if nodo_completo else ""

    lineas_resto = []
    if resto_nodos:
        lineas_resto.append('      <div class="row">')
        for rn in resto_nodos:
            lineas_resto.append(_generar_nodo_html(rn, molde, textos_nivel, es_lvl1=True, indent="        "))
        lineas_resto.append('      </div>')
    html_resto = "\n".join(lineas_resto)

    # 4. Pie de página
    if len(pie_parrafos) >= 2:
        p1 = pie_parrafos[0]
        p2 = pie_parrafos[1]
    else:
        p1 = (
            "Cada caja es un repositorio en GitHub, y el acceso se da en GitHub, repositorio por repositorio. "
            "En la computadora, cada carpeta es la copia de su repositorio y se conecta por su .git/. "
            "Cada persona descarga solo los repositorios donde está su punto: Beto nunca tiene Marketing ni Empresa-B, porque no las puede descargar.\n"
            "Los puntos huecos son para que Claude lea las reglas de la empresa o del área, aunque esa persona trabaje solo en un proyecto."
        )
        p2 = (
            "Todas las cajas tienen los mismos archivos (empresa, área y proyecto), porque en cualquiera se puede abrir "
            "Claude a trabajar. Lo que está en .claude/ rige solo cuando trabajás en esa caja. Lo marcado con "
            "↓ llega a lo de adentro es lo único que pasa a las cajas de adentro: las reglas "
            "(CLAUDE.md) y el paquete, que cada caja activa en su settings.json.\n"
            "Lo verde no se sube a GitHub."
        )

    # Formateo enriquecido del pie
    p1_fmt = (
        '<p class="foot"><b>Cada caja es un repositorio en GitHub, y el acceso se da en GitHub, repositorio por repositorio.</b> En la computadora, cada carpeta\n'
        'es la copia de su repositorio y se conecta por su <span class="mono">.git/</span>. Cada persona descarga solo los repositorios donde está su punto: Beto nunca tiene Marketing ni Empresa-B, porque no las puede descargar.\n'
        'Los puntos huecos son para que Claude lea las reglas de la empresa o del área, aunque esa persona trabaje solo en un proyecto.</p>'
    )
    p2_fmt = (
        '<p class="foot"><b>Todas las cajas tienen los mismos archivos</b> (empresa, área y proyecto), porque en cualquiera se puede abrir\n'
        'Claude a trabajar. Lo que está en <span class="mono">.claude/</span> rige solo cuando trabajás en esa caja. Lo marcado con\n'
        '<span class="down" style="margin:0">↓ llega a lo de adentro</span> es lo único que pasa a las cajas de adentro: las reglas\n'
        '(<span class="mono">CLAUDE.md</span>) y el paquete, que cada caja activa en su <span class="mono">settings.json</span>.\n'
        'Lo verde no se sube a GitHub.</p>'
    )

    doc = f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Estructura de referencia</title>
<style>
{CSS_PLANTILLA}
</style>
</head>
<body>
<main>
<h1>Cómo se ordena Claude con varias empresas, áreas y personas</h1>

<div class="wrap">

  <div>
    <div class="box people">
{html_personas}
      <div class="ghkey">
        <div class="ghs" style="margin:0 0 6px"><span class="ghl">⇅ GitHub</span><span class="ghr">empresa/carpeta</span></div>
        <div class="q">Arriba de cada caja: el repositorio en internet donde se guarda su copia. Los puntos son quién tiene acceso, y se dan ahí.</div>
        <div class="q" style="margin-top:6px"><b>Descargar:</b> la primera vez trae la caja a tu compu. <b>Subir:</b> manda tus cambios. <b>Actualizar:</b> trae los de los demás. Todo pasa por <span class="mono">.git/</span>.</div>
      </div>
      <div class="key">
        <span><span class="d"></span>trabaja</span>
        <span><span class="d r"></span>solo lee las reglas</span>
      </div>
    </div>

    <div class="box cfg">
      <div class="f">~/.claude/</div>
      <div class="q" style="margin-bottom:6px">De cada persona, en su computadora. Vale para todos sus proyectos. No va a GitHub de la empresa.</div>
{html_claude}
    </div>
  </div>

  <div class="box">
    <div class="ttl"><span class="f">~/Proyectos/</span><span class="q">la carpeta de todo, en la computadora de cada uno · no es un repositorio: no va a GitHub</span></div>
    <div class="kids">

{html_nodo_completo}

{html_resto}

    </div>
  </div>

</div>

{p1_fmt}
{p2_fmt}
</main>
</body>
</html>
"""
    return doc


def comando_dibujo(salida_ruta=None, origen_ruta=None):
    origen = resolver_origen_md(origen_ruta)
    salida = Path(salida_ruta).resolve() if salida_ruta else (origen.parent / "estructura.html")
    md_texto = origen.read_text(encoding="utf-8", errors="replace")
    html = generar_dibujo_html(md_texto)
    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_text(html, encoding="utf-8")
    print(f"Dibujo generado en: {salida}")
    return 0


# ==============================================================================
# 3. CONTROL Y REGLAS R1 - R12 (REVISAR)
# ==============================================================================

def ejecutar_git(*args, cwd=None):
    """Ejecuta comando git con subprocess, sin shell y con -c core.fsmonitor=."""
    if not shutil.which("git"):
        return None, "git no está disponible"
    cmd = ["git", "-c", "core.fsmonitor="]
    if cwd:
        cmd.extend(["-C", str(cwd)])
    cmd.extend(args)
    try:
        res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
        return res.returncode, res.stdout.strip()
    except Exception as e:
        return None, str(e)


# Qué cuenta como caja (decisión de diseño, revisión de Claude 2026-10-13):
# - en la raíz (~/Proyectos/) toda carpeta es una caja: ahí no va nada más;
# - más adentro, solo la carpeta que tiene .git o CLAUDE.md (src/, app/, datos/ no son cajas);
# - se saltean los enlaces (los dormidos de _latentes/ aparecerían dos veces) y lo que empieza con «.» o «_»;
# - dentro de un proyecto no se baja: un proyecto no tiene cajas adentro.
# El nivel sale de la posición y de si tiene cajas adentro: arriba de todo con cajas adentro = empresa;
# con cajas adentro dentro de otra caja = área; sin cajas adentro = proyecto.

def _es_carpeta_visible(p: Path) -> bool:
    return p.is_dir() and not p.is_symlink() and not p.name.startswith((".", "_"))


def es_caja(p: Path) -> bool:
    return _es_carpeta_visible(p) and ((p / ".git").exists() or (p / "CLAUDE.md").is_file())


def cajas_hijas(carpeta: Path) -> list:
    """Cajas que están directamente adentro de esta carpeta."""
    try:
        return sorted(h for h in carpeta.iterdir() if es_caja(h))
    except OSError:
        return []


def detectar_nivel_carpeta(carpeta: Path, raiz: Path = None, nivel_explicit=None, dentro_de_caja=None) -> str:
    """Decide el nivel de la caja según su posición y si tiene cajas adentro."""
    if nivel_explicit:
        return nivel_explicit
    if not cajas_hijas(carpeta):
        return "proyecto"
    if dentro_de_caja is None:
        dentro_de_caja = es_caja(carpeta.parent) and (raiz is None or carpeta.parent != raiz)
    return "area" if dentro_de_caja else "empresa"


SENALES_CODIGO_ARCHIVOS = ("package.json", "pyproject.toml", "requirements.txt", "Package.swift")
SENALES_CODIGO_CARPETAS = ("src", "app")
EXTENSIONES_CODIGO = {".py", ".js", ".ts", ".tsx", ".jsx", ".swift", ".go", ".rs", ".java", ".php", ".rb"}


def tiene_codigo(carpeta: Path) -> bool:
    """Señales baratas de que la caja es desarrollo (ver «Proyectos con desarrollo» en ESTRUCTURA.md)."""
    if any((carpeta / n).is_file() for n in SENALES_CODIGO_ARCHIVOS):
        return True
    for n in SENALES_CODIGO_CARPETAS:
        d = carpeta / n
        if d.is_dir() and not d.is_symlink():
            try:
                for raiz_d, _dirs, archivos in os.walk(d):
                    if any(Path(a).suffix.lower() in EXTENSIONES_CODIGO for a in archivos):
                        return True
            except OSError:
                pass
    return False


def revisar_caja(carpeta: Path, nivel: str, parent_caja: Path = None) -> list:
    """Aplica las reglas R1-R10 y R12 a una caja concreta. Retorna [(tipo, id, mensaje)]."""
    hallazgos = []
    nombre = carpeta.name

    # R1: Tiene .git/ con un remoto
    git_dir = carpeta / ".git"
    if not shutil.which("git"):
        hallazgos.append(("aviso", "R1", "no se pudo revisar (git no está disponible)"))
    elif not git_dir.exists():
        hallazgos.append(("error", "R1", "no tiene .git/ ni remoto en GitHub"))
    else:
        code, out = ejecutar_git("remote", cwd=carpeta)
        if code != 0 or not out:
            hallazgos.append(("error", "R1", "no tiene un remoto configurado en GitHub"))

    # R2: Tiene CLAUDE.md
    claude_md = carpeta / "CLAUDE.md"
    if not claude_md.is_file():
        hallazgos.append(("error", "R2", "falta CLAUDE.md"))

    # R3: CLAUDE.md con menos de 200 líneas (aviso)
    if claude_md.is_file():
        try:
            lineas = claude_md.read_text(encoding="utf-8", errors="replace").splitlines()
            if len(lineas) >= 200:
                hallazgos.append(("aviso", "R3", f"CLAUDE.md tiene 200 líneas o más ({len(lineas)} líneas)"))
        except Exception:
            pass

    # R4: Tiene .claude/settings.json y es un JSON válido
    settings_json = carpeta / ".claude" / "settings.json"
    if not settings_json.is_file():
        hallazgos.append(("error", "R4", "falta .claude/settings.json"))
    else:
        try:
            json.loads(settings_json.read_text(encoding="utf-8", errors="replace"))
        except Exception:
            hallazgos.append(("error", "R4", ".claude/settings.json tiene JSON inválido"))

    # R5: Tiene .gitignore
    gitignore = carpeta / ".gitignore"
    if not gitignore.is_file():
        hallazgos.append(("error", "R5", "falta .gitignore"))

    # R6: .env, .claude/settings.local.json y CLAUDE.local.md no están en GitHub
    if not shutil.which("git"):
        hallazgos.append(("aviso", "R6", "no se pudo revisar (git no está disponible)"))
    elif git_dir.exists():
        code, out = ejecutar_git("ls-files", "--", ".env", ".claude/settings.local.json", "CLAUDE.local.md", cwd=carpeta)
        if code == 0 and out:
            tracked = [l.strip() for l in out.splitlines() if l.strip()]
            for trk in tracked:
                hallazgos.append(("error", "R6", f"{trk} está versionado en el repositorio (no debe compartirse)"))

    # R7: Si hay .env, hay .env.example (aviso)
    env_file = carpeta / ".env"
    env_example = carpeta / ".env.example"
    if env_file.exists() and not env_example.is_file():
        hallazgos.append(("aviso", "R7", "hay .env pero falta .env.example"))

    # R8: El repositorio no guarda las cajas de adentro (empresa y área): cada caja de adentro tiene que estar
    # ignorada por el .gitignore y no tener nada versionado en este repositorio. Se pregunta a git (check-ignore,
    # ls-files) en vez de buscar un asterisco en el texto: «*.pyc» no ignora ninguna caja.
    if nivel in ("empresa", "area") and git_dir.exists() and shutil.which("git"):
        problemas = []
        for hija in cajas_hijas(carpeta):
            code_ls, out_ls = ejecutar_git("ls-files", "--", hija.name, cwd=carpeta)
            code_ci, _ = ejecutar_git("check-ignore", "-q", "--no-index", hija.name + "/", cwd=carpeta)
            if (code_ls == 0 and out_ls) or code_ci == 1:
                problemas.append(hija.name)
        if problemas:
            hallazgos.append(("error", "R8", "guarda en su repositorio las cajas de adentro ("
                              + ", ".join(problemas) + "): cada una va en su propio repositorio y el .gitignore las ignora"))

    # R9: Encabezado de skills y agentes con name y description
    skills_dir = carpeta / ".claude" / "skills"
    if skills_dir.is_dir():
        for sk_sub in skills_dir.iterdir():
            if sk_sub.is_dir():
                sk_md = sk_sub / "SKILL.md"
                if sk_md.is_file():
                    txt = sk_md.read_text(encoding="utf-8", errors="replace")
                    tiene_name = bool(re.search(r'(?m)^name\s*:\s*\S+', txt))
                    tiene_desc = bool(re.search(r'(?m)^description\s*:\s*\S+', txt))
                    if not (tiene_name and tiene_desc):
                        hallazgos.append(("error", "R9", f"skill '{sk_sub.name}' no tiene name o description en su encabezado"))

    agents_dir = carpeta / ".claude" / "agents"
    if agents_dir.is_dir():
        for ag_file in agents_dir.iterdir():
            if ag_file.is_file() and ag_file.name.endswith(".md"):
                txt = ag_file.read_text(encoding="utf-8", errors="replace")
                tiene_name = bool(re.search(r'(?m)^name\s*:\s*\S+', txt))
                tiene_desc = bool(re.search(r'(?m)^description\s*:\s*\S+', txt))
                if not (tiene_name and tiene_desc):
                    hallazgos.append(("error", "R9", f"agente '{ag_file.name}' no tiene name o description en su encabezado"))

    # R10: Si la empresa o área de arriba tiene paquete, settings.json lo activa (aviso)
    if parent_caja:
        parent_tiene_paquete = (parent_caja / "plugins").is_dir() or (parent_caja / ".claude-plugin" / "marketplace.json").is_file()
        if parent_tiene_paquete and settings_json.is_file():
            try:
                st = json.loads(settings_json.read_text(encoding="utf-8", errors="replace"))
                activa = any(k in st for k in ("enabledPlugins", "plugins", "extraPlugins"))
                if not activa:
                    hallazgos.append(("aviso", "R10", "la caja superior tiene paquete pero .claude/settings.json no lo activa"))
            except Exception:
                pass

    # R12: si la caja (proyecto) tiene código, tiene docs/PRD.md (aviso)
    if nivel == "proyecto" and tiene_codigo(carpeta) and not (carpeta / "docs" / "PRD.md").is_file():
        hallazgos.append(("aviso", "R12", "tiene código pero falta docs/PRD.md"))

    return hallazgos


def revisar_raiz(raiz: Path) -> list:
    """Aplica la regla R11 a la raíz de proyectos."""
    hallazgos = []
    if (raiz / ".git").exists():
        hallazgos.append(("error", "R11", "~/Proyectos/ no debe ser un repositorio git"))
    return hallazgos


def descubrir_cajas(raiz: Path):
    """Cajas debajo de la raíz: [(carpeta, nivel, caja de arriba o None)]. Ver «Qué cuenta como caja»."""
    cajas = []
    # Varias copias de trabajo (git worktree) del mismo repositorio tienen lo mismo adentro: el repositorio se revisa
    # una sola vez (en la copia principal, la que tiene la carpeta .git de verdad), para no repetir cada aviso por copia.
    repos_vistos = set()

    def repo_comun(carpeta: Path):
        if not (carpeta / ".git").exists():
            return None
        code, out = ejecutar_git("rev-parse", "--path-format=absolute", "--git-common-dir", cwd=carpeta)
        return out if code == 0 and out else None

    def recorrer(carpeta: Path, parent, profundidad: int):
        comun = repo_comun(carpeta)
        if comun is not None:
            if comun in repos_vistos:
                return
            repos_vistos.add(comun)
        nivel = detectar_nivel_carpeta(carpeta, raiz, dentro_de_caja=parent is not None)
        cajas.append((carpeta, nivel, parent))
        if nivel != "proyecto" and profundidad < 3:
            for hija in sorted(cajas_hijas(carpeta), key=lambda h: (not (h / ".git").is_dir(), h.name)):
                recorrer(hija, carpeta, profundidad + 1)

    try:
        primeras = sorted((d for d in raiz.iterdir() if _es_carpeta_visible(d)),
                          key=lambda d: (not (d / ".git").is_dir(), d.name))
    except OSError:
        primeras = []
    for d in primeras:
        recorrer(d, None, 1)
    return cajas


MAX_LINEAS_AVISO = 10


def comando_revisar(carpeta_arg=None, todas=False, nivel_arg=None, aviso=False, raiz_arg=None, origen_arg=None) -> int:
    """Implementa el subcomando revisar."""
    raiz = Path(raiz_arg).resolve() if raiz_arg else (Path.home() / "Proyectos")

    # Manejo de modo aviso con semana ISO
    if aviso:
        plugin_data = os.environ.get("CLAUDE_PLUGIN_DATA")
        estado_dir = Path(plugin_data) if plugin_data else (Path.home() / ".claude" / "metodo-estado")
        estado_file = estado_dir / "semana-revisar.txt"
        iso_year, iso_week, _ = date.today().isocalendar()
        semana_actual = f"{iso_year}-W{iso_week:02d}"

        primera_vez_semana = False
        try:
            if estado_file.is_file():
                if estado_file.read_text(encoding="utf-8").strip() != semana_actual:
                    primera_vez_semana = True
            else:
                primera_vez_semana = True

            if primera_vez_semana:
                todas = True  # la marca se guarda al terminar la pasada: si el aviso se corta por tiempo, se repite
        except Exception:
            pass

    arreglos = cargar_arreglos(origen_arg)

    def con_arreglo(r_id, linea):
        return f"{linea} → {arreglos[r_id]}" if arreglos.get(r_id) else linea

    lineas_salida = []
    total_errores = 0

    if todas:
        # Revisar R11 en la raíz
        for tipo, r_id, msg in revisar_raiz(raiz):
            total_errores += 1
            lineas_salida.append(con_arreglo(r_id, f"✗ {r_id} {raiz.name}: {msg}"))

        # Recorrer cajas
        cajas = descubrir_cajas(raiz)
        for c_path, c_nivel, parent in cajas:
            rel_display = str(c_path.relative_to(raiz))
            hallazgos = revisar_caja(c_path, c_nivel, parent_caja=parent)
            for tipo, r_id, msg in hallazgos:
                if tipo == "error":
                    total_errores += 1
                    lineas_salida.append(con_arreglo(r_id, f"✗ {r_id} {rel_display}: {msg}"))
                else:
                    lineas_salida.append(con_arreglo(r_id, f"• {r_id} {rel_display}: {msg}"))
    else:
        objetivo = Path(carpeta_arg).resolve() if carpeta_arg else Path.cwd()
        # Si se apunta a la raíz directamente
        if objetivo == raiz or (raiz_arg and objetivo == Path(raiz_arg).resolve()):
            for tipo, r_id, msg in revisar_raiz(objetivo):
                total_errores += 1
                lineas_salida.append(con_arreglo(r_id, f"✗ {r_id} {objetivo.name}: {msg}"))
        else:
            nivel = detectar_nivel_carpeta(objetivo, raiz, nivel_explicit=nivel_arg)
            parent = objetivo.parent if objetivo.parent != raiz and es_caja(objetivo.parent) else None
            hallazgos = revisar_caja(objetivo, nivel, parent_caja=parent)
            display_name = objetivo.name
            for tipo, r_id, msg in hallazgos:
                if tipo == "error":
                    total_errores += 1
                    lineas_salida.append(con_arreglo(r_id, f"✗ {r_id} {display_name}: {msg}"))
                else:
                    lineas_salida.append(con_arreglo(r_id, f"• {r_id} {display_name}: {msg}"))

    # En modo aviso: si todo está bien, no imprime nada y sale 0. Si hay fallas, imprime y sale 0.
    if aviso:
        if primera_vez_semana:
            try:
                estado_dir.mkdir(parents=True, exist_ok=True)
                estado_file.write_text(semana_actual, encoding="utf-8")
            except OSError:
                pass
        if lineas_salida:
            # primero los ✗ (sort estable), como mucho 10 líneas
            ordenadas = sorted(lineas_salida, key=lambda l: not l.startswith("✗"))
            for l in ordenadas[:MAX_LINEAS_AVISO]:
                print(l)
            if len(ordenadas) > MAX_LINEAS_AVISO:
                print(f"… y {len(ordenadas) - MAX_LINEAS_AVISO} más (estructura.py revisar --todas)")
            palabra = "cosa" if total_errores == 1 else "cosas"
            print(f"Falta: {total_errores} {palabra} ✗")
            print("Claude: ofrecé arreglarlo con `estructura.py arreglar` (primero el plan; pedí OK antes de `--si`).")
        return 0

    # Modo normal
    for l in lineas_salida:
        print(l)

    if total_errores == 0:
        print("Estructura al día ✓")
        return 0
    else:
        palabra = "cosa" if total_errores == 1 else "cosas"
        print(f"Falta: {total_errores} {palabra} ✗")
        return 1


# ==============================================================================
# 4. COMPLETAR (CREAR LO OBLIGATORIO)
# ==============================================================================

def nombres_de_env(env_file: Path) -> list:
    """Solo los NOMBRES de las variables de un archivo de entorno (lo que está antes del «=»); nunca un valor."""
    nombres = []
    try:
        texto = env_file.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return nombres
    # Un valor entre comillas puede seguir en varias líneas (por ejemplo una clave privada). Esas líneas se saltean:
    # si no, un pedazo de la clave que termina en «=» parecería un nombre y llegaría al .env.example, que va a GitHub.
    comilla_abierta = None
    for linea in texto.splitlines():
        linea = linea.strip()
        if comilla_abierta:
            if comilla_abierta in linea:
                comilla_abierta = None
            continue
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        nombre, valor = (x.strip() for x in linea.split("=", 1))
        if valor[:1] in ("'", '"') and valor.count(valor[0]) == 1:
            comilla_abierta = valor[0]
        if nombre.startswith("export "):
            nombre = nombre[len("export "):].strip()
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.-]*", nombre) and nombre not in nombres:
            nombres.append(nombre)
    return nombres


PLANTILLA_PRD = """# {nombre} — PRD

> Documento vivo. Lo completa el PM del proyecto con Claude a partir del código; no se inventa nada.

## Qué se construye y para quién

## Cuándo está terminado

## Qué NO se hace

## Sección técnica (TRD)
Cómo está armado: piezas, dependencias, dónde corre. El esquema de datos se genera desde el código, no se escribe a mano.

## Flujo de la app
Diagrama de cómo se mueve la persona por la app. Las pantallas van como mockups (Figma o HTML), no como texto.
"""


def plan_seguro(carpeta: Path, nivel: str) -> list:
    """Lo seguro y reversible que falta: [(ruta relativa, contenido, regla)]. Nunca incluye lo que ya existe."""
    plan = []
    if not (carpeta / "CLAUDE.md").exists():
        plan.append(("CLAUDE.md", f"# {carpeta.name}\n\nReglas de trabajo.\n", "R2"))
    if not (carpeta / ".claude" / "settings.json").exists():
        plan.append((".claude/settings.json", "{}\n", "R4"))
    if not (carpeta / ".gitignore").exists():
        lineas_gi = [".env", ".claude/settings.local.json", "CLAUDE.local.md"]
        if nivel in ("empresa", "area"):
            lineas_gi.extend(["", "# Cajas de adentro: cada una tiene su propio repositorio",
                              "/*/", "!/.claude/", "!/plugins/", "!/docs/"])
        plan.append((".gitignore", "\n".join(lineas_gi) + "\n", "R5"))
    if (carpeta / ".env").exists() and not (carpeta / ".env.example").exists():
        cuerpo = "# Claves y variables de entorno requeridas (sin valores)\n"
        cuerpo += "".join(f"{n}=\n" for n in nombres_de_env(carpeta / ".env"))
        plan.append((".env.example", cuerpo, "R7"))
    if nivel == "proyecto" and tiene_codigo(carpeta) and not (carpeta / "docs" / "PRD.md").exists():
        plan.append(("docs/PRD.md", PLANTILLA_PRD.format(nombre=carpeta.name), "R12"))
    return plan


def comando_completar(carpeta_arg: str, nivel: str, origen_arg=None) -> int:
    """Crea los archivos obligatorios según el molde sin pisar nada existente."""
    carpeta = Path(carpeta_arg).resolve()
    carpeta.mkdir(parents=True, exist_ok=True)

    plan = {rel: cont for rel, cont, _ in plan_seguro(carpeta, nivel)}
    for rel in ("CLAUDE.md", ".claude/settings.json", ".gitignore"):
        if rel in plan:
            destino = carpeta / rel
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_text(plan[rel], encoding="utf-8")
            print(f"+ Creado: {rel}")
        else:
            print(f"= Ya existe: {rel}")

    if (carpeta / ".env").exists():
        if ".env.example" in plan:
            (carpeta / ".env.example").write_text(plan[".env.example"], encoding="utf-8")
            print("+ Creado: .env.example")
        else:
            print("= Ya existe: .env.example")

    # Git y remoto (informa como pendiente)
    git_dir = carpeta / ".git"
    if not git_dir.exists():
        print("! Pendiente: inicializar git y configurar remoto (git init / git remote add)")
    else:
        code, out = ejecutar_git("remote", cwd=carpeta)
        if code != 0 or not out:
            print("! Pendiente: configurar remoto en GitHub (git remote add origin ...)")
        else:
            print("✓ Git y remoto configurados")

    return 0


# ==============================================================================
# 4b. ARREGLAR (PLAN Y, CON --si, LO SEGURO)
# ==============================================================================

def comando_arreglar(carpeta_arg=None, todas=False, raiz_arg=None, origen_arg=None, aplicar=False) -> int:
    """Sin aplicar: muestra el plan. Con aplicar: crea solo lo seguro; el resto queda para hacer con Claude."""
    raiz = Path(raiz_arg).resolve() if raiz_arg else (Path.home() / "Proyectos")
    arreglos = cargar_arreglos(origen_arg)

    if todas:
        objetivos = descubrir_cajas(raiz)
        pendientes_raiz = revisar_raiz(raiz)
    else:
        objetivo = Path(carpeta_arg).resolve() if carpeta_arg else Path.cwd()
        if objetivo == raiz:
            objetivos, pendientes_raiz = [], revisar_raiz(raiz)
        else:
            parent = objetivo.parent if objetivo.parent != raiz and es_caja(objetivo.parent) else None
            objetivos = [(objetivo, detectar_nivel_carpeta(objetivo, raiz), parent)]
            pendientes_raiz = []

    creados = 0
    pendientes = 0

    def mostrar_pendiente(r_id, msg):
        extra = f" → {arreglos[r_id]}" if arreglos.get(r_id) else ""
        print(f"  ! para hacer con Claude (pide tu OK): {r_id} {msg}{extra}")

    for _tipo, r_id, msg in pendientes_raiz:
        pendientes += 1
        print(f"== {raiz.name} ==")
        mostrar_pendiente(r_id, msg)

    for c_path, c_nivel, parent in objetivos:
        try:
            rel = str(c_path.relative_to(raiz))
        except ValueError:
            rel = c_path.name
        plan = plan_seguro(c_path, c_nivel)
        cubiertas = {r for _, _, r in plan}
        # lo que queda se mide ANTES de aplicar y sin lo que el plan va a resolver
        resto = [h for h in revisar_caja(c_path, c_nivel, parent_caja=parent) if h[1] not in cubiertas]
        if not plan and not resto:
            continue
        print(f"== {rel} ==")
        for ruta, contenido, _r in plan:
            if aplicar:
                destino = c_path / ruta
                destino.parent.mkdir(parents=True, exist_ok=True)
                with open(destino, "x", encoding="utf-8") as fh:  # "x": jamás pisa un archivo existente
                    fh.write(contenido)
                print(f"  + creado: {ruta}")
            else:
                print(f"  + crearía: {ruta}")
            creados += 1
        for _tipo, r_id, msg in resto:
            pendientes += 1
            mostrar_pendiente(r_id, msg)

    if aplicar:
        print(f"Arreglado ✓ ({creados} archivos creados) · quedan {pendientes} para hacer con Claude")
    else:
        print(f"Plan: {creados} archivos para crear · {pendientes} para hacer con Claude — corré con --si para aplicarlo")
    return 0


# ==============================================================================
# 5. PUNTO DE ENTRADA CLI
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(description="Estructura Claude: dibujo, control y completar desde ESTRUCTURA.md")
    subparsers = parser.add_subparsers(dest="comando", required=True)

    # Subcomando dibujo
    p_dibujo = subparsers.add_parser("dibujo", help="Genera el dibujo HTML a partir de ESTRUCTURA.md")
    p_dibujo.add_argument("--salida", default=None, help="Ruta de salida del archivo HTML")
    p_dibujo.add_argument("--origen", default=None, help="Ruta de ESTRUCTURA.md")

    # Subcomando revisar
    p_revisar = subparsers.add_parser("revisar", help="Revisa el cumplimiento de las reglas R1-R12")
    p_revisar.add_argument("carpeta", nargs="?", default=None, help="Carpeta a revisar (por defecto la actual)")
    p_revisar.add_argument("--todas", action="store_true", help="Revisa todas las cajas bajo ~/Proyectos/ o --raiz")
    p_revisar.add_argument("--nivel", choices=["empresa", "area", "proyecto"], help="Nivel forzado para la caja")
    p_revisar.add_argument("--aviso", action="store_true", help="Modo silencioso para hook de arranque")
    p_revisar.add_argument("--raiz", default=None, help="Raíz de proyectos (por defecto ~/Proyectos)")
    p_revisar.add_argument("--origen", default=None, help="Ruta de ESTRUCTURA.md")

    # Subcomando completar
    p_completar = subparsers.add_parser("completar", help="Crea los archivos obligatorios faltantes según el molde")
    p_completar.add_argument("carpeta", help="Carpeta donde crear la estructura")
    p_completar.add_argument("--nivel", required=True, choices=["empresa", "area", "proyecto"], help="Nivel de la caja")
    p_completar.add_argument("--origen", default=None, help="Ruta de ESTRUCTURA.md")

    # Subcomando arreglar
    p_arreglar = subparsers.add_parser("arreglar", help="Muestra el plan (o con --si crea) lo seguro que falta")
    p_arreglar.add_argument("carpeta", nargs="?", default=None, help="Carpeta a arreglar (por defecto la actual)")
    p_arreglar.add_argument("--todas", action="store_true", help="Todas las cajas bajo ~/Proyectos/ o --raiz")
    p_arreglar.add_argument("--raiz", default=None, help="Raíz de proyectos (por defecto ~/Proyectos)")
    p_arreglar.add_argument("--origen", default=None, help="Ruta de ESTRUCTURA.md")
    p_arreglar.add_argument("--si", action="store_true", help="Aplica el plan (sin esto solo lo muestra)")

    args = parser.parse_args()

    if args.comando == "dibujo":
        sys.exit(comando_dibujo(salida_ruta=args.salida, origen_ruta=args.origen))
    elif args.comando == "revisar":
        sys.exit(comando_revisar(
            carpeta_arg=args.carpeta,
            todas=args.todas,
            nivel_arg=args.nivel,
            aviso=args.aviso,
            raiz_arg=args.raiz,
            origen_arg=args.origen,
        ))
    elif args.comando == "arreglar":
        sys.exit(comando_arreglar(
            carpeta_arg=args.carpeta,
            todas=args.todas,
            raiz_arg=args.raiz,
            origen_arg=args.origen,
            aplicar=args.si,
        ))
    elif args.comando == "completar":
        sys.exit(comando_completar(
            carpeta_arg=args.carpeta,
            nivel=args.nivel,
            origen_arg=args.origen,
        ))


if __name__ == "__main__":
    main()
