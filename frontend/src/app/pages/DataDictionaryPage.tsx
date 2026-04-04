/**
 * Data Dictionary page (PRD §4.2)
 *
 * Field-level documentation for all API endpoints and response types.
 * Versioned alongside the platform; increment DATA_DICT_VERSION on each
 * annual data refresh.
 */

const DATA_DICT_VERSION = '1.0'
const LAST_UPDATED = 'March 2026'

export default function DataDictionaryPage() {
  return (
    <div className="min-h-screen bg-gray-950 text-gray-200">
      <header className="flex items-center justify-between px-6 py-3 bg-gray-900 border-b border-gray-800 sticky top-0 z-10">
        <a href="/" className="text-sm font-semibold text-emerald-400 hover:text-emerald-300 transition-colors">
          ← EWasteTradeFlow
        </a>
        <span className="text-xs text-gray-500">Data Dictionary v{DATA_DICT_VERSION}</span>
      </header>

      <div className="max-w-4xl mx-auto px-6 py-10">
        <h1 className="text-2xl font-bold text-white mb-2">Data Dictionary</h1>
        <p className="text-sm text-gray-400 mb-2">
          Field definitions for all API response types. This dictionary is versioned and updated
          with each annual data refresh. Version <strong className="text-emerald-400">{DATA_DICT_VERSION}</strong> ·
          Last updated {LAST_UPDATED}.
        </p>
        <p className="text-xs text-gray-500 mb-8">
          Base URL: <code className="bg-gray-800 px-1 rounded">https://api.ewaste-tradeflow.vercel.app/api/v1</code> ·
          Full interactive docs: <code className="bg-gray-800 px-1 rounded">/api/docs</code>
        </p>

        <DictSection title="Country" endpoint="GET /countries  ·  GET /countries/{iso3}">
          <Fields fields={[
            { name: 'iso3', type: 'string(3)', desc: 'ISO 3166-1 alpha-3 country code. Primary key across all datasets.' },
            { name: 'name', type: 'string', desc: 'Standard English country name from the UN Geoscheme.' },
            { name: 'region', type: 'string | null', desc: 'UN geographic region (e.g., "Africa", "Americas", "Asia").' },
            { name: 'subregion', type: 'string | null', desc: 'UN geographic sub-region (e.g., "Western Africa", "Northern Europe").' },
            { name: 'income_classification', type: '"high" | "upper_middle" | "lower_middle" | "low" | null', desc: 'World Bank income group classification.' },
            { name: 'basel_signatory', type: 'boolean', desc: 'True if the country has signed and ratified the Basel Convention.' },
            { name: 'basel_ban_ratified', type: 'boolean', desc: 'True if the country has ratified the Basel Ban Amendment (prohibits hazardous waste exports to non-OECD countries).' },
            { name: 'is_oecd_member', type: 'boolean', desc: 'True if the country is an OECD member state.' },
          ]} />
        </DictSection>

        <DictSection title="Choropleth Layer" endpoint="GET /map/choropleth?metric={metric}&year={year}">
          <p className="text-sm text-gray-400 mb-3">
            Pre-aggregated per-country values for the map layer. One row per country.
            Missing data countries are included with <code>is_missing: true</code> and{' '}
            <code>value: null</code>.
          </p>
          <Fields fields={[
            { name: 'year', type: 'integer', desc: 'Reporting year for this dataset.' },
            { name: 'metric', type: 'string', desc: 'The metric being displayed. See metric values below.' },
            { name: 'countries[].iso3', type: 'string(3)', desc: 'Country ISO3 code.' },
            { name: 'countries[].name', type: 'string', desc: 'Country display name.' },
            { name: 'countries[].value', type: 'number | null', desc: 'Metric value for this country. Null if no data is available.' },
            { name: 'countries[].confidence_tier', type: '"reported" | "estimated" | "interpolated" | null', desc: 'Data quality tier. "reported" = directly from official source. "interpolated" = gap-filled via linear interpolation.' },
            { name: 'countries[].data_vintage_year', type: 'integer | null', desc: 'Year the source data was published, which may differ from the reporting year.' },
            { name: 'countries[].is_missing', type: 'boolean', desc: 'True if no data is available for this country-year combination. Display with hatch pattern, not as zero.' },
          ]} />
          <MetricTable />
        </DictSection>

        <DictSection title="Sankey / Trade Flows" endpoint="GET /map/flows/sankey">
          <p className="text-sm text-gray-400 mb-3">
            Top N bilateral trade routes for the selected year, formatted for D3-sankey rendering.
            Nodes represent countries; links represent trade corridors.
          </p>
          <Fields fields={[
            { name: 'year', type: 'integer', desc: 'Reporting year.' },
            { name: 'nodes[].id', type: 'string', desc: 'ISO3 code (node identifier used in link source/target).' },
            { name: 'nodes[].name', type: 'string', desc: 'Country display name.' },
            { name: 'nodes[].region', type: 'string', desc: 'UN geographic region.' },
            { name: 'links[].source', type: 'string', desc: 'Exporter ISO3 — matches a node.id.' },
            { name: 'links[].target', type: 'string', desc: 'Importer ISO3 — matches a node.id.' },
            { name: 'links[].volume_mt', type: 'number', desc: 'Trade volume in metric tonnes.' },
            { name: 'links[].value_usd', type: 'number | null', desc: 'Estimated trade value in USD. Null when not reported by either party.' },
            { name: 'links[].compliance_color', type: '"green" | "amber" | "red"', desc: 'Basel compliance indicator. green = compliant, amber = uncertain, red = potential violation.' },
            { name: 'links[].has_violation', type: 'boolean', desc: 'True if this route meets all criteria for a potential Basel Convention violation. See Methodology §5.' },
            { name: 'links[].prs_risk_flag', type: 'boolean', desc: 'True if the importing country has a PRS score ≥ 7 (high processing risk).' },
            { name: 'links[].importer_prs_score', type: 'number | null', desc: 'Processing Risk Score (0–10) of the importing country. See Methodology §6.' },
            { name: 'links[].data_conflict', type: 'boolean', desc: 'True when exporter and importer reports conflict by more than 20% — the exporter figure is used.' },
            { name: 'links[].confidence_tier', type: 'string', desc: 'Overall confidence tier for this flow record.' },
            { name: 'links[].mapping_confidence', type: '"HIGH" | "MEDIUM" | "LOW"', desc: 'Confidence of the HS-to-UN-category mapping. See Methodology §3.' },
          ]} />
        </DictSection>

        <DictSection title="Country Profile" endpoint="GET /country/{iso3}/profile">
          <p className="text-sm text-gray-400 mb-3">
            Full analytical profile for a single country: generation time series, trade partners,
            PRS score, and treaty status.
          </p>
          <Fields fields={[
            { name: 'iso3, name, region, subregion, income_classification, basel_signatory, basel_ban_ratified, is_oecd_member', type: '(see Country)', desc: 'All fields from the Country schema.' },
            { name: 'prs_score', type: 'number | null', desc: 'Processing Risk Score (0–10) for the most recent available year. Null if insufficient data.' },
            { name: 'prs_methodology_version', type: 'integer | null', desc: 'Version of the PRS model used to compute this score.' },
            { name: 'generation_series[].year', type: 'integer', desc: 'Reporting year.' },
            { name: 'generation_series[].total_mt', type: 'number | null', desc: 'Total e-waste generated (all categories) in metric tonnes.' },
            { name: 'generation_series[].per_capita_kg', type: 'number | null', desc: 'Per capita e-waste generation in kilograms.' },
            { name: 'generation_series[].formal_collection_rate', type: 'number | null', desc: 'Share of generated e-waste formally documented as collected and recycled (0–1).' },
            { name: 'generation_series[].confidence_tier', type: 'string | null', desc: 'Data quality tier for this year\'s generation figure.' },
            { name: 'generation_series[].is_interpolated', type: 'boolean', desc: 'True if this data point was gap-filled via linear interpolation.' },
            { name: 'top_exports[].partner_iso3', type: 'string(3)', desc: 'Destination country ISO3.' },
            { name: 'top_exports[].partner_name', type: 'string', desc: 'Destination country name.' },
            { name: 'top_exports[].volume_mt', type: 'number | null', desc: 'Export volume to this destination in metric tonnes.' },
            { name: 'top_exports[].compliance_color', type: '"green" | "amber" | "red"', desc: 'Basel compliance status for this export route.' },
            { name: 'top_exports[].basel_compliant', type: 'boolean | null', desc: 'Explicit compliance determination if available; null when indeterminate.' },
            { name: 'top_imports[].partner_iso3', type: 'string(3)', desc: 'Origin country ISO3.' },
            { name: 'top_imports[].volume_mt', type: 'number | null', desc: 'Import volume from this origin in metric tonnes.' },
            { name: 'top_imports[].prs_risk_flag', type: 'boolean', desc: 'True if this import route is from a high-PRS origin.' },
          ]} />
        </DictSection>

        <DictSection title="E-Waste Generation Series" endpoint="GET /generation/{iso3}">
          <Fields fields={[
            { name: 'iso3', type: 'string(3)', desc: 'Country ISO3 code.' },
            { name: 'series[].year', type: 'integer', desc: 'Reporting year.' },
            { name: 'series[].category_code', type: 'integer | null', desc: 'UN e-waste category (1–6). Null for the all-categories aggregate row.' },
            { name: 'series[].total_mt', type: 'number | null', desc: 'Total e-waste generated in metric tonnes.' },
            { name: 'series[].per_capita_kg', type: 'number | null', desc: 'Per capita generation in kilograms.' },
            { name: 'series[].formal_collection_mt', type: 'number | null', desc: 'Volume formally collected and documented as recycled (MT).' },
            { name: 'series[].formal_collection_rate', type: 'number | null', desc: 'Formal collection rate as a fraction (0–1).' },
            { name: 'series[].source_name', type: 'string | null', desc: 'Name of the data source for this record.' },
            { name: 'series[].confidence_tier', type: 'string | null', desc: '"reported", "estimated", or "interpolated".' },
            { name: 'series[].is_interpolated', type: 'boolean', desc: 'True if gap-filled.' },
          ]} />
        </DictSection>

        <DictSection title="Confidence Tier Reference">
          <table className="dict-table">
            <thead>
              <tr>
                <th>Tier</th>
                <th>Meaning</th>
                <th>Display treatment</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td><Tag color="green">reported</Tag></td>
                <td>Directly reported by official source</td>
                <td>Full opacity, green badge</td>
              </tr>
              <tr>
                <td><Tag color="amber">estimated</Tag></td>
                <td>Modelled or estimated by source methodology</td>
                <td>Slightly reduced opacity, amber badge</td>
              </tr>
              <tr>
                <td><Tag color="amber">interpolated</Tag></td>
                <td>Gap-filled via linear interpolation between reported years</td>
                <td>Lighter bar color, amber badge</td>
              </tr>
              <tr>
                <td><Tag color="green">HIGH</Tag></td>
                <td>High-confidence HS→UN category mapping</td>
                <td>Green badge on trade flow records</td>
              </tr>
              <tr>
                <td><Tag color="amber">MEDIUM</Tag></td>
                <td>Medium-confidence mapping (includes new goods)</td>
                <td>Amber badge</td>
              </tr>
              <tr>
                <td><Tag color="red">LOW</Tag></td>
                <td>Low-confidence mapping (mixed-use equipment)</td>
                <td>Red badge; figures shown with caveat</td>
              </tr>
              <tr>
                <td><Tag color="gray">UNKNOWN</Tag></td>
                <td>Confidence not determined</td>
                <td>Gray badge</td>
              </tr>
            </tbody>
          </table>
        </DictSection>

        <div className="mt-12 pt-6 border-t border-gray-800 text-xs text-gray-500">
          Data Dictionary v{DATA_DICT_VERSION} · Last updated {LAST_UPDATED} · EWasteTradeFlow
        </div>
      </div>

      <style>{`
        .dict-table {
          width: 100%;
          border-collapse: collapse;
          font-size: 0.8rem;
        }
        .dict-table thead tr { background: #1f2937; }
        .dict-table thead th {
          text-align: left; padding: 6px 10px;
          color: #9ca3af; font-weight: 600;
          border-bottom: 1px solid #374151;
        }
        .dict-table tbody tr:nth-child(even) { background: #111827; }
        .dict-table tbody td {
          padding: 6px 10px; color: #d1d5db;
          border-bottom: 1px solid #1f2937; vertical-align: top;
        }
      `}</style>
    </div>
  )
}

// ── Helper sub-components ─────────────────────────────────────────────────────

function DictSection({
  title,
  endpoint,
  children,
}: {
  title: string
  endpoint?: string
  children: React.ReactNode
}) {
  return (
    <section className="mb-10">
      <div className="flex flex-wrap items-baseline gap-3 mb-3 pb-1 border-b border-gray-800">
        <h2 className="text-base font-semibold text-white">{title}</h2>
        {endpoint && (
          <code className="text-xs text-emerald-400 bg-gray-900 px-2 py-0.5 rounded border border-gray-700">
            {endpoint}
          </code>
        )}
      </div>
      {children}
    </section>
  )
}

interface FieldDef {
  name: string
  type: string
  desc: string
}

function Fields({ fields }: { fields: FieldDef[] }) {
  return (
    <table className="dict-table">
      <thead>
        <tr>
          <th style={{ width: '26%' }}>Field</th>
          <th style={{ width: '22%' }}>Type</th>
          <th>Description</th>
        </tr>
      </thead>
      <tbody>
        {fields.map((f) => (
          <tr key={f.name}>
            <td>
              <code className="text-emerald-300 text-xs">{f.name}</code>
            </td>
            <td>
              <code className="text-amber-300 text-xs">{f.type}</code>
            </td>
            <td className="text-gray-300">{f.desc}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

function MetricTable() {
  const metrics: Array<{ key: string; label: string; unit: string; source: string }> = [
    { key: 'generation', label: 'Total Generation', unit: 'Metric tonnes (MT)', source: 'UN Monitor' },
    { key: 'per_capita', label: 'Per Capita Generation', unit: 'Kilograms (kg)', source: 'UN Monitor + UN population' },
    { key: 'formal_collection', label: 'Formal Collection Rate', unit: 'Percent (0–100)', source: 'UN Monitor' },
    { key: 'exports', label: 'Total Exports', unit: 'Metric tonnes (MT)', source: 'Comtrade' },
    { key: 'imports', label: 'Total Imports', unit: 'Metric tonnes (MT)', source: 'Comtrade' },
    { key: 'net_trade', label: 'Net Trade', unit: 'MT (positive = net exporter)', source: 'Comtrade' },
    { key: 'export_intensity', label: 'Export Intensity', unit: 'Exports / generation (dimensionless)', source: 'Derived' },
    { key: 'prs', label: 'Processing Risk Score', unit: 'Score 0–10', source: 'Derived (see Methodology §6)' },
    { key: 'compliance_rate', label: 'Compliance Rate', unit: 'Percent of routes that are compliant', source: 'Derived' },
  ]

  return (
    <>
      <p className="text-sm text-gray-400 mt-3 mb-2">Available metric values for the <code>metric</code> query parameter:</p>
      <table className="dict-table">
        <thead>
          <tr>
            <th>metric value</th>
            <th>Display name</th>
            <th>Unit</th>
            <th>Primary source</th>
          </tr>
        </thead>
        <tbody>
          {metrics.map((m) => (
            <tr key={m.key}>
              <td><code className="text-emerald-300 text-xs">{m.key}</code></td>
              <td>{m.label}</td>
              <td className="text-gray-400">{m.unit}</td>
              <td className="text-gray-400">{m.source}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  )
}

function Tag({ color, children }: { color: string; children: React.ReactNode }) {
  const cls =
    color === 'green'
      ? 'bg-emerald-900/50 text-emerald-300 border-emerald-700'
      : color === 'amber'
        ? 'bg-amber-900/50 text-amber-300 border-amber-700'
        : color === 'red'
          ? 'bg-red-900/50 text-red-300 border-red-700'
          : 'bg-gray-800 text-gray-400 border-gray-700'
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${cls}`}>
      {children}
    </span>
  )
}
