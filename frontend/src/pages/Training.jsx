import { useEffect, useState } from 'react'
import { fetchCyclingStats, fetchPowerCurveBest, fetchActivities, fetchGymSessions } from '../api/client'
import TrainingLoadChart from '../components/TrainingLoadChart'
import PowerCurveChart from '../components/PowerCurveChart'
import DateRangeSelector from '../components/DateRangeSelector'
import useDateRange from '../hooks/useDateRange'
import aggregateByRange from '../utils/aggregateByRange'
import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend, RadarChart, PolarGrid,
  PolarAngleAxis, Radar, ReferenceLine,
} from 'recharts'

const Tooltip_ = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="bg-surface-2 border border-border rounded-xl p-3 text-sm min-w-[140px]">
      <p className="text-muted mb-2 text-xs">{label}</p>
      {payload.map((p) => (
        <p key={p.name} style={{ color: p.color }} className="font-mono text-xs">
          {p.name}: {p.value != null ? (typeof p.value === 'number' ? p.value.toFixed(1) : p.value) : '—'}
        </p>
      ))}
    </div>
  )
}

function fmtDuration(sec) {
  if (!sec) return '—'
  const h = Math.floor(sec / 3600)
  const m = Math.floor((sec % 3600) / 60)
  return h > 0 ? `${h}h ${m}m` : `${m}m`
}

function fmtDist(m) {
  if (!m) return '—'
  return `${(m / 1000).toFixed(1)} km`
}

function fmtSpeed(ms) {
  if (!ms) return '—'
  return `${(ms * 3.6).toFixed(1)} km/h`
}

function StatPill({ label, value, unit, color = 'text-white' }) {
  return (
    <div className="flex flex-col items-center bg-surface-2 rounded-xl px-4 py-3 min-w-[80px]">
      <span className={`font-mono text-lg font-medium ${color}`}>
        {value != null ? `${typeof value === 'number' ? value % 1 === 0 ? value : value.toFixed(1) : value}` : '—'}
        {unit && <span className="text-xs text-muted ml-0.5">{unit}</span>}
      </span>
      <span className="text-xs text-muted mt-0.5 text-center">{label}</span>
    </div>
  )
}

const HR_ZONE_COLORS = ['#4a9eff', '#00e5a0', '#f5a623', '#ff8c42', '#ff4757']
const HR_ZONE_NAMES = ['Z1', 'Z2', 'Z3', 'Z4', 'Z5']
const POWER_ZONE_COLORS = ['#2a3a5a', '#1a4a6a', '#4a9eff', '#00c8a0', '#f5a623', '#ff8c42', '#ff4757']

export default function Training() {
  const { preset, days, startDate, offset, windowLabel, canGoForward, select, goBack, goForward } = useDateRange('3M')
  const [stats, setStats] = useState([])
  const [bestPower, setBestPower] = useState(null)
  const [activities, setActivities] = useState([])
  const [gymSessions, setGymSessions] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedRide, setSelectedRide] = useState(null)
  const [compareRide, setCompareRide] = useState(null)

  useEffect(() => {
    setLoading(true)
    Promise.all([
      fetchCyclingStats(days, startDate),
      fetchPowerCurveBest(days, startDate),
      fetchActivities(days, startDate),
      fetchGymSessions(days, startDate),
    ])
      .then(([s, bp, acts, gym]) => {
        setStats(s)
        setBestPower(bp)
        setActivities(acts)
        setGymSessions(gym)
        if (acts.length) setSelectedRide(acts[0])
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [days, startDate])

  const tssData = aggregateByRange(
    stats.map(r => ({ date: r.date, tss: r.tss, load: r.training_load })),
    days
  )

  const powerData = aggregateByRange(
    stats.map(r => ({ date: r.date, np: r.norm_power, avg: r.avg_power })),
    days
  )

  // Power curve — durations in seconds for proper x-axis ordering
  const CURVE_POINTS = [
    { key: '5s',  label: '5s',  sec: 5 },
    { key: '20s', label: '20s', sec: 20 },
    { key: '1m',  label: '1m',  sec: 60 },
    { key: '5m',  label: '5m',  sec: 300 },
    { key: '10m', label: '10m', sec: 600 },
    { key: '20m', label: '20m', sec: 1200 },
    { key: '60m', label: '60m', sec: 3600 },
  ]
  const rideForCurve = selectedRide
  const powerCurveData = rideForCurve?.power_curve
    ? CURVE_POINTS.map(({ key, label, sec }) => ({
        label,
        sec,
        power: rideForCurve.power_curve[key] ?? null,
        compare: compareRide?.power_curve?.[key] ?? null,
        best: bestPower?.[key] ?? null,
      }))
    : []

  // HR zone distribution for selected ride
  const hrZoneData = rideForCurve?.hr_zones?.map((sec, i) => ({
    name: HR_ZONE_NAMES[i],
    minutes: sec ? Math.round(sec / 60) : 0,
    fill: HR_ZONE_COLORS[i],
  })).filter(z => z.minutes > 0) || []

  // Power zone distribution
  const pwrZoneData = rideForCurve?.power_zones?.map((sec, i) => ({
    name: `PZ${i + 1}`,
    minutes: sec ? Math.round(sec / 60) : 0,
    fill: POWER_ZONE_COLORS[i],
  })).filter(z => z.minutes > 0) || []

  // Aggregated HR zone totals across all rides (last 10)
  const last10 = activities.slice(0, 10)
  const totalHrZones = HR_ZONE_NAMES.map((name, i) => ({
    name,
    minutes: Math.round(last10.reduce((s, a) => s + (a.hr_zones?.[i] || 0), 0) / 60),
    fill: HR_ZONE_COLORS[i],
  }))

  return (
    <div className="max-w-6xl mx-auto px-4 py-6 flex flex-col gap-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h1 className="text-xl font-semibold">Training</h1>
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

      {/* KPI strip */}
      {activities.length > 0 && (() => {
        const totalTSS = activities.reduce((s, a) => s + (a.tss || 0), 0)
        const npRides = activities.filter(a => a.norm_power)
        const avgNP = npRides.length ? npRides.reduce((s, a) => s + a.norm_power, 0) / npRides.length : 0
        const ifRides = activities.filter(a => a.intensity_factor)
        const avgIF = ifRides.length ? ifRides.reduce((s, a) => s + a.intensity_factor, 0) / ifRides.length : 0
        const totalKm = activities.reduce((s, a) => s + (a.distance_meters || 0), 0) / 1000
        const totalElev = activities.reduce((s, a) => s + (a.elevation_gain || 0), 0)
        return (
          <div className="flex gap-3 flex-wrap">
            <StatPill label={`${preset} TSS`} value={Math.round(totalTSS)} color="text-blue" />
            <StatPill label="Avg NP" value={npRides.length ? Math.round(avgNP) : null} unit="W" color="text-purple" />
            <StatPill label="Avg IF" value={ifRides.length ? avgIF : null} color="text-amber" />
            <StatPill label={`${preset} Distance`} value={totalKm.toFixed(0)} unit="km" color="text-green" />
            <StatPill label={`${preset} Elevation`} value={Math.round(totalElev)} unit="m" />
            <StatPill label="Best 20m Power" value={bestPower?.['20m']} unit="W" color="text-red" />
            <StatPill label="Best 5m Power" value={bestPower?.['5m']} unit="W" color="text-amber" />
          </div>
        )
      })()}

      {/* TSS + Training Load */}
      <div className="bg-surface rounded-2xl p-5 border border-border">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="metric-label">Training Stress Score (TSS) per Ride</h3>
            <p className="text-xs text-muted mt-0.5">Low &lt;50 · Medium 50–150 · High &gt;150</p>
          </div>
          <span className="text-xs font-medium text-blue">Garmin</span>
        </div>
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={tssData} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#2a2a3a" />
            <XAxis dataKey="date" tick={{ fill: '#6b6b8a', fontSize: 10 }} />
            <YAxis tick={{ fill: '#6b6b8a', fontSize: 11 }} />
            <Tooltip content={<Tooltip_ />} />
            <ReferenceLine y={150} stroke="#ff4757" strokeDasharray="4 4" strokeOpacity={0.5} />
            <ReferenceLine y={50} stroke="#00e5a0" strokeDasharray="4 4" strokeOpacity={0.5} />
            <Bar dataKey="tss" name="TSS" fill="#4a9eff" radius={[3, 3, 0, 0]} maxBarSize={24} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* NP + Avg Power trend */}
      <div className="bg-surface rounded-2xl p-5 border border-border">
        <div className="flex items-center justify-between mb-4">
          <h3 className="metric-label">Power Trend — NP vs Avg Power (W)</h3>
          <span className="text-xs font-medium text-blue">Garmin</span>
        </div>
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={powerData} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#2a2a3a" />
            <XAxis dataKey="date" tick={{ fill: '#6b6b8a', fontSize: 10 }} />
            <YAxis tick={{ fill: '#6b6b8a', fontSize: 11 }} domain={['auto', 'auto']} />
            <Tooltip content={<Tooltip_ />} />
            <Legend formatter={(v) => <span style={{ color: '#6b6b8a', fontSize: 12 }}>{v}</span>} />
            <Line type="monotone" dataKey="np" name="NP (W)" stroke="#b44aff" strokeWidth={2} dot={{ r: 3, fill: '#b44aff' }} connectNulls />
            <Line type="monotone" dataKey="avg" name="Avg Power (W)" stroke="#4a9eff" strokeWidth={2} dot={{ r: 3, fill: '#4a9eff' }} connectNulls />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Training Load chart */}
      <TrainingLoadChart data={aggregateByRange(stats.map(r => ({ date: r.date, training_load: r.training_load, acute_load: r.acute_load })), days)} />

      {/* Ride selector + per-ride deep dive */}
      <div className="bg-surface rounded-2xl p-5 border border-border">
        <div className="flex items-center justify-between mb-4">
          <h3 className="metric-label">Ride Analysis</h3>
          <select
            className="bg-surface-2 border border-border text-sm text-white rounded-lg px-3 py-1.5 outline-none"
            value={selectedRide?.id || ''}
            onChange={(e) => { setSelectedRide(activities.find(a => a.id === e.target.value)); setCompareRide(null) }}
          >
            {activities.map(a => (
              <option key={a.id} value={a.id}>
                {a.date} — {a.name || a.type}
              </option>
            ))}
          </select>
        </div>

        {selectedRide && (
          <div className="flex flex-col gap-5">
            {/* Ride KPIs */}
            <div className="flex gap-3 flex-wrap">
              <StatPill label="Duration" value={fmtDuration(selectedRide.duration_seconds)} />
              <StatPill label="Distance" value={fmtDist(selectedRide.distance_meters)} />
              <StatPill label="Avg Power" value={selectedRide.avg_power} unit="W" color="text-blue" />
              <StatPill label="NP" value={selectedRide.norm_power} unit="W" color="text-purple" />
              <StatPill label="TSS" value={selectedRide.tss?.toFixed(0)} color="text-amber" />
              <StatPill label="IF" value={selectedRide.intensity_factor} color="text-green" />
              <StatPill label="Avg Cadence" value={selectedRide.avg_cadence} unit="rpm" />
              <StatPill label="Elevation" value={selectedRide.elevation_gain} unit="m" />
              <StatPill label="Avg Speed" value={fmtSpeed(selectedRide.avg_speed)} />
              {selectedRide.grit != null && <StatPill label="Grit" value={selectedRide.grit?.toFixed(1)} color="text-red" />}
              {selectedRide.flow != null && <StatPill label="Flow" value={selectedRide.flow?.toFixed(2)} color="text-green" />}
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {/* Power curve */}
              {powerCurveData.length > 0 && (
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <p className="metric-label">Power Curve</p>
                    <select
                      className="bg-surface-2 border border-border text-xs text-white rounded-lg px-2 py-1 outline-none max-w-[180px]"
                      value={compareRide?.id || ''}
                      onChange={(e) => {
                        const val = e.target.value
                        setCompareRide(val ? activities.find(a => a.id === val) : null)
                      }}
                    >
                      <option value="">+ Compare ride…</option>
                      {activities
                        .filter(a => a.id !== selectedRide?.id && a.power_curve)
                        .map(a => (
                          <option key={a.id} value={a.id}>
                            {a.date?.slice(5)} — {a.name || a.type}
                          </option>
                        ))}
                    </select>
                  </div>
                  <PowerCurveChart
                    data={powerCurveData}
                    compareLabel={compareRide ? `${compareRide.date?.slice(5)}` : null}
                  />
                </div>
              )}

              {/* HR zones */}
              {hrZoneData.length > 0 && (
                <div>
                  <p className="metric-label mb-3">HR Zone Distribution</p>
                  <ResponsiveContainer width="100%" height={180}>
                    <BarChart data={hrZoneData} layout="vertical" margin={{ top: 0, right: 10, left: 10, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#2a2a3a" horizontal={false} />
                      <XAxis type="number" tick={{ fill: '#6b6b8a', fontSize: 11 }} unit="m" />
                      <YAxis type="category" dataKey="name" tick={{ fill: '#6b6b8a', fontSize: 11 }} width={28} />
                      <Tooltip content={<Tooltip_ />} />
                      <Bar dataKey="minutes" name="Minutes" radius={[0, 4, 4, 0]}>
                        {hrZoneData.map((entry, i) => (
                          <rect key={i} fill={entry.fill} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Gym sessions */}
      {(gymSessions.length > 0 || !loading) && (
        <div className="bg-surface rounded-2xl p-5 border border-border">
          <div className="flex items-center justify-between mb-4">
            <h3 className="metric-label">Gym Sessions</h3>
            <div className="flex items-center gap-2">
              <span className="text-xs font-medium text-orange-400">Strava</span>
              {gymSessions.length === 0 && (
                <button onClick={() => { window.location.href = 'http://localhost:8000/strava/login' }} className="text-xs text-orange-400 border border-orange-400/30 rounded-lg px-2 py-1 hover:bg-orange-400/10 transition-colors">
                  Connect →
                </button>
              )}
            </div>
          </div>
          {gymSessions.length === 0 ? (
            <p className="text-muted text-sm">No gym sessions found. Connect Strava and run a backfill.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-muted text-xs uppercase tracking-wider border-b border-border">
                    {['Date', 'Name', 'Type', 'Duration', 'Avg HR', 'Max HR', 'Calories'].map(h => (
                      <th key={h} className={`pb-3 font-medium ${h === 'Date' || h === 'Name' || h === 'Type' ? 'text-left' : 'text-right'}`}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {gymSessions.map((s) => (
                    <tr key={s.activity_id} className="hover:bg-surface-2 transition-colors">
                      <td className="py-2.5 text-muted text-xs">{s.date?.slice(5)}</td>
                      <td className="py-2.5 font-medium max-w-[180px] truncate pr-3">{s.name}</td>
                      <td className="py-2.5 text-xs text-orange-400">{s.sport_type}</td>
                      <td className="py-2.5 text-right font-mono text-xs">{fmtDuration(s.duration_seconds)}</td>
                      <td className="py-2.5 text-right font-mono text-xs text-blue">{s.avg_hr ? `${Math.round(s.avg_hr)}` : '—'}</td>
                      <td className="py-2.5 text-right font-mono text-xs text-red">{s.max_hr ? `${Math.round(s.max_hr)}` : '—'}</td>
                      <td className="py-2.5 text-right font-mono text-xs">{s.calories ? `${Math.round(s.calories)}` : '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Activity table */}
      <div className="bg-surface rounded-2xl p-5 border border-border">
        <h3 className="metric-label mb-4">All Rides</h3>
        {loading ? (
          <div className="flex flex-col gap-2">
            {[1, 2, 3].map((i) => <div key={i} className="h-10 bg-surface-2 animate-pulse rounded-xl" />)}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-muted text-xs uppercase tracking-wider border-b border-border">
                  {['Date', 'Name', 'Dur', 'Dist', 'Avg W', 'NP', 'TSS', 'IF', 'Cad', 'Elev', 'TE'].map(h => (
                    <th key={h} className={`pb-3 font-medium ${h === 'Date' || h === 'Name' ? 'text-left' : 'text-right'}`}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {activities.map((a) => (
                  <tr
                    key={a.id}
                    className={`hover:bg-surface-2 transition-colors cursor-pointer ${selectedRide?.id === a.id ? 'bg-surface-2' : ''}`}
                    onClick={() => { setSelectedRide(a); setCompareRide(null) }}
                  >
                    <td className="py-2.5 text-muted text-xs">{a.date?.slice(5)}</td>
                    <td className="py-2.5 font-medium max-w-[160px] truncate pr-3">{a.name || a.type}</td>
                    <td className="py-2.5 text-right font-mono text-xs">{fmtDuration(a.duration_seconds)}</td>
                    <td className="py-2.5 text-right font-mono text-xs">{fmtDist(a.distance_meters)}</td>
                    <td className="py-2.5 text-right font-mono text-xs text-blue">{a.avg_power ? `${Math.round(a.avg_power)}` : '—'}</td>
                    <td className="py-2.5 text-right font-mono text-xs text-purple">{a.norm_power ? `${Math.round(a.norm_power)}` : '—'}</td>
                    <td className="py-2.5 text-right font-mono text-xs text-amber">{a.tss ? `${Math.round(a.tss)}` : '—'}</td>
                    <td className="py-2.5 text-right font-mono text-xs">{a.intensity_factor?.toFixed(2) || '—'}</td>
                    <td className="py-2.5 text-right font-mono text-xs">{a.avg_cadence || '—'}</td>
                    <td className="py-2.5 text-right font-mono text-xs">{a.elevation_gain ? `${Math.round(a.elevation_gain)}m` : '—'}</td>
                    <td className="py-2.5 text-right font-mono text-xs text-green">{a.training_effect?.toFixed(1) || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
