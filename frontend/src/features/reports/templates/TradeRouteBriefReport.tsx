import { useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api-client'
import { formatMT, formatUSD } from '@/lib/formatters'
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

export default function TradeRouteBriefReport({ params }: Props) {
  const exporter = (params.exporter as string) ?? ''
  const importer = (params.importer as string) ?? ''
  const year = (params.year as number) ?? 2022

  // Fetch both country profiles and the current-year sankey to locate the link
  const exporterProfile = useQuery({
    queryKey: ['report-profile-exp', exporter],
    queryFn: () => api.getCountryProfile(exporter),
    enabled: !!exporter,
    retry: false,
  })

  const importerProfile = useQuery({
    queryKey: ['report-profile-imp', importer],
    queryFn: () => api.getCountryProfile(importer),
    enabled: !!importer,
    retry: false,
  })

  const sankey = useQuery({
    queryKey: ['report-sankey-route', year],
    queryFn: () => api.getSankey({ year, top_n: 100 }),
    retry: false,
  })

  const isReady =
    (exporterProfile.isSuccess || exporterProfile.isError) &&
    (importerProfile.isSuccess || importerProfile.isError) &&
    (sankey.isSuccess || sankey.isError)

  useEffect(() => {
    if (isReady) {
      ;(window as unknown as Record<string, unknown>).__REPORT_READY__ = true
    }
  }, [isReady])

  if (!exporter || !importer) {
    ;(window as unknown as Record<string, unknown>).__REPORT_READY__ = true
    return (
      <div className="report-page" style={{ padding: '40px 48px' }}>
        <p style={{ color: '#991b1b' }}>Missing exporter or importer in report params.</p>
      </div>
    )
  }

  if (!isReady) return null

  const exp = exporterProfile.data
  const imp = importerProfile.data
  const link = sankey.data?.links.find(
    (l) => l.source === exporter && l.target === importer,
  )

  const exporterName = exp?.name ?? exporter
  const importerName = imp?.name ?? importer

  return (
    <div className="report-page" style={{ padding: '40px 48px' }}>
      {/* Header */}
      <div className="report-header">
        <h1 className="report-title">
          Trade Route Brief: {exporterName} → {importerName}
        </h1>
        <p className="report-subtitle">
          Reporting year: {year} · EWasteTradeFlow — UN Comtrade, OECD, World Bank data
        </p>
      </div>

      {/* Key stats */}
      <div className="report-stat-grid">
        <div className="report-stat-card report-avoid-break">
          <p className="report-stat-label">Trade volume ({year})</p>
          <p className="report-stat-value">{link ? formatMT(link.volume_mt) : '—'}</p>
          <p className="report-stat-note">{link?.value_usd ? `Est. ${formatUSD(link.value_usd)}` : 'Trade value not available'}</p>
        </div>
        <div className="report-stat-card report-avoid-break">
          <p className="report-stat-label">Basel compliance</p>
          <p className="report-stat-value">
            {link ? (
              <span className={COMPLIANCE_BADGE[link.compliance_color]}>
                {COMPLIANCE_LABEL[link.compliance_color]}
              </span>
            ) : (
              '—'
            )}
          </p>
          <p className="report-stat-note">
            {link?.has_violation
              ? 'Potential Basel Convention violation detected'
              : 'No violation flag on this route'}
          </p>
        </div>
        <div className="report-stat-card report-avoid-break">
          <p className="report-stat-label">Importer PRS score</p>
          <p className="report-stat-value">
            {link?.importer_prs_score !== null && link?.importer_prs_score !== undefined
              ? `${link.importer_prs_score.toFixed(1)} / 10`
              : '—'}
          </p>
          <p className="report-stat-note">
            {link?.prs_risk_flag ? (
              <span className="report-badge report-badge-red">High processing risk</span>
            ) : (
              <span className="report-badge report-badge-green">Acceptable risk level</span>
            )}
          </p>
        </div>
      </div>

      {/* Exporter profile summary */}
      <h2 className="report-section-title">Exporting Country — {exporterName}</h2>
      {exp ? (
        <table className="report-table report-avoid-break">
          <tbody>
            <tr>
              <td style={{ fontWeight: 500, width: 220 }}>Region</td>
              <td>{exp.region} / {exp.subregion}</td>
            </tr>
            <tr>
              <td style={{ fontWeight: 500 }}>Basel signatory</td>
              <td>
                <span className={`report-badge ${exp.basel_signatory ? 'report-badge-green' : 'report-badge-red'}`}>
                  {exp.basel_signatory ? 'Yes' : 'No'}
                </span>
              </td>
            </tr>
            <tr>
              <td style={{ fontWeight: 500 }}>Basel Ban Amendment</td>
              <td>
                <span className={`report-badge ${exp.basel_ban_ratified ? 'report-badge-green' : 'report-badge-amber'}`}>
                  {exp.basel_ban_ratified ? 'Ratified' : 'Not ratified'}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      ) : (
        <p style={{ color: '#9ca3af', fontSize: '9pt' }}>Profile data unavailable.</p>
      )}

      {/* Importer profile summary */}
      <h2 className="report-section-title">Importing Country — {importerName}</h2>
      {imp ? (
        <table className="report-table report-avoid-break">
          <tbody>
            <tr>
              <td style={{ fontWeight: 500, width: 220 }}>Region</td>
              <td>{imp.region} / {imp.subregion}</td>
            </tr>
            <tr>
              <td style={{ fontWeight: 500 }}>Basel signatory</td>
              <td>
                <span className={`report-badge ${imp.basel_signatory ? 'report-badge-green' : 'report-badge-red'}`}>
                  {imp.basel_signatory ? 'Yes' : 'No'}
                </span>
              </td>
            </tr>
            <tr>
              <td style={{ fontWeight: 500 }}>Processing Risk Score</td>
              <td>
                {imp.prs_score !== null ? (
                  <span
                    className={`report-badge ${
                      imp.prs_score >= 7
                        ? 'report-badge-red'
                        : imp.prs_score >= 4
                          ? 'report-badge-amber'
                          : 'report-badge-green'
                    }`}
                  >
                    {imp.prs_score.toFixed(1)} / 10
                  </span>
                ) : (
                  <span className="report-badge report-badge-gray">Not scored</span>
                )}
              </td>
            </tr>
            <tr>
              <td style={{ fontWeight: 500 }}>OECD member</td>
              <td>
                <span className={`report-badge ${imp.is_oecd_member ? 'report-badge-blue' : 'report-badge-gray'}`}>
                  {imp.is_oecd_member ? 'Yes' : 'No'}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      ) : (
        <p style={{ color: '#9ca3af', fontSize: '9pt' }}>Profile data unavailable.</p>
      )}

      {/* Route context */}
      {link && (
        <>
          <h2 className="report-section-title">Route Details</h2>
          <table className="report-table report-avoid-break">
            <tbody>
              <tr>
                <td style={{ fontWeight: 500, width: 220 }}>Mapping confidence</td>
                <td>
                  <span
                    className={`report-badge ${
                      link.mapping_confidence === 'HIGH'
                        ? 'report-badge-green'
                        : link.mapping_confidence === 'MEDIUM'
                          ? 'report-badge-amber'
                          : 'report-badge-red'
                    }`}
                  >
                    {link.mapping_confidence}
                  </span>
                </td>
              </tr>
              <tr>
                <td style={{ fontWeight: 500 }}>Data confidence tier</td>
                <td>
                  <span className="report-badge report-badge-gray">{link.confidence_tier}</span>
                </td>
              </tr>
              <tr>
                <td style={{ fontWeight: 500 }}>Data conflict flag</td>
                <td>
                  {link.data_conflict ? (
                    <span className="report-badge report-badge-amber">Conflict detected</span>
                  ) : (
                    <span className="report-badge report-badge-green">No conflict</span>
                  )}
                </td>
              </tr>
            </tbody>
          </table>
        </>
      )}

      {!link && (
        <div style={{ padding: '16px', background: '#fef3c7', borderRadius: 6, fontSize: '9.5pt', color: '#92400e' }}>
          This specific route was not in the top 100 trade routes for {year}. Volume may be below
          the reporting threshold or data may not be available for this year.
        </div>
      )}

      <div className="report-footer">
        <span>EWasteTradeFlow · ewaste-tradeflow.vercel.app</span>
        <span>Generated {new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' })}</span>
      </div>
    </div>
  )
}
