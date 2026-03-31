"""Map data router — choropleth and Sankey diagram endpoints.

These are the most performance-critical endpoints in the API.  Both query
pre-aggregated dbt mart tables and cache results in Redis.

Endpoints:
  GET /map/choropleth      — per-country metric values for map colouring
  GET /map/flows/sankey    — bilateral trade flows for Sankey diagram
"""

from __future__ import annotations

from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.schemas import ChoroplethResponse, SankeyResponse
from app.services.cache import cache_service
from app.services.choropleth import METRIC_COLUMN_MAP, get_choropleth
from app.services.sankey import get_sankey

router = APIRouter(prefix="/map", tags=["map"])

_CHOROPLETH_TTL = 21600  # 6 hours
_SANKEY_TTL = 21600      # 6 hours

MetricLiteral = Literal[
    "generation",
    "per_capita",
    "formal_collection",
    "net_trade",
    "exports",
    "imports",
    "prs",
    "export_intensity",
    "compliance_rate",
]


@router.get("/choropleth", response_model=ChoroplethResponse)
async def choropleth(
    metric: MetricLiteral = Query(..., description="Metric to map"),
    year: int = Query(..., ge=1990, le=2100, description="Data year"),
    db: AsyncSession = Depends(get_db),
) -> ChoroplethResponse:
    """Return per-country values for the requested metric and year.

    Reads from ``mart_choropleth_cache`` (populated by dbt).
    Results are cached in Redis for 6 hours.
    """
    cache_key = f"choropleth:{metric}:{year}"
    cached = await cache_service.get(cache_key)
    if cached is not None:
        return ChoroplethResponse(**cached)

    try:
        response = await get_choropleth(db, metric=metric, year=year)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    await cache_service.set(cache_key, response.model_dump(), ttl_seconds=_CHOROPLETH_TTL)
    return response


@router.get("/flows/sankey", response_model=SankeyResponse)
async def sankey(
    year: int = Query(..., ge=1990, le=2100, description="Trade year"),
    top_n: int = Query(20, ge=1, le=50, description="Number of top flows to return"),
    exporter_region: Optional[str] = Query(None, description="Filter by exporter region"),
    importer_region: Optional[str] = Query(None, description="Filter by importer region"),
    flagged_only: bool = Query(False, description="Return only flagged / non-compliant flows"),
    category: Optional[int] = Query(None, ge=0, le=6, description="UN category code filter"),
    db: AsyncSession = Depends(get_db),
) -> SankeyResponse:
    """Return Sankey diagram data for trade flows in the requested year.

    Reads from ``mart_sankey_cache`` (populated by dbt).
    Results are cached in Redis for 6 hours.
    """
    cache_key = (
        f"sankey:{year}:{top_n}:{exporter_region or ''}:"
        f"{importer_region or ''}:{int(flagged_only)}:{category or ''}"
    )
    cached = await cache_service.get(cache_key)
    if cached is not None:
        return SankeyResponse(**cached)

    response = await get_sankey(
        db,
        year=year,
        top_n=top_n,
        exporter_region=exporter_region,
        importer_region=importer_region,
        flagged_only=flagged_only,
        category=category,
    )

    await cache_service.set(cache_key, response.model_dump(), ttl_seconds=_SANKEY_TTL)
    return response
