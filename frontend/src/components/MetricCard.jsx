export default function MetricCard({ label, value, unit, source, color, sub, loading }) {
  const sourceColor = source === 'whoop' ? 'text-purple' : source === 'garmin' ? 'text-blue' : 'text-muted'
  const sourceLabel = source === 'whoop' ? 'WHOOP' : source === 'garmin' ? 'Garmin' : source || ''

  const scoreColor =
    color === 'green' ? 'text-green' :
    color === 'amber' ? 'text-amber' :
    color === 'red' ? 'text-red' :
    color === 'blue' ? 'text-blue' :
    color === 'purple' ? 'text-purple' :
    'text-white'

  return (
    <div className="bg-surface rounded-2xl p-5 flex flex-col gap-3 border border-border">
      <div className="flex items-center justify-between">
        <span className="metric-label">{label}</span>
        {sourceLabel && (
          <span className={`text-xs font-medium ${sourceColor}`}>{sourceLabel}</span>
        )}
      </div>
      {loading ? (
        <div className="h-9 w-24 bg-surface-2 animate-pulse rounded-lg" />
      ) : (
        <div className={`font-mono text-3xl font-medium tracking-tight ${scoreColor}`}>
          {value !== undefined && value !== null ? (
            <>
              {typeof value === 'number' ? value.toLocaleString() : value}
              {unit && <span className="text-lg text-muted ml-1">{unit}</span>}
            </>
          ) : (
            <span className="text-muted text-2xl">—</span>
          )}
        </div>
      )}
      {sub && <p className="text-xs text-muted leading-relaxed">{sub}</p>}
    </div>
  )
}
