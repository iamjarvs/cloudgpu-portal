import { useEffect, useRef, useState } from 'react'
import { currentStepIndex } from '../deploymentSteps'
import { EXTRA_META } from '../netrisExtras'

// Animated system diagram shown while an environment is deploying: compute,
// storage, and network fabric light up in sequence as the fake-compute
// animation and the real Netris poll progress, and any requested add-on
// service (NAT rule, ACL, V-Net, load balancer) gets its own node that
// stays greyed out until Netris actually confirms it — see
// app/provisioning/extras.py for the state machine this mirrors
// ('pending' -> 'created' | 'failed').

const CORE_NODES = [
  { key: 'compute', label: 'Compute', sub: 'GPU servers', icon: 'cpu' },
  { key: 'storage', label: 'Storage', sub: 'NVMe scratch volumes', icon: 'database' },
  { key: 'network', label: 'Networking', sub: 'VPC + VLAN fabric', icon: 'network' },
]

function stageFromIndex(threshold, currentIndex) {
  if (currentIndex === -1) return 'done'
  if (currentIndex > threshold) return 'done'
  if (currentIndex === threshold) return 'active'
  return 'pending'
}

function coreStates(env) {
  const currentIndex = currentStepIndex(env.status_detail)
  const compute = stageFromIndex(2, currentIndex)
  const storage = stageFromIndex(3, currentIndex)
  const fabricRequested = stageFromIndex(4, currentIndex)
  let network
  if (env.status === 'active') network = 'done'
  else if (fabricRequested !== 'pending') network = 'active'
  else network = 'pending'
  return { compute, storage, network }
}

function StateBadge({ state }) {
  if (state === 'done') return <span className="diagram-badge done">✓</span>
  if (state === 'failed') return <span className="diagram-badge failed">!</span>
  if (state === 'active') return <span className="diagram-badge active" />
  return null
}

function DiagramNode({ label, sub, icon, state, flash, highlight }) {
  return (
    <div className={`diagram-node state-${state}${flash ? ' flash' : ''}${highlight ? ' highlight' : ''}`}>
      <div className="diagram-node-icon">
        <NodeIcon name={icon} />
      </div>
      <div className="diagram-node-text">
        <span className="diagram-node-label">{label}</span>
        <span className="diagram-node-sub">{sub}</span>
      </div>
      <StateBadge state={state} />
    </div>
  )
}

// Small inline glyph set — deliberately separate from components/Icon.jsx
// so a node's stroke color can be driven by the state-* CSS classes above
// via currentColor without fighting that component's own size/color props.
function NodeIcon({ name }) {
  const common = { fill: 'none', stroke: 'currentColor', strokeWidth: 1.6, strokeLinecap: 'round', strokeLinejoin: 'round' }
  switch (name) {
    case 'cpu':
      return (
        <svg width="18" height="18" viewBox="0 0 20 20">
          <rect x="6" y="6" width="8" height="8" rx="1" {...common} />
          <rect x="8.3" y="8.3" width="3.4" height="3.4" rx="0.5" {...common} />
          <line x1="10" y1="2.5" x2="10" y2="5" {...common} />
          <line x1="10" y1="15" x2="10" y2="17.5" {...common} />
          <line x1="2.5" y1="10" x2="5" y2="10" {...common} />
          <line x1="15" y1="10" x2="17.5" y2="10" {...common} />
        </svg>
      )
    case 'database':
      return (
        <svg width="18" height="18" viewBox="0 0 20 20">
          <ellipse cx="10" cy="5" rx="6.5" ry="2.4" {...common} />
          <path d="M3.5 5 V15 C3.5 16.3 6.4 17.4 10 17.4 C13.6 17.4 16.5 16.3 16.5 15 V5" {...common} />
          <path d="M3.5 10 C3.5 11.3 6.4 12.4 10 12.4 C13.6 12.4 16.5 11.3 16.5 10" {...common} />
        </svg>
      )
    case 'network':
      return (
        <svg width="18" height="18" viewBox="0 0 20 20">
          <circle cx="10" cy="4" r="2" {...common} />
          <circle cx="4" cy="16" r="2" {...common} />
          <circle cx="16" cy="16" r="2" {...common} />
          <line x1="9" y1="5.6" x2="5" y2="14.2" {...common} />
          <line x1="11" y1="5.6" x2="15" y2="14.2" {...common} />
        </svg>
      )
    case 'globe':
      return (
        <svg width="18" height="18" viewBox="0 0 20 20">
          <circle cx="10" cy="10" r="7.5" {...common} />
          <ellipse cx="10" cy="10" rx="3.2" ry="7.5" {...common} />
          <line x1="2.5" y1="10" x2="17.5" y2="10" {...common} />
        </svg>
      )
    case 'shield':
      return (
        <svg width="18" height="18" viewBox="0 0 20 20">
          <path d="M10 2.5 L16.5 5 V9.5 C16.5 13.5 13.7 16.4 10 17.5 C6.3 16.4 3.5 13.5 3.5 9.5 V5 Z" {...common} />
          <polyline points="7.2,10 9.2,12 13,7.5" {...common} />
        </svg>
      )
    case 'barChart':
      return (
        <svg width="18" height="18" viewBox="0 0 20 20">
          <line x1="3.5" y1="16.5" x2="16.5" y2="16.5" {...common} />
          <rect x="5" y="10.5" width="3" height="6" rx="0.6" {...common} />
          <rect x="8.7" y="6.5" width="3" height="10" rx="0.6" {...common} />
          <rect x="12.4" y="3" width="3" height="13.5" rx="0.6" {...common} />
        </svg>
      )
    default:
      return null
  }
}

export default function DeploymentDiagram({ env }) {
  const { compute, storage, network } = coreStates(env)
  const extraKinds = ['nat', 'acl', 'vnet', 'lb'].filter((k) => (env.extras?.[k] || []).length > 0)

  // Track the moment each add-on flips to "created" so it gets one brief
  // highlight pulse instead of just quietly turning green — this is the
  // "highlight the NAT rule being created" behavior called out explicitly.
  const [flashKeys, setFlashKeys] = useState({})
  const prevStates = useRef({})
  useEffect(() => {
    const next = {}
    extraKinds.forEach((kind) => {
      (env.extras[kind] || []).forEach((item) => {
        const state = item.state === 'created' ? 'done' : item.state === 'failed' ? 'failed' : 'active'
        const trackKey = `${kind}:${item.local_id}`
        if (prevStates.current[trackKey] && prevStates.current[trackKey] !== 'done' && state === 'done') {
          next[trackKey] = true
          setTimeout(() => {
            setFlashKeys((prev) => {
              const copy = { ...prev }
              delete copy[trackKey]
              return copy
            })
          }, 1800)
        }
        prevStates.current[trackKey] = state
      })
    })
    if (Object.keys(next).length) setFlashKeys((prev) => ({ ...prev, ...next }))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [JSON.stringify(env.extras)])

  return (
    <div className="deployment-diagram">
      <div className="diagram-column diagram-core">
        {CORE_NODES.map((n) => (
          <DiagramNode key={n.key} label={n.label} sub={n.sub} icon={n.icon} state={{ compute, storage, network }[n.key]} />
        ))}
      </div>
      <div className="diagram-connector">
        <span className={`diagram-connector-line${network !== 'pending' ? ' flowing' : ''}`} />
      </div>
      <div className="diagram-column diagram-extras">
        {extraKinds.length === 0 && <p className="muted small diagram-extras-empty">No add-on services requested.</p>}
        {extraKinds.map((kind) =>
          (env.extras[kind] || []).map((item) => {
            const state = item.state === 'created' ? 'done' : item.state === 'failed' ? 'failed' : 'active'
            const trackKey = `${kind}:${item.local_id}`
            return (
              <DiagramNode
                key={trackKey}
                label={item.config?.name || EXTRA_META[kind].label}
                sub={EXTRA_META[kind].label}
                icon={EXTRA_META[kind].icon}
                state={network === 'pending' ? 'pending' : state}
                highlight={kind === 'nat'}
                flash={!!flashKeys[trackKey]}
              />
            )
          }),
        )}
      </div>
    </div>
  )
}
