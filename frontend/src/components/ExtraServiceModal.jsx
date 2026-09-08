import { useState } from 'react'
import Modal from './Modal'
import { EXTRA_META, FIELD_SPECS, defaultConfig } from '../netrisExtras'

export default function ExtraServiceModal({ kind, envName, initialConfig, onSave, onClose }) {
  const [config, setConfig] = useState(() => ({ ...defaultConfig(kind, envName), ...(initialConfig || {}) }))
  const meta = EXTRA_META[kind]

  function setField(key, value) {
    setConfig((prev) => ({ ...prev, [key]: value }))
  }

  function handleSubmit(e) {
    // React re-bubbles portaled events up the *component* tree, not the DOM
    // tree (see Modal.jsx) — without stopPropagation this submit would also
    // reach the page's own <form onSubmit> (e.g. New Environment's "deploy"
    // handler) and fire it with a stale pre-update extras list.
    e.preventDefault()
    e.stopPropagation()
    onSave(config)
  }

  return (
    <Modal title={`${initialConfig ? 'Edit' : 'Add'} ${meta.label}`} onClose={onClose}>
      <form onSubmit={handleSubmit} className="extra-service-form">
        <p className="hint" style={{ margin: '0 0 0.9rem' }}>
          Prepopulated with sensible defaults — edit anything before saving. This is sent to Netris as a real{' '}
          {meta.short} object.
        </p>
        {FIELD_SPECS[kind].map((field) => (
          <div key={field.key} className="extra-field-row">
            <label htmlFor={`extra-${kind}-${field.key}`}>{field.label}</label>
            {field.type === 'select' ? (
              <select
                id={`extra-${kind}-${field.key}`}
                value={config[field.key] ?? ''}
                onChange={(e) => setField(field.key, e.target.value)}
              >
                {field.options.map((opt) => (
                  <option key={opt} value={opt}>
                    {opt}
                  </option>
                ))}
              </select>
            ) : (
              <input
                id={`extra-${kind}-${field.key}`}
                type={field.type === 'number' ? 'number' : 'text'}
                value={config[field.key] ?? ''}
                onChange={(e) =>
                  setField(field.key, field.type === 'number' ? (e.target.value === '' ? null : Number(e.target.value)) : e.target.value)
                }
              />
            )}
          </div>
        ))}
        <div className="modal-actions">
          <button type="button" className="btn-ghost" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="btn-primary" style={{ marginTop: 0 }}>
            {initialConfig ? 'Save' : `Add ${meta.short}`}
          </button>
        </div>
      </form>
    </Modal>
  )
}
