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
