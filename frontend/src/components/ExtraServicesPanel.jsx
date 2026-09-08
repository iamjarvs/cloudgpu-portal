import { useState } from 'react'
import { api } from '../api'
import Icon from './Icon'
import NetrisServicesMenu from './NetrisServicesMenu'
import { EXTRA_KINDS, EXTRA_META, summarize } from '../netrisExtras'

const STATE_PILL = {
  pending: { cls: 'pill-amber', label: 'Creating…' },
  created: { cls: 'pill-green', label: 'Active' },
  failed: { cls: 'pill-red', label: 'Failed' },
}

export default function ExtraServicesPanel({ env, onChange }) {
  const [busyId, setBusyId] = useState(null)
  const items = EXTRA_KINDS.flatMap((kind) => (env.extras?.[kind] || []).map((item) => ({ kind, ...item })))

  async function handleAdd(kind, config) {
    const updated = await api.addExtra(env.uuid, kind, config)
    onChange(updated)
  }

  async function handleDelete(kind, localId) {
    setBusyId(localId)
    try {
      const updated = await api.deleteExtra(env.uuid, kind, localId)
      onChange(updated)
    } finally {
      setBusyId(null)
    }
  }

  return (
    <section className="panel">
      <div className="panel-header-row">
        <h2>Netris Services</h2>
        <NetrisServicesMenu envName={env.name} onAdd={handleAdd} />
      </div>
      {items.length === 0 ? (
        <p className="muted small">
          No NAT rules, ACLs, V-Nets, or load balancers attached to this environment yet.
        </p>
      ) : (
        <ul className="extra-service-list">
          {items.map((item) => {
            const pill = STATE_PILL[item.state] || STATE_PILL.pending
            return (
              <li key={`${item.kind}-${item.local_id}`} className="extra-service-row">
                <span className="extra-service-icon">
                  <Icon name={EXTRA_META[item.kind].icon} size={16} />
                </span>
                <div className="extra-service-info">
                  <div className="extra-service-name">
                    <span className="extra-service-kind">{EXTRA_META[item.kind].short}</span>
                    {item.config?.name}
                  </div>
                  <div className="muted small mono">{summarize(item.kind, item.config)}</div>
                  {item.state === 'failed' && item.error && <div className="form-error">{item.error}</div>}
                </div>
                <span className={`status-pill ${pill.cls}`} style={{ margin: 0 }}>
                  {pill.label}
                </span>
                <button
                  type="button"
                  className="btn-ghost"
                  disabled={busyId === item.local_id}
                  onClick={() => handleDelete(item.kind, item.local_id)}
                >
                  <Icon name="x" size={14} />
                </button>
              </li>
            )
          })}
        </ul>
      )}
    </section>
  )
}
