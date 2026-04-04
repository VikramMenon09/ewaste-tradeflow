/**
 * Methodology page (PRD §4.2)
 *
 * Explains all calculations, category mappings, PRS scoring, Basel compliance
 * flagging, and known data limitations — required before launch.
 */

export default function MethodologyPage() {
  return (
    <div className="min-h-screen bg-gray-950 text-gray-200">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-3 bg-gray-900 border-b border-gray-800 sticky top-0 z-10">
        <a href="/" className="text-sm font-semibold text-emerald-400 hover:text-emerald-300 transition-colors">
          ← EWasteTradeFlow
        </a>
        <span className="text-xs text-gray-500">Methodology & Data Quality</span>
      </header>

      <div className="max-w-3xl mx-auto px-6 py-10">
        <h1 className="text-2xl font-bold text-white mb-2">Methodology</h1>
        <p className="text-sm text-gray-400 mb-8">
          This page describes how EWasteTradeFlow collects, normalizes, and interprets data from its
          three primary sources. All calculations are versioned; this document reflects{' '}
          <span className="text-emerald-400 font-medium">Methodology v1.0</span>.
        </p>

        {/* Data sources */}
        <Section title="1. Data Sources">
          <p>
            EWasteTradeFlow ingests data from three primary sources and one reference dataset. All
            raw files are stored immutably in object storage before any transformation is applied.
          </p>
          <table className="method-table mt-4">
            <thead>
              <tr>
                <th>Source</th>
                <th>Coverage</th>
                <th>What it provides</th>
                <th>Update frequency</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td className="font-medium text-white">UN Global E-Waste Monitor (2024)</td>
                <td>193 countries, 2010–2022</td>
                <td>E-waste generation by country and UN category; formal collection rates</td>
                <td>Every 2–3 years</td>
              </tr>
              <tr>
                <td className="font-medium text-white">UN Comtrade (via World Bank API)</td>
                <td>Global bilateral trade, 2000–present</td>
                <td>HS-code trade flows; volume (MT) and value (USD)</td>
                <td>Annual</td>
              </tr>
              <tr>
                <td className="font-medium text-white">OECD Waste Statistics (OECD.Stat)</td>
                <td>38 OECD members + select partners</td>
                <td>Transboundary waste movement; treatment statistics</td>
                <td>Annual</td>
              </tr>
              <tr>
                <td className="font-medium text-white">Basel Convention party list (UNEP)</td>
                <td>All UN member states</td>
                <td>Convention signatory status; Ban Amendment ratification date</td>
                <td>Infrequent (reviewed annually)</td>
              </tr>
              <tr>
                <td className="font-medium text-white">World Bank Governance Indicators</td>
                <td>~215 countries, annual</td>
                <td>Rule of Law score; environmental enforcement proxy (PRS input)</td>
                <td>Annual</td>
              </tr>
            </tbody>
          </table>
        </Section>

        {/* Country identifiers */}
        <Section title="2. Country Identifier Normalization">
          <p>
            All data sources use different country naming conventions. EWasteTradeFlow normalizes
            every country identifier to{' '}
            <strong className="text-white">ISO 3166-1 alpha-3 (iso3)</strong> codes before any
            join or aggregation. A custom mapping table handles non-standard codes (e.g., Taiwan,
            Kosovo, historical country codes) and routes disputed territories to their closest
            UN-recognized equivalent for display purposes.
          </p>
          <p className="mt-2">
            Countries that cannot be mapped are excluded from analysis and counted in the data gap
            log. The mapping table is reviewed with each annual data refresh.
          </p>
        </Section>

        {/* E-waste categories */}
        <Section title="3. E-Waste Category Mapping">
          <p>
            The UN Monitor uses six standardized e-waste categories. UN Comtrade uses HS commodity
            codes. EWasteTradeFlow applies a mapping layer to assign each HS code to a UN category
            with a <strong className="text-white">mapping confidence tier</strong>:
          </p>
          <table className="method-table mt-4">
            <thead>
              <tr>
                <th>UN Category</th>
                <th>Description</th>
                <th>Primary HS codes</th>
              </tr>
            </thead>
            <tbody>
              <tr><td>1</td><td>Temperature exchange equipment</td><td>8418, 8415</td></tr>
              <tr><td>2</td><td>Screens and monitors</td><td>8471, 8528</td></tr>
              <tr><td>3</td><td>Lamps</td><td>8539, 8540</td></tr>
              <tr><td>4</td><td>Large equipment</td><td>8450–8479 (subset)</td></tr>
              <tr><td>5</td><td>Small equipment</td><td>8508–8519, 8531</td></tr>
              <tr><td>6</td><td>Small IT and telecom</td><td>8471, 8517, 8525, 8548, 8549</td></tr>
            </tbody>
          </table>
          <p className="mt-3 text-sm text-gray-400">
            HS codes covering both new goods and end-of-life equipment (e.g., 8471 — computers)
            are assigned mapping confidence <span className="text-amber-400">MEDIUM</span>. Codes
            specific to waste or parts (e.g., 8549 — electrical waste) are assigned{' '}
            <span className="text-emerald-400">HIGH</span>. Ambiguous codes (e.g., mixed-use
            equipment categories) are assigned <span className="text-red-400">LOW</span>. All
            figures derived from LOW confidence mappings are visually flagged in the platform.
          </p>
        </Section>

        {/* Generation estimates */}
        <Section title="4. Generation Data & Gap Filling">
          <p>
            Official generation figures come from the UN Global E-Waste Monitor. Where the Monitor
            does not provide country-level data for a given year, EWasteTradeFlow applies{' '}
            <strong className="text-white">linear interpolation</strong> between adjacent reported
            years. Interpolated values are marked with confidence tier{' '}
            <span className="text-amber-400">interpolated</span> and shown with a lighter color
            on charts and maps.
          </p>
          <p className="mt-2">
            Countries with no reported data in any year appear as{' '}
            <span className="text-gray-400 bg-gray-800 px-1 rounded">No Data</span> on the map
            using a distinct hatch pattern, not a zero value. They are excluded from all
            aggregations.
          </p>
        </Section>

        {/* Basel compliance */}
        <Section title="5. Basel Convention Compliance Flagging">
          <p>
            A trade flow is flagged as a{' '}
            <span className="text-red-400 font-medium">Potential Basel Violation</span> when{' '}
            <em>all</em> of the following are true:
          </p>
          <ul className="list-disc pl-5 mt-2 space-y-1 text-sm text-gray-300">
            <li>The exporting country has ratified the Basel Convention</li>
            <li>
              The importing country has <strong className="text-white">not</strong> ratified the
              Basel Ban Amendment (which prohibits OECD→non-OECD hazardous waste exports)
            </li>
            <li>
              The commodity code maps to e-waste categories classified as hazardous under Annex
              VIII of the Convention (categories 1, 2, 5, 6)
            </li>
          </ul>
          <p className="mt-3 text-sm text-amber-400 bg-amber-900/20 border border-amber-800 rounded px-3 py-2">
            Compliance flags are <strong>modeled estimates</strong> based on treaty membership and
            commodity categories — not legal determinations. A flagged route does not necessarily
            constitute a confirmed violation. The platform is designed to highlight routes
            warranting further investigation, not to make legal findings.
          </p>
        </Section>

        {/* PRS scoring */}
        <Section title="6. Processing Risk Score (PRS)">
          <p>
            The PRS (0–10 scale) estimates the likelihood that e-waste imported by a country is
            processed under unsafe conditions or informally. Higher scores indicate higher risk.
            The score is <strong className="text-white">methodology version 1</strong> and will
            be re-evaluated with each annual data refresh.
          </p>
          <table className="method-table mt-4">
            <thead>
              <tr>
                <th>Component</th>
                <th>Weight</th>
                <th>Source</th>
                <th>Description</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>Formal capacity ratio</td>
                <td>35%</td>
                <td>OECD Waste Statistics</td>
                <td>Formal recycling capacity (MT) relative to import volume</td>
              </tr>
              <tr>
                <td>Rule of Law score</td>
                <td>30%</td>
                <td>World Bank Governance Indicators</td>
                <td>Proxy for environmental enforcement effectiveness (−2.5 to +2.5 scale, normalized)</td>
              </tr>
              <tr>
                <td>Income classification</td>
                <td>20%</td>
                <td>World Bank</td>
                <td>High income = 0, low income = 1 (normalized to 0–10)</td>
              </tr>
              <tr>
                <td>Literature flag</td>
                <td>15%</td>
                <td>Academic literature</td>
                <td>Documented presence of informal processing sites in peer-reviewed sources</td>
              </tr>
            </tbody>
          </table>
          <p className="mt-3 text-sm text-gray-400">
            Countries with insufficient data to compute any component are assigned a partial score
            with a note on data completeness. PRS scores below 4 are considered low risk, 4–7
            moderate, above 7 high. Countries receive a score of null if fewer than two components
            have source data.
          </p>
        </Section>

        {/* Data validation */}
        <Section title="7. Data Validation">
          <p>
            Each pipeline run executes automated checks before data is promoted to the mart tables:
          </p>
          <ul className="list-disc pl-5 mt-2 space-y-1 text-sm text-gray-300">
            <li>
              <strong className="text-white">Global balance check</strong>: total reported imports
              cannot exceed total reported exports by more than 15% in any given year (accounts for
              reporting lag and informal flows)
            </li>
            <li>
              <strong className="text-white">Country coverage</strong>: at least 100 countries must
              have generation data for a year to be included in time-series views
            </li>
            <li>
              <strong className="text-white">Freshness check</strong>: mart tables are flagged
              stale after 10 days without refresh; an error is raised after 30 days
            </li>
            <li>
              <strong className="text-white">Source completeness</strong>: each source table must
              contain records for at least 80% of the expected country-year combinations before its
              data is published
            </li>
          </ul>
        </Section>

        {/* Known limitations */}
        <Section title="8. Known Limitations">
          <ul className="list-disc pl-5 space-y-2 text-sm text-gray-300">
            <li>
              <strong className="text-white">Informal flows are not captured.</strong> The
              platform measures officially reported trade data only. Estimates from academic
              literature suggest informal flows may represent 50–80% of total e-waste movement in
              some corridors; this platform cannot quantify those flows and explicitly excludes
              them from aggregations.
            </li>
            <li>
              <strong className="text-white">Comtrade double-counting risk.</strong> When both
              exporter and importer report the same trade flow, we use the exporter-reported figure
              as the primary source. Conflicts are flagged with the{' '}
              <span className="text-amber-400">data_conflict</span> field.
            </li>
            <li>
              <strong className="text-white">UN Monitor coverage gaps.</strong> Several low-income
              countries have no reported data in the UN Monitor. Generation figures for these
              countries are either interpolated (if adjacent years exist) or absent.
            </li>
            <li>
              <strong className="text-white">PRS literature component is static.</strong> The
              literature flag is reviewed manually every 1–2 years and may not reflect the most
              recent academic evidence for rapidly changing countries.
            </li>
          </ul>
        </Section>

        <div className="mt-12 pt-6 border-t border-gray-800 text-xs text-gray-500">
          Methodology v1.0 · Last updated March 2026 · EWasteTradeFlow
        </div>
      </div>

      <style>{`
        .method-table {
          width: 100%;
          border-collapse: collapse;
          font-size: 0.8rem;
        }
        .method-table thead tr {
          background: #1f2937;
        }
        .method-table thead th {
          text-align: left;
          padding: 6px 10px;
          color: #9ca3af;
          font-weight: 600;
          border-bottom: 1px solid #374151;
        }
        .method-table tbody tr:nth-child(even) {
          background: #111827;
        }
        .method-table tbody td {
          padding: 6px 10px;
          color: #d1d5db;
          border-bottom: 1px solid #1f2937;
          vertical-align: top;
        }
      `}</style>
    </div>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mb-8">
      <h2 className="text-base font-semibold text-white mb-3 pb-1 border-b border-gray-800">{title}</h2>
      <div className="text-sm text-gray-300 space-y-2 leading-relaxed">{children}</div>
    </section>
  )
}
