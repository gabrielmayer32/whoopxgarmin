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

// Shift a date back by one "period" for the given preset, n times.
// 1W → 7 days, 1M → 1 calendar month, 3M → 3 calendar months,
// 6M → 6 calendar months, 1Y → 1 calendar year.
function shiftBack(date, preset, n) {
  const d = new Date(date)
  if (preset === '1W') {
    d.setDate(d.getDate() - 7 * n)
  } else if (preset === '1M') {
    d.setMonth(d.getMonth() - n)
  } else if (preset === '3M') {
    d.setMonth(d.getMonth() - 3 * n)
  } else if (preset === '6M') {
    d.setMonth(d.getMonth() - 6 * n)
  } else if (preset === '1Y') {
    d.setFullYear(d.getFullYear() - n)
  }
  return d
}

export default function useDateRange(defaultPreset = '1M') {
  const [preset, setPreset] = useState(defaultPreset)
  const [offset, setOffset] = useState(0)

  const days = PRESETS.find((p) => p.label === preset)?.days ?? 30
  const isAll = preset === 'All'

  const startDate = (() => {
    if (isAll || offset === 0) return null
    const end = shiftBack(new Date(), preset, offset)
    const start = shiftBack(new Date(end), preset, 1)
    start.setDate(start.getDate() + 1)
    return toIso(start)
  })()

  // How many days is the current offset window (for the backend `days` param)
  const effectiveDays = (() => {
    if (isAll || offset === 0) return days
    const end = shiftBack(new Date(), preset, offset)
    const start = shiftBack(new Date(end), preset, 1)
    start.setDate(start.getDate() + 1)
    return Math.round((end - start) / 86400000) + 1
  })()

  const canGoForward = offset > 0

  const goBack = useCallback(() => setOffset((o) => o + 1), [])
  const goForward = useCallback(() => setOffset((o) => Math.max(0, o - 1)), [])

  const select = useCallback((label) => {
    setPreset(label)
    setOffset(0)
  }, [])

  const windowLabel = (() => {
    if (isAll) return 'All time'
    if (offset === 0) return 'Current'
    const end = shiftBack(new Date(), preset, offset)
    const start = shiftBack(new Date(end), preset, 1)
    start.setDate(start.getDate() + 1)
    if (preset === '1Y') {
      return start.getFullYear().toString()
    }
    const fmt = (d) => d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
    return `${fmt(start)} – ${fmt(end)}`
  })()

  return { preset, days: effectiveDays, offset, startDate, canGoForward, goBack, goForward, select, windowLabel }
}
