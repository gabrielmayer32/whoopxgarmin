import { colors } from '../colors.js'
import { useEffect, useState } from 'react'
import { fetchDashboard, fetchTrends, fetchWhoopStatus, fetchWhoopGarminCorrelation, fetchStrainRecoveryCorrelation, fetchRecoveryPrediction } from '../api/client'
import MetricCard from '../components/MetricCard'
import HRVChart from '../components/HRVChart'
import SleepChart from '../components/SleepChart'
import ActivityFeed from '../components/ActivityFeed'
import StrainRing from '../components/StrainRing'
import InsightsPanel from '../components/InsightsPanel'
import CorrelationChart from '../components/CorrelationChart'
import DateRangeSelector from '../components/DateRangeSelector'
import useDateRange from '../hooks/useDateRange'
import aggregateByRange from '../utils/aggregateByRange'
import { Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend, ComposedChart, Line } from 'recharts'

function recoveryColor(score) {
  if (score == null) return null
  if (score >= 67) return 'green'
  if (score >= 34) return 'amber'
  return 'red'
}

function sleepColor(pct) {
  if (pct == null) return null
  if (pct >= 85) return 'green'
  if (pct >= 70) return 'amber'
  return 'red'
}

const ChartTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-surface-2 border border-border rounded-xl p-3 text-sm">
      <p className="text-muted mb-1 text-xs">{label}</p>
      {payload.map((p) => (
        <p key={p.name} style={{ color: p.color?.length > 7 ? p.color.slice(0, 7) : p.color }} className="font-mono text-xs">
          {p.name}: {p.value != null ? (typeof p.value === 'number' ? p.value.toFixed(1) : p.value) : '—'}
        </p>
      ))}
    </div>
  )
}

export default function Dashboard() {
  const { preset, days, startDate, offset, windowLabel, canGoForward, select, goBack, goForward } = useDateRange('1M')
  const [data, setData] = useState(null)
  const [trends, setTrends] = useState([])
  const [correlation, setCorrelation] = useState([])
  const [strainCorr, setStrainCorr] = useState([])
  const [prediction, setPrediction] = useState(null)
  const [loading, setLoading] = useState(true)
  const [whoopAuth, setWhoopAuth] = useState(null)

  useEffect(() => {
    setLoading(true)
    Promise.all([
      fetchDashboard(),
      fetchTrends(days, startDate),
      fetchWhoopStatus(),
      fetchWhoopGarminCorrelation(days, startDate),
      fetchStrainRecoveryCorrelation(days, startDate),
      fetchRecoveryPrediction(),
    ])
      .then(([dash, t, ws, corr, sc, pred]) => {
        setData(dash)
        setTrends(t)
        setWhoopAuth(ws.authorized)
        setCorrelation(corr)
        setStrainCorr(sc)
        setPrediction(pred)
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [days, startDate])

  const today = new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' })

  const recoveryVsTss = strainCorr

  const aggregatedTrends = aggregateByRange(trends, days)

  const overlayData = aggregatedTrends.map((t, i) => {
    const nextDay = aggregatedTrends[i + 1]
    return {
      date: t.date,
      training_load: t.garmin_training_load,
      next_recovery: nextDay?.whoop_recovery_score ?? null,
    }
  }).filter((_, i) => i < aggregatedTrends.length - 1)

  return (
    <div className="max-w-6xl mx-auto px-4 py-6 flex flex-col gap-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-semibold">Overview</h1>
          <p className="text-sm text-muted mt-0.5">{today}</p>
        </div>
        <div className="flex items-center gap-3">
          <DateRangeSelector
            preset={preset}
            offset={offset}
            windowLabel={windowLabel}
            canGoForward={canGoForward}
            onSelect={select}
            onBack={goBack}
            onForward={goForward}
          />
          {whoopAuth === false && (
            <button
              onClick={() => { window.location.href = 'http://localhost:8000/whoop/login' }}
              className="px-4 py-2 text-sm font-medium rounded-lg bg-purple/10 text-purple border border-purple/30 hover:bg-purple/20 transition-colors"
            >
              Connect WHOOP →
            </button>
          )}
        </div>
      </div>

      {/* WHOOP vitals — top row */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
        <MetricCard label="Recovery Score" value={data?.recovery?.whoop_recovery_score} unit="%" source="whoop"
          color={recoveryColor(data?.recovery?.whoop_recovery_score)} loading={loading} />
        <MetricCard label="HRV" value={data?.recovery?.whoop_hrv != null ? +data.recovery.whoop_hrv.toFixed(1) : null}
          unit="ms" source="whoop" loading={loading} />
        <MetricCard label="Resting HR" value={data?.recovery?.whoop_resting_hr} unit="bpm" source="whoop" loading={loading} />
        <MetricCard label="Sleep Performance" value={data?.sleep?.whoop_sleep_performance} unit="%" source="whoop"
          color={sleepColor(data?.sleep?.whoop_sleep_performance)} loading={loading} />
        <MetricCard
          label="Tomorrow Recovery"
          value={prediction?.status === 'ok' ? prediction.predicted_recovery : null}
          unit="%"
          source="LightGBM"
          color={prediction?.band}
          sub={prediction?.status === 'ok'
            ? `${prediction.confidence} confidence${prediction.validation_mae != null ? ` · MAE ±${prediction.validation_mae}%` : ''}`
            : prediction?.reason}
          loading={loading}
        />
      </div>

      {/* Recovery ↔ Training Load overlay — the core cross-device insight */}
      <div className="bg-surface rounded-2xl p-5 border border-border">
        <div className="mb-4">
          <h3 className="metric-label">Recovery vs Training Load</h3>
          <p className="text-xs text-muted mt-0.5">Bar = day's training load → line = next-morning WHOOP recovery</p>
        </div>
        <ResponsiveContainer width="100%" height={220}>
          <ComposedChart data={overlayData} margin={{ top: 5, right: 40, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={colors.border} />
            <XAxis dataKey="date" tick={{ fill: colors.muted, fontSize: 10 }} />
            <YAxis yAxisId="recovery" tick={{ fill: colors.muted, fontSize: 11 }} domain={[0, 100]} />
            <YAxis yAxisId="load" orientation="right" tick={{ fill: colors.muted, fontSize: 11 }} />
            <Tooltip content={<ChartTooltip />} />
            <Legend formatter={(v) => <span style={{ color: colors.muted, fontSize: 12 }}>{v}</span>} />
            <Bar yAxisId="load" dataKey="training_load" name="Training Load" fill={colors.blue + "18"} stroke={colors.blue + "55"} strokeWidth={1} radius={[2, 2, 0, 0]} />
            <Line yAxisId="recovery" type="monotone" dataKey="next_recovery" name="Next-day Recovery %" stroke={colors.purple} strokeWidth={2} dot={{ r: 3, fill: colors.purple }} connectNulls />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* HRV + Sleep side by side */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <HRVChart data={aggregatedTrends} />
        <SleepChart data={aggregatedTrends} source="whoop" />
      </div>

      {/* Scatter correlations */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <CorrelationChart
          data={recoveryVsTss}
          xKey="strain"
          yKey="next_day_recovery"
          xLabel="Strain"
          yLabel="Next-day Recovery %"
          color={colors.purple}
          title="Strain → Next-Day Recovery"
          subtitle="Each point = day's strain vs the following morning's recovery"
        />
        <CorrelationChart
          data={correlation.filter(d => d.hrv && d.tss)}
          xKey="hrv"
          yKey="tss"
          xLabel="HRV (ms)"
          yLabel="TSS"
          color={colors.blue}
          title="HRV → Ride Load"
          subtitle="Do you push harder on high-HRV mornings?"
        />
      </div>

      {/* Activities + Strain */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2">
          <ActivityFeed activities={data?.training?.garmin_activities || []} whoopWorkouts={data?.training?.whoop_workouts || []} />
        </div>
        <StrainRing strain={data?.training?.whoop_strain} />
      </div>

      {/* Sleep detail */}
      <div className="grid grid-cols-3 gap-4">
        <MetricCard label="Sleep Duration" value={data?.sleep?.whoop_duration_hours} unit="h" source="whoop" loading={loading} />
        <MetricCard label="REM" value={data?.sleep?.whoop_rem_hours} unit="h" source="whoop" loading={loading} />
        <MetricCard label="Deep" value={data?.sleep?.whoop_deep_hours} unit="h" source="whoop" loading={loading} />
      </div>

      <InsightsPanel date={data?.date} />
    </div>
  )
}
