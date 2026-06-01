import { NavLink } from 'react-router-dom'
import { useState } from 'react'
import { triggerSync } from '../api/client'
import HistoryBackfillModal from './HistoryBackfillModal'

export default function Navbar() {
  const [syncing, setSyncing] = useState(false)
  const [synced, setSynced] = useState(false)
  const [showBackfill, setShowBackfill] = useState(false)

  async function handleSync() {
    setSyncing(true)
    try {
      await triggerSync()
      setSynced(true)
      setTimeout(() => setSynced(false), 3000)
    } finally {
      setSyncing(false)
    }
  }

  const linkClass = ({ isActive }) =>
    `px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
      isActive ? 'bg-surface-2 text-white' : 'text-muted hover:text-white'
    }`

  return (
    <nav className="border-b border-border bg-surface sticky top-0 z-10">
      <div className="max-w-6xl mx-auto px-4 h-14 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="font-semibold text-sm tracking-tight">Whoop x Garmin </span>
          <span className="text-border">|</span>
          <div className="flex gap-1">
            <NavLink to="/" end className={linkClass}>Dashboard</NavLink>
            <NavLink to="/recovery" className={linkClass}>Recovery</NavLink>
            <NavLink to="/training" className={linkClass}>Training</NavLink>
          </div>
        </div>
        <div className="flex items-center gap-2">
        <button
          onClick={() => setShowBackfill(true)}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border border-border hover:border-muted text-muted hover:text-white transition-colors"
          title="Import full history from a past date"
        >
          <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M12 10v6m0 0l-3-3m3 3l3-3M3 17V7a2 2 0 012-2h6l2 2h6a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2z" />
          </svg>
          Import History
        </button>
        <button
          onClick={handleSync}
          disabled={syncing}
          className="flex items-center gap-2 px-3 py-1.5 text-xs font-medium rounded-lg border border-border hover:border-muted text-muted hover:text-white transition-colors disabled:opacity-50"
        >
          {syncing ? (
            <svg className="animate-spin w-3 h-3" viewBox="0 0 24 24" fill="none">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
            </svg>
          ) : (
            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          )}
          {synced ? 'Synced!' : syncing ? 'Syncing...' : 'Sync'}
        </button>
        </div>
      </div>
      {showBackfill && <HistoryBackfillModal onClose={() => setShowBackfill(false)} />}
    </nav>
  )
}
