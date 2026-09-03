import { useMemo, useState } from 'react'
import AppShell from '../components/AppShell'
import Sparkline from '../components/Sparkline'
import { dummySeries } from '../fakeMetrics'
import { formatCurrency } from '../utils'

const INVOICES = [
  { id: 'INV-2026-08', period: 'August 2026', amount: 41230, status: 'Paid' },
  { id: 'INV-2026-07', period: 'July 2026', amount: 38650, status: 'Paid' },
  { id: 'INV-2026-06', period: 'June 2026', amount: 35100, status: 'Paid' },
  { id: 'INV-2026-05', period: 'May 2026', amount: 29870, status: 'Paid' },
]

export default function Billing() {
  const series = useMemo(() => dummySeries('billing-6mo', 6, { min: 28000, max: 45000 }), [])
  const current = series[series.length - 1]
  const [updateSent, setUpdateSent] = useState(false)

  function handleUpdatePayment() {
    setUpdateSent(true)
    setTimeout(() => setUpdateSent(false), 2500)
  }

  return (
    <AppShell title="Billing">
      <div className="content-header">
        <p className="content-subtitle">Usage-based billing across all environments.</p>
      </div>
      <div className="dash-row">
        <div className="panel dash-panel-wide">
          <div className="panel-header-row">
            <h2>Spend — last 6 months</h2>
          </div>
          <div className="billing-amount">
            {formatCurrency(current)}
            <span className="muted small"> this month</span>
          </div>
          <Sparkline data={series} color="var(--blue)" height={80} />
        </div>
        <div className="panel dash-panel-narrow">
          <div className="panel-header-row">
            <h2>Payment method</h2>
          </div>
          <div className="kv-grid mono">
            <div>
              <span className="k">Card</span>
              <span className="v">Visa •••• 4242</span>
            </div>
            <div>
              <span className="k">Billing cycle</span>
              <span className="v">Monthly</span>
            </div>
            <div>
              <span className="k">Next invoice</span>
              <span className="v">Oct 1, 2026</span>
            </div>
            <div>
              <span className="k">Plan</span>
              <span className="v">Pay-as-you-go</span>
            </div>
          </div>
          <button type="button" className="btn-secondary" style={{ marginTop: '1rem' }} onClick={handleUpdatePayment}>
            Update payment method
          </button>
          {updateSent && <span className="save-confirm">✓ Request sent</span>}
        </div>
      </div>
      <div className="panel">
        <div className="panel-header-row">
          <h2>Invoice history</h2>
        </div>
        <table className="data-table mono">
          <thead>
            <tr>
              <th>Invoice</th>
              <th>Period</th>
              <th>Amount</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {INVOICES.map((inv) => (
              <tr key={inv.id}>
                <td>{inv.id}</td>
                <td className="not-mono">{inv.period}</td>
                <td>{formatCurrency(inv.amount)}</td>
                <td>
                  <span className="status-pill pill-green">{inv.status}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </AppShell>
  )
}
