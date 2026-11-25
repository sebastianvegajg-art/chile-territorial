import { useEffect, useId, useMemo, useRef, useState } from 'react'
import {
  ANIOS_AYSEN,
  COMUNAS_AYSEN,
  fetchAysenEconomia,
  fetchAysenPresupuestos,
  fetchAysenProyectos,
  getComunaNombre,
} from '../services/aysenPilotoService'
import type {
  AysenEconomiaResponse,
  AysenPresupuestosResponse,
  AysenProyectosResponse,
  RolBilletera,
} from '../services/aysenPilotoService'
import {
  MINUTA_PREGUNTAS,
  analizarExtensionUnaPagina,
  buildReferenciasNumeradas,
  buildSugerenciasArrastre,
  buildSugerenciasEconomia,
  buildSugerenciasGastoCorriente,
  buildSugerenciasGestionObra,
  createEmptyMinutaDraft,
  generarRespuestaCotidiana,
} from './minutaModel'
import type {
  MinutaCifra,
  MinutaDraft,
  MinutaPreguntaId,
  SugerenciaWizardResult,
} from './minutaModel'

export type MinutaModalMode = 'crear' | 'editar' | 'vista_previa'

const ANIOS_PRESUPUESTOS = ANIOS_AYSEN.filter(y => y >= 2018)
const ANIOS_PROYECTOS = ANIOS_AYSEN.filter(y => y >= 2021)

const INSTITUCIONES_PRESUPUESTO_OPCIONES: readonly {
  rol: RolBilletera
  etiqueta: string
}[] = [
  { rol: 'municipal', etiqueta: 'Municipalidad (comuna de Aysén)' },
  { rol: 'regional', etiqueta: 'Gobierno Regional de Aysén (GORE)' },
  { rol: 'nacional_en_region', etiqueta: 'Dirección de Vialidad (MOP) en Aysén' },
  { rol: 'nacional', etiqueta: 'Gobierno Central Nacional (referencia)' },
] as const

/* ============================================================
   HOJA DE 1 PÁGINA (VISTA PREVIA DIGITAL + IMPRESIÓN CARTA B&N)
============================================================ */

export function MinutaSheet({
  draft,
  sheetRef,
  isPrintOnly = false,
}: {
  draft: MinutaDraft
  sheetRef?: React.RefObject<HTMLDivElement | null>
  isPrintOnly?: boolean
}) {
  const { referencias, indicePorCifraId, indiceObra } = useMemo(
    () => buildReferenciasNumeradas(draft),
    [draft],
  )

  const hasPartialCoverage = draft.cifras.some(c => c.coberturaParcial)
  const missingCifras = draft.cifras.filter(c => !c.disponible)
  const fechaGeneracion = useMemo(() => {
    try {
      return new Intl.DateTimeFormat('es-CL', {
        day: '2-digit',
        month: 'long',
        year: 'numeric',
      }).format(new Date(draft.actualizadoEn || Date.now()))
    } catch {
      return new Date().toISOString().slice(0, 10)
    }
  }, [draft.actualizadoEn])

  const tituloVisible =
    draft.titulo.trim() || 'Minuta técnica · Región de Aysén'
  const respuestaVisible =
    draft.respuesta.trim() ||
    generarRespuestaCotidiana(draft) ||
    'Selecciona una pregunta o guarda hasta tres cifras desde el visualizador para redactar la respuesta al aire.'

  return (
    <article
      ref={sheetRef}
      className={`minuta-sheet${isPrintOnly ? ' is-print-only' : ''}`}
      aria-label="Hoja de minuta técnica de una página"
    >
      <header className="minuta-sheet-header">
        <div className="minuta-sheet-brand">
          <span className="minuta-sheet-kicker">Chile Territorial · Observatorio de Aysén</span>
          <span className="minuta-sheet-date">Minuta de 1 página · {fechaGeneracion}</span>
        </div>
        <h2 className="minuta-sheet-title">{tituloVisible}</h2>
      </header>

      <section className="minuta-sheet-answer" aria-label="Respuesta en lenguaje cotidiano">
        <span className="minuta-sheet-section-label">Respuesta rápida (al aire)</span>
        <p className="minuta-sheet-answer-text">{respuestaVisible}</p>
        {(hasPartialCoverage || missingCifras.length > 0) && (
          <p className="minuta-sheet-coverage-flag">
            {missingCifras.length > 0 && (
              <span>
                <strong>Antecedente pendiente:</strong>{' '}
                {missingCifras[0].antecedenteFaltante || 'Falta registro oficial publicado para completar el cálculo.'}
              </span>
            )}
            {hasPartialCoverage && (
              <span>
                {missingCifras.length > 0 ? ' · ' : ''}
                <strong>Cobertura parcial:</strong>{' '}
                {draft.cifras.find(c => c.coberturaParcial && c.notaCobertura)?.notaCobertura ||
                  'Las cifras reflejan únicamente los organismos o períodos con corte oficial publicado.'}
              </span>
            )}
          </p>
        )}
      </section>

      <section className="minuta-sheet-figures" aria-label="Cifras clave seleccionadas">
        <span className="minuta-sheet-section-label">
          Cifras clave ({draft.cifras.length})
        </span>

        {draft.cifras.length === 0 ? (
          <p className="minuta-sheet-empty">
            Aún no hay cifras incorporadas. Usa «Crear desde pregunta» o pulsa «Agregar a minuta» en cualquier indicador del sitio.
          </p>
        ) : (
          <div className={`minuta-sheet-grid count-${Math.min(3, draft.cifras.length)}`}>
            {draft.cifras.map(cifra => {
              const refNum = indicePorCifraId[cifra.id]
              return (
                <div
                  key={cifra.id}
                  className={`minuta-figure-card${!cifra.disponible ? ' is-missing' : ''}`}
                >
                  <div className="minuta-figure-top">
                    <span className="minuta-figure-label">
                      {cifra.etiqueta}
                      {refNum && <sup className="minuta-ref-sup">[{refNum}]</sup>}
                    </span>
                  </div>

                  <p className={`minuta-figure-value${!cifra.disponible ? ' is-missing' : ''}`}>
                    {cifra.valorTexto}
                  </p>

                  {cifra.subvalor && (
                    <p className="minuta-figure-subvalue">{cifra.subvalor}</p>
                  )}

                  <p className="minuta-figure-expl">{cifra.explicacion}</p>

                  {cifra.baseCalculo && (
                    <p className="minuta-figure-base">
                      <strong>Base de cálculo:</strong> {cifra.baseCalculo}
                    </p>
                  )}

                  {!cifra.disponible && cifra.antecedenteFaltante && (
                    <p className="minuta-figure-missing-note">
                      <strong>Falta antecedente:</strong> {cifra.antecedenteFaltante}
                    </p>
                  )}

                  <p className="minuta-figure-context">
                    {cifra.periodo} · {cifra.territorio} · {cifra.institucion} · {cifra.unidad}
                  </p>
                </div>
              )
            })}
          </div>
        )}
      </section>

      {draft.obraEjemplo && (
        <section className="minuta-sheet-example" aria-label="Obra de ejemplo">
          <div className="minuta-example-head">
            <span className="minuta-sheet-section-label">
              Obra de ejemplo {indiceObra ? <sup className="minuta-ref-sup">[{indiceObra}]</sup> : null}
            </span>
            <span className="minuta-example-tag">{draft.obraEjemplo.clasificacion}</span>
          </div>
          <h3 className="minuta-example-name">{draft.obraEjemplo.nombre}</h3>
          <p className="minuta-example-meta">
            {draft.obraEjemplo.institucion} · {draft.obraEjemplo.comuna} · Período {draft.obraEjemplo.periodo}
            {draft.obraEjemplo.administracionOrigen
              ? ` · Contratada en gestión ${draft.obraEjemplo.administracionOrigen}`
              : ' · Gestión de origen: Sin dato disponible'}
          </p>
          <dl className="minuta-example-nums">
            <div>
              <dt>Costo total</dt>
              <dd>{draft.obraEjemplo.costoTotalTexto}</dd>
            </div>
            <div>
              <dt>Pagado en {draft.obraEjemplo.periodo}</dt>
              <dd>{draft.obraEjemplo.pagadoAnioTexto}</dd>
            </div>
            <div>
              <dt>Saldo por pagar</dt>
              <dd>{draft.obraEjemplo.saldoPorPagarTexto}</dd>
            </div>
          </dl>
        </section>
      )}

      <footer className="minuta-sheet-footnotes" aria-label="Fuentes oficiales numeradas">
        <span className="minuta-sheet-section-label">Fuentes y referencias</span>
        {referencias.length === 0 ? (
          <p className="subtle">Las fuentes oficiales se numerarán automáticamente al incorporar cifras.</p>
        ) : (
          <ol className="minuta-footnotes-list">
            {referencias.map(ref => (
              <li key={ref.id} value={ref.numero}>
                <span className="minuta-fn-num">[{ref.numero}]</span>{' '}
                <strong>{ref.organismo}</strong> — {ref.documento}.{' '}
                <span className="minuta-fn-cut">Fecha de corte: {ref.fechaCorte}.</span>
                {ref.url && (
                  <>
                    {' '}
                    <a
                      href={ref.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="minuta-fn-link no-print"
                    >
                      Abrir fuente <span aria-hidden="true">↗</span>
                    </a>
                    <span className="minuta-fn-print-url print-only-inline"> ({ref.url})</span>
                  </>
                )}
              </li>
            ))}
          </ol>
        )}
      </footer>
    </article>
  )
}

/* ============================================================
   PANEL PRINCIPAL DE MI MINUTA (ASISTENTE + EDITOR + VISTA PREVIA)
============================================================ */

export function MiMinutaPanel({
  open,
  mode,
  onModeChange,
  onClose,
  draft,
  onDraftChange,
  defaultAnio,
  defaultComuna,
}: {
  open: boolean
  mode: MinutaModalMode
  onModeChange: (next: MinutaModalMode) => void
  onClose: () => void
  draft: MinutaDraft
  onDraftChange: (next: MinutaDraft) => void
  defaultAnio: number
  defaultComuna: string
}) {
  const headingId = useId()
  const titleInputId = useId()
  const answerInputId = useId()
  const previewSheetRef = useRef<HTMLDivElement>(null)
  const [measuredHeight, setMeasuredHeight] = useState<number | null>(null)

  // Estado del asistente «¿Qué quieres explicar?»
  const [selectedQuestion, setSelectedQuestion] = useState<Exclude<MinutaPreguntaId, 'libre'>>(
    draft.preguntaId !== 'libre' ? draft.preguntaId : 'gasto_corriente_institucion',
  )
  const [wizAnio, setWizAnio] = useState<number>(defaultAnio)
  const [wizRolInst, setWizRolInst] = useState<RolBilletera>('municipal')
  const [wizComuna, setWizComuna] = useState<string>(defaultComuna || '11201')
  const [wizComunaOpcional, setWizComunaOpcional] = useState<string>('')
  const [wizObraQuery, setWizObraQuery] = useState<string>('')
  const [wizObraId, setWizObraId] = useState<string>('')

  // Datos cargados por el asistente
  const [wizLoading, setWizLoading] = useState(false)
  const [wizError, setWizError] = useState<string | null>(null)
  const [wizEcoData, setWizEcoData] = useState<AysenEconomiaResponse | null>(null)
  const [wizPresupData, setWizPresupData] = useState<AysenPresupuestosResponse | null>(null)
  const [wizProyData, setWizProyData] = useState<AysenProyectosResponse | null>(null)

  // Selección de cifras sugeridas en el asistente
  const [selectedCifraIds, setSelectedCifraIds] = useState<Record<string, boolean>>({})
  const [includeObraSugerida, setIncludeObraSugerida] = useState<boolean>(true)
  const [feedbackMsg, setFeedbackMsg] = useState<string>('')

  // Sincronizar período válido cuando cambia la pregunta elegida
  useEffect(() => {
    if (selectedQuestion === 'gasto_corriente_institucion' && wizAnio < 2018) {
      setWizAnio(2025)
    } else if (
      (selectedQuestion === 'arrastre_inversion' || selectedQuestion === 'gestion_obra') &&
      wizAnio < 2021
    ) {
      setWizAnio(2025)
    }
  }, [selectedQuestion, wizAnio])

  // Consultar datos oficiales pertinentes al abrir el asistente o cambiar filtros
  useEffect(() => {
    if (!open || mode !== 'crear') return
    const controller = new AbortController()
    setWizLoading(true)
    setWizError(null)

    if (selectedQuestion === 'crecimiento_economia') {
      fetchAysenEconomia(wizAnio, controller.signal)
        .then(data => {
          if (!controller.signal.aborted) {
            setWizEcoData(data)
            setWizLoading(false)
          }
        })
        .catch(err => {
          if (!controller.signal.aborted) {
            setWizError(err instanceof Error ? err.message : 'No se pudieron consultar los datos económicos.')
            setWizLoading(false)
          }
        })
    } else if (selectedQuestion === 'gasto_corriente_institucion') {
      const comunaConsulta = wizRolInst === 'municipal' ? wizComuna : '11201'
      fetchAysenPresupuestos(wizAnio, comunaConsulta, controller.signal)
        .then(data => {
          if (!controller.signal.aborted) {
            setWizPresupData(data)
            setWizLoading(false)
          }
        })
        .catch(err => {
          if (!controller.signal.aborted) {
            setWizError(err instanceof Error ? err.message : 'No se pudieron consultar los presupuestos.')
            setWizLoading(false)
          }
        })
    } else {
      fetchAysenProyectos(
        {
          anio: wizAnio,
          comuna: wizComunaOpcional || undefined,
          q: selectedQuestion === 'gestion_obra' && wizObraQuery.trim() ? wizObraQuery.trim() : undefined,
        },
        controller.signal,
      )
        .then(data => {
          if (!controller.signal.aborted) {
            setWizProyData(data)
            if (selectedQuestion === 'gestion_obra') {
              const firstId = data.proyectos[0]?.id ?? data.proyectos_insuficientes[0]?.id ?? ''
              setWizObraId(prev => {
                const exists =
                  data.proyectos.some(p => p.id === prev) ||
                  data.proyectos_insuficientes.some(p => p.id === prev)
                return exists ? prev : firstId
              })
            }
            setWizLoading(false)
          }
        })
        .catch(err => {
          if (!controller.signal.aborted) {
            setWizError(err instanceof Error ? err.message : 'No se pudieron consultar los proyectos.')
            setWizLoading(false)
          }
        })
    }

    return () => controller.abort()
  }, [open, mode, selectedQuestion, wizAnio, wizRolInst, wizComuna, wizComunaOpcional, wizObraQuery])

  // Construir sugerencias del asistente
  const sugerencias: SugerenciaWizardResult | null = useMemo(() => {
    if (selectedQuestion === 'crecimiento_economia' && wizEcoData) {
      return buildSugerenciasEconomia(wizEcoData, wizAnio)
    }
    if (selectedQuestion === 'gasto_corriente_institucion' && wizPresupData) {
      return buildSugerenciasGastoCorriente(wizPresupData, wizRolInst, wizAnio)
    }
    if (selectedQuestion === 'arrastre_inversion' && wizProyData) {
      const terr = wizComunaOpcional ? `Comuna de ${getComunaNombre(wizComunaOpcional)}` : 'Región de Aysén'
      return buildSugerenciasArrastre(wizProyData, wizAnio, terr)
    }
    if (selectedQuestion === 'gestion_obra' && wizProyData) {
      const allObras = [...wizProyData.proyectos, ...wizProyData.proyectos_insuficientes]
      const chosen = allObras.find(o => o.id === wizObraId) ?? allObras[0]
      if (!chosen) return null
      return buildSugerenciasGestionObra(chosen, wizAnio)
    }
    return null
  }, [selectedQuestion, wizEcoData, wizPresupData, wizProyData, wizAnio, wizRolInst, wizComunaOpcional, wizObraId])

  // Seleccionar por defecto todas las cifras sugeridas al cambiar sugerencias
  useEffect(() => {
    if (!sugerencias) return
    const nextMap: Record<string, boolean> = {}
    sugerencias.cifras.forEach(c => {
      nextMap[c.id] = true
    })
    setSelectedCifraIds(nextMap)
    setIncludeObraSugerida(Boolean(sugerencias.obraSugerida))
  }, [sugerencias])

  // Medir alto de la hoja en Vista Previa solo a ancho de escritorio equivalente a Carta (en móvil las columnas se apilan solo para lectura táctil)
  useEffect(() => {
    if (!open || mode !== 'vista_previa') {
      setMeasuredHeight(null)
      return
    }
    const el = previewSheetRef.current
    if (!el) return
    const measure = () => {
      if (el.offsetWidth >= 640) {
        setMeasuredHeight(el.offsetHeight)
      } else {
        setMeasuredHeight(null)
      }
    }
    measure()
    if (typeof ResizeObserver !== 'undefined') {
      const ro = new ResizeObserver(measure)
      ro.observe(el)
      return () => ro.disconnect()
    }
    return undefined
  }, [open, mode, draft])

  // Cerrar con Escape
  useEffect(() => {
    if (!open) return
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [open, onClose])

  const extensionReport = useMemo(
    () => analizarExtensionUnaPagina(draft, measuredHeight),
    [draft, measuredHeight],
  )

  if (!open) return null

  const obrasDisponibles = wizProyData
    ? [...wizProyData.proyectos, ...wizProyData.proyectos_insuficientes]
    : []

  function applyWizardSelection(strategy: 'replace' | 'merge') {
    if (!sugerencias) return
    const picked = sugerencias.cifras.filter(c => selectedCifraIds[c.id])
    const obra = includeObraSugerida && sugerencias.obraSugerida ? sugerencias.obraSugerida : null

    if (picked.length === 0 && !obra) {
      setFeedbackMsg('Marca al menos una cifra o una obra de ejemplo para incorporar a tu minuta.')
      return
    }

    const nextCifras =
      strategy === 'replace'
        ? picked
        : [
            ...draft.cifras,
            ...picked.filter(p => !draft.cifras.some(existing => existing.id === p.id)),
          ]

    const baseDraft: MinutaDraft = {
      version: 1,
      preguntaId: selectedQuestion,
      titulo: strategy === 'replace' || !draft.titulo.trim() ? sugerencias.tituloSugerido : draft.titulo,
      respuesta: strategy === 'replace' ? '' : draft.respuesta,
      respuestaEditadaManualmente: strategy === 'replace' ? false : draft.respuestaEditadaManualmente,
      cifras: nextCifras,
      obraEjemplo: obra ?? (strategy === 'merge' ? draft.obraEjemplo : null),
      actualizadoEn: new Date().toISOString(),
    }

    const respuestaFinal =
      baseDraft.respuestaEditadaManualmente && baseDraft.respuesta.trim()
        ? baseDraft.respuesta
        : generarRespuestaCotidiana(baseDraft)

    onDraftChange({
      ...baseDraft,
      respuesta: respuestaFinal,
    })
    setFeedbackMsg('')
    onModeChange('vista_previa')
  }

  function handleMoveCifra(index: number, direction: -1 | 1) {
    const target = index + direction
    if (target < 0 || target >= draft.cifras.length) return
    const copy = [...draft.cifras]
    const [item] = copy.splice(index, 1)
    copy.splice(target, 0, item)
    const updated: MinutaDraft = {
      ...draft,
      cifras: copy,
      actualizadoEn: new Date().toISOString(),
    }
    onDraftChange(updated)
  }

  function handleRemoveCifra(id: string) {
    const nextCifras = draft.cifras.filter(c => c.id !== id)
    const updated: MinutaDraft = {
      ...draft,
      cifras: nextCifras,
      actualizadoEn: new Date().toISOString(),
    }
    if (!updated.respuestaEditadaManualmente) {
      updated.respuesta = generarRespuestaCotidiana(updated)
    }
    onDraftChange(updated)
  }

  function handleUpdateCifraExplanation(id: string, explicacion: string) {
    onDraftChange({
      ...draft,
      cifras: draft.cifras.map(c => (c.id === id ? { ...c, explicacion } : c)),
      actualizadoEn: new Date().toISOString(),
    })
  }

  function handleRegenerateAnswer() {
    const regenerated = generarRespuestaCotidiana(draft)
    onDraftChange({
      ...draft,
      respuesta: regenerated,
      respuestaEditadaManualmente: false,
      actualizadoEn: new Date().toISOString(),
    })
  }

  function handleClearDraft() {
    onDraftChange(createEmptyMinutaDraft())
    setFeedbackMsg('Borrador vaciado. Puedes comenzar con una nueva pregunta o guardar cifras desde el sitio.')
  }

  function handlePrint() {
    window.print()
  }

  const aniosSelector =
    selectedQuestion === 'gasto_corriente_institucion'
      ? ANIOS_PRESUPUESTOS
      : selectedQuestion === 'arrastre_inversion' || selectedQuestion === 'gestion_obra'
        ? ANIOS_PROYECTOS
        : ANIOS_AYSEN

  return (
    <div
      className="minuta-backdrop no-print"
      role="dialog"
      aria-modal="true"
      aria-labelledby={headingId}
      onClick={e => {
        if (e.target === e.currentTarget) onClose()
      }}
    >
      <div className="minuta-drawer">
        {/* Cabecera del panel Mi minuta */}
        <div className="minuta-drawer-head">
          <div>
            <p className="eyebrow">Hoja de 1 página para entrevista o reunión</p>
            <h2 id={headingId} className="minuta-drawer-title">Mi minuta</h2>
          </div>
          <button
            type="button"
            className="secondary-btn minuta-close-btn"
            onClick={onClose}
            aria-label="Cerrar Mi minuta"
          >
            Cerrar ✕
          </button>
        </div>

        {/* Navegación interna de 3 pasos */}
        <div className="minuta-mode-tabs" role="tablist" aria-label="Pasos de Mi minuta">
          <button
            type="button"
            role="tab"
            aria-selected={mode === 'crear'}
            className={`minuta-mode-tab${mode === 'crear' ? ' is-active' : ''}`}
            onClick={() => onModeChange('crear')}
          >
            1. Crear desde pregunta
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={mode === 'editar'}
            className={`minuta-mode-tab${mode === 'editar' ? ' is-active' : ''}`}
            onClick={() => onModeChange('editar')}
          >
            2. Editar borrador ({draft.cifras.length})
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={mode === 'vista_previa'}
            className={`minuta-mode-tab${mode === 'vista_previa' ? ' is-active' : ''}`}
            onClick={() => onModeChange('vista_previa')}
          >
            3. Vista previa e imprimir
          </button>
        </div>

        <div className="minuta-drawer-body">
          {/* ==========================================================
              MODO 1 · CREAR DESDE UNA PREGUNTA («¿Qué quieres explicar?»)
          ========================================================== */}
          {mode === 'crear' && (
            <div className="minuta-wizard">
              <div className="minuta-wizard-intro">
                <h3>¿Qué quieres explicar?</h3>
                <p className="subtle">
                  Elige una pregunta concreta. Solo te pediremos los filtros necesarios y te sugeriremos hasta tres cifras verificadas con su fuente oficial.
                </p>
              </div>

              <div className="minuta-question-options" role="radiogroup" aria-label="¿Qué quieres explicar?">
                {MINUTA_PREGUNTAS.map(opt => {
                  const isSelected = selectedQuestion === opt.id
                  return (
                    <button
                      key={opt.id}
                      type="button"
                      role="radio"
                      aria-checked={isSelected}
                      className={`minuta-question-option${isSelected ? ' is-selected' : ''}`}
                      onClick={() => setSelectedQuestion(opt.id)}
                    >
                      <strong>{opt.etiqueta}</strong>
                      <span>{opt.descripcion}</span>
                      <small>Filtros: {opt.filtrosResumen}</small>
                    </button>
                  )
                })}
              </div>

              {/* Filtros pertinentes según la pregunta elegida */}
              <div className="minuta-filters-box">
                <h4>Filtros pertinentes</h4>
                <div className="minuta-filters-grid">
                  <label className="aysen-control-field">
                    <span>Período (Año)</span>
                    <select
                      value={wizAnio}
                      onChange={e => setWizAnio(Number(e.target.value))}
                    >
                      {aniosSelector.map(y => (
                        <option key={y} value={y}>
                          {y}{y >= 2026 ? ' (en curso)' : ''}
                        </option>
                      ))}
                    </select>
                  </label>

                  {selectedQuestion === 'gasto_corriente_institucion' && (
                    <label className="aysen-control-field">
                      <span>Institución</span>
                      <select
                        value={wizRolInst}
                        onChange={e => setWizRolInst(e.target.value as RolBilletera)}
                      >
                        {INSTITUCIONES_PRESUPUESTO_OPCIONES.map(opt => (
                          <option key={opt.rol} value={opt.rol}>
                            {opt.etiqueta}
                          </option>
                        ))}
                      </select>
                    </label>
                  )}

                  {selectedQuestion === 'gasto_corriente_institucion' && wizRolInst === 'municipal' && (
                    <label className="aysen-control-field">
                      <span>Comuna</span>
                      <select
                        value={wizComuna}
                        onChange={e => setWizComuna(e.target.value)}
                      >
                        {COMUNAS_AYSEN.map(c => (
                          <option key={c.cut} value={c.cut}>
                            Municipalidad de {c.nombre} ({c.cut})
                          </option>
                        ))}
                      </select>
                    </label>
                  )}

                  {(selectedQuestion === 'arrastre_inversion' || selectedQuestion === 'gestion_obra') && (
                    <label className="aysen-control-field">
                      <span>Comuna (opcional)</span>
                      <select
                        value={wizComunaOpcional}
                        onChange={e => setWizComunaOpcional(e.target.value)}
                      >
                        <option value="">Toda la Región de Aysén</option>
                        {COMUNAS_AYSEN.map(c => (
                          <option key={c.cut} value={c.cut}>
                            {c.nombre} ({c.cut})
                          </option>
                        ))}
                      </select>
                    </label>
                  )}

                  {selectedQuestion === 'gestion_obra' && (
                    <>
                      <label className="aysen-control-field">
                        <span>Filtrar obra (opcional)</span>
                        <input
                          type="search"
                          value={wizObraQuery}
                          placeholder="Ej. Ruta 7, puente, hospital…"
                          onChange={e => setWizObraQuery(e.target.value)}
                        />
                      </label>
                      <label className="aysen-control-field minuta-filter-wide">
                        <span>Obra registrada ({obrasDisponibles.length})</span>
                        <select
                          value={wizObraId}
                          onChange={e => setWizObraId(e.target.value)}
                          disabled={obrasDisponibles.length === 0}
                        >
                          {obrasDisponibles.length === 0 ? (
                            <option value="">Sin obras registradas con estos filtros</option>
                          ) : (
                            obrasDisponibles.map(o => (
                              <option key={o.id} value={o.id}>
                                {o.nombre} ({o.institucion}{o.comuna ? ` · ${o.comuna}` : ''})
                              </option>
                            ))
                          )}
                        </select>
                      </label>
                    </>
                  )}
                </div>
              </div>

              {/* Resultados y cifras sugeridas */}
              {wizLoading ? (
                <div className="aysen-card aysen-loading" role="status" aria-live="polite">
                  <span className="aysen-spinner" aria-hidden="true" />
                  <span>Consultando fuentes oficiales para sugerir cifras…</span>
                </div>
              ) : wizError ? (
                <div className="aysen-error-box" role="alert">
                  <p className="error">{wizError}</p>
                </div>
              ) : !sugerencias ? (
                <p className="aysen-empty">
                  No se encontraron registros suficientes con los filtros elegidos. Prueba otro período o comuna.
                </p>
              ) : (
                <div className="minuta-suggestions-block">
                  <div className="minuta-suggested-title-box">
                    <span className="minuta-sheet-section-label">Título sugerido para tu minuta</span>
                    <strong>{sugerencias.tituloSugerido}</strong>
                  </div>

                  {sugerencias.antecedenteFaltanteGlobal && (
                    <div className="minuta-missing-alert" role="alert">
                      <strong>Sin dato disponible — Antecedente pendiente:</strong>{' '}
                      <span>{sugerencias.antecedenteFaltanteGlobal}</span>
                    </div>
                  )}

                  {sugerencias.notaCobertura && !sugerencias.antecedenteFaltanteGlobal && (
                    <p className="aysen-hint-bar" role="note">
                      {sugerencias.notaCobertura}
                    </p>
                  )}

                  {/* Tabla de montos usados en el cálculo (transparencia presupuestaria) */}
                  {sugerencias.detalleCalculo && sugerencias.detalleCalculo.length > 0 && (
                    <div className="minuta-calc-audit">
                      <h5>Montos oficiales usados en el cálculo</h5>
                      <dl className="minuta-calc-grid">
                        {sugerencias.detalleCalculo.map(row => (
                          <div key={row.etiqueta}>
                            <dt>{row.etiqueta}</dt>
                            <dd className={row.valor === 'Sin dato disponible' ? 'is-missing' : ''}>
                              {row.valor}
                            </dd>
                          </div>
                        ))}
                      </dl>
                    </div>
                  )}

                  {/* Checkboxes de las hasta 3 cifras sugeridas */}
                  <div className="minuta-suggestions-list">
                    <h4>Cifras sugeridas (elige las que quieres incorporar)</h4>
                    {sugerencias.cifras.map(cifra => {
                      const checked = Boolean(selectedCifraIds[cifra.id])
                      return (
                        <label
                          key={cifra.id}
                          className={`minuta-suggestion-item${checked ? ' is-checked' : ''}${!cifra.disponible ? ' is-missing' : ''}`}
                        >
                          <input
                            type="checkbox"
                            checked={checked}
                            onChange={e =>
                              setSelectedCifraIds(prev => ({ ...prev, [cifra.id]: e.target.checked }))
                            }
                          />
                          <div className="minuta-suggestion-body">
                            <div className="minuta-suggestion-head">
                              <strong>{cifra.etiqueta}</strong>
                              <span className={`minuta-suggestion-val${!cifra.disponible ? ' is-missing' : ''}`}>
                                {cifra.valorTexto}
                              </span>
                            </div>
                            {cifra.subvalor && (
                              <p className="minuta-suggestion-sub">{cifra.subvalor}</p>
                            )}
                            <p className="minuta-suggestion-expl">{cifra.explicacion}</p>
                            {cifra.baseCalculo && (
                              <p className="minuta-suggestion-meta">
                                <strong>Base de cálculo:</strong> {cifra.baseCalculo}
                              </p>
                            )}
                            {!cifra.disponible && cifra.antecedenteFaltante && (
                              <p className="minuta-suggestion-missing">
                                <strong>Antecedente faltante:</strong> {cifra.antecedenteFaltante}
                              </p>
                            )}
                            <p className="minuta-suggestion-meta">
                              Fuente: {cifra.fuente.organismo} · Corte: {cifra.fuente.fechaCorte}
                            </p>
                          </div>
                        </label>
                      )
                    })}

                    {sugerencias.obraSugerida && (
                      <label className={`minuta-suggestion-item${includeObraSugerida ? ' is-checked' : ''}`}>
                        <input
                          type="checkbox"
                          checked={includeObraSugerida}
                          onChange={e => setIncludeObraSugerida(e.target.checked)}
                        />
                        <div className="minuta-suggestion-body">
                          <div className="minuta-suggestion-head">
                            <strong>Incluir obra de ejemplo: {sugerencias.obraSugerida.nombre}</strong>
                            <span className="minuta-suggestion-val">{sugerencias.obraSugerida.pagadoAnioTexto}</span>
                          </div>
                          <p className="minuta-suggestion-expl">{sugerencias.obraSugerida.resumen}</p>
                        </div>
                      </label>
                    )}
                  </div>

                  {feedbackMsg && <p className="error" role="alert">{feedbackMsg}</p>}

                  <div className="minuta-wizard-actions">
                    <button
                      type="button"
                      className="primary"
                      onClick={() => applyWizardSelection('replace')}
                    >
                      Armar minuta con estas cifras →
                    </button>
                    {draft.cifras.length > 0 && (
                      <button
                        type="button"
                        className="secondary-btn"
                        onClick={() => applyWizardSelection('merge')}
                      >
                        + Sumar al borrador actual ({draft.cifras.length})
                      </button>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* ==========================================================
              MODO 2 · EDITAR BORRADOR (TÍTULO, RESPUESTA, ORDEN, QUITAR)
          ========================================================== */}
          {mode === 'editar' && (
            <div className="minuta-editor">
              {/* Alerta de extensión a 1 página */}
              <div className={`minuta-fit-banner is-${extensionReport.nivel}`} role="status">
                <strong>{extensionReport.cabeEnUnaPagina ? '✓ 1 página carta' : '⚠ Revisa la extensión'}</strong>
                <span>{extensionReport.resumen}</span>
                {extensionReport.sugerencias.length > 0 && (
                  <ul>
                    {extensionReport.sugerencias.map((s, idx) => (
                      <li key={idx}>{s}</li>
                    ))}
                  </ul>
                )}
              </div>

              <div className="minuta-field">
                <label htmlFor={titleInputId}>
                  <span>Pregunta o título de la minuta</span>
                  <small>{draft.titulo.length}/125 caracteres sugeridos</small>
                </label>
                <input
                  id={titleInputId}
                  type="text"
                  value={draft.titulo}
                  placeholder="Ej. De cada $100 ejecutados por la Municipalidad de Aysén en 2025, ¿cuántos correspondieron a gasto corriente?"
                  onChange={e =>
                    onDraftChange({
                      ...draft,
                      titulo: e.target.value,
                      actualizadoEn: new Date().toISOString(),
                    })
                  }
                />
              </div>

              <div className="minuta-field">
                <label htmlFor={answerInputId}>
                  <span>Respuesta al aire (2 líneas en lenguaje cotidiano)</span>
                  <small>{draft.respuesta.length}/280 caracteres sugeridos</small>
                </label>
                <textarea
                  id={answerInputId}
                  rows={3}
                  value={draft.respuesta}
                  placeholder="Respuesta clara basada únicamente en los datos seleccionados…"
                  onChange={e =>
                    onDraftChange({
                      ...draft,
                      respuesta: e.target.value,
                      respuestaEditadaManualmente: true,
                      actualizadoEn: new Date().toISOString(),
                    })
                  }
                />
                <div className="minuta-field-actions">
                  <button
                    type="button"
                    className="text-button"
                    onClick={handleRegenerateAnswer}
                    disabled={draft.cifras.length === 0 && !draft.obraEjemplo}
                  >
                    ↻ Regenerar respuesta desde los datos elegidos
                  </button>
                </div>
              </div>

              {/* Lista ordenable de cifras guardadas */}
              <div className="minuta-editor-section">
                <div className="minuta-editor-section-head">
                  <h4>Cifras incorporadas ({draft.cifras.length} · recomendado hasta 3)</h4>
                  <button
                    type="button"
                    className="text-button"
                    onClick={() => onModeChange('crear')}
                  >
                    + Agregar desde pregunta
                  </button>
                </div>

                {draft.cifras.length === 0 ? (
                  <p className="aysen-empty">
                    No has guardado cifras todavía. Pulsa «Agregar a minuta» en Resumen, Economía, Presupuestos o Proyectos, o usa «Crear desde pregunta».
                  </p>
                ) : (
                  <ul className="minuta-editor-list">
                    {draft.cifras.map((cifra, idx) => (
                      <li key={cifra.id} className="minuta-editor-item">
                        <div className="minuta-editor-item-top">
                          <div>
                            <span className="minuta-editor-order">#{idx + 1}</span>{' '}
                            <strong>{cifra.etiqueta}</strong>
                            <span className={`minuta-editor-val${!cifra.disponible ? ' is-missing' : ''}`}>
                              {' '}· {cifra.valorTexto}
                            </span>
                          </div>
                          <div className="minuta-editor-controls">
                            <button
                              type="button"
                              className="minuta-icon-btn"
                              aria-label={`Subir ${cifra.etiqueta}`}
                              disabled={idx === 0}
                              onClick={() => handleMoveCifra(idx, -1)}
                            >
                              ↑
                            </button>
                            <button
                              type="button"
                              className="minuta-icon-btn"
                              aria-label={`Bajar ${cifra.etiqueta}`}
                              disabled={idx === draft.cifras.length - 1}
                              onClick={() => handleMoveCifra(idx, 1)}
                            >
                              ↓
                            </button>
                            <button
                              type="button"
                              className="minuta-icon-btn is-danger"
                              aria-label={`Quitar ${cifra.etiqueta}`}
                              onClick={() => handleRemoveCifra(cifra.id)}
                            >
                              ✕
                            </button>
                          </div>
                        </div>

                        <p className="minuta-editor-context">
                          Contexto congelado: <strong>{cifra.periodo}</strong> · {cifra.territorio} · {cifra.institucion} ({cifra.unidad})
                          {cifra.baseCalculo ? ` · Base: ${cifra.baseCalculo}` : ''}
                        </p>

                        <label className="minuta-inline-expl">
                          <span>Qué representa (1 línea):</span>
                          <input
                            type="text"
                            value={cifra.explicacion}
                            onChange={e => handleUpdateCifraExplanation(cifra.id, e.target.value)}
                          />
                        </label>
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              {/* Obra de ejemplo */}
              {draft.obraEjemplo && (
                <div className="minuta-editor-section">
                  <div className="minuta-editor-section-head">
                    <h4>Obra de ejemplo</h4>
                    <button
                      type="button"
                      className="text-button"
                      onClick={() =>
                        onDraftChange({
                          ...draft,
                          obraEjemplo: null,
                          actualizadoEn: new Date().toISOString(),
                        })
                      }
                    >
                      Quitar obra de ejemplo
                    </button>
                  </div>
                  <div className="minuta-editor-item">
                    <strong>{draft.obraEjemplo.nombre}</strong>
                    <p className="minuta-editor-context">
                      {draft.obraEjemplo.institucion} · {draft.obraEjemplo.comuna} · Período {draft.obraEjemplo.periodo} · Pagado: {draft.obraEjemplo.pagadoAnioTexto}
                    </p>
                  </div>
                </div>
              )}

              <div className="minuta-wizard-actions">
                <button
                  type="button"
                  className="primary"
                  onClick={() => onModeChange('vista_previa')}
                >
                  Revisar vista previa e imprimir →
                </button>
                <button
                  type="button"
                  className="secondary-btn"
                  onClick={handleClearDraft}
                >
                  Vaciar borrador
                </button>
              </div>
            </div>
          )}

          {/* ==========================================================
              MODO 3 · VISTA PREVIA E IMPRIMIR / GUARDAR COMO PDF
          ========================================================== */}
          {mode === 'vista_previa' && (
            <div className="minuta-preview-wrap">
              <div className="minuta-preview-toolbar">
                <div className={`minuta-fit-banner is-${extensionReport.nivel}`} role="status">
                  <strong>
                    {extensionReport.cabeEnUnaPagina
                      ? '✓ Lista para 1 página carta vertical'
                      : '⚠ Excede 1 página carta'}
                  </strong>
                  <span>{extensionReport.resumen}</span>
                  {extensionReport.sugerencias.length > 0 && (
                    <ul>
                      {extensionReport.sugerencias.map((s, idx) => (
                        <li key={idx}>{s}</li>
                      ))}
                    </ul>
                  )}
                </div>

                <div className="minuta-preview-actions">
                  <button
                    type="button"
                    className="primary minuta-print-btn"
                    onClick={handlePrint}
                    disabled={draft.cifras.length === 0 && !draft.obraEjemplo && !draft.titulo.trim()}
                  >
                    Imprimir o guardar como PDF
                  </button>
                  <button
                    type="button"
                    className="secondary-btn"
                    onClick={() => onModeChange('editar')}
                  >
                    Editar título o cifras
                  </button>
                  <button
                    type="button"
                    className="secondary-btn"
                    onClick={() => onModeChange('crear')}
                  >
                    Cambiar pregunta
                  </button>
                </div>
              </div>

              <div className="minuta-sheet-frame">
                <MinutaSheet draft={draft} sheetRef={previewSheetRef} />
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
