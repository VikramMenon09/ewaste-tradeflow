/**
 * Embeddable widget entry point.
 *
 * Built separately via `npm run build:embed` (vite.embed.config.ts).
 * Third-party sites include it as a single <script> tag:
 *
 *   <div id="ewaste-embed" data-year="2022" data-metric="prs" data-view="map"></div>
 *   <script src="https://cdn.example.com/ewaste-embed.js"></script>
 *
 * Supported data attributes on the host element:
 *   data-year    — initial year (default: 2022)
 *   data-metric  — initial choropleth metric (default: "generation")
 *   data-view    — "map" | "sankey" (default: "map")
 *   data-api-url — override the API base URL
 *   data-token   — embed token (forwarded to API for scoped access)
 */

import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useFilterStore } from '@/shared/stores/filterStore'
import ChoroplethMap from '@/features/map/ChoroplethMap'
import SankeyDiagram from '@/features/sankey/SankeyDiagram'
import FilterBar from '@/features/filters/FilterBar'
import type { ChoroplethMetric } from '@/shared/types'

// ── Read config from the host element's data attributes ───────────────────────

const HOST_ID = 'ewaste-embed'
const hostEl = document.getElementById(HOST_ID) ?? document.body

const initYear = parseInt(hostEl.dataset.year ?? '2022', 10)
const initMetric = (hostEl.dataset.metric ?? 'generation') as ChoroplethMetric
const initView = (hostEl.dataset.view ?? 'map') as 'map' | 'sankey'
const apiUrl = hostEl.dataset.apiUrl ?? import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

// Override the API base URL if the embed host specifies one
if (hostEl.dataset.apiUrl) {
  // Re-configure the singleton client with the host-provided URL
  ;(window as Window & { __EWASTE_API_URL__?: string }).__EWASTE_API_URL__ = apiUrl
}

// ── Lightweight embed shell ───────────────────────────────────────────────────

function EmbedApp() {
  const setYear = useFilterStore((s) => s.setYear)
  const setMetric = useFilterStore((s) => s.setMetric)
  const setActiveView = useFilterStore((s) => s.setActiveView)
  const activeView = useFilterStore((s) => s.activeView)

  // Apply data-attribute overrides once on mount
  React.useEffect(() => {
    if (!isNaN(initYear)) setYear(initYear)
    setMetric(initMetric)
    setActiveView(initView)
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div
      style={{ width: '100%', height: '100%', minHeight: 400, display: 'flex', flexDirection: 'column' }}
      className="bg-gray-950 text-white"
    >
      {/* Minimal filter bar — year + view toggle only */}
      <FilterBar />

      {/* Visualization */}
      <div style={{ flex: 1, position: 'relative', minHeight: 0 }}>
        {activeView === 'map' ? <ChoroplethMap /> : <SankeyDiagram />}
      </div>

      {/* Attribution footer */}
      <div
        style={{ fontSize: 10, padding: '4px 8px', textAlign: 'right' }}
        className="text-gray-600 border-t border-gray-800"
      >
        Data: UN Comtrade · OECD · UN Global E-Waste Monitor ·{' '}
        <a
          href="https://github.com/your-org/ewaste-tradeflow"
          target="_blank"
          rel="noreferrer"
          className="text-emerald-700 hover:text-emerald-500"
        >
          EWasteTradeFlow
        </a>
      </div>
    </div>
  )
}

// ── Mount ─────────────────────────────────────────────────────────────────────

const queryClient = new QueryClient({
  defaultOptions: { queries: { staleTime: 5 * 60 * 1000, retry: 1 } },
})

// Create a shadow-DOM-friendly mount target inside the host element
const mountEl = document.createElement('div')
mountEl.style.cssText = 'width:100%;height:100%;'
hostEl.appendChild(mountEl)

ReactDOM.createRoot(mountEl).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <EmbedApp />
    </QueryClientProvider>
  </React.StrictMode>,
)

// Signal to the Puppeteer microservice that the widget has rendered
;(window as Window & { __REPORT_READY__?: boolean }).__REPORT_READY__ = true
