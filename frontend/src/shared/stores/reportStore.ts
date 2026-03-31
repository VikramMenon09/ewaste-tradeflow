import { create } from 'zustand'
import type { ReportStatusResponse } from '@/shared/types'

interface ReportState {
  activeJobId: string | null
  reportStatus: ReportStatusResponse['status'] | null
  downloadUrl: string | null
  error: string | null
}

interface ReportActions {
  startReport: (jobId: string) => void
  setStatus: (status: ReportStatusResponse['status'], downloadUrl?: string | null, error?: string | null) => void
  clearReport: () => void
}

type ReportStore = ReportState & ReportActions

export const useReportStore = create<ReportStore>()((set) => ({
  activeJobId: null,
  reportStatus: null,
  downloadUrl: null,
  error: null,

  startReport: (jobId) =>
    set({
      activeJobId: jobId,
      reportStatus: 'queued',
      downloadUrl: null,
      error: null,
    }),

  setStatus: (status, downloadUrl = null, error = null) =>
    set({ reportStatus: status, downloadUrl, error }),

  clearReport: () =>
    set({
      activeJobId: null,
      reportStatus: null,
      downloadUrl: null,
      error: null,
    }),
}))
