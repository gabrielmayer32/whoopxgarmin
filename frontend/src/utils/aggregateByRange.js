// Groups daily data into weekly or monthly buckets depending on range size.
// For each bucket, numeric fields are averaged; the date is the bucket start.
// Returns raw data unchanged when range is <= 90 days.

function isoWeek(dateStr) {
  const d = new Date(dateStr)
  const day = d.getUTCDay() || 7
  d.setUTCDate(d.getUTCDate() + 4 - day)
  const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1))
  const week = Math.ceil(((d - yearStart) / 86400000 + 1) / 7)
  return `${d.getUTCFullYear()}-W${String(week).padStart(2, '0')}`
}

function isoMonth(dateStr) {
  return dateStr.slice(0, 7)
}

function bucketKey(dateStr, days) {
  if (days <= 90) return dateStr
  if (days <= 365) return isoWeek(dateStr)
  return isoMonth(dateStr)
}

function bucketLabel(key, days) {
  if (days <= 90) return key.slice(5) // MM-DD
  if (days <= 365) {
    // Parse ISO week back to a readable date (Monday of that week)
    const [year, w] = key.split('-W').map(Number)
    const jan4 = new Date(Date.UTC(year, 0, 4))
    const monday = new Date(jan4)
    monday.setUTCDate(jan4.getUTCDate() - ((jan4.getUTCDay() || 7) - 1) + (w - 1) * 7)
    return monday.toLocaleDateString('en-US', { month: 'short', day: 'numeric', timeZone: 'UTC' })
  }
  // Monthly: "Jan '24"
  const [year, month] = key.split('-')
  const d = new Date(Date.UTC(Number(year), Number(month) - 1, 1))
  return d.toLocaleDateString('en-US', { month: 'short', year: '2-digit', timeZone: 'UTC' })
}

export default function aggregateByRange(data, days) {
  if (!data?.length || days <= 90) {
    return data.map((d) => ({ ...d, date: d.date?.slice(5) ?? d.date }))
  }

  const buckets = new Map()

  for (const row of data) {
    if (!row.date) continue
    const key = bucketKey(row.date, days)
    if (!buckets.has(key)) buckets.set(key, { _rows: [], _key: key })
    buckets.get(key)._rows.push(row)
  }

  return Array.from(buckets.values()).map(({ _rows, _key }) => {
    const agg = { date: bucketLabel(_key, days) }
    const numericKeys = Object.keys(_rows[0]).filter(
      (k) => k !== 'date' && typeof _rows[0][k] === 'number'
    )
    for (const k of numericKeys) {
      const vals = _rows.map((r) => r[k]).filter((v) => v != null && !isNaN(v))
      agg[k] = vals.length ? parseFloat((vals.reduce((a, b) => a + b, 0) / vals.length).toFixed(1)) : null
    }
    return agg
  })
}
