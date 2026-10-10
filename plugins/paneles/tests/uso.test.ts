import { expect, mock, test } from 'claude-code/testing'
import type { On } from 'claude-code'

// El mundo de abajo: reloj fijo, panel vacío, mediciones y desglose de mentira.
function fondo(on: On) {
  mock.clock(on, { now: Date.parse('2026-10-10T13:00:00Z') })
  on('ui.render', ($, e) => {
    const { Box } = $.ui.resolve(e)
    return h(Box, {})
  })
  on('session.measure', (_$, e) => ({ changed: e.changed }))
  on('prompt.submit', (_$, e) => ({ text: e.text }))
  on('session.usage', () =>
    ({
      value: {
      startedAt: 0,
      rateLimits: [],
      context: {
        tokens: 236_597,
        window: 1_000_000,
        percent: 24,
        breakdown: {
          categories: [
            { name: 'Messages', tokens: 95_000, color: 'claude', isDeferred: false, kind: 'used' },
            { name: 'MCP tools', tokens: 32_000, color: 'permission', isDeferred: false, kind: 'used' },
            { name: 'Free space', tokens: 700_000, color: 'inactive', isDeferred: false, kind: 'free' },
          ],
        },
      },
      },
    }) as never,
  )
}

const PANEL = {
  component: 'Pane' as const,
  requestId: 'medidor-uso',
  props: {
    title: 'Uso',
    isFocused: false,
    bodyColumns: 36,
    placement: 'dock' as const,
    scroll: { offset: 0, bodyRows: 30 },
    view: {},
  },
}

const LIMITES = [
  { kind: 'five_hour', percentUsed: 1, resetsAt: '2026-10-10T17:49:59Z' },
  { kind: 'seven_day', percentUsed: 95, resetsAt: '2026-10-10T17:59:59Z' },
]

test('muestra contexto por categoría, límites y qué gastó más', async ($, on) => {
  fondo(on)
  await $.prompt.submit({ text: '/arrancar' })
  await $.session.measure({
    context: { tokens: 236_597, window: 1_000_000, percent: 24 },
    rateLimits: LIMITES,
    cost: { usd: 3 },
    changed: ['context', 'rateLimits', 'cost'],
  })
  await $.prompt.submit({ text: 'seguimos con el panel' })
  await $.session.measure({
    context: { tokens: 240_000, window: 1_000_000, percent: 24 },
    rateLimits: LIMITES,
    cost: { usd: 4 },
    changed: ['context', 'cost'],
  })

  for (const surface of ['terminal', 'desktop'] as const) {
    const ui = await $.ui.mount({ plugin: 'paneles', surface, ...PANEL })
    expect(await ui.find({ type: 'Text', text: /95 %/ })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: /Se renueva hoy a las 14:59/ })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: /\/arrancar/ })).toBeDefined()
    await ui.unmount()
  }

  const ui = await $.ui.mount({ plugin: 'paneles', surface: 'desktop', ...PANEL })
  const graficos = (await ui.findAll({ type: 'Svg' })).map(x => String(x.props.alt))
  expect(graficos).toContain('Mensajes 95K, MCP 32K')
  expect(await ui.find({ type: 'Text', text: /^75 %$/ })).toBeDefined()
  expect(await ui.find({ type: 'Text', text: /modelo más barato/ })).toBeDefined()
  // Sin Codex ni Gemini: no aparece nada de eso ni ningún error técnico.
  expect(await ui.find({ type: 'Text', text: /Codex|Gemini|rror/ })).toBeUndefined()
  await ui.unmount()
})

test('sin medición todavía avisa que espera', async ($, on) => {
  fondo(on)
  const ui = await $.ui.mount({ plugin: 'paneles', surface: 'desktop', ...PANEL })
  expect(await ui.find({ type: 'Text', text: /Esperando/ })).toBeDefined()
  await ui.unmount()
})
