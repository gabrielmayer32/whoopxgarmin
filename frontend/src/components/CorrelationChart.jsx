import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts'

export default function CorrelationChart({ data = [], xKey, yKey, xLabel, yLabel, color = '#b44aff', title, subtitle }) {
  const filtered = data.filter(d => d[xKey] != null && d[yKey] != null)

  return (
    <div className="bg-surface rounded-2xl p-5 border border-border">
      <div className="mb-4">
        <h3 className="metric-label">{title}</h3>
        {subtitle && <p className="text-xs text-muted mt-0.5">{subtitle}</p>}
      </div>
      {filtered.length < 3 ? (
        <p className="text-muted text-sm py-8 text-center">Not enough data yet — keep riding</p>
      ) : (
        <ResponsiveContainer width="100%" height={200}>
          <ScatterChart margin={{ top: 5, right: 10, left: -10, bottom: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#2a2a3a" />
            <XAxis
              dataKey={xKey}
              name={xLabel}
              type="number"
              tick={{ fill: '#6b6b8a', fontSize: 11 }}
              label={{ value: xLabel, fill: '#6b6b8a', fontSize: 11, position: 'insideBottom', offset: -10 }}
            />
            <YAxis
              dataKey={yKey}
              name={yLabel}
              type="number"
              tick={{ fill: '#6b6b8a', fontSize: 11 }}
              label={{ value: yLabel, fill: '#6b6b8a', fontSize: 11, angle: -90, position: 'insideLeft', offset: 15 }}
            />
            <Tooltip cursor={{ strokeDasharray: '3 3' }} content={({ active, payload }) => {
              if (!active || !payload?.length) return null
              const d = payload[0]?.payload
              return (
                <div className="bg-surface-2 border border-border rounded-xl p-3 text-sm">
                  <p className="text-muted text-xs mb-1">{d?.date}</p>
                  <p style={{ color }} className="font-mono text-xs">{xLabel}: {d?.[xKey]?.toFixed(1)}</p>
                  <p className="text-blue font-mono text-xs">{yLabel}: {d?.[yKey]?.toFixed(1)}</p>
                </div>
              )
            }} />
            <Scatter data={filtered} fill={color} fillOpacity={0.75} />
          </ScatterChart>
        </ResponsiveContainer>
      )}
    </div>
  )
}
