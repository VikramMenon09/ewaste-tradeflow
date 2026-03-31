import { create } from 'zustand'

export interface Viewport {
  longitude: number
  latitude: number
  zoom: number
}

interface MapState {
  selectedCountry: string | null
  hoveredCountry: string | null
  activeLayer: string
  viewport: Viewport
}

interface MapActions {
  selectCountry: (iso3: string | null) => void
  hoverCountry: (iso3: string | null) => void
  clearSelection: () => void
  setViewport: (viewport: Viewport) => void
  setActiveLayer: (layer: string) => void
}

type MapStore = MapState & MapActions

const DEFAULT_VIEWPORT: Viewport = {
  longitude: 0,
  latitude: 20,
  zoom: 1.8,
}

export const useMapStore = create<MapStore>()((set) => ({
  selectedCountry: null,
  hoveredCountry: null,
  activeLayer: 'choropleth',
  viewport: DEFAULT_VIEWPORT,

  selectCountry: (iso3) => set({ selectedCountry: iso3 }),

  hoverCountry: (iso3) => set({ hoveredCountry: iso3 }),

  clearSelection: () => set({ selectedCountry: null }),

  setViewport: (viewport) => set({ viewport }),

  setActiveLayer: (activeLayer) => set({ activeLayer }),
}))
