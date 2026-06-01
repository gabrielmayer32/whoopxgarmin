import { useState, useEffect, useRef } from 'react'
import { triggerBackfillFromDate, fetchBackfillStatus } from '../api/client'

export default function HistoryBackfillModal({ onClose }) {
  const [startDate, setStartDate] = useState('')
  const [phase, setPhase] = useState('idle') // idle | running | done | error
  const [status, setStatus] = useState(null)
  const [error, setError] = useState(null)
  const pollRef = useRef(null)

  // Oldest reasonable date (10 years back)
  const minDate = new Date()
  minDate.setFullYear(minDate.getFullYear() - 10)
  const minDateStr = minDate.toISOString().slice(0, 10)
  const todayStr = new Date().toISOString().slice(0, 10)

  useEffect(() => {
    return () => clearInterval(pollRef.current)
  }, [])

  function startPolling() {
    pollRef.current = setInterval(async () => {
      try {
        const s = await fetchBackfillStatus()
        setStatus(s)
        if (!s.running) {
          clearInterval(pollRef.current)
          setPhase(s.error ? 'error' : 'done')
          if (s.error) setError(s.error)
        }
      } catch {
        // ignore transient failures
      }
    }, 3000)
  }

  async function handleStart() {
    if (!startDate) return
    setError(null)
    setPhase('running')
    try {
      await triggerBackfillFromDate(startDate)
      startPolling()
    } catch (e) {
      const msg = e?.response?.data?.detail || e.message || 'Failed to start backfill'
      setError(msg)
      setPhase('error')
    }
  }

  const pct = status && status.total > 0
    ? Math.round((status.done / status.total) * 100)
    : 0

  const serviceLabel = {
    garmin: 'Garmin',
    whoop: 'WHOOP',
    strava: 'Strava',
  }[status?.service] || status?.service || ''

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="bg-surface border border-border rounded-xl shadow-2xl w-full max-w-md mx-4 p-6">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-base font-semibold text-white">Import Full History</h2>
          {phase !== 'running' && (
            <button onClick={onClose} className="text-muted hover:text-white transition-colors">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>

        {phase === 'idle' && (
          <>
            <p className="text-sm text-muted mb-5">
              Pick the earliest date you want to import. All your Garmin and WHOOP data from that date to today will be synced. This can take 30–60 minutes for several years of data.
            </p>
            <label className="block text-xs text-muted mb-1.5">Start from</label>
            <input
              type="date"
              value={startDate}
              min={minDateStr}
              max={todayStr}
              onChange={e => setStartDate(e.target.value)}
              className="w-full bg-surface-2 border border-border rounded-lg px-3 py-2 text-sm text-white mb-5 focus:outline-none focus:border-muted"
            />
            <div className="flex gap-3">
              <button
                onClick={onClose}
                className="flex-1 px-4 py-2 text-sm rounded-lg border border-border text-muted hover:text-white transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleStart}
                disabled={!startDate}
                className="flex-1 px-4 py-2 text-sm font-medium rounded-lg bg-blue-600 hover:bg-blue-500 text-white transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              >
                Start Import
              </button>
            </div>
          </>
        )}

        {phase === 'running' && (
          <>
            <p className="text-sm text-muted mb-4">
              Importing from <span className="text-white">{status?.start_date || startDate}</span> — please keep the app open.
            </p>
            <div className="mb-2 flex justify-between text-xs text-muted">
              <span>{serviceLabel && `Syncing ${serviceLabel}…`}</span>
              <span>{status ? `${status.done} / ${status.total} days` : 'Starting…'}</span>
            </div>
            <div className="w-full bg-surface-2 rounded-full h-2 mb-5">
              <div
                className="bg-blue-500 h-2 rounded-full transition-all duration-500"
                style={{ width: `${pct}%` }}
              />
            </div>
            <p className="text-xs text-muted text-center">
              {pct}% complete — this runs in the background, you can browse the app
            </p>
          </>
        )}

        {phase === 'done' && (
          <>
            <div className="flex flex-col items-center gap-3 py-2">
              <svg className="w-10 h-10 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <p className="text-sm text-white font-medium">Import complete!</p>
              <p className="text-xs text-muted text-center">All your historical data has been synced. Refresh the dashboard to see it.</p>
            </div>
            <button
              onClick={() => { onClose(); window.location.reload() }}
              className="w-full mt-5 px-4 py-2 text-sm font-medium rounded-lg bg-blue-600 hover:bg-blue-500 text-white transition-colors"
            >
              View Dashboard
            </button>
          </>
        )}

        {phase === 'error' && (
          <>
            <div className="flex flex-col items-center gap-3 py-2">
              <svg className="w-10 h-10 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <p className="text-sm text-white font-medium">Something went wrong</p>
              <p className="text-xs text-muted text-center">{error}</p>
            </div>
            <button
              onClick={onClose}
              className="w-full mt-5 px-4 py-2 text-sm rounded-lg border border-border text-muted hover:text-white transition-colors"
            >
              Close
            </button>
          </>
        )}
      </div>
    </div>
  )
}
