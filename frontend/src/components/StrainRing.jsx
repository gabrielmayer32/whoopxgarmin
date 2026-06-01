export default function StrainRing({ strain }) {
  const maxStrain = 21
  const pct = strain != null ? Math.min(strain / maxStrain, 1) : 0
  const r = 40
  const circ = 2 * Math.PI * r
  const offset = circ * (1 - pct)

  const color =
    strain == null ? '#2a2a3a' :
    strain < 10 ? '#00e5a0' :
    strain < 15 ? '#f5a623' :
    '#ff4757'

  return (
    <div className="bg-surface rounded-2xl p-5 border border-border flex flex-col items-center gap-3">
      <span className="metric-label">WHOOP Strain</span>
      <div className="relative w-24 h-24">
        <svg viewBox="0 0 100 100" className="w-full h-full -rotate-90">
          <circle cx="50" cy="50" r={r} fill="none" stroke="#2a2a3a" strokeWidth="10" />
          <circle
            cx="50"
            cy="50"
            r={r}
            fill="none"
            stroke={color}
            strokeWidth="10"
            strokeDasharray={circ}
            strokeDashoffset={offset}
            strokeLinecap="round"
            style={{ transition: 'stroke-dashoffset 0.5s ease' }}
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="font-mono text-xl font-medium" style={{ color }}>
            {strain != null ? strain.toFixed(1) : '—'}
          </span>
        </div>
      </div>
      <p className="text-xs text-muted">out of 21</p>
    </div>
  )
}
