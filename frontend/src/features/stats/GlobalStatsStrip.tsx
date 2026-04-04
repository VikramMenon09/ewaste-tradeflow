import { useMemo } from 'react'
import { useFilterStore } from '@/shared/stores/filterStore'
import { useMapData } from '@/features/map/useMapData'
import { METRIC_LABELS } from '@/shared/types'

function fmtNum(value: number, metric: string): string {
  if (metric === 'prs') return value.toFixed(2)
  if (metric === 'per_capita') return `${value.toFixed(1)} kg`
  if (metric === 'formal_collection' || metric === 'compliance_rate' || metric === 'export_intensity') {
    return `${(value * 100).toFixed(1)}%`
  }
  if (Math.abs(value) >= 1_000_000) return `${(value / 1_000_000).toFixed(2)}M t`
  if (Math.abs(value) >= 1_000) return `${(value / 1_000).toFixed(1)}k t`
  return value.toFixed(1) + ' t'
}

export default function GlobalStatsStrip() {
  const { metric, year } = useFilterStore()
  const { data, isLoading } = useMapData(metric, year)

  const stats = useMemo(() => {
    if (!data) return null
    const countries = data.countries
    const withData = countries.filter((c) => !c.is_missing && c.value !== null)
    const values = withData.map((c) => c.value as number)
    const total = values.reduce((s, v) => s + v, 0)
    const avg = values.length ? total / values.length : 0
    const max = values.length ? Math.max(...values) : 0
    const maxCountry = withData.find((c) => c.value === max)
    const reported = withData.filter((c) => c.confidence_tier === 'reported').length
    const pctReported = withData.length ? Math.round((reported / withData.length) * 100) : 0

    return { total, avg, max, maxCountry, pctReported, n: withData.length, total_countries: countries.length }
  }, [data])

  const isAggregate = !['prs', 'per_capita', 'formal_collection', 'compliance_rate', 'export_intensity'].includes(metric)

  const cells: { label: string; value: string; note?: string }[] = stats
    ? [
        {
          label: isAggregate ? 'Global total' : 'Global avg',
          value: fmtNum(isAggregate ? stats.total : stats.avg, metric),
          note: METRIC_LABELS[metric],
        },
        {
          label: 'Countries w/ data',
          value: `${stats.n} / ${stats.total_countries}`,
          note: `${stats.pctReported}% directly reported`,
        },
        {
          label: 'Highest',
          value: fmtNum(stats.max, metric),
          note: stats.maxCountry ? `${stats.maxCountry.name} (${stats.maxCountry.iso3})` : '',
        },
        {
          label: 'Year',
          value: String(year),
          note: 'Reference year',
        },
      ]
    : []

  return (
    <div
      className="flex items-stretch text-xs shrink-0"
      style={{ borderBottom: '1px solid var(--c-border)', background: 'var(--c-raised)' }}
    >
      {isLoading
        ? <div className="px-4 py-1.5" style={{ color: 'var(--c-text-3)' }}>Loading global statistics…</div>
        : cells.map((cell, i) => (
          <div
            key={i}
            className="flex flex-col justify-center px-5 py-1"
            style={{ borderRight: '1px solid var(--c-border)', minWidth: 160 }}
          >
            <span style={{ color: 'var(--c-text-3)', fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              {cell.label}
            </span>
            <span className="mono font-semibold" style={{ color: 'var(--c-text)', fontSize: '13px', lineHeight: 1.3 }}>
              {cell.value}
            </span>
            {cell.note && (
              <span style={{ color: 'var(--c-text-3)', fontSize: '9.5px' }}>{cell.note}</span>
            )}
          </div>
        ))
      }
    </div>
  )
}
