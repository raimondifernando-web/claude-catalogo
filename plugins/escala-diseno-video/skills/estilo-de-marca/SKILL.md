---
name: estilo-de-marca
description: |
  Le da a una web, landing, app o componente el estilo visual de una marca conocida (Stripe, Apple,
  Notion, Linear, Nike, Airbnb y ~70 más). Trae el DESIGN.md de esa marca, que describe colores,
  tipografía, componentes, espaciado, sombras y reglas, y construye la interfaz siguiéndolo.
  Automatiza el método oficial de la colección Awesome Design (VoltAgent/awesome-design-md).
  Usala siempre que el usuario diga "el estilo de X", "que se vea como X", "diseño tipo X",
  "inspirado en X", "con la onda de X", "awesome design", "DESIGN.md", "un sistema de diseño de una
  marca", o cuando pida una interfaz linda y nombre una empresa como referencia visual, aunque no
  diga "estilo".
origen: github:VoltAgent/awesome-design-md@f6961238d5cddcf8042a74a70fc400ec67181abb
license: MIT (la colección); esta skill es propia
sync: cowork
---

# Estilo de marca

**Fuente fija:** `VoltAgent/awesome-design-md` @ `SHA=f6961238d5cddcf8042a74a70fc400ec67181abb`.
Es la única constante que cambia cuando el vigía avisa que el repo avanzó. Se usa ese sha y no `main`
porque el contenido quedó auditado en ese commit: si alguien cambia el repo, a esta skill no le llega
hasta que se revise.

## Qué es un DESIGN.md
Es un archivo de texto con el sistema visual de un sitio, en 9 secciones:
1. clima visual;
2. paleta con roles;
3. tipografía;
4. componentes y sus estados;
5. espaciado y grilla;
6. sombras y profundidad;
7. qué hacer y qué no;
8. comportamiento responsive;
9. guía de prompts.

El método oficial de la colección es copiarlo a la raíz del proyecto y pedirle al agente que lo use.
Esta skill hace esos dos pasos por vos.

## Pasos

### 1. Elegir la marca
El nombre de la carpeta es la marca en minúsculas, a veces con dominio: `stripe`, `apple`, `linear.app`,
`mistral.ai`, `x.ai`, `bmw-m`. Para ver cuáles hay:

```bash
gh api "repos/VoltAgent/awesome-design-md/contents/design-md?ref=$SHA" --jq '.[].name'
```

- Si la marca pedida no está o el usuario no nombró ninguna, proponé 3 que se parezcan por rubro o por
  clima visual. Por ejemplo: fintech → `stripe`, `revolut`, `wise`; herramienta minimalista →
  `linear.app`, `notion`, `vercel`; lujo/auto → `ferrari`, `lamborghini`, `bmw`; consumo masivo →
  `nike`, `spotify`, `airbnb`.
- Decí en una línea por qué elegiste cada una. Con la elección del usuario, seguí.

### 2. Traer el archivo a la raíz del proyecto
- Si ya hay un `DESIGN.md` en la raíz, **preguntá antes de reemplazarlo**: puede ser el sistema de diseño
  propio del proyecto, y pisarlo borra trabajo. La alternativa es guardarlo como `DESIGN-<marca>.md`.

```bash
curl -fsSL "https://raw.githubusercontent.com/VoltAgent/awesome-design-md/$SHA/design-md/<marca>/DESIGN.md" -o DESIGN.md
```

- Verificá que haya bajado bien: tiene que empezar con `---` y tener la sección de colores. Si `curl`
  falla, la marca no existe en ese commit: volvé al paso 1.

### 3. Construir con él
- Leé el DESIGN.md completo antes de escribir código.
- Tomá los valores exactos: hex, familias tipográficas, escala de tamaños, radios, sombras.
- Respetá la sección «qué hacer y qué no» como restricción, no como sugerencia.
- Si el proyecto ya tiene componentes, adaptalos al DESIGN.md en vez de reescribirlos.
- **Dos estilos mezclados** («la tipografía de Apple con los colores de Stripe»): se puede. Bajá los dos
  como `DESIGN-<marca>.md` y escribí arriba de todo, en el DESIGN.md final, qué marca manda en cada una
  de las 9 secciones, así no queda ambiguo.

### 4. Aviso de marca (siempre, en una línea)
Estos archivos son análisis *inspirados* en cada marca, no su sistema oficial. Sirven como dirección
visual: paleta, ritmo, tipografía, sensación.

**No copies** logos, nombres, marcas registradas, ilustraciones ni fotos propias de la marca. Si el sitio
es de un cliente, que tampoco quede una imitación reconocible de otra empresa: parecerse demasiado a una
marca ajena («trade dress») puede traer un reclamo legal y además le quita identidad al cliente. Cuando
el usuario pide «que se vea igual a X», proponé que se vea *de la familia de X* con la identidad propia
del cliente arriba.

## Cuando el vigía avise que el repo avanzó
Cambiá el `SHA` de arriba y el `origen:` del frontmatter por el commit nuevo, después de revisar el diff:

```bash
gh api "repos/VoltAgent/awesome-design-md/compare/<sha-viejo>...<sha-nuevo>" --jq '.files[].filename'
```

Como es solo texto, alcanza con leer lo que cambió.
