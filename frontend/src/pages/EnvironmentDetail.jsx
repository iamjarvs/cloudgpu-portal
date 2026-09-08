import { useEffect, useRef, useState, useCallback, useMemo } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api } from '../api'
import AppShell from '../components/AppShell'
import StatusPill from '../components/StatusPill'
import EventLogPanel from '../components/EventLogPanel'
import ConnectivityCard from '../components/ConnectivityCard'
import DeploymentDiagram from '../components/DeploymentDiagram'
import ExtraServicesPanel from '../components/ExtraServicesPanel'
import { COMPUTE_STEPS, STEP_LOGS } from '../deploymentSteps'

const NON_TERMINAL = new Set(['queued', 'provisioning_compute', 'awaiting_network', 'stalled', 'deleting'])
const CHECKLIST_STATUSES = new Set(['queued', 'provisioning_compute', 'awaiting_network', 'stalled'])
const CAN_TERMINATE = new Set(['queued', 'provisioning_compute', 'awaiting_network', 'stalled', 'active', 'failed'])

function buildLogLines(currentIndex, elapsed, total) {
  const lines = []
  const stepCount = COMPUTE_STEPS.length
  const stepDuration = total && total > 0 ? total / stepCount : 0
  const resolvedIndex = currentIndex === -1 ? stepCount : currentIndex

  for (let i = 0; i < stepCount; i++) {
    const stepLogs = STEP_LOGS[i]
    if (i < resolvedIndex) {
      lines.push(...stepLogs.map((l) => ({ text: l, step: i })))
    } else if (i === resolvedIndex && stepDuration > 0) {
      const stepStart = i * stepDuration
      const fraction = Math.max(0, Math.min(1, (elapsed - stepStart) / stepDuration))
      const count = Math.max(1, Math.ceil(fraction * stepLogs.length))
      lines.push(...stepLogs.slice(0, count).map((l) => ({ text: l, step: i })))
    }
  }
  return lines
}

export default function EnvironmentDetail() {
  const { uuid } = useParams()
  const navigate = useNavigate()
  const [env, setEnv] = useState(null)
  const [events, setEvents] = useState([])
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)
  const [connectivityRun, setConnectivityRun] = useState(null)

  const load = useCallback(async () => {
    try {
      const [data, eventRows] = await Promise.all([api.getEnvironment(uuid), api.getEnvironmentEvents(uuid)])
      setEnv(data)
      setEvents(eventRows)
    } catch (err) {
      setError(err.message)
    }
  }, [uuid])

  useEffect(() => {
    load()
  }, [load])

  useEffect(() => {
    if (!env || !NON_TERMINAL.has(env.status)) return
    const interval = setInterval(load, 2000)
    return () => clearInterval(interval)
  }, [env, load])

  const currentIndex = env ? COMPUTE_STEPS.indexOf(env.status_detail) : -1
  const logLines = useMemo(() => {
    if (!env) return []
    return buildLogLines(currentIndex, env.compute_elapsed_seconds || 0, env.compute_total_seconds || 0)
  }, [env, currentIndex])

  const logRef = useRef(null)
  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight
  }, [logLines])

  async function handleTerminate() {
    if (!window.confirm(`Terminate "${env.name}"? This cannot be undone.`)) return
    setBusy(true)
    try {
      await api.deleteEnvironment(uuid)
      await load()
    } finally {
      setBusy(false)
    }
  }

  async function handleRetryDelete() {
    setBusy(true)
    try {
      await api.retryDelete(uuid)
      await load()
    } finally {
      setBusy(false)
    }
  }

  async function handleDismissDelete() {
    if (
      !window.confirm(
        `Dismiss this delete failure? This only removes "${env.name}" from your dashboard — we could not confirm the underlying infrastructure was torn down, so it may still exist. Contact support if you need that verified.`,
      )
    ) {
      return
    }
    setBusy(true)
    try {
      await api.dismissDelete(uuid)
      await load()
    } finally {
      setBusy(false)
    }
  }

  if (error) {
    return (
      <AppShell title="Environment">
        <p className="form-error">{error}</p>
      </AppShell>
    )
  }
  if (!env) {
    return (
      <AppShell title="Environment">
        <p className="muted">Loading…</p>
      </AppShell>
    )
  }

  return (
    <AppShell title={env.name}>
      <div className="detail-header">
        <button type="button" className="btn-ghost" onClick={() => navigate('/environments')}>
          ← All environments
        </button>
        {env.kind === 'dummy' && <span className="demo-badge">DEMO</span>}
      </div>
      <div className="detail-title-row">
        <h1>{env.name}</h1>
        <StatusPill status={env.status} />
      </div>

      {env.status === 'failed' && <div className="banner banner-error">{env.error_message}</div>}

      {env.status === 'delete_failed' && (
        <div className="banner banner-error">
          Netris delete failed: {env.error_message}
          <div className="banner-actions">
            <button className="btn-secondary" disabled={busy} onClick={handleRetryDelete}>
              Retry
            </button>
            <button className="btn-ghost" disabled={busy} onClick={handleDismissDelete}>
              Dismiss
            </button>
          </div>
        </div>
      )}

      {CHECKLIST_STATUSES.has(env.status) && (
        <section className="panel">
          <div className="panel-header-row">
            <h2>Deployment console</h2>
            <span className="muted small">
              {env.compute_elapsed_seconds ?? 0}s / {env.compute_total_seconds ?? '–'}s
            </span>
          </div>
          <div className="progress-bar">
            <div className="progress-bar-fill" style={{ width: `${env.compute_progress_pct}%` }} />
          </div>
          <DeploymentDiagram env={env} />
          <div className="console-grid">
            <ul className="checklist">
              {COMPUTE_STEPS.map((step, i) => {
                const state = currentIndex === -1 ? 'done' : i < currentIndex ? 'done' : i === currentIndex ? 'active' : 'pending'
                return (
                  <li key={step} className={`checklist-item ${state}`}>
                    <span className="checklist-icon">{state === 'done' ? '✓' : state === 'active' ? '●' : '○'}</span>
                    {step}
                  </li>
                )
              })}
            </ul>
            <div className="console-log mono" ref={logRef}>
              {logLines.map((line, i) => (
                <div key={i} className="console-log-line">
                  <span className="console-log-prompt">$</span> {line.text}
                </div>
              ))}
              <div className="console-log-line console-cursor">
                <span className="console-log-prompt">$</span>
                <span className="cursor-blink">▍</span>
              </div>
            </div>
          </div>
          {env.kind === 'real' && (
            <div className={`fabric-status${env.status === 'stalled' ? ' stalled' : ''}`}>
              Network fabric: {env.netris_status_label || 'waiting for Netris…'}
              {env.status === 'stalled' && <span className="hint"> — taking longer than expected, still waiting</span>}
            </div>
          )}
        </section>
      )}

      <section className="panel">
        <h2>Overview</h2>
        <div className="kv-grid mono">
          <div>
            <span className="k">Servers</span>
            <span className="v">{env.requested_server_count}</span>
          </div>
          <div>
            <span className="k">Total GPUs</span>
            <span className="v">{env.total_gpus}</span>
          </div>
          <div>
            <span className="k">VPC</span>
            <span className="v">{env.netris_vpc_name || '—'}</span>
          </div>
          <div>
            <span className="k">Created</span>
            <span className="v">{new Date(env.created_at).toLocaleString()}</span>
          </div>
        </div>
        {env.kind === 'real' && env.servers?.length > 0 && (
          <div className="actions-row">
            <button
              type="button"
              className="btn-secondary"
              onClick={() => setConnectivityRun((n) => (n === null ? 0 : n + 1))}
            >
              Test Connectivity
            </button>
          </div>
        )}
      </section>

      <ExtraServicesPanel env={env} onChange={setEnv} />

      {connectivityRun !== null && (
        <section className="panel">
          <div className="panel-header-row">
            <h2>Connectivity Test</h2>
            <span className="muted small">cluster-ping.sh, source → every other server in this environment</span>
          </div>
          <div className="connectivity-grid">
            {env.servers.map((s) => (
              <ConnectivityCard key={`${connectivityRun}-${s.id}`} envUuid={uuid} server={s} />
            ))}
          </div>
        </section>
      )}

      {env.servers?.length > 0 && (
        <section className="panel">
          <h2>Servers</h2>
          <table className="data-table mono">
            <thead>
              <tr>
                <th>Name</th>
                <th>ID</th>
              </tr>
            </thead>
            <tbody>
              {env.servers.map((s) => (
                <tr key={s.id}>
                  <td>{s.name}</td>
                  <td>{s.id}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      {env.subnets?.vnets?.length > 0 && (
        <section className="panel">
          <h2>Network</h2>
          <table className="data-table mono">
            <thead>
              <tr>
                <th>Network</th>
                <th>VLAN</th>
                <th>Gateway</th>
              </tr>
            </thead>
            <tbody>
              {env.subnets.vnets.map((v) => (
                <tr key={v.id}>
                  <td>{v.name}</td>
                  <td>{v.vlan || '—'}</td>
                  <td>{(v.ipv4Gateways || []).map((g) => g.prefix || g.address).join(', ') || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      <EventLogPanel events={events} />

      {CAN_TERMINATE.has(env.status) && (
        <div className="actions-row">
          <button className="btn-danger" disabled={busy} onClick={handleTerminate}>
            Terminate environment
          </button>
        </div>
      )}
    </AppShell>
  )
}
