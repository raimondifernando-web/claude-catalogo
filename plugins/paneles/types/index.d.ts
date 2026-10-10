export type Limite = { kind: string; percentUsed: number; resetsAt?: string }

export type Categoria = { name: string; tokens: number; color: string; kind: 'used' | 'free' | 'buffer' }

export type Medida = {
  tokens?: number
  window: number
  percent?: number
  limites: Limite[]
}

export type Gasto = {
  // Qué arrancó el turno en curso: un comando («/arrancar») o «conversación».
  actual: string
  // Cuándo corrió el último comando (ms): un mensaje que llega enseguida es su expansión.
  marca?: number
  // Costo total de la sesión en la última medición (US$), para sacar la diferencia.
  costoPrevio: number
  // US$ acumulados por lo que arrancó cada turno.
  porOrigen: Record<string, number>
}

export type Fila = {
  id: string
  // Una línea corta, sin marcas de markdown.
  texto: string
  prio: 1 | 2 | 3
  estado: string
  quien: string
  // El texto entero de la fila, sin marcas de markdown.
  completo: string
  depende: string
  esfuerzo: string
  origen: string
  // IDs de las filas que dependen de esta (salen de la columna «Depende de» de las otras).
  desbloquea: string[]
  // Letra de la sección (A, B, C…).
  seccion: string
}

export type Cambio = {
  tipo: 'nuevo' | 'cerrado' | 'prio' | 'estado' | 'sacado'
  id: string
  texto: string
  detalle?: string
}

export type Cambios = {
  estado: 'ok' | 'sin-anterior' | 'error'
  lista: Cambio[]
  // Cuántos más hay que no entraron en la lista.
  extra: number
  // Fecha (AAAA-MM-DD) de la versión contra la que se compara.
  desde?: string
  // La versión de trabajo tiene cambios sin guardar en git.
  sucio?: boolean
  error?: string
}

export type Proxima = { cuando: string; texto: string }

export type Modelo = {
  // Si no se pudo leer nada, el motivo: el panel lo muestra en lugar de las listas.
  error?: string
  // La carpeta de la sesión no tiene .claude/PENDIENTES.md: el panel lo dice en criollo.
  sinLista?: boolean
  // Filas o tablas mal formadas: el panel avisa y muestra lo que sí pudo leer.
  problemas: string[]
  ahora: Fila[]
  semana: Fila[]
  despues: Fila[]
  hechos: number
  // Letra de sección → nombre.
  nombres: Record<string, string>
  cambios: Cambios
  proxima?: Proxima
  // false si el archivo no trae la tabla «Fechas».
  hayFechas: boolean
  // Días desde la última línea fechada de «Cambios» (undefined si no hay).
  dias?: number
}

declare module 'claude-code' {
  interface PluginState {
    paneles: {
      medida: Medida | null
      categorias: Categoria[]
      gasto: Gasto
      datos: Modelo | null
      abierto: boolean
      detalle: string[]
    }
  }
}
