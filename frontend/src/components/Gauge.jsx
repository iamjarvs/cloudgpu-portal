// Half-circle arc gauge, pure inline SVG (no chart library dependency).
export default function Gauge({ value, size = 128, label, color = 'var(--coral)' }) {
  const clamped = Math.max(0, Math.min(100, value))
  const radius = size / 2 - 10
  const cx = size / 2
  const cy = size / 2
  const circumference = Math.PI * radius
  const offset = circumference * (1 - clamped / 100)

  return (
    <div className="gauge" style={{ width: size }}>
      <svg width={size} height={size / 2 + 16} viewBox={`0 0 ${size} ${size / 2 + 16}`}>
        <path
          d={`M 10 ${cy} A ${radius} ${radius} 0 0 1 ${size - 10} ${cy}`}
          fill="none"
          stroke="var(--border)"
          strokeWidth="10"
          strokeLinecap="round"
        />
        <path
          d={`M 10 ${cy} A ${radius} ${radius} 0 0 1 ${size - 10} ${cy}`}
          fill="none"
          stroke={color}
          strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          style={{ transition: 'stroke-dashoffset 0.6s ease' }}
        />
      </svg>
      <div className="gauge-value">{Math.round(clamped)}%</div>
      {label && <div className="gauge-label">{label}</div>}
    </div>
  )
}
