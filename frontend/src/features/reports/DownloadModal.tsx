import { useEffect } from 'react'
import { useReportStore } from '@/shared/stores/reportStore'
import { useReportPolling } from '@/shared/hooks/useReportPolling'
import Spinner from '@/shared/components/Spinner'

export default function DownloadModal() {
  const { activeJobId, reportStatus, downloadUrl, error, setStatus, clearReport } =
    useReportStore()

  // Poll the job while it's active
  const poll = useReportPolling(activeJobId)

  // Sync polling results back into the store
  useEffect(() => {
    if (poll.status && poll.status !== reportStatus) {
      setStatus(poll.status, poll.downloadUrl, poll.error)
    }
  }, [poll.status, poll.downloadUrl, poll.error, reportStatus, setStatus])

  // Nothing to show if no active job
  if (!activeJobId) return null

  const isFinished = reportStatus === 'complete' || reportStatus === 'failed'

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black bg-opacity-60"
        onClick={isFinished ? clearReport : undefined}
      />

      {/* Modal */}
      <div className="relative bg-gray-900 border border-gray-700 rounded-lg shadow-2xl w-full max-w-sm p-5 text-sm">
        <h2 className="font-semibold text-white mb-4">
          {reportStatus === 'complete'
            ? 'Report Ready'
            : reportStatus === 'failed'
            ? 'Report Failed'
            : 'Generating Report…'}
        </h2>

        {/* Status body */}
        {(reportStatus === 'queued' || reportStatus === 'processing') && (
          <div className="flex items-center gap-3 text-gray-400">
            <Spinner />
            <span>
              {reportStatus === 'queued'
                ? 'Queued — waiting for a worker…'
                : 'Rendering PDF via Puppeteer…'}
            </span>
          </div>
        )}

        {reportStatus === 'complete' && downloadUrl && (
          <div className="space-y-3">
            <p className="text-gray-400 text-xs">
              Your PDF is ready. The link expires in 24 hours.
            </p>
            <a
              href={downloadUrl}
              download
              target="_blank"
              rel="noreferrer"
              className="flex items-center justify-center gap-2 w-full px-4 py-2 bg-emerald-700 hover:bg-emerald-600 text-white rounded transition-colors"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
              Download PDF
            </a>
          </div>
        )}

        {reportStatus === 'failed' && (
          <div className="space-y-3">
            <p className="text-red-400 text-xs">
              {error ?? 'An unknown error occurred during report generation.'}
            </p>
            <p className="text-gray-500 text-xs">
              Check that the Puppeteer microservice is running and S3 credentials
              are configured.
            </p>
          </div>
        )}

        {/* Actions */}
        <div className="flex justify-end gap-2 mt-5">
          {isFinished && (
            <button
              onClick={clearReport}
              className="px-4 py-1.5 text-xs rounded border border-gray-700 text-gray-400 hover:text-white hover:border-gray-500 transition-colors"
            >
              Dismiss
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
