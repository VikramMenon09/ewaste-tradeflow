import { useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api-client'
import { formatMT, formatPercent } from '@/lib/formatters'
import type { ComplianceColor } from '@/shared/types'

interface Props {
  params: Record<string, unknown>
}

const COMPLIANCE_BADGE: Record<ComplianceColor, string> = {
  green: 'report-badge report-badge-green',
  amber: 'report-badge report-badge-amber',
  red: 'report-badge report-badge-red',
}

const COMPLIANCE_LABEL: Record<ComplianceColor, string> = {
  green: 'Compliant',
  amber: 'Uncertain',
  red: 'Potential Violation',
}

export default function RegionalSummaryReport({ params }: Props) {
  const region = (params.region as string) ?? ''
  const year = (params.year as number) ?? 2022

  // Choropleth for per-country generation breakdown
  const choropleth = useQuery({
    queryKey: ['report-region-choropleth', year],
    queryFn: () => api.getChoropleth('generation', year),
    retry: false,
  })

  const outflows = useQuery({
    queryKey: ['report-region-outflows', year, region],
    queryFn: () =>
      api.getSankey({
        year,
        top_n: 30,
        exporter_region: region || undefined,
      }),
    retry: false,
  })

  const inflows = useQuery({
    queryKey: ['report-region-inflows', year, region],
    queryFn: () =>
      api.getSankey({
        year,
        top_n: 30,
        importer_region: region || undefined,
      }),
    retry: false,
  })

  const isReady =
    (choropleth.isSuccess || choropleth.isError) &&
    (outflows.isSuccess || outflows.isError) &&
    (inflows.isSuccess || inflows.isError)

  useEffect(() => {
    if (isReady) {
      ;(window as unknown as Record<string, unknown>).__REPORT_READY__ = true
    }
  }, [isReady])

  if (!isReady) return null

  // Countries in this region from choropleth data
  const allCountries = choropleth.data?.countries ?? []

  // We don't have region on ChoroplethCountry, so if no region param show all
  const regionCountries = allCountries
    .filter((c) => !c.is_missing && c.value !== null)
    .sort((a, b) => (b.value ?? 0) - (a.value ?? 0))
    .slice(0, 15)

  const regionTotal = regionCountries.reduce((sum, c) => sum + (c.value ?? 0), 0)

  const outflowLinks = outflows.data?.links ?? []
  const inflowLinks = inflows.data?.links ?? []
  const outflowNodes = outflows.data?.nodes ?? []

  const violations = outflowLinks.filter((l) => l.has_violation).length
  const outflowTotal = outflowLinks.reduce((sum, l) => sum + l.volume_mt, 0)
  const inflowTotal = inflowLinks.reduce((sum, l) => sum + l.volume_mt, 0)

  const complianceRate =
    outflowLinks.length > 0
      ? (outflowLinks.filter((l) => l.compliance_color === 'green').length / outflowLinks.length) * 100
      : null

  return (
    <div className="report-page" style={{ padding: '40px 48px' }}>
      {/* Header */}
      <div className="report-header">
        <h1 className="report-title">
          {region ? `${region} — Regional E-Waste Summary` : 'Global Regional Summary'} — {year}
        </h1>
        <p className="report-subtitle">
          EWasteTradeFlow · Data sourced from UN Global E-Waste Monitor, UN Comtrade, OECD Waste Statistics
        </p>
      </div>

      {/* Key stats */}
      <div className="report-stat-grid">
        <div className="report-stat-card report-avoid-break">
          <p className="report-stat-label">Regional generation (top 15)</p>
          <p className="report-stat-value">{formatMT(regionTotal)}</p>
          <p className="report-stat-note">Sum of top 15 countries by reported generation</p>
        </div>
        <div className="report-stat-card report-avoid-break">
          <p className="report-stat-label">Total exports (top 30 routes)</p>
          <p className="report-stat-value">{formatMT(outflowTotal)}</p>
          <p className="report-stat-note">{violations} potential Basel violations in top routes</p>
        </div>
        <div className="report-stat-card report-avoid-break">
          <p className="report-stat-label">Export route compliance</p>
          <p className="report-stat-value">{complianceRate !== null ? formatPercent(complianceRate) : '—'}</p>
          <p className="report-stat-note">Of top 30 export routes from this region</p>
        </div>
      </div>

      {/* Country breakdown */}
      <h2 className="report-section-title">
        {region ? `Countries in ${region}` : 'Top Generating Countries'} by Generation
      </h2>
      <table className="report-table report-avoid-break">
        <thead>
          <tr>
            <th style={{ width: 32 }}>#</th>
            <th>Country</th>
            <th>Generation (MT)</th>
            <th>Confidence</th>
            <th style={{ width: 140 }}>Share of listed total</th>
          </tr>
        </thead>
        <tbody>
          {regionCountries.map((c, i) => {
            const pct = regionTotal > 0 ? ((c.value ?? 0) / regionTotal) * 100 : 0
            return (
              <tr key={c.iso3}>
                <td style={{ color: '#9ca3af' }}>{i + 1}</td>
                <td style={{ fontWeight: 500 }}>{c.name}</td>
                <td>{formatMT(c.value)}</td>
                <td>
                  <span
                    className={
                      c.confidence_tier === 'reported'
                        ? 'report-badge report-badge-green'
                        : 'report-badge report-badge-amber'
                    }
                  >
                    {c.confidence_tier ?? 'Unknown'}
                  </span>
                </td>
                <td>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <div
                      style={{
                        height: 8,
                        width: `${Math.round(pct * 1.2)}px`,
                        background: '#10b981',
                        borderRadius: 2,
                        flexShrink: 0,
                      }}
                    />
                    <span style={{ fontSize: '8.5pt', color: '#6b7280' }}>{pct.toFixed(1)}%</span>
                  </div>
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>

      {/* Outflow routes */}
      <h2 className="report-section-title">Top Export Routes {region ? `from ${region}` : ''}</h2>
      {outflowLinks.length === 0 ? (
        <p style={{ color: '#9ca3af', fontSize: '9pt' }}>No outflow data available for this region and year.</p>
      ) : (
        <table className="report-table report-avoid-break">
          <thead>
            <tr>
              <th>From</th>
              <th>To</th>
              <th>Volume (MT)</th>
              <th>PRS Flag</th>
              <th>Basel</th>
            </tr>
          </thead>
          <tbody>
            {outflowLinks.slice(0, 10).map((link) => {
              const srcName = outflowNodes.find((n) => n.id === link.source)?.name ?? link.source
              const dstName = outflowNodes.find((n) => n.id === link.target)?.name ?? link.target
              return (
                <tr key={`${link.source}-${link.target}`}>
                  <td style={{ fontWeight: 500 }}>{srcName}</td>
                  <td>{dstName}</td>
                  <td>{formatMT(link.volume_mt)}</td>
                  <td>
                    {link.prs_risk_flag ? (
                      <span className="report-badge report-badge-red">High</span>
                    ) : (
                      <span className="report-badge report-badge-green">Low</span>
                    )}
                  </td>
                  <td>
                    <span className={COMPLIANCE_BADGE[link.compliance_color]}>
                      {COMPLIANCE_LABEL[link.compliance_color]}
                    </span>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      )}

      {/* Policy gaps */}
      {outflowLinks.some((l) => l.has_violation) && (
        <>
          <h2 className="report-section-title">Policy Gap Alerts</h2>
          <div
            style={{
              background: '#fee2e2',
              border: '1px solid #fca5a5',
              borderRadius: 6,
              padding: '12px 16px',
              fontSize: '9.5pt',
              color: '#7f1d1d',
            }}
            className="report-avoid-break"
          >
            <strong>{violations} potential Basel Convention violation{violations !== 1 ? 's' : ''}</strong>{' '}
            detected in the top 30 export routes from this region. These routes involve exports from Basel-ratified
            countries to destinations that have not ratified the Basel Ban Amendment, consistent with prohibited
            hazardous waste transfers. Total volume in flagged routes:{' '}
            <strong>
              {formatMT(outflowLinks.filter((l) => l.has_violation).reduce((s, l) => s + l.volume_mt, 0))}
            </strong>
            .
          </div>
        </>
      )}

      {/* Import flow summary */}
      {inflowTotal > 0 && (
        <>
          <h2 className="report-section-title">Inbound E-Waste Flows {region ? `to ${region}` : ''}</h2>
          <div className="report-stat-grid" style={{ marginTop: 0, marginBottom: 16 }}>
            <div className="report-stat-card">
              <p className="report-stat-label">Total imports (top 30 routes)</p>
              <p className="report-stat-value">{formatMT(inflowTotal)}</p>
            </div>
            <div className="report-stat-card">
              <p className="report-stat-label">Inflow high-risk routes</p>
              <p className="report-stat-value">{inflowLinks.filter((l) => l.prs_risk_flag).length}</p>
              <p className="report-stat-note">Flagged by PRS model</p>
            </div>
            <div className="report-stat-card">
              <p className="report-stat-label">Net trade position</p>
              <p className="report-stat-value">
                {outflowTotal > inflowTotal ? 'Net Exporter' : 'Net Importer'}
              </p>
              <p className="report-stat-note">
                {formatMT(Math.abs(outflowTotal - inflowTotal))} net {outflowTotal > inflowTotal ? 'outflow' : 'inflow'}
              </p>
            </div>
          </div>
        </>
      )}

      <div className="report-footer">
        <span>EWasteTradeFlow · ewaste-tradeflow.vercel.app</span>
        <span>Generated {new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })}</span>
      </div>
    </div>
  )
}
