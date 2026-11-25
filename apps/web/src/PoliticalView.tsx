import { useCallback, useEffect, useId, useMemo, useRef, useState } from 'react'
import type { ChangeEvent, FormEvent, ReactNode } from 'react'
import {
  ApiServiceError,
  fetchAysenEstructura,
  fetchBcchSeries,
  searchBcchSeries,
} from './services/bcchService'
import type {
  ActividadAysen,
  BcchSearchResponse,
  BcchSeriesResponse,
  EstructuraAysenResponse,
  FuenteTrazabilidad,
} from './services/bcchService'
import { fetchDipresAysen } from './services/dipresService'
import type { DipresAysenResponse } from './services/dipresService'
import { fetchDemografiaPoblacion } from './services/fase2Service'
import type { DemografiaPoblacionResponse } from './services/fase2Service'
import { fetchSinimAysen, importSinimFile, normalizeSinimErrors, sinimTemplateUrl } from './services/sinimService'
import type { SinimAysenResponse, SinimErrorFila } from './services/sinimService'

const num0 = new Intl.NumberFormat('es-CL', { maximumFractionDigits: 0 })
const num1 = new Intl.NumberFormat('es-CL', { minimumFractionDigits: 1, maximumFractionDigits: 1 })
const num2 = new Intl.NumberFormat('es-CL', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

const QUICK_DELTAS = [-15, -10, 0, 10, 15] as const

const MULTIPLIERS = [
  {
    value: 1.0,
    label: '1,0x · Directo contable (multiplicador hipotético)',
    description: 'Supuesto hipotético de impacto contable directo puro sobre el Valor Agregado de Administración Pública (BCCh), sin arrastre secundario.',
  },
  {
    value: 0.8,
    label: '0,8x · Conservador (multiplicador hipotético)',
    description: 'Supuesto hipotético conservador con filtración parcial de demanda hacia fuera de la región.',
  },
  {
    value: 1.25,
    label: '1,25x · Arrastre moderado (multiplicador hipotético)',
    description: 'Supuesto hipotético de encadenamiento local moderado sobre comercio y servicios regionales.',
  },
  {
    value: 1.5,
    label: '1,5x · Encadenamiento ampliado (multiplicador hipotético)',
    description: 'Escenario hipotético de sensibilidad superior con mayor circulación de remuneraciones en la economía local.',
  },
] as const

function fmtClp(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return 'Sin dato'
  return `$ ${num0.format(value)}`
}

function fmtMillions(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return 'Sin dato'
  return `MM$ ${num0.format(value)}`
}

function fmtPct(value: number | null | undefined, signed = false): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return 'Sin dato'
  const sign = signed && value > 0 ? '+' : ''
  return `${sign}${num2.format(value)}%`
}

function fmtTimestamp(value?: string | null): string {
  if (!value) return 'No informada'
  const trimmed = value.trim()
  if (!trimmed) return 'No informada'
  if (trimmed.includes('T')) {
    const date = trimmed.slice(0, 10)
    const time = trimmed.slice(11, 19).replace(/Z$/, '')
    return time ? `${date} · ${time} UTC` : date
  }
  return trimmed.slice(0, 19)
}

function isAdminPublica(item: ActividadAysen): boolean {
  if (item.es_administracion_publica !== undefined) return item.es_administracion_publica
  const normalized = item.nombre.toLowerCase()
  return normalized.includes('administración pública') || normalized.includes('administracion publica')
}

function isPesca(item: ActividadAysen): boolean {
  if (item.es_pesca !== undefined) return item.es_pesca
  const normalized = item.nombre.toLowerCase()
  return normalized.includes('pesca') || normalized.includes('acuicultura')
}

function extractHhiInfo(data: EstructuraAysenResponse | null): {
  indice: number | null
  escala: string
  interpretacion: string | null
  origen: 'servicio' | 'calculado' | 'sin_dato'
} {
  if (!data) return { indice: null, escala: '0–10.000', interpretacion: null, origen: 'sin_dato' }
  if (typeof data.hhi === 'number' && Number.isFinite(data.hhi)) {
    return { indice: data.hhi, escala: '0–10.000', interpretacion: null, origen: 'servicio' }
  }
  if (data.hhi && typeof data.hhi === 'object' && data.hhi.indice !== null && Number.isFinite(data.hhi.indice)) {
    return {
      indice: data.hhi.indice,
      escala: data.hhi.escala || '0–10.000',
      interpretacion: data.hhi.interpretacion || null,
      origen: 'servicio',
    }
  }
  const withShare = data.actividades.filter(item => item.participacion_pct !== null && Number.isFinite(item.participacion_pct))
  if (withShare.length > 0) {
    const sumSq = withShare.reduce((acc, item) => acc + Math.pow(item.participacion_pct!, 2), 0)
    const interpretacion = sumSq >= 2500
      ? 'Alta concentración sectorial (≥ 2.500)'
      : sumSq >= 1500
        ? 'Concentración sectorial moderada (1.500–2.499)'
        : 'Estructura relativamente diversificada (< 1.500)'
    return { indice: sumSq, escala: '0–10.000', interpretacion, origen: 'calculado' }
  }
  return { indice: null, escala: '0–10.000', interpretacion: null, origen: 'sin_dato' }
}

interface SourceFooterProps {
  fuente?: FuenteTrazabilidad | null
  institucionFallback: string
  endpointFallback: string
  seriesCodigos?: string[]
  actualizadoEn?: string | null
  extraidoEn?: string | null
  notaExtra?: string
}

function SourceFooter({
  fuente,
  institucionFallback,
  endpointFallback,
  seriesCodigos,
  actualizadoEn,
  extraidoEn,
  notaExtra,
}: SourceFooterProps) {
  const institucion = fuente?.institucion || institucionFallback
  const endpoint = fuente?.endpoint || endpointFallback
  const explicitCodes = (seriesCodigos ?? []).filter(Boolean)
  const fallbackCodes = [
    ...(fuente?.codigo_serie ? [fuente.codigo_serie] : []),
    ...(fuente?.codigos_series ?? []),
  ].filter(Boolean)
  const rawCodigos = explicitCodes.length > 0 ? explicitCodes : fallbackCodes
  const codigos = rawCodigos.filter((value, index, array) => array.indexOf(value) === index)
  const shownCodigos = codigos.slice(0, 4)
  const hiddenCount = codigos.length - shownCodigos.length

  const updated = actualizadoEn ?? fuente?.actualizado_en ?? fuente?.corte ?? null
  const extracted = extraidoEn ?? fuente?.extraido_en ?? fuente?.fecha_extraccion ?? null

  return (
    <footer className="source-footer" aria-label="Trazabilidad de fuente">
      <div className="source-footer-row">
        <span><strong>Fuente:</strong> {institucion}</span>
        <span><strong>Endpoint:</strong> <code className="mono">{endpoint}</code></span>
      </div>
      {shownCodigos.length > 0 && (
        <div className="source-footer-row">
          <span>
            <strong>{codigos.length === 1 ? 'Serie oficial:' : 'Series oficiales:'}</strong>{' '}
            <code className="mono">
              {shownCodigos.join(' · ')}
              {hiddenCount > 0 ? ` (+${hiddenCount} series)` : ''}
            </code>
          </span>
        </div>
      )}
      <div className="source-footer-row">
        <span><strong>Última actualización:</strong> {fmtTimestamp(updated)}</span>
        <span><strong>Extracción:</strong> {fmtTimestamp(extracted)}</span>
        {notaExtra && <span>{notaExtra}</span>}
      </div>
    </footer>
  )
}

interface KeyTerritorialCardProps {
  ejeLabel: string
  title: string
  summary: ReactNode
  evidenciaFavorable: string
  evidenciaContraria: string
  limiteInferencia: string
  source: SourceFooterProps
}

function KeyTerritorialCard({
  ejeLabel,
  title,
  summary,
  evidenciaFavorable,
  evidenciaContraria,
  limiteInferencia,
  source,
}: KeyTerritorialCardProps) {
  return (
    <aside className="panel key-card" aria-label={`Clave Territorial: ${title}`}>
      <div className="key-card-head">
        <span className="axis-badge">Clave Territorial</span>
        <span className="key-card-axis">{ejeLabel}</span>
      </div>
      <h3>{title}</h3>
      <div className="key-card-body">{summary}</div>
      <dl className="key-evidence">
        <div>
          <dt>Evidencia favorable</dt>
          <dd>{evidenciaFavorable}</dd>
        </div>
        <div>
          <dt>Evidencia contraria / matices</dt>
          <dd>{evidenciaContraria}</dd>
        </div>
        <div>
          <dt>Límites de inferencia</dt>
          <dd>{limiteInferencia}</dd>
        </div>
      </dl>
      <SourceFooter {...source} />
    </aside>
  )
}

function LoadingSkeleton({ label }: { label: string }) {
  return (
    <div className="pol-loading" role="status" aria-live="polite">
      <span className="pol-spinner" aria-hidden="true" />
      <div className="pol-skeleton-lines">
        <p className="pol-loading-label">{label}</p>
        <div className="skeleton-bar wide" />
        <div className="skeleton-bar medium" />
        <div className="skeleton-bar short" />
      </div>
    </div>
  )
}

function MissingBcchTokenPanel({
  message,
  onRetry,
}: {
  message: string
  onRetry: () => void
}) {
  return (
    <div className="token-diagnostic" role="alert">
      <div className="token-diagnostic-head">
        <span className="status-badge is-warn">Credencial BCCh requerida</span>
        <h3>Configura el token oficial del Banco Central en el servidor local</h3>
      </div>
      <p>{message}</p>
      <ol className="token-steps">
        <li>Abre o crea el archivo <code className="mono">.env</code> local en el servidor backend de <code className="mono">chile-territorial</code> (excluido de Git).</li>
        <li>Define <code className="mono">BCCH_API_TOKEN=tu_credencial_oficial</code> (o <code className="mono">BCCH_API_USER</code> y <code className="mono">BCCH_API_PASS</code>) exclusivamente en el entorno del servidor.</li>
        <li>Reinicia el servidor API y vuelve a consultar. El frontend jamás recibe credenciales ni rellena indicadores con cifras simuladas.</li>
      </ol>
      <button type="button" className="primary" onClick={onRetry}>
        Reintentar consulta BCCh
      </button>
    </div>
  )
}

function ServiceErrorBox({
  error,
  onRetry,
  retryLabel = 'Reintentar',
}: {
  error: ApiServiceError | Error
  onRetry: () => void
  retryLabel?: string
}) {
  if (error instanceof ApiServiceError && error.isMissingBcchToken) {
    return <MissingBcchTokenPanel message={error.message} onRetry={onRetry} />
  }
  return (
    <div className="service-error-box" role="alert">
      <p className="error">{error.message}</p>
      <button type="button" className="secondary-btn" onClick={onRetry}>
        {retryLabel}
      </button>
    </div>
  )
}

function extractSinimErrors(error: unknown): SinimErrorFila[] {
  if (!(error instanceof ApiServiceError) || !error.detalle) return []
  return normalizeSinimErrors(error.detalle.errores ?? error.detalle.errores_validacion)
}

export function PoliticalView() {
  const currentYear = new Date().getFullYear()
  const sliderId = useId()
  const numInputId = useId()
  const multiplierId = useId()
  const sinimInputId = useId()
  const dipresYearId = useId()
  const searchFreqId = useId()
  const searchQueryId = useId()
  const seriesIdInput = useId()
  const firstDateInput = useId()

  // Estado BCCh (Ejes 1, 2 y Simulador)
  const [bcch, setBcch] = useState<{
    loading: boolean
    data: EstructuraAysenResponse | null
    error: ApiServiceError | Error | null
  }>({ loading: true, data: null, error: null })
  const [axis2Mode, setAxis2Mode] = useState<'bars' | 'table'>('bars')

  // Estado Demografía INE + PIB per cápita (Eje 1 · silencioso si aún no está disponible)
  const [demografia, setDemografia] = useState<DemografiaPoblacionResponse | null>(null)

  // Estado DIPRES (Ejes 3 y 4)
  const [dipresYear, setDipresYear] = useState<number>(2025)
  const [dipres, setDipres] = useState<{
    loading: boolean
    data: DipresAysenResponse | null
    error: ApiServiceError | Error | null
  }>({ loading: true, data: null, error: null })

  // Estado SINIM (Eje 4)
  const [sinim, setSinim] = useState<{
    loading: boolean
    data: SinimAysenResponse | null
    error: ApiServiceError | Error | null
  }>({ loading: true, data: null, error: null })
  const [sinimUpload, setSinimUpload] = useState<{
    submitting: boolean
    selectedFileName: string
    successMessage: string
    errorMessage: string
    rowErrors: SinimErrorFila[]
  }>({
    submitting: false,
    selectedFileName: '',
    successMessage: '',
    errorMessage: '',
    rowErrors: [],
  })
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Estado Simulador
  const [deltaPct, setDeltaPct] = useState<number>(0)
  const [multiplier, setMultiplier] = useState<number>(1.0)

  // Estado Explorador vivo BCCh
  const [searchFreq, setSearchFreq] = useState<'ANNUAL' | 'QUARTERLY'>('ANNUAL')
  const [searchTerm, setSearchTerm] = useState<string>('Aysén')
  const [searchState, setSearchState] = useState<{
    loading: boolean
    data: BcchSearchResponse | null
    error: ApiServiceError | Error | null
  }>({ loading: false, data: null, error: null })
  const [manualSeriesId, setManualSeriesId] = useState<string>('')
  const [firstDate, setFirstDate] = useState<string>('2018-01-01')
  const [seriesState, setSeriesState] = useState<{
    loading: boolean
    data: BcchSeriesResponse | null
    error: ApiServiceError | Error | null
  }>({ loading: false, data: null, error: null })

  const loadBcch = useCallback(async (refresh = false, signal?: AbortSignal) => {
    setBcch(prev => ({ ...prev, loading: true, error: null }))
    try {
      const data = await fetchAysenEstructura(2013, currentYear, refresh, signal)
      if (!signal?.aborted) setBcch({ loading: false, data, error: null })
    } catch (err) {
      if (signal?.aborted || (err instanceof DOMException && err.name === 'AbortError')) return
      setBcch({
        loading: false,
        data: null,
        error: err instanceof Error ? err : new Error('Error desconocido al consultar BCCh.'),
      })
    }
  }, [currentYear])

  const loadDipres = useCallback(async (year: number, refresh = false, signal?: AbortSignal) => {
    setDipres(prev => ({ ...prev, loading: true, error: null }))
    try {
      const data = await fetchDipresAysen(year, refresh, signal)
      if (!signal?.aborted) setDipres({ loading: false, data, error: null })
    } catch (err) {
      if (signal?.aborted || (err instanceof DOMException && err.name === 'AbortError')) return
      setDipres({
        loading: false,
        data: null,
        error: err instanceof Error ? err : new Error('Error desconocido al consultar DIPRES.'),
      })
    }
  }, [])

  const loadSinim = useCallback(async (signal?: AbortSignal) => {
    setSinim(prev => ({ ...prev, loading: true, error: null }))
    try {
      const data = await fetchSinimAysen(signal)
      if (!signal?.aborted) setSinim({ loading: false, data, error: null })
    } catch (err) {
      if (signal?.aborted || (err instanceof DOMException && err.name === 'AbortError')) return
      setSinim({
        loading: false,
        data: null,
        error: err instanceof Error ? err : new Error('Error desconocido al consultar SINIM.'),
      })
    }
  }, [])

  const loadDemografiaSilenciosa = useCallback(async (signal?: AbortSignal) => {
    try {
      const data = await fetchDemografiaPoblacion(2013, currentYear, signal)
      if (!signal?.aborted && data.observaciones.length > 0) {
        setDemografia(data)
      }
    } catch {
      // Silencioso: si /api/v1/demografia/poblacion aún no está publicado, se mantiene el aviso de pendiente.
    }
  }, [currentYear])

  useEffect(() => {
    const controller = new AbortController()
    loadBcch(false, controller.signal)
    loadSinim(controller.signal)
    loadDemografiaSilenciosa(controller.signal)
    return () => controller.abort()
  }, [loadBcch, loadSinim, loadDemografiaSilenciosa])

  useEffect(() => {
    const controller = new AbortController()
    loadDipres(dipresYear, false, controller.signal)
    return () => controller.abort()
  }, [dipresYear, loadDipres])

  // Datos derivados BCCh (solo desde observaciones reales)
  const resumen = bcch.data?.resumen_pib ?? null

  // Datos derivados PIB per cápita oficial (BCCh + INE) para Eje 1
  const perCapitaEje1 = useMemo(() => {
    if (!demografia || demografia.observaciones.length === 0) return null
    const targetYear = resumen?.anio ?? demografia.ultimo_anio
    const pickYear = demografia.observaciones.some(o => o.anio === targetYear && o.territorio === '11')
      ? targetYear
      : demografia.ultimo_anio
    const aysen = demografia.observaciones.find(o => o.territorio === '11' && o.anio === pickYear) ?? null
    const chile = demografia.observaciones.find(o => o.territorio === 'CL' && o.anio === pickYear) ?? null
    if (!aysen || (aysen.pib_per_capita_real_clp === null && aysen.pib_per_capita_nominal_clp === null)) {
      return null
    }
    return { anio: pickYear, aysen, chile }
  }, [demografia, resumen?.anio])
  const actividadesOrdenadas = useMemo(() => {
    if (!bcch.data?.actividades) return []
    return [...bcch.data.actividades].sort((a, b) => {
      const av = a.participacion_pct ?? a.valor_millones ?? -Infinity
      const bv = b.participacion_pct ?? b.valor_millones ?? -Infinity
      return bv - av
    })
  }, [bcch.data])

  const adminActivity = useMemo(
    () => actividadesOrdenadas.find(isAdminPublica) ?? null,
    [actividadesOrdenadas],
  )
  const pescaActivity = useMemo(
    () => actividadesOrdenadas.find(isPesca) ?? null,
    [actividadesOrdenadas],
  )
  const hhiInfo = useMemo(() => extractHhiInfo(bcch.data), [bcch.data])

  const maxActivityPct = useMemo(() => {
    const values = actividadesOrdenadas
      .map(item => item.participacion_pct ?? 0)
      .filter(value => Number.isFinite(value) && value > 0)
    return values.length ? Math.max(...values) : 1
  }, [actividadesOrdenadas])

  // Datos derivados DIPRES
  const dipresCorriente = dipres.data?.gore_aysen?.gasto_corriente_sub_21_26_millones ?? null
  const dipresInversion = dipres.data?.gore_aysen?.inversion_sub_29_31_millones ?? null
  const dipresSub33 = dipres.data?.gore_aysen?.transferencias_capital_sub_33_millones ?? null
  const dipresPartida31 = dipres.data?.gore_aysen?.financiamiento_partida_31_millones ?? null

  const dipresRatio = useMemo(() => {
    if (dipres.data?.ratio_corriente_sobre_inversion_pct !== null && dipres.data?.ratio_corriente_sobre_inversion_pct !== undefined) {
      return dipres.data.ratio_corriente_sobre_inversion_pct
    }
    if (dipresCorriente !== null && dipresCorriente > 0 && dipresInversion !== null && dipresInversion > 0) {
      return (dipresCorriente / dipresInversion) * 100
    }
    return null
  }, [dipres.data, dipresCorriente, dipresInversion])

  // Datos derivados SINIM
  const sinimExpected = sinim.data?.total_comunas_esperadas ?? 10
  const sinimLoaded = sinim.data?.comunas_cargadas ?? sinim.data?.comunas.length ?? 0
  const sinimCoveragePct = sinim.data?.cobertura_pct !== undefined && sinim.data?.cobertura_pct !== null
    ? sinim.data.cobertura_pct
    : sinimExpected > 0
      ? (sinimLoaded / sinimExpected) * 100
      : 0

  const sinimGastoTotalBrutoMillones = useMemo(() => {
    if (sinim.data?.total_gasto_devengado_millones !== null && sinim.data?.total_gasto_devengado_millones !== undefined) {
      return sinim.data.total_gasto_devengado_millones
    }
    if (!sinim.data?.comunas.length) return null
    const valid = sinim.data.comunas
      .map(c => c.gasto_total_devengado_millones)
      .filter((v): v is number => v !== null && v !== undefined && Number.isFinite(v))
    if (!valid.length) return null
    return valid.reduce((acc, v) => acc + v, 0)
  }, [sinim.data])

  // Datos derivados Simulador (100% reales BCCh)
  const simAdminBase = resumen?.administracion_publica_millones ?? adminActivity?.valor_millones ?? null
  const simPibBase = resumen?.aysen_nominal_millones ?? null
  const simReady = simAdminBase !== null && simPibBase !== null && simPibBase > 0

  const simulation = useMemo(() => {
    if (!simReady || simAdminBase === null || simPibBase === null) return null
    const deltaAdmin = simAdminBase * (deltaPct / 100)
    const deltaPib = deltaAdmin * multiplier
    const adminSimulated = simAdminBase + deltaAdmin
    const pibSimulated = simPibBase + deltaPib
    const impactPibPp = (deltaPib / simPibBase) * 100
    const baseAdminSharePct = (simAdminBase / simPibBase) * 100
    const simAdminSharePct = pibSimulated > 0 ? (adminSimulated / pibSimulated) * 100 : null
    return {
      deltaAdmin,
      deltaPib,
      adminSimulated,
      pibSimulated,
      impactPibPp,
      baseAdminSharePct,
      simAdminSharePct,
    }
  }, [simReady, simAdminBase, simPibBase, deltaPct, multiplier])

  const selectedMultiplierInfo = MULTIPLIERS.find(m => m.value === multiplier) ?? MULTIPLIERS[0]

  // Handlers SINIM Importador
  function handleFileSelected(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    setSinimUpload(prev => ({
      ...prev,
      selectedFileName: file?.name ?? '',
      successMessage: '',
      errorMessage: '',
      rowErrors: [],
    }))
  }

  async function handleSinimImport(event: FormEvent) {
    event.preventDefault()
    const file = fileInputRef.current?.files?.[0]
    if (!file) {
      setSinimUpload(prev => ({
        ...prev,
        errorMessage: 'Selecciona un archivo .csv o .json de SINIM antes de importar.',
        successMessage: '',
        rowErrors: [],
      }))
      return
    }
    const lower = file.name.toLowerCase()
    if (!lower.endsWith('.csv') && !lower.endsWith('.json')) {
      setSinimUpload(prev => ({
        ...prev,
        errorMessage: 'Formato no admitido. Sube un archivo .csv o .json estructurado según la plantilla oficial.',
        successMessage: '',
        rowErrors: [],
      }))
      return
    }

    setSinimUpload(prev => ({
      ...prev,
      submitting: true,
      successMessage: '',
      errorMessage: '',
      rowErrors: [],
    }))

    try {
      const content = await file.text()
      if (!content.trim()) {
        setSinimUpload(prev => ({
          ...prev,
          submitting: false,
          errorMessage: 'El archivo seleccionado está vacío.',
        }))
        return
      }
      const response = await importSinimFile(file.name, content)
      setSinim({ loading: false, data: response, error: null })
      const errors = response.errores_validacion ?? []
      setSinimUpload({
        submitting: false,
        selectedFileName: file.name,
        successMessage: response.mensaje ||
          `Archivo «${file.name}» procesado. Cobertura actual: ${response.comunas_cargadas} / ${response.total_comunas_esperadas} comunas de Aysén.`,
        errorMessage: '',
        rowErrors: errors,
      })
    } catch (err) {
      const rowErrors = extractSinimErrors(err)
      setSinimUpload(prev => ({
        ...prev,
        submitting: false,
        successMessage: '',
        errorMessage: err instanceof Error ? err.message : 'No se pudo validar o importar el archivo SINIM.',
        rowErrors,
      }))
    }
  }

  // Handlers Explorador BCCh
  async function handleBcchSearch(event: FormEvent) {
    event.preventDefault()
    if (!searchTerm.trim()) return
    setSearchState({ loading: true, data: null, error: null })
    try {
      const res = await searchBcchSeries(searchFreq, searchTerm)
      setSearchState({ loading: false, data: res, error: null })
    } catch (err) {
      setSearchState({
        loading: false,
        data: null,
        error: err instanceof Error ? err : new Error('No se pudo consultar el catálogo del BCCh.'),
      })
    }
  }

  async function handleInspectSeries(seriesId: string) {
    const cleanId = seriesId.trim()
    if (!cleanId) return
    setManualSeriesId(cleanId)
    setSeriesState({ loading: true, data: null, error: null })
    try {
      const res = await fetchBcchSeries(cleanId, firstDate || undefined)
      setSeriesState({ loading: false, data: res, error: null })
    } catch (err) {
      setSeriesState({
        loading: false,
        data: null,
        error: err instanceof Error ? err : new Error('No se pudo consultar la serie en el BCCh.'),
      })
    }
  }

  function handleNumericDeltaChange(raw: string) {
    const parsed = Number(raw)
    if (!Number.isFinite(parsed)) {
      setDeltaPct(0)
      return
    }
    const clamped = Math.max(-30, Math.min(30, Math.round(parsed * 2) / 2))
    setDeltaPct(clamped)
  }

  const bcchSourceBase: SourceFooterProps = {
    fuente: bcch.data?.fuente_trazabilidad,
    institucionFallback: 'Banco Central de Chile (BDE · Cuentas Nacionales)',
    endpointFallback: '/api/v1/territorial/aysen/estructura',
    actualizadoEn: bcch.data?.actualizado_en ?? bcch.data?.fuente_trazabilidad?.actualizado_en,
    extraidoEn: bcch.data?.extraido_en ?? bcch.data?.fuente_trazabilidad?.extraido_en,
  }

  const dipresSourceBase: SourceFooterProps = {
    fuente: dipres.data?.fuente_trazabilidad,
    institucionFallback: 'DIPRES · datos.gob.cl (CKAN)',
    endpointFallback: `/api/v1/fiscal/dipres?anio=${dipresYear}`,
    actualizadoEn: dipres.data?.actualizado_en ?? dipres.data?.fuente_trazabilidad?.actualizado_en,
    extraidoEn: dipres.data?.extraido_en ?? dipres.data?.fuente_trazabilidad?.extraido_en,
  }

  const sinimSourceBase: SourceFooterProps = {
    fuente: sinim.data?.fuente_trazabilidad,
    institucionFallback: 'SINIM · SUBDERE (Balances Municipales)',
    endpointFallback: '/api/v1/fiscal/sinim',
    actualizadoEn: sinim.data?.actualizado_en ?? sinim.data?.fuente_trazabilidad?.actualizado_en,
    extraidoEn: sinim.data?.extraido_en ?? sinim.data?.fuente_trazabilidad?.extraido_en,
  }

  const consultadas = bcch.data?.fuente_trazabilidad?.series_consultadas ?? []
  const bcchAxis1Codes = [
    resumen?.serie_aysen_nominal,
    resumen?.serie_chile_nominal,
    resumen?.serie_aysen_real,
    resumen?.serie_chile_real,
    ...consultadas.filter(code => code.includes('.Z.Z.Z.')),
  ].filter((c, i, arr): c is string => Boolean(c) && arr.indexOf(c) === i)

  const bcchSimCodes = [
    resumen?.serie_admin_publica || adminActivity?.serie_id,
    resumen?.serie_aysen_nominal || consultadas.find(code => code.includes('.N.') && code.includes('.11.') && code.includes('.Z.')),
  ].filter((c, i, arr): c is string => Boolean(c) && arr.indexOf(c) === i)

  return (
    <div className="political-page">
      <section className="intro pol-intro">
        <div>
          <p className="eyebrow">Observatorio territorial · Región de Aysén (Código 11)</p>
          <h1>Lectura Política y Estratégica</h1>
          <p className="lede">
            Diagnóstico en vivo de la estructura productiva y fiscal de la Región de Aysén del General Carlos Ibáñez del Campo.
            Cada cifra proviene de consultas directas a BCCh, DIPRES y SINIM con trazabilidad verificable y límites de inferencia explícitos.
          </p>
        </div>
        <div className="pol-status-bar" aria-label="Estado de fuentes en vivo">
          <div className="pol-source-pill">
            <span className={`status-dot ${bcch.loading ? 'is-loading' : bcch.error ? 'is-error' : 'is-ok'}`} aria-hidden="true" />
            <div>
              <strong>BCCh</strong>
              <span>
                {bcch.loading
                  ? 'Consultando…'
                  : bcch.error instanceof ApiServiceError && bcch.error.isMissingBcchToken
                    ? 'Falta token'
                    : bcch.error
                      ? 'Sin conexión'
                      : `Corte ${resumen?.anio ?? 'en vivo'}`}
              </span>
            </div>
          </div>
          <div className="pol-source-pill">
            <span className={`status-dot ${dipres.loading ? 'is-loading' : dipres.error ? 'is-error' : 'is-ok'}`} aria-hidden="true" />
            <div>
              <strong>DIPRES</strong>
              <span>
                {dipres.loading ? 'Consultando…' : dipres.error ? 'Sin conexión' : `Ejercicio ${dipres.data?.anio ?? dipresYear}`}
              </span>
            </div>
          </div>
          <div className="pol-source-pill">
            <span className={`status-dot ${sinim.loading ? 'is-loading' : sinim.error ? 'is-error' : sinimLoaded === sinimExpected ? 'is-ok' : 'is-warn'}`} aria-hidden="true" />
            <div>
              <strong>SINIM</strong>
              <span>
                {sinim.loading ? 'Consultando…' : sinim.error ? 'Sin conexión' : `${sinimLoaded}/${sinimExpected} comunas`}
              </span>
            </div>
          </div>
          <button
            type="button"
            className="secondary-btn"
            onClick={() => {
              loadBcch(true)
              loadDipres(dipresYear, true)
              loadSinim()
              loadDemografiaSilenciosa()
            }}
          >
            Actualizar fuentes
          </button>
        </div>
      </section>

      <nav className="pol-toc" aria-label="Navegación por ejes estratégicos">
        <a href="#eje-1">Eje 1 · Centro-Periferia</a>
        <a href="#eje-2">Eje 2 · Estado Motor Local</a>
        <a href="#eje-3">Eje 3 · Rigidez Descentralización</a>
        <a href="#eje-4">Eje 4 · 3 Billeteras y SINIM</a>
        <a href="#simulador-aysen">Simulador PIB</a>
        <a href="#explorador-bcch">Explorador BCCh</a>
      </nav>

      {/* ============================================================
          EJE 1 · PARADOJA CENTRO-PERIFERIA
      ============================================================ */}
      <section id="eje-1" className="axis-section" aria-labelledby="eje-1-titulo">
        <div className="axis-header">
          <span className="axis-badge">Eje 1</span>
          <div>
            <h2 id="eje-1-titulo">Paradoja Centro-Periferia</h2>
            <p className="subtle">Peso nominal de Aysén en el PIB nacional frente a su dinámica de crecimiento real y su relevancia territorial.</p>
          </div>
        </div>

        <div className="axis-grid">
          <article className="panel axis-main">
            <h3>Escala macroeconómica de Aysén frente a Chile</h3>
            {bcch.loading ? (
              <LoadingSkeleton label="Consultando series oficiales de PIB regional y nacional en BCCh…" />
            ) : bcch.error ? (
              <ServiceErrorBox error={bcch.error} onRetry={() => loadBcch(true)} />
            ) : !resumen ? (
              <p className="empty">El servicio BCCh no devolvió un resumen de PIB para el período solicitado.</p>
            ) : (
              <>
                {bcch.data?.estado_actualizacion === 'respaldo_ultimo_corte_aprobado' && (
                  <p className="notice" role="status">
                    <strong>Respaldo del último corte aprobado (BCCh):</strong>{' '}
                    {bcch.data.advertencia_respaldo ||
                      'La actualización en vivo no respondió; se muestran las observaciones verificadas del último corte oficial guardado.'}
                  </p>
                )}

                <div className="pol-kpi-grid">
                  <div className="pol-kpi-card is-highlight">
                    <span className="kpi-label">Participación en PIB nacional nominal ({resumen.anio ?? '—'})</span>
                    <strong className="pol-kpi-num">{fmtPct(resumen.participacion_nacional_pct)}</strong>
                    <span className="kpi-meta">Precios corrientes · Aysén / Chile</span>
                  </div>
                  <div className="pol-kpi-card">
                    <span className="kpi-label">PIB nominal Aysén ({resumen.anio ?? '—'})</span>
                    <strong className="pol-kpi-num">{fmtMillions(resumen.aysen_nominal_millones)}</strong>
                    <span className="kpi-meta">Chile: {fmtMillions(resumen.chile_nominal_millones)}</span>
                  </div>
                  <div className="pol-kpi-card">
                    <span className="kpi-label">PIB real Aysén ({resumen.anio ?? '—'})</span>
                    <strong className="pol-kpi-num">{fmtMillions(resumen.aysen_real_millones)}</strong>
                    <span className="kpi-meta">Volumen encadenado (no aditivo) · Chile: {fmtMillions(resumen.chile_real_millones)}</span>
                  </div>
                  <div className="pol-kpi-card">
                    <span className="kpi-label">Crecimiento real anual ({resumen.anio ?? '—'})</span>
                    <strong className="pol-kpi-num">{fmtPct(resumen.crecimiento_real_aysen_pct, true)}</strong>
                    <span className="kpi-meta">Referencia Chile: {fmtPct(resumen.crecimiento_real_chile_pct, true)}</span>
                  </div>
                </div>

                {/* Visualización comparativa de peso y crecimiento real */}
                <div className="visual-card">
                  <h4>Comparación visual · Peso nominal y variación real ({resumen.anio ?? '—'})</h4>
                  <div className="compare-bars" role="img" aria-label={`Participación nominal de Aysén ${fmtPct(resumen.participacion_nacional_pct)} y crecimiento real Aysén ${fmtPct(resumen.crecimiento_real_aysen_pct, true)} frente a Chile ${fmtPct(resumen.crecimiento_real_chile_pct, true)}`}>
                    <div className="compare-bar-row">
                      <span className="compare-bar-label">Peso nominal de Aysén en Chile</span>
                      <div className="compare-track" aria-hidden="true">
                        <div
                          className="compare-fill is-primary"
                          style={{
                            width: `${resumen.participacion_nacional_pct !== null ? Math.min(100, Math.max(1.5, resumen.participacion_nacional_pct)) : 0}%`,
                          }}
                        />
                      </div>
                      <span className="compare-bar-val">{fmtPct(resumen.participacion_nacional_pct)}</span>
                    </div>

                    {(() => {
                      const a = resumen.crecimiento_real_aysen_pct
                      const c = resumen.crecimiento_real_chile_pct
                      const maxAbs = Math.max(1, Math.abs(a ?? 0), Math.abs(c ?? 0))
                      return (
                        <>
                          <div className="compare-bar-row">
                            <span className="compare-bar-label">Crecimiento real Aysén</span>
                            <div className="compare-track is-diverging" aria-hidden="true">
                              {a !== null && (
                                <div
                                  className={`compare-fill ${a < 0 ? 'is-negative' : 'is-primary'}`}
                                  style={{
                                    width: `${(Math.abs(a) / maxAbs) * 50}%`,
                                    left: `${a < 0 ? 50 - (Math.abs(a) / maxAbs) * 50 : 50}%`,
                                  }}
                                />
                              )}
                            </div>
                            <span className="compare-bar-val">{fmtPct(a, true)}</span>
                          </div>
                          <div className="compare-bar-row">
                            <span className="compare-bar-label">Crecimiento real Chile</span>
                            <div className="compare-track is-diverging" aria-hidden="true">
                              {c !== null && (
                                <div
                                  className={`compare-fill ${c < 0 ? 'is-negative' : 'is-reference'}`}
                                  style={{
                                    width: `${(Math.abs(c) / maxAbs) * 50}%`,
                                    left: `${c < 0 ? 50 - (Math.abs(c) / maxAbs) * 50 : 50}%`,
                                  }}
                                />
                              )}
                            </div>
                            <span className="compare-bar-val">{fmtPct(c, true)}</span>
                          </div>
                        </>
                      )
                    })()}
                  </div>

                  <div className="table-scroll pol-table-gap" tabIndex={0} role="region" aria-label="Tabla resumen PIB Aysén frente a Chile">
                    <table className="pol-table">
                      <caption className="sr-only">Indicadores macroeconómicos oficiales de Aysén y Chile en {resumen.anio ?? 'último año disponible'}</caption>
                      <thead>
                        <tr>
                          <th scope="col">Indicador</th>
                          <th scope="col" className="numeric">Aysén (Región 11)</th>
                          <th scope="col" className="numeric">Chile (Total)</th>
                          <th scope="col">Valoración</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr>
                          <th scope="row">PIB nominal ({resumen.anio ?? '—'})</th>
                          <td className="numeric">{fmtMillions(resumen.aysen_nominal_millones)}</td>
                          <td className="numeric">{fmtMillions(resumen.chile_nominal_millones)}</td>
                          <td>Precios corrientes</td>
                        </tr>
                        <tr>
                          <th scope="row">PIB real ({resumen.anio ?? '—'})</th>
                          <td className="numeric">{fmtMillions(resumen.aysen_real_millones)}</td>
                          <td className="numeric">{fmtMillions(resumen.chile_real_millones)}</td>
                          <td>Volumen encadenado</td>
                        </tr>
                        <tr>
                          <th scope="row">Crecimiento real anual</th>
                          <td className="numeric">{fmtPct(resumen.crecimiento_real_aysen_pct, true)}</td>
                          <td className="numeric">{fmtPct(resumen.crecimiento_real_chile_pct, true)}</td>
                          <td>Variación anual volumen</td>
                        </tr>
                        <tr>
                          <th scope="row">Participación nominal en el país</th>
                          <td className="numeric">{fmtPct(resumen.participacion_nacional_pct)}</td>
                          <td className="numeric">100,00%</td>
                          <td>Precios corrientes</td>
                        </tr>
                        {perCapitaEje1 && (
                          <>
                            <tr className="row-admin">
                              <th scope="row">PIB per cápita real ({perCapitaEje1.anio} · BCCh + INE)</th>
                              <td className="numeric">{fmtClp(perCapitaEje1.aysen.pib_per_capita_real_clp)}</td>
                              <td className="numeric">{fmtClp(perCapitaEje1.chile?.pib_per_capita_real_clp)}</td>
                              <td>
                                CLP/hab. · Aysén = {perCapitaEje1.aysen.indice_real_chile_100 !== null ? num1.format(perCapitaEje1.aysen.indice_real_chile_100) : '—'} (Chile = 100)
                              </td>
                            </tr>
                            <tr className="row-admin">
                              <th scope="row">PIB per cápita nominal ({perCapitaEje1.anio} · BCCh + INE)</th>
                              <td className="numeric">{fmtClp(perCapitaEje1.aysen.pib_per_capita_nominal_clp)}</td>
                              <td className="numeric">{fmtClp(perCapitaEje1.chile?.pib_per_capita_nominal_clp)}</td>
                              <td>
                                CLP/hab. · Aysén = {perCapitaEje1.aysen.indice_nominal_chile_100 !== null ? num1.format(perCapitaEje1.aysen.indice_nominal_chile_100) : '—'} (Chile = 100)
                              </td>
                            </tr>
                          </>
                        )}
                      </tbody>
                    </table>
                  </div>
                  {perCapitaEje1 && (
                    <div className="eje1-pc-banner">
                      <div>
                        <strong>PIB per cápita oficial acoplado (BCCh + INE · {perCapitaEje1.anio}):</strong>{' '}
                        Aysén registra <strong>{fmtClp(perCapitaEje1.aysen.pib_per_capita_real_clp)}</strong> reales por habitante
                        {perCapitaEje1.chile?.pib_per_capita_real_clp !== null && perCapitaEje1.chile?.pib_per_capita_real_clp !== undefined
                          ? ` frente a ${fmtClp(perCapitaEje1.chile.pib_per_capita_real_clp)} en Chile`
                          : ''}
                        {' '}(nominal: {fmtClp(perCapitaEje1.aysen.pib_per_capita_nominal_clp)} vs {fmtClp(perCapitaEje1.chile?.pib_per_capita_nominal_clp)}).
                      </div>
                      <a className="secondary-btn link-btn" href="#demografia">
                        Ver módulo PIB per Cápita y Convergencia →
                      </a>
                    </div>
                  )}
                  <SourceFooter
                    {...bcchSourceBase}
                    seriesCodigos={bcchAxis1Codes}
                    notaExtra="Valores nominales y reales se reportan por separado respetando la no aditividad de volúmenes encadenados."
                  />
                </div>
              </>
            )}
            <SourceFooter {...bcchSourceBase} seriesCodigos={bcchAxis1Codes} />
          </article>

          <KeyTerritorialCard
            ejeLabel="Eje 1 · Paradoja Centro-Periferia"
            title="Bajo peso agregado, alta relevancia geoestratégica"
            summary={
              <>
                <p>
                  En el corte oficial vigente del Banco Central{resumen?.anio ? ` (${resumen.anio})` : ''}, Aysén representa{' '}
                  <strong>{resumen ? fmtPct(resumen.participacion_nacional_pct) : 'sin dato oficial disponible'}</strong> del PIB nominal de Chile.
                  Esta fracción reducida en la escala agregada nacional suele invisibilizar a la región en reglas de asignación central basadas en volumen bruto.
                </p>
                {perCapitaEje1 ? (
                  <p>
                    Al cruzar las cuentas regionales del <strong>BCCh</strong> con la población oficial del <strong>INE ({perCapitaEje1.anio})</strong>, el{' '}
                    <strong>PIB per cápita real de Aysén alcanza {fmtClp(perCapitaEje1.aysen.pib_per_capita_real_clp)}</strong>{' '}
                    (nominal: <strong>{fmtClp(perCapitaEje1.aysen.pib_per_capita_nominal_clp)}</strong>), frente a{' '}
                    <strong>{fmtClp(perCapitaEje1.chile?.pib_per_capita_real_clp)}</strong> reales en Chile
                    {perCapitaEje1.aysen.indice_real_chile_100 !== null
                      ? ` (índice ${num1.format(perCapitaEje1.aysen.indice_real_chile_100)} con Chile = 100)`
                      : ''}.
                    El bajo peso agregado coexiste así con una producción por habitante comparable o superior al promedio nacional.
                  </p>
                ) : (
                  <p>
                    Sin embargo, Aysén ocupa una vasta superficie austral con baja densidad poblacional y valor geoestratégico en conectividad, soberanía y recursos naturales.
                    <strong> Nota sobre PIB per cápita:</strong> el cálculo per cápita exacto queda explícitamente pendiente de acoplar la serie censal y de proyecciones poblacionales oficiales del <strong>INE</strong>; este observatorio no introduce denominadores demográficos fijos.
                  </p>
                )}
              </>
            }
            evidenciaFavorable="La participación nominal observada confirma un peso reducido en el total nacional, lo que genera asimetría de visibilidad cuando los criterios fiscales premian escala poblacional o recaudación agregada."
            evidenciaContraria="Un bajo peso agregado no implica por sí mismo estancamiento económico: la variación real anual y el producto por habitante de Aysén pueden divergir significativamente del promedio nacional por escala demográfica y shocks sectoriales específicos."
            limiteInferencia="El PIB nominal y per cápita regional miden producción localizada en el territorio (escala nacional y regional, nunca imputable a comunas) y no equivalen directamente al ingreso disponible de los hogares."
            source={{ ...bcchSourceBase, seriesCodigos: bcchAxis1Codes }}
          />
        </div>
      </section>

      {/* ============================================================
          EJE 2 · EL ESTADO COMO MOTOR ECONÓMICO LOCAL
      ============================================================ */}
      <section id="eje-2" className="axis-section" aria-labelledby="eje-2-titulo">
        <div className="axis-header">
          <span className="axis-badge">Eje 2</span>
          <div>
            <h2 id="eje-2-titulo">El Estado como Motor Económico Local</h2>
            <p className="subtle">Desglose de las 13 actividades económicas oficiales de Aysén, concentración HHI y seguimiento trimestral reciente.</p>
          </div>
        </div>

        <div className="axis-grid">
          <article className="panel axis-main">
            <div className="axis-main-top">
              <div>
                <h3>Estructura sectorial del PIB nominal de Aysén</h3>
                <p className="subtle">
                  Series oficiales <code className="mono">F035.PIB.FLU.N.CLP.2018.*.11.0.A</code>
                  {resumen?.anio ? ` · Año ${resumen.anio}` : ''}
                </p>
              </div>
              {bcch.data && actividadesOrdenadas.length > 0 && (
                <div className="view-switch compact-switch" role="group" aria-label="Formato de actividades económicas">
                  <button type="button" aria-pressed={axis2Mode === 'bars'} onClick={() => setAxis2Mode('bars')}>
                    Barras proporcionales
                  </button>
                  <button type="button" aria-pressed={axis2Mode === 'table'} onClick={() => setAxis2Mode('table')}>
                    Tabla completa
                  </button>
                </div>
              )}
            </div>

            {bcch.loading ? (
              <LoadingSkeleton label="Consultando las 13 actividades económicas y series trimestrales de Aysén en BCCh…" />
            ) : bcch.error ? (
              <ServiceErrorBox error={bcch.error} onRetry={() => loadBcch(true)} />
            ) : !bcch.data || actividadesOrdenadas.length === 0 ? (
              <p className="empty">No se recibieron observaciones de actividades económicas para Aysén en este corte.</p>
            ) : (
              <>
                <div className="pol-kpi-grid is-three">
                  <div className="pol-kpi-card is-highlight">
                    <span className="kpi-label">Administración Pública</span>
                    <strong className="pol-kpi-num">
                      {fmtPct(resumen?.administracion_publica_pct ?? adminActivity?.participacion_pct)}
                    </strong>
                    <span className="kpi-meta">
                      {fmtMillions(resumen?.administracion_publica_millones ?? adminActivity?.valor_millones)}
                    </span>
                  </div>
                  <div className="pol-kpi-card">
                    <span className="kpi-label">Pesca y Acuicultura</span>
                    <strong className="pol-kpi-num">
                      {fmtPct(resumen?.pesca_pct ?? pescaActivity?.participacion_pct)}
                    </strong>
                    <span className="kpi-meta">
                      {fmtMillions(resumen?.pesca_millones ?? pescaActivity?.valor_millones)}
                    </span>
                  </div>
                  <div className="pol-kpi-card">
                    <span className="kpi-label">Índice de concentración HHI</span>
                    <strong className="pol-kpi-num">
                      {hhiInfo.indice !== null ? num0.format(hhiInfo.indice) : 'Sin dato'}
                    </strong>
                    <span className="kpi-meta">
                      {hhiInfo.interpretacion || `Escala ${hhiInfo.escala} · ${actividadesOrdenadas.length} actividades`}
                    </span>
                  </div>
                </div>

                <div className="visual-card">
                  <h4>Participación por actividad económica ({actividadesOrdenadas.length} actividades oficiales)</h4>
                  {axis2Mode === 'bars' ? (
                    <ul className="activity-chart" aria-label="Participación de las actividades económicas en el PIB nominal de Aysén">
                      {actividadesOrdenadas.map(item => {
                        const highlightAdmin = isAdminPublica(item)
                        const highlightPesca = isPesca(item)
                        const widthPct = item.participacion_pct !== null && maxActivityPct > 0
                          ? Math.max(1.5, (item.participacion_pct / maxActivityPct) * 100)
                          : 0
                        return (
                          <li
                            key={item.serie_id || item.codigo}
                            className={`activity-row${highlightAdmin ? ' is-admin' : highlightPesca ? ' is-pesca' : ''}`}
                          >
                            <div className="activity-name">
                              <span>{item.nombre}</span>
                              {highlightAdmin && <span className="mini-tag is-admin">Estado</span>}
                              {highlightPesca && <span className="mini-tag is-pesca">Sector exportador</span>}
                            </div>
                            <span className="activity-track" aria-hidden="true">
                              {item.participacion_pct !== null && (
                                <span className="activity-bar" style={{ width: `${widthPct}%` }} />
                              )}
                            </span>
                            <div className="activity-values">
                              <strong>{fmtPct(item.participacion_pct)}</strong>
                              <span className="subtle">{fmtMillions(item.valor_millones)}</span>
                            </div>
                          </li>
                        )
                      })}
                    </ul>
                  ) : (
                    <div className="table-scroll" tabIndex={0} role="region" aria-label="Tabla de actividades económicas de Aysén">
                      <table className="pol-table">
                        <caption className="sr-only">Actividades económicas oficiales de Aysén, valor nominal en millones CLP y participación porcentual</caption>
                        <thead>
                          <tr>
                            <th scope="col">Actividad económica</th>
                            <th scope="col">Serie BDE</th>
                            <th scope="col" className="numeric">Valor (MM$ CLP)</th>
                            <th scope="col" className="numeric">Participación</th>
                          </tr>
                        </thead>
                        <tbody>
                          {actividadesOrdenadas.map(item => (
                            <tr
                              key={item.serie_id || item.codigo}
                              className={isAdminPublica(item) ? 'row-admin' : isPesca(item) ? 'row-pesca' : undefined}
                            >
                              <th scope="row">{item.nombre}</th>
                              <td className="mono">{item.serie_id}</td>
                              <td className="numeric">{fmtMillions(item.valor_millones)}</td>
                              <td className="numeric">{fmtPct(item.participacion_pct)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                  <SourceFooter
                    {...bcchSourceBase}
                    seriesCodigos={actividadesOrdenadas.slice(0, 3).map(a => a.serie_id)}
                    notaExtra={`Total series sectoriales consultadas: ${actividadesOrdenadas.length}.`}
                  />
                </div>

                {/* Observaciones trimestrales recientes */}
                {bcch.data.trimestral && bcch.data.trimestral.length > 0 && (
                  <div className="visual-card">
                    <h4>Seguimiento trimestral reciente (coyuntura Aysén)</h4>
                    <div className="quarterly-grid">
                      {bcch.data.trimestral.map(serie => {
                        const latestObs = serie.observaciones?.at(-1)
                        const recent = (serie.observaciones ?? []).slice(-4).reverse()
                        return (
                          <div key={serie.serie_id} className="quarterly-card">
                            <div className="quarterly-head">
                              <strong>{serie.nombre}</strong>
                              <code className="mono">{serie.serie_id}</code>
                            </div>
                            <div className="quarterly-highlight">
                              <span>Último dato ({serie.ultimo_periodo ?? latestObs?.periodo ?? latestObs?.fecha ?? '—'}):</span>
                              <strong>
                                {serie.ultima_variacion_pct !== undefined && serie.ultima_variacion_pct !== null
                                  ? fmtPct(serie.ultima_variacion_pct, true)
                                  : latestObs?.variacion_interanual_pct !== undefined && latestObs?.variacion_interanual_pct !== null
                                    ? fmtPct(latestObs.variacion_interanual_pct, true)
                                    : serie.ultimo_valor !== undefined && serie.ultimo_valor !== null
                                      ? num2.format(serie.ultimo_valor)
                                      : latestObs?.valor !== null && latestObs?.valor !== undefined
                                        ? num2.format(latestObs.valor)
                                        : 'Sin dato'}
                              </strong>
                            </div>
                            {recent.length > 0 && (
                              <div className="table-scroll" tabIndex={0} role="region" aria-label={`Últimos trimestres de ${serie.nombre}`}>
                                <table className="pol-table is-compact">
                                  <thead>
                                    <tr>
                                      <th scope="col">Período</th>
                                      <th scope="col" className="numeric">Valor</th>
                                      <th scope="col" className="numeric">Var. interanual</th>
                                    </tr>
                                  </thead>
                                  <tbody>
                                    {recent.map((obs, idx) => (
                                      <tr key={`${serie.serie_id}-${obs.fecha}-${idx}`}>
                                        <td>{obs.periodo || obs.fecha}</td>
                                        <td className="numeric">{obs.valor !== null ? num2.format(obs.valor) : 'Sin dato'}</td>
                                        <td className="numeric">
                                          {obs.variacion_interanual_pct !== undefined && obs.variacion_interanual_pct !== null
                                            ? fmtPct(obs.variacion_interanual_pct, true)
                                            : '—'}
                                        </td>
                                      </tr>
                                    ))}
                                  </tbody>
                                </table>
                              </div>
                            )}
                            <SourceFooter
                              {...bcchSourceBase}
                              seriesCodigos={[serie.serie_id]}
                            />
                          </div>
                        )
                      })}
                    </div>
                  </div>
                )}

                {bcch.data.series_faltantes && bcch.data.series_faltantes.length > 0 && (
                  <p className="notice">
                    <strong>Series sin dato en el corte:</strong>{' '}
                    {bcch.data.series_faltantes.map(s => `${s.nombre || s.serie_id}${s.motivo ? ` (${s.motivo})` : ''}`).join(' · ')}
                  </p>
                )}
              </>
            )}
            <SourceFooter
              {...bcchSourceBase}
              seriesCodigos={[resumen?.serie_admin_publica || adminActivity?.serie_id || 'F035.PIB.FLU.N.CLP.2018.*.11.0.A']}
            />
          </article>

          <KeyTerritorialCard
            ejeLabel="Eje 2 · Estado como Motor Local"
            title="Peso estructural de Administración Pública y concentración productiva"
            summary={
              <>
                <p>
                  En la composición oficial del PIB nominal de Aysén, <strong>Administración Pública</strong> representa{' '}
                  <strong>{fmtPct(resumen?.administracion_publica_pct ?? adminActivity?.participacion_pct)}</strong>{' '}
                  ({fmtMillions(resumen?.administracion_publica_millones ?? adminActivity?.valor_millones)}), mientras que{' '}
                  <strong>Pesca y Acuicultura</strong> aporta{' '}
                  <strong>{fmtPct(resumen?.pesca_pct ?? pescaActivity?.participacion_pct)}</strong>.
                </p>
                <p>
                  El índice <strong>HHI observado ({hhiInfo.indice !== null ? num0.format(hhiInfo.indice) : 'sin dato'})</strong> resume el grado de concentración en pocas ramas productivas.
                  Cuando el sector público y un único complejo exportador concentran una fracción elevada del producto regional, la economía territorial se vuelve altamente sensible tanto a decisiones presupuestarias centrales como a ciclos biológicos o de precios externos.
                </p>
              </>
            }
            evidenciaFavorable="La participación observada de Administración Pública en las cuentas nacionales confirma que el aparato estatal constituye uno de los pilares de mayor tamaño relativo dentro de la estructura productiva local."
            evidenciaContraria="El valor agregado de Administración Pública en Cuentas Nacionales se valora principalmente por costos de remuneraciones y consumo de capital fijo, lo que tiende a sobrerrepresentar su peso nominal relativo cuando el sector privado transable sufre caídas de precios."
            limiteInferencia="Una alta participación contable del sector público en el PIB regional es una relación descriptiva; no equivale a demostrar causalidad automática de dependencia ni a estimar un multiplicador fiscal sin diseño contrafactual."
            source={{
              ...bcchSourceBase,
              seriesCodigos: [resumen?.serie_admin_publica || adminActivity?.serie_id || 'F035.PIB.FLU.N.CLP.2018.*.11.0.A'],
            }}
          />
        </div>
      </section>

      {/* ============================================================
          EJE 3 · RIGIDEZ OPERATIVA DE LA DESCENTRALIZACIÓN (DIPRES)
      ============================================================ */}
      <section id="eje-3" className="axis-section" aria-labelledby="eje-3-titulo">
        <div className="axis-header">
          <span className="axis-badge">Eje 3</span>
          <div>
            <h2 id="eje-3-titulo">Rigidez Operativa de la Descentralización</h2>
            <p className="subtle">Ejecución presupuestaria DIPRES (datos.gob.cl CKAN) del GORE Aysén y servicios públicos en la región, separando gasto corriente, inversión y transferencias.</p>
          </div>
        </div>

        <div className="axis-grid">
          <article className="panel axis-main">
            <div className="axis-main-top">
              <div>
                <h3>Desglose presupuestario GORE Aysén y Servicios Públicos</h3>
                <p className="subtle">
                  {dipres.data?.etapa_contable ? `Etapa contable: ${dipres.data.etapa_contable}` : 'Consulta en vivo desde CKAN / datos.gob.cl'}
                  {dipres.data?.moneda ? ` · ${dipres.data.moneda}` : ''}
                </p>
              </div>
              <div className="dipres-controls">
                <label className="inline-field" htmlFor={dipresYearId}>
                  <span>Ejercicio</span>
                  <select
                    id={dipresYearId}
                    value={dipresYear}
                    onChange={event => setDipresYear(Number(event.target.value))}
                  >
                    <option value={2025}>2025</option>
                    <option value={2026}>2026</option>
                  </select>
                </label>
                <button
                  type="button"
                  className="secondary-btn"
                  disabled={dipres.loading}
                  onClick={() => loadDipres(dipresYear, true)}
                >
                  {dipres.loading ? 'Actualizando…' : 'Actualizar en vivo'}
                </button>
              </div>
            </div>

            {dipres.loading ? (
              <LoadingSkeleton label={`Consultando ejecución presupuestaria DIPRES ${dipresYear} en datos.gob.cl…`} />
            ) : dipres.error ? (
              <ServiceErrorBox error={dipres.error} onRetry={() => loadDipres(dipresYear, true)} />
            ) : !dipres.data ? (
              <p className="empty">No se encontraron registros DIPRES para el ejercicio {dipresYear}.</p>
            ) : (
              <>
                {dipres.data.estado_actualizacion === 'respaldo_ultimo_corte_aprobado' && (
                  <p className="notice" role="status">
                    <strong>Respaldo del último corte aprobado (DIPRES):</strong>{' '}
                    {dipres.data.advertencia_respaldo ||
                      'La consulta en vivo a datos.gob.cl no respondió; se exhibe el último corte oficial validado en caché local.'}
                  </p>
                )}

                {(dipres.data.advertencia_comparabilidad_meses ||
                  (dipres.data.mes_corte !== null && dipres.data.mes_corte !== undefined && dipres.data.mes_corte < 12)) && (
                  <div className="brecha-box" role="note">
                    <strong>
                      Advertencia de comparabilidad por meses equivalentes
                      {dipres.data.mes_corte !== null && dipres.data.mes_corte !== undefined
                        ? ` · Corte mes ${dipres.data.mes_corte}${dipres.data.mes_corte_nombre ? ` (${dipres.data.mes_corte_nombre})` : ''}`
                        : ''}
                    </strong>
                    <p>
                      {dipres.data.advertencia_comparabilidad_meses ||
                        `El ejercicio ${dipres.data.anio} cubre ejecución acumulada parcial (mes ${dipres.data.mes_corte}). No comparar directamente sus montos acumulados contra cierres anuales de diciembre (12 meses) sin restringir ambos ejercicios a meses equivalentes.`}
                    </p>
                  </div>
                )}

                <div className="pol-kpi-grid">
                  <div className="pol-kpi-card">
                    <span className="kpi-label">Gasto Corriente (Subt. 21–26)</span>
                    <strong className="pol-kpi-num">{fmtMillions(dipresCorriente)}</strong>
                    <span className="kpi-meta">Personal, bienes y servicios de operación</span>
                  </div>
                  <div className="pol-kpi-card">
                    <span className="kpi-label">Inversión Real (Subt. 29–31)</span>
                    <strong className="pol-kpi-num">{fmtMillions(dipresInversion)}</strong>
                    <span className="kpi-meta">Activos no financieros e iniciativas de inversión</span>
                  </div>
                  <div className="pol-kpi-card">
                    <span className="kpi-label">Transf. de Capital (Subt. 33)</span>
                    <strong className="pol-kpi-num">{fmtMillions(dipresSub33)}</strong>
                    <span className="kpi-meta">Traspasos de capital (no sumar directo con ejecutor)</span>
                  </div>
                  <div className="pol-kpi-card is-highlight">
                    <span className="kpi-label">Financiamiento GORE (Partida 31)</span>
                    <strong className="pol-kpi-num">{fmtMillions(dipresPartida31)}</strong>
                    <span className="kpi-meta">Transferencias y marcos de financiamiento regional</span>
                  </div>
                </div>

                {/* Ratio corriente / inversión o brecha transparente */}
                <div className="visual-card">
                  <h4>Relación Gasto Corriente / Inversión (Subt. 21–26 vs Subt. 29–31)</h4>
                  {dipresRatio !== null ? (
                    <div className="ratio-display">
                      <div className="ratio-metric">
                        <span className="kpi-label">Razón corriente sobre inversión</span>
                        <strong className="pol-kpi-num">{fmtPct(dipresRatio)}</strong>
                        <span className="kpi-meta">
                          Por cada $100 en Subtítulos 29–31, el corte registra ${num1.format(dipresRatio)} en Subtítulos 21–26.
                        </span>
                      </div>
                      {dipresCorriente !== null && dipresInversion !== null && (dipresCorriente + dipresInversion) > 0 && (
                        <div className="stacked-bar-wrap" aria-label="Proporción entre gasto corriente e inversión">
                          <div className="stacked-bar" aria-hidden="true">
                            <span
                              className="stacked-seg is-current"
                              style={{ width: `${(dipresCorriente / (dipresCorriente + dipresInversion)) * 100}%` }}
                            />
                            <span
                              className="stacked-seg is-invest"
                              style={{ width: `${(dipresInversion / (dipresCorriente + dipresInversion)) * 100}%` }}
                            />
                          </div>
                          <div className="stacked-legend">
                            <span><i className="swatch is-current" /> Corriente 21–26 ({fmtPct((dipresCorriente / (dipresCorriente + dipresInversion)) * 100)})</span>
                            <span><i className="swatch is-invest" /> Inversión 29–31 ({fmtPct((dipresInversion / (dipresCorriente + dipresInversion)) * 100)})</span>
                          </div>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="brecha-box" role="note">
                      <strong>Relación no calculable en este corte (brecha documentada)</strong>
                      <p>
                        {dipres.data.motivo_brecha ||
                          'El recurso central consultado en CKAN/datos.gob.cl no desglosa simultáneamente Subtítulos 21–26 e Inversión 29–31 para GORE Aysén en este corte (por ejemplo, reporta únicamente financiamiento agregado Partida 31). No se estiman ni imputan subtítulos faltantes.'}
                      </p>
                    </div>
                  )}

                  {dipres.data.gore_aysen?.subtitulos && dipres.data.gore_aysen.subtitulos.length > 0 && (
                    <div className="table-scroll pol-table-gap" tabIndex={0} role="region" aria-label="Detalle por subtítulo GORE Aysén">
                      <table className="pol-table">
                        <caption className="sr-only">Detalle presupuestario por subtítulo de GORE Aysén en {dipres.data.anio}</caption>
                        <thead>
                          <tr>
                            <th scope="col">Subtítulo</th>
                            <th scope="col">Denominación</th>
                            <th scope="col" className="numeric">Monto (MM$ CLP)</th>
                            <th scope="col" className="numeric">Avance</th>
                          </tr>
                        </thead>
                        <tbody>
                          {dipres.data.gore_aysen.subtitulos.map((sub, idx) => (
                            <tr key={`${sub.subtitulo}-${idx}`}>
                              <td className="mono">{sub.subtitulo}</td>
                              <th scope="row">{sub.nombre}</th>
                              <td className="numeric">
                                {sub.monto_millones !== undefined && sub.monto_millones !== null
                                  ? fmtMillions(sub.monto_millones)
                                  : sub.vigente_millones !== undefined && sub.vigente_millones !== null
                                    ? fmtMillions(sub.vigente_millones)
                                    : 'Sin dato'}
                              </td>
                              <td className="numeric">{sub.avance_pct !== undefined && sub.avance_pct !== null ? fmtPct(sub.avance_pct) : '—'}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}

                  {dipres.data.servicios_publicos_aysen && dipres.data.servicios_publicos_aysen.length > 0 && (
                    <div className="table-scroll pol-table-gap" tabIndex={0} role="region" aria-label="Servicios públicos con registro en Aysén">
                      <table className="pol-table">
                        <caption className="sr-only">Servicios públicos identificados en Aysén según recurso DIPRES {dipres.data.anio}</caption>
                        <thead>
                          <tr>
                            <th scope="col">Servicio / Programa</th>
                            <th scope="col" className="numeric">Corriente</th>
                            <th scope="col" className="numeric">Inversión</th>
                            <th scope="col" className="numeric">Total (MM$ CLP)</th>
                          </tr>
                        </thead>
                        <tbody>
                          {dipres.data.servicios_publicos_aysen.map((srv, idx) => (
                            <tr key={`${srv.nombre}-${idx}`}>
                              <th scope="row">{srv.nombre}</th>
                              <td className="numeric">{fmtMillions(srv.gasto_corriente_millones)}</td>
                              <td className="numeric">{fmtMillions(srv.inversion_millones)}</td>
                              <td className="numeric">{fmtMillions(srv.total_millones)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}

                  <SourceFooter {...dipresSourceBase} />
                </div>

                {/* Estado en vivo de Presupuesto Abierto */}
                <div className="visual-card open-budget-card">
                  <div className="open-budget-head">
                    <h4>Estado en vivo · Presupuesto Abierto</h4>
                    <span className={`status-badge ${dipres.data.presupuesto_abierto?.disponible ? 'is-official' : 'is-warn'}`}>
                      {dipres.data.presupuesto_abierto?.disponible
                        ? (dipres.data.presupuesto_abierto.estado || 'Disponible')
                        : (dipres.data.presupuesto_abierto?.estado || 'No disponible / Restringido')}
                    </span>
                  </div>
                  <p className="subtle">
                    {dipres.data.presupuesto_abierto?.mensaje ||
                      'Verificación automática del portal Presupuesto Abierto para contraste mensualizado por servicio y subtítulo.'}
                  </p>
                  <div className="open-budget-meta">
                    {dipres.data.presupuesto_abierto?.ultimo_corte && (
                      <span><strong>Último corte:</strong> {dipres.data.presupuesto_abierto.ultimo_corte}</span>
                    )}
                    {dipres.data.presupuesto_abierto?.url && (
                      <a href={dipres.data.presupuesto_abierto.url} target="_blank" rel="noreferrer">
                        Abrir fuente oficial ↗
                      </a>
                    )}
                  </div>
                  <SourceFooter
                    institucionFallback="DIPRES · Presupuesto Abierto"
                    endpointFallback={`/api/v1/fiscal/dipres?anio=${dipresYear}`}
                    actualizadoEn={dipres.data.presupuesto_abierto?.ultimo_corte}
                    extraidoEn={dipres.data.presupuesto_abierto?.verificado_en ?? dipres.data.extraido_en}
                  />
                </div>
              </>
            )}
            <SourceFooter {...dipresSourceBase} />
          </article>

          <KeyTerritorialCard
            ejeLabel="Eje 3 · Rigidez Operativa"
            title="Estructura administrativa y sobrecosto por aislamiento geográfico"
            summary={
              <>
                <p>
                  Evaluar la descentralización en Aysén exige distinguir entre el presupuesto disponible para inversión real (Subtítulos 29–31), las transferencias de capital a terceros ejecutores (Subtítulo 33) y el costo fijo de sostener la operación institucional (Subtítulos 21–26).
                </p>
                <p>
                  {dipresRatio !== null ? (
                    <>
                      En el corte {dipres.data?.anio ?? dipresYear}, la razón gasto corriente sobre inversión alcanza{' '}
                      <strong>{fmtPct(dipresRatio)}</strong>.
                    </>
                  ) : (
                    <>
                      En el corte {dipres.data?.anio ?? dipresYear} persiste una <strong>brecha de desagregación abierta</strong> en los recursos centrales de CKAN, donde la información del GORE aparece consolidada a nivel de financiamiento Partida 31 sin separar todos los subtítulos operativos e inversión.
                    </>
                  )}{' '}
                  La dispersión territorial, las distancias terrestres/marítimas y la baja escala demográfica imponen sobrecostos estructurales de operación y logística en zonas extremas.
                </p>
              </>
            }
            evidenciaFavorable="Separar explícitamente Subtítulos 21–26, 29–31 y 33 permite auditar cuánta holgura presupuestaria real se destina a formación de capital versus funcionamiento rígido."
            evidenciaContraria="Un mayor gasto corriente relativo en zonas extremas puede reflejar asignaciones de zona, logística de conectividad y cobertura de servicios mínimos indispensables, más que burocracia prescindible."
            limiteInferencia="El cociente gasto corriente / inversión es un indicador descriptivo de composición presupuestaria; no permite diagnosticar ineficiencia administrativa sin controlar por escala, aislamiento geográfico, plazos y calidad de servicio."
            source={dipresSourceBase}
          />
        </div>
      </section>

      {/* ============================================================
          EJE 4 · FRAGMENTACIÓN FISCAL (3 BILLETERAS) + IMPORTADOR SINIM
      ============================================================ */}
      <section id="eje-4" className="axis-section" aria-labelledby="eje-4-titulo">
        <div className="axis-header">
          <span className="axis-badge">Eje 4</span>
          <div>
            <h2 id="eje-4-titulo">Fragmentación Fiscal: 3 Billeteras Territoriales y Cobertura SINIM</h2>
            <p className="subtle">Vistas brutas estrictamente separadas de Gobierno Central, GORE Aysén y las 10 Municipalidades, junto al importador oficial SINIM.</p>
          </div>
        </div>

        <div className="axis-grid">
          <article className="panel axis-main">
            <h3>Matriz de las 3 billeteras territoriales en Aysén</h3>
            <p className="notice anti-double-notice">
              <strong>Regla anti doble contabilización:</strong> las tres billeteras se presentan en <strong>vistas brutas separadas</strong> y <strong>no se suman entre sí</strong>.
              Consolidar gasto territorial exige conciliar documentalmente transferencias internas (Partida 31, Subtítulos 24 y 33, y Fondo Común Municipal) bajo la misma etapa contable de devengo.
            </p>

            <div className="wallets-grid">
              {/* Billetera 1: Gobierno Central */}
              <div className="wallet-card">
                <div className="wallet-head">
                  <span className="wallet-num">Billetera 1</span>
                  <span className="status-badge is-official">Sectorial</span>
                </div>
                <h4>Gobierno Central en Aysén</h4>
                <p className="wallet-metric">
                  {dipres.loading
                    ? 'Cargando…'
                    : dipres.data?.servicios_total_millones !== undefined && dipres.data?.servicios_total_millones !== null
                      ? fmtMillions(dipres.data.servicios_total_millones)
                      : dipres.data?.servicios_publicos_aysen && dipres.data.servicios_publicos_aysen.length > 0
                        ? `${dipres.data.servicios_publicos_aysen.length} servicios identificados`
                        : 'Cobertura parcial en CKAN'}
                </p>
                <p className="subtle">
                  Ejecución de ministerios y servicios públicos con asiento o ejecución en la región. Etapa:{' '}
                  <strong>{dipres.data?.etapa_contable || 'Según corte DIPRES'}</strong>.
                </p>
                <SourceFooter {...dipresSourceBase} notaExtra="Vista bruta sectorial; excluye partidas nacionales sin asignación territorial." />
              </div>

              {/* Billetera 2: GORE Aysén */}
              <div className="wallet-card">
                <div className="wallet-head">
                  <span className="wallet-num">Billetera 2</span>
                  <span className="status-badge is-official">Regional</span>
                </div>
                <h4>Gobierno Regional (GORE Aysén)</h4>
                <p className="wallet-metric">
                  {dipres.loading
                    ? 'Cargando…'
                    : fmtMillions(
                      dipres.data?.gore_aysen?.total_bruto_millones ??
                      dipresPartida31 ??
                      dipresInversion ??
                      dipresCorriente,
                    )}
                </p>
                <p className="subtle">
                  {dipresPartida31 !== null
                    ? `Financiamiento Partida 31: ${fmtMillions(dipresPartida31)}.`
                    : 'Programa de funcionamiento y cartera FNDR/inversión regional.'}{' '}
                  Contiene traspasos (Subt. 33) hacia municipios y servicios.
                </p>
                <SourceFooter {...dipresSourceBase} notaExtra="Vista bruta GORE; no sumar con transferencias recibidas por municipios." />
              </div>

              {/* Billetera 3: 10 Municipios (SINIM) */}
              <div className="wallet-card">
                <div className="wallet-head">
                  <span className="wallet-num">Billetera 3</span>
                  <span className={`status-badge ${sinimLoaded === sinimExpected && sinimLoaded > 0 ? 'is-official' : 'is-warn'}`}>
                    {sinimLoaded}/{sinimExpected} comunas
                  </span>
                </div>
                <h4>10 Municipalidades de Aysén</h4>
                <p className="wallet-metric">
                  {sinim.loading
                    ? 'Cargando…'
                    : sinimGastoTotalBrutoMillones !== null
                      ? fmtMillions(sinimGastoTotalBrutoMillones)
                      : 'Sin balances cargados'}
                </p>
                <p className="subtle">
                  {sinimLoaded > 0
                    ? `Suma bruta de las ${sinimLoaded} comunas con balance BEP importado desde SINIM.`
                    : 'Importa los Balances de Ejecución Presupuestaria (BEP) comunales en el módulo inferior.'}
                </p>
                <SourceFooter {...sinimSourceBase} notaExtra="Vista bruta municipal; incluye ingresos vía Fondo Común Municipal (FCM)." />
              </div>
            </div>

            {/* Módulo Importador SINIM Interactivo */}
            <div className="visual-card sinim-module">
              <div className="sinim-head">
                <div>
                  <h4>Módulo Importador SINIM · 10 Comunas de Aysén</h4>
                  <p className="subtle">
                    Carga archivos oficiales exportados de SINIM (<code className="mono">.csv</code> o <code className="mono">.json</code>) con validación fila por fila y cobertura comunal automática.
                  </p>
                </div>
                <a className="secondary-btn link-btn" href={sinimTemplateUrl} download>
                  ↓ Descargar plantilla oficial CSV
                </a>
              </div>

              {sinim.loading ? (
                <LoadingSkeleton label="Consultando cobertura comunal SINIM de Aysén…" />
              ) : sinim.error ? (
                <ServiceErrorBox error={sinim.error} onRetry={() => loadSinim()} />
              ) : (
                <>
                  {/* Barra de cobertura comunal */}
                  <div className="sinim-coverage">
                    <div className="sinim-coverage-top">
                      <strong>Cobertura comunal: {sinimLoaded} / {sinimExpected} comunas de Aysén</strong>
                      <span className="mono">{num1.format(sinimCoveragePct)}%</span>
                    </div>
                    <div
                      className="coverage-meter is-large"
                      role="progressbar"
                      aria-valuenow={sinimLoaded}
                      aria-valuemin={0}
                      aria-valuemax={sinimExpected}
                      aria-label={`Cobertura SINIM: ${sinimLoaded} de ${sinimExpected} comunas de Aysén`}
                    >
                      <span style={{ width: `${Math.min(100, Math.max(0, sinimCoveragePct))}%` }} />
                    </div>
                    {sinim.data?.comunas_faltantes && sinim.data.comunas_faltantes.length > 0 && (
                      <div className="missing-comunas">
                        <span className="subtle"><strong>Comunas faltantes ({sinim.data.comunas_faltantes.length}):</strong></span>
                        <ul className="chip-list" aria-label="Comunas de Aysén pendientes de carga SINIM">
                          {sinim.data.comunas_faltantes.map((item, idx) => {
                            const label = typeof item === 'string' ? item : `${item.comuna} (${item.cut})`
                            return <li key={`${label}-${idx}`} className="missing-chip">{label}</li>
                          })}
                        </ul>
                      </div>
                    )}
                  </div>

                  {/* Formulario de carga de archivo SINIM */}
                  <form className="sinim-upload-form" onSubmit={handleSinimImport}>
                    <div className="sinim-file-picker">
                      <label htmlFor={sinimInputId} className="field-inline-label">
                        Archivo SINIM (.csv o .json)
                      </label>
                      <input
                        ref={fileInputRef}
                        id={sinimInputId}
                        type="file"
                        accept=".csv,.json,text/csv,application/json"
                        onChange={handleFileSelected}
                      />
                    </div>
                    <button
                      type="submit"
                      className="primary"
                      disabled={sinimUpload.submitting}
                    >
                      {sinimUpload.submitting ? 'Validando e importando…' : 'Validar e importar SINIM'}
                    </button>
                  </form>

                  {sinimUpload.successMessage && (
                    <p className="sinim-success" role="status" aria-live="polite">
                      {sinimUpload.successMessage}
                    </p>
                  )}

                  {sinimUpload.errorMessage && (
                    <div className="service-error-box" role="alert">
                      <p className="error">{sinimUpload.errorMessage}</p>
                    </div>
                  )}

                  {sinimUpload.rowErrors.length > 0 && (
                    <div className="validation-errors" role="alert">
                      <strong>Errores de validación detectados ({sinimUpload.rowErrors.length}):</strong>
                      <ul>
                        {sinimUpload.rowErrors.map((err, idx) => (
                          <li key={idx}>
                            {err.fila !== null && err.fila !== undefined ? `Fila ${err.fila} · ` : ''}
                            {err.columna ? `Columna «${err.columna}» · ` : ''}
                            {err.valor ? `(valor: «${err.valor}») ` : ''}{err.motivo}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Tabla de municipios cargados */}
                  {sinim.data && sinim.data.comunas.length > 0 ? (
                    <div className="table-scroll pol-table-gap" tabIndex={0} role="region" aria-label="Municipios de Aysén cargados desde SINIM">
                      <table className="pol-table">
                        <caption className="sr-only">Registros municipales SINIM cargados para la Región de Aysén (normalizados a millones CLP)</caption>
                        <thead>
                          <tr>
                            <th scope="col">CUT</th>
                            <th scope="col">Comuna</th>
                            <th scope="col">Año</th>
                            <th scope="col">Etapa</th>
                            <th scope="col" className="numeric">Ingresos (MM$)</th>
                            <th scope="col" className="numeric">Gasto devengado (MM$)</th>
                            <th scope="col" className="numeric">Corriente (MM$)</th>
                            <th scope="col" className="numeric">Inversión (MM$)</th>
                          </tr>
                        </thead>
                        <tbody>
                          {sinim.data.comunas.map(row => (
                            <tr key={`${row.cut}-${row.anio ?? 'na'}`}>
                              <td className="mono">{row.cut}</td>
                              <th scope="row">{row.comuna}</th>
                              <td>{row.anio ?? '—'}</td>
                              <td>{row.etapa ?? '—'}</td>
                              <td className="numeric">{fmtMillions(row.ingresos_totales_millones)}</td>
                              <td className="numeric">{fmtMillions(row.gasto_total_devengado_millones)}</td>
                              <td className="numeric">{fmtMillions(row.gasto_corriente_millones)}</td>
                              <td className="numeric">{fmtMillions(row.gasto_inversion_millones)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <p className="subtle sinim-empty-note">
                      {sinim.data?.motivo_brecha || 'Aún no hay comunas de Aysén importadas en el almacenamiento local. Descarga la plantilla CSV vacía y carga los balances BEP de SINIM.'}
                    </p>
                  )}
                </>
              )}

              <SourceFooter
                {...sinimSourceBase}
                endpointFallback="/api/v1/fiscal/sinim · POST /api/v1/fiscal/sinim/importar"
                notaExtra={sinim.data?.ultimo_archivo ? `Último archivo validado: ${sinim.data.ultimo_archivo}` : undefined}
              />
            </div>
          </article>

          <KeyTerritorialCard
            ejeLabel="Eje 4 · Fragmentación Multinivel"
            title="Tres billeteras descoordinadas y autonomía municipal acotada"
            summary={
              <>
                <p>
                  El gasto público que opera en Aysén fluye por tres carriles institucionales distintos: ministerios sectoriales del <strong>Gobierno Central</strong>, el <strong>Gobierno Regional (GORE)</strong> y las <strong>10 municipalidades</strong> de la región (cobertura SINIM actual: <strong>{sinimLoaded}/{sinimExpected}</strong>).
                </p>
                <p>
                  Cada billetera utiliza calendarios, clasificaciones y sistemas contables distintos (SIGFE/DIPRES, reportes FNDR y balances BEP municipales bajo NICSP), lo que dificulta a la ciudadanía y a las autoridades territoriales observar un presupuesto integrado sin incurrir en doble contabilización de transferencias.
                </p>
              </>
            }
            evidenciaFavorable="Mantener las tres billeteras visibles pero separadas revela dónde se concentra la decisión financiera y evita inflar artificialmente el gasto territorial al sumar transferencias internas como el Subtítulo 33 o el FCM."
            evidenciaContraria="La existencia de tres niveles de gasto también responde a competencias legales diferenciadas (obras estructurales nacionales, inversión regional y servicios locales de proximidad), no únicamente a fragmentación evitable."
            limiteInferencia="Mientras no existan llaves documentales completas que concilien cada transferencia inter-billetera en etapa de devengo y cobertura 10/10 en SINIM, no corresponde publicar un total consolidado neto único para Aysén."
            source={sinimSourceBase}
          />
        </div>
      </section>

      {/* ============================================================
          SIMULADOR INTERACTIVO DE IMPACTO EN EL PIB DE AYSÉN
      ============================================================ */}
      <section id="simulador-aysen" className="axis-section" aria-labelledby="simulador-titulo">
        <div className="axis-header">
          <span className="axis-badge is-sim">Simulador hipotético</span>
          <div>
            <h2 id="simulador-titulo">Simulador Hipotético del Valor Agregado de Administración Pública en el PIB de Aysén</h2>
            <p className="subtle">
              Sensibilidad aritmética sobre el <strong>Valor Agregado de la actividad Administración Pública (Cuentas Nacionales BCCh)</strong> — magnitud contable distinta del gasto presupuestario DIPRES y del empleo público.
            </p>
          </div>
        </div>

        <article className="panel simulator-panel">
          <div className="sim-disclaimer" role="note">
            <strong>Escenario simulado con multiplicadores explícitamente hipotéticos · No equivale a observación oficial ni estimación causal.</strong>{' '}
            La variación opera exclusivamente sobre el <strong>Valor Agregado nominal de Administración Pública (BCCh)</strong>, que mide remuneraciones y consumo de capital fijo en Cuentas Nacionales y <strong>no debe confundirse con el gasto presupuestario ejecutado DIPRES</strong> (Subtítulos 21–33) ni con dotaciones de empleo público.
          </div>

          {bcch.loading ? (
            <LoadingSkeleton label="Esperando línea base oficial del Banco Central (Administración Pública y PIB nominal de Aysén)…" />
          ) : bcch.error ? (
            <ServiceErrorBox error={bcch.error} onRetry={() => loadBcch(true)} />
          ) : !simReady || !simulation || simAdminBase === null || simPibBase === null ? (
            <div className="brecha-box" role="note">
              <strong>Simulador en espera de observaciones oficiales BCCh</strong>
              <p>
                Para ejecutar la simulación se requieren los valores nominales oficiales vigentes de Administración Pública y PIB total de Aysén.
                Este módulo nunca utiliza cifras fijas ni inventadas como línea base.
              </p>
            </div>
          ) : (
            <div className="sim-grid">
              {/* Controles del simulador */}
              <div className="sim-controls">
                <div className="sim-control-block">
                  <div className="sim-label-row">
                    <label htmlFor={sliderId}>Variación hipotética del Valor Agregado de Administración Pública (BCCh)</label>
                    <div className="sim-num-wrap">
                      <label htmlFor={numInputId} className="sr-only">Porcentaje de variación</label>
                      <input
                        id={numInputId}
                        type="number"
                        min={-30}
                        max={30}
                        step={0.5}
                        value={deltaPct}
                        onChange={event => handleNumericDeltaChange(event.target.value)}
                      />
                      <span>%</span>
                    </div>
                  </div>
                  <input
                    id={sliderId}
                    className="sim-slider"
                    type="range"
                    min={-30}
                    max={30}
                    step={0.5}
                    value={deltaPct}
                    onChange={event => setDeltaPct(Number(event.target.value))}
                  />
                  <div className="sim-scale-marks" aria-hidden="true">
                    <span>-30%</span>
                    <span>-15%</span>
                    <span>0%</span>
                    <span>+15%</span>
                    <span>+30%</span>
                  </div>
                </div>

                <div className="sim-quick-group" role="group" aria-label="Atajos de variación porcentual">
                  {QUICK_DELTAS.map(val => (
                    <button
                      key={val}
                      type="button"
                      className="preset-chip"
                      aria-pressed={deltaPct === val}
                      onClick={() => setDeltaPct(val)}
                    >
                      {val > 0 ? `+${val}%` : `${val}%`}
                    </button>
                  ))}
                </div>

                <div className="sim-control-block">
                  <label htmlFor={multiplierId}>Multiplicador regional explícitamente hipotético</label>
                  <select
                    id={multiplierId}
                    value={multiplier}
                    onChange={event => setMultiplier(Number(event.target.value))}
                  >
                    {MULTIPLIERS.map(item => (
                      <option key={item.value} value={item.value}>{item.label}</option>
                    ))}
                  </select>
                  <p className="subtle">{selectedMultiplierInfo.description}</p>
                </div>

                <dl className="sim-formula">
                  <div>
                    <dt>Línea base oficial BCCh ({resumen?.anio ?? 'último año'})</dt>
                    <dd>
                      VA Admin. Pública (BCCh): <strong>{fmtMillions(simAdminBase)}</strong> · PIB nominal Aysén: <strong>{fmtMillions(simPibBase)}</strong>
                    </dd>
                  </div>
                  <div>
                    <dt>Fórmula aritmética hipotética</dt>
                    <dd className="mono">
                      ΔPIB = (VA Admin. Pública BCCh × {deltaPct > 0 ? `+${deltaPct}` : deltaPct}%) × {num2.format(multiplier)}x (hipotético)
                    </dd>
                  </div>
                </dl>
              </div>

              {/* Resultados del simulador */}
              <div className="sim-results" aria-live="polite">
                <div className="pol-kpi-grid is-three">
                  <div className={`pol-kpi-card ${simulation.deltaPib < 0 ? 'is-negative' : simulation.deltaPib > 0 ? 'is-highlight' : ''}`}>
                    <span className="kpi-label">Delta estimado en PIB Aysén</span>
                    <strong className="pol-kpi-num">
                      {simulation.deltaPib > 0 ? '+' : ''}{fmtMillions(simulation.deltaPib)}
                    </strong>
                    <span className="kpi-meta">Delta Admin. Pública: {simulation.deltaAdmin > 0 ? '+' : ''}{fmtMillions(simulation.deltaAdmin)}</span>
                  </div>
                  <div className={`pol-kpi-card ${simulation.impactPibPp < 0 ? 'is-negative' : simulation.impactPibPp > 0 ? 'is-highlight' : ''}`}>
                    <span className="kpi-label">Impacto en PIB total de Aysén</span>
                    <strong className="pol-kpi-num">
                      {simulation.impactPibPp > 0 ? '+' : ''}{num2.format(simulation.impactPibPp)} pp
                    </strong>
                    <span className="kpi-meta">Puntos porcentuales sobre PIB nominal observado</span>
                  </div>
                  <div className="pol-kpi-card">
                    <span className="kpi-label">PIB nominal simulado</span>
                    <strong className="pol-kpi-num">{fmtMillions(simulation.pibSimulated)}</strong>
                    <span className="kpi-meta">
                      Peso Admin. Pública: {fmtPct(simulation.baseAdminSharePct)} → {fmtPct(simulation.simAdminSharePct)}
                    </span>
                  </div>
                </div>

                {/* Comparación visual Observado oficial vs Escenario simulado */}
                <div className="visual-card">
                  <h4>Observado oficial ({resumen?.anio ?? '—'}) vs Escenario simulado</h4>
                  {(() => {
                    const maxPib = Math.max(simPibBase, simulation.pibSimulated, 1)
                    const maxAdmin = Math.max(simAdminBase, simulation.adminSimulated, 1)
                    return (
                      <div className="compare-bars">
                        <div className="compare-bar-row">
                          <span className="compare-bar-label">PIB Aysén · Observado oficial</span>
                          <div className="compare-track" aria-hidden="true">
                            <div className="compare-fill is-reference" style={{ width: `${(simPibBase / maxPib) * 100}%` }} />
                          </div>
                          <span className="compare-bar-val">{fmtMillions(simPibBase)}</span>
                        </div>
                        <div className="compare-bar-row">
                          <span className="compare-bar-label">PIB Aysén · Escenario simulado</span>
                          <div className="compare-track" aria-hidden="true">
                            <div
                              className={`compare-fill ${simulation.deltaPib < 0 ? 'is-negative' : 'is-primary'}`}
                              style={{ width: `${Math.max(0, (simulation.pibSimulated / maxPib) * 100)}%` }}
                            />
                          </div>
                          <span className="compare-bar-val">{fmtMillions(simulation.pibSimulated)}</span>
                        </div>
                        <div className="compare-bar-row">
                          <span className="compare-bar-label">Admin. Pública · Observado oficial</span>
                          <div className="compare-track" aria-hidden="true">
                            <div className="compare-fill is-reference" style={{ width: `${(simAdminBase / maxAdmin) * 100}%` }} />
                          </div>
                          <span className="compare-bar-val">{fmtMillions(simAdminBase)}</span>
                        </div>
                        <div className="compare-bar-row">
                          <span className="compare-bar-label">Admin. Pública · Escenario simulado</span>
                          <div className="compare-track" aria-hidden="true">
                            <div
                              className={`compare-fill ${simulation.deltaAdmin < 0 ? 'is-negative' : 'is-primary'}`}
                              style={{ width: `${Math.max(0, (simulation.adminSimulated / maxAdmin) * 100)}%` }}
                            />
                          </div>
                          <span className="compare-bar-val">{fmtMillions(simulation.adminSimulated)}</span>
                        </div>
                      </div>
                    )
                  })()}
                  <SourceFooter
                    {...bcchSourceBase}
                    seriesCodigos={bcchSimCodes}
                    notaExtra="Escenario simulado paramétrico a partir de observaciones oficiales del BCCh."
                  />
                </div>
              </div>
            </div>
          )}

          <SourceFooter
            {...bcchSourceBase}
            seriesCodigos={bcchSimCodes}
            notaExtra="Línea base oficial BCCh · Simulación bajo supuestos paramétricos explícitos."
          />
        </article>
      </section>

      {/* ============================================================
          EXPLORADOR VIVO DE SERIES BCCh (ACORDEÓN <details>)
      ============================================================ */}
      <section id="explorador-bcch" className="axis-section" aria-labelledby="explorador-titulo">
        <details className="panel bcch-explorer">
          <summary id="explorador-titulo">
            <span>
              <strong>Explorador vivo de series del Banco Central de Chile</strong>
              <small className="subtle">Busca en tiempo real series anuales o trimestrales y consulta observaciones directamente por código BDE.</small>
            </span>
          </summary>

          <div className="explorer-body">
            <form className="explorer-search-form" onSubmit={handleBcchSearch}>
              <label className="field" htmlFor={searchFreqId}>
                Frecuencia
                <select
                  id={searchFreqId}
                  value={searchFreq}
                  onChange={event => setSearchFreq(event.target.value as 'ANNUAL' | 'QUARTERLY')}
                >
                  <option value="ANNUAL">Anual (ANNUAL)</option>
                  <option value="QUARTERLY">Trimestral (QUARTERLY)</option>
                </select>
              </label>
              <label className="field explorer-query-field" htmlFor={searchQueryId}>
                Término de búsqueda en catálogo BCCh
                <input
                  id={searchQueryId}
                  type="search"
                  value={searchTerm}
                  placeholder="Ej. Aysén, PIB, Pesca, Administración pública…"
                  onChange={event => setSearchTerm(event.target.value)}
                />
              </label>
              <button type="submit" className="primary" disabled={searchState.loading || !searchTerm.trim()}>
                {searchState.loading ? 'Buscando…' : 'Buscar series'}
              </button>
            </form>

            {searchState.loading && <LoadingSkeleton label="Consultando catálogo de series BCCh…" />}
            {searchState.error && (
              <ServiceErrorBox
                error={searchState.error}
                onRetry={() => {
                  searchBcchSeries(searchFreq, searchTerm)
                    .then(data => setSearchState({ loading: false, data, error: null }))
                    .catch(err => setSearchState({ loading: false, data: null, error: err instanceof Error ? err : new Error('Error en búsqueda') }))
                }}
              />
            )}

            {searchState.data && (
              <div className="visual-card">
                <h4>Resultados en catálogo BCCh ({searchState.data.total} coincidencias)</h4>
                {searchState.data.resultados.length === 0 ? (
                  <p className="subtle">No se encontraron series para «{searchState.data.query}» en frecuencia {searchState.data.frequency}.</p>
                ) : (
                  <div className="table-scroll" tabIndex={0} role="region" aria-label="Resultados de búsqueda de series BCCh">
                    <table className="pol-table">
                      <thead>
                        <tr>
                          <th scope="col">Código serie</th>
                          <th scope="col">Descripción</th>
                          <th scope="col">Cobertura</th>
                          <th scope="col">Acción</th>
                        </tr>
                      </thead>
                      <tbody>
                        {searchState.data.resultados.slice(0, 25).map(item => (
                          <tr key={item.seriesId}>
                            <td className="mono">{item.seriesId}</td>
                            <th scope="row">{item.spanishTitle}</th>
                            <td className="mono">
                              {item.firstObservation || '—'} → {item.lastObservation || '—'}
                            </td>
                            <td>
                              <button
                                type="button"
                                className="text-button"
                                onClick={() => handleInspectSeries(item.seriesId)}
                              >
                                Consultar serie
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
                <SourceFooter
                  fuente={searchState.data.fuente_trazabilidad}
                  institucionFallback="Banco Central de Chile (Catálogo BDE)"
                  endpointFallback={`/api/v1/bcch/search?frequency=${searchState.data.frequency}&q=${encodeURIComponent(searchState.data.query)}`}
                  actualizadoEn={searchState.data.actualizado_en}
                  extraidoEn={searchState.data.extraido_en}
                />
              </div>
            )}

            {/* Consulta directa de serie puntual */}
            <form
              className="explorer-direct-form"
              onSubmit={event => {
                event.preventDefault()
                handleInspectSeries(manualSeriesId)
              }}
            >
              <label className="field explorer-query-field" htmlFor={seriesIdInput}>
                Consultar código de serie exacto
                <input
                  id={seriesIdInput}
                  type="text"
                  value={manualSeriesId}
                  placeholder="Ej. F035.PIB.FLU.N.CLP.2018.Z.Z.Z.11.0.A"
                  onChange={event => setManualSeriesId(event.target.value)}
                />
              </label>
              <label className="field" htmlFor={firstDateInput}>
                Desde fecha (opcional)
                <input
                  id={firstDateInput}
                  type="text"
                  value={firstDate}
                  placeholder="YYYY-MM-DD"
                  onChange={event => setFirstDate(event.target.value)}
                />
              </label>
              <button type="submit" className="secondary-btn" disabled={seriesState.loading || !manualSeriesId.trim()}>
                {seriesState.loading ? 'Consultando…' : 'Consultar serie'}
              </button>
            </form>

            {seriesState.loading && <LoadingSkeleton label={`Descargando observaciones de ${manualSeriesId} desde BCCh…`} />}
            {seriesState.error && (
              <ServiceErrorBox error={seriesState.error} onRetry={() => handleInspectSeries(manualSeriesId)} />
            )}
            {seriesState.data && (
              <div className="visual-card">
                <h4>{seriesState.data.titulo}</h4>
                <p className="subtle">
                  Código oficial: <code className="mono">{seriesState.data.serie_id}</code>
                  {seriesState.data.unidad ? ` · Unidad: ${seriesState.data.unidad}` : ''}
                  {` · ${seriesState.data.observaciones.length} observaciones`}
                </p>
                {seriesState.data.observaciones.length > 0 ? (
                  <div className="table-scroll pol-table-gap" tabIndex={0} role="region" aria-label={`Observaciones de ${seriesState.data.serie_id}`}>
                    <table className="pol-table is-compact">
                      <thead>
                        <tr>
                          <th scope="col">Fecha / Período</th>
                          <th scope="col" className="numeric">Valor</th>
                          <th scope="col">Estado</th>
                        </tr>
                      </thead>
                      <tbody>
                        {[...seriesState.data.observaciones].reverse().slice(0, 24).map((obs, idx) => (
                          <tr key={`${obs.fecha}-${idx}`}>
                            <td className="mono">{obs.fecha}</td>
                            <td className="numeric">{obs.valor !== null ? num2.format(obs.valor) : 'Sin dato'}</td>
                            <td>{obs.estado || 'OK'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <p className="subtle">La serie no devolvió observaciones para el rango solicitado.</p>
                )}
                <SourceFooter
                  fuente={seriesState.data.fuente_trazabilidad}
                  institucionFallback="Banco Central de Chile (BDE)"
                  endpointFallback={`/api/v1/bcch/series/${encodeURIComponent(seriesState.data.serie_id)}`}
                  seriesCodigos={[seriesState.data.serie_id]}
                  actualizadoEn={seriesState.data.actualizado_en}
                  extraidoEn={seriesState.data.extraido_en}
                />
              </div>
            )}
          </div>
        </details>
      </section>
    </div>
  )
}
