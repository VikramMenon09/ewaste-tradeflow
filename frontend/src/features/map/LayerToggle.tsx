import { useFilterStore } from '@/shared/stores/filterStore'
import { METRIC_LABELS, type ChoroplethMetric } from '@/shared/types'
import { IS_STATIC, FULL_STACK_LABEL, isMetricAvailable } from '@/lib/static-data'

const MAP_METRICS: ChoroplethMetric[] = IS_STATIC
  ? ['generation', 'per_capita', 'formal_collection', 'prs', 'exports', 'imports', 'compliance_rate']
  : ['generation', 'per_capita', 'exports', 'imports', 'prs', 'compliance_rate']

export default function LayerToggle() {
  const { metric, setMetric } = useFilterStore()

  return (
    <div
      className="absolute top-4 right-4 z-10 rounded"
      style={{
        background: 'var(--c-surface)',
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
      {MAP_METRICS.map((m) => {
        const available = isMetricAvailable(m)
        return (
          <button
            key={m}
            onClick={() => available && setMetric(m)}
            disabled={!available}
            title={available ? undefined : `${METRIC_LABELS[m]}: ${FULL_STACK_LABEL} (UN Comtrade trade data)`}
            className="block w-full text-left rounded px-2 py-1 text-xs transition-colors disabled:cursor-not-allowed"
            style={{
              background: metric === m ? 'var(--c-accent)' : 'transparent',
              color: metric === m ? '#fff' : available ? 'var(--c-text-2)' : 'var(--c-text-3)',
              fontWeight: metric === m ? 600 : 400,
              opacity: available ? 1 : 0.6,
            }}
          >
            {METRIC_LABELS[m]}
            {!available && <span style={{ fontSize: '9px', display: 'block' }}>{FULL_STACK_LABEL}</span>}
          </button>
        )
      })}
    </div>
  )
}
