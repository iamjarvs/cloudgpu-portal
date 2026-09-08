import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import AppShell from '../components/AppShell'
import Icon from '../components/Icon'
import NetrisServicesMenu from '../components/NetrisServicesMenu'
import ExtraServiceModal from '../components/ExtraServiceModal'
import { EXTRA_META, summarize } from '../netrisExtras'

const INCLUDED_GROUPS = [
  {
    title: 'Compute',
    icon: 'cpu',
    items: [
      'Bare-metal GPU servers (HGX, NVLink)',
      'Kubernetes control plane (highly available, 3 nodes)',
      'NVIDIA drivers + CUDA / NCCL runtime',
      'Container runtime (containerd)',
    ],
  },
  {
    title: 'Networking',
    icon: 'network',
    items: [
      'Isolated VPC, created fresh per environment',
      'VLAN segmentation (North-South + OOB Management)',
      'Dedicated subnet allocation',
    ],
  },
  {
    title: 'Security & monitoring',
    icon: 'shield',
    items: [
      'Hard tenant-level network isolation',
      'Node health monitoring agent',
      'Encrypted at-rest storage',
    ],
  },
]

export default function NewEnvironment() {
  const [name, setName] = useState('')
  const [serverCount, setServerCount] = useState(1)
  const [capacity, setCapacity] = useState(null)
  const [error, setError] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  const [extrasList, setExtrasList] = useState([])
  const [editingExtra, setEditingExtra] = useState(null) // { id, kind } | null
  const navigate = useNavigate()

  useEffect(() => {
    api.capacity().then(setCapacity).catch(() => {})
  }, [])

  const maxCount = capacity ? Math.max(1, Math.min(capacity.available_count, capacity.max_per_request)) : 1
  const gpusPerServer = capacity?.gpus_per_server ?? 8
  const totalGpus = serverCount * gpusPerServer

  function addExtra(kind, config) {
    setExtrasList((prev) => [...prev, { id: `${kind}-${Date.now()}`, kind, config }])
  }
  function updateExtra(id, config) {
    setExtrasList((prev) => prev.map((x) => (x.id === id ? { ...x, config } : x)))
  }
  function removeExtra(id) {
    setExtrasList((prev) => prev.filter((x) => x.id !== id))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      const payload = extrasList.map((x) => ({ kind: x.kind, config: x.config }))
      const env = await api.createEnvironment(name.trim(), serverCount, payload)
      navigate(`/environments/${env.uuid}`)
    } catch (err) {
      setError(err.message)
      setSubmitting(false)
    }
  }

  return (
    <AppShell title="New Environment">
      <div className="content-header">
        <p className="content-subtitle">Every environment ships with the same production-ready stack — you only choose the size.</p>
      </div>

      {capacity && !capacity.configured && (
        <div className="banner banner-warn">
          This Neo Cloud isn't accepting new orders right now — please contact support.
        </div>
      )}

      <div className="new-env-grid">
        <div className="panel">
          <div className="panel-header-row">
            <h2>What's included</h2>
          </div>
          {INCLUDED_GROUPS.map((group) => (
            <div key={group.title} className="included-group">
              <div className="included-group-title">
                <Icon name={group.icon} size={16} /> {group.title}
              </div>
              {group.items.map((item) => (
                <label key={item} className="toggle-row preset">
                  <input type="checkbox" checked disabled />
                  {item}
                </label>
              ))}
            </div>
          ))}
        </div>

        <form onSubmit={handleSubmit} className="panel new-env-form">
          <div className="panel-header-row">
            <h2>Deployment details</h2>
          </div>
          <label htmlFor="env-name">Environment name</label>
          <input
            id="env-name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Training-Run-12"
            required
            maxLength={80}
          />

          <label htmlFor="server-count">Number of GPU servers</label>
          <input
            id="server-count"
            type="number"
            min={1}
            max={maxCount}
            value={serverCount}
            onChange={(e) => {
              const next = parseInt(e.target.value || '1', 10)
              setServerCount(Math.max(1, Math.min(maxCount, Number.isNaN(next) ? 1 : next)))
            }}
          />
          <input
            type="range"
            min={1}
            max={maxCount}
            value={serverCount}
            onChange={(e) => setServerCount(parseInt(e.target.value, 10))}
            className="server-slider"
          />
          <p className="hint mono">
            {capacity ? `${capacity.available_count} servers available` : 'Checking availability…'} · {gpusPerServer}{' '}
            GPUs/server
          </p>

          <div className="new-env-summary">
            <div>
              <span className="k">Servers</span>
              <span className="v">{serverCount}</span>
            </div>
            <div>
              <span className="k">Total GPUs</span>
              <span className="v">{totalGpus}</span>
            </div>
            <div>
              <span className="k">Est. cost</span>
              <span className="v">${(totalGpus * 2.5).toLocaleString()}/hr</span>
            </div>
          </div>

          <div className="net-services-panel">
            <div className="panel-header-row">
              <span className="hint" style={{ margin: 0 }}>
                Netris services — NAT rules, Softgate ACLs, V-Nets, load balancing
              </span>
              <NetrisServicesMenu envName={name} onAdd={addExtra} />
            </div>
            {extrasList.length > 0 && (
              <ul className="extra-chip-list">
                {extrasList.map((x) => (
                  <li key={x.id} className="extra-chip">
                    <span className="extra-chip-icon">
                      <Icon name={EXTRA_META[x.kind].icon} size={14} />
                    </span>
                    <span className="extra-chip-kind">{EXTRA_META[x.kind].short}</span>
                    <span className="mono small extra-chip-summary">{summarize(x.kind, x.config)}</span>
                    <button type="button" className="btn-ghost" onClick={() => setEditingExtra(x.id)}>
                      Edit
                    </button>
                    <button type="button" className="btn-ghost" onClick={() => removeExtra(x.id)}>
                      <Icon name="x" size={13} />
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>

          {error && <div className="form-error">{error}</div>}
          <button type="submit" className="btn-primary" disabled={submitting || !capacity?.configured}>
            {submitting ? 'Deploying…' : 'Deploy environment'}
          </button>
        </form>
      </div>

      {editingExtra &&
        (() => {
          const item = extrasList.find((x) => x.id === editingExtra)
          if (!item) return null
          return (
            <ExtraServiceModal
              kind={item.kind}
              envName={name}
              initialConfig={item.config}
              onClose={() => setEditingExtra(null)}
              onSave={(config) => {
                updateExtra(item.id, config)
                setEditingExtra(null)
              }}
            />
          )
        })()}
    </AppShell>
  )
}
