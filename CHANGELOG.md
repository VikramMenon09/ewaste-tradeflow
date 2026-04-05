# Changelog

All notable changes to this project will be documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased] — Phase 4 (In Progress)

### Added
- **Dark mode** — full dark palette via `[data-theme="dark"]` CSS custom properties; `useDarkMode` hook persists preference to `localStorage` and respects OS `prefers-color-scheme`; ☾/☀ toggle button in the header
- **Error boundaries** — `ErrorBoundary` class component wraps the map, Sankey diagram, data table, country panel, and top-level app; failed sub-trees show a contained fallback with a "Try again" reset instead of crashing the whole page
- **Country search endpoint** — `GET /api/v1/countries/search?q=&limit=` searches country name, ISO3 code, region, and subregion; returns results ordered by relevance (exact ISO3 match → name prefix → substring)
- **axe-core accessibility tests** — `axe-core`, `@testing-library/react`, and `jsdom` added to frontend devDependencies; `ErrorBoundary.a11y.test.tsx` asserts no WCAG violations on the error fallback UI; CI runs a11y tests as a dedicated step after the unit test suite
- **Annual data refresh guide** — `docs/data/annual-refresh-guide.md`: 6-step walkthrough covering ingestion, dbt run, cache invalidation, version bumping, verification, and troubleshooting
- **Data dictionary version history** — `CHANGELOG` array in `DataDictionaryPage.tsx` renders a "Version History" table at the bottom of the page; pointer to `annual-refresh-guide.md` for future maintainers

### In Progress
- WCAG 2.1 AA accessibility audit — color-coded map layers still need non-color differentiators (patterns/ARIA)
- Performance audit — map initial load target <3s, filter update target <2s (not yet measured)
- Cross-browser QA (Chrome, Firefox, Safari, Edge) — particularly MapLibre GL rendering on Safari

---

## [0.3.0] — 2026-04-04

### Added — Research UI & Light Mode
- **Light mode** throughout — CSS custom properties (`--c-bg`, `--c-surface`, `--c-raised`, `--c-border`, `--c-text`, `--c-accent`) replacing dark theme across all components
- **CartoDB Positron basemap** — neutral light-gray basemap standard in academic GIS research (MapLibre GL, no API key required)
- **GlobalStatsStrip** — persistent bar above main content showing global total, country coverage, % directly reported, and highest-value country for the current metric and year; computed client-side from the same React Query cache as the choropleth
- **Data Table view** — sortable, searchable table of all countries ranked by selected metric; confidence codes `[R]` reported / `[E]` estimated / `[I]` interpolated with color coding; click row opens country detail panel
- **MapLegend** — 7-step color bar with formatted min/mid/max values and no-data swatch, metric-aware labels and units
- **MapTooltip** — hover tooltip showing metric value with units, confidence badge, vintage year, and "click for profile" hint
- **LayerToggle** — toggles choropleth fill visibility without reloading tiles
- View toggle in filter bar extended to include **Data Table** as a third view alongside Map and Sankey

### Added — Map Layer Ordering Fix
- Added `beforeId="waterway"` to both `country-fill` and `country-border` Layer components — inserts GeoJSON layers above Positron land/landcover but below waterways, roads, and labels

### Added — Mock Dev Server Improvements
- Replaced static `MOCK_CHOROPLETH` with `buildChoropleth(metric, year)` function in `vite.config.ts`
- Function returns metric-appropriate mock values: `per_capita` (gen/pop×1000), `prs` (1.2–9.5 based on OECD membership), `compliance_rate` (0.15–0.97), etc.
- Prevents legend from showing nonsensical values like "6500000%" when metric is compliance_rate

### Added — Reports & Embeds
- `/internal/report-view` React route — Puppeteer-rendered page reads `?type=&filters=` from URL and signals readiness via `window.__REPORT_READY__ = true`
- Four PDF report templates: `CountryProfileReport`, `TradeRouteBriefReport`, `RegionalSummaryReport`, `GlobalStateReport`
- Print-optimized CSS (`report-print.css`) — A4 page breaks, margins, and typography at 96 DPI
- `DownloadModal` — async PDF job polling UI with progress states
- Embed token API router (`POST/GET/DELETE /api/v1/embed/tokens`) with signed token generation
- `EmbedButton` + modal — generates `<script>` + `<div>` iframe snippet using signed embed token
- `MethodologyPage` (`/methodology`) — PRS formula walkthrough, confidence tier definitions, Basel flagging logic, known limitations
- `DataDictionaryPage` (`/data-dictionary`) — field-level documentation for all API response types

### Added — Data Pipeline (Phase 3 completion)
- Basel Convention ingestion source (`ingestion/sources/basel/`) — fetch, parse, schema
- UN Monitor ingestion source (`ingestion/sources/un_monitor/`) — fetch, parse, schema
- World Bank Governance ingestion source (`ingestion/sources/wb_governance/`) — schema, __init__
- dbt staging models: `stg_basel_status`, `stg_oecd_flows`, `stg_wb_governance`
- dbt intermediate models: `int_generation_filled` (gap-fill via interpolation), `int_prs_components`
- dbt mart models: `mart_countries`, `mart_ewaste_generation`, `mart_trade_flows`, `mart_processing_risk_scores`
- dbt `schema.yml` with data quality tests and `sources.yml` with freshness checks

### Added — Tests
- `api/tests/test_routers.py` — integration tests for countries, generation, trade-flows, map, and export endpoints (pytest-asyncio + httpx)
- `api/tests/conftest.py` — async test client fixtures
- `frontend/src/lib/__tests__/url-codec.test.ts` — URL encode/decode round-trip tests

---

## [0.2.0] — 2026-03-31

### Added — Core Frontend
- React + TypeScript + Vite project with path aliases (`@/`)
- **MapLibre GL choropleth map** (`react-map-gl/maplibre`)
  - GeoJSON country boundaries from `datasets/geo-countries` (4.6 MB, cached)
  - Blue color scale (generation, collection rate, per capita) and red scale (PRS, net trade)
  - `buildFillExpression` — normalizes values to 7-step color scale per metric
- **D3.js Sankey diagram** (`d3-sankey`) with Basel compliance link coloring and volume labels on large links
- **Filter bar** — metric selector (7 options), year slider (2018–2023), category toggles (UN e-waste categories 1–6), region filter, compliant-only / flagged-only checkboxes
- **Country detail panel** — generation trend chart (D3 area + line), PRS score bar with explanation, key indicators grid (generation, per capita, collection rate, YoY growth), trade partner list with Basel compliance colors and Basel ✗ / ⚠ PRS badges
- `GenerationChart` — D3 area chart with grid lines, vintage-distinguished dots (white stroke for interpolated)
- **URL state sharing** — full filter state encoded in query string (`encodeFilters` / `decodeFilters`); shareable links for citation
- **Auth0 integration** — `AuthButton`, `SavedStatesMenu` for bookmarked filter configurations
- CSV export via `/api/v1/export`
- Shared components: `Badge`, `DataQualityBadge`, `Spinner`, `EmptyState`, `Tooltip`
- Zustand stores: `filterStore`, `uiStore`, `mapStore`, `reportStore`
- React Query data hooks: `useMapData`, `useSankeyData`, `useCountryProfile`

---

## [0.1.0] — 2026-03-28

### Added — FastAPI Backend
- 8 API routers: `countries`, `generation`, `trade_flows`, `profiles`, `map`, `reports`, `export`, `saved_states`
- PRS scoring model: `0.30 × capacity + 0.35 × enforcement + 0.20 × income + 0.15 × literature`
- Basel Convention compliance flagging on all trade flow records
- Redis response caching (TTL: 24h for static data, 5m for user-specific endpoints)
- Rate limiting via `slowapi`
- Alembic migration `001_initial_schema` — all tables, indexes, PostGIS geometry columns
- `EmbedToken` DB model for signed iframe tokens

---

## [0.0.1] — 2026-03-25

### Added — Foundation
- Monorepo scaffold with full directory structure
- Comtrade Plus API v2 ingestion client with pagination and rate limit backoff
- HS-to-UN-e-waste-category seed mapping (52 HS codes, confidence tiers, waste fraction scalars)
- Literature flags seed (15 countries, peer-reviewed citations)
- Income classification PRS weight seed
- dbt project: staging → intermediate → mart transformation layers
- `int_trade_flows_unified` — central reconciliation model with Basel compliance flagging
- `mart_choropleth_cache` and `mart_sankey_cache` — pre-aggregated for API performance
- `run_ingestion.py` CLI with dry-run support, rich terminal output, and audit logging
- S3 upload utility with immutable timestamped Parquet keys
- Pipeline run audit log (`catalog.py`)
- Docker Compose for local development (PostgreSQL/PostGIS + Redis)
- `.env.example` documenting all required environment variables
