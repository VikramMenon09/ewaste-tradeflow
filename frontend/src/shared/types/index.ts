// ─── Filter State ────────────────────────────────────────────────────────────

export type ChoroplethMetric =
  | 'generation'
  | 'per_capita'
  | 'formal_collection'
  | 'net_trade'
  | 'exports'
  | 'imports'
  | 'prs'
  | 'export_intensity'
  | 'compliance_rate'

export type FilterState = {
  year: number
  metric: ChoroplethMetric
  region: string[]
  category: number[]
  compliantOnly: boolean
  flaggedOnly: boolean
  topN: number
  activeView: 'map' | 'sankey'
}

// ─── API Response Types ───────────────────────────────────────────────────────

export type IncomeClassification = 'high' | 'upper_middle' | 'lower_middle' | 'low'
export type ComplianceColor = 'green' | 'amber' | 'red'

export type CountryBasic = {
  iso3: string
  name: string
  region: string
  subregion: string
  income_classification: IncomeClassification
  basel_signatory: boolean
  basel_ban_ratified: boolean
  is_oecd_member: boolean
}

export type ChoroplethCountry = {
  iso3: string
  name: string
  value: number | null
  confidence_tier: string | null
  data_vintage_year: number | null
  is_missing: boolean
}

export type ChoroplethResponse = {
  year: number
  metric: string
  countries: ChoroplethCountry[]
}

export type SankeyNode = {
  id: string
  name: string
  region: string
}

export type SankeyLink = {
  source: string
  target: string
  volume_mt: number
  value_usd: number | null
  compliance_color: ComplianceColor
  has_violation: boolean
  prs_risk_flag: boolean
  importer_prs_score: number | null
  data_conflict: boolean
  confidence_tier: string
  mapping_confidence: string
}

export type SankeyResponse = {
  year: number
  nodes: SankeyNode[]
  links: SankeyLink[]
}

export type GenerationPoint = {
  year: number
  total_mt: number
  per_capita_kg: number
  formal_collection_rate: number | null
  confidence_tier: string
  is_interpolated: boolean
}

export type TradePartner = {
  partner_iso3: string
  partner_name: string
  volume_mt: number
  value_usd: number | null
  prs_risk_flag: boolean
  compliance_color: ComplianceColor
}

export type ExportPartner = TradePartner & {
  basel_compliant: boolean | null
}

export type CountryProfile = {
  iso3: string
  name: string
  region: string
  subregion: string
  income_classification: string
  basel_signatory: boolean
  basel_ban_ratified: boolean
  is_oecd_member: boolean
  prs_score: number | null
  prs_methodology_version: number | null
  generation_series: GenerationPoint[]
  top_exports: ExportPartner[]
  top_imports: TradePartner[]
}

export type ReportGenerateResponse = {
  job_id: string
  poll_url: string
  estimated_wait_seconds: number
}

export type ReportStatusResponse = {
  job_id: string
  status: 'queued' | 'processing' | 'complete' | 'failed'
  download_url: string | null
  expires_at: string | null
  error_message: string | null
}

export type UserSavedState = {
  id: string
  name: string
  description?: string
  filter_state: FilterState
  is_default: boolean
  created_at: string
  updated_at: string
}

// ─── Constants ───────────────────────────────────────────────────────────────

export const CHOROPLETH_METRICS = [
  'generation',
  'per_capita',
  'formal_collection',
  'net_trade',
  'exports',
  'imports',
  'prs',
  'export_intensity',
  'compliance_rate',
] as const

export const METRIC_LABELS: Record<ChoroplethMetric, string> = {
  generation: 'Total Generation (MT)',
  per_capita: 'Per Capita (kg)',
  formal_collection: 'Formal Collection Rate (%)',
  net_trade: 'Net Trade (MT)',
  exports: 'Exports (MT)',
  imports: 'Imports (MT)',
  prs: 'PRS Risk Score',
  export_intensity: 'Export Intensity',
  compliance_rate: 'Compliance Rate (%)',
}

export const EWASTE_CATEGORIES = [0, 1, 2, 3, 4, 5, 6] as const

export const CATEGORY_LABELS: Record<number, string> = {
  0: 'All Categories',
  1: 'Temperature Exchange',
  2: 'Screens & Monitors',
  3: 'Lamps',
  4: 'Large Equipment',
  5: 'Small Equipment',
  6: 'Small IT & Telecom',
}

export const COMPLIANCE_COLORS: Record<ComplianceColor, string> = {
  green: '#22c55e',
  amber: '#f59e0b',
  red: '#ef4444',
} as const

export const YEAR_RANGE = { min: 2010, max: 2024 } as const

export const DEFAULT_FILTER_STATE: FilterState = {
  year: 2022,
  metric: 'generation',
  region: [],
  category: [],
  compliantOnly: false,
  flaggedOnly: false,
  topN: 20,
  activeView: 'map',
}

// ─── Color Scales (colorblind-safe, 7-step sequential) ───────────────────────

export const BLUE_SCALE = [
  '#f7fbff',
  '#deebf7',
  '#c6dbef',
  '#9ecae1',
  '#6baed6',
  '#3182bd',
  '#08519c',
] as const

export const RED_SCALE = [
  '#fff5f0',
  '#fee0d2',
  '#fcbba1',
  '#fc9272',
  '#fb6a4a',
  '#de2d26',
  '#a50f15',
] as const

export const GREEN_SCALE = [
  '#f7fcf5',
  '#e5f5e0',
  '#c7e9c0',
  '#a1d99b',
  '#74c476',
  '#31a354',
  '#006d2c',
] as const
