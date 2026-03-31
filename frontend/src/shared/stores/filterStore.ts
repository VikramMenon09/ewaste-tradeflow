import { create } from 'zustand'
import { subscribeWithSelector } from 'zustand/middleware'
import { DEFAULT_FILTER_STATE, type FilterState, type ChoroplethMetric } from '@/shared/types'

interface FilterActions {
  setYear: (year: number) => void
  setMetric: (metric: ChoroplethMetric) => void
  setRegion: (region: string[]) => void
  toggleCategory: (category: number) => void
  setCompliantOnly: (value: boolean) => void
  setFlaggedOnly: (value: boolean) => void
  setTopN: (topN: number) => void
  setActiveView: (view: FilterState['activeView']) => void
  applyFilterState: (state: FilterState) => void
}

type FilterStore = FilterState & FilterActions

export const useFilterStore = create<FilterStore>()(
  subscribeWithSelector((set) => ({
    ...DEFAULT_FILTER_STATE,

    setYear: (year) => set({ year }),

    setMetric: (metric) => set({ metric }),

    setRegion: (region) => set({ region }),

    toggleCategory: (category) =>
      set((state) => ({
        category: state.category.includes(category)
          ? state.category.filter((c) => c !== category)
          : [...state.category, category],
      })),

    setCompliantOnly: (compliantOnly) => set({ compliantOnly }),

    setFlaggedOnly: (flaggedOnly) => set({ flaggedOnly }),

    setTopN: (topN) => set({ topN }),

    setActiveView: (activeView) => set({ activeView }),

    applyFilterState: (filterState) => set({ ...filterState }),
  })),
)
