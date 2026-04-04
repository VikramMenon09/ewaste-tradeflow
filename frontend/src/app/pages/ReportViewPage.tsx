/**
 * /internal/report-view
 *
 * This route is navigated to by the Puppeteer microservice during PDF generation.
 * It reads ?type= and ?filters= (base64url-encoded JSON) from the URL, selects the
 * correct report template, and sets window.__REPORT_READY__ = true once data has
 * loaded — which Puppeteer polls for before capturing the PDF.
 *
 * This page is NOT linked to from the main UI and intentionally renders without
 * the app header, filter bar, or any other chrome.
 */

import { useSearchParams } from 'react-router-dom'
import CountryProfileReport from '@/features/reports/templates/CountryProfileReport'
import TradeRouteBriefReport from '@/features/reports/templates/TradeRouteBriefReport'
import RegionalSummaryReport from '@/features/reports/templates/RegionalSummaryReport'
import GlobalStateReport from '@/features/reports/templates/GlobalStateReport'
import '@/features/reports/templates/report-print.css'

type ReportType = 'country_profile' | 'trade_route' | 'regional' | 'global'

/**
 * Decode base64url-encoded JSON params produced by report_generator.py:
 *   base64.urlsafe_b64encode(json.dumps(params).encode()).decode()
 */
function decodeFilters(encoded: string): Record<string, unknown> {
  if (!encoded) return {}
  try {
    // base64url → standard base64 → JSON
    const b64 = encoded.replace(/-/g, '+').replace(/_/g, '/')
    return JSON.parse(atob(b64)) as Record<string, unknown>
  } catch {
    return {}
  }
}

export default function ReportViewPage() {
  const [searchParams] = useSearchParams()
  const type = (searchParams.get('type') ?? 'global') as ReportType
  const params = decodeFilters(searchParams.get('filters') ?? '')

  // White background at the page level so loading state isn't a black screen.
  // Each template sets window.__REPORT_READY__ = true once data has loaded —
  // Puppeteer waits for that signal before capturing the PDF.
  return (
    <div style={{ background: '#ffffff', minHeight: '100vh' }}>
      {type === 'country_profile' && <CountryProfileReport params={params} />}
      {type === 'trade_route' && <TradeRouteBriefReport params={params} />}
      {type === 'regional' && <RegionalSummaryReport params={params} />}
      {(type === 'global' || (type !== 'country_profile' && type !== 'trade_route' && type !== 'regional')) && (
        <GlobalStateReport params={params} />
      )}
    </div>
  )
}
