/**
 * Format a metric-tonne value with appropriate precision.
 *   ≥1000 MT  → "1,234 MT"
 *   1–999 MT  → "123 MT"
 *   <1 MT     → "0.8 MT"
 *   null      → "—"
 */
export function formatMT(value: number | null | undefined): string {
  if (value === null || value === undefined) return '—'
  if (value >= 1000) {
    return (
      new Intl.NumberFormat('en-US', { maximumFractionDigits: 0 }).format(Math.round(value)) + ' MT'
    )
  }
  if (value >= 1) {
    return (
      new Intl.NumberFormat('en-US', { maximumFractionDigits: 1 }).format(value) + ' MT'
    )
  }
  return (
    new Intl.NumberFormat('en-US', { minimumFractionDigits: 1, maximumFractionDigits: 2 }).format(
      value,
    ) + ' MT'
  )
}

/**
 * Format a USD value.
 *   null → "—"
 */
export function formatUSD(value: number | null | undefined): string {
  if (value === null || value === undefined) return '—'
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    notation: value >= 1_000_000 ? 'compact' : 'standard',
    maximumFractionDigits: value >= 1_000_000 ? 1 : 0,
  }).format(value)
}

/**
 * Format a percentage value.
 */
export function formatPercent(value: number | null | undefined, decimals = 1): string {
  if (value === null || value === undefined) return '—'
  return new Intl.NumberFormat('en-US', {
    style: 'percent',
    minimumFractionDigits: 0,
    maximumFractionDigits: decimals,
  }).format(value / 100)
}

/**
 * Format a PRS score (0–10).
 */
export function formatPRS(value: number | null | undefined): string {
  if (value === null || value === undefined) return '—'
  return new Intl.NumberFormat('en-US', { minimumFractionDigits: 1, maximumFractionDigits: 1 }).format(value)
}
