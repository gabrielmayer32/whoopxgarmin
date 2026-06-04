import { useState } from 'react'
import { colors } from '../colors.js'
import {
  ComposedChart, Line, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, ReferenceLine,
} from 'recharts'

const VARIANTS = [
  { key: 'classic', label: 'Classic TSS', desc: 'Raw Garmin TSS only' },
  { key: 'augmented', label: 'Augmented', desc: 'TSS × Whoop recovery modifier' },
  { key: 'hrv', label: 'HRV-Adjusted', desc: 'TSS × HRV deviation from 30-day baseline' },
]

const PREFIX = { classic: '', augmented: 'aug_', hrv: 'hrv_' }

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-surface-2 border border-border rounded-xl p-3 text-sm min-w-[160px]">
      <p className="text-muted mb-2 text-xs">{label}</p>
      {payload.map((p) => (
        <p key={p.name} style={{ color: typeof p.color === 'string' && p.color.length > 7 ? p.color.slice(0, 7) : p.color }} className="font-mono text-xs">
          {p.name}: {p.value != null ? (typeof p.value === 'number' ? p.value.toFixed(1) : p.value) : '—'}
        </p>
      ))}
    </div>
  )
}

export default function PMCChart({ data = [] }) {
  const [variant, setVariant] = useState('classic')
  const p = PREFIX[variant]

  const chartData = data.map((d) => ({
    date: d.date,
    TSS: d.tss,
    Fitness: d[`${p}ctl`],
    Fatigue: d[`${p}atl`],
    Form: d[`${p}tsb`],
  }))

  return (
    <div className="bg-surface rounded-2xl p-5 border border-border">
      <div className="flex items-start justify-between gap-4 mb-4 flex-wrap">
        <div>
          <h3 className="metric-label">Performance Management Chart</h3>
          <p className="text-xs text-muted mt-0.5">
            Fitness (CTL 42d) · Fatigue (ATL 7d) · Form = Fitness − Fatigue
          </p>
        </div>
        <div className="flex gap-1">
          {VARIANTS.map((v) => (
            <button
              key={v.key}
              onClick={() => setVariant(v.key)}
              title={v.desc}
              className={`px-3 py-1 rounded-lg text-xs font-medium transition-colors border ${
                variant === v.key
                  ? 'bg-blue/20 text-blue border-blue/40'
                  : 'bg-transparent text-muted border-border hover:border-muted'
              }`}
            >
              {v.label}
            </button>
          ))}
        </div>
      </div>

      <ResponsiveContainer width="100%" height={280}>
        <ComposedChart data={chartData} margin={{ top: 5, right: 20, left: -20, bottom: 0 }}>
          <defs>
            <linearGradient id="tssGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={colors.blue} stopOpacity={0.25} />
              <stop offset="95%" stopColor={colors.blue} stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke={colors.border} />
          <XAxis dataKey="date" tick={{ fill: colors.muted, fontSize: 10 }} />
          <YAxis yAxisId="load" tick={{ fill: colors.muted, fontSize: 11 }} domain={['auto', 'auto']} />
          <YAxis yAxisId="tsb" orientation="right" tick={{ fill: colors.muted, fontSize: 11 }} domain={['auto', 'auto']} />
          <Tooltip content={<CustomTooltip />} />
          <Legend formatter={(v) => <span style={{ color: colors.muted, fontSize: 12 }}>{v}</span>} />
          <ReferenceLine yAxisId="tsb" y={0} stroke={colors.border} strokeDasharray="4 4" />

          {/* TSS bars in background */}
          <Bar yAxisId="load" dataKey="TSS" fill={colors.blue + '18'} stroke={colors.blue + '40'} strokeWidth={1} radius={[2, 2, 0, 0]} />

          {/* CTL = Fitness */}
          <Line yAxisId="load" type="monotone" dataKey="Fitness" stroke={colors.blue} strokeWidth={2.5} dot={false} connectNulls />

          {/* ATL = Fatigue */}
          <Line yAxisId="load" type="monotone" dataKey="Fatigue" stroke={colors.amber} strokeWidth={2} dot={false} connectNulls strokeDasharray="5 3" />

          {/* TSB = Form — plotted on right axis so it's centered around 0 */}
          <Line yAxisId="tsb" type="monotone" dataKey="Form" stroke={colors.green} strokeWidth={2} dot={false} connectNulls />
        </ComposedChart>
      </ResponsiveContainer>

      <div className="flex gap-4 mt-3 text-xs text-muted flex-wrap">
        <span><span style={{ color: colors.green }}>Form &gt; 0</span> = fresh (peak performance window)</span>
        <span><span style={{ color: colors.amber }}>Form &lt; −10</span> = fatigued</span>
        <span><span style={{ color: colors.blue }}>Fitness</span> = 42-day load</span>
      </div>
    </div>
  )
}
