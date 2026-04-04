import * as d3 from 'd3'
import { useD3 } from '@/shared/hooks/useD3'
import type { GenerationPoint } from '@/shared/types'

interface GenerationChartProps {
  data: GenerationPoint[]
}

export default function GenerationChart({ data }: GenerationChartProps) {
  const ref = useD3<SVGSVGElement>(
    (svg) => {
      if (!data.length) return

      const el = svg.node()!
      const width = el.clientWidth || 280
      const height = 110
      const margin = { top: 10, right: 10, bottom: 22, left: 42 }
      const innerWidth = width - margin.left - margin.right
      const innerHeight = height - margin.top - margin.bottom

      svg.attr('viewBox', `0 0 ${width} ${height}`)

      const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`)

      const x = d3
        .scaleLinear()
        .domain(d3.extent(data, (d) => d.year) as [number, number])
        .range([0, innerWidth])

      const y = d3
        .scaleLinear()
        .domain([0, d3.max(data, (d) => d.total_mt) ?? 1])
        .nice()
        .range([innerHeight, 0])

      // Grid lines
      g.append('g')
        .attr('class', 'grid')
        .call(d3.axisLeft(y).ticks(4).tickSize(-innerWidth).tickFormat(() => ''))
        .call((g) => g.select('.domain').remove())
        .call((g) => g.selectAll('.tick line').attr('stroke', '#e8e5e0').attr('stroke-dasharray', '2,2'))

      // Area
      const area = d3
        .area<GenerationPoint>()
        .x((d) => x(d.year))
        .y0(innerHeight)
        .y1((d) => y(d.total_mt))
        .curve(d3.curveMonotoneX)

      g.append('path')
        .datum(data)
        .attr('fill', '#dcfce7')
        .attr('d', area)

      // Line
      const line = d3
        .line<GenerationPoint>()
        .x((d) => x(d.year))
        .y((d) => y(d.total_mt))
        .curve(d3.curveMonotoneX)

      g.append('path')
        .datum(data)
        .attr('fill', 'none')
        .attr('stroke', '#166534')
        .attr('stroke-width', 1.5)
        .attr('d', line)

      // Interpolated dots
      g.selectAll('.interp-dot')
        .data(data.filter((d) => d.is_interpolated))
        .join('circle')
        .attr('cx', (d) => x(d.year))
        .attr('cy', (d) => y(d.total_mt))
        .attr('r', 3)
        .attr('fill', '#94a3b8')
        .attr('stroke', '#fff')
        .attr('stroke-width', 1)

      // X axis
      g.append('g')
        .attr('transform', `translate(0,${innerHeight})`)
        .call(d3.axisBottom(x).ticks(5).tickFormat(d3.format('d')))
        .call((g) => g.select('.domain').attr('stroke', '#d6d3ce'))
        .call((g) => g.selectAll('.tick line').attr('stroke', '#d6d3ce'))
        .selectAll('text')
        .style('fill', '#a8a29e')
        .style('font-size', '9px')
        .style('font-family', 'ui-monospace, monospace')

      // Y axis
      g.append('g')
        .call(d3.axisLeft(y).ticks(4).tickFormat((v) => {
          const n = Number(v)
          if (n >= 1_000_000) return `${(n/1_000_000).toFixed(1)}M`
          if (n >= 1_000) return `${(n/1_000).toFixed(0)}k`
          return String(n)
        }))
        .call((g) => g.select('.domain').attr('stroke', '#d6d3ce'))
        .call((g) => g.selectAll('.tick line').attr('stroke', '#d6d3ce'))
        .selectAll('text')
        .style('fill', '#a8a29e')
        .style('font-size', '9px')
        .style('font-family', 'ui-monospace, monospace')
    },
    [data],
  )

  return <svg ref={ref} className="w-full" style={{ height: 110, background: 'transparent' }} />
}
