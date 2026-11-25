import { useCallback, useEffect, useId, useMemo, useRef, useState } from 'react'
import type { ChangeEvent, FormEvent, KeyboardEvent } from 'react'
import { ApiServiceError } from './services/bcchService'
import {
  ANIOS_AYSEN,
  COMUNAS_AYSEN,
  fetchAysenEconomia,
  fetchAysenPresupuestos,
  fetchAysenProyectos,
  fetchAysenResumen,
  getComunaNombre,
} from './services/aysenPilotoService'
import type {
  AysenEconomiaResponse,
  AysenPresupuestosResponse,
  AysenProyectosResponse,
  AysenResumenResponse,
  FuenteOficial,
  InstitucionPresupuesto,
  ProyectoObra,
  SerieCrecimientoPunto,
  SerieParticipacionPunto,
} from './services/aysenPilotoService'
import { importSinimFile, normalizeSinimErrors, sinimTemplateUrl } from './services/sinimService'
import type { SinimErrorFila } from './services/sinimService'

type TabId = 'resumen' | 'economia' | 'presupuestos' | 'proyectos'
type EconomiaChartView = 'crecimiento' | 'participacion' | 'actividades'
type BilleteraFiltro = 'todas' | 'regional' | 'municipal' | 'nacional_en_region' | 'nacional'

const TABS: readonly { id: TabId; label: string }[] = [
  { id: 'resumen', label: 'Resumen' },
  { id: 'economia', label: 'Economía' },
  { id: 'presupuestos', label: 'Presupuestos' },
  { id: 'proyectos', label: 'Proyectos' },
] as const

const QUICK_DELTAS = [-15, -10, 0, 10, 15] as const

const SIM_MULTIPLIERS = [
  {
    value: 1.0,
    label: '1,0x · Directo contable (hipotético)',
    description: 'Supuesto hipotético de impacto contable directo sobre el Valor Agregado de Administración Pública (BCCh).',
  },
  {
    value: 0.8,
    label: '0,8x · Conservador (hipotético)',
    description: 'Supuesto hipotético conservador con filtración parcial de demanda fuera de la región.',
  },
  {
    value: 1.25,
    label: '1,25x · Arrastre moderado (hipotético)',
    description: 'Supuesto hipotético de encadenamiento local moderado sobre comercio y servicios.',
  },
  {
    value: 1.5,
    label: '1,5x · Encadenamiento ampliado (hipotético)',
    description: 'Escenario hipotético de sensibilidad superior con mayor circulación local de remuneraciones.',
  },
] as const

const num0 = new Intl.NumberFormat('es-CL', { maximumFractionDigits: 0 })
const num1 = new Intl.NumberFormat('es-CL', { minimumFractionDigits: 1, maximumFractionDigits: 1 })
const num2 = new Intl.NumberFormat('es-CL', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

function fmtMillions(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return 'Sin dato disponible'
  return `$ ${num0.format(value)} MM`
}

function fmtPct(value: number | null | undefined, signed = false, decimals: 1 | 2 = 1): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return 'Sin dato disponible'
  const sign = signed && value > 0 ? '+' : ''
  const formatter = decimals === 2 ? num2 : num1
  return `${sign}${formatter.format(value)}%`
}

function fmtPp(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return 'Sin dato disponible'
  const sign = value > 0 ? '+' : ''
  return `${sign}${num2.format(value)} pp`
}

function fmtDate(value?: string | null): string {
  if (!value) return 'Sin dato disponible'
  const trimmed = value.trim()
  if (!trimmed) return 'Sin dato disponible'
  if (trimmed.includes('T')) return trimmed.slice(0, 10)
  return trimmed
}

function extractSinimErrors(error: unknown): SinimErrorFila[] {
  if (!(error instanceof ApiServiceError) || !error.detalle) return []
  return normalizeSinimErrors(error.detalle.errores ?? error.detalle.errores_validacion)
}

function resolveFuenteUrl(fuente?: FuenteOficial | null): string | null {
  if (!fuente?.url) return null
  return /^https?:\/\//i.test(fuente.url) ? fuente.url : null
}

/* ============================================================
   COMPONENTES AUXILIARES REUTILIZABLES
============================================================ */

function LoadingCard({ label }: { label: string }) {
  return (
    <div className="aysen-loading" role="status" aria-live="polite">
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

function ErrorNotice({
  error,
  onRetry,
}: {
  error: Error
  onRetry: () => void
}) {
  return (
    <div className="aysen-error-box" role="alert">
      <p className="error">{error.message}</p>
      <button type="button" className="secondary-btn" onClick={onRetry}>
        Reintentar consulta
      </button>
    </div>
  )
}

function InProgressBanner({
  anio,
  mesCorteNombre,
  aviso,
}: {
  anio: number
  mesCorteNombre?: string | null
  aviso?: string | null
}) {
  return (
    <aside className="aysen-banner is-info" role="note" aria-label={`Año ${anio} en curso`}>
      <span className="aysen-banner-badge">Año en curso · {anio}</span>
      <p>
        {aviso ||
          `Datos acumulados${mesCorteNombre ? ` con corte a ${mesCorteNombre} de ${anio}` : ` del ejercicio ${anio} en ejecución`}. Las variaciones se comparan exclusivamente contra el mismo período del año anterior para no distorsionar la lectura.`}
      </p>
    </aside>
  )
}

function SourceLink({
  fuente,
  label = 'Fuente oficial',
}: {
  fuente?: FuenteOficial | null
  label?: string
}) {
  const url = resolveFuenteUrl(fuente)
  if (url) {
    return (
      <a
        className="aysen-source-link"
        href={url}
        target="_blank"
        rel="noopener noreferrer"
      >
        {label} <span aria-hidden="true">↗</span>
      </a>
    )
  }
  if (fuente?.nombre) {
    return <span className="aysen-source-text">Fuente: {fuente.nombre}</span>
  }
  return null
}

function SourceDetailsBlock({
  fuente,
  summaryLabel = 'Ver fuente',
  extraCodes,
}: {
  fuente?: FuenteOficial | null
  summaryLabel?: string
  extraCodes?: string[]
}) {
  const url = resolveFuenteUrl(fuente)
  const codes = Array.from(new Set([...(fuente?.codigos_series ?? []), ...(extraCodes ?? [])].filter(Boolean)))
  return (
    <details className="aysen-details">
      <summary>{summaryLabel}</summary>
      <div className="aysen-details-body">
        <dl className="aysen-meta-list">
          <div>
            <dt>Fuente</dt>
            <dd>{fuente?.nombre || 'Sin dato disponible'}</dd>
          </div>
          {fuente?.institucion && (
            <div>
              <dt>Institución</dt>
              <dd>{fuente.institucion}</dd>
            </div>
          )}
          <div>
            <dt>Período</dt>
            <dd>{fuente?.periodo || 'Sin dato disponible'}</dd>
          </div>
          <div>
            <dt>Unidad</dt>
            <dd>{fuente?.unidad || 'Sin dato disponible'}</dd>
          </div>
          <div>
            <dt>Cobertura</dt>
            <dd>{fuente?.cobertura || 'Sin dato disponible'}</dd>
          </div>
          {fuente?.actualizado_en && (
            <div>
              <dt>Actualizado</dt>
              <dd>{fmtDate(fuente.actualizado_en)}</dd>
            </div>
          )}
          {codes.length > 0 && (
            <div>
              <dt>Series oficiales</dt>
              <dd className="mono">{codes.join(' · ')}</dd>
            </div>
          )}
        </dl>
        {fuente?.nota && <p className="subtle">{fuente.nota}</p>}
        {url && (
          <a className="aysen-source-btn" href={url} target="_blank" rel="noopener noreferrer">
            Abrir registro oficial <span aria-hidden="true">↗</span>
          </a>
        )}
      </div>
    </details>
  )
}

/* ============================================================
   GRÁFICOS ACCESIBLES MOBILE-FIRST · PESTAÑA ECONOMÍA
============================================================ */

function buildSmoothSvgPath(pts: Array<{ x: number; y: number }>): string {
  if (pts.length === 0) return ''
  if (pts.length === 1) return `M${pts[0].x.toFixed(1)},${pts[0].y.toFixed(1)}`
  if (pts.length === 2) {
    return `M${pts[0].x.toFixed(1)},${pts[0].y.toFixed(1)} L${pts[1].x.toFixed(1)},${pts[1].y.toFixed(1)}`
  }
  let d = `M${pts[0].x.toFixed(1)},${pts[0].y.toFixed(1)}`
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[Math.max(0, i - 1)]
    const p1 = pts[i]
    const p2 = pts[i + 1]
    const p3 = pts[Math.min(pts.length - 1, i + 2)]
    const cp1x = p1.x + (p2.x - p0.x) / 6
    const cp1y = p1.y + (p2.y - p0.y) / 6
    const cp2x = p2.x - (p3.x - p1.x) / 6
    const cp2y = p2.y - (p3.y - p1.y) / 6
    d += ` C${cp1x.toFixed(1)},${cp1y.toFixed(1)} ${cp2x.toFixed(1)},${cp2y.toFixed(1)} ${p2.x.toFixed(1)},${p2.y.toFixed(1)}`
  }
  return d
}

function buildCleanGrowthTicks(low: number, high: number): number[] {
  const span = Math.max(2, high - low)
  const step = span <= 10 ? 2 : span <= 24 ? 5 : 10
  const start = Math.ceil(low / step) * step
  const ticks: number[] = [0]
  for (let v = start; v <= high; v += step) {
    if (Math.abs(v) < step * 0.65) continue
    ticks.push(v)
  }
  return Array.from(new Set(ticks)).sort((a, b) => b - a)
}

function CrecimientoChart({
  serie,
  selectedYear,
  onSelectYear,
}: {
  serie: SerieCrecimientoPunto[]
  selectedYear: number
  onSelectYear: (year: number) => void
}) {
  const [hoveredYear, setHoveredYear] = useState<number | null>(null)
  const validPoints = serie.filter(p => p.aysen_pct !== null || p.chile_pct !== null)
  if (validPoints.length === 0) {
    return <p className="aysen-empty">Sin dato disponible para la serie histórica de crecimiento real del PIB.</p>
  }

  const W = 680
  const H = 276
  const padL = 50
  const padR = 20
  const padT = 30
  const padB = 36
  const plotW = W - padL - padR
  const plotH = H - padT - padB

  const allVals = validPoints.flatMap(p => [p.aysen_pct, p.chile_pct]).filter((v): v is number => v !== null)
  const minVal = Math.min(0, ...allVals)
  const maxVal = Math.max(0, ...allVals)
  const span = Math.max(4, maxVal - minVal)
  const low = minVal - span * 0.16
  const high = maxVal + span * 0.18

  const yPos = (val: number) => padT + ((high - val) / (high - low)) * plotH
  const zeroY = yPos(0)
  const stepX = plotW / Math.max(1, validPoints.length)
  // Cápsulas esbeltas y sutiles en vez de bloques rectangulares toscos
  const barW = Math.min(12, Math.max(7, stepX * 0.24))

  const chileSegments: Array<Array<{ x: number; y: number }>> = []
  let currentSeg: Array<{ x: number; y: number }> = []
  validPoints.forEach((p, i) => {
    if (p.chile_pct === null) {
      if (currentSeg.length) chileSegments.push(currentSeg)
      currentSeg = []
      return
    }
    currentSeg.push({ x: padL + stepX * i + stepX / 2, y: yPos(p.chile_pct) })
  })
  if (currentSeg.length) chileSegments.push(currentSeg)

  const focusYear = hoveredYear ?? selectedYear
  const activePoint = validPoints.find(p => p.anio === focusYear) ?? validPoints.at(-1)!
  const ticks = buildCleanGrowthTicks(low, high)
  const gapPp =
    activePoint.aysen_pct !== null && activePoint.chile_pct !== null
      ? activePoint.aysen_pct - activePoint.chile_pct
      : null

  return (
    <div className="aysen-chart-wrap">
      <div className="aysen-chart-legend" aria-label="Leyenda del gráfico">
        <span><i className="aysen-swatch is-aysen-capsule" aria-hidden="true" /> Aysén (crecimiento real anual)</span>
        <span><i className="aysen-swatch is-aysen-neg" aria-hidden="true" /> Contracción Aysén</span>
        <span><i className="aysen-swatch is-chile-line" aria-hidden="true" /> Chile (referencia)</span>
      </div>
      <svg
        className="aysen-svg-chart"
        viewBox={`0 0 ${W} ${H}`}
        role="img"
        aria-label={`Crecimiento real anual del PIB de Aysén comparado con Chile entre ${validPoints[0].anio} y ${validPoints.at(-1)!.anio}.`}
        onMouseLeave={() => setHoveredYear(null)}
      >
        <defs>
          <linearGradient id="aysenPosGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#0f8c6c" stopOpacity="0.92" />
            <stop offset="100%" stopColor="#0f8c6c" stopOpacity="0.16" />
          </linearGradient>
          <linearGradient id="aysenPosGradActive" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#06664e" stopOpacity="1" />
            <stop offset="100%" stopColor="#0f8c6c" stopOpacity="0.28" />
          </linearGradient>
          <linearGradient id="aysenNegGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#d16052" stopOpacity="0.18" />
            <stop offset="100%" stopColor="#c44738" stopOpacity="0.9" />
          </linearGradient>
          <linearGradient id="aysenNegGradActive" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#c44738" stopOpacity="0.28" />
            <stop offset="100%" stopColor="#9e2a1f" stopOpacity="1" />
          </linearGradient>
          <linearGradient id="aysenFocusCol" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#0b7a5e" stopOpacity="0.09" />
            <stop offset="100%" stopColor="#0b7a5e" stopOpacity="0.02" />
          </linearGradient>
        </defs>

        {ticks.map((tick, idx) => {
          const y = yPos(tick)
          const isZero = Math.abs(tick) < 0.01
          return (
            <g key={idx}>
              <line
                x1={padL}
                x2={W - padR}
                y1={y}
                y2={y}
                stroke={isZero ? '#8da39b' : '#e8eeea'}
                strokeWidth={isZero ? 1.25 : 1}
                strokeDasharray={isZero ? undefined : '3 3'}
              />
              <text
                x={padL - 10}
                y={y + 4}
                textAnchor="end"
                fontSize="11"
                fontWeight={isZero ? '600' : '400'}
                fill={isZero ? '#344c45' : '#6b7e78'}
              >
                {tick > 0 ? `+${num1.format(tick)}%` : `${num1.format(tick)}%`}
              </text>
            </g>
          )
        })}

        {validPoints.map((pt, i) => {
          const cx = padL + stepX * i + stepX / 2
          const isActive = pt.anio === activePoint.anio
          const isPinned = pt.anio === selectedYear
          const val = pt.aysen_pct
          const valY = val !== null ? yPos(val) : zeroY
          const topY = val !== null ? Math.min(valY, zeroY) : zeroY
          const h = val !== null ? Math.max(3, Math.abs(valY - zeroY)) : 0
          const isNeg = val !== null && val < 0
          const fillId = isNeg
            ? (isActive ? 'url(#aysenNegGradActive)' : 'url(#aysenNegGrad)')
            : (isActive ? 'url(#aysenPosGradActive)' : 'url(#aysenPosGrad)')
          const capColor = isNeg
            ? (isActive ? '#9e2a1f' : '#c95648')
            : (isActive ? '#065a46' : '#0d8566')
          const showYearLabel = validPoints.length <= 9 || i % 2 === 0 || i === validPoints.length - 1 || isActive
          const labelY = isNeg ? Math.min(H - 42, valY + 16) : Math.max(padT - 8, valY - 10)

          return (
            <g
              key={pt.anio}
              className="aysen-svg-bar-group"
              onMouseEnter={() => setHoveredYear(pt.anio)}
              onClick={() => onSelectYear(pt.anio)}
            >
              {/* Zona interactiva amplia e invisible */}
              <rect x={cx - stepX / 2} y={padT - 8} width={stepX} height={plotH + 34} fill="transparent" />

              {isActive && (
                <rect
                  x={cx - Math.min(22, stepX * 0.42)}
                  y={padT - 4}
                  width={Math.min(44, stepX * 0.84)}
                  height={plotH + 8}
                  rx={10}
                  fill="url(#aysenFocusCol)"
                />
              )}

              {val !== null && (
                <>
                  <rect
                    x={cx - barW / 2}
                    y={topY}
                    width={barW}
                    height={h}
                    rx={barW / 2}
                    fill={fillId}
                  />
                  {/* Halo sutil + punta luminosa tipo editorial */}
                  {isActive && (
                    <circle
                      cx={cx}
                      cy={valY}
                      r={8}
                      fill={capColor}
                      fillOpacity={0.18}
                    />
                  )}
                  <circle
                    cx={cx}
                    cy={valY}
                    r={isActive ? 4.4 : 2.8}
                    fill={capColor}
                    stroke="#ffffff"
                    strokeWidth={1.5}
                  />
                  {isActive && (
                    <text
                      x={cx}
                      y={labelY}
                      textAnchor="middle"
                      fontSize="11"
                      fontWeight="700"
                      fill={capColor}
                    >
                      {fmtPct(val, true)}
                    </text>
                  )}
                </>
              )}

              {showYearLabel && (
                <g>
                  {isPinned && (
                    <rect
                      x={cx - 19}
                      y={H - 25}
                      width={38}
                      height={18}
                      rx={9}
                      fill="#e7f5ef"
                      stroke="#9acbb9"
                      strokeWidth={1}
                    />
                  )}
                  <text
                    x={cx}
                    y={H - 12}
                    textAnchor="middle"
                    fontSize="11"
                    fontWeight={isActive || isPinned ? '700' : '500'}
                    fill={isActive || isPinned ? '#07392f' : '#5e706b'}
                  >
                    {pt.anio}
                  </text>
                </g>
              )}
            </g>
          )
        })}

        {/* Curva suave de Chile como referencia elegante */}
        {chileSegments.map((seg, sIdx) => (
          <path
            key={`cl-seg-${sIdx}`}
            d={buildSmoothSvgPath(seg)}
            fill="none"
            stroke="#365f82"
            strokeWidth={2}
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeOpacity={0.85}
          />
        ))}

        {validPoints.map((pt, i) => {
          if (pt.chile_pct === null) return null
          const cx = padL + stepX * i + stepX / 2
          const cy = yPos(pt.chile_pct)
          const isActive = pt.anio === activePoint.anio
          return (
            <circle
              key={`cl-${pt.anio}`}
              cx={cx}
              cy={cy}
              r={isActive ? 4.4 : 2.6}
              fill={isActive ? '#2c5375' : '#ffffff'}
              stroke="#365f82"
              strokeWidth={isActive ? 1.8 : 1.7}
            />
          )
        })}
      </svg>

      <div className="aysen-chart-readout" aria-live="polite">
        <span className="aysen-readout-year">Año {activePoint.anio}</span>
        <span>Aysén: <strong className={activePoint.aysen_pct !== null && activePoint.aysen_pct < 0 ? 'is-neg' : 'is-pos'}>{fmtPct(activePoint.aysen_pct, true)}</strong></span>
        <span>Chile: <strong>{fmtPct(activePoint.chile_pct, true)}</strong></span>
        {gapPp !== null && (
          <span className="subtle">
            Brecha: <strong>{gapPp >= 0 ? `+${num1.format(gapPp)}` : num1.format(gapPp)} pp</strong>
          </span>
        )}
        {activePoint.estado && <span className="subtle">({activePoint.estado})</span>}
      </div>
    </div>
  )
}

function ParticipacionChart({
  serie,
  selectedYear,
  onSelectYear,
}: {
  serie: SerieParticipacionPunto[]
  selectedYear: number
  onSelectYear: (year: number) => void
}) {
  const [hoveredYear, setHoveredYear] = useState<number | null>(null)
  const validPoints = serie.filter(p => p.participacion_pct !== null)
  if (validPoints.length === 0) {
    return <p className="aysen-empty">Sin dato disponible para la participación histórica en el PIB nacional.</p>
  }

  const W = 680
  const H = 250
  const padL = 54
  const padR = 20
  const padT = 26
  const padB = 36
  const plotW = W - padL - padR
  const plotH = H - padT - padB

  const vals = validPoints.map(p => p.participacion_pct!)
  const minVal = Math.min(...vals)
  const maxVal = Math.max(...vals)
  const pad = Math.max(0.06, (maxVal - minVal) * 0.28)
  const low = Math.max(0, minVal - pad)
  const high = maxVal + pad

  const xPos = (idx: number) => padL + (validPoints.length > 1 ? (idx / (validPoints.length - 1)) * plotW : plotW / 2)
  const yPos = (val: number) => padT + ((high - val) / Math.max(0.0001, high - low)) * plotH

  const pts = validPoints.map((p, i) => ({ x: xPos(i), y: yPos(p.participacion_pct!) }))
  const linePath = buildSmoothSvgPath(pts)
  const areaPath = `${linePath} L${pts[pts.length - 1].x.toFixed(1)},${(padT + plotH).toFixed(1)} L${pts[0].x.toFixed(1)},${(padT + plotH).toFixed(1)} Z`

  const focusYear = hoveredYear ?? selectedYear
  const activePoint = validPoints.find(p => p.anio === focusYear) ?? validPoints.at(-1)!
  const ticks = [high, (high + low) / 2, low]

  return (
    <div className="aysen-chart-wrap">
      <svg
        className="aysen-svg-chart"
        viewBox={`0 0 ${W} ${H}`}
        role="img"
        aria-label={`Participación nominal de Aysén en el PIB nacional de Chile entre ${validPoints[0].anio} y ${validPoints.at(-1)!.anio}.`}
        onMouseLeave={() => setHoveredYear(null)}
      >
        <defs>
          <linearGradient id="aysenShareArea" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#0f8c6c" stopOpacity="0.24" />
            <stop offset="100%" stopColor="#0f8c6c" stopOpacity="0.01" />
          </linearGradient>
        </defs>

        {ticks.map((tick, idx) => {
          const y = yPos(tick)
          return (
            <g key={idx}>
              <line x1={padL} x2={W - padR} y1={y} y2={y} stroke="#e8eeea" strokeWidth={1} strokeDasharray="3 3" />
              <text x={padL - 10} y={y + 4} textAnchor="end" fontSize="11" fill="#6b7e78">
                {num2.format(tick)}%
              </text>
            </g>
          )
        })}

        <path d={areaPath} fill="url(#aysenShareArea)" />
        <path d={linePath} fill="none" stroke="#0b7a5e" strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round" />

        {validPoints.map((pt, i) => {
          const cx = pts[i].x
          const cy = pts[i].y
          const isActive = pt.anio === activePoint.anio
          const showLabel = validPoints.length <= 8 || i % 2 === 0 || i === validPoints.length - 1 || isActive
          return (
            <g
              key={pt.anio}
              className="aysen-svg-bar-group"
              onMouseEnter={() => setHoveredYear(pt.anio)}
              onClick={() => onSelectYear(pt.anio)}
            >
              {isActive && (
                <>
                  <line x1={cx} x2={cx} y1={padT} y2={padT + plotH} stroke="#0b7a5e44" strokeDasharray="3 3" />
                  <circle cx={cx} cy={cy} r={8.5} fill="#0b7a5e22" />
                  <text x={cx} y={Math.max(14, cy - 11)} textAnchor="middle" fontSize="11" fontWeight="700" fill="#07392f">
                    {num2.format(pt.participacion_pct!)}%
                  </text>
                </>
              )}
              <circle
                cx={cx}
                cy={cy}
                r={isActive ? 4.6 : 2.8}
                fill={isActive ? '#065a46' : '#0f8c6c'}
                stroke="#fff"
                strokeWidth={1.6}
              />
              {showLabel && (
                <text
                  x={cx}
                  y={H - 12}
                  textAnchor="middle"
                  fontSize="11"
                  fontWeight={isActive ? '700' : '500'}
                  fill={isActive ? '#07392f' : '#5e706b'}
                >
                  {pt.anio}
                </text>
              )}
            </g>
          )
        })}
      </svg>

      <div className="aysen-chart-readout" aria-live="polite">
        <span className="aysen-readout-year">Año {activePoint.anio}</span>
        <span>Participación en Chile: <strong>{fmtPct(activePoint.participacion_pct, false, 2)}</strong></span>
        {activePoint.pib_aysen_millones !== null && (
          <span>PIB Aysén: <strong>{fmtMillions(activePoint.pib_aysen_millones)}</strong></span>
        )}
      </div>
    </div>
  )
}

/* ============================================================
   TARJETA DE INSTITUCIÓN · PESTAÑA PRESUPUESTOS
============================================================ */

function InstitucionPresupuestoCard({ inst }: { inst: InstitucionPresupuesto }) {
  const radioPhrase =
    inst.frase_radial ||
    (inst.gasto_corriente_pct !== null
      ? `De cada $100 ejecutados por ${inst.nombre}, $${num1.format(inst.gasto_corriente_pct)} correspondieron a gasto corriente${inst.inversion_pct !== null ? ` y $${num1.format(inst.inversion_pct)} a inversión` : ''}.`
      : null)

  const currentPctBar = inst.gasto_corriente_pct !== null ? Math.min(100, Math.max(0, inst.gasto_corriente_pct)) : 0
  const investPctBar = inst.inversion_pct !== null ? Math.min(100 - currentPctBar, Math.max(0, inst.inversion_pct)) : 0
  const hasBar = currentPctBar > 0 || investPctBar > 0

  return (
    <article className={`aysen-card aysen-inst-card${inst.destacado_piloto ? ' is-pilot' : ''}`}>
      <div className="aysen-card-top">
        <span className={`aysen-territory-tag is-${inst.rol_billetera}`}>
          {inst.territorio_etiqueta}
        </span>
        {inst.avance_ejecucion_pct !== null && (
          <span className="aysen-pill-muted">Avance {fmtPct(inst.avance_ejecucion_pct)}</span>
        )}
      </div>

      <h3 className="aysen-inst-title">{inst.nombre}</h3>

      {/* 3 cifras presupuestarias */}
      <dl className="aysen-budget-trio">
        <div>
          <dt>Presupuesto inicial</dt>
          <dd className={inst.presupuesto_inicial_millones === null ? 'is-missing' : ''}>
            {fmtMillions(inst.presupuesto_inicial_millones)}
          </dd>
        </div>
        <div>
          <dt>Presupuesto vigente</dt>
          <dd className={inst.presupuesto_vigente_millones === null ? 'is-missing' : ''}>
            {fmtMillions(inst.presupuesto_vigente_millones)}
          </dd>
        </div>
        <div className="is-primary">
          <dt>Gasto ejecutado</dt>
          <dd className={inst.gasto_ejecutado_millones === null ? 'is-missing' : ''}>
            {fmtMillions(inst.gasto_ejecutado_millones)}
          </dd>
        </div>
      </dl>

      {/* Corriente vs Inversión */}
      <div className="aysen-split-box">
        <div className="aysen-split-grid">
          <div>
            <span className="aysen-split-label">
              <i className="aysen-swatch is-current" aria-hidden="true" /> Gasto corriente
            </span>
            <strong className="aysen-split-val">{fmtMillions(inst.gasto_corriente_millones)}</strong>
            <span className="aysen-split-pct">{fmtPct(inst.gasto_corriente_pct)}</span>
          </div>
          <div>
            <span className="aysen-split-label">
              <i className="aysen-swatch is-invest" aria-hidden="true" /> Inversión
            </span>
            <strong className="aysen-split-val">{fmtMillions(inst.inversion_millones)}</strong>
            <span className="aysen-split-pct">{fmtPct(inst.inversion_pct)}</span>
          </div>
        </div>

        {hasBar && (
          <div className="aysen-split-bar" aria-hidden="true">
            {currentPctBar > 0 && <span className="is-current" style={{ width: `${currentPctBar}%` }} />}
            {investPctBar > 0 && <span className="is-invest" style={{ width: `${investPctBar}%` }} />}
          </div>
        )}

        <p className="aysen-base-note">
          <strong>Base de cálculo:</strong> {inst.base_calculo || 'Porcentaje sobre gasto ejecutado total informado por la fuente.'}
        </p>
      </div>

      {/* Frase radial destacada */}
      {radioPhrase ? (
        <blockquote className="aysen-radio-quote">
          «{radioPhrase}»
        </blockquote>
      ) : (
        inst.sin_dato_motivo && <p className="subtle">{inst.sin_dato_motivo}</p>
      )}

      {/* ¿Cuánto cuesta administrar esta institución? */}
      <div className="aysen-admin-cost">
        <h4>¿Cuánto cuesta administrar esta institución?</h4>
        {inst.costo_administracion.disponible ? (
          <>
            <p className="aysen-admin-cost-num">
              <strong>{fmtMillions(inst.costo_administracion.monto_millones)}</strong>
              {inst.costo_administracion.porcentaje_pct !== null && (
                <span> ({fmtPct(inst.costo_administracion.porcentaje_pct)})</span>
              )}
            </p>
            {inst.costo_administracion.respuesta && <p>{inst.costo_administracion.respuesta}</p>}
          </>
        ) : (
          <p>
            {inst.costo_administracion.brecha_explicacion ||
              inst.costo_administracion.respuesta ||
              'El registro presupuestario oficial no separa el funcionamiento administrativo interno de la prestación directa de servicios.'}
          </p>
        )}
      </div>

      {/* Desplegable Ver desglose */}
      {(inst.desglose.length > 0 || inst.personal_sinim.length > 0) && (
        <details className="aysen-details">
          <summary>Ver desglose</summary>
          <div className="aysen-details-body">
            {inst.desglose.length > 0 && (
              <ul className="aysen-breakdown-list">
                {inst.desglose.map((item, idx) => (
                  <li key={`${item.categoria}-${idx}`}>
                    <div>
                      <strong>{item.categoria}</strong>
                      {item.detalle && <span className="subtle"> · {item.detalle}</span>}
                    </div>
                    <div className="aysen-breakdown-nums">
                      <span>{fmtMillions(item.monto_millones)}</span>
                      {item.porcentaje_pct !== null && <small>{' '}({fmtPct(item.porcentaje_pct)})</small>}
                    </div>
                  </li>
                ))}
              </ul>
            )}

            {inst.personal_sinim.length > 0 && (
              <div className="aysen-sub-breakdown">
                <h5>Detalle de personal (SINIM: Planta · Contrata · Honorarios · Programas)</h5>
                <ul className="aysen-breakdown-list is-compact">
                  {inst.personal_sinim.map((item, idx) => (
                    <li key={`${item.categoria}-${idx}`}>
                      <span>{item.categoria}</span>
                      <div className="aysen-breakdown-nums">
                        <span>{fmtMillions(item.monto_millones)}</span>
                        {item.porcentaje_pct !== null && <small>{' '}({fmtPct(item.porcentaje_pct)})</small>}
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        </details>
      )}

      {/* Desplegable Ver fuente */}
      <SourceDetailsBlock fuente={inst.fuente} summaryLabel="Ver fuente" />
    </article>
  )
}

/* ============================================================
   FICHA DE PROYECTO · PESTAÑA PROYECTOS
============================================================ */

function ProyectoFicha({
  proyecto,
  anio,
  onBack,
}: {
  proyecto: ProyectoObra
  anio: number
  onBack: () => void
}) {
  const radioOneLiner =
    proyecto.frase_radial ||
    `Obra a cargo de ${proyecto.institucion}${proyecto.administracion_origen ? ` (contratada en la gestión ${proyecto.administracion_origen})` : ''}: durante ${anio} registró pagos por ${fmtMillions(proyecto.pagado_anio_millones)}.`

  return (
    <article className="aysen-card aysen-project-dossier" aria-labelledby="ficha-proyecto-titulo">
      <div className="aysen-dossier-nav">
        <button type="button" className="secondary-btn" onClick={onBack}>
          ← Volver a la lista
        </button>
        <span className={`aysen-arrastre-badge is-${proyecto.clasificacion_arrastre}`}>
          {proyecto.etiqueta_arrastre}
        </span>
      </div>

      <div className="aysen-dossier-head">
        <div className="aysen-dossier-meta">
          {proyecto.comuna && <span>{proyecto.comuna}</span>}
          <span>{proyecto.institucion}</span>
          {proyecto.codigo_bip && <span className="mono">BIP {proyecto.codigo_bip}</span>}
          {proyecto.codigo_contrato && <span className="mono">Contrato {proyecto.codigo_contrato}</span>}
        </div>
        <h3 id="ficha-proyecto-titulo">{proyecto.nombre}</h3>
      </div>

      <blockquote className="aysen-radio-quote">
        «{radioOneLiner}»
      </blockquote>

      {/* 3 cifras monetarias claramente diferenciadas */}
      <section aria-label="Cifras financieras de la obra">
        <dl className="aysen-project-money">
          <div className="is-total">
            <dt>Costo total del contrato / proyecto</dt>
            <dd className={proyecto.costo_total_millones === null ? 'is-missing' : ''}>
              {fmtMillions(proyecto.costo_total_millones)}
            </dd>
          </div>
          <div>
            <dt>Compromiso del año ({anio})</dt>
            <dd className={proyecto.compromiso_anio_millones === null ? 'is-missing' : ''}>
              {fmtMillions(proyecto.compromiso_anio_millones)}
            </dd>
          </div>
          <div className="is-paid">
            <dt>Pagado en el año ({anio})</dt>
            <dd className={proyecto.pagado_anio_millones === null ? 'is-missing' : ''}>
              {fmtMillions(proyecto.pagado_anio_millones)}
            </dd>
          </div>
        </dl>

        <dl className="aysen-project-money-sub">
          <div>
            <dt>Pagado en años anteriores</dt>
            <dd>{fmtMillions(proyecto.pagado_anios_anteriores_millones)}</dd>
          </div>
          <div>
            <dt>Saldo por pagar</dt>
            <dd>{fmtMillions(proyecto.saldo_por_pagar_millones)}</dd>
          </div>
        </dl>
      </section>

      {/* Línea de tiempo de 4 hitos */}
      <section className="aysen-timeline-section" aria-label="Línea de tiempo de hitos oficiales">
        <h4>Línea de tiempo de la obra (4 hitos)</h4>
        <ol className="aysen-timeline">
          {proyecto.hitos.map(hito => {
            const docUrl = hito.documento_url && /^https?:\/\//i.test(hito.documento_url) ? hito.documento_url : null
            return (
              <li key={`${hito.orden}-${hito.etapa}`} className="aysen-timeline-item">
                <span className="aysen-timeline-step" aria-hidden="true">{hito.orden}</span>
                <div className="aysen-timeline-body">
                  <div className="aysen-timeline-top">
                    <strong>{hito.etapa}</strong>
                    <span className={`aysen-timeline-date${!hito.fecha ? ' is-missing' : ''}`}>
                      {fmtDate(hito.fecha)}
                    </span>
                  </div>
                  <dl className="aysen-timeline-meta">
                    <div>
                      <dt>Institución responsable</dt>
                      <dd>{hito.institucion_responsable || 'Sin dato disponible'}</dd>
                    </div>
                    <div>
                      <dt>Administración vigente</dt>
                      <dd>{hito.administracion_vigente || 'Sin dato disponible'}</dd>
                    </div>
                  </dl>
                  {hito.nota && <p className="subtle">{hito.nota}</p>}
                  {docUrl ? (
                    <a
                      className="aysen-source-link"
                      href={docUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      {hito.documento_etiqueta || 'Ver documento de respaldo'} <span aria-hidden="true">↗</span>
                    </a>
                  ) : (
                    <span className="subtle">Documento oficial: Sin dato disponible</span>
                  )}
                </div>
              </li>
            )
          })}
        </ol>
      </section>

      <SourceDetailsBlock fuente={proyecto.fuente} summaryLabel="Ver fuente de la ficha" />
    </article>
  )
}

/* ============================================================
   VISTA PRINCIPAL · OBSERVATORIO DE AYSÉN (4 PESTAÑAS)
============================================================ */

export function PoliticalView() {
  const yearSelectId = useId()
  const comunaSelectId = useId()
  const searchInputId = useId()
  const instSelectId = useId()
  const sliderId = useId()
  const numInputId = useId()
  const multiplierId = useId()
  const sinimInputId = useId()

  // Estado compartido que se conserva al cambiar de pestaña
  const [activeTab, setActiveTab] = useState<TabId>('resumen')
  const [anio, setAnio] = useState<number>(2025)
  const [comunaPresupuesto, setComunaPresupuesto] = useState<string>('11201')
  const [comunaProyectos, setComunaProyectos] = useState<string>('')
  const [comunaActivaEnCabecera, setComunaActivaEnCabecera] = useState<string>('11201')
  const [refreshTick, setRefreshTick] = useState<number>(0)

  // Sub-estado pestaña Economía
  const [ecoView, setEcoView] = useState<EconomiaChartView>('crecimiento')
  const [deltaPct, setDeltaPct] = useState<number>(0)
  const [multiplier, setMultiplier] = useState<number>(1.0)

  // Sub-estado pestaña Presupuestos
  const [billeteraFiltro, setBilleteraFiltro] = useState<BilleteraFiltro>('todas')
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [sinimUpload, setSinimUpload] = useState<{
    submitting: boolean
    successMessage: string
    errorMessage: string
    rowErrors: SinimErrorFila[]
  }>({
    submitting: false,
    successMessage: '',
    errorMessage: '',
    rowErrors: [],
  })

  // Sub-estado pestaña Proyectos
  const [institucionFiltro, setInstitucionFiltro] = useState<string>('')
  const [searchInput, setSearchInput] = useState<string>('')
  const [appliedSearch, setAppliedSearch] = useState<string>('')
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null)

  // Estados de carga de cada endpoint
  const [resumenState, setResumenState] = useState<{
    loading: boolean
    data: AysenResumenResponse | null
    error: Error | null
  }>({ loading: false, data: null, error: null })

  const [economiaState, setEconomiaState] = useState<{
    loading: boolean
    data: AysenEconomiaResponse | null
    error: Error | null
  }>({ loading: false, data: null, error: null })

  const [presupuestosState, setPresupuestosState] = useState<{
    loading: boolean
    data: AysenPresupuestosResponse | null
    error: Error | null
  }>({ loading: false, data: null, error: null })

  const [proyectosState, setProyectosState] = useState<{
    loading: boolean
    data: AysenProyectosResponse | null
    error: Error | null
  }>({ loading: false, data: null, error: null })

  const tabRefs = useRef<Record<TabId, HTMLButtonElement | null>>({
    resumen: null,
    economia: null,
    presupuestos: null,
    proyectos: null,
  })

  // Sincronización amable de comuna entre Presupuestos y Proyectos
  function handleComunaChange(value: string) {
    if (activeTab === 'proyectos') {
      setComunaProyectos(value)
      setSelectedProjectId(null)
      if (value) {
        setComunaPresupuesto(value)
        setComunaActivaEnCabecera(value)
      } else {
        setComunaActivaEnCabecera('')
      }
      return
    }
    const clean = value || '11201'
    setComunaPresupuesto(clean)
    setComunaProyectos(clean)
    setComunaActivaEnCabecera(clean)
    setSelectedProjectId(null)
  }

  function switchTab(next: TabId) {
    setActiveTab(next)
    if (next !== 'proyectos') {
      setSelectedProjectId(null)
    }
  }

  function handleTabKeyDown(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    let nextIndex: number | null = null
    if (event.key === 'ArrowRight') nextIndex = (index + 1) % TABS.length
    else if (event.key === 'ArrowLeft') nextIndex = (index - 1 + TABS.length) % TABS.length
    else if (event.key === 'Home') nextIndex = 0
    else if (event.key === 'End') nextIndex = TABS.length - 1
    if (nextIndex === null) return
    event.preventDefault()
    const nextTab = TABS[nextIndex].id
    switchTab(nextTab)
    tabRefs.current[nextTab]?.focus()
  }

  // Carga pestaña 1: Resumen
  useEffect(() => {
    if (activeTab !== 'resumen') return
    const controller = new AbortController()
    setResumenState(prev => ({ ...prev, loading: true, error: null }))
    fetchAysenResumen(anio, comunaActivaEnCabecera || undefined, controller.signal)
      .then(data => {
        if (!controller.signal.aborted) setResumenState({ loading: false, data, error: null })
      })
      .catch(err => {
        if (controller.signal.aborted || (err instanceof DOMException && err.name === 'AbortError')) return
        setResumenState({
          loading: false,
          data: null,
          error: err instanceof Error ? err : new Error('No se pudo cargar el resumen de Aysén.'),
        })
      })
    return () => controller.abort()
  }, [activeTab, anio, comunaActivaEnCabecera, refreshTick])

  // Carga pestaña 2: Economía
  useEffect(() => {
    if (activeTab !== 'economia') return
    const controller = new AbortController()
    setEconomiaState(prev => ({ ...prev, loading: true, error: null }))
    fetchAysenEconomia(anio, controller.signal)
      .then(data => {
        if (!controller.signal.aborted) setEconomiaState({ loading: false, data, error: null })
      })
      .catch(err => {
        if (controller.signal.aborted || (err instanceof DOMException && err.name === 'AbortError')) return
        setEconomiaState({
          loading: false,
          data: null,
          error: err instanceof Error ? err : new Error('No se pudo cargar la información económica de Aysén.'),
        })
      })
    return () => controller.abort()
  }, [activeTab, anio, refreshTick])

  // Carga pestaña 3: Presupuestos
  useEffect(() => {
    if (activeTab !== 'presupuestos') return
    const controller = new AbortController()
    setPresupuestosState(prev => ({ ...prev, loading: true, error: null }))
    fetchAysenPresupuestos(anio, comunaPresupuesto, controller.signal)
      .then(data => {
        if (!controller.signal.aborted) setPresupuestosState({ loading: false, data, error: null })
      })
      .catch(err => {
        if (controller.signal.aborted || (err instanceof DOMException && err.name === 'AbortError')) return
        setPresupuestosState({
          loading: false,
          data: null,
          error: err instanceof Error ? err : new Error('No se pudieron cargar los presupuestos de Aysén.'),
        })
      })
    return () => controller.abort()
  }, [activeTab, anio, comunaPresupuesto, refreshTick])

  // Carga pestaña 4: Proyectos
  useEffect(() => {
    if (activeTab !== 'proyectos') return
    const controller = new AbortController()
    setProyectosState(prev => ({ ...prev, loading: true, error: null }))
    fetchAysenProyectos(
      {
        anio,
        comuna: comunaProyectos || undefined,
        institucion: institucionFiltro || undefined,
        q: appliedSearch || undefined,
      },
      controller.signal,
    )
      .then(data => {
        if (!controller.signal.aborted) setProyectosState({ loading: false, data, error: null })
      })
      .catch(err => {
        if (controller.signal.aborted || (err instanceof DOMException && err.name === 'AbortError')) return
        setProyectosState({
          loading: false,
          data: null,
          error: err instanceof Error ? err : new Error('No se pudieron cargar los proyectos de Aysén.'),
        })
      })
    return () => controller.abort()
  }, [activeTab, anio, comunaProyectos, institucionFiltro, appliedSearch, refreshTick])

  // Simulador hipotético (dentro de <details> en Economía)
  const simAdminBase = economiaState.data?.admin_publica_millones ?? null
  const simPibBase = economiaState.data?.pib_nominal_millones ?? null
  const simulation = useMemo(() => {
    if (simAdminBase === null || simPibBase === null || simPibBase <= 0) return null
    const deltaAdmin = simAdminBase * (deltaPct / 100)
    const deltaPib = deltaAdmin * multiplier
    const pibSimulated = simPibBase + deltaPib
    const impactPibPp = (deltaPib / simPibBase) * 100
    return { deltaAdmin, deltaPib, pibSimulated, impactPibPp }
  }, [simAdminBase, simPibBase, deltaPct, multiplier])

  const selectedMultiplierInfo = SIM_MULTIPLIERS.find(m => m.value === multiplier) ?? SIM_MULTIPLIERS[0]

  // Actividades ordenadas para Economía
  const actividadesOrdenadas = useMemo(() => {
    if (!economiaState.data?.actividades) return []
    return [...economiaState.data.actividades].sort((a, b) => {
      const av = a.participacion_pct ?? a.valor_millones ?? -Infinity
      const bv = b.participacion_pct ?? b.valor_millones ?? -Infinity
      return bv - av
    })
  }, [economiaState.data])

  const maxActivityPct = useMemo(() => {
    const values = actividadesOrdenadas
      .map(a => a.participacion_pct ?? 0)
      .filter(v => Number.isFinite(v) && v > 0)
    return values.length > 0 ? Math.max(...values) : 1
  }, [actividadesOrdenadas])

  // Instituciones ordenadas y filtradas en Presupuestos
  const institucionesFiltradas = useMemo(() => {
    const list = presupuestosState.data?.instituciones ?? []
    const order: Record<InstitucionPresupuesto['rol_billetera'], number> = {
      regional: 1,
      municipal: 2,
      nacional_en_region: 3,
      nacional: 4,
    }
    const sorted = [...list].sort((a, b) => {
      const pa = a.destacado_piloto ? 0 : 1
      const pb = b.destacado_piloto ? 0 : 1
      if (pa !== pb) return pa - pb
      return order[a.rol_billetera] - order[b.rol_billetera]
    })
    if (billeteraFiltro === 'todas') return sorted
    return sorted.filter(item => item.rol_billetera === billeteraFiltro)
  }, [presupuestosState.data, billeteraFiltro])

  // Proyecto seleccionado en Ficha
  const selectedProject = useMemo(() => {
    if (!selectedProjectId || !proyectosState.data) return null
    return (
      proyectosState.data.proyectos.find(p => p.id === selectedProjectId) ??
      proyectosState.data.proyectos_insuficientes.find(p => p.id === selectedProjectId) ??
      null
    )
  }, [selectedProjectId, proyectosState.data])

  // Handlers SINIM discreto en Presupuestos
  function handleSinimFileChange(_event: ChangeEvent<HTMLInputElement>) {
    setSinimUpload(prev => ({ ...prev, successMessage: '', errorMessage: '', rowErrors: [] }))
  }

  async function handleSinimImport(event: FormEvent) {
    event.preventDefault()
    const file = fileInputRef.current?.files?.[0]
    if (!file) {
      setSinimUpload({
        submitting: false,
        successMessage: '',
        errorMessage: 'Selecciona un archivo .csv o .json de SINIM antes de importar.',
        rowErrors: [],
      })
      return
    }
    setSinimUpload({ submitting: true, successMessage: '', errorMessage: '', rowErrors: [] })
    try {
      const content = await file.text()
      if (!content.trim()) {
        setSinimUpload({
          submitting: false,
          successMessage: '',
          errorMessage: 'El archivo seleccionado está vacío.',
          rowErrors: [],
        })
        return
      }
      const res = await importSinimFile(file.name, content)
      setSinimUpload({
        submitting: false,
        successMessage:
          res.mensaje ||
          `Archivo «${file.name}» importado (${res.comunas_cargadas}/${res.total_comunas_esperadas} comunas de Aysén).`,
        errorMessage: '',
        rowErrors: res.errores_validacion ?? [],
      })
      setRefreshTick(t => t + 1)
    } catch (err) {
      setSinimUpload({
        submitting: false,
        successMessage: '',
        errorMessage: err instanceof Error ? err.message : 'No se pudo validar o importar el archivo SINIM.',
        rowErrors: extractSinimErrors(err),
      })
    }
  }

  function handleNumericDeltaChange(raw: string) {
    const parsed = Number(raw)
    if (!Number.isFinite(parsed)) {
      setDeltaPct(0)
      return
    }
    setDeltaPct(Math.max(-30, Math.min(30, Math.round(parsed * 2) / 2)))
  }

  function handleProjectSearchSubmit(event: FormEvent) {
    event.preventDefault()
    setSelectedProjectId(null)
    setAppliedSearch(searchInput.trim())
  }

  const triggerRetry = useCallback(() => setRefreshTick(t => t + 1), [])

  const showComunaSelector = activeTab === 'presupuestos' || activeTab === 'proyectos'
  const comunaSelectorValue = activeTab === 'proyectos' ? comunaProyectos : comunaPresupuesto
  const showRegionalPibHint =
    (activeTab === 'resumen' || activeTab === 'economia') && Boolean(comunaActivaEnCabecera)

  return (
    <div className="aysen-page">
      {/* ============================================================
          CABECERA COMPACTA SUPERIOR + CONTROLES COMPARTIDOS + 4 TABS
      ============================================================ */}
      <header className="aysen-header">
        <div className="aysen-header-row">
          <div className="aysen-header-top">
            <p className="eyebrow">Región de Aysén · Código 11</p>
            <h1 className="aysen-title">Observatorio de Aysén</h1>
            <p className="aysen-subtitle">
              Economía, presupuestos públicos y obras con respaldo oficial verificable.
            </p>
          </div>

          {/* Barra de controles compartidos */}
          <div className="aysen-controls" aria-label="Filtros globales del Observatorio de Aysén">
            <label className="aysen-control-field" htmlFor={yearSelectId}>
              <span>Año</span>
              <select
                id={yearSelectId}
                value={anio}
                onChange={event => {
                  setAnio(Number(event.target.value))
                  setSelectedProjectId(null)
                }}
              >
                {ANIOS_AYSEN.map(y => (
                  <option key={y} value={y}>
                    {y}{y >= 2026 ? ' (en curso)' : ''}
                  </option>
                ))}
              </select>
            </label>

            {showComunaSelector && (
              <label className="aysen-control-field" htmlFor={comunaSelectId}>
                <span>Comuna</span>
                <select
                  id={comunaSelectId}
                  value={comunaSelectorValue}
                  onChange={event => handleComunaChange(event.target.value)}
                >
                  {activeTab === 'proyectos' && <option value="">Todas las comunas (10)</option>}
                  {COMUNAS_AYSEN.map(c => (
                    <option key={c.cut} value={c.cut}>
                      {c.nombre} ({c.cut})
                    </option>
                  ))}
                </select>
              </label>
            )}
          </div>
        </div>

        {/* Navegación exclusiva de 4 pestañas */}
        <div className="aysen-tablist" role="tablist" aria-label="Secciones del Observatorio de Aysén">
          {TABS.map((tab, idx) => {
            const isSelected = activeTab === tab.id
            return (
              <button
                key={tab.id}
                ref={el => { tabRefs.current[tab.id] = el }}
                id={`tab-${tab.id}`}
                type="button"
                role="tab"
                aria-selected={isSelected}
                aria-controls={`panel-${tab.id}`}
                tabIndex={isSelected ? 0 : -1}
                className="aysen-tab"
                onClick={() => switchTab(tab.id)}
                onKeyDown={event => handleTabKeyDown(event, idx)}
              >
                {tab.label}
              </button>
            )
          })}
        </div>
      </header>

      {/* ============================================================
          PANEL ACTIVO ÚNICO (STRICT: SOLO RENDERIZA 1 TABPANEL)
      ============================================================ */}

      {activeTab === 'resumen' && (
        <section
          id="panel-resumen"
          role="tabpanel"
          aria-labelledby="tab-resumen"
          className="aysen-panel"
        >
          <div className="aysen-question-head">
            <h2>¿Qué pasó en Aysén durante {anio}?</h2>
            <p className="subtle">
              Tres respuestas directas con datos oficiales verificables para entender actividad económica, inversión y compromisos heredados.
            </p>
          </div>

          {showRegionalPibHint && (
            <p className="aysen-hint-bar" role="note">
              Comuna seleccionada para presupuestos: <strong>{getComunaNombre(comunaActivaEnCabecera)}</strong>. El PIB se mide únicamente a escala regional (Región de Aysén).
            </p>
          )}

          {resumenState.loading ? (
            <LoadingCard label={`Consultando el resumen oficial de Aysén para ${anio}…`} />
          ) : resumenState.error ? (
            <ErrorNotice error={resumenState.error} onRetry={triggerRetry} />
          ) : !resumenState.data ? (
            <p className="aysen-empty">Sin dato disponible para {anio}.</p>
          ) : (
            <>
              {resumenState.data.en_curso && (
                <InProgressBanner
                  anio={resumenState.data.anio}
                  mesCorteNombre={resumenState.data.mes_corte_nombre}
                  aviso={resumenState.data.aviso_anio_en_curso}
                />
              )}

              <div className="aysen-summary-grid">
                {/* Tarjeta 1: Evolución económica */}
                <article className="aysen-card aysen-summary-card">
                  <div className="aysen-card-top">
                    <span className="aysen-card-kicker">1 · Evolución económica</span>
                    <span className="aysen-territory-tag is-regional">Región de Aysén</span>
                  </div>

                  <p className={`aysen-big-figure${!resumenState.data.evolucion_economica.disponible ? ' is-missing' : ''}`}>
                    {resumenState.data.evolucion_economica.crecimiento_real_pct !== null
                      ? fmtPct(resumenState.data.evolucion_economica.crecimiento_real_pct, true)
                      : 'Sin dato disponible'}
                  </p>
                  <p className="aysen-figure-caption">
                    Crecimiento real del PIB regional ({anio})
                    {resumenState.data.evolucion_economica.crecimiento_chile_pct !== null && (
                      <> · Chile: <strong>{fmtPct(resumenState.data.evolucion_economica.crecimiento_chile_pct, true)}</strong></>
                    )}
                  </p>

                  {resumenState.data.evolucion_economica.frase_radial ? (
                    <blockquote className="aysen-radio-quote">
                      «{resumenState.data.evolucion_economica.frase_radial}»
                    </blockquote>
                  ) : resumenState.data.evolucion_economica.sin_dato_motivo ? (
                    <p className="subtle">{resumenState.data.evolucion_economica.sin_dato_motivo}</p>
                  ) : null}

                  <dl className="aysen-inline-meta">
                    <div>
                      <dt>Período</dt>
                      <dd>{resumenState.data.evolucion_economica.periodo || String(anio)}</dd>
                    </div>
                    <div>
                      <dt>Unidad</dt>
                      <dd>{resumenState.data.evolucion_economica.unidad || 'Variación real anual (%)'}</dd>
                    </div>
                    <div>
                      <dt>Cobertura</dt>
                      <dd>{resumenState.data.evolucion_economica.cobertura || 'Región de Aysén (BCCh)'}</dd>
                    </div>
                  </dl>

                  <div className="aysen-card-actions">
                    <button
                      type="button"
                      className="aysen-cta-btn"
                      onClick={() => switchTab('economia')}
                    >
                      Ver en Economía <span aria-hidden="true">→</span>
                    </button>
                    <SourceLink fuente={resumenState.data.evolucion_economica.fuente} />
                  </div>
                </article>

                {/* Tarjeta 2: Inversión pública registrada */}
                <article className="aysen-card aysen-summary-card">
                  <div className="aysen-card-top">
                    <span className="aysen-card-kicker">2 · Inversión pública</span>
                    {resumenState.data.inversion_publica.variacion_mismo_periodo_pct !== null && (
                      <span className="aysen-pill-accent">
                        {fmtPct(resumenState.data.inversion_publica.variacion_mismo_periodo_pct, true)} vs mismo período
                      </span>
                    )}
                  </div>

                  <p className={`aysen-big-figure${!resumenState.data.inversion_publica.disponible ? ' is-missing' : ''}`}>
                    {resumenState.data.inversion_publica.monto_millones !== null
                      ? fmtMillions(resumenState.data.inversion_publica.monto_millones)
                      : 'Sin dato disponible'}
                  </p>
                  <p className="aysen-figure-caption">
                    {resumenState.data.inversion_publica.variacion_mismo_periodo_pct !== null &&
                    resumenState.data.inversion_publica.periodo_comparado
                      ? resumenState.data.inversion_publica.periodo_comparado
                      : `Ejecución de inversión y capital registrada (${anio})`}
                  </p>

                  {resumenState.data.inversion_publica.instituciones_cubiertas.length > 0 && (
                    <div className="aysen-covered-block">
                      <span className="aysen-covered-label">Instituciones cubiertas:</span>
                      <ul className="aysen-chip-list">
                        {resumenState.data.inversion_publica.instituciones_cubiertas.map(inst => (
                          <li key={inst}>{inst}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {resumenState.data.inversion_publica.frase_radial ? (
                    <blockquote className="aysen-radio-quote">
                      «{resumenState.data.inversion_publica.frase_radial}»
                    </blockquote>
                  ) : resumenState.data.inversion_publica.sin_dato_motivo ? (
                    <p className="subtle">{resumenState.data.inversion_publica.sin_dato_motivo}</p>
                  ) : null}

                  <dl className="aysen-inline-meta">
                    <div>
                      <dt>Período</dt>
                      <dd>{resumenState.data.inversion_publica.periodo || String(anio)}</dd>
                    </div>
                    <div>
                      <dt>Unidad</dt>
                      <dd>{resumenState.data.inversion_publica.unidad || 'Millones de pesos ($ MM)'}</dd>
                    </div>
                    <div>
                      <dt>Cobertura</dt>
                      <dd>{resumenState.data.inversion_publica.cobertura || 'Instituciones con corte oficial'}</dd>
                    </div>
                  </dl>

                  <div className="aysen-card-actions">
                    <button
                      type="button"
                      className="aysen-cta-btn"
                      onClick={() => switchTab('presupuestos')}
                    >
                      Ver en Presupuestos <span aria-hidden="true">→</span>
                    </button>
                    <SourceLink fuente={resumenState.data.inversion_publica.fuente} />
                  </div>
                </article>

                {/* Tarjeta 3: Compromisos de años anteriores (arrastre) */}
                <article className="aysen-card aysen-summary-card">
                  <div className="aysen-card-top">
                    <span className="aysen-card-kicker">3 · Arrastre comprometido</span>
                    <span className="aysen-arrastre-badge is-arrastre">Arrastre</span>
                  </div>

                  <p className={`aysen-big-figure${!resumenState.data.arrastre.disponible ? ' is-missing' : ''}`}>
                    {resumenState.data.arrastre.porcentaje_pct !== null
                      ? fmtPct(resumenState.data.arrastre.porcentaje_pct)
                      : resumenState.data.arrastre.monto_millones !== null
                        ? fmtMillions(resumenState.data.arrastre.monto_millones)
                        : 'Sin dato disponible'}
                  </p>
                  <p className="aysen-figure-caption">
                    {resumenState.data.arrastre.monto_millones !== null && resumenState.data.arrastre.porcentaje_pct !== null
                      ? `Equivale a ${fmtMillions(resumenState.data.arrastre.monto_millones)}`
                      : 'Arrastre documentado en obras de inversión'}
                    {resumenState.data.arrastre.base_calculo ? ` · ${resumenState.data.arrastre.base_calculo}` : ''}
                  </p>

                  {resumenState.data.arrastre.frase_radial ? (
                    <blockquote className="aysen-radio-quote">
                      «{resumenState.data.arrastre.frase_radial}»
                    </blockquote>
                  ) : resumenState.data.arrastre.sin_dato_motivo ? (
                    <p className="subtle">{resumenState.data.arrastre.sin_dato_motivo}</p>
                  ) : null}

                  <dl className="aysen-inline-meta">
                    <div>
                      <dt>Período</dt>
                      <dd>{resumenState.data.arrastre.periodo || String(anio)}</dd>
                    </div>
                    <div>
                      <dt>Unidad</dt>
                      <dd>{resumenState.data.arrastre.unidad || '% y millones CLP'}</dd>
                    </div>
                    <div>
                      <dt>Cobertura</dt>
                      <dd>
                        {resumenState.data.arrastre.cobertura ||
                          (resumenState.data.arrastre.total_proyectos_evaluados !== null
                            ? `${resumenState.data.arrastre.total_proyectos_evaluados} obras evaluadas`
                            : 'Registro de contratos con fecha verificada')}
                      </dd>
                    </div>
                  </dl>

                  <div className="aysen-card-actions">
                    <button
                      type="button"
                      className="aysen-cta-btn"
                      onClick={() => switchTab('proyectos')}
                    >
                      Ver en Proyectos <span aria-hidden="true">→</span>
                    </button>
                    <SourceLink fuente={resumenState.data.arrastre.fuente} />
                  </div>
                </article>
              </div>
            </>
          )}
        </section>
      )}

      {activeTab === 'economia' && (
        <section
          id="panel-economia"
          role="tabpanel"
          aria-labelledby="tab-economia"
          className="aysen-panel"
        >
          <div className="aysen-question-head">
            <h2>¿De qué vive Aysén y cómo ha cambiado?</h2>
            <p className="subtle">
              Actividad económica regional oficial del Banco Central de Chile (Cuentas Nacionales).
            </p>
          </div>

          {showRegionalPibHint && (
            <p className="aysen-hint-bar" role="note">
              El PIB se publica solo a escala regional (<strong>Región de Aysén</strong>). Tu filtro comunal ({getComunaNombre(comunaActivaEnCabecera)}) se conserva para Presupuestos y Proyectos.
            </p>
          )}

          {economiaState.loading ? (
            <LoadingCard label={`Consultando Cuentas Nacionales de Aysén para ${anio}…`} />
          ) : economiaState.error ? (
            <ErrorNotice error={economiaState.error} onRetry={triggerRetry} />
          ) : !economiaState.data ? (
            <p className="aysen-empty">Sin dato disponible para el año {anio}.</p>
          ) : (
            <>
              {(economiaState.data.en_curso || economiaState.data.aviso_periodo) && (
                <InProgressBanner
                  anio={economiaState.data.anio}
                  mesCorteNombre={economiaState.data.mes_corte_nombre}
                  aviso={
                    economiaState.data.aviso_periodo ||
                    `El PIB regional anual de ${economiaState.data.anio} se publica una vez cerrado el año calendario. Se muestran las series oficiales disponibles hasta ${economiaState.data.anio_datos ?? 'el último cierre publicado'}.`
                  }
                />
              )}

              {/* Gráfico principal único + selector de 3 vistas */}
              <article className="aysen-card aysen-chart-card">
                <div className="aysen-chart-header">
                  <div>
                    <span className="aysen-territory-tag is-regional">Región de Aysén</span>
                    <h3>
                      {ecoView === 'crecimiento'
                        ? 'Crecimiento real del PIB (Aysén vs Chile)'
                        : ecoView === 'participacion'
                          ? 'Participación de Aysén en el PIB nacional (%)'
                          : `Peso por actividad productiva (${economiaState.data.anio_datos ?? anio})`}
                    </h3>
                  </div>

                  <div className="aysen-view-pills" role="group" aria-label="Vista del gráfico económico">
                    <button
                      type="button"
                      aria-pressed={ecoView === 'crecimiento'}
                      onClick={() => setEcoView('crecimiento')}
                    >
                      Crecimiento real del PIB
                    </button>
                    <button
                      type="button"
                      aria-pressed={ecoView === 'participacion'}
                      onClick={() => setEcoView('participacion')}
                    >
                      Participación en el PIB nacional
                    </button>
                    <button
                      type="button"
                      aria-pressed={ecoView === 'actividades'}
                      onClick={() => setEcoView('actividades')}
                    >
                      Peso por actividad productiva
                    </button>
                  </div>
                </div>

                {ecoView === 'crecimiento' && (
                  <CrecimientoChart
                    serie={economiaState.data.serie_crecimiento}
                    selectedYear={anio}
                    onSelectYear={y => setAnio(y)}
                  />
                )}

                {ecoView === 'participacion' && (
                  <ParticipacionChart
                    serie={economiaState.data.serie_participacion}
                    selectedYear={anio}
                    onSelectYear={y => setAnio(y)}
                  />
                )}

                {ecoView === 'actividades' && (
                  actividadesOrdenadas.length === 0 ? (
                    <p className="aysen-empty">
                      Sin dato disponible de actividades productivas nominales para {anio}.
                    </p>
                  ) : (
                    <ul className="aysen-activity-list" aria-label="Peso de las actividades productivas de Aysén">
                      {actividadesOrdenadas.map(act => {
                        const pct = act.participacion_pct ?? 0
                        const width = Math.max(2, (pct / maxActivityPct) * 100)
                        return (
                          <li
                            key={act.codigo}
                            className={`aysen-activity-item${act.es_administracion_publica ? ' is-admin' : act.es_pesca ? ' is-pesca' : ''}`}
                          >
                            <div className="aysen-activity-top">
                              <span className="aysen-activity-name">
                                {act.nombre}
                                {act.es_administracion_publica && <span className="mini-tag is-admin">Estado</span>}
                                {act.es_pesca && <span className="mini-tag is-pesca">Pesca</span>}
                              </span>
                              <span className="aysen-activity-val">
                                <strong>{fmtPct(act.participacion_pct)}</strong>
                                <small>{fmtMillions(act.valor_millones)}</small>
                              </span>
                            </div>
                            <div className="aysen-activity-track" aria-hidden="true">
                              <span className="aysen-activity-fill" style={{ width: `${width}%` }} />
                            </div>
                          </li>
                        )
                      })}
                    </ul>
                  )
                )}
              </article>

              {/* Frase destacada: tamaño vs aporte al crecimiento */}
              <aside className="aysen-callout" aria-label="Cómo leer tamaño versus crecimiento">
                <strong>Tamaño de una actividad ≠ aporte al crecimiento del año</strong>
                <p>
                  {economiaState.data.frase_tamano_vs_aporte ||
                    'El peso de cada actividad muestra qué parte de la economía representa en pesos corrientes (tamaño), mientras que el aporte al crecimiento depende de cuánto varió su producción real en el año multiplicado por su peso. Un sector pequeño puede explicar gran parte del crecimiento si tiene un salto fuerte.'}
                </p>
              </aside>

              {/* Tarjetas de sectores que crecieron y cayeron */}
              <div className="aysen-sectors-grid">
                <article className="aysen-card aysen-sector-card is-up">
                  <h3>Sectores que más crecieron</h3>
                  {economiaState.data.sectores_crecieron.length === 0 ? (
                    <p className="subtle">Sin dato disponible para el año seleccionado.</p>
                  ) : (
                    <ul className="aysen-sector-list">
                      {economiaState.data.sectores_crecieron.map(s => (
                        <li key={s.nombre}>
                          <div>
                            <strong>{s.nombre}</strong>
                            {s.participacion_pct !== null && (
                              <span className="subtle"> · Peso: {fmtPct(s.participacion_pct)}</span>
                            )}
                          </div>
                          <div className="aysen-sector-nums">
                            <span className="is-pos">{fmtPct(s.variacion_pct, true)}</span>
                            {s.aporte_pp !== null && <small>Aporte est.: {fmtPp(s.aporte_pp)}</small>}
                          </div>
                        </li>
                      ))}
                    </ul>
                  )}
                </article>

                <article className="aysen-card aysen-sector-card is-down">
                  <h3>Sectores que cayeron</h3>
                  {economiaState.data.sectores_cayeron.length === 0 ? (
                    <p className="subtle">Sin dato disponible o sin sectores en contracción informados para este período.</p>
                  ) : (
                    <ul className="aysen-sector-list">
                      {economiaState.data.sectores_cayeron.map(s => (
                        <li key={s.nombre}>
                          <div>
                            <strong>{s.nombre}</strong>
                            {s.participacion_pct !== null && (
                              <span className="subtle"> · Peso: {fmtPct(s.participacion_pct)}</span>
                            )}
                          </div>
                          <div className="aysen-sector-nums">
                            <span className="is-neg">{fmtPct(s.variacion_pct, true)}</span>
                            {s.aporte_pp !== null && <small>Aporte est.: {fmtPp(s.aporte_pp)}</small>}
                          </div>
                        </li>
                      ))}
                    </ul>
                  )}
                </article>
              </div>

              <p className="aysen-method-note">
                <strong>Nota sobre volúmenes encadenados:</strong>{' '}
                {economiaState.data.nota_volumenes_encadenados ||
                  'Las series reales del Banco Central usan volúmenes encadenados (referencia 2018), por lo que la suma de actividades reales no es exactamente aditiva al PIB total. El peso porcentual sectorial se calcula siempre sobre cifras nominales (precios corrientes).'}
              </p>

              {/* Bloques secundarios guardados detrás de <details> */}
              <div className="aysen-details-stack">
                <details className="aysen-details">
                  <summary>Ver detalle (tablas completas de series y actividades)</summary>
                  <div className="aysen-details-body">
                    {economiaState.data.serie_crecimiento.length > 0 && (
                      <div className="table-scroll" tabIndex={0} role="region" aria-label="Tabla histórica de crecimiento real del PIB">
                        <table className="pol-table is-compact">
                          <thead>
                            <tr>
                              <th scope="col">Año</th>
                              <th scope="col" className="numeric">Aysén (% real)</th>
                              <th scope="col" className="numeric">Chile (% real)</th>
                              <th scope="col">Estado</th>
                            </tr>
                          </thead>
                          <tbody>
                            {[...economiaState.data.serie_crecimiento].reverse().map(row => (
                              <tr key={row.anio}>
                                <td>{row.anio}</td>
                                <td className="numeric">{fmtPct(row.aysen_pct, true)}</td>
                                <td className="numeric">{fmtPct(row.chile_pct, true)}</td>
                                <td>{row.estado || 'Oficial'}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}

                    {actividadesOrdenadas.length > 0 && (
                      <div className="table-scroll" tabIndex={0} role="region" aria-label="Tabla de actividades productivas de Aysén">
                        <table className="pol-table is-compact">
                          <thead>
                            <tr>
                              <th scope="col">Actividad</th>
                              <th scope="col" className="numeric">Monto nominal</th>
                              <th scope="col" className="numeric">Peso (%)</th>
                              <th scope="col" className="numeric">Var. real</th>
                              <th scope="col">Serie BDE</th>
                            </tr>
                          </thead>
                          <tbody>
                            {actividadesOrdenadas.map(act => (
                              <tr key={act.codigo}>
                                <th scope="row">{act.nombre}</th>
                                <td className="numeric">{fmtMillions(act.valor_millones)}</td>
                                <td className="numeric">{fmtPct(act.participacion_pct)}</td>
                                <td className="numeric">{fmtPct(act.variacion_real_pct, true)}</td>
                                <td className="mono">{act.serie_id || '—'}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>
                </details>

                <details className="aysen-details">
                  <summary>Ver fuente y códigos de series BDE</summary>
                  <div className="aysen-details-body">
                    {economiaState.data.fuentes.length > 0 ? (
                      economiaState.data.fuentes.map((f, idx) => (
                        <div key={`${f.nombre}-${idx}`} className="aysen-source-item">
                          <strong>{f.nombre}</strong>
                          <p className="subtle">
                            {f.periodo ? `Período: ${f.periodo}` : `Corte ${anio}`}
                            {f.unidad ? ` · ${f.unidad}` : ''}
                            {f.cobertura ? ` · ${f.cobertura}` : ''}
                          </p>
                          <SourceLink fuente={f} label="Abrir cuadro oficial BCCh" />
                        </div>
                      ))
                    ) : (
                      <p className="subtle">Banco Central de Chile · Base de Datos Estadísticos (BDE).</p>
                    )}
                    {economiaState.data.codigos_series.length > 0 && (
                      <div>
                        <span className="aysen-covered-label">Códigos de series BDE consultadas:</span>
                        <p className="mono">{economiaState.data.codigos_series.join(' · ')}</p>
                      </div>
                    )}
                  </div>
                </details>

                <details className="aysen-details">
                  <summary>Simulador hipotético (Administración Pública en el PIB)</summary>
                  <div className="aysen-details-body">
                    <div className="sim-disclaimer" role="note">
                      <strong>Herramienta hipotética complementaria · No es observación oficial ni predicción causal.</strong>{' '}
                      Simula cambios aritméticos sobre el Valor Agregado nominal de Administración Pública (Cuentas Nacionales BCCh), magnitud distinta del presupuesto DIPRES.
                    </div>

                    {!simulation || simAdminBase === null || simPibBase === null ? (
                      <p className="subtle">
                        Sin dato disponible de línea base nominal BCCh para ejecutar el simulador en {anio}.
                      </p>
                    ) : (
                      <div className="aysen-sim-box">
                        <div className="sim-control-block">
                          <div className="sim-label-row">
                            <label htmlFor={sliderId}>Variación hipotética de Administración Pública</label>
                            <div className="sim-num-wrap">
                              <label htmlFor={numInputId} className="sr-only">Porcentaje</label>
                              <input
                                id={numInputId}
                                type="number"
                                min={-30}
                                max={30}
                                step={0.5}
                                value={deltaPct}
                                onChange={e => handleNumericDeltaChange(e.target.value)}
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
                            onChange={e => setDeltaPct(Number(e.target.value))}
                          />
                          <div className="aysen-quick-deltas" role="group" aria-label="Atajos de variación">
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
                        </div>

                        <div className="sim-control-block">
                          <label htmlFor={multiplierId}>Multiplicador regional hipotético</label>
                          <select
                            id={multiplierId}
                            value={multiplier}
                            onChange={e => setMultiplier(Number(e.target.value))}
                          >
                            {SIM_MULTIPLIERS.map(item => (
                              <option key={item.value} value={item.value}>{item.label}</option>
                            ))}
                          </select>
                          <p className="subtle">{selectedMultiplierInfo.description}</p>
                        </div>

                        <dl className="aysen-budget-trio" aria-live="polite">
                          <div>
                            <dt>Base Admin. Pública</dt>
                            <dd>{fmtMillions(simAdminBase)}</dd>
                          </div>
                          <div>
                            <dt>Impacto en PIB Aysén</dt>
                            <dd>{fmtPp(simulation.impactPibPp)}</dd>
                          </div>
                          <div className="is-primary">
                            <dt>PIB nominal simulado</dt>
                            <dd>{fmtMillions(simulation.pibSimulated)}</dd>
                          </div>
                        </dl>
                      </div>
                    )}
                  </div>
                </details>
              </div>
            </>
          )}
        </section>
      )}

      {activeTab === 'presupuestos' && (
        <section
          id="panel-presupuestos"
          role="tabpanel"
          aria-labelledby="tab-presupuestos"
          className="aysen-panel"
        >
          <div className="aysen-question-head">
            <h2>¿Cuánto dinero administra cada nivel y en qué lo gasta?</h2>
            <p className="subtle">
              Comparación clara por billetera institucional para {anio} · Comuna seleccionada: <strong>{getComunaNombre(comunaPresupuesto)}</strong>.
            </p>
          </div>

          {presupuestosState.loading ? (
            <LoadingCard label={`Consultando presupuestos de Aysén y ${getComunaNombre(comunaPresupuesto)} para ${anio}…`} />
          ) : presupuestosState.error ? (
            <ErrorNotice error={presupuestosState.error} onRetry={triggerRetry} />
          ) : !presupuestosState.data ? (
            <p className="aysen-empty">Sin dato disponible de presupuestos para {anio}.</p>
          ) : (
            <>
              {presupuestosState.data.en_curso && (
                <InProgressBanner
                  anio={presupuestosState.data.anio}
                  mesCorteNombre={presupuestosState.data.mes_corte_nombre}
                  aviso={presupuestosState.data.aviso_anio_en_curso}
                />
              )}

              {/* Resumen Consolidado sin doble contabilización */}
              {presupuestosState.data.consolidado && (
                <article className="aysen-card aysen-consolidated-card" aria-label="Resumen consolidado sin doble contabilización">
                  <div className="aysen-card-top">
                    <span className="aysen-card-kicker">Consolidado sin doble contabilización</span>
                    <span className="aysen-territory-tag is-regional">Región de Aysén</span>
                  </div>

                  <div className="aysen-consolidated-main">
                    <div>
                      <span className="aysen-split-label">Gasto ejecutado consolidado</span>
                      <p className={`aysen-big-figure${!presupuestosState.data.consolidado.disponible ? ' is-missing' : ''}`}>
                        {fmtMillions(presupuestosState.data.consolidado.ejecutado_total_millones)}
                      </p>
                    </div>
                    {presupuestosState.data.consolidado.transferencias_eliminadas_millones !== null && (
                      <div className="aysen-eliminated-box">
                        <span>Transferencias internas descontadas: </span>
                        <strong>{fmtMillions(presupuestosState.data.consolidado.transferencias_eliminadas_millones)}</strong>
                      </div>
                    )}
                  </div>

                  {presupuestosState.data.consolidado.instituciones_cubiertas.length > 0 && (
                    <div className="aysen-covered-block">
                      <span className="aysen-covered-label">Instituciones cubiertas en este consolidado:</span>
                      <ul className="aysen-chip-list">
                        {presupuestosState.data.consolidado.instituciones_cubiertas.map(inst => (
                          <li key={inst}>{inst}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {presupuestosState.data.consolidado.frase_radial && (
                    <blockquote className="aysen-radio-quote">
                      «{presupuestosState.data.consolidado.frase_radial}»
                    </blockquote>
                  )}

                  {presupuestosState.data.consolidado.nota_sin_doble_contabilizacion && (
                    <p className="subtle">{presupuestosState.data.consolidado.nota_sin_doble_contabilizacion}</p>
                  )}
                </article>
              )}

              {/* Selector de las 3 billeteras + Gobierno Central Nacional */}
              <div className="aysen-view-pills" role="group" aria-label="Filtrar por nivel de presupuesto">
                <button
                  type="button"
                  aria-pressed={billeteraFiltro === 'todas'}
                  onClick={() => setBilleteraFiltro('todas')}
                >
                  Todas ({presupuestosState.data.instituciones.length})
                </button>
                <button
                  type="button"
                  aria-pressed={billeteraFiltro === 'regional'}
                  onClick={() => setBilleteraFiltro('regional')}
                >
                  Gobierno Regional
                </button>
                <button
                  type="button"
                  aria-pressed={billeteraFiltro === 'municipal'}
                  onClick={() => setBilleteraFiltro('municipal')}
                >
                  Municipalidad
                </button>
                <button
                  type="button"
                  aria-pressed={billeteraFiltro === 'nacional_en_region'}
                  onClick={() => setBilleteraFiltro('nacional_en_region')}
                >
                  Vialidad MOP / Servicios
                </button>
                <button
                  type="button"
                  aria-pressed={billeteraFiltro === 'nacional'}
                  onClick={() => setBilleteraFiltro('nacional')}
                >
                  Gobierno Central Nacional
                </button>
              </div>

              {institucionesFiltradas.length === 0 ? (
                <p className="aysen-empty">
                  Sin dato disponible para el nivel institucional seleccionado en {anio}.
                </p>
              ) : (
                <div className="aysen-inst-grid">
                  {institucionesFiltradas.map(inst => (
                    <InstitucionPresupuestoCard key={inst.id} inst={inst} />
                  ))}
                </div>
              )}

              {/* Importador SINIM discreto en <details> */}
              <details className="aysen-details aysen-sinim-details">
                <summary>Cargar otro archivo SINIM (CSV o JSON oficial)</summary>
                <div className="aysen-details-body">
                  <p className="subtle">
                    Si deseas actualizar los balances municipales BEP locales, sube un archivo oficial CSV o JSON de SINIM con formato validado.
                  </p>
                  <div className="aysen-sinim-actions">
                    <a className="secondary-btn link-btn" href={sinimTemplateUrl} download>
                      ↓ Descargar plantilla CSV
                    </a>
                  </div>
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
                        onChange={handleSinimFileChange}
                      />
                    </div>
                    <button type="submit" className="primary" disabled={sinimUpload.submitting}>
                      {sinimUpload.submitting ? 'Importando…' : 'Validar e importar'}
                    </button>
                  </form>

                  {sinimUpload.successMessage && (
                    <p className="sinim-success" role="status" aria-live="polite">
                      {sinimUpload.successMessage}
                    </p>
                  )}
                  {sinimUpload.errorMessage && (
                    <div className="aysen-error-box" role="alert">
                      <p className="error">{sinimUpload.errorMessage}</p>
                    </div>
                  )}
                  {sinimUpload.rowErrors.length > 0 && (
                    <div className="validation-errors" role="alert">
                      <strong>Errores de validación ({sinimUpload.rowErrors.length}):</strong>
                      <ul>
                        {sinimUpload.rowErrors.map((err, idx) => (
                          <li key={idx}>
                            {err.fila !== null && err.fila !== undefined ? `Fila ${err.fila} · ` : ''}
                            {err.columna ? `${err.columna}: ` : ''}
                            {err.motivo}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </details>
            </>
          )}
        </section>
      )}

      {activeTab === 'proyectos' && (
        <section
          id="panel-proyectos"
          role="tabpanel"
          aria-labelledby="tab-proyectos"
          className="aysen-panel"
        >
          <div className="aysen-question-head">
            <h2>¿Qué se hizo, cuándo se decidió y cuánto se pagó?</h2>
            <p className="subtle">
              Contratos, pagos anuales y compromisos de arrastre con trazabilidad por hito oficial.
            </p>
          </div>

          {/* Buscador y filtros */}
          <form className="aysen-search-bar" onSubmit={handleProjectSearchSubmit}>
            <label className="aysen-search-field" htmlFor={searchInputId}>
              <span>Buscar obra, BIP o contrato</span>
              <input
                id={searchInputId}
                type="search"
                value={searchInput}
                placeholder="Ej. Ruta 7, puente, BIP 400…"
                onChange={e => setSearchInput(e.target.value)}
              />
            </label>

            <label className="aysen-search-field" htmlFor={instSelectId}>
              <span>Institución</span>
              <select
                id={instSelectId}
                value={institucionFiltro}
                onChange={e => {
                  setInstitucionFiltro(e.target.value)
                  setSelectedProjectId(null)
                }}
              >
                <option value="">Todas las instituciones</option>
                {(proyectosState.data?.instituciones_disponibles ?? ['Dirección de Vialidad']).map(inst => (
                  <option key={inst} value={inst}>
                    {inst}
                  </option>
                ))}
              </select>
            </label>

            <div className="aysen-search-actions">
              <button type="submit" className="primary">
                Buscar
              </button>
              {(appliedSearch || institucionFiltro || comunaProyectos) && (
                <button
                  type="button"
                  className="secondary-btn"
                  onClick={() => {
                    setSearchInput('')
                    setAppliedSearch('')
                    setInstitucionFiltro('')
                    setComunaProyectos('')
                    setSelectedProjectId(null)
                  }}
                >
                  Limpiar
                </button>
              )}
            </div>
          </form>

          {proyectosState.loading ? (
            <LoadingCard label={`Consultando proyectos y contratos de Aysén para ${anio}…`} />
          ) : proyectosState.error ? (
            <ErrorNotice error={proyectosState.error} onRetry={triggerRetry} />
          ) : !proyectosState.data ? (
            <p className="aysen-empty">Sin dato disponible de proyectos para {anio}.</p>
          ) : (
            <>
              {proyectosState.data.en_curso && (
                <InProgressBanner
                  anio={proyectosState.data.anio}
                  mesCorteNombre={proyectosState.data.mes_corte_nombre}
                />
              )}

              {/* Dos tarjetas separadas respondiendo las dos preguntas distintas */}
              <div className="aysen-arrastre-grid">
                {[
                  proyectosState.data.pregunta_pagado_arrastre,
                  proyectosState.data.pregunta_presupuesto_comprometido,
                ].map((preg, idx) => (
                  <article key={idx} className="aysen-card aysen-question-card">
                    <span className="aysen-card-kicker">Pregunta {idx + 1}</span>
                    <h3>{preg.titulo}</h3>
                    <p className={`aysen-big-figure${!preg.disponible ? ' is-missing' : ''}`}>
                      {preg.porcentaje_pct !== null
                        ? fmtPct(preg.porcentaje_pct)
                        : preg.numerador_millones !== null
                          ? fmtMillions(preg.numerador_millones)
                          : 'Sin dato disponible'}
                    </p>
                    {(preg.numerador_millones !== null || preg.denominador_millones !== null) && (
                      <p className="aysen-figure-caption">
                        {fmtMillions(preg.numerador_millones)} sobre {fmtMillions(preg.denominador_millones)}
                      </p>
                    )}
                    {preg.base_calculo && (
                      <p className="aysen-base-note">
                        <strong>Base:</strong> {preg.base_calculo}
                      </p>
                    )}
                    {preg.frase_radial ? (
                      <blockquote className="aysen-radio-quote">
                        «{preg.frase_radial}»
                      </blockquote>
                    ) : preg.sin_dato_motivo ? (
                      <p className="subtle">{preg.sin_dato_motivo}</p>
                    ) : null}
                    <div className="aysen-question-card-foot">
                      {preg.proyectos_incluidos !== null && (
                        <span className="subtle">
                          {preg.proyectos_incluidos} obras incluidas
                          {preg.proyectos_excluidos ? ` · ${preg.proyectos_excluidos} excluidas por falta de fecha` : ''}
                        </span>
                      )}
                      <SourceLink fuente={preg.fuente} />
                    </div>
                  </article>
                ))}
              </div>

              {/* Vista de Ficha de Proyecto o Lista de Obras */}
              {selectedProject ? (
                <ProyectoFicha
                  proyecto={selectedProject}
                  anio={anio}
                  onBack={() => setSelectedProjectId(null)}
                />
              ) : (
                <section className="aysen-projects-list-wrap" aria-label="Listado de obras y contratos">
                  <div className="aysen-list-head">
                    <h3>Obras registradas ({proyectosState.data.proyectos.length})</h3>
                    <span className="subtle">Toca cualquier obra para abrir su ficha e hitos oficiales.</span>
                  </div>

                  {proyectosState.data.proyectos.length === 0 ? (
                    <p className="aysen-empty">
                      No se encontraron obras con los filtros aplicados para {anio}.
                    </p>
                  ) : (
                    <ul className="aysen-project-list">
                      {proyectosState.data.proyectos.map(proy => (
                        <li key={proy.id}>
                          <button
                            type="button"
                            className="aysen-project-row"
                            onClick={() => setSelectedProjectId(proy.id)}
                          >
                            <div className="aysen-project-row-top">
                              <span className={`aysen-arrastre-badge is-${proy.clasificacion_arrastre}`}>
                                {proy.etiqueta_arrastre}
                              </span>
                              <span className="aysen-project-meta">
                                {proy.comuna ? `${proy.comuna} · ` : ''}{proy.institucion}
                              </span>
                            </div>
                            <strong className="aysen-project-name">{proy.nombre}</strong>
                            <div className="aysen-project-row-nums">
                              <span>
                                <small>Contratado</small>
                                <strong>{fmtMillions(proy.costo_total_millones)}</strong>
                              </span>
                              <span>
                                <small>Pagado {anio}</small>
                                <strong>{fmtMillions(proy.pagado_anio_millones)}</strong>
                              </span>
                              <span className="aysen-row-arrow" aria-hidden="true">Ver ficha →</span>
                            </div>
                          </button>
                        </li>
                      ))}
                    </ul>
                  )}
                </section>
              )}

              {/* Sección separada en <details>: Proyectos con información insuficiente */}
              <details className="aysen-details">
                <summary>
                  Proyectos con información insuficiente ({proyectosState.data.proyectos_insuficientes.length})
                </summary>
                <div className="aysen-details-body">
                  <p className="subtle">
                    Estos proyectos se muestran aparte y quedan excluidos del cálculo porcentual de arrastre para no distorsionar los resultados cuando falta fecha de contratación o monto oficial verificable.
                  </p>
                  {proyectosState.data.proyectos_insuficientes.length === 0 ? (
                    <p className="subtle">No hay proyectos excluidos por información insuficiente con los filtros actuales.</p>
                  ) : (
                    <ul className="aysen-insuf-list">
                      {proyectosState.data.proyectos_insuficientes.map(proy => (
                        <li key={proy.id}>
                          <div className="aysen-insuf-head">
                            <strong>{proy.nombre}</strong>
                            <span className="aysen-project-meta">
                              {proy.comuna ? `${proy.comuna} · ` : ''}{proy.institucion}
                            </span>
                          </div>
                          <p className="subtle">
                            {proy.motivo_insuficiente || 'Falta fecha de contratación o respaldo de pagos para clasificar arrastre.'}
                          </p>
                          <button
                            type="button"
                            className="text-button"
                            onClick={() => setSelectedProjectId(proy.id)}
                          >
                            Ver ficha disponible →
                          </button>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </details>
            </>
          )}
        </section>
      )}
    </div>
  )
}
