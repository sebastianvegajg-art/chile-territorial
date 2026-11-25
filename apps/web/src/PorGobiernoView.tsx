import { useCallback, useEffect, useMemo, useState } from 'react'
import { POR_GOBIERNO_VIVIENDA } from './data/porGobiernoVivienda'
import type {
  AdminId,
  GlosaCategoriaId,
  GlosaFamilia,
  GlosaVersionAnio,
  ViviendaPresupuestoRow,
} from './data/porGobiernoVivienda'
import { MiMinutaPanel, MinutaSheet } from './minuta/MiMinutaPanel'
import type { MinutaModalMode } from './minuta/MiMinutaPanel'
import {
  generarRespuestaCotidiana,
  loadMinutaDraft,
  saveMinutaDraft,
} from './minuta/minutaModel'
import type {
  MinutaCifra,
  MinutaContextoComparacion,
  MinutaDraft,
  MinutaFuenteRef,
  MinutaGlosaRelevante,
} from './minuta/minutaModel'

type SubVista = 'presupuesto' | 'glosas'
type UnidadPresupuesto = 'real_2025' | 'pct_nacional'
type GlosaFiltro = 'todas' | GlosaCategoriaId

const fmtInt = new Intl.NumberFormat('es-CL', { maximumFractionDigits: 0 })
const fmtDec1 = new Intl.NumberFormat('es-CL', { minimumFractionDigits: 1, maximumFractionDigits: 1 })
const fmtDec2 = new Intl.NumberFormat('es-CL', { minimumFractionDigits: 2, maximumFractionDigits: 2 })

function fmtBillonesOMillones(mm: number): string {
  if (!Number.isFinite(mm)) return 'Sin dato disponible'
  if (Math.abs(mm) >= 1_000_000) {
    return `$${fmtDec2.format(mm / 1_000_000)} billones`
  }
  return `$${fmtInt.format(Math.round(mm))} millones`
}

function fmtMMCompacto(mm: number): string {
  if (!Number.isFinite(mm)) return 'Sin dato'
  return `$${fmtInt.format(Math.round(mm))} MM`
}

function fmtSignedPct(val: number, digits: 1 | 2 = 1): string {
  const f = digits === 1 ? fmtDec1 : fmtDec2
  const sign = val > 0 ? '+' : ''
  return `${sign}${f.format(val)}%`
}

function fmtSignedPP(val: number): string {
  const sign = val > 0 ? '+' : ''
  return `${sign}${fmtDec2.format(val)} pp`
}

function avg(values: number[]): number {
  if (values.length === 0) return 0
  return values.reduce((a, b) => a + b, 0) / values.length
}

/* ============================================================
   MOTOR DE DIFF PALABRA A PALABRA (LCS) PARA GLOSAS OFICIALES
============================================================ */

interface DiffSegment {
  type: 'same' | 'del' | 'ins'
  text: string
}

function tokenizeWords(text: string): string[] {
  return text.trim().split(/\s+/).filter(Boolean)
}

function computeWordDiff(textA: string, textB: string): { left: DiffSegment[]; right: DiffSegment[]; changedCount: number } {
  const a = tokenizeWords(textA)
  const b = tokenizeWords(textB)
  const m = a.length
  const n = b.length

  // Para textos extensos (hasta ~400 palabras), LCS por matriz plana Uint16 es instantáneo (<2 ms)
  const dp = new Uint16Array((m + 1) * (n + 1))
  const stride = n + 1
  for (let i = m - 1; i >= 0; i--) {
    const ai = a[i].toLowerCase()
    for (let j = n - 1; j >= 0; j--) {
      if (ai === b[j].toLowerCase()) {
        dp[i * stride + j] = dp[(i + 1) * stride + (j + 1)] + 1
      } else {
        const down = dp[(i + 1) * stride + j]
        const right = dp[i * stride + (j + 1)]
        dp[i * stride + j] = down >= right ? down : right
      }
    }
  }

  const left: DiffSegment[] = []
  const right: DiffSegment[] = []
  let i = 0
  let j = 0
  let changedCount = 0

  const pushSeg = (arr: DiffSegment[], type: DiffSegment['type'], word: string) => {
    const last = arr[arr.length - 1]
    if (last && last.type === type) {
      last.text += ` ${word}`
    } else {
      arr.push({ type, text: word })
    }
  }

  while (i < m && j < n) {
    if (a[i].toLowerCase() === b[j].toLowerCase()) {
      pushSeg(left, 'same', a[i])
      pushSeg(right, 'same', b[j])
      i++
      j++
    } else if (dp[(i + 1) * stride + j] >= dp[i * stride + (j + 1)]) {
      pushSeg(left, 'del', a[i])
      changedCount++
      i++
    } else {
      pushSeg(right, 'ins', b[j])
      changedCount++
      j++
    }
  }
  while (i < m) {
    pushSeg(left, 'del', a[i++])
    changedCount++
  }
  while (j < n) {
    pushSeg(right, 'ins', b[j++])
    changedCount++
  }

  return { left, right, changedCount }
}

function summarizePassage(text: string, maxChars = 240): string {
  const clean = text.trim()
  if (clean.length <= maxChars) return clean
  const cut = clean.slice(0, maxChars).lastIndexOf(' ')
  return `${clean.slice(0, cut > 120 ? cut : maxChars)}…`
}

const CATEGORIA_LABELS: Record<GlosaCategoriaId, string> = {
  limites_uso: 'Límites de uso',
  requisitos_transferencia: 'Requisitos para transferir',
  obligaciones_informar: 'Obligaciones de informar',
}

/* ============================================================
   COMPONENTE PRINCIPAL · POR GOBIERNO
============================================================ */

export function PorGobiernoView() {
  const data = POR_GOBIERNO_VIVIENDA

  // Selección compartida entre Presupuesto y Glosas
  const [adminA, setAdminA] = useState<AdminId>('pinera_2')
  const [adminB, setAdminB] = useState<AdminId>('boric')
  const [tema] = useState<'vivienda'>('vivienda')
  const [subVista, setSubVista] = useState<SubVista>('presupuesto')

  // Controles de Vista Presupuesto
  const [unidad, setUnidad] = useState<UnidadPresupuesto>('real_2025')
  const [anioSeleccionado, setAnioSeleccionado] = useState<number>(2025)

  // Controles de Vista Glosas
  const [glosaAnioA, setGlosaAnioA] = useState<number>(2021)
  const [glosaAnioB, setGlosaAnioB] = useState<number>(2025)
  const [glosaFiltro, setGlosaFiltro] = useState<GlosaFiltro>('todas')
  const [soloCambiosResaltados, setSoloCambiosResaltados] = useState<boolean>(true)
  const [glosaAbiertaId, setGlosaAbiertaId] = useState<string>(data.glosas_familias[0].id)
  const [mostrarRestricciones, setMostrarRestricciones] = useState<boolean>(false)

  // Estado compartido de Mi minuta (mismo localStorage que Vista Política Aysén)
  const [minutaDraft, setMinutaDraft] = useState<MinutaDraft>(() => loadMinutaDraft())
  const [minutaOpen, setMinutaOpen] = useState<boolean>(false)
  const [minutaMode, setMinutaMode] = useState<MinutaModalMode>('vista_previa')
  const [minutaToast, setMinutaToast] = useState<string>('')

  const updateMinutaDraft = useCallback((next: MinutaDraft) => {
    setMinutaDraft(next)
    saveMinutaDraft(next)
  }, [])

  // Sincronizar cambios si se editó en otra pestaña
  useEffect(() => {
    const onStorage = () => setMinutaDraft(loadMinutaDraft())
    window.addEventListener('storage', onStorage)
    return () => window.removeEventListener('storage', onStorage)
  }, [])

  // Evitar comparar la misma administración contra sí misma al cambiar selectores
  const handleChangeAdminA = (next: AdminId) => {
    setAdminA(next)
    if (next === adminB) {
      const other = data.administraciones.find(a => a.id !== next)!.id
      setAdminB(other)
    }
  }
  const handleChangeAdminB = (next: AdminId) => {
    setAdminB(next)
    if (next === adminA) {
      const other = data.administraciones.find(a => a.id !== next)!.id
      setAdminA(other)
    }
  }

  const metaA = useMemo(() => data.administraciones.find(a => a.id === adminA)!, [data.administraciones, adminA])
  const metaB = useMemo(() => data.administraciones.find(a => a.id === adminB)!, [data.administraciones, adminB])

  // Sincronizar años por defecto de glosas cuando cambian las administraciones seleccionadas
  useEffect(() => {
    const yA = metaA.anio_glosa_defecto
    const yB = metaB.anio_glosa_defecto
    if (yA <= yB) {
      setGlosaAnioA(yA)
      setGlosaAnioB(yB)
    } else {
      setGlosaAnioA(yB)
      setGlosaAnioB(yA)
    }
  }, [metaA.anio_glosa_defecto, metaB.anio_glosa_defecto])

  // Determinar si corresponde modo equivalente enero–agosto (cuando una administración está en curso)
  const esModoEquivalenteEneAgo = metaA.en_curso || metaB.en_curso

  const serieActiva: ViviendaPresupuestoRow[] = useMemo(
    () => (esModoEquivalenteEneAgo ? data.serie_equivalente_ene_ago : data.serie_anual_dic),
    [esModoEquivalenteEneAgo, data.serie_equivalente_ene_ago, data.serie_anual_dic],
  )

  useEffect(() => {
    if (!serieActiva.some(r => r.anio === anioSeleccionado)) {
      setAnioSeleccionado(serieActiva[serieActiva.length - 1].anio)
    }
  }, [serieActiva, anioSeleccionado])

  // Calcular resumen comparable de Administración A vs Administración B
  const resumenComparacion = useMemo(() => {
    const getSummary = (adm: typeof metaA) => {
      if (esModoEquivalenteEneAgo) {
        const row = data.serie_equivalente_ene_ago.find(r => r.anio === adm.anio_referencia_ene_ago)!
        return {
          admin: adm,
          etiquetaPeriodo: row.es_cambio_mando
            ? `Ene–ago ${row.anio} (año compartido · en curso)`
            : `Ene–ago ${row.anio} (mismo tramo 8 meses)`,
          aniosUsados: [row.anio],
          incluyeCompartido: row.es_cambio_mando,
          inicialReal: row.real_2025_mm.inicial,
          vigenteReal: row.real_2025_mm.vigente,
          ejecutadoReal: row.real_2025_mm.ejecutado,
          inicialPct: row.participacion_nacional_pct.inicial,
          vigentePct: row.participacion_nacional_pct.vigente,
          ejecutadoPct: row.participacion_nacional_pct.ejecutado,
          avancePct: row.avance_sobre_vigente_pct,
          modificacionPct: row.modificacion_vigente_vs_inicial_pct,
          rowRef: row,
        }
      }
      const rows = data.serie_anual_dic.filter(r => adm.anios_completos.includes(r.anio))
      const lastRow = rows[rows.length - 1] ?? data.serie_anual_dic[data.serie_anual_dic.length - 1]
      return {
        admin: adm,
        etiquetaPeriodo: `Promedio años completos ${adm.anios_completos[0]}–${adm.anios_completos[adm.anios_completos.length - 1]} (${rows.length} cierres anuales)`,
        aniosUsados: adm.anios_completos,
        incluyeCompartido: false,
        inicialReal: avg(rows.map(r => r.real_2025_mm.inicial)),
        vigenteReal: avg(rows.map(r => r.real_2025_mm.vigente)),
        ejecutadoReal: avg(rows.map(r => r.real_2025_mm.ejecutado)),
        inicialPct: avg(rows.map(r => r.participacion_nacional_pct.inicial)),
        vigentePct: avg(rows.map(r => r.participacion_nacional_pct.vigente)),
        ejecutadoPct: avg(rows.map(r => r.participacion_nacional_pct.ejecutado)),
        avancePct: avg(rows.map(r => r.avance_sobre_vigente_pct)),
        modificacionPct: avg(rows.map(r => r.modificacion_vigente_vs_inicial_pct)),
        rowRef: lastRow,
      }
    }

    const a = getSummary(metaA)
    const b = getSummary(metaB)

    const deltaEjecRealPct = ((b.ejecutadoReal - a.ejecutadoReal) / a.ejecutadoReal) * 100
    const deltaIniRealPct = ((b.inicialReal - a.inicialReal) / a.inicialReal) * 100
    const deltaVigRealPct = ((b.vigenteReal - a.vigenteReal) / a.vigenteReal) * 100

    const deltaEjecPP = b.ejecutadoPct - a.ejecutadoPct
    const deltaIniPP = b.inicialPct - a.inicialPct
    const deltaVigPP = b.vigentePct - a.vigentePct

    const conclusion = esModoEquivalenteEneAgo
      ? `Al comparar el mismo tramo enero–agosto en pesos de 2025, el gasto ejecutado (devengado) en Vivienda (Partida 18 MINVU) pasó de ${fmtBillonesOMillones(a.ejecutadoReal)} (${a.rowRef.anio}) a ${fmtBillonesOMillones(b.ejecutadoReal)} (${b.rowRef.anio}), una variación real de ${fmtSignedPct(deltaEjecRealPct, 1)}. Su participación en el gasto nacional directo varió ${fmtSignedPP(deltaEjecPP)} (de ${fmtDec2.format(a.ejecutadoPct)}% a ${fmtDec2.format(b.ejecutadoPct)}%). Como 2026 es un año de cambio de mando en curso, el monto acumulado se informa íntegro sin prorratear entre administraciones.`
      : `Entre los años completos exclusivos de ${metaA.nombre} (${a.aniosUsados.join('–')}) y ${metaB.nombre} (${b.aniosUsados.join('–')}), el gasto ejecutado anual promedio en Vivienda (Partida 18 MINVU) pasó de ${fmtBillonesOMillones(a.ejecutadoReal)} a ${fmtBillonesOMillones(b.ejecutadoReal)} en pesos de 2025 (${fmtSignedPct(deltaEjecRealPct, 1)} real). En participación sobre el gasto nacional directo, pasó de ${fmtDec2.format(a.ejecutadoPct)}% a ${fmtDec2.format(b.ejecutadoPct)}% (${fmtSignedPP(deltaEjecPP)}). Los años de cambio de mando (2018 y 2022) se reportan aparte como años compartidos sin repartir.`

    return {
      a,
      b,
      deltaEjecRealPct,
      deltaIniRealPct,
      deltaVigRealPct,
      deltaEjecPP,
      deltaIniPP,
      deltaVigPP,
      conclusion,
    }
  }, [metaA, metaB, esModoEquivalenteEneAgo, data.serie_anual_dic, data.serie_equivalente_ene_ago])

  const filaDestacada = useMemo(
    () => serieActiva.find(r => r.anio === anioSeleccionado) ?? serieActiva[serieActiva.length - 1],
    [serieActiva, anioSeleccionado],
  )

  const aniosCompartidosRelevantes = useMemo(() => {
    const pool = esModoEquivalenteEneAgo
      ? data.serie_equivalente_ene_ago.filter(r => r.es_cambio_mando)
      : data.serie_anual_dic.filter(r => r.es_cambio_mando)
    return pool
  }, [esModoEquivalenteEneAgo, data.serie_anual_dic, data.serie_equivalente_ene_ago])

  // Filtrado de glosas
  const glosasFiltradas = useMemo(() => {
    if (glosaFiltro === 'todas') return data.glosas_familias
    return data.glosas_familias.filter(g => g.categorias.includes(glosaFiltro))
  }, [data.glosas_familias, glosaFiltro])

  useEffect(() => {
    if (glosasFiltradas.length > 0 && !glosasFiltradas.some(g => g.id === glosaAbiertaId)) {
      setGlosaAbiertaId(glosasFiltradas[0].id)
    }
  }, [glosasFiltradas, glosaAbiertaId])

  const contextoMinutaActual: MinutaContextoComparacion = useMemo(
    () => ({
      tema: 'Vivienda y Urbanismo (Partida 18 MINVU)',
      alcance: 'Presupuesto Nacional de Chile (Gobierno Central · distinto de Aysén)',
      administraciones: `${metaA.nombre} vs ${metaB.nombre}`,
      periodos: esModoEquivalenteEneAgo
        ? `Corte equivalente enero–agosto (${resumenComparacion.a.rowRef.anio} vs ${resumenComparacion.b.rowRef.anio})`
        : `Años completos ${resumenComparacion.a.aniosUsados[0]}–${resumenComparacion.a.aniosUsados[resumenComparacion.a.aniosUsados.length - 1]} vs ${resumenComparacion.b.aniosUsados[0]}–${resumenComparacion.b.aniosUsados[resumenComparacion.b.aniosUsados.length - 1]} (2018 y 2022 compartidos aparte)`,
    }),
    [metaA.nombre, metaB.nombre, esModoEquivalenteEneAgo, resumenComparacion],
  )

  /* ============================================================
     ACCIONES «AGREGAR A MI MINUTA» (PRESUPUESTO Y GLOSAS EN LA MISMA MINUTA)
  ============================================================ */

  const showToast = (msg: string) => {
    setMinutaToast(msg)
    window.setTimeout(() => setMinutaToast(prev => (prev === msg ? '' : prev)), 4500)
  }

  const buildFuentePresupuesto = (row: ViviendaPresupuestoRow): MinutaFuenteRef => ({
    id: `dipres-minvu-${row.tramo}-${row.anio}`,
    organismo: 'DIPRES / INE-BCCh',
    documento: `${row.fuentes.ejecucion_titulo} · Partida 18 MINVU (ajuste IPC serie G073.IPC.IND.2023.M base 2025)`,
    fechaCorte: row.fecha_corte,
    url: row.fuentes.ejecucion_url,
  })

  const agregarCifraPresupuestoAMinuta = (tipo: 'ejecutado' | 'inicial' | 'vigente') => {
    const { a, b } = resumenComparacion
    const esReal = unidad === 'real_2025'
    const fuente = buildFuentePresupuesto(b.rowRef)

    const labelMap = {
      ejecutado: 'Gasto ejecutado (devengado) en Vivienda',
      inicial: 'Presupuesto inicial aprobado (Ley) en Vivienda',
      vigente: 'Presupuesto vigente (con modificaciones) en Vivienda',
    } as const

    const valA = tipo === 'ejecutado' ? (esReal ? a.ejecutadoReal : a.ejecutadoPct) : tipo === 'inicial' ? (esReal ? a.inicialReal : a.inicialPct) : (esReal ? a.vigenteReal : a.vigentePct)
    const valB = tipo === 'ejecutado' ? (esReal ? b.ejecutadoReal : b.ejecutadoPct) : tipo === 'inicial' ? (esReal ? b.inicialReal : b.inicialPct) : (esReal ? b.vigenteReal : b.vigentePct)
    const delta = tipo === 'ejecutado'
      ? (esReal ? resumenComparacion.deltaEjecRealPct : resumenComparacion.deltaEjecPP)
      : tipo === 'inicial'
        ? (esReal ? resumenComparacion.deltaIniRealPct : resumenComparacion.deltaIniPP)
        : (esReal ? resumenComparacion.deltaVigRealPct : resumenComparacion.deltaVigPP)

    const nuevaCifra: MinutaCifra = {
      id: `pg-vivienda-${tipo}-${unidad}-${adminA}-${adminB}-${esModoEquivalenteEneAgo ? 'ago' : 'dic'}`,
      etiqueta: `${labelMap[tipo]} (${metaA.nombre.split(' ')[1] ?? metaA.nombre} vs ${metaB.nombre.split(' ')[1] ?? metaB.nombre})`,
      valorTexto: esReal ? fmtSignedPct(delta, 1) : fmtSignedPP(delta),
      subvalor: esReal
        ? `${fmtBillonesOMillones(valA)} → ${fmtBillonesOMillones(valB)} (pesos 2025)`
        : `${fmtDec2.format(valA)}% → ${fmtDec2.format(valB)}% del gasto nacional`,
      unidad: esReal ? 'Pesos constantes de 2025 (IPC INE/BCCh)' : '% sobre Gobierno Central Total (Subt. 21–26, 29–31 y 33)',
      periodo: contextoMinutaActual.periodos,
      territorio: 'Chile · Presupuesto Nacional (no regional Aysén)',
      institucion: 'Partida 18 · Ministerio de Vivienda y Urbanismo (MINVU)',
      explicacion:
        tipo === 'ejecutado'
          ? 'Mide el cambio efectivo en gasto devengado en Vivienda entre ambas administraciones en períodos comparables.'
          : tipo === 'inicial'
            ? 'Compara el marco aprobado originalmente en la Ley de Presupuestos para Partida 18 MINVU.'
            : 'Refleja el presupuesto vigente tras modificaciones e incorporaciones del año en Partida 18 MINVU.',
      baseCalculo: esReal
        ? `Deflactado a pesos promedio de 2025 con IPC oficial INE/BCCh (G073.IPC.IND.2023.M). ${esModoEquivalenteEneAgo ? 'Corte equivalente enero–agosto.' : 'Promedio anual de años completos exclusivos.'}`
        : `Partida 18 MINVU ÷ Gobierno Central Total (Subt. 21–26, 29–31 y 33) × 100 en el mismo corte.`,
      disponible: true,
      coberturaParcial: esModoEquivalenteEneAgo,
      notaCobertura: esModoEquivalenteEneAgo
        ? '2026 está en curso (corte acumulado enero–agosto) y es año compartido de cambio de mando.'
        : 'Años de cambio de mando (2018 y 2022) se mantienen aparte como compartidos sin repartir.',
      origenSeccion: 'Por gobierno · Presupuesto',
      fuente,
      agregadoEn: new Date().toISOString(),
    }

    const exists = minutaDraft.cifras.some(c => c.id === nuevaCifra.id)
    const nextCifras = exists
      ? minutaDraft.cifras.map(c => (c.id === nuevaCifra.id ? nuevaCifra : c))
      : [...minutaDraft.cifras, nuevaCifra].slice(0, 3)

    const defaultTitle = `¿Cómo cambió el presupuesto y las reglas de Vivienda entre ${metaA.nombre} y ${metaB.nombre}?`
    const nextDraft: MinutaDraft = {
      ...minutaDraft,
      preguntaId: 'por_gobierno_vivienda',
      titulo: minutaDraft.titulo.trim() && minutaDraft.preguntaId === 'por_gobierno_vivienda'
        ? minutaDraft.titulo
        : defaultTitle,
      contextoComparacion: contextoMinutaActual,
      cifras: nextCifras,
      actualizadoEn: new Date().toISOString(),
    }
    if (!nextDraft.respuestaEditadaManualmente) {
      nextDraft.respuesta = generarRespuestaCotidiana(nextDraft)
    }
    updateMinutaDraft(nextDraft)
    showToast(exists ? 'Cifra de Vivienda actualizada en Mi minuta.' : 'Cifra de Vivienda guardada en Mi minuta.')
  }

  const agregarGlosaAMinuta = (familia: GlosaFamilia, verA: GlosaVersionAnio, verB: GlosaVersionAnio) => {
    const fuenteA: MinutaFuenteRef = {
      id: `ley-${verA.anio}-${verA.numero_glosa}`,
      organismo: 'DIPRES / Congreso Nacional',
      documento: `${verA.ley_numero} (${verA.anio}) · ${verA.ubicacion} (${verA.tipo_texto_etiqueta})`,
      fechaCorte: verA.fecha_corte,
      url: verA.url,
    }
    const fuenteB: MinutaFuenteRef = {
      id: `ley-${verB.anio}-${verB.numero_glosa}`,
      organismo: 'DIPRES / Congreso Nacional',
      documento: `${verB.ley_numero} (${verB.anio}) · ${verB.ubicacion} (${verB.tipo_texto_etiqueta})`,
      fechaCorte: verB.fecha_corte,
      url: verB.url,
    }

    const glosaSnap: MinutaGlosaRelevante = {
      id: `${familia.id}-${verA.anio}-${verB.anio}`,
      titulo: familia.titulo,
      materia: familia.materia,
      trazaNumeracion: `${verA.numero_glosa} (${verA.anio}) → ${verB.numero_glosa} (${verB.anio})`,
      anioA: verA.anio,
      anioB: verB.anio,
      ubicacionA: `${verA.ley_numero} · ${verA.numero_glosa}`,
      ubicacionB: `${verB.ley_numero} · ${verB.numero_glosa}`,
      pasajeA: verA.disponible
        ? summarizePassage(verA.texto, 230)
        : `Sin dato disponible: ${verA.sin_dato_motivo || 'Sin equivalente en ese año.'}`,
      pasajeB: verB.disponible
        ? summarizePassage(verB.texto, 230)
        : `Sin dato disponible: ${verB.sin_dato_motivo || 'Sin equivalente en ese año.'}`,
      diferenciaPractica: familia.diferencia_practica,
      notaEvidenciaGasto: familia.nota_evidencia_gasto,
      fuenteA,
      fuenteB,
    }

    const defaultTitle = `¿Cómo cambió el presupuesto y las reglas de Vivienda entre ${metaA.nombre} y ${metaB.nombre}?`
    const nextDraft: MinutaDraft = {
      ...minutaDraft,
      preguntaId: 'por_gobierno_vivienda',
      titulo: minutaDraft.titulo.trim() && minutaDraft.preguntaId === 'por_gobierno_vivienda'
        ? minutaDraft.titulo
        : defaultTitle,
      contextoComparacion: contextoMinutaActual,
      glosaRelevante: glosaSnap,
      actualizadoEn: new Date().toISOString(),
    }
    if (!nextDraft.respuestaEditadaManualmente) {
      nextDraft.respuesta = generarRespuestaCotidiana(nextDraft)
    }
    updateMinutaDraft(nextDraft)
    showToast(`Glosa «${familia.titulo.slice(0, 42)}…» incorporada a la misma minuta.`)
  }

  const isCifraSaved = (tipo: 'ejecutado' | 'inicial' | 'vigente') => {
    const id = `pg-vivienda-${tipo}-${unidad}-${adminA}-${adminB}-${esModoEquivalenteEneAgo ? 'ago' : 'dic'}`
    return minutaDraft.cifras.some(c => c.id === id)
  }

  /* ============================================================
     GRÁFICO SVG DE EVOLUCIÓN ANUAL / EQUIVALENTE (CLARO Y RESPONSIVO)
  ============================================================ */

  const chartMetrics = useMemo(() => {
    const vals = serieActiva.flatMap(r =>
      unidad === 'real_2025'
        ? [r.real_2025_mm.inicial, r.real_2025_mm.vigente, r.real_2025_mm.ejecutado]
        : [r.participacion_nacional_pct.inicial, r.participacion_nacional_pct.vigente, r.participacion_nacional_pct.ejecutado],
    )
    const maxVal = Math.max(...vals, 1) * 1.12
    const minVal = 0
    return { maxVal, minVal }
  }, [serieActiva, unidad])

  const totalItemsMinuta = minutaDraft.cifras.length + (minutaDraft.glosaRelevante ? 1 : 0) + (minutaDraft.obraEjemplo ? 1 : 0)

  return (
    <div className="pg-page">
      {/* Cabecera principal */}
      <header className="pg-header panel">
        <div className="pg-header-top">
          <div>
            <p className="eyebrow">Presupuesto Nacional de Chile · Partida 18 MINVU</p>
            <h1 className="pg-title">Por gobierno</h1>
            <p className="pg-lede">
              Compara presupuestos oficiales y cambios en las glosas de la Ley de Presupuestos entre administraciones presidenciales, separando la regla legal de la ejecución observada.
            </p>
          </div>
          <div className="pg-header-actions">
            <button
              type="button"
              className="primary pg-minuta-btn"
              onClick={() => {
                setMinutaMode(totalItemsMinuta > 0 ? 'vista_previa' : 'editar')
                setMinutaOpen(true)
              }}
            >
              Mi minuta {totalItemsMinuta > 0 ? `(${totalItemsMinuta})` : ''}
            </button>
          </div>
        </div>

        {/* Aviso obligatorio de alcance nacional vs regional */}
        <div className="pg-scope-banner" role="note">
          <strong>Alcance nacional:</strong> {data.meta.advertencia_alcance}
        </div>
      </header>

      {/* Toast al guardar en Mi minuta */}
      {minutaToast && (
        <div className="pg-toast" role="status" aria-live="polite">
          <span>{minutaToast}</span>
          <button
            type="button"
            className="text-button"
            onClick={() => {
              setMinutaMode('vista_previa')
              setMinutaOpen(true)
            }}
          >
            Abrir Mi minuta →
          </button>
        </div>
      )}

      {/* Selector compartido entre ambas consultas */}
      <section className="panel pg-controls-card" aria-label="Selección de administraciones y tema">
        <div className="pg-controls-grid">
          <label className="pg-field">
            <span>Primera administración</span>
            <select
              aria-label="Primera administración"
              value={adminA}
              onChange={e => handleChangeAdminA(e.target.value as AdminId)}
            >
              {data.administraciones.map(adm => (
                <option key={adm.id} value={adm.id}>
                  {adm.nombre} ({adm.periodo})
                </option>
              ))}
            </select>
          </label>

          <label className="pg-field">
            <span>Segunda administración</span>
            <select
              aria-label="Segunda administración"
              value={adminB}
              onChange={e => handleChangeAdminB(e.target.value as AdminId)}
            >
              {data.administraciones.map(adm => (
                <option key={adm.id} value={adm.id}>
                  {adm.nombre} ({adm.periodo})
                </option>
              ))}
            </select>
          </label>

          <label className="pg-field">
            <span>Tema de gasto</span>
            <select aria-label="Tema de gasto" value={tema} onChange={() => {}}>
              <option value="vivienda">Vivienda y Urbanismo (Partida 18 MINVU)</option>
              <option value="salud_prox" disabled>Salud (próximamente)</option>
              <option value="seguridad_prox" disabled>Seguridad Pública (próximamente)</option>
            </select>
          </label>
        </div>

        {/* Atajos rápidos de comparación */}
        <div className="pg-presets-row" role="group" aria-label="Comparaciones rápidas">
          <button
            type="button"
            className={`pg-preset-btn${adminA === 'pinera_2' && adminB === 'boric' ? ' is-active' : ''}`}
            onClick={() => {
              setAdminA('pinera_2')
              setAdminB('boric')
            }}
          >
            Piñera II vs Boric (cierres anuales)
          </button>
          <button
            type="button"
            className={`pg-preset-btn${(adminA === 'boric' && adminB === 'actual_2026') || (adminA === 'actual_2026' && adminB === 'boric') ? ' is-active' : ''}`}
            onClick={() => {
              setAdminA('boric')
              setAdminB('actual_2026')
            }}
          >
            Boric vs Adm. 2026–2030 (corte ene–ago)
          </button>
        </div>

        {/* Dos consultas que comparten la selección */}
        <div className="pg-query-tabs" role="tablist" aria-label="Consultas sobre Vivienda">
          <button
            type="button"
            role="tab"
            aria-selected={subVista === 'presupuesto'}
            className={`pg-query-tab${subVista === 'presupuesto' ? ' is-active' : ''}`}
            onClick={() => setSubVista('presupuesto')}
          >
            <span className="pg-query-step">Consulta 1 · Presupuesto</span>
            <strong>¿Cómo cambió el presupuesto?</strong>
            <small>Aprobado, vigente y ejecutado (devengado) en pesos constantes o % nacional</small>
          </button>

          <button
            type="button"
            role="tab"
            aria-selected={subVista === 'glosas'}
            className={`pg-query-tab${subVista === 'glosas' ? ' is-active' : ''}`}
            onClick={() => setSubVista('glosas')}
          >
            <span className="pg-query-step">Consulta 2 · Glosas oficiales</span>
            <strong>¿Qué reglas cambiaron para usar esos recursos?</strong>
            <small>Lectura en paralelo con cambios resaltados, filtros y evidencia legal</small>
          </button>
        </div>
      </section>

      {/* ============================================================
          VISTA 1 · PRESUPUESTO
      ============================================================ */}
      {subVista === 'presupuesto' && (
        <div className="pg-section-stack" role="tabpanel" aria-label="Comparación presupuestaria de Vivienda">
          {/* Banner de período equivalente si hay administración en curso */}
          <div className={`pg-method-banner${esModoEquivalenteEneAgo ? ' is-equivalente' : ''}`} role="note">
            {esModoEquivalenteEneAgo ? (
              <>
                <strong>Comparación en período equivalente (enero–agosto · mes 8):</strong>{' '}
                Como {metaA.en_curso ? metaA.nombre : metaB.nombre} está en curso, comparamos exactamente el mismo tramo acumulado de 8 meses ({resumenComparacion.a.rowRef.anio} vs {resumenComparacion.b.rowRef.anio}) y nunca 8 meses contra un año completo. Además, 2026 es un <strong>año compartido de cambio de mando</strong>: su monto se mantiene íntegro sin repartir.
              </>
            ) : (
              <>
                <strong>Comparación de años completos exclusivos ({resumenComparacion.a.aniosUsados.join('–')} vs {resumenComparacion.b.aniosUsados.join('–')}):</strong>{' '}
                Cada administración se compara por su promedio anual de años completos. Los años de cambio de mando (<strong>2018</strong> y <strong>2022</strong>) figuran marcados aparte como <strong>Año compartido</strong> sin repartir montos anuales.
              </>
            )}
          </div>

          {/* Alternador de unidad + Explicación explícita de base, IPC y denominador */}
          <section className="panel pg-unit-panel">
            <div className="pg-unit-top">
              <div>
                <h2 className="pg-card-title">Presupuesto de Vivienda · Partida 18 (MINVU)</h2>
                <p className="subtle">
                  {data.meta.partidas_y_programas}
                </p>
              </div>
              <div className="pg-unit-toggle" role="group" aria-label="Unidad de comparación presupuestaria">
                <button
                  type="button"
                  aria-pressed={unidad === 'real_2025'}
                  className={unidad === 'real_2025' ? 'is-active' : ''}
                  onClick={() => setUnidad('real_2025')}
                >
                  Pesos de 2025 (IPC)
                </button>
                <button
                  type="button"
                  aria-pressed={unidad === 'pct_nacional'}
                  className={unidad === 'pct_nacional' ? 'is-active' : ''}
                  onClick={() => setUnidad('pct_nacional')}
                >
                  % del gasto nacional
                </button>
              </div>
            </div>

            <dl className="pg-method-strip">
              <div>
                <dt>Etapa del gasto publicado</dt>
                <dd>{data.meta.etapa_ejecucion}</dd>
              </div>
              <div>
                <dt>{unidad === 'real_2025' ? 'Año base y ajuste inflacionario' : 'Denominador del porcentaje'}</dt>
                <dd>{unidad === 'real_2025' ? data.meta.fuente_ajuste_ipc : data.meta.denominador_participacion}</dd>
              </div>
              <div>
                <dt>Subtítulos incluidos</dt>
                <dd>{data.meta.clasificacion_gasto}</dd>
              </div>
            </dl>
          </section>

          {/* 3 Tarjetas KPI principales: Ejecutado, Inicial aprobado, Vigente */}
          <section className="pg-kpi-grid" aria-label="Indicadores comparados entre gobiernos">
            {/* KPI 1: Gasto ejecutado (devengado) */}
            <article className="panel pg-kpi-card is-primary">
              <div className="pg-kpi-head">
                <span className="pg-kpi-kicker">Gasto ejecutado (devengado)</span>
                <span className={`pg-delta-pill ${(unidad === 'real_2025' ? resumenComparacion.deltaEjecRealPct : resumenComparacion.deltaEjecPP) >= 0 ? 'is-up' : 'is-down'}`}>
                  {unidad === 'real_2025'
                    ? `${fmtSignedPct(resumenComparacion.deltaEjecRealPct, 1)} real`
                    : fmtSignedPP(resumenComparacion.deltaEjecPP)}
                </span>
              </div>

              <div className="pg-kpi-pair">
                <div>
                  <small>{metaA.nombre}</small>
                  <strong>
                    {unidad === 'real_2025'
                      ? fmtBillonesOMillones(resumenComparacion.a.ejecutadoReal)
                      : `${fmtDec2.format(resumenComparacion.a.ejecutadoPct)}%`}
                  </strong>
                  <span className="pg-kpi-sub">{resumenComparacion.a.etiquetaPeriodo}</span>
                </div>
                <div>
                  <small>{metaB.nombre}</small>
                  <strong>
                    {unidad === 'real_2025'
                      ? fmtBillonesOMillones(resumenComparacion.b.ejecutadoReal)
                      : `${fmtDec2.format(resumenComparacion.b.ejecutadoPct)}%`}
                  </strong>
                  <span className="pg-kpi-sub">{resumenComparacion.b.etiquetaPeriodo}</span>
                </div>
              </div>

              <p className="pg-kpi-foot">
                Avance sobre presupuesto vigente: {fmtDec1.format(resumenComparacion.a.avancePct)}% vs {fmtDec1.format(resumenComparacion.b.avancePct)}%.
              </p>

              <button
                type="button"
                className={`pg-add-minuta-btn${isCifraSaved('ejecutado') ? ' is-saved' : ''}`}
                onClick={() => agregarCifraPresupuestoAMinuta('ejecutado')}
              >
                {isCifraSaved('ejecutado') ? '✓ En Mi minuta (ejecutado)' : '+ Agregar a Mi minuta'}
              </button>
            </article>

            {/* KPI 2: Presupuesto inicial aprobado (Ley) */}
            <article className="panel pg-kpi-card">
              <div className="pg-kpi-head">
                <span className="pg-kpi-kicker">Presupuesto inicial aprobado (Ley)</span>
                <span className={`pg-delta-pill ${(unidad === 'real_2025' ? resumenComparacion.deltaIniRealPct : resumenComparacion.deltaIniPP) >= 0 ? 'is-up' : 'is-down'}`}>
                  {unidad === 'real_2025'
                    ? `${fmtSignedPct(resumenComparacion.deltaIniRealPct, 1)} real`
                    : fmtSignedPP(resumenComparacion.deltaIniPP)}
                </span>
              </div>

              <div className="pg-kpi-pair">
                <div>
                  <small>{metaA.nombre}</small>
                  <strong>
                    {unidad === 'real_2025'
                      ? fmtBillonesOMillones(resumenComparacion.a.inicialReal)
                      : `${fmtDec2.format(resumenComparacion.a.inicialPct)}%`}
                  </strong>
                  <span className="pg-kpi-sub">Marco aprobado en Ley</span>
                </div>
                <div>
                  <small>{metaB.nombre}</small>
                  <strong>
                    {unidad === 'real_2025'
                      ? fmtBillonesOMillones(resumenComparacion.b.inicialReal)
                      : `${fmtDec2.format(resumenComparacion.b.inicialPct)}%`}
                  </strong>
                  <span className="pg-kpi-sub">Marco aprobado en Ley</span>
                </div>
              </div>

              <p className="pg-kpi-foot">
                Corresponde a la Ley de Presupuestos publicada antes del inicio de cada ejercicio.
              </p>

              <button
                type="button"
                className={`pg-add-minuta-btn${isCifraSaved('inicial') ? ' is-saved' : ''}`}
                onClick={() => agregarCifraPresupuestoAMinuta('inicial')}
              >
                {isCifraSaved('inicial') ? '✓ En Mi minuta (inicial)' : '+ Agregar a Mi minuta'}
              </button>
            </article>

            {/* KPI 3: Presupuesto vigente (con modificaciones) */}
            <article className="panel pg-kpi-card">
              <div className="pg-kpi-head">
                <span className="pg-kpi-kicker">Presupuesto vigente (modificado)</span>
                <span className={`pg-delta-pill ${(unidad === 'real_2025' ? resumenComparacion.deltaVigRealPct : resumenComparacion.deltaVigPP) >= 0 ? 'is-up' : 'is-down'}`}>
                  {unidad === 'real_2025'
                    ? `${fmtSignedPct(resumenComparacion.deltaVigRealPct, 1)} real`
                    : fmtSignedPP(resumenComparacion.deltaVigPP)}
                </span>
              </div>

              <div className="pg-kpi-pair">
                <div>
                  <small>{metaA.nombre}</small>
                  <strong>
                    {unidad === 'real_2025'
                      ? fmtBillonesOMillones(resumenComparacion.a.vigenteReal)
                      : `${fmtDec2.format(resumenComparacion.a.vigentePct)}%`}
                  </strong>
                  <span className="pg-kpi-sub">Ajuste vs inicial: {fmtSignedPct(resumenComparacion.a.modificacionPct, 1)}</span>
                </div>
                <div>
                  <small>{metaB.nombre}</small>
                  <strong>
                    {unidad === 'real_2025'
                      ? fmtBillonesOMillones(resumenComparacion.b.vigenteReal)
                      : `${fmtDec2.format(resumenComparacion.b.vigentePct)}%`}
                  </strong>
                  <span className="pg-kpi-sub">Ajuste vs inicial: {fmtSignedPct(resumenComparacion.b.modificacionPct, 1)}</span>
                </div>
              </div>

              <p className="pg-kpi-foot">
                Incluye reasignaciones, decretos modificatorios y suplementos al corte oficial.
              </p>

              <button
                type="button"
                className={`pg-add-minuta-btn${isCifraSaved('vigente') ? ' is-saved' : ''}`}
                onClick={() => agregarCifraPresupuestoAMinuta('vigente')}
              >
                {isCifraSaved('vigente') ? '✓ En Mi minuta (vigente)' : '+ Agregar a Mi minuta'}
              </button>
            </article>
          </section>

          {/* Conclusión breve en lenguaje claro */}
          <section className="panel pg-conclusion-box" aria-label="Conclusión breve">
            <div className="pg-conclusion-head">
              <span className="pg-kpi-kicker">Conclusión breve · Lectura ciudadana</span>
              <button
                type="button"
                className="text-button"
                onClick={() => setSubVista('glosas')}
              >
                Ver qué reglas (glosas) cambiaron →
              </button>
            </div>
            <p className="pg-conclusion-text">{resumenComparacion.conclusion}</p>
            <p className="pg-caution-line">
              <strong>Separación metodológica:</strong> Esta conclusión describe únicamente la evolución presupuestaria observada en DIPRES. Para atribuir una variación del gasto a una glosa específica se requiere evidencia documental adicional por programa.
            </p>
          </section>

          {/* Gráfico claro con evolución anual / equivalente */}
          <section className="panel pg-chart-panel" aria-label="Evolución anual del presupuesto de Vivienda">
            <div className="pg-chart-head">
              <div>
                <h3>
                  {esModoEquivalenteEneAgo
                    ? 'Evolución en tramo equivalente enero–agosto (mes 8)'
                    : 'Evolución anual del presupuesto de Vivienda (2018–2025)'}
                </h3>
                <p className="subtle">
                  {unidad === 'real_2025'
                    ? 'Montos en millones de pesos de 2025 (ajustados por IPC INE/BCCh). Toca un año para ver su ficha.'
                    : 'Participación (%) sobre el Gobierno Central Total en el mismo corte. Toca un año para ver su ficha.'}
                </p>
              </div>
              <div className="pg-chart-legend" aria-label="Leyenda del gráfico">
                <span><i className="pg-dot is-ini" /> Inicial aprobado</span>
                <span><i className="pg-dot is-vig" /> Vigente</span>
                <span><i className="pg-dot is-ejec" /> Ejecutado (devengado)</span>
                <span><i className="pg-dot is-shared" /> Año compartido</span>
              </div>
            </div>

            <div className="pg-svg-wrap">
              <svg
                viewBox="0 0 760 270"
                className="pg-svg-chart"
                role="img"
                aria-label="Gráfico de evolución de presupuesto aprobado, vigente y ejecutado en Vivienda"
              >
                {/* Líneas horizontales de grilla */}
                {[0, 0.25, 0.5, 0.75, 1].map(t => {
                  const y = 216 - t * 184
                  const val = chartMetrics.maxVal * t
                  return (
                    <g key={t}>
                      <line x1={68} y1={y} x2={740} y2={y} stroke="#e3ece8" strokeWidth={1} />
                      <text x={60} y={y + 4} textAnchor="end" fontSize="11" fill="#526a64">
                        {unidad === 'real_2025'
                          ? val === 0 ? '0' : `${fmtDec1.format(val / 1_000_000)}B`
                          : `${fmtDec1.format(val)}%`}
                      </text>
                    </g>
                  )
                })}

                {/* Columnas por año */}
                {serieActiva.map((row, idx) => {
                  const count = serieActiva.length
                  const plotW = 660
                  const slotW = plotW / count
                  const cx = 74 + slotW * idx + slotW / 2
                  const barW = Math.min(20, Math.max(10, slotW * 0.2))
                  const isSel = row.anio === filaDestacada.anio

                  const vIni = unidad === 'real_2025' ? row.real_2025_mm.inicial : row.participacion_nacional_pct.inicial
                  const vVig = unidad === 'real_2025' ? row.real_2025_mm.vigente : row.participacion_nacional_pct.vigente
                  const vEjec = unidad === 'real_2025' ? row.real_2025_mm.ejecutado : row.participacion_nacional_pct.ejecutado

                  const hIni = (vIni / chartMetrics.maxVal) * 184
                  const hVig = (vVig / chartMetrics.maxVal) * 184
                  const hEjec = (vEjec / chartMetrics.maxVal) * 184

                  const ejecColor = row.es_cambio_mando
                    ? '#a8561c'
                    : row.admin_id === 'pinera_2'
                      ? '#1b5e8a'
                      : '#0d6b58'

                  return (
                    <g
                      key={row.anio}
                      className="pg-bar-group"
                      style={{ cursor: 'pointer' }}
                      onClick={() => setAnioSeleccionado(row.anio)}
                    >
                      {isSel && (
                        <rect
                          x={cx - slotW * 0.44}
                          y={20}
                          width={slotW * 0.88}
                          height={202}
                          rx={8}
                          fill="#edf6f2"
                          stroke="#0d6b58"
                          strokeOpacity={0.3}
                        />
                      )}
                      {/* Inicial */}
                      <rect
                        x={cx - barW * 1.55}
                        y={216 - hIni}
                        width={barW}
                        height={Math.max(2, hIni)}
                        rx={3}
                        fill="#b8cbc4"
                      />
                      {/* Vigente */}
                      <rect
                        x={cx - barW * 0.5}
                        y={216 - hVig}
                        width={barW}
                        height={Math.max(2, hVig)}
                        rx={3}
                        fill="#6b968a"
                      />
                      {/* Ejecutado */}
                      <rect
                        x={cx + barW * 0.55}
                        y={216 - hEjec}
                        width={barW}
                        height={Math.max(2, hEjec)}
                        rx={3}
                        fill={ejecColor}
                      />
                      {/* Valor ejecutado arriba */}
                      <text
                        x={cx}
                        y={Math.min(216 - Math.max(hIni, hVig, hEjec) - 6, 206)}
                        textAnchor="middle"
                        fontSize="10.5"
                        fontWeight={isSel ? '700' : '600'}
                        fill="#102d28"
                      >
                        {unidad === 'real_2025'
                          ? `${fmtDec2.format(vEjec / 1_000_000)}B`
                          : `${fmtDec2.format(vEjec)}%`}
                      </text>
                      {/* Etiqueta año */}
                      <text
                        x={cx}
                        y={236}
                        textAnchor="middle"
                        fontSize="12"
                        fontWeight={isSel ? '800' : '600'}
                        fill={isSel ? '#0d6b58' : '#243c37'}
                      >
                        {row.anio}
                      </text>
                      {/* Subetiqueta administración / compartido */}
                      <text
                        x={cx}
                        y={252}
                        textAnchor="middle"
                        fontSize="9.5"
                        fontWeight={row.es_cambio_mando ? '700' : '500'}
                        fill={row.es_cambio_mando ? '#9b4a10' : '#5b726c'}
                      >
                        {row.es_cambio_mando
                          ? 'Compartido'
                          : row.admin_id === 'pinera_2'
                            ? 'Piñera II'
                            : 'Boric'}
                      </text>
                    </g>
                  )
                })}
              </svg>
            </div>

            {/* Selector táctil de año + Ficha del año seleccionado */}
            <div className="pg-year-pills" role="group" aria-label="Seleccionar año del gráfico">
              {serieActiva.map(r => (
                <button
                  key={r.anio}
                  type="button"
                  className={`pg-year-pill${r.anio === filaDestacada.anio ? ' is-active' : ''}${r.es_cambio_mando ? ' is-shared' : ''}`}
                  onClick={() => setAnioSeleccionado(r.anio)}
                >
                  {r.anio}{r.es_cambio_mando ? ' · Compartido' : ''}
                </button>
              ))}
            </div>

            <div className="pg-selected-year-box">
              <div className="pg-selected-year-head">
                <strong>
                  {filaDestacada.corte_etiqueta} · {filaDestacada.ley_numero}
                </strong>
                {filaDestacada.es_cambio_mando && (
                  <span className="pg-shared-badge">Año de cambio de mando (compartido · sin repartir)</span>
                )}
              </div>
              <div className="pg-selected-year-nums">
                <div>
                  <span>Inicial aprobado</span>
                  <strong>
                    {unidad === 'real_2025'
                      ? fmtBillonesOMillones(filaDestacada.real_2025_mm.inicial)
                      : `${fmtDec2.format(filaDestacada.participacion_nacional_pct.inicial)}% nac.`}
                  </strong>
                </div>
                <div>
                  <span>Vigente</span>
                  <strong>
                    {unidad === 'real_2025'
                      ? fmtBillonesOMillones(filaDestacada.real_2025_mm.vigente)
                      : `${fmtDec2.format(filaDestacada.participacion_nacional_pct.vigente)}% nac.`}
                  </strong>
                </div>
                <div>
                  <span>Ejecutado (devengado)</span>
                  <strong>
                    {unidad === 'real_2025'
                      ? fmtBillonesOMillones(filaDestacada.real_2025_mm.ejecutado)
                      : `${fmtDec2.format(filaDestacada.participacion_nacional_pct.ejecutado)}% nac.`}
                  </strong>
                </div>
                <div>
                  <span>Avance sobre vigente</span>
                  <strong>{fmtDec1.format(filaDestacada.avance_sobre_vigente_pct)}%</strong>
                </div>
              </div>
              <p className="pg-selected-year-meta">
                <strong>Proyecto presentado por:</strong> {filaDestacada.proyecto_presentado_por}.{' '}
                <strong>Ley aprobada:</strong> {filaDestacada.ley_aprobada_alcance}{' '}
                <strong>Ejecución:</strong> {filaDestacada.administracion_ejecucion}
              </p>
              <div className="pg-source-links">
                <a href={filaDestacada.fuentes.ejecucion_url} target="_blank" rel="noopener noreferrer">
                  DIPRES Ejecución {filaDestacada.anio} ({filaDestacada.fecha_corte}) ↗
                </a>
                <a href={filaDestacada.fuentes.ley_vigente_url} target="_blank" rel="noopener noreferrer">
                  DIPRES Ley Inicial/Vigente {filaDestacada.anio} ↗
                </a>
                <a href={filaDestacada.fuentes.dipres_partida_url} target="_blank" rel="noopener noreferrer">
                  {filaDestacada.ley_numero} · Partida 18 ↗
                </a>
              </div>
            </div>
          </section>

          {/* Tarjeta dedicada a años de cambio de mando */}
          <section className="panel pg-transition-panel" aria-label="Años de cambio de mando">
            <h3>Años de cambio de mando (compartidos, sin repartir el monto anual)</h3>
            <p className="subtle">
              Cuando la fuente oficial DIPRES entrega un total anual (o acumulado sin corte al 11 de marzo), identificamos quién presentó el proyecto, qué fijó la ley y bajo qué administraciones se ejecutó, conservando íntegro el monto.
            </p>
            <div className="pg-transition-grid">
              {aniosCompartidosRelevantes.map(row => (
                <article key={`${row.tramo}-${row.anio}`} className="pg-transition-card">
                  <div className="pg-transition-head">
                    <strong>{row.anio} · {row.ley_numero}</strong>
                    <span className="pg-shared-badge">Año compartido</span>
                  </div>
                  <dl className="pg-transition-dl">
                    <div>
                      <dt>Proyecto presentado por</dt>
                      <dd>{row.proyecto_presentado_por}</dd>
                    </div>
                    <div>
                      <dt>Ley aprobada ({row.ley_fecha_publicacion})</dt>
                      <dd>{row.ley_aprobada_alcance}</dd>
                    </div>
                    <div>
                      <dt>Ejecución registrada</dt>
                      <dd>
                        {row.administracion_ejecucion} Total {row.corte_etiqueta.toLowerCase()}:{' '}
                        <strong>{fmtBillonesOMillones(row.real_2025_mm.ejecutado)}</strong> (pesos 2025; {fmtDec2.format(row.participacion_nacional_pct.ejecutado)}% del gasto nacional).
                      </dd>
                    </div>
                  </dl>
                </article>
              ))}
            </div>
          </section>

          {/* Desglose completo en Ver detalle */}
          <details className="panel pg-details-box">
            <summary className="pg-details-summary">
              Ver detalle: tabla completa, capítulos MINVU, composición económica, IPC y vacíos de cobertura
            </summary>

            <div className="pg-details-body">
              <h4>1. Serie completa ({esModoEquivalenteEneAgo ? 'corte enero–agosto' : 'cierres anuales diciembre'})</h4>
              <div className="table-scroll">
                <table className="pg-detail-table">
                  <thead>
                    <tr>
                      <th>Año</th>
                      <th>Administración</th>
                      <th className="numeric">Inicial nominal</th>
                      <th className="numeric">Vigente nominal</th>
                      <th className="numeric">Ejecutado nominal</th>
                      <th className="numeric">Factor IPC 2025</th>
                      <th className="numeric">Ejecutado real 2025</th>
                      <th className="numeric">% Gasto nac.</th>
                      <th className="numeric">Avance</th>
                      <th>Fuente</th>
                    </tr>
                  </thead>
                  <tbody>
                    {serieActiva.map(r => (
                      <tr key={r.anio} className={r.es_cambio_mando ? 'is-shared-row' : ''}>
                        <td><strong>{r.anio}</strong></td>
                        <td>{r.es_cambio_mando ? 'Año compartido' : r.admin_id === 'pinera_2' ? 'Piñera II' : 'Boric'}</td>
                        <td className="numeric">{fmtMMCompacto(r.nominal_mm.inicial)}</td>
                        <td className="numeric">{fmtMMCompacto(r.nominal_mm.vigente)}</td>
                        <td className="numeric">{fmtMMCompacto(r.nominal_mm.ejecutado)}</td>
                        <td className="numeric">{r.factor_pesos_2025.toFixed(4)}</td>
                        <td className="numeric"><strong>{fmtMMCompacto(r.real_2025_mm.ejecutado)}</strong></td>
                        <td className="numeric">{fmtDec2.format(r.participacion_nacional_pct.ejecutado)}%</td>
                        <td className="numeric">{fmtDec1.format(r.avance_sobre_vigente_pct)}%</td>
                        <td>
                          <a href={r.fuentes.ejecucion_url} target="_blank" rel="noopener noreferrer">
                            DIPRES ↗
                          </a>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <h4>2. Composición del gasto ejecutado en {filaDestacada.corte_etiqueta}</h4>
              <div className="pg-split-detail">
                <div className="pg-mini-card">
                  <h5>Por capítulo institucional (nominal)</h5>
                  <ul>
                    <li>
                      <span>Servicios Regionales de Vivienda y Urbanización ({filaDestacada.capitulos_ejecutado_nominal_mm.serviu_count} SERVIU)</span>
                      <strong>{fmtMMCompacto(filaDestacada.capitulos_ejecutado_nominal_mm.serviu_regionales)}</strong>
                    </li>
                    <li>
                      <span>Subsecretaría de Vivienda y Urbanismo (Cap. 01)</span>
                      <strong>{fmtMMCompacto(filaDestacada.capitulos_ejecutado_nominal_mm.subsecretaria)}</strong>
                    </li>
                    <li>
                      <span>Parque Metropolitano de Santiago</span>
                      <strong>{fmtMMCompacto(filaDestacada.capitulos_ejecutado_nominal_mm.parque_metropolitano)}</strong>
                    </li>
                  </ul>
                </div>

                <div className="pg-mini-card">
                  <h5>Por clasificación económica (pesos de 2025)</h5>
                  <ul>
                    <li>
                      <span>Transferencias de capital / subsidios habitacionales (Subt. 33)</span>
                      <strong>{fmtMMCompacto(filaDestacada.desglose_ejecutado_real_2025_mm.transferencias_capital_subsidios)}</strong>
                    </li>
                    <li>
                      <span>Inversión directa e iniciativas urbanas (Subt. 29–31)</span>
                      <strong>{fmtMMCompacto(filaDestacada.desglose_ejecutado_real_2025_mm.inversion)}</strong>
                    </li>
                    <li>
                      <span>Gasto corriente de operación y personal (Subt. 21–26)</span>
                      <strong>{fmtMMCompacto(filaDestacada.desglose_ejecutado_real_2025_mm.corriente)}</strong>
                    </li>
                  </ul>
                </div>
              </div>

              <h4>3. Vacíos de cobertura y notas metodológicas</h4>
              <ul className="pg-gaps-list">
                {data.meta.vacios_cobertura.map((v, i) => (
                  <li key={i}>{v}</li>
                ))}
              </ul>
            </div>
          </details>
        </div>
      )}

      {/* ============================================================
          VISTA 2 · GLOSAS OFICIALES EN PARALELO
      ============================================================ */}
      {subVista === 'glosas' && (
        <div className="pg-section-stack" role="tabpanel" aria-label="Comparación de glosas oficiales de Vivienda">
          {/* Selector de los dos años de glosas + filtros por tipo de regla */}
          <section className="panel pg-glosas-toolbar">
            <div className="pg-glosas-years">
              <label className="pg-field">
                <span>Año base (texto A)</span>
                <select
                  aria-label="Año base de glosa"
                  value={glosaAnioA}
                  onChange={e => setGlosaAnioA(Number(e.target.value))}
                >
                  {data.glosas_anios_disponibles.map(y => (
                    <option key={y} value={y}>
                      Ley {y} ({data.glosas_familias[0].versiones[String(y)].ley_numero})
                    </option>
                  ))}
                </select>
              </label>

              <label className="pg-field">
                <span>Año comparado (texto B)</span>
                <select
                  aria-label="Año comparado de glosa"
                  value={glosaAnioB}
                  onChange={e => setGlosaAnioB(Number(e.target.value))}
                >
                  {data.glosas_anios_disponibles.map(y => (
                    <option key={y} value={y}>
                      Ley {y} ({data.glosas_familias[0].versiones[String(y)].ley_numero})
                    </option>
                  ))}
                </select>
              </label>

              <div className="pg-diff-toggle-wrap">
                <label className="pg-check-inline">
                  <input
                    type="checkbox"
                    checked={soloCambiosResaltados}
                    onChange={e => setSoloCambiosResaltados(e.target.checked)}
                  />
                  <span>Resaltar pasajes agregados, eliminados o modificados</span>
                </label>
              </div>
            </div>

            {/* Filtros por tipo de regla */}
            <div className="pg-filter-pills" role="group" aria-label="Filtrar glosas por tipo de regla">
              {([
                ['todas', `Todas (${data.glosas_familias.length})`],
                ['limites_uso', 'Límites de uso'],
                ['requisitos_transferencia', 'Requisitos para transferir'],
                ['obligaciones_informar', 'Obligaciones de informar'],
              ] as const).map(([val, lbl]) => (
                <button
                  key={val}
                  type="button"
                  aria-pressed={glosaFiltro === val}
                  className={`pg-filter-pill${glosaFiltro === val ? ' is-active' : ''}`}
                  onClick={() => setGlosaFiltro(val)}
                >
                  {lbl}
                </button>
              ))}
            </div>

            {/* Pregunta directa: ¿Qué glosa restringió más el gasto? + Nota Proyecto vs Ley vigente */}
            <div className="pg-glosas-callouts">
              <button
                type="button"
                className={`pg-restriccion-trigger${mostrarRestricciones ? ' is-open' : ''}`}
                aria-expanded={mostrarRestricciones}
                onClick={() => setMostrarRestricciones(v => !v)}
              >
                <span>
                  <strong>¿Qué glosa restringió más el gasto?</strong>{' '}
                  <small>Ver condiciones concretas endurecidas por aspecto y evidencia textual</small>
                </span>
                <span aria-hidden="true">{mostrarRestricciones ? '▲' : '▼'}</span>
              </button>

              {mostrarRestricciones && (
                <div className="pg-restricciones-box">
                  <p className="subtle">
                    Cuando dos o más condiciones regulan aspectos distintos del gasto habitacional, se explican por separado con su evidencia textual verificable:
                  </p>
                  <div className="pg-restricciones-grid">
                    {data.restricciones_clave.map((item, idx) => (
                      <article key={item.id} className="pg-restriccion-card">
                        <span className="pg-restriccion-num">Aspecto {idx + 1} · {item.ubicacion}</span>
                        <h4>{item.aspecto_regulado}</h4>
                        <p><strong>Condición endurecida:</strong> {item.condicion_endurecida}</p>
                        <p className="pg-evidencia-quote"><strong>Evidencia textual:</strong> {item.evidencia_textual}</p>
                        <button
                          type="button"
                          className="text-button"
                          onClick={() => {
                            setGlosaFiltro('todas')
                            setGlosaAnioA(item.anios_comparar_sugeridos[0])
                            setGlosaAnioB(item.anios_comparar_sugeridos[1])
                            setGlosaAbiertaId(item.glosa_id)
                            setMostrarRestricciones(false)
                          }}
                        >
                          Abrir comparación {item.anios_comparar_sugeridos[0]} vs {item.anios_comparar_sugeridos[1]} →
                        </button>
                      </article>
                    ))}
                  </div>
                </div>
              )}

              <div className="pg-proyecto-vs-ley-note" role="note">
                <strong>Texto vigente vs Proyecto de Ley:</strong> Todas las tarjetas abajo comparan el <em>texto vigente publicado de la Ley de Presupuestos</em>.{' '}
                {data.meta.nota_proyecto_vs_ley_2025.resumen}{' '}
                <a href={data.meta.nota_proyecto_vs_ley_2025.proyecto_url} target="_blank" rel="noopener noreferrer">
                  Proyecto 2025 (PDF DIPRES) ↗
                </a>{' '}
                ·{' '}
                <a href={data.meta.nota_proyecto_vs_ley_2025.ley_vigente_url} target="_blank" rel="noopener noreferrer">
                  Ley 2025 vigente (PDF DIPRES) ↗
                </a>
                <span className="pg-gap-inline"> · Cobertura textual verificada: 2021–2026 (2018–2020: Sin dato disponible en este corte).</span>
              </div>
            </div>
          </section>

          {/* Listado interactivo de glosas vinculadas por materia */}
          <div className="pg-glosa-list">
            {glosasFiltradas.map(fam => {
              const verA = fam.versiones[String(glosaAnioA)]
              const verB = fam.versiones[String(glosaAnioB)]
              const isOpen = fam.id === glosaAbiertaId
              const bothAvailable = Boolean(verA?.disponible && verB?.disponible)
              const diff = bothAvailable ? computeWordDiff(verA.texto, verB.texto) : null
              const sameText = Boolean(bothAvailable && diff && diff.changedCount === 0)
              const numberChanged = Boolean(verA?.disponible && verB?.disponible && verA.numero_glosa !== verB.numero_glosa)
              const isSavedGlosa = minutaDraft.glosaRelevante?.id === `${fam.id}-${glosaAnioA}-${glosaAnioB}`

              return (
                <article key={fam.id} className={`panel pg-glosa-card${isOpen ? ' is-open' : ''}`}>
                  <button
                    type="button"
                    className="pg-glosa-header-btn"
                    aria-expanded={isOpen}
                    onClick={() => setGlosaAbiertaId(isOpen ? '' : fam.id)}
                  >
                    <div className="pg-glosa-header-main">
                      <div className="pg-glosa-badges">
                        {fam.categorias.map(cat => (
                          <span key={cat} className={`pg-cat-chip is-${cat}`}>
                            {CATEGORIA_LABELS[cat]}
                          </span>
                        ))}
                        {numberChanged && (
                          <span className="pg-renum-chip">
                            Renumerada: {verA.numero_glosa} ({glosaAnioA}) → {verB.numero_glosa} ({glosaAnioB})
                          </span>
                        )}
                        {!bothAvailable ? (
                          <span className="pg-status-chip is-missing">Cobertura parcial / Sin equivalente</span>
                        ) : sameText ? (
                          <span className="pg-status-chip is-same">Sin cambios entre {glosaAnioA} y {glosaAnioB}</span>
                        ) : (
                          <span className="pg-status-chip is-changed">Cambió redacción ({glosaAnioA} vs {glosaAnioB})</span>
                        )}
                      </div>
                      <h3>{fam.titulo}</h3>
                      <p className="pg-glosa-sub">{fam.programa_alcance}</p>
                    </div>
                    <span className="pg-glosa-chevron" aria-hidden="true">{isOpen ? '▲' : '▼'}</span>
                  </button>

                  {isOpen && (
                    <div className="pg-glosa-body">
                      {/* Explicación en lenguaje sencillo */}
                      <dl className="pg-plain-grid">
                        <div>
                          <dt>A qué recursos se aplica</dt>
                          <dd>{fam.a_que_recursos_aplica}</dd>
                        </div>
                        <div>
                          <dt>Qué permite o exige</dt>
                          <dd>{fam.que_permite_o_exige}</dd>
                        </div>
                        <div>
                          <dt>Qué diferencia práctica introduce</dt>
                          <dd>{fam.diferencia_practica}</dd>
                        </div>
                      </dl>

                      {/* Vínculo por materia aunque cambie el número */}
                      <p className="pg-trace-line">
                        <strong>Trazabilidad por materia (aunque cambie el número):</strong> {fam.traza_numeracion}
                      </p>

                      {verA?.nota_proyecto_vs_ley && (
                        <p className="pg-proj-note">
                          <strong>Nota Proyecto vs Ley ({verA.anio}):</strong> {verA.nota_proyecto_vs_ley}
                        </p>
                      )}
                      {verB?.nota_proyecto_vs_ley && verB.anio !== verA?.anio && (
                        <p className="pg-proj-note">
                          <strong>Nota Proyecto vs Ley ({verB.anio}):</strong> {verB.nota_proyecto_vs_ley}
                        </p>
                      )}

                      {/* Leyenda de resaltado */}
                      {bothAvailable && soloCambiosResaltados && !sameText && (
                        <div className="pg-diff-legend" aria-label="Leyenda de cambios textuales">
                          <span><mark className="pg-diff-del">Tachado en rojo</mark> eliminado o reemplazado desde {glosaAnioA}</span>
                          <span><mark className="pg-diff-ins">Resaltado en verde</mark> agregado o modificado en {glosaAnioB}</span>
                        </div>
                      )}

                      {/* Lectura en paralelo */}
                      <div className="pg-parallel-grid">
                        {/* Columna A */}
                        <div className="pg-parallel-col">
                          <div className="pg-parallel-head">
                            <div>
                              <span className="pg-parallel-year">{glosaAnioA} · {verA.ley_numero}</span>
                              <strong>{verA.ubicacion}</strong>
                            </div>
                            <span className="pg-tipo-badge">{verA.tipo_texto_etiqueta}</span>
                          </div>

                          {!verA.disponible ? (
                            <div className="pg-missing-glosa">
                              <strong>Sin dato disponible ({glosaAnioA})</strong>
                              <p>{verA.sin_dato_motivo}</p>
                            </div>
                          ) : (
                            <div className="pg-legal-text">
                              {diff && soloCambiosResaltados && !sameText ? (
                                diff.left.map((seg, idx) =>
                                  seg.type === 'del' ? (
                                    <del key={idx} className="pg-diff-del">{seg.text} </del>
                                  ) : (
                                    <span key={idx}>{seg.text} </span>
                                  ),
                                )
                              ) : (
                                verA.texto
                              )}
                            </div>
                          )}

                          <div className="pg-parallel-foot">
                            <span>Fecha publicación/corte: {verA.fecha_corte}</span>
                            <a href={verA.url} target="_blank" rel="noopener noreferrer">
                              Abrir documento oficial {glosaAnioA} ↗
                            </a>
                          </div>
                        </div>

                        {/* Columna B */}
                        <div className="pg-parallel-col">
                          <div className="pg-parallel-head">
                            <div>
                              <span className="pg-parallel-year">{glosaAnioB} · {verB.ley_numero}</span>
                              <strong>{verB.ubicacion}</strong>
                            </div>
                            <span className="pg-tipo-badge">{verB.tipo_texto_etiqueta}</span>
                          </div>

                          {!verB.disponible ? (
                            <div className="pg-missing-glosa">
                              <strong>Sin dato disponible ({glosaAnioB})</strong>
                              <p>{verB.sin_dato_motivo}</p>
                            </div>
                          ) : (
                            <div className="pg-legal-text">
                              {diff && soloCambiosResaltados && !sameText ? (
                                diff.right.map((seg, idx) =>
                                  seg.type === 'ins' ? (
                                    <ins key={idx} className="pg-diff-ins">{seg.text} </ins>
                                  ) : (
                                    <span key={idx}>{seg.text} </span>
                                  ),
                                )
                              ) : (
                                verB.texto
                              )}
                            </div>
                          )}

                          <div className="pg-parallel-foot">
                            <span>Fecha publicación/corte: {verB.fecha_corte}</span>
                            <a href={verB.url} target="_blank" rel="noopener noreferrer">
                              Abrir documento oficial {glosaAnioB} ↗
                            </a>
                          </div>
                        </div>
                      </div>

                      {/* Regla vs ejecución: exige evidencia */}
                      <p className="pg-caution-line">
                        <strong>Regla aprobada vs ejecución observada:</strong> {fam.nota_evidencia_gasto}
                      </p>

                      <div className="pg-glosa-actions">
                        <button
                          type="button"
                          className={`pg-add-minuta-btn${isSavedGlosa ? ' is-saved' : ''}`}
                          onClick={() => agregarGlosaAMinuta(fam, verA, verB)}
                        >
                          {isSavedGlosa
                            ? `✓ Glosa (${glosaAnioA} vs ${glosaAnioB}) en Mi minuta`
                            : `+ Agregar pasaje de glosa a Mi minuta`}
                        </button>
                        {totalItemsMinuta > 0 && (
                          <button
                            type="button"
                            className="secondary-btn"
                            onClick={() => {
                              setMinutaMode('vista_previa')
                              setMinutaOpen(true)
                            }}
                          >
                            Revisar e imprimir Mi minuta ({totalItemsMinuta}) →
                          </button>
                        )}
                      </div>
                    </div>
                  )}
                </article>
              )
            })}
          </div>
        </div>
      )}

      {/* Modal compartido de Mi minuta */}
      <MiMinutaPanel
        open={minutaOpen}
        mode={minutaMode}
        onModeChange={setMinutaMode}
        onClose={() => setMinutaOpen(false)}
        draft={minutaDraft}
        onDraftChange={updateMinutaDraft}
        defaultAnio={2025}
        defaultComuna="11201"
      />

      {/* Hoja oculta en pantalla y visible únicamente al imprimir Carta B&N */}
      <div className="minuta-print-root" aria-hidden="true">
        <MinutaSheet draft={minutaDraft} isPrintOnly />
      </div>
    </div>
  )
}
