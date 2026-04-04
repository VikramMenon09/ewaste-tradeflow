import { useEffect } from 'react'
import { Routes, Route } from 'react-router-dom'
import { useAuth0 } from '@auth0/auth0-react'
import Layout from './Layout'
import ReportViewPage from './pages/ReportViewPage'
import MethodologyPage from './pages/MethodologyPage'
import DataDictionaryPage from './pages/DataDictionaryPage'
import { configureApiClient } from '@/lib/api-client'
import { useUrlState } from '@/shared/hooks/useUrlState'

// Auth0 may not be configured — guard against missing context
function useOptionalAuth0Token(): (() => Promise<string>) | null {
  try {
    const { getAccessTokenSilently, isAuthenticated } = useAuth0()
    if (!isAuthenticated) return null
    return getAccessTokenSilently
  } catch {
    // Auth0Provider not in tree — auth is disabled
    return null
  }
}

// Main app wrapper — syncs URL state and renders the map/Sankey layout
function MainApp() {
  useUrlState()
  return <Layout />
}

export default function App() {
  const getToken = useOptionalAuth0Token()

  // Wire the API client's token getter whenever auth state changes
  useEffect(() => {
    if (getToken) {
      configureApiClient(getToken)
    }
  }, [getToken])

  return (
    <Routes>
      {/* Internal route rendered by Puppeteer for PDF generation — no app chrome */}
      <Route path="/internal/report-view" element={<ReportViewPage />} />
      {/* Documentation pages */}
      <Route path="/methodology" element={<MethodologyPage />} />
      <Route path="/data-dictionary" element={<DataDictionaryPage />} />
      {/* All other routes go through the main interactive layout */}
      <Route path="*" element={<MainApp />} />
    </Routes>
  )
}
