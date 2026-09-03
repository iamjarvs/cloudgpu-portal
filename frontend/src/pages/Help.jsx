import { useState } from 'react'
import AppShell from '../components/AppShell'
import Icon from '../components/Icon'

const ARTICLES = [
  { title: 'Getting started with your first environment', icon: 'rocket' },
  { title: 'Understanding GPU server allocation', icon: 'gpu' },
  { title: 'Networking and VPC isolation basics', icon: 'network' },
  { title: 'Billing and invoices FAQ', icon: 'creditCard' },
]

export default function Help() {
  const [submitted, setSubmitted] = useState(false)

  function handleOpenTicket() {
    setSubmitted(true)
    setTimeout(() => setSubmitted(false), 2500)
  }

  return (
    <AppShell title="Get Help">
      <div className="content-header">
        <p className="content-subtitle">Documentation, support, and platform status.</p>
      </div>
      <div className="dash-row">
        <div className="panel dash-panel-wide">
          <div className="panel-header-row">
            <h2>Popular articles</h2>
          </div>
          <ul className="help-list">
            {ARTICLES.map((a) => (
              <li key={a.title}>
                <Icon name={a.icon} size={16} /> {a.title}
              </li>
            ))}
          </ul>
        </div>
        <div className="panel dash-panel-narrow">
          <div className="panel-header-row">
            <h2>Contact support</h2>
          </div>
          <p className="muted small">Our infrastructure team is available 24/7 for HackMeCorp.</p>
          <button type="button" className="btn-primary" style={{ marginTop: '0.5rem' }} onClick={handleOpenTicket}>
            Open a ticket
          </button>
          {submitted && <span className="save-confirm">✓ Ticket submitted</span>}
        </div>
      </div>
    </AppShell>
  )
}
