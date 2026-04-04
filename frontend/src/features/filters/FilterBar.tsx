import { useFilterStore } from '@/shared/stores/filterStore'
import { CATEGORY_LABELS, EWASTE_CATEGORIES, METRIC_LABELS, YEAR_RANGE, type ChoroplethMetric } from '@/shared/types'
import ShareButton from './ShareButton'

const METRICS = Object.entries(METRIC_LABELS) as [ChoroplethMetric, string][]

const VIEWS = [
  { key: 'map',    label: 'Map' },
  { key: 'sankey', label: 'Sankey' },
  { key: 'table',  label: 'Data Table' },
] as const

export default function FilterBar() {
  const {
    year, setYear,
    metric, setMetric,
    category, toggleCategory,
    compliantOnly, setCompliantOnly,
    flaggedOnly, setFlaggedOnly,
    topN, setTopN,
    activeView, setActiveView,
  } = useFilterStore()

  const btnBase = 'px-3 py-1.5 text-xs border-b-2 transition-colors whitespace-nowrap'
  const btnActive = 'border-green-700 font-semibold'
  const btnInactive = 'border-transparent hover:border-stone-300'

  return (
    <div
      className="flex flex-wrap items-center gap-x-4 gap-y-1 px-4 py-1.5 text-xs"
      style={{ background: 'var(--c-surface)', borderBottom: '1px solid var(--c-border)', color: 'var(--c-text-2)' }}
    >
      {/* View toggle — tab style */}
      <div className="flex items-center" style={{ gap: 0 }}>
        {VIEWS.map(({ key, label }) => (
          <button
            key={key}
            onClick={() => setActiveView(key)}
            className={`${btnBase} ${activeView === key ? btnActive : btnInactive}`}
            style={{
              color: activeView === key ? 'var(--c-accent)' : 'var(--c-text-2)',
              background: 'transparent',
            }}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="w-px h-4 shrink-0" style={{ background: 'var(--c-border)' }} />

      {/* Year slider */}
      <label className="flex items-center gap-2">
        <span style={{ color: 'var(--c-text-3)' }}>Year</span>
        <input
          type="range"
          min={YEAR_RANGE.min}
          max={YEAR_RANGE.max}
          value={year}
          onChange={(e) => setYear(Number(e.target.value))}
          className="w-24"
          style={{ accentColor: 'var(--c-accent)' }}
        />
        <span className="mono font-semibold w-10" style={{ color: 'var(--c-text)' }}>{year}</span>
      </label>

      {/* Metric selector (map + table views) */}
      {activeView !== 'sankey' && (
        <label className="flex items-center gap-2">
          <span style={{ color: 'var(--c-text-3)' }}>Metric</span>
          <select
            value={metric}
            onChange={(e) => setMetric(e.target.value as ChoroplethMetric)}
            className="text-xs rounded px-2 py-0.5"
            style={{
              background: 'var(--c-surface)',
              color: 'var(--c-text)',
              border: '1px solid var(--c-border)',
            }}
          >
            {METRICS.map(([key, label]) => (
              <option key={key} value={key}>{label}</option>
            ))}
          </select>
        </label>
      )}

      {/* Category multi-select */}
      <div className="flex items-center gap-1">
        <span style={{ color: 'var(--c-text-3)' }}>Category</span>
        <div className="flex gap-1">
          {EWASTE_CATEGORIES.slice(1).map((cat) => (
            <button
              key={cat}
              onClick={() => toggleCategory(cat)}
              title={CATEGORY_LABELS[cat]}
              className="px-1.5 py-0.5 rounded border text-xs transition-colors mono"
              style={{
                background: category.includes(cat) ? 'var(--c-accent)' : 'transparent',
                color: category.includes(cat) ? '#fff' : 'var(--c-text-2)',
                borderColor: category.includes(cat) ? 'var(--c-accent)' : 'var(--c-border)',
              }}
            >
              {cat}
            </button>
          ))}
        </div>
      </div>

      {/* Sankey top-N */}
      {activeView === 'sankey' && (
        <label className="flex items-center gap-2">
          <span style={{ color: 'var(--c-text-3)' }}>Top</span>
          <select
            value={topN}
            onChange={(e) => setTopN(Number(e.target.value))}
            className="text-xs rounded px-2 py-0.5"
            style={{ background: 'var(--c-surface)', color: 'var(--c-text)', border: '1px solid var(--c-border)' }}
          >
            {[10, 20, 30, 50].map((n) => (
              <option key={n} value={n}>{n} flows</option>
            ))}
          </select>
        </label>
      )}

      {/* Compliance toggles */}
      <label className="flex items-center gap-1 cursor-pointer">
        <input
          type="checkbox"
          checked={compliantOnly}
          onChange={(e) => setCompliantOnly(e.target.checked)}
          style={{ accentColor: '#166534' }}
        />
        <span>Compliant only</span>
      </label>

      <label className="flex items-center gap-1 cursor-pointer">
        <input
          type="checkbox"
          checked={flaggedOnly}
          onChange={(e) => setFlaggedOnly(e.target.checked)}
          style={{ accentColor: '#b91c1c' }}
        />
        <span>Flagged only</span>
      </label>

      <div className="ml-auto">
        <ShareButton />
      </div>
    </div>
  )
}
