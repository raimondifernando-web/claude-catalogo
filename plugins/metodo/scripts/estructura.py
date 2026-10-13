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

Subcomandos:
- dibujo [--salida RUTA] [--origen RUTA]
- revisar [CARPETA] [--todas] [--nivel empresa|area|proyecto] [--aviso] [--raiz RUTA] [--origen RUTA]
- completar CARPETA --nivel empresa|area|proyecto [--origen RUTA]
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
    """Devuelve las reglas de control R1-R11."""
    sec = extraer_seccion(md_texto, "Reglas que revisa el control")
    filas = parsear_tabla_md(sec)
    reglas = []
    for f in filas:
        reglas.append({
            "id": f.get("Id", "").strip(),
            "regla": f.get("Regla", "").strip(),
            "donde": f.get("Dónde", "").strip(),
            "si_falla": f.get("Si falla", "").strip(),
        })
    return reglas


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
        etiq = f.get("Etiqueta", "").strip()
        desc = f.get("Descripción", "").strip()
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
        desc = git_row["que_es"]
        lineas.append(f'{indent_str}<div class="file link"><span class="mono">.git/</span><span class="q">{desc}</span></div>')

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
                estilo_h = "grid-column:1/-1" if (h["modo"] == "completa" and hijos_son_hojas) else None
                lineas.append(_generar_nodo_html(h, molde, textos_nivel, es_lvl1=False, estilo_extra=estilo_h, indent=indent + "    "))
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
# 3. CONTROL Y REGLAS R1 - R11 (REVISAR)
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


def detectar_nivel_carpeta(carpeta: Path, raiz: Path = None, nivel_explicit=None) -> str:
    """Decide el nivel de la caja según jerarquía o subdirectorios."""
    if nivel_explicit:
        return nivel_explicit

    # Detectar por presencia de subdirectorios que son cajas
    carpetas_ignoradas = {".git", ".claude", ".claude-plugin", "plugins", "docs", "node_modules", "__pycache__"}
    subcajas = []
    if carpeta.is_dir():
        for sub in carpeta.iterdir():
            if sub.is_dir() and sub.name not in carpetas_ignoradas and not sub.name.startswith("."):
                subcajas.append(sub)

    if subcajas:
        # ¿Tienen sus hijas cajas adentro?
        hijas_tienen_cajas = False
        for sc in subcajas:
            for ssc in sc.iterdir():
                if ssc.is_dir() and ssc.name not in carpetas_ignoradas and not ssc.name.startswith("."):
                    hijas_tienen_cajas = True
                    break
            if hijas_tienen_cajas:
                break
        if hijas_tienen_cajas:
            return "empresa"
        return "area"

    # Si estamos dentro de una raíz y no tiene subcajas
    return "proyecto"


def revisar_caja(carpeta: Path, nivel: str, parent_caja: Path = None) -> list:
    """Aplica las reglas R1-R10 a una caja concreta. Retorna [(tipo, id, mensaje)]."""
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

    # R8: El repositorio no guarda las cajas de adentro (empresa y área)
    if nivel in ("empresa", "area"):
        # 1. Si git versiona archivos en carpetas de proyectos o hijas
        if git_dir.exists():
            code, out = ejecutar_git("ls-files", cwd=carpeta)
            if code == 0 and out:
                carpetas_permitidas = {".claude", ".claude-plugin", "plugins", "docs", ".git"}
                for linea_f in out.splitlines():
                    partes = linea_f.strip().split("/")
                    if len(partes) > 1 and partes[0] not in carpetas_permitidas:
                        sub_nombre = partes[0]
                        hallazgos.append(("error", "R8", f"versiona la carpeta de adentro '{sub_nombre}' (debe ser un repositorio independiente)"))
                        break

        # 2. .gitignore debe tener un patrón para ignorar carpetas hijas
        if gitignore.is_file():
            gi_texto = gitignore.read_text(encoding="utf-8", errors="replace")
            # Buscar patrones genéricos de ignorar carpetas
            tiene_patron = any(p in gi_texto for p in ("/*/", "/*", "*", "!/"))
            if not tiene_patron:
                hallazgos.append(("error", "R8", ".gitignore no tiene patrón para ignorar las carpetas de adentro"))

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

    return hallazgos


def revisar_raiz(raiz: Path) -> list:
    """Aplica la regla R11 a la raíz de proyectos."""
    hallazgos = []
    if (raiz / ".git").exists():
        hallazgos.append(("error", "R11", "~/Proyectos/ no debe ser un repositorio git"))
    return hallazgos


def descubrir_cajas(raiz: Path):
    """Descubre recursivamente las cajas de trabajo bajo la raíz."""
    carpetas_ignoradas = {".git", ".claude", ".claude-plugin", "plugins", "docs", "node_modules", "__pycache__"}
    cajas = []

    def recorrer(carpeta: Path, parent: Path = None):
        if not carpeta.is_dir():
            return
        # Es caja si tiene .git, CLAUDE.md, .claude o si es subdirectorio válido de nivel 1..3
        subdirs = [d for d in carpeta.iterdir() if d.is_dir() and d.name not in carpetas_ignoradas and not d.name.startswith(".")]

        # Si no es la raíz, evaluamos si es caja
        if carpeta != raiz:
            nivel = detectar_nivel_carpeta(carpeta, raiz)
            cajas.append((carpeta, nivel, parent))
            for sub in subdirs:
                recorrer(sub, parent=carpeta)
        else:
            for sub in subdirs:
                recorrer(sub, parent=None)

    recorrer(raiz)
    return cajas


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
                estado_dir.mkdir(parents=True, exist_ok=True)
                estado_file.write_text(semana_actual, encoding="utf-8")
                todas = True
        except Exception:
            pass

    lineas_salida = []
    total_errores = 0

    if todas:
        # Revisar R11 en la raíz
        for tipo, r_id, msg in revisar_raiz(raiz):
            total_errores += 1
            lineas_salida.append(f"✗ {r_id} {raiz.name}: {msg}")

        # Recorrer cajas
        cajas = descubrir_cajas(raiz)
        for c_path, c_nivel, parent in cajas:
            rel_display = str(c_path.relative_to(raiz))
            hallazgos = revisar_caja(c_path, c_nivel, parent_caja=parent)
            for tipo, r_id, msg in hallazgos:
                if tipo == "error":
                    total_errores += 1
                    lineas_salida.append(f"✗ {r_id} {rel_display}: {msg}")
                else:
                    lineas_salida.append(f"• {r_id} {rel_display}: {msg}")
    else:
        objetivo = Path(carpeta_arg).resolve() if carpeta_arg else Path.cwd()
        # Si se apunta a la raíz directamente
        if objetivo == raiz or (raiz_arg and objetivo == Path(raiz_arg).resolve()):
            for tipo, r_id, msg in revisar_raiz(objetivo):
                total_errores += 1
                lineas_salida.append(f"✗ {r_id} {objetivo.name}: {msg}")
        else:
            nivel = detectar_nivel_carpeta(objetivo, raiz, nivel_explicit=nivel_arg)
            parent = objetivo.parent if objetivo.parent != raiz and (objetivo.parent / "CLAUDE.md").exists() else None
            hallazgos = revisar_caja(objetivo, nivel, parent_caja=parent)
            display_name = objetivo.name
            for tipo, r_id, msg in hallazgos:
                if tipo == "error":
                    total_errores += 1
                    lineas_salida.append(f"✗ {r_id} {display_name}: {msg}")
                else:
                    lineas_salida.append(f"• {r_id} {display_name}: {msg}")

    # En modo aviso: si todo está bien, no imprime nada y sale 0. Si hay fallas, imprime y sale 0.
    if aviso:
        if lineas_salida:
            for l in lineas_salida:
                print(l)
            palabra = "cosa" if total_errores == 1 else "cosas"
            print(f"Falta: {total_errores} {palabra} ✗")
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

def comando_completar(carpeta_arg: str, nivel: str, origen_arg=None) -> int:
    """Crea los archivos obligatorios según el molde sin pisar nada existente."""
    carpeta = Path(carpeta_arg).resolve()
    carpeta.mkdir(parents=True, exist_ok=True)

    # 1. CLAUDE.md
    claude_md = carpeta / "CLAUDE.md"
    if claude_md.exists():
        print("= Ya existe: CLAUDE.md")
    else:
        claude_md.write_text(f"# {carpeta.name}\n\nReglas de trabajo.\n", encoding="utf-8")
        print("+ Creado: CLAUDE.md")

    # 2. .claude/settings.json = {}
    settings_dir = carpeta / ".claude"
    settings_dir.mkdir(parents=True, exist_ok=True)
    settings_json = settings_dir / "settings.json"
    if settings_json.exists():
        print("= Ya existe: .claude/settings.json")
    else:
        settings_json.write_text("{}\n", encoding="utf-8")
        print("+ Creado: .claude/settings.json")

    # 3. .gitignore
    gitignore = carpeta / ".gitignore"
    if gitignore.exists():
        print("= Ya existe: .gitignore")
    else:
        lineas_gi = [
            ".env",
            ".claude/settings.local.json",
            "CLAUDE.local.md",
        ]
        if nivel in ("empresa", "area"):
            lineas_gi.extend([
                "",
                "# Cajas de adentro: cada una tiene su propio repositorio",
                "/*/",
                "!/.claude/",
                "!/plugins/",
                "!/docs/",
            ])
        gitignore.write_text("\n".join(lineas_gi) + "\n", encoding="utf-8")
        print("+ Creado: .gitignore")

    # 4. .env.example si hay .env
    env_file = carpeta / ".env"
    env_example = carpeta / ".env.example"
    if env_file.exists():
        if env_example.exists():
            print("= Ya existe: .env.example")
        else:
            env_example.write_text("# Claves y variables de entorno requeridas (sin valores)\n", encoding="utf-8")
            print("+ Creado: .env.example")

    # 5. Git y remoto (informa como pendiente)
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
    p_revisar = subparsers.add_parser("revisar", help="Revisa el cumplimiento de las reglas R1-R11")
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
    elif args.comando == "completar":
        sys.exit(comando_completar(
            carpeta_arg=args.carpeta,
            nivel=args.nivel,
            origen_arg=args.origen,
        ))


if __name__ == "__main__":
    main()
