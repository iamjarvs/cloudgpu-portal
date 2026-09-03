import { useParams, Link } from 'react-router-dom'
import AppShell from '../components/AppShell'
import Icon from '../components/Icon'
import { PLATFORM_SECTIONS } from '../platformSections'

export default function PlatformPlaceholder() {
  const { section, sub } = useParams()
  const config = PLATFORM_SECTIONS[section]

  if (!config) {
    return (
      <AppShell title="Not found">
        <p className="muted">Unknown section.</p>
      </AppShell>
    )
  }

  const activeChild = sub ? config.children.find((c) => c.slug === sub) : null

  return (
    <AppShell title={config.label}>
      <div className="content-header">
        <p className="content-subtitle">{config.description}</p>
      </div>
      <div className="panel placeholder-panel">
        <div className="placeholder-icon">
          <Icon name={config.icon} size={32} />
        </div>
        <h2>{activeChild ? activeChild.label : `${config.label} isn't part of this demo`}</h2>
        <p className="muted">
          {activeChild
            ? activeChild.blurb
            : 'This account is scoped to dedicated GPU environments. Reach out to your HeliosGrid rep to enable this capability.'}
        </p>
      </div>
      <div className="env-grid">
        {config.children.map((child) => (
          <Link key={child.slug} to={`/platform/${section}/${child.slug}`} className="env-card platform-card">
            <div className="env-card-header">
              <span className="env-name">{child.label}</span>
            </div>
            <p className="muted small">{child.blurb}</p>
          </Link>
        ))}
      </div>
    </AppShell>
  )
}
