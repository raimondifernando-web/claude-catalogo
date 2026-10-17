import { atom, read, update } from 'claude-code'
import type { EngineInterface, Register, SessionContextUsage, SessionRateLimit } from 'claude-code'

import type { ActModelo, ActNodo, ActSesion, ActSinUso, Tarea, Categoria, Cambio, Cambios, Fila, Gasto, Limite, Medida, Modelo, Proxima } from '../types'

// Plugin «paneles»: tres paneles a la derecha, «Uso», «Tareas y pendientes» (uno solo) y «Actividad». Un plugin tiene un solo
// módulo de hooks y no admite dos hooks del mismo evento sin filtro, y `$` no cruza archivos:
// por eso van juntos acá, y los hooks de los dos paneles se encadenan al final.


// Panel propio «Uso»: lo mismo que el circulito de uso de la app (contexto de esta
// sesión por categoría + límites del plan) y qué gastó más, siempre a la vista.
// Estilo macOS (como Almacenamiento): solo la línea del contexto lleva color; el resto, en grises.
// Hook sin filtro: lo registra register.tsx (un solo hook por evento en todo el plugin).
type H = ($: EngineInterface, e: any, next: (e: any) => any) => any // eslint-disable-line @typescript-eslint/no-explicit-any

const PANEL = 'medidor-uso'
const TITULO = 'Uso y actividad'
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
    const actividad = (await actDibujar($, e)) as never
    // En la línea, lo usado de mayor a menor y después la reserva y lo libre, como en macOS.
    const usadas = cats.filter(c => c.kind === 'used').sort((a, b) => b.tokens - a.tokens)
    const enLinea = [...usadas, ...cats.filter(c => c.kind === 'buffer'), ...cats.filter(c => c.kind === 'free')]

    if (e.surface === 'desktop') {
      const { Box, Text, Svg, Button } = $.ui.resolve(e)
      if (m === null) return <Text dimColor>Esperando la primera respuesta…</Text>
      const abierta = (await read($, leyendaAbierta)) === true
      return (
        <Box flexDirection="column" gap={0}>
          <Box flexDirection="column" gap={0} paddingX={1}>
          <Box flexDirection="column">
            <Box flexDirection="row" justifyContent="space-between">
              <Text bold>Contexto</Text>
              <Text dimColor>
                {m.tokens === undefined ? abreviar(m.window) : `${abreviar(m.tokens)} de ${abreviar(m.window)}`}
              </Text>
            </Box>
            <Svg source={lineaContexto(enLinea, m.percent)} alt={`Contexto ${m.percent ?? '—'} %`} />
            {usadas.length > 0 ? (
              <Button key="leyenda" plain label={`${abierta ? '⌄' : '›'} Detalle del contexto`} onPress={() => update($, leyendaAbierta, v => v !== true)} />
            ) : null}
            {usadas.length > 0 && abierta ? (
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
          {actividad}
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
        {actividad}
      </Box>
    )
  })
}

// ======================= Panel «Pendientes» =======================


// Panel «Pendientes»: la lista de .claude/PENDIENTES.md de la CARPETA de la sesión (la carpeta misma
// o la raíz de su repo git) siempre a la vista, a la derecha, como el panel «Uso»..
// SOLO LEE el archivo. Los «Cambios» salen de git.

const P_PANEL = 'pendientes'

// Panel «Tareas y pendientes» (unifica los mods tareas-sesion y pendientes, 2026-10-16). Arriba, «Esta sesión»: las
// tareas de la sesión (.claude/tareas.json y las llamadas a TodoWrite/TaskCreate). Abajo, «Pendientes que arrastramos»:
// la lista de .claude/PENDIENTES.md de la CARPETA de la sesión (la carpeta misma o la raíz de su repo git). Lo que
// está en las dos listas se MARCA abajo («en sesión»), no se esconde. SOLO LEE los archivos. Los «Cambios» salen de git.
const UN_PANEL = 'pendientes'
const UN_TITULO = 'Tareas y pendientes'
const ARCHIVO_TAREAS = '.claude/tareas.json'
const ARCHIVO = '.claude/PENDIENTES.md'
const CADA = 5_000

const datos = atom({ plugin: 'paneles', key: 'datos' } as const, null)
// Grupos de prioridad desplegados (p1 siempre se ve; p2 y p3 arrancan plegados).
const grupos = atom({ plugin: 'paneles', key: 'grupos' } as const, [])
// Tareas que la propia sesión carga con TodoWrite / TaskCreate (valen si no hay tareas.json).
const lista = atom({ plugin: 'paneles', key: 'lista' } as const, [])
// Detalle de colores del contexto (los puntitos): plegado hasta que se toca.
const leyendaAbierta = atom({ plugin: 'paneles', key: 'leyendaAbierta' } as const, false)
// IDs de las filas desplegadas para ver su detalle.
const detalle = atom({ plugin: 'paneles', key: 'detalle' } as const, [])

const COLUMNAS = ['ID', 'Pendiente', 'Prio', 'Estado', 'Depende de', 'Esf.', 'Quién', 'Origen']
const ESTADOS = ['pendiente', 'en curso', 'espera dato de F', 'espera OK de F', 'hecho']
const ESTADOS_TAREA = ['pending', 'in_progress', 'completed']
const MAX_CAMBIOS = 8
// Topes: un archivo enorme o con miles de filas no tiene que colgar el panel (se corta, no se rechaza).
const MAX_TEXTO = 300_000
const MAX_FILAS = 500
const MAX_TAREAS = 200
// git corre en la carpeta de la sesión, que puede ser un repo ajeno: un `.git/config` con `core.fsmonitor=<comando>` ejecutaría ese comando al hacer `git status`.
// Se apagan las dos opciones que lanzan programas o escriben caché (F11 del security check 0.35.0). Todas las llamadas a git de este archivo pasan por acá.
const GIT_SEGURO = ['--no-optional-locks', '-c', 'core.fsmonitor=false', '-c', 'core.untrackedCache=false']

// Colores del sistema de Apple, sin flúor: lo que depende de Fernando se destaca.
// Naranja = te toca a vos. Rojo suave = algo falló. Todo lo demás, en gris.
const NARANJA = '#FF9F0A'
const ROJO = '#FF453A'
const UN_SEPARADOR = 'rgba(142,142,147,0.28)'

// Argentina no cambia de hora: UTC-3 todo el año.
const DIA_MS = 24 * 60 * 60 * 1000
const MESES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic']

const UN_ANCHO = 300
const UN_SEPARACION = `<svg xmlns="http://www.w3.org/2000/svg" width="${UN_ANCHO}" height="1" viewBox="0 0 ${UN_ANCHO} 1"><rect width="${UN_ANCHO}" height="1" fill="${UN_SEPARADOR}"/></svg>`

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
    if (!ESTADOS.includes(estado)) {
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
  const d = new Date(ms - ART_MS)
  return Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate())
}

const dos = (n: number): string => String(n).padStart(2, '0')

// Hasta cuándo vale la fecha: la hora exacta, o el final del día / del mes si no trae hora.
function finDe(f: Fecha): number {
  if (f.d !== undefined && f.h !== undefined) return Date.UTC(f.y, f.mo - 1, f.d, f.h, f.mi ?? 0) + ART_MS
  if (f.d !== undefined) return Date.UTC(f.y, f.mo - 1, f.d + 1) + ART_MS
  return Date.UTC(f.y, f.mo, 1) + ART_MS
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
  return { sesion: null, error, problemas: [], ahora: [], semana: [], despues: [], hechos: 0, nombres: {}, cambios: VACIO, hayFechas: false }
}

function modeloSinLista(): Modelo {
  return { sesion: null, sinLista: true, problemas: [], ahora: [], semana: [], despues: [], hechos: 0, nombres: {}, cambios: VACIO, hayFechas: false }
}

let ultimaClave = ''
let ultimosCambios: Cambios = VACIO

// Busca el archivo en la carpeta de la sesión, en su carpeta de trabajo y en la raíz de SU repo git.
// Nunca en las carpetas madre: podrían ser de otro proyecto o de otro cliente (0.3.1).
async function buscar($: EngineInterface, carpeta: string, archivo: string = ARCHIVO): Promise<{ repo: string; texto: string } | null> {
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
    if (inicio === '') continue
    agregar(inicio)
    try {
      const top = await $.process.run(['git', ...GIT_SEGURO, '-C', inicio, 'rev-parse', '--show-toplevel'])
      const raiz = top.exitCode === 0 ? top.stdout.trim() : ''
      if (raiz !== '') agregar(raiz)
    } catch {
      // sin git: se usa solo la carpeta
    }
  }
  for (const repo of candidatas) {
    try {
      const crudo = await $.fs.read(`${repo}/${archivo}`)
      return { repo, texto: crudo.length > MAX_TEXTO ? crudo.slice(0, crudo.lastIndexOf('\n', MAX_TEXTO)) : crudo }
    } catch {
      // no está acá; se prueba la siguiente
    }
  }
  return null
}

// Lee .claude/tareas.json. null = no hay archivo o no se entiende.
function leerTareas(texto: string): Tarea[] | null {
  try {
    const d = JSON.parse(texto) as { tareas?: unknown }
    if (!Array.isArray(d.tareas)) return null
    return d.tareas.slice(0, MAX_TAREAS).flatMap((t, i) => {
      const o = t as { id?: unknown; texto?: unknown; estado?: unknown }
      if (typeof o?.texto !== 'string') return []
      const estado = ESTADOS_TAREA.includes(String(o.estado)) ? (o.estado as Tarea['estado']) : 'pending'
      return [{ id: String(o.id ?? `a${i + 1}`), texto: o.texto, estado }]
    })
  } catch {
    return null
  }
}

async function refrescar($: EngineInterface): Promise<void> {
  try {
    const ahora = await $.clock.now()
    const carpeta = await $.session.root()
    let modelo: Modelo
    const deTareas = await buscar($, carpeta, ARCHIVO_TAREAS)
    const sesion = deTareas === null ? null : leerTareas(deTareas.texto)
    const hallada = await buscar($, carpeta)
    if (hallada === null) {
      modelo = modeloSinLista()
    } else {
      const { repo, texto } = hallada
      const l = analizar(texto)
      l.filas = l.filas.slice(0, MAX_FILAS)
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
          sesion,
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
    if (modelo.sesion === null && sesion !== null) modelo = { ...modelo, sesion }
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
  estado === 'espera dato de F' || estado === 'espera OK de F' ? NARANJA : undefined

const ICONO: Record<Cambio['tipo'], string> = { nuevo: '＋', cerrado: '✓', prio: '↕', estado: '→', sacado: '–' }
const VERBO: Record<Cambio['tipo'], string> = {
  nuevo: 'Nuevo',
  cerrado: 'Cerrado',
  prio: 'Cambió de prioridad',
  estado: 'Cambió de estado',
  sacado: 'Salió de la lista',
}

// Un panel que se abre «solo» (sin que la persona lo pida) no se dibuja por debajo de 144 columnas, ni si todavía no hay
// ventana (sesiones que abre /cerrar). Un open que responde al mensaje de la persona (PaneOpenArgs) se dibuja con
// cualquier ancho, pero solo cuenta como «pedido» si se hace DENTRO del hook de prompt.submit, esperado (await) antes de
// devolver. Por eso el open va primero y sin consultar nada antes (consultar $.ui.panes() primero dejaba el open
// para después de que el hook ya había vuelto). Abrir un id ya abierto solo lo retitula, así que se hace con cada mensaje.
// Si la persona lo cierra a mano, no se vuelve a abrir solo.
let cerradoAMano = false
// Sesiones que abre /cerrar (start_session): el open de session.start y el de prompt.submit (mensajes inyectados, no de la
// persona) ocurren SIN ventana y quedan sin dibujar (isPlaced false). Si la persona después abre la sesión y no escribe
// nada, nada vuelve a pedirlos y los paneles quedan vacíos. Por eso se recuerda si el panel quedó dibujado y, mientras no,
// se reintenta con el reloj y al terminar cada turno (sin pedido de la persona se dibuja desde 144 columnas).
let colocado = false

async function asegurarPanel($: EngineInterface): Promise<void> {
  if (cerradoAMano) return
  try {
    const r = await $.ui.open({ id: UN_PANEL, title: UN_TITULO, columns: 38 })
    colocado = r.isPlaced
  } catch {
    // se reintenta con el próximo mensaje
  }
}


const unSessionStart: H = async ($, e, next) => {
    const ran = await next(e)
    cerradoAMano = false
    colocado = false
    ultimaClave = ''
    await $.command.register({ name: 'pendientes', description: 'Abre el panel de tareas y pendientes' })
    // «/pendientes» choca con la skill /metodo:pendientes (que solo imprime la tabla); «/tareas» abre el panel sin ambigüedad.
    await $.command.register({ name: 'tareas', description: 'Abre el panel de tareas y pendientes' })
    // El reloj va ANTES de leer nada: si una lectura (git) se cuelga, el panel igual se refresca después.
    $.clock.every(CADA, () => {
      if (!colocado) void asegurarPanel($)
      return refrescar($)
    })
    void asegurarPanel($)
    void refrescar($)
    return ran
}

const unPromptSubmit: H = async ($, e, next) => {
    await asegurarPanel($)
    void refrescar($)
    return next(e)
}

const unSessionMeasure: H = async ($, e, next) => {
    if (!colocado) await asegurarPanel($)
    await refrescar($)
    return next(e)
}

const registrarUnico: Register = on => {
  on('ui.close', { id: UN_PANEL }, async ($, e, next) => {
    if (e.origin.kind === 'person') cerradoAMano = true
    return next(e)
  }).catch(($, e, next) => next(e))

  on('command.run', { command: 'pendientes' }, async $ => {
    cerradoAMano = false
    await $.ui.open({ id: UN_PANEL, title: UN_TITULO, columns: 38 })
    await refrescar($)
    return { text: 'Panel de tareas y pendientes abierto.' }
  })

  on('command.run', { command: 'tareas' }, async $ => {
    cerradoAMano = false
    await $.ui.open({ id: UN_PANEL, title: UN_TITULO, columns: 38 })
    await refrescar($)
    return { text: 'Panel de tareas y pendientes abierto.' }
  })

  // Las tareas que la propia sesión carga: TodoWrite trae la lista entera; TaskCreate/TaskUpdate, de a una.
  on('tool.call', { tool: 'TodoWrite' }, async ($, e, next) => {
    const ran = await next(e)
    if (ran.deny === undefined && ran.isError !== true) {
      const nueva: Tarea[] = e.todos.map((t, i) => ({ id: `t${i + 1}`, texto: t.content, estado: t.status }))
      await update($, lista, () => nueva)
    }
    return ran
  }).catch(($, e, next) => next(e))

  on('tool.call', { tool: 'TaskCreate' }, async ($, e, next) => {
    const ran = await next(e)
    if (ran.deny === undefined && ran.isError !== true) {
      const id = String(ran.result?.task?.id ?? `n${Date.now()}`)
      await update($, lista, l => [...(l ?? []).filter(t => t.id !== id), { id, texto: e.subject, estado: 'pending' as const }])
    }
    return ran
  }).catch(($, e, next) => next(e))

  on('tool.call', { tool: 'TaskUpdate' }, async ($, e, next) => {
    const ran = await next(e)
    if (ran.deny === undefined && ran.isError !== true) {
      await update($, lista, l =>
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

  on('ui.render', { component: 'Pane', requestId: UN_PANEL }, async ($, e) => {
    const ui = $.ui.resolve(e)
    const { Box, Text, Button } = ui
    const m = await read($, datos)
    const abiertos = (await read($, grupos)) ?? []
    const desplegadas = (await read($, detalle)) ?? []
    const deSesion = (await read($, lista)) ?? []
    const Linea = e.surface === 'desktop' && 'Svg' in ui ? ui.Svg : null
    const sep = (k: string) => (Linea ? <Linea key={k} source={UN_SEPARACION} alt="" /> : null)

    if (m === null) return <Text dimColor>Leyendo tareas y pendientes…</Text>

    // ---------- Esta sesión: tareas.json manda; si no hay, valen TodoWrite/TaskCreate ----------
    const tareas = m.sesion ?? deSesion
    const enCurso = tareas.filter(t => t.estado === 'in_progress')
    const porHacer = tareas.filter(t => t.estado === 'pending')
    const hechasS = tareas.filter(t => t.estado === 'completed')
    const idsSesion = new Set(tareas.map(t => t.id))
    const lineaTarea = (t: Tarea) => (
      <Text key={`t-${t.id}`} strikethrough={t.estado === 'completed'} dimColor={t.estado === 'completed'} bold={t.estado === 'in_progress'}>
        {ICONO_ESTADO[t.estado]} {t.texto}
        {/^[A-Z]\d+$/.test(t.id) ? <Text dimColor>{'  '}{t.id}</Text> : null}
      </Text>
    )
    const bloqueSesion = (
      <Box flexDirection="column" gap={1}>
        <Text dimColor>ESTA SESIÓN</Text>
        {tareas.length === 0 ? (
          <Text dimColor>Sin tareas todavía.</Text>
        ) : (
          <Text dimColor>
            {enCurso.length} en curso · {porHacer.length} por hacer · {hechasS.length} {hechasS.length === 1 ? 'hecha' : 'hechas'}
          </Text>
        )}
        {enCurso.length > 0 ? (
          <Box flexDirection="column">
            <Text bold>En curso</Text>
            {enCurso.map(lineaTarea)}
          </Box>
        ) : null}
        {porHacer.length > 0 ? (
          <Box flexDirection="column">
            <Box flexDirection="row" justifyContent="space-between">
              <Text bold>Por hacer</Text>
              <Text dimColor>{porHacer.length}</Text>
            </Box>
            {porHacer.map(lineaTarea)}
          </Box>
        ) : null}
        {hechasS.length > 0 ? (
          <Box flexDirection="column">
            <Box flexDirection="row" justifyContent="space-between">
              <Text bold>Hechas</Text>
              <Text dimColor>{hechasS.length}</Text>
            </Box>
            {hechasS.map(lineaTarea)}
          </Box>
        ) : null}
      </Box>
    )

    // ---------- Pendientes que arrastramos ----------
    let bloquePend: JSX.Element
    if (m.sinLista) {
      bloquePend = (
        <Box flexDirection="column">
          <Text>Esta carpeta no tiene lista de pendientes todavía.</Text>
          <Text dimColor>Se arma sola con /cerrar (queda en .claude/PENDIENTES.md).</Text>
        </Box>
      )
    } else if (m.error) {
      bloquePend = (
        <Box flexDirection="column">
          <Text color={ROJO}>{m.error}</Text>
          <Text dimColor>Revisá el formato de las tablas en .claude/PENDIENTES.md de esta carpeta.</Text>
        </Box>
      )
    } else {
      bloquePend = renderPendientes($, ui, m, abiertos, desplegadas, idsSesion, sep)
    }

    return (
      <Box flexDirection="column" gap={1} paddingX={1}>
        {bloqueSesion}
        {sep('sb')}
        {bloquePend}
      </Box>
    )
  })
}

const dato = (Text: any, titulo: string, valor: string) => (
  <Text>
    <Text dimColor>{titulo}: </Text>
    {valor}
  </Text>
)

// Icono de estado de una tarea de la sesión.
const ICONO_ESTADO: Record<Tarea['estado'], string> = { pending: '○', in_progress: '◐', completed: '✅' }

const iconoDe = (estado: string): string =>
  estado === 'espera dato de F' || estado === 'espera OK de F' ? '✋' : estado === 'en curso' ? '◐' : estado === 'hecho' ? '✅' : '○'

// Una fila depende de otra si su columna «Depende de» nombra el ID de la otra y esa otra sigue abierta en el mismo grupo.
function agrupar(filas: Fila[]): { fila: Fila; hijas: Fila[] }[] {
  const ids = new Set(filas.map(f => f.id))
  const padreDe = new Map<string, string>()
  for (const f of filas) {
    const p = filas.find(o => o.id !== f.id && ids.has(o.id) && new RegExp(`(^|[^A-Za-z0-9])${o.id}([^A-Za-z0-9]|$)`).test(f.depende))
    if (p) padreDe.set(f.id, p.id)
  }
  // Solo un nivel: si el padre también espera a otra, la fila queda al nivel de arriba (evita ciclos y sangrías sin fin).
  const arriba = filas.filter(f => !padreDe.has(f.id) || padreDe.has(padreDe.get(f.id) ?? ''))
  return arriba.map(f => ({ fila: f, hijas: filas.filter(h => padreDe.get(h.id) === f.id && !padreDe.has(f.id)) }))
}

function renderPendientes(
  $: EngineInterface,
  ui: ReturnType<EngineInterface['ui']['resolve']>,
  m: Modelo,
  abiertos: string[],
  desplegadas: string[],
  idsSesion: Set<string>,
  sep: (k: string) => JSX.Element | null,
): JSX.Element {
  const { Box, Text, Button } = ui
  const fila = (f: Fila, sangria: boolean) => {
    const color = colorDe(f.estado)
    const abierta = desplegadas.includes(f.id)
    const enSesion = idsSesion.has(f.id)
    return (
      <Box key={f.id} flexDirection="column" paddingLeft={sangria ? 2 : 0}>
        <Box flexDirection="row" gap={1}>
          {sangria ? <Text dimColor>↳</Text> : null}
          <Text color={color} dimColor={color === undefined && f.estado !== 'en curso'}>
            {iconoDe(f.estado)}
          </Text>
          <Button
            key={`fila-${f.id}`}
            label={`${f.texto}  ${f.id}${enSesion ? ' · en sesión' : ''} ${abierta ? '⌄' : '›'}`}
            plain
            onPress={() =>
              update($, detalle, l => {
                const lst = l ?? []
                return lst.includes(f.id) ? lst.filter(i => i !== f.id) : [...lst, f.id]
              })
            }
          />
        </Box>
        {f.estado === 'espera dato de F' || f.estado === 'espera OK de F' ? (
          <Text color={NARANJA} bold>
            {'    '}te llama: {f.estado === 'espera dato de F' ? 'falta un dato tuyo' : 'falta tu OK'}
          </Text>
        ) : null}
        {abierta ? (
          <Box flexDirection="column" paddingLeft={4}>
            <Text>{f.completo}</Text>
            {f.estado === 'espera dato de F' ? <Text color={NARANJA}>Necesita un dato tuyo para avanzar.</Text> : null}
            {f.estado === 'espera OK de F' ? <Text color={NARANJA}>Necesita tu OK para avanzar.</Text> : null}
            {dato(Text, 'Depende de', f.depende === '—' || f.depende === '' ? 'nada, se puede hacer ya' : f.depende)}
            {f.desbloquea.length > 0 ? dato(Text, 'Desbloquea', f.desbloquea.join(', ')) : null}
            {dato(Text, 'Esfuerzo', f.esfuerzo)}
            {dato(Text, 'Quién', f.quien)}
            {dato(Text, 'Viene de', f.origen)}
          </Box>
        ) : null}
      </Box>
    )
  }
  const lista = (filas: Fila[]) =>
    agrupar(filas).map(g => (
      <Box key={g.fila.id} flexDirection="column">
        {fila(g.fila, false)}
        {g.hijas.map(h => fila(h, true))}
      </Box>
    ))
  const alternar = (id: string) => update($, grupos, a => ((a ?? []).includes(id) ? (a ?? []).filter(x => x !== id) : [...(a ?? []), id]))
  // Grupo de prioridad: el título es el botón; la prioridad no lleva símbolo.
  const grupo = (id: string, titulo: string, filas: Fila[], siempreAbierto: boolean, nota?: string) => {
    const abierto = siempreAbierto || abiertos.includes(id)
    return (
      <Box flexDirection="column">
        {siempreAbierto ? (
          <Box flexDirection="row" justifyContent="space-between">
            <Text bold>{titulo}</Text>
            <Text dimColor>{filas.length}</Text>
          </Box>
        ) : (
          <Button key={id} plain label={`${abierto ? '⌄' : '›'} ${titulo} · ${filas.length}`} onPress={() => alternar(id)} />
        )}
        {abierto && nota ? <Text dimColor>{nota}</Text> : null}
        {abierto && filas.length === 0 ? <Text dimColor>Nada por acá.</Text> : null}
        {abierto ? lista(filas) : null}
      </Box>
    )
  }

  const esperan = m.ahora.filter(f => f.estado === 'espera dato de F' || f.estado === 'espera OK de F').length

  return (
    <Box flexDirection="column" gap={1}>
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

      <Text dimColor>PENDIENTES QUE ARRASTRAMOS</Text>
      {m.dias === undefined ? (
        <Text color={ROJO}>No encuentro la fecha de la última actualización (falta una línea fechada en «Cambios»).</Text>
      ) : (
        <Text color={m.dias > 7 ? ROJO : undefined} dimColor={m.dias <= 7}>
          {m.dias === 0 ? 'Actualizada hoy' : m.dias === 1 ? 'Actualizada hace 1 día' : `Actualizada hace ${m.dias} días`}
          {m.dias > 7 ? ' · puede estar vieja' : ''}
        </Text>
      )}
      {m.desde !== undefined ? <Text dimColor>Lista de {m.desde}</Text> : null}
      <Text dimColor>Tocá un título para ver el detalle. ✋ = te llama.</Text>

      <Box flexDirection="column">
        {esperan > 0 ? <Text color={NARANJA}>{esperan === 1 ? 'Hay 1 que depende de vos' : `Hay ${esperan} que dependen de vos`}</Text> : null}
        {grupo('p1', 'Prioridad 1 · ahora', m.ahora, true)}
      </Box>

      {sep('s1')}
      {grupo('p2', 'Prioridad 2 · esta semana', m.semana, false, 'Para esta semana')}
      {grupo('p3', 'Prioridad 3 · después', m.despues, false, 'Espera cupo o una decisión')}

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
    </Box>
  )
}

// ───────── Panel «Actividad» (agentes, subagentes y skills) ─────────
// Pedido de Fer (C137): ver, en un panel a la derecha, cuándo se activa un agente,
// subagente o skill. El registro guarda SOLO tipo, nombre, actHora, id actCorto de sesión y
// actCarpeta; nunca el prompt, la descripción ni los argumentos (Mand. XXII). Un archivo
// por día y por sesión: actDos sesiones a la vez nunca se pisan. Un mod no puede borrar:
// los archivos de más de 90 días los poda quien administre la Mac (hoy son livianos).
const actPANEL = 'medidor-uso'
const actTITULO = 'Uso y actividad'
// La actCarpeta del registro sale de la configuración de actCADA persona (nunca una ruta fija).
let actDIR = ''
let actSIN_USO = ''
async function actCarpeta($: EngineInterface): Promise<void> {
  if (actDIR !== '') return
  const cfg = await $.env.get('CLAUDE_CONFIG_DIR').catch(() => undefined)
  const casa = await $.env.get('HOME').catch(() => undefined)
  const base = cfg || (casa ? `${casa}/.claude` : '')
  actDIR = base ? `${base}/actividad` : ''
  actSIN_USO = `${actDIR}/sin-uso.json`
}
const actCADA = 5_000
const actLEE_DIAS = 2
const actSKILL_FRESCA = 20_000
const actACTIVO_MAX = 6 * 3600 * 1000
const actART_MS = 3 * 60 * 60 * 1000
const actDIA_MS = 24 * 3600 * 1000

const actDatos = atom({ plugin: 'paneles', key: 'actividadDatos' } as const, null)

const actVERDE = '#30D158'
const actBARRA = '#3A3A3C'
const actROJO = '#FF453A'
const actAMARILLO = '#FFD60A'


// Dibujos del panel (pantalla de la app): el agente es el Bicho del notch; el subagente, una luciérnaga.
// Verde y animado = trabajando; gris y quieto = terminó. En la terminal no hay dibujos: se cae a ● / ◦.
const actSVG = (cuerpo: string) => `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="22" viewBox="0 0 20 22">${cuerpo}</svg>`
const actBICHO_VERDE = actSVG(
  `<g><animateTransform attributeName="transform" type="translate" values="0 0;0 -1.5;0 0" dur="1s" repeatCount="indefinite"/>` +
    `<path d="M7 4 Q6 1 3.5 .5 M13 4 Q14 1 16.5 .5" stroke="#30D158" stroke-width="1.1" fill="none" stroke-linecap="round"/>` +
    `<circle cx="3.2" cy=".8" r="1.3" fill="#30D158"/><circle cx="16.8" cy=".8" r="1.3" fill="#30D158"/>` +
    `<rect x="2" y="3.5" width="16" height="13" rx="6.5" fill="#1F5A33" stroke="#30D158" stroke-width=".9"/>` +
    `<ellipse cx="7" cy="9.5" rx="2.6" ry="3" fill="#F5F5F7"/><ellipse cx="13" cy="9.5" rx="2.6" ry="3" fill="#F5F5F7"/>` +
    `<circle cx="7.4" cy="9.9" r="1.3" fill="#0F0F10"/><circle cx="12.6" cy="9.9" r="1.3" fill="#0F0F10"/>` +
    `<path d="M5 17 l-1.5 2.5 M10 17 v2.5 M15 17 l1.5 2.5" stroke="#30D158" stroke-width="1.1" stroke-linecap="round"/></g>`,
)
const actBICHO_GRIS = actSVG(
  `<path d="M7 4 Q6 1 3.5 .5 M13 4 Q14 1 16.5 .5" stroke="#636366" stroke-width="1.1" fill="none" stroke-linecap="round"/>` +
    `<circle cx="3.2" cy=".8" r="1.2" fill="#636366"/><circle cx="16.8" cy=".8" r="1.2" fill="#636366"/>` +
    `<rect x="2" y="3.5" width="16" height="13" rx="6.5" fill="#2C2C2E" stroke="#48484A" stroke-width=".8"/>` +
    `<path d="M4.8 9.8 q2.2 1.6 4.4 0 M10.8 9.8 q2.2 1.6 4.4 0" stroke="#8E8E93" stroke-width="1.1" fill="none" stroke-linecap="round"/>` +
    `<path d="M5 17 l-1.5 2.5 M10 17 v2.5 M15 17 l1.5 2.5" stroke="#48484A" stroke-width="1.1" stroke-linecap="round"/>`,
)
const actLUCI_VERDE = actSVG(
  `<ellipse cx="6" cy="6" rx="4.2" ry="2.2" transform="rotate(-25 6 6)" fill="#30D158" opacity=".35"/>` +
    `<ellipse cx="14" cy="6" rx="4.2" ry="2.2" transform="rotate(25 14 6)" fill="#30D158" opacity=".35"/>` +
    `<ellipse cx="10" cy="10" rx="3" ry="5.5" fill="#2E3A31" stroke="#30D158" stroke-width=".8"/>` +
    `<circle cx="10" cy="3.8" r="2" fill="#2E3A31" stroke="#30D158" stroke-width=".8"/>` +
    `<ellipse cx="10" cy="14.4" rx="5.6" ry="5.6" fill="#30D158" opacity=".22"><animate attributeName="opacity" values=".1;.35;.1" dur="1.4s" repeatCount="indefinite"/></ellipse>` +
    `<ellipse cx="10" cy="14.4" rx="3.2" ry="3.4" fill="#30D158"><animate attributeName="opacity" values="1;.55;1" dur="1.4s" repeatCount="indefinite"/></ellipse>` +
    `<path d="M8.8 1.6 Q8 .3 6.8 .2 M11.2 1.6 Q12 .3 13.2 .2" stroke="#30D158" stroke-width=".8" fill="none" stroke-linecap="round"/>`,
)
const actLUCI_GRIS = actSVG(
  `<ellipse cx="6" cy="6" rx="4.2" ry="2.2" transform="rotate(-25 6 6)" fill="#636366" opacity=".25"/>` +
    `<ellipse cx="14" cy="6" rx="4.2" ry="2.2" transform="rotate(25 14 6)" fill="#636366" opacity=".25"/>` +
    `<ellipse cx="10" cy="10" rx="3" ry="5.5" fill="#2C2C2E" stroke="#48484A" stroke-width=".8"/>` +
    `<circle cx="10" cy="3.8" r="2" fill="#2C2C2E" stroke="#48484A" stroke-width=".8"/>` +
    `<ellipse cx="10" cy="14.4" rx="3.2" ry="3.4" fill="#48484A"/>` +
    `<path d="M8.8 1.6 Q8 .3 6.8 .2 M11.2 1.6 Q12 .3 13.2 .2" stroke="#636366" stroke-width=".8" fill="none" stroke-linecap="round"/>`,
)

const actCorto = (s: unknown) => String(s ?? '').slice(0, 80)

// Sesión y actCarpeta de la última conversación vista: la herramienta Skill no las trae.
let actSidActual = ''
let actCwdActual = ''

// Una actCola: actDos eventos casi a la vez (arranque y vínculo de un subagente) no se pisan al escribir.
let actCola: Promise<unknown> = Promise.resolve()

function actAnotar($: EngineInterface, linea: Record<string, unknown>): Promise<void> {
  const t = Date.now()
  const hecho = actCola.then(async () => {
    await actCarpeta($)
    if (actDIR === '') return
    const dia = new Date(t).toISOString().slice(0, 10)
    const sid = String(linea.s ?? '').replace(/[^a-zA-Z0-9_-]/g, '')
    const ruta = `${actDIR}/${dia}-${sid || 'sin-sesion'}.jsonl`
    const previo = await $.fs.read(ruta).catch(() => '')
    await $.fs.write(ruta, `${typeof previo === 'string' ? previo : ''}${JSON.stringify({ t, ...linea })}\n`)
  })
  actCola = hecho.catch(() => undefined)
  return hecho
}

function actALineas(texto: string): Record<string, unknown>[] {
  const out: Record<string, unknown>[] = []
  for (const l of texto.split('\n')) {
    if (l.trim() === '') continue
    try {
      const o = JSON.parse(l)
      if (o && typeof o === 'object') out.push(o as Record<string, unknown>)
    } catch {
      // línea cortada: se ignora
    }
  }
  return out
}

// Pura (se prueba sola): del conjunto de líneas al árbol del panel.
export function actArmar(lineas: Record<string, unknown>[], ahora: number, sinUso?: ActSinUso): ActModelo {
  const paradas = new Map<string, number>()
  // «Terminó» (SubagentStop) llega cuando el agente entrega su informe, aunque siga con trabajo en segundo plano:
  // si el motor lo vio corriendo después de esa parada, la parada no cuenta hasta la próxima.
  const seguia = new Map<string, number>()
  const padres = new Map<string, string>()
  for (const l of lineas) {
    if (l.ev === 'stop' && typeof l.id === 'string' && typeof l.t === 'number') paradas.set(l.id, Math.max(l.t, paradas.get(l.id) ?? 0))
    if (l.ev === 'resume' && typeof l.id === 'string' && typeof l.t === 'number') seguia.set(l.id, Math.max(l.t, seguia.get(l.id) ?? 0))
    if (l.ev === 'link' && typeof l.id === 'string' && typeof l.padre === 'string') padres.set(l.id, l.padre)
  }
  const nodos: ActNodo[] = []
  const porId = new Map<string, ActNodo>()
  for (const l of lineas) {
    if (l.ev !== 'start' || typeof l.t !== 'number') continue
    const tipo = l.tipo === 'skill' ? 'skill' : 'agente'
    const nombre = actCorto(l.n)
    if (nombre === '') continue
    const id = typeof l.id === 'string' ? l.id : undefined
    // El mismo agente puede anotarse dos veces (evento de arranque y recuento del motor): vale la primera.
    if (id !== undefined && porId.has(id)) continue
    const parada = id !== undefined ? paradas.get(id) : undefined
    const fin = parada !== undefined && id !== undefined && (seguia.get(id) ?? 0) > parada ? undefined : parada
    const n: ActNodo = {
      tipo,
      nombre,
      t: l.t,
      dur: fin !== undefined && fin >= l.t ? fin - l.t : undefined,
      activo: false,
      sesion: actCorto(l.s),
      cwd: actCorto(l.cwd).split('/').filter(Boolean).pop() ?? '',
      hijos: [],
    }
    n.activo = tipo === 'agente' && fin === undefined && ahora - l.t < actACTIVO_MAX
    const padre = id !== undefined ? padres.get(id) : typeof l.por === 'string' ? l.por : undefined
    ;(n as ActNodo & { _p?: string })._p = padre
    if (id !== undefined) porId.set(id, n)
    nodos.push(n)
  }
  const raices: ActNodo[] = []
  for (const n of nodos) {
    const padre = (n as ActNodo & { _p?: string })._p
    const sup = padre !== undefined && padre !== 'main' ? porId.get(padre) : undefined
    if (sup && sup !== n) sup.hijos.push(n)
    else raices.push(n)
  }
  for (const n of nodos) {
    delete (n as ActNodo & { _p?: string })._p
    n.hijos.sort((a, b) => a.t - b.t)
    // Una skill cuenta como «trabajando» un rato, mientras su agente sigue activo.
    if (n.tipo === 'skill') n.activo = ahora - n.t < actSKILL_FRESCA
  }
  // Un agente sigue «trabajando» si él o algo de lo que colgó lo está.
  const vivo = (n: ActNodo): boolean => n.activo || n.hijos.some(vivo)
  const cuenta = (n: ActNodo): number => (n.activo ? 1 : 0) + n.hijos.reduce((x, h) => x + cuenta(h), 0)
  const inicioHoy = Math.floor((ahora - actART_MS) / actDIA_MS) * actDIA_MS + actART_MS
  raices.sort((a, b) => b.t - a.t)
  const agrupar = (lista: ActNodo[]): ActSesion[] => {
    const por = new Map<string, ActSesion>()
    for (const r of lista) {
      const k = r.sesion || '-'
      const g = por.get(k) ?? { sesion: k, cwd: r.cwd, raices: [] }
      g.raices.push(r)
      por.set(k, g)
    }
    return [...por.values()]
  }
  return {
    ahora: agrupar(raices.filter(vivo)),
    hoy: agrupar(raices.filter(r => !vivo(r) && r.t >= inicioHoy).slice(0, 12)),
    trabajando: raices.reduce((x, r) => x + cuenta(r), 0),
    sinUso,
  }
}

// Agentes ya anotados como «empezó» por este módulo.
const actVistos = new Set<string>()
// Agentes con una parada anotada y todavía sin reanudar.
const actParados = new Set<string>()

// El aviso «empezó» (SubagentStart) no llega para todos: los agentes que lanza una skill
// o se reanudan con un mensaje terminan (SubagentStop) sin haber avisado que empezaron, y el
// panel nunca los mostraba encendidos. Y «terminó» llega al entregar el informe, aunque el
// agente siga con trabajo en segundo plano. Por eso, cada vez que un agente empieza un turno o
// usa una herramienta (eventos con su id), se anota: si es nuevo, arranque; si figuraba parado, reanuda.
// Solo el tipo, nunca la descripción.
async function actAvisarVivo($: EngineInterface, agentId: string | undefined): Promise<void> {
  if (agentId === undefined) return
  const id = actCorto(agentId)
  if (actVistos.has(id)) {
    if (actParados.delete(id)) {
      await actAnotar($, { s: actSidActual, ev: 'resume', id })
      void actRefrescar($)
    }
    return
  }
  actVistos.add(id)
  let tipo = ''
  let padre = 'main'
  try {
    const a = (await $.agent.list()).find(x => x.id === agentId)
    // Los trabajos internos del motor (resumir la conversación, memoria) llevan un id que la lista no nombra: no son agentes para mostrar.
    if (a === undefined) return
    tipo = actCorto(a.type)
    padre = a.parentId ?? 'main'
  } catch {
    // sin la lista: queda como «agente»
  }
  await actAnotar($, { s: actSidActual, ev: 'start', tipo: 'agente', n: tipo || 'agente', id, cwd: actCwdActual })
  await actAnotar($, { s: actSidActual, ev: 'link', id, padre })
  void actRefrescar($)
}

async function actRefrescar($: EngineInterface): Promise<void> {
  try {
    await actCarpeta($)
    if (actDIR === '') throw new Error('No encuentro la actCarpeta de Claude de esta Mac.')
    const ahora = await $.clock.now()
    const archivos = await $.fs.list(actDIR).catch(() => [])
    const lineas: Record<string, unknown>[] = []
    for (const f of archivos) {
      if (f.kind !== 'file' || !f.name.endsWith('.jsonl')) continue
      if (ahora - f.mtimeMs > actLEE_DIAS * actDIA_MS) continue
      const txt = await $.fs.read(`${actDIR}/${f.name}`).catch(() => '')
      if (typeof txt === 'string') for (const l of actALineas(txt)) lineas.push(l)
    }
    let sinUso: ActSinUso | undefined
    try {
      const r = await $.fs.read(actSIN_USO)
      const o = JSON.parse(typeof r === 'string' ? r : '{}')
      if (typeof o.sin === 'number' && typeof o.total === 'number') sinUso = { dias: Number(o.dias) || 30, sin: o.sin, total: o.total, generado: String(o.generado ?? '') }
    } catch {
      // todavía no se corrió sin-activar
    }
    await update($, actDatos, () => actArmar(lineas, ahora, sinUso)).catch(() => undefined)
  } catch (err) {
    await update($, actDatos, () => ({ ahora: [], hoy: [], trabajando: 0, error: String((err as Error)?.message ?? err) })).catch(() => undefined)
  }
}

let actCerradoAMano = false
let actColocado = false

async function actAsegurarPanel(_$: EngineInterface): Promise<void> {
  // Actividad vive dentro del panel de Uso («Uso y actividad»): ese panel ya lo abre el de Uso.
  actColocado = true
}

const actDos = (n: number) => String(n).padStart(2, '0')
function actHora(ms: number): string {
  const d = new Date(ms - actART_MS)
  return `${actDos(d.getUTCHours())}:${actDos(d.getUTCMinutes())}`
}
function actHace(ms: number): string {
  const s = Math.max(0, Math.round(ms / 1000))
  if (s < 60) return `${s} s`
  if (s < 3600) return `${Math.round(s / 60)} min`
  return `${Math.floor(s / 3600)} h ${actDos(Math.round((s % 3600) / 60))} min`
}


export const actSessionStart: H = async ($, e, next) => {
  const ran = await next(e)
  actCerradoAMano = false
  actColocado = false
  await $.command.register({ name: 'actividad', description: 'Abre el panel de actividad de agentes y skills' })
  $.clock.every(actCADA, () => {
    if (!actColocado) void actAsegurarPanel($)
    return actRefrescar($)
  })
  void actAsegurarPanel($)
  void actRefrescar($)
  return ran
}

export const actPromptSubmit: H = async ($, e, next) => {
  await actAsegurarPanel($)
  void actRefrescar($)
  return next(e)
}

// Se relee también al terminar cada turno.
export const actSessionMeasure: H = async ($, e, next) => {
  if (!actColocado) await actAsegurarPanel($)
  await actRefrescar($)
  return next(e)
}

// Lo de «Actividad» que se dibuja abajo del panel de Uso (un solo panel: «Uso y actividad»).
async function actDibujar($: EngineInterface, e: any): Promise<unknown> { // eslint-disable-line @typescript-eslint/no-explicit-any
  const ui = $.ui.resolve(e)
  const { Box, Text } = ui
  const m = await read($, actDatos)
  const ahora = await $.clock.now()
  if (m === null) return <Text dimColor>Leyendo la actividad…</Text>
  if (m.error) return <Text color={actROJO}>{m.error}</Text>

  const Dibujo = e.surface === 'desktop' && 'Svg' in ui ? ui.Svg : null
  // El dibujo de cada fila: Bicho (agente), luciérnaga (subagente) o hoja de archivo (skill).
  const icono = (n: ActNodo, nivel: number) => {
    if (n.tipo === 'skill') return <Text color={n.activo ? actVERDE : undefined} dimColor={!n.activo}>▤ </Text>
    const luciernaga = nivel > 0
    if (Dibujo === null) return <Text color={n.activo ? actVERDE : undefined} dimColor={!n.activo}>{n.activo ? '● ' : '◦ '}</Text>
    const fuente = luciernaga ? (n.activo ? actLUCI_VERDE : actLUCI_GRIS) : n.activo ? actBICHO_VERDE : actBICHO_GRIS
    return <Dibujo source={fuente} alt={`${luciernaga ? 'subagente' : 'agente'} ${n.activo ? 'trabajando' : 'terminó'}`} width={luciernaga ? 17 : 20} height={luciernaga ? 19 : 22} isInteractive={n.activo} />
  }
  // Una fila del árbol: agente = Bicho, subagente = luciérnaga, skill = hoja de archivo (son instrucciones).
  const fila = (n: ActNodo, nivel: number, k: string): unknown[] => {
    if (nivel > 8) return []
    const esSkill = n.tipo === 'skill'
    const etiqueta = esSkill ? 'skill' : nivel > 0 ? 'subagente' : 'agente'
    const cuando = n.activo
      ? esSkill
        ? 'ahora'
        : actHace(ahora - n.t)
      : `${actHora(n.t)}${n.dur !== undefined ? ` · ${actHace(n.dur)}` : ''}`
    const propia = (
      <Box key={k} flexDirection="row" justifyContent="space-between">
        <Box flexDirection="row" gap={1}>
          {nivel > 0 ? <Text dimColor>{`${'   '.repeat(nivel - 1)}└`}</Text> : null}
          {icono(n, nivel)}
          <Text bold={n.activo}>
            {n.nombre}
            <Text dimColor> {etiqueta}</Text>
          </Text>
        </Box>
        <Text color={n.activo ? actVERDE : undefined} dimColor={!n.activo}>{cuando}</Text>
      </Box>
    )
    return [propia, ...n.hijos.flatMap((h, i) => fila(h, nivel + 1, `${k}.${i}`))]
  }
  const grupos = (lista: ActSesion[], pref: string) =>
    lista.map((g, gi) => (
      <Box key={`${pref}${gi}`} flexDirection="column">
        <Text dimColor>
          {g.cwd || 'sesión'} · {g.sesion}
        </Text>
        {g.raices.flatMap((r, i) => fila(r, 0, `${pref}${gi}-${i}`))}
      </Box>
    ))

  return (
    <Box flexDirection="column" gap={1} marginTop={1}>
      <Box flexDirection="row" justifyContent="space-between" backgroundColor={actBARRA} paddingX={1}>
        <Text bold color="#F5F5F7">Actividad</Text>
        {m.trabajando > 0 ? <Text color={actVERDE}>{`● ${m.trabajando} trabajando`}</Text> : null}
      </Box>
      <Box flexDirection="column" gap={1} paddingX={1}>
      <Box flexDirection="column">
        <Text bold>Ahora</Text>
        {m.ahora.length === 0 ? <Text dimColor>Nada activo.</Text> : grupos(m.ahora, 'a')}
      </Box>
      <Box flexDirection="column">
        <Text bold>Hoy · terminaron</Text>
        {m.hoy.length === 0 ? <Text dimColor>Todavía nada hoy.</Text> : grupos(m.hoy, 'h')}
      </Box>
      {m.sinUso ? (
        <Text dimColor>{`Sin activarse en ${m.sinUso.dias} días: ${m.sinUso.sin} de ${m.sinUso.total} (propios)`}</Text>
      ) : null}
      <Text dimColor>Bicho = agente · luciérnaga = subagente · ▤ skill (instrucciones) · verde = trabajando</Text>
      </Box>
    </Box>
  )
}

export const registrarActividad = (on: Parameters<Register>[0]): void => {
  // ── Registro: dispara solo, con cada agente o skill que se activa ──
  on('classic.UserPromptSubmit', async ($, e, next) => {
    actSidActual = actCorto(e.session_id).slice(0, 8)
    actCwdActual = actCorto(e.cwd)
    return next(e)
  }).catch(($, e, next) => next(e))

  on('classic.SubagentStart', async ($, e, next) => {
    actSidActual = actCorto(e.session_id).slice(0, 8)
    actVistos.add(actCorto(e.agent_id))
    await actAnotar($, { s: actSidActual, ev: 'start', tipo: 'agente', n: actCorto(e.agent_type), id: actCorto(e.agent_id), cwd: actCorto(e.cwd) })
    void actRefrescar($)
    return next(e)
  }).catch(($, e, next) => next(e))

  // El padre de cada subagente: quién lo lanzó (el agente de arriba, o 'main' si fue la conversación).
  on('agent.spawn', async ($, e, next) => {
    const r = await next(e)
    const hijo = (r as { agentId?: string }).agentId
    if (hijo) actVistos.add(actCorto(hijo))
    if (hijo) await actAnotar($, { s: actSidActual, ev: 'link', id: hijo, padre: (e as { parentAgentId?: string }).parentAgentId ?? 'main' })
    return r
  }).catch(($, e, next) => next(e))

  on('classic.SubagentStop', async ($, e, next) => {
    actParados.add(actCorto(e.agent_id))
    await actAnotar($, { s: actCorto(e.session_id).slice(0, 8), ev: 'stop', tipo: 'agente', n: actCorto(e.agent_type), id: actCorto(e.agent_id) })
    void actRefrescar($)
    return next(e)
  }).catch(($, e, next) => next(e))

  on('turn.start', async ($, e, next) => {
    await actAvisarVivo($, e.agentId)
    return next(e)
  }).catch(($, e, next) => next(e))

  on('tool.call', async ($, e, next) => {
    await actAvisarVivo($, (e as { agentId?: string }).agentId)
    return next(e)
  }).catch(($, e, next) => next(e))

  on('tool.call', { tool: 'Skill' }, async ($, e, next) => {
    await actAnotar($, { s: actSidActual, ev: 'start', tipo: 'skill', n: actCorto((e as { skill?: string }).skill), cwd: actCwdActual, por: (e as { agentId?: string }).agentId })
    void actRefrescar($)
    return next(e)
  }).catch(($, e, next) => next(e))

  // ── Panel ──
  on('ui.close', { id: actPANEL }, async ($, e, next) => {
    if (e.origin.kind === 'person') actCerradoAMano = true
    return next(e)
  }).catch(($, e, next) => next(e))

  on('command.run', { command: 'actividad' }, async $ => {
    actCerradoAMano = false
    await $.ui.open({ id: actPANEL, title: actTITULO, columns: 38 })
    await actRefrescar($)
    return { text: 'Panel de actividad abierto.' }
  })
}

export const register: Register = on => {
  on('session.start', ($, e, next) => usoSessionStart($, e, e2 => unSessionStart($, e2, e3 => actSessionStart($, e3, next)))).catch(($, e, next) => next(e))
  on('command.run', ($, e, next) => usoCommandRun($, e, next)).catch(($, e, next) => next(e))
  on('prompt.submit', ($, e, next) => usoPromptSubmit($, e, e2 => unPromptSubmit($, e2, e3 => actPromptSubmit($, e3, next)))).catch(($, e, next) => next(e))
  on('session.measure', ($, e, next) => usoSessionMeasure($, e, e2 => unSessionMeasure($, e2, e3 => actSessionMeasure($, e3, next))))
  registrarUso(on)
  registrarUnico(on)
  // Tercer panel: «Actividad» (agentes, subagentes y skills), en su propio archivo.
  registrarActividad(on)
}
