import { useMapStore } from '@/shared/stores/mapStore'
import { useUIStore } from '@/shared/stores/uiStore'
import { useCountryProfile } from './useCountryProfile'
import GenerationChart from './GenerationChart'
import Badge from '@/shared/components/Badge'
import Spinner from '@/shared/components/Spinner'
import EmptyState from '@/shared/components/EmptyState'

function fmt(value: number | null | undefined, decimals = 1): string {
  if (value === null || value === undefined) return '—'
  if (Math.abs(value) >= 1_000_000) return `${(value / 1_000_000).toFixed(decimals)}M`
  if (Math.abs(value) >= 1_000) return `${(value / 1_000).toFixed(decimals)}k`
  return value.toFixed(decimals)
}

const S = {
  label: { fontSize: '9.5px', textTransform: 'uppercase' as const, letterSpacing: '0.06em', color: 'var(--c-text-3)', display: 'block' as const },
  value: { fontFamily: 'ui-monospace, monospace', fontWeight: 600, color: 'var(--c-text)', fontSize: '15px' },
  card: { background: 'var(--c-raised)', border: '1px solid var(--c-border-lt)', borderRadius: 4, padding: '8px 10px' },
  divider: { borderTop: '1px solid var(--c-border)', margin: '12px 0' },
  sectionTitle: { fontSize: '9.5px', fontWeight: 600, textTransform: 'uppercase' as const, letterSpacing: '0.07em', color: 'var(--c-text-3)', marginBottom: 8 },
}

export default function CountryPanel() {
  const selectedCountry = useMapStore((s) => s.selectedCountry)
  const clearSelection = useMapStore((s) => s.clearSelection)
  const closePanel = useUIStore((s) => s.closePanel)
  const { data, isLoading, isError } = useCountryProfile()

  function handleClose() {
    clearSelection()
    closePanel()
  }

  const latest = data?.generation_series.at(-1)
  const earliest = data?.generation_series.at(0)
  const growthPct =
    latest && earliest && earliest.total_mt > 0
      ? (((latest.total_mt - earliest.total_mt) / earliest.total_mt) * 100).toFixed(1)
      : null

  const totalExports = data?.top_exports.reduce((s, p) => s + (p.volume_mt ?? 0), 0) ?? 0
  const totalImports = data?.top_imports.reduce((s, p) => s + (p.volume_mt ?? 0), 0) ?? 0

  return (
    <div className="flex flex-col h-full" style={{ fontSize: '12px', color: 'var(--c-text)' }}>
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 py-2.5 shrink-0"
        style={{ borderBottom: '1px solid var(--c-border)', background: 'var(--c-raised)' }}
      >
        <span style={{ ...S.label, marginBottom: 0 }}>Country Profile</span>
        <button
          onClick={handleClose}
          className="transition-colors"
          style={{ color: 'var(--c-text-3)', fontSize: '14px', lineHeight: 1 }}
          aria-label="Close panel"
        >
          ✕
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-4 py-3" style={{ gap: 0 }}>
        {isLoading && (
          <div className="flex justify-center pt-8">
            <Spinner />
          </div>
        )}

        {isError && (
          <EmptyState
            title="Could not load country data"
            description={selectedCountry ?? undefined}
          />
        )}

        {data && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            {/* Name + classification */}
            <div>
              <div className="flex items-baseline gap-2">
                <h2 style={{ fontSize: '16px', fontWeight: 700, color: 'var(--c-text)', margin: 0 }}>{data.name}</h2>
                <span className="mono" style={{ fontSize: '11px', color: 'var(--c-text-3)', fontWeight: 600 }}>{data.iso3}</span>
              </div>
              <p style={{ color: 'var(--c-text-3)', fontSize: '11px', margin: '2px 0 6px' }}>{data.region} · {data.subregion}</p>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                {data.is_oecd_member && <Badge variant="blue">OECD</Badge>}
                {data.basel_signatory && <Badge variant="green">Basel Party</Badge>}
                {data.basel_ban_ratified && <Badge variant="green">Ban Ratified</Badge>}
                {!data.basel_ban_ratified && data.basel_signatory && (
                  <Badge variant="amber">Ban Not Ratified</Badge>
                )}
                {data.income_classification && (
                  <Badge variant="gray">{data.income_classification.replace(/_/g, ' ')}</Badge>
                )}
              </div>
            </div>

            <div style={S.divider} />

            {/* Key indicators grid */}
            {latest && (
              <div>
                <p style={S.sectionTitle}>Key Indicators — {latest.year}</p>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
                  <div style={S.card}>
                    <span style={S.label}>Generation</span>
                    <span style={S.value}>{fmt(latest.total_mt)}</span>
                    <span style={{ ...S.label, textTransform: 'none', letterSpacing: 0, marginTop: 1 }}>metric tonnes</span>
                  </div>
                  <div style={S.card}>
                    <span style={S.label}>Per Capita</span>
                    <span style={S.value}>{latest.per_capita_kg?.toFixed(1) ?? '—'}</span>
                    <span style={{ ...S.label, textTransform: 'none', letterSpacing: 0, marginTop: 1 }}>kg / person</span>
                  </div>
                  {latest.formal_collection_rate !== null && (
                    <div style={{ ...S.card, gridColumn: '1 / -1' }}>
                      <span style={S.label}>Formal Collection Rate</span>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 4 }}>
                        <div style={{ flex: 1, background: 'var(--c-border)', borderRadius: 2, height: 6 }}>
                          <div
                            style={{
                              width: `${Math.min(100, (latest.formal_collection_rate ?? 0) * 100)}%`,
                              background: 'var(--c-accent)',
                              height: 6,
                              borderRadius: 2,
                            }}
                          />
                        </div>
                        <span className="mono" style={{ color: 'var(--c-text)', fontWeight: 600, fontSize: '13px', minWidth: 36, textAlign: 'right' }}>
                          {((latest.formal_collection_rate ?? 0) * 100).toFixed(0)}%
                        </span>
                      </div>
                      <span style={{ ...S.label, textTransform: 'none', letterSpacing: 0, marginTop: 3 }}>
                        share collected by certified recyclers
                      </span>
                    </div>
                  )}
                  {growthPct !== null && (
                    <div style={{ ...S.card, gridColumn: '1 / -1' }}>
                      <span style={S.label}>Growth {earliest?.year}–{latest.year}</span>
                      <span className="mono" style={{ fontWeight: 700, fontSize: '15px', color: Number(growthPct) >= 0 ? '#92400e' : '#166534' }}>
                        {Number(growthPct) >= 0 ? '+' : ''}{growthPct}%
                      </span>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* PRS Score */}
            {data.prs_score !== null && (
              <div style={S.card}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <span style={S.label}>Processing Risk Score</span>
                  <Badge
                    variant={(data.prs_score ?? 0) >= 7 ? 'red' : (data.prs_score ?? 0) >= 4 ? 'amber' : 'green'}
                  >
                    {(data.prs_score ?? 0) >= 7 ? 'High risk' : (data.prs_score ?? 0) >= 4 ? 'Medium' : 'Low risk'}
                  </Badge>
                </div>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: 4 }}>
                  <span className="mono" style={{ fontSize: '22px', fontWeight: 700, color: 'var(--c-text)' }}>
                    {data.prs_score?.toFixed(1)}
                  </span>
                  <span style={{ color: 'var(--c-text-3)', fontSize: '11px' }}>/ 10</span>
                </div>
                <div style={{ background: 'var(--c-border)', borderRadius: 2, height: 5, marginTop: 6 }}>
                  <div
                    style={{
                      width: `${((data.prs_score ?? 0) / 10) * 100}%`,
                      height: 5,
                      borderRadius: 2,
                      background: (data.prs_score ?? 0) >= 7 ? '#991b1b' : (data.prs_score ?? 0) >= 4 ? '#92400e' : '#166534',
                    }}
                  />
                </div>
                <p style={{ ...S.label, textTransform: 'none', letterSpacing: 0, marginTop: 5, lineHeight: 1.4 }}>
                  Composite of governance, infrastructure, and informal sector indicators.
                  Higher = greater risk of hazardous informal processing. PRS v{data.prs_methodology_version ?? 1}.
                </p>
              </div>
            )}

            {/* Generation trend */}
            {data.generation_series.length > 0 && (
              <div>
                <p style={S.sectionTitle}>Generation Trend (MT)</p>
                <GenerationChart data={data.generation_series} />
                <div style={{ display: 'flex', gap: 12, marginTop: 4 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                    <div style={{ width: 16, height: 2, background: '#166534' }} />
                    <span style={{ ...S.label, textTransform: 'none', letterSpacing: 0, marginBottom: 0 }}>Reported</span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                    <div style={{ width: 6, height: 6, borderRadius: '50%', background: '#94a3b8' }} />
                    <span style={{ ...S.label, textTransform: 'none', letterSpacing: 0, marginBottom: 0 }}>Interpolated</span>
                  </div>
                </div>
              </div>
            )}

            {/* Trade flows */}
            {(data.top_exports.length > 0 || data.top_imports.length > 0) && (
              <div>
                <p style={S.sectionTitle}>Trade Flows</p>

                {/* Net position */}
                {totalExports > 0 && totalImports > 0 && (
                  <div style={{ ...S.card, display: 'flex', justifyContent: 'space-around', textAlign: 'center', marginBottom: 10 }}>
                    <div>
                      <span style={S.label}>Exports (top)</span>
                      <span className="mono" style={{ fontSize: '12px', fontWeight: 600, color: 'var(--c-text)', display: 'block' }}>{fmt(totalExports)} MT</span>
                    </div>
                    <div style={{ borderLeft: '1px solid var(--c-border)' }} />
                    <div>
                      <span style={S.label}>Imports (top)</span>
                      <span className="mono" style={{ fontSize: '12px', fontWeight: 600, color: 'var(--c-text)', display: 'block' }}>{fmt(totalImports)} MT</span>
                    </div>
                    <div style={{ borderLeft: '1px solid var(--c-border)' }} />
                    <div>
                      <span style={S.label}>Net position</span>
                      <span style={{ fontSize: '11px', fontWeight: 600, color: totalExports > totalImports ? '#92400e' : '#166534', display: 'block' }}>
                        {totalExports > totalImports ? '▲ Exporter' : '▼ Importer'}
                      </span>
                    </div>
                  </div>
                )}

                {/* Export partners */}
                {data.top_exports.length > 0 && (
                  <div style={{ marginBottom: 10 }}>
                    <p style={{ ...S.label, textTransform: 'none', letterSpacing: 0, marginBottom: 4, fontWeight: 600, color: 'var(--c-text-2)' }}>
                      Top Export Destinations
                    </p>
                    {data.top_exports.map((p) => (
                      <div
                        key={p.partner_iso3}
                        style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '3px 0', borderBottom: '1px solid var(--c-border-lt)' }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                          <span
                            style={{
                              width: 8, height: 8, borderRadius: '50%', flexShrink: 0,
                              background: p.compliance_color === 'green' ? '#166534' : p.compliance_color === 'red' ? '#991b1b' : '#92400e',
                            }}
                          />
                          <span style={{ color: 'var(--c-text)' }}>{p.partner_name ?? p.partner_iso3}</span>
                          <span className="mono" style={{ fontSize: '9.5px', color: 'var(--c-text-3)', letterSpacing: '0.05em' }}>
                            {p.partner_iso3}
                          </span>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                          <span className="mono" style={{ fontSize: '11px', color: 'var(--c-text-2)' }}>{fmt(p.volume_mt)} MT</span>
                          {p.prs_risk_flag && <span style={{ fontSize: '9px', color: '#991b1b' }}>⚠ PRS</span>}
                          {p.basel_compliant === false && <span style={{ fontSize: '9px', color: '#92400e' }}>Basel ✗</span>}
                        </div>
                      </div>
                    ))}
                    <div style={{ display: 'flex', gap: 10, marginTop: 4 }}>
                      {[
                        { color: '#166534', label: 'Compliant' },
                        { color: '#92400e', label: 'Uncertain' },
                        { color: '#991b1b', label: 'Violation' },
                      ].map(({ color, label }) => (
                        <span key={label} style={{ display: 'flex', alignItems: 'center', gap: 3, fontSize: '9px', color: 'var(--c-text-3)' }}>
                          <span style={{ width: 6, height: 6, borderRadius: '50%', background: color, display: 'inline-block' }} />
                          {label}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Import partners */}
                {data.top_imports.length > 0 && (
                  <div>
                    <p style={{ ...S.label, textTransform: 'none', letterSpacing: 0, marginBottom: 4, fontWeight: 600, color: 'var(--c-text-2)' }}>
                      Top Import Sources
                    </p>
                    {data.top_imports.map((p) => (
                      <div
                        key={p.partner_iso3}
                        style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '3px 0', borderBottom: '1px solid var(--c-border-lt)' }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                          <span
                            style={{
                              width: 8, height: 8, borderRadius: '50%', flexShrink: 0,
                              background: p.compliance_color === 'green' ? '#166534' : p.compliance_color === 'red' ? '#991b1b' : '#92400e',
                            }}
                          />
                          <span style={{ color: 'var(--c-text)' }}>{p.partner_name ?? p.partner_iso3}</span>
                          <span className="mono" style={{ fontSize: '9.5px', color: 'var(--c-text-3)', letterSpacing: '0.05em' }}>{p.partner_iso3}</span>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                          <span className="mono" style={{ fontSize: '11px', color: 'var(--c-text-2)' }}>{fmt(p.volume_mt)} MT</span>
                          {p.prs_risk_flag && <span style={{ fontSize: '9px', color: '#991b1b' }}>⚠ PRS</span>}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Source note */}
            <div style={{ ...S.divider, marginBottom: 0 }} />
            <p style={{ ...S.label, textTransform: 'none', letterSpacing: 0, lineHeight: 1.5, paddingBottom: 8 }}>
              Sources: UN Global E-Waste Monitor, UN Comtrade, OECD Waste Statistics, World Bank Governance Indicators.
              Click <em>Export PDF</em> to generate a full country report.
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
