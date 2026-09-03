import { Link } from 'react-router-dom'
import StatusPill from './StatusPill'
import { dummyMetrics } from '../fakeMetrics'
import { timeAgo } from '../utils'

export default function EnvironmentCard({ env }) {
  const isLive = env.status === 'active'
  const metrics = isLive ? dummyMetrics(env.uuid) : null

  return (
    <Link to={`/environments/${env.uuid}`} className="env-card">
      <div className="env-card-top">
        <div className="env-card-title">
          <span className="env-name">{env.name}</span>
          {env.kind === 'dummy' && <span className="demo-badge">DEMO</span>}
        </div>
        <StatusPill status={env.status} />
      </div>

      <div className="env-card-specs">
        <div className="env-spec">
          <span className="env-spec-value">{env.requested_server_count}</span>
          <span className="env-spec-label">Servers</span>
        </div>
        <div className="env-spec">
          <span className="env-spec-value">{env.total_gpus}</span>
          <span className="env-spec-label">GPUs</span>
        </div>
        <div className="env-spec">
          <span className="env-spec-value">{env.netris_vpc_name ? '1' : '—'}</span>
          <span className="env-spec-label">VPC</span>
        </div>
      </div>

      {isLive ? (
        <div className="env-card-metrics">
          <div className="env-metric-row">
            <span>GPU utilization</span>
            <span className="env-metric-value">{metrics.gpuUtilPct}%</span>
          </div>
          <div className="env-metric-bar">
            <div className="env-metric-bar-fill" style={{ width: `${metrics.gpuUtilPct}%` }} />
          </div>
          <div className="env-metric-foot">
            <span>{metrics.netThroughputGbps} Gbps throughput</span>
            <span>{metrics.avgTempC}°C avg temp</span>
          </div>
        </div>
      ) : (
        <div className="env-card-pending">{env.status_detail || 'Waiting to start…'}</div>
      )}

      <div className="env-card-footer">Updated {timeAgo(env.updated_at)}</div>
    </Link>
  )
}
