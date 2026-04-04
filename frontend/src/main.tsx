import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Auth0Provider } from '@auth0/auth0-react'
import App from './app/App'
import './index.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      retry: 2,
    },
  },
})

const auth0Domain = import.meta.env.VITE_AUTH0_DOMAIN as string | undefined
const auth0ClientId = import.meta.env.VITE_AUTH0_CLIENT_ID as string | undefined
const auth0Audience = import.meta.env.VITE_AUTH0_AUDIENCE as string | undefined
const hasAuth0 = Boolean(auth0Domain && auth0ClientId)

function Root() {
  return (
    <BrowserRouter>
      <QueryClientProvider client={queryClient}>
        <App />
      </QueryClientProvider>
    </BrowserRouter>
  )
}

// Wrap with Auth0 only if credentials are configured
const tree = hasAuth0 ? (
  <Auth0Provider
    domain={auth0Domain!}
    clientId={auth0ClientId!}
    authorizationParams={{
      redirect_uri: window.location.origin,
      audience: auth0Audience,
    }}
  >
    <Root />
  </Auth0Provider>
) : (
  <Root />
)

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>{tree}</React.StrictMode>,
)
