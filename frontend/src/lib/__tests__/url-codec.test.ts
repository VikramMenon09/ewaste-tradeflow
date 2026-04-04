import { describe, it, expect } from 'vitest'
import { encodeFilters, decodeFilters } from '../url-codec'
import { DEFAULT_FILTER_STATE } from '@/shared/types'

describe('url-codec round-trip', () => {
  it('encodes and decodes default state without loss', () => {
    const params = encodeFilters(DEFAULT_FILTER_STATE)
    const decoded = decodeFilters(params)
    expect(decoded).toEqual(DEFAULT_FILTER_STATE)
  })

  it('encodes and decodes a non-default state', () => {
    const state = {
      year: 2020,
      metric: 'prs' as const,
      region: ['Asia', 'Europe'],
      category: [2, 5],
      compliantOnly: false,
      flaggedOnly: true,
      topN: 30,
      activeView: 'sankey' as const,
    }
    const decoded = decodeFilters(encodeFilters(state))
    expect(decoded).toEqual(state)
  })

  it('falls back to defaults for out-of-range year', () => {
    const params = new URLSearchParams('year=1800&metric=generation&view=map&topN=20')
    const decoded = decodeFilters(params)
    expect(decoded.year).toBe(DEFAULT_FILTER_STATE.year)
  })

  it('falls back to defaults for unknown metric', () => {
    const params = new URLSearchParams('year=2022&metric=unknown_metric&view=map&topN=20')
    const decoded = decodeFilters(params)
    expect(decoded.metric).toBe(DEFAULT_FILTER_STATE.metric)
  })

  it('falls back to default view for invalid view value', () => {
    const params = new URLSearchParams('year=2022&metric=generation&view=globe&topN=20')
    const decoded = decodeFilters(params)
    expect(decoded.activeView).toBe(DEFAULT_FILTER_STATE.activeView)
  })

  it('handles empty category and region params', () => {
    const params = new URLSearchParams('year=2022&metric=generation&view=map&topN=20')
    const decoded = decodeFilters(params)
    expect(decoded.region).toEqual([])
    expect(decoded.category).toEqual([])
  })

  it('does not include compliantOnly or flaggedOnly params when false', () => {
    const state = { ...DEFAULT_FILTER_STATE, compliantOnly: false, flaggedOnly: false }
    const params = encodeFilters(state)
    expect(params.has('compliantOnly')).toBe(false)
    expect(params.has('flaggedOnly')).toBe(false)
  })

  it('includes flaggedOnly param when true', () => {
    const state = { ...DEFAULT_FILTER_STATE, flaggedOnly: true }
    const params = encodeFilters(state)
    expect(params.get('flaggedOnly')).toBe('true')
  })
})

describe('decodeFilters', () => {
  it('correctly parses comma-separated regions', () => {
    const params = new URLSearchParams('year=2022&metric=generation&view=map&topN=20&region=Africa,Asia')
    const decoded = decodeFilters(params)
    expect(decoded.region).toEqual(['Africa', 'Asia'])
  })

  it('correctly parses comma-separated categories', () => {
    const params = new URLSearchParams('year=2022&metric=generation&view=map&topN=20&category=1,3,5')
    const decoded = decodeFilters(params)
    expect(decoded.category).toEqual([1, 3, 5])
  })

  it('filters out invalid category codes', () => {
    const params = new URLSearchParams('year=2022&metric=generation&view=map&topN=20&category=1,99,abc,3')
    const decoded = decodeFilters(params)
    expect(decoded.category).toEqual([1, 3])
  })
})
