import { sankey as d3Sankey, sankeyLinkHorizontal } from 'd3-sankey'
import type { SankeyNodeMinimal, SankeyLinkMinimal } from 'd3-sankey'
import { useD3 } from '@/shared/hooks/useD3'
import { useSankeyData } from './useSankeyData'
import { COMPLIANCE_COLORS } from '@/shared/types'
import Spinner from '@/shared/components/Spinner'
import EmptyState from '@/shared/components/EmptyState'
import type { SankeyNode, SankeyLink } from '@/shared/types'

// D3-sankey types
type D3SankeyNode = SankeyNodeMinimal<SankeyNode, SankeyLink> & SankeyNode & {
  x0: number; x1: number; y0: number; y1: number
}
type D3SankeyLink = SankeyLinkMinimal<D3SankeyNode, SankeyLink> & SankeyLink & {
  width: number; source: D3SankeyNode; target: D3SankeyNode
}

// Darker compliance colors for light background readability
const COMPLIANCE_COLORS_LIGHT: Record<string, string> = {
  green: '#166534',
  amber: '#92400e',
  red:   '#991b1b',
}

export default function SankeyDiagram() {
  const { data, isLoading, isError } = useSankeyData()

  const { nodes: rawNodes, links: rawLinks } = data ?? { nodes: [], links: [] }

  const ref = useD3<SVGSVGElement>(
    (svg) => {
      if (!rawNodes.length || !rawLinks.length) return

      const el = svg.node()!
      const width = el.clientWidth || 900
      const height = el.clientHeight || 500
      const margin = { top: 16, right: 16, bottom: 16, left: 16 }

      const generator = d3Sankey<D3SankeyNode, D3SankeyLink>()
        .nodeId((d) => d.id)
        .nodeWidth(14)
        .nodePadding(10)
        .extent([
          [margin.left, margin.top],
          [width - margin.right, height - margin.bottom],
        ])

      const sankeyNodes: D3SankeyNode[] = rawNodes.map((n) => ({ ...n } as D3SankeyNode))
      const sankeyLinks: D3SankeyLink[] = rawLinks.map((l) => ({
        ...l,
        value: l.volume_mt ?? 1,
      })) as unknown as D3SankeyLink[]

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const { nodes, links } = generator({ nodes: sankeyNodes as any, links: sankeyLinks as any }) as { nodes: D3SankeyNode[]; links: D3SankeyLink[] }

      // Links
      svg
        .append('g')
        .attr('fill', 'none')
        .selectAll('path')
        .data(links)
        .join('path')
        .attr('d', sankeyLinkHorizontal())
        .attr('stroke', (d) => COMPLIANCE_COLORS[d.compliance_color] ?? '#a8a29e')
        .attr('stroke-width', (d) => Math.max(1, d.width))
        .attr('stroke-opacity', 0.35)
        .append('title')
        .text((d) => `${d.source.name} → ${d.target.name}\n${(d.volume_mt ?? 0).toLocaleString()} MT`)

      // Nodes
      svg
        .append('g')
        .selectAll('rect')
        .data(nodes)
        .join('rect')
        .attr('x', (d) => d.x0)
        .attr('y', (d) => d.y0)
        .attr('height', (d) => d.y1 - d.y0)
        .attr('width', (d) => d.x1 - d.x0)
        .attr('fill', '#1e3a5f')
        .attr('rx', 2)
        .append('title')
        .text((d) => d.name)

      // Labels
      svg
        .append('g')
        .style('font-size', '11px')
        .style('font-family', 'ui-sans-serif, system-ui, sans-serif')
        .style('fill', '#1c1917')
        .selectAll('text')
        .data(nodes)
        .join('text')
        .attr('x', (d) => (d.x0 < width / 2 ? d.x1 + 6 : d.x0 - 6))
        .attr('y', (d) => (d.y0 + d.y1) / 2)
        .attr('dy', '0.35em')
        .attr('text-anchor', (d) => (d.x0 < width / 2 ? 'start' : 'end'))
        .text((d) => d.name)

      // Volume labels on large links
      svg
        .append('g')
        .selectAll('text')
        .data(links.filter((l) => l.width > 10))
        .join('text')
        .attr('x', (d) => (d.source.x1 + d.target.x0) / 2)
        .attr('y', (d) => ((d.source.y0 + d.source.y1 + d.target.y0 + d.target.y1) / 4))
        .attr('text-anchor', 'middle')
        .attr('dy', '0.35em')
        .style('font-size', '9px')
        .style('font-family', 'ui-monospace, monospace')
        .style('fill', '#57534e')
        .style('pointer-events', 'none')
        .text((d) => {
          const v = d.volume_mt ?? 0
          if (v >= 1_000_000) return `${(v/1_000_000).toFixed(1)}M t`
          if (v >= 1_000) return `${(v/1_000).toFixed(0)}k t`
          return `${v} t`
        })

      // Compliance legend
      const legendData = [
        { label: 'Basel compliant', color: COMPLIANCE_COLORS_LIGHT.green },
        { label: 'Uncertain',       color: COMPLIANCE_COLORS_LIGHT.amber },
        { label: 'Potential violation', color: COMPLIANCE_COLORS_LIGHT.red },
      ]
      const lg = svg.append('g').attr('transform', `translate(${margin.left}, ${height - margin.bottom - 12})`)
      legendData.forEach((d, i) => {
        const g = lg.append('g').attr('transform', `translate(${i * 140}, 0)`)
        g.append('rect').attr('width', 12).attr('height', 6).attr('y', -3).attr('fill', d.color).attr('opacity', 0.7).attr('rx', 1)
        g.append('text').attr('x', 16).attr('fill', '#57534e').style('font-size', '9px').style('font-family', 'ui-sans-serif').text(d.label)
      })
    },
    [rawNodes, rawLinks],
  )

  if (isError) {
    return (
      <EmptyState
        title="Could not load flow data"
        description="Check that the API is running and trade flow data is available."
      />
    )
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Spinner size="lg" />
      </div>
    )
  }

  if (!rawNodes.length) {
    return (
      <EmptyState
        title="No flows found"
        description="Try adjusting the filters — no trade flows match the current selection."
      />
    )
  }

  return (
    <div className="w-full h-full p-4" style={{ background: 'var(--c-bg)' }}>
      <svg ref={ref} className="w-full h-full" style={{ background: 'var(--c-bg)' }} />
    </div>
  )
}
