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
  red: 'Violation',
}

export default function GlobalStateReport({ params }: Props) {
  const year = (params.year as number) ?? 2022

  const choropleth = useQuery({
    queryKey: ['report-choropleth', year],
    queryFn: () => api.getChoropleth('generation', year),
    retry: false,
  })

  const sankey = useQuery({
    queryKey: ['report-sankey', year],
    queryFn: () => api.getSankey({ year, top_n: 15 }),
    retry: false,
  })

  const isReady = choropleth.isSuccess && sankey.isSuccess

  useEffect(() => {
    if (isReady) {
      ;(window as unknown as Record<string, unknown>).__REPORT_READY__ = true
    }
  }, [isReady])

  if (choropleth.isError || sankey.isError) {
    ;(window as unknown as Record<string, unknown>).__REPORT_READY__ = true
    return (
      <div className="report-page" style={{ padding: '40px 48px' }}>
        <p style={{ color: '#991b1b' }}>Data unavailable — could not load report data.</p>
      </div>
    )
  }

  if (!isReady) {
    return (
      <div className="report-page" style={{ padding: '40px 48px', display: 'flex', alignItems: 'center', gap: 10, color: '#6b7280', fontSize: '10pt' }}>
        <svg style={{ width: 18, height: 18, animation: 'spin 1s linear infinite' }} viewBox="0 0 24 24" fill="none">
          <circle cx="12" cy="12" r="10" stroke="#d1d5db" strokeWidth="3" />
          <path d="M4 12a8 8 0 018-8" stroke="#10b981" strokeWidth="3" strokeLinecap="round" />
        </svg>
        <style>{`@keyframes spin { to { transform: rotate(360deg) } }`}</style>
        Loading report data…
      </div>
    )
  }

  const topGenerators = [...(choropleth.data?.countries ?? [])]
    .filter((c) => c.value !== null && !c.is_missing)
    .sort((a, b) => (b.value ?? 0) - (a.value ?? 0))
    .slice(0, 10)

  const totalGeneration = topGenerators.reduce((sum, c) => sum + (c.value ?? 0), 0)

  const links = sankey.data?.links ?? []
  const violations = links.filter((l) => l.has_violation).length
  const compliantCount = links.filter((l) => l.compliance_color === 'green').length
  const complianceRate = links.length > 0 ? (compliantCount / links.length) * 100 : 0

  const maxVolume = Math.max(...links.map((l) => l.volume_mt), 1)
  const nodes = sankey.data?.nodes ?? []
  const nodeName = (id: string) => nodes.find((n) => n.id === id)?.name ?? id

  return (
    <div className="report-page" style={{ padding: '40px 48px' }}>
      {/* Header */}
      <div className="report-header">
        <h1 className="report-title">Global State of E-Waste — {year}</h1>
        <p className="report-subtitle">
          EWasteTradeFlow · Data sourced from UN Global E-Waste Monitor, UN Comtrade, OECD Waste Statistics
        </p>
      </div>

      {/* Key stats */}
      <div className="report-stat-grid">
        <div className="report-stat-card report-avoid-break">
          <p className="report-stat-label">Top-10 Generation (reported)</p>
          <p className="report-stat-value">{formatMT(totalGeneration)}</p>
          <p className="report-stat-note">Sum of top 10 generating countries</p>
        </div>
        <div className="report-stat-card report-avoid-break">
          <p className="report-stat-label">Top-15 routes compliance</p>
          <p className="report-stat-value">{formatPercent(complianceRate)}</p>
          <p className="report-stat-note">{violations} potential Basel violations detected</p>
        </div>
        <div className="report-stat-card report-avoid-break">
          <p className="report-stat-label">Data vintage</p>
          <p className="report-stat-value">{year}</p>
          <p className="report-stat-note">Most recent year in selected dataset</p>
        </div>
      </div>

      {/* Top generators */}
      <h2 className="report-section-title">Top 10 Generating Countries</h2>
      <table className="report-table report-avoid-break">
        <thead>
          <tr>
            <th style={{ width: 32 }}>#</th>
            <th>Country</th>
            <th>Generation (MT)</th>
            <th>Data Confidence</th>
            <th style={{ width: 200 }}>Share of listed total</th>
          </tr>
        </thead>
        <tbody>
          {topGenerators.map((c, i) => {
            const pct = totalGeneration > 0 ? ((c.value ?? 0) / totalGeneration) * 100 : 0
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
                        width: `${pct * 1.5}px`,
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

      {/* Top trade routes */}
      <h2 className="report-section-title">Top 15 Export Routes by Volume</h2>
      <table className="report-table">
        <thead>
          <tr>
            <th style={{ width: 32 }}>#</th>
            <th>Exporter</th>
            <th>Importer</th>
            <th>Volume (MT)</th>
            <th>PRS Flag</th>
            <th>Basel Status</th>
            <th style={{ width: 160 }}>Relative volume</th>
          </tr>
        </thead>
        <tbody>
          {links.slice(0, 15).map((link, i) => (
            <tr key={`${link.source}-${link.target}`}>
              <td style={{ color: '#9ca3af' }}>{i + 1}</td>
              <td style={{ fontWeight: 500 }}>{nodeName(link.source)}</td>
              <td>{nodeName(link.target)}</td>
              <td>{formatMT(link.volume_mt)}</td>
              <td>
                {link.prs_risk_flag ? (
                  <span className="report-badge report-badge-red">High Risk</span>
                ) : (
                  <span className="report-badge report-badge-green">Low</span>
                )}
              </td>
              <td>
                <span className={COMPLIANCE_BADGE[link.compliance_color]}>
                  {COMPLIANCE_LABEL[link.compliance_color]}
                </span>
              </td>
              <td>
                <div
                  style={{
                    height: 8,
                    width: `${(link.volume_mt / maxVolume) * 140}px`,
                    background:
                      link.compliance_color === 'red'
                        ? '#ef4444'
                        : link.compliance_color === 'amber'
                          ? '#f59e0b'
                          : '#10b981',
                    borderRadius: 2,
                  }}
                />
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {/* Footer */}
      <div className="report-footer">
        <span>EWasteTradeFlow · ewaste-tradeflow.vercel.app</span>
        <span>Generated {new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })}</span>
      </div>
    </div>
  )
}
