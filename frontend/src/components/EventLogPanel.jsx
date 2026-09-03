import { useState } from 'react'

const TYPE_LABELS = {
  state_change: 'State',
  netris_api_call: 'Netris API',
  netris_poll: 'Netris',
  fake_step: 'Simulated',
  error: 'Error',
  delete_attempt: 'Delete',
}

function formatTime(iso) {
  return new Date(iso).toLocaleTimeString()
}

function describe(ev) {
  if (ev.message) return ev.message
  if (ev.event_type === 'state_change' && ev.to_status) return `Status changed to ${ev.to_status}`
  return '—'
}

export default function EventLogPanel({ events }) {
  const [expanded, setExpanded] = useState(() => new Set())

  function toggle(key) {
    setExpanded((prev) => {
      const next = new Set(prev)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })
  }

  return (
    <section className="panel">
      <div className="panel-header-row">
        <h2>Activity &amp; API log</h2>
        <span className="muted small">Real Netris calls and simulated steps, in order</span>
      </div>
      {!events || events.length === 0 ? (
        <p className="muted small">No activity recorded yet.</p>
      ) : (
        <ul className="event-log">
          {events.map((ev, i) => {
            const key = `${ev.at}-${i}`
            const isCall = ev.event_type === 'netris_api_call' && ev.detail
            const isOpen = expanded.has(key)
            return (
              <li key={key} className="event-log-item">
                <div
                  className={`event-log-row${isCall ? ' clickable' : ''}`}
                  onClick={isCall ? () => toggle(key) : undefined}
                >
                  <span className="event-log-time mono">{formatTime(ev.at)}</span>
                  <span className={`event-log-badge badge-${ev.event_type}`}>
                    {TYPE_LABELS[ev.event_type] || ev.event_type}
                  </span>
                  <span className="event-log-message">{describe(ev)}</span>
                  {isCall && <span className="event-log-chevron">{isOpen ? '▾' : '▸'}</span>}
                </div>
                {isCall && isOpen && (
                  <div className="event-log-detail mono">
                    <div className="event-log-detail-line">
                      <strong>{ev.detail.method}</strong> {ev.detail.url}
                    </div>
                    <div className="event-log-detail-label">Request body</div>
                    <pre>{ev.detail.request_body ? JSON.stringify(ev.detail.request_body, null, 2) : '(none)'}</pre>
                    <div className="event-log-detail-label">Response — HTTP {ev.detail.response_status}</div>
                    <pre>{JSON.stringify(ev.detail.response_body, null, 2)}</pre>
                  </div>
                )}
              </li>
            )
          })}
        </ul>
      )}
    </section>
  )
}
