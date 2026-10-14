import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register, SessionContextUsage, SessionRateLimit } from 'claude-code'

import type { Tarea, Categoria, Cambio, Cambios, Fila, Gasto, Limite, Medida, Modelo, Proxima } from '../types'

// Plugin «paneles»: tres paneles a la derecha, «Uso», «Pendientes» y «Tareas». Un plugin tiene un solo
// módulo de hooks y no admite dos hooks del mismo evento sin filtro, y `$` no cruza archivos:
// por eso van juntos acá, y los hooks de los dos paneles se encadenan al final.


// Panel propio «Uso»: lo mismo que el circulito de uso de la app (contexto de esta
// sesión por categoría + límites del plan) y qué gastó más, siempre a la vista.
// Estilo macOS (como Almacenamiento): solo la línea del contexto lleva color; el resto, en grises.
// Hook sin filtro: lo registra register.tsx (un solo hook por evento en todo el plugin).
type H = ($: EngineInterface, e: any, next: (e: any) => any) => any // eslint-disable-line @typescript-eslint/no-explicit-any

const PANEL = 'medidor-uso'
const TITULO = 'Uso'
const medida = atom({ plugin: 'paneles', key: 'medida' } as const, null)
const categorias = atom({ plugin: 'paneles', key: 'categorias' } as const, [])
const GASTO_INICIAL: Gasto = { actual: 'conversación', costoPrevio: 0, porOrigen: {} }
const gasto = atom({ plugin: 'paneles', key: 'gasto' } as const, GASTO_INICIAL)

// Grises del sistema de Apple: se leen en modo claro y oscuro.
const GRIS = '#8E8E93'
const PISTA = 'rgba(142,142,147,0.22)'
const RESERVA = 'rgba(142,142,147,0.45)'
const SEPARADOR = 'rgba(142,142,147,0.28)'

// Colores del sistema de Apple por categoría, como la barra de Almacenamiento de macOS.
const COLOR_CATEGORIA: Record<string, string> = {
  Messages: '#0A84FF', // azul
  'MCP tools': '#BF5AF2', // violeta
  'Memory files': '#FF9F0A', // naranja
  'System tools': '#64D2FF', // celeste
  'System prompt': '#5E5CE6', // índigo
  'Custom agents': '#FF375F', // rosa
  Skills: '#FFD60A', // amarillo
}
const COLOR_OTRA = '#30D158' // verde, para lo que no está arriba

// Nombres de /context en castellano; lo que no está, queda como viene.
const CATEGORIAS: Record<string, string> = {
  'System prompt': 'Sistema',
  'System tools': 'Herramientas',
  'MCP tools': 'MCP',
  'Custom agents': 'Agentes',
  'Memory files': 'Memoria',
  Skills: 'Skills',
  Messages: 'Mensajes',
  'Free space': 'Libre',
  'Autocompact buffer': 'Reserva',
}

// Argentina no cambia de hora: UTC-3 todo el año.
const ART_MS = 3 * 60 * 60 * 1000
const DIAS = ['dom', 'lun', 'mar', 'mié', 'jue', 'vie', 'sáb']

const NOMBRES: Record<string, string> = {
  five_hour: 'Sesión de 5 horas',
  seven_day: 'Semana',
  spend_limit: 'Tope de gasto',
}

const ANCHO = 300
const ALTO = 6

function abreviar(n: number): string {
  if (n >= 1_000_000) return `${+(n / 1_000_000).toFixed(1)}M`
  if (n >= 1_000) return `${Math.round(n / 1_000)}K`
  return String(n)
}

function horaRenovacion(iso: string | undefined, ahora: number): string {
  const t = iso ? Date.parse(iso) : NaN
  if (Number.isNaN(t)) return ''
  const local = new Date(t - ART_MS)
  const hoy = new Date(ahora - ART_MS)
  const hh = String(local.getUTCHours()).padStart(2, '0')
  const mm = String(local.getUTCMinutes()).padStart(2, '0')
  const mismoDia =
    local.getUTCFullYear() === hoy.getUTCFullYear() &&
    local.getUTCMonth() === hoy.getUTCMonth() &&
    local.getUTCDate() === hoy.getUTCDate()
  if (mismoDia) return `hoy a las ${hh}:${mm}`
  // A más de 6 días el día de la semana confunde: va la fecha.
  if (t - ahora > 6 * 24 * 3600 * 1000) return `el ${local.getUTCDate()}/${local.getUTCMonth() + 1}`
  return `el ${DIAS[local.getUTCDay()]} a las ${hh}:${mm}`
}

function colorCategoria(c: Categoria): string {
  if (c.kind === 'free') return PISTA
  if (c.kind === 'buffer') return RESERVA
  return COLOR_CATEGORIA[c.name] ?? COLOR_OTRA
}

function svg(cuerpo: string, alto = ALTO): string {
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${ANCHO}" height="${alto}" viewBox="0 0 ${ANCHO} ${alto}">${cuerpo}</svg>`
}

// Línea de progreso en grises: pista clara y tramo gris redondeado.
function lineaGris(pct: number): string {
  const lleno = (Math.max(0, Math.min(100, pct)) / 100) * ANCHO
  return svg(
    `<rect width="${ANCHO}" height="${ALTO}" rx="${ALTO / 2}" fill="${PISTA}"/>` +
      (lleno > 0 ? `<rect width="${Math.max(lleno, ALTO).toFixed(1)}" height="${ALTO}" rx="${ALTO / 2}" fill="${GRIS}"/>` : ''),
  )
}

// La línea del contexto partida por categoría, con un hilo de separación entre tramos.
function lineaContexto(cats: Categoria[], pct: number | undefined): string {
  if (cats.length === 0) {
    const lleno = (Math.max(0, Math.min(100, pct ?? 0)) / 100) * ANCHO
    return svg(
      `<rect width="${ANCHO}" height="${ALTO}" rx="${ALTO / 2}" fill="${PISTA}"/>` +
        `<rect width="${lleno.toFixed(1)}" height="${ALTO}" rx="${ALTO / 2}" fill="${COLOR_CATEGORIA.Messages}"/>`,
    )
  }
  const total = cats.reduce((s, c) => s + c.tokens, 0) || 1
  let x = 0
  let tramos = ''
  for (const c of cats) {
    const w = (c.tokens / total) * ANCHO
    if (w > 0.5) {
      const hueco = c.kind === 'used' ? 1 : 0
      tramos += `<rect x="${x.toFixed(1)}" width="${Math.max(0, w - hueco).toFixed(1)}" height="${ALTO}" fill="${colorCategoria(c)}"/>`
    }
    x += w
  }
  return svg(`<clipPath id="r"><rect width="${ANCHO}" height="${ALTO}" rx="${ALTO / 2}"/></clipPath><g clip-path="url(#r)">${tramos}</g>`)
}

// Leyenda chica en dos columnas, de mayor a menor (primero baja la izquierda), como macOS.
function leyenda(cats: Categoria[]): string {
  const FILA = 16
  const COL = ANCHO / 2
  const porColumna = Math.ceil(cats.length / 2)
  const alto = porColumna * FILA
  const fuente = `font-family="-apple-system, BlinkMacSystemFont, 'SF Pro Text', system-ui, sans-serif" font-size="11"`
  let cuerpo = ''
  cats.forEach((c, i) => {
    const x = i < porColumna ? 0 : COL
    const y = (i % porColumna) * FILA + FILA / 2
    const nombre = (CATEGORIAS[c.name] ?? c.name).replace(/[<>&"]/g, '')
    cuerpo +=
      `<circle cx="${x + 4}" cy="${y}" r="3.5" fill="${colorCategoria(c)}"/>` +
      `<text x="${x + 13}" y="${y + 4}" ${fuente} fill="${GRIS}">${nombre}</text>` +
      `<text x="${x + COL - 10}" y="${y + 4}" ${fuente} fill="${GRIS}" fill-opacity="0.7" text-anchor="end">${abreviar(c.tokens)}</text>`
  })
  return svg(cuerpo, alto)
}

const SEPARACION = svg(`<rect y="0" width="${ANCHO}" height="1" fill="${SEPARADOR}"/>`, 1)

function barra(pct: number | undefined): string {
  const n = Math.round(Math.max(0, Math.min(100, pct ?? 0)) / 5)
  return '━'.repeat(n) + '╌'.repeat(20 - n)
}

function armar(context: SessionContextUsage, rateLimits: SessionRateLimit[], previa: Medida | null): Medida {
  const limites: Limite[] = rateLimits.map(l => ({ kind: l.kind, percentUsed: l.percentUsed, resetsAt: l.resetsAt }))
  return {
    tokens: context.tokens ?? previa?.tokens,
    window: context.window,
    percent: context.percent ?? previa?.percent,
    // Antes de la primera respuesta los límites vienen vacíos: se mantiene la última lectura.
    limites: limites.length > 0 ? limites : (previa?.limites ?? []),
  }
}

// Qué arrancó el turno: el comando con el que empieza el mensaje, o la charla.
function origenDe(texto: string): string {
  const m = /^\s*(\/[\w:.-]+)/.exec(texto)
  return m?.[1] ?? 'conversación'
}

function ranking(g: Gasto): { origen: string; pct: number }[] {
  const total = Object.values(g.porOrigen).reduce((s, v) => s + v, 0)
  if (total <= 0) return []
  return Object.entries(g.porOrigen)
    .map(([origen, usd]) => ({ origen, pct: Math.round((usd / total) * 100) }))
    .filter(r => r.pct > 0)
    .sort((a, b) => b.pct - a.pct)
    .slice(0, 4)
}

// Un panel que se abre «solo» (sin que la persona lo pida) no se dibuja por debajo de 144 columnas, ni si todavía no hay
// ventana (sesiones que abre /cerrar). Un open que responde al mensaje de la persona se dibuja con cualquier ancho, pero
// solo cuenta como «pedido» si se hace DENTRO del hook de prompt.submit, esperado (await) antes de devolver. Por eso el
// open va primero y sin consultar nada antes. Abrir un id ya abierto solo lo retitula, así que se hace con cada mensaje.
// Si la persona lo cierra a mano, no se vuelve a abrir solo.
let uCerrado = false

async function uAsegurar($: EngineInterface): Promise<void> {
  if (uCerrado) return
  try {
    await $.ui.open({ id: PANEL, title: TITULO, columns: 36 })
  } catch {
    // se reintenta con el próximo mensaje
  }
}

const usoSessionStart: H = async ($, e, next) => {
  const ran = await next(e)
  uCerrado = false
  await $.command.register({ name: 'uso', description: 'Abre el panel de uso (contexto y límites del plan)' })
  void uAsegurar($)
  // La primera medición llega sola con session.measure si esta falla.
  try {
    const u = await $.session.usage()
    await update($, medida, previa => armar(u.context, u.rateLimits, previa))
  } catch {
    // se mide con el primer turno
  }
  return ran
}

const usoCommandRun: H = async ($, e, next) => {
  if (e.command !== 'uso') {
    const ahora = await $.clock.now()
    await update($, gasto, g => ({ ...(g ?? GASTO_INICIAL), actual: `/${e.command}`, marca: ahora }))
  }
  return next(e)
}

const usoPromptSubmit: H = async ($, e, next) => {
  await uAsegurar($)
  const ahora = await $.clock.now()
  await update($, gasto, g => {
    const base = g ?? GASTO_INICIAL
    const reciente = base.marca !== undefined && ahora - base.marca < 5_000
    const origen = origenDe(e.text)
    return { ...base, actual: origen !== 'conversación' || !reciente ? origen : base.actual, marca: undefined }
  })
  return next(e)
}

const usoSessionMeasure: H = async ($, e, next) => {
  await update($, medida, previa => armar(e.context, e.rateLimits, previa))

  // Lo que costó desde la medición anterior se le asigna a lo que arrancó el turno.
  if (e.cost) {
    const total = e.cost.usd
    await update($, gasto, g => {
      const base = g ?? GASTO_INICIAL
      const delta = Math.max(0, total - base.costoPrevio)
      const porOrigen = { ...base.porOrigen }
      if (delta > 0) porOrigen[base.actual] = (porOrigen[base.actual] ?? 0) + delta
      return { ...base, costoPrevio: total, porOrigen }
    })
  }

  // Desglose por categoría: estimado local, sin pedidos a la API (gratis).
  try {
    const u = await $.session.usage({ breakdown: 'summary' })
    const cats = (u.context.breakdown?.categories ?? [])
      .filter(c => c.kind !== 'deferred')
      .map(c => ({ name: c.name, tokens: c.tokens, color: c.color, kind: c.kind as Categoria['kind'] }))
    if (cats.length > 0) await update($, categorias, () => cats)
  } catch {
    // Sin desglose se dibuja la línea simple.
  }
  return next(e)
}

const registrarUso: Register = on => {

  on('ui.close', { id: PANEL }, async ($, e, next) => {
    if (e.origin.kind === 'person') uCerrado = true
    return next(e)
  }).catch(($, e, next) => next(e))

  on('command.run', { command: 'uso' }, async $ => {
    uCerrado = false
    await $.ui.open({ id: PANEL, title: TITULO, columns: 36 })
    return { text: 'Panel de uso abierto.' }
  })

  // Un comando escrito («/arrancar») marca el origen; si después llega su texto expandido
  // como mensaje, se respeta el comando. 5 s alcanzan: la expansión es inmediata.



  on('ui.render', { component: 'Pane', requestId: PANEL }, async ($, e) => {
    const m = await read($, medida)
    const cats = (await read($, categorias)) ?? []
    const g = (await read($, gasto)) ?? GASTO_INICIAL
    const ahora = await $.clock.now()
    const top = ranking(g)
    // En la línea, lo usado de mayor a menor y después la reserva y lo libre, como en macOS.
    const usadas = cats.filter(c => c.kind === 'used').sort((a, b) => b.tokens - a.tokens)
    const enLinea = [...usadas, ...cats.filter(c => c.kind === 'buffer'), ...cats.filter(c => c.kind === 'free')]

    if (e.surface === 'desktop') {
      const { Box, Text, Svg } = $.ui.resolve(e)
      if (m === null) return <Text dimColor>Esperando la primera respuesta…</Text>
      return (
        <Box flexDirection="column" gap={1} paddingX={1}>
          <Box flexDirection="column">
            <Box flexDirection="row" justifyContent="space-between">
              <Text bold>Contexto</Text>
              <Text dimColor>
                {m.tokens === undefined ? abreviar(m.window) : `${abreviar(m.tokens)} de ${abreviar(m.window)}`}
              </Text>
            </Box>
            <Svg source={lineaContexto(enLinea, m.percent)} alt={`Contexto ${m.percent ?? '—'} %`} />
            {usadas.length > 0 ? (
              <Svg
                source={leyenda(usadas)}
                alt={usadas.map(c => `${CATEGORIAS[c.name] ?? c.name} ${abreviar(c.tokens)}`).join(', ')}
              />
            ) : null}
            <Text dimColor>{m.percent === undefined ? '' : `${m.percent} % usado`}</Text>
          </Box>

          <Svg source={SEPARACION} alt="" />

          {m.limites.map(l => (
            <Box key={l.kind} flexDirection="column">
              <Box flexDirection="row" justifyContent="space-between">
                <Text bold>{NOMBRES[l.kind] ?? 'Otro límite'}</Text>
                <Text dimColor>{l.percentUsed} %</Text>
              </Box>
              <Svg source={lineaGris(l.percentUsed)} alt={`${NOMBRES[l.kind] ?? 'Otro límite'} ${l.percentUsed} %`} />
              {l.resetsAt ? <Text dimColor>Se renueva {horaRenovacion(l.resetsAt, ahora)}</Text> : null}
            </Box>
          ))}

          {top.length > 0 ? <Svg source={SEPARACION} alt="" /> : null}
          {top.length > 0 ? (
            <Box flexDirection="column">
              <Text bold>Qué gastó más en esta sesión</Text>
              {top.map(r => (
                <Box key={r.origen} flexDirection="row" justifyContent="space-between">
                  <Text dimColor>{r.origen}</Text>
                  <Text dimColor>{r.pct} %</Text>
                </Box>
              ))}
              {top[0]!.origen.startsWith('/') ? (
                <Text dimColor italic>
                  {top[0]!.origen} es lo que más gasta: se puede correr o acotar con un modelo más barato.
                </Text>
              ) : null}
            </Box>
          ) : null}
        </Box>
      )
    }

    const { Box, Text } = $.ui.resolve(e)
    if (m === null) return <Text dimColor>Esperando la primera respuesta…</Text>
    return (
      <Box flexDirection="column">
        <Text>
          <Text bold>Contexto </Text>
          <Text dimColor>{m.percent === undefined ? '—' : `${m.percent} %`}</Text>
        </Text>
        <Text color={COLOR_CATEGORIA.Messages}>{barra(m.percent)}</Text>
        {m.limites.map(l => (
          <Box key={l.kind} flexDirection="column">
            <Text>
              <Text bold>{NOMBRES[l.kind] ?? 'Otro límite'} </Text>
              <Text dimColor>{l.percentUsed} %</Text>
            </Text>
            <Text dimColor>{barra(l.percentUsed)}</Text>
            {l.resetsAt ? <Text dimColor>Se renueva {horaRenovacion(l.resetsAt, ahora)}</Text> : null}
          </Box>
        ))}
        {top.map(r => (
          <Text key={r.origen} dimColor>
            {r.origen} {r.pct} %
          </Text>
        ))}
      </Box>
    )
  })
}

// ======================= Panel «Pendientes» =======================


// Panel «Pendientes»: la lista de .claude/PENDIENTES.md de la CARPETA de la sesión (la carpeta misma
// o la raíz de su repo git) siempre a la vista, a la derecha, como el panel «Uso»..
// SOLO LEE el archivo. Los «Cambios» salen de git.

const P_PANEL = 'pendientes'
const P_TITULO = 'Pendientes'
const ARCHIVO = '.claude/PENDIENTES.md'
const CADA = 30_000

const datos = atom({ plugin: 'paneles', key: 'datos' } as const, null)
const abierto = atom({ plugin: 'paneles', key: 'abierto' } as const, false)
// IDs de las filas desplegadas para ver su detalle.
const detalle = atom({ plugin: 'paneles', key: 'detalle' } as const, [])

const COLUMNAS = ['ID', 'Pendiente', 'Prio', 'Estado', 'Depende de', 'Esf.', 'Quién', 'Origen']
const ESTADOS = ['pendiente', 'en curso', 'hecho']
// «espera dato de <alguien>» / «espera OK de <alguien>»: lo que está parado esperando una respuesta.
const esperaRespuesta = (estado: string): boolean => /^espera (dato|OK) de \S/.test(estado)
const estadoValido = (estado: string): boolean => ESTADOS.includes(estado) || esperaRespuesta(estado)
const MAX_CAMBIOS = 8

// Colores del sistema de Apple, sin flúor.
// Naranja = espera una respuesta. Rojo suave = algo falló. Todo lo demás, en gris.
const NARANJA = '#FF9F0A'
const ROJO = '#FF453A'
const P_SEPARADOR = 'rgba(142,142,147,0.28)'

// Argentina no cambia de hora: UTC-3 todo el año.
const P_ART_MS = 3 * 60 * 60 * 1000
const DIA_MS = 24 * 60 * 60 * 1000
const MESES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']

const P_ANCHO = 300
const P_SEPARACION = `<svg xmlns="http://www.w3.org/2000/svg" width="${P_ANCHO}" height="1" viewBox="0 0 ${P_ANCHO} 1"><rect width="${P_ANCHO}" height="1" fill="${P_SEPARADOR}"/></svg>`

// ---------- Lectura del archivo ----------

// Parte una fila de tabla en celdas; un «|» dentro de `código` no separa.
function celdas(linea: string): string[] {
  const t = linea.trim()
  if (!t.startsWith('|')) return []
  const salida: string[] = []
  let actual = ''
  let codigo = false
  for (const ch of t.slice(1)) {
    if (ch === '`') codigo = !codigo
    if (ch === '|' && !codigo) {
      salida.push(actual.trim())
      actual = ''
    } else {
      actual += ch
    }
  }
  if (actual.trim() !== '') salida.push(actual.trim())
  return salida
}

function esSeparador(c: string[]): boolean {
  return c.length > 0 && c.every(x => /^:?-{3,}:?$/.test(x))
}

function sinMarcas(s: string): string {
  return s.replace(/\*\*(.+?)\*\*/g, '$1').replace(/`([^`]*)`/g, '$1')
}

// Una línea corta: el título en negrita si lo hay; si no, hasta el primer «:», «. » o «(».
function corto(texto: string): string {
  const negrita = /^\*\*(.+?)\*\*/.exec(texto)
  let t = negrita?.[1] ?? sinMarcas(texto)
  if (!negrita) {
    const corte = [': ', '. ', ' ('].map(s => t.indexOf(s)).filter(i => i > 0)
    if (corte.length > 0) t = t.slice(0, Math.min(...corte))
  }
  t = sinMarcas(t).trim()
  return t.length > 70 ? `${t.slice(0, 69).trimEnd()}…` : t
}

type Fecha = { y: number; mo: number; d?: number; h?: number; mi?: number; texto: string }

type Lectura = {
  filas: Fila[]
  fechas: Fecha[] | null
  // Fecha (AAAA-MM-DD) de la última línea fechada de «Cambios».
  ultima?: string
  nombres: Record<string, string>
  problemas: string[]
}

function analizar(texto: string): Lectura {
  const filas: Fila[] = []
  const fechas: Fecha[] = []
  const nombres: Record<string, string> = {}
  const problemas: string[] = []
  const vistas = new Set<string>()
  const conTabla = new Set<string>()
  let hayFechas = false
  let ultima: string | undefined
  let modo: 'fila' | 'fechas' | 'cambios' | 'otro' = 'otro'
  let letra = ''
  let cabecera = false
  let columnasOk = true

  texto.split('\n').forEach((linea, i) => {
    const titulo = /^##\s+(.*)$/.exec(linea)
    if (titulo) {
      const t = titulo[1] ?? ''
      const seccion = /^([A-Z])\s*·\s*(.+)$/.exec(t)
      if (seccion) {
        modo = 'fila'
        letra = seccion[1] ?? ''
        nombres[letra] = (seccion[2] ?? '').trim()
      } else {
        modo = /^Fechas\b/.test(t) ? 'fechas' : /^Cambios\b/.test(t) ? 'cambios' : 'otro'
      }
      cabecera = false
      columnasOk = true
      return
    }
    if (/^(<{7}|>{7})/.test(linea) && !problemas.some(x => x.startsWith('El archivo tiene marcas de conflicto'))) {
      problemas.push(`El archivo tiene marcas de conflicto de git (línea ${i + 1}): dos sesiones editaron lo mismo y hay que resolverlo a mano.`)
    }
    if (modo === 'cambios') {
      const m = /^\s*(?:[-*]\s*)?(\d{4}-\d{2}-\d{2})\b/.exec(linea)
      if (m && (ultima === undefined || (m[1] ?? '') > ultima)) ultima = m[1]
      return
    }
    if (modo === 'otro' || !linea.trimStart().startsWith('|')) return
    const c = celdas(linea)
    if (esSeparador(c)) return

    if (modo === 'fechas') {
      if (!cabecera) {
        cabecera = true
        hayFechas = true
        if (c[0] !== 'Fecha' || c[1] !== 'Qué') problemas.push('La tabla «Fechas» no tiene las columnas Fecha | Qué.')
        columnasOk = c[0] === 'Fecha' && c[1] === 'Qué'
        return
      }
      if (!columnasOk) return
      const m = /^(\d{4})-(\d{2})(?:-(\d{2}))?(?:\s+(\d{1,2}):(\d{2}))?$/.exec(c[0] ?? '')
      if (c.length !== 2 || !m) {
        problemas.push(`«Fechas», línea ${i + 1}: no entiendo la fila.`)
        return
      }
      fechas.push({
        y: Number(m[1]),
        mo: Number(m[2]),
        d: m[3] === undefined ? undefined : Number(m[3]),
        h: m[4] === undefined ? undefined : Number(m[4]),
        mi: m[5] === undefined ? undefined : Number(m[5]),
        texto: sinMarcas(c[1] ?? ''),
      })
      return
    }

    // Tabla de pendientes de una sección.
    if (!cabecera) {
      cabecera = true
      conTabla.add(letra)
      columnasOk = c.length === COLUMNAS.length && COLUMNAS.every((x, k) => c[k] === x)
      if (!columnasOk) problemas.push(`Sección ${letra}: la tabla no tiene las columnas ${COLUMNAS.join(' | ')}.`)
      return
    }
    if (!columnasOk) return
    const id = c[0] ?? `línea ${i + 1}`
    if (c.length !== COLUMNAS.length) {
      problemas.push(`${id}: tiene ${c.length} columnas y tiene que tener ${COLUMNAS.length}.`)
      return
    }
    const prio = Number(c[2])
    const estado = c[3] ?? ''
    if (!/^[A-Z]\d+$/.test(id)) {
      problemas.push(`Línea ${i + 1}: «${id}» no es un ID válido.`)
      return
    }
    if (prio !== 1 && prio !== 2 && prio !== 3) {
      problemas.push(`${id}: la prioridad «${c[2]}» no es 1, 2 ni 3.`)
      return
    }
    if (!estadoValido(estado)) {
      problemas.push(`${id}: el estado «${estado}» no es uno de los conocidos.`)
      return
    }
    if (vistas.has(id)) {
      problemas.push(`${id}: el mismo número está en dos filas (dos sesiones lo crearon a la vez). Cambiale el número a la más nueva.`)
      return
    }
    vistas.add(id)
    filas.push({
      id,
      texto: corto(c[1] ?? ''),
      prio,
      estado,
      quien: sinMarcas(c[6] ?? ''),
      completo: sinMarcas(c[1] ?? ''),
      depende: sinMarcas(c[4] ?? ''),
      esfuerzo: sinMarcas(c[5] ?? ''),
      origen: sinMarcas(c[7] ?? ''),
      desbloquea: [],
      seccion: letra,
    })
  })

  // Quién desbloquea a quién: si la columna «Depende de» de una fila nombra un ID, esa fila lo espera.
  for (const f of filas) {
    for (const otra of filas) {
      if (otra.id !== f.id && new RegExp(`(^|[^A-Za-z0-9])${f.id}([^A-Za-z0-9]|$)`).test(otra.depende)) f.desbloquea.push(otra.id)
    }
  }

  for (const l of Object.keys(nombres)) {
    if (!conTabla.has(l)) problemas.push(`Sección ${l}: no encontré su tabla.`)
  }
  return { filas, fechas: hayFechas ? fechas : null, ultima, nombres, problemas }
}

// ---------- Próxima fecha ----------

function diaART(ms: number): number {
  const d = new Date(ms - P_ART_MS)
  return Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate())
}

const dos = (n: number): string => String(n).padStart(2, '0')

// Hasta cuándo vale la fecha: la hora exacta, o el final del día / del mes si no trae hora.
function finDe(f: Fecha): number {
  if (f.d !== undefined && f.h !== undefined) return Date.UTC(f.y, f.mo - 1, f.d, f.h, f.mi ?? 0) + P_ART_MS
  if (f.d !== undefined) return Date.UTC(f.y, f.mo - 1, f.d + 1) + P_ART_MS
  return Date.UTC(f.y, f.mo, 1) + P_ART_MS
}

function etiquetaFecha(f: Fecha, ahora: number): string {
  if (f.d === undefined) return `${MESES[f.mo - 1] ?? f.mo} ${f.y}`
  const dias = Math.round((Date.UTC(f.y, f.mo - 1, f.d) - diaART(ahora)) / DIA_MS)
  const dia = dias === 0 ? 'hoy' : dias === 1 ? 'mañana' : `el ${f.d}/${f.mo}`
  const hora = f.h === undefined ? '' : ` ${dos(f.h)}:${dos(f.mi ?? 0)}`
  return `${dia}${hora}${dias > 1 ? ` (en ${dias} días)` : ''}`
}

function proximaFecha(fechas: Fecha[], ahora: number): Proxima | undefined {
  let mejor: Fecha | undefined
  for (const f of fechas) {
    if (finDe(f) > ahora && (mejor === undefined || finDe(f) < finDe(mejor))) mejor = f
  }
  return mejor ? { cuando: etiquetaFecha(mejor, ahora), texto: mejor.texto } : undefined
}

// ---------- Cambios (git) ----------
// git corre en la carpeta de la sesión, que puede ser un repo ajeno: un `.git/config` con `core.fsmonitor=<comando>` ejecutaría ese comando al hacer `git status`.
// Se apagan las dos opciones que lanzan programas o escriben caché (F11 del security check 0.35.0). Todas las llamadas a git de este archivo pasan por acá.
const GIT_SEGURO = ['--no-optional-locks', '-c', 'core.fsmonitor=false', '-c', 'core.untrackedCache=false']


function comparar(vieja: Fila[], nueva: Fila[]): Cambio[] {
  const antes = new Map(vieja.map(f => [f.id, f]))
  const ahora = new Map(nueva.map(f => [f.id, f]))
  const nuevos: Cambio[] = []
  const cerrados: Cambio[] = []
  const prios: Cambio[] = []
  const estados: Cambio[] = []
  const sacados: Cambio[] = []
  for (const f of nueva) {
    const a = antes.get(f.id)
    if (!a) {
      nuevos.push({ tipo: 'nuevo', id: f.id, texto: f.texto, detalle: `prio ${f.prio}` })
      continue
    }
    if (a.estado !== f.estado) {
      if (f.estado === 'hecho') cerrados.push({ tipo: 'cerrado', id: f.id, texto: f.texto })
      else estados.push({ tipo: 'estado', id: f.id, texto: f.texto, detalle: `${a.estado} → ${f.estado}` })
    }
    if (a.prio !== f.prio) prios.push({ tipo: 'prio', id: f.id, texto: f.texto, detalle: `prio ${a.prio} → ${f.prio}` })
  }
  for (const a of vieja) {
    if (!ahora.has(a.id)) sacados.push({ tipo: 'sacado', id: a.id, texto: a.texto })
  }
  return [...nuevos, ...cerrados, ...prios, ...estados, ...sacados]
}

// Días desde la última línea fechada de «Cambios» (undefined si no hay ninguna).
function diasDesde(iso: string | undefined, ahora: number): number | undefined {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso ?? '')
  if (!m) return undefined
  return Math.max(0, Math.round((diaART(ahora) - Date.UTC(Number(m[1]), Number(m[2]) - 1, Number(m[3]))) / DIA_MS))
}

function diaCorto(iso: string | undefined): string | undefined {
  const m = /^\d{4}-(\d{2})-(\d{2})$/.exec(iso ?? '')
  return m ? `${Number(m[2])}/${Number(m[1])}` : iso
}

// La versión de comparación: si el archivo tiene cambios sin guardar, la última guardada;
// si no, la anterior a la última. Todo sale de `git log` del archivo.
async function cambiosDeGit($: EngineInterface, repo: string, nueva: Fila[]): Promise<Cambios> {
  const git = (args: string[]) => $.process.run(['git', ...GIT_SEGURO, '-C', repo, ...args])
  try {
    const estado = await git(['status', '--porcelain', '--', ARCHIVO])
    // Carpeta que no es repo git (código 128): no hay historial, no es un error.
    if (estado.exitCode === 128 && /not a git repository/.test(estado.stderr)) return { estado: 'sin-anterior', lista: [], extra: 0 }
    if (estado.exitCode !== 0) throw new Error(estado.stderr.trim().split('\n')[0] || `git terminó con ${estado.exitCode}`)
    const log = await git(['log', '--format=%H %cs', '-n', '2', '--', ARCHIVO])
    if (log.exitCode !== 0) throw new Error(log.stderr.trim().split('\n')[0] || `git terminó con ${log.exitCode}`)
    const versiones = log.stdout.trim().split('\n').filter(Boolean)
    const sucio = estado.stdout.trim() !== ''
    const base = (sucio ? versiones[0] : versiones[1])?.split(' ')
    if (!base || !base[0]) return { estado: 'sin-anterior', lista: [], extra: 0 }
    const viejo = await git(['show', `${base[0]}:./${ARCHIVO}`])
    if (viejo.exitCode !== 0) throw new Error(viejo.stderr.trim().split('\n')[0] || 'no pude leer la versión anterior')
    const todos = comparar(analizar(viejo.stdout).filas, nueva)
    return {
      estado: 'ok',
      lista: todos.slice(0, MAX_CAMBIOS),
      extra: Math.max(0, todos.length - MAX_CAMBIOS),
      desde: base[1],
      sucio,
    }
  } catch (err) {
    return { estado: 'error', lista: [], extra: 0, error: err instanceof Error ? err.message : String(err) }
  }
}

// ---------- Armado del modelo ----------

const VACIO: Cambios = { estado: 'sin-anterior', lista: [], extra: 0 }

function modeloConError(error: string): Modelo {
  return { error, problemas: [], ahora: [], semana: [], despues: [], hechos: 0, nombres: {}, cambios: VACIO, hayFechas: false }
}

function modeloSinLista(): Modelo {
  return { sinLista: true, problemas: [], ahora: [], semana: [], despues: [], hechos: 0, nombres: {}, cambios: VACIO, hayFechas: false }
}

let ultimaClave = ''
let ultimosCambios: Cambios = VACIO

// Busca .claude/PENDIENTES.md en la carpeta de la sesión y, si no está, en la raíz de su repo git.
async function buscar($: EngineInterface, carpeta: string): Promise<{ repo: string; texto: string } | null> {
  const candidatas: string[] = []
  const agregar = (c: string) => {
    if (c !== '' && c !== '/' && !candidatas.includes(c)) candidatas.push(c)
  }
  let cwd = ''
  try {
    cwd = await $.session.cwd()
  } catch {
    // queda solo la raíz
  }
  for (const inicio of [carpeta, cwd]) {
    let c = inicio
    for (let nivel = 0; nivel < 4 && c !== '' && c !== '/'; nivel++) {
      agregar(c)
      c = c.slice(0, c.lastIndexOf('/'))
    }
  }
  try {
    const top = await $.process.run(['git', ...GIT_SEGURO, '-C', carpeta, 'rev-parse', '--show-toplevel'])
    const raiz = top.exitCode === 0 ? top.stdout.trim() : ''
    if (raiz !== '') agregar(raiz)
  } catch {
    // sin git: se usan solo las carpetas
  }
  for (const repo of candidatas) {
    try {
      return { repo, texto: await $.fs.read(`${repo}/${ARCHIVO}`) }
    } catch {
      // no está acá; se prueba la siguiente
    }
  }
  return null
}

async function refrescar($: EngineInterface): Promise<void> {
  try {
    const ahora = await $.clock.now()
    const carpeta = await $.session.root()
    let modelo: Modelo
    const hallada = await buscar($, carpeta)
    if (hallada === null) {
      modelo = modeloSinLista()
    } else {
      const { repo, texto } = hallada
      const l = analizar(texto)
      if (l.filas.length === 0) {
        const detalle = l.problemas.length > 0 ? ` ${l.problemas[0]}` : ' No encontré ninguna fila de pendientes.'
        modelo = modeloConError(`No pude leer PENDIENTES.md:${detalle}`)
      } else {
        // El historial se vuelve a pedir solo si cambió el archivo o la carpeta.
        const clave = `${repo}:${texto.length}:${texto}`
        if (clave !== ultimaClave) {
          ultimosCambios = await cambiosDeGit($, repo, l.filas)
          ultimaClave = clave
        }
        const abiertas = l.filas.filter(f => f.estado !== 'hecho')
        modelo = {
          problemas: l.problemas,
          ahora: abiertas.filter(f => f.prio === 1),
          semana: abiertas.filter(f => f.prio === 2),
          despues: abiertas.filter(f => f.prio === 3),
          hechos: l.filas.length - abiertas.length,
          nombres: l.nombres,
          cambios: ultimosCambios,
          proxima: l.fechas ? proximaFecha(l.fechas, ahora) : undefined,
          hayFechas: l.fechas !== null,
          dias: diasDesde(l.ultima, ahora),
          // Si la lista salió de una carpeta de arriba (la sesión entró a una subcarpeta), el panel dice de cuál.
          desde: repo !== carpeta ? repo : undefined,
        }
      }
    }
    // Se compara con lo que tiene la app guardado, no con una copia de este módulo: si la app reinicia sus valores
    // y el módulo sigue con su copia, comparar contra la copia dejaba el panel vacío hasta que cambiara el archivo.
    const enApp = await $.state.get({ plugin: 'paneles', key: 'datos' } as const)
    if (JSON.stringify(enApp.value ?? null) !== JSON.stringify(modelo)) await update($, datos, () => modelo)
  } catch {
    // Este refresco se llama sin esperar (void): si hasta avisar el error falla, no puede quedar un rechazo suelto.
    try {
      await update($, datos, () => modeloConError('El panel no pudo actualizarse esta vez. Se reintenta solo en 30 segundos.'))
    } catch {
      // se reintenta en el próximo ciclo
    }
  }
}

// ---------- Dibujo ----------

const colorDe = (estado: string): string | undefined =>
  esperaRespuesta(estado) ? NARANJA : undefined

const ICONO: Record<Cambio['tipo'], string> = { nuevo: '＋', cerrado: '✓', prio: '↕', estado: '→', sacado: '–' }
const VERBO: Record<Cambio['tipo'], string> = {
  nuevo: 'Nuevo',
  cerrado: 'Cerrado',
  prio: 'Cambió de prioridad',
  estado: 'Cambió de estado',
  sacado: 'Salió de la lista',
}

// Ver uCerrado / uAsegurar (Uso): mismo motivo.
let pCerrado = false

async function pAsegurar($: EngineInterface): Promise<void> {
  if (pCerrado) return
  try {
    await $.ui.open({ id: P_PANEL, title: P_TITULO, columns: 38 })
  } catch {
    // se reintenta con el próximo mensaje
  }
}

const pendSessionStart: H = async ($, e, next) => {
  const ran = await next(e)
  pCerrado = false
  ultimaClave = ''
  await $.command.register({ name: 'pendientes', description: 'Abre el panel de pendientes (PENDIENTES.md)' })
  // El reloj va ANTES de leer nada: si una lectura (git) se cuelga, el panel igual se refresca después.
  $.clock.every(CADA, () => refrescar($))
  void pAsegurar($)
  void refrescar($)
  return ran
}

const pendPromptSubmit: H = async ($, e, next) => {
  await pAsegurar($)
  void refrescar($)
  return next(e)
}

const pendSessionMeasure: H = async ($, e, next) => {
  await refrescar($)
  return next(e)
}

const registrarPendientes: Register = on => {

  on('ui.close', { id: P_PANEL }, async ($, e, next) => {
    if (e.origin.kind === 'person') pCerrado = true
    return next(e)
  }).catch(($, e, next) => next(e))

  on('command.run', { command: 'pendientes' }, async $ => {
    pCerrado = false
    await $.ui.open({ id: P_PANEL, title: P_TITULO, columns: 38 })
    await refrescar($)
    return { text: 'Panel de pendientes abierto.' }
  })

  // Además del reloj, se relee al enviar un mensaje y al terminar cada turno.


  on('ui.render', { component: 'Pane', requestId: P_PANEL }, async ($, e) => {
    const ui = $.ui.resolve(e)
    const { Box, Text, Button } = ui
    const m = await read($, datos)
    const desplegado = (await read($, abierto)) ?? false
    const abiertas = (await read($, detalle)) ?? []
    const Linea = e.surface === 'desktop' && 'Svg' in ui ? ui.Svg : null
    const sep = (k: string) => (Linea ? <Linea key={k} source={P_SEPARACION} alt="" /> : null)

    if (m === null) return <Text dimColor>Leyendo PENDIENTES.md…</Text>
    if (m.sinLista) {
      return (
        <Box flexDirection="column" paddingX={1}>
          <Text>Esta carpeta no tiene lista de pendientes todavía.</Text>
          <Text dimColor>Para tener una, creá el archivo .claude/PENDIENTES.md en esta carpeta.</Text>
        </Box>
      )
    }
    if (m.error) {
      return (
        <Box flexDirection="column" paddingX={1}>
          <Text color={ROJO}>{m.error}</Text>
          <Text dimColor>Revisá el formato de las tablas en .claude/PENDIENTES.md de esta carpeta.</Text>
        </Box>
      )
    }

    const dato = (titulo: string, valor: string) => (
      <Text>
        <Text dimColor>{titulo}: </Text>
        {valor}
      </Text>
    )
    // Una fila: el título se toca para ver de qué se trata, de qué depende y qué desbloquea.
    const fila = (f: Fila, siempreEstado: boolean) => {
      const color = colorDe(f.estado)
      const desplegada = abiertas.includes(f.id)
      return (
        <Box key={f.id} flexDirection="column">
          <Button
            key={`fila-${f.id}`}
            label={`${desplegada ? '▾' : '▸'} ${f.id} ${f.texto}`}
            plain
            onPress={() =>
              update($, detalle, l => {
                const lista = l ?? []
                return lista.includes(f.id) ? lista.filter(i => i !== f.id) : [...lista, f.id]
              })
            }
          />
          {siempreEstado || f.estado !== 'pendiente' ? (
            <Text color={color} dimColor={color === undefined} bold={color !== undefined}>
              {'  '}
              {color ? '● ' : ''}
              {f.estado}
              {siempreEstado ? <Text dimColor> · {f.quien}</Text> : null}
            </Text>
          ) : null}
          {desplegada ? (
            <Box flexDirection="column" paddingLeft={2}>
              <Text>{f.completo}</Text>
              {f.estado.startsWith('espera dato') ? <Text color={NARANJA}>Necesita un dato para avanzar.</Text> : null}
              {f.estado.startsWith('espera OK') ? <Text color={NARANJA}>Necesita un OK para avanzar.</Text> : null}
              {dato('Depende de', f.depende === '—' || f.depende === '' ? 'nada, se puede hacer ya' : f.depende)}
              {f.desbloquea.length > 0 ? dato('Desbloquea', f.desbloquea.join(', ')) : null}
              {dato('Esfuerzo', f.esfuerzo)}
              {dato('Quién', f.quien)}
              {dato('Viene de', f.origen)}
            </Box>
          ) : null}
        </Box>
      )
    }

    const esperan = m.ahora.filter(f => esperaRespuesta(f.estado)).length
    const porSeccion: { letra: string; filas: Fila[] }[] = []
    for (const f of m.semana) {
      const grupo = porSeccion.find(g => g.letra === f.seccion)
      if (grupo) grupo.filas.push(f)
      else porSeccion.push({ letra: f.seccion, filas: [f] })
    }

    return (
      <Box flexDirection="column" gap={1} paddingX={1}>
        {m.problemas.length > 0 ? (
          <Box flexDirection="column">
            <Text color={ROJO}>
              No pude leer bien PENDIENTES.md ({m.problemas.length} {m.problemas.length === 1 ? 'problema' : 'problemas'}):
            </Text>
            {m.problemas.slice(0, 3).map((p, i) => (
              <Text key={`p${i}`} dimColor>
                {p}
              </Text>
            ))}
            {m.problemas.length > 3 ? <Text dimColor>y {m.problemas.length - 3} más</Text> : null}
          </Box>
        ) : null}

        {m.dias === undefined ? (
          <Text color={ROJO}>No encuentro la fecha de la última actualización (falta una línea fechada en «Cambios»).</Text>
        ) : (
          <Text color={m.dias > 7 ? ROJO : undefined} dimColor={m.dias <= 7}>
            {m.dias === 0 ? 'Actualizada hoy' : m.dias === 1 ? 'Actualizada hace 1 día' : `Actualizada hace ${m.dias} días`}
            {m.dias > 7 ? ' · puede estar vieja' : ''}
          </Text>
        )}

        {m.desde !== undefined ? <Text dimColor>Lista de {m.desde}</Text> : null}

        <Text dimColor>Tocá un título para ver el detalle.</Text>

        <Box flexDirection="column">
          <Box flexDirection="row" justifyContent="space-between">
            <Text bold>Ahora</Text>
            <Text dimColor>{m.ahora.length}</Text>
          </Box>
          <Text dimColor>Prio 1 · lo que va primero</Text>
          {esperan > 0 ? (
            <Text color={NARANJA}>
              {esperan === 1 ? 'Hay 1 esperando un dato o un OK' : `Hay ${esperan} esperando un dato o un OK`}
            </Text>
          ) : null}
          {m.ahora.length === 0 ? <Text dimColor>Nada urgente.</Text> : null}
          {m.ahora.map(f => fila(f, true))}
        </Box>

        {sep('s1')}

        <Box flexDirection="column">
          <Box flexDirection="row" justifyContent="space-between">
            <Text bold>Esta semana</Text>
            <Text dimColor>{m.semana.length}</Text>
          </Box>
          <Text dimColor>Prio 2 · para esta semana</Text>
          {m.semana.length === 0 ? <Text dimColor>Nada para esta semana.</Text> : null}
          {porSeccion.map(g => (
            <Box key={g.letra} flexDirection="column">
              <Text dimColor>{m.nombres[g.letra] ?? g.letra}</Text>
              {g.filas.map(f => fila(f, false))}
            </Box>
          ))}
        </Box>

        {sep('s2')}

        <Box flexDirection="column">
          <Text bold>Cambios</Text>
          {m.cambios.estado === 'error' ? (
            <Text color={ROJO}>No pude leer el historial de git, así que no se ven los Cambios. La lista sí.</Text>
          ) : m.cambios.estado === 'sin-anterior' ? (
            <Text dimColor>Todavía no hay una versión anterior en git para comparar.</Text>
          ) : (
            <Box flexDirection="column">
              <Text dimColor>
                {m.cambios.sucio ? 'Contra la última versión guardada' : 'Contra la versión anterior'}
                {m.cambios.desde ? ` (${diaCorto(m.cambios.desde)})` : ''}
              </Text>
              {m.cambios.lista.length === 0 ? <Text dimColor>Sin cambios.</Text> : null}
              {m.cambios.lista.map(c => (
                <Box key={`${c.tipo}${c.id}`} flexDirection="column">
                  <Text>
                    <Text dimColor>{ICONO[c.tipo]} </Text>
                    <Text bold>{c.id} </Text>
                    {c.texto}
                  </Text>
                  <Text dimColor>
                    {'  '}
                    {VERBO[c.tipo]}
                    {c.detalle ? ` · ${c.detalle}` : ''}
                  </Text>
                </Box>
              ))}
              {m.cambios.extra > 0 ? <Text dimColor>y {m.cambios.extra} más</Text> : null}
            </Box>
          )}
        </Box>

        {sep('s3')}

        <Box flexDirection="column">
          <Text bold>Próxima fecha</Text>
          {!m.hayFechas ? (
            <Text color={ROJO}>No encontré la tabla «Fechas» en el archivo.</Text>
          ) : m.proxima ? (
            <Box flexDirection="column">
              <Text>{m.proxima.cuando}</Text>
              <Text dimColor>{m.proxima.texto}</Text>
            </Box>
          ) : (
            <Text dimColor>No quedan fechas por delante.</Text>
          )}
        </Box>

        {sep('s4')}

        <Box flexDirection="column">
          <Button
            key="despues"
            plain
            label={`${desplegado ? '▾' : '▸'} Después · ${m.despues.length}`}
            onPress={() => update($, abierto, a => !(a ?? false))}
          />
          {desplegado
            ? [<Text key="p3" dimColor>Prio 3 · espera cupo o una decisión</Text>, ...m.despues.map(f => fila(f, false))]
            : null}
        </Box>
      </Box>
    )
  })
}


// ---------- Panel «Tareas» ----------
// Las tareas de ESTA sesión, en vivo. Se alimenta de las llamadas que la propia sesión hace a
// TodoWrite / TaskCreate / TaskUpdate, o de <carpeta>/.claude/tareas.json si existe. Hechas = tachadas.
const T_PANEL = 'tareas-sesion'
const tLista = atom({ plugin: 'paneles', key: 'tareasLista' } as const, [])
// null = no hay archivo.
const tArchivo = atom({ plugin: 'paneles', key: 'tareasArchivo' } as const, null)
const T_ARCHIVO = '.claude/tareas.json'
const T_CADA = 3_000
const T_ESTADOS = ['pending', 'in_progress', 'completed']
// Tareas que salen de PENDIENTES.md + git (ver abajo). null = la carpeta no tiene lista.
// Carpeta de la que salió la lista cuando no es la de la sesión (una de arriba). null = la de la sesión.
const tOrigen = atom({ plugin: 'paneles', key: 'tareasOrigen' } as const, null)
const derivadas = atom({ plugin: 'paneles', key: 'tareasDerivadas' } as const, null)

// ---------- Tareas derivadas de PENDIENTES.md + git ----------
// El panel se arma solo: en curso → ▶, pendientes de prioridad 1 (y nuevos de prioridad 2) → ○, y lo cerrado desde la
// versión anterior del archivo (según git) → ✓. Lo que está en tareas.json con el mismo ID se reemplaza: PENDIENTES manda.
const TP_ARCHIVO = '.claude/PENDIENTES.md'
const TP_MAX = 15
const TP_DIAS_HECHO = 2

type TpFila = { id: string; texto: string; prio: number; estado: string }

function tpCeldas(linea: string): string[] {
  const t = linea.trim()
  if (!t.startsWith('|')) return []
  const salida: string[] = []
  let actual = ''
  let codigo = false
  for (const ch of t.slice(1)) {
    if (ch === '`') codigo = !codigo
    if (ch === '|' && !codigo) {
      salida.push(actual.trim())
      actual = ''
    } else {
      actual += ch
    }
  }
  if (actual.trim() !== '') salida.push(actual.trim())
  return salida
}

function tpCorto(texto: string): string {
  const sin = (s: string) => s.replace(/\*\*(.+?)\*\*/g, '$1').replace(/`([^`]*)`/g, '$1')
  const negrita = /^\*\*(.+?)\*\*/.exec(texto)
  let t = negrita?.[1] ?? sin(texto)
  if (!negrita) {
    const corte = [': ', '. ', ' ('].map(s => t.indexOf(s)).filter(i => i > 0)
    if (corte.length > 0) t = t.slice(0, Math.min(...corte))
  }
  t = sin(t).trim()
  return t.length > 60 ? `${t.slice(0, 59).trimEnd()}…` : t
}

function tpFilas(texto: string): TpFila[] {
  const filas: TpFila[] = []
  for (const linea of texto.split('\n')) {
    const c = tpCeldas(linea)
    if (c.length < 8 || !/^[A-Z]\d+$/.test(c[0] ?? '')) continue
    filas.push({ id: c[0] ?? '', texto: tpCorto(c[1] ?? ''), prio: Number(c[2]), estado: c[3] ?? '' })
  }
  return filas
}

// viejo = la versión anterior del archivo (null si no hay historial). `reciente` = el cambio es de hace poco.
function tpDerivar(nuevo: string, viejo: string | null, reciente: boolean): Tarea[] {
  const antes = new Map(tpFilas(viejo ?? '').map(f => [f.id, f]))
  const hay = viejo !== null
  const encurso: Tarea[] = []
  const pendientes: Tarea[] = []
  const hechas: Tarea[] = []
  for (const f of tpFilas(nuevo)) {
    const texto = `${f.id}: ${f.texto}`
    const a = antes.get(f.id)
    if (f.estado === 'en curso') encurso.push({ id: f.id, texto, estado: 'in_progress' })
    else if (f.estado === 'pendiente' && (f.prio === 1 || (f.prio === 2 && hay && !a))) pendientes.push({ id: f.id, texto, estado: 'pending' })
    else if (f.estado === 'hecho' && hay && reciente && a && a.estado !== 'hecho') hechas.push({ id: f.id, texto, estado: 'completed' })
  }
  return [...encurso, ...pendientes, ...hechas].slice(0, TP_MAX)
}

// Quita de la lista manual lo que PENDIENTES ya cubre (mismo ID al principio del texto).
function tpMezclar(manual: Tarea[], derivadas: Tarea[]): Tarea[] {
  const ids = new Set(derivadas.map(t => t.id))
  return [...manual.filter(t => !ids.has(t.texto.replace(':', ' ').split(' ')[0] ?? '')), ...derivadas]
}

let tpUltimoTexto: string | null = null
let tpCache: Tarea[] | null = null

// Lee PENDIENTES.md de la carpeta y la versión anterior en git. null = la carpeta no tiene lista.
async function tpLeer($: EngineInterface, carpeta: string, texto: string): Promise<Tarea[] | null> {
  // Sin cambios en el archivo (ni de carpeta) no se vuelve a llamar a git (esto corre cada pocos segundos).
  const clave = `${carpeta}\0${texto}`
  if (clave === tpUltimoTexto) return tpCache
  let viejo: string | null = null
  let reciente = false
  try {
    const git = (args: string[]) => $.process.run(['git', ...GIT_SEGURO, '-C', carpeta, ...args])
    const estado = await git(['status', '--porcelain', '--', TP_ARCHIVO])
    const log = await git(['log', '--format=%H %cs', '-n', '2', '--', TP_ARCHIVO])
    if (estado.exitCode === 0 && log.exitCode === 0) {
      const v = log.stdout.trim().split('\n').filter(Boolean).map(l => l.split(' '))
      const sucio = estado.stdout.trim() !== ''
      const base = sucio ? v[0] : v[1]
      const fecha = Date.parse(`${(sucio ? 'hoy' : v[0]?.[1]) ?? ''}T12:00:00Z`)
      reciente = sucio || (!Number.isNaN(fecha) && Date.now() - fecha < TP_DIAS_HECHO * 86_400_000 + 43_200_000)
      if (base?.[0]) {
        const r = await git(['show', `${base[0]}:./${TP_ARCHIVO}`])
        if (r.exitCode === 0) viejo = r.stdout
      }
    }
  } catch {
    // sin git: se muestran en curso y prioridad 1, sin lo cerrado
  }
  tpUltimoTexto = clave
  tpCache = tpDerivar(texto, viejo, reciente)
  return tpCache
}


function tLeer(texto: string): Tarea[] | null {
  try {
    const d = JSON.parse(texto) as { tareas?: unknown }
    if (!Array.isArray(d.tareas)) return null
    return d.tareas.flatMap((t, i) => {
      const o = t as { id?: unknown; texto?: unknown; estado?: unknown }
      if (typeof o?.texto !== 'string') return []
      const estado = T_ESTADOS.includes(String(o.estado)) ? (o.estado as Tarea['estado']) : 'pending'
      return [{ id: String(o.id ?? `a${i + 1}`), texto: o.texto, estado }]
    })
  } catch {
    return null
  }
}

// La carpeta de la sesión puede no ser la que tiene el archivo (la sesión entra a un subrepo, o la app la deja en otra).
// Se prueba la raíz, la carpeta de trabajo y sus carpetas madre (hasta 3 niveles); gana la primera que lo tiene.
async function tDonde($: EngineInterface, relativo: string): Promise<{ carpeta: string; texto: string } | null> {
  const vistas = new Set<string>()
  const inicios: string[] = []
  for (const pedir of [() => $.session.root(), () => $.session.cwd()]) {
    try {
      inicios.push(await pedir())
    } catch {
      // esa forma de saber la carpeta no respondió; queda la otra
    }
  }
  for (const inicio of inicios) {
    let c = inicio
    for (let nivel = 0; nivel < 4 && c !== '' && c !== '/'; nivel++) {
      if (!vistas.has(c)) {
        vistas.add(c)
        try {
          return { carpeta: c, texto: await $.fs.read(`${c}/${relativo}`) }
        } catch {
          // no está acá; se prueba la carpeta madre
        }
      }
      c = c.slice(0, c.lastIndexOf('/'))
    }
  }
  return null
}

async function tRefrescar($: EngineInterface): Promise<void> {
  try {
    let nuevo: Tarea[] | null = null
    const dTareas = await tDonde($, T_ARCHIVO)
    if (dTareas !== null) nuevo = tLeer(dTareas.texto)
    // Se compara con lo que tiene la app guardado, no con una copia de este módulo: si la app reinicia sus valores
    // (otra sesión, /clear) y el módulo sigue con su copia, comparar contra la copia dejaba el panel vacío para siempre.
    const enApp = await $.state.get({ plugin: 'paneles', key: 'tareasArchivo' } as const)
    if (JSON.stringify(enApp.value ?? null) !== JSON.stringify(nuevo)) await update($, tArchivo, () => nuevo)

    const dPend = await tDonde($, TP_ARCHIVO)
    const der = dPend === null ? null : await tpLeer($, dPend.carpeta, dPend.texto)
    // Si alguna de las dos fuentes salió de una carpeta de arriba, el panel lo dice.
    let raiz = ''
    try {
      raiz = await $.session.root()
    } catch {
      // sin raíz no se puede decir de dónde salió
    }
    const de = [dTareas, dPend].find(d => d !== null && raiz !== '' && d.carpeta !== raiz)?.carpeta ?? null
    const oApp = await $.state.get({ plugin: 'paneles', key: 'tareasOrigen' } as const)
    if ((oApp.value ?? null) !== de) await update($, tOrigen, () => de)
    const derApp = await $.state.get({ plugin: 'paneles', key: 'tareasDerivadas' } as const)
    if (JSON.stringify(derApp.value ?? null) !== JSON.stringify(der)) await update($, derivadas, () => der)
  } catch {
    // se reintenta en el próximo ciclo
  }
}

// Ver uCerrado / uAsegurar (Uso): mismo motivo.
let tCerrado = false

async function tAsegurar($: EngineInterface): Promise<void> {
  if (tCerrado) return
  try {
    await $.ui.open({ id: T_PANEL, title: 'Tareas', columns: 38 })
  } catch {
    // se reintenta con el próximo mensaje
  }
}

const tSessionStart: H = async ($, e, next) => {
  const ran = await next(e)
  tCerrado = false
  tpUltimoTexto = null
  tpCache = null
  await $.command.register({ name: 'tareas', description: 'Abre el panel de tareas de la sesión' })
  // El reloj va ANTES de leer nada: si una lectura se cuelga, el panel igual se refresca después.
  $.clock.every(T_CADA, () => tRefrescar($))
  void tAsegurar($)
  void tRefrescar($)
  return ran
}

// Además del reloj (que en la app puede no latir), Tareas se relee con cada mensaje y al terminar cada turno.
const tPromptSubmit: H = async ($, e, next) => {
  await tAsegurar($)
  await tRefrescar($)
  return next(e)
}

const tRelee: H = async ($, e, next) => {
  await tRefrescar($)
  return next(e)
}

const registrarTareas: Register = on => {
  on('ui.close', { id: T_PANEL }, async ($, e, next) => {
    if (e.origin.kind === 'person') tCerrado = true
    return next(e)
  }).catch(($, e, next) => next(e))

  on('command.run', { command: 'tareas' }, async $ => {
    tCerrado = false
    await $.ui.open({ id: T_PANEL, title: 'Tareas', columns: 38 })
    await tRefrescar($)
    return { text: 'Panel de tareas abierto.' }
  })

  // TodoWrite trae la lista entera cada vez.
  on('tool.call', { tool: 'TodoWrite' }, async ($, e, next) => {
    const ran = await next(e)
    if (ran.deny === undefined && ran.isError !== true) {
      const nueva: Tarea[] = e.todos.map((t, i) => ({ id: `t${i + 1}`, texto: t.content, estado: t.status }))
      await update($, tLista, () => nueva)
    }
    return ran
  }).catch(($, e, next) => next(e))

  // TaskCreate: el id lo da el resultado.
  on('tool.call', { tool: 'TaskCreate' }, async ($, e, next) => {
    const ran = await next(e)
    if (ran.deny === undefined && ran.isError !== true) {
      const id = String(ran.result?.task?.id ?? `n${Date.now()}`)
      await update($, tLista, l => [...(l ?? []).filter(t => t.id !== id), { id, texto: e.subject, estado: 'pending' as const }])
    }
    return ran
  }).catch(($, e, next) => next(e))

  on('tool.call', { tool: 'TaskUpdate' }, async ($, e, next) => {
    const ran = await next(e)
    if (ran.deny === undefined && ran.isError !== true) {
      await update($, tLista, l =>
        (l ?? [])
          .filter(t => !(t.id === e.taskId && e.status === 'deleted'))
          .map(t =>
            t.id === e.taskId
              ? { ...t, texto: e.subject ?? t.texto, estado: e.status && e.status !== 'deleted' ? e.status : t.estado }
              : t,
          ),
      )
    }
    return ran
  }).catch(($, e, next) => next(e))

  on('ui.render', { component: 'Pane', requestId: T_PANEL }, async ($, e) => {
    const { Box, Text } = $.ui.resolve(e)
    const deArchivo = await read($, tArchivo)
    // El archivo manda cuando existe; si no, valen las llamadas a TodoWrite/TaskCreate.
    const manual = deArchivo ?? (await read($, tLista)) ?? []
    const tareas = tpMezclar(manual, (await read($, derivadas)) ?? [])
    const hechas = tareas.filter(t => t.estado === 'completed').length
    return (
      <Box flexDirection="column" paddingX={1} gap={1}>
        {(await read($, tOrigen)) != null ? <Text dimColor>Lista de {await read($, tOrigen)}</Text> : null}
        <Text dimColor>
          {tareas.length === 0 ? 'Sin tareas todavía.' : `${hechas} de ${tareas.length} hechas`}
        </Text>
        {tareas.map(t => (
          <Text key={t.id} strikethrough={t.estado === 'completed'} dimColor={t.estado === 'completed'} bold={t.estado === 'in_progress'}>
            {t.estado === 'completed' ? '✓' : t.estado === 'in_progress' ? '▶' : '○'} {t.texto}
          </Text>
        ))}
      </Box>
    )
  })
}

export const register: Register = on => {
  on('session.start', ($, e, next) => usoSessionStart($, e, e2 => pendSessionStart($, e2, e3 => tSessionStart($, e3, next)))).catch(($, e, next) => next(e))
  on('command.run', ($, e, next) => usoCommandRun($, e, next)).catch(($, e, next) => next(e))
  on('prompt.submit', ($, e, next) => usoPromptSubmit($, e, e2 => pendPromptSubmit($, e2, e3 => tPromptSubmit($, e3, next)))).catch(($, e, next) => next(e))
  on('session.measure', ($, e, next) => usoSessionMeasure($, e, e2 => pendSessionMeasure($, e2, e3 => tRelee($, e3, next))))
  registrarUso(on)
  registrarPendientes(on)
  registrarTareas(on)
}
