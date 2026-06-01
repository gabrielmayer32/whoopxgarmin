import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts'

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-surface-2 border border-border rounded-xl p-3 text-sm">
      <p className="text-muted mb-2">{label}</p>
      {payload.map((p) => (
        <p key={p.name} style={{ color: p.color }} className="font-mono">
          {p.name}: {p.value != null ? `${p.value}h` : '—'}
        </p>
      ))}
    </div>
  )
}

export default function SleepChart({ data = [], source = 'garmin' }) {
  const prefix = source === 'whoop' ? 'whoop' : 'garmin'
  const accent = source === 'whoop' ? '#b44aff' : '#4a9eff'

  return (
    <div className="bg-surface rounded-2xl p-5 border border-border">
      <div className="flex items-center justify-between mb-4">
        <h3 className="metric-label">Sleep Breakdown</h3>
        <span className={`text-xs font-medium ${source === 'whoop' ? 'text-purple' : 'text-blue'}`}>
          {source === 'whoop' ? 'WHOOP' : 'Garmin'}
        </span>
      </div>
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={data} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#2a2a3a" />
          <XAxis
            dataKey="date"
            tick={{ fill: '#6b6b8a', fontSize: 11 }}
            tickFormatter={(v) => v.slice(5)}
          />
          <YAxis tick={{ fill: '#6b6b8a', fontSize: 11 }} unit="h" />
          <Tooltip content={<CustomTooltip />} />
          <Legend
            formatter={(v) => <span style={{ color: '#6b6b8a', fontSize: 12 }}>{v}</span>}
          />
          <Bar dataKey={`${prefix}_deep_hours`} name="Deep" stackId="a" fill="#4a9eff" radius={0} />
          <Bar dataKey={`${prefix}_rem_hours`} name="REM" stackId="a" fill={accent} radius={0} />
          <Bar
            dataKey={`${prefix}_sleep_hours`}
            name="Light"
            stackId="a"
            fill="#2a2a3a"
            radius={[4, 4, 0, 0]}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
