import { useMemo, useState } from 'react'
import { InfoPopover } from './components/InfoPopover'
import { INE_EMPLEO_SECTORIAL } from './data/ineEmpleoSectorial'
import { escapeCsvCell, triggerFileDownload } from './services/fase2Service'

type TrayectoriaModo = 'sector' | 'total' | 'desocupacion'

const num0 = new Intl.NumberFormat('es-CL', { maximumFractionDigits: 0 })
const num1 = new Intl.NumberFormat('es-CL', { minimumFractionDigits: 1, maximumFractionDigits: 1 })

function fmtPersonas(miles: number | null | undefined): string {
  if (miles === null || miles === undefined || !Number.isFinite(miles)) return 'Sin dato'
  const personas = Math.round(miles * 1000)
  return num0.format(personas)
}

function fmtPersonasCorto(miles: number): string {
  if (miles >= 1000) return `${num1.format(miles / 1000)} mill.`
  if (miles >= 10) return `${num1.format(miles)} mil`
  return num0.format(Math.round(miles * 1000))
}

function fmtSignedPct(val: number | null): string {
  if (val === null || !Number.isFinite(val)) return '—'
  const sign = val > 0 ? '+' : ''
  return `${sign}${num1.format(val)}%`
}

const REGION_ORDER = [
  '11', 'CL', '15', '01', '02', '03', '04', '05', '13', '06', '07', '16', '08', '09', '14', '10', '12',
]

const QUICK_REGIONS = [
  { code: '11', label: 'Aysén' },
  { code: 'CL', label: 'Chile' },
  { code: '10', label: 'Los Lagos' },
  { code: '12', label: 'Magallanes' },
] as const

export function EmpleoIneView() {
  const data = INE_EMPLEO_SECTORIAL

  const [regionCode, setRegionCode] = useState<string>('11')
  const [selectedYear, setSelectedYear] = useState<number>(2025)
  const [showAllSectors, setShowAllSectors] = useState<boolean>(false)
  const [trayectoriaModo, setTrayectoriaModo] = useState<TrayectoriaModo>('sector')
  const [selectedSectorId, setSelectedSectorId] = useState<string>('administracion_publica_y_defensa')

  const regionOptions = useMemo(
    () =>
      REGION_ORDER
        .filter(code => Boolean(data.regiones[code]))
        .map(code => ({
          code,
          nombre: code === 'CL' ? 'Chile (total nacional)' : data.regiones[code].nombre,
        })),
    [data.regiones],
  )

  const region = data.regiones[regionCode] ?? data.regiones['11']
  const chile = data.regiones['CL']

  const aniosDisponibles = useMemo(() => [...data.anios].reverse(), [data.anios])

  const yearRec = useMemo(
    () => region.anuales.find(a => a.anio === selectedYear) ?? region.anuales[region.anuales.length - 1],
    [region.anuales, selectedYear],
  )
  const prevYearRec = useMemo(
    () => region.anuales.find(a => a.anio === yearRec.anio - 1) ?? null,
    [region.anuales, yearRec.anio],
  )
  const firstYearRec = region.anuales[0]
  const chileYearRec = useMemo(
    () => chile.anuales.find(a => a.anio === yearRec.anio) ?? chile.anuales[chile.anuales.length - 1],
    [chile.anuales, yearRec.anio],
  )

  // Sectores ordenados de mayor a menor para el año elegido (excluye 'no_sabe_no_responde' si es 0)
  const sectoresRanking = useMemo(() => {
    const total = yearRec.ocupados_miles || 1
    return data.sectores
      .filter(s => s.id !== 'no_sabe_no_responde' || (yearRec.sectores_miles[s.id] ?? 0) > 0)
      .map(s => {
        const miles = yearRec.sectores_miles[s.id] ?? 0
        const prevMiles = prevYearRec ? (prevYearRec.sectores_miles[s.id] ?? 0) : null
        const pctTotal = (miles / total) * 100
        const varAnualPct =
          prevMiles !== null && prevMiles > 0.05 ? ((miles - prevMiles) / prevMiles) * 100 : null
        return {
          ...s,
          miles,
          personas: Math.round(miles * 1000),
          pctTotal,
          varAnualPct,
        }
      })
      .filter(s => s.miles > 0)
      .sort((a, b) => b.miles - a.miles)
  }, [data.sectores, yearRec, prevYearRec])

  const sectoresVisibles = showAllSectors ? sectoresRanking : sectoresRanking.slice(0, 10)
  const maxSectorMiles = sectoresRanking[0]?.miles ?? 1
  const topSector = sectoresRanking[0] ?? null
  const secondSector = sectoresRanking[1] ?? null

  const activeSector = useMemo(
    () => data.sectores.find(s => s.id === selectedSectorId) ?? sectoresRanking[0] ?? data.sectores[0],
    [data.sectores, selectedSectorId, sectoresRanking],
  )

  // Variación total de ocupados
  const varTotalAnualPct = useMemo(() => {
    if (!prevYearRec || prevYearRec.ocupados_miles <= 0) return null
    return ((yearRec.ocupados_miles - prevYearRec.ocupados_miles) / prevYearRec.ocupados_miles) * 100
  }, [yearRec, prevYearRec])

  const cambioDesde2013Personas = Math.round((yearRec.ocupados_miles - firstYearRec.ocupados_miles) * 1000)

  // Serie histórica 2013–2026 para el gráfico SVG
  const chartPoints = useMemo(() => {
    return region.anuales.map(rec => {
      const ch = chile.anuales.find(c => c.anio === rec.anio)
      const val =
        trayectoriaModo === 'sector'
          ? rec.sectores_miles[activeSector.id] ?? 0
          : trayectoriaModo === 'total'
            ? rec.ocupados_miles
            : rec.tasa_desocupacion_pct ?? 0
      const refVal = trayectoriaModo === 'desocupacion' ? ch?.tasa_desocupacion_pct ?? null : null
      return {
        anio: rec.anio,
        enCurso: rec.en_curso,
        ultimoTrimestre: rec.ultimo_trimestre,
        val,
        refVal,
      }
    })
  }, [region.anuales, chile.anuales, trayectoriaModo, activeSector.id])

  const chartBounds = useMemo(() => {
    const vals = chartPoints.flatMap(p => (p.refVal !== null ? [p.val, p.refVal] : [p.val]))
    const maxV = Math.max(...vals, 0.5)
    const minV = trayectoriaModo === 'desocupacion' ? 0 : Math.min(...vals) * 0.78
    const span = Math.max(maxV - minV, 0.5)
    return {
      min: Math.max(0, minV),
      max: maxV + span * 0.14,
    }
  }, [chartPoints, trayectoriaModo])

  const selectedPoint = chartPoints.find(p => p.anio === yearRec.anio) ?? chartPoints[chartPoints.length - 1]
  const firstPoint = chartPoints[0]
  const deltaHistorico =
    firstPoint && selectedPoint && firstPoint.val > 0
      ? trayectoriaModo === 'desocupacion'
        ? selectedPoint.val - firstPoint.val
        : ((selectedPoint.val - firstPoint.val) / firstPoint.val) * 100
      : null

  function handleDownloadCsv() {
    const header = ['region', 'anio', 'estado', 'sector', 'personas_ocupadas', 'participacion_pct', 'variacion_anual_pct']
    const rows = sectoresRanking.map(s => [
      region.nombre,
      yearRec.anio,
      yearRec.en_curso ? `En curso (${yearRec.ultimo_trimestre})` : 'Promedio anual',
      s.nombre,
      s.personas,
      s.pctTotal.toFixed(2),
      s.varAnualPct !== null ? s.varAnualPct.toFixed(2) : '',
    ])
    const csv = [header, ...rows].map(line => line.map(escapeCsvCell).join(',')).join('\r\n')
    triggerFileDownload(`empleo-ine-${region.codigo}-${yearRec.anio}.csv`, csv, 'text/csv;charset=utf-8')
  }

  // Coordenadas SVG del gráfico de trayectoria
  const svgW = 760
  const svgH = 250
  const padL = 62
  const padR = 24
  const padT = 24
  const padB = 42
  const plotW = svgW - padL - padR
  const plotH = svgH - padT - padB

  const getX = (idx: number) =>
    chartPoints.length <= 1 ? padL + plotW / 2 : padL + (idx / (chartPoints.length - 1)) * plotW
  const getY = (val: number) => {
    const ratio = (val - chartBounds.min) / Math.max(chartBounds.max - chartBounds.min, 0.001)
    return padT + plotH - Math.max(0, Math.min(1, ratio)) * plotH
  }

  const linePath = chartPoints
    .map((p, i) => `${i === 0 ? 'M' : 'L'} ${getX(i).toFixed(1)} ${getY(p.val).toFixed(1)}`)
    .join(' ')

  const areaPath = chartPoints.length > 1
    ? `${linePath} L ${getX(chartPoints.length - 1).toFixed(1)} ${(padT + plotH).toFixed(1)} L ${getX(0).toFixed(1)} ${(padT + plotH).toFixed(1)} Z`
    : ''

  const refLinePath =
    trayectoriaModo === 'desocupacion'
      ? chartPoints
          .filter(p => p.refVal !== null)
          .map((p, i) => {
            const origIdx = chartPoints.findIndex(cp => cp.anio === p.anio)
            return `${i === 0 ? 'M' : 'L'} ${getX(origIdx).toFixed(1)} ${getY(p.refVal!).toFixed(1)}`
          })
          .join(' ')
      : ''

  return (
    <div className="emp-page">
      {/* Cabecera liviana y ordenada */}
      <header className="panel emp-header has-info-corner">
        <InfoPopover label="Fuente oficial y metodología del INE" title="Fuente oficial · INE">
          <p><strong>Organismo:</strong> {data.meta.fuente}</p>
          <p><strong>Actualización INE:</strong> {data.meta.fecha_actualizacion} (último trimestre: {data.meta.ultimo_trimestre_disponible}).</p>
          <p>{data.meta.nota_metodologica}</p>
          <p>{data.meta.nota_fiabilidad}</p>
          <p>
            <a href={data.meta.url_oficial} target="_blank" rel="noopener noreferrer">
              Portal INE Ocupación y Desocupación ↗
            </a>
          </p>
        </InfoPopover>

        <div className="emp-header-top">
          <div>
            <p className="eyebrow">Mercado laboral · Encuesta Nacional de Empleo (INE)</p>
            <h1 className="emp-title">Empleo por sector y trayectoria histórica</h1>
            <p className="emp-lede">
              Cuántas personas trabajan en cada actividad económica y cómo ha evolucionado el empleo entre 2013 y 2026.
            </p>
          </div>
          <div className="emp-header-actions">
            <button type="button" className="secondary-btn" onClick={handleDownloadCsv}>
              ↓ Descargar CSV
            </button>
          </div>
        </div>

        {/* Controles simples */}
        <div className="emp-controls">
          <div className="emp-controls-row">
            <label className="emp-field">
              <span>Territorio</span>
              <select
                aria-label="Territorio"
                value={regionCode}
                onChange={e => setRegionCode(e.target.value)}
              >
                {regionOptions.map(r => (
                  <option key={r.code} value={r.code}>{r.nombre}</option>
                ))}
              </select>
            </label>

            <label className="emp-field">
              <span>Año</span>
              <select
                aria-label="Año de empleo"
                value={selectedYear}
                onChange={e => setSelectedYear(Number(e.target.value))}
              >
                {aniosDisponibles.map(y => {
                  const rec = region.anuales.find(a => a.anio === y)
                  return (
                    <option key={y} value={y}>
                      {y}{rec?.en_curso ? ` (en curso · hasta ${rec.ultimo_trimestre})` : ''}
                    </option>
                  )
                })}
              </select>
            </label>
          </div>

          <div className="emp-quick-chips" role="group" aria-label="Atajos de territorio">
            {QUICK_REGIONS.map(q => (
              <button
                key={q.code}
                type="button"
                className={`emp-chip${regionCode === q.code ? ' is-active' : ''}`}
                onClick={() => setRegionCode(q.code)}
              >
                {q.label}
              </button>
            ))}
          </div>
        </div>
      </header>

      {/* Aviso suave cuando se mira 2026 en curso */}
      {yearRec.en_curso && (
        <p className="emp-notice" role="note">
          <strong>Año {yearRec.anio} en curso:</strong> promedio de los {yearRec.trimestres} trimestres móviles publicados hasta <strong>{yearRec.ultimo_trimestre} {yearRec.anio}</strong>.
        </p>
      )}

      {/* 3 Tarjetas KPI simples */}
      <section className="emp-kpi-grid" aria-label="Resumen laboral del territorio">
        <article className="panel emp-kpi-card is-accent has-info-corner">
          <InfoPopover label="Detalle de personas ocupadas" title="Personas ocupadas (ENE)">
            <p>Promedio anual de personas ocupadas residentes en {region.nombre} según la Encuesta Nacional de Empleo del INE.</p>
          </InfoPopover>
          <span className="emp-kpi-label">Personas ocupadas ({yearRec.anio})</span>
          <strong className="emp-kpi-value">{fmtPersonas(yearRec.ocupados_miles)}</strong>
          <p className="emp-kpi-meta">
            {varTotalAnualPct !== null ? `${fmtSignedPct(varTotalAnualPct)} vs ${yearRec.anio - 1}` : 'Primer año de la serie'}
            {' · '}
            {cambioDesde2013Personas >= 0 ? '+' : ''}{num0.format(cambioDesde2013Personas)} desde 2013
          </p>
        </article>

        <article className="panel emp-kpi-card has-info-corner">
          <InfoPopover label="Qué mide la tasa de desocupación" title="Tasa de desocupación">
            <p>Porcentaje de la fuerza de trabajo que busca empleo activamente y no está ocupada. Promedio anual oficial INE ENE.</p>
          </InfoPopover>
          <span className="emp-kpi-label">Tasa de desocupación ({yearRec.anio})</span>
          <strong className="emp-kpi-value">
            {yearRec.tasa_desocupacion_pct !== null ? `${num1.format(yearRec.tasa_desocupacion_pct)}%` : 'Sin dato'}
          </strong>
          <p className="emp-kpi-meta">
            {regionCode !== 'CL' && chileYearRec?.tasa_desocupacion_pct !== null
              ? `Promedio Chile: ${num1.format(chileYearRec.tasa_desocupacion_pct)}%`
              : 'Promedio nacional oficial INE'}
          </p>
        </article>

        <article className="panel emp-kpi-card has-info-corner">
          <InfoPopover label="Cómo se ordenan los sectores" title="Sectores económicos (INE)">
            <p>Clasificación de ramas de actividad económica del INE (CAENES / CIIU Rev. 4) ordenada según cantidad de personas ocupadas.</p>
          </InfoPopover>
          <span className="emp-kpi-label">Sector con más empleos</span>
          <strong className="emp-kpi-value is-text">{topSector ? topSector.nombre : 'Sin dato'}</strong>
          <p className="emp-kpi-meta">
            {topSector
              ? `${fmtPersonas(topSector.miles)} personas (${num1.format(topSector.pctTotal)}%)${secondSector ? ` · 2° ${secondSector.nombre}` : ''}`
              : 'Sin desglose disponible'}
          </p>
        </article>
      </section>

      {/* BLOQUE 1 · EMPLEO POR SECTOR */}
      <section className="panel emp-card has-info-corner" aria-labelledby="emp-sectores-titulo">
        <InfoPopover label="Nota sobre fiabilidad muestral por sector" title="Fiabilidad por tamaño de sector">
          <p>{data.meta.nota_fiabilidad}</p>
          <p>Al tocar cualquier sector, el gráfico de abajo muestra su trayectoria histórica completa (2013–2026).</p>
        </InfoPopover>

        <div className="emp-card-head">
          <div>
            <h2 id="emp-sectores-titulo">Empleo por sector · {region.nombre} ({yearRec.anio})</h2>
            <p className="subtle">
              Toca cualquier sector para ver cómo evolucionó desde 2013 en el gráfico de trayectoria.
            </p>
          </div>
          {sectoresRanking.length > 10 && (
            <button
              type="button"
              className="emp-toggle-btn"
              onClick={() => setShowAllSectors(v => !v)}
            >
              {showAllSectors ? 'Ver principales 10' : `Ver todos (${sectoresRanking.length})`}
            </button>
          )}
        </div>

        <ul className="emp-sector-list" aria-label={`Sectores laborales en ${region.nombre}`}>
          {sectoresVisibles.map((sec, idx) => {
            const widthPct = maxSectorMiles > 0 ? Math.max(2, (sec.miles / maxSectorMiles) * 100) : 0
            const isSelected = sec.id === activeSector.id && trayectoriaModo === 'sector'
            return (
              <li key={sec.id}>
                <button
                  type="button"
                  className={`emp-sector-row${isSelected ? ' is-selected' : ''}`}
                  aria-pressed={isSelected}
                  onClick={() => {
                    setSelectedSectorId(sec.id)
                    setTrayectoriaModo('sector')
                  }}
                >
                  <div className="emp-sector-top">
                    <span className="emp-sector-name">
                      <span className="emp-sector-rank">{idx + 1}.</span> {sec.nombre}
                    </span>
                    <span className="emp-sector-nums">
                      <strong>{fmtPersonas(sec.miles)}</strong>
                      <span className="emp-sector-pct">{num1.format(sec.pctTotal)}%</span>
                      {sec.varAnualPct !== null && (
                        <span className={`emp-delta ${sec.varAnualPct >= 0 ? 'is-up' : 'is-down'}`}>
                          {fmtSignedPct(sec.varAnualPct)}
                        </span>
                      )}
                    </span>
                  </div>
                  <span className="emp-bar-track" aria-hidden="true">
                    <span className="emp-bar-fill" style={{ width: `${widthPct}%` }} />
                  </span>
                </button>
              </li>
            )
          })}
        </ul>
      </section>

      {/* BLOQUE 2 · TRAYECTORIA HISTÓRICA (2013–2026) */}
      <section className="panel emp-card has-info-corner" aria-labelledby="emp-trayectoria-titulo">
        <InfoPopover label="Cómo se construye la trayectoria histórica" title="Trayectoria anual (2013–2026)">
          <p>{data.meta.nota_metodologica}</p>
          <p>La línea punteada en el tramo final corresponde a 2026 en curso (hasta {region.ultimo_trimestre}).</p>
        </InfoPopover>

        <div className="emp-card-head">
          <div>
            <h2 id="emp-trayectoria-titulo">
              Trayectoria histórica (2013–2026) ·{' '}
              {trayectoriaModo === 'sector'
                ? activeSector.nombre
                : trayectoriaModo === 'total'
                  ? 'Total de ocupados'
                  : 'Tasa de desocupación'}
            </h2>
            <p className="subtle">
              {trayectoriaModo === 'sector'
                ? `Personas ocupadas en ${activeSector.nombre} en ${region.nombre}.`
                : trayectoriaModo === 'total'
                  ? `Evolución anual del empleo total en ${region.nombre}.`
                  : `Porcentaje de desocupación en ${region.nombre} comparado con Chile (línea punteada).`}
            </p>
          </div>

          <div className="emp-mode-pills" role="group" aria-label="Serie histórica a graficar">
            <button
              type="button"
              className={trayectoriaModo === 'sector' ? 'is-active' : ''}
              onClick={() => setTrayectoriaModo('sector')}
            >
              Por sector
            </button>
            <button
              type="button"
              className={trayectoriaModo === 'total' ? 'is-active' : ''}
              onClick={() => setTrayectoriaModo('total')}
            >
              Total ocupados
            </button>
            <button
              type="button"
              className={trayectoriaModo === 'desocupacion' ? 'is-active' : ''}
              onClick={() => setTrayectoriaModo('desocupacion')}
            >
              Desocupación (%)
            </button>
          </div>
        </div>

        {trayectoriaModo === 'sector' && (
          <label className="emp-inline-select">
            <span>Sector graficado</span>
            <select
              aria-label="Sector graficado en trayectoria histórica"
              value={activeSector.id}
              onChange={e => setSelectedSectorId(e.target.value)}
            >
              {sectoresRanking.map(s => (
                <option key={s.id} value={s.id}>
                  {s.nombre} ({fmtPersonas(s.miles)} en {yearRec.anio})
                </option>
              ))}
            </select>
          </label>
        )}

        <div className="emp-svg-wrap">
          <svg
            viewBox={`0 0 ${svgW} ${svgH}`}
            className="emp-svg-chart"
            role="img"
            aria-label={`Trayectoria histórica 2013 a 2026 en ${region.nombre}`}
          >
            <defs>
              <linearGradient id="empAreaGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#0d6b58" stopOpacity="0.22" />
                <stop offset="100%" stopColor="#0d6b58" stopOpacity="0.02" />
              </linearGradient>
            </defs>

            {/* Grilla horizontal sutil */}
            {[0, 0.33, 0.66, 1].map(t => {
              const y = padT + plotH - t * plotH
              const v = chartBounds.min + t * (chartBounds.max - chartBounds.min)
              return (
                <g key={t}>
                  <line x1={padL} y1={y} x2={svgW - padR} y2={y} stroke="#e6eeea" strokeWidth={1} />
                  <text x={padL - 8} y={y + 4} textAnchor="end" fontSize="11" fill="#546d67">
                    {trayectoriaModo === 'desocupacion' ? `${num1.format(v)}%` : fmtPersonasCorto(v)}
                  </text>
                </g>
              )
            })}

            {/* Área y línea principal */}
            {areaPath && <path d={areaPath} fill="url(#empAreaGrad)" />}
            {refLinePath && (
              <path
                d={refLinePath}
                fill="none"
                stroke="#3a6b8c"
                strokeWidth={2}
                strokeDasharray="5 4"
              />
            )}
            {linePath && (
              <path
                d={linePath}
                fill="none"
                stroke="#0d6b58"
                strokeWidth={2.75}
                strokeLinejoin="round"
                strokeLinecap="round"
              />
            )}

            {/* Puntos interactivos por año */}
            {chartPoints.map((p, idx) => {
              const cx = getX(idx)
              const cy = getY(p.val)
              const isSel = p.anio === yearRec.anio
              const showLabel = isSel || idx === 0 || idx === chartPoints.length - 1
              return (
                <g
                  key={p.anio}
                  style={{ cursor: 'pointer' }}
                  onClick={() => setSelectedYear(p.anio)}
                >
                  {isSel && (
                    <line
                      x1={cx}
                      y1={padT}
                      x2={cx}
                      y2={padT + plotH}
                      stroke="#0d6b58"
                      strokeDasharray="3 3"
                      strokeOpacity={0.35}
                    />
                  )}
                  <circle
                    cx={cx}
                    cy={cy}
                    r={isSel ? 6 : 3.8}
                    fill={p.enCurso ? '#b45a18' : isSel ? '#0d6b58' : '#ffffff'}
                    stroke={p.enCurso ? '#b45a18' : '#0d6b58'}
                    strokeWidth={2.2}
                  />
                  {showLabel && (
                    <text
                      x={cx}
                      y={Math.max(14, cy - 11)}
                      textAnchor="middle"
                      fontSize="10.5"
                      fontWeight={isSel ? '800' : '600'}
                      fill="#102b26"
                    >
                      {trayectoriaModo === 'desocupacion' ? `${num1.format(p.val)}%` : fmtPersonasCorto(p.val)}
                    </text>
                  )}
                  <text
                    x={cx}
                    y={svgH - 16}
                    textAnchor="middle"
                    fontSize="11"
                    fontWeight={isSel ? '800' : '500'}
                    fill={isSel ? '#0d6b58' : '#536c66'}
                  >
                    {p.anio}{p.enCurso ? '*' : ''}
                  </text>
                </g>
              )
            })}
          </svg>
        </div>

        {/* Resumen limpio de la trayectoria */}
        <div className="emp-traj-summary">
          <div>
            <span>Inicio ({firstPoint.anio})</span>
            <strong>
              {trayectoriaModo === 'desocupacion'
                ? `${num1.format(firstPoint.val)}%`
                : `${fmtPersonas(firstPoint.val)} personas`}
            </strong>
          </div>
          <div>
            <span>Año elegido ({selectedPoint.anio}{selectedPoint.enCurso ? ' en curso' : ''})</span>
            <strong>
              {trayectoriaModo === 'desocupacion'
                ? `${num1.format(selectedPoint.val)}%`
                : `${fmtPersonas(selectedPoint.val)} personas`}
            </strong>
          </div>
          <div>
            <span>Cambio acumulado ({firstPoint.anio}–{selectedPoint.anio})</span>
            <strong>
              {deltaHistorico === null
                ? '—'
                : trayectoriaModo === 'desocupacion'
                  ? `${deltaHistorico > 0 ? '+' : ''}${num1.format(deltaHistorico)} pp`
                  : fmtSignedPct(deltaHistorico)}
            </strong>
          </div>
        </div>

        {/* Tabla histórica opcional y limpia */}
        <details className="emp-table-details">
          <summary>Ver tabla histórica anual (2013–2026)</summary>
          <div className="table-scroll">
            <table className="pol-table is-compact">
              <thead>
                <tr>
                  <th scope="col">Año</th>
                  <th scope="col" className="numeric">Total ocupados</th>
                  <th scope="col" className="numeric">{activeSector.nombre}</th>
                  <th scope="col" className="numeric">Peso del sector</th>
                  <th scope="col" className="numeric">Desocupación</th>
                </tr>
              </thead>
              <tbody>
                {[...region.anuales].reverse().map(rec => {
                  const secMiles = rec.sectores_miles[activeSector.id] ?? 0
                  const share = rec.ocupados_miles > 0 ? (secMiles / rec.ocupados_miles) * 100 : 0
                  return (
                    <tr key={rec.anio} className={rec.anio === yearRec.anio ? 'row-admin' : undefined}>
                      <th scope="row">
                        {rec.anio}{rec.en_curso ? ` (hasta ${rec.ultimo_trimestre})` : ''}
                      </th>
                      <td className="numeric">{fmtPersonas(rec.ocupados_miles)}</td>
                      <td className="numeric"><strong>{fmtPersonas(secMiles)}</strong></td>
                      <td className="numeric">{num1.format(share)}%</td>
                      <td className="numeric">
                        {rec.tasa_desocupacion_pct !== null ? `${num1.format(rec.tasa_desocupacion_pct)}%` : 'Sin dato'}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </details>

        <footer className="source-footer">
          <div className="source-footer-row">
            <span><strong>Fuente:</strong> Instituto Nacional de Estadísticas (INE) · Encuesta Nacional de Empleo</span>
            <span><strong>Último trimestre:</strong> {region.ultimo_trimestre} · Actualizado {data.meta.fecha_actualizacion}</span>
          </div>
        </footer>
      </section>
    </div>
  )
}
