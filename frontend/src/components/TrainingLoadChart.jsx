import { colors } from '../colors.js'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts'

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-surface-2 border border-border rounded-xl p-3 text-sm">
      <p className="text-muted mb-2">{label}</p>
      {payload.map((p) => (
        <p key={p.name} style={{ color: p.color }} className="font-mono">
          {p.name}: {p.value != null ? p.value.toFixed(0) : '—'}
        </p>
      ))}
    </div>
  )
}

export default function TrainingLoadChart({ data = [] }) {
  return (
    <div className="bg-surface rounded-2xl p-5 border border-border">
      <h3 className="metric-label mb-4">Training Load (Garmin)</h3>
      <ResponsiveContainer width="100%" height={200}>
        <AreaChart data={data} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
          <defs>
            <linearGradient id="loadGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={colors.blue} stopOpacity={0.3} />
              <stop offset="95%" stopColor={colors.blue} stopOpacity={0} />
            </linearGradient>
            <linearGradient id="acuteGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={colors.amber} stopOpacity={0.3} />
              <stop offset="95%" stopColor={colors.amber} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke={colors.border} />
          <XAxis
            dataKey="date"
            tick={{ fill: colors.muted, fontSize: 11 }}
          />
          <YAxis tick={{ fill: colors.muted, fontSize: 11 }} />
          <Tooltip content={<CustomTooltip />} />
          <Legend
            formatter={(v) => <span style={{ color: colors.muted, fontSize: 12 }}>{v}</span>}
          />
          <Area
            type="monotone"
            dataKey="training_load"
            name="7-Day Load"
            stroke={colors.blue}
            fill="url(#loadGrad)"
            strokeWidth={2}
            connectNulls
          />
          <Area
            type="monotone"
            dataKey="acute_load"
            name="Acute Load"
            stroke={colors.amber}
            fill="url(#acuteGrad)"
            strokeWidth={2}
            connectNulls
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}
