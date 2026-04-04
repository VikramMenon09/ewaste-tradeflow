import { useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api-client'
import { formatMT, formatPercent, formatPRS } from '@/lib/formatters'
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
  red: 'Violation',
}

const INCOME_LABELS: Record<string, string> = {
  high: 'High Income',
  upper_middle: 'Upper Middle Income',
  lower_middle: 'Lower Middle Income',
  low: 'Low Income',
}

export default function CountryProfileReport({ params }: Props) {
  const iso3 = (params.iso3 as string) ?? ''

  const profile = useQuery({
    queryKey: ['report-country-profile', iso3],
    queryFn: () => api.getCountryProfile(iso3),
    enabled: !!iso3,
    retry: false,
  })

  const isReady = profile.isSuccess || profile.isError || !iso3

  useEffect(() => {
    if (isReady) {
      ;(window as unknown as Record<string, unknown>).__REPORT_READY__ = true
    }
  }, [isReady])

  if (!iso3) {
    ;(window as unknown as Record<string, unknown>).__REPORT_READY__ = true
    return (
      <div className="report-page" style={{ padding: '40px 48px' }}>
        <p style={{ color: '#991b1b' }}>No country specified — pass iso3 in report params.</p>
      </div>
    )
  }

  if (profile.isError) {
    return (
      <div className="report-page" style={{ padding: '40px 48px' }}>
        <p style={{ color: '#991b1b' }}>Could not load country profile for {iso3}.</p>
      </div>
    )
  }

  if (!profile.isSuccess) return null

  const p = profile.data
  const series = p.generation_series.slice().sort((a, b) => a.year - b.year)
  const latestYear = series[series.length - 1]
  const maxMT = Math.max(...series.map((s) => s.total_mt), 1)

  const prsColor =
    p.prs_score === null ? 'gray' : p.prs_score >= 7 ? 'red' : p.prs_score >= 4 ? 'amber' : 'green'

  return (
    <div className="report-page" style={{ padding: '40px 48px' }}>
      {/* Header */}
      <div className="report-header">
        <h1 className="report-title">{p.name} — E-Waste Country Profile</h1>
        <p className="report-subtitle">
          {p.region} · {p.subregion} ·{' '}
          {INCOME_LABELS[p.income_classification] ?? p.income_classification} ·
          EWasteTradeFlow — UN, Comtrade, OECD data
        </p>
      </div>

      {/* Key stats */}
      <div className="report-stat-grid">
        <div className="report-stat-card report-avoid-break">
          <p className="report-stat-label">Latest generation</p>
          <p className="report-stat-value">{formatMT(latestYear?.total_mt)}</p>
          <p className="report-stat-note">{latestYear?.year ?? '—'} · {latestYear?.confidence_tier ?? ''}</p>
        </div>
        <div className="report-stat-card report-avoid-break">
          <p className="report-stat-label">Formal collection rate</p>
          <p className="report-stat-value">{formatPercent(latestYear?.formal_collection_rate ?? null)}</p>
          <p className="report-stat-note">Share formally documented as recycled</p>
        </div>
        <div className="report-stat-card report-avoid-break">
          <p className="report-stat-label">Processing Risk Score</p>
          <p className="report-stat-value">{formatPRS(p.prs_score)} / 10</p>
          <p className="report-stat-note">
            <span className={`report-badge report-badge-${prsColor}`}>
              {prsColor === 'red' ? 'High risk' : prsColor === 'amber' ? 'Moderate risk' : 'Low risk'}
            </span>
          </p>
        </div>
      </div>

      {/* Treaty status */}
      <h2 className="report-section-title">Treaty & Policy Status</h2>
      <table className="report-table report-avoid-break">
        <tbody>
          <tr>
            <td style={{ fontWeight: 500, width: 220 }}>Basel Convention signatory</td>
            <td>
              <span className={`report-badge ${p.basel_signatory ? 'report-badge-green' : 'report-badge-red'}`}>
                {p.basel_signatory ? 'Yes' : 'No'}
              </span>
            </td>
          </tr>
          <tr>
            <td style={{ fontWeight: 500 }}>Basel Ban Amendment ratified</td>
            <td>
              <span className={`report-badge ${p.basel_ban_ratified ? 'report-badge-green' : 'report-badge-amber'}`}>
                {p.basel_ban_ratified ? 'Ratified' : 'Not ratified'}
              </span>
            </td>
          </tr>
          <tr>
            <td style={{ fontWeight: 500 }}>OECD member</td>
            <td>
              <span className={`report-badge ${p.is_oecd_member ? 'report-badge-blue' : 'report-badge-gray'}`}>
                {p.is_oecd_member ? 'Yes' : 'No'}
              </span>
            </td>
          </tr>
        </tbody>
      </table>

      {/* Generation time series bar chart */}
      <h2 className="report-section-title">E-Waste Generation Trend</h2>
      <div className="report-bar-chart report-avoid-break" style={{ padding: '8px 0 16px' }}>
        <svg
          width="100%"
          viewBox={`0 0 ${series.length * 36 + 40} 120`}
          preserveAspectRatio="xMinYMid meet"
          aria-label="E-waste generation bar chart"
        >
          {series.map((pt, i) => {
            const barH = (pt.total_mt / maxMT) * 80
            const x = 20 + i * 36
            const isInterpolated = pt.is_interpolated
            return (
              <g key={pt.year}>
                <rect
                  x={x}
                  y={90 - barH}
                  width={26}
                  height={barH}
                  fill={isInterpolated ? '#a7f3d0' : '#10b981'}
                  rx={2}
                />
                <text
                  x={x + 13}
                  y={108}
                  textAnchor="middle"
                  fontSize={7}
                  fill="#6b7280"
                >
                  {String(pt.year).slice(2)}
                </text>
                <text
                  x={x + 13}
                  y={88 - barH}
                  textAnchor="middle"
                  fontSize={6.5}
                  fill="#374151"
                >
                  {pt.total_mt >= 1000
                    ? `${(pt.total_mt / 1000).toFixed(0)}k`
                    : pt.total_mt.toFixed(0)}
                </text>
              </g>
            )
          })}
          {/* Y-axis label */}
          <text x={8} y={50} textAnchor="middle" fontSize={7} fill="#9ca3af" transform="rotate(-90, 8, 50)">
            MT
          </text>
        </svg>
        <p style={{ fontSize: '7.5pt', color: '#9ca3af', marginTop: 4 }}>
          Light green bars indicate interpolated/estimated values. Dark green = officially reported.
        </p>
      </div>

      {/* Trade partners */}
      <div className="report-cols">
        <div>
          <h2 className="report-section-title">Top Export Destinations</h2>
          <table className="report-table report-avoid-break">
            <thead>
              <tr>
                <th>Destination</th>
                <th>Volume (MT)</th>
                <th>Basel</th>
              </tr>
            </thead>
            <tbody>
              {p.top_exports.length === 0 ? (
                <tr>
                  <td colSpan={3} style={{ color: '#9ca3af' }}>No export data available</td>
                </tr>
              ) : (
                p.top_exports.map((ex) => (
                  <tr key={ex.partner_iso3}>
                    <td style={{ fontWeight: 500 }}>{ex.partner_name}</td>
                    <td>{formatMT(ex.volume_mt)}</td>
                    <td>
                      <span className={COMPLIANCE_BADGE[ex.compliance_color]}>
                        {COMPLIANCE_LABEL[ex.compliance_color]}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        <div>
          <h2 className="report-section-title">Top Import Sources</h2>
          <table className="report-table report-avoid-break">
            <thead>
              <tr>
                <th>Origin</th>
                <th>Volume (MT)</th>
                <th>PRS</th>
              </tr>
            </thead>
            <tbody>
              {p.top_imports.length === 0 ? (
                <tr>
                  <td colSpan={3} style={{ color: '#9ca3af' }}>No import data available</td>
                </tr>
              ) : (
                p.top_imports.map((im) => (
                  <tr key={im.partner_iso3}>
                    <td style={{ fontWeight: 500 }}>{im.partner_name}</td>
                    <td>{formatMT(im.volume_mt)}</td>
                    <td>
                      {im.prs_risk_flag ? (
                        <span className="report-badge report-badge-red">High risk</span>
                      ) : (
                        <span className="report-badge report-badge-green">Low</span>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div className="report-footer">
        <span>EWasteTradeFlow · ewaste-tradeflow.vercel.app</span>
        <span>Generated {new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })}</span>
      </div>
    </div>
  )
}
