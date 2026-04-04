import { useFilterStore } from '@/shared/stores/filterStore'
import { useReportStore } from '@/shared/stores/reportStore'
import { api } from '@/lib/api-client'
import Spinner from '@/shared/components/Spinner'

export default function ReportButton() {
  const { year, metric, region, category } = useFilterStore()
  const { reportStatus, startReport, setStatus } = useReportStore()

  const isGenerating = reportStatus === 'queued' || reportStatus === 'processing'

  async function handleGenerate() {
    if (isGenerating) return
    try {
      const res = await api.generateReport('global', { year, metric, region, category })
      startReport(res.job_id)
    } catch (err) {
      setStatus('failed', null, err instanceof Error ? err.message : 'Failed to start report')
    }
  }

  return (
    <button
      onClick={handleGenerate}
      disabled={isGenerating}
      className="flex items-center gap-1.5 px-3 py-1 text-xs rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
      style={{
        border: '1px solid var(--c-border)',
        color: 'var(--c-text-2)',
        background: 'var(--c-surface)',
      }}
    >
      {isGenerating ? (
        <>
          <Spinner size="sm" />
          <span>Generating…</span>
        </>
      ) : (
        <>
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          Export PDF
        </>
      )}
    </button>
  )
}
