import { DEFAULT_FILTER_STATE, YEAR_RANGE, type FilterState, type ChoroplethMetric } from '@/shared/types'

const VALID_METRICS: ChoroplethMetric[] = [
  'generation',
  'per_capita',
  'formal_collection',
  'net_trade',
  'exports',
  'imports',
  'prs',
  'export_intensity',
  'compliance_rate',
]

function isValidMetric(value: string): value is ChoroplethMetric {
  return VALID_METRICS.includes(value as ChoroplethMetric)
}

/**
 * Serialize a FilterState into URLSearchParams.
 * Human-readable: /explore?year=2022&metric=prs&region=EAS,SAS&flaggedOnly=true&view=map
 * Arrays encoded as comma-separated values.
 */
export function encodeFilters(state: FilterState): URLSearchParams {
  const params = new URLSearchParams()

  params.set('year', String(state.year))
  params.set('metric', state.metric)
  params.set('view', state.activeView)
  params.set('topN', String(state.topN))

  if (state.region.length > 0) {
    params.set('region', state.region.join(','))
  }

  if (state.category.length > 0) {
    params.set('category', state.category.join(','))
  }

  if (state.compliantOnly) {
    params.set('compliantOnly', 'true')
  }

  if (state.flaggedOnly) {
    params.set('flaggedOnly', 'true')
  }

  return params
}

/**
 * Deserialize URLSearchParams into a FilterState.
 * Handles missing/invalid params gracefully by filling defaults.
 */
export function decodeFilters(params: URLSearchParams): FilterState {
  const yearRaw = params.get('year')
  const year = yearRaw !== null ? parseInt(yearRaw, 10) : DEFAULT_FILTER_STATE.year
  const validYear =
    !isNaN(year) && year >= YEAR_RANGE.min && year <= YEAR_RANGE.max
      ? year
      : DEFAULT_FILTER_STATE.year

  const metricRaw = params.get('metric') ?? ''
  const metric = isValidMetric(metricRaw) ? metricRaw : DEFAULT_FILTER_STATE.metric

  const viewRaw = params.get('view')
  const activeView: FilterState['activeView'] =
    viewRaw === 'map' || viewRaw === 'sankey' ? viewRaw : DEFAULT_FILTER_STATE.activeView

  const regionRaw = params.get('region')
  const region =
    regionRaw && regionRaw.trim().length > 0
      ? regionRaw
          .split(',')
          .map((r) => r.trim())
          .filter(Boolean)
      : []

  const categoryRaw = params.get('category')
  const category =
    categoryRaw && categoryRaw.trim().length > 0
      ? categoryRaw
          .split(',')
          .map((c) => parseInt(c.trim(), 10))
          .filter((n) => !isNaN(n) && n >= 0 && n <= 6)
      : []

  const topNRaw = params.get('topN')
  const topN = topNRaw !== null ? parseInt(topNRaw, 10) : DEFAULT_FILTER_STATE.topN
  const validTopN = !isNaN(topN) && topN > 0 ? topN : DEFAULT_FILTER_STATE.topN

  const compliantOnly = params.get('compliantOnly') === 'true'
  const flaggedOnly = params.get('flaggedOnly') === 'true'

  return {
    year: validYear,
    metric,
    region,
    category,
    compliantOnly,
    flaggedOnly,
    topN: validTopN,
    activeView,
  }
}
