import { requestApiJson, toNumberOrNull } from './bcchService'
import type { FuenteTrazabilidad } from './bcchService'

export interface DipresSubtituloResumen {
  subtitulo: string
  nombre: string
  categoria?: string | null
  monto_millones?: number | null
  vigente_millones?: number | null
  avance_pct?: number | null
}

export interface DipresServicioAysen {
  partida?: string | null
  nombre_partida?: string | null
  capitulo?: string | null
  nombre: string
  programas?: string[]
  gasto_corriente_millones: number | null
  inversion_millones: number | null
  transferencias_capital_millones: number | null
  total_millones: number | null
  vigente_millones?: number | null
  registros?: number | null
}

export interface DipresPresupuestoAbiertoEstado {
  disponible: boolean
  estado?: string | null
  http_status?: number | null
  mensaje?: string | null
  url?: string | null
  ultimo_corte?: string | null
  verificado_en?: string | null
}

export interface DipresGoreAysen {
  nombre?: string
  partida?: string
  gasto_corriente_sub_21_26_millones: number | null
  inversion_sub_29_31_millones: number | null
  transferencias_capital_sub_33_millones: number | null
  financiamiento_partida_31_millones: number | null
  total_bruto_millones: number | null
  subtitulos?: DipresSubtituloResumen[]
}

export interface DipresTotalesGobiernoCentral {
  gasto_corriente_sub_21_26_millones: number | null
  inversion_sub_29_31_millones: number | null
  transferencias_capital_sub_33_millones: number | null
  total_gasto_directo_millones: number | null
  financiamiento_gore_p31_millones: number | null
  ingresos_servicios_excluidos_millones: number | null
}

export interface DipresAysenResponse {
  anio: number
  region_codigo: string
  region_nombre: string
  etapa_contable: string | null
  moneda: string | null
  gore_aysen: DipresGoreAysen
  servicios_publicos_aysen: DipresServicioAysen[]
  servicios_total_millones: number | null
  totales_gobierno_central_aysen?: DipresTotalesGobiernoCentral | null
  ratio_corriente_sobre_inversion_pct: number | null
  motivo_brecha: string | null
  presupuesto_abierto: DipresPresupuestoAbiertoEstado | null
  fuente_trazabilidad: FuenteTrazabilidad
  actualizado_en: string | null
  extraido_en: string | null
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null
}

export async function fetchDipresAysen(
  anio?: number,
  refresh?: boolean,
  signal?: AbortSignal,
): Promise<DipresAysenResponse> {
  const params = new URLSearchParams()
  if (anio !== undefined) params.set('anio', String(anio))
  if (refresh) params.set('refresh', 'true')
  const qs = params.toString()
  const endpoint = `/fiscal/dipres${qs ? `?${qs}` : ''}`
  const raw = await requestApiJson<Record<string, unknown>>(endpoint, { signal })

  const goreRaw = asRecord(raw.gore_aysen) ?? {}
  const totalesRaw = asRecord(raw.totales_gobierno_central_aysen)
  const fuenteRaw = asRecord(raw.fuente_trazabilidad) ?? {}
  const paRaw = asRecord(raw.presupuesto_abierto)

  const goreCorriente = toNumberOrNull(
    goreRaw.gasto_corriente_sub_21_26 ?? goreRaw.gasto_corriente_sub_21_26_millones ?? raw.gasto_corriente_sub_21_26_millones,
  )
  const goreInversion = toNumberOrNull(
    goreRaw.inversion_sub_29_31 ?? goreRaw.inversion_sub_29_31_millones ?? raw.inversion_sub_29_31_millones,
  )
  const goreSub33 = toNumberOrNull(
    goreRaw.transferencias_capital_sub_33 ?? goreRaw.transferencias_capital_sub_33_millones ?? raw.transferencias_capital_sub_33_millones,
  )
  const gorePartida31 = toNumberOrNull(
    goreRaw.ingresos_financiamiento_p31 ?? goreRaw.financiamiento_partida_31_millones ?? raw.financiamiento_partida_31_millones,
  )
  const goreTotalDirecto = toNumberOrNull(
    goreRaw.total_gasto_directo_millones ?? goreRaw.total_bruto_millones,
  )

  const rawPartidas = Array.isArray(goreRaw.partidas)
    ? goreRaw.partidas
    : Array.isArray(goreRaw.subtitulos)
      ? goreRaw.subtitulos
      : []

  const subtitulos: DipresSubtituloResumen[] = rawPartidas
    .map(item => asRecord(item))
    .filter((item): item is Record<string, unknown> => item !== null)
    .map(item => ({
      subtitulo: String(item.subtitulo ?? item.codigo_subtitulo ?? item.partida ?? ''),
      nombre: String(item.nombre_subtitulo ?? item.nombre ?? item.nombre_programa ?? item.nombre_capitulo ?? 'Partida'),
      categoria: typeof item.categoria === 'string' ? item.categoria : null,
      monto_millones: toNumberOrNull(item.ejecucion_millones ?? item.monto_millones ?? item.ejecutado_millones),
      vigente_millones: toNumberOrNull(item.vigente_millones),
      avance_pct: toNumberOrNull(item.avance_pct),
    }))

  const rawServicios = Array.isArray(raw.servicios_publicos_aysen) ? raw.servicios_publicos_aysen : []
  const servicios: DipresServicioAysen[] = rawServicios
    .map(item => asRecord(item))
    .filter((item): item is Record<string, unknown> => item !== null)
    .map(item => ({
      partida: typeof item.partida === 'string' ? item.partida : null,
      nombre_partida: typeof item.nombre_partida === 'string' ? item.nombre_partida : null,
      capitulo: typeof item.capitulo === 'string' ? item.capitulo : null,
      nombre: String(item.nombre_capitulo ?? item.nombre ?? item.nombre_partida ?? 'Servicio público'),
      programas: Array.isArray(item.programas) ? item.programas.map(String) : undefined,
      gasto_corriente_millones: toNumberOrNull(item.gasto_corriente_sub_21_26 ?? item.gasto_corriente_millones),
      inversion_millones: toNumberOrNull(item.inversion_sub_29_31 ?? item.inversion_millones),
      transferencias_capital_millones: toNumberOrNull(item.transferencias_capital_sub_33 ?? item.transferencias_capital_millones),
      total_millones: toNumberOrNull(item.total_gasto_millones ?? item.total_millones),
      vigente_millones: toNumberOrNull(item.vigente_gasto_millones),
      registros: typeof item.registros === 'number' ? item.registros : null,
    }))

  const serviciosSum = servicios.length > 0
    ? servicios.reduce((acc, s) => acc + (s.total_millones ?? 0), 0)
    : null

  const totales: DipresTotalesGobiernoCentral | null = totalesRaw
    ? {
        gasto_corriente_sub_21_26_millones: toNumberOrNull(totalesRaw.gasto_corriente_sub_21_26),
        inversion_sub_29_31_millones: toNumberOrNull(totalesRaw.inversion_sub_29_31),
        transferencias_capital_sub_33_millones: toNumberOrNull(totalesRaw.transferencias_capital_sub_33),
        total_gasto_directo_millones: toNumberOrNull(totalesRaw.total_gasto_directo_millones),
        financiamiento_gore_p31_millones: toNumberOrNull(totalesRaw.financiamiento_gore_p31),
        ingresos_servicios_excluidos_millones: toNumberOrNull(totalesRaw.ingresos_servicios_excluidos),
      }
    : null

  const fuente: FuenteTrazabilidad = {
    institucion: typeof fuenteRaw.institucion === 'string'
      ? fuenteRaw.institucion
      : 'DIPRES · Ministerio de Hacienda (datos.gob.cl CKAN)',
    endpoint: typeof fuenteRaw.endpoint_ckan === 'string'
      ? `${fuenteRaw.endpoint_ckan}${fuenteRaw.resource_id ? ` · resource_id=${fuenteRaw.resource_id}` : ''}`
      : `/api/v1${endpoint}`,
    endpoint_ckan: typeof fuenteRaw.endpoint_ckan === 'string' ? fuenteRaw.endpoint_ckan : null,
    package_name: typeof fuenteRaw.package_name === 'string' ? fuenteRaw.package_name : null,
    package_title: typeof fuenteRaw.package_title === 'string' ? fuenteRaw.package_title : null,
    resource_id: typeof fuenteRaw.resource_id === 'string' ? fuenteRaw.resource_id : null,
    resource_name: typeof fuenteRaw.resource_name === 'string' ? fuenteRaw.resource_name : null,
    actualizado_en: typeof fuenteRaw.actualizado_en === 'string' ? fuenteRaw.actualizado_en : null,
    extraido_en: typeof fuenteRaw.extraido_en === 'string' ? fuenteRaw.extraido_en : null,
    unidad: typeof fuenteRaw.unidad_salida === 'string' ? fuenteRaw.unidad_salida : 'millones CLP',
    desde_cache: typeof fuenteRaw.desde_cache === 'boolean' ? fuenteRaw.desde_cache : undefined,
  }

  return {
    anio: typeof raw.anio === 'number' ? raw.anio : (anio ?? 2025),
    region_codigo: String(raw.region_codigo ?? '11'),
    region_nombre: String(raw.region_nombre ?? 'Aysén del General Carlos Ibáñez del Campo'),
    etapa_contable: typeof fuenteRaw.etapa_informada === 'string'
      ? fuenteRaw.etapa_informada
      : typeof raw.etapa_contable === 'string'
        ? raw.etapa_contable
        : null,
    moneda: typeof fuenteRaw.unidad_salida === 'string' ? fuenteRaw.unidad_salida : 'millones CLP',
    gore_aysen: {
      nombre: typeof goreRaw.nombre === 'string' ? goreRaw.nombre : 'Gobierno Regional de Aysén',
      partida: typeof goreRaw.partida === 'string' ? goreRaw.partida : '31',
      gasto_corriente_sub_21_26_millones: goreCorriente,
      inversion_sub_29_31_millones: goreInversion,
      transferencias_capital_sub_33_millones: goreSub33,
      financiamiento_partida_31_millones: gorePartida31,
      total_bruto_millones: goreTotalDirecto,
      subtitulos,
    },
    servicios_publicos_aysen: servicios,
    servicios_total_millones: toNumberOrNull(raw.servicios_total_millones) ?? serviciosSum,
    totales_gobierno_central_aysen: totales,
    ratio_corriente_sobre_inversion_pct: toNumberOrNull(
      goreRaw.ratio_corriente_sobre_inversion_pct ?? raw.ratio_corriente_sobre_inversion_pct,
    ),
    motivo_brecha:
      typeof goreRaw.motivo_brecha === 'string'
        ? goreRaw.motivo_brecha
        : typeof raw.motivo_brecha === 'string'
          ? raw.motivo_brecha
          : null,
    presupuesto_abierto: paRaw
      ? {
          disponible: Boolean(paRaw.disponible),
          estado: typeof paRaw.estado === 'string'
            ? paRaw.estado
            : paRaw.disponible
              ? `HTTP ${paRaw.http_status ?? 200} · Disponible`
              : paRaw.http_status
                ? `HTTP ${paRaw.http_status}`
                : 'No disponible',
          http_status: typeof paRaw.http_status === 'number' ? paRaw.http_status : null,
          mensaje: typeof paRaw.nota === 'string' ? paRaw.nota : typeof paRaw.mensaje === 'string' ? paRaw.mensaje : null,
          url: typeof paRaw.url === 'string' ? paRaw.url : null,
          ultimo_corte: typeof paRaw.ultimo_corte === 'string' ? paRaw.ultimo_corte : null,
          verificado_en: typeof paRaw.verificado_en === 'string' ? paRaw.verificado_en : fuente.extraido_en,
        }
      : null,
    fuente_trazabilidad: fuente,
    actualizado_en: typeof raw.actualizado_en === 'string' ? raw.actualizado_en : fuente.actualizado_en ?? null,
    extraido_en: typeof raw.extraido_en === 'string' ? raw.extraido_en : fuente.extraido_en ?? null,
  }
}
