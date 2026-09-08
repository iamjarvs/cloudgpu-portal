import { useEffect } from 'react'
import { createPortal } from 'react-dom'
import Icon from './Icon'

export default function Modal({ title, onClose, children, wide }) {
  useEffect(() => {
    function onKey(e) {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [onClose])

  // Portaled to <body> — this modal's own <form> must never end up nested
  // inside a page-level <form> (e.g. New Environment's), which is invalid
  // HTML and silently breaks submit handling (the click falls through to a
  // native full-page form submission instead of the intercepted onSubmit).
  return createPortal(
    <div className="modal-backdrop" onMouseDown={onClose}>
      <div className={`modal-panel${wide ? ' wide' : ''}`} onMouseDown={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>{title}</h3>
          <button type="button" className="modal-close" onClick={onClose} aria-label="Close">
            <Icon name="x" size={16} />
          </button>
        </div>
        <div className="modal-body">{children}</div>
      </div>
    </div>,
    document.body,
  )
}
