import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api-client'
import type { ChoroplethResponse } from '@/shared/types'

export function useMapData(metric: string, year: number) {
  return useQuery<ChoroplethResponse>({
    queryKey: ['choropleth', metric, year],
    queryFn: () => api.getChoropleth(metric, year),
    staleTime: 10 * 60 * 1000, // 10 minutes — data changes infrequently
  })
}
