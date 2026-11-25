import { requestApiJson, toNumberOrNull } from './bcchService'
import type { FuenteTrazabilidad } from './bcchService'

export const sinimTemplateUrl = '/api/v1/fiscal/sinim/plantilla.csv'

export interface SinimComunaRegistro {
  cut: string
  comuna: string
  anio: number | null
  etapa: string | null
  unidad_origen?: string | null
  ingresos_totales_millones: number | null
  gasto_total_devengado_millones: number | null
  gasto_corriente_millones: number | null
  gasto_inversion_millones: number | null
  fuente_archivo: string | null
}

export interface SinimComunaFaltante {
  cut: string
  comuna: string
}

export interface SinimErrorFila {
  fila?: number | null
  columna?: string | null
  valor?: string | null
  motivo: string
}

export interface SinimAysenResponse {
  cargado: boolean
  anio: number | null
  total_comunas_esperadas: number
  comunas_cargadas: number
  cobertura_pct: number
  total_ingresos_millones: number | null
  total_gasto_devengado_millones: number | null
  total_gasto_corriente_millones: number | null
  total_inversion_millones: number | null
  comunas: SinimComunaRegistro[]
  comunas_faltantes: SinimComunaFaltante[]
  errores_validacion: SinimErrorFila[]
  ultimo_archivo: string | null
  motivo_brecha: string | null
  fuente_trazabilidad: FuenteTrazabilidad
  actualizado_en: string | null
  extraido_en: string | null
}

export interface SinimImportResponse extends SinimAysenResponse {
  mensaje?: string | null
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null
}

export function normalizeSinimErrors(raw: unknown): SinimErrorFila[] {
  if (!Array.isArray(raw)) return []
  return raw.map(item => {
    if (typeof item === 'string') {
      return { motivo: item }
    }
    const rec = asRecord(item)
    if (!rec) return { motivo: String(item) }
    return {
      fila: typeof rec.fila === 'number' ? rec.fila : null,
      columna: typeof rec.columna === 'string' ? rec.columna : null,
      valor: rec.valor !== undefined && rec.valor !== null ? String(rec.valor) : null,
      motivo: String(rec.motivo ?? rec.mensaje ?? 'Error de validación'),
    }
  })
}

function normalizeSinimResponse(raw: Record<string, unknown>, endpointFallback: string): SinimAysenResponse {
  const resumen = asRecord(raw.resumen)
  const fuenteRaw = asRecord(raw.fuente_trazabilidad) ?? {}
  const rawComunas = Array.isArray(raw.comunas) ? raw.comunas : []

  const comunas: SinimComunaRegistro[] = rawComunas
    .map(item => asRecord(item))
    .filter((item): item is Record<string, unknown> => item !== null)
    .map(item => ({
      cut: String(item.cut ?? ''),
      comuna: String(item.municipio ?? item.comuna ?? item.cut ?? ''),
      anio: typeof item.anio === 'number' ? item.anio : null,
      etapa: typeof item.etapa === 'string' ? item.etapa : null,
      unidad_origen: typeof item.unidad_origen === 'string' ? item.unidad_origen : null,
      ingresos_totales_millones: toNumberOrNull(item.ingresos_totales_millones),
      gasto_total_devengado_millones: toNumberOrNull(item.gasto_total_devengado_millones),
      gasto_corriente_millones: toNumberOrNull(item.gasto_corriente_millones),
      gasto_inversion_millones: toNumberOrNull(item.gasto_inversion_millones),
      fuente_archivo: typeof item.fuente_archivo === 'string' ? item.fuente_archivo : null,
    }))

  const rawFaltantes = Array.isArray(resumen?.comunas_faltantes)
    ? resumen!.comunas_faltantes
    : Array.isArray(raw.comunas_faltantes)
      ? raw.comunas_faltantes
      : []

  const comunas_faltantes: SinimComunaFaltante[] = rawFaltantes.map(item => {
    if (typeof item === 'string') return { cut: '', comuna: item }
    const rec = asRecord(item)
    return {
      cut: String(rec?.cut ?? ''),
      comuna: String(rec?.municipio ?? rec?.comuna ?? ''),
    }
  }).filter(item => item.comuna.length > 0 || item.cut.length > 0)

  const expected = Number(resumen?.comunas_esperadas ?? raw.comunas_esperadas ?? raw.total_comunas_esperadas ?? 10)
  const loaded = Number(resumen?.comunas_cargadas ?? raw.comunas_cargadas ?? comunas.length)
  const coberturaPct = expected > 0 ? (loaded / expected) * 100 : 0

  const fuente: FuenteTrazabilidad = {
    institucion: typeof fuenteRaw.institucion === 'string'
      ? fuenteRaw.institucion
      : 'SINIM · SUBDERE (importación oficial local)',
    endpoint: endpointFallback,
    actualizado_en: typeof fuenteRaw.actualizado_en === 'string' ? fuenteRaw.actualizado_en : null,
    extraido_en: typeof fuenteRaw.actualizado_en === 'string' ? fuenteRaw.actualizado_en : null,
    unidad: typeof fuenteRaw.unidad_salida === 'string' ? fuenteRaw.unidad_salida : 'millones CLP',
    nota: typeof fuenteRaw.nota === 'string' ? fuenteRaw.nota : null,
    archivo: typeof fuenteRaw.archivo === 'string' ? fuenteRaw.archivo : null,
    sha256: typeof fuenteRaw.sha256 === 'string' ? fuenteRaw.sha256 : null,
  }

  return {
    cargado: Boolean(raw.cargado ?? comunas.length > 0),
    anio: typeof resumen?.anio === 'number' ? resumen.anio : (comunas[0]?.anio ?? null),
    total_comunas_esperadas: expected,
    comunas_cargadas: loaded,
    cobertura_pct: coberturaPct,
    total_ingresos_millones: toNumberOrNull(resumen?.total_ingresos_millones),
    total_gasto_devengado_millones: toNumberOrNull(resumen?.total_gasto_devengado_millones),
    total_gasto_corriente_millones: toNumberOrNull(resumen?.total_gasto_corriente_millones),
    total_inversion_millones: toNumberOrNull(resumen?.total_inversion_millones),
    comunas,
    comunas_faltantes,
    errores_validacion: normalizeSinimErrors(raw.errores ?? raw.errores_validacion),
    ultimo_archivo: typeof fuenteRaw.archivo === 'string' ? fuenteRaw.archivo : null,
    motivo_brecha: typeof fuenteRaw.nota === 'string' ? fuenteRaw.nota : null,
    fuente_trazabilidad: fuente,
    actualizado_en: fuente.actualizado_en ?? null,
    extraido_en: fuente.extraido_en ?? null,
  }
}

export async function fetchSinimAysen(signal?: AbortSignal): Promise<SinimAysenResponse> {
  const raw = await requestApiJson<Record<string, unknown>>('/fiscal/sinim', { signal })
  return normalizeSinimResponse(raw, '/api/v1/fiscal/sinim')
}

export async function importSinimFile(
  nombreArchivo: string,
  contenido: string,
  signal?: AbortSignal,
): Promise<SinimImportResponse> {
  const raw = await requestApiJson<Record<string, unknown>>('/fiscal/sinim/importar', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      nombre_archivo: nombreArchivo,
      contenido,
    }),
    signal,
  })
  return {
    ...normalizeSinimResponse(raw, '/api/v1/fiscal/sinim/importar'),
    mensaje: typeof raw.mensaje === 'string' ? raw.mensaje : null,
  }
}
