import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api-client'
import { useMapStore } from '@/shared/stores/mapStore'
import type { CountryProfile } from '@/shared/types'

export function useCountryProfile() {
  const selectedCountry = useMapStore((s) => s.selectedCountry)

  return useQuery<CountryProfile>({
    queryKey: ['countryProfile', selectedCountry],
    queryFn: () => api.getCountryProfile(selectedCountry!),
    enabled: Boolean(selectedCountry),
    staleTime: 10 * 60 * 1000,
  })
}
