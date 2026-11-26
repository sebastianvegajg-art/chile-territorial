import { useEffect, useRef, useState } from 'react'
import { createRoot } from 'react-dom/client'
import { demoDefault, demoRelease, downloadObservations, get, observations, standalone } from './api'
import type { Metric, Observation, Provenance, Publication, Territory, Valuation } from './api'
import { History } from './history'
import { comparable, compareValues, derive } from './metrics'
import type { Derived } from './metrics'
import { DemografiaView } from './DemografiaView'
import { EmpleoIneView } from './EmpleoIneView'
import { EstructuraView } from './EstructuraView'
import { LaboratorioView } from './LaboratorioView'
import { PoliticalView } from './PoliticalView'
import { PorGobiernoView } from './PorGobiernoView'
import { PortadaView } from './PortadaView'
import { InfoPopover } from './components/InfoPopover'
import './styles.css'

type Page = 'portada' | 'comparar' | 'politica' | 'por-gobierno' | 'empleo' | 'estructura' | 'demografia' | 'laboratorio' | 'metodologia'
type Lens = 'contable' | 'politica'

const CONTABLE_PAGES = new Set<Page>(['comparar', 'estructura', 'empleo', 'demografia'])
const POLITICA_PAGES = new Set<Page>(['politica', 'por-gobierno', 'laboratorio'])

const POLITICAL_HASHES = new Set([
  '#politica',
  '#eje-1',
  '#eje-2',
  '#eje-3',
  '#eje-4',
  '#simulador-aysen',
  '#explorador-bcch',
])

function resolvePage(hash: string, current: Page = 'portada'): Page {
  if (hash === '#contenido') return current
  if (hash === '' || hash === '#' || hash === '#portada') return 'portada'
  if (hash === '#comparar') return 'comparar'
  if (hash === '#metodologia') return 'metodologia'
  if (hash === '#por-gobierno') return 'por-gobierno'
  if (hash === '#empleo') return 'empleo'
  if (hash === '#estructura') return 'estructura'
  if (hash === '#demografia') return 'demografia'
  if (hash === '#laboratorio') return 'laboratorio'
  if (POLITICAL_HASHES.has(hash)) return 'politica'
  return 'comparar'
}

const metrics = [
  {
    id: 'nivel-real',
    label: 'PIB real',
    optionLabel: 'PIB real (sin inflación, base 2018)',
    metric: 'nivel',
    valuation: 'real',
    unitShort: 'millones de pesos (base 2018)',
    precision: 'Mide la producción económica descontando la inflación, valorada a precios constantes de 2018. Sirve para comparar cuánto creció realmente la actividad entre distintos años.',
  },
  {
    id: 'nivel-nominal',
    label: 'PIB nominal',
    optionLabel: 'PIB nominal (precios de cada año)',
    metric: 'nivel',
    valuation: 'nominal',
    unitShort: 'millones de pesos corrientes',
    precision: 'Mide la producción a los precios vigentes de cada año (incluye la inflación). Sirve para ver el tamaño económico en pesos de ese momento y comparar regiones en un mismo año.',
  },
  {
    id: 'crecimiento',
    label: 'Crecimiento real',
    optionLabel: 'Crecimiento real anual (%)',
    metric: 'crecimiento',
    valuation: 'real',
    unitShort: 'variación real anual',
    precision: 'Muestra cuánto aumentó o disminuyó la producción real respecto al año anterior, ya descontado el efecto de la inflación.',
  },
  {
    id: 'participacion',
    label: 'Participación regional',
    optionLabel: 'Participación regional (%)',
    metric: 'participacion',
    valuation: 'nominal',
    unitShort: 'del PIB nominal nacional',
    precision: 'Indica qué porcentaje del PIB de Chile aporta cada región. Se calcula con PIB nominal (precios de cada año) para que los pesos regionales sumen coherentemente.',
  },
  {
    id: 'acumulado',
    label: 'Crecimiento real acumulado',
    optionLabel: 'Crecimiento real acumulado (%)',
    metric: 'nivel',
    valuation: 'real',
    unitShort: 'variación real acumulada',
    precision: 'Mide cuánto creció o retrocedió la producción en términos reales (sin inflación) entre el año inicial seleccionado y cada año siguiente.',
  },
  {
    id: 'indice',
    label: 'Índice histórico real',
    optionLabel: 'Índice histórico real (base 100)',
    metric: 'nivel',
    valuation: 'real',
    unitShort: 'índice real (año inicial = 100)',
    precision: 'Iguala todas las regiones en 100 el primer año para comparar fácilmente su ritmo real de crecimiento, incluso entre economías de distinto tamaño.',
  },
] as const satisfies readonly {
  id: string
  label: string
  optionLabel: string
  metric: Metric
  valuation: Valuation
  unitShort: string
  precision: string
}[]

const regionPresets = [
  { id: 'aysen', label: 'Aysén', codes: ['11'] },
  { id: 'austral', label: 'Austral', codes: ['10', '11', '12'] },
  { id: 'norte', label: 'Norte', codes: ['15', '01', '02', '03', '04'] },
  { id: 'centro-sur', label: 'Centro-Sur', codes: ['05', '13', '06', '07', '16', '08', '09', '14'] },
] as const

const bdeRoot = 'https://si3.bcentral.cl/Siete/ES/Siete/Cuadro/CAP_CCNN/MN_CCNN76/'
const bdeReal = bdeRoot + 'CCNN2018_PIB_REGIONAL'
const bdeNominal = bdeRoot + 'CCNN2018_PIB_REGIONAL_N/637899740344107786'

const number = new Intl.NumberFormat('es-CL', { maximumFractionDigits: 2 })
const intNumber = new Intl.NumberFormat('es-CL', { maximumFractionDigits: 0 })
const dec1Number = new Intl.NumberFormat('es-CL', { minimumFractionDigits: 1, maximumFractionDigits: 1 })
const humanDateFormatter = new Intl.DateTimeFormat('es-CL', {
  day: 'numeric',
  month: 'short',
  year: 'numeric',
  timeZone: 'UTC',
})
const status = {
  informado: 'Informado', preliminar: 'Preliminar', faltante: 'Sin dato',
  suprimido: 'Suprimido', no_aplicable: 'No aplica', error: 'Error',
}

function evidence(row: Observation) {
  if (row.clase === 'prueba') return 'Sintético'
  if (row.clase === 'estimacion') return 'Estimación'
  if (row.clase === 'no_disponible') return status[row.estado]
  return row.metrica === 'nivel' ? 'Oficial' : 'Calculado con datos oficiales'
}

function display(row?: Observation) {
  if (row?.valor == null) return '—'
  // Preserve the original decimal string in the table and CSV. The chart uses an approximate scale.
  const [integer, fraction] = row.valor.split('.')
  return [integer.replace(/\B(?=(\d{3})+(?!\d))/g, '.'), fraction].filter(Boolean).join(',')
}

function formatKpiValue(row?: Observation) {
  if (row?.valor == null) return '—'
  const numeric = Number(row.valor)
  if (!Number.isFinite(numeric)) return '—'
  if (row.unidad === '%') return `${dec1Number.format(numeric)}%`
  if (row.unidad === 'millones CLP') return intNumber.format(Math.round(numeric))
  return dec1Number.format(numeric)
}

function formatHumanDate(value?: string) {
  if (!value || value === '—') return 'Sin fecha'
  const isoDay = value.slice(0, 10)
  const parsed = new Date(`${isoDay}T12:00:00Z`)
  if (Number.isNaN(parsed.getTime())) return isoDay
  return humanDateFormatter.format(parsed)
}

function formatReleaseDate(value?: string) {
  if (!value || value === '—') return '—'
  if (value.includes('T')) {
    const date = value.slice(0, 10)
    const time = value.slice(11, 19).replace(/Z$/, '')
    return time ? `${date} · ${time} UTC` : date
  }
  return value.slice(0, 10)
}

function App() {
  const [page, setPage] = useState<Page>(() => resolvePage(location.hash))
  const [lastLens, setLastLens] = useState<Lens>(() => (POLITICA_PAGES.has(resolvePage(location.hash)) ? 'politica' : 'contable'))
  const [mode, setMode] = useState<'official' | 'demo'>(demoDefault ? 'demo' : 'official')
  const [territories, setTerritories] = useState<Territory[]>([])
  const [releases, setReleases] = useState<Publication[]>([])
  const [cut, setCut] = useState('')
  const [selected, setSelected] = useState(['11'])
  const [benchmark, setBenchmark] = useState(true)
  const [start, setStart] = useState(2013)
  const [end, setEnd] = useState<number | null>(null)
  const [measure, setMeasure] = useState<(typeof metrics)[number]['id']>('nivel-real')
  const [view, setView] = useState<'chart' | 'ranking' | 'table'>('chart')
  const [retry, setRetry] = useState(0)
  const [metadata, setMetadata] = useState({ loading: true, error: '' })
  const [result, setResult] = useState<{ key: string; rows: Observation[]; publication: string; error: string }>({
    key: '', rows: [], publication: '', error: '',
  })
  const [detail, setDetail] = useState<{ id: string; row?: Provenance; error?: string } | null>(null)
  const [downloading, setDownloading] = useState(false)
  const [downloadError, setDownloadError] = useState('')
  const [offlineDownload, setOfflineDownload] = useState(false)
  const dialog = useRef<HTMLDialogElement>(null)
  const provenanceRequest = useRef<AbortController | null>(null)

  const metric = metrics.find(item => item.id === measure)!
  const derived: Derived | undefined = measure === 'acumulado' || measure === 'indice' ? measure : undefined
  const regions = territories.filter(item => item.nivel === 'regional' && item.codigo !== 'CL')
  const regionCodeSet = new Set(regions.map(item => item.codigo))
  const chosen = regions.filter(item => selected.includes(item.codigo))
  const chile = territories.find(item => item.codigo === 'CL')
  const showBenchmark = benchmark && metric.metric !== 'participacion'
  const requestedTerritories = metric.metric === 'participacion' ? regions : territories
  const compared = showBenchmark && chile ? [...chosen, chile] : chosen
  const publication = mode === 'demo' ? demoRelease : cut || releases[0]?.id
  const query = new URLSearchParams({
    anio_desde: '2013', anio_hasta: String(new Date().getFullYear()), metrica: metric.metric, valoracion: metric.valuation,
  })
  if (publication) query.set('publicacion', publication)
  for (const item of requestedTerritories) query.append('territorios', item.codigo)
  const key = publication && compared.length && chosen.length && !metadata.loading && !metadata.error ? query.toString() : ''
  const active = key && key === result.key ? result : null
  const isDemo = mode === 'demo' || active?.rows.some(row => row.clase === 'prueba')
  const errors = metadata.error || active?.error
  const pendingOfficial = mode === 'official' && !metadata.loading && !metadata.error && !publication
  const loading = metadata.loading || (!!key && !active)
  const publishedYears = active?.rows.filter(row => row.valor !== null).map(row => row.anio) ?? []
  const latest = publishedYears.length ? Math.max(...publishedYears) : new Date().getFullYear()
  const last = Math.max(start, end ?? latest)
  const years = Array.from({ length: last - start + 1 }, (_, index) => start + index)
  const options = Array.from({ length: Math.max(latest, start, end ?? 2013) - 2012 }, (_, index) => 2013 + index)
  const observationByKey = new Map(active?.rows.map(row => [`${row.territorio}/${row.anio}`, row]))
  const raw = (code: string, year: number) => observationByKey.get(`${code}/${year}`)
  const series = compared.map(territory => {
    const observations = new Map<number, Observation>()
    for (const year of years) {
      const row = raw(territory.codigo, year)
      if (row) observations.set(year, derived ? derive(row, raw(territory.codigo, start), derived) : row)
    }
    return { territory, years: observations }
  })
  const tableRows = [...years].reverse().flatMap(year => series.map(({ territory, years }) => ({
    territory, row: years.get(year), year,
  })))
  const rowsAtEnd = series.map(({ territory, years }) => ({ territory, row: years.get(last) }))
  const regionalValues = rowsAtEnd.filter(({ territory, row }) => territory.codigo !== 'CL' && row?.valor != null)
  const comparableRanking = regionalValues.every(({ row }) => comparable(row!, regionalValues[0].row!))
  const ranked = [...regionalValues].sort((left, right) => compareValues(right.row!.valor!, left.row!.valor!))
  const rows = [...ranked, ...rowsAtEnd.filter(item => !ranked.includes(item))]
  const unitRow = tableRows.find(({ row }) => row?.valor != null)?.row ?? tableRows.find(({ row }) => row)?.row
  const unit = unitRow?.unidad
  const magnitude = Math.max(1, ...rows.map(({ row }) => Math.abs(Number(row?.valor ?? 0))))
  const hasNegative = rows.some(({ row }) => Number(row?.valor) < 0)
  const chosenPublication = releases.find(item => item.id === active?.publication)
  const activeRelease: Publication | undefined = mode === 'demo'
    ? { id: demoRelease, fecha: '—', estado: 'prueba', fuente: 'Demostración sintética local' }
    : (chosenPublication ?? releases.find(item => item.id === (cut || releases[0]?.id)) ?? releases[0])
  const publicTables = chosenPublication?.id.startsWith('bcch-bde-publico-')

  // KPI strip: cifras derivadas exclusivamente del corte activo
  const leader = comparableRanking ? ranked[0] : undefined
  const tiedLeaders = leader?.row?.valor != null
    ? ranked.filter(item => compareValues(item.row!.valor!, leader.row!.valor!) === 0)
    : []
  const chileRawAtEnd = raw('CL', last)
  const chileRowAtEnd = chileRawAtEnd
    ? (derived ? derive(chileRawAtEnd, raw('CL', start), derived) : chileRawAtEnd)
    : undefined
  const participationSum = metric.metric === 'participacion' && comparableRanking && regionalValues.length > 0
    ? regionalValues.reduce((acc, item) => acc + Number(item.row!.valor), 0)
    : null
  const releaseCoverage = chosenPublication?.cobertura
  const selectedWithValue = tableRows.filter(({ row }) => row?.valor != null).length

  function chooseStart(year: number) {
    setStart(year)
    if (end !== null && end < year) setEnd(year)
    setDownloadError('')
  }

  useEffect(() => {
    if (standalone || mode !== 'official') return
    const request = new AbortController()
    fetch('/descargas/Chile_Territorial_Oficial.html', { method: 'HEAD', signal: request.signal })
      .then(response => setOfflineDownload(response.ok && !!response.headers.get('Content-Disposition')))
      .catch(() => {})
    return () => request.abort()
  }, [mode])

  const activeLens: Lens = page === 'portada'
    ? 'contable'
    : POLITICA_PAGES.has(page)
      ? 'politica'
      : CONTABLE_PAGES.has(page)
        ? 'contable'
        : lastLens

  useEffect(() => {
    if (POLITICA_PAGES.has(page)) setLastLens('politica')
    else if (CONTABLE_PAGES.has(page)) setLastLens('contable')
  }, [page])

  useEffect(() => {
    document.documentElement.dataset.lens = activeLens
  }, [activeLens])

  useEffect(() => {
    const sync = () => setPage(current => resolvePage(location.hash, current))
    window.addEventListener('hashchange', sync)
    return () => window.removeEventListener('hashchange', sync)
  }, [])

  function enterObservatory() {
    const targetPage: Page = standalone ? 'comparar' : 'politica'
    const targetHash = standalone ? '#comparar' : '#politica'
    setPage(targetPage)
    if (location.hash !== targetHash) location.hash = targetHash
  }

  function selectReadingMode(next: Lens) {
    setLastLens(next)
    if (next === 'politica') {
      const targetPage: Page = standalone ? 'por-gobierno' : 'politica'
      const targetHash = standalone ? '#por-gobierno' : '#politica'
      if (!POLITICA_PAGES.has(page)) {
        setPage(targetPage)
        if (location.hash !== targetHash) location.hash = targetHash
      }
      return
    }
    if (!CONTABLE_PAGES.has(page)) {
      setPage('comparar')
      if (location.hash !== '#comparar') location.hash = '#comparar'
    }
  }

  useEffect(() => {
    const request = new AbortController()
    Promise.all([
      get<Territory[]>('/territorios', request.signal),
      get<Publication[]>('/publicaciones', request.signal),
    ]).then(([data, publications]) => {
      setTerritories(data)
      const approved = publications.filter(item => item.estado === 'aprobada')
      setReleases(approved)
      setCut(previous => previous || approved[0]?.id || '')
      setMetadata({ loading: false, error: '' })
    }).catch(error => {
      if (!request.signal.aborted) setMetadata({ loading: false, error: error.message })
    })
    return () => request.abort()
  }, [retry])

  useEffect(() => {
    if (!key) return
    const request = new AbortController()
    const filters = new URLSearchParams(key)
    observations(filters, request.signal).then(data => {
      if (data.publication !== filters.get('publicacion') || (mode === 'official' && data.rows.some(row => row.clase === 'prueba'))) {
        throw new Error('El servicio devolvió un corte distinto al solicitado.')
      }
      setResult({ ...data, key, error: '' })
    }).catch(error => {
      if (!request.signal.aborted) setResult({ key, rows: [], publication: '', error: error.message })
    })
    return () => request.abort()
  }, [key, mode, retry])

  function toggle(code: string) {
    setDownloadError('')
    setSelected(previous => previous.includes(code) ? previous.filter(item => item !== code) : [...previous, code])
  }

  function explainDerived(row: Observation) {
    const base = raw(row.territorio, start)
    setDetail({ id: row.id, row: {
      observacion: row.id, publicacion: row.publicacion, serie_bde: null, artefacto: null, selector: null,
      formula_version: derived === 'indice' ? '100 × nivel real actual / nivel real base' : '100 × (nivel real actual / nivel real base − 1)',
      insumos: [...new Set([row.id, base?.id].filter((id): id is string => !!id))],
      motivo: `Año base ${start}. Redondeo a ocho decimales. Los insumos pueden consultarse en PIB real.`,
    } })
    dialog.current?.showModal()
  }

  async function explain(row: Observation) {
    provenanceRequest.current?.abort()
    const request = new AbortController()
    provenanceRequest.current = request
    setDetail({ id: row.id })
    dialog.current?.showModal()
    try {
      const item = await get<Provenance>(`/observaciones/${encodeURIComponent(row.id)}/procedencia`, request.signal)
      if (!request.signal.aborted) setDetail({ id: row.id, row: item })
    } catch (error) {
      if (!request.signal.aborted) setDetail({ id: row.id, error: (error as Error).message })
    }
  }

  async function download() {
    if (!active?.publication) return
    setDownloading(true)
    setDownloadError('')
    try {
      let blob: Blob
      if (derived) {
        const csv = [
          ['territorio', 'anio', 'metrica', 'valor', 'unidad', 'estado', 'clase', 'publicacion', 'anio_base', 'nivel_real_actual', 'nivel_real_base', 'id_nivel_actual', 'id_nivel_base'],
          ...tableRows.map(({ territory, year, row }) => {
            const current = raw(territory.codigo, year)
            const base = raw(territory.codigo, start)
            return [territory.codigo, year, derived, row?.valor, row?.unidad, row?.estado ?? 'faltante',
              row?.clase ?? 'no_disponible', active.publication, start, current?.valor, base?.valor, current?.id, base?.id]
          }),
        ].map(fields => fields.join(',')).join('\r\n')
        blob = new Blob([csv], { type: 'text/csv;charset=utf-8' })
      } else {
        const filters = new URLSearchParams(key)
        filters.set('anio_desde', String(start))
        filters.set('anio_hasta', String(last))
        filters.set('publicacion', active.publication)
        filters.delete('territorios')
        compared.forEach(item => filters.append('territorios', item.codigo))
        blob = await downloadObservations(filters, active.publication)
      }
      const url = URL.createObjectURL(blob)
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = `pib-${active.publication}-${measure}-${start}-${last}.csv`
      anchor.click()
      window.setTimeout(() => URL.revokeObjectURL(url), 1000)
    } catch {
      setDownloadError('No se pudo descargar el CSV para este corte.')
    } finally {
      setDownloading(false)
    }
  }

  const activeReleaseCoveragePct = activeRelease?.cobertura && activeRelease.cobertura.esperadas > 0
    ? Math.min(100, (activeRelease.cobertura.disponibles / activeRelease.cobertura.esperadas) * 100)
    : null

  if (page === 'portada') {
    return (
      <>
        <a className="skip-link" href="#portada-titulo">Ir al contenido principal</a>
        <PortadaView onEnter={enterObservatory} />
      </>
    )
  }

  return (
    <>
      <a className="skip-link" href="#contenido">Ir al contenido principal</a>
      <header className="masthead">
        <div className="masthead-inner wrap">
          <a
            className="brand brand-confiasur"
            href="#portada"
            aria-label="CONFIASUR Consultores · Volver a la portada"
          >
            <img
              src="/brand/confiasur-logo-light.png"
              alt="CONFIASUR Consultores"
              className="brand-logo-img"
              width={183}
              height={36}
            />
            <span className="brand-divider" aria-hidden="true" />
            <span className="brand-observatory">Observatorio <strong>Territorial</strong></span>
          </a>
          <div className="masthead-right">
            <div className="mode-switch" role="group" aria-label="Lente de análisis">
              <button
                type="button"
                className="lens-btn is-contable"
                aria-pressed={activeLens === 'contable'}
                title="Enfoque estadístico y numérico: PIB, estructura productiva, empleo INE y PIB per cápita"
                onClick={() => selectReadingMode('contable')}
              >
                <span className="lens-dot is-contable" aria-hidden="true" />
                Vista Contable
              </button>
              <button
                type="button"
                className="lens-btn is-politica"
                aria-pressed={activeLens === 'politica'}
                title="Enfoque político y de gestión pública: Aysén, comparación por gobierno y dossiers"
                onClick={() => selectReadingMode('politica')}
              >
                <span className="lens-dot is-politica" aria-hidden="true" />
                Vista Política
              </button>
            </div>
            <nav aria-label="Principal">
              <a href="#metodologia" aria-current={page === 'metodologia' ? 'page' : undefined}>Metodología</a>
            </nav>
          </div>
        </div>
      </header>

      {!standalone && (
        <div className="module-bar-wrap">
          <nav
            className="module-bar wrap"
            aria-label={activeLens === 'politica' ? 'Módulos de Vista Política' : 'Módulos de Vista Contable'}
          >
            <span className={`module-bar-lens is-${activeLens}`}>
              <span className={`lens-dot is-${activeLens}`} aria-hidden="true" />
              {activeLens === 'politica' ? 'Lente político' : 'Lente contable'}
            </span>
            {activeLens === 'contable' ? (
              <>
                <a href="#comparar" aria-current={page === 'comparar' ? 'page' : undefined}>Comparador PIB</a>
                <a href="#estructura" aria-current={page === 'estructura' ? 'page' : undefined}>Estructura 16 Regiones</a>
                <a href="#empleo" aria-current={page === 'empleo' ? 'page' : undefined}>Empleo INE</a>
                <a href="#demografia" aria-current={page === 'demografia' ? 'page' : undefined}>PIB per Cápita</a>
              </>
            ) : (
              <>
                <a href="#politica" aria-current={page === 'politica' ? 'page' : undefined}>Aysén: Gestión y Obras</a>
                <a href="#por-gobierno" aria-current={page === 'por-gobierno' ? 'page' : undefined}>Por gobierno</a>
                <a href="#laboratorio" aria-current={page === 'laboratorio' ? 'page' : undefined}>Laboratorio y Dossiers</a>
              </>
            )}
          </nav>
        </div>
      )}

      <main id="contenido" className="wrap" tabIndex={-1}>
        {page === 'por-gobierno' ? (
          <PorGobiernoView />
        ) : page === 'empleo' ? (
          <EmpleoIneView />
        ) : page === 'politica' ? (
          standalone ? (
            <section className="panel standalone-notice" aria-labelledby="standalone-politica-titulo">
              <p className="eyebrow">Copia HTML autónoma sin conexión</p>
              <h1 id="standalone-politica-titulo">Vista Política no disponible sin conexión</h1>
              <p className="lede">
                La Lectura Política y Estratégica de la Región de Aysén consulta en vivo las APIs oficiales del Banco Central (BCCh), DIPRES y SINIM.
                Para utilizarla, abre la aplicación conectada al servidor local de Chile Territorial.
              </p>
              <a className="primary link-button" href="#comparar">Volver a Vista Contable</a>
            </section>
          ) : (
            <PoliticalView />
          )
        ) : page === 'estructura' ? (
          standalone ? (
            <section className="panel standalone-notice" aria-labelledby="standalone-estructura-titulo">
              <p className="eyebrow">Copia HTML autónoma sin conexión</p>
              <h1 id="standalone-estructura-titulo">Estructura Productiva no disponible sin conexión</h1>
              <p className="lede">
                El módulo de Estructura Productiva y Especialización (416 series BCCh-BDE) consulta el servidor local de Chile Territorial.
              </p>
              <a className="primary link-button" href="#comparar">Volver al comparador</a>
            </section>
          ) : (
            <EstructuraView />
          )
        ) : page === 'demografia' ? (
          standalone ? (
            <section className="panel standalone-notice" aria-labelledby="standalone-demografia-titulo">
              <p className="eyebrow">Copia HTML autónoma sin conexión</p>
              <h1 id="standalone-demografia-titulo">PIB per Cápita y Convergencia no disponible sin conexión</h1>
              <p className="lede">
                El módulo de PIB per Cápita, Población INE y σ-convergencia requiere conexión al servidor local de Chile Territorial.
              </p>
              <a className="primary link-button" href="#comparar">Volver al comparador</a>
            </section>
          ) : (
            <DemografiaView />
          )
        ) : page === 'laboratorio' ? (
          standalone ? (
            <section className="panel standalone-notice" aria-labelledby="standalone-laboratorio-titulo">
              <p className="eyebrow">Copia HTML autónoma sin conexión</p>
              <h1 id="standalone-laboratorio-titulo">Laboratorio y Dossiers no disponible sin conexión</h1>
              <p className="lede">
                El Laboratorio de Investigación y Dossiers de solo lectura requiere conexión al servidor local de Chile Territorial.
              </p>
              <a className="primary link-button" href="#comparar">Volver al comparador</a>
            </section>
          ) : (
            <LaboratorioView />
          )
        ) : page === 'metodologia' ? (
          <article className="method">
            <p className="eyebrow">Observatorio económico · Cuentas Nacionales</p>
            <h1>Metodología</h1>
            <p className="lede">Qué mide cada indicador del comparador, cómo interpretar los resultados y cuál es el estado del corte activo.</p>

            <section className="method-release panel" aria-labelledby="corte-activo-titulo">
              <div className="method-release-head">
                <h2 id="corte-activo-titulo">Corte activo y cobertura</h2>
                {activeRelease && (
                  <span className={`status-badge ${activeRelease.estado === 'aprobada' ? 'is-official' : 'is-demo'}`}>
                    {activeRelease.estado === 'aprobada' ? 'Oficial' : 'Prueba'}
                  </span>
                )}
              </div>
              {metadata.loading ? (
                <p className="subtle" role="status">Cargando metadatos del corte…</p>
              ) : metadata.error ? (
                <p className="error" role="alert">{metadata.error}</p>
              ) : !activeRelease ? (
                <p className="subtle">No hay publicaciones oficiales registradas en el servicio.</p>
              ) : (
                <>
                  <dl className="release-grid">
                    <div>
                      <dt>Corte cargado</dt>
                      <dd className="mono">{activeRelease.id}</dd>
                    </div>
                    <div>
                      <dt>Fuente</dt>
                      <dd>{activeRelease.fuente}</dd>
                    </div>
                    <div>
                      <dt>Fecha de actualización / extracción</dt>
                      <dd>{formatReleaseDate(activeRelease.fecha)}</dd>
                    </div>
                    <div>
                      <dt>Cobertura</dt>
                      <dd>
                        {activeRelease.cobertura ? (
                          <div className="coverage-block">
                            <span>
                              <strong>{number.format(activeRelease.cobertura.disponibles)}</strong> / {number.format(activeRelease.cobertura.esperadas)} observaciones
                              {activeReleaseCoveragePct !== null && ` (${number.format(activeReleaseCoveragePct)}%)`}
                            </span>
                            {activeReleaseCoveragePct !== null && (
                              <span className="coverage-meter" aria-hidden="true">
                                <span style={{ width: `${activeReleaseCoveragePct}%` }} />
                              </span>
                            )}
                          </div>
                        ) : (
                          'No informada en el registro de este corte'
                        )}
                      </dd>
                    </div>
                  </dl>
                  <div className="release-notes">
                    <h3>Notas de versión</h3>
                    {activeRelease.cambios && activeRelease.cambios.length > 0 ? (
                      <ul className="changelog">
                        {activeRelease.cambios.map((note, index) => <li key={index}>{note}</li>)}
                      </ul>
                    ) : (
                      <p className="subtle">Sin notas de versión registradas para este corte.</p>
                    )}
                  </div>
                </>
              )}
            </section>

            <dl className="method-definitions">
              <dt>PIB real</dt><dd>Volumen encadenado en millones de pesos. El año de referencia figura en cada observación. Los componentes encadenados pueden no sumar el total oficial.</dd>
              <dt>PIB nominal</dt><dd>Valor de la producción a precios corrientes, en millones de pesos.</dd>
              <dt>Crecimiento real</dt><dd>Variación porcentual respecto al año anterior compatible. Se utiliza la fórmula 100 × (PIB real actual / PIB real anterior − 1).</dd>
              <dt>Participación regional</dt><dd>PIB nominal regional dividido por el PIB nominal nacional del mismo año y corte, expresado como porcentaje. Solo aplica a regiones.</dd>
              <dt>Crecimiento acumulado e índice histórico</dt><dd>Ambos usan el PIB real del año inicial seleccionado como base. El índice divide el nivel de cada año por la base y multiplica por 100. El crecimiento acumulado equivale al índice menos 100. Se requiere una base positiva y compatible.</dd>
              <dt>Ranking del último año</dt><dd>Orden descendente de las regiones seleccionadas con un valor comparable. Los empates comparten posición y Chile figura como referencia.</dd>
              <dt>Fuente oficial</dt><dd>Base de Datos Estadísticos del Banco Central de Chile. <a href={bdeReal}>Cuadro de PIB real</a> y <a href={bdeNominal}>cuadro de PIB nominal</a>.</dd>
              <dt>Precisión del corte BDE público</dt><dd>Los cuadros aportan los niveles redondeados a miles de millones de pesos. La conversión a millones es exacta. Las tasas y participaciones calculadas usan esos niveles y pueden diferir de los indicadores publicados con más precisión por el Banco Central.</dd>
              <dt>Procedencia</dt><dd>Consulta el origen y la precisión disponible en la tabla. La escala del gráfico es aproximada. Los datos sintéticos están identificados como prueba. Un cero informado conserva su valor y cada ausencia conserva su estado.</dd>
            </dl>
            <a className="primary link-button" href="#comparar">Volver al comparador</a>
          </article>
        ) : (
          <>
            <section className="intro">
              <div>
                <p className="eyebrow">Observatorio económico regional · Chile</p>
                <h1>Comparador de PIB</h1>
                <p className="lede">Compara la actividad económica de las 16 regiones y usa el total de Chile como referencia con trazabilidad por corte oficial.</p>
              </div>
              {regions.length > 0 && (
                <div className="intro-index" aria-hidden="true">
                  <strong>{regions.length}</strong>
                  <span>Regiones · {start}–{last}</span>
                </div>
              )}
            </section>

            <div className="dashboard">
              <aside className="filters panel" aria-labelledby="filters">
                <h2 id="filters">Filtros</h2>
                {!standalone && <label className="field">Origen de los datos
                  <select value={mode} onChange={event => { setMode(event.target.value as typeof mode); setDownloadError('') }}>
                    <option value="official">Publicaciones oficiales</option>
                    <option value="demo">Demostración sintética</option>
                  </select>
                </label>}
                {mode === 'official' && releases.length > 0 && <label className="field">Fecha de actualización
                  <select value={cut} onChange={event => { setCut(event.target.value); setDownloadError('') }}>
                    {releases.map((item, idx) => (
                      <option key={item.id} value={item.id}>
                        {formatHumanDate(item.fecha)}{releases.length > 1 && idx === 0 ? ' (más reciente)' : ''}
                      </option>
                    ))}
                  </select>
                </label>}
                <div className="field-pair">
                  <label className="field">Desde
                    <select value={start} onChange={event => chooseStart(Number(event.target.value))}>
                      {options.map(value => <option key={value}>{value}</option>)}
                    </select>
                  </label>
                  <label className="field">Hasta
                    <select value={end ?? ''} onChange={event => { setEnd(event.target.value ? Number(event.target.value) : null); setDownloadError('') }}>
                      <option value="">Último disponible</option>
                      {options.filter(value => value >= start).reverse().map(value => <option key={value}>{value}</option>)}
                    </select>
                  </label>
                </div>
                <label className="field">Indicador
                  <select value={measure} onChange={event => { setMeasure(event.target.value as typeof measure); setDownloadError('') }}>
                    {metrics.map(item => <option key={item.id} value={item.id}>{item.optionLabel}</option>)}
                  </select>
                </label>
                <fieldset>
                  <legend>Regiones</legend>
                  <div className="region-actions">
                    <button type="button" className="text-button" disabled={!regions.length} onClick={() => { setDownloadError(''); setSelected(regions.map(item => item.codigo)) }}>Seleccionar todas</button>
                    <button type="button" className="text-button" disabled={!selected.length} onClick={() => { setDownloadError(''); setSelected([]) }}>Limpiar</button>
                  </div>
                  <div className="region-presets" role="group" aria-label="Atajos por macrozona">
                    {regionPresets.map(preset => {
                      const presetCodes = preset.codes.filter(code => regionCodeSet.has(code))
                      const isActive = presetCodes.length > 0 && presetCodes.length === selected.length && presetCodes.every(code => selected.includes(code))
                      return (
                        <button
                          key={preset.id}
                          type="button"
                          className="preset-chip"
                          aria-pressed={isActive}
                          disabled={!presetCodes.length}
                          onClick={() => { setDownloadError(''); setSelected(presetCodes) }}
                        >
                          {preset.label}
                        </button>
                      )
                    })}
                  </div>
                  <div className="regions">
                    {regions.map(region => <label key={region.codigo} className="check-row"><input type="checkbox" checked={selected.includes(region.codigo)} onChange={() => toggle(region.codigo)} />{region.nombre}</label>)}
                  </div>
                </fieldset>
                <label className="check-row benchmark"><input type="checkbox" checked={showBenchmark} disabled={metric.metric === 'participacion'} onChange={event => setBenchmark(event.target.checked)} /> Incluir referencia de Chile</label>
                {metric.metric === 'participacion' && <p className="subtle">La participación se calcula solo para regiones.</p>}
              </aside>

              <section className="panel results" aria-labelledby="results" aria-busy={loading}>
                <div className="results-top">
                  <div className="results-heading">
                    <p className="eyebrow">{start === last ? start : `${start}–${last}`} · {chosen.length} {chosen.length === 1 ? 'región' : 'regiones'}</p>
                    <h2 id="results">{metric.label} por región</h2>
                    <p className="results-unit-line">
                      {metric.unitShort}
                      {derived ? ` · Base ${start}` : unitRow?.anio_referencia && metric.valuation === 'real' ? ` · Precios constantes ${unitRow.anio_referencia}` : ''}
                    </p>
                  </div>
                  <div className="result-downloads">
                    <button className="primary" disabled={!active?.publication || downloading} onClick={download}>
                      <span aria-hidden="true">↓</span> {downloading ? 'Descargando…' : 'Descargar CSV'}
                    </button>
                    {offlineDownload && mode === 'official' && <>
                      <a href="/descargas/Chile_Territorial_Oficial.html" download aria-describedby="offline-description">Descargar HTML autónomo</a>
                      <small id="offline-description" className="subtle">Copia del corte completo</small>
                    </>}
                  </div>
                </div>

                <div className="metric-precision-bar">
                  <p className="metric-precision-text">{metric.precision}</p>
                  <InfoPopover
                    title="¿Qué diferencia al PIB real del PIB nominal?"
                    label="Diferencia entre PIB real y PIB nominal"
                    placement="inline"
                    align="right"
                  >
                    <p><strong>PIB real:</strong> valora toda la producción usando los precios de un mismo año base (2018), eliminando la inflación. Es la medida correcta para saber si la economía creció o cayó entre años.</p>
                    <p><strong>PIB nominal:</strong> usa los precios vigentes de cada año (incluye la inflación). Sirve para medir el tamaño monetario de ese año y calcular el peso (%) de cada región sobre Chile.</p>
                  </InfoPopover>
                </div>
                {isDemo && <p className="notice"><strong>Datos sintéticos</strong> · Demostración del comparador. Las cifras son ficticias.</p>}
                {downloadError && <p className="error" role="alert">{downloadError}</p>}
                {loading ? <p className="empty" role="status">Cargando información…</p> : errors ? (
                  <div className="empty">
                    <p className="error" role="alert">{errors}</p>
                    <button className="text-button" onClick={() => {
                      setResult({ key: '', rows: [], publication: '', error: '' })
                      if (metadata.error) setMetadata({ loading: true, error: '' })
                      setRetry(value => value + 1)
                    }}>Reintentar</button>
                  </div>
                ) : pendingOfficial ? <p className="empty">Aún no hay publicaciones oficiales disponibles. La demostración sintética se activa desde los filtros.</p> : !chosen.length ? <p className="empty">Selecciona al menos una región para comparar.</p> : (
                  <>
                    <section className="kpi-strip is-three" aria-label="Resumen de cifras seleccionadas">
                      <div className="kpi-card kpi-card-accent">
                        <span className="kpi-label">{chosen.length === 1 ? `Región seleccionada (${last})` : `Mayor valor regional (${last})`}</span>
                        <strong className="kpi-value" title={leader?.row ? `${display(leader.row)} ${leader.row.unidad}` : undefined}>
                          {formatKpiValue(leader?.row)}
                        </strong>
                        <span className="kpi-unit">{metric.unitShort}</span>
                        <span className="kpi-meta">
                          {leader
                            ? `${leader.territory.nombre}${tiedLeaders.length > 1 ? ` (+${tiedLeaders.length - 1} empate)` : ''}${leader.row?.estado === 'preliminar' ? ' · Preliminar' : ''}`
                            : comparableRanking ? 'Sin dato informado' : 'Unidades o referencias distintas'}
                        </span>
                      </div>

                      <div className="kpi-card">
                        {metric.metric === 'participacion' ? (
                          <>
                            <span className="kpi-label">Suma seleccionada ({last})</span>
                            <strong className="kpi-value">
                              {participationSum !== null ? `${dec1Number.format(participationSum)}%` : '—'}
                            </strong>
                            <span className="kpi-unit">del PIB nominal nacional</span>
                            <span className="kpi-meta">
                              {regionalValues.length > 0
                                ? `Peso de ${regionalValues.length} ${regionalValues.length === 1 ? 'región' : 'regiones'} en Chile`
                                : 'Sin dato comparable'}
                            </span>
                          </>
                        ) : (
                          <>
                            <span className="kpi-label">Referencia Chile ({last})</span>
                            <strong className="kpi-value" title={chileRowAtEnd ? `${display(chileRowAtEnd)} ${chileRowAtEnd.unidad}` : undefined}>
                              {formatKpiValue(chileRowAtEnd)}
                            </strong>
                            <span className="kpi-unit">{metric.unitShort}</span>
                            <span className="kpi-meta">
                              {chileRowAtEnd?.valor != null
                                ? `${derived ? `Base ${start}` : 'Total nacional'}${chileRowAtEnd.estado === 'preliminar' ? ' · Preliminar' : ''}`
                                : chileRowAtEnd ? status[chileRowAtEnd.estado] : 'Sin dato nacional'}
                            </span>
                          </>
                        )}
                      </div>

                      <div className="kpi-card has-info-corner">
                        <InfoPopover
                          title="Respaldo técnico de los datos"
                          label="Ver respaldo técnico y cobertura del corte"
                          placement="corner"
                          align="right"
                        >
                          <p><strong>Fuente:</strong> {isDemo ? 'Datos sintéticos de demostración local' : 'Banco Central de Chile · Cuentas Nacionales Regionales (BDE)'}.</p>
                          <p><strong>Cobertura:</strong> {releaseCoverage && releaseCoverage.esperadas > 0
                            ? `${intNumber.format(releaseCoverage.disponibles)} de ${intNumber.format(releaseCoverage.esperadas)} registros (${dec1Number.format((releaseCoverage.disponibles / releaseCoverage.esperadas) * 100)}%)`
                            : `${intNumber.format(selectedWithValue)} de ${intNumber.format(tableRows.length)} observaciones con dato`}.</p>
                          {active?.publication && <p><strong>Identificador interno:</strong> <code>{active.publication}</code></p>}
                        </InfoPopover>
                        <span className="kpi-label">Actualización</span>
                        <strong className="kpi-value is-date">
                          {chosenPublication ? formatHumanDate(chosenPublication.fecha) : 'Corte local'}
                        </strong>
                        <span className="kpi-unit">{isDemo ? 'Demostración sintética' : 'Datos oficiales · BCCh'}</span>
                        <span className="kpi-meta">Período {start === last ? start : `${start}–${last}`}</span>
                      </div>
                    </section>

                    <div className="view-switch" role="group" aria-label="Visualización">
                      <button aria-pressed={view === 'chart'} onClick={() => setView('chart')}>Serie histórica</button>
                      <button aria-pressed={view === 'ranking'} onClick={() => setView('ranking')}>Ranking {last}</button>
                      <button aria-pressed={view === 'table'} onClick={() => setView('table')}>Tabla y procedencia</button>
                    </div>
                    {view === 'chart' ? <History series={series} years={years} label={metric.label} unit={unit} /> : view === 'ranking' ? (
                      comparableRanking ? <ul className="chart" aria-label={`${metric.label} por región en ${last}`}>
                        {rows.map(({ territory, row }) => {
                          const value = Number(row?.valor ?? 0)
                          const width = Math.abs(value) / magnitude * (hasNegative ? 50 : 100)
                          const rank = row?.valor == null ? 0 : ranked.findIndex(item => compareValues(item.row!.valor!, row.valor!) === 0) + 1
                          return <li key={territory.codigo}>
                            <span className="chart-label">{territory.codigo !== 'CL' && rank > 0 && `${rank}. `}{territory.nombre}</span>
                            <span className={`track ${hasNegative ? 'diverging' : ''}`} aria-hidden="true">
                              {row?.valor != null && <span className={`bar ${territory.codigo === 'CL' ? 'reference' : ''}`} style={{ width: `${width}%`, left: `${hasNegative ? (value < 0 ? 50 - width : 50) : 0}%` }} />}
                            </span>
                            <span className="chart-value">{row?.valor == null ? (row ? status[row.estado] : 'Sin dato') : number.format(value)}</span>
                          </li>
                        })}
                      </ul> : <p className="empty">Las regiones seleccionadas usan unidades o referencias distintas en {last}.</p>
                    ) : (
                      <div className="table-scroll" tabIndex={0} aria-label="Tabla de PIB regional" role="region">
                        <table className="history-table">
                          <caption className="sr-only">{metric.label}, {start}–{last}{unit ? `, ${unit}` : ''}</caption>
                          <thead><tr><th scope="col">Año</th><th scope="col">Territorio</th><th scope="col" className="numeric">Valor</th><th scope="col">Evidencia</th><th scope="col">Procedencia</th></tr></thead>
                          <tbody>{tableRows.map(({ territory, row, year }) => <tr key={`${territory.codigo}/${year}`}>
                            <td>{year}</td><th scope="row">{territory.nombre}</th>
                            <td className="numeric">{display(row)}</td>
                            <td>{row ? (derived && row.clase === 'oficial' ? 'Calculado con datos oficiales' : evidence(row)) : 'Sin dato'}{row?.estado === 'preliminar' && ' · Preliminar'}</td>
                            <td>{row ? <button className="text-button" aria-label={`Ver procedencia de ${territory.nombre} en ${year}`} onClick={() => derived ? explainDerived(row) : explain(row)}>Ver detalle</button> : '—'}</td>
                          </tr>)}</tbody>
                        </table>
                      </div>
                    )}
                    <p className="result-source">
                      <strong>Fuente:</strong> {isDemo ? 'Demostración sintética local' : 'Banco Central de Chile · Cuentas Nacionales Regionales'}
                      {chosenPublication && ` · Actualizado el ${formatHumanDate(chosenPublication.fecha)}`}
                    </p>
                    {publicTables && <p className="subtle">Niveles de origen redondeados a miles de millones de pesos. <a href={metric.valuation === 'real' ? bdeReal : bdeNominal}>Ver cuadro del Banco Central</a>.</p>}
                  </>
                )}
              </section>
            </div>
          </>
        )}
      </main>

      <footer className="wrap footer footer-confiasur">
        <div className="footer-brand-block">
          <img
            src="/brand/confiasur-logo-dark.png"
            alt="CONFIASUR Consultores"
            className="footer-logo-img"
            width={168}
            height={33}
          />
          <span className="footer-tagline">INTEGRIDAD · CONFIANZA · TERRITORIO</span>
        </div>
        <div className="footer-contact-block">
          <a href="mailto:Contacto@confiasur.com">Contacto@confiasur.com</a>
          <span>@confiasur</span>
          <span>Región de Aysén · Patagonia, Chile</span>
          <a href="#metodologia">Metodología y fuentes</a>
        </div>
      </footer>
      <dialog ref={dialog} onClose={() => provenanceRequest.current?.abort()} aria-labelledby="detail-title">
        <h2 id="detail-title">Procedencia</h2>
        {detail?.error ? <p role="alert">{detail.error}</p> : !detail?.row ? <p role="status">Cargando detalle…</p> :
          <dl className="detail">
            <dt>Observación</dt><dd>{detail.row.observacion}</dd>
            <dt>Corte</dt><dd>{detail.row.publicacion}</dd>
            {detail.row.serie_bde && <><dt>Serie BDE</dt><dd>{detail.row.serie_bde}</dd></>}
            {publicTables && <><dt>Cuadro de origen</dt><dd><a href={metric.valuation === 'real' ? bdeReal : bdeNominal}>Base de Datos Estadísticos del Banco Central de Chile</a></dd></>}
            {detail.row.artefacto && <><dt>Artefacto</dt><dd>{detail.row.artefacto}</dd></>}
            {detail.row.selector && <><dt>Registro de origen</dt><dd>{detail.row.selector}</dd></>}
            {detail.row.formula_version && <><dt>Fórmula</dt><dd>{detail.row.formula_version}</dd></>}
            {detail.row.insumos.length > 0 && <><dt>Insumos</dt><dd>{detail.row.insumos.join(', ')}</dd></>}
            {detail.row.motivo && <><dt>Nota</dt><dd>{detail.row.motivo}</dd></>}
          </dl>}
        <form method="dialog"><button className="primary">Cerrar</button></form>
      </dialog>
    </>
  )
}

createRoot(document.getElementById('root')!).render(<App />)
