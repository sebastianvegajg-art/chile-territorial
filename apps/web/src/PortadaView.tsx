import { useCallback, useEffect, useRef, useState } from 'react'

type ViewBox = [number, number, number, number]

interface RegionGeometry {
  cod: string
  nombre: string
  nombreOficial: string
  d: string
  bbox: [number, number, number, number]
  label: [number, number]
}

interface ChileMapPayload {
  meta: {
    fuente: string
    url: string
    proyeccion: string
    nota: string
  }
  viewBoxes: {
    chile: ViewBox
    aysen: ViewBox
  }
  aysen: {
    cod: string
    titulo: string
    capital: string
    division: string
    coyhaique: [number, number]
    bbox: [number, number, number, number]
  }
  regiones: RegionGeometry[]
}

interface PortadaViewProps {
  onEnter: () => void
}

type CyclePhase = 'national' | 'zooming_in' | 'card' | 'zooming_out'

// Paleta suave alternada para que se distingan las 16 regiones en la vista nacional
const SOFT_REGION_TONES = ['#d8e4dd', '#cad9d0', '#e1eae5', '#cfdcd4']

const NATIONAL_HOLD_MS = 2000
const ZOOM_IN_MS = 1650
const CARD_HOLD_MS = 5000
const ZOOM_OUT_MS = 1550

function easeInOutCubic(t: number): number {
  return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2
}

function lerpViewBox(from: ViewBox, to: ViewBox, t: number): ViewBox {
  const e = easeInOutCubic(Math.max(0, Math.min(1, t)))
  return [
    from[0] + (to[0] - from[0]) * e,
    from[1] + (to[1] - from[1]) * e,
    from[2] + (to[2] - from[2]) * e,
    from[3] + (to[3] - from[3]) * e,
  ]
}

function formatViewBox(vb: ViewBox): string {
  return `${vb[0].toFixed(1)} ${vb[1].toFixed(1)} ${vb[2].toFixed(1)} ${vb[3].toFixed(1)}`
}

export function PortadaView({ onEnter }: PortadaViewProps) {
  const [mapData, setMapData] = useState<ChileMapPayload | null>(null)
  const [mapError, setMapError] = useState(false)

  const [reducedMotion, setReducedMotion] = useState<boolean>(() => {
    if (typeof window === 'undefined' || !window.matchMedia) return false
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches
  })

  const [paused, setPaused] = useState<boolean>(() => {
    if (typeof window === 'undefined' || !window.matchMedia) return false
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches
  })

  const [viewBox, setViewBox] = useState<ViewBox>([-213.0, -1.6, 762.3, 1003.0])
  const [aysenHighlighted, setAysenHighlighted] = useState<boolean>(() => {
    if (typeof window === 'undefined' || !window.matchMedia) return false
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches
  })
  const [isZoomedAysen, setIsZoomedAysen] = useState(false)
  const [showCard, setShowCard] = useState(false)
  const [lockedOnAysen, setLockedOnAysen] = useState(false)
  const [cycleToken, setCycleToken] = useState(0)

  const viewBoxRef = useRef<ViewBox>(viewBox)
  viewBoxRef.current = viewBox

  const rafRef = useRef<number | null>(null)
  const timerRef = useRef<number | null>(null)

  const clearScheduled = useCallback(() => {
    if (rafRef.current !== null) {
      cancelAnimationFrame(rafRef.current)
      rafRef.current = null
    }
    if (timerRef.current !== null) {
      window.clearTimeout(timerRef.current)
      timerRef.current = null
    }
  }, [])

  // Detecta cambios en la preferencia de movimiento reducido del dispositivo
  useEffect(() => {
    if (typeof window === 'undefined' || !window.matchMedia) return
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)')
    const onChange = (event: MediaQueryListEvent) => {
      setReducedMotion(event.matches)
      if (event.matches) {
        clearScheduled()
        setPaused(true)
        setAysenHighlighted(true)
      }
    }
    mq.addEventListener('change', onChange)
    return () => mq.removeEventListener('change', onChange)
  }, [clearScheduled])

  // Carga asíncrona del mapa vectorial oficial BCN sin bloquear nunca el texto ni el botón
  useEffect(() => {
    const controller = new AbortController()
    fetch('/data/chile-regiones-bcn.json', { signal: controller.signal })
      .then(res => {
        if (!res.ok) throw new Error('No se pudo cargar la cartografía')
        return res.json() as Promise<ChileMapPayload>
      })
      .then(payload => {
        setMapData(payload)
        setViewBox(payload.viewBoxes.chile)
        viewBoxRef.current = payload.viewBoxes.chile
      })
      .catch(err => {
        if (!controller.signal.aborted) {
          console.error(err)
          setMapError(true)
        }
      })
    return () => controller.abort()
  }, [])

  const animateViewBox = useCallback(
    (target: ViewBox, durationMs: number, onComplete?: () => void) => {
      clearScheduled()
      if (reducedMotion || durationMs <= 0) {
        setViewBox(target)
        viewBoxRef.current = target
        onComplete?.()
        return
      }
      const startVb = viewBoxRef.current
      const startedAt = performance.now()

      const tick = (now: number) => {
        const progress = Math.min(1, (now - startedAt) / durationMs)
        const nextVb = lerpViewBox(startVb, target, progress)
        setViewBox(nextVb)
        viewBoxRef.current = nextVb
        if (progress < 1) {
          rafRef.current = requestAnimationFrame(tick)
        } else {
          rafRef.current = null
          onComplete?.()
        }
      }
      rafRef.current = requestAnimationFrame(tick)
    },
    [clearScheduled, reducedMotion],
  )

  // Ciclo automático: vista nacional (2s) -> resaltar y acercar a Aysén -> ficha (5s) -> alejar a Chile -> repetir
  useEffect(() => {
    if (!mapData || paused || reducedMotion) {
      return
    }

    let cancelled = false
    const { chile, aysen } = mapData.viewBoxes

    const runPhase = (phase: CyclePhase) => {
      if (cancelled) return

      if (phase === 'national') {
        setShowCard(false)
        setIsZoomedAysen(false)
        setAysenHighlighted(false)
        setViewBox(chile)
        viewBoxRef.current = chile
        timerRef.current = window.setTimeout(() => {
          if (!cancelled) runPhase('zooming_in')
        }, NATIONAL_HOLD_MS)
        return
      }

      if (phase === 'zooming_in') {
        setAysenHighlighted(true)
        setIsZoomedAysen(true)
        animateViewBox(aysen, ZOOM_IN_MS, () => {
          if (!cancelled) runPhase('card')
        })
        return
      }

      if (phase === 'card') {
        setShowCard(true)
        timerRef.current = window.setTimeout(() => {
          if (!cancelled) runPhase('zooming_out')
        }, CARD_HOLD_MS)
        return
      }

      if (phase === 'zooming_out') {
        setShowCard(false)
        animateViewBox(chile, ZOOM_OUT_MS, () => {
          if (!cancelled) {
            setIsZoomedAysen(false)
            setAysenHighlighted(false)
            runPhase('national')
          }
        })
      }
    }

    // Si el usuario reanuda desde la ficha abierta, continúa suavemente saliendo a Chile y repitiendo
    if (isZoomedAysen) {
      runPhase('zooming_out')
    } else {
      runPhase('national')
    }

    return () => {
      cancelled = true
      clearScheduled()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mapData, paused, reducedMotion, cycleToken])

  // Si se activa movimiento reducido, deja el mapa estático con Aysén destacada
  useEffect(() => {
    if (!mapData || !reducedMotion) return
    clearScheduled()
    setPaused(true)
    setAysenHighlighted(true)
    if (!lockedOnAysen) {
      setViewBox(mapData.viewBoxes.chile)
      viewBoxRef.current = mapData.viewBoxes.chile
      setIsZoomedAysen(false)
      setShowCard(false)
    }
  }, [mapData, reducedMotion, lockedOnAysen, clearScheduled])

  // Interacción: pulsar o seleccionar Aysén con teclado detiene el ciclo y mantiene la ficha abierta
  const handleSelectAysen = useCallback(() => {
    if (!mapData) return
    clearScheduled()
    setPaused(true)
    setLockedOnAysen(true)
    setAysenHighlighted(true)
    setIsZoomedAysen(true)
    const target = mapData.viewBoxes.aysen
    const cur = viewBoxRef.current
    const alreadyClose =
      Math.abs(cur[0] - target[0]) < 1 &&
      Math.abs(cur[1] - target[1]) < 1 &&
      Math.abs(cur[2] - target[2]) < 1
    if (alreadyClose || reducedMotion) {
      setViewBox(target)
      viewBoxRef.current = target
      setShowCard(true)
      return
    }
    animateViewBox(target, 950, () => {
      setShowCard(true)
    })
  }, [animateViewBox, clearScheduled, mapData, reducedMotion])

  const handleViewChile = useCallback(() => {
    if (!mapData) return
    clearScheduled()
    setPaused(true)
    setLockedOnAysen(false)
    setShowCard(false)
    setIsZoomedAysen(false)
    setAysenHighlighted(reducedMotion)
    animateViewBox(mapData.viewBoxes.chile, reducedMotion ? 0 : 950)
  }, [animateViewBox, clearScheduled, mapData, reducedMotion])

  const handleTogglePause = useCallback(() => {
    if (reducedMotion) return
    if (paused) {
      setLockedOnAysen(false)
      setPaused(false)
      setCycleToken(v => v + 1)
    } else {
      clearScheduled()
      setPaused(true)
    }
  }, [clearScheduled, paused, reducedMotion])

  const regionFill = (reg: RegionGeometry, idx: number): string => {
    if (reg.cod === '11') {
      return aysenHighlighted ? '#08785e' : '#cad9d0'
    }
    if (reg.cod === '00') {
      return isZoomedAysen ? '#e5ece9' : '#dde6e1'
    }
    if (isZoomedAysen) {
      return '#dce6e1'
    }
    return SOFT_REGION_TONES[idx % SOFT_REGION_TONES.length]
  }

  return (
    <div className="portada-shell">
      <div className="portada-grid wrap">
        {/* Columna izquierda: presentación breve + CTA inmediato */}
        <section className="portada-copy" aria-labelledby="portada-titulo">
          <div className="portada-brand-lockup">
            <img
              src="/brand/confiasur-logo-dark.png"
              alt="CONFIASUR Consultores"
              className="portada-logo"
              width={214}
              height={42}
            />
          </div>

          <div className="portada-heading-group">
            <p className="portada-kicker">Confía Sur</p>
            <h1 id="portada-titulo" className="portada-title">
              Datos públicos para entender Aysén.
            </h1>
          </div>

          <p className="portada-lede">
            En Confía Sur reunimos y explicamos datos públicos para que cualquier persona pueda entender qué mueve la economía de Aysén, cómo se usan los recursos del Estado y qué cambia en las comunas de la región.
          </p>

          <div className="portada-actions">
            <button type="button" className="portada-cta" onClick={onEnter}>
              Ingresar al observatorio
              <span className="portada-cta-arrow" aria-hidden="true">→</span>
            </button>
          </div>

          <p className="portada-sources-note">
            Observatorio Territorial · Cifras oficiales verificables de BCCh, DIPRES, INE, MOP y BCN.
          </p>
        </section>

        {/* Columna derecha: mapa vectorial interactivo de Chile y Aysén */}
        <section className="portada-map-col" aria-label="Mapa interactivo de Chile y la Región de Aysén">
          <div className="portada-map-stage">
            <div className="portada-map-canvas">
              <div className="portada-map-status" aria-hidden="true">
                <span className={`portada-status-dot${aysenHighlighted ? ' is-aysen' : ''}`} />
                {isZoomedAysen ? 'Región de Aysén' : 'Chile · 16 regiones'}
              </div>

              {!mapData && !mapError && (
                <div className="portada-map-loading" role="status" aria-live="polite">
                  <span className="portada-loading-pulse" aria-hidden="true" />
                  Cargando cartografía oficial…
                </div>
              )}

              {mapError && (
                <div className="portada-map-loading">
                  Mapa temporalmente no disponible. Puedes ingresar al observatorio directamente.
                </div>
              )}

              {mapData && (
                <svg
                  className="portada-svg"
                  viewBox={formatViewBox(viewBox)}
                  preserveAspectRatio="xMidYMid meet"
                  role="img"
                  aria-label="Mapa vectorial oficial de las 16 regiones de Chile destacando la Región de Aysén"
                >
                  <defs>
                    <filter id="aysenGlow" x="-12%" y="-12%" width="124%" height="124%">
                      <feDropShadow dx="0" dy="1.2" stdDeviation="1.6" floodColor="#064536" floodOpacity="0.24" />
                    </filter>
                  </defs>

                  {/* Regiones vecinas y resto de Chile primero */}
                  <g className="portada-regions-layer">
                    {mapData.regiones
                      .filter(r => r.cod !== '11')
                      .map((reg, idx) => (
                        <path
                          key={reg.cod}
                          d={reg.d}
                          fill={regionFill(reg, idx)}
                          stroke={isZoomedAysen ? '#f4f8f6' : '#f8fbf9'}
                          strokeWidth={isZoomedAysen ? 0.85 : 1.05}
                          vectorEffect="non-scaling-stroke"
                          className="portada-region-path"
                        >
                          <title>{reg.nombreOficial}</title>
                        </path>
                      ))}
                  </g>

                  {/* Región de Aysén interactiva (encima para nitidez de borde y foco accesible) */}
                  {mapData.regiones
                    .filter(r => r.cod === '11')
                    .map(aysenReg => (
                      <g
                        key={aysenReg.cod}
                        role="button"
                        tabIndex={0}
                        className={`portada-aysen-hit${aysenHighlighted ? ' is-highlighted' : ''}`}
                        aria-label="Región de Aysén. Capital regional: Coyhaique. 4 provincias y 10 comunas. Selecciona para enfocar Aysén y mantener abierta la ficha."
                        aria-pressed={lockedOnAysen}
                        onClick={handleSelectAysen}
                        onKeyDown={event => {
                          if (event.key === 'Enter' || event.key === ' ') {
                            event.preventDefault()
                            handleSelectAysen()
                          }
                        }}
                      >
                        <path
                          d={aysenReg.d}
                          fill={regionFill(aysenReg, 0)}
                          stroke={aysenHighlighted ? '#054a3a' : '#89a399'}
                          strokeWidth={aysenHighlighted ? 1.5 : 1.05}
                          vectorEffect="non-scaling-stroke"
                          filter={aysenHighlighted ? 'url(#aysenGlow)' : undefined}
                          className="portada-aysen-path"
                        >
                          <title>Región de Aysén · Clic para ver ficha</title>
                        </path>
                      </g>
                    ))}

                  {/* Referencias discretas de regiones vecinas y capital regional durante el acercamiento */}
                  {isZoomedAysen && (
                    <g className="portada-context-labels" pointerEvents="none">
                      <text x={118} y={655} className="portada-neighbor-label">
                        Los Lagos
                      </text>
                      <text x={118} y={832} className="portada-neighbor-label">
                        Magallanes
                      </text>

                      {/* Punto de Coyhaique y línea guía sutil hacia la ficha */}
                      <line
                        x1={mapData.aysen.coyhaique[0]}
                        y1={mapData.aysen.coyhaique[1]}
                        x2={161}
                        y2={mapData.aysen.coyhaique[1]}
                        className={`portada-leader-line${showCard ? ' is-visible' : ''}`}
                        vectorEffect="non-scaling-stroke"
                      />
                      <circle
                        cx={mapData.aysen.coyhaique[0]}
                        cy={mapData.aysen.coyhaique[1]}
                        r={2.1}
                        className="portada-capital-dot"
                      />
                      <circle
                        cx={mapData.aysen.coyhaique[0]}
                        cy={mapData.aysen.coyhaique[1]}
                        r={4.2}
                        className="portada-capital-halo"
                      />
                    </g>
                  )}
                </svg>
              )}

              {/* Ficha de 3 líneas ubicada en el margen libre derecho sin tapar Aysén ni sus islas */}
              <aside
                className={`portada-aysen-card${showCard ? ' is-visible' : ''}`}
                aria-hidden={!showCard}
                aria-label="Ficha de la Región de Aysén"
              >
                <p className="portada-card-title">Región de Aysén</p>
                <p className="portada-card-line">Capital regional: <strong>Coyhaique</strong></p>
                <p className="portada-card-meta">4 provincias · 10 comunas</p>
              </aside>
            </div>

            {/* Controles discretos del mapa */}
            <div className="portada-map-bar">
              <div className="portada-map-controls" role="group" aria-label="Controles del mapa">
                <button
                  type="button"
                  className="portada-ctrl-btn"
                  onClick={handleViewChile}
                  disabled={!mapData}
                >
                  Ver Chile
                </button>
                <button
                  type="button"
                  className="portada-ctrl-btn"
                  onClick={handleTogglePause}
                  aria-pressed={paused}
                  disabled={!mapData || reducedMotion}
                  title={
                    reducedMotion
                      ? 'Animación desactivada por la preferencia de movimiento reducido del dispositivo'
                      : paused
                        ? 'Reanudar secuencia automática del mapa'
                        : 'Pausar secuencia automática del mapa'
                  }
                >
                  {reducedMotion
                    ? 'Mapa estático'
                    : paused
                      ? 'Reanudar animación'
                      : 'Pausar animación'}
                </button>
              </div>
              <span className="portada-map-credit">
                Límites oficiales{' '}
                <a
                  href="https://www.bcn.cl/siit/mapas_vectoriales/"
                  target="_blank"
                  rel="noreferrer"
                >
                  BCN
                </a>
              </span>
            </div>
          </div>
        </section>
      </div>
    </div>
  )
}
