import { BLUE_SCALE, RED_SCALE, type ChoroplethMetric, METRIC_LABELS } from '@/shared/types'

const HIGH_IS_BAD: ChoroplethMetric[] = ['prs', 'net_trade']

const METRIC_DESCRIPTIONS: Partial<Record<ChoroplethMetric, string>> = {
  generation: 'Total e-waste generated across all 6 UN equipment categories (metric tonnes)',
  per_capita: 'E-waste generated per person per year',
  formal_collection: 'Share of e-waste collected by certified recyclers (reported rate)',
  net_trade: 'Exports minus imports — positive values indicate net exporters',
  exports: 'Total e-waste exported to other countries (metric tonnes)',
  imports: 'Total e-waste received from other countries (metric tonnes)',
  prs: 'Processing Risk Score (0–10): likelihood of informal, hazardous recycling',
  export_intensity: 'Exports as a proportion of total domestic generation',
  compliance_rate: 'Share of outbound trade routes compliant with the Basel Convention',
}

function formatLegendValue(value: number, metric: ChoroplethMetric): string {
  if (metric === 'prs') return value.toFixed(1)
  if (metric === 'formal_collection' || metric === 'compliance_rate' || metric === 'export_intensity') {
    return `${(value * 100).toFixed(0)}%`
  }
  if (metric === 'per_capita') return `${value.toFixed(0)} kg`
  if (Math.abs(value) >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M t`
  if (Math.abs(value) >= 1_000) return `${(value / 1_000).toFixed(0)}k t`
  return `${value.toFixed(0)} t`
}

interface MapLegendProps {
  metric: ChoroplethMetric
  min: number
  max: number
  hasData: boolean
}

export default function MapLegend({ metric, min, max, hasData }: MapLegendProps) {
  const scale = HIGH_IS_BAD.includes(metric) ? RED_SCALE : BLUE_SCALE
  const label = METRIC_LABELS[metric]
  const description = METRIC_DESCRIPTIONS[metric]
  const mid = (min + max) / 2
  const isInverted = HIGH_IS_BAD.includes(metric)

  return (
    <div
      className="absolute bottom-8 left-3 z-10 rounded"
      style={{
        width: 210,
        background: 'rgba(255,255,255,0.95)',
        border: '1px solid var(--c-border)',
        padding: '10px 12px',
        boxShadow: '0 2px 8px rgba(0,0,0,0.10)',
      }}
    >
      <p className="font-semibold leading-tight" style={{ color: 'var(--c-text)', fontSize: '11px' }}>{label}</p>

      {description && (
        <p className="leading-snug mt-1" style={{ color: 'var(--c-text-2)', fontSize: '9.5px' }}>
          {description}
        </p>
      )}

      {hasData ? (
        <div className="mt-2">
          {/* Color bar */}
          <div className="flex h-2 rounded overflow-hidden" style={{ border: '1px solid var(--c-border-lt)' }}>
            {scale.map((color, i) => (
              <div key={i} style={{ background: color, flex: 1 }} />
            ))}
          </div>

          {/* Value labels */}
          <div className="flex justify-between mt-1" style={{ fontSize: '9px', fontFamily: 'ui-monospace, monospace' }}>
            <span style={{ color: 'var(--c-text-2)' }}>
              {isInverted ? 'Low risk' : 'Low'} {formatLegendValue(min, metric)}
            </span>
            <span style={{ color: 'var(--c-text-3)' }}>{formatLegendValue(mid, metric)}</span>
            <span style={{ color: 'var(--c-text-2)' }}>
              {formatLegendValue(max, metric)} {isInverted ? 'High risk' : 'High'}
            </span>
          </div>

          {/* No-data swatch */}
          <div className="flex items-center gap-1.5 mt-2 pt-2" style={{ borderTop: '1px solid var(--c-border-lt)' }}>
            <div className="w-3 h-2.5 rounded-sm" style={{ background: '#d6d3ce', border: '1px solid var(--c-border)' }} />
            <span style={{ color: 'var(--c-text-3)', fontSize: '9px' }}>No data / not reported</span>
          </div>
        </div>
      ) : (
        <p className="text-xs mt-2" style={{ color: 'var(--c-text-3)' }}>No data for selected year</p>
      )}
    </div>
  )
}
