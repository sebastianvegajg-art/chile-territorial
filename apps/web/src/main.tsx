import { useEffect, useRef, useState } from 'react'
import { createRoot } from 'react-dom/client'
import { apiRoot, demoDefault, demoRelease, get, observations } from './api'
import type { Metric, Observation, Provenance, Publication, Territory, Valuation } from './api'
import './styles.css'

const metrics = [
  { id: 'nivel-real', label: 'PIB real', metric: 'nivel', valuation: 'real' },
  { id: 'nivel-nominal', label: 'PIB nominal', metric: 'nivel', valuation: 'nominal' },
  { id: 'crecimiento', label: 'Crecimiento real', metric: 'crecimiento', valuation: 'real' },
  { id: 'participacion', label: 'Participación regional', metric: 'participacion', valuation: 'nominal' },
] as const satisfies readonly { id: string; label: string; metric: Metric; valuation: Valuation }[]

const number = new Intl.NumberFormat('es-CL', { maximumFractionDigits: 2 })
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

function App() {
  const [page, setPage] = useState(location.hash === '#metodologia' ? 'metodologia' : 'comparar')
  const [mode, setMode] = useState<'official' | 'demo'>(demoDefault ? 'demo' : 'official')
  const [territories, setTerritories] = useState<Territory[]>([])
  const [releases, setReleases] = useState<Publication[]>([])
  const [cut, setCut] = useState('')
  const [selected, setSelected] = useState(['11'])
  const [benchmark, setBenchmark] = useState(true)
  const [year, setYear] = useState(2025)
  const [measure, setMeasure] = useState<(typeof metrics)[number]['id']>('nivel-real')
  const [view, setView] = useState<'chart' | 'table'>('chart')
  const [retry, setRetry] = useState(0)
  const [metadata, setMetadata] = useState({ loading: true, error: '' })
  const [result, setResult] = useState<{ key: string; rows: Observation[]; publication: string; error: string }>({
    key: '', rows: [], publication: '', error: '',
  })
  const [detail, setDetail] = useState<{ id: string; row?: Provenance; error?: string } | null>(null)
  const [downloading, setDownloading] = useState(false)
  const [downloadError, setDownloadError] = useState('')
  const dialog = useRef<HTMLDialogElement>(null)
  const provenanceRequest = useRef<AbortController | null>(null)

  const metric = metrics.find(item => item.id === measure)!
  const regions = territories.filter(item => item.nivel === 'regional' && item.codigo !== 'CL')
  const chosen = regions.filter(item => selected.includes(item.codigo))
  const chile = territories.find(item => item.codigo === 'CL')
  const showBenchmark = benchmark && metric.metric !== 'participacion'
  const compared = showBenchmark && chile ? [...chosen, chile] : chosen
  const publication = mode === 'demo' ? demoRelease : cut || releases[0]?.id
  const query = new URLSearchParams({
    anio_desde: String(year), anio_hasta: String(year), metrica: metric.metric, valoracion: metric.valuation,
  })
  if (publication) query.set('publicacion', publication)
  for (const item of compared) query.append('territorios', item.codigo)
  const key = publication && compared.length && chosen.length && !metadata.loading && !metadata.error ? query.toString() : ''
  const active = key && key === result.key ? result : null
  const isDemo = mode === 'demo' || active?.rows.some(row => row.clase === 'prueba')
  const errors = metadata.error || active?.error
  const pendingOfficial = mode === 'official' && !metadata.loading && !metadata.error && !publication
  const loading = metadata.loading || (!!key && !active)
  const rows = compared.map(territory => ({ territory, row: active?.rows.find(row => row.territorio === territory.codigo) }))
  const unit = active?.rows.find(row => row.valor !== null)?.unidad ?? active?.rows[0]?.unidad
  const magnitude = Math.max(1, ...rows.map(({ row }) => Math.abs(Number(row?.valor ?? 0))))
  const hasNegative = rows.some(({ row }) => Number(row?.valor) < 0)

  useEffect(() => {
    const sync = () => setPage(location.hash === '#metodologia' ? 'metodologia' : 'comparar')
    window.addEventListener('hashchange', sync)
    return () => window.removeEventListener('hashchange', sync)
  }, [])

  useEffect(() => {
    const request = new AbortController()
    Promise.all([
      get<Territory[]>('/territorios', request.signal),
      get<Publication[]>('/publicaciones', request.signal),
    ]).then(([data, publications]) => {
      setTerritories(data)
      setReleases(publications.filter(item => item.estado === 'aprobada'))
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
      const filters = new URLSearchParams(key)
      filters.set('publicacion', active.publication)
      const response = await fetch(`${apiRoot}/pib.csv?${filters}`)
      if (!response.ok || response.headers.get('X-Publicacion') !== active.publication) throw new Error()
      const url = URL.createObjectURL(await response.blob())
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = `pib-${active.publication}-${year}.csv`
      anchor.click()
      window.setTimeout(() => URL.revokeObjectURL(url), 1000)
    } catch {
      setDownloadError('No se pudo descargar el CSV para este corte.')
    } finally {
      setDownloading(false)
    }
  }

  return (
    <>
      <a className="skip-link" href="#contenido">Ir al contenido principal</a>
      <header className="masthead">
        <div className="masthead-inner wrap">
          <a className="brand" href="#comparar" aria-label="Chile Territorial, inicio">
            <span className="brand-mark" aria-hidden="true">▥</span>
            <span>Chile <strong>Territorial</strong></span>
          </a>
          <nav aria-label="Principal">
            <a href="#comparar" aria-current={page === 'comparar' ? 'page' : undefined}>Comparador</a>
            <a href="#metodologia" aria-current={page === 'metodologia' ? 'page' : undefined}>Metodología</a>
          </nav>
        </div>
      </header>

      <main id="contenido" className="wrap" tabIndex={-1}>
        {page === 'metodologia' ? (
          <article className="method">
            <h1>Metodología</h1>
            <p className="lede">Qué mide cada indicador del comparador y cómo interpretar los resultados.</p>
            <dl>
              <dt>PIB real</dt><dd>Volumen encadenado en millones de pesos. El año de referencia figura en cada observación. Los componentes encadenados pueden no sumar el total oficial.</dd>
              <dt>PIB nominal</dt><dd>Valor de la producción a precios corrientes, en millones de pesos.</dd>
              <dt>Crecimiento real</dt><dd>Variación porcentual respecto al año anterior compatible. Se utiliza la fórmula 100 × (PIB real actual / PIB real anterior − 1).</dd>
              <dt>Participación regional</dt><dd>PIB nominal regional dividido por el PIB nominal nacional del mismo año y corte, expresado como porcentaje. Solo aplica a regiones.</dd>
              <dt>Procedencia</dt><dd>Consulta el origen de cada fila en la tabla. Los datos sintéticos están identificados como prueba. Un cero informado conserva su valor y cada ausencia conserva su estado.</dd>
            </dl>
            <a className="primary link-button" href="#comparar">Volver al comparador</a>
          </article>
        ) : (
          <>
            <section className="intro">
              <div>
                <p className="eyebrow">Economía regional · Chile</p>
                <h1>Comparador de PIB</h1>
                <p className="lede">Compara la actividad económica de las 16 regiones y usa el total de Chile como referencia.</p>
              </div>

            </section>

            <div className="dashboard">
              <aside className="filters panel" aria-labelledby="filters">
                <h2 id="filters">Filtros</h2>
                <label className="field">Origen de los datos
                  <select value={mode} onChange={event => { setMode(event.target.value as typeof mode); setDownloadError('') }}>
                    <option value="official">Publicaciones oficiales</option>
                    <option value="demo">Demostración sintética</option>
                  </select>
                </label>
                {mode === 'official' && releases.length > 0 && <label className="field">Corte
                  <select value={cut} onChange={event => { setCut(event.target.value); setDownloadError('') }}>
                    <option value="">Última publicación</option>
                    {releases.map(item => <option key={item.id} value={item.id}>{item.fecha.slice(0, 10)} · {item.id}</option>)}
                  </select>
                </label>}
                <div className="field-pair">
                  <label className="field">Año
                    <select value={year} onChange={event => { setYear(Number(event.target.value)); setDownloadError('') }}>
                      {Array.from({ length: Math.max(2025, new Date().getFullYear()) - 2012 }, (_, index) => 2013 + index).reverse().map(value => <option key={value}>{value}</option>)}
                    </select>
                  </label>
                  <label className="field">Indicador
                    <select value={measure} onChange={event => { setMeasure(event.target.value as typeof measure); setDownloadError('') }}>
                      {metrics.map(item => <option key={item.id} value={item.id}>{item.label}</option>)}
                    </select>
                  </label>
                </div>
                <fieldset>
                  <legend>Regiones</legend>
                  <div className="region-actions">
                    <button type="button" className="text-button" disabled={!regions.length} onClick={() => setSelected(regions.map(item => item.codigo))}>Seleccionar todas</button>
                    <button type="button" className="text-button" disabled={!selected.length} onClick={() => setSelected([])}>Limpiar</button>
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
                  <div>
                    <p className="eyebrow">{year} · {chosen.length} {chosen.length === 1 ? 'región' : 'regiones'}</p>
                    <h2 id="results">{metric.label} por región</h2>
                    {unit && <p className="subtle">{unit}{active?.rows[0]?.anio_referencia && ` · Referencia ${active.rows[0].anio_referencia}`}</p>}
                  </div>
                  <button className="primary" disabled={!active?.publication || downloading} onClick={download}>
                    <span aria-hidden="true">↓</span> {downloading ? 'Descargando…' : 'Descargar CSV'}
                  </button>
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
                    <div className="view-switch" role="group" aria-label="Visualización">
                      <button aria-pressed={view === 'chart'} onClick={() => setView('chart')}>Gráfico</button>
                      <button aria-pressed={view === 'table'} onClick={() => setView('table')}>Tabla y procedencia</button>
                    </div>
                    {view === 'chart' ? (
                      <ul className="chart" aria-label={`${metric.label} por región en ${year}`}>
                        {rows.map(({ territory, row }) => {
                          const value = Number(row?.valor ?? 0)
                          const width = Math.abs(value) / magnitude * (hasNegative ? 50 : 100)
                          return <li key={territory.codigo}>
                            <span className="chart-label">{territory.nombre}</span>
                            <span className={`track ${hasNegative ? 'diverging' : ''}`} aria-hidden="true">
                              {row?.valor != null && <span className={`bar ${territory.codigo === 'CL' ? 'reference' : ''}`} style={{ width: `${width}%`, left: `${hasNegative ? (value < 0 ? 50 - width : 50) : 0}%` }} />}
                            </span>
                            <span className="chart-value">{row?.valor == null ? (row ? status[row.estado] : 'Sin dato') : number.format(value)}</span>
                          </li>
                        })}
                      </ul>
                    ) : (
                      <div className="table-scroll" tabIndex={0} aria-label="Tabla de PIB regional" role="region">
                        <table>
                          <caption className="sr-only">{metric.label}, {year}{unit ? `, ${unit}` : ''}</caption>
                          <thead><tr><th scope="col">Territorio</th><th scope="col">Valor</th><th scope="col">Evidencia</th><th scope="col">Procedencia</th></tr></thead>
                          <tbody>{rows.map(({ territory, row }) => <tr key={territory.codigo}>
                            <th scope="row">{territory.nombre}</th>
                            <td>{display(row)}</td>
                            <td>{row ? evidence(row) : 'Sin dato'}{row?.estado === 'preliminar' && ' · Preliminar'}</td>
                            <td>{row ? <button className="text-button" aria-label={`Ver procedencia de ${territory.nombre}`} onClick={() => explain(row)}>Ver detalle</button> : '—'}</td>
                          </tr>)}</tbody>
                        </table>
                      </div>
                    )}
                    <p className="result-source"><strong>Corte</strong> {active?.publication ?? '—'}{isDemo ? ' · Fuente de prueba' : active?.publication ? ` · Fuente: ${releases.find(item => item.id === active.publication)?.fuente ?? 'Banco Central de Chile'}` : ''}</p>
                  </>
                )}
              </section>
            </div>
          </>
        )}
      </main>

      <footer className="wrap footer"><strong>Chile Territorial</strong><a href="#metodologia">Metodología del PIB regional</a></footer>
      <dialog ref={dialog} onClose={() => provenanceRequest.current?.abort()} aria-labelledby="detail-title">
        <h2 id="detail-title">Procedencia</h2>
        {detail?.error ? <p role="alert">{detail.error}</p> : !detail?.row ? <p role="status">Cargando detalle…</p> :
          <dl className="detail">
            <dt>Observación</dt><dd>{detail.row.observacion}</dd>
            <dt>Corte</dt><dd>{detail.row.publicacion}</dd>
            {detail.row.serie_bde && <><dt>Serie BDE</dt><dd>{detail.row.serie_bde}</dd></>}
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
