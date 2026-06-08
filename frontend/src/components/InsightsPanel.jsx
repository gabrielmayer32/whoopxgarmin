import { useEffect, useState } from 'react'
import { fetchInsights } from '../api/client'

const SECTIONS = [
  { key: 'day',               label: "Readiness",          icon: "◈" },
  { key: 'week',              label: "Weekly Load",         icon: "◷" },
  { key: 'sleep',             label: "Sleep",               icon: "◑" },
  { key: 'hrv',               label: "HRV Trends",          icon: "∿" },
  { key: 'training',          label: "Performance",         icon: "△" },
  { key: 'recovery_patterns', label: "Recovery Patterns",   icon: "⇄" },
]

function InsightSection({ label, icon, facts, coaching, loading }) {
  const [open, setOpen] = useState(true)

  if (loading) {
    return (
      <div className="bg-surface rounded-2xl p-5 border border-border">
        <div className="flex items-center gap-2 mb-3">
          <span className="text-muted text-base">{icon}</span>
          <span className="metric-label">{label}</span>
        </div>
        <div className="flex flex-col gap-2">
          {[1, 2].map(i => <div key={i} className="h-3 bg-surface-2 animate-pulse rounded" />)}
        </div>
      </div>
    )
  }

  const hasData = facts?.length > 0 || coaching

  return (
    <div className="bg-surface rounded-2xl border border-border overflow-hidden">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-5 py-4 hover:bg-surface-2 transition-colors"
      >
        <div className="flex items-center gap-2">
          <span className="text-muted">{icon}</span>
          <span className="metric-label">{label}</span>
        </div>
        <span className="text-muted text-xs">{open ? '▲' : '▼'}</span>
      </button>

      {open && hasData && (
        <div className="px-5 pb-5 flex flex-col gap-3">
          {facts?.length > 0 && (
            <ul className="flex flex-col gap-1.5">
              {facts.map((f, i) => (
                <li key={i} className="flex gap-2 text-xs text-gray-400 leading-relaxed">
                  <span className="text-muted flex-shrink-0 mt-0.5">·</span>
                  {f}
                </li>
              ))}
            </ul>
          )}
          {coaching && (
            <div className="border-t border-border pt-3 mt-1">
              <p className="text-sm text-gray-200 leading-relaxed italic">{coaching}</p>
            </div>
          )}
        </div>
      )}

      {open && !hasData && (
        <p className="px-5 pb-5 text-xs text-muted">No data available yet — keep syncing.</p>
      )}
    </div>
  )
}

export default function InsightsPanel({ date }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    fetchInsights(date)
      .then(d => setData(d))
      .catch(() => setData(null))
      .finally(() => setLoading(false))
  }, [date])

  return (
    <div className="flex flex-col gap-3">
      <h3 className="text-base font-semibold px-1">Insights</h3>
      {SECTIONS.map(s => (
        <InsightSection
          key={s.key}
          icon={s.icon}
          label={s.label}
          facts={data?.[s.key]?.facts}
          coaching={data?.[s.key]?.coaching}
          loading={loading}
        />
      ))}
    </div>
  )
}
