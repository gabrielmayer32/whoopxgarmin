import { colors } from '../colors.js'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts'

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  const total = payload.reduce((s, p) => s + (p.value || 0), 0)
  return (
    <div className="bg-surface-2 border border-border rounded-xl p-3 text-sm">
      <p className="text-muted mb-2">{label}</p>
      {payload.map((p) => (
        <p key={p.name} style={{ color: p.fill }} className="font-mono">
          {p.name}: {p.value != null ? `${p.value.toFixed(1)}h` : '—'}
        </p>
      ))}
      <p className="text-muted font-mono mt-1 pt-1 border-t border-border">
        Total: {total.toFixed(1)}h
      </p>
    </div>
  )
}

export default function SleepChart({ data = [], source = 'garmin' }) {
  const prefix = source === 'whoop' ? 'whoop' : 'garmin'

  const chartData = data.map(d => ({
    ...d,
    _deep:  d[`${prefix}_deep_hours`]  || 0,
    _rem:   d[`${prefix}_rem_hours`]   || 0,
    _light: d[`${prefix}_light_hours`] || Math.max(0,
      (d[`${prefix}_sleep_hours`] || 0) -
      (d[`${prefix}_deep_hours`]  || 0) -
      (d[`${prefix}_rem_hours`]   || 0)
    ),
  }))

  return (
    <div className="bg-surface rounded-2xl p-5 border border-border">
      <div className="flex items-center justify-between mb-4">
        <h3 className="metric-label">Sleep Breakdown</h3>
        <span className={`text-xs font-medium ${source === 'whoop' ? 'text-purple' : 'text-blue'}`}>
          {source === 'whoop' ? 'WHOOP' : 'Garmin'}
        </span>
      </div>
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={chartData} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={colors.border} />
          <XAxis dataKey="date" tick={{ fill: colors.muted, fontSize: 11 }} />
          <YAxis tick={{ fill: colors.muted, fontSize: 11 }} unit="h" />
          <Tooltip content={<CustomTooltip />} />
          <Legend formatter={(v) => <span style={{ color: colors.muted, fontSize: 12 }}>{v}</span>} />
          <Bar dataKey="_deep"  name="Deep"  stackId="a" fill={colors.blue}   radius={0} />
          <Bar dataKey="_rem"   name="REM"   stackId="a" fill={colors.purple} radius={0} />
          <Bar dataKey="_light" name="Light" stackId="a" fill={colors.muted}  radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
