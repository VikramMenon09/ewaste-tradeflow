# ADR-001: Map Library — MapLibre GL JS over Mapbox GL JS

**Date:** March 2026
**Status:** Accepted

---

## Context

The platform requires a high-performance WebGL map renderer capable of rendering choropleth layers at country level with dynamic color expressions, line layers for trade routes, and tooltip interactions. The PRD specified Mapbox GL JS but flagged its licensing cost as a risk.

Mapbox GL JS v2 (the current version) is source-available but not open source. It charges per map load above 50,000/month on the free tier, at approximately $0.50 per 1,000 additional loads.

MapLibre GL JS is an open-source fork of Mapbox GL JS v1 maintained by the MapLibre organization. It is BSD-licensed with no per-load cost.

## Decision

Use **MapLibre GL JS** instead of Mapbox GL JS.

## Rationale

- MapLibre is API-compatible with Mapbox GL JS v1. The core map component code is nearly identical; only the import statement and the tile URL change.
- The features we need (choropleth fills, line layers, GeoJSON sources, `match` expressions for dynamic color) are all fully supported in MapLibre.
- Mapbox-proprietary features we do not need: Terrain-DEM, Standard Style, Navigation SDK.
- Cost predictability matters for a public-interest platform that may see variable traffic from press coverage.
- The `react-map-gl` library supports MapLibre as a first-class target.
- For base map tiles: Maptiler provides a generous free tier (100,000 tiles/month) and is MapLibre-compatible.

## Consequences

- Slightly less polished documentation than Mapbox, though MapLibre's docs are improving.
- If we ever need Mapbox-proprietary features (unlikely given the use case), we can switch back — the component interface is abstracted behind a `MapContainer` component.
- No per-load licensing cost at any scale.
