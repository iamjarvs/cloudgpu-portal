// Small hand-rolled line-icon set (no external icon font/library — keeps the
// app free of another network dependency). Consistent 20x20 viewBox,
// stroke-based, currentColor so icons pick up their container's text color.
const STROKE = { fill: 'none', stroke: 'currentColor', strokeWidth: 1.6, strokeLinecap: 'round', strokeLinejoin: 'round' }

const PATHS = {
  grid: (
    <>
      <rect x="3" y="3" width="6.5" height="6.5" rx="1.2" {...STROKE} />
      <rect x="10.5" y="3" width="6.5" height="6.5" rx="1.2" {...STROKE} />
      <rect x="3" y="10.5" width="6.5" height="6.5" rx="1.2" {...STROKE} />
      <rect x="10.5" y="10.5" width="6.5" height="6.5" rx="1.2" {...STROKE} />
    </>
  ),
  server: (
    <>
      <rect x="3" y="3.5" width="14" height="5.5" rx="1.2" {...STROKE} />
      <rect x="3" y="11" width="14" height="5.5" rx="1.2" {...STROKE} />
      <circle cx="6" cy="6.25" r="0.9" fill="currentColor" />
      <circle cx="6" cy="13.75" r="0.9" fill="currentColor" />
    </>
  ),
  cpu: (
    <>
      <rect x="6" y="6" width="8" height="8" rx="1" {...STROKE} />
      <rect x="8.3" y="8.3" width="3.4" height="3.4" rx="0.5" {...STROKE} />
      <line x1="6" y1="2.5" x2="6" y2="5" {...STROKE} />
      <line x1="10" y1="2.5" x2="10" y2="5" {...STROKE} />
      <line x1="14" y1="2.5" x2="14" y2="5" {...STROKE} />
      <line x1="6" y1="15" x2="6" y2="17.5" {...STROKE} />
      <line x1="10" y1="15" x2="10" y2="17.5" {...STROKE} />
      <line x1="14" y1="15" x2="14" y2="17.5" {...STROKE} />
      <line x1="2.5" y1="6" x2="5" y2="6" {...STROKE} />
      <line x1="2.5" y1="10" x2="5" y2="10" {...STROKE} />
      <line x1="2.5" y1="14" x2="5" y2="14" {...STROKE} />
      <line x1="15" y1="6" x2="17.5" y2="6" {...STROKE} />
      <line x1="15" y1="10" x2="17.5" y2="10" {...STROKE} />
      <line x1="15" y1="14" x2="17.5" y2="14" {...STROKE} />
    </>
  ),
  network: (
    <>
      <circle cx="10" cy="4" r="2" {...STROKE} />
      <circle cx="4" cy="16" r="2" {...STROKE} />
      <circle cx="16" cy="16" r="2" {...STROKE} />
      <line x1="9" y1="5.6" x2="5" y2="14.2" {...STROKE} />
      <line x1="11" y1="5.6" x2="15" y2="14.2" {...STROKE} />
    </>
  ),
  database: (
    <>
      <ellipse cx="10" cy="5" rx="6.5" ry="2.4" {...STROKE} />
      <path d="M3.5 5 V15 C3.5 16.3 6.4 17.4 10 17.4 C13.6 17.4 16.5 16.3 16.5 15 V5" {...STROKE} />
      <path d="M3.5 10 C3.5 11.3 6.4 12.4 10 12.4 C13.6 12.4 16.5 11.3 16.5 10" {...STROKE} />
    </>
  ),
  barChart: (
    <>
      <line x1="3.5" y1="16.5" x2="16.5" y2="16.5" {...STROKE} />
      <rect x="5" y="10.5" width="3" height="6" rx="0.6" {...STROKE} />
      <rect x="8.7" y="6.5" width="3" height="10" rx="0.6" {...STROKE} />
      <rect x="12.4" y="3" width="3" height="13.5" rx="0.6" {...STROKE} />
    </>
  ),
  activity: <polyline points="2.5,10 6,10 8,4 12,16 14,10 17.5,10" {...STROKE} />,
  shoppingBag: (
    <>
      <path d="M5 7 H15 L14.3 17 H5.7 Z" {...STROKE} />
      <path d="M7.2 7 V5.2 C7.2 3.4 8.5 2.5 10 2.5 C11.5 2.5 12.8 3.4 12.8 5.2 V7" {...STROKE} />
    </>
  ),
  shield: (
    <>
      <path d="M10 2.5 L16.5 5 V9.5 C16.5 13.5 13.7 16.4 10 17.5 C6.3 16.4 3.5 13.5 3.5 9.5 V5 Z" {...STROKE} />
      <polyline points="7.2,10 9.2,12 13,7.5" {...STROKE} />
    </>
  ),
  creditCard: (
    <>
      <rect x="2.5" y="4.5" width="15" height="11" rx="1.4" {...STROKE} />
      <line x1="2.5" y1="8" x2="17.5" y2="8" {...STROKE} />
      <line x1="5" y1="12" x2="9" y2="12" {...STROKE} />
    </>
  ),
  user: (
    <>
      <circle cx="10" cy="6.5" r="3.2" {...STROKE} />
      <path d="M3.5 17 C3.5 13 6.4 11 10 11 C13.6 11 16.5 13 16.5 17" {...STROKE} />
    </>
  ),
  settings: (
    <>
      <rect x="8.95" y="1.7" width="2.1" height="2" rx="0.5" transform="rotate(0 10 10)" fill="currentColor" />
      <rect x="8.95" y="1.7" width="2.1" height="2" rx="0.5" transform="rotate(45 10 10)" fill="currentColor" />
      <rect x="8.95" y="1.7" width="2.1" height="2" rx="0.5" transform="rotate(90 10 10)" fill="currentColor" />
      <rect x="8.95" y="1.7" width="2.1" height="2" rx="0.5" transform="rotate(135 10 10)" fill="currentColor" />
      <rect x="8.95" y="1.7" width="2.1" height="2" rx="0.5" transform="rotate(180 10 10)" fill="currentColor" />
      <rect x="8.95" y="1.7" width="2.1" height="2" rx="0.5" transform="rotate(225 10 10)" fill="currentColor" />
      <rect x="8.95" y="1.7" width="2.1" height="2" rx="0.5" transform="rotate(270 10 10)" fill="currentColor" />
      <rect x="8.95" y="1.7" width="2.1" height="2" rx="0.5" transform="rotate(315 10 10)" fill="currentColor" />
      <circle cx="10" cy="10" r="6.3" {...STROKE} />
      <circle cx="10" cy="10" r="2.3" {...STROKE} />
    </>
  ),
  helpCircle: (
    <>
      <circle cx="10" cy="10" r="7.5" {...STROKE} />
      <path d="M7.8 7.8c0-1.4 1-2.3 2.2-2.3s2.2.8 2.2 2c0 1.5-2.2 1.6-2.2 3.3" {...STROKE} />
      <circle cx="10" cy="14" r="0.15" fill="currentColor" stroke="currentColor" strokeWidth="1.4" />
    </>
  ),
  bell: (
    <>
      <path d="M10 3.2c-2.4 0-4 1.9-4 4.4v2.7l-1.4 2.7h10.8L14 10.3V7.6c0-2.5-1.6-4.4-4-4.4Z" {...STROKE} />
      <path d="M8.3 15.8a1.9 1.9 0 0 0 3.4 0" {...STROKE} />
    </>
  ),
  search: (
    <>
      <circle cx="8.7" cy="8.7" r="5.2" {...STROKE} />
      <line x1="12.6" y1="12.6" x2="17" y2="17" {...STROKE} />
    </>
  ),
  chevronDown: <polyline points="5,7.5 10,12.5 15,7.5" {...STROKE} />,
  chevronRight: <polyline points="7.5,5 12.5,10 7.5,15" {...STROKE} />,
  logOut: (
    <>
      <path d="M8 3.5H4.8A1.3 1.3 0 0 0 3.5 4.8v10.4a1.3 1.3 0 0 0 1.3 1.3H8" {...STROKE} />
      <polyline points="12.5,6.5 16.5,10 12.5,13.5" {...STROKE} />
      <line x1="16.5" y1="10" x2="7.5" y2="10" {...STROKE} />
    </>
  ),
  plus: (
    <>
      <line x1="10" y1="4" x2="10" y2="16" {...STROKE} />
      <line x1="4" y1="10" x2="16" y2="10" {...STROKE} />
    </>
  ),
  check: <polyline points="4,10.5 8,14.5 16,5.5" {...STROKE} />,
  x: (
    <>
      <line x1="5" y1="5" x2="15" y2="15" {...STROKE} />
      <line x1="15" y1="5" x2="5" y2="15" {...STROKE} />
    </>
  ),
  home: (
    <>
      <path d="M3.2 9.5 L10 3.5 L16.8 9.5" {...STROKE} />
      <path d="M5 8.5V16.5H15V8.5" {...STROKE} />
    </>
  ),
  rocket: (
    <>
      <path d="M10 2.8c2.4 1.3 3.8 4 3.8 7.2 0 1.6-.4 3-1 4.2l-2.8 2.3-2.8-2.3c-.6-1.2-1-2.6-1-4.2 0-3.2 1.4-5.9 3.8-7.2Z" {...STROKE} />
      <circle cx="10" cy="9" r="1.4" {...STROKE} />
      <path d="M7 13.5l-2 3.7M13 13.5l2 3.7" {...STROKE} />
    </>
  ),
  gpu: (
    <>
      <rect x="2.5" y="6" width="15" height="8" rx="1.2" {...STROKE} />
      <circle cx="6.3" cy="10" r="1.7" {...STROKE} />
      <line x1="10.5" y1="8" x2="15" y2="8" {...STROKE} />
      <line x1="10.5" y1="10" x2="15" y2="10" {...STROKE} />
      <line x1="10.5" y1="12" x2="15" y2="12" {...STROKE} />
    </>
  ),
  clock: (
    <>
      <circle cx="10" cy="10" r="7.5" {...STROKE} />
      <polyline points="10,5.8 10,10 13.2,12" {...STROKE} />
    </>
  ),
  globe: (
    <>
      <circle cx="10" cy="10" r="7.5" {...STROKE} />
      <ellipse cx="10" cy="10" rx="3.2" ry="7.5" {...STROKE} />
      <line x1="2.5" y1="10" x2="17.5" y2="10" {...STROKE} />
    </>
  ),
  trendUp: (
    <>
      <polyline points="3,14 8,8.5 11.5,12 17,5.5" {...STROKE} />
      <polyline points="12,5.5 17,5.5 17,10.5" {...STROKE} />
    </>
  ),
  trendDown: (
    <>
      <polyline points="3,6 8,11.5 11.5,8 17,14.5" {...STROKE} />
      <polyline points="12,14.5 17,14.5 17,9.5" {...STROKE} />
    </>
  ),
}

export default function Icon({ name, size = 18, className = '' }) {
  const content = PATHS[name]
  if (!content) return null
  return (
    <svg width={size} height={size} viewBox="0 0 20 20" className={`icon ${className}`} aria-hidden="true">
      {content}
    </svg>
  )
}
