import type { Observation } from './api'

export type Derived = 'acumulado' | 'indice'

const scale = 100_000_000n

function integer(value: string, precision: number) {
  const [whole, decimals = ''] = value.split('.')
  return BigInt(whole + decimals.padEnd(precision, '0'))
}

export function derive(row: Observation, base: Observation | undefined, metric: Derived): Observation {
  const common = { ...row, unidad: metric === 'indice' ? 'Índice' : '%' }
  if (row.valor === null) return { ...common, valor: null }
  if (!base || base.valor === null || Number(base.valor) <= 0 || row.unidad !== base.unidad ||
      row.anio_referencia !== base.anio_referencia || row.clase !== base.clase) {
    return { ...common, valor: null, clase: 'no_disponible', estado: 'faltante' }
  }
  const precision = Math.max(row.valor.split('.')[1]?.length ?? 0, base.valor.split('.')[1]?.length ?? 0)
  const start = integer(base.valor, precision)
  const end = integer(row.valor, precision)
  const numerator = (metric === 'indice' ? end : end - start) * 100n * scale
  const absolute = numerator < 0n ? -numerator : numerator
  const rounded = (absolute * 2n + start) / (start * 2n)
  const sign = numerator < 0n && rounded !== 0n ? '-' : ''
  const decimals = String(rounded % scale).padStart(8, '0').replace(/0+$/, '')
  const value = sign + [String(rounded / scale), decimals].filter(Boolean).join('.')
  return { ...common, valor: value, estado: row.estado === 'preliminar' || base.estado === 'preliminar' ? 'preliminar' : row.estado }
}

export function comparable(left: Observation, right: Observation) {
  return left.unidad === right.unidad && left.anio_referencia === right.anio_referencia
}

export function compareValues(left: string, right: string) {
  const precision = Math.max(left.split('.')[1]?.length ?? 0, right.split('.')[1]?.length ?? 0)
  const difference = integer(left, precision) - integer(right, precision)
  return difference < 0n ? -1 : difference > 0n ? 1 : 0
}
