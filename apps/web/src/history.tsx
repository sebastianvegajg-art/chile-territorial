import { useEffect, useMemo, useRef, useState } from 'react'
import type { PointerEvent } from 'react'
import type { Observation, Territory } from './api'

export type Series = { territory: Territory; years: Map<number, Observation> }

const colors = ['#08785e', '#335c9b', '#a14324', '#85621a', '#6c4393', '#92604d', '#087389', '#b13667']
const compact = new Intl.NumberFormat('es-CL', { notation: 'compact', maximumFractionDigits: 1 })
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

export function History({ series, years, label, unit }: { series: Series[]; years: number[]; label: string; unit?: string }) {
  const plot = useRef<HTMLCanvasElement>(null)
  const drawRef = useRef<() => void>(() => {})
  const [pinnedYear, setPinnedYear] = useState<number | null>(null)
  const [hoverYear, setHoverYear] = useState<number | null>(null)

  const color = (index: number) => colors[index % colors.length]
  const lineStyle = (index: number) => index >= colors.length * 2 ? 'dotted' : index >= colors.length ? 'dashed' : 'solid'

  const values = useMemo(
    () => series
      .flatMap(item => Array.from(item.years.values(), row => row.valor === null ? NaN : Number(row.valor)))
      .filter(Number.isFinite),
    [series],
  )

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
      if (!canvas || !ctx || !values.length) return
      const { width, height } = canvas.getBoundingClientRect()
      if (!width || !height) return
      const scale = window.devicePixelRatio || 1
      canvas.width = Math.round(width * scale)
      canvas.height = Math.round(height * scale)
      ctx.scale(scale, scale)

      const left = 58
      const top = 18
      const bottom = height - 37
      const right = width - 17
      const min = Math.min(...values)
      const max = Math.max(...values)
      const pad = (max - min || Math.abs(max) || 1) * 0.08
      const low = min - pad
      const high = max + pad
      const x = (index: number) => left + (right - left) * (years.length > 1 ? index / (years.length - 1) : 0.5)
      const y = (value: number) => bottom - (bottom - top) * (value - low) / (high - low)

      ctx.font = '11px system-ui, sans-serif'
      ctx.setLineDash([])

      // Cuadrícula horizontal y etiquetas Y
      for (let index = 0; index <= 4; index++) {
        const value = low + (high - low) * index / 4
        ctx.strokeStyle = '#dce3dd'
        ctx.lineWidth = 1
        ctx.beginPath()
        ctx.moveTo(left, y(value))
        ctx.lineTo(right, y(value))
        ctx.stroke()
        ctx.fillStyle = '#536460'
        ctx.textAlign = 'right'
        ctx.fillText(compact.format(value), left - 7, y(value) + 4, left - 8)
      }

      // Línea guía vertical del año enfocado
      const guideX = activeIndex >= 0 ? x(activeIndex) : null
      if (guideX !== null) {
        ctx.save()
        ctx.strokeStyle = '#08785e75'
        ctx.lineWidth = 1.5
        ctx.setLineDash([4, 3])
        ctx.beginPath()
        ctx.moveTo(guideX, top)
        ctx.lineTo(guideX, bottom)
        ctx.stroke()
        ctx.restore()
      }

      // Etiquetas del eje X
      ctx.textAlign = 'center'
      ctx.fillStyle = '#536460'
      const tickSpacing = Math.max(1, Math.ceil((years.length - 1) / Math.max(1, Math.floor((right - left) / 45))))
      years.forEach((year, index) => {
        const last = years.length - 1
        if (index !== last && (index % tickSpacing !== 0 || (index !== 0 && last - index < tickSpacing))) return
        const tickX = x(index)
        if (guideX !== null && index !== activeIndex && Math.abs(tickX - guideX) < 34) return
        ctx.fillText(String(year), tickX, bottom + 21)
      })

      if (guideX !== null && activeYear !== null) {
        const labelText = String(activeYear)
        ctx.save()
        ctx.font = '700 11px system-ui, sans-serif'
        const badgeWidth = 38
        const badgeX = Math.min(Math.max(guideX - badgeWidth / 2, left), right - badgeWidth)
        ctx.fillStyle = '#e6f4ee'
        ctx.strokeStyle = '#94c5b5'
        ctx.lineWidth = 1
        ctx.beginPath()
        ctx.roundRect(badgeX, bottom + 8, badgeWidth, 18, 4)
        ctx.fill()
        ctx.stroke()
        ctx.fillStyle = '#07392f'
        ctx.textAlign = 'center'
        ctx.fillText(labelText, badgeX + badgeWidth / 2, bottom + 21)
        ctx.restore()
      }

      // Series y puntos
      series.forEach((item, index) => {
        ctx.strokeStyle = color(index)
        ctx.fillStyle = color(index)
        ctx.lineWidth = 2
        ctx.setLineDash(lineStyle(index) === 'dotted' ? [1, 4] : lineStyle(index) === 'dashed' ? [6, 4] : [])
        let previous: { x: number; y: number } | undefined
        years.forEach((year, position) => {
          const value = item.years.get(year)?.valor
          if (value == null) {
            previous = undefined
            return
          }
          const point = { x: x(position), y: y(Number(value)) }
          if (previous) {
            ctx.beginPath()
            ctx.moveTo(previous.x, previous.y)
            ctx.lineTo(point.x, point.y)
            ctx.stroke()
          }
          ctx.beginPath()
          ctx.arc(point.x, point.y, 2.3, 0, Math.PI * 2)
          ctx.fill()
          previous = point
        })
      })

      // Marcadores destacados en el año activo
      if (activeYear !== null && activeIndex >= 0) {
        ctx.setLineDash([])
        const highlightX = x(activeIndex)
        series.forEach((item, index) => {
          const value = item.years.get(activeYear)?.valor
          if (value == null) return
          const pointY = y(Number(value))
          ctx.beginPath()
          ctx.arc(highlightX, pointY, 4.8, 0, Math.PI * 2)
          ctx.fillStyle = color(index)
          ctx.fill()
          ctx.lineWidth = 2
          ctx.strokeStyle = '#ffffff'
          ctx.stroke()
        })
      }
    }

    drawRef.current = draw
    draw()
  }, [series, years, values, activeIndex, activeYear])

  useEffect(() => {
    const canvas = plot.current
    if (!canvas) return
    const resize = new ResizeObserver(() => drawRef.current())
    resize.observe(canvas)
    return () => resize.disconnect()
  }, [values.length])

  function resolveYear(event: PointerEvent<HTMLCanvasElement>) {
    const canvas = plot.current
    if (!canvas || !years.length) return null
    const rect = canvas.getBoundingClientRect()
    const left = 58
    const right = rect.width - 17
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

  if (!values.length) return <p className="empty">Sin observaciones para el período y los territorios seleccionados.</p>

  return (
    <figure className="history">
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
                  <span className={`history-readout-value${missing ? ' is-missing' : ''}`}>
                    {formatExact(row)}
                    {row?.estado === 'preliminar' && <span className="history-prelim"> (prelim.)</span>}
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
