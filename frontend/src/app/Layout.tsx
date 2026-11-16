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
import ErrorBoundary from '@/shared/components/ErrorBoundary'
import { useDarkMode } from '@/shared/hooks/useDarkMode'
import { IS_STATIC } from '@/lib/static-data'
import SnapshotBanner from '@/features/static/SnapshotBanner'
import FullStackNotice from '@/features/static/FullStackNotice'

export default function Layout() {
  const activeView = useFilterStore((s) => s.activeView)
  const panelOpen = useUIStore((s) => s.panelOpen)
  const { isDark, toggle: toggleTheme } = useDarkMode()

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
          {!IS_STATIC && <EmbedButton />}
          {!IS_STATIC && <ReportButton />}
          <AuthButton />
          <button
            onClick={toggleTheme}
            title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
            aria-label={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
            className="rounded px-2 py-1.5 text-xs transition-colors hover:border-gray-500"
            style={{
              background: 'transparent',
              border: '1px solid var(--c-border)',
              color: 'var(--c-text-2)',
            }}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              {isDark ? (
                <>
                  <circle cx="12" cy="12" r="4" />
                  <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41" />
                </>
              ) : (
                <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
              )}
            </svg>
          </button>
        </div>
      </header>

      {IS_STATIC && (
        <div className="shrink-0">
          <SnapshotBanner />
        </div>
      )}

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
          <ErrorBoundary label="map">
            {activeView === 'map' && <ChoroplethMap />}
          </ErrorBoundary>
          <ErrorBoundary label="diagram">
            {activeView === 'sankey' && (IS_STATIC ? <FullStackNotice feature="The trade flow (Sankey) diagram" /> : <SankeyDiagram />)}
          </ErrorBoundary>
          <ErrorBoundary label="table">
            {activeView === 'table' && <DataTable />}
          </ErrorBoundary>
        </div>

        {/* Country detail panel (slide-in) */}
        {panelOpen && (
          <aside
            className="w-80 shrink-0 overflow-y-auto"
            style={{ background: 'var(--c-surface)', borderLeft: '1px solid var(--c-border)' }}
          >
            <ErrorBoundary label="country panel">
              <CountryPanel />
            </ErrorBoundary>
          </aside>
        )}
      </main>

      {/* ── Modals ─────────────────────────────────────────────────────── */}
      <DownloadModal />

      {/* ── Footer links ───────────────────────────────────────────────── */}
      <footer
        className="shrink-0 flex flex-wrap items-center gap-x-4 gap-y-1 px-4 py-1.5 text-xs"
        style={{ background: 'var(--c-surface)', borderTop: '1px solid var(--c-border)', color: 'var(--c-text-3)' }}
      >
        <a href="/methodology" className="hover:underline" style={{ color: 'var(--c-text-2)' }}>Methodology</a>
        <a href="/data-dictionary" className="hover:underline" style={{ color: 'var(--c-text-2)' }}>Data Dictionary</a>
        <a href="https://github.com/VikramMenon09/ewaste-tradeflow" target="_blank" rel="noreferrer" className="hover:underline" style={{ color: 'var(--c-text-2)' }}>Source</a>
        <span className="ml-auto hidden md:block" style={{ fontFamily: 'ui-monospace, monospace', fontSize: '11px' }}>
          {IS_STATIC ? 'Static snapshot · OECD · UN SDG 12.4.2 · World Bank WGI · UN Treaty Collection' : 'UN Comtrade · OECD · GEM 2024'}
        </span>
        <span className="ml-auto md:ml-0" style={{ fontSize: '11px' }}>© {new Date().getFullYear()} EWasteTradeFlow</span>
      </footer>
    </div>
  )
}
