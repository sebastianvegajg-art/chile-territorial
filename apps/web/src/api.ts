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

interface Page {
  datos: Observation[]
  total: number
  publicacion: string
}

export async function get<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(apiRoot + path, { signal })
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new Error(body?.mensaje || `El servicio respondió con el código ${response.status}.`)
  }
  return response.json()
}

export async function observations(query: URLSearchParams, signal: AbortSignal) {
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
