declare const __CT_DEMO_DEFAULT__: boolean

export const demoDefault = __CT_DEMO_DEFAULT__
export const demoRelease = 'prueba-local'
export const apiRoot = '/api/v1'

export type Metric = 'nivel' | 'crecimiento' | 'participacion'
export type Valuation = 'real' | 'nominal'

export interface Territory {
  codigo: string
  nombre: string
  nivel: 'nacional' | 'regional'
}

export interface Publication {
  id: string
  fecha: string
  estado: 'aprobada' | 'prueba'
  fuente: string
  cobertura?: {
    esperadas: number
    disponibles: number
  }
  cambios?: string[]
}

export interface Observation {
  id: string
  territorio: string
  anio: number
  metrica: Metric
  valoracion: Valuation
  valor: string | null
  unidad: string
  anio_referencia: number | null
  estado: 'informado' | 'preliminar' | 'faltante' | 'suprimido' | 'no_aplicable' | 'error'
  clase: 'oficial' | 'estimacion' | 'prueba' | 'no_disponible'
  publicacion: string
}

export interface Provenance {
  observacion: string
  publicacion: string
  serie_bde: string | null
  artefacto: string | null
  selector: string | null
  formula_version: string | null
  insumos: string[]
  motivo: string | null
}

interface Snapshot {
  territories: Territory[]
  publication: Publication
  rows: Observation[]
  provenance: Record<string, Provenance>
}

const embedded = document.getElementById('ct-snapshot')
const snapshot: Snapshot | null = embedded ? JSON.parse(embedded.textContent ?? '') : null
export const standalone = snapshot !== null

function selectRows(data: Snapshot, filters: URLSearchParams) {
  if (filters.get('publicacion') !== data.publication.id) throw new Error('El corte solicitado no está disponible.')
  const territories = filters.getAll('territorios')
  return data.rows.filter(row =>
    territories.includes(row.territorio) && row.metrica === filters.get('metrica') &&
    row.valoracion === filters.get('valoracion') && row.anio >= Number(filters.get('anio_desde')) &&
    row.anio <= Number(filters.get('anio_hasta')),
  )
}

interface Page {
  datos: Observation[]
  total: number
  publicacion: string
}

export async function get<T>(path: string, signal?: AbortSignal): Promise<T> {
  if (snapshot) {
    if (path === '/territorios') return snapshot.territories as T
    if (path === '/publicaciones') return [snapshot.publication] as T
    const match = path.match(/^\/observaciones\/([^/]+)\/procedencia$/)
    const entry = match && snapshot.provenance[decodeURIComponent(match[1])]
    if (entry) return entry as T
    throw new Error('La procedencia solicitada no está en este corte.')
  }
  const response = await fetch(apiRoot + path, { signal })
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new Error(body?.mensaje || `El servicio respondió con el código ${response.status}.`)
  }
  return response.json()
}

export async function observations(query: URLSearchParams, signal: AbortSignal) {
  if (snapshot) return { rows: selectRows(snapshot, query), publication: snapshot.publication.id }
  const request = new URLSearchParams(query)
  request.set('limite', '500')
  const first = await get<Page>(`/pib?${request}`, signal)
  const rows = [...first.datos]
  request.set('publicacion', first.publicacion)
  for (let page = 2; rows.length < first.total; page++) {
    request.set('pagina', String(page))
    const next = await get<Page>(`/pib?${request}`, signal)
    if (next.publicacion !== first.publicacion || !next.datos.length) {
      throw new Error('No se pudo conservar el corte de la consulta.')
    }
    rows.push(...next.datos)
  }
  return { rows, publication: first.publicacion }
}

export async function downloadObservations(filters: URLSearchParams, publication: string) {
  if (snapshot) {
    const fields = ['id', 'territorio', 'anio', 'metrica', 'valoracion', 'valor', 'unidad',
      'anio_referencia', 'estado', 'clase', 'publicacion'] as const
    const csv = [fields.join(','), ...selectRows(snapshot, filters).map(row => fields.map(field => {
      const value = String(row[field] ?? '')
      return /[,"\r\n]/.test(value) ? `"${value.replaceAll('"', '""')}"` : value
    }).join(','))].join('\r\n')
    return new Blob([csv], { type: 'text/csv;charset=utf-8' })
  }
  const response = await fetch(`${apiRoot}/pib.csv?${filters}`)
  if (!response.ok || response.headers.get('X-Publicacion') !== publication) throw new Error()
  return response.blob()
}
