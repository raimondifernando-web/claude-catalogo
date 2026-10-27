import { expect, mock, test } from 'claude-code/testing'
import type { On } from 'claude-code'

import { PLANTILLA } from './plantilla'
import { EJEMPLO } from './ejemplo'

// 10/10 a las 12:30 en Argentina (UTC-3).
const AHORA = Date.parse('2026-10-10T15:30:00Z')
const CARPETA = '/casa/Proyectos/Tienda'
const RUTA = `${CARPETA}/.claude/PENDIENTES.md`

// La versión anterior en git: la lista sin E10 y con B14 en prio 2 y S1 sin esperar a F.
const ANTERIOR = EJEMPLO.replace(/^\| E10 \|.*\n/m, '')
  .replace(/^(\| B14 \|.*?\| )1( \| pendiente \|)/m, '$12$2')
  .replace(/^(\| S1 \|.*?\| 1 \| )espera dato de F( \|)/m, '$1pendiente$2')

type Mundo = { llamadas?: string[][]; raiz?: string; tareas?: string; texto?: string; sucio?: boolean; versiones?: string[]; antes?: string; fallaGit?: boolean; carpeta?: string; sinGit?: boolean }

function salida(stdout: string, exitCode = 0, stderr = '') {
  return { value: { exitCode, stdout, stderr, isStdoutTruncated: false, isStderrTruncated: false } } as never
}

// El mundo de abajo: reloj fijo, archivo y git de mentira, un panel vacío de base.
function fondo(on: On, mundo: Mundo) {
  const reloj = mock.clock(on, { now: AHORA })
  mock.env(on, { HOME: '/casa' })
  on('session.root', () => ({ value: mundo.carpeta ?? CARPETA }) as never)
  on('ui.render', ($, e) => {
    const { Box } = $.ui.resolve(e)
    return h(Box, {})
  })
  on('session.measure', (_$, e) => ({ changed: e.changed }))
  on('prompt.submit', (_$, e) => ({ text: e.text }))
  // Sin texto, la lectura sigue al archivo de verdad, que en /casa no existe.
  on('fs.read', (_$, e, next) => {
    if (e.path === RUTA && mundo.texto !== undefined) return { value: mundo.texto } as never
    if (e.path === `${CARPETA}/.claude/tareas.json` && mundo.tareas !== undefined) return { value: mundo.tareas } as never
    return next(e)
  })
  on('process.run', (_$, e) => {
    mundo.llamadas?.push([...e.argv])
    // Se quitan las opciones de seguridad (-c …, --no-optional-locks) y -C <carpeta> para ver el comando de git.
    const [, , cmd, ...resto] = e.argv.filter((a: string, i: number, todo: string[]) => a !== '--no-optional-locks' && a !== '-C' && a !== '-c' && todo[i - 1] !== '-c')
    if (cmd === 'rev-parse') return salida(`${mundo.raiz ?? ((mundo.carpeta ?? CARPETA).startsWith(CARPETA) ? CARPETA : mundo.carpeta)}\n`)
    if (mundo.sinGit) return salida('', 128, 'fatal: not a git repository')
    if (mundo.fallaGit) return salida('', 128, 'fatal: index file corrupt')
    if (cmd === 'status') return salida(mundo.sucio ? ' M .claude/PENDIENTES.md\n' : '')
    if (cmd === 'log') return salida((mundo.versiones ?? ['aaa 2026-10-10', 'bbb 2026-10-09']).join('\n') + '\n')
    if (cmd === 'show' && resto[0]?.startsWith('bbb:')) return salida(mundo.antes ?? ANTERIOR)
    if (cmd === 'show') return salida(mundo.antes ?? ANTERIOR)
    return salida('', 1, 'comando inesperado')
  })
  return reloj
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

test('lee el archivo real: Ahora, Esta semana, Cambios y Próxima fecha', async ($, on) => {
  fondo(on, { texto: EJEMPLO })
  for (const surface of ['terminal', 'desktop'] as const) {
    const ui = await abrir($, surface)
    // Ahora: las 9 filas de prio 1, con lo que depende de Fernando destacado.
    expect(await ui.find({ type: 'Text', text: /^Prioridad 1 · ahora$/ })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: /Hay 2 que dependen de vos|Hay 3 que dependen de vos/ })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: /te llama: falta un dato tuyo/ })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: /te llama: falta tu OK/ })).toBeDefined()
    expect(await ui.find({ type: 'Button', text: /Respaldo real de toda la Mac/ })).toBeDefined()
    expect(await ui.find({ type: 'Button', text: /Panel de pendientes a la derecha/ })).toBeDefined()
    // Prioridad 2 y 3 arrancan plegadas, con su conteo.
    expect(await ui.find({ type: 'Button', text: /› Prioridad 2 · esta semana · \d+/ })).toBeDefined()
    expect(await ui.find({ type: 'Button', text: /› Prioridad 3 · después · \d+/ })).toBeDefined()
    // Cambios: sale de comparar contra la versión anterior en git.
    expect(await ui.find({ type: 'Text', text: /Contra la versión anterior \(9\/10\)/ })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: /Nuevo · prio 2/ })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: /Cambió de prioridad · prio 2 → 1/ })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: /Cambió de estado · pendiente → espera dato/ })).toBeDefined()
    // Próxima fecha: la primera de la tabla que todavía no pasó (10/10 15:00).
    expect(await ui.find({ type: 'Text', text: /^hoy 15:00$/ })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: /Se renueva el cupo semanal de Claude/ })).toBeDefined()
    await ui.unmount()
  }
})

test('prioridad 3: solo el conteo, y un clic lo despliega', async ($, on) => {
  fondo(on, { texto: EJEMPLO })
  const ui = await abrir($)
  const antes = await ui.find({ type: 'Button', text: /Prioridad 3 · después · \d+/ })
  expect(antes).toBeDefined()
  expect(await ui.find({ type: 'Button', text: /Terminar vistas y secciones/ })).toBeUndefined()
  await ui.press({ key: 'p3' })
  expect(await ui.find({ type: 'Button', text: /Terminar vistas y secciones/ })).toBeDefined()
  expect(await ui.find({ type: 'Text', text: /Espera cupo o una decisión/ })).toBeDefined()
  await ui.unmount()
})

for (const surface of ['terminal', 'desktop'] as const) {
  test(`tocar un título muestra el detalle: de qué depende, qué desbloquea, esfuerzo y quién (${surface})`, async ($, on) => {
    fondo(on, { texto: EJEMPLO })
    const ui = await abrir($, surface)
    expect(await ui.find({ type: 'Text', text: /^Prioridad 1 · ahora$/ })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: /^Desbloquea:/ })).toBeUndefined()
    await ui.press({ key: 'fila-B1' })
    // B1 (el plan del Bicho) no depende de nada y desbloquea a las filas que lo nombran en «Depende de».
    expect(await ui.find({ type: 'Text', text: /Plan del Bicho como asistente tipo Jarvis: qué es, dónde vive/ })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: /Depende de: nada, se puede hacer ya/ })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: /Desbloquea: B3, B4, B5, B13, B7, B10, B11, E11/ })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: /Esfuerzo: grande/ })).toBeDefined()
    // S1 espera un dato de F: lo aclara en criollo.
    await ui.press({ key: 'fila-S1' })
    expect(await ui.find({ type: 'Text', text: /Necesita un dato tuyo para avanzar/ })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: /Depende de: dato de F: espacio libre en Drive/ })).toBeDefined()
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
  expect(await ui.find({ type: 'Button', text: /Respaldo real de toda la Mac/ })).toBeDefined()
  await ui.unmount()
})

test('carpeta sin lista: mensaje en criollo, no un error técnico', async ($, on) => {
  fondo(on, { texto: EJEMPLO, carpeta: '/casa/Proyectos/Otro' })
  const ui = await abrir($)
  expect(await ui.find({ type: 'Text', text: /^Esta carpeta no tiene lista de pendientes todavía\.$/ })).toBeDefined()
  expect(await ui.find({ type: 'Text', text: /^No pude leer/ })).toBeUndefined()
  expect(await ui.find({ type: 'Text', text: /^Prioridad 1 · ahora$/ })).toBeUndefined()
  await ui.unmount()
})

test('desde una subcarpeta del repo encuentra la lista de la raíz', async ($, on) => {
  fondo(on, { texto: EJEMPLO, carpeta: `${CARPETA}/sub` })
  const ui = await abrir($)
  expect(await ui.find({ type: 'Text', text: /^Prioridad 1 · ahora$/ })).toBeDefined()
  await ui.unmount()
})

test('lista con un estado inválido: avisa el problema, sigue mostrando el resto', async ($, on) => {
  fondo(on, { texto: EJEMPLO.replace(/^(\| S2 \|.*?\| 1 \| )pendiente( \|)/m, '$1inventado$2') })
  const ui = await abrir($)
  expect(await ui.find({ type: 'Text', text: /S2: el estado «inventado» no es uno de los conocidos/ })).toBeDefined()
  expect(await ui.find({ type: 'Button', text: /Respaldo real de toda la Mac/ })).toBeDefined()
  await ui.unmount()
})

async function seLeeBien($: Parameters<Parameters<typeof test>[1]>[0], on: On, texto: string) {
  fondo(on, { texto })
  const ui = await abrir($)
  expect(await ui.find({ type: 'Text', text: /^No pude leer/ })).toBeUndefined()
  expect(await ui.find({ type: 'Text', text: /te llama: falta un dato tuyo/ })).toBeDefined()
  expect(await ui.find({ type: 'Text', text: /Hay \d que dependen de vos/ })).toBeDefined()
  await ui.unmount()
}

// /metodo:cerrar y la plantilla escriben «espera dato» / «espera OK»; las listas viejas, «… de F».
test('estados cortos («espera dato», «espera OK», los que escribe /cerrar) se leen igual que los largos', async ($, on) => {
  await seLeeBien($, on, EJEMPLO.replace(/espera dato de F/g, 'espera dato').replace(/espera OK de F/g, 'espera OK'))
})

test('«Espera DATO de F» con otras mayúsculas también se lee', async ($, on) => {
  await seLeeBien($, on, EJEMPLO.replace(/espera dato de F/g, 'Espera DATO de F'))
})

test('«espera dato de Ana» se lee, pero no llama a Fer (espera a otra persona)', async ($, on) => {
  fondo(on, { texto: EJEMPLO.replace(/espera dato de F/g, 'espera dato de Ana') })
  const ui = await abrir($)
  expect(await ui.find({ type: 'Text', text: /^No pude leer/ })).toBeUndefined()
  expect(await ui.find({ type: 'Text', text: /te llama: falta un dato tuyo/ })).toBeUndefined()
  expect(await ui.find({ type: 'Text', text: /te llama: falta tu OK/ })).toBeDefined()
  await ui.unmount()
})

test('sin ninguna lista en la carpeta ni en su repo: lo dice en criollo', async ($, on) => {
  fondo(on, {})
  const ui = await abrir($)
  expect(await ui.find({ type: 'Text', text: /^Esta carpeta no tiene lista de pendientes todavía\.$/ })).toBeDefined()
  expect(await ui.find({ type: 'Text', text: /^Prioridad 1 · ahora$/ })).toBeUndefined()
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
  expect(await ui.find({ type: 'Button', text: /Respaldo real de toda la Mac/ })).toBeDefined()
  await ui.unmount()
})

test('una tabla con otras columnas se avisa', async ($, on) => {
  const roto = EJEMPLO.replace('| ID | Pendiente | Prio | Estado | Depende de | Esf. | Quién | Origen |', '| ID | Pendiente | Prio |')
  fondo(on, { texto: roto })
  const ui = await abrir($)
  expect(await ui.find({ type: 'Text', text: /Sección [SBCEMO]: la tabla no tiene las columnas/ })).toBeDefined()
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
  expect(await ui.find({ type: 'Text', text: /^Prioridad 1 · ahora$/ })).toBeDefined()
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
  expect(await ui.find({ type: 'Button', text: /Respaldo real de toda la Mac/ })).toBeDefined()
  await ui.unmount()
})

test('marcas de conflicto de git: el panel lo dice en criollo', async ($, on) => {
  fondo(on, { texto: '<<<<<<< HEAD\n' + EJEMPLO + '\n=======\n>>>>>>> otra\n' })
  const ui = await abrir($)
  expect(await ui.find({ type: 'Text', text: /marcas de conflicto de git \(línea 1\): dos sesiones editaron lo mismo/ })).toBeDefined()
  await ui.unmount()
})

test('todas las llamadas a git apagan fsmonitor y untrackedCache (repo ajeno)', async ($, on) => {
  const llamadas: string[][] = []
  fondo(on, { texto: EJEMPLO, llamadas })
  await abrir($)
  const deGit = llamadas.filter(a => a[0] === 'git')
  expect(deGit.length).toBeGreaterThan(0)
  for (const argv of deGit) {
    expect(argv.join(' ')).toContain('-c core.fsmonitor=false')
    expect(argv.join(' ')).toContain('-c core.untrackedCache=false')
    expect(argv).toContain('--no-optional-locks')
  }
})

test('nunca busca la lista en carpetas madre (podrían ser de otro proyecto o cliente)', async ($, on) => {
  // La lista existe solo en CARPETA; la sesión está en una subcarpeta que es su propio repo.
  fondo(on, { texto: EJEMPLO, carpeta: `${CARPETA}/plataforma`, raiz: `${CARPETA}/plataforma` })
  const ui = await abrir($)
  expect(await ui.find({ type: 'Text', text: /no tiene lista de pendientes/ })).toBeDefined()
  expect(await ui.find({ type: 'Text', text: /^Prioridad 1 · ahora$/ })).toBeUndefined()
  await ui.unmount()
})

test('un PENDIENTES.md enorme se corta: no cuelga el panel y muestra a lo sumo 500 filas', async ($, on) => {
  const fila = (i: number) => `| Z${i} | Fila de relleno número ${i} | 1 | pendiente | — | chico | C | prueba |\n`
  const enorme = EJEMPLO.replace('## Cadena de dependencias', '## Z · Relleno\n| ID | Pendiente | Prio | Estado | Depende de | Esf. | Quién | Origen |\n|---|---|---|---|---|---|---|---|\n' + Array.from({ length: 5000 }, (_, i) => fila(i)).join('') + '\n## Cadena de dependencias')
  expect(enorme.length).toBeGreaterThan(300_000)
  fondo(on, { texto: enorme })
  const ui = await abrir($)
  expect(await ui.find({ type: 'Text', text: /^Prioridad 1 · ahora$/ })).toBeDefined()
  expect(await ui.find({ type: 'Button', text: /Fila de relleno número 4999/ })).toBeUndefined()
  await ui.unmount()
})

// ---------- Arreglos de 2026-10-14 ----------
function arranque(on: On) {
  on('session.start', (_$, e) => ({ cwd: e.cwd }) as never)
  on('command.register', () => ({ value: { command: 'pendientes' } }) as never)
}

test('cada mensaje abre el panel DENTRO del hook (así cuenta como pedido de la persona y se dibuja con cualquier ancho)', async ($, on) => {
  fondo(on, { texto: EJEMPLO })
  arranque(on)
  let aperturas = 0
  // Cuenta solo las aperturas de ESTE panel (Uso y Actividad también abren el suyo).
  on('ui.open', (_$, e) => {
    if (e.id === 'pendientes') aperturas++
    return { value: { isPlaced: false } } as never
  })
  await $.session.start({ cwd: CARPETA } as never)
  const alArrancar = aperturas
  await $.prompt.submit({ text: 'hola' } as never)
  expect(aperturas).toBe(alArrancar + 1)
  await $.prompt.submit({ text: 'otro' } as never)
  expect(aperturas).toBe(alArrancar + 2)
})

test('la app reinicia su estado y el módulo se queda con su copia vieja: el panel se vuelve a llenar', async ($, on) => {
  const reloj = fondo(on, { texto: EJEMPLO })
  arranque(on)
  on('ui.open', () => ({ value: { isPlaced: true } }) as never)
  let escrituras = 0
  on('state.get', (_$, e, next) => (e.key === 'datos' ? ({ value: { value: undefined, version: 0 } } as never) : next(e)))
  on('state.set', (_$, e, next) => {
    if (e.key === 'datos') escrituras++
    return next(e)
  })
  await $.session.start({ cwd: CARPETA } as never)
  await reloj.advance(10)
  const primera = escrituras
  expect(primera).toBeGreaterThan(0)
  await reloj.advance(40_000)
  expect(escrituras).toBeGreaterThan(primera)
})

test('si la lista salió de una carpeta de arriba, el panel dice de cuál', async ($, on) => {
  fondo(on, { texto: EJEMPLO, carpeta: `${CARPETA}/plataforma` })
  const ui = await abrir($)
  expect(await ui.find({ type: 'Text', text: new RegExp(`Lista de ${CARPETA}`) })).toBeDefined()
  await ui.unmount()
})

test('si la lista está en la carpeta de la sesión, no avisa de otra carpeta', async ($, on) => {
  fondo(on, { texto: EJEMPLO })
  const ui = await abrir($)
  expect(await ui.find({ type: 'Text', text: /Lista de / })).toBeUndefined()
  await ui.unmount()
})

test('sesión de /cerrar sin ventana: el panel se pide de nuevo con el reloj hasta que se dibuja, y después deja de insistir', async ($, on) => {
  const reloj = fondo(on, { texto: EJEMPLO })
  on('session.start', (_$, e) => ({ cwd: e.cwd }) as never)
  on('command.register', () => ({ value: { command: 'pendientes' } }) as never)
  let hayVentana = false
  let aperturas = 0
  on('ui.open', () => {
    aperturas++
    return { value: { isPlaced: hayVentana } } as never
  })
  await $.session.start({ cwd: '/casa/Proyectos/Tienda' } as never)
  const sinVentana = aperturas
  await reloj.advance(90100)
  expect(aperturas).toBeGreaterThan(sinVentana) // insiste mientras no hay ventana
  hayVentana = true
  await reloj.advance(30100)
  const alDibujar = aperturas
  await reloj.advance(120000)
  expect(aperturas).toBe(alDibujar) // ya dibujado: no vuelve a pedirlo
})

// ---------- Unificación con las tareas de la sesión (2026-10-16) ----------
const TAREAS = JSON.stringify({
  tareas: [
    { id: 'T0', texto: 'Unificar paneles', estado: 'in_progress' },
    { id: 'S1', texto: 'Respaldo en sesión', estado: 'pending' },
    { id: 'T1', texto: 'Arranque de sesión', estado: 'completed' },
  ],
})

test('arriba «Esta sesión»: en curso ◐, por hacer ○, hechas ✅ tachadas', async ($, on) => {
  fondo(on, { texto: EJEMPLO, tareas: TAREAS })
  for (const surface of ['terminal', 'desktop'] as const) {
    const ui = await abrir($, surface)
    expect(await ui.find({ type: 'Text', text: /ESTA SESIÓN/ })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: /1 en curso · 1 por hacer · 1 hecha/ })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: /◐ Unificar paneles/ })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: /○ Respaldo en sesión/ })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: /✅ Arranque de sesión/ })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: /PENDIENTES QUE ARRASTRAMOS/ })).toBeDefined()
    await ui.unmount()
  }
})

test('lo que está en las dos listas se MARCA abajo («en sesión»), no se esconde', async ($, on) => {
  fondo(on, { texto: EJEMPLO, tareas: TAREAS })
  const ui = await abrir($)
  expect(await ui.find({ type: 'Button', text: /Respaldo real de toda la Mac.*S1 · en sesión/ })).toBeDefined()
  expect(await ui.find({ type: 'Button', text: /Plan del Bicho como asistente tipo Jarvis.*B1 ›/ })).toBeDefined()
  await ui.unmount()
})

test('lo que espera algo de Fer lleva la manito ✋ y «te llama»; ◐ en curso; ○ por hacer', async ($, on) => {
  fondo(on, { texto: EJEMPLO })
  const ui = await abrir($)
  expect(await ui.find({ type: 'Text', text: /^✋$/ })).toBeDefined()
  expect(await ui.find({ type: 'Text', text: /te llama: falta un dato tuyo/ })).toBeDefined()
  expect(await ui.find({ type: 'Text', text: /^◐$/ })).toBeDefined()
  expect(await ui.find({ type: 'Text', text: /^○$/ })).toBeDefined()
  await ui.unmount()
})

test('sin tareas de sesión: lo dice, y la lista de pendientes se ve igual', async ($, on) => {
  fondo(on, { texto: EJEMPLO })
  const ui = await abrir($)
  expect(await ui.find({ type: 'Text', text: /Sin tareas todavía/ })).toBeDefined()
  expect(await ui.find({ type: 'Button', text: /Respaldo real de toda la Mac/ })).toBeDefined()
  await ui.unmount()
})

test('si la carpeta no tiene PENDIENTES.md, las tareas de la sesión se ven igual', async ($, on) => {
  fondo(on, { tareas: TAREAS })
  const ui = await abrir($)
  expect(await ui.find({ type: 'Text', text: /◐ Unificar paneles/ })).toBeDefined()
  expect(await ui.find({ type: 'Text', text: /Esta carpeta no tiene lista de pendientes todavía/ })).toBeDefined()
  await ui.unmount()
})

test('la que espera a otra va sangrada debajo, con ↳', async ($, on) => {
  fondo(on, { texto: EJEMPLO.replace(/^(\| B3 \|.*?\| )2( \|)/m, '$11$2') })
  const ui = await abrir($)
  // B3 (ahora prioridad 1) nombra a B1 en «Depende de»: B1 va arriba y B3 cuelga de él.
  // En el archivo real, B1 desbloquea a otras; las prioridad 1 que lo nombran en «Depende de» cuelgan de él.
  expect(await ui.find({ type: 'Text', text: /^↳$/ })).toBeDefined()
  await ui.unmount()
})
