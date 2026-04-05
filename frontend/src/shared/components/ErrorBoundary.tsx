import { Component, type ErrorInfo, type ReactNode } from 'react'

interface Props {
  children: ReactNode
  /** Optional custom fallback. Receives the error for display. */
  fallback?: (error: Error, reset: () => void) => ReactNode
  /** Label shown in the default fallback (e.g. "map", "chart") */
  label?: string
}

interface State {
  error: Error | null
}

/**
 * Class-based error boundary — catches render-time exceptions in the subtree
 * and renders a contained fallback instead of crashing the whole app.
 */
export default class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('[ErrorBoundary]', error, info.componentStack)
  }

  reset = () => this.setState({ error: null })

  render() {
    const { error } = this.state
    if (!error) return this.props.children

    if (this.props.fallback) {
      return this.props.fallback(error, this.reset)
    }

    const label = this.props.label ?? 'component'
    return (
      <div
        className="flex flex-col items-center justify-center gap-3 p-6 rounded"
        style={{
          background: '#fffbeb',
          border: '1px solid #d97706',
          color: '#92400e',
          minHeight: 120,
        }}
        role="alert"
        aria-live="assertive"
      >
        <p className="text-sm font-semibold">
          The {label} failed to render.
        </p>
        <p className="text-xs" style={{ color: '#b45309' }}>
          {error.message}
        </p>
        <button
          onClick={this.reset}
          className="text-xs px-3 py-1 rounded border transition-colors"
          style={{
            borderColor: '#d97706',
            color: '#92400e',
            background: 'transparent',
          }}
        >
          Try again
        </button>
      </div>
    )
  }
}
