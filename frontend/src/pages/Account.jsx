import AppShell from '../components/AppShell'
import { useAuth } from '../AuthContext'

const TEAM = [
  { name: 'Alex Rivera', role: 'Owner', email: 'alex@hackmecorp.io' },
  { name: 'Priya Nair', role: 'Infrastructure Admin', email: 'priya@hackmecorp.io' },
  { name: 'Sam Okafor', role: 'Billing Admin', email: 'sam@hackmecorp.io' },
]

export default function Account() {
  const { me } = useAuth()
  return (
    <AppShell title="Account" narrow>
      <div className="panel account-header-panel">
        <span className="account-avatar large">{(me?.tenant_display_name || 'H').slice(0, 1)}</span>
        <div>
          <h2 style={{ margin: 0 }}>{me?.tenant_display_name}</h2>
          <p className="muted">Customer since March 2026 · Pay-as-you-go plan</p>
        </div>
      </div>
      <div className="panel">
        <h2>Team</h2>
        <table className="data-table mono">
          <thead>
            <tr>
              <th>Name</th>
              <th>Role</th>
              <th>Email</th>
            </tr>
          </thead>
          <tbody>
            {TEAM.map((t) => (
              <tr key={t.email}>
                <td className="not-mono">{t.name}</td>
                <td>{t.role}</td>
                <td>{t.email}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </AppShell>
  )
}
