import { requestApiJson, toNumberOrNull } from './bcchService'
import type { FuenteTrazabilidad } from './bcchService'

export const REGIONES_CHILE: readonly { codigo: string; nombre: string }[] = [
  { codigo: '15', nombre: 'Arica y Parinacota' },
  { codigo: '01', nombre: 'Tarapacá' },
  { codigo: '02', nombre: 'Antofagasta' },
  { codigo: '03', nombre: 'Atacama' },
  { codigo: '04', nombre: 'Coquimbo' },
  { codigo: '05', nombre: 'Valparaíso' },
  { codigo: '13', nombre: 'Metropolitana de Santiago' },
  { codigo: '06', nombre: "Libertador General Bernardo O'Higgins" },
  { codigo: '07', nombre: 'Maule' },
  { codigo: '16', nombre: 'Ñuble' },
  { codigo: '08', nombre: 'Biobío' },
  { codigo: '09', nombre: 'La Araucanía' },
  { codigo: '14', nombre: 'Los Ríos' },
  { codigo: '10', nombre: 'Los Lagos' },
  { codigo: '11', nombre: 'Aysén del General Carlos Ibáñez del Campo' },
  { codigo: '12', nombre: 'Magallanes y de la Antártica Chilena' },
] as const

export const NOMBRE_TERRITORIO_POR_CODIGO: Record<string, string> = {
  CL: 'Chile (Total Nacional)',
  ...Object.fromEntries(REGIONES_CHILE.map(r => [r.codigo, r.nombre])),
}

export function nombreTerritorio(codigo: string, fallback?: string | null): string {
  if (fallback && fallback.trim()) return fallback.trim()
  return NOMBRE_TERRITORIO_POR_CODIGO[codigo] ?? codigo
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null
}

function asString(value: unknown): string | null {
  return typeof value === 'string' && value.trim().length > 0 ? value.trim() : null
}

function asStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) return []
  return value
    .map(item => (typeof item === 'string' ? item.trim() : item !== null && item !== undefined ? String(item) : ''))
    .filter(Boolean)
}

function normalizeFuenteFase2(
  raw: unknown,
  fallbackInstitucion: string,
  fallbackEndpoint: string,
): FuenteTrazabilidad {
  const f = asRecord(raw) ?? {}
  const series = Array.isArray(f.series_consultadas)
    ? f.series_consultadas.map(String)
    : Array.isArray(f.codigos_series)
      ? f.codigos_series.map(String)
      : null
  return {
    institucion: asString(f.institucion) ?? fallbackInstitucion,
    sistema: asString(f.sistema),
    endpoint: asString(f.endpoint) ?? fallbackEndpoint,
    codigo_serie: asString(f.codigo_serie),
    codigos_series: series,
    series_consultadas: series,
    actualizado_en: asString(f.actualizado_en) ?? asString(f.corte),
    extraido_en: asString(f.extraido_en) ?? asString(f.fecha_extraccion),
    corte: asString(f.corte) ?? asString(f.publicacion),
    unidad: asString(f.unidad) ?? asString(f.unidad_salida),
    nota: asString(f.nota) ?? asString(f.notas),
    desde_cache: typeof f.desde_cache === 'boolean' ? f.desde_cache : undefined,
  }
}

/* ============================================================================
   1. ESTRUCTURA PRODUCTIVA Y ESPECIALIZACIÓN (416 SERIES · 16 REGIONES)
   GET /api/v1/sectorial/regiones
============================================================================ */

export interface ActividadSectorial {
  codigo: string
  nombre: string
  valor_nominal_millones: number | null
  participacion_nominal_pct: number | null
  lq: number | null
  especializada: boolean
  valor_real_millones: number | null
  crecimiento_real_pct: number | null
  serie_nominal: string | null
  serie_real: string | null
  estado: string | null
}

export interface RegionSectorial {
  codigo: string
  nombre: string
  anio: number
  vab_nominal_millones: number | null
  pib_nominal_millones: number | null
  diferencia_impuestos_millones: number | null
  hhi: number | null
  diversificacion: number | null
  krugman: number | null
  sector_mas_especializado: {
    codigo: string
    nombre: string
    lq: number
  } | null
  actividades: ActividadSectorial[]
}

export interface RankingRegionalSectorial {
  codigo: string
  nombre: string
  hhi: number | null
  diversificacion: number | null
  krugman: number | null
  vab_nominal_millones: number | null
  sector_principal: string | null
  sector_principal_pct: number | null
  sector_mas_especializado: string | null
  max_lq: number | null
}

export interface SectorialRegionesResponse {
  anio: number
  anios_disponibles: number[]
  total_series: number
  regiones: RegionSectorial[]
  ranking_hhi: RankingRegionalSectorial[]
  ranking_krugman: RankingRegionalSectorial[]
  notas_metodologicas: string[]
  fuente_trazabilidad: FuenteTrazabilidad
  actualizado_en: string | null
  extraido_en: string | null
  estado_actualizacion: string | null
}

function parseActividad(raw: Record<string, unknown>): ActividadSectorial {
  const codigo = asString(raw.actividad_id ?? raw.codigo_actividad ?? raw.codigo ?? raw.actividad ?? raw.clave) ?? ''
  const nombre = asString(raw.nombre ?? raw.actividad_nombre ?? raw.titulo ?? raw.glosa ?? codigo) ?? 'Actividad'
  const lq = toNumberOrNull(
    raw.lq ?? raw.lq_especializacion ?? raw.cociente_localizacion ?? raw.coeficiente_localizacion ?? raw.especializacion_lq,
  )
  return {
    codigo: codigo || nombre,
    nombre,
    valor_nominal_millones: toNumberOrNull(
      raw.valor_nominal_millones ?? raw.nominal_millones ?? raw.vab_nominal_millones ?? raw.valor_millones,
    ),
    participacion_nominal_pct: toNumberOrNull(
      raw.participacion_nominal_pct ?? raw.participacion_pct ?? raw.participacion_vab_pct ?? raw.participacion,
    ),
    lq,
    especializada: typeof raw.especializada === 'boolean' ? raw.especializada : (lq !== null && lq > 1),
    valor_real_millones: toNumberOrNull(
      raw.valor_real_millones ?? raw.real_millones ?? raw.vab_real_millones,
    ),
    crecimiento_real_pct: toNumberOrNull(
      raw.crecimiento_real_pct ?? raw.variacion_real_pct ?? raw.crecimiento_real_anual_pct ?? raw.crecimiento_pct,
    ),
    serie_nominal: asString(raw.serie_nominal ?? raw.serie_bde_nominal ?? raw.serie_id_nominal ?? raw.serie_bde ?? raw.serie_id),
    serie_real: asString(raw.serie_real ?? raw.serie_bde_real ?? raw.serie_id_real),
    estado: asString(raw.estado),
  }
}

function parseRegionSectorial(
  raw: Record<string, unknown>,
  defaultAnio: number,
  fallbackCode?: string,
): RegionSectorial {
  const codigo = asString(raw.codigo ?? raw.territorio ?? raw.region_codigo ?? fallbackCode) ?? ''
  const nombre = nombreTerritorio(codigo, asString(raw.nombre ?? raw.region_nombre ?? raw.territorio_nombre))
  const anioRaw = toNumberOrNull(raw.anio)
  const anio = anioRaw !== null ? Math.trunc(anioRaw) : defaultAnio

  const rawActividades = Array.isArray(raw.actividades)
    ? raw.actividades
    : Array.isArray(raw.sectores)
      ? raw.sectores
      : []

  const actividades: ActividadSectorial[] = rawActividades
    .map(item => asRecord(item))
    .filter((item): item is Record<string, unknown> => item !== null)
    .map(parseActividad)

  const vabFromActs = actividades.reduce<number | null>((acc, item) => {
    if (item.valor_nominal_millones === null) return acc
    return (acc ?? 0) + item.valor_nominal_millones
  }, null)

  const vabNominal = toNumberOrNull(
    raw.vab_nominal_millones ?? raw.total_vab_nominal_millones ?? raw.suma_actividades_nominal_millones ?? raw.vab_total_millones ?? raw.total_nominal_millones,
  ) ?? vabFromActs

  const pibNominal = toNumberOrNull(raw.pib_nominal_millones ?? raw.pib_total_nominal_millones)
  const diffImp = toNumberOrNull(raw.diferencia_impuestos_millones ?? raw.diferencia_impuestos_productos_millones)
    ?? (pibNominal !== null && vabNominal !== null ? pibNominal - vabNominal : null)

  const hhiObj = asRecord(raw.hhi) ?? asRecord(raw.concentracion_hhi)
  const hhi = toNumberOrNull(
    hhiObj?.valor ?? hhiObj?.indice ?? raw.hhi ?? raw.hhi_indice ?? raw.indice_hhi,
  )

  const divRaw = toNumberOrNull(raw.diversificacion ?? raw.indice_diversificacion)
  const diversificacion = divRaw !== null ? divRaw : (hhi !== null ? Math.max(0, 1 - hhi / 10000) : null)

  const krugmanObj = asRecord(raw.krugman) ?? asRecord(raw.indice_krugman)
  const krugman = toNumberOrNull(
    krugmanObj?.valor ?? krugmanObj?.indice ?? raw.krugman ?? raw.indice_krugman,
  )

  const maxSpecObj = asRecord(raw.sector_mas_especializado_lq ?? raw.sector_mas_especializado ?? raw.actividad_mas_especializada)
  let sectorMasEspecializado: RegionSectorial['sector_mas_especializado'] = null
  const maxSpecLq = maxSpecObj ? toNumberOrNull(maxSpecObj.lq ?? maxSpecObj.lq_especializacion) : null
  if (maxSpecObj && maxSpecLq !== null) {
    sectorMasEspecializado = {
      codigo: asString(maxSpecObj.actividad_id ?? maxSpecObj.codigo) ?? '',
      nombre: asString(maxSpecObj.nombre ?? maxSpecObj.actividad) ?? 'Actividad',
      lq: maxSpecLq,
    }
  } else {
    const withLq = actividades.filter(a => a.lq !== null)
    if (withLq.length > 0) {
      const top = [...withLq].sort((a, b) => (b.lq ?? -Infinity) - (a.lq ?? -Infinity))[0]
      sectorMasEspecializado = {
        codigo: top.codigo,
        nombre: top.nombre,
        lq: top.lq!,
      }
    }
  }

  return {
    codigo,
    nombre,
    anio,
    vab_nominal_millones: vabNominal,
    pib_nominal_millones: pibNominal,
    diferencia_impuestos_millones: diffImp,
    hhi,
    diversificacion,
    krugman,
    sector_mas_especializado: sectorMasEspecializado,
    actividades,
  }
}

function buildRankingFromRegions(regiones: RegionSectorial[]): RankingRegionalSectorial[] {
  return regiones.map(reg => {
    const sortedByShare = [...reg.actividades]
      .filter(a => a.participacion_nominal_pct !== null)
      .sort((a, b) => (b.participacion_nominal_pct ?? -Infinity) - (a.participacion_nominal_pct ?? -Infinity))
    const principal = sortedByShare[0]
    return {
      codigo: reg.codigo,
      nombre: reg.nombre,
      hhi: reg.hhi,
      diversificacion: reg.diversificacion,
      krugman: reg.krugman,
      vab_nominal_millones: reg.vab_nominal_millones,
      sector_principal: principal?.nombre ?? null,
      sector_principal_pct: principal?.participacion_nominal_pct ?? null,
      sector_mas_especializado: reg.sector_mas_especializado?.nombre ?? null,
      max_lq: reg.sector_mas_especializado?.lq ?? null,
    }
  })
}

function parseRankingList(raw: unknown): RankingRegionalSectorial[] {
  if (!Array.isArray(raw)) return []
  return raw
    .map(item => asRecord(item))
    .filter((item): item is Record<string, unknown> => item !== null)
    .map(item => {
      const codigo = asString(item.codigo ?? item.territorio ?? item.region_codigo) ?? ''
      const hhi = toNumberOrNull(item.hhi ?? item.indice_hhi)
      const divRaw = toNumberOrNull(item.diversificacion)
      return {
        codigo,
        nombre: nombreTerritorio(codigo, asString(item.nombre ?? item.region_nombre)),
        hhi,
        diversificacion: divRaw !== null ? divRaw : (hhi !== null ? Math.max(0, 1 - hhi / 10000) : null),
        krugman: toNumberOrNull(item.krugman ?? item.indice_krugman),
        vab_nominal_millones: toNumberOrNull(item.vab_nominal_millones ?? item.vab_total_millones),
        sector_principal: asString(item.sector_principal),
        sector_principal_pct: toNumberOrNull(item.sector_principal_pct),
        sector_mas_especializado: asString(item.sector_mas_especializado ?? item.actividad_mas_especializada),
        max_lq: toNumberOrNull(item.max_lq ?? item.lq_maximo ?? item.lq),
      }
    })
    .filter(item => item.codigo.length > 0)
}

export async function fetchSectorialRegiones(
  anio?: number,
  territorio?: string,
  signal?: AbortSignal,
): Promise<SectorialRegionesResponse> {
  const params = new URLSearchParams()
  if (anio !== undefined) params.set('anio', String(anio))
  if (territorio && territorio.trim()) params.set('territorio', territorio.trim())
  const qs = params.toString()
  const path = `/sectorial/regiones${qs ? `?${qs}` : ''}`
  const raw = await requestApiJson<Record<string, unknown>>(path, { signal })

  const pubObj = asRecord(raw.publicacion)
  const porAnioObj = asRecord(raw.por_anio)
  const aniosRaw = Array.isArray(raw.anios_disponibles)
    ? raw.anios_disponibles
    : Array.isArray(raw.anios)
      ? raw.anios
      : Array.isArray(pubObj?.anios)
        ? (pubObj!.anios as unknown[])
        : porAnioObj
          ? Object.keys(porAnioObj)
          : []
  const aniosDisponibles = aniosRaw
    .map(v => toNumberOrNull(v))
    .filter((v): v is number => v !== null)
    .map(v => Math.trunc(v))
    .sort((a, b) => a - b)

  const anioRes = Math.trunc(
    toNumberOrNull(raw.anio ?? raw.ultimo_anio ?? anio) ??
    (aniosDisponibles.length > 0 ? aniosDisponibles[aniosDisponibles.length - 1] : 2025),
  )

  // El backend fase2.py entrega los cortes anidados bajo por_anio[String(anio)]
  const bloqueAnio = porAnioObj
    ? (asRecord(porAnioObj[String(anioRes)]) ??
      asRecord(porAnioObj[Object.keys(porAnioObj).sort().slice(-1)[0]]))
    : null
  const fuenteRegiones = bloqueAnio?.regiones ?? raw.regiones

  const regiones: RegionSectorial[] = []
  if (Array.isArray(fuenteRegiones)) {
    for (const item of fuenteRegiones) {
      const rec = asRecord(item)
      if (rec) regiones.push(parseRegionSectorial(rec, anioRes))
    }
  } else if (asRecord(fuenteRegiones)) {
    for (const [code, val] of Object.entries(asRecord(fuenteRegiones)!)) {
      const rec = asRecord(val)
      if (rec) regiones.push(parseRegionSectorial(rec, anioRes, code))
    }
  } else if (asRecord(raw.region)) {
    regiones.push(parseRegionSectorial(asRecord(raw.region)!, anioRes, territorio))
  } else if (Array.isArray(raw.datos)) {
    for (const item of raw.datos) {
      const rec = asRecord(item)
      if (rec) regiones.push(parseRegionSectorial(rec, anioRes))
    }
  }

  const baseRanking = buildRankingFromRegions(regiones)
  const baseByCode = new Map(baseRanking.map(r => [r.codigo, r]))
  const enrichRanking = (items: RankingRegionalSectorial[]) =>
    items.map(it => {
      const b = baseByCode.get(it.codigo)
      if (!b) return it
      return {
        ...b,
        ...it,
        hhi: it.hhi ?? b.hhi,
        diversificacion: it.diversificacion ?? b.diversificacion,
        krugman: it.krugman ?? b.krugman,
        vab_nominal_millones: it.vab_nominal_millones ?? b.vab_nominal_millones,
        sector_principal: it.sector_principal ?? b.sector_principal,
        sector_principal_pct: it.sector_principal_pct ?? b.sector_principal_pct,
        sector_mas_especializado: it.sector_mas_especializado ?? b.sector_mas_especializado,
        max_lq: it.max_lq ?? b.max_lq,
      }
    })
  const rawRankingHhi = enrichRanking(parseRankingList(bloqueAnio?.ranking_hhi ?? raw.ranking_hhi))
  const rawRankingKrugman = enrichRanking(parseRankingList(bloqueAnio?.ranking_krugman ?? raw.ranking_krugman))

  const rankingHhi = rawRankingHhi.length > 0
    ? rawRankingHhi
    : [...baseRanking].sort((a, b) => (b.hhi ?? -Infinity) - (a.hhi ?? -Infinity))

  const rankingKrugman = rawRankingKrugman.length > 0
    ? rawRankingKrugman
    : [...baseRanking].sort((a, b) => (b.krugman ?? -Infinity) - (a.krugman ?? -Infinity))

  const fuente = normalizeFuenteFase2(
    raw.fuente_trazabilidad,
    'Banco Central de Chile (BCCh-BDE · 416 series sectoriales)',
    `/api/v1${path}`,
  )

  return {
    anio: anioRes,
    anios_disponibles: aniosDisponibles.length > 0 ? aniosDisponibles : Array.from({ length: 13 }, (_, i) => 2013 + i),
    total_series: Math.trunc(toNumberOrNull(raw.total_series ?? raw.series_totales ?? pubObj?.series_totales) ?? 416),
    regiones,
    ranking_hhi: rankingHhi,
    ranking_krugman: rankingKrugman,
    notas_metodologicas: asStringArray(raw.notas_metodologicas ?? raw.notas ?? pubObj?.notas),
    fuente_trazabilidad: fuente,
    actualizado_en: asString(raw.actualizado_en ?? pubObj?.fecha) ?? fuente.actualizado_en ?? null,
    extraido_en: asString(raw.extraido_en ?? pubObj?.fecha) ?? fuente.extraido_en ?? null,
    estado_actualizacion: asString(raw.estado_actualizacion),
  }
}

/* ============================================================================
   2. DEMOGRAFÍA INE, PIB PER CÁPITA Y SIGMA-CONVERGENCIA
   GET /api/v1/demografia/poblacion
============================================================================ */

export interface ObservacionPerCapita {
  territorio: string
  nombre: string
  anio: number
  poblacion: number | null
  pib_nominal_millones: number | null
  pib_real_millones: number | null
  pib_per_capita_nominal_clp: number | null
  pib_per_capita_real_clp: number | null
  indice_nominal_chile_100: number | null
  indice_real_chile_100: number | null
  serie_poblacion: string | null
  serie_pib_nominal: string | null
  serie_pib_real: string | null
  estado: string | null
}

export interface SigmaConvergenciaPunto {
  anio: number
  cv_real_pct: number | null
  cv_nominal_pct: number | null
  desviacion_std_real_clp: number | null
  media_real_clp: number | null
  regiones_incluidas: number | null
}

export interface DemografiaPoblacionResponse {
  anios_disponibles: number[]
  ultimo_anio: number
  total_series: number
  observaciones: ObservacionPerCapita[]
  sigma_convergencia: SigmaConvergenciaPunto[]
  advertencia_comunal: string
  fuente_trazabilidad: FuenteTrazabilidad
  actualizado_en: string | null
  extraido_en: string | null
  estado_actualizacion: string | null
}

function normalizePerCapitaToClp(
  directClp: number | null,
  millonesPerCapita: number | null,
  milesPerCapita: number | null,
  pibMillones: number | null,
  poblacion: number | null,
): number | null {
  if (directClp !== null) return directClp
  if (millonesPerCapita !== null) return millonesPerCapita * 1_000_000
  if (milesPerCapita !== null) return milesPerCapita * 1_000
  if (pibMillones !== null && poblacion !== null && poblacion > 0) {
    return (pibMillones * 1_000_000) / poblacion
  }
  return null
}

function normalizeCvPct(rawVal: number | null, isAlreadyPct: boolean): number | null {
  if (rawVal === null) return null
  if (isAlreadyPct) return rawVal
  // Si el coeficiente de variación viene en proporción (ej. 0.42), convertir a porcentaje (42.0%)
  return rawVal <= 2.5 ? rawVal * 100 : rawVal
}

export async function fetchDemografiaPoblacion(
  anioDesde?: number,
  anioHasta?: number,
  signal?: AbortSignal,
): Promise<DemografiaPoblacionResponse> {
  const params = new URLSearchParams()
  if (anioDesde !== undefined) params.set('anio_desde', String(anioDesde))
  if (anioHasta !== undefined) params.set('anio_hasta', String(anioHasta))
  const qs = params.toString()
  const path = `/demografia/poblacion${qs ? `?${qs}` : ''}`
  const raw = await requestApiJson<Record<string, unknown>>(path, { signal })

  const rawObsList: Record<string, unknown>[] = []
  // Soporta formato oficial fase2.py: raw.pib_per_capita.por_anio[anio].territorios[code]
  const pibPcObj = asRecord(raw.pib_per_capita)
  const pibPcPorAnio = asRecord(pibPcObj?.por_anio)
  if (pibPcPorAnio) {
    for (const [anioKey, bloque] of Object.entries(pibPcPorAnio)) {
      const bloqueRec = asRecord(bloque)
      const terrs = asRecord(bloqueRec?.territorios)
      if (!terrs) continue
      for (const [code, val] of Object.entries(terrs)) {
        const rec = asRecord(val)
        if (rec) {
          rawObsList.push({ ...rec, territorio: rec.territorio ?? code, anio: rec.anio ?? Number(anioKey) })
        }
      }
    }
  }
  const candidates = rawObsList.length === 0 ? [raw.observaciones, raw.pib_per_capita, raw.datos, raw.series] : []
  for (const list of candidates) {
    if (Array.isArray(list)) {
      for (const item of list) {
        const rec = asRecord(item)
        if (!rec) continue
        // Soporta formato anidado por territorio con array `anios`/`observaciones`
        if (Array.isArray(rec.observaciones) || Array.isArray(rec.serie)) {
          const inner = (Array.isArray(rec.observaciones) ? rec.observaciones : rec.serie) as unknown[]
          const terr = asString(rec.territorio ?? rec.codigo) ?? ''
          const nom = asString(rec.nombre ?? rec.territorio_nombre)
          const seriePob = asString(rec.serie_poblacion ?? rec.serie_bde ?? rec.serie_id)
          for (const sub of inner) {
            const subRec = asRecord(sub)
            if (subRec) {
              rawObsList.push({
                ...subRec,
                territorio: subRec.territorio ?? terr,
                nombre: subRec.nombre ?? nom,
                serie_poblacion: subRec.serie_poblacion ?? seriePob,
              })
            }
          }
        } else {
          rawObsList.push(rec)
        }
      }
      if (rawObsList.length > 0) break
    }
  }

  const obsMap = new Map<string, ObservacionPerCapita>()
  for (const item of rawObsList) {
    const territorio = asString(item.territorio ?? item.codigo ?? item.region_codigo) ?? ''
    const anioVal = toNumberOrNull(item.anio)
    if (!territorio || anioVal === null) continue
    const anio = Math.trunc(anioVal)

    const poblacion = toNumberOrNull(item.poblacion ?? item.poblacion_ine ?? item.habitantes)
    const pibNom = toNumberOrNull(item.pib_nominal_millones ?? item.pib_nominal)
    const pibReal = toNumberOrNull(item.pib_real_millones ?? item.pib_real)

    const pcNomClp = normalizePerCapitaToClp(
      toNumberOrNull(
        item.pib_per_capita_nominal_clp ?? item.pib_nominal_per_capita_clp ?? item.pib_pc_nominal_clp ?? item.per_capita_nominal_clp,
      ),
      toNumberOrNull(item.pib_per_capita_nominal_millones ?? item.pib_pc_nominal_millones),
      toNumberOrNull(item.pib_per_capita_nominal_miles ?? item.pib_pc_nominal_miles),
      pibNom,
      poblacion,
    )

    const pcRealClp = normalizePerCapitaToClp(
      toNumberOrNull(
        item.pib_per_capita_real_clp ?? item.pib_real_per_capita_clp ?? item.pib_pc_real_clp ?? item.per_capita_real_clp,
      ),
      toNumberOrNull(item.pib_per_capita_real_millones ?? item.pib_pc_real_millones),
      toNumberOrNull(item.pib_per_capita_real_miles ?? item.pib_pc_real_miles),
      pibReal,
      poblacion,
    )

    obsMap.set(`${territorio}/${anio}`, {
      territorio,
      nombre: nombreTerritorio(territorio, asString(item.nombre ?? item.nombre_territorio ?? item.territorio_nombre ?? item.region_nombre)),
      anio,
      poblacion,
      pib_nominal_millones: pibNom,
      pib_real_millones: pibReal,
      pib_per_capita_nominal_clp: pcNomClp,
      pib_per_capita_real_clp: pcRealClp,
      indice_nominal_chile_100: toNumberOrNull(item.indice_nominal_chile_100 ?? item.ratio_vs_chile_nominal ?? item.razon_nominal_chile_100),
      indice_real_chile_100: toNumberOrNull(item.indice_real_chile_100 ?? item.ratio_vs_chile_real ?? item.razon_real_chile_100),
      serie_poblacion: asString(item.serie_poblacion ?? item.serie_bde_poblacion),
      serie_pib_nominal: asString(item.serie_pib_nominal),
      serie_pib_real: asString(item.serie_pib_real),
      estado: asString(item.estado ?? item.estado_real),
    })
  }

  // Completar índice Chile = 100 si el backend no lo entrega precalculado
  const chileByYear = new Map<number, ObservacionPerCapita>()
  for (const obs of obsMap.values()) {
    if (obs.territorio === 'CL') chileByYear.set(obs.anio, obs)
  }
  const observaciones: ObservacionPerCapita[] = Array.from(obsMap.values()).map(obs => {
    const cl = chileByYear.get(obs.anio)
    const idxNom = obs.indice_nominal_chile_100 ?? (
      obs.pib_per_capita_nominal_clp !== null && cl?.pib_per_capita_nominal_clp && cl.pib_per_capita_nominal_clp > 0
        ? (obs.pib_per_capita_nominal_clp / cl.pib_per_capita_nominal_clp) * 100
        : null
    )
    const idxReal = obs.indice_real_chile_100 ?? (
      obs.pib_per_capita_real_clp !== null && cl?.pib_per_capita_real_clp && cl.pib_per_capita_real_clp > 0
        ? (obs.pib_per_capita_real_clp / cl.pib_per_capita_real_clp) * 100
        : null
    )
    return {
      ...obs,
      indice_nominal_chile_100: idxNom,
      indice_real_chile_100: idxReal,
    }
  })

  // Parseo de sigma-convergencia
  const sigmaRaw = raw.sigma_convergencia ?? raw.convergencia ?? raw.convergencia_sigma
  const sigmaList: SigmaConvergenciaPunto[] = []
  if (Array.isArray(sigmaRaw)) {
    for (const item of sigmaRaw) {
      const rec = asRecord(item)
      if (!rec) continue
      const anioVal = toNumberOrNull(rec.anio)
      if (anioVal === null) continue
      const cvRealPctRaw = toNumberOrNull(rec.cv_real_pct ?? rec.coeficiente_variacion_real_pct)
      const cvRealDecRaw = toNumberOrNull(rec.cv_real ?? rec.coeficiente_variacion_real ?? rec.cv)
      const cvNomPctRaw = toNumberOrNull(rec.cv_nominal_pct ?? rec.coeficiente_variacion_nominal_pct)
      const cvNomDecRaw = toNumberOrNull(rec.cv_nominal ?? rec.coeficiente_variacion_nominal)
      sigmaList.push({
        anio: Math.trunc(anioVal),
        cv_real_pct: cvRealPctRaw !== null ? cvRealPctRaw : normalizeCvPct(cvRealDecRaw, false),
        cv_nominal_pct: cvNomPctRaw !== null ? cvNomPctRaw : normalizeCvPct(cvNomDecRaw, false),
        desviacion_std_real_clp: toNumberOrNull(rec.desviacion_std_real_clp ?? rec.desviacion_estandar_real),
        media_real_clp: toNumberOrNull(rec.media_real_clp ?? rec.promedio_real),
        regiones_incluidas: toNumberOrNull(rec.regiones_incluidas ?? rec.n_regiones) !== null
          ? Math.trunc(toNumberOrNull(rec.regiones_incluidas ?? rec.n_regiones)!)
          : null,
      })
    }
  } else if (asRecord(sigmaRaw)) {
    const sr = asRecord(sigmaRaw)!
    const innerSeries = Array.isArray(sr.serie) ? sr.serie : Array.isArray(sr.anios) ? sr.anios : null
    if (innerSeries) {
      for (const item of innerSeries) {
        const rec = asRecord(item)
        if (!rec) continue
        const anioVal = toNumberOrNull(rec.anio)
        if (anioVal === null) continue
        const cvRealPctRaw = toNumberOrNull(rec.cv_real_pct ?? rec.coeficiente_variacion_real_pct)
        const cvRealDecRaw = toNumberOrNull(rec.cv_real ?? rec.coeficiente_variacion_real ?? rec.cv)
        const cvNomPctRaw = toNumberOrNull(rec.cv_nominal_pct ?? rec.coeficiente_variacion_nominal_pct)
        const cvNomDecRaw = toNumberOrNull(rec.cv_nominal ?? rec.coeficiente_variacion_nominal)
        sigmaList.push({
          anio: Math.trunc(anioVal),
          cv_real_pct: cvRealPctRaw !== null ? cvRealPctRaw : normalizeCvPct(cvRealDecRaw, false),
          cv_nominal_pct: cvNomPctRaw !== null ? cvNomPctRaw : normalizeCvPct(cvNomDecRaw, false),
          desviacion_std_real_clp: toNumberOrNull(rec.desviacion_std_real_clp ?? rec.desviacion_estandar_real_clp ?? rec.desviacion_estandar_real),
          media_real_clp: toNumberOrNull(rec.media_real_clp ?? rec.media_regional_real_clp ?? rec.promedio_real),
          regiones_incluidas: toNumberOrNull(rec.regiones_incluidas ?? rec.n_regiones) !== null
            ? Math.trunc(toNumberOrNull(rec.regiones_incluidas ?? rec.n_regiones)!)
            : null,
        })
      }
    } else {
      // Diccionario indexado por año ("2013".."2025") tal como lo entrega fase2.py
      for (const [key, val] of Object.entries(sr)) {
        const rec = asRecord(val)
        const anioVal = toNumberOrNull(rec?.anio ?? key)
        if (!rec || anioVal === null) continue
        const cvRealPctRaw = toNumberOrNull(rec.cv_real_pct ?? rec.coeficiente_variacion_real_pct)
        const cvRealDecRaw = toNumberOrNull(rec.cv_real ?? rec.coeficiente_variacion_real ?? rec.cv)
        const cvNomPctRaw = toNumberOrNull(rec.cv_nominal_pct ?? rec.coeficiente_variacion_nominal_pct)
        const cvNomDecRaw = toNumberOrNull(rec.cv_nominal ?? rec.coeficiente_variacion_nominal)
        sigmaList.push({
          anio: Math.trunc(anioVal),
          cv_real_pct: cvRealPctRaw !== null ? cvRealPctRaw : normalizeCvPct(cvRealDecRaw, false),
          cv_nominal_pct: cvNomPctRaw !== null ? cvNomPctRaw : normalizeCvPct(cvNomDecRaw, false),
          desviacion_std_real_clp: toNumberOrNull(rec.desviacion_std_real_clp ?? rec.desviacion_estandar_real_clp ?? rec.desviacion_estandar_real),
          media_real_clp: toNumberOrNull(rec.media_real_clp ?? rec.media_regional_real_clp ?? rec.promedio_real),
          regiones_incluidas: toNumberOrNull(rec.regiones_incluidas ?? rec.n_regiones) !== null
            ? Math.trunc(toNumberOrNull(rec.regiones_incluidas ?? rec.n_regiones)!)
            : null,
        })
      }
    }
  }

  // Si no viene sigma_convergencia pero sí observaciones regionales, derivar CV poblacional entre 16 regiones por año
  const yearsSet = new Set<number>(observaciones.map(o => o.anio))
  const aniosDisponibles = Array.from(yearsSet).sort((a, b) => a - b)
  if (sigmaList.length === 0 && aniosDisponibles.length > 0) {
    for (const yr of aniosDisponibles) {
      const regYear = observaciones.filter(o => o.anio === yr && o.territorio !== 'CL')
      const reals = regYear.map(o => o.pib_per_capita_real_clp).filter((v): v is number => v !== null && v > 0)
      const noms = regYear.map(o => o.pib_per_capita_nominal_clp).filter((v): v is number => v !== null && v > 0)
      const calcCv = (vals: number[]) => {
        if (vals.length < 2) return { cv: null as number | null, std: null as number | null, mean: null as number | null }
        const mean = vals.reduce((a, b) => a + b, 0) / vals.length
        if (mean <= 0) return { cv: null, std: null, mean }
        const variance = vals.reduce((acc, v) => acc + Math.pow(v - mean, 2), 0) / vals.length
        const std = Math.sqrt(variance)
        return { cv: (std / mean) * 100, std, mean }
      }
      const rStat = calcCv(reals)
      const nStat = calcCv(noms)
      if (rStat.cv !== null || nStat.cv !== null) {
        sigmaList.push({
          anio: yr,
          cv_real_pct: rStat.cv,
          cv_nominal_pct: nStat.cv,
          desviacion_std_real_clp: rStat.std,
          media_real_clp: rStat.mean,
          regiones_incluidas: Math.max(reals.length, noms.length),
        })
      }
    }
  }
  sigmaList.sort((a, b) => a.anio - b.anio)

  const ultimoAnio = Math.trunc(
    toNumberOrNull(raw.ultimo_anio) ??
    (aniosDisponibles.length > 0 ? aniosDisponibles[aniosDisponibles.length - 1] : 2025),
  )

  const fuente = normalizeFuenteFase2(
    raw.fuente_trazabilidad,
    'Banco Central de Chile (BCCh-BDE) + Instituto Nacional de Estadísticas (INE)',
    `/api/v1${path}`,
  )

  return {
    anios_disponibles: aniosDisponibles.length > 0 ? aniosDisponibles : Array.from({ length: 13 }, (_, i) => 2013 + i),
    ultimo_anio: ultimoAnio,
    total_series: Math.trunc(toNumberOrNull(raw.total_series ?? raw.series_totales) ?? 17),
    observaciones,
    sigma_convergencia: sigmaList,
    advertencia_comunal:
      asString(raw.advertencia_comunal ?? raw.advertencia_metodologica) ??
      'Las cifras de PIB son de escala nacional y regional y nunca deben imputarse a las 346 comunas.',
    fuente_trazabilidad: fuente,
    actualizado_en: asString(raw.actualizado_en) ?? fuente.actualizado_en ?? null,
    extraido_en: asString(raw.extraido_en) ?? fuente.extraido_en ?? null,
    estado_actualizacion: asString(raw.estado_actualizacion),
  }
}

/* ============================================================================
   3. RESUMEN DE CRUCES ANALÍTICOS Y DEPENDENCIA ESTATAL
   GET /api/v1/cruces/resumen
============================================================================ */

export interface CruceItemResumen {
  id: string
  titulo: string
  estado: string
  descripcion: string
  hallazgo_principal: string | null
  limitacion: string | null
  metricas: Record<string, unknown>
}

export interface CrucesResumenResponse {
  territorio: string
  cruces: CruceItemResumen[]
  dependencia_estatal: Record<string, unknown> | null
  fuente_trazabilidad: FuenteTrazabilidad
  actualizado_en: string | null
  extraido_en: string | null
}

export async function fetchCrucesResumen(signal?: AbortSignal): Promise<CrucesResumenResponse> {
  const raw = await requestApiJson<Record<string, unknown>>('/cruces/resumen', { signal })
  const rawCruces = Array.isArray(raw.cruces) ? raw.cruces : []
  const cruces: CruceItemResumen[] = rawCruces
    .map(item => asRecord(item))
    .filter((item): item is Record<string, unknown> => item !== null)
    .map((item, idx) => ({
      id: asString(item.id ?? item.codigo) ?? `cruce-${idx + 1}`,
      titulo: asString(item.titulo ?? item.nombre) ?? `Cruce ${idx + 1}`,
      estado: asString(item.estado) ?? 'disponible',
      descripcion: asString(item.descripcion ?? item.resumen) ?? '',
      hallazgo_principal: asString(item.hallazgo_principal ?? item.conclusión ?? item.conclusion),
      limitacion: asString(item.limitacion ?? item.limite_inferencia),
      metricas: asRecord(item.metricas) ?? {},
    }))

  const fuente = normalizeFuenteFase2(
    raw.fuente_trazabilidad,
    'Chile Territorial · Cruces verificados (BCCh + DIPRES + SINIM + INE)',
    '/api/v1/cruces/resumen',
  )

  return {
    territorio: asString(raw.territorio) ?? '11',
    cruces,
    dependencia_estatal: asRecord(raw.dependencia_estatal ?? raw.matriz_dependencia_estatal),
    fuente_trazabilidad: fuente,
    actualizado_en: asString(raw.actualizado_en) ?? fuente.actualizado_en ?? null,
    extraido_en: asString(raw.extraido_en) ?? fuente.extraido_en ?? null,
  }
}

/* ============================================================================
   4. LABORATORIO DE INVESTIGACIÓN Y DOSSIERS (SOLO LECTURA · 10 PASOS)
   POST /api/v1/laboratorio/consultar
============================================================================ */

export interface DossierFuenteVerificada {
  institucion: string
  sistema?: string | null
  corte?: string | null
  endpoint?: string | null
  series?: string[]
}

export interface DossierMetrica {
  nombre: string
  valor: string
  unidad?: string | null
  periodo?: string | null
  fuente?: string | null
  serie?: string | null
}

export interface DossierTablaEvidencia {
  titulo?: string | null
  columnas: string[]
  filas: string[][]
}

export interface DossierPaso {
  numero: number
  titulo: string
  contenido: string
}

export interface LaboratorioConsultaResponse {
  id_consulta: string
  generado_en: string
  territorio: string
  territorio_nombre: string
  pregunta: string
  solo_lectura: boolean
  motor: string
  fuentes_verificadas: DossierFuenteVerificada[]
  hipotesis_y_metodo: string
  metricas_reproducibles: DossierMetrica[]
  tabla_evidencia: DossierTablaEvidencia | null
  evidencia_favorable: string[]
  hipotesis_alternativas: string[]
  interpretacion: string
  limitaciones_metodologicas: string[]
  pasos: DossierPaso[]
  dossier_markdown: string | null
  dossier_html: string | null
  fuente_trazabilidad: FuenteTrazabilidad
}

function normalizeTablaEvidencia(raw: unknown): DossierTablaEvidencia | null {
  if (!raw) return null
  if (Array.isArray(raw) && raw.length > 0) {
    const first = asRecord(raw[0])
    if (first) {
      const columnas = Object.keys(first)
      const filas = raw
        .map(item => asRecord(item))
        .filter((item): item is Record<string, unknown> => item !== null)
        .map(row => columnas.map(col => (row[col] === null || row[col] === undefined ? '—' : String(row[col]))))
      return { titulo: 'Evidencia tabular verificada', columnas, filas }
    }
    return null
  }

  const rec = asRecord(raw)
  if (!rec) return null
  const rawCols = Array.isArray(rec.columnas) ? rec.columnas.map(String) : []
  const rawRows = Array.isArray(rec.filas) ? rec.filas : Array.isArray(rec.rows) ? rec.rows : []

  if (rawCols.length === 0 && rawRows.length > 0 && asRecord(rawRows[0])) {
    const cols = Object.keys(asRecord(rawRows[0])!)
    const filas = rawRows
      .map(r => asRecord(r))
      .filter((r): r is Record<string, unknown> => r !== null)
      .map(r => cols.map(c => (r[c] === null || r[c] === undefined ? '—' : String(r[c]))))
    return { titulo: asString(rec.titulo), columnas: cols, filas }
  }

  const filas: string[][] = rawRows.map(row => {
    if (Array.isArray(row)) {
      return row.map(cell => (cell === null || cell === undefined ? '—' : String(cell)))
    }
    const r = asRecord(row)
    if (r) {
      return rawCols.map(c => (r[c] === null || r[c] === undefined ? '—' : String(r[c])))
    }
    return [String(row ?? '—')]
  })

  if (rawCols.length === 0 && filas.length === 0) return null
  return {
    titulo: asString(rec.titulo),
    columnas: rawCols,
    filas,
  }
}

export async function consultarLaboratorio(
  pregunta: string,
  territorio: string,
  signal?: AbortSignal,
): Promise<LaboratorioConsultaResponse> {
  const raw = await requestApiJson<Record<string, unknown>>('/laboratorio/consultar', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      pregunta: pregunta.trim(),
      territorio: territorio.trim(),
    }),
    signal,
  })

  const protocolo = asRecord(raw.protocolo) ?? asRecord(raw.dossier) ?? raw
  const terrCode = asString(raw.territorio ?? protocolo.territorio) ?? territorio
  const terrName = nombreTerritorio(
    terrCode,
    asString(raw.territorio_nombre ?? protocolo.territorio_nombre),
  )

  const rawFuentes = Array.isArray(raw.fuentes_verificadas)
    ? raw.fuentes_verificadas
    : Array.isArray(protocolo.fuentes_verificadas)
      ? protocolo.fuentes_verificadas
      : Array.isArray(raw.fuentes)
        ? raw.fuentes
        : []

  const fuentesVerificadas: DossierFuenteVerificada[] = rawFuentes.map(item => {
    if (typeof item === 'string') return { institucion: item }
    const rec = asRecord(item) ?? {}
    return {
      institucion: asString(rec.institucion ?? rec.fuente ?? rec.nombre) ?? 'Fuente oficial verificada',
      sistema: asString(rec.sistema),
      corte: asString(rec.corte ?? rec.publicacion),
      endpoint: asString(rec.endpoint),
      series: asStringArray(rec.series ?? rec.codigos_series),
    }
  })

  const rawMetricas = Array.isArray(raw.metricas_reproducibles)
    ? raw.metricas_reproducibles
    : Array.isArray(protocolo.metricas_reproducibles)
      ? protocolo.metricas_reproducibles
      : Array.isArray(raw.metricas)
        ? raw.metricas
        : []

  const metricasReproducibles: DossierMetrica[] = rawMetricas
    .map(item => asRecord(item))
    .filter((item): item is Record<string, unknown> => item !== null)
    .map(item => ({
      nombre: asString(item.nombre ?? item.indicador ?? item.etiqueta) ?? 'Indicador',
      valor: item.valor !== null && item.valor !== undefined ? String(item.valor) : 'Sin dato',
      unidad: asString(item.unidad),
      periodo: asString(item.periodo ?? item.anio !== undefined ? String(item.anio) : null),
      fuente: asString(item.fuente),
      serie: asString(item.serie ?? item.serie_bde ?? item.formula),
    }))

  const hipotesisTxt =
    asString(raw.hipotesis_y_metodo ?? protocolo.hipotesis_y_metodo) ??
    [asString(raw.hipotesis ?? protocolo.hipotesis), asString(raw.metodo ?? protocolo.metodo)]
      .filter(Boolean)
      .join(' ') ??
    'Contraste descriptivo determinista sobre cortes publicados de solo lectura.'

  const rawPasos = Array.isArray(raw.pasos)
    ? raw.pasos
    : Array.isArray(protocolo.pasos)
      ? protocolo.pasos
      : []

  const pasos: DossierPaso[] = rawPasos
    .map(item => asRecord(item))
    .filter((item): item is Record<string, unknown> => item !== null)
    .map((item, idx) => ({
      numero: Math.trunc(toNumberOrNull(item.numero ?? item.paso) ?? idx + 1),
      titulo: asString(item.titulo ?? item.etapa ?? item.nombre) ?? `Paso ${idx + 1}`,
      contenido: asString(item.contenido ?? item.detalle ?? item.texto ?? item.descripcion) ?? '',
    }))

  const fuente = normalizeFuenteFase2(
    raw.fuente_trazabilidad,
    'Chile Territorial · Laboratorio de Investigación (solo lectura)',
    '/api/v1/laboratorio/consultar',
  )

  const evidenciaFavorable = asStringArray(
    raw.evidencia_favorable ?? protocolo.evidencia_favorable ?? raw.hallazgos,
  )
  const hipotesisAlternativas = asStringArray(
    raw.hipotesis_alternativas ??
      protocolo.hipotesis_alternativas ??
      raw.evidencia_contraria ??
      protocolo.evidencia_contraria,
  )
  const limitaciones = asStringArray(
    raw.limitaciones_metodologicas ?? protocolo.limitaciones_metodologicas ?? raw.limitaciones,
  )

  return {
    id_consulta: asString(raw.id_consulta ?? raw.id) ?? `lab-${Date.now()}`,
    generado_en: asString(raw.generado_en ?? raw.timestamp) ?? new Date().toISOString(),
    territorio: terrCode,
    territorio_nombre: terrName,
    pregunta: asString(raw.pregunta ?? protocolo.pregunta) ?? pregunta.trim(),
    solo_lectura: typeof raw.solo_lectura === 'boolean' ? raw.solo_lectura : true,
    motor: asString(raw.motor) ?? 'Motor analítico determinista de solo lectura (sin IA de pago)',
    fuentes_verificadas: fuentesVerificadas,
    hipotesis_y_metodo: hipotesisTxt,
    metricas_reproducibles: metricasReproducibles,
    tabla_evidencia: normalizeTablaEvidencia(
      raw.tabla_evidencia ?? protocolo.tabla_evidencia ?? raw.evidencia_tabular,
    ),
    evidencia_favorable: evidenciaFavorable,
    hipotesis_alternativas: hipotesisAlternativas,
    interpretacion:
      asString(raw.interpretacion ?? protocolo.interpretacion ?? raw.interpretacion_sobria) ??
      'Consulta procesada sobre los cortes oficiales disponibles sin extrapolación fuera de los datos publicados.',
    limitaciones_metodologicas: limitaciones,
    pasos,
    dossier_markdown: asString(raw.dossier_markdown ?? raw.markdown),
    dossier_html: asString(raw.dossier_html ?? raw.html),
    fuente_trazabilidad: fuente,
  }
}

/* ============================================================================
   HELPERS DE DESCARGA (CSV, MARKDOWN, HTML)
============================================================================ */

export function escapeCsvCell(value: unknown): string {
  const str = value === null || value === undefined ? '' : String(value)
  return /[,"\r\n]/.test(str) ? `"${str.replaceAll('"', '""')}"` : str
}

export function triggerFileDownload(filename: string, content: string, mimeType: string): void {
  const blob = new Blob([content], { type: mimeType })
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  anchor.click()
  window.setTimeout(() => URL.revokeObjectURL(url), 1000)
}
