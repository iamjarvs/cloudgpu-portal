import { useEffect, useState, useMemo } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../AuthContext'
import AppShell from '../components/AppShell'
import StatCard from '../components/StatCard'
import Gauge from '../components/Gauge'
import Sparkline from '../components/Sparkline'
import Icon from '../components/Icon'
import StatusPill from '../components/StatusPill'
import { dummyMetrics, dummySeries } from '../fakeMetrics'
import { timeAgo, formatCurrency } from '../utils'

const LIVE_STATUSES = new Set(['queued', 'provisioning_compute', 'awaiting_network', 'stalled', 'active'])

function activityText(env) {
  switch (env.status) {
    case 'active':
      return `"${env.name}" is now active`
    case 'failed':
      return `"${env.name}" failed to provision`
    case 'provisioning_compute':
      return `"${env.name}" is provisioning`
    case 'awaiting_network':
      return `"${env.name}" is finalizing network fabric`
    case 'stalled':
      return `"${env.name}" is taking longer than expected`
    case 'deleted':
      return `"${env.name}" was terminated`
    case 'delete_failed':
      return `"${env.name}" failed to terminate`
    default:
      return `"${env.name}" updated`
  }
}

function activityIcon(status) {
  if (status === 'active') return 'check'
  if (status === 'failed' || status === 'delete_failed') return 'x'
  if (status === 'deleted') return 'x'
  return 'clock'
}

const FAKE_ACTIVITY = [
  { id: 'fake-1', text: 'Weekly usage report generated for HackMeCorp', when: '2d ago', icon: 'barChart' },
  { id: 'fake-2', text: 'Scheduled network maintenance completed at Datacenter-A', when: '4d ago', icon: 'network' },
]

export default function Dashboard() {
  const { me } = useAuth()
  const navigate = useNavigate()
  const [environments, setEnvironments] = useState([])
  const [capacity, setCapacity] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([api.listEnvironments(), api.capacity().catch(() => null)]).then(([envs, cap]) => {
      setEnvironments(envs)
      setCapacity(cap)
      setLoading(false)
    })
  }, [])

  const liveEnvs = useMemo(() => environments.filter((e) => LIVE_STATUSES.has(e.status)), [environments])
  const totalGpus = liveEnvs.reduce((sum, e) => sum + e.total_gpus, 0)
  const usedServers = liveEnvs.reduce((sum, e) => sum + e.requested_server_count, 0)
  const activeCount = environments.filter((e) => e.status === 'active').length

  const today = new Date()
  const dayOfMonth = today.getDate()
  const monthlySpend = Math.round(totalGpus * 2.5 * 24 * Math.max(dayOfMonth, 3))

  const avgUtil = useMemo(() => {
    const active = environments.filter((e) => e.status === 'active')
    if (active.length === 0) return 0
    return Math.round(active.reduce((sum, e) => sum + dummyMetrics(e.uuid).gpuUtilPct, 0) / active.length)
  }, [environments])

  const utilSeries = useMemo(() => dummySeries('fleet-util-24h', 24, { min: 35, max: 88 }), [])
  const spendSeries = useMemo(
    () => dummySeries('fleet-spend-6mo', 6, { min: monthlySpend * 0.55, max: monthlySpend * 1.05 }),
    [monthlySpend],
  )

  const totalPoolServers = capacity?.configured ? capacity.available_count + usedServers : null
  const capacityPct = totalPoolServers ? Math.round((usedServers / totalPoolServers) * 100) : 0

  const activity = useMemo(() => {
    const real = environments
      .slice()
      .sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at))
      .slice(0, 4)
      .map((e) => ({ id: e.uuid, text: activityText(e), when: timeAgo(e.updated_at), icon: activityIcon(e.status) }))
    return [...real, ...FAKE_ACTIVITY].slice(0, 6)
  }, [environments])

  const recentEnvs = useMemo(
    () => environments.slice().sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at)).slice(0, 5),
    [environments],
  )

  return (
    <AppShell title="Dashboard">
      <div className="dash-welcome">
        <div>
          <h2>Welcome back, {me?.tenant_display_name}</h2>
          <p className="muted">
            {today.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' })}
          </p>
        </div>
        <Link to="/environments/new" className="btn-primary">
          + New Environment
        </Link>
      </div>

      {loading ? (
        <p className="muted">Loading…</p>
      ) : (
        <>
          <div className="stat-grid">
            <StatCard icon="gpu" label="Total GPUs" value={totalGpus} sublabel={`${usedServers} servers in use`} />
            <StatCard
              icon="server"
              label="Active Environments"
              value={activeCount}
              sublabel={`${environments.length} total`}
            />
            <StatCard
              icon="creditCard"
              label="Est. Spend (MTD)"
              value={formatCurrency(monthlySpend)}
              trend={{ direction: 'up', text: '+4.2% vs last month' }}
            />
            <StatCard icon="clock" label="Platform Uptime" value="99.98%" sublabel="Trailing 90 days" />
          </div>

          <div className="dash-row">
            <div className="panel dash-panel-wide">
              <div className="panel-header-row">
                <h2>GPU Utilization</h2>
                <span className="muted small">Last 24 hours · all environments</span>
              </div>
              <div className="dash-util-row">
                <Gauge value={avgUtil} label="Fleet average" />
                <div className="dash-util-chart">
                  <Sparkline data={utilSeries} />
                  <div className="sparkline-axis">
                    <span>24h ago</span>
                    <span>Now</span>
                  </div>
                </div>
              </div>
            </div>
            <div className="panel dash-panel-narrow">
              <div className="panel-header-row">
                <h2>Capacity — Datacenter-A</h2>
              </div>
              {totalPoolServers ? (
                <>
                  <div className="capacity-bar">
                    <div className="capacity-bar-fill" style={{ width: `${capacityPct}%` }} />
                  </div>
                  <p className="muted small">
                    {usedServers} of {totalPoolServers} servers in use ({capacityPct}%)
                  </p>
                </>
              ) : (
                <p className="muted small">Capacity data unavailable right now.</p>
              )}
              <div className="kv-grid mono" style={{ marginTop: '1rem' }}>
                <div>
                  <span className="k">Site</span>
                  <span className="v">Datacenter-A</span>
                </div>
                <div>
                  <span className="k">Network status</span>
                  <span className="v" style={{ color: 'var(--green)' }}>
                    Operational
                  </span>
                </div>
              </div>
            </div>
          </div>

          <div className="dash-row">
            <div className="panel dash-panel-wide">
              <div className="panel-header-row">
                <h2>Recent Activity</h2>
              </div>
              <ul className="activity-list">
                {activity.map((a) => (
                  <li key={a.id} className="activity-item">
                    <span className="activity-icon">
                      <Icon name={a.icon} size={15} />
                    </span>
                    <div>
                      <div className="activity-text">{a.text}</div>
                      <div className="activity-when">{a.when}</div>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
            <div className="panel dash-panel-narrow">
              <div className="panel-header-row">
                <h2>Billing</h2>
                <Link to="/billing" className="panel-link">
                  View details
                </Link>
              </div>
              <div className="billing-amount">
                {formatCurrency(monthlySpend)}
                <span className="muted small"> MTD</span>
              </div>
              <Sparkline data={spendSeries} height={48} color="var(--blue)" />
            </div>
          </div>

          <div className="panel">
            <div className="panel-header-row">
              <h2>Your Environments</h2>
              <Link to="/environments" className="panel-link">
                View all
              </Link>
            </div>
            <table className="data-table mono dash-env-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Status</th>
                  <th>Servers</th>
                  <th>GPUs</th>
                  <th>Updated</th>
                </tr>
              </thead>
              <tbody>
                {recentEnvs.map((e) => (
                  <tr key={e.uuid} onClick={() => navigate(`/environments/${e.uuid}`)}>
                    <td className="not-mono">
                      {e.name}
                      {e.kind === 'dummy' && <span className="demo-badge inline">DEMO</span>}
                    </td>
                    <td>
                      <StatusPill status={e.status} />
                    </td>
                    <td>{e.requested_server_count}</td>
                    <td>{e.total_gpus}</td>
                    <td>{timeAgo(e.updated_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </AppShell>
  )
}
