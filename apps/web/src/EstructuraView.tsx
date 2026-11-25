import { useCallback, useEffect, useId, useMemo, useState } from 'react'
import { ApiServiceError } from './services/bcchService'
import {
  REGIONES_CHILE,
  escapeCsvCell,
  fetchSectorialRegiones,
  triggerFileDownload,
} from './services/fase2Service'
import type {
  ActividadSectorial,
  RegionSectorial,
  SectorialRegionesResponse,
} from './services/fase2Service'

const num0 = new Intl.NumberFormat('es-CL', { maximumFractionDigits: 0 })
const num2 = new Intl.NumberFormat('es-CL', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
const num3 = new Intl.NumberFormat('es-CL', { minimumFractionDigits: 3, maximumFractionDigits: 3 })

const ANIOS_DEFECTO = Array.from({ length: 13 }, (_, i) => 2013 + i)

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

function describeHhi(hhi: number | null): string {
  if (hhi === null || !Number.isFinite(hhi)) return 'Sin dato'
  if (hhi >= 2500) return 'Alta concentración (≥ 2.500)'
  if (hhi >= 1500) return 'Concentración moderada (1.500–2.499)'
  return 'Estructura diversificada (< 1.500)'
}

export function EstructuraView() {
  const regionSelectId = useId()
  const yearSelectId = useId()

  const [selectedRegion, setSelectedRegion] = useState<string>('11')
  const [selectedYear, setSelectedYear] = useState<number>(2025)
  const [viewMode, setViewMode] = useState<'regional' | 'comparativa'>('regional')
  const [activityFormat, setActivityFormat] = useState<'both' | 'bars' | 'table'>('both')
  const [rankingMetric, setRankingMetric] = useState<'hhi' | 'krugman'>('hhi')

  const [state, setState] = useState<{
    loading: boolean
    data: SectorialRegionesResponse | null
    error: ApiServiceError | Error | null
  }>({ loading: true, data: null, error: null })

  const loadSectorial = useCallback(async (anio: number, signal?: AbortSignal) => {
    setState(prev => ({ ...prev, loading: true, error: null }))
    try {
      const data = await fetchSectorialRegiones(anio, undefined, signal)
      if (!signal?.aborted) {
        setState({ loading: false, data, error: null })
      }
    } catch (err) {
      if (signal?.aborted || (err instanceof DOMException && err.name === 'AbortError')) return
      setState({
        loading: false,
        data: null,
        error: err instanceof Error ? err : new Error('No se pudo consultar la estructura sectorial de las 16 regiones.'),
      })
    }
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    loadSectorial(selectedYear, controller.signal)
    return () => controller.abort()
  }, [selectedYear, loadSectorial])

  const aniosDisponibles = useMemo(() => {
    const raw = state.data?.anios_disponibles
    return raw && raw.length > 0 ? [...raw].reverse() : [...ANIOS_DEFECTO].reverse()
  }, [state.data])

  const regionOptions = useMemo(() => {
    if (state.data && state.data.regiones.length > 0) {
      const byCode = new Map(state.data.regiones.map(r => [r.codigo, r.nombre]))
      return REGIONES_CHILE.map(r => ({
        codigo: r.codigo,
        nombre: byCode.get(r.codigo) ?? r.nombre,
      }))
    }
    return REGIONES_CHILE
  }, [state.data])

  const activeRegion: RegionSectorial | null = useMemo(() => {
    if (!state.data || state.data.regiones.length === 0) return null
    return (
      state.data.regiones.find(r => r.codigo === selectedRegion) ??
      state.data.regiones[0] ??
      null
    )
  }, [state.data, selectedRegion])

  const actividadesOrdenadas: ActividadSectorial[] = useMemo(() => {
    if (!activeRegion) return []
    return [...activeRegion.actividades].sort((a, b) => {
      const av = a.participacion_nominal_pct ?? a.valor_nominal_millones ?? -Infinity
      const bv = b.participacion_nominal_pct ?? b.valor_nominal_millones ?? -Infinity
      return bv - av
    })
  }, [activeRegion])

  const maxSharePct = useMemo(() => {
    const vals = actividadesOrdenadas
      .map(a => a.participacion_nominal_pct ?? 0)
      .filter(v => Number.isFinite(v) && v > 0)
    return vals.length ? Math.max(...vals) : 1
  }, [actividadesOrdenadas])

  const rankingHhi = useMemo(() => state.data?.ranking_hhi ?? [], [state.data])
  const rankingKrugman = useMemo(() => state.data?.ranking_krugman ?? [], [state.data])
  const maxHhi = useMemo(() => {
    const vals = rankingHhi.map(r => r.hhi ?? 0).filter(v => Number.isFinite(v) && v > 0)
    return vals.length ? Math.max(...vals, 1) : 10000
  }, [rankingHhi])
  const maxKrugman = useMemo(() => {
    const vals = rankingKrugman.map(r => r.krugman ?? 0).filter(v => Number.isFinite(v) && v > 0)
    return vals.length ? Math.max(...vals, 0.01) : 1
  }, [rankingKrugman])

  function handleDownloadCsv() {
    if (!state.data) return
    if (viewMode === 'regional' && activeRegion) {
      const header = [
        'anio',
        'region_codigo',
        'region_nombre',
        'actividad_codigo',
        'actividad_nombre',
        'valor_nominal_millones',
        'participacion_nominal_pct',
        'cociente_localizacion_lq',
        'especializada_lq_gt_1',
        'crecimiento_real_anual_pct',
        'serie_bde_nominal',
        'serie_bde_real',
        'hhi_regional',
        'diversificacion_regional',
        'krugman_regional',
      ]
      const rows = actividadesOrdenadas.map(act => [
        activeRegion.anio,
        activeRegion.codigo,
        activeRegion.nombre,
        act.codigo,
        act.nombre,
        act.valor_nominal_millones ?? '',
        act.participacion_nominal_pct ?? '',
        act.lq ?? '',
        act.especializada ? 'si' : 'no',
        act.crecimiento_real_pct ?? '',
        act.serie_nominal ?? '',
        act.serie_real ?? '',
        activeRegion.hhi ?? '',
        activeRegion.diversificacion ?? '',
        activeRegion.krugman ?? '',
      ])
      const csv = [header, ...rows].map(line => line.map(escapeCsvCell).join(',')).join('\r\n')
      triggerFileDownload(
        `estructura-sectorial-r${activeRegion.codigo}-${activeRegion.anio}.csv`,
        csv,
        'text/csv;charset=utf-8',
      )
      return
    }

    const header = [
      'anio',
      'region_codigo',
      'region_nombre',
      'vab_nominal_millones',
      'hhi_0_10000',
      'diversificacion_0_1',
      'krugman_0_1',
      'sector_mas_especializado',
      'lq_maximo',
    ]
    const rows = rankingHhi.map(r => [
      state.data!.anio,
      r.codigo,
      r.nombre,
      r.vab_nominal_millones ?? '',
      r.hhi ?? '',
      r.diversificacion ?? '',
      r.krugman ?? '',
      r.sector_mas_especializado ?? '',
      r.max_lq ?? '',
    ])
    const csv = [header, ...rows].map(line => line.map(escapeCsvCell).join(',')).join('\r\n')
    triggerFileDownload(
      `ranking-estructura-16-regiones-${state.data.anio}.csv`,
      csv,
      'text/csv;charset=utf-8',
    )
  }

  return (
    <div className="fase2-page">
      <section className="intro pol-intro">
        <div>
          <p className="eyebrow">Observatorio económico · BCCh-BDE · {state.data?.total_series ?? 416} series oficiales</p>
          <h1>Estructura Productiva y Especialización · 16 Regiones</h1>
          <p className="lede">
            Composición nominal por actividad económica (13 ramas Cuentas Nacionales), Cociente de Localización (LQ),
            concentración HHI, diversificación productiva e Índice de Krugman para las 16 regiones de Chile.
          </p>
        </div>
        <div className="fase2-toolbar">
          <button
            type="button"
            className="primary"
            disabled={!state.data || state.loading}
            onClick={handleDownloadCsv}
          >
            <span aria-hidden="true">↓</span> Descargar CSV
          </button>
          <button
            type="button"
            className="secondary-btn"
            disabled={state.loading}
            onClick={() => loadSectorial(selectedYear)}
          >
            {state.loading ? 'Actualizando…' : 'Actualizar'}
          </button>
        </div>
      </section>

      <section className="panel fase2-controls-bar" aria-label="Filtros de estructura productiva">
        <div className="fase2-controls-grid">
          <label className="field" htmlFor={regionSelectId}>
            Región (01 a 16)
            <select
              id={regionSelectId}
              value={selectedRegion}
              onChange={event => setSelectedRegion(event.target.value)}
            >
              {regionOptions.map(reg => (
                <option key={reg.codigo} value={reg.codigo}>
                  {reg.codigo} · {reg.nombre}
                </option>
              ))}
            </select>
          </label>

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

          <div className="field">
            <span>Vista del módulo</span>
            <div className="view-switch compact-switch" role="group" aria-label="Vista de estructura productiva">
              <button
                type="button"
                aria-pressed={viewMode === 'regional'}
                onClick={() => setViewMode('regional')}
              >
                Detalle regional
              </button>
              <button
                type="button"
                aria-pressed={viewMode === 'comparativa'}
                onClick={() => setViewMode('comparativa')}
              >
                Comparativa 16 regiones
              </button>
            </div>
          </div>
        </div>
      </section>

      {state.data?.estado_actualizacion === 'respaldo_ultimo_corte_aprobado' && (
        <p className="notice" role="status">
          <strong>Respaldo del último corte aprobado:</strong> se muestran los datos sectoriales verificados guardados localmente.
        </p>
      )}

      {state.loading ? (
        <section className="panel axis-main">
          <div className="pol-loading" role="status" aria-live="polite">
            <span className="pol-spinner" aria-hidden="true" />
            <div className="pol-skeleton-lines">
              <p className="pol-loading-label">Cargando corte sectorial de 16 regiones ({selectedYear}) desde BCCh-BDE…</p>
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
              Verifica que el corte sectorial de 416 series esté publicado en <code className="mono">GET /api/v1/sectorial/regiones</code>.
            </p>
            <button type="button" className="secondary-btn" onClick={() => loadSectorial(selectedYear)}>
              Reintentar consulta
            </button>
          </div>
        </section>
      ) : !state.data || state.data.regiones.length === 0 ? (
        <section className="panel axis-main">
          <p className="empty">No se encontraron observaciones sectoriales publicadas para el año {selectedYear}.</p>
        </section>
      ) : (
        <>
          {/* KPIs de la región seleccionada */}
          {activeRegion && (
            <section className="panel axis-main" aria-labelledby="est-kpi-titulo">
              <div className="axis-main-top">
                <div>
                  <p className="eyebrow">Región {activeRegion.codigo} · Corte {activeRegion.anio}</p>
                  <h2 id="est-kpi-titulo">{activeRegion.nombre}</h2>
                  <p className="subtle">
                    Indicadores calculados sobre Valor Agregado Bruto (VAB) a precios corrientes (valoración nominal); los volúmenes reales encadenados no son aditivos.
                  </p>
                </div>
                <span className="status-badge is-official">
                  {actividadesOrdenadas.length} actividades
                </span>
              </div>

              <div className="fase2-kpi-grid is-five">
                <div className="pol-kpi-card is-highlight">
                  <span className="kpi-label">VAB nominal total ({activeRegion.anio})</span>
                  <strong className="pol-kpi-num">{fmtMillions(activeRegion.vab_nominal_millones)}</strong>
                  <span className="kpi-meta">
                    {activeRegion.pib_nominal_millones !== null
                      ? `PIB nominal: ${fmtMillions(activeRegion.pib_nominal_millones)}`
                      : 'Suma de actividades nominales'}
                  </span>
                </div>

                <div className="pol-kpi-card">
                  <span className="kpi-label">Concentración HHI (0–10.000)</span>
                  <strong className="pol-kpi-num">
                    {activeRegion.hhi !== null ? num0.format(activeRegion.hhi) : 'Sin dato'}
                  </strong>
                  <span className="kpi-meta">{describeHhi(activeRegion.hhi)}</span>
                </div>

                <div className="pol-kpi-card">
                  <span className="kpi-label">Diversificación (1 − HHI/10.000)</span>
                  <strong className="pol-kpi-num">
                    {activeRegion.diversificacion !== null ? num3.format(activeRegion.diversificacion) : 'Sin dato'}
                  </strong>
                  <span className="kpi-meta">Más cercano a 1,000 = mayor diversidad</span>
                </div>

                <div className="pol-kpi-card">
                  <span className="kpi-label">Índice de Krugman (0–1)</span>
                  <strong className="pol-kpi-num">
                    {activeRegion.krugman !== null ? num3.format(activeRegion.krugman) : 'Sin dato'}
                  </strong>
                  <span className="kpi-meta">Disimilitud estructural vs promedio nacional</span>
                </div>

                <div className="pol-kpi-card is-highlight">
                  <span className="kpi-label">Sector más especializado (mayor LQ)</span>
                  <strong className="pol-kpi-num">
                    {activeRegion.sector_mas_especializado
                      ? `LQ ${num2.format(activeRegion.sector_mas_especializado.lq)}`
                      : 'Sin dato'}
                  </strong>
                  <span className="kpi-meta">
                    {activeRegion.sector_mas_especializado?.nombre ?? 'Sin datos de especialización'}
                  </span>
                </div>
              </div>

              {activeRegion.diferencia_impuestos_millones !== null && (
                <p className="subtle">
                  Nota contable: diferencia <code className="mono">PIB − VAB</code> en {activeRegion.anio} ={' '}
                  <strong>{fmtMillions(activeRegion.diferencia_impuestos_millones)}</strong> (impuestos sobre los productos netos de subvenciones).
                </p>
              )}
            </section>
          )}

          {/* Detalle de las 13 actividades económicas de la región seleccionada */}
          {viewMode === 'regional' && activeRegion && (
            <section className="panel axis-main" aria-labelledby="est-actividades-titulo">
              <div className="axis-main-top">
                <div>
                  <h2 id="est-actividades-titulo">
                    Las {actividadesOrdenadas.length} actividades económicas · {activeRegion.nombre} ({activeRegion.anio})
                  </h2>
                  <p className="subtle">
                    Se resaltan en verde los sectores con especialización relativa superior al perfil nacional (<strong>LQ &gt; 1,00</strong>).
                  </p>
                </div>
                <div className="view-switch compact-switch" role="group" aria-label="Formato de actividades">
                  <button type="button" aria-pressed={activityFormat === 'both'} onClick={() => setActivityFormat('both')}>
                    Barras y tabla
                  </button>
                  <button type="button" aria-pressed={activityFormat === 'bars'} onClick={() => setActivityFormat('bars')}>
                    Solo barras
                  </button>
                  <button type="button" aria-pressed={activityFormat === 'table'} onClick={() => setActivityFormat('table')}>
                    Solo tabla
                  </button>
                </div>
              </div>

              {(activityFormat === 'both' || activityFormat === 'bars') && (
                <div className="visual-card">
                  <h4>Participación nominal (%) y Cociente de Localización (LQ)</h4>
                  <ul className="activity-chart" aria-label={`Participación nominal y LQ por actividad en ${activeRegion.nombre}`}>
                    {actividadesOrdenadas.map(act => {
                      const widthPct = act.participacion_nominal_pct !== null && maxSharePct > 0
                        ? Math.max(1.5, (act.participacion_nominal_pct / maxSharePct) * 100)
                        : 0
                      const isSpec = act.especializada || (act.lq !== null && act.lq > 1)
                      return (
                        <li
                          key={`${act.codigo}-${act.serie_nominal ?? ''}`}
                          className={`activity-row${isSpec ? ' is-admin' : ''}`}
                        >
                          <div className="activity-name">
                            <span>{act.nombre}</span>
                            {isSpec && (
                              <span className="mini-tag is-admin">
                                LQ {act.lq !== null ? num2.format(act.lq) : '> 1'}
                              </span>
                            )}
                          </div>
                          <span className="activity-track" aria-hidden="true">
                            {act.participacion_nominal_pct !== null && (
                              <span className="activity-bar" style={{ width: `${widthPct}%` }} />
                            )}
                          </span>
                          <div className="activity-values">
                            <strong>{fmtPct(act.participacion_nominal_pct)}</strong>
                            <span className="subtle">
                              {fmtMillions(act.valor_nominal_millones)} · Real: {fmtPct(act.crecimiento_real_pct, true)}
                            </span>
                          </div>
                        </li>
                      )
                    })}
                  </ul>
                </div>
              )}

              {(activityFormat === 'both' || activityFormat === 'table') && (
                <div className="table-scroll" tabIndex={0} role="region" aria-label={`Tabla completa de actividades económicas de ${activeRegion.nombre}`}>
                  <table className="pol-table">
                    <caption className="sr-only">
                      Estructura sectorial de {activeRegion.nombre} en {activeRegion.anio}: valor nominal, participación, LQ, crecimiento real y códigos BDE
                    </caption>
                    <thead>
                      <tr>
                        <th scope="col">Actividad económica</th>
                        <th scope="col" className="numeric">Valor nominal (MM$)</th>
                        <th scope="col" className="numeric">Participación (%)</th>
                        <th scope="col" className="numeric">LQ</th>
                        <th scope="col" className="numeric">Crec. real anual (%)</th>
                        <th scope="col">Serie BDE (Nominal / Real)</th>
                      </tr>
                    </thead>
                    <tbody>
                      {actividadesOrdenadas.map(act => {
                        const isSpec = act.especializada || (act.lq !== null && act.lq > 1)
                        return (
                          <tr
                            key={`${act.codigo}-${act.serie_nominal ?? ''}`}
                            className={isSpec ? 'row-admin' : undefined}
                          >
                            <th scope="row">
                              {act.nombre}{' '}
                              {isSpec && <span className="mini-tag is-admin">Especializado</span>}
                            </th>
                            <td className="numeric">{fmtMillions(act.valor_nominal_millones)}</td>
                            <td className="numeric">{fmtPct(act.participacion_nominal_pct)}</td>
                            <td className="numeric">
                              <strong>{act.lq !== null ? num2.format(act.lq) : 'Sin dato'}</strong>
                            </td>
                            <td className="numeric">{fmtPct(act.crecimiento_real_pct, true)}</td>
                            <td className="mono">
                              <div>{act.serie_nominal || '—'}</div>
                              {act.serie_real && <div className="subtle">{act.serie_real}</div>}
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              )}

              <footer className="source-footer" aria-label="Trazabilidad de fuente sectorial">
                <div className="source-footer-row">
                  <span><strong>Fuente:</strong> BCCh-BDE · {state.data.total_series} series ({state.data.fuente_trazabilidad.institucion})</span>
                  <span><strong>Endpoint:</strong> <code className="mono">{state.data.fuente_trazabilidad.endpoint || `/api/v1/sectorial/regiones?anio=${selectedYear}`}</code></span>
                </div>
                <div className="source-footer-row">
                  <span><strong>Actualizado:</strong> {fmtTimestamp(state.data.actualizado_en)}</span>
                  <span><strong>Extracción:</strong> {fmtTimestamp(state.data.extraido_en)}</span>
                  <span>Perímetro nominal (VAB a precios corrientes) · LQ y Krugman respecto al agregado regionalizado de 16 regiones.</span>
                </div>
              </footer>
            </section>
          )}

          {/* Ranking comparativo de las 16 regiones por HHI y por Índice de Krugman */}
          <section className="panel axis-main" aria-labelledby="est-ranking-titulo">
            <div className="axis-main-top">
              <div>
                <h2 id="est-ranking-titulo">Ranking comparativo de las 16 regiones ({state.data.anio})</h2>
                <p className="subtle">
                  Compara la concentración interna (HHI) y la distancia estructural frente al país (Índice de Krugman). Haz clic en una región para inspeccionar sus 13 actividades.
                </p>
              </div>
              <div className="view-switch compact-switch" role="group" aria-label="Indicador del ranking regional">
                <button
                  type="button"
                  aria-pressed={rankingMetric === 'hhi'}
                  onClick={() => setRankingMetric('hhi')}
                >
                  Ranking por HHI
                </button>
                <button
                  type="button"
                  aria-pressed={rankingMetric === 'krugman'}
                  onClick={() => setRankingMetric('krugman')}
                >
                  Ranking por Krugman
                </button>
              </div>
            </div>

            <div className="visual-card">
              <h4>
                {rankingMetric === 'hhi'
                  ? `Concentración sectorial HHI (0–10.000) · Año ${state.data.anio}`
                  : `Índice de disimilitud de Krugman (0–1) · Año ${state.data.anio}`}
              </h4>
              <ul
                className="activity-chart"
                aria-label={rankingMetric === 'hhi' ? 'Ranking de regiones por HHI' : 'Ranking de regiones por Índice de Krugman'}
              >
                {(rankingMetric === 'hhi' ? rankingHhi : rankingKrugman).map((item, idx) => {
                  const val = rankingMetric === 'hhi' ? item.hhi : item.krugman
                  const denom = rankingMetric === 'hhi' ? maxHhi : maxKrugman
                  const widthPct = val !== null && denom > 0 ? Math.max(2, (val / denom) * 100) : 0
                  const isCurrent = item.codigo === selectedRegion
                  return (
                    <li key={item.codigo} className={`activity-row${isCurrent ? ' is-admin' : ''}`}>
                      <div className="activity-name">
                        <button
                          type="button"
                          className="text-button"
                          onClick={() => {
                            setSelectedRegion(item.codigo)
                            setViewMode('regional')
                          }}
                        >
                          {idx + 1}. {item.nombre}
                        </button>
                        {isCurrent && <span className="mini-tag is-admin">Seleccionada</span>}
                      </div>
                      <span className="activity-track" aria-hidden="true">
                        {val !== null && <span className="activity-bar" style={{ width: `${widthPct}%` }} />}
                      </span>
                      <div className="activity-values">
                        <strong>
                          {val !== null
                            ? (rankingMetric === 'hhi' ? num0.format(val) : num3.format(val))
                            : 'Sin dato'}
                        </strong>
                        <span className="subtle">
                          {item.sector_mas_especializado
                            ? `Top LQ: ${item.sector_mas_especializado}${item.max_lq !== null ? ` (${num2.format(item.max_lq)})` : ''}`
                            : fmtMillions(item.vab_nominal_millones)}
                        </span>
                      </div>
                    </li>
                  )
                })}
              </ul>
            </div>

            <div className="table-scroll" tabIndex={0} role="region" aria-label="Tabla comparativa de HHI, diversificación y Krugman por región">
              <table className="pol-table">
                <caption className="sr-only">Ranking comparativo de las 16 regiones por HHI, diversificación e Índice de Krugman en {state.data.anio}</caption>
                <thead>
                  <tr>
                    <th scope="col">#</th>
                    <th scope="col">Región</th>
                    <th scope="col" className="numeric">VAB nominal (MM$)</th>
                    <th scope="col" className="numeric">HHI (0–10.000)</th>
                    <th scope="col" className="numeric">Diversificación</th>
                    <th scope="col" className="numeric">Krugman (0–1)</th>
                    <th scope="col">Mayor especialización (LQ)</th>
                  </tr>
                </thead>
                <tbody>
                  {(rankingMetric === 'hhi' ? rankingHhi : rankingKrugman).map((item, idx) => (
                    <tr key={item.codigo} className={item.codigo === selectedRegion ? 'row-admin' : undefined}>
                      <td className="mono">{idx + 1}</td>
                      <th scope="row">
                        <button
                          type="button"
                          className="text-button"
                          onClick={() => {
                            setSelectedRegion(item.codigo)
                            setViewMode('regional')
                          }}
                        >
                          {item.nombre}
                        </button>
                      </th>
                      <td className="numeric">{fmtMillions(item.vab_nominal_millones)}</td>
                      <td className="numeric">{item.hhi !== null ? num0.format(item.hhi) : 'Sin dato'}</td>
                      <td className="numeric">{item.diversificacion !== null ? num3.format(item.diversificacion) : 'Sin dato'}</td>
                      <td className="numeric">{item.krugman !== null ? num3.format(item.krugman) : 'Sin dato'}</td>
                      <td>
                        {item.sector_mas_especializado
                          ? `${item.sector_mas_especializado}${item.max_lq !== null ? ` (LQ ${num2.format(item.max_lq)})` : ''}`
                          : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <footer className="source-footer" aria-label="Pie de fuente comparativa 16 regiones">
              <div className="source-footer-row">
                <span><strong>Fuente:</strong> BCCh-BDE · {state.data.total_series} series</span>
                <span><strong>Corte:</strong> {state.data.fuente_trazabilidad.corte || `Año ${state.data.anio}`}</span>
                <span><strong>Extracción:</strong> {fmtTimestamp(state.data.extraido_en)}</span>
              </div>
            </footer>
          </section>
        </>
      )}
    </div>
  )
}
