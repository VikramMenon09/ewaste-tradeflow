import { useState, useMemo } from 'react'
import { useFilterStore } from '@/shared/stores/filterStore'
import { useMapStore } from '@/shared/stores/mapStore'
import { useUIStore } from '@/shared/stores/uiStore'
import { useMapData } from '@/features/map/useMapData'
import { METRIC_LABELS } from '@/shared/types'
import type { ChoroplethCountry, ChoroplethMetric } from '@/shared/types'
import Spinner from '@/shared/components/Spinner'

type SortDir = 'asc' | 'desc'
type SortCol = 'rank' | 'iso3' | 'name' | 'value' | 'confidence_tier' | 'data_vintage_year'

function formatValue(value: number | null, metric: ChoroplethMetric): string {
  if (value === null) return '—'
  if (metric === 'prs') return value.toFixed(2)
  if (metric === 'per_capita') return value.toFixed(1) + ' kg'
  if (metric === 'formal_collection' || metric === 'compliance_rate' || metric === 'export_intensity') {
    return (value * 100).toFixed(1) + '%'
  }
  if (Math.abs(value) >= 1_000_000) return (value / 1_000_000).toFixed(3) + 'M'
  if (Math.abs(value) >= 1_000) return (value / 1_000).toFixed(1) + 'k'
  return value.toFixed(2)
}

const TIER_COLOR: Record<string, string> = {
  reported:     '#166534',
  HIGH:         '#166534',
  estimated:    '#92400e',
  MEDIUM:       '#92400e',
  interpolated: '#92400e',
  LOW:          '#991b1b',
  UNKNOWN:      '#a8a29e',
}

const TIER_CODE: Record<string, string> = {
  reported:     '[R]',
  HIGH:         '[R]',
  estimated:    '[E]',
  MEDIUM:       '[M]',
  interpolated: '[I]',
  LOW:          '[L]',
  UNKNOWN:      '[?]',
}

export default function DataTable() {
  const { metric, year } = useFilterStore()
  const selectCountry = useMapStore((s) => s.selectCountry)
  const openPanel = useUIStore((s) => s.openPanel)
  const { data, isLoading, isError } = useMapData(metric, year)

  const [sortCol, setSortCol] = useState<SortCol>('value')
  const [sortDir, setSortDir] = useState<SortDir>('desc')
  const [search, setSearch] = useState('')

  function handleSort(col: SortCol) {
    if (sortCol === col) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'))
    } else {
      setSortCol(col)
      setSortDir(col === 'value' ? 'desc' : 'asc')
    }
  }

  const sorted = useMemo(() => {
    if (!data) return []
    const filtered = data.countries.filter((c) => {
      if (!search) return true
      const q = search.toLowerCase()
      return c.name.toLowerCase().includes(q) || c.iso3.toLowerCase().includes(q)
    })

    return [...filtered].sort((a, b) => {
      let cmp = 0
      if (sortCol === 'value') {
        const av = a.value ?? -Infinity
        const bv = b.value ?? -Infinity
        cmp = av - bv
      } else if (sortCol === 'name') {
        cmp = a.name.localeCompare(b.name)
      } else if (sortCol === 'iso3') {
        cmp = a.iso3.localeCompare(b.iso3)
      } else if (sortCol === 'confidence_tier') {
        cmp = (a.confidence_tier ?? '').localeCompare(b.confidence_tier ?? '')
      } else if (sortCol === 'data_vintage_year') {
        cmp = (a.data_vintage_year ?? 0) - (b.data_vintage_year ?? 0)
      }
      return sortDir === 'asc' ? cmp : -cmp
    })
  }, [data, sortCol, sortDir, search])

  // Compute global rank by value (descending, ignoring nulls)
  const rankMap = useMemo(() => {
    if (!data) return new Map<string, number>()
    const withValues = [...data.countries]
      .filter((c) => c.value !== null)
      .sort((a, b) => (b.value as number) - (a.value as number))
    return new Map(withValues.map((c, i) => [c.iso3, i + 1]))
  }, [data])

  function handleRowClick(country: ChoroplethCountry) {
    selectCountry(country.iso3)
    openPanel()
  }

  const SortArrow = ({ col }: { col: SortCol }) =>
    sortCol === col ? (
      <span className="mono" style={{ fontSize: '9px', marginLeft: 3 }}>
        {sortDir === 'desc' ? '▼' : '▲'}
      </span>
    ) : (
      <span style={{ fontSize: '9px', marginLeft: 3, opacity: 0.3 }}>⇅</span>
    )

  const thStyle: React.CSSProperties = {
    padding: '6px 12px',
    textAlign: 'left',
    fontSize: '10px',
    fontWeight: 600,
    textTransform: 'uppercase',
    letterSpacing: '0.06em',
    cursor: 'pointer',
    userSelect: 'none',
    whiteSpace: 'nowrap',
    borderBottom: '2px solid var(--c-border)',
    background: 'var(--c-raised)',
    color: 'var(--c-text-2)',
    position: 'sticky',
    top: 0,
    zIndex: 1,
  }

  if (isLoading) return (
    <div className="flex items-center justify-center h-full">
      <Spinner />
    </div>
  )

  if (isError || !data) return (
    <div className="flex items-center justify-center h-full" style={{ color: 'var(--c-text-3)' }}>
      No data available for {year}
    </div>
  )

  return (
    <div className="flex flex-col h-full" style={{ background: 'var(--c-bg)' }}>
      {/* Table controls */}
      <div
        className="flex items-center gap-4 px-4 py-2 shrink-0"
        style={{ borderBottom: '1px solid var(--c-border)', background: 'var(--c-surface)' }}
      >
        <input
          type="search"
          placeholder="Search country or ISO3…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="text-xs px-3 py-1 rounded"
          style={{
            border: '1px solid var(--c-border)',
            background: 'var(--c-bg)',
            color: 'var(--c-text)',
            width: 220,
            fontFamily: 'ui-monospace, monospace',
          }}
        />
        <span className="text-xs" style={{ color: 'var(--c-text-3)' }}>
          {sorted.length} of {data.countries.length} countries ·{' '}
          <span className="mono">{METRIC_LABELS[metric]}</span> · {year}
        </span>
      </div>

      {/* Table */}
      <div className="flex-1 overflow-auto">
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px' }}>
          <thead>
            <tr>
              <th style={thStyle} onClick={() => handleSort('rank')}>
                # <SortArrow col="rank" />
              </th>
              <th style={thStyle} onClick={() => handleSort('iso3')}>
                ISO3 <SortArrow col="iso3" />
              </th>
              <th style={thStyle} onClick={() => handleSort('name')}>
                Country <SortArrow col="name" />
              </th>
              <th style={{ ...thStyle, textAlign: 'right' }} onClick={() => handleSort('value')}>
                {METRIC_LABELS[metric]} <SortArrow col="value" />
              </th>
              <th style={thStyle} onClick={() => handleSort('confidence_tier')}>
                Confidence <SortArrow col="confidence_tier" />
              </th>
              <th style={thStyle} onClick={() => handleSort('data_vintage_year')}>
                Vintage <SortArrow col="data_vintage_year" />
              </th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((country, i) => {
              const rank = rankMap.get(country.iso3)
              const isNull = country.value === null || country.is_missing
              const tier = country.confidence_tier
              const tierCode = tier ? (TIER_CODE[tier] ?? `[${tier[0]}]`) : ''
              const tierColor = tier ? (TIER_COLOR[tier] ?? '#a8a29e') : '#a8a29e'

              return (
                <tr
                  key={country.iso3}
                  onClick={() => handleRowClick(country)}
                  style={{
                    borderBottom: '1px solid var(--c-border-lt)',
                    cursor: 'pointer',
                    background: i % 2 === 0 ? 'var(--c-surface)' : 'var(--c-bg)',
                  }}
                  onMouseEnter={(e) => {
                    ;(e.currentTarget as HTMLTableRowElement).style.background = 'var(--c-accent-bg)'
                  }}
                  onMouseLeave={(e) => {
                    ;(e.currentTarget as HTMLTableRowElement).style.background =
                      i % 2 === 0 ? 'var(--c-surface)' : 'var(--c-bg)'
                  }}
                >
                  <td style={{ padding: '5px 12px', color: 'var(--c-text-3)', fontFamily: 'ui-monospace, monospace', fontSize: '11px' }}>
                    {rank ?? '—'}
                  </td>
                  <td style={{ padding: '5px 12px', fontFamily: 'ui-monospace, monospace', fontWeight: 600, fontSize: '11px', color: 'var(--c-text-2)', letterSpacing: '0.05em' }}>
                    {country.iso3}
                  </td>
                  <td style={{ padding: '5px 12px', color: 'var(--c-text)', fontWeight: 500 }}>
                    {country.name}
                  </td>
                  <td style={{ padding: '5px 12px', textAlign: 'right', fontFamily: 'ui-monospace, monospace', color: isNull ? 'var(--c-text-3)' : 'var(--c-text)', fontWeight: isNull ? 400 : 600 }}>
                    {formatValue(country.value, metric)}
                  </td>
                  <td style={{ padding: '5px 12px', fontFamily: 'ui-monospace, monospace', fontSize: '11px', color: tierColor, fontWeight: 600 }}>
                    {tierCode}
                    <span style={{ fontFamily: 'ui-sans-serif', fontWeight: 400, marginLeft: 4, color: 'var(--c-text-3)', fontSize: '10px' }}>
                      {tier}
                    </span>
                  </td>
                  <td style={{ padding: '5px 12px', fontFamily: 'ui-monospace, monospace', fontSize: '11px', color: 'var(--c-text-3)' }}>
                    {country.data_vintage_year ?? '—'}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      {/* Table footer */}
      <div
        className="shrink-0 px-4 py-1.5 text-xs"
        style={{ borderTop: '1px solid var(--c-border)', background: 'var(--c-raised)', color: 'var(--c-text-3)' }}
      >
        <span className="mono">[R]</span> Reported &nbsp;·&nbsp;
        <span className="mono">&#91;E&#93;</span> Estimated &nbsp;·&nbsp;
        <span className="mono">[I]</span> Interpolated &nbsp;·&nbsp;
        Click any row to open country profile
      </div>
    </div>
  )
}
