export default function Logo({ size = 28 }) {
  return (
    <div className="logo-mark">
      <svg width={size} height={size} viewBox="0 0 100 100" aria-hidden="true">
        <polygon points="50,5 90,27 90,73 50,95 10,73 10,27" fill="#FF3B69" />
        <polygon points="50,25 72,37 72,63 50,75 28,63 28,37" fill="#050505" />
      </svg>
      <span className="logo-word">HELIOSGRID</span>
    </div>
  )
}
