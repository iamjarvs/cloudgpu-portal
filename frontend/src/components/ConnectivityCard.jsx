import { useEffect, useState } from 'react'
import { api } from '../api'

export default function ConnectivityCard({ envUuid, server }) {
  const [state, setState] = useState('running') // running | ok | error
  const [output, setOutput] = useState('')
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    setState('running')
    api
      .testConnectivity(envUuid, server.id)
      .then((data) => {
        if (cancelled) return
        setOutput(data.output || '')
        setState('ok')
      })
      .catch((err) => {
        if (cancelled) return
        setError(err.message)
        setState('error')
      })
    return () => {
      cancelled = true
    }
  }, [envUuid, server.id])

  return (
    <div className="connectivity-card">
      <div className="connectivity-card-head">
        <span className="connectivity-card-name">{server.name}</span>
        {state === 'running' && <span className="connectivity-badge running">Running…</span>}
        {state === 'ok' && <span className="connectivity-badge ok">Done</span>}
        {state === 'error' && <span className="connectivity-badge error">Failed</span>}
      </div>
      {state === 'running' && <p className="muted small">Executing cluster-ping.sh over SSH…</p>}
      {state === 'error' && <p className="form-error">{error}</p>}
      {state === 'ok' && <pre className="connectivity-output mono">{output}</pre>}
    </div>
  )
}
