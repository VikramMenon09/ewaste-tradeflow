import { useState, useEffect, useRef, useCallback } from 'react'
import { api } from '@/lib/api-client'
import type { ReportStatusResponse } from '@/shared/types'

const INITIAL_INTERVAL_MS = 2_000
const BACKOFF_AFTER_MS = 30_000
const BACKOFF_INTERVAL_MS = 5_000
const MAX_POLL_MS = 5 * 60 * 1_000 // 5 minutes

interface PollResult {
  status: ReportStatusResponse['status'] | null
  downloadUrl: string | null
  error: string | null
}

/**
 * useReportPolling — polls /reports/{jobId} every 2s with exponential backoff.
 *
 * Polling strategy:
 *   - Every 2s for the first 30s
 *   - Every 5s thereafter (backoff)
 *   - Stops after 5 minutes total, or when status is complete/failed
 */
export function useReportPolling(jobId: string | null): PollResult {
  const [result, setResult] = useState<PollResult>({
    status: null,
    downloadUrl: null,
    error: null,
  })

  const startTimeRef = useRef<number | null>(null)
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const activeJobRef = useRef<string | null>(null)

  const clearTimer = useCallback(() => {
    if (timeoutRef.current !== null) {
      clearTimeout(timeoutRef.current)
      timeoutRef.current = null
    }
  }, [])

  const poll = useCallback(async (id: string) => {
    if (activeJobRef.current !== id) return

    try {
      const data = await api.getReportStatus(id)

      if (activeJobRef.current !== id) return

      setResult({
        status: data.status,
        downloadUrl: data.download_url,
        error: data.error_message,
      })

      if (data.status === 'complete' || data.status === 'failed') {
        return // Stop polling
      }

      const elapsed = Date.now() - (startTimeRef.current ?? Date.now())
      if (elapsed >= MAX_POLL_MS) {
        setResult((prev) => ({
          ...prev,
          status: 'failed',
          error: 'Report generation timed out after 5 minutes.',
        }))
        return
      }

      const interval = elapsed < BACKOFF_AFTER_MS ? INITIAL_INTERVAL_MS : BACKOFF_INTERVAL_MS
      timeoutRef.current = setTimeout(() => poll(id), interval)
    } catch (err) {
      if (activeJobRef.current !== id) return
      setResult({
        status: 'failed',
        downloadUrl: null,
        error: err instanceof Error ? err.message : 'Unknown error polling report status.',
      })
    }
  }, [])

  useEffect(() => {
    clearTimer()

    if (!jobId) {
      activeJobRef.current = null
      setResult({ status: null, downloadUrl: null, error: null })
      return
    }

    activeJobRef.current = jobId
    startTimeRef.current = Date.now()
    setResult({ status: 'queued', downloadUrl: null, error: null })

    // Start first poll immediately
    void poll(jobId)

    return () => {
      activeJobRef.current = null
      clearTimer()
    }
  }, [jobId, poll, clearTimer])

  return result
}
