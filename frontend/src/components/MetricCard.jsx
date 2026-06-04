import { colors } from '../colors.js'
import { LineChart, Line, ResponsiveContainer } from 'recharts'

export default function MetricCard({ label, value, unit, source, color, sub, loading, sparkline, yesterday, invertDelta }) {
  const sourceLabel = source === 'whoop' ? 'WHOOP' : source === 'garmin' ? 'Garmin' : source || ''

  const valueColor =
    color === 'green'  ? 'text-green'  :
    color === 'amber'  ? 'text-amber'  :
    color === 'red'    ? 'text-red'    :
    color === 'blue'   ? 'text-blue'   :
    color === 'purple' ? 'text-purple' :
    'text-white'

  const accentColor =
    color === 'green'  ? colors.green  :
    color === 'amber'  ? colors.amber  :
    color === 'red'    ? colors.red    :
    color === 'blue'   ? colors.blue   :
    color === 'purple' ? colors.purple :
    source === 'whoop'  ? colors.purple :
    source === 'garmin' ? colors.blue   :
    colors.border

  const sparkColor = accentColor

  // Delta vs yesterday
  let delta = null
  if (value != null && yesterday != null) {
    delta = value - yesterday
  }
  const deltaPositive = delta != null && delta >= 0
  const deltaColor = delta == null ? '' : (deltaPositive !== !!invertDelta) ? 'text-green' : 'text-red'
  const deltaSign = delta != null ? (delta >= 0 ? '+' : '−') : ''
  const deltaAbs = delta != null ? (Math.abs(delta) < 10 ? Math.abs(delta).toFixed(1) : Math.round(Math.abs(delta))) : null
  const deltaDisplay = deltaAbs != null ? `${deltaSign}${deltaAbs}` : null

  return (
    <div className="bg-surface rounded-2xl px-4 pt-4 pb-3 flex flex-col" style={{ boxShadow: `inset 3px 0 0 ${accentColor}` }}>
      {/* Label + source */}
      <div className="flex items-start justify-between gap-2 mb-2">
        <span className="metric-label leading-tight">{label}</span>
        {sourceLabel && (
          <span className="text-[10px] font-medium text-muted tracking-wider shrink-0 mt-0.5">
            {sourceLabel}
          </span>
        )}
      </div>

      {/* Value */}
      {loading ? (
        <div className="h-9 w-20 bg-surface-2 animate-pulse rounded-lg mb-3" />
      ) : (
        <div className={`font-mono text-3xl font-medium tracking-tight leading-none mb-2 ${valueColor}`}>
          {value !== undefined && value !== null ? (
            <>
              {typeof value === 'number' ? value.toLocaleString() : value}
              {unit && <span className="text-base font-normal text-muted ml-1">{unit}</span>}
            </>
          ) : (
            <span className="text-muted text-2xl">—</span>
          )}
        </div>
      )}

      {/* Delta + sparkline row */}
      {!loading && (sparkline?.length > 1 || deltaDisplay) && (
        <div className="flex items-center justify-between gap-2 mt-auto">
          {deltaDisplay ? (
            <span className={`text-[11px] font-mono ${deltaColor}`}>
              {deltaDisplay} {unit} vs yesterday
            </span>
          ) : <span />}
          {sparkline?.length > 1 && (
            <div style={{ width: 64, height: 28 }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={sparkline.map((v, i) => ({ v, i }))}>
                  <Line
                    type="monotone"
                    dataKey="v"
                    stroke={sparkColor}
                    strokeWidth={1.5}
                    dot={false}
                    isAnimationActive={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      )}

      {/* Sub-label */}
      {sub && <p className="text-[11px] text-muted leading-relaxed mt-1">{sub}</p>}
    </div>
  )
}
