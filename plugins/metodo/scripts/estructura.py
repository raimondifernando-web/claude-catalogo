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
- brief [CARPETA]   (brief para una sesión secundaria con lo que vale arreglar)
- descartar CLAVE   (anota un aviso que se decidió no hacer)
- arreglar [CARPETA] [--todas] [--raiz RUTA] [--origen RUTA] [--si]   (sin --si solo muestra el plan)
"""
import argparse
from datetime import date
import json
import unicodedata
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

# Instante (time.monotonic) en que vence la pasada del bucle de orden (C152): mientras está puesto, ninguna llamada a
# git pasa de ese instante, tampoco las de las funciones de este archivo que el bucle usa. None = sin tope.
LIMITE_GIT = None


ARCHIVO_CLAVES = ".env"                    # las claves de la persona (nunca a GitHub)
ARCHIVO_CLAVES_EJEMPLO = ".env.example"    # qué claves hacen falta, sin valores (sí a GitHub)


def ejecutar_git(*args, cwd=None, timeout=10, config=()):
    """Ejecuta comando git con subprocess, sin shell y con -c core.fsmonitor=.
    `config`: pares «clave=valor» extra para `-c` (el bucle de orden apaga los hooks); `timeout` en segundos."""
    if not shutil.which("git"):
        return None, "git no está disponible"
    if LIMITE_GIT is not None:
        import time
        resto = LIMITE_GIT - time.monotonic()
        if resto <= 0:
            return None, "se terminó el tiempo de la pasada"
        timeout = max(0.5, min(timeout, resto))
    # --no-optional-locks: una lectura (status) cortada por tiempo no deja .git/index.lock trabando la carpeta
    cmd = ["git", "--no-optional-locks", "-c", "core.fsmonitor="]
    for c in config:
        cmd.extend(["-c", c])
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
            timeout=timeout,
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
    """Señales baratas de que la caja es desarrollo (ver «Tres documentos vivos en toda caja» en ESTRUCTURA.md); decide el contenido del PRD."""
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


def hay_codigo_propio(carpeta: Path) -> bool:
    """¿La caja tiene un programa propio (código de aplicación)? Las señales de `tiene_codigo`, o al menos 5 archivos de
    código a dos niveles sin contar `scripts/`, `docs/` ni `tests/`. Es la medida para pedir README, arquitectura, pruebas y
    operación: una caja de consultoría con mucho historial pero sin programa no los necesita. Barato: nunca recorre más de
    dos niveles ni entra a carpetas ocultas o de dependencias."""
    if tiene_codigo(carpeta):
        return True
    saltar = {"node_modules", "venv", ".venv", "dist", "build", "__pycache__", "graphify-out", "scripts", "docs", "tests"}
    cuenta = 0
    try:
        base = len(carpeta.parts)
        for raiz_d, dirs, archivos in os.walk(carpeta):
            # no entra a las cajas de adentro (tienen su propio .git): el código de una caja hija es de ella, no de la que la contiene
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in saltar and not (Path(raiz_d) / d).is_symlink()
                       and not (Path(raiz_d) / d / ".git").exists()]
            if len(Path(raiz_d).parts) - base >= 2:
                dirs[:] = []
            cuenta += sum(1 for a in archivos if Path(a).suffix.lower() in EXTENSIONES_CODIGO)
            if cuenta >= 5:
                return True
    except OSError:
        pass
    return False


def necesita_documentos(carpeta: Path) -> bool:
    """¿La caja tiene un producto propio que documentar (PRD, decisiones, planes)? Sí si tiene código de aplicación
    (`hay_codigo_propio`) o un historial de más de 100 commits propios. Una caja de paso, de consultoría o contenedora no los
    necesita: sería crear archivos que nadie lee."""
    if hay_codigo_propio(carpeta):
        return True
    if (carpeta / ".git").exists():
        code, out = ejecutar_git("rev-list", "--count", "HEAD", cwd=carpeta)
        return code == 0 and out.strip().isdigit() and int(out.strip()) > 100
    return False


# Excepciones escritas: algo que se decidió dejar así, con su motivo, en vez de un ✗ para siempre.
# Archivo `.estructura-excepciones.json` en la raíz del repositorio de la caja (en una copia de trabajo, git worktree,
# se busca primero en la copia y después en la principal). Lista de {"regla", "ruta", "motivo", "fecha"}; «ruta» es
# la carpeta de la que habla el hallazgo, relativa a esa raíz («.» = la raíz misma). Sin motivo o sin fecha no vale.
ARCHIVO_EXCEPCIONES = ".estructura-excepciones.json"
# R11 (la raíz de proyectos no es un repo) y R6 (secretos en GitHub) no se pueden exceptuar nunca.
NO_EXCEPTUABLES = ("R6", "R11")


def raiz_del_repo(carpeta: Path):
    """(raíz del repositorio, raíz de la copia principal si esta es una copia de trabajo, o None)."""
    raiz = carpeta
    while not (raiz / ".git").exists():
        if raiz.parent == raiz:
            return None, None
        raiz = raiz.parent
    principal = None
    if (raiz / ".git").is_file():
        code, out = ejecutar_git("rev-parse", "--path-format=absolute", "--git-common-dir", cwd=raiz)
        if code == 0 and out:
            principal = Path(out).parent
    return raiz, principal


def cargar_excepciones(carpeta: Path):
    """Lee las excepciones del repositorio de esta caja. Devuelve (validas, avisos, raiz):
    validas = {(regla, ruta): motivo}; avisos = [texto] de las que no valen (se ignoran)."""
    raiz, principal = raiz_del_repo(carpeta)
    if raiz is None:
        return {}, [], None
    archivo = next((c / ARCHIVO_EXCEPCIONES for c in (raiz, principal)
                    if c is not None and (c / ARCHIVO_EXCEPCIONES).is_file()), None)
    if archivo is None:
        return {}, [], raiz
    try:
        datos = json.loads(archivo.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return {}, [f"{ARCHIVO_EXCEPCIONES} no es un JSON válido: se ignoran sus excepciones"], raiz
    if not isinstance(datos, list):
        return {}, [f"{ARCHIVO_EXCEPCIONES} tiene que ser una lista: se ignoran sus excepciones"], raiz
    validas, avisos = {}, []
    for i, e in enumerate(datos, 1):
        if not isinstance(e, dict):
            avisos.append(f"excepción {i} ignorada: no es un objeto")
            continue
        regla, ruta = str(e.get("regla", "")).strip().upper(), str(e.get("ruta", "")).strip().strip("/") or "."
        motivo, fecha = str(e.get("motivo", "")).strip(), str(e.get("fecha", "")).strip()
        if not re.fullmatch(r"R\d+", regla):
            avisos.append(f"excepción {i} ignorada: falta la regla (R1, R8…)")
        elif regla in NO_EXCEPTUABLES:
            avisos.append(f"excepción {i} ({regla}) ignorada: esa regla no se puede exceptuar")
        elif not motivo or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", fecha):
            avisos.append(f"excepción {i} ({regla} {ruta}) ignorada: necesita motivo y fecha AAAA-MM-DD")
        else:
            validas[(regla, ruta)] = motivo
    return validas, avisos, raiz


def ruta_en_repo(raiz: Path, carpeta: Path) -> str:
    try:
        rel = carpeta.resolve().relative_to(raiz.resolve()).as_posix()
    except ValueError:
        return carpeta.name
    return rel or "."


DOCUMENTOS_VIVOS = ("docs/PRD.md", "docs/decisiones.md", "docs/planes/")


def faltan_documentos_vivos(carpeta: Path) -> list:
    """Cuáles de los tres documentos vivos (PRD, decisiones, planes/) no están en la caja."""
    faltan = []
    for rel in DOCUMENTOS_VIVOS:
        ruta = carpeta / rel.rstrip("/")
        if not (ruta.is_dir() if rel.endswith("/") else ruta.is_file()):
            faltan.append(rel)
    return faltan


# ==============================================================================
# 3a. PIEZAS DE DESARROLLO (R22-R28): lo que una caja con código necesita para que otra persona (o la nube) la entienda,
# la levante y la opere. Todo mecánico y barato (sin IA). Solo avisos: el consejo decide si vale una sesión.
# ==============================================================================
DIAS_REVISION_SEGURIDAD = 90
DIAS_ESQUEMA_VIEJO = 30


def _etiqueta_con_valor(texto: str, etiqueta: str) -> bool:
    """¿Hay una línea «Etiqueta: valor» (con o sin viñeta o negrita) y el valor no está vacío? `- **Estado:**` vacío no cuenta."""
    for m in re.finditer(r"(?im)^[ \t\-*_]*" + re.escape(etiqueta) + r"\**[ \t]*:(.*)$", texto):
        if m.group(1).strip(" \t*_"):
            return True
    return False


def _sin_tildes(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")


def _settings_con_contenido(ruta: Path) -> bool:
    """¿El settings.json dice algo (permisos, paquetes, hooks)? Un `{}` no. Si no se puede leer, se considera que sí (ante la duda, se mide)."""
    try:
        d = json.loads(ruta.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return True
    return not (isinstance(d, dict) and not d)
_SENALES_DESPLIEGUE = ("Dockerfile", "docker-compose.yml", "docker-compose.yaml", "vercel.json", "fly.toml", "render.yaml",
                       "Procfile", "netlify.toml")
_PARTES_OPERACION = (("dónde corre", "dónde corre"), ("cómo se despliega", "desplieg"), ("claves", "clave"),
                     ("datos y respaldo", "respaldo"))
_PATRON_PRUEBA = re.compile(r"(^test_.*\.py$)|(_test\.[a-z]+$)|(\.(test|spec)\.[a-z]+$)", re.I)


def _recorrer(carpeta: Path, profundidad: int, ocultas=False):
    """Archivos de una caja hasta cierta profundidad, sin carpetas ocultas, de dependencias ni enlaces."""
    saltar = {"node_modules", "venv", ".venv", "dist", "build", "__pycache__", "graphify-out"}
    base = len(carpeta.parts)
    for raiz_d, dirs, archivos in os.walk(carpeta):
        dirs[:] = [d for d in dirs if (ocultas or not d.startswith(".")) and d not in saltar and not (Path(raiz_d) / d).is_symlink()
                   and not (Path(raiz_d) / d / ".git").exists()]   # las cajas de adentro tienen lo suyo
        if len(Path(raiz_d).parts) - base >= profundidad:
            dirs[:] = []
        yield Path(raiz_d), list(dirs), archivos


def se_despliega(carpeta: Path) -> bool:
    """¿La caja corre en un servidor o servicio (no solo en la Mac)? Señales de archivo, en la raíz o un nivel adentro."""
    try:
        for n in _SENALES_DESPLIEGUE:
            if (carpeta / n).is_file() or any(not (d.parent / ".git").exists() for d in carpeta.glob(f"*/{n}")):
                return True
        wf = carpeta / ".github" / "workflows"
        if wf.is_dir() and any(re.search(r"deploy|despleg|release|publish", f.name, re.I) for f in wf.iterdir()):
            return True
        return any(carpeta.glob("*.plist"))
    except OSError:
        return False


def hay_pruebas(carpeta: Path) -> bool:
    """¿Hay pruebas? Una carpeta tests/test/__tests__ o archivos test_*.py, *_test.*, *.test.*, *.spec.* (hasta 3 niveles)."""
    try:
        for _raiz, dirs, archivos in _recorrer(carpeta, 3):
            if any(d in ("tests", "test", "__tests__") for d in dirs) or any(_PATRON_PRUEBA.search(a) for a in archivos):
                return True
    except OSError:
        pass
    return False


def _fecha_en_nombre(nombre: str):
    m = re.search(r"(\d{4}-\d{2}-\d{2})", nombre)
    try:
        return date.fromisoformat(m.group(1)) if m else None
    except ValueError:
        return None


def revision_seguridad_mas_nueva(carpeta: Path):
    """Fecha de la revisión de seguridad registrada más nueva (`.claude/security-checks/AAAA-MM-DD…md`), o None."""
    d = carpeta / ".claude" / "security-checks"
    try:
        fechas = [f for f in (_fecha_en_nombre(x.name) for x in d.iterdir() if x.is_file()) if f]
    except OSError:
        return None
    return max(fechas) if fechas else None


def revisar_desarrollo(carpeta: Path) -> list:
    """R23-R26 y R28. Retorna [(tipo, id, mensaje)] (todos «aviso»)."""
    h = []
    codigo = hay_codigo_propio(carpeta)
    despliega = se_despliega(carpeta)
    if codigo:
        # R23: README, arquitectura (TRD), flujo de la app y qué claves hacen falta
        faltan = [rel for rel in ("README.md", "docs/arquitectura.md", "docs/flujo-de-la-app.md", ARCHIVO_CLAVES_EJEMPLO)
                  if not (carpeta / rel).is_file()]
        if faltan:
            h.append(("aviso", "R23", "la caja tiene código y le faltan: " + ", ".join(faltan)))
        # R24: pruebas, y que alguien diga cómo correrlas
        if not hay_pruebas(carpeta):
            h.append(("aviso", "R24", "la caja tiene código pero no se encontraron pruebas"))
        elif not any(re.search(r"\b(pruebas?|tests?|pytest|unittest|jest|vitest)\b", _lee(carpeta / n), re.I) for n in ("README.md", "CLAUDE.md")):
            h.append(("aviso", "R24", "tiene pruebas pero ni el README ni el CLAUDE.md dicen cómo correrlas"))
    if despliega:
        # R25: operación
        op = carpeta / "docs" / "operacion.md"
        if not op.is_file():
            h.append(("aviso", "R25", "la caja se despliega pero falta docs/operacion.md (dónde corre, cómo se despliega y se vuelve atrás, claves, datos y respaldo)"))
        else:
            titulos = _sin_tildes(" ".join(l.lower() for l in _lee(op).splitlines() if l.lstrip().startswith("#")))
            sin = [nombre for nombre, clave in _PARTES_OPERACION if _sin_tildes(clave) not in titulos]
            if sin:
                h.append(("aviso", "R25", "docs/operacion.md no tiene estas partes: " + ", ".join(sin)))
    if codigo or despliega:
        # R26: una revisión de seguridad registrada y reciente
        if despliega or (carpeta / ARCHIVO_CLAVES).exists() or (carpeta / ARCHIVO_CLAVES_EJEMPLO).exists():
            ultima = revision_seguridad_mas_nueva(carpeta)
            if ultima is None:
                h.append(("aviso", "R26", "se despliega o usa claves y no hay ninguna revisión de seguridad registrada en .claude/security-checks/"))
            elif (date.today() - ultima).days > DIAS_REVISION_SEGURIDAD:
                h.append(("aviso", "R26", f"la última revisión de seguridad registrada es del {ultima.isoformat()} (más de {DIAS_REVISION_SEGURIDAD} días)"))
    # R28: lo generado dice con qué comando y cuándo se generó, y no quedó viejo respecto del código
    esquema = carpeta / "docs" / "esquema"
    if esquema.is_dir():
        txt = _lee(esquema / "LEEME.md")
        comando = re.search(r"(?im)^\W*comando\s*:\s*\S", txt)
        fecha = re.search(r"(?im)^\W*fecha\s*:\s*(\d{4}-\d{2}-\d{2})", txt)
        if not (comando and fecha and _fecha_en_nombre(fecha.group(1))):
            h.append(("aviso", "R28", "docs/esquema/ no tiene un LEEME.md con «Comando:» y «Fecha: AAAA-MM-DD» (cómo y cuándo se generó)"))
        elif (carpeta / ".git").exists():
            generado = _fecha_en_nombre(fecha.group(1))
            code, out = ejecutar_git("log", "-1", "--format=%cs", "--", ".", ":(exclude)docs", cwd=carpeta)
            codigo_cambio = _fecha_en_nombre(out) if code == 0 and out else None
            if generado and codigo_cambio and (codigo_cambio - generado).days > DIAS_ESQUEMA_VIEJO:
                h.append(("aviso", "R28", f"docs/esquema/ se generó el {generado.isoformat()} y el código cambió después (el {codigo_cambio.isoformat()}): volver a generarlo"))
    return h


# ==============================================================================
# 3b. CONTENIDO (R13-R18): que lo escrito en los archivos sea correcto, no solo que el archivo exista
# ==============================================================================
# Todo mecánico (sin IA). Lo que pide juicio (¿el CLAUDE.md dice algo contradictorio?) no se mide acá.
_RUTA_PREFIJOS = ("~/", "./", "docs/", ".claude/", "scripts/", "plugins/", "src/")
_RUTA_PERSONAL = {".env", "CLAUDE.local.md", "settings.local.json"}   # personales: pueden no existir
_RUTA_GENERADA = ("graphify-out", "node_modules", ".omc", "__pycache__", ".venv", "dist/", "out/", ".git/")
_CONTEO = re.compile(r"\b(\d{2,})\s+(agentes|skills|plugins|PMs|proyectos|cajas|workflows|scripts|hooks|MCPs|repos)\b", re.I)
_BACKTICK = re.compile(r"`([^`\n]+)`")
_HISTORICA = re.compile(r"ya no existe|retirad|archivad|borrad|obsolet|desinstalad|apagad|antes:|\bera\b|\beran\b|viej", re.I)
MAX_EJEMPLOS = 3


def _misma_carpeta(a: Path, b: Path) -> bool:
    try:
        return os.path.samefile(a, b)
    except OSError:
        return False


def _lee(ruta: Path) -> str:
    try:
        return ruta.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def rutas_citadas_que_faltan(texto: str, carpeta: Path) -> list:
    """Rutas entre `comillas` que el texto cita y no existen (relativas a la caja o a la raíz de su repo)."""
    code, top = ejecutar_git("rev-parse", "--show-toplevel", cwd=carpeta)
    bases = [carpeta] + ([Path(top)] if code == 0 and top and Path(top) != carpeta else [])
    faltan = []
    for linea in texto.splitlines():
        if _HISTORICA.search(linea):
            continue
        for tok in _BACKTICK.findall(linea):
            tok = tok.strip().rstrip(".,;:)")
            tok = re.sub(r"(:\d+)+$", "", tok.split("#", 1)[0])   # sin ancla (#) ni archivo:línea[:columna]
            if not tok.startswith(_RUTA_PREFIJOS) or " " in tok or any(c in tok for c in "<>*{}$…|()[]"):
                continue
            if ".." in tok.split("/") or tok.rstrip("/").rsplit("/", 1)[-1] in _RUTA_PERSONAL:
                continue
            if any(g.rstrip("/") in tok.split("/") or g in ("graphify-out", "node_modules") and g in tok for g in _RUTA_GENERADA):
                continue
            if tok in ("~/", "./") or ("/" not in tok.lstrip("~./") and not tok.startswith("./")):
                continue
            try:
                if tok.startswith("~/"):
                    existe = Path(os.path.expanduser(tok)).exists()
                else:
                    existe = any((b / tok).exists() for b in bases)
            except OSError:   # sin permiso o nombre demasiado largo: no se puede afirmar que falte
                existe = True
            if not existe and tok not in faltan:
                faltan.append(tok)
    return faltan


def _agentes_conocidos(carpeta: Path) -> set:
    nombres = set()
    dirs = [Path.home() / ".claude" / "agents"]
    p = carpeta
    for _ in range(4):
        dirs.append(p / ".claude" / "agents")
        p = p.parent
    for d in dirs:
        if d.is_dir():
            nombres.update(f.stem for f in d.glob("*.md"))
    cache = Path.home() / ".claude" / "plugins" / "cache"
    if cache.is_dir():
        for f in cache.glob("*/*/*/agents/*.md"):
            nombres.add(f.stem)
    return nombres


def _lineas_de_plantilla() -> set:
    """Las líneas de las plantillas de PRD y decisiones (también la versión anterior, con la sección técnica adentro)."""
    return {l.strip() for t in (PLANTILLA_PRD, LEGADO_PRD_TECNICO, PLANTILLA_DECISIONES) for l in t.splitlines() if l.strip()}


def _sin_instrucciones(texto: str) -> str:
    """El texto de un documento sin títulos, citas ni líneas de la plantilla (la plantilla sin completar queda vacía)."""
    plantilla = _lineas_de_plantilla()
    return "\n".join(l for l in texto.splitlines()
                     if l.strip() and not l.lstrip().startswith(("#", ">", "<!--")) and l.strip() not in plantilla)


def revisar_contenido(carpeta: Path) -> list:
    """R13-R18, cada grupo aislado: si una regla falla por algo imprevisto, las demás igual corren."""
    h = []
    for grupo in (_contenido_claude_md, _contenido_documentos, _contenido_pendientes, _contenido_reanudar):
        try:
            h.extend(grupo(carpeta))
        except Exception as e:   # el control nunca rompe un arranque
            h.append(("aviso", "R12", f"no se pudo revisar {grupo.__name__[11:]} ({type(e).__name__})"))
    return h


def _contenido_claude_md(carpeta: Path) -> list:
    h = []
    claude_md = carpeta / "CLAUDE.md"
    if claude_md.is_file():
        texto = _lee(claude_md)
        # R13: rutas citadas que no existen
        falta = rutas_citadas_que_faltan(texto, carpeta)
        if falta:
            h.append(("aviso", "R13", f"CLAUDE.md cita {len(falta)} ruta(s) que no existen: " + ", ".join(falta[:MAX_EJEMPLOS])
                      + (" …" if len(falta) > MAX_EJEMPLOS else "")))
        # R14: conteos escritos a mano (se desactualizan)
        conteos = []
        for linea in texto.splitlines():
            if linea.lstrip().startswith(("|", "#")) or _HISTORICA.search(linea) or re.search(r"\d{4}-\d{2}-\d{2}", linea):
                continue
            conteos += [f"{n} {w}" for n, w in _CONTEO.findall(linea)]
        if conteos:
            h.append(("aviso", "R14", f"CLAUDE.md tiene {len(conteos)} conteo(s) escrito(s) a mano que se desactualizan: "
                      + ", ".join(dict.fromkeys(conteos))[:120]))
        # R15: agentes PM que nombra y no existen
        pms = sorted(set(re.findall(r"\bpm-[a-z0-9]+(?:-[a-z0-9]+)*\b", "\n".join(l for l in texto.splitlines() if not _HISTORICA.search(l)))))
        conocidos = _agentes_conocidos(carpeta)
        if pms and conocidos:
            sueltos = [x for x in pms if x not in conocidos]
            if sueltos:
                h.append(("aviso", "R15", "CLAUDE.md nombra agente(s) que no existen: " + ", ".join(sueltos[:MAX_EJEMPLOS])))
        # R19-R21: el equipo (PM, skills del PM, conectores); aislado: si falla, lo dice y las demás reglas siguen
        try:
            import estructura_equipo
            h.extend(estructura_equipo.revisar(carpeta, "\n".join(l for l in texto.splitlines() if not _HISTORICA.search(l))))
        except Exception as e:
            h.append(("aviso", "R19", f"no se pudo revisar el equipo ({type(e).__name__})"))
    return h


def _contenido_documentos(carpeta: Path) -> list:
    h = []
    # R16: documentos vivos que siguen siendo la plantilla (se compara contra las líneas de la plantilla, no solo contra
    # títulos y citas: antes, las frases de ayuda de la sección técnica contaban como contenido propio)
    vacios = [rel for rel in ("docs/PRD.md", "docs/decisiones.md")
              if (carpeta / rel).is_file() and len(_sin_instrucciones(_lee(carpeta / rel))) < 40]
    if vacios:
        h.append(("aviso", "R16", "siguen sin completar (solo la plantilla): " + ", ".join(vacios)))
    # R27: un PRD ya escrito dice quién lleva la caja, en qué estado está y dónde está su respaldo
    prd = carpeta / "docs" / "PRD.md"
    if prd.is_file() and "docs/PRD.md" not in vacios:
        txt = _lee(prd)
        sin = [etq for etq in ("Dueño", "Estado", "Respaldo", "Última revisión") if not _etiqueta_con_valor(txt, etq)]
        if sin:
            h.append(("aviso", "R27", "docs/PRD.md no dice: " + ", ".join(sin)))
    return h


def _contenido_pendientes(carpeta: Path) -> list:
    h = []
    # R17: PENDIENTES.md en el formato que lee el panel
    pend = carpeta / ".claude" / "PENDIENTES.md"
    if pend.is_file():
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("pendientes_check", Path(__file__).with_name("pendientes-check.py"))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            prob, _ids, _ult = mod.analizar(_lee(pend))
            if prob:
                h.append(("aviso", "R17", f".claude/PENDIENTES.md tiene {len(prob)} problema(s) de formato: " + " | ".join(prob[:2])))
        except Exception:
            h.append(("aviso", "R17", "no se pudo revisar .claude/PENDIENTES.md"))
    return h


def _contenido_reanudar(carpeta: Path) -> list:
    h = []
    # R18: el texto de reanudación (REANUDAR.md) coherente con la caja
    rea = carpeta / ".claude" / "prompts" / "REANUDAR.md"
    if rea.is_file():
        t = _lee(rea)
        problemas = []
        if len(t.splitlines()) > 120:
            problemas.append(f"tiene {len(t.splitlines())} líneas (conviene ≤ 120: contrato + estado, no un informe)")
        m = re.search(r"Worktree:\s*`?(\S+?)`?\s*·\s*Rama:\s*`?([^\s`]+)", t)
        if m and (m.group(1).startswith(("~", "/")) or re.match(r"[A-Za-z]:[\\/]", m.group(1))):
            wt = Path(os.path.expanduser(m.group(1))).resolve()
            if not wt.exists():
                problemas.append(f"dice Worktree {m.group(1)} y esa carpeta no existe")
            elif _misma_carpeta(wt, carpeta):
                code, rama = ejecutar_git("branch", "--show-current", cwd=carpeta)
                if code == 0 and rama and rama != m.group(2).rstrip(".,;"):
                    problemas.append(f"dice Rama {m.group(2)} y la caja está en {rama}")
        c = re.search(r"cierre (\d{4})-(\d{2})-(\d{2})", t[:800])
        if c:
            try:
                dias = (date.today() - date(int(c.group(1)), int(c.group(2)), int(c.group(3)))).days
                if dias > 30:
                    problemas.append(f"el último cierre es de hace {dias} días (más de 30)")
            except ValueError:
                pass
        falta = rutas_citadas_que_faltan(t, carpeta)
        if falta:
            problemas.append(f"cita {len(falta)} ruta(s) que no existen: " + ", ".join(falta[:MAX_EJEMPLOS]))
        if problemas:
            h.append(("aviso", "R18", "REANUDAR.md " + "; ".join(problemas)))
    return h


def revisar_caja(carpeta: Path, nivel: str, parent_caja: Path = None) -> list:
    """Aplica las reglas R1-R10 y R12 a una caja concreta, descontando las excepciones escritas.
    Retorna [(tipo, id, mensaje)]; tipo «excepcion» = lo decidido dejar así (no cuenta como falla)."""
    hallazgos = _revisar_caja(carpeta, nivel, parent_caja)
    excepciones, avisos, raiz = cargar_excepciones(carpeta)
    if raiz is None:
        return hallazgos
    mia = ruta_en_repo(raiz, carpeta)
    salida = []
    for tipo, r_id, msg in hallazgos:
        exceptuable = tipo == "error" or r_id in ("R12", "R13", "R14", "R15", "R16", "R17", "R18", "R22", "R23", "R24", "R25", "R26", "R27", "R28", "R29")  # son avisos, pero también se pueden dejar así por escrito
        if exceptuable and r_id not in NO_EXCEPTUABLES and r_id != "R8" and (r_id, mia) in excepciones:
            salida.append(("excepcion", r_id, f"{msg} (motivo: {excepciones[(r_id, mia)]})"))
        else:
            salida.append((tipo, r_id, msg))
    if mia == ".":
        salida.extend(("aviso", "EXC", a) for a in avisos)
    return salida


def _revisar_caja(carpeta: Path, nivel: str, parent_caja: Path = None) -> list:
    """Las reglas R1-R10 y R12 de una caja, sin excepciones. Retorna [(tipo, id, mensaje)]."""
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

    # R22: settings.json está subido a GitHub (existir en el disco no alcanza: si no se sube, no llega a otra persona,
    # a la nube ni a una Mac nueva). Lo más común: un ignore global de la persona lo oculta.
    # Un settings.json vacío ({}) no tiene nada que compartir: avisar por él sería ruido (28 de las 33 cajas lo tienen así).
    if settings_json.is_file() and git_dir.exists() and shutil.which("git") and _settings_con_contenido(settings_json):
        code, out = ejecutar_git("ls-files", "--", ".claude/settings.json", cwd=carpeta)
        if code == 0 and not out:
            c2, v = ejecutar_git("check-ignore", "-v", ".claude/settings.json", cwd=carpeta)
            causa = ""
            if c2 == 0 and v:
                fuente = v.split("\t")[0].rsplit(":", 2)[0]   # «archivo:línea:patrón»
                causa = (" (lo oculta la lista global de ignorados de esta Mac)" if Path(fuente).is_absolute()
                         else " (lo oculta el .gitignore de la caja)")
            hallazgos.append(("aviso", "R22", f".claude/settings.json existe pero no está subido a GitHub{causa}: no llega a otra persona, a la nube ni a una Mac nueva"))

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
        excepciones, _avisos, raiz_repo = cargar_excepciones(carpeta)
        for hija in cajas_hijas(carpeta):
            code_ls, out_ls = ejecutar_git("ls-files", "--", hija.name, cwd=carpeta)
            code_ci, _ = ejecutar_git("check-ignore", "-q", "--no-index", hija.name + "/", cwd=carpeta)
            if (code_ls == 0 and out_ls) or code_ci == 1:
                motivo = excepciones.get(("R8", ruta_en_repo(raiz_repo, hija))) if raiz_repo else None
                if motivo:
                    hallazgos.append(("excepcion", "R8", f"guarda en su repositorio la caja de adentro {hija.name} (motivo: {motivo})"))
                else:
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

    # R12: toda caja (con o sin código) tiene los tres documentos vivos (aviso)
    faltan = faltan_documentos_vivos(carpeta)
    if faltan:
        hallazgos.append(("aviso", "R12", "faltan los documentos vivos: " + ", ".join(faltan)))

    # R23-R26 y R28: las piezas de desarrollo (solo si hay código, despliegue o esquema generado)
    try:
        hallazgos.extend(revisar_desarrollo(carpeta))
    except Exception as e:   # el control nunca rompe un arranque
        hallazgos.append(("aviso", "R23", f"no se pudo revisar las piezas de desarrollo ({type(e).__name__})"))

    # R13-R18 y R27: el contenido de los archivos (rutas, conteos, agentes, documentos, pendientes, reanudación)
    try:
        hallazgos.extend(revisar_contenido(carpeta))
    except Exception as e:   # el control nunca rompe un arranque
        hallazgos.append(("aviso", "R13", f"no se pudo revisar el contenido ({type(e).__name__})"))

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


def _palabra_aviso(n: int) -> str:
    return "aviso" if n == 1 else "avisos"


def _consejos_de(registro):
    """[(clave, nombre, consejo)] de los avisos del registro, ya con acción decidida (sin los «nada»)."""
    import estructura_consejo as C
    res = []
    for tipo, r_id, nombre, msg, c_path, nivel in registro:
        if tipo != "aviso" or set(c_path.parts) & C.CARPETAS_AJENAS:
            continue
        try:
            c = C.consejo(r_id, msg, {"codigo": necesita_documentos(c_path), "nivel": nivel})
        except Exception:   # el consejo nunca rompe un arranque: ante la duda, el aviso crudo
            c = dict(accion="al_pasar", que=msg, cuesta="no se pudo estimar.", conviene="revisarlo cuando abras ese archivo.",
                     hecho="", rinde=10, medida=0)
        if c["accion"] != "nada":
            res.append((C.clave_de(r_id, c_path.name), nombre, c))
    return res


def _dentro(ruta, base) -> bool:
    try:
        Path(ruta).resolve().relative_to(Path(base).resolve())
        return True
    except (ValueError, TypeError, OSError):
        return False


def _imprimir_aviso(lineas_salida, registro, total_errores, aqui=None):
    """El aviso de apertura: errores obligatorios + consejos pensados (qué, cuánto cuesta, qué conviene), sin repetir
    lo ya mostrado ni lo decidido, ordenados por lo que más rinde. Los avisos que no valen la pena no se muestran."""
    import estructura_consejo as C
    hoy = date.today()
    memoria = C.cargar()
    errores = [l for l in lineas_salida if l.startswith("✗")]
    todos = _consejos_de(registro)
    otras = []
    if aqui is not None:   # la pasada semanal ve todas las cajas, pero esta sesión solo atiende la suya
        ruta_de = {C.clave_de(r, p.name): p for _t, r, _n, _m, p, _v in registro}
        otras = [x for x in todos if not _dentro(ruta_de.get(x[0]), aqui)]
        todos = [x for x in todos if x not in otras]
    candidatos = [x for x in todos if C.toca_mostrar(x[0], x[2]["medida"], memoria, hoy)]
    sesion = sorted((x for x in candidatos if x[2]["accion"] == "sesion"), key=lambda x: -x[2]["rinde"])
    al_pasar = [x for x in candidatos if x[2]["accion"] == "al_pasar"]
    clave_otras = "OTRAS:" + (aqui.name if aqui is not None else "")
    hay_otras = bool(otras) and C.toca_mostrar(clave_otras, len(otras), memoria, hoy)
    if not (errores or sesion or al_pasar or hay_otras):
        return
    for l in errores[:MAX_LINEAS_AVISO]:
        print(l)
    if len(errores) > MAX_LINEAS_AVISO:
        print(f"… y {len(errores) - MAX_LINEAS_AVISO} más (estructura.py revisar --todas)")
    mostrados = sesion[:C.MAX_CONSEJOS]
    for clave, nombre, c in mostrados:
        for l in C.lineas_consejo(clave, nombre, c):
            print(l)
    if len(sesion) > len(mostrados):
        print(f"… y {len(sesion) - len(mostrados)} más que valen una sesión (estructura.py brief)")
    if al_pasar:
        det = ", ".join(f"{k.split(':')[0]} {n}" for k, n, _ in al_pasar[:4])
        print(f"• {len(al_pasar)} detalle(s) chico(s) para corregir de paso, sin abrir una sesión aparte: {det}"
              + (" …" if len(al_pasar) > 4 else "") + " (estructura.py revisar)")
    if hay_otras:
        print(f"• Hay {len(otras)} aviso(s) en otras carpetas: no son de esta sesión, no los arregles acá "
              "(los ve su dueña o Tech con `estructura.py revisar --todas`).")
        C.anotar_visto(clave_otras, len(otras), memoria, hoy)
    for clave, _n, c in mostrados + al_pasar:
        C.anotar_visto(clave, c["medida"], memoria, hoy)
    C.guardar(memoria)
    n_av = len(mostrados) + len(al_pasar)
    if total_errores:
        palabra = "cosa" if total_errores == 1 else "cosas"
        print(f"Falta: {total_errores} {palabra} ✗" + (f" · además {n_av} {_palabra_aviso(n_av)} ⚠" if n_av else ""))
    else:
        print(f"Sin errores, pero con {n_av} {_palabra_aviso(n_av)} pendiente{'s' if n_av != 1 else ''} ⚠")
    if errores or sesion:
        print("Claude: no lo arregles en esta sesión. Proponé UNA sesión secundaria (tarjeta `start_session`, «own_initiative») "
              "con el brief de `estructura.py brief` y seguí con lo que te pidieron. Un punto que se decidió no hacer: "
              "`estructura.py descartar <clave>`.")


def comando_brief(carpeta_arg=None) -> int:
    """Brief listo para una sesión secundaria: errores obligatorios + consejos que valen una sesión (menos los descartados)."""
    import estructura_consejo as C
    objetivo = Path(carpeta_arg).resolve() if carpeta_arg else Path.cwd()
    raiz = Path.home() / "Proyectos"
    nivel = detectar_nivel_carpeta(objetivo, raiz)
    parent = objetivo.parent if objetivo.parent != raiz and es_caja(objetivo.parent) else None
    registro, errores = [], []
    for tipo, r_id, msg in revisar_caja(objetivo, nivel, parent_caja=parent):
        if tipo == "error":
            errores.append(f"{r_id} {msg}")
        elif tipo == "aviso":
            registro.append((tipo, r_id, objetivo.name, msg, objetivo, nivel))
    memoria = C.cargar()
    hoy = date.today()
    sesion = [(k, c) for k, _n, c in sorted(_consejos_de(registro), key=lambda x: -x[2]["rinde"])
              if c["accion"] == "sesion" and not ((memoria.get(k) or {}).get("descartado") and not C.empeoro(c["medida"], (memoria.get(k) or {}).get("medida", 0)))]
    if not (errores or sesion):
        print(f"Nada que valga una sesión en {objetivo.name} ✓")
        return 0
    print(C.armar_brief(objetivo.name, str(objetivo), sesion, errores))
    return 0


def comando_descartar(clave: str) -> int:
    import estructura_consejo as C
    if C.descartar(clave):
        print(f"Anotado ✓ no se vuelve a avisar de {clave} (salvo que empeore o pasen {C.DIAS_DESCARTADO} días)")
        return 0
    print("Falta la clave completa del aviso, por ejemplo R3:Mi-Carpeta (la muestra el aviso entre corchetes)")
    return 1


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
    lineas_excepcion = []  # lo decidido dejar así: se muestra, pero no cuenta como falla
    registro = []          # (tipo, regla, nombre a mostrar, mensaje, carpeta, nivel): el aviso lo convierte en consejos
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
                elif tipo == "excepcion":
                    lineas_excepcion.append(f"• excepción {r_id} {rel_display}: {msg}")
                else:
                    registro.append((tipo, r_id, rel_display, msg, c_path, c_nivel))
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
                elif tipo == "excepcion":
                    lineas_excepcion.append(f"• excepción {r_id} {display_name}: {msg}")
                else:
                    registro.append((tipo, r_id, display_name, msg, objetivo, nivel))
                    lineas_salida.append(con_arreglo(r_id, f"• {r_id} {display_name}: {msg}"))

    total_avisos = sum(1 for l in lineas_salida if not l.startswith("✗"))
    # En modo aviso: si todo está bien, no imprime nada y sale 0. Si hay fallas, imprime y sale 0.
    if aviso:
        if primera_vez_semana:
            try:
                estado_dir.mkdir(parents=True, exist_ok=True)
                estado_file.write_text(semana_actual, encoding="utf-8")
            except OSError:
                pass
            try:   # el bucle de orden (C140): la primera vez de la semana, y solo ahí
                import estructura_orden
                estructura_orden.semanal(raiz)
            except Exception:
                pass
        _imprimir_aviso(lineas_salida, registro, total_errores,
                        aqui=(Path(carpeta_arg).resolve() if carpeta_arg else Path.cwd()) if todas else None)
        return 0

    # Modo normal
    for l in lineas_salida + lineas_excepcion:
        print(l)

    if total_errores == 0:
        if total_avisos:
            print(f"Sin errores, pero con {total_avisos} {_palabra_aviso(total_avisos)} pendiente{'s' if total_avisos != 1 else ''} ⚠")
        else:
            print("Estructura al día ✓")
        return 0
    else:
        if total_avisos:
            print(f"Además: {total_avisos} {_palabra_aviso(total_avisos)} pendiente{'s' if total_avisos != 1 else ''} ⚠")
        palabra = "cosa" if total_errores == 1 else "cosas"
        print(f"Falta: {total_errores} {palabra} ✗")
        return 1


# ==============================================================================
# 3c. REMOTO: medir lo que hay en GitHub, no en la carpeta de esta computadora
# ==============================================================================
_BASE_REMOTO = ("CLAUDE.md", ".claude/settings.json", ".gitignore", "docs/PRD.md", "docs/decisiones.md")
_DESARROLLO_REMOTO = ("README.md", "docs/arquitectura.md", "docs/flujo-de-la-app.md", ARCHIVO_CLAVES_EJEMPLO)


def medir_remoto(carpeta: Path, traer: bool = True) -> dict:
    """Lo que hay en la rama principal del repositorio de la caja EN GITHUB (`git fetch` + `git ls-tree`). Solo lee: no toca
    archivos ni ramas de trabajo (el fetch actualiza las referencias remotas). {"estado": ..., "archivos": [...]}"""
    if not (carpeta / ".git").exists():
        return {"estado": "sin .git", "archivos": []}
    code, url = ejecutar_git("remote", "get-url", "origin", cwd=carpeta)
    if code != 0 or not url:
        return {"estado": "sin remoto", "archivos": []}
    if traer:
        code, _ = ejecutar_git("fetch", "--quiet", "origin", cwd=carpeta, timeout=60,
                               config=(f"core.hooksPath={os.devnull}",))   # un hook del repositorio no corre por medir
        if code != 0:
            return {"estado": "no se pudo traer de GitHub", "archivos": []}
    for ref in ("origin/main", "origin/master"):
        code, _ = ejecutar_git("rev-parse", "--verify", "--quiet", ref, cwd=carpeta)
        if code == 0:
            code, out = ejecutar_git("ls-tree", "-r", "--name-only", ref, cwd=carpeta, timeout=60)
            if code == 0:
                return {"estado": "ok", "archivos": out.splitlines()}
    return {"estado": "sin rama principal en GitHub", "archivos": []}


def comando_remoto(raiz_arg=None, traer: bool = True) -> int:
    """`estructura.py remoto`: cuántas cajas tienen en GITHUB el molde completo. Es la medida de «terminado»; `revisar` mira la
    carpeta de la computadora, que puede ir atrasada respecto de GitHub."""
    raiz = Path(raiz_arg).resolve() if raiz_arg else (Path.home() / "Proyectos")
    medidas = completas = con_settings = con_codigo = codigo_completo = 0
    for carpeta, _nivel, _parent in descubrir_cajas(raiz):
        rel = str(carpeta.relative_to(raiz))
        r = medir_remoto(carpeta, traer)
        if r["estado"] != "ok":
            print(f"• {rel}: no se pudo medir ({r['estado']})")
            continue
        medidas += 1
        a = set(r["archivos"])
        faltan = [x for x in _BASE_REMOTO if x not in a]
        local_settings = carpeta / ".claude" / "settings.json"
        if ".claude/settings.json" in faltan and local_settings.is_file() and not _settings_con_contenido(local_settings):
            faltan.remove(".claude/settings.json")   # un settings.json vacío ({}) no tiene nada que compartir (igual que R22)
        if not any(x.startswith("docs/planes/") for x in a):
            faltan.append("docs/planes/")
        con_settings += ".claude/settings.json" in a
        codigo = hay_codigo_propio(carpeta)
        if codigo:
            con_codigo += 1
            falta_dev = [x for x in _DESARROLLO_REMOTO if x not in a]
            codigo_completo += not falta_dev
            faltan += falta_dev
        if not faltan:
            completas += 1
        else:
            print(f"• {rel}: falta en GitHub: {', '.join(faltan)}")
    print(f"En GitHub: {medidas} cajas medidas · {completas} con el molde completo · {con_settings} con settings.json subido · "
          f"{con_codigo} con código ({codigo_completo} con README, arquitectura, flujo y claves de ejemplo)")
    return 0


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

> Documento vivo: qué es esta caja. Lo completa quien la lleva con Claude; no se inventa nada.
> Acá se guarda: quién la lleva, qué es, para quién, cuándo está terminada y qué NO se hace. Una decisión va en
> docs/decisiones.md; un plan de etapa, en docs/planes/. Si la caja tiene código: cómo está armada va en
> docs/arquitectura.md y cómo se mueve la persona por la app, en docs/flujo-de-la-app.md.
> Estado: activa, dormida o archivada. Respaldo: dónde está la copia además de GitHub (Drive, disco externo, ninguna).

- Dueño:
- Estado:
- Respaldo:
- Última revisión:

## Qué es y para quién

## Cuándo está terminado

## Qué NO se hace
"""

# Texto de las versiones anteriores de la plantilla (la sección técnica vivía dentro del PRD): sirve para reconocer
# como «sin completar» los PRD ya creados con ese texto.
LEGADO_PRD_TECNICO = """
## Sección técnica (TRD)
Cómo está armado: piezas, dependencias, dónde corre. El esquema de datos se genera desde el código, no se escribe a mano.

## Flujo de la app
Diagrama de cómo se mueve la persona por la app. Las pantallas van como mockups (Figma o HTML), no como texto.
"""

PLANTILLA_ARQUITECTURA = """# {nombre} — Arquitectura (TRD)

> Cómo está armado por dentro. Lo completa quien lleva la caja a partir del código; no se inventa nada.
> El esquema de datos NO se escribe a mano: se genera desde el código y va en docs/esquema/.
> El recorrido de la persona por la app va en docs/flujo-de-la-app.md; el diseño de pantallas, en docs/diseno/.

## Piezas
Qué partes tiene y qué hace cada una.

## Dependencias y servicios externos
De qué depende y qué pasa si se cae.

## Dónde corre
Dónde vive (esta Mac, un servidor, un servicio en internet) y cómo se entra. Cómo se despliega va en docs/operacion.md.
"""

PLANTILLA_FLUJO = """# {nombre} — Flujo de la app

> Cómo se mueve la persona por la app, paso a paso: por dónde entra, qué ve, qué decide, adónde llega.
> Va como diagrama (Mermaid, que GitHub dibuja solo) o como lista de pasos. Las pantallas se dibujan en
> docs/diseno/ (mockups: HTML o enlace a Figma), no acá.

## Recorrido principal
```mermaid
flowchart TD
    A[Entra] --> B[Hace algo] --> C[Llega a un resultado]
```
"""

PLANTILLA_README = """# {nombre}

Qué es, en una frase.

## Cómo se levanta

## Cómo se prueba

## Dónde está cada cosa
Ver `docs/PRD.md` (qué es), `docs/arquitectura.md` (cómo está armado) y `docs/decisiones.md` (qué se decidió y por qué).
"""

PLANTILLA_ENV_EJEMPLO = """# Nombres de las claves y variables que necesita esta caja, SIN los valores. Una por línea: NOMBRE=
# Si no usa ninguna, dejar solo este comentario.
"""

DONDE_VA = """# Dónde va cada cosa en esta caja
Qué es, para quién y quién la lleva → `docs/PRD.md` · Decisiones con fecha y el porqué → `docs/decisiones.md` · Un plan por etapa → `docs/planes/AAAA-MM-DD-tema.md`
Cómo está armado (TRD) → `docs/arquitectura.md` · Cómo se mueve la persona por la app → `docs/flujo-de-la-app.md` · Pantallas (mockups, Figma) → `docs/diseno/`
Esquema de datos y API, GENERADOS desde el código → `docs/esquema/` (con el comando y la fecha) · Qué debe hacer cada funcionalidad → `docs/specs/`
Dónde corre, cómo se despliega y se vuelve atrás, claves (solo nombres), datos y respaldo → `docs/operacion.md`
Revisiones de seguridad → `.claude/security-checks/AAAA-MM-DD.md` · Pruebas → `tests/` (y cómo correrlas, en el README) · Claves que hacen falta (sin valores) → `.env.example`
Nunca: valores de claves en ningún archivo · un esquema de datos escrito a mano · un documento nuevo si ya hay uno para esa cosa.
"""

PLANTILLA_DECISIONES = """# {nombre} — Decisiones

> Registro de decisiones: cada una con su fecha y el porqué, para no volver a discutirla.
> Se agrega al final, una por bloque, la más nueva abajo. Nunca se borra una vieja: si cambia, se anota la nueva.
> Ejemplo mínimo:
>
> ## 2026-10-15 — Usamos una sola planilla de precios
> Porque tener dos se desfasaba. Reemplaza lo decidido el 2026-08-02.
"""

README_PLANES = """# Planes

Acá va un plan por etapa de trabajo. Nombre del archivo: `AAAA-MM-DD-tema.md` (la fecha en que se empieza).
Ejemplo: `2026-10-15-catalogo-nuevo.md`.
Cada plan dice: qué se hace, en qué orden, cómo se sabe que terminó. Cuando la etapa termina, el plan se mueve
a `docs/planes/archivo/` (no se borra). Lo que se decidió en el camino va en `docs/decisiones.md`.
"""

CLAUDE_BASE = """# {nombre}

Reglas de trabajo.

## Dónde se guarda cada cosa
- Qué es esta caja, para quién, cuándo está terminada y qué NO se hace → `docs/PRD.md`
- Una decisión (con fecha y el porqué) → `docs/decisiones.md`
- El plan de una etapa → `docs/planes/AAAA-MM-DD-tema.md` (al terminar la etapa, se archiva)
- Si la caja tiene código: cómo está armado → `docs/arquitectura.md`; cómo se mueve la persona por la app → `docs/flujo-de-la-app.md`; pantallas (mockups) → `docs/diseno/`; esquema de datos (generado, nunca a mano) → `docs/esquema/`; dónde corre y cómo se despliega → `docs/operacion.md`
- Las claves nunca van en los documentos: van en `.env` (que no se sube a GitHub).
"""


def nombre_limpio(carpeta: Path) -> str:
    """Nombre de la carpeta para escribirlo en un documento: sin saltos de línea ni tabulaciones, y corto."""
    return re.sub(r"[\r\n\t]", " ", carpeta.name)[:100]


def crear_nuevo(carpeta: Path, rel: str, contenido: str):
    """Crea `rel` dentro de la caja, solo si no existe. Devuelve None si lo creó, o el motivo si no pudo.
    Nunca pisa ni escribe fuera de la caja (se niega si una carpeta del camino es un enlace) ni corta el recorrido."""
    destino = carpeta / rel
    try:
        padre = carpeta
        for parte in Path(rel).parent.parts:
            padre = padre / parte
            if padre.is_symlink():
                return f"{padre.relative_to(carpeta).as_posix()} es un enlace; se deja a mano"
        base = carpeta.resolve()
        if base not in destino.parent.resolve().parents and destino.parent.resolve() != base:
            return "saldría de la caja"
        destino.parent.mkdir(parents=True, exist_ok=True)
        with open(destino, "x", encoding="utf-8") as fh:  # "x": jamás pisa un archivo existente
            fh.write(contenido)
    except OSError as e:
        return f"{e.__class__.__name__}; se deja a mano"
    return None


def plan_seguro(carpeta: Path, nivel: str) -> list:
    """Lo seguro y reversible que falta: [(ruta relativa, contenido, regla)]. Nunca incluye lo que ya existe."""
    plan = []
    if not (carpeta / "CLAUDE.md").exists():
        plan.append(("CLAUDE.md", CLAUDE_BASE.format(nombre=nombre_limpio(carpeta)), "R2"))
    if not (carpeta / ".claude" / "settings.json").exists():
        plan.append((".claude/settings.json", "{}\n", "R4"))
    if not (carpeta / ".gitignore").exists():
        lineas_gi = [".env", ".claude/settings.local.json", "CLAUDE.local.md", ".claude/cerrando.json",
                     "# settings.json SÍ se sube (permisos y paquetes de la caja); esta línea le gana a un ignore global de la persona",
                     "!.claude/settings.json"]
        if nivel in ("empresa", "area"):
            lineas_gi.extend(["", "# Cajas de adentro: cada una tiene su propio repositorio",
                              "/*/", "!/.claude/", "!/plugins/", "!/docs/"])
        plan.append((".gitignore", "\n".join(lineas_gi) + "\n", "R5"))
    if (carpeta / ".env").exists() and not (carpeta / ".env.example").exists():
        cuerpo = "# Claves y variables de entorno requeridas (sin valores)\n"
        cuerpo += "".join(f"{n}=\n" for n in nombres_de_env(carpeta / ".env"))
        plan.append((".env.example", cuerpo, "R7"))
    exceptuado = False  # una excepción escrita para R12 también frena que se creen los documentos
    excepciones, _avisos, raiz_repo = cargar_excepciones(carpeta)
    if raiz_repo is not None:
        exceptuado = ("R12", ruta_en_repo(raiz_repo, carpeta)) in excepciones
    if not exceptuado and not (carpeta / "docs" / "PRD.md").exists():
        plan.append(("docs/PRD.md", PLANTILLA_PRD.format(nombre=nombre_limpio(carpeta)), "R12"))
    if not exceptuado and not (carpeta / "docs" / "decisiones.md").exists():
        plan.append(("docs/decisiones.md", PLANTILLA_DECISIONES.format(nombre=nombre_limpio(carpeta)), "R12"))
    if not exceptuado and not (carpeta / "docs" / "planes").exists():
        plan.append(("docs/planes/README.md", README_PLANES, "R12"))
    # Piezas de desarrollo (R23): solo en una caja con código propio. Son esqueletos para `arreglar --si` / `completar`
    # (la persona los pide); el bucle de orden NO los crea solos: un esqueleto vacío es un archivo más que nadie lee.
    exceptuado23 = raiz_repo is not None and ("R23", ruta_en_repo(raiz_repo, carpeta)) in excepciones
    if not exceptuado23 and hay_codigo_propio(carpeta):
        nombre = nombre_limpio(carpeta)
        for rel, plantilla in (("docs/arquitectura.md", PLANTILLA_ARQUITECTURA), ("docs/flujo-de-la-app.md", PLANTILLA_FLUJO),
                               ("README.md", PLANTILLA_README)):
            if not (carpeta / rel).exists():
                plan.append((rel, plantilla.format(nombre=nombre), "R23"))
        if not (carpeta / ARCHIVO_CLAVES_EJEMPLO).exists() and not (carpeta / ARCHIVO_CLAVES).exists():   # con claves reales ya lo cubre R7
            plan.append((ARCHIVO_CLAVES_EJEMPLO, PLANTILLA_ENV_EJEMPLO, "R23"))
        if not (carpeta / ".claude" / "rules" / "donde-va-cada-cosa.md").exists():
            plan.append((".claude/rules/donde-va-cada-cosa.md", DONDE_VA, "R23"))
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

    for rel in ("docs/PRD.md", "docs/decisiones.md", "docs/planes/README.md"):
        if rel in plan:
            motivo = crear_nuevo(carpeta, rel, plan[rel])
            print(f"+ Creado: {rel}" if motivo is None else f"! No se creó {rel}: {motivo}")
        else:
            print(f"= Ya existe: {rel.replace('/README.md', '/')}")

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
        planeados = {rel.replace("/README.md", "/") for rel, _, _ in plan}
        if not set(faltan_documentos_vivos(c_path)) <= planeados:
            cubiertas.discard("R12")  # algo falta y el plan no lo crea (ruta ocupada): queda para hacer a mano
        # lo que queda se mide ANTES de aplicar y sin lo que el plan va a resolver
        resto = [h for h in revisar_caja(c_path, c_nivel, parent_caja=parent)
                 if h[1] not in cubiertas and h[0] != "excepcion"]
        if not plan and not resto:
            continue
        print(f"== {rel} ==")
        for ruta, contenido, _r in plan:
            if aplicar:
                motivo = crear_nuevo(c_path, ruta, contenido)
                if motivo is not None:
                    pendientes += 1
                    print(f"  ! no se creó {ruta}: {motivo}")
                    continue
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

    p_remoto = subparsers.add_parser("remoto", help="Mide cuántas cajas tienen el molde completo EN GITHUB (no en la carpeta de esta computadora)")
    p_remoto.add_argument("--raiz", default=None, help="Raíz de proyectos (por defecto ~/Proyectos)")
    p_remoto.add_argument("--sin-traer", action="store_true", help="No hace git fetch: usa lo último que se trajo")

    p_brief = subparsers.add_parser("brief", help="Brief listo para una sesión secundaria con lo que vale arreglar")
    p_brief.add_argument("carpeta", nargs="?", default=None, help="Carpeta (por defecto la actual)")
    p_desc = subparsers.add_parser("descartar", help="Anota que un aviso se decidió no hacer (no vuelve a aparecer)")
    p_desc.add_argument("clave", help="La clave que muestra el aviso entre corchetes, por ejemplo R3:Mi-Carpeta")

    # Subcomandos del bucle de orden (estructura_orden.py)
    p_auto = subparsers.add_parser("auto", help="Muestra (o con --si aplica) los arreglos seguros del bucle de orden")
    p_auto.add_argument("--raiz", default=None, help="Raíz de proyectos (por defecto ~/Proyectos)")
    p_auto.add_argument("--si", action="store_true", help="Aplica el grupo 1 (un commit por arreglo, con registro)")
    p_aplicar = subparsers.add_parser("aplicar", help="Aplica un hallazgo de juicio (grupo 2) ya verificado por una segunda IA")
    p_aplicar.add_argument("id")
    p_aplicar.add_argument("--verificado-por", required=True, help="Qué IA verificó la evidencia (lista cerrada: gemini, codex, gpt, claude, opus, sonnet, haiku, pal, persona). Es una declaración, no un control")
    p_aplicar.add_argument("--raiz", default=None)
    p_deshacer = subparsers.add_parser("deshacer", help="Deshace un arreglo automático por su id")
    p_deshacer.add_argument("id")
    p_resumen = subparsers.add_parser("resumen", help="Resumen semanal de 3 líneas del bucle de orden")
    p_resumen.add_argument("--raiz", default=None)
    p_cfg = subparsers.add_parser("orden-config", help="Muestra, enciende o apaga la aplicación automática (viene encendida por defecto)")
    p_cfg.add_argument("--encender", action="store_true")
    p_cfg.add_argument("--apagar", action="store_true")

    args = parser.parse_args()

    if args.comando in ("auto", "aplicar", "deshacer", "resumen", "orden-config"):
        import estructura_orden as O
        if args.comando == "auto":
            sys.exit(O.comando_auto(raiz_arg=args.raiz, aplicar=args.si))
        if args.comando == "aplicar":
            sys.exit(O.comando_aplicar(args.id, args.verificado_por, raiz_arg=args.raiz))
        if args.comando == "deshacer":
            sys.exit(O.comando_deshacer(args.id))
        if args.comando == "resumen":
            sys.exit(O.comando_resumen(raiz_arg=args.raiz))
        sys.exit(O.comando_config(args.encender, args.apagar))

    if args.comando == "remoto":
        sys.exit(comando_remoto(args.raiz, traer=not args.sin_traer))
    if args.comando == "brief":
        sys.exit(comando_brief(args.carpeta))
    if args.comando == "descartar":
        sys.exit(comando_descartar(args.clave))
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
