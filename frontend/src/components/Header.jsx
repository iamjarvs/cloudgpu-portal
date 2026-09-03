import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../AuthContext'
import Icon from './Icon'

const NOTIFICATIONS = [
  { id: 1, title: 'Environment active', body: '"Training-Cluster-Alpha" finished provisioning.', when: '2h ago' },
  { id: 2, title: 'Usage report ready', body: 'Your weekly utilization report is available.', when: '1d ago' },
  { id: 3, title: 'Maintenance window', body: 'Datacenter-A network maintenance scheduled for next week.', when: '3d ago' },
]

export default function Header({ title }) {
  const { me, refresh } = useAuth()
  const navigate = useNavigate()
  const [notifOpen, setNotifOpen] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)
  const [notifSeen, setNotifSeen] = useState(false)
  const ref = useRef(null)

  useEffect(() => {
    function onClickOutside(e) {
      if (ref.current && !ref.current.contains(e.target)) {
        setNotifOpen(false)
        setMenuOpen(false)
      }
    }
    document.addEventListener('mousedown', onClickOutside)
    return () => document.removeEventListener('mousedown', onClickOutside)
  }, [])

  async function handleLogout() {
    await api.logout()
    await refresh()
    navigate('/login')
  }

  function openNotifications() {
    setNotifOpen((o) => !o)
    setMenuOpen(false)
    setNotifSeen(true)
  }

  return (
    <header className="topbar" ref={ref}>
      <h1 className="topbar-title">{title}</h1>

      <div className="topbar-search">
        <Icon name="search" size={16} />
        <input type="text" placeholder="Search environments, docs, resources…" />
      </div>

      <div className="topbar-right">
        <div className="topbar-icon-btn-wrap">
          <button
            type="button"
            className="topbar-icon-btn"
            onClick={openNotifications}
            aria-label="Notifications"
          >
            <Icon name="bell" size={18} />
            {!notifSeen && <span className="topbar-badge" />}
          </button>
          {notifOpen && (
            <div className="dropdown notif-dropdown">
              <div className="dropdown-heading">Notifications</div>
              {NOTIFICATIONS.map((n) => (
                <div className="notif-item" key={n.id}>
                  <div className="notif-title">{n.title}</div>
                  <div className="notif-body">{n.body}</div>
                  <div className="notif-when">{n.when}</div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="topbar-icon-btn-wrap">
          <button
            type="button"
            className="account-pill"
            onClick={() => {
              setMenuOpen((o) => !o)
              setNotifOpen(false)
            }}
          >
            <span className="account-avatar">{(me?.tenant_display_name || 'H').slice(0, 1)}</span>
            <span className="account-name">{me?.tenant_display_name}</span>
            <Icon name="chevronDown" size={14} />
          </button>
          {menuOpen && (
            <div className="dropdown account-dropdown">
              <button type="button" onClick={() => { setMenuOpen(false); navigate('/account') }}>
                <Icon name="user" size={15} /> Account
              </button>
              <button type="button" onClick={() => { setMenuOpen(false); navigate('/settings') }}>
                <Icon name="settings" size={15} /> Settings
              </button>
              <button type="button" onClick={handleLogout}>
                <Icon name="logOut" size={15} /> Sign out
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}
