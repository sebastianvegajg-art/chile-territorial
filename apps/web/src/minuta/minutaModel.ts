import type {
  AysenEconomiaResponse,
  AysenPresupuestosResponse,
  AysenProyectosResponse,
  AysenResumenResponse,
  FuenteOficial,
  InstitucionPresupuesto,
  PreguntaArrastreResumen,
  ProyectoObra,
} from '../services/aysenPilotoService'

/* ============================================================
   MODELO DE DATOS · MI MINUTA (1 PÁGINA PARA ENTREVISTA / REUNIÓN)
============================================================ */

export type MinutaPreguntaId =
  | 'crecimiento_economia'
  | 'gasto_corriente_institucion'
  | 'arrastre_inversion'
  | 'gestion_obra'
  | 'libre'

export interface MinutaFuenteRef {
  id: string
  organismo: string
  documento: string
  fechaCorte: string
  url: string | null
  nota?: string | null
}

export interface MinutaCifra {
  /** Identificador estable y determinístico para evitar duplicados al agregar desde tarjetas */
  id: string
  /** Etiqueta breve de la cifra (ej. "Gasto corriente sobre ejecutado") */
  etiqueta: string
  /** Valor formateado congelado en su contexto original (ej. "85,21%" o "Sin dato disponible") */
  valorTexto: string
  /** Subvalor opcional en lenguaje radial (ej. "$85,2 de cada $100 ejecutados") */
  subvalor?: string | null
  /** Unidad de medida congelada */
  unidad: string
  /** Período congelado (ej. "2025" o "Enero–febrero 2026") */
  periodo: string
  /** Territorio congelado (ej. "Comuna de Aysén", "Región de Aysén") */
  territorio: string
  /** Institución u organismo al que pertenece el dato */
  institucion: string
  /** Explicación en una línea de qué representa o para qué sirve esta cifra */
  explicacion: string
  /** Obligatorio para porcentajes: numerador, denominador y fórmula */
  baseCalculo?: string | null
  /** Si el dato es oficial completo o sin dato disponible */
  disponible: boolean
  /** Antecedente faltante exacto cuando disponible === false */
  antecedenteFaltante?: string | null
  /** Señala si la cobertura es parcial o el año está en curso */
  coberturaParcial?: boolean
  /** Breve aclaración de cobertura parcial si aplica */
  notaCobertura?: string | null
  /** Origen en el sitio (Resumen, Economía, Presupuestos, Proyectos, Asistente) */
  origenSeccion: string
  /** Fuente oficial congelada */
  fuente: MinutaFuenteRef
  /** Fecha/hora ISO de captura */
  agregadoEn: string
}

export interface MinutaObraEjemplo {
  id: string
  nombre: string
  institucion: string
  comuna: string
  periodo: string
  clasificacion: string
  administracionOrigen: string | null
  costoTotalTexto: string
  pagadoAnioTexto: string
  saldoPorPagarTexto: string
  resumen: string
  fuente: MinutaFuenteRef
}

export interface MinutaDraft {
  version: 1
  preguntaId: MinutaPreguntaId
  titulo: string
  respuesta: string
  respuestaEditadaManualmente: boolean
  cifras: MinutaCifra[]
  obraEjemplo: MinutaObraEjemplo | null
  actualizadoEn: string
}

export interface MinutaReferenciaNumerada extends MinutaFuenteRef {
  numero: number
}

export interface MinutaExtensionReport {
  cabeEnUnaPagina: boolean
  nivel: 'ok' | 'alerta'
  resumen: string
  sugerencias: string[]
  estimacionLineas: number
}

export interface MinutaPreguntaOpcion {
  id: Exclude<MinutaPreguntaId, 'libre'>
  etiqueta: string
  descripcion: string
  filtrosResumen: string
}

export const MINUTA_PREGUNTAS: readonly MinutaPreguntaOpcion[] = [
  {
    id: 'crecimiento_economia',
    etiqueta: '¿Qué actividades explican el crecimiento o la caída de la economía de Aysén?',
    descripcion: 'Crecimiento real del PIB de Aysén vs Chile y actividades productivas que más empujaron o frenaron el año.',
    filtrosResumen: 'Período',
  },
  {
    id: 'gasto_corriente_institucion',
    etiqueta: '¿Cuánto representa el gasto corriente dentro del presupuesto ejecutado de una institución?',
    descripcion: 'Proporción de gasto corriente por cada $100 ejecutados, montos usados en el cálculo y comparación con inversión.',
    filtrosResumen: 'Período, institución y comuna (si es municipio)',
  },
  {
    id: 'arrastre_inversion',
    etiqueta: '¿Qué parte del presupuesto de inversión de este año ya estaba comprometida por proyectos anteriores?',
    descripcion: 'Presupuesto o cartera de inversión identificada, compromisos de arrastre documentados y porcentaje comprometido.',
    filtrosResumen: 'Período y territorio/institución',
  },
  {
    id: 'gestion_obra',
    etiqueta: '¿En qué gestión se contrató una obra y cuánto se pagó durante el año seleccionado?',
    descripcion: 'Traza la administración que contrató el proyecto, su costo total, lo pagado en el año y el saldo pendiente.',
    filtrosResumen: 'Período, comuna (opcional) y obra',
  },
] as const

export const MINUTA_STORAGE_KEY = 'chile_territorial_mi_minuta_v1'

/* ============================================================
   FORMATEADORES NUMÉRICOS CONSISTENTES CON EL VISUALIZADOR
============================================================ */

const num1 = new Intl.NumberFormat('es-CL', { minimumFractionDigits: 1, maximumFractionDigits: 1 })
const num2 = new Intl.NumberFormat('es-CL', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
const numInt = new Intl.NumberFormat('es-CL', { maximumFractionDigits: 0 })

export function fmtMinutaMillions(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return 'Sin dato disponible'
  const abs = Math.abs(value)
  if (abs >= 10000) return `$${numInt.format(Math.round(value))} MM`
  return `$${num1.format(value)} MM`
}

export function fmtMinutaMillionsExact1(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return 'Sin dato disponible'
  return `$${num1.format(value)} MM`
}

export function fmtMinutaPct(value: number | null | undefined, signed = false, digits: 1 | 2 = 2): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return 'Sin dato disponible'
  const formatter = digits === 1 ? num1 : num2
  const prefix = signed && value > 0 ? '+' : ''
  return `${prefix}${formatter.format(value)}%`
}

export function fmtPesosDeCada100(pct: number | null | undefined): string | null {
  if (pct === null || pct === undefined || !Number.isFinite(pct)) return null
  return `$${num1.format(pct)} de cada $100`
}

function cleanDateCut(raw?: string | null, fallbackPeriodo?: string): string {
  if (raw && raw.trim()) {
    const trimmed = raw.trim()
    if (/^\d{4}-\d{2}-\d{2}/.test(trimmed)) return trimmed.slice(0, 10)
    return trimmed
  }
  return fallbackPeriodo ? `Corte ${fallbackPeriodo}` : 'Sin fecha de corte informada'
}

export function normalizeFuenteRef(
  fuente: FuenteOficial | null | undefined,
  fallback: {
    organismo: string
    documento: string
    fechaCorte: string
    url?: string | null
  },
): MinutaFuenteRef {
  const organismo = (fuente?.institucion || fuente?.nombre || fallback.organismo).trim()
  const seriesSuffix =
    fuente?.codigos_series && fuente.codigos_series.length > 0
      ? ` (series: ${fuente.codigos_series.slice(0, 3).join(', ')}${fuente.codigos_series.length > 3 ? '…' : ''})`
      : ''
  const rawDoc = fuente?.nombre && fuente.nombre !== organismo
    ? `${fuente.nombre}${seriesSuffix}`
    : `${fallback.documento}${seriesSuffix}`
  const fechaCorte = cleanDateCut(
    fuente?.actualizado_en || fuente?.extraido_en || fuente?.periodo,
    fallback.fechaCorte,
  )
  const url = fuente?.url && /^https?:\/\//i.test(fuente.url)
    ? fuente.url
    : (fallback.url && /^https?:\/\//i.test(fallback.url) ? fallback.url : null)

  const id = `${organismo.toLowerCase()}|${rawDoc.toLowerCase()}|${fechaCorte.toLowerCase()}|${(url || '').toLowerCase()}`
  return {
    id,
    organismo,
    documento: rawDoc,
    fechaCorte,
    url,
    nota: fuente?.nota ?? null,
  }
}

/* ============================================================
   PERSISTENCIA EN LOCALSTORAGE
============================================================ */

export function createEmptyMinutaDraft(): MinutaDraft {
  return {
    version: 1,
    preguntaId: 'libre',
    titulo: '',
    respuesta: '',
    respuestaEditadaManualmente: false,
    cifras: [],
    obraEjemplo: null,
    actualizadoEn: new Date().toISOString(),
  }
}

export function loadMinutaDraft(): MinutaDraft {
  if (typeof window === 'undefined') return createEmptyMinutaDraft()
  try {
    const raw = window.localStorage.getItem(MINUTA_STORAGE_KEY)
    if (!raw) return createEmptyMinutaDraft()
    const parsed = JSON.parse(raw) as Partial<MinutaDraft>
    if (!parsed || typeof parsed !== 'object') return createEmptyMinutaDraft()
    return {
      version: 1,
      preguntaId: parsed.preguntaId ?? 'libre',
      titulo: typeof parsed.titulo === 'string' ? parsed.titulo : '',
      respuesta: typeof parsed.respuesta === 'string' ? parsed.respuesta : '',
      respuestaEditadaManualmente: Boolean(parsed.respuestaEditadaManualmente),
      cifras: Array.isArray(parsed.cifras) ? parsed.cifras : [],
      obraEjemplo: parsed.obraEjemplo && typeof parsed.obraEjemplo === 'object' ? parsed.obraEjemplo : null,
      actualizadoEn: typeof parsed.actualizadoEn === 'string' ? parsed.actualizadoEn : new Date().toISOString(),
    }
  } catch {
    return createEmptyMinutaDraft()
  }
}

export function saveMinutaDraft(draft: MinutaDraft): void {
  if (typeof window === 'undefined') return
  try {
    window.localStorage.setItem(MINUTA_STORAGE_KEY, JSON.stringify(draft))
  } catch {
    // Silencioso si el navegador bloquea almacenamiento en modo privado
  }
}

/* ============================================================
   REFERENCIAS NUMERADAS AL PIE ([1], [2], ...)
============================================================ */

export function buildReferenciasNumeradas(draft: MinutaDraft): {
  referencias: MinutaReferenciaNumerada[]
  indicePorCifraId: Record<string, number>
  indiceObra: number | null
} {
  const map = new Map<string, MinutaReferenciaNumerada>()
  const referencias: MinutaReferenciaNumerada[] = []
  const indicePorCifraId: Record<string, number> = {}

  const register = (fuente: MinutaFuenteRef): number => {
    const existing = map.get(fuente.id)
    if (existing) return existing.numero
    const numero = referencias.length + 1
    const entry: MinutaReferenciaNumerada = { ...fuente, numero }
    map.set(fuente.id, entry)
    referencias.push(entry)
    return numero
  }

  for (const cifra of draft.cifras) {
    indicePorCifraId[cifra.id] = register(cifra.fuente)
  }

  const indiceObra = draft.obraEjemplo ? register(draft.obraEjemplo.fuente) : null

  return { referencias, indicePorCifraId, indiceObra }
}

/* ============================================================
   REDACCIÓN AUTOMÁTICA DE RESPUESTA DE 2 LÍNEAS EN LENGUAJE COTIDIANO
============================================================ */

export function generarRespuestaCotidiana(draft: MinutaDraft): string {
  const cifras = draft.cifras
  const obra = draft.obraEjemplo

  if (cifras.length === 0 && !obra) {
    return ''
  }

  const disponibles = cifras.filter(c => c.disponible)
  const faltantes = cifras.filter(c => !c.disponible)
  const parciales = cifras.filter(c => c.coberturaParcial)

  // Caso 1: Ninguna cifra disponible -> explicar el antecedente faltante de frente
  if (disponibles.length === 0 && faltantes.length > 0) {
    const primera = faltantes[0]
    const motivo =
      primera.antecedenteFaltante ||
      `falta la publicación oficial de ${primera.fuente.organismo} para ${primera.periodo}`
    return `Sin dato disponible para ${primera.institucion} (${primera.periodo}): ${motivo}. Conviene señalar al aire que el registro oficial aún no está publicado y no corresponde estimar la cifra.`
  }

  // Caso 2: Pregunta específica de gasto corriente institucional
  if (draft.preguntaId === 'gasto_corriente_institucion') {
    const pctCifra = disponibles.find(c => c.unidad.includes('%') && c.etiqueta.toLowerCase().includes('corriente'))
    const ejecCifra = disponibles.find(
      c => c.id !== pctCifra?.id && !c.unidad.includes('%') && c.etiqueta.toLowerCase().includes('ejecutado'),
    )
    const corrCifra = disponibles.find(
      c => c.id !== pctCifra?.id && !c.unidad.includes('%') && c.etiqueta.toLowerCase().includes('corriente'),
    )
    if (pctCifra) {
      const pesos = (pctCifra.subvalor || `${pctCifra.valorTexto} de lo ejecutado`).replace(/\s+ejecutados$/i, '')
      const instConArticulo = pctCifra.institucion.startsWith('Municipalidad') || pctCifra.institucion.startsWith('Dirección')
        ? `la ${pctCifra.institucion}`
        : `el ${pctCifra.institucion}`
      const detalleMontos =
        corrCifra && ejecCifra
          ? ` (${corrCifra.valorTexto} sobre ${ejecCifra.valorTexto} devengados)`
          : pctCifra.baseCalculo
            ? ` (${pctCifra.baseCalculo})`
            : ''
      const linea1 = `En ${pctCifra.periodo}, ${pesos} ejecutados por ${instConArticulo} correspondieron a gasto corriente${detalleMontos}.`
      const notaExtra =
        faltantes.length > 0
          ? ` Falta antecedente para ${faltantes[0].etiqueta.toLowerCase()}: ${faltantes[0].antecedenteFaltante || 'dato oficial pendiente'}.`
          : parciales.length > 0
            ? ` Cobertura parcial: ${parciales[0].notaCobertura || 'período en curso sujeto a actualización oficial'}.`
            : ` Cifra verificada directamente en ${pctCifra.fuente.organismo}.`
      return `${linea1}${notaExtra}`
    }
  }

  // Caso 3: Pregunta de arrastre / compromisos anteriores
  if (draft.preguntaId === 'arrastre_inversion') {
    const pct = disponibles.find(c => c.unidad.includes('%'))
    const monto = disponibles.find(c => c.etiqueta.toLowerCase().includes('compromiso') && !c.unidad.includes('%'))
    if (pct) {
      const linea1 = `En ${pct.periodo}, ${pct.valorTexto} de la inversión identificada en ${pct.territorio} correspondía a compromisos de proyectos anteriores${monto ? ` (${monto.valorTexto})` : ''}.`
      const linea2 =
        parciales.length > 0
          ? ` Cobertura parcial: ${parciales[0].notaCobertura || 'solo incluye obras con fecha de contratación y pagos documentados'}.`
          : ` La medición se calcula únicamente sobre obras con contrato y respaldo oficial verificable.`
      return `${linea1}${linea2}`
    }
    if (faltantes.length > 0 && monto) {
      return `En ${monto.periodo} se documentan ${monto.valorTexto} en compromisos anteriores, pero el porcentaje figura sin dato disponible: ${faltantes[0].antecedenteFaltante || 'falta un denominador oficial comparable'}.`
    }
  }

  // Caso 4: Pregunta de crecimiento económico de Aysén
  if (draft.preguntaId === 'crecimiento_economia') {
    const pib = disponibles.find(c => c.etiqueta.toLowerCase().includes('crecimiento'))
    const motor = disponibles.find(c => c.id !== pib?.id)
    if (pib) {
      const linea1 = `En ${pib.periodo}, la economía de Aysén registró una variación real de ${pib.valorTexto}${pib.subvalor ? ` (${pib.subvalor})` : ''}.`
      const linea2 = motor
        ? ` ${motor.etiqueta}: ${motor.valorTexto}, según Cuentas Nacionales del Banco Central.`
        : ` Resultado verificado en las Cuentas Nacionales Regionales del Banco Central de Chile.`
      const avisoParcial = parciales.length > 0 ? ` Cobertura parcial: ${parciales[0].notaCobertura || 'corte sujeto a revisión'}.` : ''
      return `${linea1}${linea2}${avisoParcial}`
    }
  }

  // Caso 5: Pregunta sobre una obra específica
  if (draft.preguntaId === 'gestion_obra' && obra) {
    const origen = obra.administracionOrigen
      ? `contratada durante la gestión ${obra.administracionOrigen}`
      : 'sin fecha de administración de origen publicada'
    const linea1 = `La obra «${obra.nombre}» (${obra.institucion}) fue ${origen}, con un costo total de ${obra.costoTotalTexto}.`
    const linea2 = ` Durante ${obra.periodo} registró pagos por ${obra.pagadoAnioTexto} y mantiene un saldo por pagar de ${obra.saldoPorPagarTexto}.`
    return `${linea1}${linea2}`
  }

  // Caso general: combinación libre de cifras guardadas al navegar
  const primera = disponibles[0]
  const segunda = disponibles[1]
  let linea1 = primera
    ? `En ${primera.periodo}, ${primera.etiqueta.toLowerCase()} en ${primera.territorio} (${primera.institucion}) alcanzó ${primera.valorTexto}${primera.subvalor ? ` (${primera.subvalor})` : ''}.`
    : obra
      ? `Ejemplo seleccionado: ${obra.nombre} (${obra.institucion}), con pagos por ${obra.pagadoAnioTexto} en ${obra.periodo}.`
      : ''

  let linea2 = ''
  if (segunda) {
    linea2 = ` Como complemento, ${segunda.etiqueta.toLowerCase()} registró ${segunda.valorTexto} (${segunda.periodo}).`
  } else if (obra && primera) {
    linea2 = ` Como ejemplo concreto, «${obra.nombre}» registró pagos por ${obra.pagadoAnioTexto} en ${obra.periodo}.`
  } else if (primera) {
    linea2 = ` Dato respaldado por ${primera.fuente.organismo} (${primera.fuente.fechaCorte}).`
  }

  if (faltantes.length > 0) {
    linea2 += ` Queda sin dato disponible ${faltantes[0].etiqueta.toLowerCase()} (${faltantes[0].antecedenteFaltante || 'antecedente oficial pendiente'}).`
  } else if (parciales.length > 0) {
    linea2 += ` Cobertura parcial: ${parciales[0].notaCobertura || 'ver alcance en las fuentes al pie'}.`
  }

  return `${linea1}${linea2}`.trim()
}

/* ============================================================
   CONTROL DE EXTENSIÓN PARA 1 PÁGINA CARTA VERTICAL
============================================================ */

export function analizarExtensionUnaPagina(
  draft: MinutaDraft,
  measuredHeightPx?: number | null,
): MinutaExtensionReport {
  const sugerencias: string[] = []
  const { referencias } = buildReferenciasNumeradas(draft)

  if (draft.cifras.length > 3) {
    sugerencias.push(
      `Tienes ${draft.cifras.length} cifras guardadas; deja hasta 3 cifras clave para que la minuta quepa en una hoja y sea fácil de leer al aire.`,
    )
  }
  if (draft.titulo.trim().length > 130) {
    sugerencias.push(
      `El título tiene ${draft.titulo.trim().length} caracteres; acórtalo a menos de 125 caracteres (una o dos líneas).`,
    )
  }
  if (draft.respuesta.trim().length > 310) {
    sugerencias.push(
      `La respuesta tiene ${draft.respuesta.trim().length} caracteres; sintetízala a dos líneas (máximo ~280 caracteres) para lectura rápida.`,
    )
  }
  const longExpl = draft.cifras.filter(c => c.explicacion.length > 140)
  if (longExpl.length > 0) {
    sugerencias.push(
      `Hay ${longExpl.length} explicación(es) extensas debajo de las cifras; mantenerlas en una línea mejora el espacio.`,
    )
  }
  if (referencias.length > 4) {
    sugerencias.push(
      `Se acumulan ${referencias.length} fuentes al pie; prioriza cifras de las fuentes más relevantes para no desbordar el pie de página.`,
    )
  }

  // Estimación estructural en "unidades de línea" (Carta vertical útil ≈ 46 líneas cómodas en 3 columnas)
  const tituloLineas = Math.max(1, Math.ceil((draft.titulo.length || 40) / 62))
  const respuestaLineas = Math.max(2, Math.ceil((draft.respuesta.length || 120) / 86))
  // En impresión Carta vertical hasta 3 cifras van en 1 fila de 3 columnas (no apiladas)
  const filasCifras = draft.cifras.length === 0 ? 0 : Math.ceil(draft.cifras.length / 3)
  const maxCardLineas = draft.cifras.reduce((mx, c) => {
    const baseExtra = c.baseCalculo ? 2 : 0
    const missingExtra = !c.disponible ? 1.5 : 0
    return Math.max(mx, 8 + baseExtra + missingExtra)
  }, 0)
  const cifrasLineas = filasCifras * maxCardLineas
  const obraLineas = draft.obraEjemplo ? 7.5 : 0
  const fuentesLineas = 2 + referencias.length * 1.9
  const estimacionLineas = Math.round(6 + tituloLineas + respuestaLineas + cifrasLineas + obraLineas + fuentesLineas)

  // Carta vertical imprimible (11in - 1in márgenes = ~10in; vista digital tiene ~15% más aire vertical)
  const heightOverflow = typeof measuredHeightPx === 'number' && measuredHeightPx > 1060

  if (heightOverflow && sugerencias.length === 0) {
    if (draft.obraEjemplo && draft.cifras.length >= 3) {
      sugerencias.push(
        'La hoja supera el alto de una página carta; quita la obra de ejemplo o reduce de 3 a 2 cifras clave antes de imprimir.',
      )
    } else {
      sugerencias.push(
        'La vista previa supera el alto de una página carta; acorta la respuesta en 2 líneas o quita una cifra secundaria.',
      )
    }
  } else if (estimacionLineas > 46 && sugerencias.length === 0) {
    sugerencias.push(
      'El borrador está cerca del límite de una página carta; acorta la respuesta o reduce una cifra antes de imprimir.',
    )
  }

  const cabeEnUnaPagina = !heightOverflow && estimacionLineas <= 46 && draft.cifras.length <= 3

  return {
    cabeEnUnaPagina,
    nivel: cabeEnUnaPagina ? 'ok' : 'alerta',
    resumen: cabeEnUnaPagina
      ? 'Cabe en 1 página carta vertical (lista para imprimir o guardar como PDF).'
      : 'El contenido puede exceder 1 página carta. Revisa las sugerencias para acortar antes de imprimir.',
    sugerencias,
    estimacionLineas,
  }
}

/* ============================================================
   CONSTRUCTORES DE SNAPSHOTS CONGELADOS DESDE CADA PESTAÑA
   (Cualquier cambio posterior de filtros en la página NO altera
    estas cifras porque guardan valor, unidad, período, territorio,
    institución, base de cálculo y fuente al momento de capturar.)
============================================================ */

export function cifraFromResumenEconomia(resumen: AysenResumenResponse): MinutaCifra {
  const eco = resumen.evolucion_economica
  const disponible = eco.disponible && eco.crecimiento_real_pct !== null
  const periodo = eco.periodo || String(resumen.anio)
  const fuente = normalizeFuenteRef(eco.fuente, {
    organismo: 'Banco Central de Chile',
    documento: 'Cuentas Nacionales · PIB Regional de Aysén (BDE)',
    fechaCorte: resumen.actualizado_en || periodo,
    url: 'https://si3.bcentral.cl/Siete/ES/Siete/Cuadro/CAP_CCNN/MN_CCNN76/CCNN2018_PIB_REGIONAL',
  })

  return {
    id: `resumen-eco-${resumen.anio}`,
    etiqueta: `Crecimiento real del PIB de Aysén (${resumen.anio})`,
    valorTexto: disponible ? fmtMinutaPct(eco.crecimiento_real_pct, true, 1) : 'Sin dato disponible',
    subvalor:
      disponible && eco.crecimiento_chile_pct !== null
        ? `Chile: ${fmtMinutaPct(eco.crecimiento_chile_pct, true, 1)}`
        : null,
    unidad: eco.unidad || 'Variación real anual (%)',
    periodo,
    territorio: 'Región de Aysén',
    institucion: 'Banco Central de Chile (Cuentas Nacionales)',
    explicacion:
      'Mide si la producción real de bienes y servicios de Aysén creció o cayó en el año respecto del período anterior.',
    baseCalculo: 'Variación anual de volúmenes encadenados (referencia 2018) sobre el año inmediatamente anterior.',
    disponible,
    antecedenteFaltante: disponible
      ? null
      : eco.sin_dato_motivo || `Falta la publicación oficial del PIB regional anual ${resumen.anio} por parte del Banco Central de Chile.`,
    coberturaParcial: Boolean(resumen.en_curso),
    notaCobertura: resumen.en_curso ? resumen.aviso_anio_en_curso || 'Año en curso; cierre anual pendiente.' : null,
    origenSeccion: 'Resumen',
    fuente,
    agregadoEn: new Date().toISOString(),
  }
}

export function cifraFromResumenInversion(resumen: AysenResumenResponse): MinutaCifra {
  const inv = resumen.inversion_publica
  const disponible = inv.disponible && inv.monto_millones !== null
  const periodo = inv.periodo || String(resumen.anio)
  const fuente = normalizeFuenteRef(inv.fuente, {
    organismo: 'DIPRES / SUBDERE SINIM',
    documento: `Ejecución de inversión pública registrada en Aysén (${periodo})`,
    fechaCorte: resumen.actualizado_en || periodo,
    url: 'https://www.dipres.gob.cl',
  })
  const cubiertas = inv.instituciones_cubiertas.length > 0 ? inv.instituciones_cubiertas.join(', ') : 'Instituciones con corte oficial'

  return {
    id: `resumen-inv-${resumen.anio}-${resumen.comuna_codigo || 'reg'}`,
    etiqueta: `Inversión pública registrada en Aysén (${resumen.anio})`,
    valorTexto: disponible ? fmtMinutaMillions(inv.monto_millones) : 'Sin dato disponible',
    subvalor:
      inv.variacion_mismo_periodo_pct !== null
        ? `${fmtMinutaPct(inv.variacion_mismo_periodo_pct, true, 1)} vs mismo período`
        : null,
    unidad: inv.unidad || 'Millones de pesos ($ MM)',
    periodo,
    territorio: resumen.comuna_nombre ? `Región de Aysén (incl. ${resumen.comuna_nombre})` : 'Región de Aysén',
    institucion: cubiertas,
    explicacion: `Suma la ejecución de inversión y gasto de capital publicada por las instituciones cubiertas (${cubiertas}).`,
    baseCalculo: null,
    disponible,
    antecedenteFaltante: disponible
      ? null
      : inv.sin_dato_motivo || `Falta la ejecución presupuestaria de inversión con corte oficial para ${resumen.anio}.`,
    coberturaParcial: Boolean(resumen.en_curso || inv.instituciones_cubiertas.length < 3),
    notaCobertura: resumen.en_curso
      ? `Corte parcial del año en curso (${resumen.mes_corte_nombre || periodo}); cobertura: ${cubiertas}.`
      : `Cobertura institucional incluida: ${cubiertas}.`,
    origenSeccion: 'Resumen',
    fuente,
    agregadoEn: new Date().toISOString(),
  }
}

export function cifraFromResumenArrastre(resumen: AysenResumenResponse): MinutaCifra {
  const arr = resumen.arrastre
  const hasPct = arr.porcentaje_pct !== null
  const disponible = arr.disponible && (hasPct || arr.monto_millones !== null)
  const periodo = arr.periodo || String(resumen.anio)
  const fuente = normalizeFuenteRef(arr.fuente, {
    organismo: 'MOP / DIPRES BIP',
    documento: `Contratos y proyectos de inversión con arrastre documentado (${periodo})`,
    fechaCorte: resumen.actualizado_en || periodo,
    url: 'https://www.mop.gob.cl',
  })

  return {
    id: `resumen-arrastre-${resumen.anio}`,
    etiqueta: `Compromisos de proyectos anteriores (${resumen.anio})`,
    valorTexto: hasPct
      ? fmtMinutaPct(arr.porcentaje_pct, false, 1)
      : arr.monto_millones !== null
        ? fmtMinutaMillions(arr.monto_millones)
        : 'Sin dato disponible',
    subvalor: hasPct && arr.monto_millones !== null ? `Equivale a ${fmtMinutaMillions(arr.monto_millones)}` : null,
    unidad: hasPct ? '% sobre pagos/inversión evaluada' : 'Millones de pesos ($ MM)',
    periodo,
    territorio: 'Región de Aysén',
    institucion: 'Obras con contrato oficial verificado (MOP / BIP)',
    explicacion:
      'Muestra qué parte de la inversión ejecutada o comprometida en el año ya venía contratada desde años previos.',
    baseCalculo: arr.base_calculo || 'Porcentaje sobre el total pagado en obras con fecha de contratación verificable.',
    disponible,
    antecedenteFaltante: disponible
      ? null
      : arr.sin_dato_motivo || `Falta respaldo de fecha de contratación o pagos del año ${resumen.anio} para calcular el arrastre.`,
    coberturaParcial: Boolean(arr.proyectos_excluidos && arr.proyectos_excluidos > 0) || Boolean(resumen.en_curso),
    notaCobertura:
      arr.total_proyectos_evaluados !== null
        ? `Basado en ${arr.total_proyectos_evaluados} obras con fecha verificada${arr.proyectos_excluidos ? ` (${arr.proyectos_excluidos} excluidas por información insuficiente)` : ''}.`
        : null,
    origenSeccion: 'Resumen',
    fuente,
    agregadoEn: new Date().toISOString(),
  }
}

export function cifraFromInstitucionPresupuesto(
  inst: InstitucionPresupuesto,
  anio: number,
  options?: {
    mesCorteNombre?: string | null
    enCurso?: boolean
    modo?: 'gasto_corriente_pct' | 'gasto_ejecutado' | 'gasto_corriente_monto' | 'inversion'
  },
): MinutaCifra {
  const modo = options?.modo ?? 'gasto_corriente_pct'
  const periodo = options?.enCurso && options?.mesCorteNombre
    ? `${options.mesCorteNombre} ${anio} (en curso)`
    : String(anio)

  const fuente = normalizeFuenteRef(inst.fuente, {
    organismo: inst.rol_billetera === 'municipal' ? 'SUBDERE · SINIM' : 'DIPRES',
    documento: `Ejecución presupuestaria ${inst.nombre} (${anio})`,
    fechaCorte: inst.fuente?.actualizado_en || periodo,
    url: inst.fuente?.url ?? null,
  })

  const baseFormula =
    inst.gasto_corriente_millones !== null && inst.gasto_ejecutado_millones !== null
      ? `Gasto corriente (${fmtMinutaMillionsExact1(inst.gasto_corriente_millones)}) ÷ Gasto ejecutado total (${fmtMinutaMillionsExact1(inst.gasto_ejecutado_millones)}) × 100`
      : inst.base_calculo || 'Porcentaje sobre gasto ejecutado total informado por la fuente oficial.'

  const missingReason =
    inst.sin_dato_motivo ||
    (inst.rol_billetera === 'municipal'
      ? `Falta la publicación oficial del Balance de Ejecución Presupuestaria (BEP) SINIM de ${inst.nombre} para ${anio} por parte de SUBDERE.`
      : `Falta el informe oficial de ejecución presupuestaria de ${inst.nombre} para ${anio}.`)

  if (modo === 'gasto_ejecutado') {
    const disponible = inst.gasto_ejecutado_millones !== null
    return {
      id: `presup-${inst.id}-${anio}-ejecutado`,
      etiqueta: `Gasto ejecutado total · ${inst.nombre}`,
      valorTexto: disponible ? fmtMinutaMillionsExact1(inst.gasto_ejecutado_millones) : 'Sin dato disponible',
      subvalor:
        inst.avance_ejecucion_pct !== null && inst.presupuesto_vigente_millones !== null
          ? `Avance ${fmtMinutaPct(inst.avance_ejecucion_pct, false, 1)} sobre vigente (${fmtMinutaMillionsExact1(inst.presupuesto_vigente_millones)})`
          : null,
      unidad: 'Millones de pesos ($ MM)',
      periodo,
      territorio: inst.territorio_etiqueta,
      institucion: inst.nombre,
      explicacion: 'Fija el total efectivamente devengado en el período, que sirve de denominador para calcular proporciones.',
      baseCalculo: null,
      disponible,
      antecedenteFaltante: disponible ? null : missingReason,
      coberturaParcial: Boolean(options?.enCurso),
      notaCobertura: options?.enCurso ? `Ejecución acumulada al corte ${periodo}.` : null,
      origenSeccion: 'Presupuestos',
      fuente,
      agregadoEn: new Date().toISOString(),
    }
  }

  if (modo === 'gasto_corriente_monto') {
    const disponible = inst.gasto_corriente_millones !== null
    return {
      id: `presup-${inst.id}-${anio}-corriente-mm`,
      etiqueta: `Monto en gasto corriente · ${inst.nombre}`,
      valorTexto: disponible ? fmtMinutaMillionsExact1(inst.gasto_corriente_millones) : 'Sin dato disponible',
      subvalor:
        inst.inversion_millones !== null
          ? `Inversión / capital: ${fmtMinutaMillionsExact1(inst.inversion_millones)} (${fmtMinutaPct(inst.inversion_pct, false, 2)})`
          : null,
      unidad: 'Millones de pesos ($ MM)',
      periodo,
      territorio: inst.territorio_etiqueta,
      institucion: inst.nombre,
      explicacion: 'Expresa en pesos el monto destinado a personal, bienes, servicios de consumo y transferencias corrientes.',
      baseCalculo: null,
      disponible,
      antecedenteFaltante: disponible ? null : missingReason,
      coberturaParcial: Boolean(options?.enCurso),
      notaCobertura: options?.enCurso ? `Corte acumulado ${periodo}.` : null,
      origenSeccion: 'Presupuestos',
      fuente,
      agregadoEn: new Date().toISOString(),
    }
  }

  if (modo === 'inversion') {
    const disponible = inst.inversion_pct !== null || inst.inversion_millones !== null
    return {
      id: `presup-${inst.id}-${anio}-inversion`,
      etiqueta: `Inversión y gasto de capital · ${inst.nombre}`,
      valorTexto:
        inst.inversion_pct !== null
          ? fmtMinutaPct(inst.inversion_pct, false, 2)
          : fmtMinutaMillionsExact1(inst.inversion_millones),
      subvalor:
        inst.inversion_pct !== null && inst.inversion_millones !== null
          ? `${fmtPesosDeCada100(inst.inversion_pct)} (${fmtMinutaMillionsExact1(inst.inversion_millones)})`
          : null,
      unidad: inst.inversion_pct !== null ? '% sobre gasto ejecutado' : 'Millones de pesos ($ MM)',
      periodo,
      territorio: inst.territorio_etiqueta,
      institucion: inst.nombre,
      explicacion: 'Permite contrastar cuánto del presupuesto ejecutado se destinó a inversión frente al gasto corriente.',
      baseCalculo:
        inst.inversion_millones !== null && inst.gasto_ejecutado_millones !== null
          ? `Inversión (${fmtMinutaMillionsExact1(inst.inversion_millones)}) ÷ Gasto ejecutado total (${fmtMinutaMillionsExact1(inst.gasto_ejecutado_millones)}) × 100`
          : inst.base_calculo || 'Porcentaje sobre gasto ejecutado total.',
      disponible,
      antecedenteFaltante: disponible ? null : missingReason,
      coberturaParcial: Boolean(options?.enCurso),
      notaCobertura: options?.enCurso ? `Corte acumulado ${periodo}.` : null,
      origenSeccion: 'Presupuestos',
      fuente,
      agregadoEn: new Date().toISOString(),
    }
  }

  // Default: gasto_corriente_pct
  const disponible = inst.gasto_corriente_pct !== null
  return {
    id: `presup-${inst.id}-${anio}-corriente-pct`,
    etiqueta: `Gasto corriente sobre ejecutado · ${inst.nombre}`,
    valorTexto: disponible ? fmtMinutaPct(inst.gasto_corriente_pct, false, 2) : 'Sin dato disponible',
    subvalor: disponible ? `${fmtPesosDeCada100(inst.gasto_corriente_pct)} ejecutados` : null,
    unidad: '% sobre gasto ejecutado',
    periodo,
    territorio: inst.territorio_etiqueta,
    institucion: inst.nombre,
    explicacion: 'Responde cuántos pesos de cada $100 ejecutados se destinaron a funcionamiento y operación corriente.',
    baseCalculo: baseFormula,
    disponible,
    antecedenteFaltante: disponible ? null : missingReason,
    coberturaParcial: Boolean(options?.enCurso),
    notaCobertura: options?.enCurso ? `Ejecución parcial al corte ${periodo}.` : null,
    origenSeccion: 'Presupuestos',
    fuente,
    agregadoEn: new Date().toISOString(),
  }
}

export function cifraFromPreguntaArrastre(
  pregunta: PreguntaArrastreResumen,
  anio: number,
  keySuffix: 'pagado' | 'comprometido',
  territorioLabel = 'Región de Aysén',
  enCurso = false,
): MinutaCifra {
  const hasPct = pregunta.porcentaje_pct !== null
  const disponible = pregunta.disponible && hasPct
  const fuente = normalizeFuenteRef(pregunta.fuente, {
    organismo: 'MOP / DIPRES BIP',
    documento: pregunta.titulo,
    fechaCorte: String(anio),
    url: 'https://www.mop.gob.cl',
  })

  const baseCalculo =
    pregunta.numerador_millones !== null && pregunta.denominador_millones !== null
      ? `${fmtMinutaMillions(pregunta.numerador_millones)} ÷ ${fmtMinutaMillions(pregunta.denominador_millones)} × 100${pregunta.base_calculo ? ` (${pregunta.base_calculo})` : ''}`
      : pregunta.base_calculo || 'Porcentaje calculado sobre obras con fecha de contratación y montos verificados.'

  return {
    id: `proyectos-${keySuffix}-${anio}-${territorioLabel.toLowerCase().replace(/\s+/g, '-')}`,
    etiqueta: keySuffix === 'pagado'
      ? `Pagos del año en obras de arrastre (${anio})`
      : `Presupuesto de inversión comprometido por arrastre (${anio})`,
    valorTexto: hasPct ? fmtMinutaPct(pregunta.porcentaje_pct, false, 1) : 'Sin dato disponible',
    subvalor:
      pregunta.numerador_millones !== null && pregunta.denominador_millones !== null
        ? `${fmtMinutaMillions(pregunta.numerador_millones)} sobre ${fmtMinutaMillions(pregunta.denominador_millones)}`
        : null,
    unidad: '% sobre total evaluado',
    periodo: String(anio),
    territorio: territorioLabel,
    institucion: 'Contratos MOP Vialidad y proyectos BIP en Aysén',
    explicacion:
      keySuffix === 'pagado'
        ? 'Muestra qué fracción de los pagos de obras del año se fue a contratos firmados en años anteriores.'
        : 'Indica qué parte del presupuesto de inversión del año ya venía comprometida desde antes.',
    baseCalculo,
    disponible,
    antecedenteFaltante: disponible
      ? null
      : pregunta.sin_dato_motivo || 'Falta denominador de presupuesto vigente o respaldo contractual suficiente para calcular el porcentaje.',
    coberturaParcial: Boolean((pregunta.proyectos_excluidos && pregunta.proyectos_excluidos > 0) || enCurso),
    notaCobertura:
      pregunta.proyectos_incluidos !== null
        ? `Cobertura parcial: ${pregunta.proyectos_incluidos} obras incluidas${pregunta.proyectos_excluidos ? ` y ${pregunta.proyectos_excluidos} excluidas por falta de fecha oficial` : ''}.`
        : null,
    origenSeccion: 'Proyectos',
    fuente,
    agregadoEn: new Date().toISOString(),
  }
}

export function obraFromProyecto(proyecto: ProyectoObra, anio: number): MinutaObraEjemplo {
  const fuente = normalizeFuenteRef(proyecto.fuente, {
    organismo: proyecto.institucion || 'MOP / DIPRES BIP',
    documento: proyecto.codigo_bip
      ? `Ficha BIP ${proyecto.codigo_bip} · ${proyecto.nombre}`
      : proyecto.codigo_contrato
        ? `Contrato ${proyecto.codigo_contrato} · ${proyecto.nombre}`
        : proyecto.nombre,
    fechaCorte: String(anio),
    url: proyecto.fuente?.url ?? proyecto.hitos.find(h => h.documento_url)?.documento_url ?? null,
  })

  return {
    id: `obra-${proyecto.id}-${anio}`,
    nombre: proyecto.nombre,
    institucion: proyecto.institucion,
    comuna: proyecto.comuna || 'Región de Aysén',
    periodo: String(anio),
    clasificacion: proyecto.etiqueta_arrastre,
    administracionOrigen: proyecto.administracion_origen,
    costoTotalTexto: fmtMinutaMillions(proyecto.costo_total_millones),
    pagadoAnioTexto: fmtMinutaMillions(proyecto.pagado_anio_millones),
    saldoPorPagarTexto: fmtMinutaMillions(proyecto.saldo_por_pagar_millones),
    resumen:
      proyecto.frase_radial ||
      `Obra a cargo de ${proyecto.institucion}${proyecto.administracion_origen ? ` (contratada en la gestión ${proyecto.administracion_origen})` : ''}: pagó ${fmtMinutaMillions(proyecto.pagado_anio_millones)} en ${anio}.`,
    fuente,
  }
}

export function cifrasFromEconomiaView(
  eco: AysenEconomiaResponse,
  view: 'crecimiento' | 'participacion' | 'actividades',
  anioSeleccionado: number,
): MinutaCifra {
  const anioEfectivo = eco.anio_datos ?? anioSeleccionado
  const fuente = normalizeFuenteRef(eco.fuentes[0], {
    organismo: 'Banco Central de Chile',
    documento: 'Cuentas Nacionales Regionales · PIB de Aysén (BDE)',
    fechaCorte: eco.actualizado_en || String(anioEfectivo),
    url: 'https://si3.bcentral.cl/Siete/ES/Siete/Cuadro/CAP_CCNN/MN_CCNN76/CCNN2018_PIB_REGIONAL',
  })

  if (view === 'participacion') {
    const pt = eco.serie_participacion.find(p => p.anio === anioSeleccionado) ?? eco.serie_participacion.at(-1)
    const pct = pt?.participacion_pct ?? eco.participacion_nacional_pct
    const disponible = pct !== null
    return {
      id: `eco-participacion-${pt?.anio ?? anioEfectivo}`,
      etiqueta: `Participación de Aysén en el PIB nacional (${pt?.anio ?? anioEfectivo})`,
      valorTexto: disponible ? fmtMinutaPct(pct, false, 2) : 'Sin dato disponible',
      subvalor: eco.pib_nominal_millones !== null ? `PIB nominal Aysén: ${fmtMinutaMillions(eco.pib_nominal_millones)}` : null,
      unidad: '% del PIB nominal de Chile',
      periodo: String(pt?.anio ?? anioEfectivo),
      territorio: 'Región de Aysén',
      institucion: 'Banco Central de Chile',
      explicacion: 'Muestra qué fracción de la economía total de Chile produce la Región de Aysén en precios corrientes.',
      baseCalculo:
        pt?.pib_aysen_millones && pt?.pib_chile_millones
          ? `PIB nominal Aysén (${fmtMinutaMillions(pt.pib_aysen_millones)}) ÷ PIB nominal Chile (${fmtMinutaMillions(pt.pib_chile_millones)}) × 100`
          : 'PIB nominal regional sobre PIB nominal nacional (precios corrientes).',
      disponible,
      antecedenteFaltante: disponible ? null : `Falta la serie nominal anual ${anioSeleccionado} del PIB regional en BCCh.`,
      coberturaParcial: Boolean(eco.en_curso && eco.anio_datos !== anioSeleccionado),
      notaCobertura: eco.aviso_periodo || null,
      origenSeccion: 'Economía',
      fuente,
      agregadoEn: new Date().toISOString(),
    }
  }

  if (view === 'actividades') {
    const top = [...eco.actividades]
      .filter(a => a.participacion_pct !== null)
      .sort((a, b) => (b.participacion_pct ?? 0) - (a.participacion_pct ?? 0))[0]
    const disponible = Boolean(top && top.participacion_pct !== null)
    return {
      id: `eco-top-actividad-${anioEfectivo}-${top?.codigo || 'none'}`,
      etiqueta: top ? `Principal actividad económica: ${top.nombre}` : `Peso por actividad económica (${anioEfectivo})`,
      valorTexto: disponible ? fmtMinutaPct(top!.participacion_pct, false, 1) : 'Sin dato disponible',
      subvalor: top?.valor_millones ? `${fmtMinutaMillions(top.valor_millones)} nominales` : null,
      unidad: '% del PIB nominal regional',
      periodo: String(anioEfectivo),
      territorio: 'Región de Aysén',
      institucion: 'Banco Central de Chile',
      explicacion: 'Identifica la actividad con mayor peso en el valor agregado nominal de la economía de Aysén.',
      baseCalculo: 'Valor agregado nominal de la actividad sobre la suma nominal regional (precios corrientes).',
      disponible,
      antecedenteFaltante: disponible ? null : `Falta desglose nominal por actividad para ${anioSeleccionado} en BCCh.`,
      coberturaParcial: Boolean(eco.en_curso && eco.anio_datos !== anioSeleccionado),
      notaCobertura: eco.aviso_periodo || null,
      origenSeccion: 'Economía',
      fuente,
      agregadoEn: new Date().toISOString(),
    }
  }

  // Crecimiento real del PIB
  const pt = eco.serie_crecimiento.find(p => p.anio === anioSeleccionado)
  const aysenPct = pt?.aysen_pct ?? (anioSeleccionado === eco.anio_datos ? eco.crecimiento_real_aysen_pct : null)
  const chilePct = pt?.chile_pct ?? (anioSeleccionado === eco.anio_datos ? eco.crecimiento_real_chile_pct : null)
  const disponible = aysenPct !== null

  return {
    id: `eco-crecimiento-${anioSeleccionado}`,
    etiqueta: `Crecimiento real del PIB de Aysén (${anioSeleccionado})`,
    valorTexto: disponible ? fmtMinutaPct(aysenPct, true, 1) : 'Sin dato disponible',
    subvalor: chilePct !== null ? `Chile: ${fmtMinutaPct(chilePct, true, 1)}` : null,
    unidad: 'Variación real anual (%)',
    periodo: String(anioSeleccionado),
    territorio: 'Región de Aysén',
    institucion: 'Banco Central de Chile',
    explicacion: 'Compara el ritmo real de crecimiento o contracción de Aysén frente al promedio nacional.',
    baseCalculo: 'Variación porcentual anual del PIB a precios del año anterior encadenado (referencia 2018).',
    disponible,
    antecedenteFaltante: disponible
      ? null
      : eco.aviso_periodo || `El PIB regional anual ${anioSeleccionado} aún no ha sido publicado por el Banco Central de Chile.`,
    coberturaParcial: Boolean(eco.en_curso && !disponible),
    notaCobertura: eco.aviso_periodo || null,
    origenSeccion: 'Economía',
    fuente,
    agregadoEn: new Date().toISOString(),
  }
}

/* ============================================================
   GENERADORES DE SUGERENCIAS DEL ASISTENTE (HASTA 3 CIFRAS)
============================================================ */

export interface SugerenciaWizardResult {
  tituloSugerido: string
  cifras: MinutaCifra[]
  obraSugerida: MinutaObraEjemplo | null
  detalleCalculo?: {
    etiqueta: string
    valor: string
  }[]
  antecedenteFaltanteGlobal?: string | null
  notaCobertura?: string | null
}

export function buildSugerenciasEconomia(
  eco: AysenEconomiaResponse,
  anio: number,
): SugerenciaWizardResult {
  const anioEfectivo = eco.anio_datos ?? anio
  const fuente = normalizeFuenteRef(eco.fuentes[0], {
    organismo: 'Banco Central de Chile',
    documento: 'Cuentas Nacionales Regionales · PIB por actividad (BDE)',
    fechaCorte: eco.actualizado_en || String(anioEfectivo),
    url: 'https://si3.bcentral.cl/Siete/ES/Siete/Cuadro/CAP_CCNN/MN_CCNN76/CCNN2018_PIB_REGIONAL',
  })

  const cifras: MinutaCifra[] = []
  const c1 = cifrasFromEconomiaView(eco, 'crecimiento', anio)
  cifras.push(c1)

  const topUp = eco.sectores_crecieron[0]
  if (topUp) {
    cifras.push({
      id: `wiz-eco-up-${anioEfectivo}-${topUp.nombre.toLowerCase().slice(0, 12)}`,
      etiqueta: `Mayor impulso: ${topUp.nombre}`,
      valorTexto: fmtMinutaPct(topUp.variacion_pct, true, 1),
      subvalor: topUp.participacion_pct !== null ? `Peso en PIB: ${fmtMinutaPct(topUp.participacion_pct, false, 1)}` : null,
      unidad: 'Variación real anual (%)',
      periodo: String(anioEfectivo),
      territorio: 'Región de Aysén',
      institucion: 'Banco Central de Chile',
      explicacion: 'Señala la actividad productiva que más empujó al alza la economía regional durante el año.',
      baseCalculo: 'Variación real anual por rama de actividad (volúmenes encadenados 2018); peso sobre PIB nominal.',
      disponible: topUp.variacion_pct !== null,
      antecedenteFaltante: topUp.variacion_pct === null ? 'Sin variación real anual informada para este rubro.' : null,
      coberturaParcial: anioEfectivo !== anio,
      notaCobertura: anioEfectivo !== anio ? `Último cierre sectorial oficial disponible: ${anioEfectivo}.` : null,
      origenSeccion: 'Economía',
      fuente,
      agregadoEn: new Date().toISOString(),
    })
  }

  const topDown = eco.sectores_cayeron[0]
  if (topDown) {
    cifras.push({
      id: `wiz-eco-down-${anioEfectivo}-${topDown.nombre.toLowerCase().slice(0, 12)}`,
      etiqueta: `Mayor caída: ${topDown.nombre}`,
      valorTexto: fmtMinutaPct(topDown.variacion_pct, true, 1),
      subvalor: topDown.participacion_pct !== null ? `Peso en PIB: ${fmtMinutaPct(topDown.participacion_pct, false, 1)}` : null,
      unidad: 'Variación real anual (%)',
      periodo: String(anioEfectivo),
      territorio: 'Región de Aysén',
      institucion: 'Banco Central de Chile',
      explicacion: 'Muestra la principal actividad en contracción que restó dinamismo a la región.',
      baseCalculo: 'Variación real anual por rama de actividad (volúmenes encadenados 2018); peso sobre PIB nominal.',
      disponible: topDown.variacion_pct !== null,
      antecedenteFaltante: null,
      coberturaParcial: anioEfectivo !== anio,
      notaCobertura: anioEfectivo !== anio ? `Último cierre sectorial oficial disponible: ${anioEfectivo}.` : null,
      origenSeccion: 'Economía',
      fuente,
      agregadoEn: new Date().toISOString(),
    })
  } else if (eco.admin_publica_pct !== null) {
    cifras.push({
      id: `wiz-eco-admin-${anioEfectivo}`,
      etiqueta: 'Peso de Administración Pública en el PIB',
      valorTexto: fmtMinutaPct(eco.admin_publica_pct, false, 1),
      subvalor: eco.admin_publica_millones !== null ? fmtMinutaMillions(eco.admin_publica_millones) : null,
      unidad: '% del PIB nominal regional',
      periodo: String(anioEfectivo),
      territorio: 'Región de Aysén',
      institucion: 'Banco Central de Chile',
      explicacion: 'Contextualiza cuánto representa el aparato público dentro del valor agregado regional.',
      baseCalculo: 'Valor agregado nominal de Administración Pública sobre el PIB nominal de Aysén.',
      disponible: true,
      coberturaParcial: anioEfectivo !== anio,
      notaCobertura: anioEfectivo !== anio ? `Cifra correspondiente al último cierre publicado (${anioEfectivo}).` : null,
      origenSeccion: 'Economía',
      fuente,
      agregadoEn: new Date().toISOString(),
    })
  }

  return {
    tituloSugerido: `¿Qué actividades explican el crecimiento o la caída de la economía de Aysén en ${anio}?`,
    cifras: cifras.slice(0, 3),
    obraSugerida: null,
    antecedenteFaltanteGlobal: !c1.disponible ? c1.antecedenteFaltante : null,
    notaCobertura: eco.aviso_periodo || null,
  }
}

export function buildSugerenciasGastoCorriente(
  presup: AysenPresupuestosResponse,
  institucionIdOrRol: string,
  anio: number,
): SugerenciaWizardResult {
  const inst =
    presup.instituciones.find(i => i.id === institucionIdOrRol) ??
    presup.instituciones.find(i => i.rol_billetera === institucionIdOrRol) ??
    presup.instituciones[0]

  const periodoLabel = presup.en_curso && presup.mes_corte_nombre
    ? `${presup.mes_corte_nombre} de ${anio}`
    : String(anio)

  if (!inst) {
    const missing = `No se encontró registro oficial publicado para la institución seleccionada en ${anio}.`
    return {
      tituloSugerido: `De cada $100 ejecutados en ${anio}, ¿cuántos correspondieron a gasto corriente?`,
      cifras: [
        {
          id: `wiz-gc-missing-${institucionIdOrRol}-${anio}`,
          etiqueta: `Gasto corriente sobre ejecutado (${anio})`,
          valorTexto: 'Sin dato disponible',
          unidad: '% sobre gasto ejecutado',
          periodo: String(anio),
          territorio: presup.comuna_nombre ? `Comuna de ${presup.comuna_nombre}` : 'Región de Aysén',
          institucion: institucionIdOrRol,
          explicacion: 'Indica cuántos pesos de cada $100 ejecutados correspondieron a funcionamiento corriente.',
          baseCalculo: 'Gasto corriente ÷ Gasto ejecutado total × 100.',
          disponible: false,
          antecedenteFaltante: missing,
          origenSeccion: 'Presupuestos',
          fuente: {
            id: `pendiente|${anio}`,
            organismo: 'SUBDERE SINIM / DIPRES',
            documento: `Balance de Ejecución Presupuestaria ${anio}`,
            fechaCorte: `Pendiente de publicación (${anio})`,
            url: 'https://datos.sinim.gov.cl',
          },
          agregadoEn: new Date().toISOString(),
        },
      ],
      obraSugerida: null,
      antecedenteFaltanteGlobal: missing,
    }
  }

  const cPct = cifraFromInstitucionPresupuesto(inst, anio, {
    mesCorteNombre: presup.mes_corte_nombre,
    enCurso: presup.en_curso,
    modo: 'gasto_corriente_pct',
  })
  const cEjec = cifraFromInstitucionPresupuesto(inst, anio, {
    mesCorteNombre: presup.mes_corte_nombre,
    enCurso: presup.en_curso,
    modo: 'gasto_ejecutado',
  })
  const cCorr = cifraFromInstitucionPresupuesto(inst, anio, {
    mesCorteNombre: presup.mes_corte_nombre,
    enCurso: presup.en_curso,
    modo: 'gasto_corriente_monto',
  })

  const detalleCalculo: { etiqueta: string; valor: string }[] = [
    { etiqueta: 'Presupuesto inicial', valor: fmtMinutaMillionsExact1(inst.presupuesto_inicial_millones) },
    { etiqueta: 'Presupuesto vigente', valor: fmtMinutaMillionsExact1(inst.presupuesto_vigente_millones) },
    { etiqueta: 'Gasto ejecutado (denominador)', valor: fmtMinutaMillionsExact1(inst.gasto_ejecutado_millones) },
    { etiqueta: 'Gasto corriente (numerador)', valor: fmtMinutaMillionsExact1(inst.gasto_corriente_millones) },
    {
      etiqueta: 'Inversión / capital',
      valor:
        inst.inversion_millones !== null
          ? `${fmtMinutaMillionsExact1(inst.inversion_millones)} (${fmtMinutaPct(inst.inversion_pct, false, 2)})`
          : 'Sin dato disponible',
    },
    {
      etiqueta: 'Resultado (de cada $100 ejecutados)',
      valor:
        inst.gasto_corriente_pct !== null
          ? `${fmtMinutaPct(inst.gasto_corriente_pct, false, 2)} (${fmtPesosDeCada100(inst.gasto_corriente_pct)})`
          : 'Sin dato disponible',
    },
  ]

  const nombreConArticulo = inst.nombre.startsWith('Municipalidad')
    ? `la ${inst.nombre}`
    : inst.nombre.startsWith('Dirección')
      ? `la ${inst.nombre}`
      : `el ${inst.nombre}`

  return {
    tituloSugerido: `De cada $100 ejecutados por ${nombreConArticulo} en ${periodoLabel}, ¿cuántos correspondieron a gasto corriente?`,
    cifras: [cPct, cCorr, cEjec],
    obraSugerida: null,
    detalleCalculo,
    antecedenteFaltanteGlobal: !cPct.disponible ? cPct.antecedenteFaltante : null,
    notaCobertura: presup.en_curso ? presup.aviso_anio_en_curso : null,
  }
}

export function buildSugerenciasArrastre(
  proyectos: AysenProyectosResponse,
  anio: number,
  territorioLabel = 'Región de Aysén',
): SugerenciaWizardResult {
  const p2 = proyectos.pregunta_presupuesto_comprometido
  const p1 = proyectos.pregunta_pagado_arrastre
  const basePregunta = p2.disponible || p2.numerador_millones !== null || p2.denominador_millones !== null ? p2 : p1
  const fuente = normalizeFuenteRef(basePregunta.fuente ?? proyectos.fuentes[0], {
    organismo: 'MOP Vialidad / DIPRES BIP',
    documento: `Registro de contratos y proyectos de inversión ${anio}`,
    fechaCorte: proyectos.actualizado_en || String(anio),
    url: 'https://www.mop.gob.cl',
  })

  const faltantePct =
    basePregunta.porcentaje_pct === null
      ? basePregunta.sin_dato_motivo ||
        'Falta presupuesto vigente de inversión comparable o respaldo de fechas de contratación en todas las obras para calcular el porcentaje.'
      : null

  const cPresup: MinutaCifra = {
    id: `wiz-arr-vigente-${anio}-${territorioLabel}`,
    etiqueta: `Inversión vigente / cartera evaluada (${anio})`,
    valorTexto: fmtMinutaMillions(basePregunta.denominador_millones),
    unidad: 'Millones de pesos ($ MM)',
    periodo: String(anio),
    territorio: territorioLabel,
    institucion: proyectos.institucion || 'Instituciones con obras en Aysén',
    explicacion: 'Establece el presupuesto de inversión o total evaluado contra el cual se mide el arrastre.',
    baseCalculo: null,
    disponible: basePregunta.denominador_millones !== null,
    antecedenteFaltante:
      basePregunta.denominador_millones === null
        ? basePregunta.sin_dato_motivo || `Falta monto total vigente o pagado evaluable en ${anio}.`
        : null,
    coberturaParcial: Boolean(basePregunta.proyectos_excluidos && basePregunta.proyectos_excluidos > 0),
    notaCobertura:
      basePregunta.proyectos_incluidos !== null
        ? `Cubre ${basePregunta.proyectos_incluidos} obras con respaldo verificado.`
        : null,
    origenSeccion: 'Proyectos',
    fuente,
    agregadoEn: new Date().toISOString(),
  }

  const cCompromisos: MinutaCifra = {
    id: `wiz-arr-monto-${anio}-${territorioLabel}`,
    etiqueta: `Compromisos de proyectos anteriores imputables a ${anio}`,
    valorTexto: fmtMinutaMillions(basePregunta.numerador_millones),
    unidad: 'Millones de pesos ($ MM)',
    periodo: String(anio),
    territorio: territorioLabel,
    institucion: proyectos.institucion || 'Contratos anteriores vigentes en Aysén',
    explicacion: 'Muestra el monto documentado que corresponde a obras contratadas antes del año seleccionado.',
    baseCalculo: null,
    disponible: basePregunta.numerador_millones !== null,
    antecedenteFaltante:
      basePregunta.numerador_millones === null
        ? basePregunta.sin_dato_motivo || `Falta desglose de compromisos anteriores imputables a ${anio}.`
        : null,
    coberturaParcial: Boolean(basePregunta.proyectos_excluidos && basePregunta.proyectos_excluidos > 0),
    notaCobertura:
      basePregunta.proyectos_excluidos
        ? `Excluye ${basePregunta.proyectos_excluidos} obras sin fecha oficial de contratación.`
        : null,
    origenSeccion: 'Proyectos',
    fuente,
    agregadoEn: new Date().toISOString(),
  }

  const cPct = cifraFromPreguntaArrastre(
    basePregunta,
    anio,
    basePregunta === p2 ? 'comprometido' : 'pagado',
    territorioLabel,
    proyectos.en_curso,
  )

  return {
    tituloSugerido: `¿Qué parte de la inversión de ${anio} en ${territorioLabel} ya estaba comprometida por proyectos anteriores?`,
    cifras: [cPresup, cCompromisos, cPct],
    obraSugerida: proyectos.proyectos.find(p => p.clasificacion_arrastre === 'arrastre')
      ? obraFromProyecto(proyectos.proyectos.find(p => p.clasificacion_arrastre === 'arrastre')!, anio)
      : null,
    antecedenteFaltanteGlobal: faltantePct,
    notaCobertura:
      basePregunta.proyectos_excluidos && basePregunta.proyectos_excluidos > 0
        ? `Cobertura parcial: se incluyeron ${basePregunta.proyectos_incluidos ?? 0} obras verificadas y se excluyeron ${basePregunta.proyectos_excluidos} sin fecha de contratación.`
        : null,
  }
}

export function buildSugerenciasGestionObra(
  proyecto: ProyectoObra,
  anio: number,
): SugerenciaWizardResult {
  const obra = obraFromProyecto(proyecto, anio)
  const fuente = obra.fuente
  const territorio = proyecto.comuna ? `Comuna de ${proyecto.comuna}` : 'Región de Aysén'

  const cOrigen: MinutaCifra = {
    id: `wiz-obra-costo-${proyecto.id}-${anio}`,
    etiqueta: 'Costo total y gestión de contratación',
    valorTexto: fmtMinutaMillions(proyecto.costo_total_millones),
    subvalor: proyecto.administracion_origen
      ? `Gestión ${proyecto.administracion_origen}`
      : 'Gestión de origen: Sin dato disponible',
    unidad: 'Millones de pesos ($ MM)',
    periodo: String(anio),
    territorio,
    institucion: proyecto.institucion,
    explicacion: 'Permite precisar bajo qué administración se contrató la obra y cuál es su valor total.',
    baseCalculo: null,
    disponible: proyecto.costo_total_millones !== null,
    antecedenteFaltante:
      proyecto.costo_total_millones === null
        ? 'Falta el monto total contratado en la ficha oficial de la obra.'
        : null,
    origenSeccion: 'Proyectos',
    fuente,
    agregadoEn: new Date().toISOString(),
  }

  const cPagado: MinutaCifra = {
    id: `wiz-obra-pagado-${proyecto.id}-${anio}`,
    etiqueta: `Pagado durante ${anio}`,
    valorTexto: fmtMinutaMillions(proyecto.pagado_anio_millones),
    subvalor: proyecto.compromiso_anio_millones !== null
      ? `Compromiso ${anio}: ${fmtMinutaMillions(proyecto.compromiso_anio_millones)}`
      : null,
    unidad: 'Millones de pesos ($ MM)',
    periodo: String(anio),
    territorio,
    institucion: proyecto.institucion,
    explicacion: 'Muestra cuánto se pagó efectivamente por esta obra durante el año seleccionado.',
    baseCalculo: null,
    disponible: proyecto.pagado_anio_millones !== null,
    antecedenteFaltante:
      proyecto.pagado_anio_millones === null
        ? `Falta el registro de pagos ejecutados durante ${anio} para esta obra.`
        : null,
    origenSeccion: 'Proyectos',
    fuente,
    agregadoEn: new Date().toISOString(),
  }

  const cSaldo: MinutaCifra = {
    id: `wiz-obra-saldo-${proyecto.id}-${anio}`,
    etiqueta: 'Saldo por pagar / arrastre acumulado',
    valorTexto: fmtMinutaMillions(proyecto.saldo_por_pagar_millones),
    subvalor:
      proyecto.pagado_anios_anteriores_millones !== null
        ? `Pagado años previos: ${fmtMinutaMillions(proyecto.pagado_anios_anteriores_millones)}`
        : null,
    unidad: 'Millones de pesos ($ MM)',
    periodo: String(anio),
    territorio,
    institucion: proyecto.institucion,
    explicacion: 'Contextualiza cuánto falta por pagar del contrato y lo ya desembolsado antes del período.',
    baseCalculo: null,
    disponible: proyecto.saldo_por_pagar_millones !== null,
    antecedenteFaltante:
      proyecto.saldo_por_pagar_millones === null
        ? 'Falta el saldo por pagar oficial en el registro contractual.'
        : null,
    origenSeccion: 'Proyectos',
    fuente,
    agregadoEn: new Date().toISOString(),
  }

  return {
    tituloSugerido: `¿En qué gestión se contrató «${proyecto.nombre}» y cuánto se pagó en ${anio}?`,
    cifras: [cOrigen, cPagado, cSaldo],
    obraSugerida: obra,
    antecedenteFaltanteGlobal:
      !proyecto.administracion_origen
        ? 'Falta la fecha oficial de adjudicación o contratación para identificar con certeza la administración de origen.'
        : null,
  }
}
