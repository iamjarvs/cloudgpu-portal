import { useState } from 'react'
import AppShell from '../components/AppShell'
import { useAuth } from '../AuthContext'

function randomTokenSuffix() {
  const chars = 'abcdef0123456789'
  let out = ''
  for (let i = 0; i < 4; i++) out += chars[Math.floor(Math.random() * chars.length)]
  return out
}

export default function Settings() {
  const { me } = useAuth()
  const [email, setEmail] = useState('ops@hackmecorp.io')
  const [notifs, setNotifs] = useState({ email: true, weekly: true, incidents: true })
  const [saved, setSaved] = useState(false)
  const [tokenSuffix, setTokenSuffix] = useState('7f2a')
  const [regenerated, setRegenerated] = useState(false)

  function handleSave(e) {
    e.preventDefault()
    setSaved(true)
    setTimeout(() => setSaved(false), 2500)
  }

  function handleRegenerate() {
    if (!window.confirm('Regenerate your API token? Anything using the current token will stop working.')) return
    setTokenSuffix(randomTokenSuffix())
    setRegenerated(true)
    setTimeout(() => setRegenerated(false), 2500)
  }

  return (
    <AppShell title="Settings" narrow>
      <div className="content-header">
        <p className="content-subtitle">Manage your account preferences.</p>
      </div>
      <form onSubmit={handleSave}>
        <section className="panel">
          <h2>Profile</h2>
          <label>Organization</label>
          <input value={me?.tenant_display_name || ''} disabled />
          <label>Contact email</label>
          <input value={email} onChange={(e) => setEmail(e.target.value)} />
        </section>

        <section className="panel">
          <h2>Notifications</h2>
          <label className="toggle-row">
            <input
              type="checkbox"
              checked={notifs.email}
              onChange={(e) => setNotifs((n) => ({ ...n, email: e.target.checked }))}
            />
            Email me when an environment finishes provisioning
          </label>
          <label className="toggle-row">
            <input
              type="checkbox"
              checked={notifs.weekly}
              onChange={(e) => setNotifs((n) => ({ ...n, weekly: e.target.checked }))}
            />
            Send weekly usage reports
          </label>
          <label className="toggle-row">
            <input
              type="checkbox"
              checked={notifs.incidents}
              onChange={(e) => setNotifs((n) => ({ ...n, incidents: e.target.checked }))}
            />
            Notify me about network incidents at my sites
          </label>
        </section>

        <section className="panel">
          <h2>API Access</h2>
          <label>API Token</label>
          <div className="token-row">
            <input value={`hg_live_••••••••••••${tokenSuffix}`} disabled className="mono" />
            <button type="button" className="btn-secondary" onClick={handleRegenerate}>
              Regenerate
            </button>
          </div>
          <p className="hint">Use this token to authenticate CLI and SDK requests against the HeliosGrid API.</p>
          {regenerated && <span className="save-confirm">✓ Token regenerated</span>}
        </section>

        <div className="actions-row">
          <button type="submit" className="btn-primary">
            Save changes
          </button>
          {saved && <span className="save-confirm">✓ Saved</span>}
        </div>
      </form>
    </AppShell>
  )
}
