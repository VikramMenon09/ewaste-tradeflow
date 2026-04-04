import DataQualityBadge from '@/shared/components/DataQualityBadge'
import type { ChoroplethCountry, ChoroplethMetric } from '@/shared/types'

interface MapTooltipProps {
  country: ChoroplethCountry
  metric: ChoroplethMetric
  metricLabel: string
  x: number
  y: number
}

function formatValue(value: number | null, metric: ChoroplethMetric): string {
  if (value === null) return 'No data'
  if (metric === 'prs') return `${value.toFixed(2)} / 10`
  if (metric === 'per_capita') return `${value.toLocaleString(undefined, { maximumFractionDigits: 1 })} kg / person`
  if (metric === 'formal_collection' || metric === 'compliance_rate') return `${(value * 100).toFixed(1)}%`
  if (metric === 'export_intensity') return `${(value * 100).toFixed(2)}%`
  if (Math.abs(value) >= 1_000_000) return `${(value / 1_000_000).toFixed(3)}M MT`
  if (Math.abs(value) >= 1_000) return `${(value / 1_000).toFixed(1)}k MT`
  return `${value.toFixed(2)} MT`
}

const METRIC_UNIT_HINT: Partial<Record<ChoroplethMetric, string>> = {
  generation: 'metric tonnes · UN Global E-Waste Monitor',
  per_capita: 'kg per person per year',
  formal_collection: 'certified collection rate',
  exports: 'metric tonnes exported',
  imports: 'metric tonnes imported',
  net_trade: 'positive = net exporter',
  prs: 'Processing Risk Score 0–10',
  compliance_rate: 'Basel-compliant routes',
  export_intensity: 'exports ÷ generation',
}

export default function MapTooltip({ country, metric, metricLabel, x, y }: MapTooltipProps) {
  const isNoData = country.is_missing || country.value === null
  const displayValue = formatValue(country.value, metric)
  const hint = METRIC_UNIT_HINT[metric]

  return (
    <div
      className="fixed z-50 pointer-events-none rounded"
      style={{
        left: x + 14,
        top: y - 10,
        minWidth: 190,
        maxWidth: 230,
        background: 'rgba(255,255,255,0.97)',
        border: '1px solid var(--c-border)',
        boxShadow: '0 4px 16px rgba(0,0,0,0.12)',
        padding: '8px 12px',
        fontSize: '12px',
      }}
    >
      <p className="font-semibold" style={{ color: 'var(--c-text)', fontSize: '13px', marginBottom: 4 }}>
        {country.name}
        <span className="mono font-normal" style={{ color: 'var(--c-text-3)', fontSize: '10px', marginLeft: 6 }}>
          {country.iso3}
        </span>
      </p>

      <div style={{ borderTop: '1px solid var(--c-border-lt)', paddingTop: 6, marginTop: 2 }}>
        <div className="flex items-start justify-between gap-3">
          <span style={{ color: 'var(--c-text-2)' }}>{metricLabel}</span>
          <span
            className="mono font-semibold"
            style={{ color: isNoData ? 'var(--c-text-3)' : 'var(--c-text)', textAlign: 'right' }}
          >
            {displayValue}
          </span>
        </div>

        {hint && !isNoData && (
          <p className="leading-snug mt-1" style={{ color: 'var(--c-text-3)', fontSize: '9.5px' }}>{hint}</p>
        )}

        {country.confidence_tier && !isNoData && (
          <div className="mt-1.5">
            <DataQualityBadge tier={country.confidence_tier} />
          </div>
        )}

        {country.data_vintage_year && !isNoData && (
          <p className="mono mt-0.5" style={{ color: 'var(--c-text-3)', fontSize: '9.5px' }}>
            vintage: {country.data_vintage_year}
          </p>
        )}
      </div>

      <p className="mt-1.5" style={{ color: 'var(--c-text-3)', fontSize: '9px' }}>
        Click for full country profile →
      </p>
    </div>
  )
}
