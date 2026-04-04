import { useRef, useEffect, type RefObject, type DependencyList } from 'react'
import * as d3 from 'd3'

/**
 * useD3 — attach a D3 render function to an SVG ref.
 *
 * Clears all children before each render so D3 starts from a clean slate.
 * Only re-renders when `deps` change (not on every React render).
 */
export function useD3<SVGEl extends SVGSVGElement | SVGGElement = SVGSVGElement>(
  renderFn: (selection: d3.Selection<SVGEl, unknown, null, undefined>) => void,
  deps: DependencyList,
): RefObject<SVGEl> {
  const ref = useRef<SVGEl>(null)

  useEffect(() => {
    if (!ref.current) return
    const selection = d3.select(ref.current) as d3.Selection<SVGEl, unknown, null, undefined>
    // Remove all existing children before re-rendering
    selection.selectAll('*').remove()
    renderFn(selection)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)

  return ref
}
