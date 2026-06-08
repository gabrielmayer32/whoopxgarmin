import { useState } from 'react'

function severityColor(severity) {
  if (severity === 'high') return 'text-red'
  if (severity === 'medium') return 'text-amber'
  if (severity === 'low') return 'text-blue'
  return 'text-muted'
}

function sentimentColor(sentiment) {
  if (sentiment === 'positive' || sentiment === 'improving') return 'text-emerald-400'
  if (sentiment === 'negative' || sentiment === 'declining') return 'text-red-400'
  return 'text-gray-400'
}

function sentimentBg(sentiment) {
  if (sentiment === 'positive' || sentiment === 'improving') return 'bg-emerald-500/10'
  if (sentiment === 'negative' || sentiment === 'declining') return 'bg-red-500/10'
  return 'bg-white/5'
}

function trendArrow(direction) {
  return direction === 'up' ? '↑' : '↓'
}

function scoreLabel(score) {
  if (score == null) return '—'
  return Math.round(score * 100)
}

function AnomalyItem({ item }) {
  const [expanded, setExpanded] = useState(false)
  const hasDetails = (item.flags?.length > 0) || (item.deviations?.length > 0) || (item.trends?.length > 0)

  return (
    <div className="border border-border rounded-lg bg-surface-2/40 overflow-hidden">
      <button
        onClick={() => hasDetails && setExpanded(!expanded)}
        className={`w-full text-left p-4 ${hasDetails ? 'cursor-pointer hover:bg-white/[0.02]' : 'cursor-default'} transition-colors`}
      >
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2 min-w-0">
            {hasDetails && (
              <span className={`text-[10px] text-muted transition-transform ${expanded ? 'rotate-90' : ''}`}>▶</span>
            )}
            <span className="font-mono text-xs text-gray-300">{item.date}</span>
            <span className={`text-xs font-medium ${severityColor(item.severity)}`}>{item.severity}</span>
          </div>
          <span className="font-mono text-xs text-muted shrink-0">score {scoreLabel(item.anomaly_score)}</span>
        </div>
        {item.interpretation && (
          <p className="text-xs text-gray-300 mt-1.5 leading-relaxed italic pl-[18px]">
            {item.interpretation}
          </p>
        )}
      </button>

      {expanded && (
        <div className="px-4 pb-4 pt-0 flex flex-col gap-3 border-t border-border/50">
          {item.flags?.length > 0 && (
            <ul className="flex flex-col gap-1 mt-3">
              {item.flags.slice(0, 4).map((flag, index) => (
                <li key={index} className="text-xs text-gray-400 leading-relaxed">• {flag}</li>
              ))}
            </ul>
          )}

          {item.deviations?.length > 0 && (
            <div>
              <p className="text-[10px] uppercase tracking-wider text-muted mb-1.5">Metric Deviations</p>
              <div className="flex flex-wrap gap-1.5">
                {item.deviations.slice(0, 5).map((d) => (
                  <span
                    key={d.key}
                    className={`inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-full ${sentimentBg(d.sentiment)} ${sentimentColor(d.sentiment)}`}
                  >
                    {d.metric} {d.pct_change > 0 ? '+' : ''}{d.pct_change}%
                  </span>
                ))}
              </div>
            </div>
          )}

          {item.trends?.length > 0 && (
            <div>
              <p className="text-[10px] uppercase tracking-wider text-muted mb-1.5">7-Day Trends</p>
              <div className="flex flex-wrap gap-1.5">
                {item.trends.slice(0, 4).map((t) => (
                  <span
                    key={t.key}
                    className={`inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-full ${sentimentBg(t.sentiment)} ${sentimentColor(t.sentiment)}`}
                  >
                    {trendArrow(t.direction)} {t.metric} {t.sentiment}
                    {t.pct_change_7d ? ` (${t.pct_change_7d > 0 ? '+' : ''}${t.pct_change_7d}%)` : ''}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default function AnomalyPanel({ data, loading }) {
  const items = (data?.items || []).filter((item) => item.severity !== 'normal').slice(0, 5)

  return (
    <div className="bg-surface rounded-2xl p-5 border border-border">
      <div className="flex items-start justify-between gap-3 mb-4">
        <div>
          <h3 className="metric-label">Deep Anomaly Analysis</h3>
          <p className="text-xs text-muted mt-0.5">ML detection + directional per-metric breakdown</p>
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
        <div className="flex flex-col gap-2">
          {items.map((item) => (
            <AnomalyItem key={item.date} item={item} />
          ))}
        </div>
      )}
    </div>
  )
}
