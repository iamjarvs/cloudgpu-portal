import Icon from './Icon'

export default function StatCard({ icon, label, value, sublabel, trend }) {
  return (
    <div className="stat-card">
      <div className="stat-card-icon">
        <Icon name={icon} size={20} />
      </div>
      <div className="stat-card-body">
        <div className="stat-card-value">{value}</div>
        <div className="stat-card-label">{label}</div>
        {sublabel && <div className="stat-card-sub">{sublabel}</div>}
        {trend && (
          <div className={`stat-card-trend trend-${trend.direction}`}>
            <Icon name={trend.direction === 'up' ? 'trendUp' : 'trendDown'} size={12} />
            {trend.text}
          </div>
        )}
      </div>
    </div>
  )
}
