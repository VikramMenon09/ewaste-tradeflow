import { useFilterStore } from '@/shared/stores/filterStore'
import { useUIStore } from '@/shared/stores/uiStore'
import FilterBar from '@/features/filters/FilterBar'
import GlobalStatsStrip from '@/features/stats/GlobalStatsStrip'
import ChoroplethMap from '@/features/map/ChoroplethMap'
import SankeyDiagram from '@/features/sankey/SankeyDiagram'
import DataTable from '@/features/data-table/DataTable'
import CountryPanel from '@/features/country-panel/CountryPanel'
import AuthButton from '@/features/auth/AuthButton'
import ReportButton from '@/features/reports/ReportButton'
import DownloadModal from '@/features/reports/DownloadModal'
import EmbedButton from '@/features/embed/EmbedButton'

export default function Layout() {
  const activeView = useFilterStore((s) => s.activeView)
  const panelOpen = useUIStore((s) => s.panelOpen)

  return (
    <div className="flex flex-col h-screen overflow-hidden" style={{ background: 'var(--c-bg)', color: 'var(--c-text)' }}>
      {/* ── Top navigation bar ─────────────────────────────────────────── */}
      <header
        className="flex items-center justify-between px-4 py-2 shrink-0 z-20"
        style={{ background: 'var(--c-surface)', borderBottom: '1px solid var(--c-border)' }}
      >
        <div className="flex items-center gap-3">
          <span className="text-sm font-bold tracking-tight" style={{ color: 'var(--c-accent)', fontFamily: 'ui-monospace, monospace' }}>
            EWasteTradeFlow
          </span>
          <span className="text-xs hidden sm:block" style={{ color: 'var(--c-text-3)' }}>
            Global E-Waste Trade Analytics
          </span>
        </div>
        <div className="flex items-center gap-2">
          <EmbedButton />
          <ReportButton />
          <AuthButton />
        </div>
      </header>

      {/* ── Filter bar ─────────────────────────────────────────────────── */}
      <div className="shrink-0 z-10">
        <FilterBar />
      </div>

      {/* ── Global stats strip ─────────────────────────────────────────── */}
      <div className="shrink-0">
        <GlobalStatsStrip />
      </div>

      {/* ── Main content area ──────────────────────────────────────────── */}
      <main className="flex flex-1 min-h-0 relative">
        {/* Primary visualization */}
        <div className="flex-1 relative overflow-hidden">
          {activeView === 'map' && <ChoroplethMap />}
          {activeView === 'sankey' && <SankeyDiagram />}
          {activeView === 'table' && <DataTable />}
        </div>

        {/* Country detail panel (slide-in) */}
        {panelOpen && (
          <aside
            className="w-80 shrink-0 overflow-y-auto"
            style={{ background: 'var(--c-surface)', borderLeft: '1px solid var(--c-border)' }}
          >
            <CountryPanel />
          </aside>
        )}
      </main>

      {/* ── Modals ─────────────────────────────────────────────────────── */}
      <DownloadModal />

      {/* ── Footer links ───────────────────────────────────────────────── */}
      <footer
        className="shrink-0 flex items-center gap-4 px-4 py-1 text-xs"
        style={{ background: 'var(--c-surface)', borderTop: '1px solid var(--c-border)', color: 'var(--c-text-3)' }}
      >
        <a href="/methodology" className="hover:underline" style={{ color: 'var(--c-text-2)' }}>Methodology</a>
        <a href="/data-dictionary" className="hover:underline" style={{ color: 'var(--c-text-2)' }}>Data Dictionary</a>
        <span className="ml-auto" style={{ fontFamily: 'ui-monospace, monospace', fontSize: '10px' }}>
          UN Comtrade · OECD · GEM 2024
        </span>
      </footer>
    </div>
  )
}
