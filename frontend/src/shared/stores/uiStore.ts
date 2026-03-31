import { create } from 'zustand'

interface UIState {
  panelOpen: boolean
  sidebarOpen: boolean
  loadingStates: Record<string, boolean>
}

interface UIActions {
  openPanel: () => void
  closePanel: () => void
  toggleSidebar: () => void
  setSidebarOpen: (open: boolean) => void
  setLoading: (key: string, loading: boolean) => void
  isLoading: (key: string) => boolean
}

type UIStore = UIState & UIActions

export const useUIStore = create<UIStore>()((set, get) => ({
  panelOpen: false,
  sidebarOpen: true,
  loadingStates: {},

  openPanel: () => set({ panelOpen: true }),

  closePanel: () => set({ panelOpen: false }),

  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),

  setSidebarOpen: (open) => set({ sidebarOpen: open }),

  setLoading: (key, loading) =>
    set((state) => ({
      loadingStates: { ...state.loadingStates, [key]: loading },
    })),

  isLoading: (key) => get().loadingStates[key] ?? false,
}))
