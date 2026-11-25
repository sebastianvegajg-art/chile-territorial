import { apiRoot } from '../api'

export interface FuenteTrazabilidad {
  institucion: string
  sistema?: string | null
  endpoint?: string | null
  endpoint_ckan?: string | null
  url?: string | null
  codigo_serie?: string | null
  codigos_series?: string[] | null
  series_consultadas?: string[] | null
  actualizado_en?: string | null
  extraido_en?: string | null
  fecha_extraccion?: string | null
  corte?: string | null
  unidad?: string | null
  unidad_salida?: string | null
  periodicidad?: string | null
  metodo?: string | null
  notas?: string | null
  nota?: string | null
  desde_cache?: boolean
  archivo?: string | null
  sha256?: string | null
  package_name?: string | null
  package_title?: string | null
  resource_id?: string | null
  resource_name?: string | null
}

export interface ObservacionAnual {
  anio: number
  valor: number | null
  estado?: string | null
}

export interface ActividadAysen {
  codigo: string
  nombre: string
  serie_id: string
  valor_millones: number | null
  participacion_pct: number | null
  participacion_pib_pct?: number | null
  anio?: number
  estado?: string | null
  es_administracion_publica: boolean
  es_pesca: boolean
  serie_historica?: ObservacionAnual[]
}

export interface ObservacionTrimestral {
  fecha: string
  periodo?: string | null
  valor: number | null
  valor_millones?: number | null
  variacion_interanual_pct?: number | null
  estado?: string | null
}

export interface SerieTrimestral {
  serie_id: string
  nombre: string
  unidad?: string | null
  observaciones: ObservacionTrimestral[]
  ultimo_periodo?: string | null
  ultimo_valor?: number | null
  ultima_variacion_pct?: number | null
}

export interface ResumenPibAysen {
  anio: number | null
  aysen_nominal_millones: number | null
  chile_nominal_millones: number | null
  participacion_nacional_pct: number | null
  aysen_real_millones: number | null
  chile_real_millones: number | null
  crecimiento_real_aysen_pct: number | null
  crecimiento_real_chile_pct: number | null
  administracion_publica_millones: number | null
  administracion_publica_pct: number | null
  administracion_publica_vab_pct?: number | null
  pesca_millones?: number | null
  pesca_pct?: number | null
  suma_actividades_nominal_millones?: number | null
  diferencia_impuestos_productos_millones?: number | null
  diferencia_impuestos_productos_nota?: string | null
  serie_aysen_nominal?: string | null
  serie_chile_nominal?: string | null
  serie_aysen_real?: string | null
  serie_chile_real?: string | null
  serie_admin_publica?: string | null
}

export interface ConcentracionHHI {
  indice: number | null
  escala?: string | null
  interpretacion?: string | null
  formula_version?: string | null
  estado?: string | null
  motivo?: string | null
}

export interface SerieFaltante {
  serie_id: string
  nombre?: string | null
  motivo?: string | null
}

export interface EstructuraAysenResponse {
  region_codigo: string
  region_nombre: string
  anio_desde: number
  anio_hasta: number
  anio_referencia_ultimo?: number | null
  resumen_pib: ResumenPibAysen
  actividades: ActividadAysen[]
  hhi?: ConcentracionHHI | null
  trimestral: SerieTrimestral[]
  series_faltantes?: SerieFaltante[]
  fuente_trazabilidad: FuenteTrazabilidad
  actualizado_en?: string | null
  extraido_en?: string | null
}

export interface BcchSearchItem {
  seriesId: string
  spanishTitle: string
  englishTitle?: string | null
  firstObservation?: string | null
  lastObservation?: string | null
  updatedAt?: string | null
  frequencyCode?: string | null
}

export interface BcchSearchResponse {
  frequency: 'ANNUAL' | 'QUARTERLY'
  query: string
  total: number
  resultados: BcchSearchItem[]
  fuente_trazabilidad?: FuenteTrazabilidad | null
  actualizado_en?: string | null
  extraido_en?: string | null
}

export interface BcchSeriesObservation {
  fecha: string
  valor: number | null
  estado?: string | null
}

export interface BcchSeriesResponse {
  serie_id: string
  titulo: string
  titulo_en?: string | null
  unidad?: string | null
  observaciones: BcchSeriesObservation[]
  fuente_trazabilidad?: FuenteTrazabilidad | null
  actualizado_en?: string | null
  extraido_en?: string | null
}

export class ApiServiceError extends Error {
  readonly status: number
  readonly codigo: string
  readonly detalle?: Record<string, unknown>

  constructor(message: string, status: number, codigo = 'error', detalle?: Record<string, unknown>) {
    super(message)
    this.name = 'ApiServiceError'
    this.status = status
    this.codigo = codigo
    this.detalle = detalle
  }

  get isMissingBcchToken(): boolean {
    return this.codigo === 'falta_token_bcch'
  }
}

export function toNumberOrNull(value: unknown): number | null {
  if (value === null || value === undefined || value === '') return null
  if (typeof value === 'number') return Number.isFinite(value) ? value : null
  const parsed = Number(String(value).trim().replace(',', '.'))
  return Number.isFinite(parsed) ? parsed : null
}

export async function requestApiJson<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  let response: Response
  try {
    response = await fetch(apiRoot + path, init)
  } catch (err) {
    if (err instanceof DOMException && err.name === 'AbortError') throw err
    throw new ApiServiceError(
      'No se pudo establecer conexión con el servicio de datos en vivo.',
      0,
      'red_no_disponible',
    )
  }

  const contentType = response.headers.get('content-type') ?? ''
  const body = contentType.includes('application/json')
    ? await response.json().catch(() => null)
    : null

  if (!response.ok) {
    const record = (body && typeof body === 'object' ? body : null) as Record<string, unknown> | null
    const nestedDetail = record?.detail && typeof record.detail === 'object'
      ? (record.detail as Record<string, unknown>)
      : null
    const codigo = String(record?.codigo ?? nestedDetail?.codigo ?? (response.status === 404 ? 'no_encontrado' : 'error'))

    if (codigo === 'falta_token_bcch') {
      const serverMsg = typeof record?.mensaje === 'string'
        ? record.mensaje
        : typeof nestedDetail?.mensaje === 'string'
          ? nestedDetail.mensaje
          : null
      throw new ApiServiceError(
        serverMsg ||
          'Falta configurar la credencial oficial del Banco Central de Chile. Define BCCH_API_TOKEN (o VITE_BCENTRAL_TOKEN) en el archivo .env local del servidor backend; las credenciales nunca se exponen al navegador.',
        response.status,
        'falta_token_bcch',
        record ?? undefined,
      )
    }

    const message =
      (typeof record?.mensaje === 'string' && record.mensaje) ||
      (typeof nestedDetail?.mensaje === 'string' && nestedDetail.mensaje) ||
      (typeof record?.detail === 'string' && record.detail) ||
      `El servicio respondió con el código HTTP ${response.status}.`

    throw new ApiServiceError(message, response.status, codigo, record ?? undefined)
  }

  return body as T
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null
}

function normalizeFuente(raw: unknown, fallbackInstitucion: string, fallbackEndpoint: string): FuenteTrazabilidad {
  const f = asRecord(raw) ?? {}
  const seriesConsultadas = Array.isArray(f.series_consultadas)
    ? f.series_consultadas.map(String)
    : Array.isArray(f.codigos_series)
      ? f.codigos_series.map(String)
      : null
  return {
    institucion: typeof f.institucion === 'string' && f.institucion ? f.institucion : fallbackInstitucion,
    endpoint: typeof f.endpoint === 'string'
      ? f.endpoint
      : typeof f.endpoint_ckan === 'string'
        ? f.endpoint_ckan
        : fallbackEndpoint,
    endpoint_ckan: typeof f.endpoint_ckan === 'string' ? f.endpoint_ckan : null,
    codigo_serie: typeof f.codigo_serie === 'string' ? f.codigo_serie : null,
    codigos_series: seriesConsultadas,
    series_consultadas: seriesConsultadas,
    actualizado_en: typeof f.actualizado_en === 'string' ? f.actualizado_en : null,
    extraido_en: typeof f.extraido_en === 'string'
      ? f.extraido_en
      : typeof f.fecha_extraccion === 'string'
        ? f.fecha_extraccion
        : null,
    unidad: typeof f.unidad === 'string' ? f.unidad : typeof f.unidad_salida === 'string' ? f.unidad_salida : null,
    nota: typeof f.nota === 'string' ? f.nota : typeof f.notas === 'string' ? f.notas : null,
    desde_cache: typeof f.desde_cache === 'boolean' ? f.desde_cache : undefined,
    archivo: typeof f.archivo === 'string' ? f.archivo : null,
    sha256: typeof f.sha256 === 'string' ? f.sha256 : null,
    package_name: typeof f.package_name === 'string' ? f.package_name : null,
    package_title: typeof f.package_title === 'string' ? f.package_title : null,
    resource_id: typeof f.resource_id === 'string' ? f.resource_id : null,
    resource_name: typeof f.resource_name === 'string' ? f.resource_name : null,
  }
}

export async function fetchAysenEstructura(
  anioDesde?: number,
  anioHasta?: number,
  refresh?: boolean,
  signal?: AbortSignal,
): Promise<EstructuraAysenResponse> {
  const params = new URLSearchParams()
  if (anioDesde !== undefined) params.set('anio_desde', String(anioDesde))
  if (anioHasta !== undefined) params.set('anio_hasta', String(anioHasta))
  if (refresh) params.set('refresh', 'true')
  const qs = params.toString()
  const raw = await requestApiJson<Record<string, unknown>>(
    `/territorial/aysen/estructura${qs ? `?${qs}` : ''}`,
    { signal },
  )

  const territorio = asRecord(raw.territorio)
  const rango = asRecord(raw.rango_solicitado)
  const resumenRaw = asRecord(raw.resumen_pib) ?? {}
  const sectoresClave = asRecord(resumenRaw.sectores_clave)
  const adminClave = asRecord(sectoresClave?.administracion_publica)
  const pescaClave = asRecord(sectoresClave?.pesca)
  const hhiRaw = asRecord(resumenRaw.concentracion_hhi) ?? asRecord(raw.hhi)

  const rawActividades = Array.isArray(raw.actividades) ? raw.actividades : []
  const actividades: ActividadAysen[] = rawActividades
    .map(item => asRecord(item))
    .filter((item): item is Record<string, unknown> => item !== null)
    .map(item => {
      const nombre = String(item.nombre ?? item.titulo_es ?? item.codigo_actividad ?? '')
      const lower = nombre.toLowerCase()
      return {
        codigo: String(item.codigo_actividad ?? item.codigo ?? item.serie_bde ?? ''),
        nombre,
        serie_id: String(item.serie_bde ?? item.serie_id ?? ''),
        valor_millones: toNumberOrNull(item.valor_millones),
        participacion_pct: toNumberOrNull(
          item.participacion_pib_pct ?? item.participacion_pct ?? item.participacion_actividades_pct,
        ),
        participacion_pib_pct: toNumberOrNull(item.participacion_pib_pct),
        estado: typeof item.estado === 'string' ? item.estado : null,
        es_administracion_publica:
          typeof item.es_administracion_publica === 'boolean'
            ? item.es_administracion_publica
            : lower.includes('administración pública') || lower.includes('administracion publica'),
        es_pesca:
          typeof item.es_pesca === 'boolean'
            ? item.es_pesca
            : lower.includes('pesca') || lower.includes('acuicultura'),
      }
    })

  const rawTrimestralField = raw.trimestral
  const rawTrimestralList = Array.isArray(rawTrimestralField)
    ? rawTrimestralField
    : Array.isArray(asRecord(rawTrimestralField)?.series)
      ? (asRecord(rawTrimestralField)!.series as unknown[])
      : []

  const trimestral: SerieTrimestral[] = rawTrimestralList
    .map(item => asRecord(item))
    .filter((item): item is Record<string, unknown> => item !== null)
    .map(item => {
      const rawObs = Array.isArray(item.observaciones) ? item.observaciones : []
      const observaciones: ObservacionTrimestral[] = rawObs
        .map(obs => asRecord(obs))
        .filter((obs): obs is Record<string, unknown> => obs !== null)
        .map(obs => ({
          fecha: String(obs.fecha ?? obs.indexDateString ?? ''),
          periodo: typeof obs.periodo === 'string' ? obs.periodo : null,
          valor: toNumberOrNull(obs.valor_millones ?? obs.valor),
          valor_millones: toNumberOrNull(obs.valor_millones),
          variacion_interanual_pct: toNumberOrNull(obs.variacion_interanual_pct),
          estado: typeof obs.estado === 'string' ? obs.estado : null,
        }))
      const last = observaciones.at(-1)
      return {
        serie_id: String(item.seriesId ?? item.serie_id ?? ''),
        nombre: String(item.spanishTitle ?? item.descripEsp ?? item.nombre ?? item.seriesId ?? ''),
        unidad: typeof item.unidad === 'string' ? item.unidad : null,
        observaciones,
        ultimo_periodo: typeof item.ultimo_periodo === 'string' ? item.ultimo_periodo : (last?.periodo ?? last?.fecha ?? null),
        ultimo_valor: toNumberOrNull(item.ultimo_valor) ?? last?.valor ?? null,
        ultima_variacion_pct: toNumberOrNull(item.ultima_variacion_pct) ?? last?.variacion_interanual_pct ?? null,
      }
    })

  const fuente = normalizeFuente(
    raw.fuente_trazabilidad,
    'Banco Central de Chile (BDE SI3 REST API)',
    '/api/v1/territorial/aysen/estructura',
  )

  const hhiValor = toNumberOrNull(hhiRaw?.valor ?? hhiRaw?.indice ?? raw.hhi)
  const hhiInterpretacion =
    typeof hhiRaw?.interpretacion === 'string'
      ? hhiRaw.interpretacion
      : hhiValor !== null
        ? hhiValor >= 2500
          ? 'Alta concentración sectorial (≥ 2.500)'
          : hhiValor >= 1500
            ? 'Concentración sectorial moderada (1.500–2.499)'
            : 'Estructura relativamente diversificada (< 1.500)'
        : null

  const adminFromList = actividades.find(a => a.es_administracion_publica)
  const pescaFromList = actividades.find(a => a.es_pesca)

  return {
    region_codigo: String(territorio?.codigo ?? raw.region_codigo ?? '11'),
    region_nombre: String(territorio?.nombre ?? raw.region_nombre ?? 'Aysén del General Carlos Ibáñez del Campo'),
    anio_desde: Number(rango?.anio_desde ?? raw.anio_desde ?? anioDesde ?? 2013),
    anio_hasta: Number(rango?.anio_hasta ?? raw.anio_hasta ?? anioHasta ?? new Date().getFullYear()),
    anio_referencia_ultimo: typeof raw.ultimo_anio === 'number' ? raw.ultimo_anio : (typeof resumenRaw.anio === 'number' ? resumenRaw.anio : null),
    resumen_pib: {
      anio: typeof resumenRaw.anio === 'number' ? resumenRaw.anio : (typeof raw.ultimo_anio === 'number' ? raw.ultimo_anio : null),
      aysen_nominal_millones: toNumberOrNull(resumenRaw.aysen_nominal_millones),
      chile_nominal_millones: toNumberOrNull(resumenRaw.chile_nominal_millones),
      participacion_nacional_pct: toNumberOrNull(
        resumenRaw.participacion_aysen_en_chile_pct ?? resumenRaw.participacion_nacional_pct,
      ),
      aysen_real_millones: toNumberOrNull(resumenRaw.aysen_real_millones),
      chile_real_millones: toNumberOrNull(resumenRaw.chile_real_millones),
      crecimiento_real_aysen_pct: toNumberOrNull(resumenRaw.crecimiento_real_aysen_pct),
      crecimiento_real_chile_pct: toNumberOrNull(resumenRaw.crecimiento_real_chile_pct),
      administracion_publica_millones: toNumberOrNull(
        adminClave?.valor_millones ?? resumenRaw.administracion_publica_millones ?? adminFromList?.valor_millones,
      ),
      administracion_publica_pct: toNumberOrNull(
        adminClave?.participacion_pib_pct ??
          resumenRaw.administracion_publica_pct ??
          adminClave?.participacion_actividades_pct ??
          adminFromList?.participacion_pct,
      ),
      administracion_publica_vab_pct: toNumberOrNull(adminClave?.participacion_actividades_pct),
      pesca_millones: toNumberOrNull(pescaClave?.valor_millones ?? resumenRaw.pesca_millones ?? pescaFromList?.valor_millones),
      pesca_pct: toNumberOrNull(
        pescaClave?.participacion_pib_pct ??
          resumenRaw.pesca_pct ??
          pescaClave?.participacion_actividades_pct ??
          pescaFromList?.participacion_pct,
      ),
      suma_actividades_nominal_millones: toNumberOrNull(resumenRaw.suma_actividades_nominal_millones),
      diferencia_impuestos_productos_millones: toNumberOrNull(resumenRaw.diferencia_impuestos_productos_millones),
      diferencia_impuestos_productos_nota:
        typeof resumenRaw.diferencia_impuestos_productos_nota === 'string'
          ? resumenRaw.diferencia_impuestos_productos_nota
          : null,
      serie_aysen_nominal: typeof resumenRaw.serie_aysen_nominal === 'string' ? resumenRaw.serie_aysen_nominal : null,
      serie_chile_nominal: typeof resumenRaw.serie_chile_nominal === 'string' ? resumenRaw.serie_chile_nominal : null,
      serie_aysen_real: typeof resumenRaw.serie_aysen_real === 'string' ? resumenRaw.serie_aysen_real : null,
      serie_chile_real: typeof resumenRaw.serie_chile_real === 'string' ? resumenRaw.serie_chile_real : null,
      serie_admin_publica:
        typeof adminClave?.serie_bde === 'string'
          ? adminClave.serie_bde
          : typeof resumenRaw.serie_admin_publica === 'string'
            ? resumenRaw.serie_admin_publica
            : adminFromList?.serie_id ?? null,
    },
    actividades,
    hhi: {
      indice: hhiValor,
      escala: typeof hhiRaw?.escala === 'string' ? hhiRaw.escala : '0-10000',
      interpretacion: hhiInterpretacion,
      formula_version: typeof hhiRaw?.formula_version === 'string' ? hhiRaw.formula_version : null,
      estado: typeof hhiRaw?.estado === 'string' ? hhiRaw.estado : null,
      motivo: typeof hhiRaw?.motivo === 'string' ? hhiRaw.motivo : null,
    },
    trimestral,
    series_faltantes: Array.isArray(raw.series_faltantes) ? (raw.series_faltantes as SerieFaltante[]) : [],
    fuente_trazabilidad: fuente,
    actualizado_en: typeof raw.actualizado_en === 'string' ? raw.actualizado_en : fuente.actualizado_en,
    extraido_en: typeof raw.extraido_en === 'string' ? raw.extraido_en : fuente.extraido_en,
  }
}

export async function searchBcchSeries(
  frequency: 'ANNUAL' | 'QUARTERLY',
  q: string,
  signal?: AbortSignal,
): Promise<BcchSearchResponse> {
  const params = new URLSearchParams({ frequency, q: q.trim() })
  const raw = await requestApiJson<Record<string, unknown>>(`/bcch/search?${params.toString()}`, { signal })
  const rawItems = (
    Array.isArray(raw?.series)
      ? raw.series
      : Array.isArray(raw?.resultados)
        ? raw.resultados
        : Array.isArray(raw?.items)
          ? raw.items
          : []
  ) as Array<Record<string, unknown>>

  const resultados: BcchSearchItem[] = rawItems.map(item => ({
    seriesId: String(item.seriesId ?? item.serie_id ?? item.id ?? ''),
    spanishTitle: String(item.spanishTitle ?? item.titulo ?? item.descripEsp ?? item.seriesId ?? ''),
    englishTitle: item.englishTitle ? String(item.englishTitle) : item.descripIng ? String(item.descripIng) : null,
    firstObservation: item.firstObservation ? String(item.firstObservation) : item.primera_observacion ? String(item.primera_observacion) : null,
    lastObservation: item.lastObservation ? String(item.lastObservation) : item.ultima_observacion ? String(item.ultima_observacion) : null,
    updatedAt: item.updatedAt ? String(item.updatedAt) : item.actualizado_en ? String(item.actualizado_en) : null,
    frequencyCode: item.frequencyCode ? String(item.frequencyCode) : item.frecuencia ? String(item.frecuencia) : frequency,
  })).filter(item => item.seriesId.length > 0)

  const fuente = normalizeFuente(
    raw.fuente_trazabilidad,
    'Banco Central de Chile (BDE SI3 REST API)',
    `/api/v1/bcch/search?${params.toString()}`,
  )

  return {
    frequency,
    query: String(raw?.query ?? q.trim()),
    total: typeof raw?.total === 'number' ? raw.total : resultados.length,
    resultados,
    fuente_trazabilidad: fuente,
    actualizado_en: typeof raw?.actualizado_en === 'string' ? raw.actualizado_en : fuente.actualizado_en,
    extraido_en: typeof raw?.extraido_en === 'string' ? raw.extraido_en : fuente.extraido_en,
  }
}

export async function fetchBcchSeries(
  seriesId: string,
  firstdate?: string,
  signal?: AbortSignal,
): Promise<BcchSeriesResponse> {
  const params = new URLSearchParams()
  if (firstdate && firstdate.trim()) params.set('firstdate', firstdate.trim())
  const qs = params.toString()
  const raw = await requestApiJson<Record<string, unknown>>(
    `/bcch/series/${encodeURIComponent(seriesId.trim())}${qs ? `?${qs}` : ''}`,
    { signal },
  )

  const serieBlock = asRecord(raw?.serie) ?? raw
  const rawObs = (
    Array.isArray(serieBlock?.observaciones)
      ? serieBlock.observaciones
      : Array.isArray(raw?.observaciones)
        ? raw.observaciones
        : Array.isArray(serieBlock?.Obs)
          ? serieBlock.Obs
          : []
  ) as Array<Record<string, unknown>>

  const observaciones: BcchSeriesObservation[] = rawObs.map(item => ({
    fecha: String(item.fecha ?? item.indexDateString ?? item.periodo ?? ''),
    valor: toNumberOrNull(item.valor ?? item.value),
    estado: item.estado ? String(item.estado) : item.statusCode ? String(item.statusCode) : null,
  }))

  const fuente = normalizeFuente(
    raw.fuente_trazabilidad,
    'Banco Central de Chile (BDE SI3 REST API)',
    `/api/v1/bcch/series/${encodeURIComponent(seriesId.trim())}`,
  )

  return {
    serie_id: String(serieBlock?.seriesId ?? serieBlock?.serie_id ?? seriesId.trim()),
    titulo: String(serieBlock?.descripEsp ?? serieBlock?.titulo ?? serieBlock?.spanishTitle ?? seriesId.trim()),
    titulo_en: serieBlock?.descripIng ? String(serieBlock.descripIng) : serieBlock?.englishTitle ? String(serieBlock.englishTitle) : null,
    unidad: typeof serieBlock?.unidad === 'string' ? serieBlock.unidad : null,
    observaciones,
    fuente_trazabilidad: fuente,
    actualizado_en: typeof raw?.actualizado_en === 'string' ? raw.actualizado_en : fuente.actualizado_en,
    extraido_en: typeof raw?.extraido_en === 'string' ? raw.extraido_en : fuente.extraido_en,
  }
}
