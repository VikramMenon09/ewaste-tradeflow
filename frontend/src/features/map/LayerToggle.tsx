import { useFilterStore } from '@/shared/stores/filterStore'
import { METRIC_LABELS, type ChoroplethMetric } from '@/shared/types'

const MAP_METRICS: ChoroplethMetric[] = [
  'generation', 'per_capita', 'exports', 'imports', 'prs', 'compliance_rate',
]

export default function LayerToggle() {
  const { metric, setMetric } = useFilterStore()

  return (
    <div
      className="absolute top-4 right-4 z-10 rounded"
      style={{
        background: 'rgba(255,255,255,0.95)',
        border: '1px solid var(--c-border)',
        padding: '8px',
        boxShadow: '0 2px 8px rgba(0,0,0,0.10)',
        minWidth: 148,
      }}
    >
      <p
        className="font-semibold mb-1"
        style={{ color: 'var(--c-text-3)', fontSize: '9px', textTransform: 'uppercase', letterSpacing: '0.07em' }}
      >
        Metric
      </p>
      {MAP_METRICS.map((m) => (
        <button
          key={m}
          onClick={() => setMetric(m)}
          className="block w-full text-left rounded px-2 py-1 text-xs transition-colors"
          style={{
            background: metric === m ? 'var(--c-accent)' : 'transparent',
            color: metric === m ? '#fff' : 'var(--c-text-2)',
            fontWeight: metric === m ? 600 : 400,
          }}
        >
          {METRIC_LABELS[m]}
        </button>
      ))}
    </div>
  )
}
