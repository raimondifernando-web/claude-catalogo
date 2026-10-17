import { expect, test } from 'claude-code/testing'

import { actArmar as armar } from '../hooks/register'

// 16/10/2026 12:00 en Argentina (UTC-3).
const AHORA = Date.parse('2026-10-16T15:00:00Z')
const min = (n: number) => AHORA - n * 60_000

test('un agente sin parada reciente aparece en «Ahora» y cuenta como trabajando', () => {
  const m = armar([{ t: min(2), ev: 'start', tipo: 'agente', n: 'pm-marketing', id: 'a1', s: 'abc' }], AHORA)
  expect(m.ahora[0]?.raices.map(a => a.nombre)).toEqual(['pm-marketing'])
  expect(m.trabajando).toBe(1)
  expect(m.hoy).toEqual([])
})

test('árbol: la skill y el subagente cuelgan del agente que los usó', () => {
  const m = armar(
    [
      { t: min(5), ev: 'start', tipo: 'agente', n: 'pm-marketing', id: 'p', s: 'abc' },
      { t: min(4), ev: 'link', id: 'e', padre: 'p' },
      { t: min(4), ev: 'start', tipo: 'agente', n: 'Explore', id: 'e', s: 'abc' },
      { t: min(3), ev: 'start', tipo: 'skill', n: 'copywriting', por: 'p', s: 'abc' },
      { t: min(3), ev: 'start', tipo: 'skill', n: 'seo-audit', por: 'e', s: 'abc' },
      { t: min(1), ev: 'start', tipo: 'skill', n: 'fable-plan', s: 'abc' },
    ],
    AHORA,
  )
  const raices = m.ahora[0]?.raices ?? []
  const pm = raices.find(r => r.nombre === 'pm-marketing')
  expect(pm?.hijos.map(h => h.nombre)).toEqual(['Explore', 'copywriting'])
  expect(pm?.hijos[0]?.hijos.map(h => h.nombre)).toEqual(['seo-audit'])
  // La skill que usó la persona queda suelta, en la raíz.
  expect(m.hoy[0]?.raices.map(r => r.nombre)).toContain('fable-plan')
})

test('con parada pasa a «Hoy» y trae la duración; nada queda trabajando', () => {
  const m = armar(
    [
      { t: min(10), ev: 'start', tipo: 'agente', n: 'Explore', id: 'a2', s: 'abc' },
      { t: min(9), ev: 'stop', tipo: 'agente', n: 'Explore', id: 'a2' },
    ],
    AHORA,
  )
  expect(m.ahora).toEqual([])
  expect(m.trabajando).toBe(0)
  expect(m.hoy[0]?.raices[0]?.dur).toBe(60_000)
})

test('un agente colgado viejo no queda «activo» y las líneas sin nombre se ignoran', () => {
  const m = armar(
    [
      { t: min(300), ev: 'start', tipo: 'agente', n: 'Explore', id: 'x', s: 'abc' },
      { t: min(1), ev: 'start', tipo: 'agente', n: '', id: 'z', s: 'abc' },
    ],
    AHORA + 7 * 3600_000,
  )
  expect(m.ahora).toEqual([])
  expect(m.trabajando).toBe(0)
})

test('nunca guarda ni expone contenido: el modelo solo tiene nombre, hora y duración', () => {
  const m = armar([{ t: min(1), ev: 'start', tipo: 'agente', n: 'Explore', id: 'q', s: 'abc', prompt: 'SECRETO' }], AHORA)
  expect(JSON.stringify(m)).not.toContain('SECRETO')
})

import { mock } from 'claude-code/testing'

const REGISTRO = [
  { t: AHORA - 40_000, ev: 'start', tipo: 'agente', n: 'pm-marketing', id: 'p1', s: 'abc' },
  { t: AHORA - 30_000, ev: 'start', tipo: 'skill', n: 'copywriting', por: 'p1', s: 'abc' },
  { t: AHORA - 3_600_000, ev: 'start', tipo: 'agente', n: 'Explore', id: 'e1', s: 'abc' },
  { t: AHORA - 3_588_000, ev: 'stop', tipo: 'agente', n: 'Explore', id: 'e1', s: 'abc' },
  { t: AHORA - 7_200_000, ev: 'start', tipo: 'skill', n: 'fable-plan', s: 'abc' },
]
  .map(o => JSON.stringify(o))
  .join('\n')

for (const surface of ['terminal', 'desktop'] as const) {
  test(`el panel muestra Ahora, Hoy y los 30 días (${surface})`, async ($, on) => {
    mock.clock(on, { now: AHORA })
    on('session.measure', (_$, e) => ({ changed: e.changed }))
    on('ui.render', ($, e) => { const { Box } = $.ui.resolve(e); return h(Box, {}) })
    mock.env(on, { HOME: '/casa' })
    on('process.run', () => ({ value: { exitCode: 128, stdout: '', stderr: 'fatal', isStdoutTruncated: false, isStderrTruncated: false } }) as never)
    on('ui.open', () => ({ value: { isPlaced: true } }) as never)
    on('session.root', () => ({ value: '/casa' }) as never)
    on('fs.list', () => ({ value: [{ name: '2026-10-16-abc.jsonl', kind: 'file', size: 1, mtimeMs: AHORA, isLink: false }] }) as never)
    on('fs.read', (_$, e, next) => {
      if (e.path.endsWith('.jsonl')) return { value: REGISTRO } as never
      if (e.path.endsWith('sin-uso.json')) return { value: JSON.stringify({ dias: 30, sin: 154, total: 191, generado: 'x' }) } as never
      return next(e)
    })
    await $.session.measure({ context: { window: 1_000_000 }, rateLimits: [], changed: ['context'] })
    const ui = await $.ui.mount({
      plugin: 'paneles',
      surface,
      component: 'Pane' as const,
      requestId: 'actividad',
      props: { title: 'Actividad', isFocused: false, bodyColumns: 38, placement: 'dock' as const, scroll: { offset: 0, bodyRows: 40 }, view: {} },
    })
    expect(await ui.find({ type: 'Text', text: /^Ahora$/ })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: /pm-marketing/ })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: /^Hoy · terminaron$/ })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: /copywriting/ })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: /1 trabajando/ })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: /Explore/ })).toBeDefined()
    expect(await ui.find({ type: 'Text', text: /Sin activarse en 30 días: 154 de 191/ })).toBeDefined()
    // En la app van los bichitos dibujados; en la terminal, símbolos de texto.
    if (surface === 'desktop') expect(await ui.find({ type: 'Svg' })).toBeDefined()
    else expect(await ui.find({ type: 'Svg' })).toBeUndefined()
    await ui.unmount()
  })
}

test('un agente anotado dos veces (arranque y recuento del motor) cuenta una sola vez', () => {
  const m = armar(
    [
      { t: min(2), ev: 'start', tipo: 'agente', n: 'general-purpose', id: 'a9', s: 'abc' },
      { t: min(1), ev: 'start', tipo: 'agente', n: 'agente', id: 'a9', s: 'abc' },
    ],
    AHORA,
  )
  expect(m.ahora[0]?.raices.length).toBe(1)
  expect(m.trabajando).toBe(1)
})

test('si el motor lo vio corriendo después de la parada, sigue encendido; la parada final lo apaga', () => {
  const base = [
    { t: min(5), ev: 'start', tipo: 'agente', n: 'general-purpose', id: 'a7', s: 'abc' },
    { t: min(4), ev: 'stop', tipo: 'agente', n: 'general-purpose', id: 'a7' },
    { t: min(3), ev: 'resume', id: 'a7', s: 'abc' },
  ]
  expect(armar(base, AHORA).trabajando).toBe(1)
  const fin = armar([...base, { t: min(1), ev: 'stop', tipo: 'agente', n: 'general-purpose', id: 'a7' }], AHORA)
  expect(fin.trabajando).toBe(0)
  expect(fin.hoy[0]?.raices[0]?.dur).toBe(4 * 60_000)
})
