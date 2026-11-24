import { useEffect, useRef } from 'react'
import type { Observation, Territory } from './api'

export type Series = { territory: Territory; years: Map<number, Observation> }

const colors = ['#08785e', '#335c9b', '#a14324', '#85621a', '#6c4393', '#92604d', '#087389', '#b13667']
const compact = new Intl.NumberFormat('es-CL', { notation: 'compact', maximumFractionDigits: 1 })

export function History({ series, years, label }: { series: Series[]; years: number[]; label: string }) {
  const plot = useRef<HTMLCanvasElement>(null)
  const color = (index: number) => colors[index % colors.length]
  const lineStyle = (index: number) => index >= colors.length * 2 ? 'dotted' : index >= colors.length ? 'dashed' : 'solid'
  const values = series.flatMap(item => Array.from(item.years.values(), row => row.valor === null ? NaN : Number(row.valor)))
    .filter(Number.isFinite)

  useEffect(() => {
    const canvas = plot.current
    const ctx = canvas?.getContext('2d')
    if (!canvas || !ctx || !values.length) return
    const draw = () => {
      const { width, height } = canvas.getBoundingClientRect()
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
      const x = (index: number) => left + (right - left) * (years.length > 1 ? index / (years.length - 1) : .5)
      const y = (value: number) => bottom - (bottom - top) * (value - low) / (high - low)
      ctx.font = '11px system-ui'
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
      ctx.textAlign = 'center'
      const tickSpacing = Math.max(1, Math.ceil((years.length - 1) / Math.max(1, Math.floor((right - left) / 45))))
      years.forEach((year, index) => {
        const last = years.length - 1
        if (index !== last && (index % tickSpacing !== 0 || (index !== 0 && last - index < tickSpacing))) return
        ctx.fillText(String(year), x(index), bottom + 21)
      })
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
    }
    const resize = new ResizeObserver(draw)
    resize.observe(canvas)
    draw()
    return () => resize.disconnect()
  }, [series, years, values])

  if (!values.length) return <p className="empty">Sin observaciones para el período y los territorios seleccionados.</p>
  return <figure className="history">
    <canvas ref={plot} role="img" aria-label={`${label}, ${years[0]} a ${years.at(-1)}. Los valores exactos están en Tabla y procedencia.`} />
    <ul className="history-legend" aria-label="Series del gráfico">
      {series.map(({ territory }, index) => <li key={territory.codigo}>
        <span aria-hidden="true" style={{ borderColor: color(index), borderTopStyle: lineStyle(index) }} />
        {territory.nombre}
      </li>)}
    </ul>
  </figure>
}
