import { useEffect, useRef } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useFilterStore } from '@/shared/stores/filterStore'
import { encodeFilters, decodeFilters } from '@/lib/url-codec'

/**
 * useUrlState — purely a side-effect hook, called once in App.tsx.
 *
 * On mount: reads URL search params and hydrates the filter store.
 * Subscribes to the filter store and updates the URL whenever state changes.
 */
export function useUrlState(): void {
  const navigate = useNavigate()
  const location = useLocation()
  const applyFilterState = useFilterStore((s) => s.applyFilterState)
  const hasHydrated = useRef(false)

  // Hydrate from URL on mount (only once)
  useEffect(() => {
    if (hasHydrated.current) return
    hasHydrated.current = true
    const params = new URLSearchParams(location.search)
    if (params.toString()) {
      applyFilterState(decodeFilters(params))
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Sync store → URL whenever filter state changes
  useEffect(() => {
    const unsubscribe = useFilterStore.subscribe(
      (state) => state,
      (state) => {
        const params = encodeFilters(state)
        navigate({ search: params.toString() }, { replace: true })
      },
    )
    return unsubscribe
  }, [navigate])
}
