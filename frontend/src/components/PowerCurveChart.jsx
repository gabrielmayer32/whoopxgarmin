import { colors } from '../colors.js'
import { useRef, useState, useCallback, useEffect } from 'react'
import { line as d3line, curveCatmullRom } from 'd3-shape'
import { scaleLog, scaleLinear } from 'd3-scale'

const W = 560
const H = 300
const PAD = { top: 12, right: 16, bottom: 28, left: 48 }
const INNER_W = W - PAD.left - PAD.right
const INNER_H = H - PAD.top - PAD.bottom

function fmtSec(s) {
  if (s < 60) return `${s}s`
  if (s < 3600) {
    const m = Math.floor(s / 60), r = s % 60
    return r ? `${m}m ${r}s` : `${m}m`
  }
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60)
  return m ? `${h}h ${m}m` : `${h}h`
}

// monotone interpolation at x between two points
function interpY(x0, y0, x1, y1, x) {
  if (x <= x0) return y0
  if (x >= x1) return y1
  const t = (x - x0) / (x1 - x0)
  // cubic hermite (catmull-rom approximation — simple lerp for adjacent segments)
  return y0 + (y1 - y0) * t
}

function interpolateAtX(points, xVal) {
  // points: [{sec, val}] sorted by sec, all non-null
  if (!points.length) return null
  if (xVal <= points[0].sec) return points[0].val
  if (xVal >= points[points.length - 1].sec) return points[points.length - 1].val
  for (let i = 0; i < points.length - 1; i++) {
    if (xVal >= points[i].sec && xVal <= points[i + 1].sec) {
      return interpY(points[i].sec, points[i].val, points[i + 1].sec, points[i + 1].val, xVal)
    }
  }
  return null
}

export default function PowerCurveChart({ data, compareLabel, seriesColors = {} }) {
  const svgRef = useRef(null)
  const containerRef = useRef(null)
  const [cursor, setCursor] = useState(null) // {svgX, sec, values}
  const [dims, setDims] = useState({ w: W })

  useEffect(() => {
    if (!containerRef.current) return
    const ro = new ResizeObserver(([entry]) => {
      setDims({ w: entry.contentRect.width || W })
    })
    ro.observe(containerRef.current)
    return () => ro.disconnect()
  }, [])

  const innerW = dims.w - PAD.left - PAD.right

  // Build series — filter null values per series
  const series = [
    { key: 'power', label: 'This ride', color: seriesColors.power || colors.purple },
    compareLabel ? { key: 'compare', label: compareLabel, color: seriesColors.compare || colors.amber } : null,
    { key: 'best', label: '90d best', color: seriesColors.best || colors.blue },
  ].filter(Boolean)

  const allSecs = data.map(d => d.sec)
  const allVals = data.flatMap(d => series.map(s => d[s.key]).filter(v => v != null))

  const xScale = scaleLog()
    .domain([allSecs[0], allSecs[allSecs.length - 1]])
    .range([0, innerW])
    .clamp(true)

  const rawMin = Math.min(...allVals)
  const rawMax = Math.max(...allVals)
  const padding = (rawMax - rawMin) * 0.15 || 20
  const yMin = Math.floor(rawMin - padding)
  const yMax = Math.ceil(rawMax + padding * 0.5)
  const yScale = scaleLinear().domain([yMin, yMax]).range([INNER_H, 0]).clamp(true)

  const makeLine = (key) => {
    const pts = data.filter(d => d[key] != null)
    if (pts.length < 2) return null
    return d3line()
      .x(d => xScale(d.sec))
      .y(d => yScale(d[key]))
      .curve(curveCatmullRom.alpha(0.5))(pts)
  }

  // Y-axis ticks
  const yTicks = yScale.ticks(8)

  // X-axis ticks (the actual data points)
  const xTicks = data.map(d => ({ sec: d.sec, label: d.label }))

  const handleMouseMove = useCallback((e) => {
    const svg = svgRef.current
    if (!svg) return
    const rect = svg.getBoundingClientRect()
    const svgX = (e.clientX - rect.left - PAD.left)
    const clampedX = Math.max(0, Math.min(innerW, svgX))
    // invert log scale
    const sec = Math.round(xScale.invert(clampedX))

    const values = {}
    series.forEach(({ key }) => {
      const pts = data.filter(d => d[key] != null).map(d => ({ sec: d.sec, val: d[key] }))
      values[key] = interpolateAtX(pts, sec)
    })
    setCursor({ svgX: clampedX, sec, values })
  }, [data, series, xScale, innerW])

  const handleMouseLeave = useCallback(() => setCursor(null), [])

  // Tooltip position — flip left when near right edge
  const tooltipX = cursor ? (cursor.svgX > innerW * 0.65 ? cursor.svgX - 130 : cursor.svgX + 12) : 0

  return (
    <div ref={containerRef} className="w-full select-none" style={{ height: H, minHeight: H }}>
      <svg
        ref={svgRef}
        width="100%"
        height={H}
        viewBox={`0 0 ${dims.w} ${H}`}
        onMouseMove={handleMouseMove}
        onMouseLeave={handleMouseLeave}
        style={{ cursor: 'crosshair' }}
      >
        <g transform={`translate(${PAD.left},${PAD.top})`}>
          {/* Grid lines */}
          {yTicks.map(t => (
            <line key={t} x1={0} x2={innerW} y1={yScale(t)} y2={yScale(t)}
              stroke={colors.border} strokeDasharray="3 3" />
          ))}
          {xTicks.map(({ sec }) => (
            <line key={sec} x1={xScale(sec)} x2={xScale(sec)} y1={0} y2={INNER_H}
              stroke={colors.border} strokeDasharray="3 3" />
          ))}

          {/* Area fills (subtle) */}
          {series.map(({ key, color }) => {
            const pts = data.filter(d => d[key] != null)
            if (pts.length < 2) return null
            const areaPath = d3line()
              .x(d => xScale(d.sec))
              .y(d => yScale(d[key]))
              .curve(curveCatmullRom.alpha(0.5))(pts)
            // close path at bottom
            const first = pts[0], last = pts[pts.length - 1]
            const closedPath = `${areaPath} L${xScale(last.sec)},${INNER_H} L${xScale(first.sec)},${INNER_H} Z`
            return (
              <path key={`area-${key}`} d={closedPath}
                fill={color} fillOpacity={0.07} stroke="none" />
            )
          })}

          {/* Lines */}
          {series.map(({ key, color }) => {
            const path = makeLine(key)
            if (!path) return null
            const isDashed = key === 'best'
            return (
              <path key={key} d={path} fill="none" stroke={color}
                strokeWidth={key === 'best' ? 1.5 : 2}
                strokeDasharray={isDashed ? '5 3' : undefined}
                strokeLinecap="round" strokeLinejoin="round" />
            )
          })}

          {/* Data point dots */}
          {series.map(({ key, color }) =>
            data.filter(d => d[key] != null).map(d => (
              <circle key={`${key}-${d.sec}`} cx={xScale(d.sec)} cy={yScale(d[key])}
                r={3} fill={color} stroke={colors.surface} strokeWidth={1.5} />
            ))
          )}

          {/* Cursor crosshair */}
          {cursor && (
            <>
              <line x1={cursor.svgX} x2={cursor.svgX} y1={0} y2={INNER_H}
                stroke="#ffffff22" strokeWidth={1} />
              {series.map(({ key, color }) => {
                const v = cursor.values[key]
                if (v == null) return null
                return (
                  <circle key={`cur-${key}`} cx={cursor.svgX} cy={yScale(v)}
                    r={4} fill={color} stroke={colors.surface} strokeWidth={1.5} />
                )
              })}

              {/* Tooltip */}
              {(() => {
                const vals = cursor.values
                // diffs: this ride vs compare (if present), this ride vs best
                const diffs = []
                if (vals.power != null && vals.compare != null) {
                  const pct = ((vals.power - vals.compare) / vals.compare) * 100
                  diffs.push({ label: 'vs compare', pct, colorA: seriesColors.power || colors.purple, colorB: seriesColors.compare || colors.amber })
                }
                if (vals.power != null && vals.best != null) {
                  const pct = ((vals.power - vals.best) / vals.best) * 100
                  diffs.push({ label: 'vs 90d best', pct, colorA: seriesColors.power || colors.purple, colorB: seriesColors.best || colors.blue })
                }
                const tooltipH = series.length * 20 + diffs.length * 18 + 36
                return (
                  <foreignObject x={tooltipX} y={4} width={148} height={tooltipH}
                    style={{ overflow: 'visible' }}>
                    <div className="bg-surface-2 border border-border rounded-xl px-3 py-2 shadow-lg"
                      style={{ fontSize: 11, minWidth: 140 }}>
                      <p className="text-muted mb-1.5" style={{ fontSize: 10 }}>{fmtSec(cursor.sec)}</p>
                      {series.map(({ key, label, color }) => {
                        const v = cursor.values[key]
                        return (
                          <p key={key} style={{ color }} className="font-mono leading-tight">
                            {label}: {v != null ? `${Math.round(v)} W` : '—'}
                          </p>
                        )
                      })}
                      {diffs.length > 0 && (
                        <div className="mt-1.5 pt-1.5 border-t border-border">
                          {diffs.map(({ label, pct }) => {
                            const sign = pct >= 0 ? '+' : ''
                            const col = pct >= 0 ? colors.green : colors.red
                            return (
                              <p key={label} style={{ color: col }} className="font-mono leading-tight">
                                {label}: {sign}{pct.toFixed(1)}%
                              </p>
                            )
                          })}
                        </div>
                      )}
                    </div>
                  </foreignObject>
                )
              })()}
            </>
          )}

          {/* Y axis labels */}
          {yTicks.map(t => (
            <text key={t} x={-6} y={yScale(t) + 4} textAnchor="end"
              fill={colors.muted} fontSize={10}>{t}</text>
          ))}

          {/* X axis labels */}
          {xTicks.map(({ sec, label }) => (
            <text key={sec} x={xScale(sec)} y={INNER_H + 16} textAnchor="middle"
              fill={colors.muted} fontSize={10}>{label}</text>
          ))}

          {/* Axes */}
          <line x1={0} x2={innerW} y1={INNER_H} y2={INNER_H} stroke={colors.border} />
          <line x1={0} x2={0} y1={0} y2={INNER_H} stroke={colors.border} />
        </g>
      </svg>
    </div>
  )
}
