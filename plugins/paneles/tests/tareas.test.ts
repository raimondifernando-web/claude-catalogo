import { expect, mock, test } from 'claude-code/testing'
import type { On } from 'claude-code'

const PANEL = {
  component: 'Pane' as const,
  requestId: 'tareas-sesion',
  props: { title: 'Tareas', isFocused: false, bodyColumns: 36, placement: 'dock' as const, scroll: { offset: 0, bodyRows: 30 }, view: {} },
}

// El motor de abajo: las herramientas de tareas "andan" y devuelven un id.
function fondo(on: On) {
  on('tool.call', (_$, e) => {
    if (e.tool === 'TaskCreate') return { result: { task: { id: '7', subject: e.subject } } } as never
    if (e.tool === 'TaskUpdate') return { result: { success: true, taskId: e.taskId, updatedFields: ['status'] } } as never
    return { result: { oldTodos: [], newTodos: [] } } as never
  })
}

test('TodoWrite y TaskCreate/TaskUpdate se ven en vivo y lo hecho se tacha', async ($, on) => {
  fondo(on)
  const ui = await $.ui.mount({ plugin: 'paneles', surface: 'desktop', ...PANEL })
  expect(await ui.find({ type: 'Text', text: /Sin tareas/ })).toBeDefined()

  await $.tool.call({ tool: 'TodoWrite', todos: [
    { content: 'Investigar', status: 'completed', activeForm: 'Investigando' },
    { content: 'Armar mod', status: 'in_progress', activeForm: 'Armando' },
  ] } as never)
  const a = await ui.find({ type: 'Text', text: /Investigar/ })
  expect(a.props.strikethrough).toBe(true)
  const b = await ui.find({ type: 'Text', text: /Armar mod/ })
  expect(b.props.strikethrough).toBeFalsy()

  await $.tool.call({ tool: 'TaskCreate', subject: 'Tarea nueva', description: 'x' } as never)
  expect(await ui.find({ type: 'Text', text: /Tarea nueva/ })).toBeDefined()
  await $.tool.call({ tool: 'TaskUpdate', taskId: '7', status: 'completed' } as never)
  const c = await ui.find({ type: 'Text', text: /Tarea nueva/ })
  expect(c.props.strikethrough).toBe(true)
  await ui.unmount()
})

test('lee .claude/tareas.json: tacha completed, ▶ in_progress y se actualiza solo', async ($, on) => {
  const reloj = mock.clock(on, { now: 0 })
  let contenido = JSON.stringify({ tareas: [
    { id: '1', texto: 'Hecha', estado: 'completed' },
    { id: '2', texto: 'En curso', estado: 'in_progress' },
  ] })
  on('session.start', (_$, e) => ({ cwd: e.cwd }) as never)
  on('command.register', () => ({ value: { command: 'tareas' } }) as never)
  on('ui.open', () => ({ value: { isPlaced: true } }) as never)
  on('session.root', () => ({ value: '/proy' }) as never)
  on('fs.read', (_$, e) => {
    if (e.path !== '/proy/.claude/tareas.json') throw new Error('ENOENT')
    return { value: contenido } as never
  })
  await $.session.start({ cwd: '/proy' } as never)
  const ui = await $.ui.mount({ plugin: 'paneles', surface: 'desktop', ...PANEL })
  expect((await ui.find({ type: 'Text', text: /Hecha/ })).props.strikethrough).toBe(true)
  expect(await ui.find({ type: 'Text', text: /▶ En curso/ })).toBeDefined()
  contenido = JSON.stringify({ tareas: [
    { id: '1', texto: 'Hecha', estado: 'completed' },
    { id: '2', texto: 'En curso', estado: 'completed' },
    { id: '3', texto: 'Nueva', estado: 'pending' },
  ] })
  await reloj.advance(4000)
  expect((await ui.find({ type: 'Text', text: /En curso/ })).props.strikethrough).toBe(true)
  expect(await ui.find({ type: 'Text', text: /Nueva/ })).toBeDefined()
  await ui.unmount()
})

// ---------- Derivadas de PENDIENTES.md + git ----------
const CAB = '| ID | Pendiente | Prio | Estado | Depende de | Esf. | Quién | Origen |\n|---|---|---|---|---|---|---|---|\n'
const fila = (id: string, txt: string, prio: number, estado: string) => `| ${id} | ${txt} | ${prio} | ${estado} | — | chico | C | x |\n`
const PEND_ANTES = '## A · Tema\n' + CAB + fila('A1', '**Cerrar el trato**: detalle largo', 1, 'en curso') + fila('A2', 'Arreglar el robot', 2, 'pendiente') + fila('A3', 'Algo para después', 3, 'pendiente')
const PEND_AHORA = '## A · Tema\n' + CAB + fila('A1', '**Cerrar el trato**: detalle largo', 1, 'hecho') + fila('A2', 'Arreglar el robot', 2, 'en curso') +
  fila('A3', 'Algo para después', 3, 'pendiente') + fila('A4', 'Cosa urgente nueva', 1, 'pendiente') + fila('A5', 'Nueva esta semana', 2, 'pendiente') + fila('A6', 'Nueva lejana', 3, 'pendiente')

function mundoGit(on: On, ahora: string, anterior: string, fechaCambio: string) {
  const hoy = new Date().toISOString().slice(0, 10)
  on('session.start', (_$, e) => ({ cwd: e.cwd }) as never)
  on('command.register', () => ({ value: { command: 'tareas' } }) as never)
  on('ui.open', () => ({ value: { isPlaced: true } }) as never)
  on('session.root', () => ({ value: '/proy' }) as never)
  on('fs.read', (_$, e) => {
    if (e.path === '/proy/.claude/PENDIENTES.md') return { value: ahora } as never
    if (e.path === '/proy/.claude/tareas.json')
      return { value: JSON.stringify({ tareas: [{ id: 't1', texto: 'A4: texto viejo', estado: 'pending' }, { id: 't2', texto: 'Tarea manual', estado: 'pending' }] }) } as never
    throw new Error('ENOENT')
  })
  on('process.run', (_$, e) => {
    const cmd = e.argv[4]
    const ok = (stdout: string) => ({ value: { exitCode: 0, stdout, stderr: '', isStdoutTruncated: false, isStderrTruncated: false } }) as never
    if (cmd === 'status') return ok('')
    if (cmd === 'log') return ok(`aaa ${fechaCambio === 'hoy' ? hoy : fechaCambio}\nbbb 2026-01-01\n`)
    if (cmd === 'show') return ok(anterior)
    return { value: { exitCode: 1, stdout: '', stderr: 'inesperado', isStdoutTruncated: false, isStderrTruncated: false } } as never
  })
}

test('se arma solo desde PENDIENTES+git: en curso ▶, urgentes ○, cerrado ✓; lo manual con el mismo ID se reemplaza', async ($, on) => {
  mock.clock(on, { now: Date.now() })
  mundoGit(on, PEND_AHORA, PEND_ANTES, 'hoy')
  await $.session.start({ cwd: '/proy' } as never)
  const ui = await $.ui.mount({ plugin: 'paneles', surface: 'desktop', ...PANEL })
  for (const r of [/▶ A2: Arreglar el robot/, /○ A4: Cosa urgente nueva/, /○ A5: Nueva esta semana/, /A1: Cerrar el trato/, /Tarea manual/]) expect(await ui.find({ type: 'Text', text: r }), String(r)).toBeDefined()
  expect(await ui.find({ type: 'Text', text: /○ A4: Cosa urgente nueva/ })).toBeDefined()
  expect(await ui.find({ type: 'Text', text: /○ A5: Nueva esta semana/ })).toBeDefined()
  const hecha = await ui.find({ type: 'Text', text: /A1: Cerrar el trato/ })
  expect(hecha.props.strikethrough).toBe(true)
  expect(await ui.find({ type: 'Text', text: /Tarea manual/ })).toBeDefined()
  expect(await ui.find({ type: 'Text', text: /texto viejo/ })).toBeUndefined()
  expect(await ui.find({ type: 'Text', text: /Algo para después/ })).toBeUndefined()
  expect(await ui.find({ type: 'Text', text: /Nueva lejana/ })).toBeUndefined()
  await ui.unmount()
})

test('lo cerrado hace más de 2 días no se muestra', async ($, on) => {
  mock.clock(on, { now: Date.now() })
  mundoGit(on, PEND_AHORA, PEND_ANTES, '2026-01-02')
  await $.session.start({ cwd: '/proy' } as never)
  const ui = await $.ui.mount({ plugin: 'paneles', surface: 'desktop', ...PANEL })
  expect(await ui.find({ type: 'Text', text: /▶ A2/ })).toBeDefined()
  expect(await ui.find({ type: 'Text', text: /A1: Cerrar el trato/ })).toBeUndefined()
  await ui.unmount()
})
