import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts'

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-surface-2 border border-border rounded-xl p-3 text-sm">
      <p className="text-muted mb-2">{label}</p>
      {payload.map((p) => (
        <p key={p.name} style={{ color: p.color }} className="font-mono">
          {p.name}: {p.value != null ? `${p.value} ms` : '—'}
        </p>
      ))}
    </div>
  )
}

export default function HRVChart({ data = [] }) {
  return (
    <div className="bg-surface rounded-2xl p-5 border border-border">
      <div className="flex items-center justify-between mb-4">
        <h3 className="metric-label">HRV Trend</h3>
        <span className="text-xs font-medium text-purple">WHOOP</span>
      </div>
      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={data} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#2a2a3a" />
          <XAxis
            dataKey="date"
            tick={{ fill: '#6b6b8a', fontSize: 11 }}
            tickFormatter={(v) => v.slice(5)}
          />
          <YAxis tick={{ fill: '#6b6b8a', fontSize: 11 }} domain={['auto', 'auto']} />
          <Tooltip content={<CustomTooltip />} />
          <Line
            type="monotone"
            dataKey="whoop_hrv"
            name="HRV"
            stroke="#b44aff"
            strokeWidth={2}
            dot={{ fill: '#b44aff', r: 3 }}
            connectNulls
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
