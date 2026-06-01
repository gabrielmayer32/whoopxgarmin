import { useState, useCallback } from 'react'

export const PRESETS = [
  { label: '1W', days: 7 },
  { label: '1M', days: 30 },
  { label: '3M', days: 90 },
  { label: '6M', days: 180 },
  { label: '1Y', days: 365 },
  { label: 'All', days: 9999 },
]

function toIso(date) {
  return date.toISOString().slice(0, 10)
}

export default function useDateRange(defaultPreset = '1M') {
  const [preset, setPreset] = useState(defaultPreset)
  // offset in number-of-windows: 0 = current window, 1 = previous window, etc.
  const [offset, setOffset] = useState(0)

  const days = PRESETS.find((p) => p.label === preset)?.days ?? 30
  const isAll = preset === 'All'

  // Compute the start date for the current offset
  const startDate = (() => {
    if (isAll || offset === 0) return null // null = backend uses today as anchor
    const end = new Date()
    end.setDate(end.getDate() - offset * days)
    const start = new Date(end)
    start.setDate(end.getDate() - days + 1)
    return toIso(start)
  })()

  const canGoForward = offset > 0

  const goBack = useCallback(() => setOffset((o) => o + 1), [])
  const goForward = useCallback(() => setOffset((o) => Math.max(0, o - 1)), [])

  const select = useCallback((label) => {
    setPreset(label)
    setOffset(0)
  }, [])

  // Human-readable label for the current window
  const windowLabel = (() => {
    if (isAll) return 'All time'
    if (offset === 0) return 'Current'
    const end = new Date()
    end.setDate(end.getDate() - offset * days)
    const start = new Date(end)
    start.setDate(end.getDate() - days + 1)
    const fmt = (d) => d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
    return `${fmt(start)} – ${fmt(end)}`
  })()

  return { preset, days, offset, startDate, canGoForward, goBack, goForward, select, windowLabel }
}
