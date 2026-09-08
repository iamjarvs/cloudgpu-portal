import { useEffect, useRef, useState } from 'react'
import Icon from './Icon'
import ExtraServiceModal from './ExtraServiceModal'
import { EXTRA_KINDS, EXTRA_META } from '../netrisExtras'

// "+ Netris service" — the menu of Softgate-backed add-ons (NAT, ACL,
// V-Net, Load Balancer) that can be attached to an environment, either at
// deploy time or later from its detail page. Opens straight into the
// pop-out form for whichever kind is picked.
export default function NetrisServicesMenu({ envName, onAdd }) {
  const [open, setOpen] = useState(false)
  const [activeKind, setActiveKind] = useState(null)
  const ref = useRef(null)

  useEffect(() => {
    if (!open) return
    function onClick(e) {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false)
    }
    document.addEventListener('mousedown', onClick)
    return () => document.removeEventListener('mousedown', onClick)
  }, [open])

  return (
    <div className="netris-services-menu" ref={ref}>
      <button type="button" className="btn-secondary" onClick={() => setOpen((v) => !v)}>
        <Icon name="plus" size={14} /> Netris service
      </button>
      {open && (
        <div className="dropdown services-dropdown">
          {EXTRA_KINDS.map((kind) => (
            <button
              key={kind}
              type="button"
              onClick={() => {
                setActiveKind(kind)
                setOpen(false)
              }}
            >
              <Icon name={EXTRA_META[kind].icon} size={16} />
              {EXTRA_META[kind].label}
            </button>
          ))}
        </div>
      )}
      {activeKind && (
        <ExtraServiceModal
          kind={activeKind}
          envName={envName}
          onClose={() => setActiveKind(null)}
          onSave={(config) => {
            onAdd(activeKind, config)
            setActiveKind(null)
          }}
        />
      )}
    </div>
  )
}
