import { useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import Logo from './Logo'
import Icon from './Icon'
import { PLATFORM_SECTIONS } from '../platformSections'

const PLATFORM_ORDER = ['compute', 'networking', 'storage', 'data-services', 'insights', 'marketplace', 'security']

export default function Sidebar() {
  const location = useLocation()
  const [expanded, setExpanded] = useState(() => {
    const active = PLATFORM_ORDER.find((slug) => location.pathname.startsWith(`/platform/${slug}`))
    return active ? { [active]: true } : {}
  })

  function toggle(slug) {
    setExpanded((prev) => ({ ...prev, [slug]: !prev[slug] }))
  }

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <Logo size={24} />
      </div>

      <nav className="sidebar-nav">
        <NavLink to="/dashboard" className={({ isActive }) => `sidebar-link${isActive ? ' active' : ''}`}>
          <Icon name="home" /> Dashboard
        </NavLink>
        <NavLink to="/environments" className={({ isActive }) => `sidebar-link${isActive ? ' active' : ''}`}>
          <Icon name="server" /> Environments
        </NavLink>

        <div className="sidebar-heading">Platform</div>
        {PLATFORM_ORDER.map((slug) => {
          const section = PLATFORM_SECTIONS[slug]
          const isOpen = !!expanded[slug]
          const sectionActive = location.pathname.startsWith(`/platform/${slug}`)
          return (
            <div key={slug} className="sidebar-group">
              <button
                type="button"
                className={`sidebar-link sidebar-group-toggle${sectionActive ? ' active' : ''}`}
                onClick={() => toggle(slug)}
              >
                <Icon name={section.icon} />
                <span className="sidebar-link-label">{section.label}</span>
                <Icon name={isOpen ? 'chevronDown' : 'chevronRight'} size={14} className="sidebar-chevron" />
              </button>
              {isOpen && (
                <div className="sidebar-subnav">
                  {section.children.map((child) => (
                    <NavLink
                      key={child.slug}
                      to={`/platform/${slug}/${child.slug}`}
                      className={({ isActive }) => `sidebar-sublink${isActive ? ' active' : ''}`}
                    >
                      {child.label}
                    </NavLink>
                  ))}
                </div>
              )}
            </div>
          )
        })}

        <div className="sidebar-heading">Account</div>
        <NavLink to="/billing" className={({ isActive }) => `sidebar-link${isActive ? ' active' : ''}`}>
          <Icon name="creditCard" /> Billing
        </NavLink>
        <NavLink to="/account" className={({ isActive }) => `sidebar-link${isActive ? ' active' : ''}`}>
          <Icon name="user" /> Account
        </NavLink>
        <NavLink to="/settings" className={({ isActive }) => `sidebar-link${isActive ? ' active' : ''}`}>
          <Icon name="settings" /> Settings
        </NavLink>
        <NavLink to="/help" className={({ isActive }) => `sidebar-link${isActive ? ' active' : ''}`}>
          <Icon name="helpCircle" /> Get Help
        </NavLink>
      </nav>
    </aside>
  )
}
