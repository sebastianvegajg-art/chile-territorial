import { useMemo, useState } from 'react'
import { PDZE_AYSEN_2026 } from './data/pdzeAysen2026'
import type { PdzeIniciativa } from './data/pdzeAysen2026'
import {
  PROYECTO_CATEGORIAS,
  classifyProyecto,
  formatProjectDisplayName,
} from './ProyectosVisuals'
import type { ProyectoCategoriaId } from './ProyectosVisuals'
import type { MinutaCifra } from './minuta/minutaModel'
import type { ProyectoObra } from './services/aysenPilotoService'

const num0 = new Intl.NumberFormat('es-CL', { maximumFractionDigits: 0 })
const num1 = new Intl.NumberFormat('es-CL', { minimumFractionDigits: 1, maximumFractionDigits: 1 })
const num2 = new Intl.NumberFormat('es-CL', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

function fmtMillones(val: number): string {
  if (!Number.isFinite(val) || val <= 0) return '—'
  if (val >= 100) return `$${num0.format(Math.round(val))} millones`
  return `$${num1.format(val)} millones`
}

function fmtMillonesCorto(val: number): string {
  if (!Number.isFinite(val) || val <= 0) return '—'
  if (val >= 100) return `$${num0.format(Math.round(val))} mill.`
  return `$${num1.format(val)} mill.`
}

function classifyPdzeItem(item: PdzeIniciativa) {
  const proxy = {
    nombre: item.nombre,
    institucion: item.institucion_principal,
  } as ProyectoObra
  return classifyProyecto(proxy)
}

function getPlazo(inicio: number): 'corto' | 'mediano' | 'largo' {
  if (inicio <= 2028) return 'corto'
  if (inicio <= 2031) return 'mediano'
  return 'largo'
}

export function cifraFromPdzeResumen(): MinutaCifra {
  const res = PDZE_AYSEN_2026.resumen_oficial
  const totalMM = res.presupuesto_total_miles / 1000
  return {
    id: 'pdze-aysen-resumen-2026-2035',
    etiqueta: 'Cartera total PDZE Aysén 2026–2035',
    valorTexto: `$${num0.format(Math.round(totalMM))} millones`,
    subvalor: `${res.iniciativas_total} iniciativas · ${res.etapas_total} etapas ($${num2.format(totalMM / 1_000_000)} billones)`,
    unidad: 'Millones de pesos (10 años)',
    periodo: '2026–2035',
    territorio: 'Región de Aysén (10 comunas)',
    institucion: 'Gobierno Regional de Aysén · SUBDERE · Ministerios',
    explicacion: `Plan de inversión a 10 años financiado en un ${res.financiamiento_pct.sectorial}% por ministerios sectoriales, ${res.financiamiento_pct.gore_fndr}% por el GORE (FNDR) y ${res.financiamiento_pct.subdere_pdze}% por Provisión PDZE SUBDERE.`,
    baseCalculo: 'Presupuesto oficial de cartera aprobada por Acuerdo CORE N° 6.959 y Res. Ex. SUBDERE N° 361.',
    disponible: true,
    origenSeccion: 'PDZE 2026–2035',
    fuente: {
      id: 'gore-aysen-subdere|pdze-2026-2035|2026-01-27',
      organismo: 'Gobierno Regional de Aysén · SUBDERE',
      documento: 'Plan de Desarrollo de Zonas Extremas (PDZE) 2026–2035 · Res. Ex. SUBDERE N° 361',
      fechaCorte: '2026-01-27',
      url: 'https://www.goreaysen.cl',
    },
    agregadoEn: new Date().toISOString(),
  }
}

export function cifraFromPdzeIniciativa(item: PdzeIniciativa): MinutaCifra {
  return {
    id: `pdze-inic-${item.id}`,
    etiqueta: `PDZE: ${formatProjectDisplayName(item.nombre)}`,
    valorTexto: fmtMillones(item.monto_total_millones),
    subvalor: `${item.comuna} · ${item.anio_inicio}–${item.anio_termino} (${item.etapas.map(e => e.etapa).join(' + ')})`,
    unidad: 'Millones de pesos (cartera PDZE)',
    periodo: `${item.anio_inicio}–${item.anio_termino}`,
    territorio: `Comuna de ${item.comuna} (${item.provincia})`,
    institucion: item.instituciones.join(' / '),
    explicacion: `Iniciativa incluida en el PDZE Aysén 2026–2035${item.codigo_bip ? ` (BIP ${item.codigo_bip})` : ''}, con aporte sectorial ${fmtMillonesCorto(item.monto_sectorial_millones)}, GORE ${fmtMillonesCorto(item.monto_gore_millones)} y SUBDERE ${fmtMillonesCorto(item.monto_subdere_millones)}.`,
    baseCalculo: null,
    disponible: true,
    origenSeccion: 'PDZE 2026–2035',
    fuente: {
      id: 'gore-aysen-subdere|pdze-2026-2035|2026-01-27',
      organismo: 'Gobierno Regional de Aysén · SUBDERE',
      documento: `PDZE Aysén 2026–2035 · Res. Ex. SUBDERE N° 361 (pág. ${item.pagina_documento})`,
      fechaCorte: '2026-01-27',
      url: 'https://www.goreaysen.cl',
    },
    agregadoEn: new Date().toISOString(),
  }
}

interface PdzeSlice {
  id: string
  label: string
  value: number
  secondary: string
  color: string
}

function PdzeDonut({
  title,
  subtitle,
  slices,
  centerMain,
  centerSub,
  selectedId,
  onSelect,
}: {
  title: string
  subtitle: string
  slices: PdzeSlice[]
  centerMain: string
  centerSub: string
  selectedId?: string | null
  onSelect?: (id: string) => void
}) {
  const [hovered, setHovered] = useState<string | null>(null)
  const total = slices.reduce((acc, s) => acc + s.value, 0)
  const active = slices.find(s => s.id === (hovered ?? selectedId)) ?? null

  const size = 196
  const cx = size / 2
  const cy = size / 2
  const radius = 70
  const strokeWidth = 26
  const circumference = 2 * Math.PI * radius

  let cum = 0
  const segments = slices
    .filter(s => s.value > 0)
    .map(s => {
      const frac = total > 0 ? s.value / total : 0
      const dash = Math.max(0.5, frac * circumference - 1.8)
      const offset = -cum * circumference
      cum += frac
      return { ...s, pct: frac * 100, dash, offset }
    })

  return (
    <article className="aysen-card proy-donut-card">
      <div className="proy-donut-head">
        <h3>{title}</h3>
        <p className="subtle">{subtitle}</p>
      </div>

      <div className="proy-donut-layout">
        <div className="proy-donut-svg-wrap">
          <svg
            className="proy-donut-svg"
            viewBox={`0 0 ${size} ${size}`}
            role="img"
            aria-label={title}
            onMouseLeave={() => setHovered(null)}
          >
            <circle cx={cx} cy={cy} r={radius} fill="none" stroke="#ebf1f5" strokeWidth={strokeWidth} />
            <g transform={`rotate(-90 ${cx} ${cy})`}>
              {segments.map(seg => {
                const isAct = active?.id === seg.id
                const dim = Boolean(active) && !isAct
                return (
                  <circle
                    key={seg.id}
                    cx={cx}
                    cy={cy}
                    r={radius}
                    fill="none"
                    stroke={seg.color}
                    strokeWidth={isAct ? strokeWidth + 5 : strokeWidth}
                    strokeDasharray={`${seg.dash} ${circumference}`}
                    strokeDashoffset={seg.offset}
                    className={`proy-donut-seg${onSelect ? ' is-clickable' : ''}`}
                    style={{ opacity: dim ? 0.34 : 1 }}
                    onMouseEnter={() => setHovered(seg.id)}
                    onClick={() => onSelect?.(seg.id)}
                  >
                    <title>{seg.label}: {num1.format(seg.pct)}% ({seg.secondary})</title>
                  </circle>
                )
              })}
            </g>
          </svg>
          <div className="proy-donut-center" aria-live="polite">
            {active ? (
              <>
                <strong>{num1.format(total > 0 ? (active.value / total) * 100 : 0)}%</strong>
                <span>{active.label}</span>
                <small>{active.secondary}</small>
              </>
            ) : (
              <>
                <strong>{centerMain}</strong>
                <span>{centerSub}</span>
                <small>{onSelect ? 'Toca para filtrar' : 'Plan 2026–2035'}</small>
              </>
            )}
          </div>
        </div>

        <ul className="proy-donut-legend">
          {segments.map(seg => (
            <li key={seg.id}>
              <button
                type="button"
                className={`proy-legend-btn${selectedId === seg.id ? ' is-selected' : ''}`}
                onMouseEnter={() => setHovered(seg.id)}
                onMouseLeave={() => setHovered(null)}
                onClick={() => onSelect?.(seg.id)}
                disabled={!onSelect}
              >
                <span className="proy-legend-dot" style={{ background: seg.color }} aria-hidden="true" />
                <span className="proy-legend-name">{seg.label}</span>
                <span className="proy-legend-val">
                  <strong>{num1.format(seg.pct)}%</strong>
                  <small>{seg.secondary}</small>
                </span>
              </button>
            </li>
          ))}
        </ul>
      </div>
    </article>
  )
}

export function PdzeView({
  isCifraInMinuta,
  onToggleMinutaCifra,
}: {
  isCifraInMinuta: (id: string) => boolean
  onToggleMinutaCifra: (cifra: MinutaCifra) => void
}) {
  const { resumen_oficial: plan, provincias, comunas, iniciativas } = PDZE_AYSEN_2026

  const [leftChartMode, setLeftChartMode] = useState<'financiamiento' | 'etapas'>('financiamiento')
  const [rightChartMode, setRightChartMode] = useState<'provincia' | 'categoria'>('provincia')
  const [provinciaFiltro, setProvinciaFiltro] = useState<string>('')
  const [comunaFiltro, setComunaFiltro] = useState<string>('')
  const [categoriaFiltro, setCategoriaFiltro] = useState<ProyectoCategoriaId | ''>('')
  const [etapaFiltro, setEtapaFiltro] = useState<'' | 'Prefactibilidad' | 'Diseño' | 'Ejecución'>('')
  const [plazoFiltro, setPlazoFiltro] = useState<'' | 'corto' | 'mediano' | 'largo'>('')
  const [busqueda, setBusqueda] = useState<string>('')
  const [orden, setOrden] = useState<'monto' | 'inicio' | 'nombre'>('monto')

  const totalBillones = plan.presupuesto_total_miles / 1_000_000_000
  const totalMillones = plan.presupuesto_total_miles / 1000
  const sectorMillones = plan.financiamiento_miles.sectorial / 1000
  const goreMillones = plan.financiamiento_miles.gore_fndr / 1000
  const subdereMillones = plan.financiamiento_miles.subdere_pdze / 1000

  const financiamientoSlices: PdzeSlice[] = [
    {
      id: 'sectorial',
      label: 'Ministerios (Sectorial)',
      value: sectorMillones,
      secondary: fmtMillonesCorto(sectorMillones),
      color: '#1769aa',
    },
    {
      id: 'gore',
      label: 'Gobierno Regional (FNDR)',
      value: goreMillones,
      secondary: fmtMillonesCorto(goreMillones),
      color: '#0d7a5f',
    },
    {
      id: 'subdere',
      label: 'Provisión PDZE (SUBDERE)',
      value: subdereMillones,
      secondary: fmtMillonesCorto(subdereMillones),
      color: '#3aa0c7',
    },
  ]

  const etapasSlices: PdzeSlice[] = [
    {
      id: 'ejecucion',
      label: 'Ejecución de obras',
      value: plan.etapas_porcentaje.ejecucion,
      secondary: '59% de etapas',
      color: '#0d7a5f',
    },
    {
      id: 'diseno',
      label: 'Diseño',
      value: plan.etapas_porcentaje.diseno,
      secondary: '36% de etapas',
      color: '#1d6e9b',
    },
    {
      id: 'prefactibilidad',
      label: 'Prefactibilidad',
      value: plan.etapas_porcentaje.prefactibilidad,
      secondary: '5% de etapas',
      color: '#d4822a',
    },
  ]

  const provinciaColors = ['#1769aa', '#0d7a5f', '#2b95b5', '#7652b3']
  const provinciaSlices: PdzeSlice[] = provincias.map((p, idx) => ({
    id: p.nombre,
    label: p.nombre.replace('Provincia ', '').replace('de ', ''),
    value: p.pdze_miles / 1000,
    secondary: `${p.iniciativas} obras · ${fmtMillonesCorto(p.pdze_miles / 1000)}`,
    color: provinciaColors[idx % provinciaColors.length],
  }))

  const categoriaSlices = useMemo<PdzeSlice[]>(() => {
    const map = new Map<ProyectoCategoriaId, { count: number; mm: number }>()
    for (const item of iniciativas) {
      const cat = classifyPdzeItem(item)
      const prev = map.get(cat.id) ?? { count: 0, mm: 0 }
      prev.count += 1
      prev.mm += item.monto_total_millones
      map.set(cat.id, prev)
    }
    return PROYECTO_CATEGORIAS.map(c => {
      const d = map.get(c.id) ?? { count: 0, mm: 0 }
      return {
        id: c.id,
        label: c.label,
        value: d.mm,
        secondary: `${d.count} obras · ${fmtMillonesCorto(d.mm)}`,
        color: c.color,
      }
    })
      .filter(s => s.value > 0)
      .sort((a, b) => b.value - a.value)
  }, [iniciativas])

  const comunasOrdenadasPerCapita = useMemo(
    () => [...comunas].sort((a, b) => b.per_capita_miles - a.per_capita_miles),
    [comunas],
  )
  const maxPerCapita = Math.max(...comunas.map(c => c.per_capita_miles), 1)

  const iniciativasFiltradas = useMemo(() => {
    const q = busqueda.trim().toLowerCase()
    const list = iniciativas.filter(item => {
      if (provinciaFiltro && item.provincia !== provinciaFiltro) return false
      if (comunaFiltro && item.comuna !== comunaFiltro) return false
      if (categoriaFiltro && classifyPdzeItem(item).id !== categoriaFiltro) return false
      if (etapaFiltro && !item.etapas.some(e => e.etapa === etapaFiltro)) return false
      if (plazoFiltro && getPlazo(item.anio_inicio) !== plazoFiltro) return false
      if (q) {
        const hay = `${item.nombre} ${item.codigo_bip ?? ''} ${item.comuna} ${item.instituciones.join(' ')}`.toLowerCase()
        if (!hay.includes(q)) return false
      }
      return true
    })
    return [...list].sort((a, b) => {
      if (orden === 'inicio') return a.anio_inicio - b.anio_inicio || b.monto_total_millones - a.monto_total_millones
      if (orden === 'nombre') return formatProjectDisplayName(a.nombre).localeCompare(formatProjectDisplayName(b.nombre), 'es')
      return b.monto_total_millones - a.monto_total_millones
    })
  }, [iniciativas, provinciaFiltro, comunaFiltro, categoriaFiltro, etapaFiltro, plazoFiltro, busqueda, orden])

  const hasFilters = Boolean(provinciaFiltro || comunaFiltro || categoriaFiltro || etapaFiltro || plazoFiltro || busqueda.trim())

  return (
    <section
      id="panel-pdze"
      role="tabpanel"
      aria-labelledby="tab-pdze"
      className="aysen-panel"
    >
      {/* Encabezado PDZE */}
      <div className="pdze-hero-card">
        <div className="pdze-hero-top">
          <div>
            <span className="pdze-badge-official">PDZE Aysén · 2026–2035</span>
            <h2>Plan de Desarrollo de Zonas Extremas (PDZE)</h2>
            <p className="pdze-hero-desc">
              Cartera oficial a 10 años para cerrar brechas de conectividad, salud, agua, educación y equipamiento en las 10 comunas de Aysén. Aprobada por unanimidad por el Consejo Regional ({plan.acuerdo_core}) y oficializada mediante <strong>{plan.resolucion}</strong>.
            </p>
          </div>
          <div className="pdze-hero-actions">
            <button
              type="button"
              className={`minuta-add-btn${isCifraInMinuta('pdze-aysen-resumen-2026-2035') ? ' is-saved' : ''}`}
              aria-pressed={isCifraInMinuta('pdze-aysen-resumen-2026-2035')}
              onClick={() => onToggleMinutaCifra(cifraFromPdzeResumen())}
            >
              <span>{isCifraInMinuta('pdze-aysen-resumen-2026-2035') ? '✓' : '+'}</span>{' '}
              {isCifraInMinuta('pdze-aysen-resumen-2026-2035') ? 'Resumen PDZE en minuta' : 'Agregar resumen a minuta'}
            </button>
            <a
              href={plan.url_oficial}
              target="_blank"
              rel="noopener noreferrer"
              className="aysen-source-link"
            >
              GORE Aysén <span aria-hidden="true">↗</span>
            </a>
          </div>
        </div>
      </div>

      {/* 4 Letreros KPI con números grandes */}
      <section className="proy-billboards pdze-billboards" aria-label="Cifras principales del PDZE 2026-2035">
        <div className="proy-billboard is-pdze-total">
          <span className="proy-billboard-kicker">Inversión total (10 años)</span>
          <strong className="proy-billboard-num">
            ${num2.format(totalBillones)}
            <span className="proy-billboard-unit">billones</span>
          </strong>
          <span className="proy-billboard-sub">
            Equivale a <strong>${num0.format(Math.round(totalMillones))} millones</strong> (2026–2035)
          </span>
        </div>

        <div className="proy-billboard is-pdze-count">
          <span className="proy-billboard-kicker">Cartera aprobada</span>
          <strong className="proy-billboard-num">
            {plan.iniciativas_total}
            <span className="proy-billboard-unit">iniciativas</span>
          </strong>
          <span className="proy-billboard-sub">
            <strong>{plan.etapas_total} etapas</strong> (59% ejecución · 36% diseño · 5% prefact.)
          </span>
        </div>

        <div className="proy-billboard is-pdze-sector">
          <span className="proy-billboard-kicker">Aporte Ministerios</span>
          <strong className="proy-billboard-num">
            {plan.financiamiento_pct.sectorial}%
            <span className="proy-billboard-unit">sectorial</span>
          </strong>
          <span className="proy-billboard-sub">
            <strong>{fmtMillonesCorto(sectorMillones)}</strong> (MOP, Salud, MINVU, etc.)
          </span>
        </div>

        <div className="proy-billboard is-pdze-gore">
          <span className="proy-billboard-kicker">GORE + Provisión PDZE</span>
          <strong className="proy-billboard-num">
            {plan.financiamiento_pct.gore_fndr + plan.financiamiento_pct.subdere_pdze}%
            <span className="proy-billboard-unit">regional</span>
          </strong>
          <span className="proy-billboard-sub">
            GORE FNDR <strong>22%</strong> ({fmtMillonesCorto(goreMillones)}) · SUBDERE <strong>10%</strong>
          </span>
        </div>
      </section>

      {/* 2 Gráficos de torta interactivos */}
      <section className="proy-charts-section" aria-label="Distribución visual del PDZE">
        <div className="proy-donuts-grid">
          <div className="proy-donut-right-wrap">
            <div className="proy-donut-subtabs" role="group" aria-label="Vista primera torta PDZE">
              <button
                type="button"
                aria-pressed={leftChartMode === 'financiamiento'}
                onClick={() => setLeftChartMode('financiamiento')}
              >
                ¿Quién financia?
              </button>
              <button
                type="button"
                aria-pressed={leftChartMode === 'etapas'}
                onClick={() => setLeftChartMode('etapas')}
              >
                Por etapa (266)
              </button>
            </div>
            {leftChartMode === 'financiamiento' ? (
              <PdzeDonut
                title="Financiamiento del PDZE 2026–2035"
                subtitle="Aporte de Ministerios (68%), Gobierno Regional FNDR (22%) y Provisión SUBDERE (10%)"
                slices={financiamientoSlices}
                centerMain={`$${num2.format(totalBillones)}`}
                centerSub="billones de pesos"
              />
            ) : (
              <PdzeDonut
                title="Etapas de la cartera (266 etapas)"
                subtitle="Mayoría en ejecución directa de obras (59%) y diseños listos para licitar (36%)"
                slices={etapasSlices}
                centerMain={String(plan.etapas_total)}
                centerSub="etapas en 10 años"
              />
            )}
          </div>

          <div className="proy-donut-right-wrap">
            <div className="proy-donut-subtabs" role="group" aria-label="Vista segunda torta PDZE">
              <button
                type="button"
                aria-pressed={rightChartMode === 'provincia'}
                onClick={() => setRightChartMode('provincia')}
              >
                Por provincia
              </button>
              <button
                type="button"
                aria-pressed={rightChartMode === 'categoria'}
                onClick={() => setRightChartMode('categoria')}
              >
                Por área o tema
              </button>
            </div>
            {rightChartMode === 'provincia' ? (
              <PdzeDonut
                title="Inversión PDZE por provincia"
                subtitle="Toca una provincia para filtrar las iniciativas del plan abajo"
                slices={provinciaSlices}
                centerMain="4"
                centerSub="provincias"
                selectedId={provinciaFiltro || null}
                onSelect={id => {
                  setProvinciaFiltro(prev => (prev === id ? '' : id))
                  setComunaFiltro('')
                }}
              />
            ) : (
              <PdzeDonut
                title="Inversión PDZE por área temática"
                subtitle="Toca un área para filtrar las iniciativas del plan abajo"
                slices={categoriaSlices}
                centerMain={String(iniciativas.length)}
                centerSub="iniciativas detalladas"
                selectedId={categoriaFiltro || null}
                onSelect={id =>
                  setCategoriaFiltro(prev => (prev === id ? '' : (id as ProyectoCategoriaId)))
                }
              />
            )}
          </div>
        </div>
      </section>

      {/* Inversión por comuna (incluye inversión por habitante) */}
      <article className="aysen-card pdze-comunas-card">
        <div className="aysen-list-head">
          <div>
            <h3>Inversión PDZE en las 10 comunas (total y por habitante)</h3>
            <span className="subtle">Toca cualquier comuna para ver sus iniciativas del plan 2026–2035.</span>
          </div>
          {comunaFiltro && (
            <button type="button" className="text-button" onClick={() => setComunaFiltro('')}>
              Ver las 10 comunas ✕
            </button>
          )}
        </div>

        <div className="pdze-comunas-grid">
          {comunasOrdenadasPerCapita.map(com => {
            const isSelected = comunaFiltro === com.nombre
            const barW = Math.max(8, (com.per_capita_miles / maxPerCapita) * 100)
            return (
              <button
                key={com.cut}
                type="button"
                className={`pdze-comuna-tile${isSelected ? ' is-selected' : ''}`}
                aria-pressed={isSelected}
                onClick={() => {
                  setComunaFiltro(isSelected ? '' : com.nombre)
                  setProvinciaFiltro('')
                }}
              >
                <div className="pdze-comuna-top">
                  <strong>{com.nombre}</strong>
                  <span className="pdze-comuna-count">{com.iniciativas} obras</span>
                </div>
                <p className="pdze-comuna-money">
                  <strong>${num0.format(Math.round(com.pdze_miles / 1000))}</strong> <span>millones</span>
                </p>
                <div className="pdze-percapita-row">
                  <small>${num1.format(com.per_capita_miles / 1000)} mill. por habitante</small>
                  <div className="aysen-activity-track" aria-hidden="true">
                    <span className="pdze-percapita-fill" style={{ width: `${barW}%` }} />
                  </div>
                </div>
              </button>
            )
          })}
        </div>
      </article>

      {/* Explorador completo de la cartera PDZE */}
      <section className="aysen-projects-list-wrap" aria-label="Cartera de iniciativas PDZE 2026-2035">
        <div className="aysen-list-head">
          <div>
            <h3>
              Cartera de iniciativas PDZE ({iniciativasFiltradas.length}
              {iniciativasFiltradas.length !== iniciativas.length ? ` de ${iniciativas.length}` : ''})
            </h3>
            <span className="subtle">
              Incluye etapas (prefactibilidad, diseño y ejecución), años proyectados y quién financia cada peso.
            </span>
          </div>
          <label className="proy-sort-field">
            <span>Ordenar por</span>
            <select value={orden} onChange={e => setOrden(e.target.value as 'monto' | 'inicio' | 'nombre')}>
              <option value="monto">Mayor inversión total</option>
              <option value="inicio">Año de inicio más cercano</option>
              <option value="nombre">Nombre (A–Z)</option>
            </select>
          </label>
        </div>

        {/* Barra de búsqueda y filtros */}
        <div className="pdze-filter-bar">
          <input
            type="search"
            value={busqueda}
            placeholder="Buscar iniciativa PDZE, BIP, comuna o institución…"
            aria-label="Buscar iniciativa PDZE"
            onChange={e => setBusqueda(e.target.value)}
          />
          <select
            aria-label="Filtrar por comuna PDZE"
            value={comunaFiltro}
            onChange={e => {
              setComunaFiltro(e.target.value)
              setProvinciaFiltro('')
            }}
          >
            <option value="">Todas las comunas (10)</option>
            {comunas.map(c => (
              <option key={c.cut} value={c.nombre}>
                {c.nombre} ({c.iniciativas})
              </option>
            ))}
          </select>
          <select
            aria-label="Filtrar por etapa PDZE"
            value={etapaFiltro}
            onChange={e => setEtapaFiltro(e.target.value as '' | 'Prefactibilidad' | 'Diseño' | 'Ejecución')}
          >
            <option value="">Todas las etapas</option>
            <option value="Ejecución">Ejecución</option>
            <option value="Diseño">Diseño</option>
            <option value="Prefactibilidad">Prefactibilidad</option>
          </select>
          <select
            aria-label="Filtrar por plazo PDZE"
            value={plazoFiltro}
            onChange={e => setPlazoFiltro(e.target.value as '' | 'corto' | 'mediano' | 'largo')}
          >
            <option value="">Todo el horizonte (2026–2035)</option>
            <option value="corto">Corto plazo (inicio 2026–2028)</option>
            <option value="mediano">Mediano plazo (inicio 2029–2031)</option>
            <option value="largo">Largo plazo (inicio 2032–2035)</option>
          </select>
          {hasFilters && (
            <button
              type="button"
              className="secondary-btn"
              onClick={() => {
                setProvinciaFiltro('')
                setComunaFiltro('')
                setCategoriaFiltro('')
                setEtapaFiltro('')
                setPlazoFiltro('')
                setBusqueda('')
              }}
            >
              Limpiar
            </button>
          )}
        </div>

        {/* Pills de categoría temática */}
        <div className="proy-category-pills" role="group" aria-label="Filtrar PDZE por área temática">
          <button
            type="button"
            className={`proy-cat-pill${categoriaFiltro === '' ? ' is-active' : ''}`}
            onClick={() => setCategoriaFiltro('')}
          >
            Todas ({iniciativas.length})
          </button>
          {PROYECTO_CATEGORIAS.map(cat => {
            const count = iniciativas.filter(i => classifyPdzeItem(i).id === cat.id).length
            if (count === 0) return null
            const isAct = categoriaFiltro === cat.id
            return (
              <button
                key={cat.id}
                type="button"
                className={`proy-cat-pill${isAct ? ' is-active' : ''}`}
                onClick={() => setCategoriaFiltro(isAct ? '' : cat.id)}
              >
                <span className="proy-cat-dot" style={{ background: cat.color }} aria-hidden="true" />
                {cat.shortLabel} ({count})
              </button>
            )
          })}
        </div>

        {iniciativasFiltradas.length === 0 ? (
          <p className="aysen-empty">No se encontraron iniciativas PDZE con los filtros aplicados.</p>
        ) : (
          <ul className="pdze-list">
            {iniciativasFiltradas.map(item => {
              const cat = classifyPdzeItem(item)
              const saved = isCifraInMinuta(`pdze-inic-${item.id}`)
              return (
                <li key={item.id} className="pdze-item-card">
                  <div className="pdze-item-top">
                    <div className="pdze-item-badges">
                      <span className="pdze-tag-pill">PDZE 2026–2035</span>
                      <span className="proy-row-cat-tag" style={{ background: cat.softBg, color: cat.color }}>
                        <i style={{ background: cat.color }} aria-hidden="true" />
                        {cat.shortLabel}
                      </span>
                      <span className="pdze-meta-chip">{item.comuna}</span>
                      {item.codigo_bip && <span className="mono pdze-bip-code">BIP {item.codigo_bip}</span>}
                    </div>
                    <span className="pdze-horizon-pill">
                      {item.anio_inicio === item.anio_termino ? item.anio_inicio : `${item.anio_inicio}–${item.anio_termino}`}
                    </span>
                  </div>

                  <div className="pdze-item-main">
                    <div>
                      <h4 className="pdze-item-title">{formatProjectDisplayName(item.nombre)}</h4>
                      <p className="pdze-item-inst">Responsable: <strong>{item.instituciones.join(' · ')}</strong></p>
                    </div>
                    <div className="pdze-item-total">
                      <small>Inversión total PDZE</small>
                      <strong>{fmtMillones(item.monto_total_millones)}</strong>
                    </div>
                  </div>

                  {/* Etapas y desglose de financiamiento */}
                  <div className="pdze-etapas-row">
                    {item.etapas.map((et, idx) => (
                      <span key={`${et.etapa}-${idx}`} className="pdze-etapa-chip">
                        <strong>{et.etapa}</strong> ({et.anio_inicio}–{et.anio_termino}): {fmtMillonesCorto(et.monto_total_millones)}
                      </span>
                    ))}
                  </div>

                  <div className="pdze-item-foot">
                    <div className="pdze-funding-split">
                      {item.monto_sectorial_millones > 0 && (
                        <span>Sectorial: <strong>{fmtMillonesCorto(item.monto_sectorial_millones)}</strong></span>
                      )}
                      {item.monto_gore_millones > 0 && (
                        <span>GORE FNDR: <strong>{fmtMillonesCorto(item.monto_gore_millones)}</strong></span>
                      )}
                      {item.monto_subdere_millones > 0 && (
                        <span>SUBDERE PDZE: <strong>{fmtMillonesCorto(item.monto_subdere_millones)}</strong></span>
                      )}
                      <span className="subtle">Pág. {item.pagina_documento} del plan oficial</span>
                    </div>

                    <button
                      type="button"
                      className={`minuta-add-btn${saved ? ' is-saved' : ''}`}
                      aria-pressed={saved}
                      onClick={() => onToggleMinutaCifra(cifraFromPdzeIniciativa(item))}
                    >
                      <span>{saved ? '✓' : '+'}</span> {saved ? 'En minuta' : 'Agregar a minuta'}
                    </button>
                  </div>
                </li>
              )
            })}
          </ul>
        )}
      </section>

      <details className="aysen-details">
        <summary>Ver respaldo oficial y nota técnica del documento PDZE</summary>
        <div className="aysen-details-body">
          <p className="subtle">{plan.nota_auditoria_documento}</p>
          <p className="subtle">
            Documento fuente: <strong>{plan.titulo}</strong> · {plan.resolucion} · {plan.acuerdo_core}.
          </p>
        </div>
      </details>
    </section>
  )
}
