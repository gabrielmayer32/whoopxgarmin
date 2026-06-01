import { useEffect, useState } from 'react'
import { fetchRecoveryTimeline, fetchTrends, fetchStrainRecoveryCorrelation } from '../api/client'
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ResponsiveContainer, ReferenceLine, ScatterChart, Scatter,
} from 'recharts'
import MetricCard from '../components/MetricCard'
import DateRangeSelector from '../components/DateRangeSelector'
import useDateRange from '../hooks/useDateRange'
import aggregateByRange from '../utils/aggregateByRange'

const ChartTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-surface-2 border border-border rounded-xl p-3 text-sm">
      <p className="text-muted mb-2">{label}</p>
      {payload.map((p) => (
        <p key={p.name} style={{ color: p.color }} className="font-mono text-xs">
          {p.name}: {p.value != null ? (typeof p.value === 'number' ? p.value.toFixed(1) : p.value) : '—'}
        </p>
      ))}
    </div>
  )
}

export default function Recovery() {
  const { preset, days, startDate, offset, windowLabel, canGoForward, select, goBack, goForward } = useDateRange('1M')
  const [timeline, setTimeline] = useState([])
  const [trends, setTrends] = useState([])
  const [strainCorr, setStrainCorr] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    Promise.all([
      fetchRecoveryTimeline(days, startDate),
      fetchTrends(days, startDate),
      fetchStrainRecoveryCorrelation(days, startDate),
    ])
      .then(([t, tr, sc]) => {
        setTimeline(t)
        setTrends(tr)
        setStrainCorr(sc)
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [days, startDate])

  const todayIso = new Date().toISOString().slice(0, 10)
  const todayEntry = timeline.find(r => r.date === todayIso) || {}

  const validRecovery = timeline.filter(r => r.recovery_score)
  const avgRecovery = validRecovery.length
    ? Math.round(validRecovery.reduce((s, r) => s + r.recovery_score, 0) / validRecovery.length)
    : null
  const maxRecovery = validRecovery.length ? Math.max(...validRecovery.map(r => r.recovery_score)) : null
  const minRecovery = validRecovery.length ? Math.min(...validRecovery.map(r => r.recovery_score)) : null

  const validHrv = timeline.filter(r => r.hrv)
  const avgHrv = validHrv.length
    ? parseFloat((validHrv.reduce((s, r) => s + r.hrv, 0) / validHrv.length).toFixed(1))
    : null
  const maxHrv = validHrv.length ? Math.max(...validHrv.map(r => r.hrv)) : null
  const minHrv = validHrv.length ? Math.min(...validHrv.map(r => r.hrv)) : null

  const isCurrent = offset === 0

  const correlationData = strainCorr
  const aggTimeline = aggregateByRange(timeline, days)
  const aggTrends = aggregateByRange(trends, days)

  return (
    <div className="max-w-6xl mx-auto px-4 py-6 flex flex-col gap-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h1 className="text-xl font-semibold">Recovery</h1>
        <DateRangeSelector
          preset={preset}
          offset={offset}
          windowLabel={windowLabel}
          canGoForward={canGoForward}
          onSelect={select}
          onBack={goBack}
          onForward={goForward}
        />
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {isCurrent ? (
          <>
            <MetricCard
              label="Today's Recovery"
              value={todayEntry.recovery_score}
              unit="%"
              source="whoop"
              color={todayEntry.recovery_score >= 67 ? 'green' : todayEntry.recovery_score >= 34 ? 'amber' : 'red'}
              sub={avgRecovery != null ? `${preset} avg ${avgRecovery}%` : undefined}
              loading={loading}
            />
            <MetricCard
              label={`${preset} Avg Recovery`}
              value={avgRecovery}
              unit="%"
              source="whoop"
              sub={maxRecovery != null ? `↑ ${maxRecovery}%  ↓ ${minRecovery}%` : undefined}
              loading={loading}
            />
            <MetricCard
              label="Today's HRV"
              value={todayEntry.hrv != null ? +todayEntry.hrv.toFixed(1) : null}
              unit="ms"
              source="whoop"
              sub={avgHrv != null ? `${preset} avg ${avgHrv} ms` : undefined}
              loading={loading}
            />
            <MetricCard
              label={`${preset} Avg HRV`}
              value={avgHrv}
              unit="ms"
              source="whoop"
              sub={maxHrv != null ? `↑ ${maxHrv.toFixed(1)}  ↓ ${minHrv.toFixed(1)} ms` : undefined}
              loading={loading}
            />
          </>
        ) : (
          <>
            <MetricCard
              label="Avg Recovery"
              value={avgRecovery}
              unit="%"
              source="whoop"
              color={avgRecovery >= 67 ? 'green' : avgRecovery >= 34 ? 'amber' : avgRecovery != null ? 'red' : null}
              sub={maxRecovery != null ? `↑ ${maxRecovery}%  ↓ ${minRecovery}%` : undefined}
              loading={loading}
            />
            <MetricCard
              label="Days Tracked"
              value={validRecovery.length || null}
              source="whoop"
              sub={windowLabel}
              loading={loading}
            />
            <MetricCard
              label="Avg HRV"
              value={avgHrv}
              unit="ms"
              source="whoop"
              sub={maxHrv != null ? `↑ ${maxHrv.toFixed(1)}  ↓ ${minHrv.toFixed(1)} ms` : undefined}
              loading={loading}
            />
            <MetricCard
              label="Best Recovery"
              value={maxRecovery}
              unit="%"
              source="whoop"
              color={maxRecovery >= 67 ? 'green' : maxRecovery >= 34 ? 'amber' : maxRecovery != null ? 'red' : null}
              sub={maxHrv != null ? `Best HRV ${maxHrv.toFixed(1)} ms` : undefined}
              loading={loading}
            />
          </>
        )}
      </div>

      {/* Recovery timeline */}
      <div className="bg-surface rounded-2xl p-5 border border-border">
        <div className="flex items-center justify-between mb-4">
          <h3 className="metric-label">Recovery Timeline</h3>
          <span className="text-xs font-medium text-purple">WHOOP</span>
        </div>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={aggTimeline} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#2a2a3a" />
            <XAxis dataKey="date" tick={{ fill: '#6b6b8a', fontSize: 10 }} />
            <YAxis tick={{ fill: '#6b6b8a', fontSize: 11 }} domain={[0, 100]} />
            <Tooltip content={<ChartTooltip />} />
            <ReferenceLine y={67} stroke="#00e5a0" strokeDasharray="4 4" strokeOpacity={0.5} />
            <ReferenceLine y={34} stroke="#f5a623" strokeDasharray="4 4" strokeOpacity={0.5} />
            <Bar dataKey="recovery_score" name="Recovery %" fill="#b44aff" radius={[3, 3, 0, 0]} maxBarSize={20} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* HRV trend */}
      <div className="bg-surface rounded-2xl p-5 border border-border">
        <div className="flex items-center justify-between mb-4">
          <h3 className="metric-label">HRV Trend</h3>
          <span className="text-xs font-medium text-purple">WHOOP</span>
        </div>
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={aggTrends} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#2a2a3a" />
            <XAxis dataKey="date" tick={{ fill: '#6b6b8a', fontSize: 10 }} />
            <YAxis tick={{ fill: '#6b6b8a', fontSize: 11 }} domain={['auto', 'auto']} />
            <Tooltip content={<ChartTooltip />} />
            <Line type="monotone" dataKey="whoop_hrv" name="HRV (ms)" stroke="#b44aff" strokeWidth={2} dot={false} connectNulls />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Sleep performance */}
      <div className="bg-surface rounded-2xl p-5 border border-border">
        <div className="flex items-center justify-between mb-4">
          <h3 className="metric-label">Sleep Performance</h3>
          <span className="text-xs font-medium text-purple">WHOOP</span>
        </div>
        <ResponsiveContainer width="100%" height={180}>
          <LineChart data={aggTrends} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#2a2a3a" />
            <XAxis dataKey="date" tick={{ fill: '#6b6b8a', fontSize: 10 }} />
            <YAxis tick={{ fill: '#6b6b8a', fontSize: 11 }} domain={[0, 100]} />
            <Tooltip content={<ChartTooltip />} />
            <ReferenceLine y={85} stroke="#00e5a0" strokeDasharray="4 4" strokeOpacity={0.5} />
            <Line type="monotone" dataKey="whoop_sleep_performance" name="Sleep %" stroke="#b44aff" strokeWidth={2} dot={false} connectNulls />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Strain vs Recovery scatter */}
      {correlationData.length > 0 && (
        <div className="bg-surface rounded-2xl p-5 border border-border">
          <div className="flex items-center justify-between mb-1">
            <h3 className="metric-label">Strain → Next-Day Recovery</h3>
            <span className="text-xs font-medium text-purple">WHOOP</span>
          </div>
          <p className="text-xs text-muted mb-4">Each point = day's strain vs the following morning's recovery score</p>
          <ResponsiveContainer width="100%" height={220}>
            <ScatterChart margin={{ top: 5, right: 10, left: -20, bottom: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2a2a3a" />
              <XAxis dataKey="strain" name="Strain" type="number" tick={{ fill: '#6b6b8a', fontSize: 11 }}
                label={{ value: 'Strain', fill: '#6b6b8a', fontSize: 11, position: 'insideBottom', offset: -10 }} />
              <YAxis dataKey="next_day_recovery" name="Next-day Recovery %" type="number" tick={{ fill: '#6b6b8a', fontSize: 11 }} domain={[0, 100]} />
              <Tooltip cursor={{ strokeDasharray: '3 3' }} content={({ active, payload }) => {
                if (!active || !payload?.length) return null
                const d = payload[0]?.payload
                return (
                  <div className="bg-surface-2 border border-border rounded-xl p-3 text-sm">
                    <p className="text-muted text-xs mb-1">{d?.date} → next morning</p>
                    <p className="text-purple font-mono text-xs">Strain: {d?.strain?.toFixed(1)}</p>
                    <p className="text-green font-mono text-xs">Next-day recovery: {d?.next_day_recovery}%</p>
                  </div>
                )
              }} />
              <Scatter data={correlationData} fill="#b44aff" fillOpacity={0.75} />
            </ScatterChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}
