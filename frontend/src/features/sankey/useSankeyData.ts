import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api-client'
import { useFilterStore } from '@/shared/stores/filterStore'
import type { SankeyResponse } from '@/shared/types'

export function useSankeyData() {
  const { year, topN, category, compliantOnly, flaggedOnly } = useFilterStore()

  return useQuery<SankeyResponse>({
    queryKey: ['sankey', year, topN, category, compliantOnly, flaggedOnly],
    queryFn: () =>
      api.getSankey({
        year,
        top_n: topN,
        category: category.length === 1 ? category[0] : undefined,
        flagged_only: flaggedOnly || undefined,
      }),
    staleTime: 10 * 60 * 1000,
  })
}
