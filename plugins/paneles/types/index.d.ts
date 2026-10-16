export type Tarea = { id: string; texto: string; estado: 'pending' | 'in_progress' | 'completed' }
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
  // Letra de la sección (S, B, C, E, M, O).
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
  // Tareas de esta sesión según .claude/tareas.json (null = no hay archivo).
  sesion: Tarea[] | null
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
  // Carpeta de la que salió la lista cuando no es la de la sesión (una de arriba).
  desde?: string
}

// ── Panel «Actividad» ──
export type ActNodo = {
  tipo: 'agente' | 'skill'
  nombre: string
  // Milisegundos desde 1970 del arranque.
  t: number
  // Duración en milisegundos si ya terminó (solo agentes); undefined si sigue o no se sabe.
  dur?: number
  activo: boolean
  // Id corto de la sesión y nombre de la carpeta donde corrió.
  sesion: string
  cwd: string
  // Lo que cuelga de este: subagentes lanzados y skills usadas por él.
  hijos: ActNodo[]
}

export type ActSesion = { sesion: string; cwd: string; raices: ActNodo[] }

export type ActSinUso = { dias: number; sin: number; total: number; generado: string }

export type ActModelo = {
  ahora: ActSesion[]
  hoy: ActSesion[]
  // Cuántos nodos (agentes y skills) están trabajando ahora.
  trabajando: number
  sinUso?: ActSinUso
  error?: string
}

declare module 'claude-code' {
  interface PluginState {
    paneles: {
      medida: Medida | null
      categorias: Categoria[]
      gasto: Gasto
      datos: Modelo | null
      grupos: string[]
      detalle: string[]
      lista: Tarea[]
      actividadDatos: ActModelo | null
    }
  }
}
