# Conectar Claude a tu programa de CAD / BIM / 3D — qué existe y con qué cuidado

> Para estudios que ya usan Revit, Archicad, AutoCAD, Rhino, SketchUp, FreeCAD, Blender o QGIS.
> Nada de esto se instala con el catálogo: son **conectores** (servidores MCP) que se activan **uno por vez, cuando tu
> consultor lo indique**, después de responder una pregunta: **¿qué programa usás y con qué licencia?** Eso decide cuál
> se activa. Verificado en GitHub el 2026-09-21; los números cambian, la regla no.

## Las 3 reglas antes de conectar cualquier CAD
1. **El conector no reemplaza la licencia.** Todos requieren el programa instalado y con licencia vigente en tu computadora.
2. **Probar en un archivo de prueba, nunca en un proyecto real.** Estos conectores dejan que Claude **cree, modifique y borre elementos** dentro del programa. Copiá un proyecto viejo, probá ahí, mirá qué hace.
3. **Oficial gana a comunitario.** Si el fabricante publica su propio conector (Autodesk lo hizo para Revit 2027), se usa ese aunque el de la comunidad tenga más estrellas.

## Tabla por programa
| Programa | Conector recomendado | Estado (2026-09-21) | Qué pide | Aviso |
|---|---|---|---|---|
| **Revit 2027** | **Autodesk Revit MCP Server** (oficial, tech preview) — se descarga desde tu cuenta de Autodesk, con la licencia de Revit 2027 | Oficial · Windows | Revit 2027 con licencia | Es vista previa técnica: puede cambiar sin aviso. Preferirlo igual al comunitario |
| **Revit 2020-2026** | `mcp-servers-for-revit/mcp-servers-for-revit` (MIT, 339★) | Comunitario · activo (el repo original `revit-mcp` de 461★ está **archivado**, no usarlo) | Revit con licencia, Windows, instalar add-in | Sin garantía de soporte; probar en archivo de prueba |
| **Archicad** | `SzamosiMate/tapir-archicad-MCP` (MIT, 105★) | Comunitario · **alfa** · activo | Archicad con licencia + add-on Tapir (Mac/Windows) | Muy nuevo; solo si el estudio quiere experimentar |
| **AutoCAD** | `daobataotie/CAD-MCP` (MIT, 562★) | Comunitario · activo | AutoCAD con licencia, Windows | Ejecuta código LISP dentro de AutoCAD: doble cuidado con la regla 2 |
| **Planos DXF sin AutoCAD** | librería `ezdxf` (MIT, 1,4k★) — la usa una skill del catálogo cuando esté lista (`planos-dxf`) | Librería Python · madura | Python 3 + `python3 -m pip install --user ezdxf` | Todo corre en tu computadora; nada sale. Es la opción más segura para leer/medir planos |
| **Rhino / Grasshopper** | `jingcheng-chen/rhinomcp` (MIT, 1,1k★) | Comunitario · activo | Rhino 8 con licencia + plugin | — |
| **FreeCAD** (gratis) | `neka-nat/freecad-mcp` (MIT, 2,4k★, auditoría externa) | Comunitario · activo | FreeCAD + add-on | Alternativa sin licencia paga para CAD 3D |
| **Blender** (gratis; maquetas, masa, asoleamiento) | `ahujasid/mcp-for-blender` (MIT, 29k★; antes `blender-mcp`) | Comunitario · el más usado del mundo | Blender + add-on | Render final: seguí usando el motor de tu plugin; para imágenes de concepto, `generate-image` |
| **QGIS** (gratis; mapas, catastro) | `nkarasiak/qgis-mcp` (GPL-2, 314★) | Comunitario · activo | QGIS + plugin | Licencia GPL: se instala desde su repo, **el catálogo no lo redistribuye**. Ejecuta código dentro de QGIS |
| **IFC / BIM abierto** | `IfcOpenShell` + Bonsai (LGPL/GPL, 2,8k★) | Librería madura | Gratis, se instala en tu computadora | El catálogo no lo redistribuye (licencia); lo instalás vos. Útil si tu CAD exporta IFC |
| **Speckle** (intercambio entre programas) | `specklesystems/speckle-server` | Apache-2.0 (salvo 2 módulos "Enterprise Edition": `workspaces` y `gatekeeper`) · muy activo | Cuenta Speckle (gratis) + token personal | El token es una clave: la cargás vos, nunca se pega en el chat |
| **Mapas y geocodificación** | `mapbox/mcp-server` (**oficial** de Mapbox, MIT) | Oficial | Cuenta Mapbox (gratis hasta cierto uso) + token | Las direcciones y coordenadas que consultes salen hacia Mapbox |

## Lo que NO recomendamos hoy
- **SketchUp:** el conector más popular ejecuta código Ruby arbitrario y **no tiene licencia** publicada. No hay opción segura todavía.
- **Autodesk APS MCP** (el genérico de Autodesk Platform Services): archivado por Autodesk. Usar el de Revit 2027 en su lugar.
- **Render en tiempo real** (Enscape, Twinmotion, Lumion, D5, V-Ray): no existe conector. Seguí con el plugin del motor.
- **Cómputo métrico automático, catastro por API, normativa por API:** no existe. Para normativa, la skill `normativa-argentina` trabaja sobre los PDFs oficiales que vos tengas.

## Cómo se activa uno (cuando llegue el momento)
1. Tu consultor confirma qué programa y qué versión tenés, y que la licencia está vigente.
2. Se prueba primero en **una computadora, un archivo de prueba, un solo conector**.
3. Los que ejecutan código dentro del programa (AutoCAD, QGIS, Revit comunitario) se instalan con la regla del filtro de `docs/RECURSOS.md` (pregunta 5 pesa doble) y pasan por `skill-security-auditor` si traen scripts.
4. Recién después se documenta en tu `CLAUDE.md` qué conector está activo y para qué.

## Para el consultor
- Fuentes: `mcp-servers-for-revit` push 2026-04-05 (más lento que el resto; la variante `mcp-server-for-revit-python`, 193★, push 2026-09-19, es la más activa de esa organización) · Autodesk Revit Public MCP Server anunciado 2026-06-17 (blog AEC de Autodesk) · resto verificado por API de GitHub el 2026-09-21.
- Directorios (glama.ai, smithery, PulseMCP, mcp.so): sus APIs públicas no respondieron en la verificación; la búsqueda web confirma los mismos líderes. Revisar de nuevo antes del primer cliente que instale CAD.
- Cuando exista la primera skill de CAD (`planos-dxf` con `ezdxf`), estos conectores pasan a un paquete propio (`rubro-cad-bim`). Hasta entonces, este documento es la fuente.
