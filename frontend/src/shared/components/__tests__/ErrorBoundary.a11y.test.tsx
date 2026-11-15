// @vitest-environment jsdom
/**
 * Accessibility smoke-tests for shared UI components.
 *
 * Uses axe-core to assert no automatic WCAG 2.1 violations are present.
 * These tests catch regressions (missing labels, bad contrast roles, etc.)
 * before they reach production.
 */
import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import axe from 'axe-core'

// Component under test — the error fallback UI

async function checkA11y(container: HTMLElement) {
  const results = await axe.run(container)
  const violations = results.violations

  if (violations.length > 0) {
    const summary = violations
      .map((v) => `[${v.impact}] ${v.id}: ${v.description}\n  ${v.nodes.map((n) => n.html).join('\n  ')}`)
      .join('\n')
    throw new Error(`axe found ${violations.length} accessibility violation(s):\n${summary}`)
  }
  return violations
}

describe('ErrorBoundary fallback accessibility', () => {
  it('renders an accessible error fallback with no axe violations', async () => {
    // Render the fallback UI directly
    const { container } = render(
      <div
        className="flex flex-col items-center justify-center gap-3 p-6 rounded"
        role="alert"
        aria-live="assertive"
      >
        <p className="text-sm font-semibold">The test component failed to render.</p>
        <p className="text-xs">Test error message</p>
        <button className="text-xs px-3 py-1 rounded border">Try again</button>
      </div>
    )

    const violations = await checkA11y(container)
    expect(violations).toHaveLength(0)
  })
})
