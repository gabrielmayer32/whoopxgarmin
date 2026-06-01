import { PRESETS } from '../hooks/useDateRange'

export default function DateRangeSelector({ preset, offset, windowLabel, canGoForward, onSelect, onBack, onForward }) {
  const isAll = preset === 'All'

  return (
    <div className="flex items-center gap-2">
      {/* Preset pills */}
      <div className="flex gap-1">
        {PRESETS.map(({ label }) => (
          <button
            key={label}
            onClick={() => onSelect(label)}
            className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-colors ${
              preset === label
                ? 'bg-blue/20 text-blue border border-blue/40'
                : 'text-muted hover:text-white hover:bg-surface-2'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Navigation — hidden for All */}
      {!isAll && (
        <div className="flex items-center gap-1 ml-1">
          <button
            onClick={onBack}
            className="w-6 h-6 flex items-center justify-center rounded-lg text-muted hover:text-white hover:bg-surface-2 transition-colors text-sm"
            title="Previous period"
          >
            ‹
          </button>
          <span className="text-xs text-muted min-w-[90px] text-center tabular-nums">
            {windowLabel}
          </span>
          <button
            onClick={onForward}
            disabled={!canGoForward}
            className={`w-6 h-6 flex items-center justify-center rounded-lg transition-colors text-sm ${
              canGoForward
                ? 'text-muted hover:text-white hover:bg-surface-2'
                : 'text-muted/30 cursor-not-allowed'
            }`}
            title="Next period"
          >
            ›
          </button>
        </div>
      )}
    </div>
  )
}
