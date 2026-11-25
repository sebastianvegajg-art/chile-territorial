import { useEffect, useId, useRef, useState } from 'react'
import type { ReactNode } from 'react'

interface InfoPopoverProps {
  /** Etiqueta accesible para lectores de pantalla y tooltip nativo */
  label: string
  /** Título breve dentro del cuadro informativo */
  title?: string
  /** Contenido técnico u opcional que se muestra solo al pulsar (i) */
  children: ReactNode
  /** 'corner' lo ubica en la esquina superior derecha de una tarjeta con position: relative */
  placement?: 'corner' | 'inline'
  /** Alineación del panel emergente */
  align?: 'right' | 'left'
}

export function InfoPopover({
  label,
  title,
  children,
  placement = 'corner',
  align = 'right',
}: InfoPopoverProps) {
  const [open, setOpen] = useState(false)
  const panelId = useId()
  const wrapRef = useRef<HTMLSpanElement>(null)

  useEffect(() => {
    if (!open) return
    const onPointerDown = (event: MouseEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(event.target as Node)) {
        setOpen(false)
      }
    }
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpen(false)
    }
    document.addEventListener('mousedown', onPointerDown)
    window.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('mousedown', onPointerDown)
      window.removeEventListener('keydown', onKeyDown)
    }
  }, [open])

  return (
    <span
      ref={wrapRef}
      className={`info-pop-wrap is-${placement}`}
    >
      <button
        type="button"
        className={`info-pop-btn${open ? ' is-open' : ''}`}
        aria-label={label}
        title={label}
        aria-expanded={open}
        aria-controls={panelId}
        onClick={event => {
          event.stopPropagation()
          setOpen(prev => !prev)
        }}
      >
        <span aria-hidden="true">i</span>
      </button>

      {open && (
        <div
          id={panelId}
          role="dialog"
          aria-label={title || label}
          className={`info-pop-card is-align-${align}`}
          onClick={event => event.stopPropagation()}
        >
          <div className="info-pop-head">
            {title && <strong>{title}</strong>}
            <button
              type="button"
              className="info-pop-close"
              aria-label="Cerrar información"
              onClick={() => setOpen(false)}
            >
              ✕
            </button>
          </div>
          <div className="info-pop-body">{children}</div>
        </div>
      )}
    </span>
  )
}
