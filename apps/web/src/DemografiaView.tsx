import { useCallback, useEffect, useId, useMemo, useState } from 'react'
import { InfoPopover } from './components/InfoPopover'
import { ApiServiceError } from './services/bcchService'
import {
  escapeCsvCell,
  fetchDemografiaPoblacion,
  triggerFileDownload,
} from './services/fase2Service'
import type {
  DemografiaPoblacionResponse,
  ObservacionPerCapita,
  SigmaConvergenciaPunto,
} from './services/fase2Service'

const num0 = new Intl.NumberFormat('es-CL', { maximumFractionDigits: 0 })
const num1 = new Intl.NumberFormat('es-CL', { minimumFractionDigits: 1, maximumFractionDigits: 1 })
const num2 = new Intl.NumberFormat('es-CL', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

function fmtClp(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return 'Sin dato'
  return `$ ${num0.format(value)}`
}

function fmtMillionsClp(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return 'Sin dato'
  return `$${num0.format(value)} millones`
}

function fmtPop(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return 'Sin dato'
  return `${num0.format(value)} hab.`
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

export function DemografiaView() {
  const yearSelectId = useId()
  const valuationSelectId = useId()

  const [selectedYear, setSelectedYear] = useState<number>(2025)
  const [valuation, setValuation] = useState<'real' | 'nominal'>('real')
  const [rankingView, setRankingView] = useState<'both' | 'bars' | 'table'>('both')

  const [state, setState] = useState<{
    loading: boolean
    data: DemografiaPoblacionResponse | null
    error: ApiServiceError | Error | null
  }>({ loading: true, data: null, error: null })

  const loadDemografia = useCallback(async (signal?: AbortSignal) => {
    setState(prev => ({ ...prev, loading: true, error: null }))
    try {
      const data = await fetchDemografiaPoblacion(2013, 2025, signal)
      if (!signal?.aborted) {
        setState({ loading: false, data, error: null })
        if (data.anios_disponibles.length > 0 && !data.anios_disponibles.includes(2025)) {
          setSelectedYear(data.ultimo_anio)
        }
      }
    } catch (err) {
      if (signal?.aborted || (err instanceof DOMException && err.name === 'AbortError')) return
      setState({
        loading: false,
        data: null,
        error: err instanceof Error ? err : new Error('No se pudo consultar PIB per cápita y población INE.'),
      })
    }
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    loadDemografia(controller.signal)
    return () => controller.abort()
  }, [loadDemografia])

  const aniosDisponibles = useMemo(() => {
    const list = state.data?.anios_disponibles ?? Array.from({ length: 13 }, (_, i) => 2013 + i)
    return [...list].reverse()
  }, [state.data])

  const getPerCapita = useCallback(
    (row?: ObservacionPerCapita | null): number | null => {
      if (!row) return null
      return valuation === 'real' ? row.pib_per_capita_real_clp : row.pib_per_capita_nominal_clp
    },
    [valuation],
  )

  const getIndexChile = useCallback(
    (row?: ObservacionPerCapita | null): number | null => {
      if (!row) return null
      return valuation === 'real' ? row.indice_real_chile_100 : row.indice_nominal_chile_100
    },
    [valuation],
  )

  const getPibTotal = useCallback(
    (row?: ObservacionPerCapita | null): number | null => {
      if (!row) return null
      return valuation === 'real' ? row.pib_real_millones : row.pib_nominal_millones
    },
    [valuation],
  )

  const yearRows = useMemo(() => {
    if (!state.data) return []
    return state.data.observaciones.filter(o => o.anio === selectedYear)
  }, [state.data, selectedYear])

  const chileRow = useMemo(() => yearRows.find(r => r.territorio === 'CL') ?? null, [yearRows])
  const aysenRow = useMemo(() => yearRows.find(r => r.territorio === '11') ?? null, [yearRows])

  const rankedAll = useMemo(() => {
    const regional = yearRows
      .filter(r => r.territorio !== 'CL')
      .sort((a, b) => (getPerCapita(b) ?? -Infinity) - (getPerCapita(a) ?? -Infinity))
    return chileRow ? [...regional, chileRow].sort((a, b) => (getPerCapita(b) ?? -Infinity) - (getPerCapita(a) ?? -Infinity)) : regional
  }, [yearRows, chileRow, getPerCapita])

  const regionalLeader = useMemo(() => {
    return yearRows
      .filter(r => r.territorio !== 'CL' && getPerCapita(r) !== null)
      .sort((a, b) => (getPerCapita(b) ?? -Infinity) - (getPerCapita(a) ?? -Infinity))[0] ?? null
  }, [yearRows, getPerCapita])

  const maxPerCapita = useMemo(() => {
    const vals = rankedAll.map(r => getPerCapita(r) ?? 0).filter(v => Number.isFinite(v) && v > 0)
    return vals.length ? Math.max(...vals) : 1
  }, [rankedAll, getPerCapita])

  const sigmaSeries: SigmaConvergenciaPunto[] = useMemo(
    () => state.data?.sigma_convergencia ?? [],
    [state.data],
  )

  const getCv = useCallback(
    (pt?: SigmaConvergenciaPunto | null): number | null => {
      if (!pt) return null
      return valuation === 'real' ? pt.cv_real_pct : pt.cv_nominal_pct
    },
    [valuation],
  )

  const sigmaSelected = useMemo(
    () => sigmaSeries.find(s => s.anio === selectedYear) ?? sigmaSeries.at(-1) ?? null,
    [sigmaSeries, selectedYear],
  )

  const sigmaTrend = useMemo(() => {
    const valid = sigmaSeries.filter(s => getCv(s) !== null)
    if (valid.length < 2) return null
    const first = valid[0]
    const last = valid[valid.length - 1]
    const diff = (getCv(last) ?? 0) - (getCv(first) ?? 0)
    return {
      firstYear: first.anio,
      lastYear: last.anio,
      diffPp: diff,
      label: diff < -0.5
        ? 'Convergencia regional (menor dispersión)'
        : diff > 0.5
          ? 'Divergencia regional (mayor dispersión)'
          : 'Dispersión regional estable',
    }
  }, [sigmaSeries, getCv])

  const maxCv = useMemo(() => {
    const vals = sigmaSeries.map(s => getCv(s) ?? 0).filter(v => Number.isFinite(v) && v > 0)
    return vals.length ? Math.max(...vals, 1) : 100
  }, [sigmaSeries, getCv])

  function handleDownloadCsv() {
    if (!state.data || rankedAll.length === 0) return
    const header = [
      'anio',
      'territorio',
      'nombre',
      'valoracion',
      'poblacion_ine',
      'pib_total_millones_clp',
      'pib_per_capita_clp',
      'indice_chile_100',
      'serie_poblacion',
      'serie_pib',
    ]
    const rows = rankedAll.map(row => [
      row.anio,
      row.territorio,
      row.nombre,
      valuation,
      row.poblacion ?? '',
      getPibTotal(row) ?? '',
      getPerCapita(row) !== null ? Math.round(getPerCapita(row)!) : '',
      getIndexChile(row) !== null ? getIndexChile(row)!.toFixed(2) : '',
      row.serie_poblacion ?? '',
      valuation === 'real' ? (row.serie_pib_real ?? '') : (row.serie_pib_nominal ?? ''),
    ])
    const csv = [header, ...rows].map(line => line.map(escapeCsvCell).join(',')).join('\r\n')
    triggerFileDownload(
      `pib-per-capita-${valuation}-${selectedYear}.csv`,
      csv,
      'text/csv;charset=utf-8',
    )
  }

  let regionalRankCounter = 0

  return (
    <div className="fase2-page">
      <section className="intro pol-intro">
        <div>
          <p className="eyebrow">Economía y población · Banco Central + INE</p>
          <h1>PIB por habitante y brechas entre regiones</h1>
          <p className="lede">
            Cuánto produce en promedio cada habitante en las 16 regiones de Chile (2013–2025) y si las diferencias territoriales se han acortado o ampliado.
          </p>
        </div>
        <div className="fase2-toolbar">
          <button
            type="button"
            className="primary"
            disabled={!state.data || rankedAll.length === 0 || state.loading}
            onClick={handleDownloadCsv}
          >
            <span aria-hidden="true">↓</span> Descargar CSV
          </button>
          <button
            type="button"
            className="secondary-btn"
            disabled={state.loading}
            onClick={() => loadDemografia()}
          >
            {state.loading ? 'Actualizando…' : 'Actualizar'}
          </button>
        </div>
      </section>

      {/* Advertencia metodológica destacada (obligatoria por ADR-009) */}
      <div className="method-warning-banner" role="note" aria-label="Advertencia metodológica de escala territorial">
        <strong>Advertencia metodológica · Escala territorial del PIB:</strong>{' '}
        {state.data?.advertencia_comunal ||
          'Las cifras de PIB son de escala nacional y regional y nunca deben imputarse a las 346 comunas.'}
      </div>

      <section className="panel fase2-controls-bar" aria-label="Filtros de PIB per cápita y convergencia">
        <div className="fase2-controls-grid">
          <label className="field" htmlFor={yearSelectId}>
            Año del corte (2013–2025)
            <select
              id={yearSelectId}
              value={selectedYear}
              onChange={event => setSelectedYear(Number(event.target.value))}
            >
              {aniosDisponibles.map(yr => (
                <option key={yr} value={yr}>{yr}</option>
              ))}
            </select>
          </label>

          <label className="field" htmlFor={valuationSelectId}>
            Valoración del PIB
            <select
              id={valuationSelectId}
              value={valuation}
              onChange={event => setValuation(event.target.value as 'real' | 'nominal')}
            >
              <option value="real">Real (volumen encadenado · comparable en el tiempo)</option>
              <option value="nominal">Nominal (precios corrientes de cada año)</option>
            </select>
          </label>

          <div className="field">
            <span>Formato del ranking</span>
            <div className="view-switch compact-switch" role="group" aria-label="Formato del ranking per cápita">
              <button type="button" aria-pressed={rankingView === 'both'} onClick={() => setRankingView('both')}>
                Barras y tabla
              </button>
              <button type="button" aria-pressed={rankingView === 'bars'} onClick={() => setRankingView('bars')}>
                Barras
              </button>
              <button type="button" aria-pressed={rankingView === 'table'} onClick={() => setRankingView('table')}>
                Tabla
              </button>
            </div>
          </div>
        </div>
      </section>

      {state.loading ? (
        <section className="panel axis-main">
          <div className="pol-loading" role="status" aria-live="polite">
            <span className="pol-spinner" aria-hidden="true" />
            <div className="pol-skeleton-lines">
              <p className="pol-loading-label">Cargando series oficiales de población INE y PIB regional BCCh…</p>
              <div className="skeleton-bar wide" />
              <div className="skeleton-bar medium" />
              <div className="skeleton-bar short" />
            </div>
          </div>
        </section>
      ) : state.error ? (
        <section className="panel axis-main">
          <div className="service-error-box" role="alert">
            <p className="error">{state.error.message}</p>
            <p className="subtle">
              Verifica que el corte demográfico esté publicado en <code className="mono">GET /api/v1/demografia/poblacion</code>.
            </p>
            <button type="button" className="secondary-btn" onClick={() => loadDemografia()}>
              Reintentar consulta
            </button>
          </div>
        </section>
      ) : !state.data || yearRows.length === 0 ? (
        <section className="panel axis-main">
          <p className="empty">No se encontraron observaciones demográficas y de PIB per cápita para {selectedYear}.</p>
        </section>
      ) : (
        <>
          {/* 4 Tarjetas KPI */}
          <section className="panel axis-main" aria-label="Indicadores clave de PIB per cápita y convergencia">
            <div className="pol-kpi-grid">
              <div className="pol-kpi-card">
                <span className="kpi-label">PIB per cápita Chile ({selectedYear} · {valuation})</span>
                <strong className="pol-kpi-num">{fmtClp(getPerCapita(chileRow))}</strong>
                <span className="kpi-meta">
                  Índice base = 100 · Población INE: {fmtPop(chileRow?.poblacion)}
                </span>
              </div>

              <div className="pol-kpi-card is-highlight">
                <span className="kpi-label">PIB per cápita Aysén ({selectedYear} · {valuation})</span>
                <strong className="pol-kpi-num">{fmtClp(getPerCapita(aysenRow))}</strong>
                <span className="kpi-meta">
                  Razón vs Chile = {getIndexChile(aysenRow) !== null ? num1.format(getIndexChile(aysenRow)!) : '—'} (Chile = 100) · {fmtPop(aysenRow?.poblacion)}
                </span>
              </div>

              <div className="pol-kpi-card">
                <span className="kpi-label">Líder regional per cápita ({selectedYear})</span>
                <strong className="pol-kpi-num">{fmtClp(getPerCapita(regionalLeader))}</strong>
                <span className="kpi-meta">
                  {regionalLeader
                    ? `${regionalLeader.nombre} · Índice ${getIndexChile(regionalLeader) !== null ? num1.format(getIndexChile(regionalLeader)!) : '—'}`
                    : 'Sin dato'}
                </span>
              </div>

              <div className="pol-kpi-card has-info-corner">
                <InfoPopover label="Cómo se calcula la brecha entre regiones" title="Brecha territorial (σ-convergencia)">
                  <p>Corresponde al coeficiente de variación (CV) del PIB por habitante entre las 16 regiones. Si baja con los años, las regiones se acercan entre sí (convergencia); si sube, la brecha se amplía.</p>
                </InfoPopover>
                <span className="kpi-label">Brecha entre regiones ({sigmaSelected?.anio ?? selectedYear})</span>
                <strong className="pol-kpi-num">
                  {getCv(sigmaSelected) !== null ? `${num2.format(getCv(sigmaSelected)!)}%` : 'Sin dato'}
                </strong>
                <span className="kpi-meta">
                  {sigmaTrend
                    ? `${sigmaTrend.label} (${sigmaTrend.diffPp > 0 ? '+' : ''}${num2.format(sigmaTrend.diffPp)} pp en ${sigmaTrend.firstYear}–${sigmaTrend.lastYear})`
                    : 'Dispersión entre las 16 regiones'}
                </span>
              </div>
            </div>
          </section>

          {/* Ranking de las 16 regiones + Chile */}
          <section className="panel axis-main" aria-labelledby="demo-ranking-titulo">
            <div className="axis-main-top">
              <div>
                <h2 id="demo-ranking-titulo">
                  Ranking de PIB per cápita ({valuation === 'real' ? 'real' : 'nominal'}) · 16 regiones y Chile ({selectedYear})
                </h2>
                <p className="subtle">
                  Pesos chilenos por habitante (CLP/hab.) e índice relativo con <strong>Chile = 100</strong>. Aysén se resalta en verde y la referencia nacional de Chile en azul pizarra.
                </p>
              </div>
            </div>

            {(rankingView === 'both' || rankingView === 'bars') && (
              <div className="visual-card">
                <h4>Comparación horizontal · PIB per cápita {valuation} ({selectedYear})</h4>
                <ul className="activity-chart" aria-label={`Ranking de PIB per cápita ${valuation} en ${selectedYear}`}>
                  {rankedAll.map(row => {
                    const isChile = row.territorio === 'CL'
                    const isAysen = row.territorio === '11'
                    if (!isChile) regionalRankCounter += 1
                    const val = getPerCapita(row)
                    const idxChile = getIndexChile(row)
                    const widthPct = val !== null && maxPerCapita > 0 ? Math.max(2, (val / maxPerCapita) * 100) : 0
                    return (
                      <li
                        key={row.territorio}
                        className={`activity-row${isAysen ? ' is-admin' : isChile ? ' is-pesca' : ''}`}
                      >
                        <div className="activity-name">
                          <span>{isChile ? 'Ref.' : `${regionalRankCounter}.`} {row.nombre}</span>
                          {isAysen && <span className="mini-tag is-admin">Aysén</span>}
                          {isChile && <span className="mini-tag is-pesca">Chile = 100</span>}
                        </div>
                        <span className="activity-track" aria-hidden="true">
                          {val !== null && <span className="activity-bar" style={{ width: `${widthPct}%` }} />}
                        </span>
                        <div className="activity-values">
                          <strong>{fmtClp(val)}</strong>
                          <span className="subtle">
                            Índice: {idxChile !== null ? num1.format(idxChile) : '—'} · {fmtPop(row.poblacion)}
                          </span>
                        </div>
                      </li>
                    )
                  })}
                </ul>
              </div>
            )}

            {(rankingView === 'both' || rankingView === 'table') && (
              <div className="table-scroll" tabIndex={0} role="region" aria-label={`Tabla de PIB per cápita y población INE ${selectedYear}`}>
                <table className="pol-table">
                  <caption className="sr-only">
                    PIB per cápita {valuation}, PIB total y población INE de las 16 regiones y Chile en {selectedYear}
                  </caption>
                  <thead>
                    <tr>
                      <th scope="col">Territorio</th>
                      <th scope="col" className="numeric">Población INE</th>
                      <th scope="col" className="numeric">PIB {valuation}</th>
                      <th scope="col" className="numeric">PIB por habitante</th>
                      <th scope="col" className="numeric">Relación vs Chile (100)</th>
                      <th scope="col" className="numeric"><span className="sr-only">Fuente técnica</span></th>
                    </tr>
                  </thead>
                  <tbody>
                    {rankedAll.map(row => {
                      const isChile = row.territorio === 'CL'
                      const isAysen = row.territorio === '11'
                      return (
                        <tr
                          key={row.territorio}
                          className={isAysen ? 'row-admin' : isChile ? 'row-pesca' : undefined}
                        >
                          <th scope="row">{row.nombre}</th>
                          <td className="numeric">{row.poblacion !== null ? num0.format(row.poblacion) : 'Sin dato'}</td>
                          <td className="numeric">{fmtMillionsClp(getPibTotal(row))}</td>
                          <td className="numeric"><strong>{fmtClp(getPerCapita(row))}</strong></td>
                          <td className="numeric">
                            {getIndexChile(row) !== null ? num1.format(getIndexChile(row)!) : 'Sin dato'}
                          </td>
                          <td className="numeric info-cell">
                            <InfoPopover
                              placement="inline"
                              label={`Ver referencia oficial de ${row.nombre}`}
                              title={`Series oficiales · ${row.nombre}`}
                            >
                              <p><strong>Población (INE):</strong> <code className="mono">{row.serie_poblacion || 'INE/BDE'}</code></p>
                              <p><strong>PIB {valuation} (BCCh):</strong> <code className="mono">{valuation === 'real' ? (row.serie_pib_real || '—') : (row.serie_pib_nominal || '—')}</code></p>
                            </InfoPopover>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )}

            <footer className="source-footer" aria-label="Pie de fuente PIB per cápita">
              <div className="source-footer-row">
                <span><strong>Fuente:</strong> Banco Central de Chile + INE (Población)</span>
                <span><strong>Actualizado:</strong> {fmtTimestamp(state.data.actualizado_en)}</span>
                <span>El PIB oficial se mide solo a escala nacional y regional.</span>
              </div>
            </footer>
          </section>

          {/* Evolución histórica de sigma-convergencia (2013-2025) */}
          <section className="panel axis-main" aria-labelledby="demo-sigma-titulo">
            <div>
              <h2 id="demo-sigma-titulo">Evolución histórica de σ-convergencia (2013–2025)</h2>
              <p className="subtle">
                El coeficiente de variación (CV = desviación estándar / media entre las 16 regiones) mide la dispersión territorial del PIB per cápita.
                Una caída sostenida del CV sugiere <strong>σ-convergencia</strong>; un aumento sugiere <strong>divergencia regional</strong>.
              </p>
            </div>

            {sigmaSeries.length === 0 ? (
              <p className="empty">No hay serie histórica de σ-convergencia disponible en este corte.</p>
            ) : (
              <>
                <div className="visual-card">
                  <h4>Coeficiente de variación interregional ({valuation === 'real' ? 'PIB per cápita real' : 'PIB per cápita nominal'})</h4>
                  <ul className="sigma-bars" aria-label={`Evolución histórica del coeficiente de variación ${valuation} entre 2013 y 2025`}>
                    {sigmaSeries.map(pt => {
                      const val = getCv(pt)
                      const widthPct = val !== null && maxCv > 0 ? Math.max(2, (val / maxCv) * 100) : 0
                      const isSelectedYr = pt.anio === selectedYear
                      return (
                        <li key={pt.anio} className={`compare-bar-row${isSelectedYr ? ' is-selected-year' : ''}`}>
                          <span className="compare-bar-label">
                            {pt.anio} {isSelectedYr && <span className="mini-tag is-admin">Corte</span>}
                          </span>
                          <span className="compare-track" aria-hidden="true">
                            {val !== null && (
                              <span
                                className={`compare-fill ${isSelectedYr ? 'is-primary' : 'is-reference'}`}
                                style={{ width: `${widthPct}%` }}
                              />
                            )}
                          </span>
                          <span className="compare-bar-val">
                            {val !== null ? `${num2.format(val)}%` : 'Sin dato'}
                          </span>
                        </li>
                      )
                    })}
                  </ul>
                </div>

                <div className="table-scroll" tabIndex={0} role="region" aria-label="Tabla histórica de sigma-convergencia 2013 a 2025">
                  <table className="pol-table is-compact">
                    <caption className="sr-only">Serie anual de coeficiente de variación (σ-convergencia) del PIB per cápita entre las 16 regiones</caption>
                    <thead>
                      <tr>
                        <th scope="col">Año</th>
                        <th scope="col" className="numeric">CV Real (%)</th>
                        <th scope="col" className="numeric">CV Nominal (%)</th>
                        <th scope="col" className="numeric">Media regional real ($ CLP)</th>
                        <th scope="col" className="numeric">Regiones</th>
                      </tr>
                    </thead>
                    <tbody>
                      {[...sigmaSeries].reverse().map(pt => (
                        <tr key={pt.anio} className={pt.anio === selectedYear ? 'row-admin' : undefined}>
                          <th scope="row">{pt.anio}</th>
                          <td className="numeric">{pt.cv_real_pct !== null ? `${num2.format(pt.cv_real_pct)}%` : '—'}</td>
                          <td className="numeric">{pt.cv_nominal_pct !== null ? `${num2.format(pt.cv_nominal_pct)}%` : '—'}</td>
                          <td className="numeric">{fmtClp(pt.media_real_clp)}</td>
                          <td className="numeric">{pt.regiones_incluidas ?? 16}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            )}

            <footer className="source-footer" aria-label="Pie de fuente convergencia regional">
              <div className="source-footer-row">
                <span><strong>Fuente:</strong> BCCh-BDE + INE</span>
                <span><strong>Método:</strong> σ-convergencia mediante coeficiente de variación no ponderado de las 16 regiones.</span>
              </div>
            </footer>
          </section>
        </>
      )}
    </div>
  )
}
