import type {
  CountryBasic,
  ChoroplethResponse,
  SankeyResponse,
  CountryProfile,
  ReportGenerateResponse,
  ReportStatusResponse,
  UserSavedState,
  FilterState,
} from '@/shared/types'

const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

// ─── Error Type ──────────────────────────────────────────────────────────────

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

// ─── Core Client ─────────────────────────────────────────────────────────────

class ApiClient {
  private baseUrl: string
  private getAccessToken: (() => Promise<string>) | null = null

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl
  }

  setTokenGetter(fn: () => Promise<string>): void {
    this.getAccessToken = fn
  }

  private async buildHeaders(extra?: Record<string, string>): Promise<Headers> {
    const headers = new Headers({ 'Content-Type': 'application/json', ...extra })
    if (this.getAccessToken) {
      try {
        const token = await this.getAccessToken()
        headers.set('Authorization', `Bearer ${token}`)
      } catch {
        // Not authenticated — proceed without token
      }
    }
    return headers
  }

  private buildUrl(path: string, params?: Record<string, unknown>): string {
    const url = new URL(`${this.baseUrl}${path}`)
    if (params) {
      for (const [key, value] of Object.entries(params)) {
        if (value !== undefined && value !== null) {
          url.searchParams.set(key, String(value))
        }
      }
    }
    return url.toString()
  }

  async get<T>(path: string, params?: Record<string, unknown>): Promise<T> {
    const headers = await this.buildHeaders()
    const response = await fetch(this.buildUrl(path, params), {
      method: 'GET',
      headers,
    })
    if (!response.ok) {
      const message = await response.text().catch(() => response.statusText)
      throw new ApiError(response.status, message)
    }
    return response.json() as Promise<T>
  }

  async post<T>(path: string, body: unknown): Promise<T> {
    const headers = await this.buildHeaders()
    const response = await fetch(this.buildUrl(path), {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
    })
    if (!response.ok) {
      const message = await response.text().catch(() => response.statusText)
      throw new ApiError(response.status, message)
    }
    return response.json() as Promise<T>
  }

  async delete(path: string): Promise<void> {
    const headers = await this.buildHeaders()
    const response = await fetch(this.buildUrl(path), {
      method: 'DELETE',
      headers,
    })
    if (!response.ok) {
      const message = await response.text().catch(() => response.statusText)
      throw new ApiError(response.status, message)
    }
  }

  async getBlob(path: string, params?: Record<string, unknown>): Promise<Blob> {
    const headers = await this.buildHeaders({ 'Content-Type': 'application/octet-stream' })
    headers.delete('Content-Type') // Let browser set appropriate Accept
    const response = await fetch(this.buildUrl(path, params), {
      method: 'GET',
      headers,
    })
    if (!response.ok) {
      const message = await response.text().catch(() => response.statusText)
      throw new ApiError(response.status, message)
    }
    return response.blob()
  }
}

// ─── Singleton Instance ───────────────────────────────────────────────────────

const client = new ApiClient(BASE_URL)

export function configureApiClient(getAccessToken: () => Promise<string>): void {
  client.setTokenGetter(getAccessToken)
}

// ─── Typed API Methods ────────────────────────────────────────────────────────

export const api = {
  getCountries: (params?: { region?: string; income_class?: string }): Promise<CountryBasic[]> =>
    client.get<CountryBasic[]>('/api/v1/countries', params as Record<string, unknown>),

  getChoropleth: (metric: string, year: number): Promise<ChoroplethResponse> =>
    client.get<ChoroplethResponse>('/api/v1/map/choropleth', { metric, year }),

  getSankey: (params: {
    year: number
    top_n?: number
    exporter_region?: string
    importer_region?: string
    flagged_only?: boolean
    category?: number
  }): Promise<SankeyResponse> =>
    client.get<SankeyResponse>('/api/v1/map/flows/sankey', params as Record<string, unknown>),

  getCountryProfile: (iso3: string): Promise<CountryProfile> =>
    client.get<CountryProfile>(`/api/v1/country/${encodeURIComponent(iso3)}/profile`),

  generateReport: (type: string, params: object): Promise<ReportGenerateResponse> =>
    client.post<ReportGenerateResponse>('/api/v1/reports/generate', { type, ...params }),

  getReportStatus: (jobId: string): Promise<ReportStatusResponse> =>
    client.get<ReportStatusResponse>(`/api/v1/reports/${encodeURIComponent(jobId)}`),

  exportCsv: (params: object): Promise<Blob> =>
    client.getBlob('/api/v1/export/csv', params as Record<string, unknown>),

  getSavedStates: (): Promise<UserSavedState[]> =>
    client.get<UserSavedState[]>('/api/v1/saved-states'),

  createSavedState: (data: {
    name: string
    description?: string
    filter_state: FilterState
    is_default?: boolean
  }): Promise<UserSavedState> => client.post<UserSavedState>('/api/v1/saved-states', data),

  deleteSavedState: (id: string): Promise<void> =>
    client.delete(`/api/v1/saved-states/${encodeURIComponent(id)}`),
}
