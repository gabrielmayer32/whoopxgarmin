function fmtDuration(sec) {
  if (!sec) return '—'
  const h = Math.floor(sec / 3600)
  const m = Math.floor((sec % 3600) / 60)
  return h > 0 ? `${h}h ${m}m` : `${m}m`
}

function fmtDist(m) {
  if (!m) return null
  if (m >= 1000) return `${(m / 1000).toFixed(1)} km`
  return `${Math.round(m)} m`
}

export default function ActivityFeed({ activities = [], stravaActivities = [] }) {
  const garminRows = activities.map(a => ({ ...a, _source: 'garmin' }))
  const stravaRows = stravaActivities.map(a => ({ ...a, _source: 'strava' }))
  const all = [...garminRows, ...stravaRows]

  return (
    <div className="bg-surface rounded-2xl p-5 border border-border">
      <h3 className="metric-label mb-4">Today's Activities</h3>
      {all.length === 0 ? (
        <p className="text-muted text-sm">No activities recorded today.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-muted text-xs uppercase tracking-wider border-b border-border">
                {['Name', 'Type', 'Duration', 'Dist', 'Avg HR', 'Max HR', 'Cal', 'Source'].map(h => (
                  <th key={h} className={`pb-3 font-medium ${h === 'Name' || h === 'Type' ? 'text-left' : 'text-right'}`}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {all.map((a) => (
                <tr key={a.id} className="hover:bg-surface-2 transition-colors">
                  <td className="py-2.5 font-medium max-w-[180px] truncate pr-3">{a.name || a.type || 'Activity'}</td>
                  <td className="py-2.5 text-xs text-muted">{a.type}</td>
                  <td className="py-2.5 text-right font-mono text-xs">{fmtDuration(a.duration_seconds)}</td>
                  <td className="py-2.5 text-right font-mono text-xs">{fmtDist(a.distance_meters) || '—'}</td>
                  <td className="py-2.5 text-right font-mono text-xs text-blue">{a.avg_hr ? Math.round(a.avg_hr) : '—'}</td>
                  <td className="py-2.5 text-right font-mono text-xs text-red">{a.max_hr ? Math.round(a.max_hr) : '—'}</td>
                  <td className="py-2.5 text-right font-mono text-xs">{a.calories ? Math.round(a.calories) : '—'}</td>
                  <td className="py-2.5 text-right">
                    {a._source === 'strava'
                      ? <span className="text-[10px] px-1.5 py-0.5 rounded bg-orange-500/20 text-orange-400">Strava</span>
                      : <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-400">Garmin</span>
                    }
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
