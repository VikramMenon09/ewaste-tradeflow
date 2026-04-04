import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useAuth0 } from '@auth0/auth0-react'
import { api } from '@/lib/api-client'
import { useFilterStore } from '@/shared/stores/filterStore'
import Spinner from '@/shared/components/Spinner'
import type { UserSavedState } from '@/shared/types'

// Guard: only render if Auth0 is configured and user is authenticated
function useOptionalAuth0() {
  try {
    return useAuth0()
  } catch {
    return null
  }
}

export default function SavedStatesMenu() {
  const auth0 = useOptionalAuth0()
  const [open, setOpen] = useState(false)
  const [saveName, setSaveName] = useState('')
  const [saving, setSaving] = useState(false)
  const qc = useQueryClient()
  const filterState = useFilterStore()
  const applyFilterState = useFilterStore((s) => s.applyFilterState)

  const isAuthenticated = auth0?.isAuthenticated ?? false

  const { data: states, isLoading } = useQuery<UserSavedState[]>({
    queryKey: ['savedStates'],
    queryFn: api.getSavedStates,
    enabled: isAuthenticated && open,
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.deleteSavedState(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['savedStates'] }),
  })

  async function handleSave() {
    if (!saveName.trim()) return
    setSaving(true)
    try {
      await api.createSavedState({
        name: saveName.trim(),
        filter_state: filterState,
      })
      await qc.invalidateQueries({ queryKey: ['savedStates'] })
      setSaveName('')
    } finally {
      setSaving(false)
    }
  }

  function handleLoad(state: UserSavedState) {
    applyFilterState(state.filter_state)
    setOpen(false)
  }

  if (!isAuthenticated || !import.meta.env.VITE_AUTH0_DOMAIN) return null

  return (
    <div className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        className="px-3 py-1 text-xs rounded border border-gray-700 text-gray-400 hover:text-white hover:border-gray-500 transition-colors"
      >
        Saved views
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-1 w-64 bg-gray-900 border border-gray-700 rounded shadow-xl z-50 text-xs">
          {/* Save current state */}
          <div className="p-3 border-b border-gray-800">
            <p className="text-gray-400 mb-2">Save current view</p>
            <div className="flex gap-2">
              <input
                type="text"
                value={saveName}
                onChange={(e) => setSaveName(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSave()}
                placeholder="View name…"
                className="flex-1 bg-gray-800 border border-gray-700 rounded px-2 py-1 text-white placeholder-gray-600 text-xs"
              />
              <button
                onClick={handleSave}
                disabled={!saveName.trim() || saving}
                className="px-2 py-1 bg-emerald-700 hover:bg-emerald-600 disabled:opacity-40 text-white rounded transition-colors"
              >
                {saving ? <Spinner size="sm" /> : 'Save'}
              </button>
            </div>
          </div>

          {/* Saved states list */}
          <div className="max-h-56 overflow-y-auto">
            {isLoading && (
              <div className="flex justify-center p-4">
                <Spinner size="sm" />
              </div>
            )}
            {!isLoading && (!states || states.length === 0) && (
              <p className="text-gray-600 text-center p-4">No saved views yet</p>
            )}
            {states?.map((s) => (
              <div
                key={s.id}
                className="flex items-center justify-between px-3 py-2 hover:bg-gray-800 group"
              >
                <button
                  onClick={() => handleLoad(s)}
                  className="flex-1 text-left text-gray-300 hover:text-white truncate"
                >
                  {s.name}
                </button>
                <button
                  onClick={() => deleteMutation.mutate(s.id)}
                  className="text-gray-600 hover:text-red-400 transition-colors opacity-0 group-hover:opacity-100 ml-2"
                  aria-label="Delete saved view"
                >
                  ✕
                </button>
              </div>
            ))}
          </div>

          {/* Close */}
          <div className="p-2 border-t border-gray-800 text-right">
            <button
              onClick={() => setOpen(false)}
              className="text-gray-600 hover:text-gray-400 text-xs"
            >
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
