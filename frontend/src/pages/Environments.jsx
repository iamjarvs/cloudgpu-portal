import { useEffect, useState, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import AppShell from '../components/AppShell'
import EnvironmentCard from '../components/EnvironmentCard'

const NON_TERMINAL = new Set(['queued', 'provisioning_compute', 'awaiting_network', 'stalled', 'deleting'])

export default function Environments() {
  const [environments, setEnvironments] = useState([])
  const [loading, setLoading] = useState(true)
  const [, setTick] = useState(0)

  const load = useCallback(async () => {
    try {
      const data = await api.listEnvironments()
      setEnvironments(data)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const hasNonTerminal = environments.some((e) => NON_TERMINAL.has(e.status))
  const hasDummy = environments.some((e) => e.kind === 'dummy')

  useEffect(() => {
    if (!hasNonTerminal) return
    const interval = setInterval(load, 3000)
    return () => clearInterval(interval)
  }, [hasNonTerminal, load])

  useEffect(() => {
    if (!hasDummy) return
    const interval = setInterval(() => setTick((t) => t + 1), 4000)
    return () => clearInterval(interval)
  }, [hasDummy])

  return (
    <AppShell title="Environments">
      <div className="content-header">
        <p className="content-subtitle">Every environment provisioned on your account, real and demo.</p>
        <Link to="/environments/new" className="btn-primary">
          <span>+ New Environment</span>
        </Link>
      </div>
      {loading ? (
        <p className="muted">Loading…</p>
      ) : environments.length === 0 ? (
        <p className="muted">No environments yet — deploy your first one.</p>
      ) : (
        <div className="env-grid">
          {environments.map((env) => (
            <EnvironmentCard key={env.uuid} env={env} />
          ))}
        </div>
      )}
    </AppShell>
  )
}
