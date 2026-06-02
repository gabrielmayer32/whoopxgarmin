function severityColor(severity) {
  if (severity === 'high') return 'text-red'
  if (severity === 'medium') return 'text-amber'
  if (severity === 'low') return 'text-blue'
  return 'text-muted'
}

function scoreLabel(score) {
  if (score == null) return '—'
  return Math.round(score * 100)
}

export default function AnomalyPanel({ data, loading }) {
  const items = (data?.items || []).filter((item) => item.severity !== 'normal').slice(0, 5)

  return (
    <div className="bg-surface rounded-2xl p-5 border border-border">
      <div className="flex items-start justify-between gap-3 mb-4">
        <div>
          <h3 className="metric-label">Personal Anomaly Detection</h3>
          <p className="text-xs text-muted mt-0.5">IsolationForest with rule-assisted explanations</p>
        </div>
        <span className="text-xs font-medium text-blue">ML</span>
      </div>

      {loading ? (
        <div className="flex flex-col gap-2">
          {[1, 2, 3].map((i) => <div key={i} className="h-12 bg-surface-2 animate-pulse rounded-lg" />)}
        </div>
      ) : data?.status !== 'ok' ? (
        <p className="text-xs text-muted">{data?.reason || 'No anomaly data available yet.'}</p>
      ) : items.length === 0 ? (
        <p className="text-sm text-gray-300">No unusual recovery, sleep, or training patterns flagged in this window.</p>
      ) : (
        <div className="flex flex-col gap-3">
          {items.map((item) => (
            <div key={item.date} className="border border-border rounded-lg p-3 bg-surface-2/40">
              <div className="flex items-center justify-between gap-3 mb-2">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-xs text-gray-300">{item.date}</span>
                  <span className={`text-xs font-medium ${severityColor(item.severity)}`}>{item.severity}</span>
                </div>
                <span className="font-mono text-xs text-muted">score {scoreLabel(item.anomaly_score)}</span>
              </div>
              <ul className="flex flex-col gap-1">
                {item.flags.slice(0, 3).map((flag, index) => (
                  <li key={index} className="text-xs text-gray-400 leading-relaxed">{flag}</li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
