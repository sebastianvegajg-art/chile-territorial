import { requestApiJson, toNumberOrNull } from './bcchService'

export interface ComunaAysen {
  cut: string
  nombre: string
}

export const COMUNAS_AYSEN: readonly ComunaAysen[] = [
  { cut: '11201', nombre: 'Aysén' },
  { cut: '11101', nombre: 'Coyhaique' },
  { cut: '11202', nombre: 'Cisnes' },
  { cut: '11301', nombre: 'Cochrane' },
  { cut: '11401', nombre: 'Chile Chico' },
  { cut: '11402', nombre: 'Río Ibáñez' },
  { cut: '11203', nombre: 'Guaitecas' },
  { cut: '11102', nombre: 'Lago Verde' },
  { cut: '11302', nombre: 'O’Higgins' },
  { cut: '11303', nombre: 'Tortel' },
] as const

export const ANIOS_AYSEN: readonly number[] = [
  2026, 2025, 2024, 2023, 2022, 2021, 2020, 2019, 2018, 2017, 2016, 2015, 2014, 2013,
] as const

export function getComunaNombre(cut?: string | null): string {
  if (!cut) return 'Todas las comunas'
  return COMUNAS_AYSEN.find(c => c.cut === cut)?.nombre ?? cut
}

export interface FuenteOficial {
  nombre: string
  institucion: string | null
  periodo: string | null
  unidad: string | null
  cobertura: string | null
  url: string | null
  endpoint: string | null
  actualizado_en: string | null
  extraido_en: string | null
  codigos_series: string[]
  nota: string | null
}

/* ============================================================
   1. RESUMEN · GET /api/v1/aysen/resumen
============================================================ */

export interface ResumenEconomiaCard {
  disponible: boolean
  crecimiento_real_pct: number | null
  crecimiento_chile_pct: number | null
  pib_nominal_millones: number | null
  participacion_nacional_pct: number | null
  frase_radial: string | null
  periodo: string | null
  unidad: string | null
  cobertura: string | null
  fuente: FuenteOficial | null
  sin_dato_motivo: string | null
}

export interface ResumenInversionCard {
  disponible: boolean
  monto_millones: number | null
  variacion_mismo_periodo_pct: number | null
  periodo_comparado: string | null
  instituciones_cubiertas: string[]
  frase_radial: string | null
  periodo: string | null
  unidad: string | null
  cobertura: string | null
  fuente: FuenteOficial | null
  sin_dato_motivo: string | null
}

export interface ResumenArrastreCard {
  disponible: boolean
  porcentaje_pct: number | null
  monto_millones: number | null
  base_calculo: string | null
  proyectos_con_arrastre: number | null
  total_proyectos_evaluados: number | null
  proyectos_excluidos: number | null
  frase_radial: string | null
  periodo: string | null
  unidad: string | null
  cobertura: string | null
  fuente: FuenteOficial | null
  sin_dato_motivo: string | null
}

export interface AysenResumenResponse {
  anio: number
  comuna_codigo: string | null
  comuna_nombre: string | null
  en_curso: boolean
  mes_corte: number | null
  mes_corte_nombre: string | null
  aviso_anio_en_curso: string | null
  aviso_granularidad: string | null
  evolucion_economica: ResumenEconomiaCard
  inversion_publica: ResumenInversionCard
  arrastre: ResumenArrastreCard
  actualizado_en: string | null
}

/* ============================================================
   2. ECONOMÍA · GET /api/v1/aysen/economia
============================================================ */

export interface SerieCrecimientoPunto {
  anio: number
  aysen_pct: number | null
  chile_pct: number | null
  estado: string | null
}

export interface SerieParticipacionPunto {
  anio: number
  participacion_pct: number | null
  pib_aysen_millones: number | null
  pib_chile_millones: number | null
}

export interface ActividadEconomicaItem {
  codigo: string
  nombre: string
  serie_id: string | null
  valor_millones: number | null
  participacion_pct: number | null
  variacion_real_pct: number | null
  aporte_crecimiento_pp: number | null
  es_administracion_publica: boolean
  es_pesca: boolean
  estado: string | null
}

export interface SectorDestacado {
  nombre: string
  codigo: string | null
  variacion_pct: number | null
  participacion_pct: number | null
  aporte_pp: number | null
  nota: string | null
}

export interface AysenEconomiaResponse {
  anio: number
  anio_datos: number | null
  en_curso: boolean
  mes_corte_nombre: string | null
  aviso_periodo: string | null
  pib_nominal_millones: number | null
  pib_real_millones: number | null
  crecimiento_real_aysen_pct: number | null
  crecimiento_real_chile_pct: number | null
  participacion_nacional_pct: number | null
  admin_publica_millones: number | null
  admin_publica_pct: number | null
  diferencia_impuestos_productos_millones: number | null
  frase_tamano_vs_aporte: string | null
  nota_volumenes_encadenados: string | null
  serie_crecimiento: SerieCrecimientoPunto[]
  serie_participacion: SerieParticipacionPunto[]
  actividades: ActividadEconomicaItem[]
  sectores_crecieron: SectorDestacado[]
  sectores_cayeron: SectorDestacado[]
  codigos_series: string[]
  fuentes: FuenteOficial[]
  actualizado_en: string | null
}

/* ============================================================
   3. PRESUPUESTOS · GET /api/v1/aysen/presupuestos
============================================================ */

export interface DesglosePartida {
  categoria: string
  subcategoria: string | null
  monto_millones: number | null
  porcentaje_pct: number | null
  detalle: string | null
}

export interface CostoAdministracionInfo {
  disponible: boolean
  monto_millones: number | null
  porcentaje_pct: number | null
  respuesta: string | null
  brecha_explicacion: string | null
}

export type RolBilletera = 'regional' | 'municipal' | 'nacional_en_region' | 'nacional'

export interface InstitucionPresupuesto {
  id: string
  nombre: string
  rol_billetera: RolBilletera
  territorio_etiqueta: string
  destacado_piloto: boolean
  presupuesto_inicial_millones: number | null
  presupuesto_vigente_millones: number | null
  gasto_ejecutado_millones: number | null
  avance_ejecucion_pct: number | null
  gasto_corriente_millones: number | null
  gasto_corriente_pct: number | null
  inversion_millones: number | null
  inversion_pct: number | null
  base_calculo: string | null
  frase_radial: string | null
  desglose: DesglosePartida[]
  personal_sinim: DesglosePartida[]
  costo_administracion: CostoAdministracionInfo
  fuente: FuenteOficial
  sin_dato_motivo: string | null
}

export interface ConsolidadoPresupuesto {
  disponible: boolean
  ejecutado_total_millones: number | null
  vigente_total_millones: number | null
  gasto_corriente_millones: number | null
  inversion_millones: number | null
  transferencias_eliminadas_millones: number | null
  instituciones_cubiertas: string[]
  nota_sin_doble_contabilizacion: string | null
  frase_radial: string | null
  fuente: FuenteOficial | null
}

export interface AysenPresupuestosResponse {
  anio: number
  comuna_codigo: string
  comuna_nombre: string
  en_curso: boolean
  mes_corte: number | null
  mes_corte_nombre: string | null
  aviso_anio_en_curso: string | null
  consolidado: ConsolidadoPresupuesto | null
  instituciones: InstitucionPresupuesto[]
  comunas_disponibles: ComunaAysen[]
  actualizado_en: string | null
}

/* ============================================================
   4. PROYECTOS · GET /api/v1/aysen/proyectos
============================================================ */

export interface PreguntaArrastreResumen {
  titulo: string
  disponible: boolean
  porcentaje_pct: number | null
  numerador_millones: number | null
  denominador_millones: number | null
  base_calculo: string | null
  frase_radial: string | null
  proyectos_incluidos: number | null
  proyectos_excluidos: number | null
  fuente: FuenteOficial | null
  sin_dato_motivo: string | null
}

export interface HitoProyecto {
  orden: number
  etapa: string
  fecha: string | null
  institucion_responsable: string | null
  administracion_vigente: string | null
  documento_url: string | null
  documento_etiqueta: string | null
  estado: string | null
  nota: string | null
}

export type ClasificacionArrastre = 'arrastre' | 'nuevo' | 'insuficiente'

export interface ProyectoObra {
  id: string
  codigo_bip: string | null
  codigo_contrato: string | null
  nombre: string
  comuna: string | null
  comuna_cut: string | null
  institucion: string
  clasificacion_arrastre: ClasificacionArrastre
  etiqueta_arrastre: string
  administracion_origen: string | null
  frase_radial: string | null
  costo_total_millones: number | null
  compromiso_anio_millones: number | null
  pagado_anio_millones: number | null
  pagado_anios_anteriores_millones: number | null
  saldo_por_pagar_millones: number | null
  hitos: HitoProyecto[]
  fuente: FuenteOficial | null
  motivo_insuficiente: string | null
}

export interface AysenProyectosParams {
  anio: number
  comuna?: string
  institucion?: string
  q?: string
}

export interface AysenProyectosResponse {
  anio: number
  comuna: string | null
  institucion: string | null
  q: string
  en_curso: boolean
  mes_corte_nombre: string | null
  instituciones_disponibles: string[]
  pregunta_pagado_arrastre: PreguntaArrastreResumen
  pregunta_presupuesto_comprometido: PreguntaArrastreResumen
  proyectos: ProyectoObra[]
  proyectos_insuficientes: ProyectoObra[]
  total_proyectos: number
  fuentes: FuenteOficial[]
  actualizado_en: string | null
}

/* ============================================================
   UTILIDADES DE NORMALIZACIÓN DEFENSIVA
============================================================ */

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null
}

function asString(value: unknown): string | null {
  if (typeof value === 'string') {
    const trimmed = value.trim()
    return trimmed.length > 0 ? trimmed : null
  }
  return null
}

function asStringArray(value: unknown): string[] {
  if (!Array.isArray(value)) return []
  return value
    .map(item => {
      if (typeof item === 'string') return item.trim()
      const rec = asRecord(item)
      return asString(rec?.nombre ?? rec?.etiqueta ?? rec?.codigo ?? rec?.id) ?? ''
    })
    .filter(Boolean)
}

function asIntOrNull(value: unknown): number | null {
  const num = toNumberOrNull(value)
  return num !== null ? Math.trunc(num) : null
}

function pickString(rec: Record<string, unknown> | null, keys: readonly string[]): string | null {
  if (!rec) return null
  for (const key of keys) {
    const val = asString(rec[key])
    if (val !== null) return val
  }
  return null
}

function pickNumber(rec: Record<string, unknown> | null, keys: readonly string[]): number | null {
  if (!rec) return null
  for (const key of keys) {
    const val = toNumberOrNull(rec[key])
    if (val !== null) return val
  }
  return null
}

function normalizeFuente(
  raw: unknown,
  fallbackNombre: string,
  fallbackEndpoint?: string | null,
): FuenteOficial {
  const rec = asRecord(raw) ?? {}
  const codigosRaw = rec.codigos_series ?? rec.series_consultadas ?? rec.series ?? rec.codigo_serie
  const codigos_series = Array.isArray(codigosRaw)
    ? codigosRaw.map(String).filter(Boolean)
    : typeof codigosRaw === 'string' && codigosRaw.trim()
      ? [codigosRaw.trim()]
      : []

  return {
    nombre:
      pickString(rec, ['nombre', 'titulo', 'fuente', 'institucion', 'sistema']) ??
      fallbackNombre,
    institucion: pickString(rec, ['institucion', 'organismo', 'entidad']),
    periodo: pickString(rec, ['periodo', 'corte', 'anio_referencia', 'periodo_cubierto']),
    unidad: pickString(rec, ['unidad', 'unidad_salida', 'moneda']),
    cobertura: pickString(rec, ['cobertura', 'alcance', 'territorio']),
    url: pickString(rec, ['url', 'url_oficial', 'enlace', 'enlace_oficial', 'url_fuente', 'link', 'documento_url']),
    endpoint: pickString(rec, ['endpoint', 'endpoint_ckan']) ?? fallbackEndpoint ?? null,
    actualizado_en: pickString(rec, ['actualizado_en', 'fecha_actualizacion', 'ultimo_corte']),
    extraido_en: pickString(rec, ['extraido_en', 'fecha_extraccion']),
    codigos_series,
    nota: pickString(rec, ['nota', 'notas', 'observacion']),
  }
}

function normalizeFuentesList(raw: unknown, fallbackNombre: string, fallbackEndpoint: string): FuenteOficial[] {
  if (Array.isArray(raw)) {
    return raw
      .map(item => normalizeFuente(item, fallbackNombre, fallbackEndpoint))
      .filter(f => Boolean(f.nombre || f.url))
  }
  const rec = asRecord(raw)
  if (rec) {
    return [normalizeFuente(rec, fallbackNombre, fallbackEndpoint)]
  }
  return []
}

function pickCardFromArray(
  cards: unknown,
  candidates: readonly string[],
): Record<string, unknown> | null {
  if (!Array.isArray(cards)) return null
  for (const item of cards) {
    const rec = asRecord(item)
    if (!rec) continue
    const key = (pickString(rec, ['id', 'clave', 'tipo', 'slug', 'categoria']) ?? '').toLowerCase()
    if (candidates.some(c => key.includes(c))) return rec
  }
  return null
}

function buildFuenteFromCard(
  rec: Record<string, unknown> | null,
  fallbackNombre: string,
  fallbackEndpoint: string,
): FuenteOficial | null {
  if (!rec) return null
  const rawFuente = rec.fuente ?? rec.fuente_oficial ?? rec.fuente_trazabilidad
  if (typeof rawFuente === 'string' && rawFuente.trim()) {
    return {
      nombre: rawFuente.trim(),
      institucion: rawFuente.trim(),
      periodo: pickString(rec, ['periodo']),
      unidad: pickString(rec, ['unidad']),
      cobertura: pickString(rec, ['cobertura']),
      url: pickString(rec, ['url_fuente', 'url_ficha_oficial', 'url_respaldo', 'url']),
      endpoint: fallbackEndpoint,
      actualizado_en: pickString(rec, ['actualizado_en']),
      extraido_en: pickString(rec, ['extraido_en']),
      codigos_series: [],
      nota: pickString(rec, ['nota']),
    }
  }
  if (rawFuente && typeof rawFuente === 'object') {
    const f = normalizeFuente(rawFuente, fallbackNombre, fallbackEndpoint)
    if (!f.url) {
      f.url = pickString(rec, ['url_fuente', 'url_ficha_oficial', 'url_respaldo', 'url'])
    }
    return f
  }
  const url = pickString(rec, ['url_fuente', 'url_ficha_oficial', 'url_respaldo', 'url'])
  if (url) {
    return {
      nombre: fallbackNombre,
      institucion: fallbackNombre,
      periodo: pickString(rec, ['periodo']),
      unidad: pickString(rec, ['unidad']),
      cobertura: pickString(rec, ['cobertura']),
      url,
      endpoint: fallbackEndpoint,
      actualizado_en: null,
      extraido_en: null,
      codigos_series: [],
      nota: null,
    }
  }
  return null
}

/* ============================================================
   CLIENTE 1 · RESUMEN
============================================================ */

export async function fetchAysenResumen(
  anio: number,
  comuna?: string,
  signal?: AbortSignal,
): Promise<AysenResumenResponse> {
  const params = new URLSearchParams({ anio: String(anio) })
  if (comuna && comuna.trim()) params.set('comuna', comuna.trim())
  const path = `/aysen/resumen?${params.toString()}`
  const raw = await requestApiJson<Record<string, unknown>>(path, { signal })

  const periodoMeta = asRecord(raw.periodo) ?? asRecord(raw.corte) ?? {}
  const territorioRec = asRecord(raw.territorio)
  const comunaRec = asRecord(raw.comuna) ?? asRecord(territorioRec?.comuna_seleccionada)
  const comunaCodigo =
    pickString(comunaRec, ['codigo', 'cut']) ??
    asString(raw.comuna_codigo) ??
    (typeof raw.comuna === 'string' ? asString(raw.comuna) : null) ??
    (comuna?.trim() || null)
  const comunaNombre =
    pickString(comunaRec, ['nombre', 'municipio']) ??
    asString(raw.comuna_nombre) ??
    (comunaCodigo ? getComunaNombre(comunaCodigo) : null)

  const mesCorte = asIntOrNull(raw.mes_corte_vigente ?? raw.mes_corte ?? periodoMeta.mes_corte)
  const MESES_ES: Record<number, string> = {
    1: 'enero', 2: 'febrero', 3: 'marzo', 4: 'abril', 5: 'mayo', 6: 'junio',
    7: 'julio', 8: 'agosto', 9: 'septiembre', 10: 'octubre', 11: 'noviembre', 12: 'diciembre',
  }
  const mesCorteNombre =
    pickString(raw, ['mes_corte_nombre', 'mes_nombre']) ??
    pickString(periodoMeta, ['mes_corte_nombre', 'mes_nombre']) ??
    (mesCorte ? MESES_ES[mesCorte] ?? null : null)
  const enCurso = Boolean(
    raw.en_curso ??
      raw.anio_en_curso ??
      periodoMeta.en_curso ??
      (mesCorte !== null && mesCorte < 12) ??
      anio >= new Date().getFullYear(),
  )

  const tarjetasRec = asRecord(raw.tarjetas)
  const ecoRaw =
    asRecord(tarjetasRec?.economia) ??
    asRecord(raw.evolucion_economica) ??
    asRecord(raw.economia) ??
    pickCardFromArray(raw.tarjetas, ['econom', 'pib'])
  const invRaw =
    asRecord(tarjetasRec?.inversion) ??
    asRecord(raw.inversion_publica) ??
    asRecord(raw.inversion) ??
    asRecord(raw.presupuesto) ??
    pickCardFromArray(raw.tarjetas, ['invers', 'presup'])
  const arrRaw =
    asRecord(tarjetasRec?.arrastre) ??
    asRecord(raw.arrastre) ??
    asRecord(raw.compromisos_arrastre) ??
    asRecord(raw.compromisos) ??
    pickCardFromArray(raw.tarjetas, ['arrastr', 'compromis', 'proyect'])

  const ecoCrec = pickNumber(ecoRaw, [
    'crecimiento_real_pct',
    'crecimiento_real_aysen_pct',
    'variacion_real_pct',
    'valor_pct',
    'valor',
  ])
  const evolucion_economica: ResumenEconomiaCard = {
    disponible: ecoCrec !== null || Boolean(ecoRaw?.disponible),
    crecimiento_real_pct: ecoCrec,
    crecimiento_chile_pct: pickNumber(ecoRaw, ['valor_chile', 'crecimiento_chile_pct', 'crecimiento_real_chile_pct', 'referencia_chile_pct']),
    pib_nominal_millones: pickNumber(ecoRaw, ['pib_nominal_millones', 'aysen_nominal_millones']),
    participacion_nacional_pct: pickNumber(ecoRaw, ['participacion_nacional_pct', 'participacion_pib_pct']),
    frase_radial: pickString(ecoRaw, ['frase_radial', 'frase_ciudadana', 'frase', 'resumen', 'texto']),
    periodo: pickString(ecoRaw, ['periodo', 'anio_referencia']),
    unidad: pickString(ecoRaw, ['unidad']),
    cobertura: pickString(ecoRaw, ['cobertura']),
    fuente: buildFuenteFromCard(ecoRaw, 'Banco Central de Chile (BDE)', `/api/v1${path}`),
    sin_dato_motivo: pickString(ecoRaw, ['motivo_no_disponible', 'sin_dato_motivo', 'motivo_sin_dato', 'motivo_brecha', 'nota_sin_dato']),
  }

  const invMonto = pickNumber(invRaw, ['monto_millones', 'inversion_millones', 'total_millones', 'valor_millones', 'valor'])
  const invComp = asRecord(invRaw?.comparacion_mismo_periodo_anterior)
  const inversion_publica: ResumenInversionCard = {
    disponible: invMonto !== null || Boolean(invRaw?.disponible),
    monto_millones: invMonto,
    variacion_mismo_periodo_pct:
      pickNumber(invComp, ['variacion_pct', 'variacion_nominal_pct']) ??
      pickNumber(invRaw, ['variacion_mismo_periodo_pct', 'variacion_interanual_pct', 'variacion_pct']),
    periodo_comparado:
      pickString(invComp, ['etiqueta', 'nota']) ??
      pickString(invRaw, ['periodo_comparado', 'comparacion_periodo', 'referencia_comparacion']),
    instituciones_cubiertas: asStringArray(
      invRaw?.instituciones_cubiertas ?? invRaw?.instituciones ?? invRaw?.cobertura_institucional,
    ),
    frase_radial: pickString(invRaw, ['frase_radial', 'frase_ciudadana', 'frase', 'resumen', 'texto']),
    periodo: pickString(invRaw, ['periodo']),
    unidad: pickString(invRaw, ['unidad']),
    cobertura: pickString(invRaw, ['cobertura']),
    fuente: buildFuenteFromCard(invRaw, 'DIPRES · MOP DGOP', `/api/v1${path}`),
    sin_dato_motivo: pickString(invRaw, ['motivo_no_disponible', 'sin_dato_motivo', 'motivo_sin_dato', 'motivo_brecha', 'nota_sin_dato']),
  }

  const arrPct = pickNumber(arrRaw, ['porcentaje_pct', 'arrastre_pct', 'porcentaje', 'valor_pct', 'valor'])
  const arrMonto = pickNumber(arrRaw, ['monto_arrastre_millones', 'monto_millones', 'valor_millones'])
  const arrastre: ResumenArrastreCard = {
    disponible: arrPct !== null || arrMonto !== null || Boolean(arrRaw?.disponible),
    porcentaje_pct: arrPct,
    monto_millones: arrMonto,
    base_calculo:
      pickString(arrRaw, ['base_calculo', 'denominador', 'base']) ??
      (pickNumber(arrRaw, ['presupuesto_inversion_millones']) !== null
        ? `Sobre $${pickNumber(arrRaw, ['presupuesto_inversion_millones'])!.toLocaleString('es-CL', { maximumFractionDigits: 1 })} millones de inversión MOP comprometida en el año.`
        : null),
    proyectos_con_arrastre: asIntOrNull(arrRaw?.proyectos_con_arrastre ?? arrRaw?.cantidad_arrastre),
    total_proyectos_evaluados: asIntOrNull(arrRaw?.total_proyectos_evaluados ?? arrRaw?.proyectos_incluidos ?? arrRaw?.total_proyectos),
    proyectos_excluidos: asIntOrNull(arrRaw?.proyectos_excluidos ?? arrRaw?.proyectos_insuficientes),
    frase_radial: pickString(arrRaw, ['frase_radial', 'frase_ciudadana', 'frase', 'resumen', 'texto']),
    periodo: pickString(arrRaw, ['periodo']),
    unidad: pickString(arrRaw, ['unidad']),
    cobertura: pickString(arrRaw, ['cobertura']),
    fuente: buildFuenteFromCard(arrRaw, 'MOP · DGOP', `/api/v1${path}`),
    sin_dato_motivo: pickString(arrRaw, ['motivo_no_disponible', 'sin_dato_motivo', 'motivo_sin_dato', 'motivo_brecha', 'nota_sin_dato']),
  }

  const avisoEnCurso =
    pickString(raw, ['aviso_anio_en_curso', 'advertencia_anio_en_curso', 'aviso_corte']) ??
    pickString(periodoMeta, ['aviso', 'advertencia']) ??
    (enCurso && mesCorteNombre
      ? `Año ${anio} en curso (corte presupuestario a ${mesCorteNombre} de ${anio}). Las comparaciones interanuales utilizan el mismo período acumulado de ${anio - 1} para no comparar meses desiguales.`
      : null)

  const avisoGranularidad =
    pickString(raw, ['aviso_granularidad', 'aviso_pib_regional', 'nota_granularidad']) ??
    (comunaNombre
      ? `Filtro activo: Comuna de ${comunaNombre}. El PIB oficial del Banco Central se mide únicamente a escala regional (Región de Aysén) y nunca se asigna a escala comunal.`
      : null)

  return {
    anio: asIntOrNull(raw.anio_seleccionado ?? raw.anio) ?? anio,
    comuna_codigo: comunaCodigo,
    comuna_nombre: comunaNombre,
    en_curso: enCurso,
    mes_corte: mesCorte,
    mes_corte_nombre: mesCorteNombre,
    aviso_anio_en_curso: avisoEnCurso,
    aviso_granularidad: avisoGranularidad,
    evolucion_economica,
    inversion_publica,
    arrastre,
    actualizado_en: pickString(raw, ['actualizado_en', 'extraido_en']),
  }
}

/* ============================================================
   CLIENTE 2 · ECONOMÍA
============================================================ */

function normalizeSectorDestacado(item: unknown): SectorDestacado | null {
  const rec = asRecord(item)
  if (!rec) return null
  const nombre = pickString(rec, ['nombre', 'actividad', 'sector', 'titulo'])
  if (!nombre) return null
  return {
    nombre,
    codigo: pickString(rec, ['actividad_id', 'codigo', 'codigo_actividad', 'serie_bde_nominal', 'serie_id']),
    variacion_pct: pickNumber(rec, ['crecimiento_real_pct', 'variacion_real_pct', 'variacion_pct', 'crecimiento_pct', 'valor_pct']),
    participacion_pct: pickNumber(rec, ['participacion_nominal_pct', 'participacion_pct', 'peso_pct', 'participacion_pib_pct']),
    aporte_pp: pickNumber(rec, ['aporte_estimado_pp', 'aporte_crecimiento_pp', 'aporte_pp', 'incidencia_pp', 'contribucion_pp']),
    nota: pickString(rec, ['nota_aporte_estimado', 'nota', 'detalle', 'comentario']),
  }
}

export async function fetchAysenEconomia(
  anio: number,
  signal?: AbortSignal,
): Promise<AysenEconomiaResponse> {
  const params = new URLSearchParams({ anio: String(anio) })
  const path = `/aysen/economia?${params.toString()}`
  const raw = await requestApiJson<Record<string, unknown>>(path, { signal })

  const resumenRaw = asRecord(raw.resumen_anio) ?? asRecord(raw.resumen) ?? asRecord(raw.resumen_pib) ?? raw
  const vistasRaw = asRecord(raw.vistas) ?? asRecord(raw.series) ?? {}

  const rawCrec =
    (Array.isArray(raw.serie_crecimiento) && raw.serie_crecimiento) ||
    (Array.isArray(raw.crecimiento_historico) && raw.crecimiento_historico) ||
    (Array.isArray(vistasRaw.crecimiento_real) && vistasRaw.crecimiento_real) ||
    (Array.isArray(raw.serie_historica) && raw.serie_historica) ||
    []

  const serie_crecimiento: SerieCrecimientoPunto[] = rawCrec
    .map(item => asRecord(item))
    .filter((item): item is Record<string, unknown> => item !== null)
    .map(item => ({
      anio: asIntOrNull(item.anio ?? item.year) ?? 0,
      aysen_pct: pickNumber(item, ['crecimiento_aysen_pct', 'aysen_pct', 'aysen', 'region_pct', 'valor_aysen']),
      chile_pct: pickNumber(item, ['crecimiento_chile_pct', 'chile_pct', 'chile', 'nacional_pct', 'valor_chile']),
      estado: pickString(item, ['estado', 'estado_aysen']),
    }))
    .filter(item => item.anio > 0)
    .sort((a, b) => a.anio - b.anio)

  const rawPart =
    (Array.isArray(raw.serie_participacion) && raw.serie_participacion) ||
    (Array.isArray(raw.participacion_historica) && raw.participacion_historica) ||
    (Array.isArray(vistasRaw.participacion_nacional) && vistasRaw.participacion_nacional) ||
    (Array.isArray(raw.serie_historica) && raw.serie_historica) ||
    []

  const serie_participacion: SerieParticipacionPunto[] = rawPart
    .map(item => asRecord(item))
    .filter((item): item is Record<string, unknown> => item !== null)
    .map(item => ({
      anio: asIntOrNull(item.anio ?? item.year) ?? 0,
      participacion_pct: pickNumber(item, ['participacion_aysen_pct', 'participacion_pct', 'participacion_nacional_pct', 'peso_pct', 'valor_pct', 'valor']),
      pib_aysen_millones: pickNumber(item, ['pib_nominal_aysen_millones', 'pib_aysen_millones', 'aysen_nominal_millones']),
      pib_chile_millones: pickNumber(item, ['pib_nominal_chile_millones', 'pib_chile_millones', 'chile_nominal_millones']),
    }))
    .filter(item => item.anio > 0 && item.participacion_pct !== null)
    .sort((a, b) => a.anio - b.anio)

  const rawActs =
    (Array.isArray(raw.actividades) && raw.actividades) ||
    (Array.isArray(raw.actividades_nominales) && raw.actividades_nominales) ||
    (Array.isArray(vistasRaw.actividades) && vistasRaw.actividades) ||
    []

  const actividades: ActividadEconomicaItem[] = rawActs
    .map(item => asRecord(item))
    .filter((item): item is Record<string, unknown> => item !== null)
    .map(item => {
      const nombre = pickString(item, ['nombre', 'actividad', 'titulo_es', 'codigo_actividad']) ?? ''
      const lower = nombre.toLowerCase()
      return {
        codigo: pickString(item, ['actividad_id', 'codigo', 'codigo_actividad', 'serie_bde_nominal', 'serie_id']) ?? nombre,
        nombre,
        serie_id: pickString(item, ['serie_bde_nominal', 'serie_bde_real', 'serie_id', 'serie_bde']),
        valor_millones: pickNumber(item, ['nominal_millones', 'valor_millones', 'monto_millones', 'pib_nominal_millones']),
        participacion_pct: pickNumber(item, ['participacion_nominal_pct', 'participacion_pct', 'participacion_pib_pct', 'peso_pct', 'participacion_vab_pct']),
        variacion_real_pct: pickNumber(item, ['crecimiento_real_pct', 'variacion_real_pct', 'variacion_pct']),
        aporte_crecimiento_pp: pickNumber(item, ['aporte_estimado_pp', 'aporte_crecimiento_pp', 'aporte_pp', 'incidencia_pp']),
        es_administracion_publica:
          typeof item.es_administracion_publica === 'boolean'
            ? item.es_administracion_publica
            : lower.includes('administración pública') || lower.includes('administracion publica'),
        es_pesca:
          typeof item.es_pesca === 'boolean'
            ? item.es_pesca
            : lower.includes('pesca') || lower.includes('acuicultura'),
        estado: pickString(item, ['estado']),
      }
    })
    .filter(item => item.nombre.length > 0)

  const rawCrecieron =
    raw.sectores_crecieron ?? raw.sectores_que_crecieron ?? raw.sectores_alza ?? raw.top_crecimiento
  const rawCayeron =
    raw.sectores_cayeron ?? raw.sectores_que_cayeron ?? raw.sectores_baja ?? raw.top_caida

  let sectores_crecieron: SectorDestacado[] = Array.isArray(rawCrecieron)
    ? rawCrecieron.map(normalizeSectorDestacado).filter((s): s is SectorDestacado => s !== null)
    : []
  let sectores_cayeron: SectorDestacado[] = Array.isArray(rawCayeron)
    ? rawCayeron.map(normalizeSectorDestacado).filter((s): s is SectorDestacado => s !== null)
    : []

  if (sectores_crecieron.length === 0 && sectores_cayeron.length === 0) {
    const withVar = actividades.filter(a => a.variacion_real_pct !== null)
    sectores_crecieron = withVar
      .filter(a => (a.variacion_real_pct ?? 0) > 0)
      .sort((a, b) => (b.variacion_real_pct ?? 0) - (a.variacion_real_pct ?? 0))
      .slice(0, 4)
      .map(a => ({
        nombre: a.nombre,
        codigo: a.codigo,
        variacion_pct: a.variacion_real_pct,
        participacion_pct: a.participacion_pct,
        aporte_pp: a.aporte_crecimiento_pp,
        nota: null,
      }))
    sectores_cayeron = withVar
      .filter(a => (a.variacion_real_pct ?? 0) < 0)
      .sort((a, b) => (a.variacion_real_pct ?? 0) - (b.variacion_real_pct ?? 0))
      .slice(0, 4)
      .map(a => ({
        nombre: a.nombre,
        codigo: a.codigo,
        variacion_pct: a.variacion_real_pct,
        participacion_pct: a.participacion_pct,
        aporte_pp: a.aporte_crecimiento_pp,
        nota: null,
      }))
  }

  const trazaEco = asRecord(raw.fuente_trazabilidad)
  const enlacesEco = asRecord(trazaEco?.enlaces_oficiales)
  const fuentes = normalizeFuentesList(
    raw.fuentes ?? raw.fuente ?? raw.fuente_trazabilidad,
    'Banco Central de Chile · Base de Datos Estadísticos (BDE)',
    `/api/v1${path}`,
  )
  if (fuentes.length > 0 && !fuentes[0].url) {
    fuentes[0].url = pickString(enlacesEco, ['bde_siete', 'cuentas_nacionales']) ?? 'https://si3.bcentral.cl/Siete'
  }

  const codigosSet = new Set<string>([
    ...asStringArray(raw.codigos_series ?? raw.series_consultadas),
    ...fuentes.flatMap(f => f.codigos_series),
    ...actividades.map(a => a.serie_id).filter((s): s is string => Boolean(s)),
  ])

  const adminAct = actividades.find(a => a.es_administracion_publica) ?? null

  return {
    anio: asIntOrNull(raw.anio_seleccionado ?? raw.anio) ?? anio,
    anio_datos: asIntOrNull(raw.ultimo_anio_pib ?? raw.anio_datos ?? raw.anio_disponible ?? resumenRaw.anio),
    en_curso: Boolean(raw.en_curso ?? raw.anio_en_curso ?? raw.datos_anio_disponibles === false),
    mes_corte_nombre: pickString(raw, ['mes_corte_nombre', 'mes_nombre']),
    aviso_periodo: pickString(raw, ['aviso_sin_cierre_anual', 'aviso_periodo', 'advertencia_periodo', 'aviso_anio_en_curso']),
    pib_nominal_millones: pickNumber(resumenRaw, ['pib_nominal_aysen_millones', 'pib_nominal_millones', 'aysen_nominal_millones']),
    pib_real_millones: pickNumber(resumenRaw, ['pib_real_aysen_millones', 'pib_real_millones', 'aysen_real_millones']),
    crecimiento_real_aysen_pct: pickNumber(resumenRaw, ['crecimiento_real_aysen_pct', 'crecimiento_real_pct']),
    crecimiento_real_chile_pct: pickNumber(resumenRaw, ['crecimiento_real_chile_pct', 'crecimiento_chile_pct']),
    participacion_nacional_pct: pickNumber(resumenRaw, ['participacion_nominal_aysen_pct', 'participacion_nacional_pct', 'participacion_aysen_en_chile_pct']),
    admin_publica_millones: pickNumber(resumenRaw, ['admin_publica_millones', 'administracion_publica_millones']) ?? adminAct?.valor_millones ?? null,
    admin_publica_pct: pickNumber(resumenRaw, ['admin_publica_pct', 'administracion_publica_pct']) ?? adminAct?.participacion_pct ?? null,
    diferencia_impuestos_productos_millones: pickNumber(resumenRaw, ['diferencia_impuestos_productos_millones']),
    frase_tamano_vs_aporte: pickString(raw, [
      'frase_tamano_vs_aporte',
      'frase_destacada',
      'frase_radial',
      'lectura_tamano_vs_aporte',
    ]),
    nota_volumenes_encadenados: pickString(raw, [
      'nota_metodologica_aporte',
      'nota_volumenes_encadenados',
      'nota_metodologica',
      'advertencia_volumenes_encadenados',
    ]),
    serie_crecimiento,
    serie_participacion,
    actividades,
    sectores_crecieron,
    sectores_cayeron,
    codigos_series: Array.from(codigosSet),
    fuentes,
    actualizado_en: pickString(trazaEco, ['publicacion_sectorial_fecha', 'publicacion_pib_fecha']) ?? pickString(raw, ['actualizado_en', 'extraido_en']) ?? fuentes[0]?.actualizado_en ?? null,
  }
}

/* ============================================================
   CLIENTE 3 · PRESUPUESTOS
============================================================ */

function normalizeDesgloseList(raw: unknown): DesglosePartida[] {
  if (!Array.isArray(raw)) return []
  return raw
    .map(item => asRecord(item))
    .filter((item): item is Record<string, unknown> => item !== null)
    .map(item => ({
      categoria: pickString(item, ['etiqueta', 'categoria', 'nombre', 'tipo', 'rubro', 'subtitulo']) ?? 'Partida',
      subcategoria: pickString(item, ['subcategoria', 'codigo', 'grupo', 'subtitulo']),
      monto_millones: pickNumber(item, ['ejecutado_millones', 'monto_millones', 'valor_millones', 'monto']),
      porcentaje_pct: pickNumber(item, ['porcentaje_ejecutado_pct', 'porcentaje_pct', 'participacion_pct', 'porcentaje']),
      detalle: pickString(item, ['detalle', 'nota', 'descripcion']),
    }))
}

function inferRolBilletera(id: string, nombre: string, rawRol: string | null): RolBilletera {
  const norm = (rawRol ?? `${id} ${nombre}`).toLowerCase()
  if (norm.includes('municip') || norm.includes('comuna') || norm.includes('sinim')) return 'municipal'
  if (norm.includes('gore') || norm.includes('gobierno regional') || norm.includes('regional')) return 'regional'
  if (norm.includes('nacional_en_region') || norm.includes('sectorial') || norm.includes('vialidad') || norm.includes('mop') || norm.includes('servicio')) {
    return 'nacional_en_region'
  }
  return 'nacional'
}

function defaultTerritorioEtiqueta(rol: RolBilletera, comunaNombre: string): string {
  if (rol === 'municipal') return `Comuna de ${comunaNombre}`
  if (rol === 'nacional') return 'Chile · Nivel Nacional'
  return 'Región de Aysén'
}

function normalizeInstitucionPresupuesto(
  raw: Record<string, unknown>,
  fallbackId: string,
  comunaNombre: string,
  endpoint: string,
  forcedRol?: RolBilletera,
): InstitucionPresupuesto {
  const id = pickString(raw, ['id', 'clave', 'slug']) ?? fallbackId
  const nombre = pickString(raw, ['nombre', 'institucion', 'titulo']) ?? fallbackId
  const rol = forcedRol ?? inferRolBilletera(id, nombre, pickString(raw, ['rol_billetera', 'billetera', 'nivel', 'ambito', 'tipo']))
  const territorio_etiqueta =
    pickString(raw, ['territorio_etiqueta', 'etiqueta_territorio', 'territorio']) ??
    defaultTerritorioEtiqueta(rol, comunaNombre)

  const costoRec =
    asRecord(raw.costo_administracion) ??
    asRecord(raw.costo_administrar) ??
    asRecord(raw.costo_administracion_interna) ??
    asRecord(raw.administracion_interna)
  const costoMonto = pickNumber(costoRec, ['monto_millones', 'gasto_millones', 'valor_millones'])
  const costoPct = pickNumber(costoRec, ['porcentaje_pct', 'porcentaje_sobre_devengado', 'porcentaje'])
  const costoDisponible =
    typeof costoRec?.disponible === 'boolean'
      ? costoRec.disponible
      : costoMonto !== null || costoPct !== null

  const gastoEjecutado = pickNumber(raw, [
    'gasto_ejecutado_millones',
    'ejecutado_millones',
    'devengado_bep_millones',
    'devengado_millones',
    'total_gasto_millones',
    'gasto_total_millones',
    'gasto_total_devengado_millones',
  ])
  const gastoCorriente = pickNumber(raw, [
    'gasto_corriente_millones',
    'gasto_corriente_observable_millones',
    'corriente_millones',
  ])
  const gastoCorrientePct = pickNumber(raw, [
    'gasto_corriente_pct',
    'proporcion_gasto_corriente_pct',
    'gasto_corriente_observable_pct',
    'corriente_pct',
  ])
  const inversion = pickNumber(raw, [
    'inversion_y_capital_millones',
    'inversion_millones',
    'gasto_inversion_millones',
    'capital_millones',
  ])
  const inversionPct = pickNumber(raw, [
    'inversion_pct',
    'inversion_y_capital_pct',
    'gasto_inversion_pct',
    'capital_pct',
  ])

  const urlDirecta = pickString(raw, ['url_ficha_oficial', 'url_fuente', 'url_respaldo', 'url'])
  const fuenteRaw = raw.fuente ?? raw.fuente_oficial ?? raw.fuente_trazabilidad
  const fuente = normalizeFuente(fuenteRaw, rol === 'municipal' ? 'SINIM · Ficha Comunal BEP' : 'DIPRES · datos.gob.cl', endpoint)
  if (!fuente.url && urlDirecta) fuente.url = urlDirecta
  if (!fuente.periodo) {
    const anioDatos = asIntOrNull(raw.anio_datos)
    const mesC = asIntOrNull(raw.mes_corte)
    fuente.periodo = anioDatos
      ? `Ejercicio ${anioDatos} (BEP devengado)`
      : mesC && mesC < 12
        ? `Acumulado a mes ${mesC}`
        : 'Cierre anual presupuestario'
  }
  if (!fuente.unidad) fuente.unidad = 'millones CLP'
  if (!fuente.cobertura) fuente.cobertura = territorio_etiqueta

  // Desglose partidas (DIPRES o SINIM)
  let desglose: DesglosePartida[] = []
  const desgloseRaw = Array.isArray(raw.desglose_partidas)
    ? raw.desglose_partidas
    : Array.isArray(raw.desglose)
      ? raw.desglose
      : Array.isArray(asRecord(raw.desglose)?.partidas)
        ? asRecord(raw.desglose)!.partidas
        : Array.isArray(raw.partidas)
          ? raw.partidas
          : []
  desglose = normalizeDesgloseList(desgloseRaw)

  // Construir desglose SINIM (Subt. 21 + Subt. 22 + Otros gastos no desglosados) si viene en esquema municipal
  const s21Rec = asRecord(raw.desglose_subt_21)
  const personal_sinim: DesglosePartida[] = []
  if (s21Rec) {
    const s21Total = pickNumber(s21Rec, ['total_millones'])
    const s22 = pickNumber(raw, ['subt_22_bienes_servicios_millones'])
    const baseDev = gastoEjecutado && gastoEjecutado > 0 ? gastoEjecutado : null
    if (desglose.length === 0) {
      if (s21Total !== null) {
        desglose.push({
          categoria: 'Personal Municipal (Subtítulo 21)',
          subcategoria: 'Subt. 21',
          monto_millones: s21Total,
          porcentaje_pct: baseDev ? Number(((s21Total / baseDev) * 100).toFixed(2)) : null,
          detalle: 'Total devengado en personal municipal según ficha BEP SINIM.',
        })
      }
      if (s22 !== null) {
        desglose.push({
          categoria: 'Bienes y Servicios de Consumo (Subtítulo 22)',
          subcategoria: 'Subt. 22',
          monto_millones: s22,
          porcentaje_pct: baseDev ? Number(((s22 / baseDev) * 100).toFixed(2)) : null,
          detalle: 'Operación, consumos básicos y servicios contratados.',
        })
      }
      if (baseDev !== null && gastoCorriente !== null && baseDev >= gastoCorriente) {
        const otros = Number((baseDev - gastoCorriente).toFixed(3))
        desglose.push({
          categoria: 'Otros gastos devengados (transferencias, inversión y otros no desglosados en BEP)',
          subcategoria: 'Otros',
          monto_millones: otros,
          porcentaje_pct: Number(((otros / baseDev) * 100).toFixed(2)),
          detalle: 'La ficha resumida BEP SINIM no separa Subt. 24 y Subt. 31 individualmente.',
        })
      }
    }
    const itemsPersonal: Array<[string, string, string]> = [
      ['Personal de Planta (215.21.01)', 'planta_millones', 'Gestión interna'],
      ['Personal a Contrata (215.21.02)', 'contrata_millones', 'Gestión interna'],
      ['Personal a Honorarios (215.21.03)', 'honorarios_millones', 'Gestión interna'],
      ['Programas Comunitarios (215.21.04.004)', 'programas_millones', 'Servicios a la comunidad'],
    ]
    for (const [label, key, detalle] of itemsPersonal) {
      const m = pickNumber(s21Rec, [key])
      if (m !== null) {
        personal_sinim.push({
          categoria: label,
          subcategoria: 'Subt. 21',
          monto_millones: m,
          porcentaje_pct: baseDev ? Number(((m / baseDev) * 100).toFixed(2)) : null,
          detalle,
        })
      }
    }
  } else {
    const personalRaw =
      raw.personal_sinim ??
      raw.desglose_personal ??
      asRecord(raw.desglose)?.personal_detalle ??
      asRecord(raw.desglose)?.personal_sinim
    personal_sinim.push(...normalizeDesgloseList(personalRaw))
  }

  const destacadoPiloto =
    typeof raw.destacado_piloto === 'boolean'
      ? raw.destacado_piloto
      : rol === 'regional' || rol === 'municipal' || id.toLowerCase().includes('vialidad')

  return {
    id,
    nombre,
    rol_billetera: rol,
    territorio_etiqueta,
    destacado_piloto: destacadoPiloto,
    presupuesto_inicial_millones: pickNumber(raw, ['presupuesto_inicial_millones', 'inicial_millones', 'ley_inicial_millones']),
    presupuesto_vigente_millones: pickNumber(raw, ['presupuesto_vigente_millones', 'vigente_millones']),
    gasto_ejecutado_millones: gastoEjecutado,
    avance_ejecucion_pct: pickNumber(raw, ['tasa_ejecucion_pct', 'avance_ejecucion_pct', 'ejecucion_pct', 'avance_pct']),
    gasto_corriente_millones: gastoCorriente,
    gasto_corriente_pct: gastoCorrientePct,
    inversion_millones: inversion,
    inversion_pct: inversionPct,
    base_calculo: pickString(raw, ['base_calculo', 'base_calculo_gasto_corriente', 'base_porcentajes', 'denominador']),
    frase_radial: pickString(raw, ['frase_radial', 'frase_ciudadana', 'frase', 'resumen']),
    desglose,
    personal_sinim,
    costo_administracion: {
      disponible: costoDisponible,
      monto_millones: costoMonto,
      porcentaje_pct: costoPct,
      respuesta: pickString(costoRec, ['respuesta', 'explicacion', 'descripcion', 'frase', 'resumen', 'texto']),
      brecha_explicacion: pickString(costoRec, ['brecha_explicacion', 'brecha', 'motivo_brecha', 'limitacion']) ?? pickString(raw, ['nota_inicial_vigente']),
    },
    fuente,
    sin_dato_motivo: pickString(raw, ['motivo_no_disponible', 'sin_dato_motivo', 'motivo_brecha', 'motivo_sin_dato']),
  }
}

export async function fetchAysenPresupuestos(
  anio: number,
  comuna: string,
  signal?: AbortSignal,
): Promise<AysenPresupuestosResponse> {
  const cleanComuna = comuna.trim() || '11201'
  const params = new URLSearchParams({ anio: String(anio), comuna: cleanComuna })
  const path = `/aysen/presupuestos?${params.toString()}`
  const raw = await requestApiJson<Record<string, unknown>>(path, { signal })

  const comunaRec = asRecord(raw.comuna_seleccionada) ?? asRecord(raw.comuna)
  const comunaCodigo = pickString(comunaRec, ['codigo', 'cut']) ?? asString(raw.comuna_codigo) ?? cleanComuna
  const comunaNombre = pickString(comunaRec, ['nombre', 'municipio']) ?? asString(raw.comuna_nombre) ?? getComunaNombre(comunaCodigo)

  const mesCorte = asIntOrNull(raw.mes_corte)
  const MESES_ES: Record<number, string> = {
    1: 'enero', 2: 'febrero', 3: 'marzo', 4: 'abril', 5: 'mayo', 6: 'junio',
    7: 'julio', 8: 'agosto', 9: 'septiembre', 10: 'octubre', 11: 'noviembre', 12: 'diciembre',
  }
  const compMes = asRecord(raw.comparacion_mismo_mes)
  const mesCorteNombre =
    pickString(raw, ['mes_corte_nombre', 'mes_nombre']) ??
    pickString(compMes, ['mes_corte_nombre']) ??
    (mesCorte ? MESES_ES[mesCorte] ?? null : null)
  const enCurso = Boolean(
    raw.en_curso ??
      raw.anio_en_curso ??
      (raw.es_cierre_anual === false ? true : mesCorte !== null && mesCorte < 12),
  )

  const billeteras = asRecord(raw.billeteras)
  let instituciones: InstitucionPresupuesto[] = []

  if (Array.isArray(raw.instituciones)) {
    instituciones = raw.instituciones
      .map(item => asRecord(item))
      .filter((item): item is Record<string, unknown> => item !== null)
      .map((item, idx) => normalizeInstitucionPresupuesto(item, `inst-${idx}`, comunaNombre, `/api/v1${path}`))
  } else {
    const goreRaw = asRecord(billeteras?.gore_aysen ?? raw.gore_aysen ?? raw.gobierno_regional)
    if (goreRaw) {
      instituciones.push(normalizeInstitucionPresupuesto(goreRaw, 'gore_aysen', comunaNombre, `/api/v1${path}`, 'regional'))
    }

    const muniRaw = asRecord(billeteras?.municipal ?? raw.municipalidad ?? raw.municipio)
    if (muniRaw) {
      instituciones.push(normalizeInstitucionPresupuesto(muniRaw, `municipal_${comunaCodigo}`, comunaNombre, `/api/v1${path}`, 'municipal'))
    }

    const servBlock = asRecord(billeteras?.servicios_nacionales_aysen ?? raw.servicios_nacionales)
    if (servBlock) {
      // 1) Dirección de Vialidad MOP (Piloto)
      const vialPiloto = asRecord(servBlock.piloto_vialidad_mop)
      const vialDipres = asRecord(vialPiloto?.dipres_nacional)
      const vialContratos = asRecord(vialPiloto?.contratos_territorializados_aysen)
      if (vialDipres) {
        const notaTerr =
          vialContratos?.disponible === true
            ? `En la Región de Aysén, MOP DGOP registra ${vialContratos.total_proyectos} contratos vigentes de Vialidad por $${Number(vialContratos.presupuesto_anio_aysen_millones ?? 0).toLocaleString('es-CL', { maximumFractionDigits: 1 })} millones comprometidos en el corte (detalle en pestaña Proyectos).`
            : null
        const enrichedVial: Record<string, unknown> = {
          ...vialDipres,
          id: 'vialidad_mop',
          nombre: pickString(vialDipres, ['nombre']) ?? 'Dirección de Vialidad — MOP (Partida 12, Cap. 02)',
          destacado_piloto: true,
          base_calculo:
            [pickString(vialDipres, ['base_calculo']), notaTerr].filter(Boolean).join(' '),
        }
        instituciones.push(normalizeInstitucionPresupuesto(enrichedVial, 'vialidad_mop', comunaNombre, `/api/v1${path}`, 'nacional_en_region'))
      }

      // 2) Servicios públicos del Gobierno Central identificables en Aysén
      const srvsList = Array.isArray(servBlock.servicios_identificables_aysen) ? servBlock.servicios_identificables_aysen : []
      for (let i = 0; i < srvsList.length; i += 1) {
        const sRec = asRecord(srvsList[i])
        if (sRec) {
          instituciones.push(
            normalizeInstitucionPresupuesto(
              { ...sRec, destacado_piloto: false },
              `servicio_aysen_${i + 1}`,
              comunaNombre,
              `/api/v1${path}`,
              'nacional_en_region',
            ),
          )
        }
      }
    }

    const gcRaw = asRecord(raw.gobierno_central_nacional ?? raw.gobierno_central)
    if (gcRaw) {
      instituciones.push(
        normalizeInstitucionPresupuesto(
          { ...gcRaw, destacado_piloto: false },
          'gobierno_central_nacional',
          comunaNombre,
          `/api/v1${path}`,
          'nacional',
        ),
      )
    }
  }

  const consRaw = asRecord(raw.consolidacion) ?? asRecord(raw.consolidado) ?? asRecord(raw.resumen_consolidado)
  const consolidado: ConsolidadoPresupuesto | null = consRaw
    ? {
        disponible:
          typeof consRaw.disponible === 'boolean'
            ? consRaw.disponible
            : pickNumber(consRaw, ['consolidado_neto_millones', 'ejecutado_total_millones', 'total_ejecutado_millones', 'total_millones']) !== null,
        ejecutado_total_millones: pickNumber(consRaw, ['consolidado_neto_millones', 'ejecutado_total_millones', 'total_ejecutado_millones', 'total_millones']),
        vigente_total_millones: pickNumber(consRaw, ['vigente_total_millones', 'total_vigente_millones', 'total_bruto_millones']),
        gasto_corriente_millones: pickNumber(consRaw, ['gasto_corriente_millones', 'corriente_millones']),
        inversion_millones: pickNumber(consRaw, ['inversion_millones', 'gasto_inversion_millones']),
        transferencias_eliminadas_millones: pickNumber(consRaw, [
          'total_transferencias_eliminadas_millones',
          'transferencias_eliminadas_millones',
          'ajustes_transferencias_millones',
        ]),
        instituciones_cubiertas: asStringArray(consRaw.instituciones_cubiertas ?? consRaw.instituciones),
        nota_sin_doble_contabilizacion: pickString(consRaw, [
          'advertencia_metodologica',
          'nota_sin_doble_contabilizacion',
          'nota_consolidacion',
          'nota',
          'advertencia',
        ]),
        frase_radial: pickString(consRaw, ['frase_radial', 'frase_ciudadana', 'frase', 'resumen']),
        fuente: consRaw.fuente ? normalizeFuente(consRaw.fuente, 'Consolidado territorial sin doble contabilización', `/api/v1${path}`) : null,
      }
    : null

  const comunasRaw = Array.isArray(raw.comunas_aysen)
    ? raw.comunas_aysen
    : Array.isArray(raw.comunas_disponibles)
      ? raw.comunas_disponibles
      : []
  const comunas_disponibles: ComunaAysen[] = comunasRaw.length > 0
    ? comunasRaw
        .map(item => asRecord(item))
        .filter((item): item is Record<string, unknown> => item !== null)
        .map(item => ({
          cut: pickString(item, ['cut', 'codigo']) ?? '',
          nombre: pickString(item, ['nombre', 'municipio', 'comuna']) ?? '',
        }))
        .filter(item => item.cut.length > 0 && item.nombre.length > 0)
    : [...COMUNAS_AYSEN]

  const avisoEnCurso =
    pickString(raw, ['aviso_anio_en_curso', 'advertencia_anio_en_curso', 'advertencia_comparabilidad_meses']) ??
    (enCurso && compMes
      ? [
          `Ejercicio ${anio} en curso (corte DIPRES a ${mesCorteNombre ?? `mes ${mesCorte}`}).`,
          pickString(compMes, ['etiqueta']) && pickNumber(compMes, ['variacion_gore_pct']) !== null
            ? `GORE Aysén (${pickString(compMes, ['etiqueta'])}): variación nominal de ${pickNumber(compMes, ['variacion_gore_pct'])!.toLocaleString('es-CL', { maximumFractionDigits: 2 })}%.`
            : null,
          pickString(compMes, ['nota']),
        ].filter(Boolean).join(' ')
      : null)

  return {
    anio: asIntOrNull(raw.anio_seleccionado ?? raw.anio) ?? anio,
    comuna_codigo: comunaCodigo,
    comuna_nombre: comunaNombre,
    en_curso: enCurso,
    mes_corte: mesCorte,
    mes_corte_nombre: mesCorteNombre,
    aviso_anio_en_curso: avisoEnCurso,
    consolidado,
    instituciones,
    comunas_disponibles,
    actualizado_en: pickString(raw, ['actualizado_en', 'extraido_en']),
  }
}

/* ============================================================
   CLIENTE 4 · PROYECTOS
============================================================ */

const DEFAULT_MILESTONE_STAGES = [
  'Aprobación del financiamiento',
  'Contratación',
  'Pagos',
  'Entrada en funcionamiento',
] as const

function normalizePreguntaArrastre(
  raw: unknown,
  fallbackTitulo: string,
  endpoint: string,
): PreguntaArrastreResumen {
  const rec = asRecord(raw) ?? {}
  const pct = pickNumber(rec, ['porcentaje_pct', 'porcentaje', 'arrastre_pct', 'valor_pct'])
  const num = pickNumber(rec, [
    'monto_pagado_contratos_anteriores_millones',
    'monto_arrastre_comprometido_millones',
    'numerador_millones',
    'monto_arrastre_millones',
    'monto_comprometido_millones',
    'monto_millones',
  ])
  const den = pickNumber(rec, [
    'monto_pagado_total_millones',
    'presupuesto_inversion_anio_millones',
    'denominador_millones',
    'presupuesto_inversion_millones',
    'total_millones',
  ])
  const fuenteRaw = rec.fuente ?? rec.fuente_oficial ?? rec.fuente_trazabilidad
  return {
    titulo: pickString(rec, ['pregunta', 'titulo', 'nombre']) ?? fallbackTitulo,
    disponible: typeof rec.disponible === 'boolean' ? rec.disponible : pct !== null || num !== null,
    porcentaje_pct: pct,
    numerador_millones: num,
    denominador_millones: den,
    base_calculo:
      pickString(rec, ['base_calculo', 'base', 'denominador_etiqueta']) ??
      (rec.fecha_corte_administracion
        ? `Contratos firmados antes del ${String(rec.fecha_corte_administracion)} sobre el total pagado documentado del ejercicio.`
        : 'Compromisos documentados de proyectos en arrastre sobre el presupuesto de inversión documentado del ejercicio.'),
    frase_radial: pickString(rec, ['frase_radial', 'frase_ciudadana', 'frase', 'resumen']),
    proyectos_incluidos: asIntOrNull(rec.contratos_evaluados ?? rec.proyectos_evaluados ?? rec.proyectos_incluidos ?? rec.n_proyectos ?? rec.cantidad_incluidos),
    proyectos_excluidos: asIntOrNull(rec.proyectos_excluidos_sin_dato ?? rec.proyectos_excluidos ?? rec.cantidad_excluidos),
    fuente: fuenteRaw ? normalizeFuente(fuenteRaw, 'MOP DGOP · SIPRO · Mercado Público', endpoint) : null,
    sin_dato_motivo: pickString(rec, ['sin_dato_motivo', 'motivo_sin_dato', 'motivo_brecha']),
  }
}

function normalizeHitos(rawHitos: unknown): HitoProyecto[] {
  const items = Array.isArray(rawHitos)
    ? rawHitos.map(asRecord).filter((h): h is Record<string, unknown> => h !== null)
    : []

  if (items.length > 0) {
    return items.map((h, idx) => ({
      orden: asIntOrNull(h.orden) ?? idx + 1,
      etapa: pickString(h, ['titulo', 'etapa', 'nombre', 'fase', 'hito']) ?? DEFAULT_MILESTONE_STAGES[idx] ?? `Hito ${idx + 1}`,
      fecha: pickString(h, ['fecha', 'fecha_hito', 'periodo']),
      institucion_responsable: pickString(h, ['institucion_responsable', 'institucion', 'organismo', 'responsable']),
      administracion_vigente: pickString(h, ['administracion_vigente', 'administracion', 'gobierno', 'gestion']),
      documento_url: pickString(h, ['url_respaldo', 'documento_url', 'url', 'enlace', 'respaldo_url']),
      documento_etiqueta: pickString(h, ['documento_respaldo', 'documento_etiqueta', 'documento_nombre', 'respaldo_etiqueta', 'fuente_documento']),
      estado: pickString(h, ['estado']),
      nota: pickString(h, ['nota', 'detalle', 'observacion']),
    }))
  }

  return DEFAULT_MILESTONE_STAGES.map((etapa, idx) => ({
    orden: idx + 1,
    etapa,
    fecha: null,
    institucion_responsable: null,
    administracion_vigente: null,
    documento_url: null,
    documento_etiqueta: null,
    estado: null,
    nota: null,
  }))
}

function normalizeClasificacionArrastre(raw: Record<string, unknown>): {
  clasificacion: ClasificacionArrastre
  etiqueta: string
} {
  const val = (pickString(raw, ['nuevo_o_arrastre', 'clasificacion_arrastre', 'clasificacion', 'tipo_arrastre', 'estado_arrastre']) ?? '').toLowerCase()
  const cal = (pickString(raw, ['calidad_informacion']) ?? '').toLowerCase()
  if (cal.includes('insuf') || val.includes('insuf') || val.includes('exclu') || val.includes('sin_info') || raw.informacion_insuficiente === true) {
    return { clasificacion: 'insuficiente', etiqueta: 'Información insuficiente' }
  }
  if (val.includes('arrast') || raw.es_arrastre === true) {
    return { clasificacion: 'arrastre', etiqueta: 'Arrastre' }
  }
  if (val.includes('nuev') || raw.es_arrastre === false) {
    return { clasificacion: 'nuevo', etiqueta: 'Nuevo' }
  }
  return { clasificacion: 'insuficiente', etiqueta: 'Información insuficiente' }
}

function normalizeProyecto(raw: Record<string, unknown>, idx: number, endpoint: string): ProyectoObra {
  const { clasificacion, etiqueta } = normalizeClasificacionArrastre(raw)
  const hitosSource = raw.linea_tiempo ?? raw.hitos ?? raw.timeline
  const enlaces = asRecord(raw.enlaces_oficiales)
  const fuenteRaw = raw.fuente ?? raw.fuente_oficial
  const comunaRec = asRecord(raw.comuna)
  const comunasArr = Array.isArray(raw.comunas) ? raw.comunas.map(String).filter(Boolean) : []
  const comunaCut = pickString(comunaRec, ['cut', 'codigo']) ?? pickString(raw, ['comuna_cut', 'cut'])
  const comunaNombre =
    (comunasArr.length > 0 ? comunasArr.join(', ') : null) ??
    pickString(comunaRec, ['nombre', 'municipio']) ??
    (typeof raw.comuna === 'string' ? asString(raw.comuna) : null) ??
    pickString(raw, ['comuna_nombre']) ??
    (comunaCut ? getComunaNombre(comunaCut) : null)

  const urlProyecto = pickString(enlaces, ['ficha_contrato_sipro', 'ficha_proyecto_sipro', 'mercado_publico'])
  const fuente: FuenteOficial | null = fuenteRaw
    ? normalizeFuente(fuenteRaw, 'MOP DGOP · SIPRO · Mercado Público', endpoint)
    : urlProyecto
      ? {
          nombre: 'MOP DGOP · Visor Obras / SIPRO',
          institucion: pickString(raw, ['institucion']) ?? 'Ministerio de Obras Públicas',
          periodo: pickString(raw, ['fecha_corte_visor']),
          unidad: 'millones CLP',
          cobertura: comunaNombre,
          url: urlProyecto,
          endpoint,
          actualizado_en: pickString(raw, ['fecha_corte_visor']),
          extraido_en: null,
          codigos_series: [],
          nota: null,
        }
      : null

  return {
    id: pickString(raw, ['id_contrato', 'id', 'codigo_contrato', 'codigo_bip', 'bip']) ?? `proy-${idx}`,
    codigo_bip: pickString(raw, ['codigo_bip', 'bip']),
    codigo_contrato: pickString(raw, ['id_contrato', 'codigo_contrato', 'contrato', 'codigo_licitacion']),
    nombre: pickString(raw, ['nombre_contrato', 'nombre_proyecto', 'nombre', 'titulo', 'nombre_obra', 'obra', 'descripcion']) ?? 'Obra sin título',
    comuna: comunaNombre,
    comuna_cut: comunaCut,
    institucion: pickString(raw, ['institucion', 'organismo', 'mandante', 'servicio']) ?? 'Institución no informada',
    clasificacion_arrastre: clasificacion,
    etiqueta_arrastre: pickString(raw, ['etiqueta_arrastre', 'etiqueta']) ?? etiqueta,
    administracion_origen: pickString(raw, ['administracion_contratacion', 'administracion_origen', 'gestion_origen']),
    frase_radial: pickString(raw, ['frase_radial', 'frase_ciudadana', 'frase', 'resumen_una_oracion']),
    costo_total_millones: pickNumber(raw, [
      'costo_total_contrato_millones',
      'costo_total_presupuestado_millones',
      'costo_total_millones',
      'monto_contratado_millones',
      'monto_total_millones',
      'costo_contrato_millones',
    ]),
    compromiso_anio_millones: pickNumber(raw, [
      'compromiso_anio_millones',
      'comprometido_anio_millones',
      'presupuesto_anio_millones',
    ]),
    pagado_anio_millones: pickNumber(raw, [
      'pagado_anio_millones',
      'ejecutado_anio_millones',
      'pago_anio_millones',
    ]),
    pagado_anios_anteriores_millones: pickNumber(raw, [
      'pagado_anios_anteriores_millones',
      'pagado_previo_millones',
      'acumulado_anterior_millones',
    ]),
    saldo_por_pagar_millones: pickNumber(raw, ['saldo_pendiente_millones', 'saldo_por_pagar_millones', 'saldo_millones']),
    hitos: normalizeHitos(hitosSource),
    fuente,
    motivo_insuficiente: pickString(raw, ['motivo_insuficiencia', 'motivo_insuficiente', 'motivo_exclusion', 'motivo_brecha']),
  }
}

export async function fetchAysenProyectos(
  params: AysenProyectosParams,
  signal?: AbortSignal,
): Promise<AysenProyectosResponse> {
  const qs = new URLSearchParams({ anio: String(params.anio) })
  if (params.comuna && params.comuna.trim()) qs.set('comuna', params.comuna.trim())
  if (params.institucion && params.institucion.trim()) qs.set('institucion', params.institucion.trim())
  if (params.q && params.q.trim()) qs.set('q', params.q.trim())
  const path = `/aysen/proyectos?${qs.toString()}`
  const raw = await requestApiJson<Record<string, unknown>>(path, { signal })

  const metricas = asRecord(raw.metricas_arrastre) ?? asRecord(raw.resumen_arrastre) ?? {}
  const preguntaPagadoRaw =
    raw.pagos_contratos_anteriores ??
    raw.pregunta_pagado_arrastre ??
    raw.arrastre_pagado ??
    metricas.pagado_contratos_anteriores ??
    metricas.pagado_arrastre
  const preguntaComprometidoRaw =
    raw.arrastre_presupuesto ??
    raw.pregunta_presupuesto_comprometido ??
    metricas.presupuesto_comprometido ??
    metricas.presupuesto_arrastre

  const rawList = Array.isArray(raw.proyectos_documentados)
    ? raw.proyectos_documentados
    : Array.isArray(raw.proyectos)
      ? raw.proyectos
      : Array.isArray(raw.obras)
        ? raw.obras
        : Array.isArray(raw.items)
          ? raw.items
          : []

  const normalizedMain = rawList
    .map(item => asRecord(item))
    .filter((item): item is Record<string, unknown> => item !== null)
    .map((item, idx) => normalizeProyecto(item, idx, `/api/v1${path}`))

  const rawInsuf =
    (Array.isArray(raw.proyectos_informacion_insuficiente) && raw.proyectos_informacion_insuficiente) ||
    (Array.isArray(raw.proyectos_insuficientes) && raw.proyectos_insuficientes) ||
    (Array.isArray(raw.excluidos) && raw.excluidos) ||
    []

  const explicitInsuf = rawInsuf
    .map(item => asRecord(item))
    .filter((item): item is Record<string, unknown> => item !== null)
    .map((item, idx) => {
      const p = normalizeProyecto(item, idx + 10_000, `/api/v1${path}`)
      return { ...p, clasificacion_arrastre: 'insuficiente' as const, etiqueta_arrastre: 'Información insuficiente' }
    })

  const proyectos = normalizedMain.filter(p => p.clasificacion_arrastre !== 'insuficiente')
  const proyectos_insuficientes =
    explicitInsuf.length > 0
      ? explicitInsuf
      : normalizedMain.filter(p => p.clasificacion_arrastre === 'insuficiente')

  const institucionesSet = new Set<string>([
    ...asStringArray(raw.instituciones_disponibles ?? raw.instituciones),
    ...proyectos.map(p => p.institucion).filter(Boolean),
  ])
  if (!Array.from(institucionesSet).some(i => i.toLowerCase().includes('vialidad'))) {
    institucionesSet.add('Dirección de Vialidad')
  }

  return {
    anio: asIntOrNull(raw.anio_seleccionado ?? raw.anio) ?? params.anio,
    comuna: pickString(raw, ['comuna']) ?? (params.comuna?.trim() || null),
    institucion: pickString(raw, ['institucion']) ?? (params.institucion?.trim() || null),
    q: pickString(raw, ['q']) ?? (params.q?.trim() || ''),
    en_curso: Boolean(raw.en_curso ?? raw.anio_en_curso ?? params.anio >= new Date().getFullYear()),
    mes_corte_nombre: pickString(raw, ['mes_corte_nombre', 'mes_nombre']),
    instituciones_disponibles: Array.from(institucionesSet),
    pregunta_pagado_arrastre: normalizePreguntaArrastre(
      preguntaPagadoRaw,
      'De lo pagado este año, ¿cuánto corresponde a contratos firmados antes de que asumiera esta administración?',
      `/api/v1${path}`,
    ),
    pregunta_presupuesto_comprometido: normalizePreguntaArrastre(
      preguntaComprometidoRaw,
      'Del presupuesto de inversión de este año, ¿cuánto ya estaba comprometido por proyectos de años anteriores?',
      `/api/v1${path}`,
    ),
    proyectos,
    proyectos_insuficientes,
    total_proyectos: asIntOrNull(raw.total_proyectos_filtrados ?? raw.total_proyectos ?? raw.total) ?? proyectos.length,
    fuentes: normalizeFuentesList(
      raw.fuentes ?? raw.fuente ?? raw.fuente_trazabilidad,
      'MOP DGOP · SIPRO · Mercado Público',
      `/api/v1${path}`,
    ),
    actualizado_en: pickString(raw, ['actualizado_en', 'extraido_en']),
  }
}
