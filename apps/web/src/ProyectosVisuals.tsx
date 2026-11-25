import { useMemo, useState } from 'react'
import type { ProyectoObra } from './services/aysenPilotoService'

/* ============================================================
   CLASIFICADOR TEMÁTICO Y FORMATO LEGIBLE DE PROYECTOS (AYSÉN)
============================================================ */

export type ProyectoCategoriaId =
  | 'caminos'
  | 'agua_energia'
  | 'salud'
  | 'educacion'
  | 'vivienda_ciudad'
  | 'seguridad_otros'

export interface ProyectoCategoriaInfo {
  id: ProyectoCategoriaId
  label: string
  shortLabel: string
  color: string
  softBg: string
}

export const PROYECTO_CATEGORIAS: readonly ProyectoCategoriaInfo[] = [
  {
    id: 'caminos',
    label: 'Caminos y conectividad',
    shortLabel: 'Caminos',
    color: '#0d7a5f',
    softBg: '#e6f5ef',
  },
  {
    id: 'agua_energia',
    label: 'Agua, saneamiento y energía',
    shortLabel: 'Agua y energía',
    color: '#1e6e94',
    softBg: '#e7f3f9',
  },
  {
    id: 'vivienda_ciudad',
    label: 'Vivienda, ciudad y deporte',
    shortLabel: 'Ciudad y deporte',
    color: '#d4822a',
    softBg: '#fdf2e4',
  },
  {
    id: 'salud',
    label: 'Salud',
    shortLabel: 'Salud',
    color: '#c44a4a',
    softBg: '#fcebeb',
  },
  {
    id: 'educacion',
    label: 'Educación',
    shortLabel: 'Educación',
    color: '#7652b3',
    softBg: '#f2ecfb',
  },
  {
    id: 'seguridad_otros',
    label: 'Seguridad, equipamiento y otros',
    shortLabel: 'Seguridad y otros',
    color: '#54706a',
    softBg: '#edf2f0',
  },
] as const

const CATEGORIA_BY_ID: Record<ProyectoCategoriaId, ProyectoCategoriaInfo> =
  PROYECTO_CATEGORIAS.reduce(
    (acc, item) => {
      acc[item.id] = item
      return acc
    },
    {} as Record<ProyectoCategoriaId, ProyectoCategoriaInfo>,
  )

function normalizePlain(value: string): string {
  return value
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
}

export function classifyProyecto(proy: ProyectoObra): ProyectoCategoriaInfo {
  const nombre = normalizePlain(proy.nombre || '')
  const inst = normalizePlain(proy.institucion || '')

  // 1. Salud (nombre o institución)
  if (
    inst.includes('salud') ||
    /\b(hospital|posta|cesfam|cecosf|consultorio|ambulancia|sar|sapu|salud rural|clinica)\b/.test(nombre)
  ) {
    return CATEGORIA_BY_ID.salud
  }

  // 2. Educación
  if (
    inst.includes('slep') ||
    inst.includes('educacion') ||
    inst.includes('jardines infantiles') ||
    inst.includes('junji') ||
    /\b(escuela|liceo|colegio|jardin infantil|sala cuna|internado|educacion|educacional|establecimiento educ)\b/.test(nombre)
  ) {
    return CATEGORIA_BY_ID.educacion
  }

  // 3. Agua, saneamiento y energía
  if (
    inst.includes('sanitarios rurales') ||
    inst.includes('obras hidraulicas') ||
    /\b(agua potable|apr|alcantarillado|sanitari|electrific|electrica|fotovoltaic|energia|hidraulic|encauzamiento|defensa fluvial|riego|residuos|relleno sanitario|vertedero|planta de tratamiento)\b/.test(nombre)
  ) {
    return CATEGORIA_BY_ID.agua_energia
  }

  // 4. Caminos, puentes, aeródromos y puertos
  if (
    inst.includes('vialidad') ||
    inst.includes('obras portuarias') ||
    inst.includes('aeropuertos') ||
    inst.includes('transportes') ||
    /\b(ruta\s*\d|camino|puente|pasarela|vial|carretera|aerodromo|aeropuerto|puerto|muelle|rampa|barcaza|transbordador|conectividad|cuesta|balsa|asfalt|ripio|sendero vehicular)\b/.test(nombre)
  ) {
    return CATEGORIA_BY_ID.caminos
  }

  // 5. Vivienda, ciudad, parques y deporte
  if (
    inst.includes('serviu') ||
    inst.includes('vivienda') ||
    /\b(vivienda|parque|plaza|estadio|gimnasio|deportiv|multicancha|cancha|sede social|centro comunitario|mirador|pavimentos participativos|vereda|acera|urban|medialuna|biblioteca|museo|teatro|cultural|paseo|costanera|cementerio)\b/.test(nombre)
  ) {
    return CATEGORIA_BY_ID.vivienda_ciudad
  }

  // Fallback para MOP DGOP genérico sin palabra clave específica -> Caminos y conectividad
  if (inst.includes('mop') || inst.includes('obras publicas')) {
    return CATEGORIA_BY_ID.caminos
  }

  return CATEGORIA_BY_ID.seguridad_otros
}

/** Convierte nombres BIP que vienen EN MAYÚSCULAS a un formato legible en español */
export function formatProjectDisplayName(raw: string): string {
  const trimmed = (raw || '').trim().replace(/\s+/g, ' ')
  if (!trimmed) return 'Obra sin nombre registrado'

  // Si ya tiene minúsculas mezcladas, conservarlo limpio
  const letters = trimmed.replace(/[^a-zA-ZÁÉÍÓÚÑáéíóúñ]/g, '')
  const upperCount = (letters.match(/[A-ZÁÉÍÓÚÑ]/g) || []).length
  if (letters.length > 0 && upperCount / letters.length < 0.72) {
    return trimmed
  }

  const lower = trimmed.toLowerCase()
  const capitalized = lower.charAt(0).toUpperCase() + lower.slice(1)

  const replacements: [RegExp, string][] = [
    [/\baysen\b/gi, 'Aysén'],
    [/\bcoyhaique\b/gi, 'Coyhaique'],
    [/\bcisnes\b/gi, 'Cisnes'],
    [/\bcochrane\b/gi, 'Cochrane'],
    [/\bchile chico\b/gi, 'Chile Chico'],
    [/\brio ibanez\b/gi, 'Río Ibáñez'],
    [/\bguaitecas\b/gi, 'Guaitecas'],
    [/\blago verde\b/gi, 'Lago Verde'],
    [/\bo['’]?higgins\b/gi, 'O’Higgins'],
    [/\btortel\b/gi, 'Tortel'],
    [/\bpuerto aysen\b/gi, 'Puerto Aysén'],
    [/\bpuerto chacabuco\b/gi, 'Puerto Chacabuco'],
    [/\bpuerto cisnes\b/gi, 'Puerto Cisnes'],
    [/\bpuerto ibanez\b/gi, 'Puerto Ibáñez'],
    [/\bpuerto bertrand\b/gi, 'Puerto Bertrand'],
    [/\bpuerto tranquilo\b/gi, 'Puerto Tranquilo'],
    [/\bpuyuhuapi\b/gi, 'Puyuhuapi'],
    [/\bla junta\b/gi, 'La Junta'],
    [/\bvilla manihuales\b/gi, 'Villa Mañihuales'],
    [/\bvilla o['’]?higgins\b/gi, 'Villa O’Higgins'],
    [/\bbalmaceda\b/gi, 'Balmaceda'],
    [/\bcaleta tortel\b/gi, 'Caleta Tortel'],
    [/\bmelinka\b/gi, 'Melinka'],
    [/\bqueulat\b/gi, 'Queulat'],
    [/\bruta\s+(\d+)/gi, 'Ruta $1'],
    [/\bconstruccion\b/gi, 'Construcción'],
    [/\breposicion\b/gi, 'Reposición'],
    [/\bconservacion\b/gi, 'Conservación'],
    [/\bampliacion\b/gi, 'Ampliación'],
    [/\bhabilitacion\b/gi, 'Habilitación'],
    [/\badquisicion\b/gi, 'Adquisición'],
    [/\bregion\b/gi, 'Región'],
    [/\bpublico\b/gi, 'público'],
    [/\bpublica\b/gi, 'pública'],
    [/\bnormalizacion\b/gi, 'Normalización'],
    [/\bpavimentacion\b/gi, 'Pavimentación'],
    [/\belectrificacion\b/gi, 'Electrificación'],
    [/\binfraestructura\b/gi, 'infraestructura'],
  ]

  let result = capitalized
  for (const [pattern, replacement] of replacements) {
    result = result.replace(pattern, replacement)
  }
  result = result.replace(/\brol\s+([a-z]-\d+)/gi, (_m: string, code: string) => `Rol ${code.toUpperCase()}`)
  result = result.replace(/\b(mop|bip|apr|cesfam|cecosf|fndr|slep|serviu|gore|minvu|pdi|junji|ssr|sar|sapu)\b/gi, (m: string) => m.toUpperCase())
  return result.charAt(0).toUpperCase() + result.slice(1)
}

export function simplifyProyectoInst(raw: string): string {
  return (raw || '')
    .replace(/\s*\(BIP\)/gi, '')
    .replace(/\s*\(FNDR\)/gi, '')
    .replace(/\s*\(MINVU\)/gi, '')
    .replace(/\s*\(CAPJ\)/gi, '')
    .replace(/MOP\s*[—–-]\s*Dirección General de Obras Públicas/gi, 'MOP · Obras Públicas')
    .trim()
}

/* ============================================================
   FORMATEADORES NUMÉRICOS
============================================================ */

const num0 = new Intl.NumberFormat('es-CL', { maximumFractionDigits: 0 })
const num1 = new Intl.NumberFormat('es-CL', { minimumFractionDigits: 1, maximumFractionDigits: 1 })

function fmtCompactMillions(val: number): string {
  if (val >= 1000) return `$${num0.format(Math.round(val))} mill.`
  return `$${num1.format(val)} mill.`
}

/* ============================================================
   1. LETREROS CON NÚMEROS GRANDES (BILLBOARD KPI STRIP)
============================================================ */

export function ProyectosBillboardStrip({
  proyectos,
  insuficientesCount,
  anio,
  activeOrigin,
  onSelectOrigin,
}: {
  proyectos: ProyectoObra[]
  insuficientesCount: number
  anio: number
  activeOrigin: 'todos' | 'arrastre' | 'nuevo'
  onSelectOrigin: (next: 'todos' | 'arrastre' | 'nuevo') => void
}) {
  const stats = useMemo(() => {
    let arrastreCount = 0
    let nuevoCount = 0
    let pagadoTotal = 0
    let pagadoArrastre = 0
    let pagadoNuevo = 0
    let compromisoTotal = 0

    for (const p of proyectos) {
      const pag = p.pagado_anio_millones ?? 0
      const comp = p.compromiso_anio_millones ?? 0
      pagadoTotal += pag
      compromisoTotal += comp
      if (p.clasificacion_arrastre === 'arrastre') {
        arrastreCount += 1
        pagadoArrastre += pag
      } else if (p.clasificacion_arrastre === 'nuevo') {
        nuevoCount += 1
        pagadoNuevo += pag
      }
    }

    const total = proyectos.length
    const pctArrastre = total > 0 ? (arrastreCount / total) * 100 : 0
    const pctNuevo = total > 0 ? (nuevoCount / total) * 100 : 0

    return {
      total,
      arrastreCount,
      nuevoCount,
      pctArrastre,
      pctNuevo,
      pagadoTotal,
      pagadoArrastre,
      pagadoNuevo,
      compromisoTotal,
    }
  }, [proyectos])

  return (
    <section className="proy-billboards" aria-label={`Resumen visual de proyectos en ${anio}`}>
      <button
        type="button"
        className={`proy-billboard is-total${activeOrigin === 'todos' ? ' is-selected' : ''}`}
        onClick={() => onSelectOrigin('todos')}
        aria-pressed={activeOrigin === 'todos'}
      >
        <span className="proy-billboard-kicker">Total de obras ({anio})</span>
        <strong className="proy-billboard-num">
          {num0.format(stats.total)}
          <span className="proy-billboard-unit">obras</span>
        </strong>
        <span className="proy-billboard-sub">
          {insuficientesCount > 0
            ? `+ ${insuficientesCount} aparte por falta de datos`
            : 'Todas con respaldo oficial'}
        </span>
      </button>

      <button
        type="button"
        className={`proy-billboard is-arrastre${activeOrigin === 'arrastre' ? ' is-selected' : ''}`}
        onClick={() => onSelectOrigin(activeOrigin === 'arrastre' ? 'todos' : 'arrastre')}
        aria-pressed={activeOrigin === 'arrastre'}
      >
        <span className="proy-billboard-kicker">Venían de antes (arrastre)</span>
        <strong className="proy-billboard-num">
          {num0.format(stats.arrastreCount)}
          <span className="proy-billboard-unit">{num1.format(stats.pctArrastre)}%</span>
        </strong>
        <span className="proy-billboard-sub">
          Pagado en {anio}: <strong>{fmtCompactMillions(stats.pagadoArrastre)}</strong>
        </span>
      </button>

      <button
        type="button"
        className={`proy-billboard is-nuevo${activeOrigin === 'nuevo' ? ' is-selected' : ''}`}
        onClick={() => onSelectOrigin(activeOrigin === 'nuevo' ? 'todos' : 'nuevo')}
        aria-pressed={activeOrigin === 'nuevo'}
      >
        <span className="proy-billboard-kicker">Obras nuevas en {anio}</span>
        <strong className="proy-billboard-num">
          {num0.format(stats.nuevoCount)}
          <span className="proy-billboard-unit">{num1.format(stats.pctNuevo)}%</span>
        </strong>
        <span className="proy-billboard-sub">
          Pagado en {anio}: <strong>{fmtCompactMillions(stats.pagadoNuevo)}</strong>
        </span>
      </button>

      <div className="proy-billboard is-money">
        <span className="proy-billboard-kicker">Dinero pagado en {anio}</span>
        <strong className="proy-billboard-num">
          ${num0.format(Math.round(stats.pagadoTotal))}
          <span className="proy-billboard-unit">millones</span>
        </strong>
        <span className="proy-billboard-sub">
          Comprometido: <strong>${num0.format(Math.round(stats.compromisoTotal))} mill.</strong>
        </span>
      </div>
    </section>
  )
}

/* ============================================================
   2. GRÁFICO DE TORTA / DONUT SVG REUTILIZABLE E INTERACTIVO
============================================================ */

interface DonutSlice {
  id: string
  label: string
  value: number
  count: number
  amountMillions: number
  color: string
}

function InteractiveDonutChart({
  title,
  subtitle,
  slices,
  metricMode,
  selectedId,
  onSelectSlice,
  centerUnitLabel,
}: {
  title: string
  subtitle: string
  slices: DonutSlice[]
  metricMode: 'count' | 'amount'
  selectedId: string | null
  onSelectSlice?: (id: string) => void
  centerUnitLabel: string
}) {
  const [hoveredId, setHoveredId] = useState<string | null>(null)
  const total = useMemo(() => slices.reduce((acc, s) => acc + s.value, 0), [slices])

  const activeSlice = useMemo(() => {
    const targetId = hoveredId ?? selectedId
    if (!targetId) return null
    return slices.find(s => s.id === targetId) ?? null
  }, [hoveredId, selectedId, slices])

  // Geometría SVG del anillo (donut)
  const size = 200
  const cx = size / 2
  const cy = size / 2
  const radius = 72
  const strokeWidth = 28
  const circumference = 2 * Math.PI * radius

  let cumulativeFraction = 0
  const segments = slices
    .filter(s => s.value > 0)
    .map(slice => {
      const fraction = total > 0 ? slice.value / total : 0
      const dashLength = fraction * circumference
      const gap = slices.filter(s => s.value > 0).length > 1 ? 1.8 : 0
      const visibleDash = Math.max(0.5, dashLength - gap)
      const dashOffset = -cumulativeFraction * circumference
      cumulativeFraction += fraction
      return {
        ...slice,
        fraction,
        pct: fraction * 100,
        visibleDash,
        dashOffset,
      }
    })

  return (
    <article className="aysen-card proy-donut-card">
      <div className="proy-donut-head">
        <h3>{title}</h3>
        <p className="subtle">{subtitle}</p>
      </div>

      {total <= 0 ? (
        <p className="aysen-empty">Sin montos o proyectos para graficar con los filtros actuales.</p>
      ) : (
        <div className="proy-donut-layout">
          <div className="proy-donut-svg-wrap">
            <svg
              className="proy-donut-svg"
              viewBox={`0 0 ${size} ${size}`}
              role="img"
              aria-label={`${title}: ${segments.map(s => `${s.label} ${num1.format(s.pct)}%`).join(', ')}`}
              onMouseLeave={() => setHoveredId(null)}
            >
              <circle
                cx={cx}
                cy={cy}
                r={radius}
                fill="none"
                stroke="#edf3f0"
                strokeWidth={strokeWidth}
              />
              <g transform={`rotate(-90 ${cx} ${cy})`}>
                {segments.map(seg => {
                  const isActive = activeSlice?.id === seg.id
                  const isDimmed = Boolean(activeSlice) && !isActive
                  return (
                    <circle
                      key={seg.id}
                      cx={cx}
                      cy={cy}
                      r={radius}
                      fill="none"
                      stroke={seg.color}
                      strokeWidth={isActive ? strokeWidth + 5 : strokeWidth}
                      strokeDasharray={`${seg.visibleDash} ${circumference}`}
                      strokeDashoffset={seg.dashOffset}
                      className={`proy-donut-seg${onSelectSlice ? ' is-clickable' : ''}`}
                      style={{ opacity: isDimmed ? 0.34 : 1 }}
                      onMouseEnter={() => setHoveredId(seg.id)}
                      onClick={() => onSelectSlice?.(seg.id)}
                    >
                      <title>
                        {seg.label}: {num1.format(seg.pct)}% ({seg.count} obras · {fmtCompactMillions(seg.amountMillions)})
                      </title>
                    </circle>
                  )
                })}
              </g>
            </svg>

            <div className="proy-donut-center" aria-live="polite">
              {activeSlice ? (
                <>
                  <strong>
                    {num1.format(total > 0 ? (activeSlice.value / total) * 100 : 0)}%
                  </strong>
                  <span>{activeSlice.label}</span>
                  <small>
                    {metricMode === 'count'
                      ? `${activeSlice.count} obras`
                      : fmtCompactMillions(activeSlice.amountMillions)}
                  </small>
                </>
              ) : (
                <>
                  <strong>
                    {metricMode === 'count'
                      ? num0.format(total)
                      : `$${num0.format(Math.round(total))}`}
                  </strong>
                  <span>{centerUnitLabel}</span>
                  <small>{onSelectSlice ? 'Toca para filtrar' : 'Total revisado'}</small>
                </>
              )}
            </div>
          </div>

          <ul className="proy-donut-legend">
            {segments.map(seg => {
              const isSelected = selectedId === seg.id
              return (
                <li key={seg.id}>
                  <button
                    type="button"
                    className={`proy-legend-btn${isSelected ? ' is-selected' : ''}`}
                    onMouseEnter={() => setHoveredId(seg.id)}
                    onMouseLeave={() => setHoveredId(null)}
                    onClick={() => onSelectSlice?.(seg.id)}
                    disabled={!onSelectSlice}
                  >
                    <span className="proy-legend-dot" style={{ background: seg.color }} aria-hidden="true" />
                    <span className="proy-legend-name">{seg.label}</span>
                    <span className="proy-legend-val">
                      <strong>{num1.format(seg.pct)}%</strong>
                      <small>
                        {metricMode === 'count'
                          ? `${seg.count}`
                          : fmtCompactMillions(seg.amountMillions)}
                      </small>
                    </span>
                  </button>
                </li>
              )
            })}
          </ul>
        </div>
      )}
    </article>
  )
}

/* ============================================================
   3. BLOQUE DE DOS TORTAS INTERACTIVAS DE DISTRIBUCIÓN
============================================================ */

const INST_PALETTE = ['#0d7a5f', '#1d6f96', '#d4822a', '#7652b3', '#c44a4a', '#59746d']

export function ProyectosDistributionCharts({
  proyectos,
  anio,
  selectedCategory,
  onSelectCategory,
  selectedOrigin,
  onSelectOrigin,
  selectedInstitucion,
  onSelectInstitucion,
}: {
  proyectos: ProyectoObra[]
  anio: number
  selectedCategory: ProyectoCategoriaId | ''
  onSelectCategory: (cat: ProyectoCategoriaId | '') => void
  selectedOrigin: 'todos' | 'arrastre' | 'nuevo'
  onSelectOrigin: (orig: 'todos' | 'arrastre' | 'nuevo') => void
  selectedInstitucion: string
  onSelectInstitucion: (inst: string) => void
}) {
  const [metricMode, setMetricMode] = useState<'count' | 'amount'>('count')
  const [rightChartMode, setRightChartMode] = useState<'institucion' | 'origen'>('institucion')

  // Torta 1: por categoría temática
  const categorySlices = useMemo<DonutSlice[]>(() => {
    const map = new Map<ProyectoCategoriaId, { count: number; amount: number }>()
    for (const p of proyectos) {
      const cat = classifyProyecto(p)
      const prev = map.get(cat.id) ?? { count: 0, amount: 0 }
      prev.count += 1
      prev.amount += p.pagado_anio_millones ?? p.compromiso_anio_millones ?? 0
      map.set(cat.id, prev)
    }
    return PROYECTO_CATEGORIAS.map(cat => {
      const data = map.get(cat.id) ?? { count: 0, amount: 0 }
      return {
        id: cat.id,
        label: cat.label,
        count: data.count,
        amountMillions: data.amount,
        value: metricMode === 'count' ? data.count : data.amount,
        color: cat.color,
      }
    })
      .filter(s => s.count > 0)
      .sort((a, b) => b.value - a.value)
  }, [proyectos, metricMode])

  // Torta 2A: por institución (top 5 + Otras)
  const instSlices = useMemo<DonutSlice[]>(() => {
    const map = new Map<string, { raw: string; label: string; count: number; amount: number }>()
    for (const p of proyectos) {
      const raw = p.institucion || 'Otra institución'
      const prev = map.get(raw) ?? { raw, label: simplifyProyectoInst(raw), count: 0, amount: 0 }
      prev.count += 1
      prev.amount += p.pagado_anio_millones ?? p.compromiso_anio_millones ?? 0
      map.set(raw, prev)
    }
    const sorted = [...map.values()].sort((a, b) =>
      metricMode === 'count' ? b.count - a.count : b.amount - a.amount,
    )
    const top = sorted.slice(0, 5)
    const rest = sorted.slice(5)
    const slices: DonutSlice[] = top.map((item, idx) => ({
      id: item.raw,
      label: item.label,
      count: item.count,
      amountMillions: item.amount,
      value: metricMode === 'count' ? item.count : item.amount,
      color: INST_PALETTE[idx % INST_PALETTE.length],
    }))
    if (rest.length > 0) {
      const restCount = rest.reduce((a, r) => a + r.count, 0)
      const restAmount = rest.reduce((a, r) => a + r.amount, 0)
      slices.push({
        id: '__otras__',
        label: `Otras (${rest.length} instituciones)`,
        count: restCount,
        amountMillions: restAmount,
        value: metricMode === 'count' ? restCount : restAmount,
        color: '#889c96',
      })
    }
    return slices
  }, [proyectos, metricMode])

  // Torta 2B: por origen (Arrastre vs Nuevas)
  const originSlices = useMemo<DonutSlice[]>(() => {
    let arrCount = 0
    let arrAmount = 0
    let newCount = 0
    let newAmount = 0
    for (const p of proyectos) {
      const val = p.pagado_anio_millones ?? p.compromiso_anio_millones ?? 0
      if (p.clasificacion_arrastre === 'arrastre') {
        arrCount += 1
        arrAmount += val
      } else {
        newCount += 1
        newAmount += val
      }
    }
    return [
      {
        id: 'arrastre',
        label: 'Venían de antes (arrastre)',
        count: arrCount,
        amountMillions: arrAmount,
        value: metricMode === 'count' ? arrCount : arrAmount,
        color: '#c97b2c',
      },
      {
        id: 'nuevo',
        label: `Obras nuevas en ${anio}`,
        count: newCount,
        amountMillions: newAmount,
        value: metricMode === 'count' ? newCount : newAmount,
        color: '#0d7a5f',
      },
    ].filter(s => s.count > 0)
  }, [proyectos, metricMode, anio])

  return (
    <section className="proy-charts-section" aria-label="Gráficos de distribución de proyectos">
      <div className="proy-charts-bar">
        <div>
          <h3>¿Cómo se distribuyen los proyectos en {anio}?</h3>
          <p className="subtle">
            Toca cualquier tajada o fila de la leyenda para filtrar la lista de obras abajo.
          </p>
        </div>

        <div className="proy-charts-toggles">
          <div className="history-scale-pills" role="group" aria-label="Medida de los gráficos de torta">
            <button
              type="button"
              aria-pressed={metricMode === 'count'}
              onClick={() => setMetricMode('count')}
            >
              Por cantidad de obras
            </button>
            <button
              type="button"
              aria-pressed={metricMode === 'amount'}
              onClick={() => setMetricMode('amount')}
            >
              Por dinero pagado
            </button>
          </div>
        </div>
      </div>

      <div className="proy-donuts-grid">
        <InteractiveDonutChart
          title="Por área o tema"
          subtitle={
            metricMode === 'count'
              ? 'Cantidad de obras según su tipo (caminos, agua, salud, ciudad, educación)'
              : `Distribución del dinero pagado en ${anio} según área`
          }
          slices={categorySlices}
          metricMode={metricMode}
          selectedId={selectedCategory || null}
          onSelectSlice={id =>
            onSelectCategory(selectedCategory === id ? '' : (id as ProyectoCategoriaId))
          }
          centerUnitLabel={metricMode === 'count' ? 'obras' : 'millones'}
        />

        <div className="proy-donut-right-wrap">
          <div className="proy-donut-subtabs" role="group" aria-label="Cambiar segunda torta">
            <button
              type="button"
              aria-pressed={rightChartMode === 'institucion'}
              onClick={() => setRightChartMode('institucion')}
            >
              Por institución
            </button>
            <button
              type="button"
              aria-pressed={rightChartMode === 'origen'}
              onClick={() => setRightChartMode('origen')}
            >
              Venían de antes vs nuevas
            </button>
          </div>

          {rightChartMode === 'institucion' ? (
            <InteractiveDonutChart
              title="Por institución ejecutora"
              subtitle={
                metricMode === 'count'
                  ? 'Organismos que administran las obras registradas'
                  : `Dinero pagado en ${anio} por organismo`
              }
              slices={instSlices}
              metricMode={metricMode}
              selectedId={selectedInstitucion || null}
              onSelectSlice={id => {
                if (id === '__otras__') return
                onSelectInstitucion(selectedInstitucion === id ? '' : id)
              }}
              centerUnitLabel={metricMode === 'count' ? 'obras' : 'millones'}
            />
          ) : (
            <InteractiveDonutChart
              title="¿Venían de antes o son nuevas?"
              subtitle={
                metricMode === 'count'
                  ? 'Obras que ya venían contratadas frente a proyectos nuevos del año'
                  : `Peso del dinero en obras anteriores frente a nuevas (${anio})`
              }
              slices={originSlices}
              metricMode={metricMode}
              selectedId={selectedOrigin === 'todos' ? null : selectedOrigin}
              onSelectSlice={id => {
                const next = id as 'arrastre' | 'nuevo'
                onSelectOrigin(selectedOrigin === next ? 'todos' : next)
              }}
              centerUnitLabel={metricMode === 'count' ? 'obras' : 'millones'}
            />
          )}
        </div>
      </div>
    </section>
  )
}
