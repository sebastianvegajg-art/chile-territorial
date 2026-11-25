import { useEffect, useMemo, useRef, useState } from 'react'
import type { PointerEvent } from 'react'
import type { Observation, Territory } from './api'

export type Series = { territory: Territory; years: Map<number, Observation> }
type ScaleMode = 'index' | 'log' | 'linear'

const colors = ['#0b7a5e', '#2f6196', '#b8502e', '#946b1e', '#6f4a99', '#8c5e4b', '#0d7b8f', '#b23b6b']
const compact = new Intl.NumberFormat('es-CL', { notation: 'compact', maximumFractionDigits: 1 })
const dec1 = new Intl.NumberFormat('es-CL', { minimumFractionDigits: 1, maximumFractionDigits: 1 })
const statusText: Record<Observation['estado'], string> = {
  informado: 'Informado',
  preliminar: 'Preliminar',
  faltante: 'Sin dato',
  suprimido: 'Suprimido',
  no_aplicable: 'No aplica',
  error: 'Error',
}

function formatExact(row?: Observation) {
  if (row?.valor == null) return row ? statusText[row.estado] : 'Sin dato'
  const negative = row.valor.startsWith('-')
  const unsigned = negative ? row.valor.slice(1) : row.valor
  const [integer, fraction] = unsigned.split('.')
  const formatted = [integer.replace(/\B(?=(\d{3})+(?!\d))/g, '.'), fraction].filter(Boolean).join(',')
  const suffix = row.unidad === '%' ? '%' : ''
  return `${negative ? '−' : ''}${formatted}${suffix}`
}

function formatReadable(row?: Observation) {
  if (row?.valor == null) return row ? statusText[row.estado] : 'Sin dato'
  const num = Number(row.valor)
  if (!Number.isFinite(num)) return formatExact(row)
  if (row.unidad === '%') {
    return `${num.toLocaleString('es-CL', { minimumFractionDigits: 1, maximumFractionDigits: 2 })}%`
  }
  return num.toLocaleString('es-CL', { minimumFractionDigits: 1, maximumFractionDigits: 1 })
}

function niceStep(range: number, targetTicks = 4): number {
  if (!Number.isFinite(range) || range <= 0) return 1
  const rough = range / Math.max(1, targetTicks)
  const mag = Math.pow(10, Math.floor(Math.log10(rough)))
  const norm = rough / mag
  if (norm <= 1.5) return mag
  if (norm <= 3) return 2 * mag
  if (norm <= 7) return 5 * mag
  return 10 * mag
}

function buildNiceTicks(minVal: number, maxVal: number, nonNegative: boolean): { low: number; high: number; ticks: number[] } {
  const safeMin = nonNegative ? Math.max(0, minVal) : minVal
  const span = Math.max(maxVal - safeMin, Math.abs(maxVal) * 0.1 || 1)
  const step = niceStep(span, 4)
  const low = nonNegative ? Math.max(0, Math.floor(safeMin / step) * step) : Math.floor(safeMin / step) * step
  let high = Math.ceil(maxVal / step) * step
  if (high <= low) high = low + step
  const ticks: number[] = []
  for (let v = low; v <= high + step * 0.001; v += step) {
    ticks.push(Math.abs(v) < 1e-9 ? 0 : Number(v.toPrecision(10)))
  }
  return { low, high, ticks }
}

function buildLogTicks(minPos: number, maxPos: number): { lowExp: number; highExp: number; ticks: number[] } {
  const lo = Math.floor(Math.log10(minPos))
  const hi = Math.ceil(Math.log10(maxPos))
  const ticks: number[] = []
  const multipliers = hi - lo <= 2 ? [1, 2, 5] : [1, 3]
  for (let e = lo; e <= hi; e++) {
    for (const m of multipliers) {
      const val = m * Math.pow(10, e)
      if (val >= minPos * 0.72 && val <= maxPos * 1.35) {
        ticks.push(val)
      }
    }
  }
  if (ticks.length < 2) {
    ticks.push(Math.pow(10, lo), Math.pow(10, hi))
  }
  const unique = Array.from(new Set(ticks)).sort((a, b) => a - b)
  const lowExp = Math.log10(Math.min(minPos * 0.85, unique[0]))
  const highExp = Math.log10(Math.max(maxPos * 1.18, unique[unique.length - 1]))
  return { lowExp, highExp, ticks: unique }
}

function traceSmoothCurve(ctx: CanvasRenderingContext2D, pts: Array<{ x: number; y: number }>) {
  if (pts.length === 0) return
  ctx.moveTo(pts[0].x, pts[0].y)
  if (pts.length === 1) return
  if (pts.length === 2) {
    ctx.lineTo(pts[1].x, pts[1].y)
    return
  }
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[Math.max(0, i - 1)]
    const p1 = pts[i]
    const p2 = pts[i + 1]
    const p3 = pts[Math.min(pts.length - 1, i + 2)]
    const cp1x = p1.x + (p2.x - p0.x) / 6
    const cp1y = p1.y + (p2.y - p0.y) / 6
    const cp2x = p2.x - (p3.x - p1.x) / 6
    const cp2y = p2.y - (p3.y - p1.y) / 6
    ctx.bezierCurveTo(cp1x, cp1y, cp2x, cp2y, p2.x, p2.y)
  }
}

function shortTerritoryLabel(name: string): string {
  const clean = name
    .replace(/^Región (de la |del |de )?/i, '')
    .replace(/del General Carlos Ibáñez del Campo/i, '')
    .replace(/y de la Antártica Chilena/i, '')
    .replace(/Libertador General Bernardo /i, '')
    .trim()
  return clean.length > 15 ? `${clean.slice(0, 14)}…` : clean
}

export function History({ series, years, label, unit }: { series: Series[]; years: number[]; label: string; unit?: string }) {
  const plot = useRef<HTMLCanvasElement>(null)
  const drawRef = useRef<() => void>(() => {})
  const [pinnedYear, setPinnedYear] = useState<number | null>(null)
  const [hoverYear, setHoverYear] = useState<number | null>(null)
  const [userScaleMode, setUserScaleMode] = useState<ScaleMode | null>(null)

  const color = (index: number) => colors[index % colors.length]
  const lineStyle = (index: number) => index >= colors.length * 2 ? 'dotted' : index >= colors.length ? 'dashed' : 'solid'

  const rawValues = useMemo(
    () => series
      .flatMap(item => Array.from(item.years.values(), row => row.valor === null ? NaN : Number(row.valor)))
      .filter(Number.isFinite),
    [series],
  )

  const allPositive = useMemo(
    () => rawValues.length > 0 && rawValues.every(v => v > 0),
    [rawValues],
  )
  const isPercentUnit = unit?.includes('%') ?? false
  const canUseComparableScales = allPositive && !isPercentUnit && series.length >= 2

  const hasLargeScaleGap = useMemo(() => {
    if (!canUseComparableScales || rawValues.length < 2) return false
    const min = Math.min(...rawValues)
    const max = Math.max(...rawValues)
    return min > 0 && max / min >= 5
  }, [canUseComparableScales, rawValues])

  // Si hay brecha grande de escala (ej. Chile vs Aysén), por defecto muestra Índice base 100 para visibilidad real
  const effectiveScale: ScaleMode = !canUseComparableScales
    ? 'linear'
    : (userScaleMode ?? (hasLargeScaleGap ? 'index' : 'linear'))

  // Mapa base por territorio para modo Índice (primer año con dato positivo en el rango visible)
  const baseByTerritory = useMemo(() => {
    const map = new Map<string, { year: number; value: number }>()
    for (const item of series) {
      for (const yr of years) {
        const raw = item.years.get(yr)?.valor
        const num = raw == null ? NaN : Number(raw)
        if (Number.isFinite(num) && num > 0) {
          map.set(item.territory.codigo, { year: yr, value: num })
          break
        }
      }
    }
    return map
  }, [series, years])

  const baseYearLabel = useMemo(() => {
    const firstYears = Array.from(baseByTerritory.values(), b => b.year)
    return firstYears.length ? Math.min(...firstYears) : (years[0] ?? 2013)
  }, [baseByTerritory, years])

  const activeYear = hoverYear !== null && years.includes(hoverYear)
    ? hoverYear
    : pinnedYear !== null && years.includes(pinnedYear)
      ? pinnedYear
      : (years.at(-1) ?? null)

  const activeIndex = activeYear !== null ? years.indexOf(activeYear) : -1

  useEffect(() => {
    const draw = () => {
      const canvas = plot.current
      const ctx = canvas?.getContext('2d')
      if (!canvas || !ctx || !rawValues.length) return
      const { width, height } = canvas.getBoundingClientRect()
      if (!width || !height) return
      const scale = window.devicePixelRatio || 1
      canvas.width = Math.round(width * scale)
      canvas.height = Math.round(height * scale)
      ctx.scale(scale, scale)

      const showEndLabels = width >= 500 && series.length <= 6
      const left = 60
      const top = 20
      const bottom = height - 38
      const right = width - (showEndLabels ? 112 : 18)

      // Construir valores ploteados según la escala elegida
      const plottedValues: number[] = []
      const getPlotted = (item: Series, yr: number): number | null => {
        const raw = item.years.get(yr)?.valor
        if (raw == null) return null
        const num = Number(raw)
        if (!Number.isFinite(num)) return null
        if (effectiveScale === 'index') {
          const base = baseByTerritory.get(item.territory.codigo)
          if (!base || base.value <= 0) return null
          return (num / base.value) * 100
        }
        if (effectiveScale === 'log') {
          return num > 0 ? num : null
        }
        return num
      }

      series.forEach(item => {
        years.forEach(yr => {
          const v = getPlotted(item, yr)
          if (v !== null) plottedValues.push(v)
        })
      })
      if (!plottedValues.length) return

      const minVal = Math.min(...plottedValues)
      const maxVal = Math.max(...plottedValues)

      let yFor: (v: number) => number
      let yTicks: Array<{ value: number; text: string; emphasize?: boolean }> = []

      if (effectiveScale === 'log') {
        const { lowExp, highExp, ticks } = buildLogTicks(minVal, maxVal)
        const expSpan = Math.max(0.25, highExp - lowExp)
        yFor = (v: number) => bottom - ((Math.log10(v) - lowExp) / expSpan) * (bottom - top)
        yTicks = ticks.map(v => ({ value: v, text: compact.format(v) }))
      } else {
        const nonNeg = effectiveScale === 'index' || allPositive
        const { low, high, ticks } = buildNiceTicks(minVal, maxVal, nonNeg)
        const span = Math.max(0.0001, high - low)
        yFor = (v: number) => bottom - ((v - low) / span) * (bottom - top)
        yTicks = ticks.map(v => ({
          value: v,
          text: effectiveScale === 'index'
            ? dec1.format(v)
            : isPercentUnit
              ? `${dec1.format(v)}%`
              : compact.format(v),
          emphasize: (effectiveScale === 'index' && Math.abs(v - 100) < 0.01) || (effectiveScale === 'linear' && !nonNeg && v === 0),
        }))
      }

      const xFor = (index: number) => left + (right - left) * (years.length > 1 ? index / (years.length - 1) : 0.5)

      ctx.font = '11px system-ui, -apple-system, sans-serif'

      // Cuadrícula horizontal sutil
      yTicks.forEach(tick => {
        const py = yFor(tick.value)
        if (py < top - 4 || py > bottom + 4) return
        ctx.save()
        ctx.strokeStyle = tick.emphasize ? '#89a399' : '#e6ece8'
        ctx.lineWidth = tick.emphasize ? 1.25 : 1
        ctx.setLineDash(tick.emphasize ? [4, 3] : [])
        ctx.beginPath()
        ctx.moveTo(left, py)
        ctx.lineTo(right, py)
        ctx.stroke()
        ctx.restore()

        ctx.fillStyle = tick.emphasize ? '#27443c' : '#637570'
        ctx.textAlign = 'right'
        ctx.fillText(tick.text, left - 8, py + 4, left - 10)
      })

      // Línea guía vertical del año enfocado
      const guideX = activeIndex >= 0 ? xFor(activeIndex) : null
      if (guideX !== null) {
        ctx.save()
        ctx.strokeStyle = 'rgba(11, 122, 94, 0.35)'
        ctx.lineWidth = 1.25
        ctx.setLineDash([3, 3])
        ctx.beginPath()
        ctx.moveTo(guideX, top)
        ctx.lineTo(guideX, bottom)
        ctx.stroke()
        ctx.restore()
      }

      // Etiquetas eje X
      ctx.textAlign = 'center'
      ctx.fillStyle = '#5e706b'
      const tickSpacing = Math.max(1, Math.ceil((years.length - 1) / Math.max(1, Math.floor((right - left) / 48))))
      years.forEach((year, index) => {
        const last = years.length - 1
        if (index !== last && (index % tickSpacing !== 0 || (index !== 0 && last - index < tickSpacing))) return
        const tickX = xFor(index)
        if (guideX !== null && index !== activeIndex && Math.abs(tickX - guideX) < 34) return
        ctx.fillText(String(year), tickX, bottom + 22)
      })

      if (guideX !== null && activeYear !== null) {
        ctx.save()
        ctx.font = '700 11px system-ui, -apple-system, sans-serif'
        const badgeWidth = 40
        const badgeX = Math.min(Math.max(guideX - badgeWidth / 2, left), right - badgeWidth)
        ctx.fillStyle = '#e7f5ef'
        ctx.strokeStyle = '#92c7b6'
        ctx.lineWidth = 1
        ctx.beginPath()
        ctx.roundRect(badgeX, bottom + 8, badgeWidth, 19, 99)
        ctx.fill()
        ctx.stroke()
        ctx.fillStyle = '#07392f'
        ctx.textAlign = 'center'
        ctx.fillText(String(activeYear), badgeX + badgeWidth / 2, bottom + 21)
        ctx.restore()
      }

      // Dibujar curvas suaves con área sutil en la serie primaria y etiquetas directas al final
      const endLabels: Array<{ y: number; text: string; color: string }> = []

      series.forEach((item, index) => {
        const strokeColor = color(index)
        const segments: Array<Array<{ x: number; y: number }>> = []
        let current: Array<{ x: number; y: number }> = []
        let lastPt: { x: number; y: number; val: number } | null = null

        years.forEach((year, pos) => {
          const val = getPlotted(item, year)
          if (val === null) {
            if (current.length) segments.push(current)
            current = []
            return
          }
          const pt = { x: xFor(pos), y: yFor(val) }
          current.push(pt)
          lastPt = { ...pt, val }
        })
        if (current.length) segments.push(current)

        // Sutil degradado de área solo si hay <= 3 series para mantener claridad visual
        if (series.length <= 3 && segments.length === 1 && segments[0].length >= 2) {
          const pts = segments[0]
          ctx.save()
          const grad = ctx.createLinearGradient(0, top, 0, bottom)
          grad.addColorStop(0, `${strokeColor}22`)
          grad.addColorStop(1, `${strokeColor}00`)
          ctx.beginPath()
          traceSmoothCurve(ctx, pts)
          ctx.lineTo(pts[pts.length - 1].x, bottom)
          ctx.lineTo(pts[0].x, bottom)
          ctx.closePath()
          ctx.fillStyle = grad
          ctx.fill()
          ctx.restore()
        }

        // Trazo principal suave
        ctx.save()
        ctx.strokeStyle = strokeColor
        ctx.lineWidth = index === 0 ? 2.5 : 2.1
        ctx.lineCap = 'round'
        ctx.lineJoin = 'round'
        ctx.setLineDash(lineStyle(index) === 'dotted' ? [2, 4] : lineStyle(index) === 'dashed' ? [6, 4] : [])
        segments.forEach(seg => {
          ctx.beginPath()
          traceSmoothCurve(ctx, seg)
          ctx.stroke()
        })
        ctx.restore()

        // Puntos discretos
        ctx.save()
        ctx.fillStyle = strokeColor
        segments.forEach(seg => {
          seg.forEach(pt => {
            ctx.beginPath()
            ctx.arc(pt.x, pt.y, 2.1, 0, Math.PI * 2)
            ctx.fill()
          })
        })
        ctx.restore()

        if (lastPt && showEndLabels) {
          endLabels.push({
            y: (lastPt as { y: number }).y,
            text: shortTerritoryLabel(item.territory.nombre),
            color: strokeColor,
          })
        }
      })

      // Etiquetas directas en el borde derecho sin colisiones
      if (showEndLabels && endLabels.length) {
        endLabels.sort((a, b) => a.y - b.y)
        const minGap = 15
        for (let i = 1; i < endLabels.length; i++) {
          if (endLabels[i].y - endLabels[i - 1].y < minGap) {
            endLabels[i].y = endLabels[i - 1].y + minGap
          }
        }
        ctx.save()
        ctx.font = '600 11px system-ui, -apple-system, sans-serif'
        ctx.textAlign = 'left'
        endLabels.forEach(lbl => {
          const clampedY = Math.min(bottom - 2, Math.max(top + 6, lbl.y))
          ctx.fillStyle = lbl.color
          ctx.fillText(lbl.text, right + 8, clampedY + 3, 102)
        })
        ctx.restore()
      }

      // Marcadores luminosos en el año activo
      if (activeYear !== null && activeIndex >= 0) {
        ctx.setLineDash([])
        const highlightX = xFor(activeIndex)
        series.forEach((item, index) => {
          const val = getPlotted(item, activeYear)
          if (val === null) return
          const pointY = yFor(val)
          const strokeColor = color(index)
          ctx.beginPath()
          ctx.arc(highlightX, pointY, 7.5, 0, Math.PI * 2)
          ctx.fillStyle = `${strokeColor}26`
          ctx.fill()
          ctx.beginPath()
          ctx.arc(highlightX, pointY, 4.4, 0, Math.PI * 2)
          ctx.fillStyle = strokeColor
          ctx.fill()
          ctx.lineWidth = 2
          ctx.strokeStyle = '#ffffff'
          ctx.stroke()
        })
      }
    }

    drawRef.current = draw
    draw()
  }, [series, years, rawValues, activeIndex, activeYear, effectiveScale, allPositive, isPercentUnit, baseByTerritory])

  useEffect(() => {
    const canvas = plot.current
    if (!canvas) return
    const resize = new ResizeObserver(() => drawRef.current())
    resize.observe(canvas)
    return () => resize.disconnect()
  }, [rawValues.length])

  function resolveYear(event: PointerEvent<HTMLCanvasElement>) {
    const canvas = plot.current
    if (!canvas || !years.length) return null
    const rect = canvas.getBoundingClientRect()
    const showEndLabels = rect.width >= 500 && series.length <= 6
    const left = 60
    const right = rect.width - (showEndLabels ? 112 : 18)
    const span = Math.max(1, right - left)
    const ratio = Math.min(1, Math.max(0, (event.clientX - rect.left - left) / span))
    const index = years.length > 1 ? Math.round(ratio * (years.length - 1)) : 0
    return years[index] ?? null
  }

  function handlePointerMove(event: PointerEvent<HTMLCanvasElement>) {
    const year = resolveYear(event)
    if (year !== null) setHoverYear(year)
  }

  function handlePointerDown(event: PointerEvent<HTMLCanvasElement>) {
    const year = resolveYear(event)
    if (year !== null) {
      setPinnedYear(year)
      setHoverYear(year)
    }
  }

  if (!rawValues.length) return <p className="empty">Sin observaciones para el período y los territorios seleccionados.</p>

  return (
    <figure className="history">
      {canUseComparableScales && (
        <div className="history-scale-bar">
          <div className="history-scale-pills" role="group" aria-label="Modo de escala del eje vertical">
            <button
              type="button"
              aria-pressed={effectiveScale === 'index'}
              onClick={() => setUserScaleMode('index')}
            >
              Índice ({baseYearLabel} = 100)
            </button>
            <button
              type="button"
              aria-pressed={effectiveScale === 'log'}
              onClick={() => setUserScaleMode('log')}
            >
              Escala logarítmica
            </button>
            <button
              type="button"
              aria-pressed={effectiveScale === 'linear'}
              onClick={() => setUserScaleMode('linear')}
            >
              Escala lineal
            </button>
          </div>
          <span className="history-scale-note subtle">
            {effectiveScale === 'index'
              ? `Evolución comparable desde ${baseYearLabel} = 100 (evita que economías más grandes aplasten a las regiones).`
              : effectiveScale === 'log'
                ? 'Escala logarítmica: muestra magnitudes reales simultáneas entre territorios de distinto tamaño.'
                : 'Escala lineal en valores absolutos.'}
          </span>
        </div>
      )}

      <div className="history-stage">
        <canvas
          ref={plot}
          role="img"
          aria-label={`${label}, ${years[0]} a ${years.at(-1)}. Los valores exactos están en Tabla y procedencia.`}
          onPointerMove={handlePointerMove}
          onPointerDown={handlePointerDown}
          onPointerLeave={() => setHoverYear(null)}
        />
      </div>

      {activeYear !== null && (
        <div className="history-inspector" aria-live="polite">
          <div className="history-inspector-head">
            <div className="history-inspector-title">
              <strong>Detalle {activeYear}</strong>
              {unit && <span className="subtle"> · {unit}</span>}
              <span className="history-hint subtle"> · Desliza sobre el gráfico o elige un año</span>
            </div>
            <label className="history-year-picker">
              <span>Año</span>
              <select
                aria-label="Inspeccionar año"
                value={activeYear}
                onChange={event => {
                  const chosen = Number(event.target.value)
                  setPinnedYear(chosen)
                  setHoverYear(null)
                }}
              >
                {[...years].reverse().map(year => <option key={year} value={year}>{year}</option>)}
              </select>
            </label>
          </div>
          <div className="history-readout">
            {series.map(({ territory, years: byYear }, index) => {
              const row = byYear.get(activeYear)
              const missing = row?.valor == null
              const base = baseByTerritory.get(territory.codigo)
              const num = row?.valor != null ? Number(row.valor) : NaN
              const idxVal = effectiveScale === 'index' && base && Number.isFinite(num) && base.value > 0
                ? (num / base.value) * 100
                : null
              return (
                <div key={territory.codigo} className={`history-readout-item${territory.codigo === 'CL' ? ' is-reference' : ''}`}>
                  <span className="history-readout-name">
                    <span
                      className="history-swatch"
                      aria-hidden="true"
                      style={{ borderColor: color(index), borderTopStyle: lineStyle(index) }}
                    />
                    <span>{territory.nombre}</span>
                  </span>
                  <span
                    className={`history-readout-value${missing ? ' is-missing' : ''}`}
                    title={missing ? undefined : `Valor exacto: ${formatExact(row)}`}
                  >
                    <span>
                      {formatReadable(row)}
                      {row?.estado === 'preliminar' && <span className="history-prelim"> (prelim.)</span>}
                    </span>
                    {idxVal !== null && (
                      <span className="history-index-pill">índice {dec1.format(idxVal)}</span>
                    )}
                  </span>
                </div>
              )
            })}
          </div>
        </div>
      )}

      <ul className="history-legend" aria-label="Series del gráfico">
        {series.map(({ territory }, index) => (
          <li key={territory.codigo}>
            <span aria-hidden="true" style={{ borderColor: color(index), borderTopStyle: lineStyle(index) }} />
            {territory.nombre}
          </li>
        ))}
      </ul>
    </figure>
  )
}
