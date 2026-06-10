import { colors } from '../colors.js'
import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

export default function CorrelationChart({ data = [], xKey, yKey, xLabel, yLabel, color = colors.purple, title, subtitle }) {
  const filtered = data.filter(d => d[xKey] != null && d[yKey] != null)

  const cutoff = new Date()
  cutoff.setDate(cutoff.getDate() - 7)
  const cutoffStr = cutoff.toISOString().slice(0, 10)

  const older = filtered.filter(d => !d.date || d.date < cutoffStr)
  const recent = filtered.filter(d => d.date && d.date >= cutoffStr)

  const tooltip = ({ active, payload }) => {
    if (!active || !payload?.length) return null
    const d = payload[0]?.payload
    const isRecent = d?.date && d.date >= cutoffStr
    return (
      <div className="bg-surface-2 border border-border rounded-xl p-3 text-sm">
        <p className="text-muted text-xs mb-1">{d?.date}{isRecent ? ' · last 7d' : ''}</p>
        <p style={{ color }} className="font-mono text-xs">{xLabel}: {d?.[xKey]?.toFixed(1)}</p>
        <p className="text-blue font-mono text-xs">{yLabel}: {d?.[yKey]?.toFixed(1)}</p>
      </div>
    )
  }

  return (
    <div className="bg-surface rounded-2xl p-5 border border-border">
      <div className="flex items-start justify-between mb-4">
        <div>
          <h3 className="metric-label">{title}</h3>
          {subtitle && <p className="text-xs text-muted mt-0.5">{subtitle}</p>}
        </div>
        {recent.length > 0 && (
          <div className="flex items-center gap-1.5 shrink-0 mt-0.5">
            <span className="w-2 h-2 rounded-full" style={{ background: colors.amber }} />
            <span className="text-[10px] text-muted">last 7d</span>
          </div>
        )}
      </div>
      {filtered.length < 3 ? (
        <p className="text-muted text-sm py-8 text-center">Not enough data yet — keep riding</p>
      ) : (
        <ResponsiveContainer width="100%" height={200}>
          <ScatterChart margin={{ top: 5, right: 10, left: -10, bottom: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={colors.border} />
            <XAxis
              dataKey={xKey}
              name={xLabel}
              type="number"
              tick={{ fill: colors.muted, fontSize: 11 }}
              label={{ value: xLabel, fill: colors.muted, fontSize: 11, position: 'insideBottom', offset: -10 }}
            />
            <YAxis
              dataKey={yKey}
              name={yLabel}
              type="number"
              tick={{ fill: colors.muted, fontSize: 11 }}
              label={{ value: yLabel, fill: colors.muted, fontSize: 11, angle: -90, position: 'insideLeft', offset: 15 }}
            />
            <Tooltip cursor={{ strokeDasharray: '3 3' }} content={tooltip} />
            <Scatter data={older} fill={color} fillOpacity={0.3} r={3} />
            <Scatter data={recent} fill={colors.amber} fillOpacity={1} r={5} stroke={colors.amber} strokeWidth={1} />
          </ScatterChart>
        </ResponsiveContainer>
      )}
    </div>
  )
}
