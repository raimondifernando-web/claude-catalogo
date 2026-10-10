import { expect, mock, test } from 'claude-code/testing'
import type { On } from 'claude-code'

import { PLANTILLA } from './plantilla'
import { EJEMPLO } from './ejemplo'

// 10/10 a las 12:30 en Argentina (UTC-3).
const AHORA = Date.parse('2026-10-10T15:30:00Z')
const CARPETA = '/casa/Proyectos/Tienda'
const RUTA = `${CARPETA}/.claude/PENDIENTES.md`

// La versión anterior en git: la lista sin E10 y con B14 en prio 2 y S1 sin esperar a Ana.
const ANTERIOR = EJEMPLO.replace(/^\| E10 \|.*\n/m, '')
  .replace(/^(\| B14 \|.*?\| )1( \| pendiente \|)/m, '$12$2')
  .replace(/^(\| S1 \|.*?\| 1 \| )espera dato de Ana( \|)/m, '$1pendiente$2')

type Mundo = { texto?: string; sucio?: boolean; versiones?: string[]; antes?: string; fallaGit?: boolean; carpeta?: string; sinGit?: boolean }

function salida(stdout: string, exitCode = 0, stderr = '') {
  return { value: { exitCode, stdout, stderr, isStdoutTruncated: false, isStderrTruncated: false } } as never
}

// El mundo de abajo: reloj fijo, archivo y git de mentira, un panel vacío de base.
function fondo(on: On, mundo: Mundo) {
  mock.clock(on, { now: AHORA })
  mock.env(on, { HOME: '/casa' })
  on('session.root', () => ({ value: mundo.carpeta ?? CARPETA }) as never)
  on('ui.render', ($, e) => {
    const { Box } = $.ui.resolve(e)
    return h(Box, {})
  })
  on('session.measure', (_$, e) => ({ changed: e.changed }))
  on('prompt.submit', (_$, e) => ({ text: e.text }))
  // Sin texto, la lectura sigue al archivo de verdad, que en /casa no existe.
  on('fs.read', (_$, e, next) => (e.path === RUTA && mundo.texto !== undefined ? ({ value: mundo.texto } as never) : next(e)))
  on('process.run', (_$, e) => {
    const [, , , , cmd, ...resto] = e.argv
    if (cmd === 'rev-parse') return salida(`${(mundo.carpeta ?? CARPETA).startsWith(CARPETA) ? CARPETA : mundo.carpeta}\n`)
    if (mundo.sinGit) return salida('', 128, 'fatal: not a git repository')
    if (mundo.fallaGit) return salida('', 128, 'fatal: index file corrupt')
    if (cmd === 'status') return salida(mundo.sucio ? ' M .claude/PENDIENTES.md\n' : '')
    if (cmd === 'log') return salida((mundo.versiones ?? ['aaa 2026-10-10', 'bbb 2026-10-09']).join('\n') + '\n')
    if (cmd === 'show' && resto[0]?.startsWith('bbb:')) return salida(mundo.antes ?? ANTERIOR)
    if (cmd === 'show') return salida(mundo.antes ?? ANTERIOR)
    return salida('', 1, 'comando inesperado')
  })
}

const PANEL = {
  component: 'Pane' as const,
  requestId: 'pendientes',
  props: {
    title: 'Pendientes',
    isFocused: false,
    bodyColumns: 38,
    placement: 'dock' as const,
    scroll: { offset: 0, bodyRows: 40 },
    view: {},
  },
}

async function abrir($: Parameters<Parameters<typeof test>[1]>[0], surface: 'terminal' | 'desktop' = 'desktop') {
  await $.session.measure({ context: { window: 1_000_000 }, rateLimits: [], changed: ['context'] })
  return $.ui.mount({ plugin: 'paneles', surface, ...PANEL })
}

test('lee un archivo con el formato verdadero: Ahora, Esta semana, Cambios y Próxima fecha', async ($, on) => {
  fondo(on, { texto: EJEMPLO })
  for (const surface of ['terminal', 'desktop'] as const) {
    const ui = await abrir($, surface)
    // Ahora: las filas de prio 1, con lo que espera una respuesta destacado.
    expect(await ui.find({ type: 'Text', text: /^Ahora$/ })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: /Hay 2 esperando un dato o un OK/ })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: /espera dato de Ana/ })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: /espera OK de Ana/ })).toBeDefined()
    expect(await ui.find({ type: 'Button', text: /Armar el respaldo del equipo/ })).toBeDefined()
    expect(await ui.find({ type: 'Button', text: /Lista de tareas visible en pantalla/ })).toBeDefined()
    // Esta semana, agrupado por sección.
    expect(await ui.find({ type: 'Text', text: /^Esta semana$/ })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: /^Seguridad y respaldo$/ })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: /^Orden interno/ })).toBeDefined()
    // Cambios: sale de comparar contra la versión anterior en git.
    expect(await ui.find({ type: 'Text', text: /Contra la versión anterior \(9\/10\)/ })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: /Nuevo · prio 2/ })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: /Cambió de prioridad · prio 2 → 1/ })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: /Cambió de estado · pendiente → espera dato de Ana/ })).toBeDefined()
    // Próxima fecha: la primera de la tabla que todavía no pasó (10/10 15:00).
    expect(await ui.find({ type: 'Text', text: /^hoy 15:00$/ })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: /Hacer la copia semanal/ })).toBeDefined()
    await ui.unmount()
  }
})

test('prio 3: solo el conteo, y un clic lo despliega', async ($, on) => {
  fondo(on, { texto: EJEMPLO })
  const ui = await abrir($)
  const antes = await ui.find({ type: 'Button', text: /Después · \d+/ })
  expect(antes).toBeDefined()
  expect(await ui.find({ type: 'Button', text: /Terminar las vistas del tablero/ })).toBeUndefined()
  await ui.press({ key: 'despues' })
  expect(await ui.find({ type: 'Button', text: /Terminar las vistas del tablero/ })).toBeDefined()
  expect(await ui.find({ type: 'Text', text: /Prio 3 · espera cupo o una decisión/ })).toBeDefined()
  await ui.unmount()
})

for (const surface of ['terminal', 'desktop'] as const) {
  test(`tocar un título muestra el detalle: de qué depende, qué desbloquea, esfuerzo y quién (${surface})`, async ($, on) => {
    fondo(on, { texto: EJEMPLO })
    const ui = await abrir($, surface)
    expect(await ui.find({ type: 'Text', text: /^Prio 1 · lo que va primero$/ })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: /^Desbloquea:/ })).toBeUndefined()
    await ui.press({ key: 'fila-B1' })
    // B1 (el plan de la tienda) no depende de nada y desbloquea a las filas que lo nombran en «Depende de».
    expect(await ui.find({ type: 'Text', text: /Plan de la tienda: catálogo, pagos y envíos/ })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: /Depende de: nada, se puede hacer ya/ })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: /Desbloquea: B3, B4, B5/ })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: /Esfuerzo: grande/ })).toBeDefined()
    // S1 espera un dato: lo aclara en criollo.
    await ui.press({ key: 'fila-S1' })
    expect(await ui.find({ type: 'Text', text: /Necesita un dato para avanzar/ })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: /Depende de: dato de Ana: espacio libre en el disco/ })).toBeDefined()
    // Otro toque lo cierra.
    await ui.press({ key: 'fila-B1' })
    expect(await ui.find({ type: 'Text', text: /Esfuerzo: grande/ })).toBeUndefined()
    await ui.unmount()
  })
}

test('con cambios sin guardar compara contra la última versión guardada', async ($, on) => {
  fondo(on, { texto: EJEMPLO, sucio: true, versiones: ['aaa 2026-10-10'] })
  const ui = await abrir($)
  expect(await ui.find({ type: 'Text', text: /Contra la última versión guardada \(10\/10\)/ })).toBeDefined()
  await ui.unmount()
})

test('sin versión anterior en git lo dice', async ($, on) => {
  fondo(on, { texto: EJEMPLO, versiones: ['aaa 2026-10-10'] })
  const ui = await abrir($)
  expect(await ui.find({ type: 'Text', text: /Todavía no hay una versión anterior en git/ })).toBeDefined()
  await ui.unmount()
})

test('carpeta sin git: Cambios dice que no hay versión anterior, sin error', async ($, on) => {
  fondo(on, { texto: EJEMPLO, sinGit: true })
  const ui = await abrir($)
  expect(await ui.find({ type: 'Text', text: /Todavía no hay una versión anterior en git/ })).toBeDefined()
  expect(await ui.find({ type: 'Text', text: /No pude leer el historial/ })).toBeUndefined()
  await ui.unmount()
})

test('si git falla, avisa en lugar de dejar Cambios vacío', async ($, on) => {
  fondo(on, { texto: EJEMPLO, fallaGit: true })
  const ui = await abrir($)
  expect(await ui.find({ type: 'Text', text: /No pude leer el historial de git, así que no se ven los Cambios/ })).toBeDefined()
  // Lo demás se sigue viendo.
  expect(await ui.find({ type: 'Button', text: /Armar el respaldo del equipo/ })).toBeDefined()
  await ui.unmount()
})

test('carpeta sin lista: mensaje en criollo, no un error técnico', async ($, on) => {
  fondo(on, { texto: EJEMPLO, carpeta: '/casa/Proyectos/Otro' })
  const ui = await abrir($)
  expect(await ui.find({ type: 'Text', text: /^Esta carpeta no tiene lista de pendientes todavía\.$/ })).toBeDefined()
  expect(await ui.find({ type: 'Text', text: /^No pude leer/ })).toBeUndefined()
  expect(await ui.find({ type: 'Text', text: /^Ahora$/ })).toBeUndefined()
  await ui.unmount()
})

test('desde una subcarpeta del repo encuentra la lista de la raíz', async ($, on) => {
  fondo(on, { texto: EJEMPLO, carpeta: `${CARPETA}/sub` })
  const ui = await abrir($)
  expect(await ui.find({ type: 'Text', text: /^Ahora$/ })).toBeDefined()
  await ui.unmount()
})

test('lista con un estado inválido: avisa el problema, sigue mostrando el resto', async ($, on) => {
  fondo(on, { texto: EJEMPLO.replace(/^(\| S2 \|.*?\| 1 \| )pendiente( \|)/m, '$1inventado$2') })
  const ui = await abrir($)
  expect(await ui.find({ type: 'Text', text: /S2: el estado «inventado» no es uno de los conocidos/ })).toBeDefined()
  expect(await ui.find({ type: 'Button', text: /Armar el respaldo del equipo/ })).toBeDefined()
  await ui.unmount()
})

test('sin ninguna lista en la carpeta ni en su repo: lo dice en criollo', async ($, on) => {
  fondo(on, {})
  const ui = await abrir($)
  expect(await ui.find({ type: 'Text', text: /^Esta carpeta no tiene lista de pendientes todavía\.$/ })).toBeDefined()
  expect(await ui.find({ type: 'Text', text: /^Ahora$/ })).toBeUndefined()
  await ui.unmount()
})

test('archivo sin ninguna tabla: lo dice, no muestra vacío', async ($, on) => {
  fondo(on, { texto: '# PENDIENTES\n\nSolo texto.\n' })
  const ui = await abrir($)
  expect(await ui.find({ type: 'Text', text: /No pude leer PENDIENTES\.md: No encontré ninguna fila/ })).toBeDefined()
  await ui.unmount()
})

test('una fila mal formada se avisa y el resto se sigue mostrando', async ($, on) => {
  const roto = EJEMPLO.replace(/^\| S3 \|.*$/m, '| S3 | Falta una columna | 2 | pendiente |')
    .replace(/^\| S4 \|(.*)\| 3 \| pendiente \|/m, '| S4 |$1| 7 | pendiente |')
  fondo(on, { texto: roto })
  const ui = await abrir($)
  expect(await ui.find({ type: 'Text', text: /No pude leer bien PENDIENTES\.md \(2 problemas\)/ })).toBeDefined()
  expect(await ui.find({ type: 'Text', text: /S3: tiene 4 columnas y tiene que tener 8/ })).toBeDefined()
  expect(await ui.find({ type: 'Text', text: /S4: la prioridad «7» no es 1, 2 ni 3/ })).toBeDefined()
  expect(await ui.find({ type: 'Button', text: /Armar el respaldo del equipo/ })).toBeDefined()
  await ui.unmount()
})

test('una tabla con otras columnas se avisa', async ($, on) => {
  const roto = EJEMPLO.replace('| ID | Pendiente | Prio | Estado | Depende de | Esf. | Quién | Origen |', '| ID | Pendiente | Prio |')
  fondo(on, { texto: roto })
  const ui = await abrir($)
  expect(await ui.find({ type: 'Text', text: /Sección [SBE]: la tabla no tiene las columnas/ })).toBeDefined()
  await ui.unmount()
})

test('sin tabla de fechas lo avisa', async ($, on) => {
  fondo(on, { texto: EJEMPLO.replace('## Fechas', '## Calendario') })
  const ui = await abrir($)
  expect(await ui.find({ type: 'Text', text: /No encontré la tabla «Fechas»/ })).toBeDefined()
  await ui.unmount()
})

test('la plantilla de PENDIENTES.md se lee sin problemas', async ($, on) => {
  fondo(on, { texto: PLANTILLA })
  const ui = await abrir($)
  expect(await ui.find({ type: 'Text', text: /^Ahora$/ })).toBeDefined()
  expect(await ui.find({ type: 'Text', text: /^No pude leer/ })).toBeUndefined()
  expect(await ui.find({ type: 'Text', text: /^hoy|^el \d|2099/ })).toBeDefined()
  await ui.unmount()
})

test('antigüedad: hoy se ve normal; más de 7 días avisa «puede estar vieja»', async ($, on) => {
  fondo(on, { texto: EJEMPLO })
  let ui = await abrir($)
  expect(await ui.find({ type: 'Text', text: /^Actualizada hoy/ })).toBeDefined()
  await ui.unmount()
})

test('lista vieja: «Actualizada hace 20 días · puede estar vieja»', async ($, on) => {
  const vieja = EJEMPLO.replace(/^(- )2026-10-\d{2}/gm, '$12026-09-20')
  fondo(on, { texto: vieja })
  const ui = await abrir($)
  expect(await ui.find({ type: 'Text', text: /Actualizada hace 20 días · puede estar vieja/ })).toBeDefined()
  await ui.unmount()
})

test('sin línea fechada en Cambios: lo avisa en criollo', async ($, on) => {
  fondo(on, { texto: EJEMPLO.replace(/^- 2026-\d{2}-\d{2}/gm, '- (sin fecha)') })
  const ui = await abrir($)
  expect(await ui.find({ type: 'Text', text: /No encuentro la fecha de la última actualización/ })).toBeDefined()
  await ui.unmount()
})

test('dos sesiones crearon el mismo ID: el panel dice cuál y qué hacer', async ($, on) => {
  const repetido = EJEMPLO.replace(/^(\| S3 \|)/m, '| S2 | Fila duplicada por otra sesión | 2 | pendiente | — | chico | C | otra sesión |\n$1')
  fondo(on, { texto: repetido })
  const ui = await abrir($)
  expect(await ui.find({ type: 'Text', text: /S2: el mismo número está en dos filas/ })).toBeDefined()
  expect(await ui.find({ type: 'Button', text: /Armar el respaldo del equipo/ })).toBeDefined()
  await ui.unmount()
})

test('marcas de conflicto de git: el panel lo dice en criollo', async ($, on) => {
  fondo(on, { texto: '<<<<<<< HEAD\n' + EJEMPLO + '\n=======\n>>>>>>> otra\n' })
  const ui = await abrir($)
  expect(await ui.find({ type: 'Text', text: /marcas de conflicto de git \(línea 1\): dos sesiones editaron lo mismo/ })).toBeDefined()
  await ui.unmount()
})

test('«espera dato de» o «espera OK de» con cualquier nombre se acepta y se destaca', async ($, on) => {
  fondo(on, { texto: EJEMPLO.replace(/^(\| S2 \|.*?\| 1 \| )pendiente( \|)/m, '$1espera OK de Marcos$2') })
  const ui = await abrir($)
  expect(await ui.find({ type: 'Text', text: /Hay 3 esperando un dato o un OK/ })).toBeDefined()
  expect(await ui.find({ type: 'Text', text: /No pude leer bien/ })).toBeUndefined()
  await ui.unmount()
})
