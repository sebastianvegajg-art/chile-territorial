import { useCallback, useEffect, useId, useState } from 'react'
import type { FormEvent } from 'react'
import { ApiServiceError } from './services/bcchService'
import {
  REGIONES_CHILE,
  consultarLaboratorio,
  fetchCrucesResumen,
  fetchLaboralResumen,
  triggerFileDownload,
} from './services/fase2Service'
import type {
  CrucesResumenResponse,
  LaboratorioConsultaResponse,
  LaboralResumenResponse,
} from './services/fase2Service'

const PREGUNTAS_SUGERIDAS: readonly {
  id: string
  etiqueta: string
  territorio: string
  pregunta: string
}[] = [
  {
    id: 'aysen-estructura',
    etiqueta: 'Estructura productiva Aysén',
    territorio: '11',
    pregunta: '¿Qué peso tiene la Administración Pública y la Pesca en la estructura productiva de Aysén?',
  },
  {
    id: 'aysen-per-capita',
    etiqueta: 'PIB per cápita y convergencia',
    territorio: '11',
    pregunta: '¿Cómo evoluciona el PIB per cápita de Aysén frente a Chile y existe convergencia regional?',
  },
  {
    id: 'aysen-billeteras',
    etiqueta: '3 billeteras y DIPRES Aysén',
    territorio: '11',
    pregunta: '¿Cuál es el estado de las tres billeteras fiscales y la ejecución DIPRES de Aysén?',
  },
  {
    id: 'regiones-hhi',
    etiqueta: 'Concentración HHI 2025',
    territorio: 'CL',
    pregunta: '¿Qué regiones muestran mayor concentración HHI y especialización económica en 2025?',
  },
] as const

function fmtTimestamp(value?: string | null): string {
  if (!value) return 'No informada'
  const trimmed = value.trim()
  if (!trimmed) return 'No informada'
  if (trimmed.includes('T')) {
    const date = trimmed.slice(0, 10)
    const time = trimmed.slice(11, 19).replace(/Z$/, '')
    return time ? `${date} · ${time} UTC` : date
  }
  return trimmed.slice(0, 19)
}

function escapeHtml(text: string): string {
  return text
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
}

function buildDossierMarkdown(res: LaboratorioConsultaResponse): string {
  if (res.dossier_markdown && res.dossier_markdown.trim().length > 0) {
    return res.dossier_markdown
  }

  const lines: string[] = [
    `# Dossier de Investigación Territorial · ${res.territorio_nombre}`,
    '',
    `- **ID consulta:** \`${res.id_consulta}\``,
    `- **Fecha de generación:** ${fmtTimestamp(res.generado_en)}`,
    `- **Territorio:** ${res.territorio_nombre} (\`${res.territorio}\`)`,
    `- **Modo:** Solo lectura · ${res.motor}`,
    '',
    '## 1. Pregunta formulada',
    res.pregunta,
    '',
    '## 2. Fuentes oficiales verificadas',
    ...(res.fuentes_verificadas.length > 0
      ? res.fuentes_verificadas.map(
          f =>
            `- **${f.institucion}**${f.corte ? ` · Corte: ${f.corte}` : ''}${f.endpoint ? ` · \`${f.endpoint}\`` : ''}${f.series && f.series.length ? ` · Series: ${f.series.join(', ')}` : ''}`,
        )
      : ['- Cortes oficiales publicados de Chile Territorial (BCCh, DIPRES, SINIM, INE).']),
    '',
    '## 3. Hipótesis y método',
    res.hipotesis_y_metodo,
    '',
    '## 4. Métricas reproducibles',
    ...(res.metricas_reproducibles.length > 0
      ? res.metricas_reproducibles.map(
          m =>
            `- **${m.nombre}:** ${m.valor}${m.unidad ? ` ${m.unidad}` : ''}${m.periodo ? ` (${m.periodo})` : ''}${m.serie ? ` · \`${m.serie}\`` : ''}`,
        )
      : ['- Sin métricas estructuradas adicionales en este corte.']),
    '',
    '## 5. Tabla de evidencia',
  ]

  if (res.tabla_evidencia && res.tabla_evidencia.columnas.length > 0) {
    const cols = res.tabla_evidencia.columnas
    lines.push(`| ${cols.join(' | ')} |`)
    lines.push(`| ${cols.map(() => '---').join(' | ')} |`)
    for (const row of res.tabla_evidencia.filas) {
      lines.push(`| ${row.map(c => c.replaceAll('|', '\\|')).join(' | ')} |`)
    }
  } else {
    lines.push('Sin tabla adjunta para esta consulta.')
  }

  lines.push(
    '',
    '## 6. Evidencia favorable / hallazgos principales',
    ...(res.evidencia_favorable.length > 0
      ? res.evidencia_favorable.map(item => `- ${item}`)
      : ['- Ver métricas reproducibles y tabla de evidencia arriba.']),
    '',
    '## 7. Hipótesis alternativas y evidencia contraria',
    ...(res.hipotesis_alternativas.length > 0
      ? res.hipotesis_alternativas.map(item => `- ${item}`)
      : ['- Los indicadores agregados admiten lecturas complementarias según deflactores, cobertura y composición sectorial.']),
    '',
    '## 8. Interpretación sobria',
    res.interpretacion,
    '',
    '## 9. Limitaciones metodológicas',
    ...(res.limitaciones_metodologicas.length > 0
      ? res.limitaciones_metodologicas.map(item => `- ${item}`)
      : ['- Análisis descriptivo de solo lectura; correlación no implica causalidad y el PIB regional nunca se imputa a comunas.']),
    '',
    '## 10. Gobernanza y reproducibilidad',
    'Este dossier fue generado de forma determinista sobre cortes publicados de solo lectura en Chile Territorial, sin servicios de IA de pago y sin alterar datos oficiales.',
  )

  return lines.join('\n')
}

function buildDossierHtml(res: LaboratorioConsultaResponse): string {
  if (res.dossier_html && res.dossier_html.trim().length > 0) {
    return res.dossier_html
  }

  const metricsHtml = res.metricas_reproducibles.length > 0
    ? `<div class="grid">${res.metricas_reproducibles
        .map(
          m => `<div class="card"><div class="label">${escapeHtml(m.nombre)}</div><div class="val">${escapeHtml(m.valor)}${m.unidad ? ` ${escapeHtml(m.unidad)}` : ''}</div><div class="meta">${escapeHtml([m.periodo, m.fuente, m.serie].filter(Boolean).join(' · '))}</div></div>`,
        )
        .join('')}</div>`
    : '<p>Sin métricas estructuradas adicionales.</p>'

  const tableHtml = res.tabla_evidencia && res.tabla_evidencia.columnas.length > 0
    ? `<table><thead><tr>${res.tabla_evidencia.columnas.map(c => `<th>${escapeHtml(c)}</th>`).join('')}</tr></thead><tbody>${res.tabla_evidencia.filas
        .map(row => `<tr>${row.map(cell => `<td>${escapeHtml(cell)}</td>`).join('')}</tr>`)
        .join('')}</tbody></table>`
    : '<p>Sin tabla de evidencia adjunta.</p>'

  const listHtml = (items: string[], fallback: string) =>
    items.length > 0
      ? `<ul>${items.map(item => `<li>${escapeHtml(item)}</li>`).join('')}</ul>`
      : `<p>${escapeHtml(fallback)}</p>`

  return `<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>Dossier · ${escapeHtml(res.territorio_nombre)} · Chile Territorial</title>
<style>
  body { font-family: "Inter", "Segoe UI", system-ui, sans-serif; color: #112b29; background: #f3f0e9; margin: 0; padding: 2rem 1rem; line-height: 1.55; }
  main { max-width: 920px; margin: 0 auto; background: #fff; border: 1px solid #d6e0d9; border-radius: 14px; padding: 2rem; }
  h1 { color: #07392f; margin-top: 0; letter-spacing: -.03em; }
  h2 { color: #065a46; font-size: 1.05rem; margin-top: 1.6rem; border-bottom: 1px solid #e3ebe5; padding-bottom: .3rem; }
  .eyebrow { text-transform: uppercase; letter-spacing: .1em; font-size: .75rem; font-weight: 700; color: #065a46; }
  .meta-bar { background: #f7faf8; border: 1px solid #d6e0d9; border-radius: 8px; padding: .85rem 1rem; font-size: .85rem; margin: 1rem 0; }
  .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: .75rem; }
  .card { background: #f7faf8; border: 1px solid #d6e0d9; border-radius: 8px; padding: .8rem; }
  .label { font-size: .74rem; text-transform: uppercase; font-weight: 700; color: #4b5e59; }
  .val { font-size: 1.2rem; font-weight: 700; color: #07392f; margin: .25rem 0; }
  .meta { font-size: .76rem; color: #4b5e59; }
  table { width: 100%; border-collapse: collapse; font-size: .85rem; margin-top: .5rem; }
  th, td { border-bottom: 1px solid #d6e0d9; padding: .5rem .6rem; text-align: left; }
  thead { background: #edf3ef; }
  footer { margin-top: 2rem; padding-top: 1rem; border-top: 1px dashed #c8d7ce; font-size: .78rem; color: #4b5e59; }
</style>
</head>
<body>
<main>
  <div class="eyebrow">Chile Territorial · Dossier de Investigación Verificada (Solo lectura)</div>
  <h1>${escapeHtml(res.territorio_nombre)} (${escapeHtml(res.territorio)})</h1>
  <div class="meta-bar">
    <strong>ID consulta:</strong> ${escapeHtml(res.id_consulta)} ·
    <strong>Generado:</strong> ${escapeHtml(fmtTimestamp(res.generado_en))} ·
    <strong>Motor:</strong> ${escapeHtml(res.motor)}
  </div>
  <h2>1. Pregunta formulada</h2>
  <p>${escapeHtml(res.pregunta)}</p>
  <h2>2. Fuentes oficiales verificadas</h2>
  ${listHtml(
    res.fuentes_verificadas.map(f => `${f.institucion}${f.corte ? ` (${f.corte})` : ''}${f.endpoint ? ` · ${f.endpoint}` : ''}`),
    'Cortes oficiales publicados de Chile Territorial.',
  )}
  <h2>3. Hipótesis y método</h2>
  <p>${escapeHtml(res.hipotesis_y_metodo)}</p>
  <h2>4. Métricas reproducibles</h2>
  ${metricsHtml}
  <h2>5. Tabla de evidencia</h2>
  ${tableHtml}
  <h2>6. Evidencia favorable / hallazgos principales</h2>
  ${listHtml(res.evidencia_favorable, 'Ver métricas reproducibles y tabla de evidencia.')}
  <h2>7. Hipótesis alternativas y evidencia contraria</h2>
  ${listHtml(res.hipotesis_alternativas, 'Contrastar siempre con series complementarias de empleo, precios y cobertura.')}
  <h2>8. Interpretación sobria</h2>
  <p>${escapeHtml(res.interpretacion)}</p>
  <h2>9. Limitaciones metodológicas</h2>
  ${listHtml(res.limitaciones_metodologicas, 'Análisis descriptivo de solo lectura; correlación no implica causalidad.')}
  <h2>10. Gobernanza y reproducibilidad</h2>
  <p>Generado de manera determinista sobre bases publicadas de solo lectura de Chile Territorial, sin servicios de IA de pago y sin modificar datos oficiales.</p>
  <footer>Chile Territorial · Observatorio Económico y Territorial Auditable</footer>
</main>
</body>
</html>`
}

export function LaboratorioView() {
  const territorioId = useId()
  const preguntaId = useId()

  const [territorio, setTerritorio] = useState<string>('11')
  const [pregunta, setPregunta] = useState<string>(PREGUNTAS_SUGERIDAS[0].pregunta)
  const [queryState, setQueryState] = useState<{
    loading: boolean
    data: LaboratorioConsultaResponse | null
    error: ApiServiceError | Error | null
  }>({ loading: false, data: null, error: null })

  const [cruces, setCruces] = useState<CrucesResumenResponse | null>(null)
  const [laboral, setLaboral] = useState<LaboralResumenResponse | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    fetchCrucesResumen(controller.signal)
      .then(res => {
        if (!controller.signal.aborted) setCruces(res)
      })
      .catch(() => {
        // Silencioso: la tarjeta complementaria de cruces es informativa.
      })
    fetchLaboralResumen(2025, undefined, controller.signal)
      .then(res => {
        if (!controller.signal.aborted && res.disponible) setLaboral(res)
      })
      .catch(() => {
        // Silencioso si el corte laboral aún no está publicado.
      })
    return () => controller.abort()
  }, [])

  const runConsulta = useCallback(async (q: string, terr: string) => {
    const cleanQ = q.trim()
    if (!cleanQ) return
    setQueryState({ loading: true, data: null, error: null })
    try {
      const data = await consultarLaboratorio(cleanQ, terr)
      setQueryState({ loading: false, data, error: null })
    } catch (err) {
      setQueryState({
        loading: false,
        data: null,
        error: err instanceof Error ? err : new Error('No se pudo ejecutar la consulta en el laboratorio.'),
      })
    }
  }, [])

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    runConsulta(pregunta, territorio)
  }

  function handleSelectSuggestion(item: (typeof PREGUNTAS_SUGERIDAS)[number]) {
    setTerritorio(item.territorio)
    setPregunta(item.pregunta)
    runConsulta(item.pregunta, item.territorio)
  }

  function handleDownloadMd() {
    if (!queryState.data) return
    const md = buildDossierMarkdown(queryState.data)
    triggerFileDownload(
      `dossier-${queryState.data.territorio}-${queryState.data.id_consulta}.md`,
      md,
      'text/markdown;charset=utf-8',
    )
  }

  function handleDownloadHtml() {
    if (!queryState.data) return
    const html = buildDossierHtml(queryState.data)
    triggerFileDownload(
      `dossier-${queryState.data.territorio}-${queryState.data.id_consulta}.html`,
      html,
      'text/html;charset=utf-8',
    )
  }

  const res = queryState.data

  return (
    <div className="fase2-page">
      <section className="intro pol-intro">
        <div>
          <p className="eyebrow">Observatorio territorial · Motor determinista de solo lectura</p>
          <h1>Laboratorio de Investigación y Dossiers</h1>
          <p className="lede">
            Formula preguntas en lenguaje natural sobre las bases verificadas de Chile Territorial y obtén un dossier
            auditable de 10 pasos con fuentes oficiales, evidencia favorable, hipótesis alternativas y exportación reproducible.
          </p>
        </div>
        <span className="status-badge is-official">Solo lectura · Sin IA de pago</span>
      </section>

      <div className="brecha-box" role="note" aria-label="Garantía de solo lectura y gobernanza">
        <strong>Garantía de gobernanza y solo lectura:</strong>
        <p>
          Este laboratorio consulta únicamente cortes publicados de <strong>solo lectura</strong> (BCCh, DIPRES, SINIM e INE).
          No utiliza servicios de inteligencia artificial de pago, no envía datos a terceros y jamás altera observaciones oficiales.
        </p>
      </div>

      {/* Formulario de consulta + 4 preguntas sugeridas */}
      <section className="panel axis-main" aria-labelledby="lab-form-titulo">
        <h2 id="lab-form-titulo">Consulta verificada sobre cortes oficiales</h2>

        <form className="lab-form" onSubmit={handleSubmit}>
          <div className="lab-form-row">
            <label className="field lab-territory-field" htmlFor={territorioId}>
              Territorio de análisis
              <select
                id={territorioId}
                value={territorio}
                onChange={event => setTerritorio(event.target.value)}
              >
                <option value="11">11 · Aysén del General Carlos Ibáñez del Campo</option>
                <option value="CL">CL · Chile (Total Nacional / 16 regiones)</option>
                {REGIONES_CHILE.filter(r => r.codigo !== '11').map(reg => (
                  <option key={reg.codigo} value={reg.codigo}>
                    {reg.codigo} · {reg.nombre}
                  </option>
                ))}
              </select>
            </label>

            <label className="field lab-question-field" htmlFor={preguntaId}>
              Pregunta de investigación (lenguaje natural)
              <textarea
                id={preguntaId}
                rows={3}
                value={pregunta}
                placeholder="Ej. ¿Qué peso tiene la Administración Pública y la Pesca en la estructura productiva de Aysén?"
                onChange={event => setPregunta(event.target.value)}
              />
            </label>
          </div>

          <div className="lab-form-actions">
            <button
              type="submit"
              className="primary"
              disabled={queryState.loading || !pregunta.trim()}
            >
              {queryState.loading ? 'Analizando cortes oficiales…' : 'Generar dossier verificado'}
            </button>
            {res && (
              <>
                <button type="button" className="secondary-btn" onClick={handleDownloadMd}>
                  ↓ Descargar Dossier (.md)
                </button>
                <button type="button" className="secondary-btn" onClick={handleDownloadHtml}>
                  ↓ Exportar Dossier (.html)
                </button>
              </>
            )}
          </div>
        </form>

        <div className="lab-suggestions" aria-label="Preguntas sugeridas de un clic">
          <p className="kpi-label">Preguntas sugeridas de un clic</p>
          <div className="lab-suggestion-grid">
            {PREGUNTAS_SUGERIDAS.map(item => (
              <button
                key={item.id}
                type="button"
                className="suggestion-card"
                disabled={queryState.loading}
                onClick={() => handleSelectSuggestion(item)}
              >
                <strong>{item.etiqueta}</strong>
                <span>{item.pregunta}</span>
              </button>
            ))}
          </div>
        </div>
      </section>

      {/* Estado de carga o error */}
      {queryState.loading && (
        <section className="panel axis-main">
          <div className="pol-loading" role="status" aria-live="polite">
            <span className="pol-spinner" aria-hidden="true" />
            <div className="pol-skeleton-lines">
              <p className="pol-loading-label">
                Ejecutando protocolo transparente de 10 pasos sobre las bases verificadas de solo lectura…
              </p>
              <div className="skeleton-bar wide" />
              <div className="skeleton-bar medium" />
              <div className="skeleton-bar short" />
            </div>
          </div>
        </section>
      )}

      {queryState.error && (
        <section className="panel axis-main">
          <div className="service-error-box" role="alert">
            <p className="error">{queryState.error.message}</p>
            <p className="subtle">
              Verifica que el endpoint <code className="mono">POST /api/v1/laboratorio/consultar</code> esté activo en el servidor local.
            </p>
            <button type="button" className="secondary-btn" onClick={() => runConsulta(pregunta, territorio)}>
              Reintentar consulta
            </button>
          </div>
        </section>
      )}

      {/* Renderizado del protocolo transparente de 10 pasos */}
      {res && (
        <article className="panel axis-main dossier-article" aria-labelledby="dossier-titulo">
          <div className="axis-main-top">
            <div>
              <p className="eyebrow">
                Protocolo transparente de 10 pasos · ID <code className="mono">{res.id_consulta}</code>
              </p>
              <h2 id="dossier-titulo">Dossier · {res.territorio_nombre} ({res.territorio})</h2>
              <p className="subtle">
                Generado: {fmtTimestamp(res.generado_en)} · {res.motor}
              </p>
            </div>
            <div className="fase2-toolbar">
              <button type="button" className="primary" onClick={handleDownloadMd}>
                <span aria-hidden="true">↓</span> Descargar Dossier (.md)
              </button>
              <button type="button" className="secondary-btn" onClick={handleDownloadHtml}>
                Exportar Dossier (.html)
              </button>
            </div>
          </div>

          <ol className="protocol-list">
            <li className="protocol-step">
              <div className="protocol-step-head">
                <span className="step-num">Paso 1</span>
                <h3>Pregunta formulada y alcance territorial</h3>
              </div>
              <p className="dossier-question">«{res.pregunta}»</p>
              <p className="subtle">
                Territorio seleccionado: <strong>{res.territorio_nombre}</strong> (<code className="mono">{res.territorio}</code>).
              </p>
            </li>

            <li className="protocol-step">
              <div className="protocol-step-head">
                <span className="step-num">Paso 2</span>
                <h3>Fuentes oficiales verificadas</h3>
              </div>
              {res.fuentes_verificadas.length > 0 ? (
                <ul className="dossier-list">
                  {res.fuentes_verificadas.map((f, idx) => (
                    <li key={`${f.institucion}-${idx}`}>
                      <strong>{f.institucion}</strong>
                      {f.sistema ? ` · ${f.sistema}` : ''}
                      {f.corte ? ` · Corte: ${f.corte}` : ''}
                      {f.endpoint ? <> · <code className="mono">{f.endpoint}</code></> : null}
                      {f.series && f.series.length > 0 && (
                        <div className="subtle mono">Series: {f.series.slice(0, 6).join(' · ')}{f.series.length > 6 ? ` (+${f.series.length - 6})` : ''}</div>
                      )}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="subtle">Bases publicadas verificadas de Chile Territorial (BCCh, DIPRES, SINIM e INE).</p>
              )}
            </li>

            <li className="protocol-step">
              <div className="protocol-step-head">
                <span className="step-num">Paso 3</span>
                <h3>Hipótesis y método aplicado</h3>
              </div>
              <p>{res.hipotesis_y_metodo}</p>
            </li>

            <li className="protocol-step">
              <div className="protocol-step-head">
                <span className="step-num">Paso 4</span>
                <h3>Métricas reproducibles</h3>
              </div>
              {res.metricas_reproducibles.length > 0 ? (
                <div className="pol-kpi-grid is-three">
                  {res.metricas_reproducibles.map((m, idx) => (
                    <div key={`${m.nombre}-${idx}`} className="pol-kpi-card">
                      <span className="kpi-label">{m.nombre}</span>
                      <strong className="pol-kpi-num">
                        {m.valor}{m.unidad ? ` ${m.unidad}` : ''}
                      </strong>
                      <span className="kpi-meta">
                        {[m.periodo, m.fuente, m.serie].filter(Boolean).join(' · ') || 'Dato verificado'}
                      </span>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="subtle">No se reportaron métricas escalares adicionales para esta consulta.</p>
              )}
            </li>

            <li className="protocol-step">
              <div className="protocol-step-head">
                <span className="step-num">Paso 5</span>
                <h3>Tabla de evidencia verificada</h3>
              </div>
              {res.tabla_evidencia && res.tabla_evidencia.columnas.length > 0 ? (
                <div className="table-scroll" tabIndex={0} role="region" aria-label={res.tabla_evidencia.titulo || 'Tabla de evidencia del dossier'}>
                  <table className="pol-table">
                    {res.tabla_evidencia.titulo && <caption className="sr-only">{res.tabla_evidencia.titulo}</caption>}
                    <thead>
                      <tr>
                        {res.tabla_evidencia.columnas.map((col, idx) => (
                          <th key={`${col}-${idx}`} scope="col">{col}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {res.tabla_evidencia.filas.map((row, rIdx) => (
                        <tr key={rIdx}>
                          {row.map((cell, cIdx) => (
                            cIdx === 0 ? <th key={cIdx} scope="row">{cell}</th> : <td key={cIdx}>{cell}</td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="subtle">Sin tabla adjunta para esta consulta.</p>
              )}
            </li>

            <li className="protocol-step">
              <div className="protocol-step-head">
                <span className="step-num">Paso 6</span>
                <h3>Evidencia favorable y hallazgos observados</h3>
              </div>
              {res.evidencia_favorable.length > 0 ? (
                <ul className="dossier-list">
                  {res.evidencia_favorable.map((item, idx) => <li key={idx}>{item}</li>)}
                </ul>
              ) : (
                <p className="subtle">Los hallazgos cuantitativos figuran en los pasos 4 y 5.</p>
              )}
            </li>

            <li className="protocol-step">
              <div className="protocol-step-head">
                <span className="step-num">Paso 7</span>
                <h3>Hipótesis alternativas y evidencia contraria</h3>
              </div>
              {res.hipotesis_alternativas.length > 0 ? (
                <ul className="dossier-list">
                  {res.hipotesis_alternativas.map((item, idx) => <li key={idx}>{item}</li>)}
                </ul>
              ) : (
                <p className="subtle">
                  Toda lectura sectorial o fiscal debe contrastarse con variación de precios relativos, escala demográfica y cobertura de registros.
                </p>
              )}
            </li>

            <li className="protocol-step">
              <div className="protocol-step-head">
                <span className="step-num">Paso 8</span>
                <h3>Interpretación sobria</h3>
              </div>
              <p>{res.interpretacion}</p>
            </li>

            <li className="protocol-step">
              <div className="protocol-step-head">
                <span className="step-num">Paso 9</span>
                <h3>Limitaciones metodológicas</h3>
              </div>
              {res.limitaciones_metodologicas.length > 0 ? (
                <ul className="dossier-list">
                  {res.limitaciones_metodologicas.map((item, idx) => <li key={idx}>{item}</li>)}
                </ul>
              ) : (
                <p className="subtle">
                  Las relaciones descriptivas observadas no acreditan causalidad sin diseño contrafactual. El PIB regional jamás se imputa a comunas.
                </p>
              )}
            </li>

            <li className="protocol-step">
              <div className="protocol-step-head">
                <span className="step-num">Paso 10</span>
                <h3>Archivo y trazabilidad reproducible</h3>
              </div>
              <p>
                Puedes archivar o compartir este dossier completo en formato Markdown (<code className="mono">.md</code>) o documento HTML autónomo (<code className="mono">.html</code>) preservando el identificador de consulta, fecha y fuentes oficiales.
              </p>
              <div className="lab-form-actions">
                <button type="button" className="primary" onClick={handleDownloadMd}>
                  <span aria-hidden="true">↓</span> Descargar Dossier (.md)
                </button>
                <button type="button" className="secondary-btn" onClick={handleDownloadHtml}>
                  Exportar Dossier (.html)
                </button>
              </div>
            </li>
          </ol>

          <footer className="source-footer" aria-label="Pie de fuente del laboratorio">
            <div className="source-footer-row">
              <span><strong>Fuente:</strong> {res.fuente_trazabilidad.institucion}</span>
              <span><strong>Endpoint:</strong> <code className="mono">POST /api/v1/laboratorio/consultar</code></span>
            </div>
            <div className="source-footer-row">
              <span><strong>Modo:</strong> Solo lectura ({res.solo_lectura ? 'verificado' : 'revisar'})</span>
              <span><strong>Generado:</strong> {fmtTimestamp(res.generado_en)}</span>
            </div>
          </footer>
        </article>
      )}

      {/* Matriz de Dependencia Estatal (3 planos independientes) + Mercado Laboral y SII */}
      {cruces && cruces.dependencia_estatal && (() => {
        const dep = cruces.dependencia_estatal as Record<string, Record<string, unknown>>
        const adm = dep.actividad_economica_administracion_publica ?? {}
        const gasto = dep.gasto_publico_presupuestario ?? {}
        const emp = dep.empleo_publico ?? {}
        const eneAy = (emp.ine_ene_aysen ?? {}) as Record<string, unknown>
        const siiAy = (emp.sii_aysen_rubro_o ?? {}) as Record<string, unknown>
        const sinimMun = (gasto.sinim_municipal ?? {}) as Record<string, unknown>
        const fmtN = (v: unknown, dec = 1) => {
          const n = Number(v)
          return Number.isFinite(n)
            ? n.toLocaleString('es-CL', { minimumFractionDigits: dec, maximumFractionDigits: dec })
            : 'Sin dato'
        }
        return (
          <section className="panel" aria-label="Matriz de Dependencia Estatal de Aysén">
            <div className="panel-head">
              <div>
                <p className="eyebrow">Matriz de Dependencia Estatal · 3 planos no sumables (Aysén)</p>
                <h2>Presencia del Estado: PIB, Presupuesto y Empleo Formal</h2>
              </div>
              <span className="status-badge is-official">BCCh · DIPRES · SINIM · INE · SII</span>
            </div>
            <div className="wallets-grid">
              <article className="wallet-card">
                <div className="wallet-head">
                  <span className="wallet-num">Plano (a)</span>
                  <span className="status-badge is-official">BCCh CCNN {String(adm.anio ?? 2025)}</span>
                </div>
                <h4>Actividad Administración Pública</h4>
                <p className="kpi-value">{fmtN(adm.participacion_pib_nominal_pct, 2)}%</p>
                <p className="subtle">
                  del PIB nominal regional (${fmtN(adm.valor_millones_clp, 1)} MM). Mide valor agregado de la rama en Cuentas Nacionales; no equivale a gasto fiscal ni empleo.
                </p>
              </article>

              <article className="wallet-card">
                <div className="wallet-head">
                  <span className="wallet-num">Plano (b)</span>
                  <span className="status-badge is-official">DIPRES + SINIM {String(gasto.anio ?? 2025)}</span>
                </div>
                <h4>Gasto Público Presupuestario</h4>
                <p className="kpi-value">${fmtN(gasto.gasto_directo_gobierno_central_millones, 0)} MM</p>
                <p className="subtle">
                  Gobierno Central en Aysén ({fmtN(gasto.ratio_gasto_directo_sobre_pib_nominal_pct, 1)}% ref. PIB nominal) + GORE ${fmtN(gasto.financiamiento_gore_p31_millones, 0)} MM
                  {sinimMun.cargado ? ` + ${String(sinimMun.comunas_cargadas)}/10 municipios SINIM ($${fmtN(sinimMun.total_gasto_devengado_millones, 0)} MM).` : '.'}
                </p>
              </article>

              <article className="wallet-card">
                <div className="wallet-head">
                  <span className="wallet-num">Plano (c)</span>
                  <span className="status-badge is-official">
                    {emp.disponible ? `INE ENE + SII ${String(emp.anio_sii ?? 2025)}` : 'Pendiente'}
                  </span>
                </div>
                <h4>Empleo, Productividad y Masa Salarial</h4>
                {emp.disponible ? (
                  <>
                    <p className="kpi-value">{fmtN(siiAy.participacion_rubro_o_trabajadores_pct, 2)}% / {fmtN(siiAy.participacion_rubro_o_masa_salarial_pct, 2)}%</p>
                    <p className="subtle">
                      <strong>SII Rubro O (Adm. Pública):</strong> {fmtN(siiAy.participacion_rubro_o_trabajadores_pct, 2)}% de los {fmtN(siiAy.trabajadores_ponderados_totales_aysen, 0)} trabajadores dependientes ponderados y {fmtN(siiAy.participacion_rubro_o_masa_salarial_pct, 2)}% de la masa salarial formal en UF (domicilio tributario en Aysén).{' '}
                      <strong>INE ENE ({String(emp.anio_ene ?? 2025)}):</strong> {fmtN(eneAy.ocupados_personas, 0)} ocupados, {fmtN(eneAy.tasa_desocupacion_pct, 2)}% desocupación y productividad real ${fmtN(eneAy.productividad_laboral_real_clp, 0)} CLP/ocup. (#{String(eneAy.ranking_productividad_regional ?? '—')} en Chile).
                    </p>
                  </>
                ) : (
                  <p className="subtle">{String(emp.motivo ?? 'Sin dato laboral disponible.')}</p>
                )}
              </article>
            </div>
            {laboral && laboral.sii_comunas_aysen.length > 0 && (
              <details className="bcch-explorer" style={{ marginTop: '1rem' }}>
                <summary>
                  <span>
                    <strong>Tejido empresarial y empleo formal SII — {laboral.sii_comunas_aysen.length} comunas de Aysén ({laboral.anio_sii})</strong>
                    <small className="subtle"> Empresas, ventas (UF), trabajadores dependientes ponderados y masa salarial formal por domicilio tributario del empleador (SII).</small>
                  </span>
                </summary>
                <div className="explorer-body">
                  <div className="table-wrap">
                    <table>
                      <thead>
                        <tr>
                          <th>Comuna (CUT)</th>
                          <th>Empresas</th>
                          <th>Ventas anuales (UF)</th>
                          <th>Trab. dependientes pond.</th>
                          <th>Masa salarial formal (UF)</th>
                          <th>Honorarios (pers.)</th>
                        </tr>
                      </thead>
                      <tbody>
                        {laboral.sii_comunas_aysen.map(c => (
                          <tr key={c.cut}>
                            <th scope="row">{c.comuna} <span className="mono subtle">({c.cut})</span></th>
                            <td>{c.empresas !== null ? c.empresas.toLocaleString('es-CL') : 'Sin dato'}</td>
                            <td>{c.ventas_uf ? fmtN(c.ventas_uf, 0) : 'Secreto est. (*)'}</td>
                            <td>{c.trabajadores_ponderados ? fmtN(c.trabajadores_ponderados, 1) : 'Sin dato'}</td>
                            <td>{c.renta_neta_uf ? fmtN(c.renta_neta_uf, 0) : 'Secreto est. (*)'}</td>
                            <td>{c.honorarios_trabajadores !== null ? c.honorarios_trabajadores.toLocaleString('es-CL') : 'Sin dato'}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  {laboral.nota_metodologica_separacion && (
                    <p className="subtle" style={{ marginTop: '0.75rem' }}>{laboral.nota_metodologica_separacion}</p>
                  )}
                </div>
              </details>
            )}
          </section>
        )
      })()}

      {/* Bloque informativo de cruces analíticos si /api/v1/cruces/resumen está disponible */}
      {cruces && cruces.cruces.length > 0 && (
        <details className="panel bcch-explorer">
          <summary>
            <span>
              <strong>Catálogo de cruces analíticos verificados ({cruces.cruces.length} cruces)</strong>
              <small className="subtle">Referencia rápida desde <code className="mono">GET /api/v1/cruces/resumen</code> sobre estado de datos disponibles.</small>
            </span>
          </summary>
          <div className="explorer-body">
            <div className="wallets-grid">
              {cruces.cruces.map(c => (
                <div key={c.id} className="wallet-card">
                  <div className="wallet-head">
                    <span className="wallet-num">{c.id}</span>
                    <span className="status-badge is-official">{c.estado}</span>
                  </div>
                  <h4>{c.titulo}</h4>
                  <p className="subtle">{c.descripcion}</p>
                  {c.hallazgo_principal && <p className="subtle"><strong>Hallazgo:</strong> {c.hallazgo_principal}</p>}
                  {c.limitacion && <p className="subtle"><strong>Límite:</strong> {c.limitacion}</p>}
                </div>
              ))}
            </div>
          </div>
        </details>
      )}
    </div>
  )
}
