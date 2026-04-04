import { useAuth0 } from '@auth0/auth0-react'

// Try to use Auth0 — gracefully degrade if the provider is not in the tree.
function useOptionalAuth0() {
  try {
    return useAuth0()
  } catch {
    return null
  }
}

export default function AuthButton() {
  const auth0 = useOptionalAuth0()

  if (!auth0 || !import.meta.env.VITE_AUTH0_DOMAIN) {
    return null // Auth not configured — hide the button
  }

  const { isAuthenticated, loginWithRedirect, logout, user } = auth0

  if (!isAuthenticated) {
    return (
      <button
        onClick={() => loginWithRedirect()}
        className="px-3 py-1 text-xs rounded border border-gray-700 text-gray-400 hover:text-white hover:border-gray-500 transition-colors"
      >
        Sign in
      </button>
    )
  }

  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-gray-400 hidden sm:block">{user?.email}</span>
      <button
        onClick={() => logout({ logoutParams: { returnTo: window.location.origin } })}
        className="px-3 py-1 text-xs rounded border border-gray-700 text-gray-400 hover:text-white hover:border-gray-500 transition-colors"
      >
        Sign out
      </button>
    </div>
  )
}
