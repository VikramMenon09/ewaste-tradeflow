import { useState, useCallback, useMemo } from 'react'
import MapGL, { Layer, Source, type MapLayerMouseEvent } from 'react-map-gl/maplibre'
import { useFilterStore } from '@/shared/stores/filterStore'
import { useUIStore } from '@/shared/stores/uiStore'
import { useMapStore } from '@/shared/stores/mapStore'
import { METRIC_LABELS, BLUE_SCALE, RED_SCALE, type ChoroplethMetric } from '@/shared/types'
import { useMapData } from './useMapData'
import MapTooltip from './MapTooltip'
import MapLegend from './MapLegend'
import LayerToggle from './LayerToggle'
import Spinner from '@/shared/components/Spinner'
import type { ChoroplethCountry } from '@/shared/types'

const MAPTILER_KEY = import.meta.env.VITE_MAPTILER_KEY as string | undefined
// CartoDB Positron — light gray neutral basemap standard in academic research
const MAP_STYLE = MAPTILER_KEY
  ? `https://api.maptiler.com/maps/dataviz-light/style.json?key=${MAPTILER_KEY}`
  : 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json'

// Metrics where higher = worse (use red scale)
const HIGH_IS_BAD: ChoroplethMetric[] = ['prs', 'net_trade']

function getColorScale(metric: ChoroplethMetric) {
  return HIGH_IS_BAD.includes(metric) ? RED_SCALE : BLUE_SCALE
}

function buildFillExpression(
  data: ChoroplethCountry[],
  scale: readonly string[],
// eslint-disable-next-line @typescript-eslint/no-explicit-any
): any {
  if (!data.length) return ['literal', '#d6d3ce']

  const values = data.map((c) => c.value).filter((v) => v !== null) as number[]
  if (!values.length) return ['literal', '#d6d3ce']

  const min = Math.min(...values)
  const max = Math.max(...values)
  const range = max - min || 1

  const stops: [string, string][] = data
    .filter((c) => c.value !== null)
    .map((c) => {
      const normalized = ((c.value as number) - min) / range
      const idx = Math.min(scale.length - 1, Math.floor(normalized * scale.length))
      return [c.iso3, scale[idx]]
    })

  if (!stops.length) return ['literal', '#d6d3ce']

  return [
    'match',
    ['get', 'ISO3166-1-Alpha-3'],
    ...stops.flatMap(([iso3, color]) => [iso3, color]),
    '#d6d3ce', // default for unknown countries — light gray on light basemap
  ]
}

export default function ChoroplethMap() {
  const { metric, year } = useFilterStore()
  const { openPanel } = useUIStore()
  const setSelectedCountry = useMapStore((s) => s.selectCountry)
  const { data, isLoading, isError } = useMapData(metric, year)

  const [tooltip, setTooltip] = useState<{
    country: ChoroplethCountry
    x: number
    y: number
  } | null>(null)

  const countryMap = useMemo(() => {
    if (!data) return new Map<string, ChoroplethCountry>()
    return new Map(data.countries.map((c) => [c.iso3, c]))
  }, [data])

  const colorScale = getColorScale(metric)
  const fillExpression = useMemo(
    () => buildFillExpression(data?.countries ?? [], colorScale),
    [data, colorScale],
  )

  const { legendMin, legendMax } = useMemo(() => {
    const values = (data?.countries ?? [])
      .map((c) => c.value)
      .filter((v) => v !== null) as number[]
    if (!values.length) return { legendMin: 0, legendMax: 0 }
    return { legendMin: Math.min(...values), legendMax: Math.max(...values) }
  }, [data])

  const handleClick = useCallback(
    (e: MapLayerMouseEvent) => {
      const features = e.features
      if (!features?.length) return
      const iso3 = features[0].properties?.['ISO3166-1-Alpha-3'] as string | undefined
      if (!iso3) return
      setSelectedCountry(iso3)
      openPanel()
    },
    [setSelectedCountry, openPanel],
  )

  const handleMouseMove = useCallback(
    (e: MapLayerMouseEvent) => {
      const features = e.features
      if (!features?.length) {
        setTooltip(null)
        return
      }
      const iso3 = features[0].properties?.['ISO3166-1-Alpha-3'] as string | undefined
      const country = iso3 ? countryMap.get(iso3) : undefined
      if (!country) {
        setTooltip(null)
        return
      }
      setTooltip({ country, x: e.originalEvent.clientX, y: e.originalEvent.clientY })
    },
    [countryMap],
  )

  const handleMouseLeave = useCallback(() => setTooltip(null), [])

  return (
    <div className="relative w-full h-full">
      <MapGL
        initialViewState={{ longitude: 10, latitude: 20, zoom: 1.5 }}
        style={{ width: '100%', height: '100%' }}
        mapStyle={MAP_STYLE}
        interactiveLayerIds={['country-fill']}
        onClick={handleClick}
        onMouseMove={handleMouseMove}
        onMouseLeave={handleMouseLeave}
        cursor={tooltip ? 'pointer' : 'grab'}
      >
        <Source
          id="countries"
          type="geojson"
          data="https://raw.githubusercontent.com/datasets/geo-countries/master/data/countries.geojson"
        >
          {/* beforeId inserts our layers above Positron land-fill but below water/roads/labels */}
          <Layer
            id="country-fill"
            beforeId="waterway"
            type="fill"
            paint={{
              // eslint-disable-next-line @typescript-eslint/no-explicit-any
              'fill-color': fillExpression as any,
              'fill-opacity': 0.85,
            }}
          />
          <Layer
            id="country-border"
            beforeId="waterway"
            type="line"
            paint={{
              'line-color': '#b8b5b0',
              'line-width': 0.4,
            }}
          />
          <Layer
            id="country-highlight"
            type="fill"
            filter={['==', ['get', 'ISO3166-1-Alpha-3'], tooltip?.country.iso3 ?? '']}
            paint={{
              'fill-color': '#ffffff',
              'fill-opacity': 0.15,
            }}
          />
        </Source>
      </MapGL>

      <LayerToggle />

      <MapLegend
        metric={metric}
        min={legendMin}
        max={legendMax}
        hasData={!!(data?.countries.length)}
      />

      {isLoading && (
        <div className="absolute inset-0 flex items-center justify-center bg-black bg-opacity-30">
          <Spinner size="lg" />
        </div>
      )}

      {isError && (
        <div className="absolute top-3 left-1/2 -translate-x-1/2 text-xs px-4 py-2 rounded shadow-lg z-10"
          style={{ background: '#fffbeb', border: '1px solid #d97706', color: '#92400e' }}>
          No API data — connect the backend to see choropleth colors
        </div>
      )}

      {tooltip && (
        <MapTooltip
          country={tooltip.country}
          metric={metric}
          metricLabel={METRIC_LABELS[metric]}
          x={tooltip.x}
          y={tooltip.y}
        />
      )}
    </div>
  )
}
